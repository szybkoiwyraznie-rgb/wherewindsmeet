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
  * katalog artefaktów MPK (`*_<file_id:016x>.dat` albo surowe `ezst_*.bin`),
  * `index/mpk/cine_ujecia.jsonl` — dzieci `sXXX` mastera.

Część cutscen (30163 `sq003_qhyt`) trzyma w masterze tylko muzykę;
kwestie mówione siedzą w ujęciach-dzieciach, w tym samym formacie
`czas:id`. Gdy master nie ma tekstu w `sound_data`, bierzemy dzieci
w kolejności z mastera i przesuwamy ich czasy, żeby nie splątać ujęć.

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


_HEX16 = frozenset("0123456789abcdef")


def indeks_artefaktow(katalog: str | Path) -> dict[str, Path]:
    """`file_id` (hex16) → artefakt (`.dat` po EZST albo surowy `ezst_*.bin`)."""
    mapa: dict[str, Path] = {}
    root = Path(katalog)
    if not root.exists():
        return mapa
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        hx = p.stem.rsplit("_", 1)[-1].lower()
        if len(hx) == 16 and all(c in _HEX16 for c in hx):
            mapa[hx] = p
    return mapa


def dekoduj_cine(dane: bytes) -> bytes:
    """EZST/ZSTD → surowe `.cine`; inne bajty bez zmian."""
    if dane[:4] in (b"EZST", b"ZSTD"):
        from mpk_artefakty import ezst_decode, _importe
        _lz4, zstandard, AES = _importe()
        return ezst_decode(dane, AES, zstandard)
    return dane


def wczytaj_ujecia(sciezka: str | Path = "index/mpk/cine_ujecia.jsonl") -> list[dict]:
    """Wiersze `cine_ujecia.jsonl` (master + dzieci w kolejności z `.cine`)."""
    p = Path(sciezka)
    if not p.exists():
        return []
    with p.open(encoding="utf-8") as f:
        return [json.loads(linia) for linia in f if linia.strip()]


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


def kwestie_z_ujec(
    master: bytes,
    dzieci: list[bytes],
    nagrania: dict[int, dict],
) -> list[dict]:
    """Kwestie mówione: z mastera, gdy je ma; inaczej z ujęć w jego kolejności.

    Czas dziecka jest lokalny dla ujęcia — dodajemy przesunięcie, żeby
    s0030 nie weszło między kwestie s0010 (oba startują koło t=0).
    """
    k = kwestie_z_cine(dekoduj_cine(master), nagrania)
    if k:
        return k
    out: list[dict] = []
    offset = 0.0
    for blob in dzieci:
        kd = kwestie_z_cine(dekoduj_cine(blob), nagrania)
        for item in kd:
            pozycja = dict(item)
            pozycja["t"] = round(item["t"] + offset, 3)
            out.append(pozycja)
        if kd:
            offset = max(x["t"] for x in out) + 0.01
    out.sort(key=lambda x: (x["t"], x["id"]))
    return out


def _bajty(artefakty: dict[str, Path], hx: str) -> bytes | None:
    p = artefakty.get((hx or "").lower())
    return p.read_bytes() if p is not None else None


def _film_z_sciezki(sciezka: str) -> str:
    nazwa = Path(sciezka.replace("\\", "/")).stem
    return nazwa or sciezka


