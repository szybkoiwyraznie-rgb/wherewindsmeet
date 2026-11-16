from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools import czytanka_czysta


class _Tekst:
    def __init__(self, wiersz, zh, en=None):
        self.w = wiersz
        self.zrodlo = zh
        self.en = en
        self.z_en = False


class _Indeks:
    zrodla = [["active_interact_way", "button_name", 1]]

    def __init__(self):
        self.teksty = {"z-swiatka": _Tekst((0, "200046001"), "龙纹标记", "Dragon Pattern Marker")}


class NazwyTests(unittest.TestCase):
    def test_klucz_nazwy_ma_przeklad(self):
        nazwy = {"173": {"id": 173, "k": "abc", "zh": "龙纹标记", "en": "Dragon Pattern Mark"}}
        tekst, klucz = czytanka_czysta._tekst_nazwy(_Indeks(), {"abc": "Znak Smoczego Wzoru"},
                                                    {}, 173, nazwy)
        self.assertEqual((tekst, klucz), ("Znak Smoczego Wzoru", "abc"))

    def test_bez_przekladu_gwiazdka_i_angielski(self):
        nazwy = {"173": {"id": 173, "k": "abc", "zh": "龙纹标记", "en": "Dragon Pattern Mark"}}
        tekst, klucz = czytanka_czysta._tekst_nazwy(_Indeks(), {}, {}, 173, nazwy)
        self.assertEqual(klucz, "abc")
        self.assertTrue(tekst.startswith("\\*"))
        self.assertIn("Dragon Pattern Mark", tekst)

    def test_bez_mapy_zostaje_swiadek(self):
        tekst, klucz = czytanka_czysta._tekst_nazwy(
            _Indeks(), {"z-swiatka": "Znak"}, {"200046001": "z-swiatka"}, "200046001", {})
        self.assertEqual((tekst, klucz), ("Znak", "z-swiatka"))

    def test_bez_identyfikatora(self):
        self.assertEqual(czytanka_czysta._tekst_nazwy(_Indeks(), {}, {}, None, {}), ("", None))

    def test_wczytaj_nazwy_pomija_wiersze_bez_klucza(self):
        with tempfile.TemporaryDirectory() as katalog:
            Path(katalog, "nazwy.jsonl").write_text(
                json.dumps({"id": 1, "k": "aaa", "zh": "一", "en": "One"}) + "\n"
                + json.dumps({"id": 2, "zh": "二"}) + "\n",
                encoding="utf-8")
            mapa = czytanka_czysta._wczytaj_nazwy(katalog)
        self.assertEqual(list(mapa), ["1"])
        self.assertEqual(mapa["1"]["k"], "aaa")

    def test_brak_pliku_nazw(self):
        with tempfile.TemporaryDirectory() as katalog:
            self.assertEqual(czytanka_czysta._wczytaj_nazwy(katalog), {})


if __name__ == "__main__":
    unittest.main()
