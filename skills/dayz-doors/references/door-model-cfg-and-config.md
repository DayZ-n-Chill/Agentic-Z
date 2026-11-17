# Door `model.cfg` and `config.cpp` contract

Every class and key a building door needs in `model.cfg` and `config.cpp`, the 1.30 rules for opening and locking a door, and which of these are proven. Vanilla script and config facts were checked on `P:\` (DayZ 1.30). The three worked patterns are third-party mod patterns, not vanilla; their values cannot be checked on `P:\`.

## Contents

- [Evidence convention](#evidence-convention)
- [Name flow](#name-flow)
- [model.cfg contract](#modelcfg-contract)
- [config.cpp contract](#configcpp-contract)
- [DamageSystem contract](#damagesystem-contract)
- [Verified mappings](#verified-mappings)
- [Unverified or conflicting details](#unverified-or-conflicting-details)
- [Door open conditions and locks (DayZ 1.30)](#door-open-conditions-and-locks-dayz-130)

## Evidence convention

- **In the worked patterns** means the class or key is in the `model.cfg` or `config.cpp` of one of the three worked patterns: Simple Door (`Simple_Door.cfg`), Door with Button (`Door_w_Button.cfg`) and Expert Mode (`Expert_Mode.cfg`), each with its own `config.cpp`. These are third-party mod patterns, not vanilla, and their files are not in this repo.
- A `P:\` path with a line is a vanilla file on the work drive.
- A leading **?** means the files at hand do not confirm the claim, or two of them conflict.
- `worked-examples.md` describes the three patterns in tables. Neither file copies their code, and this one describes the contract without quietly normalizing the patterns.

## Name flow

The normal mapping:

**View Geometry interaction selection in the P3D, to the `model.cfg` source, to the `component` of the `class Doors` entry in `config.cpp`.**

The moving geometry:

**Moving named selection in the P3D, to a `CfgSkeletons` bone, to the `selection` of a `CfgModels` animation.**

The two chains can share a name (**door1**, as in Simple Door) or split (**selection = "door1"**, **source = "door1_open"**, as in Door with Button).

In vanilla the `Doors` subclass name, its `component` and the animation source are always one name. All 1,373 `class Doors` entries in the configs under `P:\DZ` have a class name equal to their `component` apart from letter case, for example `class Doors5` with `component="Doors5"` (`P:\DZ\structures\residential\config.cpp:7385`). So vanilla cannot show which of the two the engine binds the animation source to. Keep all three identical in a new door and the question never comes up.

## model.cfg contract

### CfgSkeletons

The three worked patterns spell the root class **cfgSkeletons**; the usual spelling is **CfgSkeletons**. Keep the working spelling when following a pattern.

| Class or key | Contract | In the worked patterns |
|---|---|---|
| **class CfgSkeletons / cfgSkeletons** | Root skeleton declaration. | All three. |
| Custom skeleton class | Named by the model's **skeletonName**. | **Simple_DoorSkeleton**, **Door_w_ButtonSkeleton**, **Expert_ModeSkeleton**. |
| **skeletonInherit** | Parent skeleton. | **""** in all three. |
| **isDiscrete** | Skeleton flag. | **0** in all three. |
| **SkeletonBones[]** | Flat (child, parent) string pairs. | All three. |
| Parent **""** | The bone follows no animated parent. | The **door1** roots and the Expert **lever**. |
| Parent bone name | The child follows that parent's transform. | **handle, door1** in Simple and Expert. |

Prefer a skeleton name unique to the model, built from the P3D base name, such as **<p3dname>_skeleton**. The separator and suffix are a convention, not a proven engine rule.

? Duplicate skeleton names may crash a server. The files at hand cannot reproduce that. Treat uniqueness as a cheap precaution.

### CfgModels and class Animations

| Class or key | Contract | In the worked patterns |
|---|---|---|
| **class CfgModels** | Root model declaration. | All three. |
| **class Default** | Empty base with sections and skeleton fields. | All three. |
| **sections[]** | Named material sections. | Empty in all three. |
| **sectionsInherit** | Inherited sections. | Empty in all three. |
| **skeletonName** | The exact custom skeleton class name. | All three. |
| Model class | Named after the P3D. | **Simple_Door**, **Door_w_Button**, **Expert_Mode**. |
| **class Animations** | One class per animated selection, not per source. | Simple has two, Button one, Expert three. |
| **type = "rotation"** | Rotates the named selection. | Every animation class. |
| **selection** | The moving named selection, in the LODs where it exists. | **door1**, **handle**, **lever**. |
| **source** | The controller or interaction name; may differ from the selection. | **door1** in Simple; **door1_open** in Button and Expert. |
| **axis** | A named axis selection in the Memory LOD. | **door1_axis**, **handle_axis**, **lever_axis**. |
| **memory = 1** | The axis is read from the Memory LOD. | Every rotation. |
| **minValue** | Source phase where the motion starts. | Simple door **0.15**, Simple handle **0**. |
| **maxValue** | Source phase where angle1 is reached. | Simple handle **0.15**, Expert lever **0.5**. |
| **angle0** | Rotation at minValue. | **0** in every rotation. |
| **angle1** | Rotation at maxValue; the sign sets the direction. | Simple **1.9** and **-1.4**; Expert **1.9**, **-1.7** and **-0.88**. |

`angle0` and `angle1` are in radians (degrees times pi over 180). A bare number is radians; `"rad 90"` writes 90 degrees. The pattern values fit: Simple Door's `angle1 = 1.9` is about 109 degrees of swing. This is engine behaviour, not checkable on `P:\`; the repo's notes on these keys are in `_shared/animation/model-cfg-animations.md`.

### Source aggregation

One source can drive several animation classes:

- Simple Door: **Door1** and **handle** both use **source = "door1"**.
- Button: only **Door1** animates, with **source = "door1_open"**.
- Expert: **Door1**, **Handle** and **Lever** all use **source = "door1_open"**.

The button is missing from its skeleton because it does not animate.

## config.cpp contract

### Outer classes and the object

| Class or key | Contract | In the worked patterns |
|---|---|---|
| **class CfgPatches** | Addon patch root. | All three. |
| Patch subclass | A patch name for the addon. | All three. |
| **requiredAddons[] = {"DZ_Data"}** | Needed in every working pattern. | All three. |
| **class CfgVehicles** | Entity declaration root. | All three. |
| **class HouseNoDestruct;** | Forward declaration of the base. | All three. |
| **class land_*: HouseNoDestruct** | The entity class. | **land_Simple_Door** and its two siblings. |
| **scope** | See below. | **scope = 1** in all three. |
| **model** | P3D path relative to the addon. | All three. |
| **class Doors** | The door subsystem under the entity. | All three. |

`HouseNoDestruct` is a vanilla class (`P:\DZ\data\config.cpp:3119`).

`scope` is 0 private, 1 protected, 2 public. In DayZ practice a class with `scope = 1` can be placed in Terrain Builder, inherited and created by script, but tools and lists that filter on `scope = 2` do not show it. Vanilla does exactly that with `LargeTentClutterCutter`: `scope=1` (`P:\DZ\gear\camping\config.cpp:1454` to `:1456`), created from script with `CreateObjectEx` (`P:\scripts\4_world\entities\itembase\tentbase\largetent.c:140`). Buildings ship with `scope = 1`, which is what the worked patterns do.

### One entry per door

| Key | Contract | In the worked patterns, or where vanilla reads it |
|---|---|---|
| Doors subclass | By convention named like the source and component; **component** is the exact binding. | **Door1** in Simple; **Door1_Open** in Button and Expert; **Lever** as Expert's second entry. |
| **displayName** | Label of the door or controller. | Every entry. |
| **component** | The exact `model.cfg` interaction source. | **door1** in Simple; **door1_open** in Button and in both Expert entries. |
| **soundPos** | Memory point where the door sound plays. | **door1_action**; the Expert Lever entry has none. |
| **animPeriod** | Duration in seconds. | Simple **1.3**; Button and Expert main **1.0**; Expert Lever **0.50**. |
| **initPhase** | Animation phase at spawn. | **0.0** in every entry. |
| **initOpened** | Chance to spawn open. | Simple and Button **0.0**; Expert main **0.5**, Lever **0.0**. |
| **soundOpen** | Opening sound name. | Every entry except the Expert Lever. |
| **soundClose** | Closing sound name. | The same entries. |
| **soundLocked** | Locked rattle sound. | The same entries. |
| **soundOpenABit** | Sound of opening a little. | The same entries. |
| `relatedInventorySlots[]` (1.30) | Names of the inventory slots tied to this door (locks). Read into `m_RelatedInventorySlotNames`. Not in the worked patterns. | `P:\scripts\3_game\entities\additionaldoorsinfo.c:23` to `:27` |
| `lockCompatibilityBitMask` (1.30) | An integer already in bit form. When the key is missing, script uses `1 << EBuildingLockType.LOCKPICK`. | `P:\scripts\3_game\entities\additionaldoorsinfo.c:29` to `:32` |
| `interactPositionPoint`, `interactDirPoint` (1.30) | Memory point names for a door that opens from one side. The members are `m_InteractLimitingPositionPoint` and `m_InteractLimitingDirPoint`. | `P:\scripts\3_game\entities\additionaldoorsinfo.c:34` to `:38` |
| `doorConstructionPart`, `doorConstructionPhysicsSource` (1.30) | For a door of a house that can be rebuilt: the construction part name, and the `AnimationSources` name that switches the door's physics. | `P:\scripts\3_game\entities\additionaldoorsinfo.c:40` to `:44` |

The door sounds are defined in `P:\DZ\sounds\hpp\config.cpp`; `class doorMetalSmallOpen` is at `P:\DZ\sounds\hpp\config.cpp:519064`. Check that a sound exists there before using it.

`initPhase` is the animation phase (0 to 1) the door has when it spawns, not a start delay. `0.0` spawns the door closed. This is engine behaviour, not checkable on `P:\`.

`initOpened` is a spawn probability: when a random number is below `initOpened` the door spawns open, so `0` never spawns open and `0.5` does about half the time. This too is engine behaviour, not checkable on `P:\`. Vanilla houses use values such as 0.3 and 0.7 (`initOpened=0.69999999`, `P:\DZ\structures\residential\config.cpp:7392`).

### One source, one Doors entry

Start from this rule: one **class Doors** subclass per unique **source**, with **component** equal to that source. Animated selections that share the source get no entry of their own. Simple and Button follow it.

? Expert breaks it: its model has only **source = "door1_open"**, but its config declares **Door1_Open** and **Lever**, both with **component = "door1_open"**. Ask the user before copying the second entry.

## DamageSystem contract

All three worked patterns carry the same `DamageSystem`.

| Class or key | Value in the worked patterns |
|---|---|
| **class DamageSystem** | Root damage definition. |
| **GlobalHealth > Health** | Global **hitpoints = 1000**. |
| **GlobalArmor** | Projectile and Melee damage to Health, Blood and Shock all **0**. |
| **DamageZones** | Zones per component. |
| Zone **class Door1** | The one zone, in all three. |
| Zone **class Health** | **hitpoints = 1000**, **transferToGlobalCoef = 0**. |
| **componentNames[]** | The moving geometry **{"door1"}**, even when the source is **door1_open**. |
| **fatalInjuryCoef** | **-1** in every zone. |
| **class ArmorType** | Projectile Health **2**; Melee Health **2.5**; Blood and Shock **0**. |

Do not replace **DamageZones.componentNames[]** with the Doors component by reflex: Button and Expert show the two can differ.

## Verified mappings

| Pattern | Bones | Animation selections | Unique source | Doors component |
|---|---|---|---|---|
| Simple Door | door1 -> ""; handle -> door1 | door1, handle | door1 | door1 |
| Door with Button | door1 -> "" | door1 | door1_open | door1_open |
| Expert Mode | door1 -> ""; handle -> door1; lever -> "" | door1, handle, lever | door1_open | door1_open twice |

## Unverified or conflicting details

Settled (details in the sections above): `angle0` and `angle1` are radians, `initPhase` is the starting phase and not a delay, `initOpened` is a spawn probability, `scope` 0, 1, 2 is private, protected, public.

Still open:

- ? Duplicate skeleton names crashing a server: not reproduced. Keep names unique as a precaution.
- The one source, one Doors entry rule is broken by Expert, where two Doors entries share the component `door1_open`. It is a quirk of that pattern.
- The Expert Lever entry sets no `soundPos`, no `soundOpen` and no `soundClose`.
- No `config.cpp` under `P:\DZ` sets `relatedInventorySlots[]`, `lockCompatibilityBitMask`, `interactPositionPoint`, `interactDirPoint`, `doorConstructionPart` or `doorConstructionPhysicsSource` (searched every `.cpp` there). The parser and the scripts that use the values are on `P:\`; a vanilla `class Doors` block to copy these keys from is not, because the Badlands structures that would carry them are not unpacked. What vanilla does show is the fence listing `Att_CombinationLock` and `Att_CodeLock` in its entity level `attachments[]` (`class Fence`, list at `P:\DZ\gear\camping\config.cpp:4362` to `:4368`).

## Door open conditions and locks (DayZ 1.30)

Until 1.29 `Building.CanDoorBeOpened(int doorIndex, bool checkIfLocked = false)` was the only signature, vanilla `ActionOpenDoors` called it directly, and `GetLockCompatibilityType` always returned `1 << EBuildingLockType.LOCKPICK`. That build is not on `P:\`, so this is not checked there.

In 1.30 both signatures exist. The `int` form is a wrapper that builds a `DoorManipulationParams` and does not set `m_Caller`. Vanilla Open uses the params form and a directional check.

```c
// P:\scripts\3_game\entities\building.c:5
class DoorManipulationParams
{
	int m_DoorIndex;
	bool m_CheckIfLocked;
	Object m_Caller;
}
```

```c
// P:\scripts\3_game\entities\building.c:141
	bool CanDoorBeOpened(notnull DoorManipulationParams params)
	{
		if (IsDoorOpen(params.m_DoorIndex))
			return false;

		if (params.m_CheckIfLocked)
		{
			if (IsDoorLocked(params.m_DoorIndex))
				return false;
		}
		else
		{
			if (!IsDoorLocked(params.m_DoorIndex))
				return false;
		}

		return true;
	}
