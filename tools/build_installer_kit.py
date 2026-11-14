#!/usr/bin/env python3
"""Build a deterministic Windows installer/backup/restore ZIP from instalator/ (+ optional --latka)."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile, ZipInfo

try:
    from tools import wypisz
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from tools import wypisz


ROOT = Path(__file__).resolve().parent.parent
KIT_DIR = ROOT / "instalator"
FIXED_ZIP_TIME = (2025, 1, 1, 0, 0, 0)
MEMBERS = ("CZYTAJ_TO.txt", "ZAINSTALUJ.bat", "PRZYWROC.bat", "SPRAWDZ_STAN.bat", "instaluj_latke.ps1")


def windows_lines(raw: bytes) -> bytes:
    """Normalize text bytes to CRLF and remove UTF-8 BOM before optional re-addition."""
    text = raw.decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
    return text.replace("\n", "\r\n").encode("utf-8")


def kit_files() -> dict[str, bytes]:
    """Return Windows-encoded files from instalator/ after basic checks."""
    out: dict[str, bytes] = {}
    for name in MEMBERS:
        raw = (KIT_DIR / name).read_bytes()
        if name.endswith(".bat"):
            raw.decode("ascii")
            out[name] = windows_lines(raw)
        elif name.endswith(".ps1"):
            out[name] = b"\xef\xbb\xbf" + windows_lines(raw)
        else:
            out[name] = b"\xef\xbb\xbf" + windows_lines(raw)
    return out


def _safe_rel(rel: str) -> str:
    norm = rel.replace("\\", "/").strip()
    if not norm or norm.startswith("/") or ":" in norm or "\x00" in norm:
        raise ValueError(f"unsafe relative path in latka.json: {rel!r}")
    parts = norm.split("/")
    if any(p in ("", ".", "..") for p in parts):
        raise ValueError(f"unsafe relative path in latka.json: {rel!r}")
    return "/".join(parts)


def collect_patch_files(latka_dir: Path) -> dict[str, bytes]:
    """Read and SHA-256-verify latka.json and all patch payload files from `latka_dir`."""
    manifest_path = latka_dir / "latka.json"
    if not manifest_path.is_file():
        raise ValueError(f"missing latka.json in {latka_dir}")
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes.decode("utf-8"))
    if manifest.get("format") != "wwm-latka-v1":
        raise ValueError(f"unsupported latka.json format: {manifest.get('format')!r}")
    files_list = manifest.get("pliki")
    if not isinstance(files_list, list) or not files_list:
        raise ValueError("latka.json has no pliki entries")

    out: dict[str, bytes] = {"latka.json": manifest_bytes}
    for entry in files_list:
        rel_game = _safe_rel(str(entry["sciezka_w_grze"]))
        if not (rel_game.lower().startswith("package/") or rel_game.lower().startswith("localdata/patch/")):
            raise ValueError(f"sciezka_w_grze must be under Package/ or LocalData/Patch/: {rel_game!r}")
        rel_patch = _safe_rel(str(entry.get("plik_latki") or entry["plik"]))
        if rel_patch in out:
            raise ValueError(f"duplicate patch file path: {rel_patch!r}")
        src = latka_dir / rel_patch
        if not src.is_file():
            raise ValueError(f"missing patch payload file: {src}")
        payload = src.read_bytes()
        expected_sha = str(entry["sha256_po"]).lower()
        actual_sha = hashlib.sha256(payload).hexdigest().lower()
        if actual_sha != expected_sha:
            raise ValueError(f"SHA-256 mismatch for {rel_patch}: expected {expected_sha}, got {actual_sha}")
        out[rel_patch] = payload
    return out


def build_zip(output: Path, latka_dir: Path | None = None) -> tuple[str, int, dict[str, bytes]]:
    """Write a deterministic ZIP containing the installer kit (and optional patch files) and verify by re-reading."""
    files = kit_files()
    if latka_dir is not None:
        patch_files = collect_patch_files(latka_dir)
        for name, data in patch_files.items():
            if name in files:
                raise ValueError(f"patch file collides with kit member: {name}")
            files[name] = data

    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "w", compression=ZIP_DEFLATED if latka_dir else ZIP_STORED) as archive:
        for name in sorted(files):
            data = files[name]
            info = ZipInfo(filename=name, date_time=FIXED_ZIP_TIME)
            info.compress_type = ZIP_DEFLATED if latka_dir and not name.endswith(".bat") else ZIP_STORED
            info.create_system = 0
            info.external_attr = 0o644 << 16
            archive.writestr(info, data)
    with ZipFile(output) as check:
        if check.testzip() is not None or set(check.namelist()) != set(files):
            raise RuntimeError("installer archive failed verification")
        for name, expected in files.items():
            if check.read(name) != expected:
                raise RuntimeError(f"installer archive content mismatch for {name}")
    raw = output.read_bytes()
    return hashlib.sha256(raw).hexdigest(), len(raw), files


def main(argv: list[str] | None = None) -> int:
    wypisz.utf8()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, help="Output ZIP path outside the game directory")
    parser.add_argument("--latka", default="", help="Optional built patch directory containing latka.json")
    args = parser.parse_args(argv)
    latka = Path(args.latka) if args.latka else None
    digest, size, files = build_zip(Path(args.output), latka_dir=latka)
    print(f"{args.output} ({size} bytes, {len(files)} files, SHA-256 {digest})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
