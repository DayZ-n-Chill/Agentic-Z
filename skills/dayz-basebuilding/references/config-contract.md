# Config contract: declaring a buildable BaseBuildingBase entity

Every config field a buildable object needs, with the vanilla code that reads it. Open this when writing or reviewing a `Construction` class, its materials, its tool masks or its damage zones.

Line numbers are from the vanilla scripts and configs on `P:\` (game storage version 144). A citation marked `1.29` points at the 1.29 scripts, which are not on `P:\`; those lines were not checked there and are kept as a map for older mods.

Since 1.30 the fields are read once per entity type: `ConstructionPartTypeData.InitPartTypeData` caches them (`P:\scripts\4_world\classes\basebuilding\typeconstructiondata\constructionparttyped.c:45-70`), and each `ConstructionPart` instance only holds `m_PartTypeData` plus its built and sync state. Until 1.29 every instance re-read the config through `g_Game.ConfigGet*`. The field names in the `Construction` block did not change.

## 1. The entity class

Base class (`P:\DZ\gear\camping\config.cpp:25-31`):

```cpp
class BaseBuildingBase: Inventory_Base { weight=100000; itemSize[]={50,50}; disallowSwapCollisions="true"; };
```

A concrete entity, for example `class Fence: BaseBuildingBase` (`P:\DZ\gear\camping\config.cpp:3252-3282`):

- `scope=2; model="\DZ\gear\camping\fence.p3d"; carveNavmesh=1; physLayer="item_large";`
- `createProxyPhysicsOnInit="false";` plus `createdProxiesOnInit[]={"Deployed"};`. The `Deployed` proxy is the base collision, toggled by animation (see `entity-lifecycle.md`).

## 2. Attachment and material slots on the entity class

| Field | Meaning | Reader |
|---|---|---|
| `attachments[]` | every material and attachment slot the entity accepts | `GetAttachmentSlots()` reads `CfgVehicles <type> attachments`, `P:\scripts\4_world\entities\itembase\basebuildingbase.c:847-854`; declared `config.cpp:4362` |
| `hybridAttachments[]` | attachments whose health mirrors a damage zone of the same name | `CheckForHybridAttachments` `basebuildingbase.c:1121-1131`; read in the constructor `:53-57`; declared `config.cpp:3270` |
| `mountables[]` | attachments that get proxy physics toggled (barbed wire) | read in the constructor `basebuildingbase.c:58-62`; `UpdateAttachmentPhysics` returns early if a slot is not in `mountables` `:785-786`; declared `config.cpp:3277` |

## 3. The `Construction` block, field by field

Two levels of nesting: `Construction { class <main_part> { class <part> {...} } }`. Example `Construction > wall > base` (`config.cpp:4529-4554`) and `wall > wall_base_down` (`:4555-4587`).

| Field | Type and meaning | Reader on `P:\` | 1.29 reader |
|---|---|---|---|
| `name` | localized display name (`$STR_...`) | `InitBasicStrings` `constructionparttyped.c:78` | `UpdateConstructionParts` 1.29 `construction.c:256-264` |
| `id` | unique sync and save bit index, 1 to 93 | `constructionparttyped.c:83`; used by `RegisterPartForSync` `basebuildingbase.c:137-164` | same 1.29 reader |
| `is_base` | 1 = foundation part; dismantling it destroys the whole entity | `constructionparttyped.c:84`; destroy path `basebuildingbase.c:615-619` | 1.29 `construction.c:256-264` |
| `is_gate` | 1 = this part is a gate (Fence) | `constructionparttyped.c:85` | 1.29 `construction.c:256-264` |
| `show_on_init` | read by the 1.29 reader with no observed effect on the show and hide paths. No script on `P:\` reads it any more (a search of `P:\scripts\4_world` for `show_on_init` finds nothing). | none | 1.29 `construction.c:256-264` |
| `required_parts[]` | parts that must be built first | `InitRequiredParts` `constructionparttyped.c:88-93`; checked by `HasRequiredPart` `P:\scripts\4_world\classes\constructionbase.c:682-695` | `HasRequiredPart` 1.29 `construction.c:415-418,546-553` |
| `conflicted_parts[]` | parts that block this one if already built | `constructionparttyped.c:141`; checked by `HasConflictPart` `constructionbase.c:704-726` | `HasConflictPart` 1.29 `construction.c:441-443` |
| `collision_data[]` | two memory point names `{min, max}` for the build collision box | `constructionparttyped.c:151` | 1.29 `construction.c:1128-1141` |
| `build_action_type` | bitmask AND-matched against the tool's own `build_action_type` | `InitActionMasks` `constructionparttyped.c:95-107` | 1.29 `construction.c:959,966-1003` |
| `dismantle_action_type` | same, for dismantle | `constructionparttyped.c:104` | 1.29 `construction.c:989` |
| `material_type` | `ConstructionMaterialType` value; picks the build and dismantle sounds | `constructionparttyped.c:132` | 1.29 `construction.c:1005-1015` |

### `ConstructionMaterialType` enum

On `P:\` the enum is `MATERIAL_NONE = 0`, `MATERIAL_LOG = 1`, `MATERIAL_WOOD = 2`, `MATERIAL_STAIRS = 3`, `MATERIAL_METAL = 4`, `MATERIAL_WIRE = 5`, `MATERIAL_BRICK = 6`, `MATERIAL_RUBBLE = 7` (`constructionbase.c:2-12`). Until 1.29 it sat at the top of 1.29 `construction.c:1-9` with the first six values only. The sound switch on `BaseBuildingBase` still handles only log, wood, stairs, metal and wire (`GetBuildSoundByMaterial`, `basebuildingbase.c:1088-1102`).

### `Materials` sub-block

Each `Material1..N` child under a part fills one material record, `m_MaterialType`, `m_MaterialSlotName`, `m_MaterialQuantity` and `m_MaterialLockable` (`P:\scripts\4_world\classes\basebuilding\constructionmaterials.c:26-32`; 1.29 `construction.c:632-693,758-766`):

| Field | Meaning |
|---|---|
| `type` | item class name, used when refunding piles on dismantle |
| `slot_name` | attachment slot the material sits in; `HasMaterials` needs the attachment there with enough quantity (`HasMaterialsEx`, `constructionbase.c:1081-1119`; 1.29 `construction.c:617-655`) |
| `quantity` | amount consumed; `-1` deletes the whole material item in the slot (not the buildable) and `0` ignores the quantity (`TakeMaterialsServer`, `constructionbase.c:1162-1176`; the material check skips a `0` at `:1100`) |
| `lockable` | `1` locks the material in its slot (it stays attached and becomes part of the wall) instead of consuming it (`TakeMaterialsServer`, `constructionbase.c:1139-1179`; 1.29 `construction.c:671-723`) |
| `skipOnRepair`, `skipOnDismantle` | since 1.30: the material is not needed to repair, or not refunded on dismantle (`constructionmaterials.c:31-32`) |

If the `Materials` block is absent, `HasMaterials` returns true (no material needed).

## 4. `GUIInventoryAttachmentsProps` (`config.cpp:4375-4417`)

Groups attachment slots into inventory categories (Base, Attachments, Material). Each child has `attachmentSlots[]`, `selection` (the model selection the category maps to), `icon` and `name`. `GetAttachmentSlotFromSelection` and `GetAttachmentsFromSelection` read it to find which slot an attach action targets (`P:\scripts\4_world\classes\basebuilding\constructionactiondata.c:469` and `:499`; 1.29 `constructionactiondata.c:250-336`). On 1.29 `DropNonUsableMaterialsServer` also read a `platform_support` key (1.29 `construction.c:788-908`); no script on `P:\` reads `platform_support`, and the current method is at `constructionbase.c:1221-1276`.

## 5. Tool contract

A tool takes part by declaring `build_action_type` and `dismantle_action_type` in its own `CfgVehicles` entry. `CanUseToolToBuildPart` reads `cfgVehicles <tool type> build_action_type` and allows the build when the part mask and the tool mask share a bit (`constructionbase.c:1404-1441`; 1.29 `construction.c:966,989`). The part masks are `EConstructionTools`, which must mirror the config values and includes `TOOL_BRICKLAYING = 256` since 1.30 (`P:\scripts\4_world\classes\basebuilding\constructionconstants.c:14-26`). Shovel, Pickaxe, Pliers and SledgeHammer also switch the player animation command, and `BrickTrowel` uses `CMD_ACTIONFB_BRICKTROWEL` (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionbuildpart.c:248-262`; 1.29 `actionbuildpart.c:161-181`).

