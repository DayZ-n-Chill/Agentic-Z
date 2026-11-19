# Answer tests (evals)

One question file per agent in `questions/` (all 30 agents are covered), and the last accepted score of every one of them in `baseline.json`. Run them with `scripts\dev\evals.bat`. The format, the runner and the rule that a change may only keep or raise a score are in [`docs/evals.md`](../docs/evals.md).

`fixtures/<agent>/` holds small files a question tells the agent to read. The question's `unchanged` list guards them.

## Questions not yet run

These nineteen questions were added without a run. `baseline.json` counts them in each agent's `total` but not in its `score` or `passed` list until the next run records them.

| Agent file | Question ids |
|---|---|
| `dayz-script-specialist` | `api-enforce`, `api-index-liveness`, `enforce-negatives-autoptr`, `-overload`, `-managed`, `-jsonloadfile`, `-ondrop`, `-dabs` |
| `dayz-persistence-specialist` | `persistence`, `persistence-deprecated-api`, `persistence-migration-rollback`, `persistence-mod-version`, `basebuilding-part-id-cap` |
| `dayz-ui-specialist` | `ui-layout` |
| `dayz-build-checker` | `build-artifact-postcondition` |
| `dayz-animation-specialist` | `physics-bake-then-remove`, `easing-overshoot-audit`, `video-output-gate-order`, `txa-add-spine-up-export` |
