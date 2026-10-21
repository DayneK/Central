# Goal Graph

`goals.json` is the canonical structured goal registry for this agent. It represents goals across immediate, short-term, medium-term, long-term, and ongoing horizons.

- `depends_on`: prerequisite goal IDs.
- `contingent_on`: explicit external conditions or events.
- `supports`: higher-level goals advanced by this goal.
- `status`: current lifecycle state; retain achieved, abandoned, and superseded goals for history.

Before activating a goal, check its dependencies and contingent conditions. Flag cycles, dangling IDs, and contradictory statuses for review.
