# Heat stroke and cooling

How sustained heat turns into heat stroke: the thermal bias value, what feeds and drains it, the four heat stroke phases, washing the head, shade and sun, and wind on a motorbike or boat. Where a later 1.30 update changes a value, the line says so and is not checked on `P:\`.

## The thermal bias handler

`PlayerBase` owns one `ThermalBiasHandler`, declared as `m_ThermalBiasHandler` (`P:\scripts\4_world\entities\manbase\playerbase.c:339`) and created in the constructor (`playerbase.c:426`). The value itself is the player stat `EPlayerStats_current.THERMAL_BIAS` (`P:\scripts\4_world\classes\thermalbiashandler.c:16`).

`Add` does nothing while `m_TemporaryResistanceTime` is above 0, for positive and negative values alike (`thermalbiashandler.c:40` to `:48`). `OnTick` counts that time down (`:21` to `:29`).

The handler saves one float. From `P:\scripts\4_world\classes\thermalbiashandler.c:67`:

```c
    void OnStoreSave(ParamsWriteContext ctx)
    {
        ctx.Write(m_TemporaryResistanceTime);
    }

    bool OnStoreLoad(ParamsReadContext ctx, int version)
    {
        if (!ctx.Read(m_TemporaryResistanceTime))
            return false;

        return true;
    }
```

`PlayerBase.OnStoreSave` writes it last, with `m_ThermalBiasHandler.OnStoreSave(ctx)` (`playerbase.c:7395`), and `PlayerBase.OnStoreLoad` reads it back with `m_ThermalBiasHandler.OnStoreLoad(ctx, version)` (`playerbase.c:7520`). A `modded class PlayerBase` that saves its own data calls `super.OnStoreSave` and `super.OnStoreLoad` first and reads in the order it writes; the rules are in `_shared/persistence/save-load-contract.md`.

## What feeds the bias

`HeatComfortMdfr` no longer takes health for heat. The hot side of its tick only feeds the bias; the cold side still takes health with `AddHealth` (`P:\scripts\4_world\classes\playermodifiers\modifiers\heatcomfortmdfr.c:62` to `:71`).

From `heatcomfortmdfr.c:74`:

```c
		//! Thermal Bias value feeding (based on HeatStroke stages)	
		if (heatComfortValue > PlayerConstants.THRESHOLD_HEAT_COMFORT_PLUS_EMPTY)
		{
			thermalBiasHandler.Add(PlayerConstants.THERMAL_BIAS_POSITIVE_HC_HIGH_INCREMENT * deltaT);
		}
		else if (heatComfortValue > PlayerConstants.THRESHOLD_HEAT_COMFORT_PLUS_CRITICAL)
		{
			thermalBiasHandler.Add(PlayerConstants.THERMAL_BIAS_POSITIVE_HC_MEDIUM_INCREMENT * deltaT);
		}
