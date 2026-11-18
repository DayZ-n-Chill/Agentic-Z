# Motorbike invariants

The ten rules that break a motorbike when ignored, the tuning lessons measured on a real import, and what vanilla left unfinished in 1.30. Read `motorbikes.md` first for the class tree.

How to read the marks: `[EXACT]` was read in the cited vanilla file on `P:\`. `[UNVERIFIED]` could not be confirmed from the text sources or in game; a symptom marked that way is what the code suggests, not something measured. `[INFERRED]` and `[DESIGN]` are a deduction and a recommendation. `config.cpp:N` alone means `P:\DZ\vehicles\singletrack\config.cpp`, and a bare script file name is the vanilla file of that name under `P:\scripts\`. Line numbers match the 1.30 data on `P:\` at the time of writing.

## The ten invariants

### 1. Flat `Wheels` in config, never an `Axles` block

- **Symptom** [UNVERIFIED]: the simulation fails to initialize when the entity spawns. The exact failure (an RPT error, an inert entity or a crash) has not been measured.
- **Cause**: `simulation = "motorbike"` reads `class Wheels { class Front; class Rear; }` directly (`P:\DZ\vehicles\singletrack\config.cpp:73-91` in the base class, `:340-377` in `Motorbike_01_ColorBase`). `class Axles` belongs to the car simulation.
- **Remedy**: remove any `Axles` block from `SimulationModule` and declare `Front` and `Rear` inside `Wheels: Wheels`:
  ```cpp
  class Wheels: Wheels
  {
      class Front: Front { inventorySlot = "MyBike_Wheel_1"; animDamper = "damperfront"; };
      class Rear: Rear   { inventorySlot = "MyBike_Wheel_2"; animDamper = "damperback"; };
  };
  ```

### 2. Brakes: `Front` is `input = 1`, `Rear` is `input = 0`

- **Symptom**: the front brake lever does nothing, or the rear pedal locks the front wheel.
- **Cause**: the front brake is bound to the handbrake channel and the rear brake to the pedal channel. The API says so: `SetBrake` is the rear brake and `SetHandbrake` the front brake (`P:\scripts\3_game\vehicles\motorbike.c:129-139`).
- **Citation**: `input=1` at `config.cpp:292` and `input=0` at `:301`.
- **Remedy**:
  ```cpp
  class Brakes
  {
      class Front { input = 1; pressureBySpeed[] = {0,0.85,10,0.7,40,0.6,60,0.5,80,0.5}; };
      class Rear  { input = 0; pressureBySpeed[] = {0,0.95,10,0.1,20,0.1,40,0.1,50,0.1}; };
  };
  ```
  The rear `pressureBySpeed[]` drops from `0.95` at standstill to `0.1` from point `10` on (`config.cpp:302`). Whether that is there to prevent rear wheel skids is an interpretation [UNVERIFIED].

### 3. A `"drivewheel"` bone in the model for the headlight

- **Symptom**: the headlight cone stays fixed to the chassis and does not turn with the handlebars.
- **Cause**: the script looks the bone up by name, `GetBoneIndex("drivewheel")`, and attaches the front light to it (`P:\scripts\4_world\entities\vehicles\motorbikescript.c:1107-1109`).
- **Remedy**: name the front fork and handlebar selection `drivewheel` in the model and list it in `skeletonBones[]` of the `model.cfg`:
  ```c
  int driveWheelIndex = GetBoneIndex("drivewheel");
  m_LightsComponent.AttachLightOnObject("Front", GetMemoryPointPos(m_HeadLightPoint), vector.Zero, VehicleLightMode.SEGREGATED, driveWheelIndex);
  ```

### 4. `SeatDriver` and the `CanGetIn` condition

- **Symptom**: the player gets no prompt to get on (`CanGetIn()` returns `false`).
- **Cause**: `Motorbike_01_ColorBase` requires `GetAnimationPhase("SeatDriver") == 0.0` (`P:\scripts\4_world\entities\vehicles\inheritedmotorbikes\motorbike_01.c:92-98`). A model without the `SeatDriver` animation never satisfies it.
- **Remedy**: for a bike without a flip-up seat, inherit `MotorbikeScript` directly or override `CanGetIn()` without the `SeatDriver` check. To keep the seat, declare the source with phase `0.0`:
  ```cpp
  class AnimationSources: AnimationSources
  {
      class SeatDriver { source = "user"; initPhase = 0.0; animPeriod = 1.0; };
  };
  ```

### 5. Contact damage coefficients and instant death

- **Symptom**: the rider dies when the bike grazes a small obstacle at low speed.
- **Cause**: each contact gives two values on the server (`CheckContactCache`, `P:\scripts\4_world\entities\vehicles\motorbikescript.c:1252-1357`, called inside `if (g_Game.IsServer())` at `:743-758`). Vehicle damage is `dmg = |impulse × m_VehicleContactDamageCoef|` (`:1263`). The crew damage base is `crewDmgBase = |impulse / mass × 500 × m_CrewContactDamageCoef|` (`:1264`), so it is computed as if the bike weighed 500 kg. The tier is chosen with `dmg`; only the last tier hurts the crew, and death there depends on `crewDmgBase` (`DamageCrew`, `:1360-1412`).
- **Tiers by `dmg`** (the constants are at `P:\scripts\3_game\constants.c:898-901`):
  - `dmg < 10` (`MOTORBIKES_CONTACT_DMG_MIN`): ignored (`motorbikescript.c:1301-1302`).
  - `10 ≤ dmg < 25` (`MOTORBIKES_CONTACT_DMG_THRESHOLD_SMALL`): damage to the zone without transfer (`NO_TRANSFER`) and the light crash sound (`:1310-1320`).
  - `25 ≤ dmg < 40` (`MOTORBIKES_CONTACT_DMG_THRESHOLD_MID`): `FallOver()` and the light sound; the crew takes no damage (`:1321-1331`).
  - `dmg ≥ 40`: `DamageCrew(crewDmgBase)`, `FallOver()` and the heavy sound (`:1332-1344`).
  - From `dmg ≥ 10`, `ProcessDirectDamage` applies `dmg` to the zone that was hit (`:1350`).
- **Inside `DamageCrew`**: when `crewDmgBase > 80` (`MOTORBIKES_CONTACT_DMG_KILLCREW`, strictly greater) it runs `crew.SetHealth(0.0)` (`:1369`, `:1383`). Otherwise it takes 50 to 150 shock and 2 to 100 health, interpolated between 25 and 80 (`:1387-1409`).
- **Remedy**: `m_VehicleContactDamageCoef` decides when the bike falls (`dmg ≥ 25`) and when the crew is hurt (`dmg ≥ 40`); `m_CrewContactDamageCoef` decides whether that kills (`crewDmgBase > 80`). Vanilla values: `0.03` and `0.018` (`motorbike_01.c:5-6`), `0.035` and `0.012` (`motorbike_02.c:5-6`).

### 6. Lean angles (`maxLeanAngle[]`) and tip-over (`tipoverAngle`)

- **Symptom** [UNVERIFIED]: the bike falls over by itself when accelerating, or stays upright and does not lean in turns.
- **Cause**: `class Steering` declares the lean curves and `tipoverAngle = 50.0` (`P:\DZ\vehicles\singletrack\config.cpp:266-278`). The native simulation consumes them, not script, so their exact effect cannot be read in text [UNVERIFIED].
- **Remedy**: start from the `Motorbike_01` table:
  ```cpp
  class Steering
  {
      tipoverAngle = 50.0;
      maxLeanAngle[] = {1,0,5,8,15,10,30,17,40,22,80,30};
      maxSteeringAngle[] = {1,40,5,40,15,20,30,5,40,3,80,1};
      directControl[] = {0.0,1.0,5.0,1.0,30.0,0.6,60.0,0.2,80.0,0.0};
  };
  ```

### 7. The kickstand in the lifecycle

- **Symptom** [UNVERIFIED]: the bike falls on its side when it spawns.
- **Cause**: the vanilla constructor deploys the kickstand with `SetKickstand(1)` (`P:\scripts\4_world\entities\vehicles\motorbikescript.c:141`). What the native physics does with the value is an assumption [UNVERIFIED].
- **Remedy**: keep `SetKickstand(1);` in the constructor. No retail script retracts it: the only `SetKickstand(0.0)` is in `OnInput` inside `#ifdef DIAG_DEVELOPER` and runs only with a debug mode set (`motorbikescript.c:841-843`, `:915`). If it retracts while riding, the native simulation does it [UNVERIFIED].

