#!/usr/bin/env python3
"""Audyt aktualizacji gry: co się zmieniło między dwoma wyciągami `index/`.

    # po nowym patchu gry: zbuduj nowy wyciąg w katalogu roboczym (tools/wyciag.py),
    # a potem porównaj go z wersją z ostatniego commita:
    python3 tools/audyt_aktualizacji.py --stary-git HEAD --nowy index --wyj dist/audyt \\
        --tlumaczenie tlumaczenie

    # albo z dowolnym katalogiem starego wyciągu:
    python3 tools/audyt_aktualizacji.py --stary KATALOG --nowy index --wyj dist/audyt

Wynik w `--wyj`:
    audyt.json            liczby i listy: nowe i usunięte teksty, sceny nowe / zmienione / usunięte
    nowe_sloty.txt        klucze nowych tekstów i `@id` nowych kwestii zależnych od płci —
                          wejście `tools/buduj_paczke.py --tylko-sloty` (pakiet uzupełniający)
    usuniete_klucze.txt   klucze i `@id` usunięte między wyciągami (jeden na linię)
    usuniete_klucze.jsonl usunięte wpisy ze szczegółami (`k`, `sekcja`, `plik`, `zh`, `en`, `pl`)
    rewizje_en.jsonl      zmiany `EN -> EN` przy wspólnym `ZH`, wyłącznie dla już przetłumaczonych wpisów
                          (`{"k","sekcja","plik","zh","en_przed","en_po","pl"}`) — gdy podano `--tlumaczenie`
    AUDYT.md              to samo po ludzku

„Nowy tekst” to tekst źródłowy, którego klucza nie było w starym wyciągu. Tekst,
który zmienił tylko identyfikator, nie jest nowy — jego przekład działa dalej.
Zmieniony tekst pod starym identyfikatorem ma nowy klucz, więc jest nowy.
"""

from __future__ import annotations

import argparse
import io
import json
import re
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from collections import Counter
from pathlib import Path

try:
    from tools import format_paczki as fmt
    from tools import indeks as indeks_mod
    from tools import tlumaczenie as magazyn_mod
    from tools import wypisz
except ImportError:  # uruchomienie jako skrypt
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from tools import format_paczki as fmt
    from tools import indeks as indeks_mod
    from tools import tlumaczenie as magazyn_mod
    from tools import wypisz

MAKS_NA_LISCIE = 500
_RE_KLUCZ_LINIA = re.compile(r"^\s+klucz:\s*(@?[0-9a-f]{16})\s*$")


class AudytError(Exception):
    """Nie da się porównać wyciągów."""


def _sloty_sceny(scena: dict) -> list[str]:
    return ["@" + element[4] if len(element) > 4 and element[3] else element[2] for element in scena["e"]]


def _ma_en_tekst(text) -> bool:
    return text is not None and (text.en is not None or text.z_en)


def _ma_en_wariant(ix, ident: str) -> bool:
    var = ix.warianty.get(ident, {})
    return bool(var.get("en") or _ma_en_tekst(ix.teksty.get(var.get("k", ""))))


def _zapisz_sloty_z_md(tekst: str, sekcja: str, nazwa_pliku: str, wynik: dict[str, tuple[str, str]]) -> None:
    for line in tekst.splitlines():
        match = _RE_KLUCZ_LINIA.match(line)
        if match:
            wynik.setdefault(match.group(1), (sekcja, nazwa_pliku))


def _zbierz_z_zipa_bytes(data: bytes, wynik: dict[str, tuple[str, str]], domyslna_sekcja: str = "") -> None:
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for info in sorted(zf.infolist(), key=lambda i: i.filename):
            if info.is_dir():
                continue
            name = info.filename.replace("\\", "/")
            lower = name.lower()
            if lower in ("sceny.zip", "cutsceny.zip", "widoki.zip"):
                _zbierz_z_zipa_bytes(zf.read(info), wynik, domyslna_sekcja=Path(lower).stem)
            elif lower.endswith(".zip"):
                _zbierz_z_zipa_bytes(zf.read(info), wynik, domyslna_sekcja=domyslna_sekcja)
            elif lower.endswith(".md"):
                parts = Path(name).parts
                if len(parts) >= 2 and parts[0] in ("sceny", "cutsceny", "widoki"):
                    sekcja, plik = parts[0], parts[-1]
                else:
                    sekcja, plik = domyslna_sekcja or "widoki", Path(name).name
                _zapisz_sloty_z_md(zf.read(info).decode("utf-8-sig", "replace"), sekcja, plik, wynik)


