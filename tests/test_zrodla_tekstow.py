from __future__ import annotations

import unittest

from tools import baza_gry, zrodla_tekstow

T = 0x1_0000_0000
KNOWN = {T + n for n in range(1, 60)}


class FakeBaza:
    """Tylko to, czego używa przegląd: nazwy tabel i wiersze."""

    def __init__(self, tables: dict):
        self._tables = tables
        self.tabele = {name: None for name in tables}

    def wiersze(self, name):
        rows = self._tables[name]
        if isinstance(rows, Exception):
            raise rows
        yield from rows


class TextSourceTests(unittest.TestCase):
    def test_table_kind_replaces_identifiers_after_first_part(self):
        self.assertEqual(zrodla_tekstow.rodzaj_tabeli("spaces.s501.region"), "spaces.*.region")
        self.assertEqual(zrodla_tekstow.rodzaj_tabeli("stuff_items"), "stuff_items")
        self.assertEqual(zrodla_tekstow.rodzaj_tabeli("task2_data"), "task2_data")

    def test_paths_cover_lists_nested_objects_and_numeric_keys(self):
        row = {"name": T + 1, "data": [{"text": T + 2}, {"text": T + 3}], 7: {"opis": T + 4}, "12": T + 5, "liczba": 9}
        self.assertEqual(
            zrodla_tekstow.teksty_wiersza(row, KNOWN.__contains__),
            [("name", T + 1), ("data[].text", T + 2), ("data[].text", T + 3), ("{}.opis", T + 4), ("{}", T + 5)],
        )

    def test_row_label_prefers_name_over_title(self):
        known = KNOWN.__contains__
        self.assertEqual(zrodla_tekstow.etykieta_wiersza({"title": T + 1, "name": T + 2, "opis": T + 3}, known), T + 2)
        self.assertEqual(zrodla_tekstow.etykieta_wiersza({"task_name": T + 4, "opis": T + 3}, known), T + 4)
        self.assertEqual(zrodla_tekstow.etykieta_wiersza({"opis": T + 3}, known), 0)
        self.assertEqual(zrodla_tekstow.etykieta_wiersza([T + 3], known), 0)

    def test_collect_records_kind_path_row_and_label(self):
        baza = FakeBaza(
            {
                "stuff_items": [(10, {"name": T + 1, "describe_str": T + 2}), (11, {"name": T + 3})],
                "spaces.s5.region": [(1, {"name": T + 4})],
                "dialog_timelines.9": [("timeline", {"text": T + 5})],
            }
        )
        seen = []
        result = zrodla_tekstow.zbierz(
            baza, KNOWN.__contains__, pomin_rodziny=("dialog_timelines",), obserwator=lambda *args: seen.append(args[:3])
        )
        self.assertNotIn(T + 5, result.wystapienia)
        kind, path = result.pochodzenia[result.wystapienia[T + 2][0][0]]
        self.assertEqual((kind, path), ("stuff_items", "describe_str"))
        self.assertEqual(result.wystapienia[T + 2][0][1:], ("10", T + 1))
        # w tabelach wielokrotnych klucz wiersza niesie nazwę tabeli
        self.assertEqual(result.wystapienia[T + 4][0][1], "spaces.s5.region#1")
        self.assertEqual(result.wiersze["stuff_items"], 2)
        self.assertEqual(seen[0], ("stuff_items", "stuff_items", 10))
        self.assertEqual(sum(result.liczba.values()), 4)

    def test_occurrences_are_capped_but_counted(self):
        baza = FakeBaza({"text_msg": [(n, {"content": T + 1}) for n in range(9)]})
        result = zrodla_tekstow.zbierz(baza, KNOWN.__contains__)
        self.assertEqual(len(result.wystapienia[T + 1]), zrodla_tekstow.MAKS_WYSTAPIEN)
        self.assertEqual(result.liczba[0], 9)

    def test_unreadable_table_is_reported_not_fatal(self):
        baza = FakeBaza({"zepsuta": baza_gry.BazaError("nieznany typ"), "dobra": [(1, {"name": T + 1})]})
        result = zrodla_tekstow.zbierz(baza, KNOWN.__contains__)
        self.assertEqual(list(result.bledy), ["zepsuta"])
        self.assertIn(T + 1, result.wystapienia)


if __name__ == "__main__":
    unittest.main()
