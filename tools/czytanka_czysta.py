#!/usr/bin/env python3
"""Czytanka WWM do czytania — trzy pliki w układzie ustalonym z właścicielem.

1. `01_sceny_i_cutsceny.md` — sceny **i** cutsceny razem, chronologicznie:
   filmy otwierające, prolog w kolejności sprawdzonej z transkryptem, potem krainy
   w kolejności odwiedzania (sceny w porządku grafu następstw), na końcu pozostałe pule
   napisów przerywników.
2. `02_kontekst_scen_i_cutscen.md` — kontekst do tych samych jednostek i w tej
   samej kolejności: postacie, encyklopedia, frakcje, miejsca, przedmioty, sztuki
   walki — wszystko, co pada w danej scenie. Hasło ma pełną kartę przy pierwszym
   wystąpieniu.
3. `03_reszta.md` — cała reszta przekładów, której nie ma w 01 ani w 02,
   pogrupowana według rodzaju danych.

Format kwestii w 01: jedna linia `**Mówca:** tekst` (bez punktora), bez czasów,
kluczy i tabel; kwestia bez mówcy to goły tekst.

Cutsceny: kwestie w kolejności wierszy puli `text_msg` (a nie w kolejności z
chronologii), bo tylko numer wiersza jest porządkiem gry. Gdy w plikach leżą dwa
zestawy napisów tej samej cutsceny, pierwszy jest treścią, a pozostałe stoją pod
nagłówkiem `### Inny wariant napisów tej cutsceny (wiersze …)`; powtórzone kwestie
wypadają. Streszczenie sceny stoi zawsze na początku cutsceny, a po nim pusta
linia przerwy przed kwestiami dialogu.

Użycie:
    python3 tools/czytanka_czysta.py --wyj out/czytanka --zip dist/WWM_Czytanka.zip
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import textwrap
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools import indeks as indeks_mod  # noqa: E402
from tools import chronologia as chronologia_mod  # noqa: E402
from tools import kolejnosc_gry, kolejnosc_zadan, powiazania_czytanek, pinyin_slownik  # noqa: E402
from tools import tlumaczenie as tlumaczenie_mod  # noqa: E402

DLUGOSC_KARTY = 600        # ile znaków opisu pokazać w kontekście (reszta w pliku 03)
PROG_WARIANTU = 48
PROG_NAGLOWKA_REDAKCJI = 3   # ile kwestii przed pierwszym bliźniakiem należy jeszcze do dialogu sceny
BEZ_PRZEKLADU = "\\*"   # kwestia bez przekładu: gwiazdka i tekst z gry
BEZ_MAPY = ":sceny-bez-mapy:"
_KOLOR = re.compile(r"#[0-9a-fA-F]{6}|#[A-Z]")
_ODNOSNIK = re.compile(r"<([^<>|]{1,80})(\|[^<>]*)?>")
_SPACJE = re.compile(r"\s+")

# W danych gracza ta sama postać bywa nazwana różnie; dla czytelnika to zawsze „Ty”.
GRACZ = {nazwa.lower(): "Youxia" for nazwa in (
    "你", "我", "玩家", "主角", "player", "Player", "PLAYER", "You", "主角（玩家）",
    "main_player", "main player", "mainplayer", "protagonist", "主角玩家",
)}
TECHNICZNE = {"Entity轨道组", "轨道组", "entity", "Entity", "旁白占位"}

KATEGORIE = (
    (("kongfu", "xinfa", "jianghu_skill", "qishu", "buff", "skill", "talent"),
     "Sztuki walki i umiejętności"),
    (("equip", "stuff", "fashion", "item", "bag", "weapon", "armor", "title"),
     "Przedmioty, stroje i tytuły"),
    (("encyclopedia", "manual", "ever_know", "book", "clue", "letter", "email",
      "jianwen", "envelop", "poem", "kaoju"),
     "Encyklopedia, księgi i poszlaki"),
    (("task", "guider", "quest", "storyline", "expedition"),
     "Zadania i wątki"),
    (("fuben", "boss", "monster", "enemy", "combat"),
     "Walka i przeciwnicy"),
    (("world_view", "school", "menpai", "shili", "region", "space", "place",
      "area", "loading", "expedition_history"),
     "Świat, sekty i miejsca"),
    (("person", "npc", "amity", "voice", "entity_attr"),
     "Postacie i relacje"),
    (("ui", "setting", "tips", "guide", "sys", "option", "hud", "button"),
     "Interfejs i komunikaty"),
)

_NAZWA = re.compile(r"name|title|bowu|imie", re.I)
# Kolumny z definicją hasła. Świadomie nie ma tu `content`, `story_*`, `page_*`,
# `talk_content`, `tips` — to opowieści i streszczenia scen, nie opisy.
_OPIS = re.compile(r"describe|description|intro|^des$|job_info|npc_desc", re.I)
# Kolejność: najpierw zwięzła definicja, potem dłuższe warianty.
_OPIS_KOLEJNOSC = (
    "describe_str", "describe", "brief_describe_str", "introduction",
    "introduction_long", "description", "jianghu_brief_description", "job_info",
    "npc_desc", "des", "introduction_location", "introduction_short",
    "extra_describe_1", "generation_description", "sidepage_boss_desc",
)
# Tabele, w których „opis” to w rzeczywistości opowieść, list, mail albo kwestia.
_NARRACYJNE = {
    "ac_raw", "book_config", "cutscene_person_info_config", "display_poem_text_config",
    "emails_data", "ever_know_clue_data", "ever_know_content_data",
    "expedition_history", "expedition_story_info", "guider_task", "guider_tujian_data",
    "loading_base_config", "npc_amity_relation_data", "region_collect_jianwen_data",
    "tasks_envelop_data", "world_view_person_event", "world_view_person_voice",
    "task_progress_light_info", "task_progress_dark_info", "task_progress_ending",
    "task_progress_dark_group", "task_prelude_custom_config", "task_group_info",
}


def _czysty(tekst: str) -> str:
    """Zdejmij kody kolorów i odnośniki rich-text, złóż białe znaki.

    W danych gry łamanie akapitu bywa zapisane dosłownie jako `\\n`, a kwestia
    ma być jedną linią — zamieniamy to na spację.
    """
    tekst = (tekst or "").replace("\\n", " ").replace("\\r", " ").replace("\\t", " ")
    tekst = _ODNOSNIK.sub(lambda m: m.group(1), tekst or "")
    tekst = _KOLOR.sub("", tekst)
    return _SPACJE.sub(" ", tekst).strip()


def _kategoria(tabela: str) -> str:
    nazwa = tabela.lower()
    for slowa, etykieta in KATEGORIE:
        if any(slowo in nazwa for slowo in slowa):
            return etykieta
    return "Pozostałe teksty"


def _magazyn(katalog: Path, index: Path | str = "index") -> dict[str, str]:
    """Przekłady po kluczu tekstu, razem z wariantami płci bohatera.

    Kwestie zależne od płci gracza mają w grze osobne identyfikatory (`@id`),
    a w magazynie osobny plik `pl_warianty.jsonl`. Bez `index/warianty.jsonl`
    nie da się ich przypisać do klucza tekstu — i wtedy czytanka pokazywała
    angielski tekst mimo gotowego przekładu (np. „This symbol…” w scenie
    4700001). Czytamy wariant bohatera; gdy go nie ma, pierwszy dostępny.
    """
    magazyn = tlumaczenie_mod.wczytaj(katalog, warianty=Path(index) / "warianty.jsonl")
    return {klucz: _czysty(tekst) for klucz, tekst in magazyn.po_kluczu_pelny().items()
            if tekst and tekst.strip()}


# W danych gry gracz bywa zapisany różnie, także z literówkami (`mian_player`).
_GRACZ_LAT = re.compile(r"^(?:main|mian)?[_ ]?player[_ ]?\d*[：:]?$", re.I)

_GLOSARIUSZ: dict[str, str] | None = None


def _glosariusz(index: str = "index") -> dict[str, str]:
    """Ręczny słownik chińskich etykiet mówców → angielskie imiona (`index/nazwy_mowcow.json`).

    Gra nie ma nazw obcych dla mówców zapisanych tylko rolą („青年女人”), więc
    uzupełniamy je w repo; każdy dopisany wpis działa od razu po przebudowaniu.
    """
    global _GLOSARIUSZ
    if _GLOSARIUSZ is None:
        plik = Path(index) / "nazwy_mowcow.json"
        _GLOSARIUSZ = json.loads(plik.read_text(encoding="utf-8")) if plik.exists() else {}
    return _GLOSARIUSZ


_NAZWY_ENCJI: tuple | None = None
_NAZWY_ZH: tuple | None = None
_NAZWY_EN: tuple | None = None


def _przyciete(imie: str) -> str:
    """Imię bez wielokropka na końcu („Yingying…” to w danych ozdobnik)."""
    imie = (imie or "").strip()
    for ogon in ("…", "..."):
        if imie.endswith(ogon):
            imie = imie[: -len(ogon)].strip()
    return imie


def _dobre_imie(nazwa: str) -> bool:
    """Czy rozwiązana nazwa wygląda na imię, a nie na zdanie z magazynu."""
    nazwa = nazwa.strip()
    if not nazwa or len(nazwa) > 30:
        return False
    if ". " in nazwa or "。" in nazwa or "!" in nazwa or "?" in nazwa:
        return False
    return True


def _imie_do_etykiety(nazwa: str) -> str:
    """Nazwa mówcy do wyświetlenia: bez ogona interpunkcji, z wielkiej litery."""
    nazwa = _przyciete(nazwa).strip(" .。,，:：;；")
    return nazwa[:1].upper() + nazwa[1:] if nazwa else nazwa


_ZH = re.compile(r"[\u3400-\u9fff]")


def _etykieta_hasla(ix, nazwa: str) -> str:
    """Nazwa hasła do pokazania w kontekście (albo pustka, gdy hasło nic nie wnosi).

    Z danych wpadają śmieci: gracz zapisany jako `玩家`/`0`, techniczne
    „Entity轨道组”, chińskie role („中年男人”). Gracz nie dostaje karty,
    techniczne śmieci też nie, a chińskie role idą przez słownik nazw mówców.
    """
    nazwa = (nazwa or "").strip()
    if not nazwa or _GRACZ_LAT.match(nazwa) or nazwa.lower() in GRACZ:
        return ""
    if nazwa in TECHNICZNE or nazwa.lower() in {t.lower() for t in TECHNICZNE}:
        return ""
    if not _ZH.search(nazwa) and not re.search(r"[A-Za-z]", nazwa):
        return ""            # „0”, myślniki, cyfry
    if _ZH.search(nazwa):
        en = _nazwy_en(ix).get(nazwa) or _glosariusz().get(nazwa) or ""
        if en:
            nazwa = en
    if not _dobre_imie(nazwa):
        return ""
    return _imie_do_etykiety(nazwa)


def _nazwy_en(ix) -> dict[str, str]:
    """Chińska nazwa → angielska (zlatynizowana), gdy gra ją ma."""
    global _NAZWY_EN
    if _NAZWY_EN is None or _NAZWY_EN[0] is not ix:
        mapa = {t.zrodlo: t.en for k, t in ix.teksty.items() if t.zrodlo and t.en}
        _NAZWY_EN = (ix, mapa)
    return _NAZWY_EN[1]


def _nazwy_encji(ix) -> dict[int, str]:
    """Numer bytu → angielska nazwa z tabliczki (`spaces.*.entity.N.name`).

    Część obsady scen ma w danych tylko chińską etykietę roboczą, ale byt bywa
    opisany nazwą w tabeli przestrzeni — wtedy bierzemy ją zamiast transliteracji.
    """
    global _NAZWY_ENCJI
    if _NAZWY_ENCJI is None or _NAZWY_ENCJI[0] is not ix:
        mapa: dict[int, str] = {}
        for tekst in ix.teksty.values():
            zrodlo = ix.zrodlo(tekst)
            if not zrodlo or not zrodlo[0].startswith("spaces.") or zrodlo[1] != "name":
                continue
            trafienie = re.search(r"#(\d+)$", zrodlo[2] or "")
            if trafienie and tekst.en:
                mapa[int(trafienie[1])] = tekst.en
        _NAZWY_ENCJI = (ix, mapa)
    return _NAZWY_ENCJI[1]


def _nazwy_zh(ix) -> dict[str, str]:
    """Chińskie imię → klucz nazwy, żeby mówca nie zostawał po chińsku, gdy gra ma nazwę obcą."""
    global _NAZWY_ZH
    if _NAZWY_ZH is None or _NAZWY_ZH[0] is not ix:
        mapa = {t.zrodlo: k for k, t in ix.teksty.items() if t.zrodlo}
        _NAZWY_ZH = (ix, mapa)
    return _NAZWY_ZH[1]


def _nazwa_klucza(ix, klucz: str | None, pl: dict[str, str]) -> str:
    if not klucz:
        return ""
    if klucz in pl:
        return pl[klucz]
    tekst = ix.teksty.get(klucz)
    return _czysty(tekst.en or tekst.zrodlo) if tekst is not None else ""


def _cokolwiek_lacinskie(nazwa: str) -> str:
    """Imię z danych: łacinka zostaje, chińska nazwa bez przekładu idzie w transliterację."""
    nazwa = _przyciete(nazwa)
    return pinyin_slownik.romanizuj(nazwa) if re.search(r"[\u3400-\u9fff]", nazwa) else nazwa


_ROLE_ZH = ("士兵", "侍卫", "守卫", "护卫", "军士", "甲士", "官兵", "公差", "衙役", "捕快",
            "路人", "村民", "百姓", "众人", "众弟子", "黑衣人", "看客", "商贩", "伙计", "小厮",
            "侍从", "宫人", "车夫", "黄门", "百姓们", "围观")
_ROLE_EN = frozenset({"soldier", "soldiers", "guard", "guards", "officer", "enforcer", "attendant",
                      "bystander", "civilian", "crowd", "vendor", "passerby", "patrol", "servant",
                      "maid", "peasant", "villager", "sentry", "trooper", "guardman", "onlooker",
                      "spectator", "escort", "porter", "beggar", "clerk", "official", "inspector"})
_ROLE_PL = ("żołnierz", "strażnik", "oficer", "wartownik", "przechodzień", "wieśniak", "sługa",
            "urzędnik", "straż", "tłum", "gwardzista", "konwojent")


# Same okrzyki: w danych gry stoją przy nich nazwy cudzych postaci (gracz nie ma nazwy),
# więc podpis mówcy jest tu częściej mylny niż pomocny.
_OKRZYKI_ZH = frozenset({"哼", "嗯", "啊", "哎", "诶", "哦", "噢", "呀", "哈", "嘿", "喂", "咦",
                        "呃", "唉", "唔", "嘶", "嗯嗯", "哈哈", "嘿嘿", "呵呵", "哎呀", "哎哟",
                        "哎呦", "啊呀", "哇", "嘁", "呸", "嘻", "嚯", "嗷", "呜", "嗷呜"})


def _okrzyk(tekst: str) -> bool:
    """Czy kwestia to sam okrzyk (bez treści, która wskazywałaby mówcę)."""
    czysty = re.sub(r"[^\w]", "", tekst or "")
    return bool(czysty) and czysty in _OKRZYKI_ZH


def _bez_roli(nazwa: str) -> str:
    """Nazwa mówcy bez etykiet samych ról („审查士兵”, „Inspection Soldier”).

    Kwestie anonimowych przechodniów mają w danych gry nazwę roli, nie osoby. Taka
    etykieta nie identyfikuje mówcy (właściciel: „Inspection Soldier” przed „Stój!” to
    nie ten, kto mówi), więc jej nie pokazujemy — lepiej żadnego podpisu niż mylny.
    """
    tekst = (nazwa or "").strip()
    if not tekst:
        return ""
    if any(token in tekst for token in _ROLE_ZH):
        return ""
    slowa = {slowo.strip(".,'’()[]").lower() for slowo in tekst.split()}
    if slowa & _ROLE_EN:
        return ""
    maly = tekst.lower()
    if any(token in maly for token in _ROLE_PL):
        return ""
    return nazwa


def _mowca(osoba: list, ix, pl: dict[str, str]) -> str:
    """Imię mówcy: polskie, a gdy brak przekładu — angielskie z danych gry."""
    nazwa_zh = _czysty(str(osoba[0] or ""))
    if nazwa_zh.lower() in GRACZ:
        return GRACZ[nazwa_zh.lower()]
    if _GRACZ_LAT.match(nazwa_zh):
        return "Youxia"
    if nazwa_zh in TECHNICZNE:
        return ""
    osoba_id = osoba[2] if len(osoba) > 2 else None
    wiersz = ix.postacie.get(osoba_id) if isinstance(osoba_id, int) else None
    if wiersz and wiersz.get("n"):
        nazwa = _nazwa_klucza(ix, wiersz["n"], pl)
        if nazwa:
            return _cokolwiek_lacinskie(nazwa)
    klucz = osoba[3] if len(osoba) > 3 else None
    tekst = ix.teksty.get(klucz) if klucz else None
    if tekst is not None and tekst.zrodlo == nazwa_zh:
        nazwa = _nazwa_klucza(ix, klucz, pl)
        if nazwa:
            return _przyciete(nazwa)
    # imię podane tylko po chińsku: poszukaj klucza nazwy o tej samej treści
    nazwa_zh = _przyciete(nazwa_zh)
    klucz_zh = _nazwy_zh(ix).get(nazwa_zh)
    if klucz_zh:
        nazwa = _nazwa_klucza(ix, klucz_zh, pl)
        if nazwa and nazwa != nazwa_zh and _dobre_imie(nazwa):
            return _imie_do_etykiety(nazwa)
    if isinstance(osoba_id, int):
        en = _nazwy_encji(ix).get(osoba_id, "")
        if en and _dobre_imie(en):
            return _imie_do_etykiety(en)
    if nazwa_zh.isdigit():
        return ""                    # samo id postaci to nie mówca
    if any("\u3400" <= z <= "\u9fff" for z in nazwa_zh):
        en = _nazwy_en(ix).get(nazwa_zh, "") or _glosariusz().get(nazwa_zh, "")
        if en and _dobre_imie(en):
            return _imie_do_etykiety(en)
    etykieta = _glosariusz().get(nazwa_zh) or nazwa_zh
    if etykieta.isdigit():
        return ""
    return pinyin_slownik.romanizuj(etykieta)


def _mowca_w_scenie(scena: dict, indeks_mowcy, ix, pl) -> str:
    obsada = scena.get("o") or []
    if indeks_mowcy is None or not (0 <= indeks_mowcy < len(obsada)):
        if len(obsada) != 1:
            return ""
        indeks_mowcy = 0
    return _bez_roli(_mowca(obsada[indeks_mowcy], ix, pl))


@dataclass
class Jednostka:
    """Scena albo cutscena: jednostka czytanki i kontekstu."""

    rodzaj: str                      # scena | cutscena | film | prolog
    etykieta: str                    # np. „Scena 10094”, „Film 2 — …”
    sekcja: str                      # np. „# 燕南”
    linie: list[tuple[str, str]] = field(default_factory=list)   # (mówca, klucz)
    przestrzenie: set[int] = field(default_factory=set)
    osoby: list[tuple[str, str]] = field(default_factory=list)    # (id postaci, imię z obsady)
    z_brakami: bool = False                                      # pokazuj kwestie bez przekładu
    podtytuly: dict[int, str] = field(default_factory=dict)      # numer linii → nagłówek nad nią
    zasloniete: tuple[str, ...] = ()                            # kwestie powtórzone w wariancie
    streszczenie: int = 0                                     # ile linii na początku to streszczenie


def _wczytaj_porzadek(index: str) -> dict[str, list[dict]]:
    porzadek: dict[str, list[dict]] = {}
    for wiersz in kolejnosc_gry.wczytaj(Path(index)):
        if wiersz.get("k"):
            porzadek.setdefault(wiersz["k"], []).append(wiersz)
    return porzadek


TYTULY_FILMOW = {1: "Pieśń o lampionach", 2: "Utwór pingtan „Szpila feniksa”",
                 3: "Bitwa na Moście Zhongdu"}


def _mowca_klucza(klucz: str, ix, pl, porzadek, mowcy_napisow=None) -> tuple[str, set[int]]:
    """Mówca i przestrzenie dla pojedynczego klucza tekstu z chronologii.

    Mówcę podajemy **tylko wtedy, gdy naprawdę wynika z danych**: z kroku dialogu
    w scenie (`o`), gdzie gra przypisuje kwestię do osoby. Napisy puli `text_msg`
    (cutsceny, prolog) nie mają pola mówcy — dawniej braliśmy go z podpowiedzi
    `mowca_en` dopisanej przy innym tekście o tej samej treści i to podszywało
    cudze nazwiska (np. „Inspection Soldier” przed „Stój!”, „Handlebar Hu” w Prologu 4).
    Podpowiedzi nie są identyfikacją mówcy, więc ich nie używamy (`mowcy_napisow`
    zostaje w sygnaturze dla zgodności wywołań).
    """
    przestrzenie: set[int] = set()
    for wiersz in porzadek.get(klucz) or []:
        if wiersz["z"] == "dialog" and wiersz["d"]:
            scena = ix.sceny.get(int(wiersz["d"])) or {}
            przestrzenie.update(int(m) for m in scena.get("m") or [] if str(m).isdigit())
            for element in scena.get("e") or []:
                if element[0] == "k" and element[2] == klucz:
                    return _mowca_w_scenie(scena, element[1] if len(element) > 1 else None,
                                           ix, pl), przestrzenie
    return "", przestrzenie


def _nazwy_krain(ix, pl, porzadki: list[dict]) -> dict[str, str]:
    """Chińska nazwa krainy → polska, jeśli przekład jest w magazynie."""
    zh_klucz = {t.zrodlo: k for k, t in ix.teksty.items() if t.zrodlo}
    nazwy: dict[str, str] = {}
    for porzadek in porzadki:
        for nazwa in porzadek.get("nazwy") or []:
            klucz = zh_klucz.get(nazwa)
            if klucz and klucz in pl and pl[klucz]:
                nazwy.setdefault(porzadek["kraina"], pl[klucz])
    return nazwy


def _wiersze_napisow(ix, porzadek: dict[str, list[dict]]) -> dict[str, int]:
    """Klucz napisu → numer wiersza w puli `text_msg`, czyli kolejność gry.

    Numer wiersza jest jedynym porządkiem, jaki gra podaje dla napisów przerywnika
    (`kn` w chronologii miesza napisy przypisane wprost z tabeli i bloki puli, więc
    kolejność w nim bywa losowa). Bierzemy go z kontekstu cutscen, a gdy tam nie ma —
    z osi `kolejnosc_*` (wiersze typu `napis*` mają w polu `i` numer wiersza puli).
    """
    wiersze: dict[str, int] = {}
    for wpis in ix.cutsceny_kontekst.get("napis") or []:
        klucz, numer = wpis.get("k"), wpis.get("wiersz")
        if klucz and isinstance(numer, int):
            wiersze.setdefault(klucz, numer)
    for klucz, wystapienia in porzadek.items():
        if klucz in wiersze:
            continue
        for wpis in wystapienia:
            if wpis.get("z") == "napis" and isinstance(wpis.get("i"), int):
                wiersze[klucz] = wpis["i"]
                break
    return wiersze


def _bez_interpunkcji(tekst: str) -> str:
    """Sygnatura kwestii do wyłapania powtórzeń: bez interpunkcji i wielkości liter."""
    return " ".join(re.sub(r"[^\w\s]", " ", tekst.lower()).split())


def _sygnatury(klucze: list[str], pl: dict[str, str]) -> dict[str, str]:
    """Sygnatura treści kwestii (bez interpunkcji i wielkości liter)."""
    return {k: _bez_interpunkcji(pl[k]) for k in klucze if pl.get(k)}


def _podziel_na_bloki(klucze: list[str], wiersze: dict[str, int]) -> list[list[str]]:
    """Bloki napisów cutsceny: ciągłe fragmenty puli `text_msg`.

    Ten sam przerywnik leży w puli kilka razy (starsza i nowsza wersja napisów), a obok
    niego potrafią stać wiersze z innej treści (np. recytacja wiersza w 30161). Bloki
    rozcinamy tam, gdzie numer wiersza odskakuje o więcej niż `PROG_WARIANTU`.
    """
    bloki: list[list[str]] = []
    for klucz in klucze:
        numer = wiersze.get(klucz)
        poprzedni = wiersze.get(bloki[-1][-1]) if bloki else None
        if bloki and (numer is None or poprzedni is None or numer - poprzedni <= PROG_WARIANTU):
            bloki[-1].append(klucz)
        else:
            bloki.append([klucz])
    return bloki


def _najwyzszy(blok: list[str], wiersze: dict[str, int]) -> int:
    numery = [wiersze[k] for k in blok if k in wiersze]
    return max(numery) if numery else -1


def _dialog_sceny(blok: list[str], bloki: list[list[str]], wiersze: dict[str, int],
                  sygnatury: dict[str, str]) -> tuple[list[str], list[str]]:
    """(dialog sceny, treść wsunięta przed dialog) w bloku najnowszej redakcji.

    Grana wersja napisów powtarza zdania starszej wersji tej samej sceny, więc kwestia
    z bliźniakiem w innym bloku jest dialogiem sceny. Najnowsza redakcja zaczyna się
    jednak czasem o kilka kwestii wcześniej niż pierwszy bliźniak (w 30161 to dwa
    okrzyki „Wodzu! Wodzu!”, „Wodzu, obudź się!”) — dlatego dialog zaczynamy
    `PROG_NAGLOWKA_REDAKCJI` wierszy przed pierwszym bliźniakiem. Wszystko przed tym
    progiem to inna treść wsunięta w ten sam ciąg wierszy (recytacja wiersza w 30161)
    i idzie osobno, po dialogu.
    """
    inne: set[str] = set()
    for inny in bloki:
        if inny is blok:
            continue
        for klucz in inny:
            syg = sygnatury.get(klucz)
            if syg:
                inne.add(syg)
    blizniaki = [wiersze[k] for k in blok
                 if k in wiersze and sygnatury.get(k) in inne]
    if not blizniaki:
        return blok, []
    prog = min(blizniaki) - PROG_NAGLOWKA_REDAKCJI
    dialog = [k for k in blok if (wiersze.get(k) or 0) >= prog]
    obce = [k for k in blok if (wiersze.get(k) or 0) < prog]
    return dialog, obce


def _napisy_cutsceny(wiersz: dict, wiersze: dict[str, int], pl: dict[str, str],
                     audio: dict[int, str] | None = None
                     ) -> tuple[list[str], dict[int, str], list[str]]:
    """Napisy cutsceny w kolejności gry, z osobnymi wariantami i streszczeniem.

    Kolejność bierzemy z numerów wierszy puli `text_msg` — to jedyna oś porządku, jaką
    gra podaje dla napisów przerywnika (`kn` w chronologii miesza napisy przypisane
    wprost z tabeli gry z blokami puli). Ten sam przerywnik leży w puli kilka razy:
    starsza i nowsza wersja napisów (np. 590153–590179 i 591148–591169 w cutscenie
    30161). Grany jest **najnowszy** blok (najwyższe numery wierszy, patrz
    `_podziel_na_bloki`), a w nim najpierw dialog sceny, potem treść bez bliźniaka
    (`_kwestie_sceny`). Starsze wersje schodzą pod nagłówek, żeby nic nie ginęło,
    ale czytelnik nie dostał dwóch scen splątanych w jedną.

    Streszczenie sceny (`k`) stoi **na początku**, zaraz pod nagłówkiem cutsceny.
    """
    napisy = [k for k in wiersz.get("kn") or [] if k]
    pozycja: dict[str, int] = {}
    for numer, klucz in enumerate(napisy):
        pozycja.setdefault(klucz, numer)

    def do_sortowania(klucz: str) -> tuple:
        numer = wiersze.get(klucz)
        return (0, numer, pozycja[klucz]) if numer is not None else (1, 0, pozycja[klucz])

    bloki = _podziel_na_bloki(sorted(pozycja, key=do_sortowania), wiersze)
    if len(bloki) > 1:
        kolejnosc = sorted(range(len(bloki)), key=lambda i: _najwyzszy(bloki[i], wiersze),
                           reverse=True)
        bloki = [bloki[i] for i in kolejnosc]
        sygnatury = _sygnatury([k for blok in bloki for k in blok], pl)
        dialog, obce = _dialog_sceny(bloki[0], bloki, wiersze, sygnatury)
        bloki = [dialog] + ([obce] if obce else []) + bloki[1:]

    klucze: list[str] = []
    podtytuly: dict[int, str] = {}
    powtorzone: list[str] = []
    widziane: set[str] = set()

    streszczenie = [k for k in wiersz.get("k") or [] if k]
    if streszczenie:
        podtytuly[0] = "Streszczenie sceny"
        klucze.extend(streszczenie)
        widziane.update(_bez_interpunkcji(pl[k]) for k in streszczenie if pl.get(k))

    for numer_bloku, blok in enumerate(bloki):
        naglowek = ""
        if numer_bloku:
            numery = [wiersze[k] for k in blok if k in wiersze]
            opis = (f"wiersze {min(numery)}–{max(numery)}" if numery and min(numery) != max(numery)
                    else f"wiersz {numery[0]}" if numery else "wiersze bez numeru")
            naglowek = f"Inny wariant napisów tej cutsceny ({opis})"
        czeka_na_naglowek = bool(naglowek)
        for klucz in blok:
            tekst = pl.get(klucz)
            if tekst:
                sygnatura = _bez_interpunkcji(tekst)
                if sygnatura and sygnatura in widziane:
                    powtorzone.append(klucz)
                    continue        # ta sama kwestia drugi raz (wariant napisów)
                widziane.add(sygnatura)
            if czeka_na_naglowek:
                podtytuly[len(klucze)] = naglowek
                czeka_na_naglowek = False
            klucze.append(klucz)
    return klucze, podtytuly, powtorzone


def _jednostki_z_chronologii(ix, pl, porzadek, chronologia: list[dict],
                             krainy: list[dict] | None = None) -> list[Jednostka]:
    """Chronologia jest zapisana w `index/chronologia.jsonl`; tu tylko czytamy kolejność."""
    nazwy_pl = _nazwy_krain(ix, pl, krainy or [])

    def sekcja(nazwa: str) -> str:
        polska = nazwy_pl.get(nazwa)
        return f"# {nazwa} — {polska}" if polska and polska != nazwa else f"# {nazwa}"
    mowcy_napisow = {w["wiersz"]: w.get("mowca_en")
                     for w in ix.cutsceny_kontekst.get("napis", []) if w.get("wiersz")}
    audio_napisow = {w["wiersz"]: w["audio"]
                     for w in ix.cutsceny_kontekst.get("napis", []) if w.get("audio")}
    wiersze_napisow = _wiersze_napisow(ix, porzadek)
    klucze_wierszy = {w["wiersz"]: w["k"] for w in ix.cutsceny_kontekst.get("napis", [])
                      if w.get("wiersz") and w.get("k")}

    def klucze_filmu(numer: int) -> list[str]:
        wiersze = [w for klucz, wystapienia in porzadek.items() for w in wystapienia
                   if w["z"] == "film" and w["d"] is not None and int(w["d"]) == numer]
        wiersze.sort(key=lambda w: (w["t"] or 0, w["i"] or 0))
        return [w["k"] for w in wiersze]

    jednostki: list[Jednostka] = []
    licznik_prologu = 0
    for wiersz in chronologia:
        rodzaj = wiersz["t"]
        if rodzaj == "film":
            numer = int(wiersz["n"])
            jednostki.append(Jednostka(
                "film", f"Pieśń {numer} — {TYTULY_FILMOW.get(numer, f'Pieśń {numer}')}",
                "# Pieśni", [("", k) for k in klucze_filmu(numer) if k]))
        elif rodzaj == "prolog":
            linie, przestrzenie = [], set()
            for klucz in wiersz.get("k") or []:
                if linie and linie[-1][1] == klucz:
                    continue
                mowca, gdzie = _mowca_klucza(klucz, ix, pl, porzadek, mowcy_napisow)
                przestrzenie |= gdzie
                if _okrzyk(ix.zh(klucz)):
                    mowca = ""
                linie.append((mowca, klucz))
            licznik_prologu += 1
            osoby = [("", m) for m in dict.fromkeys(m for m, _k in linie if m)]
            jednostki.append(Jednostka("prolog", f"Prolog {licznik_prologu}",
                                       "# Prolog", linie, przestrzenie, osoby, z_brakami=True))
        elif rodzaj == "scena":
            numer = int(wiersz["n"])
            scena = ix.sceny.get(numer) or {}
            linie = []
            for element in scena.get("e") or []:
                if element[0] != "k":
                    continue
                if linie and linie[-1][1] == element[2]:
                    continue
                mowca = _mowca_w_scenie(scena, element[1] if len(element) > 1 else None, ix, pl)
                if _okrzyk(ix.zh(element[2])):
                    mowca = ""      # samo „Ech!”, „Ha!”, „Mhm.” — obsada podaje tu zwykle kogoś innego
                linie.append((mowca, element[2]))
            osoby: list[tuple[str, str]] = []
            widziani: set[tuple[str, str]] = set()
            for osoba in scena.get("o") or []:
                if not osoba:
                    continue
                pid = str(osoba[2]) if len(osoba) > 2 and isinstance(osoba[2], int) else ""
                imie = _czysty(str(osoba[0] or ""))
                if not pid and not imie:
                    continue
                if (pid, imie) not in widziani:
                    widziani.add((pid, imie))
                    osoby.append((pid, imie))
            jednostki.append(Jednostka(
                "scena", f"Scena {numer}", sekcja(wiersz["s"]), linie,
                {int(m) for m in scena.get("m") or [] if str(m).isdigit()}, osoby))
        elif rodzaj == "cutscena":
            numer = int(wiersz["n"])
            klucze, podtytuly, powtorzone = _napisy_cutsceny(wiersz, wiersze_napisow, pl,
                                                            audio_napisow)
            linie = [(_mowca_klucza(klucz, ix, pl, porzadek, mowcy_napisow)[0], klucz)
                     for klucz in klucze]
            osoby = [("", m) for m in dict.fromkeys(m for m, _k in linie if m)]
            liczba_streszczenia = sum(1 for k in wiersz.get("k") or [] if k)
            jednostki.append(Jednostka("cutscena", f"Cutscena {numer}", sekcja(wiersz["s"]),
                                       linie, osoby=osoby, podtytuly=podtytuly,
                                       zasloniete=tuple(powtorzone),
                                       streszczenie=liczba_streszczenia))
        elif rodzaj == "napisy":
            linie = []
            for klucz in wiersz.get("k") or []:
                if linie and linie[-1][1] == klucz:
                    continue
                mowca, gdzie = _mowca_klucza(klucz, ix, pl, porzadek, mowcy_napisow)
                linie.append((mowca, klucz))
            osoby = [("", m) for m in dict.fromkeys(m for m, _k in linie if m)]
            jednostki.append(Jednostka(
                "napisy", wiersz.get("e") or "Napisy przerywnika",
                "# Napisy przerywników — kolejność z pliku gry (bez numeru cutsceny)",
                linie, osoby=osoby))
    return jednostki


def _z_gry(ix, klucz: str) -> str:
    """Tekst kwestii bez przekładu: angielski, a gdy brak — źródłowy chiński."""
    tekst = ix.teksty.get(klucz)
    if tekst is None:
        return ""
    return _czysty(tekst.en or tekst.zrodlo or "")


# Karty zbiorów: w jednym wierszu gry leży tytuł i pełny tekst. Wcześniej
# trafiał do 03 tylko tekst (jako „nazwa — opis” z przypadku), a karty bez
# przekładu nie trafiały wcale — dlatego w czytance brakowało pamiątek.
_ZBIORY = (
    ("region_collect_jianwen_data", "jianwen_title", "jianwen_text",
     "Zbiory i pamiątki — zasłyszane historie"),
    ("card_collecting_boss", "card_name", "card_content",
     "Zbiory i pamiątki — karty przeciwników"),
)


def _zbiory(ix, pl: dict[str, str], uzyte: set[str], statystyka: dict) -> list[str]:
    """Karty zbiorów: tytuł + pełny tekst, także bez przekładu (z gwiazdką)."""
    out: list[str] = []
    kolumny = dict(enumerate(ix.zrodla))
    for tabela, kol_tytul, kol_tekst, naglowek in _ZBIORY:
        indeksy = {i for i, wpis in kolumny.items() if wpis[0] == tabela}
        if not indeksy:
            continue
        wiersze: dict[str, dict[str, str]] = {}
        for klucz, tekst in ix.teksty.items():
            if tekst.w and tekst.w[0] in indeksy:
                wiersze.setdefault(str(tekst.w[1]), {})[kolumny[tekst.w[0]][1]] = klucz
        karty: list[str] = []
        widziane: set[str] = set()
        for numer in sorted(wiersze):
            pola = wiersze[numer]
            klucz_tytulu, klucz_tekstu = pola.get(kol_tytul), pola.get(kol_tekst)
            if not klucz_tytulu or not klucz_tekstu or klucz_tekstu in uzyte:
                continue
            tytul = pl.get(klucz_tytulu) or ("\\*" + _z_gry(ix, klucz_tytulu))
            opis = pl.get(klucz_tekstu) or ("\\*" + _z_gry(ix, klucz_tekstu))
            if not tytul.strip(GWIAZDKA + " ") or not opis.strip(GWIAZDKA + " "):
                continue
            karta = f"**{tytul}:** {opis}"
            if karta in widziane:
                continue
            widziane.add(karta)
            karty.append(karta)
            statystyka["zbiory"] = statystyka.get("zbiory", 0) + 1
        if karty:
            out += [f"# {naglowek}", ""] + karty + [""]
    return out


# gwiazdka przy tekście bez przekładu: dwa backslashe i gwiazdka,
# tak jak w pozostałych sekcjach 03
GWIAZDKA = "\\*"

_PAMIATKI_PLIK = "pamiatki.jsonl"
# rola -> (tabela, kolumna): przestrzeń świadków z `index/zrodla.json`
_PAMIATKI_PRZESTRZENIE = (
    ("nazwa", "equip_items", "name"),
    ("wlasciciel", "curio_owner", "owner_name"),
    ("pamiec", "text_msg", "content"),
)


def _przestrzen(ix, tabela: str, kolumna: str) -> int | None:
    """Numer przestrzeni świadków dla (tabela, kolumna) albo None."""
    for numer, wpis in enumerate(ix.zrodla):
        if wpis[0] == tabela and wpis[1] == kolumna:
            return numer
    return None


def _wlasiciel(pl, wpis: dict, klucz: str | None) -> str:
    """Kto jest właścicielem pamiątki: przekład, a bez niego sama nazwa z ikony.

    Ikona właściciela (`head_npc_zhuxiannpc_jiangwulang`) to identyfikator
    z danych gry, nie wymyślony tekst — bierzemy z niej ostatni człon.
    """
    if klucz:
        przeklad = pl.get(klucz)
        if przeklad:
            return przeklad.strip()
    ikona = str(wpis.get("wlasciciel_ikona") or "")
    if not ikona:
        return ""
    czlon = ikona.rsplit("/", 1)[-1].split(".", 1)[0]
    czlon = czlon.rsplit("_", 1)[-1]
    return "" if czlon.isdigit() else czlon


def _blok_tekstu(tekst: str, przeklad: bool) -> list[str]:
    """Historia przedmiotu: przekład bez zmian, źródło z gwiazdką przy każdej linii."""
    linie = [linia.rstrip() for linia in textwrap.dedent(tekst).splitlines()]
    if przeklad:
        return linie
    return [(GWIAZDKA + linia) if linia.strip() else "" for linia in linie]


_NAZWY_PLIK = "nazwy.jsonl"


def _wczytaj_nazwy(katalog: str | Path) -> dict[str, dict]:
    """`index/nazwy.jsonl`: identyfikator tekstu -> klucz przekładu i treść gry."""
    plik = Path(katalog) / _NAZWY_PLIK
    if not plik.is_file():
        return {}
    mapa: dict[str, dict] = {}
    for linia in plik.read_text(encoding="utf-8").splitlines():
        if not linia.strip():
            continue
        wpis = json.loads(linia)
        if wpis.get("k"):
            mapa[str(wpis.get("id"))] = wpis
    return mapa


def _tekst_nazwy(ix, pl, mapa: dict[str, str], ident,
                 nazwy: dict[str, dict]) -> tuple[str, str | None]:
    """(tekst nazwy, klucz przekładu) z mapy identyfikatorów, a bez niej ze świadków.

    Mapy języka (`index/nazwy.jsonl`) znają treść **każdego** identyfikatora
    z danych gry, świadkowie `index/teksty_*.jsonl` tylko te, które trafiły do
    wyciągu — dlatego mapa idzie pierwsza.
    """
    if ident is None:
        return "", None
    wpis = nazwy.get(str(ident))
    if wpis:
        klucz = str(wpis["k"])
        przeklad = pl.get(klucz)
        if przeklad:
            return przeklad.strip(), klucz
        return GWIAZDKA + _czysty(str(wpis.get("en") or wpis.get("zh") or "")), klucz
    klucz = mapa.get(str(ident))
    if not klucz:
        return "", None
    return (pl.get(klucz) or ("\\\\*" + _z_gry(ix, klucz))).strip(), klucz


def _pamiatki(ix, pl: dict[str, str], uzyte: set[str], statystyka: dict,
              katalog: str | Path) -> list[str]:
    """Pamiątki (przedmioty z historią): właściciel, nazwa i cała historia.

    Wiersze liczbowe bierze `index/pamiatki.jsonl` (`tools/pamiatki_z_bazy.py`),
    teksty — jak wszędzie — świadkowie `index/teksty_*.jsonl`. Pamiątka bez
    nazwy przedmiotu nie wchodzi (nie mamy jak jej zatytułować), a licznik
    `pamiatki_bez_nazwy` mówi, ile ich było.
    """
    plik = Path(katalog) / _PAMIATKI_PLIK
    if not plik.is_file():
        return []
    nazwy = _wczytaj_nazwy(katalog)
    mapy: dict[str, dict[str, str]] = {}
    for rola, tabela, kolumna in _PAMIATKI_PRZESTRZENIE:
        numer = _przestrzen(ix, tabela, kolumna)
        mapa: dict[str, str] = {}
        if numer is not None:
            for klucz, tekst in ix.teksty.items():
                if tekst.w and tekst.w[0] == numer:
                    mapa.setdefault(str(tekst.w[1]), klucz)
        mapy[rola] = mapa
    ukryte = 0
    karty: list[str] = []
    widziane: set[str] = set()
    for wiersz in plik.read_text(encoding="utf-8").splitlines():
        if not wiersz.strip():
            continue
        wpis = json.loads(wiersz)
        klucz_historii = mapy["pamiec"].get(str(wpis.get("pamiec") or ""))
        if not klucz_historii or klucz_historii in uzyte:
            continue
        nazwa, klucz_nazwy = _tekst_nazwy(
            ix, pl, mapy["nazwa"],
            wpis.get("nazwa_id") or wpis.get("przedmiot"), nazwy)
        if not nazwa.strip(GWIAZDKA + " "):
            ukryte += 1
            continue
        historia = pl.get(klucz_historii)
        zrodlo = historia or _z_gry(ix, klucz_historii)
        if not zrodlo.strip():
            continue
        wlasciciel, _ = _tekst_nazwy(
            ix, pl, mapy["wlasciciel"],
            wpis.get("wlasciciel_id") or wpis.get("wlasciciel"), nazwy)
        wlasciciel = wlasciciel.strip(GWIAZDKA + " ") or _wlasiciel(pl, wpis, None)
        tytul = f"{wlasciciel} — {nazwa}" if wlasciciel else nazwa
        if tytul in widziane:
            continue
        widziane.add(tytul)
        uzyte.add(klucz_historii)
        karty.append(f"**{tytul}**")
        karty.append("")
        karty.extend(_blok_tekstu(zrodlo, bool(historia)))
        karty.append("")
        statystyka["pamiatki"] = statystyka.get("pamiatki", 0) + 1
    statystyka["pamiatki_bez_nazwy"] = statystyka.get("pamiatki_bez_nazwy", 0) + ukryte
    if not karty:
        return []
    return ["# Pamiątki — przedmioty z historią", ""] + karty


_POI_PLIK = "poi.jsonl"


def _poi(ix, pl: dict[str, str], uzyte: set[str], statystyka: dict,
         katalog: str | Path) -> list[str]:
    """Punkty na mapie (POI): nazwa, a przy dowodzie także numer sceny.

    Numer sceny wchodzi tylko wtedy, gdy gra zapisała go w wierszu POI
    (`play_dialog_no` / `result_play_dialog` — patrz `tools/poi_z_bazy.py`).
    Sama nazwa pliku scenariusza (`interact_storyline`) nie jest powiązaniem,
    więc nie robi z POI „sceny N”.
    """
    plik = Path(katalog) / _POI_PLIK
    if not plik.is_file():
        return []
    nazwy = _wczytaj_nazwy(katalog)
    numer = _przestrzen(ix, "active_interact_way", "button_name")
    mapa: dict[str, str] = {}
    if numer is not None:
        for klucz, tekst in ix.teksty.items():
            if tekst.w and tekst.w[0] == numer:
                mapa.setdefault(str(tekst.w[1]), klucz)
    wpisy: list[str] = []
    widziane: set[str] = set()
    bez_nazwy = 0
    z_dialogiem = 0
    for wiersz in plik.read_text(encoding="utf-8").splitlines():
        if not wiersz.strip():
            continue
        wpis = json.loads(wiersz)
        nazwa, klucz = _tekst_nazwy(ix, pl, mapa,
                                    wpis.get("nazwa") or wpis.get("id"), nazwy)
        if not nazwa.strip(GWIAZDKA + " "):
            bez_nazwy += 1
            continue
        if klucz in uzyte:
            continue
        if nazwa in widziane:
            continue
        widziane.add(nazwa)
        dialog = wpis.get("dialog")
        if dialog:
            z_dialogiem += 1
            wpisy.append(f"**{nazwa}** — scena {dialog}")
        else:
            wpisy.append(f"**{nazwa}**")
        statystyka["poi"] = statystyka.get("poi", 0) + 1
    statystyka["poi_z_dialogiem"] = z_dialogiem
    statystyka["poi_bez_nazwy"] = bez_nazwy
    if not wpisy:
        return []
    return ["# Punkty na mapie (POI)", ""] + wpisy + [""]


def _linia(mowca: str, tekst: str) -> str:
    """Kwestia w jednej linii, bez punktora.

    Punktor mylił: część kwestii to dalszy ciąg zdania łamanego na dwa wiersze,
    a w cutscenach i tak nie ma mówcy. Zostaje sam mówca i tekst.
    """
    return f"**{mowca}:** {tekst}" if mowca else tekst


def _plik_scen(jednostki: list[Jednostka], pl: dict[str, str], zakres: str,
               statystyka: dict, ix=None) -> tuple[list[str], set[str], set[str]]:
    out: list[str] = []
    uzyte: set[str] = set()
    zrobione: set[str] = set()
    ostatnia_sekcja = None
    for jednostka in jednostki:
        linie = []
        widziane_linie: set[str] = set()
        uzyte.update(jednostka.zasloniete)
        podtytuly = dict(jednostka.podtytuly)
        # Przerwa po streszczeniu: pusty wiersz, zanim zaczną się kwestie dialogu.
        granica_streszczenia = jednostka.streszczenie
        przerwa_wstawiona = False
        streszczenie_naglowek = False
        streszczenie_tresc = 0
        for numer_linii, (mowca, klucz) in enumerate(jednostka.linie):
            uzyte.add(klucz)
            tekst = pl.get(klucz)
            if tekst is None:
                if zakres == "przetlumaczone":
                    statystyka["pominiete"] += 1
                    continue
                zrodlo_tekst = _z_gry(ix, klucz)
                if not zrodlo_tekst:
                    statystyka["pominiete"] += 1
                    continue
                tekst = f"\\*{zrodlo_tekst}"
                statystyka["bez_przekladu"] += 1
            else:
                statystyka["linii"] += 1
            gotowa = _linia(mowca, tekst)
            if gotowa in widziane_linie:
                continue          # ta sama kwestia drugi raz w tej samej jednostce
            widziane_linie.add(gotowa)
            if granica_streszczenia and numer_linii < granica_streszczenia:
                streszczenie_tresc += 1
            if (granica_streszczenia and not przerwa_wstawiona
                    and numer_linii >= granica_streszczenia):
                if streszczenie_naglowek and streszczenie_tresc:
                    linie.append("")     # przerwa: streszczenie → kwestie
                przerwa_wstawiona = True
            for indeks in sorted(i for i in podtytuly if i <= numer_linii):
                naglowek = f"### {podtytuly.pop(indeks)}"
                linie.append(naglowek)
                if naglowek == "### Streszczenie sceny":
                    streszczenie_naglowek = True
            linie.append(gotowa)
        if not linie:
            continue
        statystyka["jednostek"] += 1
        if jednostka.sekcja != ostatnia_sekcja:
            out += [jednostka.sekcja, ""]
            ostatnia_sekcja = jednostka.sekcja
        out.append(f"## {jednostka.etykieta}")
        out.extend(linie)
        out.append("")
        zrobione.add(jednostka.etykieta)
    return out, uzyte, zrobione


def _tekst(ix, pl: dict[str, str], klucz: str | None) -> tuple[str, bool]:
    """(tekst, czy_polski) — polski z magazynu, a gdy brak, angielski z danych gry."""
    if not klucz:
        return "", True
    if klucz in pl:
        return pl[klucz], True
    tekst = ix.teksty.get(klucz)
    if tekst is None:
        return "", True
    return _czysty(tekst.en or tekst.zrodlo or ""), False


def _tozsamosc(ix, pl, wpis: dict) -> tuple[str, bool]:
    """Krótkie „kim jest” z encyklopedii (`tozsamosc`), a nie opowieść.

    Wpisy encyklopedii mają tylko rozdziały fabularne (`historie`) — to streszczenia
    scen, nie opisy postaci, więc ich nie bierzemy. Zostaje etykieta tożsamości,
    np. „回春堂主人” → „Master of the Vernal Hall”, „叛徒” → „The Traitor”.
    """
    czesci: list[str] = []
    opis_pl = True
    for klucz in wpis.get("tozsamosc") or []:
        tekst, jest_pl = _tekst(ix, pl, klucz)
        if tekst and tekst not in czesci:
            czesci.append(tekst)
            opis_pl = opis_pl and jest_pl
    return " · ".join(czesci), opis_pl


def _karta_encyklopedii(baza, ix, pl, pid: str) -> tuple[str, str, bool]:
    """Hasło encyklopedii: imię i tożsamość. Rozdziałów fabularnych nie pokazujemy."""
    row = ix.encyklopedia.get(int(pid)) if str(pid).isdigit() else None
    if not row:
        return "", "", True
    nazwa, _ = _tekst(ix, pl, row.get("nazwa"))
    if not nazwa:
        nazwa, _ = _tekst(ix, pl, row.get("inna_nazwa"))
    opis, opis_pl = _tozsamosc(ix, pl, row)
    return nazwa, opis, opis_pl


def _karta_osoby(baza, ix, pl, pid: str) -> tuple[str, str, bool]:
    """Postać mówiąca: imię z danych gry i tożsamość z encyklopedii, jeśli jest."""
    row = ix.postacie.get(int(pid)) if str(pid).isdigit() else None
    if not row:
        return "", "", True
    nazwa, _ = _tekst(ix, pl, row.get("n"))
    wpis = baza.encyklopedia_po_kluczu.get(row.get("n")) or {}
    opis, opis_pl = _tozsamosc(ix, pl, wpis)
    return nazwa, opis, opis_pl


def _karta_nazwy(ix, pl, nazwa: str, encje: dict) -> tuple[str, str, bool]:
    """Postać znana tylko z imienia w obsadzie: imię plus tożsamość z encyklopedii."""
    wpis = encje.get(nazwa) or {}
    opis, opis_pl = _tozsamosc(ix, pl, wpis)
    return nazwa, opis, opis_pl


def _karta(baza, ix, pl: dict[str, str], tabela: str, rid: str) -> tuple[str, str, bool]:
    """Karta hasła: nazwa, opis i informacja, czy opis jest po polsku."""
    if tabela == "encyklopedia":
        return _karta_encyklopedii(baza, ix, pl, rid)
    if tabela == "osoba":
        return _karta_osoby(baza, ix, pl, rid)
    kolumny = (baza.tabele.get(tabela) or {}).get(rid) or {}
    nazwa, opis, opis_pl = "", "", True
    for kolumna, klucze in kolumny.items():
        for klucz in klucze:
            tekst, jest_pl = _tekst(ix, pl, klucz)
            if tekst and not nazwa and _NAZWA.search(kolumna):
                nazwa = tekst
    if tabela not in _NARRACYJNE:
        opisowe = [k for k in kolumny if _OPIS.search(k)]
        opisowe.sort(key=lambda k: _OPIS_KOLEJNOSC.index(k) if k in _OPIS_KOLEJNOSC else len(_OPIS_KOLEJNOSC))
        for kolumna in opisowe:
            for klucz in kolumny[kolumna]:
                tekst, jest_pl = _tekst(ix, pl, klucz)
                if tekst and len(tekst) > len(opis):
                    opis, opis_pl = tekst, jest_pl
                    break
            if opis:
                break
    if nazwa and opis and (opis in nazwa or nazwa in opis):
        opis = ""
    return nazwa, opis, opis_pl


def _dodaj(karty: list[str], linia: str) -> None:
    """Dopisuje kartę, ale nie powtarza jej, gdy ta sama linia stoi już wyżej."""
    if linia and (not karty or karty[-1] != linia):
        karty.append(linia)


def _plik_kontekstu(ix, jednostki: list[Jednostka], pl: dict[str, str], baza,
                    zrobione: set[str] | None = None) -> tuple[list[str], set[str], int]:
    """Kontekst do każdej jednostki w kolejności z pliku 01.

    Hasło dostaje pełną kartę przy pierwszym wystąpieniu, a przy kolejnych —
    samo imię lub nazwę, żeby dało się prześledzić, kto i co wraca w scenie.
    Kolejność w obrębie jednostki: najpierw mówiący, potem hasła z tekstu.
    """
    teksty = {}
    for numer, jednostka in enumerate(jednostki):
        if not jednostka.linie:
            continue
        zrodla = [ix.zh(klucz) for _m, klucz in jednostka.linie]
        teksty[f"u{numer}"] = ("\n".join(z for z in zrodla if z), jednostka.przestrzenie)
    wzmianki = powiazania_czytanek.skanuj_wzmianki_w_scenach(baza, teksty)
    encje_po_zh: dict[str, dict] = {}
    for wiersz in ix.encyklopedia.values():
        for pole in ("nazwa", "inna_nazwa"):
            klucz = wiersz.get(pole)
            for wariant in (ix.zh(klucz), ix.en(klucz), pl.get(klucz or "")):
                if wariant:
                    encje_po_zh.setdefault(wariant, wiersz)

    out: list[str] = []
    widziane: dict[tuple[str, str], bool] = {}
    pokazane_nazwy: dict[str, bool] = {}
    uzyte: set[str] = set()
    ostatnia_sekcja = None
    ktory = 0
    for numer, jednostka in enumerate(jednostki):
        if not jednostka.linie:
            continue
        if zrobione is not None and jednostka.etykieta not in zrobione:
            continue
        hasla: list[tuple[str, str]] = [
            ("osoba", pid) if pid and pid.isdigit() and int(pid) in ix.postacie else ("nazwa", imie or pid)
            for pid, imie in jednostka.osoby]
        for tabela, ridy in (wzmianki.get(f"u{numer}") or {}).items():
            hasla.extend((tabela, rid) for rid in ridy)
        karty: list[str] = []
        for para in hasla:
            if para[0] == "nazwa":
                nazwa, opis, opis_pl = _karta_nazwy(ix, pl, para[1], encje_po_zh)
            else:
                nazwa, opis, opis_pl = _karta(baza, ix, pl, *para)
            nazwa = _etykieta_hasla(ix, nazwa)
            if not opis:
                # bez opisu nie ma czego pokazać — hasło zostaje w pliku 03
                continue
            # to samo hasło bywa w danych pod dwoma kluczami (postać + nazwa);
            # powtórka nie wnosi treści, więc się nie pojawia
            if nazwa and nazwa in pokazane_nazwy:
                continue
            if para in widziane:
                continue
            widziane[para] = True
            if nazwa:
                pokazane_nazwy[nazwa] = True
            skrocony = len(opis) > DLUGOSC_KARTY
            tresc_opisu = opis
            if skrocony:
                # w kontekście tylko zajawka; pełny tekst zostaje w pliku 03
                tresc_opisu = opis[:DLUGOSC_KARTY].rsplit(" ", 1)[0] + "…"
            if not opis_pl and tresc_opisu:
                tresc_opisu = f"\\*{tresc_opisu}"
            # hasła zużywamy z pliku 03 tylko wtedy, gdy pokazaliśmy pełny opis
            if not skrocony:
                if para[0] == "nazwa":
                    uzyte.update(k for grupa in (encje_po_zh.get(para[1]) or {}).get("historie", [])
                                 for k in grupa)
                elif para[0] == "osoba":
                    wiersz = ix.postacie.get(int(para[1])) or {}
                    if wiersz.get("n"):
                        uzyte.add(wiersz["n"])
                    wpis = baza.encyklopedia_po_kluczu.get(wiersz.get("n")) or {}
                    for klucz in (wpis.get("nazwa"), wpis.get("inna_nazwa")):
                        if klucz:
                            uzyte.add(klucz)
                    for grupa in wpis.get("historie") or []:
                        uzyte.update(k for k in grupa if k)
                else:
                    kolumny = (baza.tabele.get(para[0]) or {}).get(para[1]) or {}
                    uzyte.update(k for klucze in kolumny.values() for k in klucze)
            if nazwa and tresc_opisu:
                _dodaj(karty, f"**{nazwa}:** {tresc_opisu}")
            elif nazwa:
                _dodaj(karty, f"**{nazwa}**")
            else:
                _dodaj(karty, tresc_opisu)
        if not karty:
            continue
        ktory += 1
        if jednostka.sekcja != ostatnia_sekcja:
            out += [jednostka.sekcja, ""]
            ostatnia_sekcja = jednostka.sekcja
        out += [f"## {jednostka.etykieta}", ""] + karty + [""]
    return out, uzyte, ktory


def _haslo(nazwa: str, opisy: list[str]) -> str:
    opis = " · ".join(opisy)
    return f"**{nazwa}:** {opis}" if opis else f"**{nazwa}**"


def _sekcja_zadan(opisy: dict[str, list[str]], klucze_nazw: dict[str, str], ix, pl,
                  krainy: list[dict] | None) -> list[str]:
    """Sekcja „Zadania i wątki” w kolejności łańcucha gry, nie alfabetycznie."""
    z_klucza: dict[str, str] = {}
    for nazwa, klucz in klucze_nazw.items():
        z_klucza.setdefault(klucz, nazwa)
    out: list[str] = []
    wypisane: set[str] = set()
    for blok in kolejnosc_zadan.plan(ix, pl, krainy):
        linie = []
        for klucz in blok.klucze:
            nazwa = z_klucza.get(klucz)
            if not nazwa or nazwa in wypisane or nazwa not in opisy:
                continue
            wypisane.add(nazwa)
            linie.append(_haslo(nazwa, opisy[nazwa]))
        if linie:
            out += [f"## {blok.tytul}", ""] + linie + [""]
    reszta = [nazwa for nazwa in sorted(opisy, key=str.lower) if nazwa not in wypisane]
    if reszta:
        out += ["## Pozostałe zadania i wątki", ""]
        out += [_haslo(nazwa, opisy[nazwa]) for nazwa in reszta]
        out.append("")
    return out


def _reszta(ix, pl, uzyte: set[str], statystyka: dict,
            krainy: list[dict] | None = None) -> list[str]:
    """Co nie trafiło do 01 ani 02 — pogrupowane rodzajem: „nazwa — opis”."""
    sekcje: dict[str, dict[str, list[str]]] = {}
    bez_nazwy: dict[str, list[str]] = {}
    widziane: dict[str, set[tuple[str, str]]] = {}
    klucze_nazw: dict[str, str] = {}   # „etykieta\x00nazwa” → klucz nazwy w indeksie
    for klucz, tekst in pl.items():
        if klucz in uzyte:
            continue
        zrodlo = ix.teksty.get(klucz)
        if zrodlo is None or not zrodlo.w:
            continue
        numer = zrodlo.w[0]
        nazwa_tabeli = ix.zrodla[numer][0] if isinstance(numer, int) and numer < len(ix.zrodla) else str(numer)
        etykieta = _kategoria(nazwa_tabeli)
        nazwa = _nazwa_klucza(ix, zrodlo.w[2], pl) if len(zrodlo.w) > 2 else ""
        nazwa = pinyin_slownik.romanizuj(nazwa) if nazwa else nazwa
        zbior = widziane.setdefault(etykieta, set())
        if nazwa:
            if ("nazwa", nazwa) not in zbior:
                sekcje.setdefault(etykieta, {})[nazwa] = []
                zbior.add(("nazwa", nazwa))
                if len(zrodlo.w) > 2 and isinstance(zrodlo.w[2], str):
                    klucze_nazw[etykieta + "\x00" + nazwa] = zrodlo.w[2]
            if tekst != nazwa and tekst not in nazwa and nazwa not in tekst:
                if tekst not in sekcje[etykieta][nazwa]:
                    sekcje[etykieta][nazwa].append(tekst)
        else:
            linia = tekst
            if len(linia) >= 4 and ("linia", linia) not in zbior:
                zbior.add(("linia", linia))
                bez_nazwy.setdefault(etykieta, []).append(linia)
        statystyka["reszta"] += 1

    out: list[str] = []
    for etykieta in sorted(set(sekcje) | set(bez_nazwy)):
        out += [f"# {etykieta}", ""]
        if etykieta == "Zadania i wątki" and sekcje.get(etykieta):
            wlasne = {klucz.split("\x00", 1)[1]: wartosc
                      for klucz, wartosc in klucze_nazw.items()
                      if klucz.startswith(etykieta + "\x00")}
            out += _sekcja_zadan(sekcje[etykieta], wlasne, ix, pl, krainy)
            out.extend(sorted(bez_nazwy.get(etykieta, []), key=str.lower))
            out.append("")
            continue
        for nazwa in sorted(sekcje.get(etykieta, {}), key=str.lower):
            out.append(_haslo(nazwa, sekcje[etykieta][nazwa]))
        out.extend(sorted(bez_nazwy.get(etykieta, []), key=str.lower))
        out.append("")
    return out


def zbuduj(*, index: str, magazyn: str, wyj: Path, zakres: str) -> dict:
    ix = indeks_mod.wczytaj(index, teksty=True, sceny=True)
    pl = _magazyn(Path(magazyn), Path(index))
    porzadek = _wczytaj_porzadek(index)
    chronologia = chronologia_mod.wczytaj(index)
    krainy = json.loads((Path(index) / "prowincje.json").read_text(encoding="utf-8"))

    wyj.mkdir(parents=True, exist_ok=True)
    statystyka = {"jednostek": 0, "linii": 0, "pominiete": 0, "reszta": 0, "plikow": 0,
                  "kontekst": 0, "bez_przekladu": 0}

    jednostki = _jednostki_z_chronologii(ix, pl, porzadek, chronologia, krainy)
    tresc, uzyte, zrobione = _plik_scen(jednostki, pl, zakres, statystyka, ix)
    (wyj / "01_sceny_i_cutsceny.md").write_text(
        _naglowek("Sceny i cutsceny",
                  "Prolog i krainy po kolei (sceny i cutsceny przemieszane), "
                  "pieśni na końcu, bo w grze nie ma ich na początku: "
                  "sceny i cutsceny przemieszane w kolejności występowania.") + "\n".join(tresc) + "\n",
        encoding="utf-8")
    statystyka["plikow"] += 1

    baza = powiazania_czytanek.zbuduj_baze(ix)
    tresc_kontekstu, uzyte_kontekstu, ktore = _plik_kontekstu(ix, jednostki, pl, baza, zrobione)
    statystyka["kontekst"] = ktore
    (wyj / "02_kontekst_scen_i_cutscen.md").write_text(
        _naglowek("Kontekst scen i cutscen",
                  "Te same jednostki i ta sama kolejność co w pliku 01: postacie, encyklopedia, "
                  "frakcje, miejsca, przedmioty i sztuki walki wymienione w scenie. Wchodzą tylko "
                  "hasła, które gra naprawdę opisuje; pełna karta stoi przy pierwszym wystąpieniu, "
                  "przy kolejnych samo imię albo nazwa. Opis dłuższy niż "
                  f"{DLUGOSC_KARTY} znaków jest ucinany wielokropkiem — całość zostaje w pliku 03.") + "\n".join(tresc_kontekstu) + "\n",
        encoding="utf-8")
    statystyka["plikow"] += 1

    tresc_reszty = _reszta(ix, pl, uzyte | uzyte_kontekstu, statystyka, krainy)
    tresc_reszty += _zbiory(ix, pl, uzyte | uzyte_kontekstu, statystyka)
    tresc_reszty += _pamiatki(ix, pl, uzyte | uzyte_kontekstu, statystyka, index)
    tresc_reszty += _poi(ix, pl, uzyte | uzyte_kontekstu, statystyka, index)
    (wyj / "03_reszta.md").write_text(
        _naglowek("Reszta", "Przekłady, których nie ma w plikach 01 i 02, pogrupowane rodzajem.")
        + "\n".join(tresc_reszty) + "\n", encoding="utf-8")
    statystyka["plikow"] += 1

    (wyj / "README.md").write_text(_readme(statystyka, zakres), encoding="utf-8")
    statystyka["plikow"] += 1
    return statystyka


def _naglowek(tytul: str, opis: str) -> str:
    return f"# Where Winds Meet — {tytul}\n\n{opis}\n\n"


def _readme(statystyka: dict, zakres: str) -> str:
    return f"""# Czytanka Where Winds Meet

