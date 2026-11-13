#!/usr/bin/env python3
"""Generator polskich czytanek `.md` i archiwum `WWM_CZYTANKI_PL.zip` dla Where Winds Meet.

Trzyplikowy zestaw czytelniczy dopasowany do korpusu Where Winds Meet:
- `README.md` — metryczka edycji, pokrycie tłumaczeń oraz spis ponumerowanych epizodów,
- `epizody.md` — czysty, nieprzerwany scenariusz fabularny (Prolog, Wątek Główny,
  zadania poboczne i sekwencje cutscen) z jednolitą numeracją `Epizod E` / `Scena E.S`,
  narracjami otwierającymi z gry, wyborami gracza (ze wskazaniem docelowych scen),
  rozpoznanymi mówcami cutscen oraz nazwą bohatera `You Xia` (z zaznaczeniem przebrań),
- `kontekst_scen.md` — samowystarczalny towarzysz kontekstowy o lustrzanych
  nagłówkach `Epizod E` / `Scena E.S`, skupiający przy każdej scenie powiązany
  kontekst z całej bazy `index/`: opisy NPC z obsady, karty encyklopedii postaci
  (bez spoilerów dalszych wspomnień), głosy, relacje, bossów, frakcje i sekty,
  lokacje/podobszary/poematy miejsc/ekrany ładowania, kalendarium, księgi,
  zapiski regionalne, poszlaki, listy, przedmioty, sztuki walki oraz wskazówki UI,
  a na końcu dalsze wpisy spotkanych postaci odblokowywane później w grze,
- `dodatkowe.md` — pełny zbiór pozostałego materiału ze świata gry poza scenami,
  sekwencjami i przypisanym kontekstem (bohaterowie, zadania, przedmioty,
  encyklopedia, lokacje, walka, rozmowy/komunikaty, interfejs i reszta korpusu),
  podzielony na rodzaje materiału do wygodnego wyszukiwania brakujących haseł.

Przykłady:
    python3 tools/buduj_czytanki.py \\
        --magazyn tlumaczenie \\
        --wyj-katalog dist/czytanki \\
        --wyj-zip dist/WWM_CZYTANKI_PL.zip

    python3 tools/buduj_czytanki.py \\
        --zwrotka zwrotka_czesc1.zip \\
        --tylko-zwrotka \\
        --zakres przetlumaczone \\
        --wyj-katalog dist/czytanki_podglad
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import textwrap
import zipfile

try:
    from tools import buduj_paczke as bp
    from tools import import_zwrotki
    from tools import indeks as indeks_mod
    from tools import kontekst_cutscen as kc
    from tools import powiazania_czytanek as pc
    from tools import tlumaczenie as magazyn_mod
    from tools import uklad_scen
    from tools import wypisz
except ImportError:  # uruchomienie jako skrypt
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from tools import buduj_paczke as bp
    from tools import import_zwrotki
    from tools import indeks as indeks_mod
    from tools import kontekst_cutscen as kc
    from tools import powiazania_czytanek as pc
    from tools import tlumaczenie as magazyn_mod
    from tools import uklad_scen
    from tools import wypisz

FORMAT = "wwm-czytanki-v2"
STALA_DATA_ZIP = (2026, 1, 1, 0, 0, 0)
DOMYSLNY_LIMIT_BAJTOW = 0
MAX_SZEROKOSC_TABELI = 120
ZAKRES_PROLOG_TM = kc.ZAKRES_PROLOG_TM

NAZWY_TYPOW_PL = {
    1: "Wątek główny",
    2: "Przewodnik i wskazówki",
    3: "Spotkania",
    4: "Wyprawy i próby",
    6: "Zlecenia",
    8: "Dziedzictwo Jianghu",
    11: "Krzywdy i dochodzenia",
    12: "Kampanie",
    13: "Eksploracja",
    14: "Krzywdy i dochodzenia (dodatkowe)",
    15: "Sprawy świata",
    16: "Festiwale i wydarzenia",
    17: "Posiadłość",
    18: "Towarzysze",
    19: "Codzienne przysługi",
    21: "Wydarzenia specjalne",
    300: "Warunki wstępne spotkań",
    None: "Zadania bez kategorii",
}

_RE_ODNOSNIK = re.compile(r"<([^<>\n|]+)(?:\|[^|<>\n]*)+>")
_RE_TAG_XML = re.compile(r"</?(?:LINK|IMAGE|COLOR|FONT|SIZE|STYLE|OUTLINE|TEXT)(?:\s[^<>\n]*)?>", re.I)
_RE_KOLOR = re.compile(r"#(?:[0-9a-fA-F]{6}|[A-Z])")
_RE_WIELE_SPACJI = re.compile(r"[ \t]{2,}")
_RE_PUSTE_LINIE = re.compile(r"\n{3,}")

_GENERYCZNE_NAZWY_GRACZA_ZH = kc.GENERYCZNE_NAZWY_GRACZA_ZH
_GENERYCZNE_NAZWY_GRACZA_TXT = kc.GENERYCZNE_NAZWY_GRACZA_TXT
_MOWCY_CUTSCEN_EN_IGNORUJ = kc.MOWCY_CUTSCEN_EN_IGNORUJ
_MOWCY_CUTSCEN_ZH_NA_EN = kc.MOWCY_CUTSCEN_ZH_NA_EN
_MOWCY_CUTSCEN_ZH_DO_TLUMACZENIA = kc.MOWCY_CUTSCEN_ZH_DO_TLUMACZENIA
_MOWCY_ROLE_PL = kc.MOWCY_ROLE_PL

_norm_cut_zh = kc.norm_cut_zh
_wvpv_pid = kc.wvpv_pid


class CzytankiError(Exception):
    """Błąd przygotowania czytanek WWM."""


def oczysc_tekst(text: str, *, jedna_linia: bool = False) -> str:
    """Usuń tagi kolorów NetEase, tagi XML i surowe parametry linków z tekstu gry."""
    if not text:
        return ""
    cleaned = text.replace("\r\n", "\n").replace("\r", "\n").replace("\t", " ")
    for _ in range(4):
        updated = _RE_ODNOSNIK.sub(r"\1", cleaned)
        if updated == cleaned:
            break
        cleaned = updated
    cleaned = _RE_TAG_XML.sub("", cleaned)
    cleaned = _RE_KOLOR.sub("", cleaned)
    lines = [_RE_WIELE_SPACJI.sub(" ", line).strip() for line in cleaned.split("\n")]
    if jedna_linia:
        return " ".join(part for part in lines if part).strip()
    joined = "\n".join(lines)
    joined = _RE_PUSTE_LINIE.sub("\n\n", joined)
    return joined.strip()


def _escapuj_komorke(text: str, *, jedna_linia: bool = False) -> str:
    cleaned = text.replace("\r\n", "\n").replace("\r", "\n").replace("\t", " ")
    lines = [_RE_WIELE_SPACJI.sub(" ", line).strip() for line in cleaned.split("\n")]
    if jedna_linia:
        joined = " ".join(part for part in lines if part)
    else:
        joined = "\n".join(lines)
        joined = _RE_PUSTE_LINIE.sub("\n\n", joined)
    return joined.replace("|", "\\|").strip()


def formatuj_tabele(
    naglowki: list[str],
    wiersze: list[list[str]],
    *,
    max_szerokosc: int = MAX_SZEROKOSC_TABELI,
) -> list[str]:
    """Zbuduj tabelę Markdown zawijaną do `max_szerokosc` znaków bez `<br>` (wiersze kontynuacji)."""
    if not naglowki or not wiersze:
        return []
    cols = len(naglowki)
    norm_headers = [_escapuj_komorke(h, jedna_linia=True) for h in naglowki]
    norm_rows: list[list[str]] = []
    for row in wiersze:
        padded = list(row[:cols]) + [""] * max(0, cols - len(row))
        norm_rows.append([_escapuj_komorke(str(cell)) for cell in padded])

    overhead = 3 * cols + 1
    budget = max(cols * 8, max_szerokosc - overhead)

    natural_widths = []
    for idx in range(cols):
        cell_max = max(
            [len(norm_headers[idx])]
            + [max((len(part) for part in row[idx].split("\n")), default=0) for row in norm_rows]
        )
        natural_widths.append(max(len(norm_headers[idx]), min(cell_max, budget)))

    widths = list(natural_widths)
    total = sum(widths)
    if total > budget:
        longest_tokens = [
            max(
                [len(norm_headers[i])]
                + [max((len(tok) for tok in row[i].split()), default=0) for row in norm_rows]
            )
            for i in range(cols)
        ]
        soft_floor = [
            min(natural_widths[i], max(len(norm_headers[i]), min(42, max(longest_tokens[i], 24))))
            for i in range(cols)
        ]
        if sum(soft_floor) <= budget:
            min_w = soft_floor
        else:
            min_w = [min(natural_widths[i], max(len(norm_headers[i]), 8)) for i in range(cols)]
        if sum(min_w) >= budget:
            widths = [max(6, budget // cols) for _ in range(cols)]
        else:
            widths = list(min_w)
            rem = budget - sum(widths)
            flex = [max(0, natural_widths[i] - widths[i]) for i in range(cols)]
            flex_sum = sum(flex)
            if flex_sum > 0:
                for i in range(cols):
                    widths[i] += (rem * flex[i]) // flex_sum
                leftover = budget - sum(widths)
                for i in sorted(range(cols), key=lambda k: flex[k], reverse=True):
                    if leftover <= 0:
                        break
                    widths[i] += 1
                    leftover -= 1

    out: list[str] = []
    out.append("| " + " | ".join(norm_headers[i].ljust(widths[i]) for i in range(cols)) + " |")
    out.append("| " + " | ".join("-" * max(3, widths[i]) for i in range(cols)) + " |")

    for row in norm_rows:
        wrapped_cols: list[list[str]] = []
        for i in range(cols):
            w = max(6, widths[i])
            parts: list[str] = []
            for para in row[i].split("\n"):
                para = para.strip()
                if not para:
                    continue
                parts.extend(
                    textwrap.wrap(
                        para,
                        width=w,
                        break_long_words=True,
                        break_on_hyphens=False,
                    )
                    or [""]
                )
            wrapped_cols.append(parts or [""])
        max_lines = max(len(c) for c in wrapped_cols)
        for line_idx in range(max_lines):
            cells = []
            for col_idx in range(cols):
                val = wrapped_cols[col_idx][line_idx] if line_idx < len(wrapped_cols[col_idx]) else ""
                cells.append(val.ljust(widths[col_idx]))
            out.append("| " + " | ".join(cells) + " |")
    return out


class ZrodloPL:
    """Warstwa odczytu wyłącznie polskich przekładów z magazynu + wariantów."""

    jest_podgladem_en = False

    def __init__(self, ix: indeks_mod.Indeks, magazyn: magazyn_mod.Magazyn, *, tylko_klucze: set[str] | None = None):
        self.ix = ix
        self.magazyn = magazyn
        self.tylko_klucze = tylko_klucze

    def ma(self, slot: str | None) -> bool:
        return self.tekst(slot) is not None

    def tekst(self, slot: str | None, *, jedna_linia: bool = False) -> str | None:
        if not slot:
            return None
        if self.tylko_klucze is not None and slot not in self.tylko_klucze:
            if not (slot.startswith("@") and self.ix.warianty.get(slot[1:], {}).get("k") in self.tylko_klucze):
                return None
        done = self.magazyn.przeklad(slot)
        if done is None and slot.startswith("@"):
            var = self.ix.warianty.get(slot[1:])
            if var and var.get("k"):
                if self.tylko_klucze is None or var["k"] in self.tylko_klucze:
                    done = self.magazyn.przeklad(var["k"])
        if done is None:
            return None
        cleaned = oczysc_tekst(done, jedna_linia=jedna_linia)
        return cleaned if cleaned else None

    def klucz_bazowy(self, slot: str) -> str:
        if slot.startswith("@"):
            var = self.ix.warianty.get(slot[1:])
            if var and var.get("k"):
                return var["k"]
        return slot


class ZrodloPodgladuEN:
    """Jawny tryb podglądu formy czytanek w języku angielskim (wyłącznie z flagą `--podglad-en`)."""

    jest_podgladem_en = True

    def __init__(self, ix: indeks_mod.Indeks):
        self.ix = ix

    def ma(self, slot: str | None) -> bool:
        return self.tekst(slot) is not None

    def tekst(self, slot: str | None, *, jedna_linia: bool = False) -> str | None:
        if not slot:
            return None
        val = self.ix.en(slot)
        if not val and slot.startswith("@"):
            var = self.ix.warianty.get(slot[1:])
            if var and var.get("k"):
                val = self.ix.en(var["k"])
        if not val:
            return None
        cleaned = oczysc_tekst(val, jedna_linia=jedna_linia)
        return cleaned if cleaned else None

    def klucz_bazowy(self, slot: str) -> str:
        if slot.startswith("@"):
            var = self.ix.warianty.get(slot[1:])
            if var and var.get("k"):
                return var["k"]
        return slot


class _RejestratorZrodla:
    """Przeźroczysty wrapper źródła PL/EN śledzący klucze faktycznie wypisane do plików czytanek."""

    def __init__(self, baza):
        self._baza = baza
        self.jest_podgladem_en = getattr(baza, "jest_podgladem_en", False)
        self.magazyn = getattr(baza, "magazyn", None)
        self.tylko_klucze = getattr(baza, "tylko_klucze", None)
        self._stos: list[set[str]] = []

    @contextmanager
    def zbieraj(self, cel: set[str]):
        self._stos.append(cel)
        try:
            yield cel
        finally:
            self._stos.pop()

    def zanotuj(self, slot: str | None) -> None:
        if slot and self._stos:
            self._stos[-1].add(self._baza.klucz_bazowy(slot))

    def ma(self, slot: str | None) -> bool:
        return self._baza.ma(slot)

    def tekst(self, slot: str | None, *, jedna_linia: bool = False) -> str | None:
        val = self._baza.tekst(slot, jedna_linia=jedna_linia)
        if slot and val is not None:
            self.zanotuj(slot)
        return val

    def klucz_bazowy(self, slot: str) -> str:
        return self._baza.klucz_bazowy(slot)


def _naturalny(value: str):
    return pc._naturalny(value)


@dataclass
class _Scena:
    uid: str
    epizod_nr: int
    scena_nr: int
    tytul: str
    rodzaj: str  # "dialog" | "przerywnik" | "dziennik" | "intro" | "text_msg" | "film"
    dialog_no: int | None = None
    miejsce_ukladu: object | None = None
    zadanie_id: int | None = None
    przerywnik_no: int | None = None
    powtorka_row: dict | None = None
    cut_moment: str = ""
    segment: dict | None = None
    intro_rows: list[dict] = field(default_factory=list)
    film_rows: list[dict] = field(default_factory=list)
    film_id: int | None = None
    tekst_zh_do_skanu: str = ""
    przestrzenie: set[int] = field(default_factory=set)
    linie_skryptu: list[str] = field(default_factory=list)
    mowcy_cutsceny: list[tuple[str | None, str | None]] = field(default_factory=list)
    obsada_dodatkowa: list[str] = field(default_factory=list)
    uzyte_klucze: set[str] = field(default_factory=set)
    done: int = 0
    total: int = 0
    pokaz_zadanie_info: bool = False

    @property
    def etykieta_krotka(self) -> str:
        return f"Scena {self.epizod_nr}.{self.scena_nr}"

    @property
    def naglowek(self) -> str:
        return f"Scena {self.epizod_nr}.{self.scena_nr} — {self.tytul}"


@dataclass
class _Epizod:
    nr: int
    kategoria: str  # "prolog" | "watek_glowny" | "poboczne" | "cutsceny" | "otoczenie"
    tytul: str
    typ_zadania: int | None = None
    grupa: int | None = None
    projekt: str | None = None
    tlo_klucz: tuple | None = None
    notka_kategorii: str = ""
    sceny: list[_Scena] = field(default_factory=list)
    zadania_ids: list[int] = field(default_factory=list)
    done: int = 0
    total: int = 0


@dataclass
class ZbudowanyPlik:
    nazwa: str
    tytul: str
    opis: str
    linie: list[str]
    statystyka: dict


class BudowniczyCzytanek:
    """Składa trzyplikowy zestaw czytanek WWM (`epizody.md` + `kontekst_scen.md` + `dodatkowe.md`) z `index/` oraz przekładów."""

    def __init__(
        self,
        ix: indeks_mod.Indeks,
        pl: ZrodloPL,
        *,
        zakres: str = "przetlumaczone",
        plec: str = "oba",
        z_otoczeniem: bool = False,
        tylko_watek_glowny: bool = False,
        wersja: str = "v1",
    ):
        if zakres not in ("przetlumaczone", "kompletne-rozdzialy", "wszystko"):
            raise CzytankiError(f"nieznany zakres: {zakres!r}")
        if plec not in ("bohater", "bohaterka", "oba"):
            raise CzytankiError(f"nieznana opcja --plec: {plec!r}")
        self.ix = ix
        self._rejestr = _RejestratorZrodla(pl)
        self.pl = self._rejestr
        self.zakres = zakres
        self.plec = plec
        self.z_otoczeniem = z_otoczeniem
        self.tylko_watek_glowny = tylko_watek_glowny
        self.wersja = wersja
        self.uklad = uklad_scen.uloz(ix)
        self._przygotuj_indeksy()

    def _przygotuj_indeksy(self) -> None:
        ix = self.ix
        self.baza = pc.zbuduj_baze(ix)
        self.tabele = self.baza.tabele
        self.encyklopedia_po_kluczu = self.baza.encyklopedia_po_kluczu
        self.encyklopedia_po_id = self.baza.encyklopedia_po_id
        self.encyklopedia_po_en = self.baza.encyklopedia_po_en

        # Słowniki nazw i lokalnych opisów NPC do rozwiązywania mówców i obsady
        self.nazwa_po_tekscie: dict[str, str] = {}
        self.klucz_nazwy_po_en: dict[str, str] = {}
        wvpv_raw: dict[str, str] = {}
        for kl, text in ix.teksty.items():
            zr = ix.zrodlo(text)
            if text.zrodlo:
                if text.zrodlo not in self.nazwa_po_tekscie and zr and any(p in zr[1] for p in ("name", "title", "nazwa")):
                    self.nazwa_po_tekscie[text.zrodlo] = kl
                en_val = (ix.en(kl) or "").strip()
                if en_val and len(en_val) <= 64 and zr and (
                    zr[0] in ("entity_billboard", "world_view_person_info", "cutscene_person_info_config", "avatars")
                    or any(p in zr[1] for p in ("name", "title", "nazwa"))
                ):
                    if en_val not in self.klucz_nazwy_po_en or zr[0] in ("entity_billboard", "world_view_person_info", "cutscene_person_info_config"):
                        self.klucz_nazwy_po_en[en_val] = kl
            if zr and zr[0] == "world_view_person_voice" and zr[1] == "description" and text.zrodlo:
                wvpv_raw[zr[2]] = text.zrodlo

        # Zbiorczy słownik opisów/tytułów wyłącznie dla wiarygodnych unikalnych postaci z `ix.postacie`
        self.npc_tytul_po_nazwie: dict[str, str] = {}
        self.npc_opis_po_nazwie: dict[str, str] = {}
        opisy_per_klucz: dict[str, set[str]] = defaultdict(set)
        tytuly_per_klucz: dict[str, set[str]] = defaultdict(set)
        for prow in ix.postacie.values():
            nk = prow.get("n")
            if not nk:
                continue
            zh_n = pc._oczysc_do_dopasowania(ix.zh(nk))
            if not zh_n or zh_n in pc.GENERYCZNE_ROLE_ZH or zh_n.lower() in pc.GENERYCZNE_ROLE_LAT:
                continue
            if prow.get("t"):
                tytuly_per_klucz[nk].add(prow["t"])
            if prow.get("o"):
                opisy_per_klucz[nk].add(prow["o"])
        for nk, vals in tytuly_per_klucz.items():
            if len(vals) == 1:
                self.npc_tytul_po_nazwie[nk] = next(iter(vals))
        for nk, vals in opisy_per_klucz.items():
            if len(vals) == 1:
                self.npc_opis_po_nazwie[nk] = next(iter(vals))

        # Wybory po dialogu, streszczenia i powtórki cutscen
        self.wybory_po: dict[int, list[dict]] = defaultdict(list)
        for row in ix.wybory.values():
            for dialog_no in row.get("po_dialogach", ()):
                self.wybory_po[dialog_no].append(row)
        for rows in self.wybory_po.values():
            rows.sort(key=lambda r: (r.get("pytanie", 0), r.get("krok", 0)))

        self.streszczenia_grupy: dict[int | None, list[dict]] = defaultdict(list)
        for row in ix.streszczenia:
            if row.get("tekst"):
                self.streszczenia_grupy[row.get("grupa")].append(row)

        all_section_tasks = {tid for sec in self.uklad.sekcje for tid in sec.zadania}
        self.powtorka_po_no: dict[int, dict] = {}
        self.powtorki_po_zadaniu: dict[int, list[dict]] = defaultdict(list)
        self.powtorki_po_grupie: dict[int, list[dict]] = defaultdict(list)
        for row in ix.cutsceny_kontekst.get("powtorka", ()):
            pno = row.get("no")
            if pno is not None:
                self.powtorka_po_no[pno] = row
            tno = row.get("task_no")
            fno = row.get("finish_task")
            if tno:
                self.powtorki_po_zadaniu[tno].append(row)
            if fno and fno != tno and (not tno or tno not in all_section_tasks):
                self.powtorki_po_zadaniu[fno].append(row)
            if row.get("grupa"):
                self.powtorki_po_grupie[row["grupa"]].append(row)

        self.przerywniki_w_zadaniach: set[int] = set()
        for task in ix.zadania.values():
            for lst in (task.get("przerywniki") or {}).values():
                self.przerywniki_w_zadaniach.update(lst)

        (
            self.glos_wvpv_dokladny,
            self.mowca_napisow_exact,
            self.mowca_napisow_dlugie,
        ) = kc.zbuduj_indeksy_mowcow(ix, wvpv_raw, self.encyklopedia_po_id)

    # -------------------------------------------------------- pomocniki językowe PL-only

    def _tekst(self, slot: str | None, *, fallback_label: str = "", jedna_linia: bool = False) -> str | None:
        val = self.pl.tekst(slot, jedna_linia=jedna_linia)
        if val is not None:
            return val
        if self.zakres == "wszystko" and slot:
            if fallback_label:
                return f"[Brak polskiego tekstu ({fallback_label}): {slot}]"
            return f"[Brak polskiego tekstu: {slot}]"
        return None

    def _nazwa_typu(self, typ: int | None) -> str:
        row = self.ix.typy_zadan.get(typ)
        if row and row.get("nazwa"):
            pl_name = self.pl.tekst(row["nazwa"], jedna_linia=True)
            if pl_name:
                return pl_name
        return NAZWY_TYPOW_PL.get(typ, f"Kategoria zadań #{typ}")

    def _nazwa_grupy(self, grupa: int | None) -> str:
        if grupa is None:
            return "Zadania bez przypisanego rozdziału"
        row = self.ix.grupy.get(grupa) or {}
        parts = []
        for field_name in ("numer_tytulu", "tytul", "nazwa"):
            val = self.pl.tekst(row.get(field_name), jedna_linia=True)
            if val:
                parts.append(val)
        if parts:
            return " — ".join(parts)
        return f"Rozdział #{grupa} [brak polskiego tytułu]"

    def _nazwa_zadania(self, tid: int) -> str:
        row = self.ix.zadania.get(tid) or {}
        val = self.pl.tekst(row.get("nazwa"), jedna_linia=True)
        if val:
            return val
        if self.zakres == "wszystko":
            return f"Zadanie #{tid} [brak polskiego tytułu]"
        return f"Zadanie #{tid}"

    def _miejsce(self, space_id: int | None) -> str | None:
        if space_id is None:
            return None
        row = self.ix.miejsca.get(space_id) or {}
        if row.get("nazwa"):
            pl_val = self.pl.tekst(row["nazwa"], jedna_linia=True)
            if pl_val:
                return pl_val
        return None

    def _znajdz_osobe(self, scena: dict, osoba_id) -> list | None:
        obsada = scena.get("o") or ()
        if isinstance(osoba_id, int) and 0 <= osoba_id < len(obsada):
            return obsada[osoba_id]
        for person in obsada:
            if person[0] == osoba_id:
                return person
        return None

    def _dane_osoby_w_scenie(self, person: list) -> tuple[str | None, str | None, str | None, str | None]:
        """Zwróć `(name_kl, tyt_kl, opis_kl, role_kind)` preferując autorytatywne `ix.postacie[entity_no]`."""
        role_kind = person[1] if len(person) > 1 else None
        entity_no = person[2] if len(person) > 2 and isinstance(person[2], int) else None
        prow = self.ix.postacie.get(entity_no) if entity_no else None
        raw_n = person[3] if len(person) > 3 else None
        raw_t = person[4] if len(person) > 4 and person[4] else None
        raw_o = person[5] if len(person) > 5 and person[5] else None
        if prow and prow.get("n"):
            name_kl = prow["n"]
            zgodny_raw = (raw_n is None or raw_n == name_kl)
            tyt_kl = prow.get("t") or (raw_t if zgodny_raw else None)
            opis_kl = prow.get("o") or (raw_o if zgodny_raw else None)
            return name_kl, tyt_kl, opis_kl, role_kind
        return raw_n, raw_t, raw_o, role_kind

    def _mowca(self, scena: dict, osoba_id, przebranie_klucz: str | None = None) -> str:
        person = self._znajdz_osobe(scena, osoba_id)
        if person is not None:
            name_key, _, _, role_kind = self._dane_osoby_w_scenie(person)
            en_name = (self.ix.en(name_key) or "").strip() if name_key else ""
            zh_name = (self.ix.zh(name_key) or "").strip() if name_key else ""
            pl_name = self.pl.tekst(name_key, jedna_linia=True) if name_key else None
            czy_gracz = (
                role_kind == "gracz"
                or role_kind == 1
                or (person[0] in ("我", "player", "主角"))
                or zh_name in _GENERYCZNE_NAZWY_GRACZA_ZH
                or en_name.lower() in _GENERYCZNE_NAZWY_GRACZA_TXT
                or (pl_name or "").lower() in _GENERYCZNE_NAZWY_GRACZA_TXT
            )
            if czy_gracz:
                if przebranie_klucz:
                    przebr = self._tekst(przebranie_klucz, fallback_label="przebrania", jedna_linia=True)
                    if przebr:
                        return f"You Xia ({przebr})"
                if pl_name and not (
                    zh_name in _GENERYCZNE_NAZWY_GRACZA_ZH
                    or en_name.lower() in _GENERYCZNE_NAZWY_GRACZA_TXT
                    or pl_name.lower() in _GENERYCZNE_NAZWY_GRACZA_TXT
                ):
                    return f"You Xia ({pl_name})"
                return "You Xia"
            if pl_name:
                return pl_name
            if self.zakres == "wszystko" and name_key:
                return f"[Brak polskiej nazwy mówcy: {name_key}]"
            return f"Postać ({osoba_id})"
        return "You Xia" if osoba_id in ("ja", 0) else f"Postać ({osoba_id})"

    def _tlumacz_mowce_cutsceny(self, en_name: str) -> str | None:
        if not en_name:
            return None
        if en_name in ("You Xia", "Me", "Player", "Main Character"):
            return "You Xia"
        if getattr(self.pl, "jest_podgladem_en", False):
            return en_name
        entry = self.encyklopedia_po_en.get(en_name)
        if entry and entry.get("nazwa"):
            pl_val = self.pl.tekst(entry["nazwa"], jedna_linia=True)
            if pl_val:
                return pl_val
        kl = self.klucz_nazwy_po_en.get(en_name)
        if kl:
            pl_val = self.pl.tekst(kl, jedna_linia=True)
            if pl_val:
                return pl_val
        if en_name in _MOWCY_ROLE_PL:
            return _MOWCY_ROLE_PL[en_name]
        for zh_tag, mapped_en in (*_MOWCY_CUTSCEN_ZH_NA_EN.items(), *_MOWCY_CUTSCEN_ZH_DO_TLUMACZENIA.items()):
            if mapped_en == en_name and zh_tag in self.nazwa_po_tekscie:
                pl_val = self.pl.tekst(self.nazwa_po_tekscie[zh_tag], jedna_linia=True)
                if pl_val:
                    return pl_val
        return None

    def _klucz_mowcy_cutsceny(self, en_name: str | None) -> str | None:
        if not en_name or en_name in ("You Xia", "Me", "Player", "Main Character"):
            return None
        entry = self.encyklopedia_po_en.get(en_name)
        if entry and entry.get("nazwa"):
            return entry["nazwa"]
        return self.klucz_nazwy_po_en.get(en_name)

    def _rozwiaz_mowce_napisu(self, row: dict, txt: str, *, ignoruj_audio: bool = False) -> tuple[str | None, str, bool, str | None]:
        kl = row["k"]
        zh = self.ix.teksty[kl].zrodlo
        en_raw = self.ix.en(kl) or ""
        sp_en = kc.rozwiaz_mowce_en(
            row,
            zh,
            en_raw,
            self.glos_wvpv_dokladny,
            self.mowca_napisow_exact,
            self.mowca_napisow_dlugie,
            ignoruj_audio=ignoruj_audio,
        )
        mowca_out = self._tlumacz_mowce_cutsceny(sp_en) if sp_en else None
        cleaned_txt, detected_sp, czy_gracz = kc.wyczysc_prefiks_mowcy(txt, sp_en, mowca_out)
        used_en = sp_en or detected_sp
        if not mowca_out and detected_sp:
            if detected_sp == "You Xia":
                mowca_out = "You Xia"
            else:
                mowca_out = self._tlumacz_mowce_cutsceny(detected_sp) or (
                    detected_sp if getattr(self.pl, "jest_podgladem_en", False) else None
                )
        return mowca_out, cleaned_txt, czy_gracz, used_en

    def _pasuje_plec_elementu(self, element: list) -> tuple[bool, str]:
        if len(element) <= 3 or not element[3]:
            return True, ""
        w = element[3]
        if w == 1:
            if self.plec == "bohaterka":
                return False, ""
            return True, "[♂ Bohater] " if self.plec == "oba" else ""
        if w == 2:
            if self.plec == "bohater":
                return False, ""
            return True, "[♀ Bohaterka] " if self.plec == "oba" else ""
        return True, ""

    def _slot_sceny(self, element: list) -> str:
        return "@" + element[4] if len(element) > 4 and element[3] else element[2]

    def _stat_slotow(self, sloty: list[str]) -> tuple[int, int]:
        unikatowe: list[str] = []
        seen = set()
        for slot in sloty:
            if not slot or slot in seen:
                continue
            seen.add(slot)
            key = self.pl.klucz_bazowy(slot)
            text = self.ix.teksty.get(key)
            if text is not None and text.zrodlo.strip():
                unikatowe.append(slot)
        done = sum(1 for slot in unikatowe if self.pl.ma(slot))
        return done, len(unikatowe)

    def _ma_dopuszczalne_pokrycie(self, done: int, total: int) -> bool:
        if total == 0:
            return False
        if self.zakres == "wszystko":
            return True
        if self.zakres == "kompletne-rozdzialy":
            return done == total
        return done > 0

    def _tytul_powtorki(self, cut_no: int) -> str | None:
        prow = self.powtorka_po_no.get(cut_no)
        if not prow:
            return None
        pn = self.pl.tekst(prow.get("nazwa"), jedna_linia=True)
        pr = self.pl.tekst(prow.get("rozdzial"), jedna_linia=True)
        psp_id = prow.get("przestrzen")
        psp = self._miejsce(psp_id) if psp_id not in (None, 501, 502, 504) else None
        czesci = [c for c in (pn, pr, psp) if c]
        return " — ".join(czesci) if czesci else None

    # -------------------------------------------------------- zbieranie epizodów i scen (Przebieg 1)

    def _zbierz_epizody(self) -> list[_Epizod]:
        ix = self.ix
        epizody: list[_Epizod] = []
        ep_nr = 0

        # ---- Przygotowanie danych cutscen text_msg i intro ----
        intro_rows = sorted(
            (r for r in ix.cutsceny_kontekst.get("intro", ()) if r.get("k") in ix.teksty),
            key=lambda r: r["id"],
        )
        napisy = sorted(
            (r for r in ix.cutsceny_kontekst.get("napis", ()) if r.get("k") in ix.teksty),
            key=lambda r: r["wiersz"],
        )
        ciagi: list[list[dict]] = []
        for row in napisy:
            if not ciagi or row["wiersz"] - ciagi[-1][-1]["wiersz"] > 1:
                ciagi.append([row])
            else:
                ciagi[-1].append(row)
        plec_wiersza = kc.wykryj_plec_napisow(napisy, ix.teksty)
        prolog_ciagi = [c for c in ciagi if not (c[-1]["wiersz"] < ZAKRES_PROLOG_TM[0] or c[0]["wiersz"] > ZAKRES_PROLOG_TM[1])]
        inne_ciagi = [c for c in ciagi if c not in prolog_ciagi]

        def _zbuduj_scene_segmentu(seg: dict, tytul_bazowy: str, ep_id: int, sc_idx: int) -> tuple[_Scena | None, int, int]:
            filtrowane: list[tuple[dict, str, str]] = []
            for row in seg["rows"]:
                p = plec_wiersza.get(row["wiersz"], "")
                if p == "bohaterka" and self.plec == "bohater":
                    continue
                if p == "bohater" and self.plec == "bohaterka":
                    continue
                pref = "[♂ Bohater] " if (p == "bohater" and self.plec == "oba") else ("[♀ Bohaterka] " if (p == "bohaterka" and self.plec == "oba") else "")
                filtrowane.append((row, p, pref))
            d_s, t_s = self._stat_slotow([r["k"] for r, _, _ in filtrowane])
            if not self._ma_dopuszczalne_pokrycie(d_s, t_s):
                return None, d_s, t_s

            sc_klucze: set[str] = set()
            with self.pl.zbieraj(sc_klucze):
                for row, _, _ in filtrowane:
                    self.pl.zanotuj(row["k"])
                out_lines: list[str] = []
                if seg["grupa"] is not None:
                    row_g = ix.grupy.get(seg["grupa"]) or {}
                    if any(self.pl.tekst(row_g.get(f), jedna_linia=True) for f in ("numer_tytulu", "tytul", "nazwa")):
                        out_lines.append(f"*Wątek:* {self._nazwa_grupy(seg['grupa'])}")
                cut_opisy = []
                for cno in seg.get("cuts", ()):
                    ct = self._tytul_powtorki(cno)
                    if ct:
                        cut_opisy.append(f"#{cno} ({ct})")
                if cut_opisy:
                    out_lines.append(f"*Powiązane cutsceny w dzienniku:* {', '.join(cut_opisy)}")
                if seg.get("notka"):
                    out_lines.append(f"*{seg['notka']}*")

                rendered_dialog: list[str] = []
                rozpoznani_mowcy: list[str] = []
                mowcy_pary: list[tuple[str | None, str | None]] = []
                widziani_mowcy: set[str] = set()
                brak_mowcy = 0
                last_vo = ""
                wygl_wiersze = seg.get("wygladzono_audio") or set()
                zh_parts: list[str] = []
                i = 0
                while i < len(filtrowane):
                    row, p, pref = filtrowane[i]
                    zh_parts.append(ix.zh(row["k"]))
                    txt = self._tekst(row["k"], fallback_label="napisu", jedna_linia=True)
                    if not txt:
                        i += 1
                        continue
                    ignoruj_a1 = row["wiersz"] in wygl_wiersze
                    mowca1, clean_txt1, _, sp_en1 = self._rozwiaz_mowce_napisu(row, txt, ignoruj_audio=ignoruj_a1)
                    merged_pair = False
                    if self.plec == "oba" and p and i + 1 < len(filtrowane):
                        row2, p2, _ = filtrowane[i + 1]
                        if {p, p2} == {"bohater", "bohaterka"}:
                            txt2 = self._tekst(row2["k"], fallback_label="napisu", jedna_linia=True)
                            if txt2 is not None:
                                mowca2, clean_txt2, _, _ = self._rozwiaz_mowce_napisu(
                                    row2, txt2, ignoruj_audio=row2["wiersz"] in wygl_wiersze
                                )
                                if clean_txt2 == clean_txt1 and (mowca2 == mowca1 or not mowca2):
                                    merged_pair = True
                                    pref = ""
                    i += 2 if merged_pair else 1
                    aud = row.get("audio") or ""
                    vo = "_".join([part for part in aud.split("_") if not part.isdigit()][:3]) if aud else ""
                    if vo and vo != last_vo and last_vo and rendered_dialog:
                        rendered_dialog.append("")
                    last_vo = vo
                    if mowca1:
                        if mowca1 not in widziani_mowcy:
                            widziani_mowcy.add(mowca1)
                            rozpoznani_mowcy.append(mowca1)
                            mowcy_pary.append((self._klucz_mowcy_cutsceny(sp_en1), sp_en1))
                        rendered_dialog.append(f"**{pref}{mowca1}:** {clean_txt1}")
                    elif pref:
                        brak_mowcy += 1
                        rendered_dialog.append(f"**{pref.strip()}** {clean_txt1}")
                    else:
                        brak_mowcy += 1
                        rendered_dialog.append(clean_txt1)

                if rozpoznani_mowcy and brak_mowcy > 0 and len(rendered_dialog) >= 4:
                    out_lines.append(
                        f"*Rozpoznani mówcy: {', '.join(rozpoznani_mowcy)} "
                        "(część napisów zapisano w tabeli `text_msg` bez etykiety mówcy).*"
                    )
                elif not rozpoznani_mowcy and brak_mowcy >= 4:
                    out_lines.append("*Uwaga: w źródłowej tabeli `text_msg` tej sekwencji brak przypisanych etykiet mówcy.*")

                if out_lines:
                    out_lines.append("")
                out_lines.extend(rendered_dialog)
                out_lines.append("")

            w0, w1 = seg["rows"][0]["wiersz"], seg["rows"][-1]["wiersz"]
            sc = _Scena(
                uid=f"tm_{w0}_{w1}",
                epizod_nr=ep_id,
                scena_nr=sc_idx,
                tytul=f"{tytul_bazowy} (napisy {w0}–{w1}, {d_s}/{t_s})",
                rodzaj="text_msg",
                segment=seg,
                tekst_zh_do_skanu="\n".join(zh_parts),
                linie_skryptu=out_lines,
                mowcy_cutsceny=mowcy_pary,
                uzyte_klucze=sc_klucze,
                done=d_s,
                total=t_s,
            )
            return sc, d_s, t_s

        # ---- EPIZOD 1: Intro i Prolog ----
        prolog_sceny: list[_Scena] = []
        p_done = 0
        p_all = 0
        next_ep = 1
        sc_idx = 0

        if intro_rows:
            intro_slots = [r["k"] for r in intro_rows]
            d_i, t_i = self._stat_slotow(intro_slots)
            p_done += d_i
            p_all += t_i
            if self._ma_dopuszczalne_pokrycie(d_i, t_i):
                sc_idx += 1
                intro_klucze: set[str] = set()
                with self.pl.zbieraj(intro_klucze):
                    for s_i in intro_slots:
                        self.pl.zanotuj(s_i)
                    s_lines = ["*Sekwencja wprowadzająca — „One Day in the Imperial Service” (`wds_oneday_intro_cutscene_data`).*", ""]
                    zh_i = []
                    for r in intro_rows:
                        zh_i.append(ix.zh(r["k"]))
                        txt = self._tekst(r["k"], fallback_label="napisu intro", jedna_linia=True)
                        if txt:
                            mowca_lbl = "You Xia" if r["mowca"] == 1 else ("Mówca 2 (Gwardia Cesarska)" if r["mowca"] == 2 else f"Mówca {r['mowca']}")
                            s_lines.append(f"- `{r['czas']:.1f}s` **{mowca_lbl}:** {txt}")
                    s_lines.append("")
                prolog_sceny.append(
                    _Scena(
                        uid="intro_0",
                        epizod_nr=next_ep,
                        scena_nr=sc_idx,
                        tytul=f"Intro otwierające ({d_i}/{t_i} linii)",
                        rodzaj="intro",
                        intro_rows=intro_rows,
                        tekst_zh_do_skanu="\n".join(zh_i),
                        linie_skryptu=s_lines,
                        uzyte_klucze=intro_klucze,
                        done=d_i,
                        total=t_i,
                    )
                )

        for idx_c, ciag in enumerate(prolog_ciagi, 1):
            segmenty = kc.segmentuj_ciag_napisow(ciag)
            for sub_idx, seg in enumerate(segmenty, 1):
                tyt_seg = seg["tytul"] or (f"Prolog — sekwencja {idx_c}.{sub_idx}" if len(segmenty) > 1 else f"Prolog — sekwencja {idx_c}")
                sc, ds, ts = _zbuduj_scene_segmentu(seg, tyt_seg, next_ep, sc_idx + 1)
                p_done += ds
                p_all += ts
                if sc is not None and not (self.zakres == "kompletne-rozdzialy" and ds < ts):
                    sc_idx += 1
                    sc.scena_nr = sc_idx
                    prolog_sceny.append(sc)

        if prolog_sceny and not (self.zakres == "kompletne-rozdzialy" and p_done < p_all):
            epizody.append(
                _Epizod(
                    nr=next_ep,
                    kategoria="prolog",
                    tytul="Prolog i sekwencje otwierające",
                    sceny=prolog_sceny,
                    done=p_done,
                    total=p_all,
                )
            )
            ep_nr = next_ep

        # ---- EPIZODY WĄTKU GŁÓWNEGO ORAZ ZADAŃ POBOCZNYCH ----
        przerywniki_uzyte: set[int] = set()
        powtorki_uzyte: set[int] = set()

        def _renderuj_dialog(numer_sceny: int, miejsce_uk, tid: int, *, jest_pierwsza_w_zadaniu: bool) -> tuple[_Scena | None, int, int]:
            scena = ix.sceny[numer_sceny]
            slots: list[str] = []
            active: list[tuple[list, str, str]] = []
            for el in scena["e"]:
                ok, prefix = self._pasuje_plec_elementu(el)
                if not ok:
                    continue
                slot = self._slot_sceny(el)
                slots.append(slot)
                active.append((el, slot, prefix))

            wybory = self.wybory_po.get(numer_sceny, ())
            for row in wybory:
                for ch in row.get("wybory", ()):
                    if ch.get("tekst"):
                        slots.append(ch["tekst"])

            done, total = self._stat_slotow(slots)
            if not self._ma_dopuszczalne_pokrycie(done, total):
                return None, done, total

            sc_klucze: set[str] = set()
            with self.pl.zbieraj(sc_klucze):
                for s_akt in slots:
                    self.pl.zanotuj(s_akt)
                s_lines: list[str] = []
                miejsca_txt = [self._miejsce(m) for m in (scena.get("m") or [])[:3]]
                miejsca_txt = [m for m in miejsca_txt if m]
                if miejsca_txt:
                    s_lines.append(f"*Miejsce: {', '.join(miejsca_txt)}*")
                if miejsce_uk.moment == "numeracja":
                    s_lines.append("*Kolejność przybliżona według numeracji dialogów gry.*")
                if done < total and self.zakres != "wszystko":
                    s_lines.append(f"*Uwaga: przetłumaczono {done} z {total} wypowiedzi w tej scenie.*")
                if s_lines:
                    s_lines.append("")

                surowe_wpisy: list[tuple[str, int, str, str, str, str]] = []
                for el, slot, prefix in active:
                    kind = el[0]
                    txt = self._tekst(slot, fallback_label="kwestii")
                    if txt is None:
                        continue
                    wariant = el[3] if len(el) > 3 and el[3] else 0
                    bazowy = el[2]
                    mowca = self._mowca(scena, el[1], el[5] if len(el) > 5 else None) if kind == "k" else ""
                    surowe_wpisy.append((kind, wariant, bazowy, mowca, txt, prefix))

                blok: list[str] = []
                i = 0
                while i < len(surowe_wpisy):
                    kind, wariant, bazowy, mowca, txt, prefix = surowe_wpisy[i]
                    if (
                        self.plec == "oba"
                        and i + 1 < len(surowe_wpisy)
                        and {wariant, surowe_wpisy[i + 1][1]} == {1, 2}
                        and surowe_wpisy[i + 1][0] == kind
                        and surowe_wpisy[i + 1][2] == bazowy
                        and surowe_wpisy[i + 1][3] == mowca
                        and surowe_wpisy[i + 1][4] == txt
                    ):
                        prefix = ""
                        i += 2
                    else:
                        i += 1
                    if kind == "k":
                        blok.append(f"**{prefix}{mowca}:** {txt.replace(chr(10), ' ')}")
                    elif kind in ("p", "o", "i"):
                        blok.append(f"*{prefix}{txt.replace(chr(10), ' ')}*")
                    elif kind == "wi":
                        blok.append(f"> **Wizytówka — {txt}**")
                    elif kind == "wt":
                        blok.append(f"> *{txt}*")
                    else:
                        blok.append(f"> {prefix}{txt.replace(chr(10), ' ')}")
                if blok:
                    s_lines.extend(blok)

                for row in wybory:
                    tytul_w = self._tekst(row.get("tytul"), fallback_label="pytania", jedna_linia=True)
                    opcje = []
                    for ch in row.get("wybory", ()):
                        t_opcji = self._tekst(ch.get("tekst"), fallback_label="opcji wyboru", jedna_linia=True)
                        if t_opcji is None:
                            continue
                        cele = ch.get("dialogi", ())
                        if cele:
                            # Placeholder z markowaniem docelowych dialogów — podmienimy po zamknięciu numeracji scen na `Scena X.Y (dialog ...)`!
                            cele_txt = ", ".join(f"@@CEL_DIALOG:{d}@@" for d in cele)
                            opcje.append(f"- **Wybór {ch['nr']}:** {t_opcji} *(→ {cele_txt})*")
                        else:
                            opcje.append(f"- **Wybór {ch['nr']}:** {t_opcji}")
                    if opcje:
                        s_lines.append("")
                        s_lines.append(f"**Wybór gracza — {tytul_w}:**" if tytul_w else "**Wybór gracza:**")
                        s_lines.extend(opcje)
                s_lines.append("")

                # Tekst ZH do skanowania powiązań: dialog + czysta obsada + metadane zadania
                tr = ix.zadania[tid]
                zh_parts = [ix.zh(el[2]) for el in scena["e"] if el[2]]
                for o in scena.get("o", ()):
                    nk, tk, ok, _rk = self._dane_osoby_w_scenie(o)
                    for k_os in (nk, tk, ok):
                        if k_os:
                            zh_parts.append(ix.zh(k_os))
                for f in ("nazwa", "cel", "opis"):
                    if tr.get(f):
                        zh_parts.append(ix.zh(tr[f]))
                przestrzenie = set(scena.get("m") or ())
                if tr.get("przestrzen") is not None:
                    przestrzenie.add(tr["przestrzen"])

                tyt_zad = self._nazwa_zadania(tid)
                tyt_sceny = f"{tyt_zad} (dialog {numer_sceny})"
            return (
                _Scena(
                    uid=f"dlg_{numer_sceny}",
                    epizod_nr=0,
                    scena_nr=0,
                    tytul=tyt_sceny,
                    rodzaj="dialog",
                    dialog_no=numer_sceny,
                    miejsce_ukladu=miejsce_uk,
                    zadanie_id=tid,
                    tekst_zh_do_skanu="\n".join(p for p in zh_parts if p),
                    przestrzenie=przestrzenie,
                    linie_skryptu=s_lines,
                    uzyte_klucze=sc_klucze,
                    done=done,
                    total=total,
                    pokaz_zadanie_info=jest_pierwsza_w_zadaniu,
                ),
                done,
                total,
            )

        def _renderuj_przerywnik_zadania(cut_no: int, tid: int, moment_lbl: str, prow: dict | None = None) -> tuple[_Scena | None, int, int]:
            crow = ix.przerywniki.get(cut_no) or {}
            t_slot = crow.get("tekst")
            s_slot = crow.get("streszczenie") or (prow.get("streszczenie") if prow else None)
            c_slots = [s for s in (t_slot, s_slot) if s]
            cd, ct = self._stat_slotow(c_slots) if c_slots else (0, 0)
            tyt_p = self._tytul_powtorki(cut_no)
            ma_crow = bool(c_slots) and self._ma_dopuszczalne_pokrycie(cd, ct)
            if not ma_crow and not (prow and tyt_p):
                return None, cd, ct

            sc_klucze: set[str] = set()
            with self.pl.zbieraj(sc_klucze):
                for s_c in c_slots:
                    self.pl.zanotuj(s_c)
                s_lines: list[str] = [f"*[Przerywnik fabularny #{cut_no} — {moment_lbl}]*"]
                t_pl = self._tekst(t_slot, fallback_label="planszy przerywnika") if t_slot else None
                s_pl = self._tekst(s_slot, fallback_label="streszczenia") if s_slot else None
                if t_pl:
                    s_lines.append("")
                    s_lines.append(t_pl)
                if s_pl:
                    s_lines.append("")
                    s_lines.append(f"> **Streszczenie z dziennika:** {s_pl}")
                s_lines.append("")

                zh_parts = [ix.zh(s) for s in c_slots if s]
                tr = ix.zadania[tid]
                for f in ("nazwa", "cel", "opis"):
                    if tr.get(f):
                        zh_parts.append(ix.zh(tr[f]))
                przestrzenie = {tr["przestrzen"]} if tr.get("przestrzen") is not None else set()
                tyt_zad = self._nazwa_zadania(tid)
                tyt_p = self._tytul_powtorki(cut_no)
                nazwa_cut = tyt_p or f"Przerywnik #{cut_no}"
            return (
                _Scena(
                    uid=f"cut_{cut_no}_{tid}",
                    epizod_nr=0,
                    scena_nr=0,
                    tytul=f"{tyt_zad} — {nazwa_cut}",
                    rodzaj="przerywnik",
                    zadanie_id=tid,
                    przerywnik_no=cut_no,
                    powtorka_row=prow,
                    cut_moment=moment_lbl,
                    tekst_zh_do_skanu="\n".join(p for p in zh_parts if p),
                    przestrzenie=przestrzenie,
                    linie_skryptu=s_lines,
                    uzyte_klucze=sc_klucze,
                    done=cd,
                    total=ct,
                ),
                cd,
                ct,
            )

        for sekcja in self.uklad.sekcje:
            is_main = sekcja.typ == uklad_scen.TYP_WATKU_GLOWNEGO
            if self.tylko_watek_glowny and not is_main:
                continue

            ep_sceny: list[_Scena] = []
            ep_done = 0
            ep_all = 0
            last_meta: tuple[str, str | None, str | None] | None = None
            seen_metas: set[tuple[str, str | None, str | None]] = set()
            ep_zadania: list[int] = []
            szac_ep_nr = ep_nr + 1

            for tid in sekcja.zadania:
                trow = ix.zadania[tid]
                miejsca_sceny = self.uklad.sceny_zadania.get(tid, ())
                zad_sceny: list[_Scena] = []
                zad_done = 0
                zad_all = 0
                pierwsza_dla_zadania = True

                for cut_no in (trow.get("przerywniki") or {}).get("przyjecie", ()):
                    if cut_no in przerywniki_uzyte:
                        continue
                    sc_c, cd, ct = _renderuj_przerywnik_zadania(cut_no, tid, "rozpoczęcie zadania")
                    zad_done += cd
                    zad_all += ct
                    if sc_c is not None:
                        przerywniki_uzyte.add(cut_no)
                        powtorki_uzyte.add(cut_no)
                        self.przerywniki_w_zadaniach.add(cut_no)
                        zad_sceny.append(sc_c)
                        pierwsza_dla_zadania = False

                for m in miejsca_sceny:
                    sc_d, sd, st = _renderuj_dialog(m.dialog, m, tid, jest_pierwsza_w_zadaniu=pierwsza_dla_zadania)
                    zad_done += sd
                    zad_all += st
                    if sc_d is not None:
                        zad_sceny.append(sc_d)
                        pierwsza_dla_zadania = False

                for cut_no in (trow.get("przerywniki") or {}).get("zakonczenie", ()):
                    if cut_no in przerywniki_uzyte:
                        continue
                    sc_c, cd, ct = _renderuj_przerywnik_zadania(cut_no, tid, "zakończenie zadania")
                    zad_done += cd
                    zad_all += ct
                    if sc_c is not None:
                        przerywniki_uzyte.add(cut_no)
                        powtorki_uzyte.add(cut_no)
                        self.przerywniki_w_zadaniach.add(cut_no)
                        zad_sceny.append(sc_c)

                for prow in self.powtorki_po_zadaniu.get(tid, ()):
                    pno = prow.get("no")
                    if pno in powtorki_uzyte or pno in przerywniki_uzyte:
                        continue
                    sc_p, pd, pt = _renderuj_przerywnik_zadania(pno, tid, "powtórka w dzienniku", prow=prow)
                    if sc_p is not None:
                        zad_done += pd
                        zad_all += pt
                        powtorki_uzyte.add(pno)
                        przerywniki_uzyte.add(pno)
                        self.przerywniki_w_zadaniach.add(pno)
                        zad_sceny.append(sc_p)

                nazwa_z = self.pl.tekst(trow.get("nazwa"), jedna_linia=True)
                cel_z = self.pl.tekst(trow.get("cel"), jedna_linia=True)
                opis_z = self.pl.tekst(trow.get("opis"))
                meta_slots = [s for s in (trow.get("nazwa"), trow.get("cel"), trow.get("opis")) if s]
                md, mt = self._stat_slotow(meta_slots)
                zad_done += md
                zad_all += mt

                ma_tresc = bool(zad_sceny) or self._ma_dopuszczalne_pokrycie(zad_done, zad_all)
                if not ma_tresc:
                    continue
                if self.zakres == "kompletne-rozdzialy" and zad_done < zad_all:
                    ep_all += zad_all
                    ep_done += zad_done
                    continue

                tyt = nazwa_z or (f"Zadanie #{tid} [brak polskiego tytułu]" if self.zakres == "wszystko" else f"Zadanie #{tid}")
                cur_meta = (tyt, cel_z, opis_z)
                if (last_meta == cur_meta or cur_meta in seen_metas) and not zad_sceny:
                    continue
                seen_metas.add(cur_meta)

                # Jeśli zadanie ma tylko opis/cel bez dialogów ani przerywników -> Scena dziennikowa
                if not zad_sceny:
                    j_klucze: set[str] = set()
                    with self.pl.zbieraj(j_klucze):
                        for ms in meta_slots:
                            self.pl.zanotuj(ms)
                        j_lines = []
                        miejsce_z = self._miejsce(trow["przestrzen"]) if trow.get("przestrzen") is not None else None
                        if miejsce_z:
                            j_lines.append(f"*Miejsce: {miejsce_z}*")
                        if cel_z:
                            j_lines.append(f"- **Cel w dzienniku:** {cel_z}")
                        if opis_z:
                            j_lines.append(f"- **Opis zadania:** {opis_z}")
                        j_lines.append("")
                    zh_j = " ".join(ix.zh(trow.get(f)) for f in ("nazwa", "cel", "opis") if trow.get(f))
                    zad_sceny.append(
                        _Scena(
                            uid=f"zad_{tid}",
                            epizod_nr=szac_ep_nr,
                            scena_nr=0,
                            tytul=f"{tyt} (wpis w dzienniku)",
                            rodzaj="dziennik",
                            zadanie_id=tid,
                            tekst_zh_do_skanu=zh_j,
                            przestrzenie={trow["przestrzen"]} if trow.get("przestrzen") is not None else set(),
                            linie_skryptu=j_lines,
                            uzyte_klucze=j_klucze,
                            done=zad_done,
                            total=zad_all,
                            pokaz_zadanie_info=True,
                        )
                    )
                else:
                    # Do pierwszej sceny zadania dodajemy na górze dyskretną metkę celu/opisu, jeśli jest nowa
                    for ms in meta_slots:
                        zad_sceny[0].uzyte_klucze.add(self.pl.klucz_bazowy(ms))
                    if not (last_meta and last_meta == cur_meta):
                        prefix_lines: list[str] = []
                        if last_meta and last_meta[0] == tyt and nazwa_z is not None:
                            if cel_z and cel_z != last_meta[1]:
                                prefix_lines.append(f"> **Cel etapu:** {cel_z}")
                            if opis_z and opis_z != last_meta[2]:
                                prefix_lines.append(f"> **Dalszy opis:** {opis_z}")
                        else:
                            if cel_z:
                                prefix_lines.append(f"> **Cel w dzienniku:** {cel_z}")
                            if opis_z:
                                prefix_lines.append(f"> **Opis w dzienniku:** {opis_z}")
                        if prefix_lines:
                            prefix_lines.append("")
                            zad_sceny[0].linie_skryptu = prefix_lines + zad_sceny[0].linie_skryptu
                        zad_sceny[0].pokaz_zadanie_info = True

                last_meta = cur_meta
                ep_done += zad_done
                ep_all += zad_all
                ep_zadania.append(tid)
                ep_sceny.extend(zad_sceny)

            if not ep_sceny:
                continue
            if self.zakres == "kompletne-rozdzialy" and ep_done < ep_all:
                continue

            ep_nr += 1
            for idx_s, sc in enumerate(ep_sceny, 1):
                sc.epizod_nr = ep_nr
                sc.scena_nr = idx_s
            nazwa_kat = self._nazwa_typu(sekcja.typ)
            tyt_ep = f"{nazwa_kat}: {self._nazwa_grupy(sekcja.grupa)}"
            epizody.append(
                _Epizod(
                    nr=ep_nr,
                    kategoria="watek_glowny" if is_main else "poboczne",
                    tytul=tyt_ep,
                    typ_zadania=sekcja.typ,
                    grupa=sekcja.grupa,
                    notka_kategorii=(
                        ""
                        if is_main
                        else "Uwaga: zadania tej kategorii w otwartym świecie można podejmować w dowolnej kolejności."
                    ),
                    sceny=ep_sceny,
                    zadania_ids=ep_zadania,
                    done=ep_done,
                    total=ep_all,
                )
            )

        # ---- POZOSTAŁE CUTSCENY, FILMY I LUŹNE PRZERYWNIKI (tylko gdy nie jesteśmy w wąskim trybie? Nie — zawsze, chyba że `--tylko-watek-glowny` ogranicza też poboczne napisy) ----
        cut_sceny: list[_Scena] = []
        cut_done = 0
        cut_all = 0
        cand_ep = ep_nr + 1

        if not self.tylko_watek_glowny:
            nr_sek = 0
            for ciag in inne_ciagi:
                segmenty = kc.segmentuj_ciag_napisow(ciag)
                nr_sek += 1
                for sub_idx, seg in enumerate(segmenty, 1):
                    tyt_seg = seg["tytul"] or f"Sekwencja cutscen {nr_sek}.{sub_idx}"
                    sc, ds, ts = _zbuduj_scene_segmentu(seg, tyt_seg, cand_ep, len(cut_sceny) + 1)
                    cut_done += ds
                    cut_all += ts
                    if sc is not None and not (self.zakres == "kompletne-rozdzialy" and ds < ts):
                        cut_sceny.append(sc)

            by_film: dict[int, list[dict]] = defaultdict(list)
            for r in ix.cutsceny_kontekst.get("film", ()):
                if r.get("k") in ix.teksty:
                    by_film[r["film"]].append(r)
            for film_id, rows in sorted(by_film.items()):
                rows.sort(key=lambda r: (r["czas"], r["id"]))
                df, tf = self._stat_slotow([r["k"] for r in rows])
                cut_done += df
                cut_all += tf
                if not self._ma_dopuszczalne_pokrycie(df, tf):
                    continue
                if self.zakres == "kompletne-rozdzialy" and df < tf:
                    continue
                f_klucze: set[str] = set()
                with self.pl.zbieraj(f_klucze):
                    f_lines = []
                    zh_f = []
                    for r in rows:
                        self.pl.zanotuj(r["k"])
                        zh_f.append(ix.zh(r["k"]))
                        txt = self._tekst(r["k"], fallback_label="napisu filmowego", jedna_linia=True)
                        if txt:
                            f_lines.append(f"- `{r['czas']:.1f}s` {txt}")
                    f_lines.append("")
                cut_sceny.append(
                    _Scena(
                        uid=f"film_{film_id}",
                        epizod_nr=cand_ep,
                        scena_nr=len(cut_sceny) + 1,
                        tytul=f"Sekwencja filmowa #{film_id} ({df}/{tf} napisów)",
                        rodzaj="film",
                        film_id=film_id,
                        film_rows=rows,
                        tekst_zh_do_skanu="\n".join(zh_f),
                        linie_skryptu=f_lines,
                        uzyte_klucze=f_klucze,
                        done=df,
                        total=tf,
                    )
                )

            # Luźne przerywniki nieprzypisane do żadnego zadania
            luzne = []
            for no, row in sorted(ix.przerywniki.items()):
                if no in self.przerywniki_w_zadaniach or no in przerywniki_uzyte:
                    continue
                if no >= 10_000_000 and (no % 10_000_000) in ix.przerywniki:
                    base_row = ix.przerywniki[no % 10_000_000]
                    if (
                        self.pl.tekst(row.get("tekst")) == self.pl.tekst(base_row.get("tekst"))
                        and self.pl.tekst(row.get("streszczenie")) == self.pl.tekst(base_row.get("streszczenie"))
                    ):
                        continue
                luzne.append((no, row))

            plansze_buf: list[tuple[int, str, str, set[str]]] = []  # (no, txt_pl, zh, klucze)
            for no, row in luzne:
                slots = [row[f] for f in ("tekst", "streszczenie") if row.get(f)]
                dp, tp = self._stat_slotow(slots)
                cut_done += dp
                cut_all += tp
                if not self._ma_dopuszczalne_pokrycie(dp, tp):
                    continue
                if self.zakres == "kompletne-rozdzialy" and dp < tp:
                    continue
                p_klucze: set[str] = set()
                with self.pl.zbieraj(p_klucze):
                    for s_p in slots:
                        self.pl.zanotuj(s_p)
                    t_pl = self._tekst(row.get("tekst"), fallback_label="planszy przerywnika")
                    s_pl = self._tekst(row.get("streszczenie"), fallback_label="streszczenia przerywnika")
                    tyt_powt = self._tytul_powtorki(no)
                if s_pl or tyt_powt:
                    p_lines: list[str] = []
                    if t_pl:
                        p_lines.append(t_pl)
                    if s_pl:
                        p_lines.append(f"> **Streszczenie:** {s_pl}")
                    p_lines.append("")
                    cut_sceny.append(
                        _Scena(
                            uid=f"cut_loose_{no}",
                            epizod_nr=cand_ep,
                            scena_nr=len(cut_sceny) + 1,
                            tytul=f"Przerywnik #{no}" + (f" — {tyt_powt}" if tyt_powt else ""),
                            rodzaj="przerywnik",
                            przerywnik_no=no,
                            tekst_zh_do_skanu="\n".join(ix.zh(s) for s in slots),
                            linie_skryptu=p_lines,
                            uzyte_klucze=p_klucze,
                            done=dp,
                            total=tp,
                        )
                    )
                elif t_pl:
                    plansze_buf.append((no, t_pl.replace("\n", " "), ix.zh(row.get("tekst")), p_klucze))

            if plansze_buf:
                pl_lines = [f"- **#{no}:** {txt}" for no, txt, _, _ in plansze_buf] + [""]
                pl_klucze = set().union(*(kl_set for _, _, _, kl_set in plansze_buf))
                cut_sceny.append(
                    _Scena(
                        uid="cut_blackscreens",
                        epizod_nr=cand_ep,
                        scena_nr=len(cut_sceny) + 1,
                        tytul=f"Plansze przejściowe ({len(plansze_buf)} wpisów)",
                        rodzaj="przerywnik",
                        tekst_zh_do_skanu="\n".join(z for _, _, z, _ in plansze_buf if z),
                        linie_skryptu=pl_lines,
                        uzyte_klucze=pl_klucze,
                        done=len(plansze_buf),
                        total=len(plansze_buf),
                    )
                )

            if cut_sceny:
                ep_nr = cand_ep
                for idx_s, sc in enumerate(cut_sceny, 1):
                    sc.epizod_nr = ep_nr
                    sc.scena_nr = idx_s
                epizody.append(
                    _Epizod(
                        nr=ep_nr,
                        kategoria="cutsceny",
                        tytul="Pozostałe sekwencje filmowe, cutsceny i plansze przejściowe",
                        sceny=cut_sceny,
                        done=cut_done,
                        total=cut_all,
                    )
                )

        # ---- OPCJONALNIE: OTOCZENIE (`--z-otoczeniem`) ----
        if self.z_otoczeniem:
            def _dodaj_epizod_otoczenia(tytul_o: str, numery: list[int], *, projekt: str | None = None, tlo_k: tuple | None = None) -> None:
                nonlocal ep_nr
                sc_list: list[_Scena] = []
                d_o = 0
                t_o = 0
                for dno in numery:
                    scena = ix.sceny[dno]
                    slots = []
                    active = []
                    for el in scena["e"]:
                        ok, prefix = self._pasuje_plec_elementu(el)
                        if not ok:
                            continue
                        slot = self._slot_sceny(el)
                        slots.append(slot)
                        active.append((el, slot, prefix))
                    ds, ts = self._stat_slotow(slots)
                    d_o += ds
                    t_o += ts
                    if not self._ma_dopuszczalne_pokrycie(ds, ts):
                        continue
                    e_klucze: set[str] = set()
                    with self.pl.zbieraj(e_klucze):
                        for s_e in slots:
                            self.pl.zanotuj(s_e)
                        s_lines = []
                        miejsca_txt = [m for m in (self._miejsce(mm) for mm in (scena.get("m") or [])[:3]) if m]
                        if miejsca_txt:
                            s_lines.append(f"*Miejsce: {', '.join(miejsca_txt)}*")
                            s_lines.append("")
                        for el, slot, prefix in active:
                            txt = self._tekst(slot, fallback_label="kwestii")
                            if not txt:
                                continue
                            if el[0] == "k":
                                mowca = self._mowca(scena, el[1], el[5] if len(el) > 5 else None)
                                s_lines.append(f"**{prefix}{mowca}:** {txt.replace(chr(10), ' ')}")
                            else:
                                s_lines.append(f"*{prefix}{txt.replace(chr(10), ' ')}*")
                        s_lines.append("")
                    zh_p = [ix.zh(el[2]) for el in scena["e"] if el[2]]
                    sc_list.append(
                        _Scena(
                            uid=f"env_{dno}",
                            epizod_nr=ep_nr + 1,
                            scena_nr=len(sc_list) + 1,
                            tytul=f"Rozmowa świata (dialog {dno})",
                            rodzaj="dialog",
                            dialog_no=dno,
                            miejsce_ukladu=self.uklad.miejsca[dno],
                            tekst_zh_do_skanu="\n".join(zh_p),
                            przestrzenie=set(scena.get("m") or ()),
                            linie_skryptu=s_lines,
                            uzyte_klucze=e_klucze,
                            done=ds,
                            total=ts,
                        )
                    )
                if not sc_list:
                    return
                ep_nr += 1
                for idx_s, sc in enumerate(sc_list, 1):
                    sc.epizod_nr = ep_nr
                    sc.scena_nr = idx_s
                epizody.append(
                    _Epizod(
                        nr=ep_nr,
                        kategoria="otoczenie",
                        tytul=tytul_o,
                        projekt=projekt,
                        tlo_klucz=tlo_k,
                        notka_kategorii="Katalog dialogów bez powiązania z zadaniami oraz rozmów tła NPC (kolejność katalogowa).",
                        sceny=sc_list,
                        done=d_o,
                        total=t_o,
                    )
                )

            for project, numbers in self.uklad.projekty:
                _dodaj_epizod_otoczenia(f"Rozmowy świata — projekt: {project or '(bez nazwy)'}", numbers, projekt=project)
            for (kind, value), numbers in self.uklad.tlo:
                miejsce_lbl = (self._miejsce(value) or f"Obszar #{value}") if kind == "miejsce" else f"Reakcje NPC: {value}"
                _dodaj_epizod_otoczenia(f"Rozmowy tła — {miejsce_lbl}", numbers, tlo_k=(kind, value))

        # Rozwiązanie docelowych odnośników wyborów (`@@CEL_DIALOG:<id>@@` -> `Scena E.S (dialog <id>)`)
        dialog_na_scene: dict[int, str] = {}
        for ep in epizody:
            for sc in ep.sceny:
                if sc.dialog_no is not None and sc.dialog_no not in dialog_na_scene:
                    dialog_na_scene[sc.dialog_no] = sc.etykieta_krotka
        re_cel = re.compile(r"@@CEL_DIALOG:(\d+)@@")
        for ep in epizody:
            for sc in ep.sceny:
                sc.linie_skryptu = [
                    re_cel.sub(
                        lambda m: f"{dialog_na_scene[int(m.group(1))]}, dialog {m.group(1)}"
                        if int(m.group(1)) in dialog_na_scene
                        else f"dialog {m.group(1)}",
                        line,
                    )
                    for line in sc.linie_skryptu
                ]

        return epizody

    # -------------------------------------------------------- budowa `epizody.md` i `kontekst_scen.md`

    def _narracja_otwierajaca_epizodu(self, ep: _Epizod) -> list[str]:
        """Narracja otwierająca rozdział/epizod z gry (`main_storyline_activity_config`, `task_group_info`, `plot_recap_data`)."""
        linie: list[str] = []
        if ep.grupa is not None:
            # 1. Poemat otwierający rozdział (`task_group_info`: text_shang[] + text_xia[])
            gid_s = str(ep.grupa)
            poemat_g = self.baza.wszystkie_klucze("task_group_info", gid_s, "text_shang[]")
            poemat_d = self.baza.wszystkie_klucze("task_group_info", gid_s, "text_xia[]")
            wiersze_p = [
                t for t in (self.pl.tekst(k, jedna_linia=True) for k in (*poemat_g, *poemat_d)) if t
            ]
            if wiersze_p:
                linie.append("> " + " / ".join(wiersze_p))
            # 2. Opis głównego aktu z `main_storyline_activity_config`
            for act_id, target_gr in pc.AKTY_FABULARNE_DO_GRUPY.items():
                if target_gr == ep.grupa:
                    des_kl = self.baza.pierwszy_klucz("main_storyline_activity_config", act_id, "des", z_w2=False)
                    des_pl = self.pl.tekst(des_kl)
                    if des_pl:
                        linie.append(f"> **Wprowadzenie do aktu:** {des_pl}")
            # 3. Kronika rozdziału z `plot_recap_data`
            for srow in self.streszczenia_grupy.get(ep.grupa, ()):
                s_pl = self._tekst(srow.get("tekst"), fallback_label="streszczenia fabuły")
                if s_pl:
                    linie.append(f"> **Kronika rozdziału:** {s_pl}")
        if ep.notka_kategorii:
            linie.insert(0, f"*{ep.notka_kategorii}*")
        if linie:
            linie.append("")
        return linie

    def _buduj_epizody_md(self, epizody: list[_Epizod]) -> tuple[ZbudowanyPlik, set[str], set[int]]:
        lines: list[str] = [
            "# Where Winds Meet — Scenariusz fabularny (Epizody)",
            "",
            "Czysty scenariusz do ciągłej lektury: Prolog, Wątek Główny, wątki poboczne oraz sekwencje przerywników.",
            "Powiązane biografie, opisy NPC, frakcje, miejsca, księgi, poszlaki, listy, przedmioty i techniki",
            "znajdziesz pod identycznymi numerami `Epizod E` i `Scena E.S` w równoległym pliku `kontekst_scen.md`,",
            "a cały pozostały materiał ze świata gry poza scenami — pogrupowany w `dodatkowe.md`.",
            "",
        ]
        done_total = 0
        all_total = 0
        scen_total = 0
        uzyte_klucze: set[str] = set()
        uzyte_zadania: set[int] = set()
        prev_kat = None
        naglowki_kat = {
            "prolog": "Część I — Prolog i sekwencje otwierające",
            "watek_glowny": "Część II — Wątek Główny (chronologicznie)",
            "poboczne": "Część III — Zadania poboczne i historie świata",
            "cutsceny": "Część IV — Pozostałe sekwencje filmowe, cutsceny i plansze",
            "otoczenie": "Część V — Rozmowy świata poza zadaniami",
        }

        for ep in epizody:
            if ep.kategoria != prev_kat:
                prev_kat = ep.kategoria
                lines.append(f"# {naglowki_kat.get(ep.kategoria, ep.kategoria)}")
                lines.append("")
                if ep.kategoria == "poboczne":
                    lines.append(
                        "> **Uwaga dla czytelnika:** Zadania poboczne (Spotkania, Kampanie, Dziedzictwo Jianghu, Sprawy świata itp.) "
                        "są uporządkowane według kategorii i wewnętrznych łańcuchów zależności, lecz w otwartym świecie gry można je podejmować w dowolnej kolejności."
                    )
                    lines.append("")

            lines.append(f"## Epizod {ep.nr} — {ep.tytul}")
            lines.append(f"*Scen: {len(ep.sceny)} · przetłumaczenie: {ep.done}/{ep.total}*")
            lines.append("")
            with self.pl.zbieraj(uzyte_klucze):
                if ep.typ_zadania is not None:
                    self._nazwa_typu(ep.typ_zadania)
                if ep.grupa is not None:
                    self._nazwa_grupy(ep.grupa)
                if ep.tlo_klucz and ep.tlo_klucz[0] == "miejsce":
                    self._miejsce(ep.tlo_klucz[1])
                lines.extend(self._narracja_otwierajaca_epizodu(ep))

            uzyte_zadania.update(ep.zadania_ids)
            for sc in ep.sceny:
                uzyte_klucze.update(sc.uzyte_klucze)
                if sc.zadanie_id is not None:
                    uzyte_zadania.add(sc.zadanie_id)
                lines.append(f"### {sc.naglowek}")
                lines.append("")
                lines.extend(sc.linie_skryptu)
                scen_total += 1

            done_total += ep.done
            all_total += ep.total

        if not epizody:
            lines.append("*W aktualnym zakresie i zbiorze polskich tłumaczeń brak jeszcze ukończonych epizodów.*")
            lines.append("")

        return (
            ZbudowanyPlik(
                nazwa="epizody.md",
                tytul="Scenariusz fabularny (Epizody)",
                opis="Numerowany skrypt Prologu, Wątku Głównego, zadań pobocznych i cutscen.",
                linie=lines,
                statystyka={
                    "epizodow": len(epizody),
                    "scen": scen_total,
                    "przetlumaczono": done_total,
                    "wszystkich": all_total,
                },
            ),
            uzyte_klucze,
            uzyte_zadania,
        )

    # -------------------------------------------------------- budowa `kontekst_scen.md`

    def _zbierz_wiersz_tabeli_pl(self, tbl: str, rid: str, pola: list[tuple[str, str]], *, uzyj_w2: bool = True) -> tuple[str | None, list[tuple[str, str]], int, int]:
        """Odczytaj nazwę i opisane pola wiersza wyłącznie przez `self.pl`."""
        nazwa_kl = self.baza.pierwszy_klucz(tbl, rid, pola[0][0], z_w2=uzyj_w2)
        sloty: list[str] = [nazwa_kl] if nazwa_kl else []
        for col, _lbl in pola[1:]:
            sloty.extend(self.baza.wszystkie_klucze(tbl, rid, col))
        d_r, t_r = self._stat_slotow(sloty)
        if not self._ma_dopuszczalne_pokrycie(d_r, t_r):
            return None, [], d_r, t_r
        nazwa = self._tekst(nazwa_kl, fallback_label="nazwy", jedna_linia=True) if nazwa_kl else None
        detale: list[tuple[str, str]] = []
        for col, lbl in pola[1:]:
            klucze = self.baza.wszystkie_klucze(tbl, rid, col)
            teksty = []
            seen_t = set()
            for kl in klucze:
                val = self._tekst(kl, fallback_label=lbl.lower())
                if val and val not in seen_t:
                    seen_t.add(val)
                    teksty.append(val)
            if teksty:
                detale.append((lbl, "\n".join(teksty)))
        return nazwa, detale, d_r, t_r

    def _renderuj_karte_postaci_pelna(
        self,
        *,
        imie_pl: str,
        rola_sceny: str,
        tytul_pl: str | None = None,
        opis_npc_pl: str | None = None,
        enc_entry: dict | None = None,
        amity_rids: list[str] = (),
        boss_rids: list[str] = (),
        fuben_boss_rids: list[str] = (),
        mistrz_rids: list[str] = (),
        wiz_cut_rids: list[str] = (),
        dalsze_wpisy_buf: list[tuple[str, list[str]]],
    ) -> list[str]:
        out: list[str] = []
        tyt_dodatki = [x for x in (tytul_pl,) if x]
        for wr in wiz_cut_rids:
            b_kl = self.baza.pierwszy_klucz("cutscene_person_info_config", wr, "base_info", "base_info_en", z_w2=False)
            b_pl = self.pl.tekst(b_kl, jedna_linia=True)
            if b_pl and b_pl not in tyt_dodatki:
                tyt_dodatki.append(b_pl)
        if enc_entry and enc_entry.get("inna_nazwa"):
            inna = self.pl.tekst(enc_entry["inna_nazwa"], jedna_linia=True)
            if inna and inna != imie_pl:
                tyt_dodatki.append(f"inne miano: {inna}")
        if enc_entry and enc_entry.get("urodziny"):
            ur = self.pl.tekst(enc_entry["urodziny"], jedna_linia=True)
            if ur:
                tyt_dodatki.append(f"urodziny: {ur}")

        nagl = f"- **{imie_pl}** *({rola_sceny})*"
        if tyt_dodatki:
            nagl += f" — {'; '.join(tyt_dodatki)}"
        out.append(nagl)

        if opis_npc_pl:
            out.append(f"  - *Opis postaci w scenie (`entity_attr`):* {opis_npc_pl}")

        dalsze_linie_tej_postaci: list[str] = []
        if enc_entry:
            toz = [t for t in (self.pl.tekst(k, jedna_linia=True) for k in enc_entry.get("tozsamosc", ())) if t]
            if toz:
                out.append(f"  - *Tożsamość (encyklopedia):* {'; '.join(toz)}")
            historie = enc_entry.get("historie", ())
            pierwsza_ok = False
            for idx_h, item in enumerate(historie, 1):
                if isinstance(item, (list, tuple)):
                    cz = [self.pl.tekst(k) for k in item if k]
                    cz = [c for c in cz if c]
                    h_txt = " — ".join(cz) if cz else None
                elif isinstance(item, str):
                    h_txt = self.pl.tekst(item)
                else:
                    h_txt = None
                if not h_txt:
                    continue
                if not pierwsza_ok:
                    pierwsza_ok = True
                    out.append(f"  - *Biografia (wpis 1):* {h_txt}")
                else:
                    dalsze_linie_tej_postaci.append(f"- **Wpis biograficzny {idx_h}:** {h_txt}")

            pid = enc_entry["id"]
            glosy = self.baza.glosy_postaci.get(pid, ())
            for t_kl, d_kl in glosy[:2]:
                g_txt = self.pl.tekst(d_kl, jedna_linia=True)
                if g_txt:
                    g_tyt = self.pl.tekst(t_kl, jedna_linia=True) if t_kl else None
                    out.append(f"  - *Cytat postaci" + (f" ({g_tyt})" if g_tyt else "") + f":* „{g_txt}”")

        for mr in mistrz_rids:
            id_kl = self.baza.pierwszy_klucz("school_chuancheng_npc_data", mr, "generation_identity", z_w2=False)
            ds_kl = self.baza.pierwszy_klucz("school_chuancheng_npc_data", mr, "generation_description", z_w2=False)
            id_pl = self.pl.tekst(id_kl, jedna_linia=True)
            ds_pl = self.pl.tekst(ds_kl)
            if id_pl or ds_pl:
                out.append("  - *Dziedzictwo sekty:* " + " — ".join(x for x in (id_pl, ds_pl) if x))

        for br in boss_rids:
            dng = self.pl.tekst(self.baza.pierwszy_klucz("single_world_boss_data", br, "sidepage_danger_txt", z_w2=False), jedna_linia=True)
            dsc = self.pl.tekst(self.baza.pierwszy_klucz("single_world_boss_data", br, "sidepage_boss_desc", z_w2=False))
            txt_b = self.pl.tekst(self.baza.pierwszy_klucz("single_world_boss_data", br, "sidepage_boss_txt", z_w2=False))
            czesci = [c for c in (dng, dsc, txt_b) if c]
            if czesci:
                out.append(f"  - *Profil World Bossa:* {' — '.join(czesci)}")

        for fbr in fuben_boss_rids:
            umiej = []
            for sk_i in range(1, 10):
                sn = self.pl.tekst(self.baza.pierwszy_klucz("fuben_boss_tips", fbr, f"boss_skill{sk_i}_name", z_w2=False), jedna_linia=True)
                si = self.pl.tekst(self.baza.pierwszy_klucz("fuben_boss_tips", fbr, f"boss_skill{sk_i}_intro", z_w2=False), jedna_linia=True)
                if sn or si:
                    umiej.append(f"**{sn or f'Atak {sk_i}'}:** {si}" if si else f"**{sn}**")
            if umiej:
                out.append(f"  - *Umiejętności bossa (`fuben_boss_tips`):* {'; '.join(umiej)}")

        for ar in amity_rids:
            s1 = self.pl.tekst(self.baza.pierwszy_klucz("npc_amity_relation_data", ar, "story_1", z_w2=False))
            if s1:
                out.append(f"  - *Relacja / historia 1 (`npc_amity`):* {s1}")
            for st_i in range(2, 5):
                sn_txt = self.pl.tekst(self.baza.pierwszy_klucz("npc_amity_relation_data", ar, f"story_{st_i}", z_w2=False))
                if sn_txt:
                    dalsze_linie_tej_postaci.append(f"- *Relacja / historia {st_i} (`npc_amity`):* {sn_txt}")

        if dalsze_linie_tej_postaci:
            out.append("  - *Uwaga bezspoilerowa:* dalsze wpisy biograficzne/relacyjne znajdują się na końcu tego pliku w sekcji „Dalsze wpisy encyklopedii postaci i relacji”.")
            dalsze_wpisy_buf.append((imie_pl, dalsze_linie_tej_postaci))

        return out

    def _buduj_kontekst_scen_md(
        self,
        epizody: list[_Epizod],
        uzyte_klucze_ep: set[str] | None = None,
        uzyte_zadania: set[int] | None = None,
    ) -> tuple[ZbudowanyPlik, dict]:
        ix = self.ix
        baza = self.baza
        uzyte_klucze: set[str] = uzyte_klucze_ep if uzyte_klucze_ep is not None else set()
        uzyte_zadania_set: set[int] = set(uzyte_zadania or ())

        # 1. Zbiorcze szybkie skanowanie Aho-Corasick dla wszystkich scen tego wydania
        wszystkie_sceny_skan: dict[str, tuple[str, set[int]]] = {
            sc.uid: (sc.tekst_zh_do_skanu, sc.przestrzenie)
            for ep in epizody
            for sc in ep.sceny
            if sc.tekst_zh_do_skanu
        }
        wzmianki_per_scena = pc.skanuj_wzmianki_w_scenach(baza, wszystkie_sceny_skan)

        # Stan śledzenia pierwszego wystąpienia (anty-duplikacja w `kontekst_scen.md`)
        pierwsze_postacie: dict[str, str] = {}   # id_kanoniczne -> "Scena E.S"
        pierwsze_opisy_postaci: dict[str, str] = {}  # id_kanoniczne -> lokalny opis z pierwszego wystąpienia
        pierwsze_rekordy: dict[tuple[str, str], str] = {}  # (tbl, rid) -> "Scena E.S"
        pierwsze_podobszary: dict[str, str] = {}  # area_kl -> "Scena E.S"
        uzyte_rekordy: dict[str, set[str]] = defaultdict(set)
        uzyte_postacie_enc: set[int] = set()
        uzyte_amity: set[str] = set()
        uzyte_bossy: set[str] = set()
        uzyte_mistrzowie: set[str] = set()
        uzyte_dark: set[str] = set()
        uzyte_ending: set[str] = set()
        dalsze_wpisy_spotkanych: list[tuple[str, list[str]]] = []
        widziane_dalsze_klucze: set[str] = set()

        lines: list[str] = [
            "# Where Winds Meet — Skonsolidowany kontekst scen",
            "",
            "Towarzysz kontekstowy 1:1 do równoległego pliku `epizody.md`. Zawiera powiązane",
            "karty postaci, opisy NPC z obsady, frakcje, miejsca, poezję lokacji, karty ładowania,",
            "księgi, zapiski regionalne, poszlaki, listy, przedmioty, sztuki walki oraz wątki cienia",
            "pod identycznymi numerami `Epizod E` i `Scena E.S`. Pozostały materiał ze świata gry",
            "spoza scen i sekwencji znajdziesz podzielony według rodzajów w pliku `dodatkowe.md`.",
            "",
            "## Zakres i zasady odczytu",
            "",
            "- **Numeracja 1:1:** nagłówki `Epizod E` i `Scena E.S` odpowiadają dokładnie numerom w `epizody.md`.",
            "- **Warstwy powiązań:** łączymy (1) bezpośrednie relacje z `index/` (`tasks`, `task_group_info`, `task_progress_light_info`, `sceny.o`, `entity_attr`, `world_view_person_*`, `opcje_npc`, `guider_task`, `region_game_config`, `spaces.*.region`), (2) rozpoznania tekstowe z dialogów, opisów zadań i tytułów obsady (automat Aho-Corasick po frazach źródłowych), oraz (3) poszlaki, listy, maile i księgi powiązane jednoznacznym imieniem własnym postaci danej sceny.",
            "- **Anty-duplikacja:** każde hasło (postać, frakcja, miejsce, przedmiot, księga, poszlaka, technika) pojawia się w pełni przy pierwszym wystąpieniu; kolejne sceny podają zwięzły odsyłacz do `Scena E.S`.",
            "- **Ochrona przed spoilerami:** w kartach przy scenach pokazujemy wyłącznie pierwszy wpis biograficzny postaci z encyklopedii oraz pierwszą historię relacji (`npc_amity`); dalsze odblokowywane wpisy spotkanych bohaterów umieszczono w sekcji końcowej dokumentu.",
            "- **Zasady języka:** " + (
                "tryb `--podglad-en` (angielski podgląd układu)."
                if getattr(self.pl, "jest_podgladem_en", False)
                else "wyłącznie język polski (nieprzetłumaczone wpisy są pomijane lub oznaczone w trybie `--zakres wszystko`)."
            ),
            "",
        ]

        done_ctx = 0
        all_ctx = 0

        def _oznaczenie_powtorzenia(tbl: str, rid: str, tytul_baz: str, sc_label: str, powt_buf: list[tuple[str, str]]) -> bool:
            """Zwróć True jeśli to powtórzenie (dopisuje zwięźle do `powt_buf`), False dla pierwszego wystąpienia."""
            kl = (tbl, rid)
            if kl in pierwsze_rekordy:
                powt_buf.append((tytul_baz, pierwsze_rekordy[kl]))
                return True
            pierwsze_rekordy[kl] = sc_label
            uzyte_rekordy[tbl].add(rid)
            return False

        def _dopisz_powtorzenia(target_lines: list[str], powt_buf: list[tuple[str, str]]) -> None:
            if not powt_buf:
                return
            widziane_nazwy: set[str] = set()
            wpisy: list[str] = []
            for nazwa_p, sc_p in powt_buf:
                if nazwa_p in widziane_nazwy:
                    continue
                widziane_nazwy.add(nazwa_p)
                wpisy.append(f"{nazwa_p} (*{sc_p}*)")
            if wpisy:
                target_lines.append(f"- *Wcześniej opisane:* {', '.join(wpisy)}")

        # ---- RENDEROWANIE EPIZODÓW I SCEN W `kontekst_scen.md` ----
        for ep in epizody:
            lines.append(f"## Epizod {ep.nr} — {ep.tytul}")
            lines.append("")

            # Kontekst na poziomie Epizodu (grupa zadań / rozdział / Dark Surge)
            ep_meta_lines: list[str] = []
            if ep.grupa is not None:
                gid_s = str(ep.grupa)
                for act_id, target_gr in pc.AKTY_FABULARNE_DO_GRUPY.items():
                    if target_gr == ep.grupa:
                        n_kl = baza.pierwszy_klucz("main_storyline_activity_config", act_id, "name", z_w2=False)
                        d_kl = baza.pierwszy_klucz("main_storyline_activity_config", act_id, "des", z_w2=False)
                        n_pl = self.pl.tekst(n_kl, jedna_linia=True)
                        d_pl = self.pl.tekst(d_kl)
                        if d_pl:
                            ep_meta_lines.append(f"- **Akt fabularny ({n_pl or gid_s}):** {d_pl}")

                for col_k, col_lbl in (
                    ("before_fetch_des", "Wprowadzenie przed podjęciem wątku"),
                    ("qiyu_chufa_tip", "Wskazówka rozpoczęcia"),
                    ("qiyu_jiequ_tip", "Wskazówka podjęcia"),
                    ("unlock_des[]", "Warunek odblokowania"),
                    ("touch_suc_discr", "Zaliczenie odkrycia"),
                    ("finish_des[]", "Podsumowanie zakończenia"),
                    ("finish_summarize", "Finałowa kronika grupy"),
                ):
                    vals = [
                        self._tekst(k, fallback_label=col_lbl.lower())
                        for k in baza.wszystkie_klucze("task_group_info", gid_s, col_k)
                    ]
                    vals = [v for v in vals if v]
                    if vals:
                        ep_meta_lines.append(f"- **{col_lbl}:** {' / '.join(dict.fromkeys(vals))}")

                for srow in self.streszczenia_grupy.get(ep.grupa, ()):
                    s_pl = self._tekst(srow.get("tekst"), fallback_label="streszczenia fabuły")
                    if s_pl:
                        ep_meta_lines.append(f"- **Kronika rozdziału (`plot_recap_data`):** {s_pl}")

                # Dark Surge przypisane do aktu (1->1xx, 4->2xx, 6->3xx, 7->4xx)
                dark_pref = next((p for p, g in pc.DARK_GRUPA_DO_AKTU.items() if g == ep.grupa), None)
                if dark_pref is not None:
                    dark_lines: list[str] = []
                    for rid, _cols in baza.wiersze("task_progress_dark_info"):
                        if rid.isdigit() and int(rid) // 100 == dark_pref:
                            d_nm, d_det, dd, dt = self._zbierz_wiersz_tabeli_pl(
                                "task_progress_dark_info", rid, [("content", "Wątek"), ("introduction", "Opis")]
                            )
                            done_ctx += dd
                            all_ctx += dt
                            if d_nm or d_det:
                                uzyte_dark.add(rid)
                                tyt_d = d_nm or f"Wątek cienia #{rid}"
                                opis_d = d_det[0][1] if d_det else ""
                                dark_lines.append(f"- **{tyt_d}:** {opis_d}" if opis_d else f"- **{tyt_d}**")
                            # Powiązane kroki `task_progress_dark_group`
                            names = baza.wszystkie_klucze("task_progress_dark_group", rid, "[].name")
                            descs = baza.wszystkie_klucze("task_progress_dark_group", rid, "[].small_point_describe")
                            for idx_k in range(max(len(names), len(descs))):
                                kn = self.pl.tekst(names[idx_k], jedna_linia=True) if idx_k < len(names) else None
                                kd = self.pl.tekst(descs[idx_k]) if idx_k < len(descs) else None
                                if kn or kd:
                                    uzyte_rekordy["task_progress_dark_group"].add(rid)
                                    dark_lines.append(f"  - *{kn or f'Etap {idx_k+1}'}:* {kd or ''}".rstrip())
                    if dark_lines:
                        ep_meta_lines.append("- **Wątek cienia aktu (Dark Surge — tło poza głównym szlakiem):**")
                        ep_meta_lines.extend(f"  {dl}" for dl in dark_lines)

                for end_rid, target_gr in pc.ZAKONCZENIA_DO_GRUPY.items():
                    if target_gr == ep.grupa and end_rid in baza.tabele.get("task_progress_ending", {}):
                        en_nm, en_det, ed, et = self._zbierz_wiersz_tabeli_pl(
                            "task_progress_ending",
                            end_rid,
                            [
                                ("name", "Zakończenie"),
                                ("stuff_lock_description[]", "Warunek"),
                                ("stuff_unlock_description", "Odblokowanie"),
                                ("ending_descri", "Opis zakończenia"),
                            ],
                        )
                        done_ctx += ed
                        all_ctx += et
                        if en_nm or en_det:
                            uzyte_ending.add(end_rid)
                            ep_meta_lines.append(f"- **Zakończenie aktu ({en_nm or f'#{end_rid}'}):** " + " · ".join(f"{l}: {v}" for l, v in en_det))

            # Przestrzenie występujące w tym epizodzie
            ep_przestrzenie = sorted({sp for sc in ep.sceny for sp in sc.przestrzenie})
            miejsca_ep = [m for m in (self._miejsce(sp) for sp in ep_przestrzenie) if m]
            if miejsca_ep:
                ep_meta_lines.append(f"- **Lokacje / mapy epizodu:** {', '.join(dict.fromkeys(miejsca_ep))}")

            if ep_meta_lines:
                lines.append("#### Kontekst całego epizodu")
                lines.extend(ep_meta_lines)
                lines.append("")

            # ---- POSZCZEGÓLNE SCENY EPIZODU ----
            for sc in ep.sceny:
                sc_label = sc.etykieta_krotka
                lines.append(f"### {sc.naglowek}")
                lines.append("")
                sc_blocks: list[str] = []
                wzmianki = wzmianki_per_scena.get(sc.uid, {})

                # 1. Zadanie, dziennik, Bright Tide, opcje NPC i wskazówki UI
                zad_lines: list[str] = []
                if sc.zadanie_id is not None and sc.pokaz_zadanie_info:
                    trow = ix.zadania.get(sc.zadanie_id, {})
                    cel_z = self.pl.tekst(trow.get("cel"), jedna_linia=True)
                    opis_z = self.pl.tekst(trow.get("opis"))
                    m_z = self._miejsce(trow.get("przestrzen"))
                    zad_lines.append(f"- **Zadanie #{sc.zadanie_id}:** {self._nazwa_zadania(sc.zadanie_id)}" + (f" *(miejsce: {m_z})*" if m_z else ""))
                    if cel_z:
                        zad_lines.append(f"  - *Cel w dzienniku:* {cel_z}")
                    if opis_z:
                        zad_lines.append(f"  - *Opis w dzienniku:* {opis_z}")

                    tid_s = str(sc.zadanie_id)
                    if tid_s in baza.tabele.get("task_progress_light_info", {}):
                        bt_nm, bt_det, bd, bt = self._zbierz_wiersz_tabeli_pl(
                            "task_progress_light_info", tid_s, [("content", "Tytuł"), ("introduction", "Opis")]
                        )
                        done_ctx += bd
                        all_ctx += bt
                        if bt_nm or bt_det:
                            uzyte_rekordy["task_progress_light_info"].add(tid_s)
                            zad_lines.append(f"  - *Kamień milowy (Bright Tide — {bt_nm or tid_s}):* {bt_det[0][1] if bt_det else ''}".rstrip())

                    if tid_s in baza.tabele.get("guider_task", {}):
                        gt_parts = []
                        for col_g in ("pop_title", "talk_content[]"):
                            for kl in baza.wszystkie_klucze("guider_task", tid_s, col_g):
                                v = self.pl.tekst(kl, jedna_linia=True)
                                if v:
                                    gt_parts.append(v)
                        if gt_parts:
                            uzyte_rekordy["guider_task"].add(tid_s)
                            zad_lines.append(f"  - *Wskazówka z gry (`guider_task`):* {' — '.join(dict.fromkeys(gt_parts))}")

                    if tid_s in baza.tabele.get("region_game_config", {}):
                        rg_kl = baza.pierwszy_klucz("region_game_config", tid_s, "name")
                        rg_pl = self.pl.tekst(rg_kl, jedna_linia=True)
                        if rg_pl:
                            uzyte_rekordy["region_game_config"].add(tid_s)
                            zad_lines.append(f"  - *Aktywność regionalna (`region_game_config`):* {rg_pl}")

                if sc.dialog_no is not None:
                    opcje = baza.opcje_npc_po_dialogu.get(sc.dialog_no, ())
                    for op_row in opcje:
                        op_txt = []
                        for opt in op_row.get("opcje", ()):
                            t_op = self.pl.tekst(opt.get("tekst"), jedna_linia=True)
                            if t_op:
                                p_str = str(opt.get("parametr") or "")
                                cel = f" → dialog {p_str}" if p_str.isdigit() else ""
                                op_txt.append(f"{t_op}{cel}")
                        if op_txt:
                            zad_lines.append(f"- *Opcje rozmowy z NPC (`opcje_npc`):* {' | '.join(op_txt)}")

                if sc.powtorka_row:
                    pno = sc.powtorka_row.get("no")
                    tyt_p = self._tytul_powtorki(pno)
                    if tyt_p:
                        zad_lines.append(f"- *Powiązana powtórka w dzienniku (#{pno}):* {tyt_p}")

                if zad_lines:
                    sc_blocks.append("#### Zadanie, dziennik i rozgrywka")
                    sc_blocks.extend(zad_lines)
                    sc_blocks.append("")

                # 2. Postacie w scenie + wzmiankowani bohaterowie + powiązane poszlaki/listy/księgi
                # Zbieramy kandydatów postaci dla tej sceny:
                # [(kanoniczny_id, rola_sceny, name_kl, tytul_kl, opis_kl, enc_pid)]
                postacie_sceny: list[tuple[str, str, str | None, str | None, str | None, int | None]] = []
                widziane_w_scenie: set[str] = set()
                nazwy_dla_posrednich: list[tuple[str, str]] = []  # (norm_zh, imie_pl)

                if sc.dialog_no is not None:
                    scena_raw = ix.sceny[sc.dialog_no]
                    for person in scena_raw.get("o", ()):
                        name_kl, tyt_raw, ops_raw, role_kind = self._dane_osoby_w_scenie(person)
                        if not name_kl:
                            continue
                        zh_n = (ix.zh(name_kl) or "").strip()
                        en_n = (ix.en(name_kl) or "").strip()
                        if role_kind in ("gracz", 1) or (person[0] in ("我", "player", "主角")) or zh_n in _GENERYCZNE_NAZWY_GRACZA_ZH or en_n.lower() in _GENERYCZNE_NAZWY_GRACZA_TXT:
                            continue
                        tyt_kl = tyt_raw or self.npc_tytul_po_nazwie.get(name_kl)
                        ops_kl = ops_raw or self.npc_opis_po_nazwie.get(name_kl)
                        enc = self.encyklopedia_po_kluczu.get(name_kl)
                        enc_pid = enc["id"] if enc else None
                        kan_id = f"enc:{enc_pid}" if enc_pid is not None else f"name:{zh_n or name_kl}"
                        if kan_id not in widziane_w_scenie:
                            widziane_w_scenie.add(kan_id)
                            postacie_sceny.append((kan_id, "w obsadzie", name_kl, tyt_kl, ops_kl, enc_pid))

                for m_kl, m_en in sc.mowcy_cutsceny:
                    if m_en and m_en in ("You Xia", "Me", "Player", "Main Character"):
                        continue
                    enc = (self.encyklopedia_po_en.get(m_en) if m_en else None) or (self.encyklopedia_po_kluczu.get(m_kl) if m_kl else None)
                    enc_pid = enc["id"] if enc else None
                    eff_kl = (enc["nazwa"] if enc and enc.get("nazwa") else m_kl)
                    zh_n = (ix.zh(eff_kl) or m_en or "").strip()
                    kan_id = f"enc:{enc_pid}" if enc_pid is not None else f"name:{zh_n or eff_kl}"
                    if kan_id not in widziane_w_scenie:
                        widziane_w_scenie.add(kan_id)
                        postacie_sceny.append(
                            (
                                kan_id,
                                "mówca w cutscenie",
                                eff_kl,
                                self.npc_tytul_po_nazwie.get(eff_kl) if eff_kl else None,
                                self.npc_opis_po_nazwie.get(eff_kl) if eff_kl else None,
                                enc_pid,
                            )
                        )

                for rid in wzmianki.get("encyklopedia", ()):
                    if rid.isdigit() and int(rid) in ix.encyklopedia:
                        enc_pid = int(rid)
                        kan_id = f"enc:{enc_pid}"
                        if kan_id not in widziane_w_scenie:
                            widziane_w_scenie.add(kan_id)
                            enc = ix.encyklopedia[enc_pid]
                            n_kl = enc.get("nazwa")
                            postacie_sceny.append(
                                (
                                    kan_id,
                                    "wspomniany w scenie",
                                    n_kl,
                                    self.npc_tytul_po_nazwie.get(n_kl) if n_kl else None,
                                    self.npc_opis_po_nazwie.get(n_kl) if n_kl else None,
                                    enc_pid,
                                )
                            )

                # Dodatkowi bossowie / mistrzowie / relacje / wizytówki znalezieni wprost przez automat AC
                for tbl_os, rola_lbl in (
                    ("single_world_boss_data", "World Boss wspomniany w scenie"),
                    ("school_chuancheng_npc_data", "postać sekty wspomniana w scenie"),
                    ("npc_amity_relation_data", "postać relacji wspomniana w scenie"),
                    ("cutscene_person_info_config", "postać z wizytówki wspomniana w scenie"),
                ):
                    col_n = {"single_world_boss_data": "boss_name", "school_chuancheng_npc_data": "generation_name", "npc_amity_relation_data": "amity_target_name", "cutscene_person_info_config": "name"}[tbl_os]
                    for rid in wzmianki.get(tbl_os, ()):
                        n_kl = baza.pierwszy_klucz(tbl_os, rid, col_n)
                        if not n_kl:
                            continue
                        zh_n = (ix.zh(n_kl) or "").strip()
                        enc = self.encyklopedia_po_kluczu.get(n_kl)
                        enc_pid = enc["id"] if enc else None
                        kan_id = f"enc:{enc_pid}" if enc_pid is not None else f"name:{zh_n or n_kl}"
                        if kan_id not in widziane_w_scenie:
                            widziane_w_scenie.add(kan_id)
                            postacie_sceny.append((kan_id, rola_lbl, n_kl, None, None, enc_pid))

                postacie_lines: list[str] = []
                dodatkowe_zh_z_postaci: list[str] = []
                for kan_id, rola_sceny, name_kl, tyt_kl, opis_kl, enc_pid in postacie_sceny:
                    enc_entry = ix.encyklopedia.get(enc_pid) if enc_pid is not None else None
                    eff_name_kl = (enc_entry.get("nazwa") if enc_entry and enc_entry.get("nazwa") else name_kl)
                    tmp_postac: set[str] = set()
                    with self.pl.zbieraj(tmp_postac):
                        imie_pl = self._tekst(eff_name_kl, fallback_label="imienia", jedna_linia=True) if eff_name_kl else None
                        if not imie_pl:
                            continue
                        tytul_pl = self.pl.tekst(tyt_kl, jedna_linia=True) if tyt_kl else None
                        opis_pl = self.pl.tekst(opis_kl) if opis_kl else None

                    # Dopasowania specjalnych kart po imieniu
                    klucze_szukania = {
                        pc._oczysc_do_dopasowania(x).lower()
                        for x in (
                            ix.zh(eff_name_kl) if eff_name_kl else "",
                            ix.en(eff_name_kl) if eff_name_kl else "",
                        )
                        if x
                    }
                    amity_rids = sorted({r for k in klucze_szukania for r in baza.amity_po_nazwie.get(k, ())}, key=_naturalny)
                    boss_rids = sorted({r for k in klucze_szukania for r in baza.boss_swiatowy_po_nazwie.get(k, ())}, key=_naturalny)
                    fuben_boss_rids = sorted({r for k in klucze_szukania for r in baza.boss_fuben_po_nazwie.get(k, ())}, key=_naturalny)
                    mistrz_rids = sorted({r for k in klucze_szukania for r in baza.mistrz_sekty_po_nazwie.get(k, ())}, key=_naturalny)
                    wiz_rids = sorted({r for k in klucze_szukania for r in baza.wizytowka_cutsceny_po_nazwie.get(k, ())}, key=_naturalny)

                    # Pomijamy bezimienne tłumy bez żadnego tytułu/opisu/karty (np. "Wieśniak" bez opisu)
                    ma_bogate_dane = bool(tytul_pl or opis_pl or enc_entry or amity_rids or boss_rids or fuben_boss_rids or mistrz_rids or wiz_rids)
                    if not ma_bogate_dane and rola_sceny == "w obsadzie":
                        continue
                    uzyte_klucze.update(tmp_postac)

                    if kan_id in pierwsze_postacie:
                        linia = f"- **{imie_pl}** *({rola_sceny})* — pełna karta przy pierwszym wystąpieniu: *{pierwsze_postacie[kan_id]}*"
                        if opis_pl and opis_pl != pierwsze_opisy_postaci.get(kan_id):
                            linia += f" *(lokalny opis: {opis_pl})*"
                        postacie_lines.append(linia)
                        continue

                    pierwsze_postacie[kan_id] = sc_label
                    if opis_pl:
                        pierwsze_opisy_postaci[kan_id] = opis_pl
                    if enc_pid is not None:
                        uzyte_postacie_enc.add(enc_pid)
                    uzyte_amity.update(amity_rids)
                    uzyte_bossy.update(boss_rids)
                    uzyte_mistrzowie.update(mistrz_rids)
                    for br in fuben_boss_rids:
                        uzyte_rekordy["fuben_boss_tips"].add(br)

                    if tyt_kl:
                        dodatkowe_zh_z_postaci.append(ix.zh(tyt_kl))
                    if opis_kl:
                        dodatkowe_zh_z_postaci.append(ix.zh(opis_kl))

                    # Zarejestruj do pośredniego przyciągania poszlak/listów/ksiąg jeśli unikalne imię własne
                    zh_imie_norm = pc._oczysc_do_dopasowania(ix.zh(eff_name_kl) if eff_name_kl else "").lower()
                    if zh_imie_norm and zh_imie_norm in baza.unikalne_postacie_zh:
                        nazwy_dla_posrednich.append((zh_imie_norm, imie_pl))

                    karta = self._renderuj_karte_postaci_pelna(
                        imie_pl=imie_pl,
                        rola_sceny=rola_sceny,
                        tytul_pl=tytul_pl,
                        opis_npc_pl=opis_pl,
                        enc_entry=enc_entry,
                        amity_rids=amity_rids,
                        boss_rids=boss_rids,
                        fuben_boss_rids=fuben_boss_rids,
                        mistrz_rids=mistrz_rids,
                        wiz_cut_rids=wiz_rids,
                        dalsze_wpisy_buf=dalsze_wpisy_spotkanych,
                    )
                    postacie_lines.extend(karta)

                if postacie_lines:
                    sc_blocks.append("#### Postacie i obsada sceny")
                    sc_blocks.extend(postacie_lines)
                    sc_blocks.append("")

                # Wzbogacenie wykrytych wzmianek o nazwy frakcji/organizacji występujących w opisach nowych postaci
                if dodatkowe_zh_z_postaci:
                    extra_wzm = pc.skanuj_wzmianki_w_scenach(baza, {"__extra": ("\n".join(dodatkowe_zh_z_postaci), sc.przestrzenie)}).get("__extra", {})
                    for etbl, erids in extra_wzm.items():
                        lst = wzmianki.setdefault(etbl, [])
                        for er in erids:
                            if er not in lst:
                                lst.append(er)

                # 3. Frakcje, sekty i ugrupowania
                frakcje_lines: list[str] = []
                frakcje_powt: list[tuple[str, str]] = []
                for rid in wzmianki.get("world_view_shili_data", ()):
                    nm, det, dd, dt = self._zbierz_wiersz_tabeli_pl(
                        "world_view_shili_data",
                        rid,
                        [
                            ("name", "Frakcja"),
                            ("introduction_short", "Motto / skrót"),
                            ("introduction_location", "Siedziba"),
                            ("introduction_long", "Historia i charakterystyka"),
                        ],
                    )
                    done_ctx += dd
                    all_ctx += dt
                    if not (nm or det):
                        continue
                    tyt_f = nm or f"Frakcja #{rid}"
                    if not _oznaczenie_powtorzenia("world_view_shili_data", rid, tyt_f, sc_label, frakcje_powt):
                        frakcje_lines.append(f"- **{tyt_f}**")
                        for lbl, val in det:
                            frakcje_lines.append(f"  - *{lbl}:* {val}")
                        # Powiązane kalendarium frakcji (`world_view_history_info`)
                        kal_items: list[str] = []
                        for hrid in baza.historia_po_frakcji.get(rid, ()):
                            hnm, hdet, hd, ht = self._zbierz_wiersz_tabeli_pl(
                                "world_view_history_info", hrid, [("name", "Wydarzenie"), ("time_1", "Era / rok"), ("time_2", "Data")]
                            )
                            done_ctx += hd
                            all_ctx += ht
                            if hnm or hdet:
                                uzyte_rekordy["world_view_history_info"].add(hrid)
                                pierwsze_rekordy[("world_view_history_info", hrid)] = sc_label
                                daty = " · ".join(v for _, v in hdet)
                                kal_items.append(f"{hnm or f'Wydarzenie #{hrid}'}" + (f" ({daty})" if daty else ""))
                        if kal_items:
                            frakcje_lines.append(f"  - *Kalendarium frakcji:* {'; '.join(kal_items)}")

                for rid in wzmianki.get("school_sect_chuancheng_data", ()):
                    pola_s = [("school_name", "Sekta"), *[(f"generation_description_{i}", f"Pokolenie {i}") for i in range(1, 11)]]
                    nm, det, dd, dt = self._zbierz_wiersz_tabeli_pl("school_sect_chuancheng_data", rid, pola_s)
                    done_ctx += dd
                    all_ctx += dt
                    if not (nm or det):
                        continue
                    tyt_s = nm or f"Sekta #{rid}"
                    if not _oznaczenie_powtorzenia("school_sect_chuancheng_data", rid, tyt_s, sc_label, frakcje_powt):
                        frakcje_lines.append(f"- **{tyt_s}** *(dziedzictwo sekty)*")
                        for lbl, val in det:
                            frakcje_lines.append(f"  - *{lbl}:* {val}")

                _dopisz_powtorzenia(frakcje_lines, frakcje_powt)
                if frakcje_lines:
                    sc_blocks.append("#### Frakcje i sekty")
                    sc_blocks.extend(frakcje_lines)
                    sc_blocks.append("")

                # 4. Lokacje, podobszary, poematy miejsc i karty ładowania
                lok_lines: list[str] = []
                lok_powt: list[tuple[str, str]] = []
                for rid_sp in wzmianki.get("space_region", ()):
                    kl_area = baza.podobszary_klucze.get(rid_sp)
                    area_pl = self.pl.tekst(kl_area, jedna_linia=True) if kl_area else None
                    if area_pl:
                        sp_id = rid_sp.partition(":")[0]
                        if kl_area in pierwsze_podobszary:
                            lok_powt.append((f"Podobszar: {area_pl}", pierwsze_podobszary[kl_area]))
                        else:
                            pierwsze_podobszary[kl_area] = sc_label
                            lok_lines.append(f"- **Podobszar: {area_pl}** *(potwierdzony obszar mapy #{sp_id})*")

                for tbl_l, kat_l, pola_l in (
                    ("display_poem_text_config", "Poemat miejsca", [("name", "Miejsce"), ("description[]", "Wiersz / poemat")]),
                    ("loading_base_config", "Karta świata / ładowania", [("title", "Tytuł"), ("tips[]", "Opis / wskazówka")]),
                    ("region_story_act_data", "Akt regionalny", [("name", "Nazwa"), ("backing_area", "Obszar")]),
                    ("normal_story_act_data", "Strefa opowieści", [("name", "Nazwa")]),
                    ("task_space_replay", "Przestrzeń fabularna", [("space_name", "Nazwa")]),
                    ("fuben_info", "Instancja / loch", [("instance_name", "Nazwa"), ("hard_level_description", "Opis"), ("suggest_qishu_title[]", "Zalecana technika"), ("suggest_qishu_hint[]", "Wskazówka")]),
                ):
                    for rid in wzmianki.get(tbl_l, ()):
                        nm, det, dd, dt = self._zbierz_wiersz_tabeli_pl(tbl_l, rid, pola_l)
                        done_ctx += dd
                        all_ctx += dt
                        if not (nm or det):
                            continue
                        tyt_l = nm or f"{kat_l} #{rid}"
                        if not _oznaczenie_powtorzenia(tbl_l, rid, tyt_l, sc_label, lok_powt):
                            lok_lines.append(f"- **{tyt_l}** *({kat_l})*")
                            for lbl, val in det:
                                lok_lines.append(f"  - *{lbl}:* {val}")

                _dopisz_powtorzenia(lok_lines, lok_powt)
                if lok_lines:
                    sc_blocks.append("#### Lokacje, poezja miejsc i opisy świata")
                    sc_blocks.extend(lok_lines)
                    sc_blocks.append("")

                # 5. Kalendarium, wyprawy, kompendium, zapiski i księgi
                wiedza_lines: list[str] = []
                wiedza_powt: list[tuple[str, str]] = []
                for rid in wzmianki.get("world_view_history_info", ()):
                    nm, det, dd, dt = self._zbierz_wiersz_tabeli_pl(
                        "world_view_history_info", rid, [("name", "Wydarzenie"), ("time_1", "Era / rok chiński"), ("time_2", "Data")]
                    )
                    done_ctx += dd
                    all_ctx += dt
                    if not (nm or det):
                        continue
                    tyt_h = nm or f"Wydarzenie #{rid}"
                    shili_nm = self.pl.tekst(baza.pierwszy_klucz("world_view_shili_data", str(int(rid) // 100), "name"), jedna_linia=True) if rid.isdigit() else None
                    et_h = f"{shili_nm}: {tyt_h}" if shili_nm else tyt_h
                    if not _oznaczenie_powtorzenia("world_view_history_info", rid, et_h, sc_label, wiedza_powt):
                        wiedza_lines.append(f"- **{et_h}** *(kalendarium)* — {'; '.join(f'{l}: {v}' for l, v in det)}")

                for rid in wzmianki.get("manual_items", ()):
                    nm, det, dd, dt = self._zbierz_wiersz_tabeli_pl(
                        "manual_items",
                        rid,
                        [("bowu_name", "Hasło"), ("describe", "Opis"), ("locate_describe", "Występowanie"), ("shiyi_show_word", "Cytat / przekaz"), ("shiyi_show_word_from", "Źródło")],
                    )
                    done_ctx += dd
                    all_ctx += dt
                    if not (nm or det):
                        continue
                    tyt_m = nm or f"Kompendium #{rid}"
                    if not _oznaczenie_powtorzenia("manual_items", rid, tyt_m, sc_label, wiedza_powt):
                        wiedza_lines.append(f"- **{tyt_m}** *(kompendium świata)*")
                        for lbl, val in det:
                            wiedza_lines.append(f"  - *{lbl}:* {val}")

                # Zapiski regionalne i księgi: bezpośrednie z tekstu + przypisane przez unikalną postać debiutującą w scenie
                zapiski_kandydaci: list[tuple[str, str]] = [(r, "wzmianka w scenie") for r in wzmianki.get("region_collect_jianwen_data", ())]
                ksiegi_kandydaci: list[tuple[str, str]] = [(r, "wzmianka w scenie") for r in wzmianki.get("book_config", ())]
                for zh_imie, pl_imie in nazwy_dla_posrednich:
                    for r in baza.zapiski_po_postaci.get(zh_imie, ()):
                        zapiski_kandydaci.append((r, f"powiązane przez postać: {pl_imie}"))
                    for r in baza.ksiegi_po_postaci.get(zh_imie, ()):
                        ksiegi_kandydaci.append((r, f"powiązane przez postać: {pl_imie}"))

                widz_zapiski = set()
                for rid, powod in zapiski_kandydaci:
                    if rid in widz_zapiski:
                        continue
                    widz_zapiski.add(rid)
                    nm, det, dd, dt = self._zbierz_wiersz_tabeli_pl(
                        "region_collect_jianwen_data",
                        rid,
                        [("jianwen_title", "Tytuł"), ("jianwen_text", "Treść"), ("jianwen_from", "Źródło")],
                    )
                    done_ctx += dd
                    all_ctx += dt
                    if not (nm or det):
                        continue
                    tyt_j = nm or f"Zapisek #{rid}"
                    if ("region_collect_jianwen_data", rid) in pierwsze_rekordy:
                        if powod == "wzmianka w scenie":
                            wiedza_powt.append((tyt_j, pierwsze_rekordy[("region_collect_jianwen_data", rid)]))
                    else:
                        pierwsze_rekordy[("region_collect_jianwen_data", rid)] = sc_label
                        uzyte_rekordy["region_collect_jianwen_data"].add(rid)
                        wiedza_lines.append(f"- **{tyt_j}** *(zapisek regionalny — {powod})*")
                        for lbl, val in det:
                            wiedza_lines.append(f"  - *{lbl}:* {val}")

                widz_ksiegi = set()
                for rid, powod in ksiegi_kandydaci:
                    if rid in widz_ksiegi:
                        continue
                    widz_ksiegi.add(rid)
                    page_cols = sorted(
                        (c for c in baza.tabele.get("book_config", {}).get(rid, {}) if c.startswith("page_")),
                        key=lambda x: (0, int(x.split("_")[1])) if x.split("_")[1].isdigit() else (1, 0),
                    )
                    nm, det, dd, dt = self._zbierz_wiersz_tabeli_pl(
                        "book_config",
                        rid,
                        [("name", "Tytuł"), ("author", "Autor"), *[(p, f"Strona {idx_p}") for idx_p, p in enumerate(page_cols, 1)]],
                    )
                    done_ctx += dd
                    all_ctx += dt
                    if not (nm or det):
                        continue
                    tyt_b = nm or f"Księga #{rid}"
                    if ("book_config", rid) in pierwsze_rekordy:
                        if powod == "wzmianka w scenie":
                            wiedza_powt.append((tyt_b, pierwsze_rekordy[("book_config", rid)]))
                    else:
                        pierwsze_rekordy[("book_config", rid)] = sc_label
                        uzyte_rekordy["book_config"].add(rid)
                        wiedza_lines.append(f"- **{tyt_b}** *(księga z gry — {powod})*")
                        for lbl, val in det:
                            wiedza_lines.append(f"  - *{lbl}:* {val}")

                _dopisz_powtorzenia(wiedza_lines, wiedza_powt)
                if wiedza_lines:
                    sc_blocks.append("#### Kalendarium, kompendium, zapiski i księgi")
                    sc_blocks.extend(wiedza_lines)
                    sc_blocks.append("")

                # 6. Poszlaki, dochodzenia, listy i korespondencja
                trop_lines: list[str] = []
                trop_powt: list[tuple[str, str]] = []
                for rid in wzmianki.get("ever_know_content_data", ()):
                    nm, _, dd, dt = self._zbierz_wiersz_tabeli_pl("ever_know_content_data", rid, [("title", "Wątek śledztwa")])
                    done_ctx += dd
                    all_ctx += dt
                    if nm and not _oznaczenie_powtorzenia("ever_know_content_data", rid, nm, sc_label, trop_powt):
                        trop_lines.append(f"- **Wątek dochodzenia:** {nm}")

                poszlaki_kand: list[tuple[str, str]] = []
                listy_kand: list[tuple[str, str]] = []
                maile_kand: list[tuple[str, str]] = []
                for zh_imie, pl_imie in nazwy_dla_posrednich:
                    for r in baza.poszlaki_po_postaci.get(zh_imie, ()):
                        poszlaki_kand.append((r, pl_imie))
                    for r in baza.listy_po_postaci.get(zh_imie, ()):
                        listy_kand.append((r, pl_imie))
                    for r in baza.maile_po_postaci.get(zh_imie, ()):
                        maile_kand.append((r, pl_imie))

                for tbl_k, tyt_kat, pola_k, kand_list in (
                    ("ever_know_clue_data", "Poszlaka", [("clue", "Poszlaka"), ("record", "Gdzie odnotowano")], poszlaki_kand),
                    ("tasks_envelop_data", "List / koperta z misji", [("to", "Adresat / tytuł"), ("from", "Nadawca"), ("text", "Treść"), ("melody_solved_text", "Rozwiązanie")], listy_kand),
                    ("emails_data", "Wiadomość / list", [("mail_title", "Tytuł"), ("sender_title", "Nadawca"), ("content", "Treść")], maile_kand),
                ):
                    widz_k = set()
                    for rid, pl_imie in kand_list:
                        if rid in widz_k or (tbl_k, rid) in pierwsze_rekordy:
                            continue
                        widz_k.add(rid)
                        nm, det, dd, dt = self._zbierz_wiersz_tabeli_pl(tbl_k, rid, pola_k)
                        done_ctx += dd
                        all_ctx += dt
                        if not (nm or det):
                            continue
                        pierwsze_rekordy[(tbl_k, rid)] = sc_label
                        uzyte_rekordy[tbl_k].add(rid)
                        tyt_p = nm or f"{tyt_kat} #{rid}"
                        trop_lines.append(f"- **{tyt_p}** *({tyt_kat} — powiązane przez postać: {pl_imie})*")
                        for lbl, val in det:
                            trop_lines.append(f"  - *{lbl}:* {val}")

                _dopisz_powtorzenia(trop_lines, trop_powt)
                if trop_lines:
                    sc_blocks.append("#### Poszlaki, listy i korespondencja")
                    sc_blocks.extend(trop_lines)
                    sc_blocks.append("")

                # 7. Przedmioty, ekwipunek, stroje, tytuły i sztuki walki
                rzeczy_lines: list[str] = []
                rzeczy_powt: list[tuple[str, str]] = []
                for tbl_r, kat_r, pola_r in (
                    ("equip_items", "Wyposażenie", [("name", "Nazwa"), ("describe_str", "Opis"), ("story_describe_str", "Historia")]),
                    ("stuff_items", "Przedmiot", [("name", "Nazwa"), ("brief_describe_str", "Skrót"), ("describe_str", "Opis"), ("story_describe_str", "Historia / pochodzenie")]),
                    ("fashion_items", "Strój / poza", [("name", "Nazwa"), ("describe_str", "Opis"), ("story_describe_str", "Historia")]),
                    ("title", "Tytuł", [("name", "Tytuł"), ("des", "Opis"), ("get_des", "Jak zdobyć")]),
                    ("kongfu", "Styl walki (Kongfu)", [("name", "Styl"), ("description", "Opis"), ("attr_tip[]", "Atut / typ")]),
                    ("xinfa", "Sztuka wewnętrzna (Xinfa)", [("name", "Sztuka"), ("passive_skill_brief_description", "Efekt / opis")]),
                    ("jianghu_skills", "Umiejętność Jianghu", [("jianghu_skill_name", "Umiejętność"), ("jianghu_description", "Opis"), ("jianghu_background", "Tło fabularne")]),
                    ("qishu_combat_data", "Zdolność bojowa (Qishu)", [("name", "Zdolność"), ("description", "Opis")]),
                ):
                    for rid in wzmianki.get(tbl_r, ()):
                        nm, det, dd, dt = self._zbierz_wiersz_tabeli_pl(tbl_r, rid, pola_r)
                        done_ctx += dd
                        all_ctx += dt
                        if not (nm or det):
                            continue
                        tyt_r = nm or f"{kat_r} #{rid}"
                        if not _oznaczenie_powtorzenia(tbl_r, rid, tyt_r, sc_label, rzeczy_powt):
                            rzeczy_lines.append(f"- **{tyt_r}** *({kat_r})*")
                            for lbl, val in det:
                                rzeczy_lines.append(f"  - *{lbl}:* {val}")

                _dopisz_powtorzenia(rzeczy_lines, rzeczy_powt)
                if rzeczy_lines:
                    sc_blocks.append("#### Wzmiankowane przedmioty, stroje, tytuły i sztuki walki")
                    sc_blocks.extend(rzeczy_lines)
                    sc_blocks.append("")

                # 8. Powiązane wpisy UI / poradników i osiągnięć (`widoki/`)
                ui_lines: list[str] = []
                ui_powt: list[tuple[str, str]] = []
                for tbl_u, kat_u, pola_u in (
                    ("guider_tujian_data", "Wpis przewodnika", [("manual_name", "Temat"), ("talk_title[]", "Nagłówek"), ("talk_content[]", "Treść")]),
                    ("ac_raw", "Osiągnięcie", [("achievement_name", "Osiągnięcie"), ("achievement_info", "Warunek"), ("achievement_text", "Opis")]),
                ):
                    for rid in wzmianki.get(tbl_u, ()):
                        nm, det, dd, dt = self._zbierz_wiersz_tabeli_pl(tbl_u, rid, pola_u)
                        done_ctx += dd
                        all_ctx += dt
                        if not (nm or det):
                            continue
                        tyt_u = nm or f"{kat_u} #{rid}"
                        if not _oznaczenie_powtorzenia(tbl_u, rid, tyt_u, sc_label, ui_powt):
                            ui_lines.append(f"- **{tyt_u}** *({kat_u})*")
                            for lbl, val in det:
                                ui_lines.append(f"  - *{lbl}:* {val}")

                _dopisz_powtorzenia(ui_lines, ui_powt)
                if ui_lines:
                    sc_blocks.append("#### Powiązane wpisy interfejsu i przewodników")
                    sc_blocks.extend(ui_lines)
                    sc_blocks.append("")

                if sc_blocks:
                    lines.extend(sc_blocks)
                else:
                    lines.append("*Brak dodatkowych powiązań kontekstowych dla tej sceny poza treścią skryptu w `epizody.md`.*")
                    lines.append("")

        # ---- SEKCJA KOŃCOWA: DALSZE WPISY SPOTKANYCH POSTACI (BEZ SPOILERÓW WCZESNYCH SCEN) ----
        dalsze_linie_sekcji: list[str] = []
        for imie_pl, wpisy_l in dalsze_wpisy_spotkanych:
            if imie_pl in widziane_dalsze_klucze:
                continue
            widziane_dalsze_klucze.add(imie_pl)
            dalsze_linie_sekcji.append(f"### {imie_pl} — dalsze wpisy odblokowywane w toku gry")
            dalsze_linie_sekcji.extend(wpisy_l)
            dalsze_linie_sekcji.append("")

        if dalsze_linie_sekcji:
            lines.append("## Dalsze wpisy encyklopedii postaci i relacji (odblokowywane w miarę postępów fabuły)")
            lines.append("")
            lines.append("*Poniżej znajdują się późniejsze wspomnienia bohaterów (`historie[1:]`) i dalsze stopnie relacji (`npc_amity_relation_data`) dla postaci spotkanych w scenach tego wydania. Pozostałe postacie i hasła spoza scen znajdują się w `dodatkowe.md`.*")
            lines.append("")
            lines.extend(dalsze_linie_sekcji)

        stat = {
            "epizodow": len(epizody),
            "postaci_przypisanych": len(pierwsze_postacie),
            "przetlumaczono": done_ctx,
            "wszystkich": all_ctx,
            "uzyte_klucze": uzyte_klucze,
            "uzyte_zadania": uzyte_zadania_set,
            "uzyte_rekordy": uzyte_rekordy,
            "uzyte_postacie_enc": uzyte_postacie_enc,
            "uzyte_amity": uzyte_amity,
            "uzyte_bossy": uzyte_bossy,
            "uzyte_mistrzowie": uzyte_mistrzowie,
            "uzyte_dark": uzyte_dark,
            "uzyte_ending": uzyte_ending,
        }
        return (
            ZbudowanyPlik(
                nazwa="kontekst_scen.md",
                tytul="Skonsolidowany kontekst scen",
                opis="Biografie postaci, opisy NPC, frakcje, miejsca, księgi, poszlaki, przedmioty i sztuki walki pod każdą sceną.",
                linie=lines,
                statystyka={
                    "epizodow": len(epizody),
                    "postaci_przypisanych": len(pierwsze_postacie),
                    "przetlumaczono": done_ctx,
                    "wszystkich": all_ctx,
                },
            ),
            stat,
        )

    # -------------------------------------------------------- budowa `dodatkowe.md` (100% pozostałego materiału poza scenami)

    def _buduj_dodatkowe_md(self, epizody: list[_Epizod], stan_kontekstu: dict) -> ZbudowanyPlik:
        ix = self.ix
        baza = self.baza
        uzyte_klucze: set[str] = set(stan_kontekstu.get("uzyte_klucze") or ())
        uzyte_zadania: set[int] = set(stan_kontekstu.get("uzyte_zadania") or ())
        uzyte_rekordy: dict[str, set[str]] = {k: set(v) for k, v in (stan_kontekstu.get("uzyte_rekordy") or {}).items()}
        uzyte_postacie_enc: set[int] = set(stan_kontekstu.get("uzyte_postacie_enc") or ())
        uzyte_amity: set[str] = set(stan_kontekstu.get("uzyte_amity") or ())
        uzyte_bossy: set[str] = set(stan_kontekstu.get("uzyte_bossy") or ())
        uzyte_mistrzowie: set[str] = set(stan_kontekstu.get("uzyte_mistrzowie") or ())
        uzyte_dark: set[str] = set(stan_kontekstu.get("uzyte_dark") or ())
        uzyte_ending: set[str] = set(stan_kontekstu.get("uzyte_ending") or ())

        sekcje_tytuly = [
            (1, "Bohaterowie, NPC, relacje, bossowie i tytuły"),
            (2, "Zadania, wątki cienia, zakończenia i wskazówki"),
            (3, "Przedmioty, wyposażenie, stroje i budowle"),
            (4, "Encyklopedia świata, historia, księgi, poszlaki i listy"),
            (5, "Świat, regiony, miejsca i lokacje"),
            (6, "Sztuki walki, umiejętności, efekty i przeciwnicy"),
            (7, "Rozmowy, wybory i komunikaty poza scenami"),
            (8, "Osiągnięcia, poradniki, interfejs i systemy gry"),
            (9, "Pozostałe tabele i teksty bez przypisanej tabeli"),
        ]
        kategoria_na_sekcje = {
            "00_postacie": 1,
            "01_zadania": 2,
            "03_przedmioty": 3,
            "06_encyklopedia_i_ksiegi": 4,
            "05_swiat_i_miejsca": 5,
            "04_walka_i_umiejetnosci": 6,
            "02_wybory_i_rozmowy": 7,
            "07_komunikaty": 7,
            "08_interfejs_i_systemy": 8,
            "09_pozostale": 9,
            bp.BEZ_ZRODLA: 9,
        }

        bogate_linie: dict[int, list[str]] = defaultdict(list)
        done_dod = 0
        all_dod = 0

        def _dodaj_tabele(
            sec_id: int,
            tytul_kat: str,
            tbl: str,
            map_col: list[tuple[str, str]],
            *,
            jak_lista: bool = False,
            dom_pref: str = "Wpis",
            wykluczone_id: set[str] | None = None,
            uzyj_w2: bool = True,
        ) -> None:
            nonlocal done_dod, all_dod
            uzyte = set(uzyte_rekordy.get(tbl, set()))
            if wykluczone_id:
                uzyte |= wykluczone_id
            rows = [(rid, cols) for rid, cols in baza.wiersze(tbl) if rid not in uzyte]
            if not rows:
                return
            wiersze_tab: list[list[str]] = []
            lista_out: list[str] = []
            d_s = 0
            t_s = 0
            for rid, _cols in rows:
                nm, det, dd, dt = self._zbierz_wiersz_tabeli_pl(tbl, rid, map_col, uzyj_w2=uzyj_w2)
                d_s += dd
                t_s += dt
                if not self._ma_dopuszczalne_pokrycie(dd, dt):
                    continue
                if jak_lista:
                    tyt = nm or f"{dom_pref} #{rid}"
                    lista_out.append(f"#### {tyt}")
                    for lbl, val in det:
                        lista_out.append(f"- **{lbl}:** {val}")
                    lista_out.append("")
                else:
                    det_map = dict(det)
                    row_vals = [nm or f"{dom_pref} #{rid}"] + [det_map.get(lbl, "").replace("\n", " ") for _, lbl in map_col[1:]]
                    if any(row_vals):
                        wiersze_tab.append(row_vals)
            done_dod += d_s
            all_dod += t_s
            out = bogate_linie[sec_id]
            if jak_lista and lista_out:
                out.append(f"### {tytul_kat} ({d_s}/{t_s})")
                out.append("")
                out.extend(lista_out)
            elif wiersze_tab:
                out.append(f"### {tytul_kat} ({d_s}/{t_s})")
                out.append("")
                out.extend(formatuj_tabele([lbl for _, lbl in map_col], wiersze_tab))
                out.append("")

        with self.pl.zbieraj(uzyte_klucze):
            # ---- FAZA 1: BOGATE KARTY I TABELE NIEPRZYPISANE DO SCEN ----

            # Sekcja 1: Bohaterowie, NPC, relacje, bossowie i tytuły
            enc_out: list[str] = []
            d_enc = 0
            t_enc = 0
            for pid, entry in sorted(ix.encyklopedia.items()):
                if pid in uzyte_postacie_enc:
                    continue
                hist_keys = [
                    k
                    for item in entry.get("historie", ())
                    for k in (item if isinstance(item, (list, tuple)) else [item])
                    if k
                ]
                glosy = baza.glosy_postaci.get(pid, ())
                glosy_slots = [k for pair in glosy for k in pair if k]
                slots = [
                    s
                    for s in [entry.get("nazwa"), entry.get("inna_nazwa"), entry.get("urodziny"), *entry.get("tozsamosc", ()), *hist_keys, *glosy_slots]
                    if s
                ]
                d_p, t_p = self._stat_slotow(slots)
                d_enc += d_p
                t_enc += t_p
                if not self._ma_dopuszczalne_pokrycie(d_p, t_p):
                    continue
                toz = [t for t in (self._tekst(k, jedna_linia=True) for k in entry.get("tozsamosc", ())) if t]
                hist_wypisy = []
                for idx_h, item in enumerate(entry.get("historie", ()), 1):
                    if isinstance(item, (list, tuple)):
                        cz = [self._tekst(k) for k in item if k]
                        cz = [c for c in cz if c]
                        if cz:
                            hist_wypisy.append(f"- **Wpis biograficzny {idx_h}:** {' — '.join(cz)}")
                    elif item:
                        hp = self._tekst(item)
                        if hp:
                            hist_wypisy.append(f"- **Wpis biograficzny {idx_h}:** {hp}")
                glos_wypisy = []
                for t_kl, d_kl in glosy:
                    g_txt = self.pl.tekst(d_kl, jedna_linia=True)
                    if g_txt:
                        g_tyt = self.pl.tekst(t_kl, jedna_linia=True) if t_kl else None
                        glos_wypisy.append(f"- **Cytat" + (f" ({g_tyt})" if g_tyt else "") + f":** „{g_txt}”")
                if not toz and not hist_wypisy and not glos_wypisy and self.zakres != "wszystko":
                    continue
                nazwa = self._tekst(entry.get("nazwa"), fallback_label="imienia", jedna_linia=True) or f"Postać #{pid}"
                inna = self._tekst(entry.get("inna_nazwa"), jedna_linia=True)
                ur = self.pl.tekst(entry.get("urodziny"), jedna_linia=True) if entry.get("urodziny") else None
                dod_tyt = [x for x in (inna, f"urodziny: {ur}" if ur else None) if x]
                enc_out.append(f"#### {nazwa}" + (f" ({'; '.join(dod_tyt)})" if dod_tyt else ""))
                if toz:
                    enc_out.append(f"- **Tożsamość:** {'; '.join(toz)}")
                enc_out.extend(hist_wypisy)
                enc_out.extend(glos_wypisy)
                enc_out.append("")
            done_dod += d_enc
            all_dod += t_enc
            if enc_out:
                bogate_linie[1].append(f"### Encyklopedia postaci spoza scen ({d_enc}/{t_enc})")
                bogate_linie[1].append("")
                bogate_linie[1].extend(enc_out)

            _dodaj_tabele(
                1,
                "Pozostałe relacje i wspomnienia bohaterów (`npc_amity_relation_data`)",
                "npc_amity_relation_data",
                [("amity_target_name", "Postać"), ("story_1", "Historia 1"), ("story_2", "Historia 2"), ("story_3", "Historia 3"), ("story_4", "Historia 4")],
                jak_lista=True,
                dom_pref="Relacja",
                wykluczone_id=uzyte_amity,
                uzyj_w2=False,
            )
            _dodaj_tabele(
                1,
                "World Bossowie (`single_world_boss_data`)",
                "single_world_boss_data",
                [("boss_name", "Boss"), ("sidepage_danger_txt", "Zagrożenie"), ("sidepage_boss_desc", "Opis"), ("sidepage_boss_txt", "Tło / charakterystyka")],
                jak_lista=True,
                dom_pref="Boss",
                wykluczone_id=uzyte_bossy,
                uzyj_w2=False,
            )
            _dodaj_tabele(
                1,
                "Bossowie instancji (`fuben_boss_tips`)",
                "fuben_boss_tips",
                [
                    ("boss_skill1_name", "Atak 1"), ("boss_skill1_intro", "Opis ataku 1"),
                    ("boss_skill2_name", "Atak 2"), ("boss_skill2_intro", "Opis ataku 2"),
                    ("boss_skill3_name", "Atak 3"), ("boss_skill3_intro", "Opis ataku 3"),
                    ("boss_skill4_name", "Atak 4"), ("boss_skill4_intro", "Opis ataku 4"),
                    ("boss_skill5_name", "Atak 5"), ("boss_skill5_intro", "Opis ataku 5"),
                    ("boss_skill6_name", "Atak 6"), ("boss_skill6_intro", "Opis ataku 6"),
                ],
                jak_lista=True,
                dom_pref="Boss instancji",
                uzyj_w2=False,
            )
            _dodaj_tabele(
                1,
                "Mistrzowie i postacie sekt (`school_chuancheng_npc_data`)",
                "school_chuancheng_npc_data",
                [("generation_name", "Postać"), ("generation_identity", "Rola w sekcie"), ("generation_description", "Opis")],
                jak_lista=True,
                dom_pref="Mistrz sekty",
                wykluczone_id=uzyte_mistrzowie,
                uzyj_w2=False,
            )
            _dodaj_tabele(
                1,
                "Wizytówki postaci z przerywników (`cutscene_person_info_config`)",
                "cutscene_person_info_config",
                [("name_en", "Postać"), ("base_info_en", "Opis / rola")],
                dom_pref="Wizytówka",
                uzyj_w2=False,
            )
            _dodaj_tabele(
                1,
                "Głosy i cytaty bohaterów (`world_view_person_voice`)",
                "world_view_person_voice",
                [("title", "Tytuł / okazja"), ("description", "Cytat")],
                dom_pref="Cytat",
            )
            _dodaj_tabele(
                1,
                "Tytuły i przydomki (`title`)",
                "title",
                [("name", "Tytuł"), ("des", "Opis"), ("get_des", "Jak zdobyć")],
                dom_pref="Tytuł",
            )

            # Sekcja 2: Zadania, wątki cienia, zakończenia i wskazówki
            zad_dod_rows: list[list[str]] = []
            d_zd = 0
            t_zd = 0
            for tid, trow in sorted(ix.zadania.items()):
                if tid in uzyte_zadania:
                    continue
                if self.tylko_watek_glowny and trow.get("typ") != uklad_scen.TYP_WATKU_GLOWNEGO:
                    continue
                slots_z = [s for s in (trow.get("nazwa"), trow.get("cel"), trow.get("opis")) if s]
                dz, tz = self._stat_slotow(slots_z)
                d_zd += dz
                t_zd += tz
                if not self._ma_dopuszczalne_pokrycie(dz, tz):
                    continue
                nz = self._tekst(trow.get("nazwa"), fallback_label="nazwy", jedna_linia=True) if trow.get("nazwa") else None
                cz = self._tekst(trow.get("cel"), fallback_label="celu", jedna_linia=True) if trow.get("cel") else None
                oz = self._tekst(trow.get("opis"), fallback_label="opisu", jedna_linia=True) if trow.get("opis") else None
                mz = self._miejsce(trow.get("przestrzen")) if trow.get("przestrzen") is not None else None
                if nz or cz or oz:
                    zad_dod_rows.append([f"#{tid}", nz or "", cz or "", oz or "", mz or ""])
            done_dod += d_zd
            all_dod += t_zd
            if zad_dod_rows:
                bogate_linie[2].append(f"### Zadania nieprzypisane do scen (`tasks`, {d_zd}/{t_zd})")
                bogate_linie[2].append("")
                bogate_linie[2].extend(formatuj_tabele(["ID", "Nazwa zadania", "Cel", "Opis", "Miejsce"], zad_dod_rows))
                bogate_linie[2].append("")

            cien_lines: list[str] = []
            d_ci = 0
            t_ci = 0
            for rid, _ in baza.wiersze("task_progress_dark_info"):
                if rid in uzyte_dark:
                    continue
                nm, det, dd, dt = self._zbierz_wiersz_tabeli_pl("task_progress_dark_info", rid, [("content", "Wątek"), ("introduction", "Opis")])
                d_ci += dd
                t_ci += dt
                if nm or det:
                    cien_lines.append(f"- **{nm or f'Wątek cienia #{rid}'}:** {det[0][1] if det else ''}".rstrip())
            for rid, _ in baza.wiersze("task_progress_dark_group"):
                if rid in uzyte_rekordy.get("task_progress_dark_group", set()):
                    continue
                names = baza.wszystkie_klucze("task_progress_dark_group", rid, "[].name")
                descs = baza.wszystkie_klucze("task_progress_dark_group", rid, "[].small_point_describe")
                sd, st = self._stat_slotow([s for s in (*names, *descs) if s])
                d_ci += sd
                t_ci += st
                if not self._ma_dopuszczalne_pokrycie(sd, st):
                    continue
                for idx_k in range(max(len(names), len(descs))):
                    kn = self.pl.tekst(names[idx_k], jedna_linia=True) if idx_k < len(names) else None
                    kd = self.pl.tekst(descs[idx_k]) if idx_k < len(descs) else None
                    if kn or kd:
                        cien_lines.append(f"- **{kn or f'Wątek #{rid}.{idx_k+1}'}:** {kd or ''}".rstrip())
            for rid, _ in baza.wiersze("task_progress_ending"):
                if rid in uzyte_ending:
                    continue
                nm, det, dd, dt = self._zbierz_wiersz_tabeli_pl(
                    "task_progress_ending", rid, [("name", "Zakończenie"), ("stuff_lock_description[]", "Warunek"), ("stuff_unlock_description", "Odblokowanie"), ("ending_descri", "Opis")]
                )
                d_ci += dd
                t_ci += dt
                if nm or det:
                    cien_lines.append(f"- **Zakończenie ({nm or f'#{rid}'}):** " + " · ".join(f"{l}: {v}" for l, v in det))
            for rid, _ in baza.wiersze("task_prelude_custom_config"):
                nm, det, dd, dt = self._zbierz_wiersz_tabeli_pl(
                    "task_prelude_custom_config", rid, [("title_name", "Wspomnienie"), ("text_shang[]", "Tekst")]
                )
                d_ci += dd
                t_ci += dt
                if nm or det:
                    cien_lines.append(f"- **{nm or f'Wspomnienie #{rid}'}** *(fragmenty w nieokreślonej kolejności)*:")
                    for _, val in det:
                        for wers in val.splitlines():
                            if wers.strip():
                                cien_lines.append(f"  - {wers.strip()}")
            done_dod += d_ci
            all_dod += t_ci
            if cien_lines:
                bogate_linie[2].append(f"### Pozostałe wątki cienia (Dark Surge), zakończenia i wspomnienia ({d_ci}/{t_ci})")
                bogate_linie[2].append("")
                bogate_linie[2].extend(cien_lines)
                bogate_linie[2].append("")

            _dodaj_tabele(2, "Pozostałe kamienie milowe (`task_progress_light_info`)", "task_progress_light_info", [("content", "Tytuł"), ("introduction", "Opis")], dom_pref="Kamień milowy")
            _dodaj_tabele(2, "Zakończenia zadań (`tasks_ending_data`)", "tasks_ending_data", [("name", "Zakończenie")], dom_pref="Zakończenie")
            _dodaj_tabele(2, "Opisy niepowodzeń zadań (`task_fail_desc`)", "task_fail_desc", [("task_details_show", "Opis porażki")], dom_pref="Niepowodzenie")

            # Sekcja 3: Przedmioty, wyposażenie, stroje i budowle
            _dodaj_tabele(3, "Wyposażenie (broń, pancerz i narzędzia)", "equip_items", [("name", "Nazwa"), ("describe_str", "Opis"), ("story_describe_str", "Historia")], dom_pref="Przedmiot")
            _dodaj_tabele(3, "Przedmioty, artefakty i zasoby", "stuff_items", [("name", "Nazwa"), ("brief_describe_str", "Skrót"), ("describe_str", "Opis"), ("story_describe_str", "Historia / pochodzenie")], dom_pref="Przedmiot")
            _dodaj_tabele(3, "Stroje, wygląd i pozy (`fashion_items`)", "fashion_items", [("name", "Nazwa"), ("describe_str", "Opis"), ("story_describe_str", "Historia")], dom_pref="Strój")

            # Sekcja 4: Encyklopedia świata, historia, księgi, poszlaki i listy
            hist_uzyte = uzyte_rekordy.get("world_view_history_info", set())
            hist_rows: list[list[str]] = []
            d_hi = 0
            t_hi = 0
            for rid, _ in baza.wiersze("world_view_history_info"):
                if rid in hist_uzyte:
                    continue
                nm, det, dh, th = self._zbierz_wiersz_tabeli_pl(
                    "world_view_history_info", rid, [("name", "Wydarzenie"), ("time_1", "Era / rok chiński"), ("time_2", "Data")]
                )
                d_hi += dh
                t_hi += th
                if not self._ma_dopuszczalne_pokrycie(dh, th):
                    continue
                shili_id = str(int(rid) // 100) if rid.isdigit() else ""
                shili_nm = (self.pl.tekst(baza.pierwszy_klucz("world_view_shili_data", shili_id, "name"), jedna_linia=True) if shili_id else None) or (f"#{shili_id}" if shili_id else "")
                det_m = dict(det)
                hist_rows.append([shili_nm, nm or f"Wydarzenie #{rid}", det_m.get("Era / rok chiński", ""), det_m.get("Data", "")])
            done_dod += d_hi
            all_dod += t_hi
            if hist_rows:
                bogate_linie[4].append(f"### Kalendarium i wydarzenia historyczne ({d_hi}/{t_hi})")
                bogate_linie[4].append("")
                bogate_linie[4].extend(formatuj_tabele(["Frakcja", "Wydarzenie", "Era / rok chiński", "Data"], hist_rows))
                bogate_linie[4].append("")

            _dodaj_tabele(4, "Frakcje i ugrupowania (Shili)", "world_view_shili_data", [("name", "Frakcja"), ("introduction_short", "Motto"), ("introduction_location", "Siedziba"), ("introduction_long", "Historia")], jak_lista=True, dom_pref="Frakcja")
            _dodaj_tabele(4, "Linie dziedzictwa sekt", "school_sect_chuancheng_data", [("school_name", "Sekta"), *[(f"generation_description_{i}", f"Pokolenie {i}") for i in range(1, 11)]], jak_lista=True, dom_pref="Sekta")
            _dodaj_tabele(4, "Kompendium świata (Archiwum)", "manual_items", [("bowu_name", "Hasło"), ("describe", "Opis"), ("locate_describe", "Występowanie"), ("shiyi_show_word", "Cytat / przekaz"), ("shiyi_show_word_from", "Źródło")], jak_lista=True)
            _dodaj_tabele(4, "Opowieści i zapiski regionalne", "region_collect_jianwen_data", [("jianwen_title", "Tytuł"), ("jianwen_text", "Treść"), ("jianwen_from", "Źródło")], jak_lista=True)

            book_uzyte = uzyte_rekordy.get("book_config", set())
            book_out: list[str] = []
            d_bk = 0
            t_bk = 0
            for rid, cols in baza.wiersze("book_config"):
                if rid in book_uzyte:
                    continue
                page_cols = sorted(
                    (c for c in cols if c.startswith("page_")),
                    key=lambda x: (0, int(x.split("_")[1])) if x.split("_")[1].isdigit() else (1, 0),
                )
                nm, det, db, tb = self._zbierz_wiersz_tabeli_pl(
                    "book_config", rid, [("name", "Tytuł"), ("author", "Autor"), *[(p, f"Strona {idx_p}") for idx_p, p in enumerate(page_cols, 1)]]
                )
                d_bk += db
                t_bk += tb
                if not self._ma_dopuszczalne_pokrycie(db, tb):
                    continue
                autor_txt = next((v for l, v in det if l == "Autor"), None)
                book_out.append(f"#### {nm or f'Księga #{rid}'}" + (f" — *{autor_txt}*" if autor_txt else ""))
                for lbl, val in det:
                    if lbl != "Autor":
                        book_out.append(f"**{lbl}:**\n{val}\n")
                book_out.append("")
            done_dod += d_bk
            all_dod += t_bk
            if book_out:
                bogate_linie[4].append(f"### Księgi z gry ({d_bk}/{t_bk})")
                bogate_linie[4].append("")
                bogate_linie[4].extend(book_out)

            _dodaj_tabele(4, "Listy i koperty z misji", "tasks_envelop_data", [("to", "Adresat / tytuł"), ("from", "Nadawca"), ("text", "Treść listu"), ("melody_solved_text", "Rozwiązanie / szyfr")], jak_lista=True)
            _dodaj_tabele(4, "Wiadomości i korespondencja (`emails_data`)", "emails_data", [("mail_title", "Tytuł"), ("sender_title", "Nadawca"), ("content", "Treść"), ("end", "Podpis")], jak_lista=True, dom_pref="Wiadomość")
            _dodaj_tabele(4, "Wątki śledztw (`ever_know_content_data`)", "ever_know_content_data", [("title", "Wątek dochodzenia")], dom_pref="Śledztwo")
            _dodaj_tabele(4, "Notatnik poszlak i śledztw (`ever_know_clue_data`)", "ever_know_clue_data", [("clue", "Poszlaka"), ("record", "Gdzie odnotowano")])
            _dodaj_tabele(4, "Poezja miejsc i tablic (`display_poem_text_config`)", "display_poem_text_config", [("name", "Miejsce"), ("description[]", "Wiersz / poemat")], jak_lista=True, dom_pref="Poemat")
            _dodaj_tabele(4, "Karty świata i ekrany ładowania (`loading_base_config`)", "loading_base_config", [("title", "Tytuł"), ("tips[]", "Opis / wskazówka")], jak_lista=True, dom_pref="Karta")

            # Sekcja 5: Świat, regiony, miejsca i lokacje
            _dodaj_tabele(5, "Akty regionalne (`region_story_act_data`)", "region_story_act_data", [("name", "Nazwa"), ("backing_area", "Obszar")], dom_pref="Akt")
            _dodaj_tabele(5, "Strefy opowieści (`normal_story_act_data`)", "normal_story_act_data", [("name", "Nazwa")], dom_pref="Strefa")
            _dodaj_tabele(5, "Instancje i lochy (`fuben_info`)", "fuben_info", [("instance_name", "Nazwa"), ("hard_level_description", "Opis"), ("challenge_times_rule", "Zasady"), ("suggest_qishu_title[]", "Zalecana technika"), ("suggest_qishu_hint[]", "Wskazówka")], jak_lista=True, dom_pref="Instancja")
            _dodaj_tabele(5, "Opowieści z wypraw (`expedition_story_info`)", "expedition_story_info", [("story_title", "Tytuł"), ("story_detail", "Treść")], jak_lista=True, dom_pref="Wyprawa")
            _dodaj_tabele(5, "Kronika wypraw (`expedition_history`)", "expedition_history", [("jiyao_text", "Zapis"), ("jiyao_analysis", "Analiza")], jak_lista=True, dom_pref="Zapis wyprawy")
            _dodaj_tabele(5, "Aktywności regionalne (`region_game_config`)", "region_game_config", [("name", "Aktywność")], dom_pref="Aktywność")

            # Sekcja 6: Sztuki walki, umiejętności, efekty i przeciwnicy
            _dodaj_tabele(6, "Style walki (Kongfu)", "kongfu", [("name", "Styl"), ("description", "Opis"), ("attr_tip[]", "Atut / typ")], dom_pref="Styl")
            _dodaj_tabele(6, "Sztuki wewnętrzne (Xinfa)", "xinfa", [("name", "Sztuka"), ("passive_skill_brief_description", "Efekt / opis")], dom_pref="Sztuka")
            _dodaj_tabele(6, "Umiejętności Jianghu", "jianghu_skills", [("jianghu_skill_name", "Umiejętność"), ("function_description", "Rola"), ("jianghu_description", "Opis działania"), ("jianghu_background", "Tło fabularne")], dom_pref="Umiejętność")
            _dodaj_tabele(6, "Zdolności bojowe (Qishu)", "qishu_combat_data", [("name", "Zdolność"), ("description", "Opis")], dom_pref="Zdolność")

            # Sekcja 8: Osiągnięcia, poradniki, interfejs i systemy gry
            _dodaj_tabele(8, "Osiągnięcia (`ac_raw`)", "ac_raw", [("achievement_name", "Osiągnięcie"), ("achievement_info", "Warunek"), ("achievement_text", "Opis")], dom_pref="Osiągnięcie")
            _dodaj_tabele(8, "Przewodniki i encyklopedia rozgrywki (`guider_tujian_data`)", "guider_tujian_data", [("manual_name", "Temat"), ("talk_title[]", "Nagłówek"), ("talk_content[]", "Treść")], jak_lista=True, dom_pref="Poradnik")

        # ---- FAZA 2: SIEĆ BEZ DZIUR — 100% WSZYSTKICH POZOSTAŁYCH WPISÓW Z `index/` ----
        wszystkie_klucze_scen: set[str] = {
            self.pl.klucz_bazowy(el[2])
            for sc in ix.sceny.values()
            for el in sc.get("e", ())
            if len(el) > 2 and el[2]
        }
        warianty_po_kluczu: dict[str, list[tuple[str, int]]] = defaultdict(list)
        for vid, var in ix.warianty.items():
            k_var = var.get("k")
            if k_var:
                warianty_po_kluczu[k_var].append((f"@{vid}", int(var.get("w") or 0)))

        baza_src = self._rejestr._baza
        niepelne_wiersze: set[tuple[str, bool, str]] = set()
        if self.zakres == "kompletne-rozdzialy":
            for key, text in ix.teksty.items():
                if not text.zrodlo.strip():
                    continue
                zr = ix.zrodlo(text)
                if zr is None:
                    continue
                kind, _path, row_key = zr
                base_tbl = kind.removesuffix("__grey")
                jest_grey = kind != base_tbl
                if baza_src.tekst(key, jedna_linia=True) is None:
                    # Sprawdź czy istnieją warianty pasujące do płci
                    ma_war = any(
                        baza_src.tekst(slot, jedna_linia=True) is not None
                        for slot, w in warianty_po_kluczu.get(key, ())
                        if not ((w == 2 and self.plec == "bohater") or (w == 1 and self.plec == "bohaterka"))
                    )
                    if not ma_war:
                        niepelne_wiersze.add((base_tbl, jest_grey, row_key))

        # sec_id -> (base_tbl, jest_grey) -> row_key -> list[(path, row_label, tekst_wyj)]
        reszta_grupy: dict[int, dict[tuple[str, bool], dict[str, list[tuple[str, str | None, str]]]]] = defaultdict(
            lambda: defaultdict(lambda: defaultdict(list))
        )
        reszta_stat: dict[int, list[int]] = defaultdict(lambda: [0, 0])  # [done, total]

        for key, text in ix.teksty.items():
            if key in uzyte_klucze or not text.zrodlo.strip():
                continue
            zr = ix.zrodlo(text)
            if self.tylko_watek_glowny and key in wszystkie_klucze_scen:
                continue
            if zr is None:
                base_tbl, jest_grey, path, row_key = ("", False, "", key)
                kat = bp.BEZ_ZRODLA
            else:
                kind, path, row_key = zr
                base_tbl = kind.removesuffix("__grey")
                jest_grey = kind != base_tbl
                if self.zakres == "kompletne-rozdzialy" and (base_tbl, jest_grey, row_key) in niepelne_wiersze:
                    continue
                kat = bp.kategoria(kind)

            sec_id = kategoria_na_sekcje.get(kat, 9)
            wiersz_nazwa_kl = ix.nazwa_wiersza(text)
            row_label = baza_src.tekst(wiersz_nazwa_kl, jedna_linia=True) if wiersz_nazwa_kl else None

            tekst_bez = baza_src.tekst(key, jedna_linia=True)
            war_list = warianty_po_kluczu.get(key)
            if tekst_bez is not None:
                reszta_stat[sec_id][0] += 1
                reszta_stat[sec_id][1] += 1
                reszta_grupy[sec_id][(base_tbl, jest_grey)][row_key].append((path, row_label, tekst_bez))
            elif war_list:
                dostepne: list[tuple[int, str]] = []
                total_w = 0
                for slot_w, w_plec in war_list:
                    if w_plec == 2 and self.plec == "bohater":
                        continue
                    if w_plec == 1 and self.plec == "bohaterka":
                        continue
                    total_w += 1
                    wt = baza_src.tekst(slot_w, jedna_linia=True)
                    if wt is not None:
                        dostepne.append((w_plec, wt))
                reszta_stat[sec_id][0] += len(dostepne)
                reszta_stat[sec_id][1] += max(total_w, 1)
                if dostepne:
                    if self.plec == "oba" and len({t for _, t in dostepne}) > 1:
                        rendered_w = " / ".join(
                            (f"[♂ Bohater] {t}" if w == 1 else (f"[♀ Bohaterka] {t}" if w == 2 else t))
                            for w, t in dostepne
                        )
                    else:
                        rendered_w = dostepne[0][1]
                    reszta_grupy[sec_id][(base_tbl, jest_grey)][row_key].append((path, row_label, rendered_w))
                elif self.zakres == "wszystko":
                    reszta_grupy[sec_id][(base_tbl, jest_grey)][row_key].append((path, row_label, f"[Brak polskiego tekstu: {key}]"))
            else:
                reszta_stat[sec_id][1] += 1
                if self.zakres == "wszystko":
                    reszta_grupy[sec_id][(base_tbl, jest_grey)][row_key].append((path, row_label, f"[Brak polskiego tekstu: {key}]"))

        reszta_linie: dict[int, list[str]] = defaultdict(list)
        for sec_id, tbl_map in reszta_grupy.items():
            d_r, t_r = reszta_stat[sec_id]
            done_dod += d_r
            all_dod += t_r
            out_r = reszta_linie[sec_id]
            for base_tbl, jest_grey in sorted(tbl_map, key=lambda pair: (pair[0] == "", pair[0], pair[1])):
                row_map = tbl_map[(base_tbl, jest_grey)]
                if base_tbl == "":
                    out_r.append("### Pozostałe teksty bez przypisanej tabeli")
                else:
                    tbl_disp = base_tbl + ("__grey" if jest_grey else "")
                    opis_tbl = bp.OPIS_TABELI.get(base_tbl, "")
                    out_r.append(f"### Tabela: `{tbl_disp}`" + (f" — {opis_tbl}" if opis_tbl else ""))
                out_r.append("")
                for rkey in sorted(row_map, key=_naturalny):
                    pola_wiersza = row_map[rkey]
                    if len(pola_wiersza) == 1:
                        path, rlabel, val = pola_wiersza[0]
                        if base_tbl == "":
                            out_r.append(f"- **`{rkey}`:** {val}")
                        else:
                            etyk = f"{rlabel} (`#{rkey}`, `{path}`)" if rlabel else (f"`#{rkey}` · `{path}`" if path else f"`#{rkey}`")
                            out_r.append(f"- **{etyk}:** {val}")
                    else:
                        first_label = next((rl for _, rl, _ in pola_wiersza if rl), None)
                        nagl_w = f"{first_label} (`#{rkey}`)" if first_label else f"`#{rkey}`"
                        out_r.append(f"- **{nagl_w}:**")
                        for path, _rl, val in pola_wiersza:
                            out_r.append(f"  - *`{path or 'wartość'}`:* {val}")
                out_r.append("")

        # ---- FAZA 3: ZŁOŻENIE `dodatkowe.md` ----
        lines: list[str] = [
            "# Where Winds Meet — Materiał dodatkowy spoza scen (wg rodzaju)",
            "",
            "Pełny zbiór pozostałego materiału ze świata gry, który nie należy do scen ani sekwencji",
            "w `epizody.md` i nie został już wypisany jako przypisany kontekst w `kontekst_scen.md`.",
            "Wpisy ułożono przejrzyście według rodzaju materiału (bohaterowie, zadania, przedmioty,",
            "encyklopedia, lokacje, walka, rozmowy/komunikaty, interfejs i pozostałe tabele), aby",
            "podczas grania łatwo było odszukać dowolny element niewystępujący bezpośrednio przy scenie.",
            "",
            "- **Zasady języka:** " + (
                "tryb `--podglad-en` (angielski podgląd układu)."
                if getattr(self.pl, "jest_podgladem_en", False)
                else "wyłącznie język polski (nieprzetłumaczone wpisy są pomijane lub oznaczone w trybie `--zakres wszystko`)."
            ),
            "",
        ]

        ma_jakakolwiek_sekcje = False
        for sec_id, sec_tyt in sekcje_tytuly:
            b_lin = bogate_linie.get(sec_id)
            r_lin = reszta_linie.get(sec_id)
            if not b_lin and not r_lin:
                continue
            ma_jakakolwiek_sekcje = True
            lines.append(f"## {sec_id}. {sec_tyt}")
            lines.append("")
            if b_lin:
                lines.extend(b_lin)
            if r_lin:
                lines.extend(r_lin)

        if not ma_jakakolwiek_sekcje:
            lines.append("*Brak dodatkowych przetłumaczonych wpisów spoza scen i przypisanego kontekstu w tym wydaniu.*")
            lines.append("")

        return ZbudowanyPlik(
            nazwa="dodatkowe.md",
            tytul="Materiał dodatkowy spoza scen",
            opis="Cały pozostały materiał spoza scen i przypisanego kontekstu podzielony na rodzaje (bohaterowie, zadania, przedmioty, encyklopedia, świat, walka, komunikaty, interfejs).",
            linie=lines,
            statystyka={
                "epizodow": len(epizody),
                "przetlumaczono": done_dod,
                "wszystkich": all_dod,
            },
        )

    def buduj_z_epizodami(self) -> tuple[list[ZbudowanyPlik], list[_Epizod]]:
        epizody = self._zbierz_epizody()
        plik_epizody, uzyte_klucze_ep, uzyte_zadania = self._buduj_epizody_md(epizody)
        wszystkie_klucze = set(uzyte_klucze_ep)
        with self.pl.zbieraj(wszystkie_klucze):
            plik_kontekst, stan_kontekstu = self._buduj_kontekst_scen_md(epizody, wszystkie_klucze, uzyte_zadania)
        plik_dodatkowe = self._buduj_dodatkowe_md(epizody, stan_kontekstu)
        return [plik_epizody, plik_kontekst, plik_dodatkowe], epizody

    def buduj(self) -> list[ZbudowanyPlik]:
        pliki, _ = self.buduj_z_epizodami()
        return pliki


def _podziel_sekcje_po_podnaglowku(sekcja: list[str], limit_czysty: int) -> list[list[str]]:
    """Gdy pojedyncza sekcja `## ` przekracza limit, dziel ją wzdłuż podnagłówków `### `, powtarzając nagłówek `## `."""
    if sum(len(l.encode("utf-8")) + 1 for l in sekcja) <= limit_czysty:
        return [sekcja]
    nagl_h2 = sekcja[0]
    wstep_h2: list[str] = []
    podsekcje: list[list[str]] = []
    biezaca: list[str] | None = None
    for line in sekcja[1:]:
        if line.startswith("### "):
            if biezaca is not None:
                podsekcje.append(biezaca)
            biezaca = [line]
        elif biezaca is None:
            wstep_h2.append(line)
        else:
            biezaca.append(line)
    if biezaca is not None:
        podsekcje.append(biezaca)

    if len(podsekcje) <= 1:
        # Gdy nawet jedno `### ` przekracza limit (np. ogromna pojedyncza tabela lub lista), dziel po wierszach
        if len(podsekcje) == 1 and len(podsekcje[0]) > 40:
            sub = podsekcje[0]
            nagl_h3 = sub[0]
            tab_header: list[str] = []
            start_idx = 1
            if len(sub) >= 4 and not sub[1].strip() and sub[2].startswith("|") and sub[3].startswith("| -"):
                tab_header = [sub[2], sub[3]]
                start_idx = 4
            prefix = [nagl_h2, *wstep_h2, nagl_h3, "", *tab_header]
            prefix_b = sum(len(l.encode("utf-8")) + 1 for l in prefix)
            # Zgrupuj wiersze w atomowe rekordy (wiersz tabeli lub pozycja listy `- **...**` z podpunktami),
            # aby żaden podział nie dokładał kolejnego rekordu ponad `limit_czysty`.
            rekordy: list[list[str]] = []
            cur_rek: list[str] = []
            for line in sub[start_idx:]:
                is_tab_row_start = bool(
                    tab_header
                    and line.startswith("| ")
                    and line.split("|", 2)[1].strip()
                )
                rozpoczyna_nowy = bool(cur_rek) and (
                    line.startswith("- **")
                    or line.startswith("#### ")
                    or is_tab_row_start
                    or (not tab_header and not line.strip() and not cur_rek[0].startswith("- **"))
                )
                if rozpoczyna_nowy:
                    rekordy.append(cur_rek)
                    cur_rek = [line]
                else:
                    cur_rek.append(line)
            if cur_rek:
                rekordy.append(cur_rek)

            czesci: list[list[str]] = []
            cur_sub: list[str] = list(prefix)
            cur_b = prefix_b
            pad_b = 1 if tab_header else 0
            for rek in rekordy:
                rek_b = sum(len(l.encode("utf-8")) + 1 for l in rek)
                if len(cur_sub) > len(prefix) and cur_b + rek_b + pad_b > limit_czysty:
                    if tab_header:
                        cur_sub.append("")
                    czesci.append(cur_sub)
                    cur_sub = list(prefix)
                    cur_b = prefix_b
                cur_sub.extend(rek)
                cur_b += rek_b
            if len(cur_sub) > len(prefix):
                czesci.append(cur_sub)
            if len(czesci) > 1:
                return czesci
        return [sekcja]

    prefix_h2 = [nagl_h2, *wstep_h2]
    prefix_b = sum(len(l.encode("utf-8")) + 1 for l in prefix_h2)
    wynik: list[list[str]] = []
    cur_h2: list[str] = list(prefix_h2)
    cur_b = prefix_b
    for sub in podsekcje:
        sub_b = sum(len(l.encode("utf-8")) + 1 for l in sub)
        if len(cur_h2) > len(prefix_h2) and cur_b + sub_b > limit_czysty:
            wynik.append(cur_h2)
            cur_h2 = list(prefix_h2)
            cur_b = prefix_b
        if sub_b > limit_czysty:
            if len(cur_h2) > len(prefix_h2):
                wynik.append(cur_h2)
                cur_h2 = list(prefix_h2)
                cur_b = prefix_b
            for frag in _podziel_sekcje_po_podnaglowku([nagl_h2, *wstep_h2, *sub], limit_czysty):
                wynik.append(frag)
        else:
            cur_h2.extend(sub)
            cur_b += sub_b
    if len(cur_h2) > len(prefix_h2):
        wynik.append(cur_h2)
    return wynik or [sekcja]


def _podziel_na_czesci(plik: ZbudowanyPlik, limit_bajtow: int) -> list[tuple[str, list[str], dict]]:
    """Jeśli treść przekracza `limit_bajtow` (> 0), dziel ją na granicach `## ` (oraz awaryjnie `### `)."""
    pelny_tekst = "\n".join(plik.linie).rstrip("\n") + "\n"
    if limit_bajtow <= 0 or len(pelny_tekst.encode("utf-8")) <= limit_bajtow:
        return [(plik.nazwa, [pelny_tekst], plik.statystyka)]

    intro: list[str] = []
    surowe_sekcje: list[list[str]] = []
    biezaca: list[str] | None = None
    for line in plik.linie:
        if line.startswith("## "):
            if biezaca is not None:
                surowe_sekcje.append(biezaca)
            biezaca = [line]
        elif biezaca is None:
            intro.append(line)
        else:
            biezaca.append(line)
    if biezaca is not None:
        surowe_sekcje.append(biezaca)

    if not surowe_sekcje:
        return [(plik.nazwa, [pelny_tekst], plik.statystyka)]

    # Uwzględnij dłuższy tytuł z sufiksowanym numerem części (`— część 9999/9999`), żeby żaden
    # chunk po złożeniu nie przekroczył `limit_bajtow`.
    intro_max = [f"# {plik.tytul} — część 9999/9999", *intro[1:]]
    intro_b = sum(len(l.encode("utf-8")) + 1 for l in intro_max) + 2
    limit_sekcji = max(limit_bajtow - intro_b, max(limit_bajtow // 2, 1024))
    sekcje: list[list[str]] = []
    for sec in surowe_sekcje:
        sekcje.extend(_podziel_sekcje_po_podnaglowku(sec, limit_sekcji))

    if len(sekcje) <= 1:
        return [(plik.nazwa, [pelny_tekst], plik.statystyka)]

    czesc_grupy: list[list[list[str]]] = []
    cur: list[list[str]] = []
    cur_bytes = intro_b
    for sec in sekcje:
        sec_bytes = sum(len(l.encode("utf-8")) + 1 for l in sec)
        if cur and cur_bytes + sec_bytes > limit_bajtow:
            czesc_grupy.append(cur)
            cur = [sec]
            cur_bytes = intro_b + sec_bytes
        else:
            cur.append(sec)
            cur_bytes += sec_bytes
    if cur:
        czesc_grupy.append(cur)

    if len(czesc_grupy) == 1:
        return [(plik.nazwa, [pelny_tekst], plik.statystyka)]

    stem = Path(plik.nazwa).stem
    wynik: list[tuple[str, list[str], dict]] = []
    for idx, grupa in enumerate(czesc_grupy, 1):
        nazwa = f"{stem}_czesc_{idx:02d}.md"
        naglowek = [f"# {plik.tytul} — część {idx}/{len(czesc_grupy)}", *intro[1:]]
        linie = naglowek + [l for sec in grupa for l in sec]
        tresc = "\n".join(linie).rstrip("\n") + "\n"
        wynik.append((nazwa, [tresc], plik.statystyka))
    return wynik


def zapisz_czytanki(
    pliki: list[ZbudowanyPlik],
    wyj_katalog: Path,
    *,
    epizody: list[_Epizod] | None = None,
    wyj_zip: Path | None = None,
    limit_bajtow: int = DOMYSLNY_LIMIT_BAJTOW,
    zakres: str = "przetlumaczone",
    plec: str = "oba",
    wersja: str = "v1",
    zrodlo_przekladow: str = "",
    podglad_en: bool = False,
) -> dict:
    """Zapisz pliki czytanek (`epizody.md`, `kontekst_scen.md`, `dodatkowe.md`, `README.md`) oraz opcjonalny deterministyczny ZIP."""
    if wyj_katalog.exists():
        shutil.rmtree(wyj_katalog)
    wyj_katalog.mkdir(parents=True, exist_ok=True)

    zapisane: list[dict] = []
    for plik in pliki:
        for nazwa, chunk_texts, stat in _podziel_na_czesci(plik, limit_bajtow):
            text = "".join(chunk_texts)
            target = wyj_katalog / nazwa
            target.write_text(text, encoding="utf-8", newline="\n")
            zapisane.append(
                {
                    "plik": nazwa,
                    "tytul": plik.tytul,
                    "opis": plik.opis,
                    "bajtow": len(text.encode("utf-8")),
                    "statystyka": stat,
                }
            )

    zakres_opis = {
        "przetlumaczone": "wyłącznie przetłumaczone kwestie, wpisy i rozdziały z magazynu/zwrotki",
        "kompletne-rozdzialy": "wyłącznie sekcje i rozdziały przetłumaczone w 100%",
        "wszystko": "pełna struktura książki wraz z jawnymi miejscami `[Brak polskiego ...]`",
    }[zakres]
    plec_opis = {
        "oba": "oba warianty płci tam, gdzie się różnią (`[♂ Bohater]` / `[♀ Bohaterka]`)",
        "bohater": "ścieżka bohatera (wariant męski)",
        "bohaterka": "ścieżka bohaterki (wariant żeński)",
    }[plec]

    zasada_jezyka = (
        "- **Tryb techniczny (`--podglad-en`):** **podgląd angielski** z bazy gry wyłącznie do oceny formy i układu."
        if podglad_en
        else "- **Zasady tekstu:** wyłącznie język polski — brak automatycznego cofania do angielskiego ani chińskiego."
    )
    tytul_glowny = (
        f"# Where Winds Meet — Podgląd formy czytanek (EN, {wersja})"
        if podglad_en
        else f"# Where Winds Meet — Czytanki polskie ({wersja})"
    )
    kol_pokrycia = "Pokrycie EN" if podglad_en else "Pokrycie PL"

    readme: list[str] = [
        tytul_glowny,
        "",
        "Trzyplikowy zestaw `.md` do czytania fabuły, kontekstu scen i całej reszty materiału ze świata",
        "Where Winds Meet (wzorowany na układzie SRW Y). Scenariusz mieści się w `epizody.md`, powiązany",
        "kontekst pod każdą sceną w `kontekst_scen.md`, a pozostałe wpisy spoza scen — w `dodatkowe.md`.",
        "",
        f"- **Data wygenerowania:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"- **Zakres wydania:** {zakres} ({zakres_opis})",
        f"- **Wariant płci bohatera:** {plec} ({plec_opis})",
        *([f"- **Źródło przekładów:** {zrodlo_przekladow}"] if zrodlo_przekladow else []),
        zasada_jezyka,
        "",
        "## Spis plików",
        "",
        *formatuj_tabele(
            ["Plik", "Zawartość", kol_pokrycia, "Rozmiar"],
            [
                [
                    row["plik"],
                    row["opis"],
                    f"{row['statystyka'].get('przetlumaczono', 0)}/{row['statystyka'].get('wszystkich', 0)}",
                    f"{row['bajtow'] / 1024:.1f} KiB",
                ]
                for row in zapisane
            ],
        ),
        "",
        "## Jak czytać zestaw plików",
        "",
        "1. Otwórz `epizody.md` — znajdziesz tam czysty, numerowany scenariusz (`Epizod E` / `Scena E.S`)",
        "   od Prologu i Wątku Głównego po wątki poboczne i sekwencje cutscen.",
        "2. Równolegle otwórz `kontekst_scen.md` — pod identycznymi numerami `Epizod E` i `Scena E.S`",
        "   zebrano opisy NPC, karty postaci, frakcje, miejsca, poematy, księgi, poszlaki, listy,",
        "   przedmioty, sztuki walki oraz wątki cienia (`Dark Surge`), a na końcu dalsze wpisy",
        "   odblokowywane dla spotkanych postaci (bez spoilerów przy wczesnych scenach).",
        "3. Zajrzyj do `dodatkowe.md` — znajduje się tam cały pozostały materiał ze świata gry",
        "   spoza scen i przypisanego kontekstu, uporządkowany przejrzyście według rodzaju",
        "   (bohaterowie, zadania, przedmioty, encyklopedia, miejsca, walka, komunikaty, interfejs).",
        "",
    ]

    if epizody:
        readme.append("## Spis numerowanych epizodów")
        readme.append("")
        for ep in epizody:
            readme.append(f"- **Epizod {ep.nr}** — {ep.tytul} *(scen: {len(ep.sceny)}, {ep.done}/{ep.total})*")
        readme.append("")

    readme_text = "\n".join(readme)
    (wyj_katalog / "README.md").write_text(readme_text, encoding="utf-8", newline="\n")

    zip_info = None
    if wyj_zip is not None:
        wyj_zip.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(wyj_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
            for file_path in sorted(wyj_katalog.rglob("*")):
                if not file_path.is_file():
                    continue
                rel = file_path.relative_to(wyj_katalog).as_posix()
                info = zipfile.ZipInfo(rel, date_time=STALA_DATA_ZIP)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                zf.writestr(info, file_path.read_bytes())
        sha = hashlib.sha256(wyj_zip.read_bytes()).hexdigest()
        zip_info = {
            "zip": str(wyj_zip),
            "bajtow": wyj_zip.stat().st_size,
            "sha256": sha,
        }

    return {
        "format": FORMAT,
        "wersja": wersja,
        "zakres": zakres,
        "plec": plec,
        "katalog": str(wyj_katalog),
        "pliki": [{"plik": "README.md", "bajtow": len(readme_text.encode("utf-8"))}, *zapisane],
        "zip": zip_info,
    }


def _wczytaj_przeklady(
    ix: indeks_mod.Indeks,
    *,
    magazyn_dir: str | Path | None,
    zwrotki: list[str | Path],
    tylko_zwrotka: bool,
    pomin_bledne: bool,
) -> tuple[magazyn_mod.Magazyn, set[str] | None, str]:
    if tylko_zwrotka or magazyn_dir is None or not Path(magazyn_dir).exists():
        magazyn = magazyn_mod.Magazyn()
        zrodlo_opis = "tylko zwrotka" if zwrotki else "brak magazynu"
    else:
        magazyn = magazyn_mod.wczytaj(magazyn_dir)
        zrodlo_opis = f"magazyn `{magazyn_dir}`"

    tylko_klucze: set[str] | None = None
    if zwrotki:
        raport = import_zwrotki.importuj(ix, import_zwrotki.pliki_zwrotki(zwrotki), magazyn, mimo_tokenow=True)
        if raport["odrzucone"] and not pomin_bledne:
            raise CzytankiError(
                f"zwrotka ma {raport['odrzucone']} odrzuconych wpisów "
                "(popraw je albo dodaj --pomin-bledne)"
            )
        if tylko_zwrotka:
            tylko_klucze = set(magazyn.po_kluczu) | {f"@{ident}" for ident in magazyn.po_id}
        zrodlo_opis = (zrodlo_opis + " + " if not tylko_zwrotka and magazyn_dir and Path(magazyn_dir).exists() else "") + f"zwrotka ({len(zwrotki)} źródeł)"
    elif tylko_zwrotka:
        raise CzytankiError("--tylko-zwrotka wymaga podania --zwrotka")

    return magazyn, tylko_klucze, zrodlo_opis


def main(argv: list[str] | None = None) -> int:
    wypisz.utf8()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--indeks", default="index", help="katalog wyciągu index/")
    parser.add_argument("--magazyn", default="tlumaczenie", help="katalog magazynu tłumaczeń (domyślnie: tlumaczenie)")
    parser.add_argument("--zwrotka", nargs="+", default=[], help="opcjonalne pliki .md, katalogi albo .zip ze zwrotką")
    parser.add_argument("--tylko-zwrotka", action="store_true", help="użyj wyłącznie przekładów z --zwrotka")
    parser.add_argument("--pomin-bledne", action="store_true", help="pomiń odrzucone linie zwrotki zamiast przerywać")
    parser.add_argument(
        "--zakres",
        choices=("przetlumaczone", "kompletne-rozdzialy", "wszystko"),
        default="przetlumaczone",
        help="zakres treści: przetłumaczone (domyślnie), tylko 100%% rozdziały, albo wszystko z jawnymi lukami",
    )
    parser.add_argument(
        "--plec",
        choices=("oba", "bohater", "bohaterka"),
        default="oba",
        help="wariant płci w dialogach zależnych od płci gracza",
    )
    parser.add_argument("--z-otoczeniem", action="store_true", help="dołącz rozmowy poza zadaniami do epizodów i kontekstu")
    parser.add_argument("--tylko-watek-glowny", action="store_true", help="uwzględnij wyłącznie Prolog i Wątek Główny (+ powiązany kontekst)")
    parser.add_argument("--podglad-en", action="store_true", help="tryb podglądu formy z angielskim tekstem z index/ (bez tłumaczenia PL)")
    parser.add_argument("--podziel-powyzej", type=int, default=DOMYSLNY_LIMIT_BAJTOW, help="limit bajtów pliku przed podziałem na części (0 = nie dziel, domyślnie)")
    parser.add_argument("--wersja", default="v1", help="etykieta wersji w README (domyślnie: v1)")
    parser.add_argument("--wyj-katalog", default="dist/czytanki", help="katalog docelowy plików .md")
    parser.add_argument("--wyj-zip", default="", help="opcjonalny plik ZIP z gotowymi czytankami")
    parser.add_argument("--raport", help="opcjonalny raport JSON")
    args = parser.parse_args(argv)

    try:
        ix = indeks_mod.wczytaj(args.indeks)
        if args.podglad_en:
            if args.zwrotka or args.tylko_zwrotka:
                raise CzytankiError("--podglad-en nie łączy się z --zwrotka ani --tylko-zwrotka")
            pl = ZrodloPodgladuEN(ix)
            zrodlo_opis = "podgląd angielski (index/)"
        else:
            magazyn, tylko_klucze, zrodlo_opis = _wczytaj_przeklady(
                ix,
                magazyn_dir=args.magazyn,
                zwrotki=args.zwrotka,
                tylko_zwrotka=args.tylko_zwrotka,
                pomin_bledne=args.pomin_bledne,
            )
            pl = ZrodloPL(ix, magazyn, tylko_klucze=tylko_klucze)
        builder = BudowniczyCzytanek(
            ix,
            pl,
            zakres=args.zakres,
            plec=args.plec,
            z_otoczeniem=args.z_otoczeniem,
            tylko_watek_glowny=args.tylko_watek_glowny,
            wersja=args.wersja,
        )
        pliki, epizody = builder.buduj_z_epizodami()
        raport = zapisz_czytanki(
            pliki,
            Path(args.wyj_katalog),
            epizody=epizody,
            wyj_zip=Path(args.wyj_zip) if args.wyj_zip else None,
            limit_bajtow=args.podziel_powyzej,
            zakres=args.zakres,
            plec=args.plec,
            wersja=args.wersja,
            zrodlo_przekladow=zrodlo_opis,
            podglad_en=args.podglad_en,
        )
    except (CzytankiError, import_zwrotki.ZwrotkaError, indeks_mod.IndeksError, magazyn_mod.MagazynError, OSError, ValueError) as error:
        print(json.dumps({"ok": False, "powod": str(error)}, ensure_ascii=False, indent=1))
        return 1

    if args.raport:
        Path(args.raport).parent.mkdir(parents=True, exist_ok=True)
        Path(args.raport).write_text(json.dumps(raport, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")

    print(json.dumps({"ok": True, **raport}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
