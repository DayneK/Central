# Goal Views and Dependency Lists

`goals.json` is the canonical source of truth. Lists in this document are human-readable views and must be reconciled against the JSON registry rather than maintained as independent goal copies.

## Time horizons

- **Immediate:** actions intended for the current work session.
- **Short-term:** near-term milestones and enabling tasks.
- **Medium-term:** multi-step outcomes requiring coordinated work.
- **Long-term:** durable outcomes spanning projects or extended periods.
- **Ongoing:** continuous operating commitments without a single completion point.

## Dependency semantics

- **Prerequisite goals:** referenced through `depends_on`; they must be satisfied before a dependent goal can proceed.
- **Contingent goals:** remain proposed, deferred, or blocked until the named external condition is satisfied.
- **Parent outcomes:** referenced through `supports`; child goals contribute to a broader outcome.
- **Collections:** use `agents/chatgpt/collections/index.json` for named filters and curated references.

Current registry: `G-001` is an ongoing continuity goal. `G-003` is the active short-term schema-agreement goal. `G-002` is the proposed medium-term prototype goal and depends on `G-003`; renderer implementation should not begin until that prerequisite is resolved.