def zbierz_sloty_z_paczki(sciezka: Path | str) -> dict[str, tuple[str, str]]:
    """Mapa `slot -> (sekcja, plik_md)` wczytana z katalogu albo archiwum ZIP pakietu."""
    root = Path(sciezka)
    if not root.exists():
        raise AudytError(f"nie ma pakietu: {sciezka}")
    wynik: dict[str, tuple[str, str]] = {}
    if root.is_file() and root.suffix.lower() == ".zip":
        _zbierz_z_zipa_bytes(root.read_bytes(), wynik)
        return wynik
    if root.is_dir():
        found_dir = False
        for sekcja in ("sceny", "cutsceny", "widoki"):
            sub = root / sekcja
            if sub.is_dir():
                found_dir = True
                for md in sorted(sub.glob("*.md")):
                    _zapisz_sloty_z_md(md.read_text(encoding="utf-8-sig", errors="replace"), sekcja, md.name, wynik)
        if not found_dir:
            for sekcja in ("sceny", "cutsceny", "widoki"):
                sub_zip = root / f"{sekcja}.zip"
                if sub_zip.is_file():
                    _zbierz_z_zipa_bytes(sub_zip.read_bytes(), wynik, domyslna_sekcja=sekcja)
        return wynik
    raise AudytError(f"nieznany format pakietu: {sciezka}")


def _indeks_klas_cache(ix) -> dict:
    from tools import buduj_paczke

    scene_keys: set[str] = set()
    for scene in ix.sceny.values():
        for el in scene["e"]:
            scene_keys.add(el[2])
            if len(el) > 4 and el[3]:
                scene_keys.add("@" + el[4])
    for row in ix.wybory.values():
        for ch in row.get("wybory", ()):
            scene_keys.add(ch["tekst"])

    cut_keys: set[str] = set()
    for typ in ("napis", "intro", "film"):
        for row in ix.cutsceny_kontekst.get(typ, ()):
            if row.get("k"):
                cut_keys.add(row["k"])
    for row in ix.cutsceny_kontekst.get("powtorka", ()):
        for f in ("nazwa", "rozdzial", "streszczenie"):
            if row.get(f):
                cut_keys.add(row[f])
    for row in ix.przerywniki.values():
        for f in ("tekst", "streszczenie"):
            if row.get(f):
                cut_keys.add(row[f])
    return {"sceny": scene_keys, "cutsceny": cut_keys, "kategoria": buduj_paczke.kategoria}


def _klasyfikuj_z_indeksu(ix, slot: str, cache: dict) -> tuple[str, str]:
    if slot in cache["sceny"]:
        return "sceny", "dialogi"
    key = ix.warianty[slot[1:]]["k"] if slot.startswith("@") and slot[1:] in ix.warianty else slot
    if key in cache["cutsceny"]:
        return "cutsceny", "cutsceny"
    text = ix.teksty.get(key)
    if text is None:
        return "widoki", "10_bez_zrodla"
    src = ix.zrodlo(text)
    if src is None:
        return "widoki", "10_bez_zrodla"
    return "widoki", cache["kategoria"](src[0])


