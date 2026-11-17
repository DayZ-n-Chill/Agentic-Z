---
name: dayz-feature-spec
description: "Defines and quality-gates a non-trivial DayZ feature before it is implemented. Produces measurable success criteria, Given/When/Then scenarios with in-game repro steps, resolved ASSUMED markers and a forward contract for every classname, model.cfg selection, .p3d proxy, stringtable or layout key and injected object the next phase reads; then runs a spec checklist and a read-only consistency gate over spec, plan, task list and code for coverage gaps, contradictions, terminology drift and unverified references. Use for a feature spec, definition of done, acceptance criteria, a spec checklist, a consistency or analyze gate, 'before implementing', or 'is it ready to code?' (also 'spec de la feature', 'definición de done', 'criterios de aceptación', 'antes de implementar', '¿está listo para codear?'). Run it after planning and before dayz-mod-workflow; add rigorous-data-audit for data-critical work."
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# DayZ feature spec

Follow `skills/_shared/dayz-conventions.md`. This skill is reference only; it runs no scripts, so there is no preflight gate. `dayz-mod-architect` reads it when a plan needs a definition of done, and any worker reads it before a change that touches more than one file.

A feature spec says what done means and how it will be checked, before any code is written. Two gates then keep an expensive in-game test from being spent on a spec that could never pass: a checklist on the spec itself, and a read-only consistency pass over the spec, the plan, the task list and the code.

## When to use it and when to skip it

Use it before implementing:

- a new mod feature, or any change that touches more than one file,
- anything data-critical (persistence, progression); then also run `rigorous-data-audit`,
- anything where "done" is not obvious, or where a later phase or another consumer reads what this phase produces (the forward contract below).

Skip it for a one-line typo or a trivial reversible tweak (a default keybind, a stringtable key, a path slash). Small reversible changes go straight in; a spec for them is ceremony.

## The flow

```
plan  ->  Step 1 spec + Step 2 checklist (gate)  ->  code  ->  Step 3 analyze gate (gate)  ->  dayz-mod-workflow  ->  in-game test
```

In this repo the plan is `output/<ModName>-plan/plan.md`, written by `dayz-mod-architect` together with `behavior-checks.json` (and `visual-shots.json` when something is visible). Keep the spec in the same folder. The in-game test is one batched session: `/dayz-gate ingame`, `/dayz-gate behavior` and `/dayz-gate visual`, plus whatever a person has to try by hand. The two gates exist so that nothing reaches that session with a criterion nobody can measure, a cross-file reference nobody opened, or a contradiction between spec and code.

## References

| Question | File |
|---|---|
| What does the spec look like, section by section? | `references/spec-template.md` |
| Is this spec ready to implement? | `references/spec-checklist.md` (18 checks) |
| Do spec, plan, task list and code agree before the in-game test? | `references/analyze-gate.md` |

## Step 1: write the feature spec

Fill in `references/spec-template.md`. It is short on purpose. Four sections carry the DayZ-specific weight:

- **Acceptance scenarios.** Given/When/Then, each with concrete in-game repro steps (spawn what, do what, observe what). "It works" is not a scenario.
- **Success criteria.** Measurable and, where possible, independent of the implementation. DayZ examples: "the bolt moves when firing", "0 `Error` lines in `script_*.log` after the test", "hands within 0.5 cm of the grip", "the car reaches at least X km/h on flat ground". Vague adjectives ("looks good", "works") are not criteria.
- **Assumptions.** Mark every guess `ASSUMED`. If an assumption decides whether the work is correct (a path, a classname, a version, a format), resolve it with the user now, not after coding (ask with AskUserQuestion where the agent has it). Saying a risk out loud is not managing it.
- **Forward contract.** List every symbol the next phase or another consumer reads: `config.cpp` classnames, `model.cfg` selections and bones, `.p3d` proxy paths, `hiddenSelections`, stringtable keys, layout names. Each one carries a verify status: a `path:line` you opened (Tier 2, "Cite, then verify"), or `[UNVERIFIED]`. The analyze gate treats an `[UNVERIFIED]` reference as CRITICAL. This is the class of bug the contract exists to catch: a proxy path that points at a file that does not exist, and selections `model.cfg` needs that the model does not have. Before spending an in-game test on changing a field (a `config.cpp` value, a JSON setting, a script member), grep for the code that reads it, not counting its declaration, default, clamp and serialization. Changing a field nobody reads changes nothing in game; when the reader runs only under a condition, show from the test's logs that the condition was reached.

## Step 2: spec quality checklist

Before writing any code, run `references/spec-checklist.md` against the spec. It checks the spec the way tests check code: every criterion measurable, every scenario reproducible, every `ASSUMED` resolved or flagged, every cross-file reference verified, the scope boundary explicit, and every criterion attacked with a broken build that would still pass it. A spec that fails the checklist is not ready to implement. This gate checks the wording; `rigorous-data-audit` checks the code.

## Step 3: analyze gate

After the code and the task list exist and before the in-game test, run `references/analyze-gate.md`. It is a read-only pass over spec, plan, task list or handoff, code and the repo rules (Tier 1 and Tier 2). It reports coverage gaps, contradictions, terminology drift, duplicate or near-duplicate requirements, unverified forward-contract references and rule violations, each with a severity (CRITICAL, HIGH, MEDIUM, LOW). The gate changes no file; it writes a report and offers fixes for the user to approve.

Coverage means every acceptance criterion has a verification path: an offline check (`/dayz-lint`, a grep, a Python or py3d script, a log scan) or a place in the batched in-game session. A criterion with no verification path is a CRITICAL gap, and CRITICAL findings block the in-game session.

This gate works on the documents. Tracing an invariant to every call site in the code and walking the feature end to end are still done on the code itself (`dayz-mod-workflow`).

