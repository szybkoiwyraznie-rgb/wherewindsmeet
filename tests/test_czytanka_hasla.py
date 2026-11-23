"""Karty haseł w 02: wielolinijkowe, kolejność kolumn, bez sklejania ` · `."""

from __future__ import annotations

import unittest

from tools.czytanka_czysta import (
    PoleHasla, _karta_hasla, _kategoria, _waga_pola, _reszta,
)


def pole(tekst, kolumna, wiersz="1", tabela="x"):
    return PoleHasla(tekst, tabela, kolumna, wiersz, "k")


class TestKartaHasla(unittest.TestCase):
    def test_przedmiot_tytul_potem_akapity(self):
        linie = _karta_hasla("Ochłapy mięsa", [
            pole("Mięso drobnych zwierząt.", "story_describe_str"),
            pole("Soczyste ochłapy mięsa. Zastosowań wiele.", "describe_str"),
        ])
        self.assertEqual(linie, [
            "**Ochłapy mięsa**",
            "Mięso drobnych zwierząt.",
            "Soczyste ochłapy mięsa. Zastosowań wiele.",
        ])
        self.assertNotIn("", linie)

    def test_quest_etapy_po_numerze_zadania(self):
        linie = _karta_hasla("Łucznictwo", [
            pole("Feng daruje sztukę.", "task_desc_str", "330006"),
            pole("Znajdź łucznika.", "task_target_str", "330002"),
            pole("Wiadomo już, czemu ptaki spadają.", "task_desc_str", "330002"),
            pole("Potrenuj łucznictwo.", "task_target_str", "330006"),
            pole("Użyj przedmiotu.", "task_target_str", "330003"),
        ])
        self.assertEqual([l for l in linie if l and not l.startswith("**")], [
            "Wiadomo już, czemu ptaki spadają.",
            "Znajdź łucznika.",
            "Użyj przedmiotu.",
            "Feng daruje sztukę.",
            "Potrenuj łucznictwo.",
        ])

    def test_quest_etapy_lancuchem_pre_post_nie_numerem(self):
        class _Ix:
            zadania = {
                500003: {"pre": [500002], "post": [500004]},
                500004: {"pre": [500003], "post": [500204]},
                500204: {"pre": [500004], "post": [250130]},
                250130: {"pre": [500204], "post": []},
            }
        linie = _karta_hasla("Niedźwiedzie zadanie", [
            pole("Wskazówki ula włączone", "task_target_str", "250130"),
            pole("Na pożegnanie Wędrowiec…", "task_desc_str", "250130"),
            pole("Podejdź do dziwnego przybysza", "task_target_str", "500003"),
            pole("Czerwona Nić już pomknęła naprzód…", "task_desc_str", "500003"),
            pole("Odpowiedz nieznajomemu", "task_target_str", "500004"),
            pole("Użyj tai chi i pokonaj niedźwiedzia", "task_target_str", "500204"),
        ], ix=_Ix())
        cialo = [l for l in linie if l and not l.startswith("**")]
        self.assertEqual(cialo[0], "Czerwona Nić już pomknęła naprzód…")
        self.assertEqual(cialo[1], "Podejdź do dziwnego przybysza")
        self.assertLess(cialo.index("Odpowiedz nieznajomemu"),
                        cialo.index("Użyj tai chi i pokonaj niedźwiedzia"))
        self.assertEqual(cialo[-1], "Wskazówki ula włączone")

    def test_kompendium_pomija_podpowiedz_questa_bez_lokalizacji(self):
        linie = _karta_hasla("Biały Ptak Strzela do Yi", [
            pole("Od Ruby wiesz, że w Qinghe…", "describe"),
            pole("Bezlitosna strzała omal cię nie zraniła.", "extra_describe_1"),
        ])
        self.assertIn("Od Ruby wiesz, że w Qinghe…", linie)
        self.assertNotIn("Bezlitosna strzała omal cię nie zraniła.", linie)

    def test_choroba_definicja_przed_cytatem(self):
        linie = _karta_hasla("Zarażenie Miazmatami", [
            pole("- Sui, Chao Yuanfang…", "shiyi_show_word_from"),
            pole("Zielonotrawiasta zgnilizna…", "shiyi_show_word"),
            pole("Miazmaty wchodzą w meridiały.", "description"),
        ])
        cialo = [l for l in linie if l and not l.startswith("**")]
        self.assertEqual(cialo, [
            "Miazmaty wchodzą w meridiały.",
            "Zielonotrawiasta zgnilizna…",
            "- Sui, Chao Yuanfang…",
        ])

    def test_manual_items_to_encyklopedia_nie_przedmiot(self):
        self.assertEqual(_kategoria("manual_items"),
                         "Encyklopedia, księgi i poszlaki")
        self.assertEqual(_kategoria("all_homeland_stuff_items"),
                         "Przedmioty, stroje i tytuły")


