"""Windows-only execution tests for the standalone patcher ZIP (no game binaries inside)."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from tests.test_apply_translation import container, table
from tests.test_buduj_paczke import EN_EXTRA, ZH_EXTRA, world
from tests.test_mapa_tekstow import diff_container
from tests.test_wyciag_indeks import EN, ZH, K, T
from tests.test_zrodla_tekstow import FakeBaza
from tools import apply_translation, one_click_patch, wyciag, buduj_paczke


if os.name == "nt":
    def _fill(text: str, translations: dict[str, str]) -> str:
        out, pending = [], None
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("klucz: "):
                pending = stripped[7:]
            elif stripped == "PL:" and pending in translations:
                line = f"{line} {translations[pending]}"
            out.append(line)
        return "\n".join(out) + "\n"

    class WindowsStandalonePatcherTests(unittest.TestCase):
        def setUp(self):
            self.temp = tempfile.TemporaryDirectory()
            self.addCleanup(self.temp.cleanup)
            self.root = Path(self.temp.name)
            self.steam = self.root / "Steam [główny]"
            self.game = self.steam / "steamapps/common/Where Winds Meet"
            self.backup = self.root / "Kopia standalone [test] żółć"
            self.kit = self.root / "Latka standalone [test] żółć"

            (self.steam / "steamapps").mkdir(parents=True)
            (self.steam / "steamapps/appmanifest_3564740.acf").write_text(
                '"AppState"\n{\n"installdir" "Where Winds Meet"\n"buildid" "25906190"\n}\n',
                encoding="utf-8",
            )
            (self.game / "Package/HD/oversea/locale").mkdir(parents=True, exist_ok=True)
            (self.game / "LocalData/Patch/HD/oversea/locale").mkdir(parents=True, exist_ok=True)

            self.zh_bytes = container(
                [table([(T + 1, ZH[T + 1].encode("utf-8")), (T + 3, ZH[T + 3].encode("utf-8"))])],
                with_metadata=True,
            )
            self.en_base = container(
                [table([(T + 1, b"smith line"), (T + 3, b"male version")])],
                with_metadata=True,
            )
            self.en_patch_diff = diff_container([0], 1, [table([(T + 20, b"Sword")])])

            (self.game / "Package/HD/oversea/locale/translate_words_map_zh_cn").write_bytes(self.zh_bytes)
            (self.game / "Package/HD/oversea/locale/translate_words_map_en").write_bytes(self.en_base)
            (self.game / "LocalData/Patch/HD/oversea/locale/translate_words_map_en_diff").write_bytes(self.en_patch_diff)

            ix_dir = self.root / "index"
            wyciag.zbuduj(FakeBaza(world()), {**ZH, **ZH_EXTRA}, {**EN, **EN_EXTRA}, ix_dir, {"opis": "win-sa"}, log=lambda _t: None)
            ix = __import__("tools.indeks", fromlist=["wczytaj"]).wczytaj(ix_dir)
            paczka_dir = self.root / "paczka"
            buduj_paczke.zbuduj(ix, paczka_dir, wersja="1", data="2026-01-01", zip_=False)

            md1 = self.root / "zwrotka.md"
            raw = (paczka_dir / "sceny/01_watek-glowny_rozdzial-1_01.md").read_text(encoding="utf-8")
            md1.write_text(_fill(raw, {K("kwestia kowala"): "Cześć żółć!", f"@{T + 3:016x}": "Zrobiłem to"}), encoding="utf-8")

            zip_path = self.root / "WWM_LATKA_PL.zip"
            rc = one_click_patch.main(["--zwrotka", str(md1), "--indeks", str(ix_dir), "--tylko-zwrotka", "--wyj-zip", str(zip_path)])
            self.assertEqual(rc, 0)
            with ZipFile(zip_path) as zf:
                zf.extractall(self.kit)

        def run_bat(self, bat_name: str, *extra: str) -> subprocess.CompletedProcess:
            bat = self.kit / bat_name
            args = " ".join(f'"{a}"' if " " in a else a for a in extra)
            command = f'"{bat}" "{self.game}" {args}'
            env = {**os.environ, "WWM_USE_CURRENT_PYTHON": "1"}
            return subprocess.run(
                command,
                shell=True,
                input=b"\r\n",
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=env,
                timeout=180,
                check=False,
            )

        def test_standalone_bat_status_install_and_restore_on_windows(self):
            st0 = self.run_bat("SPRAWDZ_STAN.bat", "--backup-dir", str(self.backup), "--non-interactive")
            self.assertEqual(st0.returncode, 0, st0.stdout.decode("utf-8", "replace"))
            self.assertIn("ORYGINAL_NIEZAPISANY", st0.stdout.decode("utf-8", "replace"))

            ins = self.run_bat("ZAINSTALUJ.bat", "--backup-dir", str(self.backup), "--non-interactive")
            self.assertEqual(ins.returncode, 0, ins.stdout.decode("utf-8", "replace"))
            patched = {
                e["id"]: e["text"].decode("utf-8")
                for e in apply_translation.iter_all_entries(
                    (self.game / "Package/HD/oversea/locale/translate_words_map_en").read_bytes()
                )
            }
            self.assertEqual(patched[T + 1], "Cześć żółć!")
            self.assertEqual(patched[T + 3], "Zrobiłem to")

            st1 = self.run_bat("SPRAWDZ_STAN.bat", "--backup-dir", str(self.backup), "--non-interactive")
            self.assertEqual(st1.returncode, 0, st1.stdout.decode("utf-8", "replace"))
            self.assertIn("ZAINSTALOWANO_LATKE", st1.stdout.decode("utf-8", "replace"))

            res = self.run_bat("PRZYWROC.bat", "--backup-dir", str(self.backup), "--non-interactive")
            self.assertEqual(res.returncode, 0, res.stdout.decode("utf-8", "replace"))
            self.assertEqual((self.game / "Package/HD/oversea/locale/translate_words_map_en").read_bytes(), self.en_base)
