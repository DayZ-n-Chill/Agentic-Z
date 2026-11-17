---
name: dayz-basebuilding
description: "Reference for writing, extending and debugging DayZ buildable structures on BaseBuildingBase: fences, watchtowers, gates, walls, shelters, flag poles and barbed wire. Covers the kit, deploy and hologram flow, the Construction config block, build, dismantle and destroy actions, the bit mask save, damage zones, the Fence gate and the 1.30 changes (ConstructionBase, Rebuilding, BuildPartServerEx, bricks and mortar, the fence code lock). Use when a base won't save, parts reset or vanish after a restart, a construction part or build action is missing, dismantle is blocked, a part has no collision, or the hologram won't place. Spanish triggers: la base no se guarda, las partes desaparecen tras reiniciar, construcción de bases."
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-basebuilding

Reference only: this skill has no script. It holds what a worker needs to build on the vanilla base building system instead of writing its own. A buildable structure extends the `BaseBuildingBase` chain, not `EntityAI`, and so inherits the build, dismantle and destroy actions, the bit mask save, the hologram deploy flow and damage that destroys parts. You author a `.p3d` with the right selections and memory points, and a `Construction` config block that declares each part.

Follow `skills/_shared/dayz-conventions.md`. Writing config offline needs nothing; packing and testing go through `/dayz-build-pbo` and `/dayz-launch-test`, which run `/dayz-preflight` themselves.

Line numbers are from the vanilla scripts and configs on `P:\` (game storage version 144, `GAME_STORAGE_VERSION` at `P:\scripts\3_game\global\game.c:5`). Class and field names in this area are easy to half remember: before writing one, find it in `P:\scripts\4_world\` or in `P:\DZ\gear\camping\config.cpp`.

## Which file answers which question

Deep material lives in `<skill-dir>\references\`. Open only the file the task needs.

| Question | File |
|---|---|
| Which config fields does a buildable object need, and which code reads each one? Tool masks, materials, damage zones. | `references/config-contract.md` |
| What is the exact call chain from crafting the kit to a base that survives a restart? Which hook do I override? | `references/entity-lifecycle.md` |
| How does the vanilla Fence add a gate, a lock, barbed wire damage and extra saved fields? | `references/fence-gate-case.md` |
| How are parts saved, what is the 93 part cap, and what must be checked before a save change ships? | `references/persistence-audit.md` |
| What did 1.30 change (class hierarchy, `*ServerEx`, Rebuilding on map buildings, masonry, code lock), and how do I port a 1.29 mod? | `references/dayz-1-30-construction-rebuilding.md` |
| Why does the build action never appear, why is the hologram not tinted, why is my item carried in one hand, how do I place on a wall? | `references/placement-and-materials.md` |

The pack file `skills/_shared/persistence/base-building.md` holds the short version of the save rules for workers that only touch `OnStoreSave`.

## The model

| Class | Role | Where |
|---|---|---|
| `BaseBuildingBase` | the saved world entity; owns the construction component, the sync ints, events, physics and area damage | `P:\scripts\4_world\entities\itembase\basebuildingbase.c:2` |
| `ConstructionBasic` | stub in `3_Game`; `EntityAI` creates the component through `CreateConstructionComponent()` | `P:\scripts\3_game\systems\construction_basic.c:2`; `P:\scripts\3_game\entities\entityai.c:3474` |
| `ConstructionBase` | shared controller since 1.30: `BuildPartServerEx`, `DismantlePartServerEx`, `IsCollidingEx` | `P:\scripts\4_world\classes\constructionbase.c:30`, `:179`, `:190`, `:1481` |
| `Construction` | the controller a `BaseBuildingBase` gets | `P:\scripts\4_world\classes\basebuilding\construction.c:2` |
| `Rebuilding` | the controller a map building (`BuildingBase`) gets; ten sync ints, its own save | `P:\scripts\4_world\classes\rebuilding\rebuilding.c:1`; created at `P:\scripts\4_world\entities\game\super\building.c:23-27` |
| `ConstructionPartTypeData` | the `Construction` config fields, cached once per entity type | `P:\scripts\4_world\classes\basebuilding\typeconstructiondata\constructionparttyped.c:2` |
| `ConstructionPart` | one part's changing state (built or not, sync bits) | `P:\scripts\4_world\classes\basebuilding\constructionpart.c:3` |
| `ConstructionActionData` | per player scratch data: which parts can be built under the cursor, action variants | `P:\scripts\4_world\classes\basebuilding\constructionactiondata.c:1` |

The controller is not saved. It is rebuilt from config on every load and its part states come back from the sync bit masks.

The flow, with the hooks in `references/entity-lifecycle.md`:

1. **Craft the kit.** A recipe gives a `KitBase` item (`P:\scripts\4_world\entities\itembase\kitbase.c:1`).
2. **Deploy.** The kit adds `ActionTogglePlaceObject` and `ActionDeployObject` (`kitbase.c:146-152`). On finish the server creates the real entity with no parts shown (`FenceKit.OnPlacementComplete`, `P:\scripts\4_world\entities\itembase\fencekit.c:19-34`).
3. **Base part.** The player attaches the base material and builds the part with `is_base=1`. That sets the base state and spawns a construction kit back (`OnPartBuiltServer`, `basebuildingbase.c:554-560`).
4. **Build a part.** `ActionBuildPart` with a tool calls `BuildPartServerEx` on the server (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionbuildpart.c:170`). Override `BuildPartServerEx`; `BuildPartServer` is an obsolete wrapper (`constructionbase.c:1702-1708`).
5. **Upgrade.** Further parts become buildable when their `required_parts[]` are built and none of their `conflicted_parts[]` is (`HasRequiredPart`, `constructionbase.c:682-695`; `HasConflictPart`, `:711-726`).
6. **Dismantle.** Refunds materials; blocked while another built part depends on this one (`HasDependentPart`, `constructionbase.c:772-783`). Dismantling the base destroys the whole object (`basebuildingbase.c:615-619`).
7. **Fold.** With no base and no attachments the object folds back into a kit (`CanFoldBaseBuildingObject`, `basebuildingbase.c:962-970`).

