#!/usr/bin/env python3
"""Indeks powiązań kontekstowych dla czytanek WWM (`index/` + tabele `widoki/`).

Moduł wydobywa bezpośrednie i tekstowe powiązania pomiędzy numerowanymi
epizodami/scenami czytanki a resztą korpusu gry w `index/`:
- bezpośrednie identyfikatory zadań i grup (`task_group_info`, `task_progress_light_info`,
  `task_progress_dark_info/group`, `task_progress_ending`, `main_storyline_activity_config`,
  `guider_task`, `region_game_config`, `opcje_npc`),
- pełną obsługę `ix.nazwa_wiersza(tekst)` (`w[2]`) odzyskującą nazwy wierszy ukryte
  przez kolizje między tabelami (`world_view_shili_data`, `xinfa`, `manual_items`,
  `book_config`, `npc_amity_relation_data`, `display_poem_text_config`, ...),
- zachowanie wszystkich elementów kolumn listowych `[]` (np. `text_shang[]`,
  `text_xia[]`, `finish_des[]`, `[].name`, `[].small_point_describe`),
- szybki automat Aho-Corasick w czystym Pythonie wykrywający wzmianki o postaciach,
  frakcjach, sektach, lokacjach, poematach miejsc, kartach ładowania, księgach,
  poszlakach, listach, przedmiotach, sztukach walki, bossach i wpisach UI.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
import re

try:
    from tools import indeks as indeks_mod
    from tools import kontekst_cutscen as kc
except ImportError:  # uruchomienie jako skrypt
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from tools import indeks as indeks_mod
    from tools import kontekst_cutscen as kc


_RE_CJK = re.compile(r"[\u4e00-\u9fff]")
_RE_TAG_KOLOR = re.compile(r"#(?:[0-9a-fA-F]{6}|[A-Z])")
_RE_ODNOSNIK = re.compile(r"<([^<>\n|]+)(?:\|[^|<>\n]*)+>")
_RE_SPACE_REGION = re.compile(r"^spaces\.s(\d+)\.region#(.+)$")

# Generyczne role i oznaczenia NPC, po których NIE przyciągamy listów/poszlak/ksiąg
GENERYCZNE_ROLE_ZH = frozenset(
    {
        "玩家", "主角", "我", "你", "众人", "路人", "村民", "百姓", "侠客", "侠士", "少侠",
        "游侠", "江湖人", "江湖客", "老人", "老者", "老翁", "老妇", "青年", "男子", "女子",
        "少女", "少年", "孩子", "小童", "孩童", "官兵", "士兵", "守卫", "侍卫", "卫兵",
        "山贼", "强盗", "匪徒", "土匪", "弟子", "掌柜", "小二", "店小二", "酒客", "客人",
        "商贩", "商人", "货郎", "药师", "大夫", "郎中", "船夫", "车夫", "渔夫", "樵夫",
        "天涯客", "匿名人", "神秘人", "黑衣人", "蒙面人", "画像", "妙妙喵", "无名", "未知",
        "师父", "众弟子", "行当管理员",
    }
)
GENERYCZNE_ROLE_LAT = frozenset(
    {
        "player", "main character", "me", "you xia", "villager", "passerby", "stranger",
        "traveler", "wayfarer", "wanderer", "jianghu wanderer", "swordsman", "disciple",
        "guard", "soldier", "bandit", "merchant", "shopkeeper", "waiter", "drinker",
        "guest", "elder", "old man", "old woman", "child", "boy", "girl", "youth",
        "mysterious person", "anonymous", "unknown", "portrait", "meow meow",
        "bohater", "bohaterka", "gracz", "wieśniak", "mieszkaniec", "przechodzień",
        "wędrowiec", "nieznajomy", "strażnik", "żołnierz", "bandyta", "kupiec",
        "karczmarz", "uczeń", "starzec", "dziecko",
    }
)

# Mapowanie prefiksów `task_progress_dark_info` / `dark_group` i `main_storyline_activity_config` na główne grupy (rozdziały)
DARK_GRUPA_DO_AKTU: dict[int, int] = {
    1: 1,   # 1xx -> Qinghe (grupa 1)
    2: 4,   # 2xx -> Kaifeng (grupa 4)
    3: 6,   # 3xx -> Hexi (grupa 6)
    4: 7,   # 4xx -> Hidden Mountain / Bringer of Embers (grupa 7)
}
AKTY_FABULARNE_DO_GRUPY: dict[str, int] = {
    "1": 1,
    "2": 4,
    "3": 6,
    "4": 7,
}
ZAKONCZENIA_DO_GRUPY: dict[str, int] = {
    "1": 1,
    "2": 4,
}


def _oczysc_do_dopasowania(text: str) -> str:
    if not text:
        return ""
    s = _RE_ODNOSNIK.sub(r"\1", text)
    s = _RE_TAG_KOLOR.sub("", s)
    return " ".join(s.split()).strip().strip("“”\"'‘’")


def _ma_cjk(text: str) -> bool:
    return bool(_RE_CJK.search(text))


def _naturalny(value: str):
    head, _, tail = value.partition("#")
    if tail.isdigit():
        return (0, int(tail), value)
    if head.lstrip("-").isdigit():
        return (0, int(head), value)
    return (1, 0, value)


class AutomatWzorcow:
    """Szybki automat Aho-Corasick w czystym Pythonie do masowego dopasowania fraz."""

    def __init__(self):
        self.goto: list[dict[str, int]] = [{}]
        self.fail: list[int] = [0]
        self.out: list[list[tuple]] = [[]]
        self._wzorce: dict[str, str] = {}  # pat -> pat_orig

    def dodaj(self, wzorzec: str, ladunek: tuple) -> None:
        if not wzorzec:
            return
        state = 0
        for ch in wzorzec:
            nxt = self.goto[state].get(ch)
            if nxt is None:
                nxt = len(self.goto)
                self.goto[state][ch] = nxt
                self.goto.append({})
                self.fail.append(0)
                self.out.append([])
            state = nxt
        self.out[state].append((wzorzec, ladunek))

    def buduj(self) -> None:
        q: deque[int] = deque()
        for nxt in self.goto[0].values():
            self.fail[nxt] = 0
            q.append(nxt)
        while q:
            r = q.popleft()
            for ch, s in self.goto[r].items():
                q.append(s)
                f = self.fail[r]
                while f and ch not in self.goto[f]:
                    f = self.fail[f]
                self.fail[s] = self.goto[f].get(ch, 0)
                if self.out[self.fail[s]]:
                    self.out[s].extend(self.out[self.fail[s]])

    def szukaj(self, tekst: str) -> list[tuple]:
        """Zwróć listę dopasowanych ładunków z weryfikacją granic słów dla wzorców nie-CJK."""
        if not tekst:
            return []
        tekst_l = tekst.lower()
        n = len(tekst_l)
        state = 0
        trafione: list[tuple] = []
        widziane: set[tuple] = set()
        for i, ch in enumerate(tekst_l):
            while state and ch not in self.goto[state]:
                state = self.fail[state]
            state = self.goto[state].get(ch, 0)
            if not self.out[state]:
                continue
            for pat, ladunek in self.out[state]:
                if ladunek in widziane:
                    continue
                if not _ma_cjk(pat):
                    start = i - len(pat) + 1
                    end = i + 1
                    if start > 0 and tekst_l[start - 1].isalnum():
                        continue
                    if end < n and tekst_l[end].isalnum():
                        continue
                widziane.add(ladunek)
                trafione.append(ladunek)
        return trafione


@dataclass
class BazaPowiazan:
    """Kompleksowa baza powiązań scen/epizodów ze wszystkimi tabelami `index/`."""

    ix: indeks_mod.Indeks
    tabele: dict[str, dict[str, dict[str, list[str]]]] = field(default_factory=dict)
    nazwy_wierszy: dict[str, dict[str, str]] = field(default_factory=dict)
    przestrzen_podobszary: dict[int, list[tuple[str, str]]] = field(default_factory=dict)
    podobszary_klucze: dict[str, str] = field(default_factory=dict)

    # Postacie i encyklopedia
    encyklopedia_po_kluczu: dict[str, dict] = field(default_factory=dict)
    encyklopedia_po_id: dict[int, dict] = field(default_factory=dict)
    encyklopedia_po_en: dict[str, dict] = field(default_factory=dict)
    glosy_postaci: dict[int, list[tuple[str | None, str]]] = field(default_factory=dict)  # pid -> [(title_kl, desc_kl)]

    # Zindeksowane nazwy postaci poza encyklopedią
    unikalne_postacie_zh: dict[str, str] = field(default_factory=dict)  # norm_zh -> klucz_nazwy
    amity_po_nazwie: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))
    boss_swiatowy_po_nazwie: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))
    boss_fuben_po_nazwie: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))
    mistrz_sekty_po_nazwie: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))
    wizytowka_cutsceny_po_nazwie: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))
    entity_attr_po_id: dict[str, dict[str, list[str]]] = field(default_factory=dict)

    # Indeks powiązań pośrednich i kalendarium frakcji
    historia_po_frakcji: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))
    automat: AutomatWzorcow = field(default_factory=AutomatWzorcow)
    szerokie_wzorce: set[tuple[str, str]] = field(default_factory=set)
    poszlaki_po_postaci: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))
    zapiski_po_postaci: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))
    listy_po_postaci: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))
    maile_po_postaci: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))
    ksiegi_po_postaci: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))

    # Opcje NPC przy dialogach
    opcje_npc_po_dialogu: dict[int, list[dict]] = field(default_factory=lambda: defaultdict(list))

    def pierwszy_klucz(self, tbl: str, rid: str, *cols: str, z_w2: bool = True) -> str | None:
        row = self.tabele.get(tbl, {}).get(rid, {})
        for col in cols:
            vals = row.get(col)
            if vals:
                return vals[0]
        if z_w2:
            return self.nazwy_wierszy.get(tbl, {}).get(rid)
        return None

    def wszystkie_klucze(self, tbl: str, rid: str, col: str) -> list[str]:
        return list(self.tabele.get(tbl, {}).get(rid, {}).get(col, ()))

    def wiersze(self, tbl: str) -> list[tuple[str, dict[str, list[str]]]]:
        return sorted(self.tabele.get(tbl, {}).items(), key=lambda x: _naturalny(x[0]))


CHCIANE_TABELE = {
    # Postacie, relacje, bossowie i sekty
    "world_view_person_info",
    "world_view_person_event",
    "world_view_person_voice",
    "cutscene_person_info_config",
    "npc_amity_relation_data",
    "single_world_boss_data",
    "fuben_boss_tips",
    "fuben_info",
    "school_chuancheng_npc_data",
    "school_sect_chuancheng_data",
    "school",
    "xinhu_menpai_list",
    "entity_attr",
    # Świat, historia, grupy i postęp fabularny
    "world_view_region_info",
    "world_view_shili_data",
    "world_view_history_info",
    "world_view_default_kaoju_config",
    "task_group_info",
    "task_progress_light_info",
    "task_progress_dark_info",
    "task_progress_dark_group",
    "task_progress_ending",
    "task_prelude_custom_config",
    "task_fail_desc",
    "tasks_ending_data",
    "main_storyline_activity_config",
    "expedition_story_info",
    "expedition_history",
    # Lokacje i poezja / opisy świata
    "display_poem_text_config",
    "loading_base_config",
    "region_story_act_data",
    "normal_story_act_data",
    "task_space_replay",
    # Kompendium, zapiski, księgi, poszlaki, listy
    "manual_items",
    "region_collect_jianwen_data",
    "book_config",
    "ever_know_content_data",
    "ever_know_clue_data",
    "tasks_envelop_data",
    "emails_data",
    # Przedmioty, stroje, tytuły i sztuki walki
    "equip_items",
    "stuff_items",
    "fashion_items",
    "title",
    "kongfu",
    "xinfa",
    "jianghu_skills",
    "qishu_combat_data",
    # UI i zadania pomocnicze
    "guider_task",
    "guider_tujian_data",
    "region_game_config",
    "ac_raw",
}


def zbuduj_baze(ix: indeks_mod.Indeks) -> BazaPowiazan:
    """Zbuduj w jednym przebiegu wszystkie słowniki i automat powiązań z `index/`."""
    baza = BazaPowiazan(ix=ix)
    tabele: dict[str, dict[str, dict[str, list[str]]]] = {name: {} for name in CHCIANE_TABELE}
    nazwy_wierszy: dict[str, dict[str, str]] = defaultdict(dict)
    spaces_regions: dict[int, list[tuple[str, str]]] = defaultdict(list)

    for kl, text in ix.teksty.items():
        zr = ix.zrodlo(text)
        if not zr:
            continue
        tbl, col, row_id = zr
        if tbl in tabele:
            row_dict = tabele[tbl].setdefault(row_id, {})
            col_list = row_dict.setdefault(col, [])
            if kl not in col_list:
                col_list.append(kl)
            nk = ix.nazwa_wiersza(text)
            if nk and row_id not in nazwy_wierszy[tbl]:
                nazwy_wierszy[tbl][row_id] = nk
        elif tbl == "spaces.*.region" and col == "area_name":
            m_sp = _RE_SPACE_REGION.match(row_id)
            if m_sp:
                sp_id = int(m_sp.group(1))
                sp_rid = m_sp.group(2)
                spaces_regions[sp_id].append((sp_rid, kl))
                baza.podobszary_klucze[f"{sp_id}:{sp_rid}"] = kl

    baza.tabele = tabele
    baza.nazwy_wierszy = nazwy_wierszy
    baza.przestrzen_podobszary = spaces_regions
    baza.entity_attr_po_id = tabele.get("entity_attr", {})

    # 1. Encyklopedia postaci + mapowanie głosów world_view_person_voice
    baza.encyklopedia_po_id = dict(ix.encyklopedia)
    for row in ix.encyklopedia.values():
        for field_name in ("nazwa", "inna_nazwa"):
            if row.get(field_name):
                baza.encyklopedia_po_kluczu.setdefault(row[field_name], row)
        if row.get("nazwa"):
            en_name = (ix.en(row["nazwa"]) or "").strip()
            if en_name:
                baza.encyklopedia_po_en.setdefault(en_name, row)

    for rid, cols in sorted(tabele.get("world_view_person_voice", {}).items(), key=lambda x: _naturalny(x[0])):
        pid = kc.wvpv_pid(rid, ix.encyklopedia)
        if pid is not None and pid in ix.encyklopedia:
            t_kl = cols.get("title", [None])[0] or nazwy_wierszy.get("world_view_person_voice", {}).get(rid)
            for d_kl in cols.get("description", ()):
                baza.glosy_postaci.setdefault(pid, []).append((t_kl, d_kl))

    # 2. Opcje NPC po dialogu
    for row in ix.opcje_npc.values():
        for dno in row.get("dialogi", ()):
            baza.opcje_npc_po_dialogu[dno].append(row)

    # 3. Indeksy pomocnicze dla wyspecjalizowanych tabel postaciowych
    def _indeksuj_po_nazwie(tbl: str, *cols: str) -> dict[str, list[str]]:
        out: dict[str, list[str]] = defaultdict(list)
        for rid, _rcols in baza.wiersze(tbl):
            nk = baza.pierwszy_klucz(tbl, rid, *cols)
            if not nk:
                continue
            for txt_k in (ix.zh(nk), ix.en(nk)):
                norm = _oczysc_do_dopasowania(txt_k).lower()
                if norm:
                    out[norm].append(rid)
        return out

    baza.amity_po_nazwie = _indeksuj_po_nazwie("npc_amity_relation_data", "amity_target_name")
    baza.boss_swiatowy_po_nazwie = _indeksuj_po_nazwie("single_world_boss_data", "boss_name")
    baza.boss_fuben_po_nazwie = _indeksuj_po_nazwie("fuben_boss_tips", "boss_name")
    baza.mistrz_sekty_po_nazwie = _indeksuj_po_nazwie("school_chuancheng_npc_data", "generation_name")
    baza.wizytowka_cutsceny_po_nazwie = _indeksuj_po_nazwie("cutscene_person_info_config", "name", "name_en")

    # 4. Zbiór unikalnych imion własnych postaci do bezpiecznego łączenia z poszlakami/listami/księgami
    licznik_nazw_bytow: dict[str, int] = defaultdict(int)
    for prow in ix.postacie.values():
        if prow.get("n"):
            z = _oczysc_do_dopasowania(ix.zh(prow["n"]))
            if z:
                licznik_nazw_bytow[z] += 1

    imiona_wlasne: dict[str, str] = {}  # norm_lower -> klucz_nazwy

    def _rejestruj_imie(name_kl: str | None, *, zaufane: bool = False) -> None:
        if not name_kl:
            return
        z = _oczysc_do_dopasowania(ix.zh(name_kl))
        if not z:
            return
        if z in GENERYCZNE_ROLE_ZH or z.lower() in GENERYCZNE_ROLE_LAT:
            return
        if not zaufane and licznik_nazw_bytow.get(z, 0) > 12:
            return
        min_l = 2 if _ma_cjk(z) else 4
        if len(z) < min_l:
            return
        imiona_wlasne.setdefault(z.lower(), name_kl)
        baza.unikalne_postacie_zh.setdefault(z.lower(), name_kl)

    for row in ix.encyklopedia.values():
        _rejestruj_imie(row.get("nazwa"), zaufane=True)
    for tbl, col in (
        ("single_world_boss_data", "boss_name"),
        ("school_chuancheng_npc_data", "generation_name"),
        ("npc_amity_relation_data", "amity_target_name"),
        ("cutscene_person_info_config", "name"),
    ):
        for rid, _ in baza.wiersze(tbl):
            _rejestruj_imie(baza.pierwszy_klucz(tbl, rid, col), zaufane=True)
    for sc in ix.sceny.values():
        for o in sc.get("o", ()):
            if len(o) > 3 and o[3]:
                _rejestruj_imie(o[3], zaufane=False)

    # 5. Budowa automatu Aho-Corasick ze wszystkich tabel kontekstowych
    automat = baza.automat

    def _dodaj_wzorzec(text_raw: str | None, payload: tuple, *, min_cjk: int = 2, min_lat: int = 4, szeroka: bool = False) -> None:
        if not text_raw:
            return
        pat = _oczysc_do_dopasowania(text_raw)
        if not pat:
            return
        cjk = _ma_cjk(pat)
        if cjk and len(pat) < min_cjk:
            return
        if not cjk and len(pat) < min_lat:
            return
        if not cjk and pat.lower() in GENERYCZNE_ROLE_LAT:
            return
        if cjk and pat in GENERYCZNE_ROLE_ZH:
            return
        automat.dodaj(pat.lower(), payload)
        if szeroka:
            baza.szerokie_wzorce.add(payload)

    # Postacie z encyklopedii oraz dodatkowe źródła postaciowe
    for pid, row in sorted(ix.encyklopedia.items()):
        _dodaj_wzorzec(ix.zh(row.get("nazwa")), ("encyklopedia", str(pid)), min_cjk=2, min_lat=4)
        _dodaj_wzorzec(ix.zh(row.get("inna_nazwa")), ("encyklopedia", str(pid)), min_cjk=2, min_lat=4)

    # Tabela konfiguracyjna (tabela, kolumny_nazwy, min_cjk, min_lat, czy_szeroka)
    reguly_tabel: list[tuple[str, tuple[str, ...], int, int, bool]] = [
        ("world_view_shili_data", ("name",), 2, 4, False),
        ("school_sect_chuancheng_data", ("school_name",), 2, 4, False),
        ("school", ("name",), 2, 4, False),
        ("xinhu_menpai_list", ("school_name",), 2, 4, False),
        ("display_poem_text_config", ("name",), 2, 4, False),
        ("single_world_boss_data", ("boss_name",), 2, 4, False),
        ("fuben_boss_tips", ("boss_name",), 2, 4, False),
        ("school_chuancheng_npc_data", ("generation_name",), 2, 4, False),
        ("npc_amity_relation_data", ("amity_target_name",), 2, 4, False),
        ("cutscene_person_info_config", ("name", "name_en"), 2, 4, False),
        ("world_view_history_info", ("name",), 3, 5, False),
        ("world_view_default_kaoju_config", ("name",), 3, 5, False),
        ("expedition_story_info", ("story_title",), 3, 5, False),
        ("fuben_info", ("instance_name",), 3, 5, False),
        ("region_story_act_data", ("name",), 3, 5, False),
        ("normal_story_act_data", ("name",), 3, 5, False),
        ("task_space_replay", ("space_name",), 3, 5, False),
        ("ever_know_content_data", ("title",), 3, 5, False),
        ("kongfu", ("name",), 3, 5, False),
        ("xinfa", ("name",), 3, 5, False),
        ("jianghu_skills", ("jianghu_skill_name",), 3, 5, False),
        ("qishu_combat_data", ("name",), 3, 5, False),
        ("equip_items", ("name",), 3, 5, False),
        ("book_config", ("name",), 3, 5, False),
        ("loading_base_config", ("title",), 3, 5, True),
        ("manual_items", ("bowu_name",), 3, 5, True),
        ("region_collect_jianwen_data", ("jianwen_title",), 3, 5, True),
        ("stuff_items", ("name",), 4, 6, True),
        ("fashion_items", ("name",), 4, 6, True),
        ("title", ("name",), 4, 6, True),
        ("ac_raw", ("achievement_name",), 4, 6, True),
        ("guider_tujian_data", ("manual_name", "talk_title[]"), 4, 6, True),
    ]

    for tbl, cols, min_cjk, min_lat, szeroka in reguly_tabel:
        for rid, _ in baza.wiersze(tbl):
            nk = baza.pierwszy_klucz(tbl, rid, *cols)
            if not nk:
                continue
            txt = ix.zh(nk)
            if not _ma_cjk(txt) and tbl == "stuff_items" and len(txt.split()) < 2:
                continue
            _dodaj_wzorzec(txt, (tbl, rid), min_cjk=min_cjk, min_lat=min_lat, szeroka=szeroka)

    # Podobszary spaces.*.region (zawsze wymagają zgodności `space_id` ze sceną lub wyraźnej nazwy!)
    for space_id, items in spaces_regions.items():
        for rid, area_kl in items:
            _dodaj_wzorzec(ix.zh(area_kl), ("space_region", f"{space_id}:{rid}"), min_cjk=3, min_lat=5, szeroka=False)

    automat.buduj()

    # 6. Drugi automat wyłącznie dla jednoznacznych imion własnych — indeksacja poszlak, zapisków, listów, maili i ksiąg
    ac_imion = AutomatWzorcow()
    for norm_imie in imiona_wlasne:
        ac_imion.dodaj(norm_imie, ("imie", norm_imie))
    ac_imion.buduj()

    def _indeksuj_po_imionach(tbl: str, cols: tuple[str, ...], cel: dict[str, list[str]]) -> None:
        for rid, rcols in baza.wiersze(tbl):
            fragmenty = []
            if tbl in ("region_collect_jianwen_data", "book_config"):
                nk = nazwy_wierszy.get(tbl, {}).get(rid)
                if nk:
                    fragmenty.append(ix.zh(nk))
            for col in cols:
                for kl in rcols.get(col, ()):
                    z = ix.zh(kl)
                    if z:
                        fragmenty.append(z)
            if not fragmenty:
                continue
            calosc = "\n".join(fragmenty)
            widziane_imiona: set[str] = set()
            for _, norm_imie in ac_imion.szukaj(calosc):
                if norm_imie not in widziane_imiona:
                    widziane_imiona.add(norm_imie)
                    cel[norm_imie].append(rid)

    _indeksuj_po_imionach("ever_know_clue_data", ("record", "clue"), baza.poszlaki_po_postaci)
    _indeksuj_po_imionach("region_collect_jianwen_data", ("jianwen_from", "jianwen_text", "jianwen_title"), baza.zapiski_po_postaci)
    _indeksuj_po_imionach("tasks_envelop_data", ("from", "to", "text"), baza.listy_po_postaci)
    _indeksuj_po_imionach("emails_data", ("sender_title", "mail_title", "end"), baza.maile_po_postaci)
    _indeksuj_po_imionach("book_config", ("author", "name", "page_1"), baza.ksiegi_po_postaci)

    # 7. Kalendarium historyczne pogrupowane według ID frakcji (`world_view_shili_data`)
    for hrid, _ in baza.wiersze("world_view_history_info"):
        if hrid.isdigit():
            shili_id = str(int(hrid) // 100)
            baza.historia_po_frakcji[shili_id].append(hrid)

    return baza


def skanuj_wzmianki_w_scenach(
    baza: BazaPowiazan,
    teksty_scen: dict[str, tuple[str, set[int]]],
) -> dict[str, dict[str, list[str]]]:
    """Przeskanuj wszystkie sceny w jednym przebiegu Aho-Corasick z filtracją pospolitych fałszywych trafień.

    `teksty_scen`: `scene_uid -> (tekst_zh_sceny, zbior_space_id)`.
    Zwraca `scene_uid -> {tabela: [rid, ...]}` z zachowaniem kolejności wystąpienia.
    """
    surowe: dict[str, list[tuple[str, str]]] = {}
    czestosc: dict[tuple[str, str], int] = defaultdict(int)
    for uid, (txt, sp_ids) in teksty_scen.items():
        if not txt:
            surowe[uid] = []
            continue
        rozszerzone_sp = set(sp_ids)
        # Mapy powtórkowe / fabularne (701, 702, 711..713, 801) odpowiadają otwartym światom 501 / 502.
        if sp_ids & {701, 711, 712, 713, 801, 17022, 17023, 35005}:
            rozszerzone_sp.add(501)
        if sp_ids & {702}:
            rozszerzone_sp.add(502)

        lista: list[tuple[str, str]] = []
        seen: set[tuple[str, str]] = set()
        for tbl, rid in baza.automat.szukaj(txt):
            if tbl == "space_region":
                sp_str, _, _ = rid.partition(":")
                if sp_str.isdigit() and rozszerzone_sp and int(sp_str) not in rozszerzone_sp:
                    continue
            para = (tbl, rid)
            if para not in seen:
                seen.add(para)
                lista.append(para)
                czestosc[para] += 1
        surowe[uid] = lista

    n_scen = len(teksty_scen)
    prog_szumu = max(80, n_scen // 10) if n_scen >= 300 else n_scen + 1
    wynik: dict[str, dict[str, list[str]]] = {}
    for uid, lista in surowe.items():
        per_tbl: dict[str, list[str]] = defaultdict(list)
        for para in lista:
            if para in baza.szerokie_wzorce and czestosc[para] > prog_szumu:
                continue
            tbl, rid = para
            per_tbl[tbl].append(rid)
        wynik[uid] = dict(per_tbl)
    return wynik
