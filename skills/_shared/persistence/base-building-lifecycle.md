# Base building lifecycle

How a buildable object goes from a crafted kit to a base that survives a restart, call by call: deploy, the construction component, the base part, building, upgrading, dismantling and the save. Open it when one step misbehaves or you need the hook to override.

Every step that changes state runs in a `*Server` method on the server; the client only previews.

## Deploy the kit

1. A recipe such as `CraftFenceKit` (`P:\scripts\4_world\classes\recipes\recipes\craftfencekit.c:1`) uses up materials and gives a `KitBase` item (`P:\scripts\4_world\entities\itembase\kitbase.c:1`), whose `IsBasebuildingKit()` returns true (`:5`).
2. The kit's `SetActions` adds `ActionTogglePlaceObject` and `ActionDeployObject` (`kitbase.c:146` to `:152`).
3. `ActionDeployObject` (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\deployactions\actiondeployobject.c:7`) uses a hologram (`ActionUsesHologram` returns true, `:15`). It checks the placement against `player.GetHologramLocal()` on the client and `GetHologramServer()` on the server, `IsColliding()` and `item.CanBePlaced(...)` (`actiondeployobject.c:42` to `:75`). Kits turn on `DoPlacingHeightCheck()` and set `HeightCheckOverride()`: 2.54 for `FenceKit` (`P:\scripts\4_world\entities\itembase\fencekit.c:36` to `:44`) and 2.83 for `WatchtowerKit` (`P:\scripts\4_world\entities\itembase\watchtowerkit.c:32` to `:40`).
4. On finish the action calls `OnPlacementComplete` (`actiondeployobject.c:164`). The server part of `FenceKit.OnPlacementComplete` (`fencekit.c:19` to `:34`) creates the `Fence` with `g_Game.CreateObjectEx` and `ECE_PLACE_ON_SURFACE`, sets its position and orientation and calls `HideAllSelections()`.
5. A placed kit deletes itself in `OnEndServer` (`actiondeployobject.c:205`, the delete at `:228` to `:234`).

## The construction component

`EntityAI.ConstructionInit` (`P:\scripts\3_game\entities\entityai.c:3464` to `:3471`) calls `CreateConstructionComponent` (`:3474`). `BaseBuildingBase` overrides it to `m_Construction = new Construction(this)` (`P:\scripts\4_world\entities\itembase\basebuildingbase.c:871` to `:875`), stored as `protected ref ConstructionBasic m_Construction` (`:15`) and reached with `GetConstruction()`, which is `Construction.Cast(m_Construction)` (`:882` to `:885`). The constructor calls `ConstructionInit` (`:51`), and `OnCreatePhysics` calls it again before rebuilding the parts (`:488` to `:494`).

`UpdateConstructionParts` (`P:\scripts\4_world\classes\constructionbase.c:575` to `:606`) fills the parts from the cached type data, not by walking the config on each instance. `BuildingBase` uses the same hook to install `Rebuilding` (`P:\scripts\4_world\entities\game\super\building.c:47` to `:51`); that path never goes through a kit (`base-building-rebuildable.md`).

## The base part

A new object has no parts built. The player attaches the base material, for example wooden logs, and builds the part with `is_base=1`. That sets `HasBase()` to true, gives a construction kit back (`OnPartBuiltServer`, `basebuildingbase.c:553` to `:559`) and switches the `Deployed` animation (`InitVisuals`, `:676` to `:690`).

## Building a part

1. `ActionBuildPart` (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionbuildpart.c:33`) runs with a tool in hand. The server checks collision again in `ActionConditionContinue` and `OnFinishProgressServer` with `IsCollidingEx` (`actionbuildpart.c:123` to `:148` and `:150` to `:167`).
2. `OnFinishProgressServer` checks `CanBuildPart` again and, when `IsCollidingEx(checkData)` is false, calls `construction.BuildPartServerEx(action_data.m_Player, partName, AT_BUILD_PART)` (`actionbuildpart.c:157` to `:170`).
3. `Construction.BuildPartServerEx` resets the part's damage zone and calls `OnPartBuiltServer` on the object (`P:\scripts\4_world\classes\basebuilding\construction.c:52` to `:74`). The base `ConstructionBase.BuildPartServerEx` only calls `TakeMaterialsServer(part_name)` (`constructionbase.c:214` to `:219`), which locks a `lockable=1` material, subtracts `quantity`, or deletes the material item in the slot when `quantity` is `-1` (`constructionbase.c:1244` to `:1284`).
4. `OnPartBuiltServer` (`basebuildingbase.c:548` to `:579`) calls `RegisterPartForSync`, which sets the part's `id` bit in `m_SyncParts01`, `02` or `03` (`basebuildingbase.c:136` to `:163`), then syncs, shows the part's physics and visual and rebuilds the navmesh.

