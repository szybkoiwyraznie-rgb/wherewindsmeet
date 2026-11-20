#!/usr/bin/env python3
"""Geografia jednolinijkowych kwestii wyzwalanych w świecie (pierwsza kraina).

Kwestie „wyzwalane ze świata” to brakujące teksty scen, które mają relację
`r` do `spaces.*.spawn_kit_dict#<kit>`, ale nie należą ani do kitów
ambientowych z `index/mpk/sceny_ambient_kity.jsonl`, ani do scen zadań.
Kit wskazany w relacji ma pozycję XYZ w tym samym pliku, więc taką kwestię
można przypisać do miejsca w świecie — i wybrać do tłumaczenia według
odległości od punktu startowego (kotwicy) albo klastra.

    python3 tools/barks_regiony.py                       # tabela pierścieni i klastrów
    python3 tools/barks_regiony.py --json
    python3 tools/barks_regiony.py --promien 800 --slotki dist/region_0800.txt
    python3 tools/barks_regiony.py --kotwica -1330 -109 --siatka 400

Kotwica domyślna to mediana pozycji kitów scen prologu (`chronologia.jsonl`,
wpisy `prolog`), czyli okolica startu gry. Narzędzie tylko czyta `index/`
i magazyn; nie potrzebuje plików gry. Odległość liczona w płaszczyźnie XZ.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import statistics
import sys
from pathlib import Path

try:
    from tools import indeks as indeks_mod
    from tools import tlumaczenie as magazyn_mod
    from tools import wypisz
except ImportError:  # uruchomienie jako skrypt
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from tools import indeks as indeks_mod
    from tools import tlumaczenie as magazyn_mod
    from tools import wypisz

RELACJA = re.compile(r"spaces\.(s\d+)\.([a-z_]+)#(\d+)")
PIERSCIENIE = (200, 400, 800, 1600, 3200, 6400)


class RegionyError(Exception):
    """Wejścia nie daje się odczytać albo nie ma danych o pozycjach."""


def _wiersze(sciezka: Path):
    with sciezka.open(encoding="utf-8") as uchwyt:
        for linia in uchwyt:
            if linia.strip():
                yield json.loads(linia)


def wczytaj_kity(katalog) -> tuple[dict[int, list[tuple[float, float, float]]], dict[int, list[tuple[float, float, float]]]]:
    """(kit_no -> pozycje XYZ, scena -> pozycje XYZ jej kitów)."""
    sciezka = Path(katalog) / "mpk" / "sceny_ambient_kity.jsonl"
    po_kicie: dict[int, list[tuple[float, float, float]]] = {}
    po_scenie: dict[int, list[tuple[float, float, float]]] = {}
    try:
        for wiersz in _wiersze(sciezka):
            punkt = wiersz.get("pozycja")
            if not (isinstance(punkt, list) and len(punkt) == 3 and all(isinstance(x, (int, float)) for x in punkt)):
                continue
            trojka = tuple(punkt)
            if isinstance(wiersz.get("kit_no"), int):
                po_kicie.setdefault(wiersz["kit_no"], []).append(trojka)
            if isinstance(wiersz.get("scena"), int):
                po_scenie.setdefault(wiersz["scena"], []).append(trojka)
    except (OSError, json.JSONDecodeError) as error:
        raise RegionyError(f"{sciezka}: {error}") from error
    return po_kicie, po_scenie


def wczytaj_zadania(katalog) -> dict[int, set[int]]:
    """scena -> zadania (puste, gdy pliku nie ma)."""
    sciezka = Path(katalog) / "zadania_sceny.jsonl"
    zadania: dict[int, set[int]] = {}
    try:
        for wiersz in _wiersze(sciezka):
            numer = wiersz.get("zadanie")
            for zdarzenie in wiersz.get("zdarzenia") or ():
                if isinstance(zdarzenie, (list, tuple)) and zdarzenie[0] == "scena" and numer is not None:
                    zadania.setdefault(zdarzenie[1], set()).add(numer)
    except (OSError, json.JSONDecodeError):
        pass
    return zadania


def kotwica_prologu(index, ix, kity_scen) -> tuple[float, float] | None:
    """Mediana XZ kitów scen prologu; None, gdy nie ma danych."""
    try:
        wiersze = _wiersze(Path(index) / "chronologia.jsonl")
    except (OSError, json.JSONDecodeError):
        return None
    po_kluczu: dict[str, set[int]] = {}
    for scena in ix.sceny.values():
        for element in scena.get("e", ()):
            po_kluczu.setdefault(element[2], set()).add(scena.get("d"))
    for wiersz in wiersze:
        if wiersz.get("t") != "prolog":
            continue
        sceny = {d for klucz in (wiersz.get("k") or ()) for d in po_kluczu.get(klucz, ()) }
        punkty = [punkt for d in sceny for punkt in kity_scen.get(d, ())]
        if punkty:
            return punkty[0][0], punkty[0][2]
    return None


def zbierz(index, magazyn, *, mapy: set[int] | None = None) -> tuple[dict[str, list[tuple[float, float]]], int]:
    """Zwraca (klucz -> pozycje XZ, liczba brakujących kluczy bez pozycji)."""
    ix = indeks_mod.wczytaj(index)
    kity, kity_scen = wczytaj_kity(index)
    zadania = wczytaj_zadania(index)
    if mapy is None:
        mapy = set()
        try:
            prowincje = json.loads((Path(index) / "prowincje.json").read_text(encoding="utf-8"))
            mapy = set(prowincje[0].get("mapy") or ())
        except (OSError, json.JSONDecodeError, IndexError) as error:
            raise RegionyError(f"brak prowincje.json ({error})") from error

    punkty: dict[str, list[tuple[float, float]]] = {}
    bez_pozycji: set[str] = set()
    for scena in ix.sceny.values():
        if not (set(scena.get("m") or ()) & mapy):
            continue
        klucze = []
        for element in scena.get("e", ()):
            slot = element[4] if len(element) > 4 and element[3] else element[2]
            klucz = slot[1:] if slot.startswith("@") else slot
            if klucz in ix.teksty and not magazyn.przeklad(klucz):
                klucze.append(klucz)
        if not klucze:
            continue
        if scena.get("d") in kity_scen or scena.get("d") in zadania:
            continue
        dopasowania = [
            dopasowanie
            for dopasowanie in (
                RELACJA.match(str(r[1])) for r in (scena.get("r") or ()) if isinstance(r, list) and len(r) > 1
            )
            if dopasowanie
        ]
        if not dopasowania:
            continue
        pozycje: list[tuple[float, float]] = []
        for dopasowanie in dopasowania:
            if dopasowanie.group(2) != "spawn_kit_dict":
                continue
            for punkt in kity.get(int(dopasowanie.group(3)), ()):
                pozycje.append((punkt[0], punkt[2]))
        for klucz in klucze:
            if pozycje:
                punkty.setdefault(klucz, []).extend(pozycje)
            else:
                bez_pozycji.add(klucz)
    return punkty, len(bez_pozycji - set(punkty))


def _odleglosci(punkty, kotwica) -> dict[str, float]:
    return {klucz: min(math.dist(p, kotwica) for p in lista) for klucz, lista in punkty.items()}


def raport(punkty, kotwica, *, siatka: int = 400, pierscienie=PIERSCIENIE) -> dict:
    """Pierścienie odległości od kotwicy i klastry siatki."""
    odleglosci = _odleglosci(punkty, kotwica)
    pierścienie_wynik = [
        {"do_m": promien, "klucze": sum(1 for wartosc in odleglosci.values() if wartosc <= promien)}
        for promien in sorted(pierscienie)
    ]
    klastry: dict[tuple[int, int], set[str]] = {}
    for klucz, lista in punkty.items():
        for punkt in lista:
            klastry.setdefault((round(punkt[0] / siatka) * siatka, round(punkt[1] / siatka) * siatka), set()).add(klucz)
    grupy = [
        {"x": x, "z": z, "klucze": len(klucze), "od_m": round(math.dist((x, z), kotwica))}
        for (x, z), klucze in klastry.items()
    ]
    grupy.sort(key=lambda row: (-row["klucze"], row["od_m"]))
    return {
        "format": "wwm-regiony-barks-v1",
        "kotwica_xz": [round(kotwica[0], 2), round(kotwica[1], 2)],
        "siatka_m": siatka,
        "z_pozycja": len(punkty),
        "pierścienie": pierścienie_wynik,
        "klastry": grupy,
    }


def klucze_w_promieniu(punkty, kotwica, promien: int) -> list[str]:
    """Klucze w promieniu, od najbliższego."""
    odleglosci = _odleglosci(punkty, kotwica)
    return [klucz for klucz, odleglosc in sorted(odleglosci.items(), key=lambda para: para[1]) if odleglosc <= promien]


def main(argv=None) -> int:
    wypisz.utf8()
    parser = argparse.ArgumentParser(description="Geografia kwestii wyzwalanych w świecie.")
    parser.add_argument("--indeks", default="index")
    parser.add_argument("--magazyn", default="tlumaczenie")
    parser.add_argument("--kraina", help="nazwa krainy z prowincje.json (domyślnie pierwsza)")
    parser.add_argument("--kotwica", nargs=2, type=float, metavar=("X", "Z"), help="punkt odniesienia (domyślnie prolog)")
    parser.add_argument("--siatka", type=int, default=400, help="bok klastra w metrach (domyślnie 400)")
    parser.add_argument("--promien", type=int, help="zapisz klucze w tym promieniu od kotwicy")
    parser.add_argument("--slotki", help="plik wyjściowy z listą kluczy (jeden na linię, od najbliższego)")
    parser.add_argument("--json", action="store_true")
    arguments = parser.parse_args(argv)
    try:
        magazyn = magazyn_mod.wczytaj(arguments.magazyn)
        mapy = None
        if arguments.kraina:
            prowincje = json.loads((Path(arguments.indeks) / "prowincje.json").read_text(encoding="utf-8"))
            wpis = next((row for row in prowincje if row.get("kraina") == arguments.kraina), None)
            if wpis is None:
                raise RegionyError(f"nie ma krainy {arguments.kraina!r}")
            mapy = set(wpis.get("mapy") or ())
        punkty, bez_pozycji = zbierz(arguments.indeks, magazyn, mapy=mapy)
        if not punkty:
            raise RegionyError("brak kwestii z pozycją — sprawdź index/ i magazyn")
        ix = indeks_mod.wczytaj(arguments.indeks, teksty=False)
        _kity, kity_scen = wczytaj_kity(arguments.indeks)
        kotwica = tuple(arguments.kotwica) if arguments.kotwica else kotwica_prologu(arguments.indeks, ix, kity_scen)
        if kotwica is None:
            raise RegionyError("nie ma pozycji prologu — podaj --kotwica X Z")
        wynik = raport(punkty, kotwica, siatka=arguments.siatka)
        wynik["bez_pozycji"] = bez_pozycji
    except (RegionyError, indeks_mod.IndeksError, magazyn_mod.MagazynError, OSError) as error:
        print(json.dumps({"ok": False, "powod": str(error)}, ensure_ascii=False))
        return 1

    if arguments.promien:
        wybrane = klucze_w_promieniu(punkty, kotwica, arguments.promien)
        if arguments.slotki:
            Path(arguments.slotki).parent.mkdir(parents=True, exist_ok=True)
            Path(arguments.slotki).write_text("".join(f"{klucz}\n" for klucz in wybrane), encoding="utf-8")
        wynik["wybranych"] = len(wybrane)
        wynik["plik_slotkow"] = arguments.slotki

    if arguments.json:
        print(json.dumps(wynik, ensure_ascii=False, indent=1))
        return 0
    print(f"Kotwica (XZ): {wynik['kotwica_xz']}  klastry co {arguments.siatka} m")
    print(f"Kwestie z pozycją: {wynik['z_pozycja']}, bez pozycji: {bez_pozycji}")
    print("Pierścienie od kotwicy:")
    for pierscien in wynik["pierścienie"]:
        print(f"  ≤{pierscien['do_m']:>5} m: {pierscien['klucze']:5d}")
    print("Największe klastry:")
    for grupa in wynik["klastry"][:10]:
        print(f"  X {grupa['x']:>6} Z {grupa['z']:>6}: {grupa['klucze']:5d} kluczy, {grupa['od_m']:>5} m od kotwicy")
    if arguments.promien:
        print(f"Zapisano {wynik['wybranych']} kluczy (≤{arguments.promien} m) do {arguments.slotki or '—'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
