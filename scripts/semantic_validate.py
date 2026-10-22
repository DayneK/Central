#!/usr/bin/env python3
"""Validate Central's explicit semantic substrate.

Standard-library only. This validates repository data; it does not authenticate
authors or make inferred relationships authoritative.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROVENANCE = {"declared", "observed", "evidenced", "inferred", "unknown_disputed"}


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


def validate_events(root: Path):
    errors = []
    for relative, fields in {
        "shared/state/events.jsonl": ("id", "timestamp", "type", "summary", "actors", "source_refs"),
        "shared/state/snapshots.jsonl": ("id", "timestamp", "label", "source_commit", "state_file"),
        "shared/decisions.jsonl": ("id", "timestamp", "decision", "context", "alternatives", "rationale", "status", "affected_goals", "evidence", "review_trigger"),
        "shared/communications/threads.jsonl": ("thread_id", "title", "status", "message_ids", "topic"),
    }.items():
        path = root / relative
        ids = set()
        for line, item in jsonl(path):
            for field in fields:
                if field not in item:
                    errors.append(f"{path}:{line}: missing {field}")
            key = item.get(fields[0])
            if key in ids:
                errors.append(f"{path}:{line}: duplicate id {key!r}")
            ids.add(key)
    return errors


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    errors = []
    try:
        document_errors, ids = validate_documents(root)
        errors.extend(document_errors)
        errors.extend(validate_relations(root, ids))
        errors.extend(validate_events(root))
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
