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
SEKCJA_PRZERYWNIKI = "sceny przerywników (timeline, `ui_type` 10)"
SEKCJA_GREY = "napisy — warstwa `text_msg__grey` (mówca wpisany w treść)"
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

    dodaj(SEKCJA_GREY, sorted(klucz for klucz, tekst in ix.teksty.items() if _zrodlo_grey(ix, tekst)))
    if sceny:
        dodaj(SEKCJA_PRZERYWNIKI, (slot for _numer, sloty in sceny_przerywnikow(ix) for slot in sloty))
        dodaj(
            "sceny — dialogi i plansze z timeline'ów",
            (slot_elementu(element) for scena in ix.sceny.values() for element in scena.get("e", ())),
        )

    dodaj("wszystkie unikalne teksty wyciągu", ix.teksty.keys())
    return wynik


def _zrodlo_grey(ix: indeks_mod.Indeks, tekst) -> bool:
    """Czy tekst pochodzi z warstwy `text_msg__grey` (napisy z mówcą w treści)."""
    zrodlo = ix.zrodlo(tekst)
    return bool(zrodlo) and zrodlo[0] == "text_msg__grey"


def wiersze_grey(ix: indeks_mod.Indeks, magazyn: magazyn_mod.Magazyn) -> list[dict]:
    """Wiersze warstwy `text_msg__grey` bez przekładu (numer wiersza `text_msg`)."""
    wynik: list[dict] = []
    for klucz, tekst in sorted(ix.teksty.items()):
        if not _zrodlo_grey(ix, tekst) or magazyn.przeklad(klucz):
            continue
        zrodlo = ix.zrodlo(tekst)
        wynik.append({"klucz": klucz, "wiersz": int(zrodlo[2]), "zh": tekst.zrodlo, "en": tekst.en})
    return wynik


def sceny_przerywnikow(ix: indeks_mod.Indeks) -> list[tuple[int, list[str]]]:
    """(numer sceny, sloty jej elementów) dla scen odtwarzanych jako przerywniki."""
    wynik: list[tuple[int, list[str]]] = []
    for numer in sorted(ix.sceny):
        scena = ix.sceny[numer]
        if scena.get("u") not in indeks_mod.UI_TYPY_PRZERYWNIKA:
            continue
        wynik.append((numer, [slot_elementu(element) for element in scena.get("e", ())]))
    return wynik


def braki_przerywnikow(
    ix: indeks_mod.Indeks,
    magazyn: magazyn_mod.Magazyn,
    *,
    od: int | None = None,
    do: int | None = None,
) -> list[dict]:
    """Wiersze scen przerywników (timeline) bez przekładu — to one zostają po angielsku."""
    wynik: list[dict] = []
    for numer, sloty in sceny_przerywnikow(ix):
        if od is not None and numer < od:
            continue
        if do is not None and numer > do:
            continue
        scena = ix.sceny[numer]
        for element, slot in zip(scena.get("e", ()), sloty):
            if magazyn.przeklad(slot):
                continue
            tekst = ix.teksty.get(slot[1:]) if slot.startswith("@") else ix.teksty.get(slot)
            if tekst is None:
                continue
            if slot.startswith("@"):
                wariant = ix.warianty.get(slot[1:], {})
                en = wariant.get("en")
            else:
                en = tekst.en
            wynik.append(
                {
                    "scena": numer,
                    "dialog": scena.get("d"),
                    "projekt": scena.get("p"),
                    "klucz": slot,
                    "zh": None if tekst.z_en else tekst.zrodlo,
                    "en": en,
                    "zrodlo": list(ix.zrodlo(tekst) or ()),
                }
            )
    return wynik


def arkusz(
    ix: indeks_mod.Indeks,
    magazyn: magazyn_mod.Magazyn,
    *,
    kinowe: bool = True,
    przerywniki: bool = True,
    od: int | None = None,
    do: int | None = None,
) -> str:
    """Arkusz braków w formacie pakietu (`klucz:` / `PL:`) gotowy do wczytania zwrotką."""
    czesci = [
        "# Arkusz uzupełnienia przekładu",
        "",
        "Wiersze, które w grze zostają po angielsku. Polski tekst wpisz w jednej linii po `PL:`,",
        "a plik oddaj przez `python3 tools/import_zwrotki.py ARKUSZ --indeks index --magazyn tlumaczenie`.",
        "",
    ]
    if kinowe:
        rows = braki_kinowe(ix, magazyn)
        if rows:
            czesci += [f"## Napisy cutscen, intro i filmów — {len(rows)} wierszy", ""]
            licznik = 0
            for typ in TYPY_KINOWE:
                grupa = [row for row in rows if row["typ"] == typ]
                if not grupa:
                    continue
                czesci += [f"### {OPIS_TYPU[typ]}", ""]
                for row in grupa:
                    licznik += 1
                    if typ == "film":
                        gdzie = f"film {row.get('film')} · id {row.get('id')}"
                    elif typ == "napis":
                        gdzie = f"text_msg {row.get('wiersz')}"
                    else:
                        gdzie = f"id {row.get('id')}"
                    czesci.append(f"{licznik}. [{gdzie}] {row.get('zh') or ''}".rstrip())
                    czesci.append(f"   klucz: {row['klucz']}")
                    czesci.append(f"   EN: {_tekst_na_jedna_linie(row.get('en'))}")
                    czesci.append("   PL:")
                    czesci.append("")
    if przerywniki:
        rows = braki_przerywnikow(ix, magazyn, od=od, do=do)
        if rows:
            zakres = "" if od is None and do is None else f" (sceny {od if od is not None else '…'}–{do if do is not None else '…'})"
            czesci += [f"## Sceny przerywników (timeline){zakres} — {len(rows)} wierszy", ""]
            poprzednia = None
            licznik = 0
            for row in rows:
                if row["scena"] != poprzednia:
                    poprzednia = row["scena"]
                    licznik = 0
                    naglowek = f"### Scena {row['scena']} — dialog {row['dialog']}"
                    if row.get("projekt"):
                        naglowek += f" — projekt {row['projekt']}"
                    czesci += [naglowek, ""]
                licznik += 1
                czesci.append(f"{licznik}. [Kwestia] {row.get('zh') or ''}".rstrip())
                czesci.append(f"   klucz: {row['klucz']}")
                czesci.append(f"   EN: {_tekst_na_jedna_linie(row.get('en'))}")
                czesci.append("   PL:")
                czesci.append("")
    return "\n".join(czesci).rstrip() + "\n"


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


