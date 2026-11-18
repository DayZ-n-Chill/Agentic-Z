# Spec outline

What a feature spec holds, section by section: one copy per feature, saved as `spec.md` next to the plan in `output/<ModName>-plan/`. Fill it in before writing code and keep it short. Delete the guidance lines in square brackets before marking it Ready. Skip it for a one-line typo or a small reversible tweak. Where it sits in the order of work is in `scoping-a-feature.md`.

```markdown
# Feature spec: [FEATURE NAME]

**Mod / PBO**: [for example MyMod.pbo]
**Date**: [YYYY-MM-DD]
**Status**: Draft | Ready to implement | Implemented | Checked in game
**Plan**: [link to the plan or handoff section this comes from, for example output/<ModName>-plan/plan.md]

## Why

[1 to 3 lines: the problem this solves and why now. No implementation detail.]

## Acceptance scenarios

Each scenario is Given, When, Then, with concrete in-game steps. "It works" is not a scenario.

1. **Given** [starting state, for example "player spawned next to a placed WoodenCrate"],
   **When** [action, for example "player fires one round"],
   **Then** [what you see, for example "the bolt selection moves back and a casing ejects toward -Z"].
   - **In game**: [spawn what, do what, see what: the exact steps for the batched in-game session]

2. **Given** ... **When** ... **Then** ...
   - **In game**: ...

## Success criteria

Measurable, and independent of the implementation where possible. No vague adjectives.

- **SC-001**: [for example "0 `Error` lines in `script_*.log` during the scenario"]
- **SC-002**: [for example "hands sit less than 0.5 cm from the grip memory point"]
- **SC-003**: [for example "the vehicle reaches at least X km/h on flat terrain within Y s"]

## Out of scope

- [What this feature does not do, so the consistency pass and reviewers do not report its absence as a gap.]

## Assumptions

Mark every guess. If an assumption decides correctness (path, classname, version, format), settle it with the user now; do not leave it to the code.

- `ASSUMED` [for example "inherits from Inventory_Base, not Container_Base"] - [settle it, or put it off and say why]
- `ASSUMED` ...

## Forward contract

Every symbol the next phase or another consumer reads. Each is a `path:line` you opened, or is marked `UNVERIFIED`; the consistency pass blocks the in-game session on an `UNVERIFIED` reference.

| Consumer | Symbol it reads | Kind | Status |
|---|---|---|---|
| model.cfg | `bolt` | selection | `Model.p3d` LOD0 selection, `UNVERIFIED` |
| config.cpp | `DamageZones.Engine` | class | (the vanilla line you opened; see the example below) |
| config.cpp | `hiddenSelections[0]` | texture slot | `UNVERIFIED` |
| stringtable | `STR_MYMOD_ACTION` | key | `stringtable.csv:12` |

## How each criterion is checked

Prefer offline checks, which cost no in-game cycle, and batch the in-game checks into one session.

| Criterion | Check | Where |
|---|---|---|
| SC-001 | scan `script_*.log` for `Error` | offline, after the test (`/dayz-gate ingame` reads the same logs) |
| SC-002 | py3d distance between the grip point and the hand bone | offline |
| Scenario 1 | fire and watch the bolt and casing | in game (batched session) |

## Open questions

- [Anything blocking that must be answered before implementing. Ask the user; do not guess.]
```

## A forward contract row you opened

A checked row names the file and line you opened. For a vehicle that inherits the engine damage zone of the vanilla hatchback, the row reads: consumer `config.cpp`, symbol `DamageZones.Engine`, kind class, status `P:\DZ\vehicles\wheeled\config.cpp:2170` (`class Engine` inside the `DamageZones` of `OffroadHatchback`, whose class opens at `:1250`).
