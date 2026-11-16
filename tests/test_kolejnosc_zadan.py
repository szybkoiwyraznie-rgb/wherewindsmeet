from __future__ import annotations

import json
import unittest
from pathlib import Path

from tools import indeks, kolejnosc_zadan, uklad_scen

ROOT = Path(__file__).resolve().parent.parent


def _magazyn(katalog: Path) -> dict[str, str]:
    pl: dict[str, str] = {}
    for sciezka in sorted(katalog.glob("pl_*.jsonl")):
        for linia in sciezka.open(encoding="utf-8"):
            rekord = json.loads(linia)
            klucz = rekord.get("k") or rekord.get("klucz")
            if klucz and rekord.get("pl"):
                pl[klucz] = rekord["pl"]
    return pl


class KolejnoscZadanTests(unittest.TestCase):
    """Porządek sekcji „Zadania i wątki”: łańcuch gry, nie alfabet."""

    @classmethod
    def setUpClass(cls):
        cls.indeks = indeks.wczytaj(ROOT / "index", teksty=True, sceny=True)
        cls.pl = _magazyn(ROOT / "tlumaczenie")
        cls.krainy = json.loads((ROOT / "index" / "prowincje.json").read_text(encoding="utf-8"))
        cls.bloki = kolejnosc_zadan.plan(cls.indeks, cls.pl, cls.krainy)

    def test_watek_glowny_stoi_pierwszy(self):
        self.assertTrue(self.bloki, "brak bloków zadań")
        self.assertEqual(self.bloki[0].tytul, "Wątek główny")

    def test_zadne_zadanie_nie_powtarza_sie_w_dwoch_blokach(self):
        widziane: set[str] = set()
        for blok in self.bloki:
            powtorki = widziane & set(blok.klucze)
            self.assertEqual(powtorki, set(), f"blok {blok.tytul}: {sorted(powtorki)[:3]}")
            widziane |= set(blok.klucze)

    def test_kolejnosc_watku_glownego_to_kolejnosc_sekcji_gry(self):
        sekcje = uklad_scen.uloz(self.indeks).sekcje
        oczekiwane: list[str] = []
        for sekcja in sekcje:
            if sekcja.typ != uklad_scen.TYP_WATKU_GLOWNEGO:
                continue
            for numer in sekcja.zadania:
                klucz = self.indeks.zadania[numer].get("nazwa")
                if klucz and klucz not in oczekiwane:
                    oczekiwane.append(klucz)
        self.assertEqual(self.bloki[0].klucze, oczekiwane)

    def test_lancuchy_przed_pojedynczymi(self):
        rodzaje = [("pojedyncze" if blok.tytul.startswith("Zadania pojedyncze") else blok.rodzaj)
                   for blok in self.bloki]
        self.assertIn("watek", rodzaje)
        pierwsze_pojedyncze = rodzaje.index("pojedyncze") if "pojedyncze" in rodzaje else len(rodzaje)
        self.assertEqual(rodzaje[:pierwsze_pojedyncze].count("pojedyncze"), 0)

    def test_kazde_zadanie_z_nazwa_jest_w_ktoryms_bloku(self):
        klucze = {blok_klucz for blok in self.bloki for blok_klucz in blok.klucze}
        bez_bloku = [numer for numer, zadanie in self.indeks.zadania.items()
                     if zadanie.get("nazwa") and zadanie["nazwa"] not in klucze]
        self.assertEqual(bez_bloku[:5], [], f"{len(bez_bloku)} zadań bez bloku")


class SekcjaZadanTests(unittest.TestCase):
    """Sekcja w pliku 03 nie gubi haseł, których nie ma w planie."""

    def test_hasla_spoza_planu_idą_na_koniec(self):
        from tools import czytanka_czysta

        opisy = {"Zadanie z planu": ["opis"], "Zadanie spoza planu": []}
        klucze = {"Zadanie z planu": "aaa", "Zadanie spoza planu": "bbb"}

        class PustyIndeks:
            zadania: dict = {}
            grupy: dict = {}
            typy_zadan: dict = {}
            sceny: dict = {}
            pola_dialogow: dict = {}
            wybory: dict = {}
            opcje_npc: dict = {}

        linie = czytanka_czysta._sekcja_zadan(opisy, klucze, PustyIndeks(), {}, [])
        tekst = "\n".join(linie)
        self.assertIn("**Zadanie z planu:** opis", tekst)
        self.assertIn("## Pozostałe zadania i wątki", tekst)
        self.assertIn("**Zadanie spoza planu**", tekst)


if __name__ == "__main__":
    unittest.main()
