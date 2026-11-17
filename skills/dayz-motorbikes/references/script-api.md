# Motorbike script API (`motorbike.c` and `motorbikescript.c`)

The native interface (`proto native`) of `motorbike.c`, the simulation callbacks, the `motorbikescript.c` lifecycle, the net sync variables, and what a motorbike lacks compared with `carscript.c`. Short citations: `config.cpp:N` is `P:\DZ\vehicles\singletrack\config.cpp`, and a bare script file name is the file of that name under `P:\scripts\` (`motorbike_01.c` and `motorbike_02.c` are the ones in `4_world\entities\vehicles\inheritedmotorbikes\`). Line numbers match the 1.30 data on `P:\` at the time of writing; when a line has moved, Grep for the symbol.

---

## 1. Proto native Signatures of motorbike.c

All native functions declared in `P:\scripts\3_game\vehicles\motorbike.c`:

```c
// P:\scripts\3_game\vehicles\motorbike.c:100
proto native float GetSteering();
// P:\scripts\3_game\vehicles\motorbike.c:103
proto native void SetSteering(float value);

// P:\scripts\3_game\vehicles\motorbike.c:106
proto native bool CanPickUp();
// P:\scripts\3_game\vehicles\motorbike.c:109
proto native void PickUp();

// P:\scripts\3_game\vehicles\motorbike.c:112
proto native bool IsFallen();
// P:\scripts\3_game\vehicles\motorbike.c:115
proto native bool FallOver();

// P:\scripts\3_game\vehicles\motorbike.c:118
proto native float GetThrottle();
// P:\scripts\3_game\vehicles\motorbike.c:121
proto native void SetThrottle(float value);

// P:\scripts\3_game\vehicles\motorbike.c:124
proto native int GetClutch();
// P:\scripts\3_game\vehicles\motorbike.c:127
proto native void SetClutch(float value);

// P:\scripts\3_game\vehicles\motorbike.c:130
proto native float GetBrake();
// P:\scripts\3_game\vehicles\motorbike.c:133
proto native void SetBrake(float value);

// P:\scripts\3_game\vehicles\motorbike.c:136
proto native float GetHandbrake();
// P:\scripts\3_game\vehicles\motorbike.c:139
proto native void SetHandbrake(float value);

// P:\scripts\3_game\vehicles\motorbike.c:142
proto native float GetKickstand();
// P:\scripts\3_game\vehicles\motorbike.c:145
proto native void SetKickstand(float value);

// P:\scripts\3_game\vehicles\motorbike.c:148
proto native float EngineGetRPMMin();
// P:\scripts\3_game\vehicles\motorbike.c:151
proto native float EngineGetRPMIdle();
// P:\scripts\3_game\vehicles\motorbike.c:154
proto native float EngineGetRPMMax();
// P:\scripts\3_game\vehicles\motorbike.c:157
proto native float EngineGetRPMRedline();
// P:\scripts\3_game\vehicles\motorbike.c:160
proto native float EngineGetRPM();
// P:\scripts\3_game\vehicles\motorbike.c:163
proto native bool EngineIsOn();
// P:\scripts\3_game\vehicles\motorbike.c:166
proto native void EngineStart();
// P:\scripts\3_game\vehicles\motorbike.c:169
proto native void EngineStop();

// P:\scripts\3_game\vehicles\motorbike.c:172
proto native vector GetEnginePos();
// P:\scripts\3_game\vehicles\motorbike.c:175
proto native void SetEnginePos(vector pos);

// P:\scripts\3_game\vehicles\motorbike.c:178
proto native int GetCurrentGear();
// P:\scripts\3_game\vehicles\motorbike.c:181
proto native int GetGear();
// P:\scripts\3_game\vehicles\motorbike.c:184
proto native int GetNeutralGear();
// P:\scripts\3_game\vehicles\motorbike.c:187
proto native int GetGearCount();
// P:\scripts\3_game\vehicles\motorbike.c:190
proto native void ShiftUp();
// P:\scripts\3_game\vehicles\motorbike.c:193
proto native void ShiftTo(int gear);
// P:\scripts\3_game\vehicles\motorbike.c:196
proto native void ShiftDown();

// P:\scripts\3_game\vehicles\motorbike.c:199
proto native CarGearboxType GearboxGetType();
// P:\scripts\3_game\vehicles\motorbike.c:202
proto native CarAutomaticGearboxMode GearboxGetMode();

