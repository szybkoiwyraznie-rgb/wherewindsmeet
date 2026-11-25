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

    def test_pogrupuj_rekordy_trzyma_nazwe_i_opis_razem(self):
        pozycje = [
            {"klucz": "n1", "tabela": "tasks", "kolumna": "task_name", "wiersz": "1", "origin": 0, "name_key": "n1"},
            {"klucz": "t1", "tabela": "tasks", "kolumna": "task_target_str", "wiersz": "1", "origin": 1, "name_key": "n1"},
            {"klucz": "n2", "tabela": "tasks", "kolumna": "task_name", "wiersz": "2", "origin": 0, "name_key": "n2"},
        ]
        out = kpak.pogrupuj_rekordy(pozycje, lambda _t: "01_zadania")
        recs = out["01_zadania"]
        po_nazwie = {r.nazwa_klucz: r for r in recs}
        self.assertEqual([p.klucz for p in po_nazwie["n1"].pola], ["n1", "t1"])
        self.assertEqual([p.klucz for p in po_nazwie["n2"].pola], ["n2"])

    def test_homonimy_roznych_wierszy_osobno(self):
        pozycje = [
            {"klucz": "n", "tabela": "tasks", "kolumna": "task_name", "wiersz": "10", "origin": 0, "name_key": "n"},
            {"klucz": "a", "tabela": "tasks", "kolumna": "task_target_str", "wiersz": "10", "origin": 1, "name_key": "n"},
            {"klucz": "n", "tabela": "tasks", "kolumna": "task_name", "wiersz": "20", "origin": 0, "name_key": "n"},
            {"klucz": "b", "tabela": "tasks", "kolumna": "task_target_str", "wiersz": "20", "origin": 1, "name_key": "n"},
        ]
        recs = kpak.pogrupuj_rekordy(pozycje, lambda _t: "01_zadania")["01_zadania"]
        self.assertEqual(len(recs), 2)
        wiersze = {r.pola[0].wiersz: [p.klucz for p in r.pola] for r in recs}
        self.assertEqual(wiersze["10"], ["n", "a"])
        self.assertEqual(wiersze["20"], ["n", "b"])

    def test_nazwa_bez_w2_skleja_sie_z_opisem(self):
        pozycje = [
            {"klucz": "n1", "tabela": "stuff_items", "kolumna": "name", "wiersz": "1", "origin": 0, "name_key": None},
            {"klucz": "d1", "tabela": "stuff_items", "kolumna": "describe_str", "wiersz": "1", "origin": 1, "name_key": "n1"},
        ]
        recs = kpak.pogrupuj_rekordy(pozycje, lambda _t: "03_przedmioty")["03_przedmioty"]
        self.assertEqual(len(recs), 1)
        self.assertEqual([p.klucz for p in recs[0].pola], ["n1", "d1"])
        self.assertEqual(recs[0].nazwa_klucz, "n1")

    def test_wspolna_nazwa_w_dwoch_tabelach_nie_scala_bytow(self):
        pozycje = [
            {"klucz": "n", "tabela": "stuff_items", "kolumna": "name", "wiersz": "1", "origin": 0, "name_key": "n"},
            {"klucz": "d", "tabela": "stuff_items", "kolumna": "describe_str", "wiersz": "1", "origin": 1, "name_key": "n"},
            {"klucz": "n", "tabela": "buff", "kolumna": "buff_name", "wiersz": "1", "origin": 0, "name_key": "n"},
            {"klucz": "e", "tabela": "buff", "kolumna": "buff_detail", "wiersz": "1", "origin": 3, "name_key": "n"},
        ]
        out = kpak.pogrupuj_rekordy(pozycje, lambda t: "03" if t.startswith("stuff") else "04")
        self.assertEqual({p.klucz for p in out["03"][0].pola}, {"n", "d"})
        self.assertEqual({p.klucz for p in out["04"][0].pola}, {"n", "e"})

    def test_uszereguj_zadania_lancuchem_potem_reszta(self):
        rec_a = kpak.Rekord(grupa=("r", "tasks", "1"), kategoria="01", nazwa_klucz="a", tabela_nazwy="tasks")
        rec_b = kpak.Rekord(grupa=("r", "tasks", "2"), kategoria="01", nazwa_klucz="b", tabela_nazwy="tasks")
        rec_c = kpak.Rekord(grupa=("r", "tasks", "3"), kategoria="01", nazwa_klucz="c", tabela_nazwy="tasks")
        rec_a.pola = [kpak.PoleRekordu("a", "tasks", "task_name", "1", 0)]
        rec_b.pola = [kpak.PoleRekordu("b", "tasks", "task_name", "2", 0)]
        rec_c.pola = [kpak.PoleRekordu("c", "tasks", "task_name", "3", 0)]
        out = kpak.uszereguj_rekordy_zadan([rec_c, rec_a, rec_b], [("Rozdział 1", ["a", "b"])])
        self.assertEqual([r.nazwa_klucz for _, r in out], ["a", "b", "c"])
        self.assertEqual(out[0][0], "Rozdział 1")
        self.assertIsNone(out[1][0])
        self.assertIsNone(out[2][0])
