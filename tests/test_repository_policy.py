from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile
import unittest

from tools.check_repository import (
    MAX_FILE_BYTES,
    IndexEntry,
    entry_violations,
    scan_index,
)


ROOT = Path(__file__).resolve().parent.parent


def entry(path: str, *, mode: str = "100644", stage: int = 0) -> IndexEntry:
    return IndexEntry(path=path, mode=mode, oid="synthetic", stage=stage)


class PathPolicyTests(unittest.TestCase):
    def test_private_directories_are_blocked_at_any_depth_case_insensitively(self):
        for path in (
            "local/entries.jsonl",
            "data/LOCAL/source.txt",
            "build/kit.txt",
            "foo/google_drive/report.txt",
            "node_modules/package/readme.md",
        ):
            with self.subTest(path=path):
                self.assertTrue(entry_violations(entry(path), 1))

    def test_game_archives_binaries_and_secrets_are_blocked_even_if_forced(self):
        for path in (
            "game/data.PAK",
            "game/client.exe",
            "game/asset.ucas",
            "game/save.sav",
            "output/result.zip",
            "credentials/private.key",
            ".env",
            "config/.env.local",
        ):
            with self.subTest(path=path):
                self.assertTrue(entry_violations(entry(path), 1))

    def test_text_and_safe_example_names_are_not_blanket_blocked(self):
        for path in (
            "README.md",
            "docs/STATUS.md",
            "data/source.jsonl",
            "translations/pl.json",
            "tests/fixtures/sample.txt",
            ".env.example",
            "config/.env.example",
        ):
            with self.subTest(path=path):
                self.assertEqual(entry_violations(entry(path), 1), [])

    def test_size_limit_is_exact_and_applies_to_index_blob(self):
        self.assertEqual(entry_violations(entry("data/a.jsonl"), MAX_FILE_BYTES), [])
        issues = entry_violations(entry("data/a.jsonl"), MAX_FILE_BYTES + 1)
        self.assertTrue(any("staged blob" in issue for issue in issues))

    def test_unresolved_conflict_and_unreviewed_submodule_are_blocked(self):
        self.assertTrue(entry_violations(entry("notes.md", stage=2), 1))
        self.assertTrue(entry_violations(entry("vendor/source", mode="160000"), None))


class RealIndexTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="wwm-policy-test-")
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.git("init", "--quiet")

    def git(self, *args: str):
        return subprocess.run(
            ["git", *args], cwd=self.repo, check=True, capture_output=True
        )

    def put(self, name: str, content: bytes):
        path = self.repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    def test_large_staged_blob_is_not_hidden_by_smaller_working_tree_file(self):
        self.put("data/sample.txt", b"01234567890")
        self.git("add", "--", "data/sample.txt")
        self.put("data/sample.txt", b"x")
        result = scan_index(self.repo, max_file_bytes=10)
        self.assertEqual(result.entries, 1)
        self.assertTrue(any("staged blob is 11 B" in issue for issue in result.violations))

    def test_unstaged_growth_does_not_change_what_is_in_the_index(self):
        self.put("data/sample.txt", b"x")
        self.git("add", "--", "data/sample.txt")
        self.put("data/sample.txt", b"x" * 20)
        result = scan_index(self.repo, max_file_bytes=10)
        self.assertEqual(result.violations, ())

    def test_force_added_ignored_game_file_is_still_rejected(self):
        self.put(".gitignore", b"local/\n*.pak\n")
        self.put("local/game.pak", b"synthetic fixture, not game data")
        self.git("add", "--", ".gitignore")
        self.git("add", "-f", "--", "local/game.pak")
        result = scan_index(self.repo)
        self.assertTrue(any("local/game.pak" in issue for issue in result.violations))

    def test_unicode_and_spaces_in_tracked_paths_are_supported(self):
        self.put("data/źródło próbne.txt", b"synthetic")
        self.git("add", "--", "data/źródło próbne.txt")
        result = scan_index(self.repo)
        self.assertEqual(result.entries, 1)
        self.assertEqual(result.violations, ())


class RepositoryConfigurationTests(unittest.TestCase):
    def test_gitignore_blocks_typical_private_files_but_allows_text_sources(self):
        ignored = {
            "local/source.jsonl",
            "nested/local/source.txt",
            "google_drive/report.json",
            "build/patch.zip",
            ".env",
            "config/.env.production",
            "game/client.exe",
            "game/data.pak",
            "game/save.sav",
            "game/archive.zip",
            "node_modules/module/index.js",
        }
        allowed = {
            "README.md",
            "data/source.jsonl",
            "translations/pl.jsonl",
            "tests/fixtures/example.txt",
            ".env.example",
            "config/.env.example",
        }
        paths = sorted(ignored | allowed)
        result = subprocess.run(
            ["git", "check-ignore", "--no-index", "-z", "--stdin"],
            cwd=ROOT,
            input=("\0".join(paths) + "\0").encode("utf-8"),
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", "replace"))
        actual = {item.decode("utf-8") for item in result.stdout.split(b"\0") if item}
        self.assertEqual(actual, ignored)

    def test_windows_scripts_are_stored_without_line_ending_conversion(self):
        paths = ["example.bat", "example.cmd", "example.ps1", "README.md"]
        result = subprocess.run(
            ["git", "check-attr", "-z", "text", "eol", "--", *paths],
            cwd=ROOT,
            capture_output=True,
            check=True,
        )
        values = result.stdout.split(b"\0")
        self.assertEqual(values.pop(), b"")
        attrs = {
            (values[i].decode(), values[i + 1].decode()): values[i + 2].decode()
            for i in range(0, len(values), 3)
        }
        for path in paths[:-1]:
            self.assertEqual(attrs[(path, "text")], "unset")
        self.assertEqual(attrs[("README.md", "text")], "auto")
        self.assertEqual(attrs[("README.md", "eol")], "lf")


if __name__ == "__main__":
    unittest.main()
