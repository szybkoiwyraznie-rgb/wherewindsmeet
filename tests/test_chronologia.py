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

import re

from tools import chronologia, czytanka_czysta, pinyin_slownik

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

    def test_prolog_krainy_piesni(self):
        rodzaje = [j["t"] for j in self.jednostki]
        # pieśni na końcu — w grze nie ma ich na początku
        self.assertEqual(rodzaje[-3:], ["film"] * 3)
        pierwszy_prolog = rodzaje.index("prolog")
        pierwsza_scena = rodzaje.index("scena")
        self.assertLess(pierwszy_prolog, pierwsza_scena)
        self.assertNotIn("film", rodzaje[:pierwszy_prolog])
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
                      if j["t"] == "cutscena" and j["s"] not in (chronologia.BEZ_GRUPY, "Prolog")]
        self.assertGreater(len(przypisane), 100)
        for jednostka in przypisane:
            self.assertIn("g", jednostka)
            self.assertTrue(jednostka.get("k"))

    def test_cutscena_w_prologu_ma_streszczenie(self):
        """Streszczenie cutsceny z transkryptu stoi w prologu, między sekcjami."""
        prolog = [j for j in self.jednostki if j["s"] == "Prolog"]
        cutsceny = [j for j in prolog if j["t"] == "cutscena"]
        self.assertTrue(cutsceny, "w prologu jest cutscena ze streszczeniem")
        for jednostka in cutsceny:
            self.assertTrue(jednostka.get("k"))
            self.assertNotIn("g", jednostka)
        pozycje_prologu = [i for i, j in enumerate(self.jednostki) if j["s"] == "Prolog"]
        for jednostka in cutsceny:
            pozycja = self.jednostki.index(jednostka)
            self.assertGreater(pozycja, min(pozycje_prologu))
            self.assertLess(pozycja, max(pozycje_prologu))

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