def rewizje_en(
    stary,
    nowy,
    magazyn,
    *,
    tylko_z_en: bool = False,
    sloty_w_paczce: dict[str, tuple[str, str]] | None = None,
) -> list[dict]:
    """Wpisy już przetłumaczone w `magazyn`, w których zmienił się tekst `EN -> EN` przy tym samym `ZH`."""
    if magazyn is None:
        return []
    cache = None
    rows: list[dict] = []

    def loc(slot: str) -> tuple[str, str]:
        nonlocal cache
        if sloty_w_paczce and slot in sloty_w_paczce:
            return sloty_w_paczce[slot]
        if cache is None:
            cache = _indeks_klas_cache(nowy)
        return _klasyfikuj_z_indeksu(nowy, slot, cache)

    for key in sorted(set(stary.teksty) & set(nowy.teksty)):
        pl = magazyn.przeklad(key)
        if not pl:
            continue
        old_t, new_t = stary.teksty[key], nowy.teksty[key]
        if tylko_z_en and not (_ma_en_tekst(old_t) and _ma_en_tekst(new_t)):
            continue
        if old_t.en and new_t.en and old_t.en != new_t.en:
            sekcja, plik = loc(key)
            rows.append(
                {
                    "k": key,
                    "sekcja": sekcja,
                    "plik": plik,
                    "zh": new_t.zrodlo,
                    "en_przed": old_t.en,
                    "en_po": new_t.en,
                    "pl": pl,
                }
            )

    for vid in sorted(set(stary.warianty) & set(nowy.warianty)):
        slot = "@" + vid
        pl = magazyn.przeklad(slot)
        if not pl:
            continue
        old_v, new_v = stary.warianty[vid], nowy.warianty[vid]
        if tylko_z_en and not (_ma_en_wariant(stary, vid) and _ma_en_wariant(nowy, vid)):
            continue
        old_en, new_en = old_v.get("en"), new_v.get("en")
        if old_en and new_en and old_en != new_en:
            base_t = nowy.teksty.get(new_v.get("k", ""))
            sekcja, plik = loc(slot)
            rows.append(
                {
                    "k": slot,
                    "sekcja": sekcja,
                    "plik": plik,
                    "zh": base_t.zrodlo if base_t else "",
                    "en_przed": old_en,
                    "en_po": new_en,
                    "pl": pl,
                }
            )

    rows.sort(key=lambda r: (r["sekcja"], r["plik"], r["k"]))
    return rows


def usuniete_klucze(
    stary,
    nowy,
    magazyn=None,
    *,
    tylko_z_en: bool = False,
    sloty_w_paczce: dict[str, tuple[str, str]] | None = None,
    dodatkowe_pl: dict[str, str] | None = None,
) -> list[dict]:
    """Klucze i `@id` usunięte między `stary` a `nowy`, z ewentualnym `pl` z magazynu lub zwrotki."""
    if tylko_z_en:
        old_keys = {k for k, t in stary.teksty.items() if _ma_en_tekst(t)}
        new_keys = {k for k, t in nowy.teksty.items() if _ma_en_tekst(t)}
        old_variants = {vid for vid in stary.warianty if _ma_en_wariant(stary, vid)}
        new_variants = {vid for vid in nowy.warianty if _ma_en_wariant(nowy, vid)}
    else:
        old_keys, new_keys = set(stary.teksty), set(nowy.teksty)
        old_variants, new_variants = set(stary.warianty), set(nowy.warianty)

    cache = None

    def loc(slot: str) -> tuple[str, str]:
        nonlocal cache
        if sloty_w_paczce and slot in sloty_w_paczce:
            return sloty_w_paczce[slot]
        if cache is None:
            cache = _indeks_klas_cache(stary)
        return _klasyfikuj_z_indeksu(stary, slot, cache)

    rows: list[dict] = []
    for key in sorted(old_keys - new_keys):
        t = stary.teksty[key]
        pl = (magazyn.przeklad(key) if magazyn is not None else None) or (dodatkowe_pl.get(key) if dodatkowe_pl else None)
        sekcja, plik = loc(key)
        rows.append(
            {
                "k": key,
                "sekcja": sekcja,
                "plik": plik,
                "zh": t.zrodlo,
                "en": t.en,
                "pl": pl,
            }
        )
    for vid in sorted(old_variants - new_variants):
        slot = "@" + vid
        v = stary.warianty[vid]
        base_t = stary.teksty.get(v.get("k", ""))
        pl = (magazyn.przeklad(slot) if magazyn is not None else None) or (dodatkowe_pl.get(slot) if dodatkowe_pl else None)
        sekcja, plik = loc(slot)
        rows.append(
            {
                "k": slot,
                "sekcja": sekcja,
                "plik": plik,
                "zh": base_t.zrodlo if base_t else "",
                "en": v.get("en"),
                "pl": pl,
            }
        )
    return rows


