# DayZ 1.30 — Enforce Script contract

Consultation reference for `enforce-script-reference`. Every line cited as `P:\...:N` was opened on `P:\`, whose extraction is a 1.30 build older than 1.30.164200 (it still declares `vector.Cross`, section 8.3). On a later build a line can have moved: find the symbol by name, and see `skills/_shared/knowledge/dayz-1-30-build-history.md` ("Which line a citation gives"). `[EXACT]` marks text copied from the cited file. `[DESIGN]` marks migration advice.

Until 1.29: CE tick `OnCEUpdate()`, inventory hooked `ProcessInputData`, fill-bottle `ActionFillBottleBase`, 3rd-person `World.Is3rdPersonDisabled()`, storage `142`. Since 1.30: replacements below.

## 1. Central Economy tick: `OnCEUpdate` → `OnCEIterate`

Until 1.29: `EntityAI.OnCEUpdate()` had no time args (1.29 `entityai.c:3860`). Since 1.30 it is empty `[Obsolete]`; the live tick is `OnCEIterate(float currentTime, float elapsedTime)`.

```c
// [EXACT] P:\scripts\3_game\entities\entityai.c:3904
	void OnCEIterate(float currentTime, float elapsedTime)
	{
		ProcessVariables(elapsedTime);
		
		ConstructionBasic constructionComponent = GetConstructionBasic();
		if (constructionComponent && ConstructionBasic.CanConstructionDecay() && GetAllowDamage()) //checks if server allows damage AND decay
			constructionComponent.ProcessConstructionDecay(elapsedTime);
	}
```

```c
// [EXACT] P:\scripts\3_game\entities\entityai.c:4924
	[Obsolete("1.30: Use OnCEIterate(float currentTime, float elapsedTime) instead")]
	void OnCEUpdate();
```

`[DESIGN]` Rename `override void OnCEUpdate()` to `OnCEIterate(float currentTime, float elapsedTime)` and `super.OnCEIterate(currentTime, elapsedTime)`.

## 2. `GAME_STORAGE_VERSION = 144`

Until 1.29: `static int GAME_STORAGE_VERSION = 142;` (1.29 `game.c:5`). Since 1.30:

```c
// [EXACT] P:\scripts\3_game\global\game.c:5
static int GAME_STORAGE_VERSION = 144;
```

`CGame` still calls `StorageVersion(GAME_STORAGE_VERSION)` (`P:\scripts\3_game\global\game.c:50`). Stream layout = skill `dayz-persistence`. Do not hardcode `142` against `g_Game.SaveVersion()`.

## 3. Inventory command pipeline (retail no longer calls `ProcessInputData`)

Until 1.29: one `ProcessInputData(ParamsReadContext ctx, bool is_juncture, bool is_remote)`. Since 1.30 that method still exists (`P:\scripts\4_world\systems\inventory\dayzplayerinventory.c:3319`) but call sites are `#ifdef DIAG_DEVELOPER` **and** `PluginInventoryDebug.IsOldProcessInputDataEnable()`. Retail uses Validate / Execute*.

```c
// [EXACT] P:\scripts\4_world\systems\inventory\dayzplayerinventory.c:669
#ifdef DIAG_DEVELOPER
		if (PluginInventoryDebug.Cast(GetPlugin(PluginInventoryDebug)).IsOldProcessInputDataEnable())
		{
			ProcessInputData(ctx, true, false);
		}
		else
		{
#endif
			if(g_Game.IsServer())
			{
				ExecuteInventoryCommandServer(ctx);
			}
			else
			{
				ExecuteInventoryCommandClient(ctx);
			}
#ifdef DIAG_DEVELOPER
		}
#endif
```

| Method | Cite | Role |
|---|---|---|
| `bool ValidateInventoryCommandServer(ParamsReadContext ctx)` | `P:\scripts\4_world\systems\inventory\dayzplayerinventory.c:3410` | Server juncture validation |
| `bool ExecuteInventoryCommandServer(ParamsReadContext ctx)` | `:3501` | Server execute |
| `bool ExecuteInventoryCommandClient(ParamsReadContext ctx)` | `:3569` | Owner-client after juncture |
| `bool ExecuteInventoryCommandRemote(ParamsReadContext ctx)` | `:3633` | Remote-client execute |

