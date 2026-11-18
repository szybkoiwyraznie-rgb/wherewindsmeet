#!/usr/bin/env python3
"""Sceny ambientowe przypięte do kitów w świecie gry.

Mechanizm (udowodniony na benchmarku 4700037/4700041, patrz
docs/EXPERIMENT_LOG.md 2026-11-18 (6)): tabele `spaces.<s>.spawn_kit_sid_no`
mapują numer sceny (kit_serial_id) na numery kitów rozmieszczonych
w przestrzeni; `spaces.<s>.spawn_kit` niesie pozycję kitu. NPC ambientowy
(drzewo zachowań `u_common_qifen`) wchodzi w kit i gra scenę o numerze
seryjnym kitu, gdy gracz jest w pobliżu.

Wyjście: index/mpk/sceny_ambient_kity.jsonl —
  {"scena": nr, "space": "s501", "kit_no": …, "kit_pos_id": …,
   "pozycja": [x,y,z] | null}

Wymaga bazy gry w `local/dane` (poza Gitem).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import baza_gry  # noqa: E402

KATALOGI = [
    ROOT / "local" / "dane" / "LocalData" / "Patch" / "HD" / "oversea",
    ROOT / "local" / "dane" / "Package" / "HD" / "oversea",
]


def main() -> int:
    for k in KATALOGI:
        if not k.is_dir():
            print(f"BŁĄD: brak katalogu bazy {k} — pobierz paczki do local/dane.")
            return 2
    baza = baza_gry.Baza([str(k) for k in KATALOGI])

    wzor = re.compile(r"^spaces\.(s\d+)\.spawn_kit_sid_no$")
    przestrzenie = {}
    for nazwa in baza.tabele:
        m = wzor.match(nazwa)
        if m:
            przestrzenie[m.group(1)] = nazwa

    wiersze = []
    for space, tab_sid in sorted(przestrzenie.items()):
        # pozycje kitów: spawn_kit ma id→(kit_pos, kit_serial_id);
        # spawn_kit_id2no mapuje kit_pos_id→kit_no
        pozycje = {}   # kit_pos_id -> pozycja
        id2no = {}     # kit_pos_id -> kit_no
        tab_spawn = f"spaces.{space}.spawn_kit"
        tab_id2no = f"spaces.{space}.spawn_kit_id2no"
        if tab_spawn in baza.tabele:
            for k, v in baza.wiersze(tab_spawn):
                d = baza_gry.do_json(v)
                if isinstance(d, dict) and "kit_pos" in d:
                    pozycje[k] = [round(float(x), 2) for x in d["kit_pos"]]
        if tab_id2no in baza.tabele:
            for k, v in baza.wiersze(tab_id2no):
                no = baza_gry.do_json(v)
                if isinstance(no, int):
                    id2no[k] = no
        no2id = {no: pid for pid, no in id2no.items()}

        for scena, v in baza.wiersze(tab_sid):
            kity = baza_gry.do_json(v)
            if not isinstance(scena, int) or not isinstance(kity, list):
                continue
            for kit_no in kity:
                if not isinstance(kit_no, int):
                    continue
                pos_id = no2id.get(kit_no)
                wiersze.append({
                    "scena": scena,
                    "space": space,
                    "kit_no": kit_no,
                    "kit_pos_id": pos_id,
                    "pozycja": pozycje.get(pos_id),
                })

    wiersze.sort(key=lambda w: (w["scena"], w["space"], w["kit_no"]))
    out = ROOT / "index" / "mpk" / "sceny_ambient_kity.jsonl"
    with open(out, "w", encoding="utf-8") as fh:
        for w in wiersze:
            fh.write(json.dumps(w, ensure_ascii=False) + "\n")
    sceny = {w["scena"] for w in wiersze}
    print(json.dumps({"wierszy": len(wiersze), "scen": len(sceny),
                      "przestrzeni": len(przestrzenie),
                      "plik": str(out.relative_to(ROOT))}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
