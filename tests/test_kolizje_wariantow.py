"""Kolizje wariantów: ta sama chińska linia, różne angielskie znaczenia.

W wyciągu jedna linia ZH bywa zapisana kilka razy (np. w `text_msg` i w warstwie
`text_msg__grey`), a angielskie wersje tych wariantów są różne. Patcher i budowniczy
łatki stoją przed tym samym pytaniem: którą polską wersję wstawić w miejsce tekstu ZH?
Dotąd liczyło się podobieństwo do **angielskiej treści, która jest już w pliku gry**,
więc dokładne trafienie w wariant bez przekładu blokowało przejęcie przekładu od
bliźniaka — i cała linia zostawała po angielsku.
"""

import unittest

from tools import patcher_wwm, tlumaczenie, zbuduj_latke

WARIANTY = [
    ["klucz-podstawowy", "After him! Don't let him flee!"],
    ["klucz-grey", "After him! Don't let him get away!"],
]
ODLEGLE = [
    ["klucz-podstawowy", "Ha."],
    ["klucz-grey", "Ah..."],
]


class PatcherTests(unittest.TestCase):
    def test_przejmuje_przeklad_bilzniaka_gdy_dokladne_trafienie_jest_bez_przekladu(self):
        # w pliku gry stoi angielski wariantu `grey`; przekład ma tylko wariant podstawowy
        po_kluczu = {"klucz-podstawowy": "Za nim!"}
        self.assertEqual(
            patcher_wwm._dopasuj_kolizje(WARIANTY, "After him! Don't let him get away!", po_kluczu),
            ("Za nim!", "podobne"),
        )

    def test_dokladne_trafienie_z_przekladem_wygrywa(self):
        po_kluczu = {"klucz-podstawowy": "RAZ", "klucz-grey": "DWA"}
        self.assertEqual(
            patcher_wwm._dopasuj_kolizje(WARIANTY, "After him! Don't let him get away!", po_kluczu),
            ("DWA", "dokladne"),
        )

    def test_rozne_znaczenia_nie_podstawiaja_cudzego_przekladu(self):
        # „Ha.” i „Ah…” to różne znaczenia tej samej linii — lepiej zostawić angielski
        # i wpisać własne tłumaczenie, niż wstawić polski tekst o innym znaczeniu
        self.assertEqual(patcher_wwm._dopasuj_kolizje(ODLEGLE, "Ah...", {"klucz-podstawowy": "Ha."}), (None, ""))

    def test_bez_przekladu_zwraca_none(self):
        self.assertEqual(patcher_wwm._dopasuj_kolizje(WARIANTY, "coś zupełnie innego", {}), (None, ""))


class ZbudujLatkeTests(unittest.TestCase):
    def test_ta_sama_regula_w_budowniczym_latki(self):
        magazyn = tlumaczenie.Magazyn()
        magazyn.po_kluczu["klucz-podstawowy"] = "Za nim!"
        self.assertEqual(
            zbuduj_latke._dopasuj_kolizje(WARIANTY, "After him! Don't let him get away!", magazyn), "Za nim!"
        )

    def test_rozne_znaczenia_zostaja_bez_polskiego_takze_w_latce(self):
        magazyn = tlumaczenie.Magazyn()
        magazyn.po_kluczu["klucz-podstawowy"] = "Ha."
        self.assertIsNone(zbuduj_latke._dopasuj_kolizje(ODLEGLE, "Ah...", magazyn))

    def test_pusty_magazyn_nie_wymysla_przekladu(self):
        self.assertIsNone(zbuduj_latke._dopasuj_kolizje(WARIANTY, "After him! Don't let him get away!", tlumaczenie.Magazyn()))


if __name__ == "__main__":
    unittest.main()
