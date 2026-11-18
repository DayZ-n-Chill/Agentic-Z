# Motorbike script API

What the native `Motorbike` class offers script, which callbacks the simulation raises, what the `MotorbikeScript` constructor sets up and syncs, and what a motorbike lacks compared with `CarScript`. In this file `motorbike.c` is `P:\scripts\3_game\vehicles\motorbike.c`, `motorbikescript.c` is `P:\scripts\4_world\entities\vehicles\motorbikescript.c`, and `config.cpp` alone is `P:\DZ\vehicles\singletrack\config.cpp`.

## Native methods

Every method below is `proto native` in `motorbike.c`; each pair of a getter and a setter sits three lines apart.

| Group | Methods | Lines |
|---|---|---|
| Controls | `float GetSteering()`, `SetSteering(float)`; `float GetThrottle()`, `SetThrottle(float)`; `int GetClutch()`, `SetClutch(float)` | `:100`, `:103`; `:118`, `:121`; `:124`, `:127` |
| Brakes | `float GetBrake()`, `SetBrake(float)` (rear); `float GetHandbrake()`, `SetHandbrake(float)` (front) | `:130`, `:133`; `:136`, `:139` |
| Falling and standing | `bool CanPickUp()`, `PickUp()`; `bool IsFallen()`, `bool FallOver()`; `float GetKickstand()`, `SetKickstand(float)` | `:106`, `:109`; `:112`, `:115`; `:142`, `:145` |
| Engine | `EngineGetRPMMin()`, `EngineGetRPMIdle()`, `EngineGetRPMMax()`, `EngineGetRPMRedline()`, `EngineGetRPM()`, `bool EngineIsOn()`, `EngineStart()`, `EngineStop()`; `vector GetEnginePos()`, `SetEnginePos(vector)` | `:148` to `:169`; `:172`, `:175` |
| Gears | `GetCurrentGear()`, `GetGear()`, `GetNeutralGear()`, `GetGearCount()`, `ShiftUp()`, `ShiftTo(int)`, `ShiftDown()`; `CarGearboxType GearboxGetType()`, `CarAutomaticGearboxMode GearboxGetMode()` | `:178` to `:196`; `:199`, `:202` |
| Wheels | `bool WheelIsAnyLocked()`; per wheel `WheelGetAngularVelocity`, `WheelHasContact`, `WheelGetContactPosition`, `WheelGetPositionLS`, `WheelGetContactNormal`, `WheelGetDirection`, `WheelGetSurface` (`SurfaceInfo`), `WheelGetWaterState` (`CarWheelWaterState`), `WheelGetEntity`, `WheelIsLocked`; `WheelCount()`, `WheelCountPresent()` | `:205`; `:212` to `:275`, seven lines apart; `:278`, `:281` |
| Fluids | `GetFluidCapacity`, `GetFluidFraction`, `Leak`, `LeakAll`, `Fill`, each taking a `MotorbikeFluid` | `:288`, `:296`, `:299`, `:302`, `:305` |

## Script methods and callbacks on `Motorbike`

| Member | What it does | Lines in `motorbike.c` |
|---|---|---|
| `GetOwnerStateType()`, `GetMoveType()` | Protected events returning `MotorbikeOwnerState` and `MotorbikeMove` | `:33` to `:36`, `:39` to `:42` |
| `float GetSpeedometer()` | Speed along the bike's forward axis, times 3.6, in km/h | `:45` to `:52` |
| `float GetSpeedometerAbsolute()` | `Math.AbsFloat(GetSpeedometer())` | `:55` to `:58` |
| `IsAreaAtDoorFree(...)` | Always `true`; a bike has no doors | `:60` to `:68` |
| `bool OnBeforeEngineStart()` | Asked before the engine starts; `MotorbikeScript` requires `EMotorbikeOperationalState.OK` (`motorbikescript.c:1573` to `:1579`) | `:312` to `:316` |
| `void OnEngineStart()` | Empty; `MotorbikeScript` updates the headlights and plays the start sound (`motorbikescript.c:1018` to `:1039`) | `:321` |
| `void OnEngineStop()`, `OnGearChanged(int newGear, int oldGear)` | Empty hooks | `:326`, `:334` |
| `void OnFluidChanged(MotorbikeFluid fluid, float newValue, float oldValue)` | Called on the owner when a fluid changes | `:344` |
| `float OnSound(MotorbikeSoundCtrl ctrl, float oldValue)` | Sets the sound controllers `ENGINE`, `RPM`, `SPEED`, `PLAYER` | `:354` to `:358` |
| `void OnStabilityStart()`, `OnStabilityStop()` | Empty hooks for when the bike regains balance and when it falls | `:363`, `:368` |

`CheckOperationalRequirements()` (`motorbikescript.c:1582` to `:1606`) builds the `EMotorbikeOperationalState` flags (`:15` to `:21`): `RUINED` when the bike or its `Engine` zone is ruined, `NO_FUEL` when the fuel fraction is 0, and `NO_IGNITER` when `IsVitalSparkPlug()` is true and the `SparkPlug` slot is empty or ruined. Any flag blocks the start. A custom bike that has no spark plug slot must override `IsVitalSparkPlug()` to return `false` (it returns `true` on `Transport`, `P:\scripts_gameehicles	ransport.c:407`), or it never starts. While the engine runs, the server or owner calls `CheckVitalItemCallback(IsVitalSparkPlug(), SparkPlug.SLOT_ID, this, "EngineStop")`, so taking the spark plug out stops the engine, and a damaged `FuelTank` zone leaks fuel every tick (`motorbikescript.c:817` to `:826`).

