from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools import audyt_zakresu, indeks, mapa_tekstow, tlumaczenie

K = mapa_tekstow.klucz


def _tekst(klucz: str, zrodlo: int, wiersz: str, en: str = "line") -> indeks.Tekst:
    return indeks.Tekst(zrodlo=klucz, en=en, n=1, w=(zrodlo, wiersz), z_en=False)


def indeks_testowy() -> indeks.Indeks:
    ix = indeks.Indeks(Path("index"), {"format": indeks.FORMAT})
    ix.zrodla = [
        ["tasks", "task_target_str", 1],
        ["tasks_envelop_data", "text", 1],
        ["text_msg", "content", 1],
        ["manual_items", "describe", 1],
        ["ccs_text_msg", "content", 1],
        ["programmer_text_msg", "content", 1],
        ["guider_tujian_data", "manual_name", 1],
        ["guider_tujian_data", "talk_content[]", 1],
    ]
    ix.teksty = {
        K("hint"): _tekst("hint", 0, "220005"),
        K("lista"): _tekst("lista", 1, "5"),
        K("chwost"): _tekst("chwost", 2, "1800045"),
        K("opis przedmiotu"): _tekst("opis przedmiotu", 3, "1223001"),
        K("ślad"): _tekst("ślad", 4, "collection_1"),
        K("etykieta"): _tekst("etykieta", 5, "EQUIP_UNRETRACED"),
        K("nazwa compendium"): _tekst("nazwa compendium", 6, "9101101"),
        K("opis compendium"): _tekst("opis compendium", 7, "9101101"),
        K("kwestia sceny"): _tekst("kwestia sceny", 7, "9101101"),
    }
    ix.teksty[K("kwestia sceny")] = indeks.Tekst(
        zrodlo="kwestia sceny", en="scene line", n=1, w=None, z_en=False
    )
    ix.sceny = {
        1: {"d": 1, "m": [701], "e": [["k", 0, K("kwestia sceny")]]},
        2: {"d": 2, "m": [701], "e": [["k", 0, K("brak sceny")]]},
        3: {"d": 3, "m": [999], "e": [["k", 0, K("inna kraina")]]},
    }
    ix.teksty[K("brak sceny")] = indeks.Tekst(
        zrodlo="brak sceny", en="missing", n=1, w=None, z_en=False
    )
    ix.teksty[K("inna kraina")] = indeks.Tekst(
        zrodlo="inna kraina", en="other", n=1, w=None, z_en=False
    )
    return ix


def magazyn_testowy() -> tlumaczenie.Magazyn:
    mag = tlumaczenie.Magazyn()
    mag.po_kluczu[K("hint")] = "hint PL"
    mag.po_kluczu[K("chwost")] = "chwost PL"
    mag.po_kluczu[K("kwestia sceny")] = "kwestia PL"
    mag.po_kluczu[K("nazwa compendium")] = "nazwa PL"
    return mag


