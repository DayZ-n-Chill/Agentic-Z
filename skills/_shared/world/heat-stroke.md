# Thermal bias, heat stroke, shade and cooling

How 1.30 turns sustained heat into heat stroke: the thermal bias value, what feeds and drains it, the four heat stroke phases, washing the head, shade, and wind on a motorbike or boat. Checked on `P:\` (DayZ 1.30). Values for the later build 1.30.164289 are marked "build 1.30.164289, not checked on `P:\`".

## `ThermalBiasHandler`

`PlayerBase` owns one handler, declared as `m_ThermalBiasHandler` (`P:\scripts\4_world\entities\manbase\playerbase.c:339`) and created in the constructor (`P:\scripts\4_world\entities\manbase\playerbase.c:426`). The value itself is the player stat `EPlayerStats_current.THERMAL_BIAS` (`P:\scripts\4_world\classes\thermalbiashandler.c:16`).

`Add` does nothing while `m_TemporaryResistanceTime` is above 0, for positive and negative values alike (`P:\scripts\4_world\classes\thermalbiashandler.c:40` to `:48`). `OnTick` counts that time down (`thermalbiashandler.c:21` to `:29`).

The handler saves one float:

```c
// P:\scripts\4_world\classes\thermalbiashandler.c:67
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

`PlayerBase.OnStoreSave` writes it last, with `m_ThermalBiasHandler.OnStoreSave(ctx)` (`P:\scripts\4_world\entities\manbase\playerbase.c:7395`), and `PlayerBase.OnStoreLoad` reads it back with `m_ThermalBiasHandler.OnStoreLoad(ctx, version)` (`P:\scripts\4_world\entities\manbase\playerbase.c:7520`). A `modded class PlayerBase` that writes its own data calls `super.OnStoreSave` and `super.OnStoreLoad` first and keeps its reads in the order of its writes; the contract is in `_shared/persistence/save-load-contract.md`.

## `HeatComfortMdfr` feeds the bias

Extreme heat does not take health in this modifier. The hot side of its tick only feeds the bias; the cold side still takes health with `AddHealth` (`P:\scripts\4_world\classes\playermodifiers\modifiers\heatcomfortmdfr.c:62` to `:71`).

```c
// P:\scripts\4_world\classes\playermodifiers\modifiers\heatcomfortmdfr.c:74
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
| at or below it | any | minus `THERMAL_BIAS_POSITIVE_HC_DECREMENT`, and the bias is set to 0 once it is at or below 0 (`:105` to `:111`) |

Constants (`P:\scripts\3_game\playerconstants.c:203` to `:210`):

| Symbol | On `P:\` | Build 1.30.164289, not checked on `P:\` |
|---|---|---|
| `THERMAL_BIAS_WASH_HEAD_DECREMENT` | 0.175 | same |
| `THERMAL_BIAS_WASH_HEAD_TEMPORARY_RESISTANCE_TIME` | 30.0 s | same |
| `THERMAL_BIAS_POSITIVE_HC_DECREMENT` | 0.0001 | 0.0002 |
| `THERMAL_BIAS_POSITIVE_HC_LOW_INCREMENT` | 0.00022 | 0.0002 |
| `THERMAL_BIAS_POSITIVE_HC_MEDIUM_INCREMENT` | 0.00032 | same |
| `THERMAL_BIAS_POSITIVE_HC_HIGH_INCREMENT` | 0.00050 | same |

Build 1.30.164289, not checked on `P:\`: above the warning threshold, a player with water at or above `SL_WATER_HIGH` and heat comfort at or below `THRESHOLD_HEAT_COMFORT_PLUS_CRITICAL` loses bias through a new `RecoverThermalBias` method, and a conscious player with water between `SL_WATER_NORMAL` and `SL_WATER_HIGH` gains bias below 0.38 (0.4 minus a new `STAGE_DEACTIVATION_BUFFER` of 0.02) and loses it at or above. That holds the bias near 0.38 only while heat comfort stays at or below the critical threshold; above it the first feed adds 0.00032 or 0.0005 per second, more than the 0.0002 taken off, so the bias still rises.

## Heat stroke: four phases by threshold

```c
// P:\scripts\4_world\classes\playermodifiers\modifiers\diseases\heatstroke.c:3
	const int NUMBER_OF_STAGES = 4;
	const float STAGE_THRESHOLDS[NUMBER_OF_STAGES] = {0.0, 0.4, 0.6, 0.85};
