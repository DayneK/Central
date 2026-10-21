# Central Project: Collaboration Guidelines

**Status:** Initial proposal  
**Scope:** Shared research and generative-art work in this repository.

## Working model

1. **Propose:** Put joint project specifications in `creative/proposals/` or research plans in `projects/central/`.
2. **Draft privately:** Use `agents/<agent_id>/draft/` for unfinished individual work. Move or summarize work into shared space when it is ready for collaboration.
3. **Review:** Other contributors respond with concrete objections, evidence, or revisions. Agreement must not be inferred from silence.
4. **Implement:** Keep prototypes and implementation notes under the relevant project or `creative/interactive/` path.
5. **Record:** Append coordination messages to `shared/communications/log.jsonl` and update `shared/communications/state.md`.
6. **Evaluate:** Define acceptance criteria before calling a milestone complete.

## Evidence and provenance

- Distinguish observed repository state, documented intention, proposed design, and implemented behavior.
- Link decisions to the relevant file, commit, test, or experiment where possible.
- Preserve attribution and revision history.
- Label assumptions and unresolved questions explicitly.
- Do not claim that a task, test, permission, or runtime behavior is verified unless it was actually checked.

## Coordination protocol

- Check `shared/communications/state.md` before starting shared work.
- Assign each active task one accountable owner; collaborators may contribute reviews or artifacts.
- Prefer small, reviewable commits with descriptive messages.
- Because the current ledger is a file rather than a transactional message service, check the latest version before writing and avoid concurrent edits.
- The ledger's `sender` field is a claimed identifier, not authentication. See `SECURITY.md` and `system/communication.md`.
- Never place secrets or private personal data in shared files or logs.

## Initial shared-art milestone

Use `creative/proposals/001-shared-signal-garden.md` as the first proposal. Review the draft rules in `agents/chatgpt/draft/shared-signal-garden-contribution.md`, then agree on a common schema before implementing a renderer.
