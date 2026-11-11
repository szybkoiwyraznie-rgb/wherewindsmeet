from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from tools import buduj_indeks
from tools import sceny_z_indeksu


ROOT = Path(__file__).resolve().parent.parent
REPO_LIMIT = 10 * 1024 * 1024  # tools/check_repository.py odrzuca większe pliki


def synthetic_scenes() -> list[dict]:
    """Wymyślone sceny w formacie `tools/timeline.py` (bez danych gry)."""
    return [
        {
            "dialog_no": 1001,
            "project": "dialog-test-a",
            "timeline_id": 11,
            "start_time": 0.0,
            "total_duration": 12,
            "before_black_screen": False,
            "chunk": 3,
            "chunk_index": 0,
            "lines": [
                {"time": 0.0, "order": 1, "source_id": 900, "speaker": "Gosia",
                 "speaker_no": 5, "skeleton": "skeleton-a", "text_id": "aa" * 8,
                 "formatted_text": "Pierwsza linia\nz łamaniem."},
                {"time": 4.5, "order": 1, "source_id": 901, "speaker": "Gosia",
                 "speaker_no": 5, "skeleton": "skeleton-a", "text_id": "bb" * 8,
                 "formatted_text": "Druga linia."},
                # Ten sam tag, inny numer: obsada nie może ich ze sobą mieszać.
                {"time": 9.0, "order": 1, "source_id": 902, "speaker": "Gosia",
                 "speaker_no": 6, "skeleton": "skeleton-b", "text_id": "cc" * 8,
                 "formatted_text": "Trzecia linia."},
            ],
        },
        {
            "dialog_no": None,
            "project": None,
            "timeline_id": 12,
            "start_time": 0.0,
            "total_duration": 3,
            "before_black_screen": None,
            "chunk": 3,
            "chunk_index": 1,
            "lines": [
                {"time": 0.0, "order": 0, "source_id": 903, "speaker": None,
                 "speaker_no": None, "skeleton": None, "text_id": "dd" * 8,
                 "formatted_text": "Linia bez mówcy."},
            ],
        },
    ]


def write_scenes(directory: Path, scenes: list[dict], name: str = "sceny_data999.jsonl") -> Path:
    path = directory / name
    with path.open("w", encoding="utf-8") as handle:
        for scene in scenes:
            handle.write(json.dumps(scene, ensure_ascii=False) + "\n")
    return path


class IndexBuildTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="wwm-indeks-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.scenes_path = write_scenes(self.root, synthetic_scenes())
        self.out = self.root / "index"

    def build(self, **kwargs):
        arguments = {"limit": 4096, "data": "2026-11-11"}
        arguments.update(kwargs)
        return buduj_indeks.build([self.scenes_path], None, None, self.out,
                                  arguments["limit"], arguments["data"])

    def test_manifest_counts_and_shards_match_files(self):
        manifest = self.build()
        self.assertEqual(manifest["format"], "wwm-indeks-v1")
        self.assertEqual(manifest["liczby"]["scen"], 2)
        self.assertEqual(manifest["liczby"]["kwestii"], 4)
        self.assertEqual(manifest["liczby"]["unikalnych_tekstow"], 4)
        self.assertEqual(manifest["liczby"]["mowcow"], 2)  # "Gosia" i brak mówcy

        for group in ("sceny", "teksty"):
            total = 0
            for shard in manifest["shardy"][group]:
                path = self.out / shard["plik"]
                self.assertTrue(path.is_file(), shard["plik"])
                self.assertLessEqual(path.stat().st_size, 4096, shard["plik"])
                rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
                self.assertEqual(len(rows), shard["linie"])
                self.assertEqual(path.stat().st_size, shard["bajtow"])
                total += len(rows)
            expected = (manifest["liczby"]["scen"] if group == "sceny"
                        else manifest["liczby"]["unikalnych_tekstow"])
            self.assertEqual(total, expected, group)

    def test_shards_are_rebuilt_from_scratch(self):
        self.build()
        stale = self.out / "sceny_999.jsonl"
        stale.write_text("{}\n", encoding="utf-8")
        self.build()
        self.assertFalse(stale.exists(), "stary shard powinien zniknąć")

    def test_round_trip_restores_scenes_without_game_files(self):
        self.build()
        scenes, texts, longer, manifest = sceny_z_indeksu.load_index(self.out)
        self.assertEqual(len(scenes), 2)
        self.assertEqual(len(texts), 4)
        self.assertEqual(longer, {})
        self.assertEqual(manifest["format"], "wwm-indeks-v1")

        original = synthetic_scenes()
        for source, restored in zip(original, scenes):
            expanded = sceny_z_indeksu.expand(restored, texts)
            self.assertEqual(expanded["dialog_no"], source["dialog_no"])
            self.assertEqual(expanded["project"], source["project"])
            self.assertEqual(expanded["total_duration"], source["total_duration"])
            self.assertEqual(len(expanded["lines"]), len(source["lines"]))
            for before, after in zip(source["lines"], expanded["lines"]):
                for field in ("time", "order", "source_id", "speaker",
                              "speaker_no", "text_id", "formatted_text"):
                    self.assertEqual(after[field], before[field], field)

    def test_speaker_number_is_not_lost_when_tag_repeats(self):
        scenes = synthetic_scenes()
        self.build()
        restored, texts, _longer, _m = sceny_z_indeksu.load_index(self.out)
        expanded = sceny_z_indeksu.expand(restored[0], texts)
        numbers = [line["speaker_no"] for line in expanded["lines"]]
        self.assertEqual(numbers, [5, 5, 6], "ten sam tag z dwoma numerami")

    def test_missing_text_is_reported_not_guessed(self):
        self.build()
        scenes, texts, _longer, _m = sceny_z_indeksu.load_index(self.out)
        del texts["aa" * 8]
        with self.assertRaises(SystemExit):
            sceny_z_indeksu.expand(scenes[0], texts)

    def test_wrong_shard_line_count_stops_the_run(self):
        manifest = self.build()
        manifest["shardy"]["sceny"][0]["linie"] += 1
        (self.out / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaises(SystemExit):
            sceny_z_indeksu.load_index(self.out)

    def test_unknown_format_is_rejected(self):
        self.build()
        path = self.out / "manifest.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["format"] = "wwm-indeks-v2"
        path.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaises(SystemExit):
            sceny_z_indeksu.load_index(self.out)


class CommittedIndexTests(unittest.TestCase):
    """Kontrola samego indeksu w repozytorium: czy jest spójny i mieści się w limicie."""

    def setUp(self):
        self.root = ROOT / "index"

    def test_committed_index_is_consistent(self):
        manifest = json.loads((self.root / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["format"], "wwm-indeks-v1")
        liczby = manifest["liczby"]

        scenes: list[dict] = []
        for shard in manifest["shardy"]["sceny"]:
            path = self.root / shard["plik"]
            self.assertTrue(path.is_file(), shard["plik"])
            self.assertLessEqual(path.stat().st_size, REPO_LIMIT, shard["plik"])
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
            self.assertEqual(len(rows), shard["linie"], shard["plik"])
            scenes.extend(rows)

        texts: dict[str, str] = {}
        for shard in manifest["shardy"]["teksty"]:
            path = self.root / shard["plik"]
            self.assertTrue(path.is_file(), shard["plik"])
            self.assertLessEqual(path.stat().st_size, REPO_LIMIT, shard["plik"])
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
            self.assertEqual(len(rows), shard["linie"], shard["plik"])
            for row in rows:
                self.assertNotIn(row["text_id"], texts, "powtórzony text_id")
                texts[row["text_id"]] = row["tekst_zh"]

        self.assertEqual(len(scenes), liczby["scen"])
        self.assertEqual(len(texts), liczby["unikalnych_tekstow"])

        # Każda kwestia ma tekst w shardach i mówcę z obsady sceny.
        lines = 0
        for scene in scenes:
            cast = {(row.get("mowca"), row.get("speaker_no")) for row in scene["obsada"]}
            for line in scene["linie"]:
                lines += 1
                self.assertIn(line["text_id"], texts, line["text_id"])
                self.assertIn((line.get("mowca"), line.get("speaker_no")), cast, line["text_id"])
        self.assertEqual(lines, liczby["kwestii"])

        # Pokrycie rejestru jest zapisane i sensowne.
        coverage = manifest["pokrycie"]
        self.assertGreater(coverage["dialog_timelines"], coverage["scen_z_dialog_no"])
        self.assertEqual(coverage["scen_poza_rejestrem"], 0)


if __name__ == "__main__":
    unittest.main()
