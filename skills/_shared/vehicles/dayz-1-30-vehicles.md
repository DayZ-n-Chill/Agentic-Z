# DayZ 1.30 vehicle changes

What DayZ 1.30 changed for cars, trucks and boats beyond the class tree, which change breaks a 1.29 mod outright, and the steps to move a car from 1.29 to 1.30.

The class tree, the `Motorbike` sibling and the `CarScript` component split are in `class-hierarchy.md`; this file and the three below hold the rest. `P:\` holds a 1.30 build. A line marked "1.29" belongs to the older build and is not on `P:\`. In-game results were measured on test quads and are mod behaviour, not vanilla.

| Topic | File |
|---|---|
| Light profiles, the light toggle, the lens flare, the battery methods, the horn, `GetWeightCoef`, ganged tail and brake lights | `dayz-1-30-lights-and-battery.md` |
| The get-in condition, boats, `speedGeoms`, wreck cisterns, the motorbike camera | `dayz-1-30-get-in-and-boats.md` |
| The `_Ruined` wheel twin and the new tyre fields | `dayz-1-30-wheels.md` |
| Aircraft built on `CarScript` | `aviation-dayz-1-30.md` |
| Light material paths and hidden selection order | `lights.md` |

## What changed

| Topic | Until 1.29 | Since 1.30 | Where |
|---|---|---|---|
| `Transport` children | `Car` and `Boat` | A third sibling, `Motorbike`, with `simulation="motorbike"` | `P:\bin\config.cpp:1481` to `:1486`; `P:\scripts\3_game\vehicles\motorbike.c:30` |
| Headlights | A `CarLightBase` child and `CreateFrontLight`, `CreateRearLight` | A `VehicleLightBase` and a `VehicleLightProfileBase` child registered on `m_LightsComponent` | `P:\scripts\4_world\entities\scriptedlightbase\spotlightbase\vehiclelightbase.c:1`; `P:\scripts\4_world\entities\vehicles\inheritedcars\offroad_02.c:21` and `:22` |
| Battery | `IsVitalCarBattery`, `IsVitalTruckBattery` | `NeedElectricitySourceDevice`, `GetElectricitySourceDevice`, `GetElectricitySourceDeviceType` | `P:\scripts\3_game\vehicles\transport.c:830` to `:843`; `P:\scripts\4_world\entities\vehicles\carscript.c:2811` to `:2817` |
| Horn actions | `ActionCarHornShort`, `ActionCarHornLong` | `ActionVehicleHornShort`, `ActionVehicleHornLong`; the old input classes `CarHornShortActionInput` and `CarHornLongActionInput` are empty aliases | `carscript.c:2319` and `:2320`; `P:\scripts\4_world\classes\useractionscomponent\actioninput.c:757` to `:774` |
| Light toggle input | `UAToggleHeadlight` | `UAToggleVehicleLights` for vehicle lights | `ToggleVehicleLightsActionInput`, `actioninput.c:849` to `:855`; `P:\bin\constants.xml:90` and `:91` |
| Forced light refresh | `ForceUpdateLightsStart`, `ForceUpdateLightsEnd` | `[Obsolete("1.30: no replacement")]`; delete the calls | `carscript.c:2805` to `:2809` |
| Headlight toggle | `CarScript.ToggleHeadlights()`, called by `ActionSwitchLights` | Deleted with no obsolete stub; the action calls the native `Transport.LightToggle()` | `transport.c:239`; `P:\scripts\4_world\classes\useractionscomponent\actions\interact\vehicles\actionswitchlights.c:64` |
| Script module path | Backslashes in `files[]` loaded | Backslashes loaded nothing; forward slashes load | Measured, below |
| Ruined wheel swap | A `switch` over vanilla wheel names; a mod wheel was never swapped | Every wheel is swapped for `<class>_Ruined`; a missing class raises an error and the wheel is not swapped | `P:\scripts\4_world\entities\core\inherited\inventoryitemtype.c:17` to `:46`; `dayz-1-30-wheels.md` |
| Fluids | `CarFluid`, a separate `BoatFluid` | `enum ETransportFluid`; `BoatFluid : ETransportFluid {}` | `transport.c:52` to `:63`; `P:\scripts\3_game\vehicles\boat.c:13` |
| Boat speedometer | Car only | `Boat.GetSpeedometer` and `GetSpeedometerAbsolute` | `boat.c:42` to `:56` |
| Get-in | `IsAreaAtDoorFree` | `CanGetIn()` first, then `IsAreaAtDoorFreeDiag` | `P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetintransport.c:36` and `:54`; `transport.c:675` to `:678` |
| Effect scale | None | `GetWeightCoef()`, default 1.0 | `transport.c:478` to `:481` |
| Ganged rear bulbs | None | `HasGangedTailAndBrakeLights()`, default `false` | `carscript.c:468` to `:471` |
| High speed geometry | In the change notes only | Config `speedGeomActivation` and `speedGeoms[]` | `P:\DZ\vehicles\singletrack\config.cpp:262` and `:263` |
| Motorbike third person camera | None | `DAYZCAMERA_3RD_VEHICLE_MOTORBIKE = 32` | `P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercameras.c:20`; `motorbike-rider-animation.md` |

## Vanilla models are ODOL version 56

Vanilla models on 1.30 are ODOL version 56; on 1.29 they were version 54. `P:\DZ\vehicles\wheeled\offroadhatchback\offroadhatchback.p3d` reads 56, as do `Motorbike_01` and `Motorbike_02`; the 1.29 `offroadhatchback.p3d` reads 54. Read the version in header bytes 4 to 7 before any extraction or comparison tool runs on a new build: a version 54 reader fails with `ValueError: subsection not found`. On a new build, first run the old reader on a model it is known to handle. An external ODOL to MLOD converter needs a version 56 reader for 1.30 vanilla models. The motorbike models read this way are in `motorbike-vanilla-p3d-anatomy.md`.

## ToggleHeadlights was deleted, not deprecated

`CarScript.ToggleHeadlights()` is the one light member 1.30 removed instead of marking `[Obsolete]`. 1.29 declared it in `CarScript.c` (line 2088) and called it from `ActionSwitchLights.c` (line 75) and from `CarScript.c` (lines 834 and 3061). No file under `P:\scripts` declares or calls it; the switch action toggles the native state with `Transport.LightToggle()` (`P:\scripts\3_game\vehicles\transport.c:239`; `actionswitchlights.c:64`).

So a 1.29 car whose script says `override void ToggleHeadlights()` overrides a method that no longer exists, and Enforce refuses it: the `4_World` module fails and the game or server does not start with the mod. On a 1.30 diag server, a test quad's 1.29 scripts, with only their module path fixed, gave `Function 'ToggleHeadlights' is marked as override, but there is no function with this name in the base class`, then `Can't compile "World" script module!` and `ENGINE (F): Crashed`. The `[Obsolete]` members are the opposite case: they compile and are never called. Resolve every `override` against the target build before you ship.

