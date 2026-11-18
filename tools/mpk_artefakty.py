#!/usr/bin/env python3
"""Generuje pochodne indeksy z wyniku skanera MPK (`WWM_MPK_Skaner_WYNIK*.zip`).

Po co: surowe bloki gry (.cine, Lua 5.4 bytecode z LT1) NIE trafiają do Git.
Ten skrypt wyciąga z nich WYŁĄCZNIE metadane i identyfikatory:

  * `index/mpk/cine_dekodowane.jsonl`  — ścieżka VFS, pack/offset/rozmiar,
    sha256 bloku surowego i dekodowanego, nagłówek `.cine` (magic + u64
    długość), tabela identyfikatorów właściwości (nazwy pól — bez treści
    fabularnej),
  * `index/mpk/lt1_dekodowane.jsonl`   — metadane bloków `LT1.mpk` +
    wykryta ścieżka źródłowa (debug info) i ścieżka VFS
    (`LuaText/<debug>` — reguła potwierdzona: 240/240 file_id się zgadza),
  * `index/mpk/lt1_stringi.jsonl`      — licznik wystąpień identyfikatorów
    [A-Za-z0-9_/.@-]{4,} w zdekompresowanym Lua (bez tekstu fabularnego),
  * `index/mpk/patch_mpkdb_info0.jsonl`— wiersze `info0` (file_id hex lub
    ścieżka + rozmiar/pack_id/offset) oraz `patch_mpkdb_pak.jsonl` (2 wiersze)
    i `patch_mpkdb_meta.json` (same rozmiary + sha256, bajtów nie zapisujemy).

Wymaga bibliotek tylko do dekodowania (poza repo, np. `python3 -m venv`):
  zstandard, pycryptodome, lz4

Uruchomienie:
  python3 tools/mpk_artefakty.py --wynik-zip "google_drive/WWM_MPK_Skaner_WYNIK (1).zip"
  python3 tools/mpk_artefakty.py --wynik-katalog local/mpk_wynik_v3

Port dekodowania: Zhincore/wwm-messiah-tools (MIT) — EZST (AES-256-ECB na
prefiksie + zstd), ZSTD, LuaText (u32le + LZ4 do Lua 5.4 chunków).
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import re
import struct
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

EZST_KEY = struct.pack(
    "<4Q", 0x556A586E32723575, 0x38782F913F152867, 0x2D3B615062536756, 0x6B59703373367639
)
LUA_ID = re.compile(rb"[A-Za-z0-9_/.@-]{4,}")
DEBUG_SRC = re.compile(rb"@[A-Za-z0-9_/.@-]{3,200}")


def _importe():
    try:
        import lz4.block  # type: ignore
        import zstandard  # type: ignore
        from Crypto.Cipher import AES  # type: ignore
    except ImportError as e:
        raise SystemExit(
            f"Brak biblioteki ({e.name}). Zainstaluj w oddzielnym venv: "
            "pip install zstandard pycryptodome lz4"
        )
    return lz4.block, zstandard, AES


def ezst_decode(blob: bytes, AES, zstandard) -> bytes:
    magic = blob[:4]
    raw_size = struct.unpack_from("<I", blob, 4)[0]
    payload = blob[8:]
    if magic == b"ZSTD":
        out = zstandard.ZstdDecompressor().decompressobj().decompress(payload)
        return _check(out, raw_size)
    if magic != b"EZST":
        raise ValueError("nieznana sygnatura bloku")
    aes = AES.new(EZST_KEY, AES.MODE_ECB)
    n = min(len(payload) // 16 * 16, 256)
    last: Exception | None = None
    while n >= 0:
        try:
            out = zstandard.ZstdDecompressor().decompressobj().decompress(
                (aes.decrypt(payload[:n]) if n else b"") + payload[n:]
            )
            return _check(out, raw_size)
        except Exception as e:  # noqa: BLE001
            last, n = e, n - 16
    raise ValueError(f"EZST decode failed: {last}")


def _check(out: bytes, raw_size: int) -> bytes:
    if len(out) != raw_size:
        raise ValueError(f"size mismatch {len(out)} != {raw_size}")
    return out


def luatext_decode(blob: bytes, lz4_block):
    if len(blob) < 5:
        return None
    size = struct.unpack_from("<I", blob, 0)[0]
    try:
        out = lz4_block.decompress(blob[4:], uncompressed_size=size)
    except Exception:
        return None
    if len(out) != size:
        return None
    return out


def parse_cine(blob: bytes) -> dict:
    """Nagłówek .cine: magic + u64le długość + u8 liczba identyfikatorów + tabela."""
    if blob[:4] != b"\xc1YA\r":
        return {"magic": blob[:4].hex()}
    total = struct.unpack_from("<Q", blob, 4)[0]
    n = blob[12]
    pos = 13
    strings = []
    for _ in range(n):
        end = blob.index(b"\0", pos)
        strings.append(blob[pos:end].decode("utf-8", "replace"))
        pos = end + 1
    return {
        "magic": "c159410d",
        "dekodowana_dlugosc": total,
        "dlugosc_ok": total == len(blob),
        "liczba_stringow": len(strings),
        "stringi": strings,
        "offset_body": pos,
        "rozmiar_body": len(blob) - pos,
    }


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _as_u64(v: int) -> int:
    return v + (1 << 64) if v < 0 else v


def przetworz(wynik_kat: Path, wyjscie: Path, dekoduj_do: Path) -> dict:
    import mpk_skaner as ms  # file_id

    lz4, zstandard, AES = _importe()
    wyjscie.mkdir(parents=True, exist_ok=True)
    wyciete = wynik_kat / "wyciete"
    if not wyciete.is_dir():
        raise SystemExit(f"brak folderu wyciete/ w {wynik_kat}")

    rap_sciezka = wynik_kat / "RAPORT.json"
    rap = json.loads(rap_sciezka.read_text(encoding="utf-8")) if rap_sciezka.is_file() else {}
    sciezka_by_fid = {
        int(t["file_id"], 16): (t.get("sciezka"), t.get("pack_id"), t.get("offset"), t.get("size"))
        for t in rap.get("trafienia_kandydatow", [])
    }

    cine_out = dekoduj_do / "cine"
    lt1_out = dekoduj_do / "lt1"
    cine_out.mkdir(parents=True, exist_ok=True)
    lt1_out.mkdir(parents=True, exist_ok=True)

    wiersze_cine: list[dict] = []
    wiersze_lt1: list[dict] = []
    liczniki = Counter()
    plikow_z_stringiem = Counter()

    for p in sorted(wyciete.glob("trafienie_*.bin")):
        b = p.read_bytes()
        fid_hex = p.stem.split("_", 1)[1]
        fid = int(fid_hex, 16)
        dec = ezst_decode(b, AES, zstandard)
        sciezka_vfs, pack_id, offset, size = sciezka_by_fid.get(fid, (None, None, None, None))
        cine = parse_cine(dec)
        (cine_out / (sciezka_vfs.rsplit("/", 1)[-1] if sciezka_vfs else f"cine_{fid_hex}.cine")).write_bytes(dec)
        wiersze_cine.append(
            {
                "plik_wynikowy": p.name,
                "vfs_sciezka": sciezka_vfs,
                "pack_id": pack_id,
                "offset": offset,
                "size_w_indeksie": size,
                "file_id_hex": f"{fid:016x}",
                "sha256_surowy": sha256_hex(b),
                "sha256_dekodowany": sha256_hex(dec),
                "surowy_rozmiar": len(b),
                "dekodowany_rozmiar": len(dec),
                **cine,
            }
        )

    for p in sorted(wyciete.glob("lt1_*.bin")):
        b = p.read_bytes()
        fid_hex = p.stem.split("_", 1)[1]
        fid = int(fid_hex, 16)
        dec = luatext_decode(b, lz4)
        if dec is None:
            wiersze_lt1.append({"plik_wynikowy": p.name, "file_id_hex": f"{fid:016x}", "blad": "luatext_decode failed"})
            continue
        (lt1_out / f"{p.stem}.lua").write_bytes(dec)
        m = DEBUG_SRC.search(dec)
        debug = m.group()[1:].decode("utf-8", "replace") if m else None
        vfs = ("LuaText/" + debug) if debug else None
        match = bool(vfs) and ms.file_id(vfs) == fid
        for mm in LUA_ID.finditer(dec):
            s = mm.group().decode("ascii")
            liczniki[s] += 1
            plikow_z_stringiem[s] += 1
        wiersze_lt1.append(
            {
                "plik_wynikowy": p.name,
                "file_id_hex": f"{fid:016x}",
                "sha256_surowy": sha256_hex(b),
                "surowy_rozmiar": len(b),
                "sha256_dekodowany": sha256_hex(dec),
                "dekodowany_rozmiar": len(dec),
                "debug_source": debug,
                "vfs_sciezka": vfs,
                "vfs_file_id_match": match,
            }
        )

    # lt1_stringi — identyfikatory posortowane malejąco wg liczby wystąpień
    lt1_stringi = sorted(liczniki.items(), key=lambda kv: (-kv[1], kv[0]))

    def pisz_jsonl(nazwa: str, wiersze) -> Path:
        cel = wyjscie / nazwa
        with open(cel, "w", encoding="utf-8", newline="\n") as fh:
            for w in wiersze:
                fh.write(json.dumps(w, ensure_ascii=False, separators=(",", ":")) + "\n")
        return cel

    pisz_jsonl("cine_dekodowane.jsonl", wiersze_cine)
    pisz_jsonl("lt1_dekodowane.jsonl", wiersze_lt1)
    pisz_jsonl(
        "lt1_stringi.jsonl",
        ({"s": s, "wystapien": c} for s, c in lt1_stringi),
    )

    # Patch.mpkdb -> tabele pochodne
    mpkdb_sciezka = wynik_kat / "mpkdb_dump.json"
    stat = {"info0": 0, "pak": 0, "meta": None}
    if mpkdb_sciezka.is_file():
        dump = json.loads(mpkdb_sciezka.read_text(encoding="utf-8"))
        info0 = []
        for r in dump.get("tabele", {}).get("info0", {}).get("wiersze", []):
            v0, v1, v2, v3, v4, v5, v6 = r
            if isinstance(v0, str):
                info0.append({"sciezka": v0, "v1": v1, "v2": v2, "v3": v3, "v4": v4, "v5": v5, "v6": v6})
            else:
                info0.append(
                    {
                        "file_id_hex": f"{_as_u64(v0):016x}",
                        "v1": v1, "v2": v2, "v3": v3, "v4": v4, "v5": v5, "v6": v6,
                    }
                )
        pisz_jsonl("patch_mpkdb_info0.jsonl", info0)
        stat["info0"] = len(info0)
        pak = dump.get("tabele", {}).get("pak", {}).get("wiersze", [])
        pisz_jsonl(
            "patch_mpkdb_pak.jsonl",
            ({"v0_hex": f"{_as_u64(r[0]):016x}", "v1": r[1], "v2": r[2], "v3_hex": f"{_as_u64(r[3]):016x}"} for r in pak),
        )
        stat["pak"] = len(pak)
        meta_w = dump.get("tabele", {}).get("meta", {}).get("wiersze", [])
        meta = []
        for r in meta_w:
            wpis = {}
            for i, cz in enumerate(r):
                if isinstance(cz, dict) and cz.get("__bytes__"):
                    raw = bytes.fromhex(cz.get("hex", ""))
                    wpis[f"kolumna_{i}_rozmiar"] = cz.get("rozmiar")
                    wpis[f"kolumna_{i}_sha256"] = sha256_hex(raw)
                else:
                    wpis[f"kolumna_{i}"] = cz
            meta.append(wpis)
        (wyjscie / "patch_mpkdb_meta.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        stat["meta"] = len(meta)

    return {
        "cine": len(wiersze_cine),
        "lt1": len(wiersze_lt1),
        "lt1_vfs_match": sum(1 for w in wiersze_lt1 if w.get("vfs_file_id_match")),
        "lt1_unikalne_stringi": len(lt1_stringi),
        "mpkdb": stat,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pochodne indeksy z wyniku MPK Skanera (metadane tylko).")
    parser.add_argument("--wynik-zip", default="", help="ścieżka do WWM_MPK_Skaner_WYNIK.zip")
    parser.add_argument("--wynik-katalog", default="", help="rozpakowany katalog wyniku (z wyciete/)")
    parser.add_argument("--wyjscie", default=str(ROOT / "index" / "mpk"), help="katalog wynikowy dla indeksów")
    parser.add_argument("--lokalnie", default=str(ROOT / "local" / "mpk_dekodowane"), help="katalog na zdekodowane bloki (poza Git)")
    args = parser.parse_args(argv)

    wyjscie = Path(args.wyjscie)
    dekoduj_do = Path(args.lokalnie)
    if args.wynik_zip:
        with tempfile.TemporaryDirectory() as td:
            with zipfile.ZipFile(args.wynik_zip) as zf:
                zf.extractall(td)
            stat = przetworz(Path(td), wyjscie, dekoduj_do)
    elif args.wynik_katalog:
        stat = przetworz(Path(args.wynik_katalog), wyjscie, dekoduj_do)
    else:
        parser.error("podaj --wynik-zip albo --wynik-katalog")
    print(json.dumps(stat, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
