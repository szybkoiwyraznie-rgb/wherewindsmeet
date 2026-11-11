#!/usr/bin/env python3
"""Liczy statystyki korpusu z wersjonowanego indeksu `index/`.

Cztery analizy, których brakowało do projektowania paczki tłumacza:

    dialog <-> mowca   ile grup dialogowych, ile ma wielu mowcow, ile ma wyłącznie
                       mowce generyczna (gracz/techniczna) — tam nie ma rozmowy
    kompletnosc        pokrycie rejestru, sceny bez dialog_no, teksty uzyte
                       wielokrotnie, teksty mapy niepowiazane ze scenami
    chronologia        spojnosc (czas, kolejnosc), powtorzone czasy, czy
                       total_duration jest wiarygodna granica sceny
    kontekst           ktore pola sa wypelnione w scenach i liniach

Działa wyłącznie na repozytorium: bez `local/`, bez plików z Dysku, bez gry.
Nic nie pisze poza `--wyj`.

Użycie:
    python3 tools/analiza_korpusu.py --wyj analiza
"""

from __future__ import annotations

import argparse
import collections
import json
import statistics
from pathlib import Path

GENERIC_SPEAKERS = {"玩家", "主角", "player", "player_1", "player_2", "我", "你"}
MAP_ENTRIES_FILLED = 1816408  # zweryfikowane 2026-11-11 na mapie zh_cn


def load(root: Path) -> tuple[list[dict], dict[str, dict]]:
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    scenes: list[dict] = []
    for shard in manifest["shardy"]["sceny"]:
        for line in (root / shard["plik"]).read_text(encoding="utf-8").splitlines():
            if line:
                scenes.append(json.loads(line))
    texts: dict[str, dict] = {}
    for shard in manifest["shardy"]["teksty"]:
        for line in (root / shard["plik"]).read_text(encoding="utf-8").splitlines():
            if line:
                row = json.loads(line)
                texts[row["text_id"]] = row
    return scenes, texts


def speaker_kind(tag: object) -> str:
    if not tag:
        return "brak"
    if tag in GENERIC_SPEAKERS:
        return "gracz"
    if str(tag).startswith(("Entity", "__")):
        return "techniczny"
    return "postac"


def dialogues(scenes: list[dict]) -> dict[int, list[dict]]:
    groups: dict[int, list[dict]] = collections.defaultdict(list)
    for scene in scenes:
        number = scene.get("dialog_no")
        if isinstance(number, int):
            groups[number].append(scene)
    return groups


def analyse_dialogues(scenes: list[dict]) -> tuple[dict, list[dict]]:
    groups = dialogues(scenes)
    per_group: list[dict] = []
    for number, members in groups.items():
        speakers: collections.Counter = collections.Counter()
        for scene in members:
            for line in scene["linie"]:
                speakers[(line.get("mowca"), line.get("speaker_no"))] += 1
        cast = [{"mowca": tag, "speaker_no": entity, "kwestii": count,
                 "rodzaj": speaker_kind(tag)} for (tag, entity), count in speakers.most_common()]
        per_group.append(
            {
                "dialog_no": number,
                "timelineow": len(members),
                "pliki": sorted({scene["plik"] for scene in members}),
                "projekty": sorted({scene["projekt"] for scene in members if scene["projekt"]}),
                "kwestii": sum(len(scene["linie"]) for scene in members),
                "mowcow": len(cast),
                "mowcy": cast,
                "tylko_generyczna_obsada": all(row["rodzaj"] in ("gracz", "techniczny", "brak")
                                                for row in cast),
            }
        )
    per_group.sort(key=lambda row: row["dialog_no"])
    sizes = collections.Counter(row["mowcow"] for row in per_group)
    summary = {
        "grup_dialogowych": len(per_group),
        "grup_z_wieloma_timeline": sum(1 for row in per_group if row["timelineow"] > 1),
        "grup_z_wieloma_mowcami": sum(1 for row in per_group if row["mowcow"] > 1),
        "rozklad_liczby_mowcow": {str(key): value for key, value in sorted(sizes.items())},
        "grup_tylko_generyczna_obsada": sum(1 for row in per_group if row["tylko_generyczna_obsada"]),
        "unikalnych_mowcow_par": len({(row["mowca"], row["speaker_no"])
                                      for group in per_group for row in group["mowcy"]}),
        "unikalnych_nazw_mowcow": len({row["mowca"] for group in per_group
                                       for row in group["mowcy"] if row["mowca"]}),
        "mowcow_po_rodzaju": dict(collections.Counter(row["rodzaj"] for group in per_group
                                                      for row in group["mowcy"])),
    }
    return summary, per_group


