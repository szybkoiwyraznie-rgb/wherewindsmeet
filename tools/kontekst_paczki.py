#!/usr/bin/env python3
"""Kontekst z indeksów MPK / czytanki dla pakietu tłumacza.

Ładuje wyłącznie metadane z `index/` (bez plików gry). Wynik jest używany
do kolejności i nagłówków w `tools/buduj_paczke.py`; format `klucz:` / `PL:`
się nie zmienia, więc zwrotka importuje się tak samo.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
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


# --- rekordy widoków (jak karty czytanki: nazwa + pola, nie rozsypka po tabelach) ---

_NAZWA_KOL = re.compile(r"name|title|bowu|imie", re.I)
_WAGA_KOL = {
    "name": 0,
    "task_name": 0,
    "bowu_name": 0,
    "manual_name": 0,
    "group_name": 0,
    "talk_title[]": 1,
    "talk_title": 1,
    "title": 1,
    "locate_describe": 10,
    "backing_area": 10,
    "introduction_location": 10,
    "describe_str": 20,
    "describe": 20,
    "brief_describe_str": 21,
    "introduction": 22,
    "description": 23,
    "talk_content[]": 40,
    "talk_content": 40,
    "content": 41,
    "task_target_str": 50,
    "task_desc_str": 51,
}


def _nr_wiersza(wiersz: str) -> int:
    tekst = str(wiersz).lstrip("-")
    return int(tekst) if tekst.isdigit() else 0


@dataclass
class PoleRekordu:
    klucz: str
    tabela: str
    kolumna: str
    wiersz: str
    origin: int
    name_key: str | None = None

    def waga(self) -> tuple:
        return (_WAGA_KOL.get(self.kolumna, 70), _nr_wiersza(self.wiersz), self.kolumna, self.klucz)


@dataclass
class Rekord:
    """Jedno hasło: nazwa + wszystkie pola tego samego wiersza tabeli."""

    grupa: tuple
    kategoria: str
    nazwa_klucz: str | None
    tabela_nazwy: str
    pola: list[PoleRekordu] = field(default_factory=list)


def _domknij_rekord(rec: Rekord, kategoria_fn) -> None:
    rec.pola = list({p.klucz: p for p in rec.pola}.values())
    rec.pola.sort(key=lambda p: p.waga())
    for pole in rec.pola:
        if _NAZWA_KOL.search(pole.kolumna):
            rec.nazwa_klucz = pole.klucz
            rec.tabela_nazwy = pole.tabela.removesuffix("__grey")
            rec.kategoria = kategoria_fn(pole.tabela)
            return
    if rec.nazwa_klucz is None:
        for pole in rec.pola:
            if pole.name_key:
                rec.nazwa_klucz = pole.name_key
                break


def pogrupuj_rekordy(pozycje: list[dict], kategoria_fn) -> dict[str, list[Rekord]]:
    """Złóż wpisy widoków w rekordy.

    `pozycja`: klucz, tabela, kolumna, wiersz, origin, name_key.
    Wiersz tabeli zostaje razem (nazwa + pola tego rekordu). Homonimy
    (ten sam napis, inny wiersz / inna tabela) zostają osobno — `dotyczy:`
    i tak pokazuje nazwę. Nie spinamy bytów tylko dlatego, że dzielą string nazwy.
    """
    kubełki: dict[tuple, Rekord] = {}
    for poz in pozycje:
        tabela = str(poz["tabela"])
        baza = tabela.removesuffix("__grey")
        wiersz = str(poz["wiersz"])
        if "#" in wiersz:
            _, _, wiersz = wiersz.rpartition("#")
        kolumna = str(poz["kolumna"] or "")
        name_key = poz.get("name_key") or None
        if not name_key and _NAZWA_KOL.search(kolumna):
            name_key = poz["klucz"]
        grupa = ("r", baza, wiersz)
        rec = kubełki.get(grupa)
        if rec is None:
            rec = Rekord(grupa=grupa, kategoria=kategoria_fn(tabela), nazwa_klucz=None, tabela_nazwy=baza)
            kubełki[grupa] = rec
        rec.pola.append(
            PoleRekordu(
                klucz=poz["klucz"],
                tabela=tabela,
                kolumna=kolumna,
                wiersz=wiersz,
                origin=int(poz["origin"]),
                name_key=name_key,
            )
        )
    for rec in kubełki.values():
        _domknij_rekord(rec, kategoria_fn)

    po_widoku: dict[str, list[Rekord]] = {}
    for rec in kubełki.values():
        po_widoku.setdefault(rec.kategoria, []).append(rec)
    for recs in po_widoku.values():
        recs.sort(key=lambda r: (r.pola[0].waga() if r.pola else (99, 0, "", "")))
    return po_widoku


def bloki_zadan(ix, pl: dict[str, str] | None = None) -> list[tuple[str, list[str]]]:
    """Tytuł bloku → klucze nazw zadań w kolejności łańcucha gry."""
    try:
        from tools import kolejnosc_zadan
    except ImportError:  # pragma: no cover
        import kolejnosc_zadan  # type: ignore[no-redef]
    return [(blok.tytul, list(blok.klucze)) for blok in kolejnosc_zadan.plan(ix, pl or {})]


def uszereguj_rekordy_zadan(rekordy: list[Rekord], bloki: list[tuple[str, list[str]]]) -> list[tuple[str | None, Rekord]]:
    """Rekordy zadań z nagłówkiem bloku (łańcuch gry), potem reszta."""
    po_nazwie: dict[str, list[Rekord]] = {}
    for rec in rekordy:
        if rec.nazwa_klucz:
            po_nazwie.setdefault(rec.nazwa_klucz, []).append(rec)
    uzyte: set[int] = set()
    out: list[tuple[str | None, Rekord]] = []
    for tytul, klucze in bloki:
        pierwszy = True
        for klucz in klucze:
            for rec in po_nazwie.get(klucz, ()):
                if id(rec) in uzyte:
                    continue
                uzyte.add(id(rec))
                out.append((tytul if pierwszy else None, rec))
                pierwszy = False
    for rec in rekordy:
        if id(rec) in uzyte:
            continue
        uzyte.add(id(rec))
        out.append((None, rec))
    return out
