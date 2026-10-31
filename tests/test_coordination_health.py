"""Tests for scripts/coordination_health.py.

The report is a derived operational view, so these tests prove that each
attention signal appears from real record state, that validation failures are
surfaced rather than swallowed, and that output formats remain parseable.
"""
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path

from scripts.coordination_health import build_report, main, render_markdown, render_text
from tests.test_semantic_validate import build_substrate, read_jsonl, write_jsonl


class CoordinationHealthTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        build_substrate(self.root)

    def update(self, relative: str, index: int = 0, **fields) -> None:
        records = read_jsonl(self.root / relative)
        records[index].update(fields)
        write_jsonl(self.root / relative, records)

    def report(self, **kwargs):
        return build_report(self.root, **kwargs)

    def test_clean_substrate_is_healthy(self):
        report = self.report(now=datetime(2026, 1, 2, tzinfo=timezone.utc))
        self.assertEqual(report["status"], "healthy", report["actions"])
        self.assertEqual(report["validation"]["errors"], [])
        self.assertEqual(report["totals"]["work_items"], 1)

    def test_report_declares_schema_and_goal_attribution(self):
        report = self.report(now=datetime(2026, 1, 2, tzinfo=timezone.utc))
        self.assertEqual(report["schema_version"], 2)
        self.assertEqual(report["goals"]["rows"][0]["id"], "goal:one")
        self.assertEqual(report["goals"]["rows"][0]["work_items"], 1)
        self.assertEqual(report["goals"]["unassigned"]["work_items"], 0)

    def test_work_without_goal_attribution_is_counted_separately(self):
        self.update("shared/work/items.jsonl", goal_ids=[])
        report = self.report(now=datetime(2026, 1, 2, tzinfo=timezone.utc))
        self.assertEqual(report["goals"]["unassigned"]["work_items"], 1)
        self.assertEqual(report["goals"]["rows"][0]["work_items"], 0)

    def test_implemented_with_pending_verification_needs_attention(self):
        self.update("shared/work/items.jsonl", status="implemented")
        report = self.report(now=datetime(2026, 1, 2, tzinfo=timezone.utc))
        self.assertEqual(report["status"], "attention")
        self.assertEqual([item["id"] for item in report["work"]["awaiting_verification"]], ["work:one"])
        self.assertTrue(any("with pending verification" in action for action in report["actions"]))

    def test_verified_work_without_review_is_reported(self):
        self.update(
            "shared/work/items.jsonl",
            status="verified",
            verification={"status": "verified", "evidence_refs": ["README.md"]},
        )
        self.update("shared/work/reviews.jsonl", result="pending")
        report = self.report(now=datetime(2026, 1, 2, tzinfo=timezone.utc))
        self.assertEqual(report["status"], "attention")
        self.assertEqual([item["id"] for item in report["work"]["verified_without_review"]], ["work:one"])

    def test_stale_active_work_is_reported(self):
        report = self.report(now=datetime(2026, 2, 1, tzinfo=timezone.utc), stale_days=14)
        self.assertEqual(report["status"], "attention")
        self.assertEqual([item["id"] for item in report["work"]["stale"]], ["work:one"])
        self.assertGreater(report["work"]["stale"][0]["idle_days"], 14)
        self.assertTrue(any("work item(s) idle" in action for action in report["actions"]))

    def test_recent_work_is_not_stale(self):
        report = self.report(now=datetime(2026, 1, 2, tzinfo=timezone.utc))
        self.assertEqual(report["work"]["stale"], [])

    def test_implemented_work_is_not_stale(self):
        self.update("shared/work/items.jsonl", status="implemented")
        report = self.report(now=datetime(2026, 3, 1, tzinfo=timezone.utc))
        self.assertEqual(report["work"]["stale"], [])

    def test_aging_unresolved_thread_is_reported(self):
        report = self.report(now=datetime(2026, 3, 1, tzinfo=timezone.utc), max_age_days=30)
        self.assertEqual(report["status"], "attention")
        self.assertEqual([item["thread_id"] for item in report["threads"]["aging"]], ["thread:one"])
        self.assertGreater(report["threads"]["aging"][0]["age_days"], 30)

    def test_resolved_thread_does_not_age(self):
        self.update("shared/communications/threads.jsonl", status="resolved")
        report = self.report(now=datetime(2026, 3, 1, tzinfo=timezone.utc), max_age_days=30)
        self.assertEqual(report["threads"]["aging"], [])

    def test_empty_thread_without_legacy_evidence_is_reported(self):
        write_jsonl(self.root / "shared/communications/messages.jsonl", [])
        self.update("shared/communications/threads.jsonl", message_ids=[])
        report = self.report(now=datetime(2026, 1, 2, tzinfo=timezone.utc))
        self.assertEqual(report["status"], "invalid")
        self.assertEqual(report["threads"]["empty_without_evidence"], ["thread:one"])
        self.assertEqual(report["threads"]["legacy_mapped"], [])
        self.assertTrue(any("empty thread(s)" in action for action in report["actions"]))
        self.assertTrue(report["validation"]["errors"])

    def test_legacy_mapped_empty_thread_is_not_reported_as_unexplained(self):
        write_jsonl(self.root / "shared/communications/messages.jsonl", [])
        self.update("shared/communications/threads.jsonl", message_ids=[])
        write_jsonl(self.root / "shared/communications/log.jsonl", [{
            "timestamp": "2026-01-01T00:00:00Z", "sender": "agent", "target": "all",
            "type": "handshake", "content": "hello",
        }])
        write_jsonl(self.root / "shared/communications/migrations/legacy-thread-map.jsonl", [{
            "id": "LTM-001", "thread_id": "thread:one", "legacy_index": 0,
            "legacy_timestamp": "2026-01-01T00:00:00Z", "legacy_sender": "agent",
            "mapping_basis": "reviewed", "reviewed_by": "agent",
            "reviewed_at": "2026-01-02T00:00:00Z",
        }])
        report = self.report(now=datetime(2026, 1, 2, tzinfo=timezone.utc))
        self.assertEqual(report["threads"]["empty_without_evidence"], [])
        self.assertEqual(report["threads"]["legacy_mapped"], ["thread:one"])
        self.assertEqual(report["status"], "healthy", report["actions"])

    def test_decision_without_related_work_is_reported(self):
        self.update("shared/decisions.jsonl", related_work_ids=[])
        report = self.report(now=datetime(2026, 1, 2, tzinfo=timezone.utc))
        self.assertEqual(report["status"], "attention")
        self.assertEqual(report["decisions"]["without_related_work"], ["dec:one"])

    def test_validation_errors_make_report_invalid(self):
        self.update("shared/work/items.jsonl", status="nonsense")
        report = self.report(now=datetime(2026, 1, 2, tzinfo=timezone.utc))
        self.assertEqual(report["status"], "invalid")
        self.assertTrue(report["validation"]["errors"])
        self.assertTrue(any("semantic validation error" in action for action in report["actions"]))

    def test_fail_on_attention_exits_non_zero(self):
        self.update("shared/work/items.jsonl", status="implemented")
        out = io.StringIO()
        with redirect_stdout(out):
            code = main(["--root", str(self.root), "--format", "json", "--fail-on", "attention"])
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(out.getvalue())["status"], "attention")

    def test_fail_on_invalid_allows_attention(self):
        self.update("shared/work/items.jsonl", status="implemented")
        out = io.StringIO()
        with redirect_stdout(out):
            code = main(["--root", str(self.root), "--format", "json", "--fail-on", "invalid"])
        self.assertEqual(code, 0)

    def test_strict_cli_fails_on_validation_errors(self):
        self.update("shared/work/items.jsonl", status="nonsense")
        out = io.StringIO()
        with redirect_stdout(out):
            code = main(["--root", str(self.root), "--format", "json", "--strict"])
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(out.getvalue())["status"], "invalid")

    def test_malformed_record_file_does_not_crash_report(self):
        (self.root / "shared/communications/messages.jsonl").write_text("{bad json\n", encoding="utf-8")
        report = self.report(now=datetime(2026, 1, 2, tzinfo=timezone.utc))
        self.assertEqual(report["status"], "invalid")
        self.assertTrue(report["validation"]["errors"])

    def test_markdown_and_text_render_the_queue(self):
        self.update("shared/work/items.jsonl", status="implemented")
        report = self.report(now=datetime(2026, 1, 2, tzinfo=timezone.utc))
        markdown = render_markdown(report)
        text = render_text(report)
        self.assertIn("Central coordination health", markdown)
        self.assertIn("`work:one`", markdown)
        self.assertIn("awaiting verification=1", text)


if __name__ == "__main__":
    unittest.main()
