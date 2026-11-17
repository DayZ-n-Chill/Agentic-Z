# Recurring error catalog (E01 to E35)

Mistakes made more than once while implementing DayZ mods, each with the correct form. `dayz-mod-workflow` keeps a one-line index; this file is the detail. Check it actively while writing code, not only when something breaks.

How to read it:

- **Seen in** says in what kind of mod or file the mistake was caught.
- A `P:\` citation means the correct form was read in that vanilla file. A row with none rests on the project's own measurement and is not yet checked on `P:\`.
- Where two forms of a rule circulate, the row states what vanilla shows and which form to use.
- Until 1.29 the list ended at E20. E21 and E22 are 1.30 changes; what 1.29 had in their place is not yet checked on `P:\`, which holds no 1.29 data. E23 was measured on a 1.30 pre-release.

Log lines these mistakes produce are triaged by `/dayz-gate` and `/dayz-logwatch` (`skills/dayz-gate/known-errors.json`); this catalog also covers the mistakes that leave no log line.

## Config and materials

| ID | Error | Correct | Seen in |
|---|---|---|---|
| E01 | `requiredAddons[]={"DabsFramework"}` | Use the `CfgPatches` class names: `{"DF_Scripts"}` or `{"DF_GUI"}`. Third-party fact (Dabs Framework). | A UI mod's `config.cpp` |
| E02 | `imageSets` in `CfgSlots` or at the config root | Inside `CfgMods > <Mod> > defs > imageSets`. | An armour mod |
| E04 | A `.rvmat` `Stage4` procedural texture typed from memory | Copy the stage from a working vanilla `.rvmat` of the same shader. `color(0,1,1,1)` with no `AS` suffix is not the only correct form; vanilla ships both. See "The three `.rvmat` rows" below. | An armour mod |
| E05 | A `.rvmat` `Stage2` detail texture typed from memory | Same rule. Alpha 0.5, `color(0.5,0.5,0.5,0.5,DT)`, is not the only correct form; vanilla ships both. | An armour mod |
| E06 | `.rvmat` fresnel values guessed | Copy `Stage6` from a vanilla reference of the same shader type, for example `fresnel(1.05,0.67)` in `P:\DZ\gear\camping\data\bagpack_damage.rvmat:71`. | An armour mod |
| E07 | `.rvmat` damage stage using a procedural colour | Use the vanilla macro textures `generic_damage_mc.paa` and `generic_destruct_mc.paa`, as `P:\DZ\gear\camping\data\bagpack_damage.rvmat:35` does (the files are in `P:\DZ\characters\data\`). | An armour mod |
| E10 | `forcedDiffuse` typed from memory | Copy it from the vanilla material you started from. Alpha 1, `0,0,0,1`, is not the only correct form; vanilla ships both. | An armour mod |
| E21 | (since 1.30; the 1.29 side is not yet checked on `P:\`) A custom map's `cfgeconomycore.xml` copied from 1.29, with no motorbike or destructible-house root classes | Add `<rootclass name="MotorbikeScript" act="car" reportMemoryLOD="no" />` and `<rootclass name="HouseDestructible" reportMemoryLOD="no" />` next to `CarScript` and `BoatScript`, as in `P:\DZ\worlds\chernarusplus\ce\cfgeconomycore.xml:17-18` (the same pair on Enoch and Sakhal). | DayZ 1.30 Central Economy |
| E28 | A vehicle nested-class override in a child mod (`class SimulationModule: SimulationModule`, `class Axles: Axles`, `class Front: Front`, `class Rear: Rear`, `class DamageZones: DamageZones`) without a forward declaration `class X;` at the root of that mod's `CfgVehicles`. CfgConvert stops with `Undefined base class 'X'`, so the mod does not load. | Declare `class SimulationModule; class Axles; class Front; class Rear;` (whichever the override uses) at the root of the child mod's `CfgVehicles`. Each `config.cpp` is parsed with its own scope; it does not inherit forward declarations from the parent PBO. Nested classes with no `: parent` (`Engine`, `Steering`, `Gearbox`, `Differential`, `Suspension`) merge implicitly and need none. | A vehicle child mod |
| E32 | `attachments[] += {...}` in a child mod whose class inherits a vehicle from another PBO. The parsed config holds only the items from the `+=`, which breaks every slot (battery, wheels, doors). Measured with `CfgConvert -xml`. | Write `attachments[] = {...}` with the complete base list plus the new entries at the end. Do not rely on `+=` on a parent in another PBO. Same family as the `inventorySlot[] +=` trap in `skills/_shared/conventions/config.md`. | A vehicle child mod |
| E33 | A vehicle nested-class override (`SimulationModule`, `Axles`, `Front`, `Rear`) whose `: X` resolves to an empty forward declaration and which leaves out sub-blocks such as `class wheels`. It compiles, loads and breaks gameplay: a malformed `SimulationModule`, a vehicle nobody can enter, broken slots and wheels. | Follow the original config's pattern: `class SimulationModule: SimulationModule`, but inside it `class Axles`, `class Front` and `class Rear` with no `: X` and with the full `class wheels` (`Left`, `Right`). Or do not override at all when only a minor physics value changes. | A vehicle child mod |
| E35 | A vehicle (`: CarScript`) or custom wheel class (`: CarWheel`) with no `class DamageSystem { class GlobalHealth ... }`. Crash `[Object::GetMaxHealth] No DamageSystemData or not initialized` as soon as health is read (admin `SetHealth01`, damage, collision, possibly sync). The `CarScript` and `CarWheel` bases do not guarantee it. | Declare `DamageSystem.GlobalHealth.Health { hitpoints; healthLevels[]; }` on the vehicle and on each custom wheel class. The minimum that works is `GlobalHealth` alone, without `DamageZones`. Vanilla: `OffroadHatchback` has `class DamageSystem` with `class GlobalHealth` at `P:\DZ\vehicles\wheeled\config.cpp:1540-1542`. | A quad vehicle mod, first boot, 2026-05-25 |

## Enforce Script

| ID | Error | Correct | Seen in |
|---|---|---|---|
| E03 | The same variable name in sibling scopes | Declare the variable once, before the conditional. | A UI mod, crash |
| E08 | Assuming a function exists because it "makes sense" | Verify it on `P:\scripts\` (Tier 2 search rule), in a loaded pack, or online, before using it. | Several |
| E29 | `ProcessDirectDamage(DT_FIRE_ARM, ...)` copied from another mod's source. `DT_FIRE_ARM` is not a vanilla symbol, so it does not compile. | Use the enum: `DamageType.FIRE_ARM` (`P:\scripts\3_game\damagesystem.c:10-13`). In vanilla, `DT_FIRE_ARM` appears only in a doc comment (`P:\scripts\3_game\entities\object.c:1130`). Any `DT_*` seen in another mod's source may be that mod's own alias. | A vehicle child mod |
| E30 | A `modded` or derived class declares again a member the vanilla base already has, for example `m_NoiseSystem` on `CarScript`. Compile error `Multiple declaration of variable 'X'`. | Do not declare it again; use the inherited one (`m_NoiseSystem` is at `P:\scripts\4_world\entities\vehicles\carscript.c:2770`). Before compiling, grep each of your own `m_*` names against the base chain (`carscript.c`, `car.c`, `transport.c`, `entityai.c`, `itembase.c`). | A vehicle child mod |
| E31 | An override whose body uses the base method's parameter name while its own signature names the parameter differently, for example `OnExecuteServer(ActionData actionData)` with a body that reads `action_data`. Compile error `Can't find variable 'X'`. | Copy the base signature, parameter names included, from the vanilla file. See "E31: parameter names in an override" below for what vanilla shows. | A vehicle child mod |
| E34 | `GetInventory().CreateAttachment("<slot>")` or `CreateInInventory("<slot>")` called with a slot name. The call takes the item's class name; when the two differ it creates nothing, with no log line. Hidden in vanilla because slot and class usually share a name (`CarBattery`, `SparkPlug`, `Reflector_1_1`). | Pass the item's class name: the parameter is `typeName` in `CreateAttachment(string typeName)` (`P:\scripts\3_game\systems\inventory\inventory.c:209`). The engine fills the first compatible free slot. Check class (`CfgVehicles`) against slot (`CfgSlots`, `inventorySlot`) before writing the call. | A quad vehicle mod, 2026-05-26 |

