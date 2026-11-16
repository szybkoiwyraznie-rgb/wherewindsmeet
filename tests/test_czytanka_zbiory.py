from __future__ import annotations

import unittest

from tools import czytanka_czysta


class _Tekst:
    def __init__(self, wiersz, zh, en=None):
        self.w = wiersz
        self.zrodlo = zh
        self.en = en
        self.z_en = False


class _Indeks:
    """Minimalny wyciąg: dwie kolumny jednej tabeli zbiorów."""

    zrodla = [
        ["region_collect_jianwen_data", "jianwen_title", 1],
        ["region_collect_jianwen_data", "jianwen_text", 1],
    ]

    def __init__(self):
        self.teksty = {
            "tytul1": _Tekst((0, "10"), "标题一", "Title one"),
            "tekst1": _Tekst((1, "10"), "正文一", "Body one"),
            "tytul2": _Tekst((0, "11"), "标题二", "Title two"),
            "tekst2": _Tekst((1, "11"), "正文二", "Body two"),
        }


class ZbioryTests(unittest.TestCase):
    def test_karta_z_przekladem(self):
        linie = czytanka_czysta._zbiory(_Indeks(), {"tytul1": "Tytuł pierwszy", "tekst1": "Treść pierwsza"}, set(), {})
        self.assertIn("# Zbiory i pamiątki — zasłyszane historie", linie)
        self.assertIn("**Tytuł pierwszy:** Treść pierwsza", linie)

    def test_karta_bez_przekladu_ma_gwiazdke(self):
        linie = czytanka_czysta._zbiory(_Indeks(), {"tytul1": "Tytuł pierwszy", "tekst1": "Treść"}, set(), {})
        self.assertIn("**\\*Title two:** \\*Body two", linie)

    def test_tekst_uzyty_w_scenie_nie_powtarza_sie(self):
        linie = czytanka_czysta._zbiory(_Indeks(), {"tytul1": "T", "tekst1": "X"}, {"tekst1", "tekst2"}, {})
        self.assertNotIn("# Zbiory i pamiątki — zasłyszane historie", linie)

    def test_licznik_kart(self):
        statystyka: dict = {}
        czytanka_czysta._zbiory(_Indeks(), {"tytul1": "Tytuł", "tekst1": "Treść"}, set(), statystyka)
        self.assertEqual(statystyka["zbiory"], 2)


if __name__ == "__main__":
    unittest.main()
