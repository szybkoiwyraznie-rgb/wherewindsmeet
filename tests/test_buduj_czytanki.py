from __future__ import annotations

import json
import re
import tempfile
import unittest
import zipfile
from pathlib import Path

from tests.test_buduj_paczke import scene
from tests.test_potok_tlumaczenia import fill
from tests.test_sceny_z_bazy import group, rows, span, text_track
from tests.test_wyciag_indeks import EN, ZH, K, T, tables
from tests.test_zrodla_tekstow import FakeBaza
from tools import buduj_czytanki, buduj_paczke, indeks, mapa_tekstow, tlumaczenie, wyciag

U = T + 1000

ZH_CZYTANKI = {
    **ZH,
    U + 1: "Drugi rozdział",
    U + 2: "Drugie zadanie",
    U + 3: "Kwestia z drugiego rozdziału",
    U + 4: "Druga historia postaci",
    U + 5: "Streszczenie pierwszego rozdziału",
    U + 6: "Księga Pierwszych Dni",
    U + 7: "Mistrz Chen",
    U + 8: "Treść pierwszej strony księgi z testu.",
    U + 9: "Sztuka Żelaznego Deszczu",
    U + 10: "Bardzo długa technika wymagająca długiego opisu aby sprawdzić zawijanie wierszy w tabeli markdown bez użycia znaczników HTML oraz kontrolę maksymalnej szerokości stu dwudziestu znaków w edytorze tekstu.",
    U + 11: "Szlachetna Zbroja",
    U + 12: "Chroni przed wiatrem północy.",
    U + 13: "Bitwa pod Kaifengiem",
    U + 14: "960 n.e.",
    U + 15: "Kronika kompendium",
    U + 16: "Opis hasła w kompendium.",
    U + 17: "Zapisek z drogi",
    U + 18: "Opowieść zasłyszana w gospodzie.",
    U + 19: "Sztuka Wewnętrzna Spokoju",
    U + 20: "Zwiększa siłę ducha.",
    U + 21: "Technika Jianghu Krok Wiatru",
    U + 22: "Pozwala biec po wodzie.",
    U + 23: "Poszlaka z listu",
    U + 24: "Znaleziono w skrzyni kowala.",
    U + 25: "Zadanie poboczne na targu",
    U + 26: "Zagadaj kupca na targu.",
    U + 27: "Dialog na targu",
    U + 28: "Czego sobie życzysz, wędrowcze?",
    U + 30: "小子，快醒醒！",
    U + 31: "小妮子，快醒醒！",
    U + 32: "Nieznana fraza bez polskiego przekładu",
}

EN_CZYTANKI = {
    **EN,
    U + 1: "Chapter Two EN",
    U + 2: "Second Quest EN",
    U + 3: "Second chapter dialogue EN",
    U + 4: "Second biography entry EN",
    U + 5: "Chapter one recap EN",
    U + 6: "Book of First Days EN",
    U + 7: "Master Chen EN",
    U + 8: "First page content EN",
    U + 9: "Iron Rain Art EN",
    U + 10: "Long skill description EN",
    U + 11: "Noble Armor EN",
    U + 12: "Protects from cold EN",
    U + 13: "Battle of Kaifeng EN",
    U + 14: "960 CE",
    U + 15: "Manual Entry EN",
    U + 16: "Manual description EN",
    U + 17: "Road Tale EN",
    U + 18: "Tavern story EN",
    U + 19: "Calm Heart Xinfa EN",
    U + 20: "Increases spirit EN",
    U + 21: "Wind Step Jianghu EN",
    U + 22: "Run on water EN",
    U + 23: "Letter Clue EN",
    U + 24: "Found in smith chest EN",
    U + 25: "Market Side Quest EN",
    U + 26: "Talk to merchant EN",
    U + 28: "What do you want traveler EN",
    U + 30: "Wake up, boy! EN",
    U + 31: "Wake up, girl! EN",
    U + 32: "Untranslated English Line Sentinel",
}


def rich_world() -> dict:
    data = tables()
    # Powiążmy postać z encyklopedii #4 ("Stary kowal") ze sceną 100 oraz sceną w rozdziale 2 (dialog 200)
    data["entity_init_data"] = [(700, {"id": 700, "attr_id": 55, "billboard_data": {"name": T + 80, "title": T + 10}})]
    data["world_view_person_info"] = [(4, {"id": 4, "name": T + 80, "people_identity": [T + 10], "story": [41, 42]})]
    data["world_view_person_event"] = [
        (41, {"id": 41, "title": T + 81, "description": T + 82}),
        (42, {"id": 42, "title": U + 4, "description": U + 4}),
    ]
    data["dialog_timelines.200"] = list(
        rows([group("stary_kowal", 3, 9001, "", [text_track([span(U + 3, 0.0, 0), span(U + 32, 1.0, 0)])])]).items()
    )
    data["dialog_timelines.201"] = scene([U + 28])
    data["tasks"] = [
        *data["tasks"],
        (10, {"no": 10, "group": 6, "task_type": 1, "task_name": U + 2, "finish_dialogs": 200}),
        (20, {"no": 20, "group": 20, "task_type": 3, "task_name": U + 25, "task_target_str": U + 26, "finish_dialogs": 201}),
    ]
    data["task_group_info"] = [
        *data["task_group_info"],
        (6, {"id": 6, "group_name": U + 1, "group_sort": 2, "start_task": 10}),
        (20, {"id": 20, "group_name": U + 25, "group_sort": 1, "start_task": 20}),
    ]
    data["group_tasks"] = [*data["group_tasks"], (6, [10]), (20, [20])]
    data["plot_recap_data"] = [(1, {"id": 1, "group_id": 5, "synopsis_text": U + 5})]
    data["book_config"] = [(10, {"id": 10, "name": U + 6, "author": U + 7, "page_1": U + 8})]
    data["manual_items"] = [(10, {"id": 10, "bowu_name": U + 15, "describe": U + 16})]
    data["region_collect_jianwen_data"] = [(10, {"id": 10, "jianwen_title": U + 17, "jianwen_text": U + 18})]
    data["world_view_history_info"] = [(10, {"id": 10, "name": U + 13, "time_2": U + 14})]
    data["equip_items"] = [(10, {"id": 10, "name": U + 11, "describe_str": U + 12})]
    data["kongfu"] = [(10, {"id": 10, "name": U + 9, "description": U + 10})]
    data["xinfa"] = [(10, {"id": 10, "name": U + 19, "passive_skill_brief_description": U + 20})]
    data["jianghu_skills"] = [(10, {"id": 10, "jianghu_skill_name": U + 21, "jianghu_description": U + 22})]
    data["ever_know_clue_data"] = [(10, {"id": 10, "clue": U + 23, "record": U + 24})]
    data["text_msg"] = [
        (590291, {"id": 590291, "content": U + 30, "voice_over_no": "prolog_m_01"}),
        (590292, {"id": 590292, "content": U + 31, "voice_over_no": "prolog_f_01"}),
    ]
    return data


