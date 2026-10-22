#!/usr/bin/env python3
"""Static hygiene checks for the Central repository.

This is not a security scanner and cannot prove authentication, authorization,
or absence of secrets. It catches common accidental repository hazards.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT_EXTENSIONS = {".md", ".json", ".jsonl", ".txt", ".yaml", ".yml", ".py", ".js", ".html", ".css", ".sh", ".toml"}
CODE_EXTENSIONS = {".py", ".js", ".sh"}
SKIP = {".git", "node_modules"}
PATTERNS = {
    "private-key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    "bearer-token": re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]{20,}"),
    "credential-assignment": re.compile(r"(?i)\b(?:api[_-]?key|access[_-]?token|refresh[_-]?token|client[_-]?secret|password)\s*[:=]\s*[\"'][^\"']{8,}[\"']"),
    "sender-authorizes": re.compile(r"(?i)\b(?:if|unless|when)\b[^\n]{0,100}\b(?:sender|agent_id)\b[^\n]{0,100}\b(?:authorize|permission|allow|admin|write)\b"),
}

ALLOW = {"SECURITY.md", "scripts/security_audit.py"}


def files():
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        if any(part in SKIP for part in path.parts):
            continue
        yield path


def main() -> int:
    findings = []
    for path in files():
        rel = path.relative_to(ROOT).as_posix()
        if rel in ALLOW:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for line_no, line in enumerate(text.splitlines(), 1):
            for name, pattern in PATTERNS.items():
                if name == "sender-authorizes" and path.suffix.lower() not in CODE_EXTENSIONS:
                    continue
                if pattern.search(line):
                    findings.append((rel, line_no, name))
    if findings:
        for rel, line, name in findings:
            print(f"ERROR: {rel}:{line}: possible {name} hazard")
        print(f"Security audit found {len(findings)} possible hazard(s). Review manually before merging.")
        return 1
    print("Security audit passed: no configured static hazards detected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
