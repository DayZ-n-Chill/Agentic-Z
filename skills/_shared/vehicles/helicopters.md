# Helicopters

What vanilla gives you for helicopters, what it does not, and how to build a flyable one on the native base classes with your own code. The later sections cover the second route, `CarScript` as the base, which every shipped community helicopter read for this pack takes, and which of their flight models to learn from.

## What vanilla ships

Vanilla has the classes but no flyable helicopter. No vanilla `CfgVehicles` class uses `HelicopterScript`, and no vanilla script class extends it (Grep `P:\DZ` and `P:\scripts` for `HelicopterScript`).

| Layer | Class | Where | What it has |
|---|---|---|---|
| Native script | `Helicopter extends Transport` | `P:\scripts\3_game\vehicles\helicopter.c:9` | Nothing beyond `Transport`. |
| Native script | `HelicopterAuto extends Helicopter` | `helicopter.c:14` | Auto hover helicopter: `IsEngineOn()`, `EngineStart()`, `EngineStop()`, `IsAutohoverOn()`, `AutohoverOn()`, `AutohoverOff()` (`:17` to `:32`). |
| Script | `HelicopterScript extends HelicopterAuto` | `P:\scripts\4_world\entities\vehicles\helicopterscript.c:4` | Sets the `POSTSIMULATE` event mask; empty `EOnPostSimulate`, `OnBeforeEngineStart` (server only, returns `true`), `OnEngineStart`, `OnEngineStop` (`:6` to `:34`). |
| Native config | `Helicopter: Air` | `P:\bin\config.cpp:1563` | `simulation="helicopter"` (`:1568`), pilot view limits in `ViewPilot`, rotor selections and speeds, `class RotorLibHelicopterProperties` (`:1673`). |
| Native config | `Air: Transport` | `P:\bin\config.cpp:1507` | `fuelCapacity=1000`, `maxSpeed=400`, marker lights. |

`P:\bin\config.cpp` has no config class named `HelicopterAuto`. The `Helicopter` config class carries old rotor selection names from earlier engines (`selectionHRotorStill="velka vrtule staticka"`, `:1609`), so redeclare every selection and memory point your model uses rather than relying on the inherited ones.

## What is missing, and who writes it

Everything a player needs beyond auto hover is yours to write in the mod's own code. Never copy it from another mod.

| Need | Where it comes from |
|---|---|
| Seats and get in | `class Crew` in config as for cars (`attachments-and-crew.md`), plus `GetAnimInstance`, `GetSeatAnimationType`, `CrewCanGetThrough` and `CanReachSeatFromDoors` overrides. `Transport` errors or returns `false` without them (`class-hierarchy.md`). `VehicleAnimInstances` has no helicopter entry (`P:\scripts\4_world\entities\vehicles\vehicleaniminstances.c:1`); reuse an existing one. |
| Camera | `Get3rdPersonCameraType()` errors in `Transport` (`P:\scripts\3_game\vehicles\transport.c:698`) and `HelicopterScript` does not override it. Return `DayZPlayerCameras.DAYZCAMERA_3RD_VEHICLE` as `CarScript` does (`carscript.c:2232`). |
| Engine rules | Override `OnBeforeEngineStart` for fuel, battery or parts checks. `HelicopterScript` has no fluid or part logic. |
| Flight input | Script calls `AutohoverOn()` and `AutohoverOff()`; any control beyond the native simulation is new script, which goes to dayz-script-specialist through the config lead. |
| Actions | `HelicopterScript` registers no actions. Add get in and get out the way `CarScript.SetActions` does (`carscript.c:2313`). |
| Damage | A `DamageSystem` written fresh; none of the `CarScript` zone logic applies. |

## Starting point

```cpp
// config.cpp
class CfgVehicles
{
    class Helicopter;
    class MyMod_Heli: Helicopter
    {
        scope = 2;
        displayName = "MyMod helicopter";
        model = "\MyMod\data\heli.p3d";
    };
};
```