### 8. Geometry hidden at speed (`speedGeomActivation`, `speedGeoms[]`)

- **Symptom**: the bike catches on small bumps in the terrain or is thrown into the air at speed.
- **Cause**: the kickstand collision geometry hits ground unevenness unless it is switched off while moving. `speedGeomActivation` is `0.29` on `Motorbike_01` and `0.27` on `Motorbike_02`, both with `speedGeoms[] = {"geotohide"}` (`P:\DZ\vehicles\singletrack\config.cpp:258-262` and `:1448-1452`).
- **Remedy**: set `speedGeomActivation = 0.29;` and `speedGeoms[] = {"geotohide"};`, and put the kickstand collision in its own component named `geotohide` in the Geometry LOD.

### 9. The three components (lights, horn, particles)

- **Symptom** [UNVERIFIED]: a failure when the light code reaches a component that was never created, or a horn with no sound and no noise for infected.
- **Cause**: in 1.30 the lights no longer live in `m_Headlight` and the horn no longer in `m_CarHornState`; each has its own component, created in the `MotorbikeScript` constructor: `m_LightsComponent` (`P:\scripts\4_world\entities\vehicles\motorbikescript.c:113`), `m_HornComponent` (`:127`) and, through `InitializeParticles()` (`:139`), `m_VFXComponent`.
- **Remedy**: call the base constructor's work (a class on `MotorbikeScript` gets it for free) and register the bike's own profiles and sound sets on the components:
  ```c
  m_LightsComponent = VehicleLightsComponent(this);
  m_HornComponent = VehicleHornComponent(this);
  InitializeParticles(); // creates m_VFXComponent
  ```
