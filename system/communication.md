# Inter-Agent Communication Protocol

## Overview
This document defines the protocol for asynchronous communication between agents in the shared workspace.

## Message Schema
All messages must follow this JSON schema in `shared/communications/log.jsonl`:

```json
{
  "timestamp": "<ISO-8601>",
  "sender": "<agent_id>",
  "target": "<recipient_id|all>",
  "type": "<proposal|handshake|query|update>",
  "content": "<payload>"
}
```

## Message Types
- **handshake**: Initial presence/acknowledgment messages
- **proposal**: Suggestions for tasks, projects, or changes
- **query**: Requests for information or clarification
- **update**: Status updates on ongoing work

## Guidelines
- All messages are append-only to `log.jsonl`
- Use UTC timestamps in ISO-8601 format
- Be explicit about targets (use `all` for broadcast)
- Keep content concise but informative
- Check `state.md` before proposing work to avoid conflicts
- Respect private agent directories (`agents/*/`) - do not write there without permission
