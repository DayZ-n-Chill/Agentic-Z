# RFFS helicopter: the kinematic reference

How the RFFS helicopter framework (`RFFSHeli_Core` version 1.0) flies a `CarScript` child with `SetVelocity` and `SetOrientation`: class layout, the `FlightSimulation()` integrator, the typed JSON config, rotor animation, memory points, crew, damage zones, actions, aviation attachments, HUD and sync. Open it when building or debugging a kinematic helicopter.

Third-party mod behaviour, not vanilla, and not yet checked on `P:\`. The mod is not obfuscated: every claim below was read in its own de-rapified `config.cpp` files and scripts (`Core_config.cpp`, `S76_config.cpp`, `Core_scripts\{3_Game,4_World,5_Mission}\...`, `S76_scripts\4_world\RFFSHeli_S76.c`), which are not in this repo. Citations are `file:line` into those files; `Core.c` is short for `Core_scripts\4_World\RFFSHeli_Core.c`. Tags: `[VERIFIED-RFFS]` read in the mod's files, `[UNVERIFIED]` not read, so do not invent it. Learn the pattern from it and write the mod's own code; `skills/_shared/vehicles/helicopters.md` says which model to build from.

**This is the recommended kinematic reference.** Unlike SIB (`helicopter-sib.md`), nothing here is
DRM-gated or missing: the full flight integrator is legible. It is a *far* more physically-grounded flight
model than SIB's (real thrust-vector rotation by attitude, ground effect, translational lift, speed/climb
governors, aerodynamic drag, weathervaning), while still being **kinematic** (`SetVelocity`-based, no
`dBodyApplyForce`) — the same choice SIB makes.

## 1. Architecture — `RFFSHeli_S76 : RFFSHeli_base : CarScript`

[VERIFIED-RFFS] Two layers (vs SIB's three):

| Layer | Adds | Cite |
|---|---|---|
| `CarScript` (vanilla) | wheels, seats, fuel, damage, sound | — |
| `RFFSHeli_base : CarScript` | the **entire flight model** + all tunables + sync vars + CarScript ground fallback (4 `NivaWheel` wheels, axles, steering, gearbox), aviation attachment slots, rotor/gauge `AnimationSources` | `Core.c:2`, config `Core_config.cpp:517-873` |
| `RFFSHeli_S76 : RFFSHeli_base` | per-heli config values (fuel/airspeed/altitude/etc.), door/seat/crew wiring, per-model gauge needle logic, wreck class | `RFFSHeli_S76.c:1`, config `S76_config.cpp:116-734` |

Same **CarScript-as-aviation** hack as SIB and LM_Planes: `class RFFSHeli_base: CarScript`
(`Core_config.cpp:517`) declares a full ground `SimulationModule` (`drive="DRIVE_AWD"`, torque curve,
gearbox, 4 axles/wheels — `Core_config.cpp:525-664`) that exists only as the taxi fallback. The heli
sets `SetEventMask(EntityEvent.SIMULATE)` + `SetEventMask(EntityEvent.FRAME)` (`Core.c:180-181`) and
overrides **`EOnSimulate`** (`Core.c:1027`) to fly itself with `SetVelocity`/`SetOrientation`.
`vehicleClass = "Expansion_Helicopter"` (`Core_config.cpp:523`).

## 2. Flight model — `FlightSimulation()`, kinematic but physically grounded

[VERIFIED-RFFS] The whole flight model is `FlightSimulation()` (`Core.c:1767-2129`), called from
`EOnSimulate` **server-side only** when the engine is running and `m_heli_state == 2`
(`Core.c:1149-1156`). The client re-runs `EOnSimulate` off `EOnFrame` every >5 ms
(`Core.c:1008-1016`), but that re-entry never reaches pose: `FlightSimulation()` stays behind the
server gate, so the client pump only advances `ExecuteAnimations()` + `KeyboardInputClient()`
(`Core.c:1143-1145`). It is not a smoothing mechanism — proxy pose smoothness comes from native
CarScript replication.

### 2a. Controls → state (per tick)

Inputs are read server-side in `KeyboardInput()` (`Core.c:510-544`) from pilot `CrewMember(0)` and/or
copilot `CrewMember(1)`, each via `player.GetInputInterface().SyncedValue("UARFFS...")`. The client
also *reads* the same synced values in `KeyboardInputClient()` (`Core.c:475-507`) purely to keep them
network-synced (it discards the result). Custom UA inputs (declared in
`inputs="RFFSHeli_Core/modded_Inputs.xml"`, `Core_config.cpp:30`; the names are confirmed from
the script reads, and section 7 says what the XML holds):

| Input | State written | Meaning | Cite |
|---|---|---|---|
| `UARFFSCyclicForward` / `…Back` | `r_cyclic_ForwardBack ∓= v * c_tilt_rate` | cyclic pitch (fore/aft) | `Core.c:549-550` |
| `UARFFSCyclicLeft` / `…Right` | `r_cyclic_LeftRight ∓= v * c_lateral_tilt_rate` | cyclic roll | `Core.c:551-552` |
| `UARFFSPedalLeft` / `…Right` | `r_pedal_LeftRight ∓= v * c_rotation_rate` | anti-torque / yaw (tail rotor) | `Core.c:553-554` |
| `UARFFSCollectiveUp` / `…Down` | `m_collective_level = Clamp(±1, 0, 20)` | **collective, discrete 0-20 detent** | `Core.c:563-583` |
| `UARFFSToggleHUD` | toggles `m_show_hud_*` (3-tick debounce) | HUD on/off | `Core.c:661-668` |
| `UARFFSToggleCommand` | toggles `m_pilot_in_command` | hand control pilot↔copilot | `Core.c:683-690` |
| `UARFFSRecover` | `m_flight_recovery_*` | flight-recovery / auto-level mode | `Core.c:637-657` |

[VERIFIED-RFFS] **The collective is a discrete 0-20 lever (each = 5% → 0-100%)**, not analog
(`m_collective_level` comment `Core.c:105`). The up/down keys step it with a 5-frame repeat gate
(`Core.c:565-583`), and each tick the applied thrust is
`r_collective_power = ((m_collective_level)/20) * c_thrust_rate` (`Core.c:543`). This is RFFS's
signature control and the cleanest difference from SIB (which had no collective detent). Two arcade
fallbacks exist: `c_simple_collective` (server master-config global) and `c_heli_simple_collective`
(per-heli), which replace the detent with a momentary `r_collective_power = ±(0.85 * c_thrust_rate)`
while a key is held (`Core.c:585-592`).

### 2b. Integration — `FlightSimulation()` (`Core.c:1767-2129`)

The realistic (non-recovery) branch runs `Core.c:1895-2126`:

1. **Ceiling clamp**: if `GetPosition()[1] > c_max_altitude_m`, hard-clamp Y via `SetPosition`
   (`Core.c:1774-1780`). Default `c_max_altitude_m = 1219.2` (`Core.c:38`), overridden per-heli
   (S76 = 1250 m, `RFFSHeli_S76.c:45`).
2. **Damage-driven yaw/power loss**: a damaged/ruined `TailRotor` injects escalating uncommanded
   `r_pedal_LeftRight` spin (`Core.c:1783-1801`); a damaged `Engine` or `MainRotor` cuts
   `r_collective_power *= 0.85` (`Core.c:1804-1817`).
3. **Angular-moment model**: cyclic/pedal inputs feed `m_angular_moment` (a carried-forward angular
   momentum vector), which is drag-decayed each tick by `c_tilt_drag_rate * m_cyclic_modifier`, clamped
   to `±c_angular_moment_limit`, and snapped to 0 near zero (`Core.c:1898-1931`). Attitude is then
   rotated by building `YawPitchRollMatrix` from current orientation and from `m_angular_moment` and
   `Math3D.MatrixMultiply3`-ing them (`Core.c:1954-1961`) — a proper 3D orientation compose, not
   SIB's per-axis literal nudges. Cyclic self-centers via `c_cyclic_retard` when input is released
   (`Core.c:1947-1952`).
4. **Collective → world lift vector** (`Core.c:1993-1996`): the scalar `r_collective_power` is rotated
   into world space by the heli's own pitch/roll/yaw:
   ```
   vector_x = r_collective_power * (-sin(roll)*cos(yaw) - cos(roll)*sin(pitch)*sin(yaw))
   vector_y = r_collective_power * ( sin(roll)*sin(yaw) - cos(roll)*sin(pitch)*cos(yaw))
   vector_z = r_collective_power * ( cos(roll)*cos(pitch))
   ```
   So tilting the disc (via cyclic) redirects lift into horizontal translation — the physically
   correct helicopter behaviour, and a real step up from SIB's "pitch attitude → scalar forward speed".
5. **Ground effect**: near the ground on descent, `vector_z` is boosted by a
   `c_rotor_diameter_m`-scaled term (`Core.c:1998-2000`).
6. **Effective translational lift (ETL)**: extra `vector_z` added as a function of horizontal speed
   `~(translational_speed*0.00007)^2 * c_thrust_rate` (`Core.c:2002-2004`).
7. **Speed governor**: as horizontal speed approaches `c_max_airspeed_kph`, a `translational_speed^4 /
   ((max+40)*0.277778)^4` term is subtracted from the horizontal thrust components — but only when the
   thrust would *increase* speed, not brake (`Core.c:2006-2027`).
8. **Climb governor**: as `heli_velocity[1]` approaches `c_max_climb_rate`, `vector_z` is scaled down
   by a 5th-power term (`Core.c:2029-2030`).
9. **Merge + drag**: thrust vectors add onto current velocity (`Core.c:2032-2035`); aerodynamic drag
   `c_aero_drag_rate` is split proportionally across X/Z and subtracted (`Core.c:2037-2048`).
10. **Weathervaning**: the nose is yawed toward the velocity vector by
    `(angle_diff/360) * log2(speed*0.1) * c_bank_turn_coeff` (`Core.c:2069-2087`) — banked turns
    naturally rotate the heading. Wind terms exist but are **commented out** (`Core.c:2050-2067`).
11. **Trainer mode**: optional pitch/roll clamp to ±35° and descent clamp to −7.5 m/s
    (`Core.c:2089-2106`).
12. **Extensibility hook**: `AdditionalThrustVectors(velocity, orient, out, out)` (`Core.c:2132-2136`,
    empty base) lets a concrete heli add thrust (e.g. tilt-rotor) by override.
13. **Apply**: `SetOrientation(heli_orient)` then `SetVelocityAdjusted(heli_velocity)`
    (`Core.c:2116-2119`); the four `r_*` input accumulators reset to 0 (`Core.c:2122-2125`);
    `ConsumeFuel()` at the end (`Core.c:2128`).

[VERIFIED-RFFS] **`SetVelocityAdjusted`/`GetVelocityAdjusted`** (`Core.c:2465-2487`) wrap
`SetVelocity`/`GetVelocity(this)` with a per-heli horizontal scale
(`c_speed_adjustement_factor` / `c_speed_factor`) — a DayZ-1.21/1.28 speed-compensation fudge
(`Core.c:82-84`, S76 sets `SpeedFactor=195`, `RFFSHeli_S76.c:49`). **`dBodyApplyImpulse` is present
only as a commented-out line** (`Core.c:272`) — like SIB, the buildable model is kinematic, never
force-based.

### 2c. Recovery / auto-stabilization mode

[VERIFIED-RFFS] If `UARFFSRecover` is held and `c_allow_recovery`, the recovery branch
(`Core.c:1819-1894`) zeroes all control inputs, sets collective to 50% (`m_collective_level = 10`),
counters gravity (`heli_velocity[1] += 0.245`), bleeds vertical/horizontal speed, and eases the heli
back to a level attitude derived from its current velocity vector. This is RFFS's genuine
auto-stabilization — richer than SIB's simple attitude-recenter, but still not a PID. There is **no
autohover/auto-navigate** system (unlike SIB's license-gated `AutopilotState` bot-map).

## 3. Config framework — `MasterConfig` + per-heli `HeliConfig` (typed JSON, data-driven)

[VERIFIED-RFFS] Two-tier JSON config under `$profile:\RFFSHeli\`, loaded via `JsonFileLoader<T>` with
auto-create-from-defaults + version-bump-migrate:

- **`RFFSHeli_MasterConfig`** → `$profile:\RFFSHeli\MasterConfig.json` (`RFFSHeli_MasterConfig.c:193-268`,
  `ConfigVersion=12`): server-wide policy — HUD units/allow-1PP/3PP/helmet, control flags
  (`AllowTakeCommand`, `SimpleCollective`, `AllowRecoveryMode`, `Grounded`), sound volume, damage
  toggles + collision coef, storage flags, and a full crash-site model (create-on-ruin, scatter/damage
  inventory, spawn zombies with a default class list, distances/counts, loot damage). Read once in
  `EEInit()` server-side (`Core.c:287-352`).
- **`RFFSHeli_HeliConfig`** → `$profile:\RFFSHeli\<classname>_Config.json`
  (`RFFSHeli_HeliConfig.c:136-188`, `ConfigVersion=7`): per-model flight tuning — fuel capacity/rate,
  trainer mode, has-hydraulics, simple-collective, max airspeed/altitude/climb-rate, aero drag, bank-turn
  coeff, speed factor, and the four control rates (anti-torque / cyclic / collective / cyclic-dampening).
  The concrete heli seeds the defaults in its own `EEInit()` and calls `ApplyHeliConfig()`
  (S76: `RFFSHeli_S76.c:38-62`).

[VERIFIED-RFFS] **This is a genuinely typed, named config framework** — a class
`RFFSHeli_HeliConfigData` with named `protected` fields + `get*` accessors (`RFFSHeli_HeliConfig.c:3-133`),
consumed field-by-name in `ApplyHeliConfig()` (`Core.c:232-265`, e.g.
`c_thrust_rate = getControlsCollectiveThrustRate()*0.01*0.47`). Contrast SIB's **positional/index-by-index**
`map<string,float>` store — RFFS's is safer and self-documenting. Notable reusable pattern:
config values are stored as **percentages** (100.0 = baseline) that scale a hard-coded engineering
constant, so servers tune "±X %" without knowing the raw physics coefficient.

[VERIFIED-RFFS] **Config-boolean sync trick**: server packs ~12 config booleans into a single
`RegisterNetSyncVariableInt("c_encoded_config_bool")` bitfield (`Core.c:334-345`) and the client
un-bit-shifts it in `EOnSimulate` (`Core.c:1030-1081`). Reusable when you have many small client-visible
config flags and don't want a sync var per flag. (SIB uses the same idea.)

## 4. AnimationSources, rotors, memory points, Crew, DamageZones (config)

[VERIFIED-RFFS] **AnimationSources** (`Core_config.cpp:665-838`, S76 extends at `S76_config.cpp:318-545`),
all `source="user"` driven by `SetAnimationPhase`:
- **Rotors** — paired main+tail, each with 4 sources: `rotorN_speed` (spin phase), `rotorN_blur_hide`
  (static↔blur swap), `rotorN_blades_hide`, `rotorN_bent_hide` (damage states). Rotors are **baked
  geometry with a blur variant**, health-gated — same choice as SIB, opposite of the attachable-blade
  community heli.
- **Engine/state** — `engine_rpm`, `engine_running`, `engine_running_fast`, `rotor_spinning`.
- **Gauges** — `airspeed_kts`, `altitude_ft`, `agl_ft` (+ `_sm/_lg_hide` or per-model `_low/_med/_high_hide`
  multi-needle bands), `compass`, `pitch_orientation`, `roll_orientation`, `vs_ft` (+ up/down hide).
  Driven from `UpdateCockpitGauges()` (`Core.c:428-441`); the S76 adds 4-band airspeed / 3-band AGL /
  3-needle VS logic (`RFFSHeli_S76.c:85-158`).
- **Wheels/doors** — vanilla CarScript `damper_*`, `AnimHitWheel_*`, plus per-model `DoorsDriver`/
  `DoorsCoDriver`/`DoorsCargo1/2` (`S76_config.cpp:347-370`).

[VERIFIED-RFFS] **Engine-start / rotor-spin state machine** — `m_heli_state`
(0=off, 1=startup, 2=running, 3=shutdown, +11/13 mid-transition; `Core.c:100`). `ExecuteAnimations()`
(`Core.c:1323-1368`) dispatches per state; `StartUpAnimation()` ramps `rotor1_speed` and cross-fades
to blur at 80% of `c_startup_sound_length` (`Core.c:1481-1502`). `EvaluateDamageStates()`
(`Core.c:1371-1468`) is the failure brain: a missing/ruined wiring harness, ruined engine/main-rotor,
bingo fuel, or (if `c_has_hydraulics`) low hydraulic fluid all force `m_heli_state = 3` (auto-shutdown);
low hydraulics also degrade cyclic authority via `m_cyclic_modifier` (`Core.c:1407-1414`).

[VERIFIED-RFFS] **Memory points** (from config `memoryPoints[]` + script reads):
`dmgZone_chassis/avionics/engine/hydraulics/fuelTank/rotor1/rotor2/lights_1_1`
(`S76_config.cpp:561-665`), `ptcExhaust_start` (engine smoke, `Core.c:1332/1343`), crew
`crewDriver/crewCoDriver/crewCargo1-4` + `pos_*`/`pos_*_dir` (`S76_config.cpp:125-171`), headlight
points via CarScript. **The `.p3d` itself was not read** — memory points are
[VERIFIED-RFFS] from config/script text, [UNVERIFIED] as actual model selections.

[VERIFIED-RFFS] **Crew** (`S76_config.cpp:125-171`): Driver + CoDriver + Cargo1-4 (6 seats), each with
`actionSel`/`proxyPos`/`getInPos`/`getInDir`. Both front seats have `isDriver=0` (control is arbitrated
in script via `m_pilot_in_command`, not the vanilla driver flag) — this is how RFFS gives pilot and
copilot flight control with a hand-off toggle.

[VERIFIED-RFFS] **Per-component DamageZones** (`S76_config.cpp:546-677`) — a real aviation damage model:
`Chassis`, `Avionics`, `Engine`, `Hydraulics`, `FuelTank`, `MainRotor`, `TailRotor`, `Reflector_1_1`
(landing light). Each has own hitpoints + `transferToZonesNames`/`Coefs` cross-links (e.g. Engine→Hydraulics
0.5, TailRotor→Chassis 0.75+Engine 0.2) and `inventorySlots`/`Coefs` tying part health to attachment
health. Global `hitpoints=8000`. Contact/collision damage flows through `m_ContactCache` +
`ChassisImpactDamage()` (hard skid landing >1500 fpm → `DecreaseHealth("Chassis")`, `Core.c:752-768`).

## 5. Inputs, actions, aviation attachments, HUD

[VERIFIED-RFFS] **Start/Stop actions** replace the vanilla car ones:
- `ActionStartHelicopter` (`ActionStartHelicopter.c:9-205`) — in-vehicle, driver/copilot-in-command
  only, blocked if `c_grounded` or engine ruined; on start it verifies battery(>5 energy)+igniter+
  (hydraulic hoses if applicable)+wiring+fuel, sets `m_heli_state=1`, and calls `OnBeforeEngineStart`.
  `ActionStopHelicopter` (`ActionStopHelicopter.c:1-101`) requires airspeed <8 kph → sets `m_heli_state=3`.
  Both vanilla `ActionStartEngine`/`ActionStopEngine` are `modded` to return false on an `RFFSHeli_base`
  (`ActionStartHelicopter.c:209-232`, `ActionStopHelicopter.c:104-127`), and `SetActions()` removes the
  car horn + start-engine actions (`Core.c:2456-2463`).
- **Component repair actions** — `ActionRepairHelicopter{MainRotor,TailRotor,Engine,Chassis,Hydraulics,
  Avionics,FuelTank,...}` + `ActionReplaceHelicopterAvionics`: each steps one damage zone up a health
  level with a repair item, driven off a per-player `RepairHelicopterActionData` zone selector
  (`ActionRepairHelicopterMainRotor.c`). This is the per-component maintenance loop that pairs with the
  DamageZones above.

[VERIFIED-RFFS] **Aviation attachments** replace the car vitals: `AviationBattery`, `AviationIgniterPlug`,
`AviationHydraulicHoses`, `AviationWiringHarness` (custom `CfgSlots` + inventory items in
`Core_config.cpp:159-505,875-908`). The heli overrides `IsVitalCarBattery/SparkPlug/...` → false and
`IsVitalAviationBattery` → true (`Core.c:2227-2260`); `GetBattery()` returns the aviation battery
(`Core.c:2268-2271`). Fuel = `CarFluid.FUEL`; hydraulic fluid = `CarFluid.OIL` (`Core.c:1135-1136`).

[VERIFIED-RFFS] **HUD** — `modded class IngameHud` (`headsUpDisplay.c:1`) creates
`RFFSHeli_Core/GUI/RFFSHelicopterGUI.layout` under the vanilla `LeftHUDPanel` (`:66-71`). Per-frame it
gets the player's `GetCommand_Vehicle().GetTransport()`, casts to `RFFSHeli_base`, and shows the panel
only for the in-command pilot/copilot with HUD enabled and (optionally) a pilot helmet (`:150-165`). It
reads telemetry straight off the synced heli fields (`RFFSHeli.m_airspeed_kph`, `m_altitude_m`,
`m_fuel_level`, `m_hydraulic_level`, `m_collective_level`) and `GetHealthLevel(...)` for warning lights
(`:202-490`). A **badly-damaged/ruined Avionics zone distorts or blanks the HUD** (`:167-187`) — a nice
touch tying the instrument panel to the avionics damage zone. Metric/imperial switch honoured throughout.

## 6. Multiplayer / sync

[VERIFIED-RFFS] Server-authoritative: `FlightSimulation()` only runs under `g_Game.IsServer()`
(`Core.c:1151`). State is pushed to clients via a bank of `RegisterNetSyncVariable*` in the ctor
(`Core.c:189-208`): telemetry floats (`m_altitude_m`, `m_agl_altitude_m`, `m_airspeed_kph`), the
`m_heli_state` int, `m_collective_level`, `m_rotor_spin`, fuel/hydraulic levels, klaxon/engine-damaged/
bullet-strike sound flags, `m_pilot_in_command`, and the packed `c_encoded_config_bool`. Every state
mutation calls `SetSynchDirty()`. The client pump `EOnFrame`→`EOnSimulate` (`Core.c:1008-1016`)
does not mirror physics or interpolate pose — `FlightSimulation()` is server-gated (`Core.c:1151`)
and the client re-entry only runs animations + input sync (`Core.c:1143-1145`); proxy pose
presentation is native CarScript replication, and the client never owns the authoritative velocity.

## 7. Not read / [UNVERIFIED]

- **`modded_Inputs.xml`** — referenced (`Core_config.cpp:30`); the `UARFFS*` input *names* are confirmed
  from script reads (`Core.c:491-501,549-554,563-583`). The file ships inside `RFFSHeli_Core.pbo`
  (`mod-sources.md`) and holds only `<actions>`, `<sorting>` and `<preset>`, with no input `<context>`;
  the individual key bindings in its `<preset>` are not recorded here.
- **`.p3d` models + `model.cfg`** — not read. Memory points, rotor/gauge selections, and the
  skeleton bone graph are [VERIFIED-RFFS] as *names* (config/script), [UNVERIFIED] as actual model data.
- **`RFFSHelicopterGUI.layout`** and the sound `.p3d`/wave assets — referenced, not read.
- **`config.bin`** — the config files read are de-rapified `config.cpp`; treat as authoritative for
  classes/inheritance but verify exact numerics against the live PBO before shipping.
