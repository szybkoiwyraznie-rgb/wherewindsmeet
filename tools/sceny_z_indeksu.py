#!/usr/bin/env python3
"""Odtwarza sceny i listy tekstów z wersjonowanego indeksu `index/`.

To druga połowa obiegu: `tools/buduj_indeks.py` zapisuje indeks do repozytorium,
a ten skrypt czyta **wyłącznie repozytorium** — bez `local/`, bez plików z Dysku
i bez instalacji gry. Dzięki temu patcher i skrypty budujące paczki mają stałe
wejście, które nie znika przy czyszczeniu piaskownicy.

Wyniki:

    --sceny-wyj   JSONL w formacie `tools/timeline.py` (sceny z liniami), gotowy
                  dla `tools/build_scene_pack.py`
    --teksty-wyj  JSONL `{id, text}` dla `tools/build_translator_pack.py`; z
                  `--z-mapa` bierze dłuższą wersję tekstu z mapy źródłowej, czyli
                  tę z dopiskiem scenicznym w nawiasach

Użycie:
    python3 tools/sceny_z_indeksu.py --sceny-wyj local/sceny.jsonl
    python3 tools/sceny_z_indeksu.py --teksty-wyj local/teksty.jsonl --z-mapa
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

FORMAT = "wwm-indeks-v1"


def load_index(root: Path) -> tuple[list[dict], dict[str, str], dict[str, str], dict]:
    """Czyta manifest i shardy; zwraca sceny, teksty scen, teksty mapy, manifest.

    Tekst sceny (`tekst_zh`) to wersja **wyświetlana** w grze, z łamaniami wierszy.
    Tekst mapy (`tekst_mapa`) jest dłuższy — z dopiskiem scenicznym w nawiasach —
    i służy tylko jako źródło przekładu. Mieszać ich nie wolno: scena odtwarzana
    z indeksu musi być taka, jaką ją zapisał `tools/timeline.py`.
    """
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("format") != FORMAT:
        raise SystemExit(f"nieobsługiwany format indeksu: {manifest.get('format')!r}")

    texts: dict[str, str] = {}
    longer: dict[str, str] = {}
    for shard in manifest["shardy"]["teksty"]:
        path = root / shard["plik"]
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
        if len(rows) != shard["linie"]:
            raise SystemExit(f"{shard['plik']}: {len(rows)} linii, manifest mówi {shard['linie']}")
        for row in rows:
            key = row["text_id"]
            if key in texts:
                raise SystemExit(f"powtórzone text_id w shardach tekstów: {key}")
            texts[key] = row["tekst_zh"]
            if row.get("tekst_mapa"):
                longer[key] = row["tekst_mapa"]

    scenes: list[dict] = []
    for shard in manifest["shardy"]["sceny"]:
        path = root / shard["plik"]
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
        if len(rows) != shard["linie"]:
            raise SystemExit(f"{shard['plik']}: {len(rows)} linii, manifest mówi {shard['linie']}")
        scenes.extend(rows)
    return scenes, texts, longer, manifest


def expand(scene: dict, texts: dict[str, str]) -> dict:
    """Scena z indeksu -> format `tools/timeline.py`."""
    cast = {(row.get("mowca"), row.get("speaker_no")): row for row in scene.get("obsada") or []}
    lines = []
    for row in scene.get("linie") or []:
        key = row.get("text_id")
        if key not in texts:
            raise SystemExit(f"scena {scene['scena']}: brak tekstu dla {key}")
        actor = cast.get((row.get("mowca"), row.get("speaker_no"))) or {}
        lines.append(
            {
                "time": row.get("czas"),
                "order": row.get("kolejnosc"),
                "source_id": row.get("source_id"),
                "speaker": row.get("mowca"),
                "speaker_no": row.get("speaker_no"),
                "skeleton": actor.get("skeleton"),
                "text_id": key,
                "formatted_text": texts[key],
            }
        )
    return {
        "dialog_no": scene.get("dialog_no"),
        "project": scene.get("projekt"),
        "timeline_id": scene.get("timeline_id"),
        "start_time": scene.get("start_time"),
        "total_duration": scene.get("total_duration"),
        "lines": lines,
        "plik": scene.get("plik"),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Odtwarza sceny i teksty z indeksu w repozytorium.",
    )
    parser.add_argument("--indeks", type=Path, default=Path("index"), help="katalog indeksu")
    parser.add_argument("--sceny-wyj", type=Path, default=None,
                        help="JSONL ze scenami (format tools/timeline.py)")
    parser.add_argument("--teksty-wyj", type=Path, default=None,
                        help="JSONL {id, text} dla build_translator_pack.py")
    parser.add_argument("--z-mapa", action="store_true",
                        help="użyj dłuższej wersji tekstu z mapy źródłowej, jeśli jest")
    arguments = parser.parse_args(argv)

    scenes, texts, longer, manifest = load_index(arguments.indeks)
    if arguments.sceny_wyj:
        arguments.sceny_wyj.parent.mkdir(parents=True, exist_ok=True)
        with arguments.sceny_wyj.open("w", encoding="utf-8") as handle:
            for scene in scenes:
                handle.write(json.dumps(expand(scene, texts), ensure_ascii=False) + "\n")
    if arguments.teksty_wyj:
        arguments.teksty_wyj.parent.mkdir(parents=True, exist_ok=True)
        with arguments.teksty_wyj.open("w", encoding="utf-8") as handle:
            for key in sorted(texts):
                text = longer[key] if (arguments.z_mapa and key in longer) else texts[key]
                handle.write(json.dumps({"id": key, "text": text}, ensure_ascii=False) + "\n")
    print(json.dumps({
        "scen": len(scenes),
        "tekstow": len(texts),
        "z_dluzsza_wersja_mapy": len(longer),
        "sceny_wyj": str(arguments.sceny_wyj) if arguments.sceny_wyj else None,
        "teksty_wyj": str(arguments.teksty_wyj) if arguments.teksty_wyj else None,
        "z_mapa": arguments.z_mapa,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
