# Motorbike actions, HUD, lights and sounds

Which user actions are specific to motorbikes, how `MotorbikeHud` reads the bike, how the lights, horn and particle components are set up, and where the motorbike sound classes live. In this file `config.cpp` alone means `P:\DZ\vehicles\singletrack\config.cpp`, `motorbikescript.c` means `P:\scripts\4_world\entities\vehicles\motorbikescript.c`, and `motorbike_01.c` and `motorbike_02.c` are the script classes in `P:\scripts\4_world\entities\vehicles\inheritedmotorbikes\`.

## Actions

The action files are under `P:\scripts\4_world\classes\useractionscomponent\actions\`; `actionconstructor.c` is `P:\scripts\4_world\classes\useractionscomponent\actionconstructor.c`.

| Action | Kind | Condition | Registered |
|---|---|---|---|
| `ActionStartEngineMotorbike` (`continuous\vehicles\actionstartenginemotorbike.c:9`) | Continuous, callback `ActionStartEngineMotorbikeCB` (`:1`) with `CAContinuousTime(UATimeSpent.START_ENGINE)` | Player in `HumanCommandVehicle` (`:28`), bike is a `MotorbikeScript` with the engine off (`:33`), player is the driver (`:36`) | `P:\scripts\4_world\entities\manbase\playerbase.c:1709`; `actionconstructor.c:223` |
| `ActionStopEngineMotorbike` (`singleuse\vehicles\actionstopenginemotorbike.c:1`) | Single use | Driver, engine running, and speed at most 8 km/h (`:29`), so the engine cannot be switched off at speed | `playerbase.c:1712`; `actionconstructor.c:76` |
| `ActionPickUpMotorbike` (`interact\vehicles\actionpickupmotorbike.c:1`) | Interact, instant | Target is a `Motorbike`, no heavy item in hands, the cursor is not on a seat (`CrewPositionIndex(componentIndex) < 0`), and `CanPickUp()` (`:64`); runs `PickUp()` (`:74`) | `motorbikescript.c:367`; the side fairings `Motorbike_02_ShieldLeft_ColorBase` and `Motorbike_02_ShieldRight_ColorBase` (`P:\scripts\4_world\entities\core\inherited\inventoryitem.c:499`, `:511`, `:539`, `:551`); `actionconstructor.c:348` |
| `ActionAnimateMotorbikeSeat` (`interact\vehicles\actionanimatemotorbikeseat.c:1`) | `ActionAnimateSeats` | No driver, player within 1 m, selection belongs to the `SeatDriver` source | `motorbike_01.c:101`; `actionconstructor.c:313` |

Starting runs in two steps. `OnExecute` (`actionstartenginemotorbike.c:66` to `:75`) calls `vehicle.OnIgnition()` (`:74`), which plays the kickstart sound through `HandleEngineSound(MotorbikeEngineSoundState.STARTING)` (`motorbikescript.c:1613` to `:1635`); with no spark plug or no fuel it plays the matching failed start sound and returns instead (`:1622` to `:1632`). `OnFinishProgress` (`:39` to `:64`) calls `vehicle.EngineStart()` (`:63`); the vanilla comment at `:51` says the engine checks the start through the `Motorbike.OnBeforeEngineStart()` callback.

## Repair actions

| Action | File (`continuous\`) | Tool | Target | In `actionconstructor.c` |
|---|---|---|---|---|
| `ActionRepairMotorbikeChassisWithBlowtorch` | `actionrepairmotorbikechassiswithblowtorch.c:9` | Blowtorch with gas | Chassis, a zone worse than `STATE_WORN` and better than `STATE_RUINED` (inherited, `actionrepairmotorbikechassis.c:42`) | `:259` |
| `ActionRepairMotorbikeChassis` | `actionrepairmotorbikechassis.c:1` | Base, no vanilla tool | Chassis | `:255` |
| `ActionRepairMotorbikeEngineWithBlowtorch` | `actionrepairmotorbikeenginewithblowtorch.c:9` | Blowtorch | `Engine` | `:260` |
| `ActionRepairMotorbikeEngine` | `actionrepairmotorbikeengine.c:1` | Base, not used | `Engine` | Not registered |
| `ActionRepairMotorbikePartWithBlowTorch` | `actionrepairmotorbikepartwithblowtorch.c:9` | Blowtorch | Parts and fairings (`MotorbikePart`) | `:253` |
| `ActionRepairMotorbikePart` | `actionrepairmotorbikepart.c:12` | Base | Parts and fairings | `:252` |

How to repair with hand tools is in `motorbike-invariants.md`.

## The HUD

`MotorbikeHud : VehicleHudBase` (`P:\scripts\5_mission\gui\vehicles\motorbikehud.c`) reuses the car layout `gui/layouts/day_z_hud_cars.layout` (`:36`). `MotorbikeScript.GetVehicleType()` returns `"VehicleTypeMotorbike"` (`motorbikescript.c:316` to `:319`), and the in-game HUD maps that name to the bike HUD with `m_VehicleHudMap.Insert("VehicleTypeMotorbike", motorbikeHud)` (`P:\scripts\5_mission\gui\ingamehud.c:183`).

| Gauge | How `RefreshVehicleHud` drives it | Line in `motorbikehud.c` |
|---|---|---|
| Rev counter | `EngineGetRPM() / EngineGetRPMMax()`, needle at `rpm_value * 270 - 130`; redline from `EngineGetRPMRedline() / EngineGetRPMMax()` | `:105`, `:106`, `:109` |
| Speedometer | `GetSpeedometerAbsolute() / 200`, needle at `speed_value * 260 - 130`; text `Math.AbsInt(GetSpeedometer())` | `:107`, `:110`, `:111` |
| Gear | `UpdateGear()` reads `GetGear()`; with `CarGearboxType.MANUAL` it sets current, previous and next from an R, N, 1 to 8 table | `:217` to `:237`, table `:77` to `:88` |
| Fuel | `GetFluidFraction(MotorbikeFluid.FUEL) * 260 - 130` | `:204` |
| Engine light | `GetHealthLevel("Engine")`, blinking while `HasEngineZoneReceivedHit()` | `:118` to `:137` |
| Wheel lock | Lit while `WheelIsAnyLocked()` | `:197` |

Two car gauges are hidden: the handbrake light, always (`:196`, vanilla comment "no kickstand while on bike"), and the temperature gauge, because `IsVitalRadiator()` is `false` (`:191` to `:194`).

## Lights

`VehicleLightsComponent` (`P:\scripts\4_world\entities\vehicles\components\vehiclelightscomponent.c`) pairs a light state with a material selection; the first argument is the `SetObjectMaterial` index (`:66` to `:81`). The base registrations (`motorbikescript.c:114` to `:122`):

```c
m_LightsComponent.RegisterSelection("FrontOn", {new VehicleLightSelectionData(0, "frontReflectorMatOn")});
m_LightsComponent.RegisterSelection("BrakeOn", {new VehicleLightSelectionData(1, "brakeReflectorMatOn")});
```

- Each vanilla bike registers `FrontOn`, `FrontOff`, `BrakeOn` and `BrakeOff` again on its own material indexes: `Motorbike_01` front 3 and brake 2 (`motorbike_01.c:19` to `:22`), `Motorbike_02` front 4 and brake 6 (`motorbike_02.c:20` to `:23`). The base also registers `TailOn`, `TailOff`, `DashboardOn` and `DashboardOff` on indexes 2 and 3 (`motorbikescript.c:118` to `:122`). A custom bike whose `hiddenSelections` order differs must register all of them again with its own indexes, or the wrong part lights up.
- Outside braking, both the `default` case and the `else` branch set `"BrakeOff"` when `HasGangedTailAndBrakeLights()` is `false` (`motorbikescript.c:1246` to `:1255`). The base returns `false` (`:169` to `:172`) and neither vanilla bike overrides it.
- The front light attaches to the `drivewheel` bone so it turns with the bars (`motorbikescript.c:1122` to `:1124`):

```c
int driveWheelIndex = GetBoneIndex("drivewheel");
m_LightsComponent.AttachLightOnObject("Front", GetMemoryPointPos(m_HeadLightPoint), vector.Zero, VehicleLightMode.SEGREGATED, driveWheelIndex);
```

The light profiles are classes on `VehicleLightProfileFront` and `VehicleLightProfileBrakeAndReverse` in `P:\scripts\4_world\entities\scriptedlightbase\spotlightbase\vehiclelightprofiles\motorbike_01.c` and `motorbike_02.c`:

| Profile | Brightness | Radius | Angle | Colour (RGB) | Lines |
|---|---|---|---|---|---|
| `Motorbike_01LightProfileFront` | 8 | 30 m | 50 degrees | `0.85, 0.85, 0.68` | `:5` to `:8` |
| `Motorbike_01LightProfileRear`, brake | 4 | 6 m | 120 degrees | `0.95, 0.16, 0.05` | `:17` to `:20` |
| `Motorbike_02LightProfileFront` | 8 | 65 m | 65 degrees | `0.85, 0.85, 0.68` | `:5` to `:8` |

The light switch uses the vehicle lights input, not the head torch. `ActionSwitchLights.GetInputType()` returns `ToggleVehicleLightsActionInput` (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\vehicles\actionswitchlights.c:16` to `:19`), which calls `SetInput("UAToggleVehicleLights")` (`P:\scripts\4_world\classes\useractionscomponent\actioninput.c:849` to `:855`). `ToggleLightsActionInput` still uses `UAToggleHeadlight`, the head torch (`actioninput.c:776` to `:782`). Both names are in `P:\bin\constants.xml:90` and `:91`. A custom `inputs.xml` that only binds `UAToggleHeadlight` turns on the head torch, not the bike's headlight.

