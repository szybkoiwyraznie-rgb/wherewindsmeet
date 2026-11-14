from __future__ import annotations

import unittest
from types import SimpleNamespace

from tools import uklad_scen


def indeks(**parts):
    base = dict(zadania={}, grupy={}, typy_zadan={}, sceny={}, wybory={}, opcje_npc={}, pola_dialogow=[])
    base.update(parts)
    return SimpleNamespace(**base)


def scena(numer, projekt="p", **extra):
    return {"d": numer, "o": [], "e": [["k", -1, "klucz"]], "p": projekt, **extra}


class TaskOrderTests(unittest.TestCase):
    def test_chain_follows_predecessors_and_start_task(self):
        ix = indeks(zadania={1: {"pre": [2]}, 2: {"pre": [3]}, 3: {}, 4: {"pre": [1]}})
        self.assertEqual(uklad_scen.porzadek_topologiczny(ix, [1, 2, 3, 4], start=3), ([3, 2, 1, 4], 0))

    def test_post_task_is_an_edge_too(self):
        ix = indeks(zadania={1: {"post": [3]}, 2: {}, 3: {"post": [2]}})
        self.assertEqual(uklad_scen.porzadek_topologiczny(ix, [1, 2, 3])[0], [1, 3, 2])

    def test_helper_without_predecessor_is_pulled_right_before_its_dependent(self):
        # 9 nie ma poprzednika, a wymaga go 3: stoi tuż przed 3, nie na początku
        ix = indeks(zadania={1: {}, 2: {"pre": [1]}, 3: {"pre": [2, 9]}, 9: {}})
        self.assertEqual(uklad_scen.porzadek_topologiczny(ix, [1, 2, 3, 9], start=1)[0], [1, 2, 9, 3])

    def test_chapter_parts_go_in_order(self):
        ix = indeks(zadania={1: {"pian": 2}, 2: {"pian": 1}, 3: {"pian": 1, "pre": [2]}, 4: {}})
        self.assertEqual(uklad_scen.porzadek_topologiczny(ix, [1, 2, 3, 4])[0], [2, 3, 1, 4])

    def test_cycle_is_broken_and_counted(self):
        ix = indeks(zadania={1: {"pre": [2]}, 2: {"pre": [1]}, 3: {}})
        order, cycles = uklad_scen.porzadek_topologiczny(ix, [1, 2, 3])
        self.assertEqual(sorted(order), [1, 2, 3])
        self.assertEqual(cycles, 1)

    def test_main_story_type_goes_first(self):
        ix = indeks(
            zadania={1: {"typ": 3}, 2: {"typ": 1}, 3: {"typ": None}, 4: {"typ": 8}, 5: {"typ": 77}},
            typy_zadan={3: {"kolejnosc": 2}, 8: {"kolejnosc": 1}},
        )
        self.assertEqual(uklad_scen.kolejnosc_typow(ix), [1, 8, 3, 77, None])


class PlacementTests(unittest.TestCase):
    def setUp(self):
        fields = [["tasks", "finish_dialogs", 9, 9], ["spaces.*.spawn_kit", "self_talk_dialogs_list[]", 9, 9], ["npc_dialog_select", "hello.{}.dialogs_id[]", 9, 9]]
        self.ix = indeks(
            zadania={
                1: {"typ": 1, "grupa": 5, "dialogi": {"zakonczenie": [100]}},
                2: {"typ": 1, "grupa": 5, "pre": [1], "dialogi": {"przyjecie": [200], "rozmowa": [100]}, "wybory": [9]},
                3: {"typ": 3, "grupa": 6, "dialogi": {"przyjecie": [300]}},
            },
            grupy={5: {"kolejnosc": 1, "start": 1}},
            typy_zadan={3: {"kolejnosc": 2}},
            wybory={"9_1": {"pytanie": 9, "krok": 1, "po_dialogach": [200], "wybory": [{"nr": 1, "tekst": "k", "dialogi": [210]}]}},
            opcje_npc={},
            pola_dialogow=fields,
            sceny={
                100: scena(100, r=[[0, "1"]]),
                101: scena(101),  # sąsiad numerem: za 100
                102: {"d": 102, "o": [], "e": [], "p": "p"},  # bez tekstu: nie jest sceną pakietu
                104: scena(104),  # odstęp 3 od 101: dalej ten sam ciąg
                120: scena(120),  # odstęp 16: już nie
                200: scena(200, x=[220]),
                210: scena(210),
                220: scena(220),
                300: scena(300, "q"),
                400: scena(400, r=[[1, "spaces.s7.spawn_kit#1"]], m=[7]),
                401: scena(401, r=[[2, "x"]]),
                500: scena(500, "inny"),
            },
        )
        self.uklad = uklad_scen.uloz(self.ix)

    def miejsce(self, numer):
        place = self.uklad.miejsca[numer]
        return (place.czesc, place.zadanie, place.moment, place.za)

    def test_every_scene_with_text_is_placed_once(self):
        self.assertEqual(sorted(self.uklad.miejsca), [100, 101, 104, 120, 200, 210, 220, 300, 400, 401, 500])
        listed = [place.dialog for places in self.uklad.sceny_zadania.values() for place in places]
        listed += [number for _name, numbers in self.uklad.projekty for number in numbers]
        listed += [number for _key, numbers in self.uklad.tlo for number in numbers]
        self.assertEqual(sorted(listed), sorted(self.uklad.miejsca))

    def test_direct_task_link_wins_and_first_task_takes_the_scene(self):
        self.assertEqual(self.miejsce(100), ("zadania", 1, "zakonczenie", None))
        self.assertEqual(self.miejsce(200), ("zadania", 2, "przyjecie", None))
        self.assertEqual(self.miejsce(300), ("zadania", 3, "przyjecie", None))

    def test_choice_targets_and_successors_follow_their_source(self):
        self.assertEqual(self.miejsce(210), ("zadania", 2, "wybor", None))
        self.assertEqual(self.miejsce(220), ("zadania", 2, "nastepstwo", 200))
        self.assertEqual([place.dialog for place in self.uklad.sceny_zadania[2]], [200, 220, 210])

    def test_neighbouring_numbers_are_attached_and_marked(self):
        self.assertEqual(self.miejsce(101), ("zadania", 1, "numeracja", 100))
        self.assertEqual(self.miejsce(104), ("zadania", 1, "numeracja", 100))
        self.assertEqual(self.miejsce(120)[0], "projekty")
        self.assertEqual([place.dialog for place in self.uklad.sceny_zadania[1]], [100, 101, 104])

    def test_background_talk_is_grouped_by_place_or_field(self):
        self.assertEqual(self.miejsce(400)[0], "tlo")
        self.assertEqual(self.miejsce(401)[0], "tlo")
        self.assertEqual(dict(self.uklad.tlo), {("miejsce", 7): [400], ("pole", "npc_dialog_select :: hello.{}.dialogs_id[]"): [401]})

    def test_rest_goes_by_project_and_number(self):
        self.assertEqual(self.uklad.projekty, [("inny", [500]), ("p", [120])])

    def test_sections_follow_type_then_group(self):
        self.assertEqual([(section.typ, section.grupa, section.zadania) for section in self.uklad.sekcje], [(1, 5, [1, 2]), (3, 6, [3])])


if __name__ == "__main__":
    unittest.main()
