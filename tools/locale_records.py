#!/usr/bin/env python3
"""Read a decompressed WWM locale table into (id, text) records.

The layout is the one used by the game's own table format and by the community
tools `dest1yo/wwm_utils` and `lehieugch68/WWM-Locale-Editor`; it is reproduced
here independently and checked against this project's own data.

    TableHeader   24 B : u64 entry_count, u64 value_count, u64 timestamp
    buckets             : max(entry_count + 1 + 16, 24) bytes, opaque
    entries             : entry_count * 16 B: u64 id, u32 offset, u32 length
    values              : strings inside the table

A value is located at `entries_pos + 16 * index + 8 + offset`, so offsets are
measured from the offset field of their own entry and the strings normally
follow the entry array directly. Entries with `id == 0` or `length == 0` are
holes (the entry array is allocated in fixed-capacity tables). A value whose
first byte is 0xFF is a placeholder, not text.

Nothing here writes, and nothing prints game text unless the caller asks.
"""

from __future__ import annotations

import argparse
import json
import struct

HEADER = struct.Struct("<QQQ")
ENTRY = struct.Struct("<QII")
HEADER_SIZE = HEADER.size
ENTRY_SIZE = ENTRY.size
PLACEHOLDER = 0xFF


class LayoutError(Exception):
    """The payload does not follow the verified table layout."""


def bucket_size(entry_count: int) -> int:
    return max(entry_count + 1 + 16, 24)


def parse_table(payload: bytes) -> dict:
    if len(payload) < HEADER_SIZE:
        raise LayoutError("payload is shorter than the table header")
    entry_count, value_count, timestamp = HEADER.unpack_from(payload, 0)
    entries_pos = HEADER_SIZE + bucket_size(entry_count)
    values_end = entries_pos + ENTRY_SIZE * entry_count
    if values_end > len(payload):
        raise LayoutError("entry array does not fit in the payload")

    entries = []
    filled = 0
    for index in range(entry_count):
        ident, offset, length = ENTRY.unpack_from(payload, entries_pos + ENTRY_SIZE * index)
        start = entries_pos + ENTRY_SIZE * index + 8 + offset
        end = start + length
        text = b""
        placeholder = False
        if ident and length:
            if start < entries_pos or end > len(payload):
                raise LayoutError(f"value {index} points outside the payload")
            text = payload[start:end]
            placeholder = text[:1] == bytes((PLACEHOLDER,))
            if not placeholder:
                filled += 1
        entries.append(
            {
                "id": ident,
                "offset": offset,
                "length": length,
                "placeholder": placeholder,
                "text": text,
            }
        )
    return {
        "entry_count": entry_count,
        "value_count": value_count,
        "timestamp": timestamp,
        "filled": filled,
        "entries": entries,
    }


def iter_texts(payload: bytes, *, encoding: str = "utf-8") -> list[dict]:
    table = parse_table(payload)
    texts = []
    for entry in table["entries"]:
        if not entry["id"] or not entry["length"] or entry["placeholder"]:
            continue
        try:
            text = entry["text"].decode(encoding)
        except UnicodeDecodeError as error:
            raise LayoutError(f"value for id {entry['id']:016x} is not {encoding}") from error
        texts.append({"id": f"{entry['id']:016x}", "text": text})
    return texts


def describe(payload: bytes) -> dict:
    table = parse_table(payload)
    lengths = [
        entry["length"]
        for entry in table["entries"]
        if entry["id"] and entry["length"] and not entry["placeholder"]
    ]
    return {
        "entry_count": table["entry_count"],
        "value_count": table["value_count"],
        "timestamp": table["timestamp"],
        "texts": len(lengths),
        "holes": table["entry_count"] - len(lengths),
        "bytes_total": sum(lengths),
        "bytes_min": min(lengths) if lengths else 0,
        "bytes_max": max(lengths) if lengths else 0,
        "placeholder_entries": sum(1 for entry in table["entries"] if entry["placeholder"]),
        "accounts_for_payload": HEADER_SIZE
        + bucket_size(table["entry_count"])
        + ENTRY_SIZE * table["entry_count"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Report the structure of one decompressed table. Prints aggregates, never game text.",
    )
    parser.add_argument("path", help="file holding one decompressed table")
    arguments = parser.parse_args(argv)
    payload = open(arguments.path, "rb").read()
    try:
        result = describe(payload)
    except LayoutError as error:
        print(json.dumps({"parsed": False, "reason": str(error)}))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

def pack_table(original: bytes, texts: dict[int, str]) -> bytes:
    """Rebuild a table with replaced texts, keeping the original layout.

    `texts` maps an entry id to its new text; other entries keep their text.
    The header and the opaque bucket region are copied from `original`, the
    entry array is rewritten in place and the values are laid out again right
    after it. Feeding back the original texts reproduces `original` byte for
    byte.
    """
    table = parse_table(original)
    entry_count = table["entry_count"]
    entries_pos = HEADER_SIZE + bucket_size(entry_count)
    header = original[:HEADER_SIZE]
    buckets = original[HEADER_SIZE:entries_pos]

    values = b""
    rows = []
    for index, entry in enumerate(table["entries"]):
        ident = entry["id"]
        if not ident or not entry["length"]:
            rows.append(ENTRY.pack(0, 0xFFFFFFFF, 0))
            continue
        payload = entry["text"]
        replacement = texts.get(ident)
        if replacement is not None:
            payload = replacement.encode("utf-8")
        offset = (entry_count - index) * ENTRY_SIZE - 8 + len(values)
        rows.append(ENTRY.pack(ident, offset, len(payload)))
        values += payload
    return header + buckets + b"".join(rows) + values

