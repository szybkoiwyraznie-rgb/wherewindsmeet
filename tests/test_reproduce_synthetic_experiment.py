from __future__ import annotations

from contextlib import redirect_stderr
import hashlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import reproduce_synthetic_experiment as experiment


class SyntheticExperimentTests(unittest.TestCase):
    def test_unrecognized_script_is_not_executed_or_path_disclosed(self):
        with tempfile.TemporaryDirectory(prefix="private-tool-directory-") as tmp:
            tool = Path(tmp) / "wwm_locmap.py"
            tool.write_bytes(b"x" * experiment.UPSTREAM_SIZE)
            stderr = io.StringIO()
            with redirect_stderr(stderr), patch.object(
                experiment.subprocess, "run", side_effect=AssertionError("unexpected execution")
            ):
                result = experiment.main(["--upstream-tool", str(tool)])
            self.assertEqual(result, 1)
            self.assertIn("hash differs", stderr.getvalue())
            self.assertNotIn(tmp, stderr.getvalue())

    def test_wrong_size_and_non_regular_input_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "wwm_locmap.py"
            path.mkdir()
            with self.assertRaisesRegex(experiment.ExperimentError, "regular"):
                experiment.read_pinned_tool(path)
            path.rmdir()
            path.write_bytes(b"not the published script")
            with self.assertRaisesRegex(experiment.ExperimentError, "size differs"):
                experiment.read_pinned_tool(path)

    def test_pin_accepts_exact_invented_bytes_in_controlled_test(self):
        contents = b"# invented test script, never executed\n"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "wwm_locmap.py"
            path.write_bytes(contents)
            with (
                patch.object(experiment, "UPSTREAM_SIZE", len(contents)),
                patch.object(experiment, "UPSTREAM_SHA256", hashlib.sha256(contents).hexdigest()),
            ):
                self.assertEqual(experiment.read_pinned_tool(path), contents)

    def test_exact_dependency_and_fixture_required_before_execution(self):
        with (
            patch.object(experiment.metadata, "version", return_value="0.0"),
            patch.object(experiment.subprocess, "run", side_effect=AssertionError("unexpected execution")),
        ):
            with self.assertRaisesRegex(experiment.ExperimentError, "zstandard==0.24.0"):
                experiment.experiment(b"# synthetic")
        with (
            patch.object(experiment.metadata, "version", return_value=experiment.ZSTANDARD_VERSION),
            patch.object(experiment, "build_sample", return_value=b"wrong synthetic fixture"),
            patch.object(experiment.subprocess, "run", side_effect=AssertionError("unexpected execution")),
        ):
            with self.assertRaisesRegex(experiment.ExperimentError, "fixture hash differs"):
                experiment.experiment(b"# synthetic")


if __name__ == "__main__":
    unittest.main()
