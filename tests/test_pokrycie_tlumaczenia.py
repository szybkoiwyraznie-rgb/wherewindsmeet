from __future__ import annotations

import unittest
from pathlib import Path

from tools import indeks, mapa_tekstow, pokrycie_tlumaczenia, tlumaczenie

K = mapa_tekstow.klucz


def tekst(zrodlo: str, en: str | None, *, z_en: bool = False) -> indeks.Tekst:
    return indeks.Tekst(zrodlo=zrodlo, en=None if z_en else en, n=1, w=None, z_en=z_en)


def indeks_testowy() -> indeks.Indeks:
    ix = indeks.Indeks(Path("index"), {"format": indeks.FORMAT})
    teksty = {
        K("linia prologu"): tekst("linia prologu", "prologue line"),
        K("powitanie"): tekst("powitanie", "greeting"),
        K("wiersz ballady"): tekst("wiersz ballady", "ballad verse"),
        K("wiersz filmu"): tekst("wiersz filmu", "movie verse"),
        K("wpis intro"): tekst("wpis intro", "intro line"),
        K("kwestia sceny"): tekst("kwestia sceny", "scene line"),
        K("plansza"): tekst("plansza", "board"),
        K("tylko angielski"): tekst("only english", "only english", z_en=True),
    }
    ix.teksty = teksty
    ix.cutsceny_kontekst = {
        "napis": [
            {"typ": "napis", "wiersz": 590000, "k": K("linia prologu")},
            {"typ": "napis", "wiersz": 590001, "k": K("powitanie")},
            {"typ": "napis", "wiersz": 590005, "k": K("tylko angielski")},
        ],
        "intro": [{"typ": "intro", "id": 1, "czas": 1.0, "k": K("wpis intro")}],
        "film": [
            {"typ": "film", "film": 1, "id": 11, "czas": 1.0, "k": K("wiersz ballady")},
            {"typ": "film", "film": 2, "id": 21, "czas": 2.0, "k": K("wiersz filmu")},
        ],
    }
    ix.sceny = {
        10: {"d": 10, "e": [["k", 0, K("kwestia sceny")], ["p", -1, K("plansza")]]},
        11: {"d": 11, "e": [["k", 0, K("linia prologu"), True, "00000000000000a1"]]},
        20: {"d": 20, "u": 10, "p": "对话-qiancen", "e": [["k", 0, K("kwestia sceny")]]},
        21: {"d": 21, "u": 10, "p": "对话-qiancen", "e": [["k", 0, K("wpis intro")], ["k", 0, K("linia prologu")]]},
    }
    ix.teksty[K("kwestia sceny")] = tekst("kwestia sceny", "scene line")
    return ix


def magazyn_testowy() -> tlumaczenie.Magazyn:
    mag = tlumaczenie.Magazyn()
    mag.po_kluczu[K("linia prologu")] = "linia prologu PL"
    mag.po_kluczu[K("wiersz ballady")] = "wiersz ballady PL"
    mag.po_id["00000000000000a1"] = "kwestia wariantu PL"
    return mag


class SekcjeTests(unittest.TestCase):
    def test_sekcje_licza_wpisy_przeklady_i_braki(self):
        rows = pokrycie_tlumaczenia.sekcje(indeks_testowy(), magazyn_testowy())
        wedlug_nazwy = {row["sekcja"]: row for row in rows}

        napisy = wedlug_nazwy["napisy cutscen (text_msg 590000–592694)"]
        self.assertEqual((napisy["elementy"], napisy["przetlumaczone"], napisy["braki"]), (3, 1, 2))
        self.assertEqual(napisy["procent"], 33.3)

        film = wedlug_nazwy["napisy filmowe (entry_collect_movie_subtitle_data)"]
        self.assertEqual((film["elementy"], film["przetlumaczone"]), (2, 1))
        self.assertEqual(wedlug_nazwy["  film 2"]["procent"], 0.0)
        self.assertEqual(wedlug_nazwy["  film 1"]["procent"], 100.0)

        intro = wedlug_nazwy["intro (wds_oneday_intro_cutscene_data)"]
        self.assertEqual((intro["elementy"], intro["przetlumaczone"]), (1, 0))

    def test_sekcja_scen_liczy_takze_warianty_plci(self):
        ix = indeks_testowy()
        rows = pokrycie_tlumaczenia.sekcje(ix, magazyn_testowy())
        sceny = next(row for row in rows if row["sekcja"].startswith("sceny"))
        # dwa elementy zwykłe bez przekładu + wariant płci znaleziony w `po_id`
        self.assertEqual((sceny["elementy"], sceny["przetlumaczone"]), (3, 1))
        bez_wariantu = pokrycie_tlumaczenia.sekcje(ix, tlumaczenie.Magazyn())
        sceny_bez = next(row for row in bez_wariantu if row["sekcja"].startswith("sceny"))
        self.assertEqual(sceny_bez["przetlumaczone"], 0)

    def test_bez_scen_pomija_najwieksza_sekcje(self):
        row = pokrycie_tlumaczenia.sekcje(indeks_testowy(), magazyn_testowy(), sceny=False)
        self.assertFalse(any(item["sekcja"].startswith("sceny") for item in row))
        self.assertEqual(row[-1]["sekcja"], "wszystkie unikalne teksty wyciągu")


