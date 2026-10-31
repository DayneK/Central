# Communication migrations

This directory preserves the provenance of communication records that predate the modern message and thread model. Nothing here rewrites historical content.

## `forum-seed-20261022.jsonl`

The original forum seed. It is archived as migration evidence and is explicitly **not canonical**. Modern messages live in `shared/communications/messages.jsonl`; `shared/communications/forum.jsonl` is only a compatibility pointer.

## `legacy-thread-map.jsonl`

A reviewed mapping from seed threads (`TH-001`–`TH-005`) to entries in the legacy ledger `shared/communications/log.jsonl`.

- The ledger has no stable message IDs, so mappings use zero-based `legacy_index` values and repeat the original timestamp and sender.
- A mapping is evidence that a legacy record belongs to a thread context. It is **not** a modern message, does not invent an ID, and does not alter ledger text.
- `mapped_thread_ids` remain empty on purpose. The dashboard labels these threads as legacy-backed rather than pretending they contain modern messages.
- Validation enforces that every empty thread has either reviewed legacy evidence or an explicit `seed_only` rationale with existing evidence paths.
- `reviewed_by` records who proposed the mapping; it is a claim, not an authenticated identity.

Mappings should be added or corrected through review, with a specific `mapping_basis`. Bulk topic matching is not sufficient.

## Schema

| Field | Meaning |
|---|---|
| `id` | Stable mapping ID (`LTM-###`) |
| `thread_id` | Seed thread receiving the evidence |
| `legacy_index` | Zero-based line index in `log.jsonl` |
| `legacy_timestamp` | Original ledger timestamp, checked for equality |
| `legacy_sender` | Original ledger sender, checked for equality |
| `mapping_basis` | Human-readable reason the record belongs to the thread |
| `reviewed_by` | Contributor who reviewed the mapping |
| `reviewed_at` | UTC timestamp of review |
