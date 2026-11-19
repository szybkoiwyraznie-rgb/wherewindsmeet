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
            # sonda EZST (v7) przebiegła po jedynym wpisie Resources.mpkinfo
            # (wynik zależy od dostępności zstd, ale sondowanie — nie)
            self.assertEqual(raport["ezst_sonda"]["sondowanych"], 1)
            self.assertEqual(raport["ezst_sonda"]["magie"], {"EZST": 1})
            self.assertIn("ezst_sonda", json.loads(json.dumps(raport)))

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


class TestAesEzst(unittest.TestCase):
    """AES-256-ECB w czystym Pythonie (prefiks bloków EZST, sonda v7)."""

    def test_wektor_nist_aes256_ecb(self):
        # NIST SP 800-38A, F.1.5/F.1.6 (ECB-AES256)
        klucz = bytes.fromhex(
            "603deb1015ca71be2b73aef0857d77811f352c073b6108d72d9810a30914dff4"
        )
        jawny = bytes.fromhex("6bc1bee22e409f96e93d7e117393172a")
        szyfr = bytes.fromhex("f3eed1bdb5d2a03c064b5a7e3db181f8")
        rundy = ms._aes256_klucze_rund(klucz)
        self.assertEqual(ms._aes_blok_szyfruj(jawny, rundy), szyfr)
        self.assertEqual(ms._aes_blok_odszyfruj(szyfr, rundy), jawny)

    def test_prefiks_ezst_tam_i_z_powrotem(self):
        for dlugosc in (0, 7, 16, 100, 256, 300, 1000):
            payload = bytes(range(256))[:dlugosc] if dlugosc <= 256 else bytes(
                i % 251 for i in range(dlugosc)
            )
            zaszyfrowany = ms.ezst_zaszyfruj_prefiks(payload)
            self.assertEqual(ms.ezst_odszyfruj_prefiks(zaszyfrowany), payload)
            n = min(len(payload) // 16 * 16, 256)
            # część poza prefiksem zostaje nietknięta
            self.assertEqual(zaszyfrowany[n:], payload[n:])
            if n:
                self.assertNotEqual(zaszyfrowany[:n], payload[:n])


class TestSondaEzst(unittest.TestCase):
    """Sonda zawartości bloków EZST (v7) — dane syntetyczne, bez prawdziwego zstd.

    CI nie ma modułu zstd, więc dekompresję podstawiamy zlib-ową atrapą
    o tym samym interfejsie (dane, max_wyjscie) -> bytes. Prawdziwy backend
    (`compression.zstd` / `zstandard`) ma identyczny kontrakt.
    """

    def _instalacja(self, td: str, bloki: list[bytes]):
        root = Path(td) / "gra"
        root.mkdir()
        pak = b"".join(bloki)
        (root / "Resources.mpk").write_bytes(pak)
        entries = []
        offset = 0
        for i, blok in enumerate(bloki):
            fid = ms.file_id(f"syn/blk{i}.bin")
            entries.append((fid & 0xFFFFFFFF, fid >> 32, offset, len(blok), 0))
            offset += len(blok)
        (root / "Resources.mpkinfo").write_bytes(_mpkinfo_bytes(entries))
        meta = ms.parsuj_mpkinfo(root, root / "Resources.mpkinfo")
        return root, meta, meta.pop("_entries")

    def _ezst_zlib(self, tresc: bytes) -> bytes:
        import zlib

        skompresowane = zlib.compress(tresc, 6)
        return b"EZST" + struct.pack("<I", len(tresc)) + ms.ezst_zaszyfruj_prefiks(
            skompresowane
        )

    def test_sonda_z_atrapa_backendu(self):
        import tempfile
        import zlib

        def atrapa_backend():
            def dek(dane: bytes, max_wyjscie: int) -> bytes:
                try:
                    return zlib.decompressobj().decompress(dane, max_wyjscie)
                except zlib.error:
                    return b""

            return ("zlib-atrapa", dek)

        bloki = [
            self._ezst_zlib(b'{"Variables": {"a": 1}} GameLevelStorylineDialogsPlayNode' + b" " * 500),
            self._ezst_zlib(bytes.fromhex("c159410d") + b"\x02Entity\x00Camera\x00" + b"\xab" * 300),
            self._ezst_zlib(b"\x00" * 400),  # bez sygnatur
            b"RAWW" + struct.pack("<I", 4700001) * 4,  # goły blok z benchmarkiem
        ]
        oryginalny = ms._zstd_backend
        ms._zstd_backend = atrapa_backend
        try:
            with tempfile.TemporaryDirectory() as td:
                root, meta, entries = self._instalacja(td, bloki)
                wyjscie = Path(td) / "wynik"
                wynik = ms.skanuj_ezst_w_indeksie(root, wyjscie, meta, entries)
                self.assertEqual(wynik["backend_zstd"], "zlib-atrapa")
                self.assertEqual(wynik["sondowanych"], 4)
                self.assertEqual(wynik["magie"], {"EZST": 3, "gole": 1})
                self.assertEqual(wynik["trafien"], 3)
                self.assertEqual(wynik["wycietych"], 3)
                self.assertIn("cine_magic", wynik["sygnatury"])
                self.assertIn("storyline_json", wynik["sygnatury"])
                self.assertIn("benchmark_4700001_u32", wynik["sygnatury"])
                # wycięte bloki są SUROWE (bajt w bajt jak w paczce)
                wyciete = {
                    p.name: p.read_bytes()
                    for p in (wyjscie / "wyciete").glob("ezst_*.bin")
                }
                self.assertEqual(len(wyciete), 3)
                self.assertIn(bloki[0], wyciete.values())
                self.assertIn(bloki[1], wyciete.values())
                self.assertIn(bloki[3], wyciete.values())
                linie = (wyjscie / "wyciete" / "ezst_trafienia.jsonl").read_text(
                    encoding="utf-8"
                ).strip().splitlines()
                self.assertEqual(len(linie), 3)
                for linia in linie:
                    wpis = json.loads(linia)
                    self.assertTrue(wpis["wyciety"])
                    self.assertTrue(wpis["sygnatury"])
        finally:
            ms._zstd_backend = oryginalny

    def test_sonda_bez_backendu_sprawdza_tylko_gole(self):
        import tempfile

        bloki = [
            self._ezst_zlib(bytes.fromhex("c159410d") + b"\xab" * 300),  # niewidoczny bez zstd
            b"GOLY" + b"client/dialogs/hjt/sxd_longwenbiaoji.etsb" + b"\x00" * 50,
        ]
        oryginalny = ms._zstd_backend
        ms._zstd_backend = lambda: None
        try:
            with tempfile.TemporaryDirectory() as td:
                root, meta, entries = self._instalacja(td, bloki)
                wyjscie = Path(td) / "wynik"
                wynik = ms.skanuj_ezst_w_indeksie(root, wyjscie, meta, entries)
        finally:
            ms._zstd_backend = oryginalny
        self.assertIsNone(wynik["backend_zstd"])
        self.assertEqual(wynik["sondowanych"], 2)
        self.assertEqual(wynik["trafien"], 1)
        self.assertEqual(sorted(wynik["sygnatury"]), ["etsb_ext", "etsb_sciezka"])

    def test_duze_wpisy_pominiete_a_limit_zapisu_honorowany(self):
        import tempfile

        bloki = [
            b"GOLY" + b".etsb" + b"\x01" * 100,
            b"GOLY" + b".etsb" + b"\x02" * 100,
            b"GOLY" + b"\x03" * (2 << 20),  # za duży dla max_blok_sondy=1 MB
        ]
        oryginalny = ms._zstd_backend
        ms._zstd_backend = lambda: None
        try:
            with tempfile.TemporaryDirectory() as td:
                root, meta, entries = self._instalacja(td, bloki)
                wyjscie = Path(td) / "wynik"
                wynik = ms.skanuj_ezst_w_indeksie(
                    root, wyjscie, meta, entries,
                    max_blok_sondy=1 << 20, limit_zapisu=120,
                )
                self.assertEqual(wynik["pominietych_duzych"], 1)
                self.assertEqual(wynik["sondowanych"], 2)
                self.assertEqual(wynik["trafien"], 2)
                # limit 120 B pozwala wyciąć tylko pierwszy blok (109 B)
                self.assertEqual(wynik["wycietych"], 1)
                self.assertTrue(wynik["limit_osiagniety"])
                linie = (wyjscie / "wyciete" / "ezst_trafienia.jsonl").read_text(
                    encoding="utf-8"
                ).strip().splitlines()
                self.assertEqual(len(linie), 2)
                self.assertEqual(
                    [json.loads(l)["wyciety"] for l in linie], [True, False]
                )
        finally:
            ms._zstd_backend = oryginalny


class TestKandydaciV7(unittest.TestCase):
    """Kandydaci kitu v7 — prawdziwe ścieżki VFS ze `sciezki_vfs.jsonl`."""

    def test_sciezki_vfs_wchodza_do_kandydatow(self):
        import tempfile

        from tools import build_mpk_skaner as bmk

        with tempfile.TemporaryDirectory() as td:
            index_dir = Path(td)
            (index_dir / "mpk").mkdir()
            (index_dir / "poi.jsonl").write_text(
                json.dumps({"storyline": "client/dialogs/hjt/sxd_lingwei.etsb"}) + "\n",
                encoding="utf-8",
            )
            (index_dir / "mpk" / "sciezki_vfs.jsonl").write_text(
                json.dumps({"sciezka": "Char/e_01_cutscene/fgd/sq003_cqck/sq003_cqck.cine",
                            "ext": "cine", "zrodla": ["cutscenes.cine_path"]}) + "\n"
                + json.dumps({"sciezka": "Char/graph/cutscene/fsbd.graph",
                              "ext": "graph", "zrodla": ["fenbao_cutscene_info.cutscene_graph"]}) + "\n"
                + json.dumps({"sciezka": "client/dialogs/hjt/horse_move.etsb",
                              "ext": "etsb", "zrodla": ["skan_dataN"]}) + "\n"
                + json.dumps({"sciezka": "goly_bez_katalogu.ets",
                              "ext": "ets", "zrodla": ["skan_dataN"]}) + "\n",
                encoding="utf-8",
            )
            kandydaci = bmk.kandydaci(index_dir)
        sciezki = {k["sciezka"]: k["pochodzenie"] for k in kandydaci}
        self.assertEqual(
            sciezki["Char/e_01_cutscene/fgd/sq003_cqck/sq003_cqck.cine"], "vfs_cine"
        )
        self.assertEqual(sciezki["Char/graph/cutscene/fsbd.graph"], "vfs_graph")
        self.assertEqual(sciezki["client/dialogs/hjt/horse_move.etsb"], "vfs_etsb")
        # wariant rozszerzenia .etsb -> .ets
        self.assertEqual(
            sciezki["client/dialogs/hjt/horse_move.ets"], "vfs_etsb_wariant_ext"
        )
        # nazwy bez katalogu nie są hashowalne — nie wchodzą
        self.assertNotIn("goly_bez_katalogu.ets", sciezki)
        # stare źródła zostają (poi_storyline)
        self.assertIn("client/dialogs/hjt/sxd_lingwei.etsb", sciezki)


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

    def test_bat_sam_doinstalowuje_zstandard(self):
        # właściciel nie uruchamia nic ręcznie: bat sprawdza moduł zstd
        # i w razie braku doinstalowuje pakiet zstandard
        self.assertIn("--sprawdz-zstd", self.bat)
        self.assertIn("%PYEXE% -m pip install --user zstandard", self.bat)
        # kontrola PRZED właściwym skanem
        idx_sprawdz = self.bat.index("--sprawdz-zstd")
        idx_pip = self.bat.index("pip install --user zstandard")
        idx_skan = self.bat.index('--wyjscie "%~dp0MPK_SKANER_WYNIK"')
        self.assertLess(idx_sprawdz, idx_pip)
        self.assertLess(idx_pip, idx_skan)
        # nieudana instalacja NIE przerywa skanu (po UWAGA nie ma goto finish)
        ogon = self.bat[self.bat.index("UWAGA"):self.bat.index(":zstd_ok")]
        self.assertNotIn("goto finish", ogon)
        self.assertNotIn("exit", ogon)

    def test_czytaj_to_bez_recznych_polecen_pip(self):
        czytaj = self.bmk.README_BODY_PL
        self.assertNotIn("py -3 -m pip", czytaj)
        self.assertIn("doinstaluje go SAM", czytaj)


class TestSprawdzZstd(unittest.TestCase):
    """Flaga --sprawdz-zstd: kod 0 gdy moduł zstd jest, 1 gdy go brak."""

    def test_kod_zero_gdy_backend_jest(self):
        import zlib

        stary = ms._zstd_backend
        ms._zstd_backend = lambda: zlib
        try:
            self.assertEqual(ms.main(["--sprawdz-zstd"]), 0)
        finally:
            ms._zstd_backend = stary

    def test_kod_jeden_gdy_backendu_brak(self):
        stary = ms._zstd_backend
        ms._zstd_backend = lambda: None
        try:
            self.assertEqual(ms.main(["--sprawdz-zstd"]), 1)
        finally:
            ms._zstd_backend = stary


if __name__ == "__main__":
    unittest.main()