## The `Construction` block

Two levels: main part, then part. This is the vanilla Fence foundation (`P:\DZ\gear\camping\config.cpp:4529-4554`); every field and its reader is in `references/config-contract.md`.

```cpp
class Construction
{
    class wall                              // main part
    {
        class base                          // part: the config class name is also the p3d selection
        {
            name="$STR_CfgVehicles_Construction_Part_Base";
            is_base=1;                      // foundation; dismantling it destroys the object
            id=1;                           // unique save and sync bit, 1 to 93
            required_parts[]={};            // parts that must be built first
            conflicted_parts[]={};          // parts that block this one
            collision_data[]={};            // {min memory point, max memory point} of the build collision box
            build_action_type=4;            // bit mask matched against the tool's build_action_type
            dismantle_action_type=4;
            material_type=1;                // picks the build and dismantle sounds
            class Materials
            {
                class Material1
                {
                    type="WoodenLog";       // item class, used when refunding
                    slot_name="Material_WoodenLogs";
                    quantity=2;             // -1 deletes the whole object, 0 ignores the quantity
                    lockable=1;             // lock the material in its slot instead of consuming it
                };
            };
        };
    };
};
```

The entity class also declares `attachments[]`, `hybridAttachments[]`, `mountables[]` and a `DamageSystem` with one damage zone per part.

## Rules that corrupt data silently when broken

Check every one before calling a buildable object done.

- **Each part `id` is unique and between 1 and 93.** The id is a bit position in three sync ints (`RegisterPartForSync`, `basebuildingbase.c:137-164`). A duplicate makes two parts toggle together; an id outside the range is never saved. Rebuildable map buildings use a different packing (ten ints, two bits per part, `rebuilding.c:7-16`); do not mix the two.
- **A damage zone name equals its part name in lower case.** The zone name is lowered and used to look the part up (`OnHealthLevelChanged`, `constructionbase.c:352-368`). With a mismatch, damage never destroys the part.
- **Save and load order is fixed.** `OnStoreSave` writes `m_SyncParts01`, `m_SyncParts02`, `m_SyncParts03`, then `m_HasBase` (`basebuildingbase.c:420-430`), and `OnStoreLoad` reads them in that order (`:432-464`). A subclass writes and reads its own fields after `super`, in the same order both ways, as the Fence does (`P:\scripts\4_world\entities\itembase\basebuildingbase\fence.c:246-254` and `:256-289`).
- **Every part name is an animation source in config and a selection in the `.p3d`.** Showing a part is `SetAnimationPhase(part_name, 0)` (`PerformShowAnim`, `constructionpart.c:474-477`). A missing selection gives a part that builds with no visual or no collision.
- **`OpenFence()` does not check the lock.** `CanOpenFence()` requires `HasHinges() && !IsOpened() && !IsLocked()` (`fence.c:472-478`); `OpenFence()` skips that and opens (`fence.c:488-506`). A script that opens a fence calls `CanOpenFence()` first. `IsLocked()` covers a closed `CombinationLock` and, since 1.30, a locked `DigitalCodeLock` (`fence.c:127-142`).
- **Action ids.** `AT_BUILD_PART = 193`, `AT_DISMANTLE_PART = 195`, `AT_DESTROY_PART = 209` (`P:\scripts\4_world\classes\useractionscomponent\_constants.c:6-8`) are passed to the `*ServerEx` methods and synced so clients play the right sound.
- **A slot's `stackMax` decides how much material fits, not the item's `varQuantityMax`.** A recipe that asks for more than the slot holds can never be built. Details and the hologram, carry pose and wall placement traps are in `references/placement-and-materials.md`.

