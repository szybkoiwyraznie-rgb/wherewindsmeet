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
    zrodla = [["active_interact_way", "button_name", 2]]

    def __init__(self):
        self.teksty = {
            "poi1": _Tekst((0, "200046001"), "龙纹标记", "Dragon Pattern Mark"),
            "poi2": _Tekst((0, "200046002"), "石碑", "Stone Tablet"),
        }


class PoiTests(unittest.TestCase):
    def _katalog(self, wiersze: list[dict]):
        katalog = tempfile.TemporaryDirectory()
        Path(katalog.name, "poi.jsonl").write_text(
            "".join(json.dumps(w, ensure_ascii=False) + "\n" for w in wiersze), encoding="utf-8")
        return katalog

    def test_poi_z_przekladem_i_scena(self):
        with self._katalog([{"id": 200046001, "dialog": 4700001,
                             "storyline": "client/dialogs/hjt/sxd_longwenbiaoji.etsb"}]) as katalog:
            linie = czytanka_czysta._poi(_Indeks(), {"poi1": "Znak Smoczego Wzoru"}, set(), {}, katalog)
        self.assertIn("# Punkty na mapie (POI)", linie)
        self.assertIn("**Znak Smoczego Wzoru** — scena 4700001", linie)

    def test_bez_dowodu_nie_ma_numeru_sceny(self):
        with self._katalog([{"id": 200046001, "dialog": None,
                             "storyline": "client/dialogs/hjt/sxd_longwenbiaoji.etsb"}]) as katalog:
            linie = czytanka_czysta._poi(_Indeks(), {"poi1": "Znak"}, set(), {}, katalog)
        self.assertIn("**Znak**", linie)
        self.assertNotIn("**Znak** — scena 4700001", linie)

    def test_bez_przekladu_gwiazdka_i_licznik(self):
        statystyka: dict = {}
        with self._katalog([{"id": 200046002, "dialog": None, "storyline": ""}]) as katalog:
            linie = czytanka_czysta._poi(_Indeks(), {}, set(), statystyka, katalog)
        self.assertIn("**\\\\*Stone Tablet**", linie)
        self.assertEqual(statystyka["poi"], 1)

    def test_poi_bez_nazwy_w_wyciagu_jest_policzony(self):
        statystyka: dict = {}
        with self._katalog([{"id": 201, "dialog": None, "storyline": ""}]) as katalog:
            linie = czytanka_czysta._poi(_Indeks(), {}, set(), statystyka, katalog)
        self.assertEqual(linie, [])
        self.assertEqual(statystyka["poi_bez_nazwy"], 1)

    def test_brak_pliku(self):
        with tempfile.TemporaryDirectory() as katalog:
            self.assertEqual(czytanka_czysta._poi(_Indeks(), {}, set(), {}, katalog), [])


if __name__ == "__main__":
    unittest.main()