Input-user-data uses the same DIAG gate (`:734-744`) then `ValidateInventoryCommandServer` on server. `[DESIGN]` A `modded DayZPlayerInventory` that only overrode `ProcessInputData` is silent in retail.

### 3.1 `INPUT_UDT_INVENTORY_CHECK` / `OnInventoryCheck`

```c
// [EXACT] P:\scripts\3_game\tools\component\_constants.c:19
const int INPUT_UDT_INVENTORY_CHECK					= 16;
```

Caps: `INVENTORY_REPAIR_MAX_DISTANCE = 500.0`, `INVENTORY_REPAIR_MAX_ITEMS = 5` (`P:\scripts\4_world\systems\inventory\dayzplayerinventory.c:163-164`, comments misspelled in vanilla).

```c
// [EXACT] P:\scripts\4_world\systems\inventory\dayzplayerinventory.c:5003
	override bool OnInventoryCheck(int userDataType, ParamsReadContext ctx)
	{
		if (userDataType == INPUT_UDT_INVENTORY_CHECK)
```

Mismatch → `InventoryInputUserData.SendServerInventoryCheck` (`:5052`), DIAG-gated by `IsDesyncRepairEnable` (`:5048-5055`).


### 3.2 Hooking inventory moves from a mod (measured on 1.30.164200)

[EXACT] The table above is the vanilla path, not a hook point: on DayZDiag 1.30.164200 `modded class DayZPlayerInventory` (scripts/4_World) does not compile. The server script log reads `Engine class 'DayZPlayerInventory' cannot be modded.` and `Can't compile "World" script module!`, and the server process died before the managed launcher saw it ready. `modded class Magazine` fails the same way (`Engine class 'Magazine' cannot be modded.`); `modded class Ammunition_Base` (`P:\scripts\4_world\entities\itembase\magazine\ammunitionpiles.c:2`) compiled in the same build. The validator rule `ES-MODDED-ENGINE-CLASS` lists the classes whose refusal is on record.

[EXACT] Measured in game on the same build with a logging test mod (2026-10-24, one server and one client on one machine): a `modded class ItemBase` overriding `EEItemLocationChanged(notnull InventoryLocation oldLoc, notnull InventoryLocation newLoc)` (`P:\scripts\3_game\entities\entityai.c:976`, ItemBase override `P:\scripts\4_world\entities\itembase.c:987`) printed one line per tested transfer, for each of these, driven by the client's own inventory calls (`PredictiveTakeEntityToHands`, `PredictiveTakeEntityToTargetCargo`, `PredictiveTakeEntityToTargetAttachment`) or by an action:

| Move | oldLoc → newLoc |
|---|---|
| crate cargo → hands, hands → crate cargo, crate → second crate | CARGO ↔ HANDS, CARGO → CARGO |
| SparkPlug out of / into a PowerGenerator lying on the ground | ATTACHMENT ↔ HANDS |
| WoodenPlank out of and into a `Land_House_1M1` slot `RB_LvL1_Plank` | ATTACHMENT ↔ HANDS |
| WoodenCrate picked up from the ground, then dropped | GROUND → HANDS, HANDS → GROUND |

- A take into hands that already held an item of the same type (a swap) printed two lines with the same script-log timestamp, one per item: the slot item to the hands and the hand item to the slot.
- The logger drops a callback before printing when both ends share a hierarchy root or neither end is a world object, so these lines bound what was printed, not how many callbacks the engine made.
- Items the server created in a container (`CreateInInventory`, `CreateAttachmentEx`) printed no line. For an item that is not itself a container, the logger prints nothing when `oldLoc` has no parent, the expected shape of a creation; a container picked up from the ground also has a parentless `oldLoc` and is printed as a pick-up. `oldLoc` itself was not printed.
- The player of a world-to-world move is not in either location. `g_Game.HasInventoryJuncture(Man player, EntityAI item)` (`P:\scripts\3_game\global\game.c:758`), called from inside `EEItemLocationChanged`, returned true for the player who made the crate-to-crate move (1 move measured). A move made without a juncture (server scripts) and two players near the crate were not measured.

