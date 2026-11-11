from __future__ import annotations

import struct
import unittest

from tools import locale_records as records


def build(entries, *, index=b"", group=1, constant=records.CONSTANT, reserved=0) -> bytes:
    header = struct.pack("<QQII", group, len(entries), constant, reserved)
    table = b"".join(struct.pack("<QII", digest, kind, len(text)) for digest, kind, text in entries)
    return header + index + table + b"".join(text for _, _, text in entries)


class LocaleRecordsTests(unittest.TestCase):
    def test_reads_records_and_concatentated_texts(self):
        entries = [(0x1111, 8, b"Hello"), (0x2222, 8, b""), (0x3333, 8, b"World!")]
        parsed = records.parse_chunk(build(entries, index=b"\x00" * 24))
        self.assertEqual(parsed["index_size"], 24)
        self.assertEqual([entry["text"] for entry in parsed["entries"]], [b"Hello", b"", b"World!"])
        self.assertEqual([entry["hash"] for entry in parsed["entries"]], [0x1111, 0x2222, 0x3333])

    def test_describe_reports_aggregates_only(self):
        entries = [(0x11, 8, b"abc"), (0x22, 30, b"de"), (0x33, 8, b"")]
        result = records.describe(build(entries, index=b"\x00" * 8))
        self.assertEqual(result["records"], 3)
        self.assertEqual(result["text_bytes_total"], 5)
        self.assertEqual(result["text_bytes_min"], 0)
        self.assertEqual(result["text_bytes_max"], 3)
        self.assertEqual(result["empty_texts"], 1)
        self.assertEqual(result["non_text_types"], 1)
        self.assertNotIn("text", result)

    def test_index_size_must_be_found_exactly(self):
        entries = [(0x11, 8, b"abcd")]
        payload = build(entries, index=b"\x00" * 12)
        self.assertEqual(records.parse_chunk(payload)["index_size"], 12)
        # a truncated payload must be rejected rather than guessed
        with self.assertRaises(records.LayoutError):
            records.parse_chunk(payload[:-1])

    def test_rejects_foreign_constant_and_reserved_field(self):
        entries = [(0x11, 8, b"a")]
        with self.assertRaises(records.LayoutError):
            records.parse_chunk(build(entries, constant=0x12345678))
        with self.assertRaises(records.LayoutError):
            records.parse_chunk(build(entries, index=b"\x00" * 4, reserved=7))

    def test_rejects_empty_chunk_and_short_header(self):
        with self.assertRaises(records.LayoutError):
            records.parse_chunk(b"\x00" * 8)
        with self.assertRaises(records.LayoutError):
            records.parse_chunk(struct.pack("<QQII", 1, 0, records.CONSTANT, 0))

    def test_rejects_records_that_cannot_fit(self):
        header = struct.pack("<QQII", 1, 10, records.CONSTANT, 0)
        with self.assertRaises(records.LayoutError):
            records.parse_chunk(header + b"\x00" * 16)

    def test_lengths_that_overrun_the_payload_are_rejected(self):
        header = struct.pack("<QQII", 1, 1, records.CONSTANT, 0)
        table = struct.pack("<QII", 0x11, 8, 999)
        with self.assertRaises(records.LayoutError):
            records.parse_chunk(header + b"\x00" * 4 + table + b"short")

    def test_utf8_text_is_returned_verbatim_including_markup(self):
        text = "Zażółć #Ygęślą#E jaźń".encode("utf-8")
        payload = build([(0x44, 8, text)], index=b"\x00" * 4)
        parsed = records.parse_chunk(payload)
        self.assertEqual(parsed["entries"][0]["text"], text)


if __name__ == "__main__":
    unittest.main()
