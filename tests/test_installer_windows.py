"""Windows-only execution tests for the unzipped installer/backup/restore kit against synthetic game files."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from tools import build_installer_kit as kit


if os.name == "nt":
    def sha256(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    class WindowsInstallerTests(unittest.TestCase):
        def setUp(self):
            self.temp = tempfile.TemporaryDirectory()
            self.addCleanup(self.temp.cleanup)
            self.root = Path(self.temp.name)
            self.steam = self.root / "Steam [główny]"
            self.game = self.steam / "steamapps/common/Where Winds Meet"
            self.backup = self.root / "Kopia [bezpieczna] żółć"
            self.kit = self.root / "Rozpakowana łatka [test] żółć"
            self.ps = Path(os.environ["SystemRoot"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"

            (self.steam / "steamapps").mkdir(parents=True)
            (self.steam / "steamapps/appmanifest_3564740.acf").write_text(
                '"AppState"\n{\n"installdir" "Where Winds Meet"\n"buildid" "25906190"\n}\n',
                encoding="utf-8",
            )
            self.orig_files = {
                "Package/HD/oversea/locale/translate_words_map_en": b"ORIGINAL EN BASE",
                "Package/HD/oversea/locale/translate_words_map_en_diff": b"ORIGINAL PKG EN DIFF",
                "LocalData/Patch/HD/oversea/locale/translate_words_map_en_diff": b"ORIGINAL PATCH EN DIFF",
            }
            for rel, data in self.orig_files.items():
                p = self.game / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(data)

        def build_and_unpack_patch(self, patches: dict[str, bytes], *, build_id: str = "25906190",
                                   orig_override: dict[str, bytes] | None = None):
            if self.kit.exists():
                shutil.rmtree(self.kit)
            stage = self.root / "latka_src"
            if stage.exists():
                shutil.rmtree(stage)
            stage.mkdir()
            entries = []
            for rel, patched_bytes in patches.items():
                orig_bytes = (orig_override or self.orig_files)[rel]
                patch_rel = f"pliki/{rel}"
                dst = stage / patch_rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(patched_bytes)
                entries.append({
                    "plik": Path(rel).name,
                    "plik_latki": patch_rel,
                    "sciezka_w_grze": rel,
                    "bajtow_przed": len(orig_bytes),
                    "bajtow_po": len(patched_bytes),
                    "sha256_przed": sha256(orig_bytes),
                    "sha256_po": sha256(patched_bytes),
                })
            manifest = {"format": "wwm-latka-v1", "build_gry": build_id, "pliki": entries}
            (stage / "latka.json").write_text(json.dumps(manifest), encoding="utf-8")
            zip_path = self.root / "latka.zip"
            kit.build_zip(zip_path, latka_dir=stage)
            with ZipFile(zip_path) as z:
                z.extractall(self.kit)

        def run_bat(self, bat_name: str, *extra: str) -> subprocess.CompletedProcess:
            bat = self.kit / bat_name
            args = " ".join(f'"{a}"' if " " in a else a for a in extra)
            command = f'"{bat}" "{self.game}" {args}'
            return subprocess.run(command, shell=True, input=b"\r\n", stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT, timeout=180, check=False)

        def run_ps(self, *args) -> subprocess.CompletedProcess:
            return subprocess.run(
                [str(self.ps), "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass",
                 "-File", str(self.kit / "instaluj_latke.ps1"), *[str(a) for a in args]],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180, check=False,
            )

        def detail(self, res: subprocess.CompletedProcess) -> str:
            return res.stdout.decode("utf-8", errors="replace")

        def game_bytes(self) -> dict[str, bytes]:
            return {rel: (self.game / rel).read_bytes() for rel in self.orig_files}

        def test_status_install_idempotent_upgrade_and_restore_roundtrip(self):
            v1 = {
                "Package/HD/oversea/locale/translate_words_map_en": b"PATCHED V1 EN",
                "Package/HD/oversea/locale/translate_words_map_en_diff": b"PATCHED V1 PKG DIFF",
                "LocalData/Patch/HD/oversea/locale/translate_words_map_en_diff": b"PATCHED V1 PATCH DIFF",
            }
            self.build_and_unpack_patch(v1)

            # 1. Read-only status before install
            st0 = self.run_bat("SPRAWDZ_STAN.bat", "-BackupDirectory", str(self.backup), "-NonInteractive")
            self.assertEqual(st0.returncode, 0, self.detail(st0))
            self.assertIn("ORYGINAL", self.detail(st0))
            self.assertEqual(self.game_bytes(), self.orig_files)

            # 2. Install via ZAINSTALUJ.bat
            ins1 = self.run_bat("ZAINSTALUJ.bat", "-BackupDirectory", str(self.backup), "-NonInteractive")
            self.assertEqual(ins1.returncode, 0, self.detail(ins1))
            self.assertEqual(self.game_bytes(), v1)
            for rel, orig in self.orig_files.items():
                self.assertEqual((self.backup / "pliki" / rel).read_bytes(), orig)

            # 3. Idempotent re-run does not overwrite original backup
            ins2 = self.run_bat("ZAINSTALUJ.bat", "-BackupDirectory", str(self.backup), "-NonInteractive")
            self.assertEqual(ins2.returncode, 0, self.detail(ins2))
            self.assertIn("Juz aktualne:", self.detail(ins2))
            for rel, orig in self.orig_files.items():
                self.assertEqual((self.backup / "pliki" / rel).read_bytes(), orig)

            # 4. Upgrade v1 -> v2 preserves original backup
            v2 = {
                "Package/HD/oversea/locale/translate_words_map_en": b"PATCHED V2 EN",
                "Package/HD/oversea/locale/translate_words_map_en_diff": b"PATCHED V2 PKG DIFF",
                "LocalData/Patch/HD/oversea/locale/translate_words_map_en_diff": b"PATCHED V2 PATCH DIFF",
            }
            self.build_and_unpack_patch(v2)
            up = self.run_ps("-Akcja", "instaluj", "-GameRoot", self.game,
                             "-BackupDirectory", self.backup, "-NonInteractive")
            self.assertEqual(up.returncode, 0, self.detail(up))
            self.assertEqual(self.game_bytes(), v2)
            for rel, orig in self.orig_files.items():
                self.assertEqual((self.backup / "pliki" / rel).read_bytes(), orig)

            # 5. Status shows installed & backup ok
            st1 = self.run_bat("SPRAWDZ_STAN.bat", "-BackupDirectory", str(self.backup), "-NonInteractive")
            self.assertEqual(st1.returncode, 0, self.detail(st1))
            self.assertIn("ZAINSTALOWANO_LATKE", self.detail(st1))
            self.assertIn("KOPIA_OK", self.detail(st1))

            # 6. Restore via PRZYWROC.bat restores exact original bytes
            res = self.run_bat("PRZYWROC.bat", "-BackupDirectory", str(self.backup), "-NonInteractive")
            self.assertEqual(res.returncode, 0, self.detail(res))
            self.assertEqual(self.game_bytes(), self.orig_files)

        def test_refuses_mismatched_build_and_corrupted_payload_without_writes(self):
            v1 = {rel: b"PATCHED " + data for rel, data in self.orig_files.items()}
            self.build_and_unpack_patch(v1, build_id="99999999")
            r = self.run_bat("ZAINSTALUJ.bat", "-BackupDirectory", str(self.backup), "-NonInteractive")
            self.assertNotEqual(r.returncode, 0, self.detail(r))
            self.assertIn("Niezgodny build Steam", self.detail(r))
            self.assertEqual(self.game_bytes(), self.orig_files)
            self.assertFalse(self.backup.exists())

            # Rebuild with matching build_id, then corrupt one payload file
            self.build_and_unpack_patch(v1, build_id="25906190")
            (self.kit / "pliki/Package/HD/oversea/locale/translate_words_map_en").write_bytes(b"TAMPERED")
            r2 = self.run_bat("ZAINSTALUJ.bat", "-BackupDirectory", str(self.backup), "-NonInteractive")
            self.assertNotEqual(r2.returncode, 0, self.detail(r2))
            self.assertEqual(self.game_bytes(), self.orig_files)

        def test_mid_write_failure_rolls_back_earlier_files_from_backup(self):
            v1 = {rel: b"PATCHED " + data for rel, data in self.orig_files.items()}
            self.build_and_unpack_patch(v1)
            locked = self.game / "LocalData/Patch/HD/oversea/locale/translate_words_map_en_diff"
            os.chmod(locked, stat.S_IREAD)
            self.addCleanup(os.chmod, locked, stat.S_IWRITE | stat.S_IREAD)

            r = self.run_bat("ZAINSTALUJ.bat", "-BackupDirectory", str(self.backup), "-NonInteractive")
            self.assertNotEqual(r.returncode, 0, self.detail(r))
            self.assertIn("Instalacja przerwana i cofnieta", self.detail(r))
            self.assertEqual(self.game_bytes(), self.orig_files)

        def test_restore_refuses_externally_updated_game_file_without_force(self):
            v1 = {rel: b"PATCHED " + data for rel, data in self.orig_files.items()}
            self.build_and_unpack_patch(v1)
            ins = self.run_bat("ZAINSTALUJ.bat", "-BackupDirectory", str(self.backup), "-NonInteractive")
            self.assertEqual(ins.returncode, 0, self.detail(ins))

            steam_updated = self.game / "Package/HD/oversea/locale/translate_words_map_en"
            steam_updated.write_bytes(b"NEW STEAM PATCH BYTES")
            res = self.run_bat("PRZYWROC.bat", "-BackupDirectory", str(self.backup), "-NonInteractive")
            self.assertNotEqual(res.returncode, 0, self.detail(res))
            self.assertEqual(steam_updated.read_bytes(), b"NEW STEAM PATCH BYTES")
            # Untouched second file wasn't partially restored either because preflight caught it first
            self.assertEqual(
                (self.game / "Package/HD/oversea/locale/translate_words_map_en_diff").read_bytes(),
                v1["Package/HD/oversea/locale/translate_words_map_en_diff"],
            )


if __name__ == "__main__":
    unittest.main()
