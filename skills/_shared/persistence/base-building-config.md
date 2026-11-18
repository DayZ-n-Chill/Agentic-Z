# Base building config

Which config fields a buildable `BaseBuildingBase` object needs, and which vanilla code reads each one: the entity class, its slots, the `Construction` block, materials, tool masks and damage zones. The kit to base flow is in `base-building-lifecycle.md`; what the save does with the part `id` is in `base-building.md`.

The fields are read once per entity type: `ConstructionPartTypeData.InitPartTypeData` caches them (`P:\scripts\4_world\classes\basebuilding\typeconstructiondata\constructionparttyped.c:45` to `:70`), and each part instance keeps only its type data, built flag and sync bits. The key names are the same as on 1.29; 1.29 read them per instance (see `base-building-1-30.md`).

## The entity class

The parent class (`P:\DZ\gear\camping\config.cpp:25` to `:31`):

```cpp
class BaseBuildingBase: Inventory_Base { debug_ItemCategory=10; weight=100000; itemSize[]={50,50}; disallowSwapCollisions="true"; };
```

The vanilla `class Fence: BaseBuildingBase` (`config.cpp:3252` to `:3282`) sets `scope=2`, `model="\DZ\gear\camping\fence.p3d"`, `carveNavmesh=1` and `physLayer="item_large"`, plus `createProxyPhysicsOnInit="false"` and `createdProxiesOnInit[]={"Deployed"}`. The `Deployed` proxy is the base collision, switched by animation.

## Slots on the entity class

| Field | Meaning | Reader |
|---|---|---|
| `attachments[]` | every material and attachment slot the object accepts | `GetAttachmentSlots`, `P:\scripts\4_world\entities\itembase\basebuildingbase.c:846` to `:853`; declared at `config.cpp:4362` |
| `hybridAttachments[]` | attachments whose health mirrors the damage zone of the same name | read in the constructor (`basebuildingbase.c:53` to `:57`), checked by `CheckForHybridAttachments` (`:1120` to `:1130`); declared at `config.cpp:3270` |
| `mountables[]` | attachments whose proxy physics is switched on and off, such as barbed wire | read in the constructor (`basebuildingbase.c:58` to `:62`); `UpdateAttachmentPhysics` returns early for a slot not in the list (`:784` and `:785`); declared at `config.cpp:3277` |

## The Construction block

Two levels: `Construction`, then a main part, then a part. The vanilla Fence has `Construction`, `wall`, `base` (`config.cpp:4539` to `:4564`) and `wall`, `wall_base_down` (`:4565` to `:4597`).

| Field | Meaning | Reader |
|---|---|---|
| `name` | display name, a `$STR_` key | `InitBasicStrings`, `constructionparttyped.c:78` |
| `id` | the part's save and sync bit, unique, 1 to 93 | `constructionparttyped.c:83`; used by `RegisterPartForSync` (`basebuildingbase.c:136` to `:163`) |
| `is_base` | 1 marks the foundation; dismantling it destroys the whole object | `constructionparttyped.c:84`; destroy path at `basebuildingbase.c:614` to `:618` |
| `is_gate` | 1 marks a gate, as on the Fence | `constructionparttyped.c:85` |
| `required_parts[]` | parts that must be built first | `InitRequiredParts`, `constructionparttyped.c:88` to `:93`; checked by `HasRequiredPart` (`P:\scripts\4_world\classes\constructionbase.c:780` to `:793`) |
| `conflicted_parts[]` | parts that block this one once built | `constructionparttyped.c:141`; checked by `HasConflictPart` (`constructionbase.c:802` to `:826`) |
| `collision_data[]` | two memory point names, min and max, for the build collision box | `constructionparttyped.c:151` |
| `build_action_type` | bit mask matched against the tool's own `build_action_type` | `InitActionMasks`, `constructionparttyped.c:95` to `:107` |
| `dismantle_action_type` | the same, for dismantling | `constructionparttyped.c:104` |
| `material_type` | a `ConstructionMaterialType` value that picks the build and dismantle sounds | `constructionparttyped.c:132` |
| `essential_attachments[]` | slots whose attachment is unlocked and dropped when the part is dismantled or destroyed; the Fence's `wall_gate` lists `Att_CodeLock` and `Att_CombinationLock` (`config.cpp:4913` to `:4917`) | `constructionparttyped.c:220`; dropped by `DropEssentialAttachments` (`constructionbase.c:1440` to `:1482`) |

