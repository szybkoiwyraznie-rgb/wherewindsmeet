from __future__ import annotations

import io
import json
import struct
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from tools import apply_translation as patcher
from tools import baza_gry


# Wszystkie dane poniżej są wymyślone; testy nie używają plików gry.


def tagged(value) -> bytes:
    """Zakoduj wartość tak, jak robi to serializator gry (na potrzeby testów)."""
    if value is None:
        return b"\x0b"
    if value is False:
        return b"\x0c"
    if value is True:
        return b"\x0d"
    if isinstance(value, int):
        if value < 0x100:
            return b"\x01" + bytes([value])
        if value < 0x10000:
            return b"\x02" + struct.pack("<H", value)
        if value < 0x100000000:
            return b"\x03" + struct.pack("<I", value)
        return b"\x04" + struct.pack("<Q", value)
    if isinstance(value, float):
        return b"\x06" + struct.pack("<d", value)
    if isinstance(value, str):
        raw = value.encode("utf-8")
        return b"\x08" + struct.pack("<H", len(raw)) + raw
    if isinstance(value, list):
        return b"\x09" + struct.pack("<H", len(value)) + b"".join(tagged(item) for item in value)
    if isinstance(value, dict):
        body = b"".join(tagged(key) + tagged(item) for key, item in value.items())
        return b"\x0a" + struct.pack("<H", 2 * len(value)) + body
    raise TypeError(type(value))


def struct_row(fields: list[tuple[int, object]]) -> bytes:
    out = struct.pack("<H", len(fields))
    for column, value in fields:
        encoded = tagged(value)
        out += struct.pack("<H", column | (encoded[0] << 10)) + encoded[1:]
    return out


def pad8(raw: bytes) -> bytes:
    return raw + b"\x00" * (-len(raw) % 8)


def container(chunks: list[bytes]) -> bytes:
    return patcher.build_container([patcher.build_chunk(patcher.STORED, chunk, 0) for chunk in chunks])


def schema_chunk(columns: list[str]) -> bytes:
    out = struct.pack("<H", len(columns))
    for name in columns:
        raw = name.encode("utf-8")
        out += struct.pack("<H", len(raw)) + raw
    return out


def index_chunk(rows: list[tuple[object, tuple[int, int, int, int]]], capacity: int = 7,
                declared: int | None = None) -> bytes:
    ctrl = bytearray(b"\x80" * max(capacity + 17, 24))
    entries = bytearray(16 * capacity)
    tail = b""
    for slot, (key, place) in enumerate(rows):
        ctrl[slot] = 0x11
        base = 16 * slot
        if isinstance(key, int):
            struct.pack_into("<Q", entries, base, key)
        else:
            raw = key.encode("utf-8")
            struct.pack_into("<II", entries, base, 16 * capacity - base + len(tail), len(raw))
            tail += raw
        struct.pack_into("<4H", entries, base + 8, *place)
    used = len(rows) if declared is None else declared
    return struct.pack("<QQQ", capacity, used, 0x608DDB2C) + bytes(ctrl) + bytes(entries) + tail


def manifest_chunk(tables: list[dict], extra_names: tuple[list[str], list[str]] = ([], []),
                   index_files=("index1",), data_files=("data1",)) -> bytes:
    names = [table["name"] for table in tables] + extra_names[0] + extra_names[1]
    parts: list[tuple[int, int]] = []
    records = b""
    for table in tables:
        first = len(parts)
        parts.extend(part if len(part) == 4 else (*part, 0xFFFF, 0xFFFF) for part in table["parts"])
        schema = table.get("schema") or (0xFFFF, 0xFFFF)
        schema_fix = table.get("schema_fix") or (0xFFFF, 0xFFFF)
        records += struct.pack("<IIHHHHIIII", table["rows"], len(table["parts"]), schema[0], schema[1],
                               schema_fix[0], schema_fix[1], 0, 0, first, table["flags"])
    out = struct.pack("<HHIIIII", 1, 1, 8, len(tables), len(parts), len(extra_names[0]), len(extra_names[1]))
    for name in names:
        raw = name.encode("ascii")
        out += pad8_from(len(out), struct.pack("<H", len(raw)) + raw)
    out += records
    out += b"".join(struct.pack("<HHHH", *part) for part in parts)
    for group in (index_files, data_files):
        out += struct.pack("<I", len(group))
        for name in group:
            out += struct.pack("<H", len(name)) + name.encode("ascii")
    return out


def pad8_from(position: int, raw: bytes) -> bytes:
    return raw + b"\x00" * (-(position + len(raw)) % 8)


DIALOG = {"Type": "Scena", "linie": [{"mowca": "Ala", "tekst": 0x1122334455667788}], "czas": 1.5,
          "puste": None, "tak": True, "nie": False, 7: "klucz liczbowy"}
CONFIG = {"numer": 70000, "nazwa": "zażółć"}


