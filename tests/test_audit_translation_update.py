from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tools import audit_translation_update as audit
from tools import translation_bundle as bundles


ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
OLD = FIXTURES / "synthetic_update_old.json"
NEW = FIXTURES / "synthetic_update_new.json"
OLD_BUNDLE = FIXTURES / "synthetic_update_old_return.json"
SCRIPT = ROOT / "tools" / "audit_translation_update.py"
OLD_DIGEST = "e5ab29fe12e61b5b47d61f38708c9403ac7ce525eb539d34c044923fa3e07e00"
NEW_DIGEST = "bb00cf4bd99152af497d03d603d1144106bbac0a2ada66b97b5965956d6b0a34"


class UpdateAuditTests(unittest.TestCase):
    def setUp(self):
        self.old = bundles.load_json(OLD)
        self.new = bundles.load_json(NEW)
        self.previous = bundles.load_json(OLD_BUNDLE)

    def run_audit(self, old=None, new=None, previous=None):
        return audit.audit_update(
            self.old if old is None else old,
            self.new if new is None else new,
            self.previous if previous is None else previous,
            assume_comparable=True,
        )

    def test_synthetic_update_counts_and_snapshot_binding(self):
        report, todo, review = self.run_audit()
        self.assertEqual(report["old_source_digest"], OLD_DIGEST)
        self.assertEqual(report["new_source_digest"], NEW_DIGEST)
        self.assertTrue(report["old_bundle_supplied"])
        self.assertFalse(report["comparison_assumption_verified"])
        self.assertFalse(report["game_compatibility_verified"])
        self.assertEqual(report["comparison_assumption"], audit.COMPARISON)
        self.assertEqual(report["counts"], {
            "old_records": 7,
            "new_records": 7,
            "same_id_same_fields": 3,
            "same_id_changed": 2,
            "id_only_in_new": 2,
            "id_only_in_old": 2,
            "changed_source": 1,
            "changed_context": 1,
            "changed_protected_tokens": 0,
            "unchanged_prior_translation_candidates": 1,
            "unchanged_prior_explicit_null": 1,
            "unchanged_prior_unknown": 1,
            "possible_id_changes_exact_unique": 1,
            "ambiguous_new_ids_with_equal_record": 0,
            "task_records": 6,
            "review_records": 4,
        })
        self.assertEqual(todo["source_digest"], NEW_DIGEST)
        self.assertEqual(review["old_source_digest"], OLD_DIGEST)
        self.assertEqual(review["new_source_digest"], NEW_DIGEST)
        self.assertEqual(review["ids_only_in_old"], ["demo/retired", "demo/old-position"])

    def test_tasks_are_a_valid_partial_new_snapshot_bundle(self):
        _, todo, review = self.run_audit()
        self.assertEqual([item["id"] for item in todo["items"]], [
            "demo/reward", "demo/action", "demo/pending", "demo/unknown",
            "demo/added", "demo/new-position",
        ])
        self.assertTrue(all(item["translation"] is None for item in todo["items"]))
        validation = bundles.validate_bundle(self.new, todo)
        self.assertEqual(validation["untranslated"], 6)
        self.assertEqual(validation["omitted_from_bundle"], 1)
        self.assertFalse(validation["complete"])
        self.assertEqual(review["task_reasons"], [
            {"id": "demo/reward", "reason": "changed_record"},
            {"id": "demo/action", "reason": "changed_record"},
            {"id": "demo/pending", "reason": "prior_explicit_null"},
            {"id": "demo/unknown", "reason": "prior_unknown"},
            {"id": "demo/added", "reason": "id_only_in_new"},
            {"id": "demo/new-position", "reason": "id_only_in_new"},
        ])
        with self.assertRaises(bundles.BundleError):
            bundles.validate_bundle(self.old, todo)

    def test_review_never_auto_carries_old_translation(self):
        _, todo, review = self.run_audit()
        categories = [item["category"] for item in review["items"]]
        self.assertEqual(categories, [
            "unchanged_translation_candidate", "changed_record", "changed_record", "possible_id_change"
        ])
        for item in review["items"]:
            self.assertTrue(item["review_required"])
            self.assertFalse(item["reused_automatically"])
        candidate, text_changed, context_changed, possible_move = review["items"]
        self.assertEqual(candidate["previous_translation"], "Cześć, {name}!")
        self.assertEqual(candidate["previous_translation_state"], "supplied_unreviewed")
        self.assertEqual(text_changed["changed_fields"], ["source"])
        self.assertEqual(context_changed["changed_fields"], ["context"])
        self.assertEqual(context_changed["previous_translation"], "Zamknij")
        self.assertEqual(possible_move["old_record"]["id"], "demo/old-position")
        self.assertEqual(possible_move["new_record"]["id"], "demo/new-position")
        self.assertEqual(possible_move["previous_translation"], "Zapomniana wstążka.")
        self.assertNotIn("Zamknij", json.dumps(todo, ensure_ascii=False))

    def test_partial_bundle_omissions_are_unknown_and_null_is_separate(self):
        report, todo, _ = self.run_audit()
        counts = report["counts"]
        self.assertEqual(counts["unchanged_prior_explicit_null"], 1)
        self.assertEqual(counts["unchanged_prior_unknown"], 1)
        task_ids = {item["id"] for item in todo["items"]}
        self.assertIn("demo/pending", task_ids)
        self.assertIn("demo/unknown", task_ids)
        # With no supplied bundle every unchanged record is unknown, not translated.
        no_bundle, tasks, review = audit.audit_update(self.old, self.new, assume_comparable=True)
        self.assertFalse(no_bundle["old_bundle_supplied"])
        self.assertIsNone(no_bundle["old_bundle_digest"])
        self.assertEqual(no_bundle["counts"]["unchanged_prior_unknown"], 3)
        self.assertEqual(no_bundle["counts"]["unchanged_prior_translation_candidates"], 0)
        self.assertEqual(len(tasks["items"]), 7)
        self.assertTrue(all(item["translation"] is None for item in tasks["items"]))
        self.assertTrue(all(item["previous_translation"] is None for item in review["items"]))

    def test_changed_token_declaration_requires_new_work(self):
        new = deepcopy(self.new)
        new["records"][0]["protected_tokens"] = []
        report, todo, review = self.run_audit(new=new)
        self.assertEqual(report["counts"]["changed_protected_tokens"], 1)
        self.assertEqual(report["counts"]["unchanged_prior_translation_candidates"], 0)
        self.assertIn("demo/welcome", {item["id"] for item in todo["items"]})
        item = next(item for item in review["items"] if item["new_record"]["id"] == "demo/welcome")
        self.assertEqual(item["changed_fields"], ["protected_tokens"])
        self.assertTrue(item["review_required"])

    def test_record_order_is_not_a_change_but_changes_snapshot_hash(self):
        new = deepcopy(self.new)
        new["records"].reverse()
        report, todo, _ = self.run_audit(new=new)
        self.assertEqual(report["counts"]["same_id_same_fields"], 3)
        self.assertEqual(report["counts"]["same_id_changed"], 2)
        self.assertNotEqual(report["new_source_digest"], NEW_DIGEST)
        self.assertEqual(todo["source_digest"], report["new_source_digest"])
        bundles.validate_bundle(new, todo)

    def test_token_declaration_order_is_normalized_not_a_change(self):
        old = {
            "schema": 1,
            "source_id": "synthetic",
            "records": [{
                "id": "entry",
                "source": "{a} and {b}",
                "context": "invented",
                "protected_tokens": ["{b}", "{a}"],
            }],
        }
        new = deepcopy(old)
        new["records"][0]["protected_tokens"].reverse()
        report, todo, _ = audit.audit_update(old, new, assume_comparable=True)
        self.assertEqual(report["counts"]["same_id_same_fields"], 1)
        self.assertEqual(report["counts"]["changed_protected_tokens"], 0)
        self.assertEqual(report["old_source_digest"], report["new_source_digest"])
        bundles.validate_bundle(new, todo)

    def test_multiple_equal_records_are_ambiguous_and_never_mapped(self):
        old = deepcopy(self.old)
        duplicate = deepcopy(old["records"][-1])
        duplicate["id"] = "demo/old-position-duplicate"
        old["records"].append(duplicate)
        # A new ID has the same text/context as two old-only IDs.
        report, todo, review = audit.audit_update(old, self.new, assume_comparable=True)
        self.assertEqual(report["counts"]["possible_id_changes_exact_unique"], 0)
        self.assertEqual(report["counts"]["ambiguous_new_ids_with_equal_record"], 1)
        self.assertIn("demo/new-position", {item["id"] for item in todo["items"]})
        item = next(item for item in review["items"] if item["category"] == "ambiguous_equal_record")
        self.assertEqual(item["matching_old_records"], 2)
        self.assertIsNone(item["old_record"])
        self.assertIsNone(item["previous_translation"])
        self.assertFalse(item["reused_automatically"])

    def test_new_duplicate_does_not_mean_old_record_moved(self):
        new = deepcopy(self.new)
        duplicate = deepcopy(new["records"][0])
        duplicate["id"] = "demo/another-welcome"
        new["records"].append(duplicate)
        report, todo, review = self.run_audit(new=new)
        self.assertEqual(report["counts"]["possible_id_changes_exact_unique"], 1)
        self.assertEqual(report["counts"]["ambiguous_new_ids_with_equal_record"], 1)
        self.assertIn("demo/another-welcome", {item["id"] for item in todo["items"]})
        ambiguous = next(item for item in review["items"] if item["category"] == "ambiguous_equal_record")
        self.assertIsNone(ambiguous["old_record"])
        self.assertEqual(ambiguous["matching_old_records"], 1)

    def test_comparison_requires_explicit_assertion(self):
        for value in (False, None, "yes", 1):
            with self.subTest(value=value), self.assertRaises(bundles.BundleError):
                audit.audit_update(self.old, self.new, self.previous, assume_comparable=value)

    def test_rejects_invalid_snapshots_and_stale_or_corrupted_old_bundle(self):
        invalid_old = deepcopy(self.old)
        invalid_old["records"].append(deepcopy(invalid_old["records"][0]))
        with self.assertRaises(bundles.BundleError):
            self.run_audit(old=invalid_old)
        invalid_new = deepcopy(self.new)
        invalid_new["records"][0]["source"] = "changed without the declared token"
        with self.assertRaises(bundles.BundleError):
            self.run_audit(new=invalid_new)
        stale = deepcopy(self.previous)
        stale["source_digest"] = "0" * 64
        with self.assertRaises(bundles.BundleError):
            self.run_audit(previous=stale)
        changed_old = deepcopy(self.old)
        changed_old["records"][1]["context"] += " changed"
        with self.assertRaises(bundles.BundleError):
            self.run_audit(old=changed_old)
        bad_tokens = deepcopy(self.previous)
        bad_tokens["items"][0]["translation"] = "Brak znacznika."
        with self.assertRaises(bundles.BundleError):
            self.run_audit(previous=bad_tokens)
        duplicate = deepcopy(self.previous)
        duplicate["items"][1] = deepcopy(duplicate["items"][0])
        with self.assertRaises(bundles.BundleError):
            self.run_audit(previous=duplicate)

    def test_source_change_does_not_reuse_old_translation_even_if_id_matches(self):
        changed = deepcopy(self.new)
        changed["records"][0]["source"] = "Bye, {name}!"
        report, todo, review = self.run_audit(new=changed)
        self.assertEqual(report["counts"]["unchanged_prior_translation_candidates"], 0)
        item = next(item for item in todo["items"] if item["id"] == "demo/welcome")
        self.assertIsNone(item["translation"])
        reference = next(item for item in review["items"] if item["new_record"]["id"] == "demo/welcome")
        self.assertEqual(reference["previous_translation"], "Cześć, {name}!")
        self.assertEqual(reference["changed_fields"], ["source"])
        self.assertFalse(reference["reused_automatically"])

    def test_generated_partial_snapshots_match_independent_classification(self):
        rng = random.Random(42)
        for case in range(100):
            with self.subTest(case=case):
                old = {"schema": 1, "source_id": "old", "records": []}
                for index in range(12):
                    old["records"].append({
                        "id": f"entry/{index}",
                        "source": f"Invented text {index % 5} {{slot}}",
                        "context": f"Invented context {index % 3}",
                        "protected_tokens": ["{slot}"] if rng.randrange(2) else [],
                    })
                prior = bundles.prepare_bundle(old)
                prior["items"] = [item for item in prior["items"] if rng.randrange(4) != 0]
                for item in prior["items"]:
                    if rng.randrange(2):
                        item["translation"] = "Wymyślony tekst {slot}" if item["protected_tokens"] else "Wymyślony tekst"
                new = {"schema": 1, "source_id": "new", "records": []}
                for record in old["records"]:
                    if rng.randrange(4) == 0:
                        continue
                    record = deepcopy(record)
                    change = rng.randrange(5)
                    if change == 1:
                        record["source"] += " changed"
                    elif change == 2:
                        record["context"] += " changed"
                    elif change == 3:
                        record["protected_tokens"] = [] if record["protected_tokens"] else ["{slot}"]
                    new["records"].append(record)
                for index in range(rng.randrange(1, 4)):
                    record = deepcopy(rng.choice(old["records"]))
                    record["id"] = f"new/{case}/{index}"
                    new["records"].append(record)
                rng.shuffle(new["records"])
                report, todo, review = audit.audit_update(old, new, prior, assume_comparable=True)
                old_by_id = {record["id"]: record for record in old["records"]}
                prior_by_id = {item["id"]: item for item in prior["items"]}
                expected_tasks = set()
                candidates = nulls = unknown = changed = 0
                changed_fields = {field: 0 for field in audit.FIELDS}
                for record in new["records"]:
                    identifier = record["id"]
                    previous = old_by_id.get(identifier)
                    if previous is None:
                        expected_tasks.add(identifier)
                    elif any(previous[field] != record[field] for field in audit.FIELDS):
                        changed += 1
                        expected_tasks.add(identifier)
                        for field in audit.FIELDS:
                            changed_fields[field] += previous[field] != record[field]
                    elif identifier not in prior_by_id:
                        unknown += 1
                        expected_tasks.add(identifier)
                    elif prior_by_id[identifier]["translation"] is None:
                        nulls += 1
                        expected_tasks.add(identifier)
                    else:
                        candidates += 1
                self.assertEqual({item["id"] for item in todo["items"]}, expected_tasks)
                self.assertEqual(report["counts"]["same_id_changed"], changed)
                self.assertEqual(report["counts"]["unchanged_prior_translation_candidates"], candidates)
                self.assertEqual(report["counts"]["unchanged_prior_explicit_null"], nulls)
                self.assertEqual(report["counts"]["unchanged_prior_unknown"], unknown)
                for field in audit.FIELDS:
                    self.assertEqual(report["counts"][f"changed_{field}"], changed_fields[field])
                self.assertTrue(all(item["translation"] is None for item in todo["items"]))
                self.assertTrue(all(not item["reused_automatically"] for item in review["items"]))
                bundles.validate_bundle(new, todo)

    def test_record_count_ceiling_and_above_limit_fail_closed(self):
        old = {
            "schema": 1,
            "source_id": "synthetic-limit",
            "records": [
                {"id": f"entry/{index}", "source": f"Invented {index}", "context": "", "protected_tokens": []}
                for index in range(bundles.MAX_RECORDS)
            ],
        }
        new = deepcopy(old)
        report, todo, _ = audit.audit_update(old, new, assume_comparable=True)
        self.assertEqual(report["counts"]["same_id_same_fields"], bundles.MAX_RECORDS)
        self.assertEqual(report["counts"]["task_records"], bundles.MAX_RECORDS)
        self.assertTrue(bundles.validate_bundle(new, todo)["valid"])
        too_many = deepcopy(old)
        too_many["records"].append({"id": "one-more", "source": "invented", "context": "", "protected_tokens": []})
        for first, second in ((too_many, new), (old, too_many)):
            with self.assertRaises(bundles.BundleError):
                audit.audit_update(first, second, assume_comparable=True)

    def test_audit_is_deterministic_side_effect_free_and_redacted_by_default(self):
        before = deepcopy((self.old, self.new, self.previous))
        with patch("socket.socket", side_effect=AssertionError("network access")):
            first = self.run_audit()
            second = self.run_audit()
        self.assertEqual(first, second)
        self.assertEqual((self.old, self.new, self.previous), before)
        report = json.dumps(first[0], ensure_ascii=False)
        for secret in ("demo/welcome", "Hello, {name}", "Cześć, {name}", "invented greeting"):
            self.assertNotIn(secret, report)


