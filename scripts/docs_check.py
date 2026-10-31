#!/usr/bin/env python3
"""Check local documentation links and required guides.

Standard-library only. External URLs are not fetched; this checks repository
paths, which is where documentation rot usually starts.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path
from urllib.parse import unquote

REQUIRED_DOCS = (
    "README.md",
    "CHANGELOG.md",
    "SECURITY.md",
    "docs/OPERATIONS.md",
    "docs/ONBOARDING.md",
    "scripts/README.md",
    "dashboard/README.md",
    "shared/coordination/README.md",
    "agents/CONTRIBUTION_PROTOCOL.md",
)
SKIP_PARTS = {".git", "node_modules", "__pycache__", ".vly-run", ".venv", "dist"}
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
EXTERNAL_PREFIXES = ("http://", "https://", "mailto:", "tel:", "#")


def markdown_files(root: Path):
    for path in sorted(root.rglob("*.md")):
        if any(part in SKIP_PARTS for part in path.parts):
            continue
        yield path


def local_links(path: Path) -> list[tuple[int, str]]:
    """Yield (line number, target) for Markdown links outside code fences."""
    links = []
    in_fence = False
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for match in LINK.finditer(line):
            target = match.group(1).strip()
            if target.startswith(EXTERNAL_PREFIXES):
                continue
            links.append((line_no, target))
    return links


def check_docs(root: Path) -> list[str]:
    errors = []
    for relative in REQUIRED_DOCS:
        if not (root / relative).is_file():
            errors.append(f"missing required document: {relative}")

    for path in markdown_files(root):
        relative = path.relative_to(root).as_posix()
        for line_no, target in local_links(path):
            cleaned = unquote(target.split("#", 1)[0].split("?", 1)[0])
            if not cleaned:
                continue
            candidate = Path(cleaned)
            resolved = candidate if candidate.is_absolute() else path.parent / candidate
            if not resolved.exists():
                errors.append(f"{relative}:{line_no}: local link target does not exist: {target}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Central repository root")
    args = parser.parse_args(argv)
    errors = check_docs(args.root.resolve())
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print(f"Documentation check failed: {len(errors)} issue(s).")
        return 1
    print("Documentation check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
