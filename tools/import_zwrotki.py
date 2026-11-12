#!/usr/bin/env python3
"""Import zwrotki tłumacza: pliki `.md` pakietu z wypełnionymi `PL:` → magazyn przekładów.

    python3 tools/import_zwrotki.py --indeks index --magazyn tlumaczenie \\
        --raport dist/import.json ZWROTKA...

`ZWROTKA` to katalog, plik `.md` albo zip (także zip z `sceny.zip` i `widoki.zip`
w środku). Czytane są tylko linie `klucz:` i `PL:` — nazwy plików, numery scen
i kolejność nie mają znaczenia, więc tłumacz może odsyłać dowolne części pakietu,
partiami i wielokrotnie.

Co jest sprawdzane przy każdym niepustym `PL:`:
- klucz istnieje w wyciągu `index/` (inaczej: `nieznany_klucz`);
- przekład stoi w jednej linii (inaczej: `zlamana_linia`);
- kody gry zgadzają się z tekstem źródłowym albo z wersją angielską — te same
  kody, tyle samo razy (inaczej: `tokeny`);
- ten sam klucz nie ma w zwrotce dwóch różnych przekładów (inaczej: `sprzeczne`).

Wpis z problemem **nie trafia** do magazynu i jest wypisany w raporcie z plikiem
i numerem linii; reszta zwrotki importuje się normalnie. Raport nie zawiera
treści przekładów. Kod wyjścia: 0 — wszystko przyjęte, 2 — część wpisów
odrzucona, 1 — błąd wejścia.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import zipfile
from collections import Counter
from pathlib import Path
from typing import Iterator

try:
    from tools import format_paczki as fmt
    from tools import indeks as indeks_mod
    from tools import tlumaczenie as magazyn_mod
except ImportError:  # uruchomienie jako skrypt
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from tools import format_paczki as fmt
    from tools import indeks as indeks_mod
    from tools import tlumaczenie as magazyn_mod

MAKS_PROBLEMOW_W_RAPORCIE = 2000


class ZwrotkaError(Exception):
    """Wejścia nie da się odczytać jako zwrotki."""


def _z_zipa(data: bytes, nazwa: str) -> Iterator[tuple[str, str]]:
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as error:
        raise ZwrotkaError(f"{nazwa}: to nie jest poprawny zip") from error
    with archive:
        for info in sorted(archive.infolist(), key=lambda item: item.filename):
            if info.is_dir():
                continue
            inner = f"{nazwa}!{info.filename}"
            lower = info.filename.lower()
            if lower.endswith(".zip"):
                yield from _z_zipa(archive.read(info), inner)
            elif lower.endswith(".md"):
                yield inner, archive.read(info).decode("utf-8-sig", "replace")


def pliki_zwrotki(sciezki) -> Iterator[tuple[str, str]]:
    """(nazwa do raportu, treść) każdego pliku `.md` zwrotki."""
    for item in sciezki:
        path = Path(item)
        if path.is_dir():
            for inner in sorted(path.rglob("*")):
                if inner.is_file() and inner.suffix.lower() == ".zip":
                    yield from _z_zipa(inner.read_bytes(), inner.relative_to(path).as_posix())
                elif inner.is_file() and inner.suffix.lower() == ".md":
                    yield inner.relative_to(path).as_posix(), inner.read_text(encoding="utf-8-sig", errors="replace")
        elif path.is_file() and path.suffix.lower() == ".zip":
            yield from _z_zipa(path.read_bytes(), path.name)
        elif path.is_file():
            yield path.name, path.read_text(encoding="utf-8-sig", errors="replace")
        else:
            raise ZwrotkaError(f"nie ma takiego pliku ani katalogu: {item}")


def _zrodla(ix, slot: str) -> tuple[str, str | None] | None:
    """(tekst źródłowy, tekst angielski) elementu albo None, gdy klucza nie ma w wyciągu."""
    if slot.startswith("@"):
        variant = ix.warianty.get(slot[1:])
        if variant is None or variant["k"] not in ix.teksty:
            return None
        return ix.teksty[variant["k"]].zrodlo, variant.get("en")
    text = ix.teksty.get(slot)
    return (text.zrodlo, text.en) if text else None


def importuj(ix, pliki, magazyn: magazyn_mod.Magazyn, *, mimo_tokenow: bool = False) -> dict:
    """Wczytaj wpisy do magazynu (w pamięci) i zwróć raport."""
    counts = Counter()
    problems: list[dict] = []
    seen: dict[str, str] = {}
    files = 0

    def problem(kind: str, name: str, entry: fmt.Wpis, **extra) -> None:
        counts[kind] += 1
        if len(problems) < MAKS_PROBLEMOW_W_RAPORCIE:
            problems.append({"rodzaj": kind, "plik": name, "linia": entry.linia, "klucz": entry.klucz, **extra})

    for name, content in pliki:
        files += 1
        for entry in fmt.czytaj_wpisy(content):
            counts["miejsc_pl"] += 1
            if not entry.pl:
                counts["puste"] += 1
                continue
            sources = _zrodla(ix, entry.klucz)
            if sources is None:
                problem("nieznany_klucz", name, entry)
                continue
            if entry.ciag_dalszy:
                problem("zlamana_linia", name, entry)
                continue
            source, english = sources
            encoded_source = fmt.zakoduj(source)
            missing, extra = fmt.roznica_tokenow(encoded_source, entry.pl)
            if (missing or extra) and english:
                missing_en, extra_en = fmt.roznica_tokenow(fmt.zakoduj(english), entry.pl)
                if not missing_en and not extra_en:
                    missing, extra = [], []
            if missing or extra:
                problem("tokeny", name, entry, brakuje=missing, nadmiar=extra)
                if not mimo_tokenow:
                    continue
            lead, trail = fmt.brzegi(source)
            text = lead + fmt.odkoduj(entry.pl) + trail
            if entry.klucz in seen:
                if seen[entry.klucz] != text:
                    problem("sprzeczne", name, entry)
                continue
            seen[entry.klucz] = text
            previous = magazyn.przeklad(entry.klucz)
            if previous is None:
                counts["nowe"] += 1
            elif previous != text:
                counts["zmienione"] += 1
            else:
                counts["bez_zmian"] += 1
            magazyn.ustaw(entry.klucz, text)

    rejected = sum(counts[kind] for kind in ("nieznany_klucz", "zlamana_linia", "sprzeczne")) + (0 if mimo_tokenow else counts["tokeny"])
    total = len(ix.teksty) + len(ix.warianty)
    return {
        "format": "wwm-import-v1",
        "plikow": files,
        "liczby": {name: counts[name] for name in ("miejsc_pl", "puste", "nowe", "zmienione", "bez_zmian")},
        "odrzucone": rejected,
        "problemy_wg_rodzaju": {kind: counts[kind] for kind in ("nieznany_klucz", "zlamana_linia", "tokeny", "sprzeczne") if counts[kind]},
        "problemy": problems,
        "problemow_pominietych_w_raporcie": max(0, sum(counts[k] for k in ("nieznany_klucz", "zlamana_linia", "tokeny", "sprzeczne")) - len(problems)),
        "magazyn": {"przekladow": len(magazyn), "miejsc_w_grze": total, "procent": round(100 * len(magazyn) / total, 2) if total else 0},
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Import zwrotki tłumacza do magazynu przekładów.")
    parser.add_argument("zwrotka", nargs="+", help="katalog, plik .md albo zip ze zwrotką")
    parser.add_argument("--indeks", default="index")
    parser.add_argument("--magazyn", default="tlumaczenie")
    parser.add_argument("--raport", help="plik JSON z raportem")
    parser.add_argument("--na-sucho", action="store_true", help="sprawdź i policz, niczego nie zapisuj w magazynie")
    parser.add_argument("--mimo-tokenow", action="store_true", help="przyjmij także wpisy z niezgodnymi kodami gry")
    arguments = parser.parse_args(argv)
    try:
        ix = indeks_mod.wczytaj(arguments.indeks, sceny=False)
        magazyn = magazyn_mod.wczytaj(arguments.magazyn)
        report = importuj(ix, pliki_zwrotki(arguments.zwrotka), magazyn, mimo_tokenow=arguments.mimo_tokenow)
        if not arguments.na_sucho:
            report["zapisane_pliki"] = magazyn_mod.zapisz(arguments.magazyn, magazyn)
    except (indeks_mod.IndeksError, magazyn_mod.MagazynError, ZwrotkaError, OSError) as error:
        print(json.dumps({"ok": False, "powod": str(error)}, ensure_ascii=False))
        return 1
    if arguments.raport:
        Path(arguments.raport).parent.mkdir(parents=True, exist_ok=True)
        Path(arguments.raport).write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    summary = {name: report[name] for name in ("plikow", "liczby", "odrzucone", "problemy_wg_rodzaju", "magazyn")}
    print(json.dumps({"ok": not report["odrzucone"], **summary}, ensure_ascii=False, indent=1))
    return 2 if report["odrzucone"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
