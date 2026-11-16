#!/usr/bin/env python3
"""Szukanie w bazie gry tabeli, która wiąże napis z cutsceną.

Po co: w wyciągu `index/` napis przerywnika ma tylko identyfikator wiersza
(`text_msg`) i nazwę nagrania — **nie ma numeru cutsceny**. Numer siedzi
w osi czasu cutsceny, a tej nie ma w tabelach objętych dotychczasowym wyciągiem.
Ten program przegląda **wszystkie** tabele bazy (`MANIFEST` + `index*` + `data*`)
i szuka takiej, w której jedna kolumna trzyma numery cutscen, a druga — wiersze
puli napisów (`text_msg`, 590000–592694). Jeśli ją znajdzie, zapisuje wiązanie
do `index/cutsceny_napisy.jsonl`; wtedy `tools/chronologia.py` kładzie każdy
napis w jego własnej cutscenie.

Dwa tryby:

1. **same schematy** (gdy w katalogu jest `MANIFEST` i `index*`, ale nie ma
   `data*`) — program wypisuje tabele i ich kolumny, które wyglądają na
   wiązanie napisów z cutscenami. Nic nie czyta z `data*`, więc nie potrzebuje
   tekstu gry; do tego służy `collector/spakuj_dane.ps1 -Zakres schematy`.
2. **pełny** (z `data*`) — program czyta wiersze podejrzanych tabel i sprawdza,
   czy wartości naprawdę są numerami cutscen i wierszami napisów. Dopiero wtedy
   zapisuje `index/cutsceny_napisy.jsonl`.

Użycie:
    python3 tools/cutsceny_z_bazy.py --katalog local/dane --raport out/schematy.json
    python3 tools/cutsceny_z_bazy.py --katalog local/dane --wyj index/cutsceny_napisy.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools import baza_gry  # noqa: E402

# Wiersze puli napisów przerywników w `text_msg` (patrz `index/cutsceny_kontekst.jsonl`).
PULA_NAPISOW = (590000, 592694)

# Po czym poznać kolumnę: nazwy z gry bywają mylące, więc zbieramy szeroko,
# a prawdę i tak sprawdza potem zawartość kolumny.
SLOWA_CUTSCENA = ("cutscene", "cut_scene", "cinematic", "timeline", "story_cut", "perform")
SLOWA_NAPIS = ("text_msg", "textmsg", "napis", "subtitle", "sub_title", "txt_id", "text_id",
               "content_id", "msg_id", "msgid", "dialog_text", "voice_text")


def _podejrzana(nazwa_tabeli: str, kolumny: list[str] | None) -> bool:
    if not kolumny:
        return False
    tekst = " ".join([nazwa_tabeli.lower(), *(k.lower() for k in kolumny)])
    ma_cut = any(slowo in tekst for slowo in SLOWA_CUTSCENA)
    ma_napis = any(slowo in tekst for slowo in SLOWA_NAPIS)
    return ma_cut and ma_napis


def _liczba(wartosc) -> int | None:
    if isinstance(wartosc, bool) or not isinstance(wartosc, int):
        return None
    return wartosc


def _kolumny_liczbowe(baza, nazwa: str, limit: int = 4000) -> dict[str, list[int]]:
    """Pierwsze `limit` wierszy tabeli: kolumna → wartości liczbowe."""
    zebrane: dict[str, list[int]] = {}
    for _, wiersz in baza.wiersze(nazwa):
        if not isinstance(wiersz, dict):
            continue
        for kolumna, wartosc in wiersz.items():
            liczba = _liczba(wartosc)
            if liczba is not None:
                zebrane.setdefault(kolumna, []).append(liczba)
            elif isinstance(wartosc, list):
                for element in wartosc:
                    liczba = _liczba(element)
                    if liczba is not None:
                        zebrane.setdefault(kolumna, []).append(liczba)
        if len(next(iter(zebrane.values()), [])) >= limit:
            break
    return zebrane


def _wiazanie(kolumny: dict[str, list[int]], cutsceny: set[int],
              napisy: set[int], min_pokrycie: float) -> tuple[str, str] | None:
    """(kolumna cutscen, kolumna napisów) — gdy obie kolumny zgadzają się z danymi."""
    def udzial(wartosci: list[int], zbior: set[int], zakres: tuple[int, int] | None = None) -> float:
        if not wartosci:
            return 0.0
        if zbior:
            trafione = sum(1 for w in wartosci if w in zbior)
        else:
            trafione = sum(1 for w in wartosci if zakres[0] <= w <= zakres[1])
        return trafione / len(wartosci)

    najlepsze = None
    for kol_cut, wart_cut in kolumny.items():
        udzial_cut = udzial(wart_cut, cutsceny)
        if udzial_cut < min_pokrycie:
            continue
        for kol_napis, wart_napis in kolumny.items():
            if kol_napis == kol_cut:
                continue
            udzial_napis = udzial(wart_napis, napisy, PULA_NAPISOW) if not napisy else udzial(wart_napis, napisy)
            if udzial_napis < min_pokrycie:
                continue
            wynik = (kol_cut, kol_napis)
            if najlepsze is None or udzial_cut + udzial_napis > najlepsze[0]:
                najlepsze = (udzial_cut + udzial_napis, wynik)
    return najlepsze[1] if najlepsze else None


def _zbierz_wiazanie(baza, nazwa: str, kol_cut: str, kol_napis: str,
                     cutsceny: set[int], napisy: set[int]) -> dict[int, list[int]]:
    mapa: dict[int, list[int]] = {}
    for _, wiersz in baza.wiersze(nazwa):
        if not isinstance(wiersz, dict):
            continue
        cut = _liczba(wiersz.get(kol_cut))
        napis = _liczba(wiersz.get(kol_napis))
        if cut is None or napis is None:
            continue
        if cutsceny and cut not in cutsceny:
            continue
        if napisy:
            if napis not in napisy:
                continue
        elif not (PULA_NAPISOW[0] <= napis <= PULA_NAPISOW[1]):
            continue
        mapa.setdefault(cut, []).append(napis)
    return mapa


def _wczytaj_odniesienia(index: Path) -> tuple[set[int], set[int]]:
    """Numery cutscen i wiersze puli napisów z wyciągu w `index/`."""
    cutsceny: set[int] = set()
    napisy: set[int] = set()
    plik = index / "przerywniki.jsonl"
    if plik.exists():
        with plik.open(encoding="utf-8") as f:
            for linia in f:
                if linia.strip():
                    cutsceny.add(int(json.loads(linia)["no"]))
    plik = index / "cutsceny_kontekst.jsonl"
    if plik.exists():
        with plik.open(encoding="utf-8") as f:
            for linia in f:
                if not linia.strip():
                    continue
                wiersz = json.loads(linia)
                if wiersz.get("typ") == "napis" and wiersz.get("wiersz"):
                    napisy.add(int(wiersz["wiersz"]))
    return cutsceny, napisy


def szukaj(katalog: list[Path], index: Path, *, min_pokrycie: float = 0.9,
           tylko_schematy: bool = False, postep=None) -> dict:
    baza = baza_gry.Baza([str(k) for k in katalog])
    cutsceny, napisy = _wczytaj_odniesienia(index)

    podejrzane: list[tuple[str, list[str]]] = []
    for nazwa in sorted(baza.tabele):
        kolumny = baza.kolumny(nazwa)
        if _podejrzana(nazwa, kolumny):
            podejrzane.append((nazwa, kolumny or []))
    wynik = {
        "tabel": len(baza.tabele),
        "podejrzanych": [n for n, _ in podejrzane],
        "znalezione": None,
        "wiazania": {},
        "tryb": "schematy" if tylko_schematy else "pelny",
    }
    if postep:
        postep(f"tabel: {len(baza.tabele)}, podejrzanych: {len(podejrzane)}")

    if tylko_schematy:
        wynik["kolumny"] = {n: k for n, k in podejrzane}
        return wynik

    plik_napisow = baza.pliki.get("data1")
    if plik_napisow is None and not any(p.name.startswith("data") for p in baza.pliki.values()):
        wynik["blad"] = "brak plików data* — dostępne są tylko schematy"
        wynik["kolumny"] = {n: k for n, k in podejrzane}
        return wynik

    for nazwa, _ in podejrzane:
        try:
            kolumny = _kolumny_liczbowe(baza, nazwa)
        except baza_gry.BazaError as blad:          # tabela nieczytelna: pomiń, nie przerywaj
            wynik["wiazania"][nazwa] = {"blad": str(blad)}
            continue
        para = _wiazanie(kolumny, cutsceny, napisy, min_pokrycie)
        if para is None:
            continue
        mapa = _zbierz_wiazanie(baza, nazwa, para[0], para[1], cutsceny, napisy)
        if not mapa:
            continue
        wynik["znalezione"] = {"tabela": nazwa, "cutscena": para[0], "napis": para[1]}
        wynik["wiazania"] = {str(cut): wartosci for cut, wartosci in sorted(mapa.items())}
        if postep:
            postep(f"wiązanie w {nazwa}: {len(mapa)} cutscen")
        break
    return wynik


def zapisz(wynik: dict, wyj: Path, index: Path) -> int:
    """Zapisz wiązanie cutscena → wiersze napisów (JSONL, po jednym wierszu)."""
    mapa = wynik.get("wiazania") or {}
    if not isinstance(mapa, dict) or not mapa:
        return 0
    klucze: dict[int, str] = {}
    plik = index / "cutsceny_kontekst.jsonl"
    if plik.exists():
        with plik.open(encoding="utf-8") as f:
            for linia in f:
                if not linia.strip():
                    continue
                wiersz = json.loads(linia)
                if wiersz.get("typ") == "napis" and wiersz.get("wiersz"):
                    klucze[int(wiersz["wiersz"])] = wiersz["k"]
    wyj.parent.mkdir(parents=True, exist_ok=True)
    zapisane = 0
    with wyj.open("w", encoding="utf-8") as f:
        for cut, wiersze in sorted(mapa.items()):
            if not isinstance(wiersze, list) or not str(cut).isdigit():
                continue
            for numer in sorted(wiersze):
                klucz = klucze.get(int(numer))
                if not klucz:
                    continue
                f.write(json.dumps({"no": int(cut), "wiersz": int(numer), "k": klucz},
                                   ensure_ascii=False, separators=(",", ":")) + "\n")
                zapisane += 1
    return zapisane


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--katalog", action="append", required=True,
                    help="katalog z MANIFEST, index* i (opcjonalnie) data*; można podać kilka")
    ap.add_argument("--index", default="index", help="wyciąg z gry (numery cutscen i wiersze napisów)")
    ap.add_argument("--wyj", default="index/cutsceny_napisy.jsonl")
    ap.add_argument("--raport", help="zapisz raport (JSON) z tabelami i kolumnami")
    ap.add_argument("--tylko-schematy", action="store_true",
                    help="nie czytaj data* — wypisz same tabele i kolumny")
    ap.add_argument("--min-pokrycie", type=float, default=0.9, dest="min_pokrycie")
    a = ap.parse_args(argv)

    wynik = szukaj([Path(k) for k in a.katalog], Path(a.index),
                   min_pokrycie=a.min_pokrycie, tylko_schematy=a.tylko_schematy,
                   postep=lambda tekst: print(tekst, file=sys.stderr))
    if a.raport:
        Path(a.raport).parent.mkdir(parents=True, exist_ok=True)
        Path(a.raport).write_text(json.dumps(wynik, ensure_ascii=False, indent=1), encoding="utf-8")
    zapisane = 0
    if wynik.get("znalezione"):
        zapisane = zapisz(wynik, Path(a.wyj), Path(a.index))
        wynik["zapisane"] = zapisane
    print(json.dumps({k: v for k, v in wynik.items() if k != "wiazania"},
                     ensure_ascii=False, indent=1))
    return 0 if (wynik.get("znalezione") or a.tylko_schematy or wynik.get("blad")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
