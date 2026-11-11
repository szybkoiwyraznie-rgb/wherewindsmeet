#!/usr/bin/env python3
"""Apply translations to a WWM locale map and write a patched map file.

The input file is never modified: the patched map is a separate file that the
player drops in place of the original (the patcher builds a backup alongside).
Only entries whose id appears in the translation file change; every other entry
keeps its text. When a translation has a different length, the table is rebuilt
so that offsets stay consistent (see docs/LOCALE_CONTAINER.md).

Translation input: JSONL, one object per line, `{"id": "...", "text": "..."}`
(`pl` is accepted instead of `text`). Ids are the ones shown in the translator
package as `id:`.

Usage:
    python3 tools/apply_translation.py --map game.map --tlumaczenia pl.jsonl --wyjscie patched.map

The tool verifies its own output before writing: the patched map is parsed back
and compared entry by entry, so a partially applied patch is never produced
silently.
"""

from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path

try:  # imported as a module (`python3 -m tools.apply_translation`)
    from tools import locale_container as container
    from tools import locale_records as records
except ImportError:  # run as a script (`python3 tools/apply_translation.py`)
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from tools import locale_container as container
    from tools import locale_records as records

MAGIC = 0xDEADBEEF
VERSION = 1
HEADER = struct.Struct("<III")
HEADER_SIZE = HEADER.size
BLOCK = struct.Struct("<BII")
BLOCK_SIZE = BLOCK.size
STORED = 0
ZSTD = 4


class PatchError(Exception):
    """The map cannot be patched safely."""


def read_container(data: bytes) -> list[bytes]:
    """Return the raw chunk bytes of a container, index chunk first."""
    try:
        spans = container.chunk_spans(data)
    except container.ContainerError as error:
        raise PatchError(str(error)) from error
    return [data[start:end] for start, end in spans]


def split_chunk(chunk: bytes) -> tuple[int, bytes]:
    if len(chunk) < BLOCK_SIZE:
        raise PatchError("chunk is shorter than its block header")
    kind, compressed_size, _decompressed_size = BLOCK.unpack_from(chunk, 0)
    payload = chunk[BLOCK_SIZE:]
    if compressed_size != len(payload):
        raise PatchError("chunk size does not match its block header")
    return kind, payload


def decompress(kind: int, payload: bytes) -> bytes:
    if kind == ZSTD:
        return records_zstd().ZstdDecompressor().decompress(payload, max_output_size=1 << 28)
    if kind == STORED:
        return payload
    raise PatchError(f"unsupported compression type {kind}")


def compress(kind: int, payload: bytes, level: int) -> bytes:
    if kind == ZSTD:
        return records_zstd().ZstdCompressor(level=level).compress(payload)
    if kind == STORED:
        return payload
    raise PatchError(f"unsupported compression type {kind}")


def records_zstd():
    try:
        import zstandard  # noqa: PLC0415 - optional dependency, imported on use
    except ImportError as error:  # pragma: no cover - depends on environment
        raise PatchError("the optional zstandard package is not installed") from error
    return zstandard


def metadata_size(chunk_count: int) -> int:
    """Size of the index chunk: u64 total, u64 chunk count, then u32 per chunk."""
    return 16 + 4 * max(chunk_count - 1, 0)


def is_metadata_chunk(chunk: bytes, chunk_count: int) -> bool:
    """The first chunk holds the map index, not a text table.

    Its payload is `u64 total entries | u64 chunk count | u32[chunk_count - 1]`,
    so its size and first two fields identify it without guessing.
    """
    try:
        kind, payload = split_chunk(chunk)
        table = decompress(kind, payload)
    except PatchError:
        return False
    if len(table) != metadata_size(chunk_count):
        return False
    total, count = struct.unpack_from("<QQ", table, 0)
    return 0 < count <= chunk_count


def build_chunk(kind: int, payload: bytes, level: int) -> bytes:
    body = compress(kind, payload, level)
    return BLOCK.pack(kind, len(body), len(payload)) + body


def build_container(chunks: list[bytes]) -> bytes:
    table_end = HEADER_SIZE + 4 * (len(chunks) + 1)
    offsets = []
    running = 0
    for chunk in chunks:
        offsets.append(running)
        running += len(chunk)
    offsets.append(running)
    return (
        HEADER.pack(MAGIC, VERSION, len(chunks))
        + struct.pack(f"<{len(offsets)}I", *offsets)
        + b"".join(chunks)
    )


