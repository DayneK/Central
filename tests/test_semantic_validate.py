"""Fixture-based tests for scripts/semantic_validate.py.

The existing substrate tests assert that the live repository is valid. These
tests do the opposite: they build a minimal valid substrate in a temp directory
and prove that each rule actually fires when its data is wrong, and that one
broken file does not silently disable validation of the others.
"""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.semantic_validate import main, run, validate_threads as real_validate_threads


def write_jsonl(path: Path, records) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(record) + "\n" for record in records), encoding="utf-8")


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def build_substrate(root: Path) -> None:
    """Write the smallest substrate that satisfies every semantic rule."""
    (root / "README.md").write_text("# Fixture\n", encoding="utf-8")
    (root / "shared/communications").mkdir(parents=True, exist_ok=True)
    (root / "shared/communications/state.md").write_text("# State\n", encoding="utf-8")
    write_jsonl(root / "shared/communications/log.jsonl", [])
    write_jsonl(root / "shared/communications/migrations/legacy-thread-map.jsonl", [])
    write_jsonl(root / "shared/knowledge/documents.jsonl", [{
        "id": "doc:one", "type": "document", "title": "One",
        "provenance_type": "declared", "status": "active", "path": "README.md",
    }])
    write_jsonl(root / "shared/knowledge/relations.jsonl", [{
        "id": "rel:one", "subject": "doc:one", "predicate": "defines",
        "object": "doc:one", "provenance_type": "declared", "status": "active",
    }])
    write_jsonl(root / "shared/communications/threads.jsonl", [{
        "thread_id": "thread:one", "title": "Thread", "status": "open",
        "topic": "testing", "message_ids": ["msg:one"],
        "created_at": "2026-01-01T00:00:00Z",
    }])
    write_jsonl(root / "shared/communications/messages.jsonl", [{
        "message_id": "msg:one", "thread_id": "thread:one",
        "timestamp": "2026-01-01T00:00:00Z", "sender": "agent", "target": "agent",
        "type": "update", "content": "hello", "source_refs": [],
        "provenance_type": "declared",
    }])
    (root / "projects/central").mkdir(parents=True, exist_ok=True)
    (root / "projects/central/shared-goals.json").write_text(
        json.dumps({"goals": [{"id": "goal:one", "title": "Goal One", "status": "active"}]}),
        encoding="utf-8",
    )
    write_jsonl(root / "shared/work/items.jsonl", [{
        "id": "work:one", "title": "Work", "description": "d", "status": "active",
        "goal_ids": ["goal:one"],
        "priority": "high", "owner": "agent", "depends_on": [], "source_refs": [],
        "acceptance_criteria": ["done"], "verification": {"status": "pending", "evidence_refs": []},
        "provenance_type": "declared", "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
    }])
    write_jsonl(root / "shared/work/reviews.jsonl", [{
        "id": "review:one", "timestamp": "2026-01-01T00:00:00Z", "work_id": "work:one",
        "reviewer": "agent", "result": "pass", "criteria_checked": ["done"], "evidence_refs": [],
    }])
    write_jsonl(root / "shared/state/events.jsonl", [{
        "id": "evt:one", "timestamp": "2026-01-01T00:00:00Z", "type": "note",
        "summary": "s", "actors": ["agent"], "source_refs": [],
    }])
    write_jsonl(root / "shared/state/snapshots.jsonl", [{
        "id": "snap:one", "timestamp": "2026-01-01T00:00:00Z", "label": "l",
        "source_commit": "abc1234", "state_file": "shared/communications/state.md",
    }])
    write_jsonl(root / "shared/decisions.jsonl", [{
        "id": "dec:one", "timestamp": "2026-01-01T00:00:00Z", "decision": "d",
        "context": "c", "alternatives": [], "rationale": "r", "status": "accepted",
        "affected_goals": [], "evidence": [], "review_trigger": "never",
        "related_work_ids": ["work:one"], "origin_thread_ids": ["thread:one"],
    }])


class SemanticValidateTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        build_substrate(self.root)

    def errors(self) -> list[str]:
        return run(self.root)

    def update(self, relative: str, index: int = 0, **fields) -> None:
        records = read_jsonl(self.root / relative)
        records[index].update(fields)
        write_jsonl(self.root / relative, records)

    # --- baseline -----------------------------------------------------------

    def test_minimal_substrate_is_valid(self):
        self.assertEqual(self.errors(), [])

    # --- stage isolation (regression for the short-circuit finding) ---------

    def test_malformed_file_does_not_disable_other_stages(self):
        (self.root / "shared/knowledge/documents.jsonl").write_text("{not json", encoding="utf-8")
        self.update("shared/work/items.jsonl", status="nonsense")
        errors = self.errors()
        self.assertTrue(any("shared/knowledge/documents.jsonl" in e for e in errors), errors)
        self.assertTrue(any("invalid work status" in e for e in errors), errors)

    def test_missing_file_is_reported_without_disabling_other_stages(self):
        (self.root / "shared/work/reviews.jsonl").unlink()
        self.update("shared/work/items.jsonl", status="nonsense")
        errors = self.errors()
        self.assertIn("missing required semantic file: shared/work/reviews.jsonl", errors)
        self.assertTrue(any("invalid work status" in e for e in errors), errors)

    def test_threads_are_validated_once(self):
        with mock.patch("scripts.semantic_validate.validate_threads", wraps=real_validate_threads) as spy:
            self.assertEqual(run(self.root), [])
        self.assertEqual(spy.call_count, 1)

    # --- document and relation rules ---------------------------------------

    def test_document_path_must_exist(self):
        self.update("shared/knowledge/documents.jsonl", path="missing/document.md")
        errors = self.errors()
        self.assertTrue(any("path references missing file 'missing/document.md'" in e for e in errors), errors)

    def init_git_repo(self) -> str:
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        subprocess.run(["git", "add", "README.md"], cwd=self.root, check=True)
        subprocess.run(
            ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-qm", "fixture"],
            cwd=self.root,
            check=True,
        )
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=self.root, check=True, text=True, capture_output=True
        ).stdout.strip()

    @unittest.skipUnless(shutil.which("git"), "git is required")
    def test_snapshot_commit_can_be_verified_against_git(self):
        self.update("shared/state/snapshots.jsonl", source_commit=self.init_git_repo())
        self.assertEqual(run(self.root, check_git=True), [])

    @unittest.skipUnless(shutil.which("git"), "git is required")
    def test_missing_snapshot_commit_is_reported(self):
        self.init_git_repo()
        self.update("shared/state/snapshots.jsonl", source_commit="deadbee")
        errors = run(self.root, check_git=True)
        self.assertTrue(any("does not exist in Git history" in e for e in errors), errors)

    def test_snapshot_commit_is_not_resolved_without_the_flag(self):
        self.update("shared/state/snapshots.jsonl", source_commit="deadbee")
        self.assertEqual(run(self.root), [])

    @unittest.skipUnless(shutil.which("git"), "git is required")
    def test_cli_check_git_reports_missing_commit(self):
        self.init_git_repo()
        self.update("shared/state/snapshots.jsonl", source_commit="deadbee")
        with mock.patch("sys.stdout"):
            self.assertEqual(main(["--root", str(self.root), "--check-git"]), 1)

    def test_invalid_timestamp_is_reported(self):
        self.update("shared/communications/messages.jsonl", timestamp="yesterday")
        errors = self.errors()
        self.assertTrue(any("timestamp must be a UTC ISO-8601 timestamp" in e for e in errors), errors)

    def test_missing_source_path_is_reported(self):
        self.update("shared/state/events.jsonl", source_refs=["missing/event-source.md"])
        errors = self.errors()
        self.assertTrue(any("source_refs references missing path 'missing/event-source.md'" in e for e in errors), errors)

    def empty_thread(self) -> None:
        write_jsonl(self.root / "shared/communications/messages.jsonl", [])
        self.update("shared/communications/threads.jsonl", message_ids=[])

    def write_mapping(self, **overrides) -> None:
        record = {
            "id": "LTM-001",
            "thread_id": "thread:one",
            "legacy_index": 0,
            "legacy_timestamp": "2026-01-01T00:00:00Z",
            "legacy_sender": "agent",
            "mapping_basis": "Reviewed orientation handshake",
            "reviewed_by": "agent",
            "reviewed_at": "2026-01-02T00:00:00Z",
        }
        record.update(overrides)
        write_jsonl(self.root / "shared/communications/migrations/legacy-thread-map.jsonl", [record])

    def test_empty_thread_requires_legacy_evidence_or_seed_rationale(self):
        self.empty_thread()
        errors = self.errors()
        self.assertTrue(any("empty thread has no legacy mapping" in e for e in errors), errors)

    def test_empty_thread_with_reviewed_legacy_mapping_is_valid(self):
        self.empty_thread()
        write_jsonl(self.root / "shared/communications/log.jsonl", [{
            "timestamp": "2026-01-01T00:00:00Z", "sender": "agent", "target": "all",
            "type": "handshake", "content": "hello",
        }])
        self.write_mapping()
        self.assertEqual(self.errors(), [])

    def test_empty_thread_with_seed_evidence_is_valid(self):
        self.empty_thread()
        self.update(
            "shared/communications/threads.jsonl",
            seed_only=True,
            evidence_refs=["README.md"],
        )
        self.assertEqual(self.errors(), [])

    def test_seed_only_thread_requires_evidence(self):
        self.empty_thread()
        self.update("shared/communications/threads.jsonl", seed_only=True, evidence_refs=[])
        errors = self.errors()
        self.assertTrue(any("evidence_refs must contain at least 1" in e for e in errors), errors)

    def test_legacy_mapping_timestamp_must_match_log_entry(self):
        self.empty_thread()
        write_jsonl(self.root / "shared/communications/log.jsonl", [{
            "timestamp": "2026-01-01T00:00:00Z", "sender": "agent", "target": "all",
            "type": "handshake", "content": "hello",
        }])
        self.write_mapping(legacy_timestamp="2026-01-01T00:00:01Z")
        errors = self.errors()
        self.assertTrue(any("legacy_timestamp does not match" in e for e in errors), errors)

    def test_legacy_mapping_thread_must_exist(self):
        self.empty_thread()
        write_jsonl(self.root / "shared/communications/log.jsonl", [{
            "timestamp": "2026-01-01T00:00:00Z", "sender": "agent", "target": "all",
            "type": "handshake", "content": "hello",
        }])
        self.write_mapping(thread_id="thread:missing")
        errors = self.errors()
        self.assertTrue(any("thread_id references unknown thread" in e for e in errors), errors)

    def test_thread_must_list_message_from_its_thread(self):
        self.update("shared/communications/threads.jsonl", message_ids=[])
        errors = self.errors()
        self.assertTrue(any("thread message_ids omits message 'msg:one'" in e for e in errors), errors)

    def test_message_must_belong_to_the_thread_that_lists_it(self):
        write_jsonl(self.root / "shared/communications/threads.jsonl", [{
            "thread_id": "thread:one", "title": "Thread", "status": "open",
            "topic": "testing", "message_ids": ["msg:one"],
            "created_at": "2026-01-01T00:00:00Z",
        }, {
            "thread_id": "thread:two", "title": "Other", "status": "open",
            "topic": "testing", "message_ids": ["msg:one"],
            "created_at": "2026-01-01T00:00:00Z",
        }])
        errors = self.errors()
        self.assertTrue(any("belongs to thread 'thread:one', not 'thread:two'" in e for e in errors), errors)

    def test_invalid_work_priority_is_reported(self):
        self.update("shared/work/items.jsonl", priority="urgent")
        errors = self.errors()
        self.assertTrue(any("invalid work priority 'urgent'" in e for e in errors), errors)

    def test_work_requires_created_and_updated_timestamps(self):
        records = read_jsonl(self.root / "shared/work/items.jsonl")
        del records[0]["created_at"]
        write_jsonl(self.root / "shared/work/items.jsonl", records)
        self.assertTrue(any("missing created_at" in e for e in self.errors()))

    def test_updated_at_cannot_precede_created_at(self):
        self.update("shared/work/items.jsonl", updated_at="2025-12-31T00:00:00Z")
        self.assertTrue(any("updated_at precedes created_at" in e for e in self.errors()))

    def test_work_requires_acceptance_criteria(self):
        self.update("shared/work/items.jsonl", acceptance_criteria=[])
        errors = self.errors()
        self.assertTrue(any("acceptance_criteria must contain at least 1 item" in e for e in errors), errors)

    def test_work_goal_reference_must_exist(self):
        self.update("shared/work/items.jsonl", goal_ids=["goal:missing"])
        errors = self.errors()
        self.assertTrue(any("goal_ids references unknown goal 'goal:missing'" in e for e in errors), errors)

    def test_verified_work_requires_verification_evidence(self):
        self.update("shared/work/items.jsonl", status="verified", verification={"status": "verified", "evidence_refs": []})
        errors = self.errors()
        self.assertTrue(any("verified work must record verification evidence" in e for e in errors), errors)

    def test_duplicate_document_id_is_reported(self):
        docs = read_jsonl(self.root / "shared/knowledge/documents.jsonl")
        write_jsonl(self.root / "shared/knowledge/documents.jsonl", docs + [dict(docs[0])])
        self.assertTrue(any("duplicate id" in e for e in self.errors()))

    def test_unknown_relation_endpoint_is_reported(self):
        self.update("shared/knowledge/relations.jsonl", object="doc:missing")
        self.assertTrue(any("references unknown entity 'doc:missing'" in e for e in self.errors()))

    def test_invalid_provenance_type_is_reported(self):
        self.update("shared/knowledge/documents.jsonl", provenance_type="made_up")
        self.assertTrue(any("invalid provenance_type" in e for e in self.errors()))

    # --- message and thread rules ------------------------------------------

    def test_message_in_unknown_thread_is_reported(self):
        self.update("shared/communications/messages.jsonl", thread_id="thread:missing")
        errors = self.errors()
        self.assertTrue(any("unknown thread_id 'thread:missing'" in e for e in errors), errors)

    def test_thread_referencing_unknown_message_is_reported(self):
        self.update("shared/communications/threads.jsonl", message_ids=["msg:missing"])
        self.assertTrue(any("references unknown message 'msg:missing'" in e for e in self.errors()))

    def test_reply_to_must_reference_an_earlier_message(self):
        (self.root / "shared/communications/messages.jsonl").write_text(
            json.dumps({
                "message_id": "msg:one", "thread_id": "thread:one",
                "timestamp": "2026-01-01T00:00:00Z", "sender": "agent", "target": "agent",
                "type": "update", "content": "hi", "source_refs": [],
                "provenance_type": "declared", "reply_to": "msg:later",
            }) + "\n" + json.dumps({
                "message_id": "msg:later", "thread_id": "thread:one",
                "timestamp": "2026-01-01T00:00:01Z", "sender": "agent", "target": "agent",
                "type": "reply", "content": "there", "source_refs": [],
                "provenance_type": "declared",
            }) + "\n",
            encoding="utf-8",
        )
        self.update("shared/communications/threads.jsonl", message_ids=["msg:one", "msg:later"])
        self.assertTrue(any("reply_to references a later/unknown message" in e for e in self.errors()))

    def test_invalid_message_type_is_reported(self):
        self.update("shared/communications/messages.jsonl", type="shout")
        self.assertTrue(any("invalid message type 'shout'" in e for e in self.errors()))

    # --- work, review and journal rules -------------------------------------

    def test_unknown_work_dependency_is_reported(self):
        self.update("shared/work/items.jsonl", depends_on=["work:missing"])
        self.assertTrue(any("depends_on references unknown work item 'work:missing'" in e for e in self.errors()))

    def test_verified_work_requires_non_pending_verification(self):
        self.update("shared/work/items.jsonl", status="verified")
        self.assertTrue(any("verified work must have non-pending verification" in e for e in self.errors()))

    def test_null_verification_is_reported_without_crashing(self):
        self.update("shared/work/items.jsonl", verification=None)
        errors = self.errors()
        self.assertTrue(any("verification must be an object" in e for e in errors), errors)

    def test_null_depends_on_is_reported_without_crashing(self):
        self.update("shared/work/items.jsonl", depends_on=None)
        errors = self.errors()
        self.assertTrue(any("depends_on must be a list" in e for e in errors), errors)

    def test_non_string_dependency_is_reported_without_crashing(self):
        self.update("shared/work/items.jsonl", depends_on=[None, {"id": "work:two"}])
        errors = self.errors()
        self.assertTrue(any("depends_on entries must be strings" in e for e in errors), errors)

    def test_malformed_event_journal_does_not_skip_later_journals(self):
        (self.root / "shared/state/events.jsonl").write_text("{bad json\n", encoding="utf-8")
        self.update("shared/state/snapshots.jsonl", source_commit="not-a-sha")
        (self.root / "shared/decisions.jsonl").write_text("{}\n", encoding="utf-8")
        errors = self.errors()
        self.assertTrue(any("events.jsonl:1: invalid JSON" in e for e in errors), errors)
        self.assertTrue(any("snapshots.jsonl" in e and "not a Git SHA" in e for e in errors), errors)
        self.assertTrue(any("decisions.jsonl:1: missing id" in e for e in errors), errors)

    def test_malformed_snapshot_journal_does_not_skip_decisions(self):
        (self.root / "shared/state/snapshots.jsonl").write_text("{bad json\n", encoding="utf-8")
        (self.root / "shared/decisions.jsonl").write_text("{}\n", encoding="utf-8")
        errors = self.errors()
        self.assertTrue(any("snapshots.jsonl:1: invalid JSON" in e for e in errors), errors)
        self.assertTrue(any("decisions.jsonl:1: missing id" in e for e in errors), errors)

    def test_review_requires_checked_criteria(self):
        self.update("shared/work/reviews.jsonl", criteria_checked=[])
        errors = self.errors()
        self.assertTrue(any("criteria_checked must contain at least 1 item" in e for e in errors), errors)

    def test_invalid_review_result_is_reported(self):
        self.update("shared/work/reviews.jsonl", result="looks_fine")
        errors = self.errors()
        self.assertTrue(any("invalid review result 'looks_fine'" in e for e in errors), errors)

    def test_decision_with_unknown_goal_is_reported(self):
        self.update("shared/decisions.jsonl", affected_goals=["CG-missing"])
        errors = self.errors()
        self.assertTrue(any("affected_goals references unknown goal 'CG-missing'" in e for e in errors), errors)

    def test_decision_with_unknown_work_item_is_reported(self):
        self.update("shared/decisions.jsonl", related_work_ids=["work:missing"])
        errors = self.errors()
        self.assertTrue(any("related_work_ids references unknown work item 'work:missing'" in e for e in errors), errors)

    def test_decision_with_unknown_origin_thread_is_reported(self):
        self.update("shared/decisions.jsonl", origin_thread_ids=["thread:missing"])
        errors = self.errors()
        self.assertTrue(any("origin_thread_ids references unknown thread 'thread:missing'" in e for e in errors), errors)

    def test_invalid_decision_status_is_reported(self):
        self.update("shared/decisions.jsonl", status="probably_fine")
        errors = self.errors()
        self.assertTrue(any("invalid decision status 'probably_fine'" in e for e in errors), errors)

    def test_review_of_unknown_work_item_is_reported(self):
        self.update("shared/work/reviews.jsonl", work_id="work:missing")
        self.assertTrue(any("work_id references unknown work item 'work:missing'" in e for e in self.errors()))

    def test_non_sha_snapshot_commit_is_reported(self):
        self.update("shared/state/snapshots.jsonl", source_commit="not-a-sha")
        self.assertTrue(any("source_commit is not a Git SHA-like value" in e for e in self.errors()))

    def test_duplicate_event_id_is_reported(self):
        events = read_jsonl(self.root / "shared/state/events.jsonl")
        write_jsonl(self.root / "shared/state/events.jsonl", events + [dict(events[0])])
        self.assertTrue(any("duplicate id 'evt:one'" in e for e in self.errors()))

    def test_missing_required_file_is_reported(self):
        (self.root / "shared/decisions.jsonl").unlink()
        errors = self.errors()
        self.assertIn("missing required semantic file: shared/decisions.jsonl", errors)


if __name__ == "__main__":
    unittest.main()
