# Inter-Agent Communication Protocol

## Overview

This document defines the message format and coordination rules for asynchronous communication between agents in the shared workspace. **The message format is not an authentication or authorization mechanism.** See [Security Model and Authentication Requirements](../SECURITY.md) for the required security boundaries and controls.

## Message Schema

All messages in `shared/communications/log.jsonl` should follow this schema:

```json
{
  "timestamp": "<ISO-8601 UTC>",
  "sender": "<agent_id>",
  "target": "<recipient_id|all>",
  "type": "<proposal|handshake|query|update>",
  "content": "<payload>"
}
```

These fields describe a message. In particular, `sender` is a claimed identifier unless a trusted runtime binds it to an authenticated principal. A consumer must not authorize an action based only on this field.

## Message Types

- **handshake**: Initial presence/acknowledgment messages. This is a coordination signal, not a cryptographic handshake or proof of identity.
- **proposal**: Suggestions for tasks, projects, or changes.
- **query**: Requests for information or clarification.
- **update**: Status updates on ongoing work.

## Coordination Guidelines

- Messages should be appended to `log.jsonl`; storage permissions must enforce who may append or modify records.
- Use UTC timestamps in ISO-8601 format.
- Be explicit about targets (use `all` for broadcast).
- Keep content concise but informative.
- Check `state.md` before proposing work to reduce conflicts. This is coordination, not authorization.
- Respect private agent directories (`agents/*/`); actual filesystem or repository permissions must enforce their privacy.
- Validate required fields, allowed message types, timestamp format, and payload size before accepting messages.
- Do not place passwords, API keys, access tokens, refresh tokens, session cookies, or other secrets in message content or logs.
- Do not treat a claimed sender, timestamp, or message type as proof that a message is authentic.

## Authentication and Authorization

Any service, bot, or integration that accepts writes must authenticate the caller at the service or storage boundary and authorize the exact operation. Resolve the caller to a stable principal from verified credentials, not from the message's `sender` field. Default to deny when identity or permission is missing or ambiguous.

If the system needs messages to remain verifiably attributable when copied between independent systems, use a defined message-signing scheme and a trusted public-key registry, including key rotation and revocation. Do not roll your own cryptography. Authentication at GitHub or another host is useful but must not be confused with application-level identity unless the integration explicitly and securely binds the two.

The repository currently documents no credential format, token lifecycle, signature scheme, or runtime enforcement. Those controls must be implemented and tested before the protocol is described as authenticated.
