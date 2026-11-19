# Checklists by file type

What to verify in each kind of file before a DayZ mod file counts as written. The implementation protocol (`skills/dayz-scope-mod/references/implementation-protocol.md`, "For each file") runs the matching checklist after every file. This file says what to check; the protocol says when.

A `P:\` citation means the item was read in that vanilla file. Where an item restates a rule a pack already holds, the pack file is named and wins on detail. Items measured on a mod project say so. The recurring mistakes behind many items are in `skills/dayz-launch-test/references/error-catalog.md` (the `E` numbers).

## `config.cpp`

### Script compile order and load order

The order in which mods' scripts and configs load follows the `requiredAddons[]` graph of each PBO's `CfgPatches`, not the order of the `-mod=` list alone. The engine compiles every mod's scripts for one layer (in that graph's order) before it starts the next layer. Measured on the native Linux 1.30 server: a `-servermod` whose `requiredAddons` names `DayZExpansion_Vehicles_Scripts` compiled right after that addon, wherever it stood in the `-servermod` string, so a `-servermod` does not come after every `-mod`. Not yet checked on `P:\`: load order is engine behaviour.

Never build a fix on a position in the `modded class` chain ("I am outermost"). Counteract another mod's behaviour from an event that provably runs after it (`EEInit()` runs after the whole constructor chain, so re-enabling damage there beats a constructor-time `SetAllowDamage(false)` from any position), and pick targets by data (a class-name prefix, config flags). Details and the other measured 1.30 facts: `skills/dayz-launch-test/references/dayz-1-30-server-measured.md`.

- [ ] `requiredAddons[]` lists the `CfgPatches` class names you really depend on (scripts and config parents), not Steam folder names. `/dayz-lint` checks the shape of each entry and every `DZ_` name (`required-addon-name`).
- [ ] Optional dependencies: leave them out of `requiredAddons` and detect them at run time (for CF, `#ifdef CF_MODULES`).

### Layer split for a script mod

The usual split:

- **3_Game:** constants, the config data class, RPC id enums
- **4_World:** the manager singleton, player and event handlers, entity logic
- **5_Mission only:** modded `MissionServer` and `MissionGameplay`, HUD and UI, boot hooks
- Ship `mod.cpp`, a scripts `config.cpp` with the right `CfgMods` `defs` module keys, `stringtable.csv`, `inputs.xml` and a build script. In this repo `/dayz-new-mod` writes the skeleton and `/dayz-add-scaffold` fills gaps.
- A habit when the mod grows: RPC endpoint, then config field, then UI panel, then keybind, then stringtable entry.

### Items

