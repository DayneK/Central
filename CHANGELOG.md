# Changelog

## 2026-10-31 — Coordination escalation

Nine units across three phases, each closing an operational gap rather than adding a parallel system.

### Phase 1 — Integrity

1. **Temporal work model.** Work items now require `created_at` and `updated_at`; health derives stale work from idle time.
2. **Legacy thread evidence.** Message-less seed threads map to reviewed ledger entries in `shared/communications/migrations/legacy-thread-map.jsonl`; validation rejects unexplained empty threads.
3. **Git-backed snapshots.** `semantic_validate.py --check-git` resolves snapshot commits against history; CI checks out full history and runs it.

### Phase 2 — Operations

4. **Tested dashboard operations.** Derived summaries moved to `dashboard/operations.js` with nine Node tests covering verification, staleness, aging, legacy evidence and reference integrity.
5. **Goal-level health.** Reports aggregate work by shared goal, declare `schema_version: 2`, and expose `--fail-on none|attention|invalid`.
6. **CI artifacts and gates.** Health JSON is uploaded for 90 days, the default gate fails only on invalid data, and manual dispatch can raise it to attention.

### Phase 3 — Platform experience

7. **Unified CLI.** `scripts/central.py` dispatches `check`, `semantic`, `workspace`, `security`, `docs`, `health`, `goals`, and `route` with explicit exit codes.
8. **Documentation integrity.** `scripts/docs_check.py` validates required guides and local Markdown links; `docs/OPERATIONS.md` and `docs/ONBOARDING.md` cover operation and contribution.
9. **Integration and version matrix.** End-to-end CLI tests run against temporary and live workspaces, and the Python suite runs on 3.10, 3.11, and 3.12.

### Verification

```sh
python3 scripts/central.py check --check-git
python3 -m unittest discover -s tests -p "test*.py"
node --test tests/js/operations.test.mjs
```

### Notes

- Implementation remains separate from verification. Work completed in these phases is `implemented` with pending verification unless a recorded review says otherwise.
- The health report intentionally reports a verification backlog as `attention`; the default gate fails only on `invalid` so real structural failures stay actionable.
- No new runtime, database, or authentication layer was introduced. The repository remains file-backed and standard-library Python.
