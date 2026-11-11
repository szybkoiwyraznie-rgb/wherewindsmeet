from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tools import audit_translation_lines as lines
from tools import translation_bundle as bundles


ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
OLD = FIXTURES / "synthetic_update_old.json"
NEW = FIXTURES / "synthetic_update_new.json"
PRIOR = FIXTURES / "synthetic_update_old_return.json"
SCRIPT = ROOT / "tools" / "audit_translation_lines.py"


class AtomicLineAuditTests(unittest.TestCase):
    def setUp(self):
        self.old = bundles.load_json(OLD)
        self.new = bundles.load_json(NEW)
        self.prior = bundles.load_json(PRIOR)

    def audit(self, old=None, new=None, prior=None):
        return lines.audit_lines(
            self.old if old is None else old,
            self.new if new is None else new,
            self.prior if prior is None else prior,
            assume_comparable=True,
        )

    def test_delta_only_has_new_or_changed_source_text(self):
        report, delta, review, backlog = self.audit()
        self.assertEqual([item["id"] for item in delta["items"]], ["demo/reward", "demo/added"])
        self.assertEqual([item["id"] for item in backlog["items"]], ["demo/pending", "demo/unknown"])
        self.assertTrue(all(item["translation"] is None for item in delta["items"]))
        self.assertTrue(all(item["translation"] is None for item in backlog["items"]))
        self.assertEqual(report["counts"], {
            "old_lines": 7,
            "new_lines": 7,
            "new_id_new_source_text": 1,
            "same_id_changed_source_text": 1,
            "new_id_existing_source_review": 1,
            "empty_or_whitespace_source_review": 0,
            "same_id_metadata_only_review": 1,
            "unchanged_unreviewed_candidate": 1,
            "unchanged_explicit_null_backlog": 1,
            "unchanged_unknown_backlog": 1,
            "id_only_in_old": 2,
            "delta_lines": 2,
            "backlog_lines": 2,
            "review_entries": 4,
        })
        self.assertEqual(review["ids_only_in_old"], ["demo/retired", "demo/old-position"])
        self.assertEqual([item["category"] for item in review["items"]], [
            "unchanged_translation_candidate", "changed_line_reference",
            "context_or_tokens_only", "new_id_source_seen_before",
        ])
        self.assertTrue(all(item["review_required"] for item in review["items"]))
        self.assertTrue(all(not item["reused_automatically"] for item in review["items"]))
        self.assertFalse(report["comparison_assumption_verified"])
        self.assertFalse(report["game_compatibility_verified"])
        self.assertTrue(bundles.validate_bundle(self.new, delta)["valid"])
        self.assertTrue(bundles.validate_bundle(self.new, backlog)["valid"])
        with self.assertRaises(bundles.BundleError):
            bundles.validate_bundle(self.old, delta)

    def test_only_changed_and_added_lines_from_long_scene_are_exported(self):
        old = {"schema": 1, "source_id": "invented-old", "records": [
            {"id": f"demo/scene/line-{i:03}", "source": f"Synthetic line {i}.",
             "context": "One invented scene", "protected_tokens": []}
            for i in range(100)
        ]}
        prior = bundles.prepare_bundle(old)
        for item in prior["items"]:
            item["translation"] = "Tłumaczenie testowe."
        new = deepcopy(old)
        new["source_id"] = "invented-new"
        new["records"][50]["source"] = "Synthetic changed line 50."
        new["records"].append({"id": "demo/scene/line-100", "source": "Brand new synthetic line.",
                               "context": "One invented scene", "protected_tokens": []})
        report, delta, _, backlog = lines.audit_lines(old, new, prior, assume_comparable=True)
        self.assertEqual([item["id"] for item in delta["items"]], ["demo/scene/line-050", "demo/scene/line-100"])
        self.assertEqual(report["counts"]["unchanged_unreviewed_candidate"], 99)
        self.assertEqual(len(backlog["items"]), 0)
        self.assertTrue(bundles.validate_bundle(new, delta)["valid"])
        self.assertNotIn("Synthetic line 49.", json.dumps(delta))
        self.assertNotIn("Synthetic line 51.", json.dumps(delta))

    def test_repeated_source_is_reviewed_not_automatically_reused(self):
        old = deepcopy(self.old)
        duplicate = deepcopy(old["records"][-1])
        duplicate["id"] = "demo/another-old-position"
        duplicate["context"] = "A different context for the same sentence."
        old["records"].append(duplicate)
        report, delta, review, _ = lines.audit_lines(old, self.new, assume_comparable=True)
        self.assertEqual(report["counts"]["new_id_existing_source_review"], 1)
        self.assertNotIn("demo/new-position", {item["id"] for item in delta["items"]})
        reference = next(item for item in review["items"] if item["category"] == "new_id_source_seen_before")
        self.assertEqual(reference["matching_old_records"], 2)
        self.assertIsNone(reference["old_record"])
        self.assertIsNone(reference["previous_translation"])
        self.assertFalse(reference["reused_automatically"])

    def test_changed_existing_line_is_delta_even_if_text_was_seen_elsewhere(self):
        new = deepcopy(self.new)
        new["records"][2]["source"] = "A blue kite."
        report, delta, _, _ = self.audit(new=new)
        self.assertIn("demo/action", {item["id"] for item in delta["items"]})
        self.assertEqual(report["counts"]["same_id_changed_source_text"], 2)

    def test_context_only_and_token_only_are_review_not_translation(self):
        new = deepcopy(self.new)
        new["records"][0]["protected_tokens"] = []
        report, delta, review, _ = self.audit(new=new)
        self.assertNotIn("demo/welcome", {item["id"] for item in delta["items"]})
        self.assertNotIn("demo/action", {item["id"] for item in delta["items"]})
        self.assertEqual(report["counts"]["same_id_metadata_only_review"], 2)
        reference = next(item for item in review["items"] if item["new_record"]["id"] == "demo/welcome")
        self.assertEqual(reference["changed_fields"], ["protected_tokens"])
        self.assertEqual(reference["previous_translation"], "Cześć, {name}!")

    def test_blank_source_goes_to_review_not_for_translation(self):
        new = deepcopy(self.new)
        new["records"][2]["source"] = "   "
        new["records"].append({"id": "demo/new-blank", "source": "", "context": "Empty field.",
                               "protected_tokens": []})
        report, delta, review, _ = self.audit(new=new)
        self.assertEqual(report["counts"]["empty_or_whitespace_source_review"], 2)
        self.assertNotIn("demo/action", {item["id"] for item in delta["items"]})
        self.assertNotIn("demo/new-blank", {item["id"] for item in delta["items"]})
        empty_reviews = [item for item in review["items"] if item["category"] == "empty_or_whitespace_source"]
        self.assertEqual({item["new_record"]["id"] for item in empty_reviews},
                         {"demo/action", "demo/new-blank"})
        self.assertTrue(all(item["review_required"] for item in empty_reviews))

    def test_missing_old_bundle_goes_to_separate_backlog_not_delta(self):
        report, delta, _, backlog = lines.audit_lines(self.old, self.new, assume_comparable=True)
        self.assertEqual(report["counts"]["unchanged_unknown_backlog"], 3)
        self.assertEqual(len(delta["items"]), 2)
        self.assertEqual({item["id"] for item in backlog["items"]},
                         {"demo/welcome", "demo/pending", "demo/unknown"})

    def test_rejects_line_breaks_in_either_snapshot(self):
        for separator in ("\n", "\r", "\v", "\f", "\x85", "\u2028", "\u2029"):
            for position in ("old", "new"):
                with self.subTest(separator=repr(separator), position=position):
                    old, new = deepcopy(self.old), deepcopy(self.new)
                    target = old if position == "old" else new
                    target["records"][1]["source"] += separator + "SECRET"
                    with self.assertRaises(bundles.BundleError) as caught:
                        lines.audit_lines(old, new, assume_comparable=True)
                    self.assertNotIn("SECRET", str(caught.exception))

    def test_bad_old_bundle_and_missing_assumption_are_rejected(self):
        with self.assertRaises(bundles.BundleError):
            lines.audit_lines(self.old, self.new, self.prior)
        stale = deepcopy(self.prior)
        stale["source_digest"] = "0" * 64
        with self.assertRaises(bundles.BundleError):
            self.audit(prior=stale)
        invalid = deepcopy(self.old)
        invalid["records"].append(deepcopy(invalid["records"][0]))
        with self.assertRaises(bundles.BundleError):
            self.audit(old=invalid)

    def test_deterministic_redacted_report_no_mutation_or_network(self):
        before = deepcopy((self.old, self.new, self.prior))
        with patch("socket.socket", side_effect=AssertionError("network access")):
            first = self.audit()
            second = self.audit()
        self.assertEqual(first, second)
        self.assertEqual((self.old, self.new, self.prior), before)
        output = json.dumps(first[0], ensure_ascii=False)
        for secret in ("demo/reward", "Found", "Cześć", str(ROOT)):
            self.assertNotIn(secret, output)