class AudytTests(unittest.TestCase):
    def test_kategorie_licza_unikalne_klucze_i_udzial_ai(self):
        raport = audyt_zakresu.audyt(
            indeks_testowy(), magazyn_testowy(), mapy={701}, ai={K("hint"), K("chwost")}
        )
        wedlug = {row["kategoria"]: row for row in raport["kategorie"]}

        hinty = wedlug["1 hinty zadań"]
        self.assertEqual((hinty["razem"], hinty["przetlumaczone"], hinty["braki"]), (1, 1, 0))
        self.assertEqual((hinty["tlumacz"], hinty["ai"]), (0, 1))

        listy = wedlug["2 listy"]
        self.assertEqual((listy["razem"], listy["przetlumaczone"]), (1, 0))

        przedmioty = wedlug["3 przedmioty fabularne"]
        self.assertEqual((przedmioty["razem"], przedmioty["przetlumaczone"], przedmioty["ai"]), (2, 1, 1))

        opisy = wedlug["4 opisy przedmiotów"]
        self.assertEqual((opisy["razem"], opisy["przetlumaczone"]), (2, 0))

    def test_sceny_tylko_z_map_pierwszej_krainy(self):
        raport = audyt_zakresu.audyt(indeks_testowy(), magazyn_testowy(), mapy={701})
        sceny = next(row for row in raport["kategorie"] if row["kategoria"].startswith("6 "))
        self.assertEqual((sceny["razem"], sceny["przetlumaczone"], sceny["braki"]), (2, 1, 1))

    def test_podzial_scen_wg_powiazania(self):
        ix = indeks.Indeks(Path("index"), {"format": indeks.FORMAT})
        ix.teksty = {
            K("kit"): indeks.Tekst("kit", None, 1, None, False),
            K("swiat"): indeks.Tekst("swiat", None, 1, None, False),
            K("zadanie"): indeks.Tekst("zadanie", None, 1, None, False),
            K("samo"): indeks.Tekst("samo", None, 1, None, False),
        }
        ix.sceny = {
            1: {"d": 1, "m": [701], "e": [["k", 0, K("kit")]]},
            2: {"d": 2, "m": [701], "e": [["k", 0, K("swiat")]], "r": [[523, "spaces.s501.trap#1"]]},
            3: {"d": 3, "m": [701], "e": [["k", 0, K("zadanie")]]},
            4: {"d": 4, "m": [701], "e": [["k", 0, K("samo")]]},
            5: {"d": 5, "m": [999], "e": [["k", 0, K("inna")]]},
        }
        ix.teksty[K("inna")] = indeks.Tekst("inna", None, 1, None, False)
        podzial = audyt_zakresu.podzial_scen(
            ix, tlumaczenie.Magazyn(), {701}, kity={1}, zadania_sceny={3: {10}}
        )
        grupy = {row["grupa"]: row["klucze"] for row in podzial["grupy"]}
        self.assertEqual(grupy["ambient (kity)"], 1)
        self.assertEqual(grupy["wyzwalane ze świata"], 1)
        self.assertEqual(grupy["zadaniowe"], 1)
        self.assertEqual(grupy["bez powiązania"], 1)
        self.assertEqual(podzial["razem"], 4)

    def test_podzial_scen_pomija_przetlumaczone(self):
        ix = indeks.Indeks(Path("index"), {"format": indeks.FORMAT})
        ix.teksty = {K("kit"): indeks.Tekst("kit", None, 1, None, False)}
        ix.sceny = {1: {"d": 1, "m": [701], "e": [["k", 0, K("kit")]]}}
        mag = tlumaczenie.Magazyn()
        mag.po_kluczu[K("kit")] = "gotowe"
        self.assertEqual(audyt_zakresu.podzial_scen(ix, mag, {701}, kity={1})["razem"], 0)

    def test_compendium_dzieli_nazwy_i_opisy(self):
        raport = audyt_zakresu.audyt(indeks_testowy(), magazyn_testowy(), mapy={701})
        comp = raport["compendium"]
        self.assertEqual((comp["nazwy"]["razem"], comp["nazwy"]["przetlumaczone"]), (1, 1))
        self.assertEqual((comp["opisy"]["razem"], comp["opisy"]["braki"]), (1, 1))

    def test_klucze_ai_czytaja_tylko_niepuste_pl(self):
        with tempfile.TemporaryDirectory() as katalog:
            path = Path(katalog) / "zwrotka.md"
            path.write_text(
                "## element\n\n    klucz: aaaaaaaaaaaaaaaa\n    PL: tekst\n\n"
                "## element\n\n    klucz: bbbbbbbbbbbbbbbb\n    PL:\n",
                encoding="utf-8",
            )
            self.assertEqual(audyt_zakresu.klucze_ai([path]), {"aaaaaaaaaaaaaaaa"})

    def test_mapy_krainy_domyslnie_pierwsza_i_po_nazwie(self):
        with tempfile.TemporaryDirectory() as katalog:
            Path(katalog, "prowincje.json").write_text(
                json.dumps(
                    [{"kraina": "燕南", "mapy": [1, 501, 701]}, {"kraina": "清河", "mapy": [711]}],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            self.assertEqual(audyt_zakresu.mapy_krainy(katalog), ("燕南", {1, 501, 701}))
            self.assertEqual(audyt_zakresu.mapy_krainy(katalog, "清河"), ("清河", {711}))
            with self.assertRaises(audyt_zakresu.AudytError):
                audyt_zakresu.mapy_krainy(katalog, "nie ma")


if __name__ == "__main__":
    unittest.main()
