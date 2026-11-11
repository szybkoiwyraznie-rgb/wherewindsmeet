from __future__ import annotations

import struct
import unittest

from tools import locale_records as records


def build(rows, *, entry_count=None, timestamp=0x595896DC, buckets=None) -> bytes:
    """rows: list of (id, text) or None for a hole."""
    entry_count = entry_count if entry_count is not None else max(len(rows), 1)
    buckets = buckets if buckets is not None else records.bucket_size(entry_count)
    entries = []
    values = b""
    filled = 0
    for row in rows:
        ident, text = row if row else (0, b"")
        if ident and text:
            filled += 1
        entries.append((ident, text))
    out = struct.pack("<QQQ", entry_count, filled, timestamp) + b"\x00" * buckets
    entries_pos = len(out)
    table = b""
    blob = b""
    entries = entries + [(0, b"")] * (entry_count - len(entries))
    for index, (ident, text) in enumerate(entries):
        if not ident or not text:
            table += struct.pack("<QII", 0, 0xFFFFFFFF, 0)
            continue
        offset = (entry_count - index) * records.ENTRY_SIZE - 8 + len(blob)
        table += struct.pack("<QII", ident, offset, len(text))
        blob += text
    assert entries_pos == len(out)
    return out + table + blob


class LocaleRecordsTests(unittest.TestCase):
    def test_reads_ids_offsets_and_texts(self):
        payload = build([(0x1111, b"Hello"), (0x2222, b"World!")])
        texts = records.iter_texts(payload)
        self.assertEqual([t["text"] for t in texts], ["Hello", "World!"])
        self.assertEqual([t["id"] for t in texts], ["0000000000001111", "0000000000002222"])

    def test_holes_are_skipped(self):
        payload = build([(0x11, b"a"), None, (0x33, b"c")])
        texts = records.iter_texts(payload)
        self.assertEqual([t["text"] for t in texts], ["a", "c"])

    def test_bucket_size_follows_entry_count(self):
        self.assertEqual(records.bucket_size(0), 24)
        self.assertEqual(records.bucket_size(7), 24)
        self.assertEqual(records.bucket_size(511), 528)
        payload = build([(0x11, b"x")], entry_count=511, buckets=528)
        result = records.describe(payload)
        self.assertEqual(result["entry_count"], 511)
        self.assertEqual(result["holes"], 510)
        self.assertEqual(result["texts"], 1)

    def test_placeholder_value_is_not_text(self):
        payload = build([(0x11, b"\xff")])
        table = records.parse_table(payload)
        self.assertTrue(table["entries"][0]["placeholder"])
        self.assertEqual(records.iter_texts(payload), [])

    def test_describe_reports_aggregates_and_no_texts(self):
        payload = build([(1, b"abc"), None, (3, b"de")])
        result = records.describe(payload)
        self.assertEqual(result["texts"], 2)
        self.assertEqual(result["bytes_total"], 5)
        self.assertEqual(result["bytes_max"], 3)
        self.assertNotIn("text", result)

    def test_missing_value_encoding_is_reported(self):
        payload = build([(0x11, b"\xfe\xff")])
        with self.assertRaises(records.LayoutError):
            records.iter_texts(payload)
        self.assertEqual(records.iter_texts(payload, encoding="latin-1")[0]["text"], "þÿ")

    def test_truncated_payload_is_rejected(self):
        payload = build([(1, b"abc")])
        with self.assertRaises(records.LayoutError):
            records.parse_table(payload[: records.HEADER_SIZE + 4])
        with self.assertRaises(records.LayoutError):
            records.parse_table(b"\x00" * 8)

    def test_value_pointing_outside_payload_is_rejected(self):
        payload = bytearray(build([(0x11, b"ab")]))
        entries_pos = records.HEADER_SIZE + records.bucket_size(1)
        struct.pack_into("<I", payload, entries_pos + 12, 999)  # absurd length
        with self.assertRaises(records.LayoutError):
            records.parse_table(bytes(payload))

    def test_repacking_without_changes_reproduces_the_table(self):
        payload = build([(0x11, b"Hello"), None, (0x33, b"World!")])
        self.assertEqual(records.pack_table(payload, {}), payload)

    def test_repacking_replaces_only_requested_texts(self):
        payload = build([(0x11, b"Hello"), (0x22, b"World!")])
        repacked = records.pack_table(payload, {0x22: "Świecie!"})
        self.assertEqual(
            [t["text"] for t in records.iter_texts(repacked)], ["Hello", "Świecie!"]
        )
        self.assertNotEqual(len(repacked), len(payload))

    def test_repacked_table_keeps_holes_and_offsets_consistent(self):
        payload = build([(0x11, b"a"), None, (0x33, b"bbb"), (0x44, b"cccc")])
        repacked = records.pack_table(payload, {0x11: "aaaaa"})
        table = records.parse_table(repacked)
        self.assertEqual(table["entry_count"], 4)
        self.assertEqual(sum(1 for e in table["entries"] if not e["id"]), 1)
        entries_pos = records.HEADER_SIZE + records.bucket_size(4)
        for index, entry in enumerate(table["entries"]):
            if not entry["id"]:
                self.assertEqual(entry["offset"], 0xFFFFFFFF)
                continue
            start = entries_pos + records.ENTRY_SIZE * index + 8 + entry["offset"]
            self.assertEqual(repacked[start : start + entry["length"]], entry["text"])

    def test_markup_survives_verbatim(self):
        text = "Zażółć #Ygęślą#E jaźń $T(5001)".encode("utf-8")
        texts = records.iter_texts(build([(0x44, text)]))
        self.assertEqual(texts[0]["text"], text.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
