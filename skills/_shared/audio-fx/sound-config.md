# Sound config: shaders and sets

How to write `CfgSoundShaders` and `CfgSoundSets` entries in a mod's `config.cpp`, with the keys vanilla uses and what each one controls.

All line numbers below are in `P:\DZ\sounds\hpp\config.cpp` unless another file is named.

## Contents

- [Where the classes live](#where-the-classes-live)
- [CfgPatches](#cfgpatches)
- [Sound shader (`CfgSoundShaders`)](#sound-shader-cfgsoundshaders)
- [Sound set (`CfgSoundSets`)](#sound-set-cfgsoundsets)
- [Worked example: a generator running loop](#worked-example-a-generator-running-loop)
- [Checks before handing back](#checks-before-handing-back)

## Where the classes live

Vanilla sound classes are in two files, so search both: `P:\DZ\sounds\hpp\config.cpp` and `P:\DZ\sounds_bliss\config.cpp`. The main file declares them at the root of the config, next to `CfgVehicles`:

| Root class | Line | What it holds |
|---|---|---|
| `CfgSoundCurves` | 59 | Named volume curves (`points[]`), used by shaders and sets. |
| `CfgSoundEffects` | 2161 | Equalizer and echo effects for attenuation. |
| `CfgDistanceFilters` | 2422 | Low pass filters that dull a sound with distance. |
| `CfgSound3DProcessors` | 2587 | How a sound is placed in 3D (`panner`, `emitter`, `surround_panner`). |
| `CfgSoundShaders` | 3072 | Shaders: samples, volume, range. |
| `CfgSoundSets` | 318379 | Sets: which shaders play and how. |
| `CfgSoundTables` | 385078 | Surface and event lookup tables (footsteps, impacts). |

The `CfgPatches` class in that file is `DZ_Sounds_Effects` (line 3).

A mod declares its own `CfgSoundShaders` and `CfgSoundSets` at the root of its `config.cpp`, outside `CfgVehicles`. Vanilla does the same in its second addon: `P:\DZ\sounds_bliss\config.cpp` declares `CfgSoundShaders` at line 6237, `CfgSoundSets` at line 13028 and `CfgSoundCurves` at line 27840, and its `CfgPatches` class `DZ_Sounds_Bliss` lists `DZ_Sounds_Effects` in `requiredAddons[]` (lines 3 to 13).

## CfgPatches

Whenever a shader or set inherits from a vanilla one, put the `CfgPatches` class of the file that defines the parent in `requiredAddons[]`, so the vanilla class is loaded first: `DZ_Sounds_Effects` for a class in `P:\DZ\sounds\hpp\config.cpp` (for example `baseCharacter_SoundSet`), `DZ_Sounds_Bliss` for a class in `P:\DZ\sounds_bliss\config.cpp`. Sound classes are not listed in `units[]`; that list is for `CfgVehicles` classes.

## Sound shader (`CfgSoundShaders`)

The vanilla generator loop, lines 5764 to 5777:

```cpp
class powerGeneratorLoop_Soundshader
{
    samples[]=
    {
        {
            "DZ\sounds\environment\buildings\power_station_bunker\generator_engine_loop",
            1
        }
    };
    volume=1.7782794;
    range=100;
    rangeCurve="Animals_new_Curve";
};
```

| Key | Meaning | Vanilla evidence |
|---|---|---|
| `samples[]` | List of `{path, number}` pairs. The path has no file extension; the file on disk is `.ogg`. | Line 5770; the file is `P:\DZ\sounds\environment\buildings\power_station_bunker\generator_engine_loop.ogg`. |
| `volume` | Loudness as a linear factor. Vanilla values are decibel steps written as factors: `1.7782794` is +5 dB, `0.31622776` is -10 dB, `0.25118864` is -12 dB. It may also be a string expression of engine sound variables, such as `"interior"`. | Lines 5774, 17075, 17062; expression at line 17093. |
| `range` | How far the sound carries, in meters. Past this distance it is not heard. | Line 5775 (`range=100`); `baseCharacter_SoundShader` uses 35 (line 3076). |
| `rangeCurve` | How volume falls over `range`. Either the name of a `CfgSoundCurves` class, or an inline `rangeCurve[]` of `{distance, volume}` points. | Named at line 5776; inline at lines 17078 to 17090. |
| `frequency` | Pitch factor; `1` is the recorded pitch. | Line 6583 (`frequency=1.1`). |
| `limitation` | Seen on some interior shaders as `limitation=1`. Vanilla does not document what it does. | Line 17103. |

Notes on samples:

- Paths start with the addon prefix, with or without a leading backslash. Both forms are in vanilla: `"DZ\sounds\..."` (line 5770) and `"\DZ\sounds\..."` (line 16412). A mod sample path starts with the mod's `$PBOPREFIX$`, such as `"MyMod\data\sounds\mymod_generator_loop"`.
- With several samples, the engine plays one of them each time. Vanilla almost always gives each sample `1`; `seachest_movement_Soundshader` (line 10493) mixes 1, 2 and 3, which reads as a relative weight. That reading is not documented in vanilla, so treat it as unverified.
- Vanilla ships both mono and stereo `.ogg` samples. A count of the files under `P:\DZ\sounds\` found about 19,000 mono and 8,000 stereo, and the generator loop above is stereo at 44100 Hz. Nothing on `P:\` states a required channel count.
- `/dayz-build-pbo` packs `.ogg` and `.wss` files (its `include.lst`), so samples under `workspace/<ModName>/` reach the PBO.

### Curves: named versus inline

A named curve in `CfgSoundCurves` has `points[]` whose first value runs from 0 to 1, a fraction of the shader's `range`. `defaultAmpAttenuationCurve` (line 61) starts at `{0,1}` and ends at `{1,0}`.

An inline `rangeCurve[]` uses meters. `reloadWeapon_SoundShader` (line 17078) has `range=30` and points from `{0,1}` to `{30,0}`, with full volume held to 2 m.

Always name a curve that exists. The vanilla generator shaders name `Animals_new_Curve`; the class is declared as `animals_new_Curve` in `CfgSoundCurves` (line 1799) and matches because lookup ignores case. In your own mod, name a curve with its exact case, such as `defaultAmpAttenuationCurve` (line 61) or `InverseSquare1Curve` (line 806), or write an inline one.

## Sound set (`CfgSoundSets`)

The vanilla generator loop set, lines 319400 to 319413:

```cpp
class powerGeneratorLoop_SoundSet
{
    soundShaders[]=
    {
        "powerGeneratorLoop_SoundShader"
    };
    volumeFactor=1.1;
    spatial=1;
    doppler=0;
    loop=0;
    volumeCurve="defaultAmpAttenuationCurve";
    sound3DProcessingType="Sakhal_Generator3DProcessingType";
    startDelay=1.2;
};
```

| Key | Meaning | Vanilla evidence |
|---|---|---|
| `soundShaders[]` | The shaders this set plays, by class name. | Line 319402. |
| `volumeFactor` | Multiplies the shader volume. Can be a number or a string expression (`"0.251 * 1"`). | Line 319406; `P:\DZ\sounds_bliss\config.cpp:13036`. |
| `volumeCurve` | A `CfgSoundCurves` class for volume over distance. | Line 319410. |
| `spatial` | `1` plays the sound in 3D at its source; `0` plays it flat. | Line 319407. |
| `doppler` | `1` turns on pitch shift for moving sources. | Line 319408. |
| `loop` | `1` loops the set. Script can loop a set whatever this says (see `sound-script.md`). | Line 319409. |
| `sound3DProcessingType` | A `CfgSound3DProcessors` class. | Line 319411; the class is at line 3029. |
| `distanceFilter` | A `CfgDistanceFilters` class that cuts high frequencies with distance. | `baseCharacterLoud_SoundSet`, line 318393. |
| `startDelay` | Seconds before the set starts. | Line 319412. |
| `frequencyFactor`, `frequencyRandomizer`, `volumeRandomizer` | Pitch factor and random spread of pitch and volume on each play. | `P:\DZ\sounds_bliss\config.cpp:13038` to `13040`. |
| `soundShadersLimit`, `soundObjectsLimit` | Caps on how many shaders and sound instances of this set play at once. | `Rifle_Shot_Interior_Base_SoundSet`, lines 323701 to 323714. |
| `occlusionFactor`, `obstructionFactor` | Seen on weapon sets (`0.6`). Vanilla does not document the scale. | Lines 323707 and 323708. |
| `positionOffset[]` | A `{x,y,z}` offset for the sound position. | Line 339640. |

Vanilla also writes some of these in lower case (`volumefactor`, `soundshaders[]`) and with `"true"` and `"false"` strings (`P:\DZ\sounds_bliss\config.cpp:13041`). Write them the way the main table shows.

### Class names are not case sensitive

`powerGeneratorLoop_SoundSet` names `"powerGeneratorLoop_SoundShader"` (line 319404), but the class is declared as `powerGeneratorLoop_Soundshader` (line 5764), and the generator plays. Lookup ignores case. Still match the case exactly in your own mod so a search finds both ends.

### 3D processors and filters

`CfgSound3DProcessors` entries set `type` (`panner`, `emitter` or `surround_panner`), `innerRange` and `range`, and optionally a `rangeCurve`. `Sakhal_Generator3DProcessingType` (line 3029) is a `panner` with `innerRange=0.5`, `range=8` and `rangeCurve="InverseSquare1Curve"`. `character3DProcessingType` (line 2602) is a `panner` with `innerRange=2` and `range=4`.

`CfgDistanceFilters` entries are low pass filters: `defaultDistanceFreqAttenuationFilter` (line 2424) has `minCutoffFrequency=150`, `innerRange=10` and `range=1000`.

Reuse the vanilla processors, filters and curves by name. Write your own only when no vanilla one fits, and put it in your own `CfgSoundCurves`, `CfgSound3DProcessors` or `CfgDistanceFilters` at the config root, as `P:\DZ\sounds_bliss\config.cpp` does for curves at line 27840.

## Worked example: a generator running loop

```cpp
class CfgPatches
{
    class MyMod_Sounds
    {
        units[]={};
        weapons[]={};
        requiredVersion=0.1;
        requiredAddons[]={"DZ_Data","DZ_Sounds_Effects"};
    };
};
class CfgSoundShaders
{
    class MyMod_GeneratorLoop_SoundShader
    {
        samples[]={{"MyMod\data\sounds\mymod_generator_loop",1}};
        volume=1;
        range=60;
        rangeCurve="defaultAmpAttenuationCurve";
    };
};
class CfgSoundSets
{
    class MyMod_GeneratorLoop_SoundSet
    {
        soundShaders[]={"MyMod_GeneratorLoop_SoundShader"};
        volumeFactor=1;
        volumeCurve="defaultAmpAttenuationCurve";
        spatial=1;
        doppler=0;
        loop=1;
    };
};
```

To make it carry further, raise `range`. To make it louder up close without carrying further, raise `volume` or `volumeFactor`. To make it fade sooner, pick a steeper curve or write an inline `rangeCurve[]` in meters.

## Checks before handing back

1. Every `soundShaders[]` name matches a shader class, and every curve, filter and 3D processor name matches a class that exists (vanilla or yours).
2. Every sample path starts with the mod prefix (or `DZ\` for a vanilla sample that exists under `P:\DZ\`) and the `.ogg` exists under `workspace/<ModName>/`.
3. When anything inherits a vanilla sound class, `requiredAddons[]` holds the `CfgPatches` class of the file that defines the parent: `DZ_Sounds_Effects` for `sounds\hpp\config.cpp`, `DZ_Sounds_Bliss` for `sounds_bliss\config.cpp`.
4. Class names carry the mod prefix (`MyMod_`), so they never collide with vanilla or another mod.
