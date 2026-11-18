# Building on BaseBuildingBase

How a buildable structure (fence, watchtower, gate, wall, shelter, flag pole, barbed wire) uses the vanilla base building system: the classes, the kit to base flow, the `Construction` block, the rules that corrupt data without a warning, quick triage and who writes what. The save rules in short are in `base-building.md`.

Build on the vanilla system instead of writing your own. A buildable structure extends the `BaseBuildingBase` chain, not `EntityAI`, and so inherits the build, dismantle and destroy actions, the bit mask save, the hologram deploy and damage that destroys parts. You author a `.p3d` with the right selections and memory points, and a `Construction` config block that declares each part. Follow `_shared/dayz-conventions.md`. Packing and testing go through `/dayz-build-pbo` and `/dayz-launch-test`, which run `/dayz-preflight` themselves.

Class and field names in this area are easy to half remember. Before writing one, find it in `P:\scripts\4_world\` or in `P:\DZ\gear\camping\config.cpp`.

## The classes

| Class | Role | Source |
|---|---|---|
| `BaseBuildingBase` | the saved world object; owns the construction component, the sync ints, events, physics and area damage | `P:\scripts\4_world\entities\itembase\basebuildingbase.c:2` |
| `ConstructionBasic` | empty shell in `3_Game`; `EntityAI` creates the component through `CreateConstructionComponent()` | `P:\scripts\3_game\systems\construction_basic.c:2`; `P:\scripts\3_game\entities\entityai.c:3474` |
| `ConstructionBase` | the shared controller: `BuildPartServerEx`, `DismantlePartServerEx`, `IsCollidingEx` | `P:\scripts\4_world\classes\constructionbase.c:30`, `:179`, `:190`, `:1481` |
| `Construction` | the controller a `BaseBuildingBase` gets | `P:\scripts\4_world\classes\basebuilding\construction.c:2` |
| `Rebuilding` | the controller a map building gets; ten sync ints and its own save | `P:\scripts\4_world\classes\rebuilding\rebuilding.c:1`; created at `P:\scripts\4_world\entities\game\super\building.c:23` to `:27` |
| `ConstructionPartTypeData` | the `Construction` config fields, cached once per object type | `P:\scripts\4_world\classes\basebuilding\typeconstructiondata\constructionparttyped.c:2` |
| `ConstructionPart` | one part's changing state: built or not, sync bits | `P:\scripts\4_world\classes\basebuilding\constructionpart.c:3` |
| `ConstructionActionData` | per player working data: which parts can be built under the cursor, action variants | `P:\scripts\4_world\classes\basebuilding\constructionactiondata.c:1` |

The controller is not saved. It is rebuilt from config on every load, and its part states come back from the sync bit masks.

## From kit to base

Each step's hooks are in `base-building-lifecycle.md`.

1. Craft the kit: a recipe gives a `KitBase` item (`P:\scripts\4_world\entities\itembase\kitbase.c:1`).
2. Deploy: the kit adds `ActionTogglePlaceObject` and `ActionDeployObject` (`kitbase.c:146` to `:152`). On finish the server creates the real object with no parts shown (`FenceKit.OnPlacementComplete`, `P:\scripts\4_world\entities\itembase\fencekit.c:19` to `:34`).
3. Base part: the player attaches the base material and builds the part with `is_base=1`, which sets the base state and gives a construction kit back (`OnPartBuiltServer`, `basebuildingbase.c:554` to `:560`).
4. Build a part: `ActionBuildPart` with a tool calls `BuildPartServerEx` on the server (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionbuildpart.c:170`). Override `BuildPartServerEx`; `BuildPartServer` is an obsolete wrapper (`constructionbase.c:1702` to `:1708`).
5. Upgrade: more parts become buildable when their `required_parts[]` are built and none of their `conflicted_parts[]` is (`HasRequiredPart`, `constructionbase.c:682` to `:695`; `HasConflictPart`, `:704` to `:726`).
6. Dismantle: refunds materials, and is blocked while another built part depends on this one (`HasDependentPart`, `constructionbase.c:772` to `:783`). Dismantling the base destroys the whole object (`basebuildingbase.c:615` to `:619`).
7. Fold: with no base and no attachments the object folds back into a kit (`CanFoldBaseBuildingObject`, `basebuildingbase.c:962` to `:970`).

