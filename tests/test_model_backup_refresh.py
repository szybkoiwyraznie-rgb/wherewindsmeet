from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tools import model_backup_refresh as refresh
from tools import translation_bundle as bundles


ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
RECORDED = FIXTURES / "synthetic_restore_recorded.json"
OBSERVED = FIXTURES / "synthetic_restore_observed.json"
REFERENCE = FIXTURES / "synthetic_refresh_reference.json"
SCRIPT = ROOT / "tools" / "model_backup_refresh.py"


class BackupRefreshTests(unittest.TestCase):
    def setUp(self):
        self.old = bundles.load_json(RECORDED)
        self.observed = bundles.load_json(OBSERVED)
        self.reference = bundles.load_json(REFERENCE)

    def model(self, old=None, observed=None, reference=None):
        return refresh.model_refresh(
            self.old if old is None else old,
            self.observed if observed is None else observed,
            self.reference if reference is None else reference,
            assume_trusted_new_reference=True,
        )

    def test_one_unchanged_patch_and_one_new_original(self):
        report, details = self.model()
        self.assertEqual(report["decision"], "needs_further_preflight")
        self.assertTrue(report["build_label_changed"])
        self.assertEqual(report["counts"]["unchanged_patch"], 1)
        self.assertEqual(report["counts"]["install_from_clean"], 1)
        self.assertEqual(report["counts"]["backup_retained"], 1)
        self.assertEqual(report["counts"]["backup_stage_new_after_verification"], 1)
        self.assertEqual(details["items"], [
            {"id": "synthetic/base", "hypothetical_file_state": "unchanged_patch",
             "hypothetical_backup_action": "backup_retained"},
            {"id": "synthetic/layer", "hypothetical_file_state": "install_from_clean",
             "hypothetical_backup_action": "backup_stage_new_after_verification"},
        ])
        self.assertTrue(report["new_reference_asserted_trusted"])
        self.assertFalse(report["new_reference_or_hashes_verified"])
        self.assertFalse(report["semantic_dependencies_verified"])
        self.assertFalse(report["filesystem_or_process_checks_performed"])
        self.assertFalse(report["writes_performed"])
        self.assertFalse(report["write_authorized"])
        self.assertFalse(report["old_backup_deletion_authorized"])

    def test_translation_update_never_backs_up_old_patched_bytes(self):
        reference = deepcopy(self.reference)
        reference["files"][0]["patched_sha256"] = "a" * 64
        report, details = self.model(reference=reference)
        self.assertEqual(report["counts"]["replace_previous_patch"], 1)
        self.assertEqual(details["items"][0]["hypothetical_backup_action"], "backup_retained")
        self.assertEqual(report["counts"]["backup_stage_new_after_verification"], 1)
        self.assertFalse(report["write_authorized"])

    def test_old_patch_is_rejected_when_new_original_changed(self):
        reference = deepcopy(self.reference)
        reference["files"][0]["original_sha256"] = "a" * 64
        report, details = self.model(reference=reference)
        self.assertEqual(report["decision"], "blocked_conflicts")
        self.assertEqual(report["counts"]["blocked_stale_patch"], 1)
        self.assertIsNone(details["items"][0]["hypothetical_backup_action"])
        self.assertFalse(report["write_authorized"])

    def test_recorded_patch_is_not_backed_up_even_if_new_reference_equals_it(self):
        reference = deepcopy(self.reference)
        reference["files"][0]["original_sha256"] = self.old["files"][0]["patched_sha256"]
        report, details = self.model(reference=reference)
        self.assertEqual(report["decision"], "blocked_conflicts")
        self.assertEqual(details["items"][0]["hypothetical_file_state"], "blocked_stale_patch")
        self.assertIsNone(details["items"][0]["hypothetical_backup_action"])
        self.assertFalse(report["old_backup_deletion_authorized"])

    def test_already_clean_with_no_patch_is_not_rewritten(self):
        reference = deepcopy(self.reference)
        reference["files"][1]["patched_sha256"] = reference["files"][1]["original_sha256"]
        report, details = self.model(reference=reference)
        self.assertEqual(report["counts"]["unchanged_clean"], 1)
        self.assertEqual(report["counts"]["backup_retained_old_build_only"], 1)
        self.assertEqual(details["items"][1]["hypothetical_backup_action"], "backup_retained_old_build_only")
        self.assertFalse(report["write_authorized"])

    def test_verified_clean_same_as_old_original_reuses_backup(self):
        observation = deepcopy(self.observed)
        reference = deepcopy(self.reference)
        observation["files"][0]["current_sha256"] = self.old["files"][0]["original_sha256"]
        report, details = self.model(observed=observation, reference=reference)
        self.assertEqual(report["counts"]["install_from_clean"], 2)
        self.assertEqual(details["items"][0]["hypothetical_backup_action"], "backup_retained")

    def test_any_invalid_backup_or_unrecognized_current_blocks_the_whole_plan(self):
        cases = (
            ("backup_sha256", None, "blocked_invalid_previous_backup"),
            ("backup_sha256", "a" * 64, "blocked_invalid_previous_backup"),
            ("current_sha256", None, "blocked_current_unavailable"),
            ("current_sha256", "b" * 64, "blocked_unknown_current"),
        )
        for field, value, count in cases:
            with self.subTest(field=field, value=value):
                observation = deepcopy(self.observed)
                observation["files"][1][field] = value
                report, _ = self.model(observed=observation)
                self.assertEqual(report["decision"], "blocked_conflicts")
                self.assertEqual(report["counts"][count], 1)
                self.assertFalse(report["write_authorized"])
                self.assertFalse(report["old_backup_deletion_authorized"])

    def test_different_scope_or_new_reference_build_blocks(self):
        observation = deepcopy(self.observed)
        observation["scope_id"] = "different-installation"
        report, _ = self.model(observed=observation)
        self.assertEqual(report["decision"], "blocked_scope_mismatch")
        reference = deepcopy(self.reference)
        reference["build_id"] = "not-the-observed-build"
        report, _ = self.model(reference=reference)
        self.assertEqual(report["decision"], "blocked_new_reference_build_mismatch")
        self.assertFalse(report["new_reference_build_label_matches"])

    def test_all_three_file_sets_must_be_complete_and_unique(self):
        for name in ("old", "observed", "reference"):
            kwargs = {"old": deepcopy(self.old), "observed": deepcopy(self.observed),
                      "reference": deepcopy(self.reference)}
            kwargs[name]["files"].pop()
            with self.subTest(name=name), self.assertRaises(bundles.BundleError):
                self.model(**kwargs)
        duplicate = deepcopy(self.reference)
        duplicate["files"].append(deepcopy(duplicate["files"][0]))
        with self.assertRaises(bundles.BundleError):
            self.model(reference=duplicate)
        bad_hash = deepcopy(self.reference)
        bad_hash["files"][0]["original_sha256"] = "ABC"
        with self.assertRaises(bundles.BundleError):
            self.model(reference=bad_hash)

    def test_assertion_is_required_and_not_verification(self):
        for value in (False, None, "yes", 1):
            with self.subTest(value=value), self.assertRaises(bundles.BundleError):
                refresh.model_refresh(self.old, self.observed, self.reference,
                                      assume_trusted_new_reference=value)
        report, _ = self.model()
        self.assertTrue(report["new_reference_asserted_trusted"])
        self.assertFalse(report["new_reference_or_hashes_verified"])
        self.assertFalse(report["write_authorized"])

    def test_combinations_never_authorize_write_or_deletion(self):
        for current in ("old-patch", "new-clean", "unknown", "unavailable"):
            for backup in ("correct", "invalid", "missing"):
                for build in ("matching-reference", "different-reference"):
                    with self.subTest(current=current, backup=backup, build=build):
                        observation = deepcopy(self.observed)
                        reference = deepcopy(self.reference)
                        observation["files"][0]["current_sha256"] = {
                            "old-patch": self.old["files"][0]["patched_sha256"],
                            "new-clean": reference["files"][0]["original_sha256"],
                            "unknown": "f" * 64,
                            "unavailable": None,
                        }[current]
                        observation["files"][0]["backup_sha256"] = {
                            "correct": self.old["files"][0]["original_sha256"],
                            "invalid": "e" * 64,
                            "missing": None,
                        }[backup]
                        if build == "different-reference":
                            reference["build_id"] = "unmatched-build"
                        report, _ = self.model(observed=observation, reference=reference)
                        self.assertFalse(report["writes_performed"])
                        self.assertFalse(report["write_authorized"])
                        self.assertFalse(report["old_backup_deletion_authorized"])
                        if build == "different-reference":
                            self.assertEqual(report["decision"], "blocked_new_reference_build_mismatch")
                        elif backup != "correct" or current in ("unknown", "unavailable"):
                            self.assertEqual(report["decision"], "blocked_conflicts")

    def test_model_is_deterministic_redacted_and_has_no_side_effects(self):
        before = deepcopy((self.old, self.observed, self.reference))
        with patch("socket.socket", side_effect=AssertionError("network access")):
            first = self.model()
            second = self.model()
        self.assertEqual(first, second)
        self.assertEqual((self.old, self.observed, self.reference), before)
        report = json.dumps(first[0])
        self.assertNotIn("synthetic/base", report)
        self.assertNotIn("0" * 64, report)
        self.assertIn("synthetic/base", json.dumps(first[1]))