def _zbierz_pl_ze_zwrotki(sciezki: list[str]) -> dict[str, str]:
    from tools import import_zwrotki

    out: dict[str, str] = {}
    try:
        for _name, content in import_zwrotki.pliki_zwrotki(sciezki):
            for entry in fmt.czytaj_wpisy(content):
                if entry.pl and not entry.ciag_dalszy:
                    out.setdefault(entry.klucz, fmt.odkoduj(entry.pl))
    except import_zwrotki.ZwrotkaError as error:
        raise AudytError(str(error)) from error
    return out


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
        f"- usunięte z gry: {texts['usuniete']} (pełna lista: `usuniete_klucze.txt`, `usuniete_klucze.jsonl`)",
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
        if "rewizji_en" in done:
            lines.append(f"- zmian `EN -> EN` wśród już przetłumaczonych wpisów: **{done['rewizji_en']}** (`rewizje_en.jsonl`)")
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
    parser.add_argument("--tlumaczenie", help="magazyn przekładów: policz braki i wyeksportuj `rewizje_en.jsonl`")
    parser.add_argument("--tylko-z-en", action="store_true", help="porównuj wyłącznie wpisy z wersją angielską (pomija wyłącznie chińskie)")
    parser.add_argument("--paczka", help="katalog lub zip docelowej paczki (do dokładnych nazw plików `.md` w `rewizje_en.jsonl`)")
    parser.add_argument("--stara-paczka", help="katalog lub zip poprzedniej paczki (do dokładnych nazw plików `.md` w `usuniete_klucze.jsonl`)")
    parser.add_argument("--usuniete-pl-z", nargs="*", default=[], help="opcjonalne pliki/zipy zwrotek do uzupełnienia pola `pl` w `usuniete_klucze.jsonl`")
    arguments = parser.parse_args(argv)
    try:
        with tempfile.TemporaryDirectory(prefix="wwm-audyt-") as temp:
            old_dir = arguments.stary or indeks_z_gita(arguments.stary_git, Path(temp), Path.cwd())
            stary = indeks_mod.wczytaj(old_dir)
        nowy = indeks_mod.wczytaj(arguments.nowy)
        magazyn = magazyn_mod.wczytaj(arguments.tlumaczenie) if arguments.tlumaczenie else None
        sloty_nowe = zbierz_sloty_z_paczki(arguments.paczka) if arguments.paczka else None
        sloty_stare = zbierz_sloty_z_paczki(arguments.stara_paczka) if arguments.stara_paczka else None
        extra_pl = _zbierz_pl_ze_zwrotki(arguments.usuniete_pl_z) if arguments.usuniete_pl_z else None
        report, slots = porownaj(stary, nowy, magazyn, tylko_z_en=arguments.tylko_z_en)
        deleted_rows = usuniete_klucze(
            stary,
            nowy,
            magazyn,
            tylko_z_en=arguments.tylko_z_en,
            sloty_w_paczce=sloty_stare,
            dodatkowe_pl=extra_pl,
        )
        en_revisions = (
            rewizje_en(
                stary,
                nowy,
                magazyn,
                tylko_z_en=arguments.tylko_z_en,
                sloty_w_paczce=sloty_nowe,
            )
            if magazyn is not None
            else None
        )
        if en_revisions is not None and "przeklady" in report:
            report["przeklady"]["rewizji_en"] = len(en_revisions)
    except (indeks_mod.IndeksError, magazyn_mod.MagazynError, AudytError, OSError, zipfile.BadZipFile) as error:
        print(json.dumps({"ok": False, "powod": str(error)}, ensure_ascii=False))
        return 1
    out = Path(arguments.wyj)
    out.mkdir(parents=True, exist_ok=True)
    (out / "audyt.json").write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    (out / "nowe_sloty.txt").write_text("".join(slot + "\n" for slot in slots), encoding="utf-8", newline="\n")
    (out / "usuniete_klucze.txt").write_text("".join(row["k"] + "\n" for row in deleted_rows), encoding="utf-8", newline="\n")
    (out / "usuniete_klucze.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in deleted_rows),
        encoding="utf-8",
        newline="\n",
    )
    if en_revisions is not None:
        (out / "rewizje_en.jsonl").write_text(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in en_revisions),
            encoding="utf-8",
            newline="\n",
        )
    (out / "AUDYT.md").write_text(opis(report), encoding="utf-8", newline="\n")
    print(
        json.dumps(
            {
                "ok": True,
                "tylko_z_en": report["tylko_z_en"],
                "teksty": {k: v for k, v in report["teksty"].items() if k != "nowe_wg_tabeli"},
                "sceny": {k: v for k, v in report["sceny"].items() if not k.startswith("lista")},
                "do_tlumacza": report["do_tlumacza"],
                "usuniete_klucze": len(deleted_rows),
                **({"rewizji_en": len(en_revisions)} if en_revisions is not None else {}),
            },
            ensure_ascii=False,
            indent=1,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
