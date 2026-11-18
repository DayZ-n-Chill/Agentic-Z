# Spec review

Which 18 checks a feature spec must pass before any code is written. They test the spec the way tests check code. This review is on the wording; the data audit (`skills/_shared/persistence/data-audit.md`) is the check on the code of a data-critical mod. Where it sits in the order of work is in `scoping-a-feature.md`.

Mark each line `[x]` for pass or `[ ]` for fail. Any fail means you fix the spec before you start coding.

## Measurable

- [ ] CHK001 Every success criterion is measurable: a check could pass or fail it the same way every time.
- [ ] CHK002 No vague adjective stands in for a criterion ("looks good", "works", "robust", "smooth"); each is replaced by a measure or a state you can see.
- [ ] CHK003 Numeric criteria have a unit and a threshold (km/h, cm, ms, a count), not "fast" or "close".

## Testable, with a way to check each one

- [ ] CHK004 Every acceptance scenario is Given, When, Then, with concrete in-game steps.
- [ ] CHK005 Every criterion and scenario has a way to be checked in the plan: offline (`/dayz-lint`, grep, Python, py3d, a log scan) or a place in the batched in-game session (`/dayz-gate`).
- [ ] CHK006 Criteria that can be checked offline are marked offline, so no in-game cycle is spent on them.

## Assumptions and clarity

- [ ] CHK007 Every guess is marked `ASSUMED`.
- [ ] CHK008 Every assumption that decides correctness (path, classname, version, format) is settled with the user, or put off on purpose with a reason.
- [ ] CHK009 No placeholder is left in the spec (TODO, `???`, `[...]`, guidance lines from the outline).

## References to other files

- [ ] CHK010 Every forward contract symbol is a `path:line` you opened, or is marked `UNVERIFIED`.
- [ ] CHK011 Every classname, selection, bone, proxy path and stringtable key the code will write or the next phase will read actually exists: the file was opened, not recalled from memory.
- [ ] CHK012 No `UNVERIFIED` reference is left that the code depends on for correctness. The search behind each one says whether the declaration is active, commented out or missing, and records the source `path:line` and its compile guards; a search with no hits is not taken as proof that something is absent.

## Scope and consistency

- [ ] CHK013 The out-of-scope section lists the non-goals.
- [ ] CHK014 One term per concept: no synonyms drifting between sections.
- [ ] CHK015 No two criteria or scenarios contradict each other.

## Data-critical work

- [ ] CHK016 If the feature touches persistence, progression, async queues or admin commands: crash recovery and admin intervention scenarios are present, and the data audit (`skills/_shared/persistence/data-audit.md`) is queued before release.

## Hard to fake

Measurable is not the same as hard to fake; CHK001 to CHK003 cannot do the job of these two.

- [ ] CHK017 For every success criterion, the false implementation is named: a broken or trivial build that would satisfy it anyway. If there is none, say so. A criterion never attacked this way is untested, not safe.
- [ ] CHK018 Every criterion carried over from an earlier version with a different architecture is worked out again, not copied: ask "which different implementations give this same result now?". If the answer includes the architecture just dropped, the criterion no longer tells them apart, even though it is still true.

A spec can pass the first 16 checks and still hold a criterion a broken build meets, or an old criterion that stopped telling designs apart after a redesign.

## Result

- Pass count: __ / 18
- Under 18: list the failing IDs and fix the spec before implementing.