class UpdateAuditCliTests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *map(str, args)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

    def test_cli_reports_counts_and_emits_task_and_review_documents(self):
        common = ["--old-source", OLD, "--new-source", NEW, "--old-bundle", OLD_BUNDLE, "--assume-comparable"]
        report = self.run_cli(*common)
        self.assertEqual(report.returncode, 0, report.stderr)
        self.assertEqual(json.loads(report.stdout)["counts"]["task_records"], 6)
        self.assertNotIn("demo/welcome", report.stdout)
        self.assertNotIn(str(ROOT), report.stdout + report.stderr)
        todo = self.run_cli(*common, "--mode", "todo")
        self.assertEqual(todo.returncode, 0, todo.stderr)
        task_bundle = json.loads(todo.stdout)
        self.assertEqual(bundles.validate_bundle(bundles.load_json(NEW), task_bundle)["untranslated"], 6)
        review = self.run_cli(*common, "--mode", "review")
        self.assertEqual(review.returncode, 0, review.stderr)
        self.assertIn("demo/welcome", review.stdout)
        self.assertEqual(len(json.loads(review.stdout)["items"]), 4)

    def test_no_file_is_modified_by_any_cli_mode(self):
        with tempfile.TemporaryDirectory(prefix="private-update-") as temp:
            directory = Path(temp)
            old, new, prior = (directory / name for name in ("old.json", "new.json", "prior.json"))
            old.write_bytes(OLD.read_bytes())
            new.write_bytes(NEW.read_bytes())
            prior.write_bytes(OLD_BUNDLE.read_bytes())
            before = {path.name: path.read_bytes() for path in directory.iterdir()}
            for mode in ("report", "todo", "review"):
                with self.subTest(mode=mode):
                    result = self.run_cli(
                        "--old-source", old, "--new-source", new, "--old-bundle", prior,
                        "--assume-comparable", "--mode", mode,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertNotIn(temp, result.stdout + result.stderr)
            after = {path.name: path.read_bytes() for path in directory.iterdir()}
            self.assertEqual(before, after)

    def test_cli_requires_assumption_and_does_not_echo_private_arguments(self):
        result = self.run_cli("--old-source", OLD, "--new-source", NEW)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertNotIn(str(OLD), result.stderr)
        self.assertNotIn(str(NEW), result.stderr)
        result = self.run_cli(
            "--old-source", OLD, "--new-source", NEW, "--assume-comparable", "--bad", "SECRET_VALUE"
        )
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("SECRET_VALUE", result.stdout + result.stderr)

    def test_explicit_null_bundle_is_invalid_not_silently_absent(self):
        with tempfile.TemporaryDirectory(prefix="private-null-") as temp:
            path = Path(temp) / "SECRET_NULL.json"
            path.write_text("null", encoding="utf-8")
            result = self.run_cli(
                "--old-source", OLD, "--new-source", NEW, "--old-bundle", path, "--assume-comparable"
            )
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stdout, "")
            self.assertNotIn("SECRET_NULL", result.stderr)
            self.assertNotIn(temp, result.stderr)

    def test_cli_rejects_duplicate_json_keys_without_echoing_input(self):
        with tempfile.TemporaryDirectory(prefix="private-update-") as temp:
            path = Path(temp) / "SECRET_SOURCE.json"
            path.write_text('{"schema": 1, "schema": 1}', encoding="utf-8")
            result = self.run_cli(
                "--old-source", path, "--new-source", NEW, "--assume-comparable"
            )
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stdout, "")
            self.assertIn("duplicate object key", result.stderr)
            self.assertNotIn("SECRET_SOURCE", result.stderr)
            self.assertNotIn(temp, result.stderr)

    def test_size_failure_has_no_partial_stdout(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        args = ["--old-source", str(OLD), "--new-source", str(NEW), "--mode", "review", "--assume-comparable"]
        with (
            patch.object(bundles, "MAX_BUNDLE_BYTES", 100),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            code = audit.main(args)
        self.assertEqual(code, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("output is too large", stderr.getvalue())
        self.assertNotIn(str(OLD), stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
