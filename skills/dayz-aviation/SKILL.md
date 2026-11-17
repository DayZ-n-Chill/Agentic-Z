---
name: dayz-aviation
description: "Reference for building planes, seaplanes and helicopters in DayZ on a CarScript base: flight physics in script (lift, drag, stall, atmosphere, NaN guards), kinematic and force based helicopter models, Pawn prediction, custom flight inputs, rotor, propeller and control surface animation, cockpit dials, buoyancy, retractable gear, sounds, lights, weapons and flight testing. Use before writing or debugging an aircraft's config or script, or when a task names a helicopter, plane, aircraft, flight model, rotor, propeller, elevator, aileron, rudder, throttle, collective, cyclic, autopilot, auto hover, seaplane or flying boat, axis_thruster, dial_horizon or dial_altitude, stall warning, Cessna, Spitfire, Catalina, Tigermoth or biplane, or the RFFS, MH6, SIB, LM_Planes or Expansion helicopter mods."
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# DayZ aviation

Follow `skills/_shared/dayz-conventions.md`. This skill is reference only; it runs no scripts, so there is no preflight gate. Writing config, `model.cfg` or flight scripts needs nothing mounted. Packing and testing go through `/dayz-build-pbo` and `/dayz-launch-test`, which gate on `/dayz-preflight`.

The `dayz-vehicle-specialist` agent owns aircraft classes and reads this skill with the vehicle pack.

## The pattern

Vanilla ships no flyable aircraft. The native helicopter classes exist but hold no flight code in script, and there is no fixed-wing class. Every shipped community aircraft read for this skill inherits `CarScript`, keeps a full ground `SimulationModule` as the taxi fallback, and flies in script: LM_Planes for planes and seaplanes, and RFFS, MH6, SIB and DayZ Expansion for helicopters. Those mods are patterns to learn from. Write the aircraft's own code and never copy theirs.

Two kinds of fact sit side by side, and each file says which is which:

