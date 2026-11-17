# Door `model.cfg` and `config.cpp` contract

Every class and key a building door needs in `model.cfg` and `config.cpp`, the 1.30 rules for opening and locking a door, and which of these are proven. Vanilla script and config facts were checked on `P:\` (DayZ 1.30). Facts about the three example doors come from a third party tutorial and name its files.

## Contents

- [Evidence convention](#evidence-convention)
- [Name flow](#name-flow)
- [model.cfg contract](#modelcfg-contract)
- [config.cpp contract](#configcpp-contract)
- [DamageSystem contract](#damagesystem-contract)
- [Verified mappings](#verified-mappings)
- [Unverified or conflicting details](#unverified-or-conflicting-details)
- [Door open conditions and locks (DayZ 1.30)](#door-open-conditions-and-locks-dayz-130)
- [Sources](#sources)

## Evidence convention

- **Tutorial verified** means the class or key appears in one of the example files of novoGOD's door tutorial *Doors_Buttons_Lesson*, or one of its four texts teaches the behavior. The tutorial's files are not in this repo; a citation names the file and line, for example **Doors_Buttons_Lesson/Door/Simple_Door.cfg:1-14**.
- A `P:\` path with a line is a vanilla file on the work drive.
- A leading **?** means the files at hand do not confirm the claim, or the sources conflict.
- `worked-examples.md` describes the three examples in tables. Neither file copies their code, and this one describes the contract without quietly normalizing the examples.

## Name flow

The normal mapping:

**View Geometry interaction selection in the P3D, to the `model.cfg` source, to the `component` of the `class Doors` entry in `config.cpp`.**

The moving geometry:

**Moving named selection in the P3D, to a `CfgSkeletons` bone, to the `selection` of a `CfgModels` animation.**

The two chains can share a name (**door1**) or split (**selection = "door1"**, **source = "door1_open"**). See **WELCOME TO novoGODS Shit Door Tutorial.txt:17-22** and **Doors_Buttons_Lesson/Door_w_Button/Door_w_Button.cfg:27-38**.

In vanilla the `Doors` subclass name, its `component` and the animation source are always one name. All 1,373 `class Doors` entries in the configs under `P:\DZ` have a class name equal to their `component` apart from letter case, for example `class Doors5` with `component="Doors5"` (`P:\DZ\structures\residential\config.cpp:7385`). So vanilla cannot show which of the two the engine binds the animation source to. Keep all three identical in a new door and the question never comes up.

## model.cfg contract

### CfgSkeletons

The tutorial's files spell the root class **cfgSkeletons**; the usual spelling is **CfgSkeletons**. Keep the working spelling when following an example.

| Class or key | Contract | Tutorial evidence |
|---|---|---|
| **class CfgSkeletons / cfgSkeletons** | Root skeleton declaration. | Simple **Doors_Buttons_Lesson/Door/Simple_Door.cfg:1-14**; button **:1-12**; expert **:1-14**. |
| Custom skeleton class | Named by the model's **skeletonName**. | **Simple_DoorSkeleton** at Simple **:3-13**; the same in the other files. |
| **skeletonInherit** | Parent skeleton; all examples use **""**. | Simple **:5**; button **:5**; expert **:5**. |
| **isDiscrete** | All three examples use **0**. | Simple **:6**; button **:6**; expert **:6**. |
| **SkeletonBones[]** | Flat (child, parent) string pairs. | Simple **:7-12**; button **:7-10**; expert **:7-12**. |
| Parent **""** | The bone follows no animated parent. | Fundamentals text **:11-14**; the **door1** roots and the expert **lever**. |
| Parent bone name | The child follows that parent's transform. | Simple **handle,door1** at **:10-11**; expert **:9-11**. |

Prefer a skeleton name unique to the model, built from the P3D base name, such as **<p3dname>_skeleton**. The tutorial uses **Simple_DoorSkeleton**, **Door_w_ButtonSkeleton** and **Expert_ModeSkeleton**; the separator and suffix are a convention, not a proven engine rule.

? The fundamentals text says duplicate skeleton names can crash a server (**WELCOME TO novoGODS Shit Door Tutorial.txt:11**). The files at hand cannot reproduce that. Treat uniqueness as a cheap precaution.

### CfgModels and class Animations

| Class or key | Contract | Tutorial evidence |
|---|---|---|
| **class CfgModels** | Root model declaration. | Simple **Doors_Buttons_Lesson/Door/Simple_Door.cfg:15-55**; button **:13-41**; expert **:15-67**. |
| **class Default** | Empty base with sections and skeleton fields. | Simple **:17-22**; button **:15-20**; expert **:17-22**. |
| **sections[]** | Named material sections; empty here. | Simple **:19,26**; button **:17,24**; expert **:19,26**. |
| **sectionsInherit** | Inherited sections; empty here. | Simple **:20**; button **:18**; expert **:20**. |
| **skeletonName** | The exact custom skeleton class name. | Simple **:25**; button **:23**; expert **:25**. |
| Model class | Named after the P3D in all examples. | **Simple_Door :23**; **Door_w_Button :21**; **Expert_Mode :23**. |
| **class Animations** | One class per animated selection, not per source. | Simple **:27-53**; expert has three at **:27-65**. |
| **type = "rotation"** | Rotates the named selection. | Every animation class in the examples. |
| **selection** | The moving named selection, in the LODs where it exists. | Fundamentals text **:17**; Simple **:32,44**. |
| **source** | The controller or interaction name; may differ from the selection. | Fundamentals text **:18**; button **:30-32**; expert **:32-33,44-45,56-57**. |
| **axis** | A named axis selection in the Memory LOD. | Simple **:34,46**; button **:32**; expert **:34,46,58**. |
| **memory = 1** | All example rotations use Memory LOD axes. | Simple **:35,47**; button **:33**; expert **:35,47,59**. |
| **minValue** | Source phase where the motion starts. | Simple door **0.15 :36**; handle **0 :48**. |
| **maxValue** | Source phase where angle1 is reached. | Simple handle **0.15 :49**; expert lever **0.5 :61**. |
| **angle0** | Rotation at minValue; all examples use **0**. | Simple **:38,50**; button **:36**; expert **:38,50,62**. |
| **angle1** | Rotation at maxValue; the sign sets the direction in these files. | Simple **1.9/-1.4 :39,51**; expert **1.9/-1.7/-0.88 :39,51,63**. |

`angle0` and `angle1` are in radians (degrees times pi over 180). A bare number is radians; `"rad 90"` writes 90 degrees. The tutorial's values fit: Simple Door's `angle1 = 1.9` is about 109 degrees of swing. This is from the Bohemia model config wiki; the repo's own notes on these keys are in `_shared/animation/model-cfg-animations.md`.

### Source aggregation

One source can drive several animation classes:

- Simple Door: **Door1** and **handle** both use **source = "door1"** (**Doors_Buttons_Lesson/Door/Simple_Door.cfg:29-52**).
- Button: only **Door1** animates, with **source = "door1_open"** (**Doors_Buttons_Lesson/Door_w_Button/Door_w_Button.cfg:27-38**).
- Expert: **Door1**, **Handle** and **Lever** all use **source = "door1_open"** (**Doors_Buttons_Lesson/Expert_Mode/Expert_Mode.cfg:29-64**).

The button is missing from its skeleton because it does not animate (**Door_w_Button Readme.txt:65**).

## config.cpp contract

### Outer classes and the object

| Class or key | Contract | Tutorial evidence |
|---|---|---|
| **class CfgPatches** | Addon patch root. | Every example **config.cpp:1-7**. |
| Patch subclass | A patch name for the example. | Each example **config.cpp:3**. |
| **requiredAddons[] = {"DZ_Data"}** | Needed in all working examples. | Every example **config.cpp:5**; fundamentals text **:101-107,228**. |
| **class CfgVehicles** | Entity declaration root. | Every example **config.cpp:9**. |
| **class HouseNoDestruct;** | Forward declaration of the base. | Every example **config.cpp:11**. |
| **class land_*: HouseNoDestruct** | The entity class pattern used here. | Every example **config.cpp:12**. |
| **scope** | All examples use **scope = 1**. | Every example **config.cpp:14**. |
| **model** | P3D path relative to the addon. | Every example **config.cpp:15**. |
| **class Doors** | The door subsystem under the entity. | Every example **config.cpp:16**. |

`HouseNoDestruct` is a vanilla class (`P:\DZ\data\config.cpp:3119`).

`scope` is 0 private, 1 protected, 2 public. In DayZ practice a class with `scope = 1` can be placed in Terrain Builder, inherited and created by script, but tools and lists that filter on `scope = 2` do not show it. Vanilla does exactly that with `LargeTentClutterCutter`: `scope=1` (`P:\DZ\gear\camping\config.cpp:1454` to `:1456`), created from script with `CreateObjectEx` (`P:\scripts\4_world\entities\itembase\tentbase\largetent.c:140`). Buildings ship with `scope = 1`, which is what the tutorial does.

### One entry per door

| Key | Contract in the examples | Evidence |
|---|---|---|
| Doors subclass | By convention named like the source and component; **component** is the exact binding. | Simple **Doors_Buttons_Lesson/Door/config.cpp:18-21**; button **Doors_Buttons_Lesson/Door_w_Button/config.cpp:18-21**. |
| **displayName** | Label of the door or controller. | Simple, button and expert main **:20**; expert secondary **:33**. |
| **component** | The exact `model.cfg` interaction source. | Simple **:21**; button **:21**; expert **:21,34**. |
| **soundPos** | Memory point where the door sound plays. | Simple **:22**; button **:22**; expert main **:22**; the expert Lever entry has none. |
| **animPeriod** | Duration in seconds, per the tutorial. | Simple **1.3 :23**; button and expert main **1.0**; expert secondary **0.50 :35**. |
| **initPhase** | All example entries use **0.0**. | Simple **:24**; button **:24**; expert **:24,36**. |
| **initOpened** | Chance to spawn open. | Simple and button **0.0**; expert **0.5/0.0 :25,37**. |
| **soundOpen** | Opening sound name. | Full door entries of Simple, button and expert **:26**. |
| **soundClose** | Closing sound name. | The same entries **:27**. |
| **soundLocked** | Locked rattle sound. | The same entries **:28**. |
| **soundOpenABit** | Sound of opening a little. | The same entries **:29**. |
| `relatedInventorySlots[]` (1.30) | Names of the inventory slots tied to this door (locks). Read into `m_RelatedInventorySlotNames`. Not in the tutorial. | `P:\scripts\3_game\entities\additionaldoorsinfo.c:23` to `:27` |
| `lockCompatibilityBitMask` (1.30) | An integer already in bit form. When the key is missing, script uses `1 << EBuildingLockType.LOCKPICK`. | `P:\scripts\3_game\entities\additionaldoorsinfo.c:29` to `:32` |
| `interactPositionPoint`, `interactDirPoint` (1.30) | Memory point names for a door that opens from one side. The members are `m_InteractLimitingPositionPoint` and `m_InteractLimitingDirPoint`. | `P:\scripts\3_game\entities\additionaldoorsinfo.c:34` to `:38` |
| `doorConstructionPart`, `doorConstructionPhysicsSource` (1.30) | For a door of a house that can be rebuilt: the construction part name, and the `AnimationSources` name that switches the door's physics. | `P:\scripts\3_game\entities\additionaldoorsinfo.c:40` to `:44` |

The tutorial's sound list is **DZ\sounds\hpp\config.cpp** (**WELCOME TO novoGODS Shit Door Tutorial.txt:255-256**); on the work drive `class doorMetalSmallOpen` is at `P:\DZ\sounds\hpp\config.cpp:519064`. Check that a sound exists there before using it.

`initPhase` is the animation phase (0 to 1) the door has when it spawns, not a start delay. The tutorial's "time it takes to start" wording is wrong; its files use `0.0`, which spawns the door closed. Source: the Bohemia wiki page on doors on buildings ("initial value for the animation").

`initOpened` is a spawn probability: when a random number is below `initOpened` the door spawns open, so `0` never spawns open and `0.5` does about half the time. Source: the same wiki page. Vanilla houses use values such as 0.3 and 0.7.

### One source, one Doors entry

Start from this rule: one **class Doors** subclass per unique **source**, with **component** equal to that source. Animated selections that share the source get no entry of their own. Simple and Button follow it.

? Expert breaks it: its model has only **source = "door1_open"** (**Doors_Buttons_Lesson/Expert_Mode/Expert_Mode.cfg:33,45,57**), but its config declares **Door1_Open** and **Lever**, both with **component = "door1_open"** (**Doors_Buttons_Lesson/Expert_Mode/config.cpp:18-38**). Ask the user before copying the second entry.

## DamageSystem contract

| Class or key | Role in the examples | Tutorial evidence |
|---|---|---|
| **class DamageSystem** | Root damage definition. | Simple and button **config.cpp:32-84**; expert **:40-92**. |
| **GlobalHealth > Health** | Global **hitpoints = 1000**. | Simple and button **:34-40**; expert **:42-48**. |
| **GlobalArmor** | Projectile and Melee damage to Health, Blood and Shock all **0**. | Simple and button **:41-55**; expert **:49-63**. |
| **DamageZones** | Zones per component. | Simple and button **:56-83**; expert **:64-91**. |
| Zone **class Door1** | The zone name in all examples. | Simple and button **:58**; expert **:66**. |
| Zone **class Health** | **hitpoints = 1000**, **transferToGlobalCoef = 0**. | Simple and button **:60-64**; expert **:68-72**. |
| **componentNames[]** | The moving geometry **{"door1"}**, even when the source is **door1_open**. | Simple and button **:65**; expert **:73**. |
| **fatalInjuryCoef** | **-1** in every zone. | Simple and button **:66**; expert **:74**. |
| **class ArmorType** | Projectile Health **2**; Melee Health **2.5**; Blood and Shock **0**. | Simple and button **:67-81**; expert **:75-89**. |

Do not replace **DamageZones.componentNames[]** with the Doors component by reflex: Button and Expert show the two can differ.

## Verified mappings

| Pattern | Bones | Animation selections | Unique source | Doors component |
|---|---|---|---|---|
| Simple Door | door1 -> ""; handle -> door1 | door1, handle | door1 | door1 |
| Door with Button | door1 -> "" | door1 | door1_open | door1_open |
| Expert Mode | door1 -> ""; handle -> door1; lever -> "" | door1, handle, lever | door1_open | door1_open twice |

## Unverified or conflicting details

Settled against the Bohemia wiki (details in the sections above): `angle0` and `angle1` are radians, `initPhase` is the starting phase and not a delay, `initOpened` is a spawn probability, `scope` 0, 1, 2 is private, protected, public.

Still open:

- ? Duplicate skeleton names crashing a server: a tutorial warning that was not reproduced. Keep names unique as a precaution.
- A conflict, settled by the files: the one source, one Doors entry rule is broken by Expert, where two Doors entries share the component `door1_open`. It is a quirk of that example.
- A conflict, settled by the files: the Expert text shows `soundOpen = "switchOpen"` and `soundClose = "switchClose"`, but the tutorial's real `Doors_Buttons_Lesson/Expert_Mode/config.cpp:31-38` has neither. The file wins.
- No `config.cpp` under `P:\DZ` sets `relatedInventorySlots[]`, `lockCompatibilityBitMask`, `interactPositionPoint`, `interactDirPoint`, `doorConstructionPart` or `doorConstructionPhysicsSource` (searched every `.cpp` there). The parser and the scripts that use the values are on `P:\`; a vanilla `class Doors` block to copy these keys from is not, because the Badlands structures that would carry them are not unpacked. What vanilla does show is the fence listing `Att_CombinationLock` and `Att_CodeLock` in its entity level `attachments[]` (`class Fence`, list at `P:\DZ\gear\camping\config.cpp:4362` to `:4368`).

## Door open conditions and locks (DayZ 1.30)

The source notes report that until 1.29 `Building.CanDoorBeOpened(int doorIndex, bool checkIfLocked = false)` was the only signature, that vanilla `ActionOpenDoors` called it directly, and that `GetLockCompatibilityType` always returned `1 << EBuildingLockType.LOCKPICK`. That build is not on `P:\`.

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

Combination locks and code locks are inventory items that return true from `IsExternalLockType()` (`P:\scripts\4_world\entities\itembase\codelock.c:542`, `P:\scripts\4_world\entities\itembase\combinationlock.c:779`; the base method is at `P:\scripts\4_world\entities\itembase.c:4848`). They are not extra `EBuildingLockType` values. A `COMBINATION_LOCK = 2` or `CODE_LOCK = 4` seen in other notes does not exist in this enum.

`GetLockCompatibilityType` returns `GetDoorInfo(doorIdx).m_LockCompatibilityBitMask` (`P:\scripts\3_game\entities\building.c:193` to `:196`). `ActionLockDoors` still tests that mask against `tool.GetKeyCompatibilityType()`, but first returns false when any related slot already holds an `IsExternalLockType()` item (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionlockdoors.c:40` to `:57`).

The native engine locks are still there: `IsDoorLocked`, `LockDoor` and `UnlockDoor` (`P:\scripts\3_game\entities\building.c:55` to `:70`).

## Sources

novoGOD's tutorial *Doors_Buttons_Lesson* (files dated 2025-04-23; third party, not in this repo). Texts read in full:

- **WELCOME TO novoGODS Shit Door Tutorial.txt**
- **Simple_Door Readme.txt**
- **Door_w_Button Readme.txt**
- **Welcome to novoGODs Expert_Mode Door mod.txt**

Example files:

- **Doors_Buttons_Lesson/Door/Simple_Door.cfg** and **Doors_Buttons_Lesson/Door/config.cpp**
- **Doors_Buttons_Lesson/Door_w_Button/Door_w_Button.cfg** and **Doors_Buttons_Lesson/Door_w_Button/config.cpp**
- **Doors_Buttons_Lesson/Expert_Mode/Expert_Mode.cfg** and **Doors_Buttons_Lesson/Expert_Mode/config.cpp**

Official references the tutorial points at:

- https://community.bistudio.com/wiki/DayZ:Doors_on_buildings
- https://github.com/BohemiaInteractive/DayZ-Samples
- https://community.bistudio.com/wiki/LOD
