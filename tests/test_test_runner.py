from types import SimpleNamespace
import unittest

from tools.run_tests import github_failure_annotations, passed


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

    def test_github_annotations_escape_control_characters(self):
        test = SimpleNamespace(id=lambda: "synthetic.test%\n::notice::")
        test_result = SimpleNamespace(errors=[(test, "Traceback\nValueError: fake%error ż")], failures=[])
        annotations = github_failure_annotations(test_result)
        self.assertEqual(annotations, [
            "::error title=Repository test failed::synthetic.test%25%0A::notice::: ValueError: fake%25error \\u017c"
        ])
        self.assertEqual(github_failure_annotations(SimpleNamespace(errors=[], failures=[])), [])


if __name__ == "__main__":
    unittest.main()
