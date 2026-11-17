# Helicopter flight models compared

SIB, RFFS, MH6, DayZ Expansion and LM_Planes side by side: what all five share, monolithic flight loop against modular aerofoil system, kinematic against force based integration, a table of differences, which one to build from, and how players say each one feels. Open it when choosing a flight model or explaining a trade-off; the per-mod detail is in `helicopter-rffs.md`, `helicopter-mh6.md`, `helicopter-sib.md`, `helicopter-expansion.md` and `fixed-wing-lm-planes.md`.

Third-party material, not yet checked on `P:\`. Every fact comes from the five mods' own sources as read for the per-mod files; the tags (`[VERIFIED-RFFS]`, `[RECOVERED-SIB]`, `[RECOVERED-MH6]`, `[UNVERIFIED]`) and `file:line` citations mean what they mean there. The player feel section is secondhand opinion, not a measurement.

## Four implementations, three authors

**Four independent flight-model implementations from three independent authors** have been read:
**SIB** (SIBNIC) heli, **RFFS** (RedFalcon) heli, **MH6** (Llama) heli, and **LM_Planes** (Llama +
Itspete-Here) fixed-wing. All four use the **CarScript-as-aviation** hack, which pins that down as **the**
way to do aviation in DayZ today. (Note on authorship: Llama accounts for two of the four — the LM_Planes
fixed-wing *and* the MH6 heli — nailed by the `LM_LLAMA/LM_Vehicles/MH6/` particle paths,
`MH6_scripts\b_off152027_o355.c:3-5`. So it is three authors, four aircraft, two of them force-based and
both Llama's.)

## What is common to all four

- **`CarScript` is the aviation base.** DayZ has no flight class; all four inherit `CarScript`, keep a full
  ground `SimulationModule` (wheels/axles/gearbox) as a taxi fallback, and override the physics in script.
  [VERIFIED-RFFS `Core_config.cpp:517`] · [RECOVERED-SIB `HeliTest_SIB:Heli_sib_cript:CarScript`] ·
  [RECOVERED-MH6 `class MH6 extends CarScript`, `MH6_flightmodel.c:112`] ·
  [LM_Planes `LlamaPlaneScript extends CarScript`].
- **Custom `UA*` inputs** drive flight, read via `GetInputInterface().SyncedValue(...)` / `GetUApi()`
  (SIB `UASIBHeli*`, RFFS `UARFFS*`, MH6 `UAKTHeli*`) or the Pawn move pipeline (LM_Planes), declared in a
  modded `Inputs.xml`.
- **Rotor/prop animation via `SetAnimationPhase`** — a static↔blur mesh swap driven by rotor state, not
  RPM-bound geometry (SIB `rot_h_start`/`rot_h_blur_end`; RFFS `rotorN_speed`/`rotorN_blur_hide`; MH6
  `rotor_1_1`/`rotor_1_1_hide`/`rotor_1_1_rotate_hide`); LM_Planes animates control surfaces the same way.
- **Per-component DamageZones** with cross-transfer coefficients (engine/rotor(s)/fuel/etc.) and
  attachment-tied part health.
- **Server-authoritative physics** gated on `IsServer()` / `IsServerOrOwner()`; state pushed to clients.
  A client never owns the authoritative velocity: RFFS's client pump runs only animations and input
  sync (corrected 2026-08-03, see `helicopter-rffs.md` section 2), while MH6, LM_Planes and Expansion
  predict on the owner and reconcile with the server.

## Cross-author synthesis, extended — now five aircraft, four authors

With Expansion added, the corpus is **five flight-model implementations from four independent authors**:
**SIB** (SIBNIC), **RFFS** (RedFalcon), **MH6** + **LM_Planes** (Llama), and **Expansion** (DayZ Expansion
Team). All five use **CarScript-as-aviation** (Expansion's modern path does; its *legacy* `Transport`-based
`ExpansionVehicleBase` is the one exception, and it was superseded). Two orthogonal axes now organise them.

### Monolithic flight loop vs modular aerofoil system

This is a **different axis** from kinematic-vs-force (§"The new axis" below) — it is about *how the
per-tick calculation is organised*, not how it is integrated.

- **Monolithic** (SIB, RFFS, MH6, LM_Planes): one large flight method computes the whole aircraft's motion
  inline — `Simulate()`/`FlightSimulation()`/`ApplyHelicopterPhysics()` — with **hard-coded constants**,
  reading orientation/velocity, computing lift/drag/attitude in one pass, and applying **one result at the
  end** (`SetVelocity` or a single `dBodyApplyForce`/`Torque`).
- **Modular** (Expansion): the aircraft is a **bag of auto-configured physics modules** (aerofoils + a
  rotor module + wheels/axles/engines). Each module, in `PreSimulate`/`Simulate`, computes **its own force
  at its own position** and adds it to a shared `ExpansionPhysicsState` accumulator
  (`pState.m_Force += ...`, `pState.m_Torque += (position × force)...`,
  `ExpansionVehicleAerofoil.c:229-230`); the framework commits the sum once via
  `dBodyApplyForce`/`dBodyApplyTorque` (`ExpansionPhysicsState.c:216-217`).

**Advantages of modular:**
- **(a) Data-driven.** A new aircraft is a config block + a thin subclass, not new code — that is exactly
  why one Expansion base flies the Gyrocopter, Merlin, MH-6, etc. (`ExpansionGyrocopter.c:25,256`). The
  monolithic mods each hand-write (or copy-paste) a flight method per model.
- **(b) Moments emerge from geometry.** Torque is `r × F` at the module's real airframe position
  (`ExpansionVehicleAerofoil.c:230`): a tail rudder yaws *because it sits at the tail*. The monolithic
  models fake the lever arm with tuned constants (SIB nudges Euler angles by literals; MH6 multiplies by
  `CYCLIC_PITCH_RATE·80`).
- **(c) Real physics that generalises.** Stall, per-altitude air density (`Expansion_GetDensity`), ground
  effect, ETL, VRS, RBS, autorotation all fall out of one model — where SIB fakes "lift" with a constant
  `+0.25 m/s` and a hard 1500 m ceiling.
- **(d) One core, every vehicle type.** The same module system + accumulator serves car, boat, plane and
  heli; the aerofoil is literally reused by the heli (`ExpansionVehicleHelicopterAerofoil` is an empty
  subclass).
- **(e) Live introspection.** Each module has a `CF_OnDebugUpdate` debug window
  (`ExpansionVehicleAerofoil.c:137-149`) — per-surface AoA/Cl/Cd on screen. Monolithic models debug by
  Print.

**Advantages of monolithic / costs of modular:**
- **(a) Weight and coupling.** Using the aerofoil means swallowing the whole scaffold — the module base +
  event dispatcher + `ExpansionPhysicsState` + Expansion's `modded CarScript`
  (`CarScript.c` alone is 3815 lines; the rotor module 3234). MH6 is a competent, complete force-based heli
  self-contained in one ~48 KB script. If you want *one* aircraft, the framework is mostly overhead.
- **(b) Debuggability.** A monolithic loop reads top-to-bottom — one method is the whole truth. The modular
  path scatters the physics across N modules × 3 hooks + an accumulator + the CarScript integration; to
  follow one force you trace it from config → `PreSimulate` → `Simulate` → accumulator → apply.
- **(c) Config surface = silent-failure surface.** A wrong memory-point name for an aerofoil's `min`/`max`
  yields a wrong area and a subtly wrong flight model with **no compile error**
  (`ExpansionVehicleAerofoil.c:80-111`) — the price of data-driven. A hard-coded constant can't be
  mis-wired.
- **(d) Realism is less forgiving.** Real Cl/Cd/stall/VRS/RBS make the aircraft twitchy, stallable, and
  spinnable — great for a sim, worse for a pick-up-and-fly server. The kinematic arcade feel (RFFS) is more
  accessible; sometimes that is the *desired* design, not a deficiency.
- **(e) Per-frame cost.** N modules each doing trig + a matrix multiply every tick > one inlined loop.
- **(f) Intuitive tuning.** Turning one `thrust_rate` knob (RFFS's %-of-baseline JSON) is easier than
  reasoning about lift coefficients, blade pitch `theta0`, and advance-ratio thresholds.

**Honest caveat — Expansion does not model every blade as an aerofoil.** That would be prohibitively
expensive. The **rotor is its own dedicated module** (`ExpansionVehicleHelicopter`, a rotor-disc /
blade-element-*sampling* model over 8 azimuth sectors, `ExpansionVehicleHelicopter.c:2300-2320`), not a
swarm of per-blade aerofoils. The aerofoil system shines on **fixed wings and control surfaces**; on a heli
it is **rotor-module + body aerofoils**, not aerofoils-all-the-way-down.

### Decision framework — which model to build from (skill default)

The two axes give a clean picking rule. **Default recommendation:**

1. **Custom heli, ship it now, arcade feel, code you can read end-to-end → monolithic.**
   - Predictable kinematic handling → **build from RFFS** (clean, DRM-free, physically-grounded but
     `SetVelocity`; discrete 0-20 collective; typed JSON config; flight HUD).
   - Real momentum/inertia + PD stability + autohover, still one legible script → **build from MH6**
     (force-based `dBodyApplyForce`/`Torque`, ISA density, rotor-RPM authority).
2. **A multi-aircraft vehicle *framework* with realistic, config-tunable physics → Expansion**
   (modular aerofoil + rotor-disc). You pay its architecture and a steeper tuning curve (memory-point
   config, blade-element coefficients) but you get data-driven aircraft, geometry-derived moments, the most
   complete rotor model (VRS/RBS/ETL/autorotation), and one core across car/boat/plane/heli.
3. **Fixed-wing with real aerodynamics → LM_Planes** (monolithic, custom Pawn) **or Expansion** (modular
   aerofoil — this is where the aerofoil system is strongest).
4. **Do not build from SIB.** Its simple model is a minimal kinematic hack (fake `+0.25 m/s` lift, hard
   1500 m ceiling) and its advanced/force model is **DRM-locked with the core integrator missing**. Use SIB
   only as a corroborating third data point.

Rule of thumb: **one aircraft, want it flying and hackable → monolithic (RFFS kinematic / MH6 force).
A fleet, want config-tunable real physics → Expansion modular.** The other axis (kinematic vs force) is
now a *sub*-choice inside "monolithic".

---

## The new axis that matters most: kinematic vs force-based

The previous 3-way write-up concluded "a buildable DayZ aircraft is kinematic". **MH6 refutes that** — it
is force-based, legible, and buildable. The real split is:

| Implementation | Integration | Source state | So the takeaway is… |
|---|---|---|---|
| **SIB — simple** (SIBNIC) | **Kinematic** — `SetVelocity`/`SetOrientation`, `dBodyApplyImpulse` commented out | Recovered, legible (buildable) | Arcade heli, minimal code — the simplest teachable loop |
| **SIB — advanced** (SIBNIC) | **Force** — `dBodyApplyForce`/`Torque` in the applicator `qmdkldkpqpmlsib` | **DRM-locked + core integrator missing** | Proof force was *used*, but unbuildable (lost + license-gated) |
| **RFFS** (RedFalcon) | **Kinematic** — `SetVelocity`/`SetOrientation`, `dBodyApplyImpulse` only as a commented line (`Core.c:272`) | Clean, complete, DRM-free | The clean **kinematic** reference: physically-grounded (attitude-rotated lift vector, ground effect, ETL, governors, drag, weathervaning), discrete 0-20 collective, typed JSON config, flight HUD |
| **MH6** (Llama) | **Force** — real `dBodyApplyForce(this, totalForce)` + `dBodyApplyTorque(this, totalTorque)` every tick (`MH6_flightmodel.c:1165-1166`) | **RECOVERED, clean, complete** | The **force-based** reference: full PD flight controller, ISA air density, rotor-RPM authority, autohover/autoland — buildable today |
| **LM_Planes** (Llama) | **Force** — real aerodynamic lift/drag/stall forces applied at `axis_thruster` | Clean (public workshop) | The fixed-wing reference (real aerodynamics + custom Pawn) |

**Conclusion, corrected:** a buildable-from-source DayZ *helicopter* can be **either** kinematic (RFFS) or
force-based (MH6) — both are clean and complete on disk. The impression the SIB mod gave — that the
force-based model is always license-gated and out of reach — was an artifact of *that one author's DRM*,
not a property of DayZ. MH6 shows real `dBodyApplyForce`/`Torque` rotor physics is fully viable in
plaintext Enforce. (And it is no coincidence the force-based heli is by the same author as the force-based
fixed-wing: LM_Planes already applied real forces; MH6 is that muscle carried onto a rotor.)

## What differs (all four)

| Axis | RFFS (RedFalcon) | SIB (SIBNIC) | MH6 (Llama) | LM_Planes (Llama) |
|---|---|---|---|---|
| Aircraft type | Helicopter | Helicopter | Helicopter | Fixed-wing (+ 1 amphib car) |
| Integration | **Kinematic** (`SetVelocity`) | **Kinematic** (simple); force (advanced, lost) | **Force** (`dBodyApplyForce`/`Torque`) | **Force** (aerodynamic) |
| Source state | **Clean, complete** | Obfuscated; simple recovered, **advanced DRM-gated + integrator missing** | **Recovered clean & complete** (config.bin missing) | Clean (public workshop) |
| Flight model | High-kinematic: attitude-rotated lift vector, ground effect, ETL, speed+climb governors, aero drag, weathervaning | Low-kinematic: pitch attitude → scalar forward speed; bank → yaw; passive +0.25 m/s hover | **PD controller**: RPM-gated authority, ISA-density lift, translational lift, ground effect, per-axis quadratic drag, overspeed + climb limiters | Real aerodynamics: lift/drag/stall, ISA atmosphere, PID auto-stab, NaN-safe forces |
| Collective / thrust | **Discrete 0-20 detent** × `c_thrust_rate` | `m_rotorTurn` ±2.8 momentary + passive baseline | Analog `m_ThrottleTarget` 0-1 → lift force `= mass·g·1.65 · collective · rotorSpeed² · density · …` | Throttle smoothed via Pawn move |
| Attitude stability | Recovery mode (level-to-velocity) | Attitude auto-recenter | **PD**: proportional (memory-point tilt) + derivative (angular-rate damping) | PID auto-stabilization |
| Autohover / autoland | none | Autohover **yes** (license-gated `AutopilotState` bot-map, DRM only) | **Autohover + autoland FSM** (kinematic `SetVelocity` assist on top of force flight) | n/a |
| Config store | **Typed named JSON** (`MasterConfig` + `HeliConfig`, `get*` accessors, %-of-baseline) | Positional `map<string,float>` from `$profile` JSON | **Hard-coded const literals** (`:141-176`); config.bin not recovered | ~60 `Get*` methods per aircraft (config-as-code) |
| Replication | Sync vars + `EOnFrame` client pump (animations and input sync only) | Sync vars + `EOnSimulate` mirror | **Custom Pawn** (`MH6OwnerState`/`MH6Move`, prediction + rewind) + 2 sync vars for toggles | **Custom Pawn** (`PlaneOwnerState`/`PlaneMove`, prediction + rewind) |
| Atmosphere | none (fixed ceiling clamp) | none (hard 1500 m literal) | **ISA `StandardAtmosphere`** density falloff (shared `Heli_Core` helper) | ISA atmosphere |
| HUD | **Full flight HUD** (airspeed/altimeter/collective/fuel/hydraulics/warning lights) | Config dials only | [UNVERIFIED] (config/model not recovered) | Cockpit dials |
| Openness | Fully open | DRM (HTTP license check to `sibnic.info`) | Recovered clean (JAPM, no live DRM in the flight script) | Open |

## Recommendation — pick by feel, not by "what's possible"

Both are now buildable; the choice is a design decision:

- **Want arcade / minimal code / predictable handling → kinematic. Build from RFFS.** It is clean,
  complete, DRM-free, and physically-grounded while staying kinematic (attitude-rotated lift, ground
  effect, ETL, governors, drag, weathervaning), with a discrete collective, typed JSON config, and a flight
  HUD. `SetVelocity` means no momentum surprises — the heli goes where the model says each tick.
- **Want realism / momentum / inertia / autohover → force-based. Build from MH6.** Real
  `dBodyApplyForce`/`Torque` gives genuine momentum and inertia (the heli carries its velocity, pendulums
  under the rotor, needs anticipation), a full PD stability controller, ISA-density performance falloff,
  rotor-RPM authority (no control until spun up), and hybrid kinematic autohover/autoland on top. More
  physically alive, more to tune.
- Use **SIB** only as a corroborating third data point (it independently confirms CarScript-as-aviation +
  baked-blur rotors + per-component damage, and its config-bitfield sync idea is worth mining) — do **not**
  build from its advanced model; that core is missing and license-locked.
- For **fixed-wing**, **LM_Planes** remains the reference (real aerodynamics + custom Pawn). For
  **rotary-wing**, you now have both a kinematic reference (RFFS) and a force-based one (MH6).

## Player-reported feel (empirical — secondhand, subjective)

Feel feedback relayed by a mod operator running these on a live server (2026-07-07). **Not measured** —
treat as subjective player impression, not a benchmark. It is the "feel" axis the code cannot show, and
it maps cleanly onto the verified mechanisms above:

| Mod | Player-reported feel | Most likely cause (code-verified) |
|---|---|---|
| **RFFS** | Strongest stabilization; most arcade; **best/easiest handling** | Heaviest assist stack on a kinematic base — speed + climb governors, trainer clamps, `UARFFSRecover` auto-level. Forgiving → easy to fly, but feels "managed"/on-rails. |
| **SIB** | **Most fluid** handling | Continuous collective (`m_rotorTurn`) vs RFFS's *discrete* 0-20 steps; weak ±0.1/tick recenter; direct `SetVelocity`, no governors → smooth and free, nothing fights the stick. Less forgiving. |
| **MH6** | **Lackluster — not fluid and poor recovery** ("worst of both") | Force-based momentum removes the direct/fluid feel, but its PD stabilizer (`PITCH_STABILITY 0.85`) + FSM autoland are not tuned strong enough for RFFS-grade recovery → the drag of force without the payoff of assistance. |
| **Expansion** | **Complex** for some players | Force-based + real rotor-disk aero (momentum, VRS/RBS, air-density falloff) + least arcade hand-holding → highest skill floor. |

**Design insight (the gap none of the five fill):** *fluidity* and *recoverability* are in tension because
both come from the stabilization system — strong constant stabilization (RFFS) is recoverable but not
fluid; weak stabilization (SIB) is fluid but not recoverable; force-based (MH6), under-tuned, loses
fluidity up front and gains no recovery. **No implementation decouples them.** The open improvement: a
fluid kinematic base (SIB-style continuous, direct response) + an *envelope-protection* stabilizer that
stays soft in normal flight (preserves fluidity) and firms up only near loss-of-control (provides
recovery) — fly-by-wire "normal law" instead of always-on correction. That is the one thing that would
feel better than all five, and it is a tuning problem, not new physics. Also confirmed from feel: strong
stabilization is not strictly "better" — RFFS wins controllability for the average player but that same
assist is what costs it the fluidity players praise in SIB. Pick by target audience, not by "strongest".


## An earlier community helicopter with attachable blades

A different mod, kept for contrast: `HelicopterSIB_Hommade_LF` (a reskin of `HelicopterModhommade`) showed
an [INFERRED] `CarScript` derived base with **attachable** rotor blades (`hommade_blade1/2`, tail
`hommade_bladem1/2`) and a `c_rotorSound` / `c_engineSound` / `c_warningSound` / `c_crashSound` hook
contract. Its flight model lived in the base addon, which was not available. The SIB mod in
`helicopter-sib.md` supersedes it as the documented flight pattern. Its own PBO holds one `.c` file of
1,177 bytes and is not the SIB source (`mod-sources.md`).