```

A second block then depends on water (`heatcomfortmdfr.c:84` to `:111`):

| Heat comfort | Water, player conscious | Bias change per second |
|---|---|---|
| above `THRESHOLD_HEAT_COMFORT_PLUS_WARNING` | below `SL_WATER_NORMAL` | plus HIGH when the bias is above 0.85, MEDIUM from 0.6, otherwise LOW (`:86` to `:94`) |
| above `THRESHOLD_HEAT_COMFORT_PLUS_WARNING` | below `SL_WATER_HIGH` | plus LOW while the bias is below 0.4, otherwise minus `THERMAL_BIAS_POSITIVE_HC_DECREMENT` (`:95` to `:103`) |
| at or below it | any | minus `THERMAL_BIAS_POSITIVE_HC_DECREMENT`; once the bias reaches 0 it is held at 0 (`:105` to `:111`) |

The constants (`P:\scripts\3_game\playerconstants.c:203` to `:210`):

| Constant | On `P:\` | Later 1.30 update, not checked on `P:\` |
|---|---|---|
| `THERMAL_BIAS_WASH_HEAD_DECREMENT` | 0.175 | same |
| `THERMAL_BIAS_WASH_HEAD_TEMPORARY_RESISTANCE_TIME` | 30.0 s | same |
| `THERMAL_BIAS_POSITIVE_HC_DECREMENT` | 0.0001 | 0.0002 |
| `THERMAL_BIAS_POSITIVE_HC_LOW_INCREMENT` | 0.00022 | 0.0002 |
| `THERMAL_BIAS_POSITIVE_HC_MEDIUM_INCREMENT` | 0.00032 | same |
| `THERMAL_BIAS_POSITIVE_HC_HIGH_INCREMENT` | 0.00050 | same |

In the later 1.30 update (not checked on `P:\`), above the warning threshold a player with water at or above `SL_WATER_HIGH` and heat comfort at or below `THRESHOLD_HEAT_COMFORT_PLUS_CRITICAL` loses bias through a new `RecoverThermalBias` method. A conscious player with water between `SL_WATER_NORMAL` and `SL_WATER_HIGH` gains bias below 0.38 (0.4 minus a new `STAGE_DEACTIVATION_BUFFER` of 0.02) and loses it from there up. That holds the bias near 0.38 only while heat comfort stays at or below the critical threshold. Above it the first block adds 0.00032 or 0.0005 per second, more than the 0.0002 taken off, so the bias still rises.

## The four heat stroke phases

From `P:\scripts\4_world\classes\playermodifiers\modifiers\diseases\heatstroke.c:3`:

```c
	const int NUMBER_OF_STAGES = 4;
	const float STAGE_THRESHOLDS[NUMBER_OF_STAGES] = {0.0, 0.4, 0.6, 0.85};
```

The modifier IDs are `MDF_HEAT_STROKE1` to `MDF_HEAT_STROKE4` (`P:\scripts\4_world\classes\playermodifiers\emodifiers.c:66` to `:69`), and all four share the sync bit `MODIFIER_SYNC_HEAT_STROKE` (`P:\scripts\4_world\classes\playermodifiers\modifiersmanager.c:12`). Each phase reads `GetThermalBiasHandler().Get()` in its `ActivateCondition` (phase 1: `heatstroke.c:58` to `:61`). Phases stack: at a bias of 0.9 all four run.

| Phase | Active while the bias is | What it does |
|---|---|---|
| 1, `HeatStrokePhase1Mdfr` (`heatstroke.c:42`) | above 0.0 | Ticks `waterStat.Add(-WATER_DRAIN_FROM_FEVER_ST1 * deltaT)` (`:80`). `OnActivate` is empty; `OnDeactivate` calls `DecreaseDiseaseCount` (`:68` to `:75`). |
| 2, `HeatStrokePhase2Mdfr` (`:84`) | above 0.4; off at or below 0.4 (`:105` to `:108`) | `OnActivate` adds `SYMPTOM_FEVERBLUR`, stamina modifier `DISEASE_PNEUMONIA` and `IncreaseDiseaseCount` (`:110` to `:116`). `OnDeactivate` removes the symptom and the stamina modifier but does not decrement (`:118` to `:123`). The tick adds random `SYMPTOM_HOT` and drains water by `WATER_DRAIN_FROM_FEVER_ST2` (`:125` to `:136`). |
| 3, `HeatStrokePhase3Mdfr` (`:140`) | above 0.6; off below 0.6, using `<` not `<=` (`:164` to `:167`) | The vanilla comment says it stays active together with phase 4 (`:139`). Drains water by `WATER_DRAIN_FROM_FEVER_ST3` (`:190`). Random `SYMPTOM_VOMIT` that takes 70 water and 55 energy, then the `VOMIT_EXHAUSTION` stamina modifier (`:186` to `:216`). `OnReconnect` runs `OnActivate` again (`:175` to `:178`). |
| 4, `HeatStrokePhase4Mdfr` (`:233`) | above 0.85 | Health loss per second remapped from `HEALTH_DAMAGE_MIN` 0.01 to `HEALTH_DAMAGE_MAX` 0.35 between bias 0.85 and 1.0, through `AddHealth` (`:27`, `:28`, `:308` and `:309`). `SYMPTOM_FAINT` (`:275`). With a bias above 0.75 and shock above 90, unconsciousness for 5 to 10 s every 60 to 120 s, with shock set to 25 (`:19` to `:24`, `:369` to `:383`). |

The three water drain constants are declared `protected static const int` with the values 0.35, 0.5 and 0.75 (`heatstroke.c:7` to `:9`). An `int` truncates each to 0, so no phase drains any water. A mod that wants the drain redeclares them as `float`.

In the later 1.30 update (not checked on `P:\`): `HEALTH_DAMAGE_MAX` is 0.15; phase 2 turns off below 0.38 and runs `OnActivate` again in `OnReconnect`; phase 1's `OnDeactivate` is empty and phase 2's `OnDeactivate` calls `DecreaseDiseaseCount`.

## The sickness icon can stay wrong

On `P:\` the only `IncreaseDiseaseCount` is in phase 2's `OnActivate` and the only `DecreaseDiseaseCount` is in phase 1's `OnDeactivate`. The count balances only when phase 2 activates exactly once per phase 1 episode: phase 1 alone nets minus 1, and each further phase 2 activation nets plus 1. `ImmuneSystemMdfr` refreshes the sick notifier only when `HasDisease()` changes (`P:\scripts\4_world\classes\playermodifiers\modifiers\immunesystem.c:44` to `:55`; `HasDisease` is at `playerbase.c:1119`), so the icon can stay on or never come back. The later 1.30 update fixes this (not checked on `P:\`). When you mod the phases, keep each `IncreaseDiseaseCount` and its `DecreaseDiseaseCount` in the same phase.

## Washing the head and wet clothing

`ActionWashHeadWettingClothesBase.OnFinishProgressServer` (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionwashheadwettingclothesbase.c:49` to `:57`) does three things:

