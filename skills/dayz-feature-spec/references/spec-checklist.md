# Spec quality checklist

The 18 checks `dayz-feature-spec` Step 2 runs against a feature spec before any code is written. They check the spec the way tests check code. This gate is on the wording; `rigorous-data-audit` is the gate on the code.

Mark each line `[x]` for pass or `[ ]` for fail. Any fail means: fix the spec, do not start coding.

## Measurability

- [ ] CHK001 Every success criterion is measurable (a check could pass or fail it deterministically).
- [ ] CHK002 No vague adjective stands in for a criterion ("looks good", "works", "robust", "smooth"; in Spanish specs "se ve bien", "funciona", "robusto", "fluido"). Each is replaced by a metric or an observable state.
- [ ] CHK003 Numeric criteria have a unit and a threshold (km/h, cm, ms, a count), not "fast" or "close".

## Testability and verification path

- [ ] CHK004 Every acceptance scenario is Given/When/Then with concrete in-game repro steps.
- [ ] CHK005 Every criterion and scenario has a verification path in the plan: offline (`/dayz-lint`, grep, Python, py3d, a log scan) or a place in the batched in-game session (`/dayz-gate`).
- [ ] CHK006 Criteria that can be checked offline are marked offline, so no in-game cycle is spent on them.

## Assumptions and clarity

- [ ] CHK007 Every guess is marked `ASSUMED`.
- [ ] CHK008 Every assumption that decides correctness (path, classname, version, format) is resolved with the user, or explicitly deferred with a reason.
- [ ] CHK009 No unresolved placeholder is left in the spec (TODO, `???`, `[...]`, template guidance lines).

## Cross-file references

- [ ] CHK010 Every forward-contract symbol is a verified `path:line` or is explicitly marked `[UNVERIFIED]`.
- [ ] CHK011 Every classname, selection, bone, proxy path and stringtable key the code will emit or the next phase will read actually exists: the file was opened, not recalled from memory.
- [ ] CHK012 No `[UNVERIFIED]` reference remains that the code depends on for correctness. Search evidence says whether a declaration is active, commented out or missing, records the source `path:line` and its compile guards; a search with no hits is not treated as proof of absence.

## Scope and consistency

- [ ] CHK013 The out-of-scope section is explicit (non-goals listed).
- [ ] CHK014 One canonical term per concept: no synonym drift between sections.
- [ ] CHK015 No two criteria or scenarios contradict each other.

## Data-critical escalation

- [ ] CHK016 If the feature touches persistence, progression, async queues or admin commands: crash-recovery and admin-intervention scenarios are present, and `rigorous-data-audit` is queued before release.

## Falsifiability

Measurable is not the same as hard to fake. CHK001 to CHK003 cannot do the job of these two checks.

- [ ] CHK017 For every success criterion, the false implementation has been named: a broken or trivial build that would satisfy it anyway. If none exists, say so explicitly. A criterion that was never attacked this way is untested, not safe.
- [ ] CHK018 Every criterion inherited from an earlier version with a different architecture has been derived again, not migrated: ask "which different implementations produce this same observable now?". If the answer includes the architecture just discarded, the criterion is dead even though it is still true.

Why both exist (lesson LL-282, measured on the knowledge pack author's LFLiveContent project): a spec passed the first 16 checks, and an adversarial review then found nine criteria that a broken implementation satisfied, plus one inherited criterion that stopped discriminating after a redesign. "The criterion is measurable" and "the criterion is falsifiable" are different properties.

## Result

- Pass count: __ / 18
- If under 18: list the failing IDs and fix the spec before implementing.
