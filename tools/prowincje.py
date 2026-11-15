#!/usr/bin/env python3
"""Kolejność krain (prowincji) w grze — z łańcucha zadań.

Gra nie ma jednej listy „najpierw ta mapa, potem tamta”. Da się ją jednak
odtworzyć z danych zadań: każde zadanie ma `przestrzen` (mapę), `pian`
(część rozdziału) oraz łańcuch `pre_task`/`post_task`. Kraina, której zadania
zaczynają się najwcześniej (najniższy `pian`, a przy remisie najniższy numer
zadania), jest odwiedzana pierwsza.

Nazwy map w grze powtarzają się w wariantach („燕南大地图” i
„任务重制_燕南大地图” to ta sama kraina, raz oryginalna, raz przerobiona),
dlatego mapy grupujemy po nazwie krainy: bierzemy początek nazwy do dwóch
znaków chińskich (燕南, 清河, 河西…) albo pierwszy człon nazwy łacińskiej.

Wynik: `index/prowincje.json` — lista krain w kolejności odwiedzania, każda
z numerami map. Ten plik jest wejściem dla `tools/buduj_czytanke_gry.py`.

Użycie:
    python3 tools/prowincje.py --index index --wyj index/prowincje.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools import indeks as indeks_mod  # noqa: E402

BEZ_PIANU = 10**9
_CN = re.compile(r"[\u3400-\u9fff]+")


def nazwa_krainy(nazwa: str | None, numer: int) -> str:
    """Nazwa krainy bez wariantów: „任务重制_燕南大地图” → „燕南”."""
    if not nazwa:
        return f"mapa {numer}"
    czysta = nazwa.replace("任务重制_", "").strip()
    trafienie = _CN.match(czysta)
    if trafienie:
        return trafienie.group()[:2]
    czlony = re.split(r"[_\-]", czysta)
    return czlony[0][:24] or f"mapa {numer}"


def zbierz(ix) -> list[dict]:
    """Krainy w kolejności odwiedzania wraz z mapami."""
    info: dict[int, dict] = {}
    for numer, zadanie in ix.zadania.items():
        mapa = zadanie.get("przestrzen")
        if mapa is None:
            continue
        rekord = info.setdefault(mapa, {"pian": BEZ_PIANU, "zadanie": 10**12, "zadan": 0})
        rekord["zadan"] += 1
        if zadanie.get("pian") is not None:
            rekord["pian"] = min(rekord["pian"], int(zadanie["pian"]))
        rekord["zadanie"] = min(rekord["zadanie"], int(numer))

    krainy: dict[str, dict] = {}
    for mapa, rekord in info.items():
        miejsce = ix.miejsca.get(mapa) or {}
        robocza = miejsce.get("robocza")
        klucz = nazwa_krainy(robocza, mapa)
        kraina = krainy.setdefault(
            klucz,
            {
                "kraina": klucz,
                "mapy": [],
                "pian": BEZ_PIANU,
                "zadanie": 10**12,
                "nazwy": set(),
            },
        )
        kraina["mapy"].append(mapa)
        kraina["pian"] = min(kraina["pian"], rekord["pian"])
        kraina["zadanie"] = min(kraina["zadanie"], rekord["zadanie"])
        if robocza:
            kraina["nazwy"].add(robocza)

    wynik = sorted(krainy.values(), key=lambda k: (k["pian"], k["zadanie"]))
    for indeks, kraina in enumerate(wynik):
        kraina["kolejnosc"] = indeks
        kraina["mapy"] = sorted(kraina["mapy"])
        kraina["nazwy"] = sorted(kraina["nazwy"])
    return wynik


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--index", default="index")
    ap.add_argument("--wyj", default="index/prowincje.json")
    a = ap.parse_args(argv)

    ix = indeks_mod.wczytaj(a.index, teksty=False, sceny=False)
    krainy = zbierz(ix)
    Path(a.wyj).write_text(json.dumps(krainy, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{a.wyj}: {len(krainy)} krain, map {sum(len(k['mapy']) for k in krainy)}")
    for k in krainy[:12]:
        print(f"  {k['kolejnosc']:>2} {k['kraina']:<8} pian={k['pian']:<5} mapy={len(k['mapy'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
