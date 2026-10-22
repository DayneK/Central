#!/usr/bin/env python3
"""Validate and operate Central's file-backed agent workspaces.

Standard-library only. This is repository workflow tooling, not an authentication
system, access-control boundary, or safe parser for hostile executable content.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HORIZONS = {"immediate", "short_term", "medium_term", "long_term", "ongoing"}
STATUSES = {"proposed", "active", "blocked", "deferred", "achieved", "abandoned", "superseded"}
INBOX_STATUSES = {"unread", "triaged", "in_progress", "replied", "archived"}


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, raw in enumerate(handle, 1):
            if not raw.strip():
                continue
            try:
                item = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc.msg}") from exc
            if not isinstance(item, dict):
                raise ValueError(f"{path}:{line_no}: each JSONL record must be an object")
            records.append(item)
    return records


def goal_cycle_ids(goals_by_id: dict[str, dict[str, Any]]) -> list[list[str]]:
    """Return dependency cycles without recursion-depth risk for ordinary goal graphs."""
    visiting: list[str] = []
    active: set[str] = set()
    done: set[str] = set()
    cycles: list[list[str]] = []

    def visit(node: str) -> None:
        if node in done:
            return
        if node in active:
            start = visiting.index(node)
            cycle = visiting[start:] + [node]
            if cycle not in cycles:
                cycles.append(cycle)
            return
        active.add(node)
        visiting.append(node)
        for dep in goals_by_id.get(node, {}).get("depends_on", []):
            if dep in goals_by_id:
                visit(dep)
        visiting.pop()
        active.remove(node)
        done.add(node)

    for goal_id in goals_by_id:
        visit(goal_id)
    return cycles


def validate_goal_file(path: Path, expected_agent: str | None = None) -> list[str]:
    errors: list[str] = []
    try:
        data = read_json(path)
    except (OSError, ValueError) as exc:
        return [f"{path}: {exc}"]
    if not isinstance(data, dict):
        return [f"{path}: root must be an object"]
    if data.get("schema_version") != "1.0":
        errors.append(f"{path}: schema_version should be '1.0'")
    if expected_agent is None and data.get("registry") == "shared":
        pass  # shared project registries are identified by "registry"/"scope", not agent_id
    elif not isinstance(data.get("agent_id"), str) or not data.get("agent_id"):
        errors.append(f"{path}: agent_id must be a non-empty string")
    elif expected_agent and data["agent_id"] != expected_agent:
        errors.append(f"{path}: agent_id is {data['agent_id']!r}, expected {expected_agent!r}")
    goals = data.get("goals")
    if not isinstance(goals, list):
        return errors + [f"{path}: goals must be an array"]
    by_id: dict[str, dict[str, Any]] = {}
    for index, goal in enumerate(goals):
        label = f"{path}: goals[{index}]"
        if not isinstance(goal, dict):
            errors.append(f"{label} must be an object")
            continue
        goal_id = goal.get("id")
        if not isinstance(goal_id, str) or not goal_id.strip():
            errors.append(f"{label}.id must be a non-empty string")
            continue
        if goal_id in by_id:
            errors.append(f"{label}: duplicate goal id {goal_id!r}")
        by_id[goal_id] = goal
        if not isinstance(goal.get("title"), str) or not goal["title"].strip():
            errors.append(f"{label} ({goal_id}): title must be a non-empty string")
        if goal.get("horizon") not in HORIZONS:
            errors.append(f"{label} ({goal_id}): invalid horizon {goal.get('horizon')!r}")
        if goal.get("status") not in STATUSES:
            errors.append(f"{label} ({goal_id}): invalid status {goal.get('status')!r}")
        for field in ("depends_on", "supports", "success_criteria", "contingent_on"):
            if field in goal and not isinstance(goal[field], list):
                errors.append(f"{label} ({goal_id}): {field} must be an array")
        for field in ("depends_on", "supports"):
            values = goal.get(field, [])
            if isinstance(values, list):
                for ref in values:
                    if not isinstance(ref, str):
                        errors.append(f"{label} ({goal_id}): {field} entries must be strings")
        if "priority" not in goal:
            errors.append(f"{label} ({goal_id}): missing explicit priority")
    for goal_id, goal in by_id.items():
        for field in ("depends_on", "supports"):
            for ref in goal.get(field, []) if isinstance(goal.get(field, []), list) else []:
                if isinstance(ref, str) and ref not in by_id:
                    errors.append(f"{path}: {goal_id}.{field} references missing goal {ref!r}")
    for cycle in goal_cycle_ids(by_id):
        errors.append(f"{path}: dependency cycle: {' -> '.join(cycle)}")
    return errors


def validate_jsonl(path: Path, required_fields: tuple[str, ...] = ()) -> list[str]:
    if not path.exists():
        return []
    try:
        records = read_jsonl(path)
    except (OSError, ValueError) as exc:
        return [str(exc)]
    errors = []
    for line_no, record in enumerate(records, 1):
        for field in required_fields:
            if field not in record:
                errors.append(f"{path}:{line_no}: missing required field {field!r}")
    return errors


def validate_repo(root: Path) -> list[str]:
    errors: list[str] = []
    agents_dir = root / "agents"
    if not agents_dir.is_dir():
        return [f"{agents_dir}: agents directory not found"]
    for agent_dir in sorted(p for p in agents_dir.iterdir() if p.is_dir()):
        goals_path = agent_dir / "goals" / "goals.json"
        if goals_path.exists():
            errors.extend(validate_goal_file(goals_path, agent_dir.name))
        for relative, required in (
            ("inbox/messages.jsonl", ("message_id", "recipient", "status")),
            ("history/events.jsonl", ("id", "timestamp", "type")),
            ("history/decisions.jsonl", ("id", "timestamp", "decision")),
        ):
            errors.extend(validate_jsonl(agent_dir / relative, required))
        collections_path = agent_dir / "collections" / "index.json"
        if collections_path.exists():
            try:
                data = read_json(collections_path)
                if not isinstance(data, dict) or not isinstance(data.get("collections"), list):
                    errors.append(f"{collections_path}: expected object with collections array")
            except (OSError, ValueError) as exc:
                errors.append(f"{collections_path}: {exc}")
    projects_dir = root / "projects"
    if projects_dir.is_dir():
        for shared_goals in sorted(projects_dir.glob("*/shared-goals.json")):
            errors.extend(validate_goal_file(shared_goals))
    shared_ledger = root / "shared" / "communications" / "log.jsonl"
    errors.extend(validate_jsonl(shared_ledger, ("timestamp", "sender", "target", "type", "content")))
    return errors


def canonical_hash(record: dict[str, Any], line_no: int) -> str:
    payload = json.dumps({"line": line_no, "record": record}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:20]


def route_messages(root: Path, dry_run: bool = False) -> tuple[int, int]:
    """Copy targeted ledger entries into inboxes; stable IDs make repeated runs safe."""
    ledger = root / "shared" / "communications" / "log.jsonl"
    if not ledger.exists():
        raise FileNotFoundError(f"shared ledger not found: {ledger}")
    agents_dir = root / "agents"
    agents = {p.name: p for p in agents_dir.iterdir() if p.is_dir()} if agents_dir.is_dir() else {}
    records = read_jsonl(ledger)
    existing: dict[str, set[str]] = {}
    for agent_id, agent_dir in agents.items():
        inbox = agent_dir / "inbox" / "messages.jsonl"
        known: set[str] = set()
        if inbox.exists():
            known = {str(r.get("message_id")) for r in read_jsonl(inbox)}
        existing[agent_id] = known

    additions: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for line_no, record in enumerate(records, 1):
        target = record.get("target", record.get("recipient", record.get("to")))
        if isinstance(target, list):
            recipients = [str(item) for item in target]
        elif target == "all" or target == "*":
            recipients = list(agents)
        elif isinstance(target, str) and target:
            recipients = [target]
        else:
            continue
        source_id = canonical_hash(record, line_no)
        for recipient in recipients:
            if recipient not in agents or source_id in existing.get(recipient, set()):
                continue
            routed = {
                "message_id": source_id,
                "recipient": recipient,
                "received_at": datetime.now(timezone.utc).isoformat(),
                "status": "unread",
                "sender_claim": record.get("sender"),
                "type": record.get("type", "message"),
                "content": record.get("content", ""),
                "source_ref": f"shared/communications/log.jsonl#L{line_no}",
                "source_timestamp": record.get("timestamp"),
                "linked_goal_ids": [],
                "linked_decision_ids": [],
                "authentication": "unverified-ledger-claim",
            }
            additions[recipient].append(routed)
            existing.setdefault(recipient, set()).add(source_id)

    total = sum(len(items) for items in additions.values())
    if not dry_run:
        for recipient, items in additions.items():
            inbox = agents[recipient] / "inbox" / "messages.jsonl"
            inbox.parent.mkdir(parents=True, exist_ok=True)
            with inbox.open("a", encoding="utf-8") as handle:
                for item in items:
                    handle.write(json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n")
    return total, len(additions)


def print_goal_graph(root: Path) -> int:
    agents_dir = root / "agents"
    if not agents_dir.is_dir():
        print(f"Error: {agents_dir} not found", file=sys.stderr)
        return 2
    for agent_dir in sorted(p for p in agents_dir.iterdir() if p.is_dir()):
        path = agent_dir / "goals" / "goals.json"
        if not path.exists():
            continue
        try:
            data = read_json(path)
        except (OSError, ValueError) as exc:
            print(f"{agent_dir.name}: cannot read goals: {exc}")
            continue
        print(f"\n{agent_dir.name}")
        goals = data.get("goals", []) if isinstance(data, dict) else []
        for goal in goals:
            if not isinstance(goal, dict):
                continue
            deps = ", ".join(goal.get("depends_on", [])) or "none"
            contingencies = goal.get("contingent_on", [])
            unsatisfied = [
                c.get("condition", str(c))
                for c in contingencies
                if isinstance(c, dict) and not c.get("satisfied", False)
            ]
            print(f"- [{goal.get('status', '?')}] {goal.get('id', '?')}: {goal.get('title', '(untitled)')}")
            print(f"  horizon={goal.get('horizon', '?')} priority={goal.get('priority', '?')} depends_on={deps}")
            if unsatisfied:
                print(f"  waiting_on: {'; '.join(unsatisfied)}")
            if goal.get("next_action"):
                print(f"  next: {goal['next_action']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Central repository root (default: current directory)")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate", help="validate goal registries, JSONL journals, and collections")
    route = sub.add_parser("route", help="route shared ledger messages into agent inboxes")
    route.add_argument("--dry-run", action="store_true", help="report routing without writing")
    sub.add_parser("goals", help="print goals and their prerequisite/contingency state")
    args = parser.parse_args(argv)
    root = args.root.resolve()

    if args.command == "validate":
        errors = validate_repo(root)
        if errors:
            print("\n".join(f"ERROR: {item}" for item in errors))
            print(f"Validation failed: {len(errors)} issue(s).")
            return 1
        print("Validation passed.")
        return 0
    if args.command == "route":
        try:
            count, inbox_count = route_messages(root, args.dry_run)
        except (OSError, ValueError) as exc:
            print(f"Routing failed: {exc}", file=sys.stderr)
            return 1
        verb = "Would route" if args.dry_run else "Routed"
        print(f"{verb} {count} message(s) into {inbox_count} inbox(es).")
        return 0
    if args.command == "goals":
        return print_goal_graph(root)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
