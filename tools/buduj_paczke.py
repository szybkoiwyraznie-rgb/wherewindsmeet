#!/usr/bin/env python3
"""Pakiet dla tłumacza: `README.md` + `sceny.zip` + `widoki.zip`, zbudowany z `index/`.

Układ jest wzorowany na pakiecie SRW Y (`plik_dla_tlumacza_v8.zip`), z różnicami
wynikającymi z gry: źródłem jest tekst chiński, angielski jest pomocą, a każdy
element ma linię `klucz:`, po której import znajduje miejsce w grze.

    python3 tools/buduj_paczke.py --indeks index --wyj dist/paczka_wwm_v1 --wersja 1 --data 2026-11-12

Pakiet uzupełniający po aktualizacji gry (tylko nowe teksty, w kontekście):

    python3 tools/audyt_aktualizacji.py --stary STARY_INDEKS --nowy index --wyj dist/audyt
    python3 tools/buduj_paczke.py --indeks index --wyj dist/paczka_wwm_v2 --wersja 2 \\
        --tylko-sloty dist/audyt/nowe_sloty.txt --tlumaczenie tlumaczenie

Zasady składania:
- każdy tekst ma w całym pakiecie **jedno** miejsce z `PL:` — pierwsze wystąpienie
  w kolejności: sceny, potem widoki; dalsze wystąpienia są oznaczone jako powtórzenia;
- kolejność scen wylicza `tools/uklad_scen.py` (zadania, następstwa, numeracja);
- widoki grupują teksty spoza scen według tabeli i pola gry, z którego pochodzą.

Skrypt czyta wyłącznie katalog wyciągu i (opcjonalnie) magazyn przekładów —
nie potrzebuje plików gry.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

try:
    from tools import format_paczki as fmt
    from tools import indeks as indeks_mod
    from tools import tlumaczenie as magazyn_mod
    from tools import uklad_scen
    from tools import wypisz
except ImportError:  # uruchomienie jako skrypt
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from tools import format_paczki as fmt
    from tools import indeks as indeks_mod
    from tools import tlumaczenie as magazyn_mod
    from tools import uklad_scen
    from tools import wypisz

LIMIT_PLIKU = 1_500_000  # bajtów na jeden plik .md
WCIECIE = "   "
MOMENT = {
    "przyjecie": "przyjęcie zadania",
    "rozmowa": "rozmowa w trakcie zadania",
    "zakonczenie": "zakończenie zadania",
    "wybor": "pytanie z wyborem w zadaniu",
    "nastepstwo": "następstwo poprzedniej sceny",
}
ETYKIETA = {"k": "Kwestia", "p": "Plansza", "wi": "Wizytówka — imię", "wt": "Wizytówka — tytuł", "i": "Tekst sceny"}
WARIANT = {1: "bohater", 2: "bohaterka"}
TYP_GRACZ = 1  # `entity_type` grupy mówcy: postać gracza (tools/sceny_z_bazy.TYP_GRACZ)

WIDOKI = [
    ("00_postacie", "Postacie: imiona, tytuły, opisy, encyklopedia osób"),
    ("01_zadania", "Zadania: nazwy, cele, opisy i podsumowania"),
    ("02_wybory_i_rozmowy", "Wybory gracza i teksty rozmów spoza scen"),
    ("03_przedmioty", "Przedmioty, wyposażenie, stroje, budowle"),
    ("04_walka_i_umiejetnosci", "Walka: umiejętności, efekty, talenty, przeciwnicy"),
    ("05_swiat_i_miejsca", "Świat: miejsca, regiony, mapy, obiekty"),
    ("06_encyklopedia_i_ksiegi", "Encyklopedia, księgi, zapiski, listy, przerywniki"),
    ("07_komunikaty", "Komunikaty i dymki (text_msg i pokrewne)"),
    ("08_interfejs_i_systemy", "Interfejs i systemy gry"),
    ("09_pozostale", "Pozostałe tabele"),
    ("10_bez_zrodla", "Teksty, których nie wskazuje żadna tabela ani scena"),
]
BEZ_ZRODLA = "10_bez_zrodla"
POZOSTALE = "09_pozostale"
# Tabele, które powtarzają kwestie scen (te same teksty co w `dialog_timelines`):
# ich powtórzeń nie wypisujemy w widokach, bo każda taka kwestia ma `PL:` w scenie.
KOPIE_KWESTII = {"debate_guider_dialog_data"}
# (wzorzec nazwy tabeli, widok) — wygrywa pierwsza pasująca reguła
REGULY = [
    (r"(text_msg|ccs_text_msg|programmer_text_msg)", "07_komunikaty"),
    (
        r"(world_view_person|world_view_people|world_view_total_person|world_view_real_npc|world_view_npc|"
        r"entity_billboard|entity_init_data|entity_attr|entity_interact|entity$|npc_amity|npc_tags|npc_view|"
        r"nickname|st_nickname|title|homeland_npc|longmen_inn_rnd_name|amity_)",
        "00_postacie",
    ),
    (
        r"(region_collect_jianwen|manual_|ever_know|guider_tujian|book_|wenjinguan|world_view_|display_poem|"
        r"cutscenes|emails_data|news_|tasks_envelop|bowu_|clue|jianghu_chapter|jianghu_story|loading_base|"
        r"plot_recap|task_cutscene_replay)",
        "06_encyklopedia_i_ksiegi",
    ),
    (
        r"(tasks|task_|group_tasks|team_target|line_run|recall_task|gameplay_tasks|battle_pass_tasks|"
        r"activity_center_task|realm_task|zhige_realm_task|eavesdrop|guider_task|strongpoint|new_npc_task)",
        "01_zadania",
    ),
    (
        r"(branch_|npc_talk_options|npc_dialog|dialog_|chat_npc|chess_conversation|zouzhe|debate_|scene_dialog|"
        r"talk_|text_ctr|ai_npc_dialog|ai_event|active_interact_way)",
        "02_wybory_i_rozmowy",
    ),
    (
        r"(stuff_|equip_|fashion_|guise_|building_|all_homeland_stuff|compound_|fenghualu|waiguan|item_|weapon_|"
        r"mount_|pet_|food_|cook|recipe|treasure|shop|store_|mall|gift|reward|drop_|currency|common_scores|"
        r"compose|craft)",
        "03_przedmioty",
    ),
    (
        r"(buff|skills|skill_|passive_skills|kongfu|talent_|xinfa|combat_|npc_ux_skill|acupoints|magic_field|"
        r"ride_skills|identity_buff|AL\.|jianghu_skill|qishu|boss_|monster_|disease_|battle_guide|attr_|formula|"
        r"langzhong|tower_|dead_config)",
        "04_walka_i_umiejetnosci",
    ),
    (
        r"(spaces\.|space_|region_|map_|maps\.|fuben_|post$|pre_road_sign|transfer|revive_|navi_|level_name|"
        r"area_|scene_|instance_|dungeon)",
        "05_swiat_i_miejsca",
    ),
    (
        r"(setting|input_func|guider_|gameplay_info|ac_raw|achievement|rank_|activity|activities|club_|homeland_|"
        r"social_|school_|pvp_|team_|ui_|windows_key|xbox|festival|version_|common_share|royal_exam|xiayuan|"
        r"ws_ans|invigilate|huashu|monopoly|footprint|mahjong|chess|flower|battle_pass|gang_|guild|friend|mail|"
        r"emoji|photo|camera|music|instrument|common_tip|red_pop|tips|notice|badge|head$)",
        "08_interfejs_i_systemy",
    ),
]
_REGULY = [(re.compile("^" + pattern), view) for pattern, view in REGULY]
OPIS_TABELI = {
    "entity_billboard": "tabliczki z nazwami i tytułami postaci oraz obiektów",
    "entity_init_data": "nazwy obiektów, z którymi można wejść w interakcję",
    "entity_attr": "opisy postaci (panel informacji o NPC)",
    "world_view_person_info": "encyklopedia osób: imiona i daty",
    "world_view_person_event": "encyklopedia osób: historie postaci",
    "world_view_person_voice": "encyklopedia osób: cytaty głosowe",
    "world_view_people_identity": "encyklopedia osób: kim jest postać",
    "npc_amity_relation_data": "relacje z NPC: opowieści odblokowywane sympatią",
    "tasks": "zadania: nazwa, cel na ekranie, opis w dzienniku",
    "task_group_info": "grupy zadań: tytuły rozdziałów i podsumowania",
    "tasks_envelop_data": "listy i koperty w zadaniach",
    "plot_recap_data": "streszczenia fabuły",
    "branch_data": "wybory gracza (pytania bez sceny w danych) i tytuły okien wyboru",
    "stuff_items": "przedmioty: nazwa, opis, opis fabularny",
    "buff": "efekty (buffy): nazwa i opis",
    "skills": "umiejętności",
    "manual_items": "kompendium (博物): hasła i opisy",
    "ever_know_clue_data": "notatnik poszlak",
    "region_collect_jianwen_data": "zapiski z podróży (见闻)",
    "book_config": "księgi do czytania w grze",
    "emails_data": "poczta w grze",
    "cutscenes": "przerywniki: plansze i streszczenia",
    "text_msg": "komunikaty i dymki nad postaciami",
    "ccs_text_msg": "komunikaty interfejsu",
    "programmer_text_msg": "komunikaty systemowe",
    "spaces.*.region": "nazwy obszarów w świecie",
    "spaces.*.entity": "obiekty rozmieszczone w świecie: nazwy i opisy",
    "space_info": "nazwy przestrzeni (mapy, instancje)",
    "region_game_config": "nazwy aktywności w regionach",
    "ac_raw": "osiągnięcia",
    "guider_task": "samouczki i podpowiedzi",
}


def kategoria(rodzaj: str) -> str:
    """Widok dla tabeli; bliźniak `__grey` trafia tam, gdzie tabela podstawowa."""
    name = rodzaj.removesuffix("__grey")
    for pattern, view in _REGULY:
        if pattern.match(name):
            return view
    return POZOSTALE


def _naturalny(value: str):
    return (0, int(value), "") if value.lstrip("-").isdigit() else (1, 0, value)


def _slug(text: str) -> str:
    out = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return out or "bez-nazwy"


class Pisarz:
    """Seria plików `.md` o wspólnej nazwie, dzielona na części poniżej limitu rozmiaru."""

    def __init__(self, katalog: Path, baza: str, tytul: str, wstep: list[str], limit: int = LIMIT_PLIKU):
        self.katalog, self.baza, self.tytul, self.wstep, self.limit = katalog, baza, tytul, wstep, limit
        self.pliki: list[dict] = []
        self._linie: list[str] = []
        self._rozmiar = 0
        self._naglowki: dict[int, list[str]] = {}
        self._czekaja: set[int] = set()
        self._wypisane: set[int] = set()

    def naglowek(self, poziom: int, linie: list[str]) -> None:
        """Ustaw nagłówek poziomu; wypisze się przed najbliższym blokiem."""
        for deeper in [level for level in self._naglowki if level >= poziom]:
            del self._naglowki[deeper]
            self._czekaja.discard(deeper)
            self._wypisane.discard(deeper)
        self._naglowki[poziom] = linie
        self._czekaja.add(poziom)

    def _nowa_czesc(self) -> None:
        self._zamknij()
        number = len(self.pliki) + 1
        self.pliki.append({"plik": f"{self.baza}_{number:02d}.md", "scen": 0, "elementow": 0, "do_wpisania": 0})
        self._linie = [f"# {self.tytul} — część {number}", "", *self.wstep, ""]
        self._rozmiar = sum(len(line.encode("utf-8")) + 1 for line in self._linie)
        self._czekaja = set(self._naglowki)

    def blok(self, linie: list[str], *, scen: int = 0, elementow: int = 0, do_wpisania: int = 0) -> str:
        """Dopisz blok (scenę, grupę elementów); zwraca nazwę pliku, do którego trafił."""
        size = sum(len(line.encode("utf-8")) + 1 for line in linie)
        if not self.pliki or (self._rozmiar + size > self.limit and self.pliki[-1]["elementow"]):
            self._nowa_czesc()
        head: list[str] = []
        for level in sorted(self._czekaja):
            lines = list(self._naglowki[level])
            if level in self._wypisane:  # nagłówek był już w poprzedniej części serii
                lines = [lines[0] + " (ciąg dalszy)"]
            self._wypisane.add(level)
            head += lines + [""]
        self._czekaja.clear()
        self._linie += head + linie + [""]
        self._rozmiar += size + 1 + sum(len(line.encode("utf-8")) + 1 for line in head)
        entry = self.pliki[-1]
        entry["scen"] += scen
        entry["elementow"] += elementow
        entry["do_wpisania"] += do_wpisania
        return entry["plik"]

    def _zamknij(self) -> None:
        if self.pliki and self._linie:
            path = self.katalog / self.pliki[-1]["plik"]
            path.write_text("\n".join(self._linie).rstrip("\n") + "\n", encoding="utf-8", newline="\n")
            self._linie = []

    def koniec(self) -> list[dict]:
        self._zamknij()
        return self.pliki


class Generator:
    def __init__(self, ix, magazyn=None, tylko_sloty: set[str] | None = None, *, tylko_z_en: bool = False):
        self.ix = ix
        self.magazyn = magazyn or magazyn_mod.Magazyn()
        self.tylko = tylko_sloty  # None = pakiet pełny; zbiór = pakiet uzupełniający
        self.tylko_z_en = tylko_z_en
        self.sloty: dict[str, tuple[str, str]] = {}  # slot -> (plik, opis miejsca)
        self.liczby = Counter()
        self.uklad = uklad_scen.uloz(ix)
        self._nazwa_po_tekscie: dict[str, str] = {}
        for row in ix.postacie.values():
            if row.get("n"):
                self._nazwa_po_tekscie.setdefault(ix.zh(row["n"]), row["n"])
        self._encyklopedia = {row["nazwa"]: row for row in ix.encyklopedia.values() if row.get("nazwa")}
        for key in self._encyklopedia:
            self._nazwa_po_tekscie.setdefault(ix.zh(key), key)
        self._wybory_po: dict[int, list[dict]] = defaultdict(list)
        for key in sorted(ix.wybory):
            row = ix.wybory[key]
            for dialog in row.get("po_dialogach", ()):
                self._wybory_po[dialog].append(row)
        self.spis_scen: list[tuple] = []  # (numer sceny, dialog, plik, część, zadanie, elementów)
        self.spis_zadan: list[dict] = []
        self.serie: list[dict] = []

    # ----------------------------------------------------------- teksty

    def para(self, klucz: str | None) -> str:
        """„źródło (angielski)” w jednej linii — do nagłówków i etykiet."""
        if not klucz or klucz not in self.ix.teksty:
            return ""
        text = self.ix.teksty[klucz]
        source = fmt.zakoduj(text.zrodlo)
        if text.en and text.en != text.zrodlo:
            return f"{source} ({fmt.zakoduj(text.en)})"
        return source

    def _slot_sceny(self, element: list) -> str:
        return "@" + element[4] if len(element) > 4 and element[3] else element[2]

    def _ma_en(self, slot: str) -> bool:
        if slot.startswith("@"):
            var = self.ix.warianty.get(slot[1:], {})
            text = self.ix.teksty.get(var.get("k", ""))
            return bool(var.get("en") or (text is not None and (text.en is not None or text.z_en)))
        text = self.ix.teksty.get(slot)
        return text is not None and (text.en is not None or text.z_en)

    def _zawiera_nowe(self, sloty) -> bool:
        for slot in sloty:
            if self.tylko is not None and slot not in self.tylko:
                continue
            if self.tylko_z_en and not self._ma_en(slot):
                continue
            return True
        return False

    def _element(self, nr: int, etykieta: str, slot: str, w_bloku: dict, dodatkowe=(), en: str | None = None, miejsce: str = "") -> tuple[list[str], bool]:
        """Linie jednego elementu i informacja, czy otwiera miejsce na `PL:`."""
        key = slot[1:] if slot.startswith("@") else slot
        text = self.ix.teksty[self.ix.warianty[key]["k"]] if slot.startswith("@") else self.ix.teksty[key]
        source = fmt.zakoduj(text.zrodlo)
        lines = [f"{nr}. [{etykieta}] {source}"]
        self.liczby["elementow"] += 1
        if slot in w_bloku:
            lines.append(f"{WCIECIE}(powtórzenie elementu {w_bloku[slot]} — nie wpisuj tu nic)")
            self.liczby["powtorzen"] += 1
            return lines, False
        if slot in self.sloty:
            plik, where = self.sloty[slot]
            lines.append(f"{WCIECIE}(powtórzenie — tłumaczysz raz: {plik}, {where})")
            self.liczby["powtorzen"] += 1
            return lines, False
        w_bloku[slot] = nr
        self._nowe_w_bloku.append((slot, miejsce.format(nr=nr)))
        if not text.zrodlo.strip():
            lines.append(f"{WCIECIE}(pusty tekst — nie ma czego tłumaczyć)")
            self.liczby["pustych"] += 1
            return lines, False
        lines.append(f"{WCIECIE}klucz: {slot}")
        lines += [WCIECIE + line for line in dodatkowe]
        tokens = fmt.rozne_tokeny(source)
        if tokens:
            lines.append(f"{WCIECIE}tokeny: zachowaj dokładnie: {', '.join(tokens)}")
        if en is None:
            en = text.en
        if text.z_en:
            lines.append(f"{WCIECIE}EN: (to jest tekst źródłowy — chińskiej wersji nie ma w danych)")
        elif en:
            lines.append(f"{WCIECIE}EN: {fmt.zakoduj(en)}")
        else:
            lines.append(f"{WCIECIE}EN: (brak wersji angielskiej w grze)")
        done = self.magazyn.przeklad(slot)
        if done is not None:
            lines.append(f"{WCIECIE}PL (już jest): {fmt.zakoduj(done)}")
            self.liczby["juz_przetlumaczone"] += 1
            return lines, False
        if self.tylko_z_en and not self._ma_en(slot):
            lines.append(f"{WCIECIE}(pominięty — brak wersji angielskiej w grze)")
            self.liczby["pominietych_bez_en"] += 1
            return lines, False
        if self.tylko is not None and slot not in self.tylko:
            lines.append(f"{WCIECIE}(tekst z wcześniejszego pakietu — tu nic nie wpisuj)")
            self.liczby["z_wczesniejszego_pakietu"] += 1
            return lines, False
        lines.append(f"{WCIECIE}PL:")
        self.liczby["do_wpisania"] += 1
        return lines, True

    def _zapisz_blok(self, pisarz: Pisarz, lines: list[str], *, scen: int, elementow: int, do_wpisania: int) -> str:
        plik = pisarz.blok(lines, scen=scen, elementow=elementow, do_wpisania=do_wpisania)
        for slot, where in self._nowe_w_bloku:
            self.sloty[slot] = (plik, where)
        self._nowe_w_bloku = []
        return plik

    # ------------------------------------------------------------ sceny

    def _mowca(self, scena: dict, numer: int, podmiana: str | None = None) -> str:
        if numer < 0 or numer >= len(scena["o"]):
            return "bez mówcy"
        person = scena["o"][numer]
        name = podmiana or (person[3] if len(person) > 3 else None)
        if person[1] == TYP_GRACZ:
            return f"gracz ({self.para(name)})" if name else "gracz"
        if name:
            return self.para(name)
        tag = person[0]
        if tag:
            known = self._nazwa_po_tekscie.get(tag)
            english = self.ix.en(known) if known else ""
            return f"{tag}* ({fmt.zakoduj(english)})" if english and english != tag else f"{tag}*"
        return "???"

    def _miejsce(self, numer) -> str:
        row = self.ix.miejsca.get(numer)
        name = self.para(row.get("nazwa")) if row else ""
        if not name and row and row.get("robocza"):
            name = f"{row['robocza']}*"
        return f"{name} [przestrzeń {numer}]" if name else f"przestrzeń {numer}"

    def _naglowek_sceny(self, scena: dict, miejsce, numer_sceny: int) -> list[str]:
        ix = self.ix
        lines = [f"#### Scena {numer_sceny}/{self.razem_scen} — dialog {scena['d']}"]
        if scena.get("p"):
            lines.append(f"- projekt: {scena['p']}")
        if miejsce.czesc == "zadania":
            task = ix.zadania.get(miejsce.zadanie, {})
            name = self.para(task.get("nazwa")) or "(bez nazwy)"
            if miejsce.moment == "numeracja":
                lines.append(
                    f"- zadanie: brak wpisu w tabelach zadań — scena ułożona według numeru, za dialogiem {miejsce.za} "
                    f"(zadanie {miejsce.zadanie}: {name})"
                )
            else:
                target = self.para(task.get("cel"))
                moment = MOMENT.get(miejsce.moment, miejsce.moment)
                if miejsce.moment == "nastepstwo":
                    moment += f" (dialog {miejsce.za})"
                lines.append(f"- zadanie: {miejsce.zadanie} — {name}" + (f" — cel: {target}" if target else "") + f" — {moment}")
        places = scena.get("m") or []
        if places:
            shown = "; ".join(self._miejsce(number) for number in places[:3])
            lines.append(f"- miejsce: {shown}" + (f" (+{len(places) - 3})" if len(places) > 3 else ""))
        refs = scena.get("r") or []
        if refs:
            fields = list(dict.fromkeys(" :: ".join(ix.pola_dialogow[number][:2]) for number, _row in refs))
            more = scena.get("rn", len(refs)) - len(refs)
            lines.append(f"- wywołanie w danych: {'; '.join(fields)}" + (f" (+{more})" if more > 0 else ""))
        config = scena.get("c") or {}
        if config.get("for_oversea"):
            lines.append(f"- wersja dla klienta zachodniego dialogu {config.get('oversea_src_dialog_no')}")
        speaking = Counter(element[1] for element in scena["e"] if element[0] == "k")
        listed, silent = [], []
        seen = set()
        for number, person in enumerate(scena["o"]):
            label = self._mowca(scena, number)
            if label in seen:
                continue
            seen.add(label)
            if number not in speaking:
                silent.append(label)
                continue
            extra = []
            if len(person) > 4 and person[4]:
                extra.append(f"tytuł: {self.para(person[4])}")
            if len(person) > 5 and person[5]:
                extra.append(f"opis: {self.para(person[5])}")
            entry = self._encyklopedia.get(person[3]) if len(person) > 3 else None
            if entry:
                identity = "; ".join(self.para(key) for key in entry.get("tozsamosc", ()))
                extra.append("postać z encyklopedii gry" + (f": {identity}" if identity else ""))
            listed.append(f"  - {label}" + (" — " + " — ".join(extra) if extra else ""))
        if listed:
            lines.append("- uczestnicy:")
            lines += listed
        if silent:
            lines.append(f"- obecni bez kwestii: {', '.join(silent)}")
        return lines

    def _sloty_sceny(self, scena: dict) -> list[str]:
        slots = [self._slot_sceny(element) for element in scena["e"]]
        for row in self._wybory_po.get(scena["d"], ()):
            slots += [choice["tekst"] for choice in row["wybory"]]
        return slots

    def _scena(self, pisarz: Pisarz, numer: int, miejsce) -> None:
        scena = self.ix.sceny[numer]
        if not self._zawiera_nowe(self._sloty_sceny(scena)):
            return
        self.numer_sceny += 1
        where = f"scena {self.numer_sceny}, element {{nr}}"
        lines = self._naglowek_sceny(scena, miejsce, self.numer_sceny) + [""]
        w_bloku: dict[str, int] = {}
        nr = opened = 0
        for element in scena["e"]:
            nr += 1
            label = ETYKIETA[element[0]]
            if element[0] == "k":
                label += f" — {self._mowca(scena, element[1], element[5] if len(element) > 5 else None)}"
            slot = self._slot_sceny(element)
            english = None
            if slot.startswith("@"):
                label += f", wariant: {WARIANT.get(element[3], element[3])}"
                english = self.ix.warianty[slot[1:]].get("en") or ""
            part, is_open = self._element(nr, label, slot, w_bloku, en=english, miejsce=where)
            lines += part
            opened += is_open
        for row in self._wybory_po.get(numer, ()):
            title = self.para(row.get("tytul"))
            lines.append(f"{WCIECIE}— wybór gracza po tej scenie (pytanie {row.get('pytanie')}, krok {row.get('krok')})" + (f": {title}" if title else ""))
            for choice in row["wybory"]:
                nr += 1
                targets = ", ".join(f"dialog {target}" for target in choice.get("dialogi", ()))
                extra = [f"prowadzi do: {targets}"] if targets else []
                part, is_open = self._element(nr, f"Wybór gracza {choice['nr']}", choice["tekst"], w_bloku, dodatkowe=extra, miejsce=where)
                lines += part
                opened += is_open
        plik = self._zapisz_blok(pisarz, lines, scen=1, elementow=nr, do_wpisania=opened)
        self.spis_scen.append((self.numer_sceny, numer, plik, miejsce.czesc, miejsce.zadanie, miejsce.moment, nr))
        self.liczby["scen"] += 1

    def _przerywniki(self, pisarz: Pisarz, task: dict, moment: str) -> None:
        for number in (task.get("przerywniki") or {}).get(moment, ()):
            row = self.ix.przerywniki.get(number)
            if not row or number in self._przerywniki_gotowe:
                continue
            slots = [row[name] for name in ("tekst", "streszczenie") if row.get(name)]
            if not slots or not self._zawiera_nowe(slots):
                continue
            self._przerywniki_gotowe.add(number)
            kind = "przy przyjęciu zadania" if moment == "przyjecie" else "po zakończeniu zadania"
            lines = [f"#### Przerywnik {number} — {kind}", ""]
            w_bloku: dict[str, int] = {}
            nr = opened = 0
            for name, label in (("tekst", "Plansza przerywnika"), ("streszczenie", "Streszczenie przerywnika")):
                if row.get(name):
                    nr += 1
                    part, is_open = self._element(nr, label, row[name], w_bloku, miejsce=f"przerywnik {number}, element {{nr}}")
                    lines += part
                    opened += is_open
            self._zapisz_blok(pisarz, lines, scen=0, elementow=nr, do_wpisania=opened)
            self.liczby["przerywnikow"] += 1

    def _naglowek_zadania(self, numer: int) -> list[str]:
        task = self.ix.zadania[numer]
        lines = [f"### Zadanie {numer} — {self.para(task.get('nazwa')) or '(bez nazwy)'}"]
        if task.get("cel"):
            lines.append(f"- cel: {self.para(task['cel'])}")
        if task.get("opis"):
            lines.append(f"- opis: {self.para(task['opis'])}")
        if task.get("przestrzen") is not None:
            lines.append(f"- miejsce zadania: {self._miejsce(task['przestrzen'])}")
        return lines

    def _nazwa_grupy(self, grupa) -> str:
        row = self.ix.grupy.get(grupa) if grupa is not None else None
        if not row:
            return "zadania bez grupy" if grupa is None else f"grupa {grupa}"
        parts = [self.para(row.get(name)) for name in ("numer_tytulu", "tytul", "nazwa")]
        return " · ".join(part for part in parts if part) or f"grupa {grupa}"

    def _nazwa_typu(self, typ) -> str:
        row = self.ix.typy_zadan.get(typ)
        if row and row.get("nazwa"):
            return self.para(row["nazwa"])
        return "zadania bez typu" if typ is None else f"typ {typ}"

    def sceny(self, katalog: Path) -> None:
        ix, uklad = self.ix, self.uklad
        katalog.mkdir(parents=True, exist_ok=True)
        self._nowe_w_bloku: list[tuple[str, str]] = []
        self._przerywniki_gotowe: set[int] = set()
        self.numer_sceny = 0
        self.razem_scen = sum(
            1 for number in uklad.miejsca if self._zawiera_nowe(self._sloty_sceny(ix.sceny[number]))
        )
        wstep = ["Polski tekst wpisujesz w jednej linii po `PL:`. Zasady i objaśnienie nagłówków: `README.md`."]
        order = 0
        streszczenia = defaultdict(list)
        for row in ix.streszczenia:
            if row.get("tekst"):
                streszczenia[row.get("grupa")].append(row["tekst"])

        def seria(pisarz: Pisarz, opis: str) -> None:
            files = pisarz.koniec()
            if files:
                self.serie.append({"baza": pisarz.baza, "tytul": pisarz.tytul, "opis": opis, "pliki": files})

        # nazwy plików dla typów zadań: angielska nazwa typu, a przy powtórce nazwy — z numerem typu
        slugi: dict = {}
        for typ in uklad_scen.kolejnosc_typow(ix):
            english = ix.en((ix.typy_zadan.get(typ) or {}).get("nazwa"))
            slugi[typ] = _slug(english) if english else ("bez-typu" if typ is None else f"typ-{typ}")
        for slug, count in Counter(slugi.values()).items():
            if count > 1:
                for typ in [typ for typ, value in slugi.items() if value == slug]:
                    slugi[typ] = f"{slug}-{typ}"

        # część 1: sceny ułożone według zadań
        pisarz = None
        current_type = object()
        for sekcja in uklad.sekcje:
            main = sekcja.typ == uklad_scen.TYP_WATKU_GLOWNEGO
            if not any(
                numer in uklad.sceny_zadania or any((ix.zadania[numer].get("przerywniki") or {}).values())
                for numer in sekcja.zadania
            ):
                continue
            if main or sekcja.typ != current_type:
                if pisarz is not None:
                    seria(pisarz, "sceny według zadań")
                order += 1
                type_name = self._nazwa_typu(sekcja.typ)
                if main:
                    row = ix.grupy.get(sekcja.grupa) or {}
                    if row.get("kolejnosc"):
                        slug = f"rozdzial-{row['kolejnosc']}"
                    else:
                        slug = "bez-grupy" if sekcja.grupa is None else f"grupa-{sekcja.grupa}"
                    pisarz = Pisarz(katalog, f"{order:02d}_watek-glowny_{slug}", f"Wątek główny — {self._nazwa_grupy(sekcja.grupa)}", wstep)
                else:
                    pisarz = Pisarz(katalog, f"{order:02d}_{slugi[sekcja.typ]}", f"Zadania: {type_name}", wstep)
                current_type = sekcja.typ
            group_lines = [f"## Grupa zadań {sekcja.grupa} — {self._nazwa_grupy(sekcja.grupa)}"]
            group_lines += [f"- streszczenie z gry: {self.para(key)}" for key in streszczenia.get(sekcja.grupa, ())[:3]]
            pisarz.naglowek(2, group_lines)
            part = None
            for numer in sekcja.zadania:
                task = ix.zadania[numer]
                placed = uklad.sceny_zadania.get(numer, ())
                if not placed and not any((task.get("przerywniki") or {}).values()):
                    continue
                if main and task.get("pian") != part:
                    part = task.get("pian")
                    if part:
                        pisarz.naglowek(2, group_lines + [f"- część rozdziału (pian): {part}"])
                pisarz.naglowek(3, self._naglowek_zadania(numer))
                before = (self.numer_sceny, self.liczby["elementow"])
                self._przerywniki(pisarz, task, "przyjecie")
                for miejsce in placed:
                    self._scena(pisarz, miejsce.dialog, miejsce)
                self._przerywniki(pisarz, task, "zakonczenie")
                if self.numer_sceny > before[0] or self.liczby["elementow"] > before[1]:
                    self.spis_zadan.append(
                        {
                            "typ": sekcja.typ,
                            "grupa": sekcja.grupa,
                            "zadanie": numer,
                            "scen": self.numer_sceny - before[0],
                            "elementow": self.liczby["elementow"] - before[1],
                            "plik": pisarz.pliki[-1]["plik"] if pisarz.pliki else "",
                        }
                    )
        if pisarz is not None:
            seria(pisarz, "sceny według zadań")

        # część 2: dialogi bez powiązania z zadaniem, według projektu i numeru
        pisarz = Pisarz(katalog, "80_dialogi-wg-projektow", "Dialogi bez wpisu w tabelach zadań — według projektu i numeru", wstep)
        for project, numbers in uklad.projekty:
            pisarz.naglowek(2, [f"## Projekt {project or '(bez nazwy)'} — {len(numbers)} scen"])
            for numer in numbers:
                self._scena(pisarz, numer, uklad.miejsca[numer])
        seria(pisarz, "dialogi według projektu")

        # część 3: rozmowy tła, według miejsca
        pisarz = Pisarz(katalog, "90_rozmowy-tla", "Rozmowy tła: kwestie NPC rozmieszczonych w świecie — według miejsca", wstep)
        for (kind, value), numbers in uklad.tlo:
            title = f"## Miejsce: {self._miejsce(value)}" if kind == "miejsce" else f"## Reakcje NPC bez miejsca: {value}"
            pisarz.naglowek(2, [f"{title} — {len(numbers)} scen"])
            for numer in numbers:
                self._scena(pisarz, numer, uklad.miejsca[numer])
        seria(pisarz, "rozmowy tła według miejsca")

    # ----------------------------------------------------------- widoki

    def widoki(self, katalog: Path) -> None:
        ix = self.ix
        katalog.mkdir(parents=True, exist_ok=True)
        self._nowe_w_bloku = []
        limity: dict[int, int] = defaultdict(int)
        for text in ix.teksty.values():
            if text.w and text.en:
                limity[text.w[0]] = max(limity[text.w[0]], len(fmt.zakoduj(text.en)))
        self.limity = limity

        groups: dict[str, list[tuple]] = defaultdict(list)
        for key, text in ix.teksty.items():
            source = ix.zrodlo(text)
            if source is None:
                if key in self.sloty:
                    continue  # tekst tylko ze scen
                groups[BEZ_ZRODLA].append((("", 0, ""), (1, 0, text.zrodlo), 0, key))
                continue
            kind, _path, row = source
            table, _, row_key = row.rpartition("#")
            base = kind.removesuffix("__grey")
            if base in KOPIE_KWESTII and key in self.sloty:
                continue
            groups[kategoria(kind)].append(((base, kind != base, table or kind), _naturalny(row_key), text.w[0], key))

        for view, title in WIDOKI:
            rows = sorted(groups.get(view, ()))
            if self.tylko is not None:
                rows = [row for row in rows if row[3] in self.tylko]
            if self.tylko_z_en:
                rows = [row for row in rows if self._ma_en(row[3])]
            if not rows:
                continue
            wstep = [
                "Kolejność: tabela gry, wiersz, pole. Polski wpisujesz w jednej linii po `PL:`.",
                "`limit:` to długość najdłuższego tekstu angielskiego w tym samym polu gry (README, punkt 3).",
            ]
            pisarz = Pisarz(katalog, view, f"{title} — Where Winds Meet", wstep)
            totals = Counter((row[0][0], row[0][1]) for row in rows)
            current = None
            block: list[str] = []
            w_bloku: dict[str, int] = {}
            nr = opened = count = 0

            def flush() -> None:
                nonlocal block, opened, count, w_bloku
                if block:
                    self._zapisz_blok(pisarz, block, scen=0, elementow=count, do_wpisania=opened)
                block, opened, count, w_bloku = [], 0, 0, {}

            last_row = None
            for (base, grey, table), row_key, origin, key in rows:
                text = ix.teksty[key]
                heading = (base, grey)
                if heading != current:
                    flush()
                    current = heading
                    name = base + ("__grey" if grey else "")
                    lines = [f"## {name or 'bez tabeli'}" + (f" — {OPIS_TABELI[base]}" if base in OPIS_TABELI else "")]
                    if grey:
                        lines.append("- tabela `__grey`: druga wersja tej samej tabeli w danych gry; tu są teksty, których nie ma w wersji podstawowej")
                    lines.append(f"- elementów: {totals[heading]}")
                    pisarz.naglowek(2, lines)
                    last_row = None
                # jeden blok = jeden wiersz tabeli, żeby plik nie dzielił nazwy od opisu
                this_row = (table, row_key)
                if this_row != last_row or count >= 200:
                    flush()
                    last_row = this_row
                nr += 1
                count += 1
                if view == BEZ_ZRODLA:
                    label, extra = "Tekst bez źródła", []
                else:
                    path = ix.zrodla[origin][1]
                    row_name = row_key[2] if row_key[0] else str(row_key[1])
                    label = f"{table} · {path or '(wartość)'} · wiersz {row_name}"
                    extra = []
                    named = ix.nazwa_wiersza(text)
                    if named:
                        extra.append(f"dotyczy: {self.para(named)}")
                    if text.n > 1:
                        extra.append(f"użycia w grze: {text.n} identyfikatorów")
                    if limity.get(origin):
                        extra.append(f"limit: do {limity[origin]} znaków")
                if key in self.sloty:
                    plik, where = self.sloty[key]
                    block.append(f"{nr}. [{label}] {fmt.zakoduj(text.zrodlo)}")
                    block.append(f"{WCIECIE}(powtórzenie — tłumaczysz raz: {plik}, {where})")
                    self.liczby["elementow"] += 1
                    self.liczby["powtorzen"] += 1
                    continue
                part, is_open = self._element(nr, label, key, w_bloku, dodatkowe=extra, miejsce="element {nr}")
                block += part
                opened += is_open
            flush()
            files = pisarz.koniec()
            self.serie.append({"baza": view, "tytul": title, "opis": "widok", "pliki": files})


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def spakuj(katalog: Path, cel: Path) -> None:
    """ZIP o stałej zawartości: pliki w kolejności nazw, stała data, bez metadanych systemu."""
    with zipfile.ZipFile(cel, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(katalog.iterdir()):
            info = zipfile.ZipInfo(path.name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())


def kontrola(generator: "Generator", wyj: Path) -> dict:
    """Przeczytaj gotowe pliki tak, jak zrobi to import, i porównaj z wyciągiem.

    Każde miejsce `PL:` ma klucz znany wyciągowi i występuje dokładnie raz;
    w pakiecie pełnym miejsca pokrywają wszystkie niepuste teksty i wszystkie
    kwestie zależne od płci, w uzupełniającym — dokładnie zamówione klucze.
    """
    ix = generator.ix
    seen = Counter()
    for folder in ("sceny", "widoki"):
        for path in sorted((wyj / folder).glob("*.md")):
            for entry in fmt.czytaj_wpisy(path.read_text(encoding="utf-8")):
                seen[entry.klucz] += 1
    wanted = {
        key for key, text in ix.teksty.items()
        if text.zrodlo.strip() and (not generator.tylko_z_en or text.en is not None or text.z_en)
    } | {
        "@" + ident for ident in ix.warianty
        if not generator.tylko_z_en or generator._ma_en("@" + ident)
    }
    if generator.tylko is not None:
        wanted &= generator.tylko
    wanted = {slot for slot in wanted if not generator.magazyn.ma(slot)}
    return {
        "miejsc_pl": len(seen),
        "powtorzonych": sum(1 for count in seen.values() if count > 1),
        "nieznanych": len(set(seen) - wanted),
        "brakujacych": len(wanted - set(seen)),
        "zgodne": set(seen) == wanted and all(count == 1 for count in seen.values()),
    }


def zbuduj(ix, wyj: Path, *, wersja: str, data: str, magazyn=None, tylko_sloty: set[str] | None = None, tylko_z_en: bool = False, zip_: bool = True) -> dict:
    """Zbuduj pakiet w katalogu `wyj`; zwraca manifest pakietu."""
    try:
        from tools import opis_paczki
    except ImportError:  # pragma: no cover - uruchomienie jako skrypt
        import opis_paczki  # type: ignore[no-redef]

    wyj.mkdir(parents=True, exist_ok=True)
    for name in ("sceny", "widoki"):
        folder = wyj / name
        if folder.is_dir():
            for old in folder.glob("*"):
                old.unlink()
    for old in wyj.glob("paczka_dla_tlumacza_wwm_v*.zip"):
        old.unlink()
    generator = Generator(ix, magazyn, tylko_sloty, tylko_z_en=tylko_z_en)
    generator.sceny(wyj / "sceny")
    sceny_serie = list(generator.serie)
    generator.serie = []
    liczby_scen = Counter(generator.liczby)
    generator.widoki(wyj / "widoki")
    widoki_serie = list(generator.serie)
    liczby = Counter(generator.liczby)
    liczby_widokow = liczby - liczby_scen

    (wyj / "sceny" / "spis-scen.md").write_text(opis_paczki.spis_scen(generator, sceny_serie), encoding="utf-8", newline="\n")
    (wyj / "sceny" / "spis-misji.md").write_text(opis_paczki.spis_misji(generator), encoding="utf-8", newline="\n")
    with (wyj / "sceny" / "spis-scen.tsv").open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("scena\tdialog\tplik\tczesc\tzadanie\tsposob\telementow\n")
        for row in generator.spis_scen:
            handle.write("\t".join("" if value is None else str(value) for value in row) + "\n")
    manifest = {
        "format": "wwm-paczka-v1",
        "wersja": wersja,
        "data": data,
        "rodzaj": "pełny" if tylko_sloty is None else "uzupełniający",
        "tylko_z_en": tylko_z_en,
        "indeks": {
            "format": ix.manifest["format"],
            "opis": ix.manifest.get("wejscia", {}).get("opis", ""),
            "liczby": {name: ix.manifest["liczby"][name] for name in ("unikalnych_tekstow_w_zakresie", "scen", "kwestii")},
        },
        "liczby": dict(liczby),
        "liczby_sceny": dict(liczby_scen),
        "liczby_widoki": dict(liczby_widokow),
        "uklad": {
            "scen_w_zadaniach": sum(1 for row in generator.spis_scen if row[3] == "zadania"),
            "w_tym_wg_numeracji": sum(1 for row in generator.spis_scen if row[5] == "numeracja"),
            "scen_wg_projektow": sum(1 for row in generator.spis_scen if row[3] == "projekty"),
            "scen_tla": sum(1 for row in generator.spis_scen if row[3] == "tlo"),
            "przerwanych_cykli_lancucha_zadan": generator.uklad.cykle,
        },
        "sceny": sceny_serie,
        "widoki": widoki_serie,
    }
    (wyj / "README.md").write_text(opis_paczki.readme(generator, manifest), encoding="utf-8", newline="\n")
    manifest["kontrola"] = kontrola(generator, wyj)
    if zip_:
        for name in ("sceny", "widoki"):
            spakuj(wyj / name, wyj / f"{name}.zip")
        # jeden plik do przekazania tłumaczowi: README.md + sceny.zip + widoki.zip
        whole = wyj / f"paczka_dla_tlumacza_wwm_v{wersja}.zip"
        with zipfile.ZipFile(whole, "w", zipfile.ZIP_STORED) as archive:
            for name in ("README.md", "sceny.zip", "widoki.zip"):
                info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                info.external_attr = 0o644 << 16
                archive.writestr(info, (wyj / name).read_bytes())
        manifest["archiwa"] = {
            name: {"bajtow": (wyj / name).stat().st_size, "sha256": sha256(wyj / name)}
            for name in ("sceny.zip", "widoki.zip", whole.name)
        }
    (wyj / "paczka.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    return manifest


def main(argv=None) -> int:
    wypisz.utf8()
    parser = argparse.ArgumentParser(description="Pakiet dla tłumacza z wyciągu index/.")
    parser.add_argument("--indeks", default="index")
    parser.add_argument("--wyj", required=True)
    parser.add_argument("--wersja", default="1")
    parser.add_argument("--data", required=True, help="data pakietu do README, np. 2026-11-12")
    parser.add_argument("--tlumaczenie", help="katalog magazynu przekładów; gotowe przekłady nie dostają `PL:`")
    parser.add_argument("--tylko-sloty", help="plik z listą kluczy (jeden na linię): pakiet uzupełniający")
    parser.add_argument("--tylko-z-en", action="store_true", help="pomiń wpisy bez wersji angielskiej w grze (tylko chińskie)")
    parser.add_argument("--bez-zip", action="store_true")
    arguments = parser.parse_args(argv)
    try:
        ix = indeks_mod.wczytaj(arguments.indeks)
        magazyn = magazyn_mod.wczytaj(arguments.tlumaczenie) if arguments.tlumaczenie else None
        only = None
        if arguments.tylko_sloty:
            only = {line.strip() for line in Path(arguments.tylko_sloty).read_text(encoding="utf-8").splitlines() if line.strip()}
    except (indeks_mod.IndeksError, magazyn_mod.MagazynError, OSError) as error:
        print(json.dumps({"ok": False, "powod": str(error)}, ensure_ascii=False))
        return 1
    manifest = zbuduj(ix, Path(arguments.wyj), wersja=arguments.wersja, data=arguments.data, magazyn=magazyn, tylko_sloty=only, tylko_z_en=arguments.tylko_z_en, zip_=not arguments.bez_zip)
    ok = manifest["kontrola"]["zgodne"]
    print(json.dumps({"ok": ok, "rodzaj": manifest["rodzaj"], "tylko_z_en": manifest["tylko_z_en"], "liczby": manifest["liczby"], "uklad": manifest["uklad"], "kontrola": manifest["kontrola"], "archiwa": manifest.get("archiwa")}, ensure_ascii=False, indent=1))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