## Horn and particles

`VehicleHornComponent` (`P:\scripts\4_world\entities\vehicles\components\vehiclehorncomponent.c`) has the modes `OFF`, `SHORT` and `LONG`, syncs `m_Mode` over the network, and on the server makes noise for infected in `GenerateHornAINoise` (`:95`), which loads the bike's `NoiseCarHorn` class (`:86`), which sets `strength=30` (`config.cpp:148` to `:152`). `CarHornShortActionInput : VehicleHornShortActionInput {}` (`actioninput.c:757` and `:758`) is an empty shell kept for 1.29 mods; register `ActionVehicleHornShort` and `ActionVehicleHornLong` (`actionconstructor.c:340` and `:341`).

`VehicleVFXComponent` (`P:\scripts\4_world\entities\vehicles\components\vehiclevfxcomponent.c`) gets its effects in `motorbikescript.c:174` to `:205`:

| Effect | Class | Memory points | Line |
|---|---|---|---|
| `DUST_BEHIND` | `EffVehicleDust` | `ptcDustPos` | `:199` |
| `ENGINE_SMOKE` | `EffEngineSmoke` | `ptcEnginePos` | `:200` |
| `EXHAUST_SMOKE` | `EffExhaustSmoke` | Between `ptcExhaust_start` and `ptcExhaust_end` | `:201` |
| `WHEEL_SMOKE`, `WHEEL_CONTACT` | `EffWheelSmoke`, `EffWheelContact` | Per wheel, 2.0 s cooldown (third `VehicleVFXDataParams` argument) | `:203`, `:204` |

