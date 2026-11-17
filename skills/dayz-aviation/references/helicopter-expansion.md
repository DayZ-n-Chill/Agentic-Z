# DayZ Expansion helicopters: the modular aerofoil framework

How the DayZ Expansion vehicle framework flies helicopters and planes: a `CarScript` entity that hosts physics modules, the `ExpansionPhysicsState` force and torque accumulator, the config driven aerofoil module, the rotor module (rotor disc, autorotation, vortex ring state, retreating blade stall, ground effect), the legacy `Transport` based stack, and how one base serves many aircraft. Open it when a task targets Expansion aircraft or weighs a module system against one flight loop.

Third-party material, not yet checked on `P:\`. The mod is not obfuscated (DayZ Expansion Mod Team; its scripts are published under CC BY-NC-ND, so read them for the pattern and do not copy them). Every claim below was read from the mod's own vehicle scripts, which are not in this repo. Citations are `file:line` into those files: `ExpansionVehicleHelicopter.c` is the rotor module, `CarScript.c` is Expansion's `modded class CarScript`, `ExpansionHelicopterScript.c` is the heli entity, the rest are named in full. Tags: `[VERIFIED-EXP]` read from that source, `[UNVERIFIED]` not read line by line or not in the copies, so do not invent it. Learn the pattern from it and write the mod's own code; `skills/_shared/vehicles/helicopters.md` says which model to build from.

**This is the fifth aircraft implementation and the first that is a general vehicle-physics
*framework* rather than one bespoke flight loop.**

Where SIB/RFFS/MH6 are each a single hand-written flight method bolted onto one heli, Expansion is a
**data-driven module system**: the airframe is composed of auto-configured physics objects (wheels,
axles, engines, gearboxes, **aerofoils**, and — for helis — a **rotor module**), each of which computes
its own force at its own position every tick and adds it to a shared accumulator that is committed once
via `dBodyApplyForce`/`dBodyApplyTorque`. One core serves cars, boats, planes and helicopters.

## 1. Architecture — entity `: CarScript` + module system + physics-state accumulator

[VERIFIED-EXP] Same **CarScript-as-aviation** hack as the other four, but organised as a framework:

| Layer | Role | Cite |
|---|---|---|
| `modded class CarScript` (Expansion's) | hosts the module system: `m_Modules`/`m_Aerofoils`/`m_Wheels`/`m_Axles`/`m_Engines`/`m_Gearboxes` arrays, the `m_State` (`ExpansionPhysicsState`) accumulator, the `m_Event_*` dispatchers, and `EOnSimulate` which drives the whole per-tick pipeline | `CarScript.c:19,28`, `EOnSimulate` `:2282-2447` |
| `ExpansionHelicopterScript : CarScript` | the heli **entity**: owns an `ExpansionVehicleHelicopter m_Simulation` (the rotor module), heli tunables, autohover/landing state, warning sounds, wreck class | `ExpansionHelicopterScript.c:17-19` |
| `ExpansionVehicleHelicopter : ExpansionVehicleModule` | the **rotor module** itself — collective/cyclic/anti-torque → rotor thrust + torque; a *special module*, not one-aerofoil-per-blade | `ExpansionVehicleHelicopter.c:223` |
| `ExpansionGyrocopter : ExpansionHelicopterScript`, `ExpansionBigGyrocopter : ExpansionGyrocopter` | concrete inherited aircraft — pure config/subclass on the shared base | `ExpansionGyrocopter.c:25,256` |

[VERIFIED-EXP] **Pawn replication** (client-prediction + server reconciliation, same family as MH6 and
LM_Planes): `ExpansionHelicopterScriptMove : CarScriptMove` + `ExpansionHelicopterScriptOwnerState :
CarScriptOwnerState` carry the flight state (`m_RotorSpeed`, `m_Collective`, `m_AntiTorque`,
`m_CyclicForward`, `m_CyclicSide` + their targets; `ExpansionVehicleHelicopter.c:3-110`).

### 1a. The per-tick pipeline (`CarScript.c EOnSimulate`, `:2282-2447`)

[VERIFIED-EXP] Server-authoritative / physics-host-gated (`m_IsPhysicsHost = IsOwner()` on client,
always true on server, `:2300-2344`). When active and simulating (`:2403-2418`):

```
m_State.SetupSimulation(dt);        // snapshot transform, mass, world+model-space velocities, zero m_Force/m_Torque
m_State.CalculateAltitudeLimiter(); // altitude-based lift falloff (soft ceiling)
m_Event_PreSimulate.PreSimulate(m_State);  // every module computes its coefficients
OnSimulation(m_State);                     // per-entity hook (heli overrides -> runs rotor module)
m_Event_Simulate.Simulate(m_State);        // every module adds its force+torque to the accumulator
...
m_State.ApplySimulation_CarScript(dt, ...) // -> ApplySimulation -> dBodyApplyForce/Torque
```

The module dispatchers are **singly-linked-list walkers** (`ExpansionVehicleModuleEvent`, whole file):
`PreSimulate`/`Simulate`/`Control`/`PostSimulate`/`Animate` each iterate the chain and call the matching
hook on every module (`ExpansionVehicleModuleEvent.c:83-125`). Base module lifecycle (all no-op
overridables) is `ExpansionVehicleModule` (`ExpansionVehicleModule.c:94-112`) — plus Pawn hooks
`ObtainMove`/`ConsumeMove`/`ReplayMove`/`ObtainState`/`RewindState` (`:70-89`).

### 1b. The accumulator — `ExpansionPhysicsState`

[VERIFIED-EXP] This is the shared force/torque sink every module writes into:
- `SetupSimulation(pDt)` (`ExpansionPhysicsState.c:178-207`): caches `m_Transform`, `m_Mass =
  dBodyGetMass`, world **and** model-space linear/angular velocity + acceleration; **zeroes `m_Force` and
  `m_Torque`** (`:188-189`).
- `GetModelVelocityAt(relPos)` (`:473-475`) = `m_LinearVelocityMS + m_AngularVelocityMS * relPos` — the
  local airflow at any module's position (this is what the aerofoil reads).
- `ApplySimulation(pDt)` (`:209-217`) commits the whole tick in one place:
  `dBodyApplyForce(m_Entity, m_Force); dBodyApplyTorque(m_Entity, m_Torque);` (`:216-217`).

**So the entire fleet is force-based** — unlike RFFS's kinematic `SetVelocity`, Expansion always goes
through `dBody*` forces, like MH6. The `dBodyApplyForce` at `CarScript.c:883` is unrelated — it is the
explosion pop when a vehicle is destroyed, not the flight applicator.

## 2. The aerofoil module — real aerodynamics, config-driven, geometry-placed

[VERIFIED-EXP] `ExpansionVehicleAerofoil : ExpansionVehicleModule` (`ExpansionVehicleAerofoil.c:17`) is
the base of the whole aerodynamic system — a self-contained lifting surface. This is what makes the
framework *data-driven*: an aerofoil auto-configures itself from config and needs no code.

**Config-driven construction** (ctor `:50-135`): reads
`CfgVehicles <veh> SimulationModule Aerofoils <name>`:
- `type` — Fixed/Wing/Rudder/Elevator, string-or-int (`:59-73`).
- `up` — the surface's up-vector, `ConfigGetTextOut(...).ToVector()` (`:77-78`).
- `min`/`max` — **memory-point names**; area is derived from the world extent between them (projected
  perpendicular to `up`), `m_Position = midpoint` (`:80-111`). **The surface's size and location come
  from the model's memory points**, not from magic numbers.
- `camber`, `maxControlAngle`, `stallAngle`, optional `animation` (`:113-124`).

**Aerodynamics in `PreSimulate`** (`:152-203`):
- Local airflow = `-pState.GetModelVelocityAt(m_Position)`, normalized; `m_AirflowMagnitudeSq = v²`
  (`:154-156`).
- Control input mapped by type: Rudder←`-m_Controller.m_Yaw`, Elevator←`m_Controller.m_Pitch`,
  Wing←±`m_Controller.m_Roll` (sign by which side, `m_Position[0]<0`), so **one aerofoil class becomes an
  aileron/elevator/rudder purely by config `type`** (`:158-178`).
- Angle of attack `= Asin(dot(m_Up, airflowNormal)) · RAD2DEG` (`:183`).
- Dynamic pressure `m_PressureCoef = area · 0.5 · Expansion_GetDensity(altitude) · v²` (`:187`) — real
  air-density falloff by altitude (`Expansion_GetDensity` is external to this copy, [UNVERIFIED] body but
  named/called here).
- Lift coefficient with stall: `sin(liftAngle · π/2 / stallAngle) · 2`, forced to 0 once
  `|liftAngle| > 2·stallAngle` — a real stall curve (`:191-193`).
- Drag coefficient parabolic: `0.05 + ((dragAngle+angle)/(stallAngle+|angle|))²` (`:195-202`).

**Force + torque in `Simulate`** (`:205-231`) — the crux of the modular idea:
```
force  = (m_Up · q · Cl) + (airflowNormal · q · Cd)      // lift along up, drag along airflow
force *= m_DeltaTime
pState.m_Force  += force.Multiply3(pState.m_Transform)            // local force -> world, accumulate
pState.m_Torque += (position * force).Multiply3(pState.m_Transform)  // r x F -> world torque, accumulate
```
[VERIFIED-EXP] **The pitching/rolling/yawing moment falls out of the geometry**: torque is `position ×
force` where `position` is the module's own location on the airframe (`:230`). A rudder placed at the
tail produces yaw *because it is at the tail* — no hand-tuned lever-arm constant. `Animate`
(`:233-236`) drives the control-surface animation phase off `m_Input`. `ExpansionVehicleHelicopterAerofoil
: ExpansionVehicleAerofoil` (`ExpansionVehicleHelicopterAerofoil.c:1-5`) is an **empty stub** — helis
reuse the fixed-wing aerofoil unchanged for any body lifting surfaces.

## 3. The rotor module — collective / cyclic / anti-torque / autorotation

[VERIFIED-EXP] The rotor is **its own module** (`ExpansionVehicleHelicopter : ExpansionVehicleModule`,
`ExpansionVehicleHelicopter.c:223`), not an aerofoil-per-blade (that would be far too expensive). It is a
large, physically-sophisticated model — 3234 lines total; the parts below are read directly, the
remainder is [UNVERIFIED] (see §6). Confirmed structure:

- **Two simulation modes** (`m_SimulationMode`, default `RotorDisk`): `Simulate_RotorDisk` (the A3
  RotorLib-style blade-element model, `:2237+`) and a `DIAG_DEVELOPER`-only `Simulate_Legacy`
  (`:1746+`), dispatched at `:1722-1735`, then a shared `Simulate_Common` (`:1819+`). It applies forces
  the framework way: `pState.m_Force += force; pState.m_Torque += torque;` at the end of `Simulate`
  (`:1742-1743`).
- **Control channels** (`:66-72,301-333`): `m_Collective`, `m_AntiTorque`, `m_CyclicForward`,
  `m_CyclicSide`, each with a `*Target` (from `m_Controller`), rate limits, trims, and hydraulic-fluid
  authority (`CarFluid.OIL` = hydraulics, `:1693`). Collective/cyclic response is **gated by
  `m_RotorSpeed`** (`m_CollectiveDelta = (target-current)·m_RotorSpeed²`, `:1676`; cyclic only moves if
  `m_RotorSpeed != 0`, `:1705-1711`) — no control authority without RPM, like MH6.
- **Rotor thrust (RotorDisk model, `:2237-2320+`)**: real momentum-theory hover induced velocity
  `viHover = sqrt(mass·g / (2·ρ·π·r²))` (`:2265-2267`), advance ratio `mu = horiSpeed/omegaR`
  (`:2246-2250`), **8-azimuth-sector blade-element sampling** (`:2300-2320`), effective translational
  lift by iterating induced velocity (`:2275-2280`), **ground effect** (`:2252-2263`), **Vortex Ring
  State** thrust loss (`ComputeVRSSeverity`, `:2287-2292`), **Retreating Blade Stall** above `mu=0.35`
  (`:2313-2318`), atmosphere via `pState.m_AltitudeLimiter` (`:2305`). Thrust is applied up the body axis;
  cyclic tilts the disc so lift redirects into translation. (Legacy model is coarser: thrust `∝ collective
  · rotorSpeed² · liftForceCoef · mass · liftFactor`, `:1806-1815`.)
- **Anti-torque / tail rotor** (`Simulate_Common`, `:1932-1960`): tail-rotor force `= m_AntiTorque ·
  m_TailForceCoef · m_RotorSpeed²`, minus the **main-rotor reaction torque** it must cancel
  (`m_MainRotorTorque · m_RotorSpeed² · torqueSpeedFactor`, `:1957-1959`). **Explicitly handles
  tandem/coaxial rotors**: if `m_TranslatingTendencyCoef == 0` (no tail rotor) the main-rotor torque
  cancellation is skipped (`:1947-1949`). Tail-rotor damage injects malfunction torque (`:1934-1944`) —
  the classic loss-of-tail-rotor spin.
- **Autorotation** (`:1662-1667`): if the heli is descending and the rotor is off
  (`goingDown > 0 && m_RotorSpeedTarget < 0.1`), `m_RotorSpeed` is driven *up* from the falling airflow
  (`change = (min(goingDown,1) - m_RotorSpeed)·0.08·pDt`) — the descending air spins the freewheeling
  rotor, exactly the real autorotation energy source (comment cites the Wikipedia autorotation diagram,
  `:1662`).
- **Translating tendency** (`Simulate_Common`, `:1823-1830`): the lateral hover drift a real tail rotor
  induces (pushes right for a CCW main rotor), full at hover, gone by ETL.

**This is the most physically-complete rotary model of the five** — more so than MH6's PD controller,
because it models the rotor *disc* (induced velocity, blade elements, VRS, RBS, ETL, ground effect,
autorotation) rather than a lumped lift force. The trade-off is size and coupling
(`helicopter-model-comparison.md`).

## 4. The legacy era — `ExpansionVehicleBase : ExpansionVehicleBaseBase : Transport` (its own physics)

[VERIFIED-EXP] Before Expansion re-based its vehicles on `CarScript`, it had a **parallel physics stack
that inherited `Transport` directly**, bypassing CarScript entirely:
`ExpansionVehicleBase : ExpansionVehicleBaseBase` (`ExpansionVehicleBase.c:13`) and
`ExpansionVehicleBaseBase : Transport` (`ExpansionVehicleBase_Towing.c:1`). It carries its **own**
`m_Controller`, `m_State` (`ExpansionPhysicsStateT<ExpansionVehicleBase>`) and `m_ExpansionVehicle`
(`ExpansionVehicleBase.c:19-28`) — the same module/accumulator idea, but on a `Transport` base rather
than reusing DayZ's `CarScript` crew/fuel/damage contract. The module system (`ExpansionVehicleModule`
ctor, `ExpansionVehicleModule.c:36-42`) still binds to *either* base: it casts the vehicle to
`ExpansionVehicleBase` **or** `CarScript` to find the controller. **The modern path is the `CarScript`
one** (`ExpansionHelicopterScript : CarScript`); the `Transport`-based `ExpansionVehicleBase` is the
legacy era, kept for towing/compatibility.

Current state (`salutesh/DayZ-Expansion-Scripts@14fd692`, 2026-10-15): the vehicle classes Expansion still
builds on are `CarScript` children, `ExpansionHelicopterScript : CarScript` and `ExpansionBoatScript : CarScript`
(`DayZExpansion/Vehicles/Scripts/4_World/DayZExpansion_Vehicles/Entities/Vehicles/expansionhelicopterscript.c:17`,
`expansionboatscript.c:16`). `ExpansionVehicleBase` survives only as a stub in an `OBSOLETE/` folder that derives
from `Transport` directly (no `ExpansionVehicleBaseBase` any more) and exists, per its own comment, only so
third-party mods that still name the type keep compiling; its methods are `[Obsolete]` and return empty values
(`.../Entities/Vehicles/OBSOLETE/ExpansionVehicleBase.c:1-12`). Write new code against the `CarScript` classes.

## 5. Clean inheritance — one base, many aircraft

[VERIFIED-EXP] Concrete aircraft are thin subclasses of `ExpansionHelicopterScript` carrying almost only
config: `ExpansionGyrocopter : ExpansionHelicopterScript` and `ExpansionBigGyrocopter : ExpansionGyrocopter`
(`ExpansionGyrocopter.c:25,256`) are the two present in the research copy. Expansion ships more helis on
the same base (the Merlin and an MH-6 are referenced in comments — big-heli ground-clip handling
`ExpansionVehicleHelicopter.c:2433`, rocket-damage thresholds `ExpansionHelicopterScript.c:450`), and the
`REFERENCE_MASS = 1700 //! MH6` tuning anchor (`ExpansionVehicleHelicopter.c:228`) confirms the framework
is authored against an MH-6-class reference and scaled per-heli by mass/bounding-radius. **This is the
payoff of the modular design: a new aircraft is a config + a subclass, not a new flight loop.** [UNVERIFIED]
the concrete `CfgVehicles` classes of Merlin/UH1H/HatchBird — not in the research copy.

