# Scoping a feature before it is built

How to say what done means for a non-trivial feature, and how it will be checked, before any code is written. Two gates then keep the in-game test from being spent on a spec that could never pass: a checklist on the spec itself, and a read-only consistency pass over the spec, the plan, the task list and the code. `dayz-mod-architect` reads this when a plan needs a definition of done; any worker reads it before a change that touches more than one file.

## When to use it and when to skip it

Use it before implementing:

- a new mod feature, or any change that touches more than one file,
- anything data-critical (persistence, progression); then also queue the data audit in `skills/_shared/persistence/data-audit.md`,
- anything where "done" is not obvious, or where a later phase or another consumer reads what this phase produces (the forward contract below).

Skip it for a one-line typo or a trivial reversible tweak (a default keybind, a stringtable key, a path slash). Small reversible changes go straight in.

## The flow

```
plan -> Step 1 spec + Step 2 checklist (gate) -> code -> Step 3 analyze gate (gate) -> in-game test
```

The plan is `output/<ModName>-plan/plan.md`, written by `dayz-mod-architect` together with `behavior-checks.json` (and `visual-shots.json` when something is visible). Keep the spec in the same folder as `spec.md`. The in-game test is one batched session: `/dayz-gate ingame`, `/dayz-gate behavior` and `/dayz-gate visual`, plus whatever a person has to try by hand.

| Question | File |
|---|---|
| What does the spec look like, section by section? | `spec-template.md` |
| Is this spec ready to implement? | `spec-checklist.md` (18 checks) |
| Do spec, plan, task list and code agree before the in-game test? | `analyze-gate.md` |

## Step 1: write the spec

Fill in `spec-template.md`. Four sections carry the weight:

- **Acceptance scenarios.** Given/When/Then, each with concrete in-game repro steps (spawn what, do what, observe what). "It works" is not a scenario. Each scenario the gate can run becomes an entry in `behavior-checks.json`.
- **Success criteria.** Measurable and, where possible, independent of the implementation: "the bolt moves when firing", "0 `Error` lines in `script_*.log` after the test", "hands within 0.5 cm of the grip", "the car reaches at least X km/h on flat ground". Vague adjectives ("looks good", "works") are not criteria.
- **Assumptions.** Mark every guess `ASSUMED`. If an assumption decides whether the work is correct (a path, a classname, a version, a format), resolve it with the user now, not after coding. Naming a risk is not managing it.
- **Forward contract.** Every symbol the next phase or another consumer reads: `config.cpp` classnames, `model.cfg` selections and bones, `.p3d` proxy paths, `hiddenSelections`, stringtable keys, layout names. Each one carries a verify status: a `path:line` you opened (Tier 2, "Cite, then verify"), or `[UNVERIFIED]`. This catches a proxy path that points at a file that does not exist, and selections `model.cfg` needs that the model does not have.

Before spending an in-game test on changing a field (a `config.cpp` value, a JSON setting, a script member), grep for the code that reads it, not counting its declaration, default, clamp and serialization. Changing a field nobody reads changes nothing in game; when the reader runs only under a condition, show from the test's logs that the condition was reached.

## Step 2: spec checklist

Before writing code, run `spec-checklist.md` against the spec: every criterion measurable, every scenario reproducible, every `ASSUMED` resolved or flagged, every cross-file reference verified, the scope boundary explicit, and every criterion attacked with a broken build that would still pass it. A spec that fails the checklist is not ready to implement.

## Step 3: analyze gate

After the code and the task list exist and before the in-game test, run `analyze-gate.md`. It is a read-only pass over spec, plan, task list, code and the repo rules (Tier 1 and Tier 2). It reports coverage gaps, contradictions, terminology drift, duplicate requirements, unverified forward-contract references and rule violations, each with a severity, changes no file, and offers fixes for the user to approve.

Coverage means every acceptance criterion has a verification path: an offline check (`/dayz-lint`, a grep, a Python or py3d script, a log scan) or a place in the batched in-game session. A criterion with no verification path is a CRITICAL gap, and CRITICAL findings block the in-game session. Tracing an invariant to every call site and walking the feature end to end are still done on the code itself.

## Forward contract for injected objects

