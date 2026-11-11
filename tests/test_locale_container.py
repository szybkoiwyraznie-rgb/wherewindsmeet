from __future__ import annotations

import struct
import unittest

from tools import locale_container as container


def synthetic(offsets: list[int], payload: bytes, *, magic: int = container.MAGIC, version: int = 1) -> bytes:
    header = struct.pack("<IIQ", magic, version, len(offsets))
    table = struct.pack(f"<{len(offsets)}I", *offsets)
    return header + table + payload


class LocaleContainerTests(unittest.TestCase):
    def test_reads_header_and_chunk_spans(self):
        data = synthetic([4, 12, 20], b"aaaabbbbbbbbcccccccc")
        header = container.parse_header(data)
        self.assertEqual(header["version"], 1)
        self.assertEqual(header["count"], 3)
        spans = container.chunk_spans(data)
        base = 16 + 4 * 3
        self.assertEqual(spans, [(base + 4, base + 12), (base + 12, base + 20)])
        described = container.describe(data)
        self.assertEqual(described["chunks"], 2)
        self.assertEqual(described["chunk_bytes_min"], 8)
        self.assertEqual(described["chunk_bytes_max"], 8)
        self.assertEqual(described["chunk_bytes_total"], 16)

    def test_rejects_foreign_magic_and_version(self):
        for kwargs in ({"magic": 0x11223344}, {"version": 2}):
            with self.subTest(**kwargs):
                data = synthetic([4, 12], b"aaaabbbbbbbb", **kwargs)
                with self.assertRaises(container.ContainerError):
                    container.parse_header(data)

    def test_rejects_short_file_and_single_entry(self):
        with self.assertRaises(container.ContainerError):
            container.parse_header(b"\xef\xbe\xad\xde\x01\x00")
        with self.assertRaises(container.ContainerError):
            container.parse_header(synthetic([0], b""))

    def test_rejects_table_past_end_and_non_monotonic_offsets(self):
        data = synthetic([4, 12], b"aaaabbbbbbbb")
        with self.assertRaises(container.ContainerError):
            container.chunk_spans(data[:-1])
        with self.assertRaises(container.ContainerError):
            container.chunk_spans(synthetic([12, 4], b"aaaabbbbbbbb"))

    def test_rejects_missing_sentinel(self):
        data = synthetic([4, 12, 12], b"aaaabbbbbbbb")
        with self.assertRaises(container.ContainerError):
            container.chunk_spans(data)

    def test_last_offset_must_end_at_file_size(self):
        with self.assertRaises(container.ContainerError):
            container.chunk_spans(synthetic([4, 10], b"aaaabbbbbbbbcccc"))

    def test_counts_zstd_prefix_offsets_without_decoding(self):
        payload = b"x" * 9 + b"\x28\xb5\x2f\xfd" + b"y" * 7
        data = synthetic([0, len(payload)], payload)
        spans = container.chunk_spans(data)
        self.assertEqual(len(spans), 1)
        self.assertEqual(container.count_zstd_prefixes(data, spans), 1)

    def test_describe_does_not_touch_chunk_payload(self):
        data = synthetic([4, 12, 20], b"aaaabbbbbbbbcccccccc")
        described = container.describe(data)
        self.assertNotIn("text", described)
        self.assertEqual(described["bytes"], len(data))


if __name__ == "__main__":
    unittest.main()
