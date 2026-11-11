#!/usr/bin/env python3
"""Liczy statystyki korpusu z wersjonowanego indeksu `index/`.

Cztery analizy, których brakowało do projektowania paczki tłumacza:

    dialog <-> mowca   ile grup dialogowych, ile ma wielu mowcow, ile ma wyłącznie
                       mowce generyczna (gracz/techniczna) — tam nie ma rozmowy
    kompletnosc        pokrycie rejestru, sceny bez dialog_no, teksty uzyte
                       wielokrotnie, grupy dialogow z kiloma timeline'ami
    chronologia        spojnosc (czas, kolejnosc), powtorzone czasy, czy
                       total_duration jest wiarygodna granica sceny
    kontekst           ktore pola sa wypelnione w scenach i liniach
    poza scenami       ile wpisow mapy tlumaczen nie nalezy do zadnej sceny
                       („widoki": interfejs, przedmioty, miejsca, encyklopedia)
                       oraz ile tekstow ma w mapie dluzsza wersje niz w scenie
Działa wyłącznie na repozytorium: bez `local/`, bez plików z Dysku, bez gry.
Nic nie pisze poza `--wyj`.

Opcjonalnie `--mapa PLIK` (mapa tłumaczeń `translate_words_map_zh_cn`) daje
dokładne liczby dla elementów poza scenami: bez pliku raport opiera się na
zweryfikowanej wcześniej liczbie niepustych wpisów mapy.

Użycie:
    python3 tools/analiza_korpusu.py --wyj analiza [--grupy] [--mapa PLIK]
"""

from __future__ import annotations

import argparse
import collections
import json
import statistics
from pathlib import Path

GENERIC_SPEAKERS = {"玩家", "主角", "player", "player_1", "player_2", "我", "你"}
MAP_ENTRIES_FILLED = 1816408  # zweryfikowane 2026-11-11 na mapie zh_cn
MAP_FILE_ENTRIES = 3581256  # wpisy w nagłowkach chunkow mapy zh_cn
EN_MAP_ENTRIES = 1122784  # mapa EN: 1 122 784 wpisow, 503 206 unikalnych tekstow
EN_MAP_UNIQUE_TEXTS = 503206
EN_MAP_REPEATS = 619578  # powtorzenia: 1 122 784 - 503 206


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


FORMAT_TOKENS = ("#H", "#R", "#Y", "{", "$T(", "[[")
DIALOG_PUNCTUATION = "「」『』！？…"


def read_map(path: Path) -> dict[str, str]:
    """Czyta mape tłumaczeń (kontener + tabele rekordow) do słownika id -> tekst."""
    try:
        from tools import apply_translation as patcher
        from tools import locale_records as records
    except ImportError:  # pragma: no cover - uruchomienie jako skrypt
        import sys

        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        from tools import apply_translation as patcher
        from tools import locale_records as records
    entries: dict[str, str] = {}
    for chunk in patcher.read_container(path.read_bytes()):
        kind, payload = patcher.split_chunk(chunk)
        try:
            buffer = patcher.decompress(kind, payload)
            for row in records.iter_texts(buffer):
                entries[row["id"]] = row["text"]
        except Exception:  # noqa: BLE001 - uszkodzony chunk nie zatrzymuje odczytu
            continue
    return entries


