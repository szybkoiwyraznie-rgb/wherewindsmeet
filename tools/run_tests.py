#!/usr/bin/env python3
"""Run the repository-only suite; empty or skipped tests are failures."""

from __future__ import annotations

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


def main() -> int:
    sys.path.insert(0, str(ROOT))
    suite = unittest.defaultTestLoader.discover(
        start_dir=str(ROOT / "tests"), pattern="test_*.py", top_level_dir=str(ROOT)
    )
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.testsRun:
        print("ERROR: no tests were discovered.", file=sys.stderr)
    if result.skipped or result.expectedFailures:
        print("ERROR: skipped tests or expected failures are not allowed.", file=sys.stderr)
    return 0 if passed(result) else 1


if __name__ == "__main__":
    raise SystemExit(main())
