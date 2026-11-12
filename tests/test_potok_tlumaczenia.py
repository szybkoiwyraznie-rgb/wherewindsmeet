from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from tests.test_apply_translation import container, table
from tests.test_buduj_paczke import EN_EXTRA, ZH_EXTRA, world
from tests.test_mapa_tekstow import diff_container
from tests.test_wyciag_indeks import EN, ZH, K, T
from tests.test_zrodla_tekstow import FakeBaza
from tools import audyt_aktualizacji, buduj_paczke, import_zwrotki, indeks, latka_testowa, mapa_tekstow, tlumaczenie, wyciag, zbuduj_latke

ROOT = Path(__file__).resolve().parent.parent
CLI_TOOLS = ("baza_gry", "wyciag", "indeks", "uklad_scen", "buduj_paczke", "import_zwrotki", "zbuduj_latke", "latka_testowa", "audyt_aktualizacji")
ZH_ALL = {**ZH, **ZH_EXTRA}
EN_ALL = {**EN, **EN_EXTRA}


def fill(text: str, translations: dict[str, str]) -> str:
    """Wpisz przekłady po `PL:` tak, jak zrobiłby to tłumacz."""
    out, pending = [], None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("klucz: "):
            pending = stripped[7:]
        elif stripped == "PL:" and pending in translations:
            line = f"{line} {translations[pending]}"
        out.append(line)
    return "\n".join(out) + "\n"


