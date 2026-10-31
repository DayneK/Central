#!/usr/bin/env python3
"""Summarise Central's coordination health from canonical records.

Standard-library only. The report is derived: it never writes repository data,
and it never treats an unverified implementation as a verified one.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

try:  # tests import this as scripts.coordination_health
    from scripts.semantic_validate import ISO_TIMESTAMP, jsonl, run as validate_semantic
except ModuleNotFoundError:  # direct execution: python3 scripts/coordination_health.py
    from semantic_validate import ISO_TIMESTAMP, jsonl, run as validate_semantic

UNRESOLVED_THREAD_STATUS = {"open", "active", "decision_pending"}
VERIFIED_REVIEW_RESULTS = {"pass", "approved", "verified"}
VERIFIED_VERIFICATION_STATUS = {"verified"}
STALE_WORK_STATUS = {"proposed", "ready", "active", "blocked"}


def load_jsonl(root: Path, relative: str) -> list[dict[str, Any]]:
    path = root / relative
    if not path.is_file():
        return []
    records = []
    try:
        for _, item in jsonl(path):
            records.append(item)
    except (OSError, ValueError, TypeError):
        return records  # semantic_validate reports the malformed remainder
    return records


def parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not ISO_TIMESTAMP.fullmatch(value):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def build_report(
    root: Path,
    *,
    now: datetime | None = None,
    max_age_days: int = 30,
    stale_days: int = 14,
) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    work = load_jsonl(root, "shared/work/items.jsonl")
    reviews = load_jsonl(root, "shared/work/reviews.jsonl")
    threads = load_jsonl(root, "shared/communications/threads.jsonl")
    messages = load_jsonl(root, "shared/communications/messages.jsonl")
    decisions = load_jsonl(root, "shared/decisions.jsonl")
    events = load_jsonl(root, "shared/state/events.jsonl")
    snapshots = load_jsonl(root, "shared/state/snapshots.jsonl")
    documents = load_jsonl(root, "shared/knowledge/documents.jsonl")
    relations = load_jsonl(root, "shared/knowledge/relations.jsonl")

    review_results_by_work: dict[str, set[str]] = {}
    for review in reviews:
        work_id = review.get("work_id")
        if isinstance(work_id, str):
            review_results_by_work.setdefault(work_id, set()).add(str(review.get("result")))

    awaiting_verification = []
    verified_without_review = []
    stale_work = []
    for item in work:
        work_id = item.get("id")
        status = item.get("status")
        verification = item.get("verification")
        verification_status = verification.get("status") if isinstance(verification, dict) else None
        if status == "implemented" and verification_status not in VERIFIED_VERIFICATION_STATUS:
            awaiting_verification.append(
                {
                    "id": work_id,
                    "title": item.get("title"),
                    "owner": item.get("owner"),
                    "verification_status": verification_status,
                }
            )
        if status == "verified" and isinstance(work_id, str):
            if not (review_results_by_work.get(work_id, set()) & VERIFIED_REVIEW_RESULTS):
                verified_without_review.append({"id": work_id, "title": item.get("title"), "owner": item.get("owner")})
        if status in STALE_WORK_STATUS:
            updated = parse_timestamp(item.get("updated_at"))
            if updated is not None:
                idle_days = (now - updated).days
                if idle_days > stale_days:
                    stale_work.append(
                        {
                            "id": work_id,
                            "title": item.get("title"),
                            "status": status,
                            "owner": item.get("owner"),
                            "updated_at": item.get("updated_at"),
                            "idle_days": idle_days,
                        }
                    )
    stale_work.sort(key=lambda item: item["idle_days"], reverse=True)

    unresolved = [t for t in threads if t.get("status") in UNRESOLVED_THREAD_STATUS]
    aging = []
    for thread in unresolved:
        created = parse_timestamp(thread.get("created_at"))
        if created is None:
            continue
        age = now - created
        if age > timedelta(days=max_age_days):
            aging.append(
                {
                    "thread_id": thread.get("thread_id"),
                    "title": thread.get("title"),
                    "status": thread.get("status"),
                    "created_at": thread.get("created_at"),
                    "age_days": age.days,
                }
            )
    aging.sort(key=lambda item: item["age_days"], reverse=True)
    empty_threads = [
        t.get("thread_id") for t in threads if isinstance(t.get("message_ids"), list) and not t["message_ids"]
    ]
    decisions_without_work = [
        d.get("id") for d in decisions if not isinstance(d.get("related_work_ids"), list) or not d["related_work_ids"]
    ]

    activity_times = [
        parse_timestamp(record.get("timestamp"))
        for record in [*messages, *events, *decisions, *reviews, *snapshots]
    ]
    activity_times = [value for value in activity_times if value is not None]
    latest_activity = max(activity_times).isoformat().replace("+00:00", "Z") if activity_times else None

    validation_errors = validate_semantic(root)
    actions = []
    if validation_errors:
        actions.append(f"Fix {len(validation_errors)} semantic validation error(s) before relying on this report.")
    if awaiting_verification:
        actions.append(
            f"Verify or explicitly defer {len(awaiting_verification)} implemented work item(s) "
            "with pending verification."
        )
    if verified_without_review:
        actions.append(f"Record review evidence for {len(verified_without_review)} verified work item(s).")
    if aging:
        actions.append(f"Review {len(aging)} unresolved thread(s) older than {max_age_days} days.")
    if stale_work:
        actions.append(f"Update or close {len(stale_work)} work item(s) idle for more than {stale_days} days.")
    if decisions_without_work:
        actions.append(f"Link {len(decisions_without_work)} decision(s) to related work items.")

    if validation_errors:
        status = "invalid"
    elif awaiting_verification or verified_without_review or aging or stale_work or decisions_without_work:
        status = "attention"
    else:
        status = "healthy"

    return {
        "as_of": now.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": status,
        "totals": {
            "documents": len(documents),
            "relations": len(relations),
            "threads": len(threads),
            "messages": len(messages),
            "work_items": len(work),
            "reviews": len(reviews),
            "decisions": len(decisions),
            "events": len(events),
            "snapshots": len(snapshots),
        },
        "work": {
            "by_status": dict(sorted(Counter(str(item.get("status")) for item in work).items())),
            "awaiting_verification": awaiting_verification,
            "verified_without_review": verified_without_review,
            "stale": stale_work,
            "stale_days": stale_days,
        },
        "threads": {
            "by_status": dict(sorted(Counter(str(item.get("status")) for item in threads).items())),
            "unresolved": len(unresolved),
            "aging": aging,
            "without_messages": empty_threads,
            "max_age_days": max_age_days,
        },
        "decisions": {
            "total": len(decisions),
            "without_related_work": decisions_without_work,
        },
        "activity": {
            "latest": latest_activity,
            "messages": len(messages),
            "events": len(events),
            "snapshots": len(snapshots),
        },
        "validation": {"errors": validation_errors},
        "actions": actions,
    }


def render_markdown(report: dict[str, Any]) -> str:
    totals = report["totals"]
    lines = [
        "## Central coordination health",
        "",
        f"**Status:** `{report['status']}` · as of `{report['as_of']}` · "
        f"{totals['threads']} threads, {totals['messages']} messages, {totals['work_items']} work items",
        "",
        "| Records | Count |",
        "| --- | ---: |",
    ]
    for key in ("documents", "relations", "threads", "messages", "work_items", "reviews", "decisions", "events", "snapshots"):
        lines.append(f"| {key.replace('_', ' ')} | {totals[key]} |")

    lines += ["", "### Work verification", ""]
    work = report["work"]
    lines.append(f"- Awaiting verification: **{len(work['awaiting_verification'])}**")
    for item in work["awaiting_verification"]:
        lines.append(f"  - `{item['id']}` — {item['title']} (owner: {item['owner']})")
    lines.append(f"- Verified without recorded review: **{len(work['verified_without_review'])}**")
    for item in work["verified_without_review"]:
        lines.append(f"  - `{item['id']}` — {item['title']}")
    lines.append(f"- Stale work (idle > {work['stale_days']} days): **{len(work['stale'])}**")
    for item in work["stale"]:
        lines.append(f"  - `{item['id']}` — {item['title']} ({item['idle_days']} days, {item['status']})")

    threads = report["threads"]
    lines += ["", "### Discussion state", ""]
    lines.append(
        f"- Unresolved threads: **{threads['unresolved']}**; older than {threads['max_age_days']} days: "
        f"**{len(threads['aging'])}**"
    )
    for item in threads["aging"]:
        lines.append(f"  - `{item['thread_id']}` — {item['title']} ({item['age_days']} days)")
    lines.append(f"- Threads without messages: **{len(threads['without_messages'])}**")

    lines += ["", "### Validation", ""]
    if report["validation"]["errors"]:
        lines.append(f"- Semantic validation errors: **{len(report['validation']['errors'])}**")
        for error in report["validation"]["errors"][:10]:
            lines.append(f"  - `{error}`")
    else:
        lines.append("- Semantic validation errors: **0**")

    lines += ["", "### Actions", ""]
    if report["actions"]:
        lines.extend(f"- {action}" for action in report["actions"])
    else:
        lines.append("- None.")
    return "\n".join(lines)


def render_text(report: dict[str, Any]) -> str:
    totals = report["totals"]
    lines = [
        f"Central coordination health: {report['status']} (as of {report['as_of']})",
        f"  threads={totals['threads']} messages={totals['messages']} work={totals['work_items']} "
        f"reviews={totals['reviews']} decisions={totals['decisions']} events={totals['events']}",
        f"  awaiting verification={len(report['work']['awaiting_verification'])} "
        f"verified without review={len(report['work']['verified_without_review'])} "
        f"stale={len(report['work']['stale'])}",
        f"  unresolved threads={report['threads']['unresolved']} "
        f"older than {report['threads']['max_age_days']}d={len(report['threads']['aging'])}",
        f"  validation errors={len(report['validation']['errors'])}",
    ]
    lines.extend(f"  - {action}" for action in report["actions"])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Central repository root (default: current directory)")
    parser.add_argument("--format", choices=("text", "markdown", "json"), default="text")
    parser.add_argument("--max-age-days", type=int, default=30, help="age at which an unresolved thread is reported")
    parser.add_argument("--stale-days", type=int, default=14, help="idle age at which open work is reported stale")
    parser.add_argument("--now", help="override the current UTC time (ISO-8601) for reproducible reports")
    parser.add_argument("--strict", action="store_true", help="exit non-zero when semantic validation fails")
    args = parser.parse_args(argv)

    now = None
    if args.now:
        now = parse_timestamp(args.now)
        if now is None:
            parser.error("--now must be a UTC ISO-8601 timestamp such as 2026-01-01T00:00:00Z")

    report = build_report(
        args.root.resolve(),
        now=now,
        max_age_days=args.max_age_days,
        stale_days=args.stale_days,
    )
    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    elif args.format == "markdown":
        print(render_markdown(report))
    else:
        print(render_text(report))

    if args.strict and report["validation"]["errors"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
