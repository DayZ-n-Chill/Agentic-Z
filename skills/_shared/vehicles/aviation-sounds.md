# Aircraft engine sounds

How a plane mod lays out its engine sound shaders and sound sets: the crossfade between RPM bands, volume shaped by thrust, speed, doors and camera, the coasting variants, the ranges, and when to share sounds between aircraft.

The layout comes from LM_Planes (Workshop `3730564764`), whose configs are the source; it is mod practice, not vanilla, except where a `P:\` line is cited. The general sound config keys are in `_shared/audio-fx/sound-config.md`.

## Shaders and sets

LM_Planes has about 700 `CfgSoundShaders` classes and about 300 `CfgSoundSets` classes. Each aircraft has a base shader with its range, and one shader per RPM band:

```cpp
class baseEngineMyMod_Plane_SoundShader { range = 780; };

class MyMod_Plane_Engine_Ext_Rpm2_SoundShader: baseEngineMyMod_Plane_SoundShader
{
    samples[] = {{"MyMod\Sounds\Plane\sc_Engine_Ext_Rpm2",1}};
    frequency = "0.80 * (850 + ((rpm - 850)/(8000/5600))) / 1700";
    volume = "0.99 * 1 * (thrust factor[0.1,0.45]) * (0.7 + 0.3 * (speed factor [10,60])) * engineOn * 0.85 * ((850 + ((rpm - 850)/(8000/5600))) factor [(((1200+1700)/2) - 2.5*150),(((1200+1700)/2) + 150)]) * ((850 + ((rpm - 850)/(8000/5600))) factor [(((1700+2300)/2) + 2.5*150),(((1700+2300)/2) - 150)]) * ((1 - 0.25*doors) max campos)";
};
```

Each sound set points at one shader and inherits a shared base:

```cpp
class MyMod_Engine_EXT_SoundSet
{
    sound3DProcessingType = "Vehicle_Ext_3DProcessingType";
    distanceFilter = "softVehiclesDistanceFreqAttenuationFilter";
    volumeCurve = "vehicleEngineAttenuationCurve";
    volumeFactor = 1;
    occlusionFactor = 0;
    obstructionFactor = 0;
    spatial = 1;
    loop = 1;
    positionOffset[] = {0,0,0.3};
};

class MyMod_Plane_Engine_Ext_Rpm2_SoundSet: MyMod_Engine_EXT_SoundSet
{
    soundShaders[] = {"MyMod_Plane_Engine_Ext_Rpm2_SoundShader"};
};
```

LM_Planes names its base `baseEngine_EXT_SoundSet`, which redeclares a vanilla class of that name (`P:\DZ\sounds\hpp\config.cpp:379546`). Give a new mod's base its own prefixed name, as above.

## The RPM band crossfade

Each engine has five or six RPM bands, each with its own sample. The frequency maps the real RPM onto the sample's recorded RPM:

```cpp
frequency = "0.80 * ((850 + ((rpm - 850)/(8000/5600))) max 850) / TARGET_RPM";
```

`TARGET_RPM` is the band's recorded RPM, for example 1200, 1700, 2300, 3250 and 4400 for five bands.

The volume chains two `factor [low, high]` terms per band, each a 0 to 1 ramp: one fades in on entering the band, one fades out on leaving it. `lower_mid` is halfway between this band's RPM and the band below, and `upper_mid` halfway to the band above; for the 1700 band that is `(1200+1700)/2` and `(1700+2300)/2`, with a spread of 150:

```cpp
// ... * ((rpm_remapped) factor [(lower_mid - 2.5*spread), (lower_mid + spread)])
//     * ((rpm_remapped) factor [(upper_mid + 2.5*spread), (upper_mid - spread)])
```

The bands overlap smoothly, with no click at the edges. This is the vanilla car engine formula with other numbers: vanilla's `Offroad_Engine_Ext_Rpm1_SoundShader` uses the same `thrust factor[0.1,0.45]`, `speed factor [10,60]`, `engineOn` and `doors` terms (`P:\DZ\sounds\hpp\config.cpp:310700`).

## Shaping the volume

Shader formulas can read `rpm`, `thrust`, `speed`, `engineOn`, `doors` and `campos`.

| Term | Effect |
|---|---|
| `thrust factor[0.1,0.45]` | Louder with throttle |
| `0.7 + 0.3 * (speed factor [10,60])` | Louder with speed, for wind noise |
| `engineOn` | 0 or 1: silent with the engine off |
| `(1 - 0.25*doors) max campos` | Closed doors muffle the sound, but the inside camera always hears it clearly |

## Load and coasting variants

Each RPM band has two shaders, with different samples (`sc_Engine_Ext_RpmN` and `sc_Engine_Ext_Offload_RpmN`):

| Shader | Load | Thrust term |
|---|---|---|
| `Engine_Ext_RpmN_SoundShader` | Pulling, accelerating | `thrust factor[0.1,0.45]`, louder with throttle |
| `Engine_Offload_Ext_RpmN_SoundShader` | Coasting, slowing | `thrust factor[0.6,0.2]`, quieter with throttle |

The engine note changes when the pilot lets go of the throttle.

## Ranges

| Sound | Range |
|---|---|
| Aircraft engine | 780 m, heard from far off in open country |
| Patty Wagon car engine | 80 m, a normal ground vehicle |
| Spitfire weapon | 2000 m |
| Crash | 1000 m, loud enough to draw players |
| Ignition, start and stop | 50 to 200 m |
| Stall warning | 10 to 50 m, inside the cockpit |
| Patty Wagon horn | 250 m |

## Sounds each aircraft needs

A stall warning; an engine start in four forms (success, and failures for battery, plug and fuel); and an engine stop in two forms (normal and out of fuel). Script returns them from `GetSoundEngineStartOK()`, `GetSoundEngineStartBattery()` and the matching getters.

Give an aircraft its own sounds when it has its own character, and share them across variants of one airframe. In LM_Planes the Catalina, Cessna180, DC-3, Patty Wagon, Spitfire, Tigermoth and Z37 each define `LM_<aircraft>_engine_start_SoundSet` and five failure and stop variants; the StuntPlane reuses all six Tigermoth sound sets; the Cessna180 reuses only `LM_Tigermoth_Engine_StallWarn_SoundSet`, a generic beep.
