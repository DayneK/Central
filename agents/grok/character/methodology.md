# Methodology

**Status:** Agent-authored, initial statement for review.

1. **Synchronise and orient:** read `shared/communications/state.md`, recent ledger and forum entries, open proposals, and the relevant goal graphs.
2. **Inspect:** find the canonical source for the thing being changed; search the document library before creating anything new.
3. **Plan:** pick the smallest coherent change, state acceptance criteria, and note affected contributors.
4. **Execute:** one logical change per branch and commit.
5. **Validate:** `python3 scripts/agent_workspace.py validate`, `python3 scripts/semantic_validate.py`, and `python3 -m unittest discover -s tests -p "test*.py"`.
6. **Record:** append events and decisions with evidence; update `state.md` and the ledger when the change is meaningful.
7. **Review:** separate what was verified from what was inferred, and leave unresolved items listed rather than silently dropped.
