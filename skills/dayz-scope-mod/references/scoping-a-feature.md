# Scoping a feature before it is built

How to say what done means for a non-trivial feature, and how each part will be checked, before any code is written. Two checks then keep the in-game test from being spent on a spec that could never pass: a review of the spec itself, and a read-only consistency pass over the spec, the plan, the task list and the code. `dayz-mod-architect` reads this when a plan needs a definition of done; any worker reads it before a change that touches more than one file.

## When to use it

Use it before you implement:

- a new mod feature, or any change that touches more than one file;
- anything data-critical (persistence, progression), and then also queue the data audit in `skills/_shared/persistence/data-audit.md`;
- anything where done is not obvious, or where a later phase or another consumer reads what this phase produces (the forward contract below).

Skip it for a one-line typo or a small reversible tweak (a default keybind, a stringtable key, a path slash). Those go straight in.

## The order of work

1. `dayz-mod-architect` writes the plan, `output/<ModName>-plan/plan.md`, with `behavior-checks.json` (and `visual-shots.json` when something is visible).
2. You write the spec beside it as `spec.md`, from `spec-outline.md`.
3. You run the spec review, `spec-review.md`. A spec that fails it is not ready to code.
4. You write the code (`implementation-protocol.md`).
5. You run the consistency pass, `consistency-pass.md`. A finding marked Blocks stops the next step.
6. The in-game test: one batched session of `/dayz-gate ingame`, `/dayz-gate behavior` and `/dayz-gate visual`, plus whatever a person has to try by hand.

| Question | File |
|---|---|
| What does the spec look like, section by section? | `spec-outline.md` |
| Is this spec ready to implement? | `spec-review.md` (18 checks) |
| Do spec, plan, task list and code agree before the in-game test? | `consistency-pass.md` |
| Which questions do I settle with the user before writing a placeable or usable object? | `questions-before-building.md` |

## Writing the spec

Fill in `spec-outline.md`. Four sections carry the weight:

- **Acceptance scenarios.** Given, When, Then, each with concrete in-game steps (spawn what, do what, see what). "It works" is not a scenario. Each scenario the gate can run becomes an entry in `behavior-checks.json`.
- **Success criteria.** Measurable and, where possible, independent of how it is built: "the bolt moves when firing", "0 `Error` lines in `script_*.log` after the test", "hands within 0.5 cm of the grip", "the car reaches at least X km/h on flat ground". Vague adjectives ("looks good", "works") are not criteria.
- **Assumptions.** Mark every guess `ASSUMED`. If an assumption decides whether the work is correct (a path, a classname, a version, a format), settle it with the user now, not after coding. Naming a risk is not managing it.
- **Forward contract.** Every symbol the next phase or another consumer reads: `config.cpp` classnames, `model.cfg` selections and bones, `.p3d` proxy paths, `hiddenSelections`, stringtable keys, layout names. Each carries a status: a `path:line` you opened (Tier 2, "Cite, then verify"), or `UNVERIFIED`. This catches a proxy path that points at a missing file, and selections `model.cfg` needs that the model does not have.

Before spending an in-game test on changing a field (a `config.cpp` value, a JSON setting, a script member), grep for the code that reads it, not counting its declaration, default, clamp and serialization. Changing a field nobody reads changes nothing in game; when the reader runs only under a condition, show from the test's logs that the condition was reached.

## The spec review

Before writing code, run `spec-review.md` on the spec: every criterion measurable, every scenario reproducible, every `ASSUMED` settled or flagged, every cross-file reference opened, the scope boundary written down, and every criterion attacked with a broken build that would still pass it.

## The consistency pass

After the code and task list exist and before the in-game test, run `consistency-pass.md`. It reads spec, plan, task list, code and the repo rules (Tier 1 and Tier 2) and reports coverage gaps, contradictions, drifting terms, duplicate requirements, unverified forward contract references and rule breaks, each with a severity. It changes no file and offers fixes for the user to approve.

Coverage means every acceptance criterion has a way to be checked: offline (`/dayz-lint`, a grep, a Python or py3d script, a log scan) or a place in the batched in-game session. A criterion with no way to be checked blocks the in-game session. Tracing an invariant to every call site and walking the feature end to end are still done on the code itself.