## Script module paths need forward slashes

A 1.29 script module path written with backslashes can load nothing on 1.30, silently. A test quad's `CfgMods` declared `dir = "MyMod"` and `worldScriptModule` `files[] = {"MyMod\scripts\4_world"}`, which loaded on 1.29. On a 1.30 diag server its `World` module loaded 2,332 files, the same as a run without the mod, with and without `-filePatching`: the quad ran as a bare `CarScript`, and the `ToggleHeadlights` compile error never appeared. With `files[] = {"MyMod/scripts/4_world"}` the module loaded 2,337 files, the mod's five scripts. Another mod whose paths use forward slashes loaded in the same runs.

Write module paths with forward slashes, and compare the script log's `Module: World; loaded Nx files` line with a run without the mod: scripts that never load never fail to compile either. This reverses the 1.29 advice on script binding in `vehicle-structural-parity.md`.

## Lines a 1.29 note still cites

| Symbol | 1.29 line in `carscript.c` | 1.30 line |
|---|---|---|
| `SetEventMask` calls in the `CarScript` constructor | 325 and 326 | `P:\scripts\4_world\entities\vehicles\carscript.c:207` and `:208` |
| `CarScript.EOnPostSimulate` | 948 | `carscript.c:807` |
| `CarScript.OnDriverExit` and its gear check | 1207 to 1215 | `carscript.c:940` to `:948` |
| Empty `Transport.OnDriverExit` | 161 in `transport.c` | `P:\scripts\3_game\vehicles\transport.c:227` |
| `ForceUpdateLightsStart` and `ForceUpdateLightsEnd` | 535 and 536, 2981 and 2990 | Obsolete at `carscript.c:2805` to `:2809` |

