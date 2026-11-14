from __future__ import annotations

import unittest

from tools import sceny_z_bazy

T = 0x1_0000_0000  # identyfikatory tekstu są większe niż 2^32


def span(text, time, order=None, **extra):
    node = {"Type": "EntityTextSpan", "text": text, "time": time, "formatted_text": "x"}
    if order is not None:
        node["order"] = order
    node.update(extra)
    return node


def group(tag, kind, number, name, tracks):
    return {
        "Type": "EntityTrackGroup",
        "entity_tag": tag,
        "entity_type": kind,
        "entity_no": number,
        "entity_name": name,
        "__children__": tracks,
    }


def text_track(spans, **extra):
    return {"Type": "EntityTextTrack", "__keyframes__": spans, **extra}


def rows(tracks, **config):
    return {
        "dialog_config": {"dialog_no": 77, "id": 5, **config},
        "project_info": {"project_name": "projekt-testowy"},
        "timeline": {"Type": "TimelinePObject", "name": "scena", "ui_type": 23, "total_duration": 9.5, "__tracks__": tracks},
        "used_sound_bnk": ["Sound/vo_test_01.bnk", 5],
    }


KNOWN = {T + n for n in range(1, 40)}


class SceneFromTableTests(unittest.TestCase):
    def build(self, tracks, **config):
        return sceny_z_bazy.scena_z_tabeli(77, rows(tracks, **config), KNOWN.__contains__)

    def test_lines_get_their_group_as_speaker_and_are_ordered_by_time(self):
        scene = self.build(
            [
                group("ja", 1, 0, "", [text_track([span(T + 1, 4.0, 1)])]),
                group("kowal", 3, 500, T + 9, [text_track([span(T + 2, 0.0, 0), span(T + 3, 8.0, 2)])]),
            ]
        )
        self.assertEqual([e["text_id"] for e in scene["elementy"]], [T + 2, T + 1, T + 3])
        self.assertEqual([e["mowca"] for e in scene["elementy"]], [1, 0, 1])
        self.assertEqual(scene["obsada"][1], {"tag": "kowal", "typ": 3, "entity_no": 500, "nazwa": T + 9, "kwestii": 2})
        self.assertIsNone(scene["obsada"][0]["nazwa"])
        self.assertEqual(scene["dialog_no"], 77)
        self.assertEqual(scene["projekt"], "projekt-testowy")
        self.assertEqual(scene["banki"], ["Sound/vo_test_01.bnk"])

    def test_speaker_name_is_not_an_element(self):
        scene = self.build([group("kowal", 3, 500, T + 9, [text_track([span(T + 2, 0.0, overrided_name=T + 7)])])])
        self.assertEqual(len(scene["elementy"]), 1)
        self.assertEqual(scene["elementy"][0]["nazwa"], T + 7)

    def test_boards_and_person_cards_are_collected_without_speaker(self):
        scene = self.build(
            [
                {"Type": "UITrack", "__keyframes__": [{"Type": "BlackSpan", "show_text": T + 4, "time": 1.0}]},
                {"Type": "UITrack", "__keyframes__": [{"Type": "PersonInfoSpan", "personal_name": T + 5, "title": T + 6, "time": 2.0}]},
                group("kowal", 3, 500, "", [text_track([span(T + 2, 3.0)])]),
            ]
        )
        self.assertEqual(
            [(e["rodzaj"], e["mowca"]) for e in scene["elementy"]],
            [("plansza", None), ("wizytowka_imie", None), ("wizytowka_tytul", None), ("kwestia", 0)],
        )

    def test_unknown_node_with_a_text_id_is_kept_as_other(self):
        scene = self.build([{"Type": "NowyTor", "__keyframes__": [{"Type": "NowySpan", "napis": T + 8, "time": 0.5}]}])
        self.assertEqual(scene["elementy"][0]["rodzaj"], "inne")
        self.assertEqual(scene["elementy"][0]["pole"], "NowySpan.napis")

    def test_numbers_that_are_not_text_ids_are_ignored(self):
        scene = self.build([group("kowal", 3, 500, "", [text_track([span(T + 999, 0.0), span(12345, 1.0), span(True, 2.0)])])])
        self.assertEqual(scene["elementy"], [])

    def test_line_outside_a_group_has_no_speaker(self):
        scene = self.build([text_track([span(T + 2, 0.0)])])
        self.assertIsNone(scene["elementy"][0]["mowca"])

    def test_gender_specific_track_marks_its_lines(self):
        scene = self.build(
            [
                group(
                    "ja",
                    1,
                    0,
                    "",
                    [
                        text_track([span(T + 1, 0.0)], valid_for_specific_type=True, entity_type=1),
                        text_track([span(T + 2, 0.0)], valid_for_specific_type=True, entity_type=2),
                        text_track([span(T + 3, 5.0)], valid_for_specific_type=False, entity_type=0),
                    ],
                )
            ]
        )
        self.assertEqual(
            sorted((e["text_id"], e["wariant"]) for e in scene["elementy"]),
            [(T + 1, sceny_z_bazy.BOHATER), (T + 2, sceny_z_bazy.BOHATERKA), (T + 3, sceny_z_bazy.WSPOLNY)],
        )
        # typ grupy (1 = gracz) nie jest wariantem płci
        self.assertEqual(scene["obsada"][0]["typ"], sceny_z_bazy.TYP_GRACZ)

    def test_config_keeps_only_set_flags(self):
        scene = self.build([], for_oversea=True, oversea_src_dialog_no=12, is_skip=False, disable=0)
        self.assertEqual(scene["konfiguracja"], {"id": 5, "for_oversea": True, "oversea_src_dialog_no": 12})

    def test_wrong_row_type_is_an_error(self):
        with self.assertRaises(ValueError):
            sceny_z_bazy.scena_z_tabeli(1, {"timeline": [1, 2]}, KNOWN.__contains__)

    def test_dialog_numbers_come_from_table_names(self):
        names = ["dialog_timelines.30", "tasks", "dialog_timelines.4", "dialog_timelines.x1", "dialog_timelinesX.9"]
        self.assertEqual(sceny_z_bazy.numery_dialogow(names), [4, 30])


if __name__ == "__main__":
    unittest.main()
