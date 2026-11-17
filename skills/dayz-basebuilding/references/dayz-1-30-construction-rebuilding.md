# DayZ 1.30: construction hierarchy, Rebuilding, masonry, Fence code lock

What 1.30 changed in the construction system: the class hierarchy, the type data cache, the `*ServerEx` methods, the second save stream for rebuildable map buildings, the masonry items and the Fence code lock. Open this when porting a 1.29 base building mod or working with rebuildable buildings.

Every code block below was copied from the file named in its first line and compared with `P:\` (game storage version 144). Some notes describe builds 1.30.164014 and 1.30.164289; where 1.30.164289 differs from the build on `P:\`, the text says so and that part is not checked on `P:\`.

## 1. Type hierarchy

`ConstructionBasic` in `3_Game` is a **stub** (`P:\scripts\3_game\systems\construction_basic.c:2-43`), it does **not** contain `GetParent()` / `IsPartConstructed()` / `HasBase()`. Those live on `ConstructionBase` in `4_World`.

```c
// P:\scripts\4_world\classes\constructionbase.c:30
class ConstructionBase : ConstructionBasic
```

```c
// P:\scripts\4_world\classes\basebuilding\construction.c:2
class Construction : ConstructionBase
```

```c
// P:\scripts\4_world\classes\rebuilding\rebuilding.c:1
class Rebuilding : ConstructionBase
```

`EntityAI.CreateConstructionComponent()` returns null (`P:\scripts\3_game\entities\entityai.c:3474-3478`). `ConstructionInit()` (`:3464-3471`) only inits when the override returns a component.

```c
// P:\scripts\4_world\entities\itembase\basebuildingbase.c:15
	protected ref ConstructionBasic 	m_Construction;
```

```c
// P:\scripts\4_world\entities\itembase\basebuildingbase.c:872-886
	override protected ConstructionBasic CreateConstructionComponent()
	{
		m_Construction = new Construction(this);
		return m_Construction;
	}
	
	override ConstructionBasic GetConstructionBasic()
	{
		return m_Construction;
	}
	
	Construction GetConstruction()
	{
		return Construction.Cast(m_Construction);
	}
```

```c
// P:\scripts\4_world\entities\game\super\building.c:23-27
	override protected ConstructionBasic CreateConstructionComponent()
	{
		m_Construction = new Rebuilding(this);
		return m_Construction;
	}
```

Design note: Mods that stored `Construction m_Construction` on a `BaseBuildingBase` subclass should switch to `GetConstruction()` (already a `Construction.Cast`) or `Construction.Cast(GetConstructionBasic())`. Direct field access from outside the class no longer compiles (`protected`).

## 2. `ConstructionPartTypeData` vs `ConstructionPart`

(until 1.29: each `ConstructionPart` stored config fields and `UpdateConstructionParts` re-read config on the instance). (since 1.30: type data is held on `EntityType` via `ConstructionDataTypeHolder`.)

`ConstructionDataTypeHolderBasic` in `3_Game` is also a stub (`P:\scripts\3_game\systems\constructiontypedata_basic.c:2-5`). The real holder is `ConstructionDataTypeHolder` (`P:\scripts\4_world\classes\basebuilding\typeconstructiondata\constructionparttypedholder.c:2`).

```c
// P:\scripts\4_world\classes\basebuilding\constructionpart.c:2-16
//! Instanced construction part data classes for dynamic data, statics now stored on EntityType level in ConstructionPartTypeData
class ConstructionPart
{
	//TODO: start with 2 bits per part, and iterate into differentiated simple/complex part structure
	static const int BITWISE_SYNCINFO_SIZE_BASE = 2; //! no. of bits to store synced info, per part. System not ready for variable size parts yet.
	protected const int ANIMATION_EFFECT_DELAY_BUILD = 350; //ms
	
	protected ConstructionPartTypeData m_PartTypeData; //! Entity-type object storing non-instanced data
	protected int 	m_LocalSyncBitMask = 0;
	bool 	m_IsBuilt;			//defines part build state
	protected ref TConstructionPartInsiderBoxData m_InsiderBoxData; //Grouped modelspace positions of min/max insidebox points
	
