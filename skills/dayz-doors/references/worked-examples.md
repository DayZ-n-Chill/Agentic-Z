# Worked door examples

Three complete door patterns (door with handle, door opened by a button, door with handle and lever), compared side by side, and the 1.30 lock attachments for building doors. The three patterns come from a third party tutorial and are cited by its file and line. The lock section was checked on `P:\` (DayZ 1.30).

## Contents

- [Where these examples come from](#where-these-examples-come-from)
- [Simple Door](#simple-door-door-plus-handle)
- [Door with Button](#door-with-button-static-controller)
- [Expert Mode](#expert-mode-door-plus-handle-plus-lever)
- [Cross-pattern diff](#cross-pattern-diff)
- [Source discrepancies](#source-discrepancies)
- [Building locks (DayZ 1.30)](#building-locks-dayz-130)

## Where these examples come from

The three doors here are the examples of novoGOD's door tutorial *Doors_Buttons_Lesson*: three models, each with its `model.cfg` and `config.cpp`, and four tutorial texts, files dated 2025-04-23. The tutorial's files are not in this repo. This page describes each example in its own words and tables and cites the tutorial's files by path and line, such as `Doors_Buttons_Lesson/Door/Simple_Door.cfg:29-40`.

Read each example as a pair. `model.cfg` declares the bones, the selections that move and the source that drives them; `config.cpp` binds that source to a **class Doors** entry and sets its timing, sounds and damage. The three share their scaffolding (a `CfgPatches` entry that requires **"DZ_Data"**, an empty **Default** model class, **skeletonInherit = ""**, **isDiscrete = 0**, **scope = 1** on a **HouseNoDestruct** child) and one DamageSystem, the same lines in all three files; `door-model-cfg-and-config.md` describes those once. The tables below keep to what each pattern adds.

## Simple Door: door plus handle

A door that swings on its hinge, and a handle that turns first and then rides along with the door. One source, **door1**, drives both.

### Side-by-side mapping

| Tutorial model.cfg | Tutorial config.cpp |
|---|---|
| **door1 -> ""**, **handle -> door1**. | One Doors entry **Door1**. |
| Door and handle use source **door1**. | **component = "door1"**. |
| Handle **0..0.15**; door **0.15..1**. | **animPeriod = 1.3**; init values **0.0**. |

The handle follows the door's transform. It reaches angle1 **-1.4** by phase **0.15**; then the door begins its rotation to **1.9**.

### Bones (`Doors_Buttons_Lesson/Door/Simple_Door.cfg:1-14`)

| Bone | Parent | Effect |
|---|---|---|
| **door1** | none (**""**) | Turns about its own axis. |
| **handle** | **door1** | Carried by the door's rotation, on top of its own turn. |

The skeleton class is **Simple_DoorSkeleton**; the model class **Simple_Door**, named after the P3D, points at it through **skeletonName** (`:23-25`).

### Animations (`Doors_Buttons_Lesson/Door/Simple_Door.cfg:27-53`)

| Class | selection | source | axis | Phase window | Turn, radians |
|---|---|---|---|---|---|
| **Door1** | **door1** | **door1** | **door1_axis** | 0.15 to 1 | 0 to 1.9 |
| **handle** | **handle** | **door1** | **handle_axis** | 0 to 0.15 | 0 to -1.4 |

Both are rotations about a Memory LOD axis (**type = "rotation"**, **memory = 1**). The windows do not overlap: the handle turns during the first 15 % of the action, and the door swings during the rest.

### Doors entry (`Doors_Buttons_Lesson/Door/config.cpp:16-31`)

| Doors class | component | soundPos | animPeriod | initPhase | initOpened | Sounds |
|---|---|---|---|---|---|---|
| **Door1** | **door1** | **door1_action** | 1.3 s | 0.0 | 0.0 | **doorMetalSmall** Open, Close, Rattle (locked), OpenABit |

The entity class is **land_Simple_Door** (`:12`); its **model** points at the addon's `Door\Simple_Door.p3d` (`:15`).

## Door with Button: static controller

A door opened from a button next to it. The button never moves, so it is not a bone: it only carries the interaction selection **door1_open**, and that name is the source of the door's rotation.

### Side-by-side mapping

| Tutorial model.cfg | Tutorial config.cpp |
|---|---|
| Only bone **door1 -> ""**; no button bone. | One Doors entry **Door1_Open**. |
| Moving **door1**; source **door1_open**. | **component = "door1_open"**. |
| Door phase **0..1**. | **soundPos = "door1_action"**, period **1.0**. |

The button is static. The tutorial puts the View Geometry selection and the interaction point at the button as **door1_open**; interacting there drives the moving selection **door1**.

### Bones (`Doors_Buttons_Lesson/Door_w_Button/Door_w_Button.cfg:1-12`)

| Bone | Parent | Effect |
|---|---|---|
| **door1** | none (**""**) | The only bone; the button is not listed. |

### Animations (`Doors_Buttons_Lesson/Door_w_Button/Door_w_Button.cfg:25-39`)

| Class | selection | source | axis | Phase window | Turn, radians |
|---|---|---|---|---|---|
| **Door1** | **door1** | **door1_open** | **door1_axis** | 0 to 1 | 0 to 1.9 |

The selection that moves (**door1**) and the source that drives it (**door1_open**) have different names; that split is the whole pattern.

### Doors entry (`Doors_Buttons_Lesson/Door_w_Button/config.cpp:16-31`)

| Doors class | component | soundPos | animPeriod | initPhase | initOpened | Sounds |
|---|---|---|---|---|---|---|
| **Door1_Open** | **door1_open** | **door1_action** | 1.0 s | 0.0 | 0.0 | the same four **doorMetalSmall** sounds |

The DamageZone still names the moving part, **componentNames[] = {"door1"}** (`:65`), not the button's **door1_open**.

## Expert Mode: door plus handle plus lever

A door with a handle, opened from a separate lever. All three parts move from one source, **door1_open**, which the lever carries as its interaction selection.

### Side-by-side mapping

| Tutorial model.cfg | Tutorial config.cpp |
|---|---|
| Door root, handle child, lever root. | Main **Door1_Open**, secondary **Lever**. |
| All use source **door1_open**. | Both use component **door1_open**. |
| Door starts at **0.10**; lever ends at **0.5**. | Main **initOpened = 0.5**; Lever period **0.50**. |

The handle follows the moving door. The lever is an independent root at the controller. All three animations share one source.

? The tutorial's config has two Doors entries for one source and component, which breaks a one entry per source rule. The secondary Lever entry also has no **soundPos** and no sounds. Ask the user before reusing that duplicate mapping.

### Bones (`Doors_Buttons_Lesson/Expert_Mode/Expert_Mode.cfg:1-14`)

| Bone | Parent | Effect |
|---|---|---|
| **door1** | none (**""**) | Turns about its own axis. |
| **handle** | **door1** | Carried by the door's rotation, on top of its own turn. |
| **lever** | none (**""**) | Turns about its own axis, independent of the door. |

### Animations (`Doors_Buttons_Lesson/Expert_Mode/Expert_Mode.cfg:27-65`)

| Class | selection | source | axis | Phase window | Turn, radians |
|---|---|---|---|---|---|
| **Door1** | **door1** | **door1_open** | **door1_axis** | 0.10 to 1 | 0 to 1.9 |
| **Handle** | **handle** | **door1_open** | **handle_axis** | 0 to 1 | 0 to -1.7 |
| **Lever** | **lever** | **door1_open** | **lever_axis** | 0 to 0.5 | 0 to -0.88 |

Here the windows overlap: the lever finishes its throw by the middle of the action, the handle turns over the whole action, and the door starts at 10 %.

### Doors entries (`Doors_Buttons_Lesson/Expert_Mode/config.cpp:16-39`)

| Doors class | component | soundPos | animPeriod | initPhase | initOpened | Sounds |
|---|---|---|---|---|---|---|
| **Door1_Open** | **door1_open** | **door1_action** | 1.0 s | 0.0 | 0.5 | the four **doorMetalSmall** sounds |
| **Lever** | **door1_open** | none | 0.50 s | 0.0 | 0.0 | none |

With **initOpened = 0.5** the main door spawns open about half the time (the **initOpened** note in `door-model-cfg-and-config.md`). Its DamageZone names **door1** (`:73`).

The lever in this example's model collides with nothing; the measurement and the repair are in `lods-and-object-builder.md`.

## Cross-pattern diff

| Concern | Simple Door | Door with Button | Expert Mode |
|---|---|---|---|
| Moving bones | Door and handle | Door only | Door, handle and lever |
| Parent graph | Handle follows door | Door is the root | Handle follows door; lever is a root |
| Interactive source | **door1** | **door1_open** at the button | **door1_open** at the lever |
| Static controller bone | not applicable | Button left out | not applicable; the lever animates |
| Phase sequencing | Handle 0..0.15; door 0.15..1 | Door 0..1 | Door 0.10..1; handle 0..1; lever 0..0.5 |
| Doors components | **door1** | **door1_open** | **door1_open** twice |
| DamageZone component | **door1** | **door1** | **door1** |

No pattern uses `AnimationSources` or script calls; those are in `_shared/animation/animation-sources.md` and `_shared/animation/script-hooks.md`.

## Source discrepancies

- Where the tutorial's texts and its files disagree, the files win.
- The Expert text at **Welcome to novoGODs Expert_Mode Door mod.txt:128-137** shows **switchOpen/switchClose**.
- The tutorial's **Doors_Buttons_Lesson/Expert_Mode/config.cpp:31-38** has neither sound.
- ? No in-game test established what the duplicate Expert Lever Doors entry is for or how it behaves.

## Building locks (DayZ 1.30)

The three tutorial buildings have no lock slots. In 1.30 `House` is a `BuildingBase`, which takes `CombinationLock` and `DigitalCodeLock` as attachments and ties them to a door through `AdditionalDoorInfo`. The source notes report that until 1.29 a world building's door locked only through the engine's `LockDoor` and `UnlockDoor` with a lockpick.

The fence, a player built gate, lists both slots at entity level, not inside **class Doors** (`attachments[]`, `P:\DZ\gear\camping\config.cpp:4362` to `:4368`). The whole list is `Wall_Barbedwire_1`, `Wall_Barbedwire_2`, `Wall_Camonet`, `Att_CombinationLock`, `Att_CodeLock`, `Material_Nails`, `Material_WoodenPlanks`, `Material_MetalSheets`, `Material_WoodenLogs` and `Material_MetalWire`.

The slot name constants of `BuildingBase`:

```c
// P:\scripts\4_world\entities\game\super\building.c:8
class BuildingBase : Building
{
	const string ATTACHMENT_SLOT_COMBINATION_LOCK = "Att_CombinationLock";
	const string ATTACHMENT_SLOT_CODE_LOCK 	= "Att_CodeLock";
```

The `CfgSlots` selections the model's Memory LOD or proxy must match:

```cpp
// P:\scripts\config.cpp:2316
	class Slot_Att_CombinationLock
	{
		name="Att_CombinationLock";
		displayName="#STR_CombinationLock0";
		selection="att_combinationlock";
		ghostIcon="set:dayz_inventory image:combolock";
	};
```

```cpp
// P:\scripts\config.cpp:2768
	class Slot_Att_CodeLock
	{
		name="Att_CodeLock";
		displayName="#STR_CodeLock0";
		selection="att_codelock";
		ghostIcon="set:dayz_inventory image:digitallock";
	};
```

The source notes report that 1.30.164200 renamed this `displayName` to `"#STR_CfgVehicles_codelock0"` on every `Slot_Att_CodeLock*` slot; `P:\` holds the earlier string.

### `AdditionalDoorInfo` on each `class Doors` child

It is read once per building type in `Building.InitializeDoorInfos` (`P:\scripts\3_game\entities\building.c:302` to `:310`). The members, and then the config keys they are read from:

```c
// P:\scripts\3_game\entities\additionaldoorsinfo.c:1
//! Single door info
class AdditionalDoorInfo
{
	protected string m_DoorPath;
	
