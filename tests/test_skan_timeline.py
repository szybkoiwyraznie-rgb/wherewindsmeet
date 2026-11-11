from __future__ import annotations

import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest import mock

from tools import skan_timeline


SERIALIZED_TYPE = b"\x08\x0f\x00TimelinePObject"
BARE_LITERAL = b"TimelinePObject"
STORED = 0  # jak w tests/test_apply_translation.py: bez zależności od zstd


def container(payloads: list[bytes]) -> bytes:
    """Synthetic container in the documented layout: header, offsets, chunks.

    Header is `u32 magic | u32 version | u32 count`, then `u32[count+1]` offsets
    relative to the end of that table (the first one is 0 and shares the 16
    header bytes), and the last offset is a sentinel equal to the chunk area.
    Chunks are STORED, so no compressor is needed to build a fixture.
    """
    chunks = [struct.pack("<BII", STORED, len(raw), len(raw)) + raw for raw in payloads]
    offsets = [0]
    for chunk in chunks:
        offsets.append(offsets[-1] + len(chunk))
    header = struct.pack("<IIII", 0xDEADBEEF, 1, len(chunks), offsets[0])
    table = struct.pack(f"<{len(chunks)}I", *offsets[1:])
    return header + table + b"".join(chunks)


class ScanTimelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="wwm-skan-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = self.root / "oversea"
        self.data.mkdir()

    def write(self, name: str, payload: bytes, directory: Path | None = None) -> Path:
        path = (directory or self.data) / name
        path.write_bytes(payload)
        return path

    def scan(self, *roots: Path) -> dict:
        return skan_timeline.scan([*roots])

    def test_counts_only_serialized_type_field(self):
        # The bare literal inside a text must not be mistaken for a scene object.
        self.write("data201", container([b"index", SERIALIZED_TYPE * 3 + b"padding",
                                         SERIALIZED_TYPE * 2]))
        self.write("data202", container([b"index", BARE_LITERAL * 7]))
        report = self.scan(self.data)

        self.assertEqual(report["plikow"], 2)
        self.assertEqual(report["kontenerow"], 2)
        self.assertEqual(report["obiekty_razem"], 5)
        found = {row["plik"]: row["obiekty"] for row in report["z_timeline"]}
        self.assertEqual(found, {"oversea/data201": 5})
        self.assertEqual(report["bez_timeline"], ["oversea/data202"])
        self.assertEqual(report["poza_kontenerem"], [])

    def test_container_without_scenes_is_not_a_container_error(self):
        self.write("data200", container([b"index", b"only context tables"]))
        report = self.scan(self.data)
        self.assertEqual(report["obiekty_razem"], 0)
        self.assertEqual(report["bez_timeline"], ["oversea/data200"])
        self.assertEqual(report["poza_kontenerem"], [])

    def test_files_without_container_are_listed_separately(self):
        self.write("CameraZone.json", b'{"zones": []}')
        self.write("data201", container([b"index", SERIALIZED_TYPE]))
        report = self.scan(self.data)
        self.assertEqual(report["poza_kontenerem"], ["oversea/CameraZone.json"])
        self.assertEqual([row["plik"] for row in report["z_timeline"]], ["oversea/data201"])

    def test_broken_chunk_does_not_stop_the_scan(self):
        # One chunk cannot be decompressed: it is skipped, the rest still counts.
        self.write("data201", container([b"index", SERIALIZED_TYPE * 2, b"unused"]))
        original = skan_timeline.patcher.decompress

        def flaky(kind, payload):
            if payload == b"unused":
                raise RuntimeError("broken chunk")
            return original(kind, payload)

        with mock.patch.object(skan_timeline.patcher, "decompress", flaky):
            report = self.scan(self.data)
        self.assertEqual(report["kontenerow"], 1)
        self.assertEqual(report["obiekty_razem"], 2)
        self.assertEqual(report["poza_kontenerem"], [])

    def test_same_file_passed_twice_is_scanned_once(self):
        path = self.write("data201", container([b"index", SERIALIZED_TYPE * 4]))
        report = self.scan(self.data, path)
        self.assertEqual(report["plikow"], 1)
        self.assertEqual(report["obiekty_razem"], 4)

    def test_names_stay_relative_and_private_paths_do_not_leak(self):
        self.write("data201", container([b"index", SERIALIZED_TYPE]))
        nested = self.root / "patch" / "oversea"
        nested.mkdir(parents=True)
        self.write("data1200", container([b"index", SERIALIZED_TYPE * 2]), nested)
        report = self.scan(self.data, self.root / "patch")

        names = [row["plik"] for row in report["z_timeline"]]
        self.assertEqual(names, ["patch/oversea/data1200", "oversea/data201"])
        for name in names:
            self.assertNotIn(str(self.root), name)

    def test_report_is_json_serialisable_and_sorted_by_size(self):
        self.write("data201", container([b"index", SERIALIZED_TYPE]))
        self.write("data202", container([b"index", SERIALIZED_TYPE * 9]))
        report = self.scan(self.data)
        json.dumps(report)  # must not raise
        self.assertEqual([row["obiekty"] for row in report["z_timeline"]], [9, 1])

    def test_cli_reports_counts_without_private_paths(self):
        import contextlib
        import io

        self.write("data201", container([b"index", SERIALIZED_TYPE * 2]))
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = skan_timeline.main([str(self.data)])
        self.assertEqual(code, 0)
        report = json.loads(buffer.getvalue())
        self.assertEqual(report["obiekty_razem"], 2)
        self.assertNotIn(str(self.root), buffer.getvalue())


if __name__ == "__main__":
    unittest.main()
