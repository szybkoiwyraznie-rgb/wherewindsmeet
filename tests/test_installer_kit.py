"""Tests for the Windows patch installer/backup/restore kit builder."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

from tools import build_installer_kit as kit


class InstallerKitTests(unittest.TestCase):
    def test_reproducible_zip_contains_expected_tools(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = Path(tmp) / "a.zip"
            second = Path(tmp) / "b.zip"
            d1, _, _ = kit.build_zip(first)
            d2, _, _ = kit.build_zip(second)
            self.assertEqual(d1, d2)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            with ZipFile(first) as z:
                self.assertEqual(sorted(z.namelist()), sorted(kit.MEMBERS))

    def test_windows_encoding_and_line_endings_are_preserved(self):
        files = kit.kit_files()
        self.assertTrue(files["instaluj_latke.ps1"].startswith(b"\xef\xbb\xbf"))
        self.assertTrue(files["CZYTAJ_TO.txt"].startswith(b"\xef\xbb\xbf"))
        for bat in ("ZAINSTALUJ.bat", "PRZYWROC.bat", "SPRAWDZ_STAN.bat"):
            self.assertFalse(files[bat].startswith(b"\xef\xbb\xbf"))
            text = files[bat].decode("ascii")
            self.assertIn("-ExecutionPolicy Bypass", text)
            self.assertIn("Unblock-File", text)
            self.assertNotIn("Set-ExecutionPolicy", text)
            self.assertNotIn("\n", text.replace("\r\n", ""))
        self.assertNotIn("\n", files["instaluj_latke.ps1"].decode("utf-8-sig").replace("\r\n", ""))

    def test_readme_states_backup_location_and_no_guarantee(self):
        readme = kit.kit_files()["CZYTAJ_TO.txt"].decode("utf-8-sig")
        self.assertIn("WhereWindsMeetPL", readme)
        self.assertIn("nie została jeszcze przetestowana w uruchomionej grze", readme)
        self.assertIn("nie zmieniają ustawień systemu", readme.lower())

    def test_bundles_patch_files_and_rejects_corrupted_or_unsafe_manifests(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            latka = root / "latka"
            p1 = latka / "pliki/Package/HD/oversea/locale/translate_words_map_en"
            p2 = latka / "pliki/LocalData/Patch/HD/oversea/locale/translate_words_map_en_diff"
            p1.parent.mkdir(parents=True)
            p2.parent.mkdir(parents=True)
            b1 = b"patched en"
            b2 = b"patched diff"
            p1.write_bytes(b1)
            p2.write_bytes(b2)
            manifest = {
                "format": "wwm-latka-v1",
                "build_gry": "25906190",
                "pliki": [
                    {
                        "plik": "translate_words_map_en",
                        "plik_latki": "pliki/Package/HD/oversea/locale/translate_words_map_en",
                        "sciezka_w_grze": "Package/HD/oversea/locale/translate_words_map_en",
                        "bajtow_po": len(b1),
                        "sha256_przed": "a" * 64,
                        "sha256_po": hashlib.sha256(b1).hexdigest(),
                    },
                    {
                        "plik": "translate_words_map_en_diff",
                        "plik_latki": "pliki/LocalData/Patch/HD/oversea/locale/translate_words_map_en_diff",
                        "sciezka_w_grze": "LocalData/Patch/HD/oversea/locale/translate_words_map_en_diff",
                        "bajtow_po": len(b2),
                        "sha256_przed": "b" * 64,
                        "sha256_po": hashlib.sha256(b2).hexdigest(),
                    },
                ],
            }
            (latka / "latka.json").write_text(json.dumps(manifest), encoding="utf-8")
            out = root / "WWM_LATKA_PL.zip"
            _, _, files = kit.build_zip(out, latka_dir=latka)
            self.assertIn("latka.json", files)
            self.assertIn("pliki/Package/HD/oversea/locale/translate_words_map_en", files)
            self.assertIn("pliki/LocalData/Patch/HD/oversea/locale/translate_words_map_en_diff", files)

            # Corrupt payload -> refused
            p1.write_bytes(b"corrupted")
            with self.assertRaises(ValueError):
                kit.build_zip(out, latka_dir=latka)
            p1.write_bytes(b1)

            # Unsafe target path -> refused
            manifest["pliki"][0]["sciezka_w_grze"] = "../evil.exe"
            (latka / "latka.json").write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaises(ValueError):
                kit.build_zip(out, latka_dir=latka)


if __name__ == "__main__":
    unittest.main()
