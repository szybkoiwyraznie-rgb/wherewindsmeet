"""A tiny, invented v1-style locale-map model for reproducible tests.

The structure is based on public community documentation, not game files. The
values and hashes are invented. This is a fixture generator, not a game parser
or encoder, and it does not establish compatibility with any real game build.
"""

from __future__ import annotations

import struct


RECORDS = (
    (1, 0x0102030405060708, b"Hello, {hero}!"),
    (5, 0x1122334455667788, b"Another line."),
)


def raw_zstd_frame(data: bytes) -> bytes:
    """Create a single-segment Zstandard frame with one uncompressed block."""
    size = len(data)
    if size <= 255:
        descriptor = b"\x20"  # single segment, one-byte content size
        content_size = bytes((size,))
    elif size <= 65791:
        descriptor = b"\x60"  # single segment, two-byte content size minus 256
        content_size = struct.pack("<H", size - 256)
    else:
        raise ValueError("synthetic fixture block too large")
    # Last block = 1, raw block type = 0, block size in the upper bits.
    block_header = ((size << 3) | 1).to_bytes(3, "little")
    return b"\x28\xb5\x2f\xfd" + descriptor + content_size + block_header + data


def build_sample() -> bytes:
    """Build two synthetic records in one shard and return the container bytes."""
    capacity = 15
    controls = bytearray(b"\x80" * capacity)
    controls[1] = 0x11
    controls[5] = 0x22
    table_start = (24 + capacity + 1 + 15 + 7) // 8 * 8
    shard = bytearray(table_start + capacity * 16)
    struct.pack_into("<QQQ", shard, 0, capacity, len(RECORDS), 0x1234)
    shard[24 : 24 + capacity] = controls
    shard[24 + capacity] = 0xFF
    shard[25 + capacity : 25 + capacity + 15] = controls
    for slot, key, value in RECORDS:
        slot_offset = table_start + slot * 16
        offset_field = slot_offset + 8
        struct.pack_into("<QII", shard, slot_offset, key, len(shard) - offset_field, len(value))
        shard.extend(value)

    index = struct.pack("<QQI", len(RECORDS), 1, 1)
    encoded = []
    for raw in (index, bytes(shard)):
        frame = raw_zstd_frame(raw)
        encoded.append(struct.pack("<BII", 4, len(frame), len(raw)) + frame)
    header = struct.pack("<IIII", 0xDEADBEEF, 1, len(encoded), 0)
    end_offsets = struct.pack("<II", len(encoded[0]), sum(map(len, encoded)))
    return header + end_offsets + b"".join(encoded)