- [EXACT] Vehicle lights are toggled with the input `UAToggleVehicleLights` through `ToggleVehicleLightsActionInput` (`P:\scripts\4_world\classes\useractionscomponent\actioninput.c:849-855`); `ActionSwitchLights.GetInputType()` returns that class (`actionswitchlights.c:16-19`). `UAToggleHeadlight` is the head torch (`ToggleLightsActionInput`, `actioninput.c:776-782`). Both names exist in `P:\bin\constants.xml:90-91`. An `inputs.xml` that binds only `UAToggleHeadlight` will not switch the bike's headlight. Detail: `motorbike-actions-hud-lights-sounds.md`, section 5.

### 10. Repair actions exist only on the blowtorch

- **Symptom**: the player gets no action to repair the engine or chassis with a wrench or epoxy putty.
- **Cause**: the motorbike repair actions are added only to the blowtorch: `ActionRepairMotorbikeEngineWithBlowtorch`, `ActionRepairMotorbikeChassisWithBlowtorch` and `ActionRepairMotorbikePartWithBlowTorch` (`P:\scripts\4_world\entities\itembase\blowtorch.c:109`, `:111`, `:113`), the only motorbike repair `AddAction` calls in the vanilla scripts. `ActionRepairMotorbikeEngine` is also missing from the action list, which registers the other motorbike repair actions (`P:\scripts\4_world\classes\useractionscomponent\actionconstructor.c:252-260`).
- **Remedy**: to repair with hand tools, add the actions to the items with a `modded class` and register the missing one:
  ```c
  modded class ActionConstructor
  {
      override void RegisterActions(TTypenameArray actions)
      {
          super.RegisterActions(actions);
          actions.Insert(ActionRepairMotorbikeEngine);
      }
  }
  ```

## Measured lessons from a real import

Measured in game on a 157 kg racing motorbike mod inheriting `Motorbike_02_ColorBase`, DayZDiag 1.30.164014, dedicated server and client. This is mod behaviour measured on one bike, not vanilla data.

1. **Overall first gear must be short.** [EXACT] With the automatic clutch, first gear × `driveRatio` between 20 and 26 pulls away (Motorbike_02: 25.7; the measured bike settled on 20). 6.77, the value of a real MotoGP bike, does not move the bike: 0.05 to 0.1 km/h at full throttle and the rpm stuck at two values. Decide it with an A/B in one session using the vanilla drivetrain as the control, and measure the ratio the engine applies (rpm·π/30 ÷ ω of the drive wheel) to confirm the config loaded. On 1.30 motorbikes wheel 0 is the front: tell the wheels apart by rolling radius (ω·r = v), not by `WheelGetPositionLS`.
2. **Suspension is sized to the load on each wheel.** [INFERRED] The model that fits the measurements is F = k (u + travelMaxDown), with the wheel hanging from the modelled axle and u linear in the damper phase (phase 0 = -travelMaxDown, phase 1 = +travelMaxUp). [EXACT] In the variant resting only on its springs, the sum of forces ÷ g gave 157.1 kg for a 157.0 kg bike; in another variant the springs carried only 132.7 kg and the rest sat on the engine collision box against the ground. To rest on the axle, travelMaxDown = F / k on each wheel (or raise k and scale the damping with √(k·m)). A bike that inherits its suspension from a lighter one inherits its sag; when the sum does not match the mass, look for what else is touching the ground.
3. **No Geometry box may touch the ground at full suspension compression.** [EXACT] Every touch is a contact: the damage that picks the tier is `Math.AbsInt(data[0].m_Impulse * m_VehicleContactDamageCoef)` (`motorbikescript.c:1263`) and from 25 up the branches call `FallOver()` (`:1310-1342`), which throws the rider off (invariant 5). Gate before testing: the lowest point of each component, minus the compression left from rest, is at least 5 mm; and scale `m_VehicleContactDamageCoef` by mass (× vanilla mass ÷ own mass) so the same hit counts the same.
   - [EXACT] When a `..._damper_land` box is lowered to seat the physical wheel, shrink it around the same centre, because the physical wheel does not move. Log the contacts on the server (`Transport.OnContact`: zone, point, impulse change) before tuning the coefficients.
