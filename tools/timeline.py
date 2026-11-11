#!/usr/bin/env python3
"""Read dialogue structure (scene, speaker, order) from a WWM timeline table.

The game stores cutscene and dialogue structure as serialized objects, not as a
flat string table. `data205` holds `TimelinePObject` trees:

    TimelinePObject
      __tracks__: [ EntityTrackGroup ... ]
        entity_tag  = the speaker's name (in-game Chinese name)
        entity_no   = the speaker's entity number
        __children__: [ EntityTextTrack ... ]
          __keyframes__: [ EntityTextSpan ... ]
            time            where the line starts inside the scene
            duration
            text            u64 hash — the key into the locale text map
            formatted_text  the line as displayed, in Chinese
            order           order of same-time lines

So a scene is one `TimelinePObject`, and its lines are `EntityTextSpan` keyframes
sorted by (time, order). The speaker is **not** `group_id` (it is always 0 in the
shipped data): the serialized field groups are written children-first and
scalars-last, so a keyframe belongs to the last `entity_tag` written before it.

The serializer encodes values as `<u8 tag><payload>`: 1 = u8, 2 = u16, 3 = u32,
4 = u64, 6 = f64, 8 = string (u16 bytes + UTF-8), 9 = array (u16 count),
0x0a = object (a u16 that is *not* a field count, then name/value pairs),
0x0b = null, 0x0c = false, 0x0d = true. An object therefore ends where the next
one starts: at the first byte that is not a `08` string field.

This module only reads; it never writes game files.
"""

from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path


class TimelineError(Exception):
    """The payload does not follow the timeline layout."""


def field_pattern(name: str) -> bytes:
    payload = name.encode("utf-8")
    return b"\x08" + struct.pack("<H", len(payload)) + payload


def value_position(buffer: bytes, offset: int, name: str) -> int:
    """Position of the value tag that follows a field name at `offset`."""
    return offset + 3 + len(name.encode("utf-8"))


def read_string(buffer: bytes, offset: int) -> str:
    if buffer[offset] != 0x08:
        raise TimelineError("field is not a string")
    size = struct.unpack_from("<H", buffer, offset + 1)[0]
    return buffer[offset + 3 : offset + 3 + size].decode("utf-8")


def find_all(buffer: bytes, pattern: bytes):
    index = buffer.find(pattern)
    while index >= 0:
        yield index
        index = buffer.find(pattern, index + 1)


MAX_DEPTH = 64


def read_value(buffer: bytes, offset: int, depth: int = 0):
    if depth > MAX_DEPTH:
        raise TimelineError("nesting is deeper than any real timeline")
    tag = buffer[offset]
    if tag == 0x01:
        return buffer[offset + 1], offset + 2
    if tag == 0x02:
        return struct.unpack_from("<H", buffer, offset + 1)[0], offset + 3
    if tag == 0x03:
        return struct.unpack_from("<I", buffer, offset + 1)[0], offset + 5
    if tag == 0x04:
        return struct.unpack_from("<Q", buffer, offset + 1)[0], offset + 9
    if tag == 0x06:
        return struct.unpack_from("<d", buffer, offset + 1)[0], offset + 9
    if tag == 0x08:
        size = struct.unpack_from("<H", buffer, offset + 1)[0]
        text = buffer[offset + 3 : offset + 3 + size].decode("utf-8", "replace")
        return text, offset + 3 + size
    if tag == 0x09:
        count = struct.unpack_from("<H", buffer, offset + 1)[0]
        offset += 3
        items = []
        for _ in range(count):
            item, offset = read_value(buffer, offset, depth + 1)
            items.append(item)
        return items, offset
    if tag == 0x0A:
        return parse_object(buffer, offset, depth + 1)
    if tag == 0x0B:
        return None, offset + 1
    if tag == 0x0C:
        return False, offset + 1
    if tag == 0x0D:
        return True, offset + 1
    raise TimelineError(f"unknown value tag {tag:#x} at {offset:#x}")


CHILD_FIELDS = ("__children__", "__keyframes__", "__tracks__")


