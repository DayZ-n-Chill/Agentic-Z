---
name: dayz-mod-workflow
description: "Protocol for implementing and debugging a DayZ mod: how to write and fix, not what to write. Covers the client and server data map to fill in before each feature, checking every API before it is used, a mini-audit and a checklist per file type, the recurring error catalog (E01 to E35), the six-layer top-down debug order with component bisection, probe and measurement rules, the DayZDiag test loop, checkpoints and a handoff document when context runs out. Use alongside the domain skills and packs (Enforce Script, UI, particles, models), not instead of them, for 'implement', 'write the code', 'build the mod', 'fix the bug', 'debug this', 'it doesn't work', 'actions not showing', sprint execution, or any move from a plan to code or to a fix. Also for 1.30 workflow changes: CanBeStarted, CCTLiquid, MotorbikeScript and HouseDestructible root classes, cfggameplay ExternalLockData and SandstormData, PluginUndergroundTriggerManager, NVTypes underground and sandstorm values, IsHeadless."
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# DayZ mod implementation and debug protocol

Follow `skills/_shared/dayz-conventions.md`. This skill is reference only; it runs no scripts of its own, so there is no preflight gate. Of the scripts it names, `/dayz-build-pbo` and `/dayz-launch-test` gate on preflight, `/dayz-gate` gates through them, and `/dayz-lint` and `/dayz-logwatch` are on the exception list because they only read files and logs.

It is a process skill. The domain knowledge lives in the packs under `skills/_shared/` and in the domain skills; this skill makes sure that knowledge is applied and that gaps are found before they become bugs. Where one of its rules repeats a Tier 2 rule or a pack, the Tier 2 file or the pack wins on detail and is named.

Until 1.29 the six-layer debug order, the sync variable rules and errors E01 to E20 were the whole contract. Since 1.30 the client also checks `CanBeStarted()` before it starts an action, vanilla water actions use `CCTLiquid`, the Central Economy has `MotorbikeScript` and `HouseDestructible` root classes, and `cfggameplay.json` has lock and sandstorm keys: `references/dayz-1-30-mod-workflow.md`. The 1.29 side of these changes is not on `P:\`, so it is not yet checked on `P:\`.

Marks used in this skill and its references: a fact with a `P:\` citation was read in that vanilla file. "Measured" facts were observed on a running game or in a mod project and are not yet checked on `P:\`, because a source file cannot show them.

## References

| Question | File |
|---|---|
| What do I check in a `config.cpp`, a script, a networked entity, a layout, an action, a `.rvmat`, a save and load pair, or a refactor? | `references/checklists.md` |
| Which mistakes keep coming back, and what is the correct form of each? | `references/error-catalog.md` (E01 to E35) |
| The feature does not work and the log is clean: in what order do I look, how do I place probes, and how do I bisect? | `references/debug-protocol.md` |
| How do I read numbers from a test session without fooling myself (clock offsets, ranges, defect rates)? | `references/measurement-discipline.md` |
| How do I run the fast DayZDiag loop, when do I stop iterating, and which debug tools do the vanilla scripts offer? What changes on Linux? | `references/test-loop.md` |
| Which questions do I settle with the user before writing a placeable or usable object? | `references/pre-implementation-grill.md` |
| How do I label the severity of an audit finding or of something missing, and keep parallel auditors independent? | `references/audit-escalation.md` |
| What did 1.30 change for actions, Central Economy root classes, `cfggameplay.json`, the underground trigger editor, `NVTypes` and the headless guards? | `references/dayz-1-30-mod-workflow.md` |
| What was measured on a running 1.30 server (version define, `FindFile`, `files[]` slashes, compile crashes, load order, Community Framework and Expansion)? | `references/dayz-1-30-server-measured.md` |
| Another session may rewrite this skill while mine runs: how do I pin the version I started with? | `references/concurrent-session-snapshot.md` |

## 1. Activation check

Which step comes first is fixed by the plan, not by this skill: the pre-implementation questions, then the feature spec of `dayz-scope-mod` (its `references/feature-spec.md`), then this skill. Do not declare this skill mandatory for a one-line change.

Before writing or fixing any code:

- [ ] Is there an approved plan or design? If not, plan first (`dayz-mod-architect` writes `output/<ModName>-plan/plan.md`).
- [ ] For a placeable or usable object: were the questions in `references/pre-implementation-grill.md` answered by the user?
- [ ] Which domain skills and packs apply? Load them now; do not work from memory:
  - Enforce Script: `skills/_shared/enscript/README.md`, `skills/_shared/enscript-style.md`, `skills/_shared/enscript/depth/`
  - UI and layouts: `skills/_shared/conventions/ui.md`, `dayz-ui-development`
  - Particles: `/dayz-particles`
  - 3D models: `skills/_shared/models/`, `dayz-model-pipeline`
  - PBO packaging: `/dayz-build-pbo` and its `references/` folder
  - Physics, collision, raycasts: `skills/_shared/physics/`
  - Sound and `CfgSoundSets`: `skills/_shared/audio-fx/`
  - AI, infected and creature behaviour: `skills/_shared/ai/`
  - The build, deploy and launch loop: `/dayz-launch-test` and its `references/` folder, `/dayz-gate`
- [ ] Is vanilla or mod reference code at hand for the key patterns? Vanilla is on `P:\`; for another mod's code, ask the user.
- [ ] List every file to write or fix, in dependency order.
- [ ] Could another session rewrite this skill while you work? Follow `references/concurrent-session-snapshot.md`.

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
| SomeWidget.SetColor  | dayz-ui-development reference       | VERIFIED |
| entity.GetSomeMethod | not found                           | ASSUMED  |
```

