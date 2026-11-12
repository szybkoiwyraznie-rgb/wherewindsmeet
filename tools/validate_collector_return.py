#!/usr/bin/env python3
"""Validate a WWM collector return ZIP without extracting or publishing it.

This reports only aggregate counts. Run it on an archive kept in ignored
local/; hashes prove consistency with the accompanying report, not origin or
completeness. The archive, filenames and game data remain private.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import stat
import sys
import zipfile


MAX_ARCHIVE_BYTES = 180 * 1024 * 1024
MAX_EXPANDED_BYTES = 180 * 1024 * 1024
MAX_INVENTORY_BYTES = 80 * 1024 * 1024
MAX_REPORT_BYTES = 16 * 1024 * 1024
MAX_SUMMARY_BYTES = 1024 * 1024
MAX_INVENTORY_ROWS = 250_000
MAX_MEMBERS = 20_000
MAX_LINE_BYTES = 16 * 1024
SHA256 = re.compile(r"^[0-9a-f]{64}$")
STORED = re.compile(r"^pliki/[0-9]{6}_(?:translate_words_map_(?:en|zh_cn)(?:__small)?(?:_mobile)?(?:_diff)?|MANIFEST|data3|data205)$", re.I)
STORED_V2 = re.compile(r"^pliki/[0-9]{6}_[A-Za-z0-9][A-Za-z0-9._-]*$")
BLOCKED_PAYLOAD_SUFFIXES = (
    ".exe", ".dll", ".so", ".dylib", ".sys", ".pdb", ".bin", ".pak", ".ucas",
    ".utoc", ".pck", ".sav", ".save", ".log", ".dmp", ".bak", ".pem", ".key",
    ".p12", ".pfx", ".bat", ".cmd", ".ps1", ".vbs", ".js", ".msi",
)
KINDS_V1 = frozenset({"map_en", "map_zh_cn", "manifest", "context_candidate"})
KINDS_V2 = KINDS_V1 | frozenset({"map_diff", "db_data", "db_index", "patch_other"})


class InvalidReturn(ValueError):
    """A malformed or inconsistent collector return (no private paths in message)."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise InvalidReturn(message)


