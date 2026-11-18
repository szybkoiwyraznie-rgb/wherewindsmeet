#!/usr/bin/env python3
"""Ścieżki plików VFS (`.cine` / `.graph` / `.etsb` / `.ets`) wyciągnięte z bazy gry.

Po co: skaner `.mpk` trafia wpis indeksu wyłącznie wtedy, gdy zna **dokładną**
ścieżkę (file_id = hash ścieżki). Dotąd kandydaci `.cine` byli zgadywani ze
wzorca `Char/e_01_cutscene/qhrw/<film>/<film>.cine` i trafiały tylko 14 plików
— bo środkowy katalog (`qhrw`, `fsbd`, `zqkyw`, …) jest nie do zgadnięcia.
Tymczasem baza gry przechowuje **pełne ścieżki**:

  * `cutscenes.cine_path`           — np. `Char/e_01_cutscene/fgd/sq003_cqck/sq003_cqck.cine`,
  * `fenbao_cutscene_info.resources` — też `.cine`,
  * `fenbao_cutscene_info.cutscene_graph` — `Char/graph/cutscene/*.graph`
    (kandydaci na pliki grafów Storyline — priorytet 1),
  * w wartościach wielu innych tabel — ścieżki `.etsb`/`.ets`/`.graph`
    widoczne w surowych chunkach `dataN` (skan wzorcem tekstowym).

Ten program czyta bazę (`MANIFEST` → `indexN` → `dataN`, oba korzenie:
`Package/HD/oversea` i `LocalData/Patch/HD/oversea`) i zapisuje
`index/mpk/sciezki_vfs.jsonl` — po jednej linii na unikalną ścieżkę:

    {"sciezka": "...", "ext": "cine", "zrodla": ["cutscenes.cine_path"],
     "cutsceny": [30210]}

Pole `cutsceny` (tylko dla źródeł kolumnowych) wiąże plik z numerem cutsceny
(`cutscenes`) albo id `fenbao_cutscene_info` — to przyda się przy mapowaniu
odzyskanych `.cine` z powrotem na cutsceny (Bramka 3).

Do Git trafiają wyłącznie teksty ścieżek (metadane), żadne binaria gry.

Użycie:
    python3 tools/sciezki_vfs.py --dane local/dane --wyjscie index/mpk/sciezki_vfs.jsonl
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import baza_gry  # noqa: E402

ROZSZERZENIA = ("cine", "graph", "etsb", "ets")
WZORZEC = re.compile(rb"[A-Za-z0-9_\-/\.]{2,200}\.(?:" + b"|".join(e.encode() for e in ROZSZERZENIA) + rb")\b")

KOLUMNY = (
    ("cutscenes", "cine_path"),
    ("fenbao_cutscene_info", "resources"),
    ("fenbao_cutscene_info", "cutscene_graph"),
)


def _ext(sciezka: str) -> str | None:
    koncowka = sciezka.rsplit(".", 1)[-1].lower()
    return koncowka if koncowka in ROZSZERZENIA else None


def z_kolumn(baza: baza_gry.Baza, zrodla: dict[str, set[str]], cutsceny: dict[str, set[int]]) -> None:
    """Pełne ścieżki z kolumn tabel + numer cutsceny/wpisu, który na nie wskazuje."""
    for tabela, kolumna in KOLUMNY:
        try:
            wiersze = baza.wiersze(tabela)
        except baza_gry.BazaError:
            continue
        for klucz, wiersz in wiersze:
            if not isinstance(wiersz, dict):
                continue
            wartosc = wiersz.get(kolumna)
            if not isinstance(wartosc, str):
                continue
            sciezka = wartosc.strip()
            if not sciezka or _ext(sciezka) is None:
                continue
            zrodla[sciezka].add(f"{tabela}.{kolumna}")
            if isinstance(klucz, int):
                cutsceny[sciezka].add(klucz)


def ze_skanu(korzenie: list[Path], zrodla: dict[str, set[str]]) -> dict:
    """Surowy skan chunków wszystkich plików `dataN` (oba korzenie, bez nakładania warstw)."""
    staty = {"plikow": 0, "chunkow_bledy": 0}
    for korzen in korzenie:
        for plik in sorted(korzen.glob("data*")):
            if not plik.is_file():
                continue
            staty["plikow"] += 1
            try:
                chunki = baza_gry.rozpakuj_chunki(plik.read_bytes())
            except baza_gry.BazaError:
                staty["chunkow_bledy"] += 1
                continue
            for chunk in chunki:
                try:
                    bufor = baza_gry.rozpakuj_chunk(chunk)
                except baza_gry.BazaError:
                    staty["chunkow_bledy"] += 1
                    continue
                for trafienie in WZORZEC.finditer(bufor):
                    try:
                        sciezka = trafienie.group().decode("ascii")
                    except UnicodeDecodeError:
                        continue
                    zrodla[sciezka].add("skan_dataN")
    return staty


def zbuduj(dane: Path, wyjscie: Path) -> dict:
    korzenie = [
        dane / "Package" / "HD" / "oversea",
        dane / "LocalData" / "Patch" / "HD" / "oversea",
    ]
    korzenie = [k for k in korzenie if k.is_dir()]
    if not korzenie:
        raise SystemExit(f"brak katalogów bazy pod {dane} (oczekiwano Package/HD/oversea)")

    zrodla: dict[str, set[str]] = defaultdict(set)
    cutsceny: dict[str, set[int]] = defaultdict(set)

    baza = baza_gry.Baza([str(k) for k in korzenie])
    z_kolumn(baza, zrodla, cutsceny)
    staty_skanu = ze_skanu(korzenie, zrodla)

    wyjscie.parent.mkdir(parents=True, exist_ok=True)
    liczniki: dict[str, int] = defaultdict(int)
    z_katalogiem = 0
    with wyjscie.open("w", encoding="utf-8") as fh:
        for sciezka in sorted(zrodla):
            ext = _ext(sciezka)
            if ext is None:
                continue
            wpis: dict = {"sciezka": sciezka, "ext": ext, "zrodla": sorted(zrodla[sciezka])}
            if cutsceny.get(sciezka):
                wpis["cutsceny"] = sorted(cutsceny[sciezka])
            fh.write(json.dumps(wpis, ensure_ascii=False) + "\n")
            liczniki[ext] += 1
            if "/" in sciezka:
                z_katalogiem += 1

    return {
        "wyjscie": str(wyjscie),
        "sciezek": sum(liczniki.values()),
        "z_katalogiem": z_katalogiem,
        "wg_rozszerzenia": dict(sorted(liczniki.items())),
        "skan": staty_skanu,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ścieżki VFS (.cine/.graph/.etsb/.ets) z bazy gry.")
    parser.add_argument("--dane", default="local/dane", help="katalog z Package/ i LocalData/ (baza gry)")
    parser.add_argument("--wyjscie", default="index/mpk/sciezki_vfs.jsonl", help="plik wynikowy JSONL")
    args = parser.parse_args(argv)
    wynik = zbuduj(Path(args.dane), Path(args.wyjscie))
    print(json.dumps(wynik, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
