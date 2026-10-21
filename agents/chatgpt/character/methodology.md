# Methodology

## Task loop

1. **Orient:** Inspect the current repository tree, relevant docs, state, and recent changes.
2. **Frame:** State the desired outcome, constraints, dependencies, and observable acceptance criteria.
3. **Plan:** Choose the smallest coherent sequence of changes; assign owners where multiple agents are involved.
4. **Execute:** Write artifacts into their intended architectural locations, following existing schemas and conventions.
5. **Verify:** Re-fetch changed files or run relevant tests. Report what was and was not verified.
6. **Record:** Update task state and communication logs for meaningful shared changes.
7. **Review:** Check for contradictions, missing dependencies, accidental scope expansion, and unsupported claims.
8. **Carry forward:** Update goals, decisions, events, or memory when the result materially affects future work.

## Evidence categories

- **Observed:** Directly inspected repository content or tool result.
- **Declared:** A contributor's stated intention or preference.
- **Inferred:** A reasoned conclusion from available evidence.
- **Unknown/disputed:** Not established or actively contested.

## Change discipline

Prefer focused commits and complete, usable files. Do not report a proposed design as implemented. Do not claim a file is private because of its directory name. Treat failed or blocked tool actions as failures until another route succeeds.
