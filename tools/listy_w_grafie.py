#!/usr/bin/env python3
"""Listy fabularne w grafach Storyline → `index/mpk/listy_w_grafie.jsonl`.

Węzeł `OpenUINode` / `OpenUIWithInputNode` z `ui_path` zawierającym `envelop`
otwiera `TaskEnvelopWindow`. Identyfikator listu to `no` w `ui_kwargs`
(`CommonMakeDictNode`: klucz `"no"` ← `StrInputParameterNode`, wartość ←
`IntInputParameterNode`). Kolejność sterowania `__out__` daje scenę tuż
przed oknem (`po`) i tuż po zamknięciu (`przed`).

Wejście: zdekodowane bloki JSON `.bin` z przebiegu skanera v7
(`MPK_SKANER_WYNIK/wyciete/ezst_*.bin`, poza Gitem). Wyjście: metadane
(numery, file_id, ścieżka) — bez tekstu gry.

    python3 tools/listy_w_grafie.py /ścieżka/wyciete --wyj index/mpk/listy_w_grafie.jsonl
"""

from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIALOG_TYPES = frozenset({
    "StorylineDialogsPlayNode",
    "GameLevelStorylineDialogsPlayNode",
})
UI_TYPES = frozenset({"OpenUINode", "OpenUIWithInputNode"})


def _wezly(dokument: dict) -> dict[int, tuple]:
    bufor = (dokument.get("Storyline") or {}).get("NodeBuffer") or []
    by: dict[int, tuple] = {}
    for idx, wezel in enumerate(bufor, start=1):
        if isinstance(wezel, dict):
            by[idx] = (
                wezel.get("Type"),
                wezel.get("Data") or {},
                wezel.get("ConnectData") or {},
                wezel.get("Value"),
            )
    return by


def _krawedzie(by: dict[int, tuple]) -> tuple[dict[int, list[int]], dict[int, list[int]]]:
    przod: dict[int, list[int]] = collections.defaultdict(list)
    wstecz: dict[int, list[int]] = collections.defaultdict(list)
    for idx, (_typ, _dane, polaczenia, _wartosc) in by.items():
        for port, krawedzie in polaczenia.items():
            if not isinstance(krawedzie, list):
                continue
            for kraw in krawedzie:
                if not isinstance(kraw, dict) or "dstNodeID" not in kraw:
                    continue
                zrodlo = kraw.get("srcPortName") or port
                if zrodlo == "__out__" or port == "__out__":
                    dst = kraw["dstNodeID"]
                    przod[idx].append(dst)
                    wstecz[dst].append(idx)
    return przod, wstecz


def _envelop_no(by: dict[int, tuple], slownik: int):
    klucze: dict[str, object] = {}
    wartosci: dict[str, tuple] = {}
    for _idx, (typ, _dane, polaczenia, wartosc) in by.items():
        for _port, krawedzie in polaczenia.items():
            if not isinstance(krawedzie, list):
                continue
            for kraw in krawedzie:
                if not isinstance(kraw, dict) or kraw.get("dstNodeID") != slownik:
                    continue
                dest = kraw.get("dstPortName") or ""
                if dest.startswith("key_"):
                    klucze[dest] = wartosc
                if dest.startswith("value_"):
                    wartosci[dest] = (typ, wartosc)
    numer = None
    for nazwa, klucz in klucze.items():
        para = wartosci.get("value_" + nazwa.split("_", 1)[-1])
        if klucz == "no" and para is not None:
            numer = para[1]
    if numer is None:
        for typ, wartosc in wartosci.values():
            if typ == "IntInputParameterNode":
                numer = wartosc
                break
    if isinstance(numer, str) and numer.isdigit():
        numer = int(numer)
    return numer


def _sceny_obok(start: int, sasiedzi: dict[int, list[int]], by: dict[int, tuple]) -> list[int]:
    widziane = {start}
    kolejka = list(sasiedzi.get(start, ()))
    znalezione: list[int] = []
    while kolejka:
        n = kolejka.pop(0)
        if n in widziane:
            continue
        widziane.add(n)
        wezel = by.get(n)
        if not wezel:
            continue
        if wezel[0] in DIALOG_TYPES:
            numer = wezel[1].get("dialogs_no")
            if isinstance(numer, int):
                znalezione.append(numer)
            continue
        kolejka.extend(sasiedzi.get(n, ()))
    return znalezione


