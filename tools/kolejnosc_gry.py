#!/usr/bin/env python3
"""Kolejność tekstów taka, jak odtwarza je gra.

Gra trzyma teksty w dwóch zupełnie różnych mechanizmach i każdy ma własny
klucz techniczny:

1. **Sceny dialogowe** — `dialog_timelines.<dialog_no>` (75 007 tabel, jedna
   na dialog). W środku siedzą tory z kluczami animacji (`__keyframes__`),
   a każdy klucz ma `time` (sekundy), `order` (kolejność w torze),
   `source_id` (= dialog_no * 100 + numer linii) oraz `text` (hash tekstu)
   i `formatted_text` (gotowy tekst źródłowy). Kolejność odtwarzania =
   `dialog_no` rosnąco, a w dialogu `order`, potem `time`.

2. **Pule napisów cutscen** — `text_msg` i `text_msg__grey` (po ~126 tys.
   wierszy). Te wiersze to *nie* dialogi, tylko basen napisów: silnik czyta
   je kolejnymi `id` w obrębie ciągłego bloku (np. 590336–590351 to jedna
   cutscena, 591495–591518 to scena w Qinghe). Żadna tabela w bazie nie
   wskazuje tych `id` liczbowo — sprawdzone skanem całej bazy — więc sam
   blok i rosnące `id` to jedyny i wystarczający klucz.

3. **Filmy (przerywniki filmowe)** — `entry_collect_movie_subtitle_data`:
   gotowa lista z `time` i `duration` dla każdej linii, numerowana
   `dialog_no` 1, 2, 3 (pieśń o lampionach, `钗头凤`, `中渡桥之战`).

Narzędzie czyta bazę gry (MANIFEST + indexN + dataN) i zapisuje płaski plik
`kolejnosc.jsonl`, po jednym wierszu na wystąpienie tekstu:

    {"k": "1e00e8af95a4fef6", "z": "napis", "i": 590336, "d": null,
     "t": null, "o": null}

gdzie `z` to rodzaj ("napis" albo "dialog"), `i` — id w puli napisów,
`d` — numer dialogu, `t`/`o` — czas i kolejność klucza w timeline.

Klucz `k` to ten sam skrót, którego używa reszta repo: pierwsze 16 znaków
SHA-256 tekstu źródłowego (patrz `index/`).

Użycie:
    python3 tools/kolejnosc_gry.py --baza /sciezka/do/Package \
        --index index --wyj index/kolejnosc.jsonl

    python3 tools/kolejnosc_gry.py --sprawdz zwrotki/prolog_transkrypt_z_gry.txt
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))



def skrot(tekst: str) -> str:
    """Skrót tekstu używany w indeksie (pierwsze 16 znaków SHA-256)."""
    return hashlib.sha256(tekst.encode("utf-8")).hexdigest()[:16]


def _klucze(x, out: list[dict]) -> None:
    """Zbierz wszystkie klucze animacji z drzewa timeline."""
    if isinstance(x, dict):
        if "text" in x and "time" in x:
            out.append(
                {
                    "text": x.get("text"),
                    "time": x.get("time"),
                    "order": x.get("order"),
                    "source_id": x.get("source_id"),
                    "formatted_text": x.get("formatted_text"),
                }
            )
        for v in x.values():
            if isinstance(v, (dict, list)):
                _klucze(v, out)
    elif isinstance(x, list):
        for v in x:
            _klucze(v, out)


def zbierz(katalogi: list[str], manifest: str | None = None) -> list[dict]:
    """Zbierz kolejność z bazy gry: dialogi, pule napisów i filmy.

    Baza gry jest potrzebna **tylko** tutaj — dlatego importujemy ją dopiero
    w tym miejscu. Reszta programu (i budowanie czytanek) działa bez plików gry.
    """
    from tools import baza_gry  # noqa: PLC0415

    b = baza_gry.Baza(katalogi, manifest=manifest, pamiec_chunkow=2048)
    wiersze: list[dict] = []

    for nazwa in b.tabele:
        if nazwa.startswith("dialog_timelines."):
            d = int(nazwa.rsplit(".", 1)[1])
            out: list[dict] = []
            try:
                for klucz, wart in b.wiersze(nazwa):
                    if klucz in ("timeline", 0):
                        _klucze(wart, out)
            except Exception:  # uszkodzona tabela nie przerywa całości
                continue
            for x in out:
                tekst = x["formatted_text"]
                if not tekst:
                    continue
                wiersze.append(
                    {
                        "k": skrot(tekst),
                        "z": "dialog",
                        "d": d,
                        "i": None,
                        "t": x["time"],
                        "o": x["order"],
                        "s": x["source_id"],
                    }
                )

    for dialog_no, lista in _filmy(b):
        for x in lista:
            wiersze.append(
                {
                    "k": skrot(x.get("text__raw_text__") or ""),
                    "z": "film",
                    "d": dialog_no,
                    "i": x.get("id"),
                    "t": x.get("time"),
                    "o": None,
                    "s": None,
                }
            )

    return wiersze


def _filmy(b) -> list[tuple[int, list]]:
    try:
        wynik = []
        for klucz, wart in b.wiersze("entry_collect_movie_subtitle_data"):
            if isinstance(wart, list):
                d = wart[0].get("dialog_no") if wart else klucz
                wynik.append((int(d), wart))
        return wynik
    except Exception:
        return []


def wczytaj(katalog: str | Path) -> list[dict]:
    """Wczytaj porządek z katalogu z plikami `kolejnosc_<x>.jsonl`."""
    katalog = Path(katalog)
    wiersze: list[dict] = []
    for plik in sorted(katalog.glob("kolejnosc_*.jsonl")):
        with plik.open(encoding="utf-8") as f:
            wiersze.extend(json.loads(l) for l in f if l.strip())
    return wiersze


def zapisz(wiersze: list[dict], katalog: str | Path) -> dict[str, int]:
    """Zapisz porządek w 16 shardach — tak jak reszta plików indeksu."""
    katalog = Path(katalog)
    katalog.mkdir(parents=True, exist_ok=True)
    shardy: dict[str, list[dict]] = {}
    for w in wiersze:
        klucz = w.get("k") or "0000000000000000"
        shardy.setdefault(klucz[0], []).append(w)
    for x, lista in shardy.items():
        with (katalog / f"kolejnosc_{x}.jsonl").open("w", encoding="utf-8") as f:
            for w in lista:
                f.write(json.dumps(w, ensure_ascii=False, separators=(",", ":")) + "\n")
    return {x: len(lista) for x, lista in sorted(shardy.items())}


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFC", s or "")
    for a, b in (("’", "'"), ("‘", "'"), ("“", '"'), ("”", '"')):
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s).strip().casefold()


def sprawdz(transkrypt: str | Path, index: str | Path = "index", magazyn: str | Path = "tlumaczenie") -> dict:
    """Porównaj kolejność techniczną z transkryptem gracza."""
    from tools import indeks as indeks_mod

    ix = indeks_mod.wczytaj(str(index), teksty=True, sceny=False)
    po_en = {}
    for k, t in ix.teksty.items():
        if t.en:
            po_en.setdefault(_norm(t.en), k)
    po_pl = {}
    for p in sorted(Path(magazyn).glob("pl_*.jsonl")):
        for line in p.open(encoding="utf-8"):
            d = json.loads(line)
            tekst = d.get("pl")
            klucz = d.get("k") or d.get("klucz")
            if isinstance(tekst, str) and klucz:
                po_pl.setdefault(_norm(tekst), klucz)

    kolej: dict[str, list[dict]] = {}
    for w in wczytaj(Path(index)):
        kolej.setdefault(w["k"], []).append(w)

    linie = Path(transkrypt).read_text(encoding="utf-8-sig").splitlines()
    # Transkrypt łamie długie kwestie w środku zdania — sklejamy kontynuacje.
    zbite: list[str] = []
    for l in linie:
        l = l.rstrip()
        if not l.strip():
            zbite.append("")
            continue
        poprzednia = zbite[-1] if zbite else ""
        if (poprzednia.startswith("*") and not l.startswith(("*", "#"))
                and not poprzednia.rstrip().endswith((".", "!", "?", "…", '"', ")"))):
            zbite[-1] = zbite[-1] + " " + l.strip()
        else:
            zbite.append(l.strip())

    def dopasuj(tekst: str) -> str | None:
        k = po_pl.get(_norm(tekst)) or po_en.get(_norm(tekst))
        if k:
            return k
        # Zapis ręczny bywa nieprecyzyjny — wystarczy zgodny początek kwestii.
        igla = _norm(tekst)[:28]
        if len(igla) < 12:
            return None
        for mapa in (po_pl, po_en):
            for zrodlo, klucz in mapa.items():
                if zrodlo.startswith(igla):
                    return klucz
        # Ostatnia deska ratunku: kwestia jest fragmentem dłuższego zdania.
        if len(igla) >= 16:
            for mapa in (po_pl, po_en):
                for zrodlo, klucz in mapa.items():
                    if igla in zrodlo:
                        return klucz
        return None

    pozycje = []
    for l in zbite:
        if not l or l.startswith("#"):
            continue
        tekst = l[1:].strip() if l.startswith("*") else l.strip()
        klucz = dopasuj(tekst)
        if klucz is None:
            pozycje.append({"tekst": tekst, "klucz": None, "status": "brak_klucza"})
            continue
        wyst = sorted(
            kolej.get(klucz, []),
            key=lambda w: (w["z"], w["d"] or 0, w["t"] or 0, w["i"] or 0),
        )
        if not wyst:
            pozycje.append({"tekst": tekst, "klucz": klucz, "status": "brak_w_gmie"})
            continue
        w = wyst[0]
        pozycje.append(
            {
                "tekst": tekst,
                "klucz": klucz,
                "z": w["z"],
                "d": w["d"],
                "i": w["i"],
                "t": w["t"],
                "o": w["o"],
                "status": "ok",
            }
        )
    return {"pozycje": pozycje}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--baza", nargs="+", help="katalogi z MANIFEST/indexN/dataN gry")
    ap.add_argument("--manifest", help="ścieżka do MANIFEST (domyślnie z bazy)")
    ap.add_argument("--wyj", default="index", help="katalog na shardy kolejnosci")
    ap.add_argument("--sprawdz", help="transkrypt do porównania")
    ap.add_argument("--index", default="index")
    ap.add_argument("--magazyn", default="tlumaczenie")
    a = ap.parse_args(argv)

    if a.sprawdz:
        wynik = sprawdz(a.sprawdz, a.index, a.magazyn)
        ok = sum(1 for p in wynik["pozycje"] if p["status"] == "ok")
        print(f"linii: {len(wynik['pozycje'])}, z kluczem technicznym: {ok}")
        for p in wynik["pozycje"]:
            if p["status"] != "ok":
                print(f"  [{p['status']}] {p['tekst'][:70]}")
        return 0

    if not a.baza:
        ap.error("podaj --baza albo --sprawdz")

    wiersze = zbierz(a.baza, a.manifest)

    # Pule napisów (`text_msg` i warstwa `_grey`) bierzemy z indeksu: indeks
    # zna tekst i numer wiersza, a w bazie warstwa `_grey` leży w osobnym
    # pliku danych, którego paczka zaktualizowanych plików nie zawiera.
    from tools import indeks as indeks_mod

    ix = indeks_mod.wczytaj(a.index, teksty=True, sceny=False)
    for k, t in ix.teksty.items():
        w = t.w
        if not (isinstance(w, tuple) and len(w) > 1 and str(w[1]).isdigit()):
            continue
        if w[0] not in (4735, 4736):
            continue
        wiersze.append(
            {
                "k": k,
                "z": "napis" if w[0] == 4735 else "napis_grey",
                "i": int(w[1]),
                "d": None,
                "t": None,
                "o": None,
            }
        )

    shardy = zapisz(wiersze, a.wyj)
    rodzaje: dict[str, int] = {}
    for w in wiersze:
        rodzaje[w["z"]] = rodzaje.get(w["z"], 0) + 1
    print(f"{a.wyj}: {len(wiersze)} wierszy w {len(shardy)} plikach, rodzaje: {rodzaje}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
