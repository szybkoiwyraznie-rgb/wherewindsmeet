from types import SimpleNamespace
import unittest

from tools.run_tests import passed


def result(*, count=1, successful=True, skipped=(), expected_failures=()):
    return SimpleNamespace(
        testsRun=count,
        wasSuccessful=lambda: successful,
        skipped=skipped,
        expectedFailures=expected_failures,
    )


class TestRunnerTests(unittest.TestCase):
    def test_success_requires_executed_successful_tests(self):
        self.assertTrue(passed(result()))
        self.assertFalse(passed(result(count=0)))
        self.assertFalse(passed(result(successful=False)))

    def test_skips_and_expected_failures_fail_the_run(self):
        self.assertFalse(passed(result(skipped=(("test", "reason"),))))
        self.assertFalse(passed(result(expected_failures=(("test", "failure"),))))


if __name__ == "__main__":
    unittest.main()
