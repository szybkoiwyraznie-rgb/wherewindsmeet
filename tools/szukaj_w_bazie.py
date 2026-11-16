#!/usr/bin/env python3
"""Szukanie wzorca w CAŁEJ bazie gry i nazwanie tabel, które z niego czytają.

Po co: pytania typu „czy ktokolwiek w danych odnosi się do tego wiersza napisów?”
wymagają przeglądu **wszystkich** plików `dataN`, a nie tylko tych, które akurat
znamy. Ten program robi dokładnie to i podaje nazwy tabel.

Użycie:
    python3 tools/szukaj_w_bazie.py --dane local/dane --tekst "站住"
    python3 tools/szukaj_w_bazie.py --dane local/dane --id 591148
    python3 tools/szukaj_w_bazie.py --dane local/dane --hash 13727916233045163908
    python3 tools/szukaj_w_bazie.py --dane local/dane --u64 7936467371205064225 --bez-tabel

Wyjście: jedna linia na trafienie, np.
    data212 1779 id_591148  tabele: text_msg__grey
"""

from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools import baza_gry  # noqa: E402


def pliki_danych(katalog: Path) -> list[tuple[int, Path]]:
    wynik = []
    for path in katalog.iterdir():
        nazwa = path.name
        if not nazwa.startswith("data") or not nazwa[4:].isdigit():
            continue
        wynik.append((int(nazwa[4:]), path))
    return sorted(wynik)


def indeks_tabel(katalog: Path) -> dict[tuple[int, int], set[str]]:
    """(plik danych, chunk danych) → nazwy tabel, które z tego miejsca czytają."""
    baza = baza_gry.Baza([katalog])
    mapa: dict[tuple[int, int], set[str]] = {}
    for nazwa in baza.tabele:
        try:
            polozenia = baza.polozenia(nazwa)
        except baza_gry.BazaError:
            continue
        for _, miejsce in polozenia:
            mapa.setdefault((miejsce.plik, miejsce.chunk), set()).add(nazwa.split(".")[0])
    return mapa


def wzorce(args) -> dict[str, bytes]:
    cele: dict[str, bytes] = {}
    if args.tekst is not None:
        cele[f"tekst_{args.tekst}"] = args.tekst.encode("utf-8")
    if args.id is not None:
        cele[f"id_{args.id}"] = struct.pack("<I", args.id)
    if args.hash is not None:
        cele[f"hash_{args.hash}"] = struct.pack("<Q", args.hash)
    if args.u64 is not None:
        cele[f"u64_{args.u64}"] = struct.pack("<Q", args.u64)
    return cele


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dane", required=True, help="katalog z MANIFEST, indexN, dataN")
    grupa = parser.add_mutually_exclusive_group(required=True)
    grupa.add_argument("--tekst", help="szukaj tekstu UTF-8")
    grupa.add_argument("--id", type=int, help="szukaj 32-bitowego identyfikatora")
    grupa.add_argument("--hash", type=int, help="szukaj 64-bitowego hasha tekstu")
    grupa.add_argument("--u64", type=int, help="szukaj dowolnej 64-bitowej liczby")
    parser.add_argument("--bez-tabel", action="store_true", help="nie nazywaj tabel (szybciej)")
    args = parser.parse_args(argv)

    katalog = Path(args.dane)
    if not (katalog / "MANIFEST").is_file():
        print(f"brak MANIFEST w {katalog}", file=sys.stderr)
        return 2
    szukane = wzorce(args)
    mapa = {} if args.bez_tabel else indeks_tabel(katalog)
    trafienia = 0
    for numer, path in pliki_danych(katalog):
        for chunk_index, surowy in enumerate(baza_gry.rozpakuj_chunki(path.read_bytes())):
            dane = baza_gry.rozpakuj_chunk(surowy)
            for etykieta, wzor in szukane.items():
                if wzor not in dane:
                    continue
                trafienia += 1
                tabele = sorted(mapa.get((numer, chunk_index), ()))
                opis = ", ".join(tabele) if tabele else "—"
                print(f"data{numer} {chunk_index} {etykieta}  tabele: {opis}", flush=True)
    print(f"# trafień: {trafienia}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