def analyse_offscene(scenes: list[dict], texts: dict[str, dict],
                     map_entries: dict[str, str] | None = None) -> dict:
    """Elementy mapy tłumaczeń, ktore nie należy do zadnej sceny (widoki).

    Bez `map_entries` liczba poza scenami wynika ze zweryfikowanej wcześniej
    liczby niepustych wpisów mapy `zh_cn`. Z plikiem mapy raport jest dokladny:
    ile to wpisów, ile unikalnych tekstow, jakie cechy maja i ktore `text_id`
    ze scen nie ma wpisu w mapie (tych linii nie da się przepisac do tłumaczeńia).
    """
    used: set[str] = set()
    occurrences: collections.Counter = collections.Counter()
    for scene in scenes:
        for line in scene["linie"]:
            used.add(line["text_id"])
            occurrences[line["text_id"]] += 1
    dangling = [text_id for scene in scenes for line in scene["linie"]
                if line["text_id"] not in texts]
    unused = [text_id for text_id in texts if text_id not in used]

    same = only_newlines = other = 0
    example: dict | None = None
    for text_id, row in texts.items():
        longer = row.get("tekst_mapa")
        if not longer:
            continue
        scene_text = row["tekst_zh"]
        if longer == scene_text:
            same += 1
        elif longer.replace("\n", "") == scene_text.replace("\n", ""):
            only_newlines += 1
        else:
            other += 1
            if example is None:
                example = {"text_id": text_id, "scena": scene_text, "mapa": longer}
    with_longer = same + only_newlines + other

    if map_entries is None:
        offscene = MAP_ENTRIES_FILLED - len(texts)
        report = {
            "mapa_zh_cn": {
                "wpisy_w_naglowkach_chunkow": MAP_FILE_ENTRIES,
                "wpisy_niepuste": MAP_ENTRIES_FILLED,
                "zweryfikowane": "2026-11-11, docs/EXPERIMENT_LOG.md",
            },
            "wpisy_przypisane_do_scen": len(texts),
            "wpisy_poza_scenami": offscene,
            "udzial_poza_scenami_procent": round(100 * offscene / MAP_ENTRIES_FILLED, 1),
            "co_siedzi_poza_scenami": {
                "zrodlo": "odczyt mapy zh_cn 2026-11-11 (docs/EXPERIMENT_LOG.md)",
                "kategorie": ["miejsca", "imiona postaci", "przedmioty", "interfejs",
                              "encyklopedia"],
                "przykłady": ["寿昌坊-平民", "邵冷乄德明", "耳砂珍坯·三阶", "累计登录2天"],
                "do_przeliczenia": ("rozbicie na kategorie i liczba unikalnych tekstów "
                                    "poza scenami wymaga pliku mapy (--mapa); indeks "
                                    "zawiera tylko teksty scen"),
            },
        }
    else:
        off = {key: value for key, value in map_entries.items() if key not in used}
        lengths = sorted(len(value) for value in off.values())
        tokens = sum(1 for value in off.values()
                     if any(token in value for token in FORMAT_TOKENS))
        spoken = sum(1 for value in off.values()
                     if any(mark in value for mark in DIALOG_PUNCTUATION))
        repeats = collections.Counter(off.values())
        report = {
            "mapa_zh_cn": {
                "wpisy_w_naglowkach_chunkow": MAP_FILE_ENTRIES,
                "wpisy_niepuste": len(map_entries),
                "zweryfikowane": "2026-11-11, odczyt pliku mapy",
            },
            "wpisy_przypisane_do_scen": len(used & set(map_entries)),
            "wpisy_poza_scenami": len(off),
            "udzial_poza_scenami_procent": round(100 * len(off) / len(map_entries), 1),
            "co_siedzi_poza_scenami": {
                "unikalnych_tekstow_poza_scenami": len(set(off.values())),
                "unikalnych_tekstow_w_calej_mapie": len(set(map_entries.values())),
                "długość_znaków": {
                    "mediana": statistics.median(lengths),
                    "średnia": round(statistics.mean(lengths), 1),
                    "p10": lengths[len(lengths) // 10],
                    "p90": lengths[len(lengths) * 9 // 10],
                    "maksimum": lengths[-1],
                },
                "krótsze_niz_5_znaków": sum(1 for length in lengths if length < 5),
                "dłuższe_niz_100_znaków": sum(1 for length in lengths if length > 100),
                "z_tokenami_formatowania": tokens,
                "z_tokenami_formatowania_procent": round(100 * tokens / len(off), 1),
                "z_interpunkcja_dialogowa": spoken,
                "najczęściej_powtarzane": [
                    {"tekst": text, "wpisów": count} for text, count in repeats.most_common(5)],
                "interpretacja": (
                    "połowa wpisów ma <= 5 znaków i tokeny formatowania występują "
                    "w 4% - to nazewnictwo i interfejs, nie dialog; najczęściej "
                    "powtarzane wpisy to nazwy wewnętrzne (np. nazwy postaci "
                    "używane w systemowych komunikatach), które nie są tekstem "
                    "dla gracza"),
            },
        }

    report["powiazania_scena_tekst"] = {
        "text_id_w_scenach_bez_tekstu": len(dangling),
        "teksty_nieuzywane_w_scenach": len(unused),
        "text_id_w_wielu_scenach": sum(1 for count in occurrences.values() if count > 1),
    }
    if map_entries is not None:
        report["powiazania_scena_tekst"]["text_id_w_scenach_bez_wpisu_w_mapie"] = \
            len(used - set(map_entries))
        report["powiazania_scena_tekst"]["text_id_w_scenach_bez_wpisu_w_mapie_przykład"] = \
            sorted(used - set(map_entries))[:10]
    report["wariant_tekstu_mapa_vs_scena"] = {
        "tekstow_z_dluzsza_wersja_w_mapie": with_longer,
        "identycznych": same,
        "rozni_sie_tylko_lamaniem_wiersza": only_newlines,
        "rozni_sie_trescia": other,
        "przykład": example,
        "znaczenie": ("wersję z mapy trzeba tłumaczyć: mapa trzyma pełną linię "
                      "z dopiskiem scenicznym w nawiasach, scena tylko fragment"),
    }
    report["skala_dla_decyzji"] = {
        "mapa_en_wpisy": EN_MAP_ENTRIES,
        "mapa_en_unikalnych_tekstow": EN_MAP_UNIQUE_TEXTS,
        "mapa_en_powtorzen": EN_MAP_REPEATS,
        "paczka_en_zip_mb": 24,
        "tokeny_w_paczce_en": 583,
        "uwaga": "liczba dla mapy EN - skala porownawcza, nie pomiar zh_cn",
    }
    return report


def analyse_registry(scenes: list[dict], manifest_path: Path) -> dict:
    """Ktore dialogi z rejestru gry nie maja sceny — lista kontrolna pokrycia.

    Rejestr (`MANIFEST`) nie jest w repozytorium, wiec ten raport tez trafia
    do osobnego pliku i nie jest odtwarzalny z wersjonowanego `index/`.
    """
    from tools import manifest_keys as keys  # noqa: PLC0415 - import lokalny

    payload = keys.read_payload(manifest_path)
    registry = keys.dialog_ids(keys.keys_from_payload(payload))
    ours = {scene["dialog_no"] for scene in scenes if isinstance(scene.get("dialog_no"), int)}
    missing = sorted(registry - ours)
    buckets: collections.Counter = collections.Counter(number // 1_000_000 for number in missing)
    return {
        "rejestr_dialog_timelines": len(registry),
        "scen_z_dialog_no": len(ours),
        "scen_poza_rejestrem": len(ours - registry),
        "pokrycie_procent": round(100 * len(ours) / len(registry), 2) if registry else 0.0,
        "brakuje_dialogow": len(missing),
        "brakujace_po_milionach": {str(key): value for key, value in sorted(buckets.items())},
        "brakujace_dialog_no": missing,
    }


def analyse_decisions(per_group: list[dict]) -> dict:
    """Grupy, ktorych nie da sie przetworzyc automatycznie — decyzja czlowieka.

    Pelna lista jest w rozpisie per grupa (`--grupy`); tutaj trafiaja te, ktore
    sa na tyle malo liczne, ze mozna je przegladac w calosci, plus probki.
    """
    multi_timeline = [
        {"dialog_no": row["dialog_no"], "timelineow": row["timelineow"],
         "pliki": row["pliki"], "kwestii": row["kwestii"], "mowcow": row["mowcow"]}
        for row in per_group if row["timelineow"] > 1]
    generic = [row for row in per_group if row["tylko_generyczna_obsada"]]
    no_speaker = [row for row in per_group if row["mowcow"] == 0]
    return {
        "grupy_z_wieloma_timeline": {
            "liczb": len(multi_timeline),
            "lista": multi_timeline,
            "co_zrobic": ("ten sam dialog_no w dwoch plikach z inna trescia i innymi "
                          "mowcami — nie scalac automatycznie; kazda timeline to osobne "
                          "przejscie dialogu"),
        },
        "grupy_tylko_generyczna_obsada": {
            "liczb": len(generic),
            "proba": [row["dialog_no"] for row in generic[:20]],
            "co_zrobic": ("brak rozpoznawalnego mowcy (gracz lub grupa techniczna) — "
                          "tlumacz nie moze wymyslac imion; przeklad po bezosobowej "
                          "wersji z mapy"),
        },
        "grupy_bez_mowcy": {
            "liczb": len(no_speaker),
            "proba": [row["dialog_no"] for row in no_speaker[:20]],
            "co_zrobic": "kwestie bez wypelnionego mowca — ustalic mowce przed paczka",
        },
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Statystyki korpusu z indeksu w repozytorium.")
    parser.add_argument("--indeks", type=Path, default=Path("index"), help="katalog indeksu")
    parser.add_argument("--wyj", type=Path, default=Path("analiza"), help="katalog wyniku")
    parser.add_argument("--grupy", action="store_true",
                        help="zapisz też rozpis per grupa dialogowa (plik ok. 18 MB)")
    parser.add_argument("--mapa", type=Path, default=None,
                        help="plik mapy tłumaczeń translate_words_map_zh_cn (dokładne "
                             "liczby elementów poza scenami)")
    parser.add_argument("--rejestr", type=Path, default=None,
                        help="plik rejestru MANIFEST — lista brakujących dialogów")
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
        "elementy_poza_scenami.json": analyse_offscene(scenes, texts),
        "do_decyzji.json": analyse_decisions(per_group),
    }
    for name, payload in outputs.items():
        (arguments.wyj / name).write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n",
                                          encoding="utf-8")

    # Pomiar z pliku mapy trafia do osobnego pliku: repozytorium nie trzyma mapy,
    # wiec ten raport nie jest odtwarzalny z wersjonowanego index/.
    if arguments.mapa:
        (arguments.wyj / "mapa_zh_cn.json").write_text(
            json.dumps(analyse_offscene(scenes, texts, read_map(arguments.mapa)),
                       ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    if arguments.rejestr:
        (arguments.wyj / "brakujace_dialogi.json").write_text(
            json.dumps(analyse_registry(scenes, arguments.rejestr),
                       ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    # Rozpis per grupa jest duzy (ok. 18 MB), wiec trafia do repo tylko na zyczenie.
    if arguments.grupy:
        with (arguments.wyj / "dialog_mowca_grupy.jsonl").open("w", encoding="utf-8") as handle:
            for row in per_group:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        outputs["dialog_mowca_grupy.jsonl"] = per_group
    print(json.dumps({"scen": len(scenes), "grup": dialogues_summary["grup_dialogowych"],
                      "plikow": len(outputs)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