```

```c
// P:\scripts\3_game\entities\building.c:160
	bool CanDoorBeOpened(int doorIndex, bool checkIfLocked = false)
	{
		DoorManipulationParams doorParams = new DoorManipulationParams();
		doorParams.m_DoorIndex = doorIndex;
		doorParams.m_CheckIfLocked = checkIfLocked;

		return CanDoorBeOpened(doorParams);
	}
```

`ActionOpenDoors` fills `m_DoorIndex`, `m_CheckIfLocked` and `m_Caller`, and requires `DoorsDirectionalCheck` before Open:

```c
// P:\scripts\4_world\classes\useractionscomponent\actions\interact\actionopendoors.c:36
		BuildingBase building;
		if (Class.CastTo(building, target.GetObject()))
		{
			DoorManipulationParams doorParams = new DoorManipulationParams();
			doorParams.m_DoorIndex = building.GetDoorIndex(target.GetComponentIndex());
			if (doorParams.m_DoorIndex != -1)
			{
				if (!IsInReach(player, target, UAMaxDistances.DEFAULT)) 
					return false;
				
				if (!building.DoorsDirectionalCheck(player,target.GetComponentIndex()))
					return false;
				
				doorParams.m_CheckIfLocked = CheckIfDoorIsLocked();
				doorParams.m_Caller = player;

				return building.CanDoorBeOpened(doorParams);
			}
		}
