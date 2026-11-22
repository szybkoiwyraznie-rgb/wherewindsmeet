#!/usr/bin/env python3
"""Czytanka WWM do czytania — dwa pliki treści plus README, w układzie ustalonym z właścicielem.

1. `01_sceny_i_cutsceny.md` — sceny **i** cutsceny razem, chronologicznie:
   filmy otwierające, prolog w kolejności sprawdzonej z transkryptem, potem krainy
   w kolejności odwiedzania (sceny w porządku grafu następstw), na końcu pozostałe pule
   napisów przerywników.
2. `02_reszta.md` — komplet informacji dodatkowych: cała reszta przekładów,
   której nie ma w 01 (przedmioty, encyklopedia, kompendium itd.), pogrupowana
   według rodzaju danych. (Dawny plik 02 z kontekstem scen zlikwidowany na
   życzenie właściciela — wszystko, co pokazywał, trafia do tego pliku,
   a numer 02 przejął plik reszty.)

Gdy któryś plik treści nie mieści się w budżecie `_CZESC_BUDZET`, jest cięty
na części `NN_baza_01.md …`, a tytuł części w środku opisuje jej zawartość
(np. `02 - przedmioty — część 2 z 3`).

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
from tools import kontekst_cutscen as kontekst_cutscen_mod  # noqa: E402
from tools import cutsceny_kolejnosc_kwestii as kolejnosc_mod  # noqa: E402
from tools import kolejnosc_gry, kolejnosc_zadan, pinyin_slownik  # noqa: E402
from tools import tlumaczenie as tlumaczenie_mod  # noqa: E402

PROG_WARIANTU = 48
PROG_NAGLOWKA_REDAKCJI = 3   # ile kwestii przed pierwszym bliźniakiem należy jeszcze do dialogu sceny
BEZ_PRZEKLADU = "\\*"   # kwestia bez przekładu: gwiazdka i tekst z gry
BEZ_MAPY = ":sceny-bez-mapy:"
_KOLOR = re.compile(r"#[0-9a-fA-F]{6}|#[A-Z]")
_ODNOSNIK = re.compile(r"<([^<>|]{1,80})(\|[^<>]*)?>")
_SPACJE = re.compile(r"\s+")
_DOLAR_T = re.compile(r"\$T\([^)]*\)")
_DOLAR_N = re.compile(r"\$N")


# W danych gracza ta sama postać bywa nazwana różnie; dla czytelnika to zawsze „Ty”.
GRACZ = {nazwa.lower(): "Youxia" for nazwa in (
    "你", "我", "玩家", "主角", "player", "Player", "PLAYER", "You", "主角（玩家）",
    "main_player", "main player", "mainplayer", "protagonist", "主角玩家",
)}
TECHNICZNE = {"Entity轨道组", "轨道组", "entity", "Entity", "旁白占位"}

KATEGORIE = (
    (("encyclopedia", "manual", "ever_know", "book", "clue", "letter", "email",
      "jianwen", "envelop", "poem", "kaoju"),
     "Encyklopedia, księgi i poszlaki"),
    (("kongfu", "xinfa", "jianghu_skill", "qishu", "buff", "skill", "talent"),
     "Sztuki walki i umiejętności"),
    (("equip", "stuff", "fashion", "item", "bag", "weapon", "armor", "title"),
     "Przedmioty, stroje i tytuły"),
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
    """Zdejmij kody kolorów, placeholdery i odnośniki rich-text, złóż białe znaki.

    W danych gry łamanie akapitu bywa zapisane dosłownie jako `\\n` albo `\\v`
    (także pionowy tabulator). Kwestia w 01 ma być jedną linią — zamieniamy
    to na spację. `$T(…)` to podstawienie imienia, `$N` — imię gracza.
    """
    tekst = tekst or ""
    tekst = (tekst.replace("\\v", " ").replace("\v", " ")
             .replace("\\n", " ").replace("\\r", " ").replace("\\t", " ")
             .replace("\\P", " "))
    tekst = _DOLAR_T.sub("", tekst)
    tekst = _DOLAR_N.sub("Youxia", tekst)
    tekst = _ODNOSNIK.sub(lambda m: m.group(1), tekst)
    tekst = _KOLOR.sub("", tekst)
    return _SPACJE.sub(" ", tekst).strip()


def _akapity(tekst: str) -> list[str]:
    """Treść listu: `\\v` / `\\n` łamie linię (bez pustego wiersza), reszta jak `_czysty`."""
    if not tekst:
        return []
    rozbity = (tekst.replace("\\v", "\n").replace("\v", "\n")
               .replace("\\n", "\n").replace("\\P", "\n"))
    return [linia for kawałek in rozbity.split("\n")
            if (linia := _czysty(kawałek))]


def _kategoria(tabela: str) -> str:
    nazwa = tabela.lower()
    for slowa, etykieta in KATEGORIE:
        if any(slowo in nazwa for slowo in slowa):
            return etykieta
    return "Pozostałe teksty"


def _magazyn(katalog: Path, index: Path | str = "index", *, czysc: bool = True) -> dict[str, str]:
    """Przekłady po kluczu tekstu, razem z wariantami płci bohatera.

    Kwestie zależne od płci gracza mają w grze osobne identyfikatory (`@id`),
    a w magazynie osobny plik `pl_warianty.jsonl`. Bez `index/warianty.jsonl`
    nie da się ich przypisać do klucza tekstu — i wtedy czytanka pokazywała
    angielski tekst mimo gotowego przekładu (np. „This symbol…” w scenie
    4700001). Czytamy wariant bohatera; gdy go nie ma, pierwszy dostępny.
    `czysc=False` zostawia surowy tekst (akapity `\\v` w listach).
    """
    magazyn = tlumaczenie_mod.wczytaj(katalog, warianty=Path(index) / "warianty.jsonl")
    pelny = {klucz: tekst for klucz, tekst in magazyn.po_kluczu_pelny().items()
             if tekst and tekst.strip()}
    if not czysc:
        return pelny
    return {klucz: _czysty(tekst) for klucz, tekst in pelny.items()}


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
    wstep: str = ""                                           # wiersz nad nagłówkiem, np. „Interakcja: …”
    numer: int | None = None                                  # numer sceny/cutsceny (do listów)


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
                     audio: dict[int, str] | None = None,
                     kolejnosc: list[list[dict]] | None = None,
                     zh=None,
                     wlasciciele: dict[str, int] | None = None
                     ) -> tuple[list[str], dict[int, str], list[str]]:
    """Napisy cutsceny w kolejności gry, z osobnymi wariantami i streszczeniem.

    Kolejność kwestii, gdy jest, bierzemy ze ścieżki audio pliku `.cine`
    (`index/cutsceny_kolejnosc_kwestii.jsonl`, patrz
    `tools/cutsceny_kolejnosc_kwestii.py`) — to pełny przeplot bloków puli
    `text_msg` (Ruby i gracz w 30161 leżą w dwóch sąsiednich zakresach, a mówią
    na przemian). Chronologia potrafi też **doczepić** wiersze, których `kn`
    cutsceny nie znało (blok gracza 591170–591183 leżał dotąd w „Napisach
    przerywnika"). Dla kwestii spoza chronologii zostaje porządek numerów
    wierszy puli. Ten sam przerywnik leży w puli kilka razy: starsza i nowsza
    wersja napisów (np. 590153–590179 i 591148–591169 w 30161). Grany jest
    **najnowszy** blok, a starsze wersje schodzą pod nagłówek wariantu, żeby
    nic nie ginęło, ale czytelnik nie dostał dwóch scen splątanych w jedną.

    Gdy podano `zh` (klucz → tekst chiński), bloki spoza chronologii, które
    prawie wcale nie pokrywają się treścią z blokiem głównym (poniżej 30 %
    kwestii), dostają uczciwszy nagłówek „Napisy sąsiadujące w puli" —
    pula trzyma obok siebie wiersze różnych scen (np. recytacja sztuki
    o Ośmiu Wspaniałych w wierszach 591125–591147 tuż przed blokiem 30161)
    i to nie są warianty tej cutsceny.

    Streszczenie sceny (`k`) stoi **na początku**, zaraz pod nagłówkiem cutsceny.
    """
    napisy = [k for k in wiersz.get("kn") or [] if k]
    pozycja: dict[str, int] = {}
    for numer, klucz in enumerate(napisy):
        pozycja.setdefault(klucz, numer)

    bloki_chrono: list[list[str]] = []
    pokryte: set[str] = set()
    for blok in kolejnosc or []:
        klucze_bloku = [r["k"] for r in blok if r.get("k")]
        if klucze_bloku:
            bloki_chrono.append(klucze_bloku)
            pokryte.update(klucze_bloku)
    bloki_chrono.sort(key=lambda b: _najwyzszy(b, wiersze), reverse=True)

    def do_sortowania(klucz: str) -> tuple:
        numer = wiersze.get(klucz)
        return (0, numer, pozycja[klucz]) if numer is not None else (1, 0, pozycja[klucz])

    luzem = [k for k in sorted(pozycja, key=do_sortowania) if k not in pokryte]
    bloki = bloki_chrono + (_podziel_na_bloki(luzem, wiersze) if luzem else [])
    if not bloki_chrono and len(bloki) > 1:
        porzadek_blokow = sorted(range(len(bloki)),
                                 key=lambda i: _najwyzszy(bloki[i], wiersze), reverse=True)
        bloki = [bloki[i] for i in porzadek_blokow]
        sygnatury = _sygnatury([k for blok in bloki for k in blok], pl)
        dialog, obce = _dialog_sceny(bloki[0], bloki, wiersze, sygnatury)
        bloki = [dialog] + ([obce] if obce else []) + bloki[1:]

    klucze: list[str] = []
    podtytuly: dict[int, str] = {}
    powtorzone: list[str] = []
    widziane: set[str] = set()

    liczba_chrono = len(bloki_chrono) or 1
    baza_norm: set[str] = set()
    if zh and bloki:
        for blok in bloki[:min(liczba_chrono, len(bloki))]:
            for k in blok:
                nz = kolejnosc_mod._norm(zh(k) or "")
                if nz:
                    baza_norm.add(nz)

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
            if zh and baza_norm and numer_bloku >= liczba_chrono:
                normy = [nz for nz in (kolejnosc_mod._norm(zh(k) or "") for k in blok) if nz]
                trafione = sum(1 for nz in normy
                               if any(nz in b or b in nz for b in baza_norm))
                if normy and trafione * 10 < len(normy) * 3:
                    naglowek = (f"Napisy sąsiadujące w puli przerywników ({opis}) — "
                                "zapewne inna scena w pobliżu")
                    # gdy nazwa nagrania któregoś wiersza zdradza cudzą cutscenę,
                    # wskazujemy ją wprost (dowód z danych, nie zgadywanie)
                    cudze = {wlasciciele.get(kontekst_cutscen_mod.rdzen_audio(
                                 (audio or {}).get(wiersze.get(k)) or ""))
                             for k in blok} - {None} if wlasciciele else set()
                    cudze -= {int(wiersz.get("n") or 0) % 10**8}
                    if len(cudze) == 1:
                        naglowek += f" (są tu nagrania cutsceny {cudze.pop()})"
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


def _mowcy_cutsceny(klucze: list[str], ix, pl, porzadek,
                    wiersze_napisow: dict[str, int],
                    audio_napisow: dict[int, str],
                    audio_kluczy: dict[str, str]) -> dict[str, str]:
    """Mówcy kwestii cutsceny + bezpieczna propagacja po plikach nagrań.

    Identyfikacja wprost: krok dialogu sceny (`_mowca_klucza`) albo nazwa
    nagrania (`mowca_z_audio`) — z audio wiersza w kontekście **i** z audio
    kwestii `.cine` osobno (kontekst potrafi mieć generyczne `npc_NN`, gdy
    `.cine` ma `pma_NN`). Potem propagacja, wyłącznie w obrębie tej jednej
    cutsceny:

    1. **Jeden plik audio to jeden głos** — gdy część wierszy tego samego
       nagrania ma mówcę, a identyfikacje są zgodne, etykieta przechodzi na
       pozostałe wiersze tego nagrania (w 30161 `sxdm7_npc_07` kryje cztery
       wiersze, z czego kontekst zna Ruby tylko dla dwóch).
    2. **Rodzina placeholderów `..._npc_NN`** ścieżki `.cine`: gdy co
       najmniej dwa nagrania rodziny są zidentyfikowane i wszystkie wskazują
       tę samą postać, pozostałe nagrania rodziny dostają tę etykietę
       (ścieżka 30161 nazywa głos Ruby `sxdm7_npc_*`, a jej prawdziwe
       nagrania `cs_zlxl_hx_*` kontekst zna dla części wierszy). Przy
       jakiejkolwiek niezgodności identyfikacji nic nie propagujemy.
    """
    mowcy: dict[str, str] = {}
    pliki: dict[str, set[str]] = {}
    for klucz in klucze:
        numer = wiersze_napisow.get(klucz)
        ctx = (audio_napisow.get(numer) if numer is not None else None) or ""
        cine = audio_kluczy.get(klucz) or ""
        mowcy[klucz] = (_mowca_klucza(klucz, ix, pl, porzadek)[0]
                        or kontekst_cutscen_mod.mowca_z_audio(ctx)
                        or kontekst_cutscen_mod.mowca_z_audio(cine))
        for plik in (ctx, cine):
            if plik:
                pliki.setdefault(plik, set()).add(klucz)
    for grupa in pliki.values():        # 1. jeden plik audio = jeden głos
        znani = {mowcy[k] for k in grupa if mowcy[k]}
        if len(znani) == 1:
            mowca = next(iter(znani))
            for k in grupa:
                mowcy[k] = mowcy[k] or mowca
    rodziny: dict[str, dict[str, str]] = {}
    for klucz in klucze:                # 2. rodzina placeholderów `_npc`
        cine = audio_kluczy.get(klucz) or ""
        rdzen = kontekst_cutscen_mod.rdzen_audio(cine)
        if rdzen.endswith("_npc"):
            wpis = rodziny.setdefault(rdzen, {})
            wpis[cine] = wpis.get(cine) or mowcy[klucz]
    for rdzen, nagrania in rodziny.items():
        znani = {m for m in nagrania.values() if m}
        if len(znani) == 1 and sum(1 for m in nagrania.values() if m) >= 2:
            mowca = next(iter(znani))
            for klucz in klucze:
                if audio_kluczy.get(klucz) in nagrania:
                    mowcy[klucz] = mowcy[klucz] or mowca
    return mowcy


def _wlasciciele_nagran(index: str | Path) -> dict[str, int]:
    """Rdzeń nazwy nagrania → cutscena, której scenariusz `.cine` go używa.

    Tylko rdzenie jednoznaczne (jedna cutscena po zwinięciu klonów
    `no % 10**8`: 40000030246 → 30246). Dzięki temu blok „Napisy
    sąsiadujące" może uczciwie wskazać właściciela, gdy któryś wiersz
    niesie nagranie cudzej cutsceny (591126 `…_cs_nzgzcj_dqgz` → 30435).
    Rdzenie wielu cutscen (placeholdery `…_npc`, domeny `vo_shenxiandu_*`)
    odpadają — nie identyfikują sceny.
    """
    plik = Path(index) / "cutsceny_sciezka_audio.jsonl"
    if not plik.exists():
        return {}
    rdzenie: dict[str, set[int]] = {}
    with plik.open(encoding="utf-8") as f:
        for linia in f:
            wpis = json.loads(linia)
            for kwestia in wpis.get("kwestie") or []:
                rdzen = kontekst_cutscen_mod.rdzen_audio(kwestia.get("audio") or "")
                if rdzen:
                    rdzenie.setdefault(rdzen, set()).add(int(wpis["no"]) % 10**8)
    return {rdzen: nums.pop() for rdzen, nums in rdzenie.items() if len(nums) == 1}


def _kolejnosc_kwestii_cutscen(index: str | Path) -> dict[int, list[list[dict]]]:
    """Chronologia kwestii cutscen ze ścieżek audio `.cine` (gdy indeks istnieje).

    `index/cutsceny_kolejnosc_kwestii.jsonl` buduje
    `tools/cutsceny_kolejnosc_kwestii.py`; bez niego czytanka wraca do
    porządku numerów wierszy puli.
    """
    plik = Path(index) / "cutsceny_kolejnosc_kwestii.jsonl"
    if not plik.exists():
        return {}
    wynik: dict[int, list[list[dict]]] = {}
    with plik.open(encoding="utf-8") as f:
        for linia in f:
            wpis = json.loads(linia)
            wynik[int(wpis["no"])] = wpis.get("bloki") or []
    return wynik


def _jednostki_z_chronologii(ix, pl, porzadek, chronologia: list[dict],
                             krainy: list[dict] | None = None,
                             index: str | Path | None = None) -> list[Jednostka]:
    """Chronologia jest zapisana w `index/chronologia.jsonl`; tu tylko czytamy kolejność."""
    nazwy_pl = _nazwy_krain(ix, pl, krainy or [])
    poi_scen = _poi_scen(ix, pl, index) if index else {}

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
    kolejnosc_cutscen = _kolejnosc_kwestii_cutscen(index) if index else {}
    wlasciciele_nagran = _wlasciciele_nagran(index) if index else {}
    numery_cutscen = {int(w["n"]) for w in chronologia if w["t"] == "cutscena"}
    # wiersze przejęte przez chronologię cutscen znikają z „Napisów przerywnika"
    przejete = {r["k"] for numer, bloki in kolejnosc_cutscen.items()
                if numer in numery_cutscen
                for blok in bloki for r in blok if r.get("k")}

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
                if not mowca:
                    # mówca z nazwy nagrania (jak w cutscenach) — prologi to
                    # też napisy puli, krok dialogu sceny zwykle ich nie zna
                    numer_wiersza = wiersze_napisow.get(klucz)
                    audio = audio_napisow.get(numer_wiersza) if numer_wiersza else None
                    mowca = kontekst_cutscen_mod.mowca_z_audio(audio or "")
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
                {int(m) for m in scena.get("m") or [] if str(m).isdigit()}, osoby,
                wstep=(f"Interakcja: {poi_scen[numer]}" if numer in poi_scen else ""),
                numer=numer))
        elif rodzaj == "cutscena":
            numer = int(wiersz["n"])
            kolejnosc = kolejnosc_cutscen.get(numer)
            klucze, podtytuly, powtorzone = _napisy_cutsceny(wiersz, wiersze_napisow, pl,
                                                            audio_napisow, kolejnosc,
                                                            zh=ix.zh,
                                                            wlasciciele=wlasciciele_nagran)
            audio_kluczy = {r["k"]: r["a"] for blok in kolejnosc or []
                            for r in blok if r.get("k") and r.get("a")}
            mowcy_osi = {r["k"]: r["m"] for blok in kolejnosc or []
                         for r in blok if r.get("k") and r.get("m")}
            mowcy = _mowcy_cutsceny(klucze, ix, pl, porzadek,
                                    wiersze_napisow, audio_napisow, audio_kluczy)
            linie = [(mowcy_osi.get(klucz) or mowcy.get(klucz, ""), klucz) for klucz in klucze]
            osoby = [("", m) for m in dict.fromkeys(m for m, _k in linie if m)]
            liczba_streszczenia = sum(1 for k in wiersz.get("k") or [] if k)
            jednostki.append(Jednostka("cutscena", f"Cutscena {numer}", sekcja(wiersz["s"]),
                                       linie, osoby=osoby, podtytuly=podtytuly,
                                       zasloniete=tuple(powtorzone),
                                       streszczenie=liczba_streszczenia))
        elif rodzaj == "napisy":
            linie = []
            for klucz in wiersz.get("k") or []:
                if klucz in przejete:
                    continue        # kwestia poszła do swojej cutsceny (chronologia `.cine`)
                if linie and linie[-1][1] == klucz:
                    continue
                mowca, gdzie = _mowca_klucza(klucz, ix, pl, porzadek, mowcy_napisow)
                linie.append((mowca, klucz))
            if not linie:
                continue            # cały blok przejęty przez cutsceny
            etykieta = wiersz.get("e") or "Napisy przerywnika"
            if przejete and etykieta.startswith("Napisy przerywnika — wiersze "):
                numery = sorted(wiersze_napisow[k] for _m, k in linie
                                if k in wiersze_napisow)
                if numery:      # po oddaniu kwestii cutscenom zakres bywa węższy
                    etykieta = (f"Napisy przerywnika — wiersze {numery[0]}–{numery[-1]}"
                                if numery[0] != numery[-1]
                                else f"Napisy przerywnika — wiersz {numery[0]}")
            osoby = [("", m) for m in dict.fromkeys(m for m, _k in linie if m)]
            jednostki.append(Jednostka(
                "napisy", etykieta,
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
# trafiał do reszty tylko tekst (jako „nazwa — opis” z przypadku), a karty bez
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
# tak jak w pozostałych sekcjach pliku 02
GWIAZDKA = "\\*"

_PAMIATKI_PLIK = "pamiatki.jsonl"
# rola -> (tabela, kolumna): przestrzeń świadków z `index/zrodla.json`
_PAMIATKI_PRZESTRZENIE = (
    ("nazwa", "equip_items", "name"),
    ("wlasciciel", "curio_owner", "owner_name"),
    ("pamiec", "text_msg", "content"),
    ("motyw", "curio_theme", "history_name"),
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


def _legenda_pamiatki(ix, pl: dict[str, str], mapa_motywow: dict[str, str],
                      wpis: dict) -> str:
    """Nazwa legendy pamiątki: nazwa motywu z gry i numer w legendzie.

    Gra podpisuje każdą pamiątkę nazwą legendy (`curio_theme.history_name`,
    np. „At Heaven's Pier”) i numerem w jej obrębie (`kolejnosc`). Kluczem
    wiersza w przestrzeni świadków jest numer motywu zapisany jako tekst —
    dlatego szukamy wprost w mapie motywów, nie przez `_tekst_nazwy`
    (mapy `index/nazwy.jsonl` używają innych identyfikatorów i mały numer
    motywu mógłby trafić w cudzy wpis).
    """
    klucz = mapa_motywow.get(str(wpis.get("motyw") or ""))
    if not klucz:
        return ""
    przeklad = pl.get(klucz)
    tekst = (przeklad or (GWIAZDKA + _z_gry(ix, klucz))).strip()
    if not tekst.strip(GWIAZDKA + " "):
        return ""
    kolejnosc = wpis.get("kolejnosc")
    return f"{tekst} · {kolejnosc}" if kolejnosc else tekst


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
        # Tytuł, legenda i treść stoją w kolejnych liniach — bez pustych wierszy.
        karty.append(f"**{tytul}**")
        legenda = _legenda_pamiatki(ix, pl, mapy["motyw"], wpis)
        if legenda:
            karty.append(legenda)
        karty.extend(_blok_tekstu(zrodlo, bool(historia)))
        karty.append("")
        statystyka["pamiatki"] = statystyka.get("pamiatki", 0) + 1
    statystyka["pamiatki_bez_nazwy"] = statystyka.get("pamiatki_bez_nazwy", 0) + ukryte
    if not karty:
        return []
    return ["# Pamiątki — przedmioty z historią", ""] + karty


_POI_PLIK = "poi.jsonl"


def _poi_scen(ix, pl: dict[str, str], katalog: str | Path) -> dict[int, str]:
    """Scena → nazwa POI, który ją wywołuje (interakcja w świecie gry).

    Powiązanie POI→scena pochodzi z `index/mpk/poi_storyline_sceny.jsonl`
    (skrypt `interact_storyline` POI gra tę scenę — patrz
    `tools/poi_storyline_sceny.py`; benchmark: POI 200046001 „Dragon Pattern
    Mark” → scena 4700001). Nazwa POI jak w sekcji POI pliku 02: najpierw
    polski przekład, bez niego tekst z gry z gwiazdką. POI bez nazwy nie
    podpisujemy — lepszy brak wstępu niż goły numer.
    """
    plik_poi = Path(katalog) / _POI_PLIK
    plik_sceny = Path(katalog) / "mpk" / "poi_storyline_sceny.jsonl"
    if not plik_poi.is_file() or not plik_sceny.is_file():
        return {}
    nazwy = _wczytaj_nazwy(katalog)
    numer = _przestrzen(ix, "active_interact_way", "button_name")
    mapa: dict[str, str] = {}
    if numer is not None:
        for klucz, tekst in ix.teksty.items():
            if tekst.w and tekst.w[0] == numer:
                mapa.setdefault(str(tekst.w[1]), klucz)
    ident_poi: dict[int, object] = {}
    for wiersz in plik_poi.read_text(encoding="utf-8").splitlines():
        if not wiersz.strip():
            continue
        wpis = json.loads(wiersz)
        ident_poi[int(wpis["id"])] = wpis.get("nazwa") or wpis.get("id")
    wynik: dict[int, str] = {}
    for wiersz in plik_sceny.read_text(encoding="utf-8").splitlines():
        if not wiersz.strip():
            continue
        wpis = json.loads(wiersz)
        if wpis.get("status") != "sceny":
            continue
        nazwa, _klucz = _tekst_nazwy(ix, pl, mapa,
                                     ident_poi.get(int(wpis["poi"])), nazwy)
        if not nazwa.strip(GWIAZDKA + " "):
            continue
        for scena in wpis.get("sceny") or []:
            wynik.setdefault(int(scena), nazwa)
    return wynik


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


def _kolumny_envelop(ix) -> dict[str, int]:
    """Kolumna `tasks_envelop_data` → indeks źródła w `ix.zrodla`."""
    out: dict[str, int] = {}
    for i, wpis in enumerate(ix.zrodla or []):
        if isinstance(wpis, (list, tuple)) and wpis and wpis[0] == "tasks_envelop_data":
            out[str(wpis[1])] = i
    return out


def _wczytaj_listy(ix) -> dict[str, dict]:
    """Listy fabularne: wiersz `tasks_envelop_data` → klucze kolumn to/from/text."""
    kolumny = _kolumny_envelop(ix)
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


def _tytul_listu(wpis: dict, pl: dict[str, str], ix) -> str:
    klucz = wpis.get("to")
    if klucz and pl.get(klucz):
        return pl[klucz].strip()
    if klucz and ix is not None:
        zrodlo = ix.teksty.get(klucz)
        if zrodlo:
            return _czysty(zrodlo.en or zrodlo.zrodlo or "") or f"List {wpis['id']}"
    return f"List {wpis['id']}"


def _karta_listu(wpis: dict, pl: dict[str, str], surowe: dict[str, str], ix) -> list[str]:
    """Tytuł i treść listu razem; `\\v` to nowa linia, bez pustych wierszy."""
    tytul = _tytul_listu(wpis, pl, ix)
    linie = [f"## List: {tytul}"]
    nadawca_klucz = wpis.get("from")
    if nadawca_klucz:
        nadawca = pl.get(nadawca_klucz) or _czysty(
            (ix.teksty[nadawca_klucz].en if ix and nadawca_klucz in ix.teksty else "")
            or (ix.teksty[nadawca_klucz].zrodlo if ix and nadawca_klucz in ix.teksty else "")
            or "")
        if nadawca and nadawca not in tytul:
            linie.append(nadawca)
    klucz_tresci = wpis.get("text")
    surowy = (surowe.get(klucz_tresci) if klucz_tresci else "") or (
        pl.get(klucz_tresci) if klucz_tresci else "") or ""
    if not surowy and klucz_tresci and ix and klucz_tresci in ix.teksty:
        t = ix.teksty[klucz_tresci]
        surowy = t.en or t.zrodlo or ""
    akapity = _akapity(surowy)
    if not akapity and klucz_tresci and pl.get(klucz_tresci):
        akapity = [pl[klucz_tresci]]
    linie.extend(akapity)
    for extra in ("melody_solved_text", "melody_puzzle_text"):
        klucz = wpis.get(extra)
        if not klucz:
            continue
        extra_txt = pl.get(klucz) or ""
        if extra_txt and extra_txt not in akapity:
            linie.append(extra_txt)
    linie.append("")
    return linie


def _wczytaj_listy_w_grafie(index: str | Path | None) -> list[dict]:
    """Wiersze `index/mpk/listy_w_grafie.jsonl` (OpenUI TaskEnvelopWindow → no)."""
    if not index:
        return []
    plik = Path(index) / "mpk" / "listy_w_grafie.jsonl"
    if not plik.is_file():
        return []
    wiersze: list[dict] = []
    for linia in plik.read_text(encoding="utf-8").splitlines():
        if not linia.strip():
            continue
        wiersze.append(json.loads(linia))
    return wiersze


def _przypisz_listy_do_scen(ix, listy: dict[str, dict],
                            index: str | Path | None = None) -> dict[int, list[str]]:
    """List po scenie, która w grafie Storyline otwiera `TaskEnvelopWindow`.

    Źródło: `index/mpk/listy_w_grafie.jsonl` — węzeł OpenUI z `ui_kwargs.no`
    stoi na krawędzi `__out__` zaraz po `dialogs_no` (pole `po`). Przykład:
    `sxd_xiaowushuxin.etsb` gra 4700002, potem list `no=5`, potem 4700003.
    Bez `po` list zostaje w 02. Nie porównujemy tytułu z kwestią.
    """
    przy: dict[int, list[str]] = {}
    zajete: set[str] = set()
    for wpis in _wczytaj_listy_w_grafie(index):
        rid = str(wpis.get("no", ""))
        if not rid or rid not in listy or rid in zajete:
            continue
        po = wpis.get("po")
        if not isinstance(po, int):
            continue
        zajete.add(rid)
        przy.setdefault(po, []).append(rid)
    return przy


def _plik_scen(jednostki: list[Jednostka], pl: dict[str, str], zakres: str,
               statystyka: dict, ix=None,
               listy: dict[str, dict] | None = None,
               listy_przy: dict[int, list[str]] | None = None,
               surowe: dict[str, str] | None = None) -> tuple[list[str], set[str], set[str]]:
    out: list[str] = []
    uzyte: set[str] = set()
    zrobione: set[str] = set()
    ostatnia_sekcja = None
    listy = listy or {}
    listy_przy = listy_przy or {}
    surowe = surowe or {}
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
        if jednostka.wstep:
            out += [jednostka.wstep]   # wiersz „Interakcja: …” tuż nad nagłówkiem, bez pustej linii
        out.append(f"## {jednostka.etykieta}")
        out.extend(linie)
        out.append("")
        zrobione.add(jednostka.etykieta)
        if jednostka.rodzaj == "scena" and jednostka.numer in listy_przy:
            for rid in listy_przy[jednostka.numer]:
                wpis = listy.get(rid)
                if not wpis:
                    continue
                out.extend(_karta_listu(wpis, pl, surowe, ix))
                uzyte.update(wpis.get("klucze") or [])
    return out, uzyte, zrobione


@dataclass
class PoleHasla:
    """Jedno pole hasła w 02: kolumna tabeli + tekst do wypisania."""

    tekst: str
    tabela: str
    kolumna: str
    wiersz: str
    klucz: str


# Kolejność pól na karcie (niżej = później). Questy: 50 + numer zadania.
_KOLUMNA_KOLEJNOSC = {
    "locate_describe": 10,
    "backing_area": 11,
    "describe_str": 20,
    "brief_describe_str": 21,
    "describe": 22,
    "introduction": 23,
    "introduction_short": 24,
    "story_describe_str": 30,
    "description": 31,
    "introduction_long": 32,
    "shiyi_show_word": 40,
    "extra_describe_1": 45,
    "shiyi_show_word_from": 80,
}
_POMIJANE_KOLUMNY = frozenset({
    "buff_detail", "unlock_dialog_new_word", "shiyi_discr_l", "shiyi_pic_from",
    "bowu_father_name", "story_name",
})


def _numer_wiersza(wiersz: str) -> int:
    try:
        return int(str(wiersz))
    except (TypeError, ValueError):
        return 0


def _waga_pola(pole: PoleHasla) -> tuple:
    """Kolejność na karcie: lokalizacja → definicja → treść; questy po id zadania."""
    if pole.kolumna == "task_target_str":
        return (50, _numer_wiersza(pole.wiersz), 0)
    if pole.kolumna == "task_desc_str":
        return (50, _numer_wiersza(pole.wiersz), 1)
    return (_KOLUMNA_KOLEJNOSC.get(pole.kolumna, 70), _numer_wiersza(pole.wiersz), 0)


def _karta_hasla(nazwa: str, pola: list[PoleHasla]) -> list[str]:
    """Hasło wielolinijkowe: tytuł, potem każde pole osobno (bez ` · `)."""
    if not pola:
        return [f"**{nazwa}**"]
    kolumny = {p.kolumna for p in pola}
    # `extra_describe_1` bez lokalizacji to zwykle podpowiedź questa, nie treść hasła
    if "extra_describe_1" in kolumny and "locate_describe" not in kolumny:
        pola = [p for p in pola if p.kolumna != "extra_describe_1"]
    pola = sorted(pola, key=_waga_pola)
    linie = [f"**{nazwa}**"]
    widziane: set[str] = set()
    for pole in pola:
        if pole.tekst in widziane:
            continue
        widziane.add(pole.tekst)
        linie.append(pole.tekst)
    return linie


def _haslo(nazwa: str, opisy: list[str]) -> list[str]:
    """Zostawione dla testów syntetycznych: opisy bez kolumn, w podanej kolejności."""
    pola = [PoleHasla(tekst, "", f"_{i}", "", "") for i, tekst in enumerate(opisy)]
    return _karta_hasla(nazwa, pola)


def _sekcja_zadan(opisy: dict[str, list[str]], klucze_nazw: dict[str, str], ix, pl,
                  krainy: list[dict] | None, luzne: list[str] | None = None) -> list[str]:
    """Sekcja „Zadania i wątki” w kolejności łańcucha gry, nie alfabetycznie.

    `luzne` to linie bez hasła z tej samej kategorii: gdy któraś jest nazwą
    zadania z planu (zadanie ma przetłumaczoną nazwę, ale żadnego opisu),
    staje pod nagłówkiem swojego rozdziału/łańcucha i znika z listy — reszta
    zostaje w `luzne` do wypisania po sekcji.
    """
    z_klucza: dict[str, str] = {}
    for nazwa, klucz in klucze_nazw.items():
        z_klucza.setdefault(klucz, nazwa)
    dostepne: set[str] = set(luzne or ())
    out: list[str] = []
    wypisane: set[str] = set()
    for blok in kolejnosc_zadan.plan(ix, pl, krainy):
        linie = []
        for klucz in blok.klucze:
            nazwa = z_klucza.get(klucz)
            if nazwa and nazwa not in wypisane and nazwa in opisy:
                wypisane.add(nazwa)
                linie.extend(_karta_z_opisow(nazwa, opisy[nazwa]))
                continue
            tekst = pl.get(klucz)
            if tekst and tekst in dostepne and tekst not in wypisane:
                wypisane.add(tekst)
                dostepne.discard(tekst)
                linie.append(tekst)
        if linie:
            out += [f"## {blok.tytul}", ""] + linie + [""]
    if luzne is not None:
        luzne[:] = [linia for linia in luzne if linia in dostepne]
    reszta = [nazwa for nazwa in sorted(opisy, key=str.lower) if nazwa not in wypisane]
    if reszta:
        out += ["## Pozostałe zadania i wątki", ""]
        for nazwa in reszta:
            out.extend(_karta_z_opisow(nazwa, opisy[nazwa]))
        out.append("")
    return out


def _karta_z_opisow(nazwa: str, opisy) -> list[str]:
    """Opisy to lista `PoleHasla` albo starych napisów."""
    if opisy and isinstance(opisy[0], PoleHasla):
        return _karta_hasla(nazwa, list(opisy))
    return _haslo(nazwa, list(opisy))


def _opis_powtarza_nazwe(tekst: str, nazwa: str) -> bool:
    """Czy opis nie mówi nic ponad nazwę hasła.

    Odpada opis równy nazwie (z dokładnością do końcowej interpunkcji) albo
    będący jej urywkiem. Opis, który nazwę ZAWIERA, ale dodaje własną treść
    („Prosty drewniany pierścień jue, nic szczególnego.”), zostaje — dawny
    warunek `nazwa not in tekst` wycinał każdy opis zaczynający się nazwą.
    """
    return tekst.strip(" .!?…") == nazwa.strip(" .!?…") or tekst in nazwa


def _wczytaj_bowu_story(katalog: str | Path) -> dict[str, list[str]]:
    """`bowu_no_to_story_no` z wyciągu: numer hasła encyklopedii → akty regionalne."""
    p = Path(katalog) / "bowu_story.jsonl"
    if not p.exists():
        return {}
    mapa: dict[str, list[str]] = {}
    with p.open(encoding="utf-8") as f:
        for linia in f:
            if not linia.strip():
                continue
            r = json.loads(linia)
            mapa[str(r["bowu"])] = [str(s) for s in r["story"]]
    return mapa


def _dolacz_lokalizacje_bowu(hasla: dict, ix, pl: dict[str, str],
                             bowu_story: dict[str, list[str]] | None) -> None:
    """Lokalizacja aktu regionalnego na kartę hasła (`bowu_no_to_story_no`).

    `region_story_act_data.backing_area` wisi na aktywności (np. 901 →
    `c26378213d93f8f7` Zawody łucznicze), nie na haśle encyklopedii.
    Tabela `bowu_no_to_story_no` (832009 → 901) i `region_story_act_data.bowu_no`
    to twarde mapowanie z gry: to samo miejsce trafia na kartę 白鸟射羿.
    """
    if bowu_story is None:
        katalog = getattr(ix, "katalog", None)
        bowu_story = _wczytaj_bowu_story(katalog) if katalog else {}
    if not bowu_story:
        return
    story_do_bowu: dict[str, list[str]] = {}
    for bowu, stories in bowu_story.items():
        for s in stories:
            story_do_bowu.setdefault(str(s), []).append(str(bowu))
    bowu_do_klucza: dict[str, str] = {}
    for name_key, wpis in hasla.items():
        for p in wpis["pola"]:
            if p.wiersz in bowu_story:
                bowu_do_klucza[p.wiersz] = name_key
    if not bowu_do_klucza:
        return
    for klucz, tekst in ix.teksty.items():
        if not tekst.w or len(tekst.w) < 2:
            continue
        zrodlo = ix.zrodlo(tekst)
        if not zrodlo or zrodlo[1] != "backing_area":
            continue
        story = str(tekst.w[1])
        tekst_pl = pl.get(klucz) or ""
        if not tekst_pl:
            surowe = _z_gry(ix, klucz)
            if not surowe:
                continue
            tekst_pl = GWIAZDKA + surowe
        for bowu in story_do_bowu.get(story, ()):
            nk = bowu_do_klucza.get(bowu)
            if not nk:
                continue
            wpis = hasla[nk]
            if any(p.klucz == klucz for p in wpis["pola"]):
                continue
            wpis["pola"].append(PoleHasla(
                tekst_pl, zrodlo[0], "backing_area", story, klucz))
            wpis["etykiety"].add(_kategoria(zrodlo[0]))


def _reszta(ix, pl, uzyte: set[str], statystyka: dict,
            krainy: list[dict] | None = None,
            bowu_story: dict[str, list[str]] | None = None) -> list[str]:
    """Co nie trafiło do 01 — karty wielolinijkowe, pola w kolejności kolumn gry."""
    hasla: dict[str, dict] = {}   # klucz nazwy → {nazwa, pola, etykiety}
    bez_nazwy: dict[str, list[str]] = {}
    widziane_linie: dict[str, set[str]] = {}

    def _meta(klucz: str):
        tekst = ix.teksty.get(klucz)
        if tekst is None:
            return None
        zrodlo = ix.zrodlo(tekst) if tekst.w else None
        if zrodlo:
            tabela, kolumna = zrodlo[0], zrodlo[1]
            wiersz = str(tekst.w[1]) if len(tekst.w) > 1 else ""
            name_key = tekst.w[2] if len(tekst.w) > 2 and isinstance(tekst.w[2], str) else None
            if name_key is None and _NAZWA.search(kolumna or ""):
                name_key = klucz
            return tekst, tabela, kolumna, wiersz, name_key
        # fixture'y bez `zrodla.json`; kwestie z `w=None` (Feng 52264b…)
        if tekst.w:
            numer = tekst.w[0]
            try:
                tabela = ix.zrodla[numer][0]
            except (KeyError, IndexError, TypeError):
                tabela = str(numer)
            wiersz = str(tekst.w[1]) if len(tekst.w) > 1 else ""
            name_key = (tekst.w[2] if len(tekst.w) > 2 and isinstance(tekst.w[2], str)
                        else None)
            return tekst, tabela, "", wiersz, name_key
        return tekst, "", "", "", None

    for klucz, tekst_pl in pl.items():
        if klucz in uzyte:
            continue
        meta = _meta(klucz)
        if meta is None:
            continue
        _t, tabela, kolumna, wiersz, name_key = meta
        etykieta = _kategoria(tabela)
        statystyka["reszta"] += 1
        if not name_key or _NAZWA.search(kolumna or ""):
            if not name_key:
                zbior = widziane_linie.setdefault(etykieta, set())
                if len(tekst_pl) >= 4 and tekst_pl not in zbior:
                    zbior.add(tekst_pl)
                    bez_nazwy.setdefault(etykieta, []).append(tekst_pl)
            else:
                wpis = hasla.setdefault(name_key, {"nazwa": "", "pola": [], "etykiety": set()})
                wpis["nazwa"] = wpis["nazwa"] or pinyin_slownik.romanizuj(
                    _nazwa_klucza(ix, name_key, pl))
                wpis["etykiety"].add(etykieta)
            continue
        if kolumna in _POMIJANE_KOLUMNY:
            continue
        nazwa = pinyin_slownik.romanizuj(_nazwa_klucza(ix, name_key, pl))
        if not nazwa or _opis_powtarza_nazwe(tekst_pl, nazwa):
            continue
        wpis = hasla.setdefault(name_key, {"nazwa": nazwa, "pola": [], "etykiety": set()})
        wpis["nazwa"] = wpis["nazwa"] or nazwa
        wpis["etykiety"].add(etykieta)
        wpis["pola"].append(PoleHasla(tekst_pl, tabela, kolumna, wiersz, klucz))

    # lokalizacja bywa nieprzetłumaczona — i tak wchodzi na kartę (z gwiazdką)
    for klucz, tekst in ix.teksty.items():
        if klucz in uzyte or klucz in pl:
            continue
        zrodlo = ix.zrodlo(tekst)
        if not zrodlo or zrodlo[1] not in ("locate_describe", "backing_area"):
            continue
        if len(tekst.w) < 3 or not isinstance(tekst.w[2], str):
            continue
        name_key = tekst.w[2]
        wpis = hasla.get(name_key)
        if not wpis:
            continue
        surowe = _z_gry(ix, klucz)
        if not surowe:
            continue
        wpis["pola"].append(PoleHasla(GWIAZDKA + surowe, zrodlo[0], zrodlo[1],
                                      str(tekst.w[1]), klucz))
        wpis["etykiety"].add(_kategoria(zrodlo[0]))

    _dolacz_lokalizacje_bowu(hasla, ix, pl, bowu_story)

    def _etykieta_hasla(wpis: dict) -> str:
        etykiety = wpis["etykiety"]
        kolumny = {p.kolumna for p in wpis["pola"]}
        if kolumny & {"task_target_str", "task_desc_str"}:
            return "Zadania i wątki"
        if "Encyklopedia, księgi i poszlaki" in etykiety:
            return "Encyklopedia, księgi i poszlaki"
        if "Przedmioty, stroje i tytuły" in etykiety:
            return "Przedmioty, stroje i tytuły"
        return next(iter(sorted(etykiety))) if etykiety else "Pozostałe teksty"

    sekcje: dict[str, dict[str, list[PoleHasla]]] = {}
    klucze_nazw: dict[str, str] = {}
    for name_key, wpis in hasla.items():
        nazwa = wpis["nazwa"]
        if not nazwa:
            continue
        etykieta = _etykieta_hasla(wpis)
        # homonimy (dwa „Łucznictwo”) zostają osobnymi kartami
        etykieta_unikalna = nazwa
        if etykieta_unikalna in sekcje.get(etykieta, {}):
            etykieta_unikalna = f"{nazwa}\u200b{name_key[:6]}"
        sekcje.setdefault(etykieta, {})[etykieta_unikalna] = wpis["pola"]
        klucze_nazw[etykieta + "\x00" + etykieta_unikalna] = name_key

    out: list[str] = []
    for etykieta in sorted(set(sekcje) | set(bez_nazwy)):
        out += [f"# {etykieta}", ""]
        if etykieta == "Zadania i wątki" and sekcje.get(etykieta):
            wlasne = {klucz.split("\x00", 1)[1]: wartosc
                      for klucz, wartosc in klucze_nazw.items()
                      if klucz.startswith(etykieta + "\x00")}
            luzne = sorted(bez_nazwy.get(etykieta, []), key=str.lower)
            out += _sekcja_zadan(sekcje[etykieta], wlasne, ix, pl, krainy, luzne)
            out.extend(luzne)
            out.append("")
            continue
        for nazwa in sorted(sekcje.get(etykieta, {}), key=lambda n: n.rstrip("\u200b0123456789abcdef").lower()):
            karta = _karta_hasla(nazwa.split("\u200b")[0], sekcje[etykieta][nazwa])
            out.extend(karta)
        out.extend(sorted(bez_nazwy.get(etykieta, []), key=str.lower))
        out.append("")
    return out


def zbuduj(*, index: str, magazyn: str, wyj: Path, zakres: str) -> dict:
    ix = indeks_mod.wczytaj(index, teksty=True, sceny=True)
    surowe = _magazyn(Path(magazyn), Path(index), czysc=False)
    pl = {klucz: _czysty(tekst) for klucz, tekst in surowe.items()}
    porzadek = _wczytaj_porzadek(index)
    chronologia = chronologia_mod.wczytaj(index)
    krainy = json.loads((Path(index) / "prowincje.json").read_text(encoding="utf-8"))

    wyj.mkdir(parents=True, exist_ok=True)
    statystyka = {"jednostek": 0, "linii": 0, "pominiete": 0, "reszta": 0, "plikow": 0,
                  "bez_przekladu": 0}

    listy = _wczytaj_listy(ix)
    listy_przy = _przypisz_listy_do_scen(ix, listy, index)
    jednostki = _jednostki_z_chronologii(ix, pl, porzadek, chronologia, krainy, index)
    tresc, uzyte, _zrobione = _plik_scen(
        jednostki, pl, zakres, statystyka, ix,
        listy=listy, listy_przy=listy_przy, surowe=surowe)
    pliki_scen, opisy_scen = _zapisz_czesci(
        wyj, "01_sceny_i_cutsceny", "Sceny i cutsceny",
        "Prolog i krainy po kolei (sceny i cutsceny przemieszane), "
        "pieśni na końcu, bo w grze nie ma ich na początku: "
        "sceny i cutsceny przemieszane w kolejności występowania.",
        tresc, statystyka)

    # Wszystkie klucze listów wychodzą z „encyklopedii”: albo przy scenie, albo w # Listy.
    for wpis in listy.values():
        uzyte.update(wpis.get("klucze") or [])
    nieprzypisane = [rid for rid in sorted(listy, key=lambda r: _tytul_listu(listy[r], pl, ix).lower())
                     if rid not in {x for grupa in listy_przy.values() for x in grupa}]
    tresc_reszty: list[str] = []
    if nieprzypisane:
        tresc_reszty += ["# Listy", ""]
        for rid in nieprzypisane:
            tresc_reszty += _karta_listu(listy[rid], pl, surowe, ix)
        statystyka["reszta"] += len(nieprzypisane)
    tresc_reszty += _reszta(ix, pl, uzyte, statystyka, krainy)
    tresc_reszty += _zbiory(ix, pl, uzyte, statystyka)
    tresc_reszty += _pamiatki(ix, pl, uzyte, statystyka, index)
    tresc_reszty += _poi(ix, pl, uzyte, statystyka, index)
    pliki_reszty, opisy_reszty = _zapisz_czesci(
        wyj, "02_reszta", "Reszta",
        "Komplet informacji dodatkowych: wszystkie przekłady, "
        "których nie ma w pliku 01, pogrupowane rodzajem.",
        tresc_reszty, statystyka)

    (wyj / "README.md").write_text(
        _readme(statystyka, zakres, pliki_scen, opisy_scen, pliki_reszty, opisy_reszty),
        encoding="utf-8")
    statystyka["plikow"] += 1
    return statystyka


def _naglowek(tytul: str, opis: str) -> str:
    return f"# Where Winds Meet — {tytul}\n\n{opis}\n\n"


# Krótkie etykiety sekcji (`# …`) do tytułu części — np. „01 - prolog, Yannan” albo „02 - przedmioty”.
# Krainy i inne sekcje z formy „# Nazwa — polski odpowiednik” biorą człon po
# ostatnim myślniku (tam leży polska nazwa).
_KROTKIE_SEKCJE = {
    "Prolog": "prolog",
    "Pieśni": "pieśni",
    "Sceny bez przypisanej mapy": "sceny bez mapy",
    "Cutsceny bez grupy zadań": "cutsceny bez grupy",
    "Napisy przerywników": "napisy przerywników",
    "Napisy przerywników — kolejność z pliku gry (bez numeru cutsceny)": "napisy przerywników",
    "Zadania i wątki": "zadania",
    "Encyklopedia, księgi i poszlaki": "kompendium",
    "Listy": "listy",
    "Przedmioty, stroje i tytuły": "przedmioty",
    "Sztuki walki i umiejętności": "sztuki walki",
    "Walka i przeciwnicy": "walka",
    "Świat, sekty i miejsca": "świat i miejsca",
    "Postacie i relacje": "postacie",
    "Interfejs i komunikaty": "interfejs",
    "Pozostałe teksty": "pozostałe",
    "Zbiory i pamiątki — zasłyszane historie": "historie zasłyszane",
    "Zbiory i pamiątki — karty przeciwników": "karty przeciwników",
    "Pamiątki — przedmioty z historią": "pamiątki",
    "Punkty na mapie (POI)": "POI",
}
_CIAG_DALSZY = re.compile(r"\s*\(ciąg dalszy\)\s*$")


def _etykieta_sekcji(linia: str) -> str:
    """Krótka etykieta nagłówka `# …` do tytułu części: „# 清河 — Qinghe - ostatnia iluzja” → „Qinghe”."""
    tekst = linia[1:].strip()
    tekst = _CIAG_DALSZY.sub("", tekst).strip()
    krotka = _KROTKIE_SEKCJE.get(tekst)
    if krotka:
        return krotka
    if " — " in tekst:                      # „# 清河 — Qinghe - …” → czas po polsku
        tekst = tekst.rsplit(" — ", 1)[-1].strip()
    for separator in (", ", " - ", " ("):     # dopisek po nazwie: utnij przy pierwszym separatorze
        if separator in tekst:
            tekst = tekst.split(separator, 1)[0].strip()
            break
    if tekst.startswith("Mapa "):            # „Mapa Yannan” → „Yannan”
        tekst = tekst[len("Mapa "):].strip()
    return tekst


def _opis_czesci(czesc: list[str], maks: int = 5) -> str:
    """Krótka lista sekcji w części, w kolejności występowania („prolog, Yan Nan, Qinghe”)."""
    etykiety: list[str] = []
    for linia in czesc:
        if not linia.startswith("# "):
            continue
        etykieta = _etykieta_sekcji(linia)
        if etykieta and etykieta not in etykiety:
            etykiety.append(etykieta)
    if not etykiety:
        return ""
    if len(etykiety) > maks:
        return ", ".join(etykiety[:maks]) + ", …"
    return ", ".join(etykiety)


# Budżet jednej części pliku treści: pliki po kilkanaście megabajtów są
# nieporęczne w podglądzie, więc tniemy na części po ~2,5 MB — najchętniej
# na granicy sekcji (`# `) albo jednostki (`## `), nigdy w środku dialogu.
_CZESC_BUDZET = 2_500_000


def _czesci(linie: list[str], budzet: int = _CZESC_BUDZET) -> list[list[str]]:
    """Tnie treść na części po ~`budzet` bajtów, na logicznych granicach.

    Całość w budżecie → jedna część (plik zostaje pod starą nazwą).
    Granice w kolejności chęci: nagłówek (`# `/`## `) zaraz po przekroczeniu
    budżetu; hasło (`**…`) lub linia po pustej, gdy nagłówka długo nie ma
    (listy w 02); dowolna linia dopiero przy podwójnym zapasie. Gdy cięcie
    wypada w środku sekcji (`# `), nowa część dostaje powtórzony nagłówek
    sekcji z dopiskiem „(ciąg dalszy)”, żeby było widać, skąd pochodzi tekst.
    Wiersz „Interakcja: …” nigdy nie zostaje sam na końcu części przed
    `## Scena …` — przechodzi na początek nowej części razem ze sceną.
    """
    czesci: list[list[str]] = []
    biezaca: list[str] = []
    bajty = 0
    sekcja = ""
    poprzednia = ""
    # Sekcje list (02) nie mają nagłówków w środku: po przekroczeniu budżetu
    # o `zapas` wolno ciąć na haśle (`**…`) albo po pustej linii, a po
    # podwójnym zapasie — na dowolnej linii, żeby część nie rosła bez końca.
    zapas = max(budzet // 10, 1)
    for linia in linie:
        if linia.startswith("# "):
            sekcja = linia
        naglowek = linia.startswith("# ") or linia.startswith("## ")
        # Cięcie na haśle (`**Tytuł**`), nie na akapicie karty po pustej linii.
        luzna = linia.startswith("**")
        tnij = biezaca and bajty > budzet and (
            naglowek
            or (bajty > budzet + zapas and luzna)
            or bajty > budzet + 2 * zapas)
        if tnij:
            # Wiersz „Interakcja: …” należy do sceny pod nim — przy cięciu
            # na `## ` razem z nią przechodzi na początek nowej części.
            przesun = ""
            if poprzednia.startswith("Interakcja: ") and biezaca and biezaca[-1] == poprzednia:
                przesun = biezaca.pop()
            czesci.append(biezaca)
            biezaca = []
            bajty = 0
            if sekcja and not linia.startswith("# "):
                biezaca = [sekcja[:2] + sekcja[2:].strip() + " (ciąg dalszy)", ""]
                bajty = len(biezaca[0].encode("utf-8")) + 2
            if przesun:
                biezaca.append(przesun)
                bajty += len(przesun.encode("utf-8")) + 1
        biezaca.append(linia)
        bajty += len(linia.encode("utf-8")) + 1
        poprzednia = linia
    if biezaca:
        czesci.append(biezaca)
    return czesci


# Znaki niedozwolone w nazwach plików (Windows) — zastępujemy myślnikiem;
# kropki i spacje na końcu nazwy są też niedozwolone w Windows.
_ZABRONIONE_W_NAZWIE = re.compile(r'[\\/:*?"<>|\x00-\x1f]')


def _nazwa_pliku_czesci(tytul_czesci: str) -> str:
    """Nazwa pliku części = tytuł części (bez „Where Winds Meet — ”), z `.md`."""
    nazwa = _ZABRONIONE_W_NAZWIE.sub("-", tytul_czesci).strip().rstrip(". ")
    return nazwa + ".md"


def _zapisz_czesci(wyj: Path, baza: str, tytul: str, opis: str,
                   linie: list[str], statystyka: dict) -> tuple[list[str], list[str]]:
    """Zapisuje treść w jednej lub kilku częściach.

    Zwraca (nazwy plików, opisy części). Przy podziale tytuł części opisuje
    jej zawartość (np. `02 - przedmioty — część 2 z 3`), a **nazwa pliku to
    ten tytuł** (np. `02 - przedmioty — część 2 z 3.md`).
    Przy jednym pliku zostaje zwykły tytuł bazowy i stara nazwa `baza.md`.
    """
    czesci = _czesci(linie)
    numer_baza = baza.split("_", 1)[0]
    nazwy: list[str] = []
    opisy: list[str] = []
    for numer, czesc in enumerate(czesci, start=1):
        if len(czesci) == 1:
            nazwa, tytul_czesci, opis_czesci = f"{baza}.md", tytul, ""
        else:
            opis_czesci = _opis_czesci(czesc)
            tytul_czesci = f"{numer_baza} - {opis_czesci}" if opis_czesci else tytul
            tytul_czesci += f" — część {numer} z {len(czesci)}"
            nazwa = _nazwa_pliku_czesci(tytul_czesci) if opis_czesci else f"{baza}_{numer:02d}.md"
        (wyj / nazwa).write_text(
            _naglowek(tytul_czesci, opis) + "\n".join(czesc) + "\n",
            encoding="utf-8")
        statystyka["plikow"] += 1
        nazwy.append(nazwa)
        opisy.append(opis_czesci)
    return nazwy, opisy


def _wiersze_readme(pliki: list[str], opis: str, szczegoly: list[str] | None = None) -> str:
    """Wiersze tabeli README: jeden plik albo kolejne części z numeracją.

    `szczegoly` to opisy części z `_zapisz_czesci` — każdy wiersz pokazuje,
    co dana część zawiera.
    """
    if len(pliki) == 1:
        return f"| `{pliki[0]}` | {opis} |"
    return "\n".join(
        f"| `{nazwa}` | {(szczegoly or [''] * len(pliki))[numer - 1] or opis}"
        f" — część {numer} z {len(pliki)} |"
        for numer, nazwa in enumerate(pliki, start=1))


def _readme(statystyka: dict, zakres: str,
            pliki_scen: list[str], opisy_scen: list[str],
            pliki_reszty: list[str], opisy_reszty: list[str]) -> str:
    return f"""# Czytanka Where Winds Meet

| plik | zawartość |
|---|---|
{_wiersze_readme(pliki_scen, "sceny i cutsceny razem, chronologicznie: prolog, krainy po kolei, pieśni na końcu", opisy_scen)}
{_wiersze_readme(pliki_reszty, "komplet informacji dodatkowych: wszystkie przekłady spoza 01 (przedmioty, encyklopedia, kompendium itd.), pogrupowane rodzajem", opisy_reszty)}

Pliki treści cięte są na części po ~2,5 MB (granice tylko na nagłówkach sekcji
i jednostek; sekcja przecięta w środku zaczyna kolejną część nagłówkiem
z dopiskiem „(ciąg dalszy)”), bo wielkich plików nie da się wygodnie przeglądać.
Tytuł i nazwa pliku każdej części nazywają jej zawartość (np. „01 - prolog, Yannan —
część 1 z 8.md” albo „02 - sztuki walki, walka, zadania, świat i miejsca, historie
zasłyszane, … — część 3 z 3.md”), a w tabeli wyżej przy każdej części stoi krótka
lista jej sekcji.

Kwestie w 01: `**Mówca:** tekst`, jedna kwestia na linię, bez punktora, czasów
i tabel; kwestia bez mówcy to goły tekst.
Gracz zawsze jako **Youxia**. Kwestie bez polskiego przekładu stoją z gwiazdką
(`\\*Fate is already sealed.`), więc widać, gdzie tłumaczenia jeszcze nie ma.
Etykiety mówców zapisane w grze tylko po chińsku są transliterowane na łacinkę
(`大祭师` → `Da Ji Shi`), bo tłumaczenia tych nazw gra nie ma.
Zakres: **{zakres}**.

Statystyka: {statystyka['jednostek']} jednostek, {statystyka['linii']} kwestii,
{statystyka['reszta']} pozycji w reszcie,
{statystyka['pominiete']} kwestii bez polskiego pominięto,
{statystyka['bez_przekladu']} kwestii stoi z gwiazdką, bo przekładu jeszcze nie ma,
{statystyka.get('zbiory', 0)} kart zbiorów, {statystyka.get('pamiatki', 0)} pamiątek (przedmiotów z historią) i {statystyka.get('poi', 0)} punktów na mapie (POI — z tego {statystyka.get('poi_z_dialogiem', 0)} z potwierdzonym numerem sceny) w pliku 02.

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
