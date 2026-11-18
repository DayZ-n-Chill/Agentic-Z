# Vanilla files behind the motorbike pack

Which vanilla files the motorbike files of this pack cite, with each path on `P:\`, its line count there and the symbols read in it. Use it to check a citation, or to see at a glance whether a DayZ update changed a file.

## How to read the counts

- The counts are text lines on `P:\`, counting a last line with no line break, on the DayZ 1.30 data the citations were read on.
- The `config.cpp` files on `P:\` are unpacked with string arrays over several lines. The same config unpacked with each array on one line is much shorter, so compare a `config.cpp` count only with one taken in the same layout.
- The motorbike files are read from source (Enforce Script, `config.cpp` and the text animation graph). A line is tested in game only where it says it was measured in game.
- After a DayZ update, run the repo integrity test (`python -m pytest -q scripts/dev/test_repo_integrity.py`); it flags every full `P:\` citation whose line no longer holds the symbol named beside it.

## Where the motorbike sounds are

`P:\DZ\sounds\vehicles\config.cpp` (`:1` to `:10`) holds only the `CfgPatches` class `DZ_Sounds_Vehicles` and defines no sound class. The motorbike sound classes are in `P:\DZ\sounds\hpp\config.cpp` (524,933 lines):

| Block | Block spans | `Motorbike_0*` classes | What they cover |
|---|---|---|---|
| `CfgSoundShaders` | `:3072` to `:319048` | `:317170` to `:318910` | Engine rpm, overrun, brake, dampers, tyres on each surface, crash |
| `CfgSoundSets` | `:319049` to `:386918` | `:385779` to `:386870` | Gear shift, kickstart, lights, getting on and off, short, long and looping horn, rpm sets |

## Engine and base scripts (3_Game)

| File on `P:\` | Lines | Symbols read |
|---|---|---|
| `P:\bin\config.cpp` | 11105 | `class Motorbike: Transport`, `simulation = "motorbike"` |
| `P:\scripts\3_game\vehicles\motorbike.c` | 370 | Motorbike `proto native` signatures, `MotorbikeOwnerState`, `MotorbikeMove`, sound and stability callbacks |
| `P:\scripts\3_game\vehicles\transport.c` | 1214 | `ETransportFluid`, `NeedElectricitySourceDevice`, `IsAnyCrewPresent`, `OnContact`, `m_ContactCache`, `VehicleContactData` |
| `P:\scripts\3_game\vehicles\car.c` | 507 | `enum CarFluid : ETransportFluid` |
| `P:\scripts\3_game\vehicles\boat.c` | 207 | `enum BoatFluid : ETransportFluid` |
| `P:\scripts\3_game\constants.c` | 1168 | `MOTORBIKES_CONTACT_DMG_*`, `ENVIRO_HEATCOMFORT_MOTORBIKE_*` |
| `P:\scripts\3_game\human.c` | 1721 | `HumanAnimInterface.IsTag()`, `HumanCommandVehicle.IsTransitioning()` |
| `P:\scripts\3_game\dayzplayer.c` | 1413 | Player constants |
| `P:\scripts\3_game\dustkickupeffects.c` | 256 | Projectile dust effects singleton |
| `P:\scripts\3_game\enums\evehiclevfxtypes.c` | 17 | `EVehicleVFXEffect`, `EVehicleVFXEffectGroup` |
| `P:\scripts\3_game\entities\object.c` | 1467 | `GetBonePivotsForAnimationSource`, `GetBoneRotationMS` |

## Gameplay and entity scripts (4_World)

| File on `P:\` | Lines | Symbols read |
|---|---|---|
| `P:\scripts\4_world\entities\vehicles\motorbikescript.c` | 1780 | Lifecycle, kickstand, starting, `drivewheel` lights, damage, network sync |
| `P:\scripts\4_world\entities\vehicles\carscript.c` | 2981 | 1.30 refactor, component delegation, deprecated methods marked with `[Obsolete]` |
| `P:\scripts\4_world\entities\vehicles\vehicleaniminstances.c` | 15 | `MOTO1 = 10`, `MOTO2 = 11` |
| `P:\scripts\4_world\entities\vehicles\inheritedmotorbikes\motorbike_01.c` | 168 | `Motorbike_01_ColorBase`, `SeatDriver`, `ActionAnimateMotorbikeSeat`, SoundSets |
| `P:\scripts\4_world\entities\vehicles\inheritedmotorbikes\motorbike_02.c` | 139 | `Motorbike_02_ColorBase`, `ShieldFront`, `ShieldLeft` and `ShieldRight` fairings, thermal comfort |
| `P:\scripts\4_world\entities\vehicles\inheritedcars\civiliansedan.c` | 497 | Lights and horn migration to components |
| `P:\scripts\4_world\entities\vehicles\inheritedcars\offroad_02.c` | 475 | `HasGangedTailAndBrakeLights`, shared lights |
| `P:\scripts\4_world\entities\vehicles\components\vehiclehorncomponent.c` | 111 | Horn modes, AI noise, `NoiseCarHorn` integration |
| `P:\scripts\4_world\entities\vehicles\components\vehiclelightscomponent.c` | 190 | Registration of light selections and profiles |
| `P:\scripts\4_world\entities\vehicles\components\vehiclevfxcomponent.c` | 588 | Particles, exhaust and wheel smoke |
| `P:\scripts\4_world\entities\scriptedlightbase\spotlightbase\vehiclelightbase.c` | 86 | Generic vehicle spotlight with parameters |
| `P:\scripts\4_world\entities\scriptedlightbase\spotlightbase\vehiclelightprofiles\vehiclelightprofilebase.c` | 95 | Base aggregated and segregated lighting profile |
| `P:\scripts\4_world\entities\scriptedlightbase\spotlightbase\vehiclelightprofiles\motorbike_01.c` | 34 | `Motorbike_01LightProfileFront`, `Motorbike_01LightProfileRear` |
| `P:\scripts\4_world\entities\scriptedlightbase\spotlightbase\vehiclelightprofiles\motorbike_02.c` | 34 | `Motorbike_02LightProfileFront` |
| `P:\scripts\4_world\entities\dayzplayerimplement.c` | 4131 | Crash ejection (`CrewShouldEject` / `eModifiers.MDF_UNCONSCIOUSNESS`), bike death (`FallOver`) |
| `P:\scripts\4_world\entities\dayzplayerimplementfalldamage.c` | 378 | `CurveExp` exponential curve and new thresholds |
| `P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercameras.c` | 173 | Registration of `DAYZCAMERA_3RD_VEHICLE_MOTORBIKE = 32` |
| `P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercameravehicles.c` | 473 | Implementation of `DayZPlayerCamera3rdPersonVehicleMotorbike` with spring lag |
| `P:\scripts\4_world\entities\manbase\playerbase.c` | 10144 | Engine start and stop actions registration |
| `P:\scripts\4_world\entities\itembase\blowtorch.c` | 146 | The only place the chassis, engine and part repair actions for bikes are added (`:109`, `:111`, `:113`) |
| `P:\scripts\4_world\entities\core\inherited\inventoryitem.c` | 1377 | `ActionPickUpMotorbike` on the `Motorbike_02` side fairings |
| `P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c` | 1658 | `AddItemInHandsProfileIK` registrations, `DayZPlayerTypeRegisterItems`, animation instance preload |

## User actions (4_World)

| File on `P:\` | Lines | Symbols read |
|---|---|---|
| `P:\scripts\4_world\classes\useractionscomponent\actions\continuous\vehicles\actionstartenginemotorbike.c` | 100 | Continuous kickstart action, `OnIgnition()` |
| `P:\scripts\4_world\classes\useractionscomponent\actions\singleuse\vehicles\actionstopenginemotorbike.c` | 76 | Engine stop action capped at 8 km/h |
| `P:\scripts\4_world\classes\useractionscomponent\actions\interact\vehicles\actionpickupmotorbike.c` | 104 | Picking up a fallen bike (`trans.PickUp()`) |
| `P:\scripts\4_world\classes\useractionscomponent\actions\interact\vehicles\actionanimatemotorbikeseat.c` | 47 | `SeatDriver` tilting |
| `P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionrepairmotorbikechassis.c` | 55 | Base chassis repair |
| `P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionrepairmotorbikechassiswithblowtorch.c` | 46 | Chassis repair with blowtorch |
| `P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionrepairmotorbikeengine.c` | 60 | Base engine repair (orphaned) |
| `P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionrepairmotorbikeenginewithblowtorch.c` | 45 | Engine repair with blowtorch |
| `P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionrepairmotorbikepart.c` | 160 | Base part and fairing repair |
| `P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionrepairmotorbikepartwithblowtorch.c` | 46 | Part repair with blowtorch |
| `P:\scripts\4_world\classes\useractionscomponent\actions\continuous\vehicles\actionvehiclehorn.c` | 350 | `ActionVehicleHornShort`, `ActionVehicleHornLong` |
| `P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetintransport.c` | 159 | Directional mounting via lateral dot product |
| `P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetouttransport.c` | 274 | Jump out while moving above 10 km/h |
| `P:\scripts\4_world\classes\useractionscomponent\actionconstructor.c` | 399 | Registration of every action |
| `P:\scripts\4_world\classes\useractionscomponent\actioninput.c` | 1035 | `ToggleVehicleLightsActionInput`, `ToggleLightsActionInput`, pre-1.30 horn input aliases |
| `P:\scripts\4_world\classes\useractionscomponent\actions\interact\vehicles\actionswitchlights.c` | 72 | `ActionSwitchLights.GetInputType()` |
| `P:\scripts\4_world\classes\useractionscomponent\actions\continuous\vehicles\actionfillfuel.c` | 69 | `FUEL_SELECTION_NAME = "refill"` |
| `P:\scripts\4_world\classes\useractionscomponent\actions\continuous\vehicles\actioncarhorn.c` | 361 | Pre-1.30 horn action names kept for compatibility |

## HUD (5_Mission)

| File on `P:\` | Lines | Symbols read |
|---|---|---|
| `P:\scripts\5_mission\gui\vehicles\motorbikehud.c` | 248 | Tachometer, speedometer, fuel gauge, disabled warning indicators (handbrake, temperature) |
| `P:\scripts\5_mission\gui\ingamehud.c` | 1316 | `m_VehicleHudMap` entry `"VehicleTypeMotorbike"` |

## Vehicle configs, animation and sound files

| File on `P:\` | Lines | Symbols read |
|---|---|---|
| `P:\DZ\vehicles\singletrack\config.cpp` | 2382 | Every vanilla motorbike class (`MotorbikeScript`, `Motorbike_01`, `Motorbike_02`, wheels, proxies) |
| `P:\DZ\vehicles\wheeled\config.cpp` | 24369 | Vanilla car config, new wheel parameters (`tyreRoughness`, `tyreLongitudinalFriction`, `tyreLateralFriction`) |
| `P:\DZ\anims\workspaces\player\player_main\vehicles.agf` | 3655 | The vehicle animation graph as text, `MotorBikeB` node, `MotorBikeSTM` state machine |
| `P:\DZ\anims\workspaces\player\player_main\player_main.ast` | 1268 | `"Jawa_05"` and `"Jawa_Bitrak"` animation columns |
| `P:\DZ\anims\workspaces\player\player_main\player_main.asi` | 6679 | `.anm` clip mapping for motorbike riding poses |
| `P:\DZ\anims\workspaces\player\player_main\player_main_surrender.asi` | 296 | Header of a child `.asi` (`Template`, `ParentTemplates`) |
| `P:\bin\constants.xml` | 938 | Input names `UAToggleHeadlight` and `UAToggleVehicleLights` |
| `P:\DZ\sounds\hpp\config.cpp` | 524933 | The motorbike `CfgSoundShaders` and `CfgSoundSets` |
| `P:\DZ\sounds\vehicles\config.cpp` | 10 | Only `CfgPatches`, no sound classes |

## What changed from 1.29

Comparing a DayZ 1.29 and a 1.30 extraction is the source of what this pack says changed from 1.29 to 1.30. DayZ 1.29 is not on `P:\`, so those statements are not checked there. The `vehicles_singletrack` addon is new in 1.30 and has no 1.29 counterpart.

The 1.30 data on `P:\` splits the broken engine sound of `Motorbike_02` into two classes, `Motorbike_02_Engine_Ext_Broken_High_SoundShader` and `Motorbike_02_Engine_Ext_Broken_Low_SoundShader` (`P:\DZ\sounds\hpp\config.cpp:318210` and `:318223`), each with its own sound set (`:386435` and `:386443`). The behaviour changes are noted where they apply: light registrations, light profiles and particle cooldown in `motorbike-actions-hud-lights-sounds.md`, and the state of 1.30 in `motorbike-invariants.md`.
