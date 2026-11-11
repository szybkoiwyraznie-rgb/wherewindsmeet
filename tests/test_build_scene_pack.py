from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools import build_scene_pack as pack


def scene(order, dialog_no, project, lines, duration=10.0):
    return {
        "dialog_no": dialog_no,
        "project": project,
        "total_duration": duration,
        "lines": lines,
    }


def line(time, speaker, text_id, zh, number=None):
    return {
        "time": time,
        "order": 255,
        "source_id": 1,
        "speaker": speaker,
        "speaker_no": number,
        "skeleton": None,
        "text_id": text_id,
        "formatted_text": zh,
    }


class ScenePackTests(unittest.TestCase):
    def setUp(self):
        self.scenes = [
            scene(0, 300002, "对话-b", [line(5.0, "乙", "bbbb", "第二句")]),
            scene(1, 300001, "对话-b", [line(0.0, "甲", "aaaa", "第一句"), line(4.0, "乙", "bbbb", "第二句")]),
            scene(2, None, None, [line(0.0, None, "cccc", "bez mówcy")]),
        ]

    def test_order_is_dialog_no_and_scenes_without_one_go_last(self):
        scenes = pack.fill_missing_order([dict(item) for item in self.scenes])
        by_dialog = {item["dialog_no"]: item["order"] for item in scenes}
        self.assertEqual(by_dialog[300001], 1)
        self.assertEqual(by_dialog[300002], 2)
        missing = [item for item in scenes if item["dialog_no"] is None][0]
        self.assertGreaterEqual(missing["order"], 9001)
        self.assertEqual(missing["order_kind"], "kolejność zapisu")

    def test_speaker_kind_marks_player_and_technical_groups(self):
        self.assertEqual(pack.speaker_kind("玩家"), "gracz")
        self.assertEqual(pack.speaker_kind("player_2"), "gracz")
        self.assertEqual(pack.speaker_kind("Entity轨道组"), "techniczny")
        self.assertEqual(pack.speaker_kind("琥珀"), "postać")
        self.assertEqual(pack.speaker_kind(None), "brak")

    def test_table_has_speaker_chinese_and_english(self):
        scene = self.scenes[1]
        scene["order"] = 1
        blocks = "\n".join(pack.scene_block(scene, {"aaaa": "First line"}))
        self.assertIn("| 1 | 0.00 | 甲 | 第一句 | First line | `aaaa` |", blocks)
        self.assertIn("obsada: 甲 (1), 乙 (1)", blocks)

    def test_missing_speaker_and_english_are_marked(self):
        scene = self.scenes[2]
        scene["order"] = 9001
        blocks = "\n".join(pack.scene_block(scene, {}))
        self.assertIn("(bez nazwy w danych)", blocks)
        self.assertIn("| — |", blocks)

    def test_pipe_and_newline_do_not_break_the_table(self):
        self.assertEqual(pack.clean("a|b\nc"), "a\\|b<br>c")

    def test_end_to_end_writes_index_speakers_and_scene_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "sceny.jsonl"
            source.write_text("\n".join(json.dumps(item, ensure_ascii=False) for item in self.scenes), encoding="utf-8")
            english = root / "en.jsonl"
            english.write_text(json.dumps({"id": "aaaa", "text": "First line"}) + "\n", encoding="utf-8")
            out = root / "wyjscie"
            argv = [str(source), "--angielski", str(english), "--wyjscie", str(out)]
            import sys

            old = sys.argv
            sys.argv = ["build_scene_pack.py"] + argv
            try:
                self.assertEqual(pack.main(), 0)
            finally:
                sys.argv = old
            self.assertTrue((out / "00_INDEX.md").exists())
            self.assertTrue((out / "01_MOWCY.md").exists())
            self.assertTrue((out / "02_CHRONOLOGIA.md").exists())
            self.assertTrue((out / "sceny.jsonl").exists())
            body = (out / "sceny" / "b.md").read_text(encoding="utf-8")
            self.assertIn("第一句", body)
            speakers = (out / "01_MOWCY.md").read_text(encoding="utf-8")
            self.assertIn("| 甲 | 1 | postać | — |", speakers)


if __name__ == "__main__":
    unittest.main()
