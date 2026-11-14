#!/usr/bin/env python3
"""Scena z tabeli `dialog_timelines.<numer>` bazy gry (docs/BAZA_GRY.md).

Jeden dialog gry to jedna tabela z wierszami `dialog_config`, `project_info`,
`timeline` i `used_sound_bnk`. Numer dialogu to nazwa tabeli — nie trzeba go
zgadywać z sąsiedztwa bajtów, jak robił to `tools/timeline.py`.

`scena_z_tabeli` przechodzi całe drzewo `timeline` i zbiera **każde** pole,
którego wartość jest identyfikatorem tekstu (`czy_tekst`), więc nie zależy od
listy znanych typów węzłów. Znane typy dostają tylko czytelną etykietę:

    EntityTextSpan.text              kwestia (mówca = tor `EntityTrackGroup`)
    EntityTextSpan.overrided_name    nazwa mówcy podmieniona dla jednej kwestii
    EntityTrackGroup.entity_name     nazwa mówcy
    BlackSpan / BlackFrame / BlackScreenSpan .show_text   plansza na czarnym tle
    PersonInfoSpan.personal_name / .title                 wizytówka postaci

Mówca jest cechą **budowy** danych: kwestia leży w torze `EntityTextTrack`
wewnątrz grupy `EntityTrackGroup`, a grupa niesie `entity_tag`, `entity_type`,
`entity_no` i `entity_name`. Kwestia poza grupą dostaje `mowca = None` i jest
liczona osobno — nie zgadujemy.

Wariant płci bohatera też jest cechą budowy: tor z `valid_for_specific_type`
= prawda gra tylko dla jednej wersji bohatera, a jego `entity_type` mówi dla
której (1 — bohater, 2 — bohaterka; tory animacji o tych samych wartościach
mają akcje `…_male` i `…_female`). Kwestie z takich torów mają własne
identyfikatory tekstu, także wtedy, gdy chiński tekst obu wersji jest
jednakowy — dzięki temu polski przekład może mieć osobne formy rodzaju.
"""

from __future__ import annotations

from typing import Callable, Iterable

GRUPA = "EntityTrackGroup"
KWESTIA = "EntityTextSpan"
TYP_GRACZ = 1
WSPOLNY, BOHATER, BOHATERKA = 0, 1, 2

# (typ węzła, pole) -> rodzaj elementu
RODZAJE = {
    ("EntityTextSpan", "text"): "kwestia",
    ("BlackSpan", "show_text"): "plansza",
    ("BlackFrame", "show_text"): "plansza",
    ("BlackScreenSpan", "show_text"): "plansza",
    ("PersonInfoSpan", "personal_name"): "wizytowka_imie",
    ("PersonInfoSpan", "title"): "wizytowka_tytul",
}
# Pola, które są nazwą mówcy, a nie osobnym elementem sceny.
POLA_NAZWY = {("EntityTrackGroup", "entity_name"), ("EntityTextSpan", "overrided_name")}


def _liczba(value) -> float:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else 0.0


