# Vanilla sources behind the motorbike references

Every vanilla file the `dayz-motorbikes` skill and its references cite, with its path on `P:\`, its line count there and the symbols read in it. Use it to check a citation or to see at a glance whether a DayZ update changed a file.

## Which build this is

- The line counts below were counted on `P:\` (text lines, counting a last line with no line break). They are the counts of DayZ 1.30.164014, the build the citations in the references were read on.
- The `config.cpp` files on `P:\` are unpacked with string arrays over several lines. The same config unpacked with each array on one line is much shorter, so compare a `config.cpp` count only with a count taken in the same layout.
- Evidence level of the references: read in source (Enforce Script, `config.cpp` and the text animation graph), except where a line is marked `[UNVERIFIED]`. Nothing is claimed as tested in game unless the line says it was measured in game.
- What differs on the later stable builds 1.30.164200 and 1.30.164289 is in section 7; not yet checked on `P:\`.

## Where the motorbike sounds are

- `P:\DZ\sounds\vehicles\config.cpp:1-10` holds only the `CfgPatches` class `DZ_Sounds_Vehicles`. It defines no sound class.
- The `CfgSoundShaders` and `CfgSoundSets` of the motorbikes (`Motorbike_01` and `Motorbike_02`) are in `P:\DZ\sounds\hpp\config.cpp` (523051 lines):
  - `Motorbike_0*` classes in `CfgSoundShaders` (which spans `P:\DZ\sounds\hpp\config.cpp:3072-318378`): lines 316513 to 318260 (engine RPM, offload overrun, brake, shock absorbers, tyres on different surfaces, crash).
  - `Motorbike_0*` classes in `CfgSoundSets` (which spans `P:\DZ\sounds\hpp\config.cpp:318379-385077`): lines 383946 to 385036 (gear shift, kickstart, lights, get in and out, short, long and looping horn, RPM sets).

## Cited files

### 1. Engine and base scripts (3_Game)

| File on `P:\` | Lines | Symbols read |
|---|---|---|
| `P:\bin\config.cpp` | 11105 | `class Motorbike: Transport`, `simulation = "motorbike"` |
| `P:\scripts\3_game\vehicles\motorbike.c` | 370 | Motorbike `proto native` signatures, `MotorbikeOwnerState`, `MotorbikeMove`, sound and stability callbacks |
| `P:\scripts\3_game\vehicles\transport.c` | 1205 | `ETransportFluid`, `NeedElectricitySourceDevice`, `IsAnyCrewPresent`, `OnContact`, `m_ContactCache`, `VehicleContactData` |
| `P:\scripts\3_game\vehicles\car.c` | 507 | `enum CarFluid : ETransportFluid` |
| `P:\scripts\3_game\vehicles\boat.c` | 207 | `enum BoatFluid : ETransportFluid` |
| `P:\scripts\3_game\constants.c` | 1168 | `MOTORBIKES_CONTACT_DMG_*`, `ENVIRO_HEATCOMFORT_MOTORBIKE_*` |
| `P:\scripts\3_game\human.c` | 1721 | `HumanAnimInterface.IsTag()`, `HumanCommandVehicle.IsTransitioning()` |
| `P:\scripts\3_game\dayzplayer.c` | 1413 | Player constants |
| `P:\scripts\3_game\dustkickupeffects.c` | 256 | Projectile dust effects singleton |
| `P:\scripts\3_game\enums\evehiclevfxtypes.c` | 17 | `EVehicleVFXEffect`, `EVehicleVFXEffectGroup` |

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
| `P:\scripts\4_world\entities\core\inherited\inventoryitem.c` | 1377 | `ActionPickUpMotorbike` on the `Motorbike_02` side fairings |
| `P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c` | 1658 | `AddItemInHandsProfileIK` registrations, `DayZPlayerTypeRegisterItems`, animation instance preload |
| `P:\scripts\3_game\entities\object.c` | 1467 | `GetBonePivotsForAnimationSource`, `GetBoneRotationMS` |

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
| `P:\scripts\4_world\classes\useractionscomponent\actioninput.c` | 1035 | `ToggleVehicleLightsActionInput`, `ToggleLightsActionInput`, pre-1.30 horn input aliases |
| `P:\scripts\4_world\classes\useractionscomponent\actions\interact\vehicles\actionswitchlights.c` | 72 | `ActionSwitchLights.GetInputType()` |
| `P:\scripts\4_world\classes\useractionscomponent\actions\continuous\vehicles\actionfillfuel.c` | 69 | `FUEL_SELECTION_NAME = "refill"` |
| `P:\scripts\4_world\classes\useractionscomponent\actions\continuous\vehicles\actioncarhorn.c` | 361 | Pre-1.30 horn action names kept for compatibility |

### 4. HUD (5_Mission)

| File on `P:\` | Lines | Symbols read |
|---|---|---|
| `P:\scripts\5_mission\gui\vehicles\motorbikehud.c` | 248 | Tachometer, speedometer, fuel gauge, disabled warning indicators (handbrake, temperature) |
| `P:\scripts\5_mission\gui\ingamehud.c` | 1316 | `m_VehicleHudMap` entry `"VehicleTypeMotorbike"` |

### 5. Vehicle configs and animation files

| File on `P:\` | Lines | Symbols read |
|---|---|---|
| `P:\DZ\vehicles\singletrack\config.cpp` | 2375 | Full vanilla motorbike contract (`MotorbikeScript`, `Motorbike_01`, `Motorbike_02`, wheels, proxies) |
| `P:\DZ\vehicles\wheeled\config.cpp` | 24369 | Vanilla car config, new wheel parameters (`tyreRoughness`, `tyreLongitudinalFriction`, `tyreLateralFriction`) |
| `P:\DZ\anims\workspaces\player\player_main\vehicles.agf` | 3655 | Enfusion animation graph in plain text, `MotorBikeB` node, `MotorBikeSTM` state machine |
| `P:\DZ\anims\workspaces\player\player_main\player_main.ast` | 1268 | `"Jawa_05"` and `"Jawa_Bitrak"` animation columns |
| `P:\DZ\anims\workspaces\player\player_main\player_main.asi` | 6679 | `.anm` clip mapping for motorbike riding poses |
| `P:\DZ\anims\workspaces\player\player_main\player_main_surrender.asi` | 296 | Header of a child `.asi` (`Template`, `ParentTemplates`) |
| `P:\bin\constants.xml` | 938 | Input names `UAToggleHeadlight` and `UAToggleVehicleLights` |
| `P:\DZ\sounds\hpp\config.cpp` | 523051 | Real CfgSoundShaders and CfgSoundSets of motorbikes |
| `P:\DZ\sounds\vehicles\config.cpp` | 10 | Exclusive CfgPatches without audio classes |

### 6. The 1.29 to 1.30 diffs

Statements in the references about what changed from 1.29 come from diffs between a 1.29 and a 1.30 extraction. The diff files are not in this repo and 1.29 is not on `P:\`, so those statements are not yet checked on `P:\`. The sizes of the diffs:

- `3_Game/human.c`: 88 diff lines
- `3_Game/Vehicles/Transport.c`: 657 diff lines (+438 / -40)
- `4_World/Entities/Vehicles/CarScript.c`: 2784 diff lines (+877 / -1155)
- `4_World/Entities/DayZPlayerImplementFallDamage.c`: 165 diff lines
- `4_World/Classes/UserActionsComponent/ActionInput.c`: 323 diff lines
- the `vehicles_wheeled` config: 785 diff lines
- There is no diff for `vehicles_singletrack`: that PBO is new in 1.30.

### 7. What differs on build 1.30.164200

Not yet checked on `P:\`. Only these cited files have a different length on that build:

| File | 1.30.164014 | 1.30.164200 |
|---|---|---|
| `transport.c` | 1205 | 1214 |
| `motorbikescript.c` | 1765 | 1780 |
| `inheritedmotorbikes\motorbike_01.c` | 171 | 168 |
| `inheritedmotorbikes\motorbike_02.c` | 142 | 139 |
| `dayzplayercameravehicles.c` | 470 | 473 |

`P:\DZ\vehicles\singletrack\config.cpp` and `P:\DZ\sounds\hpp\config.cpp` also grow on that build: by 7 and 812 lines when unpacked with each array on one line, which is not the layout on `P:\`.

In the sound config of that build each `Motorbike_0*` group has one class more, because `Motorbike_02_Engine_Ext_Broken` became `Motorbike_02_Engine_Ext_Broken_High` and `Motorbike_02_Engine_Ext_Broken_Low`. Build 1.30.164289 changed none of the script files cited here and no data file's text. The differences in behaviour on 1.30.164200 are noted where they apply, in `actions-hud-lights-sounds.md` (light registrations, light profiles, particle cooldown) and in `skills/_shared/vehicles/motorbike-invariants.md` (status in 1.30).

When DayZ updates, re-run the repo integrity test (`python -m pytest -q scripts/dev/test_repo_integrity.py`): it flags every full `P:\` citation whose line no longer holds the symbol named beside it.