class TestWagaPola(unittest.TestCase):
    def test_desc_przed_target_tego_samego_zadania(self):
        a = pole("t", "task_target_str", "330002")
        b = pole("d", "task_desc_str", "330002")
        self.assertLess(_waga_pola(b), _waga_pola(a))

    def test_story_przed_describe(self):
        a = pole("s", "story_describe_str")
        b = pole("d", "describe_str")
        self.assertLess(_waga_pola(a), _waga_pola(b))


class _Tekst:
    def __init__(self, wiersz):
        self.w = wiersz
        self.zrodlo = ""
        self.en = ""


class _Ix:
    zrodla: list = []
    teksty: dict

    def __init__(self, teksty):
        self.teksty = teksty

    def zrodlo(self, tekst):
        return None


class TestLokalizacjaBowu(unittest.TestCase):
    """`bowu_no_to_story_no` kładzie backing_area aktu na kartę hasła."""

    def test_832009_dostaje_lokalizacje_901(self):
        nazwa = _Tekst((2803, "832009"))
        opis = _Tekst((2804, "832009", "namek"))
        miejsce = _Tekst((3954, "901", "aktywnosc"))
        ix = _Ix({
            "namek": nazwa,
            "opisk": opis,
            "04bc7e22e141a8db": miejsce,
        })
        ix.mapa = {
            id(nazwa): ("manual_items", "bowu_name"),
            id(opis): ("manual_items", "describe"),
            id(miejsce): ("region_story_act_data", "backing_area"),
        }
        ix.zrodlo = lambda t: ix.mapa.get(id(t))  # type: ignore[method-assign]
        pl = {
            "namek": "Biały Ptak Strzela do Yi",
            "opisk": "Od Ruby wiesz, że w Qinghe…",
            "04bc7e22e141a8db":
                "Zielne Bezdroża, na północny zachód od Bambusowej Chaty",
        }
        linie = _reszta(ix, pl, set(), {"reszta": 0},
                        bowu_story={"832009": ["901"]})
        karta = linie[linie.index("**Biały Ptak Strzela do Yi**"):]
        karta = karta[:karta.index("") if "" in karta else len(karta)]
        # sekcja kończy się pustą linią — weźmy do następnego #
        koniec = next((i for i, l in enumerate(karta) if l.startswith("#")), len(karta))
        karta = [l for l in karta[:koniec] if l]
        self.assertEqual(karta[0], "**Biały Ptak Strzela do Yi**")
        self.assertIn(
            "Zielne Bezdroża, na północny zachód od Bambusowej Chaty", karta)
        self.assertIn("Od Ruby wiesz, że w Qinghe…", karta)
        self.assertLess(
            karta.index("Zielne Bezdroża, na północny zachód od Bambusowej Chaty"),
            karta.index("Od Ruby wiesz, że w Qinghe…"),
        )


class TestResztaBezZrodla(unittest.TestCase):
    def test_napis_bez_tabeli_idzie_do_02(self):
        from tools.czytanka_czysta import _reszta

        ix = _Ix({"k1": _Tekst((1, "1"))})
        linie = _reszta(ix, {"k1": "Napisy przerywnika."}, set(), {"reszta": 0})
        self.assertIn("Napisy przerywnika.", linie)

    def test_tekst_bez_w_tez_idzie_do_02(self):
        from tools.czytanka_czysta import _reszta

        ix = _Ix({"feng": _Tekst(None)})
        linie = _reszta(ix, {"feng": "Feng mówi."}, set(), {"reszta": 0})
        self.assertIn("Feng mówi.", linie)

    def test_dwa_wiersze_tej_samej_nazwy_to_dwie_karty(self):
        class T:
            def __init__(self, w):
                self.w = w
                self.zrodlo = ""
                self.en = ""

        class Ix:
            teksty: dict
            def __init__(self):
                self.teksty = {
                    "n": T((1, "10")),
                    "a": T((2, "10", "n")),
                    "b": T((2, "11", "n")),
                }
            def zrodlo(self, t):
                if not t.w:
                    return None
                col = "name" if t.w[0] == 1 else "describe_str"
                return ("stuff_items", col, t.w[1])

        linie = _reszta(Ix(), {
            "n": "Zioła",
            "a": "Pospolite zioło lecznicze o wielu zastosowaniach.",
            "b": "Leki z pospolitych roślin.",
        }, set(), {"reszta": 0})
        self.assertEqual(linie.count("**Zioła**"), 2)
        i1 = linie.index("**Zioła**")
        i2 = linie.index("**Zioła**", i1 + 1)
        karta1 = linie[i1 + 1:i2]
        karta2 = linie[i2 + 1:]
        opisy = {karta1[0], next(l for l in karta2 if l and not l.startswith("#"))}
        self.assertEqual(opisy, {
            "Pospolite zioło lecznicze o wielu zastosowaniach.",
            "Leki z pospolitych roślin.",
        })


if __name__ == "__main__":
    unittest.main()