`show_on_init` still appears in old configs. No script on `P:\` reads it (a search of `P:\scripts` finds nothing), so leave it out.

### Material types

`ConstructionMaterialType` is `MATERIAL_NONE = 0`, `MATERIAL_LOG = 1`, `MATERIAL_WOOD = 2`, `MATERIAL_STAIRS = 3`, `MATERIAL_METAL = 4`, `MATERIAL_WIRE = 5`, `MATERIAL_BRICK = 6`, `MATERIAL_RUBBLE = 7` (`constructionbase.c:2` to `:12`). The sound switch on `BaseBuildingBase` handles only log, wood, stairs, metal and wire (`GetBuildSoundByMaterial`, `basebuildingbase.c:1087` to `:1101`; `GetDismantleSoundByMaterial` at `:1103` to `:1117` is the same), so a brick or rubble part plays no build sound from it.

### Materials

Each `Material1`, `Material2` and so on under a part fills one `ConstructionMaterialData` record (`P:\scripts\4_world\classes\basebuilding\constructionmaterials.c:2`), and its `Init` reads the keys (`:26` to `:32`):

| Field | Meaning |
|---|---|
| `type` | item class, used to spawn piles when the part is dismantled |
| `slot_name` | the slot the material sits in; the build needs an attachment there with enough quantity (`HasMaterialsEx`, `constructionbase.c:1186` to `:1224`) |
| `quantity` | amount used; `-1` deletes the whole material item in the slot (not the buildable object) and `0` ignores the quantity (`TakeMaterialsServer`, `constructionbase.c:1267` to `:1281`; the material check skips a `0` at `:1205`) |
| `lockable` | `1` locks the material in its slot, where it stays as part of the wall, instead of using it up (`TakeMaterialsServer`, `constructionbase.c:1244` to `:1284`, the lock at `:1257` to `:1264`) |
| `skipOnRepair`, `skipOnDismantle` | not needed to repair, or not refunded on dismantle (`constructionmaterials.c:31` and `:32`) |

A part with no `Materials` block needs no material.

## Inventory categories

`GUIInventoryAttachmentsProps` (`config.cpp:4375` to `:4417`) groups the slots into inventory categories (Base, Attachments, Material). Each child has `attachmentSlots[]`, `selection` (the model selection the category maps to), `icon` and `name`. `GetAttachmentSlotFromSelection` and `GetAttachmentsFromSelection` read it to find the slot an attach action targets (`P:\scripts\4_world\classes\basebuilding\constructionactiondata.c:469` and `:499`). No script on `P:\` reads a `platform_support` key; `DropNonUsableMaterialsServer` (`constructionbase.c:1326` to `:1378`) works only on locked materials of the base part.

## Tool masks

A tool joins in by declaring `build_action_type` and `dismantle_action_type` in its own `CfgVehicles` class. `CanUseToolToBuildPart` reads the tool's `build_action_type` and allows the build when it shares a bit with the part's mask (`constructionbase.c:1506` to `:1543`). With no tool in hand, only a part whose mask has `TOOL_HANDS` can be built (`:1536` to `:1539`); a tool with no `build_action_type` key builds nothing. The bits are `EConstructionTools` (`P:\scripts\4_world\classes\basebuilding\constructionconstants.c:14` to `:26`), which must match the config values:

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

Shovel, Pickaxe, Pliers and SledgeHammer also switch the player's animation, and `BrickTrowel` uses `CMD_ACTIONFB_BRICKTROWEL` (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionbuildpart.c:246` to `:262`).

## Damage zones and part names

The object declares a `DamageSystem` with `GlobalHealth` and `DamageZones` (`config.cpp:3283`, zones from `:3353`). Name each damage zone exactly as its part, in lower case: `OnHealthLevelChanged` lowers the zone name, looks the part up by it and destroys the part when the zone is ruined and the part is built (`constructionbase.c:410` to `:426`). A zone that matches no part never destroys anything.

## Model names the readers assume

- The base uses the `Deployed` proxy; every other part gets its own through `AddProxyPhysics(GetPartName())` (`HandleAddPhysics`, `P:\scripts\4_world\classes\basebuilding\constructionpart.c:422` to `:425`). A missing memory point or selection gives a part with no collision.
- A part is shown with `SetAnimationPhase(part_name, 0)` and hidden with phase 1 (`PerformShowAnim` and `PerformHideAnim`, `constructionpart.c:474` to `:483`). Every part name must be an animation source in config and a selection in the `.p3d`.

## Build collision

Collision for a build goes through `IsCollidingEx(CollisionCheckData)` (`constructionbase.c:1591`). Fill `m_PartName` and, if needed, `m_AdditionalExcludes`; vanilla adds the player (`actionbuildpart.c:157` to `:160`). `CreateCollisionTrigger`, `DestroyCollisionTrigger` and `IsTriggerColliding` are `[Obsolete("no replacement")]` (`constructionbase.c:2400` to `:2445`); do not call them from new code.

`UpdateConstructionParts` (`constructionbase.c:575` to `:606`) does not walk the config children. It iterates `ConstructionDataTypeHolder.GetConstructionPartTypeDataArray()` (`P:\scripts\4_world\classes\basebuilding\typeconstructiondata\constructionparttypedholder.c:115`), which `InitPartsTypeDataHolder` fills (`:10` to `:63`).

Keys meant for rebuildable map buildings, such as `custom_part_type`, `can_decay_general`, `can_part_decay` and `StaticsSupportData`, are listed in `base-building-rebuildable.md`, section "Config keys the rebuild parts read". The vanilla Fence uses none of them, and a player built object can ignore them.
