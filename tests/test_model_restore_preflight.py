from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tools import model_restore_preflight as restore
from tools import translation_bundle as bundles


ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
RECORDED = FIXTURES / "synthetic_restore_recorded.json"
OBSERVED = FIXTURES / "synthetic_restore_observed.json"
SCRIPT = ROOT / "tools" / "model_restore_preflight.py"


class RestoreModelTests(unittest.TestCase):
    def setUp(self):
        self.recorded = bundles.load_json(RECORDED)
        self.observed = bundles.load_json(OBSERVED)

    def same_build(self):
        observation = deepcopy(self.observed)
        observation["build_id"] = self.recorded["build_id"]
        for entry, item in zip(self.recorded["files"], observation["files"]):
            item["current_sha256"] = entry["patched_sha256"]
            item["backup_sha256"] = entry["original_sha256"]
        return observation

    def test_game_update_blocks_even_when_one_patched_file_survives(self):
        report, details = restore.model_restore(self.recorded, self.observed)
        self.assertEqual(report["decision"], "blocked_build_mismatch")
        self.assertFalse(report["build_labels_match"])
        self.assertEqual(report["counts"]["current_matches_recorded_patch"], 1)
        self.assertEqual(report["counts"]["current_unrecognized"], 1)
        self.assertEqual(report["counts"]["backup_matches_recorded_original"], 2)
        self.assertFalse(report["labels_and_hashes_verified"])
        self.assertFalse(report["filesystem_or_process_checks_performed"])
        self.assertFalse(report["writes_performed"])
        self.assertFalse(report["write_authorized"])
        self.assertEqual(details["items"][1]["current_state"], "current_unrecognized")

    def test_same_build_and_hashes_still_require_further_preflight(self):
        report, details = restore.model_restore(self.recorded, self.same_build())
        self.assertEqual(report["decision"], "needs_further_preflight")
        self.assertEqual(report["counts"]["current_matches_recorded_patch"], 2)
        self.assertTrue(report["build_labels_match"])
        self.assertFalse(report["write_authorized"])
        self.assertFalse(details["writes_performed"])

    def test_build_change_blocks_even_if_old_original_is_still_present(self):
        observed = deepcopy(self.observed)
        for entry, item in zip(self.recorded["files"], observed["files"]):
            item["current_sha256"] = entry["original_sha256"]
        report, _ = restore.model_restore(self.recorded, observed)
        self.assertEqual(report["counts"]["current_matches_recorded_original"], 2)
        self.assertEqual(report["decision"], "blocked_build_mismatch")
        self.assertFalse(report["write_authorized"])

    def test_same_build_original_matches_are_noop_not_authenticity_proof(self):
        observed = self.same_build()
        for entry, item in zip(self.recorded["files"], observed["files"]):
            item["current_sha256"] = entry["original_sha256"]
        report, _ = restore.model_restore(self.recorded, observed)
        self.assertEqual(report["decision"], "no_patched_bytes_observed")
        self.assertEqual(report["counts"]["current_matches_recorded_original"], 2)
        self.assertFalse(report["labels_and_hashes_verified"])
        self.assertFalse(report["write_authorized"])

    def test_identical_patched_and_original_hash_is_treated_as_noop(self):
        recorded = deepcopy(self.recorded)
        observed = self.same_build()
        for entry, item in zip(recorded["files"], observed["files"]):
            entry["patched_sha256"] = entry["original_sha256"]
            item["current_sha256"] = entry["original_sha256"]
        report, _ = restore.model_restore(recorded, observed)
        self.assertEqual(report["decision"], "no_patched_bytes_observed")
        self.assertEqual(report["counts"]["current_matches_recorded_patch"], 0)

    def test_same_build_different_current_file_or_bad_backup_blocks_everything(self):
        cases = (
            ("current_sha256", "f" * 64, "current_unrecognized"),
            ("current_sha256", None, "current_unavailable"),
            ("backup_sha256", "f" * 64, "backup_mismatch"),
            ("backup_sha256", None, "backup_unavailable"),
        )
        for field, value, count in cases:
            with self.subTest(field=field, value=value):
                observed = self.same_build()
                observed["files"][0][field] = value
                report, _ = restore.model_restore(self.recorded, observed)
                self.assertEqual(report["decision"], "blocked_conflicts")
                self.assertEqual(report["counts"][count], 1)
                self.assertFalse(report["write_authorized"])

    def test_wrong_scope_blocks_even_if_build_and_hashes_match(self):
        observed = self.same_build()
        observed["scope_id"] = "some-other-installation"
        report, _ = restore.model_restore(self.recorded, observed)
        self.assertEqual(report["decision"], "blocked_scope_mismatch")
        self.assertFalse(report["scope_labels_match"])
        self.assertFalse(report["write_authorized"])

    def test_changed_or_missing_file_set_fails_closed(self):
        missing = self.same_build()
        missing["files"].pop()
        with self.assertRaisesRegex(bundles.BundleError, "file set mismatch"):
            restore.model_restore(self.recorded, missing)
        extra = self.same_build()
        item = deepcopy(extra["files"][0])
        item["id"] = "synthetic/unexpected"
        extra["files"].append(item)
        with self.assertRaisesRegex(bundles.BundleError, "file set mismatch"):
            restore.model_restore(self.recorded, extra)

    def test_rejects_duplicate_ids_invalid_hashes_and_unexpected_fields(self):
        cases = (
            ("duplicate", lambda doc: doc["files"].append(deepcopy(doc["files"][0]))),
            ("uppercase hash", lambda doc: doc["files"][0].update(current_sha256="A" * 64)),
            ("short hash", lambda doc: doc["files"][0].update(backup_sha256="abc")),
            ("bad schema", lambda doc: doc.update(schema=True)),
            ("extra root", lambda doc: doc.update(path="SECRET_PATH")),
            ("extra file", lambda doc: doc["files"][0].update(path="SECRET_PATH")),
            ("no files", lambda doc: doc.update(files=[])),
        )
        for name, mutate in cases:
            with self.subTest(name=name):
                changed = self.same_build()
                mutate(changed)
                with self.assertRaises(bundles.BundleError) as caught:
                    restore.model_restore(self.recorded, changed)
                self.assertNotIn("SECRET_PATH", str(caught.exception))
        changed = deepcopy(self.recorded)
        changed["files"][0]["original_sha256"] = None
        with self.assertRaises(bundles.BundleError):
            restore.model_restore(changed, self.same_build())

    def test_file_count_limit_fails_closed(self):
        with patch.object(restore, "MAX_FILES", 1):
            with self.assertRaises(bundles.BundleError):
                restore.model_restore(self.recorded, self.same_build())

    def test_invariant_all_state_combinations_never_authorize_writes(self):
        for build in ("same", "different"):
            for current in ("original", "patch", "unknown", "unavailable"):
                for backup in ("original", "unknown", "unavailable"):
                    with self.subTest(build=build, current=current, backup=backup):
                        observation = self.same_build()
                        if build == "different":
                            observation["build_id"] = "synthetic-other-build"
                        entry = self.recorded["files"][0]
                        observation["files"][0]["current_sha256"] = {
                            "original": entry["original_sha256"],
                            "patch": entry["patched_sha256"],
                            "unknown": "f" * 64,
                            "unavailable": None,
                        }[current]
                        observation["files"][0]["backup_sha256"] = {
                            "original": entry["original_sha256"],
                            "unknown": "e" * 64,
                            "unavailable": None,
                        }[backup]
                        report, _ = restore.model_restore(self.recorded, observation)
                        self.assertFalse(report["write_authorized"])
                        self.assertFalse(report["writes_performed"])
                        if build == "different":
                            self.assertEqual(report["decision"], "blocked_build_mismatch")
                        elif current in ("unknown", "unavailable") or backup != "original":
                            self.assertEqual(report["decision"], "blocked_conflicts")

    def test_model_does_not_mutate_inputs_or_use_network(self):
        before = deepcopy((self.recorded, self.observed))
        with patch("socket.socket", side_effect=AssertionError("network access")):
            first = restore.model_restore(self.recorded, self.observed)
            second = restore.model_restore(self.recorded, self.observed)
        self.assertEqual(first, second)
        self.assertEqual((self.recorded, self.observed), before)
        rendered = json.dumps(first[0])
        self.assertNotIn("synthetic/base", rendered)
        self.assertNotIn("0" * 64, rendered)
        self.assertIn("synthetic/base", json.dumps(first[1]))