`VehicleVFXDataParams` takes a position, an orientation and the cooldown in seconds, which defaults to 0 (`vehiclevfxcomponent.c:82` to `:94`). The `engine` memory point is read for the drowning check (`motorbikescript.c:181`).

## Sound classes

The motorbike sound classes are in `P:\DZ\sounds\hpp\config.cpp`: the `Motorbike_0*` sound shaders at lines 317170 to 318910 and the sound sets at 385779 to 386870. `P:\DZ\sounds\vehicles\config.cpp` holds only `CfgPatches` (`DZ_Sounds_Vehicles`, `:1` to `:10`). Line numbers below are in `P:\DZ\sounds\hpp\config.cpp`.

| Sound | Classes | Line |
|---|---|---|
| Engine, accelerating | `Motorbike_01_Engine_Ext_Rpm0_SoundShader` to `Rpm6`, layered on `rpm` and `thrust` | `:317170` to `:317313` |
| Engine, overrun on release | `Motorbike_01_Engine_Offload_Ext_Rpm1_SoundShader` to `Offload_Rpm6` | `:317196` to `:317326` |
| `Motorbike_02` engine | 8 accelerating layers (`Rpm0` to `Rpm7`) and 7 overrun layers (`Offload_Rpm1` to `Offload_Rpm7`) | `:318015` to `:318197` |
| Start | `Motorbike_01_engine_start_SoundSet`, sample `\DZ\sounds\vehicles\Motorbike_01\engine_start` | `:386137`, shader `:317684` |
| Failed start, no fuel | `Motorbike_01_engine_failed_start_fuel_SoundSet` | `:386147` |
| Stop, stop on empty | `Motorbike_01_engine_stop_SoundSet`, `Motorbike_01_engine_stop_fuel_SoundSet` | `:386157`, `:386166` |
| Kickstart | `Motorbike_01_Kickstart_FoldOut_SoundSet` (lever out), `Motorbike_01_Starting_Engine_Off_SoundSet` (kick with no start) | `:386229`, `:386236` |
| Horn | `Motorbike_01_Horn_SoundSet` (`loop = 1`), `Motorbike_01_Horn_Short_SoundSet` (`volumefactor = 0.4`), `Motorbike_01_Horn_Start_SoundSet` and `_End_SoundSet` | `:386282`, `:386291`, `:386299` to `:386307` |
| Dampers | `Motorbike_01_damper_front_SoundSet`, `Motorbike_01_damper_rear_SoundSet`, both on `Motorbike_01_damper_SoundShader` with ten samples `motorbike_damper_01` to `_10` | `:386052`, `:386070`, `:317627` |

The script classes name the rest: `Motorbike_01_Seat_FlipUp_SoundSet` and `Motorbike_01_Seat_FlipDown_SoundSet` (`motorbike_01.c:116`, `:120`), `Motorbike_01_hit_character_SoundSet` and `Motorbike_01_hit_heavy_SoundSet` (`motorbike_01.c:140`, `:147`). The horn sound sets are registered per bike with `m_HornComponent.RegisterSound` (`motorbike_01.c:24` and `:25`), so a custom bike sets its own there.