## 6. Not read / [UNVERIFIED] — do not fabricate

- **`ExpansionVehicleHelicopter.c` in full** — 3234 lines. The architecture, control-channel integration
  (`:1655-1743`), autorotation (`:1662-1667`), rotor-disk thrust core (`:2237-2320`), anti-torque/tail
  (`:1900-1960`), and legacy thrust (`:1800-1816`) were read directly. The **remaining bulk** — the full
  blade-element azimuth loop body past `:2320`, the complete `Simulate_Common` torque assembly, autohover
  (`UpdateAutoHover`-family around `:1440-1600`), auto-trim, RBS/VRS coefficient derivations, the collision
  `ExpansionHelicopterScriptRotor` callback (`:117`), and networking — are **[UNVERIFIED]** (not read line
  by line).
- **`Expansion_GetDensity(altitude)`** — called by the aerofoil (`ExpansionVehicleAerofoil.c:187`) and the
  ISA/altitude atmosphere generally; its definition is outside these copies. [UNVERIFIED] body.
- **`config.cpp` / `SimulationModule` blocks** — the `Aerofoils`/rotor/wheel config the modules read
  (`CfgVehicles <veh> SimulationModule ...`) is [UNVERIFIED] as on-disk config; confirmed only as the
  config *paths* the script reads.
- **`.p3d` + `model.cfg`** — memory points (aerofoil `min`/`max`, rotor selections) confirmed as *names*
  the script reads; [UNVERIFIED] as actual model data.
- **Concrete non-Gyrocopter aircraft classes** (Merlin/MH-6/UH1H) — referenced, not in the copy.