- `ReduceAgent(eAgents.EYES_IRRITATION, GetEyeIrritationReduction())`, which is 10 by default (`actionwashheadwettingclothesbase.c:46`) and 1.6 from a bottle (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionwashheaditemcontinuous.c:41`).
- `Add(-PlayerConstants.THERMAL_BIAS_WASH_HEAD_DECREMENT)`, then `SetTemporaryResistance` for 30 s. Both run on every wash. Because `Add` is ignored while resistance runs, a second wash inside the 30 s does not lower the bias, but it restarts the 30 s.
- `ApplyWetnessToClothes`, with one wetness table for a container (`s_WetnessContainer`) and one for a water surface (`s_WetnessSurface`) (`actionwashheadwettingclothesbase.c:10` to `:43`).

A wash stopped early applies the same three scaled by progress in `OnEndServer`, without the resistance (`:59` to `:67`).

In the later 1.30 update (not checked on `P:\`), the bias drop and the resistance happen only when `GetTemporaryResistance()` is 0, so a second wash inside the 30 s no longer restarts them; the irritation drop and the wetting still happen.

`ActionWashHeadItemContinuous.ActionCondition` accepts any liquid except gasoline (`actionwashheaditemcontinuous.c:32` to `:39`) and has no `IsFrozen()` check, so a frozen bottle still washes; the 1.30 changelog lists this as a known issue.

`ActionWetClothingInHandsBase` wets the item in hands with `SetWet` and takes off bias in proportion to the wetness gained, `m_WetGainPerStep` (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionwetclothinginhandsbase.c:44` and `:45`).

## Shade and sun

