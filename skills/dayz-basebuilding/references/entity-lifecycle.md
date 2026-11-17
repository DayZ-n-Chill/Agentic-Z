# Entity lifecycle: deploy, build, sync, save, load

The exact call chain from crafting a kit to a base surviving a server restart, hop by hop. Open this when a step of that chain misbehaves or you need the hook to override.

Line numbers are from the vanilla scripts and configs on `P:\` (game storage version 144). A citation marked `1.29` points at the 1.29 scripts, which are not on `P:\`; those lines were not checked there and are kept as a map for older mods.

Server-authoritative: every mutating hop runs through a `*Server` method gated by `g_Game.IsServer()`; the client only previews.

## 1. Deploy (hologram)

1. `RecipeBase` (`P:\scripts\4_world\classes\recipes\recipes\craftfencekit.c:1`) consumes materials and gives a `KitBase: ItemBase` (`P:\scripts\4_world\entities\itembase\kitbase.c:1`; `IsBasebuildingKit()` returns true, `:5`).
2. Kit `SetActions()` adds `ActionTogglePlaceObject` + `ActionDeployObject` (`kitbase.c:146-152`).
3. `ActionDeployObject` (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\deployactions\actiondeployobject.c:7`) is hologram-driven (`ActionUsesHologram()` returns true, `:15`). Placement validity is checked against `player.GetHologramLocal()/GetHologramServer()`, `IsColliding()`, `item.CanBePlaced(...)` (`actiondeployobject.c:42-75`). Kits declare `DoPlacingHeightCheck()` as true and a `HeightCheckOverride()` (FenceKit 2.54 `P:\scripts\4_world\entities\itembase\fencekit.c:36-44`; WatchtowerKit 2.83 `P:\scripts\4_world\entities\itembase\watchtowerkit.c:32-40`).
4. On finish the client calls `entity.OnPlacementComplete(...)` (`actiondeployobject.c:164`). The SERVER-only `FenceKit.OnPlacementComplete` (`fencekit.c:19-34`) does `g_Game.CreateObjectEx("Fence", …)` with `ECE_PLACE_ON_SURFACE`, sets pos/orient, `HideAllSelections()`.
5. The kit self-deletes on `OnEndServer` if it was placed (`actiondeployobject.c:230-234`).

## 2. Construction init

Until 1.29 `BaseBuildingBase` owned one `ref Construction m_Construction` (1.29 `basebuildingbase.c:8`), created in `ConstructionInit()` (1.29 `:965-973`), called from the constructor (1.29 `:52`) and again in `OnCreatePhysics()` (1.29 `:489-494`), with `GetConstruction()` at 1.29 `:975`. `Construction.UpdateConstructionParts()` (1.29 `construction.c:235-270`) reads the `Construction{}` config block and populates `map<string, ref ConstructionPart> m_ConstructionParts` (1.29 `construction.c:15`), keyed by part config-class name. Since 1.30: `protected ref ConstructionBasic m_Construction` (`P:\scripts\4_world\entities\itembase\basebuildingbase.c:15`). `ConstructionInit()` is on `EntityAI` (`P:\scripts\3_game\entities\entityai.c:3464-3471`) and calls `CreateConstructionComponent()` (`:3474`). `BaseBuildingBase` overrides that to `m_Construction = new Construction(this)` (`basebuildingbase.c:872-876`). `UpdateConstructionParts` is on `P:\scripts\4_world\classes\constructionbase.c:517-548` and fills parts from `ConstructionDataTypeHolder`, not by walking config on the instance. `GetConstruction()` is `Construction.Cast(m_Construction)` (`basebuildingbase.c:883-886`).

## 3. Base part

The freshly-spawned entity has NO parts built. The player attaches the base material (e.g. WoodenLogs) then builds the `base` part (`is_base=1`). Building the base sets `HasBase()` to true, spawns a construction kit back (`OnPartBuiltServer` `basebuildingbase.c:554-560`), and toggles the `"Deployed"` animation/proxy (`InitVisuals` `:677-691`).

## 4. Build a part

