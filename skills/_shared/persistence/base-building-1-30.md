# Base building on 1.30

What DayZ 1.30 changed in the construction system for player built objects: the class tree, the per type config cache, the `*ServerEx` methods, the build collision check, masonry and the fence code lock, with what each change breaks in a 1.29 mod. Rebuildable map buildings, which 1.30 added beside this system, are in `base-building-rebuildable.md`.

The 1.29 scripts are not on `P:\`. Every statement of what 1.29 did is a comparison that is not checked here; every 1.30 fact cites the current scripts.

## The class tree

`ConstructionBasic` in `3_Game` is an empty shell (`P:\scripts\3_game\systems\construction_basic.c:2` to `:43`). It has no `GetParent`, `IsPartConstructed` or `HasBase`; those are on `ConstructionBase` in `4_World`.

| Class | Parent | Source |
|---|---|---|
| `ConstructionBase` | `ConstructionBasic` | `P:\scripts\4_world\classes\constructionbase.c:30` |
| `Construction` | `ConstructionBase` | `P:\scripts\4_world\classes\basebuilding\construction.c:2` |
| `Rebuilding` | `ConstructionBase` | `P:\scripts\4_world\classes\rebuilding\rebuilding.c:1` |

`EntityAI.CreateConstructionComponent` returns `null` (`P:\scripts\3_game\entities\entityai.c:3474` to `:3478`), and `ConstructionInit` (`:3464` to `:3471`) sets the component up only when an override returns one. `BaseBuildingBase` overrides it:

```c
// P:\scripts\4_world\entities\itembase\basebuildingbase.c:872
override protected ConstructionBasic CreateConstructionComponent()
{
    m_Construction = new Construction(this);
    return m_Construction;
}

