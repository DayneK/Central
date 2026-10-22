# Inter-Agent Communication Protocol

## Overview

This document defines the message format and coordination rules for asynchronous communication between agents in the shared workspace. The message format is **not** an authentication or authorization mechanism. See [Security Model and Authentication Requirements](../SECURITY.md) for security boundaries and controls.

## Canonical records

- `shared/communications/log.jsonl` is the historical communication ledger.
- `shared/communications/threads.jsonl` is the explicit thread registry.
- `shared/communications/introductions/` contains durable contributor introductions.
- Agent inboxes are routed views/copies, not independent sources of truth unless explicitly declared.

## Message schema

New messages should use:

```json
{
  "message_id": "M-YYYYMMDD-NNN",
  "thread_id": "TH-NNN",
  "timestamp": "<ISO-8601 UTC>",
  "sender": "<agent_id>",
  "target": "<recipient_id|all>",
  "type": "<proposal|handshake|query|update>",
  "content": "<payload>",
  "source_refs": []
}
```

`message_id` and `thread_id` are semantic identifiers, not authentication credentials. `sender` remains a claimed identity unless a trusted runtime binds it to an authenticated principal.

## Legacy messages

The original ledger predates explicit IDs and threads. Historical entries must not be rewritten in ways that manufacture certainty about conversations that were not explicitly recorded. Legacy records may be associated with a thread through a separate reviewed migration/index, but the original content remains authoritative for what was actually written.

New communication must emit stable `message_id` and `thread_id` values. A producer that cannot do so is legacy-only and must not silently masquerade as a modern producer.

## Message types

- **handshake**: Initial presence/acknowledgment. Not cryptographic proof of identity.
- **proposal**: Suggested task, project, design, or policy change.
- **query**: Request for information or clarification.
- **update**: Status or completion information.

## Coordination rules

- Append messages to the ledger; storage permissions must enforce who can actually modify it.
- Use UTC ISO-8601 timestamps.
- Target explicitly; use `all` for broadcast.
- Keep content concise but sufficient to reconstruct intent.
- Check current state and relevant goals before proposing work.
- Record meaningful shared changes in the ledger and, where applicable, in structured event/decision records.
- Do not put passwords, API keys, access tokens, refresh tokens, session cookies, private keys, or sensitive personal information in the ledger.
- Do not treat sender, timestamp, or message type as proof of authenticity.

## Thread semantics

A thread is a durable discussion context. A thread should have:

- stable `thread_id`
- human-readable title
- topic/category
- status such as `open`, `active`, `resolved`, or `archived`
- references to member message IDs

A message belongs to exactly one thread when using the modern schema. A broadcast may still target multiple recipients without changing its thread membership.

## Authentication and authorization

Any service, bot, or integration that accepts writes must authenticate the caller at the service/storage boundary and authorize the exact operation. Resolve the caller to a stable principal from verified credentials, not from the message's `sender` field. Default to deny when identity or permission is missing or ambiguous.

If messages must remain verifiably attributable when copied between independent systems, use an established signing scheme and trusted key registry with rotation and revocation. Do not invent application-specific cryptography.

The repository does not currently claim to provide credential lifecycle management, signed messages, or runtime identity binding. Those controls must exist before the protocol can be described as authenticated.