def analyse_completeness(scenes: list[dict], texts: dict[str, dict], manifest: dict) -> dict:
    per_file = collections.Counter(scene["plik"] for scene in scenes)
    lines_per_file: collections.Counter = collections.Counter()
    for scene in scenes:
        lines_per_file[scene["plik"]] += len(scene["linie"])
    uses: collections.Counter = collections.Counter(line["text_id"] for scene in scenes
                                                    for line in scene["linie"])
    multi = [row for row in dialogues(scenes).items() if len(row[1]) > 1]
    return {
        "pokrycie_rejestru": manifest["pokrycie"],
        "sceny_na_plik": dict(sorted(per_file.items())),
        "kwestie_na_plik": dict(sorted(lines_per_file.items())),
        "scen_bez_dialog_no": sum(1 for scene in scenes if scene.get("dialog_no") is None),
        "kwestii_w_scenach_bez_dialog_no": sum(len(scene["linie"]) for scene in scenes
                                               if scene.get("dialog_no") is None),
        "text_id_w_wielu_scenach": sum(1 for count in uses.values() if count > 1),
        "maks_wystapien_text_id": max(uses.values()),
        "grupy_z_wieloma_timeline": [
            {"dialog_no": number, "timelineow": len(members),
             "pliki": sorted({scene["plik"] for scene in members}),
             "kwestii": sum(len(scene["linie"]) for scene in members),
             "id_timelineow": [scene["timeline_id"] for scene in members]}
            for number, members in sorted(multi)],
        "tekstow_poza_scenami": MAP_ENTRIES_FILLED - len(texts),
        "tekstow_poza_scenami_uwaga": (
            "mapa zh_cn miala 1816408 niepustych wpisow (zweryfikowane 2026-11-11); "
            "do wyliczenia potrzebny jest plik mapy, ktory zginął przy czyszczeniu local/"),
    }


def analyse_chronology(scenes: list[dict]) -> dict:
    unordered = repeated = no_time = no_duration = outside = 0
    durations: list[float] = []
    counts: list[int] = []
    starts: list[float] = []
    examples: list[dict] = []
    for scene in scenes:
        lines = scene["linie"]
        counts.append(len(lines))
        times = [line["czas"] if isinstance(line["czas"], (int, float)) else None for line in lines]
        if any(value is None for value in times):
            no_time += 1
        known = [value for value in times if value is not None]
        if known != sorted(known):
            unordered += 1
        if len(set(known)) != len(known):
            repeated += 1
        start, duration = scene.get("start_time"), scene.get("total_duration")
        if not isinstance(duration, (int, float)) or duration <= 0:
            no_duration += 1
        else:
            durations.append(duration)
            if isinstance(start, (int, float)) and known and max(known) > start + duration + 0.001:
                outside += 1
                if len(examples) < 5:
                    examples.append({"scena": scene["scena"], "plik": scene["plik"],
                                     "dialog_no": scene.get("dialog_no"), "start_time": start,
                                     "total_duration": duration, "ostatni_czas": max(known),
                                     "przekroczenie": round(max(known) - start - duration, 2)})
        if isinstance(start, (int, float)):
            starts.append(start)
    return {
        "scen": len(scenes),
        "linii_na_scene": {"min": min(counts), "max": max(counts),
                           "mediana": statistics.median(counts), "srednia": round(statistics.mean(counts), 2)},
        "scen_z_niemonotonicznym_czasem": unordered,
        "scen_z_duplikatem_czasu": repeated,
        "scen_z_linia_bez_czasu": no_time,
        "scen_bez_total_duration": no_duration,
        "scen_z_linia_poza_oknem_czasu": outside,
        "przyklady_poza_oknem": examples,
        "dlugosc_sceny": {"min": min(durations), "max": max(durations),
                          "mediana": statistics.median(durations),
                          "srednia": round(statistics.mean(durations), 2)},
        "start_time": {"min": min(starts), "max": max(starts),
                       "rozne_od_zera": sum(1 for value in starts if value != 0)},
        "kwestii_na_sekunde_medianowo": round(statistics.mean(counts) / statistics.mean(durations), 3),
    }


