from __future__ import annotations

import json
import struct
import tempfile
import unittest
from pathlib import Path

from tools import apply_translation as patcher
from tools import locale_records as records


def table(rows) -> bytes:
    """rows: list of (id, text) or None for a hole; stored sequentially."""
    entry_count = len(rows)
    filled = sum(1 for row in rows if row and row[1])
    out = struct.pack("<QQQ", entry_count, filled, 0x595896DC)
    out += b"\x00" * records.bucket_size(entry_count)
    entries = []
    values = b""
    for index, row in enumerate(rows):
        ident, text = row if row else (0, b"")
        if not ident or not text:
            entries.append((0, 0xFFFFFFFF, 0))
            continue
        offset = (entry_count - index) * records.ENTRY_SIZE - 8 + len(values)
        entries.append((ident, offset, len(text)))
        values += text
    body = b"".join(struct.pack("<QII", *entry) for entry in entries)
    return out + body + values


def metadata(chunk_count: int, total: int = 0) -> bytes:
    return struct.pack("<QQ", total, chunk_count - 1) + b"\x00" * 4 * (chunk_count - 1)


def container(tables, *, with_metadata: bool = False) -> bytes:
    chunk_count = len(tables) + (1 if with_metadata else 0)
    chunks = [patcher.build_chunk(patcher.STORED, metadata(chunk_count), 0)] if with_metadata else []
    chunks += [patcher.build_chunk(patcher.STORED, data, 0) for data in tables]
    return patcher.build_container(chunks)


class ApplyTranslationTests(unittest.TestCase):
    def test_reads_chunks_and_ignores_sentinel(self):
        data = container([table([(1, b"a")]), table([(2, b"b")])])
        self.assertEqual(len(patcher.read_container(data)), 2)

    def test_rebuild_without_changes_is_stable(self):
        data = container([table([(1, b"a"), (2, b"bb")])])
        rebuilt = patcher.build_container(patcher.read_container(data))
        self.assertEqual(rebuilt, data)

    def test_metadata_chunk_is_recognised_and_copied_verbatim(self):
        data = container([table([(1, b"a")]), table([(2, b"b")])], with_metadata=True)
        chunks = patcher.read_container(data)
        self.assertTrue(patcher.is_metadata_chunk(chunks[0], len(chunks)))
        self.assertFalse(patcher.is_metadata_chunk(chunks[1], len(chunks)))
        patched, stats = patcher.apply_translations(data, {2: "bb"})
        self.assertEqual(patcher.read_container(patched)[0], chunks[0])
        self.assertEqual(stats["applied"], 1)

    def test_metadata_chunk_is_not_counted_as_entries(self):
        data = container([table([(1, b"a")])], with_metadata=True)
        self.assertEqual([e["id"] for e in patcher.iter_all_entries(data)], [1])

    def test_translation_of_equal_length(self):
        data = container([table([(1, b"Hello"), (2, b"World")])])
        patched, stats = patcher.apply_translations(data, {2: "Świat"})
        self.assertEqual(stats["applied"], 1)
        texts = {e["id"]: e["text"] for e in patcher.iter_all_entries(patched)}
        self.assertEqual(texts[1], b"Hello")
        self.assertEqual(texts[2], "Świat".encode())

    def test_translation_of_different_length_keeps_offsets_valid(self):
        data = container([table([(1, b"a"), (2, b"bb"), (3, b"ccc")])])
        patched, _ = patcher.apply_translations(data, {1: "znacznie dłuższy tekst"})
        texts = {e["id"]: e["text"] for e in patcher.iter_all_entries(patched)}
        self.assertEqual(texts[1], "znacznie dłuższy tekst".encode())
        self.assertEqual(texts[2], b"bb")
        self.assertEqual(texts[3], b"ccc")

    def test_holes_and_placeholders_are_untouched(self):
        data = container([table([(1, b"x"), None, (3, b"\xff")])])
        patched, stats = patcher.apply_translations(data, {})
        self.assertEqual(stats["applied"], 0)
        self.assertEqual(
            [e["text"] for e in patcher.iter_all_entries(patched)], [b"x", b"\xff"]
        )

    def test_unknown_ids_are_reported_not_invented(self):
        data = container([table([(1, b"x")])])
        _, stats = patcher.apply_translations(data, {999: "nowy"})
        self.assertEqual(stats["applied"], 0)
        self.assertEqual(stats["ids_not_in_map"], 1)

    def test_verify_accepts_correct_patch(self):
        data = container([table([(1, b"a"), (2, b"b")])])
        patched, _ = patcher.apply_translations(data, {1: "aa"})
        result = patcher.verify(data, patched, {1: "aa"})
        self.assertEqual(result["changed"], 1)
        self.assertEqual(result["ids"], 2)

    def test_verify_rejects_a_lost_change(self):
        data = container([table([(1, b"a"), (2, b"b")])])
        with self.assertRaises(patcher.PatchError):
            patcher.verify(data, data, {1: "aa"})

    def test_container_must_end_at_file_size(self):
        data = container([table([(1, b"a")])])
        with self.assertRaises(patcher.PatchError):
            patcher.read_container(data[:-1])
        with self.assertRaises(patcher.PatchError):
            patcher.read_container(b"\x00" * 12)

    def test_chunk_size_must_match_block_header(self):
        chunk = patcher.build_chunk(patcher.STORED, b"abc", 0)
        with self.assertRaises(patcher.PatchError):
            patcher.split_chunk(chunk[:-1])

    def test_cli_refuses_to_overwrite_input_and_writes_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "game.map"
            source.write_bytes(container([table([(1, b"a")])]))
            rows = Path(tmp) / "pl.jsonl"
            rows.write_text(json.dumps({"id": f"{1:016x}", "text": "ą"}) + "\n", encoding="utf-8")
            self.assertEqual(
                patcher.main(["--map", str(source), "--tlumaczenia", str(rows), "--wyjscie", str(source)]), 2
            )
            target = Path(tmp) / "patched.map"
            self.assertEqual(
                patcher.main(["--map", str(source), "--tlumaczenia", str(rows), "--wyjscie", str(target)]), 0
            )
            texts = {e["id"]: e["text"] for e in patcher.iter_all_entries(target.read_bytes())}
            self.assertEqual(texts[1], "ą".encode())


if __name__ == "__main__":
    unittest.main()