```

The modifier IDs are `MDF_HEAT_STROKE1` to `MDF_HEAT_STROKE4` (`P:\scripts\4_world\classes\playermodifiers\emodifiers.c:66` to `:69`) and all four share the sync bit `MODIFIER_SYNC_HEAT_STROKE` (`P:\scripts\4_world\classes\playermodifiers\modifiersmanager.c:12`). Each phase reads `GetThermalBiasHandler().Get()` in its `ActivateCondition` (phase 1: `P:\scripts\4_world\classes\playermodifiers\modifiers\diseases\heatstroke.c:58` to `:61`). Phases stack: at a bias of 0.9 all four run.

| Phase | Active while bias | What it does on `P:\` |
|---|---|---|
| 1, `HeatStrokePhase1Mdfr` (`heatstroke.c:42`) | above 0.0 | Ticks `waterStat.Add(-WATER_DRAIN_FROM_FEVER_ST1 * deltaT)` (`:80`), but the constant is declared `protected static const int` with the value 0.35 (`heatstroke.c:7`), so it truncates to 0 and this phase drains no water on this build. A mod that wants the drain has to redeclare it as `float`. `OnActivate` is empty and `OnDeactivate` calls `DecreaseDiseaseCount` (`heatstroke.c:68` to `:75`). |
| 2, `HeatStrokePhase2Mdfr` (`heatstroke.c:84`) | above 0.4, off at or below 0.4 (`:105` to `:108`) | `OnActivate`: `SYMPTOM_FEVERBLUR`, stamina modifier `DISEASE_PNEUMONIA`, `IncreaseDiseaseCount` (`:110` to `:116`). `OnDeactivate` removes the symptom and the stamina modifier and does not decrement (`:118` to `:123`). Tick: random `SYMPTOM_HOT` and a water drain by `WATER_DRAIN_FROM_FEVER_ST2` (`:125` to `:136`). That constant is an `int` declared as 0.5 (`:8`), so it is 0 and no water drains unless a mod redeclares it as `float`. |
| 3, `HeatStrokePhase3Mdfr` (`heatstroke.c:140`) | above 0.6, off below 0.6 (`<`, not `<=`, `:164` to `:167`) | The vanilla comment says it stays active together with phase 4 (`:139`). Water drain by `WATER_DRAIN_FROM_FEVER_ST3` (`:190`), an `int` declared as 0.75 (`:9`) that comes out as 0, so no water drains unless a mod redeclares it as `float`. Random `SYMPTOM_VOMIT` that takes 70 water and 55 energy, then the `VOMIT_EXHAUSTION` stamina modifier (`:186` to `:216`). `OnReconnect` runs `OnActivate` again (`:175` to `:178`). |
| 4, `HeatStrokePhase4Mdfr` (`heatstroke.c:233`) | above 0.85 | Health loss per second remapped from `HEALTH_DAMAGE_MIN` 0.01 to `HEALTH_DAMAGE_MAX` 0.35 between bias 0.85 and 1.0, through `AddHealth` (`:27`, `:28`, `:308` to `:309`). `SYMPTOM_FAINT` (`:275`). Above a bias of 0.75 and with shock above 90, unconsciousness for 5 to 10 s every 60 to 120 s, with shock set to 25 (`:19` to `:24`, `:369` to `:383`). |

Build 1.30.164289, not checked on `P:\`: `HEALTH_DAMAGE_MAX` is 0.15; phase 2 turns off below 0.38 and runs `OnActivate` again in `OnReconnect`; phase 1's `OnDeactivate` is empty and phase 2's `OnDeactivate` calls `DecreaseDiseaseCount`.

### The sickness badge bug on this build

On `P:\` the only `IncreaseDiseaseCount` is in phase 2's `OnActivate` and the only `DecreaseDiseaseCount` is in phase 1's `OnDeactivate`. The counter balances only when phase 2 activates exactly once per phase 1 episode: phase 1 alone nets minus 1, and each further phase 2 activation nets plus 1. `ImmuneSystemMdfr` refreshes the sick notifier only when `HasDisease()` changes (`P:\scripts\4_world\classes\playermodifiers\modifiers\immunesystem.c:44` to `:55`; `HasDisease` is at `P:\scripts\4_world\entities\manbase\playerbase.c:1119`), so the icon can stay wrong. Build 1.30.164289 fixes this (not checked on `P:\`). When modding the phases, keep each `IncreaseDiseaseCount` and its `DecreaseDiseaseCount` in the same phase.

## Washing the head and wet clothing

`ActionWashHeadWettingClothesBase.OnFinishProgressServer` (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionwashheadwettingclothesbase.c:49` to `:57`):