Override `BuildPartServerEx`; `BuildPartServer` is an obsolete wrapper (`base-building-1-30.md`).

Each construction step prints a `[bsb]` line through `bsbDebugPrint` when `LogManager.IsBaseBuildingLogEnable()` is true (`P:\scripts\3_game\tools\debug.c:809`); the diag menu toggles it (`P:\scripts\4_world\plugins\pluginbase\plugindiagmenu\plugindiagmenuclient.c:1414`). Turn it on in a diag build to follow a build, dismantle or save in the log.

### What allows build, dismantle and destroy

| Check | Passes when | Source |
|---|---|---|
| `CanBuildPart`, `CanBuildPartEx` | the part is not built, its required parts are, its support is fulfilled (`PartHasAnySupportFulfilled`, true by default, `:796` to `:799`), no conflicting part is, the materials are there and not ruined (`MaterialIsRuined`, `:725`), and the tool matches; failure reasons are bits of `EConstructionInfoCategories` | `constructionbase.c:641` to `:668`; `P:\scripts\4_world\classes\basebuilding\constructionconstants.c:1` to `:11` |
| `CanDismantlePart` | the part is built, no built part depends on it, `SupportRemovalCheck` passes and the tool matches (`CanUseToolToDismantlePart`, `:1545`) | `constructionbase.c:837` to `:867` |
| `CanDestroyPart` | the part is built, nothing depends on it and `SupportRemovalCheck` passes; no tool or material check, because damage triggers it | `constructionbase.c:1127` to `:1133` |

`HasDependentPart` ignores utility parts (`constructionbase.c:870` to `:881`). `SupportRemovalCheck` returns true on `ConstructionBase` (`:884` to `:887`); only `Rebuilding` overrides it.

## Upgrading

An upgrade is just building more parts whose `required_parts[]` are built (`HasRequiredPart`, `constructionbase.c:780` to `:793`) and whose `conflicted_parts[]` are not (`HasConflictPart`, `:802` to `:826`). On the Fence, `wall_wood_down` needs `wall_base_down` and conflicts with `wall_metal_down`.

Several buildable parts under one selection give one action variant each. `ActionBuildPart` reads `m_VariantID`; `ConstructionActionData.OnUpdateActions` (`P:\scripts\4_world\classes\basebuilding\constructionactiondata.c:163` to `:199`) calls `GetConstructionPartsToBuild` on each cursor update and sets the count with `SetActionVariantCount` (`:187`).

## Dismantle, destroy and fold

