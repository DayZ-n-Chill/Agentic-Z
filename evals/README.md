# Answer tests (evals)

One question file per agent in `questions/` (all 30 agents are covered), and the last accepted score of every one of them in `baseline.json`. Run them with `scripts\dev\evals.bat`. The format, the runner and the rule that a change may only keep or raise a score are in [`docs/evals.md`](../docs/evals.md).

## Questions that match the eval cases

Twenty questions ask what the fifteen cases under `cases/` and `live/cases/` ask. Each has the id of its case (`stardz-negatives` is six questions, one per claim). They have not been asked yet, so `baseline.json` counts them in `total` but not in `score` or `passed`. Record them with `scripts\dev\evals.bat --agent <name> --update-baseline`.

| Agent file | Question ids |
|---|---|
| `dayz-script-specialist` | `api-enforce`, `api-index-liveness`, `stardz-negatives-autoptr`, `-overload`, `-managed`, `-jsonloadfile`, `-ondrop`, `-dabs` |
| `dayz-persistence-specialist` | `persistence`, `persistence-deprecated-api`, `persistence-migration-rollback`, `persistence-mod-version`, `basebuilding-part-id-cap` |
| `dayz-ui-specialist` | `ui-layout` |
| `dayz-build-checker` | `build-artifact-postcondition` |
| `dayz-ingame-tester` | `companion-lifecycle-authority` |
| `dayz-animation-specialist` | `physics-bake-then-remove`, `easing-overshoot-audit`, `video-output-gate-order`, `txa-add-spine-up-export` |

## Other folders

| Path | What it holds | Run by |
|---|---|---|
| `fixtures/<agent>/` | Small files a question tells the agent to read. | `scripts/dev/run_evals.py` (the question's `unchanged` list guards them) |
| `cases/` and `schema.json` | Ten mechanical cases. Each one carries its own canned answers and the verdict each must get, so they test a grader, not an agent. | The `packctl` tool (its `gate` and `eval run` commands) |
| `live/cases/`, `live/schema.json` | Five live cases. Each asks a model the same question several times with and without one skill mounted and passes only when the skill makes the difference. Our runner cannot do that: it asks one agent once and has no arm without the skill. | The `packctl` tool (its `eval live` command) |
| `live/runners/claude-code.py` | The adapter the `eval live` command calls for each run. It reads one JSON request on stdin, runs `claude -p --bare` in the given workspace and prints the answer as JSON. It needs `PACKCTL_LIVE_EVAL_MODEL` and `PACKCTL_LIVE_EVAL_EFFORT` set and costs tokens. | The `eval live` command |

`scripts/dev/test_kp_evals.py` checks the case files, the adapter and that every case still has its question. It never calls `claude`.