[EXACT] Stacking moves quantity, not an item, and a split creates a new item, so neither is a move from one parent to another (read in the source; in the two combines below the logger printed no move line):
- The quantity of a combine moves in `ItemBase.CombineItems` (`P:\scripts\4_world\entities\itembase.c:2247-2270`). `Magazine.CombineItems` (`P:\scripts\4_world\entities\itembase\magazine\magazine.c:317`) overrides it without calling super, so ammo piles take another path.
- A split creates the new stack at its destination (read in the source, not measured for every path). The `ItemBase` split functions (`P:\scripts\4_world\entities\itembase.c:1584-1953`) mark the new item with `SetResultOfSplit(true)` (ten calls, `:1604` to `:1937`; definition `:2209`), except `SplitItem` (`:1953`): it creates the copy through `PlayerBase.CreateCopyOfItemInInventoryOrGroundEx` (`P:\scripts\4_world\entities\manbase\playerbase.c:6888-6899`), which marks it only when the copy lands on the ground, not when the player's cargo takes it (`CreateCopyOfItemInInventory`, `:6856`). `Magazine`'s own `SplitItemToInventoryLocation` and `SplitItem` (`P:\scripts\4_world\entities\itembase\magazine\magazine.c:231`, `:256`) do not call `SetResultOfSplit`. The server's item-manipulation handler calls them from `PlayerBase` (`P:\scripts\4_world\entities\manbase\playerbase.c:6640-6725`).
- Measured with a `modded class ItemBase` that wraps `CombineItems`, a `modded class Ammunition_Base` that wraps `CombineItems` (`Magazine` itself cannot be modded) and both reading the receiver's quantity before and after super: 10 rounds of `Ammo_762x39` stacked from the hands onto a pile in a crate, and 5 `WoodenPlank` stacked from the hands onto the plank in the `RB_LvL1_Plank` slot of a `Land_House_1M1`, each gave one line with the moved quantity. The server read the hands after each (`weapon_state`): the remaining rounds after the first, empty after the second.
- `SplitIntoStackMaxHands` (`P:\scripts\4_world\entities\itembase.c:1889`) does nothing when the whole stack fits in the hands (`ShouldSplitQuantity`): through that function, a split from a container to the hands only happens for a stack larger than the hand stack (1 observation: after a hand split of a whole `Ammo_762x39` pile the server read the hands empty). `SplitItemToInventoryLocation` (`:1917`) splits half towards an explicit destination instead.
- `[DESIGN]` For `SplitItem`, an audit compares the source quantity before and after super: the copy into the player's cargo carries no split mark. Not measured in game.

---

## 4. `[Obsolete]` takes → Target* variants

Until 1.29: `TakeEntityToCargo` / `ToCargoEx` / `AsAttachment` / `AsAttachmentEx`. Since 1.30 they are `[Obsolete]` wrappers (the block is `:1345-1386`).

```c
// [EXACT] P:\scripts\3_game\systems\inventory\inventory.c:1345
	[Obsolete("1.30: Use TakeEntityToTargetCargo instead")]
	bool TakeEntityToCargo(InventoryMode mode, notnull EntityAI item)
```

Same file: `TakeEntityToCargoEx` `[Obsolete]` `:1357`; `TakeEntityAsAttachmentEx` `[Obsolete]` `:1374` (attribute line is extra-indented in vanilla); `TakeEntityAsAttachment` `[Obsolete]` `:1382`.

Replacements: `TakeEntityToTargetCargo(mode, target, item)` `:1077`; `TakeEntityToTargetCargoEx(mode, cargo, item, row, col)` `:1084`; `TakeEntityAsTargetAttachmentEx(mode, target, item, slot)` `:1100`; `TakeEntityAsTargetAttachment(mode, target, item)` `:1142`. The identity test (`FindAttachment(slot) == item`, see "Scripted attach on a live player" in `api-patterns.md`) still applies.

---

## 5. Hand FSM guards