## Saving is data-critical

Built state is not stored per part. It is packed into `m_SyncParts01`, `m_SyncParts02` and `m_SyncParts03` (`basebuildingbase.c:10-12`), which are both the network sync and the save format. After load, `SetPartFromSyncData` rebuilds each part from the bits and locks attached materials again as a failsafe (`basebuildingbase.c:265-304`).

Any change that adds parts, changes ids, or touches `OnStoreSave` or `OnStoreLoad` on a buildable object can lose every base on a server. Before it ships, `dayz-persistence-specialist` runs the checklist in `references/persistence-audit.md` and the audit in the `rigorous-data-audit` skill. Since 1.30 a `CombinationLock` also saves `m_CombinationInside`, read only from storage version 143 (`P:\scripts\4_world\entities\itembase\combinationlock.c:169-177`); a lock subclass that reads the old two values desyncs.

## Quick triage

| Symptom | Likely cause | Where |
|---|---|---|
| Base won't save, or parts reset on restart | save and load order differ, or a subclass wrote before `super` | `references/persistence-audit.md` |
| A built part doesn't show | the part name is not an animation source, or not a selection in the `.p3d` | `references/config-contract.md`, section 7 |
| A built part has no collision | missing proxy selection for the part, or the base lacks the `Deployed` proxy | `/dayz-p3d-audit`; `references/config-contract.md`, section 7 |
| Two parts toggle together | duplicate or out of range `id` | `RegisterPartForSync`, `basebuildingbase.c:137-164` |
| Damage never destroys a part | damage zone name differs from the lower case part name | `constructionbase.c:352-368` |
| The build action never appears | the tool's `build_action_type` shares no bit with the part's, `CanBuildPart` fails, or the recipe exceeds the slot's `stackMax` | `CanBuildPartEx`, `constructionbase.c:590-610`; `CanUseToolToBuildPart`, `:1404-1441`; `references/placement-and-materials.md` |
| Dismantle is blocked | another built part depends on this one | `HasDependentPart`, `constructionbase.c:772-783` |
| Built but not shown until sync, single player | `SetRequestBuiltState` only sets the state in multiplayer; it is obsolete, use `SetBuiltState` | `constructionpart.c:504-512` |
| The hologram won't confirm | the height check or the collision check fails | `actiondeployobject.c`, see `references/entity-lifecycle.md`, section 1 |
| Hitch when building | `UpdatePhysics()` is "a massive performance hit" by its own comment | `basebuildingbase.c:745` |
| An override of `BuildPartServer` never runs | vanilla calls `BuildPartServerEx` since 1.30 | `actionbuildpart.c:170` |
| Code uses `CreateCollisionTrigger` | still compiles but is `[Obsolete("no replacement")]`; use `IsCollidingEx(CollisionCheckData)` | `constructionbase.c:1481`, `:1756-1757` |
| A rebuilt house or well part resets | the three int `BaseBuildingBase` save was mixed with the ten int `Rebuilding` save | `rebuilding.c:473-514`; `building.c:29-46` |
| The fence code lock is ignored | the slot is `Att_CodeLock`, the getter is `Fence.GetCodeLock()` | `fence.c:26`, `:161-165` |
| A powered opener opens a locked fence | the caller used `OpenFence()` without `CanOpenFence()` | `fence.c:472-478` |

Do not build on `ActionPlugIntoFence`; it is marked deprecated (`P:\scripts\4_world\classes\useractionscomponent\actions\singleuse\actionplugintofence.c:1`).

## Who does what

| Concern | Owner |
|---|---|
| `.p3d` selections, memory points, the `Deployed` proxy, LODs, missing collision | `dayz-object-builder`, checked with `/dayz-p3d-audit` |
| `config.cpp`: the `Construction` block, slots, damage zones | `dayz-config-specialist` |
| Enforce Script: actions, RPC, sync variables, `modded class` | `dayz-script-specialist` |
| `OnStoreSave`, `OnStoreLoad`, part ids, the data audit | `dayz-persistence-specialist`, with the `dayz-persistence` and `rigorous-data-audit` skills |
| Part show and hide animations, the gate swing | `dayz-animation-specialist` |
| Build, deploy and test in game | `/dayz-build-pbo`, `/dayz-launch-test`, `/dayz-gate` |
| Terrain holes, bunkers under the terrain, underground triggers | `dayz-map-specialist` (the dayz-underground skill) |