	void ConstructionPart( string name, string part_name, string main_part_name, int id, bool is_built, bool is_base, bool is_gate, array<string> required_parts )
	{
	}
```

There is no constructor `ConstructionPart(notnull ConstructionPartTypeData)`. Type data is assigned after spawn:

```c
// P:\scripts\4_world\classes\basebuilding\constructionpart.c:395-401
	void SetPartTypeData(ConstructionPartTypeData ptd)
	{
		if (!m_PartTypeData)
			m_PartTypeData = ptd;
		else
			ErrorEx("cannot override m_PartTypeData during runtime!");
	}
```

`UpdateConstructionParts` (`P:\scripts\4_world\classes\constructionbase.c:517-548`) reads `entityType.GetConstructionDataHolderBasic()`, spawns the part, then `part.SetPartTypeData(typeData)`. Config field readers (`name`, `id`, `is_base`, `is_gate`, `required_parts`, `build_action_type`, …) now live on `ConstructionPartTypeData.InitPartTypeData` (`P:\scripts\4_world\classes\basebuilding\typeconstructiondata\constructionparttyped.c:45-70,75-107`).

`SetRequestBuiltState` is `[Obsolete("1.30: Use 'SetBuiltState' directly")]` (`P:\scripts\4_world\classes\basebuilding\constructionpart.c:505-512`). The triage row about single player skipping the local set describes that obsolete body.

## 3. `*ServerEx` and collision

```c
// P:\scripts\4_world\classes\constructionbase.c:1702-1716
	[Obsolete("call BuildPartServerEx instead")]
	void BuildPartServer(notnull Man player, string part_name, int action_id)
	{
		if (LogManager.IsBaseBuildingLogEnable()) bsbDebugPrint("[bsb] Construction BuildPartServer | " + part_name);
		
		BuildPartServerEx(player,part_name,action_id);
	}
	
