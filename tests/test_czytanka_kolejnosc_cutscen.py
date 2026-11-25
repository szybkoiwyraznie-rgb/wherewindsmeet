"""Kolejność kwestii w cutscenach czytanki.

W plikach gry ten sam przerywnik bywa zapisany dwa razy (dwa zestawy napisów),
a `kn` w chronologii miesza napisy przypisane wprost z tabeli gry i bloki puli —
dlatego kwestie trafiały do czytanki w kolejności losowej. Porządek bierzemy
z numeru wiersza puli `text_msg`; warianty rozdzielamy nagłówkiem, a streszczenie
sceny dostaje własny nagłówek.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from tools import czytanka_czysta as cz

INDEX = Path(__file__).resolve().parent.parent / "index"
MAGAZYN = Path(__file__).resolve().parent.parent / "tlumaczenie"


def _wiersze(**pary: int) -> dict[str, int]:
    return dict(pary)


class TestKolejnoscCutscen(unittest.TestCase):
    def test_porzadek_wg_wiersza_puli(self):
        # `kn` w kolejności z chronologii: najpierw kwestie przypisane wprost z tabeli
        wiersz = {"t": "cutscena", "n": 1, "kn": ["k-late", "k-early", "k-mid"], "k": ["k-sum"]}
        wiersze = _wiersze(**{"k-early": 590153, "k-mid": 590154, "k-late": 590160})
        pl = {"k-late": "Trzecia.", "k-early": "Pierwsza.", "k-mid": "Druga.", "k-sum": "Streszczenie."}

        klucze, podtytuly, powtorzone = cz._napisy_cutsceny(wiersz, wiersze, pl)

        self.assertEqual(klucze, ["k-sum", "k-early", "k-mid", "k-late"])
        self.assertEqual(podtytuly, {0: "Streszczenie sceny"})
        self.assertEqual(powtorzone, [])

    def test_streszczenie_stoi_na_poczatku_sceny(self):
        wiersz = {"t": "cutscena", "n": 1, "kn": ["a"], "k": ["sum1", "sum2"]}
        klucze, podtytuly, _ = cz._napisy_cutsceny(
            wiersz, _wiersze(a=590100), {"a": "Kwestia.", "sum1": "Raz.", "sum2": "Dwa."})
        self.assertEqual(klucze, ["sum1", "sum2", "a"])
        self.assertEqual(podtytuly, {0: "Streszczenie sceny"})

    def test_dwa_warianty_napisow_rozdzielone_i_bez_powtorzen(self):
        # dwa bloki tej samej cutsceny: 590153+ oraz 591125+
        wiersz = {"t": "cutscena", "n": 30161,
                  "kn": ["b", "a", "d", "c"], "k": []}
        wiersze = _wiersze(**{"a": 590153, "b": 590154, "c": 591125, "d": 591126})
        pl = {"a": "Wstawaj!", "b": "Wschód słońca.", "c": "Wstawaj!", "d": "Inna kwestia."}

        klucze, podtytuly, powtorzone = cz._napisy_cutsceny(wiersz, wiersze, pl)

        # grana jest wersja nowsza (wyższe numery wierszy puli), starsza schodzi do wariantu
        self.assertEqual(klucze, ["c", "d", "b"])      # „a” to to samo zdanie co „c”
        self.assertEqual(powtorzone, ["a"])
        self.assertEqual(podtytuly, {2: "Inny wariant napisów tej cutsceny (wiersze 590153–590154)"})

    def test_klucz_bez_wiersza_nie_psuje_porzadku(self):
        wiersz = {"t": "cutscena", "n": 1, "kn": ["bez", "z1"], "k": []}
        klucze, _, _ = cz._napisy_cutsceny(wiersz, _wiersze(z1=590200), {"bez": "Bez.", "z1": "Z."})
        self.assertEqual(klucze, ["z1", "bez"])

    def test_wiersze_napisow_z_osi_kolejnosci(self):
        class Ix:
            cutsceny_kontekst = {"napis": [{"k": "k1", "wiersz": 590153}]}

        # wiersze „napis_grey” nie wchodzą: to ten sam wiersz puli z tekstem bez przekładu
        porzadek = {"k1": [{"z": "napis", "i": 590153}], "k2": [{"z": "napis_grey", "i": 591125}]}
        self.assertEqual(cz._wiersze_napisow(Ix(), porzadek), {"k1": 590153})


class TestBlokGlowny(unittest.TestCase):
    """Grana jest nowsza wersja napisów cutsceny, nie pierwsza z `kn`."""

    def test_nowszy_blok_na_poczatku_starszy_w_wariancie(self):
        wiersz = {"t": "cutscena", "n": 1, "kn": ["stara1", "stara2", "nowa1", "nowa2"], "k": []}
        wiersze = _wiersze(stara1=590153, stara2=590154, nowa1=591148, nowa2=591149)
        pl = {"stara1": "Stara pierwsza.", "stara2": "Stara druga.",
              "nowa1": "Nowa pierwsza.", "nowa2": "Nowa druga."}

        klucze, podtytuly, _ = cz._napisy_cutsceny(wiersz, wiersze, pl)

        self.assertEqual(klucze, ["nowa1", "nowa2", "stara1", "stara2"])
        self.assertEqual(list(podtytuly), [2])
        self.assertTrue(podtytuly[2].startswith("Inny wariant napisów"))

    def test_trzy_bloki_w_kolejnosci_od_najnowszego(self):
        wiersz = {"t": "cutscena", "n": 1, "kn": ["a", "b", "c"], "k": []}
        wiersze = _wiersze(a=590100, b=591100, c=591900)
        pl = {"a": "Najstarsza.", "b": "Średnia.", "c": "Najnowsza."}

        klucze, _, _ = cz._napisy_cutsceny(wiersz, wiersze, pl)

        self.assertEqual(klucze, ["c", "b", "a"])


class TestNaglowkiWPliku(unittest.TestCase):
    def _statystyka(self):
        return {"jednostek": 0, "linii": 0, "pominiete": 0, "bez_przekladu": 0}

    def test_naglowki_wychodza_przed_wlasciwa_linia(self):
        jednostka = cz.Jednostka(
            "cutscena", "Cutscena 1", "# Kraina",
            [("", "a"), ("", "b"), ("", "c"), ("", "sum")],
            podtytuly={2: "Inny wariant napisów tej cutsceny (wiersze 591125–591169)",
                       3: "Streszczenie sceny"})
        pl = {"a": "Pierwsza.", "b": "Druga.", "c": "Trzecia.", "sum": "Streszczenie."}
        out, uzyte, _ = cz._plik_scen([jednostka], pl, "przetlumaczone", self._statystyka())
        self.assertEqual(out[3:], [
            "Pierwsza.",
            "Druga.",
            "### Inny wariant napisów tej cutsceny (wiersze 591125–591169)",
            "Trzecia.",
            "### Streszczenie sceny",
            "Streszczenie.",
            "",
        ])
        self.assertEqual(uzyte, {"a", "b", "c", "sum"})

    def test_przerwa_po_streszczeniu_przed_kwestiami(self):
        # streszczenie na początku (podtytuł pod linią 0) — po nim pusty wiersz
        jednostka = cz.Jednostka(
            "cutscena", "Cutscena 30150", "# Prolog",
            [("", "sum"), ("", "a"), ("", "b")],
            podtytuly={0: "Streszczenie sceny"}, streszczenie=1)
        pl = {"sum": "Król Bez Oblicza znów atakuje.", "a": "Robi się ciekawie.",
              "b": "Jak zawsze?"}
        out, _, _ = cz._plik_scen([jednostka], pl, "przetlumaczone", self._statystyka())
        self.assertEqual(out[2:], [
            "## Cutscena 30150",
            "### Streszczenie sceny",
            "Król Bez Oblicza znów atakuje.",
            "",
            "Robi się ciekawie.",
            "Jak zawsze?",
            "",
        ])

    def test_przerwa_po_streszczeniu_z_wariantem_napisow(self):
        # streszczenie, a po nim zwykłe kwestie i dopiero nagłówek wariantu
        jednostka = cz.Jednostka(
            "cutscena", "Cutscena 1", "# Prolog",
            [("", "sum"), ("", "a"), ("", "b")],
            podtytuly={0: "Streszczenie sceny", 2: "Inny wariant napisów tej cutsceny (wiersze 590153–590154)"},
            streszczenie=1)
        pl = {"sum": "Streszczenie.", "a": "Pierwsza kwestia.", "b": "Druga kwestia."}
        out, _, _ = cz._plik_scen([jednostka], pl, "przetlumaczone", self._statystyka())
        self.assertEqual(out[2:], [
            "## Cutscena 1",
            "### Streszczenie sceny",
            "Streszczenie.",
            "",
            "Pierwsza kwestia.",
            "### Inny wariant napisów tej cutsceny (wiersze 590153–590154)",
            "Druga kwestia.",
            "",
        ])

    def test_ukryte_powtorzenia_nie_trafiaja_do_reszty(self):
        jednostka = cz.Jednostka("cutscena", "Cutscena 1", "# Kraina",
                                 [("", "a")], zasloniete=("duplikat",))
        out, uzyte, _ = cz._plik_scen([jednostka], {"a": "Kwestia."},
                                      "przetlumaczone", self._statystyka())
        self.assertIn("Kwestia.", out)
        self.assertIn("duplikat", uzyte)


@unittest.skipUnless((INDEX / "chronologia.jsonl").is_file() and MAGAZYN.is_dir(),
                     "brak wyciągu gry w index/")
class TestCutscena30161(unittest.TestCase):
    """Regresja z prawdziwego wyciągu: cutscena Ruby (30161)."""

    @classmethod
    def setUpClass(cls):
        cls.wiersz = None
        with (INDEX / "chronologia.jsonl").open(encoding="utf-8") as f:
            for linia in f:
                wpis = json.loads(linia)
                if wpis.get("t") == "cutscena" and wpis.get("n") == 30161:
                    cls.wiersz = wpis
                    break
        if cls.wiersz is None:
            raise unittest.SkipTest("brak cutsceny 30161 w chronologii")
        klucze = set(cls.wiersz.get("kn") or []) | set(cls.wiersz.get("k") or [])
        cls.wiersze = {}
        with (INDEX / "cutsceny_kontekst.jsonl").open(encoding="utf-8") as f:
            for linia in f:
                wpis = json.loads(linia)
                if wpis.get("typ") == "napis" and wpis.get("k") in klucze:
                    cls.wiersze[wpis["k"]] = wpis["wiersz"]
        cls.audio = {}
        with (INDEX / "cutsceny_kontekst.jsonl").open(encoding="utf-8") as f:
            for linia in f:
                wpis = json.loads(linia)
                if wpis.get("typ") == "napis" and wpis.get("audio"):
                    cls.audio[wpis["wiersz"]] = wpis["audio"]
        cls.pl = {}
        for plik in sorted(MAGAZYN.glob("pl_*.jsonl")):
            with plik.open(encoding="utf-8") as f:
                for linia in f:
                    wpis = json.loads(linia)
                    if wpis.get("k") in klucze:
                        cls.pl[wpis["k"]] = wpis["pl"]

    def test_scena_zaczyna_sie_od_zbudzenia_a_nie_od_bebna_ani_wiersza(self):
        """Pierwsze kwestie to blok zbudzenia (wiersze puli 591148–591151,
        nagrania `vo_sm_sxdm4_cs_zlxl_hx_*`), nie bęben ani wiersz ze starszego
        wariantu (wiersze 590xxx). Porównujemy numery wierszy puli, nie brzmienie
        przekładu — tłumacz może zmieniać tekst, kolejność jest z danych gry."""
        klucze, _, _ = cz._napisy_cutsceny(self.wiersz, self.wiersze, self.pl, self.audio)
        wiersze = [self.wiersze[k] for k in klucze[1:]   # [0] to streszczenie
                   if k in self.pl and k in self.wiersze]
        self.assertEqual(wiersze[:4], [591148, 591149, 591150, 591151])
        audio_bloku = self.audio.get(591150, "")
        self.assertTrue(audio_bloku.startswith("vo_sm_sxdm4_cs_zlxl_hx"), audio_bloku)
        self.assertFalse([w for w in wiersze[:4] if w < 591000],
                         "starszy wariant napisów (590xxx) wszedł przed zbudzenie")

    def test_streszczenie_jest_pierwsze_i_pod_naglowkiem(self):
        klucze, podtytuly, _ = cz._napisy_cutsceny(self.wiersz, self.wiersze, self.pl, self.audio)
        self.assertEqual(podtytuly.get(0), "Streszczenie sceny")
        self.assertNotIn(len(klucze) - 1, podtytuly)

    def test_zaden_tekst_nie_powtarza_sie_w_scenie(self):
        klucze, _, _ = cz._napisy_cutsceny(self.wiersz, self.wiersze, self.pl, self.audio)
        sygnatury = [cz._bez_interpunkcji(self.pl[k]) for k in klucze if k in self.pl]
        self.assertEqual(len(sygnatury), len(set(sygnatury)))


if __name__ == "__main__":
    unittest.main()

# Pełny ręczny zapis gracza cutsceny 30161 (benchmark z rozmowy) — numery
# wierszy puli `text_msg` w kolejności wyświetlania w grze. Przeplot bloków
# Ruby (591148–591169) i gracza (591170–591183) pochodzi ze ścieżki audio
# pliku `.cine` (tools/cutsceny_kolejnosc_kwestii.py).
BENCHMARK_30161 = [
    591148, 591149, 591170, 591150, 591151, 591171, 591152, 591153, 591154,
    591172, 591173, 591174, 591155, 591156, 591175, 591157, 591158, 591159,
    591160, 591176, 591177, 591161, 591162, 591163, 591164, 591165, 591178,
    591179, 591180, 591166, 591167, 591168, 591169, 591181, 591182, 591183,
]


class TestChronologiaCine(unittest.TestCase):
    """Przeplot kwestii cutscen ze ścieżki audio `.cine` (indeks i render)."""

    @classmethod
    def setUpClass(cls):
        plik = INDEX / "cutsceny_kolejnosc_kwestii.jsonl"
        if not plik.exists():
            raise unittest.SkipTest("brak index/cutsceny_kolejnosc_kwestii.jsonl")
        cls.kolejnosc = {}
        with plik.open(encoding="utf-8") as f:
            for linia in f:
                wpis = json.loads(linia)
                cls.kolejnosc[int(wpis["no"])] = wpis.get("bloki") or []

    def test_30163_kolejnosc_z_ujec(self):
        """30163: master milczy, oś z ujęć s0010/s0030/s0070 (nie z zapisu gracza)."""
        bloki = self.kolejnosc.get(30163)
        self.assertTrue(bloki, "brak cutsceny 30163 w indeksie kolejności")
        self.assertEqual([r["k"] for r in bloki[0]], [
            "99aa1305b14cab9d", "686292d5404f99dc",
            "18b0e586d1f98026", "ef40bf4720988a61", "571634c537f273b9",
            "c8ae650aef035fe1", "614fbe2f5b73ac93",
            "aa44a6097c51e9dd",
        ])
        self.assertEqual(bloki[0][0]["a"], "vo_sm_sxdm7_npc_33")
        self.assertEqual(bloki[0][2]["a"], "vo_sm_sxdm5_npc_39")
        self.assertEqual(bloki[0][-1]["a"], "vo_sm_sxdm4_npc_03")

    def test_30162_kolejnosc_z_gry(self):
        """Most Ruby: „nie skacz” → Ach! → most → „co teraz” (oś `.cine`)."""
        bloki = self.kolejnosc.get(30162)
        self.assertTrue(bloki, "brak cutsceny 30162 w indeksie kolejności")
        audio = [r.get("a") for r in bloki[0]]
        self.assertEqual(audio, [
            "vo_sm_sxdm9_pma_25",
            "vo_sm_sxdm9_pma_26",
            "vo_sm_sxdm9_npc_44",
            "vo_sm_sxdm9_npc_44",
        ])
        self.assertEqual(bloki[0][1]["t"], 11.104)
        self.assertNotIn("w", bloki[0][1])

    def test_indeks_odtwarza_zapis_gracza_30161(self):
        """Nowszy blok 30161 w indeksie = pełny ręczny zapis rozgrywki."""
        bloki = self.kolejnosc.get(30161)
        self.assertTrue(bloki, "brak cutsceny 30161 w indeksie kolejności")
        nowe = [b for b in bloki if min(r["w"] for r in b) >= 591148]
        self.assertEqual(len(nowe), 1)
        self.assertEqual([r["w"] for r in nowe[0]], BENCHMARK_30161)

    def test_render_30161_w_kolejnosci_benchmarku(self):
        """`_napisy_cutsceny` z chronologią zaczyna od pełnego przeplotu."""
        wiersz = None
        with (INDEX / "chronologia.jsonl").open(encoding="utf-8") as f:
            for linia in f:
                wpis = json.loads(linia)
                if wpis.get("t") == "cutscena" and wpis.get("n") == 30161:
                    wiersz = wpis
                    break
        self.assertIsNotNone(wiersz)
        bloki = self.kolejnosc[30161]
        wiersze = {r["k"]: r["w"] for b in bloki for r in b}
        with (INDEX / "cutsceny_kontekst.jsonl").open(encoding="utf-8") as f:
            for linia in f:
                wpis = json.loads(linia)
                if wpis.get("typ") == "napis" and wpis.get("k"):
                    wiersze.setdefault(wpis["k"], wpis["wiersz"])
        klucze, _, _ = cz._napisy_cutsceny(wiersz, wiersze, {}, None, bloki)
        numery = [wiersze[k] for k in klucze if k in wiersze]
        poczatek = [n for n in numery if 591148 <= n <= 591183]
        self.assertEqual(poczatek[:len(BENCHMARK_30161)], BENCHMARK_30161)

    def test_chronologia_przeplata_a_luzem_idzie_do_wariantu(self):
        """Syntetycznie: przeplot z chronologii + kwestie spoza niej jako wariant."""
        wiersz = {"t": "cutscena", "n": 7, "kn": ["r1", "r2", "stare"], "k": []}
        wiersze = _wiersze(r1=100, r2=101, g1=110, stare=50)
        pl = {"r1": "Raz.", "r2": "Dwa.", "g1": "Trzy.", "stare": "Cztery."}
        # chronologia: r1, g1 (spoza kn!), r2 — przeplot dwóch zakresów puli
        bloki = [[{"w": 100, "k": "r1", "t": 0.5},
                  {"w": 110, "k": "g1", "t": 1.0},
                  {"w": 101, "k": "r2", "t": 2.0}]]
        klucze, podtytuly, powtorzone = cz._napisy_cutsceny(wiersz, wiersze, pl, None, bloki)
        # oś `.cine` jest pełna — „stare” z puli obok to nie wariant tej cutsceny
        self.assertEqual(klucze, ["r1", "g1", "r2"])
        self.assertNotIn("stare", klucze)
        self.assertEqual(podtytuly, {})
        self.assertEqual(powtorzone, [])


class TestMowcaZAudio(unittest.TestCase):
    """Mówca z nazwy nagrania: tylko pewniki (gracz, kody postaci w `_cs_`)."""

    def test_nagrania_gracza(self):
        from tools import kontekst_cutscen as kc
        for audio in ("vo_sm_sxdm7_pma_04", "vo_gp_wswll_pma_24",
                      "vo_gp_znqsr_pma_219_01", "vo_shenxiandu_player_m_65",
                      "vo_xyz_player_f_3", "vo_sm_sxdm4_cs_zlxl_pma_05"):
            self.assertEqual(kc.mowca_z_audio(audio), "Youxia", audio)

    def test_generyczne_npc_bez_mowcy(self):
        from tools import kontekst_cutscen as kc
        for audio in ("vo_sm_sxd_npc_124", "vo_sm_sxdm7_npc_01",
                      "vo_sm_sxd_npc_pma_44",   # licznik `pma` po `npc` to nie gracz
                      "vo_sm_kfm8_npc_231_ui", ""):
            self.assertEqual(kc.mowca_z_audio(audio), "", audio)

    def test_kod_postaci_w_sciezce_cs(self):
        from tools import kontekst_cutscen as kc
        self.assertEqual(kc.mowca_z_audio("vo_sm_sxdm4_cs_zlxl_hx_17"), "Ruby")
        self.assertEqual(kc.mowca_z_audio("vo_sm_sxdm4_cs_zlxl_hx_02"), "Ruby")


class TestWykrzyknikDidaskaliow(unittest.TestCase):
    """Okrzyk `（啊）` z didaskaliów wchodzi na oś czasu; westchnienie nie."""

    def setUp(self):
        from tools import cutsceny_kolejnosc_kwestii as ck
        self.ck = ck

    def test_ah_z_nawiasu_nie_westchnienie(self):
        zh = "（啊）（稍微惊吓的气声）（看见桥断了）（放心下来）"
        self.assertEqual(self.ck._wykrzyknik_z_didaskaliow(zh), "啊")
        self.assertEqual(self.ck._wykrzyknik_z_didaskaliow("（轻轻叹气）"), "")
        self.assertEqual(self.ck._wykrzyknik_z_didaskaliow("（跳桥前气息）+（跳）嘿呀。"), "")

    def test_wstawia_ach_miedzy_kwestie_30162(self):
        """Kolejność z gry: Ruby → Ach! → most → co teraz."""
        blok = [
            {"w": 591186, "k": "ruby", "t": 7.091, "a": "vo_sm_sxdm9_pma_25"},
            {"w": 591184, "k": "most", "t": 15.266, "a": "vo_sm_sxdm9_npc_44"},
            {"w": 591185, "k": "co", "t": 15.266, "a": "vo_sm_sxdm9_npc_44"},
        ]
        kwestie = [
            {"t": 2.052, "audio": "vo_sm_sxdm9_npc_43", "zh": "（跳桥前气息）+（跳）嘿呀。"},
            {"t": 7.091, "audio": "vo_sm_sxdm9_pma_25", "zh": "红线你好好走，别蹦！"},
            {"t": 11.104, "audio": "vo_sm_sxdm9_pma_26",
             "zh": "（啊）（稍微惊吓的气声）（看见桥断了）（放心下来）"},
            {"t": 15.266, "audio": "vo_sm_sxdm9_npc_44",
             "zh": "（反应过来）啊桥、桥被我压断了。老大你要怎么办？"},
        ]
        self.ck.wstaw_wykrzykniki(blok, kwestie, {"啊": "k-ach"})
        self.assertEqual([r["k"] for r in blok], ["ruby", "k-ach", "most", "co"])
        self.assertEqual(blok[1]["t"], 11.104)
        self.assertEqual(blok[1]["a"], "vo_sm_sxdm9_pma_26")
        self.assertNotIn("w", blok[1])

    def test_mapa_bierze_krotkie_ah_nie_wrzask(self):
        from collections import namedtuple
        Tekst = namedtuple("Tekst", "zrodlo")
        teksty = {
            "k-wrzask": Tekst("啊————————！"),
            "0aaa-szara": Tekst("啊      "),
            "k-ah": Tekst("啊"),
            "k-ah-wykrz": Tekst("啊！"),
        }
        self.assertEqual(self.ck.mapa_wykrzyknikow(teksty), {"啊": "k-ah"})


class TestKwestieZapasowe(unittest.TestCase):
    """Tryb zapasowy: cutsceny bez okna puli dopasowane do całego wyciągu."""

    def setUp(self):
        from tools import cutsceny_kolejnosc_kwestii as ck
        self.ck = ck
        self.glob = {ck._norm("还活着吗"): ["k-zywy"],
                     ck._norm("我还以为"): ["k-myslalem"],
                     ck._norm("终于可以给你用冻死骨了"): ["k-toksyna"]}
        self.pula = {}
        self.poczatki = ck.indeks_poczatkow(self.glob, self.pula)

    def test_dopasowanie_calej_kwestii_w_kolejnosci_czasu(self):
        kwestie = [
            {"t": 5.0, "zh": "我还以为", "audio": "vo_x_qunza_2"},
            {"t": 1.0, "zh": "还活着吗（冷笑）", "audio": "vo_x_qunza_1"},
        ]
        wynik = self.ck.kwestie_zapasowe(kwestie, self.glob, self.pula, self.poczatki)
        self.assertEqual([r["k"] for r in wynik], ["k-zywy", "k-myslalem"])
        self.assertEqual(wynik[0]["a"], "vo_x_qunza_1")
        self.assertNotIn("w", wynik[0])    # klucz spoza puli nie dostaje wiersza

    def test_opisy_sceniczne_pomijane(self):
        kwestie = [{"t": 0.5, "zh": "会武胜利被击败气息（视频）", "audio": "vo_x_1"},
                   {"t": 1.0, "zh": "黑市追逃群杂气息", "audio": "vo_x_2"},
                   {"t": 2.0, "zh": "（轻轻叹气）", "audio": "vo_x_3"}]
        self.assertEqual(self.ck.kwestie_zapasowe(kwestie, self.glob, self.pula,
                                                  self.poczatki), [])

    def test_segmentacja_wymaga_pelnego_pokrycia(self):
        # „还活着吗" + nieznany ogon dłuższy niż 1 znak → bez zgadywania
        kwestie = [{"t": 1.0, "zh": "还活着吗某某某某", "audio": "vo_x_1"}]
        self.assertEqual(self.ck.kwestie_zapasowe(kwestie, self.glob, self.pula,
                                                  self.poczatki), [])


class TestMowcyCutsceny(unittest.TestCase):
    """Propagacja mówców po plikach nagrań — tylko w obrębie jednej cutsceny."""

    def _mowcy(self, klucze, audio_kluczy, audio_napisow=None, wiersze=None):
        return cz._mowcy_cutsceny(klucze, None, {}, {}, wiersze or {},
                                  audio_napisow or {}, audio_kluczy)

    def test_jeden_plik_audio_jeden_glos(self):
        # cztery wiersze nagrania npc_07; kontekst zna Ruby dla dwóch (hx)
        wiersze = {"k1": 1, "k2": 2, "k3": 3, "k4": 4}
        audio_napisow = {2: "vo_sm_sxdm4_cs_zlxl_hx_05", 3: "vo_sm_sxdm4_cs_zlxl_hx_06"}
        audio_kluczy = {k: "vo_sm_sxdm7_npc_07" for k in wiersze}
        mowcy = self._mowcy(list(wiersze), audio_kluczy, audio_napisow, wiersze)
        self.assertEqual(set(mowcy.values()), {"Ruby"})

    def test_rodzina_npc_wymaga_dwoch_zgodnych_nagran(self):
        # jedno zidentyfikowane nagranie rodziny to za mało na propagację
        wiersze = {"k1": 1, "k2": 2}
        audio_napisow = {1: "vo_sm_sxdm4_cs_zlxl_hx_02"}
        audio_kluczy = {"k1": "vo_x_npc_01", "k2": "vo_x_npc_02"}
        mowcy = self._mowcy(["k1", "k2"], audio_kluczy, audio_napisow, wiersze)
        self.assertEqual(mowcy, {"k1": "Ruby", "k2": ""})
        # dwa zgodne nagrania rodziny — trzecie dostaje etykietę
        wiersze = {"k1": 1, "k2": 2, "k3": 3}
        audio_napisow = {1: "vo_sm_sxdm4_cs_zlxl_hx_02", 2: "vo_sm_sxdm4_cs_zlxl_hx_03"}
        audio_kluczy = {"k1": "vo_x_npc_01", "k2": "vo_x_npc_02", "k3": "vo_x_npc_03"}
        mowcy = self._mowcy(["k1", "k2", "k3"], audio_kluczy, audio_napisow, wiersze)
        self.assertEqual(mowcy["k3"], "Ruby")

    def test_niezgodnosc_blokuje_propagacje(self):
        # rodzina npc z dwoma różnymi postaciami — nic nie zgadujemy
        wiersze = {"k1": 1, "k2": 2, "k3": 3}
        audio_napisow = {1: "vo_sm_sxdm4_cs_zlxl_hx_02", 2: "vo_sm_sxdm7_pma_01"}
        audio_kluczy = {"k1": "vo_x_npc_01", "k2": "vo_x_npc_02", "k3": "vo_x_npc_03"}
        mowcy = self._mowcy(["k1", "k2", "k3"], audio_kluczy, audio_napisow, wiersze)
        self.assertEqual(mowcy["k3"], "")

    def test_gracz_wprost_z_cine(self):
        mowcy = self._mowcy(["k1"], {"k1": "vo_sm_sxdm7_pma_04"})
        self.assertEqual(mowcy["k1"], "Youxia")


class TestNaglowekSasiadow(unittest.TestCase):
    """Oś `.cine` jest źródłem prawdy: sąsiedzi puli nie wchodzą na tę cutscenę."""

    def setUp(self):
        self.zh_map = {"a1": "不是说好一起去将军祠吗", "a2": "怎么睡着了呀",
                       "w1": "不是说好一起去将军祠吗怎么睡着了",
                       "o1": "我兄弟集八俊护黎庶", "o2": "擂鼓三声调兵遣将"}
        self.wiersz = {"n": 30161, "kn": ["a1", "a2", "w1", "o1", "o2"], "k": []}
        self.wiersze = {"a1": 591148, "a2": 591149, "w1": 590157,
                        "o1": 591128, "o2": 591139}
        self.pl = {k: f"PL {k}" for k in self.zh_map}
        self.kolejnosc = [[{"w": 591148, "k": "a1", "t": 1.0},
                           {"w": 591149, "k": "a2", "t": 2.0}]]

    def test_cine_nie_lknie_recytacji_sasiada(self):
        klucze, podtytuly, _ = cz._napisy_cutsceny(self.wiersz, self.wiersze, self.pl,
                                                   kolejnosc=self.kolejnosc,
                                                   zh=self.zh_map.get)
        self.assertEqual(klucze, ["a1", "a2"])
        self.assertNotIn("o1", klucze)
        self.assertNotIn("o2", klucze)
        self.assertFalse(podtytuly)

    def test_bez_osi_cine_pula_nadal_sie_dzieli(self):
        klucze, podtytuly, _ = cz._napisy_cutsceny(self.wiersz, self.wiersze, self.pl,
                                                   zh=self.zh_map.get)
        self.assertIn("o1", klucze)
        self.assertTrue(podtytuly)


class TestWlascicieleNagran(unittest.TestCase):
    """Rdzeń nagrania wskazuje cudzą cutscenę tylko, gdy jest jednoznaczny."""

    @classmethod
    def setUpClass(cls):
        cls.mapa = cz._wlasciciele_nagran("index")

    def test_nagranie_nzgzcj_nalezy_do_30435(self):
        self.assertEqual(self.mapa.get("vo_ss_axnzgzgcm9_cs_nzgzcj_dqgz"), 30435)

    def test_placeholdery_wielu_cutscen_odpadaja(self):
        self.assertNotIn("vo_sm_sxdm7_npc", self.mapa)

    def test_naglowek_wskazuje_wlasciciela(self):
        # bez osi `.cine` sąsiad z nagraniem 30435 dostaje jawny nagłówek
        zh_map = {"a1": "不是说好一起去将军祠吗", "o1": "像你这样的人哪怕多救一人",
                  "o2": "只怕南北之势多救一人便多伤一人"}
        wiersz = {"n": 30161, "kn": ["a1", "o1", "o2"], "k": []}
        wiersze = {"a1": 591148, "o1": 590050, "o2": 590051}
        pl = {k: f"PL {k}" for k in zh_map}
        audio = {590050: "vo_ss_axnzgzgcm9_cs_nzgzcj_dqgz"}
        _, podtytuly, _ = cz._napisy_cutsceny(wiersz, wiersze, pl, audio, None,
                                              zh=zh_map.get,
                                              wlasciciele={"vo_ss_axnzgzgcm9_cs_nzgzcj_dqgz": 30435})
        self.assertTrue(any("nagrania cutsceny 30435" in n for n in podtytuly.values()),
                        list(podtytuly.values()))


class TestCineWalkiWorldBossa(unittest.TestCase):
    """`pyryw/sq001_pyscc` i `sq002_pyszc` to fazy walki, nie wariant 30161."""

    def test_faza_z_nazwy_filmu(self):
        self.assertEqual(cz._faza_cine_walki("Char/e_01_cutscene/pyryw/sq001_pyscc/sq001_pyscc.cine"), "cc")
        self.assertEqual(cz._faza_cine_walki("Char/e_01_cutscene/pyryw/sq002_pyszc/sq002_pyszc.cine"), "zc")
        self.assertEqual(cz._faza_cine_walki("Char/e_01_cutscene/pys1/sq001_pys1cc/sq001_pys1cc.cine"), "cc")
        self.assertIsNone(cz._faza_cine_walki("Char/e_01_cutscene/cehua_xinshoucun/sq001_zlxl.cine"))

    def test_split_recytacji_na_leigu(self):
        zh = {"a": "我兄弟集八俊", "b": "贼子", "c": "擂鼓三声调兵遣将", "d": "行不得也哥哥"}
        fazy = cz._podziel_osierocone_fazy(["a", "b", "c", "d"], zh.get)
        self.assertEqual(fazy["cc"], ["a", "b"])
        self.assertEqual(fazy["zc"], ["c", "d"])
