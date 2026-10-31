#!/usr/bin/env python3
"""Validate Central's explicit semantic substrate.

Standard-library only. This validates repository data; it does not authenticate
authors or make inferred relationships authoritative.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

PROVENANCE = {"declared", "observed", "evidenced", "inferred", "unknown_disputed"}
THREAD_STATUS = {"open", "active", "decision_pending", "resolved", "dormant", "superseded", "archived"}
WORK_STATUS = {"proposed", "ready", "active", "blocked", "implemented", "verified", "cancelled", "superseded"}
MESSAGE_TYPES = {"handshake", "proposal", "query", "update", "evidence", "decision", "reply"}
PRIORITIES = {"low", "normal", "high", "critical"}
VERIFICATION_STATUS = {"pending", "in_progress", "verified", "failed", "expired"}
REVIEW_RESULTS = {
    "pending",
    "pass",
    "approved",
    "changes_requested",
    "rejected",
    "implemented_pending_verification",
    "verified",
}
DECISION_STATUS = {"proposed", "active", "accepted", "superseded", "rejected", "deferred", "amended"}
ISO_TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")


def jsonl(path: Path):
    with path.open(encoding="utf-8") as f:
        for line_no, raw in enumerate(f, 1):
            if not raw.strip():
                continue
            try:
                value = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc.msg}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_no}: record must be an object")
            yield line_no, value


def require_fields(path: Path, line: int, item: dict, fields: tuple[str, ...], errors: list[str]):
    for field in fields:
        if field not in item:
            errors.append(f"{path}:{line}: missing {field}")


def require_strings(path: Path, line: int, item: dict, fields: tuple[str, ...], errors: list[str]):
    """Require non-empty strings, rather than merely present keys."""
    for field in fields:
        if field not in item:
            continue  # require_fields() owns the "missing" message
        value = item[field]
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{path}:{line}: missing/invalid {field}")


def parse_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str) or not ISO_TIMESTAMP.fullmatch(value):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def require_timestamp(path: Path, line: int, item: dict, field: str, errors: list[str]):
    value = item.get(field)
    if not isinstance(value, str) or not ISO_TIMESTAMP.fullmatch(value):
        errors.append(f"{path}:{line}: {field} must be a UTC ISO-8601 timestamp")


def check_string_list(
    root: Path,
    path: Path,
    line: int,
    item: dict,
    field: str,
    errors: list[str],
    *,
    min_items: int = 0,
    check_paths: bool = False,
) -> bool:
    """Validate a list of strings; optionally require each local path to exist.

    Returns True only when the field is a usable list, so callers can avoid
    running reference checks against a malformed value.
    """
    value = item.get(field)
    if not isinstance(value, list):
        errors.append(f"{path}:{line}: {field} must be a list")
        return False
    if len(value) < min_items:
        errors.append(f"{path}:{line}: {field} must contain at least {min_items} item(s)")
    valid = True
    for entry in value:
        if not isinstance(entry, str) or not entry.strip():
            errors.append(f"{path}:{line}: {field} entries must be non-empty strings")
            valid = False
            continue
        if check_paths and "://" not in entry and not (root / entry).exists():
            errors.append(f"{path}:{line}: {field} references missing path {entry!r}")
            valid = False
    return valid


def validate_documents(root: Path):
    errors = []
    ids = set()
    path = root / "shared/knowledge/documents.jsonl"
    for line, item in jsonl(path):
        require_fields(path, line, item, ("id", "type", "title", "provenance_type", "status", "path"), errors)
        require_strings(path, line, item, ("id", "type", "title", "provenance_type", "status", "path"), errors)
        if isinstance(item.get("id"), str) and item["id"] in ids:
            errors.append(f"{path}:{line}: duplicate id {item['id']!r}")
        if isinstance(item.get("id"), str):
            ids.add(item["id"])
        if item.get("provenance_type") not in PROVENANCE:
            errors.append(f"{path}:{line}: invalid provenance_type")
        document_path = item.get("path")
        if isinstance(document_path, str) and document_path.strip():
            if "://" not in document_path and not (root / document_path).exists():
                errors.append(f"{path}:{line}: path references missing file {document_path!r}")
    return errors, ids


def validate_relations(root: Path, known_ids: set[str]):
    errors = []
    ids = set()
    path = root / "shared/knowledge/relations.jsonl"
    for line, item in jsonl(path):
        require_fields(
            path,
            line,
            item,
            ("id", "subject", "predicate", "object", "provenance_type", "status"),
            errors,
        )
        require_strings(
            path,
            line,
            item,
            ("id", "subject", "predicate", "object", "provenance_type", "status"),
            errors,
        )
        if isinstance(item.get("id"), str) and item["id"] in ids:
            errors.append(f"{path}:{line}: duplicate relation id {item['id']!r}")
        if isinstance(item.get("id"), str):
            ids.add(item["id"])
        if item.get("provenance_type") not in PROVENANCE:
            errors.append(f"{path}:{line}: invalid provenance_type")
        for field in ("subject", "object"):
            value = item.get(field)
            if value not in known_ids:
                errors.append(f"{path}:{line}: {field} references unknown entity {value!r}")
    return errors


def validate_messages(root: Path):
    errors = []
    path = root / "shared/communications/messages.jsonl"
    message_ids: set[str] = set()
    thread_ids: set[str] = set()
    messages = []
    for line, item in jsonl(path):
        require_fields(
            path,
            line,
            item,
            (
                "message_id",
                "thread_id",
                "timestamp",
                "sender",
                "target",
                "type",
                "content",
                "source_refs",
                "provenance_type",
            ),
            errors,
        )
        require_strings(
            path,
            line,
            item,
            ("message_id", "thread_id", "timestamp", "sender", "target", "content", "provenance_type"),
            errors,
        )
        require_timestamp(path, line, item, "timestamp", errors)
        mid = item.get("message_id")
        if isinstance(mid, str) and mid in message_ids:
            errors.append(f"{path}:{line}: duplicate message_id {mid!r}")
        if isinstance(mid, str):
            message_ids.add(mid)
        if isinstance(item.get("thread_id"), str) and item["thread_id"]:
            thread_ids.add(item["thread_id"])
        if item.get("type") not in MESSAGE_TYPES:
            errors.append(f"{path}:{line}: invalid message type {item.get('type')!r}")
        if item.get("provenance_type") not in PROVENANCE:
            errors.append(f"{path}:{line}: invalid provenance_type")
        check_string_list(root, path, line, item, "source_refs", errors, check_paths=True)
        reply = item.get("reply_to")
        if reply is not None and reply not in message_ids:
            errors.append(f"{path}:{line}: reply_to references a later/unknown message {reply!r}")
        messages.append(item)
    return errors, message_ids, thread_ids, messages


def validate_threads(
    root: Path,
    message_ids: set[str],
    messages: list[dict] | None = None,
    mapped_threads: set[str] | None = None,
):
    errors = []
    ids = set()
    path = root / "shared/communications/threads.jsonl"
    messages = messages or []
    mapped_threads = mapped_threads or set()
    for line, item in jsonl(path):
        require_fields(
            path,
            line,
            item,
            ("thread_id", "title", "status", "message_ids", "topic", "created_at"),
            errors,
        )
        require_strings(path, line, item, ("thread_id", "title", "status", "topic", "created_at"), errors)
        require_timestamp(path, line, item, "created_at", errors)
        tid = item.get("thread_id")
        if isinstance(tid, str) and tid in ids:
            errors.append(f"{path}:{line}: duplicate thread_id {tid!r}")
        if isinstance(tid, str):
            ids.add(tid)
        if item.get("status") not in THREAD_STATUS:
            errors.append(f"{path}:{line}: invalid thread status {item.get('status')!r}")
        if item.get("provenance_type") is not None and item.get("provenance_type") not in PROVENANCE:
            errors.append(f"{path}:{line}: invalid provenance_type")
        if "tags" in item:
            check_string_list(root, path, line, item, "tags", errors)
        seed_only = item.get("seed_only")
        if seed_only is not None and not isinstance(seed_only, bool):
            errors.append(f"{path}:{line}: seed_only must be a boolean")
        if not check_string_list(root, path, line, item, "message_ids", errors):
            continue
        listed = item["message_ids"]
        if not listed and seed_only is True:
            check_string_list(root, path, line, item, "evidence_refs", errors, min_items=1, check_paths=True)
        elif not listed and isinstance(tid, str) and tid not in mapped_threads:
            errors.append(
                f"{path}:{line}: empty thread has no legacy mapping or explicit seed evidence"
            )
        elif listed and seed_only is True:
            errors.append(f"{path}:{line}: seed_only cannot be true when message_ids is not empty")
        if len(set(listed)) != len(listed):
            errors.append(f"{path}:{line}: message_ids contains duplicates")
        for mid in listed:
            if mid not in message_ids:
                errors.append(f"{path}:{line}: message_ids references unknown message {mid!r}")
            else:
                matching = next((m for m in messages if m.get("message_id") == mid), None)
                if matching is not None and matching.get("thread_id") != tid:
                    errors.append(
                        f"{path}:{line}: message {mid!r} belongs to thread "
                        f"{matching.get('thread_id')!r}, not {tid!r}"
                    )
        if isinstance(tid, str) and messages:
            missing = sorted(
                str(m.get("message_id"))
                for m in messages
                if m.get("thread_id") == tid and m.get("message_id") not in listed
            )
            for mid in missing:
                errors.append(f"{path}:{line}: thread message_ids omits message {mid!r}")
    return errors, ids


def read_legacy_mappings(root: Path) -> list[dict]:
    """Load structurally usable mappings so empty threads can reference them.

    Full validation happens in validate_legacy_map(); malformed entries are
    ignored here only to avoid attributing evidence that cannot be trusted.
    """
    path = root / "shared/communications/migrations/legacy-thread-map.jsonl"
    if not path.is_file():
        return []
    try:
        return [item for _, item in jsonl(path) if isinstance(item.get("thread_id"), str)]
    except (OSError, ValueError, TypeError):
        return []


def validate_legacy_map(root: Path, thread_ids: set[str]):
    errors = []
    ids = set()
    pairs = set()
    path = root / "shared/communications/migrations/legacy-thread-map.jsonl"
    log_path = root / "shared/communications/log.jsonl"
    try:
        legacy = [item for _, item in jsonl(log_path)]
    except (OSError, ValueError, TypeError) as exc:
        return [f"{log_path}: {exc}"]
    for line, item in jsonl(path):
        require_fields(
            path,
            line,
            item,
            (
                "id",
                "thread_id",
                "legacy_index",
                "legacy_timestamp",
                "legacy_sender",
                "mapping_basis",
                "reviewed_by",
                "reviewed_at",
            ),
            errors,
        )
        require_strings(
            path,
            line,
            item,
            ("id", "thread_id", "legacy_timestamp", "legacy_sender", "mapping_basis", "reviewed_by", "reviewed_at"),
            errors,
        )
        require_timestamp(path, line, item, "reviewed_at", errors)
        key = item.get("id")
        if isinstance(key, str) and key in ids:
            errors.append(f"{path}:{line}: duplicate mapping id {key!r}")
        if isinstance(key, str):
            ids.add(key)
        thread_id = item.get("thread_id")
        if isinstance(thread_id, str) and thread_ids is not None and thread_id not in thread_ids:
            errors.append(f"{path}:{line}: thread_id references unknown thread {thread_id!r}")
        index = item.get("legacy_index")
        if isinstance(index, bool) or not isinstance(index, int) or index < 0:
            errors.append(f"{path}:{line}: legacy_index must be a non-negative integer")
            continue
        pair = (thread_id, index)
        if pair in pairs:
            errors.append(f"{path}:{line}: duplicate mapping for {thread_id!r} at index {index}")
        pairs.add(pair)
        if index >= len(legacy):
            errors.append(f"{path}:{line}: legacy_index {index} is out of range")
            continue
        record = legacy[index]
        if item.get("legacy_timestamp") != record.get("timestamp"):
            errors.append(
                f"{path}:{line}: legacy_timestamp does not match log entry {index} "
                f"({record.get('timestamp')!r})"
            )
        if item.get("legacy_sender") != record.get("sender"):
            errors.append(
                f"{path}:{line}: legacy_sender does not match log entry {index} "
                f"({record.get('sender')!r})"
            )
    return errors


def validate_work(root: Path, goal_ids: set[str] | None = None):
    errors = []
    ids = set()
    records = []
    path = root / "shared/work/items.jsonl"
    for line, item in jsonl(path):
        records.append((line, item))
        require_fields(
            path,
            line,
            item,
            (
                "id",
                "title",
                "description",
                "status",
                "priority",
                "owner",
                "depends_on",
                "source_refs",
                "acceptance_criteria",
                "verification",
                "provenance_type",
                "created_at",
                "updated_at",
            ),
            errors,
        )
        require_strings(
            path,
            line,
            item,
            ("id", "title", "description", "owner", "provenance_type"),
            errors,
        )
        wid = item.get("id")
        if isinstance(wid, str) and wid in ids:
            errors.append(f"{path}:{line}: duplicate work id {wid!r}")
        if isinstance(wid, str):
            ids.add(wid)
        status = item.get("status")
        if not isinstance(status, str) or status not in WORK_STATUS:
            errors.append(f"{path}:{line}: invalid work status {status!r}")
        priority = item.get("priority")
        if not isinstance(priority, str) or priority not in PRIORITIES:
            errors.append(f"{path}:{line}: invalid work priority {priority!r}")
        provenance = item.get("provenance_type")
        if not isinstance(provenance, str) or provenance not in PROVENANCE:
            errors.append(f"{path}:{line}: invalid provenance_type")
        require_timestamp(path, line, item, "created_at", errors)
        require_timestamp(path, line, item, "updated_at", errors)
        created = parse_timestamp(item.get("created_at"))
        updated = parse_timestamp(item.get("updated_at"))
        if created is not None and updated is not None and updated < created:
            errors.append(f"{path}:{line}: updated_at precedes created_at")
        dependencies = item.get("depends_on")
        if not isinstance(dependencies, list):
            errors.append(f"{path}:{line}: depends_on must be a list")
        elif any(not isinstance(dep, str) for dep in dependencies):
            errors.append(f"{path}:{line}: depends_on entries must be strings")
        check_string_list(root, path, line, item, "source_refs", errors, check_paths=True)
        check_string_list(root, path, line, item, "acceptance_criteria", errors, min_items=1)
        if "goal_ids" in item:
            if check_string_list(root, path, line, item, "goal_ids", errors) and goal_ids is not None:
                for goal_id in item["goal_ids"]:
                    if goal_id not in goal_ids:
                        errors.append(f"{path}:{line}: goal_ids references unknown goal {goal_id!r}")
        verification = item.get("verification")
        if not isinstance(verification, dict):
            errors.append(f"{path}:{line}: verification must be an object")
        else:
            verification_status = verification.get("status")
            if not isinstance(verification_status, str) or verification_status not in VERIFICATION_STATUS:
                errors.append(f"{path}:{line}: invalid verification status {verification_status!r}")
            evidence_ok = check_string_list(root, path, line, verification, "evidence_refs", errors, check_paths=True)
            if status == "verified":
                if verification_status == "pending":
                    errors.append(f"{path}:{line}: verified work must have non-pending verification")
                elif verification_status != "verified":
                    errors.append(f"{path}:{line}: verified work must have verification status 'verified'")
                elif evidence_ok and not verification.get("evidence_refs"):
                    errors.append(f"{path}:{line}: verified work must record verification evidence")
    for line, item in records:
        dependencies = item.get("depends_on")
        if isinstance(dependencies, list):
            for dep in dependencies:
                if isinstance(dep, str) and dep not in ids:
                    errors.append(f"{path}:{line}: depends_on references unknown work item {dep!r}")
    return errors, ids


def validate_reviews(root: Path, work_ids: set[str]):
    errors = []
    ids = set()
    path = root / "shared/work/reviews.jsonl"
    for line, item in jsonl(path):
        require_fields(
            path,
            line,
            item,
            ("id", "timestamp", "work_id", "reviewer", "result", "criteria_checked", "evidence_refs"),
            errors,
        )
        require_strings(path, line, item, ("id", "work_id", "reviewer", "result"), errors)
        require_timestamp(path, line, item, "timestamp", errors)
        rid = item.get("id")
        if isinstance(rid, str) and rid in ids:
            errors.append(f"{path}:{line}: duplicate review id {rid!r}")
        if isinstance(rid, str):
            ids.add(rid)
        if item.get("work_id") not in work_ids:
            errors.append(f"{path}:{line}: work_id references unknown work item {item.get('work_id')!r}")
        if item.get("result") not in REVIEW_RESULTS:
            errors.append(f"{path}:{line}: invalid review result {item.get('result')!r}")
        check_string_list(root, path, line, item, "criteria_checked", errors, min_items=1)
        check_string_list(root, path, line, item, "evidence_refs", errors, check_paths=True)
    return errors


def validate_events(root: Path):
    errors = []
    path = root / "shared/state/events.jsonl"
    ids = set()
    try:
        for line, item in jsonl(path):
            fields = ("id", "timestamp", "type", "summary", "actors", "source_refs")
            require_fields(path, line, item, fields, errors)
            require_strings(path, line, item, ("id", "timestamp", "type", "summary"), errors)
            require_timestamp(path, line, item, "timestamp", errors)
            key = item.get("id")
            if isinstance(key, str) and key in ids:
                errors.append(f"{path}:{line}: duplicate id {key!r}")
            if isinstance(key, str):
                ids.add(key)
            check_string_list(root, path, line, item, "actors", errors, min_items=1)
            check_string_list(root, path, line, item, "source_refs", errors, check_paths=True)
    except (OSError, ValueError, TypeError) as exc:
        errors.append(f"{path}: {exc}")
    return errors


def git_commit_exists(root: Path, commit: str) -> bool:
    """Ask Git whether a snapshot commit resolves to a commit object."""
    result = subprocess.run(
        ["git", "-C", str(root), "cat-file", "-e", f"{commit}^{{commit}}"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def validate_snapshots(root: Path, check_git: bool = False):
    errors = []
    path = root / "shared/state/snapshots.jsonl"
    ids = set()
    try:
        for line, item in jsonl(path):
            fields = ("id", "timestamp", "label", "source_commit", "state_file")
            require_fields(path, line, item, fields, errors)
            require_strings(path, line, item, ("id", "label", "source_commit", "state_file"), errors)
            require_timestamp(path, line, item, "timestamp", errors)
            key = item.get("id")
            if isinstance(key, str) and key in ids:
                errors.append(f"{path}:{line}: duplicate id {key!r}")
            if isinstance(key, str):
                ids.add(key)
            commit = item.get("source_commit")
            if isinstance(commit, str) and commit and not re.fullmatch(r"[0-9a-f]{7,40}", commit):
                errors.append(f"{path}:{line}: source_commit is not a Git SHA-like value")
            elif check_git and isinstance(commit, str) and commit:
                try:
                    exists = git_commit_exists(root, commit)
                except OSError as exc:
                    errors.append(f"{path}:{line}: cannot verify source_commit {commit!r}: {exc}")
                else:
                    if not exists:
                        errors.append(
                            f"{path}:{line}: source_commit {commit!r} does not exist in Git history"
                        )
            state_file = item.get("state_file")
            if isinstance(state_file, str) and state_file.strip():
                if "://" not in state_file and not (root / state_file).exists():
                    errors.append(f"{path}:{line}: state_file references missing file {state_file!r}")
    except (OSError, ValueError, TypeError) as exc:
        errors.append(f"{path}: {exc}")
    return errors


def validate_decisions(
    root: Path,
    goal_ids: set[str] | None,
    work_ids: set[str] | None,
    thread_ids: set[str] | None,
):
    errors = []
    ids = set()
    path = root / "shared/decisions.jsonl"
    for line, item in jsonl(path):
        fields = (
            "id",
            "timestamp",
            "decision",
            "context",
            "alternatives",
            "rationale",
            "status",
            "affected_goals",
            "evidence",
            "review_trigger",
        )
        require_fields(path, line, item, fields, errors)
        require_strings(
            path,
            line,
            item,
            ("id", "timestamp", "decision", "context", "rationale", "status", "review_trigger"),
            errors,
        )
        require_timestamp(path, line, item, "timestamp", errors)
        key = item.get("id")
        if isinstance(key, str) and key in ids:
            errors.append(f"{path}:{line}: duplicate id {key!r}")
        if isinstance(key, str):
            ids.add(key)
        if item.get("status") not in DECISION_STATUS:
            errors.append(f"{path}:{line}: invalid decision status {item.get('status')!r}")
        check_string_list(root, path, line, item, "alternatives", errors)
        check_string_list(root, path, line, item, "evidence", errors, check_paths=True)
        if check_string_list(root, path, line, item, "affected_goals", errors) and goal_ids is not None:
            for goal_id in item["affected_goals"]:
                if goal_id not in goal_ids:
                    errors.append(f"{path}:{line}: affected_goals references unknown goal {goal_id!r}")
        if "related_work_ids" in item:
            if check_string_list(root, path, line, item, "related_work_ids", errors) and work_ids is not None:
                for work_id in item["related_work_ids"]:
                    if work_id not in work_ids:
                        errors.append(f"{path}:{line}: related_work_ids references unknown work item {work_id!r}")
        if "origin_thread_ids" in item:
            if check_string_list(root, path, line, item, "origin_thread_ids", errors) and thread_ids is not None:
                for thread_id in item["origin_thread_ids"]:
                    if thread_id not in thread_ids:
                        errors.append(f"{path}:{line}: origin_thread_ids references unknown thread {thread_id!r}")
    return errors


def collect_goal_ids(root: Path) -> set[str]:
    """Collect goal IDs across agent and shared registries.

    Agent goal registries are validated in detail by agent_workspace.py; this
    only builds the reference set needed to resolve decision records.
    """
    ids: set[str] = set()
    paths = sorted((root / "agents").glob("*/goals/goals.json"))
    paths += sorted((root / "projects").glob("*/shared-goals.json"))
    for path in paths:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue  # the workspace validator reports malformed goal files
        goals = data.get("goals") if isinstance(data, dict) else None
        if not isinstance(goals, list):
            continue
        for goal in goals:
            if isinstance(goal, dict) and isinstance(goal.get("id"), str):
                ids.add(goal["id"])
    return ids


def validate_paths(root: Path):
    errors = []
    required = [
        "shared/communications/log.jsonl",
        "shared/communications/messages.jsonl",
        "shared/communications/threads.jsonl",
        "shared/communications/migrations/legacy-thread-map.jsonl",
        "shared/knowledge/documents.jsonl",
        "shared/knowledge/relations.jsonl",
        "shared/state/events.jsonl",
        "shared/state/snapshots.jsonl",
        "shared/decisions.jsonl",
        "shared/work/items.jsonl",
        "shared/work/reviews.jsonl",
    ]
    for relative in required:
        if not (root / relative).is_file():
            errors.append(f"missing required semantic file: {relative}")
    return errors


def present(root: Path, relative: str) -> bool:
    """A stage whose input file is absent is skipped.

    validate_paths() already reports that file, so re-opening it would only add
    an opaque I/O error next to a precise message.
    """
    return (root / relative).is_file()


def run(root: Path, *, check_git: bool = False) -> list[str]:
    """Run every validation stage, isolating failures between stages.

    Stages are split only along data dependencies. A missing or malformed file
    is reported on its own and leaves independent stages running, instead of
    silently disabling every check that came after it.
    """
    errors: list[str] = []
    errors.extend(validate_paths(root))
    goal_ids = collect_goal_ids(root)

    # Knowledge documents, then the relations whose endpoints must be documents.
    if present(root, "shared/knowledge/documents.jsonl"):
        try:
            document_errors, document_ids = validate_documents(root)
            errors.extend(document_errors)
            if present(root, "shared/knowledge/relations.jsonl"):
                errors.extend(validate_relations(root, document_ids))
        except (OSError, ValueError) as exc:
            errors.append(str(exc))

    # Messages, the threads that contain them, and the cross-reference between.
    message_ids: set[str] = set()
    thread_ids: set[str] | None = None
    mapped_thread_ids = {
        item["thread_id"] for item in read_legacy_mappings(root) if isinstance(item.get("thread_id"), str)
    }
    if present(root, "shared/communications/messages.jsonl"):
        try:
            message_errors, message_ids, _, messages = validate_messages(root)
            errors.extend(message_errors)
            if present(root, "shared/communications/threads.jsonl"):
                thread_errors, thread_ids = validate_threads(root, message_ids, messages, mapped_thread_ids)
                errors.extend(thread_errors)
                # Validate that every modern message points at a registered thread.
                for line, item in jsonl(root / "shared/communications/messages.jsonl"):
                    if item.get("thread_id") not in thread_ids:
                        errors.append(
                            f"shared/communications/messages.jsonl:{line}: "
                            f"unknown thread_id {item.get('thread_id')!r}"
                        )
        except (OSError, ValueError) as exc:
            errors.append(str(exc))

    # Legacy thread evidence is independent of modern messages and threads.
    if present(root, "shared/communications/migrations/legacy-thread-map.jsonl") and present(
        root, "shared/communications/log.jsonl"
    ):
        try:
            errors.extend(validate_legacy_map(root, thread_ids or set()))
        except (OSError, ValueError, TypeError) as exc:
            errors.append(str(exc))

    # Work items, then the reviews that must reference them.
    work_ids: set[str] | None = None
    if present(root, "shared/work/items.jsonl"):
        try:
            work_errors, work_ids = validate_work(root, goal_ids)
            errors.extend(work_errors)
            if present(root, "shared/work/reviews.jsonl"):
                errors.extend(validate_reviews(root, work_ids))
        except (OSError, ValueError) as exc:
            errors.append(str(exc))

    # Event, snapshot, and decision journals are independent files.
    if present(root, "shared/state/events.jsonl"):
        errors.extend(validate_events(root))
    if present(root, "shared/state/snapshots.jsonl"):
        errors.extend(validate_snapshots(root, check_git=check_git))
    if present(root, "shared/decisions.jsonl"):
        try:
            errors.extend(validate_decisions(root, goal_ids, work_ids, thread_ids))
        except (OSError, ValueError, TypeError) as exc:
            errors.append(f"{root / 'shared/decisions.jsonl'}: {exc}")

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--check-git",
        action="store_true",
        help="verify snapshot source_commit values resolve in Git history (requires full history)",
    )
    args = parser.parse_args(argv)
    errors = run(args.root.resolve(), check_git=args.check_git)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print(f"Semantic validation failed: {len(errors)} issue(s).")
        return 1
    print("Semantic validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