**Hard rule: with more than two items ASSUMED, do not go on. Resolve them first.**

### 2c. Offline lint

Run the structural gate described under "Offline gates" below. A failure blocks. It is the offline layer only; behaviour in game is checked separately.

### 2d. Run the checklist for the file type

`references/checklists.md`: `config.cpp`, Enforce Script, networking, UI and layout, actions, `.rvmat`, persistence, edge cases, and state coherence after a refactor.

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
- **`ActionCondition()` runs on both sides:** on the client to list the action, and on the server as the start gate. The server calls `pickedAction.Can(...)` (`P:\scripts\4_world\classes\useractionscomponent\actionmanagerserver.c:168`), and `Can` calls `ActionCondition(player, target, item)` (`P:\scripts\4_world\classes\useractionscomponent\actionbase.c:954`). So `ActionCondition` may read only data both sides have; a client-only cache passes the menu and the server then rejects the start silently. The server does not blindly trust the client's choice.
- Until 1.29 a listed action was assumed startable once `Can()` passed (not yet checked on `P:\`, which holds no 1.29 data). Since 1.30 the widget can still show an action whose `CanBeStarted()` is false, and the client then never calls `ActionStart` (`P:\scripts\4_world\classes\useractionscomponent\actionmanagerclient.c:336`). Info actions return false on purpose (`references/dayz-1-30-mod-workflow.md`).
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
- Critical: stop at once and write the handoff document (section 13).
- Never write code past high context. Quality drops (E09).

## 5. Recurring error catalog

Mistakes made more than once. Check them actively while writing. The full table (error, correct form, where it was seen, the `P:\` evidence) is `references/error-catalog.md`; this is the index:

- **E01** `requiredAddons[]={"DabsFramework"}` instead of the `CfgPatches` class name
- **E02** `imageSets` in `CfgSlots` or at the config root
- **E03** the same variable name in sibling scopes
- **E04** a `.rvmat` `Stage4` placeholder typed from memory
- **E05** a `.rvmat` `Stage2` detail placeholder typed from memory
- **E06** `.rvmat` fresnel values guessed
- **E07** a `.rvmat` damage stage using a procedural colour
- **E08** assuming a function exists because it "makes sense"
- **E09** continuing past context saturation
- **E10** `forcedDiffuse` typed from memory
- **E11** a string read in `ActionCondition`: not syncable; use an integer id through a sync variable, because a client-only cache passes the menu and fails the server's `Can()`
- **E12** `IsTakeable()` false as the only pickup block, without knowing its side effects
- **E13** notifying after clearing a collection
- **E14** debugging downstream without checking upstream
- **E15** a cache not cleaned on a state transition
- **E16** a fix written without mapping the client and server boundary
- **E17** sync variable bitstream mismatch between client and server
- **E18** the wrong side guard during load
- **E19** the engine's `version` value written into a save by hand
- **E20** a modded vehicle will not drive, `WheelCountPresent()` is 0 while `WheelCount()` is N: the wheel slot's `selection` must exist in the body's Fire Geometry LOD with a wheel proxy
- **E21** (since 1.30) a custom map's `cfgeconomycore.xml` without the `MotorbikeScript` and `HouseDestructible` root classes
- **E22** (since 1.30) an action widget shows but F does nothing, or a custom pond drink never lists: `CanBeStarted()` and `CCTLiquid`
- **E23** (measured on a 1.30 pre-release, open) a `HumanCommandScript` subclass declared in `4_World` and started twice crashes every orderly exit
- **E24** blaming the model or config for a placement bug caused by another mod's `modded class Hologram`
- **E25** a rate limit or validation placed after `super.OnXxxServer`, leaving orphan state
- **E26** "preserves the original behaviour" treated as an audit pass when the original has bugs
- **E27** a sketchy pattern labelled "pre-existing" and silently carried along
- **E28** a vehicle nested-class override without the forward declaration `class X;` in the child mod's `CfgVehicles`
- **E29** `ProcessDirectDamage(DT_FIRE_ARM, ...)` instead of `DamageType.FIRE_ARM`
- **E30** a `modded` or derived class declaring a member its base already has
- **E31** an override whose body uses the base's parameter name under a different signature
- **E32** `attachments[] += {...}` on a class whose parent is in another PBO
- **E33** a vehicle nested-class override that resolves to an empty forward declaration and drops `class wheels`
- **E34** `CreateAttachment` or `CreateInInventory` called with a slot name instead of the item's class name
- **E35** a vehicle or custom wheel class with no `DamageSystem` `GlobalHealth`

Error lines in the logs are a different list: `/dayz-gate` and `/dayz-logwatch` match them against `skills/dayz-gate/known-errors.json`, which already names the fix and the owner. For "mod won't load", "works offline but not on a dedicated server" and "UI broken" symptoms, start with `docs/dayz-modding.md`, "Troubleshooting", and this catalog.

## 6. Debug and fix

When something "doesn't work" after it was implemented, diagnose top down: config and engine, entity setup, action registration, client conditions, server execution, response path. Never debug layer N+1 until layer N is confirmed. Propose the fix and say why before applying it; under 90% confidence, ask the user first; after a fix, run the edge-case checklist again.

The layers, the rules for probes (both sides from the first cycle, a time stamp on every line, proving a probe can be reached before adding fields to it, attributing an engine-channel error to whoever emitted it) and Layer 7, component bisection, are in `references/debug-protocol.md`. What the aligned numbers mean is in `references/measurement-discipline.md`. For the general method (root cause before fix) use the Superpowers debugging skill; for a log that already names the error use `/dayz-gate`, and hand a new error line to `dayz-mod-debugger`.

Two rules apply before a debug cycle starts:

- **Isolate structural changes.** Keep physics, inheritance and `SimulationModule` changes apart from feature changes, and validate each structural block on its own. Do not approve a `modded` or derived class until it has passed CfgConvert, a real compile and the in-game gate.
- **Close one bake before the next.** Before another bake of the same `.p3d` or `.pbo`, close the pending gate of the previous bake, or declare it blocked with the cause. Do not pile up changes that make the next verdict ambiguous.

## 7. Testing in game

The fast script loop with DayZDiag and file patching, the hard stop after two cycles without progress, the fix for a client stuck loading, the debug tools vanilla offers (shapes, `DbgUI`, the diag menu, the profiler, log switches) and the Linux differences are in `references/test-loop.md`. In this repo the loop is `/dayz-build-pbo`, `/dayz-launch-test`, `/dayz-logwatch`, `/dayz-stop-test` and `/dayz-gate`.

## 8. Offline gates: structure is not behaviour

An offline gate that passes does not allow you to say "done" when it checks structure and the success criterion is engine behaviour.

- **A structural gate** (offline, deterministic): class name equals file name, paths exist, topology, winding and UVs, selection sums, braces, cited APIs (the mini-audit), a skeleton or bind compared with vanilla. It predicts that the asset loads, not that it behaves.
- **A behavioural gate** (only with the engine running, or in Buldozer): deformation under animation, visible render and winding, mass, centre of mass and collision, getting in, the proxy convention the engine applies, elbow and wrist IK. It cannot be derived offline, nor in any sandbox other than the engine.

### The structural gate is mandatory before anything is called done

If you have not run it, it is not done.

```cmd
python scripts\tools\dayz-script-validator\scripts\script_validator.py <addon_root>
```

Exit 0 is PASS, 1 is FAIL, 2 is WARN. **Exit 1 blocks**: fix it, or justify it in writing in the handoff with the rule id and the reason. Read a WARN; do not ignore it silently.

If the mod has UI, the gate also includes:

```cmd
python scripts\tools\dayz-script-validator\scripts\ui_reconcile.py <addon_root>
```

It checks `FindAnyWidget` and `FindWidget` names against the real widgets in the `.layout` files, and `#STR_` keys against the stringtable: two faults that compile and show only when the menu opens.

In this repo `/dayz-lint <ModName>` is the same gate from one command: it checks the mod's setup (config, `CfgPatches`, prefix, script modules, files) and runs the script validator as its second stage. `/dayz-gate build` and `/dayz-build-pbo` run lint first.

The gate takes under a second on a whole addon, so cost is no excuse: run it on every pass, not only at the end. It catches the family of errors that otherwise show only when the script module compiles at boot (`Unknown type`, a local declared twice, an override with no base method, `delete`, an item override in the wrong `Cfg` class) and cost an in-game cycle of several minutes each.

**What this gate does not allow.** A green result predicts that the module compiles and the asset loads. It says nothing about what the engine does with them. The behavioural gate stays mandatory, separately (`/dayz-gate ingame`, `behavior` and `visual`).

Known coverage: the validator's tables in `scripts/tools/dayz-script-validator/scripts/shared/vanilla_reference.py` are small on purpose and cover only some rules. When a vanilla scripts tree is found (`--vanilla-root`, then `DAYZ_VANILLA_ROOT`, then `P:\scripts`), the validator also reads it for `ES-UNDEFINED-CLASS-REF`, `ES-UNDEFINED-BUILTIN-METHOD` and the 1.30 `RegisterConstructionSyncVariables` hook; without one those rules are reported as skipped, not as findings. Rules that rely only on the small tables have false negatives by design. Green is not proof of absence.

**The rule.** Before iterating on an offline metric, ask: does it correlate with the behavioural criterion, or is it a proxy the engine can ignore? For a proxy with no shown correlation, run one behavioural test before polishing it further; if it does not correlate, stop polishing it.

**Measured cases** (two mod projects, 2026-06):

- Character deformation. A deform test in Blender cut edge stretch from 34 times to between 6 and 9 times over about 12 offline iterations, with no improvement in game: the engine skins against the real `OFP2_ManSkeleton` from `model.cfg`, not against the FBX armature. The gate was false.
- Vehicle proxy. A derived proxy frame of identity gave an offline green twice; the engine applied another convention and the body proxy came out rotated about 90 degrees.

Related: report honestly what was and was not verified; bisect before trial and error (`references/debug-protocol.md`, Layer 7); the real gate is the tree that compiles (section 9).

### Compile gates cover both sides

A server compile pass is not a script gate for the whole build. Code under `#ifndef SERVER` (vanilla has such blocks, for example `P:\scripts\4_world\classes\constructionbase.c:151`) is absent from the server's compilation and can still break the client's module. Before accepting a build, boot both server and client, read the script compilation of each, and record a pass for each side separately. Wrapping a failing declaration in a side guard is not a fix unless the side that still compiles it also passes. `/dayz-gate ingame` boots both and reads both sets of logs.

Where a `modded class` declaration must live is a language rule (`skills/_shared/conventions/scripts.md` and `skills/_shared/enscript/patterns/modded_class.md`); this section is only about gating both sides.

### Script module capacity is calibrated by family

Measured in game, not yet checked on `P:\`: the log line `SCRIPT : Module: World; ... used X/33554 kB` reports one shared arena of about 32 MiB for vanilla and every loaded mod. Source lines, file bytes and file count are not a model of that capacity. Comments can be free, while declarations, generic instantiations and compiled method bodies cost structure and bytecode.

Do not use one global "kB per class" number. Measured: generic specializations formed one family at 5.6 to 6.6 kB each, small shell classes measured 0 to 1 kB, and two heavy source classes measured 139 kB. Size a reduction with before and after engine readings of the same family. Count class declarations case-sensitively, so a variable written `Class x` is not taken for a `class X` declaration.

When a module nears capacity, remove or parameterize repeated script declarations before shortening text. A public `config.cpp` class name does not need a script class of the same name; it binds to the nearest scripted ancestor. Keep the public config names and the `types.xml` entries while collapsing redundant script subclasses, then read the same module line again on both sides.

## 9. Dev tree and compilable tree

When a mod has two parallel trees (the one that is built and a working copy beside it, such as `<Mod>/` and `<Mod>_dev/`), every `config.cpp`, `model.cfg` or script value quoted as ground truth names the tree it came from. Before quoting:

1. Confirm which tree is the compilable one: the one the user builds, signs and deploys. A hint: it has the `$PBOPREFIX$` with the canonical path, not one ending in `_dev`.
2. Read the config from the compilable tree, not from the working copy.
3. If the two differ, report the difference as a finding (the working copy may need a rebase). Never quietly pick one as the truth.

In this repo there is one tree per mod, `workspace/<ModName>/`, reached by the engine through the `P:\<ModName>\` junction, so the question arises only for an imported project that brings its own second tree.

## 10. Changing a scheduler interval: update the harness counts

Measured on a power-grid mod: a write-behind flush constant went from 30 s to 5 s. A verification gate of 16 checks then failed on its schedule map, because the harness had the expected call counts hard-coded for the old value (2 calls in a 60,000 ms window, now 12; 10 in 300,000 ms, now 60). The only difference was that one callback; the fix was to update the harness's two expected maps, not the mod.

When a code change touches a `*_MS` or `*_S` constant that feeds a periodic scheduler or timer, before calling the build or verify gate a pass:

1. Grep the verification harnesses (the mod's `verify_*.py` tools, its tests) for hard-coded counts or intervals of that callback: expected maps, frozen cadence snapshots.
2. Recompute the expected count as window divided by the new interval, and update the harness with a minimal edit and a comment that names the reason.
3. Confirm that only that callback differs; every other count in the map must match exactly. If another callback differs, a cadence changed that nobody intended: investigate before touching the harness.
4. A gate that fails because of a legitimate interval change is not a code failure; it is an outdated harness, and updating it is part of closing the batch. Do not mask anything: the only difference must be the intended one, checked item by item against the expected map.

Scheduling patterns for the mod itself are in `skills/_shared/enscript/patterns/scheduler.md`.

## 11. Live bug ledger

Every new symptom a player can see gets a row in the mod's bug ledger (`bugs.md`, kept with the plan in `output/<ModName>-plan/`) before the next debug cycle. Search the ledger's alias fields first. A regression of a known symptom updates the existing row; it is never filed as a new bug.

A deployed fix records `F@<hash>`, but that token does **not** mean fixed. Close the row only with a named gate result or the user's verdict on that exact hash. Silence settles a reported symptom only when the regime that showed it was exercised and the observation window is recorded. That keeps build identity, exercised behaviour and closing evidence in one live ledger.

## 12. Audits

Severity labels (crash, VM exception, corruption, degradation, cosmetic: verify before labelling), the severity of something that is missing, the engine minimums that crash when absent, and the independence of parallel auditors are in `references/audit-escalation.md`. To run a data-critical audit use `skills/_shared/persistence/deep-audit.md` and `skills/_shared/persistence/data-audit.md`.

## 13. Handoff document

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
4. path/file4.c - what, dependencies, uncertainties

## Unresolved
- [ ] uncertainty 1
- [ ] uncertainty 2

## Errors found (add to the error catalog if they recur)

## Notes for the next session
```

Keep it with the plan in `output/<ModName>-plan/`. A rule that turns out to be wrong or missing goes into the right tier through `/dayz-record-correction`.

## The rest of the mod loop

This skill governs how code is written and debugged. Scoping, looking up APIs, building, the local server boot, publishing, and which domain skill to read are in `dayz-mod-dev`.