// P:\scripts\3_game\vehicles\motorbike.c:205
proto native bool WheelIsAnyLocked();
// P:\scripts\3_game\vehicles\motorbike.c:212
proto native float WheelGetAngularVelocity(int wheelIdx);
// P:\scripts\3_game\vehicles\motorbike.c:219
proto native bool WheelHasContact(int wheelIdx);
// P:\scripts\3_game\vehicles\motorbike.c:226
proto native vector WheelGetContactPosition(int wheelIdx);
// P:\scripts\3_game\vehicles\motorbike.c:233
proto native vector WheelGetPositionLS(int wheelIdx);
// P:\scripts\3_game\vehicles\motorbike.c:240
proto native vector WheelGetContactNormal(int wheelIdx);
// P:\scripts\3_game\vehicles\motorbike.c:247
proto native vector WheelGetDirection(int wheelIdx);
// P:\scripts\3_game\vehicles\motorbike.c:254
proto native SurfaceInfo WheelGetSurface(int wheelIdx);
// P:\scripts\3_game\vehicles\motorbike.c:261
proto native CarWheelWaterState WheelGetWaterState(int wheelIdx);
// P:\scripts\3_game\vehicles\motorbike.c:268
proto native EntityAI WheelGetEntity(int wheelIdx);
// P:\scripts\3_game\vehicles\motorbike.c:275
proto native bool WheelIsLocked(int wheelIdx);
// P:\scripts\3_game\vehicles\motorbike.c:278
proto native int WheelCount();
// P:\scripts\3_game\vehicles\motorbike.c:281
proto native int WheelCountPresent();

