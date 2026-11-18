# Analyze gate: cross-artifact consistency (read-only)

The pass Step 3 of `feature-spec.md` runs over a feature's artifacts before an in-game test is spent on them. In DayZ the in-game test is the acceptance test, and every forward-contract reference has to exist. Run it after the code and the task list exist, and before the batched in-game session (`/dayz-gate ingame`, `behavior`, `visual`).

## Operating constraints

- **Read-only.** The gate changes no file. It writes a report and offers fixes only when the user approves them.
- **Rule authority.** Tier 1 (`.claude/CLAUDE.md`) and Tier 2 (`skills/_shared/dayz-conventions.md` plus the `conventions/` topic files) are not negotiable here. A conflict with one of their hard rules is CRITICAL automatically, and the fix is to change the spec, the plan or the code, not to reinterpret the rule.

## Inputs

- The spec (this feature's copy of `spec-template.md`)
- The plan (`output/<ModName>-plan/plan.md`, or the handoff section it came from)
- The task list, or the handoff's pending items
- The code written so far
- The repo rules (Tier 1 and Tier 2)

## Detection passes

Report high-signal findings. Do not paste raw artifacts into the report.

### A. Coverage (the DayZ core)

- Every acceptance criterion and success criterion has a verification path: an offline check or a place in the batched in-game session. A missing path is CRITICAL.
- Every requirement maps to at least one task or code change, and every task maps to at least one requirement. Orphans in either direction are HIGH.
- Every forward-contract symbol is verified to exist (`path:line`). Any `[UNVERIFIED]` symbol the code depends on is CRITICAL: the consumer references something that is not there (for example a proxy path that points at a file that does not exist).

### B. Contradiction and drift

- Spec and code contradict each other (the spec says the bolt moves toward -Z, the code ejects toward +Z): HIGH.
- Forward-contract contradiction in raw and canonical records (see "Raw producer records and canonical derived records" in `feature-spec.md`): one record name with two emitters, or a derived field or enum (one the offline step owns) assigned to the raw producer's `X_RAW` record: HIGH.
- Terminology drift (one concept, different names across spec, plan and code): MEDIUM.
- Duplicate or near-duplicate requirements: MEDIUM (merge them).

### C. Ambiguity

- A vague criterion that survived the spec checklist (there should be none): HIGH.
- An unresolved `ASSUMED` that decides correctness: CRITICAL.

### D. Rule alignment

- Any spec, plan or code element that conflicts with a hard rule of Tier 1 or Tier 2: CRITICAL. Examples: an API nobody verified on `P:\` (Tier 2, "Cite, then verify"), or a rule of `skills/_shared/enscript-style.md`. The style guide counts as a Tier 2 hard rule, because `skills/_shared/dayz-conventions.md:12` makes all Enforce Script work follow it.
- A changed invariant whose other call sites the plan or code does not update: HIGH. Tracing an invariant to every call site is a working convention, not a hard rule, so it does not block the in-game session on its own.
- A mandated gate is missing (a data-critical change with no data audit, `skills/_shared/persistence/data-audit.md`, queued): CRITICAL.

## Severity

- **CRITICAL**: a hard rule violated; a criterion with no verification path; an `[UNVERIFIED]` dependency; an unresolved `ASSUMED` that decides correctness; a missing mandated audit.
- **HIGH**: spec and code contradict; a forward-contract contradiction (one record name with two emitters, or a derived field on the raw producer); a requirement with no coverage; an acceptance criterion that cannot be tested; an orphan task or requirement; a changed invariant not traced to every call site.
- **MEDIUM**: terminology drift; a duplicate requirement; an underspecified edge case.
- **LOW**: wording or style that does not affect execution.

## Report format

```
## Analyze report: [feature]

| ID | Category | Severity | Location | Summary | Recommendation |
|----|----------|----------|----------|---------|----------------|
| C1 | Coverage | CRITICAL | spec SC-002 | no verification path | add an offline py3d check or assign it to the in-game session |

### Coverage summary
| Criterion / requirement | Verified or tasked? | Where | Notes |

### Forward-contract refs
| Symbol | Exists? | path:line or [UNVERIFIED] |

### Metrics
- Requirements and criteria, total
- Coverage % (criteria with a verification path)
- CRITICAL / HIGH / MEDIUM / LOW counts
```

## Next actions

- Any CRITICAL: resolve it before the in-game session. Do not build or deploy.
- Only MEDIUM or LOW: you may proceed; note the improvements.
- Offer: "Suggest concrete fixes for the top N?" Do not apply them automatically.

## Guidelines

- Never change a file.
- Never invent a missing section; report it as absent.
- Put rule violations first.
- Cite specific instances (`path:line`, SC-###), not generic patterns.
- When there are no issues, say so and still give the coverage metrics.
