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
            "Soczyste ochłapy mięsa. Zastosowań wiele.",
            "Mięso drobnych zwierząt.",
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

    def test_krotki_opis_przed_tresc(self):
        a = pole("s", "story_describe_str")
        b = pole("d", "describe_str")
        self.assertLess(_waga_pola(b), _waga_pola(a))
        self.assertLess(_waga_pola(pole("e", "describe")), _waga_pola(a))
        self.assertLess(_waga_pola(pole("l", "locate_describe")), _waga_pola(b))


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

    def test_boss_i_encyklopedia_jedna_karta(self):
        class T:
            def __init__(self, w, zh="", en=""):
                self.w = w
                self.zrodlo = zh
                self.en = en

        class Ix:
            def __init__(self):
                self.teksty = {
                    "namek": T((478, "1"), zh="皮影·幕启", en="Puppeteer - Overture"),
                    "opisk": T((2804, "842037", "namek"),
                               zh="绳文绳武兄弟", en="The brothers Sheng Wen"),
                }
            def zrodlo(self, t):
                if t.w[0] == 478:
                    return ("baixiao_world_boss_data", "[].boss_name", t.w[1])
                return ("manual_items", "describe", t.w[1])

        linie = _reszta(Ix(), {
            "namek": "Teatr cieni: kurtyna w górę",
            "opisk": "Bracia Sheng Wen i Sheng Wu od dziecka utrzymywali się z teatru cieni.",
        }, set(), {"reszta": 0})
        self.assertEqual(linie.count("**Teatr cieni: kurtyna w górę**"), 1)
        karta = linie[linie.index("**Teatr cieni: kurtyna w górę**"):]
        koniec = next((i for i, l in enumerate(karta) if l.startswith("#")), len(karta))
        karta = [l for l in karta[:koniec] if l]
        self.assertIn("Bracia Sheng Wen i Sheng Wu od dziecka utrzymywali się z teatru cieni.", karta)

    def test_nazwa_bez_pl_nie_jest_angielska(self):
        from tools.czytanka_czysta import _nazwa_klucza

        class T:
            def __init__(self):
                self.zrodlo = "木箭"
                self.en = "Wooden Arrow"
                self.w = (445, "102025")

        class Ix:
            teksty = {"k": T()}

        nazwa = _nazwa_klucza(Ix(), "k", {})
        self.assertNotEqual(nazwa, "Wooden Arrow")
        self.assertTrue(nazwa)


