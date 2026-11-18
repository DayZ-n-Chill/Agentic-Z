# Helicopter flight models compared

How the SIB, RFFS, MH6 and Expansion helicopters and the LM_Planes fixed-wing mod compare: what they share, a single flight loop against a module system, kinematic against force-based flight, which one to build from, and how players say each feels.

The detail per mod is in `helicopter-rffs.md`, `helicopter-mh6.md`, `helicopter-sib.md`, `helicopter-expansion.md` and `aviation-fixed-wing.md`; the `file:line` citations here point into those mods' scripts, named in brackets. These are third-party mods, not vanilla. The section on feel is player opinion, not measurement.

There are five flight models from four code bases: SIB, RFFS, MH6 with LM_Planes (one mod family, the two force-based ones), and Expansion.

## What they share

- `CarScript` is the base. Vanilla's own helicopter class, `HelicopterScript` (`P:\scripts\4_world\entities\vehicles\helicopterscript.c:4`), is unused by all of them. Each inherits `CarScript`, keeps a ground `SimulationModule` (wheels, axles, gearbox) as a taxi fallback, and overrides the physics in script: [RFFS `Core_config.cpp:517`], [SIB `HeliTest_SIB:Heli_sib_cript:CarScript`], [MH6 `class MH6 extends CarScript`, `MH6_flightmodel.c:112`], [LM_Planes `LlamaPlaneScript extends CarScript`]. Expansion's current classes do the same; its older `Transport`-based stack is obsolete.
- Custom `UA*` inputs declared in a modded `Inputs.xml`, read with `GetInputInterface().SyncedValue(...)` or `GetUApi()` (SIB `UASIBHeli*`, RFFS `UARFFS*`, MH6 `UAKTHeli*`) or through the Pawn move (LM_Planes).
- Rotors animated by `SetAnimationPhase` as a swap between a static and a blurred mesh driven by rotor state, not geometry tied to RPM (SIB `rot_h_start`, `rot_h_blur_end`; RFFS `rotorN_speed`, `rotorN_blur_hide`; MH6 `rotor_1_1`, `rotor_1_1_hide`, `rotor_1_1_rotate_hide`). LM_Planes animates control surfaces the same way.
- Damage zones per component with transfer coefficients (engine, rotors, fuel) and part health tied to attachments.
- Physics owned by the server, gated on `IsServer()` or `IsServerOrOwner()`. A client never owns the true velocity: RFFS's client pump runs only animation and input sync, while MH6, LM_Planes and Expansion predict on the owner and correct from the server.

## One flight loop or a module system

This axis is about how the tick is organised, not how it is integrated.

- One loop (SIB, RFFS, MH6, LM_Planes): one large method (`Simulate()`, `FlightSimulation()`, `ApplyHelicopterPhysics()`) computes the whole aircraft with hard-coded constants and applies one result at the end, `SetVelocity` or one `dBodyApplyForce` and `dBodyApplyTorque`.
- Modules (Expansion): each aerofoil, the rotor, each wheel and engine computes its own force at its own position and adds it to `ExpansionPhysicsState` (`pState.m_Torque += position * force`, [Expansion `ExpansionVehicleAerofoil.c:229` to `:230`]); the sum is applied once ([Expansion `ExpansionPhysicsState.c:216` to `:217`]).

