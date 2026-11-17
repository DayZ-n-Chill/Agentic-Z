# Aircraft engine sounds

The `CfgSoundShaders` and `CfgSoundSets` layout LM_Planes uses for engines: the RPM band crossfade formula, volume modulation by thrust, speed, doors and camera, offload variants, ranges, and which aircraft own their sounds. The general sound config keys are in `skills/_shared/audio-fx/sound-config.md`.

Third-party mod behaviour, not vanilla: patterns read in the LM_Planes mod (Workshop `3730564764`), whose files are not in this repo. Not yet checked on `P:\` except where a `P:\` path is cited. Use it to learn the pattern and write the mod's own code.

## Two-tier architecture

**CfgSoundShaders** (low-level, ~700 classes):

```cpp
class baseEngineLM_Tigermoth_SoundShader { range = 780; };  // Base per aircraft

class LM_Tigermoth_Engine_Ext_Rpm2_SoundShader: baseEngineLM_Tigermoth_SoundShader
{
    samples[] = {{"LM_Planes\Sounds\Tigermoth\sc_Engine_Ext_Rpm2",1}};
    frequency = "0.80 * (850 + ((rpm - 850)/(8000/5600))) / 1700";
    volume = "0.99 * 1 * (thrust factor[0.1,0.45]) * (0.7 + 0.3 * (speed factor [10,60])) * engineOn * 0.85 * ((850 + ((rpm - 850)/(8000/5600))) factor [(((1200+1700)/2) - 2.5*150),(((1200+1700)/2) + 150)]) * ((850 + ((rpm - 850)/(8000/5600))) factor [(((1700+2300)/2) + 2.5*150),(((1700+2300)/2) - 150)]) * ((1 - 0.25*doors) max campos)";
};
```

**CfgSoundSets** (high-level, ~300 classes):

```cpp
class baseEngine_EXT_SoundSet
{
    sound3DProcessingType = "Vehicle_Ext_3DProcessingType";
    distanceFilter        = "softVehiclesDistanceFreqAttenuationFilter";
    volumeCurve           = "vehicleEngineAttenuationCurve";
    volumeFactor          = 1;
    occlusionFactor       = 0;
    obstructionFactor     = 0;
    spatial               = 1;
    loop                  = 1;
    positionOffset[]      = {0,0,0.3};
};

class LM_Tigermoth_Engine_Ext_Rpm2_SoundSet: baseEngine_EXT_SoundSet
{
    soundShaders[] = {"LM_Tigermoth_Engine_Ext_Rpm2_SoundShader"};
};
```

## Range design (engineering choices)

| Event | Range (m) | Rationale |
|---|---|---|
| Aircraft engine | 780 | Audible from far in open ambient |
| Patty_Wagon car engine | 80 | Standard ground vehicle |
| Spitfire shot (bombing) | 2000 | Combat awareness |
| Plane Boom (crash) | 1000 | Loud event, attract players |
| Ignition (start/stop) | 50-200 | Local action |
| Stall warning | 10-50 | Intimate cockpit warning |
| Patty_Wagon horn | 250 | Standard car horn |

## RPM-band crossfade formula

For each engine, 5-6 RPM bands with samples per band. Frequency maps actual RPM to sample's design RPM:

```
frequency = 0.80 * ((850 + ((rpm - 850)/(8000/5600))) max 850) / TARGET_RPM
```

Where `TARGET_RPM` is the band's design RPM (e.g., 1200, 1700, 2300, 3250, 4400 for the 5 bands).

Volume uses chained `factor [low, high]` calls (each returns 0→1 lerp). Two factors per band: one ramps up entering the band, one ramps down leaving:

```
... * ((rpm_remapped) factor [(midpoint - 2.5*spread), (midpoint - spread)])
  * ((rpm_remapped) factor [(midpoint + 2.5*spread), (midpoint - spread)])
```

Creates smooth crossfade with no audible band-edge clicks.

The formula is the vanilla car engine formula with other numbers. Vanilla's `Offroad_Engine_Ext_Rpm1_SoundShader` at `P:\DZ\sounds\hpp\config.cpp:310700` has the same `thrust factor[0.1,0.45]`, `speed factor [10,60]`, `engineOn` and `doors` terms, and the parent sound set `baseEngine_EXT_SoundSet` is vanilla too (`P:\DZ\sounds\hpp\config.cpp:379546`). LM_Planes declares its own `baseEngine_EXT_SoundSet` with `positionOffset[] = {0,0,0.3}`; give a new mod's base class its own prefixed name instead of redeclaring the vanilla one.

## Multi-factor volume modulation

Variables available in sound shader formulas: `rpm`, `thrust`, `speed`, `engineOn`, `doors`, `campos`.

Patterns:
- `thrust factor[0.1,0.45]` — volume rises with throttle
- `0.7 + 0.3 * (speed factor [10,60])` — boost with velocity (wind/road noise)
- `engineOn` — 0/1 hard mute when engine off
- `(1 - 0.25*doors) max campos` — closed doors muffle, but interior camera boosts (use `max` so interior view always hears clearly)

## Offload vs Normal load variants

For each RPM band, two variants:
- `Engine_Ext_RpmN_SoundShader` — normal/accel load: `thrust factor[0.1,0.45]` (volume rises with throttle)
- `Engine_Offload_Ext_RpmN_SoundShader` — coast/decel load: `thrust factor[0.6,0.2]` (inverse — volume falls with throttle)

Plus different sample files (`sc_Engine_Ext_RpmN` vs `sc_Engine_Ext_Offload_RpmN`). Gives realistic engine tone change when player releases throttle.

## Required sounds per aircraft

Stall warn, engine start (OK + battery + plug + fuel error variants), engine stop (normal + fuel variant). Specified in script via `GetSoundEngineStartOK()`, `GetSoundEngineStartBattery()`, etc.

## Sound asset ownership patterns

Per-aircraft pattern observed:
- **Full own sound set**: Catalina, Cessna180, DC_3, Patty_Wagon, Spitfire, Tigermoth, Z37_Bumblebee — each defines `LM_<aircraft>_engine_start_SoundSet` + 5 broken/stop variants
- **Total reuse Tigermoth sounds**: StuntPlane (all 6 sound configs reference `LM_Tigermoth_*_SoundSet`)
- **Partial reuse**: Cessna180 reuses only `LM_Tigermoth_Engine_StallWarn_SoundSet` (stall warn is generic beep, OK to share)

Rule: **define your own sounds if the aircraft has identity. Reuse template (Tigermoth) sounds for variants of the same airframe.**