	string m_DoorType;
	string m_InteractLimitingPositionPoint; //! memory point name for limiting open/close actions on the door/window
	string m_InteractLimitingDirPoint; //! memory point name for limiting open/close actions on the door/window
	string m_DoorConstructionPartName; //! Name of the construction part linked to the doors, if any (empty default)
	string m_DoorConstructionPhysicsSource; //! Name of the AnimationSource controlling door physics (required for rebuildable doors, empty default)
	int m_LockCompatibilityBitMask; //! Lock compatibility type, now in door config. Lockpick enabled by default if undefined.
	ref TStringArray m_RelatedInventorySlotNames; //! Inventory slots that have something to do with this door. Mostly external locks?
```

```c
// P:\scripts\3_game\entities\additionaldoorsinfo.c:21
	void Init()
	{
		if (g_Game.ConfigIsExisting(m_DoorPath + " relatedInventorySlots"))
		{
			m_RelatedInventorySlotNames = new TStringArray();
			g_Game.ConfigGetTextArray(m_DoorPath + " relatedInventorySlots", m_RelatedInventorySlotNames);
		}
		
		if (g_Game.ConfigIsExisting(m_DoorPath + " lockCompatibilityBitMask"))
			m_LockCompatibilityBitMask = g_Game.ConfigGetInt(m_DoorPath + " lockCompatibilityBitMask");
		else
			m_LockCompatibilityBitMask = 1 << EBuildingLockType.LOCKPICK; //default behavior if not configured
		
		if (g_Game.ConfigIsExisting(m_DoorPath + " interactPositionPoint"))
			m_InteractLimitingPositionPoint = g_Game.ConfigGetTextOut(m_DoorPath + " interactPositionPoint");
		
		if (g_Game.ConfigIsExisting(m_DoorPath + " interactDirPoint"))
			m_InteractLimitingDirPoint = g_Game.ConfigGetTextOut(m_DoorPath + " interactDirPoint");
		
		if (g_Game.ConfigIsExisting(m_DoorPath + " doorConstructionPart"))
			m_DoorConstructionPartName = g_Game.ConfigGetTextOut(m_DoorPath + " doorConstructionPart");
		
		if (g_Game.ConfigIsExisting(m_DoorPath + " doorConstructionPhysicsSource"))
			m_DoorConstructionPhysicsSource = g_Game.ConfigGetTextOut(m_DoorPath + " doorConstructionPhysicsSource");
	}
```

Design, not a copied example: a custom house door that takes a lock needs, on top of the tutorial's **class Doors** block:

1. Entity `attachments[]` holding `Att_CombinationLock`, `Att_CodeLock` or both (and the numbered wood and metal variants when you copy the slot naming of the houses that can be rebuilt).
2. On that door's Doors subclass: `relatedInventorySlots[] = {"Att_CombinationLock","Att_CodeLock"};` so Open, the lockpick and the attach action know which slots belong to which door.
3. Optionally `lockCompatibilityBitMask`, when the lockpick or ship container keys should differ from the default.
4. The Memory selections `att_combinationlock` and `att_codelock`.
5. Optionally `interactPositionPoint` and `interactDirPoint` for a door that works from one side.

No vanilla config under `P:\DZ` has `relatedInventorySlots[]` in a **class Doors** child. The parser and the `BuildingBase` and `ActionAttachToConstruction` code that use it are on `P:\`; a shipped house block with those keys is not.

### Attaching a lock to a building door

The building branch of `ActionAttachToConstruction` takes the slot from `relatedInventorySlots[]`, and only while the door is closed and not locked by the engine:

```c
// P:\scripts\4_world\classes\useractionscomponent\actions\singleuse\actionattachtoconstruction.c:151
		else if (Class.CastTo(building, targetEntity) && building.CanUseConstruction())	// Building entities
		{
			if (item.IsExternalLockType()) // External lock handling of building objects with doors and lock attachments and internal locks
			{
				int doorIndex = building.GetDoorIndex(target.GetComponentIndex());
				if (doorIndex > -1 && !building.IsDoorLocked(doorIndex) && !building.IsDoorOpen(doorIndex))
				{
					AdditionalDoorInfo doorInfo = building.GetDoorInfo(doorIndex);
					if (!doorInfo || !doorInfo.m_RelatedInventorySlotNames)
						return InventorySlots.INVALID;
					
					foreach (string slotName: doorInfo.m_RelatedInventorySlotNames)
					{
						EntityAI slotEntity = building.FindAttachmentBySlotName(slotName);
						if (slotEntity)
							continue;
						
						slotId = InventorySlots.GetSlotIdFromString(slotName);
						GameInventory inventory = building.GetInventory();
						if (inventory && inventory.CanAddAttachmentEx(item, slotId))
							break;
```

`BuildingBase.CanReceiveAttachment` refuses a second lock on the twin slot (`HasConflictingDoorAttachment` swaps the `Att_CodeLock` and `Att_CombinationLock` parts of the slot name) and refuses any external lock while that door is open (`P:\scripts\4_world\entities\game\super\building.c:192` to `:250`; `HasConflictingDoorAttachment` at `:344`). `CanReleaseAttachment` refuses while `DigitalCodeLock.IsLocked()` or `CombinationLock.IsLocked()` is true (`P:\scripts\4_world\entities\game\super\building.c:267` to `:281`).

### Combination lock: two faces and an explicit unlock

In 1.30 matching the dials is not enough: `ActionCombinationLockUnlock` has to run, and the inside and the outside have separate combinations. The source notes report that until 1.29 matching the last dial unlocked and dropped the lock.

```c
// P:\scripts\4_world\entities\itembase\combinationlock.c:25
class CombinationLock extends ItemBase
{
	static const string LOCK_SELECTION_OUTSIDE = "lock_attached_outside";
	static const string LOCK_SELECTION_INSIDE = "lock_attached_inside";
	static const int FACING_OUTSIDE = 0;
	static const int FACING_INSIDE = 1;
```

```c
// P:\scripts\4_world\classes\useractionscomponent\actions\singleuse\actioncombinationlockunlock.c:1
class ActionCombinationLockUnlock: ActionInteractBase
{
	void ActionCombinationLockUnlock()
	{
		m_CommandUID 	= DayZPlayerConstants.CMD_ACTIONMOD_OPENDOORFW;
		m_Text = "#detach_combination_lock";
	}
```

Save version 143 adds `m_CombinationInside`:

```c
// P:\scripts\4_world\entities\itembase\combinationlock.c:128
	override void OnStoreSave( ParamsWriteContext ctx )
	{   
		super.OnStoreSave(ctx);
		
		//write data
		ctx.Write( m_Combination );
		ctx.Write( m_CombinationLocked );
		ctx.Write( m_CombinationInside );
	}
```

```c
// P:\scripts\4_world\entities\itembase\combinationlock.c:169
		if (version >= 143)						//added with 143
		{
			//combination two (inside lock)
			if (!ctx.Read(m_CombinationInside))
			{
				m_CombinationInside = 0;
				return false;
			}
		}
```

### Digital code lock

The script class is `DigitalCodeLock` (`P:\scripts\4_world\entities\itembase\codelock.c:1`). No `CfgVehicles` class of that name is in the configs unpacked under `P:\DZ`, so the config class name is not confirmed here. It owns a `CodeLockComponent` and a `CodeLockVisualManager`. Its battery slot is `BatteryD` (`ATTACHMENT_SLOT_BATTERY`, `codelock.c:6`) and it takes a `Battery9V`. The PIN is 4 to 6 digits (`MIN_LOCK_PIN_LENGTH`, `P:\scripts\4_world\classes\codelockcomponent.c:23` to `:24`). The menu layout is `"gui/layouts/day_z_digital_lock.layout"` (`GetLayout`, `P:\scripts\5_mission\gui\digitalcodelockui.c:127` to `:129`). The memory points on the item are `ce_center` and `inside` (`MEMPOINT_CENTER`, `codelock.c:3` to `:4`).

```c
// P:\scripts\4_world\classes\codelockcomponent.c:4
enum CodeLockStage
{
	NONE,
	NORMAL,
	SETTING,
	PROTECTION_STAGE_ONE,
	PROTECTION_STAGE_TWO
}
```

Brute force thresholds come from `cfggameplay.json` through `CfgGameplayHandler`: `GetExternalLockProtectionTime`, `GetExternalLockProtectionResetTime`, `GetExternalLockProtectionCountStageOne` and `GetExternalLockProtectionCountStageTwo` (`P:\scripts\3_game\cfggameplayhandler.c:513` to `:528`; used at `P:\scripts\4_world\classes\codelockcomponent.c:66` to `:67` and `:474` to `:479`). There is no `GetExternalLockProtectionTimeStageOne`.

The component saves, in this order, `m_LockPIN` (string), `m_IsLocked` (bool) and `m_DoorIndex` (int) (`OnStoreSave`, `P:\scripts\4_world\classes\codelockcomponent.c:257` to `:262`). The save and load contract is in `_shared/persistence/save-load-contract.md`.

### Bunker door (broadcast)

`Bunker` overrides `CanDoorBeOpened(DoorManipulationParams)`. From the inside, it uses `MemPointDirectionalCheck` on `<m_DoorType>_action` and `<m_DoorType>_inside`; from the outside it needs `m_IsActive` and an unlocked `DigitalCodeLock_Bunker`.

```c
// P:\scripts\4_world\entities\building\bunker.c:47
	override bool CanDoorBeOpened(notnull DoorManipulationParams params)
	{
		if (IsMainDoor(params.m_DoorIndex))
		{
			AdditionalDoorInfo doorInfo = GetDoorInfo(params.m_DoorIndex);
			string memPointStartName = string.Format("%1_action", doorInfo.m_DoorType);
			string memPointEndName = string.Format("%1_inside", doorInfo.m_DoorType);
			
			bool insideAndInactive = MiscGameplayFunctions.MemPointDirectionalCheck(PlayerBase.Cast(params.m_Caller), this, memPointStartName, memPointEndName) && super.CanDoorBeOpened(params);
			bool outside = m_IsActive && !GetCodeLock().IsLocked() && super.CanDoorBeOpened(params);

			return insideAndInactive || outside;
		}
		
		return super.CanDoorBeOpened(params);
	}
```

The main door closes by itself after `DOOR_AUTOCLOSE_TIME`, 12 s (`P:\scripts\4_world\entities\building\bunker.c:3`, timer started in `OnDoorOpenStart` at `:73` to `:84`), and `OnDoorCloseStart` locks the code lock again (`bunker.c:86` to `:90`). `BroadcastedBunker` finds or creates its `DigitalCodeLock_Bunker` on the slot named by `CODE_LOCK_ATTACHMENT_NAME`, `"att_codelock"` (`P:\scripts\4_world\entities\building\bunker.c:174`, `ResolveCodeLock` at `:192` to `:206`).

### Doors of houses that can be rebuilt

`Rebuilding.OnConstructionDoorOpenStart` and `OnConstructionDoorCloseStart` set the phase of `doorConstructionPhysicsSource` to 1.0 and 0.0 (`P:\scripts\4_world\classes\rebuilding\rebuilding.c:439` to `:461`). Put `doorConstructionPart` and `doorConstructionPhysicsSource` on the Doors child when the door is a construction part that can be rebuilt.

### The script override trap

Vanilla Open no longer calls `CanDoorBeOpened(int, bool)`. Override `CanDoorBeOpened(notnull DoorManipulationParams params)` and call `super`.

Vanilla itself shows the trap on `P:\`: `Land_WarheadStorage_Main` and `Land_WarheadStorage_Bunker_Facility` still override the old signature, `CanDoorBeOpened(int doorIndex, bool checkIfLocked = false)` (`P:\scripts\4_world\entities\building\underground\land_warheadstorage_main.c:352`, `P:\scripts\4_world\entities\building\underground\land_warheadstorage_bunker_facility.c:20`), which `ActionOpenDoors` does not call. The source notes report that both classes moved to the `DoorManipulationParams` form in 1.30.164289; that build is not on `P:\`.
