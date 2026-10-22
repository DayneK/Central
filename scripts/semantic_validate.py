#!/usr/bin/env python3
"""Validate Central's explicit semantic substrate.

Standard-library only. This validates repository data; it does not authenticate
authors or make inferred relationships authoritative.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PROVENANCE = {"declared", "observed", "evidenced", "inferred", "unknown_disputed"}
THREAD_STATUS = {"open", "active", "decision_pending", "resolved", "dormant", "superseded", "archived"}
WORK_STATUS = {"proposed", "ready", "active", "blocked", "implemented", "verified", "cancelled", "superseded"}
MESSAGE_TYPES = {"handshake", "proposal", "query", "update", "evidence", "decision", "reply"}


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


def validate_documents(root: Path):
    errors = []
    ids = set()
    path = root / "shared/knowledge/documents.jsonl"
    for line, item in jsonl(path):
        for field in ("id", "type", "title", "provenance_type", "status"):
            if not isinstance(item.get(field), str) or not item[field]:
                errors.append(f"{path}:{line}: missing/invalid {field}")
        if item.get("id") in ids:
            errors.append(f"{path}:{line}: duplicate id {item['id']!r}")
        ids.add(item.get("id"))
        if item.get("provenance_type") not in PROVENANCE:
            errors.append(f"{path}:{line}: invalid provenance_type")
    return errors, ids


def validate_relations(root: Path, known_ids: set[str]):
    errors = []
    ids = set()
    path = root / "shared/knowledge/relations.jsonl"
    for line, item in jsonl(path):
        for field in ("id", "subject", "predicate", "object", "provenance_type", "status"):
            if not isinstance(item.get(field), str) or not item[field]:
                errors.append(f"{path}:{line}: missing/invalid {field}")
        if item.get("id") in ids:
            errors.append(f"{path}:{line}: duplicate relation id {item['id']!r}")
        ids.add(item.get("id"))
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
    message_ids = set()
    thread_ids = set()
    messages = []
    for line, item in jsonl(path):
        require_fields(path, line, item, ("message_id", "thread_id", "timestamp", "sender", "target", "type", "content", "source_refs", "provenance_type"), errors)
        mid = item.get("message_id")
        if mid in message_ids:
            errors.append(f"{path}:{line}: duplicate message_id {mid!r}")
        message_ids.add(mid)
        if item.get("thread_id"):
            thread_ids.add(item["thread_id"])
        if item.get("type") not in MESSAGE_TYPES:
            errors.append(f"{path}:{line}: invalid message type {item.get('type')!r}")
        if item.get("provenance_type") not in PROVENANCE:
            errors.append(f"{path}:{line}: invalid provenance_type")
        if not isinstance(item.get("source_refs"), list):
            errors.append(f"{path}:{line}: source_refs must be a list")
        reply = item.get("reply_to")
        if reply is not None and reply not in message_ids:
            errors.append(f"{path}:{line}: reply_to references a later/unknown message {reply!r}")
        messages.append(item)
    return errors, message_ids, thread_ids, messages


def validate_threads(root: Path, message_ids: set[str]):
    errors = []
    ids = set()
    path = root / "shared/communications/threads.jsonl"
    for line, item in jsonl(path):
        require_fields(path, line, item, ("thread_id", "title", "status", "message_ids", "topic"), errors)
        tid = item.get("thread_id")
        if tid in ids:
            errors.append(f"{path}:{line}: duplicate thread_id {tid!r}")
        ids.add(tid)
        if item.get("status") not in THREAD_STATUS:
            errors.append(f"{path}:{line}: invalid thread status {item.get('status')!r}")
        if not isinstance(item.get("message_ids"), list):
            errors.append(f"{path}:{line}: message_ids must be a list")
        else:
            for mid in item["message_ids"]:
                if mid not in message_ids:
                    errors.append(f"{path}:{line}: message_ids references unknown message {mid!r}")
    return errors, ids


def validate_work(root: Path):
    errors = []
    ids = set()
    path = root / "shared/work/items.jsonl"
    for line, item in jsonl(path):
        require_fields(path, line, item, ("id", "title", "description", "status", "priority", "owner", "depends_on", "source_refs", "acceptance_criteria", "verification", "provenance_type"), errors)
        wid = item.get("id")
        if wid in ids:
            errors.append(f"{path}:{line}: duplicate work id {wid!r}")
        ids.add(wid)
        if item.get("status") not in WORK_STATUS:
            errors.append(f"{path}:{line}: invalid work status {item.get('status')!r}")
        if item.get("provenance_type") not in PROVENANCE:
            errors.append(f"{path}:{line}: invalid provenance_type")
        if item.get("status") == "verified" and item.get("verification", {}).get("status") in {None, "pending"}:
            errors.append(f"{path}:{line}: verified work must have non-pending verification")
    for line, item in jsonl(path):
        for dep in item.get("depends_on", []):
            if dep not in ids:
                errors.append(f"{path}:{line}: depends_on references unknown work item {dep!r}")
    return errors, ids


def validate_reviews(root: Path, work_ids: set[str]):
    errors = []
    ids = set()
    path = root / "shared/work/reviews.jsonl"
    for line, item in jsonl(path):
        require_fields(path, line, item, ("id", "timestamp", "work_id", "reviewer", "result", "criteria_checked", "evidence_refs"), errors)
        rid = item.get("id")
        if rid in ids:
            errors.append(f"{path}:{line}: duplicate review id {rid!r}")
        ids.add(rid)
        if item.get("work_id") not in work_ids:
            errors.append(f"{path}:{line}: work_id references unknown work item {item.get('work_id')!r}")
    return errors


def validate_events(root: Path):
    errors = []
    for relative, fields in {
        "shared/state/events.jsonl": ("id", "timestamp", "type", "summary", "actors", "source_refs"),
        "shared/state/snapshots.jsonl": ("id", "timestamp", "label", "source_commit", "state_file"),
        "shared/decisions.jsonl": ("id", "timestamp", "decision", "context", "alternatives", "rationale", "status", "affected_goals", "evidence", "review_trigger"),
    }.items():
        path = root / relative
        ids = set()
        for line, item in jsonl(path):
            require_fields(path, line, item, fields, errors)
            key = item.get(fields[0])
            if key in ids:
                errors.append(f"{path}:{line}: duplicate id {key!r}")
            ids.add(key)
            if relative.endswith("snapshots.jsonl") and item.get("source_commit") and not re.fullmatch(r"[0-9a-f]{7,40}", str(item["source_commit"])):
                errors.append(f"{path}:{line}: source_commit is not a Git SHA-like value")
    return errors


def validate_paths(root: Path):
    errors = []
    required = [
        "shared/communications/messages.jsonl",
        "shared/communications/threads.jsonl",
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


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    errors = []
    try:
        errors.extend(validate_paths(root))
        document_errors, document_ids = validate_documents(root)
        errors.extend(document_errors)
        errors.extend(validate_relations(root, document_ids))
        message_errors, message_ids, _, _ = validate_messages(root)
        errors.extend(message_errors)
        _, thread_ids = validate_threads(root, message_ids)
        errors.extend(validate_threads(root, message_ids)[0])
        work_errors, work_ids = validate_work(root)
        errors.extend(work_errors)
        errors.extend(validate_reviews(root, work_ids))
        errors.extend(validate_events(root))
        # Validate that every modern message points at a registered thread.
        for line, item in jsonl(root / "shared/communications/messages.jsonl"):
            if item.get("thread_id") not in thread_ids:
                errors.append(f"shared/communications/messages.jsonl:{line}: unknown thread_id {item.get('thread_id')!r}")
    except (OSError, ValueError) as exc:
        errors.append(str(exc))
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print(f"Semantic validation failed: {len(errors)} issue(s).")
        return 1
    print("Semantic validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