## Forward contract for injected objects

When a plan injects an object that replaces another implementation (a planner, a bridge, a transport, a repository), the forward contract lists every field and method the consumer reads, not only the one that motivated the test double. Grep every access on the injected value, and prefer the existing result type over a partial look-alike. A consumer can read `.status.value`, `.proposal` and `.source` when the plan mentions only `.proposal`; the partial object then fails at run time although it meets the written spec.

When a test build changes a value to compare it with the original, apply the consumer's clamp rules first and record the value the code actually uses, not the one written in the config: a value clamped back to the original is no change at all.

### The same rule for push and pull

Before a forward contract says "use the same bound or rule as X", list every existing check that answers the same question of eligibility, visibility or permission. If full sync, incremental broadcast and request handling disagree, the contract names the chosen rule and says why; it does not copy whichever route is nearest.

When the server pushes notice of data and also serves that data on request, the pull must not be stricter than the push unless the contract defines a recoverable exception. Add an acceptance case where the direct player to object distance fails but eligibility through a connected endpoint passes: a pushed notice must lead to a successful pull. If the fault was in the contract, change the contract with the code; a code-only fix leaves the trap for the next phase.

## Raw records and derived records

When the producer at run time cannot work out a final value because an offline step owns that decision, the forward contract defines two record types from the start:

- `X_RAW`, written by the run-time producer, holds only facts that producer observes directly.
- `X`, written by the named offline step, owns the derived value, such as `GREEN`, `RED` or `INCONCLUSIVE`.

Name who writes each record and how `X_RAW` becomes `X`. Never make the raw producer fill the final value with a placeholder outside the contract. The consistency pass treats one record name with two writers, or a derived field given to the raw producer, as a contradiction.

## A search with no hits proves nothing

Before recommending an API, open the cited vanilla source, record its `path:line`, and read the surrounding `#ifdef` state, the parent chain and the config namespace (Tier 2, "Vanilla source search").

- A hit can be dead code. Grep also finds commented-out declarations and code under a define the build does not set. `disableBaseDecay` is assigned only in a commented-out line of `InitServer` (`P:\scripts\3_game\cfggameplaydatajson.c:48`), while the member itself is live at `:60`.
- No hit is not proof either. An index that strips comments gives zero records for a commented-out declaration and for a missing one alike. Until a search says whether a declaration is active, commented out or missing, a zero result only says "open the source".

## Tests that decide a design question

- **Three verdicts.** Every test that decides a design question defines PASS, FAIL and INCONCLUSIVE (the setup failed), with a precondition that separates the third from the other two. Fix the measures and the matching rule before running it.
- **Held inputs.** A probe that decides architecture keeps its inputs held during the window, uses a complete fixture, and shows it fails closed before any side effect. If a null result has more than one plausible cause, it is INCONCLUSIVE.
- **Silent logs.** Do not close a criterion because the log is silent until you have run the interaction that can show the failure. If the condition cannot be reproduced yet, keep the check open or show the same structure as a working baseline.

## Why the acceptance test stays in game

The engine has a script test framework (`class TestHarness` at `P:\scripts\2_gamelib\tests\testingframework.c:137`, `class TestBase` at `:181`), but its tests run only inside a running game, so they cannot check a spec before the build. The verification plan in the spec takes the place of writing tests first, and the in-game gate stays the acceptance test. DayZ features are often all or nothing (a vehicle drives or it does not), so scenarios keep their priorities but are not split into stories shipped one by one.

## How it fits the rest

- The plan comes first (`dayz-mod-architect`); write the spec right after it, and settle any guess that decides correctness with the user before coding. Anything beyond the request still needs the user's say first (Tier 1).
- Every claim about existing code carries a `path:line` you opened before any spec text is written: writing a spec is itself a step that can invent things.
- For data-critical mods the spec comes first, and its crash recovery and admin scenarios feed the data audit (`skills/_shared/persistence/data-audit.md`).
- The build, load and ship loop afterwards is `/dayz-gate build`, `/dayz-build-pbo`, `/dayz-launch-test` and `/dayz-release-pack`.
