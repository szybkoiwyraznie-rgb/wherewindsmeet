#!/usr/bin/env python3
"""Split a decompressed WWM locale chunk into (hash, type, text) records.

Layout verified on 2026-11-11 for chunks of `translate_words_map_*_diff`:

    header   24 B : u64 group, u64 count, u32 0x595896DC, u32 0
    index          : opaque, hash-derived; size varies per chunk
    records  count * 16 B : u64 hash, u32 type, u32 length
    texts          : all texts concatenated in record order, no terminator

The size of the opaque index is found by requiring that the declared lengths
add up exactly to the bytes left after the records. Chunks whose length fields
do not add up (shared or padded texts, unknown layouts) are rejected rather
than guessed.

This module never writes and never prints text; the caller decides what to do.
The main `translate_words_map_en` map uses a different, still-undecoded index
and is not handled here.
"""

from __future__ import annotations

import argparse
import json
import struct

HEADER = struct.Struct("<QQII")
RECORD = struct.Struct("<QII")
HEADER_SIZE = HEADER.size
RECORD_SIZE = RECORD.size
CONSTANT = 0x595896DC
# Types observed so far: 8 = plain text; other small values appear too, and are
# reported verbatim instead of being interpreted.
KNOWN_TEXT_TYPE = 8


class LayoutError(Exception):
    """The chunk does not follow the verified record layout."""


def _texts_look_valid(entries: list[dict]) -> bool:
    """Texts declared as plain text must be valid UTF-8; others are left alone."""
    checked = 0
    for entry in entries:
        text = entry["text"]
        if not text:
            continue
        if entry["type"] != KNOWN_TEXT_TYPE:
            continue
        checked += 1
        try:
            text.decode("utf-8")
        except UnicodeDecodeError:
            return False
    return checked > 0 or all(not entry["text"] for entry in entries)


def parse_chunk(payload: bytes) -> dict:
    if len(payload) < HEADER_SIZE:
        raise LayoutError("payload is shorter than the chunk header")
    group, count, constant, reserved = HEADER.unpack_from(payload, 0)
    if constant != CONSTANT:
        raise LayoutError("unexpected chunk constant; layout not recognised")
    if reserved != 0:
        raise LayoutError("unexpected reserved field in chunk header")
    if count == 0:
        raise LayoutError("chunk declares no records")
    available = len(payload) - HEADER_SIZE - RECORD_SIZE * count
    if available < 0:
        raise LayoutError("records do not fit in the payload")
    for index_size in range(0, available + 1, 4):
        records_at = HEADER_SIZE + index_size
        total = 0
        plausible = True
        for position in range(count):
            length = RECORD.unpack_from(payload, records_at + RECORD_SIZE * position)[2]
            total += length
            if total > available - index_size:
                plausible = False
                break
        if not plausible or index_size + RECORD_SIZE * count + total != len(payload) - HEADER_SIZE:
            continue
        entries = []
        cursor = records_at + RECORD_SIZE * count
        for position in range(count):
            digest, kind, length = RECORD.unpack_from(payload, records_at + RECORD_SIZE * position)
            entries.append({"hash": digest, "type": kind, "text": payload[cursor : cursor + length]})
            cursor += length
        if not _texts_look_valid(entries):
            # Several index sizes can satisfy the byte sum by accident when the
            # opaque index contains zeros; text encoding disambiguates them.
            continue
        return {"group": group, "index_size": index_size, "entries": entries}
    raise LayoutError("declared lengths do not account for the payload")


def describe(payload: bytes) -> dict:
    parsed = parse_chunk(payload)
    texts = [entry["text"] for entry in parsed["entries"]]
    lengths = [len(text) for text in texts]
    return {
        "group": parsed["group"],
        "index_size": parsed["index_size"],
        "records": len(texts),
        "bytes": len(payload),
        "text_bytes_total": sum(lengths),
        "text_bytes_min": min(lengths),
        "text_bytes_max": max(lengths),
        "empty_texts": sum(1 for length in lengths if length == 0),
        "non_text_types": sum(1 for entry in parsed["entries"] if entry["type"] != KNOWN_TEXT_TYPE),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Report the structure of a single decompressed chunk file. "
        "Prints aggregates only; never prints game text.",
    )
    parser.add_argument("path", help="file holding one decompressed chunk payload")
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
