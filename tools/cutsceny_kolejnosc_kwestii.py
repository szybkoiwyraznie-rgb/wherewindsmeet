#!/usr/bin/env python3
"""Kolejność wierszy puli napisów (`text_msg`) wewnątrz cutscen.

Łączy dwa źródła:
  * `index/cutsceny_sciezka_audio.jsonl` (z `tools/cine_sciezka_audio.py`)
    — chronologię kwestii mówionych ze ścieżki audio plików `.cine`
    (czas → wpis `sound_data` z chińskim tekstem scenariuszowym),
  * pulę napisów `text_msg` z wyciągu `index/` — wiersze wyświetlane
    w grze (zwykle drobniejsze segmenty jednej kwestii scenariusza).

Algorytm (benchmark: ręczny zapis gracza cutsceny 30161; 30162:
Ruby → Ach! → most → „co teraz”):
  1. segmentacja zachłanna tekstów scenariusza na teksty puli
     (najdłuższe dopasowanie od lewej, tolerancja wariantów 啦/了 itd.),
  2. okno pokolenia: klastry jednoznacznych dopasowań (te same zdania
     żyją w kilku blokach puli — stare/nowe pokolenie, wersja mobile),
  3. emisja kwestii w porządku czasu `.cine`; w obrębie jednej kwestii
     wiersze idą po numerach; każdy wiersz użyty raz,
  4. dopasowanie rozmyte dla wierszy w lukach numeracji (scenariusz
     i napisy różnią się czasem szykiem lub partykułami),
  5. okrzyk z didaskaliów (`（啊）` w 30162) — gdy po zdjęciu nawiasów
     nie zostaje tekst, a w nawiasie stoi sam wykrzyknik, wstawiamy
     krótki napis `啊`/`Ach!` w czasie nagrania; westchnienia i oddechy
     bez okrzyku nadal pomijamy.

Wyjście: `index/cutsceny_kolejnosc_kwestii.jsonl`
  {"no": 30161, "wiersze": [{"w": 591148, "k": "7c35…", "t": 0.359}, …]}
— wiersze w kolejności odtwarzania; to brakujący przeplot bloków puli
(dotąd czytanka znała tylko przynależność i porządek numeryczny).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

KATALOG = Path(__file__).resolve().parent
if str(KATALOG) not in sys.path:
    sys.path.insert(0, str(KATALOG))

import cutsceny_z_bazy as cz  # noqa: E402

# Warianty zapisu tych samych partykuł między scenariuszem a napisami
WARIANTY = str.maketrans({
    "啦": "了",
    "嘛": "吗",
    "欸": "哎",
    "诶": "哎",
    "呀": "啊",
})

# Słownictwo opisów scenicznych w `sound_data.text` (nie są napisami):
# oddechy, gwar tłumu, odgłosy walki opisane poza nawiasami didaskaliów
OPISY_SCENICZNE = ("气息", "群杂", "音效", "视频", "呼吸", "干音", "垫乐", "哭腔")

# Okrzyki, które gra pokazuje jako napis, nawet gdy scenariusz trzyma je
# w didaskaliach (`（啊）` w 30162 → „Ach!”). Bez wydłużonych wrzasków
# (`啊————`) i bez westchnień (`（轻轻叹气）`).
WYKRZYKNIKI = frozenset({
    "啊", "哎", "诶", "欸", "呀", "哦", "呃", "嘿", "呜", "哇", "嘿呀", "哎呀",
})
_RE_DIDASKALIA = re.compile(r"[（(]([^）)]+)[）)]")
MAKS_ZRODLO_WYKRZYKNIKA = 4   # „啊！” mieści się; „啊————！” nie

LUKA_KLASTRA = 25      # maks. przerwa numeracji w klastrze jednoznacznych trafień
MARGINES_OKNA = 10     # zapas okna wokół klastra
MIN_KLASTER = 2        # tyle jednoznacznych trafień uwiarygadnia klaster
MIN_WSPOLNY = 3        # minimalny wspólny spójny fragment dopasowania rozmytego


_RE_NIE_SLOWO = None  # leniwie, re importowane niżej


def _norm(tekst: str) -> str:
    """Tylko znaki znaczące (CJK/alfanumeryczne) + warianty partykuł.

    `cz.norm` zostawia pojedyncze spacje i nie zna np. „~" — a scenariusz
    (`sound_data.text`) i napisy puli różnią się właśnie interpunkcją.
    """
    global _RE_NIE_SLOWO
    if _RE_NIE_SLOWO is None:
        _RE_NIE_SLOWO = re.compile(r"[^0-9A-Za-z\u4e00-\u9fff\u3400-\u4dbf]+")
    return _RE_NIE_SLOWO.sub("", tekst).translate(WARIANTY)


def _norm_lite(tekst: str) -> str:
    """Jak `_norm`, bez zamiany partykuł (呀≠啊) — do rozpoznania okrzyku."""
    global _RE_NIE_SLOWO
    if _RE_NIE_SLOWO is None:
        _norm("")
    return _RE_NIE_SLOWO.sub("", tekst)


def _wykrzyknik_z_didaskaliow(zh: str) -> str:
    """Sam okrzyk z nawiasów, gdy reszta kwestii to didaskalia.

    `（啊）（稍微惊吓的气声）…` → `啊`. Westchnienie `（轻轻叹气）` → `\"\"`.
    """
    for m in _RE_DIDASKALIA.finditer(zh or ""):
        s = _norm_lite(m.group(1))
        if s in WYKRZYKNIKI:
            return s
    return ""


def mapa_wykrzyknikow(teksty) -> dict[str, str]:
    """Okrzyk (`啊`) → jeden krótki klucz wyciągu (nie wrzask `啊————`).

    Przy równej długości źródła bierzemy mniejszy klucz — deterministycznie.
    """
    najlepszy: dict[str, tuple] = {}
    for klucz, tekst in teksty.items():
        surowe = tekst.zrodlo or ""
        zrodlo = surowe.strip()
        if len(zrodlo) > MAKS_ZRODLO_WYKRZYKNIKA:
            continue
        n = _norm_lite(zrodlo)
        if n not in WYKRZYKNIKI:
            continue
        # najpierw samo `啊`, potem `啊！`; spacje w szarej warstwie odpadają
        ocena = (len(zrodlo), 0 if surowe == n else 1, len(surowe), klucz)
        if n not in najlepszy or ocena < najlepszy[n]:
            najlepszy[n] = ocena
    return {n: para[-1] for n, para in najlepszy.items()}


def wstaw_wykrzykniki(blok: list[dict], kwestie: list[dict],
                      wykrzykniki: dict[str, str]) -> None:
    """Wstaw `（啊）` z osi `.cine` w czasie nagrania, gdy brak wiersza puli."""
    if not wykrzykniki or not blok:
        return
    obecne = {(r.get("a") or "", round(float(r["t"]), 3)) for r in blok}
    nowe: list[dict] = []
    for kw in kwestie:
        if _norm(_bez_didaskaliow(kw.get("zh") or "")):
            continue
        nz = _wykrzyknik_z_didaskaliow(kw.get("zh") or "")
        klucz = wykrzykniki.get(nz) if nz else None
        if not klucz:
            continue
        t, audio = round(float(kw["t"]), 3), kw.get("audio") or ""
        if (audio, t) in obecne:
            continue
        wpis = {"k": klucz, "t": t}
        if audio:
            wpis["a"] = audio
        nowe.append(wpis)
        obecne.add((audio, t))
    if not nowe:
        return
    blok.extend(nowe)
    blok.sort(key=lambda r: (float(r["t"]), r.get("w") or 0, r.get("k") or ""))


def _bez_didaskaliow(tekst: str) -> str:
    wynik, glebokosc = [], 0
    for z in tekst:
        if z in "（(":
            glebokosc += 1
        elif z in "）)":
            glebokosc = max(0, glebokosc - 1)
        elif glebokosc == 0:
            wynik.append(z)
    return "".join(wynik)


def _segmentuj(nz: str, pula_norm: dict[str, list[tuple[int, str]]],
               dozwolone: set[int] | None = None) -> list[tuple[str, list[tuple[int, str]]]]:
    """Zachłannie od lewej: najdłuższy tekst puli pasujący od bieżącej pozycji."""
    wynik: list[tuple[str, list[tuple[int, str]]]] = []
    poz = 0
    while poz < len(nz):
        najlepszy = None
        for t, wiersze in pula_norm.items():
            if not nz.startswith(t, poz):
                continue
            if dozwolone is not None and not any(w in dozwolone for w, _ in wiersze):
                continue
            if najlepszy is None or len(t) > len(najlepszy[0]):
                najlepszy = (t, wiersze)
        if najlepszy is not None:
            wynik.append(najlepszy)
            poz += len(najlepszy[0])
        else:
            poz += 1
    return wynik


def _najdluzszy_wspolny(a: str, b: str) -> int:
    """Długość najdłuższego wspólnego spójnego fragmentu (krótkie teksty)."""
    if not a or not b:
        return 0
    najl = 0
    poprz = [0] * (len(b) + 1)
    for za in a:
        biez = [0]
        for j, zb in enumerate(b, 1):
            biez.append(poprz[j - 1] + 1 if za == zb else 0)
            if biez[-1] > najl:
                najl = biez[-1]
        poprz = biez
    return najl


def _okno(jednoznaczne: list[int]) -> set[range]:
    """Suma okien wokół klastrów jednoznacznych dopasowań."""
    okna: set[range] = set()
    klaster: list[int] = []
    posort = sorted(set(jednoznaczne))

    def domknij() -> None:
        if len(klaster) >= MIN_KLASTER:
            okna.add(range(klaster[0] - MARGINES_OKNA, klaster[-1] + MARGINES_OKNA + 1))

    for w in posort:
        if klaster and w - klaster[-1] > LUKA_KLASTRA:
            domknij()
            klaster.clear()
        klaster.append(w)
    if klaster:
        domknij()
    return okna


def kolejnosc_kwestii(kwestie: list[dict],
                      pula_norm: dict[str, list[tuple[int, str]]],
                      wykrzykniki: dict[str, str] | None = None
                      ) -> list[list[dict]]:
    """Bloki wariantów cutsceny; w każdym wiersze puli wg chronologii `.cine`.

    Te same zdania żyją w kilku rozłącznych blokach puli (stare/nowe
    pokolenie, wersja mobile) — każdy klaster dopasowań dostaje własny,
    niezależnie uporządkowany blok.
    """
    znorm = [(_norm(_bez_didaskaliow(k["zh"])), float(k["t"])) for k in kwestie]
    znorm.sort(key=lambda p: p[1])

    # 1. jednoznaczne dopasowania wyznaczają okna wariantów
    jednoznaczne: list[int] = []
    for nz, _t in znorm:
        for t, wiersze in _segmentuj(nz, pula_norm):
            if len(wiersze) == 1 and len(t) >= 2:
                jednoznaczne.append(wiersze[0][0])
    okna = _okno(jednoznaczne)
    audio_kwestii = {float(k["t"]): k.get("audio") or "" for k in kwestie}
    bloki = [blok for o in sorted(okna, key=lambda o: o.start)
             if (blok := _blok_okna(znorm, pula_norm, o, audio_kwestii))]
    for blok in bloki:
        wstaw_wykrzykniki(blok, kwestie, wykrzykniki or {})
    return bloki


def _blok_okna(znorm: list[tuple[str, float]],
               pula_norm: dict[str, list[tuple[int, str]]],
               okno: range,
               audio_kwestii: dict[float, str] | None = None) -> list[dict]:
    """Uporządkowane wiersze jednego okna (wariantu) puli."""
    dozwolone = {w for wiersze in pula_norm.values() for w, _ in wiersze
                 if w in okno}
    if not dozwolone:
        return []

    # 2. emisja kwestii w porządku czasu; wiersz użyty najwyżej raz
    audio_kwestii = audio_kwestii or {}
    uzyte: set[int] = set()
    kwestie_wiersze: list[tuple[float, list[tuple[int, str]]]] = []
    for nz, t in znorm:
        przydzial: list[tuple[int, str]] = []
        for tekst, wiersze in _segmentuj(nz, pula_norm, dozwolone):
            kandydaci = sorted((w, k) for w, k in wiersze
                               if w in dozwolone and w not in uzyte)
            if not kandydaci:
                continue
            w, k = kandydaci[0]
            # pojedynczy znak (np. samo „哎") tylko obok innego wiersza tej kwestii
            if len(tekst) < 2 and not any(abs(w - inny) <= 1 for inny, _ in przydzial):
                dalsze = {wd for td, wd_k in _segmentuj(nz, pula_norm, dozwolone)
                          if len(td) >= 2 for wd, _ in wd_k}
                if not any(abs(w - inny) <= 1 for inny in dalsze):
                    continue
            przydzial.append((w, k))
            uzyte.add(w)
        # także puste: dopasowanie rozmyte może jeszcze doczepić wiersz
        kwestie_wiersze.append((t, sorted(przydzial)))

    if not uzyte:
        return []

    # 3. dopasowanie rozmyte: wiersze okna w lukach numeracji między trafionymi
    trafione = sorted(uzyte)
    po_wierszu: dict[int, tuple[str, list[str]]] = {}
    for tekst, wiersze in pula_norm.items():
        for w, k in wiersze:
            if trafione[0] <= w <= trafione[-1] and w not in uzyte and w in dozwolone:
                wpis = po_wierszu.setdefault(w, (k, []))
                wpis[1].append(tekst)
    for w, (k, teksty_w) in sorted(po_wierszu.items()):
        najlepszy = None
        for idx, (nz, t) in enumerate(znorm):
            wspolny = max((_najdluzszy_wspolny(tw, nz) for tw in teksty_w), default=0)
            if wspolny >= MIN_WSPOLNY and (najlepszy is None or wspolny > najlepszy[0]):
                najlepszy = (wspolny, t)
        if najlepszy is None:
            continue
        for t_kw, przydzial in kwestie_wiersze:
            if t_kw == najlepszy[1]:
                przydzial.append((w, k))
                przydzial.sort()
                uzyte.add(w)
                break

    # 4. spłaszczenie: kwestie po czasie, w kwestii wiersze po numerach
    wynik: list[dict] = []
    for t, przydzial in sorted(kwestie_wiersze, key=lambda p: p[0]):
        for w, k in przydzial:
            wpis = {"w": w, "k": k, "t": round(t, 3)}
            audio = audio_kwestii.get(t)
            if audio:
                wpis["a"] = audio
            wynik.append(wpis)
    return wynik


def indeks_poczatkow(glob_norm: dict[str, list[str]],
                     pula_norm: dict[str, list[tuple[int, str]]]) -> dict[str, list[str]]:
    """Pierwsze 2 znaki → teksty (len ≥ 2) malejąco po długości — szybka segmentacja."""
    mapa: dict[str, list[str]] = {}
    for tekst in set(glob_norm) | set(pula_norm):
        if len(tekst) >= 2:
            mapa.setdefault(tekst[:2], []).append(tekst)
    for teksty in mapa.values():
        teksty.sort(key=len, reverse=True)
    return mapa


def kwestie_zapasowe(kwestie: list[dict],
                     glob_norm: dict[str, list[str]],
                     pula_norm: dict[str, list[tuple[int, str]]],
                     poczatki: dict[str, list[str]]) -> list[dict]:
    """Tryb zapasowy: kwestie cutscen bez okna puli (krótkie przerywniki).

    Cutsceny z 1–4 kwestiami nie tworzą klastrów jednoznacznych dopasowań
    (`_okno` wymaga ich co najmniej dwóch), a ich napisy często leżą poza
    pulą przerywników — w tabelach dialogów scen. Tu dopasowujemy tekst
    scenariusza do **całego** wyciągu: najpierw w całości, a gdy się nie
    uda — segmentacją z pełnym pokryciem (żadnych luk ≥ 2 znaki, segmenty
    ≥ 4 znaki), żeby nie zgadywać. Kwestie bez tekstu po zdjęciu
    didaskaliów oraz opisy sceniczne spoza nawiasów (oddechy „气息",
    gwar „群杂", opisy wideo) to nie napisy — pomijamy.
    """
    wynik: list[dict] = []
    for kw in sorted(kwestie, key=lambda k: float(k["t"])):
        zh = _bez_didaskaliow(kw["zh"])
        nz = _norm(zh)
        if not nz:
            continue                    # same didaskalia (oddech, okrzyk)
        if any(slowo in zh for slowo in OPISY_SCENICZNE):
            continue                    # opis nagrania, nie kwestia napisów
        t, audio = round(float(kw["t"]), 3), kw.get("audio") or ""

        def wpis(klucz: str, tekst_nz: str) -> dict:
            w = {"k": klucz, "t": t}
            para = min((p for p in pula_norm.get(tekst_nz, ())), default=None)
            if para is not None and para[1] == klucz:
                w["w"] = para[0]
            if audio:
                w["a"] = audio
            return w

        def klucz_dla(tekst_nz: str) -> str | None:
            """Deterministycznie: wiersz puli, a bez niego najmniejszy klucz."""
            para = min((p for p in pula_norm.get(tekst_nz, ())), default=None)
            if para is not None:
                return para[1]
            klucze = glob_norm.get(tekst_nz)
            return min(klucze) if klucze else None

        klucz = klucz_dla(nz)
        if klucz is not None:
            wynik.append(wpis(klucz, nz))
            continue
        # segmentacja z pełnym pokryciem (dziury najwyżej 1-znakowe)
        poz, dziura, segmenty = 0, 0, []
        while poz < len(nz):
            najlepszy = None
            for tekst in poczatki.get(nz[poz:poz + 2], ()):
                if len(tekst) < 4:
                    break               # krótkie zbitki łapią słownictwo UI
                if nz.startswith(tekst, poz):
                    najlepszy = tekst   # listy są posortowane malejąco po długości
                    break
            if najlepszy is None:
                poz += 1
                dziura += 1
                if dziura >= 2:
                    segmenty = []
                    break
                continue
            dziura = 0
            segmenty.append(najlepszy)
            poz += len(najlepszy)
        for tekst in segmenty:
            klucz = klucz_dla(tekst)
            if klucz is not None:
                wynik.append(wpis(klucz, tekst))
    return wynik


def zbuduj(index: str | Path = "index",
           sciezka_audio: str | Path = "index/cutsceny_sciezka_audio.jsonl",
           wyj: str | Path = "index/cutsceny_kolejnosc_kwestii.jsonl") -> dict:
    pula = cz.pula_z_wyciagu(index)
    pula_norm: dict[str, list[tuple[int, str]]] = {}
    for zh, wiersze in pula.items():
        nz = _norm(zh)
        if nz:
            pula_norm.setdefault(nz, []).extend(wiersze)

    # pełny wyciąg: tryb zapasowy dla cutscen, których napisy żyją poza pulą
    from tools import indeks as indeks_mod
    wyciag = indeks_mod.wczytaj(index, teksty=True, sceny=False)
    glob_norm: dict[str, list[str]] = {}
    for klucz, tekst in wyciag.teksty.items():
        nz = _norm(tekst.zrodlo or "")
        if nz:
            glob_norm.setdefault(nz, []).append(klucz)
    poczatki = indeks_poczatkow(glob_norm, pula_norm)
    wykrzykniki = mapa_wykrzyknikow(wyciag.teksty)

    wynik: list[dict] = []
    zapasowych = 0
    with Path(sciezka_audio).open(encoding="utf-8") as f:
        for linia in f:
            wpis = json.loads(linia)
            kwestie = wpis.get("kwestie") or []
            bloki = kolejnosc_kwestii(kwestie, pula_norm, wykrzykniki)
            if not bloki:
                zapas = kwestie_zapasowe(kwestie, glob_norm, pula_norm, poczatki)
                if zapas:
                    wstaw_wykrzykniki(zapas, kwestie, wykrzykniki)
                    bloki = [zapas]
                    zapasowych += 1
            if bloki:
                wynik.append({"no": wpis["no"], "bloki": bloki})

    cel = Path(wyj)
    cel.parent.mkdir(parents=True, exist_ok=True)
    with cel.open("w", encoding="utf-8") as f:
        for r in wynik:
            f.write(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n")

    return {
        "cutscen": len(wynik),
        "w_tym_zapasowych": zapasowych,
        "blokow": sum(len(r["bloki"]) for r in wynik),
        "wierszy": sum(len(b) for r in wynik for b in r["bloki"]),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--index", default="index")
    ap.add_argument("--sciezka-audio", default="index/cutsceny_sciezka_audio.jsonl")
    ap.add_argument("--wyj", default="index/cutsceny_kolejnosc_kwestii.jsonl")
    a = ap.parse_args(argv)
    print(json.dumps(zbuduj(a.index, a.sciezka_audio, a.wyj), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
