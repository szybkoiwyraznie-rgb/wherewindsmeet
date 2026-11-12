from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path

from tests.test_apply_translation import container, table
from tests.test_buduj_paczke import EN_EXTRA, ZH_EXTRA, world
from tests.test_mapa_tekstow import diff_container
from tests.test_wyciag_indeks import EN, ZH, K, T
from tests.test_zrodla_tekstow import FakeBaza
from tools import audyt_aktualizacji, buduj_paczke, import_zwrotki, indeks, mapa_tekstow, tlumaczenie, wyciag, zbuduj_latke

ZH_ALL = {**ZH, **ZH_EXTRA}
EN_ALL = {**EN, **EN_EXTRA}


def fill(text: str, translations: dict[str, str]) -> str:
    """Wpisz przekłady po `PL:` tak, jak zrobiłby to tłumacz."""
    out, pending = [], None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("klucz: "):
            pending = stripped[7:]
        elif stripped == "PL:" and pending in translations:
            line = f"{line} {translations[pending]}"
        out.append(line)
    return "\n".join(out) + "\n"


class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="wwm-potok-")
        cls.root = Path(cls.temp.name)
        wyciag.zbuduj(FakeBaza(world()), ZH_ALL, EN_ALL, cls.root / "index", {"opis": "wersja 1"}, log=lambda _text: None)
        cls.ix = indeks.wczytaj(cls.root / "index")
        buduj_paczke.zbuduj(cls.ix, cls.root / "paczka", wersja="1", data="2026-01-01")

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def returned(self, translations: dict[str, str], name: str = "zwrotka") -> Path:
        folder = self.root / name
        for part in ("sceny", "widoki"):
            (folder / part).mkdir(parents=True, exist_ok=True)
            for path in (self.root / "paczka" / part).glob("*.md"):
                (folder / part / path.name).write_text(fill(path.read_text(encoding="utf-8"), translations), encoding="utf-8")
        return folder

    def test_import_accepts_good_entries_and_reports_bad_ones(self):
        folder = self.returned(
            {
                K("kwestia kowala"): "kwestia kowala po polsku",
                K("Miecz"): "Miecz PL",
                f"@{T + 3:016x}": "zrobiłem",
                K("Efekt #Y{0}#E\nna dwie linie"): "Efekt {0}\\npo polsku",  # zgubione #Y i #E
            },
            "zwrotka_a",
        )
        (folder / "obcy.md").write_text("1. [X] cokolwiek\n   klucz: ffffffffffffffff\n   PL: tekst spoza gry\n", encoding="utf-8")
        store = tlumaczenie.Magazyn()
        report = import_zwrotki.importuj(self.ix, import_zwrotki.pliki_zwrotki([folder]), store)
        self.assertEqual(report["liczby"]["nowe"], 3)
        self.assertEqual(report["odrzucone"], 2)
        self.assertEqual(report["problemy_wg_rodzaju"], {"nieznany_klucz": 1, "tokeny": 1})
        tokens = [item for item in report["problemy"] if item["rodzaj"] == "tokeny"][0]
        self.assertEqual((tokens["brakuje"], tokens["nadmiar"]), (["#E", "#Y"], []))
        self.assertTrue(tokens["plik"].startswith("widoki/04_"))
        self.assertEqual(store.po_kluczu[K("Miecz")], "Miecz PL")
        self.assertEqual(store.po_id, {f"{T + 3:016x}": "zrobiłem"})
        self.assertNotIn("po polsku\n", json.dumps(report))  # raport nie niesie treści przekładów

    def test_import_decodes_newlines_restores_edge_spaces_and_accepts_english_token_set(self):
        zh = {T + 1: "  spacje na brzegach ", T + 2: "kod {0} i {1}"}
        en = {T + 1: "edge spaces", T + 2: "code {0}"}  # angielski ma mniej kodów niż chiński
        tables = {"text_msg": [(1, {"content": T + 1}), (2, {"content": T + 2})]}
        with tempfile.TemporaryDirectory(prefix="wwm-potok-") as temp:
            wyciag.zbuduj(FakeBaza(tables), zh, en, Path(temp) / "index", {}, log=lambda _text: None)
            ix = indeks.wczytaj(Path(temp) / "index")
            content = (
                f"1. [x] a\n   klucz: {K(zh[T + 1])}\n   PL: pierwsza\\ndruga\n"
                f"2. [x] b\n   klucz: {K(zh[T + 2])}\n   PL: kod {{0}}\n"
            )
            store = tlumaczenie.Magazyn()
            report = import_zwrotki.importuj(ix, [("plik.md", content)], store)
        self.assertEqual(report["odrzucone"], 0)
        self.assertEqual(store.po_kluczu[K(zh[T + 1])], "  pierwsza\ndruga ")
        self.assertEqual(store.po_kluczu[K(zh[T + 2])], "kod {0}")

    def test_import_flags_broken_lines_and_conflicts_and_reads_zips(self):
        key = K("kwestia kowala")
        broken = f"1. [x] a\n   klucz: {key}\n   PL: pierwsza linia\n   druga linia\n"
        first = f"1. [x] a\n   klucz: {key}\n   PL: wersja pierwsza\n"
        second = f"1. [x] a\n   klucz: {key}\n   PL: wersja druga\n"
        archive = self.root / "zwrotka.zip"
        with zipfile.ZipFile(archive, "w") as outer:
            outer.writestr("sceny/a.md", first)
            outer.writestr("sceny/b.md", second)
            outer.writestr("nie_md.txt", second)
        store = tlumaczenie.Magazyn()
        report = import_zwrotki.importuj(self.ix, import_zwrotki.pliki_zwrotki([archive]), store)
        self.assertEqual(report["plikow"], 2)
        self.assertEqual(report["problemy_wg_rodzaju"], {"sprzeczne": 1})
        self.assertEqual(store.po_kluczu[key], "wersja pierwsza")
        report = import_zwrotki.importuj(self.ix, [("x.md", broken)], tlumaczenie.Magazyn())
        self.assertEqual(report["problemy_wg_rodzaju"], {"zlamana_linia": 1})
        with self.assertRaises(import_zwrotki.ZwrotkaError):
            list(import_zwrotki.pliki_zwrotki([self.root / "nie_ma"]))

    def test_import_cli_writes_store_and_report(self):
        folder = self.returned({K("Miecz"): "Miecz PL"}, "zwrotka_cli")
        store_dir, report_path = self.root / "magazyn_cli", self.root / "raport.json"
        code = import_zwrotki.main([str(folder), "--indeks", str(self.root / "index"), "--magazyn", str(store_dir), "--raport", str(report_path)])
        self.assertEqual(code, 0)
        self.assertEqual(tlumaczenie.wczytaj(store_dir).po_kluczu, {K("Miecz"): "Miecz PL"})
        self.assertEqual(json.loads(report_path.read_text(encoding="utf-8"))["liczby"]["nowe"], 1)

    def test_patch_rewrites_only_translated_entries_in_base_and_diff_layers(self):
        maps = self.root / "mapy"
        maps.mkdir(exist_ok=True)
        zh_path = maps / "zh"
        zh_path.write_bytes(container([table([(T + 1, ZH[T + 1].encode()), (T + 3, ZH[T + 3].encode()), (T + 4, ZH[T + 4].encode()), (T + 20, ZH[T + 20].encode()), (T + 22, ZH[T + 22].encode())])], with_metadata=True))
        base = maps / "en"
        base.write_bytes(container([table([(T + 1, b"smith line"), (T + 3, b"male version"), (T + 4, b"female version"), (T + 20, b"Sword"), (T + 22, b"Blade"), (T + 99, b"english only text")])], with_metadata=True))
        diff = maps / "en_diff"
        diff.write_bytes(diff_container([1], 6, [table([(T + 1, b"smith line, revised"), (T + 30, b"\xff")])]))
        store_dir = self.root / "magazyn_latka"
        store = tlumaczenie.Magazyn()
        store.ustaw(K("kwestia kowala"), "kwestia kowala po polsku")
        store.ustaw(K("Miecz"), "Miecz PL")
        store.ustaw(f"@{T + 3:016x}", "zrobiłem")
        store.ustaw(K("english only text"), "tekst tylko angielski")
        tlumaczenie.zapisz(store_dir, store)
        out = self.root / "latka"
        code = zbuduj_latke.main(["--indeks", str(self.root / "index"), "--magazyn", str(store_dir), "--zh", str(zh_path), "--cel", str(base), "--cel", str(diff), "--wyj", str(out)])
        self.assertEqual(code, 0)
        patched = mapa_tekstow.wczytaj(out / "en")
        self.assertEqual(
            patched,
            {
                T + 1: "kwestia kowala po polsku",
                T + 3: "zrobiłem",
                T + 4: "zrobiłem",  # pusty wariant bohaterki dziedziczy po bohaterze
                T + 20: "Miecz PL",
                T + 22: "Miecz PL",  # ten sam tekst źródłowy pod innym identyfikatorem
                T + 99: "tekst tylko angielski",  # brak chińskiego: klucz z tekstu w pliku celu
            },
        )
        layer, removed = mapa_tekstow.wczytaj_warstwe(out / "en_diff")
        self.assertEqual(layer, {T + 1: "kwestia kowala po polsku"})
        self.assertEqual(removed, {T + 30})
        report = json.loads((out / "latka.json").read_text(encoding="utf-8"))
        self.assertEqual([(item["plik"], item["wpisow"], item["przetlumaczonych"]) for item in report["pliki"]], [("en", 6, 6), ("en_diff", 1, 1)])
        self.assertEqual(base.read_bytes()[:4], (out / "en").read_bytes()[:4])
        self.assertIn("nie była sprawdzona w grze", report["uwaga"])

    def test_patch_refuses_empty_store_and_output_next_to_sources(self):
        maps = self.root / "mapy2"
        maps.mkdir(exist_ok=True)
        (maps / "en").write_bytes(container([table([(T + 1, b"x")])], with_metadata=True))
        common = ["--indeks", str(self.root / "index"), "--zh", str(maps / "en"), "--cel", str(maps / "en")]
        self.assertEqual(zbuduj_latke.main([*common, "--magazyn", str(self.root / "pusty"), "--wyj", str(self.root / "latka2")]), 1)
        self.assertEqual(zbuduj_latke.main([*common, "--magazyn", str(self.root / "pusty"), "--wyj", str(maps)]), 1)

    def test_audit_finds_new_texts_changed_scenes_and_feeds_the_supplement(self):
        zh2 = dict(ZH_ALL)
        en2 = dict(EN_ALL)
        zh2[T + 1] = "kwestia kowala, poprawiona"  # zmieniony tekst pod starym identyfikatorem
        zh2[T + 300] = "zupełnie nowy przedmiot"
        en2[T + 300] = "brand new item"
        tables = world()
        tables["stuff_items"] = [*tables["stuff_items"], (3, {"name": T + 300})]
        del tables["dialog_timelines.900"]
        wyciag.zbuduj(FakeBaza(tables), zh2, en2, self.root / "index2", {"opis": "wersja 2"}, log=lambda _text: None)
        new = indeks.wczytaj(self.root / "index2")
        store = tlumaczenie.Magazyn()
        store.ustaw(K("kwestia kowala"), "stary przekład")
        store.ustaw(K("Miecz"), "Miecz PL")
        report, slots = audyt_aktualizacji.porownaj(self.ix, new, store)
        self.assertEqual(slots, sorted([K("kwestia kowala, poprawiona"), K("zupełnie nowy przedmiot")]))
        self.assertEqual(report["teksty"]["nowe"], 2)
        self.assertEqual(report["teksty"]["usuniete"], 1)  # „dialog z innego projektu”; stara kwestia kowala żyje dalej pod innym id
        self.assertEqual(report["sceny"]["zmienione"], 1)
        self.assertEqual(report["sceny"]["lista_zmienionych"], [[100, 4, 1]])
        self.assertEqual(report["sceny"]["usuniete"], 1)
        self.assertEqual(report["teksty"]["nowe_wg_tabeli"]["stuff_items"], 1)
        self.assertEqual(report["przeklady"]["przetlumaczonych"], 2)
        self.assertIn("## Do tłumacza: 2 miejsc", audyt_aktualizacji.opis(report))
        manifest = buduj_paczke.zbuduj(new, self.root / "paczka2", wersja="2", data="2026-01-08", magazyn=store, tylko_sloty=set(slots), zip_=False)
        self.assertEqual(manifest["liczby"]["do_wpisania"], 2)
        self.assertEqual(manifest["liczby"]["scen"], 1)

    def test_audit_cli_reads_previous_index_from_git(self):
        repo = self.root / "repo"
        (repo / "index").mkdir(parents=True)
        for path in (self.root / "index").iterdir():
            (repo / "index" / path.name).write_bytes(path.read_bytes())

        def git(*args):
            subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)

        git("init", "-q")
        git("add", "-A")
        git("-c", "user.name=test", "-c", "user.email=test@example.invalid", "commit", "-q", "-m", "wersja 1")
        target = self.root / "z_gita"
        target.mkdir(exist_ok=True)
        extracted = audyt_aktualizacji.indeks_z_gita("HEAD", target, repo)
        self.assertEqual(indeks.wczytaj(extracted).manifest["wejscia"]["opis"], "wersja 1")
        with self.assertRaises(audyt_aktualizacji.AudytError):
            audyt_aktualizacji.indeks_z_gita("nie-ma-takiego-commita", target, repo)
        out = self.root / "audyt"
        code = audyt_aktualizacji.main(["--stary", str(extracted), "--nowy", str(self.root / "index"), "--wyj", str(out)])
        self.assertEqual(code, 0)
        self.assertEqual((out / "nowe_sloty.txt").read_text(encoding="utf-8"), "")
        self.assertEqual(json.loads((out / "audyt.json").read_text(encoding="utf-8"))["do_tlumacza"], 0)


if __name__ == "__main__":
    unittest.main()
