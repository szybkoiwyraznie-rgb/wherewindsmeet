#!/usr/bin/env python3
"""Chronologia Where Winds Meet — jedna, stała lista jednostek zapisana w repo.

Po co to jest: kolejność scen i cutscen w grze ma być **raz ustalona i zapisana
w repozytorium**, żeby czytanki i łatki nie układały jej od nowa w każdej sesji
i żeby nie zależały od niczego spoza gita.

Wejście (wszystko z repo): `index/` (wyciąg z gry), `index/prowincje.json`
(kolejność krain), `zwrotki/prolog_transkrypt_z_gry.txt` (transkrypt właściciela,
zapisany w repo). Wyjście: `index/chronologia.jsonl` — po jednej jednostce
w wierszu, w kolejności występowania w grze:

    {"p": 0, "t": "film", "n": 1, "s": "Pieśni"}
    {"p": 1, "t": "prolog", "s": "Prolog", "e": "Pierwsza cutscena", "k": [...]}
    {"p": 2, "t": "cutscena", "n": 30033, "s": "燕南", "k": ["..."]}
    {"p": 3, "t": "scena", "n": 10094, "s": "燕南"}

Zasady kolejności (te same, co w ustaleniach):

1. filmy i pieśni (1–3) — na końcu, bo w grze nie ma ich na początku,
2. prolog w kolejności transkryptu — napisy i dialogi przemieszane,
3. krainy w kolejności odwiedzania, w krainie sceny po numerze dialogu,
4. cutsceny **przypisane do grupy zadań** (tabela powtórek: `no` → `grupa`,
   a grupa ma zakres numerów dialogów) stoją przy scenie, od której ta grupa
   się zaczyna — dzięki temu przerywniki są przemieszane ze scenami, choć same
   nie mają numeru dialogu,
5. cutsceny bez grupy zadań stoją na końcu, w kolejności własnych numerów
   (sekcja „Cutsceny bez grupy zadań”) — nie udajemy, że znamy ich miejsce.

Ten plik jest generowany, ale commitowany: test `tests/test_chronologia.py`
pilnuje, żeby po zmianie danych wygenerować go ponownie (`--sprawdz`), a nie
zmieniać ręcznie.

Użycie:
    python3 tools/chronologia.py                       # zapisz index/chronologia.jsonl
    python3 tools/chronologia.py --sprawdz             # tylko porównaj z zapisanym
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools import indeks as indeks_mod  # noqa: E402
from tools import kolejnosc_gry, prolog_z_klucza  # noqa: E402

BEZ_MAPY = "Sceny bez przypisanej mapy"
BEZ_GRUPY = "Cutsceny bez grupy zadań"
DOMYSLNY_PLIK = Path("index") / "chronologia.jsonl"


def _kraina_scen(ix, krainy: list[dict]) -> tuple[dict[int, str], list[str]]:
    """Numer sceny → kraina oraz kolejność krain z gry."""
    mapa_kraina = {mapa: k["kraina"] for k in krainy for mapa in k["mapy"]}
    mapa_projektu: dict[str, dict[int, int]] = defaultdict(lambda: defaultdict(int))
    for scena in ix.sceny.values():
        projekt = str(scena.get("p") or "").split(".")[0]
        for mapa in scena.get("m") or []:
            mapa_projektu[projekt][mapa] += 1

    przypisanie: dict[int, str] = {}
    for numer, scena in ix.sceny.items():
        mapy = list(scena.get("m") or [])
        if not mapy:
            liczby = mapa_projektu.get(str(scena.get("p") or "").split(".")[0]) or {}
            if liczby:
                mapy = [max(liczby, key=liczby.get)]
        przypisanie[numer] = next((mapa_kraina[m] for m in mapy if m in mapa_kraina), BEZ_MAPY)
    kolejnosc = [k["kraina"] for k in krainy] + [BEZ_MAPY]
    return przypisanie, kolejnosc


def _prolog(index: str, magazyn: str) -> list[dict]:
    """Prolog w kolejności transkryptu: sekcje z nagłówków, w środku klucze tekstów."""
    _ix, po_pl, po_en = prolog_z_klucza._mapy(index, magazyn)
    porzadek: dict[str, list[dict]] = defaultdict(list)
    for wiersz in kolejnosc_gry.wczytaj(Path(index)):
        if wiersz.get("k"):
            porzadek[wiersz["k"]].append(wiersz)
    linie = Path(prolog_z_klucza.TRANSKRYPT).read_text(encoding="utf-8-sig").splitlines()

    jednostki: list[dict] = []
    numer = 0
    etykieta, klucze = "Prolog", []
    for rodzaj, tekst in prolog_z_klucza._przejscie(linie):
        if rodzaj == "#":
            if klucze:
                jednostki.append({"t": "prolog", "s": "Prolog", "e": etykieta, "k": klucze})
            numer += 1
            # nagłówki transkryptu to komentarze właściciela, nie nazwy scen —
            # w chronologii sekcje prologu są po prostu numerowane
            etykieta, klucze = f"Prolog {numer}", []
            continue
        klucz = prolog_z_klucza._dopasuj(tekst, po_pl, po_en, porzadek)
        if klucz and (not klucze or klucze[-1] != klucz):
            # dwie linie transkryptu mogą trafić w ten sam wariant tekstu —
            # wtedy w grze to jedna kwestia, nie dwie
            klucze.append(klucz)
    if klucze:
        if numer == 0:
            numer = 1
            etykieta = "Prolog 1"
        jednostki.append({"t": "prolog", "s": "Prolog", "e": etykieta, "k": klucze})
    return jednostki


def _cutsceny(ix) -> tuple[dict[int, list[dict]], list[dict]]:
    """Cutsceny rozdzielone na przypisane do grup zadań i pozostałe."""
    przerywniki = ix.przerywniki
    grupy = ix.grupy
    powtorki = ix.cutsceny_kontekst.get("powtorka") or []

    grupa_cutsceny: dict[int, list[dict]] = defaultdict(list)
    for wiersz in powtorki:
        grupa = wiersz.get("grupa")
        no = wiersz.get("no")
        if grupa in grupy and no in przerywniki:
            grupa_cutsceny[grupa].append(wiersz)
    for lista in grupa_cutsceny.values():
        lista.sort(key=lambda w: (str(w.get("rozdzial") or ""), w.get("no") or 0))

    przypisane: set[int] = set()
    jednostki_grup: dict[int, list[dict]] = defaultdict(list)
    for grupa, lista in sorted(grupa_cutsceny.items()):
        for wiersz in lista:
            no = wiersz["no"]
            if no in przypisane:
                continue
            przypisane.add(no)
            jednostki_grup[grupa].append(_jednostka_cutsceny(no, przerywniki[no], grupa))

    reszta: list[dict] = []
    for no in sorted(przerywniki):
        if no not in przypisane:
            jednostka = _jednostka_cutsceny(no, przerywniki[no], None)
            if jednostka.get("k"):
                reszta.append(jednostka)
    return jednostki_grup, reszta


def _jednostka_cutsceny(no: int, przerywnik: dict, grupa: int | None) -> dict:
    klucze = [przerywnik[k] for k in ("tekst", "streszczenie") if przerywnik.get(k)]
    jednostka = {"t": "cutscena", "n": no, "k": klucze}
    if grupa is not None:
        jednostka["g"] = grupa
    return jednostka


def _kotwice_grup(ix, sceny: list[int]) -> dict[int, int]:
    """Grupa zadań → numer sceny, przy której grupa się zaczyna (kotwica wstawienia)."""
    posortowane = sorted(sceny)
    kotwice: dict[int, int] = {}
    for grupa, dane in ix.grupy.items():
        start = dane.get("start")
        if not start:
            continue
        kotwica = next((numer for numer in posortowane if numer >= start), None)
        if kotwica is not None:
            kotwice[grupa] = kotwica
    return kotwice


def zbuduj(*, index: str = "index", magazyn: str = "tlumaczenie", wyj: Path = DOMYSLNY_PLIK) -> dict:
    ix = indeks_mod.wczytaj(index, teksty=True, sceny=True)
    krainy = json.loads((Path(index) / "prowincje.json").read_text(encoding="utf-8"))
    przypisanie, kolejnosc_krain = _kraina_scen(ix, krainy)

    jednostki: list[dict] = []

    filmy: set[int] = set()
    for wiersz in kolejnosc_gry.wczytaj(Path(index)):
        if wiersz.get("z") == "film" and wiersz.get("d") is not None:
            filmy.add(int(wiersz["d"]))

    jednostki.extend(_prolog(index, magazyn))

    sceny = sorted(numer for numer, scena in ix.sceny.items() if scena.get("e"))
    grupy_cutscen, cutsceny_bez_grupy = _cutsceny(ix)
    kotwice = _kotwice_grup(ix, sceny)
    przy_scenie: dict[int, list[dict]] = defaultdict(list)
    for grupa, lista in grupy_cutscen.items():
        kotwica = kotwice.get(grupa)
        if kotwica is None:
            cutsceny_bez_grupy.extend(lista)
            continue
        przy_scenie[kotwica].extend(lista)

    for kraina in kolejnosc_krain:
        for numer in (n for n in sceny if przypisanie.get(n) == kraina):
            for jednostka in przy_scenie.get(numer, ()):
                jednostki.append({**jednostka, "s": kraina})
            jednostki.append({"t": "scena", "n": numer, "s": kraina})

    cutsceny_bez_grupy.sort(key=lambda j: j["n"])
    for jednostka in cutsceny_bez_grupy:
        jednostki.append({**jednostka, "s": BEZ_GRUPY})

    # pieśni i filmy idą na koniec: w grze pojawiają się później, nie na starcie
    for numer in sorted(filmy):
        jednostki.append({"t": "film", "n": numer, "s": "Pieśni"})

    for pozycja, jednostka in enumerate(jednostki):
        jednostka["p"] = pozycja

    wyj.parent.mkdir(parents=True, exist_ok=True)
    tresc = "".join(json.dumps(j, ensure_ascii=False, separators=(",", ":")) + "\n"
                    for j in jednostki)
    wyj.write_text(tresc, encoding="utf-8")
    return {
        "jednostek": len(jednostki),
        "scen": sum(1 for j in jednostki if j["t"] == "scena"),
        "cutscen_przypisanych": sum(1 for j in jednostki
                                    if j["t"] == "cutscena" and j["s"] != BEZ_GRUPY),
        "cutscen_bez_grupy": sum(1 for j in jednostki
                                 if j["t"] == "cutscena" and j["s"] == BEZ_GRUPY),
        "prolog": sum(1 for j in jednostki if j["t"] == "prolog"),
        "filmow": sum(1 for j in jednostki if j["t"] == "film"),
        "bajtow": len(tresc.encode("utf-8")),
    }


def wczytaj(katalog: str | Path = "index") -> list[dict]:
    """Wczytaj zapisaną chronologię (bez przeliczania czegokolwiek)."""
    plik = Path(katalog) / "chronologia.jsonl"
    with plik.open(encoding="utf-8") as f:
        return [json.loads(linia) for linia in f if linia.strip()]


def sprawdz(*, index: str = "index", magazyn: str = "tlumaczenie") -> dict:
    """Czy zapisana chronologia zgadza się z danymi? (dla testów i CI)"""
    plik = Path(index) / "chronologia.jsonl"
    if not plik.exists():
        return {"ok": False, "blad": f"brak {plik}"}
    zapisana = plik.read_text(encoding="utf-8")
    tymczas = plik.with_suffix(".tmp")
    try:
        zbuduj(index=index, magazyn=magazyn, wyj=tymczas)
        nowa = tymczas.read_text(encoding="utf-8")
    finally:
        tymczas.unlink(missing_ok=True)
    return {
        "ok": zapisana == nowa,
        "linii_zapisanych": len([x for x in zapisana.splitlines() if x.strip()]),
        "linii_teraz": len([x for x in nowa.splitlines() if x.strip()]),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--index", default="index")
    ap.add_argument("--magazyn", default="tlumaczenie")
    ap.add_argument("--wyj", default=str(DOMYSLNY_PLIK))
    ap.add_argument("--sprawdz", action="store_true",
                    help="porównaj zapisaną chronologię z danymi, nic nie zapisuj")
    a = ap.parse_args(argv)
    if a.sprawdz:
        wynik = sprawdz(index=a.index, magazyn=a.magazyn)
        print(json.dumps(wynik, ensure_ascii=False, indent=1))
        return 0 if wynik.get("ok") else 1
    wynik = zbuduj(index=a.index, magazyn=a.magazyn, wyj=Path(a.wyj))
    print(json.dumps({"ok": True, "wyj": a.wyj, **wynik}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
