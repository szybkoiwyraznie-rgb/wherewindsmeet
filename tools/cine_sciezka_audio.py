#!/usr/bin/env python3
"""Chronologia kwestii w cutscenach ze ścieżki audio plików `.cine`.

Odkrycie (sesja 2026-11-18): główny plik `.cine` cutsceny (kontener ujęć
`sXXX`) zawiera ścieżkę zdarzeń dźwiękowych zapisaną tekstowo jako wpisy
`czas:id_sound_data:a:b;c` (np. `3.399:7151014:0:0;0`). Posortowane po
czasie dają pełną kolejność kwestii mówionych — to brakujące źródło
przeplotu bloków puli napisów (`text_msg`), którego nie ma w żadnej
tabeli bazy.

Wejście:
  * baza gry (`cutscenes.cine_path`, `sound_data.{id,audio_name,text}`),
  * katalog zdekodowanych artefaktów MPK (pliki `*_<file_id:016x>.dat`
    z `tools/mpk_artefakty.py`, EZST już rozpakowane).

Wyjście: `index/cutsceny_sciezka_audio.jsonl` — po jednym wpisie na
cutscenę: {"no", "film", "kwestie": [{"t", "id", "audio", "zh"}...]},
kwestie posortowane po czasie; zdarzenia bez tekstu w `sound_data`
(muzyka, ambient) są pomijane.
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

import baza_gry  # noqa: E402
from mpk_skaner import file_id  # noqa: E402

# czas:id:a:b;c — id weryfikowane potem po `sound_data`, żeby odsiać
# przypadkowe zbitki liczb w innych ścieżkach animacji
RE_WPIS = re.compile(rb"(\d+(?:\.\d+)?):(\d{5,9}):(\d+):(\d+);(\d+)")


class CineChronologiaError(RuntimeError):
    pass


def indeks_artefaktow(katalog: str | Path) -> dict[str, Path]:
    """`file_id` (hex16) → ścieżka zdekodowanego artefaktu `.dat`."""
    mapa: dict[str, Path] = {}
    for p in Path(katalog).glob("*.dat"):
        hx = p.stem.rsplit("_", 1)[-1]
        if len(hx) == 16:
            mapa[hx] = p
    if not mapa:
        raise CineChronologiaError(f"brak artefaktów `.dat` w {katalog}")
    return mapa


def nagrania_po_id(baza) -> dict[int, dict]:
    """`sound_data.id` → {audio_name, text} (tylko wpisy z nazwą nagrania)."""
    mapa: dict[int, dict] = {}
    for _k, w in baza.wiersze("sound_data"):
        if not isinstance(w, dict):
            continue
        sid, nazwa = w.get("id"), w.get("audio_name")
        if isinstance(sid, int) and isinstance(nazwa, str) and nazwa:
            mapa[sid] = {"audio": nazwa, "zh": (w.get("text") or "").strip()}
    if not mapa:
        raise CineChronologiaError("tabela `sound_data` pusta lub nieczytelna")
    return mapa


def kwestie_z_cine(dane: bytes, nagrania: dict[int, dict]) -> list[dict]:
    """Wpisy ścieżki audio z surowych bajtów `.cine`, po czasie, bez muzyki."""
    kwestie: list[dict] = []
    widziane: set[tuple[float, int]] = set()
    for m in RE_WPIS.finditer(dane):
        try:
            t, sid = float(m.group(1)), int(m.group(2))
        except ValueError:
            continue
        wpis = nagrania.get(sid)
        if wpis is None or not wpis["zh"]:
            continue  # nie-sound_data (przypadkowa zbitka) albo muzyka/ambient
        if (t, sid) in widziane:
            continue
        widziane.add((t, sid))
        kwestie.append({"t": round(t, 3), "id": sid, **wpis})
    kwestie.sort(key=lambda k: (k["t"], k["id"]))
    return kwestie


def zbuduj(dane: str | Path = "local/dane",
           cine: str | Path = "local/wynik7/dekodowane",
           wyj: str | Path = "index/cutsceny_sciezka_audio.jsonl") -> dict:
    baza = baza_gry.Baza([
        Path(dane) / "LocalData/Patch/HD/oversea",
        Path(dane) / "Package/HD/oversea",
    ])
    artefakty = indeks_artefaktow(cine)
    nagrania = nagrania_po_id(baza)

    wynik: list[dict] = []
    bez_pliku: list[int] = []
    bez_kwestii = 0
    for _k, w in baza.wiersze("cutscenes"):
        if not isinstance(w, dict):
            continue
        sciezka = w.get("cine_path")
        no = w.get("no")
        if not isinstance(sciezka, str) or not sciezka or not isinstance(no, int):
            continue
        hx = f"{file_id(sciezka):016x}"
        plik = artefakty.get(hx)
        if plik is None:
            bez_pliku.append(no)
            continue
        kwestie = kwestie_z_cine(plik.read_bytes(), nagrania)
        if not kwestie:
            bez_kwestii += 1
            continue
        wpis = {"no": no, "kwestie": kwestie}
        if isinstance(w.get("cine_name"), str) and w["cine_name"]:
            wpis["film"] = w["cine_name"]
        wynik.append(wpis)

    wynik.sort(key=lambda r: r["no"])
    cel = Path(wyj)
    cel.parent.mkdir(parents=True, exist_ok=True)
    with cel.open("w", encoding="utf-8") as f:
        for r in wynik:
            f.write(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n")

    stat = {
        "cutscen_z_kwestiami": len(wynik),
        "kwestii": sum(len(r["kwestie"]) for r in wynik),
        "bez_kwestii_mowionych": bez_kwestii,
        "bez_pliku_cine": len(bez_pliku),
    }
    return stat


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dane", default="local/dane")
    ap.add_argument("--cine", default="local/wynik7/dekodowane")
    ap.add_argument("--wyj", default="index/cutsceny_sciezka_audio.jsonl")
    a = ap.parse_args(argv)
    stat = zbuduj(a.dane, a.cine, a.wyj)
    print(json.dumps(stat, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
