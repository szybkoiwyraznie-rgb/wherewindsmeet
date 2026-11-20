#!/usr/bin/env python3
"""Historyczna lista rundy 7: sceny zadań głównych z przestrzeniami 1, 501, 701.

UWAGA: przestrzeń przypisana do zadania nie dowodzi położenia ani wczesnego
czasu akcji sceny; wynik obejmuje późniejsze rozdziały i lokacje. Nie używać
bez osobnej selekcji do określania zakresu wczesnej gry.

Kolejność: numer zadania rosnąco, potem kolejność scen w `zadania_sceny`,
potem kolejność kwestii w scenie. Klucze już przetłumaczone są pomijane.

    python3 tools/lista_rundy7.py            # wypisuje klucze (jeden na linię)
    python3 tools/lista_rundy7.py --pelne     # klucz + ZH + EN
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools import indeks as indeks_mod
from tools import tlumaczenie

YANNAN = {1, 501, 701}


def klucz_bazowy(indeks, klucz: str) -> str:
    """Identyfikator wariantu (płeć bohatera) -> klucz tekstu bazowego."""
    wariant = indeks.warianty.get(klucz)
    return wariant["k"] if wariant else klucz


def klucze_sceny(indeks, numer):
    scena = indeks.sceny.get(numer)
    out: list[str] = []
    if not scena:
        return out
    for grupa in ("e", "o"):
        for element in scena.get(grupa) or []:
            if (
                isinstance(element, list)
                and element
                and isinstance(element[-1], str)
                and len(element[-1]) == 16
            ):
                out.append(element[-1])
    return out


def kolejnosc(indeks):
    """Klucze w kolejności fabularnej: zadanie numer, scena, kwestia."""
    wiersze = [
        json.loads(line)
        for line in Path("index/zadania_sceny.jsonl").open(encoding="utf-8")
        if line.strip()
    ]
    sceny_zadania: dict[int, list[int]] = {}
    for wiersz in wiersze:
        for rodzaj, numer, *_ in wiersz.get("zdarzenia") or []:
            if rodzaj == "scena":
                sceny_zadania.setdefault(wiersz["zadanie"], []).append(numer)
    zadania = sorted(
        (z for z in indeks.zadania.values() if z.get("typ") == 1 and z.get("przestrzen") in YANNAN),
        key=lambda z: z["no"],
    )
    widziane: set[str] = set()
    out: list[str] = []
    for zadanie in zadania:
        for numer in sceny_zadania.get(zadanie["no"], []):
            for klucz in klucze_sceny(indeks, numer):
                klucz = klucz_bazowy(indeks, klucz)
                if klucz not in widziane:
                    widziane.add(klucz)
                    out.append(klucz)
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pelne", action="store_true", help="dopisz tekst ZH i EN")
    parser.add_argument("--wszystkie", action="store_true", help="także już przetłumaczone")
    args = parser.parse_args(argv)
    print("UWAGA: historyczny filtr przestrzeni nie gwarantuje wczesnej gry ani prowincji sceny.", file=sys.stderr)
    indeks = indeks_mod.wczytaj("index", sceny=True)
    magazyn = tlumaczenie.wczytaj("tlumaczenie", warianty="index/warianty.jsonl")
    for klucz in kolejnosc(indeks):
        if not args.wszystkie and magazyn.ma(klucz):
            continue
        if not args.pelne:
            print(klucz)
            continue
        tekst = indeks.teksty.get(klucz)
        if not tekst:
            continue
        print(json.dumps(
            {"k": klucz, "zh": tekst.zrodlo, "en": tekst.en, "n": tekst.n},
            ensure_ascii=False,
        ))


if __name__ == "__main__":
    main()
