from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import hashlib
import io
import itertools
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tools import translation_bundle as bundles


ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
SOURCE = FIXTURES / "synthetic_translation_source.json"
RETURNED = FIXTURES / "synthetic_translation_return.json"
SCRIPT = ROOT / "tools" / "translation_bundle.py"
SOURCE_DIGEST = "ad3f5dafbd20d4eed6b0a1e7a129b9d7a7e7722cb0eebc752138b70565c94b01"
RETURN_DIGEST = "a289170e25822d860912ca37c26a39c340763db8b1cb1e8336b55882b845a6a4"


class TranslationBundleTests(unittest.TestCase):
    def setUp(self):
        self.source = bundles.load_json(SOURCE)
        self.template = bundles.prepare_bundle(self.source)
        self.returned = bundles.load_json(RETURNED)

    def test_template_is_deterministic_and_preserves_input(self):
        before = deepcopy(self.source)
        other = bundles.prepare_bundle(self.source)
        self.assertEqual(self.source, before)
        self.assertEqual(self.template, other)
        self.assertEqual(self.template["source_digest"], SOURCE_DIGEST)
        self.assertTrue(all(item["translation"] is None for item in self.template["items"]))
        first = self.template["items"][0]
        self.assertEqual(first["protected_tokens"], ["{count}", "{hero}"])
        self.assertEqual(
            first["source_sha256"], hashlib.sha256(first["source"].encode("utf-8")).hexdigest()
        )

    def test_snapshot_normalizes_object_and_token_order_but_not_record_order(self):
        rearranged = deepcopy(self.source)
        rearranged = dict(reversed(list(rearranged.items())))
        rearranged["records"][0]["protected_tokens"].reverse()
        self.assertEqual(bundles.prepare_bundle(rearranged)["source_digest"], SOURCE_DIGEST)
        rearranged["records"].reverse()
        self.assertNotEqual(bundles.prepare_bundle(rearranged)["source_digest"], SOURCE_DIGEST)
        with self.assertRaises(bundles.BundleError):
            bundles.validate_bundle(rearranged, self.returned)

    def test_partial_fixture_distinguishes_null_from_omitted(self):
        report = bundles.validate_bundle(self.source, self.returned)
        self.assertEqual(report["source_digest"], SOURCE_DIGEST)
        self.assertEqual(report["bundle_digest"], RETURN_DIGEST)
        self.assertEqual(report["source_records"], 3)
        self.assertEqual(report["bundle_items"], 2)
        self.assertEqual(report["translated"], 1)
        self.assertEqual(report["untranslated"], 1)
        self.assertEqual(report["omitted_from_bundle"], 1)
        self.assertFalse(report["complete"])
        self.assertEqual(report["token_check"], "declared_literals_only")
        self.assertFalse(report["game_compatibility_verified"])
        serialized = json.dumps(report, ensure_ascii=False)
        for secret in ("Hello, {hero}", "Witaj, {hero}", "demo/greeting", "Invented greeting"):
            self.assertNotIn(secret, serialized)

    def test_full_and_empty_partial_returns_are_reported_correctly(self):
        complete = deepcopy(self.template)
        complete["items"][0]["translation"] = "Witaj, {hero}! Masz {count} gwiazd."
        complete["items"][1]["translation"] = "Wiersz A<br>Wiersz B<br>"
        complete["items"][2]["translation"] = "Wymyślona notatka poboczna."
        report = bundles.validate_bundle(self.source, complete)
        self.assertTrue(report["complete"])
        self.assertEqual(
            (report["translated"], report["untranslated"], report["omitted_from_bundle"]), (3, 0, 0)
        )
        complete["items"].reverse()
        reordered = bundles.validate_bundle(self.source, complete)
        self.assertTrue(reordered["complete"])
        self.assertNotEqual(report["bundle_digest"], reordered["bundle_digest"])
        complete["items"] = []
        empty = bundles.validate_bundle(self.source, complete)
        self.assertEqual(
            (empty["translated"], empty["untranslated"], empty["omitted_from_bundle"]), (0, 0, 3)
        )
        self.assertFalse(empty["complete"])

    def test_validation_does_not_mutate_either_input(self):
        source_before = deepcopy(self.source)
        return_before = deepcopy(self.returned)
        with patch("socket.socket", side_effect=AssertionError("network access")):
            bundles.validate_bundle(self.source, self.returned)
        self.assertEqual(self.source, source_before)
        self.assertEqual(self.returned, return_before)
        invalid = deepcopy(self.returned)
        invalid["items"][0]["translation"] = "Brak wszystkich znaczników."
        invalid_before = deepcopy(invalid)
        with self.assertRaises(bundles.BundleError):
            bundles.validate_bundle(self.source, invalid)
        self.assertEqual(self.source, source_before)
        self.assertEqual(invalid, invalid_before)

    def test_rejects_changed_source_snapshot(self):
        for field, value in (
            ("source", "A different synthetic line."),
            ("context", "A different synthetic context."),
            ("id", "demo/changed"),
            ("protected_tokens", ["{hero}"]),
        ):
            with self.subTest(field=field):
                changed = deepcopy(self.source)
                changed["records"][0][field] = value
                with self.assertRaises(bundles.BundleError):
                    bundles.validate_bundle(changed, self.returned)
        changed = deepcopy(self.source)
        changed["source_id"] = "synthetic-demo-v2"
        with self.assertRaises(bundles.BundleError):
            bundles.validate_bundle(changed, self.returned)

    def test_rejects_tampered_bundle_fields(self):
        def drop_hash(bundle):
            del bundle["items"][0]["source_sha256"]

        def extra_field(bundle):
            bundle["items"][0]["unexpected"] = 1

        cases = (
            ("schema boolean", lambda b: b.update(schema=True)),
            ("source ID", lambda b: b.update(source_id="different")),
            ("digest malformed", lambda b: b.update(source_digest="NO")),
            ("digest mismatch", lambda b: b.update(source_digest="0" * 64)),
            ("source text", lambda b: b["items"][0].update(source="changed")),
            ("context", lambda b: b["items"][0].update(context="changed")),
            ("token list", lambda b: b["items"][0].update(protected_tokens=[])),
            ("invalid item hash", lambda b: b["items"][0].update(source_sha256="x")),
            ("wrong item hash", lambda b: b["items"][0].update(source_sha256="0" * 64)),
            ("missing item hash", drop_hash),
            ("extra item field", extra_field),
            ("unknown ID", lambda b: b["items"][0].update(id="demo/unknown")),
        )
        for name, mutate in cases:
            with self.subTest(name=name):
                changed = deepcopy(self.returned)
                mutate(changed)
                with self.assertRaises(bundles.BundleError):
                    bundles.validate_bundle(self.source, changed)

    def test_rejects_duplicate_ids_even_in_partial_returns(self):
        duplicate = deepcopy(self.returned)
        duplicate["items"][1] = deepcopy(duplicate["items"][0])
        with self.assertRaisesRegex(bundles.BundleError, "duplicate identifier"):
            bundles.validate_bundle(self.source, duplicate)
        source = deepcopy(self.source)
        source["records"][1]["id"] = source["records"][0]["id"]
        with self.assertRaisesRegex(bundles.BundleError, "duplicate identifier"):
            bundles.prepare_bundle(source)

    def test_invalid_or_empty_translations_fail_closed(self):
        for translation in ("", " \n\t", 17, {}, ["text"], "\ud800"):
            with self.subTest(translation=repr(translation)):
                changed = deepcopy(self.returned)
                changed["items"][0]["translation"] = translation
                with self.assertRaises(bundles.BundleError):
                    bundles.validate_bundle(self.source, changed)

    def test_protected_tokens_must_have_the_same_occurrence_count(self):
        for translation in (
            "Witaj! Masz {count} gwiazd.",
            "Witaj, {hero}! {hero} ma {count} gwiazd.",
            "Witaj, {HERO}! Masz {count} gwiazd.",
        ):
            with self.subTest(translation=translation):
                changed = deepcopy(self.returned)
                changed["items"][0]["translation"] = translation
                with self.assertRaisesRegex(bundles.BundleError, "protected token count changed"):
                    bundles.validate_bundle(self.source, changed)
        changed = deepcopy(self.template)
        changed["items"][1]["translation"] = "Wiersz A<br>Wiersz B"
        with self.assertRaisesRegex(bundles.BundleError, "protected token count changed"):
            bundles.validate_bundle(self.source, changed)
        changed["items"][1]["translation"] += "<br>"
        self.assertEqual(bundles.validate_bundle(self.source, changed)["translated"], 1)

    def test_overlapping_literal_occurrences_are_counted(self):
        source = {
            "schema": 1,
            "source_id": "overlap",
            "records": [{"id": "one", "source": "aaa", "context": "", "protected_tokens": ["aa"]}],
        }
        result = bundles.prepare_bundle(source)
        result["items"][0]["translation"] = "aa"
        with self.assertRaisesRegex(bundles.BundleError, "protected token count changed"):
            bundles.validate_bundle(source, result)
        result["items"][0]["translation"] = "xaaa!"
        self.assertTrue(bundles.validate_bundle(source, result)["complete"])

    def test_literal_counter_matches_brute_force_for_small_inputs(self):
        texts = ("".join(chars) for size in range(7) for chars in itertools.product("ab", repeat=size))
        tokens = ["".join(chars) for size in range(1, 4) for chars in itertools.product("ab", repeat=size)]
        for text in texts:
            for token in tokens:
                expected = sum(text.startswith(token, index) for index in range(len(text)))
                self.assertEqual(bundles._literal_count(text, token), expected, (text, token))

    def test_undeclared_tokens_are_not_discovered_automatically(self):
        # This is an intentional limitation: no WWM token syntax is assumed.
        changed = deepcopy(self.template)
        changed["items"][2]["translation"] = "Dowolny nowy {undeclared} znacznik."
        report = bundles.validate_bundle(self.source, changed)
        self.assertEqual(report["translated"], 1)
        self.assertEqual(report["token_check"], "declared_literals_only")

    def test_rejects_invalid_source_structure_and_values(self):
        cases = (
            ("extra root", lambda s: s.update(extra=1)),
            ("bad schema", lambda s: s.update(schema=True)),
            ("bad source ID", lambda s: s.update(source_id="private path with spaces")),
            ("empty records", lambda s: s.update(records=[])),
            ("bad record ID", lambda s: s["records"][0].update(id="identifier with space")),
            ("bad source", lambda s: s["records"][0].update(source=123)),
            ("bad context", lambda s: s["records"][0].update(context=None)),
            ("invalid Unicode", lambda s: s["records"][0].update(source="\ud800")),
            ("extra record field", lambda s: s["records"][0].update(extra=1)),
            ("missing record field", lambda s: s["records"][0].pop("context")),
        )
        for name, mutate in cases:
            with self.subTest(name=name):
                changed = deepcopy(self.source)
                mutate(changed)
                with self.assertRaises(bundles.BundleError):
                    bundles.prepare_bundle(changed)

    def test_rejects_bad_declared_tokens(self):
        for tokens in ([""], ["{hero}", "{hero}"], ["{missing}"], [None], "{hero}"):
            with self.subTest(tokens=tokens):
                changed = deepcopy(self.source)
                changed["records"][0]["protected_tokens"] = tokens
                with self.assertRaises(bundles.BundleError):
                    bundles.prepare_bundle(changed)

    def test_source_limits_are_enforced(self):
        limits = (("MAX_RECORDS", 2), ("MAX_TEXT_CHARS", 10), ("MAX_TOKENS", 1), ("MAX_TOKEN_CHARS", 4))
        for name, value in limits:
            with self.subTest(limit=name), patch.object(bundles, name, value):
                with self.assertRaises(bundles.BundleError):
                    bundles.prepare_bundle(self.source)

    def test_token_scan_budget_is_enforced_for_source_and_return(self):
        source_work = sum(
            len(record["source"]) * len(record["protected_tokens"]) for record in self.source["records"]
        )
        with patch.object(bundles, "MAX_TOKEN_CHECK_WORK", source_work - 1):
            with self.assertRaisesRegex(bundles.BundleError, "source: token check limit"):
                bundles.prepare_bundle(self.source)
        with patch.object(bundles, "MAX_TOKEN_CHECK_WORK", source_work):
            bundles.prepare_bundle(self.source)
            with self.assertRaisesRegex(bundles.BundleError, "bundle: token check limit"):
                bundles.validate_bundle(self.source, self.returned)


class JsonLoadingTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="private-json-")
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "SECRET_PATH.json"

    def test_utf8_with_or_without_bom(self):
        for prefix in (b"", b"\xef\xbb\xbf"):
            with self.subTest(prefix=prefix):
                self.path.write_bytes(prefix + '{"text":"żółć"}'.encode("utf-8"))
                self.assertEqual(bundles.load_json(self.path), {"text": "żółć"})

    def test_rejects_duplicate_keys_and_nonstandard_numbers(self):
        for raw in (
            b'{"key":1,"key":2}',
            b'{"outer":{"key":1,"key":2}}',
            b'{"number":NaN}',
            b'{"number":Infinity}',
            b'{"number":-Infinity}',
        ):
            with self.subTest(raw=raw):
                self.path.write_bytes(raw)
                with self.assertRaises(bundles.BundleError):
                    bundles.load_json(self.path)

    def test_rejects_invalid_encoding_wrong_suffix_and_oversized_input(self):
        self.path.write_bytes(b"\xff\xfe\x00\x00")
        with self.assertRaises(bundles.BundleError):
            bundles.load_json(self.path)
        self.path.write_bytes(b"{}")
        with self.assertRaisesRegex(bundles.BundleError, "too large"):
            bundles.load_json(self.path, max_bytes=1)
        with self.assertRaisesRegex(bundles.BundleError, "\\.json"):
            bundles.load_json(self.path.with_suffix(".txt"))

    def test_read_errors_do_not_reveal_path(self):
        with self.assertRaises(bundles.BundleError) as caught:
            bundles.load_json(self.path)
        self.assertNotIn("SECRET_PATH", str(caught.exception))
        self.assertNotIn(self.directory.name, str(caught.exception))


