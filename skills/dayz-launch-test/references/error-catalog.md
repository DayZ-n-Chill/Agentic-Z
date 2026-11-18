# Recurring errors (E01 to E35)

Which mistakes keep coming back when a DayZ mod is written, each with its correct form. Check it while you write code, not only when something breaks. This file is the one list; nothing else keeps an index of it.

- **Seen in** names the kind of mod or file the mistake was caught in.
- A `P:\` citation means the correct form was read in that vanilla file. A row with none rests on a measurement in a mod project and is not checked on `P:\`.
- Where two forms of a rule circulate, the row says what vanilla shows and which form to use.
- E21 and E22 are 1.30 changes. Nothing from 1.29 is on `P:\`, so what 1.29 had in their place is not checked there. E23 was measured on a 1.30 pre-release.

Log lines these mistakes produce are triaged by `/dayz-gate` and `/dayz-logwatch` (`skills/dayz-gate/known-errors.json`); this list also covers the mistakes that leave no log line.

## Config and materials

| ID | Error | Correct | Seen in |
|---|---|---|---|
| E01 | `requiredAddons[]={"DabsFramework"}` | Use the `CfgPatches` class names: `{"DF_Scripts"}` or `{"DF_GUI"}`. Third-party fact (Dabs Framework). | A UI mod's `config.cpp` |
| E02 | `imageSets` in `CfgSlots` or at the config root | Inside `CfgMods > <Mod> > defs > imageSets`. | An armour mod |
| E04 | A `.rvmat` `Stage4` procedural texture typed from memory | Copy the stage from a working vanilla `.rvmat` of the same shader. `color(0,1,1,1)` with no `AS` suffix is not the only correct form; vanilla ships both. See "The three material rows" below. | An armour mod |
| E05 | A `.rvmat` `Stage2` detail texture typed from memory | Same rule. Alpha 0.5, `color(0.5,0.5,0.5,0.5,DT)`, is not the only correct form; vanilla ships both. | An armour mod |
| E06 | `.rvmat` fresnel values guessed | Copy `Stage6` from a vanilla material of the same shader, for example `fresnel(1.05,0.67)` in `P:\DZ\gear\camping\data\bagpack_damage.rvmat:71`. | An armour mod |
| E07 | A `.rvmat` damage stage using a procedural colour | Use the vanilla macro textures `generic_damage_mc.paa` and `generic_destruct_mc.paa`, as `bagpack_damage.rvmat:35` does (the files are in `P:\DZ\characters\data\`). | An armour mod |
| E10 | `forcedDiffuse` typed from memory | Copy it from the vanilla material you started from. Alpha 1, `0,0,0,1`, is not the only correct form; vanilla ships both. | An armour mod |
| E21 | (1.30) A custom map's `cfgeconomycore.xml` copied from 1.29, with no motorbike or destructible house root classes | Add `<rootclass name="MotorbikeScript" act="car" reportMemoryLOD="no" />` and `<rootclass name="HouseDestructible" reportMemoryLOD="no" />` beside `CarScript` and `BoatScript`, as in `P:\DZ\worlds\chernarusplus\ce\cfgeconomycore.xml:17` and `:18` (the same pair on Enoch and Sakhal). | DayZ 1.30 Central Economy |
| E28 | A vehicle nested class override in a child mod (`class SimulationModule: SimulationModule`, `class Axles: Axles`, `class Front: Front`, `class Rear: Rear`, `class DamageZones: DamageZones`) with no forward declaration `class X;` at the root of that mod's `CfgVehicles`. CfgConvert stops with `Undefined base class 'X'` and the mod does not load. | Declare `class SimulationModule; class Axles; class Front; class Rear;` (whichever the override uses) at the root of the child mod's `CfgVehicles`. Each `config.cpp` is parsed in its own scope and does not inherit forward declarations from the parent PBO. Nested classes with no `: parent` (`Engine`, `Steering`, `Gearbox`, `Differential`, `Suspension`) merge on their own and need none. | A vehicle child mod |
| E32 | `attachments[] += {...}` in a child mod whose class inherits a vehicle from another PBO. The parsed config holds only the `+=` items, which breaks every slot (battery, wheels, doors). Measured with `CfgConvert -xml`. | Write `attachments[] = {...}` with the full base list plus the new entries at the end. Never rely on `+=` on a parent in another PBO. Same family as the `inventorySlot[] +=` trap in `_shared/conventions/config.md`. | A vehicle child mod |
| E33 | A vehicle nested class override (`SimulationModule`, `Axles`, `Front`, `Rear`) whose `: X` resolves to an empty forward declaration and which leaves out sub-blocks such as `class wheels`. It compiles and loads, then breaks play: a malformed `SimulationModule`, a vehicle nobody can enter, broken slots and wheels. | Follow the original config's shape: `class SimulationModule: SimulationModule`, but inside it `class Axles`, `class Front` and `class Rear` with no `: X` and with the full `class wheels` (`Left`, `Right`). Or do not override at all when only a small physics value changes. | A vehicle child mod |
| E35 | A vehicle (`: CarScript`) or custom wheel class (`: CarWheel`) with no `class DamageSystem { class GlobalHealth ... }`. It crashes with `[Object::GetMaxHealth] No DamageSystemData or not initialized` as soon as health is read (admin `SetHealth01`, damage, collision, possibly sync). The `CarScript` and `CarWheel` bases do not provide it. | Declare `DamageSystem.GlobalHealth.Health { hitpoints; healthLevels[]; }` on the vehicle and on each custom wheel class. `GlobalHealth` alone, without `DamageZones`, is enough. Vanilla: `OffroadHatchback` has `class DamageSystem` with `class GlobalHealth` at `P:\DZ\vehicles\wheeled\config.cpp:1540` to `:1542`. | A quad vehicle mod, first boot |

## Enforce Script

| ID | Error | Correct | Seen in |
|---|---|---|---|
| E03 | The same variable name in sibling scopes | Declare the variable once, before the conditional. | A UI mod, crash |
| E08 | Assuming a function exists because it "makes sense" | Check it on `P:\scripts\` (the Tier 2 search rule), in a loaded pack, or online, before using it. | Several |
| E29 | `ProcessDirectDamage(DT_FIRE_ARM, ...)` copied from another mod. `DT_FIRE_ARM` is not a vanilla symbol, so it does not compile. | Use the enum: `DamageType.FIRE_ARM` (`P:\scripts\3_game\damagesystem.c:10` to `:13`). In vanilla `DT_FIRE_ARM` appears only in a doc comment (`P:\scripts\3_game\entities\object.c:1130`). Any `DT_*` in another mod's source may be that mod's own alias. | A vehicle child mod |
| E30 | A `modded` or derived class declares a member the vanilla base already has, for example `m_NoiseSystem` on `CarScript`. Compile error `Multiple declaration of variable 'X'`. | Use the inherited one (`m_NoiseSystem` is at `P:\scripts\4_world\entities\vehicles\carscript.c:2770`). Before compiling, grep each of your own `m_*` names against the base chain (`carscript.c`, `car.c`, `transport.c`, `entityai.c`, `itembase.c`). | A vehicle child mod |
| E31 | An override whose body uses the base method's parameter name while its own signature names it differently, for example `OnExecuteServer(ActionData actionData)` with a body that reads `action_data`. Compile error `Can't find variable 'X'`. | Copy the base signature, parameter names included, from the vanilla file. See "Parameter names in an override (E31)" below. | A vehicle child mod |
| E34 | `GetInventory().CreateAttachment("<slot>")` or `CreateInInventory("<slot>")` called with a slot name. The call takes the item's class name; when the two differ it creates nothing and logs nothing. Vanilla hides it because slot and class usually share a name (`CarBattery`, `SparkPlug`, `Reflector_1_1`). | Pass the item's class name: the parameter is `typeName` in `CreateAttachment(string typeName)` (`P:\scripts\3_game\systems\inventory\inventory.c:209`). The engine fills the first free compatible slot. Check the class (`CfgVehicles`) against the slot (`CfgSlots`, `inventorySlot`) before writing the call. | A quad vehicle mod |

