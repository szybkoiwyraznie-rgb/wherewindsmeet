#!/usr/bin/env python3
"""Pamiątki (przedmioty z historią) z tabel `curio_*` bazy gry.

Gra trzyma je w czterech tabelach:

    curio_config   id -> stuff_id (przedmiot), owner_id (właściciel),
                   history_id (motyw), history_order, memory (tekst historii
                   w `text_msg`), dialog_id (scena, jeśli jest), location
    curio_owner    owner_id -> owner_name (tekst), owner_icon
                   (`head_npc_zhuxiannpc_jiangwulang` — stąd „JiangWulang”)
    curio_theme    history_id -> history_name (tekst), area_id, history_order
    equip_items    stuff_id -> name (tekst) i describe_str (tekst)

Ten skrypt nie tłumaczy niczego i nie składa zdań: zapisuje **same liczby**
(identyfikatory wierszy). Nazwy i historie dokłada `tools/czytanka_czysta.py`
przez świadków `index/teksty_*.jsonl` (przestrzeń -> identyfikator wiersza),
tak samo jak robi to z pozostałymi zbiorami.

Wynik: `index/pamiatki.jsonl`, jeden wiersz na pamiątkę:

    {"id": 35, "przedmiot": 1100010, "nazwa_id": 8966690341954285,
     "wlasciciel": 1, "wlasciciel_id": 13541160777956032791,
     "wlasciciel_ikona": "…", "motyw": 3, "kolejnosc": 1, "pamiec": 741036,
     "dialog": null, "lokacja": 10003}

`nazwa_id` i `wlasciciel_id` to **identyfikatory tekstów** (nie klucze
przekładu): treść bierze z map języka `tools/nazwy_z_map.py`, a klucz liczy
SHA-256 z tekstu źródłowego.

`pamiec` to klucz wiersza `text_msg`, w którym leży historia przedmiotu.

Użycie:
    python3 tools/pamiatki_z_bazy.py [KATALOG ...] [--wyj index/pamiatki.jsonl]

Bez katalogów bierze `local/dane/Package/HD/oversea` i warstwę łatki
`local/dane/LocalData/Patch/HD/oversea` (tak jak klient gry: łatka przykrywa
paczkę). Gdy danych nie ma, skrypt kończy się kodem 2 i nic nie zapisuje.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:  # import jako moduł
    from tools import baza_gry
except ImportError:  # uruchomienie jako skrypt
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from tools import baza_gry  # noqa: PLC0415

DOMYSLNE = (
    "local/dane/Package/HD/oversea",
    "local/dane/LocalData/Patch/HD/oversea",
)


def _liczba(wartosc):
    """Identyfikator z bazy jako liczba (albo None); inne typy to błąd danych."""
    if wartosc is None or wartosc == "":
        return None
    if isinstance(wartosc, bool):
        return None
    if isinstance(wartosc, int):
        return wartosc
    if isinstance(wartosc, str) and wartosc.isdigit():
        return int(wartosc)
    return None


def _wiersze(baza, tabela: str) -> list[tuple[object, dict]]:
    if tabela not in baza.tabele:
        return []
    out = []
    for klucz, wiersz in baza.wiersze(tabela):
        out.append((klucz, wiersz if isinstance(wiersz, dict) else {"wartosc": wiersz}))
    return out


def pamiatki(katalogi) -> list[dict]:
    baza = baza_gry.Baza(list(katalogi))
    wlasciciele = {}
    for klucz, wiersz in _wiersze(baza, "curio_owner"):
        wlasciciele[str(klucz)] = wiersz
    przedmioty = {}
    for klucz, wiersz in _wiersze(baza, "equip_items"):
        przedmioty[str(klucz)] = wiersz
    wynik = []
    for klucz, wiersz in _wiersze(baza, "curio_config"):
        identyfikator = _liczba(wiersz.get("id")) or _liczba(klucz)
        if identyfikator is None:
            continue
        wlasciciel = _liczba(wiersz.get("owner_id"))
        ikona = ""
        if wlasciciel is not None:
            ikona = str(wlasciciele.get(str(wlasciciel), {}).get("owner_icon") or "")
        wlasciciel_nazwa = None
        if wlasciciel is not None:
            wlasciciel_nazwa = _liczba(wlasciciele.get(str(wlasciciel), {}).get("owner_name"))
        przedmiot = _liczba(wiersz.get("stuff_id"))
        nazwa_id = None
        if przedmiot is not None:
            nazwa_id = _liczba(przedmioty.get(str(przedmiot), {}).get("name"))
        wynik.append({
            "id": identyfikator,
            "przedmiot": przedmiot,
            "nazwa_id": nazwa_id,
            "wlasciciel_id": wlasciciel_nazwa,
            "wlasciciel": wlasciciel,
            "wlasciciel_ikona": ikona,
            "motyw": _liczba(wiersz.get("history_id")),
            "kolejnosc": _liczba(wiersz.get("history_order")) or 0,
            "pamiec": _liczba(wiersz.get("memory")),
            "dialog": _liczba(wiersz.get("dialog_id")),
            "lokacja": _liczba(wiersz.get("location")),
        })
    wynik.sort(key=lambda w: (w["motyw"] or 0, w["kolejnosc"], w["id"]))
    return wynik


def motywy(katalogi) -> dict[str, dict]:
    """Motyw pamiątek (`curio_theme`): numer -> klucz wiersza nazwy."""
    baza = baza_gry.Baza(list(katalogi))
    out = {}
    for klucz, wiersz in _wiersze(baza, "curio_theme"):
        out[str(klucz)] = {"klucz_nazwy": str(klucz), "nazwa_id": _liczba(wiersz.get("history_name"))}
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("katalogi", nargs="*", default=None)
    parser.add_argument("--wyj", default="index/pamiatki.jsonl")
    args = parser.parse_args(argv)
    katalogi = args.katalogi or [k for k in DOMYSLNE if Path(k).is_dir()]
    if not katalogi or not any(Path(k, "MANIFEST").is_file() for k in katalogi):
        print("brak bazy gry (MANIFEST) w:", ", ".join(katalogi) or "—", file=sys.stderr)
        return 2
    wiersze = pamiatki(katalogi)
    cel = Path(args.wyj)
    cel.parent.mkdir(parents=True, exist_ok=True)
    with cel.open("w", encoding="utf-8") as plik:
        for wiersz in wiersze:
            plik.write(json.dumps(wiersz, ensure_ascii=False) + "\n")
    print(json.dumps({"pamiatki": len(wiersze), "plik": str(cel)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