def read_fields(buffer: bytes, offset: int, depth: int = 0) -> tuple[dict, int]:
    """Read one object's fields; child arrays are parsed recursively.

    The u16 in the object header is not a field count, so the object ends where
    the next object begins, i.e. at the first byte that is not a `08` string
    field start.
    """
    if depth > MAX_DEPTH:
        raise TimelineError("nesting is deeper than any real timeline")
    fields: dict = {}
    position = offset
    while position < len(buffer) and buffer[position] == 0x08:
        try:
            name, after_name = read_value(buffer, position, depth + 1)
        except (TimelineError, struct.error, IndexError, UnicodeDecodeError):
            break
        if not isinstance(name, str) or not name:
            break
        if name in fields:
            break
        if name in CHILD_FIELDS:
            count = struct.unpack_from("<H", buffer, after_name + 1)[0]
            cursor = after_name + 3
            children = []
            for _ in range(count):
                if cursor >= len(buffer) or buffer[cursor] != 0x0A:
                    break
                child, cursor = parse_object(buffer, cursor, depth + 1)
                children.append(child)
            fields[name] = children
            position = cursor
            continue
        try:
            fields[name], position = read_value(buffer, after_name, depth + 1)
        except (TimelineError, struct.error, IndexError, UnicodeDecodeError):
            break
    return fields, position


def parse_object(buffer: bytes, offset: int, depth: int = 0):
    if buffer[offset] != 0x0A:
        raise TimelineError("value is not an object")
    fields, position = read_fields(buffer, offset + 3, depth)
    return fields, position


def keyframe_starts(buffer: bytes):
    """Positions of `0a <count> 08 <len> time` — the start of a keyframe object."""
    for hit in find_all(buffer, field_pattern("time")):
        start = hit - 3
        if start >= 0 and buffer[start] == 0x0A:
            count = struct.unpack_from("<H", buffer, start + 1)[0]
            if 4 <= count <= 40:
                yield start


def parse_keyframe(buffer: bytes, start: int) -> dict | None:
    try:
        fields, _end = parse_object(buffer, start)
    except (TimelineError, struct.error, IndexError, RecursionError, UnicodeDecodeError):
        return None
    if not isinstance(fields.get("text"), int):
        return None
    if not isinstance(fields.get("formatted_text"), str) or not fields["formatted_text"]:
        return None
    return fields


def timelines(buffer: bytes):
    """Yield (start, end) spans of consecutive TimelinePObject blocks."""
    starts = []
    for offset in find_all(buffer, field_pattern("Type")):
        object_start = offset - 3
        if object_start < 0 or buffer[object_start] != 0x0A:
            continue
        position = value_position(buffer, offset, "Type")
        if buffer[position] != 0x08:
            continue
        try:
            if read_string(buffer, position) != "TimelinePObject":
                continue
        except (TimelineError, struct.error, IndexError):
            continue
        starts.append(object_start)
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(buffer)
        yield start, end


def _scalar(segment: bytes, name: str):
    """Read one scalar field by name anywhere in the segment."""
    hit = segment.find(field_pattern(name))
    if hit < 0:
        return None
    place = value_position(segment, hit, name)
    if place >= len(segment):
        return None
    tag = segment[place]
    if tag == 0x08:
        try:
            return read_string(segment, place)
        except (TimelineError, struct.error):
            return None
    if tag == 0x03:
        return struct.unpack_from("<I", segment, place + 1)[0]
    if tag == 0x02:
        return struct.unpack_from("<H", segment, place + 1)[0]
    if tag == 0x01:
        return segment[place + 1]
    if tag == 0x04:
        return struct.unpack_from("<Q", segment, place + 1)[0]
    if tag == 0x06:
        return struct.unpack_from("<d", segment, place + 1)[0]
    return None


def _speaker_after_tag(segment: bytes, offset: int) -> dict:
    """Describe the actor whose `entity_tag` sits at `offset`."""
    speaker = {"tag": None, "entity_no": None, "skeleton": None}
    place = value_position(segment, offset, "entity_tag")
    if place < len(segment) and segment[place] == 0x08:
        try:
            speaker["tag"] = read_string(segment, place)
        except (TimelineError, struct.error):
            speaker["tag"] = None
    window = segment[offset:offset + 400]
    hit = window.find(field_pattern("entity_no"))
    if hit >= 0:
        spot = value_position(window, hit, "entity_no")
        if spot < len(window) and window[spot] == 0x03:
            speaker["entity_no"] = struct.unpack_from("<I", window, spot + 1)[0]
    hit = window.find(field_pattern("skeleton"))
    if hit >= 0:
        spot = value_position(window, hit, "skeleton")
        if spot < len(window) and window[spot] == 0x08:
            try:
                speaker["skeleton"] = read_string(window, spot)
            except (TimelineError, struct.error):
                speaker["skeleton"] = None
    return speaker