## What the `MotorbikeScript` constructor sets up

The constructor (`motorbikescript.c:105` to `:148`) does, in order:

1. `SetEventMask(EntityEvent.POSTSIMULATE|EntityEvent.POSTFRAME)` (`:111`).
2. Creates `m_LightsComponent` and registers the selections `FrontOn`, `FrontOff`, `BrakeOn`, `BrakeOff`, `TailOn`, `TailOff`, `DashboardOn` and `DashboardOff` (`:113` to `:122`), then the lights `Front` with `VehicleLightProfileFront` and `Rear` with `VehicleLightProfileRear` (`:124`, `:125`).
3. Creates `m_HornComponent` in mode `OFF` (`:127`).
4. Calls `InitializeParticles()` (`:139`; the effects are registered at `:174` to `:205`).
5. Puts the kickstand down with `SetKickstand(1)` (`:141`).
6. Registers the synced variables (`:143` to `:147`):

```c
RegisterNetSyncVariableBool("m_BrakesArePressed");
RegisterNetSyncVariableBoolSignal("m_PlayCrashSoundLight");
RegisterNetSyncVariableBoolSignal("m_PlayCrashSoundHeavy");
RegisterNetSyncVariableInt("m_HornComponent.m_Mode", VehicleHornMode.OFF, VehicleHornMode.COUNT);
```

When the economy creates a bike, `EEOnCECreate` fills a random amount of fuel up to 35 percent of capacity (`motorbikescript.c:440` to `:447`):

```c
float maxVolume = GetFluidCapacity( MotorbikeFluid.FUEL );
float amount = Math.RandomFloat(0.0, maxVolume * 0.35 );
Fill( MotorbikeFluid.FUEL, amount );
```

`motorbikescript.c` has no `OnStoreSave` or `OnStoreLoad` of its own, so saving is left to `Transport` and `EntityAI`.

## Constants

In `P:\scripts\3_game\constants.c`:

| Constant | Value | Line |
|---|---|---|
| `ENVIRO_HEATCOMFORT_MOTORBIKE_SPEED_MIN` | `20.0` | `:792` |
| `ENVIRO_HEATCOMFORT_MOTORBIKE_SPEED_MAX` | `100.0` | `:793` |
| `ENVIRO_HEATCOMFORT_MOTORBIKE_TARGET_MAX` | `0.8` | `:794` |
| `MOTORBIKES_CONTACT_DMG_THRESHOLD_SMALL` | `25.0` | `:898` |
| `MOTORBIKES_CONTACT_DMG_THRESHOLD_MID` | `40.0` | `:899` |
| `MOTORBIKES_CONTACT_DMG_MIN` | `10.0` | `:900` |
| `MOTORBIKES_CONTACT_DMG_KILLCREW` | `80.0` | `:901` |

What the contact constants do is in `motorbike-invariants.md`.

## What a motorbike lacks compared with `CarScript`

| Car part | On a motorbike | Source |
|---|---|---|
| `class Axles` | None; `class Wheels` holds `Front` and `Rear` directly | `config.cpp:73` to `:91` |
| Doors (`CarDoor`) and door actions | None; `IsAreaAtDoorFree` is always `true`. `Motorbike_01` has a flip-up seat, `SeatDriver`, instead | `motorbike.c:60` to `:68` |
| Radiator and coolant | Not vital: `IsVitalRadiator()` returns `false`, and the HUD hides the temperature gauge, `m_VehicleTemperatureIndicator` | `motorbikescript.c:321` to `:324`; `P:\scripts\5_mission\gui\vehicles\motorbikehud.c:165` to `:194` |
| Oil and brake fluid | Capacities declared in config, but the script uses only `MotorbikeFluid.FUEL` | `config.cpp:30` to `:33` |
| Battery for ignition | `Transport.NeedElectricitySourceDevice()` returns `true` and `MotorbikeScript` keeps it; both vanilla bikes return `false`. A bike on `MotorbikeScript` must override it | `P:\scripts\3_game\vehicles\transport.c:830` to `:833`; `P:\scripts\4_world\entities\vehicles\inheritedmotorbikes\motorbike_01.c:30` to `:33`, `motorbike_02.c:31` to `:34` |
| Parking brake | None; the handbrake channel is the front brake, and the HUD hides the handbrake light | `motorbike.c:136` to `:139`; `config.cpp:296`; `motorbikehud.c:196` |
| Four-wheel steering | Lean (`maxLeanAngle[]`) and `tipoverAngle` in the native simulation | `config.cpp:270` to `:282` |
| Leaving in gear | The engine stops when the driver gets off in gear (`OnDriverExit` calls `EngineStop()`) | `motorbikescript.c:217` to `:222` |