## Client, server and actions

| ID | Error | Correct | Seen in |
|---|---|---|---|
| E11 | A string read in `ActionCondition` | Strings cannot be net-synced. Use an integer id through a sync variable, which both sides can read. A client-only cache passes the menu and then fails the server's `Can()` check (`pickedAction.Can(...)`, `P:\scripts\4_world\classes\useractionscomponent\actionmanagerserver.c:168`). | A player-group mod |
| E12 | `IsTakeable()` returning false as the only pickup block, without knowing its side effects | `IsTakeable() == false` stops the two take actions and also removes the item from the vicinity list (`GetVicinityObjects`, `P:\scripts\4_world\classes\useractionscomponent\actiontargets.c:61-64`); custom actions still run. Choose on purpose; both recipes are in "E12: stopping pickup" below. | A player-group mod |
| E13 | Notifying after clearing a collection | A loop over an empty collection sends nothing. Notify before clearing. | A player-group mod |
| E14 | Debugging downstream without checking upstream | Follow the layer order in `debug-protocol.md`: check `IsTakeable` and `AddAction` before `ActionCondition`. | A player-group mod |
| E15 | A cache not cleaned on a state transition | Every state change updates the cache, on client and server. | A player-group mod |
| E16 | A fix written without mapping the client and server boundary | Fill in the client and server data map (`dayz-mod-workflow`, "Client and server data map") before writing the fix. | A player-group mod |
| E17 | Sync variable bitstream mismatch between client and server | Register the same variables in the same order on both sides. Not yet checked on `P:\`; the stream layout is native. | Networked entities |
| E18 | The wrong side guard during load | Vanilla calls `IsDedicatedServer()` the "robust check which is preferred" over `IsServer()` and `IsClient()` because it "is valid much sooner" (`P:\scripts\3_game\global\game.c:1118-1125`). Use it in early init and to skip client-only work; after load use `IsServer()` for authority work so single player still runs it (`skills/_shared/conventions/scripts.md`). The stricter form, "always `IsDedicatedServer()`, never `IsServer()`", would skip authority code in single player. | Load-time init code |
| E19 | The engine's `version` value written into a save by hand | The engine passes the storage version to `OnStoreLoad(ParamsReadContext ctx, int version)` (`P:\scripts\3_game\entities\entityai.c:2978`); never write or read that value yourself. It is the game's storage version, not yours, so for your own fields write your own version header first (`skills/_shared/enscript/patterns/persistence.md`). | vanilla `EntityAI` |
| E22 | (since 1.30; the 1.29 side is not yet checked on `P:\`) An action widget is visible but F does nothing, or a custom pond drink never lists | After the condition checks vanilla can show an action whose `CanBeStarted()` is false: the client only starts it when `action.CanBeStarted()` (`P:\scripts\4_world\classes\useractionscomponent\actionmanagerclient.c:336`), and info actions override it to false (`CanBeStarted`, `P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionpartinfo.c:18-21`). Vanilla water, wash and fill actions use `CCTLiquid`, not `CCTWaterSurfaceEx` (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionwashhandswater.c:28`). More in `dayz-1-30-mod-workflow.md`. | DayZ 1.30 actions |
| E25 | A rate limit or validation placed after `super.OnXxxServer`, leaving orphan state | Put it before the `super` call, gated on the inferred intent. `checklists.md`, "Refactor: state coherence", ORPHAN-1. | A virtual-storage mod |

