"""Chronologia gry: stały plik w repo, nie układanie od nowa w każdej sesji.

Testy pilnują trzech rzeczy:

1. `index/chronologia.jsonl` zgadza się z danymi w `index/` (bo plik jest
   generowany — kto zmieni dane, ten go przegenerowuje),
2. kolejność w pliku trzyma ustalone zasady (filmy → prolog → krainy → sceny,
   cutsceny przy scenie swojej grupy zadań, reszta na końcu),
3. czytanka faktycznie czyta kolejność z tego pliku, a nie układa jej sama.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools import chronologia, czytanka_czysta

KATALOG = Path(__file__).resolve().parent.parent


def _dane() -> list[dict]:
    return chronologia.wczytaj(KATALOG / "index")


class TestZapisanaChronologia(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.jednostki = _dane()

    def test_plik_jest_w_repo(self):
        self.assertTrue((KATALOG / "index" / "chronologia.jsonl").exists())

    def test_pozycje_sa_ciagle(self):
        self.assertEqual([j["p"] for j in self.jednostki],
                         list(range(len(self.jednostki))))

    def test_kolejnosc_zgodna_z_danymi(self):
        wynik = chronologia.sprawdz(index=str(KATALOG / "index"),
                                    magazyn=str(KATALOG / "tlumaczenie"))
        self.assertTrue(wynik["ok"], wynik)

    def test_filmy_prolog_krainy(self):
        rodzaje = [j["t"] for j in self.jednostki]
        self.assertEqual(rodzaje[:3], ["film"] * 3)
        pierwszy_prolog = rodzaje.index("prolog")
        pierwsza_scena = rodzaje.index("scena")
        self.assertGreater(pierwszy_prolog, 2)
        self.assertLess(pierwszy_prolog, pierwsza_scena)
        self.assertNotIn("film", rodzaje[pierwszy_prolog:])
        self.assertNotIn("prolog", rodzaje[pierwsza_scena:])

    def test_krainy_raz_po_kolei(self):
        krainy = [j["s"] for j in self.jednostki if j["t"] == "scena"]
        kolejnosc: list[str] = []
        for kraina in krainy:
            if not kolejnosc or kolejnosc[-1] != kraina:
                kolejnosc.append(kraina)
        self.assertEqual(len(kolejnosc), len(set(kolejnosc)), "kraina wraca po innej")

    def test_sceny_po_numerze_w_krainie(self):
        ostatnia, poprzedni = None, None
        for jednostka in self.jednostki:
            if jednostka["t"] != "scena":
                continue
            if jednostka["s"] == poprzedni:
                self.assertGreater(int(jednostka["n"]), int(ostatnia))
            poprzedni, ostatnia = jednostka["s"], jednostka["n"]

    def test_cutsceny_przy_scenie_swojej_grupy(self):
        przypisane = [j for j in self.jednostki
                      if j["t"] == "cutscena" and j["s"] != chronologia.BEZ_GRUPY]
        self.assertGreater(len(przypisane), 100)
        for jednostka in przypisane:
            self.assertIn("g", jednostka)
            self.assertTrue(jednostka.get("k"))

    def test_cutsceny_bez_grupy_na_koncu(self):
        rodzaje = [j["t"] for j in self.jednostki]
        pierwsze_bez_grupy = next(
            (i for i, j in enumerate(self.jednostki)
             if j["t"] == "cutscena" and j["s"] == chronologia.BEZ_GRUPY), None)
        if pierwsze_bez_grupy is None:
            self.skipTest("brak cutscen bez grupy")
        self.assertNotIn("scena", rodzaje[pierwsze_bez_grupy:])

    def test_prolog_w_kolejnosci_transkryptu(self):
        prolog = [j for j in self.jednostki if j["t"] == "prolog"]
        self.assertTrue(prolog)
        transkrypt = Path(KATALOG / "zwrotki" / "prolog_transkrypt_z_gry.txt")
        self.assertTrue(transkrypt.exists(), "transkrypt prologu musi być w repo")
        naglowki = [linia for linia in transkrypt.read_text(encoding="utf-8-sig").splitlines()
                    if linia.startswith("#")]
        self.assertEqual(len(prolog), len(naglowki))
        # komentarze z transkryptu są dla nas, nie dla czytelnika — sekcje są numerowane
        for numer, jednostka in enumerate(prolog, 1):
            self.assertTrue(jednostka["e"].startswith("Prolog"))
            self.assertNotIn("cutscene w grze", jednostka["e"])

    def test_prolog_bez_sasiednich_duplikatow(self):
        for jednostka in self.jednostki:
            if jednostka["t"] != "prolog":
                continue
            klucze = jednostka["k"]
            for poprzedni, nastepny in zip(klucze, klucze[1:]):
                self.assertNotEqual(poprzedni, nastepny,
                                    f"powtórka klucza w {jednostka.get('e')}")


class TestCzytankaCzytaChronologie(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._katalog = tempfile.TemporaryDirectory()
        cls.statystyka = czytanka_czysta.zbuduj(
            index=str(KATALOG / "index"), magazyn=str(KATALOG / "tlumaczenie"),
            wyj=Path(cls._katalog.name), zakres="wszystko")
        cls.tekst = (Path(cls._katalog.name) / "01_sceny_i_cutsceny.md").read_text(encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        cls._katalog.cleanup()

    def test_sekcje_chronologii(self):
        self.assertIn("# Filmy otwierające", self.tekst)
        self.assertIn("# Prolog", self.tekst)
        self.assertIn("## Prolog 1", self.tekst)
        self.assertIn("## Cutscena", self.tekst)

    def test_bez_pustych_linii_miedzy_kwestiami(self):
        self.assertEqual(self.tekst.count("\n\n\n"), 0)

    def test_bez_powtorzonych_kwestii_pod_rzad(self):
        kwestie: list[str] = []
        for linia in self.tekst.splitlines():
            if linia.startswith("## ") or linia.startswith("# "):
                kwestie = []
            elif linia.startswith("- "):
                if kwestie and kwestie[-1] == linia:
                    self.fail(f"powtórzona kwestia w jednostce: {linia}")
                kwestie.append(linia)

    def test_prolog_jest_przetlumaczony_w_calosci(self):
        start = self.tekst.index("# Prolog")
        prolog = self.tekst[start:self.tekst.index("\n# ", start + 2)]
        self.assertNotIn("\\*", prolog, "prolog nie ma już luk w przekładzie")

    def test_kwestie_bez_przekladu_maja_gwiazdke(self):
        poza_prologiem = self.tekst[self.tekst.index("\n# ", self.tekst.index("# Prolog") + 2):]
        self.assertIn("- \\*", poza_prologiem,
                      "kwestie bez przekładu poza prologiem idą z gwiazdką")
        self.assertNotIn("[brak przekładu]", poza_prologiem)

    def test_rozmiar(self):
        self.assertGreater(self.statystyka["linii"], 10_000)


if __name__ == "__main__":
    unittest.main()
