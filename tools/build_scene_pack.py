"""Buduje paczkę scen dla Tłumacza: mówcy, kwestie w scenach, granice i kolejność scen.

Wejście:
  * JSONL ze scenami z `tools/timeline.py --jsonl` (jedna scena = jeden wiersz),
  * JSONL z unikalnymi tekstami mapy EN (`{"id": "<hex>", "text": "..."}`), opcjonalny.

Wyjście (katalog `--wyjscie`, domyślnie `local/tlumacz`):
  00_INDEX.md        – metodologia, statystyki i sposób czytania paczki,
  01_MOWCY.md        – obsada z liczbą kwestii i rodzajem mówcy,
  02_CHRONOLOGIA.md  – wszystkie sceny w kolejności, z mówcami i długością,
  sceny/*.md         – sceny z kwestiami (chiński oryginał + EN pomocniczo),
  sceny.jsonl        – te same dane maszynowo (dla patchera i audytu).

Kolejność scen: rosnące `dialog_no` (identyfikator dialogu w grze); sceny bez
`dialog_no` trafiają na pozycję sąsiada z pliku, żeby nie wypadały z ciągu.
Kolejność kwestii w scenie: `(time, order)`.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

GENERIC_SPEAKERS = {
    "玩家",
    "player",
    "player_1",
    "main_player",
    "mian_player",
    "主角",
    "我",
    "你",
    "protagonist",
}

GENERIC_PREFIXES = ("player", "mian_player", "main_player")


def speaker_kind(tag: str | None) -> str:
    """Zwraca rodzaj mówcy: gracz, techniczny, postać albo brak."""
    if not tag:
        return "brak"
    if tag in GENERIC_SPEAKERS or tag.lower().startswith(GENERIC_PREFIXES):
        return "gracz"
    if tag.startswith("Entity") or tag.startswith("__"):
        return "techniczny"
    return "postać"


def sort_key(scene: dict, index: int) -> tuple[int, int, int]:
    """Kolejność scen: dialog_no, potem kolejność w pliku."""
    dialog_no = scene.get("dialog_no")
    if isinstance(dialog_no, int):
        return (dialog_no, 0, index)
    return (-1, 0, index)


def fill_missing_order(scenes: list[dict]) -> list[dict]:
    """Numeruje sceny z `dialog_no` po kolei, a cinematics osobno od S9001.

    Sceny bez `dialog_no` nie mają żadnego znacznika miejsca w fabule, więc nie
    udajemy, że go znają: dostają własną numerację po wszystkich dialogach.
    """
    with_number = [i for i, scene in enumerate(scenes) if isinstance(scene.get("dialog_no"), int)]
    without_number = [i for i, scene in enumerate(scenes) if not isinstance(scene.get("dialog_no"), int)]
    with_number.sort(key=lambda i: (scenes[i]["dialog_no"], i))
    for rank, index in enumerate(with_number, start=1):
        scenes[index]["order"] = rank
        scenes[index]["order_kind"] = "dialog_no"
    for rank, index in enumerate(without_number, start=9001):
        scenes[index]["order"] = rank
        scenes[index]["order_kind"] = "kolejność zapisu"
    return scenes


def clean(text: str) -> str:
    """Zamienia znaki łamiące tabelę markdown."""
    return text.replace("|", "\\|").replace("\r\n", "\n").replace("\n", "<br>")


def slug(name: str | None) -> str:
    base = (name or "bez-projektu").strip() or "bez-projektu"
    base = base.replace("对话-", "").replace(".dialog", "")
    base = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff_.-]+", "_", base)
    return base.strip("_") or "cinematic"


def scene_block(scene: dict, english: dict[str, str]) -> list[str]:
    lines = scene.get("lines") or []
    duration = scene.get("total_duration")
    place = f"dialog_no {scene['dialog_no']}" if scene.get("dialog_no") is not None else "numer w pliku"
    header = f"### S{scene['order']:04d} · {place} · {len(lines)} kwestii"
    if isinstance(duration, (int, float)):
        header += f" · {duration:.1f} s"
    out = [header, ""]
    speakers = Counter(line.get("speaker") or "(bez nazwy)" for line in lines)
    cast = ", ".join(f"{name} ({count})" for name, count in speakers.most_common())
    out.append(f"Projekt: `{scene.get('project')}` · obsada: {cast}")
    out.append("")
    out.append("| # | czas | mówca | chiński (źródło) | angielski (pomocniczo) | id |")
    out.append("|---|------|-------|------------------|------------------------|----|")
    for number, line in enumerate(lines, start=1):
        moment = line.get("time")
        moment = f"{moment:.2f}" if isinstance(moment, float) else str(moment)
        speaker = line.get("speaker") or "(bez nazwy w danych)"
        kind = speaker_kind(line.get("speaker"))
        if kind == "gracz":
            speaker = f"{speaker} (gracz)"
        elif kind == "techniczny":
            speaker = f"{speaker} (grupa techniczna)"
        english_text = english.get(line.get("text_id") or "")
        out.append(
            "| {n} | {t} | {s} | {zh} | {en} | `{i}` |".format(
                n=number,
                t=moment,
                s=clean(speaker),
                zh=clean(line.get("formatted_text") or ""),
                en=clean(english_text) if english_text else "—",
                i=line.get("text_id"),
            )
        )
    out.append("")
    return out


def project_files(scenes: list[dict], english: dict[str, str], per_file: int = 400) -> dict[str, list[str]]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for scene in scenes:
        if not scene.get("lines"):
            continue  # sceny bez tekstu zostają w chronologii i JSONL, ale nie w plikach scen
        groups[slug(scene.get("project"))].append(scene)
    files: dict[str, list[str]] = {}
    for name, items in sorted(groups.items()):
        items.sort(key=lambda scene: scene["order"])
        if len(items) <= per_file:
            blocks = [f"# Sceny: {items[0].get('project') or 'dialogi bez projektu'}", ""]
            blocks.append(
                f"{len(items)} scen, {sum(len(s.get('lines') or []) for s in items)} kwestii. "
                "Kolejność: rosnące `dialog_no`, w scenie `(time, order)`."
            )
            blocks.append("")
            for scene in items:
                blocks.extend(scene_block(scene, english))
                scene["file"] = f"sceny/{name}.md"
            files[f"{name}.md"] = blocks
            continue
        for offset in range(0, len(items), per_file):
            part = items[offset:offset + per_file]
            part_no = offset // per_file + 1
            blocks = [f"# Sceny: {part[0].get('project') or 'dialogi bez projektu'} (część {part_no})", ""]
            for scene in part:
                blocks.extend(scene_block(scene, english))
                scene["file"] = f"sceny/{name}-{part_no:02d}.md"
            files[f"{name}-{part_no:02d}.md"] = blocks
    return files


def write_speakers(path: Path, scenes: list[dict]) -> None:
    stats: Counter = Counter()
    entities: dict[str, set] = defaultdict(set)
    for scene in scenes:
        for line in scene.get("lines") or []:
            tag = line.get("speaker") or "(bez nazwy w danych)"
            stats[tag] += 1
            if line.get("speaker_no") is not None:
                entities[tag].add(line["speaker_no"])
    out = [
        "# Obsada",
        "",
        "Mówca jest brany z `entity_tag` grupy, w której zapisana jest kwestia.",
        "`entity_no` to identyfikator postaci w grze (ten sam dla tej samej osoby).",
        "",
        "| mówca | kwestii | rodzaj | entity_no |",
        "|-------|---------|--------|-----------|",
    ]
    for tag, count in stats.most_common():
        numbers = ", ".join(str(value) for value in sorted(entities.get(tag, set()))[:3])
        out.append(f"| {clean(tag)} | {count} | {speaker_kind(tag)} | {numbers or '—'} |")
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def write_chronology(path: Path, scenes: list[dict]) -> None:
    out = [
        "# Chronologia scen",
        "",
        "Sceny z `dialog_no` idą rosnąco po tym identyfikatorze (S0001–S8999).",
        "Cinematics (bez `dialog_no`) mają własną numerację S9001+ w kolejności zapisu w pliku,",
        "bo nie zawierają żadnej informacji o miejscu w fabule.",
        "",
        "| # | dialog_no | projekt | kwestii | obsada | plik |",
        "|---|-----------|---------|---------|--------|------|",
    ]
    for scene in sorted(scenes, key=lambda item: (item.get("order_kind") != "dialog_no", item["order"])):
        cast = Counter(line.get("speaker") or "(bez nazwy)" for line in scene.get("lines") or [])
        out.append(
            "| S{o:04d} | {dn} | {p} | {n} | {c} | `{f}` |".format(
                o=scene["order"],
                dn=scene.get("dialog_no"),
                p=scene.get("project") or "bez projektu",
                n=len(scene.get("lines") or []),
                c=clean(", ".join(name for name, _ in cast.most_common(4))),
                f=scene.get("file"),
            )
        )
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def write_index(path: Path, scenes: list[dict], files: dict[str, list[str]], english: dict[str, str]) -> None:
    lines = [line for scene in scenes for line in scene.get("lines") or []]
    with_english = sum(1 for line in lines if line.get("text_id") in english)
    speakers = {line.get("speaker") for line in lines}
    kinds = Counter(speaker_kind(line.get("speaker")) for line in lines)
    out = [
        "# Paczka scen dla Tłumacza — Where Winds Meet",
        "",
        "## Co jest w środku",
        "",
        f"- scen: **{len(scenes)}**, kwestii: **{len(lines)}**,",
        f"- mówców (różnych etykiet): **{len(speakers)}**, kwestii bez mówcy: **{kinds.get('brak', 0)}**,",
        f"- kwestii z angielskim pomocniczym: **{with_english}** z {len(lines)}.",
        "",
        "## Skąd to jest",
        "",
        "Sceny pochodzą z `data205` gry (serializowany graf timeline'ów):",
        "",
        "- **scena** = jeden `TimelinePObject` (`dialog_no`, `project_name`, `total_duration`),",
        "- **kwestia** = `EntityTextSpan` (`text` = hash klucza mapy, `formatted_text` = chiński oryginał),",
        "- **mówca** = `entity_tag` grupy, w której zapisana jest kwestia (+ `entity_no`),",
        "- **kolejność kwestii w scenie** = `(time, order)`,",
        "- **kolejność scen** = rosnące `dialog_no`.",
        "",
        "## Jak czytać pliki scen",
        "",
        "Każda scena ma nagłówek `S<numer> · dialog_no <id> · liczba kwestii · długość`,",
        "listę obsady w kolejności częstości i tabelę kwestii:",
        "",
        "| kolumna | znaczenie |",
        "|---------|-----------|",
        "| czas | sekunda w scenie (`time`) |",
        "| mówca | `entity_tag`; dopisek `(gracz)` = postać gracza, `(grupa techniczna)` = grupa bez postaci |",
        "| chiński | tekst z gry (`formatted_text`), źródło tłumaczenia |",
        "| angielski | tekst z mapy EN, wyłącznie pomocniczo |",
        "| id | hash klucza mapy; tego używa patcher |",
        "",
        "## Pliki",
        "",
        "- `01_MOWCY.md` — obsada z liczbą kwestii i `entity_no`,",
        "- `02_CHRONOLOGIA.md` — wszystkie sceny po kolei,",
        "- `sceny/*.md` — sceny z kwestiami,",
        "- `sceny.jsonl` — te same dane maszynowo.",
        "",
        "## Ograniczenia, które trzeba znać",
        "",
        "- `dialog_no` to identyfikator dialogu w danych gry; **nie jest sprawdzone**,",
        "  czy odpowiada kolejności fabuły. To jedyny sygnał kolejności w tym pliku.",
        "- Mówcy typu `玩家`, `player`, `主角`, `我`, `你` to postać gracza — imię ustala gracz.",
        "- Grupy techniczne (`Entity轨道组`) nie mają postaci; takie kwestie nie mają mówcy.",
        "- Kwestie w cinematicach **mają** mówców (nie są puste) — sprawdzone dla 933 scen bez `project_name`.",
        "",
        "## Pliki scen",
        "",
    ]
    for name in sorted(files):
        out.append(f"- `sceny/{name}`")
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def load_english(path: Path | None) -> dict[str, str]:
    if not path or not path.exists():
        return {}
    english: dict[str, str] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            ident = record.get("id")
            text = record.get("text")
            if isinstance(ident, str) and isinstance(text, str):
                english[ident.lower()] = text
    return english


def main() -> int:
    parser = argparse.ArgumentParser(description="Paczka scen dla Tłumacza (mówcy + chronologia).")
    parser.add_argument("sceny", type=Path, help="JSONL ze scenami z tools/timeline.py")
    parser.add_argument("--anglielski", "--angielski", dest="english", type=Path, default=None,
                        help="JSONL z unikalnymi tekstami EN (id, text)")
    parser.add_argument("--wyjscie", type=Path, default=Path("local/tlumacz"))
    parser.add_argument("--na-plik", type=int, default=400, help="ile scen w jednym pliku .md")
    arguments = parser.parse_args()

    scenes = [json.loads(line) for line in arguments.sceny.open(encoding="utf-8") if line.strip()]
    scenes = fill_missing_order(scenes)
    english = load_english(arguments.english)

    out_dir = arguments.wyjscie
    scenes_dir = out_dir / "sceny"
    scenes_dir.mkdir(parents=True, exist_ok=True)

    files = project_files(scenes, english, per_file=arguments.na_plik)
    for name, blocks in files.items():
        (scenes_dir / name).write_text("\n".join(blocks) + "\n", encoding="utf-8")
    write_index(out_dir / "00_INDEX.md", scenes, files, english)
    write_speakers(out_dir / "01_MOWCY.md", scenes)
    write_chronology(out_dir / "02_CHRONOLOGIA.md", scenes)
    with (out_dir / "sceny.jsonl").open("w", encoding="utf-8") as handle:
        for scene in sorted(scenes, key=lambda item: (item.get("order_kind") != "dialog_no", item["order"])):
            handle.write(json.dumps(scene, ensure_ascii=False) + "\n")

    lines = sum(len(scene.get("lines") or []) for scene in scenes)
    print(json.dumps({
        "scen": len(scenes),
        "kwestii": lines,
        "plikow_md": len(files),
        "z_angielskim": sum(1 for s in scenes for l in s.get("lines") or [] if l.get("text_id") in english),
        "wyjscie": str(out_dir),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
