# MH6 helicopter: the force based reference

How the MH6 Little Bird helicopter mod (from the same mod family as the LM_Planes fixed-wing mod in `aviation-fixed-wing.md`) flies a `CarScript` child with real rigid body forces: Pawn owner state and move replication, the simulate loop, the PD flight controller in `ApplyHelicopterPhysics`, the ISA atmosphere helper, autohover and autoland, inputs, particles and lights. Open it when building or debugging a force based helicopter.

Third-party mod behaviour (MH6), not vanilla. Not yet checked on `P:\`. The flight model script inside `MH6_scripts.pbo` is fully legible Enforce Script; nothing in it is DRM-locked. The mod's files are not in this repo: the flight model script (named `MH6_flightmodel.c` here; in the unpacked PBO it is `MH6_scripts\b_off175614_o48037.c`), `MH6_scripts\b_*.c` (actions and particles) and the shared framework `Heli_Core\b_*.c`. Citations are `file:line` into the flight model script unless another file is named. A section or bullet marked `[UNVERIFIED]` could not be read in the mod's files, so do not invent it; everything else was read in those scripts. Learn the pattern from it and write the mod's own code; `skills/_shared/vehicles/helicopters.md` says which model to build from.

**Of the three helicopters with a single flight loop, this is the buildable force-based one.** Where SIB
and RFFS both fly kinematically (`SetVelocity`) and only SIB's *unreadable, DRM-locked* advanced variant
was force-based, MH6 applies real rigid-body forces every tick — `dBodyApplyForce(this, totalForce)` +
`dBodyApplyTorque(this, totalTorque)` (`:1165-1166`) — and its whole integrator is present in plaintext.
It proves the force-based model that SIB made look permanently gated is in fact viable and shippable.

## 1. Architecture — `MH6 : CarScript` + Pawn OwnerState/Move replication

Same **CarScript-as-aviation** hack as the other two helis and LM_Planes: `class MH6 extends
CarScript` (`:112`). But MH6's networking is the most advanced of the three helis — it uses the **custom
Pawn OwnerState/Move pipeline** (the same family LM_Planes uses for fixed-wing), not SIB's `SetSynchDirty`
polling or RFFS's `RegisterNetSyncVariable*` bank:

| Layer | Role | Cite |
|---|---|---|
| `MH6OwnerState extends CarScriptOwnerState` | replicated flight state: `m_bAutoHoverEnabled`, `m_fHoverTargetAltitude`, `m_fRotorSpeed`, `m_iAutoLandState`, landing target XYZ, and the 4 smoothed control channels (`m_fCollectiveSmooth`/`CyclicPitch`/`CyclicRoll`/`Pedal`). `Write`→`PawnStateWriter`, `Read`←`PawnStateReader` | `:17-62` |
| `MH6Move extends CarScriptMove` | per-tick pilot input: `m_fCyclicPitch`, `m_fCyclicRoll`, `m_fPedal`, `m_fThrottle`, plus `m_iToggleAutoHover`/`m_iAutoLand` command ints + autoland target XYZ. `Write`→`PawnMoveWriter`, `EstimateMaximumSize += 9*4` | `:64-110` |
| `MH6 : CarScript` | the flight model itself + rotor animation + autohover/autoland state machines + lights | `:112-1624` |

The Pawn wiring: `GetOwnerStateType()`→`MH6OwnerState`, `GetMoveType()`→`MH6Move` (`:286-294`);
`ObtainMove` (client packs inputs into the move, `:296-324`), `ConsumeMove` (server applies them +
dispatches autohover/autoland commands, `:326-351`), `ReplayMove` (client-prediction replay, `:353-368`),
`ObtainState`/`RewindState` (snapshot + rollback with client-interp targets, `:370-424`). This is
**client-side prediction + server reconciliation** — the same reason LM_Planes feels non-laggy, now on a
heli. It still keeps the vestigial CarScript ground drivetrain (gearbox forced to `CarGear.FIRST` every
tick in `OnInput`/`OnGearChanged`, `:1209-1211`/`:1244-1254`) as the taxi fallback.

Two `RegisterNetSyncVariable*` remain for the two discrete states that must survive to all observers:
`RegisterNetSyncVariableBool("m_AutoHoverEnabled")` + `RegisterNetSyncVariableInt("m_AutoLandState",0,4)`
(`:243-244`) — the continuous physics rides the Pawn state, the toggles ride sync vars.

## 2. The simulate loop — `EOnSimulate` / `EOnPostSimulate`

Physics run **server-or-owner** (`IsServerOrOwner()`), i.e. server-authoritative with owner
client-prediction. `EOnSimulate` (`:1276-1343`):

1. **Non-owner clients** just `Synchronize()`, interpolate the smoothed channels toward their synced
   targets (`UpdateClientInterpolation`, lerp rate `CLIENT_INTERP_RATE=8`, `:449-461`), animate rotors,
   and return (`:1280-1286`).
2. **Server/owner**: `CachePhysicsState()` (`:507-536`) snapshots velocity, angular velocity, position,
   speed, height-AGL, and the three body basis vectors `m_CachedFwd/Right/Up` (from `ModelToWorld` of the
   local axes) — everything the force model reads, sampled once per tick.
3. **Engine off** → spool rotor down (`SmoothApproach` toward 0 at `1/(ENGINE_SPOOL_DOWN*ROTOR_INERTIA)`),
   force `PHASE_GROUNDED`, `ClearNativeDamping()`, return (no forces) (`:1293-1301`).
4. **Engine on** → `SetupNativeDamping()`, spool rotor up toward `m_RotorSpeedTarget=1.0`, run
   `UpdateFlightPhase`, then (if enabled) `UpdateAutoHover` / `UpdateAutoLand`, smooth the 4 control
   channels toward their net inputs (`SmoothApproach` at `INPUT_SMOOTHING=4`), and — **only if autoland is
   OFF** — call `ApplyHelicopterPhysics(dt)` (`:1303-1325`). Autoland drives the heli kinematically
   instead (see §5).
5. **Adaptive sync** (`:1327-1342`): accumulate dt, and every `GetCurrentSyncInterval()` (0.033 s when
   `m_RotorSpeed>0.3`, else 0.1 s idle) call `SetSynchDirty()` if state changed or the rotor is spinning.

`EOnPostSimulate` (`:1345-1500`) runs the **owner-client input read**: it polls the `UAKTHeli*` inputs
(§6), integrates the collective throttle, handles the autohover/autoland key presses + auto-cancel on
manual override, and updates the landing marker object. It also updates a `UniversalTemperatureSource`
(engine heat) server-side (`:1495-1499`).

Native rigid-body damping is set once via `dBodySetDamping(this, BASE_LINEAR_DAMPING=0.05,
BASE_ANGULAR_DAMPING=0.15)` while the engine runs and cleared on stop (`:463-484`). The script's own drag
and PD torques ride on top of that baseline.

## 3. The PD flight controller — `ApplyHelicopterPhysics(dt)` (`:980-1167`)

This is the core and the reason MH6 is the force-based reference. It accumulates a single
`totalForce` + `totalTorque` and applies both at the end. All constants below are `protected const`
literals in the class body (`:141-176`) — **there is no JSON config** (contrast SIB/RFFS; the config.bin
that might override is not readable, see §7).

### 3a. Rotor-RPM authority gates (realism: no control without RPM)

Three `Ramp01(m_RotorSpeed, a, b)` smoothstep gates scale every control channel by how spun-up the rotor
is (`:988-990`):
- `liftAuth = Ramp01(m_RotorSpeed, 0.05, 0.35)` — lift comes online first
- `tailAuth = Ramp01(m_RotorSpeed, 0.12, 0.40)` — anti-torque next
- `cyclicAuth = Ramp01(m_RotorSpeed, 0.18, 0.50)` — cyclic last (needs the most RPM)

`m_RotorSpeed` is a normalized 0..1 spool value, `SmoothApproach`-ed toward 1.0 while the engine runs at
rate `1/(ENGINE_SPOOL_UP=3 * ROTOR_INERTIA=2)` (`:1305-1307`). `Ramp01` is `SmoothStep01((x-a)/(b-a))`
(`:492-499`). **The cyclic does not respond until the rotor has real RPM** — a genuinely realistic
authority curve, not present in SIB or RFFS.

### 3b. Collective → lift force (with atmosphere, translational lift, ground effect)

When `liftAuth>0` (`:1001-1012`):
```
weightForce   = VEHICLE_MASS(1400) * 9.81
baseThrust    = weightForce * 1.65          // maxThrustRatio: 65% thrust margin over hover
rotorEfficiency = m_RotorSpeed * m_RotorSpeed
thrustMag     = baseThrust * m_CollectiveSmooth * rotorEfficiency
thrustMag    *= densityRatio * transLift * liftAuth * groundEffect
totalForce   += m_CachedUp * thrustMag       // lift along the body up-axis
```
- `densityRatio = StandardAtmosphere.GetDensityRatio(altitude)` (`:986`) — real ISA air-density falloff
  (see §4); lift drops with altitude, giving a soft service ceiling.
- `transLift = CalculateTranslationalLift(forwardSpeed)` — effective translational lift: 1.0 below 2 m/s,
  ramping to `TRANS_LIFT_MAX=1.12` at `TRANS_LIFT_SPEED=12` m/s (`:599-605`).
- `groundEffect = CalculateGroundEffect(heightAGL)` — up to `GROUND_EFFECT_BONUS=1.15` within
  `GROUND_EFFECT_HEIGHT=4` m, quadratic falloff (`:607-615`).

Lift is applied along the **body up-vector `m_CachedUp`**, so tilting the airframe (via cyclic torque)
redirects lift into horizontal translation — the physically-correct helicopter behaviour, achieved here
through real torque + force rather than RFFS's explicit sin/cos lift-vector rotation.

### 3c. Cyclic + tail torques (attitude authority)

- **Cyclic** (`cyclicAuth>0`, `:1038-1053`): `rotorAuthority = m_RotorSpeed² * cyclicAuth`; pitch torque
  `= m_CyclicPitchSmooth * CYCLIC_PITCH_RATE(65) * rotorAuthority * 80` about `m_CachedRight`; roll torque
  `= m_CyclicRollSmooth * CYCLIC_ROLL_RATE(70) * rotorAuthority * 70` about `m_CachedFwd`.
- **Tail rotor / yaw** (`tailAuth>0`, `:1055-1065`): models main-rotor reaction torque
  (`mainRotorTorque = m_CollectiveSmooth * m_RotorSpeed * 35`) + a fixed counter-torque (`-0.9×`) + pilot
  pedal yaw (`m_PedalSmooth * PEDAL_YAW_RATE(75) * tailAuthority * 120`), all about `m_CachedUp`. So more
  collective induces more anti-torque demand — a real coupling.

### 3d. Attitude stability (the "P" term) — only when hands-off

When **not** in autohover (`:1067-1101`): read the airframe tilt from memory-point geometry
(`GetTiltFromAxisPoints`, §4), and if the pilot isn't commanding that axis (`|cyclicSmooth|<0.05`) and the
tilt is in `(3°,70°)`, apply a restoring torque proportional to angle:
```
pitchCorrection = -pitchDeg * PITCH_STABILITY(0.85) * m_RotorSpeed * 12 * pitchScale  // about Right
rollCorrection  = -rollDeg  * ROLL_STABILITY(0.90)  * m_RotorSpeed * 12 * rollScale   // about Fwd
```
`pitchScale`/`rollScale` fade the correction in with airspeed (weaker near hover, halved below 1.2 m AGL)
so it doesn't fight low-speed manoeuvring. **This is the proportional term of a PD attitude controller.**

### 3e. Angular-rate damping (the "D" term) — always on

`:1103-1116`: project angular velocity onto each body axis and apply opposing torque:
```
totalTorque += Right * (-pitchRate * PITCH_DAMPING(5.0) * 800 * dampingScale)
totalTorque += Fwd   * (-rollRate  * ROLL_DAMPING(5.5)  * 700 * dampingScale)
totalTorque += Up    * (-yawRate   * YAW_DAMPING(4.5)   * 600 * dampingScale)
```
`dampingScale = 0.6` in autohover, else 1.0. **P (3d) + D (3e) = a full PD flight-stability controller**,
the defining feature of MH6's model.

### 3f. Quadratic drag + overspeed + climb limiter (force domain)

- **Per-axis quadratic drag** scaled by `densityRatio` (`:1118-1126`): `-Fwd * fwdSpeed*|fwdSpeed| *
  DRAG_FORWARD(0.4) * densityRatio` and likewise for side (`DRAG_SIDE=7.0`) and vertical
  (`DRAG_VERTICAL=3.5`). Side drag ≫ forward drag → the heli resists sideways slip strongly (realistic).
- **Overspeed limiting** (`:1128-1132`): above `MAX_FORWARD_SPEED=70` m/s, subtract a quadratic
  `overspeed² * 4` term along the velocity direction (hard soft-cap).
- **Near-ground climb limit** (`:1135-1147`): between 0.5–3 m AGL (outside liftoff), clamp vertical speed
  to `Lerp(4,6, heightAGL/2)` m/s by subtracting `excess * VEHICLE_MASS * 2` — controlled takeoff, no
  rocket-jump off the pad.

`dBodyApplyForce(this, totalForce)` + `dBodyApplyTorque(this, totalTorque)` (`:1165-1166`) commit it all.

## 4. Shared framework — `Heli_Core` + memory-point geometry

MH6 depends on `Heli_Core.pbo`. The only **legible, sizeable** class in it is
`class StandardAtmosphere` (`Heli_Core\b_off89829_o1538.c:2-43`) — a static ISA atmosphere helper the
flight model calls for `densityRatio`:
- `GetDensity(altitude_m)` uses the real barometric law:
  `SEA_LEVEL_DENSITY(1.225) * (temp/288.15)^(-(g/(L*R))-1)` with `L=-0.0065`, `R=287.05`, `g=9.80665`,
  clamped to `MAX_ALTITUDE=2000` m (`:12-21`).
- `GetDensityRatio` = density/sea-level (`:22-25`); plus `GetPerformanceFactor` (1.0 below 1200 m, lerp to
  0.6 at 2000 m), `IsApproachingCeiling` (>1800 m), `GetCeilingWarningLevel` (`:26-42`). **This is the same
  ISA-atmosphere idea LM_Planes uses for fixed-wing**, reused for the heli.
- [UNVERIFIED] the *rest* of `Heli_Core\b_*.c` — the remaining 25 blocks are **JAPM anti-tamper
  shells** (obfuscated commented `static float ...Hash()...` lines) or byte-fragment junk, not real logic.
  Whether Heli_Core defines any shared heli base beyond `StandardAtmosphere` is [UNVERIFIED].

**Attitude sensing from memory points** (`GetTiltFromAxisPoints`, `:566-587`): rather than read
`GetOrientation()` Euler angles (SIB's approach), MH6 computes pitch/roll from the world-space height delta
between `axis_front`/`axis_back` and `axis_left`/`axis_right` memory points via `Atan2`. Rotor positions
read `rotor_main` / `rotor_tail` memory points with sane fallbacks (`GetMemoryPointSafe`, `:549-564`).
[UNVERIFIED] the actual `.p3d` memory-point set (config.bin/model not readable) — but the *names*
(`axis_front/back/left/right`, `rotor_main/tail`) and animation selections (`rotor_1_1`, `rotor_2_1`,
`rotor_1_1_hide`, `rotor_1_1_rotate_hide`, `seat_driver/codriver/cargo1/cargo2`, `seat_con_1..4`) are
confirmed from script reads.

## 5. Autohover & autoland — assist modes on top of force flight

MH6 is a **hybrid**: real force-based free flight. Autohover is a hold loop on the control channels while
force flight keeps running; only autoland switches to a kinematic `SetVelocity` state machine that replaces
the force call.

- **AutoHover** (`UpdateAutoHover`, `:663-698`): a PD altitude+attitude hold that writes *into the control
  channels* (not `SetVelocity`) — throttle `= 0.68 hover + altErr*0.06 - vertVel*0.22` (clamped 0.30..0.95),
  cyclic corrections from `GetTiltFromAxisPoints` to null tilt, and pedal yaw-rate damping. Toggled by
  `Server_ToggleAutoHover` (`:1268-1274`); auto-cancels on manual cyclic/collective input (`:1462-1469`).
  It also adds an extra horizontal-velocity damping *force* in `ApplyHelicopterPhysics` when hovering
  (`dampStr=500`, `:1149-1163`) — this is how it "parks" in the air.
- **AutoLand** (`MH6AutoLandState` FSM: `OFF→WARMUP→APPROACH→DESCEND→TOUCHDOWN`, enum `:1-8`; driver
  `UpdateAutoLand`, `:799-898`): a scripted approach that uses **`SetVelocity` + `dBodySetAngularVelocity`**
  each phase — WARMUP brakes to a stop, APPROACH flies horizontally toward the target at `Clamp(dist*0.4,
  0.3, 5)` m/s, DESCEND steps the descent rate down by height band (−2→−0.5 m/s), TOUCHDOWN settles and
  disarms (180 s cooldown). Preconditions gate it: engine on, speed `<AUTOLAND_MAX_SPEED(10)`, altitude
  `>AUTOLAND_MIN_ALTITUDE(25)`, tilt `<AUTOLAND_MAX_TILT(30°)`, target within `AUTOLAND_MAX_RANGE(65 m)`
  (`Server_InitiateAutoLand`, `:732-768`). While autoland is active, `ApplyHelicopterPhysics` is skipped
  (`:1322-1323`) — the FSM owns the body. The landing target is picked by a camera raycast
  (`FindLandingTarget` → `DayZPhysics.RaycastRV`, `:717-730`) and shown with an `MH6_landing_zone` marker
  object (`:909-978`).

**`MH6FlightPhase` FSM** (`GROUNDED→LIFTOFF→FLIGHT`, enum `:10-15`; `UpdateFlightPhase`, `:617-661`) gates
a **liftoff-assist blend**: during LIFTOFF below `LIFTOFF_BLEND_HEIGHT=3` m it adds a velocity-authority
lift force toward a desired climb rate + strong horizontal damping (`:1014-1036`), then eases out
(`EaseOutQuad`) into pure force flight — so takeoff is stable, cruise is fully dynamic.

## 6. Inputs, actions, particles, lights

- **Flight inputs** are custom `UAKTHeli*` UA actions, read owner-side in `EOnPostSimulate` via
  `GetUApi().GetInputByName(...).LocalHold()` (`:1431-1450`): `UAKTHeliForward`/`Back` → cyclic pitch,
  `UAKTHeliRight`/`Left` → cyclic roll, `UAKTHeliLeanLeft`/`LeanRight` → pedal/yaw, `UAKTHeliTurbo`/
  `Handbrake` → collective up/down (integrated into `m_ThrottleTarget` at `THROTTLE_INCREMENT_RATE=0.80`).
  Toggles `UAKTHeliAutoHover` / `UAKTHeliAutoLand` via `input.LocalPress` (`:1374-1379`). [UNVERIFIED] the
  `modded_Inputs.xml` bindings (config.bin not readable; names confirmed from script).
- **Engine start/stop**: MH6 reuses the **vanilla CarScript engine actions** — `ActionStartEngine` /
  `ActionStopEngine` are `modded` only to relabel the prompt to "Start/Stop MH6 Helicopter" when the
  transport `IsKindOf("MH6")` (`MH6_scripts\b_off212633_o856.c:1-41`). No custom start action class — the
  flight loop simply gates on `EngineIsOn()`. `OnEngineStart`/`OnEngineStop` (`:1220-1242`) seed collective
  to throttle, reset the flight phase, and set/clear native damping.
- **Particles**: `modded class ParticleList` registers rocket VFX `ROCKET_TAIL2`/`ROCKET_IMPACT`/
  `ROCKET_TAIL` from the mod's own graphics folder (`b_off152027_o355.c:1-6`) — MH6 is an *armed*
  Little Bird (the fire pipeline itself is not readable).
- **Lights**: `MH6FrontLight : CarLightBase` + `MH6RearLight : CarRearLightBase` (`:1626-1667`), standard
  CarScript segregated/aggregated light pattern.
- **Sound**: `OnSound` scales the `CarSoundCtrl.RPM` channel by `m_RotorSpeed` (`:1256-1261`) so engine
  audio tracks rotor spool, not wheel RPM.

## 7. Not readable / [UNVERIFIED] — do not fabricate

- **`config.bin`** (the MH6 CfgVehicles entry) is **obfuscated and not readable** — so the exact
  `CfgVehicles MH6` class, `AnimationSources`, `DamageZones`, `Crew`, memory-point declarations, wheel
  slots, and any config values that would *override* the script constants are all [UNVERIFIED]. The script
  is authoritative for the flight *logic*; the config contract around it is inferred from script reads
  (crew seats 0=Driver/1=CoDriver/2+=passengers via `GetSeatAnimationType`, `:1607-1616`; door state
  `DOORS_MISSING`, `:1567-1570`).
- **`model.cfg` + the `.p3d`** — not readable. Memory points (`axis_*`, `rotor_main/tail`) and animation
  selections (`rotor_1_1`, `rotor_2_1`, `rotor_1_1_hide`, `rotor_1_1_rotate_hide`, `seat_*`) are confirmed
  as *names* from script, [UNVERIFIED] as actual model data.
- **`modded_Inputs.xml`** — the `UAKTHeli*` input names are confirmed from script; bindings not readable.
- **`Heli_Core` beyond `StandardAtmosphere`** — the remaining blocks are JAPM shells / byte-fragment junk;
  any additional shared logic is [UNVERIFIED].
- **The combat/fire pipeline** — only the `ParticleList` rocket registrations survived; the projectile /
  RPC / damage code is not readable.

## Takeaway for building your own force-based heli

MH6 is the buildable **force-based** reference (all flight logic in one legible script). The teachable
skeleton: `MH6 : CarScript` with `MH6OwnerState`/`MH6Move` Pawn replication; per-tick `CachePhysicsState`
→ RPM-authority gates → collective lift force (× ISA density × translational lift × ground effect) along
body-up → cyclic/tail torques → **PD attitude control** (P from memory-point tilt, D from angular rate) →
quadratic per-axis drag → `dBodyApplyForce`+`dBodyApplyTorque`. Layer autohover as a hold loop that writes
into the control channels while force flight keeps running, and autoland as a kinematic `SetVelocity`
state machine that *replaces* the force call while active. Constants are hard-coded literals
(`:141-176`) — you can lift them as a starting tune. What you must author yourself (not on disk): the
`.p3d`, `model.cfg`, and the `CfgVehicles` config contract (crew/damage/animsources/memory points).