## Vehicles and models

| ID | Error | Correct | Seen in |
|---|---|---|---|
| E20 | A modded vehicle will not drive, with no RPT error: the wheels mount but do not spin (`WheelCountPresent()` is 0 while `WheelCount()` is N), the chassis bounces or sinks, the steering animates without the simulation turning | `CfgSlots.<wheel-slot>.selection` must name a selection that exists in the **Fire Geometry LOD of the body** and contains a wheel proxy (`proxy:\...`). If it exists only in the visual LODs, alias the Fire Geometry proxy face into the slot's selection name (an additive py3d edit that keeps the visual hide). Mechanism and the py3d fix: `enforce-script-reference`, `references/vehicle-scripting.md`, "Wheels and the simulation: `CfgSlots` `selection` must match the Fire Geometry proxy selection". | A quad vehicle mod, `wheelPresent=0` |
| E24 | Blaming the `.p3d` or the config for a placement bug whose cause is another mod's `Hologram.c` | Grep `modded class Hologram` across every loaded mod before touching the model. Third-party fact: A6_Base_Storage, BaseBuildingPlus and others rewrite `GetProjectionEntityPosition` and `EvaluateCollision`. `/dayz-conflict-check` finds class collisions between mods. | Chests stacking |

## Process

| ID | Error | Correct | Seen in |
|---|---|---|---|
| E09 | Continuing past context saturation | Stop, write a checkpoint, hand off (`dayz-mod-workflow`, "Checkpoints" and "Handoff document"). | Several |
| E23 | (measured on a 1.30 pre-release, open) A `HumanCommandScript` subclass declared in `4_World` and started two or more times: every orderly exit crashes client and server | Declare the class the engine starts in `3_Game`, as a thin shell that forwards its hooks to a `Managed` logic object in `4_World`. The workaround is not yet verified in game. Section below. | A skateboard mod, DayZDiag 1.30.164014 |
| E26 | "Preserves the original behaviour" treated as an audit pass when the original has bugs | It is not a goal. Each "preserved" behaviour is a hypothesis to check. `checklists.md`, "Refactor: state coherence". | A virtual-storage mod |
| E27 | A sketchy pattern labelled "pre-existing" and silently carried along | Stop, get an explicit decision from the user (fix now or flag for later), and grep the sibling files for the same pattern. | A virtual-storage mod |