def apply_translations(data: bytes, translations: dict[int, str], *, level: int = 9) -> tuple[bytes, dict]:
    chunks = read_container(data)
    applied = 0
    entries = 0
    missing = 0
    patched_chunks = []
    for chunk in chunks:
        if is_metadata_chunk(chunk, len(chunks)):
            # copied verbatim: it is the container's own index, not a text table
            patched_chunks.append(chunk)
            continue
        kind, payload = split_chunk(chunk)
        table = decompress(kind, payload)
        try:
            parsed = records.parse_table(table)
        except records.LayoutError as error:
            raise PatchError(f"unreadable table in chunk: {error}") from error
        wanted = {}
        for entry in parsed["entries"]:
            if not entry["id"] or not entry["length"]:
                continue
            entries += 1
            replacement = translations.get(entry["id"])
            if replacement is None:
                continue
            if not replacement:
                continue
            if replacement.encode("utf-8")[:1] == b"\xff":
                raise PatchError(f"translation for id {entry['id']:016x} starts with a reserved byte")
            wanted[entry["id"]] = replacement
        if wanted:
            applied += len(wanted)
            table = records.pack_table(table, wanted)
        patched_chunks.append(build_chunk(kind, table, level))
    patched = build_container(patched_chunks)
    ids_in_file = {entry["id"] for entry in iter_all_entries(patched)}
    missing = len(set(translations) - ids_in_file)
    stats = {
        "chunks": len(chunks),
        "entries": entries,
        "applied": applied,
        "ids_not_in_map": missing,
        "bytes_before": len(data),
        "bytes_after": len(patched),
    }
    return patched, stats


def iter_all_entries(data: bytes):
    chunks = read_container(data)
    for chunk in chunks:
        if is_metadata_chunk(chunk, len(chunks)):
            continue
        kind, payload = split_chunk(chunk)
        table = records.parse_table(decompress(kind, payload))
        for entry in table["entries"]:
            if entry["id"] and entry["length"]:
                yield entry


def verify(original: bytes, patched: bytes, translations: dict[int, str]) -> dict:
    """Compare the two maps entry by entry; raise unless exactly the intended change happened."""
    before = {entry["id"]: entry["text"] for entry in iter_all_entries(original)}
    after = {entry["id"]: entry["text"] for entry in iter_all_entries(patched)}
    if before.keys() != after.keys():
        raise PatchError("patched map has a different set of ids")
    changed = 0
    for ident, text in before.items():
        expected = translations.get(ident)
        if expected is None or not expected:
            expected = text
        else:
            expected = expected.encode("utf-8")
        if after[ident] != expected:
            raise PatchError(f"entry {ident:016x} does not hold the expected text")
        if after[ident] != text:
            changed += 1
    return {"ids": len(before), "changed": changed}


def load_translations(path) -> dict[int, str]:
    translations = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        text = row.get("text", row.get("pl"))
        if text is None:
            raise PatchError("translation row without `text` or `pl`")
        translations[int(row["id"], 16)] = text
    return translations


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Apply translated texts to a locale map and write a patched copy.",
    )
    parser.add_argument("--map", required=True, help="original locale map file")
    parser.add_argument("--tlumaczenia", required=True, help="JSONL with {id, text} rows")
    parser.add_argument("--wyjscie", required=True, help="path of the patched map to write")
    parser.add_argument("--poziom", type=int, default=9, help="zstd level (default 9)")
    parser.add_argument("--bez-weryfikacji", action="store_true", help="skip the read-back check")
    arguments = parser.parse_args(argv)

    source = Path(arguments.map)
    target = Path(arguments.wyjscie)
    if target.resolve() == source.resolve():
        print(json.dumps({"ok": False, "reason": "output must differ from the input file"}))
        return 2

    data = source.read_bytes()
    translations = load_translations(arguments.tlumaczenia)
    try:
        patched, stats = apply_translations(data, translations, level=arguments.poziom)
        if not arguments.bez_weryfikacji:
            stats["verified"] = verify(data, patched, translations)
    except (PatchError, records.LayoutError) as error:
        print(json.dumps({"ok": False, "reason": str(error)}))
        return 1

    target.write_bytes(patched)
    stats["ok"] = True
    stats["output"] = str(target)
    print(json.dumps(stats))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