- Dismantle: `ActionDismantlePart` (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actiondismantlepart.c:23`) calls `DismantlePartServerEx` (`actiondismantlepart.c:107`; `constructionbase.c:225` to `:241`, overridden at `construction.c:77` to `:90`). It refunds materials through `ReceiveMaterialsServer` and `StaticConstructionMethods.SpawnConstructionMaterialPilesEx` (`constructionbase.c:1288` to `:1299`), drops materials that cannot be reused and the part's essential attachments, runs the item fall check, and `Construction` then calls `OnPartDismantledServer`. It is blocked while a built part depends on this one (`HasDependentPart`, `constructionbase.c:870` to `:881`). Dismantling the base destroys the whole object 200 ms later (`basebuildingbase.c:614` to `:618`).
- Destroy: when a damage zone reaches `STATE_RUINED`, `ConstructionBase.OnHealthLevelChanged` (`constructionbase.c:410` to `:426`) calls `DestroyPartServer` on that part (`constructionbase.c:244`); `Construction.DestroyPartServer` then calls `DestroyConnectedParts` (`construction.c:93` to `:114`; `constructionbase.c:258` to `:273`) to destroy the parts that depend on it. A part is spared when `ExceptionCheck` returns true (`constructionbase.c:429`); `Construction.ExceptionCheck` spares a gate while `wall_base_down` or `wall_base_up` is built (`construction.c:136` to `:148`).
- Fold: with no base and no attachments (`CanFoldBaseBuildingObject`, `basebuildingbase.c:961` to `:969`), `ActionFoldBaseBuildingObject` calls `FoldBaseBuildingObject` (`:971` to `:977`), which turns the object back into a kit in the player's hands.

## Save and load

- `OnStoreSave` (`basebuildingbase.c:419` to `:429`) writes `m_SyncParts01`, `02`, `03`, then `m_HasBase`. A subclass appends its own fields after `super`; the Fence adds `m_GateState` and `m_IsOpened` (`P:\scripts\4_world\entities\itembase\basebuildingbase\fence.c:255` to `:263`).
- `OnStoreLoad` (`basebuildingbase.c:431` to `:463`) reads the three ints and `m_HasBase`, returning `false` on any failed read. A subclass reads after `super` in the same order (`fence.c:265` to `:298`).
- `AfterStoreLoad` (`basebuildingbase.c:465` to `:473`) calls `SetPartsAfterStoreLoad` (`:475` to `:486`), which calls `SetPartsFromSyncData`: each part's built flag is set from the masks, the base state from the base part, and the result is synced. When `m_FixDamageSystemInit` is set, the same rebuild runs from `EEOnAfterLoad` through a 500 ms `CallLater` instead (`:504` to `:512`).
- `SetPartFromSyncData` (`basebuildingbase.c:264` to `:304`) compares the saved bit with the built flag for each part, adds or removes it, shows or hides its physics, switches the `Deployed` proxy for the base and locks the attached materials again, which vanilla comments as a "failsafe for corrupted sync/storage data" (`:302`).

## Action ids and action classes

`AT_BUILD_PART = 193`, `AT_DISMANTLE_PART = 195` and `AT_DESTROY_PART = 209` (`P:\scripts\4_world\classes\useractionscomponent\_constants.c:6` to `:8`). `m_InteractedPartId` and `m_PerformedActionId` (`basebuildingbase.c:13` and `:14`, registered at `:46` and `:47`) sync the last action so clients play the right sound (`SetActionFromSyncData`, `:247` to `:261`).

The actions, under `P:\scripts\4_world\classes\useractionscomponent\actions\`:

| Action | File |
|---|---|
| Build | `continuous\actionbuildpart.c` |
| Dismantle | `continuous\actiondismantlepart.c` |
| Destroy | `continuous\actiondestroypart.c` |
| Deploy | `continuous\deployactions\actiondeployobject.c` |
| Fold | `continuous\actionfoldbasebuildingobject.c` |
| Build a shelter without a tool | `interact\actionbuildshelter.c` |
| Open and close a fence | `interact\actionopenfence.c`, `interact\actionclosefence.c` |
| Attach material | `singleuse\actionattachtoconstruction.c` |
| Plug into a fence | `singleuse\actionplugintofence.c`, deprecated; do not build on it |

The shelter path without a tool (`ActionBuildShelter`, and `ActionActionBuildPartNoTool` at `actionbuildpart.c:543`, a subclass of `ActionBuildPartHandsGeneric` with `UseMainItem()` false; vanilla spells the class with `Action` twice) exists, but its shelter config is not traced here.
