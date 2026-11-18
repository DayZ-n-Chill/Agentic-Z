# Base building config

Which config fields a buildable `BaseBuildingBase` object needs, and which vanilla code reads each one: the entity class, its slots, the `Construction` block, materials, tool masks and damage zones. The kit to base flow is in `base-building-lifecycle.md`; what the save does with the part `id` is in `base-building.md`.

The fields are read once per entity type: `ConstructionPartTypeData.InitPartTypeData` caches them (`P:\scripts\4_world\classes\basebuilding\typeconstructiondata\constructionparttyped.c:45` to `:70`), and each part instance keeps only its type data, built flag and sync bits. The key names are the same as on 1.29; 1.29 read them per instance (see `base-building-1-30.md`).

## The entity class

The parent class (`P:\DZ\gear\camping\config.cpp:25` to `:31`):

```cpp
class BaseBuildingBase: Inventory_Base { weight=100000; itemSize[]={50,50}; disallowSwapCollisions="true"; };
```

The vanilla `class Fence: BaseBuildingBase` (`config.cpp:3252` to `:3282`) sets `scope=2`, `model="\DZ\gear\camping\fence.p3d"`, `carveNavmesh=1` and `physLayer="item_large"`, plus `createProxyPhysicsOnInit="false"` and `createdProxiesOnInit[]={"Deployed"}`. The `Deployed` proxy is the base collision, switched by animation.

## Slots on the entity class

| Field | Meaning | Reader |
|---|---|---|
| `attachments[]` | every material and attachment slot the object accepts | `GetAttachmentSlots`, `P:\scripts\4_world\entities\itembase\basebuildingbase.c:847` to `:854`; declared at `config.cpp:4362` |
| `hybridAttachments[]` | attachments whose health mirrors the damage zone of the same name | read in the constructor (`basebuildingbase.c:53` to `:57`), checked by `CheckForHybridAttachments` (`:1121` to `:1131`); declared at `config.cpp:3270` |
| `mountables[]` | attachments whose proxy physics is switched on and off, such as barbed wire | read in the constructor (`basebuildingbase.c:58` to `:62`); `UpdateAttachmentPhysics` returns early for a slot not in the list (`:785` and `:786`); declared at `config.cpp:3277` |

## The Construction block

Two levels: `Construction`, then a main part, then a part. The vanilla Fence has `Construction`, `wall`, `base` (`config.cpp:4529` to `:4554`) and `wall`, `wall_base_down` (`:4555` to `:4587`).

| Field | Meaning | Reader |
|---|---|---|
| `name` | display name, a `$STR_` key | `InitBasicStrings`, `constructionparttyped.c:78` |
| `id` | the part's save and sync bit, unique, 1 to 93 | `constructionparttyped.c:83`; used by `RegisterPartForSync` (`basebuildingbase.c:137` to `:164`) |
| `is_base` | 1 marks the foundation; dismantling it destroys the whole object | `constructionparttyped.c:84`; destroy path at `basebuildingbase.c:615` to `:619` |
| `is_gate` | 1 marks a gate, as on the Fence | `constructionparttyped.c:85` |
| `required_parts[]` | parts that must be built first | `InitRequiredParts`, `constructionparttyped.c:88` to `:93`; checked by `HasRequiredPart` (`P:\scripts\4_world\classes\constructionbase.c:780` to `:793`) |
| `conflicted_parts[]` | parts that block this one once built | `constructionparttyped.c:141`; checked by `HasConflictPart` (`constructionbase.c:704` to `:726`) |
| `collision_data[]` | two memory point names, min and max, for the build collision box | `constructionparttyped.c:151` |
| `build_action_type` | bit mask matched against the tool's own `build_action_type` | `InitActionMasks`, `constructionparttyped.c:95` to `:107` |
| `dismantle_action_type` | the same, for dismantling | `constructionparttyped.c:104` |
| `material_type` | a `ConstructionMaterialType` value that picks the build and dismantle sounds | `constructionparttyped.c:132` |

