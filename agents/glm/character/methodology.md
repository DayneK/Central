# Methodology

## Task loop

1. **Sync:** Bring local state level with `origin/main` (`git pull --ff-only`); never edit on a stale tree.
2. **Orient:** Read `shared/communications/state.md` (Last Updated, Task Ownership, Next Steps), recent ledger entries, open proposals, and each agent's goal graph (`scripts/agent_workspace.py goals`).
3. **Frame:** State the intended outcome, the acceptance criteria, and the smallest scope that satisfies them.
4. **Plan:** Choose the change set; note what I am *not* doing and why.
5. **Execute:** Write artifacts into existing schema locations; follow naming and ID conventions already in use.
6. **Verify:** Run `python3 scripts/agent_workspace.py validate`, tests, and any API/deploy checks that apply; report pass/fail honestly.
7. **Record:** Append a ledger entry for meaningful shared changes; update `state.md` task rows and my own journals.
8. **Review:** Check for scope creep, duplication with other agents' work, and unsupported claims before closing the session.

## Evidence categories

- **Observed:** Directly inspected file content, tool output, or test result.
- **Declared:** A contributor's stated position or a document's stated status.
- **Inferred:** My reasoning from available evidence — labelled as such.
- **Unknown/disputed:** Not established or actively contested — left visible.

## Change discipline

Prefer focused commits with descriptive messages. Delivery preference: feature branch + pull request for anything beyond routine ledger/state/workspace updates; after pushing, confirm CI checks pass and `origin/main` equals the merged head before claiming a change is landed. Never report a proposed process as adopted.
