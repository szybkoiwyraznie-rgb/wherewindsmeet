from __future__ import annotations

import unittest

from tools import manifest_keys as keys


class ManifestKeysTests(unittest.TestCase):
    def test_reads_keys_written_as_u16_length_and_ascii(self):
        payload = b"\x10\x00AL.behavior.boss\x00\x00\x00" + b"\x16\x00dialog_timelines.10000001" + b"\x0c\x00dialog_test1"
        found = keys.keys_from_payload(payload)
        self.assertIn("AL.behavior.boss", found)
        self.assertIn("dialog_timelines.10000001", found)
        self.assertIn("dialog_test1", found)

    def test_dialog_ids_only_from_dialog_timelines_keys(self):
        found = ["dialog_timelines.10000001", "dialog_timelines.abc", "dialog_test1"]
        self.assertEqual(keys.dialog_ids(found), {10000001})

    def test_prefixes_count_by_first_segments(self):
        counter = keys.prefixes(["dialog_timelines.1", "dialog_timelines.2", "AL.behavior.boss"], depth=2)
        self.assertEqual(counter["dialog_timelines.1"], 1)
        self.assertEqual(counter["dialog_timelines.2"], 1)
        self.assertEqual(counter["AL.behavior"], 1)

    def test_report_counts_coverage_against_scenes(self):
        import json
        import tempfile
        from pathlib import Path

        payload = b"".join(
            b"\x19\x00dialog_timelines.%d" % number for number in (1, 2, 3)
        )
        with tempfile.TemporaryDirectory() as tmp:
            scenes = Path(tmp) / "sceny.jsonl"
            scenes.write_text(
                "\n".join(json.dumps({"dialog_no": number}) for number in (1, 2, 99)),
                encoding="utf-8",
            )
            result = keys.report(payload, scenes)
        self.assertEqual(result["dialog_timelines"], 3)
        self.assertEqual(result["scen_z_dialog_no"], 3)
        self.assertEqual(result["scen_poza_rejestrem"], 1)
        self.assertEqual(result["brakuje_dialogow"], 1)
        self.assertEqual(result["pokrycie_procent"], 100.0)


if __name__ == "__main__":
    unittest.main()
