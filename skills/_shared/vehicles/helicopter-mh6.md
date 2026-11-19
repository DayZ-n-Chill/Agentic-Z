# MH6 helicopter

How the MH6 Little Bird mod flies a `CarScript` child on real rigid body forces: Pawn replication, the simulate loop, the PD flight controller, the ISA atmosphere helper, auto hover and auto land, inputs and lights. Open it when building or debugging a force-based helicopter.

Everything here describes the MH6 mod's scripts, which are not in this repo and not vanilla. The mod comes from the same family as the fixed-wing mod in `aviation-fixed-wing.md`. Its flight model script inside `MH6_scripts.pbo` is plain, readable Enforce Script; it is called `MH6_flightmodel.c` here (in the unpacked PBO its name is `MH6_scripts\b_off175614_o48037.c`). The actions and particles are in `MH6_scripts\b_*.c` and the shared framework in `Heli_Core\b_*.c`. Citations are `file:line` into that script unless another file is named. Learn the pattern and write your own code; which model to build from is in `helicopters.md`.

Of the helicopter mods with one flight loop, MH6 is the readable force-based one. SIB and RFFS fly kinematically with `SetVelocity`, and SIB's force-based variant cannot be read; MH6 applies forces every tick, `dBodyApplyForce(this, totalForce)` and `dBodyApplyTorque(this, totalTorque)` (`:1165`, `:1166`), vanilla engine calls (`P:\scripts\1_core\proto\enphysics.c:146` and `:153`), with the whole integrator in plain text.

## Class layout and replication

`class MH6 extends CarScript` (`:112`), replicated through the Pawn owner state and move classes, the same family the fixed-wing mod uses:

| Class | Role | Source |
|---|---|---|
| `MH6OwnerState extends CarScriptOwnerState` | Replicated flight state: `m_bAutoHoverEnabled`, `m_fHoverTargetAltitude`, `m_fRotorSpeed`, `m_iAutoLandState`, the landing target, and four smoothed control channels (collective, cyclic pitch, cyclic roll, pedal), written with `PawnStateWriter` and read with `PawnStateReader` | `:17` to `:62` |
| `MH6Move extends CarScriptMove` | Pilot input per tick: `m_fCyclicPitch`, `m_fCyclicRoll`, `m_fPedal`, `m_fThrottle`, the auto hover and auto land command ints and target; `EstimateMaximumSize` grows by `9*4` | `:64` to `:110` |
| `MH6 : CarScript` | Flight model, rotor animation, auto hover and auto land, lights | `:112` to `:1624` |

`GetOwnerStateType()` and `GetMoveType()` return those classes (`:286` to `:294`). `ObtainMove` packs the client's inputs (`:296` to `:324`), `ConsumeMove` applies them on the server and dispatches the assist commands (`:326` to `:351`), `ReplayMove` replays for prediction (`:353` to `:368`), and `ObtainState` and `RewindState` snapshot and roll back (`:370` to `:424`). That is client prediction with server correction. The car drivetrain stays as a taxi fallback, with the gear forced to `CarGear.FIRST` every tick (`:1209` to `:1211`, `:1244` to `:1254`).

The two discrete states every observer must see use sync variables, `RegisterNetSyncVariableBool("m_AutoHoverEnabled")` and `RegisterNetSyncVariableInt("m_AutoLandState", 0, 4)` (`:243`, `:244`); continuous physics rides the Pawn state.

## The simulate loop

Physics run on the server or the owning client (`IsServerOrOwner()`). `EOnSimulate` (`:1276` to `:1343`):

1. Other clients call `Synchronize()`, ease the smoothed channels toward their synced targets (`UpdateClientInterpolation`, rate `CLIENT_INTERP_RATE = 8`, `:449` to `:461`), animate the rotors and return (`:1280` to `:1286`).
2. Server or owner: `CachePhysicsState()` takes velocity, angular velocity, position, speed, height above ground and the body's forward, right and up vectors once per tick (`:507` to `:536`).
3. Engine off: spool the rotor down with `SmoothApproach` (toward 0 at `1/(ENGINE_SPOOL_DOWN * ROTOR_INERTIA)`), set `PHASE_GROUNDED`, call `ClearNativeDamping()`, apply no force (`:1293` to `:1301`).
4. Engine on: call `SetupNativeDamping()`, spool toward `m_RotorSpeedTarget = 1.0`, run `UpdateFlightPhase`, then auto hover or auto land if on, smooth the four channels (`INPUT_SMOOTHING = 4`), and call `ApplyHelicopterPhysics(dt)` only when auto land is off (`:1303` to `:1325`).
5. Sync: every `GetCurrentSyncInterval()` (0.033 s when `m_RotorSpeed > 0.3`, else 0.1 s) call `SetSynchDirty()` if the state changed or the rotor turns (`:1327` to `:1342`).

