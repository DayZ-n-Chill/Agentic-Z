# Expansion helicopters

How the Expansion vehicle framework flies helicopters and planes: a `CarScript` entity hosting physics modules, one force and torque accumulator, an aerofoil module set up from config, and a rotor module that models the rotor disc. Open it when a task targets Expansion aircraft or weighs a module system against a single flight loop.

Everything here describes Expansion's own vehicle scripts, which are not in this repo and not vanilla; citations are `file:line` into those scripts. `ExpansionVehicleHelicopter.c` is the rotor module, `CarScript.c` is Expansion's `modded class CarScript`, `ExpansionHelicopterScript.c` is the helicopter entity; other files are named in full. The scripts are not obfuscated: read them for the pattern and write your own code. Which flight model to build from is in `helicopters.md`, and the comparison with the other helicopter mods in `helicopter-model-comparison.md`.

Unlike the other helicopter mods, which each bolt one hand-written flight method onto one airframe, Expansion is a module system. The airframe is built from modules (wheels, axles, engines, gearboxes, aerofoils and, for helicopters, a rotor), each computes its own force at its own position every tick and adds it to a shared accumulator, and the total is applied once. One core serves cars, boats, planes and helicopters.

## The layers

| Layer | Role | Source |
|---|---|---|
| Expansion's `modded class CarScript` | Hosts the modules: `m_Modules`, `m_Aerofoils`, `m_Wheels`, `m_Axles`, `m_Engines`, `m_Gearboxes`, the `m_State` accumulator, the `m_Event_*` dispatchers, and `EOnSimulate` | `CarScript.c:19`, `:28`; `EOnSimulate` `:2282` to `:2447` |
| `ExpansionHelicopterScript : CarScript` | The helicopter entity: owns `ExpansionVehicleHelicopter m_Simulation`, tuning values, auto hover and landing state, warning sounds, wreck class | `ExpansionHelicopterScript.c:17` to `:19` |
| `ExpansionVehicleHelicopter : ExpansionVehicleModule` | The rotor module: collective, cyclic and anti-torque to thrust and torque; one module, not an aerofoil per blade | `ExpansionVehicleHelicopter.c:223` |
| `ExpansionGyrocopter`, `ExpansionBigGyrocopter` | Concrete aircraft, config and a thin subclass on the shared base | `ExpansionGyrocopter.c:25`, `:256` |

Network replication uses the Pawn classes (client prediction with server correction): `ExpansionHelicopterScriptMove : CarScriptMove` and `ExpansionHelicopterScriptOwnerState : CarScriptOwnerState` carry `m_RotorSpeed`, `m_Collective`, `m_AntiTorque`, `m_CyclicForward`, `m_CyclicSide` and their targets (`ExpansionVehicleHelicopter.c:3` to `:110`).

Expansion's current vehicle classes are `CarScript` children, `ExpansionHelicopterScript` and `ExpansionBoatScript` (`DayZExpansion/Vehicles/Scripts/4_World/DayZExpansion_Vehicles/Entities/Vehicles/expansionhelicopterscript.c:17`, `expansionboatscript.c:16`). An older stack inherited `Transport` directly, `ExpansionVehicleBase : ExpansionVehicleBaseBase : Transport` with its own `m_Controller`, `m_State` (an `ExpansionPhysicsStateT<ExpansionVehicleBase>`) and `m_ExpansionVehicle` (`ExpansionVehicleBase.c:13`, `:19` to `:28`; `ExpansionVehicleBase_Towing.c:1`), and the module constructor still accepts either base (`ExpansionVehicleModule.c:36` to `:42`). Today `ExpansionVehicleBase` is only a stub under `OBSOLETE/` that derives from `Transport`, kept so other mods that name the type still compile; its methods are marked obsolete and return empty values (`.../Entities/Vehicles/OBSOLETE/ExpansionVehicleBase.c:1` to `:12`). Write new code against the `CarScript` classes.

## The tick

`EOnSimulate` runs on the physics host: `m_IsPhysicsHost = IsOwner()` on a client, always true on the server (`CarScript.c:2300` to `:2344`). When active (`:2403` to `:2418`):

```c
m_State.SetupSimulation(dt);              // transform, mass, velocities; zero force and torque
m_State.CalculateAltitudeLimiter();       // lift falls off with altitude, a soft ceiling
m_Event_PreSimulate.PreSimulate(m_State); // each module computes its coefficients
OnSimulation(m_State);                    // per-entity hook; the helicopter runs its rotor module
m_Event_Simulate.Simulate(m_State);       // each module adds force and torque
m_State.ApplySimulation_CarScript(dt, ...);
```