class TestNapisyPrzerywnikow(unittest.TestCase):
    """Pula napisów przerywników (`text_msg`) ma trafić do 01, nie do 03.

    W danych gry napis nie ma numeru cutsceny — jest tylko wiersz i nazwa nagrania.
    Dlatego chronologia trzyma je w blokach scen: część podpięta pod cutscenę
    (`kn`), reszta w sekcji „Napisy przerywników”, w kolejności z pliku gry.
    """

    @classmethod
    def setUpClass(cls):
        from tools import indeks
        cls.jednostki = _dane()
        cls.pula = sorted({w["k"] for w in
                           indeks.wczytaj(str(KATALOG / "index"), teksty=True, sceny=False)
                           .cutsceny_kontekst.get("napis", []) if w.get("k")})

    def _klucze(self) -> list[str]:
        """Klucze napisów przerywników (bez prologu — tam transkrypt powtarza kwestie)."""
        klucze: list[str] = []
        for jednostka in self.jednostki:
            if jednostka["t"] == "napisy":
                klucze.extend(jednostka.get("k") or [])
            elif jednostka["t"] == "cutscena":
                klucze.extend(jednostka.get("kn") or [])
        return klucze

    def test_pula_napisow_jest_w_calosci_w_chronologii(self):
        self.assertGreater(len(self.pula), 2000)
        klucze = set(self._klucze())
        brakujace = [k for k in self.pula if k not in klucze]
        # kwestie, które transkrypt prologu już pokazał, nie powtarzają się w blokach
        w_prologu = {k for j in self.jednostki if j["t"] == "prolog" for k in j.get("k") or []}
        brakujace = [k for k in brakujace if k not in w_prologu]
        self.assertFalse(brakujace[:5], f"{len(brakujace)} napisów poza chronologią")

    def test_zaden_napis_nie_stoi_dwa_razy(self):
        klucze = self._klucze()
        powtorzone = {k for k in klucze if klucze.count(k) > 1}
        self.assertFalse(sorted(powtorzone)[:5], f"powtórzone napisy: {len(powtorzone)}")

    def test_przebudzenie_z_ruby_jest_przy_cutscenie(self):
        """„Wodzu, obudź się!” należy do cutsceny 30161, nie do alfabetycznej reszty."""
        klucz = "5eca4f42781900b5"
        trafienia = [j for j in self.jednostki if klucz in (j.get("kn") or [])]
        self.assertEqual(len(trafienia), 1)
        self.assertEqual(trafienia[0]["t"], "cutscena")
        self.assertEqual(trafienia[0]["n"], 30161)

    def test_rozdzial_pierwszy_stoi_w_krainie(self):
        """Cutsceny grupy 1 (rozdział pierwszy) mają stać w krainie, nie w „scenach bez mapy”."""
        grupa1 = [j for j in self.jednostki if j["t"] == "cutscena" and j.get("g") == 1]
        self.assertGreater(len(grupa1), 10)
        bez_mapy = [j["n"] for j in grupa1 if j["s"] == chronologia.BEZ_MAPY]
        self.assertLessEqual(len(bez_mapy), 5, f"cutsceny poza krainą: {bez_mapy[:5]}")
        ruby = next(j for j in grupa1 if j["n"] == 30161)
        self.assertNotEqual(ruby["s"], chronologia.BEZ_MAPY)
        self.assertTrue(ruby.get("kn"), "scena Ruby ma swoje napisy")

    def test_napisy_stoja_przed_piesniami(self):
        rodzaje = [j["t"] for j in self.jednostki]
        self.assertIn("napisy", rodzaje)
        self.assertLess(rodzaje.index("napisy"), len(rodzaje) - 3)
        self.assertEqual(rodzaje[-3:], ["film"] * 3)

    def test_bloki_maja_tytul(self):
        for jednostka in self.jednostki:
            if jednostka["t"] == "napisy":
                self.assertGreater(len(jednostka["e"]), 5, "blok bez tytułu")
                self.assertTrue(jednostka.get("k"))


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

    def test_piesni_na_koncu(self):
        self.assertGreater(self.tekst.index("# Pieśni"),
                           self.tekst.index("# Cutsceny bez grupy zadań"))

    def test_kwestie_bez_punktora(self):
        for linia in self.tekst.splitlines():
            if linia.startswith("- "):
                self.fail(f"kwestia z punktorem: {linia[:60]}")

    def test_napisy_przerywnikow_sa_w_01(self):
        self.assertIn("Wodzu, obudź się!", self.tekst)
        reszta = (Path(self._katalog.name) / "03_reszta.md").read_text(encoding="utf-8")
        self.assertNotIn("Wodzu, obudź się!", reszta)

    def test_mowca_jest_pogrubiony(self):
        self.assertIn("**Youxia:**", self.tekst)
        self.assertNotIn("- **", self.tekst)

    def test_sekcje_chronologii(self):
        self.assertIn("# Pieśni", self.tekst)
        self.assertIn("# Prolog", self.tekst)
        self.assertIn("## Prolog 1", self.tekst)
        self.assertIn("## Cutscena", self.tekst)

    def test_bez_pustych_linii_miedzy_kwestiami(self):
        self.assertEqual(self.tekst.count("\n\n\n"), 0)

    def test_bez_powtorzonych_kwestii_pod_rzad(self):
        kwestie: list[str] = []
        kwestie: set[str] = set()
        for linia in self.tekst.splitlines():
            if linia.startswith("## ") or linia.startswith("# "):
                kwestie = set()
            elif linia.strip() and not linia.startswith("#"):
                if linia in kwestie:
                    self.fail(f"powtórzona kwestia w jednostce: {linia[:60]}")
                kwestie.add(linia)

    def test_prolog_jest_przetlumaczony_w_calosci(self):
        start = self.tekst.index("# Prolog")
        prolog = self.tekst[start:self.tekst.index("\n# ", start + 2)]
        self.assertNotIn("\\*", prolog, "prolog nie ma już luk w przekładzie")

    def test_kwestie_bez_przekladu_maja_gwiazdke(self):
        poza_prologiem = self.tekst[self.tekst.index("\n# ", self.tekst.index("# Prolog") + 2):]
        self.assertIn("\\*", poza_prologiem,
                      "kwestie bez przekładu poza prologiem idą z gwiazdką")
        self.assertNotIn("[brak przekładu]", poza_prologiem)

    def test_kontekst_bez_polskiego_ma_gwiazdke(self):
        tekst = (Path(self._katalog.name) / "02_kontekst_scen_i_cutscen.md").read_text(encoding="utf-8")
        self.assertNotIn("*(EN)*", tekst)
        if "# Prolog" in tekst:
            self.assertIn("\\*", tekst, "karta bez polskiego opisu idzie z gwiazdką")

    def test_mowca_po_lacince(self):
        """Etykiety mówców nie mogą zostać po chińsku ani jako same numery."""
        for linia in self.tekst.splitlines():
            trafienie = re.match(r"^\*\*([^*]+):\*\* ", linia)
            if not trafienie:
                continue
            mowca = trafienie[1]
            self.assertIsNone(re.search(r"[\u3400-\u9fff]", mowca),
                              f"mówca po chińsku: {mowca}")
            self.assertFalse(mowca.isdigit(), f"mówca to samo id: {mowca}")

    def test_kontekst_bez_golych_nazw(self):
        """W 02 nie ma kart z samą nazwą — hasło bez opisu zostaje w 03."""
        tekst = (Path(self._katalog.name) / "02_kontekst_scen_i_cutscen.md").read_text(encoding="utf-8")
        for trafienie in re.finditer(r"^\*\*([^*]+)\*\*$", tekst, re.M):
            self.fail(f"hasło bez opisu w kontekście: {trafienie[1]}")

    def test_kontekst_bez_opowiesci_z_encyklopedii(self):
        """Rozdziały fabularne encyklopedii to nie opisy postaci — nie wchodzą do 02."""
        tekst = (Path(self._katalog.name) / "02_kontekst_scen_i_cutscen.md").read_text(encoding="utf-8")
        self.assertNotIn("At Blissful Retreat, Jiang Wulang drank alone", tekst)
        self.assertNotIn("opened his eyes to pitch darkness", tekst)

    def test_streszczenie_cutsceny_stoi_w_prologu(self):
        """Streszczenie cutsceny z transkryptu jest w prologu, między Prolog 3 i Prolog 4."""
        self.assertLess(self.tekst.index("## Prolog 3"), self.tekst.index("## Cutscena 30150"))
        self.assertLess(self.tekst.index("## Cutscena 30150"), self.tekst.index("## Prolog 4"))
        self.assertEqual(self.tekst.count("Robak przelatuje"), 1)

    def test_rozmiar(self):
        self.assertGreater(self.statystyka["linii"], 10_000)