class PrzerywnikiTests(unittest.TestCase):
    def test_sekcja_przerywnikow_liczy_tylko_sceny_ui_typu_przerywnika(self):
        rows = pokrycie_tlumaczenia.sekcje(indeks_testowy(), magazyn_testowy())
        sekcja = next(row for row in rows if row["sekcja"].startswith("sceny przerywników"))
        # scena 20 (1 wpis bez PL) + scena 21 (2 wpisy: 1 bez PL, 1 z PL); scena 10/11 nie należą do sekcji
        self.assertEqual((sekcja["elementy"], sekcja["przetlumaczone"]), (3, 1))

    def test_braki_przerywnikow_niosa_numer_sceny_i_tekst(self):
        rows = pokrycie_tlumaczenia.braki_przerywnikow(indeks_testowy(), magazyn_testowy())
        self.assertEqual({row["scena"] for row in rows}, {20, 21})
        intro = next(row for row in rows if row["klucz"] == K("wpis intro"))
        self.assertEqual(intro["en"], "intro line")
        self.assertEqual(intro["projekt"], "对话-qiancen")

    def test_zakres_scen_ogranicza_braki(self):
        ix, mag = indeks_testowy(), magazyn_testowy()
        self.assertEqual({row["scena"] for row in pokrycie_tlumaczenia.braki_przerywnikow(ix, mag, od=21)}, {21})
        self.assertEqual({row["scena"] for row in pokrycie_tlumaczenia.braki_przerywnikow(ix, mag, do=20)}, {20})
        self.assertEqual(pokrycie_tlumaczenia.braki_przerywnikow(ix, mag, od=30), [])

    def test_sceny_przerywnikow_sortowane_po_numerze(self):
        numery = [numer for numer, _sloty in pokrycie_tlumaczenia.sceny_przerywnikow(indeks_testowy())]
        self.assertEqual(numery, [20, 21])


class ArkuszTests(unittest.TestCase):
    def test_arkusz_ma_format_pakietu_i_wszystkie_braki(self):
        tresc = pokrycie_tlumaczenia.arkusz(indeks_testowy(), magazyn_testowy())
        self.assertIn("klucz:", tresc)
        self.assertIn("   PL:", tresc)
        self.assertIn("## Sceny przerywników", tresc)
        self.assertIn("## Napisy cutscen", tresc)
        # każdy brak z obu sekcji ma dokładnie jedno miejsce na PL
        ix, mag = indeks_testowy(), magazyn_testowy()
        oczekiwane = len(pokrycie_tlumaczenia.braki_kinowe(ix, mag)) + len(pokrycie_tlumaczenia.braki_przerywnikow(ix, mag))
        self.assertEqual(tresc.count("\n   PL:\n"), oczekiwane)

    def test_arkusz_moze_objac_tylko_przerywniki(self):
        tresc = pokrycie_tlumaczenia.arkusz(indeks_testowy(), magazyn_testowy(), kinowe=False)
        self.assertNotIn("## Napisy cutscen", tresc)
        self.assertIn("## Sceny przerywników", tresc)

    def test_arkusz_moze_objac_tylko_kinowe(self):
        tresc = pokrycie_tlumaczenia.arkusz(indeks_testowy(), magazyn_testowy(), przerywniki=False)
        self.assertIn("## Napisy cutscen", tresc)
        self.assertNotIn("## Sceny przerywników", tresc)


class BrakiTests(unittest.TestCase):
    def test_braki_obejmuja_tylko_wiersze_bez_przekladu(self):
        rows = pokrycie_tlumaczenia.braki_kinowe(indeks_testowy(), magazyn_testowy())
        klucze = {row["klucz"] for row in rows}
        self.assertIn(K("powitanie"), klucze)
        self.assertIn(K("wiersz filmu"), klucze)
        self.assertIn(K("wpis intro"), klucze)
        self.assertNotIn(K("linia prologu"), klucze)
        self.assertNotIn(K("wiersz ballady"), klucze)

    def test_braki_niosa_kontekst_i_zrodlo(self):
        rows = pokrycie_tlumaczenia.braki_kinowe(indeks_testowy(), magazyn_testowy())
        filmowy = next(row for row in rows if row["typ"] == "film")
        self.assertEqual(filmowy["film"], 2)
        self.assertEqual(filmowy["id"], 21)
        self.assertEqual(filmowy["en"], "movie verse")
        napis = next(row for row in rows if row["typ"] == "napis")
        self.assertIn(napis["wiersz"], (590001, 590005))

    def test_kolejnosc_brakow_jest_stala(self):
        rows = pokrycie_tlumaczenia.braki_kinowe(indeks_testowy(), magazyn_testowy())
        typy = [row["typ"] for row in rows]
        self.assertEqual(typy, sorted(typy, key=pokrycie_tlumaczenia.TYPY_KINOWE.index))

    def test_pusty_magazyn_oznacza_wszystko_jako_braki(self):
        rows = pokrycie_tlumaczenia.braki_kinowe(indeks_testowy(), tlumaczenie.Magazyn())
        self.assertEqual(len(rows), 6)


