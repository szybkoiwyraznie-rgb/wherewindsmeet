#!/usr/bin/env python3
"""POI → scena przez skrypty Storyline (`interact_storyline` → `.etsb`).

Krzyżówka dwóch indeksów (bez danych gry, bez `local/`):
  index/poi.jsonl               — POI z `active_interact_way` (id, dialog,
                                  `interact_storyline` = ścieżka klienta),
  index/mpk/etsb_storyline.jsonl — rozwiązane grafy `Storyline/<ścieżka>.etsb`
                                  z przebiegu skanera v7 (sceny/cutsceny/skrypty).

Wynik: index/mpk/poi_storyline_sceny.jsonl — po jednym wierszu na POI
z `interact_storyline`:
  {"poi": id, "storyline": "client/...", "status": "sceny|bez_scen|nierozwiazany",
   "sceny": [...], "cutsceny": [...], "sceny_posrednio": [...], "przez": [...]}

`sceny` — grane wprost przez graf skryptu; `sceny_posrednio` — grane przez
skrypty zagnieżdżone (`ClientRunStorylineNode`, domknięcie przechodnie,
odporne na cykle). Benchmark: POI 200046001 (Dragon Pattern Mark)
→ client/dialogs/hjt/sxd_longwenbiaoji.etsb → scena 4700001.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _stem(sciezka: str) -> str:
    s = sciezka
    if s.endswith((".ets", ".etsb")):
        s = s.rsplit(".", 1)[0]
    return s


def wczytaj_etsb() -> dict[str, dict]:
    grafy: dict[str, dict] = {}
    with open(ROOT / "index" / "mpk" / "etsb_storyline.jsonl", encoding="utf-8") as fh:
        for line in fh:
            d = json.loads(line)
            stem = _stem(d["sciezka"][len("Storyline/"):])
            grafy[stem] = d
    return grafy


def domkniecie(stem: str, grafy: dict[str, dict]) -> tuple[list[int], list[str]]:
    """Sceny grane przez skrypty zagnieżdżone (bez scen wprost), ścieżka dojścia."""
    sceny: set[int] = set()
    przez: list[str] = []
    widziane = {stem}
    kolejka = [s for s in grafy.get(stem, {}).get("skrypty", [])]
    while kolejka:
        nast = _stem(kolejka.pop())
        if nast in widziane:
            continue
        widziane.add(nast)
        g = grafy.get(nast)
        if not g:
            continue
        przez.append(nast)
        sceny.update(g.get("sceny", []))
        kolejka.extend(g.get("skrypty", []))
    return sorted(sceny), przez


def main() -> int:
    grafy = wczytaj_etsb()
    wiersze = []
    liczniki = {"sceny": 0, "bez_scen": 0, "nierozwiazany": 0}
    with open(ROOT / "index" / "poi.jsonl", encoding="utf-8") as fh:
        for line in fh:
            p = json.loads(line)
            storyline = p.get("storyline") or ""
            if not storyline:
                continue
            stem = _stem(storyline)
            g = grafy.get(stem)
            w = {"poi": p["id"], "storyline": storyline}
            if g is None:
                w["status"] = "nierozwiazany"
            else:
                w["file_id"] = g["file_id"]
                sceny = g.get("sceny", [])
                cutsceny = g.get("cutsceny", [])
                posrednio, przez = domkniecie(stem, grafy)
                posrednio = [s for s in posrednio if s not in set(sceny)]
                if sceny:
                    w["sceny"] = sceny
                if cutsceny:
                    w["cutsceny"] = cutsceny
                if posrednio:
                    w["sceny_posrednio"] = posrednio
                    w["przez"] = przez
                w["status"] = "sceny" if (sceny or posrednio) else "bez_scen"
            liczniki[w["status"]] += 1
            wiersze.append(w)

    out = ROOT / "index" / "mpk" / "poi_storyline_sceny.jsonl"
    with open(out, "w", encoding="utf-8") as fh:
        for w in wiersze:
            fh.write(json.dumps(w, ensure_ascii=False, sort_keys=True) + "\n")
    print(json.dumps({"wierszy": len(wiersze), **liczniki,
                      "plik": str(out.relative_to(ROOT))}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
