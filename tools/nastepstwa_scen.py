#!/usr/bin/env python3
"""Następstwa scen z danych gry (`index/`) — krawędzie „koniec jednej → początek kolejnej”.

Gra nie ma jednej listy „scena po scenie”, ale wyciąg `index/` trzyma kilka
jawnych źródeł kolejności. Ten generator zbiera je w jeden plik krawędzi
`index/nastepstwa_scen.jsonl` (po jednym wierszu na dowód), każdy z oceną
pewności:

1. **`nastepstwo`** (`pewne`) — tabela `branch_dialog_subsequent`, w wyciągu
   pole `x` sceny: dialog → dialogi, które po nim następują.
2. **`wybor`** (`pewne`) — `branch_data`: dialog, po którym pada pytanie,
   → dialogi poszczególnych wyborów gracza (rozgałęzienie).
3. **`opcja_npc`** (`pewne`) — `npc_talk_options`: dialogi rozmowy
   → dialog wskazany parametrem opcji.
4. **`zadanie`** (`z łańcucha zadań`) — koniec zadania A (dialog/cutscena
   `zakonczenie`) → początek zadania B (dialog/cutscena `przyjecie`), gdy
   B jest następnikiem A w łańcuchu `pre`/`post`. To warunek wstępny, nie
   udowodniony bezpośredni trigger — stąd słabsza ocena.
5. **`zadanie_wewnatrz`** (`z ról zadania`) — porządek cyklu życia zadania:
   `przyjecie` → `rozmowa` → `zakonczenie` (kolejne różne sceny). Najsłabszy
   dowód: role, nie stwierdzone wyzwalanie.

Węzeł to `{"t": "d", "n": numer}` (dialog z `index/sceny_*.jsonl`) albo
`{"t": "c", "n": numer}` (cutscena wskazywana przez zadania). Krawędzie do
dialogów spoza `sceny_*` i pętle własne są pomijane (liczone w podsumowaniu).

Świadomie **nie** używamy: kolejności zadań w `grupy_zadan.zadania` (listy są
posortowane numerycznie — to przynależność, nie kolejność), `zamiany_dialogow`
(zastępowanie, nie następstwo) ani pozycji `chronologia.p` (porządek
pozycyjny, nie przyczynowy).

Użycie:
    python3 tools/nastepstwa_scen.py                       # zapisz index/nastepstwa_scen.jsonl
    python3 tools/nastepstwa_scen.py --sprawdz             # tylko porównaj z zapisanym
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools import indeks as indeks_mod  # noqa: E402

DOMYSLNY_PLIK = Path("index") / "nastepstwa_scen.jsonl"

PEWNOSC = {
    "nastepstwo": "pewne",
    "wybor": "pewne",
    "opcja_npc": "pewne",
    "zadanie": "z łańcucha zadań",
    "zadanie_wewnatrz": "z ról zadania",
}

MOMENTY = ("przyjecie", "rozmowa", "zakonczenie")


def _dialog(numer: int) -> dict:
    return {"t": "d", "n": numer}


def _cutscena(numer: int) -> dict:
    return {"t": "c", "n": numer}


def _dialogi_zadania(zadanie: dict, moment: str, sceny: dict) -> list[dict]:
    """Dialogi zadania w danym momencie, tylko znane z `sceny_*`."""
    return [_dialog(n) for n in (zadanie.get("dialogi") or {}).get(moment, ()) if n in sceny]


def _cutsceny_zadania(zadanie: dict, moment: str) -> list[dict]:
    """Cutsceny zadania w danym momencie (numer wskazany przez zadanie)."""
    return [_cutscena(n) for n in (zadanie.get("przerywniki") or {}).get(moment, ())]


def _sceny_zadania(zadanie: dict, moment: str, sceny: dict) -> list[dict]:
    return _dialogi_zadania(zadanie, moment, sceny) + _cutsceny_zadania(zadanie, moment)


def zbuduj_krawedzie(sceny: dict, zadania: dict, wybory: dict, opcje_npc: dict) -> tuple[list[dict], dict]:
    """Krawędzie następstw z wczytanych tabel wyciągu (bez plików, bez tekstu).

    Zwraca (krawędzie, statystyki pominięć). Krawędź to dict
    `{"z", "do", "zrodlo", "pewnosc"}` + opcjonalny `"kontekst"`.
    """
    krawedzie: dict[tuple, dict] = {}
    pominięte = Counter()

    def dodaj(z: dict, do: dict, zrodlo: str, kontekst: dict | None = None) -> None:
        if z == do:
            pominięte["petla_wlasna"] += 1
            return
        klucz = (z["t"], z["n"], do["t"], do["n"], zrodlo,
                 json.dumps(kontekst or {}, sort_keys=True, ensure_ascii=False))
        if klucz not in krawedzie:
            krawedz = {"z": z, "do": do, "zrodlo": zrodlo, "pewnosc": PEWNOSC[zrodlo]}
            if kontekst:
                krawedz["kontekst"] = kontekst
            krawedzie[klucz] = krawedz

    # 1. tabela następstw dialogów (`branch_dialog_subsequent` → pole `x`)
    for numer, scena in sceny.items():
        for cel in scena.get("x", ()):
            if cel not in sceny:
                pominięte["cel_spoza_scen"] += 1
                continue
            dodaj(_dialog(numer), _dialog(cel), "nastepstwo")

    # 2. wybory gracza: dialog po którym pada pytanie → dialogi wyborów
    for wiersz in wybory.values():
        pytanie = wiersz.get("pytanie")
        krok = wiersz.get("krok")
        for zrodlo in wiersz.get("po_dialogach", ()):
            if zrodlo not in sceny:
                continue
            for wybor in wiersz.get("wybory", ()):
                for cel in wybor.get("dialogi", ()):
                    if cel not in sceny:
                        pominięte["cel_spoza_scen"] += 1
                        continue
                    dodaj(_dialog(zrodlo), _dialog(cel), "wybor",
                          {"pytanie": pytanie, "krok": krok, "wybor": wybor.get("nr")})

    # 3. opcje rozmowy z NPC: dialogi rozmowy → dialog z parametru opcji
    for numer, wiersz in opcje_npc.items():
        for zrodlo in wiersz.get("dialogi", ()):
            if zrodlo not in sceny:
                continue
            for opcja in wiersz.get("opcje", ()):
                parametr = opcja.get("parametr")
                if not (isinstance(parametr, str) and parametr.isdigit()):
                    continue
                cel = int(parametr)
                if cel not in sceny:
                    pominięte["cel_spoza_scen"] += 1
                    continue
                dodaj(_dialog(zrodlo), _dialog(cel), "opcja_npc",
                      {"opcja": numer, "nr": opcja.get("nr")})

    # pary zadań z łańcucha pre/post (obie strony, bo dane bywają niesymetryczne)
    pary: set[tuple[int, int]] = set()
    for numer, zadanie in zadania.items():
        for nastepne in zadanie.get("post", ()):
            if nastepne in zadania and nastepne != numer:
                pary.add((numer, nastepne))
        for poprzednie in zadanie.get("pre", ()):
            if poprzednie in zadania and poprzednie != numer:
                pary.add((poprzednie, numer))

    # 4. koniec zadania → początek następnego w łańcuchu
    for a, b in pary:
        for z in _sceny_zadania(zadania[a], "zakonczenie", sceny):
            for do in _sceny_zadania(zadania[b], "przyjecie", sceny):
                dodaj(z, do, "zadanie",
                      {"zadanie": a, "zadanie_do": b,
                       "moment_z": "zakonczenie", "moment_do": "przyjecie"})

    # 5. porządek cyklu życia wewnątrz zadania: sceny wcześniejszej roli
    #    poprzedzają sceny późniejszej (bez kolejności wewnątrz jednej roli —
    #    dane jej nie podają, więc jej nie wymyślamy)
    for numer, zadanie in zadania.items():
        role: list[tuple[str, list[dict]]] = [
            (moment, _sceny_zadania(zadanie, moment, sceny)) for moment in MOMENTY
        ]
        role = [(moment, węzły) for moment, węzły in role if węzły]
        for (moment_z, węzły_z), (moment_do, węzły_do) in zip(role, role[1:]):
            for z in węzły_z:
                for do in węzły_do:
                    dodaj(z, do, "zadanie_wewnatrz",
                          {"zadanie": numer, "moment_z": moment_z, "moment_do": moment_do})

    posortowane = sorted(
        krawedzie.values(),
        key=lambda k: (k["z"]["t"], k["z"]["n"], k["do"]["t"], k["do"]["n"],
                       k["zrodlo"], json.dumps(k.get("kontekst") or {}, sort_keys=True, ensure_ascii=False)),
    )
    statystyki = {
        "krawedzi": len(posortowane),
        "wg_zrodla": dict(sorted(Counter(k["zrodlo"] for k in posortowane).items())),
        "pominiete": dict(sorted(pominięte.items())),
    }
    return posortowane, statystyki


def serializuj(krawedzie: list[dict]) -> str:
    """Krawędzie jako treść pliku JSONL (deterministycznie)."""
    return "".join(
        json.dumps(k, ensure_ascii=False, separators=(",", ":")) + "\n" for k in krawedzie
    )


def zbuduj(index: str | Path = "index") -> tuple[str, dict]:
    """Zbuduj treść pliku następstw z katalogu wyciągu `index/`."""
    ix = indeks_mod.wczytaj(index, teksty=False, sceny=True)
    krawedzie, statystyki = zbuduj_krawedzie(ix.sceny, ix.zadania, ix.wybory, ix.opcje_npc)
    return serializuj(krawedzie), statystyki


def sprawdz(index: str | Path = "index", wyj: Path = DOMYSLNY_PLIK) -> dict:
    """Czy zapisany plik zgadza się z danymi? (dla testów i CI)"""
    plik = Path(wyj)
    if not plik.exists():
        return {"ok": False, "blad": f"brak {plik}"}
    zapisana = plik.read_text(encoding="utf-8")
    nowa, statystyki = zbuduj(index)
    return {
        "ok": zapisana == nowa,
        "linii_zapisanych": len([x for x in zapisana.splitlines() if x.strip()]),
        "linii_teraz": len([x for x in nowa.splitlines() if x.strip()]),
        **statystyki,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--index", default="index")
    ap.add_argument("--wyj", default=str(DOMYSLNY_PLIK))
    ap.add_argument("--sprawdz", action="store_true",
                    help="porównaj zapisany plik z danymi, nic nie zapisuj")
    a = ap.parse_args(argv)
    if a.sprawdz:
        wynik = sprawdz(index=a.index, wyj=Path(a.wyj))
        print(json.dumps(wynik, ensure_ascii=False, indent=1))
        return 0 if wynik.get("ok") else 1
    tresc, statystyki = zbuduj(a.index)
    plik = Path(a.wyj)
    plik.parent.mkdir(parents=True, exist_ok=True)
    plik.write_text(tresc, encoding="utf-8", newline="\n")
    print(json.dumps({"ok": True, "wyj": a.wyj, **statystyki}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
