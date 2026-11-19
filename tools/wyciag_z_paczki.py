#!/usr/bin/env python3
"""Wyciąga elementy z pustym `PL:` z rozpakowanej paczki tłumacza do JSONL.

    python3 tools/wyciag_z_paczki.py --paczka dist/paczka_wwm_v5 --tabela building_exchange_group_config
    python3 tools/wyciag_z_paczki.py --paczka dist/paczka_wwm_v5 --prefiks manual_
Zwraca jeden wiersz JSON: {"klucz","zh","en","tabela","pole","wiersz"}.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--paczka", required=True, help="katalog rozpakowanej paczki (z podkatalogami sceny/cutsceny/widoki)")
    ap.add_argument("--tabela", action="append", default=[])
    ap.add_argument("--prefiks", action="append", default=[])
    ap.add_argument("--zrodlo", default="widoki")
    args = ap.parse_args()

    wzorzec = re.compile(r"^\d+\. \[([^\]]+)\] (.*)$")
    braki = []
    for plik in sorted(Path(args.paczka, args.zrodlo).glob("*.md")):
        lines = plik.read_text(encoding="utf-8").splitlines()
        i = 0
        biezacy = None
        while i < len(lines):
            line = lines[i]
            m = wzorzec.match(line)
            if m:
                czesci = m.group(1).split(" · ")
                tabelac = czesci[0] if czesci else ""
                pole = czesci[1] if len(czesci) > 1 else ""
                wiersz = czesci[2] if len(czesci) > 2 else ""
                biezacy = {"klucz": None, "zh": m.group(2), "tabela": tabelac, "pole": pole, "wiersz": wiersz}
            elif line.startswith("   klucz: ") and biezacy is not None:
                biezacy["klucz"] = line[len("   klucz: "):].strip()
            elif line.startswith("   EN: ") and biezacy is not None:
                biezacy["en"] = line[len("   EN: "):]
            elif line == "   PL:" and biezacy is not None:
                trafia = False
                if biezacy["tabela"] in args.tabela:
                    trafia = True
                for p in args.prefiks:
                    if biezacy["tabela"].startswith(p):
                        trafia = True
                if trafia:
                    biezacy.setdefault("en", "")
                    braki.append(biezacy)
                biezacy = None
            elif line == "   PL: " + "" and biezacy is not None:  # bezpieczeństwo
                pass
            i += 1
    json.dump(braki, sys.stdout, ensure_ascii=False, indent=0)
    print()
    wypisz_liczbe = len(braki)
    print(f"# wyciągnięto {wypisz_liczbe} elementów z pustym PL", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
