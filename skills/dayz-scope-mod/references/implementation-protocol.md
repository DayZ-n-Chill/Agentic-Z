# Implementation protocol

How to write and fix the code of a DayZ mod once the plan and the spec exist: what to load first, how to check every API before using it, the short audit after each file, the client and server data map, checkpoints, the two-tree question, interval changes, the bug ledger and the handoff document. It says how to work, not what to write; the domain knowledge lives in the packs under `skills/_shared/`.

The order around it: the questions in `questions-before-building.md`, then the feature spec (`scoping-a-feature.md`), then this protocol. Do not run it for a one-line change.

Where one of its rules repeats a Tier 2 rule or a pack, the Tier 2 file or the pack wins on detail and is named. A fact with a `P:\` citation was read in that vanilla file; a fact marked measured was seen in a running game or a mod project and is not checked on `P:\`.

| Question | File |
|---|---|
| What do I check in a `config.cpp`, a script, a networked entity, a layout, an action, a `.rvmat`, a save and load pair, or a refactor? | `skills/dayz-build-pbo/references/file-checklists.md` |
| Which mistakes keep coming back (E01 to E35), and what is the correct form of each? | `skills/dayz-launch-test/references/error-catalog.md` |
| What does an offline check prove, and what can only the engine show? | `skills/dayz-build-pbo/references/script-linter-and-compile-gate.md`, "Offline gates: structure is not behaviour" |
| The feature does not work and the log is clean: in what order do I look? | `skills/dayz-launch-test/references/debug-protocol.md` |
| How do I run the fast DayZDiag loop, and when do I stop iterating? | `skills/dayz-launch-test/references/test-loop.md` |
| How do I rate the severity of an audit finding? | `skills/dayz-launch-test/references/audit-escalation.md` |
| Which skill does each step of the mod loop, from scope to Workshop? | `skills/dayz-launch-test/references/mod-loop.md` |

## Before any code

- [ ] Is there an approved plan or design? If not, plan first (`dayz-mod-architect` writes `output/<ModName>-plan/plan.md`).
- [ ] For a placeable or usable object: did the user answer the questions in `questions-before-building.md`?
- [ ] Which packs and skills apply? Load them now; do not work from memory:
  - Enforce Script: `skills/_shared/enscript/README.md`, `skills/_shared/enscript-style.md`, `skills/_shared/enscript/depth/`
  - UI and layouts: `skills/_shared/conventions/ui.md`, `skills/_shared/ui/README.md`
  - Particles: `/dayz-particles`
  - 3D models: `skills/_shared/models/`
  - PBO packing: `/dayz-build-pbo` and its `references/` folder
  - Physics, collision, raycasts: `skills/_shared/physics/`
  - Sound and `CfgSoundSets`: `skills/_shared/audio-fx/`
  - AI, infected and creature behaviour: `skills/_shared/ai/`
  - Build, deploy and launch: `/dayz-launch-test` and its `references/` folder, `/dayz-gate`
- [ ] Is vanilla or mod reference code at hand for the key patterns? Vanilla is on `P:\`; for another mod's code, ask the user.
- [ ] List every file to write or fix, in dependency order.

## For each file

### Write or edit it

Follow the style guide and the packs. If a function, class, method or parameter is not in a loaded pack, not in vanilla or mod code you have opened, and not checked, stop. Then, in this order:

1. Grep `P:\scripts\` for the name and open the hit (the Tier 2 search rule; `/dayz-ask` does it for a one-off question).
2. Check the reference files of the loaded skills and packs.
3. Ask the user for a vanilla or mod example, or search online for the exact API.
4. Mark it ASSUMED in the short audit.

Never use a function because it makes sense that it would exist (E08).

### Short audit

After each file, write:

```markdown
## Mini-audit: [filename]
| API or function      | Source                              | Status   |
|----------------------|-------------------------------------|----------|
| CreateObjectEx       | P:\scripts\... path:line            | VERIFIED |
| SomeWidget.SetColor  | skills/_shared/ui/ pack file        | VERIFIED |
| entity.GetSomeMethod | not found                           | ASSUMED  |
```

With more than two items ASSUMED, stop and resolve them before going on.

### Offline lint

Run `/dayz-lint <ModName>` (its second stage is the script validator). A failure blocks. It is the offline layer only; behaviour in game is checked separately.

### The checklist for the file type

`skills/dayz-build-pbo/references/file-checklists.md`: `config.cpp`, Enforce Script, networking, UI and layout, actions, `.rvmat`, persistence, edge cases, and state after a refactor.

## Client and server data map

Fill in this table before writing any feature that involves entity state, actions or UI:

```markdown
| Data needed        | Client? | Server? | Bridge                      |
|--------------------|---------|---------|-----------------------------|
| (one row per item) |         |         | sync variable / RPC / cache |
```

Rules it must meet:

- Sync variable types are `Bool`, `BoolSignal`, `Int`, `Float` and `Object` only (`RegisterNetSyncVariableBool` starts the list at `P:\scripts\3_game\entities\entityai.c:2832`). There is no `RegisterNetSyncVariableString`. Pattern file: `skills/_shared/enscript/patterns/netsync.md`.
- Client and server register the same variables in the same order. A mismatch corrupts all synced data with no error (E17; not checked on `P:\`, because the stream layout is native).
- `ActionCondition()` runs on both sides: on the client to list the action, and on the server as the start check (`skills/_shared/conventions/scripts.md`, "What the server must validate"). So it may read only data both sides have; a client-only cache passes the menu and the server then rejects the start silently.
- Since 1.30 the widget can still show an action whose `CanBeStarted()` is false, and the client then never calls `ActionStart` (`P:\scripts\4_world\classes\useractionscomponent\actionmanagerclient.c:336`). Info actions return false on purpose (E22).
- `OnStart`, `OnFinish` and `OnUpdate` with the `Server` suffix run on the server. Use server-only data there.
- A string needed on the client: fill a client cache with a `ScriptRPC`, or encode it as an integer and send it through a sync variable. For data read inside `ActionCondition`, the sync variable is the only safe route, because both sides must read it (E11).
- If you are not sure the data is on the client, treat it as not there.

Who owns which state, and which side check to use, is in `skills/_shared/conventions/scripts.md`, "Which code runs where".

## Checkpoints

Write a checkpoint after every two or three files, when you are producing code faster than you are thinking about it, after more than 15 exchanges of implementation, and when you are unsure about something written five or more messages ago:

```markdown
## CHECKPOINT
### Done:
  file1.c - status
  file2.c - status