## 6. Damage zones and part names

The entity declares `class DamageSystem { class GlobalHealth ...; class DamageZones {...} }` (`config.cpp:3283`, zones from `:3353`). A damage zone name must equal the part name in lower case: `OnHealthLevelChanged` lowers the zone name and looks the part up by it, then destroys the part when the zone is ruined (`constructionbase.c:352-368`; 1.29 `basebuildingbase.c:507-517`). A zone whose name matches no part never destroys anything.

## 7. What the readers assume (check before shipping)

- The base uses the `"Deployed"` proxy; every other part gets its own proxy through `AddProxyPhysics(GetPartName())` (`HandleAddPhysics`, `P:\scripts\4_world\classes\basebuilding\constructionpart.c:422-425`; 1.29 `construction.c:591-599`). A missing memory point or selection gives a part with no collision.
- Showing or hiding a part is `SetAnimationPhase(part_name, 0)` or `(part_name, 1)`; phase 0 is visible (`PerformShowAnim` and `PerformHideAnim`, `constructionpart.c:474-483`). Every part name must be an AnimationSource in config and a selection in the `.p3d`.

## 8. DayZ 1.30: type cache, `IsCollidingEx`, obsolete trigger API

`CreateCollisionTrigger`, `DestroyCollisionTrigger` and `IsTriggerColliding` still exist on `ConstructionBase`, tagged `[Obsolete("no replacement")]` (`constructionbase.c:1756-1801`). Do not call them from new code.

Collision for a build now goes through `IsCollidingEx(CollisionCheckData)` (`constructionbase.c:1481`). Fill `m_PartName` and, if needed, `m_AdditionalExcludes`; vanilla inserts the player (`actionbuildpart.c:157-160`).

`UpdateConstructionParts` (`constructionbase.c:517-548`) no longer walks the config children. It iterates `ConstructionDataTypeHolder.GetConstructionPartTypeDataArray()` (`P:\scripts\4_world\classes\basebuilding\typeconstructiondata\constructionparttypedholder.c:115`), which `InitPartsTypeDataHolder` fills (`:10-63`).

New optional keys read by the type data (meant for rebuildable map buildings, unused by the vanilla Fence): `custom_part_type` (`constructionparttypedholder.c:35`), `can_decay_general` on the `Construction` class (`:54-55`), `can_part_decay` on a part (`constructionparttyped.c:202`) and `StaticsSupportData`. The full list is in `dayz-1-30-construction-rebuilding.md`, section 9.2. Design note: a player-built `BaseBuildingBase` can ignore them unless you are authoring a rebuildable `BuildingBase`.
