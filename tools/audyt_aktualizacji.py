#!/usr/bin/env python3
"""Audyt aktualizacji gry: co się zmieniło między dwoma wyciągami `index/`.

    # po nowym patchu gry: zbuduj nowy wyciąg w katalogu roboczym (tools/wyciag.py),
    # a potem porównaj go z wersją z ostatniego commita:
    python3 tools/audyt_aktualizacji.py --stary-git HEAD --nowy index --wyj dist/audyt \\
        --tlumaczenie tlumaczenie

    # albo z dowolnym katalogiem starego wyciągu:
    python3 tools/audyt_aktualizacji.py --stary KATALOG --nowy index --wyj dist/audyt

Wynik w `--wyj`:
    audyt.json       liczby i listy: nowe i usunięte teksty, sceny nowe / zmienione / usunięte
    nowe_sloty.txt   klucze nowych tekstów i `@id` nowych kwestii zależnych od płci —
                     wejście `tools/buduj_paczke.py --tylko-sloty` (pakiet uzupełniający)
    AUDYT.md         to samo po ludzku

„Nowy tekst” to tekst źródłowy, którego klucza nie było w starym wyciągu. Tekst,
który zmienił tylko identyfikator, nie jest nowy — jego przekład działa dalej.
Zmieniony tekst pod starym identyfikatorem ma nowy klucz, więc jest nowy.
"""

from __future__ import annotations

import argparse
import io
import json
import subprocess
import sys
import tarfile
import tempfile
from collections import Counter
from pathlib import Path

try:
    from tools import indeks as indeks_mod
    from tools import tlumaczenie as magazyn_mod
    from tools import wypisz
except ImportError:  # uruchomienie jako skrypt
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from tools import indeks as indeks_mod
    from tools import tlumaczenie as magazyn_mod
    from tools import wypisz

MAKS_NA_LISCIE = 500


class AudytError(Exception):
    """Nie da się porównać wyciągów."""


def _sloty_sceny(scena: dict) -> list[str]:
    return ["@" + element[4] if len(element) > 4 and element[3] else element[2] for element in scena["e"]]


def _ma_en_tekst(text) -> bool:
    return text is not None and (text.en is not None or text.z_en)


def _ma_en_wariant(ix, ident: str) -> bool:
    var = ix.warianty.get(ident, {})
    return bool(var.get("en") or _ma_en_tekst(ix.teksty.get(var.get("k", ""))))


