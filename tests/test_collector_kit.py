from __future__ import annotations

import hashlib
import io
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile, ZIP_STORED

from tools import build_collector_kit as kit


class CollectorKitTests(unittest.TestCase):
    def test_reproducible_zip_contains_only_three_tools_and_readme(self):
        first = kit.build_bytes()
        self.assertEqual(first, kit.build_bytes())
        with ZipFile(io.BytesIO(first)) as archive:
            self.assertEqual(archive.namelist(), list(kit.MEMBERS))
            self.assertIsNone(archive.testzip())
            for info in archive.infolist():
                self.assertEqual(info.compress_type, ZIP_STORED)
                self.assertEqual(info.date_time, kit.STAMP)
                self.assertEqual(archive.read(info), kit.kit_files()[info.filename])

    def test_windows_encoding_and_line_endings_are_preserved(self):
        files = kit.kit_files()
        self.assertTrue(files["zbierz.ps1"].startswith(b"\xef\xbb\xbf"))
        self.assertTrue(files["CZYTAJ_TO.txt"].startswith(b"\xef\xbb\xbf"))
        self.assertFalse(files["URUCHOM.bat"].startswith(b"\xef\xbb\xbf"))
        files["URUCHOM.bat"].decode("ascii")
        for name, data in files.items():
            with self.subTest(name=name):
                self.assertNotIn(b"\n", data.replace(b"\r\n", b""))
                self.assertNotIn(b"\r", data.replace(b"\r\n", b""))
                self.assertTrue(data.endswith(b"\r\n"))

    def test_invalid_script_encodings_are_rejected(self):
        for data, bom, ascii_only in (
            (b"line\n", False, True),
            (b"line\r", False, True),
            (b"line\r\n", True, False),
            (b"\xef\xbb\xbfline\r\n", False, True),
            (b"\xff\r\n", False, True),
            (b"a\rb\r\n", False, True),
        ):
            with self.subTest(data=data), self.assertRaises((ValueError, UnicodeError)):
                kit.windows_lines(data, bom=bom, ascii_only=ascii_only)

    def test_disk_artifact_readback_and_sha256(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "collector.zip"
            result = kit.build(output)
            raw = output.read_bytes()
            self.assertEqual(result["bytes"], len(raw))
            self.assertEqual(result["sha256"], hashlib.sha256(raw).hexdigest())
            self.assertEqual(result["members"], list(kit.MEMBERS))
            self.assertEqual(raw, kit.build_bytes())

    def test_launcher_runs_local_powershell_without_python_or_downloads(self):
        launcher = kit.kit_files()["URUCHOM.bat"].decode("ascii")
        self.assertIn('WindowsPowerShell\\v1.0\\powershell.exe', launcher)
        self.assertIn('-ExecutionPolicy Bypass -File "%~dp0zbierz.ps1" %*', launcher)
        self.assertIn("pause", launcher)
        self.assertNotIn("pip install", launcher.lower())
        self.assertNotIn("python.exe", launcher.lower())


if __name__ == "__main__":
    unittest.main()
