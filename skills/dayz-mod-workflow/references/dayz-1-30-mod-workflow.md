# DayZ 1.30: what changed for the implementation workflow

What 1.30 changed in the contracts `dayz-mod-workflow` checks: the action start gate, Central Economy root classes, `cfggameplay.json`, the underground trigger editor, night-vision type switches and the headless guards. The six-layer debug order, the offline gates and the sync variable rules still hold.

Every excerpt below was read in the vanilla files on `P:\`. The data on `P:\` when this was checked is a 1.30 build from before 1.30.164200 (game storage version 144); where a line is about 1.30.164200 or later and `P:\` shows something else, the line says so and is marked not yet checked on `P:\`.

Marks: `[EXACT]` copied from the cited vanilla file; `[DESIGN]` a recommendation.

## Action pipeline: `CanBeStarted` and `CCTLiquid`

Until 1.29, `Can()` (target condition, item condition, `ActionCondition`) was treated as the whole client start gate: a listed action was assumed startable. Since 1.30 the widget can still show an action whose `CanBeStarted()` is false; the client manager then does not call `ActionStart`. The 1.29 side is not on `P:\`, so it is not yet checked on `P:\`.

```c
// [EXACT] P:\scripts\4_world\classes\useractionscomponent\actionbase.c:276-291
	//! Should we display additional info panel on ActionTargetsCursor
	bool IsTargetInfoAction()
	{
		return m_InfoData != null;
	}
	
	ActionInfoDataBase GetClientActionInfo()
	{
		return m_InfoData;
	}
	
	//! If for some reason we want a non-performable action (like pure info ones)
	bool CanBeStarted()
	{
		return true;
	}
```

The client start guard:

```c
// [EXACT] P:\scripts\4_world\classes\useractionscomponent\actionmanagerclient.c:333-340
					if (ain.JustActivate())
					{
						ActionBase action = ain.GetAction();
						if (action && action.CanBeStarted())
						{
							ActionStart(action, ain.GetUsedActionTarget(), ain.GetUsedMainItem());
							break;
						}
```

An info-only override (the widget shows, F does nothing):

```c
// [EXACT] P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionpartinfo.c:18-21
	override bool CanBeStarted()
	{
		return false;
	}
```

Vanilla water, wash and fill actions no longer use `CCTWaterSurfaceEx` at the wash-hands pond action. `ActionWashHandsWater` builds a `CCTLiquid`:

```c
// [EXACT] P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionwashhandswater.c:25-29
	override void CreateConditionComponents()
	{		
		m_ConditionItem		= new CCINone();
		m_ConditionTarget 	= new CCTLiquid(LIQUID_GROUP_WATER - LIQUID_SNOW - LIQUID_HOTWATER, UAMaxDistances.DEFAULT, UAMaxDistances.DEFAULT);
	}
```

[DESIGN] Copy `CCTLiquid` for a custom drink, wash or fill action on sea or pond; keep `CCTWaterSurfaceEx` only when you mean to differ from vanilla. A listed action that never starts is often `CanBeStarted() == false`, not a broken target condition.

`ActionFillBottleBase` carries `[Obsolete("1.30: replaced by class ActionObtainLiquidBase")]` (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionfillbottlebase.c:28-29`). For the workflow that means: do not `modded class` an obsolete vanilla action that `ActionConstructor` no longer registers. The domain detail is in `skills/_shared/enscript/depth/` and `skills/_shared/persistence/base-building-1-30.md`.

## Central Economy root classes: `MotorbikeScript` and `HouseDestructible`

