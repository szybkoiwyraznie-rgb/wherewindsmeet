#!/usr/bin/env python3
"""Run the repository-only suite; empty or skipped tests are failures."""

from __future__ import annotations

import os
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parent.parent


def passed(result: unittest.TestResult) -> bool:
    return bool(
        result.testsRun
        and result.wasSuccessful()
        and not result.skipped
        and not result.expectedFailures
    )


def github_failure_annotations(result: unittest.TestResult) -> list[str]:
    """Summarize failed repo-only tests as safely escaped Actions annotations."""
    annotations = []
    for test, detail in (*result.errors, *result.failures):
        lines = detail.rstrip().splitlines()
        last_line = lines[-1] if lines else "no failure details"
        message = f"{test.id()}: {last_line}"[:1000]
        message = message.encode("ascii", errors="backslashreplace").decode("ascii")
        escaped = message.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
        annotations.append(f"::error title=Repository test failed::{escaped}")
    return annotations


def main() -> int:
    sys.path.insert(0, str(ROOT))
    suite = unittest.defaultTestLoader.discover(
        start_dir=str(ROOT / "tests"), pattern="test_*.py", top_level_dir=str(ROOT)
    )
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if os.environ.get("GITHUB_ACTIONS") == "true":
        for annotation in github_failure_annotations(result):
            print(annotation)
    if not result.testsRun:
        print("ERROR: no tests were discovered.", file=sys.stderr)
    if result.skipped or result.expectedFailures:
        print("ERROR: skipped tests or expected failures are not allowed.", file=sys.stderr)
    return 0 if passed(result) else 1


if __name__ == "__main__":
    raise SystemExit(main())