if __name__ == "__main__":
    unittest.main()


class TestPinyinEtykiet(unittest.TestCase):
    """Chińskie etykiety mówców idą w łacinkę z tabeli w repo (bez bibliotek)."""

    def test_znaki_sa_w_tabeli(self):
        mapa = pinyin_slownik.wczytaj(KATALOG / "index")
        self.assertGreater(len(mapa), 1_000)
        self.assertEqual(mapa.get("大"), "da")

    def test_transliteracja_imienia(self):
        mapa = pinyin_slownik.wczytaj(KATALOG / "index")
        self.assertEqual(pinyin_slownik.romanizuj("大祭师", mapa), "Da Ji Shi")

    def test_transliteracja_z_cyfra(self):
        mapa = pinyin_slownik.wczytaj(KATALOG / "index")
        self.assertEqual(pinyin_slownik.romanizuj("卫兵1", mapa), "Wei Bing 1")

    def test_nawiasy_pelnej_szerokosci(self):
        mapa = pinyin_slownik.wczytaj(KATALOG / "index")
        self.assertEqual(pinyin_slownik.romanizuj("兰澳（少女）", mapa), "Lan Ao (Shao Nv)")

    def test_lacina_zostaje_bez_zmian(self):
        self.assertEqual(pinyin_slownik.romanizuj("Chen Zixi"), "Chen Zixi")