1. `ActionBuildPart` (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionbuildpart.c:33`) with a tool in hand. Collision is re-checked server-side in `ActionConditionContinue` / `OnFinishProgressServer` via `IsCollidingEx` (`actionbuildpart.c:123-148,150-167`).
2. `OnFinishProgressServer` checks `CanBuildPart` again and, when `IsCollidingEx(checkData)` is false, calls `construction.BuildPartServerEx(action_data.m_Player, partName, AT_BUILD_PART)` (`actionbuildpart.c:157-170`). `Construction.BuildPartServerEx` resets the damage zone and calls `OnPartBuiltServer` (`P:\scripts\4_world\classes\basebuilding\construction.c:52-68`). Until 1.29 the same hook (1.29 `actionbuildpart.c:112-130`) called `construction.BuildPartServer(player, part_name, AT_BUILD_PART)` (1.29 `construction.c:75-95`).
3. The build itself: reset the part's damage zone health, `TakeMaterialsServer` (`constructionbase.c:1139-1179`; 1.29 `construction.c:671-723`: `lockable=1` locks the slot, otherwise it subtracts `quantity`, or deletes the object when `quantity` is `-1`), then `OnPartBuiltServer` on the parent (`basebuildingbase.c:549-580`). `ConstructionBase.BuildPartServerEx` only calls `TakeMaterialsServer(part_name)` (`constructionbase.c:179-184`). Until 1.29 `BuildPartServer` also destroyed a construction box trigger; `CreateCollisionTrigger`, `DestroyCollisionTrigger` and `IsTriggerColliding` remain as `[Obsolete("no replacement")]` (`constructionbase.c:1756-1801`). Do not write new trigger calls.
4. `OnPartBuiltServer` calls `RegisterPartForSync` (sets the part's `id` bit in `m_SyncParts01/02/03` `basebuildingbase.c:137-164`), sync, show part physics + visual, regen navmesh.

### `CanBuildPart`, `CanDismantlePart` and `CanDestroyPart` gates

- `CanBuildPart` (1.29 `construction.c:296-304`): `!IsPartConstructed && HasRequiredPart && !HasConflictPart && HasMaterials && (!use_tool || CanUseToolToBuildPart) && !MaterialIsRuined`. (since 1.30: `CanBuildPart` / `CanBuildPartEx` on `constructionbase.c:583-610`; failure bits in `EConstructionInfoCategories` (`P:\scripts\4_world\classes\basebuilding\constructionconstants.c:1-11`).)
- `CanDismantlePart` (1.29 `construction.c:468-476`): `IsPartConstructed && !HasDependentPart && CanUseToolToDismantlePart`; since 1.30 it also requires `SupportRemovalCheck` (`constructionbase.c:739-769`).
- `CanDestroyPart` (1.29 `construction.c:566-574`; since 1.30 also `SupportRemovalCheck`, `constructionbase.c:1022-1028`): `IsPartConstructed && !HasDependentPart` (no tool/material gate, triggered by damage, 1.29 `basebuildingbase.c:510-518`; 1.30 `constructionbase.c:352-368`).

## 5. Upgrade

Just building further parts whose `required_parts[]` are satisfied (`HasRequiredPart` `constructionbase.c:682-695`) and whose `conflicted_parts[]` are not built (`HasConflictPart` `:704-726`). E.g. `wall_wood_down` requires `wall_base_down` and conflicts with `wall_metal_down`. Radial variants: multiple buildable parts under one selection produce N action variants, `ActionBuildPart` uses `m_VariantID`; `ConstructionActionData.OnUpdateActions` sets the variant count with `SetActionVariantCount` (`P:\scripts\4_world\classes\basebuilding\constructionactiondata.c:187`), and its `OnUpdateActions` (`:163-199`) calls `Construction.GetConstructionPartsToBuild(...)` each cursor update.

## 6. Dismantle / destroy / fold

- `ActionDismantlePart` (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actiondismantlepart.c:23`) calls `DismantlePartServer` (1.29 `construction.c:98-118`): it refunds materials (`ReceiveMaterialsServer`, then `StaticConstructionMethods.SpawnConstructionMaterialPiles`), drops non-usable materials, calls `OnPartDismantledServer`. Blocked if the part `HasDependentPart` (`constructionbase.c:772-783`). Dismantling the **base** destroys the whole construction (`basebuildingbase.c:615-619`). (since 1.30: `DismantlePartServerEx` (`constructionbase.c:190-206`, override `construction.c:77-90`). `HasDependentPart` is `constructionbase.c:772`.)
- Destroy on ruin: `EEHealthLevelChanged` (1.29 `basebuildingbase.c:496-528`; 1.30 `ConstructionBase.OnHealthLevelChanged`, `constructionbase.c:352-368`), when a zone hits `STATE_RUINED`, `DestroyPartServer` that part + `DestroyConnectedParts` (1.29 `construction.c:141-154`, dependents, with a gate exception `ExceptionCheck` `:157-167`).
- Fold: with no base and no attachments (`CanFoldBaseBuildingObject` `basebuildingbase.c:962-970`), `ActionFoldBaseBuildingObject` calls `FoldBaseBuildingObject` (`:972-978`), which converts back to a kit in hands.

