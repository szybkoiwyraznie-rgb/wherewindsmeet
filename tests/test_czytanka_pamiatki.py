from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools import czytanka_czysta


class _Tekst:
    def __init__(self, wiersz, zh, en=None):
        self.w = wiersz
        self.zrodlo = zh
        self.en = en
        self.z_en = False


class _Indeks:
    """Minimalny wyciąg: nazwa przedmiotu, właściciel i historia pamiątki."""

    zrodla = [
        ["equip_items", "name", 1],
        ["curio_owner", "owner_name", 1],
        ["text_msg", "content", 1],
    ]

    def __init__(self):
        self.teksty = {
            "nazwa1": _Tekst((0, "1100010"), "旧枪", "Old spear"),
            "wlasciciel1": _Tekst((1, "1"), "江无浪", "Jiang Wulang"),
            "historia1": _Tekst((2, "741036"), "历史一", "Story one\nsecond line"),
            "nazwa2": _Tekst((0, "1100201"), "护腕", "Old Bracers"),
            "historia2": _Tekst((2, "741001"), "历史二", "Story two"),
        }


WLASCICIEL = {"wlasciciel_ikona": "head_npc_zhuxiannpc_jiangwulang"}


class PamiatkiTests(unittest.TestCase):
    def _katalog(self, wiersze: list[dict]) -> tempfile.TemporaryDirectory:
        katalog = tempfile.TemporaryDirectory()
        sciezka = Path(katalog.name, "pamiatki.jsonl")
        sciezka.write_text(
            "".join(json.dumps(w, ensure_ascii=False) + "\n" for w in wiersze),
            encoding="utf-8",
        )
        return katalog

    def test_pamiatka_z_przekladem(self):
        with self._katalog([{"id": 35, "przedmiot": 1100010, "wlasciciel": 1,
                             "pamiec": 741036, **WLASCICIEL}]) as katalog:
            linie = czytanka_czysta._pamiatki(
                _Indeks(), {"historia1": "Historia po polsku", "nazwa1": "Stara włócznia",
                 "wlasciciel1": "Jiang Wulang"},
                set(), {}, katalog)
        self.assertIn("# Pamiątki — przedmioty z historią", linie)
        self.assertIn("**Jiang Wulang — Stara włócznia**", linie)
        self.assertIn("Historia po polsku", linie)

    def test_bez_przekladu_gwiazdka_i_wlasciciel_z_ikony(self):
        indeks = _Indeks()
        indeks.teksty.pop("wlasciciel1")  # właściciela nie ma w wyciągu — zostaje ikona
        with self._katalog([{"id": 35, "przedmiot": 1100010, "wlasciciel": 1,
                             "pamiec": 741036, **WLASCICIEL}]) as katalog:
            linie = czytanka_czysta._pamiatki(
                indeks, {"nazwa1": "Stara włócznia"}, set(), {}, katalog)
        self.assertIn("**jiangwulang — Stara włócznia**", linie)
        self.assertIn(czytanka_czysta.GWIAZDKA + "Story one second line", linie)

    def test_bez_nazwy_przedmiotu_nie_wchodzi_ale_jest_policzona(self):
        statystyka: dict = {}
        with self._katalog([{"id": 54, "przedmiot": 999, "wlasciciel": 1,
                             "pamiec": 741036, **WLASCICIEL}]) as katalog:
            linie = czytanka_czysta._pamiatki(_Indeks(), {}, set(), statystyka, katalog)
        self.assertEqual(linie, [])
        self.assertEqual(statystyka["pamiatki_bez_nazwy"], 1)
        self.assertNotIn("pamiatki", statystyka)

    def test_historia_uzyta_w_scenie_nie_powtarza_sie(self):
        with self._katalog([{"id": 35, "przedmiot": 1100010, "wlasciciel": 1,
                             "pamiec": 741036, **WLASCICIEL}]) as katalog:
            linie = czytanka_czysta._pamiatki(
                _Indeks(), {"nazwa1": "Stara włócznia"}, {"historia1"}, {}, katalog)
        self.assertEqual(linie, [])

    def test_brak_pliku_nic_nie_zmienia(self):
        with tempfile.TemporaryDirectory() as katalog:
            self.assertEqual(czytanka_czysta._pamiatki(_Indeks(), {}, set(), {}, katalog), [])

    def test_liczba_pamiatek_w_statystyce(self):
        statystyka: dict = {}
        with self._katalog([
            {"id": 35, "przedmiot": 1100010, "wlasciciel": 1, "pamiec": 741036, **WLASCICIEL},
            {"id": 2, "przedmiot": 1100201, "wlasciciel": None, "pamiec": 741001},
        ]) as katalog:
            czytanka_czysta._pamiatki(_Indeks(), {}, set(), statystyka, katalog)
        self.assertEqual(statystyka["pamiatki"], 2)


if __name__ == "__main__":
    unittest.main()


class BazaPamiatkiTests(unittest.TestCase):
    def test_liczba_odrzuca_smieci(self):
        from tools import pamiatki_z_bazy
        self.assertEqual(pamiatki_z_bazy._liczba("1100010"), 1100010)
        self.assertEqual(pamiatki_z_bazy._liczba(7), 7)
        self.assertIsNone(pamiatki_z_bazy._liczba(None))
        self.assertIsNone(pamiatki_z_bazy._liczba(""))
        self.assertIsNone(pamiatki_z_bazy._liczba("abc"))
        self.assertIsNone(pamiatki_z_bazy._liczba(True))

    def test_bez_bazy_konczy_sie_kodem_2(self):
        from tools import pamiatki_z_bazy
        with tempfile.TemporaryDirectory() as pusty:
            self.assertEqual(pamiatki_z_bazy.main([pusty, "--wyj", str(Path(pusty, "x.jsonl"))]), 2)
