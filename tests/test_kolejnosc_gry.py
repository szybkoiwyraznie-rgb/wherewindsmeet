from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools import kolejnosc_gry


class TestSkrot(unittest.TestCase):
    def test_zgodny_ze_skrotem_indeksu(self):
        # Klucz indeksu to pierwsze 16 znaków SHA-256 tekstu źródłowego.
        tekst = "我正是受言先生所托，来杀你。"
        oczekiwany = hashlib.sha256(tekst.encode("utf-8")).hexdigest()[:16]
        self.assertEqual(kolejnosc_gry.skrot(tekst), oczekiwany)
        self.assertEqual(len(kolejnosc_gry.skrot(tekst)), 16)

    def test_inny_tekst_inny_skrot(self):
        self.assertNotEqual(kolejnosc_gry.skrot("是你"), kolejnosc_gry.skrot("是啊"))


class TestNormalizacja(unittest.TestCase):
    def test_sklada_biale_znaki_i_cudzyslowy(self):
        self.assertEqual(kolejnosc_gry._norm("  To\u00a0  ty.\n"), "to ty.")
        self.assertEqual(kolejnosc_gry._norm("Don’t"), kolejnosc_gry._norm("Don't"))


class TestZapis(unittest.TestCase):
    def test_sharduje_po_pierwszym_znaku_klucza(self):
        wiersze = [
            {"k": "abc", "z": "napis", "i": 590336, "d": None, "t": None, "o": None},
            {"k": "aef", "z": "napis", "i": 590337, "d": None, "t": None, "o": None},
            {"k": "c01", "z": "dialog", "i": None, "d": 10167, "t": 0.0, "o": 0},
        ]
        with tempfile.TemporaryDirectory() as katalog:
            shardy = kolejnosc_gry.zapisz(wiersze, katalog)
            self.assertEqual(shardy, {"a": 2, "c": 1})
            self.assertTrue((Path(katalog) / "kolejnosc_a.jsonl").exists())
            self.assertEqual(sorted(kolejnosc_gry.wczytaj(katalog), key=lambda w: w["k"]), sorted(wiersze, key=lambda w: w["k"]))


class TestZbieranieKluczy(unittest.TestCase):
    def test_zbiera_klucze_z_drzewa_timeline(self):
        drzewo = {
            "Type": "TimelinePObject",
            "__tracks__": [
                {
                    "Type": "EntityTrackGroup",
                    "__children__": [
                        {
                            "Type": "EntityTextTrack",
                            "__keyframes__": [
                                {"time": 0.0, "order": 0, "source_id": 1016801,
                                 "text": 1, "formatted_text": "追上去，不能让他带走镇冠珏！"},
                                {"time": 0.0, "order": 1, "source_id": 1016802,
                                 "text": 2, "formatted_text": None},
                            ],
                        }
                    ],
                }
            ],
        }
        zebrane: list[dict] = []
        kolejnosc_gry._klucze(drzewo, zebrane)
        # Klucz bez `formatted_text` nie wnosi tekstu — liczy się tylko ten z tekstem.
        self.assertEqual(len(zebrane), 2)
        self.assertEqual(zebrane[0]["source_id"], 1016801)
        self.assertEqual(zebrane[0]["formatted_text"], "追上去，不能让他带走镇冠珏！")


class TestWyborWariantu(unittest.TestCase):
    def test_wybiera_najwczesniejszy_wariant(self):
        from tools import prolog_z_klucza as pzk

        po_pl = {"idz": ["aaa", "bbb"]}
        porzadek = {
            "aaa": [{"k": "aaa", "z": "napis", "i": 590352, "d": None, "t": None}],
            "bbb": [{"k": "bbb", "z": "napis", "i": 590337, "d": None, "t": None}],
        }
        self.assertEqual(pzk._dopasuj("Idz", po_pl, {}, porzadek), "bbb")

    def test_tekst_poza_danymi_daje_none(self):
        from tools import prolog_z_klucza as pzk

        self.assertIsNone(pzk._dopasuj("zupełnie inny tekst", {}, {}, {}))


if __name__ == "__main__":
    unittest.main()
