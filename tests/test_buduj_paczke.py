from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from collections import Counter
from pathlib import Path

from tests.test_sceny_z_bazy import group, rows, span, text_track
from tests.test_wyciag_indeks import EN, ZH, K, T, tables
from tests.test_zrodla_tekstow import FakeBaza
from tools import buduj_paczke, format_paczki, indeks, tlumaczenie, wyciag

ZH_EXTRA = {
    T + 200: "scena obok numerem",
    T + 201: "pogawędka tła",
    T + 202: "druga pogawędka",
    T + 203: "trzecia pogawędka",
    T + 204: "dialog z innego projektu",
    T + 205: "kwestia kowala",  # ten sam tekst co w scenie 100, inny identyfikator
    T + 206: "Efekt #Y{0}#E\nna dwie linie",
    T + 207: "  ",  # sam odstęp: nie ma czego tłumaczyć
}
EN_EXTRA = {T + 200: "next by number", T + 201: "idle talk", T + 206: "Effect #Y{0}#E\nin two lines"}


def scene(text_ids, project="projekt-testowy"):
    data = rows([group("gawędziarz", 3, 0, "", [text_track([span(text, float(n), n) for n, text in enumerate(text_ids)])])])
    data["project_info"] = {"project_name": project}
    return list(data.items())


def world() -> dict:
    data = tables()
    data["dialog_timelines.103"] = scene([T + 200, T + 205])
    for number, text in ((500, T + 201), (501, T + 202), (502, T + 203)):
        data[f"dialog_timelines.{number}"] = scene([text], "tlo")
    data["dialog_timelines.900"] = scene([T + 204], "inny")
    data["spaces.s7.spawn_kit"] = [(1, {"self_talk_dialogs_list": [500, 501, 502]})]
    data["buff"] = [(1, {"buff_name": T + 20, "buff_detail": T + 206}), (2, {"buff_name": T + 207})]
    return data


class PackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="wwm-paczka-")
        root = Path(cls.temp.name)
        wyciag.zbuduj(FakeBaza(world()), {**ZH, **ZH_EXTRA}, {**EN, **EN_EXTRA}, root / "index", {"opis": "dane wymyślone"}, log=lambda _text: None)
        cls.ix = indeks.wczytaj(root / "index")
        cls.out = root / "paczka"
        cls.manifest = buduj_paczke.zbuduj(cls.ix, cls.out, wersja="1", data="2026-01-01")
        cls.files = {path.name: path.read_text(encoding="utf-8") for folder in ("sceny", "widoki") for path in (cls.out / folder).glob("*.md")}

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def entries(self, files=None):
        return [entry for text in (files or self.files).values() for entry in format_paczki.czytaj_wpisy(text)]

    def test_every_text_has_exactly_one_place_for_translation(self):
        slots = Counter(entry.klucz for entry in self.entries())
        expected = (set(self.ix.teksty) - {K("  ")}) | {"@" + ident for ident in self.ix.warianty}
        self.assertIn("(pusty tekst — nie ma czego tłumaczyć)", self.files["04_walka_i_umiejetnosci_01.md"])
        self.assertEqual(set(slots), expected)
        self.assertEqual(max(slots.values()), 1)
        self.assertEqual(self.manifest["liczby"]["do_wpisania"], len(expected))

    def test_scene_shows_speakers_variants_choices_and_context(self):
        text = self.files["01_watek-glowny_rozdzial-1_01.md"]
        self.assertIn("#### Scena 1/6 — dialog 100", text)
        self.assertIn("### Zadanie 1 — Pierwsze zadanie (First quest)", text)
        self.assertIn("- cel: Idź do kowala", text)
        self.assertIn("  - Kowal (Smith) — tytuł: Mistrz kuźni — opis: Kowal z Kuźni, mrukliwy", text)
        self.assertIn("- miejsce: Kuźnia [przestrzeń 7]", text)
        self.assertIn("1. [Kwestia — Kowal (Smith)] kwestia kowala\n   klucz: " + K("kwestia kowala") + "\n   EN: smith line\n   PL:", text)
        self.assertIn(f"[Kwestia — gracz, wariant: bohater] wersja bohatera\n   klucz: @{T + 3:016x}\n   EN: male version", text)
        self.assertIn(f"[Kwestia — gracz, wariant: bohaterka] wersja bohatera\n   klucz: @{T + 4:016x}\n   EN: female version", text)
        self.assertIn("— wybór gracza po tej scenie (pytanie 9, krok 1): Rozmowa", text)
        self.assertIn("[Wybór gracza 1] Tak\n   klucz: " + K("Tak") + "\n   prowadzi do: dialog 101", text)
        self.assertIn("#### Przerywnik 300 — przy przyjęciu zadania", text)

    def test_scene_placed_by_number_says_so_and_repeats_point_to_first_place(self):
        text = self.files["01_watek-glowny_rozdzial-1_01.md"]
        self.assertIn("- zadanie: brak wpisu w tabelach zadań — scena ułożona według numeru, za dialogiem 100", text)
        self.assertIn("2. [Kwestia — gawędziarz*] kwestia kowala\n   (powtórzenie — tłumaczysz raz: 01_watek-glowny_rozdzial-1_01.md, scena 1, element 1)", text)

    def test_background_and_project_parts(self):
        self.assertIn("## Miejsce: Kuźnia [przestrzeń 7] — 3 scen", self.files["90_rozmowy-tla_01.md"])
        self.assertIn("## Projekt inny — 1 scen", self.files["80_dialogi-wg-projektow_01.md"])
        self.assertEqual(self.manifest["uklad"]["scen_tla"], 3)
        self.assertEqual(self.manifest["uklad"]["w_tym_wg_numeracji"], 1)

    def test_views_group_by_table_with_row_context_limits_and_tokens(self):
        items = self.files["03_przedmioty_01.md"]
        self.assertIn("## stuff_items — przedmioty: nazwa, opis, opis fabularny", items)
        self.assertIn("[stuff_items · describe_str · wiersz 1] Opis miecza\n   klucz: " + K("Opis miecza") + "\n   dotyczy: Miecz (Sword)\n   limit: do 17 znaków\n   EN: Sword description", items)
        self.assertIn("użycia w grze: 2 identyfikatorów", items)
        effects = self.files["04_walka_i_umiejetnosci_01.md"]
        self.assertIn("Efekt #Y{0}#E\\nna dwie linie", effects)
        self.assertIn("   tokeny: zachowaj dokładnie: #Y, {0}, #E", effects)
        self.assertIn("EN: (to jest tekst źródłowy — chińskiej wersji nie ma w danych)", self.files["10_bez_zrodla_01.md"])

    def test_readme_and_lists_report_real_numbers(self):
        readme = (self.out / "README.md").read_text(encoding="utf-8")
        self.assertIn("wersja 1", readme)
        self.assertIn(f"razem w pakiecie **{self.manifest['liczby']['do_wpisania']}**", readme)
        self.assertIn("dane wymyślone", readme)
        listing = (self.out / "sceny" / "spis-scen.tsv").read_text(encoding="utf-8").splitlines()
        self.assertEqual(listing[1].split("\t")[:6], ["1", "100", "01_watek-glowny_rozdzial-1_01.md", "zadania", "1", "zakonczenie"])
        self.assertEqual(len(listing), 1 + self.manifest["liczby"]["scen"])
        self.assertIn("| `1` | Pierwsze zadanie (First quest) | Idź do kowala |", (self.out / "sceny" / "spis-misji.md").read_text(encoding="utf-8"))

    def test_archives_hold_the_same_files_and_are_reproducible(self):
        for name in ("sceny", "widoki"):
            with zipfile.ZipFile(self.out / f"{name}.zip") as archive:
                self.assertEqual(sorted(archive.namelist()), sorted(path.name for path in (self.out / name).iterdir()))
        with tempfile.TemporaryDirectory(prefix="wwm-paczka-") as temp:
            again = buduj_paczke.zbuduj(self.ix, Path(temp), wersja="1", data="2026-01-01")
            self.assertEqual(again["archiwa"], self.manifest["archiwa"])
        manifest = json.loads((self.out / "paczka.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["format"], "wwm-paczka-v1")
        self.assertEqual(manifest["rodzaj"], "pełny")
        with zipfile.ZipFile(self.out / "paczka_dla_tlumacza_wwm_v1.zip") as archive:
            self.assertEqual(archive.namelist(), ["README.md", "sceny.zip", "widoki.zip"])

    def test_self_check_reads_the_package_like_the_importer(self):
        check = self.manifest["kontrola"]
        self.assertTrue(check["zgodne"])
        self.assertEqual((check["powtorzonych"], check["nieznanych"], check["brakujacych"]), (0, 0, 0))
        self.assertEqual(check["miejsc_pl"], self.manifest["liczby"]["do_wpisania"])
        # dopisany ręcznie drugi wpis tego samego klucza psuje kontrolę
        generator = buduj_paczke.Generator(self.ix)
        with tempfile.TemporaryDirectory(prefix="wwm-paczka-") as temp:
            buduj_paczke.zbuduj(self.ix, Path(temp), wersja="1", data="2026-01-01", zip_=False)
            path = Path(temp) / "widoki" / "03_przedmioty_01.md"
            path.write_text(path.read_text(encoding="utf-8") + "9. [x] Miecz\n   klucz: " + K("Miecz") + "\n   PL:\n", encoding="utf-8")
            broken = buduj_paczke.kontrola(generator, Path(temp))
        self.assertFalse(broken["zgodne"])
        self.assertEqual(broken["powtorzonych"], 1)

    def test_supplement_contains_only_new_texts_in_context(self):
        new = {K("kwestia kowala"), K("Opis miecza")}
        store = tlumaczenie.Magazyn()
        store.ustaw(K("kwestia gracza"), "już po polsku")
        with tempfile.TemporaryDirectory(prefix="wwm-paczka-") as temp:
            manifest = buduj_paczke.zbuduj(self.ix, Path(temp), wersja="2", data="2026-01-02", magazyn=store, tylko_sloty=new, zip_=False)
            files = {path.name: path.read_text(encoding="utf-8") for folder in ("sceny", "widoki") for path in (Path(temp) / folder).glob("*.md")}
            readme = (Path(temp) / "README.md").read_text(encoding="utf-8")
        self.assertEqual(manifest["rodzaj"], "uzupełniający")
        self.assertTrue(manifest["kontrola"]["zgodne"])
        self.assertEqual({entry.klucz for entry in self.entries(files)}, new)
        scenes = "".join(text for name, text in files.items() if name[:2] in ("01", "80", "90"))
        self.assertIn("dialog 100", scenes)
        self.assertNotIn("dialog 900", scenes)
        self.assertIn("PL (już jest): już po polsku", scenes)
        self.assertIn("(tekst z wcześniejszego pakietu — tu nic nie wpisuj)", scenes)
        self.assertEqual(sorted(name for name in files if name[:2] == "03"), ["03_przedmioty_01.md"])
        self.assertNotIn("[stuff_items · name · wiersz 1] Miecz", files["03_przedmioty_01.md"])
        self.assertIn("pakiet uzupełniający", readme)

    def test_only_with_en_skips_zh_only_entries_and_keeps_zh_source_with_en_only_fallback(self):
        with tempfile.TemporaryDirectory(prefix="wwm-paczka-en-") as temp:
            manifest = buduj_paczke.zbuduj(self.ix, Path(temp), wersja="2", data="2026-01-03", tylko_z_en=True, zip_=False)
            files = {path.name: path.read_text(encoding="utf-8") for folder in ("sceny", "widoki") for path in (Path(temp) / folder).glob("*.md")}
            readme = (Path(temp) / "README.md").read_text(encoding="utf-8")
        self.assertTrue(manifest["tylko_z_en"])
        self.assertEqual(manifest["rodzaj"], "pełny")
        self.assertTrue(manifest["kontrola"]["zgodne"])
        slots = {entry.klucz for entry in self.entries(files)}
        expected = {
            key for key, text in self.ix.teksty.items()
            if text.zrodlo.strip() and (text.en is not None or text.z_en)
        } | {"@" + ident for ident in self.ix.warianty}
        self.assertEqual(slots, expected)
        self.assertNotIn(K("druga pogawędka"), slots)
        self.assertNotIn(K("dialog z innego projektu"), slots)
        self.assertIn(K("scena obok numerem"), slots)
        self.assertIn("--tylko-z-en", readme)
        # scena tła z samymi tekstami bez EN (501, 502) została pominięta, a ta z EN (500) została
        bg = files["90_rozmowy-tla_01.md"]
        self.assertIn("dialog 500", bg)
        self.assertNotIn("dialog 501", bg)


class WriterTests(unittest.TestCase):
    def test_series_is_split_below_the_limit_and_headings_continue(self):
        with tempfile.TemporaryDirectory(prefix="wwm-paczka-") as temp:
            writer = buduj_paczke.Pisarz(Path(temp), "seria", "Tytuł", ["wstęp"], limit=220)
            writer.naglowek(2, ["## Grupa", "- opis grupy"])
            names = [writer.blok([f"blok {number} " + "x" * 60], scen=1, elementow=1) for number in range(4)]
            files = writer.koniec()
            self.assertGreater(len(files), 1)
            self.assertEqual(names[0], "seria_01.md")
            first = (Path(temp) / "seria_01.md").read_text(encoding="utf-8")
            second = (Path(temp) / "seria_02.md").read_text(encoding="utf-8")
            self.assertTrue(first.startswith("# Tytuł — część 1\n\nwstęp\n\n## Grupa\n- opis grupy\n"))
            self.assertIn("## Grupa (ciąg dalszy)", second)
            self.assertNotIn("- opis grupy", second)
            self.assertEqual(sum(entry["scen"] for entry in files), 4)

    def test_categories(self):
        self.assertEqual(buduj_paczke.kategoria("stuff_items"), "03_przedmioty")
        self.assertEqual(buduj_paczke.kategoria("text_msg__grey"), "07_komunikaty")
        self.assertEqual(buduj_paczke.kategoria("spaces.*.region"), "05_swiat_i_miejsca")
        self.assertEqual(buduj_paczke.kategoria("world_view_person_event"), "00_postacie")
        self.assertEqual(buduj_paczke.kategoria("world_view_shili_data"), "06_encyklopedia_i_ksiegi")
        self.assertEqual(buduj_paczke.kategoria("zupelnie_nieznana"), "09_pozostale")


class V2CutscenesAndExclusionsTests(unittest.TestCase):
    def _build_v2_world(self):
        base = world()
        zh = {**ZH, **ZH_EXTRA}
        en = {**EN, **EN_EXTRA}
        extra_zh = {
            T + 700: "伊刀 别动",  # 590291 PROLOG
            T + 701: "小子 快醒来啊",  # 590453 M
            T + 702: "小妮子 快醒来啊",  # 590454 F
            T + 703: "新来的！",  # intro
            T + 704: "花果山上来了那一批灯",  # film
            T + 705: "劫后重逢",  # replay name
            T + 706: "未配 zadań przerywnik",  # cutscenes bez zadania
            T + 707: "bot nick 3220001",  # bot nick -> wykluczony
            T + 708: "测试文本123",  # placeholder -> wykluczony
            T + 709: "关注“燕云十六声”官方公众号",  # promo WeChat -> wykluczone
            T + 710: "网络连接失败，请稍后重试",  # blad sieci -> wykluczony
            T + 711: "klucz z programmer",  # programmer_text_msg -> wykluczony
            T + 712: "Press {} for tutorial",  # guider_task -> wykluczony
            T + 713: "Auto-Skip Setting",  # setting_items -> wykluczony
            T + 714: "Osiągnięcie gracza",  # ac_raw -> zostaje
            T + 715: "Tekst 3D fabularny",  # gameplay_space_3d_ui_config -> zostaje
            T + 716: "stary grey 590291",  # text_msg__grey 590291 rozny od text_msg -> wykluczony
        }
        extra_en = {
            T + 700: "Stay put.",
            T + 701: "Kid, wake up!",
            T + 702: "Girlie, wake up!",
            T + 703: "You there, the newcomer!",
            T + 704: "To Huaguo Mountain...",
            T + 705: "Reunion After the Storm",
            T + 706: "Standalone cutscene board",
            T + 707: "ShadowBot",
            T + 708: "Test Text 123",
            T + 709: "Follow Official WeChat Account",
            T + 710: "Network error, connection failed",
            T + 711: "Debug programmer text",
            T + 712: "Press {} for tutorial",
            T + 713: "Auto-Skip Setting",
            T + 714: "Player Achievement",
            T + 715: "Story 3D Text",
            T + 716: "Old grey subtitle",
        }
        zh.update(extra_zh)
        en.update(extra_en)
        base["text_msg"] = [
            (590291, {"content": T + 700}),
            (590453, {"content": T + 701}),
            (590454, {"content": T + 702}),
            (3220001, {"content": T + 707}),
            (100, {"content": T + 708}),
            (101, {"content": T + 709}),
            (102, {"content": T + 710}),
        ]
        base["text_msg__grey"] = [(590291, {"content": T + 716})]
        base["sound_data"] = [(1, {"audio_name": "vo_shenxiandu_npc_105", "text": "伊刀 别动"})]
        base["wds_oneday_intro_cutscene_data"] = [(10001, {"id": 10001, "time": 1.0, "duration": 3.0, "speaker": 2, "text": T + 703})]
        base["entry_collect_movie_subtitle_data"] = [(1, [{"dialog_no": 1, "id": 101, "time": 1.0, "duration": 3.0, "text": T + 704}])]
        base["task_cutscene_replay"] = [(32208, {"no": 32208, "task_no": 1, "group": 5, "name": T + 705})]
        base["cutscenes"] = [*base["cutscenes"], (302, {"no": 302, "content": T + 706})]
        base["programmer_text_msg"] = [(1, {"content": T + 711})]
        base["guider_task"] = [(1, {"guide_desc": T + 712}), (2, {"guide_desc": T + 30})]  # T+30 chronione przez zadania/sceny
        base["setting_items"] = [(1, {"name": T + 713})]
        base["ac_raw"] = [(1, {"name": T + 714})]
        base["gameplay_space_3d_ui_config"] = [(1, {"text": T + 715})]
        return base, zh, en

    def test_cutscenes_section_and_v2_exclusions_pass_control_and_preserve_story(self):
        data, zh, en = self._build_v2_world()
        with tempfile.TemporaryDirectory(prefix="wwm-v2-paczka-") as temp:
            root = Path(temp)
            wyciag.zbuduj(FakeBaza(data), zh, en, root / "index", {"opis": "test v2"}, log=lambda _text: None)
            ix = indeks.wczytaj(root / "index")

            # Domyślny tryb v2: cutsceny/ + wykluczenia śmieci
            manifest = buduj_paczke.zbuduj(ix, root / "out_v2", wersja="2", data="2026-11-11", tylko_z_en=True)
            self.assertTrue(manifest["kontrola"]["zgodne"])
            self.assertEqual(
                manifest["wykluczenia"],
                {"boty_nicki": 1, "stare_grey_cutsceny": 1, "tabele_meta": 3, "placeholdery_testy": 1, "promo_beta_cn": 1, "bledy_sieciowe": 1},
            )
            with zipfile.ZipFile(root / "out_v2" / "paczka_dla_tlumacza_wwm_v2.zip") as z:
                self.assertEqual(z.namelist(), ["README.md", "sceny.zip", "cutsceny.zip", "widoki.zip"])

            cut_files = {p.name: p.read_text(encoding="utf-8") for p in (root / "out_v2" / "cutsceny").glob("*.md")}
            self.assertIn("01_napisy_cutscen_01.md", cut_files)
            self.assertIn("02_intro_i_filmy_01.md", cut_files)
            self.assertIn("03_plansze_i_streszczenia_01.md", cut_files)

            napisy_md = cut_files["01_napisy_cutscen_01.md"]
            self.assertIn("PROLOG (wiersze 590291–590291", napisy_md)
            self.assertIn("vo_shenxiandu_npc_105 · mówca: 伊刀 (Yi Dao)", napisy_md)
            self.assertIn("wariant płci: bohater (męski)", napisy_md)
            self.assertIn("wariant płci: bohaterka (żeński)", napisy_md)
            self.assertIn("intro · id 10001 · 1.0s–4.0s · mówca 2", cut_files["02_intro_i_filmy_01.md"])
            self.assertIn("film 1 · id 101 · 1.0s–4.0s", cut_files["02_intro_i_filmy_01.md"])
            self.assertIn("task_cutscene_replay · 32208 · Nazwa powtórki", cut_files["03_plansze_i_streszczenia_01.md"])
            self.assertIn("cutscenes · 302 · Plansza przerywnika", cut_files["03_plansze_i_streszczenia_01.md"])

            widoki_md = "\n".join(p.read_text(encoding="utf-8") for p in (root / "out_v2" / "widoki").glob("*.md"))
            self.assertIn("Osiągnięcie gracza", widoki_md)
            self.assertIn("Tekst 3D fabularny", widoki_md)
            for excluded in ("ShadowBot", "Test Text 123", "Follow Official WeChat Account", "Network error", "Debug programmer text", "Press {} for tutorial", "Auto-Skip Setting", "Old grey subtitle"):
                self.assertNotIn(excluded, widoki_md)

            readme = (root / "out_v2" / "README.md").read_text(encoding="utf-8")
            self.assertIn("cutsceny.zip", readme)
            self.assertIn("losowych nicków botów/graczy", readme)

            # Tryb --wszystko zachowuje też pozycje wykluczone
            manifest_all = buduj_paczke.zbuduj(ix, root / "out_all", wersja="2", data="2026-11-11", wszystko=True, zip_=False)
            self.assertTrue(manifest_all["kontrola"]["zgodne"])
            self.assertEqual(manifest_all["wykluczenia"], {})


if __name__ == "__main__":
    unittest.main()