## Client, server and actions

| ID | Error | Correct | Seen in |
|---|---|---|---|
| E11 | A string read in `ActionCondition` | Strings cannot be net synced. Use an integer id through a sync variable both sides can read. A client only cache passes the menu and then fails the server's `Can()` check (`pickedAction.Can(...)`, `P:\scripts\4_world\classes\useractionscomponent\actionmanagerserver.c:168`). | A player group mod |
| E12 | `IsTakeable()` returning false as the only pickup block, without knowing its side effects | `IsTakeable() == false` stops the two take actions and also drops the item from the vicinity list (`GetVicinityObjects`, `P:\scripts\4_world\classes\useractionscomponent\actiontargets.c:61` to `:64`); custom actions still run. Choose on purpose; both recipes are in "Stopping pickup (E12)" below. | A player group mod |
| E13 | Notifying after clearing a collection | A loop over an empty collection sends nothing. Notify before clearing. | A player group mod |
| E14 | Debugging downstream without checking upstream | Follow the layer order in `debug-protocol.md`: check `IsTakeable` and `AddAction` before `ActionCondition`. | A player group mod |
| E15 | A cache not cleaned on a state change | Every state change updates the cache, on client and server. | A player group mod |
| E16 | A fix written without mapping the client and server boundary | Fill in the client and server data map (`skills/dayz-scope-mod/references/implementation-protocol.md`, "Client and server data map") before writing the fix. | A player group mod |
| E17 | Sync variables registered differently on client and server | Register the same variables in the same order on both sides. Not checked on `P:\`; the stream layout is native. | Networked entities |
| E18 | The wrong side guard during load | Vanilla calls `IsDedicatedServer()` the "Robust check which is preferred than the above, as it is valid much sooner" (`P:\scripts\3_game\global\game.c:1118` to `:1125`). Use it in early init and to skip client only work; after load use `IsServer()` for authority work so single player still runs it (`_shared/conventions/scripts.md`). The stricter form, "always `IsDedicatedServer()`, never `IsServer()`", would skip authority code in single player. | Load time init code |
| E19 | The engine's `version` value written into a save by hand | The engine passes the storage version to `OnStoreLoad(ParamsReadContext ctx, int version)` (`P:\scripts\3_game\entities\entityai.c:2978`); never write or read it yourself. It is the game's storage version, not yours, so write your own version header first for your own fields (`_shared/enscript/patterns/persistence.md`). | vanilla `EntityAI` |
| E22 | (1.30) An action widget shows but F does nothing, or a custom pond drink never lists | Vanilla can show an action whose `CanBeStarted()` is false: the client starts it only when `action.CanBeStarted()` (`P:\scripts\4_world\classes\useractionscomponent\actionmanagerclient.c:336`), and info actions override it to false (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionpartinfo.c:18` to `:21`). Vanilla water, wash and fill actions use `CCTLiquid`, not `CCTWaterSurfaceEx` (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionwashhandswater.c:28`). More in `_shared/enscript/patterns/actions.md`. | DayZ 1.30 actions |
| E25 | A rate limit or validation placed after `super.OnXxxServer`, leaving orphan state | Put it before the `super` call, gated on the inferred intent. `skills/dayz-build-pbo/references/file-checklists.md`, "Refactor: state coherence", the rate limit after an open action's `super` call. | A virtual storage mod |

## Vehicles and models

| ID | Error | Correct | Seen in |
|---|---|---|---|
| E20 | A modded vehicle will not drive and the RPT is clean: wheels mount but do not spin (`WheelCountPresent()` is 0 while `WheelCount()` is N), the chassis bounces or sinks, the steering animates but the simulation does not turn | `CfgSlots.<wheel-slot>.selection` must name a selection that exists in the Fire Geometry LOD of the body and holds a wheel proxy (`proxy:\...`). If it exists only in the visual LODs, alias the Fire Geometry proxy face into the slot's selection name (an additive py3d edit that keeps the visual hide). Mechanism and the py3d fix: `_shared/enscript/depth/vehicle-scripting.md`, "Wheels that never join the simulation". | A quad vehicle mod, `wheelPresent=0` |
| E24 | Blaming the `.p3d` or the config for a placement bug caused by another mod's `Hologram.c` | Grep `modded class Hologram` across every loaded mod before touching the model. Third-party fact: A6_Base_Storage, BaseBuildingPlus and others rewrite `GetProjectionEntityPosition` and `EvaluateCollision`. `/dayz-conflict-check` finds class collisions between mods. | Chests stacking |

## Process

| ID | Error | Correct | Seen in |
|---|---|---|---|
| E09 | Working on past context saturation | Stop, write a checkpoint, hand off (`skills/dayz-scope-mod/references/implementation-protocol.md`, "Checkpoints" and "Handoff document"). | Several |
| E23 | (1.30 pre-release, open) A `HumanCommandScript` subclass declared in `4_World` and started two or more times: every orderly exit crashes client and server | Declare the class the engine starts in `3_Game`, as a thin shell that forwards its hooks to a `Managed` logic object in `4_World`. The workaround is not yet verified in game. See the section below. | A skateboard mod, DayZ 1.30 Experimental |
| E26 | "Keeps the original behaviour" treated as an audit pass when the original has bugs | It is not a goal. Each kept behaviour is a hypothesis to check. `skills/dayz-build-pbo/references/file-checklists.md`, "Refactor: state coherence". | A virtual storage mod |
| E27 | A doubtful pattern labelled "already there" and carried along silently | Stop, get an explicit decision from the user (fix now or flag for later), and grep the sibling files for the same pattern. | A virtual storage mod |

## Keeping the list

- When a session hits a listed mistake, do not add it again; name the existing id in the handoff.
- When a session hits a new mistake for the second time, add a row with the next free id, the correct form and its `P:\` citation or the kind of project it was measured on.
- When a row goes out of date (the engine changed, an official patch), rewrite it to the current fact and keep its id, so files that cite it stay right.
- A mistake that leaves a log line also gets an entry in `skills/dayz-gate/known-errors.json`, so `/dayz-gate` and `/dayz-logwatch` name the fix. E28, E30 and E35 have one.

## The three material rows

E04, E05 and E10 each have two exact values that circulate as "the correct one". Counted over the 34,899 text `.rvmat` files under `P:\DZ\` (ignoring case and white space), vanilla ships both forms of each, and the form usually called the mistake is the more common one:

| Value | Form the texture pack uses | Vanilla files | The other form | Vanilla files |
|---|---|---|---|---|
| `Stage2` detail placeholder | `color(0.5,0.5,0.5,1,DT)` (for example `P:\DZ\animals\canis_lupus\data\fur_alpha.rvmat:27`) | 3,844 | `color(0.5,0.5,0.5,0.5,DT)` (for example `P:\DZ\animals\bos_taurus\data\bull_brown.rvmat:23`) | 1,299 |
| `Stage4` ambient shadow placeholder | `color(1,1,1,1,AS)` (for example `fur_alpha.rvmat:51`) | 4,405 | `color(0,1,1,1)` with no suffix (for example `P:\DZ\gear\camping\data\sea_chest_e.rvmat:119`) | 73 |
| `forcedDiffuse[]` | `{0,0,0,0}` (for example `bull_brown.rvmat:3`) | 16,612 | `{0,0,0,1}` (for example `P:\DZ\characters\backpacks\data\drybag.rvmat:7`) | 1,059 |

So neither value is an error by itself. The rule that holds is E06's: start from a working vanilla `.rvmat` of the same shader and kind of surface, and change only what you must. Defaults and recipes: `_shared/textures/rvmat-stages.md` and `_shared/textures/surface-recipes.md`.

## Stopping pickup (E12)

Two recipes, each with a visible consequence:

- **Vanilla's way for a fixed device.** `PowerGeneratorStatic` returns false from `CanPutInCargo`, `CanPutIntoHands` and `IsTakeable` (`P:\scripts\4_world\entities\building\underground\powergeneratorstatic.c:143` to `:152`, and `IsTakeable` at `:219`). Both take actions refuse a target that is not takeable (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiontakeitem.c:36`). The item then leaves the vicinity list (`actiontargets.c:61` to `:64`), and the action cursor hides for a ground item that is neither takeable nor `IsActionTargetVisible()` (`P:\scripts\5_mission\gui\actiontargetscursor.c:719`). That is why the vanilla generator overrides `IsActionTargetVisible` (`powergeneratorstatic.c:224`). Pattern file: `_shared/enscript/patterns/actions.md`.
- **For an item that keeps its own actions.** Leave `IsTakeable()` true, call `RemoveAction(ActionTakeItem)` and `RemoveAction(ActionTakeItemToHands)` in `SetActions()`, and refuse `CanPutInCargo` and `CanPutIntoHands`. The item stays in the vicinity list and its custom actions keep their cursor.

