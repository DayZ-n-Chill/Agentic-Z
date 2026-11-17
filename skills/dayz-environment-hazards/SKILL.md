---
name: dayz-environment-hazards
description: "Reference for the environmental hazards DayZ 1.30 added: the sandstorm (Weather.GetSandstorm, ScriptedSandstormController, sandstormFrequency, shelter fade), heat stroke (ThermalBiasHandler, HeatStroke phases, IsInShadow, washing the head), dust agents and protective gear (silicosis, irritated eyes, AGT_AIRBOURNE_SOLID, DEF_DUST_PARTICLE), oil pits (OilPitArea), surface dust (SurfaceInfo) and the Nasdara world of the Badlands DLC. Use when a mod starts, balances, shelters from or protects against one of these, or when a 1.29 heat or effect area mod stopped working on 1.30. Not for writing particle files (/dayz-particles) or the clothing item itself (the wearables pack)."
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# DayZ environment hazards (1.30)

Follow `skills/_shared/dayz-conventions.md`. This skill is reference only; it runs no scripts, so there is no preflight gate. The reference files are in `<skill-dir>\references\`.

DayZ 1.30 adds hazards that come from the environment itself:

- A sandstorm run partly by the engine and partly by script, reached through `Weather.GetSandstorm()` (`P:\scripts\3_game\weather.c:210`, class at `P:\scripts\3_game\sandstorm.c:6`).
- Exposure with a shelter fade in `ScriptedSandstormController`.
- Heat stroke driven by an accumulator, `ThermalBiasHandler`. Extreme heat no longer takes health in `HeatComfortMdfr`.
- Eye irritation and silicosis, carried by the new transmission type `AGT_AIRBOURNE_SOLID`.
- Oil pits (`OilPitArea`), dust that depends on the surface (`SurfaceInfo`), and sunstroke that depends on shade (`IsInShadow`).
- The Nasdara world (Badlands DLC, `appId = 3816030`) with its sand weather and sun table.

Everything here is read from source on `P:\` (DayZ 1.30). Nothing was measured in a running game. Lines marked "build 1.30.164289, not checked on `P:\`" describe a later build than the one on `P:\`.

## What to read

| Question | File |
|---|---|
| How do I start or balance a sandstorm on my map, and what counts as shelter? | `references/sandstorm-shelter.md` |
| How does heat stroke build, what cools a player, how do shade and vehicle wind work? | `references/thermal-heatstroke.md` |
| Which mask or glasses stop silicosis and eye irritation, and what do the agents do? | `references/ppe-agents.md` |
| Where does ceiling, kickup and wheel dust come from, how does an oil pit work, what ships with Nasdara? | `references/dust-oilpit-nasdara.md` |
| Which vanilla file holds which part, what was not checked, which common assumptions are wrong? | `references/vanilla-file-map.md` |

Work that belongs elsewhere:

| Topic | Go to |
|---|---|
| `.ptc` and `.emat` files, playing particles | `/dayz-particles` |
| The mask or glasses item, its model and slots | `_shared/wearables/references/protection-and-insulation.md` |
| The player save stream that the thermal bias handler writes into | `_shared/persistence/save-load-contract.md` |
| What infected hear in a storm (`AIParams.sandstormToNoiseMultiplier`) | `_shared/ai/perception.md` |
| Vehicle effect components | the vehicles pack, `_shared/vehicles/` |

A new environmental hazard should copy a vanilla pattern: an `EffectArea` with a synced trigger, or a `Weather.GetSandstorm().Start` call from the map's `WorldData`. Do not hang heat damage on `HeatComfortMdfr`: that path does not exist in 1.30.

## Critical path: sandstorm and heat in a custom world

1. **Reach the storm.** Script does not create the controller. On the server call `GetGame().GetWeather().GetSandstorm().Start(duration, false)` and `.Stop(duration, false)` (`P:\scripts\3_game\sandstorm.c:20` and `:27`).
2. **World config.** The world class needs a `class Sandstorm` with `soundSets[]` and `particlePath` (`P:\DZ\data\config.cpp:1532`).
3. **Frequency.** `"SandstormData": { "sandstormFrequency": 1.0 }` in `cfggameplay.json` (`ITEM_SandstormData`, `P:\scripts\3_game\cfggameplaydatajson.c:440`). 0 turns weather storms off; 2 doubles the chance on Nasdara.
4. **World data.** For storms that come with the weather, copy Nasdara's pattern, `StartSandstorm` on the overcast change and the `sandstormChance` roll in `CalculateWind` (`P:\scripts\4_world\classes\worlds\nasdara.c:318` to `:322` and `:563` to `:575`). `ChernarusPlusData` starts none. This is a design step, not a copied recipe.
5. **Shelter.** A player's intensity is `GetIntensity` at the head, faded over 1.5 s when underground, inside (a roof and `IsSoundInsideBuilding`) or in a `Car` (`P:\scripts\4_world\systems\sandstorm\scriptedsandstormcontroller.c:142` to `:178`). A motorbike and a boat are not shelter.
6. **Protective gear.** A mask with `DEF_DUST_PARTICLE_BREATH` against silicosis; eyewear, a mask or night vision goggles with `DEF_DUST_PARTICLE_EYES` against irritation (`P:\scripts\3_game\constants.c:549` to `:550`).
7. **Heat.** `HeatComfortMdfr` feeds `ThermalBiasHandler.Add` above the comfort thresholds (`P:\scripts\4_world\classes\playermodifiers\modifiers\heatcomfortmdfr.c:74` to `:82`), and the four `HeatStroke` phases read the bias (`STAGE_THRESHOLDS`, `P:\scripts\4_world\classes\playermodifiers\modifiers\diseases\heatstroke.c:4`).
8. **Shade and sun.** `CheckShadowPresence` runs every `ENVIRO_TICK_SHADOW_RC_CHECK`, 30 s (`P:\scripts\3_game\constants.c:760`). The sun table of plus 2 to plus 8 degrees is in the Nasdara world data only; a custom world fills `m_TemperatureUnderSunModifier` itself.
9. **Oil pits and other areas.** Place effect areas through the mission's `cfgeffectarea.json`; details and the caveat are in `references/dust-oilpit-nasdara.md`.

## Ten rules that break an environmental hazard

### 1. Only a `Car` cancels the sandstorm; a motorbike and a boat do not

- **Symptom:** a motorbike rider keeps squinting and collecting silicosis inside the storm.
- **Cause:** `ApplyVehicleModifier` requires `transport.IsAnyInherited({Car})` (`P:\scripts\4_world\systems\sandstorm\scriptedsandstormcontroller.c:265`).
- **Fix:** do not assume any vehicle shelters. A custom closed vehicle inherits from `Car`, or the mod overrides `GetIntensityForPlayer`.

### 2. Inside means a roof and the building sound environment

- **Symptom:** standing under an eave or a crashed helicopter does not stop the storm.
- **Cause:** `isCurrentlyInside = (isUnderRoof && isInInterior)`, and `EXCLUDED_SHELTER_TYPES` is `{CrashBase, Plant}` (`scriptedsandstormcontroller.c:20`, `:222` to `:228`).
- **Fix:** a mod building has to make `IsSoundInsideBuilding()` true and have Fire Geometry for the `ObjIntersectIFire` roof check.

### 3. Deadly heat is no longer in `HeatComfortMdfr`

- **Symptom:** a 1.29 mod that trims heat damage in `HeatComfortMdfr` does nothing; the player still dies in heat stroke phase 4.
- **Cause:** the hot tick calls `thermalBiasHandler.Add(...)` (`heatcomfortmdfr.c:74` to `:82`). The health loss is `AddHealth` in the `OnTick` of `HeatStrokePhase4Mdfr` (`heatstroke.c:308` to `:309`).
- **Fix:** balance `PlayerConstants.THERMAL_BIAS_*` (`P:\scripts\3_game\playerconstants.c:203` to `:210`) or the phases. Cold still takes health in `HeatComfortMdfr` (`heatcomfortmdfr.c:62` to `:71`).

### 4. Heat stroke phase 1 breaks the sickness badge on this build

- **Symptom:** the sickness icon does not come back, or stays on.
- **Cause:** on `P:\`, phase 1's `OnDeactivate` calls `DecreaseDiseaseCount()` with no matching increase (`heatstroke.c:72` to `:75`), and phase 2's `OnActivate` calls `IncreaseDiseaseCount()` with no matching decrease (`heatstroke.c:110` to `:123`).
- **Fix:** fixed in build 1.30.164289 (not checked on `P:\`). On an older build, or when modding the phases, keep each increase and its decrease in the same phase. Detail: `references/thermal-heatstroke.md`.

### 5. Breathing protection is not eye protection

- **Symptom:** glasses are expected to stop silicosis, or a mask without `DEF_DUST_PARTICLE_EYES` does not stop squinting.
- **Cause:** `AGT_AIRBOURNE_SOLID` checks the `MASK` category for `SILICOSIS` and eyewear, mask or night vision for `EYES_IRRITATION` (`P:\scripts\4_world\plugins\pluginbase\plugintransmissionagents.c:414` to `:434`).
- **Fix:** give the item both `dust_particle_breath` and `dust_particle_eyes` in its `class Protection` when it should stop both.

### 6. `OnCEUpdate` is no longer the effect area tick

- **Symptom:** a custom area does not resize its particles or never iterates.
- **Cause:** `EffectArea` overrides `OnCEIterate(float currentTime, float elapsedTime)` (`P:\scripts\4_world\classes\contaminatedarea\effectarea.c:191`), and `OnCEUpdate` is marked obsolete (`P:\scripts\3_game\entities\entityai.c:4924` to `:4925`).
- **Fix:** override `OnCEIterate`.

### 7. `Surface.GetStepsParticleID` and `EffWheelSmoke.SetSurface` are obsolete

- **Cause:** both carry `[Obsolete]` and forward to the new API (`P:\scripts\4_world\static\surface.c:64` to `:65`, `P:\scripts\4_world\entities\effects\wheelsmoke.c:32` to `:33`).
- **Fix:** `SurfaceInfo.GetByName(...).GetStepParticleId()` and `SelectFromSurface`.

### 8. An oil pit only does damage in the `BURNING` state

- **Cause:** a random delay of 3 to 9 whole seconds before `StartBurning` (`PRE_BURNING_DURATION_MIN` 3 and `PRE_BURNING_DURATION_MAX` 10, `P:\scripts\4_world\classes\contaminatedarea\oilpitarea.c:10` to `:11`, passed to `Math.RandomInt` at `:54`, whose upper bound is exclusive per `P:\scripts\1_core\proto\enmath.c:26` to `:38`), then 20 `HeatDamage` every second (`DAMAGE_MULTIPLIER`, `P:\scripts\4_world\entities\scriptedentities\triggers\oilpittrigger.c:7` to `:8`).
- **Fix:** wait for the state before judging a test; a fresh pit looks inert.

### 9. Shade is not a ray cast every 5 seconds

- **Cause:** the timer is 30 s, and the test is a capsule 50 m long with a 0.05 m radius toward `-GetSunOrMoonDirection()` (`P:\scripts\4_world\classes\environment\environment.c:680` to `:685`). Inside, under a roof or in a `Car` it is shade with no cast (`environment.c:667` to `:677`).
- **Fix:** time tests with the 30 s tick.

### 10. The script weather noise helpers do not govern AI

- **Cause:** `GetNoiseReductionByWeatherEx` and `GetNoiseReductionByWeather` are both marked obsolete; AI noise dampening is native and reads `AIParams`, including `sandstormToNoiseMultiplier=10` (`P:\scripts\3_game\weather.c:407` to `:408`, `P:\DZ\data\aiconfigs\config.cpp:20`).
- **Fix:** for the HUD or an old mod keep using `GetNoiseReductionByWeatherEx(object)`; for infected hearing change the `AIParams` config.

## How to verify

1. **Offline.** Run `/dayz-lint` on the mod. The script validator under `scripts/tools/dayz-script-validator/` checks the Enforce Script itself:

   ```cmd
   python scripts\tools\dayz-script-validator\scripts\script_validator.py <addon_root>
   ```

   Pass means its result has no errors.
2. **In game**, on a local test server from `/dayz-launch-test`:
   - **Start:** on the server, `GetGame().GetWeather().GetSandstorm().Start(5, false)`. The client must get the `REQ_SANDSTORMEFFECT` post process (`scriptedsandstormcontroller.c:310` to `:327`).
   - **Shelter:** walk into a building that reports `IsSoundInsideBuilding`; intensity reaches 0 within 1.5 s. Mount a motorbike: intensity must not drop. Get into a `Car`: it must.
   - **Gear:** with a dust mask, no cough and no silicosis; with glasses, no squint.
   - **Heat:** sustained high heat comfort must raise the thermal bias and turn on `MDF_HEAT_STROKE1` to `MDF_HEAT_STROKE4`.
   - **Washing the head:** removes 10 `EYES_IRRITATION` agents (1.6 from a bottle) and gives 30 s of resistance.
   - **Oil pit:** wait 3 to 9 s, then expect 20 heat damage per second and the `OIL_FIRE1` or `OIL_FIRE2` particles.
3. **Logs.** Search the RPT for `ThermalBiasHandler` and `Sandstorm`; `PlayerBase` prints "failed to load ThermalBiasHandler" when the save stream is out of order (`P:\scripts\4_world\entities\manbase\playerbase.c:7522`).

## Unfinished parts seen in 1.30

1. **Nasdara map files.** Not checked on `P:\`: the first 1.30 build shipped a 6 file stub of `data_nasdara.pbo`; 1.30.164200 installs the full set of 24 PBOs with the world in an encrypted `.ebo`. See `references/dust-oilpit-nasdara.md`.
2. **Washing the head with a frozen bottle.** `ActionWashHeadItemContinuous` only refuses gasoline, which matches the changelog's known issue.
3. **Sickness icons.** Rule 4 above.
4. **Sun on Chernarus.** `ChernarusPlusData` (`P:\scripts\4_world\classes\worlds\chernarusplus.c:2`) does not fill `m_TemperatureUnderSunModifier`, so the sun effect there stays 0.

## Building and testing the mod

When the work has to end in a mod that builds, loads and ships, use this repo's own chain: `/dayz-lint`, `/dayz-build-pbo`, `/dayz-launch-test` and `/dayz-gate`.