def scene_from(buffer: bytes, start: int, end: int) -> dict:
    """Build one scene: its dialogue lines plus the actor of each line.

    Every field group in the file is written as *children first, scalars last*,
    so a keyframe belongs to the last `entity_tag` written before it. Lines are
    ordered inside the scene by (time, order).
    """
    segment = buffer[start:end]
    events = []
    for offset in find_all(segment, field_pattern("entity_tag")):
        events.append((offset, 0, "tag", _speaker_after_tag(segment, offset)))
    for offset in keyframe_starts(segment):
        fields = parse_keyframe(segment, offset)
        if fields:
            events.append((offset, 1, "kf", fields))
    events.sort(key=lambda item: (item[0], item[1]))

    speaker = {"tag": None, "entity_no": None, "skeleton": None}
    lines = []
    for _offset, _rank, kind, payload in events:
        if kind == "tag":
            speaker = payload
            continue
        if not isinstance(payload.get("text"), int):
            continue
        text = payload.get("formatted_text")
        if not isinstance(text, str) or not text:
            continue
        lines.append(
            {
                "time": payload.get("time"),
                "order": payload.get("order"),
                "source_id": payload.get("source_id"),
                "speaker": speaker["tag"],
                "speaker_no": speaker["entity_no"],
                "skeleton": speaker["skeleton"],
                "text_id": f"{payload['text']:016x}",
                "formatted_text": text,
            }
        )
    lines.sort(
        key=lambda row: (
            row["time"] if isinstance(row["time"], (int, float)) else 0.0,
            row["order"] if isinstance(row["order"], int) else 0,
        )
    )
    return {
        "dialog_no": _scalar(segment, "dialog_no"),
        "project": _scalar(segment, "project_name"),
        "timeline_id": _scalar(segment, "id"),
        "start_time": _scalar(segment, "startTime"),
        "total_duration": _scalar(segment, "total_duration"),
        "before_black_screen": _scalar(segment, "before_black_screen"),
        "lines": lines,
    }


def read_timelines(path) -> list[dict]:
    try:
        from tools import apply_translation as patcher  # noqa: PLC0415 - local import avoids a cycle
    except ImportError:  # pragma: no cover - script use
        import sys

        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        from tools import apply_translation as patcher
    data = Path(path).read_bytes()
    scenes = []
    for number, chunk in enumerate(patcher.read_container(data)):
        kind, payload = patcher.split_chunk(chunk)
        try:
            buffer = patcher.decompress(kind, payload)
        except Exception:  # noqa: BLE001 - a broken chunk must not stop the scan
            continue
        index = 0
        for start, end in timelines(buffer):
            scene = scene_from(buffer, start, end)
            scene["chunk"] = number
            scene["chunk_index"] = index
            scenes.append(scene)
            index += 1
    return scenes


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Extract dialogue scenes (speaker, order, text id) from a timeline table.",
    )
    parser.add_argument("path", help="decompressed-container file with timeline data (data205)")
    parser.add_argument("--scena", type=int, help="print one scene with this index")
    parser.add_argument("--jsonl", help="write all scenes as JSONL to this path")
    parser.add_argument("--limit", type=int, default=3, help="how many scenes to print")
    arguments = parser.parse_args(argv)

    scenes = read_timelines(arguments.path)
    with_lines = [scene for scene in scenes if scene["lines"]]
    print(
        json.dumps(
            {
                "timelines": len(scenes),
                "with_lines": len(with_lines),
                "lines": sum(len(scene["lines"]) for scene in scenes),
                "speakers": len({line["speaker"] for scene in scenes for line in scene["lines"]}),
            }
        )
    )
    if arguments.jsonl:
        with open(arguments.jsonl, "w", encoding="utf-8") as handle:
            for scene in scenes:
                handle.write(json.dumps(scene, ensure_ascii=False) + "\n")
    shown = (
        [with_lines[arguments.scena]]
        if arguments.scena is not None and 0 <= arguments.scena < len(with_lines)
        else with_lines[: arguments.limit]
    )
    for scene in shown:
        print(f"--- scena dialog_no={scene['dialog_no']} projekt={scene['project']}")
        for number, line in enumerate(scene["lines"], 1):
            print(f"  {number}. [{line['speaker'] or '?'}] t={line['time']} {line['text_id']} {line['formatted_text'][:60]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
