#!/usr/bin/env python3
"""Chińskie etykiety mówców → pismo łacińskie (pinyin bez tonów).

Gra podaje część mówców wyłącznie po chińsku („大祭师”, „卫兵1”, „刁顺风”),
a czytanka ma być w piśmie łacińskim. Tłumaczyć tych etykiet nie ma z czego,
więc je transliterujemy: `大祭师` → `Da Ji Shi`, `卫兵1` → `Wei Bing 1`.

Tabela znaków leży w `index/pinyin_znakow.json`, żeby przebudowa czytanki
nie wymagała żadnej biblioteki. Plik odświeża się komendą:

    python3 tools/pinyin_slownik.py --pisz index/pinyin_znakow.json

(potrzebne `pypinyin`, tylko przy odświeżaniu tabeli). Nowe znaki dopisują się
do istniejącej tabeli, więc odświeżanie nigdy nie gubi wcześniejszych wpisów.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ZH = re.compile(r"[\u3400-\u9fff]")
_ZNAK = re.compile(r"[\u3400-\u9fff]|[^\u3400-\u9fff]+")

# Pełna szerokość w etykietach („（少女）”) wygląda obco w łacince.
_PELNA_SZEROKOSC = str.maketrans({
    "（": "(", "）": ")", "，": ",", "。": ".", "、": ",", "：": ":",
    "；": ";", "！": "!", "？": "?", "“": '"', "”": '"', "‘": "'", "’": "'",
    "【": "[", "】": "]", "《": "<", "》": ">", "　": " ",
})

_MAPA: dict[str, str] | None = None


def wczytaj(index: str = "index") -> dict[str, str]:
    """Tabela znak → sylaba pinyin (`index/pinyin_znakow.json`)."""
    global _MAPA
    if _MAPA is None:
        plik = Path(index) / "pinyin_znakow.json"
        _MAPA = json.loads(plik.read_text(encoding="utf-8")) if plik.exists() else {}
    return _MAPA


def romanizuj(tekst: str, mapa: dict[str, str] | None = None) -> str:
    """Etykieta po chińsku → łacinka; fragmenty niechińskie zostają bez zmian."""
    if not tekst or not ZH.search(tekst):
        return tekst
    tekst = tekst.translate(_PELNA_SZEROKOSC)
    mapa = wczytaj() if mapa is None else mapa
    czesci: list[str] = []
    for czesc in _ZNAK.findall(tekst):
        if ZH.match(czesc):
            sylaby = [mapa.get(znak, znak) for znak in czesc]
            czesci.append(" ".join(s[:1].upper() + s[1:] for s in sylaby if s))
        else:
            czesci.append(czesc.strip())
    wynik = " ".join(c for c in czesci if c).strip()
    wynik = re.sub(r"\s*([,;:!?])\s*", r"\1 ", wynik)      # „Dui Hua :” → „Dui Hua:”
    wynik = re.sub(r"\(\s+", "(", wynik)
    wynik = re.sub(r"\s+\)", ")", wynik)
    return re.sub(r"\s{2,}", " ", wynik).strip()


def zbierz_znaki(zrodla: list[str]) -> set[str]:
    """Wszystkie znaki chińskie z podanych tekstów."""
    return {z for tekst in zrodla for z in ZH.findall(tekst or "")}


def _etykiety_z_indeksu(index: str) -> list[str]:
    """Etykiety, które mogą trafić do czytanki jako imię mówcy."""
    etykiety: list[str] = []
    katalog = Path(index)
    glosariusz = katalog / "nazwy_mowcow.json"
    if glosariusz.exists():
        etykiety.extend(json.loads(glosariusz.read_text(encoding="utf-8")))
    for plik in sorted(katalog.glob("sceny_*.jsonl")):
        for linia in plik.read_text(encoding="utf-8").splitlines():
            try:
                rekord = json.loads(linia)
            except json.JSONDecodeError:
                continue
            for osoba in rekord.get("o") or []:
                if isinstance(osoba, list) and osoba and isinstance(osoba[0], str):
                    etykiety.append(osoba[0])
    for plik in sorted(katalog.glob("cutsceny_kontekst.jsonl")):
        for linia in plik.read_text(encoding="utf-8").splitlines():
            try:
                rekord = json.loads(linia)
            except json.JSONDecodeError:
                continue
            for pole in ("mowca", "mowca_zh", "mowca_en"):
                if isinstance(rekord.get(pole), str):
                    etykiety.append(rekord[pole])
    return etykiety


def _etykiety_z_czytanki(katalog: Path) -> list[str]:
    """Chińskie etykiety mówców, które faktycznie zostały w gotowych plikach."""
    etykiety: list[str] = []
    for plik in sorted(katalog.glob("*.md")):
        for linia in plik.read_text(encoding="utf-8").splitlines():
            trafienie = re.match(r"^\*\*([^*]+):\*\* ", linia)
            if trafienie and ZH.search(trafienie[1]):
                etykiety.append(trafienie[1])
    return etykiety


def zbuduj(index: str = "index", czytanka: str | None = "out/czytanka") -> dict[str, str]:
    """Tabela pinyin dla wszystkich znaków, jakie mogą się trafić w etykietach."""
    from pypinyin import lazy_pinyin  # tylko przy odświeżaniu tabeli

    teksty = _etykiety_z_indeksu(index)
    if czytanka and Path(czytanka).exists():
        teksty += _etykiety_z_czytanki(Path(czytanka))
    znaki = zbierz_znaki(teksty)
    mapa: dict[str, str] = {}
    for znak in sorted(znaki):
        sylaby = lazy_pinyin(znak)
        if sylaby and sylaby[0]:
            mapa[znak] = sylaby[0]
    return mapa


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", default="index")
    parser.add_argument("--czytanka", default="out/czytanka")
    parser.add_argument("--pisz", default="")
    parser.add_argument("--bez-scalania", action="store_true",
                        help="nie dołączaj znaków z istniejącej tabeli")
    args = parser.parse_args()
    mapa = zbuduj(args.index, args.czytanka or None)
    if args.pisz:
        cel = Path(args.pisz)
        if cel.exists() and not args.bez_scalania:
            # tabela rośnie — po wczytaniu gotowych plików nie gubimy znaków
            mapa = {**json.loads(cel.read_text(encoding="utf-8")), **mapa}
        cel.write_text(
            json.dumps(mapa, ensure_ascii=False, sort_keys=True, indent=0) + "\n",
            encoding="utf-8",
        )
        print(f"zapisano {len(mapa)} znaków do {args.pisz}")
    else:
        print(json.dumps(mapa, ensure_ascii=False, sort_keys=True)[:400])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
