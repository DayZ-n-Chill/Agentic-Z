# Feature spec template

The template `dayz-feature-spec` Step 1 fills in: one copy per feature, kept next to the plan in `output/<ModName>-plan/`. Fill it in before writing code and keep it short. Delete the guidance lines in square brackets before marking it Ready. Skip the template entirely for a one-line typo or a trivial reversible tweak.

```markdown
# Feature spec: [FEATURE NAME]

**Mod / PBO**: [for example MyMod.pbo]
**Date**: [YYYY-MM-DD]
**Status**: Draft | Ready-to-implement | Implemented | Verified-in-game
**Plan**: [link to the plan or handoff section this comes from, for example output/<ModName>-plan/plan.md]

## Context / why

[1 to 3 lines: the problem this solves and why now. No implementation detail.]

## Acceptance scenarios (mandatory)

Each scenario is Given/When/Then with concrete in-game repro steps. "It works" is not a scenario.

1. **Given** [initial state, for example "player spawned next to a placed WoodenCrate"],
   **When** [action, for example "player fires one round"],
   **Then** [observable outcome, for example "the bolt selection moves back and a casing ejects toward -Z"].
   - **Repro in game**: [spawn what / do what / observe what: the exact steps for the batched in-game session]

2. **Given** ... **When** ... **Then** ...
   - **Repro in game**: ...

## Success criteria (mandatory)

Measurable, and independent of the implementation where possible. No vague adjectives.

- **SC-001**: [for example "0 `Error` lines in `script_*.log` during the scenario"]
- **SC-002**: [for example "hands sit less than 0.5 cm from the grip memory point"]
- **SC-003**: [for example "the vehicle reaches at least X km/h on flat terrain within Y s"]

## Scope: out of scope (mandatory)

- [Explicit non-goals: what this feature does NOT do, so the analyze gate and reviewers do not treat their absence as gaps.]

## Assumptions

Mark every guess. If an assumption decides correctness (path, classname, version, format), resolve it with the user now; do not defer it to the code.

- **ASSUMED**: [for example "inherits from Inventory_Base, not Container_Base"] - [resolve, or defer and say why]
- **ASSUMED**: ...

## Forward contract

Every symbol the next phase or another consumer reads. Each one is a verified `path:line` or is marked `[UNVERIFIED]`. The analyze gate treats an `[UNVERIFIED]` reference as CRITICAL.

| Consumer | Symbol it reads | Kind | Verify status |
|---|---|---|---|
| model.cfg | `bolt` | selection | `Model.p3d` LOD0 selection `[UNVERIFIED]` |
| config.cpp | `DamageZones.Engine` | class | (the vanilla line you opened; see the worked example below) |
| config.cpp | `hiddenSelections[0]` | texture slot | `[UNVERIFIED]` |
| stringtable | `STR_MYMOD_ACTION` | key | `stringtable.csv:12` |

## Verification plan

For each criterion, how it will be checked. Prefer offline checks (they cost no in-game cycle); batch the in-game checks into one session.

| Criterion | Verification | Where |
|---|---|---|
| SC-001 | scan `script_*.log` for `Error` | offline, after the test (`/dayz-gate ingame` reads the same logs) |
| SC-002 | py3d distance between the grip point and the hand bone | offline |
| Scenario 1 | fire and observe bolt and casing | in game (batched session) |

## Open questions / needs clarification

- [Anything blocking that must be answered before implementing. Ask the user; do not guess.]
```

## Worked example of a verified forward-contract row

A verified row names the file and line that was opened. For a vehicle that inherits the engine damage zone of the vanilla hatchback, the row reads: consumer `config.cpp`, symbol `DamageZones.Engine`, kind class, verify status `P:\DZ\vehicles\wheeled\config.cpp:2170` (`class Engine` inside the `DamageZones` of `OffroadHatchback`, whose class opens at `:1250`).