def uzupelnij(
    sciezka_audio: str | Path = "index/cutsceny_sciezka_audio.jsonl",
    ujecia: str | Path = "index/mpk/cine_ujecia.jsonl",
    cine: str | Path = "local/wynik7/dekodowane",
    nagrania: dict[int, dict] | None = None,
    baza=None,
) -> dict:
    """Dopisz cutsceny, których master nie ma kwestii — oś z ujęć-dzieci.

    Nie nadpisuje istniejących wpisów z kwestiami (30162 i reszta z mastera).
    """
    if nagrania is None:
        if baza is None:
            raise CineChronologiaError("uzupelnij: podaj nagrania albo bazę")
        nagrania = nagrania_po_id(baza)
    artefakty = indeks_artefaktow(cine)
    if not artefakty:
        raise CineChronologiaError(f"brak artefaktów `.cine` w {cine}")

    obecne: dict[int, dict] = {}
    cel = Path(sciezka_audio)
    if cel.exists():
        with cel.open(encoding="utf-8") as f:
            for linia in f:
                wpis = json.loads(linia)
                obecne[int(wpis["no"])] = wpis

    dopisane = 0
    bez_pliku = 0
    bez_kwestii = 0
    for wiersz in wczytaj_ujecia(ujecia):
        dzieci_meta = wiersz.get("ujecia") or []
        if not dzieci_meta:
            continue
        master_hx = wiersz.get("file_id") or ""
        master = _bajty(artefakty, master_hx)
        if master is None:
            # sam zestaw dzieci też wystarczy — 30163 ma master bez kwestii
            master = b""
        dzieci: list[bytes] = []
        brak_dziecka = False
        for u in dzieci_meta:
            blob = _bajty(artefakty, u.get("file_id") or "")
            if blob is None:
                brak_dziecka = True
                break
            dzieci.append(blob)
        if brak_dziecka:
            bez_pliku += 1
            continue
        kwestie = kwestie_z_ujec(master, dzieci, nagrania)
        if not kwestie:
            bez_kwestii += 1
            continue
        film = _film_z_sciezki(wiersz.get("master") or "")
        for no in wiersz.get("cutsceny") or []:
            if not isinstance(no, int):
                continue
            stary = obecne.get(no) or obecne.get(no % 10**8)
            if stary and stary.get("kwestie"):
                continue
            wpis = {"no": no, "kwestie": kwestie}
            if film:
                wpis["film"] = film
            obecne[no] = wpis
            dopisane += 1

    wynik = sorted(obecne.values(), key=lambda r: r["no"])
    cel.parent.mkdir(parents=True, exist_ok=True)
    with cel.open("w", encoding="utf-8") as f:
        for r in wynik:
            f.write(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n")
    return {
        "cutscen_z_kwestiami": len(wynik),
        "dopisane_z_ujec": dopisane,
        "bez_kwestii_mowionych": bez_kwestii,
        "bez_kompletnych_dzieci": bez_pliku,
    }


def zbuduj(dane: str | Path = "local/dane",
           cine: str | Path = "local/wynik7/dekodowane",
           wyj: str | Path = "index/cutsceny_sciezka_audio.jsonl") -> dict:
    baza = baza_gry.Baza([
        Path(dane) / "LocalData/Patch/HD/oversea",
        Path(dane) / "Package/HD/oversea",
    ])
    artefakty = indeks_artefaktow(cine)
    if not artefakty:
        raise CineChronologiaError(f"brak artefaktów `.cine` w {cine}")
    nagrania = nagrania_po_id(baza)
    dzieci_po_master = {
        (w.get("file_id") or "").lower(): w.get("ujecia") or []
        for w in wczytaj_ujecia()
    }

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
        dzieci_bajty: list[bytes] = []
        for u in dzieci_po_master.get(hx, ()):
            blob = _bajty(artefakty, u.get("file_id") or "")
            if blob is None:
                dzieci_bajty = []
                break
            dzieci_bajty.append(blob)
        kwestie = kwestie_z_ujec(plik.read_bytes(), dzieci_bajty, nagrania)
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
    ap.add_argument("--ujecia", default="index/mpk/cine_ujecia.jsonl")
    ap.add_argument("--uzupelnij", action="store_true",
                    help="dopisz cutsceny z ujęć-dzieci do istniejącego jsonl")
    ap.add_argument("--baza", nargs="*", default=None,
                    help="katalogi bazy (MANIFEST/indexN/dataN), np. google_drive")
    a = ap.parse_args(argv)
    if a.uzupelnij:
        baza = baza_gry.Baza(a.baza) if a.baza else baza_gry.Baza([
            Path(a.dane) / "LocalData/Patch/HD/oversea",
            Path(a.dane) / "Package/HD/oversea",
        ])
        stat = uzupelnij(a.wyj, a.ujecia, a.cine, baza=baza)
    else:
        stat = zbuduj(a.dane, a.cine, a.wyj)
    print(json.dumps(stat, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
