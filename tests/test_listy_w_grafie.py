from __future__ import annotations

import json
import unittest
from pathlib import Path

from tools.listy_w_grafie import parsuj_graf

ROOT = Path(__file__).resolve().parent.parent


def _wezel(typ, data=None, connect=None, value=None):
    w = {"Type": typ, "Data": data or {}, "ConnectData": connect or {}}
    if value is not None:
        w["Value"] = value
    return w


def _krawedz(src, dst, src_port="__out__", dst_port="__in__"):
    return {"srcPortName": src_port, "dstPortName": dst_port,
            "srcNodeID": src, "dstNodeID": dst}


class TestParsujGrafKoperty(unittest.TestCase):
    def test_openui_miedzy_dwoma_dialogami(self):
        # Start → dialog 4700002 → dict(no=5) → OpenUI → close → dialog 4700003 → End
        graf = {"Storyline": {"NodeBuffer": [
            _wezel("OpenUIWithInputNode",
                   {"ui_path": "task.task_envelope_window.TaskEnvelopWindow"},
                   {"ui_guid": [_krawedz(1, 2, "ui_guid", "ui_guid")],
                    "__out__": [_krawedz(1, 2)]}),
            _wezel("ListenCloseUIByGuidNode", {},
                   {"__out__": [_krawedz(2, 9)]}),
            _wezel("EndEvent"),
            _wezel("IntInputParameterNode", value=5,
                   connect={"__out__": [_krawedz(4, 10, "__out__", "value_0")]}),
            _wezel("StrInputParameterNode", value="no",
                   connect={"__out__": [_krawedz(5, 10, "__out__", "key_0")]}),
            _wezel("EndEvent"),
            _wezel("StorylineDialogsPlayNode",
                   {"dialogs_no": 4700002, "block": True},
                   {"__out__": [_krawedz(7, 10)]}),
            _wezel("StartEvent", {},
                   {"__out__": [_krawedz(8, 7)]}),
            _wezel("StorylineDialogsPlayNode",
                   {"dialogs_no": 4700003, "block": True},
                   {"__out__": [_krawedz(9, 3)]}),
            _wezel("CommonMakeDictNode", {},
                   {"dict": [_krawedz(10, 1, "dict", "ui_kwargs")],
                    "__out__": [_krawedz(10, 1)]}),
        ]}}
        wiersze = parsuj_graf(graf, "3dd2fe816e69782d")
        self.assertEqual(len(wiersze), 1)
        self.assertEqual(wiersze[0]["no"], 5)
        self.assertEqual(wiersze[0]["po"], 4700002)
        self.assertEqual(wiersze[0]["przed"], 4700003)

    def test_openui_bez_dialogu_nie_ma_po(self):
        graf = {"Storyline": {"NodeBuffer": [
            _wezel("StartEvent", {}, {"__out__": [_krawedz(1, 4)]}),
            _wezel("StrInputParameterNode", value="no",
                   connect={"__out__": [_krawedz(2, 4, "__out__", "key_0")]}),
            _wezel("IntInputParameterNode", value=750,
                   connect={"__out__": [_krawedz(3, 4, "__out__", "value_0")]}),
            _wezel("CommonMakeDictNode", {},
                   {"dict": [_krawedz(4, 5, "dict", "ui_kwargs")],
                    "__out__": [_krawedz(4, 5)]}),
            _wezel("OpenUINode",
                   {"ui_path": "task.task_envelope_window.TaskEnvelopWindow"},
                   {"__out__": [_krawedz(5, 6)]}),
            _wezel("EndEvent"),
        ]}}
        wiersze = parsuj_graf(graf)
        self.assertEqual(len(wiersze), 1)
        self.assertEqual(wiersze[0]["no"], 750)
        self.assertNotIn("po", wiersze[0])
        self.assertNotIn("przed", wiersze[0])


class TestIndeksListyWGrafie(unittest.TestCase):
    def test_wei_po_4700002_przed_4700003(self):
        plik = ROOT / "index" / "mpk" / "listy_w_grafie.jsonl"
        self.assertTrue(plik.is_file(), plik)
        wiersze = [json.loads(l) for l in plik.read_text(encoding="utf-8").splitlines() if l.strip()]
        traf = [w for w in wiersze if w.get("no") == 5 and w.get("po") == 4700002]
        self.assertEqual(len(traf), 1, traf)
        self.assertEqual(traf[0].get("przed"), 4700003)
        self.assertTrue(any(w.get("po") for w in wiersze))


if __name__ == "__main__":
    unittest.main()