Until 1.29: `HandGuardCanMove` / `CanSwap` / `CanForceSwap` auto-passed `e.m_IsJuncture || e.m_IsRemote` (1.29 `hand_guards.c:299`, `:325`, `:351`). Since 1.30 only `e.m_IsRemote`; else `LocationCanMoveEntity` / `CanSwapEntitiesEx` / `CanForceSwapEntitiesEx`.

```c
// [EXACT] P:\scripts\3_game\systems\inventory\hand_guards.c:299
		bool result = e.m_IsRemote;
		if (result == false)
		{
			result = GameInventory.LocationCanMoveEntity(es.GetSrc(), es.GetDst());
		}
```

Same `m_IsRemote` test at `:325` and `:351`. New guard `HandGuardIsNotSurrendered` (`:405`) returns `!m_Player.IsSurrendered()` (`:412`). `[DESIGN]` Hand events on a surrendered player fail the FSM.

---

## 6. `GUIInventoryAttachmentsProps`, `TypeAttachmentGroupData`, `ItemBaseType`

```c
// [EXACT] P:\scripts\3_game\entities\typeattachmentgroupdataholders.c:39
		m_PropsPath = "" + pathBase + " GUIInventoryAttachmentsProps";
		if (!g_Game.ConfigIsExisting(m_PropsPath) || m_AttachmentGroupMap != null)
			return;
```

Category reach is a 1.5 m dome, vertical leeway `-range/5` (`P:\scripts\5_mission\gui\inventorynew\inherited\attachmentcategoriesrow.c:764`, default `range = 1.5` → −0.3 m).

`ItemBaseType` (`typedef ItemBaseType Inventory_BaseType`, `P:\scripts\4_world\entities\itembasetype.c:1-4`) caches type config. Keys re-opened: `varWetMax` `:71`, `headSelectionsToHide` `:105-108`, `hideSelectionsByinventorySlot` `:111-113`, `quickBarBonus` `:115`, `itemModelLength` / `itemAttachOffset` `:86-92`, `temperaturePerQuantityWeight` `:117-119`, `EnvironmentWetnessIncrements` Soaking/Drying `:121-137`, `compatibleLocks` / `lockType` `:96-99`. Rebuilding slots `Slot_RB_LvL*` from `P:\scripts\config.cpp:2915` (`Slot_RB_LvL1_Log`, `stackMax = 15`).

---

## 7. Action system 1.30

### 7.1 `CanBeStarted`, `IsTargetInfoAction`, `SortActions`, `InitInfoData`

```c
// [EXACT] P:\scripts\4_world\classes\useractionscomponent\actionbase.c:276
	//! Should we display additional info panel on ActionTargetsCursor
	bool IsTargetInfoAction()
	{
		return m_InfoData != null;
	}
```

```c
// [EXACT] P:\scripts\4_world\classes\useractionscomponent\actionbase.c:287
	//! If for some reason we want a non-performable action (like pure info ones)
	bool CanBeStarted()
	{
		return true;
	}
```

`InitInfoData()` is the empty hook (`P:\scripts\4_world\classes\useractionscomponent\actionbase.c:159-161`). Info-only construction: `P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionpartinfo.c:18-21` `override bool CanBeStarted() { return false; }`. Client does not `ActionStart` unless `CanBeStarted()` (`P:\scripts\4_world\classes\useractionscomponent\actionmanagerclient.c:336-337`).

```c
// [EXACT] P:\scripts\4_world\classes\useractionscomponent\actioninput.c:464
	//! sorts in order: performable -> non-performable (usually info). Extend/override as needed
	protected void SortActions(array<ActionBase> allActions)
```

### 7.2 Line drift: `PerformAction` / `Can()` / `UA_AM_*`

Until 1.29: `PerformAction` was `:756` inside `#ifdef BOT` `:754-760`, `PerformActionStart` `:762`, `ActionBase.Can` `:912`. Since 1.30:

```c
// [EXACT] P:\scripts\4_world\classes\useractionscomponent\actionmanagerclient.c:796
#ifdef BOT
	/// used for bots
	void PerformAction(int user_action_id, ActionTarget target, ItemBase item, Param extraData = NULL)
	{
		ActionStart(GetAction(user_action_id), target, item, extraData);
	}
#endif
	
	void PerformActionStart(ActionBase action, ActionTarget target, ItemBase item, Param extra_data = NULL)
```

