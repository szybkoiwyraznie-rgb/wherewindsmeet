#!/usr/bin/env python3
"""Audyt zakresu tymczasowego przekładu AI: co jest zrobione, a czego brakuje.

Narzędzie **tylko czyta** repozytorium (`index/` + `tlumaczenie/` + wpisy
`zwrotki/*.md`). Odpowiada na pytanie właściciela „czy tymczasowy zakres jest
domknięty?” bez zgadywania i bez plików gry:

    python3 tools/audyt_zakresu.py
    python3 tools/audyt_zakresu.py --json

Kategorie odpowiadają liście właściciela (STATUS.md, sekcja „Zakres wg potrzeb”):

1. **hinty zadań** — `tasks.task_target_str`,
2. **listy** — `tasks_envelop_data`,
3. **przedmioty fabularne** — `text_msg` w bloku 1 800 000–1 809 999
   (m.in. „Dusty Sword Tassel”) oraz wszystkie pola `manual_items`,
4. **elementy opisów przedmiotów** — `ccs_text_msg` i `programmer_text_msg`,
5. **Compendium** — `guider_tujian_data` (osobno nazwy i opisy),
6. **sceny pierwszej prowincji** — unikalne klucze tekstów scen, których mapa
   należy do pierwszej krainy z `index/prowincje.json` (domyślnie 燕南).

Dla każdej kategorii raport podaje: liczbę unikalnych kluczy, ile pochodzi
z przekładu tłumacza, ile dodano tymczasowo (klucz występuje w `zwrotki/*.md`
z niepustym `PL:`), pokrycie i braki. Brakujące kwestie scen dzieli dodatkowo
według powiązania sceny: kit ambientowy (`index/mpk/sceny_ambient_kity.jsonl`),
wyzwalacz `spaces.*` w polu `r`, zadanie (`index/zadania_sceny.jsonl`), reszta. Klucz tekstu jest wspólny dla wszystkich
miejsc w grze, więc kategoria liczy **teksty**, nie wystąpienia.

Ograniczenia: przypisanie mapy do sceny nie dowodzi, kiedy gracz ją zobaczy;
tabele `_diff` i warstwy języka nie są tu analizowane. To audyt zakresu,
nie test w grze.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path
from typing import Iterable

try:
    from tools import format_paczki as fmt
    from tools import indeks as indeks_mod
    from tools import tlumaczenie as magazyn_mod
    from tools import wypisz
except ImportError:  # uruchomienie jako skrypt
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from tools import format_paczki as fmt
    from tools import indeks as indeks_mod
    from tools import tlumaczenie as magazyn_mod
    from tools import wypisz

BLOK_PRZEDMIOTOW = (1800000, 1810000)
NAZWY_COMPENDIUM = ("manual_name", "talk_title[]", "button_name[]", "manual_goto_text", "bubble_text")

GRUPY_SCEN = ("ambient (kity)", "wyzwalane ze świata", "zadaniowe", "bez powiązania")
_KOLEJNOSC_GRUP = {nazwa: numer for numer, nazwa in enumerate(GRUPY_SCEN)}

KATEGORIE = (
    ("1 hinty zadań", "`tasks.task_target_str`"),
    ("2 listy", "`tasks_envelop_data`"),
    ("3 przedmioty fabularne", "`text_msg` 1 800 000–1 809 999 + `manual_items`"),
    ("4 opisy przedmiotów", "`ccs_text_msg` + `programmer_text_msg`"),
    ("5 Compendium", "`guider_tujian_data`"),
    ("6 sceny pierwszej prowincji", "sceny z mapami pierwszej krainy"),
)


class AudytError(Exception):
    """Wejścia nie da się odczytać."""


def klucze_ai(zwrotki: Iterable) -> set[str]:
    """Klucze tekstów, które mają niepuste `PL:` w plikach `.md` zwrotek."""
    klucze: set[str] = set()
    for sciezka in zwrotki:
        try:
            tresc = Path(sciezka).read_text(encoding="utf-8-sig", errors="replace")
        except OSError as error:
            raise AudytError(f"{sciezka}: {error}") from error
        for wpis in fmt.czytaj_wpisy(tresc):
            if wpis.pl:
                klucze.add(wpis.klucz)
    return klucze


def mapy_krainy(index_dir, kraina: str | None = None) -> tuple[str, set[int]]:
    """(nazwa krainy, numery map) pierwszej krainy albo wskazanej po nazwie."""
    try:
        prowincje = json.loads((Path(index_dir) / "prowincje.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise AudytError(f"brak czytelnego prowincje.json ({error})") from error
    if not prowincje:
        raise AudytError("prowincje.json jest pusty")
    if kraina is None:
        wpis = prowincje[0]
    else:
        wpis = next((row for row in prowincje if row.get("kraina") == kraina), None)
        if wpis is None:
            raise AudytError(f"nie ma krainy {kraina!r} w prowincje.json")
    return wpis.get("kraina", ""), set(wpis.get("mapy") or ())


def podzial_scen(ix, magazyn, mapy: set[int], *, kity=frozenset(), zadania_sceny=None) -> dict:
    """Podział brakujących kwestii scen na grupy według najsilniejszego powiązania sceny.

    Pierwszeństwo: kit ambientowy (`sceny_ambient_kity.jsonl`), wyzwalacz
    w świecie (`r` wskazujące `spaces.*`), zadanie (`zadania_sceny.jsonl`).
    Klucz liczony raz, w najsilniejszej grupie, w której występuje.
    """
    zadania = zadania_sceny or {}
    przypisanie: dict[str, str] = {}
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
        swiat = any(
            "spaces." in str(rel[1])
            for rel in (scena.get("r") or ())
            if isinstance(rel, list) and len(rel) > 1
        )
        numer = scena.get("d")
        if numer in kity:
            grupa = "ambient (kity)"
        elif swiat:
            grupa = "wyzwalane ze świata"
        elif numer in zadania:
            grupa = "zadaniowe"
        else:
            grupa = "bez powiązania"
        for klucz in klucze:
            if klucz not in przypisanie or _KOLEJNOSC_GRUP[grupa] < _KOLEJNOSC_GRUP[przypisanie[klucz]]:
                przypisanie[klucz] = grupa

    wynik = []
    for grupa in GRUPY_SCEN:
        dlugosci = [len(ix.teksty[klucz].zrodlo) for klucz, gdzie in przypisanie.items() if gdzie == grupa]
        wynik.append(
            {
                "grupa": grupa,
                "klucze": len(dlugosci),
                "mediana": statistics.median(dlugosci) if dlugosci else 0,
                "do_30": sum(1 for dlugosc in dlugosci if dlugosc <= 30),
                "od_60": sum(1 for dlugosc in dlugosci if dlugosc >= 60),
            }
        )
    return {"grupy": wynik, "razem": len(przypisanie)}


def _kategoria_tekstu(zrodlo) -> str | None:
    tabela, pole, wiersz = zrodlo
    if tabela == "tasks" and pole == "task_target_str":
        return "1 hinty zadań"
    if tabela == "tasks_envelop_data":
        return "2 listy"
    if tabela == "text_msg" and wiersz.isdigit() and BLOK_PRZEDMIOTOW[0] <= int(wiersz) < BLOK_PRZEDMIOTOW[1]:
        return "3 przedmioty fabularne"
    if tabela == "manual_items":
        return "3 przedmioty fabularne"
    if tabela in ("ccs_text_msg", "programmer_text_msg"):
        return "4 opisy przedmiotów"
    if tabela == "guider_tujian_data":
        return "5 Compendium"
    return None


def audyt(
    ix: indeks_mod.Indeks,
    magazyn: magazyn_mod.Magazyn,
    *,
    mapy: set[int],
    ai: set[str] = frozenset(),
    kity=frozenset(),
    zadania_sceny=None,
) -> dict:
    """Zestawienie pokrycia sześciu kategorii zakresu tymczasowego."""
    wedlug: dict[str, set[str]] = {nazwa: set() for nazwa, _opis in KATEGORIE}
    for klucz, tekst in ix.teksty.items():
        zrodlo = ix.zrodlo(tekst)
        if zrodlo is None:
            continue
        kategoria = _kategoria_tekstu(zrodlo)
        if kategoria is not None:
            wedlug[kategoria].add(klucz)

    if mapy:
        sceny = wedlug["6 sceny pierwszej prowincji"]
        for scena in ix.sceny.values():
            if not (set(scena.get("m") or ()) & mapy):
                continue
            for element in scena.get("e", ()):
                slot = element[4] if len(element) > 4 and element[3] else element[2]
                klucz = slot[1:] if slot.startswith("@") else slot
                if klucz in ix.teksty:
                    sceny.add(klucz)

    wynik = []
    for nazwa, opis in KATEGORIE:
        klucze = wedlug[nazwa]
        przetlumaczone = {klucz for klucz in klucze if magazyn.przeklad(klucz)}
        tymczasowe = przetlumaczone & ai
        wynik.append(
            {
                "kategoria": nazwa,
                "opis": opis,
                "razem": len(klucze),
                "tlumacz": len(przetlumaczone) - len(tymczasowe),
                "ai": len(tymczasowe),
                "przetlumaczone": len(przetlumaczone),
                "braki": len(klucze) - len(przetlumaczone),
                "procent": round(100 * len(przetlumaczone) / len(klucze), 1) if klucze else 0.0,
            }
        )

    compendium = {"nazwy": {"razem": 0, "przetlumaczone": 0}, "opisy": {"razem": 0, "przetlumaczone": 0}}
    for klucz in wedlug["5 Compendium"]:
        tekst = ix.teksty[klucz]
        pole = ix.zrodlo(tekst)[1]
        grupa = "nazwy" if pole in NAZWY_COMPENDIUM else "opisy"
        compendium[grupa]["razem"] += 1
        if magazyn.przeklad(klucz):
            compendium[grupa]["przetlumaczone"] += 1
    for grupa in compendium.values():
        grupa["braki"] = grupa["razem"] - grupa["przetlumaczone"]
        grupa["procent"] = (
            round(100 * grupa["przetlumaczone"] / grupa["razem"], 1) if grupa["razem"] else 0.0
        )

    sceny_podzial = podzial_scen(ix, magazyn, mapy, kity=kity, zadania_sceny=zadania_sceny) if mapy else {"grupy": [], "razem": 0}

    return {
        "format": "wwm-audyt-zakresu-v1",
        "kategorie": wynik,
        "sceny": sceny_podzial,
        "compendium": compendium,
        "mapy_scen": sorted(mapy),
        "lacznie_ai": len(ai),
    }


def _wczytaj_grupy_scen(katalog) -> tuple[set[int], dict]:
    """Zbiór scen z kitów ambientowych i mapa scena -> zadania (puste, gdy brak plików)."""
    kity: set[int] = set()
    zadania: dict[int, set[int]] = {}
    try:
        for wiersz in _wiersze_jsonl(Path(katalog) / "mpk" / "sceny_ambient_kity.jsonl"):
            if isinstance(wiersz.get("scena"), int):
                kity.add(wiersz["scena"])
    except (OSError, ValueError):
        pass
    try:
        for wiersz in _wiersze_jsonl(Path(katalog) / "zadania_sceny.jsonl"):
            numer = wiersz.get("zadanie")
            for zdarzenie in wiersz.get("zdarzenia") or ():
                if isinstance(zdarzenie, (list, tuple)) and zdarzenie[0] == "scena" and numer is not None:
                    zadania.setdefault(zdarzenie[1], set()).add(numer)
    except (OSError, ValueError):
        pass
    return kity, zadania


def _wiersze_jsonl(sciezka: Path):
    """Wiersze JSONL; brak pliku kończy iterację bez błędu tylko przez OSError."""
    with sciezka.open(encoding="utf-8") as uchwyt:
        for linia in uchwyt:
            if linia.strip():
                yield json.loads(linia)


def main(argv=None) -> int:
    wypisz.utf8()
    parser = argparse.ArgumentParser(description="Audyt pokrycia tymczasowego zakresu przekładu AI.")
    parser.add_argument("--indeks", default="index")
    parser.add_argument("--magazyn", default="tlumaczenie")
    parser.add_argument("--zwrotki", default="zwrotki", help="katalog z plikami .md zwrotek AI")
    parser.add_argument("--kraina", help="nazwa krainy scen (domyślnie pierwsza w prowincje.json)")
    parser.add_argument("--json", action="store_true", help="wynik w JSON zamiast tabeli")
    arguments = parser.parse_args(argv)
    try:
        kraina, mapy = mapy_krainy(arguments.indeks, arguments.kraina)
        ix = indeks_mod.wczytaj(arguments.indeks)
        magazyn = magazyn_mod.wczytaj(arguments.magazyn)
        katalog = Path(arguments.zwrotki)
        zwrotki = sorted(katalog.glob("*.md")) if katalog.is_dir() else []
        ai = klucze_ai(zwrotki)
        kity, zadania_sceny = _wczytaj_grupy_scen(arguments.indeks)
        raport = audyt(ix, magazyn, mapy=mapy, ai=ai, kity=kity, zadania_sceny=zadania_sceny)
    except (AudytError, indeks_mod.IndeksError, magazyn_mod.MagazynError, OSError) as error:
        print(json.dumps({"ok": False, "powod": str(error)}, ensure_ascii=False))
        return 1
    raport["kraina_scen"] = kraina
    raport["ok"] = True
    if arguments.json:
        print(json.dumps(raport, ensure_ascii=False, indent=1))
        return 0
    print(f"Kraina scen: {kraina} (mapy {', '.join(map(str, sorted(mapy))) or 'brak'})")
    print(f"Kluczy oznaczonych jako tymczasowe (zwrotki AI): {len(ai)}")
    print()
    print(f"{'kategoria':30s} {'razem':>7s} {'tłumacz':>8s} {'AI':>7s} {'pokrycie':>18s}")
    for row in raport["kategorie"]:
        pokrycie = f"{row['przetlumaczone']}/{row['razem']} ({row['procent']}%)"
        print(f"{row['kategoria']:30s} {row['razem']:7d} {row['tlumacz']:8d} {row['ai']:7d} {pokrycie:>18s}")
    sceny = raport.get("sceny") or {}
    if sceny.get("grupy"):
        print()
        print(f"Brakujące kwestie scen według powiązania (razem {sceny['razem']}):")
        for row in sceny["grupy"]:
            print(
                f"  {row['grupa']:22s} {row['klucze']:6d} kluczy, "
                f"mediana {row['mediana']:>4} znaków, ≤30: {row['do_30']}, ≥60: {row['od_60']}"
            )
    comp = raport["compendium"]
    print()
    print(
        "Compendium: nazwy "
        f"{comp['nazwy']['przetlumaczone']}/{comp['nazwy']['razem']} "
        f"(brak {comp['nazwy']['braki']}), opisy "
        f"{comp['opisy']['przetlumaczone']}/{comp['opisy']['razem']} "
        f"(brak {comp['opisy']['braki']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
