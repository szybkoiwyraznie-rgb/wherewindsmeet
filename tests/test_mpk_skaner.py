"""Testy skanera paczek WWM (`tools/mpk_skaner.py`).

Tylko dane syntetyczne: paczki i indeksy budowane w tmp_path; żadnych
prawdziwych plików gry. Pokrywamy: `murmur3_32`/`file_id`, parser
`.mpkinfo` v3, `Patch.mpkdb` (SQLite), haszowanie kandydatów i pełny
przebieg `main()` na sztucznej instalacji.
"""

from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import struct
import unittest

from tools import mpk_skaner as ms


def _mpkinfo_bytes(entries: list[tuple[int, int, int, int, int]]) -> bytes:
    out = [struct.pack("<II", 3, len(entries))]
    for e in entries:
        out.append(struct.pack("<IIIII", *e))
    out.append(b"\0" * 16)
    return b"".join(out)


class TestFileId(unittest.TestCase):
    def test_murmur3_pusty(self):
        self.assertEqual(ms.murmur3_32(b""), 0)

    def test_murmur3_deterministyczny(self):
        self.assertEqual(ms.murmur3_32(b"client/a.etsb"), ms.murmur3_32(b"client/a.etsb"))
        self.assertNotEqual(ms.murmur3_32(b"client/a.etsb", 0), ms.murmur3_32(b"client/a.etsb", 1))

    def test_strip_ext(self):
        self.assertEqual(ms.strip_ext(b"a/b/c.cine"), b"a/b/c")
        self.assertEqual(ms.strip_ext(b"a.b/cdef"), b"a.b/cdef")
        self.assertEqual(ms.strip_ext(b"x"), b"x")

    def test_tail_sig(self):
        self.assertEqual(ms.tail_sig(b""), 0)
        self.assertEqual(ms.tail_sig(b"a"), (ord("a") << 24) | 1)
        self.assertEqual(ms.tail_sig(b"ab"), (ord("b") << 24) | (ord("a") << 16) | 2)
        self.assertEqual(
            ms.tail_sig(b"qhrw/sq001_zlxl"),
            (ord("l") << 24) | (ord("x") << 16) | (ord("l") << 8) | (len("qhrw/sq001_zlxl") & 0xFF),
        )

    def test_file_id_sklada_sie_z_murmur_i_tail(self):
        path = "client/dialogs/hjt/sxd_lingwei.etsb"
        fid = ms.file_id(path)
        p = path.encode()
        self.assertEqual(fid >> 32, ms.murmur3_32(p))
        self.assertEqual(fid & 0xFFFFFFFF, ms.tail_sig(ms.strip_ext(p)))

    def test_file_id_guid_fast_path(self):
        guid = "e8c8d4c0-0a56-499c-8243-0c93127c7fd3"
        path = f"e8/{guid}.6"
        fid = ms.file_id(path)
        stripped = path.encode()[: -len(".6")]
        self.assertEqual(stripped[2:3], b"/")
        self.assertEqual(len(stripped), 39)
        self.assertEqual(fid & 0xFFFFFFFF, struct.unpack(">I", stripped[3:7])[0])


