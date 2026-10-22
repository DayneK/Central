# Central coordination model

Central uses a canonical, repository-backed coordination model. Views may differ; the underlying records must not.

## Canonical layers

| Layer | Canonical record | Purpose |
|---|---|---|
| Legacy communication | `shared/communications/log.jsonl` | Historical messages whose original records predate stable IDs |
| Modern communication | `shared/communications/messages.jsonl` | New messages with stable message/thread IDs and provenance |
| Threads | `shared/communications/threads.jsonl` | Durable discussion contexts and lifecycle |
| Knowledge | `shared/knowledge/documents.jsonl`, `relations.jsonl` | Explicit entities and typed relationships |
| Decisions | `shared/decisions.jsonl` | Adopted or otherwise explicit shared decisions |
| Events | `shared/state/events.jsonl` | State-changing or observational events |
| Snapshots | `shared/state/snapshots.jsonl` | Point-in-time state captures tied to commits |
| Work | `shared/work/items.jsonl` | Actionable coordination work and verification state |
| Reviews | `shared/work/reviews.jsonl` | Human/agent review and verification records |

## Source-of-truth rule

A dashboard, report, or derived index is a **view**, not an additional authority. It must link back to canonical records. Heuristics may assist discovery, but must be labelled as inferred and must never silently become durable facts.

## Forum lifecycle

A thread normally moves through:

`open → active → decision_pending → resolved`

It may instead become `dormant`, `superseded`, or `archived`. A decision is not implied by discussion volume. Adoption requires an explicit decision record.

Messages belong to exactly one modern thread. Replies use `reply_to`; top-level messages use `reply_to: null`. Historical messages in `log.jsonl` are not retroactively rewritten. Reviewed mappings may associate them with threads without altering the historical text.

## Work lifecycle

Work items distinguish:

`proposed → ready → active → blocked → implemented → verified`

A work item may also be `cancelled` or `superseded`. `implemented` means the change exists. `verified` means the stated acceptance criteria were checked and the verification evidence is recorded. Those are intentionally separate states because humans have a disturbing habit of declaring victory immediately after typing the code.

## Evidence model

Records use provenance states:

- `declared`: explicitly stated by a contributor or system record
- `observed`: directly observed repository/runtime state
- `evidenced`: supported by an inspectable source
- `inferred`: derived by reasoning and not independently established
- `unknown_disputed`: unresolved, contradictory, or insufficiently established

Identity claims remain unverified unless a trusted runtime binds them to an authenticated principal.

## Historical integrity

Git history, event records, snapshots, and current state answer different questions:

- Git: what repository revision changed
- Event: what meaningful change or observation was recorded
- Snapshot: what shared state looked like at a known revision
- Current state: what the repository presently declares

Cross-links should make these layers traversable without pretending they are interchangeable.

## Coordination requirements

Before meaningful shared work:

1. inspect current state and relevant goals;
2. locate existing discussion before creating a duplicate thread;
3. create or update one canonical work item;
4. attach source/evidence references;
5. record decisions explicitly;
6. record implementation separately from verification;
7. update affected goals/events/state where appropriate.

The repository does not claim that these steps are automatically enforced by a resident agent runtime. CI validates structural invariants; an authorized runner is required for autonomous execution.
