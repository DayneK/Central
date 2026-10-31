"""End-to-end tests for the repository command line tools.

These tests invoke the scripts the way CI and contributors do, rather than
calling their functions directly. They cover exit codes and JSON output across
process boundaries.
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.test_semantic_validate import build_substrate, read_jsonl, write_jsonl

ROOT = Path(__file__).resolve().parents[1]
CENTRAL = ROOT / "scripts/central.py"


def run_cli(*args: str, root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(CENTRAL), "--root", str(root), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


class CliIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        build_substrate(self.root)

    def test_semantic_cli_accepts_valid_fixture(self):
        result = run_cli("semantic", root=self.root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Semantic validation passed", result.stdout)

    def test_semantic_cli_reports_invalid_status(self):
        records = read_jsonl(self.root / "shared/work/items.jsonl")
        records[0]["status"] = "nonsense"
        write_jsonl(self.root / "shared/work/items.jsonl", records)
        result = run_cli("semantic", root=self.root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("invalid work status", result.stdout)

    def test_health_cli_emits_versioned_json(self):
        result = run_cli("health", "--format", "json", root=self.root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["schema_version"], 2)
        self.assertIn("goals", report)
        self.assertIn("work", report)

    def test_health_cli_fail_on_attention_returns_non_zero(self):
        result = run_cli(
            "health", "--format", "json", "--now", "2026-03-01T00:00:00Z",
            "--fail-on", "attention", root=self.root,
        )
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)["status"], "attention")

    def test_unified_check_passes_on_the_live_repository(self):
        result = run_cli("check", root=ROOT)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for stage in ("workspace: ok", "semantic: ok", "security: ok", "docs: ok"):
            self.assertIn(stage, result.stdout)

    def test_docs_cli_passes_on_the_live_repository(self):
        result = run_cli("docs", root=ROOT)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
