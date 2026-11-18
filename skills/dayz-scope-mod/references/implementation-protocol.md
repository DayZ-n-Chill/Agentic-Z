# Implementation protocol: from an approved spec to written code

How to write and fix the code of a DayZ mod once the plan and the spec exist: what to load first, how to check every API before using it, the mini-audit after each file, the client and server data map, checkpoints, the dev tree question, scheduler harness counts, the live bug ledger and the handoff document. It says how to work, not what to write; the domain knowledge lives in the packs under `skills/_shared/`.

Order of the steps around it: the questions in `pre-implementation-grill.md`, then the feature spec ("Scoping a feature" in this skill's `SKILL.md`), then this protocol. Do not apply it to a one-line change.

Where one of its rules repeats a Tier 2 rule or a pack, the Tier 2 file or the pack wins on detail and is named. A fact with a `P:\` citation was read in that vanilla file; "measured" facts were observed on a running game or in a mod project and are not yet checked on `P:\`.

Related files elsewhere:

| Question | File |
|---|---|
| What do I check in a `config.cpp`, a script, a networked entity, a layout, an action, a `.rvmat`, a save and load pair, or a refactor? | `skills/dayz-build-pbo/references/file-checklists.md` |
| Which mistakes keep coming back (E01 to E35), and what is the correct form of each? | `skills/dayz-launch-test/references/error-catalog.md` |
| What does an offline gate prove, and what only the engine can show? | `skills/dayz-build-pbo/references/script-linter-and-compile-gate.md`, "Offline gates: structure is not behaviour" |
| The feature does not work and the log is clean: in what order do I look? | `skills/dayz-launch-test/references/debug-protocol.md` |
| How do I run the fast DayZDiag loop, and when do I stop iterating? | `skills/dayz-launch-test/references/test-loop.md` |
| How do I label the severity of an audit finding? | `skills/dayz-launch-test/references/audit-escalation.md` |
| Which skill does each step of the mod loop, from scope to Workshop? | `skills/dayz-launch-test/references/mod-loop.md` |

## 1. Activation check

Before writing or fixing any code:

- [ ] Is there an approved plan or design? If not, plan first (`dayz-mod-architect` writes `output/<ModName>-plan/plan.md`).
- [ ] For a placeable or usable object: were the questions in `pre-implementation-grill.md` answered by the user?
- [ ] Which packs and domain skills apply? Load them now; do not work from memory:
  - Enforce Script: `skills/_shared/enscript/README.md`, `skills/_shared/enscript-style.md`, `skills/_shared/enscript/depth/`
  - UI and layouts: `skills/_shared/conventions/ui.md`, `skills/_shared/ui/README.md`
  - Particles: `/dayz-particles`
  - 3D models: `skills/_shared/models/`
  - PBO packaging: `/dayz-build-pbo` and its `references/` folder
  - Physics, collision, raycasts: `skills/_shared/physics/`
  - Sound and `CfgSoundSets`: `skills/_shared/audio-fx/`
  - AI, infected and creature behaviour: `skills/_shared/ai/`
  - The build, deploy and launch loop: `/dayz-launch-test` and its `references/` folder, `/dayz-gate`
- [ ] Is vanilla or mod reference code at hand for the key patterns? Vanilla is on `P:\`; for another mod's code, ask the user.
- [ ] List every file to write or fix, in dependency order.

## 2. Per-file protocol

For each file written or changed:

### 2a. Write or edit the file

Follow the style guide and the packs. When in doubt about any function, class, method or parameter:

**The golden rule: if it is not in a loaded pack, not in vanilla or mod code you have opened, and you have not verified it, stop.**

When stopped, in this order:

1. Grep `P:\scripts\` for the name and open the hit (the Tier 2 search rule; `/dayz-ask` does it for a one-off question).
2. Check the reference files of the loaded skills and packs.
3. Ask the user for a vanilla or mod example, or search online for the exact API.
4. Mark it ASSUMED in the mini-audit.

Never use a function because "it makes sense that it would exist" (E08).

### 2b. Mini-audit

After each file, write:

```
## Mini-audit: [filename]
| API or function      | Source                              | Status   |
|----------------------|-------------------------------------|----------|
| CreateObjectEx       | P:\scripts\... path:line            | VERIFIED |
| SomeWidget.SetColor  | skills/_shared/ui/ pack file        | VERIFIED |
| entity.GetSomeMethod | not found                           | ASSUMED  |
```

**Hard rule: with more than two items ASSUMED, do not go on. Resolve them first.**

### 2c. Offline lint

Run `/dayz-lint <ModName>` (its second stage is the script validator). A failure blocks. It is the offline layer only; behaviour in game is checked separately.

### 2d. Run the checklist for the file type

`skills/dayz-build-pbo/references/file-checklists.md`: `config.cpp`, Enforce Script, networking, UI and layout, actions, `.rvmat`, persistence, edge cases, and state coherence after a refactor.

## 3. Client and server data map

**Mandatory before writing any feature that involves entity state, actions or UI.**

Fill in this table:

```
| Data needed        | Client? | Server? | Bridge                    |
|--------------------|---------|---------|---------------------------|
| (one row per item) |         |         | sync variable / RPC / cache |
```

Hard rules:

- **Sync variable types** are `Bool`, `BoolSignal`, `Int`, `Float` and `Object` only (`RegisterNetSyncVariableBool` starts the list at `P:\scripts\3_game\entities\entityai.c:2832`). There is no `RegisterNetSyncVariableString`. Pattern file: `skills/_shared/enscript/patterns/netsync.md`.
- **Bitstream alignment.** Client and server register the same variables in the same order. A mismatch corrupts all synced data with no error (E17; not yet checked on `P:\`, the stream layout is native).
- **`ActionCondition()` runs on both sides:** on the client to list the action, and on the server as the start gate (`skills/_shared/conventions/scripts.md`, "What the server must validate"). So `ActionCondition` may read only data both sides have; a client-only cache passes the menu and the server then rejects the start silently.
- Since 1.30 the widget can still show an action whose `CanBeStarted()` is false, and the client then never calls `ActionStart` (`P:\scripts\4_world\classes\useractionscomponent\actionmanagerclient.c:336`). Info actions return false on purpose (E22).
- `OnStart`, `OnFinish` and `OnUpdate` with the `Server` suffix run on the server. Use server-only data there.
- A string needed on the client: fill a client cache with a `ScriptRPC`, or encode it as an integer and send it through a sync variable. For data read inside `ActionCondition`, the sync variable is the only safe route, because both sides must read it (E11).
- **If you are not sure the data is on the client, treat it as not there.**

Who owns which state, and which side guard to use, is in `skills/_shared/conventions/scripts.md`, "Which code runs where".

## 4. Checkpoints

Write a checkpoint:

- after every two or three files,
- when you are producing code faster than you are thinking about it,
- after more than 15 exchanges of implementation,
- when you are unsure about something written five or more messages ago.

```
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

Context rules:

- High: finish the current file, write a checkpoint, recommend a new session.
- Critical: stop at once and write the handoff document (section 9).
- Never write code past high context. Quality drops (E09).

## 5. Debug and fix

When something "doesn't work" after it was implemented, follow `skills/dayz-launch-test/references/debug-protocol.md` (six layers top down, probe rules, component bisection). Propose the fix and say why before applying it; under 90% confidence, ask the user first; after a fix, run the edge-case checklist again. For a log that already names the error use `/dayz-gate`, and hand a new error line to `dayz-mod-debugger`.

Two rules apply before a debug cycle starts:

- **Isolate structural changes.** Keep physics, inheritance and `SimulationModule` changes apart from feature changes, and validate each structural block on its own. Do not approve a `modded` or derived class until it has passed CfgConvert, a real compile and the in-game gate.
- **Close one bake before the next.** Before another bake of the same `.p3d` or `.pbo`, close the pending gate of the previous bake, or declare it blocked with the cause. Do not pile up changes that make the next verdict ambiguous.

## 6. Dev tree and compilable tree

When a mod has two parallel trees (the one that is built and a working copy beside it, such as `<Mod>/` and `<Mod>_dev/`), every `config.cpp`, `model.cfg` or script value quoted as ground truth names the tree it came from. Before quoting:

1. Confirm which tree is the compilable one: the one the user builds, signs and deploys. A hint: it has the `$PBOPREFIX$` with the canonical path, not one ending in `_dev`.
2. Read the config from the compilable tree, not from the working copy.
3. If the two differ, report the difference as a finding (the working copy may need a rebase). Never quietly pick one as the truth.

In this repo there is one tree per mod, `workspace/<ModName>/`, reached by the engine through the `P:\<ModName>\` junction, so the question arises only for an imported project that brings its own second tree.

## 7. Changing a scheduler interval: update the harness counts

Measured on a power-grid mod: a write-behind flush constant went from 30 s to 5 s. A verification gate of 16 checks then failed on its schedule map, because the harness had the expected call counts hard-coded for the old value (2 calls in a 60,000 ms window, now 12; 10 in 300,000 ms, now 60). The fix was to update the harness's two expected maps, not the mod.

When a code change touches a `*_MS` or `*_S` constant that feeds a periodic scheduler or timer, before calling the build or verify gate a pass:

1. Grep the verification harnesses (the mod's `verify_*.py` tools, its tests) for hard-coded counts or intervals of that callback: expected maps, frozen cadence snapshots.
2. Recompute the expected count as window divided by the new interval, and update the harness with a minimal edit and a comment that names the reason.
3. Confirm that only that callback differs; every other count in the map must match exactly. If another callback differs, a cadence changed that nobody intended: investigate before touching the harness.
4. A gate that fails because of a legitimate interval change is not a code failure; it is an outdated harness, and updating it is part of closing the batch.

Scheduling patterns for the mod itself are in `skills/_shared/enscript/patterns/scheduler.md`.

## 8. Live bug ledger

Every new symptom a player can see gets a row in the mod's bug ledger (`bugs.md`, kept with the plan in `output/<ModName>-plan/`) before the next debug cycle. Search the ledger's alias fields first. A regression of a known symptom updates the existing row; it is never filed as a new bug.

A deployed fix records `F@<hash>`, but that token does **not** mean fixed. Close the row only with a named gate result or the user's verdict on that exact hash. Silence settles a reported symptom only when the regime that showed it was exercised and the observation window is recorded.

## 9. Handoff document

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
