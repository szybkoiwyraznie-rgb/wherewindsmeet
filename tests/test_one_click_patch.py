from __future__ import annotations

import subprocess
import sys
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from tests.test_apply_translation import container, table
from tests.test_buduj_paczke import EN_EXTRA, ZH_EXTRA, world
from tests.test_mapa_tekstow import diff_container
from tests.test_potok_tlumaczenia import fill
from tests.test_wyciag_indeks import EN, ZH, K, T
from tests.test_zrodla_tekstow import FakeBaza
from tools import apply_translation, buduj_paczke, indeks, latka_testowa, mapa_tekstow, one_click_patch, tlumaczenie, wyciag

ZH_ALL = {**ZH, **ZH_EXTRA}
EN_ALL = {**EN, **EN_EXTRA}


class OneClickPatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="wwm-one-click-test-")
        cls.root = Path(cls.temp.name)
        wyciag.zbuduj(
            FakeBaza(world()),
            ZH_ALL,
            EN_ALL,
            cls.root / "index",
            {"opis": "test one-click"},
            log=lambda _text: None,
        )
        cls.ix = indeks.wczytaj(cls.root / "index")
        buduj_paczke.zbuduj(cls.ix, cls.root / "paczka", wersja="1", data="2026-01-01", zip_=False)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def _build_collector_zip(self, path: Path, *, build_id: str = "25906190") -> None:
        zh_base = container(
            [
                table(
                    [
                        (T + 1, ZH[T + 1].encode("utf-8")),
                        (T + 3, ZH[T + 3].encode("utf-8")),
                        (T + 4, ZH[T + 4].encode("utf-8")),
                        (T + 20, ZH[T + 20].encode("utf-8")),
                    ]
                )
            ],
            with_metadata=True,
        )
        zh_diff = diff_container([0], 1, [table([(T + 21, ZH[T + 21].encode("utf-8"))])])
        pkg_en = container(
            [
                table(
                    [
                        (T + 1, b"smith line"),
                        (T + 3, b"male version"),
                        (T + 4, b"female version"),
                        (T + 20, b"Sword"),
                    ]
                )
            ],
            with_metadata=True,
        )
        pkg_en_diff = diff_container([0], 1, [table([(T + 21, b"Sword description")])])
        patch_en_diff = diff_container([0], 1, [table([(T + 20, b"Sword (Patch)")])])

        raport = {
            "schema": "wwm-collection-v2",
            "steam_build_id": build_id,
            "files": [
                {
                    "source": "Package/HD/oversea/locale/translate_words_map_zh_cn",
                    "status": "copied",
                    "stored_as": "pliki/000001_translate_words_map_zh_cn",
                },
                {
                    "source": "LocalData/Patch/HD/oversea/locale/translate_words_map_zh_cn_diff",
                    "status": "copied",
                    "stored_as": "pliki/000002_translate_words_map_zh_cn_diff",
                },
                {
                    "source": "Package/HD/oversea/locale/translate_words_map_en",
                    "status": "copied",
                    "stored_as": "pliki/000003_translate_words_map_en",
                },
                {
                    "source": "Package/HD/oversea/locale/translate_words_map_en_diff",
                    "status": "copied",
                    "stored_as": "pliki/000004_translate_words_map_en_diff",
                },
                {
                    "source": "LocalData/Patch/HD/oversea/locale/translate_words_map_en_diff",
                    "status": "copied",
                    "stored_as": "pliki/000005_translate_words_map_en_diff",
                },
            ],
        }
        with zipfile.ZipFile(path, "w") as zf:
            zf.writestr("RAPORT.json", json.dumps(raport))
            zf.writestr("pliki/000001_translate_words_map_zh_cn", zh_base)
            zf.writestr("pliki/000002_translate_words_map_zh_cn_diff", zh_diff)
            zf.writestr("pliki/000003_translate_words_map_en", pkg_en)
            zf.writestr("pliki/000004_translate_words_map_en_diff", pkg_en_diff)
            zf.writestr("pliki/000005_translate_words_map_en_diff", patch_en_diff)

    def _partial_md(self, src_rel: str, translations: dict[str, str], out_path: Path) -> Path:
        raw = (self.root / "paczka" / src_rel).read_text(encoding="utf-8")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(fill(raw, translations), encoding="utf-8")
        return out_path

    def test_partial_return_and_collector_zip_produce_ready_windows_installer(self):
        collector_zip = self.root / "WWM_DANE_test.zip"
        self._build_collector_zip(collector_zip, build_id="25906190")

        # Częściowa zwrotka: 1 plik .md ze sceną + 1 plik .zip z widokiem przedmiotów (większość PL: nadal pusta!).
        md1 = self._partial_md(
            "sceny/01_watek-glowny_rozdzial-1_01.md",
            {
                K("kwestia kowala"): "Cześć, wędrowcze!",
                f"@{T + 3:016x}": "Zrobiłem to",
                f"@{T + 4:016x}": "Zrobiłam to",
            },
            self.root / "zwrotka_czesc" / "01_watek-glowny_rozdzial-1_01.md",
        )
        md2 = self._partial_md(
            "widoki/03_przedmioty_01.md",
            {K("Opis miecza"): "Zażółć gęślą jaźń"},
            self.root / "zwrotka_czesc" / "03_przedmioty_01.md",
        )
        zwrotka_zip = self.root / "czesciowa_zwrotka.zip"
        with zipfile.ZipFile(zwrotka_zip, "w") as zf:
            zf.write(md2, arcname="widoki/03_przedmioty_01.md")

        out_zip = self.root / "dist" / "WWM_LATKA_PL.zip"
        raport_json = self.root / "dist" / "raport.json"
        rc = one_click_patch.main(
            [
                "--zwrotka",
                str(md1),
                str(zwrotka_zip),
                "--dane-gry",
                str(collector_zip),
                "--indeks",
                str(self.root / "index"),
                "--tylko-zwrotka",
                "--wyj-zip",
                str(out_zip),
                "--raport",
                str(raport_json),
            ]
        )
        self.assertEqual(rc, 0)
        self.assertTrue(out_zip.is_file())
        raport = json.loads(raport_json.read_text(encoding="utf-8"))
        self.assertTrue(raport["ok"])
        self.assertEqual(raport["build_gry"], "25906190")
        self.assertEqual(raport["przekladow_po"], 4)
        self.assertEqual(len(raport["pliki_gry"]), 3)

        with zipfile.ZipFile(out_zip) as zf:
            names = set(zf.namelist())
            self.assertIn("ZAINSTALUJ.bat", names)
            self.assertIn("PRZYWROC.bat", names)
            self.assertIn("SPRAWDZ_STAN.bat", names)
            self.assertIn("instaluj_latke.ps1", names)
            self.assertIn("latka.json", names)

            manifest = json.loads(zf.read("latka.json").decode("utf-8"))
            self.assertEqual(manifest["build_gry"], "25906190")
            by_target = {row["sciezka_w_grze"]: row for row in manifest["pliki"]}

            base_map = {
                row["id"]: row["text"]
                for row in apply_translation.iter_all_entries(
                    zf.read(by_target["Package/HD/oversea/locale/translate_words_map_en"]["plik_latki"])
                )
            }
            self.assertEqual(base_map[T + 1], b"Cze\xc5\x9b\xc4\x87, w\xc4\x99drowcze!")
            self.assertEqual(base_map[T + 3], b"Zrobi\xc5\x82em to")
            self.assertEqual(base_map[T + 4], b"Zrobi\xc5\x82am to")
            self.assertEqual(base_map[T + 20], b"Sword")  # nieprzetłumaczone pozostało bez zmian

            pkg_diff = {
                row["id"]: row["text"]
                for row in apply_translation.iter_all_entries(
                    zf.read(by_target["Package/HD/oversea/locale/translate_words_map_en_diff"]["plik_latki"])
                )
            }
            self.assertEqual(pkg_diff[T + 21].decode("utf-8"), "Zażółć gęślą jaźń")

    def test_rejects_bad_return_by_default_and_builds_with_pomin_bledne(self):
        collector_zip = self.root / "WWM_DANE_bad.zip"
        self._build_collector_zip(collector_zip)

        bad_md = self.root / "bad_zwrotka" / "01.md"
        self._partial_md(
            "sceny/01_watek-glowny_rozdzial-1_01.md",
            {K("kwestia kowala"): "Dobry przekład"},
            bad_md,
        )
        with bad_md.open("a", encoding="utf-8") as handle:
            handle.write("\n99. [Kwestia] obca\n   klucz: ffffffffffffffff\n   PL: nieistniejący klucz\n")

        out_zip = self.root / "dist_bad" / "WWM_LATKA_PL.zip"
        rc_fail = one_click_patch.main(
            [
                "--zwrotka",
                str(bad_md),
                "--dane-gry",
                str(collector_zip),
                "--indeks",
                str(self.root / "index"),
                "--tylko-zwrotka",
                "--wyj-zip",
                str(out_zip),
            ]
        )
        self.assertEqual(rc_fail, 2)
        self.assertFalse(out_zip.exists())

        rc_ok = one_click_patch.main(
            [
                "--zwrotka",
                str(bad_md),
                "--dane-gry",
                str(collector_zip),
                "--indeks",
                str(self.root / "index"),
                "--tylko-zwrotka",
                "--pomin-bledne",
                "--wyj-zip",
                str(out_zip),
            ]
        )
        self.assertEqual(rc_ok, 0)
        self.assertTrue(out_zip.is_file())

    def test_merges_incremental_partial_returns_when_magazyn_provided(self):
        collector_zip = self.root / "WWM_DANE_merge.zip"
        self._build_collector_zip(collector_zip)
        magazyn_dir = self.root / "magazyn_merge"
        store = tlumaczenie.Magazyn()
        store.ustaw(K("Miecz"), "Miecz PL")
        tlumaczenie.zapisz(magazyn_dir, store)

        md1 = self._partial_md(
            "sceny/01_watek-glowny_rozdzial-1_01.md",
            {K("kwestia kowala"): "Nowa kwestia kowala"},
            self.root / "zwrotka_inc" / "01.md",
        )
        out_zip = self.root / "dist_merge" / "WWM_LATKA_PL.zip"
        rc = one_click_patch.main(
            [
                "--zwrotka",
                str(md1),
                "--magazyn",
                str(magazyn_dir),
                "--zapisz-magazyn",
                "--dane-gry",
                str(collector_zip),
                "--indeks",
                str(self.root / "index"),
                "--wyj-zip",
                str(out_zip),
            ]
        )
        self.assertEqual(rc, 0)
        reloaded = tlumaczenie.wczytaj(magazyn_dir)
        self.assertEqual(reloaded.przeklad(K("Miecz")), "Miecz PL")
        self.assertEqual(reloaded.przeklad(K("kwestia kowala")), "Nowa kwestia kowala")

        with zipfile.ZipFile(out_zip) as zf:
            manifest = json.loads(zf.read("latka.json").decode("utf-8"))
            by_target = {row["sciezka_w_grze"]: row for row in manifest["pliki"]}
            patch_diff = {
                row["id"]: row["text"]
                for row in apply_translation.iter_all_entries(
                    zf.read(by_target["LocalData/Patch/HD/oversea/locale/translate_words_map_en_diff"]["plik_latki"])
                )
            }
            self.assertEqual(patch_diff[T + 20].decode("utf-8"), "Miecz PL")

    def test_standalone_default_mode_builds_without_game_binaries_and_patches_end_to_end(self):
        # Zwrotka + magazyn bez JAKIEJKOLWIEK paczki binarnej gry (--dane-gry/--zh/--mapa pominięte).
        t_only_en = T + 999
        t_col_a = T + 910
        t_col_b = T + 911
        custom_world = world()
        zh_all = {**ZH_ALL, T + 100: "唯一", t_col_a: "十步", t_col_b: "十步"}
        en_all = {
            **EN_ALL,
            T + 100: "Unique English Label",
            t_only_en: "Fresh Hotfix Line",
            t_col_a: "Line Alpha",
            t_col_b: "Line Beta",
        }
        custom_world["text_msg"] = [(590438, {"content": t_col_a})]
        custom_world["buff"] = [*custom_world["buff"], (10, {"buff_name": T + 100}), (11, {"buff_name": t_only_en}), (12, {"buff_name": t_col_b})]
        ix_dir = self.root / "ix_standalone"
        wyciag.zbuduj(FakeBaza(custom_world), zh_all, en_all, ix_dir, {"opis": "test standalone"}, log=lambda _t: None)
        ix_local = indeks.wczytaj(ix_dir)
        paczka_dir = self.root / "paczka_standalone"
        buduj_paczke.zbuduj(ix_local, paczka_dir, wersja="1", data="2026-01-01", zip_=False)

        raw_sceny = (paczka_dir / "sceny/01_watek-glowny_rozdzial-1_01.md").read_text(encoding="utf-8")
        md1 = self.root / "zwrotka_sa" / "01.md"
        md1.parent.mkdir(parents=True, exist_ok=True)
        md1.write_text(
            fill(
                raw_sceny,
                {
                    K("kwestia kowala"): "Cześć, wędrowcze!",
                    f"@{T + 3:016x}": "Zrobiłem to",
                },
            ),
            encoding="utf-8",
        )
        raw_wid = (paczka_dir / "widoki/03_przedmioty_01.md").read_text(encoding="utf-8")
        md2 = self.root / "zwrotka_sa" / "02.md"
        md2.write_text(fill(raw_wid, {K("Opis miecza"): "Zażółć gęślą jaźń"}), encoding="utf-8")
        hotfix_key = K("Fresh Hotfix Line")
        col_a_key = mapa_tekstow.klucz_wariantu("十步", "Line Alpha")
        hotfix_sources = [p for p in paczka_dir.rglob("*.md") if hotfix_key in p.read_text(encoding="utf-8")]
        col_sources = [p for p in paczka_dir.rglob("*.md") if col_a_key in p.read_text(encoding="utf-8")]
        self.assertTrue(hotfix_sources)
        self.assertTrue(col_sources)
        md3 = self.root / "zwrotka_sa" / "03.md"
        md3.write_text(fill(hotfix_sources[0].read_text(encoding="utf-8"), {hotfix_key: "Świeża linia z hotfixa", col_a_key: "Linia Alfa PL"}), encoding="utf-8")
        md4 = self.root / "zwrotka_sa" / "04.md"
        md4.write_text(fill(col_sources[0].read_text(encoding="utf-8"), {hotfix_key: "Świeża linia z hotfixa", col_a_key: "Linia Alfa PL"}), encoding="utf-8")

        out_zip = self.root / "dist_sa" / "WWM_LATKA_PL.zip"
        raport_path = self.root / "dist_sa" / "raport.json"
        rc = one_click_patch.main(
            [
                "--zwrotka",
                str(md1),
                str(md2),
                str(md3),
                str(md4),
                "--indeks",
                str(ix_dir),
                "--tylko-zwrotka",
                "--wyj-zip",
                str(out_zip),
                "--raport",
                str(raport_path),
            ]
        )
        self.assertEqual(rc, 0)
        raport = json.loads(raport_path.read_text(encoding="utf-8"))
        self.assertEqual(raport["format"], "wwm-one-click-standalone-v1")
        self.assertEqual(raport["tryb"], "standalone")
        self.assertGreaterEqual(raport["plan"]["po_id"], 2)  # T+3 i dziedziczący T+4!
        self.assertEqual(raport["plan"]["kolizje"], 1)

        # Wewnątrz ZIP nie może być ani jednego pliku binarnego gry, tylko plan + lokalny patcher.
        with zipfile.ZipFile(out_zip) as zf:
            names = set(zf.namelist())
            self.assertIn("ZAINSTALUJ.bat", names)
            self.assertIn("PRZYWROC.bat", names)
            self.assertIn("SPRAWDZ_STAN.bat", names)
            self.assertIn("narzedzia/plan_latki.json", names)
            self.assertIn("narzedzia/patcher_wwm.py", names)
            self.assertFalse(any(n.startswith("pliki/") for n in names))
            unpack_dir = self.root / "unpacked_sa"
            zf.extractall(unpack_dir)

        # Fikcyjna instalacja gry na dysku gracza.
        game = self.root / "game_sa"
        backup = self.root / "backup_sa"
        (game / "Package/HD/oversea/locale").mkdir(parents=True, exist_ok=True)
        (game / "LocalData/Patch/HD/oversea/locale").mkdir(parents=True, exist_ok=True)
        zh_orig = container([table([(T + 1, ZH[T + 1].encode("utf-8")), (T + 3, ZH[T + 3].encode("utf-8")), (T + 4, ZH[T + 4].encode("utf-8")), (T + 21, ZH[T + 21].encode("utf-8")), (t_col_a, "十步".encode("utf-8")), (t_col_b, "十步".encode("utf-8"))])], with_metadata=True)
        en_base_orig = container([table([(T + 1, b"smith line"), (T + 3, b"male version"), (T + 4, b"female version"), (t_col_a, b"Line Alpha"), (t_col_b, b"Line Beta")])], with_metadata=True)
        en_pkg_diff_orig = diff_container([0], 1, [table([(T + 21, b"Sword description")])])
        # Świeży wpis w LocalData/Patch bez odpowiadającego wpisu w zh_cn (test fallbacku EN!).
        en_patch_diff_orig = diff_container([0], 1, [table([(t_only_en, b"Fresh Hotfix Line")])])

        (game / "Package/HD/oversea/locale/translate_words_map_zh_cn").write_bytes(zh_orig)
        (game / "Package/HD/oversea/locale/translate_words_map_en").write_bytes(en_base_orig)
        (game / "Package/HD/oversea/locale/translate_words_map_en_diff").write_bytes(en_pkg_diff_orig)
        (game / "LocalData/Patch/HD/oversea/locale/translate_words_map_en_diff").write_bytes(en_patch_diff_orig)

        tools_dir = unpack_dir / "narzedzia"
        res_ins = subprocess.run(
            [sys.executable, "patcher_wwm.py", "--akcja", "instaluj", "--plan", "plan_latki.json", "--game", str(game), "--backup-dir", str(backup), "--non-interactive", "--json"],
            cwd=str(tools_dir),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(res_ins.returncode, 0, res_ins.stderr or res_ins.stdout)

        patched_base = {e["id"]: e["text"].decode("utf-8") for e in apply_translation.iter_all_entries((game / "Package/HD/oversea/locale/translate_words_map_en").read_bytes())}
        self.assertEqual(patched_base[T + 1], "Cześć, wędrowcze!")
        self.assertEqual(patched_base[T + 3], "Zrobiłem to")
        self.assertEqual(patched_base[T + 4], "Zrobiłem to")  # dziedziczenie rodzeństwa w plan_latki.json!
        self.assertEqual(patched_base[t_col_a], "Linia Alfa PL")  # rozstrzygnięta kolizja!
        self.assertEqual(patched_base[t_col_b], "Line Beta")  # nieprzetłumaczony wariant nietknięty!

        patched_pkg_diff = {e["id"]: e["text"].decode("utf-8") for e in apply_translation.iter_all_entries((game / "Package/HD/oversea/locale/translate_words_map_en_diff").read_bytes())}
        self.assertEqual(patched_pkg_diff[T + 21], "Zażółć gęślą jaźń")

        patched_patch_diff = {e["id"]: e["text"].decode("utf-8") for e in apply_translation.iter_all_entries((game / "LocalData/Patch/HD/oversea/locale/translate_words_map_en_diff").read_bytes())}
        self.assertEqual(patched_patch_diff[t_only_en], "Świeża linia z hotfixa")

        # Upgrade łatki v1 -> v2 (np. zmiana tekstu T+21 na v2): nie może nadpisać backupu oryginału!
        md2.write_text(fill(raw_wid, {K("Opis miecza"): "Zażółć gęślą jaźń v2"}), encoding="utf-8")
        out_zip2 = self.root / "dist_sa" / "WWM_LATKA_PL_v2.zip"
        self.assertEqual(one_click_patch.main(["--zwrotka", str(md1), str(md2), str(md3), str(md4), "--indeks", str(ix_dir), "--tylko-zwrotka", "--wyj-zip", str(out_zip2)]), 0)
        unpack2 = self.root / "unpacked_sa2"
        with zipfile.ZipFile(out_zip2) as zf:
            zf.extractall(unpack2)
        res_up = subprocess.run(
            [sys.executable, "patcher_wwm.py", "--akcja", "instaluj", "--plan", "plan_latki.json", "--game", str(game), "--backup-dir", str(backup), "--non-interactive"],
            cwd=str(unpack2 / "narzedzia"),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(res_up.returncode, 0, res_up.stderr or res_up.stdout)
        self.assertEqual((backup / "pliki/Package/HD/oversea/locale/translate_words_map_en").read_bytes(), en_base_orig)
        patched_pkg_diff_v2 = {e["id"]: e["text"].decode("utf-8") for e in apply_translation.iter_all_entries((game / "Package/HD/oversea/locale/translate_words_map_en_diff").read_bytes())}
        self.assertEqual(patched_pkg_diff_v2[T + 21], "Zażółć gęślą jaźń v2")

        # Symulacja aktualizacji Steam na jednym z plików: odmowa przywracania bez --wymus,
        # a ponowna instalacja zapisuje kopię nowej wersji gry i nakłada łatkę na nową mapę.
        new_steam_patch_diff = diff_container([0], 1, [table([(t_only_en, b"Fresh Hotfix Line"), (T + 998, b"New Steam Line")])])
        (game / "LocalData/Patch/HD/oversea/locale/translate_words_map_en_diff").write_bytes(new_steam_patch_diff)
        res_refuse = subprocess.run(
            [sys.executable, "patcher_wwm.py", "--akcja", "przywroc", "--plan", "plan_latki.json", "--game", str(game), "--backup-dir", str(backup), "--non-interactive"],
            cwd=str(unpack2 / "narzedzia"),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(res_refuse.returncode, 1)
        res_repatch = subprocess.run(
            [sys.executable, "patcher_wwm.py", "--akcja", "instaluj", "--plan", "plan_latki.json", "--game", str(game), "--backup-dir", str(backup), "--non-interactive"],
            cwd=str(unpack2 / "narzedzia"),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(res_repatch.returncode, 0, res_repatch.stderr or res_repatch.stdout)
        self.assertEqual((backup / "pliki/LocalData/Patch/HD/oversea/locale/translate_words_map_en_diff").read_bytes(), new_steam_patch_diff)
        patched_after_steam = {e["id"]: e["text"].decode("utf-8") for e in apply_translation.iter_all_entries((game / "LocalData/Patch/HD/oversea/locale/translate_words_map_en_diff").read_bytes())}
        self.assertEqual(patched_after_steam[t_only_en], "Świeża linia z hotfixa")
        self.assertEqual(patched_after_steam[T + 998], "New Steam Line")

        # Przywrócenie oryginałów przywraca już nową wersję Steam w zmodyfikowanym pliku oraz pierwotną bazę EN!
        res_rest = subprocess.run(
            [sys.executable, "patcher_wwm.py", "--akcja", "przywroc", "--plan", "plan_latki.json", "--game", str(game), "--backup-dir", str(backup), "--non-interactive"],
            cwd=str(unpack2 / "narzedzia"),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(res_rest.returncode, 0, res_rest.stderr or res_rest.stdout)
        self.assertEqual((game / "Package/HD/oversea/locale/translate_words_map_en").read_bytes(), en_base_orig)
        self.assertEqual((game / "LocalData/Patch/HD/oversea/locale/translate_words_map_en_diff").read_bytes(), new_steam_patch_diff)

    def test_latka_testowa_standalone_mode_builds_without_game_binaries(self):
        t_cut = T + 860
        t_prolog = T + 861
        t_settings = T + 862
        zh_dict = {**ZH_ALL, t_cut: "十步杀一人", t_prolog: "是啊 来抓你", t_settings: "设置"}
        en_dict = {**EN_ALL, t_cut: "Cut them down, left and right", t_prolog: "That's right, here to take you in.", t_settings: "Settings"}
        custom = world()
        custom["text_msg"] = [(590438, {"content": t_cut}), (590337, {"content": t_prolog}), (1, {"content": t_settings})]
        ix_dir = self.root / "ix_latka_sa"
        wyciag.zbuduj(FakeBaza(custom), zh_dict, en_dict, ix_dir, {}, log=lambda _t: None)

        out_zip = self.root / "WWM_LATKA_TEST_STANDALONE.zip"
        rc = latka_testowa.main(["--indeks", str(ix_dir), "--zakres", "ui+prolog", "--wyj-zip", str(out_zip)])
        self.assertEqual(rc, 0)
        with zipfile.ZipFile(out_zip) as zf:
            names = set(zf.namelist())
            self.assertIn("narzedzia/plan_latki.json", names)
            self.assertFalse(any(n.startswith("pliki/") for n in names))
            plan = json.loads(zf.read("narzedzia/plan_latki.json").decode("utf-8"))
            self.assertEqual(plan["format"], "wwm-plan-latki-v1")
            self.assertGreaterEqual(len(plan["po_kluczu"]), 3)

    def test_patcher_and_one_click_replace_package_diff_with_localdata_patch_diff(self):
        # Gdy w grze istnieją zarówno Package/.../zh_cn_diff, jak i LocalData/Patch/.../zh_cn_diff,
        # nowszy _diff z LocalData/Patch musi zastąpić ten z Package (także dla wycofanych kluczy).
        game = self.root / "game_diff_replace"
        backup = self.root / "backup_diff_replace"
        (game / "Package/HD/oversea/locale").mkdir(parents=True, exist_ok=True)
        (game / "LocalData/Patch/HD/oversea/locale").mkdir(parents=True, exist_ok=True)

        zh_base = container([table([(T + 1, ZH[T + 1].encode("utf-8"))])], with_metadata=True)
        # Starszy pkg_diff zmieniał T+1 na nieaktualne ZH[T+20] ("Miecz"), a nowszy patch_diff go wycofał (pusty / inny klucz).
        zh_pkg_diff = diff_container([0], 1, [table([(T + 1, ZH[T + 20].encode("utf-8"))])])
        zh_patch_diff = diff_container([0], 1, [table([(T + 2, ZH[T + 2].encode("utf-8"))])])
        en_base = container([table([(T + 1, b"smith line"), (T + 2, b"second line")])], with_metadata=True)

        (game / "Package/HD/oversea/locale/translate_words_map_zh_cn").write_bytes(zh_base)
        (game / "Package/HD/oversea/locale/translate_words_map_zh_cn_diff").write_bytes(zh_pkg_diff)
        (game / "LocalData/Patch/HD/oversea/locale/translate_words_map_zh_cn_diff").write_bytes(zh_patch_diff)
        (game / "Package/HD/oversea/locale/translate_words_map_en").write_bytes(en_base)

        dedup_zh, pairs, _ = one_click_patch.odkryj_mapy([game], self.root / "odkryj_tmp")
        self.assertEqual(
            [p.relative_to(game).as_posix() for p in dedup_zh],
            [
                "Package/HD/oversea/locale/translate_words_map_zh_cn",
                "LocalData/Patch/HD/oversea/locale/translate_words_map_zh_cn_diff",
            ],
        )
        self.assertEqual(len(pairs), 1)

        # W magazynie tłumaczenie istnieje wyłącznie dla prawdziwego bazowego klucza T+1 (kwestia kowala), NIE dla T+20 ("Miecz"):
        store_dir = self.root / "store_diff_replace"
        store = tlumaczenie.Magazyn()
        store.ustaw(K("kwestia kowala"), "kwestia kowala po polsku")
        store.ustaw(K("Miecz"), "Błędny Miecz PL")
        tlumaczenie.zapisz(store_dir, store)

        out_zip = self.root / "WWM_DIFF_REPLACE.zip"
        rc = one_click_patch.main(["--tylko-magazyn", "--magazyn", str(store_dir), "--indeks", str(self.root / "index"), "--wyj-zip", str(out_zip)])
        self.assertEqual(rc, 0)
        unpack = self.root / "unpack_diff_replace"
        with zipfile.ZipFile(out_zip) as zf:
            zf.extractall(unpack)
        res = subprocess.run(
            [sys.executable, "patcher_wwm.py", "--akcja", "instaluj", "--plan", "plan_latki.json", "--game", str(game), "--backup-dir", str(backup), "--non-interactive"],
            cwd=str(unpack / "narzedzia"),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(res.returncode, 0, res.stderr or res.stdout)
        patched_en = {e["id"]: e["text"].decode("utf-8") for e in apply_translation.iter_all_entries((game / "Package/HD/oversea/locale/translate_words_map_en").read_bytes())}
        self.assertEqual(patched_en[T + 1], "kwestia kowala po polsku")


if __name__ == "__main__":
    unittest.main()
