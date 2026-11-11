from __future__ import annotations

import builtins
import json
import os
from pathlib import Path
import socket
import stat
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tools import inspect_localization as inventory


ROOT = Path(__file__).resolve().parent.parent


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="private-owner-path-")
        self.addCleanup(self.temp.cleanup)
        self.locale = Path(self.temp.name) / "locale"
        self.locale.mkdir()

    def test_only_known_names_and_sizes_are_reported_without_reading_contents(self):
        (self.locale / inventory.CANDIDATES[0]).write_bytes(b"synthetic base")
        (self.locale / inventory.CANDIDATES[1]).write_bytes(b"fake diff")
        (self.locale / "PRIVATE_NAME.txt").write_text("PRIVATE CONTENT", encoding="utf-8")
        with (
            patch.object(builtins, "open", side_effect=AssertionError("contents were opened")),
            patch.object(Path, "open", side_effect=AssertionError("contents were opened")),
            patch("os.open", side_effect=AssertionError("contents were opened")),
            patch.object(os, "scandir", side_effect=AssertionError("directory was listed")),
            patch.object(os, "listdir", side_effect=AssertionError("directory was listed")),
            patch.object(socket, "socket", side_effect=AssertionError("socket was created")),
        ):
            report = inventory.inspect_directory(self.locale)
        self.assertEqual(report["result"], "candidates_found")
        self.assertEqual(report["directory_state"], "matched_start_end")
        self.assertEqual(report["candidates"][0]["size_bytes"], len(b"synthetic base"))
        self.assertEqual(report["candidates"][1]["size_bytes"], len(b"fake diff"))
        self.assertEqual(report["candidates"][2]["state"], "absent")
        serialized = json.dumps(report)
        self.assertNotIn(str(self.locale), serialized)
        self.assertNotIn("private-owner-path", serialized)
        self.assertNotIn("PRIVATE_NAME", serialized)
        self.assertNotIn("PRIVATE CONTENT", serialized)
        self.assertFalse(report["contents_read"])
        self.assertFalse(report["hashes_computed"])

    def test_empty_directory_does_not_claim_a_compatible_build(self):
        report = inventory.inspect_directory(self.locale)
        self.assertEqual(report["result"], "no_candidates")
        self.assertTrue(all(item["state"] == "absent" for item in report["candidates"]))
        self.assertNotIn("version", report)

    def test_non_regular_candidate_makes_report_incomplete(self):
        (self.locale / inventory.CANDIDATES[0]).mkdir()
        report = inventory.inspect_directory(self.locale)
        self.assertEqual(report["result"], "incomplete")
        self.assertEqual(report["candidates"][0]["state"], "not_regular")
        self.assertNotIn("size_bytes", report["candidates"][0])

    def test_symlink_and_windows_reparse_point_are_not_followed(self):
        original = inventory._lstat
        first, second = inventory.CANDIDATES[:2]

        def fake_lstat(path):
            if Path(path).name == first:
                return SimpleNamespace(st_mode=stat.S_IFLNK, st_size=99)
            if Path(path).name == second:
                return SimpleNamespace(
                    st_mode=stat.S_IFREG,
                    st_size=99,
                    st_file_attributes=inventory.FILE_ATTRIBUTE_REPARSE_POINT,
                )
            return original(path)

        with patch.object(inventory, "_lstat", side_effect=fake_lstat):
            report = inventory.inspect_directory(self.locale)
        self.assertEqual(report["result"], "incomplete")
        self.assertEqual([item["state"] for item in report["candidates"][:2]], ["link_skipped"] * 2)
        self.assertNotIn("size_bytes", report["candidates"][0])

        # POSIX runners can also exercise real, including dangling, symlinks.
        # Windows reparse points are covered above without assuming privileges.
        if os.name == "posix":
            (self.locale / first).symlink_to(Path(self.temp.name) / "missing-target")
            actual = inventory.inspect_directory(self.locale)
            self.assertEqual(actual["candidates"][0]["state"], "link_skipped")
            self.assertEqual(actual["result"], "incomplete")
            link_to_directory = Path(self.temp.name) / "linked-locale"
            link_to_directory.symlink_to(self.locale, target_is_directory=True)
            with self.assertRaises(inventory.InventoryError):
                inventory.inspect_directory(link_to_directory)

    def test_inaccessible_candidate_does_not_leak_exception_or_claim_absent(self):
        original = inventory._lstat

        def fake_lstat(path):
            if Path(path).name == inventory.CANDIDATES[0]:
                raise PermissionError("private path and sensitive OS details")
            return original(path)

        with patch.object(inventory, "_lstat", side_effect=fake_lstat):
            report = inventory.inspect_directory(self.locale)
        self.assertEqual(report["result"], "incomplete")
        self.assertEqual(report["candidates"][0]["state"], "inaccessible")
        self.assertNotIn("sensitive", json.dumps(report))

    def test_directory_disappearing_mid_scan_does_not_claim_absence(self):
        (self.locale / inventory.CANDIDATES[0]).write_bytes(b"private synthetic size")
        original = inventory._lstat
        root_calls = 0

        def disappearing_root(path):
            nonlocal root_calls
            if Path(path) == self.locale:
                root_calls += 1
                if root_calls == 2:
                    raise FileNotFoundError("private directory removed")
            return original(path)

        with patch.object(inventory, "_lstat", side_effect=disappearing_root):
            report = inventory.inspect_directory(self.locale)
        self.assertEqual(report["result"], "incomplete")
        self.assertEqual(report["directory_state"], "changed_or_inaccessible")
        self.assertTrue(all(item["state"] == "unknown" for item in report["candidates"]))
        self.assertTrue(all("size_bytes" not in item for item in report["candidates"]))
        self.assertNotIn("private directory", json.dumps(report))

    def test_replaced_or_linked_root_discards_observations(self):
        original = inventory._lstat
        root_metadata = original(self.locale)
        for new_root in (
            SimpleNamespace(
                st_mode=stat.S_IFDIR,
                st_dev=root_metadata.st_dev,
                st_ino=root_metadata.st_ino + 1,
            ),
            SimpleNamespace(st_mode=stat.S_IFLNK),
        ):
            with self.subTest(new_mode=new_root.st_mode):
                root_calls = 0

                def replaced_root(path):
                    nonlocal root_calls
                    if Path(path) == self.locale:
                        root_calls += 1
                        if root_calls == 2:
                            return new_root
                    return original(path)

                with patch.object(inventory, "_lstat", side_effect=replaced_root):
                    report = inventory.inspect_directory(self.locale)
                self.assertEqual(report["result"], "incomplete")
                self.assertEqual(report["directory_state"], "changed_or_inaccessible")
                self.assertTrue(all(item["state"] == "unknown" for item in report["candidates"]))

    def test_root_must_exist_be_a_directory_and_not_be_a_link(self):
        with self.assertRaises(inventory.InventoryError):
            inventory.inspect_directory(self.locale / "missing")
        file_path = self.locale / "file"
        file_path.write_bytes(b"x")
        with self.assertRaises(inventory.InventoryError):
            inventory.inspect_directory(file_path)
        with patch.object(
            inventory, "_lstat", return_value=SimpleNamespace(st_mode=stat.S_IFLNK)
        ):
            with self.assertRaises(inventory.InventoryError):
                inventory.inspect_directory(self.locale)

    def test_cli_success_reports_only_metadata(self):
        (self.locale / inventory.CANDIDATES[0]).write_bytes(b"synthetic")
        p = subprocess.run(
            [sys.executable, str(ROOT / "tools/inspect_localization.py"), "--locale-dir", str(self.locale)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads(p.stdout)["result"], "candidates_found")
        self.assertNotIn(str(self.locale), p.stdout + p.stderr)
        self.assertNotIn("synthetic", p.stdout)

    def test_cli_emits_redacted_json_and_incomplete_exit_code(self):
        (self.locale / inventory.CANDIDATES[0]).mkdir()
        p = subprocess.run(
            [sys.executable, str(ROOT / "tools/inspect_localization.py"), "--locale-dir", str(self.locale)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(p.returncode, 1, p.stderr)
        self.assertEqual(json.loads(p.stdout)["result"], "incomplete")
        self.assertNotIn(str(self.locale), p.stdout + p.stderr)

    def test_cli_rejects_invalid_directory_without_echoing_path(self):
        missing = self.locale / "SECRET_PRIVATE_DIRECTORY"
        p = subprocess.run(
            [sys.executable, str(ROOT / "tools/inspect_localization.py"), "--locale-dir", str(missing)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(p.returncode, 2)
        self.assertNotIn("SECRET_PRIVATE_DIRECTORY", p.stdout + p.stderr)

    def test_cli_argument_errors_do_not_echo_supplied_values(self):
        p = subprocess.run(
            [
                sys.executable, str(ROOT / "tools/inspect_localization.py"),
                "--locale-dir", str(self.locale), "--unexpected", "SECRET_PRIVATE_ARGUMENT",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(p.returncode, 2)
        self.assertNotIn("SECRET_PRIVATE_ARGUMENT", p.stdout + p.stderr)
        self.assertNotIn(str(self.locale), p.stdout + p.stderr)


if __name__ == "__main__":
    unittest.main()
