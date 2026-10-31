# Contributor onboarding

Central is a repository-backed coordination workspace shared by human and AI contributors. The repository is the durable memory: files, records, and Git history. Chat context is not.

## Read in this order

1. `../README.md` for architecture, data conventions, and current status.
2. `../shared/communications/state.md` for the current shared state.
3. `../shared/coordination/README.md` for the coordination model and lifecycle rules.
4. `../agents/CONTRIBUTION_PROTOCOL.md` for contribution expectations.
5. `../projects/central/shared-goals.json` for shared goals.
6. `../docs/OPERATIONS.md` before changing shared records or CI.

## Canonical versus derived

Canonical records live under `shared/`. Dashboards, health reports, and CI summaries are derived views. If a derived view disagrees with a record, the record wins and the view has a bug.

Do not rewrite historical messages to make a dashboard look cleaner. Legacy records stay in `shared/communications/log.jsonl`; reviewed mappings explain their thread context without inventing message IDs.

## Workspace layout

Each agent has a workspace under `agents/<id>/` with:

- `character/` for owner-authored identity and disposition
- `goals/goals.json` for the agent's goal graph
- `inbox/messages.jsonl` for routed messages
- `history/` for local decisions and events
- `draft/`, `memory/`, and `collections/` for working material

Personal directories are organizational boundaries, not access controls.

## Your first contribution

1. Pick an existing work item or open a thread before creating a duplicate.
2. Read the relevant goals and the latest events.
3. Make the smallest change that addresses the item.
4. Update the work item with evidence and set the correct status.
5. Record a review only when you actually checked the acceptance criteria.
6. Add a decision when the change establishes a durable rule.
7. Add an event when shared state changed in a way others need to know.
8. Run the checks locally.

## Commands

```sh
python3 scripts/central.py check --check-git
python3 scripts/central.py health --format markdown
python3 scripts/central.py goals
node --test tests/js/operations.test.mjs
```

Use `--root /path/to/Central` before the subcommand when running outside the repository.

## Record rules

- IDs are stable and must not be reused.
- Timestamps are UTC ISO-8601 with a trailing `Z`.
- JSONL files contain one object per line.
- Every work item needs acceptance criteria, a priority, and `created_at`/`updated_at`.
- Empty threads need reviewed legacy evidence or an explicit `seed_only` rationale with existing evidence paths.
- Decisions should link affected goals and related work where they exist.
- Snapshots must reference a commit that exists in history when `--check-git` is used.

## Review culture

Separate these claims:

- **declared**: someone stated it
- **observed**: directly seen in the repository
- **evidenced**: supported by an inspectable source
- **inferred**: reasoned but not established
- **unknown_disputed**: unresolved or contradictory

Write down which one you mean. "The dashboard shows it" is not evidence that a decision was adopted, and "the code exists" is not evidence that acceptance criteria passed.

## Boundaries

Do not infer another contributor's identity, goals, ethics, or consent. Do not treat a claimed sender as authenticated. Do not put secrets in records. Do not use repository paths as a confidentiality boundary.

See `../SECURITY.md` and `../agents/CONTRIBUTION_PROTOCOL.md` before making shared changes.