- `ReduceAgent(eAgents.EYES_IRRITATION, GetEyeIrritationReduction())`, which is 10 by default (`actionwashheadwettingclothesbase.c:46`) and 1.6 from a bottle (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionwashheaditemcontinuous.c:41`).
- `Add(-PlayerConstants.THERMAL_BIAS_WASH_HEAD_DECREMENT)`, then `SetTemporaryResistance` for 30 s. On `P:\` both run on every wash. Because `Add` is ignored while resistance runs, a second wash inside the 30 s does not lower the bias, but it restarts the 30 s.
- `ApplyWetnessToClothes`, with one wetness table for a container (`s_WetnessContainer`) and one for a water surface (`s_WetnessSurface`) (`actionwashheadwettingclothesbase.c:10` to `:43`).
- A wash stopped early applies the same three scaled by progress in `OnEndServer`, without the resistance (`actionwashheadwettingclothesbase.c:59` to `:67`).

Build 1.30.164289, not checked on `P:\`: the bias drop and the resistance happen only when `GetTemporaryResistance()` is 0, so a wash inside the 30 s no longer restarts them, while the irritation drop and the wetting still happen.

`ActionWashHeadItemContinuous.ActionCondition` accepts any liquid except gasoline (`actionwashheaditemcontinuous.c:32` to `:39`) and has no `IsFrozen()` check, which matches the frozen bottle entry in the 1.30 changelog's known issues.

`ActionWetClothingInHandsBase` wets the item in hands with `SetWet` and takes off bias in proportion to the wetness gained, `m_WetGainPerStep` (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionwetclothinginhandsbase.c:44` to `:45`).

## Shade and sun