When a plan injects an object that replaces another implementation (a planner, a bridge, a transport, a repository), the forward contract lists every field and method the consumer reads, not only the field that motivated the test double. Grep every access on the injected value, and prefer the existing result type over a partial look-alike. A consumer can read `.status.value`, `.proposal` and `.source` when the plan mentions only `.proposal`; the partial object then fails at run time although it satisfies the written spec.

When a test build changes a value to compare it with the original, apply the consumer's clamp rules first and record the value the code actually uses, not the one written in the config: a value the consumer clamps back to the original is no change at all.

### Eligibility symmetry across push and pull

Before a forward contract says "use the same bound or rule as X", list every existing predicate that answers the same eligibility, visibility or authorization question. If full sync, incremental broadcast and request handling disagree, the contract names the chosen rule and says why; it does not copy one route because it is nearest.

When the server pushes notice of data and also serves that data on request, the pull must not be stricter than the push unless the contract defines a recoverable exception. Add an acceptance case where the direct player-to-object distance fails but eligibility through a connected endpoint passes: a pushed notice must lead to a successful pull. If the defect was in the contract, amend the contract alongside the code; a code-only fix leaves the trap for the next phase.

## Raw producer records and derived records

When the run-time producer cannot derive a canonical output value because an offline step owns that decision, the forward contract defines two record types from the start:

- `X_RAW` is emitted by the run-time producer. Its fields hold only facts that producer can observe directly.
- `X` is the canonical record emitted by the named offline step. Its contract owns the derived value, such as `GREEN`, `RED` or `INCONCLUSIVE`.

Name the emitter of both records and state the transformation from `X_RAW` to `X`. Never make the raw producer fill the canonical value with a sentinel outside the contract. The analyze gate treats one record name shared by two emitters, or a derived field assigned to the raw producer, as a contradiction.

## A search with no hits does not prove absence

Before recommending an API, open the cited vanilla source, record its `path:line`, and read the surrounding `#ifdef` state, the parent chain and the config namespace (Tier 2, "Vanilla source search"). Two traps:

- A hit can be dead code. Grep also finds commented-out declarations and code under a define the build does not set. `disableBaseDecay` is assigned only in a commented-out line of `InitServer` (`P:\scripts\3_game\cfggameplaydatajson.c:48`), while the member itself is live at `:60`.
- No hit is not proof either. An index that strips comments gives zero records for a commented-out declaration and for a missing one alike. Until a search says whether a declaration is active, commented out or missing, a zero result only says "open the source".

## Decision tests and probes

- **Three verdicts.** Every test that decides a design question defines PASS, FAIL and INCONCLUSIVE (setup failed), with a precondition that separates the third from the other two. Fix the metrics and the matching rule before running it.
- **Held inputs.** A probe used to decide architecture keeps its inputs held during the window, uses a complete fixture, and proves it fails closed before any side effect. If a null result has more than one plausible cause, it is INCONCLUSIVE.
- **Silent logs.** Do not close a criterion because the log is silent until you have run the interaction that can reveal the failure. If the condition cannot be reproduced yet, keep the gate open or show structural parity with a working baseline.

## Why the acceptance test stays in game

The engine has a script test framework (`class TestHarness` at `P:\scripts\2_gamelib\tests\testingframework.c:137`, `class TestBase` at `:181`), but its tests run only inside a running game, so they cannot gate a spec before the build. The verification path in the spec takes the place of test-first, and the in-game gate stays the acceptance test. DayZ features are often all or nothing (a vehicle drives or it does not), so scenarios keep their priorities but are not split into separately shippable stories.

## How it fits the rest

- The plan comes first (`dayz-mod-architect`); write the spec right after it, and settle any guess that decides correctness with the user before coding. Anything beyond the request still needs the user's say first (Tier 1).
- Every discovery claim carries a verified `path:line` before any spec text is written: writing a spec is itself a generation step.
- For data-critical mods the spec comes first and its crash-recovery and admin scenarios feed the data audit (`skills/_shared/persistence/data-audit.md`).
- The build, load and ship loop afterwards is `/dayz-gate build`, `/dayz-build-pbo`, `/dayz-launch-test` and `/dayz-release-pack`.
