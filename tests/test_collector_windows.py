"""Run the *built* BAT and PowerShell collector on synthetic Windows trees.

These integration tests are intentionally discovered only on Windows. Linux
runs the platform-independent builder, encoding and intake tests instead.
No game, credentials or external dependencies are used.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from tools.build_collector_kit import build_bytes
from tools.validate_collector_return import validate


if os.name == "nt":
    class WindowsCollectorIntegrationTests(unittest.TestCase):
        def setUp(self):
            self.tmp = tempfile.TemporaryDirectory(prefix="wwm-fixture-")
            self.addCleanup(self.tmp.cleanup)
            self.root = Path(self.tmp.name)
            self.kit = self.root / "Zestaw z polskimi znakami żółć"
            self.kit.mkdir()
            with ZipFile(io.BytesIO(build_bytes())) as archive:
                archive.extractall(self.kit)  # archive is built from our own three known filenames
            self.ps = Path(os.environ["SystemRoot"]) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
            self.game = self.root / "Biblioteka [gry] żółć" / "steamapps" / "common" / "Where Winds Meet"
            self.out = self.root / "Wyniki żółć"
            self.out.mkdir()
            self.write("Package/HD/oversea/locale/translate_words_map_en", b"synthetic base map")
            self.write("LocalData/Patch/HD/oversea/locale/translate_words_map_en", b"synthetic base map")
            self.write("LocalData/Patch/HD/oversea/locale/translate_words_map_en_diff", b"synthetic diff")
            self.write("Package/HD/oversea/locale/translate_words_map_zh_cn", b"synthetic chinese")
            self.write("Package/HD/oversea/MANIFEST", b"synthetic manifest")
            self.write("Package/HD/oversea/data3", b"synthetic context")
            self.write("Package/HD/oversea/index7", b"synthetic index not copied")
            self.write("Package/HD/oversea/not_a_candidate.exe", b"not copied")
            self.write("Package/HD/oversea/Accounts/token.dat", b"fake secret")
            self.write("LocalData/Patch/HD/oversea/Saves/slot.sav", b"fake save")
            self.write("Package/HD/oversea/session.log", b"fake log")
            self.original = self.game_files()

        def write(self, relative: str, data: bytes):
            p = self.game / relative
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)

        def game_files(self):
            return {
                p.relative_to(self.game).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in self.game.rglob("*")
                if p.is_file()
            }

        def run_ps(self, *args: str):
            return subprocess.run(
                [str(self.ps), "-NoLogo", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                 "-File", str(self.kit / "zbierz.ps1"), *map(str, args)],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180, check=False,
            )

        def detail(self, result):
            # Keep the relevant synthetic-fixture diagnostic on one annotation line.
            text = result.stdout.decode("utf-8", errors="replace")
            errors = [line.strip() for line in text.splitlines() if "BLAD:" in line]
            return (errors[0] if errors else repr(text))[:700]

        def collection(self):
            paths = list(self.out.glob("WWM_DANE_*.zip"))
            self.assertEqual(len(paths), 1, paths)
            verified = validate(paths[0])
            self.assertEqual(verified["validation"], "passed")
            with ZipFile(paths[0]) as archive:
                self.assertIsNone(archive.testzip())
                names = archive.namelist()
                report = json.loads(archive.read("RAPORT.json").decode("utf-8-sig"))
                inventory = [json.loads(line) for line in archive.read("INWENTARZ.jsonl").decode("utf-8-sig").splitlines()]
                payload = {name: archive.read(name) for name in names if name.startswith("pliki/") and not name.endswith("/")}
                summary = archive.read("RAPORT.txt").decode("utf-8-sig")
            return report, inventory, payload, summary

        def test_real_windows_powershell_parser(self):
            path = str(self.kit / "zbierz.ps1").replace("'", "''")
            command = ("$tok=$null; $err=$null; "
                       f"$null=[System.Management.Automation.Language.Parser]::ParseFile('{path}',[ref]$tok,[ref]$err); "
                       "if ($err.Count) {$err | ForEach-Object {Write-Host $_}; exit 1}; exit 0")
            result = subprocess.run([str(self.ps), "-NoProfile", "-NonInteractive", "-Command", command],
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60, check=False)
            self.assertEqual(result.returncode, 0, self.detail(result))

        def test_collects_maps_context_and_inventory_without_private_files(self):
            result = self.run_ps("-GameRoot", self.game, "-OutputDirectory", self.out, "-NonInteractive")
            self.assertEqual(result.returncode, 0, self.detail(result))
            report, inventory, payload, summary = self.collection()
            self.assertEqual(report["format"], "wwm-collection-v1")
            self.assertEqual(report["status"], "collected")
            self.assertEqual(report["inventory"]["files"], len(inventory))
            self.assertEqual(len(report["expected"]), 8)
            for row in report["expected"]:
                expected_status = "present" if (self.game / row["path"]).is_file() else "not_found_or_unavailable"
                self.assertEqual(row["status"], expected_status, f"unexpected status for {row['path']}")
            records = report["files"]
            self.assertEqual(len(records), 6)
            self.assertEqual(sum(row["status"] == "duplicate" for row in records), 1)
            self.assertEqual(sum(row["status"] == "copied" for row in records), 5)
            for row in records:
                data = payload[row["stored_as"]]
                self.assertEqual(hashlib.sha256(data).hexdigest(), row["sha256"])
                self.assertEqual(len(data), row["bytes"])
                self.assertEqual(data, (self.game / row["source"]).read_bytes())
            self.assertEqual(report["payload_bytes"], sum(map(len, payload.values())))
            listed = "\n".join(row["path"] for row in inventory).lower()
            self.assertIn("index7", listed)
            for forbidden in ("slot.sav", "token.dat", "session.log", "fake secret", "fake save"):
                self.assertNotIn(forbidden, listed)
                self.assertNotIn(forbidden.encode(), b"".join(payload.values()).lower())
            self.assertNotIn(str(self.game), json.dumps(report, ensure_ascii=False))
            self.assertNotIn(str(self.game), summary)
            self.assertEqual(self.original, self.game_files())
            self.assertFalse(list(self.out.glob(".WWM_ZBIERANIE_*")))
            self.assertFalse(list(self.out.glob("*.tmp")))

        def test_delivered_batch_runs_with_dragged_folder_and_spaces(self):
            bat = self.kit / "URUCHOM.bat"
            command = f'"{bat}" "{self.game}" -OutputDirectory "{self.out}" -NonInteractive'
            result = subprocess.run(command, shell=True, input=b"\r\n", stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, timeout=180, check=False)
            self.assertEqual(result.returncode, 0, self.detail(result))
            report, _, _, _ = self.collection()
            self.assertEqual(report["status"], "collected")
            self.assertEqual(self.original, self.game_files())

        def test_small_budget_reports_skips_and_reuses_identical_map(self):
            n = len(b"synthetic base map")
            result = self.run_ps("-GameRoot", self.game, "-OutputDirectory", self.out,
                                 "-PayloadLimitBytes", str(n), "-ContextLimitBytes", "0", "-NonInteractive")
            self.assertEqual(result.returncode, 2, self.detail(result))
            report, _, payload, _ = self.collection()
            self.assertEqual(report["status"], "partial")
            self.assertEqual(report["payload_bytes"], n)
            self.assertEqual(len(payload), 1)
            maps = [row for row in report["files"] if row["source"].endswith("translate_words_map_en")]
            self.assertCountEqual([row["status"] for row in maps], ["copied", "duplicate"])
            self.assertEqual(maps[0]["stored_as"], maps[1]["stored_as"])
            skipped = [row for row in report["files"] if row["status"] == "skipped_limit"]
            self.assertGreaterEqual(len(skipped), 1)
            self.assertTrue(all(row["reason"] == "payload_or_context_limit" for row in skipped))
            self.assertEqual(self.original, self.game_files())

        def test_steam_library_detection_and_build_id(self):
            steam = self.root / "Steam główny"
            (steam / "steamapps").mkdir(parents=True)
            library = self.game.parent.parent.parent
            escaped = str(library).replace("\\", "\\\\")
            (steam / "steamapps" / "libraryfolders.vdf").write_text(
                f'"libraryfolders"\n{{\n "1"\n {{\n  "path" "{escaped}"\n }}\n}}\n', encoding="utf-8"
            )
            (library / "steamapps" / "appmanifest_3564740.acf").write_text(
                '"AppState"\n{\n"installdir" "Where Winds Meet"\n"buildid" "12345678"\n}\n', encoding="utf-8"
            )
            result = self.run_ps("-SteamRoot", steam, "-OutputDirectory", self.out, "-NonInteractive")
            self.assertEqual(result.returncode, 0, self.detail(result))
            report, _, _, _ = self.collection()
            self.assertEqual(report["steam_app_id"], "3564740")
            self.assertEqual(report["steam_build_id"], "12345678")
            self.assertEqual(self.original, self.game_files())

        def test_default_desktop_destination_without_output_parameter(self):
            command = "[Console]::OutputEncoding=[Text.Encoding]::UTF8; [Console]::Write([Environment]::GetFolderPath('Desktop'))"
            detected = subprocess.run([str(self.ps), "-NoProfile", "-NonInteractive", "-Command", command],
                                      stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60, check=False)
            self.assertEqual(detected.returncode, 0, self.detail(detected))
            desktop_text = detected.stdout.decode("utf-8-sig").strip()
            self.assertTrue(desktop_text)
            desktop = Path(desktop_text)
            if not desktop.exists():
                desktop.mkdir()
                self.addCleanup(desktop.rmdir)
            before = set(desktop.glob("WWM_DANE_*.zip"))
            before_temp = set(desktop.glob(".WWM_ZBIERANIE_*"))
            result = self.run_ps("-GameRoot", self.game, "-NonInteractive")
            created = set(desktop.glob("WWM_DANE_*.zip")) - before
            for path in created:
                self.addCleanup(path.unlink, missing_ok=True)
            self.assertEqual(result.returncode, 0, self.detail(result))
            self.assertEqual(len(created), 1)
            self.assertEqual(validate(created.pop())["collection_status"], "collected")
            self.assertEqual(set(desktop.glob(".WWM_ZBIERANIE_*")), before_temp)
            self.assertEqual(self.original, self.game_files())

        def test_output_directory_with_brackets(self):
            output = self.root / "Wyniki [gry] żółć"
            output.mkdir()
            result = self.run_ps("-GameRoot", self.game, "-OutputDirectory", output, "-NonInteractive")
            self.assertEqual(result.returncode, 0, self.detail(result))
            paths = list(output.glob("WWM_DANE_*.zip"))
            self.assertEqual(len(paths), 1)
            self.assertEqual(validate(paths[0])["collection_status"], "collected")
            self.assertFalse(list(output.glob(".WWM_ZBIERANIE_*")))
            self.assertEqual(self.original, self.game_files())

        def test_repeated_runs_create_new_zip_without_overwriting(self):
            args = ("-GameRoot", self.game, "-OutputDirectory", self.out, "-NonInteractive")
            first_run = self.run_ps(*args)
            self.assertEqual(first_run.returncode, 0, self.detail(first_run))
            first = next(self.out.glob("WWM_DANE_*.zip"))
            original_zip = first.read_bytes()
            second_run = self.run_ps(*args)
            self.assertEqual(second_run.returncode, 0, self.detail(second_run))
            self.assertEqual(len(list(self.out.glob("WWM_DANE_*.zip"))), 2)
            self.assertEqual(first.read_bytes(), original_zip)
            self.assertEqual(self.original, self.game_files())

        def test_game_output_path_is_refused_before_writing(self):
            result = self.run_ps("-GameRoot", self.game, "-OutputDirectory", self.game / "Package", "-NonInteractive")
            self.assertEqual(result.returncode, 1, self.detail(result))
            self.assertEqual(self.original, self.game_files())
            self.assertFalse(list(self.game.rglob("WWM_DANE_*.zip")))

        def test_absent_maps_produce_explicit_partial_inventory(self):
            for p in self.game.rglob("translate_words_map_en*"):
                p.unlink()
            result = self.run_ps("-GameRoot", self.game, "-OutputDirectory", self.out, "-NonInteractive")
            self.assertEqual(result.returncode, 2, self.detail(result))
            report, inventory, _, _ = self.collection()
            self.assertEqual(report["status"], "partial")
            self.assertGreater(len(inventory), 0)
            self.assertFalse(any(row["kind"] == "map_en" for row in report["files"]))

        def test_reparse_directory_is_not_followed(self):
            outside = self.root / "outside"
            outside.mkdir()
            (outside / "should_not_enter.txt").write_text("synthetic outside", encoding="utf-8")
            junction = self.game / "Package" / "link_to_outside"
            result = subprocess.run([os.environ["COMSPEC"], "/d", "/c", "mklink", "/J", str(junction), str(outside)],
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30, check=False)
            self.assertEqual(result.returncode, 0, self.detail(result))
            result = self.run_ps("-GameRoot", self.game, "-OutputDirectory", self.out, "-NonInteractive")
            self.assertEqual(result.returncode, 2, self.detail(result))
            report, inventory, _, _ = self.collection()
            self.assertTrue(any(row["reason"] == "reparse_skipped" for row in report["problems"]))
            self.assertFalse(any("should_not_enter" in row["path"] for row in inventory))
            self.assertEqual((outside / "should_not_enter.txt").read_text(encoding="utf-8"), "synthetic outside")


if __name__ == "__main__":
    unittest.main()