Since 1.30, `cfgeconomycore.xml` on Chernarus, Livonia and Sakhal has two more root classes (that 1.29 lacked them is not yet checked on `P:\`, which holds no 1.29 data):

```xml
<!-- [EXACT] P:\DZ\worlds\chernarusplus\ce\cfgeconomycore.xml:15-18 -->
		<rootclass name="CarScript" act="car" reportMemoryLOD="no" /> <!-- cars (sedan, hatchback, transitBus, V3S, ...) -->
		<rootclass name="BoatScript" act="car" reportMemoryLOD="no" /> <!-- boats -->
		<rootclass name="MotorbikeScript" act="car" reportMemoryLOD="no" /> <!-- Motorbike -->
		<rootclass name="HouseDestructible" reportMemoryLOD="no" /> <!-- houses, wrecks -->
```

The same pair is at `P:\DZ\worlds\enoch\ce\cfgeconomycore.xml:17-18` (`MotorbikeScript`, `HouseDestructible`) and at `P:\DZ\worlds\sakhal\ce\cfgeconomycore.xml:17-18` (`MotorbikeScript`, `HouseDestructible`).

[DESIGN] A custom map whose Central Economy files leave out `MotorbikeScript` will not economy-spawn motorbikes; leaving out `HouseDestructible` drops Central Economy coverage of destructible houses. `act="car"` on `MotorbikeScript` matches boats and cars (movable vehicles).

## `cfggameplay.json`: new members

Since 1.30, `CfgGameplayJson` has `ExternalLockData` and `SandstormData`; `ITEM_GeneralData` has `disableBaseDecay`; `ITEM_VehicleData` has the wheel detach and damage flags. That 1.29 lacked them is not yet checked on `P:\`, which holds no 1.29 data.

```c
// [EXACT] P:\scripts\3_game\cfggameplaydatajson.c:14-23
	//!!! all member variables must correspond with the cfggameplay.json file contents !!!!
	ref ITEM_GeneralData GeneralData			= new ITEM_GeneralData;
	ref ITEM_PlayerData PlayerData 				= new ITEM_PlayerData;
	ref ITEM_WorldData WorldsData 				= new ITEM_WorldData;
	ref ITEM_BaseBuildingData BaseBuildingData 	= new ITEM_BaseBuildingData;
	ref ITEM_UIData UIData 						= new ITEM_UIData;
	ref ITEM_MapData MapData 					= new ITEM_MapData;
	ref ITEM_VehicleData VehicleData 			= new ITEM_VehicleData;
	ref ITEM_ExternalLockData ExternalLockData 	= new ITEM_ExternalLockData;
	ref ITEM_SandstormData SandstormData        = new ITEM_SandstormData;
```

```c
// [EXACT] P:\scripts\3_game\cfggameplaydatajson.c:59-63
	bool disableBaseDamage;
	bool disableBaseDecay;
	bool disableContainerDamage;
	bool disableRespawnDialog;
	bool disableRespawnInUnconsciousness;
```

```c
// [EXACT] P:\scripts\3_game\cfggameplaydatajson.c:414-418
	float boatDecayMultiplier = 1;
	bool canDetachAttachedCarWheels = true;
	bool canDamageAttachedCarWheels = true;
	bool canDetachAttachedBikeWheels = true;
	bool canDamageAttachedBikeWheels = true;
```

`ITEM_ExternalLockData` holds `protectionCountStageOne`, `protectionCountStageTwo`, `protectionTime` and `protectionResetTime` (`P:\scripts\3_game\cfggameplaydatajson.c:434-437`). `ITEM_SandstormData` holds `sandstormFrequency` (`P:\scripts\3_game\cfggameplaydatajson.c:458`).

`InitServer` has the `disableBaseDecay` line commented out (`P:\scripts\3_game\cfggameplaydatajson.c:48`): the JSON member exists, but the bridge from the server config integer is not wired in this build.

## Underground trigger editor (`PluginUndergroundTriggerManager`)

Since 1.30 there is an in-game editor for underground triggers, on diag builds only: the whole file is inside `#ifdef DIAG_DEVELOPER`, and the class `PluginUndergroundTriggerManager` starts at `P:\scripts\4_world\plugins\pluginbase\pluginundergroundtriggermanager.c:1-3`. That 1.29 had no such editor is not yet checked on `P:\`, which holds no 1.29 data. Its key binds:

```c
// [EXACT] P:\scripts\4_world\plugins\pluginbase\pluginkeybinding.c:55-56
		RegisterKeyBind(	 MENU_NONE|MENU_UNDERGROUND_TRIGGER_EDITOR	,KeyCode.KC_LCONTROL	,KeyCode.KC_SLASH		,"PluginUndergroundTriggerManager"		,"EditorToggle"			,"[LCTRL]+[/]"			,"Show/Hide Underground Trigger Editor");
		RegisterKeyBind(	 MENU_NONE|MENU_UNDERGROUND_TRIGGER_EDITOR	,KeyCode.KC_F	,-1		,"PluginUndergroundTriggerManager"		,"FocusOnObject"		,"[F]"							,"Focus on selected object");
```

[DESIGN] For level design of underground volumes, use this editor on DayZDiag instead of hand-editing trigger configs blind. It does not exist in retail.

The trigger JSON schema, the 4096-trigger limit, triggers tied to Object Spawner objects, the underground presence sync and terrain holes are in the world pack: `skills/_shared/world/underground-triggers.md`, `underground-presence.md` and `terrain-holes.md`.

## `NVTypes`: environment variants (custom cameras)

Until 1.29, `NVTypes` ended at the optics and pumpkin night variants (1.29 is not on `P:\`, so that half is not yet checked on `P:\`). Since 1.30 it has underground and sandstorm variants, and a `switch` over the enum that is not exhaustive misses them. On `P:\`:

```c
// [EXACT] P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercamera_base.c:54-78
enum NVTypes
{
	NONE = 0,
	NV_GOGGLES,
	NV_GOGGLES_2D,
	NV_GOGGLES_OFF,
	NV_OPTICS_ON,
	NV_OPTICS_OFF,
	NV_PUMPKIN,
	NV_OPTICS_KAZUAR_DAY,
	NV_OPTICS_KAZUAR_NIGHT,
	NV_OPTICS_STARLIGHT_DAY,
	NV_OPTICS_STARLIGHT_NIGHT,
	
	// ---- Optics condition variants ----
	NV_OPTICS_UNDERGROUND,
	NV_OPTICS_SANDSTORM_DAY,
	NV_OPTICS_SANDSTORM_NIGHT,
	NV_OPTICS_UNDERGROUND_SANDSTORM,
	
	// ---- Glasses/goggles condition variants ----
	NV_GOGGLES_DAY,
	NV_GOGGLES_UNDERGROUND,
	NV_GOGGLES_SANDSTORM,
	NV_GOGGLES_UNDERGROUND_SANDSTORM,
```

Not yet checked on `P:\` (the data here predates it): the 1.30.164200 stable file is reported to have two more values in the middle of the list, `NV_OPTICS_UNDERGROUND_DAY` right after `NV_OPTICS_UNDERGROUND` and `NV_OPTICS_UNDERGROUND_SANDSTORM_DAY` right after `NV_OPTICS_UNDERGROUND_SANDSTORM`, so every value after `NV_OPTICS_UNDERGROUND` has a different number than on the earlier 1.30 builds. The two listings agree on the rule: never store or compare an `NVTypes` value as an `int`.

[DESIGN] Custom night-vision cameras: handle the new values, or call vanilla `ResolveNVType` (used at `P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercameraironsights.c:272`) instead of applying the raw type directly. Camera detail is in `skills/_shared/enscript/depth/`.

## Headless and dedicated guards

Since 1.30, `CGame` has `IsHeadless()` and `IsHeadlessOrDedicatedServer()`. The 1.29 `Game.c` is reported to have neither (1.29 is not on `P:\`, so that half is not yet checked on `P:\`).

```c
// [EXACT] P:\scripts\3_game\global\game.c:1125-1136
	proto native bool		IsDedicatedServer();
	
	/**
	 \brief Check whether the application is headless or not (applies to both server and headless roboclients or anything else that is headless)
	*/
	proto native bool		IsHeadless();
	
	/**
	 \brief Check whether the application is headless or a dedicated server (it combines IsDedicatedServer and IsHeadless)
		\note This includes servers with a head as well (-headlessMode=0)
	*/
	proto native bool		IsHeadlessOrDedicatedServer();
```

Until 1.29, code that skipped particles or sounds on a server tested `IsDedicatedServer()` or `IsServer()` (not yet checked on `P:\`, which holds no 1.29 data). Since 1.30 vanilla skips client effects with `!g_Game.IsHeadlessOrDedicatedServer()`, so headless roboclients are treated like servers. For "skip the effect", prefer the combined helper so headless roboclients do not run particles. Which call to use as the side guard for authority work is a separate rule: `skills/_shared/conventions/scripts.md`, "Which code runs where".

Counted on `P:\`: vanilla calls `IsHeadlessOrDedicatedServer()` 97 times and `IsHeadless()` on its own never (the same numbers were counted on 1.30.164014). Measured on that build: the script log lists `DAYZ_1_30` among the defines, where 1.29 logged `DAYZ_1_29`. A mod that must compile on both can gate the new helper on the version define, which names only the current version (`DAYZ_X_XX`, `P:\scripts\1_core\defines.c:12-14`). 1.29 vanilla is reported to gate the same way in its `DynamicMusicPlayerRegistry.c` (not on `P:\`).

```c
// [DESIGN] not compiled; 1.29 has no IsHeadlessOrDedicatedServer
static bool MyMod_IsHeadlessOrDedicated()
{
#ifdef DAYZ_1_29
	return g_Game.IsDedicatedServer();
#else
	return g_Game.IsHeadlessOrDedicatedServer();
#endif
}
```

By their documented meaning (the `game.c` excerpt above) both guards agree on a rendered client and on a dedicated server and differ only on a headless client; that is inferred, not measured. Measured on the public DayZDiag 1.30.164014, client and server: `ROBOCLIENT` and `INPUT_OVERRIDE` are defined, so code under `#ifdef ROBOCLIENT` (vanilla has such blocks, `P:\scripts\3_game\dayzgame.c:972`) compiles for everyone on that exe and every `PlayerBase` carries an idle `m_Bot`. Details: `skills/dayz-launch-test/references/dayz-1-30.md`, "Roboclients vs server-side dummy bots".

## Migration checklist

1. Action mods: implement `CanBeStarted`; do not treat a visible widget as startable. Water actions: `CCTLiquid`.
2. Custom Central Economy files: add the `MotorbikeScript` and `HouseDestructible` root classes.
3. Mission `cfggameplay.json`: merge the new keys; do not assume `disableBaseDecay` is wired from the server config (the `InitServer` line is commented out).
4. Exhaustive `NVTypes` switches: add the underground and sandstorm cases.
5. Effects that must not run on roboclients: `IsHeadlessOrDedicatedServer()`.