| Modules win | One loop wins |
|---|---|
| A new aircraft is a config block and a thin subclass; one base flies the Gyrocopter, Merlin and MH-6 ([Expansion `ExpansionGyrocopter.c:25`, `:256`]) | Using the aerofoil means taking the whole scaffold: Expansion's `CarScript.c` alone is 3,815 lines and the rotor module 3,234. MH6 is a complete force-based helicopter in one script of about 48 KB |
| Moments come from geometry: torque is position times force, so a tail rudder yaws because it is at the tail ([Expansion `ExpansionVehicleAerofoil.c:230`]); the others fake the lever arm with constants | One method reads top to bottom; a module force has to be traced from config through two hooks and the accumulator |
| Stall, air density, ground effect, translational lift, vortex ring state, blade stall and autorotation come from one model, where SIB fakes lift with a constant +0.25 m/s and a 1,500 m ceiling | A wrong memory point name for an aerofoil's `min` or `max` gives a wrong area and a subtly wrong aircraft with no error ([Expansion `ExpansionVehicleAerofoil.c:80` to `:111`]); a constant cannot be mis-wired |
| One core serves car, boat, plane and helicopter; the helicopter reuses the aerofoil unchanged | Real lift, drag, stall and rotor effects make the aircraft twitchy and spinnable, good for a sim and worse for casual servers |
| Each module has a `CF_OnDebugUpdate` window showing angle of attack and coefficients live ([Expansion `ExpansionVehicleAerofoil.c:137` to `:149`]) | Many modules doing trigonometry and a matrix multiply every tick cost more than one inlined loop; one `thrust_rate` knob (RFFS's percent-of-baseline JSON) is easier to tune than lift coefficients and blade pitch |

Expansion does not model each blade as an aerofoil, which would be far too costly. The rotor is its own module, sampling blade elements over 8 azimuth sectors ([Expansion `ExpansionVehicleHelicopter.c:2300` to `:2320`]). The aerofoil system is strongest on fixed wings and control surfaces; a helicopter is the rotor module plus body aerofoils.

## Kinematic or force-based

Kinematic flight sets the velocity directly with `SetVelocity` (`P:\scripts\1_core\proto\enphysics.c:111`); force-based flight applies `dBodyApplyForce` and `dBodyApplyTorque` (`:146`, `:153`) and lets the body integrate.

| Model | Integration | Source | Use it as |
|---|---|---|---|
| SIB simple | Kinematic: `SetVelocity`, `SetOrientation`, `dBodyApplyImpulse` commented out | Readable | The simplest loop to learn from |
| SIB advanced | Force: `dBodyApplyForce` and `dBodyApplyTorque` in an obfuscated applicator | DRM-locked, core integrator missing | Proof force was used; cannot be built |
| RFFS | Kinematic: `SetVelocity`, `SetOrientation`; `dBodyApplyImpulse` only commented out ([RFFS `Core.c:272`]) | Clean, complete, no DRM | The kinematic reference: lift vector rotated with attitude, ground effect, translational lift, governors, drag, weathervaning, 0 to 20 collective, typed JSON, flight HUD |
| MH6 | Force every tick ([MH6 `MH6_flightmodel.c:1165` to `:1166`]) | Readable, complete | The force reference: PD controller, ISA density, rotor speed gating, auto hover and auto land |
| LM_Planes | Force: lift, drag and stall summed and applied; thrust at `axis_thruster` | Clean, public Workshop | The fixed-wing reference |

A buildable helicopter can be either; that SIB's force model is locked is a property of that mod, not of DayZ.

## How they differ

| | RFFS | SIB | MH6 | LM_Planes |
|---|---|---|---|---|
| Aircraft | Helicopter | Helicopter | Helicopter | Fixed wing, plus one amphibious car |
| Flight model | Lift vector rotated with attitude, ground effect, translational lift, speed and climb governors, drag, weathervaning | Pitch to forward speed, bank to yaw, passive +0.25 m/s hover | PD controller, rotor speed gating, density, translational lift, ground effect, quadratic drag, overspeed and climb limits | Lift, drag, stall, ISA atmosphere, PID auto-stabilisation, NaN-safe forces |
| Collective | Discrete 0 to 20 steps times `c_thrust_rate` | `m_rotorTurn` plus or minus 2.8 while held, plus a passive baseline | Analog 0 to 1 into lift `mass * g * 1.65 * collective * rotorSpeed² * density` | Throttle smoothed through the Pawn move |
| Stability | Recovery mode that levels to the velocity | Attitude recentre | P from memory-point tilt, D from angular rate | PID |
| Assists | None | Auto hover, only in the locked variant | Auto hover as a hold loop; auto land as a kinematic state machine | None |
| Config | Typed JSON (`MasterConfig`, `HeliConfig`, percent of baseline) | Positional `map<string,float>` from `$profile` JSON | Constant literals ([MH6 `:141` to `:176`]) | About 60 `Get*` methods per aircraft |
| Replication | Sync variables plus an `EOnFrame` client pump for animation and input | Sync variables plus an `EOnSimulate` mirror | Pawn owner state and move, plus two sync variables for toggles | Pawn owner state and move |
| Atmosphere | Fixed ceiling clamp | Hard 1,500 m literal | ISA `StandardAtmosphere` | ISA |
| HUD | Full flight HUD | Config dials | Unknown | Cockpit dials |
| Openness | Open | Licence check over HTTP to the mod's server | Readable, no live DRM in the flight script | Open |

## Which to build from

1. One custom helicopter, flying soon, code you can read end to end: a single loop. For predictable handling build from RFFS (kinematic, no momentum surprises, the helicopter goes where the model says each tick). For real momentum, inertia, PD stability and auto hover build from MH6 (it carries its velocity, swings under the rotor and needs anticipation; more alive, more to tune).
2. Several aircraft on realistic physics tuned by config: Expansion. You pay its architecture and a steeper tuning curve, and get data-driven aircraft, moments from geometry and the most complete rotor model.
3. Fixed wing with real aerodynamics: LM_Planes, or Expansion, where the aerofoil system is strongest.
4. Not SIB: its simple model is a minimal hack and its force model is locked with the core missing. Use it only as a third data point; it confirms the `CarScript` route, baked blur rotors and per-component damage, and its config bitfield sync idea is worth a look.

## How players say each feels

| Mod | Feel | Likely cause in the code |
|---|---|---|
| RFFS | Strongest stabilisation, most arcade, easiest to fly | The heaviest assists on a kinematic base: governors, trainer clamps, `UARFFSRecover` auto level. Forgiving but on rails |
| SIB | Most fluid | Continuous collective against RFFS's steps, a weak 0.1 per tick recentre, direct `SetVelocity` with no governors. Nothing fights the stick; less forgiving |
| MH6 | Neither fluid nor good at recovering | Momentum removes the direct feel, and the PD stabiliser (`PITCH_STABILITY 0.85`) and auto land are not tuned strong enough to give RFFS-grade recovery |
| Expansion | Complex | Forces plus real rotor disc aerodynamics and the least hand-holding, the highest skill floor |

Fluidity and recovery pull against each other because both come from stabilisation: strong constant stabilisation (RFFS) recovers but is not fluid, weak (SIB) is fluid but does not recover, and an under-tuned force model (MH6) loses fluidity and gains no recovery. None of the five separates them. What would beat all five is a fluid kinematic base with SIB's direct response plus envelope protection that stays soft in normal flight and firms up only near loss of control, like fly-by-wire normal law. That is a tuning problem, not new physics. Pick by audience, not by strongest stabilisation.

## An older helicopter with attachable blades

`HelicopterSIB_Hommade_LF`, a reskin of `HelicopterModhommade`, appears to use a `CarScript`-derived base (inferred, not read) with attachable rotor blades (`hommade_blade1`, `hommade_blade2`, tail `hommade_bladem1`, `hommade_bladem2`) and sound hooks `c_rotorSound`, `c_engineSound`, `c_warningSound`, `c_crashSound`. Its flight model lives in a base addon that was not available, and its own PBO holds one `.c` file of 1,177 bytes (`helicopter-mod-sources.md`). The SIB mod in `helicopter-sib.md` is the documented pattern instead.