### Pending:
  file3.c - what is needed
### New uncertainties:
  [things found that are not in the plan]
### Context: [low / medium / high / critical]
  Recommendation: [continue / finish current file / stop and hand off]
```

At high context, finish the current file, write a checkpoint and recommend a new session. At critical context, stop at once and write the handoff document below. Never write code past high context; quality drops (E09).

## Debug and fix

When something does not work after it was written, follow `skills/dayz-launch-test/references/debug-protocol.md` (six layers from the top down, probe rules, splitting the feature in halves). Propose the fix and say why before applying it; below 90 % confidence, ask the user first; after a fix, run the edge case checklist again. For a log that already names the error use `/dayz-gate`, and hand a new error line to `dayz-mod-debugger`.

Two rules apply before a debug cycle starts:

- **Keep structural changes apart.** Keep physics, inheritance and `SimulationModule` changes apart from feature changes, and validate each structural block on its own. Do not approve a `modded` or derived class until it has passed CfgConvert, a real compile and the in-game gate.
- **Close one bake before the next.** Before another bake of the same `.p3d` or `.pbo`, close the pending check of the previous bake, or declare it blocked with the cause. Piled-up changes make the next verdict ambiguous.

## Two trees of one mod

When a mod has two trees side by side (the one that is built and a working copy beside it, such as `<Mod>/` and `<Mod>_dev/`), every `config.cpp`, `model.cfg` or script value you quote as fact names the tree it came from. Before quoting:

1. Confirm which tree is built: the one the user builds, signs and deploys. Its `$PBOPREFIX$` holds the real path, not one ending in `_dev`.
2. Read the config from that tree, not from the working copy.
3. If the two differ, report the difference as a finding (the working copy may need updating). Never quietly pick one.

In this repo there is one tree per mod, `workspace/<ModName>/`, reached by the engine through the `P:\<ModName>\` junction, so the question arises only for an imported project that brings its own second tree.

## Changing a timer interval

Measured on a power grid mod: a write-behind flush constant went from 30 s to 5 s, and a 16-check verification script then failed on its schedule map, because it had the expected call counts written in for the old value (2 calls in a 60,000 ms window, now 12; 10 in 300,000 ms, now 60). The fix was to update the script's two expected maps, not the mod.

When a change touches a `*_MS` or `*_S` constant that feeds a periodic scheduler or timer, before you run the build or verify checks:

1. Grep the mod's verification scripts (its `verify_*.py` tools, its tests) for counts or intervals of that callback written in by hand: expected maps, saved cadence snapshots.
2. Work out the expected count as the window divided by the new interval, and update the script with a minimal edit and a comment that gives the reason.
3. Confirm that only that callback differs; every other count in the map must match exactly. If another callback differs, a cadence changed that nobody intended; investigate before touching the script.
4. A check that fails because of a deliberate interval change is not a code failure but an outdated script, and updating it is part of closing the batch.

Scheduling patterns for the mod itself are in `skills/_shared/enscript/patterns/scheduler.md`.

## Bug ledger

Every new symptom a player can see gets a row in the mod's bug ledger (`bugs.md`, kept with the plan in `output/<ModName>-plan/`) before the next debug cycle. Search the ledger's alias fields first. A known symptom that returns updates its existing row; it is never filed as a new bug.

A deployed fix records `F@<hash>`, but that does not mean fixed. Close the row only with a named check result or the user's verdict on that exact build. Silence settles a reported symptom only when the conditions that showed it were run again and the length of the observation is recorded.

## Handoff document

When a session ends in the middle of an implementation, write:

```markdown
# Handoff: [Mod] - session [N]

## Context
- Plan: [file]
- Skills and packs needed: [list]

## Done
1. path/file1.c - status, caveats
2. path/file2.c - status, caveats

## Pending
3. path/file3.c - what, dependencies, uncertainties

## Unresolved
- [ ] uncertainty 1

## Errors found (add to the error catalog if they recur)

## Notes for the next session
```

Keep it with the plan in `output/<ModName>-plan/`. A rule that turns out to be wrong or missing goes into the right tier through `/dayz-record-correction`.