class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="wwm-potok-")
        cls.root = Path(cls.temp.name)
        wyciag.zbuduj(FakeBaza(world()), ZH_ALL, EN_ALL, cls.root / "index", {"opis": "wersja 1"}, log=lambda _text: None)
        cls.ix = indeks.wczytaj(cls.root / "index")
        buduj_paczke.zbuduj(cls.ix, cls.root / "paczka", wersja="1", data="2026-01-01")

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def returned(self, translations: dict[str, str], name: str = "zwrotka") -> Path:
        folder = self.root / name
        for part in ("sceny", "widoki"):
            (folder / part).mkdir(parents=True, exist_ok=True)
            for path in (self.root / "paczka" / part).glob("*.md"):
                (folder / part / path.name).write_text(fill(path.read_text(encoding="utf-8"), translations), encoding="utf-8")
        return folder

    def test_command_line_tools_write_utf8_when_the_pipe_has_a_legacy_code_page(self):
        """Windows daje przekierowanemu wyjściu stronę kodową bez polskich znaków."""
        env = {**os.environ, "PYTHONIOENCODING": "cp1252", "PYTHONUTF8": "0"}
        for name in CLI_TOOLS:
            with self.subTest(tool=name):
                result = subprocess.run([sys.executable, str(ROOT / "tools" / f"{name}.py"), "--help"], capture_output=True, env=env)
                self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", "replace"))
                self.assertIn("usage:", result.stdout.decode("utf-8"))
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "buduj_paczke.py"), "--indeks", str(self.root / "index"), "--wyj", str(self.root / "paczka_cli"),
             "--wersja", "1", "--data", "2026-01-01", "--bez-zip"],
            capture_output=True, env=env,
        )
        self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", "replace"))
        self.assertEqual(json.loads(result.stdout.decode("utf-8"))["rodzaj"], "pełny")

    def test_import_accepts_good_entries_and_reports_bad_ones(self):
        folder = self.returned(
            {
                K("kwestia kowala"): "kwestia kowala po polsku",
                K("Miecz"): "Miecz PL",
                f"@{T + 3:016x}": "zrobiłem",
                K("Efekt #Y{0}#E\nna dwie linie"): "Efekt {0}\\npo polsku",  # zgubione #Y i #E
            },
            "zwrotka_a",
        )
        (folder / "obcy.md").write_text("1. [X] cokolwiek\n   klucz: ffffffffffffffff\n   PL: tekst spoza gry\n", encoding="utf-8")
        store = tlumaczenie.Magazyn()
        report = import_zwrotki.importuj(self.ix, import_zwrotki.pliki_zwrotki([folder]), store)
        self.assertEqual(report["liczby"]["nowe"], 3)
        self.assertEqual(report["odrzucone"], 2)
        self.assertEqual(report["problemy_wg_rodzaju"], {"nieznany_klucz": 1, "tokeny": 1})
        tokens = [item for item in report["problemy"] if item["rodzaj"] == "tokeny"][0]
        self.assertEqual((tokens["brakuje"], tokens["nadmiar"]), (["#E", "#Y"], []))
        self.assertTrue(tokens["plik"].startswith("widoki/04_"))
        self.assertEqual(store.po_kluczu[K("Miecz")], "Miecz PL")
        self.assertEqual(store.po_id, {f"{T + 3:016x}": "zrobiłem"})
        self.assertNotIn("po polsku\n", json.dumps(report))  # raport nie niesie treści przekładów

    def test_import_decodes_newlines_restores_edge_spaces_and_accepts_english_token_set(self):
        zh = {T + 1: "  spacje na brzegach ", T + 2: "kod {0} i {1}"}
        en = {T + 1: "edge spaces", T + 2: "code {0}"}  # angielski ma mniej kodów niż chiński
        tables = {"text_msg": [(1, {"content": T + 1}), (2, {"content": T + 2})]}
        with tempfile.TemporaryDirectory(prefix="wwm-potok-") as temp:
            wyciag.zbuduj(FakeBaza(tables), zh, en, Path(temp) / "index", {}, log=lambda _text: None)
            ix = indeks.wczytaj(Path(temp) / "index")
            content = (
                f"1. [x] a\n   klucz: {K(zh[T + 1])}\n   PL: pierwsza\\ndruga\n"
                f"2. [x] b\n   klucz: {K(zh[T + 2])}\n   PL: kod {{0}}\n"
            )
            store = tlumaczenie.Magazyn()
            report = import_zwrotki.importuj(ix, [("plik.md", content)], store)
        self.assertEqual(report["odrzucone"], 0)
        self.assertEqual(store.po_kluczu[K(zh[T + 1])], "  pierwsza\ndruga ")
        self.assertEqual(store.po_kluczu[K(zh[T + 2])], "kod {0}")

    def test_import_flags_broken_lines_and_conflicts_and_reads_zips(self):
        key = K("kwestia kowala")
        broken = f"1. [x] a\n   klucz: {key}\n   PL: pierwsza linia\n   druga linia\n"
        first = f"1. [x] a\n   klucz: {key}\n   PL: wersja pierwsza\n"
        second = f"1. [x] a\n   klucz: {key}\n   PL: wersja druga\n"
        archive = self.root / "zwrotka.zip"
        with zipfile.ZipFile(archive, "w") as outer:
            outer.writestr("sceny/a.md", first)
            outer.writestr("sceny/b.md", second)
            outer.writestr("nie_md.txt", second)
        store = tlumaczenie.Magazyn()
        report = import_zwrotki.importuj(self.ix, import_zwrotki.pliki_zwrotki([archive]), store)
        self.assertEqual(report["plikow"], 2)
        self.assertEqual(report["problemy_wg_rodzaju"], {"sprzeczne": 1})
        self.assertEqual(store.po_kluczu[key], "wersja pierwsza")
        report = import_zwrotki.importuj(self.ix, [("x.md", broken)], tlumaczenie.Magazyn())
        self.assertEqual(report["problemy_wg_rodzaju"], {"zlamana_linia": 1})
        with self.assertRaises(import_zwrotki.ZwrotkaError):
            list(import_zwrotki.pliki_zwrotki([self.root / "nie_ma"]))

    def test_import_cli_writes_store_and_report(self):
        folder = self.returned({K("Miecz"): "Miecz PL"}, "zwrotka_cli")
        store_dir, report_path = self.root / "magazyn_cli", self.root / "raport.json"
        code = import_zwrotki.main([str(folder), "--indeks", str(self.root / "index"), "--magazyn", str(store_dir), "--raport", str(report_path)])
        self.assertEqual(code, 0)
        self.assertEqual(tlumaczenie.wczytaj(store_dir).po_kluczu, {K("Miecz"): "Miecz PL"})
        self.assertEqual(json.loads(report_path.read_text(encoding="utf-8"))["liczby"]["nowe"], 1)

    def test_patch_rewrites_only_translated_entries_in_base_and_diff_layers(self):
        maps = self.root / "mapy"
        maps.mkdir(exist_ok=True)
        zh_path = maps / "zh"
        zh_path.write_bytes(container([table([(T + 1, ZH[T + 1].encode()), (T + 3, ZH[T + 3].encode()), (T + 4, ZH[T + 4].encode()), (T + 20, ZH[T + 20].encode()), (T + 22, ZH[T + 22].encode())])], with_metadata=True))
        base = maps / "en"
        base.write_bytes(container([table([(T + 1, b"smith line"), (T + 3, b"male version"), (T + 4, b"female version"), (T + 20, b"Sword"), (T + 22, b"Blade"), (T + 99, b"english only text")])], with_metadata=True))
        diff = maps / "en_diff"
        diff.write_bytes(diff_container([1], 6, [table([(T + 1, b"smith line, revised"), (T + 30, b"\xff")])]))
        store_dir = self.root / "magazyn_latka"
        store = tlumaczenie.Magazyn()
        store.ustaw(K("kwestia kowala"), "kwestia kowala po polsku")
        store.ustaw(K("Miecz"), "Miecz PL")
        store.ustaw(f"@{T + 3:016x}", "zrobiłem")
        store.ustaw(K("english only text"), "tekst tylko angielski")
        tlumaczenie.zapisz(store_dir, store)
        out = self.root / "latka"
        code = zbuduj_latke.main(["--indeks", str(self.root / "index"), "--magazyn", str(store_dir), "--zh", str(zh_path), "--cel", str(base), "--cel", str(diff), "--wyj", str(out)])
        self.assertEqual(code, 0)
        patched = mapa_tekstow.wczytaj(out / "en")
        self.assertEqual(
            patched,
            {
                T + 1: "kwestia kowala po polsku",
                T + 3: "zrobiłem",
                T + 4: "zrobiłem",  # pusty wariant bohaterki dziedziczy po bohaterze
                T + 20: "Miecz PL",
                T + 22: "Miecz PL",  # ten sam tekst źródłowy pod innym identyfikatorem
                T + 99: "tekst tylko angielski",  # brak chińskiego: klucz z tekstu w pliku celu
            },
        )
        layer, removed = mapa_tekstow.wczytaj_warstwe(out / "en_diff")
        self.assertEqual(layer, {T + 1: "kwestia kowala po polsku"})
        self.assertEqual(removed, {T + 30})
        report = json.loads((out / "latka.json").read_text(encoding="utf-8"))
        self.assertEqual([(item["plik"], item["wpisow"], item["przetlumaczonych"]) for item in report["pliki"]], [("en", 6, 6), ("en_diff", 1, 1)])
        self.assertEqual(base.read_bytes()[:4], (out / "en").read_bytes()[:4])
        self.assertIn("nie była sprawdzona w grze", report["uwaga"])

    def test_patch_refuses_empty_store_and_output_next_to_sources(self):
        maps = self.root / "mapy2"
        maps.mkdir(exist_ok=True)
        (maps / "en").write_bytes(container([table([(T + 1, b"x")])], with_metadata=True))
        common = ["--indeks", str(self.root / "index"), "--zh", str(maps / "en"), "--cel", str(maps / "en")]
        self.assertEqual(zbuduj_latke.main([*common, "--magazyn", str(self.root / "pusty"), "--wyj", str(self.root / "latka2")]), 1)
        self.assertEqual(zbuduj_latke.main([*common, "--magazyn", str(self.root / "pusty"), "--wyj", str(maps)]), 1)

    def test_patch_supports_explicit_game_paths_identical_basenames_and_build_id(self):
        maps = self.root / "mapy_duplikaty"
        a = maps / "a" / "translate_words_map_en_diff"
        b = maps / "b" / "translate_words_map_en_diff"
        zh = maps / "zh"
        a.parent.mkdir(parents=True)
        b.parent.mkdir(parents=True)
        zh.parent.mkdir(parents=True, exist_ok=True)
        zh.write_bytes(container([table([(T + 1, b"kwestia kowala"), (T + 20, b"Miecz")])], with_metadata=True))
        a.write_bytes(container([table([(T + 1, b"blacksmith line")])], with_metadata=True))
        b.write_bytes(container([table([(T + 20, b"Sword")])], with_metadata=True))

        store = tlumaczenie.Magazyn()
        store.ustaw(K("kwestia kowala"), "kwestia kowala PL")
        store.ustaw(K("Miecz"), "Miecz PL")
        tlumaczenie.zapisz(self.root / "tlum", store)

        # Duplicate basenames via --cel without Package/ or LocalData/Patch/ context must fail clearly
        self.assertEqual(zbuduj_latke.main([
            "--indeks", str(self.root / "index"), "--magazyn", str(self.root / "tlum"),
            "--zh", str(zh), "--cel", str(a), "--cel", str(b), "--wyj", str(self.root / "bad_out"),
        ]), 1)

        out = self.root / "latka_duplikaty"
        rc = zbuduj_latke.main([
            "--indeks", str(self.root / "index"), "--magazyn", str(self.root / "tlum"),
            "--zh", str(zh),
            "--mapa", "Package/HD/oversea/locale/translate_words_map_en_diff", str(a),
            "--mapa", "LocalData/Patch/HD/oversea/locale/translate_words_map_en_diff", str(b),
            "--build-gry", "25906190",
            "--wyj", str(out),
        ])
        self.assertEqual(rc, 0)
        manifest = json.loads((out / "latka.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["build_gry"], "25906190")
        by_game = {entry["sciezka_w_grze"]: entry for entry in manifest["pliki"]}
        self.assertEqual(
            set(by_game),
            {
                "Package/HD/oversea/locale/translate_words_map_en_diff",
                "LocalData/Patch/HD/oversea/locale/translate_words_map_en_diff",
            },
        )
        self.assertNotEqual(by_game["Package/HD/oversea/locale/translate_words_map_en_diff"]["plik_latki"],
                            by_game["LocalData/Patch/HD/oversea/locale/translate_words_map_en_diff"]["plik_latki"])
        self.assertTrue((out / by_game["Package/HD/oversea/locale/translate_words_map_en_diff"]["plik_latki"]).is_file())
        self.assertTrue((out / by_game["LocalData/Patch/HD/oversea/locale/translate_words_map_en_diff"]["plik_latki"]).is_file())

    def test_audit_finds_new_texts_changed_scenes_and_feeds_the_supplement(self):
        zh2 = dict(ZH_ALL)
        en2 = dict(EN_ALL)
        zh2[T + 1] = "kwestia kowala, poprawiona"  # zmieniony tekst pod starym identyfikatorem
        zh2[T + 300] = "zupełnie nowy przedmiot"
        en2[T + 300] = "brand new item"
        tables = world()
        tables["stuff_items"] = [*tables["stuff_items"], (3, {"name": T + 300})]
        del tables["dialog_timelines.900"]
        wyciag.zbuduj(FakeBaza(tables), zh2, en2, self.root / "index2", {"opis": "wersja 2"}, log=lambda _text: None)
        new = indeks.wczytaj(self.root / "index2")
        store = tlumaczenie.Magazyn()
        store.ustaw(K("kwestia kowala"), "stary przekład")
        store.ustaw(K("Miecz"), "Miecz PL")
        report, slots = audyt_aktualizacji.porownaj(self.ix, new, store)
        self.assertEqual(slots, sorted([K("kwestia kowala, poprawiona"), K("zupełnie nowy przedmiot")]))
        self.assertEqual(report["teksty"]["nowe"], 2)
        self.assertEqual(report["teksty"]["usuniete"], 1)  # „dialog z innego projektu”; stara kwestia kowala żyje dalej pod innym id
        self.assertEqual(report["sceny"]["zmienione"], 1)
        self.assertEqual(report["sceny"]["lista_zmienionych"], [[100, 4, 1]])
        self.assertEqual(report["sceny"]["usuniete"], 1)
        self.assertEqual(report["teksty"]["nowe_wg_tabeli"]["stuff_items"], 1)
        self.assertEqual(report["przeklady"]["przetlumaczonych"], 2)
        self.assertIn("## Do tłumacza: 2 miejsc", audyt_aktualizacji.opis(report))
        manifest = buduj_paczke.zbuduj(new, self.root / "paczka2", wersja="2", data="2026-01-08", magazyn=store, tylko_sloty=set(slots), zip_=False)
        self.assertEqual(manifest["liczby"]["do_wpisania"], 2)
        self.assertEqual(manifest["liczby"]["scen"], 1)

    def test_audit_cli_reads_previous_index_from_git(self):
        repo = self.root / "repo"
        (repo / "index").mkdir(parents=True)
        for path in (self.root / "index").iterdir():
            (repo / "index" / path.name).write_bytes(path.read_bytes())

        def git(*args):
            subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)

        git("init", "-q")
        git("add", "-A")
        git("-c", "user.name=test", "-c", "user.email=test@example.invalid", "commit", "-q", "-m", "wersja 1")
        target = self.root / "z_gita"
        target.mkdir(exist_ok=True)
        extracted = audyt_aktualizacji.indeks_z_gita("HEAD", target, repo)
        self.assertEqual(indeks.wczytaj(extracted).manifest["wejscia"]["opis"], "wersja 1")
        with self.assertRaises(audyt_aktualizacji.AudytError):
            audyt_aktualizacji.indeks_z_gita("nie-ma-takiego-commita", target, repo)
        out = self.root / "audyt"
        code = audyt_aktualizacji.main(["--stary", str(extracted), "--nowy", str(self.root / "index"), "--wyj", str(out)])
        self.assertEqual(code, 0)
        self.assertEqual((out / "nowe_sloty.txt").read_text(encoding="utf-8"), "")
        self.assertEqual(json.loads((out / "audyt.json").read_text(encoding="utf-8"))["do_tlumacza"], 0)


    def test_audit_only_with_en_surfaces_newly_localized_zh_only_entries(self):
        zh1 = dict(ZH_ALL)
        en1 = dict(EN_ALL)
        zh1[T + 900] = "niewydany dotąd wpis"
        tables = world()
        tables["stuff_items"] = [*tables["stuff_items"], (9, {"name": T + 900})]
        wyciag.zbuduj(FakeBaza(tables), zh1, en1, self.root / "ix_zh_only_old", {"opis": "przed en"}, log=lambda _text: None)
        old_ix = indeks.wczytaj(self.root / "ix_zh_only_old")

        en2 = dict(en1)
        en2[T + 900] = "Released globally"
        wyciag.zbuduj(FakeBaza(tables), zh1, en2, self.root / "ix_zh_only_new", {"opis": "po en"}, log=lambda _text: None)
        new_ix = indeks.wczytaj(self.root / "ix_zh_only_new")

        # Bez flagi --tylko-z-en wpis był już znany w indeksie
        _, raw_slots = audyt_aktualizacji.porownaj(old_ix, new_ix, tylko_z_en=False)
        self.assertEqual(raw_slots, [])
        # Z flagą --tylko-z-en staje się nowym tekstem do patcha tłumaczenia
        report, en_slots = audyt_aktualizacji.porownaj(old_ix, new_ix, tylko_z_en=True)
        self.assertEqual(en_slots, [K("niewydany dotąd wpis")])
        self.assertTrue(report["tylko_z_en"])
        self.assertIn("--tylko-z-en", audyt_aktualizacji.opis(report))

        manifest = buduj_paczke.zbuduj(
            new_ix,
            self.root / "paczka_patch_en",
            wersja="2",
            data="2026-01-10",
            tylko_sloty=set(en_slots),
            tylko_z_en=True,
            zip_=False,
        )
        self.assertEqual(manifest["liczby"]["do_wpisania"], 1)
        self.assertTrue(manifest["kontrola"]["zgodne"])

    def test_latka_testowa_builds_complete_windows_zip_for_ui_and_diacritics(self):
        maps = self.root / "mapy_ui"
        pkg_en = maps / "pkg_en"
        patch_diff = maps / "patch_diff"
        zh = maps / "zh"
        maps.mkdir()
        zh.write_bytes(
            container(
                [
                    table([
                        (T + 1, "设置".encode()),
                        (T + 2, "音频".encode()),
                        (T + 3, "退出".encode()),
                        (T + 10, "穷途末路".encode()),
                        (T + 11, "尚有一饮入喉".encode()),
                        (T + 12, "如何 ".encode()),  # spacja końcowa jak w grze
                        (T + 13, "淡".encode()),
                        (T + 14, "平淡无奇".encode()),  # inne ZH z takim samym EN "Bland." — nie powinno się zmienić
                    ])
                ],
                with_metadata=True,
            )
        )
        pkg_en.write_bytes(
            container(
                [
                    table([
                        (T + 1, b"Settings"),
                        (T + 2, b"Audio"),
                        (T + 10, b"Even at the end of the road,"),
                        (T + 11, b"a drink to wet your throat."),
                        (T + 12, b"Well? How is it?"),
                        (T + 13, b"Bland."),
                        (T + 14, b"Bland."),
                        (T + 99, b"Unchanged"),
                    ])
                ],
                with_metadata=True,
            )
        )
        patch_diff.write_bytes(container([table([(T + 3, b"Exit")])], with_metadata=True))

        out_zip = self.root / "WWM_LATKA_TEST_PL.zip"
        rc = latka_testowa.main([
            "--indeks", str(self.root / "index"),
            "--zh", str(zh),
            "--mapa", "Package/HD/oversea/locale/translate_words_map_en", str(pkg_en),
            "--mapa", "LocalData/Patch/HD/oversea/locale/translate_words_map_en_diff", str(patch_diff),
            "--build-gry", "25906190",
            "--wyj-zip", str(out_zip),
        ])
        self.assertEqual(rc, 0)
        self.assertTrue(out_zip.is_file())
        self.assertFalse((self.root / "tlumaczenie").exists())
        from zipfile import ZipFile
        with ZipFile(out_zip) as z:
            names = set(z.namelist())
            for req in ("CZYTAJ_TO.txt", "ZAINSTALUJ.bat", "PRZYWROC.bat", "SPRAWDZ_STAN.bat", "instaluj_latke.ps1", "latka.json"):
                self.assertIn(req, names)
            manifest = json.loads(z.read("latka.json").decode("utf-8"))
            self.assertEqual(manifest["build_gry"], "25906190")
            self.assertEqual(len(manifest["pliki"]), 2)
            # Check repacked maps kept Unchanged, non-prologue Bland., and inserted Polish diacritics in UI + prologue
            patched_pkg = self.root / "out_pkg_en"
            patched_pkg.write_bytes(z.read("pliki/Package/HD/oversea/locale/translate_words_map_en"))
            got, _ = mapa_tekstow.wczytaj_warstwe(patched_pkg)
            self.assertIn("ą ć ę ł ń ó ś ź ż", got[T + 1])
            self.assertIn("Ą Ć Ę Ł Ń Ó Ś Ź Ż", got[T + 2])
            self.assertIn("Nawet u kresu drogi", got[T + 10])
            self.assertIn("łyk trunku zwilży gardło", got[T + 11])
            self.assertIn("I jak? Smakuje", got[T + 12])
            self.assertIn("Mdłe", got[T + 13])
            self.assertEqual(got[T + 14], "Bland.")
            self.assertEqual(got[T + 99], "Unchanged")

        # Tryb --zakres prolog zmienia tylko kwestie prologu i zostawia UI nietknięte
        prolog_zip = self.root / "WWM_LATKA_TEST_PROLOG.zip"
        report_prolog = latka_testowa.zbuduj_paczke_testowa(
            indeks_dir=self.root / "index",
            zh_paths=[zh],
            cel_paths=[],
            mapa_pairs=[("Package/HD/oversea/locale/translate_words_map_en", pkg_en)],
            wyj_zip=prolog_zip,
            zakres="prolog",
        )
        self.assertEqual(report_prolog["zakres"], "prolog")
        self.assertEqual(report_prolog["dopasowane_ui"], {})
        self.assertIn("Even at the end of the road,", report_prolog["dopasowane_prolog"])
        with ZipFile(prolog_zip) as z:
            p = self.root / "out_prolog_only"
            p.write_bytes(z.read("pliki/Package/HD/oversea/locale/translate_words_map_en"))
            got_p, _ = mapa_tekstow.wczytaj_warstwe(p)
            self.assertEqual(got_p[T + 1], "Settings")
            self.assertIn("Nawet u kresu drogi", got_p[T + 10])

    def test_patcher_separates_story_collision_variants_without_leaking(self):
        t_cut = T + 800
        t_skill_1 = T + 801
        t_skill_2 = T + 802
        zh_dict = {**ZH_ALL, t_cut: "十步杀一人", t_skill_1: "十步杀一人", t_skill_2: "十步杀一人"}
        en_dict = {**EN_ALL, t_cut: "Cut them down, left and right", t_skill_1: "Relentless Advance", t_skill_2: "Relentless Advance"}
        custom = world()
        custom["text_msg"] = [(590438, {"content": t_cut})]
        custom["buff"] = [*custom["buff"], (10, {"buff_name": t_skill_1}), (11, {"buff_name": t_skill_2})]
        ix_dir = self.root / "ix_col"
        wyciag.zbuduj(FakeBaza(custom), zh_dict, en_dict, ix_dir, {}, log=lambda _text: None)

        maps = self.root / "mapy_col"
        maps.mkdir(exist_ok=True)
        zh_p = maps / "zh"
        en_p = maps / "en"
        zh_p.write_bytes(container([table([(t_cut, "十步杀一人".encode()), (t_skill_1, "十步杀一人".encode())])], with_metadata=True))
        en_p.write_bytes(container([table([(t_cut, b"Cut them down, left and right"), (t_skill_1, b"Relentless Advance")])], with_metadata=True))

        # 1. Gdy przetłumaczona jest tylko umiejętność, cutscena zostaje po angielsku (nie dostaje nazwy skilla).
        mag_partial = self.root / "mag_col_1"
        st1 = tlumaczenie.Magazyn()
        st1.ustaw(K("十步杀一人"), "Bezlitosne natarcie")
        tlumaczenie.zapisz(mag_partial, st1)
        out1 = self.root / "latka_col_1"
        self.assertEqual(zbuduj_latke.main(["--indeks", str(ix_dir), "--magazyn", str(mag_partial), "--zh", str(zh_p), "--cel", str(en_p), "--wyj", str(out1)]), 0)
        got1, _ = mapa_tekstow.wczytaj_warstwe(out1 / "en")
        self.assertEqual(got1[t_skill_1], "Bezlitosne natarcie")
        self.assertEqual(got1[t_cut], "Cut them down, left and right")

        # 2. Gdy przetłumaczone są oba warianty, każdy idzie na swoje właściwe miejsce.
        mag_full = self.root / "mag_col_2"
        st1.ustaw(mapa_tekstow.klucz_wariantu("十步杀一人", "Cut them down, left and right"), "Ścinam ich na lewo i prawo")
        tlumaczenie.zapisz(mag_full, st1)
        out2 = self.root / "latka_col_2"
        self.assertEqual(zbuduj_latke.main(["--indeks", str(ix_dir), "--magazyn", str(mag_full), "--zh", str(zh_p), "--cel", str(en_p), "--wyj", str(out2)]), 0)
        got2, _ = mapa_tekstow.wczytaj_warstwe(out2 / "en")
        self.assertEqual(got2[t_skill_1], "Bezlitosne natarcie")
        self.assertEqual(got2[t_cut], "Ścinam ich na lewo i prawo")

    def test_latka_testowa_handles_rebuilt_prologue_and_collision_variants(self):
        t_cut = T + 850
        t_skill_1 = T + 851
        t_skill_2 = T + 852
        t_prolog = T + 853
        zh_dict = {
            **ZH_ALL,
            t_cut: "十步杀一人",
            t_skill_1: "十步杀一人",
            t_skill_2: "十步杀一人",
            t_prolog: "是啊 来抓你",
        }
        en_dict = {
            **EN_ALL,
            t_cut: "Cut them down, left and right",
            t_skill_1: "Relentless Advance",
            t_skill_2: "Relentless Advance",
            t_prolog: "That's right, here to take you in.",
        }
        custom = world()
        custom["text_msg"] = [(590438, {"content": t_cut}), (590337, {"content": t_prolog})]
        custom["buff"] = [*custom["buff"], (10, {"buff_name": t_skill_1}), (11, {"buff_name": t_skill_2})]
        ix_dir = self.root / "ix_latka_v2"
        wyciag.zbuduj(FakeBaza(custom), zh_dict, en_dict, ix_dir, {}, log=lambda _text: None)

        maps = self.root / "mapy_latka_v2"
        maps.mkdir(exist_ok=True)
        zh_p = maps / "zh"
        en_p = maps / "en"
        zh_p.write_bytes(
            container(
                [table([(t_cut, "十步杀一人".encode()), (t_skill_1, "十步杀一人".encode()), (t_prolog, "是啊 来抓你".encode())])],
                with_metadata=True,
            )
        )
        en_p.write_bytes(
            container(
                [table([(t_cut, b"Cut them down, left and right"), (t_skill_1, b"Relentless Advance"), (t_prolog, b"That's right, here to take you in.")])],
                with_metadata=True,
            )
        )
        out_zip = self.root / "WWM_LATKA_TEST_V2.zip"
        rep = latka_testowa.zbuduj_paczke_testowa(
            indeks_dir=ix_dir,
            zh_paths=[zh_p],
            cel_paths=[],
            mapa_pairs=[("Package/HD/oversea/locale/translate_words_map_en", en_p)],
            wyj_zip=out_zip,
            zakres="prolog",
        )
        self.assertTrue(rep["ok"])
        with zipfile.ZipFile(out_zip) as z:
            p = self.root / "out_latka_en"
            p.write_bytes(z.read("pliki/Package/HD/oversea/locale/translate_words_map_en"))
            got, _ = mapa_tekstow.wczytaj_warstwe(p)
        self.assertIn("Ścinam ich na lewo i prawo", got[t_cut])
        self.assertIn("Zgadza się — przyszliśmy cię pojmać", got[t_prolog])
        self.assertEqual(got[t_skill_1], "Relentless Advance")


if __name__ == "__main__":
    unittest.main()
