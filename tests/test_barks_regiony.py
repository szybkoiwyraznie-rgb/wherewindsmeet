from __future__ import annotations

import unittest

from tools import barks_regiony


class RegionyTests(unittest.TestCase):
    def test_raport_liczy_pierscienie_i_klastry(self):
        punkty = {
            "blisko": [(0.0, 0.0)],
            "srednio": [(300.0, 400.0)],  # 500 m
            "daleko": [(3000.0, 4000.0)],  # 5 km
        }
        wynik = barks_regiony.raport(punkty, (0.0, 0.0), siatka=400, pierscienie=(200, 800, 1600))
        pierścienie = {row["do_m"]: row["klucze"] for row in wynik["pierścienie"]}
        self.assertEqual(pierścienie[200], 1)
        self.assertEqual(pierścienie[800], 2)
        self.assertEqual(pierścienie[1600], 2)
        self.assertEqual(wynik["z_pozycja"], 3)
        self.assertEqual(wynik["klastry"][0]["klucze"], 1)
        self.assertEqual(len(wynik["klastry"]), 3)

    def test_klucze_w_promieniu_sortuje_od_najbliszego(self):
        punkty = {"c": [(1000.0, 0.0)], "a": [(0.0, 0.0)], "b": [(300.0, 400.0)]}
        self.assertEqual(barks_regiony.klucze_w_promieniu(punkty, (0.0, 0.0), 600), ["a", "b"])
        self.assertEqual(barks_regiony.klucze_w_promieniu(punkty, (0.0, 0.0), 2000), ["a", "b", "c"])

    def test_klucz_w_wielu_miejscach_liczony_raz_i_najblizej(self):
        punkty = {"wielokrotny": [(0.0, 0.0), (5000.0, 0.0)]}
        wynik = barks_regiony.raport(punkty, (0.0, 0.0), siatka=400, pierscienie=(100,))
        self.assertEqual(wynik["z_pozycja"], 1)
        self.assertEqual(wynik["pierścienie"][0]["klucze"], 1)
        self.assertEqual(len(wynik["klastry"]), 2)


if __name__ == "__main__":
    unittest.main()
