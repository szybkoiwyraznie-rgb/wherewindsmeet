from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from tools import kontekst_paczki as kpak


class KontekstPaczkiTests(unittest.TestCase):
    def test_puste_katalogi_dają_puste_mapy(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.assertEqual(kpak.kolejnosc_cine(root), {})
            self.assertEqual(kpak.listy_przy_scenach(root), {})
            self.assertEqual(kpak.poi_przy_scenach(root), {})
            self.assertEqual(kpak.bowu_story(root), {})

    def test_cine_listy_poi_bowu_z_plików(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "mpk").mkdir()
            (root / "cutsceny_kolejnosc_kwestii.jsonl").write_text(
                json.dumps({"no": 30161, "bloki": [[{"k": "aa", "w": 591170, "t": 0.1}]]}) + "\n",
                encoding="utf-8",
            )
            (root / "mpk" / "listy_w_grafie.jsonl").write_text(
                json.dumps({"no": 5, "po": 4700002, "przed": 4700003}) + "\n"
                + json.dumps({"no": 5}) + "\n"
                + json.dumps({"no": 13, "po": 1700262}) + "\n",
                encoding="utf-8",
            )
            (root / "poi.jsonl").write_text(
                json.dumps({"id": 200046001, "nazwa": "Dragon Pattern Mark"}) + "\n",
                encoding="utf-8",
            )
            (root / "mpk" / "poi_storyline_sceny.jsonl").write_text(
                json.dumps({"poi": 200046001, "status": "sceny", "sceny": [4700001]}) + "\n"
                + json.dumps({"poi": 102, "status": "nierozwiazany"}) + "\n",
                encoding="utf-8",
            )
            (root / "bowu_story.jsonl").write_text(
                json.dumps({"bowu": 832009, "story": [901]}) + "\n",
                encoding="utf-8",
            )
            cine = kpak.kolejnosc_cine(root)
            self.assertEqual(cine[30161][0][0]["w"], 591170)
            przy = kpak.listy_przy_scenach(root)
            self.assertEqual(przy[4700002], [5])
            self.assertEqual(przy[1700262], [13])
            self.assertEqual(kpak.poi_przy_scenach(root)[4700001], "Dragon Pattern Mark")
            self.assertEqual(kpak.bowu_story(root)["832009"], ["901"])

    def test_listy_envelop_grupuje_pola_wiersza(self):
        ix = SimpleNamespace(
            zrodla=[["tasks_envelop_data", "to", 1], ["tasks_envelop_data", "text", 1], ["inne", "x", 1]],
            teksty={
                "kto": SimpleNamespace(w=(0, "5")),
                "tresc": SimpleNamespace(w=(1, "5")),
                "obcy": SimpleNamespace(w=(2, "5")),
            },
        )
        listy = kpak.listy_envelop(ix)
        self.assertEqual(listy["5"]["to"], "kto")
        self.assertEqual(listy["5"]["text"], "tresc")
        self.assertEqual(listy["5"]["klucze"], ["kto", "tresc"])
        self.assertNotIn("obcy", listy["5"]["klucze"])
