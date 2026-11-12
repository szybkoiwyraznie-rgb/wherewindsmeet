#!/usr/bin/env python3
"""Generator polskich czytanek `.md` i archiwum `WWM_CZYTANKI_PL.zip` dla Where Winds Meet.

Wzorowany na edycjach czytelniczych SRW Y / SRW OE, dopasowany do struktury WWM:
- wyłącznie polski tekst (zero cichego wstawiania angielskiego lub chińskiego źródła),
- chronologiczny scenariusz (Prolog/cutsceny, Akty Wątku Głównego z łańcuchami
  zadań, wyborami gracza, przerywnikami, wizytówkami i streszczeniami z gry,
  zadania poboczne wg kategorii z adnotacją o nieliniowości otwartego świata),
- kontekst zintegrowany przy rozdziałach z ochroną powtórzeń i spoilerów
  (postacie z encyklopedii przy pierwszym wystąpieniu, listy, poszlaki,
  wzmiankowane pojęcia/przedmioty/techniki),
- osobne księgi kompendialne: encyklopedia świata i księgi z gry, przedmioty
  i ekwipunek, sztuki walki i zdolności,
- tabele Markdown zawijane do 120 znaków bez `<br>`, przyjazne zarówno dla
  czytników Markdown, jak i zwykłych edytorów tekstu.

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
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
import sys
import textwrap
import zipfile

try:
    from tools import import_zwrotki
    from tools import indeks as indeks_mod
    from tools import kontekst_cutscen as kc
    from tools import tlumaczenie as magazyn_mod
    from tools import uklad_scen
    from tools import wypisz
except ImportError:  # uruchomienie jako skrypt
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from tools import import_zwrotki
    from tools import indeks as indeks_mod
    from tools import kontekst_cutscen as kc
    from tools import tlumaczenie as magazyn_mod
    from tools import uklad_scen
    from tools import wypisz

FORMAT = "wwm-czytanki-v1"
STALA_DATA_ZIP = (2026, 1, 1, 0, 0, 0)
DOMYSLNY_LIMIT_BAJTOW = 1_500_000
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
_RE_TAG_XML = re.compile(r"</?(?:LINK|IMAGE|COLOR|FONT|SIZE|STYLE|OUTLINE)(?:\s[^<>\n]*)?>", re.I)
_RE_KOLOR = re.compile(r"#(?:[0-9a-fA-F]{6}|[A-Z])")
_RE_WIELE_SPACJI = re.compile(r"[ \t]{2,}")
_RE_PUSTE_LINIE = re.compile(r"\n{3,}")
_RE_SLOWA = re.compile(r"\w+")

_GENERYCZNE_NAZWY_GRACZA_ZH = kc.GENERYCZNE_NAZWY_GRACZA_ZH
_GENERYCZNE_NAZWY_GRACZA_TXT = kc.GENERYCZNE_NAZWY_GRACZA_TXT
_MOWCY_CUTSCEN_EN_IGNORUJ = kc.MOWCY_CUTSCEN_EN_IGNORUJ
_MOWCY_CUTSCEN_ZH_NA_EN = kc.MOWCY_CUTSCEN_ZH_NA_EN
_MOWCY_CUTSCEN_ZH_DO_TLUMACZENIA = kc.MOWCY_CUTSCEN_ZH_DO_TLUMACZENIA
_MOWCY_ROLE_PL = kc.MOWCY_ROLE_PL
_VO_DOMENY = kc.VO_DOMENY
_KOTWICE_SCEN_TM = kc.KOTWICE_SCEN_TM

_norm_cut_zh = kc.norm_cut_zh
_wvpv_pid = kc.wvpv_pid


class CzytankiError(Exception):
    """Błąd przygotowania czytanek WWM."""


def oczysc_tekst(text: str, *, jedna_linia: bool = False) -> str:
    """Usuń tagi kolorów NetEase, tagi XML i surowe parametry linków z tekstu gry."""
    if not text:
        return ""
    cleaned = text.replace("\r\n", "\n").replace("\r", "\n").replace("\t", " ")
    # Odnośniki rich-text mogą być zagnieżdżone, więc rozwijamy w pętli.
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
    if not naglowki:
        return []
    cols = len(naglowki)
    if not wiersze:
        return []

    # Najpierw normalizacja i wstępne obliczenie rozsądnych szerokości kolumn (bez ponownego cięcia #rrggbb na gotowych etykietach).
    norm_headers = [_escapuj_komorke(h, jedna_linia=True) for h in naglowki]
    norm_rows: list[list[str]] = []
    for row in wiersze:
        padded = list(row[:cols]) + [""] * max(0, cols - len(row))
        norm_rows.append([_escapuj_komorke(str(cell)) for cell in padded])

    # Ile miejsca zostaje na treść kolumn poza separatorami `| ` + ` | ` + ` |`
    overhead = 3 * cols + 1
    budget = max(cols * 8, max_szerokosc - overhead)

    natural_widths = []
    for idx in range(cols):
        cell_max = max(
            [len(norm_headers[idx])]
            + [max((len(part) for part in row[idx].split("\n")), default=0) for row in norm_rows]
        )
        natural_widths.append(max(len(norm_headers[idx]), min(cell_max, budget)))

    # Proporcjonalne przycięcie kolumn, jeśli suma przekracza budżet.
    widths = list(natural_widths)
    total = sum(widths)
    if total > budget:
        # Najpierw zachowujemy pełną szerokość bez rozcinania pojedynczych długich wyrazów (np. nazw plików),
        # oraz krótkich kolumn do 42 znaków, o ile mieści się to w budżecie wiersza.
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
                    add = (rem * flex[i]) // flex_sum
                    widths[i] += add
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
            # Gdy tryb --tylko-zwrotka, dopuszczamy jeszcze główny klucz wariantu, jeśli był w zwrotce.
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


def _naturalny(value: str):
    head, _, tail = value.partition("#")
    if tail.isdigit():
        return (0, int(tail), value)
    if head.lstrip("-").isdigit():
        return (0, int(head), value)
    return (1, 0, value)


@dataclass
class ZbudowanyPlik:
    nazwa: str
    tytul: str
    opis: str
    linie: list[str]
    statystyka: dict


class BudowniczyCzytanek:
    """Składa komplet czytanek WWM z `index/` oraz polskiego magazynu tłumaczeń."""

    def __init__(
        self,
        ix: indeks_mod.Indeks,
        pl: ZrodloPL,
        *,
        zakres: str = "przetlumaczone",
        plec: str = "oba",
        z_otoczeniem: bool = False,
        wersja: str = "v1",
    ):
        if zakres not in ("przetlumaczone", "kompletne-rozdzialy", "wszystko"):
            raise CzytankiError(f"nieznany zakres: {zakres!r}")
        if plec not in ("bohater", "bohaterka", "oba"):
            raise CzytankiError(f"nieznana opcja --plec: {plec!r}")
        self.ix = ix
        self.pl = pl
        self.zakres = zakres
        self.plec = plec
        self.z_otoczeniem = z_otoczeniem
        self.wersja = wersja
        self.uklad = uklad_scen.uloz(ix)
        self._przygotuj_indeksy()

    def _przygotuj_indeksy(self) -> None:
        ix = self.ix
        # 1. Tabele kontekstowe w jednym przebiegu po ix.teksty.
        chciane = {
            "manual_items",
            "region_collect_jianwen_data",
            "book_config",
            "ever_know_clue_data",
            "tasks_envelop_data",
            "world_view_person_info",
            "world_view_region_info",
            "world_view_shili_data",
            "world_view_history_info",
            "school_sect_chuancheng_data",
            "xinhu_menpai_list",
            "equip_items",
            "stuff_items",
            "kongfu",
            "xinfa",
            "jianghu_skills",
            "qishu_combat_data",
            "entity_attr",
        }
        self.tabele: dict[str, dict[str, dict[str, str]]] = {name: {} for name in chciane}
        self.nazwa_po_tekscie: dict[str, str] = {}
        self.klucz_nazwy_po_en: dict[str, str] = {}
        wvpv_raw: dict[str, str] = {}
        for kl, text in ix.teksty.items():
            zr = ix.zrodlo(text)
            if text.zrodlo:
                if text.zrodlo not in self.nazwa_po_tekscie and zr and any(part in zr[1] for part in ("name", "title", "nazwa")):
                    self.nazwa_po_tekscie[text.zrodlo] = kl
                en_val = (ix.en(kl) or "").strip()
                if en_val and len(en_val) <= 64 and zr and (
                    zr[0] in ("entity_billboard", "world_view_person_info", "cutscene_person_info_config", "avatars")
                    or any(part in zr[1] for part in ("name", "title", "nazwa"))
                ):
                    # Preferujemy nazwy z entity_billboard / encyklopedii / cutscen nad przypadkowymi opisami
                    if en_val not in self.klucz_nazwy_po_en or zr[0] in ("entity_billboard", "world_view_person_info", "cutscene_person_info_config"):
                        self.klucz_nazwy_po_en[en_val] = kl
            if not zr:
                continue
            tbl, col, row_id = zr
            if tbl in chciane:
                self.tabele[tbl].setdefault(row_id, {})[col] = kl
            elif tbl == "world_view_person_voice" and col == "description" and text.zrodlo:
                wvpv_raw[row_id] = text.zrodlo

        # 2. Encyklopedia postaci indeksowana po kluczu nazwy, id wpisu oraz angielskim imieniu.
        self.encyklopedia_po_kluczu: dict[str, dict] = {}
        self.encyklopedia_po_id: dict[int, dict] = dict(ix.encyklopedia)
        self.encyklopedia_po_en: dict[str, dict] = {}
        for row in ix.encyklopedia.values():
            for field in ("nazwa", "inna_nazwa"):
                if row.get(field):
                    self.encyklopedia_po_kluczu.setdefault(row[field], row)
            if row.get("nazwa"):
                en_name = (ix.en(row["nazwa"]) or "").strip()
                if en_name:
                    self.encyklopedia_po_en.setdefault(en_name, row)

        # 3. Wybory po dialogu oraz przypisania powtórek/przerywników do zadań i grup.
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

        # Przypisania przerywników użytych już przy zadaniach (uzupełniane też w trakcie budowania ksiąg zadań).
        self.przerywniki_w_zadaniach: set[int] = set()
        for task in ix.zadania.values():
            for lst in (task.get("przerywniki") or {}).values():
                self.przerywniki_w_zadaniu_add(lst)

        # 4. Słownik jednoznacznych mówców dla cutscen `text_msg` (głosy encyklopedii + dokładne powtórzenia).
        self._przygotuj_mowcow_napisow(wvpv_raw)
        self._kandydaci_wzmianek: list[tuple[str, str, str, tuple[str, ...]]] | None = None

    def _przygotuj_mowcow_napisow(self, wvpv_raw: dict[str, str]) -> None:
        (
            self.glos_wvpv_dokladny,
            self.mowca_napisow_exact,
            self.mowca_napisow_dlugie,
        ) = kc.zbuduj_indeksy_mowcow(self.ix, wvpv_raw, self.encyklopedia_po_id)

    @staticmethod
    def _bezposredni_mowca_en(row: dict, zh: str, en_txt: str, *, ignoruj_audio: bool = False) -> str | None:
        return kc.bezposredni_mowca_en(row, zh, en_txt, ignoruj_audio=ignoruj_audio)

    def przerywniki_w_zadaniu_add(self, lst) -> None:
        self.przerywniki_w_zadaniach.update(lst)

    # -------------------------------------------------------- pomocniki PL-only

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
        for field in ("numer_tytulu", "tytul", "nazwa"):
            val = self.pl.tekst(row.get(field), jedna_linia=True)
            if val:
                parts.append(val)
        if parts:
            return " — ".join(parts)
        return f"Rozdział #{grupa} [brak polskiego tytułu]"

    def _nazwa_zadania(self, tid: int) -> str:
        row = self.ix.zadania.get(tid) or {}
        val = self.pl.tekst(row.get("nazwa"), jedna_linia=True)
        return val or f"Zadanie #{tid} [brak polskiego tytułu]"

    def _miejsce(self, numer: int) -> str | None:
        row = self.ix.miejsca.get(numer)
        if not row:
            return f"Obszar #{numer}"
        val = self.pl.tekst(row.get("nazwa"), jedna_linia=True)
        return val or (f"Obszar #{numer}" if self.zakres == "wszystko" else None)

    def _mowca(self, scena: dict, numer: int, podmiana: str | None = None) -> str:
        if numer < 0 or numer >= len(scena.get("o", ())):
            return "Nieznany mówca"
        person = scena["o"][numer]
        name_key = podmiana or (person[3] if len(person) > 3 else None)
        if len(person) > 1 and person[1] == 1:
            if name_key:
                pl_name = self.pl.tekst(name_key, jedna_linia=True)
                zh_raw = (self.ix.teksty[name_key].zrodlo or "").strip() if name_key in self.ix.teksty else ""
                if (
                    pl_name
                    and zh_raw not in _GENERYCZNE_NAZWY_GRACZA_ZH
                    and pl_name.strip().lower() not in _GENERYCZNE_NAZWY_GRACZA_TXT
                ):
                    return f"You Xia ({pl_name})"
            return "You Xia"
        tag = person[0] if person else ""
        if name_key:
            pl_name = self.pl.tekst(name_key, jedna_linia=True)
            if pl_name:
                return pl_name
            return f"Postać #{name_key[:6]}" if self.zakres == "wszystko" else "Nieznany mówca"
        if tag in ("玩家", "主角"):
            return "You Xia"
        if tag and tag in self.nazwa_po_tekscie:
            pl_name = self.pl.tekst(self.nazwa_po_tekscie[tag], jedna_linia=True)
            if pl_name:
                return pl_name
        return "Rozmówca"

    def _tlumacz_mowce_cutsceny(self, en_name: str) -> str | None:
        """Przetłumacz nazwę mówcy z cutsceny zgodnie z aktualnym źródłem (PL albo `--podglad-en`)."""
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
        # Sprawdź po chińskim odpowiedniku ze słowników
        for zh_tag, mapped_en in (*_MOWCY_CUTSCEN_ZH_NA_EN.items(), *_MOWCY_CUTSCEN_ZH_DO_TLUMACZENIA.items()):
            if mapped_en == en_name and zh_tag in self.nazwa_po_tekscie:
                pl_val = self.pl.tekst(self.nazwa_po_tekscie[zh_tag], jedna_linia=True)
                if pl_val:
                    return pl_val
        return None

    def _rozwiaz_mowce_napisu(self, row: dict, txt: str, *, ignoruj_audio: bool = False) -> tuple[str | None, str, bool]:
        """Ustal mówcę napisu `text_msg` i usuń zduplikowany prefiks `Mówca: ` z treści."""
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
        if not mowca_out and detected_sp:
            if detected_sp == "You Xia":
                mowca_out = "You Xia"
            else:
                mowca_out = self._tlumacz_mowce_cutsceny(detected_sp) or (
                    detected_sp if getattr(self.pl, "jest_podgladem_en", False) else None
                )

        return mowca_out, cleaned_txt, czy_gracz

    def _pasuje_plec_elementu(self, element: list) -> tuple[bool, str]:
        """Czy element dialogu pasuje do `--plec`; zwraca (czy_pokazac, prefiks_plci)."""
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
        """Zwróć (przetłumaczone_niepuste, wszystkich_niepustych) bez powtórek slotu."""
        unikatowe: list[str] = []
        seen = set()
        for slot in sloty:
            if slot in seen:
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

    # -------------------------------------------------------- renderowanie sceny

    def _renderuj_scene(self, numer_sceny: int, miejsce, *, poziom_naglowka: int = 4) -> tuple[list[str], int, int, set[int]]:
        """Renderuje pojedynczą scenę. Zwraca (linie, przetłumaczonych, wszystkich, zbiór_id_postaci)."""
        scena = self.ix.sceny[numer_sceny]
        slots: list[str] = []
        active_elements: list[tuple[list, str, str]] = []
        for el in scena["e"]:
            ok, prefix = self._pasuje_plec_elementu(el)
            if not ok:
                continue
            slot = self._slot_sceny(el)
            slots.append(slot)
            active_elements.append((el, slot, prefix))

        wybory = self.wybory_po.get(numer_sceny, ())
        for row in wybory:
            for ch in row.get("wybory", ()):
                if ch.get("tekst"):
                    slots.append(ch["tekst"])

        done, total = self._stat_slotow(slots)
        if not self._ma_dopuszczalne_pokrycie(done, total):
            return [], done, total, set()

        postacie_w_scenie: set[int] = set()
        for person in scena.get("o", ()):
            if len(person) > 3 and person[3] in self.encyklopedia_po_kluczu:
                postacie_w_scenie.add(self.encyklopedia_po_kluczu[person[3]]["id"])

        lines: list[str] = []
        nagl = f"{'#' * poziom_naglowka} Scena — dialog {numer_sceny}"
        miejsca_txt = [self._miejsce(m) for m in (scena.get("m") or [])[:3]]
        miejsca_txt = [m for m in miejsca_txt if m]
        if miejsce.moment == "numeracja":
            nagl += " *(kolejność przybliżona)*"
        lines.append(nagl)
        if miejsca_txt:
            lines.append(f"*Miejsce: {', '.join(miejsca_txt)}*")
        if done < total and self.zakres != "wszystko":
            lines.append(f"*Uwaga: przetłumaczono {done} z {total} wypowiedzi w tej scenie.*")
        lines.append("")

        surowe_wpisy: list[tuple[str, int, str, str, str, str]] = []
        for el, slot, prefix in active_elements:
            kind = el[0]
            txt = self._tekst(slot, fallback_label="kwestii")
            if txt is None:
                continue
            wariant = el[3] if len(el) > 3 and el[3] else 0
            bazowy = el[2]
            mowca = self._mowca(scena, el[1], el[5] if len(el) > 5 else None) if kind == "k" else ""
            surowe_wpisy.append((kind, wariant, bazowy, mowca, txt, prefix))

        blok_wiersze: list[str] = []
        idx = 0
        while idx < len(surowe_wpisy):
            kind, wariant, bazowy, mowca, txt, prefix = surowe_wpisy[idx]
            if (
                self.plec == "oba"
                and idx + 1 < len(surowe_wpisy)
                and {wariant, surowe_wpisy[idx + 1][1]} == {1, 2}
                and surowe_wpisy[idx + 1][0] == kind
                and surowe_wpisy[idx + 1][2] == bazowy
                and surowe_wpisy[idx + 1][3] == mowca
                and surowe_wpisy[idx + 1][4] == txt
            ):
                prefix = ""
                idx += 2
            else:
                idx += 1

            if kind == "k":
                akapit = txt.replace("\n", " ")
                blok_wiersze.append(f"**{prefix}{mowca}:** {akapit}")
            elif kind in ("p", "o", "i"):
                akapit = txt.replace("\n", " ")
                blok_wiersze.append(f"*{prefix}{akapit}*")
            elif kind == "wi":
                blok_wiersze.append(f"> **Wizytówka — {txt}**")
            elif kind == "wt":
                blok_wiersze.append(f"> *{txt}*")
            else:
                blok_wiersze.append(f"> {prefix}{txt.replace(chr(10), ' ')}")

        if blok_wiersze:
            lines.extend(blok_wiersze)

        for row in wybory:
            tytul_w = self._tekst(row.get("tytul"), fallback_label="pytania", jedna_linia=True)
            opcje: list[str] = []
            for ch in row.get("wybory", ()):
                t_opcji = self._tekst(ch.get("tekst"), fallback_label="opcji wyboru", jedna_linia=True)
                if t_opcji is None:
                    continue
                cele = [str(d) for d in ch.get("dialogi", ())]
                cel_txt = f" *(→ dialog {', '.join(cele)})*" if cele else ""
                opcje.append(f"- **Wybór {ch['nr']}:** {t_opcji}{cel_txt}")
            if opcje:
                lines.append("")
                if tytul_w:
                    lines.append(f"**Wybór gracza — {tytul_w}:**")
                else:
                    lines.append("**Wybór gracza:**")
                lines.extend(opcje)

        lines.append("")
        return lines, done, total, postacie_w_scenie

    # -------------------------------------------------------- kontekst w rozdziale

    def _kontekst_rozdzialu(
        self,
        postacie_ids: set[int],
        rozdzial_tytul: str,
        widziane_postacie: dict[int, str],
        teksty_rozdzialu: str,
        wzmiankowane_przedmioty: set[str],
    ) -> list[str]:
        """Zbuduj sekcję kontekstową z ochroną przed duplikacją i spoilerami."""
        lines: list[str] = []
        nowe_postacie: list[str] = []
        powrotne_postacie: list[str] = []

        for pid in sorted(postacie_ids):
            entry = self.encyklopedia_po_id.get(pid)
            if not entry:
                continue
            pl_name = self.pl.tekst(entry.get("nazwa"), jedna_linia=True)
            if not pl_name:
                if self.zakres == "wszystko" and entry.get("nazwa"):
                    pl_name = f"[Brak polskiej nazwy postaci: {entry['nazwa']}]"
                else:
                    continue
            if pid in widziane_postacie:
                powrotne_postacie.append(f"{pl_name} *(pierwsze wystąpienie: {widziane_postacie[pid]})*")
                continue
            tozsamosc = [
                t for t in (self.pl.tekst(k, jedna_linia=True) for k in entry.get("tozsamosc", ())) if t
            ]
            # Ostrożnie przed spoilerami: do rozdziału włączamy wyłącznie 1. podstawowy wpis biograficzny,
            # pełna reszta odblokowywanych wspomnień znajduje się w księdze 03_encyklopedia_swiata.md.
            pierwsza_historia = None
            for item in entry.get("historie", ())[:1]:
                if isinstance(item, (list, tuple)):
                    czesci = [self.pl.tekst(k, jedna_linia=True) for k in item if k]
                    czesci = [c for c in czesci if c]
                    if czesci:
                        pierwsza_historia = " — ".join(czesci)
                        break
                elif isinstance(item, str):
                    pierwsza_historia = self.pl.tekst(item, jedna_linia=True)
                    if pierwsza_historia:
                        break
            if tozsamosc or pierwsza_historia:
                widziane_postacie[pid] = rozdzial_tytul
                opis = f"- **{pl_name}**"
                if tozsamosc:
                    opis += f" — {'; '.join(tozsamosc)}"
                if pierwsza_historia:
                    opis += f"\n  - *Pierwszy wpis z księgi postaci:* {pierwsza_historia}"
                    if len(entry.get("historie", ())) > 1:
                        opis += " *(dalsze wpisy biograficzne w `03_encyklopedia_swiata.md`)*"
                nowe_postacie.append(opis)

        if nowe_postacie or powrotne_postacie:
            lines.append("#### Postacie napotkane w tym rozdziale (encyklopedia gry)")
            lines.extend(nowe_postacie)
            if powrotne_postacie:
                lines.append(f"- *Ponowne wystąpienia znanych postaci:* {', '.join(powrotne_postacie)}")
            lines.append("")

        # Wzmiankowane w tekście rozdziału przedmioty lub techniki (dopasowanie z zachowaniem wielkości liter,
        # bez jednosłownych nazw pospolitych z tabeli stuff_items, z jednorazowym cache dla szybkości).
        if self._kandydaci_wzmianek is None:
            kandydaci: list[tuple[str, str, str, tuple[str, ...]]] = []
            for tbl_name, kategoria in (
                ("equip_items", "Wyposażenie"),
                ("stuff_items", "Przedmiot"),
                ("kongfu", "Styl walki"),
                ("xinfa", "Sztuka wewnętrzna"),
                ("jianghu_skills", "Umiejętność Jianghu"),
            ):
                for _rid, cols in sorted(self.tabele.get(tbl_name, {}).items(), key=lambda x: _naturalny(x[0])):
                    n_kl = cols.get("name") or cols.get("jianghu_skill_name")
                    if not n_kl:
                        continue
                    pl_n = self.pl.tekst(n_kl, jedna_linia=True)
                    if not pl_n or len(pl_n) < 5:
                        continue
                    toks = tuple(_RE_SLOWA.findall(pl_n))
                    if not toks:
                        continue
                    if tbl_name == "stuff_items" and len(toks) < 2:
                        continue
                    d_kl = cols.get("brief_describe_str") or cols.get("describe_str") or cols.get("description") or cols.get("jianghu_brief_description")
                    pl_d = self.pl.tekst(d_kl, jedna_linia=True) if d_kl else None
                    if not pl_d:
                        continue
                    kandydaci.append((pl_n, kategoria, pl_d, toks))
            self._kandydaci_wzmianek = kandydaci

        znalezione_rzeczy: list[tuple[str, str, str]] = []
        word_set = set(_RE_SLOWA.findall(teksty_rozdzialu))
        for pl_n, kategoria, pl_d, toks in self._kandydaci_wzmianek:
            if pl_n in wzmiankowane_przedmioty:
                continue
            if not all(tok in word_set for tok in toks):
                continue
            if re.search(rf"(?<!\w){re.escape(pl_n)}(?!\w)", teksty_rozdzialu):
                znalezione_rzeczy.append((pl_n, kategoria, pl_d))
                wzmiankowane_przedmioty.add(pl_n)
                if len(znalezione_rzeczy) >= 8:
                    break

        if znalezione_rzeczy:
            lines.append("#### Wzmiankowane przedmioty i techniki")
            lines.extend(formatuj_tabele(["Nazwa", "Rodzaj", "Opis z gry"], znalezione_rzeczy))
            lines.append("")

        return lines

    # -------------------------------------------------------- budowa ksiąg

    def _dopasuj_domene_vo(self, aud: str) -> tuple[str, str, int | None, tuple[int, ...]] | None:
        return kc.dopasuj_domene_vo(aud)

    def _tytul_powtorki(self, cut_no: int) -> str | None:
        prow = self.powtorka_po_no.get(cut_no)
        if not prow:
            return None
        pn = self.pl.tekst(prow.get("nazwa"), jedna_linia=True)
        pr = self.pl.tekst(prow.get("rozdzial"), jedna_linia=True)
        psp_id = prow.get("przestrzen")
        psp = None
        if psp_id not in (None, 501, 502, 504):
            psp = self._miejsce(psp_id)
        czesci = [c for c in (pn, pr, psp) if c]
        return " — ".join(czesci) if czesci else None

    def _segmentuj_ciag_napisow(self, ciag: list[dict]) -> list[dict]:
        """Podziel ciągły blok `text_msg` na logiczne pod-sceny z metadanymi kontekstowymi."""
        return kc.segmentuj_ciag_napisow(ciag)

    def _buduj_prolog_i_przerywniki(self) -> ZbudowanyPlik:
        ix = self.ix
        lines: list[str] = [
            "# Prolog i przerywniki filmowe — Where Winds Meet",
            "",
            "Zbiór sekwencji wprowadzających, Prologu, napisów przerywników (`text_msg`) oraz plansz",
            "nieprzypisanych bezpośrednio do pojedynczego zadania.",
            "",
        ]
        done_total = 0
        all_total = 0

        # 1. Intro (`wds_oneday_intro_cutscene_data`)
        intro = sorted((r for r in ix.cutsceny_kontekst.get("intro", ()) if r.get("k") in ix.teksty), key=lambda r: r["id"])
        intro_slots = [r["k"] for r in intro]
        d_i, t_i = self._stat_slotow(intro_slots)
        done_total += d_i
        all_total += t_i
        if self._ma_dopuszczalne_pokrycie(d_i, t_i):
            lines.append(f"## Intro otwierające ({d_i}/{t_i} linii)")
            lines.append("*Sekwencja wprowadzająca — „One Day in the Imperial Service” (`wds_oneday_intro_cutscene_data`).*")
            lines.append("")
            for r in intro:
                txt = self._tekst(r["k"], fallback_label="napisu intro", jedna_linia=True)
                if txt:
                    if r["mowca"] == 1:
                        mowca_lbl = "You Xia"
                    elif r["mowca"] == 2:
                        mowca_lbl = "Mówca 2 (Gwardia Cesarska)"
                    else:
                        mowca_lbl = f"Mówca {r['mowca']}"
                    lines.append(f"- `{r['czas']:.1f}s` **{mowca_lbl}:** {txt}")
            lines.append("")

        # 2. Ciągi cutscen `text_msg` (w tym pasmo 590291–590459 jako wyróżniona pierwsza sekcja)
        napisy = sorted((r for r in ix.cutsceny_kontekst.get("napis", ()) if r.get("k") in ix.teksty), key=lambda r: r["wiersz"])
        ciagi: list[list[dict]] = []
        for row in napisy:
            if not ciagi or row["wiersz"] - ciagi[-1][-1]["wiersz"] > 1:
                ciagi.append([row])
            else:
                ciagi[-1].append(row)

        # Wykrywanie par męski/żeński w ciągach
        plec_wiersza = kc.wykryj_plec_napisow(napisy, ix.teksty)

        prolog_ciagi = [c for c in ciagi if not (c[-1]["wiersz"] < ZAKRES_PROLOG_TM[0] or c[0]["wiersz"] > ZAKRES_PROLOG_TM[1])]
        inne_ciagi = [c for c in ciagi if c not in prolog_ciagi]

        def renderuj_podscene(seg: dict, tytul_nagl: str, poziom_nagl: int) -> tuple[list[str], int, int]:
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
                return [], d_s, t_s

            out_lines: list[str] = [f"{'#' * poziom_nagl} {tytul_nagl} ({d_s}/{t_s} napisów)"]

            # Kontekst z bazy gry (wyłącznie w aktualnym języku przekładu / podglądu)
            if seg["grupa"] is not None:
                row_g = self.ix.grupy.get(seg["grupa"]) or {}
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

            # Render linii + zliczanie rozpoznanych mówców i nieoznaczonych wierszy
            rendered_dialog: list[str] = []
            rozpoznani_mowcy: list[str] = []
            widziani_mowcy: set[str] = set()
            brak_mowcy = 0
            last_vo = ""
            wygl_wiersze = seg.get("wygladzono_audio") or set()
            i = 0
            while i < len(filtrowane):
                row, p, pref = filtrowane[i]
                txt = self._tekst(row["k"], fallback_label="napisu", jedna_linia=True)
                if not txt:
                    i += 1
                    continue

                ignoruj_a1 = row["wiersz"] in wygl_wiersze
                mowca1, clean_txt1, czy_gracz1 = self._rozwiaz_mowce_napisu(row, txt, ignoruj_audio=ignoruj_a1)
                merged_pair = False
                if self.plec == "oba" and p and i + 1 < len(filtrowane):
                    row2, p2, _ = filtrowane[i + 1]
                    if {p, p2} == {"bohater", "bohaterka"}:
                        txt2 = self._tekst(row2["k"], fallback_label="napisu", jedna_linia=True)
                        if txt2 is not None:
                            mowca2, clean_txt2, _ = self._rozwiaz_mowce_napisu(
                                row2,
                                txt2,
                                ignoruj_audio=row2["wiersz"] in wygl_wiersze,
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
                    "(część napisów tej sekwencji zapisano w tabeli `text_msg` bez etykiety mówcy).*"
                )
            elif not rozpoznani_mowcy and brak_mowcy >= 4:
                out_lines.append("*Uwaga: w źródłowej tabeli `text_msg` tej sekwencji brak przypisanych etykiet mówcy przy napisach.*")

            out_lines.append("")
            out_lines.extend(rendered_dialog)
            out_lines.append("")
            return out_lines, d_s, t_s

        def dodaj_ciag(tytul_h2: str, ciag: list[dict], *, zawsze_podsceny: bool = False) -> None:
            nonlocal done_total, all_total
            segmenty = self._segmentuj_ciag_napisow(ciag)
            if len(segmenty) == 1 and not zawsze_podsceny:
                seg = segmenty[0]
                t_nagl = seg["tytul"] or tytul_h2
                if seg["tytul"]:
                    t_nagl = f"{seg['tytul']} (napisy {ciag[0]['wiersz']}–{ciag[-1]['wiersz']})"
                s_lines, d_c, t_c = renderuj_podscene(seg, t_nagl, poziom_nagl=2)
                done_total += d_c
                all_total += t_c
                lines.extend(s_lines)
                return

            # Sekcja nadrzędna `##` z pod-scenami `###`
            sub_chunks: list[list[str]] = []
            d_sum = 0
            t_sum = 0
            for sub_idx, seg in enumerate(segmenty, 1):
                w0, w1 = seg["rows"][0]["wiersz"], seg["rows"][-1]["wiersz"]
                podtytul = seg["tytul"] or f"Sekwencja {sub_idx}"
                t_nagl = f"{podtytul} (napisy {w0}–{w1})"
                s_lines, d_s, t_s = renderuj_podscene(seg, t_nagl, poziom_nagl=3)
                d_sum += d_s
                t_sum += t_s
                if s_lines:
                    sub_chunks.append(s_lines)

            done_total += d_sum
            all_total += t_sum
            if not sub_chunks:
                return
            lines.append(f"## {tytul_h2} ({d_sum}/{t_sum} napisów)")
            lines.append("")
            for chunk in sub_chunks:
                lines.extend(chunk)

        for idx, c in enumerate(prolog_ciagi, 1):
            if len(c) >= 10:
                dodaj_ciag(
                    f"Prolog i kluczowe sceny Rozdziału I — sekwencja {idx} (napisy {c[0]['wiersz']}–{c[-1]['wiersz']})"
                    if len(prolog_ciagi) > 1
                    else f"Prolog i kluczowe sceny Rozdziału I (napisy {c[0]['wiersz']}–{c[-1]['wiersz']})",
                    c,
                    zawsze_podsceny=True,
                )
            else:
                dodaj_ciag(f"Prolog — sekwencja {idx} (napisy {c[0]['wiersz']}–{c[-1]['wiersz']})", c)

        nr_sekwencji = 0
        for c in inne_ciagi:
            w0, w1 = c[0]["wiersz"], c[-1]["wiersz"]
            seg_probe = self._segmentuj_ciag_napisow(c)
            if len(seg_probe) == 1:
                dodaj_ciag(f"Sekwencja cutscen (napisy {w0}–{w1})", c)
            else:
                nr_sekwencji += 1
                if w0 >= 591487 and len(c) >= 20:
                    nagl_c = f"Sekwencje cutscen — część {nr_sekwencji} (warianty napisów i nowe akty, {w0}–{w1})"
                else:
                    nagl_c = f"Sekwencje cutscen — część {nr_sekwencji} (napisy {w0}–{w1})"
                dodaj_ciag(nagl_c, c)

        # 3. Filmy (`entry_collect_movie_subtitle_data`)
        by_film: dict[int, list[dict]] = defaultdict(list)
        for r in ix.cutsceny_kontekst.get("film", ()):
            if r.get("k") in ix.teksty:
                by_film[r["film"]].append(r)
        for film_id, rows in sorted(by_film.items()):
            rows.sort(key=lambda r: (r["czas"], r["id"]))
            d_f, t_f = self._stat_slotow([r["k"] for r in rows])
            done_total += d_f
            all_total += t_f
            if not self._ma_dopuszczalne_pokrycie(d_f, t_f):
                continue
            lines.append(f"## Film #{film_id} ({d_f}/{t_f} napisów)")
            lines.append("")
            for r in rows:
                txt = self._tekst(r["k"], fallback_label="napisu filmowego", jedna_linia=True)
                if txt:
                    lines.append(f"- `{r['czas']:.1f}s` {txt}")
            lines.append("")

        # 4. Przerywniki nieprzypisane do żadnego zadania (z pominięciem duplikatów platformowych >= 10_000_000)
        luźne = []
        for no, row in sorted(ix.przerywniki.items()):
            if no in self.przerywniki_w_zadaniach:
                continue
            if no >= 10_000_000 and (no % 10_000_000) in ix.przerywniki:
                base_row = ix.przerywniki[no % 10_000_000]
                if (
                    self.pl.tekst(row.get("tekst")) == self.pl.tekst(base_row.get("tekst"))
                    and self.pl.tekst(row.get("streszczenie")) == self.pl.tekst(base_row.get("streszczenie"))
                ):
                    continue
            luźne.append((no, row))
        if luźne:
            bogate_lines: list[str] = []
            plansze_lines: list[str] = []
            for no, row in luźne:
                slots = [row[f] for f in ("tekst", "streszczenie") if row.get(f)]
                d_p, t_p = self._stat_slotow(slots)
                done_total += d_p
                all_total += t_p
                if not self._ma_dopuszczalne_pokrycie(d_p, t_p):
                    continue
                t_pl = self._tekst(row.get("tekst"), fallback_label="planszy przerywnika")
                s_pl = self._tekst(row.get("streszczenie"), fallback_label="streszczenia przerywnika")
                tyt_powt = self._tytul_powtorki(no)
                if s_pl or tyt_powt:
                    nagl_p = f"### Przerywnik #{no}" + (f" — {tyt_powt}" if tyt_powt else "")
                    bogate_lines.append(nagl_p)
                    if t_pl:
                        bogate_lines.append(t_pl)
                    if s_pl:
                        bogate_lines.append(f"*Streszczenie:* {s_pl}")
                    bogate_lines.append("")
                elif t_pl:
                    plansze_lines.append(f"- **#{no}:** {t_pl.replace(chr(10), ' ')}")

            if bogate_lines or plansze_lines:
                lines.append("## Pozostałe plansze i streszczenia przerywników")
                lines.append("")
                lines.extend(bogate_lines)
                if plansze_lines:
                    lines.append("### Pozostałe plansze przejściowe (czarny ekran)")
                    lines.append("")
                    lines.extend(plansze_lines)
                    lines.append("")

        return ZbudowanyPlik(
            nazwa="00_prolog_i_przerywniki.md",
            tytul="Prolog i przerywniki filmowe",
            opis="Napisy wprowadzające, Prolog, cutsceny fabularne oraz nieprzypisane plansze.",
            linie=lines,
            statystyka={"przetlumaczono": done_total, "wszystkich": all_total},
        )

    def _buduj_sekcje_zadan(
        self,
        *,
        nazwa_pliku: str,
        tytul: str,
        opis: str,
        wstep: list[str],
        tylko_watek_glowny: bool,
    ) -> ZbudowanyPlik:
        ix = self.ix
        lines: list[str] = [f"# {tytul}", "", *wstep, ""]
        done_total = 0
        all_total = 0
        sekcji_wypisanych = 0
        zadan_wypisanych = 0
        scen_wypisanych = 0

        widziane_postacie: dict[int, str] = {}
        wzmiankowane_przedmioty: set[str] = set()
        przerywniki_wypisane: set[int] = set()
        powtorki_wypisane: set[int] = set()

        current_type = object()

        for sekcja in self.uklad.sekcje:
            is_main = sekcja.typ == uklad_scen.TYP_WATKU_GLOWNEGO
            if is_main != tylko_watek_glowny:
                continue

            rozdzial_tytul = self._nazwa_grupy(sekcja.grupa)
            rozdzial_body: list[str] = []
            postacie_rozdzialu: set[int] = set()
            teksty_rozdzialu_buf: list[str] = []
            rozdzial_done = 0
            rozdzial_all = 0
            rozdzial_scen = 0
            rozdzial_zadan = 0

            # Streszczenia rozdziału z `plot_recap_data`
            for srow in self.streszczenia_grupy.get(sekcja.grupa, ()):
                s_pl = self._tekst(srow.get("tekst"), fallback_label="streszczenia fabuły")
                if s_pl:
                    rozdzial_body.append(f"> **Kronika rozdziału:** {s_pl}")
            if rozdzial_body:
                rozdzial_body.append("")

            last_meta: tuple[str, str | None, str | None] | None = None
            seen_metas: set[tuple[str, str | None, str | None]] = set()
            for tid in sekcja.zadania:
                trow = ix.zadania[tid]
                miejsca_sceny = self.uklad.sceny_zadania.get(tid, ())
                zad_sceny_lines: list[str] = []
                zad_done = 0
                zad_all = 0
                zad_scen = 0

                # Powiązane przerywniki przy przyjęciu
                for cut_no in (trow.get("przerywniki") or {}).get("przyjecie", ()):
                    if cut_no in przerywniki_wypisane:
                        continue
                    crow = ix.przerywniki.get(cut_no)
                    if not crow:
                        continue
                    c_slots = [crow[f] for f in ("tekst", "streszczenie") if crow.get(f)]
                    cd, ct = self._stat_slotow(c_slots)
                    zad_done += cd
                    zad_all += ct
                    if self._ma_dopuszczalne_pokrycie(cd, ct):
                        przerywniki_wypisane.add(cut_no)
                        powtorki_wypisane.add(cut_no)
                        self.przerywniki_w_zadaniach.add(cut_no)
                        tyt_p = self._tytul_powtorki(cut_no)
                        t_pl = self._tekst(crow.get("tekst"), fallback_label="planszy przerywnika")
                        s_pl = self._tekst(crow.get("streszczenie"), fallback_label="streszczenia")
                        zad_sceny_lines.append(
                            f"*[Przerywnik #{cut_no}"
                            + (f" — {tyt_p}" if tyt_p else "")
                            + " — rozpoczęcie zadania]*"
                        )
                        if t_pl:
                            zad_sceny_lines.append(t_pl)
                            teksty_rozdzialu_buf.append(t_pl)
                        if s_pl:
                            zad_sceny_lines.append(f"*Streszczenie:* {s_pl}")
                            teksty_rozdzialu_buf.append(s_pl)
                        zad_sceny_lines.append("")

                for m in miejsca_sceny:
                    s_lines, sd, st, s_chars = self._renderuj_scene(
                        m.dialog,
                        m,
                        poziom_naglowka=4 if tylko_watek_glowny else 5,
                    )
                    zad_done += sd
                    zad_all += st
                    postacie_rozdzialu.update(s_chars)
                    if s_lines:
                        zad_scen += 1
                        zad_sceny_lines.extend(s_lines)
                        teksty_rozdzialu_buf.extend(s_lines)

                # Przerywniki po zakończeniu zadania
                for cut_no in (trow.get("przerywniki") or {}).get("zakonczenie", ()):
                    if cut_no in przerywniki_wypisane:
                        continue
                    crow = ix.przerywniki.get(cut_no)
                    if not crow:
                        continue
                    c_slots = [crow[f] for f in ("tekst", "streszczenie") if crow.get(f)]
                    cd, ct = self._stat_slotow(c_slots)
                    zad_done += cd
                    zad_all += ct
                    if self._ma_dopuszczalne_pokrycie(cd, ct):
                        przerywniki_wypisane.add(cut_no)
                        powtorki_wypisane.add(cut_no)
                        self.przerywniki_w_zadaniach.add(cut_no)
                        tyt_p = self._tytul_powtorki(cut_no)
                        t_pl = self._tekst(crow.get("tekst"), fallback_label="planszy przerywnika")
                        s_pl = self._tekst(crow.get("streszczenie"), fallback_label="streszczenia")
                        zad_sceny_lines.append(
                            f"*[Przerywnik #{cut_no}"
                            + (f" — {tyt_p}" if tyt_p else "")
                            + " — zakończenie zadania]*"
                        )
                        if t_pl:
                            zad_sceny_lines.append(t_pl)
                            teksty_rozdzialu_buf.append(t_pl)
                        if s_pl:
                            zad_sceny_lines.append(f"*Streszczenie:* {s_pl}")
                            teksty_rozdzialu_buf.append(s_pl)
                        zad_sceny_lines.append("")

                # Powtórki cutscen powiązane z zadaniem (`task_cutscene_replay`) nieujęte wyżej w `przerywniki`
                for prow in self.powtorki_po_zadaniu.get(tid, ()):
                    pno = prow.get("no")
                    if pno in powtorki_wypisane or pno in przerywniki_wypisane:
                        continue
                    tyt_p = self._tytul_powtorki(pno)
                    crow = ix.przerywniki.get(pno) or {}
                    t_slot = crow.get("tekst")
                    s_slot = crow.get("streszczenie") or prow.get("streszczenie")
                    c_slots = [s for s in (t_slot, s_slot) if s]
                    cd, ct = self._stat_slotow(c_slots) if c_slots else (0, 0)
                    ma_crow = bool(c_slots) and self._ma_dopuszczalne_pokrycie(cd, ct)
                    if tyt_p or ma_crow:
                        powtorki_wypisane.add(pno)
                        przerywniki_wypisane.add(pno)
                        self.przerywniki_w_zadaniach.add(pno)
                        if ma_crow:
                            zad_done += cd
                            zad_all += ct
                        zad_sceny_lines.append(
                            f"> **Przerywnik fabularny w dzienniku (#{pno}):** {tyt_p or ''}"
                        )
                        if ma_crow:
                            t_pl = self._tekst(t_slot, fallback_label="planszy przerywnika")
                            s_pl = self._tekst(s_slot, fallback_label="streszczenia")
                            if t_pl:
                                zad_sceny_lines.append(t_pl)
                                teksty_rozdzialu_buf.append(t_pl)
                            if s_pl:
                                zad_sceny_lines.append(f"*Streszczenie:* {s_pl}")
                                teksty_rozdzialu_buf.append(s_pl)
                        zad_sceny_lines.append("")

                # Metadane zadania (nazwa, cel, opis w dzienniku)
                nazwa_z = self.pl.tekst(trow.get("nazwa"), jedna_linia=True)
                cel_z = self.pl.tekst(trow.get("cel"), jedna_linia=True)
                opis_z = self.pl.tekst(trow.get("opis"))
                meta_slots = [s for s in (trow.get("nazwa"), trow.get("cel"), trow.get("opis")) if s]
                md, mt = self._stat_slotow(meta_slots)
                zad_done += md
                zad_all += mt

                ma_tresc = bool(zad_sceny_lines) or self._ma_dopuszczalne_pokrycie(zad_done, zad_all)
                if not ma_tresc:
                    continue
                if self.zakres == "kompletne-rozdzialy" and zad_done < zad_all:
                    rozdzial_all += zad_all
                    rozdzial_done += zad_done
                    continue

                tyt = nazwa_z or (f"Zadanie #{tid} [brak polskiego tytułu]" if self.zakres == "wszystko" else f"Zadanie #{tid}")
                cur_meta = (tyt, cel_z, opis_z)

                # W WWM ten sam rozdział miewa wiele kolejnych kroków technicznych o identycznej nazwie i opisie.
                # Scalamy je czytelnie w jeden nurt, zamiast powtarzać identyczny nagłówek i opis co zadanie.
                if (last_meta == cur_meta or cur_meta in seen_metas) and not zad_sceny_lines:
                    continue
                if last_meta == cur_meta:
                    rozdzial_done += zad_done
                    rozdzial_all += zad_all
                    rozdzial_scen += zad_scen
                    rozdzial_zadan += 1
                    rozdzial_body.extend(zad_sceny_lines)
                    continue
                seen_metas.add(cur_meta)

                rozdzial_done += zad_done
                rozdzial_all += zad_all
                rozdzial_scen += zad_scen
                rozdzial_zadan += 1

                if last_meta and last_meta[0] == tyt and nazwa_z is not None:
                    nowe_etapy = False
                    if (
                        len(rozdzial_body) >= 2
                        and rozdzial_body[-1] == ""
                        and rozdzial_body[-2].startswith(("- **Kolejny etap / cel:**", "- **Dalszy opis:**"))
                    ):
                        rozdzial_body.pop()
                    if cel_z and cel_z != last_meta[1]:
                        rozdzial_body.append(f"- **Kolejny etap / cel:** {cel_z}")
                        nowe_etapy = True
                    if opis_z and opis_z != last_meta[2]:
                        rozdzial_body.append(f"- **Dalszy opis:** {opis_z}")
                        nowe_etapy = True
                    if zad_sceny_lines:
                        if rozdzial_body and rozdzial_body[-1] != "":
                            rozdzial_body.append("")
                        rozdzial_body.extend(zad_sceny_lines)
                    elif nowe_etapy:
                        rozdzial_body.append("")
                else:
                    nagl_zad = "### " if tylko_watek_glowny else "#### "
                    rozdzial_body.append(f"{nagl_zad}{tyt}")
                    miejsce_z = self._miejsce(trow["przestrzen"]) if trow.get("przestrzen") is not None else None
                    if miejsce_z:
                        rozdzial_body.append(f"- **Miejsce:** {miejsce_z}")
                    if cel_z:
                        rozdzial_body.append(f"- **Cel w dzienniku:** {cel_z}")
                    if opis_z:
                        rozdzial_body.append(f"- **Opis zadania:** {opis_z}")
                    rozdzial_body.append("")
                    rozdzial_body.extend(zad_sceny_lines)
                last_meta = cur_meta
                teksty_rozdzialu_buf.extend(part for part in (tyt, cel_z, opis_z) if part)

            done_total += rozdzial_done
            all_total += rozdzial_all
            if rozdzial_zadan == 0:
                continue
            if self.zakres == "kompletne-rozdzialy" and rozdzial_done < rozdzial_all:
                continue

            sekcji_wypisanych += 1
            zadan_wypisanych += rozdzial_zadan
            scen_wypisanych += rozdzial_scen

            if not tylko_watek_glowny and sekcja.typ != current_type:
                current_type = sekcja.typ
                lines.append(f"## Kategoria: {self._nazwa_typu(sekcja.typ)}")
                lines.append("")

            nagl_rozdz = "## " if tylko_watek_glowny else "### "
            lines.append(f"{nagl_rozdz}{rozdzial_tytul}")
            lines.append(f"*Zadań w sekcji: {rozdzial_zadan} · scen dialogowych: {rozdzial_scen} · przetłumaczenie: {rozdzial_done}/{rozdzial_all}*")
            lines.append("")
            lines.extend(rozdzial_body)

            kontekst = self._kontekst_rozdzialu(
                postacie_rozdzialu,
                rozdzial_tytul,
                widziane_postacie,
                "\n".join(teksty_rozdzialu_buf),
                wzmiankowane_przedmioty,
            )
            if kontekst:
                lines.extend(kontekst)

        if sekcji_wypisanych == 0:
            lines.append("*W aktualnym zakresie i zbiorze polskich tłumaczeń brak jeszcze ukończonych rozdziałów do tej księgi.*")
            lines.append("")

        return ZbudowanyPlik(
            nazwa=nazwa_pliku,
            tytul=tytul,
            opis=opis,
            linie=lines,
            statystyka={
                "rozdzialow": sekcji_wypisanych,
                "zadan": zadan_wypisanych,
                "scen": scen_wypisanych,
                "przetlumaczono": done_total,
                "wszystkich": all_total,
            },
        )

    def _zbierz_wiersze_tabeli(self, tbl: str) -> list[tuple[str, dict[str, str]]]:
        rows = self.tabele.get(tbl, {})
        return sorted(rows.items(), key=lambda x: _naturalny(x[0]))

    def _buduj_encyklopedie_swiata(self) -> ZbudowanyPlik:
        lines: list[str] = [
            "# Encyklopedia świata, bohaterowie i księgi — Where Winds Meet",
            "",
            "Kompendium wiedzy o świecie gry: kalendarium historyczne, regiony, sekty i frakcje,",
            "biografie bohaterów Jianghu, zapiski regionalne, księgi z gry oraz listy i poszlaki.",
            "",
        ]
        done_total = 0
        all_total = 0

        def sekcja_tabelowa(
            tytul: str,
            tbl: str,
            map_col: list[tuple[str, str]],
            *,
            jak_lista: bool = False,
            domyslny_prefiks: str = "Wpis",
        ) -> None:
            nonlocal done_total, all_total
            rows = self._zbierz_wiersze_tabeli(tbl)
            if not rows:
                return
            wypisane_wiersze: list[list[str]] = []
            sekcja_linie: list[str] = []
            d_s = 0
            t_s = 0
            for rid, cols in rows:
                sloty = [cols[k] for k, _ in map_col if k in cols]
                d_r, t_r = self._stat_slotow(sloty)
                d_s += d_r
                t_s += t_r
                if not self._ma_dopuszczalne_pokrycie(d_r, t_r):
                    continue
                if jak_lista:
                    nazwa = self._tekst(cols.get(map_col[0][0]), fallback_label="tytułu", jedna_linia=True) or f"{domyslny_prefiks} #{rid}"
                    sekcja_linie.append(f"### {nazwa}")
                    for col_key, label in map_col[1:]:
                        val = self._tekst(cols.get(col_key), fallback_label=label.lower())
                        if val:
                            sekcja_linie.append(f"- **{label}:** {val}")
                    sekcja_linie.append("")
                else:
                    wiersz = [
                        self._tekst(cols.get(col_key), fallback_label=label.lower(), jedna_linia=True) or ""
                        for col_key, label in map_col
                    ]
                    if any(wiersz):
                        wypisane_wiersze.append(wiersz)
            done_total += d_s
            all_total += t_s
            if jak_lista and sekcja_linie:
                lines.append(f"## {tytul} ({d_s}/{t_s})")
                lines.append("")
                lines.extend(sekcja_linie)
            elif wypisane_wiersze:
                lines.append(f"## {tytul} ({d_s}/{t_s})")
                lines.append("")
                lines.extend(formatuj_tabele([label for _, label in map_col], wypisane_wiersze))
                lines.append("")

        sekcja_tabelowa(
            "Kalendarium i wydarzenia historyczne",
            "world_view_history_info",
            [("name", "Wydarzenie"), ("time_1", "Era / rok chiński"), ("time_2", "Data")],
        )
        sekcja_tabelowa(
            "Regiony świata",
            "world_view_region_info",
            [("name", "Region"), ("introduction", "Opis regionu")],
            jak_lista=True,
            domyslny_prefiks="Region",
        )
        sekcja_tabelowa(
            "Frakcje i ugrupowania (Shili)",
            "world_view_shili_data",
            [
                ("name", "Frakcja"),
                ("introduction_short", "Motto / skrót"),
                ("introduction_location", "Siedziba"),
                ("introduction_long", "Historia i charakterystyka"),
            ],
            jak_lista=True,
            domyslny_prefiks="Frakcja",
        )
        sekcja_tabelowa(
            "Linie dziedzictwa sekt",
            "school_sect_chuancheng_data",
            [
                ("school_name", "Sekta"),
                *[(f"generation_description_{i}", f"Pokolenie {i}") for i in range(1, 11)],
            ],
            jak_lista=True,
            domyslny_prefiks="Sekta",
        )

        # Postacie z encyklopedii (`ix.encyklopedia` + `world_view_person_info`)
        postacie_linie: list[str] = []
        d_p_sum = 0
        t_p_sum = 0
        for pid, entry in sorted(self.ix.encyklopedia.items()):
            hist_keys = [
                k
                for item in entry.get("historie", ())
                for k in (item if isinstance(item, (list, tuple)) else [item])
                if k
            ]
            slots = [s for s in [entry.get("nazwa"), entry.get("inna_nazwa"), *entry.get("tozsamosc", ()), *hist_keys] if s]
            d_p, t_p = self._stat_slotow(slots)
            d_p_sum += d_p
            t_p_sum += t_p
            if not self._ma_dopuszczalne_pokrycie(d_p, t_p):
                continue
            toz = [t for t in (self._tekst(k, jedna_linia=True) for k in entry.get("tozsamosc", ())) if t]
            hist_wypisy: list[str] = []
            for idx, item in enumerate(entry.get("historie", ()), 1):
                if isinstance(item, (list, tuple)):
                    tyt_h = self._tekst(item[0] if len(item) > 0 else None, jedna_linia=True)
                    opis_h = self._tekst(item[1] if len(item) > 1 else None)
                    if tyt_h and opis_h:
                        hist_wypisy.append(f"- **Wpis biograficzny {idx} — {tyt_h}:** {opis_h}")
                    elif tyt_h or opis_h:
                        hist_wypisy.append(f"- **Wpis biograficzny {idx}:** {tyt_h or opis_h}")
                elif item:
                    h_pl = self._tekst(item)
                    if h_pl:
                        hist_wypisy.append(f"- **Wpis biograficzny {idx}:** {h_pl}")
            if not toz and not hist_wypisy and self.zakres != "wszystko":
                continue
            nazwa = self._tekst(entry.get("nazwa"), fallback_label="imienia", jedna_linia=True) or f"Postać #{pid}"
            inna = self._tekst(entry.get("inna_nazwa"), jedna_linia=True)
            postacie_linie.append(f"### {nazwa}" + (f" ({inna})" if inna else ""))
            if toz:
                postacie_linie.append(f"- **Tożsamość:** {'; '.join(toz)}")
            postacie_linie.extend(hist_wypisy)
            postacie_linie.append("")
        done_total += d_p_sum
        all_total += t_p_sum
        if postacie_linie:
            lines.append(f"## Postacie Jianghu — encyklopedia ({d_p_sum}/{t_p_sum})")
            lines.append("")
            lines.extend(postacie_linie)

        sekcja_tabelowa(
            "Kompendium świata (Archiwum)",
            "manual_items",
            [
                ("bowu_name", "Hasło"),
                ("describe", "Opis"),
                ("shiyi_show_word", "Cytat / przekaz"),
                ("shiyi_show_word_from", "Źródło"),
            ],
            jak_lista=True,
        )
        sekcja_tabelowa(
            "Opowieści i zapiski regionalne",
            "region_collect_jianwen_data",
            [("jianwen_title", "Tytuł"), ("jianwen_text", "Treść"), ("jianwen_from", "Źródło")],
            jak_lista=True,
        )

        # Księgi z gry (`book_config`: name, author, page_1..page_8)
        book_rows = self._zbierz_wiersze_tabeli("book_config")
        book_lines: list[str] = []
        d_b_sum = 0
        t_b_sum = 0
        for rid, cols in book_rows:
            page_cols = sorted(
                (c for c in cols if c.startswith("page_")),
                key=lambda x: (0, int(x.split("_")[1])) if x.split("_")[1].isdigit() else (1, 0),
            )
            sloty = [cols[c] for c in ("name", "author", *page_cols) if c in cols]
            d_b, t_b = self._stat_slotow(sloty)
            d_b_sum += d_b
            t_b_sum += t_b
            if not self._ma_dopuszczalne_pokrycie(d_b, t_b):
                continue
            tytul_k = self._tekst(cols.get("name"), fallback_label="tytułu księgi", jedna_linia=True) or f"Księga #{rid}"
            autor_k = self._tekst(cols.get("author"), jedna_linia=True)
            book_lines.append(f"### {tytul_k}" + (f" — *{autor_k}*" if autor_k else ""))
            for idx, pcol in enumerate(page_cols, 1):
                tresc = self._tekst(cols.get(pcol), fallback_label=f"strony {idx}")
                if tresc:
                    book_lines.append(f"**Strona {idx}:**\n{tresc}\n")
            book_lines.append("")
        done_total += d_b_sum
        all_total += t_b_sum
        if book_lines:
            lines.append(f"## Księgi z gry ({d_b_sum}/{t_b_sum})")
            lines.append("")
            lines.extend(book_lines)

        sekcja_tabelowa(
            "Listy i koperty z misji",
            "tasks_envelop_data",
            [("to", "Adresat / tytuł"), ("text", "Treść listu"), ("melody_solved_text", "Rozwiązanie / szyfr")],
            jak_lista=True,
        )
        sekcja_tabelowa(
            "Notatnik poszlak i śledztw",
            "ever_know_clue_data",
            [("clue", "Poszlaka"), ("record", "Gdzie odnotowano")],
        )

        if done_total == 0 and self.zakres != "wszystko":
            lines.append("*Brak przetłumaczonych haseł encyklopedycznych w wybranym zakresie.*")
            lines.append("")

        return ZbudowanyPlik(
            nazwa="03_encyklopedia_swiata.md",
            tytul="Encyklopedia świata, bohaterowie i księgi",
            opis="Historia, regiony, sekty, biografie postaci, kompendium, księgi z gry oraz poszlaki.",
            linie=lines,
            statystyka={"przetlumaczono": done_total, "wszystkich": all_total},
        )

    def _buduj_przedmioty(self) -> ZbudowanyPlik:
        lines: list[str] = [
            "# Przedmioty i ekwipunek — Where Winds Meet",
            "",
            "Zestawienie wyposażenia, artefaktów, materiałów i przedmiotów fabularnych wraz z ich historią.",
            "",
        ]
        done_total = 0
        all_total = 0

        for tytul, tbl in (
            ("Wyposażenie (broń, pancerz i narzędzia)", "equip_items"),
            ("Przedmioty, artefakty i zasoby", "stuff_items"),
        ):
            rows = self._zbierz_wiersze_tabeli(tbl)
            wiersze_tab: list[list[str]] = []
            d_s = 0
            t_s = 0
            for rid, cols in rows:
                sloty = [cols[c] for c in ("name", "brief_describe_str", "describe_str", "story_describe_str") if c in cols]
                d_r, t_r = self._stat_slotow(sloty)
                d_s += d_r
                t_s += t_r
                if not self._ma_dopuszczalne_pokrycie(d_r, t_r):
                    continue
                nazwa = self._tekst(cols.get("name"), fallback_label="nazwy", jedna_linia=True) or f"Przedmiot #{rid}"
                opis_kr = self._tekst(cols.get("brief_describe_str"), jedna_linia=True)
                opis_dl = self._tekst(cols.get("describe_str"), jedna_linia=True)
                historia = self._tekst(cols.get("story_describe_str"), jedna_linia=True)
                opis_polaczony = " — ".join(p for p in (opis_kr, opis_dl) if p and p != opis_kr) if (opis_kr and opis_dl) else (opis_dl or opis_kr or "")
                wiersze_tab.append([nazwa, opis_polaczony, historia or ""])
            done_total += d_s
            all_total += t_s
            if wiersze_tab:
                lines.append(f"## {tytul} ({d_s}/{t_s})")
                lines.append("")
                lines.extend(formatuj_tabele(["Nazwa", "Opis", "Historia / pochodzenie"], wiersze_tab))
                lines.append("")

        if done_total == 0 and self.zakres != "wszystko":
            lines.append("*Brak przetłumaczonych opisów przedmiotów lub ekwipunku w wybranym zakresie.*")
            lines.append("")

        return ZbudowanyPlik(
            nazwa="04_przedmioty_i_ekwipunek.md",
            tytul="Przedmioty i ekwipunek",
            opis="Katalog wyposażenia oraz przedmiotów fabularnych z opisem i historią.",
            linie=lines,
            statystyka={"przetlumaczono": done_total, "wszystkich": all_total},
        )

    def _buduj_sztuki_walki(self) -> ZbudowanyPlik:
        lines: list[str] = [
            "# Sztuki walki i zdolności — Where Winds Meet",
            "",
            "Style walki (Kongfu), Sztuki Wewnętrzne (Xinfa), techniki Jianghu oraz zdolności bojowe.",
            "",
        ]
        done_total = 0
        all_total = 0

        konfiguracje = [
            ("Style walki (Kongfu)", "kongfu", [("name", "Styl"), ("description", "Opis"), ("attr_tip[]", "Atut / typ")]),
            ("Sztuki wewnętrzne (Xinfa)", "xinfa", [("name", "Sztuka"), ("passive_skill_brief_description", "Efekt / opis")]),
            (
                "Umiejętności Jianghu",
                "jianghu_skills",
                [
                    ("jianghu_skill_name", "Umiejętność"),
                    ("function_description", "Rola"),
                    ("jianghu_description", "Opis działania"),
                    ("jianghu_background", "Tło fabularne"),
                ],
            ),
            ("Zdolności bojowe (Qishu)", "qishu_combat_data", [("name", "Zdolność"), ("description", "Opis")]),
        ]

        for tytul, tbl, kolumny in konfiguracje:
            rows = self._zbierz_wiersze_tabeli(tbl)
            wiersze_tab: list[list[str]] = []
            d_s = 0
            t_s = 0
            for rid, cols in rows:
                # Nazwy kolumn w kongfu czasem mają `name` lub brak osobnej kolumny; fallback po pierwszej pasującej
                sloty = [cols[c] for c, _ in kolumny if c in cols]
                if not sloty and cols:
                    sloty = list(cols.values())
                d_r, t_r = self._stat_slotow(sloty)
                d_s += d_r
                t_s += t_r
                if not self._ma_dopuszczalne_pokrycie(d_r, t_r):
                    continue
                wiersz = [
                    self._tekst(cols.get(col_k), fallback_label=lbl.lower(), jedna_linia=True) or ""
                    for col_k, lbl in kolumny
                ]
                if not wiersz[0] and not any(wiersz[1:]):
                    continue
                if not wiersz[0]:
                    wiersz[0] = f"{kolumny[0][1]} #{rid}"
                wiersze_tab.append(wiersz)
            done_total += d_s
            all_total += t_s
            if wiersze_tab:
                lines.append(f"## {tytul} ({d_s}/{t_s})")
                lines.append("")
                lines.extend(formatuj_tabele([lbl for _, lbl in kolumny], wiersze_tab))
                lines.append("")

        if done_total == 0 and self.zakres != "wszystko":
            lines.append("*Brak przetłumaczonych sztuk walki lub zdolności w wybranym zakresie.*")
            lines.append("")

        return ZbudowanyPlik(
            nazwa="05_sztuki_walki_i_zdolnosci.md",
            tytul="Sztuki walki i zdolności",
            opis="Style walki, sztuki wewnętrzne, techniki Jianghu i umiejętności bojowe.",
            linie=lines,
            statystyka={"przetlumaczono": done_total, "wszystkich": all_total},
        )

    def _buduj_otoczenie(self) -> ZbudowanyPlik:
        lines: list[str] = [
            "# Rozmowy świata i sceny poboczne poza zadaniami — Where Winds Meet",
            "",
            "> **Uwaga redakcyjna:** Ta część grupuje dialogi bez wpisu w tabelach zadań (projekty oraz rozmowy tła NPC).",
            "> Ich kolejność ma charakter katalogowy, nie chronologiczny.",
            "",
        ]
        done_total = 0
        all_total = 0
        scen_cnt = 0

        if self.uklad.projekty:
            for project, numbers in self.uklad.projekty:
                sec_lines: list[str] = []
                for numer in numbers:
                    s_lines, sd, st, _ = self._renderuj_scene(numer, self.uklad.miejsca[numer])
                    done_total += sd
                    all_total += st
                    if s_lines:
                        scen_cnt += 1
                        sec_lines.extend(s_lines)
                if sec_lines:
                    lines.append(f"## Projekt: {project or '(bez nazwy)'}")
                    lines.append("")
                    lines.extend(sec_lines)

        for (kind, value), numbers in self.uklad.tlo:
            sec_lines = []
            for numer in numbers:
                s_lines, sd, st, _ = self._renderuj_scene(numer, self.uklad.miejsca[numer])
                done_total += sd
                all_total += st
                if s_lines:
                    scen_cnt += 1
                    sec_lines.extend(s_lines)
            if sec_lines:
                miejsce_lbl = (self._miejsce(value) or f"Obszar #{value}") if kind == "miejsce" else f"Reakcje NPC: {value}"
                lines.append(f"## {miejsce_lbl}")
                lines.append("")
                lines.extend(sec_lines)

        return ZbudowanyPlik(
            nazwa="06_rozmowy_otoczenia.md",
            tytul="Rozmowy świata i sceny poza zadaniami",
            opis="Katalog dialogów bez powiązania z zadaniami oraz rozmów tła NPC.",
            linie=lines,
            statystyka={"scen": scen_cnt, "przetlumaczono": done_total, "wszystkich": all_total},
        )

    def buduj(self) -> list[ZbudowanyPlik]:
        # Najpierw budujemy księgi zadań, aby wszystkie przerywniki i powtórki włączone przy zadaniach
        # trafiły do `self.przerywniki_w_zadaniach` i nie zostały powielone na końcu `00_prolog_i_przerywniki.md`.
        glowny = self._buduj_sekcje_zadan(
            nazwa_pliku="01_watek_glowny.md",
            tytul="Wątek główny — scenariusz chronologiczny",
            opis="Główna linia fabularna w kolejności rozdziałów, łańcuchów zadań, scen i wyborów.",
            wstep=[
                "Główna linia fabularna ułożona według rozdziałów oraz łańcuchów zależności zadań z gry.",
                "Sceny bez pewnego zaczepienia zdarzeniem oznaczono `*(kolejność przybliżona)*` (według numeracji dialogów gry).",
                "Przy każdym rozdziale znajdziesz również pierwsze pojawienia bohaterów z encyklopedii oraz wzmiankowane pojęcia.",
            ],
            tylko_watek_glowny=True,
        )
        poboczne = self._buduj_sekcje_zadan(
            nazwa_pliku="02_zadania_poboczne_i_swiat.md",
            tytul="Zadania poboczne, kampanie i historie świata",
            opis="Zadania poboczne pogrupowane według kategorii aktywności gry.",
            wstep=[
                "> **Uwaga dla czytelnika:** Zadania w tej księdze (Spotkania, Kampanie, Dziedzictwo Jianghu, Sprawy świata itp.)",
                "> są uporządkowane według kategorii i wewnętrznych łańcuchów zależności, lecz w otwartym świecie gry można je",
                "> podejmować w dowolnej kolejności. Sceny bez pewnego punktu zaczepienia oznaczono `*(kolejność przybliżona)*`.",
            ],
            tylko_watek_glowny=False,
        )
        prolog = self._buduj_prolog_i_przerywniki()
        pliki = [
            prolog,
            glowny,
            poboczne,
            self._buduj_encyklopedie_swiata(),
            self._buduj_przedmioty(),
            self._buduj_sztuki_walki(),
        ]
        if self.z_otoczeniem:
            pliki.append(self._buduj_otoczenie())
        return pliki


def _podziel_na_czesci(plik: ZbudowanyPlik, limit_bajtow: int) -> list[tuple[str, list[str], dict]]:
    """Jeśli treść przekracza `limit_bajtow`, dziel ją na granicach sekcji `## `."""
    pelny_tekst = "\n".join(plik.linie).rstrip("\n") + "\n"
    if limit_bajtow <= 0 or len(pelny_tekst.encode("utf-8")) <= limit_bajtow:
        return [(plik.nazwa, [pelny_tekst], plik.statystyka)]

    # Wydziel nagłówek wstępny przed pierwszą sekcją `## `.
    intro: list[str] = []
    sekcje: list[list[str]] = []
    biezaca: list[str] | None = None
    for line in plik.linie:
        if line.startswith("## "):
            if biezaca is not None:
                sekcje.append(biezaca)
            biezaca = [line]
        elif biezaca is None:
            intro.append(line)
        else:
            biezaca.append(line)
    if biezaca is not None:
        sekcje.append(biezaca)

    if len(sekcje) <= 1:
        return [(plik.nazwa, [pelny_tekst], plik.statystyka)]

    czesc_grupy: list[list[list[str]]] = []
    cur: list[list[str]] = []
    cur_bytes = sum(len(l.encode("utf-8")) + 1 for l in intro)
    for sec in sekcje:
        sec_bytes = sum(len(l.encode("utf-8")) + 1 for l in sec)
        if cur and cur_bytes + sec_bytes > limit_bajtow:
            czesc_grupy.append(cur)
            cur = [sec]
            cur_bytes = sum(len(l.encode("utf-8")) + 1 for l in intro) + sec_bytes
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
    wyj_zip: Path | None = None,
    limit_bajtow: int = DOMYSLNY_LIMIT_BAJTOW,
    zakres: str = "przetlumaczone",
    plec: str = "oba",
    wersja: str = "v1",
    zrodlo_przekladow: str = "",
    podglad_en: bool = False,
) -> dict:
    """Zapisz pliki czytanek, `README.md` oraz opcjonalny deterministyczny ZIP."""
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

    # README.md ze spisem treści i metryczką edycji
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
        "Zestaw plików `.md` do czytania fabuły i encyklopedii świata gry poza grą",
        "(w edytorze tekstu lub przeglądarce Markdown). Wygenerowano automatycznie z wyciągu",
        "`index/` oraz polskich przekładów gry." if not podglad_en else "`index/` w trybie podglądu angielskiego.",
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
        "## Jak czytać chronologicznie",
        "",
        "1. Zacznij od `00_prolog_i_przerywniki.md` (sekwencja intro oraz napisy filmowego Prologu).",
        "2. Przejdź do `01_watek_glowny.md` — rozdziały i zadania idą w kolejności fabularnej gry;",
        "   pod każdym rozdziałem znajdują się pierwsze wpisy bohaterów z encyklopedii oraz wzmiankowane techniki.",
        "3. Wątki poboczne i opowieści regionów czytaj w `02_zadania_poboczne_i_swiat.md`.",
        "4. Gdy chcesz zajrzeć do całych ksiąg z gry, listów, kalendarium lub pełnych biografii, otwórz `03_encyklopedia_swiata.md`,",
        "   a do opisów przedmiotów i sztuk walki — `04_przedmioty_i_ekwipunek.md` oraz `05_sztuki_walki_i_zdolnosci.md`.",
        "",
    ]
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
        import hashlib
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
    parser.add_argument("--z-otoczeniem", action="store_true", help="dołącz dodatkowy plik rozmów poza zadaniami")
    parser.add_argument("--podglad-en", action="store_true", help="tryb podglądu formy z angielskim tekstem z index/ (bez tłumaczenia PL)")
    parser.add_argument("--podziel-powyzej", type=int, default=DOMYSLNY_LIMIT_BAJTOW, help="limit bajtów pliku przed podziałem na części (0 = nie dziel)")
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
            wersja=args.wersja,
        )
        pliki = builder.buduj()
        raport = zapisz_czytanki(
            pliki,
            Path(args.wyj_katalog),
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