In single player `PerformActionStart` does nothing while an action is pending or current (`:806-814`). `GetActionState()` returns `UA_AM_INIT` while pending (`:822-825`). `Can(PlayerBase, ActionTarget, ItemBase)` is at `P:\scripts\4_world\classes\useractionscomponent\actionbase.c:968`. Using public `Can` not protected `ActionCondition` is still the rule.

```c
// [EXACT] P:\scripts\3_game\constants.c:508
const int		UA_AM_INIT = 14;
const int		UA_AM_PENDING = 15;
const int		UA_AM_ACCEPTED = 16;
const int		UA_AM_REJECTED = 17;
```

Do not hardcode those integers (1.30 inserted `UA_AM_INIT`).

### 7.3 `ActionFillBottleBase` → `ActionObtainLiquidBase`

```c
// [EXACT] P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionfillbottlebase.c:28
[Obsolete("1.30: replaced by class ActionObtainLiquidBase")]
class ActionFillBottleBase: ActionContinuousBase
```

`RegisterActions` inserts `ActionObtainLiquidBase` (`P:\scripts\4_world\classes\useractionscomponent\actionconstructor.c:156`), not FillBottle. `P:\scripts\4_world\entities\itembase\edible_base\bottle_base.c:364` `AddAction(ActionObtainLiquidBase)`. Fill CCT:

```c
// [EXACT] P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionobtainliquidbase.c:56
		m_ConditionItem 	= new CCINonRuined();
		m_ConditionTarget 	= new CCTLiquid(m_AllowedLiquidMask, UAMaxDistances.DEFAULT, UAMaxDistances.DEFAULT);
```

`[DESIGN]` `modded ActionFillBottleBase` never instantiates.

### 7.4 Animation overrides on `EntityAI`

`ActionOverrideData` is at `P:\scripts\3_game\entities\entityai.c:103-108`. Map:

```c
// [EXACT] P:\scripts\3_game\entities\entityai.c:117
	static ref map<typename, ref TActionAnimOverrideMap> m_EntityActionOverrides = new map<typename, ref TActionAnimOverrideMap>; 
```

`OverrideActionAnimation(typename action, int commandUID, int stanceMask = -1, int commandUIDProne = -1)` at `:4781`. `AnimatedActionBase.GetCommandOverride` looks up item type then **target object type** (`P:\scripts\4_world\classes\useractionscomponent\animatedactionbase.c:284-290`). Until 1.29 this lived on `ItemBase.m_ItemActionOverrides` — that name is gone.

### 7.5 CCT: `CCTLiquid`, `CCTCursorInherited`, head distance

```c
// [EXACT] P:\scripts\4_world\classes\useractionscomponent\targetconditionscomponents\cctliquid.c:37
	void CCTLiquid(int allowedLiquidSource, float maximalTargetDistance = UAMaxDistances.DEFAULT, float maxVerticalReach = UAMaxDistances.DEFAULT, SurfaceDetectionType surfaceDetectionType = SurfaceDetectionType.Roadway, bool allowSeaLevelCursorFallback = false)
```

```c
// [EXACT] P:\scripts\4_world\classes\useractionscomponent\targetconditionscomponents\cctcursorinherited.c:28
				vector cursorHitPos = target.GetCursorHitPos();
				bool fromPlayerRoot = vector.DistanceSq(cursorHitPos, player.GetPosition()) <= m_MaximalActionDistanceSq;
				bool fromPlayerHead = vector.DistanceSq(cursorHitPos, MiscGameplayFunctions.GetPlayerHeadPosition(player)) <= m_MaximalActionDistanceSq;
```

`P:\scripts\4_world\classes\useractionscomponent\targetconditionscomponents\cctcursor.c:28-33` also uses `GetPlayerHeadPosition`. Stance height, not Head bone (`P:\scripts\4_world\static\miscgameplayfunctions.c:776-786`).

### 7.6 New inputs in `P:\bin\constants.xml`

```xml
// [EXACT] P:\bin\constants.xml:90
		<input name="UAToggleHeadlight" loc="TOGGLE_LIGHT_HEAD" />
		<input name="UAToggleVehicleLights" loc="TOGGLE_LIGHT_HEAD" />
```

