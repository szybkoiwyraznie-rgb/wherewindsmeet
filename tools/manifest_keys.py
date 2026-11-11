"""Czyta rejestr kluczy z `MANIFEST` gry i audytuje nim pokrycie scen.

`Package/HD/oversea/MANIFEST` to posortowany rejestr nazw kluczy lokalizacji
(`dialog_timelines.<id>`, `AL.behavior.boss`, `maps.*`, `spaces.*`, …).
Rekordy nie mają stałej długości, więc nazwy zbiera się skanem po wzorcu
`u16 długość + ASCII`, a nie po sztywnym kroku. To odczyt, nic nie jest zapisywane.

Najważniejsze, co z niego wynika: **pełna liczba dialogów w grze**. `data205`
zawiera tylko ich część, więc rejestr służy jako lista kontrolna pokrycia.

Użycie:
    python3 tools/manifest_keys.py local/manifest.bin
    python3 tools/manifest_keys.py local/manifest.bin --sceny local/sceny.jsonl
"""

from __future__ import annotations

import argparse
import json
import re
import struct
from collections import Counter
from pathlib import Path

NAME_PATTERN = re.compile(rb"[A-Za-z][0-9A-Za-z_.@\-]{2,119}")
DIALOG_PREFIX = "dialog_timelines."


def read_payload(path) -> bytes:
    """Zwraca rozpakowany `MANIFEST` (kontener + zstd), zachowując zgodność z patcherem."""
    try:
        from tools import apply_translation as patcher  # noqa: PLC0415 - import lokalny
    except ImportError:  # pragma: no cover - uruchomienie jako skrypt
        import sys

        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        from tools import apply_translation as patcher
    data = Path(path).read_bytes()
    chunks = patcher.read_container(data)
    kind, payload = patcher.split_chunk(chunks[0])
    return patcher.decompress(kind, payload)


def keys_from_payload(payload: bytes) -> list[str]:
    """Nazwy kluczy w kolejności wystąpienia (bez duplikatów)."""
    seen: dict[str, None] = {}
    for match in NAME_PATTERN.finditer(payload):
        try:
            name = match.group().decode("ascii")
        except UnicodeDecodeError:  # pragma: no cover - wzorzec jest ASCII
            continue
        seen.setdefault(name, None)
    return list(seen)


def dialog_ids(keys: list[str]) -> set[int]:
    """Identyfikatory `dialog_timelines.<id>` z rejestru."""
    ids = set()
    for key in keys:
        if not key.startswith(DIALOG_PREFIX):
            continue
        tail = key[len(DIALOG_PREFIX):]
        if tail.isdigit():
            ids.add(int(tail))
    return ids


def prefixes(keys: list[str], depth: int = 1) -> Counter:
    """Ile kluczy przypada na każdy prefiks (np. `dialog_timelines`, `AL.behavior`)."""
    counter: Counter = Counter()
    for key in keys:
        parts = key.split(".")[:depth]
        counter[".".join(parts)] += 1
    return counter


def scene_ids(scenes_path) -> set[int]:
    ids = set()
    with Path(scenes_path).open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            scene = json.loads(line)
            dialog_no = scene.get("dialog_no")
            if isinstance(dialog_no, int):
                ids.add(dialog_no)
    return ids


def report(payload: bytes, scenes_path=None) -> dict:
    keys = keys_from_payload(payload)
    dialogues = dialog_ids(keys)
    result = {
        "kluczy": len(keys),
        "dialog_timelines": len(dialogues),
        "zakres_dialog_no": (min(dialogues), max(dialogues)) if dialogues else None,
        "prefiksy": dict(prefixes(keys).most_common(12)),
    }
    if scenes_path is not None:
        ours = scene_ids(scenes_path)
        result["scen_z_dialog_no"] = len(ours)
        result["scen_poza_rejestrem"] = len(ours - dialogues)
        result["pokrycie_procent"] = round(100 * len(ours) / len(dialogues), 1) if dialogues else 0.0
        result["brakuje_dialogow"] = len(dialogues - ours)
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Rejestr kluczy MANIFEST i audyt pokrycia scen.")
    parser.add_argument("manifest", help="plik MANIFEST z Package/HD/oversea")
    parser.add_argument("--sceny", help="JSONL ze scenami z tools/timeline.py (opcjonalnie)")
    arguments = parser.parse_args(argv)
    payload = read_payload(arguments.manifest)
    print(json.dumps(report(payload, arguments.sceny), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