## Keeping the catalog

- When a session hits a mistake that is already listed, do not add it again; name the existing id in the handoff.
- When a session hits a new mistake for the second time, add a row with the next free id, with the correct form and its `P:\` citation or the project it was measured on.
- When a row goes out of date (the engine changed, an official patch), strike it through with the date and the replacement. Do not delete it; the history is the point.
- A mistake that leaves a log line also gets an entry in `skills/dayz-gate/known-errors.json`, so `/dayz-gate` and `/dayz-logwatch` name the fix. E28, E30 and E35 have one.

## The three `.rvmat` rows (E04, E05, E10)

Three exact values circulate as "the correct one". Counted over the 34,899 text `.rvmat` files under `P:\DZ\` (ignoring letter case and white space), vanilla ships both forms of each, and the form usually called the mistake is the more common one:

| Value | Form in the Agentic-Z texture pack | Vanilla files | The other form | Vanilla files |
|---|---|---|---|---|
| `Stage2` detail placeholder | `color(0.5,0.5,0.5,1,DT)` (for example `P:\DZ\animals\canis_lupus\data\fur_alpha.rvmat:27`) | 3,844 | `color(0.5,0.5,0.5,0.5,DT)` (for example `P:\DZ\animals\bos_taurus\data\bull_brown.rvmat:23`) | 1,299 |
| `Stage4` ambient shadow placeholder | `color(1,1,1,1,AS)` (for example `P:\DZ\animals\canis_lupus\data\fur_alpha.rvmat:51`) | 4,405 | `color(0,1,1,1)` with no suffix (for example `P:\DZ\gear\camping\data\sea_chest_e.rvmat:119`) | 73 |
| `forcedDiffuse[]` | `{0,0,0,0}` (for example `P:\DZ\animals\bos_taurus\data\bull_brown.rvmat:3`) | 16,612 | `{0,0,0,1}` (for example `P:\DZ\characters\backpacks\data\drybag.rvmat:7`) | 1,059 |

So neither value is an error by itself. The rule that holds is E06's: start from a working vanilla `.rvmat` of the same shader and the same kind of surface and change only what you must. The defaults and the recipes are in `skills/_shared/textures/rvmat-stages.md` and `skills/_shared/textures/surface-recipes.md`.

## E12: stopping pickup

Two recipes exist, and each has a visible consequence:

- **Vanilla's own way for a fixed device.** `PowerGeneratorStatic` returns false from `CanPutInCargo`, `CanPutIntoHands` and `IsTakeable` (`P:\scripts\4_world\entities\building\underground\powergeneratorstatic.c:143-152` and `IsTakeable` at `P:\scripts\4_world\entities\building\underground\powergeneratorstatic.c:219`). Both take actions refuse a target that is not takeable (`IsTakeable`, `P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiontakeitem.c:36`). Consequences: the item no longer appears in the vicinity list (`P:\scripts\4_world\classes\useractionscomponent\actiontargets.c:61-64`), and the action cursor hides for a ground item that is neither takeable nor `IsActionTargetVisible()` (`P:\scripts\5_mission\gui\actiontargetscursor.c:719`). Vanilla's generator overrides `IsActionTargetVisible` for that reason (`P:\scripts\4_world\entities\building\underground\powergeneratorstatic.c:224`). Pattern file: `skills/_shared/enscript/patterns/actions.md`.
- **For an item that keeps its own actions.** Leave `IsTakeable()` true, call `RemoveAction(ActionTakeItem)` and `RemoveAction(ActionTakeItemToHands)` in `SetActions()`, and refuse `CanPutInCargo` and `CanPutIntoHands`. The item stays in the vicinity list and its custom actions keep their cursor.

The mistake E12 names is choosing the first recipe without `IsActionTargetVisible()` and then wondering why the custom action has no cursor, or expecting `IsTakeable() == false` to block custom actions (it does not: they do not read it unless you write that check).

## E31: parameter names in an override

The rule is often stated as "the parameter name in an override must match the base". Vanilla does not support that as a compiler rule: `EntityAI` declares `bool CanDetachAttachment (EntityAI parent)` (`P:\scripts\3_game\entities\entityai.c:1540`) and eight vanilla handguard classes override it as `CanDetachAttachment( EntityAI attachment )`, for example `P:\scripts\4_world\entities\itembase\inventory_base\ak74_hndgrd.c:4`. Those files compile, so a different parameter name is legal.

What does fail is a body that reads a name its own signature did not declare: the reported `Can't find variable 'action_data'` came from an override declared with `actionData`. Copying the base signature exactly, names included, removes the mismatch and keeps the code searchable, which is why the row recommends it. All 81 vanilla overrides of `OnExecuteServer` use the base's name `action_data`.