| plik | zawartość |
|---|---|
| `01_sceny_i_cutsceny.md` | sceny i cutsceny razem, chronologicznie: prolog, krainy po kolei, pieśni na końcu |
| `02_kontekst_scen_i_cutscen.md` | kontekst do tych samych jednostek w tej samej kolejności: tylko hasła, które gra naprawdę opisuje — pełna karta raz, powtórki się nie powtarzają, bez punktora |
| `03_reszta.md` | przekłady spoza 01 i 02, pogrupowane rodzajem; tu też hasła bez opisu i pełne teksty kart uciętych w 02 |

Kwestie w 01: `**Mówca:** tekst`, jedna kwestia na linię, bez punktora, czasów
i tabel; kwestia bez mówcy to goły tekst.
Gracz zawsze jako **Youxia**. Kwestie bez polskiego przekładu stoją z gwiazdką
(`\\*Fate is already sealed.`), więc widać, gdzie tłumaczenia jeszcze nie ma.
Etykiety mówców zapisane w grze tylko po chińsku są transliterowane na łacinkę
(`大祭师` → `Da Ji Shi`), bo tłumaczenia tych nazw gra nie ma.
Zakres: **{zakres}**.

Statystyka: {statystyka['jednostek']} jednostek, {statystyka['linii']} kwestii,
{statystyka['kontekst']} jednostek z kontekstem, {statystyka['reszta']} pozycji w reszcie,
{statystyka['pominiete']} kwestii bez polskiego pominięto,
{statystyka['bez_przekladu']} kwestii stoi z gwiazdką, bo przekładu jeszcze nie ma,
{statystyka.get('zbiory', 0)} kart zbiorów, {statystyka.get('pamiatki', 0)} pamiątek (przedmiotów z historią) i {statystyka.get('poi', 0)} punktów na mapie (POI — z tego {statystyka.get('poi_z_dialogiem', 0)} z potwierdzonym numerem sceny) w pliku 03.

