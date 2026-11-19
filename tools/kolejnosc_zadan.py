#!/usr/bin/env python3
"""Kolejność zadań w czytance — łańcuch gry zamiast alfabetu.

Sekcja „Zadania i wątki” w pliku 03 była sortowana po nazwie, więc rozdziały
i etapy mieszały się alfabetycznie. Tu liczy się to, co gra sama wie:

1. **Grupa zadań** (`index/grupy_zadan.jsonl`) ma `kolejnosc` — to rozdział
   wątku głównego albo osobna historia poboczna.
2. **W grupie** zadania idą łańcuchem `pre`/`post` (`tools/uklad_scen.py`,
   `porzadek_topologiczny`), a części rozdziału (`pian`) rosnąco.
3. Co nie ma grupy — to pojedyncze zadanie; takie lądują osobno, pogrupowane
   krainą w kolejności odwiedzania (`index/prowincje.json`).

Nazwa zadania to klucz przekładu (`zadania[].nazwa`), więc czytanka bierze ją
z `tlumaczenie/` tak samo jak dotąd — tu ustalamy tylko kolejność.
"""

from __future__ import annotations

from dataclasses import dataclass, field

try:
    from tools import uklad_scen
except ImportError:  # uruchomienie jako skrypt
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from tools import uklad_scen

WATEK_GLOWNY = uklad_scen.TYP_WATKU_GLOWNEGO
BEZ_KOLEJNOSCI = 10**6
PROG_LANCUCHA = 2  # grupa z tyloma zadaniami to już łańcuch, nie pojedyncze zadanie


@dataclass
class Blok:
    """Jedna część sekcji: wątek (grupa zadań) albo kraińska kupka pojedynczych."""

    tytul: str
    rodzaj: str  # "watek" | "poboczne"
    klucze: list[str] = field(default_factory=list)


def _nazwa(ix, pl: dict[str, str], klucz: str | None) -> str:
    if not klucz:
        return ""
    return pl.get(klucz) or ix.en(klucz) or ""


def _tytul_rozdzialu(ix, pl: dict[str, str], grupa: dict) -> str:
    """Tytuł rozdziału wątku głównego: „Rozdział pierwszy · Nieśmiertelni nie przypłyną”.

    Gra opisuje rozdział trzema tekstami: `numer_tytulu` („Chapter One”),
    `nazwa` („Heaven Has No Pier”) i `tytul` — nazwa melodii *cipai*
    („Across the Meadow”), pod którą rozdział występuje na ekranie rozdziałów.
    Czytelnikowi chronologię wyższego rzędu daje numer z nazwą; melodia
    zostaje jako ostateczny zapas, gdy obu brakuje.
    """
    numer = _nazwa(ix, pl, grupa.get("numer_tytulu"))
    nazwa = _nazwa(ix, pl, grupa.get("nazwa"))
    czlony = [czlon for czlon in (numer, nazwa) if czlon]
    return " · ".join(czlony) or _nazwa(ix, pl, grupa.get("tytul"))


def _tytul_lancucha(ix, pl: dict[str, str], numer: int, grupa: dict) -> str:
    tytul = _nazwa(ix, pl, grupa.get("nazwa")) or _nazwa(ix, pl, grupa.get("tytul"))
    return tytul or f"grupa {numer}"


def _krainy_map(krainy: list[dict]) -> tuple[dict[int, tuple[int, str]], list[str]]:
    """Mapa numer mapy → (kolejność krainy, nazwa) i lista krain w kolejności."""
    mapa: dict[int, tuple[int, str]] = {}
    kolejnosc: list[str] = []
    for wpis in sorted(krainy, key=lambda k: (k.get("kolejnosc", BEZ_KOLEJNOSCI), str(k.get("kraina")))):
        nazwa = str(wpis.get("kraina") or "")
        if nazwa and nazwa not in kolejnosc:
            kolejnosc.append(nazwa)
        for numer in wpis.get("mapy") or ():
            mapa.setdefault(int(numer), (wpis.get("kolejnosc", BEZ_KOLEJNOSCI), nazwa))
    return mapa, kolejnosc


def _typ_klucz(ix) -> dict:
    kolejnosc = {}
    for numer, typ in getattr(ix, "typy_zadan", {}).items():
        kolejnosc[numer] = typ.get("kolejnosc", 99)
    return kolejnosc