def scena_z_tabeli(numer: int, wiersze: dict, czy_tekst: Callable[[int], bool]) -> dict:
    """Zamień wiersze tabeli `dialog_timelines.<numer>` na rekord sceny.

    Zwraca słownik:
        dialog_no, projekt, nazwa, konfiguracja, ui_type, czas,
        obsada   lista grup: {tag, typ, entity_no, nazwa (id tekstu lub None), kwestii}
        elementy lista: {rodzaj, pole, text_id, mowca (indeks obsady lub None),
                         nazwa (id tekstu podmienionej nazwy lub None),
                         wariant (0 wspólny, 1 bohater, 2 bohaterka),
                         czas, kolejnosc, source_id}
        banki    lista banków dźwięku (wskazówka miejsca i postaci)
    Elementy są ułożone według czasu na osi, potem według `order`.
    """
    config = wiersze.get("dialog_config") or {}
    project = wiersze.get("project_info") or {}
    timeline = wiersze.get("timeline") or {}
    if not isinstance(config, dict) or not isinstance(project, dict) or not isinstance(timeline, dict):
        raise ValueError(f"dialog {numer}: nieoczekiwany typ wiersza")

    obsada: list[dict] = []
    elementy: list[dict] = []
    licznik = 0

    def walk(node, grupa: int | None, wariant: int) -> None:
        nonlocal licznik
        if isinstance(node, list):
            for item in node:
                walk(item, grupa, wariant)
            return
        if not isinstance(node, dict):
            return
        typ = node.get("Type")
        if typ != GRUPA and node.get("valid_for_specific_type") is True and node.get("entity_type") in (BOHATER, BOHATERKA):
            wariant = node["entity_type"]
        if typ == GRUPA:
            name = node.get("entity_name")
            obsada.append(
                {
                    "tag": node.get("entity_tag") if isinstance(node.get("entity_tag"), str) else "",
                    "typ": node.get("entity_type") if isinstance(node.get("entity_type"), int) else None,
                    "entity_no": node.get("entity_no") if isinstance(node.get("entity_no"), int) else 0,
                    "nazwa": name if _to_tekst(name, czy_tekst) else None,
                    "kwestii": 0,
                }
            )
            grupa = len(obsada) - 1
        for key, value in node.items():
            if isinstance(value, (dict, list)):
                walk(value, grupa, wariant)
                continue
            if not _to_tekst(value, czy_tekst) or (typ, key) in POLA_NAZWY:
                continue
            licznik += 1
            override = node.get("overrided_name") if typ == KWESTIA else None
            elementy.append(
                {
                    "rodzaj": RODZAJE.get((typ, key), "inne"),
                    "pole": f"{typ}.{key}",
                    "text_id": value,
                    "mowca": grupa if typ == KWESTIA else None,
                    "nazwa": override if _to_tekst(override, czy_tekst) else None,
                    "wariant": wariant,
                    "czas": _liczba(node.get("time")),
                    "kolejnosc": node.get("order") if isinstance(node.get("order"), int) else None,
                    "source_id": node.get("source_id") if isinstance(node.get("source_id"), int) else None,
                    "_n": licznik,
                }
            )
            if typ == KWESTIA and grupa is not None:
                obsada[grupa]["kwestii"] += 1

    walk(timeline, None, WSPOLNY)
    # `order` jest numeracją kwestii w całym dialogu; plansze go nie mają, więc
    # pierwszym kluczem jest czas, a `order` i kolejność w danych rozstrzygają remisy.
    elementy.sort(key=lambda e: (e["czas"], e["kolejnosc"] if e["kolejnosc"] is not None else -1, e["_n"]))
    for element in elementy:
        del element["_n"]

    banks = wiersze.get("used_sound_bnk")
    return {
        "dialog_no": numer,
        "projekt": project.get("project_name") if isinstance(project.get("project_name"), str) else None,
        "nazwa": timeline.get("name") if isinstance(timeline.get("name"), str) else None,
        "konfiguracja": {
            key: config[key]
            for key in ("id", "is_skip", "disable", "for_oversea", "oversea_src_dialog_no", "able_interrupt")
            if config.get(key) not in (None, False, 0)
        },
        "ui_type": timeline.get("ui_type") if isinstance(timeline.get("ui_type"), int) else None,
        "czas": _liczba(timeline.get("total_duration")),
        "obsada": obsada,
        "elementy": elementy,
        "banki": [bank for bank in banks if isinstance(bank, str)] if isinstance(banks, list) else [],
    }


def _to_tekst(value, czy_tekst: Callable[[int], bool]) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0xFFFFFFFF and czy_tekst(value)


def numery_dialogow(nazwy_tabel: Iterable[str]) -> list[int]:
    """Numery dialogów z nazw tabel `dialog_timelines.<numer>`, rosnąco."""
    numbers = []
    for name in nazwy_tabel:
        prefix, _, rest = name.partition(".")
        if prefix == "dialog_timelines" and rest.isdigit():
            numbers.append(int(rest))
    return sorted(numbers)