## The Construction block

Two levels: main part, then part. This is the vanilla Fence foundation (`P:\DZ\gear\camping\config.cpp:4529` to `:4554`); every field and its reader is in `base-building-config.md`.

```cpp
class Construction
{
    class wall                              // main part
    {
        class base                          // part: the class name is also the p3d selection
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
                    quantity=2;             // -1 deletes the whole material item in the slot, 0 ignores the quantity
                    lockable=1;             // lock the material in its slot instead of using it up
                };
            };
        };
    };
};
```

The object class also declares `attachments[]`, `hybridAttachments[]`, `mountables[]` and a `DamageSystem` with one damage zone per part.

## Rules that corrupt data without a warning

Check each one before calling a buildable object done.

- Each part `id` is unique and between 1 and 93. The id is a bit position in three sync ints (`RegisterPartForSync`, `basebuildingbase.c:137` to `:164`). A duplicate makes two parts toggle together; an id outside the range is never saved. Rebuildable map buildings pack differently (ten ints, two bits per part, `rebuilding.c:7` to `:16`); never mix the two.
- A damage zone name equals its part name in lower case. The zone name is lowered and used to look the part up (`OnHealthLevelChanged`, `constructionbase.c:352` to `:368`). With a mismatch, damage never destroys the part.
- Save and load order is fixed. `OnStoreSave` writes `m_SyncParts01`, `m_SyncParts02`, `m_SyncParts03`, then `m_HasBase` (`basebuildingbase.c:420` to `:430`), and `OnStoreLoad` reads them in that order (`:432` to `:464`). A subclass writes and reads its own fields after `super`, in the same order both ways, as the Fence does (`P:\scripts\4_world\entities\itembase\basebuildingbase\fence.c:246` to `:254` and `:256` to `:289`).
- Every part name is an animation source in config and a selection in the `.p3d`. Showing a part is `SetAnimationPhase(part_name, 0)` (`PerformShowAnim`, `constructionpart.c:474` to `:477`). A missing selection gives a part that builds with no visual or no collision.
- `OpenFence()` does not check the lock. `CanOpenFence()` requires `HasHinges() && !IsOpened() && !IsLocked()` (`fence.c:472` to `:478`); `OpenFence()` skips that and opens (`fence.c:488` to `:506`). A script that opens a fence calls `CanOpenFence()` first. `IsLocked()` covers a locked `CombinationLock` and a locked `DigitalCodeLock` (`fence.c:127` to `:142`).
- `AT_BUILD_PART = 193`, `AT_DISMANTLE_PART = 195` and `AT_DESTROY_PART = 209` (`P:\scripts\4_world\classes\useractionscomponent\_constants.c:6` to `:8`) are passed to the `*ServerEx` methods and synced so clients play the right sound.
- A slot's `stackMax` decides how much material fits, not the item's `varQuantityMax`. A recipe that asks for more than the slot holds can never be built. Details, and the hologram, carry pose and wall placement traps, are in `base-building-placement.md`.

## Saving is data critical

Built state is packed into `m_SyncParts01`, `m_SyncParts02` and `m_SyncParts03` (`basebuildingbase.c:10` to `:12`), which are both the network sync and the save. After load, `SetPartFromSyncData` rebuilds each part from the bits and locks attached materials again as a failsafe (`basebuildingbase.c:265` to `:304`).

