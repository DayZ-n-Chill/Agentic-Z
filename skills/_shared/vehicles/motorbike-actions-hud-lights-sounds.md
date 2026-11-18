# Motorbike actions, HUD, lights and sounds

The user actions specific to motorbikes in DayZ 1.30, the structure of `MotorbikeHud`, the lights, horn and VFX components, and the sound classes in `P:\DZ\sounds\hpp\config.cpp` (written `sounds\hpp\config.cpp` below). Short citations: `config.cpp:N` is `P:\DZ\vehicles\singletrack\config.cpp`, and a bare script file name is the file of that name under `P:\scripts\` (`motorbike_01.c` and `motorbike_02.c` are the ones in `4_world\entities\vehicles\inheritedmotorbikes\`). Line numbers match the 1.30 data on `P:\` at the time of writing; when a line has moved, Grep for the symbol.

---

## 1. Motorbike User Actions

### `ActionStartEngineMotorbike`
- **File**: `P:\scripts\4_world\classes\useractionscomponent\actions\continuous\vehicles\actionstartenginemotorbike.c:9`.
- **Type**: Continuous action (`ActionContinuousBase`), uses `ActionStartEngineMotorbikeCB` with `CAContinuousTime(UATimeSpent.START_ENGINE)`.
- **Condition (`ActionCondition`)**:
  - Player in `HumanCommandVehicle` (`actionstartenginemotorbike.c:28`).
  - Vehicle is `MotorbikeScript` and its engine is off (`if (!vehicle || vehicle.EngineIsOn())` returns `false`, `actionstartenginemotorbike.c:33`).
  - The player is the driver (`vehicle.CrewDriver() == player`, `actionstartenginemotorbike.c:36`).
- **Execution**:
  - In `OnExecute` (`actionstartenginemotorbike.c:66-75`): invokes `vehicle.OnIgnition()` (`actionstartenginemotorbike.c:74`), which plays the kickstart sound with `HandleEngineSound(MotorbikeEngineSoundState.STARTING)` (`motorbikescript.c:1598-1620`, called at `1619`).
  - In `OnFinishProgress` (`actionstartenginemotorbike.c:39-64`): invokes `vehicle.EngineStart()` (`actionstartenginemotorbike.c:63`). According to the comment at `actionstartenginemotorbike.c:51`, validation is performed by C++ via the `Motorbike.OnBeforeEngineStart()` callback.
- **Registration**: In `playerbase.c:1709` (`AddAction(ActionStartEngineMotorbike, InputActionMap);`) and in `actionconstructor.c:223`.

### `ActionStopEngineMotorbike`
- **File**: `P:\scripts\4_world\classes\useractionscomponent\actions\singleuse\vehicles\actionstopenginemotorbike.c:1`.
- **Type**: Single-use action (`ActionSingleUseBase`).
- **Condition**: Driver on `MotorbikeScript`, engine running (`vehicle.EngineIsOn()`), and absolute speed of at most 8 km/h (`if (vehicle.GetSpeedometerAbsolute() > 8)` returns `false`, `actionstopenginemotorbike.c:29`). Cannot be manually turned off at high speed.
- **Registration**: In `playerbase.c:1712` and in `actionconstructor.c:76`.

### `ActionPickUpMotorbike`
- **File**: `P:\scripts\4_world\classes\useractionscomponent\actions\interact\vehicles\actionpickupmotorbike.c:1`.
- **Type**: Direct interaction (`ActionInteractBase`, `IsInstant() = true`).
- **Condition**: The object is `Motorbike`, player is not carrying a heavy item in hands (`!IsHeavyBehaviour()`), cursor does not point to a seat (`trans.CrewPositionIndex(componentIndex) < 0`), and the bike is fallen over and eligible to be picked up (`trans.CanPickUp()`, `actionpickupmotorbike.c:64`).
- **Execution**: Invokes `trans.PickUp();` (`actionpickupmotorbike.c:74`).
- **Registration**: `AddAction(ActionPickUpMotorbike)` in `motorbikescript.c:367` and in the side fairing classes `Motorbike_02_ShieldLeft_ColorBase` and `Motorbike_02_ShieldRight_ColorBase` (`P:\scripts\4_world\entities\core\inherited\inventoryitem.c:499, 511, 539, 551`), and in `actionconstructor.c:348`.

### `ActionAnimateMotorbikeSeat`
- **File**: `P:\scripts\4_world\classes\useractionscomponent\actions\interact\vehicles\actionanimatemotorbikeseat.c:1`.
- **Type**: `ActionAnimateSeats`.
- **Condition**: Seat without driver (`!bike.CrewMember(VEHICLESEAT_DRIVER)`), player closer than 1 meter, and selection belongs to animation source `"SeatDriver"`.
- **Registration**: In `motorbike_01.c:104` (`AddAction(ActionAnimateMotorbikeSeat);`) and in `actionconstructor.c:313`.

### Motorbike Repair Actions
| Action | File | Required tool | Target zone | Registration in ActionConstructor |
|---|---|---|---|---|
| `ActionRepairMotorbikeChassisWithBlowtorch` | `actionrepairmotorbikechassiswithblowtorch.c:9` | `Blowtorch` (blowtorch with gas) | Chassis: damaged zone between `WORN` and `RUINED` (inherited condition, `actionrepairmotorbikechassis.c:31-47`) | Yes (`actionconstructor.c:259`) |
| `ActionRepairMotorbikeChassis` | `actionrepairmotorbikechassis.c:1` | Base without vanilla tool | Chassis | Yes (`actionconstructor.c:255`) |
| `ActionRepairMotorbikeEngineWithBlowtorch` | `actionrepairmotorbikeenginewithblowtorch.c:9` | `Blowtorch` | Engine (`"Engine"`) | Yes (`actionconstructor.c:260`) |
| `ActionRepairMotorbikeEngine` | `actionrepairmotorbikeengine.c:1` | Base (orphaned) | Engine | No (0 occurrences in `actionconstructor.c`) |
| `ActionRepairMotorbikePartWithBlowTorch` | `actionrepairmotorbikepartwithblowtorch.c:9` | `Blowtorch` | Parts / fairings (`MotorbikePart`) | Yes (`actionconstructor.c:253`) |
| `ActionRepairMotorbikePart` | `actionrepairmotorbikepart.c:12` | Base | Parts / fairings | Yes (`actionconstructor.c:252`) |

---

## 2. Vehicle HUD: `MotorbikeHud`

- **File**: `P:\scripts\5_mission\gui\vehicles\motorbikehud.c:1-248`.
- **Inheritance**: `class MotorbikeHud : VehicleHudBase`.
- **Reused base layout**: `"gui/layouts/day_z_hud_cars.layout"` (`motorbikehud.c:36`).
- **Entity binding**: `motorbikescript.c:316-319` returns `"VehicleTypeMotorbike"`, registered in `P:\scripts\5_mission\gui\ingamehud.c:183` (`m_VehicleHudMap.Insert("VehicleTypeMotorbike", motorbikeHud)`).
- **Active instrumentation (`RefreshVehicleHud`)**:
  - **RPM and Tachometer**: Reads `EngineGetRPM() / EngineGetRPMMax()` (`motorbikehud.c:105`). The needle rotates with `rpm_value * 270 - 130` (`motorbikehud.c:109`). Redline is calculated with `EngineGetRPMRedline() / EngineGetRPMMax()` (`motorbikehud.c:106`).
  - **Speedometer**: Absolute speed divided by 200 for needle (`speed_value * 260 - 130`, `motorbikehud.c:110`) and numeric text via `Math.AbsInt(GetSpeedometer()).ToString()` (`motorbikehud.c:111`).
  - **Gears**: `UpdateGear()` queries `GetGear()` (`motorbikehud.c:217-237`). On manual transmission (`CarGearboxType.MANUAL`, `motorbikehud.c:229`) it updates `Current`, `Prev`, and `Next` (`motorbikehud.c:231-236`) with the R/N/1-8 table built in `motorbikehud.c:77-88`.
  - **Fuel level**: Reads `GetFluidFraction(MotorbikeFluid.FUEL) * 260 - 130` (`motorbikehud.c:204`).
  - **Engine light**: Queries `GetHealthLevel("Engine")`. Blinks if `HasEngineZoneReceivedHit()` is active (`motorbikehud.c:118-137`).
  - **Wheel lock**: Illuminates if `WheelIsAnyLocked()` returns `true` (`motorbikehud.c:197`).
- **Visual differences compared to cars**:
  - Handbrake light **hidden**: `m_VehicleHandBrakeLight.Show(false);` (`motorbikehud.c:196`).
  - Temperature indicator **hidden**: `m_VehicleTemperatureIndicator.Show(false);` because `IsVitalRadiator()` returns `false` (`motorbikehud.c:191-194`).

---

## 3. Modular Vehicle Components

### `VehicleLightsComponent` (`vehiclelightscomponent.c:1-190`)
- Allows registering rvmat material selections associated with light states:
  ```c
  m_LightsComponent.RegisterSelection("FrontOn", {new VehicleLightSelectionData(0, "frontReflectorMatOn")});
  m_LightsComponent.RegisterSelection("BrakeOn", {new VehicleLightSelectionData(1, "brakeReflectorMatOn")});
  ```
- Those are the base registrations (`motorbikescript.c:114-122`); the first argument is the `SetObjectMaterial` index (`vehiclelightscomponent.c:66-81`). Each vanilla bike then registers `BrakeOn` and `BrakeOff` again on index 2 (`motorbike_01.c:19-20`, `motorbike_02.c:20-21`). From build 1.30.164200 the vanilla bikes also register `FrontOn` and `FrontOff` on their own index (Motorbike_01 front 3 and brake 2, Motorbike_02 front 4 and brake 6); not yet checked on `P:\`.
- Rear light off: the `else` branch sets `"BrakeOff"` only when `HasGangedTailAndBrakeLights()` returns `false` (`motorbikescript.c:1236-1240`). The base returns `false` (`motorbikescript.c:169-172`) and both vanilla bikes override it to `true` (`motorbike_01.c:28-31`, `motorbike_02.c:29-32`). The `default` case of the same switch names the key `"BrakesOff"`, which nothing registers (`motorbikescript.c:1231-1233`). From build 1.30.164200 neither bike overrides it and the `default` case names `"BrakeOff"`; not yet checked on `P:\`.
- Supports dedicated light profiles (classes on `VehicleLightProfileFront` and `VehicleLightProfileBrakeAndReverse`), set in `P:\scripts\4_world\entities\scriptedlightbase\spotlightbase\vehiclelightprofiles\motorbike_01.c:1-34` and `motorbike_02.c` in the same folder:
  - `Motorbike_01LightProfileFront`: brightness 2, radius 30m, angle 50º, RGB color `(0.85, 0.85, 0.68)` (lines 5-8). Brightness is 8 from build 1.30.164200; not yet checked on `P:\`.
  - `Motorbike_01LightProfileRear`: brake light brightness 4, radius 6m, angle 120º, RGB color `(0.95, 0.16, 0.05)` (lines 17-20).
  - `Motorbike_02LightProfileFront`: brightness 3, radius 65m, angle 65º, RGB color `(0.85, 0.85, 0.68)` (lines 5-8 of its file). Brightness is 8 from build 1.30.164200; not yet checked on `P:\`.
- Handlebar attachment:
  `int driveWheelIndex = GetBoneIndex("drivewheel");` and `m_LightsComponent.AttachLightOnObject("Front", GetMemoryPointPos(m_HeadLightPoint), vector.Zero, VehicleLightMode.SEGREGATED, driveWheelIndex);` (`motorbikescript.c:1107-1109`).

### `VehicleHornComponent` (`vehiclehorncomponent.c:1-111`)
- Manages modes `OFF`, `SHORT`, `LONG`.
- On server triggers `GenerateHornAINoise` loading `NoiseCarHorn` from `config.cpp` (`strength = 30.0`).
- Synchronizes integer variable `m_HornComponent.m_Mode` over the network.

### `VehicleVFXComponent` (`vehiclevfxcomponent.c:1-588`)
- Registers particles in `motorbikescript.c:174-205`:
  - `DUST_BEHIND` (`EffVehicleDust`) at the memory point `ptcDustPos` (`motorbikescript.c:199`).
  - `ENGINE_SMOKE` (`EffEngineSmoke`) at the memory point `ptcEnginePos` (`motorbikescript.c:200`). The memory point `engine` is read for the drowning check (`motorbikescript.c:181`).
  - `EXHAUST_SMOKE` (`EffExhaustSmoke`) oriented between `ptcExhaust_start` and `ptcExhaust_end`.
  - Wheel groups: `WHEEL_SMOKE` (`EffWheelSmoke`) and `WHEEL_CONTACT` (`EffWheelContact`), with a 5.0 s cooldown (third `VehicleVFXDataParams` argument, `vehiclevfxcomponent.c:82-94`) (`motorbikescript.c:203-204`). The cooldown is 2.0 s from build 1.30.164200; not yet checked on `P:\`.

---

## 4. Sound Configuration (`CfgSoundShaders` and `CfgSoundSets`)

The motorbike sound classes are in `P:\DZ\sounds\hpp\config.cpp`: the `Motorbike_0*` SoundShaders at `sounds\hpp\config.cpp:316513-318260` and the SoundSets at `:383946-385036`. `P:\DZ\sounds\vehicles\config.cpp:1-10` holds only `CfgPatches` (`DZ_Sounds_Vehicles`).

### Engine Shaders (RPM and Offload)
- `Motorbike_01_Engine_Ext_Rpm0_SoundShader` through `Rpm6_SoundShader` (`P:\DZ\sounds\hpp\config.cpp:316513-316668`): acceleration layers based on `rpm` and `thrust`.
- `Motorbike_01_Engine_Offload_Ext_Rpm1_SoundShader` through `Offload_Rpm6_SoundShader` (`sounds\hpp\config.cpp:316539-316681`): offload overrun layers upon releasing throttle.
- Equivalents in `Motorbike_02`: 8 acceleration layers (`Rpm0` to `Rpm7`) and 7 offload layers (`Offload_Rpm1` to `Offload_Rpm7`) (`sounds\hpp\config.cpp:317358-317552`).

### Primary SoundSets Registered in Script
- **Starting and stopping**:
  - `Motorbike_01_engine_start_SoundSet` (`sounds\hpp\config.cpp:384304-384313`) -> sample `\DZ\sounds\vehicles\Motorbike_01\engine_start`.
  - `Motorbike_01_engine_failed_start_fuel_SoundSet` (`sounds\hpp\config.cpp:384314`) -> `\DZ\sounds\vehicles\Motorbike_01\engine_failed_start_fuel`.
  - `Motorbike_01_engine_stop_SoundSet` (`sounds\hpp\config.cpp:384324`) -> `\DZ\sounds\vehicles\Motorbike_01\engine_stop`.
  - `Motorbike_01_engine_stop_fuel_SoundSet` (`sounds\hpp\config.cpp:384333`) -> `\DZ\sounds\vehicles\Motorbike_01\engine_stop_fuel`.
- **Kickstart**:
  - `Motorbike_01_Kickstart_FoldOut_SoundSet` (`sounds\hpp\config.cpp:384396`) -> lever fold out.
  - `Motorbike_01_Starting_Engine_Off_SoundSet` (`sounds\hpp\config.cpp:384403`) -> false kick sound.
- **Horn**:
  - `Motorbike_01_Horn_SoundSet` (`sounds\hpp\config.cpp:384449`): continuous loop (`loop = 1`).
  - `Motorbike_01_Horn_Short_SoundSet` (`sounds\hpp\config.cpp:384458`): short honk (`volumefactor = 0.8`).
  - `Motorbike_01_Horn_Start_SoundSet` and `Motorbike_01_Horn_End_SoundSet` (`sounds\hpp\config.cpp:384466-384481`).
- **Flip-up seat (`Motorbike_01`)**:
  - `Motorbike_01_Seat_FlipUp_SoundSet` and `Motorbike_01_Seat_FlipDown_SoundSet` (`motorbike_01.c:119, 123`).
- **Shock Absorbers and Collision**:
  - `Motorbike_01_damper_front_SoundSet` and `Motorbike_01_damper_rear_SoundSet` (`sounds\hpp\config.cpp:384219, 384237`), both based on `Motorbike_01_damper_SoundShader` (`sounds\hpp\config.cpp:316970`), with 10 samples `motorbike_damper_01` through `motorbike_damper_10`.
  - `Motorbike_01_hit_character_SoundSet` and `Motorbike_01_hit_heavy_SoundSet` (`motorbike_01.c:143, 150`).

## 5. Lights input: `UAToggleVehicleLights` versus `UAToggleHeadlight`

`ActionSwitchLights` (common to cars and motorbikes) uses the **vehicle** lights action, not the headtorch:

```c
// [EXACT] P:\scripts\4_world\classes\useractionscomponent\actions\interact\vehicles\actionswitchlights.c:16-19
	override typename GetInputType()
	{
		return ToggleVehicleLightsActionInput;
	}
```

```c
// [EXACT] P:\scripts\4_world\classes\useractionscomponent\actioninput.c:849-855
class ToggleVehicleLightsActionInput : DefaultActionInput
{
	ref ActionTarget targetNew;
	
	void ToggleVehicleLightsActionInput(PlayerBase player)
	{
		SetInput("UAToggleVehicleLights");
```

`ToggleLightsActionInput` still executes `SetInput("UAToggleHeadlight")` (`actioninput.c:776-782`). Both names exist in `P:\bin\constants.xml:90-91`. A custom `inputs.xml` that only assigns `UAToggleHeadlight` will turn on the headtorch, not the motorbike headlight. Horn aliases `CarHornShortActionInput : VehicleHornShortActionInput {}` (`actioninput.c:757-758`) are empty compatibility shells with 1.29; register `ActionVehicleHornShort`/`Long` (`actionconstructor.c:340-341`).
