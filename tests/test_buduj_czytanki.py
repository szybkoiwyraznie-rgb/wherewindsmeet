from __future__ import annotations

import json
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

    def test_wraps_markdown_tables_to_120_chars_without_br(self):
        lines = buduj_czytanki.formatuj_tabele(
            ["Nazwa", "Opis"],
            [[
                "Sztuka Żelaznego Deszczu",
                "Bardzo długa technika wymagająca długiego opisu aby sprawdzić zawijanie wierszy w tabeli markdown bez znaczników HTML oraz kontrolę szerokości.",
            ]],
            max_szerokosc=120,
        )
        self.assertGreater(len(lines), 3)  # wygenerowano wiersze kontynuacji
        for line in lines:
            self.assertNotIn("<br>", line)
            self.assertLessEqual(len(line), 120)

    def test_builds_chronological_polish_only_czytanki_with_all_books_and_zip(self):
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
                "v1",
            ]
        )
        self.assertEqual(rc, 0)
        self.assertTrue(out_zip.is_file())

        all_md = {p.name: p.read_text(encoding="utf-8") for p in out_dir.glob("*.md")}
        self.assertIn("README.md", all_md)
        self.assertIn("00_prolog_i_przerywniki.md", all_md)
        self.assertIn("01_watek_glowny.md", all_md)
        self.assertIn("02_zadania_poboczne_i_swiat.md", all_md)
        self.assertIn("03_encyklopedia_swiata.md", all_md)
        self.assertIn("04_przedmioty_i_ekwipunek.md", all_md)
        self.assertIn("05_sztuki_walki_i_zdolnosci.md", all_md)

        # ZERO wycieku angielskiego ani chińskiego tekstu nigdzie w plikach .md!
        joined = "\n".join(all_md.values())
        self.assertNotIn("Untranslated English Line Sentinel", joined)
        self.assertNotIn("Nieznana fraza bez polskiego przekładu", joined)
        self.assertNotIn("Chapter Two EN", joined)
        self.assertNotIn("Wake up, boy! EN", joined)

        # Wątek główny: chronologia, przerywnik, warianty obu płci, wybory, streszczenie i anty-duplikacja postaci
        main_md = all_md["01_watek_glowny.md"]
        self.assertIn("Rozdział I — Kuźnia", main_md)
        self.assertIn("Rozdział II — Droga", main_md)
        self.assertLess(main_md.index("Rozdział I — Kuźnia"), main_md.index("Rozdział II — Droga"))
        self.assertIn("Streszczenie aktu pierwszego po polsku.", main_md)
        self.assertIn("Plansza otwarcia aktu pierwszego.", main_md)
        self.assertIn("**Stary Kowal:** Witaj w mojej kuźni.", main_md)
        self.assertIn("[♂ Bohater]", main_md)
        self.assertIn("[♀ Bohaterka]", main_md)
        self.assertIn("**Wybór 1:** Tak *(→ dialog 101)*", main_md)
        # Pierwsza historia postaci pojawia się przy pierwszym wystąpieniu (Rozdział I), druga nie spoileruje Rozdziału II!
        self.assertIn("Pierwszy wpis z księgi życia kowala.", main_md)
        self.assertNotIn("Tajna druga biografia kowala.", main_md)
        self.assertIn("Ponowne wystąpienia znanych postaci:", main_md)

        # Zadania poboczne z uwagą o otwartym świecie
        side_md = all_md["02_zadania_poboczne_i_swiat.md"]
        self.assertIn("w otwartym świecie gry można je", side_md)
        self.assertIn("Czego szukasz wędrowcze?", side_md)

        # Księgi i encyklopedia
        enc_md = all_md["03_encyklopedia_swiata.md"]
        self.assertIn("Bitwa pod Kaifengiem", enc_md)
        self.assertIn("Księga Pierwszych Dni", enc_md)
        self.assertIn("Pierwsza strona tej prastarej księgi.", enc_md)
        self.assertIn("Tajna druga biografia kowala.", enc_md)
        self.assertIn("Wpis o Kuźniach", enc_md)
        self.assertIn("Zapisek z gościńca", enc_md)
        self.assertIn("Poszlaka ze skrzyni", enc_md)

        # Przedmioty i sztuki walki
        items_md = all_md["04_przedmioty_i_ekwipunek.md"]
        self.assertIn("Szlachetna Zbroja", items_md)
        self.assertIn("Żelazny Miecz", items_md)
        skills_md = all_md["05_sztuki_walki_i_zdolnosci.md"]
        self.assertIn("Sztuka Żelaznego Deszczu", skills_md)
        self.assertIn("Sztuka Spokojnego Serca", skills_md)
        self.assertIn("Krok Wiatru", skills_md)

        # Deterministyczny ZIP zawiera README + księgi
        with zipfile.ZipFile(out_zip) as zf:
            self.assertIn("README.md", zf.namelist())
            self.assertIn("01_watek_glowny.md", zf.namelist())

    def test_gender_filter_and_zakres_kompletne_rozdzialy_and_splitting(self):
        # 1. Filtrowanie płci --plec bohaterka wyklucza kwestie [♂ Bohater] i męską kwestię prologu
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
                "400",
                "--wyj-katalog",
                str(out_f),
            ]
        )
        self.assertEqual(rc, 0)
        prolog_f = (out_f / "00_prolog_i_przerywniki.md").read_text(encoding="utf-8")
        self.assertIn("Obudź się, dziewczyno!", prolog_f)
        self.assertNotIn("Obudź się, chłopcze!", prolog_f)

        # Wątek główny podzielił się na części przez niski --podziel-powyzej 400
        czesci_main = sorted(out_f.glob("01_watek_glowny_czesc_*.md"))
        self.assertGreaterEqual(len(czesci_main), 2)
        caly_main_f = "\n".join(p.read_text(encoding="utf-8") for p in czesci_main)
        self.assertIn("Zrobiłam nowy miecz.", caly_main_f)
        self.assertNotIn("Zrobiłem nowy miecz.", caly_main_f)

        # 2. Zakres kompletne-rozdzialy pomija Rozdział II (bo ma nieprzetłumaczone U+32), zachowuje Rozdział I!
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
        main_comp = (out_comp / "01_watek_glowny.md").read_text(encoding="utf-8")
        self.assertIn("Rozdział I — Kuźnia", main_comp)
        self.assertNotIn("Rozdział II — Droga", main_comp)

        # 3. Zakres wszystko jawnie oznacza brakujący tekst bez wstawiania angielskiego lub chińskiego
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
        main_all = (out_all / "01_watek_glowny.md").read_text(encoding="utf-8")
        self.assertIn("[Brak polskiego tekstu (", main_all)
        self.assertNotIn("Untranslated English Line Sentinel", main_all)
        self.assertNotIn("Nieznana fraza bez polskiego przekładu", main_all)

        # 4. Bezpośrednio z częściowej zwrotki (--zwrotka + --tylko-zwrotka)
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
        self.assertIn("Cześć z samej zwrotki!", (out_zwr / "01_watek_glowny.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
