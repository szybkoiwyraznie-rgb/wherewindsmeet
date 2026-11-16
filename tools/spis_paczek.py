#!/usr/bin/env python3
"""Spis paczek zbieracza: co dokładnie leży w której części.

Po co: dane z gry leżą na Dysku Google w ośmiu częściach po ~50–80 MB. Żeby
w kolejnej sesji nie ciągnąć wszystkiego, repozytorium trzyma **spis**:
źródłowa ścieżka w grze → numer części, rozmiar i SHA-256. Dość wpisać numer
części, pobrać ten jeden plik z Dysku i rozpakować.

    python3 tools/spis_paczek.py --zrodlo google_drive --wyj-json index/paczki.json \
        --wyj-md docs/PLIKI_W_PACZKACH.md
    python3 tools/spis_paczek.py --zrodlo google_drive --rozpakuj local/dane

Numer części i identyfikator na Dysku biorą się z `RAPORT.json` w paczce
(`batch.part`) oraz z `--drive-id czescN=ID` (opcjonalnie, do dokumentacji).

Rozpakowanie odtwarza ścieżki źródłowe z `RAPORT.json` (`stored_as` → `source`),
więc `local/dane/Package/HD/oversea/data1` leży tam, gdzie oczekują narzędzia.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path

FORMAT = "wwm-spis-paczek-v1"


def sha256_pliku(sciezka: Path) -> str:
    digest = hashlib.sha256()
    with sciezka.open("rb") as handle:
        for blok in iter(lambda: handle.read(1 << 20), b""):
            digest.update(blok)
    return digest.hexdigest()


def _raport(archiwum: zipfile.ZipFile) -> dict:
    for nazwa in ("RAPORT.json", "RAPORT.txt"):
        if nazwa in archiwum.namelist():
            return json.loads(archiwum.read(nazwa).decode("utf-8-sig"))
    raise SystemExit("paczka bez RAPORT.json — to nie jest wynik zbieracza")


def opis_paczki(sciezka: Path, drive_id: str | None = None) -> dict:
    """Opis jednej paczki: nagłówek + lista plików z RAPORT.json."""
    with zipfile.ZipFile(sciezka) as archiwum:
        raport = _raport(archiwum)
        pliki = []
        for wpis in raport.get("files") or ():
            pliki.append({
                "zrodlo": wpis.get("source"),
                "rodzaj": wpis.get("kind"),
                "bajtow": wpis.get("bytes"),
                "sha256": wpis.get("sha256"),
                "schowane_jako": wpis.get("stored_as"),
                "status": wpis.get("status"),
            })
        czesci = (raport.get("batch") or {}).get("parts")
        numer = (raport.get("batch") or {}).get("part")
    return {
        "paczka": sciezka.name,
        "numer": numer,
        "czesciz": czesci,
        "bajtow": sciezka.stat().st_size,
        "sha256": sha256_pliku(sciezka),
        "drive_id": drive_id,
        "utworzone": raport.get("created_utc"),
        "zbieracz": raport.get("collector_version"),
        "build": raport.get("steam_build_id"),
        "plikow": len(pliki),
        "pliki": pliki,
    }


def _identyfikator(paczka: Path, identyfikatory: dict[str, str]) -> str | None:
    """Identyfikator Dysku: po pełnej nazwie albo po końcówce (`czesc3`)."""
    if paczka.name in identyfikatory:
        return identyfikatory[paczka.name]
    for nazwa, ident in sorted(identyfikatory.items(), key=lambda para: -len(para[0])):
        if paczka.name.endswith(nazwa) or paczka.stem.endswith("_" + nazwa):
            return ident
    return None


def spis(paczki: list[Path], identyfikatory: dict[str, str]) -> dict:
    opisy = [opis_paczki(p, _identyfikator(p, identyfikatory)) for p in sorted(paczki)]
    opisy.sort(key=lambda o: (o.get("numer") or 0, o["paczka"]))
    indeks: dict[str, list[int]] = {}
    for opis in opisy:
        for wpis in opis["pliki"]:
            indeks.setdefault(wpis["zrodlo"], []).append(opis["numer"])
    return {
        "format": FORMAT,
        "paczki": opisy,
        "gdzie_szukac": {zrodlo: sorted(set(czesci)) for zrodlo, czesci in sorted(indeks.items())},
    }


def markdown(dane: dict) -> str:
    linie = [
        "# Co leży w której paczce zbieracza",
        "",
        "Plik wygenerowany przez `tools/spis_paczek.py` — nie edytować ręcznie.",
        "Każda paczka to wynik `collector/zbierz.ps1` (albo `spakuj_dane.ps1`):",
        "`RAPORT.json` + `pliki/NNNNNN_nazwa`. Ścieżka `źródło` jest tą samą,",
        "która leży w katalogu gry, więc rozpakowanie odtwarza drzewo jeden do jednego.",
        "",
        "## Paczki",
        "",
        "| część | plik | rozmiar | plików | SHA-256 | Dysk Google |",
        "|---|---|---|---|---|---|",
    ]
    for opis in dane["paczki"]:
        dysk = f"`{opis['drive_id']}`" if opis.get("drive_id") else "—"
        linie.append(
            f"| {opis.get('numer')} | `{opis['paczka']}` | {opis['bajtow']:,} B | "
            f"{opis['plikow']} | `{opis['sha256']}` | {dysk} |".replace(",", " ")
        )
    linie += ["", "## Pliki", ""]
    for opis in dane["paczki"]:
        linie += [f"### Część {opis.get('numer')}", "",
                  "| plik w grze | rozmiar | SHA-256 |", "|---|---|---|"]
        for wpis in opis["pliki"]:
            linie.append(f"| `{wpis['zrodlo']}` | {wpis['bajtow']} B | `{wpis['sha256']}` |")
        linie.append("")
    linie += ["## Gdzie szukać", "", "| plik w grze | części |", "|---|---|"]
    for zrodlo, czesci in dane["gdzie_szukac"].items():
        linie.append(f"| `{zrodlo}` | {', '.join(str(c) for c in czesci)} |")
    linie.append("")
    return "\n".join(linie)


def rozpakuj(paczki: list[Path], cel: Path) -> list[str]:
    """Odtwórz drzewo gry w `cel` według `RAPORT.json`."""
    cel.mkdir(parents=True, exist_ok=True)
    zapisane = []
    for sciezka in sorted(paczki):
        with zipfile.ZipFile(sciezka) as archiwum:
            raport = _raport(archiwum)
            for wpis in raport.get("files") or ():
                zrodlo, schowane = wpis.get("source"), wpis.get("stored_as")
                if not zrodlo or not schowane:
                    continue
                cel_pliku = cel / zrodlo
                cel_pliku.parent.mkdir(parents=True, exist_ok=True)
                with archiwum.open(schowane) as zrodlo_strumien, cel_pliku.open("wb") as wyjscie:
                    while True:
                        blok = zrodlo_strumien.read(1 << 20)
                        if not blok:
                            break
                        wyjscie.write(blok)
                zapisane.append(str(cel_pliku))
    return zapisane


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--zrodlo", default="google_drive", help="katalog z paczkami .zip")
    parser.add_argument("--wyj-json", default="index/paczki.json")
    parser.add_argument("--wyj-md", default="docs/PLIKI_W_PACZKACH.md")
    parser.add_argument("--drive-id", action="append", default=[],
                        help="czescN=ID na Dysku Google, można powtarzać")
    parser.add_argument("--rozpakuj", help="katalog docelowy dla rozpakowanych plików")
    argumenty = parser.parse_args(argv)

    identyfikatory: dict[str, str] = {}
    for wpis in argumenty.drive_id:
        if "=" not in wpis:
            parser.error("--drive-id oczekuje czescN=ID")
        nazwa, ident = wpis.split("=", 1)
        identyfikatory[nazwa] = ident
        if not nazwa.endswith(".zip"):
            identyfikatory[nazwa + ".zip"] = ident

    paczki = sorted(Path(argumenty.zrodlo).glob("*.zip"))
    if not paczki:
        print(f"brak paczek .zip w {argumenty.zrodlo}", file=sys.stderr)
        return 1

    if argumenty.rozpakuj:
        zapisane = rozpakuj(paczki, Path(argumenty.rozpakuj))
        print(json.dumps({"rozpakowano": len(zapisane), "katalog": argumenty.rozpakuj}, ensure_ascii=False))

    dane = spis(paczki, identyfikatory)
    Path(argumenty.wyj_json).parent.mkdir(parents=True, exist_ok=True)
    Path(argumenty.wyj_json).write_text(json.dumps(dane, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    Path(argumenty.wyj_md).parent.mkdir(parents=True, exist_ok=True)
    Path(argumenty.wyj_md).write_text(markdown(dane), encoding="utf-8")
    print(json.dumps({
        "paczki": len(dane["paczki"]),
        "plikow": sum(o["plikow"] for o in dane["paczki"]),
        "wyj_json": argumenty.wyj_json,
        "wyj_md": argumenty.wyj_md,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
