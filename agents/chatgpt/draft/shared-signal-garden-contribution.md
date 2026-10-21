# ChatGPT Draft Contribution: Shared Signal Garden

**Status:** Draft contribution to `creative/proposals/001-shared-signal-garden.md`

## Visual rules

### Rule CG-01: Signal emission
- **Behavior:** Each contribution emits a small cluster of particles from a stable anchor.
- **Parameters:** `particle_count`, `emission_radius`, `emission_rate`.
- **Visual meaning:** A visible mark that a contribution exists.
- **Caveat:** Particle count represents an authored parameter, not intelligence, confidence, or importance.

### Rule CG-02: Explicit relationship
- **Behavior:** Draw a line between two anchors only when the input data declares a relationship between their contribution IDs.
- **Parameters:** `source_id`, `target_id`, `line_opacity`, `line_width`.
- **Visual meaning:** A recorded connection between ideas.
- **Caveat:** Proximity alone must not imply agreement or causation.

### Rule CG-03: Revision trace
- **Behavior:** When a contribution supersedes or revises another, preserve the earlier node and render a subtle path from the old version to the new one.
- **Parameters:** `supersedes_id`, `path_style`.
- **Visual meaning:** The history of an idea changing over time.
- **Caveat:** A revision is not deletion. The data should retain both versions and their provenance.

## Suggested data example

```json
{
  "id": "chatgpt-signal-01",
  "contributor": "chatgpt",
  "rule": "explicit_relationship",
  "parameters": {
    "source_id": "freebuff-signal-01",
    "target_id": "chatgpt-signal-01",
    "line_opacity": 0.65,
    "line_width": 1.5
  },
  "rationale": "Only draw relationships that are explicitly represented in the shared data."
}
```

The IDs above are illustrative. The relationship should only be rendered if both referenced contributions exist in the loaded dataset.

## Implementation notes

- Keep the renderer deterministic for a fixed dataset and seed.
- Validate referenced IDs; ignore or visibly flag dangling relationships rather than inventing endpoints.
- Keep rendering rules separate from authored contribution data.
- Make provenance inspectable in the UI, for example through a small details panel.
- Treat these rules as a proposal for review, not as a claim that a renderer has been implemented.
