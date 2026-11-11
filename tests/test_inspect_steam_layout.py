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
from tools import inspect_steam_layout as layout


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "tools" / "inspect_steam_layout.py"


class SteamLayoutTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="private-steam-path-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "synthetic-game"
        self.root.mkdir()
        self.package = self.root.joinpath(*layout.LAYERS[0][1])
        self.patch = self.root.joinpath(*layout.LAYERS[1][1])
        self.package.mkdir(parents=True)
        self.patch.mkdir(parents=True)

    def test_two_groups_known_candidates_and_sizes_without_reading_contents(self):
        (self.package / inventory.CANDIDATES[0]).write_bytes(b"synthetic base")
        (self.patch / inventory.CANDIDATES[1]).write_bytes(b"synthetic update")
        (self.package / "PRIVATE-NAME.txt").write_text("PRIVATE CONTENT", encoding="utf-8")
        with (
            patch.object(builtins, "open", side_effect=AssertionError("opened contents")),
            patch.object(Path, "open", side_effect=AssertionError("opened contents")),
            patch("os.open", side_effect=AssertionError("opened contents")),
            patch.object(os, "mkdir", side_effect=AssertionError("created directory")),
            patch.object(os, "remove", side_effect=AssertionError("removed file")),
            patch.object(os, "unlink", side_effect=AssertionError("removed entry")),
            patch.object(os, "rename", side_effect=AssertionError("renamed entry")),
            patch.object(os, "replace", side_effect=AssertionError("replaced entry")),
            patch.object(os, "scandir", side_effect=AssertionError("listed directory")),
            patch.object(os, "listdir", side_effect=AssertionError("listed directory")),
            patch.object(socket, "socket", side_effect=AssertionError("network access")),
        ):
            report = layout.inspect_layout(self.root)
        self.assertEqual(report["result"], "candidates_found")
        self.assertEqual(report["root_state"], "matched_start_end")
        self.assertEqual([layer["role"] for layer in report["layers"]], ["package", "patch"])
        self.assertEqual([layer["candidate_result"] for layer in report["layers"]],
                         ["candidates_found", "candidates_found"])
        self.assertEqual(report["layers"][0]["candidates"][0]["size_bytes"], len(b"synthetic base"))
        self.assertEqual(report["layers"][1]["candidates"][1]["size_bytes"], len(b"synthetic update"))
        for key in ("candidate_contents_read", "hashes_computed", "game_tree_writes_attempted",
                    "input_path_included", "build_or_game_identity_verified", "atomic_snapshot_verified"):
            self.assertFalse(report[key], key)
        serialized = json.dumps(report)
        for value in (str(self.root), "private-steam-path", "PRIVATE-NAME", "PRIVATE CONTENT"):
            self.assertNotIn(value, serialized)

    def test_empty_locations_do_not_prove_game_has_no_localization(self):
        report = layout.inspect_layout(self.root)
        self.assertEqual(report["result"], "no_candidates")
        for layer in report["layers"]:
            self.assertEqual(layer["directory_state"], "available")
            self.assertEqual(layer["candidate_result"], "no_candidates")
            self.assertEqual(len(layer["candidates"]), len(inventory.CANDIDATES))
            self.assertTrue(all(item["state"] == "absent" for item in layer["candidates"]))
        self.assertFalse(report["build_or_game_identity_verified"])

    def test_missing_layer_is_not_reported_as_nine_absent_files(self):
        (self.package / inventory.CANDIDATES[0]).write_bytes(b"synthetic base")
        self.patch.rmdir()
        report = layout.inspect_layout(self.root)
        self.assertEqual(report["result"], "incomplete")
        package, patch_layer = report["layers"]
        self.assertEqual(package["directory_state"], "available")
        self.assertEqual(package["candidate_result"], "candidates_found")
        self.assertEqual(patch_layer["directory_state"], "missing")
        self.assertIsNone(patch_layer["candidate_result"])
        self.assertEqual(patch_layer["candidates"], [])

    def test_inaccessible_or_non_directory_component_is_incomplete(self):
        actual_lstat = inventory._lstat
        def denied(path):
            if Path(path) == self.root / "LocalData":
                raise PermissionError("SECRET-PATH")
            return actual_lstat(path)
        with patch.object(inventory, "_lstat", side_effect=denied):
            report = layout.inspect_layout(self.root)
        self.assertEqual(report["result"], "incomplete")
        self.assertEqual(report["layers"][1]["directory_state"], "inaccessible")
        self.assertEqual(report["layers"][1]["candidates"], [])
        self.assertNotIn("SECRET-PATH", json.dumps(report))
        replacement = self.root / "Package" / "HD" / "oversea" / "locale"
        replacement.rmdir()
        replacement.write_bytes(b"synthetic file")
        report = layout.inspect_layout(self.root)
        self.assertEqual(report["layers"][0]["directory_state"], "not_directory")
        self.assertEqual(report["result"], "incomplete")

    def test_layer_link_or_reparse_is_never_walked(self):
        actual_lstat = inventory._lstat
        watched = self.root / "Package" / "HD"
        for fake in (SimpleNamespace(st_mode=stat.S_IFLNK),
                     SimpleNamespace(st_mode=stat.S_IFDIR, st_file_attributes=inventory.FILE_ATTRIBUTE_REPARSE_POINT)):
            traversed = []
            def redirection(path):
                path = Path(path)
                if watched in path.parents:
                    traversed.append(path)
                    raise AssertionError("must not traverse a link")
                return fake if path == watched else actual_lstat(path)
            with self.subTest(mode=fake.st_mode), patch.object(inventory, "_lstat", side_effect=redirection):
                report = layout.inspect_layout(self.root)
                self.assertEqual(report["layers"][0]["directory_state"], "link_skipped")
                self.assertEqual(report["layers"][0]["candidates"], [])
                self.assertEqual(traversed, [])
                self.assertEqual(report["result"], "incomplete")

    def test_real_links_are_rejected_when_posix_symlinks_are_available(self):
        # Windows reparse behaviour is covered by the simulated test above;
        # POSIX also exercises actual links without assuming Windows privileges.
        if os.name == "posix":
            alias = self.root.parent / "alias"
            alias.symlink_to(self.root, target_is_directory=True)
            with self.assertRaises(inventory.InventoryError):
                layout.inspect_layout(alias)
            self.patch.rmdir()
            self.patch.symlink_to(self.package, target_is_directory=True)
            report = layout.inspect_layout(self.root)
            self.assertEqual(report["result"], "incomplete")
            self.assertEqual(report["layers"][1]["directory_state"], "link_skipped")
            self.assertEqual(report["layers"][1]["candidates"], [])

    def test_changed_layer_discards_candidate_observations(self):
        (self.package / inventory.CANDIDATES[0]).write_bytes(b"synthetic")
        actual_lstat = inventory._lstat
        actual = actual_lstat(self.package)
        calls = 0
        def changed(path):
            nonlocal calls
            if Path(path) == self.package:
                calls += 1
                if calls >= 4:
                    return SimpleNamespace(st_mode=stat.S_IFDIR, st_dev=actual.st_dev, st_ino=actual.st_ino + 1)
            return actual_lstat(path)
        with patch.object(inventory, "_lstat", side_effect=changed):
            report = layout.inspect_layout(self.root)
        self.assertEqual(report["result"], "incomplete")
        self.assertEqual(report["layers"][0]["directory_state"], "changed_or_inaccessible")
        self.assertEqual(report["layers"][0]["candidates"], [])
        self.assertEqual(report["layers"][1]["directory_state"], "available")

    def test_changed_intermediate_directory_discards_only_its_layer(self):
        (self.package / inventory.CANDIDATES[0]).write_bytes(b"synthetic")
        actual_lstat = inventory._lstat
        intermediate = self.root / "Package" / "HD"
        actual = actual_lstat(intermediate)
        calls = 0

        def changed(path):
            nonlocal calls
            if Path(path) == intermediate:
                calls += 1
                if calls >= 2:
                    return SimpleNamespace(st_mode=stat.S_IFDIR, st_dev=actual.st_dev, st_ino=actual.st_ino + 1)
            return actual_lstat(path)

        with patch.object(inventory, "_lstat", side_effect=changed):
            report = layout.inspect_layout(self.root)
        self.assertEqual(report["result"], "incomplete")
        self.assertEqual(report["layers"][0]["directory_state"], "changed_or_inaccessible")
        self.assertEqual(report["layers"][0]["candidates"], [])
        self.assertEqual(report["layers"][1]["candidate_result"], "no_candidates")

    def test_changed_root_discards_both_groups(self):
        (self.package / inventory.CANDIDATES[0]).write_bytes(b"synthetic")
        actual_lstat = inventory._lstat
        actual = actual_lstat(self.root)
        calls = 0
        def changed(path):
            nonlocal calls
            if Path(path) == self.root:
                calls += 1
                if calls >= 2:
                    return SimpleNamespace(st_mode=stat.S_IFDIR, st_dev=actual.st_dev, st_ino=actual.st_ino + 1)
            return actual_lstat(path)
        with patch.object(inventory, "_lstat", side_effect=changed):
            report = layout.inspect_layout(self.root)
        self.assertEqual(report["root_state"], "changed_or_inaccessible")
        self.assertEqual(report["result"], "incomplete")
        self.assertTrue(all(layer["directory_state"] == "changed_or_inaccessible" for layer in report["layers"]))
        self.assertTrue(all(not layer["candidates"] for layer in report["layers"]))

    def test_inaccessible_or_linked_root_and_parent_are_rejected(self):
        with self.assertRaises(inventory.InventoryError) as caught:
            layout.inspect_layout(self.root / "SECRET-MISSING")
        self.assertNotIn("SECRET-MISSING", str(caught.exception))
        actual_lstat = inventory._lstat
        for target in (self.root, self.root.parent):
            def linked(path):
                if Path(path) == target:
                    return SimpleNamespace(st_mode=stat.S_IFLNK)
                return actual_lstat(path)
            with self.subTest(parent=target == self.root.parent), patch.object(inventory, "_lstat", side_effect=linked):
                with self.assertRaises(inventory.InventoryError):
                    layout.inspect_layout(self.root)

    def test_candidate_link_and_unknown_are_propagated_without_files_read(self):
        actual_lstat = inventory._lstat
        candidate = self.patch / inventory.CANDIDATES[0]
        def linked(path):
            if Path(path) == candidate:
                return SimpleNamespace(st_mode=stat.S_IFLNK)
            return actual_lstat(path)
        with patch.object(inventory, "_lstat", side_effect=linked):
            report = layout.inspect_layout(self.root)
        self.assertEqual(report["result"], "incomplete")
        self.assertEqual(report["layers"][1]["candidate_result"], "incomplete")
        self.assertEqual(report["layers"][1]["candidates"][0]["state"], "link_skipped")

    def test_inaccessible_candidate_keeps_other_results_but_marks_report_incomplete(self):
        (self.package / inventory.CANDIDATES[0]).write_bytes(b"synthetic")
        inaccessible = self.patch / inventory.CANDIDATES[1]
        actual_lstat = inventory._lstat

        def denied(path):
            if Path(path) == inaccessible:
                raise PermissionError("SECRET-FILESYSTEM-DETAIL")
            return actual_lstat(path)

        with patch.object(inventory, "_lstat", side_effect=denied):
            report = layout.inspect_layout(self.root)
        self.assertEqual(report["result"], "incomplete")
        self.assertEqual(report["layers"][0]["candidate_result"], "candidates_found")
        self.assertEqual(report["layers"][1]["candidate_result"], "incomplete")
        self.assertEqual(report["layers"][1]["candidates"][1]["state"], "inaccessible")
        self.assertNotIn("SECRET-FILESYSTEM-DETAIL", json.dumps(report))

    def test_report_is_deterministic_and_does_not_mutate_disk(self):
        (self.package / inventory.CANDIDATES[0]).write_bytes(b"synthetic")
        before = {path.relative_to(self.root).as_posix(): path.read_bytes()
                  for path in self.root.rglob("*") if path.is_file()}
        first = layout.inspect_layout(self.root)
        second = layout.inspect_layout(self.root)
        after = {path.relative_to(self.root).as_posix(): path.read_bytes()
                 for path in self.root.rglob("*") if path.is_file()}
        self.assertEqual(first, second)
        self.assertEqual(before, after)


class SteamLayoutCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="private-cli-root-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "game"
        self.root.mkdir()
        for _, components in layout.LAYERS:
            self.root.joinpath(*components).mkdir(parents=True)

    def run_cli(self, *args):
        return subprocess.run([sys.executable, "-B", str(SCRIPT), *map(str, args)],
                              capture_output=True, text=True, encoding="utf-8", check=False)

    def test_cli_prints_redacted_json_and_no_files_written(self):
        target = self.root.joinpath(*layout.LAYERS[0][1]) / inventory.CANDIDATES[0]
        target.write_bytes(b"fake game data")
        before = {path.relative_to(self.root).as_posix(): path.read_bytes()
                  for path in self.root.rglob("*") if path.is_file()}
        result = self.run_cli("--root", self.root)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["result"], "candidates_found")
        self.assertNotIn(str(self.root), result.stdout + result.stderr)
        self.assertNotIn("fake game data", result.stdout + result.stderr)
        self.assertEqual(before, {path.relative_to(self.root).as_posix(): path.read_bytes()
                                  for path in self.root.rglob("*") if path.is_file()})

    def test_cli_incomplete_exit_and_redacted_invalid_arguments(self):
        patch_directory = self.root.joinpath(*layout.LAYERS[1][1])
        patch_directory.rmdir()
        result = self.run_cli("--root", self.root)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(json.loads(result.stdout)["layers"][1]["directory_state"], "missing")
        self.assertNotIn(str(self.root), result.stdout + result.stderr)
        invalid = self.run_cli("--root", self.root / "SECRET-PATH")
        self.assertEqual(invalid.returncode, 2)
        self.assertNotIn("SECRET-PATH", invalid.stdout + invalid.stderr)
        unknown = self.run_cli("--root", self.root, "--SECRET-ARGUMENT")
        self.assertEqual(unknown.returncode, 2)
        self.assertNotIn("SECRET-ARGUMENT", unknown.stdout + unknown.stderr)
        self.assertNotIn(str(self.root), unknown.stdout + unknown.stderr)


if __name__ == "__main__":
    unittest.main()
