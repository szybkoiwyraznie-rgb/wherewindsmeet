#!/usr/bin/env python3
"""Identyfikatory tekstów gry -> treść i klucz przekładu (`index/nazwy.jsonl`).

W danych gry nazwy i opisy to **liczby** (`equip_items.name`,
`active_interact_way.button_name`, `curio_owner.owner_name`), a nie tekst.
Treść tych liczb leży w mapach języka:

    Package/HD/oversea/locale/translate_words_map_zh_cn      źródło
    Package/HD/oversea/locale/translate_words_map_zh_cn_diff poprawki
    Package/HD/oversea/locale/translate_words_map_en         tłumaczenie gry
    LocalData/Patch/HD/oversea/locale/…_diff                 poprawki pobrane

Klucz przekładu (`tools/tlumaczenie.py`) to SHA-256 z **tekstu źródłowego**
(`tools/mapa_tekstow.klucz`). Więc droga jest taka:

    identyfikator -> tekst chiński -> klucz -> polski przekład z `tlumaczenie/`

Ten skrypt robi z tego mały plik: bierze **tylko identyfikatory, których
naprawdę używa czytanka** (`index/poi.jsonl`, `index/pamiatki.jsonl`), więc nie
przepisuje 1,8 mln wpisów mapy. Wynik:

    {"id": 17335944675850932813, "k": "b86a976ba200e189",
     "zh": "龙纹标记", "en": "Dragon Pattern Mark"}

Użycie:
    python3 tools/nazwy_z_map.py [--wyj index/nazwy.jsonl] [PLIK ...]

Plikami wejściowymi są JSONL-e z identyfikatorami tekstów (domyślnie poi i
pamiątki). Wymaga danych gry (`local/dane`), więc w CI bez gry nie jest
uruchamiany — wynik leży w repozytorium.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:  # import jako moduł
    from tools import mapa_tekstow
except ImportError:  # uruchomienie jako skrypt
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from tools import mapa_tekstow  # noqa: PLC0415

DOMYSLNE_PLIKI = ("index/poi.jsonl", "index/pamiatki.jsonl")
POLA = ("nazwa", "nazwa_id", "wlasciciel_id")
JEZYKI = ("zh_cn", "en")


def _pliki_jezyka(language: str) -> list[Path]:
    wzor = f"translate_words_map_{language}*"
    znalezione = sorted(Path("local/dane").rglob(wzor))
    return [p for p in znalezione if p.is_file() and not p.name.endswith("_diff")] + [
        p for p in znalezione if p.is_file() and p.name.endswith("_diff")
    ]


def _mapa(language: str) -> dict[int, str]:
    pliki = _pliki_jezyka(language)
    if not pliki:
        return {}
    return mapa_tekstow.zloz(mapa_tekstow.wybierz_warstwy_gry(pliki))


def identyfikatory(pliki) -> list[int]:
    """Wszystkie identyfikatory tekstów z podanych JSONL-i, bez powtórzeń."""
    zbior: set[int] = set()
    for nazwa in pliki:
        sciezka = Path(nazwa)
        if not sciezka.is_file():
            continue
        for linia in sciezka.read_text(encoding="utf-8").splitlines():
            if not linia.strip():
                continue
            wiersz = json.loads(linia)
            for pole in POLA:
                wartosc = wiersz.get(pole)
                if isinstance(wartosc, int):
                    zbior.add(wartosc)
                elif isinstance(wartosc, str) and wartosc.isdigit():
                    zbior.add(int(wartosc))
    return sorted(zbior)


def nazwy(pliki, *, zrodlo: dict[int, str], english: dict[int, str]) -> list[dict]:
    wynik = []
    for ident in identyfikatory(pliki):
        zh = zrodlo.get(ident)
        if not zh:
            continue
        en = english.get(ident)
        wynik.append({
            "id": ident,
            "k": mapa_tekstow.klucz(zh),
            "zh": zh,
            "en": en if en and en != zh else "",
        })
    return wynik


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("pliki", nargs="*", default=None)
    parser.add_argument("--wyj", default="index/nazwy.jsonl")
    args = parser.parse_args(argv)
    pliki = args.pliki or list(DOMYSLNE_PLIKI)
    zrodlo = _mapa("zh_cn")
    if not zrodlo:
        print("brak map języka w local/dane (translate_words_map_*)", file=sys.stderr)
        return 2
    english = _mapa("en")
    wiersze = nazwy(pliki, zrodlo=zrodlo, english=english)
    cel = Path(args.wyj)
    cel.parent.mkdir(parents=True, exist_ok=True)
    with cel.open("w", encoding="utf-8") as plik:
        for wiersz in wiersze:
            plik.write(json.dumps(wiersz, ensure_ascii=False) + "\n")
    print(json.dumps({
        "wpisy": len(wiersze),
        "z_angielskim": sum(1 for w in wiersze if w["en"]),
        "plik": str(cel),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
