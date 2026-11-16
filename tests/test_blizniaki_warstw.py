"""Bliźniaki tej samej linii w innej warstwie tabeli (`text_msg` / `text_msg__grey`).

Klucz przekładu to SHA-256 dokładnej treści, a warstwa „szara” napisów ma mówcę
wpisanego w treść i inne odstępy. Ta sama linia dostawała więc drugi, pusty klucz
— i zostawała po angielsku, mimo że polski przekład już istniał.
"""

import unittest

from tools import indeks, tlumaczenie


TABELA = 0


def tekst(zrodlo: str, en: str, wiersz: str = "590339") -> indeks.Tekst:
    return indeks.Tekst(zrodlo=zrodlo, en=en, n=1, w=(TABELA, wiersz), z_en=False)


def indeks_testowy() -> indeks.Indeks:
    ix = indeks.Indeks(katalog=None, manifest={})
    ix.zrodla = [
        ("text_msg", "content", "text_msg"),
        ("text_msg__grey", "content", "text_msg"),
    ]
    ix.teksty = {
        "aaaa000000000001": tekst("尚有一饮入喉", "still time for one last drink."),
        "aaaa000000000002": tekst(" 尚有一饮入喉 ", "a drink to wet your throat."),
        # inny wiersz, ten sam chiński tekst — kolizja znaczeń, nie bliźniak
        "aaaa000000000003": tekst("尚有一饮入喉", "Line Beta", wiersz="590999"),
    }
    ix.teksty["aaaa000000000002"] = ix.teksty["aaaa000000000002"]._replace(w=(1, "590339"))
    return ix


class BlizniakiTests(unittest.TestCase):
    def test_warstwa_grey_przejmuje_przeklad_tego_samego_wiersza(self):
        ix = indeks_testowy()
        magazyn = tlumaczenie.Magazyn()
        magazyn.po_kluczu["aaaa000000000001"] = "zawsze znajdzie się czas na ostatnią czarkę"
        raport = tlumaczenie.doloz_blizniaki(magazyn, ix)
        self.assertEqual(raport["dodane"], 1)
        self.assertEqual(magazyn.przeklad("aaaa000000000002"), "zawsze znajdzie się czas na ostatnią czarkę")

    def test_inny_wiersz_o_tym_samym_tekscie_nie_dostaje_przekladu(self):
        ix = indeks_testowy()
        magazyn = tlumaczenie.Magazyn()
        magazyn.po_kluczu["aaaa000000000001"] = "zawsze znajdzie się czas na ostatnią czarkę"
        tlumaczenie.doloz_blizniaki(magazyn, ix)
        self.assertIsNone(magazyn.przeklad("aaaa000000000003"))

    def test_istniejacy_przeklad_nie_jest_nadpisywany(self):
        ix = indeks_testowy()
        magazyn = tlumaczenie.Magazyn()
        magazyn.po_kluczu["aaaa000000000001"] = "wersja główna"
        magazyn.po_kluczu["aaaa000000000002"] = "wersja szara"
        raport = tlumaczenie.doloz_blizniaki(magazyn, ix)
        self.assertEqual(raport["dodane"], 0)
        self.assertEqual(magazyn.przeklad("aaaa000000000002"), "wersja szara")

    def test_tekst_o_innej_tresci_w_tym_samym_wierszu_nie_jest_laczony(self):
        ix = indeks_testowy()
        ix.teksty["aaaa000000000004"] = tekst("别的台词", "different line")._replace(w=(1, "590339"))
        magazyn = tlumaczenie.Magazyn()
        magazyn.po_kluczu["aaaa000000000001"] = "wersja główna"
        tlumaczenie.doloz_blizniaki(magazyn, ix)
        self.assertIsNone(magazyn.przeklad("aaaa000000000004"))

    def test_uzupelnienie_jest_tylko_w_pamieci(self):
        """Do plików magazynu trafiają wyłącznie przekłady ludzi."""
        ix = indeks_testowy()
        magazyn = tlumaczenie.Magazyn()
        magazyn.po_kluczu["aaaa000000000001"] = "wersja główna"
        tlumaczenie.doloz_blizniaki(magazyn, ix)
        self.assertIn("aaaa000000000001", magazyn.po_kluczu)
        self.assertIn("aaaa000000000002", magazyn.po_kluczu)


if __name__ == "__main__":
    unittest.main()