Construction GetConstruction()
{
    return Construction.Cast(m_Construction);
}
```

The field is `protected ref ConstructionBasic m_Construction` (`basebuildingbase.c:15`), so outside code that read it as `Construction` no longer compiles. Use `GetConstruction()` (`:883` to `:886`) or `Construction.Cast(GetConstructionBasic())`.

## Part config is cached per type

A `ConstructionPart` instance now holds only changing state: `m_PartTypeData`, `m_LocalSyncBitMask` and `m_IsBuilt` (`P:\scripts\4_world\classes\basebuilding\constructionpart.c:9` to `:12`). The config fields live once per entity type in `ConstructionPartTypeData`, filled by `InitPartTypeData` (`P:\scripts\4_world\classes\basebuilding\typeconstructiondata\constructionparttyped.c:45` to `:70` and `:75` to `:107`). In 1.29 each instance read config itself in `UpdateConstructionParts`.

- The old constructor `ConstructionPart(string name, string part_name, ..., array<string> required_parts)` still exists but its body is empty (`constructionpart.c:14` to `:16`). There is no constructor that takes the type data.
- `UpdateConstructionParts` (`P:\scripts\4_world\classes\constructionbase.c:575` to `:606`) reads `GetConstructionDataHolderBasic()` from the entity type, spawns each part through `CreatePartInstanceObject` (`partTypename.Spawn()`, `:608` to `:611`) from the type's `GetCustomInstanceType()` or else `GetDefaultPartInstanceTypename()`, then calls `SetPartTypeData` (`:596` to `:599`).
- `SetPartTypeData` refuses a second call with "cannot override m_PartTypeData during runtime!" (`constructionpart.c:395` to `:401`).
- `ConstructionDataTypeHolderBasic` in `3_Game` is another empty shell (`P:\scripts\3_game\systems\constructiontypedata_basic.c:2` to `:5`); the real holder is `ConstructionDataTypeHolder` (`P:\scripts\4_world\classes\basebuilding\typeconstructiondata\constructionparttypedholder.c:2`).
- `SetRequestBuiltState` is `[Obsolete("1.30: Use 'SetBuiltState' directly")]` and only sets the state in multiplayer (`constructionpart.c:505` to `:512`).

The config key names did not change. Each key and its reader is in `base-building-config.md`.

## Build and dismantle go through the Ex methods

`BuildPartServer` and `DismantlePartServer` are `[Obsolete]` wrappers that call the new methods (`constructionbase.c:1702` to `:1716`). An override of the old names never runs, because vanilla calls the new ones:

```c
// P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionbuildpart.c:167
if (!construction.IsCollidingEx(checkData) && canBuild)
{
    construction.BuildPartServerEx(action_data.m_Player, partName, AT_BUILD_PART);
```

| Method | What it does | Source |
|---|---|---|
| `BuildPartServerEx(Man player, string part_name, int action_id)` | on `ConstructionBase`, only `TakeMaterialsServer(part_name)`; `player` can be null | `constructionbase.c:177` to `:184` |
| `Construction.BuildPartServerEx` | also calls `m_Parent.OnPartBuiltServer` | `construction.c:52` to `:68` |
| `DismantlePartServerEx` | the dismantle path | `constructionbase.c:190` |

## Build collision takes a data object

`IsCollidingEx(CollisionCheckData check_data)` (`constructionbase.c:1481`) replaces the string based check. There is no `IsCollidingEx(string, Object, bool, bool)`. `CollisionCheckData` (`:1916` to `:1930`) holds `m_AdditionalExcludes`, `m_PartName`, `m_PrimaryGeometry` (default `ObjIntersectGeom`) and `m_SecondaryGeometry` (default `ObjIntersectView`). Fill `m_PartName` and, if needed, the excludes; vanilla adds the player (`actionbuildpart.c:157` to `:160`).

The trigger helpers are still there but marked `[Obsolete("no replacement")]`: `CreateCollisionTrigger` (`constructionbase.c:1756`), `DestroyCollisionTrigger` and `IsTriggerColliding` (`:1784` to `:1795`). `m_ConstructionBoxTrigger` is commented `//! Deprecated` (`:1803`). Old calls compile; do not write new ones.

`ConstructionActionData.SetSlotId` and `GetSlotId` are also kept and marked `[Obsolete("1.30: Unsafe, overridden ActionData used in-system instead")]` (`P:\scripts\4_world\classes\basebuilding\constructionactiondata.c:617` to `:627`).

## Masonry

1.30 adds bricklaying to the tool masks. `EConstructionTools` gains `TOOL_BRICKLAYING = 256` (`P:\scripts\4_world\classes\basebuilding\constructionconstants.c:13` to `:26`, the new value at `:25`); vanilla's comment over the enum says it "has to mirror tool defines in configs!".

| Item or action | What it does | Source |
|---|---|---|
| `BrickTrowel` | a `ToolBase` that adds `ActionBuildPart` and `ActionRepairPart`; builds with the `CMD_ACTIONFB_BRICKTROWEL` animation | `P:\scripts\4_world\entities\itembase\bricktrowel.c:1` to `:8`; `actionbuildpart.c:260` to `:262` |
| `ActionPickUpBricks` | takes bricks from a `PileOfBricks`, `YIELD = 3` | `P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionpickupbricks.c:16` to `:18` |
| `MortarMix` | mixed at water or a well into `MortarMix_Opened` | `P:\scripts\4_world\entities\itembase\mortarmix.c:1` to `:8` |
| `ActionMixMortarAtWell` | the well variant, allowed when the target's `IsWell()` is true; `MortarMix` adds both actions | `P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionmixmortaratwell.c:2` and `:24`; `mortarmix.c:6` and `:7` |
| `ActionMixMortarAtWater` | uses a `CCTLiquid` target | `P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionmixmortaratwater.c:23` and `:47` to `:50` |
| `MortarMix_Opened` | adds only `ActionAttachToConstruction` | `P:\scripts\4_world\entities\itembase\mortarmix_opened.c:1` to `:8` |
| `CommonBrick` | adds the attach to construction action | `P:\scripts\4_world\entities\itembase\commonbrick.c:1` to `:8` |

`ConstructionMaterialType` now sits in `constructionbase.c:2` to `:12` and adds `MATERIAL_BRICK = 6` and `MATERIAL_RUBBLE = 7` to the six older values.

Not checked on `P:\`: the `build_action_type` of `BrickTrowel`. The class name appears in scripts and in the character sound config (`P:\DZ\characters\data\config.cpp:7296`), but no `class BrickTrowel` block is in the unpacked `CfgVehicles` configs.

## Fence code lock and the combination lock

`Fence` now accepts a `DigitalCodeLock` in slot `Att_CodeLock` beside the `CombinationLock` in `Att_CombinationLock` (`P:\scripts\4_world\entities\itembase\basebuildingbase\fence.c:18` to `:26`), found with `GetCodeLock()` (`fence.c:161` to `:165`). How the two locks exclude each other is in `base-building-fence-gate.md`.

Dialling the right numbers no longer unlocks a combination lock: it has its own `ActionCombinationLockUnlock` (`P:\scripts\4_world\entities\itembase\combinationlock.c:686`). The lock also saves a third value, `m_CombinationInside`, read only from storage version 143 (`combinationlock.c:128` to `:136`). The stream changes are in `dayz-1-30-persistence.md`.

Lock slots on map building doors are a separate system, in `_shared/animation/building-door-locks.md`.

## The save did not change

`BaseBuildingBase.OnStoreSave` still writes `m_SyncParts01`, `m_SyncParts02`, `m_SyncParts03`, then `m_HasBase`, after `super` (`basebuildingbase.c:420` to `:430`), one bit per part for ids 1 to 93. The Fence still writes its gate fields after `super` (`fence.c:246` to `:254`). The ten int `Rebuilding` save belongs to map buildings only.

## Simulation switch on houses

The 1.30 changelog lists a `disableSimulation` config parameter for house based entities; this is not checked on `P:\` and is not a `BaseBuildingBase` field. The script side is the native pair `DisableSimulation(bool disable)` and `GetIsSimulationDisabled()` (`P:\scripts\3_game\entities\entity.c:3` to `:6`).

## What breaks in a 1.29 mod

| Break | Fix |
|---|---|
| An override of `BuildPartServer`, `DismantlePartServer` or `IsColliding` never runs | Move the override to the `*Ex` method |
| Code calls `CreateCollisionTrigger` | Build a `CollisionCheckData` and call `IsCollidingEx` |
| Outside code reads `m_Construction` as `Construction` | Call `GetConstruction()` or `GetConstructionBasic()` |
| Code builds a `ConstructionPart` with the old constructor | It gets no type data; spawn the part and call `SetPartTypeData` |
| Automation assumes the last dial unlocks a combination lock | Use `ActionCombinationLockUnlock` |
| A `CombinationLock` subclass reads two values in its own `OnStoreLoad` | Call `super`, or read `m_CombinationInside` from version 143 on |

## Porting checklist

- Override `BuildPartServerEx`, `DismantlePartServerEx` and `IsCollidingEx`, not the old names.
- Reach the construction through `GetConstruction()` or `GetConstructionBasic()`.
- Keep every `BaseBuildingBase` part `id` between 1 and 93 and the save order `m_SyncParts01`, `02`, `03`, `m_HasBase`.
- Never write the ten int `Rebuilding` block from a `BaseBuildingBase` subclass.
- To lock a fence with a code, use slot `Att_CodeLock` and `DigitalCodeLock`.
- A `CombinationLock` subclass handles storage version 143.
- Run the save checklist in `base-building-save-checklist.md` on any change to the masks or to `OnStoreSave`.