def parsuj_graf(dokument: dict, file_id: str | None = None) -> list[dict]:
    """Wiersze listów z jednego grafu Storyline."""
    by = _wezly(dokument)
    if not by:
        return []
    przod, wstecz = _krawedzie(by)
    wiersze: list[dict] = []
    for idx, (typ, dane, _polaczenia, _wartosc) in by.items():
        if typ not in UI_TYPES:
            continue
        sciezka_ui = dane.get("ui_path") if isinstance(dane, dict) else None
        if not sciezka_ui or "envelop" not in str(sciezka_ui).lower():
            continue
        slowniki = []
        for j, (_t, _d, polaczenia, _v) in by.items():
            for _port, krawedzie in polaczenia.items():
                if not isinstance(krawedzie, list):
                    continue
                for kraw in krawedzie:
                    if (isinstance(kraw, dict) and kraw.get("dstNodeID") == idx
                            and kraw.get("dstPortName") == "ui_kwargs"):
                        slowniki.append(j)
        numer = None
        for slownik in slowniki:
            numer = _envelop_no(by, slownik)
            if numer is not None:
                break
        if not isinstance(numer, int):
            continue
        rec: dict = {"no": numer}
        if file_id:
            rec["file_id"] = file_id
        po = _sceny_obok(idx, wstecz, by)
        przed = _sceny_obok(idx, przod, by)
        if len(po) == 1:
            rec["po"] = po[0]
        if len(przed) == 1:
            rec["przed"] = przed[0]
        wiersze.append(rec)
    return wiersze


def _file_id_z_nazwy(sciezka: Path) -> str | None:
    stem = sciezka.stem
    if "_" not in stem:
        return stem if len(stem) == 16 else None
    ogon = stem.rsplit("_", 1)[-1]
    return ogon if len(ogon) == 16 else None


def zbierz(zrodlo: Path) -> list[dict]:
    wiersze: list[dict] = []
    for plik in sorted(zrodlo.rglob("*.bin")):
        surowe = plik.read_bytes()
        if b"TaskEnvelopWindow" not in surowe and b"task_envelope" not in surowe:
            continue
        if not surowe.startswith(b'{"'):
            continue
        try:
            dokument = json.loads(surowe)
        except json.JSONDecodeError:
            continue
        if not isinstance(dokument, dict):
            continue
        wiersze.extend(parsuj_graf(dokument, _file_id_z_nazwy(plik)))
    wiersze.sort(key=lambda w: (w.get("no", 0), w.get("file_id") or ""))
    return wiersze


def dopisz_sciezki(wiersze: list[dict], etsb: Path) -> None:
    if not etsb.is_file():
        return
    fid2path: dict[str, str] = {}
    with etsb.open(encoding="utf-8") as fh:
        for linia in fh:
            if not linia.strip():
                continue
            rec = json.loads(linia)
            fid = rec.get("file_id")
            sciezka = rec.get("sciezka")
            if fid and sciezka:
                fid2path[fid] = sciezka
    for w in wiersze:
        sciezka = fid2path.get(w.get("file_id") or "")
        if sciezka:
            w["sciezka"] = sciezka


def zapisz(wyj: Path, wiersze: list[dict]) -> None:
    wyj.parent.mkdir(parents=True, exist_ok=True)
    with wyj.open("w", encoding="utf-8", newline="\n") as fh:
        for w in wiersze:
            fh.write(json.dumps(w, ensure_ascii=False, sort_keys=True) + "\n")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("zrodlo", type=Path, help="katalog ze zdekodowanymi ezst_*.bin")
    ap.add_argument("--wyj", type=Path, default=ROOT / "index" / "mpk" / "listy_w_grafie.jsonl")
    ap.add_argument("--etsb", type=Path, default=ROOT / "index" / "mpk" / "etsb_storyline.jsonl",
                    help="mapowanie file_id → ścieżka VFS")
    a = ap.parse_args(argv)
    if not a.zrodlo.is_dir():
        print(f"BŁĄD: brak katalogu {a.zrodlo}")
        return 2
    wiersze = zbierz(a.zrodlo)
    dopisz_sciezki(wiersze, a.etsb)
    zapisz(a.wyj, wiersze)
    z_po = sum(1 for w in wiersze if "po" in w)
    print(f"{a.wyj}: {len(wiersze)} listów, {z_po} z sceną poprzedzającą, "
          f"{a.wyj.stat().st_size} B")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
