from __future__ import annotations

import struct
import tempfile
import unittest
from pathlib import Path

from tests.test_apply_translation import container, table
from tools import apply_translation as patcher
from tools import mapa_tekstow

NONE = 0xFFFFFFFF


def diff_container(buckets: list[int], total: int, tables: list[bytes]) -> bytes:
    """Warstwa `_diff`: nagłówek z liczbą kubełków bazy i chunki samych zmian."""
    header = struct.pack("<QQ", total, len(buckets)) + struct.pack(f"<{len(buckets)}I", *buckets)
    chunks = [patcher.build_chunk(patcher.STORED, header, 0)]
    chunks += [patcher.build_chunk(patcher.STORED, data, 0) for data in tables]
    return patcher.build_container(chunks)


class TextMapTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="wwm-mapa-")
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)

    def write(self, name: str, data: bytes) -> Path:
        path = self.root / name
        path.write_bytes(data)
        return path

    def test_key_is_stable_and_depends_only_on_text(self):
        self.assertEqual(mapa_tekstow.klucz("zażółć"), mapa_tekstow.klucz("zażółć"))
        self.assertNotEqual(mapa_tekstow.klucz("a"), mapa_tekstow.klucz("b"))
        self.assertEqual(len(mapa_tekstow.klucz("a")), 16)
        self.assertEqual(mapa_tekstow.klucz("a"), "ca978112ca1bbdca")

    def test_base_map_with_metadata_chunk(self):
        base = self.write("mapa", container([table([(1, b"raz"), None]), table([(2, "dwa ż".encode())])], with_metadata=True))
        self.assertEqual(mapa_tekstow.wczytaj(base), {1: "raz", 2: "dwa ż"})

    def test_diff_header_is_recognised_although_bucket_count_differs_from_chunk_count(self):
        # 6 kubełków bazy, tylko 2 chunki zmian: stary test rozmiaru brał nagłówek za tabelę
        data = diff_container([1, NONE, NONE, 2, NONE, NONE], 3, [table([(1, b"nowy")]), table([(9, b"x")])])
        chunks = patcher.read_container(data)
        self.assertTrue(patcher.is_metadata_chunk(chunks[0], len(chunks)))
        self.assertFalse(patcher.is_metadata_chunk(chunks[1], len(chunks)))

    def test_layers_replace_add_and_delete(self):
        base = self.write("mapa", container([table([(1, b"stary"), (2, b"zostaje"), (3, b"znika")])], with_metadata=True))
        diff = self.write(
            "mapa_diff",
            diff_container([1], 3, [table([(1, b"nowy"), (3, b"\xff"), (4, b"dodany")])]),
        )
        self.assertEqual(mapa_tekstow.zloz([base, diff]), {1: "nowy", 2: "zostaje", 4: "dodany"})
        layer, removed = mapa_tekstow.wczytaj_warstwe(diff)
        self.assertEqual(removed, {3})
        self.assertEqual(layer, {1: "nowy", 4: "dodany"})

    def test_later_layer_can_restore_a_deleted_text(self):
        base = self.write("mapa", container([table([(1, b"a")])], with_metadata=True))
        first = self.write("d1", diff_container([1], 0, [table([(1, b"\xff")])]))
        second = self.write("d2", diff_container([1], 1, [table([(1, b"b")])]))
        self.assertEqual(mapa_tekstow.zloz([base, first, second]), {1: "b"})

    def test_unreadable_file_raises_map_error(self):
        broken = self.write("zepsuta", b"\x00" * 40)
        with self.assertRaises(mapa_tekstow.MapaError):
            mapa_tekstow.wczytaj(broken)
        with self.assertRaises(mapa_tekstow.MapaError):
            mapa_tekstow.wczytaj(self.root / "nie_ma")

    def test_sha256_of_file(self):
        path = self.write("plik", b"abc")
        self.assertEqual(
            mapa_tekstow.sha256_pliku(path), "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
        )


if __name__ == "__main__":
    unittest.main()
