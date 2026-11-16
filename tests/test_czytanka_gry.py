from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from tools import buduj_czytanke_gry, kolejnosc_gry, mapa_tekstow, prolog_z_klucza, prowincje

FORMAT = "wwm-indeks-v2"

ZH = {
    "prolog": "是你",
    "alfa1": "阿尔法一",
    "alfa2": "阿尔法二",
    "bez_mapy": "无地图",
    "sam": "孤零零",
    "napis_a": "字幕甲",
    "napis_b": "字幕乙",
    "film": "电影字幕",
}
KLUCZ = {nazwa: mapa_tekstow.klucz(tekst) for nazwa, tekst in ZH.items()}
PL = {KLUCZ["prolog"]: "To ty."}


def _zapisz_jsonl(sciezka: Path, wiersze: list[dict]) -> None:
    with sciezka.open("w", encoding="utf-8") as f:
        for wiersz in wiersze:
            f.write(json.dumps(wiersz, ensure_ascii=False) + "\n")


def zbuduj_indeks(katalog: Path) -> None:
    """Mały, ale prawdziwy wyciąg: te same pliki i ten sam format co `index/`."""
    katalog.mkdir(parents=True, exist_ok=True)
    manifest = {
        "format": FORMAT,
        "pliki": {
            "teksty": [{"plik": "teksty_0.jsonl"}],
            "sceny": [{"plik": "sceny_0.jsonl"}],
        },
    }
    (katalog / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (katalog / "zrodla.json").write_text("{}", encoding="utf-8")
    (katalog / "pola_dialogow.json").write_text("{}", encoding="utf-8")

    _zapisz_jsonl(katalog / "teksty_0.jsonl", [
        {"k": KLUCZ[n], "zh": t, "en": f"{t} EN", "w": [1, "1"]} for n, t in ZH.items()
    ])
    _zapisz_jsonl(katalog / "sceny_0.jsonl", [
        # scena wyczerpana przez prolog
        {"d": 100, "o": [["A"]], "e": [["k", 0, KLUCZ["prolog"]]], "m": [10], "p": "对话-alfa.dialog"},
        # zwykła scena krainy Alfa
        {"d": 200, "o": [["B"]], "e": [["k", 0, KLUCZ["alfa1"]], ["k", 0, KLUCZ["alfa2"]]],
         "m": [10], "p": "对话-alfa.dialog"},
        # bez mapy, ale projekt alfa mapę ma → dziedziczy krainę
        {"d": 150, "o": [["C"]], "e": [["k", 0, KLUCZ["bez_mapy"]]], "p": "对话-alfa.dialog"},
        # projekt bez żadnej mapy → aneks
        {"d": 400, "o": [["D"]], "e": [["k", 0, KLUCZ["sam"]]], "p": "对话-zeta.dialog"},
    ])
    _zapisz_jsonl(katalog / "kolejnosc_0.jsonl", [
        {"k": KLUCZ["prolog"], "z": "napis", "d": None, "i": 590336, "t": None, "o": None},
        {"k": KLUCZ["alfa1"], "z": "dialog", "d": 200, "i": None, "t": 1.0, "o": 0},
        {"k": KLUCZ["alfa2"], "z": "dialog", "d": 200, "i": None, "t": 0.5, "o": 1},
        {"k": KLUCZ["napis_a"], "z": "napis", "d": None, "i": 600001, "t": None, "o": None},
        {"k": KLUCZ["napis_b"], "z": "napis_grey", "d": None, "i": 600000, "t": None, "o": None},
        {"k": KLUCZ["film"], "z": "film", "d": 2, "i": None, "t": 1.0, "o": 0},
    ])
    (katalog / "prowincje.json").write_text(json.dumps([
        {"kraina": "Alfa", "mapy": [10], "pian": 1001, "zadanie": 1, "kolejnosc": 0, "nazwy": []},
        {"kraina": "Beta", "mapy": [20], "pian": 1002, "zadanie": 2, "kolejnosc": 1, "nazwy": []},
    ], ensure_ascii=False), encoding="utf-8")


class TestCzytankaGry(unittest.TestCase):
    def setUp(self):
        self._katalog = tempfile.TemporaryDirectory()
        self.root = Path(self._katalog.name)
        self.index = self.root / "index"
        zbuduj_indeks(self.index)
        self.magazyn = self.root / "tlumaczenie"
        self.magazyn.mkdir()
        _zapisz_jsonl(self.magazyn / "pl_a.jsonl", [{"k": KLUCZ["prolog"], "pl": "To ty."}])
        self.transkrypt = self.root / "prolog.txt"
        self.transkrypt.write_text("# Pierwsza cutscena\nTo ty.\n", encoding="utf-8")
        self._stary_transkrypt = prolog_z_klucza.TRANSKRYPT
        prolog_z_klucza.TRANSKRYPT = self.transkrypt
        self.wyj = self.root / "czytanka"
        self.statystyka = buduj_czytanke_gry.buduj(
            index=str(self.index), magazyn=str(self.magazyn), wyj=self.wyj, zakres="wszystko")

    def tearDown(self):
        prolog_z_klucza.TRANSKRYPT = self._stary_transkrypt
        self._katalog.cleanup()

    def czytaj(self, nazwa: str) -> str:
        return (self.wyj / nazwa).read_text(encoding="utf-8")

    def pliki(self) -> list[str]:
        return sorted(p.name for p in self.wyj.glob("*.md"))

    def test_prolog_jest_pierwszy_i_ma_wiersz_z_danych(self):
        self.assertIn("00_prolog.md", self.pliki())
        self.assertIn("napis 590336", self.czytaj("00_prolog.md"))

    def test_scena_wyczerpana_przez_prolog_nie_powtarza_sie_w_krainie(self):
        self.assertNotIn("Scena 100", self.czytaj("k01_Alfa.md"))
        self.assertEqual(self.statystyka["scen_prologu"], 1)

    def test_kraina_ma_sceny_po_numerze_dialogu(self):
        tresc = self.czytaj("k01_Alfa.md")
        self.assertIn("Scena 150", tresc)
        self.assertIn("Scena 200", tresc)
        self.assertLess(tresc.index("Scena 150"), tresc.index("Scena 200"))
        self.assertIn("阿尔法一", tresc)
        self.assertIn("—", tresc)  # brak polskiego pokazany kreską, nie pominięty

    def test_kraina_bez_scen_nie_tworzy_pustego_pliku(self):
        self.assertFalse((self.wyj / "k02_Beta.md").exists())

    def test_scena_bez_mapy_dziedziczy_kraine_projektu(self):
        self.assertIn("Scena 150", self.czytaj("k01_Alfa.md"))

    def test_projekt_bez_mapy_trafia_do_aneksu(self):
        self.assertIn("Projekt 对话-zeta", self.czytaj("95_bez_mapy.md"))
        self.assertIn("Scena 400", self.czytaj("95_bez_mapy.md"))

    def test_napisy_po_id_a_prolog_pominiety(self):
        tresc = self.czytaj("91_napisy_przerywnikow.md")
        self.assertNotIn("590336", tresc)
        self.assertLess(tresc.index("600000"), tresc.index("600001"))

    def test_filmy_maja_czas(self):
        tresc = self.czytaj("90_filmy.md")
        self.assertIn("## Film 2", tresc)
        self.assertIn("1.0 s", tresc)

    def test_readme_opisuje_kolejnosc(self):
        tresc = self.czytaj("README.md")
        self.assertIn("kolejności odwiedzania", tresc)
        self.assertIn("wszystko", tresc)


class TestZakresPrzetlumaczone(unittest.TestCase):
    def test_chowa_linie_bez_polskiego(self):
        with tempfile.TemporaryDirectory() as katalog:
            root = Path(katalog)
            index = root / "index"
            zbuduj_indeks(index)
            magazyn = root / "tlumaczenie"
            magazyn.mkdir()
            _zapisz_jsonl(magazyn / "pl_a.jsonl", [{"k": KLUCZ["alfa1"], "pl": "Alfa raz."}])
            transkrypt = root / "prolog.txt"
            transkrypt.write_text("# Cutscena\nTo ty.\n", encoding="utf-8")
            stary = prolog_z_klucza.TRANSKRYPT
            prolog_z_klucza.TRANSKRYPT = transkrypt
            try:
                wyj = root / "tylko_pl"
                buduj_czytanke_gry.buduj(
                    index=str(index), magazyn=str(magazyn), wyj=wyj, zakres="przetlumaczone")
                tresc = (wyj / "k01_Alfa.md").read_text(encoding="utf-8")
                self.assertIn("Alfa raz.", tresc)
                self.assertNotIn("阿尔法二", tresc)
            finally:
                prolog_z_klucza.TRANSKRYPT = stary


class TestDzielenieNaCzesci(unittest.TestCase):
    def test_dzieli_i_numeruje_czesci(self):
        statystyka = {"plikow": 0}
        with tempfile.TemporaryDirectory() as katalog:
            wyj = Path(katalog)
            bloki = [f"## Blok {i}\n" for i in range(5)]
            buduj_czytanke_gry._zapisz(
                wyj, "k01_Test", "Test", [], bloki, statystyka, na_plik=2)
            pliki = sorted(p.name for p in wyj.glob("*.md"))
            self.assertEqual(pliki, ["k01_Test_cz01.md", "k01_Test_cz02.md", "k01_Test_cz03.md"])
            self.assertIn("część 1 z 3", (wyj / "k01_Test_cz01.md").read_text(encoding="utf-8"))
            self.assertEqual(statystyka["plikow"], 3)


class TestNazwy(unittest.TestCase):
    def test_nazwa_bazy_bez_znakow_specjalnych(self):
        self.assertEqual(buduj_czytanke_gry._nazwa_bazy(0, "燕南"), "k01_燕南")
        self.assertEqual(buduj_czytanke_gry._nazwa_bazy(6, "KFC联动"), "k07_KFC联动")

    def test_komorka_czysci_tabele(self):
        self.assertEqual(buduj_czytanke_gry._komorka("a|b\nc\u200b"), "a\\|b c")


class TestProwincje(unittest.TestCase):
    def test_nazwa_krainy_scala_warianty(self):
        self.assertEqual(prowincje.nazwa_krainy("任务重制_燕南大地图", 701), "燕南")
        self.assertEqual(prowincje.nazwa_krainy("燕南大地图", 501), "燕南")
        self.assertEqual(prowincje.nazwa_krainy(None, 5), "mapa 5")

    def test_kolejnosc_wg_pianu_i_numeru_zadania(self):
        zadania = {
            500: {"przestrzen": 70, "pian": 1002},
            100: {"przestrzen": 50, "pian": 1001},
            200: {"przestrzen": 60, "pian": 1001},
            300: {"przestrzen": 50, "pian": 1001},
        }
        miejsca = {50: {"robocza": "燕南大地图"}, 60: {"robocza": "任务重制_燕南大地图"},
                   70: {"robocza": "清河大地图"}}
        ix = SimpleNamespace(zadania=zadania, miejsca=miejsca)
        krainy = prowincje.zbierz(ix)
        self.assertEqual([k["kraina"] for k in krainy], ["燕南", "清河"])
        self.assertEqual(krainy[0]["mapy"], [50, 60])  # obie mapy to jedna kraina
        self.assertEqual([k["kolejnosc"] for k in krainy], [0, 1])

    def test_zadanie_bez_przestrzeni_pomijane(self):
        ix = SimpleNamespace(zadania={1: {"pian": 1001}}, miejsca={})
        self.assertEqual(prowincje.zbierz(ix), [])


class TestKolejnoscWPliku(unittest.TestCase):
    def test_wczytaj_zbiera_shardy(self):
        with tempfile.TemporaryDirectory() as katalog:
            _zapisz_jsonl(Path(katalog) / "kolejnosc_a.jsonl", [{"k": "aaa", "z": "napis", "i": 1}])
            _zapisz_jsonl(Path(katalog) / "kolejnosc_b.jsonl", [{"k": "bbb", "z": "napis", "i": 2}])
            wiersze = kolejnosc_gry.wczytaj(katalog)
            self.assertEqual([w["i"] for w in wiersze], [1, 2])


if __name__ == "__main__":
    unittest.main()


class TestPakietCzytanki(unittest.TestCase):
    """Składanie trzech warstw w jeden pakiet (`tools/zbuduj_czytanke_pelna.py`)."""

    def test_katalogi_warstw(self):
        from tools import zbuduj_czytanke_pelna as pakiet

        self.assertEqual(pakiet.KATALOGI["epizody"], "03_fabula")
        self.assertEqual(pakiet.KATALOGI["kontekst_scen"], "04_kontekst")
        self.assertEqual(pakiet.KATALOGI["dodatkowe"], "05_reszta")

    def test_normalizacja_zdejmuje_kreski_tabel_i_barwy(self):
        from tools import zbuduj_czytanke_pelna as pakiet

        # czytanki łamią komórki na kilka wierszy tabeli — porównanie musi to znieść
        self.assertEqual(
            pakiet._znormalizuj("| Wachlarz Strażnika   |   Śniegu · Na próbę |"),
            "wachlarz strażnika śniegu · na próbę",
        )
        self.assertEqual(pakiet._znormalizuj("#a66829Noc#E w piwnicy"), "noc w piwnicy")
        self.assertEqual(pakiet._znormalizuj("Wejdź <Fang Wenxiu|30094|#Y> teraz"),
                         "wejdź teraz")

    def test_pokrycie_znajduje_tekst_w_pakiecie(self):
        from tools import zbuduj_czytanke_pelna as pakiet

        with tempfile.TemporaryDirectory() as katalog:
            root = Path(katalog)
            (root / "out").mkdir()
            (root / "out" / "a.md").write_text(
                "| Nazwa   |\n|---|\n| Wachlarz Strażnika |\n| Śniegu · Na próbę |\n",
                encoding="utf-8")
            magazyn = root / "tlumaczenie"
            magazyn.mkdir()
            _zapisz_jsonl(magazyn / "pl_a.jsonl", [
                {"k": "a" * 16, "pl": "Wachlarz Strażnika Śniegu · Na próbę"},
                {"k": "b" * 16, "pl": "Tekst, którego w pakiecie nie ma nigdzie"},
            ])
            wynik = pakiet.sprawdz_pokrycie(root / "out", magazyn, proba=10)
            self.assertEqual(wynik["kluczy_w_magazynie"], 2)
            self.assertEqual(wynik["nieznalezione_w_probie"], 1)


class TestCzytankaDoCzytania(unittest.TestCase):
    """Format czytanki do czytania: dialog linia po linii, trzy pliki."""

    def setUp(self):
        from tools import czytanka_czysta

        self.czytanka = czytanka_czysta
        self._katalog = tempfile.TemporaryDirectory()
        root = Path(self._katalog.name)
        self.index = root / "index"
        zbuduj_indeks(self.index)
        self.magazyn = root / "tlumaczenie"
        self.magazyn.mkdir()
        _zapisz_jsonl(self.magazyn / "pl_a.jsonl", [
            {"k": KLUCZ["prolog"], "pl": "To ty."},
            {"k": KLUCZ["alfa1"], "pl": "Alfa raz."},
            {"k": KLUCZ["sam"], "pl": "Samotna kwestia."},
            {"k": KLUCZ["napis_a"], "pl": "Napisy przerywnika."},
            {"k": KLUCZ["film"], "pl": "Wers filmu."},
        ])
        self.transkrypt = root / "prolog.txt"
        self.transkrypt.write_text("# Pierwsza cutscena\nTo ty.\n", encoding="utf-8")
        stary = prolog_z_klucza.TRANSKRYPT
        prolog_z_klucza.TRANSKRYPT = str(self.transkrypt)
        try:
            from tools import chronologia

            chronologia.zbuduj(index=str(self.index), magazyn=str(self.magazyn),
                               wyj=self.index / "chronologia.jsonl")
        finally:
            prolog_z_klucza.TRANSKRYPT = stary
        self.wyj = root / "czytanka"
        self.statystyka = czytanka_czysta.zbuduj(
            index=str(self.index), magazyn=str(self.magazyn), wyj=self.wyj,
            zakres="przetlumaczone")

    def tearDown(self):
        self._katalog.cleanup()

    def czytaj(self, nazwa: str) -> str:
        return (self.wyj / nazwa).read_text(encoding="utf-8")

    def test_trzy_pliki_po_jednym_na_rodzaj(self):
        self.assertEqual(sorted(p.name for p in self.wyj.glob("*.md")),
                         ["01_sceny_i_cutsceny.md", "02_kontekst_scen_i_cutscen.md", "03_reszta.md",
                          "README.md"])

    def test_kwestia_ma_mowce_i_tekst_w_jednej_linii(self):
        tresc = self.czytaj("01_sceny_i_cutsceny.md")
        self.assertIn("**B:** Alfa raz.", tresc)
        self.assertIn("## Scena 200", tresc)

    def test_bez_czasow_tabel_i_pustych_linii_miedzy_kwestiami(self):
        tresc = self.czytaj("01_sceny_i_cutsceny.md")
        self.assertNotIn("|", tresc)
        self.assertNotRegex(tresc, r"\d+\.\d+ ?s")
        self.assertIn("## Scena 200\n**B:** Alfa raz.", tresc)

    def test_kwestie_bez_polskiego_sa_pomijane(self):
        self.assertNotIn("阿尔法二", self.czytaj("01_sceny_i_cutsceny.md"))
        self.assertGreater(self.statystyka["pominiete"], 0)

    def test_piesn_jest_na_koncu_chronologii(self):
        tresc = self.czytaj("01_sceny_i_cutsceny.md")
        piesn = tresc.index("## Pieśń 2")
        self.assertGreater(piesn, tresc.index("# Prolog"))
        self.assertGreater(piesn, tresc.index("## Scena"))

    def test_napisy_spoza_cutscen_trafiaja_do_reszty(self):
        # `napis_a` nie należy do żadnej cutsceny ani grupy zadań → plik 03
        self.assertIn("Napisy przerywnika.", self.czytaj("03_reszta.md"))
        self.assertNotIn("Napisy przerywnika.", self.czytaj("01_sceny_i_cutsceny.md"))

    def test_scena_bez_mapy_ma_wlasna_sekcje(self):
        tresc = self.czytaj("01_sceny_i_cutsceny.md")
        self.assertIn("# Sceny bez przypisanej mapy", tresc)
        self.assertIn("## Scena 400\n**D:** Samotna kwestia.", tresc)

    def test_czysty_tekst_zdejmuje_kody(self):
        self.assertEqual(self.czytanka._czysty("#a66829Noc#E <Fang|1|#Y> w piwnicy"), "Noc Fang w piwnicy")

    def test_kategorie_po_nazwie_tabeli(self):
        self.assertEqual(self.czytanka._kategoria("equip_items"), "Przedmioty, stroje i tytuły")
        self.assertEqual(self.czytanka._kategoria("kongfu"), "Sztuki walki i umiejętności")
        self.assertEqual(self.czytanka._kategoria("cos_dziwnego"), "Pozostałe teksty")

    def test_gracz_nazywa_sie_youxia(self):
        self.assertEqual(self.czytanka.GRACZ["你"], "Youxia")
        self.assertEqual(self.czytanka.GRACZ["player"], "Youxia")
