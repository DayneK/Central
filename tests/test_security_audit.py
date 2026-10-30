"""Tests for scripts/security_audit.py.

The audit gates CI, so these tests prove it detects every hazard class it
claims to cover, stays quiet on clean input, honours the allowlist, and keeps
the authorization heuristic limited to code files.
"""
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from scripts.security_audit import ROOT, main, scan

PRIVATE_KEY = "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA\n"
CREDENTIAL = 'password = "hunter2secret"\n'
BEARER = "Authorization: Bearer abcdefghijklmnopqrstuv\n"
AUTHORIZATION_GATE = "if sender is allowed to write:\n    return True\n"


class ScanTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def write(self, relative: str, text: str) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def hazards(self, relative: str, text: str) -> list[str]:
        self.write(relative, text)
        return [name for _, _, name in scan(self.root)]

    def test_detects_private_key_block(self):
        self.assertIn("private-key", self.hazards("notes.md", PRIVATE_KEY))

    def test_detects_credential_assignment(self):
        self.assertIn("credential-assignment", self.hazards("config.py", CREDENTIAL))

    def test_detects_bearer_token_in_html(self):
        self.assertIn("bearer-token", self.hazards("dashboard/page.html", BEARER))

    def test_detects_authorization_gate_in_code(self):
        self.assertIn("sender-authorizes", self.hazards("handler.py", AUTHORIZATION_GATE))

    def test_authorization_prose_in_markdown_is_not_a_finding(self):
        self.assertNotIn(
            "sender-authorizes",
            self.hazards("guide.md", "If sender is allowed to write, proceed with caution.\n"),
        )

    def test_findings_carry_path_and_line_number(self):
        self.write("notes.md", "introduce no hazard here\n" + PRIVATE_KEY)
        findings = scan(self.root)
        self.assertEqual([(rel, line) for rel, line, _ in findings], [("notes.md", 2)])

    def test_allowlisted_files_are_exempt(self):
        self.write("SECURITY.md", CREDENTIAL)
        self.write("scripts/security_audit.py", CREDENTIAL)
        self.assertEqual(scan(self.root), [])

    def test_allowlist_does_not_extend_to_other_paths(self):
        """Guards the previous test: the exemption must come from the allowlist."""
        self.write("docs/notes.md", CREDENTIAL)
        self.assertEqual([name for _, _, name in scan(self.root)], ["credential-assignment"])

    def test_clean_tree_reports_nothing(self):
        self.write("README.md", "# Central\n\nSafe content only.\n")
        self.assertEqual(scan(self.root), [])

    def test_non_text_files_are_not_scanned(self):
        self.write("blob.bin", CREDENTIAL)
        self.assertEqual(scan(self.root), [])

    def test_short_values_do_not_count_as_credentials(self):
        self.write("config.py", 'password = "short"\n')
        self.assertEqual(scan(self.root), [])

    def test_repository_scan_is_clean(self):
        """The allowlist and the live tree must stay consistent with each other."""
        self.assertEqual(scan(ROOT), [])


class MainTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def test_returns_nonzero_when_a_hazard_is_found(self):
        (self.root / "notes.md").write_text(PRIVATE_KEY, encoding="utf-8")
        with mock.patch("scripts.security_audit.ROOT", self.root), redirect_stdout(io.StringIO()) as out:
            code = main()
        self.assertEqual(code, 1)
        self.assertIn("possible private-key hazard", out.getvalue())
        self.assertIn("Security audit found 1 possible hazard(s)", out.getvalue())

    def test_returns_zero_on_a_clean_tree(self):
        (self.root / "README.md").write_text("# clean\n", encoding="utf-8")
        with mock.patch("scripts.security_audit.ROOT", self.root), redirect_stdout(io.StringIO()) as out:
            code = main()
        self.assertEqual(code, 0)
        self.assertIn("Security audit passed", out.getvalue())


if __name__ == "__main__":
    unittest.main()
