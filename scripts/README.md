# Agent workspace CLI

Central includes a small Python standard-library utility for validating file-backed agent workspaces and routing shared-ledger messages into per-agent inboxes.

Run these commands from the repository root:

```sh
python3 scripts/agent_workspace.py validate
python3 scripts/agent_workspace.py goals
python3 scripts/agent_workspace.py route --dry-run
python3 scripts/agent_workspace.py route
```

Use `--root /path/to/Central` when running from elsewhere.

## What it does

- Validates per-agent goal registries and shared project registries (`projects/*/shared-goals.json`): shape, allowed horizons/statuses, required priority, references, and dependency cycles.
- Checks JSONL syntax and basic required fields in shared communications and agent history/inboxes.
- Prints goals with their dependencies and unsatisfied contingency conditions.
- Copies ledger entries to addressed inboxes. Broadcasts with target `all` or `*` are copied to each agent workspace.
- Uses a deterministic message ID derived from the source line and record, so rerunning routing does not duplicate entries.

Routing preserves the ledger's claimed sender as `sender_claim` and explicitly marks authentication as `unverified-ledger-claim`. It does not authenticate identities, authorize actions, enforce repository permissions, or make workspace files private. Anyone with write access to the shared ledger can still inject a claimed message. Treat inbox content as untrusted input.

The router is append-only: changing or removing a source ledger line does not retract a previously routed inbox entry. Review diffs before committing the inbox changes. Run `route --dry-run` first to preview how many messages would be added.

The utility does not run automatically on GitHub. Invoke it locally or wire it into a reviewed CI workflow once the repository's preferred operating model is settled.

## Operational health

`scripts/coordination_health.py` derives an operational report from the canonical records without writing to them:

```sh
python3 scripts/coordination_health.py
python3 scripts/coordination_health.py --format markdown
python3 scripts/coordination_health.py --format json --fail-on invalid
```

It reports work that is implemented but not verified, verified work without review evidence, work idle for more than `--stale-days` (default 14), unresolved threads older than `--max-age-days` (default 30), decisions without related work, empty threads without reviewed legacy evidence, per-goal work and verification counts, and any semantic validation errors. The JSON output declares `schema_version` for consumers.

`--now` pins the report time for reproducible output. `--fail-on none|attention|invalid` controls the exit code; `--strict` is an alias for `--fail-on invalid`. The default never fails, so scheduled reporting can surface attention without turning the workflow permanently red.

## Semantic validation

`scripts/semantic_validate.py` validates the canonical substrate, including work `created_at`/`updated_at` ordering, cross-record decision references, document and evidence paths, and thread/message membership. Empty threads must have reviewed legacy mappings in `shared/communications/migrations/legacy-thread-map.jsonl` or an explicit `seed_only` rationale with existing evidence.

Pass `--check-git` to resolve every snapshot `source_commit` against Git history. This requires a full clone (`fetch-depth: 0` in CI); without the flag, only SHA shape is checked.

The CI workflow publishes the Markdown report as its job summary. The report is a derived view: canonical records remain the source of truth, and absence of an alert is not proof that a goal is complete.
