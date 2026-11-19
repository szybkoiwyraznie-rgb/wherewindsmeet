#!/usr/bin/env python3
"""Indeksy z przebiegu skanera v7 (`local/wynik7/`) do `index/mpk/`.

Wejście (poza Gitem, patrz docs/DATA_POLICY.md):
  local/wynik7/WYNIK/MPK_SKANER_WYNIK/   — raport + wycinki z przebiegu v7,
  local/wynik7/dekodowane/               — bloki po EZST/zstd (mpk_artefakty).

Wyjście (metadane, do Gita):
  index/mpk/cine_ujecia.jsonl       — master .cine → uporządkowane pod-ujęcia,
  index/mpk/etsb_storyline.jsonl    — rozwiązane `Storyline/<ścieżka>.etsb`
                                      → sceny/cutsceny/odwołania w grafie,
  index/mpk/storyline_sceny.jsonl   — każdy graf Storyline z przebiegu
                                      (sceny, cutsceny, następstwa w grafie).

Kluczowe odkrycia v7 (dowody w docs/EXPERIMENT_LOG.md, wpis 2026-11-18 (3)):
  * master .cine wylicza pod-ujęcia w kolejności odtwarzania,
  * reguła VFS: `Storyline/` + storyline_path + `.etsb`,
  * benchmark POI: Storyline/client/dialogs/hjt/sxd_longwenbiaoji.etsb
    → graf grający dialogs_no 4700001.

Żadne teksty gry nie są kopiowane — wyłącznie numery, ścieżki i topologia.
"""

from __future__ import annotations

import collections
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WYNIK = ROOT / "local" / "wynik7" / "WYNIK" / "MPK_SKANER_WYNIK"
DEKODOWANE = ROOT / "local" / "wynik7" / "dekodowane"
INDEX_MPK = ROOT / "index" / "mpk"

sys.path.insert(0, str(ROOT / "tools"))
from mpk_skaner import file_id  # noqa: E402

RE_CINE = re.compile(rb"[ -~]{10,}\.cine")

# Typy węzłów niosące fakty o scenach / cutscenach / skryptach / zadaniach.
POLA_WEZLOW = {
    "dialogs_no": "sceny",
    "cutscene_no": "cutsceny",
    "cutscene_qte_no": "cutsceny_qte",
    "storyline_path": "skrypty",
    "task_id": "zadania",
    "cine_path": "cine",
}


def wczytaj_sonde() -> dict[str, dict]:
    sonda = {}
    with open(WYNIK / "wyciete" / "ezst_trafienia.jsonl", encoding="utf-8") as fh:
        for line in fh:
            t = json.loads(line)
            sonda[t["file_id"]] = t
    return sonda


def wczytaj_kandydatow() -> list[dict]:
    raport = json.load(open(WYNIK / "RAPORT.json", encoding="utf-8"))
    return raport["trafienia_kandydatow"]


def wczytaj_vfs() -> list[dict]:
    with open(INDEX_MPK / "sciezki_vfs.jsonl", encoding="utf-8") as fh:
        return [json.loads(line) for line in fh]


def _dat(nazwa_bin: str) -> Path:
    return DEKODOWANE / (nazwa_bin[:-4] + ".dat" if nazwa_bin.endswith(".bin") else nazwa_bin)


def dzieci_cine(blob: bytes) -> list[str]:
    """Ścieżki pod-ujęć w kolejności wystąpienia w master .cine."""
    out: list[str] = []
    for m in RE_CINE.finditer(blob):
        s = m.group(0).decode("ascii", "replace")
        if "Char/" not in s:
            continue
        s = s[s.index("Char/"):]
        if s not in out:
            out.append(s)
    return out


