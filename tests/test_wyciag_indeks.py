from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tests.test_sceny_z_bazy import group, rows, span, text_track
from tests.test_zrodla_tekstow import FakeBaza
from tools import indeks, mapa_tekstow, wyciag

T = 0x1_0000_0000
K = mapa_tekstow.klucz

ZH = {
    T + 1: "kwestia kowala",
    T + 2: "kwestia gracza",
    T + 3: "wersja bohatera",
    T + 4: "wersja bohatera",  # ten sam tekst, inny identyfikator: wariant bohaterki
    T + 9: "Kowal",
    T + 10: "Mistrz kuźni",
    T + 20: "Miecz",
    T + 21: "Opis miecza",
    T + 22: "Miecz",  # powtórzony tekst pod innym id
    T + 30: "Pierwsze zadanie",
    T + 31: "Idź do kowala",
    T + 32: "Rozdział pierwszy",
    T + 40: "Kuźnia",
    T + 50: "dymek pierwszy",
    T + 60: "Tak",
    T + 61: "Nie",
    T + 62: "Rozmowa",
    T + 70: "tylko chiński, nikt nie wskazuje",
    T + 80: "Stary kowal",
    T + 81: "Historia",
    T + 82: "Dawno temu…",
}
EN = {
    T + 1: "smith line",
    T + 2: "player line",
    T + 3: "male version",
    T + 4: "female version",
    T + 9: "Smith",
    T + 20: "Sword",
    T + 22: "Blade",
    T + 21: "Sword description",
    T + 30: "First quest",
    T + 99: "english only text",
}


def tables() -> dict:
    scene = rows(
        [
            group("kowal_roboczy", 3, 9001, "", [text_track([span(T + 1, 0.0, 0)])]),
            group(
                "ja",
                1,
                0,
                "",
                [
                    text_track([span(T + 2, 1.0, 1)]),
                    text_track([span(T + 3, 2.0)], valid_for_specific_type=True, entity_type=1),
                    text_track([span(T + 4, 2.0)], valid_for_specific_type=True, entity_type=2),
                ],
            ),
        ]
    )
    empty = rows([])
    return {
        "dialog_timelines.100": list(scene.items()),
        "dialog_timelines.101": list(empty.items()),
        "dialog_timelines.102": list(empty.items()),
        "tasks": [
            (1, {"no": 1, "group": 5, "task_type": 1, "post_task": [2], "task_name": T + 30, "task_target_str": T + 31, "finish_dialogs": 100, "task_space": 7}),
            (2, {"no": 2, "group": 5, "task_type": 1, "pre_task": [1], "finish_dialogs": 101, "process_interact_param": ["102", "55"]}),
            (3, {"no": 3, "group": 5, "task_type": 1, "pre_task": [2], "finish_dialogs": 102}),
        ],
        "task_group_info": [(5, {"id": 5, "group_name": T + 32, "group_sort": 1, "start_task": 1, "end_task": [[3]]})],
        "group_tasks": [(5, [1, 2, 3])],
        "branch_data": [("9_1", {"ques_argue_no": 9, "ques_each_no": 1, "main_title": T + 62, "choice_1": T + 60, "choice_2": T + 61, "choice_dialogs_1": 101, "ques_stop_dialogs": [[100]]})],
        "branch_dialog_subsequent": [(100, [101])],
        "entity_init_data": [(700, {"id": 700, "billboard_data": {"name": T + 9, "title": T + 10}})],
        "spaces.s7.entity": [(9001, {"npc_no": 700, "serial_id": 9001})],
        "space_info": [(7, {"name": T + 40, "fb_name": "kuznia_robocza"})],
        "stuff_items": [(1, {"name": T + 20, "describe_str": T + 21}), (2, {"name": T + 22})],
        "debate_guider_dialog_data": [(31, {"data": [{"text": T + 50, "entity_no": 9001, "time": 0}]})],
        "world_view_person_info": [(4, {"id": 4, "name": T + 80, "story": [41]})],
        "world_view_person_event": [(41, {"id": 41, "title": T + 81, "description": T + 82})],
    }


class ExtractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="wwm-wyciag-")
        cls.out = Path(cls.temp.name) / "index"
        cls.manifest = wyciag.zbuduj(FakeBaza(tables()), ZH, EN, cls.out, {"opis": "dane wymyślone"}, log=lambda _text: None)
        cls.indeks = indeks.wczytaj(cls.out)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_manifest_counts(self):
        numbers = self.manifest["liczby"]
        self.assertEqual(self.manifest["format"], "wwm-indeks-v2")
        self.assertEqual(numbers["scen"], 3)
        self.assertEqual(numbers["scen_bez_tekstu"], 2)
        self.assertEqual(numbers["kwestii"], 4)
        self.assertEqual(numbers["kwestii_zaleznych_od_plci_bohatera"], 2)
        self.assertEqual(numbers["id_tylko_zh_niewskazane_pominiete"], 1)
        self.assertEqual(numbers["tekstow_bez_wersji_zh"], 1)
        self.assertEqual(numbers["zadan"], 3)
        self.assertEqual(self.manifest["pokrycie"]["kwestii_bez_grupy_mowcy"], 0)

    def test_text_is_stored_once_per_source_text(self):
        sword = self.indeks.teksty[K("Miecz")]
        self.assertEqual(sword.n, 2)
        self.assertIn(sword.en, ("Sword", "Blade"))
        self.assertEqual(self.indeks.zrodlo(sword), ("stuff_items", "name", "1"))
        self.assertNotIn(K("tylko chiński, nikt nie wskazuje"), self.indeks.teksty)
        english_only = self.indeks.teksty[K("english only text")]
        self.assertTrue(english_only.z_en)
        self.assertEqual(self.indeks.en(K("english only text")), "english only text")

    def test_text_files_are_split_by_first_key_character(self):
        key = K("Miecz")
        lines = (self.out / f"teksty_{key[0]}.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertIn("Miecz", [json.loads(line).get("zh") for line in lines])

    def test_scene_has_cast_lines_place_and_links(self):
        scene = self.indeks.sceny[100]
        # nazwa mówcy: numer seryjny -> byt -> tabliczka
        self.assertEqual(scene["o"][0], ["kowal_roboczy", 3, 9001, K("Kowal"), K("Mistrz kuźni")])
        self.assertEqual(scene["e"][0], ["k", 0, K("kwestia kowala")])
        self.assertEqual(scene["e"][1], ["k", 1, K("kwestia gracza")])
        variants = sorted(tuple(element[2:]) for element in scene["e"][2:])
        self.assertEqual(
            variants,
            [(K("wersja bohatera"), 1, f"{T + 3:016x}"), (K("wersja bohatera"), 2, f"{T + 4:016x}")],
        )
        self.assertEqual(scene["m"], [7])
        self.assertEqual(scene["x"], [101])
        fields = {tuple(self.indeks.pola_dialogow[number][:2]) for number, _row in scene["r"]}
        self.assertIn(("tasks", "finish_dialogs"), fields)

    def test_variant_lines_keep_their_own_english(self):
        self.assertEqual(self.indeks.warianty[f"{T + 4:016x}"], {"id": f"{T + 4:016x}", "k": K("wersja bohatera"), "w": 2, "en": "female version"})

    def test_tasks_groups_choices_and_people(self):
        task = self.indeks.zadania[2]
        self.assertEqual(task["pre"], [1])
        self.assertEqual(task["dialogi"], {"rozmowa": [102], "zakonczenie": [101]})
        self.assertEqual(self.indeks.zadania[1]["nazwa"], K("Pierwsze zadanie"))
        self.assertEqual(self.indeks.grupy[5]["zadania"], [1, 2, 3])
        choice = self.indeks.wybory["9_1"]
        self.assertEqual([item["tekst"] for item in choice["wybory"]], [K("Tak"), K("Nie")])
        self.assertEqual(choice["wybory"][0]["dialogi"], [101])
        self.assertEqual(self.indeks.encyklopedia[4]["historie"], [[K("Historia"), K("Dawno temu…")]])
        self.assertEqual(self.indeks.postacie[700], {"no": 700, "n": K("Kowal"), "t": K("Mistrz kuźni")})
        self.assertEqual(self.indeks.miejsca[7]["nazwa"], K("Kuźnia"))
        self.assertEqual(self.indeks.dymki["31"], [[9001, K("dymek pierwszy"), K("Kowal"), 7]])

    def test_every_key_used_by_scenes_exists_in_texts(self):
        for scene in self.indeks.sceny.values():
            for element in scene["e"]:
                self.assertIn(element[2], self.indeks.teksty)

    def test_files_match_manifest_and_tampering_is_detected(self):
        self.assertEqual(indeks.sprawdz_pliki(self.out), [])
        with tempfile.TemporaryDirectory(prefix="wwm-wyciag-") as temp:
            copy = Path(temp) / "index"
            copy.mkdir()
            for path in self.out.iterdir():
                (copy / path.name).write_bytes(path.read_bytes())
            with (copy / "zadania.jsonl").open("a", encoding="utf-8") as handle:
                handle.write("{}\n")
            self.assertEqual(indeks.sprawdz_pliki(copy), ["zadania.jsonl: inna zawartość niż w manifeście"])

    def test_rebuild_is_byte_identical(self):
        with tempfile.TemporaryDirectory(prefix="wwm-wyciag-") as temp:
            again = Path(temp) / "index"
            wyciag.zbuduj(FakeBaza(tables()), ZH, EN, again, {"opis": "dane wymyślone"}, log=lambda _text: None)
            for path in sorted(self.out.iterdir()):
                self.assertEqual(path.read_bytes(), (again / path.name).read_bytes(), path.name)

    def test_loader_rejects_other_formats(self):
        with tempfile.TemporaryDirectory(prefix="wwm-wyciag-") as temp:
            (Path(temp) / "manifest.json").write_text('{"format": "wwm-indeks-v1"}', encoding="utf-8")
            with self.assertRaises(indeks.IndeksError):
                indeks.wczytaj(temp)
            with self.assertRaises(indeks.IndeksError):
                indeks.wczytaj(Path(temp) / "nie_ma")


if __name__ == "__main__":
    unittest.main()