```c
// scripts/4_World/MyMod/Vehicles/MyMod_Heli.c
class MyMod_Heli extends HelicopterScript
{
    override int GetAnimInstance()
    {
        return VehicleAnimInstances.HATCHBACK;
    }

    override int GetSeatAnimationType(int posIdx)
    {
        if (posIdx == 0)
            return DayZPlayerConstants.VEHICLESEAT_DRIVER;

        return DayZPlayerConstants.VEHICLESEAT_CODRIVER;
    }

    override int Get3rdPersonCameraType()
    {
        return DayZPlayerCameras.DAYZCAMERA_3RD_VEHICLE;
    }
}
```

Unverified until tested in game: that the `helicopter` simulation on this config parent creates a `HelicopterAuto` native object, which `requiredAddons[]` entry the native `Helicopter` class needs (it lives in the engine's own `P:\bin\config.cpp`, not in a `DZ_` addon), and how the native hover handles mass and rotor values. Report these as unverified to the config lead and have the in-game test spawn, enter, start and hover the helicopter before calling it done.

## The second route: CarScript as the base

The native route above is unproven in game. The script side of it is empty in 1.29 and in 1.30: the `HelicopterScript` constructor sets only the `POSTSIMULATE` mask (`P:\scripts\4_world\entities\vehicles\helicopterscript.c:8`) and its `EOnPostSimulate` and engine hooks have no body, so whatever flies would have to come from the native `helicopter` simulation, which nothing in vanilla exercises.

Every shipped community helicopter read for this pack takes another route: it inherits `CarScript` (config parent `class CarScript: Car`, `P:\DZ\vehicles\wheeled\config.cpp:236`), keeps a complete ground `SimulationModule` with wheels, axles and a gearbox as the taxi fallback, and flies entirely in script. Planes do the same. The facts in the rest of this file come from those mods' own sources and from the LFHeli project's in-game tests; they are third-party and not checked on `P:\`.

| | Native classes (sections above) | `CarScript` as the base |
|---|---|---|
| Proven by | Nothing shipped; the unverified list above | RFFS, MH6, SIB, DayZ Expansion, and LM_Planes for planes |
| Flight code | The native `helicopter` simulation plus `AutohoverOn()` and `AutohoverOff()` | All of it in the mod's script, on top of a car body |
| Seats, fluids, damage, engine sound | Written fresh | Inherited from `CarScript` |
| Config cost | Rotor and `RotorLibHelicopterProperties` keys | A full car `SimulationModule` that only matters on the ground |
| Traps | Unknown until tested | Known and listed in `aviation-carscript-base.md` |

Pick one base and stay on it. Do not move a flying `CarScript` child onto `HelicopterScript` expecting a flight model, and do not copy another mod's code on either route: the mods below are patterns to learn from.

## Shipped flight models

| Mod | Class chain | Integration | Replication | Tuning store | Use it as |
|---|---|---|---|---|---|
| RFFS (RedFalcon) | `RFFSHeli_S76 : RFFSHeli_base : CarScript` | Kinematic: `SetVelocity` and `SetOrientation` | Net sync variables, solver on the server only | Typed JSON: a server wide `MasterConfig` and a `HeliConfig` per model, loaded with `JsonFileLoader<T>`, values as percentages of a baseline | The kinematic reference: not obfuscated, complete, physically grounded |
| MH6 (Llama) | `MH6 : CarScript` | Forces: `dBodyApplyForce` and `dBodyApplyTorque` every tick | Custom Pawn state and move with owner prediction | Constants in the class | The force based reference: a PD flight controller in one legible script |
| SIB (SIBNIC) | `HeliTest_SIB : Heli_sib_cript : CarScript` | Kinematic (simple model); forces in an advanced model that is licence locked and incomplete | Net sync variables, solver on the server only | A positional `map<string,float>` read from a `$profile` JSON | A corroborating example only; do not build from it |
| DayZ Expansion | `ExpansionHelicopterScript : CarScript` plus a rotor module | Forces, summed by a module system and committed once | Custom Pawn state and move | Config driven modules (`SimulationModule` aerofoils, rotor) | The framework reference: many aircraft on one data driven core |

What all four share:

- **Custom `UA*` inputs** drive the flight (`UARFFS*`, `UAKTHeli*`, `UASIBHeli*`), declared in a modded inputs file. The traps are in `aviation-inputs-and-actions.md`.
- **Rotors are baked geometry with a static mesh and a blur mesh**, swapped and spun with `SetAnimationPhase` according to rotor state and rotor health, not attachable items and not bound to engine RPM. RFFS uses `rotorN_speed` and `rotorN_blur_hide`, SIB `rot_h_start` and `rot_h_blur_end`, MH6 `rotor_1_1` with `rotor_1_1_hide` and `rotor_1_1_rotate_hide` swapped at 70 percent rotor speed. (One older community helicopter used attachable blades instead; it is described at the end of the comparison reference.)
- **Damage zones per component** with transfer coefficients between them and part health tied to attachments: RFFS has `Chassis`, `Avionics`, `Engine`, `Hydraulics`, `FuelTank`, `MainRotor` and `TailRotor`; SIB has `Body`, `Chassis`, `Engine`, `Fuel`, `Rotor1`, `Rotor2` and `Proj`. A damaged tail rotor injecting yaw and a damaged engine or main rotor cutting lift are the usual couplings.
- **The server is the authority.** The solver runs behind `IsServer()` or `IsServerOrOwner()`; a client never owns the authoritative velocity (`aviation-networking.md`).
- **Engine start is an action.** RFFS and SIB add their own start and stop actions; MH6 keeps the vanilla ones and gates on `EngineIsOn()`.

## Kinematic or force based

Both are buildable from legible sources. An earlier reading, based only on SIB's locked advanced model, held that a buildable helicopter had to be kinematic; MH6 disproves it.

- **Kinematic** (RFFS, SIB simple): the script computes a velocity and an orientation each tick and sets them. No momentum carries over that the model did not put there, so the helicopter goes where the model says. RFFS shows how far this goes: a discrete collective with 21 positions, lift rotated into the world by the airframe's own attitude, ground effect, translational lift, speed and climb governors, drag and weathervaning.
- **Force based** (MH6, Expansion): the script applies forces and torques and the body integrates them. Real momentum and inertia, at the price of more tuning. MH6 gates each control channel on rotor speed, scales lift with air density, and stabilises with a proportional term on tilt plus a derivative term on angular rate. Expansion models the rotor disc itself, with autorotation, vortex ring state and retreating blade stall.

A separate choice is one flight loop against a module system. RFFS, MH6 and SIB each compute the whole aircraft in one method; Expansion sums forces from config driven modules placed at their real positions, so control moments come from geometry instead of tuned lever arms, at the cost of a large framework and of config mistakes that fail without an error.

## Which one to build from

1. **One helicopter, flying soon, arcade feel, code readable end to end:** one flight loop. Take RFFS as the pattern for predictable kinematic handling, or MH6 for momentum, PD stability and auto hover.
2. **A fleet with realistic physics tuned from config:** the Expansion module pattern (aerofoils plus a rotor disc model), accepting its architecture and a steeper tuning curve.
3. **Fixed-wing with real aerodynamics:** LM_Planes (one loop, custom Pawn) or Expansion aerofoils.
4. **Not SIB.** Its simple model is a minimal kinematic hack (a constant 0.25 m/s lift term and a hard 1500 m ceiling) and its force model is licence locked with the core integrator missing.

Players who flew these on a live server (secondhand opinion, not a measurement) called RFFS the easiest and most stabilised, SIB the most fluid, MH6 neither fluid nor easy to recover, and Expansion complex. Fluidity and recoverability both come from the stabiliser and pull against each other; none of the four separates them. Pick for the audience, not for "strongest".

## Where the depth is

The per-mod breakdowns live in the `dayz-aviation` skill's `references/` folder; open only the one the task needs.

| Need | File in `skills/dayz-aviation/references/` |
|---|---|
| The RFFS integrator, config framework, damage zones, actions and HUD | `helicopter-rffs.md` |
| The MH6 force model, Pawn replication, auto hover and auto land | `helicopter-mh6.md` |
| The SIB simple model, its JSON store, and what was not recovered | `helicopter-sib.md` |
| The Expansion module system, aerofoil and rotor module | `helicopter-expansion.md` |
| The five way comparison, trade-offs and player feel in full | `helicopter-model-comparison.md` |
| Which Workshop PBO holds readable flight scripts | `mod-sources.md` |
| Testing a flight model in game and reading the logs | `flight-testing-and-measurement.md` |