`EOnPostSimulate` (`:1345` to `:1500`) reads the owner's inputs, integrates the collective, handles the assist keys with cancel on manual input, moves the landing marker, and on the server updates a `UniversalTemperatureSource` for engine heat (`:1495` to `:1499`).

Native damping is set with `dBodySetDamping(this, 0.05, 0.15)` (`BASE_LINEAR_DAMPING`, `BASE_ANGULAR_DAMPING`) while the engine runs and cleared on stop (`:463` to `:484`; `P:\scripts\1_core\proto\enphysics.c:70`). The script's own drag and torques add to it.

## The flight controller

`ApplyHelicopterPhysics(dt)` (`:980` to `:1167`) sums one force and one torque and applies both at the end. Every constant is a `protected const` literal in the class (`:141` to `:176`); there is no JSON config.

Rotor speed gates control. `m_RotorSpeed` is a 0 to 1 spool value, eased toward 1.0 at `1/(ENGINE_SPOOL_UP 3 * ROTOR_INERTIA 2)` (`:1305` to `:1307`). Three smooth steps of the form `Ramp01(m_RotorSpeed, a, b)` scale the channels (`:988` to `:990`; `Ramp01` is `SmoothStep01((x - a)/(b - a))`, `:492` to `:499`): `liftAuth = Ramp01(m_RotorSpeed, 0.05, 0.35)`, `tailAuth = Ramp01(m_RotorSpeed, 0.12, 0.40)` and `cyclicAuth = Ramp01(m_RotorSpeed, 0.18, 0.50)`. Each channel's block runs only while its gate is above zero (`liftAuth > 0`, `tailAuth > 0`, `cyclicAuth > 0`). The cyclic does nothing until the rotor has real speed.

Lift (`:1001` to `:1012`):

```c
weightForce = VEHICLE_MASS * 9.81;                 // VEHICLE_MASS = 1400
baseThrust  = weightForce * 1.65;                  // 65 percent margin over hover
thrustMag   = baseThrust * m_CollectiveSmooth * m_RotorSpeed * m_RotorSpeed;
thrustMag  *= densityRatio * transLift * liftAuth * groundEffect;
totalForce += m_CachedUp * thrustMag;              // along the body up axis
```

- `densityRatio` from `StandardAtmosphere.GetDensityRatio(altitude)` (`:986`), so lift falls with height.
- `transLift = CalculateTranslationalLift(forwardSpeed)` is 1.0 below 2 m/s and rises to `TRANS_LIFT_MAX = 1.12` at `TRANS_LIFT_SPEED = 12` m/s (`:599` to `:605`).
- `groundEffect = CalculateGroundEffect(heightAGL)` is up to `GROUND_EFFECT_BONUS = 1.15` within `GROUND_EFFECT_HEIGHT = 4` m, falling off quadratically (`:607` to `:615`).

Lift acts along the body up axis, so tilting the airframe with cyclic torque turns lift into travel, through real force and torque rather than a rotated lift vector.

Torques:

