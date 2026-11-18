# API patterns

How to tell an entity's type, the order its lifecycle hooks run in, and the safe way to create entities, cast rays, cook, add a camera, move items and respawn a player from script.

## Type identity

```c
typename t = MyMod_Class;              // the class itself
typename t2 = inst.Type();             // the class of an instance
string s = inst.ClassName();           // script class name, "MyMod_Class"
string cfgName = entity.GetType();     // config class name, for entities
PlayerBase player = PlayerBase.Cast(someEntity);   // null when the cast fails
if (entity.IsKindOf("Weapon_Base")) { }            // config inheritance check
typename wt = ItemBase.StaticType();   // class without an instance
```

`GetType()` returns the `config.cpp` class name; `ClassName()` returns the script class name (`P:\scripts\1_core\proto\enscript.c:37`). For modded items the two can differ, so identify an entity with `GetType()`. `Type()` and the static `StaticType()` are declared at `:52` and `:64`.

### `IsKindOf` follows the config chain

`GetGame().IsKindOf(string cfg_class_name, string cfg_parent_name)` walks the `CfgVehicles` parents of the class, then `CfgAmmo` (`P:\scripts\3_game\global\game.c:1436` to `:1444`). `Object.IsKindOf(string type)` asks the engine the same question for one object (`P:\scripts\3_game\entities\object.c:511` to `:513`). A class declared in script as `class X : Y` can have a different parent in `CfgVehicles` (`class X : Z`), and the check uses the config parent.

This breaks compatibility layers that register "known base" class names, as Expansion and similar frameworks do. Register the script parent when the config parent differs, and no descendant matches: the layer stays in its safe no-op state, and with the log level at `ERROR` its warnings never show. A storage mod met this with `MyMod_Openable_Placeable_Base`, declared `: MyMod_Openable_Base` in script but `: MyMod_Storage_Base` in `CfgVehicles`, so its crates were never matched. Register every direct config base of the concrete classes, not only the script base.

To find it, turn the mod's `config.bin` back into text (`CfgConvert.exe -txt -dst out.cpp config.bin`), rebuild the config chain from the `class X:` lines and compare it with the script chain. Any `*_Placeable_Base`, `*_Coverable_Base` or `*_Static_Base` in the middle that is a child in script but a sibling in config is the first suspect.

## Entity lifecycle

World objects descend from `IEntity` (`P:\scripts\1_core\proto\enentity.c:164`) through `Object` (`P:\scripts\3_game\entities\object.c:64`) to `EntityAI`, then branch into `ItemBase`, `PlayerBase`, infected, animals, buildings and transport. On the server never rely on `GetGame().GetPlayer()`; iterate with `GetPlayers` (see `hard-rules.md`).

| Hook | When it runs | Source |
|---|---|---|
| Constructor | On creation, both sides | |
| `EEInit()` | After the entity is set up in the world | `P:\scripts\3_game\entities\entityai.c:905` |
| `SetActions()` | Registers player actions | `P:\scripts\4_world\entities\itembase.c:246` |
| `OnStoreSave()`, `OnStoreLoad()` | Server persistence | `_shared/persistence/save-load-contract.md` |
| `AfterStoreLoad()` | After the entity and its children loaded | `entityai.c:1419` |
| `OnVariablesSynchronized()` | Client, after synced variables change | |
| `EEDelete()` | The entity leaves the world | `entityai.c:946` |

Call `RegisterNetSyncVariableInt`, `Bool` and `Float` in the constructor, not in `EEInit`. Reported, not checked on `P:\`: a registration made after construction is ignored. `patterns/netsync.md` lists the two other vanilla places, `InitItemVariables()` and `PlayerBase.Init()`.

### Load order of stored entities

Measured in game on DayZ 1.29: stored entities are created after `MissionServer.OnMissionStart` returns, and their `EEInit` runs before `OnStoreLoad` and `AfterStoreLoad`. So a registry that reconciles stored entities must run after `AfterStoreLoad` (each entity registers itself there, the reconcile is deferred), never inside `OnMissionStart`.

An attachment created with `GetInventory().CreateAttachmentEx(type, slotId)` inside `EEInit`, or in the same tick as the parent's `CreateObjectEx`, is counted by the server but never reaches clients: it is invisible and missing from the vicinity panel, and on a stored entity it collides with the restored one. Created one second later with `g_Game.GetCallQueue(CALL_CATEGORY_SYSTEM).CallLater(fn, 1000, false)`, it renders at once. Stock new entities from their creator with a deferred call and a saved "stocked" flag.

## Creating entities

Always check what the create call returns:

```c
Object obj = GetGame().CreateObjectEx(typeName, pos, flags);
EntityAI entity = EntityAI.Cast(obj);
if (!entity)
    return;   // creation failed: keep the kit, stop here