class BackupRefreshCliTests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)],
                              capture_output=True, text=True, encoding="utf-8", check=False)

    def test_cli_summary_details_and_required_assertion(self):
        common = ["--recorded", RECORDED, "--observed", OBSERVED, "--new-reference", REFERENCE]
        missing = self.run_cli(*common)
        self.assertEqual(missing.returncode, 2)
        self.assertNotIn(str(ROOT), missing.stderr)
        summary = self.run_cli(*common, "--assume-trusted-new-reference")
        self.assertEqual(summary.returncode, 0, summary.stderr)
        self.assertFalse(json.loads(summary.stdout)["write_authorized"])
        self.assertNotIn("synthetic/base", summary.stdout)
        detail = self.run_cli(*common, "--assume-trusted-new-reference", "--details")
        self.assertEqual(detail.returncode, 0, detail.stderr)
        self.assertEqual(len(json.loads(detail.stdout)["items"]), 2)
        self.assertIn("synthetic/base", detail.stdout)
        self.assertNotIn(str(ROOT), detail.stdout + detail.stderr)

    def test_invalid_reference_is_redacted_and_has_no_partial_output(self):
        with tempfile.TemporaryDirectory(prefix="secret-refresh-") as temp:
            bad = Path(temp) / "private.json"
            bad.write_text('{"SECRET":"a","SECRET":"b"}', encoding="utf-8")
            result = self.run_cli("--recorded", RECORDED, "--observed", OBSERVED, "--new-reference", bad,
                                  "--assume-trusted-new-reference", "--details")
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stdout, "")
            self.assertNotIn("SECRET", result.stderr)
            self.assertNotIn(temp, result.stderr)
            bad.write_text("{}", encoding="utf-8")
            result = self.run_cli("--recorded", RECORDED, "--observed", OBSERVED, "--new-reference", bad,
                                  "--assume-trusted-new-reference")
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stdout, "")
            self.assertNotIn(temp, result.stderr)

    def test_cli_does_not_change_input_files(self):
        with tempfile.TemporaryDirectory(prefix="synthetic-refresh-") as temp:
            directory = Path(temp)
            paths = [directory / name for name in ("old.json", "observed.json", "reference.json")]
            for src, dst in zip((RECORDED, OBSERVED, REFERENCE), paths):
                dst.write_bytes(src.read_bytes())
            before = {path.name: path.read_bytes() for path in paths}
            result = self.run_cli("--recorded", paths[0], "--observed", paths[1],
                                  "--new-reference", paths[2], "--assume-trusted-new-reference", "--details")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn(temp, result.stdout + result.stderr)
            self.assertEqual(before, {path.name: path.read_bytes() for path in paths})
            self.assertEqual(sorted(path.name for path in directory.iterdir()), sorted(before))


if __name__ == "__main__":
    unittest.main()
