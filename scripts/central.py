#!/usr/bin/env python3
"""Unified command line for Central's file-backed coordination tooling.

Standard-library only. Commands read repository records and reports; routing is
the only operation that writes, and only to per-agent inboxes.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:  # tests import this as scripts.central
    from scripts import agent_workspace, coordination_health, security_audit, semantic_validate
except ModuleNotFoundError:  # direct execution: python3 scripts/central.py
    import agent_workspace
    import coordination_health
    import security_audit
    import semantic_validate


def run_check(root: Path, *, check_git: bool = False) -> int:
    """Run independent validation stages and report every failure."""
    stages: list[tuple[str, list[str]]] = []

    try:
        stages.append(("workspace", agent_workspace.validate_repo(root)))
    except (OSError, ValueError, TypeError) as exc:
        stages.append(("workspace", [str(exc)]))

    try:
        stages.append(("semantic", semantic_validate.run(root, check_git=check_git)))
    except (OSError, ValueError, TypeError) as exc:
        stages.append(("semantic", [str(exc)]))

    try:
        findings = security_audit.scan(root)
        stages.append(("security", [f"{path}:{line}: possible {message} hazard" for path, line, message in findings]))
    except (OSError, ValueError) as exc:
        stages.append(("security", [str(exc)]))

    failed = 0
    for name, errors in stages:
        if errors:
            failed += len(errors)
            print(f"== {name}: {len(errors)} issue(s) ==")
            for error in errors:
                print(f"ERROR: {error}")
        else:
            print(f"== {name}: ok ==")

    if failed:
        print(f"Central check failed: {failed} issue(s).")
        return 1
    print("Central check passed.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Central repository root")
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check", help="run workspace, semantic, and security validation")
    check.add_argument("--check-git", action="store_true", help="verify snapshot commits in Git history")

    semantic = sub.add_parser("semantic", help="validate the semantic substrate")
    semantic.add_argument("--check-git", action="store_true", help="verify snapshot commits in Git history")

    sub.add_parser("workspace", help="validate agent workspaces and goal registries")
    sub.add_parser("security", help="scan tracked text for configured static hazards")
    sub.add_parser("goals", help="print goal dependencies and contingencies")

    route = sub.add_parser("route", help="route shared ledger messages into agent inboxes")
    route.add_argument("--dry-run", action="store_true", help="report routing without writing")

    health = sub.add_parser("health", help="derived operational health report")
    health.add_argument("--format", choices=("text", "markdown", "json"), default="text")
    health.add_argument("--max-age-days", type=int, default=30)
    health.add_argument("--stale-days", type=int, default=14)
    health.add_argument("--now", help="override report time (UTC ISO-8601)")
    health.add_argument("--fail-on", choices=("none", "attention", "invalid"), default="none")
    health.add_argument("--strict", action="store_true", help="alias for --fail-on invalid")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = args.root.resolve()

    if args.command == "check":
        return run_check(root, check_git=args.check_git)
    if args.command == "semantic":
        return semantic_validate.main(["--root", str(root)] + (["--check-git"] if args.check_git else []))
    if args.command == "workspace":
        return agent_workspace.main(["--root", str(root), "validate"])
    if args.command == "security":
        findings = security_audit.scan(root)
        if findings:
            for path, line, message in findings:
                print(f"ERROR: {path}:{line}: {message}")
            print(f"Security audit failed: {len(findings)} finding(s).")
            return 1
        print("Security audit passed: no configured static hazards detected.")
        return 0
    if args.command == "goals":
        return agent_workspace.main(["--root", str(root), "goals"])
    if args.command == "route":
        route_args = ["--root", str(root), "route"]
        if args.dry_run:
            route_args.append("--dry-run")
        return agent_workspace.main(route_args)
    if args.command == "health":
        health_args = [
            "--root",
            str(root),
            "--format",
            args.format,
            "--max-age-days",
            str(args.max_age_days),
            "--stale-days",
            str(args.stale_days),
            "--fail-on",
            args.fail_on,
        ]
        if args.now:
            health_args += ["--now", args.now]
        if args.strict:
            health_args.append("--strict")
        return coordination_health.main(health_args)
    parser.error(f"unknown command {args.command!r}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