- Cyclic (`:1038` to `:1053`): with `rotorAuthority = m_RotorSpeed² * cyclicAuth`, pitch torque `m_CyclicPitchSmooth * 65 * rotorAuthority * 80` about the right axis and roll torque `m_CyclicRollSmooth * 70 * rotorAuthority * 70` about the forward axis.
- Tail (`:1055` to `:1065`): main rotor reaction `m_CollectiveSmooth * m_RotorSpeed * 35`, a fixed counter torque of -0.9 times that, and pedal yaw `m_PedalSmooth * 75 * tailAuthority * 120`, all about the up axis. More collective needs more pedal.
- Self levelling, the P term (`:1067` to `:1101`), outside auto hover only: tilt comes from memory points; when the pilot is not using that axis (`|cyclic| < 0.05`) and tilt is between 3 and 70 degrees, a restoring torque of `-angle * 0.85` (pitch) or `0.90` (roll) `* m_RotorSpeed * 12 * scale` is applied. The scale fades in with airspeed and halves below 1.2 m.
- Rate damping, the D term, always on (`:1103` to `:1116`): opposing torques of pitch rate times `5.0 * 800`, roll rate times `5.5 * 700`, yaw rate times `4.5 * 600`, all times `dampingScale` (`dampingScale = 0.6` in auto hover, else 1.0).

Drag and limits:

- Quadratic drag per axis scaled by density (`:1118` to `:1126`): `DRAG_FORWARD = 0.4`, `DRAG_SIDE = 7.0`, `DRAG_VERTICAL = 3.5`. Strong side drag resists sideslip.
- Above `MAX_FORWARD_SPEED = 70` m/s forward, subtract `overspeed² * 4` along the velocity (`:1128` to `:1132`).
- Between 0.5 and 3 m above ground (outside lift-off), climb rate is clamped to `Lerp(4, 6, heightAGL / 2)` m/s by subtracting `excess * VEHICLE_MASS * 2` (`:1135` to `:1147`), so the take-off is controlled.

## Atmosphere and attitude sensing

MH6 requires `Heli_Core.pbo`. Its one readable class is `StandardAtmosphere` (`Heli_Core\b_off89829_o1538.c:2` to `:43`). `GetDensity(altitude_m)` uses the barometric law, `SEA_LEVEL_DENSITY (1.225) * (temp / 288.15)^(-(g / (L * R)) - 1)` with `L = -0.0065`, `R = 287.05`, `g = 9.80665`, capped at `MAX_ALTITUDE = 2000` m (`:12` to `:21`). `GetDensityRatio` divides by sea level (`:22` to `:25`); `GetPerformanceFactor` is 1.0 below 1,200 m and falls to 0.6 at 2,000 m; `IsApproachingCeiling` is true above 1800 m, and `GetCeilingWarningLevel` grades how close the ceiling is (`:26` to `:42`). The other 25 blocks of `Heli_Core` are anti-tamper shells or junk; whether it holds more shared logic is unknown.

Tilt is read from memory points, not Euler angles: `GetTiltFromAxisPoints` (`:566` to `:587`) takes `Atan2` of the height difference between `axis_front` and `axis_back`, and between `axis_left` and `axis_right`. Rotor positions come from `rotor_main` and `rotor_tail`, with fallbacks (`GetMemoryPointSafe`, `:549` to `:564`). Script also names the selections `rotor_1_1`, `rotor_2_1`, `rotor_1_1_hide`, `rotor_1_1_rotate_hide`, `seat_driver`, `seat_codriver`, `seat_cargo1`, `seat_cargo2` and `seat_con_1` to `seat_con_4`; the model itself cannot be read.

## Auto hover and auto land

Free flight is force-based. Auto hover is a hold loop on top of it; only auto land switches to kinematic control.

- Auto hover (`UpdateAutoHover`, `:663` to `:698`) writes into the control channels: throttle `= 0.68 hover + altErr*0.06 - vertVel*0.22`, clamped to 0.30 to 0.95; cyclic corrections that null the tilt; pedal yaw damping. `Server_ToggleAutoHover` toggles it (`:1268` to `:1274`) and manual cyclic or collective cancels it (`:1462` to `:1469`). While hovering, `ApplyHelicopterPhysics` adds a horizontal damping force of strength `dampStr = 500` (`:1149` to `:1163`), which parks it in the air.
- Auto land runs the `MH6AutoLandState` states `OFF`, `WARMUP`, `APPROACH`, `DESCEND`, `TOUCHDOWN` (enum `:1` to `:8`, `UpdateAutoLand` `:799` to `:898`) with `SetVelocity` and `dBodySetAngularVelocity` (`P:\scripts\1_core\proto\enphysics.c:111` and `:165`): warm-up brakes to a stop, approach flies toward the target at `Clamp(distance * 0.4, 0.3, 5)` m/s, descent steps down from -2 to -0.5 m/s by height band, touchdown settles and disarms with a 180 s cooldown. It starts only with the engine on, speed under `AUTOLAND_MAX_SPEED (10)`, altitude over `AUTOLAND_MIN_ALTITUDE (25)` m, tilt under `AUTOLAND_MAX_TILT (30)` degrees and the target within `AUTOLAND_MAX_RANGE (65 m)` (`Server_InitiateAutoLand`, `:732` to `:768`), and while it runs the force call is skipped (`:1322`, `:1323`). The target comes from a camera raycast (`FindLandingTarget` calls `DayZPhysics.RaycastRV`, `:717` to `:730`) and is marked with an `MH6_landing_zone` object (`:909` to `:978`).