def plan(ix, pl: dict[str, str], krainy: list[dict] | None = None) -> list[Blok]:
    """Bloki zadań w kolejności czytania.

    Kolejność bierze się z `tools/uklad_scen.py` — tego samego układu, który
    dostaje pakiet dla tłumacza: typ zadania (wątek główny pierwszy), grupa
    rozdziału po `kolejnosc`, a w grupie łańcuch `pre`/`post`.

    Bloki: po jednym na rozdział wątku głównego („Wątek główny — Rozdział
    pierwszy · …”), po jednym na łańcuch poboczny („Wątek poboczny — <nazwa>”),
    a na końcu pojedyncze zadania pogrupowane krainą w kolejności odwiedzania.
    """
    uklad = uklad_scen.uloz(ix)
    mapa_krain, kolejnosc_krain = _krainy_map(krainy or [])

    glowne: list[Blok] = []
    bez_rozdzialu: list[str] = []
    poboczne: list[Blok] = []
    pojedyncze: dict[str, list[tuple]] = {}
    uzyte: set[str] = set()

    for sekcja in uklad.sekcje:
        zadania = [z for z in sekcja.zadania if z in ix.zadania]
        if not zadania:
            continue
        klucze = []
        for zadanie in zadania:
            klucz = ix.zadania[zadanie].get("nazwa")
            if klucz and klucz not in klucze:
                klucze.append(klucz)
        if not klucze:
            continue
        grupa = ix.grupy.get(sekcja.grupa) if sekcja.grupa is not None else None
        if sekcja.typ == WATEK_GLOWNY:
            nowe = [k for k in klucze if k not in uzyte]
            uzyte.update(nowe)
            if not nowe:
                continue
            tytul = _tytul_rozdzialu(ix, pl, grupa) if grupa else ""
            if tytul:
                glowne.append(Blok(f"Wątek główny — {tytul}", "watek", nowe))
            else:
                bez_rozdzialu += nowe
            continue
        if sekcja.grupa is not None and len(zadania) >= PROG_LANCUCHA:
            nowe = [k for k in klucze if k not in uzyte]
            uzyte.update(nowe)
            if not nowe:
                continue
            tytul = _tytul_lancucha(ix, pl, sekcja.grupa, grupa or {})
            poboczne.append(Blok(f"Wątek poboczny — {tytul}", "watek", nowe))
            continue
        # pojedyncze zadanie: krainą rządzi przestrzeń zadania
        for numer, klucz in zip(zadania, klucze):
            if klucz in uzyte:
                continue
            uzyte.add(klucz)
            przestrzen = ix.zadania[numer].get("przestrzen")
            w_krainie = mapa_krain.get(int(przestrzen)) if przestrzen is not None else None
            nazwa_krainy = w_krainie[1] if w_krainie else "bez mapy"
            pozycja = (w_krainie[0] if w_krainie else BEZ_KOLEJNOSCI, int(numer))
            pojedyncze.setdefault(nazwa_krainy, []).append((pozycja, klucz))

    bloki: list[Blok] = list(glowne)
    if bez_rozdzialu:
        bloki.append(Blok("Wątek główny — zadania bez rozdziału", "watek", bez_rozdzialu))
    bloki += poboczne
    kolejnosc_pojedynczych = [k for k in kolejnosc_krain if k in pojedyncze]
    kolejnosc_pojedynczych += sorted(k for k in pojedyncze if k not in kolejnosc_pojedynczych)
    for kraina in kolejnosc_pojedynczych:
        klucze = []
        for _, klucz in sorted(pojedyncze[kraina]):
            if klucz not in klucze:
                klucze.append(klucz)
        bloki.append(Blok(f"Zadania pojedyncze — {kraina}", "poboczne", klucze))
    return bloki


def main(argv: list[str] | None = None) -> int:
    import argparse
    import json
    from pathlib import Path

    from tools import indeks as indeks_mod
    from tools import tlumaczenie as tlumaczenie_mod

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--index", default="index")
    parser.add_argument("--magazyn", default="tlumaczenie")
    argumenty = parser.parse_args(argv)

    ix = indeks_mod.wczytaj(argumenty.index, teksty=True, sceny=False)
    magazyn = tlumaczenie_mod.wczytaj(
        argumenty.magazyn, warianty=Path(argumenty.index) / "warianty.jsonl"
    )
    pl = magazyn.po_kluczu_pelny()
    krainy = json.loads((Path(argumenty.index) / "prowincje.json").read_text(encoding="utf-8"))
    for blok in plan(ix, pl, krainy):
        print(f"## {blok.tytul}  ({blok.rodzaj}, {len(blok.klucze)})")
        for klucz in blok.klucze[:3]:
            print("   ", _nazwa(ix, pl, klucz) or klucz)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
