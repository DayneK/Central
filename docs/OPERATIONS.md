# Operations runbook

This runbook covers the routine maintenance of Central's file-backed coordination substrate. It describes repository operations, not hosted runtime services. Central does not run an always-on agent, queue, or authentication service from this repository.

## Source of truth

Canonical records live in Git:

| Layer | Canonical file |
|---|---|
| Modern discussion | `shared/communications/messages.jsonl` |
| Threads | `shared/communications/threads.jsonl` |
| Legacy ledger | `shared/communications/log.jsonl` |
| Legacy mappings | `shared/communications/migrations/legacy-thread-map.jsonl` |
| Decisions | `shared/decisions.jsonl` |
| Work | `shared/work/items.jsonl` |
| Reviews | `shared/work/reviews.jsonl` |
| Events | `shared/state/events.jsonl` |
| Snapshots | `shared/state/snapshots.jsonl` |
| Knowledge | `shared/knowledge/documents.jsonl`, `relations.jsonl` |

The dashboard, health report, and CI summary are derived views. They must not be treated as additional authorities. Git history records revisions; events record meaningful observations; snapshots bind state to a commit.

## Routine checks

Run from the repository root:

```sh
python3 scripts/central.py check --check-git
python3 scripts/central.py health --format markdown
node --test tests/js/operations.test.mjs
```

`check` runs workspace, semantic, security, and documentation validation independently. `--check-git` resolves every snapshot `source_commit` against Git history and therefore requires a full clone.

## Cadence

| Cadence | Action |
|---|---|
| Before shared work | Read `shared/communications/state.md`, relevant goals, and open threads |
| On every meaningful change | Update the work item, add evidence, and record an event if the shared state changed |
| Weekly | Review the health report, especially verification backlog and aging threads |
| Weekly (automated) | GitHub Actions runs the same validation without path filters and publishes the health summary |
| At phase boundaries | Record a decision, event, and snapshot; update `state.md` |

The weekly schedule is a reminder and a check, not an autonomous agent. A human or an authorized runner still has to act on the report.

## Reading health output

- `healthy`: no tracked queue is waiting.
- `attention`: verification, stale work, aging threads, linkage, or evidence work is outstanding.
- `invalid`: semantic validation failed; fix this before trusting the rest of the report.

`--fail-on invalid` is the default CI gate. Manual dispatch can raise the threshold to `attention`, but a permanent attention backlog should not be turned into a permanently red workflow.

## Verification workflow

Implementation and verification are separate states:

1. Move the work item to `implemented` only when the change exists.
2. Add or update `verification.evidence_refs` with inspectable paths.
3. Record a review with `criteria_checked` and evidence.
4. Move the item to `verified` only after the acceptance criteria were actually checked.

A green implementation status is not verification. Dashboard or CI output cannot promote work on its own.

## Dashboard

The forum at `dashboard/forum.html` renders threads, messages, decisions, work, history, and a derived operations view. It fetches canonical JSONL from the repository's raw GitHub URL and performs no writes. The operations summary is implemented in `dashboard/operations.js` and mirrors `scripts/coordination_health.py`; both are derived and can disagree only if one is stale or buggy.

The Pages deployment workflow validates inline JavaScript syntax and runs the Node operations tests before publishing.

## Failure handling

| Symptom | First check |
|---|---|
| `invalid` health | Run `python3 scripts/semantic_validate.py --check-git` and fix every reported path |
| Snapshot commit missing | Fetch full history; the CI checkout uses `fetch-depth: 0` |
| Empty thread rejected | Add reviewed legacy evidence or a `seed_only` rationale with existing evidence paths |
| Health artifact missing | Inspect the workspace-checks run; artifact upload happens before the gate |
| Forum blank | Check the browser console, then `node --check dashboard/operations.js` and the deploy workflow |
| Dashboard data stale | GitHub raw content can lag; verify the canonical file on `main` and refresh |

## Security boundaries

- Identity in records is a claim unless a trusted runtime binds it to credentials.
- Repository write access is the only real permission boundary; directory names do not provide confidentiality.
- Do not store secrets in records, dashboards, or workflow files.
- The security audit is a static hygiene check, not a guarantee.
- Routing writes only to agent inboxes and preserves the original sender as an unverified claim.

See `../SECURITY.md` for the full boundary statement.