The dispatchers walk a linked list of modules and call `PreSimulate`, `Simulate`, `Control`, `PostSimulate` or `Animate` on each (`ExpansionVehicleModuleEvent.c:83` to `:125`). The base module's hooks are empty overridables (`ExpansionVehicleModule.c:94` to `:112`), plus the Pawn hooks `ObtainMove`, `ConsumeMove`, `ReplayMove`, `ObtainState`, `RewindState` (`:70` to `:89`).

`ExpansionPhysicsState` is the shared sink:

- `SetupSimulation` caches the transform, the mass from `dBodyGetMass`, and world and model space velocities and accelerations, then zeroes `m_Force` and `m_Torque` (`ExpansionPhysicsState.c:178` to `:207`, zeroing at `:188` and `:189`).
- `GetModelVelocityAt(relPos)` returns `m_LinearVelocityMS + m_AngularVelocityMS * relPos`, the local airflow at a module's position (`:473` to `:475`).
- `ApplySimulation` commits the tick with `dBodyApplyForce` and `dBodyApplyTorque` (`:209` to `:217`).

Those are vanilla engine calls (`dBodyGetMass` at `P:\scripts\1_core\proto\enphysics.c:122`, `dBodyApplyForce` at `:146`, `dBodyApplyTorque` at `:153`), so the whole fleet flies on forces, unlike RFFS's kinematic `SetVelocity`. The `dBodyApplyForce` at `CarScript.c:883` is unrelated: it is the push when a vehicle explodes.

## The aerofoil module

`ExpansionVehicleAerofoil : ExpansionVehicleModule` (`ExpansionVehicleAerofoil.c:17`) is a self-contained lifting surface that sets itself up from config, with no code per aircraft. Its constructor reads `CfgVehicles <vehicle> SimulationModule Aerofoils <name>` (`:50` to `:135`):

| Key | Meaning |
|---|---|
| `type` | `Fixed`, `Wing`, `Rudder` or `Elevator`, as text or number (`:59` to `:73`) |
| `up` | The surface's up vector (`:77`, `:78`) |
| `min`, `max` | Memory point names; the area is the extent between them projected across `up`, and the position is their midpoint (`:80` to `:111`) |
| `camber`, `maxControlAngle`, `stallAngle`, `animation` | Shape, control travel, stall, and an optional animation (`:113` to `:124`) |

The surface's size and position come from the model's memory points, not from constants.

`PreSimulate` (`:152` to `:203`):

- Airflow is `-GetModelVelocityAt(m_Position)`, normalised, with its speed squared kept (`:154` to `:156`).
- The control input follows `type`: a rudder takes `-m_Controller.m_Yaw`, an elevator `m_Controller.m_Pitch`, a wing plus or minus `m_Controller.m_Roll` by which side it sits on (`m_Position[0] < 0`). One class becomes aileron, elevator or rudder by config alone (`:158` to `:178`).
- Angle of attack is `Asin(dot(m_Up, airflow)) * RAD2DEG` (`:183`).
- Dynamic pressure is `area * 0.5 * Expansion_GetDensity(altitude) * v²` (`:187`). The body of `Expansion_GetDensity` is outside the scripts read.
- Lift coefficient `sin(liftAngle * π/2 / stallAngle) * 2`, forced to 0 beyond twice the stall angle (`:191` to `:193`).
- Drag coefficient `0.05 + ((dragAngle + angle) / (stallAngle + |angle|))²` (`:195` to `:202`).

`Simulate` (`:205` to `:231`) adds lift along `up` plus drag along the airflow, scaled by the time step, to the world force, and adds `position * force` to the world torque (`:230`). Pitch, roll and yaw moments come from where the surface sits: a rudder at the tail yaws because it is at the tail, with no hand-tuned lever arm. `Animate` (`:233` to `:236`) drives the control surface animation from the input. `ExpansionVehicleHelicopterAerofoil` is an empty subclass (`ExpansionVehicleHelicopterAerofoil.c:1` to `:5`); helicopters reuse the fixed-wing aerofoil for any lifting body surface.

## The rotor module

The rotor is one module of 3,234 lines, not an aerofoil per blade. The parts below were read line by line: the control integration (`:1655` to `:1743`), the anti-torque and tail rotor (`:1900` to `:1960`), the legacy thrust (`:1800` to `:1816`) and the rotor disc thrust core (`:2237` to `:2320`).

