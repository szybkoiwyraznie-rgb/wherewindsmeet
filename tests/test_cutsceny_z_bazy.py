"""Wiązanie napis ↔ cutscena z bazy gry (`tools/cutsceny_z_bazy.py`).

Dane w testach są wymyślone: podajemy funkcjom gotowe słowniki (tak, jakby przyszły
z bazy), żeby sprawdzić samą regułę: numer cutsceny bierzemy **tylko** z kodu filmu
w nazwie nagrania (`vo_…_cs_<kod>_<numer>` ↔ `cutscenes.cine_name` = `sq001_<kod>`).
Druga klasa sprawdza, że `chronologia` kładzie cutscenę w krainie wskazanej przez
jej własną przestrzeń, gdy scena-kotwica mapy nie ma.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools import chronologia, cutsceny_z_bazy


class KodFilmu(unittest.TestCase):
    def test_kod_cine_z_prefiksem_zadania(self):
        self.assertEqual(cutsceny_z_bazy.kod_cine("sq001_zlxl"), "zlxl")
        self.assertEqual(cutsceny_z_bazy.kod_cine("sq001_zlxl_mobile"), "zlxl_mobile")
        self.assertEqual(cutsceny_z_bazy.kod_cine("huafang"), "huafang")
        self.assertIsNone(cutsceny_z_bazy.kod_cine(None))
        self.assertIsNone(cutsceny_z_bazy.kod_cine(""))

    def test_kod_z_nagrania_bierze_najdluzszy_kandydat(self):
        kody = {"zlxl": {30161}, "zlxl_mobile": {30663}}
        self.assertEqual(cutsceny_z_bazy.kod_z_nagrania("vo_sm_sxdm4_cs_zlxl_hx_02", kody), "zlxl")
        self.assertEqual(cutsceny_z_bazy.kod_z_nagrania("vo_sm_x_cs_zlxl_mobile_hx_02", kody),
                         "zlxl_mobile")
        self.assertIsNone(cutsceny_z_bazy.kod_z_nagrania("vo_ss_yypsm8p2_npc_82", kody))


class WiazanieNapisow(unittest.TestCase):
    def setUp(self):
        self.kody = {"zlxl": {30161}, "tsbd": {30707}, "wielokrotny": {1, 2}}
        self.pula = {
            "老大 你快醒醒啊": [(591149, "klucz1")],
            "不是说好一起去将军祠吗": [(591150, "klucz2")],
            "kwestia bez nagrania": [(591151, "klucz3")],
            "kod niejednoznaczny": [(591152, "klucz4")],
        }
        self.nagrania = {
            "老大 你快醒醒啊": {"vo_sm_sxdm4_cs_zlxl_hx_02"},
            "不是说好一起去将军祠吗": {"vo_sm_sxdm4_cs_tsbd_hx_05"},
            "kod niejednoznaczny": {"vo_sm_sxdm4_cs_wielokrotny_hx_01"},
        }

    def test_wiaze_po_kodzie_filmu(self):
        napisy, statystyka = cutsceny_z_bazy.wiaz_napisy(self.pula, self.nagrania, self.kody)
        self.assertEqual([(w["no"], w["wiersz"], w["k"], w["dowod"]) for w in napisy],
                         [(30161, 591149, "klucz1", "vo:zlxl"),
                          (30707, 591150, "klucz2", "vo:tsbd")])
        self.assertEqual(statystyka["wiazan"], 2)
        # bez nagrania: 1 napis, niejednoznaczny kod: 1 napis
        self.assertEqual(statystyka["bez_nagrania"], 1)
        self.assertEqual(statystyka["bez_kodu_filmu"], 1)

    def test_kod_wskazujacy_wiele_cutscen_jest_odrzucany(self):
        napisy, statystyka = cutsceny_z_bazy.wiaz_napisy(
            {"kod niejednoznaczny": [(591152, "klucz4")]}, self.nagrania, self.kody)
        self.assertEqual(napisy, [])
        self.assertEqual(statystyka["bez_kodu_filmu"], 1)


class MetadaneCutscen(unittest.TestCase):
    def test_bierze_przestrzen_i_czas(self):
        wiersze = [
            (30161, {"no": 30161, "cutscene_space_no": 501, "cine_duration": 78.664,
                     "cine_name": "sq001_zlxl"}),
            (30083, {"no": 30083, "cutscene_space_no": 255, "cine_duration": 0}),
            (1, {"no": 1}),
        ]
        meta = cutsceny_z_bazy.metadane(wiersze, {30161: {"fenbao": "qinghe"}})
        self.assertEqual(meta, [{"no": 30161, "przestrzen": 501, "czas_s": 78.7,
                                 "film": "sq001_zlxl", "pakiet": "qinghe"}])

    def test_bez_przestrzeni_nie_zgadujemy(self):
        meta = cutsceny_z_bazy.metadane([(2, {"no": 2, "cutscene_space_no": 0})])
        self.assertEqual(meta, [])


class ChronologiaCzytaWiazanie(unittest.TestCase):
    def test_plik_wiazania_jest_czytany(self):
        with tempfile.TemporaryDirectory() as tmp:
            katalog = Path(tmp)
            (katalog / "cutsceny_napisy.jsonl").write_text(
                json.dumps({"no": 30161, "wiersz": 591141, "k": "klucz1"}) + "\n" +
                json.dumps({"no": 30161, "wiersz": 591149, "k": "klucz2"}) + "\n",
                encoding="utf-8")
            mapa = chronologia._napisy_z_bazy(katalog)
            self.assertEqual(mapa, {30161: ["klucz1", "klucz2"]})

    def test_brak_pliku_to_puste_wiazanie(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(chronologia._napisy_z_bazy(Path(tmp)), {})


class ChronologiaCzytaPrzestrzen(unittest.TestCase):
    def test_przestrzen_cutsceny_z_meta(self):
        with tempfile.TemporaryDirectory() as tmp:
            katalog = Path(tmp)
            (katalog / "cutsceny_meta.jsonl").write_text(
                json.dumps({"no": 30161, "przestrzen": 501, "czas_s": 78.7}) + "\n" +
                json.dumps({"no": 30189, "film": "sq005_znwm"}) + "\n",
                encoding="utf-8")
            self.assertEqual(chronologia._przestrzen_cutscen(katalog), {30161: 501})

    def test_brak_pliku_to_pusta_mapa(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(chronologia._przestrzen_cutscen(Path(tmp)), {})


if __name__ == "__main__":
    unittest.main()
