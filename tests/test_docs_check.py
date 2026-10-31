"""Tests for scripts/docs_check.py."""
import tempfile
import unittest
from pathlib import Path

from scripts.docs_check import REQUIRED_DOCS, check_docs


def build_docs(root: Path, readme: str = "# Fixture\n") -> None:
    for relative in REQUIRED_DOCS:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# Guide\n", encoding="utf-8")
    (root / "README.md").write_text(readme, encoding="utf-8")


class DocsCheckTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def test_complete_docs_with_valid_local_link_pass(self):
        build_docs(self.root, "# Fixture\n\nSee [operations](docs/OPERATIONS.md).\n")
        self.assertEqual(check_docs(self.root), [])

    def test_broken_local_link_is_reported(self):
        build_docs(self.root, "# Fixture\n\nSee [missing](docs/MISSING.md).\n")
        errors = check_docs(self.root)
        self.assertTrue(any("local link target does not exist: docs/MISSING.md" in e for e in errors), errors)

    def test_external_links_and_anchors_are_ignored(self):
        build_docs(
            self.root,
            "# Fixture\n\n[site](https://example.com) [top](#fixture) [mail](mailto:a@example.com)\n",
        )
        self.assertEqual(check_docs(self.root), [])

    def test_links_inside_code_fences_are_ignored(self):
        build_docs(self.root, "# Fixture\n\n```md\n[missing](docs/MISSING.md)\n```\n")
        self.assertEqual(check_docs(self.root), [])

    def test_missing_required_document_is_reported(self):
        build_docs(self.root)
        (self.root / "docs/OPERATIONS.md").unlink()
        errors = check_docs(self.root)
        self.assertIn("missing required document: docs/OPERATIONS.md", errors)

    def test_links_resolve_relative_to_the_document(self):
        build_docs(self.root, "# Fixture\n")
        (self.root / "docs/OPERATIONS.md").write_text("[security](../SECURITY.md)\n", encoding="utf-8")
        self.assertEqual(check_docs(self.root), [])


if __name__ == "__main__":
    unittest.main()
