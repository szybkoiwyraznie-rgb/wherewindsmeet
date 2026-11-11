#!/usr/bin/env python3
"""Read the outer structure of a WWM locale container without decoding text.

The container was identified on one private collected file (2026-11-11):
`0xDEADBEEF`, version 1, chunk count, a `uint32` offset table relative to the
end of that table, and zstd frames inside chunks. This module only validates
and slices that outer structure; it never writes and never prints game text.

Decompressing a chunk needs the optional third-party `zstandard` package, which
is not required for the repository checks.
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path

MAGIC = 0xDEADBEEF
SUPPORTED_VERSION = 1
HEADER = struct.Struct("<IIQ")
MIN_HEADER_SIZE = HEADER.size


class ContainerError(Exception):
    """The file does not follow the documented outer structure."""


def parse_header(data: bytes) -> dict:
    if len(data) < MIN_HEADER_SIZE:
        raise ContainerError("file is shorter than the container header")
    magic, version, count = HEADER.unpack_from(data, 0)
    if magic != MAGIC:
        raise ContainerError("unexpected magic; not a known locale container")
    if version != SUPPORTED_VERSION:
        raise ContainerError(f"unsupported container version {version}")
    if count < 2:
        raise ContainerError("chunk table must hold at least a chunk and its sentinel")
    return {"magic": magic, "version": version, "count": count}


def chunk_spans(data: bytes) -> list[tuple[int, int]]:
    """Return (start, end) byte spans for every real chunk.

    The last table entry is a sentinel whose offset equals the end of the file,
    so it describes no bytes. Spans exclude the sentinel.
    """
    header = parse_header(data)
    count = header["count"]
    table_end = MIN_HEADER_SIZE + 4 * count
    if table_end > len(data):
        raise ContainerError("offset table runs past the end of the file")
    offsets = struct.unpack_from(f"<{count}I", data, MIN_HEADER_SIZE)
    previous = -1
    for value in offsets:
        if value < previous:
            raise ContainerError("offset table is not monotonic")
        previous = value
    if table_end + offsets[-1] != len(data):
        raise ContainerError("last offset does not end at the file size")
    if offsets[-1] == offsets[-2]:
        raise ContainerError("last chunk is empty; sentinel is missing")
    spans = []
    for index in range(count - 1):
        start = table_end + offsets[index]
        end = table_end + offsets[index + 1]
        spans.append((start, end))
    return spans


def describe(data: bytes) -> dict:
    header = parse_header(data)
    spans = chunk_spans(data)
    sizes = [end - start for start, end in spans]
    return {
        "bytes": len(data),
        "version": header["version"],
        "table_entries": header["count"],
        "chunks": len(spans),
        "chunk_bytes_min": min(sizes),
        "chunk_bytes_max": max(sizes),
        "chunk_bytes_total": sum(sizes),
    }


def count_zstd_prefixes(data: bytes, spans: list[tuple[int, int]]) -> int:
    """Count chunks whose first zstd frame magic sits at byte 9.

    This is a structural observation from the sample, not a spec guarantee.
    """
    found = 0
    for start, end in spans:
        if data[start + 9 : start + 13] == b"\x28\xb5\x2f\xfd":
            found += 1
    return found


def decompress_chunk(chunk: bytes) -> bytes:
    """Decompress one chunk; requires the optional `zstandard` package."""
    try:
        import zstandard  # noqa: PLC0415 - optional dependency, imported on use
    except ImportError as error:  # pragma: no cover - depends, on environment
        raise ContainerError("the optional zstandard package is not installed") from error
    position = chunk.find(b"\x28\xb5\x2f\xfd")
    if position < 0:
        raise ContainerError("chunk holds no zstd frame")
    stream = chunk[position:]
    output = bytearray()
    frame = zstandard.ZstdDecompressor()
    offset = 0
    while offset < len(stream):
        try:
            output += frame.decompressobj().decompress(stream[offset:])
        except Exception as error:  # noqa: BLE001 - report, never guess
            raise ContainerError(f"chunk frame did not decompress: {error}") from error
        break
    return bytes(output)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate the outer structure of a WWM locale container. "
        "Prints aggregates only; never prints game text.",
    )
    parser.add_argument("path", type=Path, help="private copy of a locale map")
    arguments = parser.parse_args(argv)
    try:
        data = arguments.path.read_bytes()
        result = describe(data)
        result["chunks_with_zstd_at_9"] = count_zstd_prefixes(data, chunk_spans(data))
    except (OSError, ContainerError) as error:
        print(json.dumps({"readable": False, "reason": str(error)}))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
