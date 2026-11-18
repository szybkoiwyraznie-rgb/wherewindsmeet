"""Następstwa scen: krawędzie „koniec jednej → początek kolejnej” z `index/`.

Testy pilnują trzech rzeczy:

1. każde źródło dowodowe (tabela następstw, wybory, opcje NPC, łańcuch
   zadań, role wewnątrz zadania) daje krawędzie z właściwą oceną pewności,
2. pętle własne i cele spoza `sceny_*` wypadają (i są liczone),
3. zapisany `index/nastepstwa_scen.jsonl` zgadza się z danymi w `index/`
   (bo plik jest generowany — kto zmieni dane, ten go przegenerowuje).
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from tools import nastepstwa_scen

KATALOG = Path(__file__).resolve().parent.parent


def scena(numer, **extra):
    return {"d": numer, "e": [["k", 0, "klucz"]], "p": "p", **extra}


class ZrodlaKrawedziTests(unittest.TestCase):
    def setUp(self):
        self.sceny = {n: scena(n) for n in (100, 101, 102, 200, 201, 300)}
        self.sceny[100]["x"] = [101, 100, 999]  # cel + pętla + brak w scenach
        self.zadania = {
            1: {"pre": [], "post": [2],
                "dialogi": {"przyjecie": [100], "rozmowa": [101], "zakonczenie": [102]},
                "przerywniki": {"przyjecie": [30161], "zakonczenie": []}},
            2: {"pre": [1], "post": [],
                "dialogi": {"przyjecie": [200], "rozmowa": [], "zakonczenie": [201]},
                "przerywniki": {}},
            3: {"pre": [2], "post": [],  # tylko `pre` — para (2, 3) też wchodzi
                "dialogi": {"przyjecie": [300], "rozmowa": [], "zakonczenie": []},
                "przerywniki": {}},
        }
        self.wybory = {
            "9_1": {"pytanie": 9, "krok": 1, "po_dialogach": [200, 999],
                    "wybory": [{"nr": 1, "dialogi": [201]}, {"nr": 2, "dialogi": [999]}]},
        }
        self.opcje_npc = {
            7: {"dialogi": [300], "opcje": [{"nr": 1, "parametr": "100"},
                                           {"nr": 2, "parametr": "nie-liczba"}]},
        }
        self.krawedzie, self.statystyki = nastepstwa_scen.zbuduj_krawedzie(
            self.sceny, self.zadania, self.wybory, self.opcje_npc)

    def krawedz(self, z, do, zrodlo):
        return [k for k in self.krawedzie
                if k["z"] == z and k["do"] == do and k["zrodlo"] == zrodlo]

    def test_tabela_nastepstw_daje_krawedz_pewna(self):
        found = self.krawedz({"t": "d", "n": 100}, {"t": "d", "n": 101}, "nastepstwo")
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["pewnosc"], "pewne")
        self.assertNotIn("kontekst", found[0])

    def test_petle_i_braki_wypadaja_i_sa_liczone(self):
        self.assertEqual(self.krawedz({"t": "d", "n": 100}, {"t": "d", "n": 100}, "nastepstwo"), [])
        self.assertEqual(self.krawedz({"t": "d", "n": 100}, {"t": "d", "n": 999}, "nastepstwo"), [])
        self.assertGreaterEqual(self.statystyki["pominiete"]["petla_wlasna"], 1)
        self.assertGreaterEqual(self.statystyki["pominiete"]["cel_spoza_scen"], 1)

    def test_wybor_prowadzi_do_dialogow_wyborow(self):
        found = self.krawedz({"t": "d", "n": 200}, {"t": "d", "n": 201}, "wybor")
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["pewnosc"], "pewne")
        self.assertEqual(found[0]["kontekst"], {"pytanie": 9, "krok": 1, "wybor": 1})
        # źródło spoza scen (999) nie daje krawędzi
        self.assertFalse(any(k["z"] == {"t": "d", "n": 999} for k in self.krawedzie))

    def test_opcja_npc_prowadzi_do_dialogu_z_parametru(self):
        found = self.krawedz({"t": "d", "n": 300}, {"t": "d", "n": 100}, "opcja_npc")
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["kontekst"], {"opcja": 7, "nr": 1})

    def test_koniec_zadania_laczy_z_poczatkiem_nastepnego(self):
        # 1 (zakonczenie 102) → 2 (przyjecie 200) przez `post`; 2 → 3 tylko przez `pre`
        found = self.krawedz({"t": "d", "n": 102}, {"t": "d", "n": 200}, "zadanie")
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["pewnosc"], "z łańcucha zadań")
        self.assertEqual(found[0]["kontekst"],
                         {"zadanie": 1, "zadanie_do": 2,
                          "moment_z": "zakonczenie", "moment_do": "przyjecie"})
        found = self.krawedz({"t": "d", "n": 201}, {"t": "d", "n": 300}, "zadanie")
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["kontekst"]["zadanie"], 2)

    def test_cutscena_zadania_jest_wezlem(self):
        # cutscena przyjęcia zadania 1 poprzedza jego rozmowę (cykl życia);
        # wewnątrz roli `przyjecie` kolejności dialog/cutscena nie wymyślamy
        found = self.krawedz({"t": "c", "n": 30161}, {"t": "d", "n": 101}, "zadanie_wewnatrz")
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["pewnosc"], "z ról zadania")
        self.assertEqual(found[0]["kontekst"],
                         {"zadanie": 1, "moment_z": "przyjecie", "moment_do": "rozmowa"})
        self.assertEqual(self.krawedz({"t": "d", "n": 100}, {"t": "c", "n": 30161}, "zadanie_wewnatrz"), [])

    def test_cykl_zycia_idzie_przyjecie_rozmowa_zakonczenie(self):
        found = self.krawedz({"t": "d", "n": 100}, {"t": "d", "n": 101}, "zadanie_wewnatrz")
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["kontekst"],
                         {"zadanie": 1, "moment_z": "przyjecie", "moment_do": "rozmowa"})
        found = self.krawedz({"t": "d", "n": 101}, {"t": "d", "n": 102}, "zadanie_wewnatrz")
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["kontekst"]["moment_do"], "zakonczenie")

    def test_wynik_jest_posortowany_i_deterministyczny(self):
        again, _ = nastepstwa_scen.zbuduj_krawedzie(
            self.sceny, self.zadania, self.wybory, self.opcje_npc)
        self.assertEqual(nastepstwa_scen.serializuj(self.krawedzie),
                         nastepstwa_scen.serializuj(again))
        klucze = [(k["z"]["t"], k["z"]["n"], k["do"]["t"], k["do"]["n"], k["zrodlo"])
                  for k in self.krawedzie]
        self.assertEqual(klucze, sorted(klucze))


class ZapisanyPlikTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plik = KATALOG / "index" / "nastepstwa_scen.jsonl"
        cls.wiersze = [json.loads(linia) for linia in cls.plik.read_text(encoding="utf-8").splitlines()
                       if linia.strip()]

    def test_plik_jest_w_repo_i_ma_wszystkie_zrodla(self):
        self.assertTrue(self.plik.exists())
        zrodla = {w["zrodlo"] for w in self.wiersze}
        self.assertEqual(zrodla, {"nastepstwo", "wybor", "opcja_npc", "zadanie", "zadanie_wewnatrz"})
        for wiersz in self.wiersze:
            self.assertEqual(wiersz["pewnosc"], nastepstwa_scen.PEWNOSC[wiersz["zrodlo"]])
            self.assertNotEqual(wiersz["z"], wiersz["do"])

    def test_plik_zgadza_sie_z_danymi(self):
        wynik = nastepstwa_scen.sprawdz(index=str(KATALOG / "index"), wyj=self.plik)
        self.assertTrue(wynik["ok"], wynik)

    def test_znana_krawedz_z_tabeli_nastepstw(self):
        # 100352 → 100353: jawne następstwo w `branch_dialog_subsequent`
        found = [w for w in self.wiersze
                 if w["z"] == {"t": "d", "n": 100352} and w["do"] == {"t": "d", "n": 100353}]
        self.assertTrue(any(w["zrodlo"] == "nastepstwo" for w in found), found)


if __name__ == "__main__":
    unittest.main()