`show_on_init` still appears in old configs. No script on `P:\` reads it (a search of `P:\scripts\4_world` finds nothing), so leave it out.

On 1.29 the same keys were read per instance in `construction.c`. `UpdateConstructionParts` (1.29 `construction.c:256` to `:264`) read `name`, `id`, `is_base`, `is_gate` and `show_on_init`; `show_on_init` had no seen effect on the show and hide paths even then. `HasRequiredPart` was at `:415` to `:418` and `:546` to `:553`, `HasConflictPart` at `:441` to `:443`, the `collision_data[]` reader at `:1128` to `:1141`, the `build_action_type` check at `:959` and `:966` to `:1003`, the `dismantle_action_type` read at `:989`, and the `material_type` read at `:1005` to `:1015`.

### Material types

`ConstructionMaterialType` is `MATERIAL_NONE = 0`, `MATERIAL_LOG = 1`, `MATERIAL_WOOD = 2`, `MATERIAL_STAIRS = 3`, `MATERIAL_METAL = 4`, `MATERIAL_WIRE = 5`, `MATERIAL_BRICK = 6`, `MATERIAL_RUBBLE = 7` (`constructionbase.c:2` to `:12`). The sound switch on `BaseBuildingBase` handles only log, wood, stairs, metal and wire (`GetBuildSoundByMaterial`, `basebuildingbase.c:1088` to `:1102`), so a brick or rubble part plays no build sound from it.

### Materials

Each `Material1`, `Material2` and so on under a part fills one `ConstructionMaterialData` record (`P:\scripts\4_world\classes\basebuilding\constructionmaterials.c:2`), and its `Init` reads the keys (`:26` to `:32`):

| Field | Meaning |
|---|---|
| `type` | item class, used to spawn piles when the part is dismantled |
| `slot_name` | the slot the material sits in; the build needs an attachment there with enough quantity (`HasMaterialsEx`, `constructionbase.c:1081` to `:1119`) |
| `quantity` | amount used; `-1` deletes the whole material item in the slot (not the buildable object) and `0` ignores the quantity (`TakeMaterialsServer`, `constructionbase.c:1162` to `:1176`; the material check skips a `0` at `:1100`) |
| `lockable` | `1` locks the material in its slot, where it stays as part of the wall, instead of using it up (`TakeMaterialsServer`, `constructionbase.c:1139` to `:1179`) |
| `skipOnRepair`, `skipOnDismantle` | not needed to repair, or not refunded on dismantle (`constructionmaterials.c:31` and `:32`) |

A part with no `Materials` block needs no material.

## Inventory categories

`GUIInventoryAttachmentsProps` (`config.cpp:4375` to `:4417`) groups the slots into inventory categories (Base, Attachments, Material). Each child has `attachmentSlots[]`, `selection` (the model selection the category maps to), `icon` and `name`. `GetAttachmentSlotFromSelection` and `GetAttachmentsFromSelection` read it to find the slot an attach action targets (`P:\scripts\4_world\classes\basebuilding\constructionactiondata.c:469` and `:499`; on 1.29 `constructionactiondata.c:250` to `:336`). On 1.29 `DropNonUsableMaterialsServer` also read a `platform_support` key (1.29 `construction.c:788` to `:908`). No script on `P:\` reads it now; `DropNonUsableMaterialsServer` is at `constructionbase.c:1221` to `:1276`.

## Tool masks

A tool joins in by declaring `build_action_type` and `dismantle_action_type` in its own `CfgVehicles` class. `CanUseToolToBuildPart` reads the tool's `build_action_type` and allows the build when it shares a bit with the part's mask (`constructionbase.c:1404` to `:1441`; on 1.29 `construction.c:966` for build and `:989` for dismantle). The bits are `EConstructionTools` (`P:\scripts\4_world\classes\basebuilding\constructionconstants.c:14` to `:26`), which must match the config values:

| Bit | Name |
|---|---|
| 1 | `TOOL_MOUNT_WIRE` |
| 2 | `TOOL_NAIL` |
| 4 | `TOOL_DIG_BASE` |
| 8 | `TOOL_MOUNT_LOG` |
| 16 | `TOOL_HEAVY` |
| 32 | `TOOL_EXCAVATION` |
| 64 | `TOOL_WOODWORK` |
| 128 | `TOOL_HANDS` |
| 256 | `TOOL_BRICKLAYING`, new in 1.30 |

Shovel, Pickaxe, Pliers and SledgeHammer also switch the player's animation, and `BrickTrowel` uses `CMD_ACTIONFB_BRICKTROWEL` (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionbuildpart.c:248` to `:262`; on 1.29 `actionbuildpart.c:161` to `:181`).

## Damage zones and part names

The object declares a `DamageSystem` with `GlobalHealth` and `DamageZones` (`config.cpp:3283`, zones from `:3353`). Name each damage zone exactly as its part, in lower case: `OnHealthLevelChanged` lowers the zone name, looks the part up by it and destroys the part when the zone is ruined (`constructionbase.c:352` to `:368`). A zone that matches no part never destroys anything.

## Model names the readers assume

- The base uses the `Deployed` proxy; every other part gets its own through `AddProxyPhysics(GetPartName())` (`HandleAddPhysics`, `P:\scripts\4_world\classes\basebuilding\constructionpart.c:422` to `:425`). A missing memory point or selection gives a part with no collision.
- A part is shown with `SetAnimationPhase(part_name, 0)` and hidden with phase 1 (`PerformShowAnim` and `PerformHideAnim`, `constructionpart.c:474` to `:483`). Every part name must be an animation source in config and a selection in the `.p3d`.

## Build collision

Collision for a build goes through `IsCollidingEx(CollisionCheckData)` (`constructionbase.c:1481`). Fill `m_PartName` and, if needed, `m_AdditionalExcludes`; vanilla adds the player (`actionbuildpart.c:157` to `:160`). `CreateCollisionTrigger`, `DestroyCollisionTrigger` and `IsTriggerColliding` are `[Obsolete("no replacement")]` (`constructionbase.c:1756` to `:1801`); do not call them from new code.

`UpdateConstructionParts` (`constructionbase.c:517` to `:548`) does not walk the config children. It iterates `ConstructionDataTypeHolder.GetConstructionPartTypeDataArray()` (`P:\scripts\4_world\classes\basebuilding\typeconstructiondata\constructionparttypedholder.c:115`), which `InitPartsTypeDataHolder` fills (`:10` to `:63`).

Keys meant for rebuildable map buildings, such as `custom_part_type`, `can_decay_general`, `can_part_decay` and `StaticsSupportData`, are listed in `base-building-rebuildable.md`, section "Config keys the rebuild parts read". The vanilla Fence uses none of them, and a player built object can ignore them.
