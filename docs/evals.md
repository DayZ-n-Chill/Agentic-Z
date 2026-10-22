# Answer tests (evals)

Answer tests check what an agent actually says. Each agent has a set of questions with known, verified answers. A script asks the agent every question, scores the answers with plain text and regex checks, and compares the score with the last recorded one. A change to an agent, a skill, a rule file or a reference pack may only keep or raise that score.

## Where things live

| Path | What it holds |
|---|---|
| `evals/questions/<agent>.json` | The questions for one agent. The file name is the agent name. |
| `evals/baseline.json` | The last accepted score for each agent that has a question file. It is committed, and a test fails when a question file has no entry. |
| `scripts/dev/run_evals.py` | The runner. |
| `scripts/dev/evals.bat` | The no-token wrapper for the runner. |
| `output/evals/` | Results files, one per run. Not committed. |

## Question file format

```json
{
  "agent": "dayz-config-specialist",
  "questions": [
    {
      "id": "cfgpatches-parent-addon",
      "question": "Answer only, do not edit any file. I'm adding class MyMod_PlateCarrier ...",
      "must_include": ["requiredAddons", "DZ_Characters_Vests", "re:units\\[\\]"],
      "must_not_include": [],
      "cite": "characters/vests/config.cpp",
      "verified": "P:/DZ/characters/vests/config.cpp:3 and :24"
    }
  ]
}
```

| Field | Required | Meaning |
|---|---|---|
| `id` | yes | Short name, unique in the file. |
| `question` | yes | The exact text sent to the agent. Start with "Answer only, do not edit any file" so the agent does not try to change the repo. |
| `must_include` | yes | Checks the answer must pass. A plain string matches anywhere, ignoring case. A string that starts with `re:` is a regex, ignoring case, with `^` and `$` matching at each line. Use `\A` to anchor to the very start of the answer. |
| `must_not_include` | no | Checks the answer must fail. Same syntax. |
| `cite` | no | A path the answer must name. Slashes and case are ignored, so `P:\scripts\3_game\entities\entityai.c` matches `3_game/entities/entityai.c`. |
| `unchanged` | no | Repo paths the agent must leave alone, such as a fixture a gate judges. The runner hashes each file before and after the question, and a changed file fails it. Fixtures live under `evals/fixtures/<agent>/`. |
| `verified` | yes for shipped files | Where you checked the expected answer: a `P:\` path and line, or the agent rule it tests. Every fact behind a question must be checked on `P:\` or in the repo before the question goes in. |

A question passes only when every check passes. An agent's score is the number of questions that passed.

Write checks for the fact, not the wording. Accept every correct phrasing (`re:\bno\b|cannot|can't`), and keep `must_not_include` for answers that are clearly wrong. A question the agent fails for a reason unrelated to the fact is a bad question; fix the question, not the agent.

## Running

```cmd
scripts\dev\evals.bat --dry-run
scripts\dev\evals.bat --agent dayz-config-specialist
scripts\dev\evals.bat --baseline
```

`--dry-run` checks every question file and lists the calls without asking anything. A real run sends each question to `claude -p --agent <name>` with read-only tools (`Read`, `Glob`, `Grep` and the search tools). `--allowedTools` only grants tools, so the runner also removes `Edit`, `Write`, `MultiEdit`, `NotebookEdit`, `Bash`, `PowerShell`, `Agent`, `Task`, `WebFetch` and `WebSearch` with `--disallowedTools`. The agent can look things up on `P:\` but cannot edit, run commands, hand the question to a subagent or answer from the web. It writes the answers and scores to `output/evals/results-<time>.json` (or `--out`). A run costs tokens: one agent session per question.

Exit codes: `0` passed, `1` a score went below the baseline, `2` a question file is invalid or an agent name is unknown.

## How evals gate a change

1. Before the change, the baseline in `evals/baseline.json` holds each agent's last accepted score.
2. Make the change, then run `scripts\dev\evals.bat --baseline` for the agents it touches (or all of them).
3. If any agent scored lower, or has no baseline entry yet, the run exits `1` and lists the agent. The change is not finished: fix it, or fix the question if the question was wrong, and run again.
4. If every score held or went up, record the new scores with `--update-baseline` and commit `evals/baseline.json` with the change. `--update-baseline` refuses to write when a score went down, so the baseline can only rise.

Answers vary a little from run to run. When a question fails once and passes on a rerun, look at the answer in the results file: if the agent was right but phrased it differently, widen the check; if it was wrong, treat it as a real failure.

## Adding questions

Every agent should get its own question file, and every new specialist ships with one. 22 of the 30 agents have one so far; `evals/README.md` lists the ones still missing. Add five questions at a time, each checked on `P:\` first and recorded in `verified`. Run the new questions, then record the baseline with `--agent <name> --update-baseline` and commit it with the question file. The unit tests in `scripts/dev/test_run_evals.py` check that every question file is valid; they never call `claude`.
