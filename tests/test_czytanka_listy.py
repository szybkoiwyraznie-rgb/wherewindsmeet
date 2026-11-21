from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from tools import czytanka_czysta as cz


class _Tekst:
    def __init__(self, wiersz, zh, en=""):
        self.w = wiersz
        self.zrodlo = zh
        self.en = en


class _Indeks:
    zrodla = [
        ["tasks_envelop_data", "text", 2],   # 0
        ["tasks_envelop_data", "to", 2],     # 1
        ["tasks_envelop_data", "from", 1],   # 2
        ["text_msg", "content", 2],          # 3
    ]

    def __init__(self):
        self.teksty = {
            "to5": _Tekst((1, "5"), "月日，魏某白，江无浪足下", "From Wei to Jiang"),
            "text5": _Tekst((0, "5"),
                            "自足下隐神仙渡至于今。\\v有门人田英偶得一物。",
                            "Since you settled.\\vTian Ying found a thing."),
            "to9": _Tekst((1, "9"), "一张欠条", "IOU"),
            "text9": _Tekst((0, "9"), "还钱。", "Pay up."),
            "sc1": _Tekst((3, "1"), "是给江叔的信？“魏某白”，一个姓魏的写的。",
                          "A letter for uncle Jiang? “Wei writes”."),
            "sc2": _Tekst((3, "2"), "田英？", "Tian Ying?"),
        }
        self.sceny = {
            4700002: {"d": 4700002, "e": [["k", 0, "sc1"]]},
            4700003: {"d": 4700003, "e": [["k", 0, "sc2"]]},
        }


class TestCzystyFormanty(unittest.TestCase):
    def test_v_i_kolory_znikaja(self):
        self.assertEqual(
            cz._czysty("A\\vB #Yżółty#E $T(2026) $N"),
            "A B żółty Youxia",
        )

    def test_akapity_na_v(self):
        self.assertEqual(
            cz._akapity("Pierwszy.\\vDrugi #Mlist#E."),
            ["Pierwszy.", "Drugi list."],
        )


class TestKartyListow(unittest.TestCase):
    def test_tytul_z_trescia_razem(self):
        ix = _Indeks()
        listy = cz._wczytaj_listy(ix)
        self.assertIn("5", listy)
        pl = {"to5": "Z Wei — do Jiang Wulanga",
              "text5": "Odkąd osiadłeś.\\vTian Ying zdobył przedmiot."}
        surowe = dict(pl)
        karta = cz._karta_listu(listy["5"], pl, surowe, ix)
        tekst = "\n".join(karta)
        self.assertIn("## List: Z Wei — do Jiang Wulanga", tekst)
        self.assertIn("Odkąd osiadłeś.", tekst)
        self.assertIn("Tian Ying zdobył przedmiot.", tekst)
        self.assertIn(
            "## List: Z Wei — do Jiang Wulanga\nOdkąd osiadłeś.\nTian Ying zdobył przedmiot.",
            tekst,
        )
        self.assertNotIn("\n\n", tekst)
        self.assertNotIn("\\v", tekst)
        # tytuł i treść nie są osobnymi hasłami
        self.assertNotIn("**Z Wei", tekst)

    def test_list_po_scenie_z_grafu_openui(self):
        ix = _Indeks()
        listy = cz._wczytaj_listy(ix)
        katalog = tempfile.TemporaryDirectory()
        mpk = Path(katalog.name, "mpk")
        mpk.mkdir()
        (mpk / "listy_w_grafie.jsonl").write_text(
            json.dumps({
                "file_id": "3dd2fe816e69782d",
                "no": 5,
                "po": 4700002,
                "przed": 4700003,
                "sciezka": "Storyline/client/dialogs/hjt/sxd_xiaowushuxin.etsb",
            }, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        przy = cz._przypisz_listy_do_scen(ix, listy, katalog.name)
        self.assertEqual(przy.get(4700002), ["5"])
        self.assertNotIn(4700003, przy)
        katalog.cleanup()

    def test_bez_pola_po_zostaje_w_02(self):
        ix = _Indeks()
        listy = cz._wczytaj_listy(ix)
        katalog = tempfile.TemporaryDirectory()
        mpk = Path(katalog.name, "mpk")
        mpk.mkdir()
        # graf otwiera list, ale bez dialogu poprzedzającego — nie zgadujemy
        (mpk / "listy_w_grafie.jsonl").write_text(
            json.dumps({"file_id": "abc", "no": 5}, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        przy = cz._przypisz_listy_do_scen(ix, listy, katalog.name)
        self.assertEqual(przy, {})
        katalog.cleanup()

    def test_cytat_tytulu_w_dialogu_nie_wystarcza(self):
        ix = _Indeks()
        listy = cz._wczytaj_listy(ix)
        przy = cz._przypisz_listy_do_scen(ix, listy, None)
        self.assertEqual(przy, {})

    def test_wstawienie_miedzy_scenami(self):
        ix = _Indeks()
        listy = cz._wczytaj_listy(ix)
        pl = {"to5": "Z Wei — do Jiang Wulanga",
              "text5": "Treść akapitu.",
              "sc1": "List do wuja Jianga?",
              "sc2": "Wuj Jiang ma odszukać Tian Ying?"}
        jednostki = [
            cz.Jednostka("scena", "Scena 4700002", "# Yannan",
                         [("Youxia", "sc1")], numer=4700002),
            cz.Jednostka("scena", "Scena 4700003", "# Yannan",
                         [("Youxia", "sc2")], numer=4700003),
        ]
        stat = {"jednostek": 0, "linii": 0, "pominiete": 0, "bez_przekladu": 0}
        tresc, uzyte, _ = cz._plik_scen(
            jednostki, pl, "wszystko", stat, ix,
            listy=listy, listy_przy={4700002: ["5"]}, surowe=pl)
        tekst = "\n".join(tresc)
        i2 = tekst.index("## Scena 4700002")
        il = tekst.index("## List: Z Wei — do Jiang Wulanga")
        i3 = tekst.index("## Scena 4700003")
        self.assertLess(i2, il)
        self.assertLess(il, i3)
        self.assertIn("text5", uzyte)
        self.assertIn("to5", uzyte)


if __name__ == "__main__":
    unittest.main()