// P:\scripts\3_game\vehicles\motorbike.c:288
proto native float GetFluidCapacity(MotorbikeFluid fluid);
// P:\scripts\3_game\vehicles\motorbike.c:296
proto native float GetFluidFraction(MotorbikeFluid fluid);
// P:\scripts\3_game\vehicles\motorbike.c:299
proto native void Leak(MotorbikeFluid fluid, float amount);
// P:\scripts\3_game\vehicles\motorbike.c:302
proto native void LeakAll(MotorbikeFluid fluid);
// P:\scripts\3_game\vehicles\motorbike.c:305
proto native void Fill(MotorbikeFluid fluid, float amount);
```

---

## 2. Engine-Script Events and Callbacks in motorbike.c

- `protected override event typename GetOwnerStateType()` (`motorbike.c:33-36`): Returns `MotorbikeOwnerState`.
- `protected override event typename GetMoveType()` (`motorbike.c:39-42`): Returns `MotorbikeMove`.
- `float GetSpeedometer()` (`motorbike.c:45-52`): Returns longitudinal speed by multiplying projection by 3.6 (km/h).
- `float GetSpeedometerAbsolute()` (`motorbike.c:55-58`): `Math.AbsFloat(GetSpeedometer())`.
- `override bool IsAreaAtDoorFree(...)` (`motorbike.c:60-68`): Unconditionally returns `true` (motorbikes have no doors).
- `bool OnBeforeEngineStart()` (`motorbike.c:312-316`): Callback evaluated before allowing engine start. `motorbikescript.c:1558-1564` checks that operational state is `EMotorbikeOperationalState.OK`.
- `void OnEngineStart()` (`motorbike.c:321`, empty): invoked upon starting. The override in `motorbikescript.c:1003-1024` updates headlights and plays `START_OK`.
- `void OnEngineStop()` (`motorbike.c:326`): Invoked upon engine stopping.
- `void OnGearChanged(int newGear, int oldGear)` (`motorbike.c:334`): Invoked upon changing gear.
- `void OnFluidChanged(MotorbikeFluid fluid, float newValue, float oldValue)` (`motorbike.c:344`): Invoked on the owner upon fluid changes.
- `float OnSound(MotorbikeSoundCtrl ctrl, float oldValue)` (`motorbike.c:354-358`): Modulates sound controllers (`ENGINE`, `RPM`, `SPEED`, `PLAYER`).
- `void OnStabilityStart()` (`motorbike.c:363`): Invoked when the motorbike regains balance.
- `void OnStabilityStop()` (`motorbike.c:368`): Invoked when the motorbike falls to the ground.

---

## 3. Lifecycle and Synchronization in motorbikescript.c

### Constructor (`motorbikescript.c:105-148`)
1. Activates event mask: `SetEventMask(EntityEvent.POSTSIMULATE | EntityEvent.POSTFRAME);` (`motorbikescript.c:111`).
2. Instantiates `m_LightsComponent = VehicleLightsComponent(this);` and registers selections:
   - `"FrontOn"`, `"FrontOff"`, `"BrakeOn"`, `"BrakeOff"`, `"TailOn"`, `"TailOff"`, `"DashboardOn"`, `"DashboardOff"`.
   - Registers base profiles: `VehicleLightProfileFront` and `VehicleLightProfileRear`.
3. Instantiates `m_HornComponent = VehicleHornComponent(this);` in `OFF` mode.
4. Initializes particles via `InitializeParticles()` (`motorbikescript.c:174-205`).
5. Deploys kickstand: `SetKickstand(1);` (`motorbikescript.c:141`).
6. Registers network synchronization:
   ```c
   RegisterNetSyncVariableBool("m_BrakesArePressed");
   RegisterNetSyncVariableBoolSignal("m_PlayCrashSoundLight");
   RegisterNetSyncVariableBoolSignal("m_PlayCrashSoundHeavy");
   RegisterNetSyncVariableInt("m_HornComponent.m_Mode", VehicleHornMode.OFF, VehicleHornMode.COUNT);
   ```

### Central Economy and Persistence
- `override void EEOnCECreate()` (`motorbikescript.c:440-447`): Assigns random initial fuel between 0.0 and 35% of capacity:
  `float maxVolume = GetFluidCapacity( MotorbikeFluid.FUEL );`, `float amount = Math.RandomFloat(0.0, maxVolume * 0.35 );` and `Fill( MotorbikeFluid.FUEL, amount );` (`motorbikescript.c:443-446`).
- **Persistence (`OnStoreSave`/`OnStoreLoad`)**: `motorbikescript.c` does not implement these methods; it has no `OnStoreSave` or `OnStoreLoad` of its own (0 occurrences in the file), so saving is left to `Transport` and `EntityAI`.

---

## 4. Relevant Global Constants (`constants.c`)

Located in `P:\scripts\3_game\constants.c`:
- `ENVIRO_HEATCOMFORT_MOTORBIKE_SPEED_MIN = 20.0;` (`constants.c:792`)
- `ENVIRO_HEATCOMFORT_MOTORBIKE_SPEED_MAX = 100.0;` (`constants.c:793`)
- `ENVIRO_HEATCOMFORT_MOTORBIKE_TARGET_MAX = 0.8;` (`constants.c:794`)
- `MOTORBIKES_CONTACT_DMG_THRESHOLD_SMALL = 25.0;` (`constants.c:898`)
- `MOTORBIKES_CONTACT_DMG_THRESHOLD_MID = 40.0;` (`constants.c:899`)
- `MOTORBIKES_CONTACT_DMG_MIN = 10.0;` (`constants.c:900`)
- `MOTORBIKES_CONTACT_DMG_KILLCREW = 80.0;` (`constants.c:901`)

---

## 5. What does not exist in motorbikes compared with CarScript

| Car Subsystem | Status in Motorbike (`MotorbikeScript`) | Alternative or Behavior |
|---|---|---|
| `class Axles` | **Nonexistent** | Flat `class Wheels { class Front; class Rear; }` |
| Doors (`CarDoor`) | **Nonexistent** | No doors; `IsAreaAtDoorFree` always returns `true` (`motorbike.c:60-68`) |
| Radiator / Coolant circuit | **Nonexistent / Non-vital** | `IsVitalRadiator()` returns `false` (`motorbikescript.c:321-324`). No temperature gauge in HUD (`motorbikehud.c:191-194`) |
| Oil / Brake fluid circuit | Declared in config, unused in script | `MotorbikeScript` declares capacities (`config.cpp:30-33`), but `motorbikescript.c` only uses `MotorbikeFluid.FUEL` |
| Battery mandatory for ignition | **Depends on override** | `Transport.NeedElectricitySourceDevice()` returns `true` (`transport.c:821-824`) and `MotorbikeScript` does not change it; `Motorbike_01`/`_02` override it to `false` (`motorbike_01.c:33-36`, `motorbike_02.c:34-37`). A bike inheriting from `MotorbikeScript` must override it |
| Door actions (`ActionOpenCarDoors`) | **Nonexistent** | In `Motorbike_01` flip-up seat `SeatDriver` exists |
| Parking handbrake | **Nonexistent** | Handbrake channel actuates front brake (`SetHandbrake`, `motorbike.c:135-139`; `Brakes.Front.input = 1`, `config.cpp:292`); handbrake indicator light is hidden in HUD (`motorbikehud.c:196`) |
| Symmetrical 4-wheel steering | **Nonexistent** | Simulation with dynamic lean (`maxLeanAngle[]`) and `tipoverAngle` |
| Dismount in gear without stalling | **Nonexistent** | If driver exits in gear, engine stops (`OnDriverExit` → `EngineStop()`, `motorbikescript.c:217-222`) |
