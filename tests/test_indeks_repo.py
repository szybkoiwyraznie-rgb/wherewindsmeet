from __future__ import annotations

import unittest
from pathlib import Path

from tools import indeks

ROOT = Path(__file__).resolve().parent.parent
REPO_LIMIT = 10 * 1024 * 1024


class CommittedIndexTests(unittest.TestCase):
    """Kontrola wyciągu `index/` w repozytorium: spójny z manifestem i kompletny w sobie."""

    @classmethod
    def setUpClass(cls):
        cls.root = ROOT / "index"
        cls.indeks = indeks.wczytaj(cls.root)

    def test_files_match_manifest_and_fit_repository_limit(self):
        self.assertEqual(indeks.sprawdz_pliki(self.root), [])
        for path in self.root.iterdir():
            self.assertLessEqual(path.stat().st_size, REPO_LIMIT, path.name)

    def test_counts_match_manifest(self):
        numbers = self.indeks.manifest["liczby"]
        self.assertEqual(len(self.indeks.teksty), numbers["unikalnych_tekstow_w_zakresie"])
        self.assertEqual(len(self.indeks.sceny), numbers["scen"])
        self.assertEqual(sum(len(scene["e"]) for scene in self.indeks.sceny.values()), numbers["elementow_scen"])
        self.assertEqual(len(self.indeks.zadania), numbers["zadan"])
        self.assertEqual(len(self.indeks.warianty), numbers["kwestii_zaleznych_od_plci_bohatera"])

    def test_every_reference_points_to_a_stored_text(self):
        texts = self.indeks.teksty
        for scene in self.indeks.sceny.values():
            for person in scene["o"]:
                for key in person[3:]:
                    if key:
                        self.assertIn(key, texts)
            for element in scene["e"]:
                self.assertIn(element[2], texts)
                if len(element) > 5 and element[5]:
                    self.assertIn(element[5], texts)
        for task in self.indeks.zadania.values():
            for name in ("nazwa", "cel", "opis"):
                if name in task:
                    self.assertIn(task[name], texts)
        for row in self.indeks.wybory.values():
            for choice in row["wybory"]:
                self.assertIn(choice["tekst"], texts)

    def test_every_line_has_a_speaker_from_the_cast(self):
        lines = 0
        for scene in self.indeks.sceny.values():
            for element in scene["e"]:
                if element[0] == "k":
                    lines += 1
                    self.assertTrue(0 <= element[1] < len(scene["o"]), scene["d"])
        self.assertEqual(lines, self.indeks.manifest["liczby"]["kwestii"])
        self.assertEqual(self.indeks.manifest["pokrycie"]["kwestii_bez_grupy_mowcy"], 0)

    def test_gender_variant_lines_carry_their_text_id(self):
        seen = set()
        for scene in self.indeks.sceny.values():
            for element in scene["e"]:
                if len(element) > 3 and element[3]:
                    self.assertIn(element[4], self.indeks.warianty)
                    seen.add(element[4])
        self.assertEqual(seen, set(self.indeks.warianty))


if __name__ == "__main__":
    unittest.main()
