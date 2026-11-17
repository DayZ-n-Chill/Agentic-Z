# Vanilla sources behind the motorbike references

Every vanilla file the `dayz-motorbikes` skill and its references cite, with its path on `P:\`, its line count there and the symbols read in it. Use it to check a citation or to see at a glance whether a DayZ update changed a file.

## Which build this is

- The line counts below were counted on `P:\` when the material was brought in (text lines, counting a last line with no line break). Every script and animation file has exactly the count the knowledge pack recorded for DayZ Experimental 1.30.164014, so the vanilla data on `P:\` at that time matches that text.
- The `config.cpp` files on `P:\` are unpacked in a longer layout than the one the knowledge pack counted (string arrays over several lines), so their counts differ while the content is the same; the tables in sections 1 and 5 give both counts.
- Evidence level of the references: read in source (Enforce Script, `config.cpp` and the text animation graph), except where a line is marked `[UNVERIFIED]`. Nothing is claimed as tested in game unless it names the project that measured it.
- The knowledge pack later re-read its citations on stable builds 1.30.164200 and 1.30.164289. What it reports as different on those builds is in section 7; not yet checked on `P:\`.

## Where the motorbike sounds are

- `P:\DZ\sounds\vehicles\config.cpp:1-10` holds only the `CfgPatches` class `DZ_Sounds_Vehicles`. It defines no sound class.
- The `CfgSoundShaders` and `CfgSoundSets` of the motorbikes (`Motorbike_01` and `Motorbike_02`) are in `P:\DZ\sounds\hpp\config.cpp` (523051 lines):
  - `Motorbike_0*` classes in `CfgSoundShaders` (which spans `P:\DZ\sounds\hpp\config.cpp:3072-318378`): lines 316513 to 318260 (engine RPM, offload overrun, brake, shock absorbers, tyres on different surfaces, crash).
  - `Motorbike_0*` classes in `CfgSoundSets` (which spans `P:\DZ\sounds\hpp\config.cpp:318379-385077`): lines 383946 to 385036 (gear shift, kickstart, lights, get in and out, short, long and looping horn, RPM sets).

## Cited files

### 1. Engine and base scripts (3_Game)

| File on `P:\` | Lines on `P:\` | Lines in the knowledge pack's layout | Symbols read |
|---|---|---|---|
| `P:\bin\config.cpp` | 11105 | 6287 | `class Motorbike: Transport`, `simulation = "motorbike"` |
| `P:\scripts\3_game\vehicles\motorbike.c` | 370 | 370 | Motorbike `proto native` signatures, `MotorbikeOwnerState`, `MotorbikeMove`, sound and stability callbacks |
| `P:\scripts\3_game\vehicles\transport.c` | 1205 | 1205 | `ETransportFluid`, `NeedElectricitySourceDevice`, `IsAnyCrewPresent`, `OnContact`, `m_ContactCache`, `VehicleContactData` |
| `P:\scripts\3_game\vehicles\car.c` | 507 | 507 | `enum CarFluid : ETransportFluid` |
| `P:\scripts\3_game\vehicles\boat.c` | 207 | 207 | `enum BoatFluid : ETransportFluid` |
| `P:\scripts\3_game\constants.c` | 1168 | 1168 | `MOTORBIKES_CONTACT_DMG_*`, `ENVIRO_HEATCOMFORT_MOTORBIKE_*` |
| `P:\scripts\3_game\human.c` | 1721 | 1721 | `HumanAnimInterface.IsTag()`, `HumanCommandVehicle.IsTransitioning()` |
| `P:\scripts\3_game\dayzplayer.c` | 1413 | 1413 | Player constants |
| `P:\scripts\3_game\dustkickupeffects.c` | 256 | 256 | Projectile dust effects singleton |
| `P:\scripts\3_game\enums\evehiclevfxtypes.c` | 17 | 17 | `EVehicleVFXEffect`, `EVehicleVFXEffectGroup` |

### 2. Gameplay and entity scripts (4_World)

| File on `P:\` | Lines | Symbols read |
|---|---|---|
| `P:\scripts\4_world\entities\vehicles\motorbikescript.c` | 1765 | Lifecycle, kickstand, starting, "drivewheel" lights, damages, network sync |
| `P:\scripts\4_world\entities\vehicles\carscript.c` | 2981 | 1.30 refactor, component delegation, deprecated methods marked with `[Obsolete]` |
| `P:\scripts\4_world\entities\vehicles\vehicleaniminstances.c` | 15 | `MOTO1 = 10`, `MOTO2 = 11` |
| `P:\scripts\4_world\entities\vehicles\inheritedmotorbikes\motorbike_01.c` | 171 | `Motorbike_01_ColorBase`, `SeatDriver`, `ActionAnimateMotorbikeSeat`, SoundSets |
| `P:\scripts\4_world\entities\vehicles\inheritedmotorbikes\motorbike_02.c` | 142 | `Motorbike_02_ColorBase`, `ShieldFront/Left/Right` fairings, thermal comfort |
| `P:\scripts\4_world\entities\vehicles\inheritedcars\civiliansedan.c` | 497 | Lights and horn migration to components |
| `P:\scripts\4_world\entities\vehicles\inheritedcars\offroad_02.c` | 475 | `HasGangedTailAndBrakeLights`, shared lights |
| `P:\scripts\4_world\entities\vehicles\components\vehiclehorncomponent.c` | 111 | Horn modes, AI noise, `NoiseCarHorn` integration |
| `P:\scripts\4_world\entities\vehicles\components\vehiclelightscomponent.c` | 190 | Registration of light selections and profiles |
| `P:\scripts\4_world\entities\vehicles\components\vehiclevfxcomponent.c` | 588 | Unified particles and exhaust/wheel smoke management |
| `P:\scripts\4_world\entities\scriptedlightbase\spotlightbase\vehiclelightbase.c` | 86 | Parameterized generic spotlight |
| `P:\scripts\4_world\entities\scriptedlightbase\spotlightbase\vehiclelightprofiles\vehiclelightprofilebase.c` | 95 | Base aggregated and segregated lighting profile |
| `P:\scripts\4_world\entities\scriptedlightbase\spotlightbase\vehiclelightprofiles\motorbike_01.c` | 34 | `Motorbike_01LightProfileFront`, `Motorbike_01LightProfileRear` |
| `P:\scripts\4_world\entities\scriptedlightbase\spotlightbase\vehiclelightprofiles\motorbike_02.c` | 34 | `Motorbike_02LightProfileFront` |
| `P:\scripts\4_world\entities\dayzplayerimplement.c` | 4131 | Crash ejection (`CrewShouldEject` / `eModifiers.MDF_UNCONSCIOUSNESS`), bike death (`FallOver`) |
| `P:\scripts\4_world\entities\dayzplayerimplementfalldamage.c` | 378 | `CurveExp` exponential curve and new thresholds |
| `P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercameras.c` | 173 | Registration of `DAYZCAMERA_3RD_VEHICLE_MOTORBIKE = 32` |
| `P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercameravehicles.c` | 470 | Implementation of `DayZPlayerCamera3rdPersonVehicleMotorbike` with spring lag |
| `P:\scripts\4_world\entities\manbase\playerbase.c` | 10144 | Engine start and stop actions registration |
| `P:\scripts\4_world\entities\itembase\blowtorch.c` | 146 | Exclusive registration of chassis, engine, and bike part repair actions |

### 3. User actions (4_World)

| File on `P:\` | Lines | Symbols read |
|---|---|---|
| `P:\scripts\4_world\classes\useractionscomponent\actions\continuous\vehicles\actionstartenginemotorbike.c` | 100 | Continuous kickstart action, `OnIgnition()` |
| `P:\scripts\4_world\classes\useractionscomponent\actions\singleuse\vehicles\actionstopenginemotorbike.c` | 76 | Engine stop action capped at 8 km/h |
| `P:\scripts\4_world\classes\useractionscomponent\actions\interact\vehicles\actionpickupmotorbike.c` | 104 | Picking up fallen bike (`trans.PickUp()`) |
| `P:\scripts\4_world\classes\useractionscomponent\actions\interact\vehicles\actionanimatemotorbikeseat.c` | 47 | `SeatDriver` tilting |
| `P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionrepairmotorbikechassis.c` | 55 | Base chassis repair |
| `P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionrepairmotorbikechassiswithblowtorch.c` | 46 | Chassis repair with blowtorch |
| `P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionrepairmotorbikeengine.c` | 60 | Base engine repair (orphaned) |
| `P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionrepairmotorbikeenginewithblowtorch.c` | 45 | Engine repair with blowtorch |
| `P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionrepairmotorbikepart.c` | 160 | Base part/fairing repair |
| `P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionrepairmotorbikepartwithblowtorch.c` | 46 | Part repair with blowtorch |
| `P:\scripts\4_world\classes\useractionscomponent\actions\continuous\vehicles\actionvehiclehorn.c` | 350 | `ActionVehicleHornShort`, `ActionVehicleHornLong` |
| `P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetintransport.c` | 159 | Directional mounting via lateral dot product |
| `P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetouttransport.c` | 274 | Jump out while moving at speed > 10 km/h |
| `P:\scripts\4_world\classes\useractionscomponent\actionconstructor.c` | 399 | Global action registration in the subsystem |

### 4. HUD (5_Mission)

| File on `P:\` | Lines | Symbols read |
|---|---|---|
| `P:\scripts\5_mission\gui\vehicles\motorbikehud.c` | 248 | Tachometer, speedometer, fuel gauge, disabled warning indicators (handbrake, temperature) |

### 5. Vehicle configs and animation files

| File on `P:\` | Lines on `P:\` | Lines in the knowledge pack's layout | Symbols read |
|---|---|---|---|
| `P:\DZ\vehicles\singletrack\config.cpp` | 2375 | 1099 | Full vanilla motorbike contract (`MotorbikeScript`, `Motorbike_01`, `Motorbike_02`, wheels, proxies) |
| `P:\DZ\vehicles\wheeled\config.cpp` | 24369 | 8357 | Vanilla car config, new wheel parameters (`tyreRoughness`, `tyreLongitudinalFriction`, `tyreLateralFriction`) |
| `P:\DZ\anims\workspaces\player\player_main\vehicles.agf` | 3655 | 3655 | Enfusion animation graph in plain text, `MotorBikeB` node, `MotorBikeSTM` state machine |
| `P:\DZ\anims\workspaces\player\player_main\player_main.ast` | 1268 | 1268 | `"Jawa_05"` and `"Jawa_Bitrak"` animation columns |
| `P:\DZ\anims\workspaces\player\player_main\player_main.asi` | 6679 | 6679 | `.anm` clip mapping for motorbike riding poses |
| `P:\DZ\sounds\hpp\config.cpp` | 523051 | 183928 | Real CfgSoundShaders and CfgSoundSets of motorbikes |
| `P:\DZ\sounds\vehicles\config.cpp` | 10 | 31 | Exclusive CfgPatches without audio classes |

### 6. The 1.29 to 1.30 diffs

Statements in the references about what changed from 1.29 come from diffs the knowledge pack author made between a 1.29 and a 1.30 extraction. The diff files are not in this repo and 1.29 is not on `P:\`, so those statements are not yet checked on `P:\`. Their sizes, as recorded:

- `3_Game/human.c`: 88 diff lines
- `3_Game/Vehicles/Transport.c`: 657 diff lines (+438 / -40)
- `4_World/Entities/Vehicles/CarScript.c`: 2784 diff lines (+877 / -1155)
- `4_World/Entities/DayZPlayerImplementFallDamage.c`: 165 diff lines
- `4_World/Classes/UserActionsComponent/ActionInput.c`: 323 diff lines
- the `vehicles_wheeled` config: 785 diff lines
- There is no diff for `vehicles_singletrack`: that PBO is new in 1.30.

### 7. What the knowledge pack reports for build 1.30.164200

Reported by the knowledge pack on 2026-10-28; not yet checked on `P:\`. Only these files have a different length on that build (the counts are in its own layout for the two `config.cpp` files):

| File | 1.30.164014 | 1.30.164200 |
|---|---|---|
| `transport.c` | 1205 | 1214 |
| `motorbikescript.c` | 1765 | 1780 |
| `inheritedmotorbikes\motorbike_01.c` | 171 | 168 |
| `inheritedmotorbikes\motorbike_02.c` | 142 | 139 |
| `dayzplayercameravehicles.c` | 470 | 473 |
| `DZ\vehicles\singletrack\config.cpp` | 1099 | 1106 |
| `DZ\sounds\hpp\config.cpp` | 183928 | 184740 |

In the sound config of that build each `Motorbike_0*` group has one class more, because `Motorbike_02_Engine_Ext_Broken` became `Motorbike_02_Engine_Ext_Broken_High` and `Motorbike_02_Engine_Ext_Broken_Low`. The knowledge pack also reports that build 1.30.164289 changed none of the script files cited here and no data file's text. The differences in behaviour it found on 1.30.164200 are noted where they apply, in `actions-hud-lights-sounds.md` (light registrations, light profiles, particle cooldown) and in `skills/_shared/vehicles/motorbike-invariants.md` (status in 1.30).

When DayZ updates, re-run the repo integrity test: it flags every full `P:\` citation whose line no longer holds the symbol named beside it.