- **Vanilla facts** cite the file on `P:\` as `path:line` and were opened there.
- **Third-party facts** name the mod they were read from, or the LFHeli helicopter project they were measured in, and are not checked on `P:\`. Treat them as leads to confirm in game.

## Before the first boot

Each line is a fault that compiles clean and fails silently. The file named holds the evidence and the fix.

| Check | Where |
|---|---|
| A flight loop in `EOnSimulate` has `SetEventMask(EntityEvent.SIMULATE)` in the constructor; `CarScript` registers only `POSTSIMULATE` and `POSTFRAME` | `skills/_shared/vehicles/aviation-carscript-base.md` |
| Nothing is pumped from `EOnFrame` with a hardcoded dt | `skills/_shared/vehicles/aviation-carscript-base.md` |
| A kinematic solver adds gravity back each tick, zeroes angular velocity after `SetOrientation`, and the test airframe has no wheels | `skills/_shared/vehicles/aviation-carscript-base.md` |
| The body is kept awake while flown, and is never put to sleep in the tick of `EEInit` | `skills/_shared/vehicles/aviation-carscript-base.md` |
| A fixed direct gear does not stop the engine when the pilot gets out (`OnDriverExit`) | `skills/_shared/vehicles/aviation-carscript-base.md` |
| Every custom `UA*` name matches across `inputs.xml`, the script read and the stringtable | `skills/_shared/vehicles/aviation-inputs-and-actions.md` |
| The driver's client primes each custom action with `SyncedValue` every tick when the server reads it | `skills/_shared/vehicles/aviation-inputs-and-actions.md` |
| `GetNetworkMoveStrategy()` was probed on the client before the network model was chosen | `skills/_shared/vehicles/aviation-networking.md` |
| No smoothing filter sits on the pilot's own camera | `skills/_shared/vehicles/aviation-networking.md` |
| Lights and battery follow the 1.30 vehicle contract | `references/dayz-1-30-aviation.md` |
| The entity base is not `HelicopterScript` for a helicopter that flies on `CarScript` | `skills/_shared/vehicles/helicopters.md` |

## What to read

Open only the file the task needs. Pack files are under `skills/_shared/vehicles/`; references are under this skill's `references/` folder.

| Question | File |
|---|---|
| Which base class for a helicopter, which shipped flight model to learn from, kinematic or force based | `skills/_shared/vehicles/helicopters.md` |
| Which entity events fire on a `CarScript` aircraft, what the car body does to `SetVelocity`, angular velocity axes, sleeping the body, what stops the engine | `skills/_shared/vehicles/aviation-carscript-base.md` |
| Owner prediction with the Pawn classes, `ForceCorrection`, when ownership changes hands, camera smoothing | `skills/_shared/vehicles/aviation-networking.md` |
| Custom inputs that read zero in the seat, deadzones, continuous actions in a seat, input excludes for a sight or camera | `skills/_shared/vehicles/aviation-inputs-and-actions.md` |
| A fixed-wing mod's layout: config skeleton, `requiredAddons`, sub-mods, the base script class, ground and air modes, memory points, bones, the dashboard material toggle | `references/fixed-wing-lm-planes.md` |
| Lift, drag and stall, the ISA atmosphere, PID self levelling, NaN guards, seaplane `Buoyancy` and water physics, presets per aircraft size | `references/aerodynamics-and-flight-physics.md` |
| Control surface, dial and damper `AnimationSources`, `model.cfg` animation classes, the propeller spin hack, aircraft damage zones, which seat animation set to reuse | `references/animation-and-modelcfg.md` |
| The LM_Planes `Inputs.xml`, its keyboard and Xbox scheme, variants in one config | `references/inputs-and-bindings.md` |
| Engine sound shaders and sets, the RPM band crossfade, offload variants, ranges | `references/sounds.md` |
| Navigation lights, headlights before and after 1.30, seaplane water spray | `references/effects-and-lights.md` |
| Weapons on an aircraft: tracer projectile, hitscan, the fire RPC pipeline, damage zone resolution, camera shake | `references/combat.md` |
| What 1.30 changed under a `CarScript` aircraft, line drift, the migration checklist | `references/dayz-1-30-aviation.md` |
| RFFS in depth: the kinematic integrator, typed JSON config, damage zones, actions, HUD, sync | `references/helicopter-rffs.md` |
| MH6 in depth: the PD force controller, Pawn replication, auto hover and auto land | `references/helicopter-mh6.md` |
| SIB in depth: the simple kinematic loop, the JSON store, what was not recovered | `references/helicopter-sib.md` |
| DayZ Expansion in depth: module system, force accumulator, aerofoil and rotor modules | `references/helicopter-expansion.md` |
| All five models compared: one loop or modules, kinematic or forces, differences, player feel | `references/helicopter-model-comparison.md` |
| Which Workshop PBO holds readable flight scripts, and which mods are a dead end | `references/mod-sources.md` |
| Testing a flight model in game: replay and handshake rules, judging a control loop, blind probes, scoring windows across logs | `references/flight-testing-and-measurement.md` |
| A coordinate measured from the `.p3d` lands on the wrong end of the aircraft | `references/model-axes-and-py3d.md` |
| A thermal (FLIR) view for a sight | `references/thermal-imaging.md` |

## Related packs and skills

- The vehicle pack (`skills/_shared/vehicles/README.md`) covers the car side every aircraft still has: `SimulationModule`, crew seats, fluids, damage zones. Packaging faults that pass with file patching and break on a dedicated server (Binarize dropping textures named only in config, `model.cfg` behaving differently for binarized and source models) are ground vehicle topics that apply to aircraft unchanged: `skills/_shared/vehicles/build-packaging-and-debug.md` and `skills/_shared/vehicles/deploy-gates-and-crash-fingerprint.md`. For an amphibious vehicle, the hull and car base belong to the vehicle pack and the buoyancy and flight layer belong here.
- Enforce Script rules: `skills/_shared/enscript-style.md` and the `skills/_shared/enscript/README.md` pack (RPC, net sync, persistence, input bindings).
- Models and materials: `skills/_shared/models/README.md` and `skills/_shared/textures/README.md`; the dayz-model-pipeline skill for the Object Builder workflow.
- Crash and impact particles: the `dayz-particles` skill.
- Building, loading and publishing the finished mod (`config.cpp` and `CfgMods`, `requiredAddons`, the PBO and its signature, a boot on a local server, the Workshop): the dayz-mod-dev skill, used alongside this one.

## On Linux

Everything above is the Windows workflow and stays valid there. The Proton setup, the measured tool matrix and the pitfalls are in the shared Linux and Proton notes (`skills/_shared/linux-proton.md`); this section says only what changes for this skill.

- Pack, sign and binarize with dayzmake 1.0.0 or later, bzed's DayZ fork of armake2 (https://github.com/bzed/dayzmake), pinned to `v1.0.0`: the release binary `dayzmake-v1.0.0-debian-trixie-x86_64.tar.gz` from https://github.com/bzed/dayzmake/releases/tag/v1.0.0, or `cargo install --git https://github.com/bzed/dayzmake --tag v1.0.0`. Use `dayzmake build`, `keygen`, `sign`, and `build --proton-binarize` where needed. Upstream armake2 is no substitute: it is built for Arma, its V3 file hash leaves out `*.c` files (dayzmake v1.0.0 includes them), and it lacks the DayZ only functions dayzmake keeps adding. The shared script `skills/_shared/scripts/dayz-mod-pack.sh` wraps them (`init`, `keygen`, `build [--binarize-models]`, `check`, `publish-hint`). A textured cube packed this way on 2026-11-03 matched Bohemia's Binarize from a `P:` root byte for byte; that is a file comparison, not an in-game check of a binarized model.
- `P:\` is a plain directory mapped by `dayz-proton.sh init <dir>` (the script is `skills/_shared/scripts/dayz-proton.sh`); a `P:\<Mod>\...` path in this skill is `<dir>/<Mod>/...`.
- Object Builder and TexView run under Proton: `dayz-proton.sh gui ObjectBuilder <p3d>` and `gui TexView <paa>`. Object Builder opened and displayed a model; editing in it was not exercised. The offline checks (`scripts/tools/py3d/`, `scripts/tools/dayz-model-preflight/`, `scripts/tools/dayz-3d-viewer/`) are Python and run natively.
- In-game checks: the Linux notes of the dayz-test-ingame skill.

## Do not

- Don't copy code from another mod. Read the references for the pattern and write the aircraft's own classes.
- Don't invent what a reference marks `[UNVERIFIED]`: a `.p3d` memory point set, a `model.cfg` skeleton, input bindings or a config value that was not read from source.
- Don't report a flight behaviour as working from a clean compile. Flight, inputs and replication are only confirmed by a piloted test in game.