Any change that adds parts, changes ids, or touches `OnStoreSave` or `OnStoreLoad` on a buildable object can lose every base on a server. Before it ships, `dayz-persistence-specialist` runs `base-building-save-checklist.md` and the deep audit in `deep-audit.md`. A `CombinationLock` also saves `m_CombinationInside`, read only from storage version 143 (`P:\scripts\4_world\entities\itembase\combinationlock.c:169` to `:177`); a lock subclass that reads the old two values loads the rest of the record wrong.

## Quick triage

| Symptom | Likely cause | Read |
|---|---|---|
| Base doesn't save, or parts reset on restart | save and load order differ, or a subclass wrote before `super` | `base-building-save-checklist.md` |
| A built part doesn't show | the part name is not an animation source, or not a selection in the `.p3d` | `base-building-config.md`, section "Model names the readers assume" |
| A built part has no collision | the part's proxy selection is missing, or the base lacks the `Deployed` proxy | `/dayz-p3d-audit`; `base-building-config.md`, section "Model names the readers assume" |
| Two parts toggle together | duplicate or out of range `id` | `RegisterPartForSync`, `basebuildingbase.c:137` to `:164` |
| Damage never destroys a part | the damage zone name differs from the lower case part name | `constructionbase.c:352` to `:368` |
| The build action never appears | the tool's `build_action_type` shares no bit with the part's, `CanBuildPart` fails, or the recipe needs more than the slot's `stackMax` | `CanBuildPartEx`, `constructionbase.c:590` to `:610`; `CanUseToolToBuildPart`, `:1404` to `:1441`; `base-building-placement.md` |
| Dismantle is blocked | another built part depends on this one | `HasDependentPart`, `constructionbase.c:772` to `:783` |
| Built but not shown until sync, in single player | `SetRequestBuiltState` sets the state only in multiplayer; it is obsolete, use `SetBuiltState` | `constructionpart.c:505` to `:512` |
| The hologram won't confirm | the height check or the collision check fails | `actiondeployobject.c`; `base-building-lifecycle.md`, section "Deploy the kit" |
| A hitch when building | `UpdatePhysics()` is "a massive performance hit" by its own comment | `basebuildingbase.c:745` |
| An override of `BuildPartServer` never runs | vanilla calls `BuildPartServerEx` | `actionbuildpart.c:170` |
| Code uses `CreateCollisionTrigger` | it compiles but is `[Obsolete("no replacement")]`; use `IsCollidingEx(CollisionCheckData)` | `constructionbase.c:1481`, `:1756` and `:1757` |
| A rebuilt house or well part resets | the three int `BaseBuildingBase` save was mixed with the ten int `Rebuilding` save | `rebuilding.c:473` to `:514`; `building.c:29` to `:46` |
| The fence code lock is ignored | the slot is `Att_CodeLock` and the getter is `Fence.GetCodeLock()` | `fence.c:26`, `:161` to `:165` |
| A powered opener opens a locked fence | the caller used `OpenFence()` without `CanOpenFence()` | `fence.c:472` to `:478` |

Do not build on `ActionPlugIntoFence`; it is marked deprecated (`P:\scripts\4_world\classes\useractionscomponent\actions\singleuse\actionplugintofence.c:1`).

## Who writes what

| Part | Owner |
|---|---|
| `.p3d` selections, memory points, the `Deployed` proxy, LODs, missing collision | `dayz-object-builder`, checked with `/dayz-p3d-audit` |
| `config.cpp`: the `Construction` block, slots, damage zones | `dayz-config-specialist` |
| Enforce Script: actions, RPC, sync variables, `modded class` | `dayz-script-specialist` |
| `OnStoreSave`, `OnStoreLoad`, part ids, the data audit | `dayz-persistence-specialist`, with this pack |
| Part show and hide animations, the gate swing | `dayz-animation-specialist` |
| Build, deploy and test in game | `/dayz-build-pbo`, `/dayz-launch-test`, `/dayz-gate` |
| Terrain holes, bunkers under the terrain, underground triggers | `dayz-map-specialist` (`_shared/world/`) |