def build_database(directory: Path, *, declared_rows: int = 2, bad_tag: bool = False) -> None:
    value_a = pad8(tagged(DIALOG))
    value_b = pad8(tagged(CONFIG)) if not bad_tag else pad8(b"\x7f\x00")
    row_1 = pad8(struct_row([(0, 5), (1, "pierwszy"), (2, True)]))
    row_2 = pad8(struct_row([(0, 300), (2, None)]))
    data = value_a + value_b + row_1 + row_2
    words = [len(value_a) // 8, len(value_b) // 8, len(row_1) // 8, len(row_2) // 8]
    offsets = [0, words[0], words[0] + words[1], words[0] + words[1] + words[2]]
    (directory / "data1").write_bytes(container([data]))
    (directory / "index1").write_bytes(container([
        index_chunk([("timeline", (1, 0, offsets[0], words[0])), ("config", (1, 0, offsets[1], words[1]))]),
        schema_chunk(["id", "opis", "aktywny"]),
        index_chunk([(5, (1, 0, offsets[2], words[2])), (300, (1, 0, offsets[3], words[3]))]),
    ]))
    manifest = manifest_chunk(
        [
            {"name": "dialogi.1", "rows": declared_rows, "parts": [(1, 0)], "flags": 0x801},
            {"name": "rzeczy", "rows": 2, "parts": [(1, 2)], "schema": (1, 1), "flags": 0x400},
        ],
        extra_names=(["bez.rekordu"], ["inne.bez", "jeszcze.jedno"]),
    )
    (directory / "MANIFEST").write_bytes(container([manifest]))


class ValueTests(unittest.TestCase):
    def test_tagged_values_round_trip(self):
        raw = tagged(DIALOG)
        value, end = baza_gry.read_value(raw, 0)
        self.assertEqual(end, len(raw))
        self.assertEqual(value, DIALOG)
        self.assertEqual(list(value), list(DIALOG))  # kolejność pól jak w pliku

    def test_unknown_tag_is_an_error(self):
        with self.assertRaisesRegex(baza_gry.BazaError, "nieznany typ 0x7f"):
            baza_gry.read_value(b"\x7f\x00\x00", 0)

    def test_truncated_value_is_an_error(self):
        with self.assertRaises(baza_gry.BazaError):
            baza_gry.read_value(tagged("dłuższy napis")[:-3], 0)
        with self.assertRaises(baza_gry.BazaError):
            baza_gry.read_value(b"\x03\x01", 0)

    def test_struct_row_uses_ten_bit_column_numbers(self):
        columns = [f"k{number}" for number in range(400)]
        raw = struct_row([(0, 1), (299, "daleko"), (399, [1, 2])])
        row, end = baza_gry.read_row(raw, 0, columns)
        self.assertEqual(end, len(raw))
        self.assertEqual(row, {"k0": 1, "k299": "daleko", "k399": [1, 2]})

    def test_struct_row_rejects_column_outside_schema(self):
        with self.assertRaisesRegex(baza_gry.BazaError, "poza schematem"):
            baza_gry.read_row(struct_row([(3, 1)]), 0, ["a", "b"])


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="wwm-baza-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_reads_tables_with_and_without_schema(self):
        build_database(self.root)
        baza = baza_gry.Baza([self.root])
        self.assertEqual(set(baza.tabele), {"dialogi.1", "rzeczy"})
        self.assertEqual(baza.manifest.bez_rekordu, ("bez.rekordu", "inne.bez", "jeszcze.jedno"))
        self.assertEqual(baza.manifest.pliki_danych, ("data1",))
        self.assertIsNone(baza.kolumny("dialogi.1"))
        self.assertEqual(dict(baza.wiersze("dialogi.1")), {"timeline": DIALOG, "config": CONFIG})
        self.assertEqual(baza.kolumny("rzeczy"), ["id", "opis", "aktywny"])
        self.assertEqual(
            dict(baza.wiersze("rzeczy")),
            {5: {"id": 5, "opis": "pierwszy", "aktywny": True}, 300: {"id": 300, "aktywny": None}},
        )

    def test_row_count_mismatch_is_reported(self):
        build_database(self.root, declared_rows=3)
        baza = baza_gry.Baza([self.root])
        with self.assertRaisesRegex(baza_gry.BazaError, "MANIFEST podaje 3 wierszy, indeks ma 2"):
            list(baza.wiersze("dialogi.1"))

    def test_unknown_value_tag_stops_the_table(self):
        build_database(self.root, bad_tag=True)
        baza = baza_gry.Baza([self.root])
        with self.assertRaisesRegex(baza_gry.BazaError, "nieznany typ"):
            list(baza.wiersze("dialogi.1"))
        report = baza_gry.sprawdz(baza)
        self.assertEqual(report["tabel_odczytanych"], 1)
        self.assertEqual(report["tabel_z_bledem"], 1)

    def test_value_must_end_inside_its_interval(self):
        build_database(self.root)
        baza = baza_gry.Baza([self.root])
        place = next(place for key, place in baza.polozenia("dialogi.1") if key == "timeline")
        short = baza_gry.Polozenie(place.plik, place.chunk, place.offset, place.dlugosc - 1)
        with self.assertRaisesRegex(baza_gry.BazaError, "kończy się"):
            baza.wartosc("dialogi.1", short)

    def test_index_slot_count_must_match_header(self):
        chunk = index_chunk([("a", (1, 0, 0, 1))], declared=2)
        with self.assertRaisesRegex(baza_gry.BazaError, "nagłówek podaje 2"):
            list(baza_gry.iter_index(chunk, False))

    def test_later_directory_overrides_earlier(self):
        base = self.root / "base"
        patch = self.root / "patch"
        base.mkdir()
        patch.mkdir()
        build_database(base)
        build_database(patch, bad_tag=True)
        self.assertEqual(dict(baza_gry.Baza([patch, base]).wiersze("dialogi.1"))["config"], CONFIG)
        with self.assertRaises(baza_gry.BazaError):
            list(baza_gry.Baza([base, patch]).wiersze("dialogi.1"))

    def test_missing_files_are_errors(self):
        build_database(self.root)
        (self.root / "data1").unlink()
        baza = baza_gry.Baza([self.root])
        with self.assertRaisesRegex(baza_gry.BazaError, "brak pliku data1"):
            list(baza.wiersze("rzeczy"))
        with self.assertRaisesRegex(baza_gry.BazaError, "brak tabeli"):
            baza.tabela("nie.ma")
        with self.assertRaisesRegex(baza_gry.BazaError, "brak katalogu"):
            baza_gry.Baza([self.root / "nie-istnieje"])

    def test_update_layer_replaces_adds_and_deletes_rows(self):
        old = pad8(tagged({"wersja": 1}))
        new = pad8(tagged({"wersja": 2}))
        added = pad8(tagged({"wersja": 3}))
        row = pad8(struct_row([(0, 7), (1, "kolumna dopisana")]))
        (self.root / "data1").write_bytes(container([old * 3]))
        (self.root / "data9").write_bytes(container([new + added + row]))
        words, row_words = len(old) // 8, len(row) // 8
        (self.root / "index1").write_bytes(container([
            index_chunk([("a", (1, 0, 0, words)), ("b", (1, 0, words, words)), ("c", (1, 0, 2 * words, words))]),
            schema_chunk(["id"]),
            index_chunk([(7, (9, 0, 2 * words, row_words))]),
        ]))
        (self.root / "index9").write_bytes(container([
            # zamiana `b`, skasowanie `c` (plik 0, długość 0), dopisanie `d`
            index_chunk([("b", (9, 0, 0, words)), ("c", (0, 0, 0, 0)), ("d", (9, 0, words, words))]),
            schema_chunk(["opis"]),
        ]))
        manifest = manifest_chunk(
            [
                {"name": "warstwy", "rows": 3, "parts": [(1, 0, 9, 0)], "flags": 0x801},
                {"name": "schemat", "rows": 1, "parts": [(1, 2)], "schema": (1, 1), "schema_fix": (9, 1),
                 "flags": 0x400},
            ],
            index_files=("index1", "index9"), data_files=("data1", "data9"),
        )
        (self.root / "MANIFEST").write_bytes(container([manifest]))
        baza = baza_gry.Baza([self.root])
        self.assertEqual(
            dict(baza.wiersze("warstwy")),
            {"a": {"wersja": 1}, "b": {"wersja": 2}, "d": {"wersja": 3}},
        )
        self.assertEqual(baza.kolumny("schemat"), ["id", "opis"])
        self.assertEqual(dict(baza.wiersze("schemat")), {7: {"id": 7, "opis": "kolumna dopisana"}})
        self.assertEqual(baza_gry.podsumowanie(baza)["czesci_z_poprawkami"], 1)

    def test_cli_summary_table_and_check(self):
        build_database(self.root)
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(baza_gry.main([str(self.root)]), 0)
        summary = json.loads(out.getvalue())
        self.assertEqual((summary["tabel"], summary["wierszy"], summary["nazw_bez_rekordu"]), (2, 4, 3))
        self.assertEqual(summary["brakujace_pliki"], [])

        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(baza_gry.main([str(self.root), "--tabela", "rzeczy", "--limit", "1"]), 0)
        rows = [json.loads(line) for line in out.getvalue().splitlines()]
        self.assertEqual(rows, [{"klucz": 5, "wartosc": {"id": 5, "opis": "pierwszy", "aktywny": True}}])

        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(baza_gry.main([str(self.root), "--tabele", "rz"]), 0)
        self.assertEqual(out.getvalue(), "rzeczy\t2\tid,opis,aktywny\n")

        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            self.assertEqual(baza_gry.main([str(self.root), "--sprawdz"]), 0)
        self.assertEqual(json.loads(out.getvalue())["wierszy_odczytanych"], 4)

    def test_cli_reports_errors_with_exit_code(self):
        err = io.StringIO()
        with redirect_stderr(err):
            self.assertEqual(baza_gry.main([str(self.root / "pusto")]), 2)
        self.assertIn("BŁĄD", err.getvalue())


if __name__ == "__main__":
    unittest.main()