class SerieTests(unittest.TestCase):
    def test_ciagle_numery_tworza_jedna_serie(self):
        rows = [{"wiersz": 1}, {"wiersz": 2}, {"wiersz": 3}]
        self.assertEqual(len(pokrycie_tlumaczenia.serie(rows, pole="wiersz")), 1)

    def test_luka_rozcina_serie(self):
        rows = [{"wiersz": 1}, {"wiersz": 2}, {"wiersz": 9}, {"wiersz": 10}]
        serie = pokrycie_tlumaczenia.serie(rows, pole="wiersz")
        self.assertEqual([len(grupa) for grupa in serie], [2, 2])

    def test_odstep_zero_grupuje_po_wartosci(self):
        rows = [{"film": 2}, {"film": 2}, {"film": 3}]
        serie = pokrycie_tlumaczenia.serie(rows, pole="film", odstep=0)
        self.assertEqual([len(grupa) for grupa in serie], [2, 1])


class SlotTests(unittest.TestCase):
    def test_zwykly_element_uzywa_klucza_tekstu(self):
        self.assertEqual(pokrycie_tlumaczenia.slot_elementu(["k", 0, "abc"]), "abc")

    def test_wariant_plci_uzywa_identyfikatora(self):
        self.assertEqual(pokrycie_tlumaczenia.slot_elementu(["k", 0, "abc", True, "00000000000000a1"]), "@00000000000000a1")

    def test_element_bez_whatu_plci_nie_jest_wariantem(self):
        self.assertEqual(pokrycie_tlumaczenia.slot_elementu(["k", 0, "abc", False, None]), "abc")


class SzukajTests(unittest.TestCase):
    def test_szukanie_po_angielskim_oznacza_brak_przekladu(self):
        rows = pokrycie_tlumaczenia.szukaj(indeks_testowy(), magazyn_testowy(), "verse")
        self.assertEqual(len(rows), 2)
        przetlumaczony = next(row for row in rows if row["gdzie"] == ["film 1 id 11"])
        self.assertEqual(przetlumaczony["pl"], "wiersz ballady PL")
        bez_przekladu = next(row for row in rows if row["gdzie"] == ["film 2 id 21"])
        self.assertIsNone(bez_przekladu["pl"])
        self.assertEqual(bez_przekladu["en"], "movie verse")

    def test_szukanie_po_polskim_znajduje_przeklad(self):
        rows = pokrycie_tlumaczenia.szukaj(indeks_testowy(), magazyn_testowy(), "ballady PL")
        self.assertEqual(rows[0]["pl"], "wiersz ballady PL")

    def test_szukanie_po_chinskim_i_ignorowanie_wielkosci_liter(self):
        self.assertTrue(pokrycie_tlumaczenia.szukaj(indeks_testowy(), magazyn_testowy(), "WIERSZ"))
        self.assertTrue(pokrycie_tlumaczenia.szukaj(indeks_testowy(), magazyn_testowy(), "movie verse"))

    def test_szukanie_pusta_fraza_jest_bledem(self):
        with self.assertRaises(ValueError):
            pokrycie_tlumaczenia.szukaj(indeks_testowy(), magazyn_testowy(), "   ")

    def test_limit_ogranicza_wyniki(self):
        rows = pokrycie_tlumaczenia.szukaj(indeks_testowy(), magazyn_testowy(), "e", limit=2)
        self.assertEqual(len(rows), 2)

    def test_mapa_scen_podaje_numer_pierwszej_sceny(self):
        mapa = pokrycie_tlumaczenia.mapa_scen(indeks_testowy())
        self.assertEqual(mapa[K("kwestia sceny")], 10)
        self.assertEqual(mapa["@00000000000000a1"], 11)

    def test_wynik_dla_wariantu_dostaje_numer_sceny(self):
        ix = indeks_testowy()
        mag = tlumaczenie.Magazyn()
        rows = pokrycie_tlumaczenia.szukaj(ix, mag, "kwestia", sceny=pokrycie_tlumaczenia.mapa_scen(ix))
        self.assertEqual(rows[0]["scena"], 10)


class TekstTests(unittest.TestCase):
    def test_wielolinijkowy_tekst_trafia_do_jednej_linii(self):
        self.assertEqual(pokrycie_tlumaczenia._tekst_na_jedna_linie("a\nb"), "a / b")
        self.assertEqual(pokrycie_tlumaczenia._tekst_na_jedna_linie(None), "")

    def test_skracanie_zachowuje_krotkie_teksty(self):
        self.assertEqual(pokrycie_tlumaczenia._skroc("krotki"), "krotki")
        dlugi = "x" * 400
        skrocony = pokrycie_tlumaczenia._skroc(dlugi)
        self.assertLessEqual(len(skrocony), 160)
        self.assertTrue(skrocony.endswith("…"))


if __name__ == "__main__":
    unittest.main()
