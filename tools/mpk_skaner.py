#!/usr/bin/env python3
"""Skaner paczek Where Winds Meet dla Windows — sonduje `.mpk` BEZ rozpakowywania.

Po co: powiązania "scena -> następna scena", "POI -> sceny" i osie `.cine` nie
leżą w tabelach HD (`Package/HD/oversea`), tylko — przypuszczalnie — w paczkach
VFS (`Resources*.mpk`, `LT*.mpk`, `Patch*.mpk`). Ten skrypt **nie odpakowuje**
paczek; odpowiada na pytania:

  1. jakie paczki i indeksy są w instalacji (ile `Resources*.mpk`, gdzie leży
     `Resources.mpkinfo` / `Patch.mpkdb`),
  2. co indeks mówi o wpisach (ile, jakie `pack_id`, offsety, pokrycie pliku),
  3. co leży pod próbkowanymi offsetami (magia EZST/ZSTD/..., entropia),
  4. czy znane kandydacje ścieżek (`client/dialogs/...` z `index/poi.jsonl`,
     wzorce `.cine` z `cine_name`) trafiają we wpisy indeksów — liczy `file_id`
     i szuka go w indeksach.

Czego ten skrypt NIE robi:
  * nie uruchamia gry i nie dotyka jej procesu,
  * nie modyfikuje żadnego pliku gry (otwiera tylko do odczytu),
  * nie wysyła niczego do sieci,
  * nie kopiuje paczek ani całych bloków (czyta kilka KB na próbkę),
  * nie odszyfrowuje bloków EZST (tylko rozpoznaje ich obecność).

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

WERSJA = "wwm-mpk-skaner-v1"
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
# Raport
# ---------------------------------------------------------------------------

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

    print("[1/4] Szukam paczek *.mpk ...")
    paczki = znajdz_paczki(root)
    suma_mpk = sum(p["rozmiar"] for p in paczki)
    print(f"      znaleziono {len(paczki)} paczek, razem {suma_mpk:,} B".replace(",", " "))

    print("[2/4] Szukam indeksów (.mpkinfo / Patch.mpkdb) ...")
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

    for mpkinfo_path in indeksy["mpkinfo"]:
        meta = parsuj_mpkinfo(root, Path(mpkinfo_path))
        entries = meta.pop("_entries", [])
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

    print("[3/4] Haszuję kandydatów ścieżek ...")
    kandydat_path = Path(args.kandydaci) if args.kandydaci else DOMYSLNI_KANDYDACI
    kandydaci = wczytaj_kandydatow(kandydat_path)
    raport["kandydaci_wczytani"] = len(kandydaci)
    raport["plik_kandydatow"] = str(kandydat_path)
    trafienia = haszuj_kandydatow(kandydaci, mpkinfo_lookup, mpkdb_fids)
    raport["trafienia_kandydatow"] = trafienia
    print(f"      kandydatów {len(kandydaci)}, trafień {len(trafienia)}")

    print("[4/4] Zapisuję wyniki ...")
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
    for t in traf:
        a(f"  {t['sciezka']}")
        a(f"      -> {t['indeks']}, pack {t['pack_id']}, offset {t['offset']}, size {t['size']}")
    if not traf:
        a("  (brak — wzorce ścieżek nietrafione albo pliki są w paczkach bez indeksu)")
    a("")
    a("Co dalej: ten ZIP wyślij na Dysk Google (folder 'Where Winds Meet').")
    a("Paczek .mpk NIE wysyłaj — wystarczy sam raport.")
    return "\n".join(linie) + "\n"


def main(argv: list[str] | None = None) -> int:
    _utf8()
    parser = argparse.ArgumentParser(description="Sonduje paczki *.mpk WWM bez rozpakowywania.")
    parser.add_argument("--gra", default="", help="katalog instalacji gry")
    parser.add_argument("--wyjscie", default="", help="folder wynikowy (domyślnie MPK_SKANER_WYNIK obok skryptu)")
    parser.add_argument("--kandydaci", default="", help="plik kandydaci.jsonl (domyślnie obok skryptu)")
    parser.add_argument("--probka", type=int, default=12, help="ile wejść próbkować na paczkę (domyślnie 12)")
    parser.add_argument("--non-interactive", action="store_true", help="bez pytań; brak --gra = błąd")
    args = parser.parse_args(argv)

    if not args.gra:
        if args.non_interactive:
            print("BŁĄD: w trybie --non-interactive podaj --gra <katalog gry>")
            return 2
        try:
            args.gra = input("Podaj ścieżkę do folderu gry Where Winds Meet: ").strip().strip('"')
        except EOFError:
            return 2
    return buduj_raport(args)


if __name__ == "__main__":
    raise SystemExit(main())