- [ ] One name for the addon: naming the `CfgPatches` class after the addon folder is a habit, not an engine rule (vanilla's `DZ_data_aiconfigs` sits in a folder named `aiconfigs`, `P:\DZ\data\aiconfigs\config.cpp:3`). What this repo requires is that `$PBOPREFIX$` holds exactly the mod name (`/dayz-lint`, `pboprefix-mismatch`).
- [ ] `requiredAddons` uses `CfgPatches` class names:
  - Community Framework: `"JM_CF_Scripts"` (not `"CommunityFramework"`). Third-party fact (CF).
  - Dabs Framework: `"DF_Scripts"` or `"DF_GUI"` (not `"DabsFramework"`). Third-party fact (Dabs).
  - Expansion: `"DayZExpansion_Core"` for Core; a module's scripts patch is `"DayZExpansion_<Module>_Scripts"` (`_Market_Scripts`, `_AI_Scripts`, `_Quests_Scripts`, `_Vehicles_Scripts`, `_BaseBuilding_Scripts`), not `"DayZExpansion_<Module>"`. Third-party fact (DayZ Expansion: its `DayZExpansion/Core/Stub/config.cpp:3` and `DayZExpansion/Market/Scripts/config.cpp:3`).
  - Vanilla: `"DZ_Data"` (`P:\DZ\data\config.cpp:3`), `"DZ_Scripts"` (`P:\scripts\config.cpp:3`).
- [ ] The `hiddenSelections[]` count matches the `hiddenSelectionsTextures[]` count.
- [ ] `scope = 2` exposes the class in public lists and tools that filter on scope 2; `scope = 1` is protected, and script can still create it (vanilla `LargeTentClutterCutter` has `scope=1`, `P:\DZ\gear\camping\config.cpp:1454` to `:1456`); `scope = 0` is abstract.
- [ ] Inheritance: the parent exists, or its addon is in `requiredAddons`.
- [ ] A vehicle nested-class override (`class SimulationModule: SimulationModule`, `class Axles: Axles`, `class Front: Front`, `class Rear: Rear`, `class DamageZones: DamageZones`): the base named after the colon is forward-declared as `class X;` at the root of this `CfgVehicles`. Each `config.cpp` is parsed with its own scope; a child mod does not inherit forward declarations from the parent PBO's config. Without them CfgConvert stops with `Undefined base class 'X'`. Nested classes with no `: parent` merge implicitly and need none. See E28 and E33 (measured on a vehicle child mod).
- [ ] `attachments[]` on a class whose parent is in another PBO is written out in full with `=`, never appended with `+=` (E32).
- [ ] `inventorySlot` is a string for one slot and `inventorySlot[]` an array for several; mixing the forms silently breaks the attachment. The rule and the vanilla examples are in `skills/_shared/conventions/config.md`.
- [ ] `ghostIcon` is `"set:setname image:imagename"`, and the imageset exists (`/dayz-build-imageset` builds one).
- [ ] `imageSets` sits inside `CfgMods > <Mod> > defs > imageSets`, not at the root and not in `CfgSlots` (E02).
- [ ] A vehicle or custom wheel class declares `DamageSystem` with `GlobalHealth` (E35), and the other engine minimums in `skills/dayz-launch-test/references/debug-protocol.md`, "Engine minimums to check early".

## Enforce Script, general

The full rules are in `skills/_shared/enscript-style.md` (the style guide, which wins on style) and in `skills/_shared/enscript/depth/`. The restrictions that bite most often:

- [ ] No ternary operator (`? :` does not compile). Workarounds: `skills/_shared/enscript/patterns/language_workarounds.md`.
- [ ] `ref` on owning member fields; never on parameters, return types or typedefs, and never `new ref` (on a local it is valid and redundant, so leave it out). Detail: `skills/_shared/enscript-style/memory.md`.
- [ ] Never `delete` an entity; call `Delete()` or `DeleteSafe()`. The `delete` keyword can segfault if references still exist (not yet checked on `P:\`). Vanilla does use it on its own script objects (`delete GetBleedingManagerServer();`, `P:\scripts\4_world\entities\manbase\playerbase.c:1224`), so the rule in this repo is the style guide's: allowed on your own script object only when nothing else still holds it.
- [ ] `foreach` works, but never loop directly over a getter's return value: assign it to a local first, then iterate. The reported failure is a null pointer on the second item; the mechanism is not yet checked on `P:\`. The habit is right either way.
- [ ] `m_` prefix on every member field.
- [ ] No `new` inside a periodic tick: keep a member and call `.Clear()`.
- [ ] A complex expression inside an array assignment can segfault: put it in a local first.
- [ ] `ProcessDirectDamage` takes the damage type as an `int` (`P:\scripts\3_game\entities\object.c:1138`). Vanilla passes the engine constant `DT_CUSTOM` (`P:\scripts\3_game\entities\entityai.c:4153`), and the method comment lists `DT_CLOSE_COMBAT`, `DT_FIRE_ARM`, `DT_EXPLOSION` and `DT_CUSTOM` (`object.c:1130`). The script enum `DamageType` (`P:\scripts\3_game\damagesystem.c:10` to `:13`, where `FIRE_ARM` is 1) is marked "exposed from C++". Either form names a damage type; whether a `DT_` name fails to compile in a mod (E29) is not checked on `P:\`.
- [ ] A `modded` or derived class does not declare a member its base already has (E30), and an override copies the base signature, parameter names included (E31).
- [ ] `CreateAttachment` and `CreateInInventory` get the item's class name, not a slot name (E34).

## Networking

Pattern file: `skills/_shared/enscript/patterns/netsync.md`. Who owns what: `skills/_shared/conventions/scripts.md`.

- [ ] `RegisterNetSyncVariable*` is called while the entity is built: in the constructor, or in an `InitItemVariables()` override. `ItemBase` has no `Init()` to override and registers in `InitItemVariables()` (`P:\scripts\4_world\entities\itembase.c:158`); `PlayerBase` has `Init()` and registers there (`P:\scripts\4_world\entities\manbase\playerbase.c:364`; `netsync.md`, "Registration").
- [ ] Types: `Bool`, `BoolSignal`, `Int`, `Float`, `Object` (`RegisterNetSyncVariableBool` to `RegisterNetSyncVariableObject`, `P:\scripts\3_game\entities\entityai.c:2832` to `:2869`). There is no string variant.
- [ ] The same variables in the same order on client and server (E17).
- [ ] `OnVariablesSynchronized` (`P:\scripts\3_game\entities\entityai.c:3069`) is overridden and reacts to every registered variable, and calls `super`.
- [ ] Side guards: `IsDedicatedServer()` in early init and to skip client-only work, `IsServer()` for authority work after load (E18).
- [ ] `SetSynchDirty()` (`P:\scripts\3_game\entities\entityai.c:3064`) after a server-side write. One call after a coherent batch of writes is enough.

## UI and layout

Read `skills/_shared/conventions/ui.md` first; depth is in `skills/_shared/ui/`.

- [ ] The `.layout` path matches `$PBOPREFIX$`.
- [ ] Widget names match the script references exactly (case sensitive). The script validator's `ui_reconcile.py` checks `FindAnyWidget` and `FindWidget` names against the `.layout` files.
- [ ] Dabs MVC: widget names equal the `ViewController` property names exactly. Third-party fact (Dabs Framework); our checked notes are `skills/_shared/enscript/integrations/dabs_framework.md`.
- [ ] `ScriptViewMenu` ghost-menu guard: check `if (layoutRoot)` before operating on it (Dabs).
- [ ] Input lock: `ChangeGameFocus(1)` on open (`P:\scripts\3_game\tools\input.c:20`), reversed on close.
- [ ] Cursor: `ShowUICursor(true)` on open (`P:\scripts\3_game\tools\uimanager.c:244`), reversed on close.
- [ ] Cleanup in the destructor or `OnHide`: remove handlers, null the references.

## Actions

Pattern file: `skills/_shared/enscript/patterns/actions.md` (registering the action class, condition components, stopping pickup).

The order of checks in `ActionBase.Can` (`P:\scripts\4_world\classes\useractionscomponent\actionbase.c:929` to `:966`):

```text
1. Condition mask    bitwise: in vehicle, on ladder, swimming, restrained, raised ...   (:931)
2. Stance            IsFullBodyEx / IsPlayerInStance / IsRolling                        (:931)
3. Target owner      the target sits in another player's hierarchy: reject              (:938-943)
4. Target condition  m_ConditionTarget.Can (CCTObject = range, CCTCursor, CCTNone)      (:947)
5. Item condition    m_ConditionItem.Can (CCINone, CCINonRuined ...)                    (:951)
6. ActionCondition   your override; runs on the client (menu) and on the server (start) (:954)
7. Full-body stance  for a full-body action, can the player change to the stance        (:957-963)
```

The server runs the same `Can` before it accepts a client's action (`pickedAction.Can(...)`, `P:\scripts\4_world\classes\useractionscomponent\actionmanagerserver.c:168`). Until 1.29 these seven steps were treated as the whole client start gate (not yet checked on `P:\`, which holds no 1.29 data). Since 1.30, after the widget lists the action, `CanBeStarted()` must also be true or the client never calls `ActionStart` (`P:\scripts\4_world\classes\useractionscomponent\actionmanagerclient.c:336`).

- [ ] `CreateConditionComponents` is overridden with the right target and item conditions.
- [ ] (since 1.30) `CanBeStarted()` returns true for an action the player can perform; info-only actions return false. The base returns true, and its comment names "pure info" actions as the reason to override it (`actionbase.c:287` and `:288`).
- [ ] (since 1.30) Water, wash and fill on sea or pond use `CCTLiquid` (as `ActionWashHandsWater` does, `P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionwashhandswater.c:28`) unless you mean to differ.
- [ ] `ActionCondition` reads only data both client and server have (the data map in `skills/dayz-scope-mod/references/implementation-protocol.md`).
- [ ] Target type: `GetType()` for an exact class, `IsKindOf()` to include subclasses.
- [ ] Pickup is blocked on purpose, with one of the two recipes in `skills/dayz-launch-test/references/error-catalog.md`, "Stopping pickup (E12)", knowing what each does to the vicinity list and the action cursor.
- [ ] `CanPutInCargo()` and `CanPutIntoHands()` are overridden when the item must not be stored.
- [ ] The stringtable key exists, or a hard-coded string is used while testing.

## `.rvmat` materials

Pack files: `skills/_shared/textures/rvmat-stages.md` and `skills/_shared/textures/surface-recipes.md`. They win on values.

- [ ] Start from a working vanilla `.rvmat` of the same shader and compare every stage against it.
- [ ] `Stage2` (detail), `Stage4` (ambient shadow) and `forcedDiffuse[]`: keep what the vanilla material you copied uses. `color(0.5,0.5,0.5,0.5,DT)`, `color(0,1,1,1)` with no `AS` suffix, and `forcedDiffuse` alpha 1 are not the only correct values; vanilla ships those and the pack defaults both (`skills/dayz-launch-test/references/error-catalog.md`, "The three material rows").
- [ ] `Stage6` fresnel: copied from a vanilla reference of the same shader type (E06).
- [ ] Damage and destruct materials use the vanilla macro textures `generic_damage_mc.paa` and `generic_destruct_mc.paa` (E07).

## Persistence: `OnStoreSave` and `OnStoreLoad`

Pack files: `skills/_shared/enscript/patterns/persistence.md` and `skills/_shared/persistence/save-load-contract.md`. They win on detail.

- [ ] The `version` parameter of `OnStoreLoad(ParamsReadContext ctx, int version)` (`P:\scripts\3_game\entities\entityai.c:2978`) is the game's storage version, passed in by the engine. Do not write or read that value yourself (E19). For your own fields write your own version header first.
- [ ] Save and load in exactly the same order (a raw sequential binary stream).
- [ ] Every `ctx.Write()` has its `ctx.Read()` at the same position.
- [ ] Call `super.OnStoreSave(ctx)` and `super.OnStoreLoad(ctx, version)` first.
- [ ] Check the return value of every `ctx.Read()` and return false on failure.
- [ ] `AfterStoreLoad` (`P:\scripts\3_game\entities\entityai.c:1419`) for work after the load, not `OnStoreLoad`.
- [ ] Test: delete the persistence files and check that a clean start works.

## Edge cases in logic

Run this for any feature with collections, state or a lifecycle:

- [ ] **Empty collection (count 0).** The loop body never runs. Send notifications before clearing, not after (E13).
- [ ] **Null or empty state.** No group, no flag, no items in the slots. Guard every access with a null check.
- [ ] **State transitions.** Active to abandoned, raised to lowered, powered to unpowered. Does the cache update on each transition? Does the UI show the new state? (E15)
- [ ] **Cache against entity lifecycle.** When the entity is destroyed, is the cache cleaned up?
- [ ] **Player reconnection.** The client cache is lost on disconnect. How is it rebuilt (an RPC on connect, a sync variable re-sync)?
- [ ] **Concurrent operations.** Two players acting on the same entity at the same moment.

## Refactor: state coherence

Mandatory when a refactor consolidates logic across calls that have side effects.

Moving a guard, a validation or a rate limit across an irreversible engine call (`super.OnStartServer`, `super.OnExecuteServer`, `ObjectDelete`, an RPC send, `SetSynchDirty`, a file write) can create **orphan state**: the engine has done half the work, the guard rejects the rest, and the world is left incoherent.

For every `return` or early exit in the refactored function, list:

- What irreversible engine state has been changed up to this point?
- If we return now, is the world in a coherent state?

If the second answer is no, the guard is in the wrong place. Move it before the irreversible call.

Orphan patterns measured on a virtual storage mod:

- **A rate limit after an open action's `super` call.** A rate limit or validation placed after `super.OnStartServer` of an open or toggle action. The `super` call already flipped `IsOpen()`; rejecting the follow-up restore leaves the container physically open with its cargo still virtualized in the project's storage file. Symptoms: an empty open container in game, the storage file not consumed. Fix: rate-limit before `super`, gated on the inferred intent (the state before was closed for a toggle, and is asserted closed for a split open hook).
- **A sync variable written between unrelated `SetSynchDirty()` calls**, out of step with the constructor's registration order. The client's values look stale but correctly typed. Fix: register and write in one fixed order; one `SetSynchDirty()` after a coherent batch of writes.
- **An entity destroyed inside a `foreach` over a registry**, then continuing the loop. The next iteration holds a stale reference: a null pointer or a crash. Fix: collect the entities to delete in a temporary array and delete them after the loop.

Process rules:

- **"Preserves the original behaviour" is not a goal** when the original is buggy. Treat each preserved behaviour as a hypothesis to check, not a fact to defend. For every "preserved" line in your audit, ask whether it should be preserved (E26).
- **"Pre-existing, not introduced by the refactor" is not an exemption.** If the audit notes a doubtful pattern with that label, stop and get an explicit decision from the user (fix now, or flag for later). Quietly continuing is the worst option (E27).
- **When an auditor or the user catches one orphan-state bug, grep the sibling files for the same pattern at once.** It rarely lives in one place. On one mod, after the auditor caught the open action case in one toggle hook, the sibling grep found two more open actions with the same pattern, which should have been fixed in the same pass.
