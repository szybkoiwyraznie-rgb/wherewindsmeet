from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tools import scan_file_changes as scan
from tools import translation_bundle as bundles


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "tools" / "scan_file_changes.py"


class StatProxy:
    """Override just the simulated metadata we need on every test platform."""

    def __init__(self, original, **overrides):
        self.original = original
        self.overrides = overrides

    def __getattr__(self, name):
        if name in self.overrides:
            return self.overrides[name]
        return getattr(self.original, name)


class EntryProxy:
    def __init__(self, original, **stat_overrides):
        self.original = original
        self.name = original.name
        self.path = original.path
        self.stat_overrides = stat_overrides

    def stat(self, *, follow_symlinks=True):
        return StatProxy(self.original.stat(follow_symlinks=follow_symlinks), **self.stat_overrides)


class ScandirProxy:
    def __init__(self, actual, name, overrides):
        self.actual = actual
        self.name = name
        self.overrides = overrides

    def __enter__(self):
        iterator = self.actual.__enter__()
        return (EntryProxy(entry, **self.overrides) if entry.name == self.name else entry for entry in iterator)

    def __exit__(self, *args):
        return self.actual.__exit__(*args)


class ReadOnlyScannerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="synthetic-inventory-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "invented-game"
        self.root.mkdir()
        (self.root / "Package").mkdir()
        (self.root / "Package" / "first.bin").write_bytes(b"First invented binary contents.")
        (self.root / "Package" / "unchanged.bin").write_bytes(b"Same invented contents.")
        (self.root / "empty.txt").write_bytes(b"")
        (self.root / "tekst-zażółć.txt").write_bytes("wymyślony".encode("utf-8"))

    def scan_with_diagnostics(self):
        original = scan._same_observation
        mismatches = []
        def traced(first, second):
            matches = original(first, second)
            if not matches:
                fields = ("st_mode", "st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns", "st_file_attributes")
                mismatches.append([(field, getattr(first, field, None), getattr(second, field, None))
                                   for field in fields if getattr(first, field, None) != getattr(second, field, None)])
            return matches
        with patch.object(scan, "_same_observation", side_effect=traced):
            manifest = scan.scan_tree(self.root)
        self.assertEqual(manifest["scan_status"], "complete", f"issues={manifest['issues']!r} differences={mismatches[:2]!r}")
        return manifest

    def test_file_identity_across_fresh_path_and_open_handle(self):
        target = self.root / "empty.txt"
        path_info = os.lstat(target)
        fd = os.open(target, os.O_RDONLY | getattr(os, "O_BINARY", 0))
        try:
            handle_info = os.fstat(fd)
        finally:
            os.close(fd)
        self.assertTrue(scan._same_identity_across_sources(path_info, handle_info))
        # Cross-API ctime/mtime can differ on Windows without any content change.
        different_timestamps = StatProxy(handle_info, st_ctime_ns=handle_info.st_ctime_ns + 1,
                                          st_mtime_ns=handle_info.st_mtime_ns + 1)
        self.assertTrue(scan._same_identity_across_sources(path_info, different_timestamps))
        self.assertFalse(scan._same_observation(handle_info, different_timestamps))
        first = StatProxy(path_info, st_dev=10, st_ino=20)
        other = StatProxy(handle_info, st_dev=10, st_ino=21)
        self.assertFalse(scan._same_identity_across_sources(first, other))
        self.assertFalse(scan._same_identity_across_sources(path_info, StatProxy(handle_info, st_size=1)))

    def test_stale_cached_directory_entry_does_not_replace_fresh_lstat(self):
        actual_scandir = os.scandir
        def stale(path):
            entry_name = "first.bin" if Path(path).name == "Package" else "Package"
            return ScandirProxy(actual_scandir(path), entry_name, {
                "st_mtime_ns": 0, "st_ctime_ns": 0, "st_dev": 0, "st_ino": 0,
            })
        with patch.object(scan.os, "scandir", side_effect=stale):
            manifest = scan.scan_tree(self.root)
        self.assertEqual(manifest["scan_status"], "complete", repr(manifest["issues"]))
        self.assertEqual(len(manifest["files"]), 4)

    def test_cross_api_timestamp_difference_does_not_mask_same_source_changes(self):
        target = self.root / "Package" / "first.bin"
        initial = os.lstat(target)
        actual_fstat = os.fstat
        def handle_timestamps(fd):
            value = actual_fstat(fd)
            return StatProxy(value, st_mtime_ns=value.st_mtime_ns + 5, st_ctime_ns=value.st_ctime_ns + 5)
        with patch.object(scan.os, "fstat", side_effect=handle_timestamps):
            digest, checked, problem = scan._hash_regular_file(target, initial)
        self.assertIsNone(problem)
        self.assertEqual(digest, hashlib.sha256(target.read_bytes()).hexdigest())
        self.assertEqual(checked.st_mtime_ns, initial.st_mtime_ns)
        calls = 0
        def changing_handle(fd):
            nonlocal calls
            value = actual_fstat(fd)
            calls += 1
            return StatProxy(value, st_ctime_ns=value.st_ctime_ns + calls)
        with patch.object(scan.os, "fstat", side_effect=changing_handle):
            digest, checked, problem = scan._hash_regular_file(target, initial)
        self.assertEqual((digest, checked, problem), (None, None, "file_changed"))

    def test_scans_every_regular_file_and_hashes_contents(self):
        first = scan.scan_tree(self.root)
        second = scan.scan_tree(self.root)
        self.assertEqual(first, second)
        self.assertEqual(first["scan_status"], "complete")
        self.assertFalse(first["atomic_snapshot_verified"])
        self.assertFalse(first["file_origin_verified"])
        self.assertEqual(first["issues"], [])
        files = {item["path"]: item for item in first["files"]}
        self.assertEqual(set(files), {"Package/first.bin", "Package/unchanged.bin", "empty.txt", "tekst-zażółć.txt"})
        for relative, item in files.items():
            content = self.root.joinpath(*relative.split("/")).read_bytes()
            self.assertEqual(item["size"], len(content))
            self.assertEqual(item["sha256"], hashlib.sha256(content).hexdigest())
        report, changes = scan.make_report(first)
        self.assertEqual(report["comparison"], {"status": "no_baseline", "counts": None})
        self.assertEqual(changes, [])
        self.assertFalse(report["writes_performed"])
        self.assertFalse(report["game_or_launcher_state_verified"])
        self.assertFalse(report["baseline_authenticated"])

    def test_compares_changed_unchanged_added_removed_not_whole_dialogues(self):
        previous = self.scan_with_diagnostics()
        (self.root / "Package" / "first.bin").write_bytes(b"New invented bytes!")
        (self.root / "empty.txt").unlink()
        (self.root / "Package" / "added.bin").write_bytes(b"Added invented bytes.")
        current = self.scan_with_diagnostics()
        summary, changes = scan.compare_manifests(current, previous)
        self.assertEqual(summary, {"status": "compared", "counts": {
            "unchanged": 2, "changed": 1, "added": 1, "removed": 1,
        }})
        self.assertEqual(changes, [
            {"path": "Package/added.bin", "change": "added"},
            {"path": "Package/first.bin", "change": "changed"},
            {"path": "empty.txt", "change": "removed"},
        ])

    def test_same_size_and_timestamp_do_not_hide_changed_bytes(self):
        target = self.root / "Package" / "first.bin"
        previous = self.scan_with_diagnostics()
        old = target.stat()
        target.write_bytes(b"z" * old.st_size)
        os.utime(target, ns=(old.st_atime_ns, old.st_mtime_ns))
        current = self.scan_with_diagnostics()
        report, changes = scan.make_report(current, previous)
        self.assertEqual(report["comparison"]["counts"]["changed"], 1)
        self.assertIn({"path": "Package/first.bin", "change": "changed"}, changes)

    def test_hashes_in_chunks_without_writing_or_network(self):
        target = self.root / "Package" / "big.bin"
        content = b"abc123" * 10000
        target.write_bytes(content)
        previous_bytes = target.read_bytes()
        actual_open, actual_read = os.open, os.read
        actual_compare = scan._same_observation
        sizes, mismatches = [], []
        def checked_open(path, flags, *args, **kwargs):
            self.assertFalse(flags & (os.O_WRONLY | os.O_RDWR))
            return actual_open(path, flags, *args, **kwargs)
        def counted_read(fd, size):
            sizes.append(size)
            return actual_read(fd, size)
        def traced_compare(first, second):
            matches = actual_compare(first, second)
            if not matches:
                fields = ("st_mode", "st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns", "st_file_attributes")
                mismatches.append([(field, getattr(first, field, None), getattr(second, field, None))
                                   for field in fields if getattr(first, field, None) != getattr(second, field, None)])
            return matches
        with patch.object(scan, "CHUNK_BYTES", 4096), patch.object(scan.os, "open", side_effect=checked_open), \
             patch.object(scan.os, "read", side_effect=counted_read), \
             patch.object(scan, "_same_observation", side_effect=traced_compare), \
             patch("socket.socket", side_effect=AssertionError("unexpected network")):
            manifest = scan.scan_tree(self.root)
        self.assertEqual(manifest["scan_status"], "complete", f"issues={manifest['issues']!r} differences={mismatches!r}")
        result = next(item for item in manifest["files"] if item["path"] == "Package/big.bin")
        self.assertEqual(result["sha256"], hashlib.sha256(content).hexdigest())
        self.assertTrue(all(size == 4096 for size in sizes))
        self.assertGreater(len(sizes), 10)
        self.assertEqual(target.read_bytes(), previous_bytes)

    def test_empty_directory_establishes_a_baseline_without_a_delta(self):
        empty = self.base / "empty-dir"
        empty.mkdir()
        first = scan.scan_tree(empty)
        self.assertEqual(first["files"], [])
        self.assertEqual(first["scan_status"], "complete")
        self.assertEqual(scan.compare_manifests(first)[0]["status"], "no_baseline")
        self.assertEqual(scan.compare_manifests(first, first)[0]["counts"], {
            "unchanged": 0, "changed": 0, "added": 0, "removed": 0,
        })

    def test_different_root_blocks_comparison_even_with_same_contents(self):
        other = self.base / "other"
        other.mkdir()
        one, two = scan.scan_tree(self.root), scan.scan_tree(other)
        comparison, changes = scan.compare_manifests(two, one)
        self.assertEqual(comparison, {"status": "blocked_scope_mismatch", "counts": None})
        self.assertEqual(changes, [])

    def test_reparse_entry_is_not_opened_and_scan_is_incomplete(self):
        previous = scan.scan_tree(self.root)
        name = "tekst-zażółć.txt"
        actual_scandir = os.scandir
        def marked(path):
            iterator = actual_scandir(path)
            return ScandirProxy(iterator, name, {"st_file_attributes": scan.REPARSE_POINT})
        with patch.object(scan.os, "scandir", side_effect=marked):
            current = scan.scan_tree(self.root)
        self.assertEqual(current["scan_status"], "incomplete")
        self.assertIn({"path": name, "reason": "link_or_reparse_skipped"}, current["issues"])
        self.assertNotIn(name, {item["path"] for item in current["files"]})
        for first, second in ((current, previous), (previous, current)):
            report, changes = scan.make_report(first, second)
            self.assertEqual(report["comparison"], {"status": "blocked_incomplete_scan", "counts": None})
            self.assertEqual(changes, [])

    def test_symlink_mode_and_other_special_entries_are_not_read(self):
        target = "empty.txt"
        actual_scandir = os.scandir
        for mode, reason in ((stat.S_IFLNK, "link_or_reparse_skipped"),
                             (stat.S_IFIFO, "unsupported_entry")):
            with self.subTest(mode=mode):
                def marked(path):
                    return ScandirProxy(actual_scandir(path), target, {"st_mode": mode | 0o600})
                with patch.object(scan.os, "scandir", side_effect=marked):
                    result = scan.scan_tree(self.root)
                self.assertEqual(result["scan_status"], "incomplete")
                self.assertIn({"path": target, "reason": reason}, result["issues"])
                self.assertNotIn(target, {item["path"] for item in result["files"]})

    def test_entry_type_changed_between_enumeration_and_lstat_blocks_comparison(self):
        previous = scan.scan_tree(self.root)
        actual_scandir = os.scandir
        def mismatched_type(path):
            return ScandirProxy(actual_scandir(path), "empty.txt", {"st_mode": stat.S_IFDIR | 0o700})
        with patch.object(scan.os, "scandir", side_effect=mismatched_type):
            current = scan.scan_tree(self.root)
        self.assertIn({"path": "empty.txt", "reason": "entry_changed"}, current["issues"])
        self.assertEqual(scan.compare_manifests(current, previous)[0]["status"], "blocked_incomplete_scan")

    def test_actual_link_when_supported_is_not_traversed(self):
        outside = self.base / "outside"
        outside.mkdir()
        (outside / "outside-secret.bin").write_bytes(b"invented external content")
        link = self.root / "external-link"
        try:
            os.symlink(outside, link, target_is_directory=True)
        except (OSError, NotImplementedError):
            # Windows runners may not have symlink privileges. Model the same
            # entry without skipping a test; real reparse behavior still needs
            # a Windows integration test on a machine with suitable rights.
            link.write_bytes(b"placeholder")
            actual_scandir = os.scandir
            def marked(path):
                return ScandirProxy(actual_scandir(path), link.name, {"st_mode": stat.S_IFLNK | 0o600})
            with patch.object(scan.os, "scandir", side_effect=marked):
                manifest = scan.scan_tree(self.root)
        else:
            manifest = scan.scan_tree(self.root)
        self.assertEqual(manifest["scan_status"], "incomplete")
        self.assertIn({"path": "external-link", "reason": "link_or_reparse_skipped"}, manifest["issues"])
        self.assertNotIn("outside-secret", json.dumps(manifest))
        self.assertTrue(all(not item["path"].startswith("external-link/") for item in manifest["files"]))

    def test_unreadable_directory_and_file_fail_closed_without_error_paths(self):
        previous = scan.scan_tree(self.root)
        with patch.object(scan.os, "scandir", side_effect=PermissionError("secret directory path")):
            unreadable = scan.scan_tree(self.root)
        self.assertEqual(unreadable["scan_status"], "incomplete")
        report, changes = scan.make_report(unreadable, previous)
        self.assertEqual(report["issue_counts"], {"directory_unavailable": 1})
        self.assertEqual(report["comparison"]["status"], "blocked_incomplete_scan")
        self.assertEqual(changes, [])
        self.assertNotIn("secret directory path", json.dumps(report))
        with patch.object(scan.os, "open", side_effect=PermissionError("private path")):
            unreadable_files = scan.scan_tree(self.root)
        report, _ = scan.make_report(unreadable_files, previous)
        self.assertEqual(report["issue_counts"]["file_unavailable"], 4)
        self.assertEqual(report["comparison"]["status"], "blocked_incomplete_scan")
        self.assertNotIn("private path", json.dumps(report))

    def test_file_changed_during_read_is_not_reported_as_a_removed_file(self):
        previous = scan.scan_tree(self.root)
        actual_fstat = os.fstat
        calls = 0
        def changed(fd):
            nonlocal calls
            calls += 1
            result = actual_fstat(fd)
            return StatProxy(result, st_size=result.st_size + 1) if calls == 2 else result
        with patch.object(scan.os, "fstat", side_effect=changed):
            current = scan.scan_tree(self.root)
        report, changes = scan.make_report(current, previous)
        self.assertEqual(report["scan_status"], "incomplete")
        self.assertGreaterEqual(report["issue_counts"].get("file_changed", 0), 1)
        self.assertEqual(report["comparison"]["status"], "blocked_incomplete_scan")
        self.assertIsNone(report["comparison"]["counts"])
        self.assertEqual(changes, [])

    def test_recheck_detects_file_changed_after_its_hash(self):
        previous = scan.scan_tree(self.root)
        target = self.root / "empty.txt"
        actual_lstat = os.lstat
        calls = 0
        def changed(path, *args, **kwargs):
            nonlocal calls
            result = actual_lstat(path, *args, **kwargs)
            if Path(path) == target:
                calls += 1
                # fresh entry observation, post-open path, post-read path,
                # then the final path recheck
                if calls >= 4:
                    return StatProxy(result, st_mtime_ns=result.st_mtime_ns + 1000000000)
            return result
        with patch.object(scan.os, "lstat", side_effect=changed):
            current = scan.scan_tree(self.root)
        self.assertIn({"path": "empty.txt", "reason": "file_changed"}, current["issues"])
        self.assertNotIn("empty.txt", {item["path"] for item in current["files"]})
        self.assertEqual(scan.compare_manifests(current, previous)[0]["status"], "blocked_incomplete_scan")

    def test_recheck_detects_directory_changed_during_scan(self):
        previous = scan.scan_tree(self.root)
        actual_lstat = os.lstat
        calls = 0
        def changed(path, *args, **kwargs):
            nonlocal calls
            result = actual_lstat(path, *args, **kwargs)
            if Path(path) == self.root:
                calls += 1
                # root validation, processing and final recheck
                if calls >= 3:
                    return StatProxy(result, st_mtime_ns=result.st_mtime_ns + 1000000000)
            return result
        with patch.object(scan.os, "lstat", side_effect=changed):
            current = scan.scan_tree(self.root)
        self.assertIn({"path": "", "reason": "directory_changed"}, current["issues"])
        self.assertEqual(scan.compare_manifests(current, previous)[0]["status"], "blocked_incomplete_scan")

    def test_node_ceiling_is_incomplete_not_a_partial_comparison(self):
        previous = scan.scan_tree(self.root)
        with patch.object(scan, "MAX_NODES", 1):
            current = scan.scan_tree(self.root)
        self.assertEqual(current["scan_status"], "incomplete")
        self.assertTrue(any(item["reason"] == "node_limit_exceeded" for item in current["issues"]))
        summary, changes = scan.compare_manifests(current, previous)
        self.assertEqual(summary["status"], "blocked_incomplete_scan")
        self.assertEqual(changes, [])

    def test_root_and_manifest_validation_fail_without_echoing_private_data(self):
        with self.assertRaises(bundles.BundleError) as caught:
            scan.scan_tree(self.base / "not-present-secret")
        self.assertNotIn("not-present-secret", str(caught.exception))
        with self.assertRaises(bundles.BundleError):
            scan.scan_tree(self.root / "empty.txt")
        manifest = scan.scan_tree(self.root)
        for mutation in ("duplicate", "absolute", "traversal", "windows-drive", "windows-traversal",
                         "bad-hash", "bad-size", "bad-status", "claim"):
            broken = deepcopy(manifest)
            if mutation == "duplicate":
                broken["files"].append(deepcopy(broken["files"][0]))
            elif mutation == "absolute":
                broken["files"][0]["path"] = "/private/secret"
            elif mutation == "traversal":
                broken["files"][0]["path"] = "../private/secret"
            elif mutation == "windows-drive":
                broken["files"][0]["path"] = "C:/private/secret"
            elif mutation == "windows-traversal":
                broken["files"][0]["path"] = "..\\private\\secret"
            elif mutation == "bad-hash":
                broken["files"][0]["sha256"] = "SECRET"
            elif mutation == "bad-size":
                broken["files"][0]["size"] = True
            elif mutation == "bad-status":
                broken["scan_status"] = "incomplete"
            else:
                broken["atomic_snapshot_verified"] = True
            with self.subTest(mutation=mutation):
                with self.assertRaises(bundles.BundleError) as caught:
                    scan.compare_manifests(manifest, broken)
                self.assertNotIn("SECRET", str(caught.exception))
                self.assertNotIn("private", str(caught.exception))

    def test_root_link_or_reparse_point_is_rejected(self):
        actual_lstat = os.lstat
        def reparse_root(path, *args, **kwargs):
            result = actual_lstat(path, *args, **kwargs)
            if Path(path) == self.root:
                return StatProxy(result, st_file_attributes=scan.REPARSE_POINT)
            return result
        with patch.object(scan.os, "lstat", side_effect=reparse_root):
            with self.assertRaises(bundles.BundleError):
                scan.scan_tree(self.root)


class ScannerCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="synthetic-inventory-cli-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "private-example-root"
        self.root.mkdir()
        (self.root / "secret-name.txt").write_bytes(b"invented private contents")
        (self.root / "stable.txt").write_bytes(b"invented unchanged")

    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)],
                              capture_output=True, text=True, encoding="utf-8", check=False)

    def test_first_scan_then_private_baseline_and_change_report(self):
        original = self.run_cli("--root", self.root, "--mode", "private")
        self.assertEqual(original.returncode, 0, original.stderr)
        first = json.loads(original.stdout)
        self.assertEqual(first["report"]["comparison"]["status"], "no_baseline")
        self.assertEqual(first["changes"], [])
        baseline = self.base / "baseline.json"
        baseline.write_text(original.stdout, encoding="utf-8")
        (self.root / "secret-name.txt").write_bytes(b"changed private contents")
        (self.root / "added.txt").write_bytes(b"added")
        result = self.run_cli("--root", self.root, "--previous", baseline)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["comparison"]["counts"], {
            "unchanged": 1, "changed": 1, "added": 1, "removed": 0,
        })
        for sensitive in (str(self.root), str(baseline), "secret-name.txt", "private contents", '"sha256":'):
            self.assertNotIn(sensitive, result.stdout + result.stderr)
        detailed = self.run_cli("--root", self.root, "--previous", baseline, "--mode", "private")
        self.assertEqual(detailed.returncode, 0, detailed.stderr)
        private = json.loads(detailed.stdout)
        self.assertEqual(private["changes"], [{"path": "added.txt", "change": "added"},
                                              {"path": "secret-name.txt", "change": "changed"}])
        self.assertIn("sha256", detailed.stdout)
        self.assertNotIn(str(self.root), detailed.stdout + detailed.stderr)
        self.assertEqual(baseline.read_text(encoding="utf-8"), original.stdout)
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), ["added.txt", "secret-name.txt", "stable.txt"])

    def test_baseline_inside_root_is_refused_and_arguments_are_redacted(self):
        baseline = self.root / "baseline-secret.json"
        baseline.write_text("{}", encoding="utf-8")
        result = self.run_cli("--root", self.root, "--previous", baseline)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertNotIn(str(self.root), result.stderr)
        self.assertNotIn("baseline-secret", result.stderr)
        self.assertIn("outside", result.stderr)
        missing = self.run_cli("--root", self.root, "--mode", "PRIVATE-SECRET")
        self.assertEqual(missing.returncode, 2)
        self.assertNotIn("PRIVATE-SECRET", missing.stderr)
        self.assertNotIn(str(self.root), missing.stderr)

    def test_wrong_scope_and_invalid_previous_data_fail_without_partial_delta(self):
        baseline_result = self.run_cli("--root", self.root, "--mode", "private")
        baseline = self.base / "baseline.json"
        baseline.write_text(baseline_result.stdout, encoding="utf-8")
        other = self.base / "other"
        other.mkdir()
        mismatch = self.run_cli("--root", other, "--previous", baseline, "--mode", "private")
        self.assertEqual(mismatch.returncode, 2, mismatch.stderr)
        result = json.loads(mismatch.stdout)
        self.assertEqual(result["report"]["comparison"]["status"], "blocked_scope_mismatch")
        self.assertIsNone(result["report"]["comparison"]["counts"])
        self.assertEqual(result["changes"], [])
        baseline.write_text('{"SECRET":"a","SECRET":"b"}', encoding="utf-8")
        invalid = self.run_cli("--root", self.root, "--previous", baseline)
        self.assertEqual(invalid.returncode, 1)
        self.assertEqual(invalid.stdout, "")
        self.assertNotIn("SECRET", invalid.stderr)
        self.assertNotIn(str(self.base), invalid.stderr)

    def test_output_size_limit_fails_without_partial_output(self):
        out, err = io.StringIO(), io.StringIO()
        with patch.object(scan, "MAX_DOCUMENT_BYTES", 100), redirect_stdout(out), redirect_stderr(err):
            result = scan.main(["--root", str(self.root), "--mode", "private"])
        self.assertEqual(result, 1)
        self.assertEqual(out.getvalue(), "")
        self.assertIn("too large", err.getvalue())
        self.assertNotIn(str(self.root), err.getvalue())


if __name__ == "__main__":
    unittest.main()