Also `:282-285` `UABuldLinkCamToTerrain` / `UABuldCopyTileCoord` / `UABuldMarkUnderground` / `UABuldRemoveUnderground`; `:308-311` `UAUICodeLockLeft/Right/Up/Down`. `UACarHorn` remains `:203`. `[DESIGN]` Vehicle lights bind `UAToggleVehicleLights`, not `UAToggleHeadlight`.

### 7.7 Recipes

Until 1.29, `m_ResultReplacesIngredient` + `TransferItemProperties` could overwrite health from `m_ResultInheritsHealth`. Since 1.30 5th arg is `transfer_health = false`. Signature: `P:\scripts\4_world\static\miscgameplayfunctions.c:269`.

```c
// [EXACT] P:\scripts\4_world\classes\recipes\recipebase.c:353
						MiscGameplayFunctions.TransferItemProperties(ingr, res, true, true, false, false);
```

`GetRecipeClassName(int recipe_id)` is `P:\scripts\4_world\plugins\pluginbase\pluginrecipesmanager.c:84`.

### 7.8 `ActionTargetsCursor.Update(bool fullUpdate = true)`

Until 1.29 the vanilla method is `Update()`. Since 1.30 it is `Update(bool fullUpdate = true)`. A 1.29 override does not compile on 1.30: `Overloaded function 'Update' not compatible` (measured in game, DayZDiag 1.30 Exp). Gate the override on the version define (see `references/dayz-1-30-mod-workflow.md` in the `dayz-mod-workflow` skill):

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

---

## 8. Engine / proto API (`1_Core`, `3_Game`)

### 8.1 Third person

The third-person API is on `World`:

```c
// [EXACT] P:\scripts\3_game\global\world.c:177
	proto native ThirdPersonMode GetThirdPersonViewMode();
```

```c
// [EXACT] P:\scripts\3_game\global\world.c:291
	[Obsolete("1.30: replaced by World::GetThirdPersonViewMode returning current thrid person mode")]
	proto native bool Is3rdPersonDisabled();
```

```c
// [EXACT] P:\scripts\3_game\global\world.c:301
enum ThirdPersonMode
{
	DISABLED,
	ENABLED,
	VEHICLES_ONLY
```

`[DESIGN]` Compare to `ThirdPersonMode.ENABLED` (or `VEHICLES_ONLY`). Vanilla typo `thrid` is in the `[Obsolete]` string.

### 8.2 Weather noise — not deleted

`GetNoiseReductionByWeather` was not removed: both methods exist. No-Ex is `[Obsolete]` → Ex; Ex is `[Obsolete]` "Kept for HUD and old mods" because AI damping is native AIParams. Vanilla still calls Ex (`P:\scripts\4_world\static\sensesaievaluate.c:23`, class `NoiseAIEvaluate`).

```c
// [EXACT] P:\scripts\3_game\weather.c:407
	[Obsolete("1.30: AI noise dampening is now done natively via AIParams config parameters. Kept for HUD and old mods.")]
	float GetNoiseReductionByWeatherEx(notnull Object object)
```

```c
// [EXACT] P:\scripts\3_game\weather.c:454
	[Obsolete("Use Weather.GetNoiseReductionByWeatherEx instead!")]
	float GetNoiseReductionByWeather()
```

### 8.3 `vector.Cross`, `array.Slice`, `EnumFlagsToString`


**1.30.164200 stable removed `vector.Cross`.** The method below is in 1.30.164014 Exp and 1.30.164078 (`P:\scripts\1_core\proto\enconvert.c:239-246`), and in no script file of 1.30.164200 (1.29 did not have it either). On 1.30.164200 a mod that calls `v.Cross(w)` has nothing to call: write the three lines of the body inline.

```c
// [EXACT] P:\scripts\1_core\proto\enconvert.c:239 (1.30.164014 and 1.30.164078 only)
	vector Cross(vector v)
	{
    	float x = value[1] * v[2] - value[2] * v[1];
    	float y = value[2] * v[0] - value[0] * v[2];
    	float z = value[0] * v[1] - value[1] * v[0];

    	return Vector(x, y, z);
	}
```