class TranslationBundleCliTests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *map(str, args)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

    def test_prepare_prints_template_without_writing_files(self):
        with tempfile.TemporaryDirectory(prefix="private-source-") as temp:
            source = Path(temp) / "private-source.json"
            source.write_bytes(SOURCE.read_bytes())
            before = source.read_bytes()
            process = self.run_cli("prepare", "--source", source)
            self.assertEqual(process.returncode, 0, process.stderr)
            template = json.loads(process.stdout)
            self.assertEqual(template["source_digest"], SOURCE_DIGEST)
            self.assertIn("Hello, {hero}", process.stdout)
            self.assertNotIn(temp, process.stdout + process.stderr)
            self.assertEqual(source.read_bytes(), before)
            self.assertEqual([path.name for path in Path(temp).iterdir()], ["private-source.json"])

    def test_validate_prints_only_report(self):
        process = self.run_cli("validate", "--source", SOURCE, "--bundle", RETURNED)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(json.loads(process.stdout)["bundle_digest"], RETURN_DIGEST)
        for secret in (str(ROOT), "Hello, {hero}", "Witaj, {hero}", "demo/greeting"):
            self.assertNotIn(secret, process.stdout + process.stderr)

    def test_invalid_return_fails_without_output_or_writes(self):
        with tempfile.TemporaryDirectory(prefix="private-bundle-") as temp:
            source_path = Path(temp) / "SECRET_SOURCE.json"
            return_path = Path(temp) / "SECRET_RETURN.json"
            source_path.write_bytes(SOURCE.read_bytes())
            returned = bundles.load_json(RETURNED)
            returned["items"][1] = deepcopy(returned["items"][0])
            return_path.write_text(json.dumps(returned), encoding="utf-8")
            before = {path.name: path.read_bytes() for path in Path(temp).iterdir()}
            process = self.run_cli("validate", "--source", source_path, "--bundle", return_path)
            self.assertNotEqual(process.returncode, 0)
            self.assertEqual(process.stdout, "")
            self.assertNotIn("SECRET_", process.stderr)
            self.assertNotIn(temp, process.stderr)
            self.assertNotIn("demo/greeting", process.stderr)
            after = {path.name: path.read_bytes() for path in Path(temp).iterdir()}
            self.assertEqual(before, after)

    def test_argument_errors_do_not_echo_private_values(self):
        process = self.run_cli("prepare", "--source", SOURCE, "--bad-option", "SECRET_ARGUMENT")
        self.assertEqual(process.returncode, 2)
        self.assertNotIn("SECRET_ARGUMENT", process.stdout + process.stderr)
        self.assertNotIn(str(SOURCE), process.stdout + process.stderr)

    def test_template_size_failure_has_no_partial_stdout(self):
        output, errors = io.StringIO(), io.StringIO()
        with (
            patch.object(bundles, "MAX_BUNDLE_BYTES", 100),
            redirect_stdout(output),
            redirect_stderr(errors),
        ):
            result = bundles.main(["prepare", "--source", str(SOURCE)])
        self.assertEqual(result, 1)
        self.assertEqual(output.getvalue(), "")
        self.assertIn("too large", errors.getvalue())
        self.assertNotIn(str(SOURCE), errors.getvalue())


if __name__ == "__main__":
    unittest.main()