- Two modes, chosen by `m_SimulationMode` (default `RotorDisk`): `Simulate_RotorDisk` (`:2237` on) and a `Simulate_Legacy` compiled only under `DIAG_DEVELOPER` (`:1746` on), dispatched at `:1722` to `:1735`, followed by the shared `Simulate_Common` (`:1819` on). The result is added to the accumulator at the end of `Simulate` (`:1742`, `:1743`).
- Controls (`:66` to `:72`, `:301` to `:333`): `m_Collective`, `m_AntiTorque`, `m_CyclicForward` and `m_CyclicSide`, each with a target from `m_Controller`, rate limits, trims, and authority from hydraulic fluid (`CarFluid.OIL`, `:1693`). Collective response scales with rotor speed squared (`m_CollectiveDelta = (target - current) * m_RotorSpeed²`, `:1676`), and cyclic moves only when `m_RotorSpeed != 0` (`:1705` to `:1711`): no control without rotor speed.
- Thrust in the rotor disc model (`:2237` to `:2320`): hover induced velocity from momentum theory, `viHover = sqrt(mass * g / (2 * ρ * π * r²))` (`:2265` to `:2267`); advance ratio `mu = horizontalSpeed / omegaR` (`:2246` to `:2250`); blade elements sampled in 8 azimuth sectors (`:2300` to `:2320`); translational lift by iterating induced velocity (`:2275` to `:2280`); ground effect (`:2252` to `:2263`); vortex ring state thrust loss through `ComputeVRSSeverity` (`:2287` to `:2292`); retreating blade stall above `mu = 0.35` (`:2313` to `:2318`); altitude through `m_AltitudeLimiter` (`:2305`). Thrust acts up the body axis and cyclic tilts the disc. The legacy model is coarser: thrust proportional to collective, rotor speed squared, a lift coefficient, mass and a lift factor (`:1806` to `:1815`).
- Tail rotor (`:1932` to `:1960`): force `m_AntiTorque * m_TailForceCoef * m_RotorSpeed²`, minus the main rotor reaction torque it must cancel (`m_MainRotorTorque * m_RotorSpeed² * torqueSpeedFactor`, `:1957` to `:1959`). With `m_TranslatingTendencyCoef == 0` (tandem or coaxial, no tail rotor) the cancellation is skipped (`:1947` to `:1949`). Tail rotor damage adds a malfunction torque, the classic spin (`:1934` to `:1944`).
- Autorotation (`:1662` to `:1667`): descending with the rotor off (`goingDown > 0 && m_RotorSpeedTarget < 0.1`), rotor speed is driven up by the falling air, `change = (min(goingDown, 1) - m_RotorSpeed) * 0.08 * pDt`.
- Translating tendency (`:1823` to `:1830`): the sideways drift a tail rotor causes in a hover (to the right for a counterclockwise main rotor), full in a hover and gone by translational lift.

This is the most complete rotor model of the helicopter mods examined: it models the disc (induced velocity, blade elements, vortex ring state, retreating blade stall, translational lift, ground effect, autorotation) rather than one lumped lift force. The cost is size and coupling.

## One base, many aircraft

`ExpansionGyrocopter` and `ExpansionBigGyrocopter` are almost pure config on the shared base. Comments mention more helicopters on the same base, a Merlin and an MH-6 (big helicopter ground clipping at `ExpansionVehicleHelicopter.c:2433`, rocket damage thresholds at `ExpansionHelicopterScript.c:450`), and `REFERENCE_MASS = 1700 //! MH6` (`ExpansionVehicleHelicopter.c:228`) shows the model is tuned against an MH-6-class reference and scaled per airframe by mass and bounding radius. A new aircraft is a config and a subclass, not a new flight loop.

## Not read

Do not fill these in from guesses:

- The rest of `ExpansionVehicleHelicopter.c`: the azimuth loop past `:2320`, the full torque assembly in `Simulate_Common`, auto hover (around `:1440` to `:1600`), auto trim, the vortex ring and blade stall coefficient derivations, the rotor collision callback class `ExpansionHelicopterScriptRotor` (`:117`) and networking.
- The body of `Expansion_GetDensity`.
- The `config.cpp` `SimulationModule` blocks and the `.p3d` and `model.cfg` data; only the config paths and memory point names the script reads are known.
- The concrete classes of the Merlin, MH-6 and UH-1H.