## 7. Save and load reconciliation

- `OnStoreSave` (`basebuildingbase.c:420-430`): writes `m_SyncParts01`, `02`, `03`, then `m_HasBase`. A subclass appends its extra fields AFTER `super` (Fence adds `m_GateState`, `m_IsOpened`, `P:\scripts\4_world\entities\itembase\basebuildingbase\fence.c:246-254`).
- `OnStoreLoad` (`basebuildingbase.c:432-464`): reads the three ints then `m_HasBase`, each with a `return false` on read failure (default-then-abort). Subclass reads AFTER `super` in the same order (`fence.c:256-289`, with a `version<110` legacy branch).
- `AfterStoreLoad` (`basebuildingbase.c:466-474`) calls `SetPartsAfterStoreLoad()` (`:476-487`), which calls `SetPartsFromSyncData()`: it rebuilds each part's built flag from the bitmask, sets base state from the base part, re-syncs. Guarded by `m_FixDamageSystemInit` (the damage-system migration path uses `EEOnAfterLoad` + a 500ms deferred call instead, `:505-513`).
- `SetPartFromSyncData` (`basebuildingbase.c:265-304`), the reconciliation core: per part, compares "built in sync bitmask" vs "built flag", adds/removes constructed parts, shows/hides physics, toggles the `Deployed` proxy for the base, and **failsafe-relocks attached materials** (`:303`, "failsafe for corrupted sync/storage data").

## 8. Action-type ints and the action set

`P:\scripts\4_world\classes\useractionscomponent\_constants.c:6-8`: `AT_BUILD_PART=193`, `AT_DISMANTLE_PART=195`, `AT_DESTROY_PART=209`. Also `m_InteractedPartId` / `m_PerformedActionId` (`basebuildingbase.c:13-14`, registered `:46-47`) sync the last action so clients play the right SFX (`SetActionFromSyncData` `:248-262`).

Action classes (under `P:\scripts\4_world\classes\useractionscomponent\actions\`): `actionbuildpart.c`, `actiondismantlepart.c`, `P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actiondestroypart.c`, `actiondeployobject.c`, `P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionfoldbasebuildingobject.c`, `P:\scripts\4_world\classes\useractionscomponent\actions\interact\actionbuildshelter.c` (no-tool build), `P:\scripts\4_world\classes\useractionscomponent\actions\interact\actionopenfence.c`, `P:\scripts\4_world\classes\useractionscomponent\actions\interact\actionclosefence.c`, `P:\scripts\4_world\classes\useractionscomponent\actions\singleuse\actionattachtoconstruction.c`, `P:\scripts\4_world\classes\useractionscomponent\actions\singleuse\actionplugintofence.c` (DEPRECATED, do not build on it).

Not checked: The no-tool shelter path (`ActionBuildShelter` / `ActionActionBuildPartNoTool` (`actionbuildpart.c:543` on `P:\`), `UseMainItem()` false, 1.29 `actionbuildpart.c:224-245` + `actionbuildshelter.c`) exists but its shelter-specific config was not fully traced in this pass.

## 9. DayZ 1.30: hop notes

- `CreateConstructionComponent` / `GetConstructionBasic` are the hooks; see `dayz-1-30-construction-rebuilding.md`, section 1, for the getters copied from vanilla.
- `BuildingBase` uses the same hooks to install `Rebuilding` (`P:\scripts\4_world\entities\game\super\building.c:23-51`). That path does **not** go through `FenceKit.OnPlacementComplete`.
- `SetRequestBuiltState` is obsolete (`P:\scripts\4_world\classes\basebuilding\constructionpart.c:505-512`); use `SetBuiltState`.
- Fence `OnStoreSave` in 1.30 is `fence.c:246-254` (still `super` then `m_GateState`, `m_IsOpened`).
