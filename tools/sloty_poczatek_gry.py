#!/usr/bin/env python3
"""Trzy zbiory tekstów na starcie gry — pomiar i listy slotów, bez tłumaczenia.

Właściciel (2026-11-20) zgłosił angielski wokół lokacji startowej w trzech
miejscach. To narzędzie **tylko czyta** `index/` i magazyn, wypisuje liczby
(w tym ile jeszcze bez PL) i (opcjonalnie) pliki kluczy pod
`buduj_paczke.py --tylko-sloty`.

    python3 tools/sloty_poczatek_gry.py
    python3 tools/sloty_poczatek_gry.py --json
    python3 tools/sloty_poczatek_gry.py --slotki index/sloty_poczatek

Zbiory:

1. **opisy zwykłych przedmiotów** — `all_homeland_stuff_items` pola
   `describe_str` / `story_describe_str` / `sub_describe_str[]` (nazwy już
   są po polsku; w grze widać „Ochłapy mięsa” + angielski opis),
2. **komentarze chorób w Kompendium** — `disease_type` poza `name`
   (przykład: „Sores and ulcers fester…”); pełne Compendium
   `guider_tujian_data` to osobny, większy worek — tu tylko licznik,
3. **pierwszy side-quest łuczniczy** — `对话-Shenxiandu`, sceny
   4700080–4700118 (Feng Jisheng + Ruby).

Klucz tekstu jest wspólny, więc liczby to unikalne teksty, nie wystąpienia.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

try:
    from tools import indeks as indeks_mod
    from tools import tlumaczenie as magazyn_mod
    from tools import wypisz
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from tools import indeks as indeks_mod
    from tools import tlumaczenie as magazyn_mod
    from tools import wypisz

POLE_PRZEDMIOTOW = ("describe_str", "story_describe_str", "sub_describe_str[]")
SCENY_LUCZNICZE = range(4700080, 4700119)
HEX16 = re.compile(r"[0-9a-f]{16}")


class SlotyError(Exception):
    """Wejścia nie da się odczytać."""


def _klucze_sceny(scena: dict, teksty: dict) -> list[str]:
    widziane: set[str] = set()
    out: list[str] = []
    for klucz in HEX16.findall(str(scena.get("e"))):
        if klucz in teksty and klucz not in widziane:
            widziane.add(klucz)
            out.append(klucz)
    return out


def zbior(ix, mag) -> dict:
    """Trzy zbiory braków + liczniki sąsiadów (Compendium UI, reszta Shenxiandu)."""
    brak_pl = lambda k: not mag.przeklad(k)
    przedmioty: dict[str, list[str]] = defaultdict(list)
    choroby: dict[str, list[str]] = defaultdict(list)
    lucznicze: list[str] = []
    tujian: dict[str, list[str]] = defaultdict(list)
    sxd_reszta: list[str] = []
    przed_lucznictwem: list[str] = []

    for klucz, tekst in ix.teksty.items():
        zrodlo = ix.zrodlo(tekst)
        if not zrodlo:
            continue
        tabela, pole, _wiersz = zrodlo
        if tabela == "all_homeland_stuff_items" and pole in POLE_PRZEDMIOTOW:
            przedmioty[pole].append(klucz)
        elif tabela == "disease_type" and pole != "name":
            choroby[pole].append(klucz)
        elif tabela == "guider_tujian_data" and brak_pl(klucz):
            tujian[pole].append(klucz)

    lucz_set: set[str] = set()
    for numer in SCENY_LUCZNICZE:
        scena = ix.sceny.get(numer)
        if not scena:
            continue
        for klucz in _klucze_sceny(scena, ix.teksty):
            if klucz not in lucz_set:
                lucz_set.add(klucz)
                lucznicze.append(klucz)

    sxd_set: set[str] = set()
    for scena in ix.sceny.values():
        if "Shenxiandu" not in str(scena.get("p") or ""):
            continue
        for klucz in _klucze_sceny(scena, ix.teksty):
            if brak_pl(klucz) and klucz not in lucz_set and klucz not in sxd_set:
                sxd_set.add(klucz)
                sxd_reszta.append(klucz)

    pre_set: set[str] = set()
    for numer in range(4700001, 4700080):
        scena = ix.sceny.get(numer)
        if not scena:
            continue
        for klucz in _klucze_sceny(scena, ix.teksty):
            if brak_pl(klucz) and klucz not in lucz_set and klucz not in pre_set:
                pre_set.add(klucz)
                przed_lucznictwem.append(klucz)

    def meta(klucze: list[str]) -> dict:
        znaki = sum(len(ix.teksty[k].zrodlo) for k in klucze)
        braki = sum(1 for k in klucze if brak_pl(k))
        return {"kluczy": len(klucze), "znaki_zh": znaki, "braki": braki}

    def pola(grupa: dict[str, list[str]]) -> dict:
        return {pole: meta(klucze) for pole, klucze in sorted(grupa.items())}

    k1 = [k for pole in POLE_PRZEDMIOTOW for k in przedmioty[pole]]
    k2 = [k for pole in sorted(choroby) for k in choroby[pole]]
    suma = sorted(set(k1) | set(k2) | set(lucznicze))
    return {
        "1_przedmioty": {"pola": pola(przedmioty), **meta(k1), "klucze": k1},
        "2_choroby": {"pola": pola(choroby), **meta(k2), "klucze": k2},
        "3_luczniczy": {**meta(lucznicze), "sceny": f"{SCENY_LUCZNICZE.start}–{SCENY_LUCZNICZE.stop - 1}", "klucze": lucznicze},
        "suma_trzech": meta(suma),
        "sasiedzi": {
            "guider_tujian_data": {**meta([k for v in tujian.values() for k in v]), "pola": pola(tujian)},
            "shenxiandu_poza_lucznictwem": meta(sxd_reszta),
            "dialog_4700001_4700079": meta(przed_lucznictwem),
        },
        "klucze_suma": suma,
    }


def zapisz_slotki(dane: dict, katalog: Path) -> list[str]:
    katalog.mkdir(parents=True, exist_ok=True)
    pliki = [
        ("przedmioty.txt", dane["1_przedmioty"]["klucze"]),
        ("choroby.txt", dane["2_choroby"]["klucze"]),
        ("quest_luczniczy.txt", dane["3_luczniczy"]["klucze"]),
        ("wszystkie.txt", dane["klucze_suma"]),
    ]
    zapisane = []
    for nazwa, klucze in pliki:
        sciezka = katalog / nazwa
        sciezka.write_text("".join(k + "\n" for k in klucze), encoding="utf-8")
        zapisane.append(str(sciezka))
    return zapisane


def _tabela(dane: dict) -> str:
    wiersze = [
        f"1 przedmioty (homeland opisy)     {dane['1_przedmioty']['kluczy']:5} kluczy  {dane['1_przedmioty']['znaki_zh']:6} znaków ZH  braki {dane['1_przedmioty']['braki']:5}",
    ]
    for pole, meta in dane["1_przedmioty"]["pola"].items():
        wiersze.append(f"    {pole:28} {meta['kluczy']:5}")
    wiersze.append(
        f"2 choroby (disease_type bez nazw) {dane['2_choroby']['kluczy']:5} kluczy  {dane['2_choroby']['znaki_zh']:6} znaków ZH  braki {dane['2_choroby']['braki']:5}"
    )
    for pole, meta in dane["2_choroby"]["pola"].items():
        wiersze.append(f"    {pole:28} {meta['kluczy']:5}")
    wiersze.append(
        f"3 quest łuczniczy {dane['3_luczniczy']['sceny']}  {dane['3_luczniczy']['kluczy']:5} kluczy  {dane['3_luczniczy']['znaki_zh']:6} znaków ZH  braki {dane['3_luczniczy']['braki']:5}"
    )
    wiersze.append(
        f"SUMA (bez pokryć)                 {dane['suma_trzech']['kluczy']:5} kluczy  {dane['suma_trzech']['znaki_zh']:6} znaków ZH  braki {dane['suma_trzech']['braki']:5}"
    )
    s = dane["sasiedzi"]
    wiersze.append("sąsiedzi (nie w sumie):")
    wiersze.append(f"    Compendium guider_tujian_data {s['guider_tujian_data']['kluczy']:5}")
    wiersze.append(f"    Shenxiandu poza łucznictwem   {s['shenxiandu_poza_lucznictwem']['kluczy']:5}")
    wiersze.append(f"    dialog 4700001–4700079        {s['dialog_4700001_4700079']['kluczy']:5}")
    return "\n".join(wiersze)


def main(argv: list[str] | None = None) -> int:
    wypisz.utf8()
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--indeks", default="index")
    parser.add_argument("--magazyn", default="tlumaczenie")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--slotki", help="katalog na pliki kluczy (przedmioty.txt, choroby.txt, …)")
    args = parser.parse_args(argv)
    try:
        ix = indeks_mod.wczytaj(args.indeks)
        mag = magazyn_mod.wczytaj(args.magazyn)
        dane = zbior(ix, mag)
    except (indeks_mod.IndeksError, magazyn_mod.MagazynError, SlotyError, OSError) as error:
        print(json.dumps({"ok": False, "powod": str(error)}, ensure_ascii=False))
        return 1
    if args.slotki:
        dane["zapisane"] = zapisz_slotki(dane, Path(args.slotki))
    if args.json:
        widok = {k: v for k, v in dane.items() if k != "klucze_suma"}
        for nazwa in ("1_przedmioty", "2_choroby", "3_luczniczy"):
            widok[nazwa] = {k: v for k, v in widok[nazwa].items() if k != "klucze"}
        print(json.dumps(widok, ensure_ascii=False, indent=1))
    else:
        print(_tabela(dane))
        if args.slotki:
            print("zapisano:", ", ".join(dane["zapisane"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
