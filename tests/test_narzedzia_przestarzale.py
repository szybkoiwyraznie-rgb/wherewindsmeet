"""Pilnuje oznaczeń narzędzi przestarzałych (obsolete).

Każdy plik z `tools/przestarzale.txt` musi istnieć i mieć w docstringu
`PRZESTARZAŁE` oraz wskazanie na aktywny generator. Aktywny generator nie może
być oznaczony jako przestarzały. Dokumentacja musi wymieniać każdy wpis.
"""

from __future__ import annotations

import unittest
from pathlib import Path

KORZEN = Path(__file__).resolve().parent.parent
AKTYWNY = "czytanka_czysta.py"


def _lista() -> list[str]:
    sciezka = KORZEN / "tools" / "przestarzale.txt"
    return [
        wiersz.strip()
        for wiersz in sciezka.read_text(encoding="utf-8").splitlines()
        if wiersz.strip() and not wiersz.strip().startswith("#")
    ]


class NarzedziaPrzestarzaleTests(unittest.TestCase):
    def test_lista_nie_jest_pusta_i_ma_aktywny_generator(self):
        wpisy = _lista()
        self.assertTrue(wpisy, "tools/przestarzale.txt nie może być puste")
        self.assertNotIn(AKTYWNY, wpisy)
        self.assertTrue((KORZEN / "tools" / AKTYWNY).is_file())

    def test_kazdy_wpis_istnieje_i_ma_baner(self):
        for nazwa in _lista():
            plik = KORZEN / "tools" / nazwa
            self.assertTrue(plik.is_file(), f"brak pliku tools/{nazwa}")
            tekst = plik.read_text(encoding="utf-8")
            self.assertIn("PRZESTARZAŁE", tekst, f"tools/{nazwa} bez banera")
            self.assertIn(AKTYWNY, tekst, f"tools/{nazwa} nie wskazuje aktywnego generatora")

    def test_aktywny_generator_nie_jest_oznaczony(self):
        tekst = (KORZEN / "tools" / AKTYWNY).read_text(encoding="utf-8")
        self.assertNotIn("PRZESTARZAŁE", tekst)

    def test_dokumentacja_wymienia_kazde_narzedzie(self):
        dokument = (KORZEN / "docs" / "NARZEDZIA_PRZESTARZALE.md").read_text(encoding="utf-8")
        for nazwa in _lista():
            self.assertIn(nazwa, dokument, f"docs/NARZEDZIA_PRZESTARZALE.md bez {nazwa}")

    def test_skrypty_cli_ostrzegaja_na_stderr(self):
        import subprocess
        import sys

        for nazwa in ("buduj_czytanki.py", "zbuduj_czytanke_pelna.py", "buduj_czytanke_gry.py"):
            wynik = subprocess.run(
                [sys.executable, str(KORZEN / "tools" / nazwa), "--help"],
                capture_output=True, text=True, encoding="utf-8",
                timeout=120, check=False,
            )
            self.assertIn("PRZESTARZAŁE", wynik.stderr, f"tools/{nazwa}: brak ostrzeżenia na stderr")


if __name__ == "__main__":
    unittest.main()