class TestMpkinfo(unittest.TestCase):
    def _instalacja_z_indeksem(self, tmp: Path) -> Path:
        root = tmp / "gra"
        root.mkdir()
        (root / "Resources.mpk").write_bytes(b"EZST" + b"\0" * 96)
        path = "client/dialogs/hjt/sxd_lingwei.etsb"
        fid = ms.file_id(path)
        entry = (fid & 0xFFFFFFFF, fid >> 32, 0, 100, 0)
        placeholder = (1, 2, 0, 0, 1)
        (root / "Resources.mpkinfo").write_bytes(_mpkinfo_bytes([entry, placeholder]))
        return root

    def test_parsuj_ok(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            root = self._instalacja_z_indeksem(Path(td))
            meta = ms.parsuj_mpkinfo(root, root / "Resources.mpkinfo")
            self.assertTrue(meta["ok"], meta.get("powod"))
            self.assertEqual(meta["wpisow"], 1)
            self.assertEqual(meta["placeholdery"], 1)
            self.assertEqual(meta["wpisow_surowych"], 2)
            kontener = meta["kontenery"][0]
            self.assertTrue(kontener["istnieje"])
            self.assertTrue(kontener["offsety_fizyczne"])
            self.assertEqual(kontener["pokrycie_pct"], 100.0)

    def test_parsuj_zla_wersja(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "Resources.mpkinfo").write_bytes(
                struct.pack("<II", 2, 0) + b"\0" * 16
            )
            meta = ms.parsuj_mpkinfo(root, root / "Resources.mpkinfo")
            self.assertFalse(meta["ok"])
            self.assertIn("wersja", meta["powod"])

    def test_parsuj_zla_dlugosc(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "Resources.mpkinfo").write_bytes(struct.pack("<II", 3, 1) + b"\0" * 8)
            meta = ms.parsuj_mpkinfo(root, root / "Resources.mpkinfo")
            self.assertFalse(meta["ok"])
            self.assertIn("długość", meta["powod"])


class TestMpkdb(unittest.TestCase):
    def test_parsuj_syntetyczna_baze(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "Patch.mpkdb"
            con = sqlite3.connect(db)
            con.execute("CREATE TABLE info0 (v0 INTEGER, v1 INTEGER, v2 INTEGER, v3 INTEGER, v6 INTEGER)")
            con.execute("CREATE TABLE info1 (v0 INTEGER, v1 INTEGER, v2 INTEGER, v3 INTEGER, v6 INTEGER)")
            con.execute("INSERT INTO info0 VALUES (-1, 100, 3, 0, 0)")  # signed i64
            con.execute("INSERT INTO info1 VALUES (5, 200, 4, 0, 400)")
            con.commit()
            con.close()
            meta = ms.parsuj_mpkdb(db)
            self.assertTrue(meta["ok"], meta.get("powod"))
            self.assertEqual(meta["wpisow"], 2)
            self.assertEqual(meta["tabele"]["info0"]["wierszy"], 1)
            fids = meta["_fids"]
            self.assertIn((1 << 64) - 1, fids)
            self.assertIn(5, fids)

    def test_nie_sqlite(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "Patch.mpkdb"
            db.write_bytes(b"nie-sqlite")
            meta = ms.parsuj_mpkdb(db)
            self.assertFalse(meta["ok"])


class TestHaszowanie(unittest.TestCase):
    def test_trafienie_i_pudlo(self):
        path = "client/dialogs/hjt/sxd_lingwei.etsb"
        fid = ms.file_id(path)
        lookup = {fid: {"file_id": fid, "offset": 0, "size": 10, "pack_id": 0}}
        traf = ms.haszuj_kandydatow(
            [{"sciezka": path, "pochodzenie": "poi_storyline"},
             {"sciezka": "client/nie/ma.etsb", "pochodzenie": "poi_storyline"}],
            [("Resources.mpkinfo", lookup)],
            [("Patch.mpkdb", {fid})],
        )
        self.assertEqual(len(traf), 2)  # mpkinfo + mpkdb dla tej samej ścieżki
        self.assertTrue(all(t["sciezka"] == path for t in traf))


class TestIntegracja(unittest.TestCase):
    def test_pelny_przebieg_na_syntetycznej_instalacji(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "gra"
            root.mkdir()
            (root / "Resources.mpk").write_bytes(b"EZST" + b"\0" * 96)
            path = "client/dialogs/hjt/sxd_lingwei.etsb"
            fid = ms.file_id(path)
            entry = (fid & 0xFFFFFFFF, fid >> 32, 0, 100, 0)
            (root / "Resources.mpkinfo").write_bytes(_mpkinfo_bytes([entry]))
            patch = root / "LocalData" / "Patch"
            patch.mkdir(parents=True)
            db = patch / "Patch.mpkdb"
            con = sqlite3.connect(db)
            con.execute("CREATE TABLE info0 (v0 INTEGER, v1 INTEGER, v2 INTEGER, v3 INTEGER, v6 INTEGER)")
            con.execute("INSERT INTO info0 VALUES (?, 100, 1, 0, 0)", ((fid - (1 << 64),)))
            con.commit()
            con.close()

            kandydaci = Path(td) / "kandydaci.jsonl"
            kandydaci.write_text(
                json.dumps({"sciezka": path, "pochodzenie": "poi_storyline"}, ensure_ascii=False) + "\n"
                + json.dumps({"sciezka": "client/brak.etsb", "pochodzenie": "cine_wzorzec"}, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            # LT1.mpk: dwa surowe bloki EZST-like
            lt1_blok_1 = b"EZST" + struct.pack("<I", 10) + b"\x11" * 64
            lt1_blok_2 = b"ZSTD" + struct.pack("<I", 20) + b"\x22" * 128
            (patch / "LT1.mpk").write_bytes(lt1_blok_1 + lt1_blok_2)
            lt1_fid_1 = ms.file_id("client/scripts/a.lua")
            lt1_fid_2 = ms.file_id("client/scripts/b.lua")
            lt1_entries = [
                (lt1_fid_1 & 0xFFFFFFFF, lt1_fid_1 >> 32, 0, len(lt1_blok_1), 1 << 1),
                (lt1_fid_2 & 0xFFFFFFFF, lt1_fid_2 >> 32, len(lt1_blok_1), len(lt1_blok_2), 1 << 1),
            ]
            (patch / "LT1.mpkinfo").write_bytes(_mpkinfo_bytes(lt1_entries))

            wyjscie = Path(td) / "wynik"
            rc = ms.main(
                ["--gra", str(root), "--wyjscie", str(wyjscie),
                 "--kandydaci", str(kandydaci), "--non-interactive"]
            )
            self.assertEqual(rc, 0)
            raport = json.loads((wyjscie / "RAPORT.json").read_text(encoding="utf-8"))
            self.assertTrue(raport["mpkinfo"][0]["ok"])
            self.assertTrue(raport["mpkdb"][0]["ok"])
            self.assertEqual(len(raport["trafienia_kandydatow"]), 2)
            self.assertTrue((wyjscie / "PODSUMOWANIE.txt").is_file())
            self.assertTrue((Path(td) / "WWM_MPK_Skaner_WYNIK.zip").is_file())
            podpis = (Path(td) / "WWM_MPK_Skaner_WYNIK.zip").read_bytes()
            self.assertTrue(podpis[:2] == b"PK")
            # wycinanie: 1 blok z trafień (mpkdb nie ma offsetu) + 2 z LT1
            wyciete = sorted((wyjscie / "wyciete").glob("*.bin"))
            etykiety = sorted(p.name.split("_", 1)[0] for p in wyciete)
            self.assertEqual(etykiety.count("trafienie"), 1)
            self.assertEqual(etykiety.count("lt1"), 2)
            surowy_lt1 = b"".join(p.read_bytes() for p in wyciete if p.name.startswith("lt1_"))
            self.assertIn(lt1_blok_1, surowy_lt1)
            self.assertIn(lt1_blok_2, surowy_lt1)
            surowe_traf = [p for p in wyciete if p.name.startswith("trafienie_")]
            self.assertEqual(surowe_traf[0].read_bytes(), b"EZST" + b"\0" * 96)
            zrzut = json.loads((wyjscie / "mpkdb_dump.json").read_text(encoding="utf-8"))
            self.assertTrue(zrzut["ok"])
            self.assertEqual(len(zrzut["tabele"]["info0"]["wiersze"]), 1)
            self.assertTrue(raport["wycinanie"][0]["ok"] >= 1)
            self.assertTrue(raport["wycinanie"][1]["ok"] == 2)
            self.assertTrue(raport["mpkdb_zrzut"]["ok"])

    def test_patch_mpkdb_z_blobami_nie_wywraca_json(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "gra"
            root.mkdir()
            (root / "Resources.mpk").write_bytes(b"EZST" + b"\0" * 32)
            fid = ms.file_id("client/x.etsb")
            entry = (fid & 0xFFFFFFFF, fid >> 32, 0, 36, 0)
            (root / "Resources.mpkinfo").write_bytes(_mpkinfo_bytes([entry]))
            patch = root / "LocalData" / "Patch"
            patch.mkdir(parents=True)
            db = patch / "Patch.mpkdb"
            con = sqlite3.connect(db)
            con.execute("CREATE TABLE meta (key TEXT, val BLOB)")
            con.execute("INSERT INTO meta VALUES ('version', ?)", (b"\xde\xad\xbe\xef" * 40,))
            con.execute("CREATE TABLE pak (v0 INTEGER, v1 BLOB, v2 INTEGER)")
            con.execute("INSERT INTO pak VALUES (?, ?, 3109)", ((1 << 63) - 1, b"\x01" * 300))
            con.commit()
            con.close()

            wyjscie = Path(td) / "wynik"
            rc = ms.main(["--gra", str(root), "--wyjscie", str(wyjscie), "--non-interactive"])
            self.assertEqual(rc, 0)
            zrzut = json.loads((wyjscie / "mpkdb_dump.json").read_text(encoding="utf-8"))
            self.assertTrue(zrzut["ok"])
            val = zrzut["tabele"]["meta"]["wiersze"][0][1]
            self.assertTrue(val["__bytes__"])
            self.assertEqual(val["rozmiar"], 160)
            self.assertEqual(bytes.fromhex(val["hex"]), b"\xde\xad\xbe\xef" * 40)
            pak_blob = zrzut["tabele"]["pak"]["wiersze"][0][1]
            self.assertTrue(pak_blob["__bytes__"])
            self.assertTrue(pak_blob["uciniete"])
            self.assertEqual(pak_blob["rozmiar"], 300)
            self.assertTrue((Path(td) / "WWM_MPK_Skaner_WYNIK.zip").is_file())

    def test_brak_katalogu_gry(self):
        rc = ms.main(["--gra", "/nie/istnieje/12345", "--non-interactive"])
        self.assertEqual(rc, 2)


class TestSkanujBat(unittest.TestCase):
    """Statyczna kontrola szablonu SKANUJ.bat (regresja: inwokacja bez cudzysłowów)."""

    def setUp(self):
        from tools import build_mpk_skaner as bmk

        self.bmk = bmk
        self.bat = bmk.BAT_TEMPLATE

    def test_pyexe_nie_jest_w_cudzyslowach_przy_wywolaniu(self):
        self.assertNotIn('"%PYEXE%"', self.bat)
        self.assertIn('%PYEXE% "narzedzia\\mpk_skaner.py"', self.bat)

    def test_bat_czysto_ascii_i_crlf(self):
        surowe = self.bmk._windows_lines(self.bat)
        surowe.decode("ascii")
        self.assertNotIn(b"\n", surowe.replace(b"\r\n", b""))

    def test_kolejnosc_odkrywania_pythona(self):
        idx_py = self.bat.index("py -3 -c")
        idx_python = self.bat.index("python -c")
        idx_wyw = self.bat.index('%PYEXE% "narzedzia')
        self.assertLess(idx_py, idx_python)
        self.assertLess(idx_python, idx_wyw)


if __name__ == "__main__":
    unittest.main()
