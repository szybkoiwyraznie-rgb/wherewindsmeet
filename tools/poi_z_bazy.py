#!/usr/bin/env python3
"""Punkty na mapie (POI) z tabeli `active_interact_way` bazy gry.

Każdy POI to jeden wiersz `active_interact_way`. Nazwa leży w kolumnie
`button_name` (tekst, świadkowie `index/teksty_*.jsonl`), a powiązanie ze sceną
— tylko tam, gdzie gra je naprawdę zapisuje:

    play_dialog_no      numer sceny (dialogu) uruchamianej po interakcji
    result_play_dialog  to samo dla wyniku interakcji

Reszta POI ma wyłącznie `interact_storyline` — **ścieżkę pliku klienta**
(`client/dialogs/hjt/sxd_longwenbiaoji.etsb`). Z niej nie da się policzyć numeru
sceny bez tego pliku, więc nazwę pliku zapisujemy jako dowód, a nie jako
powiązanie. Nie zgadujemy „ten POI startuje scenę N”, jeśli gra tego nie mówi.

Wynik: `index/poi.jsonl`, jeden wiersz na POI:

    {"id": 200046001, "dialog": null,
     "storyline": "client/dialogs/hjt/sxd_longwenbiaoji.etsb"}

Użycie:
    python3 tools/poi_z_bazy.py [KATALOG ...] [--wyj index/poi.jsonl]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:  # import jako moduł
    from tools import baza_gry
except ImportError:  # uruchomienie jako skrypt
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from tools import baza_gry  # noqa: PLC0415

DOMYSLNE = (
    "local/dane/Package/HD/oversea",
    "local/dane/LocalData/Patch/HD/oversea",
)
TABELA = "active_interact_way"


def _liczba(wartosc):
    if wartosc in (None, "") or isinstance(wartosc, bool):
        return None
    if isinstance(wartosc, int):
        return wartosc
    if isinstance(wartosc, str) and wartosc.isdigit():
        return int(wartosc)
    return None


def poi(katalogi) -> list[dict]:
    baza = baza_gry.Baza(list(katalogi))
    if TABELA not in baza.tabele:
        return []
    wynik = []
    for klucz, wiersz in baza.wiersze(TABELA):
        if not isinstance(wiersz, dict):
            continue
        identyfikator = _liczba(wiersz.get("id")) or _liczba(klucz)
        if identyfikator is None:
            continue
        if _liczba(wiersz.get("button_name")) is None and not wiersz.get("interact_storyline"):
            continue
        dialog = _liczba(wiersz.get("play_dialog_no")) or _liczba(wiersz.get("result_play_dialog"))
        wynik.append({
            "id": identyfikator,
            "dialog": dialog,
            "storyline": str(wiersz.get("interact_storyline") or ""),
        })
    wynik.sort(key=lambda w: w["id"])
    return wynik


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("katalogi", nargs="*", default=None)
    parser.add_argument("--wyj", default="index/poi.jsonl")
    args = parser.parse_args(argv)
    katalogi = args.katalogi or [k for k in DOMYSLNE if Path(k).is_dir()]
    if not katalogi or not any(Path(k, "MANIFEST").is_file() for k in katalogi):
        print("brak bazy gry (MANIFEST) w:", ", ".join(katalogi) or "—", file=sys.stderr)
        return 2
    wiersze = poi(katalogi)
    cel = Path(args.wyj)
    cel.parent.mkdir(parents=True, exist_ok=True)
    with cel.open("w", encoding="utf-8") as plik:
        for wiersz in wiersze:
            plik.write(json.dumps(wiersz, ensure_ascii=False) + "\n")
    print(json.dumps({
        "poi": len(wiersze),
        "z_dialogiem": sum(1 for w in wiersze if w["dialog"]),
        "plik": str(cel),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
