#!/usr/bin/env python3
"""Skąd pochodzi każdy tekst: tabela, pole i wiersz bazy gry.

Mapa tekstów (`translate_words_map_*`) mówi tylko `id -> tekst`. To, czym dany
tekst jest w grze (nazwa przedmiotu, cel zadania, wpis encyklopedii), wynika
z tego, **które pole której tabeli** trzyma jego identyfikator. Ten moduł
przechodzi wszystkie tabele bazy (docs/BAZA_GRY.md) i dla każdej wartości `u64`,
która jest kluczem mapy, zapisuje wystąpienie:

    (rodzaj tabeli, ścieżka pola, klucz wiersza, etykieta wiersza)

- *rodzaj tabeli* — nazwa z identyfikatorami zamienionymi na `*`
  (`spaces.s501.region` -> `spaces.*.region`);
- *ścieżka pola* — nazwy pól po kropkach, listy jako `[]`, klucze liczbowe
  słowników jako `{}`;
- *etykieta wiersza* — identyfikator tekstu z pola-nazwy tego samego wiersza
  (`name`, `*_name`, `title`), żeby opis dało się pokazać obok nazwy.

Nic tu nie jest zgadywane po treści: tekst bez wystąpienia w żadnej tabeli
zostaje „bez źródła” i jest tak raportowany.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Callable, Iterable

try:
    from tools import baza_gry
except ImportError:  # uruchomienie jako skrypt
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from tools import baza_gry

MAKS_WYSTAPIEN = 8
_Z_CYFRA = re.compile(r"\d")


def rodzaj_tabeli(nazwa: str) -> str:
    """`spaces.s1.building` -> `spaces.*.building`; pierwszy człon zostaje."""
    parts = nazwa.split(".")
    return ".".join([parts[0]] + ["*" if _Z_CYFRA.search(part) else part for part in parts[1:]])


def _pole(key) -> str:
    """Klucz słownika jako człon ścieżki; identyfikatory zlewają się w `{}`."""
    return key if isinstance(key, str) and key and not key[0].isdigit() and not key.lstrip("-").isdigit() else "{}"


def _waga_nazwy(key: str) -> int:
    """Im mniejsza liczba, tym bardziej pole wygląda na nazwę wiersza; 99 = nie nazwa."""
    if key == "name":
        return 0
    if key.endswith("_name") or key.startswith("name"):
        return 1
    if key == "title":
        return 2
    if "title" in key:
        return 3
    return 99


@dataclass
class Zrodla:
    """Wynik przeglądu: wystąpienia tekstów w tabelach."""

    pochodzenia: list[tuple[str, str]] = field(default_factory=list)  # indeks -> (rodzaj tabeli, ścieżka)
    wystapienia: dict[int, list[tuple[int, str, int]]] = field(default_factory=dict)
    liczba: Counter = field(default_factory=Counter)  # indeks pochodzenia -> liczba wystąpień
    wiersze: Counter = field(default_factory=Counter)  # rodzaj tabeli -> liczba wierszy
    bledy: dict[str, str] = field(default_factory=dict)  # tabela -> komunikat
    _indeks: dict[tuple[str, str], int] = field(default_factory=dict)

    def numer(self, rodzaj: str, sciezka: str) -> int:
        key = (rodzaj, sciezka)
        number = self._indeks.get(key)
        if number is None:
            number = self._indeks[key] = len(self.pochodzenia)
            self.pochodzenia.append(key)
        return number

    def dodaj(self, text_id: int, pochodzenie: int, klucz: str, etykieta: int) -> None:
        self.liczba[pochodzenie] += 1
        found = self.wystapienia.setdefault(text_id, [])
        if len(found) < MAKS_WYSTAPIEN:
            found.append((pochodzenie, klucz, etykieta))


def etykieta_wiersza(row, czy_tekst: Callable[[int], bool]) -> int:
    """Identyfikator tekstu z pola-nazwy wiersza albo 0."""
    if not isinstance(row, dict):
        return 0
    best, best_weight = 0, 99
    for key, value in row.items():
        if not isinstance(key, str) or not _jest_tekstem(value, czy_tekst):
            continue
        weight = _waga_nazwy(key)
        if weight < best_weight:
            best, best_weight = value, weight
    return best


def _jest_tekstem(value, czy_tekst: Callable[[int], bool]) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0xFFFFFFFF and czy_tekst(value)


def teksty_wiersza(row, czy_tekst: Callable[[int], bool]) -> list[tuple[str, int]]:
    """Wszystkie `(ścieżka pola, id tekstu)` jednego wiersza, w kolejności danych."""
    found: list[tuple[str, int]] = []

    def walk(value, path: str) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                name = _pole(key)
                walk(item, f"{path}.{name}" if path else name)
        elif isinstance(value, list):
            for item in value:
                walk(item, path + "[]")
        elif _jest_tekstem(value, czy_tekst):
            found.append((path, value))

    walk(row, "")
    return found


def zbierz(
    baza: baza_gry.Baza,
    czy_tekst: Callable[[int], bool],
    pomin_rodziny: Iterable[str] = (),
    postep: Callable[[int, int], None] | None = None,
    obserwator: Callable[[str, str, object, object], None] | None = None,
) -> Zrodla:
    """Przejdź wszystkie tabele poza `pomin_rodziny` i zbierz wystąpienia tekstów.

    `obserwator(rodzaj, nazwa_tabeli, klucz, wiersz)` dostaje każdy wiersz, żeby
    inne przeglądy (odwołania do dialogów, tabele zadań) nie musiały czytać bazy
    drugi raz.
    """
    skip = set(pomin_rodziny)
    # Tabele podstawowe zawsze przed bliźniakami `__grey`, z zachowaniem kolejności tabel.
    names = sorted(
        (name for name in baza.tabele if baza_gry.rodzina(name) not in skip),
        key=lambda name: name.endswith("__grey"),
    )
    result = Zrodla()
    for number, name in enumerate(names, 1):
        kind = rodzaj_tabeli(name)
        try:
            for key, row in baza.wiersze(name):
                result.wiersze[kind] += 1
                if obserwator is not None:
                    obserwator(kind, name, key, row)
                texts = teksty_wiersza(row, czy_tekst)
                if not texts:
                    continue
                label = etykieta_wiersza(row, czy_tekst)
                # W tabelach wielokrotnych (`spaces.s501.region`) klucz wiersza nie jest
                # jednoznaczny bez nazwy tabeli, więc dokładamy jej zmienną część.
                row_key = str(key) if kind == name else f"{name}#{key}"
                for path, text_id in texts:
                    result.dodaj(text_id, result.numer(kind, path), row_key, label)
        except baza_gry.BazaError as error:
            result.bledy[name] = str(error)[:200]
        if postep and number % 5000 == 0:
            postep(number, len(names))
    return result
