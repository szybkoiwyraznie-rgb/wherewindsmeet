#!/usr/bin/env python3
"""Następniki dialogów z tabeli `branch_dialog_subsequent` bazy gry.

Tabela mapuje numer sceny (dialogu) na UPORZĄDKOWANĄ listę scen-następników
(gałęzie po wyborze gracza / kontynuacje). To bezpośrednie, jawne źródło
krawędzi scena→scena — bez interpretacji.

Wyjście: index/mpk/nastepstwa_subsequent.jsonl —
  {"z": ["scena", nr], "do": ["scena", nr], "pozycja": i}
(pozycja = indeks na liście następników; 0 = pierwszy).

Wymaga bazy gry w `local/dane` (poza Gitem).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import baza_gry  # noqa: E402

KATALOGI = [
    ROOT / "local" / "dane" / "LocalData" / "Patch" / "HD" / "oversea",
    ROOT / "local" / "dane" / "Package" / "HD" / "oversea",
]


def main() -> int:
    for k in KATALOGI:
        if not k.is_dir():
            print(f"BŁĄD: brak katalogu bazy {k} — pobierz paczki do local/dane.")
            return 2
    baza = baza_gry.Baza([str(k) for k in KATALOGI])

    out = ROOT / "index" / "mpk" / "nastepstwa_subsequent.jsonl"
    n = 0
    wiersze = []
    for klucz, wartosc in baza.wiersze("branch_dialog_subsequent"):
        nastepniki = baza_gry.do_json(wartosc)
        if not isinstance(klucz, int) or not isinstance(nastepniki, list):
            continue
        for i, nast in enumerate(nastepniki):
            if isinstance(nast, int) and nast != klucz:
                wiersze.append({"z": ["scena", klucz], "do": ["scena", nast],
                                "pozycja": i})
                n += 1
    wiersze.sort(key=lambda w: (w["z"][1], w["pozycja"]))
    with open(out, "w", encoding="utf-8") as fh:
        for w in wiersze:
            fh.write(json.dumps(w, ensure_ascii=False) + "\n")
    print(json.dumps({"krawedzi": n, "plik": str(out.relative_to(ROOT))},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