```

### AI creatures

Spawn with `GetGame().CreateObjectEx(type, pos, ECE_PLACE_ON_SURFACE|ECE_INITAI|ECE_EQUIP_ATTACHMENTS)`, adding `ECE_NOPERSISTENCY_WORLD` when a restart should clean it up. `ECE_INITAI` (`2048`, `P:\scripts\3_game\ce\centraleconomy.c:18`) starts the AI; without it the creature stands still like a statue. `ECE_NOPERSISTENCY_WORLD` is `8388608` (`:31`), `ECE_CREATEPHYSICS` is `1024` (`:17`) and `ECE_PLACE_ON_SURFACE` is `1060`, which already contains `ECE_CREATEPHYSICS` (`:38`); the whole flag list runs from `:9` to `:39`. Vanilla examples: `SpawnAI` (`P:\scripts\4_world\entities\manbase\playerbase.c:6807`) and `P:\scripts\4_world\plugins\pluginbase\plugindayzinfecteddebug.c:367`.

With `ECE_PLACE_ON_SURFACE|ECE_INITAI|ECE_CREATEPHYSICS` (`3108`) an infected walks and attacks (measured in game; delete it as soon as the test ends). Surface placement of AI is deferred: `GetPosition()` right after creation returns the requested height, not the ground. Resolve `SurfaceY` before creating when you need the real coordinate.

Never use the `CEApi` force spawn calls (`SpawnEntity`, `SpawnLoot`, `SpawnDE`, `SpawnSingleEntity`, `centraleconomy.c:336` to `:472`): vanilla marks them "DEVELOPER/DIAG ONLY", so a release server does not promise them. The same holds for `ExecuteEnforceScript` (`P:\scripts\3_game\global\game.c:777`). Spawning custom infected at runtime: `_shared/ai/spawning-and-performance.md`.

### Client-local previews with `ECE_LOCAL`

The client can create local-only entities with `CreateObjectEx(cls, pos, ECE_LOCAL|ECE_CREATEPHYSICS|ECE_TRACE)` (`ECE_LOCAL` is `1073741824`, `P:\scripts\3_game\ce\centraleconomy.c:25`). Measured in game, repeated at two map locations: the object is not null, `HasNetworkID()` is false, the server never sees it, and `ObjectDelete` removes it cleanly. It works for `ItemBase`, containers, weapons, clothing, a complete `CarScript` and `SurvivorM_*`. Without `ECE_LOCAL` the client gets null.

To make the preview inert: `dBodyDestroy(obj)`, then `EntityAI.Cast(obj).DisableSimulation(true)` and `SetAllowDamage(false)`. `DisableSimulation` is declared on `Entity` (`P:\scripts\3_game\entities\entity.c:3`), not `Object`, so cast first or the compiler reports `Undefined function Object.DisableSimulation`.

Measured in game, two traps:

- Creatures: `DayZAnimal` and infected are created with `ECE_LOCAL`, but the inert sequence above crashes the client natively, and left alone their local simulation crashes after one or two seconds. This matches the `DZ_LightAI` exclusion in the script console preview (`P:\scripts\5_mission\gui\scriptconsoleitemstab.c:692`); the `Man` half of that exclusion does not apply.
- Camera: after a mission script creates, activates and deletes a `staticcamera` (`CreateObject("staticcamera", pos, true)`, `SetActive`, `ObjectDelete`), `Camera.GetCurrentCamera()` crashes the client natively, in the same tick and one second later. The cycle itself is safe; check the restore by eye, never through that getter. Same family as the client preload trap in `runtime-traps.md`.

### Client-local 3D segments: cables, ropes, beams

Use one client-local `HouseNoDestruct` (`P:\DZ\data\config.cpp:3119`) per segment, created with `CreateObjectEx(type, pos, ECE_LOCAL)` (`P:\scripts\3_game\global\game.c:703`). It is a client-only static that is still an `EntityAI`.

- `SetTransform(m)` (`P:\scripts\1_core\proto\enentity.c:356`) with a basis that is not orthonormal scales the render on that axis. A basis of side times thickness, up times thickness and direction times length, with `m[3]` at the midpoint, turns a 1 m cylinder along +Z into a segment of the wanted size. `GetTransform` returns the scaled basis and `GetScale()` stays 1 (`:447` and `:448`; measured in game).
- `GetBounds` returns zeros on these objects; read the model box with `Object.ClippingInfo(minMax)` (`P:\scripts\3_game\entities\object.c:358`).
- `SetObjectTexture(0, "#(argb,8,8,3)color(r,g,b,1,CO)")` (`P:\scripts\3_game\entities\entityai.c:2881`) recolours the segment only if `model.cfg` declares `sections[] = {"camo"}` for that model (measured in game).
- Use a purpose-built unit segment model, because vanilla props have arbitrary pivots, and spread creation over frames: a burst of a thousand or more segments stalls a frame.

## Rays and surface normals

`DayZPhysics.RaycastRVProxy(params, results, excluded)` with `params.type = ObjIntersectFire` (or Geom) against bare ground returns a `RaycastRVResult` with `obj == null`, `entry == false`, `exit == false` and `surface` set (`cp_grass`, `cp_concrete2`); against an object, `entry` is true (measured in game). A loop that skips `!hit.entry` drops every terrain hit, so a hologram never snaps to the ground and the server ground check fails for any wall on terrain. Skip only object exit points and treat a null `obj` as terrain:

```c
if (!hit) continue;
if (hit.obj && !hit.entry) continue;
```

Neither `RaycastRVResult.dir` nor `RaycastRV`'s `contactDir` is a face normal. Vanilla documents `dir` as "direction outside ... or (in case of line-object collision) direction and size of the intersection" (`P:\scripts\3_game\global\dayzphysics.c:104`), and its own example (`:145` to `:197`) prints a `contactDir` equal to the ray direction (`:186`). Measured in game, `RaycastRVProxy`'s `dir` has a length of only 0.16 to 0.42, so a test such as `dot(dir, fwd) >= 0.9` never passes and `sqrt(dir.x^2 + dir.z^2) >= 0.2` is a coin flip. Measured in game on vertical walls of `Land_House_1W09_Yellow` and `Land_House_1W02`, both fields follow the camera direction, with lengths from about 0.01 to 3.3. A hologram turned by either one faces the camera and only lines up when the player faces the wall squarely; at any other angle it collides with the wall it should hug, which shows as a grey hologram with no action. Use the sign or axis of `dir`, never its size.

For a real normal use `DayZPhysics.RayCastBullet(beg, end, PhxInteractionLayers.BUILDING, ignoreObj, hitObject, hitPos, hitNormal, hitFraction)` (`dayzphysics.c:211`; the layers enum is at `:1` to `:40`). Vanilla callers: `P:\scripts\4_world\classes\environment\environment.c:654`, `P:\scripts\4_world\classes\useractionscomponent\actiontargets.c:384`, `P:\scripts\4_world\classes\undergroundhandlerclient.c:147`. Keep the fire geometry ray for identity and `entry`, accept the physics normal only when both contact points lie within about 15 cm, and fall back to facing the camera. Read in the source, not yet tested in game.

`g_Game.SurfaceY(x, z)` remains a valid ground fallback. Vanilla builds `RaycastRVParams(from, to, m_Projection)` and leaves `with` unset (`P:\scripts\4_world\classes\hologram.c:1438`); `with` is documented only as "ignore object with this object, otherwise collision hits" (`dayzphysics.c:55`), so never rely on it to pick targets.

## Temperature falls with absolute height

`WorldData.GetBaseEnvTemperatureAtPosition(vector pos)` (`P:\scripts\3_game\worlddata.c:227` to `:231`) subtracts `pos[1] * m_TemperaturePerHeightReductionModifier` (0.02 degrees per metre, `:87`) using the absolute height, and `GetBaseEnvTemperatureAtObject` calls it (`:222` to `:225`) for players, items and fireplaces. A room at 3900 m is about 78 degrees colder than the ground, and a player there dies of cold within minutes (measured in game). This override fixed it in game:

```c
modded class WorldData
{
	override float GetBaseEnvTemperatureAtPosition(vector pos)
	{
		float surface = g_Game.SurfaceY(pos[0], pos[2]);
		if (pos[1] - surface > 1000.0)
		{
			vector ground = pos;
			ground[1] = surface;
			return super.GetBaseEnvTemperatureAtPosition(ground);
		}
		return super.GetBaseEnvTemperatureAtPosition(pos);
	}
}
```

Before shipping, limit the condition to your own structure with a `GetType()` check, and plan it into any raised room or platform.

## Custom cookware

The gas stove (`P:\scripts\4_world\entities\itembase\portablegasstove.c:216` to `:222`) and every `FireplaceBase` cooking path, the cooking stand (`P:\scripts\4_world\entities\itembase\fireplacebase.c:1898` to `:1902`), direct slots and the shared wrapper (`:2153` to `:2159`), end in `Cooking.CookWithEquipment`. Its second argument is not a time (the stove passes half the energy used); the cadence is `Cooking.m_UpdateTime`, set by the caller (`P:\scripts\4_world\classes\cooking\cooking.c:37` to `:42`; fireplaces use 3 s). Catch your class in one `modded class Cooking`, advance your own process by `m_UpdateTime`, and return true from `IsCookware()` so the stove and fireplace register the item.

- Attachment rules follow config inheritance. Cookware under `Edible_Base` (every `Bottle_Base`, `P:\DZ\data\config.cpp:3521`) gets the frying pan rule on `Fireplace`, oven only (`P:\scripts\4_world\entities\itembase\fireplacebase\fireplace.c:111` to `:117`), and lid-closed only on `BarrelHoles_ColorBase` (`barrelholes_colorbase.c:160` to `:166`). Only cookware outside `Edible_Base` falls through to `return true` (`fireplace.c:135`) and needs both rules patched.
- To limit which liquids enter, override `GetLiquidContainerMask()` (`P:\scripts\4_world\entities\itembase.c:830`); its only reader is `Liquid.CanFillContainer` (`P:\scripts\4_world\static\liquid.c:248`).
- Keep vanilla cooking off a custom container: `ProcessItemToCook` burns cargo that is not cookware by `PARAM_BURN_DAMAGE_COEF * 100`, 5 health per tick, and boils off `LIQUID_VAPOR_QUANTITY` per tick (`cooking.c:94` to `:105`).
- A cooling `FireplaceBase` cooks its cookware twice per tick: once as registered cookware (`fireplacebase.c:334` to `:341`) and again through the direct slots (`:2059` to `:2081`), so an `IsCookware` item on `DirectCookingA`, `DirectCookingB` or `DirectCookingC` passes through `Cooking.CookWithEquipment` twice per tick while the fire dies. The vanilla frying pan included. Credit cooking time as the smaller of `dt` and the real time since the item's last step, so an item moved between two fires cannot bank time.

## Custom player camera

Register a ride camera from a `modded class DayZPlayerCameras` whose override of the static `RegisterCameras` calls `super` first, then `RegisterCameraCreator`. Use a small id: vanilla uses 1 to 14 and 30 to 32 (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercameras.c:3` to `:16` and `:18` to `:20`, registered at `:46` to `:63`); 32, the motorbike third person camera, is new in DayZ 1.30. Measured in game on a 1.30 dedicated server: id 1171 crashed the server at startup with an access violation under `DayZPlayerTypeCreate`, and id 17 works. The ceiling is unknown, so take a free id from 15 to 29 (one shipped mod uses 15).

