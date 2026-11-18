from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.index_storyline_graphs import build


class StorylineGraphIndexTests(unittest.TestCase):
    def test_build_extracts_only_selected_metadata(self) -> None:
        document = {
            "Variables": {"private_text": "must not be copied"},
            "Storyline": {
                "NodeBuffer": [
                    {"Type": "TrackTaskNode", "Data": {"task_no": 380493, "label": "omit"}},
                    {
                        "Type": "DialogCutsceneSequenceNode",
                        "Data": {
                            "sequence": [
                                {"id": 2560507, "type": 1, "auto_preload_next": True}
                            ],
                            "dialog": "omit",
                        },
                    },
                    {
                        "Type": "GameLevelTransferNode",
                        "Data": {"transfer_no": 30019, "space_no": 31003, "position": [1, 2, 3]},
                    },
                    {
                        "Type": "ClientRunStorylineNode",
                        "Data": {"storyline_path": "client/example.ets", "other": "omit"},
                    },
                ],
                "NodeKeyList": ["omitted key"],
            },
        }
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            (source / "5_0123456789abcdef.bin").write_text(
                json.dumps(document), encoding="utf-8"
            )
            (source / "ignored.bin").write_bytes(b"not JSON")
            rows = build(source)

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["block"], "5_0123456789abcdef")
        self.assertEqual(row["pack"], 5)
        self.assertEqual(row["asset_id"], "0123456789abcdef")
        self.assertEqual(row["nodes"], 4)
        self.assertEqual(row["task_ids"], [380493])
        self.assertEqual(row["transfer_ids"], [30019])
        self.assertEqual(row["space_ids"], [31003])
        self.assertEqual(row["cutscene_sequence"], [
            {"id": 2560507, "type": 1, "auto_preload_next": True}
        ])
        self.assertEqual(row["nested_storylines"], ["client/example.ets"])
        serialized = json.dumps(row)
        self.assertNotIn("private_text", serialized)
        self.assertNotIn("position", serialized)
        self.assertNotIn("omitted key", serialized)

    def test_non_storyline_json_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            (source / "1_manifest.bin").write_text('{"Version": 1}', encoding="utf-8")
            self.assertEqual(build(source), [])


if __name__ == "__main__":
    unittest.main()