def unique_dict(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON field")
        result[key] = value
    return result


def decode_json(data: bytes) -> object:
    try:
        return json.loads(data.decode("utf-8-sig"), object_pairs_hook=unique_dict)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise InvalidReturn("invalid JSON or UTF-8") from exc


def safe_relative(value: object) -> bool:
    if not isinstance(value, str) or not value or "\\" in value or ":" in value or "\x00" in value:
        return False
    return all(part not in ("", ".", "..") for part in value.split("/"))


def nonnegative_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def in_scanned_tree(value: object) -> bool:
    return bool(safe_relative(value) and str(value).lower().startswith(("package/", "localdata/patch/")))


def validate(path: Path) -> dict[str, object]:
    require(path.is_file(), "archive is not a file")
    require(path.stat().st_size <= MAX_ARCHIVE_BYTES, "archive exceeds intake limit")
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        require(0 < len(infos) <= MAX_MEMBERS, "invalid member count")
        names: dict[str, zipfile.ZipInfo] = {}
        folded: set[str] = set()
        expanded = 0
        for info in infos:
            name = info.filename
            is_dir = info.is_dir()
            cleaned = name[:-1] if is_dir else name
            if "\\" in cleaned:
                # Windows PowerShell 5.1 CreateFromDirectory wrote "\" names;
                # the ZIP spec requires "/", so this archive is not accepted.
                # Note: zipfile rewrites "\" to "/" while reading member names
                # on Windows, so this branch cannot fire there. The report
                # fields below (source, stored_as) are read from JSON, keep the
                # separator on every platform and reject such an archive anyway.
                require(False, "archive member path uses backslashes")
            require(safe_relative(cleaned), "unsafe archive member path")
            require(name.casefold() not in folded, "duplicate archive member")
            folded.add(name.casefold())
            require(not (info.flag_bits & 1), "encrypted ZIP member")
            mode = (info.external_attr >> 16) & 0o170000
            require(not (info.create_system == 3 and mode == stat.S_IFLNK), "symlink ZIP member")
            require(info.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED), "unsupported ZIP compression")
            if is_dir:
                require(name == "pliki/" and info.file_size == 0, "unexpected directory member")
            else:
                is_payload = bool(STORED_V2.fullmatch(name)) and not name.lower().endswith(BLOCKED_PAYLOAD_SUFFIXES)
                require(name in ("RAPORT.json", "RAPORT.txt", "INWENTARZ.jsonl") or is_payload,
                        "unexpected archive member")
                names[name] = info
            expanded += info.file_size
            require(expanded <= MAX_EXPANDED_BYTES, "expanded archive exceeds intake limit")
        for name in ("RAPORT.json", "RAPORT.txt", "INWENTARZ.jsonl"):
            require(name in names, "required archive member missing")
        require(names["RAPORT.json"].file_size <= MAX_REPORT_BYTES, "report exceeds intake limit")
        require(names["RAPORT.txt"].file_size <= MAX_SUMMARY_BYTES, "summary exceeds intake limit")
        require(names["INWENTARZ.jsonl"].file_size <= MAX_INVENTORY_BYTES, "inventory exceeds intake limit")
        # Full reads check the ZIP CRC, including on the otherwise informational summary.
        report = decode_json(archive.read("RAPORT.json"))
        archive.read("RAPORT.txt").decode("utf-8-sig")
        fmt = report.get("format") if isinstance(report, dict) else None
        require(fmt in ("wwm-collection-v1", "wwm-collection-v2"), "unsupported report format")
        mode = report.get("mode", "rozpoznanie") if fmt == "wwm-collection-v2" else "rozpoznanie"
        require(mode in ("rozpoznanie", "aktualizacja"), "invalid collection mode")
        if fmt == "wwm-collection-v1":
            for member in names:
                if member.startswith("pliki/"):
                    require(bool(STORED.fullmatch(member)), "unexpected archive member")
        allowed_kinds = KINDS_V1 if fmt == "wwm-collection-v1" else KINDS_V2
        stored_pattern = STORED if fmt == "wwm-collection-v1" else STORED_V2
        require(report.get("status") in ("collected", "partial"), "invalid collection status")
        records = report.get("files")
        inventory_info = report.get("inventory")
        problems = report.get("problems")
        require(isinstance(records, list) and len(records) <= MAX_MEMBERS, "invalid file records")
        require(isinstance(problems, list), "invalid problems list")
        require(isinstance(inventory_info, dict) and inventory_info.get("path") == "INWENTARZ.jsonl", "invalid inventory metadata")
        require(nonnegative_int(inventory_info.get("files")) and inventory_info["files"] <= MAX_INVENTORY_ROWS,
                "invalid inventory count")

        referenced: dict[str, tuple[int, str]] = {}
        original_paths: set[str] = set()
        failed = 0
        copied = 0
        english_maps = 0
        for record in records:
            require(isinstance(record, dict), "invalid file record")
            source = record.get("source")
            require(in_scanned_tree(source), "unsafe original path")
            source_key = str(source).casefold()
            require(source_key not in original_paths, "duplicate original path")
            original_paths.add(source_key)
            kind = record.get("kind")
            status = record.get("status")
            length = record.get("bytes")
            require(kind in allowed_kinds, "invalid file kind")
            require(status in ("copied", "duplicate", "skipped_limit", "error"), "invalid file status")
            require(nonnegative_int(length), "invalid file size")
            stored = record.get("stored_as")
            digest = record.get("sha256")
            if status in ("copied", "duplicate"):
                require(isinstance(stored, str) and bool(stored_pattern.fullmatch(stored))
                        and not stored.lower().endswith(BLOCKED_PAYLOAD_SUFFIXES) and stored in names,
                        "stored file missing or unsafe")
                require(isinstance(digest, str) and bool(SHA256.fullmatch(digest)), "invalid SHA-256")
                require(names[stored].file_size == length, "stored file size mismatch")
                value = (length, digest)
                require(stored not in referenced or referenced[stored] == value, "conflicting stored file references")
                referenced[stored] = value
                copied += status == "copied"
                english_maps += kind == "map_en"
            else:
                require(stored is None and digest is None, "failed file must not reference stored bytes")
                failed += 1

        actual_payload = {name for name in names if name.startswith("pliki/")}
        require(actual_payload == set(referenced), "unreferenced or missing stored files")
        require(copied == len(referenced), "invalid unique file count")
        require(nonnegative_int(report.get("payload_bytes")), "invalid payload size")
        require(report["payload_bytes"] == sum(length for length, _ in referenced.values()), "payload size mismatch")
        if report["status"] == "collected":
            if fmt == "wwm-collection-v2" and mode == "aktualizacja":
                require(not failed and not problems and copied > 0, "success conflicts with missing or failed files")
            else:
                require(not failed and not problems and english_maps > 0, "success conflicts with missing or failed files")

        for name, (_, expected) in referenced.items():
            digest = hashlib.sha256()
            with archive.open(name) as stream:
                while chunk := stream.read(1024 * 1024):
                    digest.update(chunk)
            require(digest.hexdigest() == expected, "stored file SHA-256 mismatch")

        inventory_rows = 0
        seen_rows: set[str] = set()
        with archive.open("INWENTARZ.jsonl") as stream:
            while True:
                line = stream.readline(MAX_LINE_BYTES + 1)
                if not line:
                    break
                require(len(line) <= MAX_LINE_BYTES, "inventory line exceeds intake limit")
                row = decode_json(line)
                require(isinstance(row, dict) and in_scanned_tree(row.get("path")), "invalid inventory row")
                require(nonnegative_int(row.get("bytes")) and isinstance(row.get("modified_utc"), str), "invalid inventory metadata")
                key = str(row["path"]).casefold()
                require(key not in seen_rows, "duplicate inventory path")
                seen_rows.add(key)
                inventory_rows += 1
                require(inventory_rows <= MAX_INVENTORY_ROWS, "inventory row limit exceeded")
        require(inventory_rows == inventory_info["files"], "inventory count mismatch")
        return {
            "validation": "passed",
            "collection_status": report["status"],
            "inventory_files": inventory_rows,
            "candidate_files": len(records),
            "unique_files": len(referenced),
            "failed_or_skipped": failed,
            "payload_bytes": report["payload_bytes"],
            "limitations": "Consistency only; not authenticity, game-version proof or complete context.",
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("archive", type=Path, help="private return ZIP (keep in local/)")
    args = parser.parse_args(argv)
    try:
        result = validate(args.archive)
    except (InvalidReturn, OSError, UnicodeError, zipfile.BadZipFile, RuntimeError) as exc:
        # OSError/ZIP messages can contain private paths. Only show our own constant reasons.
        reason = str(exc) if isinstance(exc, InvalidReturn) else "archive could not be read or decoded"
        print(json.dumps({"validation": "failed", "reason": reason}), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
