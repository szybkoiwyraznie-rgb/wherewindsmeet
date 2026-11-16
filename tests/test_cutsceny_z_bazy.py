"""Wiązanie napis ↔ cutscena z bazy gry (`tools/cutsceny_z_bazy.py`).

Dane w testach są wymyślone: budujemy małą bazę w formacie gry (MANIFEST,
`index*`, `data*`) i sprawdzamy, że program znajduje tabelę wiążącą oraz że
`chronologia` korzysta z wyniku.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools import chronologia, cutsceny_z_bazy
from tests.test_baza_gry import (container, index_chunk, manifest_chunk, pad8,
                                 schema_chunk, struct_row)

KATALOG = Path(__file__).resolve().parent.parent


def _baza(katalog: Path, *, z_danymi: bool = True) -> None:
    """Baza z jedną tabelą `cutscene_subtitle(cutscene_no, text_id)`."""
    wiersze = [(30161, 591141), (30161, 591149), (30177, 590000)]
    if z_danymi:
        wartosci = [pad8(struct_row([(0, cut), (1, tekst)])) for cut, tekst in wiersze]
        dane = b"".join(wartosci)
        offsety, pozycja = [], 0
        for wartosc in wartosci:
            offsety.append(pozycja)
            pozycja += len(wartosc) // 8
        (katalog / "data1").write_bytes(container([dane]))
        (katalog / "index1").write_bytes(container([
            index_chunk([(1, (1, 0, offsety[0], len(wartosci[0]) // 8)),
                         (2, (1, 0, offsety[1], len(wartosci[1]) // 8)),
                         (3, (1, 0, offsety[2], len(wartosci[2]) // 8))]),
            schema_chunk(["cutscene_no", "text_id"]),
        ]))
    else:
        (katalog / "index1").write_bytes(container([schema_chunk(["cutscene_no", "text_id"])]))
    manifest = manifest_chunk([
        {"name": "cutscene_subtitle", "rows": len(wiersze),
         "parts": [(1, 0)] if z_danymi else [], "schema": (1, 1 if z_danymi else 0),
         "flags": 0x400},
    ])
    (katalog / "MANIFEST").write_bytes(container([manifest]))


def _index(katalog: Path) -> None:
    """Wyciąg z gry: numery cutscen i wiersze puli napisów."""
    katalog.mkdir(parents=True, exist_ok=True)
    (katalog / "przerywniki.jsonl").write_text(
        json.dumps({"no": 30161, "streszczenie": "a"}) + "\n" +
        json.dumps({"no": 30177, "streszczenie": "b"}) + "\n", encoding="utf-8")
    (katalog / "cutsceny_kontekst.jsonl").write_text(
        json.dumps({"typ": "napis", "wiersz": 591141, "k": "klucz1"}) + "\n" +
        json.dumps({"typ": "napis", "wiersz": 591149, "k": "klucz2"}) + "\n" +
        json.dumps({"typ": "napis", "wiersz": 590000, "k": "klucz3"}) + "\n",
        encoding="utf-8")


class SzukanieWiazania(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.dane = self.root / "dane"
        self.dane.mkdir()
        self.index = self.root / "index"
        _index(self.index)

    def test_znajduje_tabele_i_zapisuje_wiazanie(self):
        _baza(self.dane)
        wyj = self.root / "cutsceny_napisy.jsonl"
        wynik = cutsceny_z_bazy.szukaj([self.dane], self.index)
        self.assertIsNotNone(wynik["znalezione"], wynik)
        self.assertEqual(wynik["znalezione"]["tabela"], "cutscene_subtitle")
        zapisane = cutsceny_z_bazy.zapisz(wynik, wyj, self.index)
        self.assertEqual(zapisane, 3)
        linie = [json.loads(x) for x in wyj.read_text(encoding="utf-8").splitlines()]
        self.assertEqual([(x["no"], x["wiersz"], x["k"]) for x in linie],
                         [(30161, 591141, "klucz1"), (30161, 591149, "klucz2"),
                          (30177, 590000, "klucz3")])

    def test_same_schematy_wystarcza_do_wskazania_tabeli(self):
        _baza(self.dane, z_danymi=False)
        wynik = cutsceny_z_bazy.szukaj([self.dane], self.index, tylko_schematy=True)
        self.assertEqual(wynik["tryb"], "schematy")
        self.assertIn("cutscene_subtitle", wynik["podejrzanych"])
        self.assertEqual(wynik["wiazania"], {})

    def test_bez_danych_nie_udaje_wiazania(self):
        _baza(self.dane, z_danymi=False)
        wynik = cutsceny_z_bazy.szukaj([self.dane], self.index)
        self.assertIsNone(wynik["znalezione"])
        self.assertIn("brak plików data*", wynik["blad"])


class ChronologiaCzytaWiazanie(unittest.TestCase):
    def test_plik_wiazania_jest_czytany(self):
        with tempfile.TemporaryDirectory() as tmp:
            katalog = Path(tmp)
            (katalog / "cutsceny_napisy.jsonl").write_text(
                json.dumps({"no": 30161, "wiersz": 591141, "k": "klucz1"}) + "\n" +
                json.dumps({"no": 30161, "wiersz": 591149, "k": "klucz2"}) + "\n",
                encoding="utf-8")
            mapa = chronologia._napisy_z_bazy(katalog)
            self.assertEqual(mapa, {30161: ["klucz1", "klucz2"]})

    def test_brak_pliku_to_puste_wiazanie(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(chronologia._napisy_z_bazy(Path(tmp)), {})


if __name__ == "__main__":
    unittest.main()
