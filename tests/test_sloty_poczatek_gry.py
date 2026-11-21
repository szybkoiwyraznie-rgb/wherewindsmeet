"""Trzy przykłady właściciela wpadają do właściwych zbiorów braków."""

from __future__ import annotations

import unittest

from tools import indeks as indeks_mod
from tools import sloty_poczatek_gry as sloty
from tools import tlumaczenie as magazyn_mod


class SlotyPoczatekGryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ix = indeks_mod.wczytaj("index")
        cls.mag = magazyn_mod.wczytaj("tlumaczenie")
        cls.dane = sloty.zbior(cls.ix, cls.mag)

    def test_przyklad_ochlapy_miesa_to_opis_przedmiotu(self):
        # describe_str wiersza 3602002, nazwa już PL („Ochłapy mięsa”).
        klucz = None
        for k, tekst in self.ix.teksty.items():
            if tekst.en and tekst.en.startswith("Succulent small meat chunks"):
                klucz = k
                break
        self.assertIsNotNone(klucz)
        self.assertIn(klucz, self.dane["1_przedmioty"]["klucze"])

    def test_przyklad_wrzodow_to_opis_choroby(self):
        klucz = None
        for k, tekst in self.ix.teksty.items():
            if tekst.en and "Sores and ulcers fester" in tekst.en:
                klucz = k
                break
        self.assertIsNotNone(klucz)
        self.assertIn(klucz, self.dane["2_choroby"]["klucze"])

    def test_przyklad_feng_ruby_to_quest_luczniczy(self):
        klucz = None
        for k, tekst in self.ix.teksty.items():
            if tekst.zrodlo == "这些鸟儿行动非常灵活，咱们可得瞄准了。":
                klucz = k
                break
        self.assertIsNotNone(klucz)
        self.assertIn(klucz, self.dane["3_luczniczy"]["klucze"])

    def test_suma_bez_pokryc(self):
        a = set(self.dane["1_przedmioty"]["klucze"])
        b = set(self.dane["2_choroby"]["klucze"])
        c = set(self.dane["3_luczniczy"]["klucze"])
        self.assertFalse(a & b or a & c or b & c)
        self.assertEqual(self.dane["suma_trzech"]["kluczy"], len(a | b | c))
        self.assertGreater(self.dane["suma_trzech"]["kluczy"], 900)


if __name__ == "__main__":
    unittest.main()
