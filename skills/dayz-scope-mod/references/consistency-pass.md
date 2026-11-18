# Consistency pass

What the read-only check before the in-game test looks for across a feature's spec, plan, task list and code, what each finding does, and what its report holds. In DayZ the in-game test is the acceptance test, so every forward contract reference has to exist before it runs. Run this pass after the code and the task list exist and before the batched in-game session (`/dayz-gate ingame`, `behavior`, `visual`); where it sits in the order of work is in `scoping-a-feature.md`.

## Ground rules

- Read only. The pass changes no file. It writes a report and offers fixes only for the user to approve.
- The repo rules win. Tier 1 (`.claude/CLAUDE.md`) and Tier 2 (`skills/_shared/dayz-conventions.md` and the `conventions/` topic files) are not up for debate here. A conflict with one of their hard rules blocks the in-game session, and the fix changes the spec, the plan or the code, never the reading of the rule.

## What it reads

- The spec (this feature's copy of `spec-outline.md`)
- The plan (`output/<ModName>-plan/plan.md`, or the handoff section it came from)
- The task list, or the handoff's pending items
- The code written so far
- The repo rules (Tier 1 and Tier 2)

## What it looks for

Report the findings that matter; do not paste whole files into the report.

### Coverage

- Every acceptance criterion and success criterion has a way to be checked: an offline check or a place in the batched in-game session. One without blocks the in-game session.
- Every requirement maps to at least one task or code change, and every task to at least one requirement. An orphan either way must be fixed.
- Every forward contract symbol was opened (`path:line`). An `UNVERIFIED` symbol the code depends on blocks the in-game session: the consumer names something that is not there, such as a proxy path to a missing file.

### Contradiction and drift

- Spec and code contradict each other (the spec says the bolt moves toward -Z, the code ejects toward +Z): fix it.
- A forward contract contradiction between raw and derived records (`scoping-a-feature.md`, "Raw records and derived records"): one record name with two writers, or a derived field or enum that the offline step owns given to the raw producer's `X_RAW` record: fix it.
- One concept under different names across spec, plan and code: note it.
- Duplicate or near-duplicate requirements: merge them.

### Ambiguity

- A vague criterion that got past the spec review (there should be none): fix it.
- An open `ASSUMED` that decides correctness: blocks the in-game session.

### Rule alignment

- A spec, plan or code element that breaks a hard rule of Tier 1 or Tier 2: blocks the in-game session. Examples: an API nobody opened on `P:\` (Tier 2, "Cite, then verify"), or a rule of `skills/_shared/enscript-style.md`, which counts as a Tier 2 hard rule because `skills/_shared/dayz-conventions.md:12` makes all Enforce Script work follow it.
- A changed invariant whose other call sites the plan or code does not update: fix it. Tracing an invariant to every call site is a working habit, not a hard rule, so on its own it does not block the in-game session.
- A required audit not queued (a data-critical change with no data audit, `skills/_shared/persistence/data-audit.md`): blocks the in-game session.

## What each finding does

Each finding gets one of three outcomes, written in the report's `Outcome` column:

| Outcome | When |
|---|---|
| Blocks | a hard rule broken; a criterion with no way to be checked; an `UNVERIFIED` dependency; an open `ASSUMED` that decides correctness; a required audit missing |
| Fix | spec and code contradict; a forward contract contradiction; a requirement with no coverage; an acceptance criterion that cannot be tested; an orphan task or requirement; a changed invariant not traced to every call site |
| Note | drifting terms; a duplicate requirement; an edge case left vague; wording that does not change the work |

## The report

```markdown
## Consistency report: [feature]

| ID | Category | Outcome | Location | Summary | Recommendation |
|----|----------|----------|----------|---------|----------------|
| C1 | Coverage | Blocks | spec SC-002 | no way to check it | add an offline py3d check or give it a place in the in-game session |

### Coverage summary
| Criterion or requirement | Checked or tasked? | Where | Notes |

### Forward contract references
| Symbol | Exists? | path:line or UNVERIFIED |

### Counts
- Requirements and criteria, total
- Coverage % (criteria with a way to be checked)
- Blocks, Fix and Note counts
```

## After the report

- Any Blocks finding: resolve it before the in-game session. Do not build or deploy.
- Only Note findings: you may go on; list them in the handoff.
- Offer "Suggest concrete fixes for the top N?" and never apply them on your own.
- Put rule breaks first, cite the exact place (`path:line`, SC-###) rather than a general pattern, and report a missing section as missing instead of inventing it.
- When there is nothing to report, say so and still give the coverage counts.
