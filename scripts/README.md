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
