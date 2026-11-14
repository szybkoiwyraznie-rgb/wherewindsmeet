#!/usr/bin/env python3
"""Magazyn polskich przekładów w repozytorium (`tlumaczenie/`).

    tlumaczenie/pl_X.jsonl        {"k": klucz tekstu, "pl": przekład}; X = pierwszy znak klucza
    tlumaczenie/pl_warianty.jsonl {"id": id tekstu (hex), "pl": przekład} — kwestie zależne
                                  od płci bohatera, każdy identyfikator osobno

Przekład jest przypisany do **klucza tekstu źródłowego**, nie do identyfikatora
z gry. Dzięki temu po aktualizacji gry te same teksty pod nowymi identyfikatorami
są od razu przetłumaczone, a do tłumacza wracają tylko teksty naprawdę nowe.
Pliki dzielone są stałą regułą, więc kolejne zwrotki zmieniają tylko swoje wiersze.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

CZESCI = "0123456789abcdef"
PLIK_WARIANTOW = "pl_warianty.jsonl"


class MagazynError(Exception):
    """Plik magazynu przekładów jest nieczytelny albo niespójny."""


@dataclass
class Magazyn:
    po_kluczu: dict[str, str] = field(default_factory=dict)
    po_id: dict[str, str] = field(default_factory=dict)  # id tekstu jako 16 znaków hex

    def __len__(self) -> int:
        return len(self.po_kluczu) + len(self.po_id)

    def ma(self, slot: str) -> bool:
        """`slot` w zapisie pakietu: klucz albo `@id`."""
        return slot[1:] in self.po_id if slot.startswith("@") else slot in self.po_kluczu

    def przeklad(self, slot: str) -> str | None:
        return self.po_id.get(slot[1:]) if slot.startswith("@") else self.po_kluczu.get(slot)

    def ustaw(self, slot: str, pl: str) -> None:
        if slot.startswith("@"):
            self.po_id[slot[1:]] = pl
        else:
            self.po_kluczu[slot] = pl


def wczytaj(katalog) -> Magazyn:
    """Wczytaj magazyn; brak katalogu oznacza pusty magazyn."""
    root = Path(katalog)
    magazyn = Magazyn()
    if not root.is_dir():
        return magazyn
    for path in sorted(root.glob("pl_*.jsonl")):
        with path.open(encoding="utf-8") as handle:
            for number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                    text = row["pl"]
                    if not isinstance(text, str):
                        raise TypeError("pole `pl` nie jest napisem")
                    if path.name == PLIK_WARIANTOW:
                        magazyn.po_id[row["id"]] = text
                    else:
                        magazyn.po_kluczu[row["k"]] = text
                except (json.JSONDecodeError, KeyError, TypeError) as error:
                    raise MagazynError(f"{path.name}:{number}: {error!r}") from error
    return magazyn


def _rodzina_i_wiersz(ix, tekst) -> tuple[str, str] | None:
    """(`rodzina tabeli`, `wiersz`) tekstu źródłowego — np. `("text_msg", "590339")`.

    Warstwy tej samej tabeli (`text_msg` i `text_msg__grey`) mają te same numery
    wierszy, więc po nich poznajemy, że to **ta sama** linia napisu w innym stylu.
    """
    zrodlo = ix.zrodlo(tekst)
    if not zrodlo:
        return None
    tabela, _kolumna, wiersz = zrodlo[0], zrodlo[1], zrodlo[2]
    return (tabela.split("__")[0], wiersz)


def doloz_blizniaki(magazyn: Magazyn, ix) -> dict:
    """Uzupełnij magazyn przekładami tej samej linii z innej warstwy tej samej tabeli.

    Klucz przekładu to SHA-256 dokładnej treści, a ta sama chińska linia bywa
    zapisana w `text_msg` i w `text_msg__grey` z inną liczbą spacji (warstwa
    „szara” ma mówcę wpisanego w treść). Przez to miała osobny, pusty klucz —
    i właśnie dlatego część napisów cutscen zostawała po angielsku, choć ich
    przekład już istniał pod kluczem bliźniaka.

    Warunek jest celowo wąski: **ten sam wiersz tej samej tabeli** i ta sama
    treść po znormalizowaniu spacji. Nie łączymy różnych zdań o tym samym
    chińskim zapisie (kolizje znaczeń zostają nietknięte — patrz
    `tests/test_kolizje_wariantow.py`). Uzupełniamy **tylko w pamięci**: pliki
    `tlumaczenie/pl_*.jsonl` przechowują wyłącznie przekłady ludzi.
    """
    from tools import indeks as indeks_mod

    po_wierszu: dict[tuple[str, str], tuple[str, str]] = {}
    for klucz, przeklad in magazyn.po_kluczu.items():
        tekst = ix.teksty.get(klucz)
        if tekst is None or not tekst.zrodlo:
            continue
        gdzie = _rodzina_i_wiersz(ix, tekst)
        if gdzie is not None:
            po_wierszu.setdefault(gdzie, (indeks_mod.znormalizowany(tekst.zrodlo), przeklad))
    dodane = 0
    for klucz, tekst in ix.teksty.items():
        if klucz in magazyn.po_kluczu or not tekst.zrodlo:
            continue
        gdzie = _rodzina_i_wiersz(ix, tekst)
        if gdzie is None:
            continue
        blizniak = po_wierszu.get(gdzie)
        if blizniak is None or blizniak[0] != indeks_mod.znormalizowany(tekst.zrodlo):
            continue
        magazyn.po_kluczu[klucz] = blizniak[1]
        dodane += 1
    return {"dodane": dodane, "kluczy": len(magazyn.po_kluczu)}


def zapisz(katalog, magazyn: Magazyn) -> list[str]:
    """Zapisz magazyn; zwraca nazwy zapisanych plików. Puste części są usuwane."""
    root = Path(katalog)
    root.mkdir(parents=True, exist_ok=True)
    parts: dict[str, list[str]] = {part: [] for part in CZESCI}
    for key in sorted(magazyn.po_kluczu):
        if len(key) != 16 or key[0] not in parts:
            raise MagazynError(f"niepoprawny klucz tekstu: {key!r}")
        parts[key[0]].append(json.dumps({"k": key, "pl": magazyn.po_kluczu[key]}, ensure_ascii=False) + "\n")
    written = []
    for part, lines in parts.items():
        path = root / f"pl_{part}.jsonl"
        if lines:
            path.write_text("".join(lines), encoding="utf-8", newline="\n")
            written.append(path.name)
        elif path.exists():
            path.unlink()
    path = root / PLIK_WARIANTOW
    if magazyn.po_id:
        path.write_text(
            "".join(
                json.dumps({"id": ident, "pl": magazyn.po_id[ident]}, ensure_ascii=False) + "\n"
                for ident in sorted(magazyn.po_id)
            ),
            encoding="utf-8",
            newline="\n",
        )
        written.append(path.name)
    elif path.exists():
        path.unlink()
    return written