	[Obsolete("call DismantlePartServerEx instead")]
	void DismantlePartServer(notnull Man player, string part_name, int action_id)
	{
		if (LogManager.IsBaseBuildingLogEnable()) bsbDebugPrint("[bsb] Construction DismantlePartServer | " + part_name);
		
		DismantlePartServerEx(player,part_name,action_id);
	}
```

```c
// P:\scripts\4_world\classes\constructionbase.c:179-184
	void BuildPartServerEx(Man player, string part_name, int action_id)
	{
		if (LogManager.IsBaseBuildingLogEnable()) bsbDebugPrint("[bsb] Construction BuildPartServerEx | " + part_name);
		//on action
		TakeMaterialsServer(part_name);
	}
```

Note: `player` **can be null** (comment at `constructionbase.c:177`). `Construction` then calls `m_Parent.OnPartBuiltServer` (`P:\scripts\4_world\classes\basebuilding\construction.c:52-68`). Vanilla `ActionBuildPart` already calls Ex:

```c
// P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionbuildpart.c:167-170
		if (!construction.IsCollidingEx(checkData) && canBuild)
		{
			//build
			construction.BuildPartServerEx(action_data.m_Player, partName, AT_BUILD_PART);
```

`IsCollidingEx` takes a `CollisionCheckData`, not a string:

```c
// P:\scripts\4_world\classes\constructionbase.c:1481-1482
	bool IsCollidingEx(CollisionCheckData check_data)
	{
```

```c
// P:\scripts\4_world\classes\constructionbase.c:1916-1930
class CollisionCheckData
{
	ref array<Object> m_AdditionalExcludes;
	string m_PartName;
	int m_PrimaryGeometry;
	int m_SecondaryGeometry;
	
	void CollisionCheckData()
	{
		m_AdditionalExcludes = new array<Object>();
		m_PartName = "";
		m_PrimaryGeometry = ObjIntersectGeom;
		m_SecondaryGeometry = ObjIntersectView;
	}
}
```

Collision-trigger helpers still exist, marked obsolete with **no replacement**:

```c
// P:\scripts\4_world\classes\constructionbase.c:1756-1757
	[Obsolete("no replacement")]
	void CreateCollisionTrigger(string part_name, vector min_max[2], vector center)
```

```c
// P:\scripts\4_world\classes\constructionbase.c:1784-1795
	[Obsolete("no replacement")]
	void DestroyCollisionTrigger()
	{
		if (!m_ConstructionBoxTrigger)
			return;
		
		g_Game.ObjectDelete(m_ConstructionBoxTrigger);
		m_ConstructionBoxTrigger = NULL;
	}
	
	[Obsolete("no replacement")]
	bool IsTriggerColliding()
```

`m_ConstructionBoxTrigger` is tagged `//! Deprecated` (`constructionbase.c:1803`).

## 4. Rebuilding persistence (map buildings only)

`BuildingBase` registers ten netsync ints on the component (`P:\scripts\4_world\entities\game\super\building.c:29-46`). `Rebuilding` writes its own versioned blob, this is **not** `BaseBuildingBase.OnStoreSave`.

```c
// P:\scripts\4_world\classes\rebuilding\rebuilding.c:1-16
class Rebuilding : ConstructionBase
{
	static int REBUILDING_STORAGE_VERSION = 1;
	
	protected int m_LastStorageVersion;
	
	protected int m_SyncParts1;
	protected int m_SyncParts2;
	protected int m_SyncParts3;
	protected int m_SyncParts4;
	protected int m_SyncParts5;
	protected int m_SyncParts6;
	protected int m_SyncParts7;
	protected int m_SyncParts8;
	protected int m_SyncParts9;
	protected int m_SyncParts10;
```

```c
// P:\scripts\4_world\classes\rebuilding\rebuilding.c:501-514
	protected void SerializeConstructionData(ParamsWriteContext ctx)
	{
		ctx.Write(REBUILDING_STORAGE_VERSION);
		ctx.Write(m_SyncParts1);
		ctx.Write(m_SyncParts2);
		ctx.Write(m_SyncParts3);
		ctx.Write(m_SyncParts4);
		ctx.Write(m_SyncParts5);
		ctx.Write(m_SyncParts6);
		ctx.Write(m_SyncParts7);
		ctx.Write(m_SyncParts8);
		ctx.Write(m_SyncParts9);
		ctx.Write(m_SyncParts10);
	}
```

Packing math (derived):
- `BIT_INT_SIZE = 32` (`P:\scripts\3_game\tools\bitarray.c:4`)
- `GetSyncDataSize()` returns `BITWISE_SYNCINFO_SIZE_BASE = 2` (`constructionpart.c:6` and `:65-68`)
- `adjustedID = (partId - 1) * GetSyncDataSize()`; `syncIntIdx = adjustedID / BIT_INT_SIZE` (`P:\scripts\4_world\classes\rebuilding\rebuilding.c:146-148`)
- 10 ints × 32 bits / 2 bits/part = 160 part ids (1..160)

Default `CalculateBitMaskOnBuild` sets only bit 0 at `offset` (`constructionpart.c:111-117`). `ConstructionPartRebuildReversibleBase`, a subclass of `ConstructionPartRebuild` (`:1049`), also ORs its reversed flag `m_TempReversed` into bit 1 (`:1065-1072`). A three-state encoding (00 ruin, 01 built, 10 destroyed) is not in those methods; it is not checked.

`BaseBuildingBase.OnStoreSave` is unchanged (still 1 bit per part, ids 1..93):

```c
// P:\scripts\4_world\entities\itembase\basebuildingbase.c:420-430
	override void OnStoreSave( ParamsWriteContext ctx )
	{   
		super.OnStoreSave( ctx );
		
		//sync parts 01
		ctx.Write( m_SyncParts01 );
		ctx.Write( m_SyncParts02 );
		ctx.Write( m_SyncParts03 );
		
		ctx.Write( m_HasBase );
	}
```

Support graph: `ConstructionPartStaticsSupportData` parses `StaticsSupportData { SupportProviders / SupportRequirements }` (`P:\scripts\4_world\classes\rebuilding\constructionstatics.c:1-26`). `ConstructionBase.SupportRemovalCheck` defaults to true (`constructionbase.c:786-789`); Rebuilding overrides it. Design note: Do not treat `required_parts[]` as the only structural gate on rebuildable houses.

## 5. Masonry items and `TOOL_BRICKLAYING`

```c
// P:\scripts\4_world\classes\basebuilding\constructionconstants.c:13-26
//has to mirror tool defines in configs!
enum EConstructionTools
{
	TOOL_NO_ACTION = 0,
	TOOL_MOUNT_WIRE = 1,
	TOOL_NAIL = 2,
	TOOL_DIG_BASE = 4,
	TOOL_MOUNT_LOG = 8,
	TOOL_HEAVY = 16,
	TOOL_EXCAVATION = 32,
	TOOL_WOODWORK = 64,
	TOOL_HANDS = 128,
	TOOL_BRICKLAYING = 256
}
```

```c
// P:\scripts\4_world\entities\itembase\bricktrowel.c:1-8
class BrickTrowel extends ToolBase
{
	override void SetActions()
	{
		super.SetActions();
		
		AddAction(ActionBuildPart);
		AddAction(ActionRepairPart);
```

```c
// P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionpickupbricks.c:16-18
class ActionPickUpBricks: ActionContinuousBase
{	
	static const int YIELD = 3;
```

```c
// P:\scripts\4_world\entities\itembase\mortarmix.c:1-8
class MortarMix extends ItemBase
{	
	override void SetActions()
	{
		super.SetActions();
        AddAction(ActionMixMortarAtWater);
		AddAction(ActionMixMortarAtWell);
	}
```

`ActionMixMortarAtWater` uses `CCTLiquid` (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionmixmortaratwater.c:23,47-50`). `MortarMix_Opened` only adds `ActionAttachToConstruction` (`P:\scripts\4_world\entities\itembase\mortarmix_opened.c:1-8`). `CommonBrick` adds attach-to-construction (`P:\scripts\4_world\entities\itembase\commonbrick.c:1-8`). Rebuildable house scripts live under `4_World/Entities/Building/Rebuildable/` (e.g. `P:\scripts\4_world\entities\building\rebuildable\house_1m1.c:1`).

`ConstructionMaterialType` moved to `constructionbase.c:2-12` and adds brick/rubble:

```c
// P:\scripts\4_world\classes\constructionbase.c:2-12
enum ConstructionMaterialType
{
	MATERIAL_NONE	= 0,
	MATERIAL_LOG	= 1,
	MATERIAL_WOOD	= 2,
	MATERIAL_STAIRS	= 3,
	MATERIAL_METAL	= 4,
	MATERIAL_WIRE	= 5,
	MATERIAL_BRICK 	= 6,
	MATERIAL_RUBBLE = 7
}
```

Not checked: `CfgVehicles` `build_action_type` for `BrickTrowel`, the class name appears in scripts and in the character sound config (`P:\DZ\characters\data\config.cpp:7296`), but no `class BrickTrowel` block is in the `CfgVehicles` configs unpacked on `P:\DZ`.

## 6. Fence `DigitalCodeLock` and combo-lock unlock

```c
// P:\scripts\4_world\entities\itembase\basebuildingbase\fence.c:18-26
	typename ATTACHMENT_WOODEN_LOG			= WoodenLog;
	typename ATTACHMENT_COMBINATION_LOCK	= CombinationLock;
	typename ATTACHMENT_CODE_LOCK			= DigitalCodeLock;
	
	const string ATTACHMENT_SLOT_CAMONET			= "Wall_Camonet";
	const string ATTACHMENT_SLOT_BARBEDWIRE_DOWN	= "Wall_Barbedwire_1";
	const string ATTACHMENT_SLOT_BARBEDWIRE_UP		= "Wall_Barbedwire_2";
	const string ATTACHMENT_SLOT_COMBINATION_LOCK 	= "Att_CombinationLock";
	const string ATTACHMENT_SLOT_CODE_LOCK 			= "Att_CodeLock";
```

```c
// P:\scripts\4_world\entities\itembase\basebuildingbase\fence.c:161-165
	DigitalCodeLock GetCodeLock()
	{
		DigitalCodeLock codeLock = DigitalCodeLock.Cast(FindAttachmentBySlotName(ATTACHMENT_SLOT_CODE_LOCK));
		return codeLock;
	}
```

`DigitalCodeLock` owns a `CodeLockComponent` (`P:\scripts\4_world\entities\itembase\codelock.c:1,9,30`). PIN length 4..6 (`P:\scripts\4_world\classes\codelockcomponent.c:23-24`). Persist order on the component: `m_LockPIN`, `m_IsLocked`, `m_DoorIndex` (`codelockcomponent.c:257-262`). Building-door lock slots (`Att_CombinationLock` / `Att_CodeLock` on `BuildingBase`, `P:\scripts\4_world\entities\game\super\building.c:10-11`) belong to the doors skill (dayz-doors); Fence is the base-building attachment point.

Combo lock: `AddAction(ActionCombinationLockUnlock)` (`P:\scripts\4_world\entities\itembase\combinationlock.c:686`). Stream v143 adds `m_CombinationInside`:

```c
// P:\scripts\4_world\entities\itembase\combinationlock.c:128-136
	override void OnStoreSave( ParamsWriteContext ctx )
	{   
		super.OnStoreSave(ctx);
		
		//write data
		ctx.Write( m_Combination );
		ctx.Write( m_CombinationLocked );
		ctx.Write( m_CombinationInside );
	}
```

Fence gate save itself is still after `super` (`P:\scripts\4_world\entities\itembase\basebuildingbase\fence.c:246-254`; 1.29 `fence.c:212-220`).

## 7. `ConstructionActionData` slot helpers

Not removed. Marked obsolete:

```c
// P:\scripts\4_world\classes\basebuilding\constructionactiondata.c:617-627
	[Obsolete("1.30: Unsafe, overridden ActionData used in-system instead")]
	void SetSlotId( int slot_id )
	{
		m_SlotId = slot_id;
	}
	
	[Obsolete("1.30: Unsafe, overridden ActionData used in-system instead")]
	int GetSlotId()
	{
		return m_SlotId;
	}
```

## 8. `disableSimulation` (changelog only for houses)

```c
// P:\scripts\3_game\entities\entity.c:3-6
	proto native void DisableSimulation(bool disable);

	//! Returns whether simulation is disabled
	proto native bool GetIsSimulationDisabled();
```

From the 1.30 changelog (not checked on `P:\`): a `disableSimulation` config parameter on house-based entities. Not observed on `BaseBuildingBase`.

## 9. Activation, new per-part keys and rebuildable buildings

Read in the scripts; nothing in this section has been exercised in game.

### 9.1 What turns construction on

```c
// P:\scripts\3_game\entities\entityai.c:248-249
		if (g_Game.ConfigIsExisting("cfgVehicles" + " " + GetType() + " " + "Construction"))
			ConstructionInit();
```

Any `CfgVehicles` class with a `Construction` subclass gets its component when the entity is constructed. The concrete type comes from `CreateConstructionComponent()`: `new Rebuilding(this)` on `BuildingBase` (`building.c:23-27`) and `new Construction(this)` on `BaseBuildingBase` (`P:\scripts\4_world\entities\itembase\basebuildingbase.c:872-876`). Inference from those two overrides, not measured: a modded building that inherits a `BuildingBase` descendant needs no script override to become rebuildable, only the config block and the model selections.

### 9.2 Per-part keys that 1.30 reads

Readers are in `constructionparttyped.c` unless another file is named; line numbers are from `P:\`. The paths are relative to `Construction <main_part> <part>`.

| Key | Reader on `P:\` | What the code shows |
|---|---|---|
| `custom_part_type` | `constructionparttypedholder.c:35` | script class for the part's type data (for example the `ConstructionPartRebuild*Typed` classes) |
| `can_part_decay`, `part_decay_threshold`, `part_decay_rate` | `constructionparttyped.c:202`, `:208`, `:215` | per-part decay. Global switch `disableBaseDecay` (`P:\scripts\3_game\cfggameplaydatajson.c:60`, `GetDisableBaseDecay` at `P:\scripts\3_game\cfggameplayhandler.c:172`, used by `ConstructionBasic.CanConstructionDecay`, `construction_basic.c:37-40`) |
| `insider_minMaxs` | `constructionparttyped.c:162` | inner box, next to `collision_data` (`:151`) |
| `item_falling_data` | `constructionparttyped.c:191` | the two memory points of the box in which items fall when the part goes; `GetItemFallDetectionBoxData` uses them (`constructionbase.c:1608-1631`). Build 1.30.164289 drops this key and builds the box from `collision_data` plus margins by part category; that build is not on `P:\`, so this is not checked. |
| `item_fall_trigger` | not on `P:\` | build 1.30.164289 only: int, default 1; `0` takes the part out of the item-fall check (rubble, doors and windows). Not checked on `P:\`. |
| `essential_attachments` | `constructionparttyped.c:231` | read; its effect was not traced |
| `related_GUI_categories` | `constructionparttyped.c:242` | ties the part to inventory GUI categories |
| `damage_hands_on_build` | `constructionparttyped.c:253` | read; its effect was not traced |
| `is_utility`, `utility_build` | `constructionparttyped.c:262`, `:268` | an int and a text array, both read on `P:\`; their effect was not traced. Build 1.30.164014 had only `utility_build` and build 1.30.164289 reads `toggle_utility_part_update` instead (neither build is on `P:\`, not checked); no script on `P:\` reads `toggle_utility_part_update`. |
| `EffectsData` > `soundEffectPositions`, `particleEffectPositions` | `P:\scripts\4_world\classes\rebuilding\constructioneffects.c:19,26-28,37` | memory points for build effects |
| `StaticsSupportData` > `SupportProviders` / `SupportRequirements` > `<child>` > `supportCategory` (string, hashed), `supportStrength` (int) | `constructionstatics.c:13,26,37-38,45,56-57` | structural support: what a part provides and needs, by category |
| `Materials` > `<material>` > `skipOnRepair`, `skipOnDismantle` | `P:\scripts\4_world\classes\basebuilding\constructionmaterials.c:31-32` | material not needed to repair, or not refunded on dismantle (next to `type`, `slot_name`, `quantity`, `lockable`, `:26-30`) |

### 9.3 Locks on rebuilt doors

`BuildingBase` declares the slots `Att_CombinationLock` and `Att_CodeLock` (`building.c:10-11`). A door cannot hold both (`HasConflictingDoorAttachment`, `:344-356`, called at `:228`), and `CanDoorBeOpened` is overridden (`:307`). The per-door slot wiring was not traced further here.

### 9.4 What 1.30 ships and what it does not

- **Script classes.** The Nasdara houses (`4_World/Entities/Building/Rebuildable/House_*.c`) and `Land_IrrigationTunnel_Entrance_01 : BuildingSuper` (`P:\scripts\4_world\entities\building\rebuildable\irrigationtunnel_entrance.c:1-11`, whose debug spawn puts a `WoodenStick` and a `Rope` in its inventory).
- **No configs or models on 1.30.164014.** No unencrypted PBO config of that install defined `Land_House_2M1`, `Land_IrrigationTunnel_Entrance_01`, `wall1_wood` or `rubble_rubble1`. `nasdara\addons\data_nasdara.pbo` carries only the DLC `CfgMods` entry and a `mud_brick` surface.
- **Example part names.** `Land_House_2M1_Dam2.OnDebugSpawn` builds `rubble_rubble1`, `rubble_rubble2`, `wall1_wood`, `wall2_wood`, `wall3_brick` and `roof1` with `BuildPartServerEx(null, <part>, -1)` (`P:\scripts\4_world\entities\building\rebuildable\house_2m1.c:13-20`).
- **`RebuildingSpawner` is diag-only** (`P:\scripts\4_world\classes\basebuilding\rebuildingspawner.c:1`, `#ifdef DIAG_DEVELOPER`).

### 9.5 Object Spawner flag

- **The flag.** `ECE_OBJECT_SPAWNER = 256` (`P:\scripts\3_game\ce\centraleconomy.c:15`) is now set by the Object Spawner for the objects it creates by class name (`P:\scripts\3_game\objectspawner.c:48`). Its `.p3d` path calls `CreateStaticObjectUsingP3D` with five arguments (`objectspawner.c:44`): the trailing `true` is `createLocal`, and the sixth parameter `objSpawner` keeps its default `false` (`P:\scripts\3_game\global\game.c:680`).
- **New parameter.** `CreateObject` and `CreateStaticObjectUsingP3D` gained `bool objSpawner = false` (`P:\scripts\3_game\global\game.c:680,691`).
- **Unknowns.** Script does not say what the engine does with the flag. Whether a rebuildable building placed by the Object Spawner keeps its parts across a restart is unmeasured.

Terrain holes, underground triggers and the underground placement block are in the underground skill (dayz-underground).

## 10. Summary: what changes, what breaks, migration checklist

### What changes

- **Hierarchy.** `EntityAI.CreateConstructionComponent()` (`entityai.c:3474`) returns null by default. `BaseBuildingBase` overrides it to `new Construction(this)` (`basebuildingbase.c:872-876`). `BuildingBase` overrides it to `new Rebuilding(this)` (`building.c:23-27`). Field type on both is `protected ref ConstructionBasic m_Construction`.
- **Static vs instance.** `ConstructionPartTypeData` caches `Construction{}` on `EntityType` (`constructionparttyped.c:2-70`). `ConstructionPart` keeps `m_PartTypeData`, `m_LocalSyncBitMask`, `m_IsBuilt` (`constructionpart.c:9-12`). The old multi-arg constructor is empty (`:14-16`); instances are `ToType().Spawn()` then `SetPartTypeData` (`constructionbase.c:531-538`).
- **`*ServerEx`.** `BuildPartServer` / `DismantlePartServer` / `IsColliding` are `[Obsolete]` wrappers on `ConstructionBase` (`constructionbase.c:1702-1754`). Live path: `BuildPartServerEx` / `DismantlePartServerEx` / `IsCollidingEx(CollisionCheckData)` (`:179,190,1481`). There is no `IsCollidingEx(string, Object, bool, bool)` signature.
- **Collision triggers.** `CreateCollisionTrigger` / `DestroyCollisionTrigger` / `IsTriggerColliding` are **not deleted**. They are `[Obsolete("no replacement")]` (`constructionbase.c:1756-1801`). Calling them still compiles; do not build new code on them.
- **`ConstructionActionData.SetSlotId` / `GetSlotId`.** Not deleted. `[Obsolete("1.30: Unsafe, overridden ActionData used in-system instead")]` (`constructionactiondata.c:617-627`).
- **Rebuilding (map buildings, not player fences).** `BuildingBase` registers `m_Construction.m_SyncParts1`..`10` (`building.c:29-46`). Packing: `BIT_INT_SIZE = 32` (`P:\scripts\3_game\tools\bitarray.c:4`) × 10 ints / `BITWISE_SYNCINFO_SIZE_BASE = 2` (`constructionpart.c:6`) = **160 part ids**. Persist via `HandleStoreSave` → `SerializeConstructionData` (`rebuilding.c:473-514`). Default build mask sets bit 0; `ConstructionPartRebuildReversibleBase` also stores its reversed flag in bit 1 (`constructionpart.c:1065-1072`). A 00/01/10 "ruined" table is not in those methods.
- **Masonry loop.** `PileOfBricks` + `ActionPickUpBricks.YIELD = 3` (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionpickupbricks.c:16-18`). `MortarMix` mixes at water or a well (`P:\scripts\4_world\entities\itembase\mortarmix.c:1-8`) into `MortarMix_Opened`. `BrickTrowel` adds `ActionBuildPart` (`P:\scripts\4_world\entities\itembase\bricktrowel.c:1-7`); build anim `CMD_ACTIONFB_BRICKTROWEL` (`actionbuildpart.c:260-262`). Tool mask enum `TOOL_BRICKLAYING = 256` (`constructionconstants.c:25`). Not checked: `CfgVehicles BrickTrowel build_action_type`, class not in extracted configs.
- **Fence locks.** `Fence` has `ATTACHMENT_CODE_LOCK = DigitalCodeLock`, `ATTACHMENT_SLOT_CODE_LOCK = "Att_CodeLock"` and `GetCodeLock()` (`fence.c:20,26,161-165`) beside the existing combination lock. Dialing a combo lock no longer unlocks it: `ActionCombinationLockUnlock` (`combinationlock.c:686`).
- **Material enum moved.** `ConstructionMaterialType` now lives on `constructionbase.c:2-12` and adds `MATERIAL_BRICK = 6`, `MATERIAL_RUBBLE = 7`.
- **`disableSimulation`.** From the 1.30 changelog (not checked on `P:\`): house entities may set `disableSimulation` to skip ticking; the native is `DisableSimulation` (`P:\scripts\3_game\entities\entity.c:3-6`). Not a `BaseBuildingBase` field.
- **Activation.** Any `CfgVehicles` class with a `Construction` subclass gets the component at init (`entityai.c:248-249`). Rebuilding parts read new keys: per-part decay (`can_part_decay`, `part_decay_threshold`, `part_decay_rate`, global `disableBaseDecay`), `StaticsSupportData`, `EffectsData`, `custom_part_type`, `skipOnRepair`/`skipOnDismantle`. Table with readers: section 9.2.
- **Rebuildable map buildings were scripts only on 1.30.164014.** The Nasdara houses and `Land_IrrigationTunnel_Entrance_01` had script classes but no configs or models in that install (§9.4). Terrain holes and underground areas: the underground skill (dayz-underground).
- **Rebuildable houses carry attachment slots on the building itself (DayZDiag 1.30.164200)**: in that build the configs are there (the line above describes 1.30.164014). A server-side scan of `CfgVehicles` (classes that `IsKindOf "House"`, `scope` ≥ 1, non-empty `attachments[]`) found 32 classes: 22 houses from `Land_House_1M1` to `Land_House_3S2_Dam2`, whose rebuild slots are `RB_LvL<n>_{Log,Plank,Nail,MetalSheet,MetalWire}` plus `RB_LvL<n>_{Brick,MortarMix}` on all but `Land_House_1M1`, `Land_House_1M2` and `Land_House_1S1`, with `<n>` up to 1 on the `1*` houses, 2 on the `2*` and 3 on the `3*`, and lock slots `Att_CombinationLock<n>_{Wood,Metal}` / `Att_CodeLock<n>_{Wood,Metal}` in a number that varies per house; `Land_Bunker_Basement_*` / `Land_Bunker_Shelter_*` with `Att_CodeLock`, `Land_WaterWell_Brick`, `Land_IrrigationTunnel_Entrance_01` (`RB_LvL1/2_{Rope,Stick}`) and `Land_Radio_PanelBig` / `Land_Radio_PanelPAS` (`LargeBattery`). `world_spawn(Land_House_1M1)` on Chernarus answered `declared_slots` with the nine level-1 slots, and `inventory_attach(WoodenPlank, slot RB_LvL1_Plank)` filled one. Moves into and out of those slots reach `ItemBase.EEItemLocationChanged` with the house as the hierarchy root (see the 1.30 notes of the enforce-script-reference skill). Script class: `Land_House_1M1 : BuildingSuper` (`P:\scripts\4_world\entities\building\rebuildable\house_1m1.c:1`); slot rules in `BuildingBase.CanReceiveAttachment` / `CanReleaseAttachment` (`building.c:192`, `:267`). Not measured: the Nasdara map itself, models and rebuild actions on these slots.

### What breaks (1.29 mods)

1. Override of `BuildPartServer` / `DismantlePartServer` is skipped if vanilla calls `*Ex`. Migrate the override.
2. New code that called `CreateCollisionTrigger` still compiles but is obsolete with **no replacement**; use `IsCollidingEx(CollisionCheckData)` (`constructionbase.c:1481,1916-1930`).
3. Direct typed access to `m_Construction` as `Construction` fails: field is `ConstructionBasic` and `protected`. Use `GetConstruction()` or `GetConstructionBasic()`.
4. Instantiating `ConstructionPart` with the old constructor does not fill type data. Spawn + `SetPartTypeData`.
5. Fence combo-lock automation that assumed "last dial = unlocked" needs `ActionCombinationLockUnlock`.
6. Custom `CombinationLock.OnStoreLoad` must read `m_CombinationInside` when `version >= 143`.

### Migration checklist

- [ ] Replace overrides of `BuildPartServer` / `DismantlePartServer` / `IsColliding` with `*Ex`.
- [ ] Stop using construction-box triggers; build `CollisionCheckData` and call `IsCollidingEx`.
- [ ] Access construction via `GetConstruction()` / `GetConstructionBasic()`, never the raw field from outside.
- [ ] Keep `BaseBuildingBase` `id` in 1..93 and the `OnStoreSave` order `01,02,03,m_HasBase`.
- [ ] Do not write Rebuilding's 10-int stream into a `BaseBuildingBase` subclass.
- [ ] If attaching a code lock to a Fence, use slot `Att_CodeLock` and `DigitalCodeLock`.
- [ ] If subclassing `CombinationLock`, handle stream v143.
- [ ] Run the data audit on any bit mask or `OnStoreSave` change (`persistence-audit.md`).
