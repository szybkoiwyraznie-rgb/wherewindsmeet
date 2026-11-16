#!/usr/bin/env python3
"""Chronologia Where Winds Meet — jedna, stała lista jednostek zapisana w repo.

Po co to jest: kolejność scen i cutscen w grze ma być **raz ustalona i zapisana
w repozytorium**, żeby czytanki i łatki nie układały jej od nowa w każdej sesji
i żeby nie zależały od niczego spoza gita.

Wejście (wszystko z repo): `index/` (wyciąg z gry), `index/prowincje.json`
(kolejność krain), `zwrotki/prolog_transkrypt_z_gry.txt` (transkrypt właściciela,
zapisany w repo). Wyjście: `index/chronologia.jsonl` — po jednej jednostce
w wierszu, w kolejności występowania w grze:

    {"p": 0, "t": "film", "n": 1, "s": "Pieśni"}
    {"p": 1, "t": "prolog", "s": "Prolog", "e": "Pierwsza cutscena", "k": [...]}
    {"p": 2, "t": "cutscena", "n": 30033, "s": "燕南", "k": ["..."]}
    {"p": 3, "t": "scena", "n": 10094, "s": "燕南"}

Zasady kolejności (te same, co w ustaleniach):

1. filmy i pieśni (1–3) — na końcu, bo w grze nie ma ich na początku,
2. prolog w kolejności transkryptu — napisy i dialogi przemieszane,
3. krainy w kolejności odwiedzania, w krainie sceny po numerze dialogu,
4. cutsceny **przypisane do grupy zadań** (tabela powtórek: `no` → `grupa`,
   a grupa ma zakres numerów dialogów) stoją przy scenie, od której ta grupa
   się zaczyna — dzięki temu przerywniki są przemieszane ze scenami, choć same
   nie mają numeru dialogu,
5. cutsceny bez grupy zadań stoją na końcu, w kolejności własnych numerów
   (sekcja „Cutsceny bez grupy zadań”) — nie udajemy, że znamy ich miejsce,
6. napisy przerywników (pula `text_msg`) trafiają do 01, nie do 03: te, których
   scenę da się rozpoznać po nazwie nagrania albo po sprawdzonej kotwicy, stoją
   **w swojej cutscenie** (pole `kn`, przed streszczeniem), a pozostałe — w sekcji
   „Napisy przerywników”, w kolejności wierszy z pliku gry.

Ten plik jest generowany, ale commitowany: test `tests/test_chronologia.py`
pilnuje, żeby po zmianie danych wygenerować go ponownie (`--sprawdz`), a nie
zmieniać ręcznie.

Użycie:
    python3 tools/chronologia.py                       # zapisz index/chronologia.jsonl
    python3 tools/chronologia.py --sprawdz             # tylko porównaj z zapisanym
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools import indeks as indeks_mod  # noqa: E402
from tools import kolejnosc_gry, prolog_z_klucza  # noqa: E402

BEZ_MAPY = "Sceny bez przypisanej mapy"
BEZ_GRUPY = "Cutsceny bez grupy zadań"
PULA_NAPISOW = "Napisy przerywników"
DOMYSLNY_PLIK = Path("index") / "chronologia.jsonl"

# Ile napisów bez nagrania może dołączyć do sceny, która zaczyna się za nimi.
# Napisy przerywników mają w plikach gry tylko identyfikator wiersza i nazwę
# nagrania (`vo_…_cs_<scena>_<numer>`); wiersze bez nagrania stoją w puli przed
# sceną, do której należą (tak jest np. z „Wodzu, obudź się!” przed kwestiami
# Ruby z `vo_sm_sxdm4_cs_zlxl_hx_02`).
ZASIEG_NAGRANIA = 25
_KOD_VO = re.compile(r"(vo_.+_cs_[a-z0-9_]+?)_\d+$")


def _kraina_scen(ix, krainy: list[dict]) -> tuple[dict[int, str], list[str]]:
    """Numer sceny → kraina oraz kolejność krain z gry."""
    mapa_kraina = {mapa: k["kraina"] for k in krainy for mapa in k["mapy"]}
    mapa_projektu: dict[str, dict[int, int]] = defaultdict(lambda: defaultdict(int))
    for scena in ix.sceny.values():
        projekt = str(scena.get("p") or "").split(".")[0]
        for mapa in scena.get("m") or []:
            mapa_projektu[projekt][mapa] += 1

    przypisanie: dict[int, str] = {}
    for numer, scena in ix.sceny.items():
        mapy = list(scena.get("m") or [])
        if not mapy:
            liczby = mapa_projektu.get(str(scena.get("p") or "").split(".")[0]) or {}
            if liczby:
                mapy = [max(liczby, key=liczby.get)]
        przypisanie[numer] = next((mapa_kraina[m] for m in mapy if m in mapa_kraina), BEZ_MAPY)
    kolejnosc = [k["kraina"] for k in krainy] + [BEZ_MAPY]
    return przypisanie, kolejnosc


def _zrodlo_tabeli(ix, klucz: str) -> str | None:
    """Nazwa tabeli, z której pochodzi tekst (np. `cutscene_text_oversea`)."""
    tekst = ix.teksty.get(klucz)
    zrodlo = ix.zrodlo(tekst) if tekst is not None else None
    return zrodlo[0] if zrodlo else None


def _prolog(index: str, magazyn: str) -> tuple[list[dict], set[int]]:
    """Prolog w kolejności transkryptu: sekcje z nagłówków, w środku klucze tekstów.

    Linia transkryptu, która nie jest kwestią, bywa streszczeniem cutsceny
    (`cutscenes.synopsis_text_mobile`). Wtedy w tym miejscu wchodzi jednostka
    `cutscena` — tak streszczenie „Robak przelatuje i wnika w zwłoki…” trafia
    między Prolog 3 i Prolog 4, zamiast wylądować na końcu pliku jako „scena bez
    przypisanej mapy”. Zwrócone numery cutscen są potem pomijane przy
    rozmieszczaniu cutscen w krainach, żeby nic nie stało dwa razy.
    """
    _ix, po_pl, po_en = prolog_z_klucza._mapy(index, magazyn)
    porzadek: dict[str, list[dict]] = defaultdict(list)
    for wiersz in kolejnosc_gry.wczytaj(Path(index)):
        if wiersz.get("k"):
            porzadek[wiersz["k"]].append(wiersz)
    linie = Path(prolog_z_klucza.TRANSKRYPT).read_text(encoding="utf-8-sig").splitlines()

    # klucz streszczenia → numer cutsceny; transkrypt jest po polsku, więc
    # szukamy wśród kandydatów dopasowanych po polskim i angielskim tekście
    cutscena_streszczenia: dict[str, int] = {}
    for no, przerywnik in _ix.przerywniki.items():
        if przerywnik.get("streszczenie"):
            cutscena_streszczenia.setdefault(przerywnik["streszczenie"], no)

    jednostki: list[dict] = []
    uzyte_cutsceny: set[int] = set()
    numer = 0
    czesc = 0
    po_banerze = False             # sekcję otworzyła tabliczka krainy, nie nagłówek                      # ile jednostek dana sekcja transkryptu już dała
    etykieta, klucze = "Prolog", []

    def zamknij(etykieta: str, klucze: list[str]) -> None:
        if klucze:
            jednostki.append({"t": "prolog", "s": "Prolog", "e": etykieta, "k": klucze})

    for rodzaj, tekst in prolog_z_klucza._przejscie(linie):
        if rodzaj == "#":
            zamknij(etykieta if czesc == 0 else f"{etykieta} (ciąg dalszy)", klucze)
            if po_banerze:
                po_banerze = False   # tabliczka już policzyła tę sekcję
            else:
                numer += 1
            czesc = 0
            # nagłówki transkryptu to komentarze właściciela, nie nazwy scen —
            # w chronologii sekcje prologu są po prostu numerowane
            etykieta, klucze = f"Prolog {numer}", []
            continue
        # „QINGHE - VERDANT WILDS” w transkrypcie to tabliczka krainy
        # (`cutscene_text_oversea`), a nie kwestia — otwiera nową sekcję prologu
        if any(_zrodlo_tabeli(_ix, k) == "cutscene_text_oversea"
               for k in prolog_z_klucza._kandydaci(tekst, po_pl, po_en)):
            zamknij(etykieta if czesc == 0 else f"{etykieta} (ciąg dalszy)", klucze)
            numer += 1
            czesc = 0
            po_banerze = True
            etykieta, klucze = f"Prolog {numer}", []
            continue
        klucz = prolog_z_klucza._dopasuj(tekst, po_pl, po_en, porzadek)
        if not klucz:
            no = next((cutscena_streszczenia[k]
                       for k in prolog_z_klucza._kandydaci(tekst, po_pl, po_en)
                       if k in cutscena_streszczenia), None)
            if no is not None and no not in uzyte_cutsceny:
                klucz_streszczenia = _ix.przerywniki[no]["streszczenie"]
                if klucze:
                    czesc += 1
                    zamknij(etykieta if czesc == 1 else f"{etykieta} (ciąg dalszy)", klucze)
                    klucze = []
                jednostki.append({"t": "cutscena", "n": no, "s": "Prolog",
                                  "e": f"Cutscena {no}", "k": [klucz_streszczenia]})
                uzyte_cutsceny.add(no)
            continue
        if not klucze or klucze[-1] != klucz:
            # dwie linie transkryptu mogą trafić w ten sam wariant tekstu —
            # wtedy w grze to jedna kwestia, nie dwie
            klucze.append(klucz)
    if klucze:
        if numer == 0:
            numer = 1
            etykieta = "Prolog 1"
        zamknij(etykieta if czesc == 0 else f"{etykieta} (ciąg dalszy)", klucze)
    return jednostki, uzyte_cutsceny


def _cutsceny(ix, pomijane: set[int] | None = None) -> tuple[dict[int, list[dict]], list[dict]]:
    """Cutsceny rozdzielone na przypisane do grup zadań i pozostałe.

    `pomijane` to cutsceny, które już stoją w prologu (streszczenie z transkryptu) —
    nie mogą się powtórzyć w krainach.
    """
    pomijane = pomijane or set()
    przerywniki = ix.przerywniki
    grupy = ix.grupy
    powtorki = ix.cutsceny_kontekst.get("powtorka") or []

    grupa_cutsceny: dict[int, list[dict]] = defaultdict(list)
    for wiersz in powtorki:
        grupa = wiersz.get("grupa")
        no = wiersz.get("no")
        if grupa in grupy and no in przerywniki:
            grupa_cutsceny[grupa].append(wiersz)
    # kolejność w grupie: pozycja zadania, do którego cutscena należy, a nie numer
    for grupa, lista in grupa_cutsceny.items():
        kolejnosc = _kolejnosc_zadan(ix, grupa)
        lista.sort(key=lambda w: (kolejnosc.get(w.get("task_no"), len(kolejnosc)),
                                  w.get("no") or 0))

    przypisane: set[int] = set()
    jednostki_grup: dict[int, list[dict]] = defaultdict(list)
    for grupa, lista in sorted(grupa_cutsceny.items()):
        for wiersz in lista:
            no = wiersz["no"]
            if no in przypisane or no in pomijane:
                continue
            przypisane.add(no)
            jednostki_grup[grupa].append(_jednostka_cutsceny(no, przerywniki[no], grupa))

    reszta: list[dict] = []
    for no in sorted(przerywniki):
        if no not in przypisane and no not in pomijane:
            jednostka = _jednostka_cutsceny(no, przerywniki[no], None)
            if jednostka.get("k"):
                reszta.append(jednostka)
    return jednostki_grup, reszta


def _jednostka_cutsceny(no: int, przerywnik: dict, grupa: int | None) -> dict:
    klucze = [przerywnik[k] for k in ("tekst", "streszczenie") if przerywnik.get(k)]
    jednostka = {"t": "cutscena", "n": no, "k": klucze}
    if grupa is not None:
        jednostka["g"] = grupa
    return jednostka


def _kolejnosc_zadan(ix, grupa: int) -> dict[int, int]:
    """Numer zadania → jego pozycja w grupie (z `index/grupy_zadan.jsonl`)."""
    zadania = (ix.grupy.get(grupa) or {}).get("zadania") or []
    return {no: pozycja for pozycja, no in enumerate(zadania)}


def _kotwice_grup(ix, sceny: list[int]) -> dict[int, int]:
    """Grupa zadań → numer sceny, przy której grupa się zaczyna (kotwica wstawienia).

    Preferujemy scenę **z przypisaną mapą**: pierwsza scena grupy pochodzi zwykle
    z pliku dialogowego bez mapy (`luwenxin.dialog`), a wtedy cała grupa lądowała
    w sekcji „Sceny bez przypisanej mapy” zamiast w krainie. Gdy w grupie nie ma
    ani jednej sceny z mapą, zostaje stara reguła.
    """
    posortowane = sorted(sceny)
    z_mapa = [numer for numer in posortowane if (ix.sceny.get(numer) or {}).get("m")]
    kotwice: dict[int, int] = {}
    for grupa, dane in ix.grupy.items():
        start = dane.get("start")
        if not start:
            continue
        kotwica = next((numer for numer in z_mapa if numer >= start), None)
        if kotwica is None:
            kotwica = next((numer for numer in posortowane if numer >= start), None)
        if kotwica is not None:
            kotwice[grupa] = kotwica
    return kotwice


def _kod_vo(audio: str | None) -> str | None:
    """Kod sceny z nazwy nagrania: `vo_sm_sxdm4_cs_zlxl_hx_07` → `vo_…_cs_zlxl_hx`."""
    trafienie = _KOD_VO.match((audio or "").lower())
    return trafienie.group(1) if trafienie else None


def _pula_napisow(ix) -> list[dict]:
    """Napisy przerywników w kolejności wierszy z pliku gry (pula `text_msg`)."""
    wiersze = [w for w in (ix.cutsceny_kontekst.get("napis") or []) if w.get("k")]
    wiersze.sort(key=lambda w: w.get("wiersz") or 0)
    return wiersze


def _kody_napisow(wiersze: list[dict], kotwice: dict[int, tuple]) -> list[str | None]:
    """Kod sceny dla każdego napisu; napisy bez nagrania idą do sceny, która zaczyna się za nimi."""
    kody = [_kod_vo(w.get("audio")) for w in wiersze]
    wynik: list[str | None] = list(kody)
    for pozycja, kod in enumerate(kody):
        if kod is not None:
            continue
        for nastepny in range(pozycja + 1, min(pozycja + 1 + ZASIEG_NAGRANIA, len(wiersze))):
            if wiersze[nastepny].get("wiersz") in kotwice:
                break          # granica sprawdzona ręcznie — nie przechodzimy przez nią
            if kody[nastepny]:
                wynik[pozycja] = kody[nastepny]
                break
    # krótki ogon bez nagrań doklejamy do sceny przed nim; dłuższy ciąg to osobny blok
    pozycja = 0
    while pozycja < len(wynik):
        if wynik[pozycja]:
            pozycja += 1
            continue
        koniec = pozycja
        while koniec < len(wynik) and not wynik[koniec]:
            koniec += 1
        if pozycja and koniec - pozycja <= ZASIEG_NAGRANIA:
            poprzedni = wynik[pozycja - 1]
            for i in range(pozycja, koniec):
                wynik[i] = poprzedni
        pozycja = koniec
    return wynik


def _bloki_napisow(ix) -> list[dict]:
    """Pula napisów przerywników podzielona na sceny.

    W danych gry napis ma tylko identyfikator wiersza i nazwę nagrania; **nie ma
    numeru cutsceny**, do której należy (numer siedzi w osi czasu cutsceny, której
    wyciąg z gry nie obejmuje). Dlatego dzielimy pulę na bloki po sprawdzonych
    kotwicach scen (`kontekst_cutscen.KOTWICE_SCEN_TM`) i po zmianie kodu nagrania,
    a numer cutsceny przypisujemy tylko tam, gdzie kotwica lub prefiks nagrania
    podaje go wprost (`vo_sm_sxdm4_cs_zlxl` → 30161).
    """
    from tools import kontekst_cutscen as kc   # lokalnie: ten moduł ciągnie sporo wiedzy o mówcach

    wiersze = _pula_napisow(ix)
    if not wiersze:
        return []
    kotwice = kc.KOTWICE_SCEN_TM
    kody = _kody_napisow(wiersze, kotwice)

    bloki: list[dict] = []
    for wiersz, kod in zip(wiersze, kody):
        nowy = not bloki or wiersz["wiersz"] in kotwice or kod != bloki[-1]["kod"]
        if nowy:
            bloki.append({"start": wiersz["wiersz"], "koniec": wiersz["wiersz"],
                          "kod": kod, "klucze": []})
        blok = bloki[-1]
        blok["koniec"] = wiersz["wiersz"]
        blok["klucze"].append(wiersz["k"])

    for blok in bloki:
        kotwica = kotwice.get(blok["start"])
        domena = kc.dopasuj_domene_vo(blok["kod"]) if blok["kod"] else None
        if kotwica:
            blok["e"] = kotwica[0]
            blok["g"] = kotwica[1]
            blok["c"] = tuple(kotwica[2])
        elif domena:
            blok["e"] = domena[1]
            blok["g"] = domena[2]
            blok["c"] = tuple(domena[3])
        else:
            blok["e"] = (f"Napisy przerywnika — wiersze {blok['start']}–{blok['koniec']}"
                         if blok["start"] != blok["koniec"]
                         else f"Napisy przerywnika — wiersz {blok['start']}")
            blok["g"] = None
            blok["c"] = ()
    return bloki


def _przestrzen_cutscen(index: str | Path) -> dict[int, int]:
    """Cutscena → przestrzeń, w której film się odgrywa (`index/cutsceny_meta.jsonl`).

    Plik powstaje w `tools/cutsceny_z_bazy.py` z tabeli `cutscenes`
    (kolumna `cutscene_space_no`). Dzięki niemu cutscena, której scena-kotwica
    nie ma mapy, trafia do swojej krainy, a nie do sekcji „Sceny bez mapy”.
    """
    plik = Path(index) / "cutsceny_meta.jsonl"
    if not plik.exists():
        return {}
    mapa: dict[int, int] = {}
    with plik.open(encoding="utf-8") as f:
        for linia in f:
            if not linia.strip():
                continue
            wiersz = json.loads(linia)
            no, przestrzen = wiersz.get("no"), wiersz.get("przestrzen")
            if isinstance(no, int) and isinstance(przestrzen, int) and not isinstance(przestrzen, bool):
                mapa[no] = przestrzen
    return mapa


def _napisy_z_bazy(index: str | Path) -> dict[int, list[str]]:
    """Cutscena → jej napisy z `index/cutsceny_napisy.jsonl`.

    Plik powstaje w `tools/cutsceny_z_bazy.py`, gdy w bazie gry znajdzie się
    tabela wiążąca napis z cutsceną. Dopóki go nie ma, napisy idą do bloków
    scen (patrz `_bloki_napisow`).
    """
    plik = Path(index) / "cutsceny_napisy.jsonl"
    if not plik.exists():
        return {}
    mapa: dict[int, list[str]] = defaultdict(list)
    with plik.open(encoding="utf-8") as f:
        for linia in f:
            if not linia.strip():
                continue
            wiersz = json.loads(linia)
            if wiersz.get("no") is None or not wiersz.get("k"):
                continue
            mapa[int(wiersz["no"])].append(wiersz["k"])
    return dict(mapa)


def zbuduj(*, index: str = "index", magazyn: str = "tlumaczenie", wyj: Path = DOMYSLNY_PLIK) -> dict:
    ix = indeks_mod.wczytaj(index, teksty=True, sceny=True)
    krainy = json.loads((Path(index) / "prowincje.json").read_text(encoding="utf-8"))
    przypisanie, kolejnosc_krain = _kraina_scen(ix, krainy)

    jednostki: list[dict] = []

    filmy: set[int] = set()
    for wiersz in kolejnosc_gry.wczytaj(Path(index)):
        if wiersz.get("z") == "film" and wiersz.get("d") is not None:
            filmy.add(int(wiersz["d"]))

    jednostki_prologu, cutsceny_w_prologu = _prolog(index, magazyn)
    jednostki.extend(jednostki_prologu)

    sceny = sorted(numer for numer, scena in ix.sceny.items() if scena.get("e"))
    grupy_cutscen, cutsceny_bez_grupy = _cutsceny(ix, cutsceny_w_prologu)
    kotwice = _kotwice_grup(ix, sceny)
    przy_scenie: dict[int, list[dict]] = defaultdict(list)
    for grupa, lista in grupy_cutscen.items():
        kotwica = kotwice.get(grupa)
        if kotwica is None:
            cutsceny_bez_grupy.extend(lista)
            continue
        przy_scenie[kotwica].extend(lista)

    # Napisy przerywników: najpierw te, o których wiadomo, do której cutsceny należą
    klucze_prologu = {k for j in jednostki if j["t"] == "prolog" for k in j.get("k") or []}
    cutsceny_wg_numeru: dict[int, dict] = {}
    for lista in przy_scenie.values():
        for jednostka in lista:
            cutsceny_wg_numeru[int(jednostka["n"])] = jednostka
    for jednostka in cutsceny_bez_grupy:
        cutsceny_wg_numeru[int(jednostka["n"])] = jednostka

    # Gdzie cutscena naprawdę stoi: krainę daje scena-kotwica, a gdy ta nie ma
    # mapy — własna przestrzeń cutsceny z bazy gry (`cutscene_space_no`).
    mapa_kraina = {mapa: k["kraina"] for k in krainy for mapa in k["mapy"]}
    przestrzen_cutscen = _przestrzen_cutscen(index)

    def kraina_cutsceny(jednostka: dict, kotwica: str) -> str:
        if kotwica != BEZ_MAPY or jednostka.get("t") != "cutscena":
            return kotwica
        no = jednostka.get("n")
        if not isinstance(no, int):
            return kotwica
        kraina = mapa_kraina.get(przestrzen_cutscen.get(no))
        return kraina if kraina in kolejnosc_krain else kotwica

    wstawki: dict[tuple[str, int], list[dict]] = defaultdict(list)
    przeniesione: dict[str, list[dict]] = defaultdict(list)
    for numer, lista in przy_scenie.items():
        kotwica = przypisanie.get(numer, BEZ_MAPY)
        for jednostka in lista:
            cel = kraina_cutsceny(jednostka, kotwica)
            if cel == kotwica:
                wstawki[(kotwica, numer)].append(jednostka)
            else:
                przeniesione[cel].append(jednostka)
    for lista in przeniesione.values():
        lista.sort(key=lambda j: j.get("n") or 0)

    z_bazy = _napisy_z_bazy(index)
    klucze_z_bazy = {k for klucze in z_bazy.values() for k in klucze}
    for no, klucze in z_bazy.items():
        cel = cutsceny_wg_numeru.get(no)
        if cel is None:
            continue
        cel.setdefault("kn", []).extend(k for k in klucze if k not in klucze_prologu)

    osobne_napisy: list[dict] = []
    przypisane_napisy = 0
    for blok in _bloki_napisow(ix):
        klucze = [k for k in blok["klucze"]
                  if k not in klucze_prologu and k not in klucze_z_bazy]
        if not klucze:
            continue
        cel = next((cutsceny_wg_numeru[no] for no in blok["c"]
                    if no in cutsceny_wg_numeru), None)
        if cel is not None:
            cel.setdefault("kn", []).extend(klucze)   # napisy stoją przed streszczeniem
            przypisane_napisy += len(klucze)
        else:
            osobne_napisy.append({"t": "napisy", "e": blok["e"],
                                  "s": PULA_NAPISOW, "k": klucze})

    for kraina in kolejnosc_krain:
        for numer in (n for n in sceny if przypisanie.get(n) == kraina):
            for jednostka in wstawki.get((kraina, numer), ()):
                jednostki.append({**jednostka, "s": kraina})
            jednostki.append({"t": "scena", "n": numer, "s": kraina})
        for jednostka in przeniesione.get(kraina, ()):
            jednostki.append({**jednostka, "s": kraina})

    cutsceny_bez_grupy.sort(key=lambda j: j["n"])
    for jednostka in cutsceny_bez_grupy:
        jednostki.append({**jednostka, "s": BEZ_GRUPY})

    # napisy bez rozpoznanej cutsceny — w kolejności z pliku gry, nie alfabetycznie
    jednostki.extend(osobne_napisy)

    # pieśni i filmy idą na koniec: w grze pojawiają się później, nie na starcie
    for numer in sorted(filmy):
        jednostki.append({"t": "film", "n": numer, "s": "Pieśni"})

    for pozycja, jednostka in enumerate(jednostki):
        jednostka["p"] = pozycja

    wyj.parent.mkdir(parents=True, exist_ok=True)
    tresc = "".join(json.dumps(j, ensure_ascii=False, separators=(",", ":")) + "\n"
                    for j in jednostki)
    wyj.write_text(tresc, encoding="utf-8")
    return {
        "jednostek": len(jednostki),
        "scen": sum(1 for j in jednostki if j["t"] == "scena"),
        "cutscen_przypisanych": sum(1 for j in jednostki
                                    if j["t"] == "cutscena" and j["s"] != BEZ_GRUPY),
        "cutscen_bez_grupy": sum(1 for j in jednostki
                                 if j["t"] == "cutscena" and j["s"] == BEZ_GRUPY),
        "cutscen_przeniesionych_do_krain": sum(len(v) for v in przeniesione.values()),
        "prolog": sum(1 for j in jednostki if j["t"] == "prolog"),
        "napisy_blokow": sum(1 for j in jednostki if j["t"] == "napisy"),
        "napisy_linii": sum(len(j.get("k") or []) for j in jednostki if j["t"] == "napisy"),
        "napisy_przy_cutscenie": przypisane_napisy,
        "napisy_z_bazy": len(klucze_z_bazy),
        "filmow": sum(1 for j in jednostki if j["t"] == "film"),
        "bajtow": len(tresc.encode("utf-8")),
    }


def wczytaj(katalog: str | Path = "index") -> list[dict]:
    """Wczytaj zapisaną chronologię (bez przeliczania czegokolwiek)."""
    plik = Path(katalog) / "chronologia.jsonl"
    with plik.open(encoding="utf-8") as f:
        return [json.loads(linia) for linia in f if linia.strip()]


def sprawdz(*, index: str = "index", magazyn: str = "tlumaczenie") -> dict:
    """Czy zapisana chronologia zgadza się z danymi? (dla testów i CI)"""
    plik = Path(index) / "chronologia.jsonl"
    if not plik.exists():
        return {"ok": False, "blad": f"brak {plik}"}
    zapisana = plik.read_text(encoding="utf-8")
    tymczas = plik.with_suffix(".tmp")
    try:
        zbuduj(index=index, magazyn=magazyn, wyj=tymczas)
        nowa = tymczas.read_text(encoding="utf-8")
    finally:
        tymczas.unlink(missing_ok=True)
    return {
        "ok": zapisana == nowa,
        "linii_zapisanych": len([x for x in zapisana.splitlines() if x.strip()]),
        "linii_teraz": len([x for x in nowa.splitlines() if x.strip()]),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--index", default="index")
    ap.add_argument("--magazyn", default="tlumaczenie")
    ap.add_argument("--wyj", default=str(DOMYSLNY_PLIK))
    ap.add_argument("--sprawdz", action="store_true",
                    help="porównaj zapisaną chronologię z danymi, nic nie zapisuj")
    a = ap.parse_args(argv)
    if a.sprawdz:
        wynik = sprawdz(index=a.index, magazyn=a.magazyn)
        print(json.dumps(wynik, ensure_ascii=False, indent=1))
        return 0 if wynik.get("ok") else 1
    wynik = zbuduj(index=a.index, magazyn=a.magazyn, wyj=Path(a.wyj))
    print(json.dumps({"ok": True, "wyj": a.wyj, **wynik}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