4. **The rider proxy only positions the rider and turns it around the vertical.** [EXACT] The engine applies the crew proxy frame but keeps the player upright: a proxy tilted 20 degrees forward gave a yaw of about 17 degrees and no lean, and a rolled proxy gave a player standing 30 cm off the bike. Crouching or leaning the rider needs animation (`motorbike-rider-animation.md`).
5. **A hidden selection only changes material when `model.cfg` lists it in `sections[]`.** [EXACT] Config alone is not enough and the failure is silent: check it in the binarized model (the selection must be a section), not in config. The lights are painted by index in `hiddenSelections[]`: headlight 0, brake 1, tail light 2 and dashboard 3 in the base (`motorbikescript.c:114-122`), and both vanilla bikes then register their brake selection on index 2, the tail light's index (`motorbike_01.c:19-20`, `motorbike_02.c:20-21`). On a custom model those positions may fall on livery selections. From build 1.30.164200 the vanilla bikes register their own front and brake indexes (Motorbike_01 front 3 and brake 2, Motorbike_02 front 4 and brake 6); not yet checked on `P:\`.

## Unfinished in 1.30

Work in progress visible in the vanilla scripts and config on `P:\`. Where stable build 1.30.164200 differs, the item says so; those differences are not yet checked on `P:\`.

1. **Ejection by unconsciousness.** A fallen bike ejects its rider by giving the player `eModifiers.MDF_UNCONSCIOUSNESS` (`P:\scripts\4_world\entities\dayzplayerimplement.c:2452-2458`), a stand-in for a ragdoll command.
2. **Orphaned engine repair action.** `ActionRepairMotorbikeEngine` exists as a file (`actionrepairmotorbikeengine.c:1`) but is not in the list at `actionconstructor.c:252-260` and no tool adds it; only `ActionRepairMotorbikeEngineWithBlowtorch` works (invariant 10).
3. **Light materials the config does not declare.** The base registers light selections whose material name is read with `ConfigGetString` (`P:\scripts\4_world\entities\vehicles\components\vehiclelightscomponent.c:77`) from keys such as `frontReflectorMatOn` (`motorbikescript.c:114-122`). `P:\DZ\vehicles\singletrack\config.cpp` declares none of those keys (0 occurrences), while cars do, for example `frontReflectorMatOn` at `P:\DZ\vehicles\wheeled\config.cpp:1338`. On `P:\` the light entries of `hiddenSelections[]` are `lights_brake`, `lights_front`, `lights_rear` on `Motorbike_01_ColorBase` (`config.cpp:232-239`) and `light_1_1`, `light_1_2`, `light_brake_1_2` on `Motorbike_02_ColorBase` (`config.cpp:1416-1425`). On build 1.30.164200 (not yet checked on `P:\`) both bikes declare the front and brake materials, still none for the tail light or the dashboard, and the `Motorbike_02_ColorBase` entries are renamed `lights_front`, `lights_rear` and `lights_brake`.
4. **Sound classes are not in the vehicle sound addon.** `P:\DZ\sounds\vehicles\config.cpp:1-10` holds only `CfgPatches`. The motorbike sound sets and shaders are in `P:\DZ\sounds\hpp\config.cpp` (the `Motorbike_0*` SoundSets at lines 383946 to 385036, the SoundShaders at 316513 to 318260).
5. **Guides written for 1.29.** Many vehicle guides assume `CreateFrontLight`, `CarPartsHealthCheck` or `data[0].impulse`. In 1.30 those were replaced or wrapped: `dayz-1-30-vehicles.md`.
6. **Vehicle lights input.** `ActionSwitchLights` uses `UAToggleVehicleLights`, not `UAToggleHeadlight` (invariant 9).
