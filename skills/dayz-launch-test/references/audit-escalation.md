# Audit severity and independent auditors

How to label the severity of an audit finding on a DayZ mod, how to label the severity of something missing, and how to keep parallel auditors from agreeing on the same mistake. The implementation protocol (`skills/dayz-scope-mod/references/implementation-protocol.md`) points here. To run a data critical audit use `_shared/persistence/deep-audit.md` and `_shared/persistence/data-audit.md`; this file covers only the labels and the independence.

## Name what actually happened

Audit findings get inflated when a log message is read as a behaviour without checking: `String CORRUPTED` in a power grid mod's log was filed as "P1, crash" when the server kept running after a recoverable VM exception. Likewise "Server boots: NO" in a before and after table, when the server did boot and only threw an error.

Before you write a finding:

1. Reproduce it on a local server (`/dayz-launch-test`).
2. Log one whole cycle of the bug: load, run, autosave, reload.
3. Name it with one of these terms, never "crash" as a catch-all:

| Term | What happens |
|---|---|
| crash | The process dies, the server drops, a restart is needed. |
| VM exception | An Enforce Script VM exception, log spam, execution goes on. |
| corruption | Bad data persists and the code runs with it. |
| degradation | The feature works worse but runs. |
| cosmetic | Visual only, no effect on function. |

`/dayz-gate` already separates these in its reports: a `crash*.log` or a process exit is a crash, and a script error line is triaged on its own.

## Grade what is missing by what its absence does

The section above grades a bug that was seen. A gap audit grades something that is not there, and "the feature is incomplete" is not the same as "its absence crashes". Label each gap by whether lacking it crashes or stops loading, or only leaves a feature unfinished. An engine minimum deferred as a feature can be a hidden crash: on a quad vehicle mod `DamageSystem` was filed as a later "damage feature", and without it the game logs `[Object::GetMaxHealth] No DamageSystemData` and crashes as soon as anything touches health (admin tools, damage, collision, sync).

Engine minimums to check early, apart from the feature list:

| Subsystem | Minimum | Without it | Read |
|---|---|---|---|
| Vehicle (`CarScript`) | `class DamageSystem { class GlobalHealth { class Health { hitpoints; healthLevels[]; }; }; }`. Vanilla `OffroadHatchback` declares `GlobalHealth` first and `DamageZones` after it (`P:\DZ\vehicles\wheeled\config.cpp:1540` to `:1577`). Check custom wheel classes too. | Any `GetMaxHealth` or `SetHealth` crashes (measured in game). Full `DamageZones` are a feature; `GlobalHealth` is the floor. | `_shared/vehicles/damage.md` |
| Vehicle | A constructor that sets the engine sound strings (`m_EngineStart*`). | Broken audio, and possibly an exception from an empty sound set name. | the vehicles pack, `_shared/vehicles/` |
| Model `.p3d` | A Geometry LOD with convex components and mass, and the action selections (`seat_*`, `refill`, doors) in the LOD the cursor resolves (View Geometry for actions, measured in game). | The object does not simulate; actions never show. | `_shared/models/lods.md`, `_shared/physics/collision-lods.md`, `/dayz-p3d-audit` |

When an engine minimum is deferred, put it in the plan as a separate anti-crash item ahead of the full feature, not in the late bucket. A parity audit adds one pass over "engine minimums per subsystem" to the feature checklist, so crashes are not found one at a time in game.

## Keep parallel auditors independent

Four auditor agents on a virtual storage mod agreed on invented findings because they had all read the same conventions document and carried the same bias. The agreement looked like rigour and was coupling.

For a multi-agent audit of DayZ code:

- Each agent checks against its own vanilla source or `path:line`.
- Two agents that read the same document may not cite each other as confirmation.
- At least one agent works adversarially: no access to the conventions document, only the real code, checking the others' findings.
- Recheck a random 20 percent or more of the findings before applying any. If they fail, discard the whole audit, not just the doubtful items; invention is systemic, not per item.

Signs that an audit invented its findings:

- Large round counts ("47 issues found") with no `path:line` per item.
- Defensive OR branches reported as bugs when they are deliberate tolerance, such as a `classify_lod()` helper that accepts both Arma 3 and DayZ LOD bands by design.
- Inflated severity (P1 on items that are P2 or P3); compare with the first section.
- Agreement between agents that should be independent but read the same document: shared bias, not triangulation.

A finding counts as verified, and may be applied, only when all four hold:

1. It has a concrete `path:line` in real code, not in a document.
2. The code that breaks the rule is quoted.
3. The fix is quoted as a diff that applies.
4. At least one agent without the shared context checked it separately.

Otherwise mark it "possible invention" and do not apply it.

In this repo the review gates are separate agents for the same reason: `dayz-mod-reviewer` checks and does not fix, and `dayz-mod-debugger` diagnoses from the logs and names an owner. Check while you work, not only at the end, and report plainly what was and was not checked.