```

`BuildingBase` then refuses Open while a related `DigitalCodeLock` or `CombinationLock` is locked:

```c
// P:\scripts\4_world\entities\game\super\building.c:312
		int doorIndex = params.m_DoorIndex;
		AdditionalDoorInfo doorInfo = GetDoorInfo(doorIndex);
		if (doorInfo && doorInfo.m_RelatedInventorySlotNames)
		{
			foreach(string relatedSlotName: doorInfo.m_RelatedInventorySlotNames)
			{
				EntityAI slotEntity = FindAttachmentBySlotName(relatedSlotName);
				if (!slotEntity)
					continue;
				
				DigitalCodeLock codeLock;
				if (Class.CastTo(codeLock, slotEntity) && codeLock.IsLocked())
					return false;
				
				CombinationLock combinationLock;
				if (Class.CastTo(combinationLock, slotEntity) && combinationLock.IsLocked())
					return false;
			}
		}
		
		return true;
```

The directional check. Missing or empty memory point names pass, because the helper returns true:

```c
// P:\scripts\4_world\entities\game\super\building.c:335
	//! checks against player relative to defined door direction, some doors can only be operated from one side
	bool DoorsDirectionalCheck(PlayerBase player, int componentIdx)
	{
		string memPointPos = GetDoorInfo(GetDoorIndex(componentIdx)).m_InteractLimitingPositionPoint;
		string memPointDir = GetDoorInfo(GetDoorIndex(componentIdx)).m_InteractLimitingDirPoint;
		
		return MiscGameplayFunctions.MemPointDirectionalCheck(player, this, memPointPos, memPointDir);
	}