```c
// [EXACT] P:\scripts\1_core\proto\enscript.c:720
	array<T> Slice(int from, int to)
	{
	    array<T> result = new array<T>();
		for (int i = from; i <= to && i < Count(); ++i)
	        result.Insert(Get(i));

	    return result;
	}
```

`to` is inclusive. `typename.EnumFlagsToString` `P:\scripts\1_core\proto\enconvert.c:614`; `Enum.EnumFlagsToString` `:704` forwards.

### 8.4 `DoOnce`, `IsFirstRenderFrame`, `DisableSimulation`

```c
// [EXACT] P:\scripts\3_game\doonce.c:1
class DoOnce
{
    protected static ref map<string, bool> m_Done;
```

`DoOnce.Run(string key, Class target, string fnName, Param params = null)` (`:12`) calls `g_Game.GameScript.CallFunctionParams` once per key (`:21-27`).

```c
// [EXACT] P:\scripts\3_game\dayzplayer.c:1186
	//! Returns true if this is the first tick of the render frame.
	//! If the client FPS is below 30fps, the player could tick multiple times in one render frame, some systems don't 
	//! need to be processed on the client again if it has no visible effect to the screen or server simulation.
	proto native bool IsFirstRenderFrame();
```

```c
// [EXACT] P:\scripts\3_game\entities\entity.c:3
	proto native void DisableSimulation(bool disable);

	//! Returns whether simulation is disabled
	proto native bool GetIsSimulationDisabled();
```

---

## What breaks for a 1.29 mod

1. `override OnCEUpdate` — obsolete; CE work may never run → `OnCEIterate`.
2. `modded DayZPlayerInventory.ProcessInputData` — not called in retail, and on 1.30.164200 `modded class DayZPlayerInventory` does not compile at all (§3.2). To observe completed item moves, hook `ItemBase.EEItemLocationChanged`; a replacement for intercepting or rejecting inventory commands is not established.
3. `TakeEntityToCargo*` / `TakeEntityAsAttachment*` — obsolete → Target*.
4. `ActionFillBottleBase` — obsolete and **absent** from `RegisterActions` → `ActionObtainLiquidBase`.
5. `ItemBase.m_ItemActionOverrides` — compile error → `EntityAI.OverrideActionAnimation`.
6. `World.Is3rdPersonDisabled()` — obsolete; `VEHICLES_ONLY` is not a bool.
7. Hardcoded `UA_AM_*` ints — `UA_AM_INIT=14` shifted later values.
8. Hand takes on surrendered players — `HandGuardIsNotSurrendered` rejects.
9. `GetNoiseReductionByWeather()` — still compiles (obsolete). AI damping is native; HUD uses `GetNoiseReductionByWeatherEx(object)`.
10. `GAME_STORAGE_VERSION` 142 → 144. Recipe replace no longer copies ingredient health. Drink/fill CCT is `CCTLiquid`, not `CCTWaterSurfaceEx`.
11. `override void Update()` on `ActionTargetsCursor` — compile error; 1.30 takes `Update(bool fullUpdate = true)`.

## Migration checklist

- [ ] `OnCEIterate(currentTime, elapsedTime)` + `super`. Inventory: Validate + Execute* (not `ProcessInputData`).
- [ ] Target* takes. `AddAction(ActionObtainLiquidBase)`. `EntityAI.OverrideActionAnimation` (item and target).
- [ ] Info actions: `InitInfoData` + `CanBeStarted()==false`. `new CCTLiquid(mask, ...)`. `GetPlayerHeadPosition`.
- [ ] `GetThirdPersonViewMode() == ThirdPersonMode.ENABLED`. Weather HUD: `GetNoiseReductionByWeatherEx(object)`.
- [ ] No `vector.Cross` on 1.30.164200 (inline it). `array.Slice` / `EnumFlagsToString`. Client catch-up: `IsFirstRenderFrame()`. Storage `144`.
- [ ] Recipes with `m_ResultReplacesIngredient`: set `m_ResultInheritsHealth`. Bind `UAToggleVehicleLights` / `UAUICodeLock*`. Never hardcode `UA_AM_*`.