class TestManualUnlockStuff(unittest.TestCase):
    """`manual_items.unlock_stuff` nazywa sierotę encyklopedii przedmiotem z gry."""

    def _ix(self, wiersze):
        class T:
            def __init__(self, w, zh=""):
                self.w = w
                self.zrodlo = zh
                self.en = ""

        class Ix:
            def __init__(self):
                self.teksty = {k: T(*v) for k, v in wiersze.items()}
                self.mapa = {}

            def zrodlo(self, t):
                return self.mapa.get(id(t))

        return Ix()

    def test_412006_dostaje_nazwe_strzaly(self):
        ix = self._ix({
            "strzala": ((445, "102025"), "mujian"),
            "opis": ((2804, "412006"), "opis strzaly"),
        })
        ix.mapa = {
            id(ix.teksty["strzala"]): ("arrows", "arrow_name", "102025"),
            id(ix.teksty["opis"]): ("manual_items", "describe", "412006"),
        }
        linie = _reszta(ix, {
            "strzala": "Drewniana strzała",
            "opis": "Strzały strugane z drewna.",
        }, set(), {"reszta": 0}, manual_unlock={"412006": "102025"})
        self.assertEqual(linie.count("**Drewniana strzała**"), 1)
        karta = linie[linie.index("**Drewniana strzała**"):]
        koniec = next((i for i, l in enumerate(karta) if l.startswith("#")), len(karta))
        karta = [l for l in karta[:koniec] if l]
        self.assertIn("Strzały strugane z drewna.", karta)

    def test_414049_dostaje_nazwe_sciagna(self):
        ix = self._ix({
            "sciagno": ((3283, "2200015"), "niubeijin"),
            "krotki": ((3284, "2200015", "sciagno"), "krotki opis"),
            "dlugi": ((2804, "414049"), "dlugi opis"),
        })
        ix.mapa = {
            id(ix.teksty["sciagno"]): ("oversea_home_entry_bag_search", "name", "2200015"),
            id(ix.teksty["krotki"]): ("oversea_home_entry_bag_search", "describe_str", "2200015"),
            id(ix.teksty["dlugi"]): ("manual_items", "describe", "414049"),
        }
        linie = _reszta(ix, {
            "sciagno": "Ścięgno wołowe",
            "krotki": "Doskonałe ścięgno wołowe, służy do wytwarzania łuków.",
            "dlugi": "Jeden z sześciu materiałów do wyrobu łuku.",
        }, set(), {"reszta": 0}, manual_unlock={"414049": "2200015"})
        self.assertGreaterEqual(linie.count("**Ścięgno wołowe**"), 1)
        self.assertTrue(any(
            "Jeden z sześciu materiałów do wyrobu łuku." in linie[i:i + 6]
            for i, l in enumerate(linie) if l == "**Ścięgno wołowe**"
        ))

    def test_bez_mapy_nie_skleja(self):
        ix = self._ix({
            "strzala": ((445, "102025"), "mujian"),
            "opis": ((2804, "412006"), "opis strzaly"),
        })
        ix.mapa = {
            id(ix.teksty["strzala"]): ("arrows", "arrow_name", "102025"),
            id(ix.teksty["opis"]): ("manual_items", "describe", "412006"),
        }
        linie = _reszta(ix, {
            "strzala": "Drewniana strzała",
            "opis": "Strzały strugane z drewna.",
        }, set(), {"reszta": 0}, manual_unlock={})
        self.assertNotIn("**Drewniana strzała**", linie)
        self.assertIn("Strzały strugane z drewna.", linie)

    def test_nazwa_z_etykiety_wiersza_gdy_hash_w_innej_tabeli(self):
        """540002: `bag_search.name` to ten sam hash co składnik kuchni — nazwa z w[2]."""
        ix = self._ix({
            "jajko": ((688, "2"), "dan"),
            "opis_bag": ((3284, "540002", "jajko"), "ptasie jajo"),
            "ency": ((2804, "122008"), "opis jajka"),
        })
        ix.mapa = {
            id(ix.teksty["jajko"]): ("canteen_cook_ingredient", "ingredient_name", "2"),
            id(ix.teksty["opis_bag"]): ("oversea_home_entry_bag_search", "describe_str", "540002"),
            id(ix.teksty["ency"]): ("manual_items", "describe", "122008"),
        }
        linie = _reszta(ix, {
            "jajko": "Jajko",
            "opis_bag": "Jaja ptaków, żółwi lub węży.",
            "ency": "Ptasie jajo o prostym wzorze.",
        }, set(), {"reszta": 0}, manual_unlock={"122008": "540002"})
        self.assertGreaterEqual(linie.count("**Jajko**"), 1)
        self.assertTrue(any(
            "Ptasie jajo o prostym wzorze." in linie[i:i + 8]
            for i, l in enumerate(linie) if l == "**Jajko**"
        ))

    def test_encyklopedia_i_przedmiot_jedna_karta(self):
        """414037 → 540012: krótki opis encyklopedii i story przedmiotu razem."""
        ix = self._ix({
            "skora": ((3283, "540012"), "cumaopi"),
            "story": ((3286, "540012", "skora"), "story skory"),
            "ency": ((2804, "414037"), "opis encyklopedii"),
        })
        ix.mapa = {
            id(ix.teksty["skora"]): ("oversea_home_entry_bag_search", "name", "540012"),
            id(ix.teksty["story"]): ("oversea_home_entry_bag_search", "story_describe_str", "540012"),
            id(ix.teksty["ency"]): ("manual_items", "describe", "414037"),
        }
        linie = _reszta(ix, {
            "skora": "Gruba skóra z sierścią",
            "story": "Skóra z sierścią zwykłych dzikich zwierząt, szorstka; zdaje się mieć wiele zastosowań.",
            "ency": "Futra zwykłych dzikich zwierząt, o szorstkiej skórze, nadają się na materiał.",
        }, set(), {"reszta": 0}, manual_unlock={"414037": "540012"})
        self.assertEqual(linie.count("**Gruba skóra z sierścią**"), 1)
        i = linie.index("**Gruba skóra z sierścią**")
        karta = [l for l in linie[i:i + 6] if l and not l.startswith("#")]
        self.assertEqual(karta[:3], [
            "**Gruba skóra z sierścią**",
            "Futra zwykłych dzikich zwierząt, o szorstkiej skórze, nadają się na materiał.",
            "Skóra z sierścią zwykłych dzikich zwierząt, szorstka; zdaje się mieć wiele zastosowań.",
        ])

    def test_locate_wroga_z_mapy_kazdego_wiersza(self):
        """841003 dzieli locate z 841001 — mapa bowu→klucz, nie główne `w`."""
        ix = self._ix({
            "nazwa": ((1440, "96014"), "lulinmaozei"),
            "opis": ((2804, "841003", "nazwa"), "opis wroga"),
        })
        ix.mapa = {
            id(ix.teksty["nazwa"]): ("entity_billboard", "name", "96014"),
            id(ix.teksty["opis"]): ("manual_items", "describe", "841003"),
        }
        ix.teksty["lok"] = type(ix.teksty["nazwa"])((2810, "841001"), "lokacja zh")
        ix.mapa[id(ix.teksty["lok"])] = ("manual_items", "locate_describe", "841001")
        linie = _reszta(ix, {
            "nazwa": "Szkodnik z Zielonego Lasu",
            "opis": "Zbój z Zielonego Lasu grasujący po okolicach Qinghe.",
            "lok": "Zielne Bezdroża i Góra Ukrytego Księżyca, kryjówki i okolice",
        }, set(), {"reszta": 0}, manual_locate={"841003": "lok"})
        i = linie.index("**Szkodnik z Zielonego Lasu**")
        karta = [l for l in linie[i:i + 6] if l and not l.startswith("#")]
        self.assertEqual(karta[:3], [
            "**Szkodnik z Zielonego Lasu**",
            "Zielne Bezdroża i Góra Ukrytego Księżyca, kryjówki i okolice",
            "Zbój z Zielonego Lasu grasujący po okolicach Qinghe.",
        ])


if __name__ == "__main__":
    unittest.main()
