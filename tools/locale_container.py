#!/usr/bin/env python3
"""Read the outer structure of a WWM locale container without decoding text.

Layout verified on this project's own data and cross-checked against the
community tools listed in docs/PRIOR_ART.md:

    u32 magic   = 0xDEADBEEF
    u32 version = 1
    u32 count   = number of chunks
    u32[count+1] offsets, relative to the end of the offset table
    count chunks

The last offset is a sentinel equal to the size of the chunk area, so the table
accounts for the whole file. The first chunk is not a text table: it holds the
map index (`u64 total entries | u64 chunk count | u32[chunk count - 1]`), which
is why callers must treat it separately.

This module only validates and slices that outer structure; it never writes and
never prints game text. Decompressing a chunk needs the optional `zstandard`
package.
"""

from __future__ import annotations

import argparse
import json
import struct

MAGIC = 0xDEADBEEF
SUPPORTED_VERSION = 1
HEADER = struct.Struct("<III")
HEADER_SIZE = HEADER.size


class ContainerError(Exception):
    """The file does not follow the documented outer structure."""


def parse_header(data: bytes) -> dict:
    if len(data) < HEADER_SIZE:
        raise ContainerError("file is shorter than the container header")
    magic, version, count = HEADER.unpack_from(data, 0)
    if magic != MAGIC:
        raise ContainerError("unexpected magic; not a known locale container")
    if version != SUPPORTED_VERSION:
        raise ContainerError(f"unsupported container version {version}")
    if count < 1:
        raise ContainerError("container declares no chunks")
    return {"magic": magic, "version": version, "count": count}


def offsets(data: bytes) -> list[int]:
    header = parse_header(data)
    count = header["count"]
    table_end = HEADER_SIZE + 4 * (count + 1)
    if table_end > len(data):
        raise ContainerError("offset table runs past the end of the file")
    values = list(struct.unpack_from(f"<{count + 1}I", data, HEADER_SIZE))
    previous = -1
    for value in values:
        if value < previous:
            raise ContainerError("offset table is not monotonic")
        previous = value
    if table_end + values[-1] != len(data):
        raise ContainerError("last offset does not end at the file size")
    return values


def chunk_spans(data: bytes) -> list[tuple[int, int]]:
    """Return (start, end) byte spans for every chunk, index chunk included."""
    count = parse_header(data)["count"]
    values = offsets(data)
    table_end = HEADER_SIZE + 4 * (count + 1)
    return [
        (table_end + values[index], table_end + values[index + 1]) for index in range(count)
    ]


def metadata_span(data: bytes) -> tuple[int, int]:
    """Span of the index chunk, which is always the first one."""
    return chunk_spans(data)[0]


def describe(data: bytes) -> dict:
    header = parse_header(data)
    spans = chunk_spans(data)
    data_spans = spans[1:]
    sizes = [end - start for start, end in data_spans]
    return {
        "bytes": len(data),
        "version": header["version"],
        "chunks": header["count"],
        "data_chunks": len(data_spans),
        "index_chunk_bytes": spans[0][1] - spans[0][0],
        "chunk_bytes_min": min(sizes) if sizes else 0,
        "chunk_bytes_max": max(sizes) if sizes else 0,
        "chunk_bytes_total": sum(sizes),
    }


def count_zstd_prefixes(data: bytes, spans: list[tuple[int, int]]) -> int:
    """Count chunks whose block header is followed directly by a zstd frame."""
    return sum(1 for start, _end in spans if data[start + 9 : start + 13] == b"\x28\xb5\x2f\xfd")


def decompress_chunk(chunk: bytes) -> bytes:
    """Decompress one chunk; requires the optional `zstandard` package."""
    try:
        import zstandard  # noqa: PLC0415 - optional dependency, imported on use
    except ImportError as error:  # pragma: no cover - depends on environment
        raise ContainerError("the optional zstandard package is not installed") from error
    position = chunk.find(b"\x28\xb5\x2f\xfd")
    if position < 0:
        raise ContainerError("chunk holds no zstd frame")
    try:
        return zstandard.ZstdDecompressor().decompressobj().decompress(chunk[position:])
    except Exception as error:  # noqa: BLE001 - report, never guess
        raise ContainerError(f"chunk frame did not decompress: {error}") from error


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate the outer structure of a WWM locale container. "
        "Prints aggregates only; never prints game text.",
    )
    parser.add_argument("path", help="locale map file to inspect")
    arguments = parser.parse_args(argv)
    data = open(arguments.path, "rb").read()
    try:
        result = describe(data)
    except ContainerError as error:
        print(json.dumps({"parsed": False, "reason": str(error)}))
        return 1
    result["parsed"] = True
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