A flight phase machine, `MH6FlightPhase` with `GROUNDED`, `LIFTOFF`, `FLIGHT` (enum `:10` to `:15`, `UpdateFlightPhase` `:617` to `:661`), blends in a lift-off assist below `LIFTOFF_BLEND_HEIGHT = 3` m: a lift force toward a target climb rate plus strong horizontal damping (`:1014` to `:1036`), eased out with `EaseOutQuad` into pure force flight.

## Inputs, actions, effects and lights

- Inputs are custom `UAKTHeli*` actions read by the owner in `EOnPostSimulate` with `GetUApi().GetInputByName(...).LocalHold()` (`:1431` to `:1450`): `UAKTHeliForward` and `Back` for cyclic pitch, `Right` and `Left` for roll, `LeanLeft` and `LeanRight` for pedal, `Turbo` and `Handbrake` for collective up and down (integrated at 0.80 per second). `UAKTHeliAutoHover` and `UAKTHeliAutoLand` toggle with `LocalPress` (`:1374` to `:1379`). The `modded_Inputs.xml` bindings cannot be read.
- Engine start and stop reuse vanilla `ActionStartEngine` and `ActionStopEngine`, modded only to relabel the prompt when the transport `IsKindOf("MH6")` (`MH6_scripts\b_off212633_o856.c:1` to `:41`). The flight loop gates on `EngineIsOn()`. `OnEngineStart` and `OnEngineStop` (`:1220` to `:1242`) seed the collective, reset the flight phase and set or clear damping.
- A `modded class ParticleList` registers rocket effects `ROCKET_TAIL2`, `ROCKET_IMPACT` and `ROCKET_TAIL` (`b_off152027_o355.c:1` to `:6`); the fire pipeline itself cannot be read.
- Lights: `MH6FrontLight : CarLightBase` and `MH6RearLight : CarRearLightBase` (`:1626` to `:1667`), the vanilla car light classes (`P:\scripts\4_world\entities\scriptedlightbase\spotlightbase\carlightbase.c:2`).
- Sound: `OnSound` scales the `CarSoundCtrl.RPM` channel by `m_RotorSpeed` (`:1256` to `:1261`), so engine audio follows the rotor.

## What cannot be read

`config.bin` is obfuscated, so the `CfgVehicles MH6` class, `AnimationSources`, `DamageZones`, `Crew`, memory points, wheel slots and any values that override the script constants are unknown. From script: seat 0 is the driver, 1 the co-driver, 2 and up passengers (`GetSeatAnimationType`, `:1607` to `:1616`), and doors report `DOORS_MISSING` (`:1567` to `:1570`). `model.cfg`, the `.p3d` and the input bindings cannot be read either.

## Building your own from it

The skeleton: a `CarScript` child with Pawn owner state and move classes; per tick, cache the physics state, gate controls by rotor speed, apply lift along body up (times ISA density, translational lift and ground effect), add cyclic and tail torques, a PD attitude controller (P from memory-point tilt, D from angular rate) and quadratic drag per axis, then `dBodyApplyForce` and `dBodyApplyTorque`. Make auto hover a hold loop that writes into the controls while force flight runs, and auto land a kinematic state machine that replaces the force call. The literals at `:141` to `:176` are a usable first tune. The `.p3d`, `model.cfg` and the `CfgVehicles` crew, damage, animation sources and memory points are yours to write.
