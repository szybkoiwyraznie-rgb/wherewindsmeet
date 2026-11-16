"""Kolejność kwestii w cutscenach czytanki.

W plikach gry ten sam przerywnik bywa zapisany dwa razy (dwa zestawy napisów),
a `kn` w chronologii miesza napisy przypisane wprost z tabeli gry i bloki puli —
dlatego kwestie trafiały do czytanki w kolejności losowej. Porządek bierzemy
z numeru wiersza puli `text_msg`; warianty rozdzielamy nagłówkiem, a streszczenie
sceny dostaje własny nagłówek.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from tools import czytanka_czysta as cz

INDEX = Path(__file__).resolve().parent.parent / "index"
MAGAZYN = Path(__file__).resolve().parent.parent / "tlumaczenie"


def _wiersze(**pary: int) -> dict[str, int]:
    return dict(pary)


class TestKolejnoscCutscen(unittest.TestCase):
    def test_porzadek_wg_wiersza_puli(self):
        # `kn` w kolejności z chronologii: najpierw kwestie przypisane wprost z tabeli
        wiersz = {"t": "cutscena", "n": 1, "kn": ["k-late", "k-early", "k-mid"], "k": ["k-sum"]}
        wiersze = _wiersze(**{"k-early": 590153, "k-mid": 590154, "k-late": 590160})
        pl = {"k-late": "Trzecia.", "k-early": "Pierwsza.", "k-mid": "Druga.", "k-sum": "Streszczenie."}

        klucze, podtytuly, powtorzone = cz._napisy_cutsceny(wiersz, wiersze, pl)

        self.assertEqual(klucze, ["k-sum", "k-early", "k-mid", "k-late"])
        self.assertEqual(podtytuly, {0: "Streszczenie sceny"})
        self.assertEqual(powtorzone, [])

    def test_streszczenie_stoi_na_poczatku_sceny(self):
        wiersz = {"t": "cutscena", "n": 1, "kn": ["a"], "k": ["sum1", "sum2"]}
        klucze, podtytuly, _ = cz._napisy_cutsceny(
            wiersz, _wiersze(a=590100), {"a": "Kwestia.", "sum1": "Raz.", "sum2": "Dwa."})
        self.assertEqual(klucze, ["sum1", "sum2", "a"])
        self.assertEqual(podtytuly, {0: "Streszczenie sceny"})

    def test_dwa_warianty_napisow_rozdzielone_i_bez_powtorzen(self):
        # dwa bloki tej samej cutsceny: 590153+ oraz 591125+
        wiersz = {"t": "cutscena", "n": 30161,
                  "kn": ["b", "a", "d", "c"], "k": []}
        wiersze = _wiersze(**{"a": 590153, "b": 590154, "c": 591125, "d": 591126})
        pl = {"a": "Wstawaj!", "b": "Wschód słońca.", "c": "Wstawaj!", "d": "Inna kwestia."}

        klucze, podtytuly, powtorzone = cz._napisy_cutsceny(wiersz, wiersze, pl)

        # grana jest wersja nowsza (wyższe numery wierszy puli), starsza schodzi do wariantu
        self.assertEqual(klucze, ["c", "d", "b"])      # „a” to to samo zdanie co „c”
        self.assertEqual(powtorzone, ["a"])
        self.assertEqual(podtytuly, {2: "Inny wariant napisów tej cutsceny (wiersze 590153–590154)"})

    def test_klucz_bez_wiersza_nie_psuje_porzadku(self):
        wiersz = {"t": "cutscena", "n": 1, "kn": ["bez", "z1"], "k": []}
        klucze, _, _ = cz._napisy_cutsceny(wiersz, _wiersze(z1=590200), {"bez": "Bez.", "z1": "Z."})
        self.assertEqual(klucze, ["z1", "bez"])

    def test_wiersze_napisow_z_osi_kolejnosci(self):
        class Ix:
            cutsceny_kontekst = {"napis": [{"k": "k1", "wiersz": 590153}]}

        # wiersze „napis_grey” nie wchodzą: to ten sam wiersz puli z tekstem bez przekładu
        porzadek = {"k1": [{"z": "napis", "i": 590153}], "k2": [{"z": "napis_grey", "i": 591125}]}
        self.assertEqual(cz._wiersze_napisow(Ix(), porzadek), {"k1": 590153})


class TestBlokGlowny(unittest.TestCase):
    """Grana jest nowsza wersja napisów cutsceny, nie pierwsza z `kn`."""

    def test_nowszy_blok_na_poczatku_starszy_w_wariancie(self):
        wiersz = {"t": "cutscena", "n": 1, "kn": ["stara1", "stara2", "nowa1", "nowa2"], "k": []}
        wiersze = _wiersze(stara1=590153, stara2=590154, nowa1=591148, nowa2=591149)
        pl = {"stara1": "Stara pierwsza.", "stara2": "Stara druga.",
              "nowa1": "Nowa pierwsza.", "nowa2": "Nowa druga."}

        klucze, podtytuly, _ = cz._napisy_cutsceny(wiersz, wiersze, pl)

        self.assertEqual(klucze, ["nowa1", "nowa2", "stara1", "stara2"])
        self.assertEqual(list(podtytuly), [2])
        self.assertTrue(podtytuly[2].startswith("Inny wariant napisów"))

    def test_trzy_bloki_w_kolejnosci_od_najnowszego(self):
        wiersz = {"t": "cutscena", "n": 1, "kn": ["a", "b", "c"], "k": []}
        wiersze = _wiersze(a=590100, b=591100, c=591900)
        pl = {"a": "Najstarsza.", "b": "Średnia.", "c": "Najnowsza."}

        klucze, _, _ = cz._napisy_cutsceny(wiersz, wiersze, pl)

        self.assertEqual(klucze, ["c", "b", "a"])


class TestNaglowkiWPliku(unittest.TestCase):
    def _statystyka(self):
        return {"jednostek": 0, "linii": 0, "pominiete": 0, "bez_przekladu": 0}

    def test_naglowki_wychodza_przed_wlasciwa_linia(self):
        jednostka = cz.Jednostka(
            "cutscena", "Cutscena 1", "# Kraina",
            [("", "a"), ("", "b"), ("", "c"), ("", "sum")],
            podtytuly={2: "Inny wariant napisów tej cutsceny (wiersze 591125–591169)",
                       3: "Streszczenie sceny"})
        pl = {"a": "Pierwsza.", "b": "Druga.", "c": "Trzecia.", "sum": "Streszczenie."}
        out, uzyte, _ = cz._plik_scen([jednostka], pl, "przetlumaczone", self._statystyka())
        self.assertEqual(out[3:], [
            "Pierwsza.",
            "Druga.",
            "### Inny wariant napisów tej cutsceny (wiersze 591125–591169)",
            "Trzecia.",
            "### Streszczenie sceny",
            "Streszczenie.",
            "",
        ])
        self.assertEqual(uzyte, {"a", "b", "c", "sum"})

    def test_ukryte_powtorzenia_nie_trafiaja_do_reszty(self):
        jednostka = cz.Jednostka("cutscena", "Cutscena 1", "# Kraina",
                                 [("", "a")], zasloniete=("duplikat",))
        out, uzyte, _ = cz._plik_scen([jednostka], {"a": "Kwestia."},
                                      "przetlumaczone", self._statystyka())
        self.assertIn("Kwestia.", out)
        self.assertIn("duplikat", uzyte)


@unittest.skipUnless((INDEX / "chronologia.jsonl").is_file() and MAGAZYN.is_dir(),
                     "brak wyciągu gry w index/")
class TestCutscena30161(unittest.TestCase):
    """Regresja z prawdziwego wyciągu: cutscena Ruby (30161)."""

    @classmethod
    def setUpClass(cls):
        cls.wiersz = None
        with (INDEX / "chronologia.jsonl").open(encoding="utf-8") as f:
            for linia in f:
                wpis = json.loads(linia)
                if wpis.get("t") == "cutscena" and wpis.get("n") == 30161:
                    cls.wiersz = wpis
                    break
        if cls.wiersz is None:
            raise unittest.SkipTest("brak cutsceny 30161 w chronologii")
        klucze = set(cls.wiersz.get("kn") or []) | set(cls.wiersz.get("k") or [])
        cls.wiersze = {}
        with (INDEX / "cutsceny_kontekst.jsonl").open(encoding="utf-8") as f:
            for linia in f:
                wpis = json.loads(linia)
                if wpis.get("typ") == "napis" and wpis.get("k") in klucze:
                    cls.wiersze[wpis["k"]] = wpis["wiersz"]
        cls.audio = {}
        with (INDEX / "cutsceny_kontekst.jsonl").open(encoding="utf-8") as f:
            for linia in f:
                wpis = json.loads(linia)
                if wpis.get("typ") == "napis" and wpis.get("audio"):
                    cls.audio[wpis["wiersz"]] = wpis["audio"]
        cls.pl = {}
        for plik in sorted(MAGAZYN.glob("pl_*.jsonl")):
            with plik.open(encoding="utf-8") as f:
                for linia in f:
                    wpis = json.loads(linia)
                    if wpis.get("k") in klucze:
                        cls.pl[wpis["k"]] = wpis["pl"]

    def test_scena_zaczyna_sie_od_zbudzenia_a_nie_od_bebna_ani_wiersza(self):
        klucze, _, _ = cz._napisy_cutsceny(self.wiersz, self.wiersze, self.pl, self.audio)
        tresc = [self.pl[k].strip() for k in klucze[1:] if k in self.pl]   # [0] to streszczenie
        self.assertEqual(tresc[:3], ["Szefie! Szefie!", "Wodzu, obudź się!",
                                     "Miałaś iść ze mną do Kaplicy Generała!"])
        self.assertEqual(tresc[3], "Jak można tak zasnąć?")
        self.assertNotIn("Ten bęben… czemu bije coraz głośniej?", tresc[:4])

    def test_streszczenie_jest_pierwsze_i_pod_naglowkiem(self):
        klucze, podtytuly, _ = cz._napisy_cutsceny(self.wiersz, self.wiersze, self.pl, self.audio)
        self.assertEqual(podtytuly.get(0), "Streszczenie sceny")
        self.assertNotIn(len(klucze) - 1, podtytuly)

    def test_zaden_tekst_nie_powtarza_sie_w_scenie(self):
        klucze, _, _ = cz._napisy_cutsceny(self.wiersz, self.wiersze, self.pl, self.audio)
        sygnatury = [cz._bez_interpunkcji(self.pl[k]) for k in klucze if k in self.pl]
        self.assertEqual(len(sygnatury), len(set(sygnatury)))


if __name__ == "__main__":
    unittest.main()