def buduj_cine_ujecia(kandydaci, vfs, sonda) -> list[dict]:
    cut_dla_sciezki = {v["sciezka"]: v.get("cutsceny") or [] for v in vfs}
    wiersze = []
    for t in kandydaci:
        if not t["sciezka"].endswith(".cine"):
            continue
        p = _dat("trafienie_" + t["file_id"] + ".bin")
        if not p.exists():
            continue
        blob = p.read_bytes()
        dzieci = dzieci_cine(blob)
        wiersze.append({
            "master": t["sciezka"],
            "cutsceny": cut_dla_sciezki.get(t["sciezka"], []),
            "pack_id": t["pack_id"],
            "file_id": t["file_id"],
            "ujecia": [
                {
                    "sciezka": d,
                    "file_id": format(file_id(d), "016x"),
                    "w_sondzie": format(file_id(d), "016x") in sonda,
                }
                for d in dzieci
            ],
        })
    wiersze.sort(key=lambda w: w["master"])
    return wiersze


def parsuj_graf(dane: dict) -> dict | None:
    """Wyciąga z grafu Storyline fakty + następstwa (BFS po węzłach pośrednich)."""
    storyline = dane.get("Storyline") or {}
    bufor = storyline.get("NodeBuffer") or []
    if not isinstance(bufor, list) or not bufor:
        return None

    fakty: dict[str, list] = collections.defaultdict(list)
    ciekawe: dict[int, tuple[str, object]] = {}
    wyjscia: dict[int, set[int]] = collections.defaultdict(set)

    for idx, wezel in enumerate(bufor, start=1):
        if not isinstance(wezel, dict):
            continue
        dat = wezel.get("Data") or {}
        for pole, nazwa in POLA_WEZLOW.items():
            w = dat.get(pole)
            if w in (None, 0, ""):
                continue
            fakty[nazwa].append(w)
            if pole in ("dialogs_no", "cutscene_no"):
                etykieta = "scena" if pole == "dialogs_no" else "cutscena"
                ciekawe[idx] = (etykieta, w)
        cd = wezel.get("ConnectData") or {}
        for port in cd.values():
            if not isinstance(port, list):
                continue
            for kraw in port:
                if isinstance(kraw, dict) and "dstNodeID" in kraw:
                    src = kraw.get("srcNodeID", idx)
                    wyjscia[src].add(kraw["dstNodeID"])

    if not fakty:
        return None

    nastepstwa = []
    for start, (etyk_a, w_a) in ciekawe.items():
        widziane = {start}
        kolejka = list(wyjscia.get(start, ()))
        while kolejka:
            n = kolejka.pop()
            if n in widziane:
                continue
            widziane.add(n)
            if n in ciekawe:
                etyk_b, w_b = ciekawe[n]
                nastepstwa.append([etyk_a, w_a, etyk_b, w_b])
            else:
                kolejka.extend(wyjscia.get(n, ()))

    wynik = {k: sorted(set(v), key=lambda x: (isinstance(x, str), x)) for k, v in fakty.items()}
    if nastepstwa:
        wynik["nastepstwa"] = sorted(nastepstwa, key=json.dumps)
    return wynik


