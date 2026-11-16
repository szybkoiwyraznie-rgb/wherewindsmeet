#!/usr/bin/env python3
"""Prolog w kolejności z danych gry — podgląd do zatwierdzenia.

Składa transkrypt gracza (`zwrotki/prolog_transkrypt_z_gry.txt`, w repo)
z technicznym kluczem kolejności (`index/kolejnosc_*.jsonl`):

* każda linia dostaje numer techniczny (dialog + czas albo id w puli napisów),
* sceny idą w kolejności transkryptu (to szkielet, dopóki nie znajdziemy
  skryptu zadania prologu),
* sąsiednie warianty tej samej scenki trafiają do aneksu, nie do toku.

Wynik to plik markdown: kolumny „klucz techniczny / chiński / angielski / polski”.

Użycie:
    python3 tools/prolog_z_klucza.py --wyj zwrotki/prolog_wg_klucza.md
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools import indeks as indeks_mod  # noqa: E402
from tools import kolejnosc_gry  # noqa: E402

TRANSKRYPT = "zwrotki/prolog_transkrypt_z_gry.txt"


def _mapy(index: str, magazyn: str):
    ix = indeks_mod.wczytaj(index, teksty=True, sceny=False)
    po_en: dict[str, list[str]] = {}
    for k, t in ix.teksty.items():
        if t.en:
            po_en.setdefault(kolejnosc_gry._norm(t.en), []).append(k)
    po_pl: dict[str, list[str]] = {}
    for p in sorted(Path(magazyn).glob("pl_*.jsonl")):
        for line in p.open(encoding="utf-8"):
            d = json.loads(line)
            k = d.get("k") or d.get("klucz")
            if isinstance(d.get("pl"), str) and k:
                po_pl.setdefault(kolejnosc_gry._norm(d["pl"]), []).append(k)
    return ix, po_pl, po_en


# Ranga środka przy wyborze wariantu: napisy cutscen przed dialogami, bo
# ten sam tekst bywa i w puli napisów, i w krótkiej scenie dialogowej.
RANGA = {"napis": 0, "napis_grey": 0, "film": 1, "dialog": 2}


def _kandydaci(tekst: str, po_pl: dict[str, list[str]], po_en: dict[str, list[str]]) -> list[str]:
    igla = kolejnosc_gry._norm(tekst)
    wynik = list(po_pl.get(igla, ())) + list(po_en.get(igla, ()))
    if wynik:
        return wynik
    if len(igla) < 12:
        return []
    for mapa in (po_pl, po_en):
        for zrodlo, klucze in mapa.items():
            if zrodlo.startswith(igla[:24]):
                wynik.extend(klucze)
    if wynik:
        return wynik
    if len(igla) >= 16:
        for mapa in (po_pl, po_en):
            for zrodlo, klucze in mapa.items():
                if igla[:24] in zrodlo:
                    wynik.extend(klucze)
    return wynik


def _dopasuj(tekst: str, po_pl, po_en, porzadek: dict[str, list[dict]]) -> str | None:
    """Wybierz klucz najwcześniejszy w danych — to wariant główny."""
    kandydaci = [k for k in dict.fromkeys(_kandydaci(tekst, po_pl, po_en)) if k in porzadek]
    if not kandydaci:
        return None
    def pozycja(k: str):
        wyst = min(porzadek[k], key=lambda w: (RANGA.get(w["z"], 9), w["i"] or w["d"] or 0, w["t"] or 0))
        return (RANGA.get(wyst["z"], 9), wyst["i"] or wyst["d"] or 0, wyst["t"] or 0)
    return min(kandydaci, key=pozycja)


def _klucz_tekstu(w: dict) -> str:
    if w["z"] == "dialog":
        return f"dialog {w['d']} · t={w['t']} s · #{w['o']}"
    if w["z"] == "film":
        return f"film {w['d']} · t={w['t']} s"
    return f"napis {w['i']} ({w['z']})"


def _przejscie(linie: list[str]):
    """Zamienia transkrypt na strumień (rodzaj, tekst).

    `("#", tytuł)` to nagłówek sekcji, `("t", kwestia)` to linia do
    dopasowania w danych gry. Sklejanie zawiniętych linii dzieje się tutaj,
    żeby `zbuduj()` i `klucze()` czytały transkrypt identycznie.
    """
    poprzedni = ""
    for l in linie:
        l = l.rstrip()
        if not l.strip():
            continue
        if l.startswith("#"):
            poprzedni = l
            yield "#", l[1:].strip()
            continue
        if (poprzedni.startswith("*") and not l.startswith(("*", "#"))
                and not poprzedni.rstrip().endswith((".", "!", "?", "…", '"', ")"))):
            poprzedni = poprzedni + " " + l.strip()
            continue
        poprzedni = l
        yield "t", (l[1:].strip() if l.startswith("*") else l.strip())


def klucze(index: str = "index", magazyn: str = "tlumaczenie") -> set[str]:
    """Klucze tekstów, które wchodzą do prologu (do pominięcia w Czytance)."""
    _ix, po_pl, po_en = _mapy(index, magazyn)
    porzadek: dict[str, list[dict]] = {}
    for w in kolejnosc_gry.wczytaj(Path(index)):
        porzadek.setdefault(w["k"], []).append(w)
    linie = Path(TRANSKRYPT).read_text(encoding="utf-8-sig").splitlines()
    wynik: set[str] = set()
    for rodzaj, tekst in _przejscie(linie):
        if rodzaj != "t":
            continue
        k = _dopasuj(tekst, po_pl, po_en, porzadek)
        if k:
            wynik.add(k)
    return wynik


PROG_WYCZERPANIA = 0.8


def zasieg(index: str = "index", magazyn: str = "tlumaczenie") -> tuple[set[str], set[int]]:
    """Co prolog wyczerpuje: klucze i numery scen.

    Pierwszy element to najlepsze trafienia transkryptu (jedno na linię),
    drugi — numery dialogów, których co najmniej `PROG_WYCZERPANIA` linii
    pada w transkrypcie; takie sceny są już w prologu i nie powtarzamy ich
    w części „krainy”.
    """
    klucze_prologu = klucze(index, magazyn)
    _ix, po_pl, po_en = _mapy(index, magazyn)
    indeks = indeks_mod.wczytaj(index, teksty=False, sceny=True)
    porzadek: dict[str, list[dict]] = {}
    for w in kolejnosc_gry.wczytaj(Path(index)):
        porzadek.setdefault(w["k"], []).append(w)

    kandydaci: set[str] = set()
    linie = Path(TRANSKRYPT).read_text(encoding="utf-8-sig").splitlines()
    for rodzaj, tekst in _przejscie(linie):
        if rodzaj == "t":
            kandydaci.update(_kandydaci(tekst, po_pl, po_en))

    # Scenę znajdujemy dwiema drogami: przez timeline (`dialog N` w porządku gry)
    # i wprost po kluczach jej linii — prolog cytuje też wiersze puli napisów,
    # których żaden wiersz timeline nie wskazuje na dialog.
    sceny = {int(w["d"]) for k in kandydaci for w in porzadek.get(k, [])
             if w["z"] == "dialog" and w["d"]}
    for numer, scena in indeks.sceny.items():
        if any(e[0] == "k" and e[2] in kandydaci for e in scena.get("e") or []):
            sceny.add(numer)
    wyczerpane = set()
    for numer in sceny:
        scena = indeks.sceny.get(numer) or {}
        linie_sceny = [e[2] for e in scena.get("e") or [] if e[0] == "k"]
        if linie_sceny and sum(k in kandydaci for k in linie_sceny) / len(linie_sceny) >= PROG_WYCZERPANIA:
            wyczerpane.add(numer)
    return klucze_prologu, wyczerpane


def zbuduj(index: str = "index", magazyn: str = "tlumaczenie") -> str:
    ix, po_pl, po_en = _mapy(index, magazyn)
    porzadek: dict[str, list[dict]] = {}
    for w in kolejnosc_gry.wczytaj(Path(index)):
        porzadek.setdefault(w["k"], []).append(w)

    polski_po_kluczu: dict[str, str] = {}
    for p in sorted(Path(magazyn).glob("pl_*.jsonl")):
        for line in p.open(encoding="utf-8"):
            d = json.loads(line)
            k = d.get("k") or d.get("klucz")
            if k and isinstance(d.get("pl"), str):
                polski_po_kluczu.setdefault(k, d["pl"].strip())

    def opis(klucz: str) -> tuple[str, str, str, str, int | None, str]:
        t = ix.teksty[klucz]
        wyst = sorted(porzadek.get(klucz, []), key=lambda w: (RANGA.get(w["z"], 9), w["i"] or w["d"] or 0))
        if not wyst:
            return "brak w danych", t.zrodlo, t.en or "—", polski_po_kluczu.get(klucz, "—"), None, "?"
        w = wyst[0]
        return (
            _klucz_tekstu(w),
            t.zrodlo,
            (t.en or "—").replace("\n", " "),
            polski_po_kluczu.get(klucz, "—"),
            w["i"] if w["z"].startswith("napis") else None,
            w["z"],
        )

    linie = Path(TRANSKRYPT).read_text(encoding="utf-8-sig").splitlines()
    out: list[str] = [
        "# Prolog w kolejności z danych gry",
        "",
        "Kolumna „klucz techniczny” mówi, gdzie tekst leży w danych gry:",
        "`dialog N` — scena dialogowa (numer dialogu, czas i kolejność klucza",
        "w timeline), `napis N` — wiersz puli napisów cutsceny. Polskie linie",
        "pochodzą z magazynu tłumaczenia (`tlumaczenie/`).",
        "",
    ]
    scena: list[tuple[str, str, str, str, int | None, str]] = []

    def klucz_sortowania(wiersz) -> tuple:
        _t, _zh, _en, _pl, i, z = wiersz
        if z.startswith("napis"):
            return (0, i or 0, 0.0)
        if z == "dialog":
            numer = int(_t.split()[1]) if _t.split()[1].isdigit() else 0
            czas = float(_t.split("t=")[1].split()[0]) if "t=" in _t else 0.0
            return (1, numer, czas)
        return (9, 0, 0.0)

    def zamknij() -> None:
        if not scena:
            return
        out.append("| klucz techniczny | chiński | angielski | polski |")
        out.append("|---|---|---|---|")
        uporzadkowana, bez_klucza = [], []
        for wiersz in sorted(scena, key=klucz_sortowania):
            (bez_klucza if wiersz[5] == "?" else uporzadkowana).append(wiersz)
        ostatni = None
        for wiersz in uporzadkowana + bez_klucza:
            techniczny, zh, en, pl, _i, _z = wiersz
            if techniczny == ostatni and techniczny != "_(poza danymi)_":
                continue  # ta sama kwestia rozbita na dwie linie spisu
            ostatni = techniczny
            out.append(f"| {techniczny} | {zh} | {en} | {pl} |")
        out.append("")
        scena.clear()

    for rodzaj, tekst in _przejscie(linie):
        if rodzaj == "#":
            zamknij()
            out += [f"## {tekst}", ""]
            continue
        klucz = _dopasuj(tekst, po_pl, po_en, porzadek)
        if klucz is None:
            scena.append(("_(poza danymi)_", "—", tekst, "—", None, "?"))
        else:
            scena.append(opis(klucz))
    zamknij()

    # Aneks: warianty tej samej scenki otwierającej. W toku jest wariant
    # pierwszy w kolejności danych, resztę pokazujemy osobno.
    out += ["## Aneks: pozostałe warianty scenki otwierającej", ""]
    out.append("Te same kwestie w innych odgałęzieniach (nie wchodzą do toku):")
    out.append("")
    out.append("| id | chiński | angielski | polski |")
    out.append("|---|---|---|---|")
    po_id: dict[int, list[str]] = {}
    for k, t in ix.teksty.items():
        if isinstance(t.w, tuple) and len(t.w) > 1 and str(t.w[1]).isdigit():
            po_id.setdefault(int(t.w[1]), []).append(k)
    for lo, hi in ((590352, 590360), (591485, 591494)):
        for i in range(lo, hi + 1):
            for k in po_id.get(i, []):
                t = ix.teksty[k]
                out.append(
                    f"| {i} | {t.zrodlo} | {(t.en or '—').replace(chr(10), ' ')} "
                    f"| {polski_po_kluczu.get(k, '—')} |"
                )
    out.append("")
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--wyj", default="zwrotki/prolog_wg_klucza.md")
    ap.add_argument("--index", default="index")
    ap.add_argument("--magazyn", default="tlumaczenie")
    a = ap.parse_args(argv)
    tresc = zbuduj(a.index, a.magazyn)
    Path(a.wyj).parent.mkdir(parents=True, exist_ok=True)
    Path(a.wyj).write_text(tresc, encoding="utf-8")
    print(f"{a.wyj}: {tresc.count(chr(10))} linii")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