## Forward contract for injected objects

When a plan injects an object that replaces another implementation (a planner, a bridge, a transport, a repository), the forward contract lists every field and method the consumer reads, not only the field that motivated the test double. Grep every access on the injected value, and prefer the existing result type over a partial look-alike. When a test build changes a value to compare it with the original, apply the consumer's clamp rules first and record in the test notes the value the code actually uses, not the one written in the config: a value the consumer clamps back to the original is no change at all.

The failure is concrete: a consumer can read `.status.value`, `.proposal` and `.source` when the plan mentions only `.proposal`, and the partial object then fails at run time although it satisfies the written spec.

### Eligibility symmetry across push and pull

Before a forward contract says "use the same bound or rule as X", list every existing predicate that answers the same eligibility, visibility or authorization question. If full sync, incremental broadcast and request handling disagree, the contract names the chosen invariant and justifies it; it does not copy one route because it is nearest.

When the server pushes notice of data and also serves that data on request, the pull must not be stricter than the push unless the contract defines a recoverable exception. Add an acceptance case where the direct player-to-object distance fails but eligibility through a connected endpoint passes: a pushed notice must lead to a successful pull. If the defect was in the contract, amend the contract with a changelog alongside the code; a code-only fix leaves the trap for the next phase.

## A search with no hits does not prove absence

Before recommending an API, open the cited vanilla source, record its `path:line`, and read the surrounding `#ifdef` state, the parent chain and the config namespace. In this repo that is the Tier 2 search rule: Grep `P:\scripts\` for the name, then open the hit. Two traps:

- A hit can be dead code. Grep also finds commented-out declarations and code under a define the build does not set. Vanilla keeps such lines: `disableBaseDecay` is assigned only in a commented-out line of `InitServer` (`P:\scripts\3_game\cfggameplaydatajson.c:48`), while the member itself is live at `:60`.
- No hit is not proof either. An API index that strips comments gives zero records for a commented-out declaration and for a missing one alike. Until an index reports `active`, `commented` or `missing`, a zero result only says "open the source".

An index is supporting evidence. It is not a gate that blocks unrelated work such as the `.layout` viewer or a UI evidence loop.

## Decision tests and probes

Rules for tests and probes that decide a design question:

- **Three verdicts.** Every decision test defines PASS, FAIL and INCONCLUSIVE (setup failed), with an explicit precondition that separates the third from the other two. Fix the metrics and the matching rule before running the test.
- **Held inputs.** Every probe used to decide architecture keeps its inputs held during the window, uses a mechanically complete fixture, and proves it fails closed before any side effect. If a null result has more than one plausible cause, classify it INCONCLUSIVE.
- **Silent logs.** Do not close or dismiss a criterion because the log is silent until you have run the interaction that can reveal the failure. If the condition cannot be reproduced yet, keep the gate open or show structural parity with a working baseline.

## Raw producer records and canonical derived records

When the run-time producer cannot derive a canonical output enum because an offline verifier owns that decision, the forward contract defines two record types from the start:

- `X_RAW` is emitted by the run-time producer. Its fields and enums hold only facts that actor can observe directly.
- `X` is the canonical record emitted by the named offline derivation step. Its contract owns the derived enum, such as `GREEN`, `RED` or `INCONCLUSIVE`.

Name the emitter of both records and state the transformation from `X_RAW` to `X`. Never make the raw producer satisfy the canonical enum by inventing a sentinel outside the contract such as `RAW-DATA-ONLY`; that guarantees an enum violation instead of representing a third verdict. The analyze gate treats one record name shared by two emitters, or a derived field assigned to the raw producer, as a forward-contract contradiction.

## What this leaves out of generic spec-driven development

The flow is the specify, clarify, analyze, implement sequence of spec-driven development, cut down to what a DayZ mod needs. Left out on purpose:

- **Test-first, red-green and contract tests.** The engine has a script test framework (`TestHarness` at `P:\scripts\2_gamelib\tests\testingframework.c:137`, `TestBase` at `:181`), but its tests run only inside a running game, so they cannot gate a spec before the build; the acceptance test stays the in-game gate. The verification path replaces test-first.
- **Each user story as an independent MVP.** DayZ features are often all or nothing (a vehicle drives or it does not; a grip pose is right or wrong). Priorities and scenarios stay; the per-story MVP ceremony does not.
- **A scaffolding CLI and a tech-stack research phase.** The stack is fixed (Enforce Script, `config.cpp`, `model.cfg`, `.p3d`) and so is the toolchain (AddonBuilder, DayZDiag).
- **Exporting tasks to issues, extension marketplaces.** Overkill for one mod.

Do not add generic application scaffolding back in.

## How it fits the other rules and skills

- The plan comes first (`dayz-mod-architect`); run this skill right after it.
- A guess that decides whether the work is correct is settled with the user before coding, not after: Step 1's `ASSUMED` resolution does that at spec time. Anything beyond the request still needs the user's say first (Tier 1, "Never add what wasn't asked for").
- Cite, then verify (Tier 2): every forward-contract reference and cross-file symbol is a `path:line` someone opened.
- Report honestly what was checked and how: the success criteria say it up front.
- `rigorous-data-audit`: for data-critical mods this skill comes first; the spec's crash-recovery and admin scenarios feed that audit.
- `dayz-mod-workflow` takes the approved spec and implements it.
- Writing the spec is itself a generation step, so validate what you found first: every discovery claim carries a verified `path:line` before any spec text is written.
- When the work has to end in a mod that builds, loads and ships (`config.cpp` and `CfgMods`, `requiredAddons`, the PBO and its signature, a boot on a local server, the Workshop), follow the loop in `dayz-mod-dev`.
