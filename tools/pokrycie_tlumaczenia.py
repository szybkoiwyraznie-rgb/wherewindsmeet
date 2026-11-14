#!/usr/bin/env python3
"""Pokrycie przekładu: co w grze zostanie po angielsku (`index/` + `tlumaczenie/`).

Narzędzie **tylko czyta** repozytorium — nie potrzebuje plików gry, Dysku Google
ani `zstandard`. Odpowiada na pytanie „dlaczego ten napis jest jeszcze po
angielsku?” bez zgadywania i bez patrzenia na binarki:

    python3 tools/pokrycie_tlumaczenia.py
    python3 tools/pokrycie_tlumaczenia.py --brak
    python3 tools/pokrycie_tlumaczenia.py --szukaj "Winter Night"
    python3 tools/pokrycie_tlumaczenia.py --bez-scen --json

Sekcje odpowiadają temu, co realnie wyświetla klient gry:

- **napisy cutscen** — `text_msg` 590000–592694 (sekcja `cutsceny/01_…`),
- **intro** — `wds_oneday_intro_cutscene_data` (sekcja `cutsceny/02_…`),
- **napisy filmowe** — `entry_collect_movie_subtitle_data`, osobno dla każdego
  filmu (sekcja `cutsceny/02_…`); to napisy prerenderowanych przerywników,
- **sceny** — dialogi i plansze z timeline'ów (sekcje `sceny/`), czyli
  największa część wypowiadanego tekstu w grze,
- **wszystkie unikalne teksty wyciągu** — suma kontrolna pokrycia.

Klucz przekładu to SHA-256 tekstu źródłowego (`tools/mapa_tekstow.py`), więc
ten sam tekst w mapie, w cutscenie i w scenie dzieli jeden wpis magazynu:
tłumaczenie w jednym miejscu działa we wszystkich. Brak przekładu w tabeli
oznacza, że dany wiersz zostanie w kliencie po angielsku.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

try:
    from tools import indeks as indeks_mod
    from tools import tlumaczenie as magazyn_mod
    from tools import wypisz
except ImportError:  # uruchomienie jako skrypt
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from tools import indeks as indeks_mod
    from tools import tlumaczenie as magazyn_mod
    from tools import wypisz

TYPY_KINOWE = ("napis", "intro", "film")
OPIS_TYPU = {
    "napis": "napisy cutscen (text_msg 590000–592694)",
    "intro": "intro (wds_oneday_intro_cutscene_data)",
    "film": "napisy filmowe (entry_collect_movie_subtitle_data)",
}


def slot_elementu(element: list) -> str:
    """Slot przekładu dla elementu sceny: `@id` (wariant płci) albo klucz tekstu."""
    if len(element) > 4 and element[3]:
        return "@" + element[4]
    return element[2]


def _procent(czesc: int, calosc: int) -> float:
    return round(100.0 * czesc / calosc, 1) if calosc else 0.0


def sekcje(ix: indeks_mod.Indeks, magazyn: magazyn_mod.Magazyn, *, sceny: bool = True) -> list[dict]:
    """Pokrycie przekładu w podziale na sekcje widoczne w grze."""
    wynik: list[dict] = []

    def dodaj(nazwa: str, sloty) -> None:
        sloty = list(sloty)
        z_przekladem = sum(1 for slot in sloty if magazyn.przeklad(slot))
        wynik.append(
            {
                "sekcja": nazwa,
                "elementy": len(sloty),
                "przetlumaczone": z_przekladem,
                "braki": len(sloty) - z_przekladem,
                "procent": _procent(z_przekladem, len(sloty)),
            }
        )

    for typ in TYPY_KINOWE:
        dodaj(OPIS_TYPU[typ], (row.get("k") for row in ix.cutsceny_kontekst.get(typ, ()) if row.get("k")))

    wedlug_filmow: dict[object, list[str]] = {}
    for row in ix.cutsceny_kontekst.get("film", ()):
        if row.get("k"):
            wedlug_filmow.setdefault(row.get("film"), []).append(row["k"])
    for numer in sorted(wedlug_filmow, key=lambda value: (str(type(value)), str(value))):
        dodaj(f"  film {numer}", wedlug_filmow[numer])

    if sceny:
        dodaj(
            "sceny — dialogi i plansze z timeline'ów",
            (slot_elementu(element) for scena in ix.sceny.values() for element in scena.get("e", ())),
        )

    dodaj("wszystkie unikalne teksty wyciągu", ix.teksty.keys())
    return wynik


def braki_kinowe(ix: indeks_mod.Indeks, magazyn: magazyn_mod.Magazyn, typy=TYPY_KINOWE) -> list[dict]:
    """Wiersze napisów cutscen, intro i filmów bez przekładu w magazynie."""
    wynik: list[dict] = []
    for typ in typy:
        for row in ix.cutsceny_kontekst.get(typ, ()):
            klucz = row.get("k")
            if not klucz or klucz not in ix.teksty or magazyn.przeklad(klucz):
                continue
            tekst = ix.teksty[klucz]
            wpis = {
                "typ": typ,
                "klucz": klucz,
                "en": ix.en(klucz),
                "zh": None if tekst.z_en else tekst.zrodlo,
                "zrodlo": list(ix.zrodlo(tekst) or ()),
            }
            for pole in ("wiersz", "film", "id", "czas", "czas_konca", "mowca_en", "audio"):
                if pole in row:
                    wpis[pole] = row[pole]
            wynik.append(wpis)
    wynik.sort(key=lambda item: (TYPY_KINOWE.index(item["typ"]), item.get("film") or 0, item.get("wiersz") or 0, item.get("id") or 0))
    return wynik


def serie(rows: list[dict], *, pole: str, odstep: int = 1) -> list[list[dict]]:
    """Podziel posortowane wiersze na ciągłe serie (np. kolejne numery `text_msg`)."""
    serie_wynik: list[list[dict]] = []
    biezaca: list[dict] = []
    poprzednia: object = None
    for row in rows:
        numer = row.get(pole)
        if biezaca and isinstance(numer, int) and isinstance(poprzednia, int) and numer - poprzednia > odstep:
            serie_wynik.append(biezaca)
            biezaca = []
        biezaca.append(row)
        poprzednia = numer if isinstance(numer, int) else None
    if biezaca:
        serie_wynik.append(biezaca)
    return serie_wynik


def mapa_scen(ix: indeks_mod.Indeks) -> dict[str, int]:
    """Klucz tekstu -> numer pierwszej sceny, w której występuje."""
    mapa: dict[str, int] = {}
    for numer, scena in ix.sceny.items():
        for element in scena.get("e", ()):
            klucz = slot_elementu(element)
            mapa.setdefault(klucz, numer)
    return mapa


def szukaj(
    ix: indeks_mod.Indeks,
    magazyn: magazyn_mod.Magazyn,
    fraza: str,
    *,
    limit: int = 20,
    sceny: dict[str, int] | None = None,
) -> list[dict]:
    """Znajdź tekst po angielskim, chińskim albo polskim fragmencie (bez rozróżniania wielkości liter)."""
    igla = fraza.strip().casefold()
    if not igla:
        raise ValueError("pusta fraza")
    gdzie: dict[str, list[str]] = {}
    for typ in TYPY_KINOWE:
        for row in ix.cutsceny_kontekst.get(typ, ()):
            klucz = row.get("k")
            if not klucz:
                continue
            etykieta = f"{typ} {row['wiersz']}" if typ == "napis" else (f"film {row.get('film')} id {row.get('id')}" if typ == "film" else f"intro id {row.get('id')}")
            gdzie.setdefault(klucz, []).append(etykieta)

    wynik: list[dict] = []
    for klucz, tekst in ix.teksty.items():
        pl = magazyn.przeklad(klucz) or ""
        if igla not in tekst.zrodlo.casefold() and igla not in (tekst.en or "").casefold() and igla not in pl.casefold():
            continue
        wpis = {
            "klucz": klucz,
            "zh": None if tekst.z_en else tekst.zrodlo,
            "en": tekst.en,
            "pl": pl or None,
            "zrodlo": list(ix.zrodlo(tekst) or ()),
            "gdzie": gdzie.get(klucz, []),
        }
        if sceny and klucz in sceny:
            wpis["scena"] = sceny[klucz]
        wynik.append(wpis)
    wynik.sort(
        key=lambda item: (
            0 if igla in ((item["en"] or "").casefold(), (item["zh"] or "").casefold(), (item["pl"] or "").casefold()) else 1,
            len(item["en"] or item["zh"] or ""),
            item["klucz"],
        )
    )
    return wynik[:limit]


def _liczba(value: int) -> str:
    return f"{value:,}".replace(",", " ")


def _tekst_na_jedna_linie(text: str | None) -> str:
    """Wielolinijkowy tekst mapy w jednej linii raportu."""
    return " / ".join((text or "").split("\n"))


def _skroc(text: str | None, limit: int = 160) -> str:
    """Skróć długi tekst do czytelnej długości (pełny tekst: `--pelny`)."""
    jedna = _tekst_na_jedna_linie(text)
    return jedna if len(jedna) <= limit else jedna[: limit - 1].rstrip() + "…"


def _wypisz_podsumowanie(rows: list[dict], magazyn: magazyn_mod.Magazyn) -> None:
    print("POKRYCIE PRZEKŁADU (index/ + tlumaczenie/, bez plików gry)")
    print(f"Magazyn: {_liczba(len(magazyn))} przekładów ({_liczba(len(magazyn.po_kluczu))} po kluczu + {_liczba(len(magazyn.po_id))} warianty płci)")
    print()
    print(f"{'sekcja':<56}{'wpisów':>9}{'PL':>9}{'braki':>9}{'%':>7}")
    print("-" * 90)
    for row in rows:
        print(
            f"{row['sekcja']:<56}{_liczba(row['elementy']):>9}{_liczba(row['przetlumaczone']):>9}"
            f"{_liczba(row['braki']):>9}{row['procent']:>6}%"
        )
    print("-" * 90)
    print("Przekład przypisany jest do klucza tekstu źródłowego, więc jeden wpis obejmuje")
    print("wszystkie identyfikatory o tym samym tekście — w mapie, w cutscenie i w scenach.")


def _wypisz_braki(rows: list[dict]) -> None:
    if not rows:
        print("Brak braków: wszystkie napisy cutscen, intro i filmów mają przekład.")
        return
    print(f"NAJPISY BEZ PRZEKŁADU: {_liczba(len(rows))} wierszy (w grze zostaną po angielsku)")
    print()
    for typ in TYPY_KINOWE:
        wybrane = [row for row in rows if row["typ"] == typ]
        if not wybrane:
            continue
        print(f"== {OPIS_TYPU[typ]} — {_liczba(len(wybrane))} braków")
        grupy = serie(wybrane, pole="film" if typ != "napis" else "wiersz", odstep=0 if typ != "napis" else 1)
        for grupa in grupy:
            if typ == "film":
                numery = {row.get("film") for row in grupa}
                print(f"-- film {', '.join(str(n) for n in sorted(numery, key=str))}: {_liczba(len(grupa))} wierszy bez przekładu")
            elif typ == "napis":
                pierwszy, ostatni = grupa[0].get("wiersz"), grupa[-1].get("wiersz")
                zakres = f"{pierwszy}" if pierwszy == ostatni else f"{pierwszy}–{ostatni}"
                print(f"-- text_msg {zakres}: {_liczba(len(grupa))} wierszy bez przekładu")
            for row in grupa:
                en = _tekst_na_jedna_linie(row.get("en"))
                print(f"   [{row.get('wiersz') or row.get('id')}] {en}")
        print()


def _wypisz_szukanie(fraza: str, rows: list[dict], *, pelny: bool = False) -> None:
    if not rows:
        print(f"Nie znaleziono tekstu zawierającego: {fraza!r}")
        return
    print(f"TRAFIENIA DLA: {fraza!r} ({_liczba(len(rows))})")
    for row in rows:
        stan = "PL jest" if row["pl"] else "BRAK przekładu → w grze po angielsku"
        print(f"- klucz {row['klucz']}: {stan}")
        if row.get("gdzie"):
            print(f"   występuje: {', '.join(row['gdzie'])}")
        if row.get("scena") is not None:
            print(f"   scena: {row['scena']}")
        if row["zrodlo"]:
            print(f"   źródło: {' / '.join(str(part) for part in row['zrodlo'])}")
        pokaz = (lambda value: _tekst_na_jedna_linie(value)) if pelny else _skroc
        print(f"   ZH: {pokaz(row['zh'])}")
        print(f"   EN: {pokaz(row['en'])}")
        if row["pl"]:
            print(f"   PL: {pokaz(row['pl'])}")


def main(argv: list[str] | None = None) -> int:
    wypisz.utf8()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--indeks", default="index", help="katalog wyciągu (domyślnie index)")
    parser.add_argument("--magazyn", default="tlumaczenie", help="katalog magazynu przekładów (domyślnie tlumaczenie)")
    parser.add_argument("--brak", action="store_true", help="wypisz napisy cutscen, intro i filmów bez przekładu")
    parser.add_argument("--szukaj", help="znajdź tekst po fragmencie EN, ZH albo PL i pokaż, czy ma przekład")
    parser.add_argument("--bez-scen", action="store_true", help="pomiń sekcję scen (szybsze, bez wczytywania timeline'ów)")
    parser.add_argument("--pelny", action="store_true", help="przy `--szukaj` pokaż pełne teksty zamiast skróconych")
    parser.add_argument("--json", action="store_true", help="wynik jako JSON")
    arguments = parser.parse_args(argv)

    try:
        ix = indeks_mod.wczytaj(arguments.indeks, sceny=not arguments.bez_scen or bool(arguments.szukaj))
        magazyn = magazyn_mod.wczytaj(arguments.magazyn)
    except (indeks_mod.IndeksError, magazyn_mod.MagazynError, OSError) as error:
        print(json.dumps({"ok": False, "powod": str(error)}, ensure_ascii=False))
        return 1

    if arguments.szukaj:
        try:
            rows = szukaj(ix, magazyn, arguments.szukaj, sceny=mapa_scen(ix))
        except ValueError as error:
            print(json.dumps({"ok": False, "powod": str(error)}, ensure_ascii=False))
            return 2
        if arguments.json:
            print(json.dumps({"ok": True, "fraza": arguments.szukaj, "trafienia": rows}, ensure_ascii=False, indent=1))
        else:
            _wypisz_szukanie(arguments.szukaj, rows, pelny=arguments.pelny)
        return 0

    if arguments.brak:
        rows = braki_kinowe(ix, magazyn)
        if arguments.json:
            print(json.dumps({"ok": True, "braki": rows}, ensure_ascii=False, indent=1))
        else:
            _wypisz_braki(rows)
        return 0

    rows = sekcje(ix, magazyn, sceny=not arguments.bez_scen)
    if arguments.json:
        print(json.dumps({"ok": True, "magazyn": len(magazyn), "sekcje": rows}, ensure_ascii=False, indent=1))
    else:
        _wypisz_podsumowanie(rows, magazyn)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