class RestoreModelCliTests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *map(str, args)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

    def test_cli_summary_and_explicit_details(self):
        summary = self.run_cli("--recorded", RECORDED, "--observed", OBSERVED)
        self.assertEqual(summary.returncode, 0, summary.stderr)
        self.assertEqual(json.loads(summary.stdout)["decision"], "blocked_build_mismatch")
        self.assertNotIn(str(ROOT), summary.stdout + summary.stderr)
        self.assertNotIn("synthetic/base", summary.stdout)
        detail = self.run_cli("--recorded", RECORDED, "--observed", OBSERVED, "--details")
        self.assertEqual(detail.returncode, 0, detail.stderr)
        self.assertEqual(len(json.loads(detail.stdout)["items"]), 2)
        self.assertIn("synthetic/base", detail.stdout)

    def test_cli_does_not_modify_input_files(self):
        with tempfile.TemporaryDirectory(prefix="private-restore-model-") as temp:
            directory = Path(temp)
            recorded, observed = directory / "private-recorded.json", directory / "private-observed.json"
            recorded.write_bytes(RECORDED.read_bytes())
            observed.write_bytes(OBSERVED.read_bytes())
            before = {path.name: path.read_bytes() for path in directory.iterdir()}
            process = self.run_cli("--recorded", recorded, "--observed", observed, "--details")
            self.assertEqual(process.returncode, 0, process.stderr)
            self.assertNotIn(temp, process.stdout + process.stderr)
            self.assertEqual(before, {path.name: path.read_bytes() for path in directory.iterdir()})

    def test_cli_invalid_observations_do_not_disclose_paths_or_print_partial_report(self):
        with tempfile.TemporaryDirectory(prefix="private-restore-model-") as temp:
            bad = Path(temp) / "SECRET_PATH.json"
            changed = bundles.load_json(OBSERVED)
            changed["files"].pop()
            bad.write_text(json.dumps(changed), encoding="utf-8")
            result = self.run_cli("--recorded", RECORDED, "--observed", bad)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stdout, "")
            self.assertNotIn("SECRET_PATH", result.stderr)
            self.assertNotIn(temp, result.stderr)

    def test_argument_errors_are_redacted(self):
        result = self.run_cli("--recorded", RECORDED, "--observed", OBSERVED, "--bad", "SECRET_ARG")
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("SECRET_ARG", result.stdout + result.stderr)
        self.assertNotIn(str(RECORDED), result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
