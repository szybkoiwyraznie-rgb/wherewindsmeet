from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools import build_translator_pack as pack


class BuildTranslatorPackTests(unittest.TestCase):
    def test_entry_keeps_numbering_and_frozen_source(self):
        lines = pack.render_entry(1, {"id": "abc", "text": "Northmount West"}, "Tekst")
        self.assertEqual(lines[0], "1. [Tekst] Northmount West")
        self.assertIn("   id: abc", lines)
        self.assertIn("   limit: 15 B", lines)
        self.assertIn("   EN: Northmount West", lines)
        self.assertEqual(lines[-1], "   PL:")

    def test_multiline_entry_repeats_en_and_pl_lines(self):
        lines = pack.render_entry(2, {"id": "x", "text": "pierwsza\ndruga"}, "Scena")
        self.assertEqual([l for l in lines if l.startswith("   EN:")], ["   EN: pierwsza", "   EN: druga"])
        self.assertEqual([l for l in lines if l == "   PL:"], ["   PL:", "   PL:"])

    def test_limit_counts_utf8_bytes_of_source(self):
        lines = pack.render_entry(1, {"id": "x", "text": "Zażółć #Yjaźń#E"}, "Tekst")
        self.assertIn(f"   limit: {len('Zażółć #Yjaźń#E'.encode('utf-8'))} B", lines)

    def test_empty_text_is_marked_but_keeps_place(self):
        lines = pack.render_entry(3, {"id": "x", "text": ""}, "Tekst")
        self.assertEqual(lines[0], "3. [Tekst] (pusty)")
        self.assertIn("   limit: 0 B", lines)

    def test_tokens_are_collected_once_each(self):
        tokens = pack.collect_tokens(["#Yzłoto#E i #Yzłoto#E", "$T(5001) {0}"])
        self.assertEqual(tokens["kolor"], ["#Y"])
        self.assertEqual(tokens["zamkniecie"], ["#E"])
        self.assertEqual(tokens["funkcja"], ["$T(5001)"])
        self.assertEqual(tokens["podstawienie"], ["{0}"])

    def test_build_pack_writes_readme_view_and_tokens(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "paczka"
            entries = [{"id": "a1", "text": "Unlocked at 5:00 on Jul 3"}, {"id": "b2", "text": "#YGot it#E"}]
            result = pack.build_pack(entries, out, group="Interfejs", view="05_interfejs")
            self.assertEqual(result["entries"], 2)
            self.assertTrue((out / "README.md").is_file())
            body = (out / "widoki" / "05_interfejs.md").read_text(encoding="utf-8")
            self.assertIn("1. [Interfejs] Unlocked at 5:00 on Jul 3", body)
            self.assertIn("2. [Interfejs] #YGot it#E", body)
            tokens = (out / "tokeny.tsv").read_text(encoding="utf-8")
            self.assertIn("#Y", tokens)
            self.assertIn("rodzaj", tokens.splitlines()[0])

    def test_load_entries_ignores_blank_lines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "e.jsonl"
            path.write_text('{"id":"1","text":"a"}\n\n{"id":"2","text":"b"}\n', encoding="utf-8")
            entries = pack.load_entries(path)
            self.assertEqual([e["id"] for e in entries], ["1", "2"])

    def test_entries_round_trip_as_valid_json(self):
        entry = {"id": "z", "text": "linia"}
        self.assertEqual(json.loads(json.dumps(entry)), entry)


if __name__ == "__main__":
    unittest.main()