def analyse_context(scenes: list[dict]) -> dict:
    def filled(field: str) -> int:
        return sum(1 for scene in scenes if scene.get(field) not in (None, "", []))

    lines = [line for scene in scenes for line in scene["linie"]]
    sources = [line.get("source_id") for line in lines]
    casts = [len(scene["obsada"]) for scene in scenes if scene.get("obsada")]
    return {
        "scen": len(scenes),
        "uzupelnienie_pol_sceny": {"projekt": filled("projekt"), "timeline_id": filled("timeline_id"),
                                   "start_time": filled("start_time"),
                                   "total_duration": filled("total_duration"), "obsada": len(casts)},
        "uzupelnienie_pol_linii": {
            "czas": sum(1 for line in lines if isinstance(line.get("czas"), (int, float))),
            "kolejnosc": sum(1 for line in lines if isinstance(line.get("kolejnosc"), int)),
            "source_id": sum(1 for line in lines if line.get("source_id") is not None),
            "mowca": sum(1 for line in lines if line.get("mowca")),
            "speaker_no": sum(1 for line in lines if line.get("speaker_no") is not None),
        },
        "kwestii": len(lines),
        "source_id_unikalne": len(set(sources)),
        "projekty_unikalne": len({scene["projekt"] for scene in scenes if scene.get("projekt")}),
        "timeline_id_unikalne": len({scene["timeline_id"] for scene in scenes
                                     if scene.get("timeline_id")}),
        "obsada_rozmiar": {"min": min(casts), "max": max(casts),
                           "mediana": statistics.median(casts)},
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Statystyki korpusu z indeksu w repozytorium.")
    parser.add_argument("--indeks", type=Path, default=Path("index"), help="katalog indeksu")
    parser.add_argument("--wyj", type=Path, default=Path("analiza"), help="katalog wyniku")
    arguments = parser.parse_args(argv)

    scenes, texts = load(arguments.indeks)
    manifest = json.loads((arguments.indeks / "manifest.json").read_text(encoding="utf-8"))
    dialogues_summary, per_group = analyse_dialogues(scenes)
    arguments.wyj.mkdir(parents=True, exist_ok=True)

    outputs = {
        "dialog_mowca.json": dialogues_summary,
        "kompletnosc.json": analyse_completeness(scenes, texts, manifest),
        "chronologia.json": analyse_chronology(scenes),
        "kontekst.json": analyse_context(scenes),
    }
    for name, payload in outputs.items():
        (arguments.wyj / name).write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n",
                                          encoding="utf-8")

    # Rozpis per grupa jest duza (megabajty), wiec jest tylko na zyczenie.
    if arguments.wyj.joinpath("dialog_mowca_grupy.jsonl").exists():
        arguments.wyj.joinpath("dialog_mowca_grupy.jsonl").unlink()
    print(json.dumps({"scen": len(scenes), "grup": dialogues_summary["grup_dialogowych"],
                      "plikow": len(outputs)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