## Offroad_02 in 1.30

- Its front-left door part `Offroad_02_Door_1_1` carries the roof panels as two hidden selections, `texture_roof_ext` and `texture_roof_int`, each with its own material (`P:\DZ\vehicles\wheeled\config.cpp:20576` to `:20601`).
- The `Front` damage zone of `Offroad_02` (`config.cpp:20899` on) has no `dmgZone_bumper_1`. That 1.29 had one is reported, not checked on `P:\`.
- Beige variants are new: `Offroad_02_Beige` (`:22394`) and `_BeigeRust` parts such as `Offroad_02_Door_1_1_BeigeRust` (`:23441`).

## Moving a car from 1.29 to 1.30

1. Resolve every `override` in the car's scripts against the 1.30 class chain, class by class, not by method name. A deleted method (`ToggleHeadlights`) fails the compile; an `[Obsolete]` one compiles and is never called. The script validator (`scripts/tools/dayz-script-validator/`) with `--vanilla-root` on a 1.30 tree passes scripts that override `ToggleHeadlights`, so it does not catch this. A resolver that walks the class chain does: it flagged that override as missing and three others as obsolete, and resolved all 211 overrides of the vanilla `inheritedcars` folder without a finding.
2. Delete overrides of `ToggleHeadlights`, `CreateFrontLight`, `CreateRearLight`, `IsVitalCarBattery`, `IsVitalTruckBattery`, `CarPartsHealthCheck`, `ForceUpdateLightsStart` and `ForceUpdateLightsEnd`.
3. Keep `m_LightsComponent`, `m_HornComponent` and `m_VFXComponent`, which `CarScript` already constructs.
4. Call `RegisterLight("Front"|"Rear", new VehicleLightData(new MyMod_Profile()))` and `RegisterSound(VehicleHornMode.SHORT|LONG, "...")`.
5. Override `NeedElectricitySourceDevice` and its two getters if the vehicle needs a battery; return `false` for a magneto. Without the getters a battery car reports `NO_BATTERY` with a battery fitted (`dayz-1-30-lights-and-battery.md`).
6. Bind the vehicle light action to `UAToggleVehicleLights`, not `UAToggleHeadlight`.
7. Register `ActionVehicleHornShort` and `ActionVehicleHornLong` in `SetActions`, not `ActionCarHorn*`.
8. Override `GetWeightCoef` if dust and exhaust are the wrong size, and `HasGangedTailAndBrakeLights` if brake and tail share a bulb.
9. If get-in has gone, implement `CanGetIn()` and check `IsAreaAtDoorFreeDiag` and `CanReachSeatFromDoors` (`dayz-1-30-get-in-and-boats.md`).
10. Fill fluids through `ETransportFluid` and `GetFluidCapacityScript` on `Transport`.
11. Check every `carscript.c` line number the mod or its notes cite against the 1.30 file.
12. Write the `CfgMods` module paths with forward slashes, and check the `Module: World; loaded Nx files` line against a run without the mod.
13. Give every wheel class a `<class>_Ruined` config twin and a script class extending `CarWheel_Ruined`, register the twins in `RegisterHeavy` if the intact wheels are there, and declare the four 1.30 tyre fields on every wheel (`dayz-1-30-wheels.md`).
14. Before porting a published mod, hash the PBO players actually run (the Workshop item) and compare it with the release or source you port. One published quad's Workshop build carried older tuning than its tagged release: suspension twice as stiff, clutch 140 against 180, steering animation plus or minus 30 against 45 degrees, the opposite wheel spin, and no full tank from the Central Economy. A port of the release changes the handling Workshop players know.
15. A front light profile that should keep the 1.29 single bulb lens flare needs the restore in `dayz-1-30-lights-and-battery.md`; a 1.29 parked headlight workaround has nothing left to fix.
