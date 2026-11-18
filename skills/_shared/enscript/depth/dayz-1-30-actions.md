# Actions in DayZ 1.30

What changed in the 1.30 action system: info only actions, action manager states, the liquid action, animation overrides, target conditions, new inputs, recipes and the targets cursor. The full list of 1.30 changes is in `dayz-1-30-enforce-script.md`.

## Info only actions

`ActionBase` gained three hooks:

| Hook | What it does | Source |
|---|---|---|
| `InitInfoData()` | Empty hook that fills `m_InfoData` | `P:\scripts\4_world\classes\useractionscomponent\actionbase.c:159` to `:161` |
| `bool IsTargetInfoAction()` | True when `m_InfoData` is set; the cursor shows an info panel | `actionbase.c:276` |
| `bool CanBeStarted()` | True by default; false for an action that only shows information | `actionbase.c:287` |

`ActionPartInfo` returns false from `CanBeStarted()` (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionpartinfo.c:18` to `:21`), and the client never calls `ActionStart` on such an action (`P:\scripts\4_world\classes\useractionscomponent\actionmanagerclient.c:336` and `:337`). `ActionInput.SortActions(array<ActionBase> allActions)` (`P:\scripts\4_world\classes\useractionscomponent\actioninput.c:464`) puts actions that can run before info actions.

## Action manager states and starting

`PerformAction(int user_action_id, ActionTarget target, ItemBase item, Param extraData = NULL)` is still inside `#ifdef BOT`, followed by `PerformActionStart` (`actionmanagerclient.c:796`). The lines moved: in 1.29 `PerformAction` was at `:756` inside the `#ifdef BOT` block at `:754` to `:760`, `PerformActionStart` at `:762` and `ActionBase.Can` at `:912`. In single player `PerformActionStart` does nothing while an action is pending or running (`:806` to `:814`), and `GetActionState()` returns `UA_AM_INIT` while pending (`:822` to `:825`).

`UA_AM_INIT` is new and moved the values after it (`P:\scripts\3_game\constants.c:508` to `:511`); in 1.29 `UA_AM_PENDING` was 14:

| Constant | Value |
|---|---|
| `UA_AM_INIT` | 14 |
| `UA_AM_PENDING` | 15 |
| `UA_AM_ACCEPTED` | 16 |
| `UA_AM_REJECTED` | 17 |

Use the names, never the numbers. Check conditions through the public `Can(PlayerBase, ActionTarget, ItemBase)` (`actionbase.c:968`), not the protected `ActionCondition`.

## Filling a container

`ActionFillBottleBase` is `[Obsolete("1.30: replaced by class ActionObtainLiquidBase")]` (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionfillbottlebase.c:28`), and `RegisterActions` inserts `ActionObtainLiquidBase` instead (`P:\scripts\4_world\classes\useractionscomponent\actionconstructor.c:156`). Bottles add it with `AddAction(ActionObtainLiquidBase)` (`P:\scripts\4_world\entities\itembase\edible_base\bottle_base.c:364`). A `modded ActionFillBottleBase` is never created.

The new action's conditions (`actionobtainliquidbase.c:56`):

```c
m_ConditionItem 	= new CCINonRuined();
m_ConditionTarget 	= new CCTLiquid(m_AllowedLiquidMask, UAMaxDistances.DEFAULT, UAMaxDistances.DEFAULT);
```

## Target conditions

- `CCTLiquid(int allowedLiquidSource, float maximalTargetDistance = UAMaxDistances.DEFAULT, float maxVerticalReach = UAMaxDistances.DEFAULT, SurfaceDetectionType surfaceDetectionType = SurfaceDetectionType.Roadway, bool allowSeaLevelCursorFallback = false)` (`P:\scripts\4_world\classes\useractionscomponent\targetconditionscomponents\cctliquid.c:37`) replaces `CCTWaterSurfaceEx` for fill and drink targets.
- `CCTCursorInherited` accepts the cursor hit, `target.GetCursorHitPos()`, when its squared distance to either the player's root or the head position is within `m_MaximalActionDistanceSq` (`cctcursorinherited.c:28` to `:32`). `CCTCursor` does the same on the client (`cctcursor.c:35` to `:43`); on the server it ignores the cursor and compares the target's `GetPosition()` with the player's, allowing the distance plus the target's `GetCollisionRadius()` (`:28` to `:33`).
- `MiscGameplayFunctions.GetPlayerHeadPosition` returns a height from the stance, not the head bone (`P:\scripts\4_world\static\miscgameplayfunctions.c:778` to `:789`, with the heights from `GetPlayerHeadHeight` at `:761` to `:771`).

## Animation overrides

Overrides moved from `ItemBase.m_ItemActionOverrides`, which no longer exists, to `EntityAI`: `ActionOverrideData` (`P:\scripts\3_game\entities\entityai.c:103` to `:108`) and the static map `m_EntityActionOverrides` (`:117`). Register with `OverrideActionAnimation(typename action, int commandUID, int stanceMask = -1, int commandUIDProne = -1)` (`:4781`). `AnimatedActionBase.GetCommandOverride` looks up the item's type, then the target object's type (`P:\scripts\4_world\classes\useractionscomponent\animatedactionbase.c:284` to `:290`), so a target can carry the override too.

## New inputs

`P:\bin\constants.xml` adds `UAToggleVehicleLights` beside `UAToggleHeadlight`, both with `loc="TOGGLE_LIGHT_HEAD"` (`:90` and `:91`). Bind vehicle lights to `UAToggleVehicleLights`. Also new: `UABuldLinkCamToTerrain`, `UABuldCopyTileCoord`, `UABuldMarkUnderground`, `UABuldRemoveUnderground` (`:282` to `:285`; vanilla spells them `Buld`) and `UAUICodeLockLeft`, `Right`, `Up`, `Down` (`:308` to `:311`). `UACarHorn` is unchanged (`:203`).

## Recipes keep the result's health

In 1.29 a recipe with `m_ResultReplacesIngredient` called `TransferItemProperties` and could overwrite the health chosen by `m_ResultInheritsHealth`. In 1.30 the recipe passes `false` as the fifth argument, `transfer_health`:

```c
MiscGameplayFunctions.TransferItemProperties(ingr, res, true, true, false, false);   // P:\scripts\4_world\classes\recipes\recipebase.c:353
```

In `TransferItemProperties`, `transfer_health` still defaults to true (`P:\scripts\4_world\static\miscgameplayfunctions.c:271`). Set `m_ResultInheritsHealth` when the result should keep the ingredient's health. `GetRecipeClassName(int recipe_id)` is at `P:\scripts\4_world\plugins\pluginbase\pluginrecipesmanager.c:84`.

## The targets cursor update

`ActionTargetsCursor.Update()` became `Update(bool fullUpdate = true)`. A 1.29 override fails on 1.30 with `Overloaded function 'Update' not compatible` (measured in game). Gate the override on the version define (see `skills/dayz-launch-test/references/dayz-1-30-server-measured.md`, section on the version define):

```c
#ifdef DAYZ_1_29
	override void Update()
	{
		super.Update();
#else
	override void Update(bool fullUpdate = true)
	{
		super.Update(fullUpdate);
#endif
		// shared body
	}
```