Never register the creator from `ModItemRegisterCallbacks.RegisterCustom`; it does not survive. `DayZPlayerTypeUtils.DayZPlayerTypeCreate` registers item types (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:21`), sounds (`:24`), then cameras (`:27`), and `RegisterCameras` (`dayzplayercameras.c:38`) starts by calling `ResetCameraCreators` (`:40`). `RegisterCustom` (`dayzplayercfgbase.c:329`) runs inside `DayZPlayerTypeRegisterItems` (`:334`, called at `:1570`), so its creator is wiped before cameras register. `DayZPlayerTypeInitMovement` (`:10` to `:14`) also calls `DayZPlayerTypeRegisterItems`; when the engine calls it is not visible in script.

## Inventory moves

```c
PlayerBase player = PlayerBase.Cast(GetGame().GetPlayer());
if (!player)
    return;
EntityAI item = player.GetInventory().CreateInInventory(className);
if (!item)
    return;
```

### Skip null entries from `EnumerateInventory`

Check each entry that `GetInventory().EnumerateInventory(...)` returns before use, as vanilla does in all five `InventoryTraversalType.LEVELORDER` calls (`P:\scripts\4_world\static\miscgameplayfunctions.c:131`, checked at `:136`; `:349` at `:354`; `:1222` at `:1239`; `P:\scripts\4_world\entities\manbase\playerbase.c:7004` at `:7011`; `P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionskinning.c:238` at `:241`). Never pass an unchecked entry to a `notnull` parameter such as `HasInventoryJunctureItem(notnull EntityAI item)` (`P:\scripts\3_game\global\game.c:757`).

Measured in game on a DayZ 1.30 server with Expansion AI: an array filled only by a `LEVELORDER` traversal led to `Virtual Machine Exception: NULL pointer to instance` at `HasInventoryJunctureItem(entry)`. The script carried on and counted the item as kept, so the bug showed as a wrong result rather than a crash. With `if (entry && ...)` the exception stopped. Unverified: what a null stands for inside the native traversal, and whether `PREORDER` and `INORDER` return nulls too.

### A take call's return value is not success

Test an attach by identity: `FindAttachment(slot) == item`. Never trust the return of a `Take*` or `LocalTake*` call.

- On a live player a `LOCAL` take returns true unconditionally. The `LOCAL` case of `DayZPlayerInventory.TakeToDst` (`P:\scripts\4_world\systems\inventory\dayzplayerinventory.c:3728`) runs `LocationSyncMoveEntity(src, dst); return true;` (`:3808` to `:3810`), gated only by `IsAlive()`, which is `!IsDamageDestroyed()` (`P:\scripts\3_game\entities\object.c:517` to `:520`), so a freshly spawned survivor always passes. In DayZ 1.29 `Man` overrode `LocalTakeEntityAsAttachmentEx` (1.29 `man.c:503` to `:518`), so the `EntityAI` base (1.29 `entityai.c:2012` to `:2015`) never ran; the call went through `HumanInventory.TakeEntityAsAttachmentEx` (1.29 `humaninventory.c:308` to `:331`; an item on the ground falls through to `super`) to `DayZPlayerInventory.TakeToDst` (1.29 `dayzplayerinventory.c:1904`), whose `case InventoryMode.LOCAL:` returned true the same way (1.29 `:1984` to `:1986`). These 1.29 line numbers are from a build that is not on `P:\`. In 1.30 the call is `[Obsolete]` in favour of `LocalTakeEntityToTargetAttachmentEx` (`P:\scripts\3_game\entities\entityai.c:4880` to `:4884`), and the 1.30 path from the call to `TakeToDst` has not been traced.
- An occupied slot gives a silent false success. `GameInventory.TakeEntityAsTargetAttachmentEx` finds the slot taken, calls `CombineItemsEx(item, true)` on the server or `CombineItemsClient(item, true)` otherwise, and returns true without attaching (`P:\scripts\3_game\systems\inventory\inventory.c:1106` to `:1118`). A swap for the same type is invisible to `GetType()`.
- `CanAddAttachmentEx` returns a bool with no reason (`inventory.c:246`).
- Use the `InventorySlots` constants (`P:\scripts\3_game\systems\inventory\inventoryslots.c:7`), not strings. `GetSlotIdFromString` looks up `Slot_<name>` and config uses title case (`Slot_Body name="Body"`, `P:\scripts\config.cpp:90` to `:94`); whether the runtime lookup ignores case is unverified.

Read in the source, not yet confirmed in game. Equipping NPCs and survivors from script: `_shared/ai/spawning-and-performance.md`.

## Respawning a player from script

On the client, before changing anything, refuse the request when the local `PlayerBase` exists, `IsAlive()`, `!IsUnconscious()` and `!IsRestrained()`. A null player is not refused. To give a living player a new body, kill it first.

`RespawnPlayer()` is `proto native void RespawnPlayer();` (`P:\scripts\3_game\global\game.c:1107`), called as `GetGame().RespawnPlayer()`. On the server, `MissionServer.OnClientRespawnEvent(PlayerIdentity identity, PlayerBase player)` (`P:\scripts\5_mission\mission\missionserver.c:611` to `:624`) kills the character only if it is unconscious or restrained (`:615`, `SetHealth("", "", 0.0)` at `:621`) and ignores anyone else. The client rule is the complement of `:615`.

The vanilla menus split it the same way:

- The in-game menu sets `playerAlive = player && player.GetPlayerState() == EPlayerStates.ALIVE` (`P:\scripts\5_mission\gui\ingamemenu.c:321`) and shows Respawn only with `m_RespawnButton.Show(!playerAlive)` (`:326`), so a null player counts as not alive, and the unconscious respawn button only when the player is alive, unconscious and cfggameplay's `disableRespawnInUnconsciousness` is off (`:325`).
- A confirmed dialog is dropped if `player && player.IsAlive() && !player.IsUnconscious()` (`:286` to `:291`).
- `InGameMenu.GameRespawn(bool random)` (`:345` to `:363`) calls `RespawnPlayer()` (`:348`), then `SimulateDeath(true)` (`:353`) and the dead screen (`:354`), then `SetPlayerRespawning(true)` (`:359`).
- `SimulateDeath(true)` (`P:\scripts\4_world\entities\dayzplayerimplement.c:844` to `:881`) locks the controls (`:849`), fades the dead screen to black (`:868`) and mutes the sound (`:870` to `:874`).
- The only `SetPlayerRespawning(false)` is in `PlayerBase.OnPlayerLoaded()` (`P:\scripts\4_world\entities\manbase\playerbase.c:2569`, at `:2595`) for the controlled player (`:2585`), and the mission's pause handling returns early while `IsPlayerRespawning()` (`P:\scripts\5_mission\mission\missiongameplay.c:1314`).
- `disableRespawnInUnconsciousness` is read only by the two in-game menus (`ingamemenu.c:325`, `P:\scripts\5_mission\gui\ingamemenuxbox.c:599`), never by `OnClientRespawnEvent`.

Signatures: `IsAlive()` on `Object` (`P:\scripts\3_game\entities\object.c:517`), `IsUnconscious()` on `Man` (`P:\scripts\3_game\entities\man.c:63`), `IsRestrained()` on `DayZPlayerImplement` (`dayzplayerimplement.c:3935`); `PlayerBase` overrides both (`playerbase.c:3925`, `:2219`).

Measured in game on DayZ 1.30 with a custom respawn mode: a copy of `GameRespawn` without the check reported success on a living, conscious player and nothing happened. With the check, the living player was refused and could still move and use the menu; after a kill the respawn worked. The check reads replicated state, so right after a kill the client can still see the player alive; retry once the death reaches the client. Unverified: whether the client stays locked after a request the server ignores (read from the code), and the unconscious and restrained paths.

## Config lookups, strings and maths

`language-builtins.md` covers `ConfigIsExisting` and the `ConfigGet*` calls, string operations, and maths and vector helpers. Reflection is in `reflection-api.md` and the global functions in `global-functions.md`.
