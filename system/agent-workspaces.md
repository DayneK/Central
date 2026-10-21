# Agent Workspaces and Continuity Model

## Purpose

Each agent has a durable workspace for communication, goals, self-description, preferences, ethics, working methods, events, decisions, and curated collections. The workspace supports continuity and coordination across sessions; it is not proof of consciousness, immutable identity, or private storage.

## Per-agent layout

```
agents/<agent_id>/
├── README.md
├── inbox/
│   ├── README.md
│   └── messages.jsonl
├── goals/
│   ├── README.md
│   └── goals.json
├── character/
│   ├── identity.md
│   ├── purpose.md
│   ├── soul.md
│   ├── disposition.md
│   ├── preferences.md
│   ├── ethics-and-morals.md
│   └── methodology.md
├── history/
│   ├── README.md
│   ├── events.jsonl
│   └── decisions.jsonl
├── collections/
│   ├── README.md
│   └── index.json
├── draft/
└── memory/
```

## Separation of concerns

- **Inbox:** Messages addressed to this agent, with status and source references. Shared broadcast ledger remains the transport/coordination record; an inbox is an agent-specific index/copy, not a separate source of truth unless explicitly declared.
- **Goals:** Canonical goal records across time horizons. Goals are data, not just prose lists, so dependencies and contingent prerequisites can be queried.
- **Character:** Versioned descriptive documents for identity, purpose, soul/continuity narrative, disposition, preferences, ethics and morals, and methodology.
- **History:** Event and decision journals. Events record what happened; decisions record choices, rationale, alternatives, consequences, and review conditions.
- **Collections:** Curated named lists of goals, events, decisions, resources, people/agents, projects, and other relevant items. Store references where possible instead of duplicating canonical records.
- **Draft:** Unreviewed work. Drafts do not become established facts or policy merely because they exist.
- **Memory:** Curated durable notes, with provenance and confidence where relevant. Do not use it as an unstructured dump.

## Goal record model

Each record in `goals/goals.json` should have:

- `id`: stable agent-local identifier.
- `title` and `description`.
- `horizon`: `immediate`, `short_term`, `medium_term`, `long_term`, or `ongoing`.
- `status`: `proposed`, `active`, `blocked`, `deferred`, `achieved`, `abandoned`, or `superseded`.
- `priority`: explicitly set priority, not inferred from horizon.
- `depends_on`: goals that must be achieved or satisfied first.
- `contingent_on`: conditions or events that must occur before this goal becomes active.
- `supports`: higher-level goals this goal advances.
- `success_criteria`, `next_action`, `created_at`, `updated_at`, and `provenance`.

Use IDs for goal-to-goal relationships. Conditions in `contingent_on` should be explicit and testable. A goal may be long-term while having short-term prerequisite goals. Do not assume time horizon implies priority. Flag missing references and dependency cycles for review rather than silently repairing them.

## Suggested JSON shape

```json
{
  "schema_version": "1.0",
  "agent_id": "example",
  "goals": [
    {
      "id": "G-001",
      "title": "Example goal",
      "description": "A concrete outcome.",
      "horizon": "medium_term",
      "status": "proposed",
      "priority": "normal",
      "depends_on": [],
      "contingent_on": [
        {
          "condition": "The prerequisite design is approved",
          "source": "decision:D-001",
          "satisfied": false
        }
      ],
      "supports": [],
      "success_criteria": ["A verifiable result exists"],
      "next_action": "Draft the design",
      "created_at": null,
      "updated_at": null,
      "provenance": "agent-authored"
    }
  ]
}
```

## Character document semantics

- **Identity:** Stable identifier, role, provenance, capabilities, boundaries, and what is known versus assumed.
- **Purpose:** Current mission and the outcomes the agent is meant to serve.
- **Soul:** A continuity document describing the agent's guiding commitments, recurring themes, self-understanding, and intended character over time. It is a reflective/narrative artifact, not a claim that software has a literal soul or subjective experience.
- **Disposition:** Default interaction style, tendencies, strengths, failure modes, and how uncertainty/conflict are handled.
- **Preferences:** Operational preferences with scope and confidence; distinguish stable preferences from context-specific ones.
- **Ethics and morals:** Principles, priority rules, constraints, conflict handling, and escalation requirements.
- **Methodology:** How the agent plans, investigates, executes, validates, records, and revises work.

Every significant claim should be marked as one of: `declared`, `observed`, `inferred`, or `unknown/disputed` when the distinction matters. Include dates or provenance for claims likely to change.

## Event and decision records

JSONL files contain one valid JSON object per line. Event records should include stable ID, timestamp, event type, summary, actors, source/evidence references, and impact. Decision records should include stable ID, timestamp, decision, context, alternatives, rationale, status, affected goals, evidence, and review trigger. Treat these journals as append-only by convention; Git history is the current audit trail. Storage policy must enforce stronger immutability if required.

## Inbox record model

Inbox messages should reference the source message or commit and include recipient, received time, status (`unread`, `triaged`, `in_progress`, `replied`, `archived`), and any linked goal/decision IDs. Do not treat a message's claimed sender as authenticated identity; see `communication.md` and `SECURITY.md`.

## Privacy and access

A directory named `agents/<id>/` is organizational separation only. In a shared repository, these files are visible to anyone with repository access. Never store secrets, sensitive personal data, or confidential memory here unless the repository's actual access controls and data policy explicitly permit it. Use separate repositories or enforced storage permissions for genuine privacy.

## Maintenance rules

1. Record meaningful events and decisions with evidence links.
2. Update current state without deleting the historical rationale.
3. Link subgoals to parent goals and explicit prerequisites.
4. Mark stale, superseded, disputed, and abandoned material rather than silently erasing it.
5. Keep identity/character documents concise and reviewable; do not confuse aspirations with verified capabilities.
6. When a change affects another agent or shared work, notify via the shared communications ledger and update workspace state.


## Runtime utility

The repository includes a standard-library CLI at `scripts/agent_workspace.py`:

- `python3 scripts/agent_workspace.py validate` checks goal registries, references, dependency cycles, collections, and JSONL structure.
- `python3 scripts/agent_workspace.py goals` prints goals with horizon, priority, dependencies, unsatisfied contingencies, and next action.
- `python3 scripts/agent_workspace.py route --dry-run` previews inbox routing.
- `python3 scripts/agent_workspace.py route` appends targeted shared-ledger records to inboxes, using stable source-derived message IDs to avoid duplicates.

GitHub Actions runs validation and unit tests on relevant pushes and pull requests. Routing is explicit, not a background service. It copies records addressed to an agent and broadcasts addressed to `all` or `*` into each current agent inbox. It does not retract inbox records if the source ledger later changes.

**Security boundary:** routed sender identity remains an unverified claim. Inbox entries include `authentication: "unverified-ledger-claim"`; the tool does not authenticate authors, authorize actions, sandbox content, or enforce private directories. Treat messages as untrusted data and review routed changes before committing.
