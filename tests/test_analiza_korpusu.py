from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from tools import analiza_korpusu


ROOT = Path(__file__).resolve().parent.parent


class CorpusAnalysisTests(unittest.TestCase):
    """Statystyki liczone z indeksu w repozytorium — bez gry i bez Dysku."""

    @classmethod
    def setUpClass(cls):
        cls.scenes, cls.texts = analiza_korpusu.load(ROOT / "index")
        cls.manifest = json.loads((ROOT / "index" / "manifest.json").read_text(encoding="utf-8"))

    def test_counts_agree_with_the_manifest(self):
        self.assertEqual(len(self.scenes), self.manifest["liczby"]["scen"])
        self.assertEqual(len(self.texts), self.manifest["liczby"]["unikalnych_tekstow"])
        lines = sum(len(scene["linie"]) for scene in self.scenes)
        self.assertEqual(lines, self.manifest["liczby"]["kwestii"])

    def test_dialogue_groups_match_the_registry_coverage(self):
        summary, per_group = analiza_korpusu.analyse_dialogues(self.scenes)
        self.assertEqual(summary["grup_dialogowych"],
                         self.manifest["pokrycie"]["scen_z_dialog_no"])
        self.assertEqual(summary["grup_z_wieloma_timeline"],
                         len(analiza_korpusu.analyse_completeness(
                             self.scenes, self.texts, self.manifest)["grupy_z_wieloma_timeline"]))
        for group in per_group:
            # Kazda kwestia grupy ma dokladnie jednego mówcę z obsady.
            self.assertEqual(sum(row["kwestii"] for row in group["mowcy"]), group["kwestii"])
            if group["mowcow"]:
                self.assertGreaterEqual(group["kwestii"], group["mowcow"])

    def test_line_order_is_consistent_and_duration_is_not_a_bound(self):
        report = analiza_korpusu.analyse_chronology(self.scenes)
        self.assertEqual(report["scen_z_niemonotonicznym_czasem"], 0)
        self.assertEqual(report["scen_z_linia_bez_czasu"], 0)
        # total_duration is not a trustworthy scene bound: some lines fall outside.
        self.assertGreater(report["scen_z_linia_poza_oknem_czasu"], 0)
        self.assertLess(report["scen_z_linia_poza_oknem_czasu"], 0.05 * report["scen"])

    def test_context_fields_are_reported_with_real_gaps(self):
        report = analiza_korpusu.analyse_context(self.scenes)
        self.assertEqual(report["kwestii"], self.manifest["liczby"]["kwestii"])
        self.assertEqual(report["uzupelnienie_pol_linii"]["czas"], report["kwestii"])
        self.assertEqual(report["uzupelnienie_pol_linii"]["source_id"], report["kwestii"])
        self.assertLess(report["uzupelnienie_pol_linii"]["speaker_no"], report["kwestii"])

    def test_tool_writes_five_reports(self):
        with tempfile.TemporaryDirectory(prefix="wwm-analiza-") as temp:
            out = Path(temp) / "analiza"
            code = analiza_korpusu.main(["--indeks", str(ROOT / "index"), "--wyj", str(out)])
            self.assertEqual(code, 0)
            names = sorted(path.name for path in out.iterdir())
            self.assertEqual(names, ["chronologia.json", "co_brakuje.json", "dialog_mowca.json",
                                     "do_decyzji.json", "elementy_poza_scenami.json",
                                     "kompletnosc.json", "kontekst.json",
                                     "mapowanie_mowcow.json"])
            for path in out.iterdir():
                json.loads(path.read_text(encoding="utf-8"))

    def test_tool_writes_per_group_only_on_request(self):
        with tempfile.TemporaryDirectory(prefix="wwm-analiza-") as temp:
            out = Path(temp) / "analiza"
            analiza_korpusu.main(["--indeks", str(ROOT / "index"), "--wyj", str(out)])
            self.assertFalse((out / "dialog_mowca_grupy.jsonl").exists())
            out2 = Path(temp) / "grupy"
            analiza_korpusu.main(["--indeks", str(ROOT / "index"), "--wyj", str(out2), "--grupy"])
            rows = [json.loads(line) for line in
                    (out2 / "dialog_mowca_grupy.jsonl").read_text(encoding="utf-8").splitlines()
                    if line]
            self.assertEqual(len(rows), self.manifest["pokrycie"]["scen_z_dialog_no"])

    def test_offscene_report_adds_up(self):
        report = analiza_korpusu.analyse_offscene(self.scenes, self.texts)
        self.assertEqual(report["wpisy_przypisane_do_scen"], len(self.texts))
        self.assertEqual(report["wpisy_poza_scenami"],
                         analiza_korpusu.MAP_ENTRIES_FILLED - len(self.texts))
        self.assertEqual(report["udzial_poza_scenami_procent"], 90.3)
        # Sceny nie odwoluja sie do tekstow, ktorych nie ma w indeksie.
        self.assertEqual(report["powiazania_scena_tekst"]["text_id_w_scenach_bez_tekstu"], 0)
        self.assertEqual(report["powiazania_scena_tekst"]["teksty_nieuzywane_w_scenach"], 0)
        variants = report["wariant_tekstu_mapa_vs_scena"]
        self.assertEqual(variants["identycznych"], 0)
        self.assertEqual(variants["tekstow_z_dluzsza_wersja_w_mapie"],
                         self.manifest["liczby"]["tekstow_z_dluzsza_wersja_mapy"])
        self.assertEqual(variants["tekstow_z_dluzsza_wersja_w_mapie"],
                         variants["identycznych"] + variants["rozni_sie_tylko_lamaniem_wiersza"]
                         + variants["rozni_sie_trescia"])

    def test_decision_report_lists_what_needs_a_human(self):
        summary, per_group = analiza_korpusu.analyse_dialogues(self.scenes)
        report = analiza_korpusu.analyse_decisions(per_group)
        multi = report["grupy_z_wieloma_timeline"]
        self.assertEqual(multi["liczb"], summary["grup_z_wieloma_timeline"])
        self.assertEqual(len(multi["lista"]), multi["liczb"])
        for row in multi["lista"]:
            self.assertLessEqual(len(row["pliki"]), row["timelineow"])
        self.assertEqual(report["grupy_tylko_generyczna_obsada"]["liczb"],
                         summary["grup_tylko_generyczna_obsada"])
        self.assertEqual(report["grupy_bez_mowcy"]["liczb"],
                         summary["rozklad_liczby_mowcow"].get("0", 0))
        for key in ("grupy_tylko_generyczna_obsada", "grupy_bez_mowcy"):
            self.assertLessEqual(len(report[key]["proba"]), 20)

    def test_speaker_mapping_is_not_one_to_one(self):
        report = analiza_korpusu.analyse_speakers(self.scenes)
        self.assertEqual(report["kwestii"], self.manifest["liczby"]["kwestii"])
        self.assertEqual(report["kwestii_bez_nazwy_mowcy"], 232)
        # Identyfikatorem mówcy jest para (nazwa, speaker_no), nie sama nazwa.
        self.assertGreater(report["unikalnych_par_mowca_speaker_no"], report["unikalnych_nazw"])
        self.assertGreater(report["nazw_z_wieloma_speaker_no"], 0)
        self.assertGreater(report["speaker_no_z_wieloma_nazwami"], 0)
        self.assertGreaterEqual(report["maks_speaker_no_na_nazwe"], 100)
        self.assertEqual(report["entity_name_w_grze"]["niepustych"], 0)
        self.assertGreater(report["etykiety_dłuższe_niż_20_znaków"]["liczb"], 0)

    def test_map_and_registry_reports_are_opt_in(self):
        with tempfile.TemporaryDirectory(prefix="wwm-analiza-") as temp:
            out = Path(temp) / "analiza"
            analiza_korpusu.main(["--indeks", str(ROOT / "index"), "--wyj", str(out)])
            # Oba pomiary potrzebuja pliku, ktorego nie ma w repo.
            self.assertFalse((out / "mapa_zh_cn.json").exists())
            self.assertFalse((out / "brakujace_dialogi.json").exists())

    def test_blockers_report_names_what_is_needed(self):
        report = analiza_korpusu.analyse_blockers(self.scenes, self.texts)
        self.assertEqual(set(report), {"1_pokrycie_danych", "2_kategorie_tekstow",
                                       "3_mapowanie_mowcow", "4_chronologia"})
        coverage = report["1_pokrycie_danych"]
        self.assertEqual(coverage["rejestr_dialog_timelines"] - coverage["mamy_unikalnych_dialog_no"],
                         coverage["brakuje"])
        self.assertEqual(coverage["brakuje"], 5859)
        for key, value in report.items():
            self.assertTrue(value["co_trzeba_dostarczyc"], key)
            self.assertTrue(value.get("stan") or value.get("stan_procent"), key)

    def test_committed_reports_match_a_fresh_run(self):
        with tempfile.TemporaryDirectory(prefix="wwm-analiza-") as temp:
            out = Path(temp) / "analiza"
            analiza_korpusu.main(["--indeks", str(ROOT / "index"), "--wyj", str(out)])
            for name in ("dialog_mowca.json", "kompletnosc.json", "chronologia.json",
                         "kontekst.json", "elementy_poza_scenami.json", "do_decyzji.json",
                         "mapowanie_mowcow.json", "co_brakuje.json"):
                committed = json.loads((ROOT / "analiza" / name).read_text(encoding="utf-8"))
                fresh = json.loads((out / name).read_text(encoding="utf-8"))
                self.assertEqual(committed, fresh, name)


if __name__ == "__main__":
    unittest.main()