- The shade check runs every `ENVIRO_TICK_SHADOW_RC_CHECK`, 30 s (`P:\scripts\3_game\constants.c:760`), not every 5 s. The timer is in `P:\scripts\4_world\classes\environment\environment.c:406` to `:415`: inside a building the result is true at once, otherwise `CheckShadowPresence` runs.
- `IsInShadow()` returns the stored result (`environment.c:519`).
- `CheckShadowPresence` (`environment.c:665` to `:720`): being inside, under a roof or in a `Car` gives shade without a cast. Otherwise it sweeps a capsule 50 m long with a 0.05 m radius from the head toward `-GetSunOrMoonDirection()` against `ITEM_LARGE`, `BUILDING`, `VEHICLE`, `TERRAIN` and `ROADWAY`, with `DayZPhysics.CapsuleOverlapBullet` (`:680` to `:719`).
- Out of shade, temperature gains `GetSunEffectOnTemperature(m_DayTime) * HeadGearProtectionAgainstSun()`, but only when the world's `m_TemperatureUnderSunModifier` map has the current time of day (`environment.c:868` to `:872`). `GetSunEffectOnTemperature` scales the map value by overcast (`P:\scripts\3_game\worlddata.c:355` to `:360`).
- Only Nasdara fills that map: `DAWN` 2, `MORNING` 6, `NOON` 8, `AFTERNOON` 4, `EVENING` 2, `DUSK` 0, `NIGHT` 0 (`P:\scripts\4_world\classes\worlds\nasdara.c:67` to `:73`). `ChernarusPlusData.Init` does not write it (`P:\scripts\4_world\classes\worlds\chernarusplus.c:31`), so Chernarus has no sun effect. A custom world that wants sunstroke fills the map in its own world data class.
- `HeadGearProtectionAgainstSun` (`environment.c:2037` to `:2065`): with headgear it returns the item's heat isolation times `HC_EXPOSED_HEAD_TO_SUN` (1.2, `environment.c:79`) plus 0.4; with none it returns 1.2. The loop returns the exposed value at the first clothing attachment that is not in the `HEADGEAR` slot, so the result depends on attachment order.

## Wind on a motorbike or boat

`DetermineHeatcomfortBehavior` (`P:\scripts\4_world\classes\environment\environment.c:575` to `:627`) picks one of three cases: a `Car` with the engine on, a `Motorbike` faster than `ENVIRO_HEATCOMFORT_MOTORBIKE_SPEED_MIN` (20, `P:\scripts\3_game\constants.c:792`), or a `Boat` faster than `ENVIRO_HEATCOMFORT_BOAT_SPEED_MIN` (15, `constants.c:797`).

`SetHeatcomfortDirectly` (`environment.c:1369`) then sets heat comfort itself. In a car with the engine on the target is 0. On a motorbike or boat it subtracts `Easing.EaseInCubic(normalizedSpeed)` times a maximum of 0.8, minus the vehicle's `GetHeatComfortOverride()` (`:1403` to `:1406` and `:1431`). `BoatScript.GetHeatComfortOverride` returns `m_HeatComfortOverride` (`P:\scripts\4_world\entities\vehicles\boatscript.c:256`), which starts at 0.0 (`boatscript.c:108`); `MotorbikeScript` has the same getter (`P:\scripts\4_world\entities\vehicles\motorbikescript.c:164`).

A motorbike and a boat cool the rider through wind, but they are neither shade nor sandstorm shelter (`sandstorm.md`).

## Porting a 1.29 heat mod

A 1.29 mod that trims heat damage in `HeatComfortMdfr` does nothing on 1.30, and the player still dies in phase 4. The hot tick only feeds the bias (`heatcomfortmdfr.c:74` to `:82`); the health loss is the `AddHealth` in phase 4 (`heatstroke.c:308` and `:309`). Balance `PlayerConstants.THERMAL_BIAS_*` (`playerconstants.c:203` to `:210`) or the phases instead, and never hang new heat damage on `HeatComfortMdfr`.

## Checking it in game

On a local test server from `/dayz-launch-test`:

- Heat: sustained high heat comfort raises the thermal bias and turns on `MDF_HEAT_STROKE1` to `MDF_HEAT_STROKE4` in turn.
- Washing the head removes 10 `EYES_IRRITATION` agents (1.6 from a bottle) and gives 30 s of resistance.
- Shade: time shade tests against the 30 s tick, not 5 s.
- Logs: search the RPT for `ThermalBiasHandler`. `PlayerBase` prints "failed to load ThermalBiasHandler" when the save stream is out of order (`playerbase.c:7522`).
