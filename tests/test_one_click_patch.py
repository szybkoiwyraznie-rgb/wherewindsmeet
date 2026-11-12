from __future__ import annotations

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
from tools import apply_translation, buduj_paczke, indeks, one_click_patch, tlumaczenie, wyciag

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


if __name__ == "__main__":
    unittest.main()
