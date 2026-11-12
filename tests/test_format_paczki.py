from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools import format_paczki as fmt
from tools import tlumaczenie


class EncodingTests(unittest.TestCase):
    def test_round_trip_of_control_characters_and_backslashes(self):
        for text in ("zwykły", "linia\nlinia", "tab\tulator", "powrót\rkaretki", "ukośnik \\n dosłowny", "\\\\", "koniec\\"):
            with self.subTest(text=text):
                encoded = fmt.zakoduj(text)
                self.assertNotIn("\n", encoded)
                self.assertEqual(fmt.odkoduj(encoded), text)

    def test_unknown_escape_is_left_alone(self):
        self.assertEqual(fmt.odkoduj("a\\qb"), "a\\qb")

    def test_tokens_are_found_in_order(self):
        self.assertEqual(fmt.tokeny("造成#Y{0}#E点，持续$T(2001)秒"), ["#Y", "{0}", "#E", "$T(2001)"])
        self.assertEqual(fmt.tokeny("<nazwa|780|#C|15> +{1:.1%}"), ["|780|#C|15>", "{1:.1%}"])
        self.assertEqual(fmt.tokeny("<LINK id='a' color='#8c5823'>x</LINK>"), ["<LINK id='a' color='#8c5823'>", "</LINK>"])
        self.assertEqual(fmt.tokeny("%d szt. %s, 100%%"), ["%d", "%s", "%%"])
        self.assertEqual(fmt.tokeny("#a66b3c kolor#E [#201] @T"), ["#a66b3c", "#E", "[#201]", "@T"])
        self.assertEqual(fmt.tokeny("[[{4}?x]]"), ["[[", "{4}", "]]"])

    def test_newline_is_not_a_token_but_literal_backslash_n_is(self):
        self.assertEqual(fmt.tokeny(fmt.zakoduj("a\nb")), [])
        self.assertEqual(fmt.tokeny(fmt.zakoduj("a\\nb")), ["\\\\n"])

    def test_text_after_end_colour_is_not_taken_for_a_hex_colour(self):
        self.assertEqual(fmt.tokeny("#Y10#E #EDefeat"), ["#Y", "#E", "#E"])

    def test_token_difference(self):
        self.assertEqual(fmt.roznica_tokenow("#Ya#E {0}", "#Ya {0} {1}"), (["#E"], ["{1}"]))
        self.assertEqual(fmt.roznica_tokenow("{0} {1}", "{1} {0}"), ([], []))
        self.assertEqual(fmt.rozne_tokeny("#Ya#E #Yb#E"), ["#Y", "#E"])

    def test_edge_whitespace(self):
        self.assertEqual(fmt.brzegi("  a b \n"), ("  ", " \n"))
        self.assertEqual(fmt.brzegi("ab"), ("", ""))
        self.assertEqual(fmt.brzegi("   "), ("", ""))


PLIK = """# tytuł

#### Scena 1/2 — dialog 5
- projekt: x

1. [Kwestia — A] tekst
   klucz: 0123456789abcdef
   EN: text
   PL:   przekład pierwszy<SPACJE>
2. [Kwestia — B] tekst
   (powtórzenie elementu 1 — nie wpisuj tu nic)
3. [Kwestia — gracz, wariant: bohater] tekst3
   klucz: @00000001000000aa
   EN: t
   PL:
4. [Kwestia — C] tekst4
   klucz: aaaaaaaaaaaaaaaa
   PL: linia pierwsza
   i druga linia
5. [Kwestia — D] stary
   klucz: bbbbbbbbbbbbbbbb
   PL (już jest): stary przekład
6. [Kwestia — E] ostatni
   klucz: cccccccccccccccc
   PL: koniec
""".replace("<SPACJE>", "  ")  # spacje na końcu linii: edytory tłumacza je zostawiają albo ucinają


class EntryParsingTests(unittest.TestCase):
    def test_entries_are_read_with_key_text_and_line(self):
        entries = list(fmt.czytaj_wpisy(PLIK))
        self.assertEqual([entry.klucz for entry in entries], ["0123456789abcdef", "@00000001000000aa", "aaaaaaaaaaaaaaaa", "cccccccccccccccc"])
        self.assertEqual(entries[0].pl, "przekład pierwszy")
        self.assertEqual(entries[0].linia, 9)
        self.assertEqual(entries[1].pl, "")

    def test_broken_line_is_flagged(self):
        entries = {entry.klucz: entry for entry in fmt.czytaj_wpisy(PLIK)}
        self.assertTrue(entries["aaaaaaaaaaaaaaaa"].ciag_dalszy)
        self.assertFalse(entries["0123456789abcdef"].ciag_dalszy)
        self.assertFalse(entries["cccccccccccccccc"].ciag_dalszy)

    def test_existing_translation_line_is_not_an_entry(self):
        self.assertNotIn("bbbbbbbbbbbbbbbb", [entry.klucz for entry in fmt.czytaj_wpisy(PLIK)])


class StoreTests(unittest.TestCase):
    def test_round_trip_and_stable_split(self):
        store = tlumaczenie.Magazyn()
        store.ustaw("a000000000000001", "pierwszy")
        store.ustaw("a000000000000002", "drugi\\nwiersz")
        store.ustaw("f000000000000003", "trzeci")
        store.ustaw("@00000001000000aa", "wariant")
        with tempfile.TemporaryDirectory(prefix="wwm-magazyn-") as temp:
            written = tlumaczenie.zapisz(temp, store)
            self.assertEqual(written, ["pl_a.jsonl", "pl_f.jsonl", "pl_warianty.jsonl"])
            loaded = tlumaczenie.wczytaj(temp)
            self.assertEqual(loaded.po_kluczu, store.po_kluczu)
            self.assertEqual(loaded.po_id, {"00000001000000aa": "wariant"})
            self.assertTrue(loaded.ma("@00000001000000aa"))
            self.assertEqual(loaded.przeklad("a000000000000001"), "pierwszy")
            self.assertIsNone(loaded.przeklad("0000000000000000"))
            self.assertEqual(len(loaded), 4)
            # usunięcie ostatniego wpisu części usuwa jej plik
            del loaded.po_kluczu["f000000000000003"]
            tlumaczenie.zapisz(temp, loaded)
            self.assertFalse((Path(temp) / "pl_f.jsonl").exists())

    def test_missing_directory_is_an_empty_store(self):
        self.assertEqual(len(tlumaczenie.wczytaj("/nie/ma/takiego/katalogu")), 0)

    def test_bad_rows_and_keys_are_errors(self):
        with tempfile.TemporaryDirectory(prefix="wwm-magazyn-") as temp:
            (Path(temp) / "pl_a.jsonl").write_text('{"k": "a000000000000001"}\n', encoding="utf-8")
            with self.assertRaises(tlumaczenie.MagazynError):
                tlumaczenie.wczytaj(temp)
        store = tlumaczenie.Magazyn(po_kluczu={"zly-klucz": "x"})
        with tempfile.TemporaryDirectory(prefix="wwm-magazyn-") as temp:
            with self.assertRaises(tlumaczenie.MagazynError):
                tlumaczenie.zapisz(temp, store)


if __name__ == "__main__":
    unittest.main()