def _naglowki_epizody_i_sceny(text: str) -> list[str]:
    return [line for line in text.splitlines() if line.startswith("## Epizod ") or line.startswith("### Scena ")]


class CzytankiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="wwm-czytanki-test-")
        cls.root = Path(cls.temp.name)
        wyciag.zbuduj(
            FakeBaza(rich_world()),
            ZH_CZYTANKI,
            EN_CZYTANKI,
            cls.root / "index",
            {"opis": "czytanki test"},
            log=lambda _text: None,
        )
        cls.ix = indeks.wczytaj(cls.root / "index")
        cls.magazyn = tlumaczenie.Magazyn()
        k = mapa_tekstow.klucz
        # Zestaw polskich przekładów (bez U+32 — celowo pozostaje nieprzetłumaczone!)
        przeklady = {
            k(ZH_CZYTANKI[T + 1]): "Witaj w mojej kuźni.",
            k(ZH_CZYTANKI[T + 2]): "Kuję od rana!",
            f"@{T + 3:016x}": "Zrobiłem nowy miecz.",
            f"@{T + 4:016x}": "Zrobiłam nowy miecz.",
            k(ZH_CZYTANKI[T + 10]): "Mistrz Żelaza",
            k(ZH_CZYTANKI[T + 20]): "Żelazny Miecz",
            k(ZH_CZYTANKI[T + 21]): "Solidny oręż kowalski.",
            k(ZH_CZYTANKI[T + 30]): "Pierwsze zadanie",
            k(ZH_CZYTANKI[T + 31]): "Idź do kowala",
            k(ZH_CZYTANKI[T + 32]): "Rozdział I — Kuźnia",
            k(ZH_CZYTANKI[T + 40]): "Kuźnia Północy",
            k(ZH_CZYTANKI[T + 60]): "Tak",
            k(ZH_CZYTANKI[T + 61]): "Nie",
            k(ZH_CZYTANKI[T + 62]): "Wybór u kowala",
            k(ZH_CZYTANKI[T + 80]): "Stary Kowal",
            k(ZH_CZYTANKI[T + 81]): "Historia pierwsza",
            k(ZH_CZYTANKI[T + 82]): "Pierwszy wpis z księgi życia kowala.",
            k(ZH_CZYTANKI[T + 90]): "Plansza otwarcia aktu pierwszego.",
            k(ZH_CZYTANKI[U + 1]): "Rozdział II — Droga",
            k(ZH_CZYTANKI[U + 2]): "Drugie zadanie",
            k(ZH_CZYTANKI[U + 3]): "Spotykamy się znów, wędrowcze.",
            k(ZH_CZYTANKI[U + 4]): "Tajna druga biografia kowala.",
            k(ZH_CZYTANKI[U + 5]): "Streszczenie aktu pierwszego po polsku.",
            k(ZH_CZYTANKI[U + 6]): "Księga Pierwszych Dni",
            k(ZH_CZYTANKI[U + 7]): "Mistrz Chen",
            k(ZH_CZYTANKI[U + 8]): "Pierwsza strona tej prastarej księgi.",
            k(ZH_CZYTANKI[U + 9]): "Sztuka Żelaznego Deszczu",
            k(ZH_CZYTANKI[U + 10]): (
                "Bardzo długa technika wymagająca długiego opisu aby sprawdzić zawijanie wierszy w tabeli "
                "markdown bez użycia znaczników HTML oraz kontrolę szerokości stu dwudziestu znaków."
            ),
            k(ZH_CZYTANKI[U + 11]): "Szlachetna Zbroja",
            k(ZH_CZYTANKI[U + 12]): "Chroni przed mroźnym wiatrem.",
            k(ZH_CZYTANKI[U + 13]): "Bitwa pod Kaifengiem",
            k(ZH_CZYTANKI[U + 14]): "960 n.e.",
            k(ZH_CZYTANKI[U + 15]): "Wpis o Kuźniach",
            k(ZH_CZYTANKI[U + 16]): "Opis hasła w archiwum świata.",
            k(ZH_CZYTANKI[U + 17]): "Zapisek z gościńca",
            k(ZH_CZYTANKI[U + 18]): "Zasłyszana pieśń w gospodzie.",
            k(ZH_CZYTANKI[U + 19]): "Sztuka Spokojnego Serca",
            k(ZH_CZYTANKI[U + 20]): "Wzmacnia siłę ducha.",
            k(ZH_CZYTANKI[U + 21]): "Krok Wiatru",
            k(ZH_CZYTANKI[U + 22]): "Pozwala biec po powierzchni wody.",
            k(ZH_CZYTANKI[U + 23]): "Poszlaka ze skrzyni",
            k(ZH_CZYTANKI[U + 24]): "Znaleziona w kuźni.",
            k(ZH_CZYTANKI[U + 25]): "Sprawa na targu",
            k(ZH_CZYTANKI[U + 26]): "Porozmawiaj z kupcem.",
            k(ZH_CZYTANKI[U + 28]): "Czego szukasz wędrowcze?",
            k(ZH_CZYTANKI[U + 30]): "Obudź się, chłopcze!",
            k(ZH_CZYTANKI[U + 31]): "Obudź się, dziewczyno!",
        }
        for slot, val in przeklady.items():
            cls.magazyn.ustaw(slot, val)
        cls.magazyn_dir = cls.root / "magazyn"
        tlumaczenie.zapisz(cls.magazyn_dir, cls.magazyn)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_cleans_netease_color_and_richtext_tags_safely(self):
        self.assertEqual(
            buduj_czytanki.oczysc_tekst("#8C5823175#E pkt za <Silkbind Penetration|780|#C|154> i #Y10#E <LINK id='1'>kliknij</LINK>"),
            "175 pkt za Silkbind Penetration i 10 kliknij",
        )
        self.assertEqual(
            buduj_czytanki.oczysc_tekst("Naciśnij #ccac18{}#E, aby skoczyć."),
            "Naciśnij {}, aby skoczyć.",
        )

    def test_wraps_markdown_tables_to_120_chars_without_br(self):
        lines = buduj_czytanki.formatuj_tabele(
            ["Nazwa", "Opis"],
            [[
                "Sztuka Żelaznego Deszczu",
                "Bardzo długa technika wymagająca długiego opisu aby sprawdzić zawijanie wierszy w tabeli markdown bez użycia znaczników HTML oraz kontrolę szerokości.",
            ]],
            max_szerokosc=120,
        )
        self.assertGreater(len(lines), 3)  # wygenerowano wiersze kontynuacji
        for line in lines:
            self.assertNotIn("<br>", line)
            self.assertLessEqual(len(line), 120)

    def test_builds_dual_file_srwy_style_polish_only_czytanki_and_zip(self):
        out_dir = self.root / "czytanki_oba"
        out_zip = self.root / "WWM_CZYTANKI_PL.zip"
        rc = buduj_czytanki.main(
            [
                "--indeks",
                str(self.root / "index"),
                "--magazyn",
                str(self.magazyn_dir),
                "--wyj-katalog",
                str(out_dir),
                "--wyj-zip",
                str(out_zip),
                "--wersja",
                "v2",
            ]
        )
        self.assertEqual(rc, 0)
        self.assertTrue(out_zip.is_file())

        all_md = {p.name: p.read_text(encoding="utf-8") for p in out_dir.glob("*.md")}
        self.assertEqual(set(all_md), {"README.md", "epizody.md", "kontekst_scen.md", "dodatkowe.md"})

        # ZERO wycieku angielskiego ani chińskiego tekstu nigdzie w plikach .md!
        joined = "\n".join(all_md.values())
        self.assertNotIn("Untranslated English Line Sentinel", joined)
        self.assertNotIn("Nieznana fraza bez polskiego przekładu", joined)
        self.assertNotIn("Chapter Two EN", joined)
        self.assertNotIn("Wake up, boy! EN", joined)

        ep_md = all_md["epizody.md"]
        ctx_md = all_md["kontekst_scen.md"]
        dod_md = all_md["dodatkowe.md"]

        # Lustrzane nagłówki Epizod E / Scena E.S dokładnie 1:1 pomiędzy epizody.md i kontekst_scen.md
        self.assertEqual(_naglowki_epizody_i_sceny(ep_md), _naglowki_epizody_i_sceny(ctx_md))
        self.assertGreaterEqual(len(_naglowki_epizody_i_sceny(ep_md)), 6)

        # W epizody.md: prolog, chronologiczny wątek główny, warianty płci, rozwiązane skoki wyborów, zadania poboczne
        self.assertIn("Obudź się, chłopcze!", ep_md)
        self.assertIn("Obudź się, dziewczyno!", ep_md)
        self.assertIn("Rozdział I — Kuźnia", ep_md)
        self.assertIn("Rozdział II — Droga", ep_md)
        self.assertLess(ep_md.index("Rozdział I — Kuźnia"), ep_md.index("Rozdział II — Droga"))
        self.assertIn("Streszczenie aktu pierwszego po polsku.", ep_md)
        self.assertIn("Plansza otwarcia aktu pierwszego.", ep_md)
        self.assertIn("**Stary Kowal:** Witaj w mojej kuźni.", ep_md)
        self.assertIn("[♂ Bohater]", ep_md)
        self.assertIn("[♀ Bohaterka]", ep_md)
        self.assertIn("**Wybór 1:** Tak *(→ dialog 101)*", ep_md)
        self.assertIn("w otwartym świecie gry można je podejmować w dowolnej kolejności", ep_md)
        self.assertIn("Czego szukasz wędrowcze?", ep_md)
        # Czysty skrypt nie zawiera ścian tabel ani biografii encyklopedycznych
        self.assertNotIn("Pierwszy wpis z księgi życia kowala.", ep_md)

        # W kontekst_scen.md: pierwsza historia przy scenie, brak spoilerów przed końcem, bez nieprzypisanego katalogu
        self.assertIn("Pierwszy wpis z księgi życia kowala.", ctx_md)
        pos_druga_bio = ctx_md.index("Tajna druga biografia kowala.")
        pos_dalsze = ctx_md.index("## Dalsze wpisy encyklopedii postaci i relacji")
        self.assertGreater(pos_druga_bio, pos_dalsze)
        self.assertNotIn("## Katalog nieprzypisanych haseł ze świata gry", ctx_md)
        self.assertNotIn("Szlachetna Zbroja", ctx_md)

        # Całe nieprzypisane zaplecze świata trafia przejrzyście według rodzaju do `dodatkowe.md`
        for expected in (
            "Bitwa pod Kaifengiem",
            "Księga Pierwszych Dni",
            "Pierwsza strona tej prastarej księgi.",
            "Wpis o Kuźniach",
            "Zapisek z gościńca",
            "Poszlaka ze skrzyni",
            "Szlachetna Zbroja",
            "Sztuka Żelaznego Deszczu",
            "Sztuka Spokojnego Serca",
            "Krok Wiatru",
        ):
            self.assertIn(expected, dod_md)

        # Deterministyczny ZIP zawiera README + wszystkie 3 pliki treści
        with zipfile.ZipFile(out_zip) as zf:
            self.assertEqual(sorted(zf.namelist()), ["README.md", "dodatkowe.md", "epizody.md", "kontekst_scen.md"])

    def test_gender_filter_and_zakres_kompletne_rozdzialy_and_splitting_and_main_only(self):
        # 1. Filtrowanie płci --plec bohaterka + wymuszone dzielenie --podziel-powyzej 500
        out_f = self.root / "czytanki_f"
        rc = buduj_czytanki.main(
            [
                "--indeks",
                str(self.root / "index"),
                "--magazyn",
                str(self.magazyn_dir),
                "--plec",
                "bohaterka",
                "--podziel-powyzej",
                "500",
                "--wyj-katalog",
                str(out_f),
            ]
        )
        self.assertEqual(rc, 0)
        czesci_ep = sorted(out_f.glob("epizody_czesc_*.md"))
        self.assertGreaterEqual(len(czesci_ep), 2)
        caly_ep_f = "\n".join(p.read_text(encoding="utf-8") for p in czesci_ep)
        self.assertIn("Obudź się, dziewczyno!", caly_ep_f)
        self.assertNotIn("Obudź się, chłopcze!", caly_ep_f)
        self.assertIn("Zrobiłam nowy miecz.", caly_ep_f)
        self.assertNotIn("Zrobiłem nowy miecz.", caly_ep_f)

        # 2. --tylko-watek-glowny wyklucza zadania poboczne z epizodów
        out_main = self.root / "czytanki_main_only"
        rc_m = buduj_czytanki.main(
            [
                "--indeks",
                str(self.root / "index"),
                "--magazyn",
                str(self.magazyn_dir),
                "--tylko-watek-glowny",
                "--wyj-katalog",
                str(out_main),
            ]
        )
        self.assertEqual(rc_m, 0)
        ep_main = (out_main / "epizody.md").read_text(encoding="utf-8")
        self.assertIn("Rozdział I — Kuźnia", ep_main)
        self.assertNotIn("Sprawa na targu", ep_main)
        self.assertNotIn("Czego szukasz wędrowcze?", ep_main)

        # 3. Zakres kompletne-rozdzialy pomija Rozdział II (bo ma nieprzetłumaczone U+32), zachowuje Rozdział I!
        out_comp = self.root / "czytanki_comp"
        rc2 = buduj_czytanki.main(
            [
                "--indeks",
                str(self.root / "index"),
                "--magazyn",
                str(self.magazyn_dir),
                "--zakres",
                "kompletne-rozdzialy",
                "--wyj-katalog",
                str(out_comp),
            ]
        )
        self.assertEqual(rc2, 0)
        ep_comp = (out_comp / "epizody.md").read_text(encoding="utf-8")
        self.assertIn("Rozdział I — Kuźnia", ep_comp)
        self.assertNotIn("Rozdział II — Droga", ep_comp)

        # 4. Zakres wszystko jawnie oznacza brakujący tekst bez wstawiania angielskiego lub chińskiego
        out_all = self.root / "czytanki_all"
        rc3 = buduj_czytanki.main(
            [
                "--indeks",
                str(self.root / "index"),
                "--magazyn",
                str(self.magazyn_dir),
                "--zakres",
                "wszystko",
                "--wyj-katalog",
                str(out_all),
            ]
        )
        self.assertEqual(rc3, 0)
        ep_all = (out_all / "epizody.md").read_text(encoding="utf-8")
        self.assertIn("[Brak polskiego tekstu (", ep_all)
        self.assertNotIn("Untranslated English Line Sentinel", ep_all)
        self.assertNotIn("Nieznana fraza bez polskiego przekładu", ep_all)

        # 5. Bezpośrednio z częściowej zwrotki (--zwrotka + --tylko-zwrotka)
        paczka_dir = self.root / "paczka_do_zwrotki"
        buduj_paczke.zbuduj(self.ix, paczka_dir, wersja="1", data="2026-01-01", zip_=False)
        zwrotka_md = self.root / "zwrotka_czytanki.md"
        src_md = (paczka_dir / "sceny" / "01_watek-glowny_rozdzial-1_01.md").read_text(encoding="utf-8")
        zwrotka_md.write_text(
            fill(src_md, {K("kwestia kowala"): "Cześć z samej zwrotki!"}),
            encoding="utf-8",
        )
        out_zwr = self.root / "czytanki_zwrotka"
        rc4 = buduj_czytanki.main(
            [
                "--indeks",
                str(self.root / "index"),
                "--zwrotka",
                str(zwrotka_md),
                "--tylko-zwrotka",
                "--wyj-katalog",
                str(out_zwr),
            ]
        )
        self.assertEqual(rc4, 0)
        self.assertIn("Cześć z samej zwrotki!", (out_zwr / "epizody.md").read_text(encoding="utf-8"))

    def test_podglad_en_and_merges_identical_gender_variants(self):
        mag_same = tlumaczenie.Magazyn()
        mag_same.ustaw(f"@{T + 3:016x}", "To samo zdanie dla obu płci.")
        mag_same.ustaw(f"@{T + 4:016x}", "To samo zdanie dla obu płci.")
        mag_same_dir = self.root / "mag_same"
        tlumaczenie.zapisz(mag_same_dir, mag_same)

        out_same = self.root / "czytanki_same"
        rc_same = buduj_czytanki.main(
            [
                "--indeks",
                str(self.root / "index"),
                "--magazyn",
                str(mag_same_dir),
                "--wyj-katalog",
                str(out_same),
            ]
        )
        self.assertEqual(rc_same, 0)
        ep_same = (out_same / "epizody.md").read_text(encoding="utf-8")
        self.assertEqual(ep_same.count("To samo zdanie dla obu płci."), 1)
        self.assertNotIn("[♂ Bohater]", ep_same)

        out_en = self.root / "czytanki_en"
        rc_en = buduj_czytanki.main(
            [
                "--indeks",
                str(self.root / "index"),
                "--podglad-en",
                "--wyj-katalog",
                str(out_en),
            ]
        )
        self.assertEqual(rc_en, 0)
        self.assertIn("Podgląd formy czytanek (EN", (out_en / "README.md").read_text(encoding="utf-8"))
        self.assertIn("Chapter Two EN", (out_en / "epizody.md").read_text(encoding="utf-8"))

    def test_table_preserves_hex_ids_and_keeps_filenames_intact(self):
        lines = buduj_czytanki.formatuj_tabele(
            ["Nazwa", "Opis", "Pochodzenie"],
            [
                ["Przedmiot #102020", "A common fish lure.", ""],
                ["#102022", "Grain or dough bait.", "Made using flour."],
                ["kontekst_scen.md", "Bardzo długi opis towarzysza kontekstowego wszystkich scen w dwuplikowym układzie.", "100/100"],
            ],
        )
        rendered = "\n".join(lines)
        self.assertIn("Przedmiot #102020", rendered)
        self.assertIn("#102022", rendered)
        self.assertIn("kontekst_scen.md", rendered)
        self.assertTrue(all(len(line) <= 120 for line in lines if line.startswith("|")))

    def test_cutscene_context_you_xia_and_replay_linking(self):
        V = T + 5000
        zh = {
            **ZH_CZYTANKI,
            V + 1: "主角",
            V + 2: "曹静观音",
            V + 3: "Kwestia gracza pod przebraniem",
            V + 4: "Stoisz tu?",
            V + 5: "Ja?",
            V + 6: "寒香寻",
            V + 7: "我们终究还是走到了这一步",
            V + 8: "天音之誓绝不可忘",
            V + 9: "这是天泉的规矩",
            V + 10: "解释一下为何如此",
            V + 11: "莫要再多言了",
            V + 12: "记住今天的教训",
            V + 13: "且看我这一剑",
            V + 14: "寒姨 你是去竹林小屋了吗",
            V + 15: "我 还是先回去吧",
            V + 16: "你可真有本事啊",
            V + 17: "Powtórka zadania kluczowego",
            V + 18: "Streszczenie kluczowej cutsceny zadania",
            V + 19: "Kluczowy rozdział",
            V + 20: "Luźna plansza przejściowa",
            V + 21: "我们终究还是走到了这一步。",
        }
        en = {
            **EN_CZYTANKI,
            V + 1: "Main Character",
            V + 2: "Cao Jing Guanyin",
            V + 3: "Disguised player line",
            V + 4: "Why standing here?",
            V + 5: "Me?",
            V + 6: "Han Xiangxun",
            V + 7: "We reached this point at last",
            V + 8: "Never forget the oath of Heaven",
            V + 9: "These are the rules of Heaven",
            V + 10: "Explain why it happened",
            V + 11: "Say no more words",
            V + 12: "Remember today's lesson",
            V + 13: "Watch this blade strike",
            V + 14: "Aunt Han, did you go to the hut?",
            V + 15: "Me: I should head back first.",
            V + 16: "You really have some nerve",
            V + 17: "Key Replay Title",
            V + 18: "Key replay synopsis EN",
            V + 19: "Key chapter EN",
            V + 20: "Loose black screen EN",
            V + 21: "We reached this point at last.",
        }
        data = rich_world()
        data["dialog_timelines.300"] = list(
            rows([
                group("ja_gen", 1, 0, V + 1, [text_track([span(T + 2, 0.0, 1)])]),
                group("ja_przebr", 1, 0, V + 2, [text_track([span(V + 3, 1.0, 1)])]),
            ]).items()
        )
        data["tasks"] = [
            *data["tasks"],
            (11, {"no": 11, "group": 5, "task_type": 1, "pre_task": [10], "task_name": V + 19, "finish_dialogs": 300}),
        ]
        data["group_tasks"] = [(5, [1, 2, 3, 11]), (6, [10]), (20, [20])]
        data["world_view_person_info"] = [
            *data["world_view_person_info"],
            (12, {"id": 12, "name": V + 6, "people_identity": [T + 10], "story": []}),
        ]
        data["world_view_person_voice"] = [
            ("12001", {"id": "12001", "person_id": 12, "description": V + 21}),
        ]
        data["wds_oneday_intro_cutscene_data"] = [
            (1, {"id": 1, "time": 1.0, "duration": 2.0, "speaker": 2, "text": V + 4}),
            (2, {"id": 2, "time": 3.0, "duration": 2.0, "speaker": 1, "text": V + 5}),
        ]
        data["text_msg"] = [
            (591342, {"id": 591342, "content": V + 8}),
            (591343, {"id": 591343, "content": V + 9}),
            (591344, {"id": 591344, "content": V + 10}),
            (591345, {"id": 591345, "content": V + 11}),
            (591346, {"id": 591346, "content": V + 12}),
            (591347, {"id": 591347, "content": V + 13}),
            (591348, {"id": 591348, "content": V + 7}),
            (591349, {"id": 591349, "content": V + 14}),
            (591350, {"id": 591350, "content": V + 15}),
            (591351, {"id": 591351, "content": V + 16}),
        ]
        data["sound_data"] = [
            (1, {"text": zh[V + 8], "audio_name": "vo_sm_xsm9p4_ty_01"}),
            (2, {"text": zh[V + 9], "audio_name": "vo_sm_xsm9p4_ty_02"}),
            (3, {"text": zh[V + 10], "audio_name": "vo_sm_kfm8_pma_53"}),
            (4, {"text": zh[V + 11], "audio_name": "vo_sm_xsm9p4_ty_03"}),
            (5, {"text": zh[V + 12], "audio_name": "vo_sm_xsm9p4_ty_04"}),
            (6, {"text": zh[V + 13], "audio_name": "vo_sm_xsm9p4_pma_05"}),
            (7, {"text": zh[V + 16], "audio_name": "vo_sm_xsm9p4_npc_pma_06"}),
        ]
        data["cutscenes"] = [
            *data["cutscenes"],
            (30999, {"no": 30999, "synopsis_text_pc": V + 18}),
            (30888, {"no": 30888, "content": V + 20}),
            (10030888, {"no": 10030888, "content": V + 20}),
        ]
        data["task_cutscene_replay"] = [
            (30999, {"no": 30999, "task_no": 11, "group": 5, "name": V + 17, "synopsis_text": V + 18}),
        ]

        root_c = self.root / "cutscene_ctx"
        wyciag.zbuduj(FakeBaza(data), zh, en, root_c / "index", {"opis": "cutscene ctx"}, log=lambda _t: None)
        mag = tlumaczenie.Magazyn()
        k = mapa_tekstow.klucz
        base_mag = tlumaczenie.wczytaj(self.magazyn_dir)
        for slot, val in base_mag.po_kluczu.items():
            mag.ustaw(slot, val)
        for vid, val in base_mag.po_id.items():
            mag.ustaw(f"@{vid}", val)
        for src_id, pl_val in (
            (V + 1, "Bohater"),
            (V + 2, "Przebrana Cao"),
            (V + 3, "Wypowiedź w przebraniu."),
            (V + 4, "Dlaczego tu stoisz?"),
            (V + 5, "Ja?"),
            (V + 6, "Ciocia Han"),
            (V + 7, "W końcu doszliśmy do tego miejsca."),
            (V + 8, "Nigdy nie zapomnij przysięgi."),
            (V + 9, "Takie są zasady sekty."),
            (V + 10, "Wyjaśnij, dlaczego tak się stało."),
            (V + 11, "Nie mów już ani słowa."),
            (V + 12, "Zapamiętaj dzisiejszą lekcję."),
            (V + 13, "Spójrz na to cięcie miecza!"),
            (V + 14, "Ciociu Han, byłaś w chatce w gaju?"),
            (V + 15, "Ja: Wrócę lepiej pierwszy."),
            (V + 16, "Masz odwagę."),
            (V + 17, "Powtórka finału aktu"),
            (V + 18, "Streszczenie przypisane bezpośrednio do zadania jedenastego."),
            (V + 19, "Zadanie jedenaste"),
            (V + 20, "Krótka plansza czarnego ekranu."),
        ):
            mag.ustaw(k(zh[src_id]), pl_val)
        tlumaczenie.zapisz(root_c / "magazyn", mag)

        out_c = root_c / "czytanki"
        rc = buduj_czytanki.main(
            [
                "--indeks",
                str(root_c / "index"),
                "--magazyn",
                str(root_c / "magazyn"),
                "--wyj-katalog",
                str(out_c),
            ]
        )
        self.assertEqual(rc, 0)
        ep_md = (out_c / "epizody.md").read_text(encoding="utf-8")
        ctx_md = (out_c / "kontekst_scen.md").read_text(encoding="utf-8")

        self.assertEqual(_naglowki_epizody_i_sceny(ep_md), _naglowki_epizody_i_sceny(ctx_md))

        # 1. Zero generycznego "Gracz" / "You Xia (Bohater)"; poprawne "You Xia" i "You Xia (Przebrana Cao)"
        self.assertNotIn("**Gracz:**", ep_md)
        self.assertNotIn("You Xia (Bohater)", ep_md)
        self.assertIn("**You Xia:** Kuję od rana!", ep_md)
        self.assertIn("**You Xia (Przebrana Cao):** Wypowiedź w przebraniu.", ep_md)

        # 2. Intro ma You Xia i Gwardię Cesarską
        self.assertIn("Mówca 2 (Gwardia Cesarska):", ep_md)
        self.assertIn("**You Xia:** Ja?", ep_md)

        # 3. `vo_sm_xsm9p4` trafia do Poligonu Tian Yinga (nie Prologu!)
        self.assertIn("Qinghe — poligon Tian Yinga", ep_md)
        self.assertNotIn("Prolog — zasadzka w ulewie", ep_md)

        # 4. Wygładzona 1-wierszowa kolizja V+10 nie przypisała błędnie `You Xia`,
        # a cała scena 591342–591351 pozostała jednym spójnym blokiem
        self.assertEqual(ep_md.count("591342–591351"), 1)
        self.assertNotIn("**You Xia:** Wyjaśnij, dlaczego tak się stało.", ep_md)
        self.assertIn("Wyjaśnij, dlaczego tak się stało.", ep_md)

        # 5. WVPV przypisało polską nazwę "Ciocia Han" (bez wycieku EN "Han Xiangxun")
        self.assertIn("**Ciocia Han:** W końcu doszliśmy do tego miejsca.", ep_md)
        self.assertNotIn("Han Xiangxun", ep_md)
        # Jednocześnie w kontekst_scen.md dla tej sceny pojawia się karta postaci Ciocia Han!
        self.assertIn("**Ciocia Han** *(mówca w cutscenie)*", ctx_md)

        # 6. Wołacz V+14 NIE przypisał Cioci Han, prefiks V+15 dał You Xia bez podwójnego "Ja:"
        self.assertNotIn("**Ciocia Han:** Ciociu Han, byłaś w chatce w gaju?", ep_md)
        self.assertIn("Ciociu Han, byłaś w chatce w gaju?", ep_md)
        self.assertIn("**You Xia:** Wrócę lepiej pierwszy.", ep_md)
        self.assertNotIn("**You Xia:** Masz odwagę.", ep_md)
        self.assertIn("Masz odwagę.", ep_md)
        self.assertNotIn("**You Xia:** Ja: Wrócę lepiej pierwszy.", ep_md)

        # 7. Powtórka #30999 z `task_cutscene_replay` weszła do zadania #11 w Epizodzie, nie jako luźny wpis,
        # a klon #10030888 został pominięty
        self.assertIn("Streszczenie przypisane bezpośrednio do zadania jedenastego.", ep_md)
        self.assertIn("- **#30888:** Krótka plansza czarnego ekranu.", ep_md)
        self.assertNotIn("#10030888", ep_md)

    def test_v2_associations_int_speakers_w2_arrays_ac_boundaries_and_spoilers(self):
        """Testuje nowe mechanizmy v2: mówcy int + `entity_no`, kolumny `[]`, `w[2]`, AC i anty-duplikację."""
        W = T + 7000
        zh = {
            **ZH_CZYTANKI,
            W + 1: "冯继升",
            W + 2: "红线_kolizja",
            W + 3: "墨山道门人",
            W + 4: "墨山道传人描述",
            W + 5: "我",
            W + 6: "大师你好，听说墨山道和青溪有旧！",
            W + 7: "你们在找绿林好汉吗？",
            W + 8: "墨山道",
            W + 9: "兼爱非攻",
            W + 10: "隐匿墨山",
            W + 11: "古老的机关门派，弟子常行侠义之事。",
            W + 12: "墨山道建立",
            W + 13: "公元940年",
            W + 14: "冯继升的秘密信件",
            W + 15: "信中记录了冯继升调查墨山道的经过。",
            W + 16: "关系故事一：初识墨山。",
            W + 17: "关系故事二：结局秘密（剧透）。",
            W + 18: "诗句第一行",
            W + 19: "诗句第二行",
            W + 20: "暗涌标题",
            W + 21: "暗涌详情",
            W + 22: "Iron",
            W + 23: "Ironsmith",
            W + 24: "This ironsmith stands near the gate.",
            W + 25: "Iron Guild description",
        }
        en = {
            **EN_CZYTANKI,
            W + 1: "Feng Jisheng",
            W + 2: "RubyCollision",
            W + 3: "Mohist Disciple",
            W + 4: "A wandering Mohist disciple.",
            W + 5: "Me",
            W + 6: "Hello master, I heard about the Mohist Order!",
            W + 7: "Are you looking for wanderers?",
            W + 8: "Mohist Order",
            W + 9: "Universal Love",
            W + 10: "Hidden Mohist Peak",
            W + 11: "An ancient order of master artisans.",
            W + 12: "Mohist Founding",
            W + 13: "940 CE",
            W + 14: "Feng's Secret Letter",
            W + 15: "Letter tracing Feng Jisheng's investigation.",
            W + 16: "Amity story 1: first meeting.",
            W + 17: "Amity story 2: endgame spoiler.",
            W + 18: "Poem line one",
            W + 19: "Poem line two",
            W + 20: "Dark surge step",
            W + 21: "Dark surge step detail",
            W + 22: "Iron",
            W + 23: "Ironsmith",
            W + 24: "This ironsmith stands near the gate.",
            W + 25: "Iron Guild description",
        }
        data = rich_world()
        # Entity #8801 należy do prawdziwego Feng Jishenga, mimo że w scenie o[3] skolidował się na W+2!
        data["entity_init_data"] = [
            *data["entity_init_data"],
            (8801, {"id": 8801, "attr_id": 885, "billboard_data": {"name": W + 1, "title": W + 3}}),
        ]
        data["entity_attr"] = [(885, {"id": 885, "introduction": W + 4})]
        # Tabele z `[]`, `w[2]`, amity, listami i granicami słów AC
        data["world_view_shili_data"] = [
            (1, {"id": 1, "name": W + 8, "introduction_short": W + 9, "introduction_location": W + 10, "introduction_long": W + 11}),
            (2, {"id": 2, "name": W + 22, "introduction_short": W + 25}),
        ]
        data["world_view_history_info"] = [
            *data["world_view_history_info"],
            (101, {"id": 101, "name": W + 12, "time_2": W + 13}),
        ]
        data["npc_amity_relation_data"] = [
            (50, {"id": 50, "amity_target_name": W + 1, "story_1": W + 16, "story_2": W + 17}),
        ]
        data["tasks_envelop_data"] = [
            (99, {"id": 99, "to": W + 14, "text": W + 15}),
        ]
        data["task_progress_dark_info"] = [
            (101, {"id": 101, "content": W + 20, "introduction": W + 21}),
        ]
        data["task_progress_dark_group"] = [
            (101, {"id": 101, "steps": [{"name": W + 20, "small_point_describe": W + 21}, {"name": W + 18, "small_point_describe": W + 19}]}),
        ]
        # Dialog 400 i 401 z mówcą int (0 / 1) oraz kolizją person[3], użyte w zadaniu #12/#13 (grupa 5)
        data["dialog_timelines.400"] = list(
            rows([
                group("我", 1, 0, "", [text_track([span(W + 6, 0.0, 0)])]),
                group("feng", 2, 8801, W + 2, [text_track([span(W + 7, 1.0, 1)])]),
            ]).items()
        )
        data["dialog_timelines.401"] = list(
            rows([
                group("我", 1, 0, "", [text_track([span(W + 24, 0.0, 0)])]),
                group("feng", 2, 8801, W + 2, [text_track([span(W + 8, 1.0, 1)])]),
            ]).items()
        )
        data["branch_data"] = [
            *data["branch_data"],
            ("9_2", {"ques_argue_no": 9, "ques_each_no": 2, "main_title": T + 62, "choice_1": T + 60, "choice_dialogs_1": 400, "ques_stop_dialogs": [[200]]}),
        ]
        data["tasks"] = [
            *data["tasks"],
            (12, {"no": 12, "group": 5, "task_type": 1, "pre_task": [10], "task_name": W + 1, "finish_dialogs": 400}),
            (13, {"no": 13, "group": 5, "task_type": 1, "pre_task": [12], "task_name": W + 23, "finish_dialogs": 401}),
        ]
        data["group_tasks"] = [(5, [1, 2, 3, 12, 13]), (6, [10]), (20, [20])]

        root_v = self.root / "v2_assoc"
        wyciag.zbuduj(FakeBaza(data), zh, en, root_v / "index", {"opis": "v2 assoc"}, log=lambda _t: None)
        ix_v = indeks.wczytaj(root_v / "index")
        builder = buduj_czytanki.BudowniczyCzytanek(ix_v, buduj_czytanki.ZrodloPodgladuEN(ix_v), zakres="wszystko")
        pliki, epizody = builder.buduj_z_epizodami()
        by_name = {p.nazwa: "\n".join(p.linie) for p in pliki}
        ep_txt = by_name["epizody.md"]
        ctx_txt = by_name["kontekst_scen.md"]

        # 1. Mówca int i kolizja: prawdziwy Feng Jisheng mówi w dialogu 400, NIGDY "Postać (1)" ani RubyCollision!
        self.assertIn("**Feng Jisheng:** Are you looking for wanderers?", ep_txt)
        self.assertNotIn("**Postać (1):**", ep_txt)
        self.assertNotIn("RubyCollision", ep_txt)
        # Rozwiązany skok wyboru na konkretną Scenę E.S:
        self.assertRegex(ep_txt, r"→ Scena \d+\.\d+, dialog 400")

        # 2. Karta Feng Jishenga przy pierwszym wystąpieniu zawiera opis `entity_attr` i relację `story_1`,
        # ale NIE `story_2` (ochrona przed spoilerem — ląduje w sekcji końcowej!).
        self.assertIn("A wandering Mohist disciple.", ctx_txt)
        self.assertIn("Amity story 1: first meeting.", ctx_txt)
        pos_s2 = ctx_txt.index("Amity story 2: endgame spoiler.")
        pos_end = ctx_txt.index("## Dalsze wpisy encyklopedii postaci i relacji")
        self.assertGreater(pos_s2, pos_end)

        # 3. Pośrednio po unikalnym imieniu Feng Jishenga podpiął się list `Feng's Secret Letter`!
        self.assertIn("Feng's Secret Letter", ctx_txt)
        self.assertIn("powiązane przez postać: Feng Jisheng", ctx_txt)

        # 4. Z tekstu dialogu podpięła się frakcja `Mohist Order` wraz z jej kalendarium (`Mohist Founding`)
        self.assertIn("An ancient order of master artisans.", ctx_txt)
        self.assertIn("Mohist Founding", ctx_txt)
        # Drugie wystąpienie w dialogu 401 pokazuje skrócony zbiorczy odsyłacz `*Wcześniej opisane:*`
        self.assertIn("*Wcześniej opisane:*", ctx_txt)

        # 5. Granica słów AC dla łaciny: `"Ironsmith"` w dialogu 401 NIE przyciąga frakcji `"Iron"` do sceny!
        sc_401_start = ctx_txt.index("(dialog 401)")
        sc_401_end = ctx_txt.index("## ", sc_401_start)
        sc_401_block = ctx_txt[sc_401_start:sc_401_end]
        self.assertNotIn("Iron Guild description", sc_401_block)
        self.assertIn("Iron Guild description", by_name["dodatkowe.md"])

    def test_dodatkowe_md_zero_gaps_and_all_categories_and_subsplitting(self):
        """Każdy przetłumaczony tekst spoza scen trafia bez duplikatów do właściwego działu `dodatkowe.md`, bez wycieku EN."""
        Q = T + 9000
        zh = {
            **ZH_CZYTANKI,
            Q + 1: "Strój Wędrowca",
            Q + 2: "Lekki płaszcz podróżny z jedwabiu.",
            Q + 3: "List z Jiangnan",
            Q + 4: "Spotkajmy się o świcie przy przystani.",
            Q + 5: "Osiągnięcie Pierwszy Krok",
            Q + 6: "Ukończ swój pierwszy rozdział.",
            Q + 7: "Wpis techniczny debug",
            Q + 8: "Tekst bez nazwy tabeli źródłowej",
            Q + 9: "Nieprzetłumaczony wpis dodatkowy",
        }
        en = {
            **EN_CZYTANKI,
            Q + 1: "Wanderer Outfit EN",
            Q + 2: "Light silk traveling cloak EN",
            Q + 3: "Letter from Jiangnan EN",
            Q + 4: "Meet at dawn at the pier EN",
            Q + 5: "First Step Achievement EN",
            Q + 6: "Finish your first chapter EN",
            Q + 7: "Debug UI msg EN",
            Q + 8: "Sourceless entry EN",
            Q + 9: "Untranslated Extra Entry EN",
        }
        data = rich_world()
        data["fashion_items"] = [(501, {"id": 501, "name": Q + 1, "describe_str": Q + 2})]
        data["emails_data"] = [(601, {"id": 601, "mail_title": Q + 3, "content": Q + 4})]
        data["ac_raw"] = [(701, {"id": 701, "achievement_name": Q + 5, "achievement_info": Q + 6})]
        data["programmer_text_msg"] = [(801, {"id": 801, "text": Q + 7})]
        # Dodatkowy wiersz bez przypisanej tabeli i bez tłumaczenia dla Q+9
        data["stuff_items"] = [*data["stuff_items"], (901, {"id": 901, "name": Q + 9})]

        root_z = self.root / "zero_gaps"
        wyciag.zbuduj(FakeBaza(data), zh, en, root_z / "index", {"opis": "zero gaps"}, log=lambda _t: None)
        ix_z = indeks.wczytaj(root_z / "index")
        # Dodajemy sztuczny klucz spoza tabel (10_bez_zrodla)
        from tools.indeks import Tekst

        kl_bez = K(zh[Q + 8])
        ix_z.teksty[kl_bez] = Tekst(
            zrodlo=zh[Q + 8],
            en=en[Q + 8],
            n=1,
            w=None,
            z_en=False,
        )

        mag = tlumaczenie.Magazyn()
        for slot, val in self.magazyn.po_kluczu.items():
            mag.ustaw(slot, val)
        for ident, val in self.magazyn.po_id.items():
            mag.ustaw("@" + ident, val)
        pl_entries = {
            Q + 1: "Strój Nocnego Wędrowca PL",
            Q + 2: "Lekki płaszcz jedwabny PL.",
            Q + 3: "List znad Rzeki PL",
            Q + 4: "Spotkajmy się na pomoście o świcie PL.",
            Q + 5: "Osiągnięcie: Pierwszy Krok PL",
            Q + 6: "Ukończ pierwszy rozdział opowieści PL.",
            Q + 7: "Wpis systemowy z tabeli technicznej PL.",
            Q + 8: "Tekst bez przypisanej tabeli PL.",
        }
        for num, txt in pl_entries.items():
            mag.ustaw(K(zh[num]), txt)

        builder = buduj_czytanki.BudowniczyCzytanek(ix_z, buduj_czytanki.ZrodloPL(ix_z, mag), z_otoczeniem=True)
        pliki, _ = builder.buduj_z_epizodami()
        by_name = {p.nazwa: "\n".join(p.linie) for p in pliki}
        ep_txt = by_name["epizody.md"]
        ctx_txt = by_name["kontekst_scen.md"]
        dod_txt = by_name["dodatkowe.md"]

        # 1. Wszystkie 8 dodatkowych polskich tekstów znalazło się w `dodatkowe.md` (i nigdzie indziej), zero wycieku EN
        for txt in pl_entries.values():
            self.assertIn(txt, dod_txt)
        for en_sentinel in (
            "Wanderer Outfit EN",
            "Untranslated Extra Entry EN",
            "Sourceless entry EN",
            "Debug UI msg EN",
        ):
            self.assertNotIn(en_sentinel, ep_txt + ctx_txt + dod_txt)

        # 2. Podział tematyczny na sekcje `dodatkowe.md`
        self.assertIn("## 3. Przedmioty, wyposażenie, stroje i budowle", dod_txt)
        self.assertIn("## 4. Encyklopedia świata, historia, księgi, poszlaki i listy", dod_txt)
        self.assertIn("## 8. Osiągnięcia, poradniki, interfejs i systemy gry", dod_txt)
        self.assertIn("## 9. Pozostałe tabele i teksty bez przypisanej tabeli", dod_txt)

        # 3. Elementy z `epizody.md` i `kontekst_scen.md` NIE duplikują się w `dodatkowe.md`
        self.assertNotIn("Witaj w mojej kuźni.", dod_txt)
        self.assertNotIn("Pierwszy wpis z księgi życia kowala.", dod_txt)
        self.assertNotIn("Tajna druga biografia kowala.", dod_txt)

        # 4. Tryb `--zakres wszystko` ujawnia brakujący Q+9 jawnym znacznikiem PL (bez EN)
        builder_all = buduj_czytanki.BudowniczyCzytanek(ix_z, buduj_czytanki.ZrodloPL(ix_z, mag), zakres="wszystko", z_otoczeniem=True)
        pliki_all, _ = builder_all.buduj_z_epizodami()
        dod_all = "\n".join(next(p for p in pliki_all if p.nazwa == "dodatkowe.md").linie)
        self.assertIn(f"[Brak polskiego tekstu: {K(zh[Q + 9])}]", dod_all)

        # 5. Podział `_podziel_na_czesci` z małym limitem tnie także po `### ` i dużych tabelach w `dodatkowe.md`
        czesci = buduj_czytanki._podziel_na_czesci(pliki[2], 700)
        self.assertGreaterEqual(len(czesci), 3)
        self.assertEqual(czesci[0][0], "dodatkowe_czesc_01.md")


if __name__ == "__main__":
    unittest.main()
