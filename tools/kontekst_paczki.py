#!/usr/bin/env python3
"""Kontekst z indeksów MPK / czytanki dla pakietu tłumacza.

Ładuje wyłącznie metadane z `index/` (bez plików gry). Wynik jest używany
do kolejności i nagłówków w `tools/buduj_paczke.py`; format `klucz:` / `PL:`
się nie zmienia, więc zwrotka importuje się tak samo.
"""

from __future__ import annotations

import json
from pathlib import Path


def _jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    wiersze: list[dict] = []
    with path.open(encoding="utf-8") as handle:
        for linia in handle:
            if linia.strip():
                wiersze.append(json.loads(linia))
    return wiersze


def kolejnosc_cine(katalog: Path) -> dict[int, list[list[dict]]]:
    """Cutscena `no` → bloki kwestii w kolejności osi `.cine`."""
    wynik: dict[int, list[list[dict]]] = {}
    for wpis in _jsonl(Path(katalog) / "cutsceny_kolejnosc_kwestii.jsonl"):
        wynik[int(wpis["no"])] = wpis.get("bloki") or []
    return wynik


def listy_przy_scenach(katalog: Path) -> dict[int, list[int]]:
    """Dialog → numery listów otwieranych tuż po tej scenie (`listy_w_grafie`)."""
    przy: dict[int, list[int]] = {}
    zajete: set[int] = set()
    for wpis in _jsonl(Path(katalog) / "mpk" / "listy_w_grafie.jsonl"):
        try:
            no = int(wpis["no"])
        except (KeyError, TypeError, ValueError):
            continue
        po = wpis.get("po")
        if not isinstance(po, int) or no in zajete:
            continue
        zajete.add(no)
        przy.setdefault(po, []).append(no)
    return przy


def listy_envelop(ix) -> dict[str, dict]:
    """Wiersz `tasks_envelop_data` → klucze kolumn (`to` / `from` / `text` / …)."""
    kolumny: dict[str, int] = {}
    for i, wpis in enumerate(ix.zrodla or []):
        if isinstance(wpis, (list, tuple)) and wpis and wpis[0] == "tasks_envelop_data":
            kolumny[str(wpis[1])] = i
    if not kolumny:
        return {}
    indeksy = set(kolumny.values())
    wiersze: dict[str, dict] = {}
    for klucz, tekst in ix.teksty.items():
        w = tekst.w
        if not w or not isinstance(w[0], int) or w[0] not in indeksy:
            continue
        pole = next((nazwa for nazwa, nr in kolumny.items() if nr == w[0]), None)
        if not pole:
            continue
        rid = str(w[1])
        wpis = wiersze.setdefault(rid, {"id": rid, "klucze": []})
        wpis[pole] = klucz
        wpis["klucze"].append(klucz)
    return wiersze


def _nazwy_po_id(katalog: Path) -> dict[str, dict]:
    mapa: dict[str, dict] = {}
    for wpis in _jsonl(Path(katalog) / "nazwy.jsonl"):
        if wpis.get("id") is not None:
            mapa[str(wpis["id"])] = wpis
    return mapa


def poi_przy_scenach(katalog: Path) -> dict[int, str]:
    """Dialog → nazwa POI, który go odpala (`poi_storyline_sceny` + `poi.jsonl`)."""
    root = Path(katalog)
    poi_plik = root / "poi.jsonl"
    sceny_plik = root / "mpk" / "poi_storyline_sceny.jsonl"
    if not poi_plik.is_file() or not sceny_plik.is_file():
        return {}
    nazwy = _nazwy_po_id(root)
    ident: dict[int, object] = {}
    for wpis in _jsonl(poi_plik):
        try:
            ident[int(wpis["id"])] = wpis.get("nazwa") if wpis.get("nazwa") is not None else wpis.get("id")
        except (KeyError, TypeError, ValueError):
            continue

    def etykieta(surowa) -> str:
        if surowa is None:
            return ""
        if isinstance(surowa, str) and not surowa.isdigit():
            return surowa.strip()
        wpis = nazwy.get(str(surowa))
        if not wpis:
            return str(surowa)
        zh = (wpis.get("zh") or "").strip()
        en = (wpis.get("en") or "").strip()
        if zh and en and zh != en:
            return f"{zh} ({en})"
        return zh or en or str(surowa)

    wynik: dict[int, str] = {}
    for wpis in _jsonl(sceny_plik):
        if wpis.get("status") != "sceny":
            continue
        etyk = etykieta(ident.get(int(wpis["poi"]))) if wpis.get("poi") is not None else ""
        if not etyk:
            continue
        for scena in wpis.get("sceny") or []:
            wynik.setdefault(int(scena), etyk)
    return wynik


def bowu_story(katalog: Path) -> dict[str, list[str]]:
    """Numer hasła encyklopedii (`bowu`) → akty regionalne (`story`)."""
    mapa: dict[str, list[str]] = {}
    for wpis in _jsonl(Path(katalog) / "bowu_story.jsonl"):
        mapa[str(wpis["bowu"])] = [str(s) for s in wpis.get("story") or []]
    return mapa


def lokalizacje_bowu(ix, bowu: dict[str, list[str]]) -> dict[str, str]:
    """`bowu_no` → klucz tekstu `backing_area` (do `para()` w pakiecie)."""
    if not bowu:
        return {}
    story_klucz: dict[str, str] = {}
    for klucz, tekst in ix.teksty.items():
        if not tekst.w or len(tekst.w) < 2:
            continue
        zrodlo = ix.zrodlo(tekst)
        if not zrodlo or zrodlo[1] != "backing_area":
            continue
        story_klucz.setdefault(str(tekst.w[1]), klucz)
    wynik: dict[str, str] = {}
    for numer, stories in bowu.items():
        klucze = [story_klucz[s] for s in stories if s in story_klucz]
        if klucze:
            wynik[numer] = klucze[0]
    return wynik