## E23: a `HumanCommandScript` subclass in `4_World`, started twice, crashes the orderly exit (open)

Measured in game on 2026-10-07 on DayZDiag 1.30.164014 (Experimental), server and client, with a skateboard mod's ride command. Not yet checked on `P:\`; a source file cannot show it.

- After two or more rides of the ride command, a `HumanCommandScript` subclass declared in `4_World`, the orderly exit crashed client and server with an access violation during the cleanup of the `World` script module, right after `Leaked '<RideCommand>' script instance (-Nx)!` and before `Leaked 'HumanCommandScript' (+Nx)`, N being the number of rides. After one ride the exit was clean. A constructor and destructor probe counted exactly one of each per ride, and starting the command with `StartCommand_Script` on a new instance or with `StartCommand_ScriptInst` on its class made no difference.
- An empty class deriving from `HumanCommandScript`, declared in `scripts/4_World` and started twice with `StartCommand_ScriptInst`, ending itself after 1 s each time, crashed the orderly exit the same way: an access violation in the `World` module's teardown right after `Leaked 'X' script instance (-2x)!`, where the bytes before the faulting address are a reference-count release.
- The same empty class declared in `scripts/3_Game` exited clean (`Termination successfully completed`), and still printed -2x for the class and +2x for `HumanCommandScript`, in the `Game` module.
- Started once, it exited clean from either module.

The cause is not known. One reading of the leak counts is creation being counted under `HumanCommandScript` and destruction under the subclass; that is an interpretation, not a measurement. The workaround keeps the class the engine starts in `3_Game`, a thin shell that forwards the command's hooks to a `Managed` logic object in `4_World`. As of 2026-10-08 its verification in game on the real ride command was still running; no result is recorded here. Measured only on DayZDiag 1.30.164014.
