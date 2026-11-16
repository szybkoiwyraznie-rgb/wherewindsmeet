from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools import czytanka_czysta, tlumaczenie

KLUCZ = "5eb6a0036634f83f"
ID_BOHATER = "50241dd649380f3b"
ID_BOHATERKA = "c220449413345a19"


def _zapisz(sciezka: Path, wiersze: list[dict]) -> None:
    sciezka.parent.mkdir(parents=True, exist_ok=True)
    sciezka.write_text(
        "".join(json.dumps(w, ensure_ascii=False) + "\n" for w in wiersze), encoding="utf-8"
    )


class WariantyPlecTests(unittest.TestCase):
    """Kwestie zależne od płci bohatera: `@id` w magazynie, klucz tekstu w indeksie."""

    def setUp(self):
        self.katalog = tempfile.TemporaryDirectory()
        self.dodaj = Path(self.katalog.name)
        self.magazyn = self.dodaj / "tlumaczenie"
        self.indeks = self.dodaj / "index"
        _zapisz(self.magazyn / "pl_9.jsonl", [{"k": "9" * 16, "pl": "Zwykły przekład"}])
        _zapisz(self.magazyn / "pl_warianty.jsonl", [
            {"id": ID_BOHATER, "pl": "Ten znak to…"},
            {"id": ID_BOHATERKA, "pl": "Ten znak to… (bohaterka)"},
        ])
        _zapisz(self.indeks / "warianty.jsonl", [
            {"id": ID_BOHATER, "k": KLUCZ, "w": 1, "en": "This symbol..."},
            {"id": ID_BOHATERKA, "k": KLUCZ, "w": 2, "en": "This symbol..."},
        ])

    def tearDown(self):
        self.katalog.cleanup()

    def test_bez_wariantow_klucz_zalezny_od_plci_nie_ma_przekladu(self):
        magazyn = tlumaczenie.wczytaj(self.magazyn)
        self.assertIsNone(magazyn.przeklad(KLUCZ))

    def test_wariant_bohatera_rozpoznany_po_kluczu_tekstu(self):
        magazyn = tlumaczenie.wczytaj(self.magazyn, warianty=self.indeks / "warianty.jsonl")
        self.assertTrue(magazyn.ma(KLUCZ))
        self.assertEqual(magazyn.przeklad(KLUCZ), "Ten znak to…")
        self.assertEqual(magazyn.przeklad("@" + ID_BOHATERKA), "Ten znak to… (bohaterka)")

    def test_zwykly_przeklad_wygrywa_z_wariantem(self):
        magazyn = tlumaczenie.wczytaj(self.magazyn, warianty=self.indeks / "warianty.jsonl")
        self.assertEqual(magazyn.po_kluczu_pelny()[KLUCZ], "Ten znak to…")
        self.assertEqual(magazyn.po_kluczu_pelny()["9" * 16], "Zwykły przekład")

    def test_czytanka_czyta_warianty(self):
        pl = czytanka_czysta._magazyn(self.magazyn, self.indeks)
        self.assertEqual(pl[KLUCZ], "Ten znak to…")


if __name__ == "__main__":
    unittest.main()
