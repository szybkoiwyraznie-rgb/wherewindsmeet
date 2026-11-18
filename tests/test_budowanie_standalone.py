"""Budowanie (czytanka, paczka dla tłumacza, łatka, instalator) stoi na repo.

Bezwzględny wymóg właściciela: **build nie może potrzebować niczego spoza
repozytorium** — żadnego `google_drive/`, żadnego `local/`, żadnego dociągania
z Dysku. Pliki z Dysku są wyłącznie materiałem do inwestygacji (baza gry,
paczki aktualizacji), a nie wejściem budowania.

Ten test pilnuje dwóch rzeczy:

1. moduły budowania nie sięgają po bazę gry (`tools.baza_gry`) ani po katalogi
   gitignore'owane,
2. import `tools.czytanka_czysta` nie wciąga bazy gry do procesu — czyli
   czytankę da się zbudować na maszynie bez plików gry.
"""

from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Wejścia budowania: to one muszą być samowystarczalne.
MODULY_BUDOWANIA = (
    "tools/czytanka_czysta.py",
    "tools/zbuduj_czytanke_pelna.py",
    "tools/buduj_paczke.py",
    "tools/zbuduj_latke.py",
    "tools/one_click_patch.py",
    "tools/build_installer_kit.py",
)

# Ścieżki, których w kodzie budowania być nie może (w komentarzach i opisach mogą).
ZAKAZANE_SCIEZKI = ("google_drive/", "google_drive\\", "local/dane", "local\\dane")


def _zrodlo(sciezka: str) -> str:
    return (ROOT / sciezka).read_text(encoding="utf-8")


def _kod_bez_napisow(sciezka: str) -> list[str]:
    """Linie kodu z pominięciem docstringów i komentarzy."""
    tekst = _zrodlo(sciezka)
    drzewo = ast.parse(tekst)
    pominiete: set[int] = set()
    for wezel in ast.walk(drzewo):
        if isinstance(wezel, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            cialo = getattr(wezel, "body", [])
            if (
                cialo
                and isinstance(cialo[0], ast.Expr)
                and isinstance(cialo[0].value, ast.Constant)
                and isinstance(cialo[0].value.value, str)
            ):
                for numer in range(cialo[0].lineno, (cialo[0].end_lineno or cialo[0].lineno) + 1):
                    pominiete.add(numer)
    wynik = []
    for numer, linia in enumerate(tekst.splitlines(), start=1):
        if numer in pominiete or linia.lstrip().startswith("#"):
            continue
        wynik.append(linia)
    return wynik


class BudowanieBezDanychZPozaRepo(unittest.TestCase):
    def test_budowanie_nie_siega_po_baze_gry(self):
        for sciezka in MODULY_BUDOWANIA:
            kod = "\n".join(_kod_bez_napisow(sciezka))
            self.assertNotIn("baza_gry", kod, f"{sciezka}: budowanie nie może czytać bazy gry")

    def test_budowanie_nie_siega_po_katalogi_z_gitignore(self):
        for sciezka in MODULY_BUDOWANIA:
            kod = "\n".join(_kod_bez_napisow(sciezka))
            for zakazana in ZAKAZANE_SCIEZKI:
                self.assertNotIn(zakazana, kod, f"{sciezka}: zakazana ścieżka {zakazana}")

    def test_import_czytanki_nie_wciaga_bazy_gry(self):
        for nazwa in [n for n in list(sys.modules) if n.startswith("tools.")]:
            del sys.modules[nazwa]
        import tools.czytanka_czysta  # noqa: F401

        self.assertNotIn("tools.baza_gry", sys.modules)

    def test_kolejnosc_gry_importuje_baze_dopiero_w_funkcji(self):
        """`tools.kolejnosc_gry` jest używany przez czytankę — baza ma być leniwa."""
        drzewo = ast.parse(_zrodlo("tools/kolejnosc_gry.py"))
        importy = [
            w
            for w in ast.walk(drzewo)
            if isinstance(w, (ast.Import, ast.ImportFrom))
            and "baza_gry" in ast.dump(w)
        ]
        self.assertTrue(importy, "oczekiwano importu baza_gry (w funkcji)")
        for wezel in importy:
            self.assertGreater(getattr(wezel, "col_offset", 0), 0)

    def test_dane_z_dysku_sa_tylko_do_inwestygacji(self):
        """Narzędzia inwestygacyjne mogą czytać bazę gry — i tylko one."""
        with_bazy = {
            sciezka.name
            for sciezka in (ROOT / "tools").glob("*.py")
            if "from tools import baza_gry" in sciezka.read_text(encoding="utf-8")
            or "baza_gry.Baza(" in sciezka.read_text(encoding="utf-8")
        }
        dozwolone = {
            "baza_gry.py", "szukaj_w_bazie.py", "cutsceny_z_bazy.py", "kolejnosc_gry.py",
            "pamiatki_z_bazy.py", "poi_z_bazy.py", "wyciag.py", "zrodla_tekstow.py",
            "sprawdz_baze.py", "sciezki_vfs.py", "zadania_sceny.py", "dialog_subsequent.py",
        }
        self.assertTrue(with_bazy)
        self.assertLessEqual(with_bazy, dozwolone, f"nowe zależności: {sorted(with_bazy - dozwolone)}")


if __name__ == "__main__":
    unittest.main()
