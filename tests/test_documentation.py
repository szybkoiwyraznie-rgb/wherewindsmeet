from __future__ import annotations

from pathlib import Path
import re
import unittest
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parent.parent
GUIDES = (
    "README.md",
    "AGENTS.md",
    "ENVIRONMENT.md",
    "docs/STATUS.md",
    "docs/ROADMAP.md",
    "docs/FEASIBILITY.md",
    "docs/INVENTORY.md",
    "docs/WORKFLOW.md",
    "docs/DATA_POLICY.md",
    "docs/EXPERIMENT_LOG.md",
    "docs/PRIOR_ART.md",
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".github/ISSUE_TEMPLATE/bug_report.md",
    ".github/ISSUE_TEMPLATE/research.md",
)
INLINE_LINK = re.compile(r"\[[^\]\n]+\]\(([^)\s]+)\)")


class DocumentationTests(unittest.TestCase):
    def test_guides_exist_and_are_utf8(self):
        for name in GUIDES:
            with self.subTest(name=name):
                text = (ROOT / name).read_text(encoding="utf-8")
                self.assertTrue(text.strip(), name)

    def test_internal_markdown_links_resolve_inside_repository(self):
        for name in GUIDES:
            source = ROOT / name
            for link in INLINE_LINK.findall(source.read_text(encoding="utf-8")):
                parsed = urlsplit(link)
                if parsed.scheme or parsed.netloc or not parsed.path:
                    continue
                with self.subTest(source=name, link=link):
                    target = (source.parent / unquote(parsed.path)).resolve()
                    self.assertTrue(target.is_relative_to(ROOT), link)
                    self.assertTrue(target.exists(), f"{name}: missing {link}")


if __name__ == "__main__":
    unittest.main()