- The check runs every `ENVIRO_TICK_SHADOW_RC_CHECK`, 30 s (`P:\scripts\3_game\constants.c:760`), not every 5 s. The timer is in `P:\scripts\4_world\classes\environment\environment.c:406` to `:415`: inside a building the result is true at once, otherwise `CheckShadowPresence` runs.
- `IsInShadow()` returns the stored result (`environment.c:519`).
- `CheckShadowPresence` (`P:\scripts\4_world\classes\environment\environment.c:665` to `:720`): inside, under a roof, or riding in a `Car` gives shade without a cast. Otherwise it sweeps a capsule 50 m long with a 0.05 m radius from the head toward `-GetSunOrMoonDirection()` against the layers `ITEM_LARGE`, `BUILDING`, `VEHICLE`, `TERRAIN` and `ROADWAY`, with `DayZPhysics.CapsuleOverlapBullet` (`:680` to `:719`).
- Out of shade, temperature gains `GetSunEffectOnTemperature(m_DayTime) * HeadGearProtectionAgainstSun()`, but only when the world's `m_TemperatureUnderSunModifier` map has the current time of day (`environment.c:868` to `:872`). `GetSunEffectOnTemperature` scales the map value by overcast (`P:\scripts\3_game\worlddata.c:355` to `:360`).
- Only Nasdara fills that map: `DAWN` 2, `MORNING` 6, `NOON` 8, `AFTERNOON` 4, `EVENING` 2, `DUSK` 0, `NIGHT` 0 (`P:\scripts\4_world\classes\worlds\nasdara.c:67` to `:73`). The `Init` of `ChernarusPlusData` does not write it (`P:\scripts\4_world\classes\worlds\chernarusplus.c:31`), so the sun effect is skipped on Chernarus. A custom world that wants sunstroke fills the map in its own world data class.
- `HeadGearProtectionAgainstSun` (`environment.c:2037` to `:2065`): with headgear it returns the item's heat isolation times `HC_EXPOSED_HEAD_TO_SUN` (1.2, `environment.c:79`) plus 0.4; with none it returns 1.2. Design note: the loop returns the exposed value at the first clothing attachment that is not in the `HEADGEAR` slot, so the result depends on attachment order.

## Wind on a motorbike or boat

`DetermineHeatcomfortBehavior` (`P:\scripts\4_world\classes\environment\environment.c:575` to `:627`) picks a category: a `Car` with the engine on, a `Motorbike` faster than `ENVIRO_HEATCOMFORT_MOTORBIKE_SPEED_MIN` (20, `P:\scripts\3_game\constants.c:792`), or a `Boat` faster than `ENVIRO_HEATCOMFORT_BOAT_SPEED_MIN` (15, `P:\scripts\3_game\constants.c:797`).

`SetHeatcomfortDirectly` (`environment.c:1369`) then sets heat comfort itself. In a car with the engine on the target is 0. On a motorbike or boat it subtracts `Easing.EaseInCubic(normalizedSpeed)` times a maximum of 0.8 minus the vehicle's `GetHeatComfortOverride()` (`environment.c:1403` to `:1406` and `:1431`). `BoatScript.GetHeatComfortOverride` returns `m_HeatComfortOverride` (`P:\scripts\4_world\entities\vehicles\boatscript.c:256`), which starts at 0.0 (`boatscript.c:108`); `MotorbikeScript` has the same getter (`P:\scripts\4_world\entities\vehicles\motorbikescript.c:164`).

A motorbike and a boat cool the rider through wind but are not shade and are not sandstorm shelter (`sandstorm.md`).

## Porting a 1.29 heat mod

A 1.29 mod that trims heat damage in `HeatComfortMdfr` does nothing on 1.30, and the player still dies in heat stroke phase 4: the hot tick only feeds the bias (`heatcomfortmdfr.c:74` to `:82`), and the health loss is the `AddHealth` in phase 4 (`heatstroke.c:308` to `:309`). Balance `PlayerConstants.THERMAL_BIAS_*` (`P:\scripts\3_game\playerconstants.c:203` to `:210`) or the phases instead. Do not hang new heat damage on `HeatComfortMdfr`.

## Testing in game

On a local test server from `/dayz-launch-test`:

- **Heat:** sustained high heat comfort must raise the thermal bias and turn on `MDF_HEAT_STROKE1` to `MDF_HEAT_STROKE4`.
- **Washing the head:** removes 10 `EYES_IRRITATION` agents (1.6 from a bottle) and gives 30 s of resistance.
- **Shade:** time shade tests with the 30 s tick, not 5 s.
- **Logs:** search the RPT for `ThermalBiasHandler`; `PlayerBase` prints "failed to load ThermalBiasHandler" when the save stream is out of order (`P:\scripts\4_world\entities\manbase\playerbase.c:7522`).
