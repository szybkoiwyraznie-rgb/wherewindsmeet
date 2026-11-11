from __future__ import annotations

import struct
import unittest

from tools import locale_container as container


def synthetic(chunks, *, magic: int = container.MAGIC, version: int = 1) -> bytes:
    count = len(chunks)
    offsets = []
    running = 0
    for chunk in chunks:
        offsets.append(running)
        running += len(chunk)
    offsets.append(running)
    table = struct.pack(f"<{len(offsets)}I", *offsets)
    return struct.pack("<III", magic, version, count) + table + b"".join(chunks)


class LocaleContainerTests(unittest.TestCase):
    def test_reads_header_and_all_chunk_spans(self):
        data = synthetic([b"idxx", b"aaaabbbbbbbb", b"cccccccc"])
        header = container.parse_header(data)
        self.assertEqual(header["version"], 1)
        self.assertEqual(header["count"], 3)
        base = 12 + 4 * 4
        self.assertEqual(
            container.chunk_spans(data),
            [(base, base + 4), (base + 4, base + 16), (base + 16, base + 24)],
        )

    def test_first_chunk_is_the_map_index_and_is_reported_separately(self):
        data = synthetic([b"idxx", b"aaaabbbbbbbb", b"cccccccc"])
        described = container.describe(data)
        self.assertEqual(described["chunks"], 3)
        self.assertEqual(described["data_chunks"], 2)
        self.assertEqual(described["index_chunk_bytes"], 4)
        self.assertEqual(described["chunk_bytes_min"], 8)
        self.assertEqual(described["chunk_bytes_total"], 20)
        start, end = container.metadata_span(data)
        self.assertEqual(end - start, 4)

    def test_rejects_foreign_magic_and_version(self):
        for kwargs in ({"magic": 0x11223344}, {"version": 2}):
            with self.subTest(**kwargs):
                with self.assertRaises(container.ContainerError):
                    container.parse_header(synthetic([b"idxx"], **kwargs))

    def test_rejects_short_file_and_empty_container(self):
        with self.assertRaises(container.ContainerError):
            container.parse_header(b"\xef\xbe\xad\xde\x01\x00")
        with self.assertRaises(container.ContainerError):
            container.parse_header(synthetic([]))

    def test_rejects_table_past_end_and_non_monotonic_offsets(self):
        data = synthetic([b"idxx", b"aaaabbbbbbbb"])
        with self.assertRaises(container.ContainerError):
            container.chunk_spans(data[:-1])
        non_monotonic = struct.pack("<III", container.MAGIC, 1, 2) + struct.pack("<3I", 4, 0, 16) + b"x" * 16
        with self.assertRaises(container.ContainerError):
            container.chunk_spans(non_monotonic)

    def test_last_offset_must_end_at_file_size(self):
        data = synthetic([b"idxx", b"aaaabbbbbbbb"])
        broken = bytearray(data)
        struct.pack_into("<I", broken, 12 + 4 * 2, 3)
        with self.assertRaises(container.ContainerError):
            container.chunk_spans(bytes(broken))

    def test_counts_zstd_prefix_offsets_without_decoding(self):
        chunk = b"\x04" + b"\x00" * 8 + b"\x28\xb5\x2f\xfd" + b"y" * 7
        data = synthetic([b"idxx", chunk])
        spans = container.chunk_spans(data)
        self.assertEqual(len(spans), 2)
        self.assertEqual(container.count_zstd_prefixes(data, spans), 1)

    def test_describe_does_not_touch_chunk_payload(self):
        data = synthetic([b"idxx", b"aaaabbbbbbbb"])
        described = container.describe(data)
        self.assertNotIn("text", described)
        self.assertEqual(described["bytes"], len(data))

    def test_cli_reports_failure_for_a_foreign_file(self):
        import json
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.bin"
            path.write_bytes(b"not a container at all")
            self.assertEqual(container.main([str(path)]), 1)
            data = synthetic([b"idxx", b"aaaabbbbbbbb"])
            path.write_bytes(data)
            self.assertEqual(container.main([str(path)]), 0)
            self.assertTrue(json.dumps(container.describe(data)))


if __name__ == "__main__":
    unittest.main()