The mistake E12 names is taking the first recipe without `IsActionTargetVisible()` and then wondering why the custom action has no cursor, or expecting `IsTakeable() == false` to block custom actions. It does not; they never read it unless you write that check.

## Parameter names in an override (E31)

The rule is often stated as "the parameter name in an override must match the base". Vanilla does not bear that out as a compiler rule: `EntityAI` declares `bool CanDetachAttachment (EntityAI parent)` (`P:\scripts\3_game\entities\entityai.c:1540`) and eight vanilla handguard classes override it as `CanDetachAttachment( EntityAI attachment )`, for example `P:\scripts\4_world\entities\itembase\inventory_base\ak74_hndgrd.c:4`. Those files compile, so a different name is legal.

What fails is a body that reads a name its own signature did not declare: the `Can't find variable 'action_data'` came from an override declared with `actionData`. Copying the base signature exactly, names included, removes the mismatch and keeps the code searchable, which is why the row asks for it. All 81 vanilla overrides of `OnExecuteServer` use the base's name `action_data`.

## A `HumanCommandScript` subclass started twice in `4_World` (E23, open)

Measured in game on 1.30 Experimental, server and client, with a skateboard mod's ride command. A source file cannot show it, so it is not checked on `P:\`.

- After two or more rides, with the ride command a `HumanCommandScript` subclass declared in `4_World`, the orderly exit crashed client and server with an access violation while the `World` script module was cleaned up, right after `Leaked '<RideCommand>' script instance (-Nx)!` and before `Leaked 'HumanCommandScript' (+Nx)`, N being the number of rides. After one ride the exit was clean. A constructor and destructor probe counted exactly one of each per ride, and starting the command with `StartCommand_Script` on a new instance or with `StartCommand_ScriptInst` on its class made no difference.
- An empty class deriving from `HumanCommandScript`, declared in `scripts/4_World`, started twice with `StartCommand_ScriptInst` and ending itself after one second each time, crashed the exit the same way: an access violation in the `World` module's teardown right after `Leaked 'X' script instance (-2x)!`, where the bytes before the faulting address are a reference count release.
- The same empty class declared in `scripts/3_Game` exited clean (`Termination successfully completed`), and still printed -2x for the class and +2x for `HumanCommandScript`, in the `Game` module.
- Started once, it exited clean from either module.

The cause is not known. One reading of the leak counts is that creation is counted under `HumanCommandScript` and destruction under the subclass; that is an interpretation, not a measurement. The workaround keeps the class the engine starts in `3_Game`, a thin shell that forwards the command's hooks to a `Managed` logic object in `4_World`; it is not yet verified in game on the real ride command.
