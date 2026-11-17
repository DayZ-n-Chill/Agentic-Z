# API patterns

Recurring Enforce Script API patterns and the traps measured around them: type identity, entity lifecycle, creating entities (server, client-local, AI), raycasts and surface normals, temperature, cooking, custom cameras, inventory moves and respawn. A line cited as `P:\...:N` was opened on `P:\`; "measured in game" results name the mod and build that measured them and were not re-run here; 1.29 line numbers are for a build that is not on `P:\`.

## Type system quick reference

```
// typename — the class itself (compile-time)
typename t = MyClass;              // class reference
typename t2 = inst.Type();         // get typename from instance

// ClassName() — script class name as string
string s = inst.ClassName();       // "MyClass"
// same as:
string s2 = inst.Type().ToString(); // "MyClass"

// GetType() — config.cpp entry name (for entities)
string cfgName = entity.GetType(); // config class name (preferred over ClassName for entities)

// Cast<> — safe downcast (returns null on failure)
PlayerBase player = PlayerBase.Cast(someEntity);
if (player) { /* safe */ }

// IsKindOf — inheritance check against config class name
string kWeapon = "Weapon_Base";
if (entity.IsKindOf(kWeapon)) { /* is a weapon */ }

// StaticType — get typename without instance
typename wt = ItemBase.StaticType(); // class, no instance needed
```

**Key distinction**: `GetType()` returns the `config.cpp` class name (what the entity is in game data), `ClassName()` returns the script class name (what the script class is in code; `P:\scripts\1_core\proto\enscript.c:37`). For modded items these can differ. Prefer `GetType()` to identify an entity. `Type()` and the static `StaticType()` are declared at `P:\scripts\1_core\proto\enscript.c:52` and `:64`.

### `IsKindOf` follows the config chain, not the script chain

`GetGame().IsKindOf(string cfg_class_name, string cfg_parent_name)` walks the `CfgVehicles` parents of the class and then `CfgAmmo` (`P:\scripts\3_game\global\game.c:1436-1444`); `Object.IsKindOf(string type)` asks the engine the same question for that object (`P:\scripts\3_game\entities\object.c:511-513`). A class declared in script as `class X : Y` can have another parent in `CfgVehicles` (`class X : Z`), with `Y` and `Z` siblings in config. The check uses the config parent.

Recurring failure (reported from the LF_VStorage mod, 2026-05-20): a compatibility layer registers "verified base" class names, as Expansion and similar frameworks do, and registers the script parent, which is not the config parent. Every descendant then silently fails to match, the layer goes into its defensive no-op state, and the feature is not applied to that subclass; with the log level at `ERROR` the diagnostic warnings are filtered out. The documented case: `A6_Openable_Placeable_Base` is declared `: A6_Openable_Base` in script but `: A6_Storage_Base` in `CfgVehicles`, so `A6_MilitaryStorageCrate` was never matched. The fix was to register every direct config base of the concrete classes that have cargo, not only the "logical" script base.

How to diagnose it: when a class "is not caught" by a hook that should cover it through inheritance, turn the mod's `config.bin` back into text (`CfgConvert.exe -txt -dst out.cpp config.bin`), search for `class X:` and rebuild the config chain, then compare it with the script chain. Any `*_Placeable_Base`, `*_Coverable_Base` or `*_Static_Base` in the middle that is a child in script but a sibling in config is a suspect. It takes about 30 seconds and removes most of the search space.

## Entity lifecycle quick reference

World objects descend from `IEntity` (`P:\scripts\1_core\proto\enentity.c:164`) through `Object` (`class Object extends IEntity`, `P:\scripts\3_game\entities\object.c:64`) to `EntityAI`, then branch into items (`ItemBase`), players (`PlayerBase`), infected, animals, buildings and transport (the StarDZ modding wiki's summary, CLAIM-STARDZ-ENTITY-ROOT; take signatures from `P:\scripts\`, not from a summary). On the server do not rely on `GetGame().GetPlayer()`; iterate with `GetPlayers` (see the table in `hard-rules.md`).

```
Constructor      → Called on object creation (both client/server)
EEInit()         → Called after entity is fully initialized in world
SetActions()     → Register player actions (server)
OnStoreSave()    → Persistence: write SyncVars to storage (server)
OnStoreLoad()    → Persistence: read SyncVars from storage (server)
OnVariablesSynchronized() → SyncVar changed on client (client)
EEDelete()       → Entity being removed from world
Destructor       → Object being garbage collected
```

The vanilla declarations: `EEInit` (`P:\scripts\3_game\entities\entityai.c:905`), `EEDelete` (`:946`), `AfterStoreLoad` (`:1419`), and `SetActions` on `ItemBase` (`P:\scripts\4_world\entities\itembase.c:246`).

**Registration timing**: call `RegisterNetSyncVariableInt`, `Bool` and `Float` in the constructor, not in `EEInit`. The knowledge pack reports that a registration made after construction is ignored. (`skills/_shared/enscript/patterns/netsync.md` lists the other two vanilla places: `InitItemVariables()` and `PlayerBase.Init()`.)

**Storage load order and attachments at creation (SP-LFS-3, measured 2026-09-10, DayZDiag 1.29)**: persisted entities are created after `MissionServer.OnMissionStart` returns (three `Print`s: the `OnMissionStart` dump came at server script log line 33, the stored entities' `EEInit`/`AfterStoreLoad` at 49-61), and `EEInit` runs before `OnStoreLoad`/`AfterStoreLoad`. Consequences: (a) a registry that reconciles persisted entities must run after `AfterStoreLoad` (self-register there, reconcile deferred), never inside `OnMissionStart`; (b) an attachment created with `GetInventory().CreateAttachmentEx(type, slotId)` inside `EEInit` — or in the same tick as `CreateObjectEx` of the parent — is counted by the server but never reaches clients (invisible, absent from the vicinity panel) and on a stored entity collides with the restored one; created 1 s later via `g_Game.GetCallQueue(CALL_CATEGORY_SYSTEM).CallLater(fn, 1000, false)` it renders immediately. Stock new entities from their creator with a deferred call and a persisted "stocked" flag. Origin: the LFSecure mod's armory probes.

## Common API patterns

### Safe entity creation

```
// Always check the return of CreateObjectEx
Object obj = GetGame().CreateObjectEx(typeName, pos, flags);
EntityAI entity = EntityAI.Cast(obj);
if (!entity)
{
    // Creation failed: do not delete the kit, do not go on
    return;
}
```

### AI creature spawn — ECE flags (SP-048)

The production way to spawn AI creatures is `GetGame().CreateObjectEx(type, pos, ECE_PLACE_ON_SURFACE|ECE_INITAI|ECE_EQUIP_ATTACHMENTS[|ECE_NOPERSISTENCY_WORLD])`. `ECE_INITAI` (=2048, `P:\scripts\3_game\ce\centraleconomy.c:18`) is what initializes the AI — without it the creature spawns inert. `ECE_NOPERSISTENCY_WORLD` (=8388608, `P:\scripts\3_game\ce\centraleconomy.c:31`) lets a restart clean it up. Vanilla patterns: `P:\scripts\4_world\entities\manbase\playerbase.c:6807` (`SpawnAI`), `P:\scripts\4_world\plugins\pluginbase\plugindayzinfecteddebug.c:367`. Do not use the `CEApi` force-spawn methods (`SpawnEntity`, `SpawnLoot`, `SpawnDE`, `SpawnSingleEntity`, `P:\scripts\3_game\ce\centraleconomy.c:336-472`): vanilla marks them "DEVELOPER/DIAG ONLY", so they are not something a release `DayZServer_x64` promises (the same holds for `ExecuteEnforceScript`, `P:\scripts\3_game\global\game.c:777`). [VERIFIED in game on a production server 2026-07-02, GameMaster mod] See also the `dayz-characters` skill (spawning custom infected at runtime).


### Client-local preview entity: the `ECE_LOCAL` pattern (SP-181)

The client can create local-only entities with `CreateObjectEx(cls, pos, ECE_LOCAL|ECE_CREATEPHYSICS|ECE_TRACE)` (`ECE_LOCAL`=1073741824, `P:\scripts\3_game\ce\centraleconomy.c:25`). Return is non-null, `HasNetworkID()==false`, invisible to the server (`GetObjectsAtPosition` authoritative = 0 hits in 144/144 scans), deletable with `ObjectDelete` without residue. Verified for `ItemBase`, containers, weapons (`CfgWeapons`), clothing, a complete `CarScript`, and `SurvivorM_*` (a `Man`). Without `ECE_LOCAL` the client returns null (control reproduced). To make it inert after the spawn: `dBodyDestroy(obj)` + `EntityAI.Cast(obj).DisableSimulation(true)` + `SetAllowDamage(false)` — note: `DisableSimulation` is declared in Entity (`P:\scripts\3_game\entities\entity.c:3`), not in Object; cast first or you get compile error `Undefined function Object.DisableSimulation`. [VERIFIED in game 2026-08-06, more than 12 repetitions at 2 map locations, LF-COM mod]

**Trap, creatures:** `DayZAnimal` and infected do get created with `ECE_LOCAL`, but (a) the make-inert sequence above on a freshly created creature is a native client crash (RPT stack in the caller), and (b) left as they are, their local simulation crashes after about 1 to 2 s (a fault with no script stack). Consistent with the `DZ_LightAI`/`Man` exclusion from the script-console preview (`P:\scripts\5_mission\gui\scriptconsoleitemstab.c:692`) — the `Man` half of that exclusion does not apply (SurvivorM works).

**Trap, camera:** after creating and deleting a `staticcamera` script in mission (`CreateObject("staticcamera", pos, true)` + `SetActive(true/false)` + `ObjectDelete`), `Camera.GetCurrentCamera()` is poisoned: a native crash with identical fault bytes both in the same tick and 1 s later (2 repros). The activate/restore/delete cycle itself is safe (`restored=1` verified); verify the restore visually (capture), never through that getter. Same family as SP-064 (`runtime-traps.md`).

### Client-local 3D segments (cables, ropes, beams): a scaled `SetTransform` basis (SP-441)

[EXACT] One client-local `HouseNoDestruct` (`P:\DZ\data\config.cpp:3119`) per segment, created with `CreateObjectEx(type, pos, ECE_LOCAL)` (`P:\scripts\3_game\global\game.c:703`, `P:\scripts\3_game\ce\centraleconomy.c:25`), is a client-only static that is still an `EntityAI`. [EXACT] `SetTransform(m)` (`P:\scripts\1_core\proto\enentity.c:356`) with a basis that is not orthonormal scales the render on that axis: basis = (side*thickness, up*thickness, dir*length) and `m[3]` = segment midpoint turns a 1 m cylinder over +Z into a cable segment of the wanted length and thickness; `GetTransform` returns the scaled basis and `GetScale()` stays 1 (`P:\scripts\1_core\proto\enentity.c:447-448`) (measured in game, DayZDiag 1.29). [EXACT] `GetBounds` returns zeros on these objects — take the model box from `Object.ClippingInfo(minMax)` (`P:\scripts\3_game\entities\object.c:358`). [EXACT] `SetObjectTexture(0, "#(argb,8,8,3)color(r,g,b,1,CO)")` (`P:\scripts\3_game\entities\entityai.c:2881`) recolours a selection only if `model.cfg` declares `sections[] = {"camo"}` for that p3d; without that entry the face texture always shows (measured in game, DayZDiag 1.29). [DESIGN] Use a purpose-built unit segment model (vanilla props have arbitrary pivots) and spread creation over frames: a four-digit burst of segments visibly stalls one frame.


### Infected alive from script: the full ECE flag set (SP-287)

`GetGame().CreateObjectEx(type, pos, ECE_PLACE_ON_SURFACE|ECE_INITAI|ECE_CREATEPHYSICS)` (= 3108; `P:\scripts\3_game\ce\centraleconomy.c:9-39`: CREATEPHYSICS 1024, INITAI 2048, PLACE_ON_SURFACE 1060). Without `ECE_INITAI` it is a statue; with all three it walks and attacks (12.7 m in ~16 s, player health 0.695→0.483 — delete as soon as measured). **Surface placement of the AI is deferred**: `GetPosition()` immediately after creation returns the requested y (0), not the surface y; if you need an honest coordinate, resolve `SurfaceY` before creating.

### Placement and ground raycasts: `RaycastRVProxy` does not flag terrain with `entry`, and `dir` is not a unit normal (SP-LFS-1)

[MEASURED in game, DayZDiag 1.29.163709, LFSecure mod] `DayZPhysics.RaycastRVProxy(params, results, excluded)` with `params.type = ObjIntersectFire` (or Geom) against natural ground returns a `RaycastRVResult` with `obj == null`, `entry == false`, `exit == false` and `surface` set (`cp_grass`, `cp_concrete2`); against an object it returns `entry == true`. A loop that skips `!hit.entry` therefore drops every terrain hit: the hologram never snaps to the ground and the server ground check fails with "no ground" for any wall standing on terrain (LFSecure `LFS_HologramMod.c:116`, `LFS_Door_Kit.c:144`). Skip only object exit points: `if (!hit) continue; if (hit.obj && !hit.entry) continue;`, and treat `hit.obj == null` as terrain. `RaycastRVResult.dir` is documented as "direction outside ... or (in case of line-object collision) direction and size of the intersection" (`P:\scripts\3_game\global\dayzphysics.c:104`): measured magnitudes 0.16-0.42, so `dot(dir, fwd) >= 0.9` never passes and `sqrt(dir.x^2 + dir.z^2) >= 0.2` is a coin flip. Use it for sign/axis only. Superseded on 2026-09-09 (SP-LFS-2 below): `DayZPhysics.RaycastRV(... contactDir ...)` is not a surface normal either; the earlier advice to take the normal from it, as the LFPowerGrid mod's `LFPG_HologramMod.c` does (its lines 542 and 829), was wrong and that mod carries the same hidden defect. `g_Game.SurfaceY(x, z)` as the ground fallback (line 843 of the same LFPowerGrid file) stays valid; vanilla builds `RaycastRVParams(from, to, m_Projection)` at `P:\scripts\4_world\classes\hologram.c:1438` and leaves `with` unset. `RaycastRVParams.with` is documented only as "ignore object with this object, otherwise collision hits" (`P:\scripts\3_game\global\dayzphysics.c:55`): do not rely on it to restrict or select targets.

### Surface normals: neither `RaycastRVResult.dir` nor `RaycastRV.contactDir` is one, use `RayCastBullet` (SP-LFS-2)

[MEASURED in game, DayZDiag 1.29.163709, LFSecure mod, 2026-09-09] For object hits both fields carry the ray direction, not the face normal: `RaycastRVProxy` `dir` on a dozen vertical wall components of `Land_House_1W09_Yellow` had Y between 0.25 and 0.45 (the camera pitch), and `RaycastRV` `contactDir` on `Land_House_1W02` pointed the same way with magnitudes 0.01-3.3 ("direction and size of the intersection", `P:\scripts\3_game\global\dayzphysics.c:104`; the doc example at `P:\scripts\3_game\global\dayzphysics.c:170-181` prints a `contactDir` equal to the ray direction). A hologram yaw derived from either faces the camera: it looks aligned only when the player faces the wall squarely, and at any other angle the ghost's box collides with the wall it is supposed to hug (the "grey hologram, no action" symptom). The LFPowerGrid file named above inherits this (its lines 542 and 711); its floor/wall/ceiling split works only because camera pitch correlates with the surface aimed at. For a physics normal use `DayZPhysics.RayCastBullet(beg, end, PhxInteractionLayers.BUILDING, ignoreObj, hitObject, hitPos, hitNormal, hitFraction)` (`P:\scripts\3_game\global\dayzphysics.c:211`; `enum PhxInteractionLayers` is at `P:\scripts\3_game\global\dayzphysics.c:1-40`; vanilla callers `P:\scripts\4_world\classes\environment\environment.c:654`, `P:\scripts\4_world\classes\useractionscomponent\actiontargets.c:384`, `P:\scripts\4_world\classes\undergroundhandlerclient.c:147`), keep the fire-geometry ray for identity and `entry`, accept the normal only when both contacts lie within ~15 cm, and log which source the pose used (`src phx|ray`). The physics path shipped in a later LFSecure release and had not yet been exercised in game; its fallback (face the camera) is the behaviour the earlier releases accepted. The `dir` and `contactDir` findings were measured in game; the `RayCastBullet` advice was read in the source only.

### Ambient temperature falls with absolute height: elevated structures freeze players (SP-LFS-5)

`WorldData.GetBaseEnvTemperatureAtPosition(vector pos)` (`P:\scripts\3_game\worlddata.c:227-231`) subtracts `pos[1] * m_TemperaturePerHeightReductionModifier` (0.02 °C/m, `:87`) using the absolute Y, and `GetBaseEnvTemperatureAtObject` delegates to it (`:222-225`; used by `Environment` for players, `ItemBase` for items, fireplaces). A room at 3900 m is ~78 °C colder than ground level: the player died of hypothermia within minutes (LFSecure, 2026-09-10). The fix, measured in game ("normal temperature in the room"):

```c
modded class WorldData
{
	override float GetBaseEnvTemperatureAtPosition(vector pos)
	{
		float surface = g_Game.SurfaceY(pos[0], pos[2]);
		if (pos[1] - surface > 1000.0)   // far above the terrain: use the ground under it
		{
			vector ground = pos;
			ground[1] = surface;
			return super.GetBaseEnvTemperatureAtPosition(ground);
		}
		return super.GetBaseEnvTemperatureAtPosition(pos);
	}
}
```

Restrict the condition to your own structure (class name check from 3_Game via `GetType()`) before shipping; put the override in the contract of any elevated room/platform design.

### Custom cookware: every vanilla heat source ends in `Cooking.CookWithEquipment` (SP-430)

[EXACT][CLAIM-ENF-COOKWITHEQUIPMENT-HUB] The gas stove (`P:\scripts\4_world\entities\itembase\portablegasstove.c:216-222`) and every `FireplaceBase` cooking path — cooking stand (`P:\scripts\4_world\entities\itembase\fireplacebase.c:1898-1902`), direct slots, and the common wrapper (`P:\scripts\4_world\entities\itembase\fireplacebase.c:2153-2159`) — converge on `Cooking.CookWithEquipment`. The second argument is not a time (on the stove it is 0.5 x consumed energy); the cadence is `Cooking.m_UpdateTime`, set by the caller (`P:\scripts\4_world\classes\cooking\cooking.c:37-42`; fireplaces use 3 s) (DayZ 1.30.164014 Exp). Intercept it for your class in one `modded class Cooking` and advance your own process by `m_UpdateTime`; return `IsCookware() == true` so the stove and the fireplace register the item.

[EXACT] Attachment gates follow config inheritance, not script classes: a cookware under `Edible_Base` (every `Bottle_Base`, `P:\DZ\data\config.cpp:3521`) gets the frying-pan rule on `Fireplace` — oven only (`P:\scripts\4_world\entities\itembase\fireplacebase\fireplace.c:111-117`) — and closed-lid-only on `BarrelHoles_ColorBase` (`P:\scripts\4_world\entities\itembase\fireplacebase\barrelholes_colorbase.c:160-166`); only cookware outside `Edible_Base` falls through to `return true` (`P:\scripts\4_world\entities\itembase\fireplacebase\fireplace.c:135`) and needs those two gates patched. To restrict which liquid can enter the container, override `GetLiquidContainerMask()` (`P:\scripts\4_world\entities\itembase.c:830`): its only consumer is `Liquid.CanFillContainer` (`P:\scripts\4_world\static\liquid.c:248`).

[DESIGN] Do not let vanilla cooking run on a custom container: `ProcessItemToCook` burns non-cookware cargo by `PARAM_BURN_DAMAGE_COEF * 100` = 5 health per tick and boils off `LIQUID_VAPOR_QUANTITY` per tick (`P:\scripts\4_world\classes\cooking\cooking.c:94-105`).

[EXACT] **A cooling `FireplaceBase` cooks its cookware twice per tick** (SP-439): while cooling it cooks the registered cookware (any `IsCookware` item in any slot, `P:\scripts\4_world\entities\itembase\fireplacebase.c:334-341`) and then every direct slot in the same tick (`P:\scripts\4_world\entities\itembase\fireplacebase.c:2059-2081`): an `IsCookware` on `DirectCookingA/B/C` passes twice through `Cooking.CookWithEquipment` per tick while the fire dies (the vanilla frying pan included). [DESIGN] Credit cooking time as `min(dt, real time since the item's last step)` so an item alternating between two fires cannot bank time.

### Custom player camera: a small id, registered in `RegisterCameras` (LFSkateboard mod)

[EXACT][CLAIM-ENF-CAMERA-CREATOR-ID-130] A ride camera registered with `RegisterCameraCreator` under id 1171, from a `modded class DayZPlayerCameras` whose override of the static `RegisterCameras` calls `super` first, crashed the dedicated server at startup (DayZDiag 1.30.164014 Exp server, LFSkateboard, 2026-10-07): an access violation, with that override on the script stack under vanilla's `DayZPlayerTypeCreate` (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:27`). With id 17 the same camera works in game. Vanilla's ids are 1-14 and 30-32 (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercameras.c:3-16` and `:18-20`, each registered with its class at `:46-63`); 32, the motorbike's third-person camera, is new in 1.30, and 1.29 has 1-14, 30 and 31. The id ceiling was not measured: take a free id in the gap 15-29 (LFTurret's P0 used 15).

Register the creator in that override, after `super`, and not from `ModItemRegisterCallbacks.RegisterCustom`, where LFSkateboard's did not survive. [EXACT][CLAIM-ENF-CAMERA-CREATOR-RESET-ORDER] Vanilla's order explains it: `DayZPlayerTypeUtils.DayZPlayerTypeCreate` registers the item types (`DayZPlayerTypeRegisterItems`, `P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:21`), then the sounds (`:24`), then the cameras (`DayZPlayerCameras.RegisterCameras`, `:27`), and `RegisterCameras` (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercameras.c:38`) begins by calling `ResetCameraCreators` on the player type (`:40`). `RegisterCustom` (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:329`) is called inside `DayZPlayerTypeRegisterItems` (`:334`, the call at `:1570`), so a creator it registers is reset before the cameras are registered. `DayZPlayerTypeInitMovement` (`:10-14`) calls `DayZPlayerTypeRegisterItems` too; when the engine calls it is not visible in script. These are the lines on `P:\`. 1.29 has the same code, with the `RegisterCustom` call at line 1487 of its `dayzplayercfgbase.c` and `RegisterCameras` at line 37 of its `dayzplayercameras.c`, the reset at line 39.

### Safe inventory operations

```
PlayerBase player = PlayerBase.Cast(GetGame().GetPlayer());
if (!player)
    return;
EntityAI item = player.GetInventory().CreateInInventory(className);
if (!item)
    return;
// item created successfully
```

### `EnumerateInventory` results: skip null entries before use (SP-525)

[EXACT][CLAIM-ENF-ENUMINV-SKIP-NULL] Check each entry of the array that `GetInventory().EnumerateInventory(...)` fills before you use it, as vanilla does: the five `InventoryTraversalType.LEVELORDER` calls in the vanilla scripts on `P:\` each test the entry first (`P:\scripts\4_world\static\miscgameplayfunctions.c:131` → `:136`, `:349` → `:354`, `:1222` → `:1239`; `P:\scripts\4_world\entities\manbase\playerbase.c:7004` → `:7011`; `P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionskinning.c:238` → `:241`). Never pass an unchecked entry to a `notnull` parameter, such as that of `HasInventoryJunctureItem(notnull EntityAI item)` (`P:\scripts\3_game\global\game.c:757`).

[EXACT][CLAIM-ENF-ENUMINV-NULL-RUNTIME-130] Measured in dayz-mcp's Expansion AI adapter (PR #410, DayZDiag 1.30 server with Expansion AI): in two in-game runs on 2026-11-14, a fresh array filled only by `EnumerateInventory(InventoryTraversalType.LEVELORDER, entries)` led to `Virtual Machine Exception: NULL pointer to instance` at `HasInventoryJunctureItem(entry)`. The script went on and the candidate was counted as kept, so the defect showed as a wrong result, not a crash. With `if (entry && ...)` in the loop, the run of 2026-11-15 logged no such exception and its sweep deleted the dropped items. Not established: what the null stands for inside the native traversal (not visible in script), whether `PREORDER` or `INORDER` return nulls too, and whether a null ever stands for a real item. That `LEVELORDER` returns nulls is inferred from the exception and its disappearance; no null was seen directly.

### Scripted attach on a live player: the return value is not success (SP-184)

**Code review check, first:** the return of an inventory `Take*` or `LocalTake*` call is not success. The test is identity: `FindAttachment(slot) == item`.

**Live player: a `LOCAL` take returns `true` unconditionally.** On 1.29, on a live player/survivor, `LocalTakeEntityAsAttachmentEx` does not execute the EntityAI base (1.29 `entityai.c:2012-2015`) — `Man` overrides it (1.29 `man.c:503-518`) → `HumanInventory.TakeEntityAsAttachmentEx` (1.29 `humaninventory.c:308-331`; item on GROUND falls through to `super` GameInventory) → `DayZPlayerInventory.TakeToDst` (1.29 `dayzplayerinventory.c:1904`), whose `case InventoryMode.LOCAL:` does `LocationSyncMoveEntity(src,dst); return true` **unconditionally** (1.29 `:1984-1986`), gated by `IsAlive()` (= `!IsDamageDestroyed`, 1.29 `object.c:523-526` — a freshly spawned survivor is always alive). (Since 1.30: `LocalTakeEntityAsAttachmentEx` is `[Obsolete]` in favour of `LocalTakeEntityToTargetAttachmentEx` (`P:\scripts\3_game\entities\entityai.c:4880-4884`) and `Man` no longer overrides it; the `LOCAL` case of `DayZPlayerInventory.TakeToDst` (`P:\scripts\4_world\systems\inventory\dayzplayerinventory.c:3728`) still moves and returns `true` (`:3808-3810`), but the 1.30 path from the call to it was not traced.) Corollary: on live players that return cannot be treated as a failure signal; citing the EntityAI base as the live receiver's semantics is the same failure as LL-222.

**An occupied destination slot is a silent false success.** `GameInventory.TakeEntityAsTargetAttachmentEx` does `CombineItemsClient(item)` and `return true` without attaching the new item (`P:\scripts\3_game\systems\inventory\inventory.c:1106-1118`) — the slot keeps the old item (same-type swap is invisible to `GetType()`).

**The correct test is identity, not the return.** `FindAttachment(slot) == item` by entity identity + `return_liar` telemetry when return is true and find ≠ item. `CanAddAttachmentEx` returns bool only, no reason (`P:\scripts\3_game\systems\inventory\inventory.c:246`). Slots via `InventorySlots.*` constants (engine-prepopulated from CfgSlots, `P:\scripts\3_game\systems\inventory\inventoryslots.c:7`), not strings (`GetSlotIdFromString` looks up `Slot_<name>`; config uses Title case — `Slot_Body name="Body"`, `P:\scripts\config.cpp:90-94`; runtime lookup case unverified). [Read in the source 2026-08-06 for the LF-COM mod; not yet confirmed in game.] See also the `dayz-characters` skill (equipping NPCs and survivors from script).

### `RespawnPlayer()` from script on a living player: refuse before calling it (SP-527)

[EXACT][CLAIM-ENF-RESPAWN-LIVING-NOOP] Before calling `RespawnPlayer()` from script, on the client and before changing anything, refuse when the local `PlayerBase` exists, `IsAlive()`, `!IsUnconscious()` and `!IsRestrained()`; a null player is not refused, and to give a living player a new body, kill it first. In the vanilla scripts on `P:\`, `RespawnPlayer()` is `proto native void RespawnPlayer();` at `P:\scripts\3_game\global\game.c:1107`, reached as `GetGame().RespawnPlayer()`. On the server, `MissionServer.OnClientRespawnEvent(PlayerIdentity identity, PlayerBase player)` (`P:\scripts\5_mission\mission\missionserver.c:611-624`) kills the character only if the player is unconscious or restrained (`player.IsUnconscious() || player.IsRestrained()`, `:615`; `player.SetHealth("", "", 0.0)`, `:621`) and leaves any other player alone, so the rule above is the complement of `P:\scripts\5_mission\mission\missionserver.c:615`. Vanilla's menus follow the same split: the in-game menu shows Respawn only when the player is not alive (`playerAlive = player && player.GetPlayerState() == EPlayerStates.ALIVE`, `P:\scripts\5_mission\gui\ingamemenu.c:321`; `m_RespawnButton.Show(!playerAlive)`, `:326`; a null player counts as not alive), and the respawn-while-unconscious button only when the player is alive and unconscious and cfggameplay's `disableRespawnInUnconsciousness` is off (`:325`), and when the respawn dialog is confirmed the request is dropped if `player && player.IsAlive() && !player.IsUnconscious()` (`:286-291`; the comment at `:287` speaks of players "still alive and not unconscious anymore"). Vanilla's recipe `InGameMenu.GameRespawn(bool random)` (`P:\scripts\5_mission\gui\ingamemenu.c:345-363`) calls `RespawnPlayer()` (`:348`), then on the local player `SimulateDeath(true)` (`:353`) and the dead screen (`:354`), then `SetPlayerRespawning(true)` on the mission (`:359`); `SimulateDeath(true)` (`P:\scripts\4_world\entities\dayzplayerimplement.c:844-881`) locks the controls (`:849`), shows the dead screen, which fades to black (`:868`), and mutes the sound scene (`:870-874`), and the only `SetPlayerRespawning(false)` in vanilla is inside `PlayerBase.OnPlayerLoaded()` (`P:\scripts\4_world\entities\manbase\playerbase.c:2569`, at `:2595`) for the controlled player (`:2585`), so only a newly loaded controlled player clears the flag, and the mission's pause handling returns early while `IsPlayerRespawning()` (`P:\scripts\5_mission\mission\missiongameplay.c:1314`). Signatures: `IsAlive()` on `Object` (`P:\scripts\3_game\entities\object.c:517`); `IsUnconscious()` on `Man` (`P:\scripts\3_game\entities\man.c:63`); `IsRestrained()` on `DayZPlayerImplement` (`P:\scripts\4_world\entities\dayzplayerimplement.c:3935`); `PlayerBase` overrides both (`P:\scripts\4_world\entities\manbase\playerbase.c:3925`, `:2219`). Cfggameplay's `disableRespawnInUnconsciousness` is read only by the two in-game menus (`P:\scripts\5_mission\gui\ingamemenu.c:325`, `P:\scripts\5_mission\gui\ingamemenuxbox.c:599`); `OnClientRespawnEvent` does not read it.

[EXACT][CLAIM-ENF-RESPAWN-LIVING-RUNTIME-130] Measured with dayz-mcp on DayZDiag 1.30 (experimental instance, server respawn mode custom): in dayz-mcp PR #408, `player_respawn`, which copies `InGameMenu.GameRespawn`, answered `ok`/`requested` on a living, conscious player and nothing happened; after `player_kill` it worked. Copying vanilla's `GameRespawn` recipe without the check gives a false success and costs an in-game round. In dayz-mcp PR #416, in-game run `99d065fa` (2026-11-15), with the rule's check on the client before anything changes, the living, conscious player was refused (`player_alive_conscious`); its position and class did not change, the view was not black, the in-game menu opened and closed, and the player could move. After `player_kill`, once the death had reached the client, the respawn worked, and the new living body was refused again. The check reads the client's replicated state: right after a kill the client can still see the player alive and refuse; retry once the death has reached the client (#416, known limit). Not established: that the client stays locked (controls, dead screen, `IsPlayerRespawning()` left true) after a request the server ignores, read from the code and not measured, and #408 recorded only that nothing happened; the unconscious and restrained paths were not exercised in game; what the engine itself does with a living, conscious player's request, where only the script side is readable; and how long the client takes to see the death after a kill.

### Config lookups, strings and math

See `verified-api-catalog.md`: `ConfigIsExisting` and `ConfigGet*` patterns, string operations (`Substring`, `IndexOfFrom`, `Replace`, `ToLower`), and the math, vector and world helpers. Reflection (`GetClassVar`, `CallFunction`, `typename` introspection, `ToType`, `Spawn`, `ScriptCaller`, load-time attributes) and the verified global functions are in the same file.
