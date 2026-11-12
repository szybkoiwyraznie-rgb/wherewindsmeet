#!/usr/bin/env python3
"""Łatka tłumaczenia: przepisuje mapy tekstów gry polskimi przekładami z magazynu.

    python3 tools/zbuduj_latke.py --indeks index --magazyn tlumaczenie \\
        --zh translate_words_map_zh_cn [translate_words_map_zh_cn_diff ...] \\
        --cel translate_words_map_en [--cel translate_words_map_en_diff ...] \\
        --wyj dist/latka

Gra nie ma języka polskiego, więc przekład zastępuje teksty jednego z języków
klienta (tu: plików podanych w `--cel`, zwykle angielskich). Każdy plik celu —
mapa podstawowa i jej warstwy `_diff` — jest przepisywany osobno i zapisywany
pod tą samą nazwą w katalogu wyjściowym. Oryginały nie są zmieniane.

Skąd bierze się przekład jednego wpisu (identyfikatora tekstu):
1. z magazynu po identyfikatorze (`pl_warianty.jsonl`) — kwestie zależne od płci
   bohatera; pusty wariant dziedziczy po drugim wariancie tego samego tekstu;
2. z magazynu po kluczu tekstu źródłowego: klucz liczy się z tekstu chińskiego
   tego identyfikatora (`--zh`), a gdy chińskiego nie ma — z tekstu w pliku celu.

Wpis bez przekładu zostaje bez zmian. Po zapisaniu każdy plik jest czytany
z powrotem i porównywany wpis po wpisie: zmienić się mogły tylko wpisy
z przekładem i tylko na ten przekład.

To narzędzie nie instaluje niczego w grze i **nie było sprawdzone w grze** —
patrz docs/PAKIET_TLUMACZA.md, rozdział o łatce.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

try:
    from tools import apply_translation as patcher
    from tools import indeks as indeks_mod
    from tools import locale_records as records
    from tools import mapa_tekstow
    from tools import tlumaczenie as magazyn_mod
except ImportError:  # uruchomienie jako skrypt
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from tools import apply_translation as patcher
    from tools import indeks as indeks_mod
    from tools import locale_records as records
    from tools import mapa_tekstow
    from tools import tlumaczenie as magazyn_mod


class LatkaError(Exception):
    """Łatki nie da się zbudować albo wynik nie przeszedł kontroli."""


def rodzenstwo_wariantow(warianty: dict[str, dict]) -> dict[str, list[str]]:
    """Klucz tekstu -> identyfikatory (hex) kwestii zależnych od płci z tym tekstem."""
    groups: dict[str, list[str]] = defaultdict(list)
    for ident in sorted(warianty):
        groups[warianty[ident]["k"]].append(ident)
    return groups


def przeklady_pliku(
    teksty: dict[int, str],
    zh: dict[int, str],
    magazyn: magazyn_mod.Magazyn,
    warianty: dict[str, dict],
    rodzenstwo: dict[str, list[str]],
) -> dict[int, str]:
    """`id -> przekład` dla wpisów jednego pliku; tylko wpisy, które się zmienią."""
    wanted: dict[int, str] = {}
    for ident, current in teksty.items():
        hex_id = f"{ident:016x}"
        text = magazyn.po_id.get(hex_id)
        if text is None and hex_id in warianty:
            for sibling in rodzenstwo.get(warianty[hex_id]["k"], ()):
                if sibling in magazyn.po_id:
                    text = magazyn.po_id[sibling]
                    break
        if text is None:
            source = zh.get(ident, current)
            text = magazyn.po_kluczu.get(mapa_tekstow.klucz(source))
        if text and text != current:
            wanted[ident] = text
    return wanted


def przepisz(path: Path, cel: Path, zh: dict[int, str], magazyn, warianty, rodzenstwo, poziom: int = 9) -> dict:
    """Przepisz jeden plik mapy do `cel` i zwróć raport; rzuca `LatkaError` przy niezgodności."""
    try:
        data = path.read_bytes()
        teksty, _removed = mapa_tekstow.wczytaj_warstwe(path)
        wanted = przeklady_pliku(teksty, zh, magazyn, warianty, rodzenstwo)
        patched, stats = patcher.apply_translations(data, wanted, level=poziom, text_map={})
        check = patcher.verify(data, patched, wanted, text_map={})
    except (OSError, mapa_tekstow.MapaError, patcher.PatchError, records.LayoutError) as error:
        raise LatkaError(f"{path.name}: {error}") from error
    if check["changed"] != len(wanted) or stats["ids_not_in_map"]:
        raise LatkaError(f"{path.name}: zmieniono {check['changed']} wpisów, oczekiwano {len(wanted)}")
    cel.write_bytes(patched)
    return {
        "plik": path.name,
        "wpisow": len(teksty),
        "przetlumaczonych": len(wanted),
        "procent": round(100 * len(wanted) / len(teksty), 2) if teksty else 0,
        "bajtow_przed": len(data),
        "bajtow_po": len(patched),
        "sha256_przed": mapa_tekstow.sha256_pliku(path),
        "sha256_po": mapa_tekstow.sha256_pliku(cel),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Zbuduj łatkę: mapy tekstów z polskimi przekładami.")
    parser.add_argument("--indeks", default="index")
    parser.add_argument("--magazyn", default="tlumaczenie")
    parser.add_argument("--zh", nargs="+", required=True, help="mapa zh_cn i jej warstwy _diff, w kolejności nakładania")
    parser.add_argument("--cel", action="append", required=True, help="plik mapy do przepisania (można podać kilka razy)")
    parser.add_argument("--wyj", required=True, help="katalog na przepisane pliki i raport latka.json")
    parser.add_argument("--poziom", type=int, default=9, help="poziom kompresji zstd")
    arguments = parser.parse_args(argv)

    out = Path(arguments.wyj)
    targets = [Path(item) for item in arguments.cel]
    names = [path.name for path in targets]
    if len(set(names)) != len(names):
        print(json.dumps({"ok": False, "powod": "dwa pliki celu mają tę samą nazwę — zbuduj je w osobnych katalogach"}, ensure_ascii=False))
        return 1
    if any(out.resolve() == path.parent.resolve() for path in targets):
        print(json.dumps({"ok": False, "powod": "katalog wyjściowy nie może być katalogiem plików celu"}, ensure_ascii=False))
        return 1
    try:
        ix = indeks_mod.wczytaj(arguments.indeks, teksty=False, sceny=False)
        magazyn = magazyn_mod.wczytaj(arguments.magazyn)
        if not len(magazyn):
            raise LatkaError("magazyn przekładów jest pusty — nie ma czego wstawiać")
        zh = mapa_tekstow.zloz(arguments.zh)
        siblings = rodzenstwo_wariantow(ix.warianty)
        out.mkdir(parents=True, exist_ok=True)
        files = [przepisz(path, out / path.name, zh, magazyn, ix.warianty, siblings, arguments.poziom) for path in targets]
    except (indeks_mod.IndeksError, magazyn_mod.MagazynError, mapa_tekstow.MapaError, LatkaError, OSError) as error:
        print(json.dumps({"ok": False, "powod": str(error)}, ensure_ascii=False))
        return 1
    report = {
        "format": "wwm-latka-v1",
        "przekladow_w_magazynie": len(magazyn),
        "pliki": files,
        "uwaga": "łatka nie była sprawdzona w grze; przed podmianą plików zrób kopię oryginałów",
    }
    (out / "latka.json").write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, **report}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
