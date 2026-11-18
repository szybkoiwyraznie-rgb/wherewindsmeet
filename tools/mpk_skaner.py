#!/usr/bin/env python3
"""Skaner paczek Where Winds Meet dla Windows — sonda `.mpk` + wycinanie małych bloków.

Po co: powiązania "scena -> następna scena", "POI -> sceny" i osie `.cine` nie
leżą w tabelach HD (`Package/HD/oversea`), tylko — przypuszczalnie — w paczkach
VFS (`Resources*.mpk`, `LT*.mpk`, `Patch*.mpk`). Ten skrypt odpowiada:

  1. jakie paczki i indeksy są w instalacji (ile `Resources*.mpk`, gdzie leży
     `Resources.mpkinfo` / `Patch.mpkdb`),
  2. co indeks mówi o wpisach (ile, jakie `pack_id`, offsety, pokrycie pliku),
  3. co leży pod próbkowanymi offsetami (magia EZST/ZSTD/..., entropia),
  4. czy znane kandydacje ścieżek (`client/dialogs/...` z `index/poi.jsonl`,
     wzorce `.cine` z `cine_name`) trafiają we wpisy indeksów — liczy `file_id`
     i szuka go w indeksach,
  5. (od v2) wycina SUROWE bajty trafionych bloków oraz **wszystkich** bloków
     z `LT1.mpkinfo` (skrypty klienta) oraz zrzuca `Patch.mpkdb` do JSON —
     do analizy po stronie narzędzi. Kolumny BLOB kodowane jako hex; błąd
     pojedynczej tabeli/kroku nie blokuje wyniku,
  6. (od v6) wyszukuje w `Resources*.mpk` nieskompresowane grafy JSON
     Storyline i zapisuje je do `wyciete/storyline_wyciete.jsonl`,
  7. (od v7) SONDA EZST: dla każdego małego wpisu `Resources.mpkinfo`
     odszyfrowuje AES-owy prefiks bloku EZST (czysty Python, klucz publiczny)
     i dekompresuje POCZĄTEK ramki zstd (gdy dostępny moduł zstd: Python 3.14+
     albo pakiet `zstandard`), po czym szuka sygnatur treści: magii `.cine`
     (`c159410d`), grafów Storyline, ścieżek `client/dialogs`/`.etsb`
     i benchmarku `4700001`. Trafione bloki wycina SUROWO do `wyciete/`
     (`ezst_*.bin` + `ezst_trafienia.jsonl`).

Czego ten skrypt NIE robi:
  * nie uruchamia gry i nie dotyka jej procesu,
  * nie modyfikuje żadnego pliku gry (otwiera tylko do odczytu),
  * nie wysyła niczego do sieci,
  * nie rozpakowuje paczek — wycina tylko SUROWE bloki (`wyciete/`: trafienia
    z sondażu, wszystkie wpisy `LT1.mpkinfo` i trafienia sondy EZST; limity
    64 MB/blok, 512 MB łącznie + 256 MB na sondę EZST),
  * nie zapisuje zdekodowanej treści bloków — odszyfrowany prefiks i początek
    dekompresji służą WYŁĄCZNIE sondowaniu sygnatur w pamięci; pełne
    dekodowanie odbywa się po naszej stronie.

Uruchomienie (dwuklik `SKANUJ.bat` albo ręcznie):
  python mpk_skaner.py --gra "C:\\...\\Where Winds Meet"
  python mpk_skaner.py --gra ... --wyjscie D:\\wynik --non-interactive

Wynik: folder `MPK_SKANER_WYNIK/` obok skryptu (albo `--wyjscie`) z plikami
`RAPORT.json`, `PODSUMOWANIE.txt` i całość spakowaną do
`WWM_MPK_Skaner_WYNIK.zip`. Ten ZIP wysyłamy właścicielowi — paczek `.mpk` NIE.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
import math
from pathlib import Path
import sqlite3
import struct
import sys
import zipfile
import hashlib

WERSJA = "wwm-mpk-skaner-v7"
DOMYSLNI_KANDYDACI = Path(__file__).resolve().parent / "kandydaci.jsonl"

# Magie bloków rozpoznawane w paczkach Messiah (docs/MPK_FORMAT_RESEARCH.md §1.5).
MAGIE = [
    (b"EZST", "ezst (AES-ECB prefiks + zstd)"),
    (b"ZSTD", "zstd-blok (Messiah 'ZSTD' + u32 raw_size)"),
    (b"\x28\xb5\x2f\xfd", "zstd-frame"),
    (b"ZZZ4", "zzz4 (lz4)"),
    (b"CCCC", "cccc (podwójny lz4)"),
    (b"\x02\x02\x02\x01", "tekstura (02 02 02 01)"),
    (b"RIFF", "riff (audio)"),
    (b"BKHD", "wwise-bank"),
    (b"LZMA", "lzma"),
    (b".MES", "mes (mesh?)"),
    (b"\x1bLua", "lua-skompilowany"),
    (b"<?xml", "xml"),
    (b"\xef\xbb\xbf<", "xml (BOM)"),
    (b"SQLite format 3", "sqlite"),
]

SKIP_DIRS = {".git", ".svn", "node_modules", "__pycache__"}


def _utf8() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# file_id: ścieżka VFS -> klucz indeksu (format wg dokumentacji publicznej,
# implementacja własna; patrz docs/MPK_FORMAT_RESEARCH.md §1.4)
# ---------------------------------------------------------------------------

def murmur3_32(data: bytes, seed: int = 0) -> int:
    c1, c2 = 0xCC9E2D51, 0x1B873593
    h = seed
    n = len(data) // 4 * 4
    for i in range(0, n, 4):
        k = struct.unpack_from("<I", data, i)[0]
        k = (k * c1) & 0xFFFFFFFF
        k = ((k << 15) | (k >> 17)) & 0xFFFFFFFF
        k = (k * c2) & 0xFFFFFFFF
        h ^= k
        h = ((h << 13) | (h >> 19)) & 0xFFFFFFFF
        h = (h * 5 + 0xE6546B64) & 0xFFFFFFFF
    k = 0
    tail = data[n:]
    if len(tail) >= 3:
        k ^= tail[2] << 16
    if len(tail) >= 2:
        k ^= tail[1] << 8
    if len(tail) >= 1:
        k ^= tail[0]
        k = (k * c1) & 0xFFFFFFFF
        k = ((k << 15) | (k >> 17)) & 0xFFFFFFFF
        k = (k * c2) & 0xFFFFFFFF
        h ^= k
    h ^= len(data)
    h ^= h >> 16
    h = (h * 0x85EBCA6B) & 0xFFFFFFFF
    h ^= h >> 13
    h = (h * 0xC2B2AE35) & 0xFFFFFFFF
    h ^= h >> 16
    return h


def strip_ext(path: bytes) -> bytes:
    dot, slash = path.rfind(b"."), path.rfind(b"/")
    return path[:dot] if dot > slash else path


def tail_sig(stripped: bytes) -> int:
    n = len(stripped)
    if n == 0:
        return 0
    if n == 1:
        return (stripped[0] << 24) | n
    if n == 2:
        return (stripped[1] << 24) | (stripped[0] << 16) | n
    return (
        (stripped[n - 1] << 24)
        | (stripped[n - 2] << 16)
        | (stripped[n - 3] << 8)
        | (n & 0xFF)
    )


def file_id(path: str) -> int:
    p = path.encode("utf-8")
    stripped = strip_ext(p)
    if len(stripped) in (39, 41) and len(stripped) > 2 and stripped[2:3] == b"/":
        lo = struct.unpack(">I", stripped[3:7])[0]
    else:
        lo = tail_sig(stripped)
    return (murmur3_32(p) << 32) | lo


# ---------------------------------------------------------------------------
# Inwentarz paczek
# ---------------------------------------------------------------------------

def znajdz_paczki(root: Path) -> list[dict]:
    paczki: list[dict] = []
    for sciezka in root.rglob("*.mpk"):
        if any(czesc in SKIP_DIRS for czesc in sciezka.parts):
            continue
        try:
            rozmiar = sciezka.stat().st_size
        except OSError:
            continue
        paczki.append(
            {
                "sciezka": sciezka.relative_to(root).as_posix(),
                "rozmiar": rozmiar,
            }
        )
    paczki.sort(key=lambda p: p["sciezka"])
    return paczki


def znajdz_indeksy(root: Path) -> dict:
    wynik = {"mpkinfo": [], "mpkdb": [], "mpkinfo_w_grze": 0}
    # Install root: Resources.mpkinfo
    for kandydat in [root / "Resources.mpkinfo"]:
        if kandydat.is_file():
            wynik["mpkinfo"].append(str(kandydat))
    patch_root = root / "LocalData" / "Patch"
    if patch_root.is_dir():
        for kandydat in sorted(patch_root.glob("*.mpkinfo")):
            wynik["mpkinfo"].append(str(kandydat))
        db = patch_root / "Patch.mpkdb"
        if db.is_file():
            wynik["mpkdb"].append(str(db))
    return wynik


# ---------------------------------------------------------------------------
# Odczyt indeksów
# ---------------------------------------------------------------------------

def _kontener_dla_indeksu(root: Path, mpkinfo: Path, pack_id: int) -> Path:
    stem = mpkinfo.stem
    if stem == "Resources":
        return root / ("Resources.mpk" if pack_id == 0 else f"Resources{pack_id}.mpk")
    if stem.startswith("LT") and stem[2:].isdigit():
        return mpkinfo.parent / f"LT{pack_id}.mpk"
    return mpkinfo.parent / f"Patch{pack_id}.mpk"


def parsuj_mpkinfo(root: Path, mpkinfo: Path) -> dict:
    """Zwróć wpis indeksu: statystyki + lista wpisów (id, offset, size, packed)."""
    meta: dict = {
        "plik": str(mpkinfo),
        "nazwa": mpkinfo.name,
        "ok": False,
        "powod": "",
        "wersja": None,
        "wpisow_surowych": 0,
        "wpisow": 0,
        "placeholdery": 0,
        "pack_id_hist": {},
        "offset_min": None,
        "offset_max_plus_size": None,
        "suma_rozmiarow": 0,
        "kontenery": {},
    }
    try:
        data = mpkinfo.read_bytes()
    except OSError as e:
        meta["powod"] = f"nie można odczytać: {e}"
        return meta
    if data[:4] in (b"HEX_", b"HEXB"):
        meta["powod"] = "HEX_/HEXB_ (opakowany metadanymi integralności) — to nie indeks"
        return meta
    if len(data) < 8:
        meta["powod"] = "zbyt krótki plik"
        return meta
    version, count = struct.unpack_from("<II", data, 0)
    meta["wersja"] = version
    meta["wpisow_surowych"] = count
    oczekiwane = 8 + 20 * count + 16
    if version != 3:
        meta["powod"] = f"nieobsługiwana wersja {version} (oczekiwano 3)"
        return meta
    if len(data) != oczekiwane:
        meta["powod"] = f"zła długość pliku: {len(data)} B, oczekiwano {oczekiwane} B"
        return meta

    entries = []
    pack_hist: Counter = Counter()
    placeholdery = 0
    off_min = None
    off_max_end = 0
    suma = 0
    for s0, s1, off, size, packed in struct.iter_unpack("<IIIII", data[8 : 8 + 20 * count]):
        if size == 0 or (packed & 1):
            placeholdery += 1
            continue
        pack_id = packed >> 1
        pack_hist[pack_id] += 1
        fid = (s1 << 32) | s0
        entries.append(
            {"file_id": fid, "offset": off, "size": size, "pack_id": pack_id}
        )
        off_min = off if off_min is None else min(off_min, off)
        off_max_end = max(off_max_end, off + size)
        suma += size

    kontenery: dict[int, dict] = {}
    for pack_id in sorted(pack_hist):
        sciezka = _kontener_dla_indeksu(root, mpkinfo, pack_id)
        wpis = {
            "pack_id": pack_id,
            "sciezka": str(sciezka),
            "istnieje": sciezka.is_file(),
            "wpisow": pack_hist[pack_id],
            "rozmiar_pliku": None,
            "pokrycie_pct": None,
            "offsety_fizyczne": None,
        }
        if wpis["istnieje"]:
            try:
                wpis["rozmiar_pliku"] = sciezka.stat().st_size
            except OSError:
                wpis["istnieje"] = False
        if wpis["istnieje"]:
            suma_pack = sum(e["size"] for e in entries if e["pack_id"] == pack_id)
            wpis["pokrycie_pct"] = round(100.0 * suma_pack / max(1, wpis["rozmiar_pliku"]), 1)
            kontener_entries = [e for e in entries if e["pack_id"] == pack_id]
            wpis["offsety_fizyczne"] = all(
                e["offset"] + e["size"] <= wpis["rozmiar_pliku"] for e in kontener_entries
            )
        kontenery[pack_id] = wpis

    meta.update(
        {
            "ok": True,
            "wpisow": len(entries),
            "placeholdery": placeholdery,
            "pack_id_hist": {str(k): v for k, v in sorted(pack_hist.items())},
            "offset_min": off_min,
            "offset_max_plus_size": off_max_end,
            "suma_rozmiarow": suma,
            "kontenery": kontenery,
            "_entries": entries,
        }
    )
    return meta


def parsuj_mpkdb(db: Path) -> dict:
    meta: dict = {
        "plik": str(db),
        "nazwa": db.name,
        "ok": False,
        "powod": "",
        "tabele": {},
        "wpisow": 0,
    }
    try:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        try:
            wiersze = con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
            for (table,) in wiersze:
                try:
                    (n,) = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
                except sqlite3.OperationalError:
                    n = None
                schema = []
                try:
                    for kol in con.execute(f"PRAGMA table_info({table})").fetchall():
                        schema.append(str(kol[1]))
                except sqlite3.OperationalError:
                    pass
                meta["tabele"][table] = {"wierszy": n, "kolumny": schema}
            wpisow = 0
            fids: list[int] = []
            for table in ("info0", "info1"):
                if table not in meta["tabele"]:
                    continue
                try:
                    for (v0,) in con.execute(f"SELECT v0 FROM {table}"):
                        if v0 is None or isinstance(v0, str):
                            continue
                        fid = int(v0) & 0xFFFFFFFFFFFFFFFF
                        fids.append(fid)
                        wpisow += 1
                except sqlite3.OperationalError:
                    continue
            meta["wpisow"] = wpisow
            meta["_fids"] = set(fids)
            meta["ok"] = True
        finally:
            con.close()
    except sqlite3.DatabaseError as e:
        meta["powod"] = f"nie można otworzyć jako SQLite: {e}"
    except OSError as e:
        meta["powod"] = f"nie można odczytać: {e}"
    return meta


# ---------------------------------------------------------------------------
# Próbkowanie wnętrza paczek
# ---------------------------------------------------------------------------

def entropia(bajty: bytes) -> float:
    if not bajty:
        return 0.0
    licznik = [0] * 256
    for b in bajty:
        licznik[b] += 1
    ent = 0.0
    for l in licznik:
        if l:
            p = l / len(bajty)
            ent -= p * math.log2(p)
    return round(ent, 2)


def _magia(bajty: bytes) -> str:
    for magia, opis in MAGIE:
        if bajty.startswith(magia):
            return opis
    return "nieznana/surowa"


def probkuj(kontenery: dict[int, Path], entries: list[dict], zapytan_na_pack: int = 12) -> dict:
    """Próbka kilku wejść na paczkę: magia + entropia pierwszych 4 KB."""
    per_pack: dict[int, list[dict]] = {}
    for e in entries:
        per_pack.setdefault(e["pack_id"], []).append(e)

    raport: dict[int, dict] = {}
    for pack_id, lista in sorted(per_pack.items()):
        wpis = {
            "probkowane": 0,
            "poza_kontenerem": 0,
            "magia": {},
            "entropia_proba": [],
        }
        kontener = kontenery.get(pack_id)
        if kontener is None or not kontener.is_file():
            wpis["powod"] = "kontener nie istnieje — pomijam próbkowanie"
            raport[pack_id] = wpis
            continue
        try:
            rozmiar = kontener.stat().st_size
        except OSError:
            wpis["powod"] = "nie można ustalić rozmiaru"
            raport[pack_id] = wpis
            continue
        krok = max(1, len(lista) // zapytan_na_pack)
        probka = lista[::krok][:zapytan_na_pack]
        try:
            fh = open(kontener, "rb")
        except OSError as e:
            wpis["powod"] = f"nie można otworzyć: {e}"
            raport[pack_id] = wpis
            continue
        with fh:
            for e in probka:
                if e["offset"] + 1 > rozmiar:
                    wpis["poza_kontenerem"] += 1
                    continue
                fh.seek(e["offset"])
                blok = fh.read(min(4096, max(1, rozmiar - e["offset"])))
                wpis["probkowane"] += 1
                magia = _magia(blok)
                wpis["magia"][magia] = wpis["magia"].get(magia, 0) + 1
                wpis["entropia_proba"].append(entropia(blok))
        wpis["magia"] = dict(sorted(wpis["magia"].items(), key=lambda kv: -kv[1]))
        if wpis["entropia_proba"]:
            wpis["entropia_srednia"] = round(
                sum(wpis["entropia_proba"]) / len(wpis["entropia_proba"]), 2
            )
        raport[pack_id] = wpis
    return raport


# ---------------------------------------------------------------------------
# Kandydaci ścieżek
# ---------------------------------------------------------------------------

def wczytaj_kandydatow(sciezka: Path) -> list[dict]:
    kandydaci: list[dict] = []
    if not sciezka.is_file():
        return kandydaci
    with open(sciezka, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                wpis = json.loads(line)
            except json.JSONDecodeError:
                continue
            if wpis.get("sciezka"):
                kandydaci.append(wpis)
    return kandydaci


def haszuj_kandydatow(
    kandydaci: list[dict],
    indeksy: list[tuple[str, dict[int, dict]]],
    mpkdb_fids: list[tuple[str, set[int]]],
) -> list[dict]:
    trafienia: list[dict] = []
    for kand in kandydaci:
        fid = file_id(kand["sciezka"])
        for nazwa, lookup in indeksy:
            e = lookup.get(fid)
            if e is not None:
                trafienia.append(
                    {
                        "sciezka": kand["sciezka"],
                        "pochodzenie": kand.get("pochodzenie", ""),
                        "file_id": f"{fid:016x}",
                        "indeks": nazwa,
                        "pack_id": e["pack_id"],
                        "offset": e["offset"],
                        "size": e["size"],
                    }
                )
        for nazwa, fids in mpkdb_fids:
            if fid in fids:
                trafienia.append(
                    {
                        "sciezka": kand["sciezka"],
                        "pochodzenie": kand.get("pochodzenie", ""),
                        "file_id": f"{fid:016x}",
                        "indeks": nazwa,
                        "pack_id": None,
                        "offset": None,
                        "size": None,
                    }
                )
    return trafienia


# ---------------------------------------------------------------------------
# AES-256-ECB (czysty Python, tylko stdlib) — prefiks bloków EZST
# ---------------------------------------------------------------------------
# Format EZST (docs/MPK_FORMAT_RESEARCH.md §1.5, publiczny algorytm MIT
# z Zhincore/wwm-messiah-tools): `EZST` + u32 raw_size + payload, w którym
# pierwsze floor16(min(len, 256)) bajtów jest zaszyfrowane AES-256-ECB,
# a reszta to zwykła ramka zstd. Klucz jest opublikowany w tym repo (to
# "drzwi frontowe", nie kryptografia). Do sondowania zawartości wystarczy
# odszyfrować prefiks i zdekompresować początek ramki.

EZST_KLUCZ = struct.pack(
    "<4Q", 0x556A586E32723575, 0x38782F913F152867, 0x2D3B615062536756, 0x6B59703373367639
)

_SBOX = bytes.fromhex(
    "637c777bf26b6fc53001672bfed7ab76ca82c97dfa5947f0add4a2af9ca472c0"
    "b7fd9326363ff7cc34a5e5f171d8311504c723c31896059a071280e2eb27b275"
    "09832c1a1b6e5aa0523bd6b329e32f8453d100ed20fcb15b6acbbe394a4c58cf"
    "d0efaafb434d338545f9027f503c9fa851a3408f929d38f5bcb6da2110fff3d2"
    "cd0c13ec5f974417c4a77e3d645d197360814fdc222a908846eeb814de5e0bdb"
    "e0323a0a4906245cc2d3ac629195e479e7c8376d8dd54ea96c56f4ea657aae08"
    "ba78252e1ca6b4c6e8dd741f4bbd8b8a703eb5664803f60e613557b986c11d9e"
    "e1f8981169d98e949b1e87e9ce5528df8ca1890dbfe6426841992d0fb054bb16"
)
_INV_SBOX = bytearray(256)
for _i, _s in enumerate(_SBOX):
    _INV_SBOX[_s] = _i
_INV_SBOX = bytes(_INV_SBOX)


def _gf_mul(a: int, b: int) -> int:
    wynik = 0
    while b:
        if b & 1:
            wynik ^= a
        a <<= 1
        if a & 0x100:
            a ^= 0x11B
        b >>= 1
    return wynik


_MUL = {n: bytes(_gf_mul(n, x) for x in range(256)) for n in (2, 3, 9, 11, 13, 14)}
_RCON = (0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1B, 0x36, 0x6C)


def _aes256_klucze_rund(klucz: bytes) -> list[bytes]:
    """Rozwinięcie klucza AES-256: 15 kluczy rund po 16 B."""
    slowa = [klucz[4 * i : 4 * i + 4] for i in range(8)]
    for i in range(8, 60):
        temp = slowa[i - 1]
        if i % 8 == 0:
            temp = bytes(
                (
                    _SBOX[temp[1]] ^ _RCON[i // 8 - 1],
                    _SBOX[temp[2]],
                    _SBOX[temp[3]],
                    _SBOX[temp[0]],
                )
            )
        elif i % 8 == 4:
            temp = bytes(_SBOX[b] for b in temp)
        slowa.append(bytes(x ^ y for x, y in zip(slowa[i - 8], temp)))
    return [b"".join(slowa[4 * r : 4 * r + 4]) for r in range(15)]


_SHIFT = (0, 5, 10, 15, 4, 9, 14, 3, 8, 13, 2, 7, 12, 1, 6, 11)
_INV_SHIFT = (0, 13, 10, 7, 4, 1, 14, 11, 8, 5, 2, 15, 12, 9, 6, 3)


def _aes_blok_szyfruj(blok: bytes, rundy: list[bytes]) -> bytes:
    """Szyfrowanie pojedynczego bloku (potrzebne tylko testom syntetycznym)."""
    stan = bytes(x ^ y for x, y in zip(blok, rundy[0]))
    m2, m3 = _MUL[2], _MUL[3]
    for r in range(1, 14):
        stan = bytes(_SBOX[stan[_SHIFT[i]]] for i in range(16))
        nowy = bytearray(16)
        for c in range(4):
            a0, a1, a2, a3 = stan[4 * c : 4 * c + 4]
            nowy[4 * c + 0] = m2[a0] ^ m3[a1] ^ a2 ^ a3
            nowy[4 * c + 1] = a0 ^ m2[a1] ^ m3[a2] ^ a3
            nowy[4 * c + 2] = a0 ^ a1 ^ m2[a2] ^ m3[a3]
            nowy[4 * c + 3] = m3[a0] ^ a1 ^ a2 ^ m2[a3]
        stan = bytes(x ^ y for x, y in zip(nowy, rundy[r]))
    stan = bytes(_SBOX[stan[_SHIFT[i]]] for i in range(16))
    return bytes(x ^ y for x, y in zip(stan, rundy[14]))


def _aes_blok_odszyfruj(blok: bytes, rundy: list[bytes]) -> bytes:
    stan = bytes(x ^ y for x, y in zip(blok, rundy[14]))
    m9, m11, m13, m14 = _MUL[9], _MUL[11], _MUL[13], _MUL[14]
    for r in range(13, 0, -1):
        stan = bytes(_INV_SBOX[stan[_INV_SHIFT[i]]] for i in range(16))
        stan = bytes(x ^ y for x, y in zip(stan, rundy[r]))
        nowy = bytearray(16)
        for c in range(4):
            a0, a1, a2, a3 = stan[4 * c : 4 * c + 4]
            nowy[4 * c + 0] = m14[a0] ^ m11[a1] ^ m13[a2] ^ m9[a3]
            nowy[4 * c + 1] = m9[a0] ^ m14[a1] ^ m11[a2] ^ m13[a3]
            nowy[4 * c + 2] = m13[a0] ^ m9[a1] ^ m14[a2] ^ m11[a3]
            nowy[4 * c + 3] = m11[a0] ^ m13[a1] ^ m9[a2] ^ m14[a3]
        stan = bytes(nowy)
    stan = bytes(_INV_SBOX[stan[_INV_SHIFT[i]]] for i in range(16))
    return bytes(x ^ y for x, y in zip(stan, rundy[0]))


_RUNDY_EZST: list[bytes] | None = None


def ezst_odszyfruj_prefiks(payload: bytes) -> bytes:
    """Odszyfruj AES-owy prefiks payloadu EZST (floor16(min(len, 256)) bajtów)."""
    global _RUNDY_EZST
    if _RUNDY_EZST is None:
        _RUNDY_EZST = _aes256_klucze_rund(EZST_KLUCZ)
    n = min(len(payload) // 16 * 16, 256)
    kawalki = [
        _aes_blok_odszyfruj(payload[i : i + 16], _RUNDY_EZST) for i in range(0, n, 16)
    ]
    return b"".join(kawalki) + payload[n:]


def ezst_zaszyfruj_prefiks(payload: bytes) -> bytes:
    """Odwrotność `ezst_odszyfruj_prefiks` — wyłącznie dla testów syntetycznych."""
    global _RUNDY_EZST
    if _RUNDY_EZST is None:
        _RUNDY_EZST = _aes256_klucze_rund(EZST_KLUCZ)
    n = min(len(payload) // 16 * 16, 256)
    kawalki = [
        _aes_blok_szyfruj(payload[i : i + 16], _RUNDY_EZST) for i in range(0, n, 16)
    ]
    return b"".join(kawalki) + payload[n:]


def _zstd_backend():
    """Backend zstd do sondy zawartości: (nazwa, dekompresuj(dane, max_wyjscie)).

    Zwraca None, gdy w Pythonie właściciela nie ma ani `compression.zstd`
    (Python 3.14+), ani pakietu `zstandard`. Sonda zawartości EZST jest wtedy
    uczciwie pomijana — kit nadal niczego nie pobiera z sieci.
    Ucięte wejście jest normalne (czytamy tylko głowę bloku): backend ma
    zwracać tyle wyjścia, ile się da.
    """
    try:
        from compression import zstd as _z  # Python 3.14+

        def _dek_stdlib(dane: bytes, max_wyjscie: int) -> bytes:
            try:
                return _z.ZstdDecompressor().decompress(dane, max_wyjscie)
            except _z.ZstdError:
                return b""

        return ("compression.zstd", _dek_stdlib)
    except ImportError:
        pass
    try:
        import io

        import zstandard as _zs

        def _dek_zstandard(dane: bytes, max_wyjscie: int) -> bytes:
            try:
                czytnik = _zs.ZstdDecompressor().stream_reader(io.BytesIO(dane))
                return czytnik.read(max_wyjscie)
            except _zs.ZstdError:
                return b""
            except OSError:
                return b""

        return ("zstandard", _dek_zstandard)
    except ImportError:
        return None


# Sygnatury szukane w ZDEKODOWANEJ głowie bloku (i w blokach gołych):
SYGNATURY_TRESCI: tuple[tuple[str, bytes], ...] = (
    # oś czasu cutsceny — magic dekodowanego pliku .cine (priorytet 3)
    ("cine_magic", bytes.fromhex("c159410d")),
    # grafy Storyline (priorytet 1) — jak w skanie JSON nieskompresowanym
    ("storyline_json", b'{"Variables":'),
    ("storyline_node", b"GameLevelStorylineDialogsPlayNode"),
    ("storyline_cutscene", b"DialogCutsceneSequenceNode"),
    # skrypty klienta wskazywane przez POI (priorytet 2)
    ("etsb_sciezka", b"client/dialogs"),
    ("etsb_ext", b".etsb"),
    # benchmark priorytetu 1: łańcuch scen 4700001 -> 4700041 -> 4700352
    ("benchmark_4700001", b"4700001"),
    ("benchmark_4700001_u32", struct.pack("<I", 4700001)),
)


def skanuj_ezst_w_indeksie(
    root: Path,
    wyjscie: Path,
    meta_mpkinfo: dict,
    entries: list[dict],
    max_blok_sondy: int = 4 << 20,
    limit_zapisu: int = 256 << 20,
    glowa_wejscia: int = 16 * 1024,
    glowa_wyjscia: int = 64 * 1024,
) -> dict:
    """Sonda zawartości bloków EZST/ZSTD wpisów indeksu + wycinanie trafień (v7).

    Dla każdego wpisu `Resources.mpkinfo` (z pominięciem wpisów > max_blok_sondy —
    duże zasoby to tekstury/dźwięk, a szukane pliki są małe):
      1. czyta głowę bloku spod offsetu,
      2. EZST: odszyfrowuje prefiks AES (czysty Python) i dekompresuje początek
         ramki zstd; ZSTD/zstd-frame: dekompresuje wprost; inne magie: patrzy
         na gołe bajty,
      3. szuka sygnatur treści (`SYGNATURY_TRESCI`),
      4. trafienia zapisuje SUROWO do `wyciete/ezst_<pack>_<fileid>.bin`
         i do `wyciete/ezst_trafienia.jsonl`.

    Bez backendu zstd (patrz `_zstd_backend`) sonda treści EZST/ZSTD jest
    pomijana; sprawdzane są wtedy tylko bloki gołe, a raport mówi to wprost.
    """
    wynik: dict = {
        "ok": True,
        "indeks": meta_mpkinfo.get("nazwa"),
        "backend_zstd": None,
        "wpisow": len(entries),
        "sondowanych": 0,
        "pominietych_duzych": 0,
        "magie": {},
        "trafien": 0,
        "wycietych": 0,
        "zapisano_bajtow": 0,
        "limit_osiagniety": False,
        "sygnatury": {},
        "bledy": 0,
    }
    backend = _zstd_backend()
    if backend is not None:
        wynik["backend_zstd"] = backend[0]
    dekompresuj = backend[1] if backend is not None else None

    wyciete = wyjscie / "wyciete"
    wyciete.mkdir(parents=True, exist_ok=True)
    jsonl = wyciete / "ezst_trafienia.jsonl"
    magie: Counter = Counter()
    sygnatury: Counter = Counter()
    zapisano = 0

    kontenery = {
        int(pid): Path(k["sciezka"])
        for pid, k in meta_mpkinfo.get("kontenery", {}).items()
        if k.get("istnieje")
    }
    # Sekwencyjny odczyt: wpisy po (kontener, offset).
    plan: dict[int, list[dict]] = {}
    for e in entries:
        if e["size"] > max_blok_sondy:
            wynik["pominietych_duzych"] += 1
            continue
        plan.setdefault(e["pack_id"], []).append(e)

    with jsonl.open("w", encoding="utf-8") as out_f:
        for pack_id in sorted(plan):
            kontener = kontenery.get(pack_id)
            if kontener is None or not kontener.is_file():
                continue
            wpisy = sorted(plan[pack_id], key=lambda e: e["offset"])
            try:
                with kontener.open("rb") as fh:
                    for e in wpisy:
                        try:
                            fh.seek(e["offset"])
                            glowa = fh.read(min(e["size"], glowa_wejscia))
                        except OSError:
                            wynik["bledy"] += 1
                            continue
                        if len(glowa) < 8:
                            continue
                        wynik["sondowanych"] += 1
                        magia = glowa[:4]
                        tresc = b""
                        if magia == b"EZST":
                            magie["EZST"] += 1
                            if dekompresuj is not None:
                                tresc = dekompresuj(
                                    ezst_odszyfruj_prefiks(glowa[8:]), glowa_wyjscia
                                )
                                if not tresc:
                                    # prefiks krótszy niż floor16(256) — spróbuj bez AES
                                    tresc = dekompresuj(glowa[8:], glowa_wyjscia)
                        elif magia == b"ZSTD":
                            magie["ZSTD"] += 1
                            if dekompresuj is not None:
                                tresc = dekompresuj(glowa[8:], glowa_wyjscia)
                        elif magia == b"\x28\xb5\x2f\xfd":
                            magie["zstd-frame"] += 1
                            if dekompresuj is not None:
                                tresc = dekompresuj(glowa, glowa_wyjscia)
                        else:
                            magie["gole"] += 1
                            tresc = glowa
                        if not tresc:
                            continue
                        trafione = [n for n, syg in SYGNATURY_TRESCI if syg in tresc]
                        if not trafione:
                            continue
                        wynik["trafien"] += 1
                        for n in trafione:
                            sygnatury[n] += 1
                        wpis_raportu = {
                            "indeks": meta_mpkinfo.get("nazwa"),
                            "kontener": kontener.name,
                            "pack_id": pack_id,
                            "offset": e["offset"],
                            "size": e["size"],
                            "file_id": f"{e['file_id']:016x}",
                            "magia": magia.decode("ascii", "replace")
                            if magia in (b"EZST", b"ZSTD")
                            else magia.hex(),
                            "sygnatury": trafione,
                            "wyciety": False,
                        }
                        if (
                            zapisano + e["size"] <= limit_zapisu
                            and e["size"] <= MAX_BLOK
                        ):
                            try:
                                fh.seek(e["offset"])
                                blok = fh.read(e["size"])
                                if len(blok) == e["size"]:
                                    nazwa = f"ezst_{pack_id}_{e['file_id']:016x}.bin"
                                    (wyciete / nazwa).write_bytes(blok)
                                    zapisano += len(blok)
                                    wynik["wycietych"] += 1
                                    wpis_raportu["wyciety"] = True
                                    wpis_raportu["plik"] = nazwa
                            except OSError:
                                wynik["bledy"] += 1
                        else:
                            wynik["limit_osiagniety"] = wynik["limit_osiagniety"] or (
                                zapisano + e["size"] > limit_zapisu
                            )
                        out_f.write(json.dumps(wpis_raportu, ensure_ascii=False) + "\n")
            except OSError:
                wynik["bledy"] += 1
                continue
            print(
                f"        {kontener.name}: wpisów {len(wpisy)}, "
                f"trafień dotąd {wynik['trafien']}, wyciętych {wynik['wycietych']}"
            )
    wynik["magie"] = dict(magie)
    wynik["sygnatury"] = dict(sygnatury)
    wynik["zapisano_bajtow"] = zapisano
    return wynik


# ---------------------------------------------------------------------------
# Wycinanie surowych bloków (bramka 2) — bez dekodowania EZST/ZSTD
# ---------------------------------------------------------------------------

MAX_BLOK = 64 << 20
MAX_RAZEM = 512 << 20


def _wytnij_bloki(root: Path, pozycje: list[dict], cel: Path, etykieta: str) -> dict:
    """Wytnij surowe bloki wg listy {nazwa_indeksu, pack_id, offset, size, file_id(hex)}.

    Zwraca statystykę; każdy błąd pojedynczego bloku jest raportowany, ale nie
    przerywa całości. Zapisane jako <etykieta>_<file_id>.bin w `cel/wyciete`.
    """
    wyciete = cel / "wyciete"
    wyciete.mkdir(parents=True, exist_ok=True)
    stat = {"etykieta": etykieta, "pozycji": len(pozycje), "ok": 0, "bledy": [], "bajtow": 0}
    razem = 0
    kontenery: dict[tuple[str, int], Path] = {}
    for poz in pozycje:
        try:
            klucz = (poz["nazwa_indeksu"], int(poz["pack_id"]))
            kontener = kontenery.get(klucz)
            if kontener is None:
                if poz.get("_indeks_sciezka"):
                    fake_index = Path(poz["_indeks_sciezka"])
                elif poz["nazwa_indeksu"] == "Resources.mpkinfo":
                    fake_index = root / "Resources.mpkinfo"
                elif (root / "LocalData" / "Patch" / poz["nazwa_indeksu"]).is_file():
                    fake_index = root / "LocalData" / "Patch" / poz["nazwa_indeksu"]
                else:
                    fake_index = root / poz["nazwa_indeksu"]
                kontener = _kontener_dla_indeksu(root, fake_index, int(poz["pack_id"]))
                kontenery[klucz] = kontener
            if not kontener.is_file():
                stat["bledy"].append({"plik": poz.get("plik", "?"), "blad": f"brak kontenera {kontener}"})
                continue
            size = int(poz["size"])
            if size <= 0 or size > MAX_BLOK:
                stat["bledy"].append({"plik": poz.get("plik", "?"), "blad": f"podejrzany rozmiar {size}"})
                continue
            if razem + size > MAX_RAZEM:
                stat["bledy"].append({"plik": poz.get("plik", "?"), "blad": "przekroczono limit 512 MB na uruchomienie"})
                continue
            with open(kontener, "rb") as fh:
                fh.seek(int(poz["offset"]))
                blok = fh.read(size)
            if len(blok) != size:
                stat["bledy"].append({"plik": poz.get("plik", "?"), "blad": f"krótki odczyt: {len(blok)}/{size}"})
                continue
            nazwa = f"{etykieta}_{int(poz['file_id']):016x}.bin"
            (wyciete / nazwa).write_bytes(blok)
            stat["ok"] += 1
            stat["bajtow"] += len(blok)
            razem += len(blok)
        except (OSError, KeyError, ValueError) as e:
            stat["bledy"].append({"plik": poz.get("plik", "?"), "blad": str(e)})
    return stat


def wytnij_trafienia(root: Path, wyjscie: Path, trafienia: list[dict]) -> dict:
    pozycje = []
    for t in trafienia:
        if t.get("offset") is None or t.get("size") is None:
            continue
        pozycje.append(
            {
                "nazwa_indeksu": t.get("indeks", "Resources.mpkinfo"),
                "pack_id": t["pack_id"],
                "offset": t["offset"],
                "size": t["size"],
                "file_id": int(t["file_id"], 16) if isinstance(t.get("file_id"), str) else t.get("file_id"),
                "plik": t.get("sciezka", "?"),
                "_indeks_sciezka": None,
            }
        )
    return _wytnij_bloki(root, pozycje, wyjscie, "trafienie")


def wytnij_z_indeksu(root: Path, wyjscie: Path, nazwa_indeksu: str, prefiks: str) -> dict:
    """Wytnij wszystkie wpisy wskazanego indeksu (np. LT1.mpkinfo)."""
    patch_root = root / "LocalData" / "Patch"
    indeks = patch_root / nazwa_indeksu if (patch_root / nazwa_indeksu).is_file() else root / nazwa_indeksu
    if not indeks.is_file():
        return {"etykieta": prefiks, "pozycji": 0, "ok": 0, "bledy": [{"blad": f"brak indeksu {nazwa_indeksu}"}], "bajtow": 0}
    meta = parsuj_mpkinfo(root, indeks)
    if not meta["ok"]:
        return {"etykieta": prefiks, "pozycji": 0, "ok": 0, "bledy": [{"blad": f"indeks nieczytelny: {meta['powod']}"}], "bajtow": 0}
    pozycje = []
    for e in meta["_entries"]:
        pozycje.append(
            {
                "nazwa_indeksu": meta["nazwa"],
                "pack_id": e["pack_id"],
                "offset": e["offset"],
                "size": e["size"],
                "file_id": e["file_id"],
                "plik": meta["nazwa"],
                "_indeks_sciezka": str(indeks),
            }
        )
    return _wytnij_bloki(root, pozycje, wyjscie, prefiks)


def skanuj_storyline_w_paczkach(root: Path, wyjscie: Path, limit_bajtow: int = 80 * 1024 * 1024) -> dict:
    """Skanuje Resources*.mpk pod kątem kompletnych grafów JSON Storyline (priorytet 1)."""
    wyciete = wyjscie / "wyciete"
    wyciete.mkdir(parents=True, exist_ok=True)
    jsonl_path = wyciete / "storyline_wyciete.jsonl"
    wzorce = (
        b"GameLevelStorylineDialogsPlayNode",
        b"DialogCutsceneSequenceNode",
        b"DialogNode",
        b"BranchDialog",
        b"TrackTaskNode",
    )
    marker = b'{"Variables":'
    przeszukano = 0
    grafow = 0
    zapisano_b = 0
    decoder = json.JSONDecoder()
    with jsonl_path.open("w", encoding="utf-8") as out_f:
        for pak in sorted(root.rglob("Resources*.mpk")):
            przeszukano += 1
            try:
                rozmiar = pak.stat().st_size
                with pak.open("rb") as f:
                    okno = 8 * 1024 * 1024
                    zakladka = 512 * 1024
                    offset = 0
                    poprzedni_koniec = b""
                    widziane_off = set()
                    while offset < rozmiar:
                        blok = f.read(okno)
                        if not blok:
                            break
                        bufor = poprzedni_koniec + blok
                        baza = offset - len(poprzedni_koniec)
                        pos = 0
                        while True:
                            idx = bufor.find(marker, pos)
                            if idx == -1:
                                break
                            pos = idx + len(marker)
                            abs_off = baza + idx
                            if abs_off in widziane_off:
                                continue
                            # Szybki filtr przed dekodowaniem JSON
                            okno_podgladu = bufor[idx:idx + 262144]
                            if not any(w in okno_podgladu for w in wzorce):
                                continue
                            try:
                                tekst = okno_podgladu.decode("utf-8", errors="ignore")
                                obj, _ = decoder.raw_decode(tekst)
                            except Exception:
                                continue
                            widziane_off.add(abs_off)
                            linia = json.dumps(
                                {"paczka": pak.name, "offset": abs_off, "graf": obj},
                                ensure_ascii=False,
                            ) + "\n"
                            lb = len(linia.encode("utf-8"))
                            if zapisano_b + lb > limit_bajtow:
                                return {
                                    "ok": True,
                                    "przeszukano_paczek": przeszukano,
                                    "trafien": grafow,
                                    "zapisano_bajtow": zapisano_b,
                                    "limit_osiagniety": True,
                                    "lista": [],
                                }
                            out_f.write(linia)
                            zapisano_b += lb
                            grafow += 1
                        poprzedni_koniec = bufor[-zakladka:] if len(bufor) >= zakladka else bufor
                        offset += len(blok)
            except Exception:
                pass
    return {
        "ok": True,
        "przeszukano_paczek": przeszukano,
        "trafien": grafow,
        "zapisano_bajtow": zapisano_b,
        "limit_osiagniety": False,
        "lista": [],
    }


def _json_safe(val):
    """Wartość SQLite → coś, co zawsze przejdzie przez json.dumps.

    Kolumny BLOB (bytes/bytearray/memoryview) — np. w tabeli `meta` — kodujemy
    jako hex; duże bloki tylko podglądem początku + rozmiarem.
    """
    if isinstance(val, (bytes, bytearray, memoryview)):
        raw = bytes(val)
        limit = 256
        opis = {
            "__bytes__": True,
            "rozmiar": len(raw),
            "hex": raw[:limit].hex(),
        }
        if len(raw) > limit:
            opis["uciniete"] = True
        return opis
    if isinstance(val, (int, float, str, bool)) or val is None:
        return val
    return str(val)


def zrzut_mpkdb(root: Path, wyjscie: Path) -> dict:
    """Zrzut Patch.mpkdb do JSON (schema + wszystkie wiersze meta/pak + info0/info1).

    Błąd pojedynczej tabeli nie wywraca całości; funkcja nigdy nie rzuca
    wyjątku (błąd trafia do wynik["tabele"][tabela]["blad"]).
    """
    db = root / "LocalData" / "Patch" / "Patch.mpkdb"
    wynik: dict = {"plik": str(db), "ok": False, "powod": "", "tabele": {}}
    if not db.is_file():
        wynik["powod"] = "brak LocalData/Patch/Patch.mpkdb"
        return _zapisz_mpkdb_dump(wyjscie, wynik)
    try:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        try:
            tabele = [r[0] for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()]
            for tabela in tabele:
                wpis: dict = {}
                try:
                    kolumny = [k[1] for k in con.execute(f'PRAGMA table_info("{tabela}")').fetchall()]
                    wiersze = [
                        [_json_safe(v) for v in row]
                        for row in con.execute(f'SELECT * FROM "{tabela}"')
                    ]
                    wpis = {"kolumny": kolumny, "wiersze": wiersze}
                except (sqlite3.DatabaseError, OSError, ValueError) as e:
                    wpis = {"blad": str(e)}
                wynik["tabele"][tabela] = wpis
            wynik["ok"] = all("blad" not in v for v in wynik["tabele"].values())
            if not wynik["ok"]:
                wynik["powod"] = "część tabel nieodczytana — patrz pola 'blad'"
        finally:
            con.close()
    except (sqlite3.DatabaseError, OSError) as e:
        wynik["powod"] = str(e)
    return _zapisz_mpkdb_dump(wyjscie, wynik)


def _zapisz_mpkdb_dump(wyjscie: Path, wynik: dict) -> dict:
    try:
        (wyjscie / "mpkdb_dump.json").write_text(
            json.dumps(wynik, ensure_ascii=False, indent=1), encoding="utf-8"
        )
    except (OSError, TypeError, ValueError) as e:
        # ostatnia linia obrony: zawsze zapisz coś, żeby diagnoza była możliwa
        (wyjscie / "mpkdb_dump.json").write_text(
            json.dumps(
                {"ok": False, "powod": f"serializacja nieudana: {e}", "sciezka": wynik.get("plik")},
                ensure_ascii=False, indent=1,
            ),
            encoding="utf-8",
        )
        wynik = {"ok": False, "powod": str(e), "tabele": {}}
    return wynik


def _zapisz_zip(zrodlo: Path, cel: Path) -> None:
    with zipfile.ZipFile(cel, "w", zipfile.ZIP_DEFLATED) as zf:
        for plik in sorted(zrodlo.rglob("*")):
            if plik.is_file():
                zf.write(plik, plik.relative_to(zrodlo))


def _sha256(plik: Path) -> str:
    h = hashlib.sha256()
    with open(plik, "rb") as fh:
        for kawal in iter(lambda: fh.read(1 << 20), b""):
            h.update(kawal)
    return h.hexdigest()


def buduj_raport(args: argparse.Namespace) -> int:
    root = Path(args.gra).expanduser().resolve()
    if not root.is_dir():
        print(f"BŁĄD: katalog gry nie istnieje: {root}")
        return 2

    wyjscie = Path(args.wyjscie).expanduser().resolve() if args.wyjscie else (
        Path(__file__).resolve().parent / "MPK_SKANER_WYNIK"
    )
    wyjscie.mkdir(parents=True, exist_ok=True)

    print(f"Skaner paczek WWM {WERSJA}")
    print(f"Katalog gry: {root}")
    print(f"Wyniki do:   {wyjscie}")
    print()

    print("[1/5] Szukam paczek *.mpk ...")
    paczki = znajdz_paczki(root)
    suma_mpk = sum(p["rozmiar"] for p in paczki)
    print(f"      znaleziono {len(paczki)} paczek, razem {suma_mpk:,} B".replace(",", " "))

    print("[2/5] Szukam indeksów (.mpkinfo / Patch.mpkdb) ...")
    indeksy = znajdz_indeksy(root)
    print(f"      .mpkinfo: {len(indeksy['mpkinfo'])}, Patch.mpkdb: {len(indeksy['mpkdb'])}")

    raport: dict = {
        "wersja_skanera": WERSJA,
        "katalog_gry": str(root),
        "paczki": paczki,
        "paczki_suma_bajtow": suma_mpk,
        "indeksy_znalezione": indeksy,
        "mpkinfo": [],
        "mpkdb": [],
        "trafienia_kandydatow": [],
        "kandydaci_wczytani": 0,
    }

    mpkinfo_lookup: list[tuple[str, dict[int, dict]]] = []
    probki: dict[str, dict] = {}
    ezst_cel: tuple[dict, list[dict]] | None = None

    for mpkinfo_path in indeksy["mpkinfo"]:
        meta = parsuj_mpkinfo(root, Path(mpkinfo_path))
        entries = meta.pop("_entries", [])
        if meta.get("ok") and meta.get("nazwa") == "Resources.mpkinfo":
            ezst_cel = (meta, entries)
        lookup = {e["file_id"]: e for e in entries}
        mpkinfo_lookup.append((meta["nazwa"], lookup))
        if meta["ok"]:
            kontenery = {
                int(pid): Path(k["sciezka"]) for pid, k in meta["kontenery"].items()
            }
            probkowane = probkuj(kontenery, entries, zapytan_na_pack=args.probka)
            probki[meta["nazwa"]] = probkowane
        print(
            f"      {meta['nazwa']}: "
            + (
                f"wpisów {meta['wpisow']}, paczek {len(meta['pack_id_hist'])}, ok"
                if meta["ok"]
                else f"POMINIĘTY ({meta['powod']})"
            )
        )
        meta["probkowanie"] = probki.get(meta["nazwa"], {})
        raport["mpkinfo"].append(meta)

    mpkdb_fids: list[tuple[str, set[int]]] = []
    for db_path in indeksy["mpkdb"]:
        meta = parsuj_mpkdb(Path(db_path))
        fids = meta.pop("_fids", set())
        if meta["ok"]:
            mpkdb_fids.append((meta["nazwa"], fids))
            print(f"      {meta['nazwa']}: wpisów {meta['wpisow']}, ok")
        else:
            print(f"      {meta['nazwa']}: POMINIĘTY ({meta['powod']})")
        raport["mpkdb"].append(meta)

    print("[3/5] Haszuję kandydatów ścieżek ...")
    kandydat_path = Path(args.kandydaci) if args.kandydaci else DOMYSLNI_KANDYDACI
    kandydaci = wczytaj_kandydatow(kandydat_path)
    raport["kandydaci_wczytani"] = len(kandydaci)
    raport["plik_kandydatow"] = str(kandydat_path)
    trafienia = haszuj_kandydatow(kandydaci, mpkinfo_lookup, mpkdb_fids)
    raport["trafienia_kandydatow"] = trafienia
    print(f"      kandydatów {len(kandydaci)}, trafień {len(trafienia)}")

    wycinanie: list[dict] = []
    if not args.bez_wycinania:
        try:
            print("[4/5] Wycinam surowe bloki (trafienia + LT1.mpk) i zrzut Patch.mpkdb ...")
            w1 = wytnij_trafienia(root, wyjscie, trafienia)
            wycinanie.append(w1)
            print(f"      trafienia: wycięto {w1['ok']}/{w1['pozycji']} ({w1['bajtow']} B)")
            w2 = wytnij_z_indeksu(root, wyjscie, "LT1.mpkinfo", "lt1")
            wycinanie.append(w2)
            print(f"      LT1.mpkinfo: wycięto {w2['ok']}/{w2['pozycji']} ({w2['bajtow']} B)")
        except Exception as e:  # nigdy nie blokuj powstania ZIPa z tym, co już jest
            wycinanie.append({"etykieta": "wycinanie", "pozycji": 0, "ok": 0,
                              "bledy": [{"blad": f"krok wycinania przerwany: {e}"}], "bajtow": 0})
            print(f"      UWAGA: krok wycinania przerwany: {e}")
        try:
            w3 = zrzut_mpkdb(root, wyjscie)
            print(
                "      Patch.mpkdb: "
                + (
                    f"zrzucono {sum(len(t.get('wiersze', [])) for t in w3['tabele'].values())} wierszy"
                    if w3.get("ok")
                    else f"POMINIĘTY ({w3.get('powod')})"
                )
            )
            raport["mpkdb_zrzut"] = (
                {"ok": True, "tabele": {t: len(v.get("wiersze", [])) for t, v in w3["tabele"].items()}}
                if w3.get("ok")
                else {"ok": False, "powod": w3.get("powod")}
            )
        except Exception as e:
            raport["mpkdb_zrzut"] = {"ok": False, "powod": f"wyjątek: {e}"}
            print(f"      UWAGA: zrzut Patch.mpkdb przerwany: {e}")
        try:
            w4 = skanuj_storyline_w_paczkach(root, wyjscie)
            raport["resources_storyline"] = {k: v for k, v in w4.items() if k != "lista"}
            print(
                f"      Resources*.mpk (storyline/sceny): przeszukano {w4['przeszukano_paczek']} paczek, "
                f"trafień {w4['trafien']} ({w4['zapisano_bajtow']} B)"
            )
        except Exception as e:
            raport["resources_storyline"] = {"ok": False, "powod": str(e)}
            print(f"      UWAGA: skanowanie Resources*.mpk przerwane: {e}")
        if args.bez_ezst:
            raport["ezst_sonda"] = {"ok": False, "powod": "--bez-ezst"}
            print("      (--bez-ezst: pomijam sondę zawartości bloków EZST)")
        elif ezst_cel is None:
            raport["ezst_sonda"] = {"ok": False, "powod": "brak czytelnego Resources.mpkinfo"}
            print("      UWAGA: brak czytelnego Resources.mpkinfo — sonda EZST pominięta")
        else:
            try:
                backend = _zstd_backend()
                if backend is None:
                    print(
                        "      UWAGA: brak modułu zstd (Python 3.14+ albo pakiet 'zstandard')\n"
                        "             — sonda EZST obejmie tylko bloki gołe (bez dekompresji)."
                    )
                print(
                    "      Sonda EZST (Resources*.mpk): to potrwa — czytam głowy wszystkich "
                    f"małych wpisów (≤ {args.ezst_max_blok_mb} MB) ..."
                )
                w5 = skanuj_ezst_w_indeksie(
                    root,
                    wyjscie,
                    ezst_cel[0],
                    ezst_cel[1],
                    max_blok_sondy=args.ezst_max_blok_mb << 20,
                    limit_zapisu=args.ezst_limit_mb << 20,
                )
                raport["ezst_sonda"] = w5
                print(
                    f"      Sonda EZST: sondowanych {w5['sondowanych']}, trafień {w5['trafien']}, "
                    f"wyciętych {w5['wycietych']} ({w5['zapisano_bajtow']} B), "
                    f"backend zstd: {w5['backend_zstd'] or 'BRAK'}"
                )
            except Exception as e:
                raport["ezst_sonda"] = {"ok": False, "powod": f"wyjątek: {e}"}
                print(f"      UWAGA: sonda EZST przerwana: {e}")
    else:
        print("[4/5] (--bez-wycinania: pomijam wycinanie bloków)")
    raport["wycinanie"] = wycinanie

    print("[5/5] Zapisuję wyniki ...")
    raport_path = wyjscie / "RAPORT.json"
    raport_path.write_text(
        json.dumps(raport, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    podsumowanie = _posumowanie(raport)
    (wyjscie / "PODSUMOWANIE.txt").write_text(podsumowanie, encoding="utf-8")

    zip_path = wyjscie.parent / "WWM_MPK_Skaner_WYNIK.zip"
    _zapisz_zip(wyjscie, zip_path)
    sha = _sha256(zip_path)
    (wyjscie / "SHA256.txt").write_text(f"{sha}  {zip_path.name}\n", encoding="ascii")
    print()
    print(f"GOTOWE: {zip_path}")
    print(f"SHA-256: {sha}")
    print("Ten ZIP wyślij na Dysk Google (folder 'Where Winds Meet'). Paczek .mpk NIE wysyłaj.")
    return 0


def _posumowanie(raport: dict) -> str:
    linie: list[str] = []
    a = linie.append
    a("WWM MPK Skaner — PODSUMOWANIE")
    a(f"wersja skanera: {raport['wersja_skanera']}")
    a(f"katalog gry: {raport['katalog_gry']}")
    a("")
    a(f"Paczki *.mpk znalezione: {len(raport['paczki'])}")
    a(f"Razem bajtów:            {raport['paczki_suma_bajtow']:,}".replace(",", " "))
    duze = sorted(raport["paczki"], key=lambda p: -p["rozmiar"])[:10]
    for p in duze:
        a(f"  {p['rozmiar']:>14,} B  {p['sciezka']}".replace(",", " "))
    a("")
    a("Indeksy .mpkinfo:")
    for m in raport["mpkinfo"]:
        if m.get("ok"):
            a(f"  {m['nazwa']}: {m['wpisow']} wpisów, paczek {len(m['pack_id_hist'])}")
            for kontener in m["kontenery"].values():
                stan = "ok" if kontener["istnieje"] else "BRAK PLIKU"
                pok = f", pokrycie {kontener['pokrycie_pct']}%" if kontener["istnieje"] else ""
                a(f"      pack {kontener['pack_id']:>4}: {stan}{pok}  {kontener['sciezka']}")
        else:
            a(f"  {m['nazwa']}: POMINIĘTY — {m['powod']}")
    a("")
    a("Patch.mpkdb:")
    for m in raport["mpkdb"]:
        if m.get("ok"):
            a(f"  {m['nazwa']}: {m['wpisow']} wpisów; tabele:")
            for tabela, info in sorted(m["tabele"].items()):
                a(f"      {tabela}: {info['wierszy']} wierszy, kolumny {','.join(info['kolumny'])}")
        else:
            a(f"  {m['nazwa']}: POMINIĘTY — {m['powod']}")
    a("")
    a(f"Kandydaci wczytani: {raport['kandydaci_wczytani']}")
    traf = raport["trafienia_kandydatow"]
    a(f"Trafień w indeksach: {len(traf)}")
    for t in traf[:300]:
        a(f"  {t['sciezka']}")
        a(f"      -> {t['indeks']}, pack {t['pack_id']}, offset {t['offset']}, size {t['size']}")
    if len(traf) > 300:
        a(f"  ... oraz {len(traf) - 300} dalszych (pełna lista w RAPORT.json)")
    if not traf:
        a("  (brak — wzorce ścieżek nietrafione albo pliki są w paczkach bez indeksu)")
    a("")
    sonda = raport.get("ezst_sonda")
    if sonda:
        a("Sonda zawartości bloków EZST (v7):")
        if sonda.get("sondowanych") is not None:
            a(f"  backend zstd: {sonda.get('backend_zstd') or 'BRAK (sonda tylko bloków gołych)'}")
            a(f"  sondowanych wpisów: {sonda.get('sondowanych')} "
              f"(pominięto dużych: {sonda.get('pominietych_duzych')})")
            a(f"  magie bloków: {sonda.get('magie')}")
            a(f"  trafień treści: {sonda.get('trafien')}; "
              f"wyciętych bloków: {sonda.get('wycietych')} ({sonda.get('zapisano_bajtow')} B)")
            a(f"  sygnatury: {sonda.get('sygnatury')}")
            if sonda.get("limit_osiagniety"):
                a("  UWAGA: osiągnięto limit zapisu — część trafień tylko w ezst_trafienia.jsonl")
        else:
            a(f"  POMINIĘTA — {sonda.get('powod')}")
        a("")
    if raport.get("wycinanie"):
        a("Wycinanie surowych bloków (bez dekodowania EZST):")
        for w in raport["wycinanie"]:
            a(f"  {w['etykieta']}: wycięto {w['ok']}/{w['pozycji']} ({w['bajtow']} B)")
            for b in w.get("bledy", []):
                a(f"      błąd: {b}")
        zrzut = raport.get("mpkdb_zrzut")
        if zrzut and zrzut.get("ok"):
            a(f"  Patch.mpkdb -> mpkdb_dump.json: {zrzut['tabele']}")
        elif zrzut:
            a(f"  Patch.mpkdb: POMINIĘTY ({zrzut.get('powod')})")
        a("")
    a("Co dalej: ten ZIP wyślij na Dysk Google (folder 'Where Winds Meet').")
    a("Paczek .mpk NIE wysyłaj — wystarczy sam raport.")
    return "\n".join(linie) + "\n"


def _wybierz_folder_gui(tytul: str) -> str:
    """Okno wyboru katalogu (jak w patcherze). Zwraca '' gdy niedostępne/anulowane."""
    try:
        import tkinter as tk  # noqa: PLC0415
        from tkinter import filedialog  # noqa: PLC0415

        root_tk = tk.Tk()
        root_tk.withdraw()
        selected = filedialog.askdirectory(title=tytul) or ""
        root_tk.destroy()
        return selected
    except Exception:
        return ""


def main(argv: list[str] | None = None) -> int:
    _utf8()
    parser = argparse.ArgumentParser(description="Sonduje paczki *.mpk WWM bez rozpakowywania.")
    parser.add_argument("--gra", default="", help="katalog instalacji gry (gdy podany, pomija okno wyboru)")
    parser.add_argument("--wyjscie", default="", help="folder wynikowy (domyślnie MPK_SKANER_WYNIK obok skryptu)")
    parser.add_argument("--kandydaci", default="", help="plik kandydaci.jsonl (domyślnie obok skryptu)")
    parser.add_argument("--probka", type=int, default=12, help="ile wejść próbkować na paczkę (domyślnie 12)")
    parser.add_argument("--non-interactive", action="store_true", help="bez pytań; brak --gra = błąd")
    parser.add_argument("--bez-wycinania", action="store_true", help="pomiń krok wycinania surowych bloków")
    parser.add_argument("--bez-ezst", action="store_true", help="pomiń sondę zawartości bloków EZST (v7)")
    parser.add_argument("--ezst-max-blok-mb", type=int, default=4,
                        help="sonduj tylko wpisy do tylu MB (domyślnie 4; większe to tekstury/dźwięk)")
    parser.add_argument("--ezst-limit-mb", type=int, default=256,
                        help="łączny limit MB na surowe bloki wycięte przez sondę EZST (domyślnie 256)")
    args = parser.parse_args(argv)

    if not args.gra:
        if args.non_interactive:
            print("BŁĄD: w trybie --non-interactive podaj --gra <katalog gry>")
            return 2
        print("Otwieram okno wyboru folderu gry ... (zamknij okno, aby przerwać)")
        args.gra = _wybierz_folder_gui("Wybierz główny folder Where Winds Meet")
        if not args.gra:
            print("Anulowano wybór folderu gry. Użycie ręczne: python mpk_skaner.py --gra <folder gry>")
            return 2
    return buduj_raport(args)


if __name__ == "__main__":
    raise SystemExit(main())