```

```c
// P:\scripts\4_world\static\miscgameplayfunctions.c:942
	static bool MemPointDirectionalCheck(PlayerBase player, EntityAI targetEnt, string memPointStartName, string memPointEndName, float toleranceAngle = Math.PI_HALF)
	{
		if (player && targetEnt && memPointEndName != "" && targetEnt.MemoryPointExists(memPointEndName) && memPointStartName != "" && targetEnt.MemoryPointExists(memPointStartName))
		{
			vector memPointEndPos = targetEnt.ModelToWorld(targetEnt.GetMemoryPointPos(memPointEndName));
			vector memPointStartPos = targetEnt.ModelToWorld(targetEnt.GetMemoryPointPos(memPointStartName));
			vector playerPosition = player.GetPosition();
			vector playerHeadPos = MiscGameplayFunctions.GetPlayerHeadPosition(player);
			vector playerDir = vector.Direction(playerHeadPos, memPointStartPos);
			playerDir.Normalize();
			vector memDir = vector.Direction(memPointStartPos, memPointEndPos);
			memDir.Normalize();
```

When that `if` fails (empty names or missing Memory points), the function returns `true` (`P:\scripts\4_world\static\miscgameplayfunctions.c:944` to `:967`).

### `EBuildingLockType` is not the attachment locks

```c
// P:\scripts\3_game\enums\ebuildinglocktypes.c:7
enum EBuildingLockType
{
	NONE = 0, //unlockable only via script
	LOCKPICK,
	SHIP_CONTAINER_0,
	SHIP_CONTAINER_1,
	SHIP_CONTAINER_2,
	SHIP_CONTAINER_3,
	SHIP_CONTAINER_4
}
```

Combination locks and code locks are inventory items that return true from `IsExternalLockType()` (`P:\scripts\4_world\entities\itembase\codelock.c:542`, `P:\scripts\4_world\entities\itembase\combinationlock.c:779`; the base method is at `P:\scripts\4_world\entities\itembase.c:4848`). They are not extra `EBuildingLockType` values. There is no `COMBINATION_LOCK = 2` or `CODE_LOCK = 4` in this enum.

`GetLockCompatibilityType` returns `GetDoorInfo(doorIdx).m_LockCompatibilityBitMask` (`P:\scripts\3_game\entities\building.c:193` to `:196`). `ActionLockDoors` still tests that mask against `tool.GetKeyCompatibilityType()`, but first returns false when any related slot already holds an `IsExternalLockType()` item (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionlockdoors.c:40` to `:57`).

The native engine locks are still there: `IsDoorLocked`, `LockDoor` and `UnlockDoor` (`P:\scripts\3_game\entities\building.c:55` to `:70`).
