#!/usr/bin/env python3
"""Odczyt wyciągu `index/` (format `wwm-indeks-v2`, zapisywany przez `tools/wyciag.py`).

Wszystkie kroki po ekstrakcji — pakiet dla tłumacza, import zwrotki, audyt
aktualizacji — czytają dane wyłącznie przez ten moduł, więc nie potrzebują
plików gry.

    indeks = wczytaj("index")
    indeks.teksty[klucz]      -> Tekst(zrodlo, en, n, w, z_en)
    indeks.sceny[numer]       -> wiersz sceny (`d`, `o`, `e`, `p`, `n`, `r`, `m`, …)
    indeks.zadania[numer]     -> wiersz zadania
    indeks.warianty[id]       -> kwestia zależna od płci bohatera: klucz, wariant, en
    indeks.zrodlo(tekst)      -> ("tabela", "pole", "wiersz") głównego źródła albo None

Użycie z wiersza poleceń (krótki opis indeksu albo jeden tekst po kluczu):
    python3 tools/indeks.py index
    python3 tools/indeks.py index --klucz 3fa91c0b7e12d455
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, NamedTuple

try:
    from tools import mapa_tekstow
except ImportError:  # uruchomienie jako skrypt
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from tools import mapa_tekstow

FORMAT = "wwm-indeks-v2"


class IndeksError(Exception):
    """Katalog nie zawiera czytelnego wyciągu w oczekiwanym formacie."""


class Tekst(NamedTuple):
    zrodlo: str  # tekst źródłowy: chiński, a gdy go nie ma — angielski
    en: str | None  # wersja angielska gry (pomocnicza); None, gdy brak
    n: int  # ile identyfikatorów gry ma ten tekst
    w: tuple | None  # (numer źródła w `zrodla`, klucz wiersza[, klucz nazwy wiersza]) albo None
    z_en: bool  # True: tekst nie ma wersji chińskiej, źródłem jest angielski


def _wiersze(path: Path) -> Iterator[dict]:
    with path.open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as error:
                raise IndeksError(f"{path.name}:{number}: {error}") from error


@dataclass
class Indeks:
    katalog: Path
    manifest: dict
    teksty: dict[str, Tekst] = field(default_factory=dict)
    zrodla: list = field(default_factory=list)
    sceny: dict[int, dict] = field(default_factory=dict)
    pola_dialogow: list = field(default_factory=list)
    zadania: dict[int, dict] = field(default_factory=dict)
    grupy: dict[int, dict] = field(default_factory=dict)
    typy_zadan: dict[int, dict] = field(default_factory=dict)
    streszczenia: list = field(default_factory=list)
    wybory: dict[str, dict] = field(default_factory=dict)
    opcje_npc: dict[int, dict] = field(default_factory=dict)
    postacie: dict[int, dict] = field(default_factory=dict)
    encyklopedia: dict[int, dict] = field(default_factory=dict)
    miejsca: dict = field(default_factory=dict)
    zamiany: list = field(default_factory=list)
    warianty: dict[str, dict] = field(default_factory=dict)  # id tekstu (hex) -> {k, w, en}
    przerywniki: dict = field(default_factory=dict)  # numer przerywnika -> {tekst, streszczenie}

    def zrodlo(self, tekst: Tekst) -> tuple[str, str, str] | None:
        """Główne źródło tekstu: (rodzaj tabeli, ścieżka pola, klucz wiersza)."""
        if not tekst.w:
            return None
        kind, path = self.zrodla[tekst.w[0]][:2]
        return kind, path, tekst.w[1]

    def nazwa_wiersza(self, tekst: Tekst) -> str | None:
        """Klucz tekstu-nazwy wiersza, z którego pochodzi tekst (np. nazwa przedmiotu przy opisie)."""
        return tekst.w[2] if tekst.w and len(tekst.w) > 2 else None

    def zh(self, klucz: str | None) -> str:
        """Tekst źródłowy po kluczu albo pusty napis."""
        tekst = self.teksty.get(klucz) if klucz else None
        return tekst.zrodlo if tekst else ""

    def en(self, klucz: str | None) -> str:
        tekst = self.teksty.get(klucz) if klucz else None
        if tekst is None:
            return ""
        return tekst.zrodlo if tekst.z_en else (tekst.en or "")


def _pliki(manifest: dict, nazwa: str) -> list[str]:
    entry = manifest.get("pliki", {}).get(nazwa)
    if entry is None:
        return []
    return [item["plik"] for item in entry] if isinstance(entry, list) else [entry["plik"]]


def wczytaj(katalog, *, teksty: bool = True, sceny: bool = True) -> Indeks:
    """Wczytaj wyciąg; `teksty=False` / `sceny=False` pomijają największe pliki."""
    root = Path(katalog)
    try:
        manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise IndeksError(f"{root}: brak czytelnego manifest.json ({error})") from error
    if manifest.get("format") != FORMAT:
        raise IndeksError(f"{root}: format {manifest.get('format')!r}, oczekiwano {FORMAT!r}")
    indeks = Indeks(root, manifest)

    def tabela(nazwa: str) -> Iterator[dict]:
        for name in _pliki(manifest, nazwa):
            yield from _wiersze(root / name)

    try:
        indeks.zrodla = json.loads((root / "zrodla.json").read_text(encoding="utf-8"))
        indeks.pola_dialogow = json.loads((root / "pola_dialogow.json").read_text(encoding="utf-8"))
        if teksty:
            for row in tabela("teksty"):
                z_en = row.get("zr") == "en"
                source = row["en"] if z_en else row["zh"]
                where = row.get("w")
                indeks.teksty[mapa_tekstow.klucz(source)] = Tekst(
                    source, None if z_en else row.get("en"), row.get("n", 1), tuple(where) if where else None, z_en
                )
        if sceny:
            for row in tabela("sceny"):
                indeks.sceny[row["d"]] = row
        for row in tabela("zadania"):
            indeks.zadania[row["no"]] = row
        for row in tabela("grupy_zadan"):
            indeks.grupy[row["id"]] = row
        for row in tabela("typy_zadan"):
            indeks.typy_zadan[row["id"]] = row
        indeks.streszczenia = list(tabela("streszczenia"))
        for row in tabela("wybory"):
            indeks.wybory[row["q"]] = row
        for row in tabela("opcje_npc"):
            indeks.opcje_npc[row["no"]] = row
        for row in tabela("postacie"):
            indeks.postacie[row["no"]] = row
        for row in tabela("encyklopedia"):
            indeks.encyklopedia[row["id"]] = row
        for row in tabela("miejsca"):
            indeks.miejsca[row["no"]] = row
        indeks.zamiany = list(tabela("zamiany_dialogow"))
        for row in tabela("warianty"):
            indeks.warianty[row["id"]] = row
        for row in tabela("przerywniki"):
            indeks.przerywniki[row["no"]] = row
    except (OSError, KeyError, json.JSONDecodeError) as error:
        raise IndeksError(f"{root}: niepełny wyciąg ({error!r})") from error
    return indeks


def sprawdz_pliki(katalog) -> list[str]:
    """Porównaj rozmiary i SHA-256 plików z manifestem; zwróć listę niezgodności."""
    root = Path(katalog)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    problems = []
    for entry in manifest.get("pliki", {}).values():
        for item in entry if isinstance(entry, list) else [entry]:
            path = root / item["plik"]
            if not path.is_file():
                problems.append(f"brak pliku {item['plik']}")
            elif path.stat().st_size != item["bajtow"] or mapa_tekstow.sha256_pliku(path) != item["sha256"]:
                problems.append(f"{item['plik']}: inna zawartość niż w manifeście")
    return problems


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Opis wyciągu index/ albo jeden tekst po kluczu.")
    parser.add_argument("katalog", nargs="?", default="index")
    parser.add_argument("--klucz", help="pokaż tekst o tym kluczu")
    parser.add_argument("--sprawdz", action="store_true", help="porównaj pliki z manifestem")
    arguments = parser.parse_args(argv)
    try:
        if arguments.sprawdz:
            problems = sprawdz_pliki(arguments.katalog)
            print(json.dumps({"ok": not problems, "niezgodnosci": problems}, ensure_ascii=False, indent=1))
            return 1 if problems else 0
        indeks = wczytaj(arguments.katalog, sceny=not arguments.klucz)
    except (IndeksError, OSError, json.JSONDecodeError) as error:
        print(json.dumps({"ok": False, "powod": str(error)}, ensure_ascii=False))
        return 1
    if arguments.klucz:
        tekst = indeks.teksty.get(arguments.klucz)
        if tekst is None:
            print(json.dumps({"ok": False, "powod": "nie ma takiego klucza"}, ensure_ascii=False))
            return 1
        print(json.dumps({"ok": True, **tekst._asdict(), "zrodlo_tabela": indeks.zrodlo(tekst)}, ensure_ascii=False, indent=1))
        return 0
    print(json.dumps({"ok": True, "format": FORMAT, "liczby": indeks.manifest["liczby"], "pokrycie": indeks.manifest["pokrycie"]}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
