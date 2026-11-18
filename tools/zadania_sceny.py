#!/usr/bin/env python3
"""Sceny i cutsceny w porządku grafu zadań (tabela `tasks` bazy gry).

Skąd kolejność: tabela `tasks` wiąże zadania krawędziami `pre_task` /
`post_task`, a samo zadanie gra sceny w ustalonych momentach życia:
  fetch_play_cutscene → fetch_play_dialogs → [sceny ze skryptów
  `run_task_storyline` — kolejność wewnątrz skryptu NIEZNANA] →
  finish_dialogs → finish_play_dialogs → finish_play_cutscene.

Sceny ze skryptów bierzemy z `index/mpk/etsb_storyline.jsonl`
(grafy `Storyline/<ścieżka>.etsb` z przebiegu skanera v7).

Wyjście:
  index/zadania_sceny.jsonl — po wierszu na zadanie, które gra cokolwiek:
    {"zadanie": no, "grupa": ..., "pre": [...], "post": [...],
     "zdarzenia": [["scena"|"cutscena", nr, "moment"], ...]}
  (momenty: fetch_cutscene, fetch, skrypt:<ścieżka>, finish, finish_play,
   finish_cutscene)

  index/mpk/nastepstwa_zadania.jsonl — krawędzie następstwa:
    wewnątrz zadania (moment po momencie; sceny z jednego skryptu NIE są
    porządkowane między sobą) oraz między zadaniami (ostatnie zdarzenia A →
    pierwsze zdarzenia B dla B ∈ post(A); zadania bez zdarzeń są
    przeskakiwane przechodnio, z limitem głębokości).

Uruchomienie wymaga bazy gry w `local/dane` (poza Gitem).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import baza_gry  # noqa: E402

KATALOGI = [
    ROOT / "local" / "dane" / "LocalData" / "Patch" / "HD" / "oversea",
    ROOT / "local" / "dane" / "Package" / "HD" / "oversea",
]

MAKS_PRZESKOK = 12


def wczytaj_skrypty() -> dict[str, list[int]]:
    """stem ścieżki klienta → sceny grane przez graf skryptu."""
    sceny: dict[str, list[int]] = {}
    with open(ROOT / "index" / "mpk" / "etsb_storyline.jsonl", encoding="utf-8") as fh:
        for line in fh:
            d = json.loads(line)
            stem = d["sciezka"][len("Storyline/"):].rsplit(".", 1)[0]
            if d.get("sceny"):
                sceny[stem] = d["sceny"]
    return sceny


def _stem(s: str) -> str:
    return s.rsplit(".", 1)[0] if s.endswith((".ets", ".etsb")) else s


def _liczby(v) -> list[int]:
    if isinstance(v, int) and v > 0:
        return [v]
    if isinstance(v, (list, tuple)):
        return [x for x in v if isinstance(x, int) and x > 0]
    return []


def zdarzenia_zadania(w: dict, skrypty: dict[str, list[int]]) -> list[list]:
    zd: list[list] = []
    for nr in _liczby(w.get("fetch_play_cutscene")):
        zd.append(["cutscena", nr, "fetch_cutscene"])
    for nr in _liczby(w.get("fetch_play_dialogs")):
        zd.append(["scena", nr, "fetch"])
    for sciezka in (w.get("run_task_storyline") or []):
        if not isinstance(sciezka, str):
            continue
        for nr in skrypty.get(_stem(sciezka), []):
            zd.append(["scena", nr, "skrypt:" + sciezka])
    for nr in _liczby(w.get("finish_dialogs")):
        zd.append(["scena", nr, "finish"])
    for nr in _liczby(w.get("finish_play_dialogs")):
        zd.append(["scena", nr, "finish_play"])
    for nr in _liczby(w.get("finish_play_cutscene")):
        zd.append(["cutscena", nr, "finish_cutscene"])
    return zd


def main() -> int:
    for k in KATALOGI:
        if not k.is_dir():
            print(f"BŁĄD: brak katalogu bazy {k} — pobierz paczki do local/dane.")
            return 2
    baza = baza_gry.Baza([str(k) for k in KATALOGI])
    skrypty = wczytaj_skrypty()

    zadania: dict[int, dict] = {}
    for klucz, wartosc in baza.wiersze("tasks"):
        if not isinstance(klucz, int):
            continue
        w = baza_gry.do_json(wartosc)
        if not isinstance(w, dict):
            continue
        zadania[klucz] = {
            "pre": _liczby(w.get("pre_task")),
            "post": _liczby(w.get("post_task")) + _liczby(w.get("one_post_task")),
            "grupa": w.get("group"),
            "zdarzenia": zdarzenia_zadania(w, skrypty),
        }

    # uzupełnij post o odwrócone pre (graf bywa jednostronny)
    for nr, z in zadania.items():
        for p in z["pre"]:
            if p in zadania and nr not in zadania[p]["post"]:
                zadania[p]["post"].append(nr)

    # 1. index/zadania_sceny.jsonl — zadania, które grają cokolwiek
    wyj1 = ROOT / "index" / "zadania_sceny.jsonl"
    n1 = 0
    with open(wyj1, "w", encoding="utf-8") as fh:
        for nr in sorted(zadania):
            z = zadania[nr]
            if not z["zdarzenia"]:
                continue
            fh.write(json.dumps({
                "zadanie": nr, "grupa": z["grupa"], "pre": sorted(z["pre"]),
                "post": sorted(set(z["post"])), "zdarzenia": z["zdarzenia"],
            }, ensure_ascii=False) + "\n")
            n1 += 1

    # 2. krawędzie następstwa
    krawedzie: set[tuple] = set()

    def dodaj(a, b):
        if a[:2] != b[:2]:
            krawedzie.add((a[0], a[1], b[0], b[1]))

    for nr, z in zadania.items():
        zd = z["zdarzenia"]
        # wewnątrz zadania: moment po momencie; sceny z tego samego skryptu
        # nie są porządkowane między sobą
        for i in range(len(zd)):
            for j in range(i + 1, len(zd)):
                if zd[i][2] == zd[j][2] and zd[i][2].startswith("skrypt:"):
                    continue
                dodaj(zd[i], zd[j])
                break  # tylko najbliższy następny moment

    # między zadaniami: ostatnie zdarzenia A → pierwsze zdarzenia B,
    # z przeskokiem przez zadania bez zdarzeń
    def pierwsze(nr: int, glebokosc: int, widziane: frozenset) -> list[list]:
        if glebokosc > MAKS_PRZESKOK or nr in widziane or nr not in zadania:
            return []
        z = zadania[nr]
        if z["zdarzenia"]:
            return z["zdarzenia"][:1] or []
        wyn: list[list] = []
        for p in z["post"]:
            wyn.extend(pierwsze(p, glebokosc + 1, widziane | {nr}))
        return wyn

    for nr, z in zadania.items():
        if not z["zdarzenia"]:
            continue
        ostatnie = z["zdarzenia"][-1]
        for p in set(z["post"]):
            for b in pierwsze(p, 0, frozenset({nr})):
                dodaj(ostatnie, b)

    wyj2 = ROOT / "index" / "mpk" / "nastepstwa_zadania.jsonl"
    with open(wyj2, "w", encoding="utf-8") as fh:
        for (ta, a, tb, b) in sorted(krawedzie):
            fh.write(json.dumps({"z": [ta, a], "do": [tb, b]},
                                ensure_ascii=False) + "\n")

    print(json.dumps({
        "zadan_w_tabeli": len(zadania), "zadan_ze_zdarzeniami": n1,
        "krawedzi": len(krawedzie),
        "pliki": [str(wyj1.relative_to(ROOT)), str(wyj2.relative_to(ROOT))],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
