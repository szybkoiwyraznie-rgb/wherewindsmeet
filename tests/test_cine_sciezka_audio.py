"""Oś audio `.cine`: master, a gdy milczy — ujęcia-dzieci w jego kolejności."""

from __future__ import annotations

import unittest

from tools.cine_sciezka_audio import kwestie_z_cine, kwestie_z_ujec


def _wpis(t: str, sid: int) -> bytes:
    return f"{t}:{sid}:0:0;0".encode()


NAGRANIA = {
    7150838: {"audio": "vo_a", "zh": "此事……你我也只能多加小心。"},
    7150839: {"audio": "vo_b", "zh": "是广胡子他们！我的话本！我来了！"},
    7150730: {"audio": "vo_c", "zh": "喂，你小心点！"},
    7150417: {"audio": "vo_d", "zh": "不要慢！我要第一个买到话本！"},
    7151014: {"audio": "vo_master", "zh": "红线你好好走，别蹦！"},
}


class TestKwestieZUjec(unittest.TestCase):
    def test_master_z_kwestia_nie_bierze_dzieci(self):
        master = _wpis("3.399", 7151014)
        dziecko = _wpis("0.1", 7150838)
        k = kwestie_z_ujec(master, [dziecko], NAGRANIA)
        self.assertEqual([x["id"] for x in k], [7151014])

    def test_master_bez_tekstu_bierze_dzieci_po_kolei(self):
        # muzyka (brak w nagraniach) + ujęcia jak 30163
        master = _wpis("0.0", 3100018)
        s0010 = _wpis("0.133", 7150838) + b" " + _wpis("4.233", 7150839)
        s0020 = b"cisza"
        s0030 = _wpis("1.367", 7150730)
        s0070 = _wpis("0.148", 7150417)
        k = kwestie_z_ujec(master, [s0010, s0020, s0030, s0070], NAGRANIA)
        self.assertEqual([x["id"] for x in k], [7150838, 7150839, 7150730, 7150417])
        self.assertLess(k[0]["t"], k[1]["t"])
        self.assertLess(k[1]["t"], k[2]["t"])
        self.assertLess(k[2]["t"], k[3]["t"])

    def test_kwestie_z_cine_pominaja_muzyke(self):
        dane = _wpis("0.0", 3100018) + b" " + _wpis("1.0", 7150730)
        k = kwestie_z_cine(dane, NAGRANIA)
        self.assertEqual([x["id"] for x in k], [7150730])


if __name__ == "__main__":
    unittest.main()