def porownaj(stary, nowy, magazyn=None, *, tylko_z_en: bool = False) -> tuple[dict, list[str]]:
    """Porównaj dwa wczytane wyciągi; zwraca (raport, lista nowych slotów)."""
    if tylko_z_en:
        old_keys = {key for key, text in stary.teksty.items() if _ma_en_tekst(text)}
        new_keys = {key for key, text in nowy.teksty.items() if _ma_en_tekst(text)}
        old_variants = {ident for ident in stary.warianty if _ma_en_wariant(stary, ident)}
        new_variants = {ident for ident in nowy.warianty if _ma_en_wariant(nowy, ident)}
    else:
        old_keys, new_keys = set(stary.teksty), set(nowy.teksty)
        old_variants, new_variants = set(stary.warianty), set(nowy.warianty)
    added = new_keys - old_keys
    added_variants = new_variants - old_variants
    removed = old_keys - new_keys

    by_table = Counter()
    for key in added:
        source = nowy.zrodlo(nowy.teksty[key])
        by_table[source[0] if source else "(bez tabeli: scena albo brak źródła)"] += 1

    scenes = {"nowe": [], "zmienione": [], "usuniete": [], "bez_zmian": 0}
    new_lines = 0
    for number, scene in nowy.sceny.items():
        slots = _sloty_sceny(scene)
        fresh = sum(1 for slot in slots if (slot[1:] in added_variants if slot.startswith("@") else slot in added))
        previous = stary.sceny.get(number)
        if previous is None:
            if slots:
                scenes["nowe"].append([number, len(slots), fresh])
                new_lines += fresh
        elif _sloty_sceny(previous) != slots:
            scenes["zmienione"].append([number, len(slots), fresh])
            new_lines += fresh
        else:
            scenes["bez_zmian"] += 1
    scenes["usuniete"] = sorted(number for number in stary.sceny if number not in nowy.sceny)

    slots = sorted(added) + sorted("@" + ident for ident in added_variants)
    report = {
        "format": "wwm-audyt-v1",
        "tylko_z_en": tylko_z_en,
        "stary": {"opis": stary.manifest.get("wejscia", {}).get("opis", ""), "tekstow": len(old_keys), "scen": len(stary.sceny)},
        "nowy": {"opis": nowy.manifest.get("wejscia", {}).get("opis", ""), "tekstow": len(new_keys), "scen": len(nowy.sceny)},
        "teksty": {
            "nowe": len(added),
            "nowe_kwestie_zalezne_od_plci": len(added_variants),
            "usuniete": len(removed),
            "bez_zmian": len(new_keys & old_keys),
            "nowe_wg_tabeli": dict(by_table.most_common(40)),
        },
        "sceny": {
            "nowe": len(scenes["nowe"]),
            "zmienione": len(scenes["zmienione"]),
            "usuniete": len(scenes["usuniete"]),
            "bez_zmian": scenes["bez_zmian"],
            "nowych_tekstow_w_scenach": new_lines,
            "lista_nowych": sorted(scenes["nowe"])[:MAKS_NA_LISCIE],
            "lista_zmienionych": sorted(scenes["zmienione"])[:MAKS_NA_LISCIE],
            "lista_usunietych": scenes["usuniete"][:MAKS_NA_LISCIE],
        },
        "zadania": {
            "nowe": len(set(nowy.zadania) - set(stary.zadania)),
            "usuniete": len(set(stary.zadania) - set(nowy.zadania)),
        },
        "do_tlumacza": len(slots),
    }
    if magazyn is not None:
        wanted = new_keys | {"@" + ident for ident in new_variants}
        done = sum(1 for slot in wanted if magazyn.ma(slot))
        orphaned = sum(1 for key in magazyn.po_kluczu if key not in new_keys)
        report["przeklady"] = {
            "miejsc_w_grze": len(wanted),
            "przetlumaczonych": done,
            "brakuje": len(wanted) - done,
            "przekladow_bez_tekstu_w_grze": orphaned,
        }
    return report, slots


def opis(report: dict) -> str:
    texts, scenes = report["teksty"], report["sceny"]
    suffix = " --tylko-z-en" if report.get("tylko_z_en") else ""
    lines = [
        "# Audyt aktualizacji gry",
        "",
        f"- poprzedni wyciąg: {report['stary']['opis'] or '(bez opisu)'} — {report['stary']['tekstow']} tekstów, {report['stary']['scen']} scen",
        f"- nowy wyciąg: {report['nowy']['opis'] or '(bez opisu)'} — {report['nowy']['tekstow']} tekstów, {report['nowy']['scen']} scen",
        *(["- zakres: wyłącznie wpisy z wersją angielską (`--tylko-z-en`)"] if report.get("tylko_z_en") else []),
        "",
        "## Teksty",
        "",
        f"- nowe: **{texts['nowe']}** (plus {texts['nowe_kwestie_zalezne_od_plci']} nowych kwestii zależnych od płci bohatera)",
        f"- usunięte z gry: {texts['usuniete']}",
        f"- bez zmian: {texts['bez_zmian']}",
        "",
        "## Sceny",
        "",
        f"- nowe: {scenes['nowe']}, zmienione: {scenes['zmienione']}, usunięte: {scenes['usuniete']}, bez zmian: {scenes['bez_zmian']}",
        f"- nowych tekstów w scenach: {scenes['nowych_tekstow_w_scenach']}",
        "",
        f"## Do tłumacza: {report['do_tlumacza']} miejsc `PL:`",
        "",
        f"Lista kluczy: `nowe_sloty.txt` → `python3 tools/buduj_paczke.py --tylko-sloty nowe_sloty.txt{suffix} …`.",
    ]
    if texts["nowe_wg_tabeli"]:
        lines += ["", "## Nowe teksty według tabeli", "", "| tabela | nowych tekstów |", "|---|---:|"]
        lines += [f"| `{name}` | {count} |" for name, count in texts["nowe_wg_tabeli"].items()]
    if "przeklady" in report:
        done = report["przeklady"]
        lines += [
            "",
            "## Stan przekładu po aktualizacji",
            "",
            f"- miejsc w grze: {done['miejsc_w_grze']}, przetłumaczonych: {done['przetlumaczonych']}, brakuje: {done['brakuje']}",
            f"- przekładów w magazynie, których tekstu nie ma już w grze: {done['przekladow_bez_tekstu_w_grze']} (zostają — tekst może wrócić)",
        ]
    return "\n".join(lines) + "\n"