class LineAuditCliTests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)],
                              capture_output=True, text=True, encoding="utf-8", check=False)

    def test_modes_have_expected_structure_and_require_assertion(self):
        common = ["--old-source", OLD, "--new-source", NEW, "--old-bundle", PRIOR, "--assume-comparable"]
        report = self.run_cli(*common)
        self.assertEqual(report.returncode, 0, report.stderr)
        self.assertEqual(json.loads(report.stdout)["counts"]["delta_lines"], 2)
        self.assertNotIn("demo/reward", report.stdout)
        for mode, length in (("delta", 2), ("backlog", 2), ("review", 4)):
            result = self.run_cli(*common, "--mode", mode)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(len(json.loads(result.stdout)["items"]), length)
            self.assertNotIn(str(ROOT), result.stdout + result.stderr)
        missing = self.run_cli("--old-source", OLD, "--new-source", NEW)
        self.assertEqual(missing.returncode, 2)
        self.assertNotIn(str(ROOT), missing.stderr)

    def test_invalid_cli_input_is_redacted_and_has_no_partial_output(self):
        with tempfile.TemporaryDirectory(prefix="secret-lines-") as temp:
            bad = Path(temp) / "private.json"
            bad.write_text('{"SECRET":"a","SECRET":"b"}', encoding="utf-8")
            result = self.run_cli("--old-source", bad, "--new-source", NEW, "--assume-comparable", "--mode", "delta")
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stdout, "")
            self.assertNotIn("SECRET", result.stderr)
            self.assertNotIn(temp, result.stderr)
            bad.write_text("null", encoding="utf-8")
            result = self.run_cli("--old-source", OLD, "--new-source", NEW, "--old-bundle", bad, "--assume-comparable")
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stdout, "")
            self.assertNotIn(temp, result.stderr)
        invalid_mode = self.run_cli("--old-source", OLD, "--new-source", NEW, "--assume-comparable", "--mode", "secret-choice")
        self.assertEqual(invalid_mode.returncode, 2)
        self.assertNotIn("secret-choice", invalid_mode.stderr)
        self.assertNotIn(str(ROOT), invalid_mode.stderr)

    def test_cli_does_not_modify_inputs(self):
        with tempfile.TemporaryDirectory(prefix="synthetic-line-test-") as temp:
            directory = Path(temp)
            paths = [directory / name for name in ("old.json", "new.json", "prior.json")]
            for src, target in zip((OLD, NEW, PRIOR), paths):
                target.write_bytes(src.read_bytes())
            before = {path.name: path.read_bytes() for path in paths}
            result = self.run_cli("--old-source", paths[0], "--new-source", paths[1],
                                  "--old-bundle", paths[2], "--assume-comparable", "--mode", "delta")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(before, {path.name: path.read_bytes() for path in paths})
            self.assertEqual(sorted(path.name for path in directory.iterdir()), sorted(before))
            self.assertNotIn(temp, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
