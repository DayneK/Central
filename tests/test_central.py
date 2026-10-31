"""Tests for scripts/central.py.

The CLI is a dispatcher, so these tests focus on exit-code composition and
argument forwarding rather than repeating the validators' own test suites.
"""
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from scripts.central import main, run_check
from tests.test_semantic_validate import build_substrate


class CentralCliTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        build_substrate(self.root)

    def test_semantic_command_uses_fixture_root(self):
        out = io.StringIO()
        with redirect_stdout(out):
            code = main(["--root", str(self.root), "semantic"])
        self.assertEqual(code, 0, out.getvalue())
        self.assertIn("Semantic validation passed", out.getvalue())

    def test_check_reports_every_stage(self):
        with mock.patch("scripts.central.agent_workspace.validate_repo", return_value=[]), \
             mock.patch("scripts.central.semantic_validate.run", return_value=[]), \
             mock.patch("scripts.central.security_audit.scan", return_value=[]), \
             mock.patch("scripts.central.docs_check.check_docs", return_value=[]):
            out = io.StringIO()
            with redirect_stdout(out):
                code = run_check(self.root, check_git=True)
        self.assertEqual(code, 0)
        text = out.getvalue()
        for stage in ("workspace: ok", "semantic: ok", "security: ok", "docs: ok"):
            self.assertIn(stage, text)

    def test_check_fails_when_one_stage_fails(self):
        with mock.patch("scripts.central.agent_workspace.validate_repo", return_value=["bad goal"]), \
             mock.patch("scripts.central.semantic_validate.run", return_value=[]), \
             mock.patch("scripts.central.security_audit.scan", return_value=[]), \
             mock.patch("scripts.central.docs_check.check_docs", return_value=[]):
            out = io.StringIO()
            with redirect_stdout(out):
                code = run_check(self.root)
        self.assertEqual(code, 1)
        self.assertIn("ERROR: bad goal", out.getvalue())
        self.assertIn("Central check failed: 1 issue", out.getvalue())

    def test_check_forwards_git_flag(self):
        with mock.patch("scripts.central.agent_workspace.validate_repo", return_value=[]), \
             mock.patch("scripts.central.semantic_validate.run", return_value=[]) as semantic, \
             mock.patch("scripts.central.security_audit.scan", return_value=[]), \
             mock.patch("scripts.central.docs_check.check_docs", return_value=[]):
            run_check(self.root, check_git=True)
        self.assertEqual(semantic.call_args.kwargs, {"check_git": True})

    def test_health_command_honours_fail_on(self):
        out = io.StringIO()
        with redirect_stdout(out):
            code = main([
                "--root", str(self.root), "health", "--format", "json",
                "--now", "2026-03-01T00:00:00Z", "--fail-on", "attention",
            ])
        self.assertEqual(code, 1)
        report = json.loads(out.getvalue())
        self.assertEqual(report["status"], "attention")
        self.assertEqual(report["schema_version"], 2)

    def test_docs_command_reports_missing_guides(self):
        out = io.StringIO()
        with redirect_stdout(out):
            code = main(["--root", str(self.root), "docs"])
        self.assertEqual(code, 1)
        self.assertIn("missing required document", out.getvalue())

    def test_security_command_passes_on_fixture(self):
        out = io.StringIO()
        with redirect_stdout(out):
            code = main(["--root", str(self.root), "security"])
        self.assertEqual(code, 0, out.getvalue())
        self.assertIn("Security audit passed", out.getvalue())

    def test_unknown_command_is_rejected(self):
        with self.assertRaises(SystemExit):
            main(["--root", str(self.root)])


if __name__ == "__main__":
    unittest.main()
