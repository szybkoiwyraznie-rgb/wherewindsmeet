#!/usr/bin/env python3
"""Scala następstwa scen/cutscen z obu skanów w jeden kanoniczny indeks.

Źródła (oba w repo):
  index/mpk/storyline_nastepstwa.jsonl — krawędzie z WYNIKv6 (skan goły,
    format {"z":{"t","n"},"do":{"t","n"},...}; t: "d" dialog, "c" cutscena),
  index/mpk/storyline_sceny.jsonl — grafy z przebiegu v7 (pole `nastepstwa`:
    [typ_a, nr_a, typ_b, nr_b]; typ: "scena"/"cutscena").

Wynik: index/mpk/nastepstwa_scen.jsonl — po jednym wierszu na unikalną
krawędź: {"z": [typ, nr], "do": [typ, nr], "zrodla": ["v6","v7"]}.
Typy ujednolicone do "scena"/"cutscena". Pętle własne (a→a) pomijane.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MPK = ROOT / "index" / "mpk"

TYP_V6 = {"d": "scena", "c": "cutscena"}


def main() -> int:
    krawedzie: dict[tuple, set[str]] = {}

    def dodaj(typ_a: str, a: int, typ_b: str, b: int, zrodlo: str) -> None:
        if (typ_a, a) == (typ_b, b):
            return
        krawedzie.setdefault((typ_a, a, typ_b, b), set()).add(zrodlo)

    plik_v6 = MPK / "storyline_nastepstwa.jsonl"
    if plik_v6.exists():
        with open(plik_v6, encoding="utf-8") as fh:
            for line in fh:
                d = json.loads(line)
                ta = TYP_V6.get(d["z"]["t"])
                tb = TYP_V6.get(d["do"]["t"])
                if ta and tb:
                    dodaj(ta, d["z"]["n"], tb, d["do"]["n"], "v6")

    with open(MPK / "storyline_sceny.jsonl", encoding="utf-8") as fh:
        for line in fh:
            d = json.loads(line)
            for ta, a, tb, b in d.get("nastepstwa", []):
                dodaj(ta, a, tb, b, "v7")

    out = MPK / "nastepstwa_scen.jsonl"
    with open(out, "w", encoding="utf-8") as fh:
        for (ta, a, tb, b) in sorted(krawedzie):
            fh.write(json.dumps({
                "z": [ta, a], "do": [tb, b],
                "zrodla": sorted(krawedzie[(ta, a, tb, b)]),
            }, ensure_ascii=False) + "\n")

    liczby = {"krawedzi": len(krawedzie)}
    for z in ("v6", "v7"):
        liczby[z] = sum(1 for s in krawedzie.values() if z in s)
    liczby["oba"] = sum(1 for s in krawedzie.values() if len(s) == 2)
    print(json.dumps({**liczby, "plik": str(out.relative_to(ROOT))}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