def zbierz_grafy(sonda, kandydaci) -> list[dict]:
    """Wszystkie grafy Storyline z przebiegu: EZST, kandydaci, skan goły."""
    sciezki_fid: dict[str, str] = {}
    for t in kandydaci:
        sciezki_fid[t["file_id"]] = t["sciezka"]

    wiersze = []
    widziane_fid: set[str] = set()

    def dodaj(zrodlo: str, fid: str | None, sciezka: str | None, dane: dict):
        parsed = parsuj_graf(dane)
        if not parsed:
            return
        w = {"zrodlo": zrodlo}
        if fid:
            w["file_id"] = fid
        if sciezka:
            w["sciezka"] = sciezka
        w.update(parsed)
        wiersze.append(w)

    # 1. bloki EZST z sondy + wycinki kandydatów (JSON-y Storyline)
    for p in sorted(DEKODOWANE.glob("*.dat")):
        with open(p, "rb") as fh:
            head = fh.read(64)
        if not head.startswith(b'{"Variables"'):
            continue
        try:
            dane = json.load(open(p, encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        nazwa = p.stem
        fid = None
        if nazwa.startswith("ezst_"):
            fid = nazwa.split("_")[-1]
        elif nazwa.startswith("trafienie_"):
            fid = nazwa.split("_")[-1]
        if fid:
            widziane_fid.add(fid)
        dodaj("blok", fid, sciezki_fid.get(fid or ""), dane)

    # 2. skan goły (storyline_wyciete.jsonl) — bez file_id; dedup po sha treści
    widziane_sha: set[str] = set()
    sw = WYNIK / "wyciete" / "storyline_wyciete.jsonl"
    if sw.exists():
        with open(sw, encoding="utf-8") as fh:
            for line in fh:
                try:
                    rek = json.loads(line)
                except json.JSONDecodeError:
                    continue
                graf = rek.get("graf")
                if not isinstance(graf, dict):
                    continue
                sha = hashlib.sha256(
                    json.dumps(graf, sort_keys=True).encode()
                ).hexdigest()[:16]
                if sha in widziane_sha:
                    continue
                widziane_sha.add(sha)
                dodaj("goly:" + rek.get("paczka", "?"), None, None, graf)

    return wiersze


def buduj_etsb(sonda) -> list[dict]:
    """Rozwiązane ścieżki Storyline/<...>.etsb → zawartość grafu."""
    vfs = wczytaj_vfs()
    kandydaci_sciezki = {v["sciezka"] for v in vfs if v["ext"] in ("ets", "etsb")}

    # dodatkowo storyline_path z samych grafów
    pat = re.compile(rb'"storyline_path"\s*:\s*"([^"]+)"')
    for p in DEKODOWANE.glob("*.dat"):
        with open(p, "rb") as fh:
            data = fh.read(3_000_000)
        for m in pat.finditer(data):
            s = m.group(1).decode("utf-8", "replace")
            kandydaci_sciezki.add(s if "." in s.rsplit("/", 1)[-1] else s + ".etsb")

    wiersze = []
    for sciezka in sorted(kandydaci_sciezki):
        stem = sciezka.rsplit(".", 1)[0]
        for wariant in (f"Storyline/{stem}.etsb", f"Storyline/{sciezka}",
                        f"Storyline/{stem}.ets"):
            fid = format(file_id(wariant), "016x")
            t = sonda.get(fid)
            if not t:
                continue
            p = _dat(t["plik"])
            if not p.exists():
                break
            try:
                dane = json.load(open(p, encoding="utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                break
            parsed = parsuj_graf(dane) or {}
            w = {"sciezka": wariant, "file_id": fid,
                 "kontener": t["kontener"], "pack_id": t["pack_id"]}
            w.update(parsed)
            wiersze.append(w)
            break
    return wiersze


def zapisz(nazwa: str, wiersze: list[dict]) -> None:
    out = INDEX_MPK / nazwa
    with open(out, "w", encoding="utf-8") as fh:
        for w in wiersze:
            fh.write(json.dumps(w, ensure_ascii=False, sort_keys=True) + "\n")
    print(f"{out.relative_to(ROOT)}: {len(wiersze)} wierszy, "
          f"{out.stat().st_size} B")


def main() -> int:
    if not WYNIK.exists() or not DEKODOWANE.exists():
        print("BŁĄD: brak local/wynik7 (WYNIK + dekodowane).")
        return 2
    sonda = wczytaj_sonde()
    kandydaci = wczytaj_kandydatow()
    vfs = wczytaj_vfs()

    zapisz("cine_ujecia.jsonl", buduj_cine_ujecia(kandydaci, vfs, sonda))
    zapisz("etsb_storyline.jsonl", buduj_etsb(sonda))
    zapisz("storyline_sceny.jsonl", zbierz_grafy(sonda, kandydaci))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