def indeks_z_gita(ref: str, katalog: Path, repo: Path) -> Path:
    """Wypakuj `index/` z podanego commita do katalogu tymczasowego."""
    result = subprocess.run(["git", "archive", "--format=tar", ref, "index"], cwd=repo, capture_output=True, check=False)
    if result.returncode:
        raise AudytError(f"git archive {ref}: {result.stderr.decode('utf-8', 'replace').strip()}")
    with tarfile.open(fileobj=io.BytesIO(result.stdout)) as archive:
        for member in archive.getmembers():
            if not member.isfile() or not member.name.startswith("index/") or ".." in member.name:
                continue
            target = katalog / Path(member.name).name
            target.write_bytes(archive.extractfile(member).read())
    return katalog


def main(argv=None) -> int:
    wypisz.utf8()
    parser = argparse.ArgumentParser(description="Porównaj dwa wyciągi index/ po aktualizacji gry.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--stary", help="katalog poprzedniego wyciągu")
    source.add_argument("--stary-git", help="commit, z którego wziąć poprzedni index/ (np. HEAD)")
    parser.add_argument("--nowy", default="index")
    parser.add_argument("--wyj", required=True)
    parser.add_argument("--tlumaczenie", help="magazyn przekładów: policz, ile po aktualizacji brakuje")
    parser.add_argument("--tylko-z-en", action="store_true", help="porównuj wyłącznie wpisy z wersją angielską (pomija wyłącznie chińskie)")
    arguments = parser.parse_args(argv)
    try:
        with tempfile.TemporaryDirectory(prefix="wwm-audyt-") as temp:
            old_dir = arguments.stary or indeks_z_gita(arguments.stary_git, Path(temp), Path.cwd())
            stary = indeks_mod.wczytaj(old_dir)
        nowy = indeks_mod.wczytaj(arguments.nowy)
        magazyn = magazyn_mod.wczytaj(arguments.tlumaczenie) if arguments.tlumaczenie else None
        report, slots = porownaj(stary, nowy, magazyn, tylko_z_en=arguments.tylko_z_en)
    except (indeks_mod.IndeksError, magazyn_mod.MagazynError, AudytError, OSError) as error:
        print(json.dumps({"ok": False, "powod": str(error)}, ensure_ascii=False))
        return 1
    out = Path(arguments.wyj)
    out.mkdir(parents=True, exist_ok=True)
    (out / "audyt.json").write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    (out / "nowe_sloty.txt").write_text("".join(slot + "\n" for slot in slots), encoding="utf-8", newline="\n")
    (out / "AUDYT.md").write_text(opis(report), encoding="utf-8", newline="\n")
    print(json.dumps({"ok": True, "tylko_z_en": report["tylko_z_en"], "teksty": {k: v for k, v in report["teksty"].items() if k != "nowe_wg_tabeli"}, "sceny": {k: v for k, v in report["sceny"].items() if not k.startswith("lista")}, "do_tlumacza": report["do_tlumacza"]}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