Karty kontekstu bez polskiego przekładu mają tekst z gry z gwiazdką — tak samo
jak kwestie w pliku 01.

Opis hasła to definicja z danych gry (przedmiot, frakcja, miejsce, sztuka walki),
a przy postaciach krótka tożsamość z encyklopedii („Chen Zixi: Master of the Vernal
Hall”). Rozdziałów fabularnych encyklopedii (`historie`) nie bierzemy — to
streszczenia scen, nie opisy postaci.
"""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--index", default="index")
    ap.add_argument("--magazyn", default="tlumaczenie")
    ap.add_argument("--wyj", default="out/czytanka")
    ap.add_argument("--zakres", choices=("przetlumaczone", "wszystko"), default="wszystko",
                    help="wszystko = kwestie bez przekładu też, z gwiazdką (domyślnie); "
                         "przetlumaczone = tylko polski")
    ap.add_argument("--zip", help="własna ścieżka paczki (nadpisuje plik)")
    ap.add_argument("--wersja", help="numer wersji paczki, np. 7 → dist/WWM_Czytanka_PL_v7.zip; "
                                     "nigdy nie nadpisuje istniejącej wersji")
    a = ap.parse_args(argv)
    if a.wersja:
        numer = a.wersja.strip().lstrip("vV")
        if not numer.isdigit():
            ap.error("--wersja przyjmuje liczbę, np. 7")
        cel = Path("dist") / f"WWM_Czytanka_PL_v{numer}.zip"
        if cel.exists():
            ap.error(f"{cel} już jest — podnieś numer wersji (v{int(numer) + 1}?)")
        a.zip = str(cel)

    wyj = Path(a.wyj)
    statystyka = zbuduj(index=a.index, magazyn=a.magazyn, wyj=wyj, zakres=a.zakres)
    print(json.dumps(statystyka, ensure_ascii=False))
    if a.zip:
        import zipfile

        Path(a.zip).parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(a.zip, "w", zipfile.ZIP_DEFLATED) as paczka:
            for plik in sorted(wyj.glob("*.md")):
                paczka.write(plik, plik.name)
        print(f"{a.zip}: {Path(a.zip).stat().st_size} B")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
