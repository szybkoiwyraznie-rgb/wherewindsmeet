#!/usr/bin/env python3
"""Index decoded Storyline JSON blocks without retaining their game content.

Reads decoded `.bin` blocks whose JSON root contains `Storyline.NodeBuffer`,
then writes a compact JSONL summary of node types and cross-table numeric
references. The output deliberately omits node text, variables, coordinates,
entity payloads and connection data.

Usage:
    python3 tools/index_storyline_graphs.py local/patch_karwedane \
        --output index/mpk/storyline_graphs.jsonl
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path


def summarize(path: Path, document: dict) -> dict | None:
    storyline = document.get("Storyline")
    if not isinstance(storyline, dict) or not isinstance(storyline.get("NodeBuffer"), list):
        return None

    nodes = storyline["NodeBuffer"]
    types: Counter[str] = Counter()
    tasks: list[int] = []
    transfers: list[int] = []
    spaces: list[int] = []
    cutscenes: list[dict] = []
    qtes: list[int] = []
    nested_paths: list[str] = []

    for node in nodes:
        if not isinstance(node, dict):
            continue
        kind = node.get("Type")
        if isinstance(kind, str):
            types[kind] += 1
        data = node.get("Data")
        if not isinstance(data, dict):
            continue

        if kind == "TrackTaskNode" and isinstance(data.get("task_no"), int):
            tasks.append(data["task_no"])
        elif kind == "GameLevelTransferNode":
            if isinstance(data.get("transfer_no"), int):
                transfers.append(data["transfer_no"])
            if isinstance(data.get("space_no"), int):
                spaces.append(data["space_no"])
        elif kind == "DialogCutsceneSequenceNode":
            for entry in data.get("sequence", []):
                if isinstance(entry, dict) and isinstance(entry.get("id"), int):
                    cutscenes.append({
                        "id": entry["id"],
                        "type": entry.get("type"),
                        "auto_preload_next": entry.get("auto_preload_next"),
                    })
        elif kind == "GameLevelCutsceneQteNode" and isinstance(data.get("cutscene_qte_no"), int):
            qtes.append(data["cutscene_qte_no"])
        elif kind == "ClientRunStorylineNode" and isinstance(data.get("storyline_path"), str):
            nested_paths.append(data["storyline_path"])

    stem = path.stem
    pack, sep, asset_id = stem.partition("_")
    return {
        "block": stem,
        "pack": int(pack) if pack.isdecimal() else None,
        "asset_id": asset_id if sep else None,
        "nodes": len(nodes),
        "node_types": dict(sorted(types.items())),
        "task_ids": list(dict.fromkeys(tasks)),
        "transfer_ids": list(dict.fromkeys(transfers)),
        "space_ids": list(dict.fromkeys(spaces)),
        "cutscene_sequence": cutscenes,
        "cutscene_qte_ids": list(dict.fromkeys(qtes)),
        "nested_storylines": list(dict.fromkeys(nested_paths)),
    }


def build(source: Path) -> list[dict]:
    records: list[dict] = []
    for path in sorted(source.glob("*.bin")):
        try:
            raw = path.read_bytes()
            if not raw.startswith(b"{\""):
                continue
            document = json.loads(raw)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        if isinstance(document, dict):
            record = summarize(path, document)
            if record is not None:
                records.append(record)
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="folder with already-decoded JSON `.bin` blocks")
    parser.add_argument("--output", type=Path, required=True, help="JSONL output path")
    args = parser.parse_args()
    records = build(args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as stream:
        for record in records:
            stream.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
    print(f"{len(records)} grafów Storyline → {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