def _wypisz_braki_przerywnikow(rows: list[dict], limit: int = 12) -> None:
    if not rows:
        print("Brak braków: wszystkie wiersze scen przerywników mają przekład.")
        return
    wedlug_sceny: dict[int, list[dict]] = {}
    for row in rows:
        wedlug_sceny.setdefault(row["scena"], []).append(row)
    print(f"SCENY PRZERYWNIKÓW BEZ PRZEKŁADU: {_liczba(len(rows))} wierszy w {_liczba(len(wedlug_sceny))} scenach")
    print("(klient pokazuje te wiersze jako napisy cutsceny; pełna lista: `--arkusz PLIK`)")
    print()
    for numer, grupa in list(wedlug_sceny.items())[:limit]:
        pierwszy = grupa[0]
        naglowek = f"scena {numer} (dialog {pierwszy.get('dialog')}"
        if pierwszy.get("projekt"):
            naglowek += f", projekt {pierwszy['projekt']}"
        print(f"- {naglowek}): {_liczba(len(grupa))} braków")
        for row in grupa[:3]:
            print(f"    [{row['klucz']}] {_skroc(row.get('en'), 90)}")
        if len(grupa) > 3:
            print(f"    … i {_liczba(len(grupa) - 3)} więcej")
    if len(wedlug_sceny) > limit:
        print(f"… i {_liczba(len(wedlug_sceny) - limit)} kolejnych scen (pełna lista w arkuszu)")


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
    parser.add_argument("--brak-przerywnikow", action="store_true", help="wypisz sceny przerywników (timeline) bez przekładu")
    parser.add_argument("--arkusz", help="zapisz plik .md z brakami w formacie pakietu (`klucz:` / `PL:`) do uzupełnienia")
    parser.add_argument(
        "--arkusz-tylko",
        choices=("wszystko", "kinowe", "przerywniki"),
        default="wszystko",
        help="co ma zawierać arkusz: napisy cutscen i filmów, sceny przerywników albo oba (domyślnie)",
    )
    parser.add_argument("--szukaj", help="znajdź tekst po fragmencie EN, ZH albo PL i pokaż, czy ma przekład")
    parser.add_argument("--bez-scen", action="store_true", help="pomiń sekcję scen (szybsze, bez wczytywania timeline'ów)")
    parser.add_argument("--sceny-od", type=int, help="przy `--arkusz`/`--brak-przerywnikow`: najniższy numer sceny")
    parser.add_argument("--sceny-do", type=int, help="przy `--arkusz`/`--brak-przerywnikow`: najwyższy numer sceny")
    parser.add_argument("--pelny", action="store_true", help="przy `--szukaj` pokaż pełne teksty zamiast skróconych")
    parser.add_argument("--json", action="store_true", help="wynik jako JSON")
    arguments = parser.parse_args(argv)

    try:
        ix = indeks_mod.wczytaj(arguments.indeks, sceny=not arguments.bez_scen or bool(arguments.szukaj))
        magazyn = magazyn_mod.wczytaj(arguments.magazyn)
        # Dołóż przekłady bliźniaków o tej samej treści źródłowej (różne białe znaki),
        # żeby pomiar odpowiadał temu, co trafi do gry.
        blizniaki = magazyn_mod.doloz_blizniaki(magazyn, ix)
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

    if arguments.arkusz:
        tresc = arkusz(
            ix,
            magazyn,
            kinowe=arguments.arkusz_tylko in ("wszystko", "kinowe"),
            przerywniki=arguments.arkusz_tylko in ("wszystko", "przerywniki"),
            od=arguments.sceny_od,
            do=arguments.sceny_do,
        )
        cel = Path(arguments.arkusz)
        cel.parent.mkdir(parents=True, exist_ok=True)
        cel.write_text(tresc, encoding="utf-8", newline="\n")
        puste = tresc.count("\n   PL:\n")
        if arguments.json:
            print(json.dumps({"ok": True, "arkusz": str(cel), "miejsc": puste}, ensure_ascii=False))
        else:
            print(f"Zapisano arkusz: {cel} — miejsc do wypełnienia: {_liczba(puste)}")
            print("Po wypełnieniu: python3 tools/import_zwrotki.py " + str(cel) + " --indeks " + arguments.indeks + " --magazyn " + arguments.magazyn)
        return 0

    if arguments.brak_przerywnikow:
        rows = braki_przerywnikow(ix, magazyn, od=arguments.sceny_od, do=arguments.sceny_do)
        if arguments.json:
            print(json.dumps({"ok": True, "braki_przerywnikow": rows}, ensure_ascii=False, indent=1))
        else:
            _wypisz_braki_przerywnikow(rows)
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
