from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import warnings
from zipfile import ZipFile, ZIP_DEFLATED

from tools import validate_collector_return as intake


BASE = b"fictional locale map with no game data"
OBJECT = "pliki/000001_translate_words_map_en"
SOURCE = "Package/HD/oversea/locale/translate_words_map_en"
OTHER = "LocalData/Patch/HD/oversea/locale/translate_words_map_en"


def fixture():
    digest = hashlib.sha256(BASE).hexdigest()
    return {
        "format": "wwm-collection-v1",
        "collector_version": "1.0.0",
        "status": "collected",
        "inventory": {"path": "INWENTARZ.jsonl", "files": 2},
        "payload_bytes": len(BASE),
        "files": [
            {"source": SOURCE, "kind": "map_en", "bytes": len(BASE), "status": "copied", "sha256": digest, "stored_as": OBJECT},
            {"source": OTHER, "kind": "map_en", "bytes": len(BASE), "status": "duplicate", "sha256": digest, "stored_as": OBJECT},
        ],
        "problems": [],
    }


def archive(path: Path, report=None, *, payload=BASE, inventory=None, extras=()):
    if report is None:
        report = fixture()
    if inventory is None:
        inventory = [
            {"path": SOURCE, "bytes": len(BASE), "modified_utc": "2026-01-01T00:00:00Z"},
            {"path": OTHER, "bytes": len(BASE), "modified_utc": "2026-01-01T00:00:00Z"},
        ]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with ZipFile(path, "w", compression=ZIP_DEFLATED) as z:
            z.writestr("RAPORT.json", json.dumps(report).encode())
            z.writestr("RAPORT.txt", b"synthetic result\n")
            z.writestr("INWENTARZ.jsonl", b"".join(json.dumps(row).encode() + b"\n" for row in inventory))
            if payload is not None:
                z.writestr(OBJECT, payload)
            for name, content in extras:
                z.writestr(name, content)


class CollectorReturnTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "private.zip"

    def rejected(self, report=None, **kwargs):
        archive(self.path, report, **kwargs)
        with self.assertRaises(intake.InvalidReturn):
            intake.validate(self.path)

    def test_rejects_member_names_with_backslashes(self):
        # Windows PowerShell 5.1 CreateFromDirectory wrote "pliki\\name".
        archive(self.path, extras=(("pliki\\000001_map", BASE),))
        with self.assertRaises(intake.InvalidReturn) as caught:
            intake.validate(self.path)
        self.assertIn("backslashes", str(caught.exception))

    def test_validates_unique_and_duplicate_bytes_without_modifying_archive(self):
        archive(self.path)
        before = self.path.read_bytes()
        result = intake.validate(self.path)
        self.assertEqual(result["validation"], "passed")
        self.assertEqual(result["collection_status"], "collected")
        self.assertEqual(result["inventory_files"], 2)
        self.assertEqual(result["candidate_files"], 2)
        self.assertEqual(result["unique_files"], 1)
        self.assertEqual(result["payload_bytes"], len(BASE))
        self.assertEqual(self.path.read_bytes(), before)

    def test_partial_return_is_valid_but_not_misrepresented_as_complete(self):
        report = fixture()
        report["status"] = "partial"
        report["files"].append({"source": "Package/HD/oversea/data205", "kind": "context_candidate", "bytes": 200,
                                "status": "skipped_limit", "sha256": None, "stored_as": None})
        archive(self.path, report)
        result = intake.validate(self.path)
        self.assertEqual(result["collection_status"], "partial")
        self.assertEqual(result["failed_or_skipped"], 1)
        report["status"] = "collected"
        self.rejected(report)

    def test_wrong_payload_or_sha_is_rejected(self):
        self.rejected(payload=b"x" * len(BASE))
        changed = fixture()
        changed["files"][0]["sha256"] = "0" * 64
        self.rejected(changed)
        self.rejected(payload=None)

    def test_mismatched_bytes_sizes_and_reference_counts_are_rejected(self):
        for mutate in (
            lambda r: r.update(payload_bytes=len(BASE) + 1),
            lambda r: r["files"][0].update(bytes=len(BASE) - 1),
            lambda r: r["files"][1].update(status="copied"),
            lambda r: r["inventory"].update(files=3),
            lambda r: r["files"][1].update(stored_as="pliki/../../secret"),
            lambda r: r["files"][1].update(sha256="not-a-sha"),
        ):
            report = fixture()
            mutate(report)
            with self.subTest(report=report):
                self.rejected(report)

    def test_unsafe_and_duplicate_archive_members_rejected(self):
        for extras in (
            [("../escape", b"x")],
            [("pliki/../../escape", b"x")],
            [("/root", b"x")],
            [("pliki\\evil", b"x")],
            [(OBJECT, BASE)],
            [("pliki/000002_data3", b"unreferenced")],
        ):
            with self.subTest(extras=extras):
                self.rejected(extras=extras)

    def test_original_paths_and_inventory_are_safe_and_unique(self):
        for bad in ("../outside", "C:/secret", "Package/../secret", "Package//secret", "Package\\secret", "Other/file"):
            report = fixture()
            report["files"][0]["source"] = bad
            with self.subTest(source=bad):
                self.rejected(report)
        row = {"path": SOURCE, "bytes": len(BASE), "modified_utc": "z"}
        self.rejected(inventory=[row, row])
        self.rejected(inventory=[row, {"path": "Package/../secret", "bytes": 0, "modified_utc": "z"}])
        self.rejected(inventory=[row, {"path": OTHER, "bytes": True, "modified_utc": "z"}])

    def test_invalid_states_and_duplicate_json_fields_are_rejected(self):
        for field, value in (("status", "unknown"), ("kind", "executable"), ("bytes", -1)):
            report = fixture()
            report["files"][0][field] = value
            with self.subTest(field=field):
                self.rejected(report)
        report = fixture()
        report["files"][0]["status"] = "skipped_limit"
        self.rejected(report)
        with self.assertRaises(intake.InvalidReturn):
            intake.decode_json(b'{"a":1,"a":2}')

    def test_cli_output_contains_counts_not_private_filenames(self):
        archive(self.path)
        runner = Path(intake.__file__)
        result = subprocess.run([sys.executable, str(runner), str(self.path)], capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn(SOURCE, result.stdout)
        self.assertNotIn(str(self.path), result.stdout)
        self.assertEqual(json.loads(result.stdout)["inventory_files"], 2)
        bad = self.path.with_name("missing-secret-name.zip")
        result = subprocess.run([sys.executable, str(runner), str(bad)], capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 1)
        self.assertNotIn(str(bad), result.stderr)

    def test_symlink_member_is_rejected_even_without_extracting(self):
        import stat
        from zipfile import ZipInfo
        archive(self.path)
        info = ZipInfo("pliki/000002_data3")
        info.create_system = 3
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        with ZipFile(self.path, "a") as z:
            z.writestr(info, "../../secret")
        with self.assertRaises(intake.InvalidReturn):
            intake.validate(self.path)

    def test_inventory_line_limit_and_total_file_limit_are_enforced(self):
        rows = [{"path": "Package/" + "x" * intake.MAX_LINE_BYTES, "bytes": 0, "modified_utc": "z"}]
        report = fixture()
        report["inventory"]["files"] = 1
        self.rejected(report, inventory=rows)
        archive(self.path)
        original = intake.MAX_ARCHIVE_BYTES
        try:
            intake.MAX_ARCHIVE_BYTES = 1
            with self.assertRaises(intake.InvalidReturn):
                intake.validate(self.path)
        finally:
            intake.MAX_ARCHIVE_BYTES = original


if __name__ == "__main__":
    unittest.main()
