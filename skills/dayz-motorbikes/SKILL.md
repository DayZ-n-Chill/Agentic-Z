---
name: dayz-motorbikes
description: "Reference for building, importing, configuring and debugging motorbikes (single-track vehicles) in DayZ 1.30: MotorbikeScript, simulation = \"motorbike\", the two-wheel SimulationModule (Wheels without Axles, front and rear Brakes, lean, steering, tip-over), kickstand, kickstart and pick-up actions, the motorbike HUD and third-person camera, rider animation, and the 1.30 vehicle script refactor (VehicleLightsComponent, VehicleHornComponent, VehicleVFXComponent). Use when creating a new motorbike, porting a two-wheel model (dirt bike, scooter, sport bike), migrating a vehicle mod from 1.29 to 1.30, or fixing get-in, fall-over, light or repair problems on a bike. Not for cars, trucks, quads or boats (the vehicles pack), aircraft (dayz-aviation), mesh work or custom animation authoring."
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# DayZ motorbikes

Follow `skills/_shared/dayz-conventions.md`. This skill is reference only; it runs no scripts of its own, so there is no preflight gate. The `dayz-vehicle-specialist` agent reads it when it builds a motorbike.

DayZ 1.30 added native single-track vehicles: the engine simulation `simulation = "motorbike"` (`P:\bin\config.cpp:1486`), the native class `Motorbike` (`P:\scripts\3_game\vehicles\motorbike.c:30`) and the script class `MotorbikeScript` (`P:\scripts\4_world\entities\vehicles\motorbikescript.c:53`), with two vanilla bikes, `Motorbike_01` and `Motorbike_02`. A motorbike shares nothing with the four-wheel `CarScript` code path.

Everything here was read in the vanilla 1.30 files on `P:\` unless a line says otherwise. Marks: `[EXACT]` read in the cited vanilla file, `[DESIGN]` a recommendation, `[INFERRED]` a deduction, `[UNVERIFIED]` not confirmed in text or in game. Nothing dynamic is claimed as tested in game unless the line says it was measured in game. Short citations: `config.cpp:N` is `P:\DZ\vehicles\singletrack\config.cpp`, and a bare script file name is the vanilla file of that name under `P:\scripts\`.

## Which material covers the job

| Job | Read |
|---|---|
| New motorbike, from scratch or derived from `Motorbike_01` or `Motorbike_02` | `skills/_shared/vehicles/motorbikes.md`, then `references/forward-contract.md` and `references/config-contract.md` |
| Motorbike model imported from another game or an asset store | this skill, plus `dayz-model-pipeline` for the mesh and LODs |
| Car, truck, quad or boat | the vehicles pack (`skills/_shared/vehicles/README.md`) and `dayz-vehicles` |
| Aircraft | `dayz-aviation` |
| Moving a car mod from 1.29 to 1.30 (components, lights, horn, particles) | `references/vehicle-1.30-refactor.md` |
| Rider animation, handlebar pose, the `.agf` graph | `references/rider-animation.md`, plus `dayz-animation-pipeline` for authoring clips |
| First-person view from the seat: a ViewPilot LOD (resolution 1100; the vanilla bikes have none) and closing the gaps the rider sees through the fairing | `skills/_shared/vehicles/view-pilot-and-first-person.md` |

## References

Deep material lives in the vehicles pack and in `<skill-dir>\references\`. Open only the file the step needs.

| Question | File |
|---|---|
| Class tree, addon, vanilla bikes, mandatory overrides, differences from a car | `skills/_shared/vehicles/motorbikes.md` |
| The ten rules that break a motorbike, measured tuning lessons, what is unfinished in 1.30 | `skills/_shared/vehicles/motorbike-invariants.md` |
| Literal `config.cpp` blocks (`Crew`, `SimulationModule`, `DamageSystem`, wheels, `AnimationSources`) and the full parameter table of both bikes | `references/config-contract.md` |
| `proto native` signatures of `Motorbike`, stability callbacks, `MotorbikeScript` lifecycle, what a bike lacks compared with `CarScript` | `references/script-api.md` |
| Kickstart, stop, pick-up, seat and repair actions, `MotorbikeHud`, the light, horn and particle components, sound sets, `UAToggleVehicleLights` against `UAToggleHeadlight` | `references/actions-hud-lights-sounds.md` |
| Rider pose, hand IK, `vehicles.agf` nodes (`MotorBikeSTM`), directional get-in, third-person camera, per-bike pose without replacing the graph | `references/rider-animation.md` |
| Deprecated `CarScript` methods, component migration, 1.29 guide claims that are false in 1.30 | `references/vehicle-1.30-refactor.md` |
| Production checklist before packing, and what to measure in the model | `references/forward-contract.md` |
| Real anatomy of the two vanilla models: mass, LODs, skeleton, all animations with sources and axes, memory points, proxies, selections | `references/vanilla-p3d-anatomy.md` (tool output, read its header before quoting a number) |
| Every cited vanilla file with its line count, where the sounds are, what a later build changed | `references/sources.md` |

## Decide the rider posture before modelling

No runtime hand adjustment exists, so the posture has to be chosen before the handlebar, footpegs and seat are modelled.

- [EXACT] The posture is chosen only by `GetAnimInstance()`: the get-in action passes it to `SetVehicleType` (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetintransport.c:104-107`), and the graph `vehicles.agf` routes on it. Five nodes test the literal `VehicleType == 10 || VehicleType == 11` (`P:\DZ\anims\workspaces\player\player_main\vehicles.agf:1429`, `:1474`, `:1529`, `:1570`, `:2806`).
- [EXACT] Each vanilla bike has its own column in the animation set, `"Jawa_05"` and `"Jawa_Bitrak"` (`P:\DZ\anims\workspaces\player\player_main\player_main.ast:1119-1120`), with its own clips (`player_main.asi` binds 19 `Vehicle.Jawa_05.*` and 17 `Vehicle.Jawa_Bitrak.*` instances; for example `Vehicle.Jawa_05.DriverSteeringMain` is `p_motorbike_01_driver_steering_pose.anm`, `player_main.asi:5131`, and `Vehicle.Jawa_Bitrak.DriverSteeringMain` is `p_motorbike_02_driver_steering_pose.anm`, `player_main.asi:5179`). Hand IK takes its targets `LHandIKTarget` and `RHandIKTarget` from those clips (`AnimNodeIK2Target0` over `SteeringBlend`, `vehicles.agf:17-46`), not from the bike's model. There is no foot IK.
- [EXACT] There are no Arma-style config keys for the hands: `driverLeftHandAnimName` has 0 occurrences in the singletrack, wheeled and `bin` configs on `P:\`.
- Consequence: neither the model nor the config moves the hands. Either fit the handlebar, footpegs and seat of the model to the contact points of `MOTO1` or `MOTO2` (measure them in game on the vanilla bike first), or supply custom clips. A handlebar of a different width does not fix itself. Measured in game on 1.30 on a sport bike with GP clip-ons: `MOTO1` and `MOTO2` leave the hands about 40 cm above the bars.
- Custom clips by adding a column mean changing `player_main`, and only one mod may replace the player graph (`references/rider-animation.md`, section 5). There is a third way that leaves the graph alone: a child `.asi` holding custom clips, registered and swapped in with `SetAnimationInstanceByName` only for the bike's class, the way vanilla does surrendering (`playerbase.c:2087-2088`, `dayzplayercfgbase.c:1543-1548`). Measured in game on two sport bike mods (2026-09-28, DayZDiag 1.30.164014, dedicated server and the owning client): it works with the bike stopped and moving. Steering clips are spread over ±45° of real wheel angle on every bike (`vehicles.agf:50`, `:1466`), not over each bike's lock, and transitions must be exported as whole-body poses (as additive differences they collapse the skeleton). Remote observers and edge cases are untested. Recipe, traps and the pose in four pieces: `references/rider-animation.md`, "Per-bike pose without replacing the graph".
- Third-party mod behaviour, not vanilla: the `MOTORCYCLE` (16) instance of the Survivor Animations mod (Workshop 2918418331) is the car driver body of the Offroad Hatchback with IK hands, in a graph of the 1.29 format. That such a graph crashes on 1.30 is not checked in game here. Detail in the same reference.

## Day-0 critical path for a new motorbike

The minimum set of deliverables for a working bike, in order. Each step that breaks silently has a rule in `skills/_shared/vehicles/motorbike-invariants.md`.

1. [EXACT] **`CfgPatches` and the vehicle class.** Require `DZ_Vehicles_Singletrack` (`P:\DZ\vehicles\singletrack\config.cpp:3`) and inherit `MotorbikeScript`, which brings `simulation = "motorbike"`. `dayz-config-specialist` owns the `CfgPatches` class.
   ```cpp
   class CfgPatches { class MyBike { units[] = {}; weapons[] = {}; requiredAddons[] = {"DZ_Data", "DZ_Vehicles_Singletrack"}; }; };
   ```
2. [EXACT] **`class Crew`.** `class Driver` and `class CoDriver: Driver` with `actionSel = "seat_driver"`, `proxyPos = "crewDriver"`, `getInPos = "pos_driver"`, `getInDir = "pos_driver_dir"`, both with `isDriver = 1;` (`config.cpp:52-70`).
3. [EXACT] **`class SimulationModule`.** `class Wheels` with `class Front` and `class Rear` (no `Axles`), `class Brakes` with `Front` (`input = 1`) and `Rear` (`input = 0`), and the lean curves in `class Steering` (`config.cpp:263-378`). Invariants 1, 2 and 6.
4. [EXACT] **`AnimationSources`.** Dampers `damper_1` and `damper_2`, wheel state `AnimHitWheel_1` and `AnimHitWheel_2` (`config.cpp:111-147`, `:379-399`). Add `SeatDriver` for a flip-up seat (invariant 4).
5. [EXACT] **`DamageSystem`.** `GlobalHealth` (1000 HP) and the zones of `Motorbike_01`: `Chassis`, `Fender` (transfer target of `Front`), `Engine` (`inventorySlots[] = {"SparkPlug"}`), `Front`, `Reflector_1_1`, `Back` and `FuelTank`, plus `GUIInventoryAttachmentsProps` (`config.cpp:400-989`). A glass slot that should hide at health 0.0, as in `Reflector_1_1`, is a config shape not yet seen working in game (the end of section 6b of `skills/_shared/vehicles/vehicle-config-and-modelcfg.md`).
6. [EXACT] **Wheels and proxies.** One class per wheel on `MotorbikeWheel` with a `_Ruined` child (`config.cpp:154-219`), and the proxies in `CfgNonAIVehicles` (`config.cpp:2316-2350`):
   ```cpp
   class MyBike_Wheel_1: MotorbikeWheel { scope = 2; radius = 0.29; width = 0.06; tyreLateralFriction = 3.0; };
   ```
7. [EXACT] **Geometry hidden at speed.** `speedGeomActivation = 0.29;` and `speedGeoms[] = {"geotohide"};` (`config.cpp:258-262`). Invariant 8.
8. [EXACT] **The 4_World script class.** A class on `MotorbikeScript`, shaped like `Motorbike_01_ColorBase` (`P:\scripts\4_world\entities\vehicles\inheritedmotorbikes\motorbike_01.c:1-166`). The constructor sets the contact damage coefficients, the engine and horn sound sets, and registers the lights on `m_LightsComponent`:
   ```c
   m_VehicleContactDamageCoef = 0.03;
   m_CrewContactDamageCoef = 0.018;
   ```
   Invariants 5 and 9.
9. [EXACT] **Script overrides.** `GetAnimInstance()` returning `VehicleAnimInstances.MOTO1` (10) or `MOTO2` (11), `HasDirectionalInOutAction()` (`true`), `GetSeatAnimationTypeDirectional()`, `GetTransportCameraDistance()`, `GetTransportCameraOffset()`, and `NeedElectricitySourceDevice()` (`false` on a magneto or kickstart bike; without the override the bike needs a battery, `transport.c:821-824`). Table with lines: `skills/_shared/vehicles/motorbikes.md`.
10. [DESIGN] **The model.** A `drivewheel` bone on the front fork (invariant 3), light memory points (`light_1_1`, `light_1_2_reverse`), smoke points (`ptcExhaust_start`, `ptcExhaust_end`, `ptcEnginePos`), the fuel cap (`refill`) and the damage selections (`dmgZone_*`). Details: `references/forward-contract.md`. `dayz-object-builder` owns the model.
11. [EXACT] **Sounds.** Reference the engine, exhaust, damper and horn sound sets from `P:\DZ\sounds\hpp\config.cpp` (the `Motorbike_0*` classes), or the mod's own:
    ```c
    m_EngineStartOK = "Motorbike_01_engine_start_SoundSet";
    m_HornComponent.RegisterSound(VehicleHornMode.SHORT, "Motorbike_01_Horn_Short_SoundSet");
    ```
12. [DESIGN] **Economy and spawn.** Register the bike in `types.xml` and `cfgspawnabletypes.xml` with a spark plug (`SparkPlug`) and its wheels attached. `dayz-server-admin` owns those files.
13. **Rider posture.** Decided before step 10: the section above.

## How to verify

1. **Offline, before opening the game.** Run `/dayz-lint` on the mod (setup errors), and the script validator on the addon folder (the code itself):
   ```cmd
   python scripts\tools\dayz-script-validator\scripts\script_validator.py <addon_root>
   ```
   - It prints JSON with `errors` and `warnings` at the root. The exit code is 0 (pass), 1 (fail) or 2 (warnings only).
   - Gate on `len(errors) == 0`: a clean tree with minor warnings exits 2 and is still valid.
   - It reports broken references in Enforce Script `.c` files, layouts, `config.cpp` and `.rvmat` files.
   - Compare against the unchanged base tree to isolate the errors the mod introduced.
2. **In game.** The orchestrator owns the test session (`/dayz-launch-test`); a worker returns these as gate checks. The ladder:
   - **Spawn**: spawn the bike on a local server started with `-filePatching`. It stays upright on the kickstand, without endless oscillation and without sinking into the ground.
   - **Render**: the wheels show their proxies, the materials respond, and no panel is grey or invisible because of a wrong selection name.
   - **Get in**: approach from the left side, then from the right; `ActionGetInTransport` plays the directional animations `GetIn_L` and `GetIn_R`.
   - **Start and ride**: `ActionStartEngineMotorbike` plays the kickstart sound, the headlight turns with the handlebars (`drivewheel`), and the third-person camera follows the steering with its spring lag.
   - **Telemetry**: rpm, speed and gear respond as the `SimulationModule` says.
   - **Fall and recover**: a side hit or a sharp turn tips the bike, the rider is thrown off (`CrewShouldEject`) and `ActionPickUpMotorbike` stands it up again.
3. **In the RPT** [UNVERIFIED: these message texts are illustrative, not measured; search by symbol]:
   - `Cannot load surface info` or `Undefined sound shader`: a sound set or particle surface is missing in `CfgSurfaces`.
   - `AnimationSource ... not found`: a source is not declared in `AnimationSources`.
   - `Bone 'drivewheel' not found`: the front fork bone is missing from the model.
   - A spawn with no simulation: check for an `Axles` block where `Wheels` should be (the exact failure is not measured).

### With the DayZ-MCP bridge

The DayZ-MCP bridge (a separate tool, installed separately: `docs/dayz-mcp.md`) can run this ladder with the verbs `world_spawn`, `vehicle_get_in_client`, `engine_set`, `vehicle_telemetry`, `telemetry_read` and `action_use`. Its limits on motorbikes, as third-party tool behaviour not re-measured here:

- (As of 2026-10-28) The bridge addon does not know `Motorbike` (0 occurrences in its `addon\` folder): control and telemetry cast to `CarScript`, so `engine_set`, `vehicle_control` and the engine part of `vehicle_telemetry` do not see a motorbike, which inherits `Transport` and not `CarScript`. Its `ResolveOwnedCar` answers `not_seated` for anything that is not a `CarScript`. There is no verb to read player bones (the rider pose).
- While 1.30 was Experimental its launcher only started the stable game; with 1.30 stable that no longer applies.
- What works without the bridge: a diagnostic addon with the scenario in a `modded MissionServer` behind a command line parameter, markers written to `script_*.log`, two `.bat` files starting `DayZDiag_x64.exe` and a Python driver that waits for the log markers. Seating the player from the server gives a crew member without `HumanCommandVehicle` on the client: good for measuring the pose on the server, not for validating actions or the HUD.

## What could not be verified

1. **The binary models.** The source `model.cfg` of the vanilla bikes is not distributed, and `/dayz-p3d-audit` reads only MLOD source models, not the binarized vanilla files. The anatomy in `references/vanilla-p3d-anatomy.md` comes from a reader for the 1.30 model format that is not in this repo (ODOL version 56; 1.29 used 54, and the public ODOL to MLOD converter only reads 54). The names `drivewheel`, `damper_1`, `damperfront`, `kickstand`, `geotohide`, `pos_driver`, `light_1_1` and `refill` are present as text in `Motorbike_01.p3d`, and the string `proxy:` occurs 49 times there (7 distinct proxy names).
2. **Bone names script does not mention.** Only `drivewheel` is named in script; the rest is in the anatomy reference.
3. **The native physics.** The gyroscopic solver, the stability logic and the balance model are compiled into the game and not reachable from Enforce Script: curve units and the effect of `tipoverAngle` are unverified.
4. **Tyre feel.** The friction keys (`tyreLateralFriction`, `tyreLongitudinalFriction`) are read from config, but grip on wet curves or gravel needs driving in game.

## On Linux

Everything above is the Windows workflow. The shared Linux and Proton notes (`skills/_shared/linux-proton.md`) hold the setup, the measured tool matrix and the pitfalls; this section only says what changes for this skill. None of it has been run in Agentic-Z.

- Pack, sign and binarize with dayzmake 1.0.0 or later, the DayZ build of armake2, pinned to `v1.0.0` (the release binary `dayzmake-v1.0.0-debian-trixie-x86_64.tar.gz`); the shared Linux notes say how to install it. Use `dayzmake build`, `keygen`, `sign`, and `build --proton-binarize` where needed. Plain armake2 is no substitute: it is built for Arma, its V3 file hash omits `*.c` files (dayzmake `v1.0.0` includes them) and it lacks the DayZ-only functions dayzmake keeps adding. A shared shell script wraps them, `skills/_shared/scripts/dayz-mod-pack.sh` (`init`, `keygen`, `build [--binarize-models]`, `check`, `publish-hint`). A textured cube packed this way on 2026-11-03 matched Bohemia's binarize from a `P:` root byte for byte; that is a file comparison, not an in-game check of the binarized model.
- `P:\` is a plain directory mapped by `dayz-proton.sh init <dir>` (the script is `skills/_shared/scripts/dayz-proton.sh`); a `P:\<Mod>\...` path in this skill is `<dir>/<Mod>/...` there.
- Object Builder and TexView run under Proton (`dayz-proton.sh gui ObjectBuilder <p3d>`, `gui TexView <paa>`). Object Builder opened and showed a model; editing in it was not tried. The offline Python checks under `scripts/tools/` run natively.

## Building, testing and publishing

When the work has to end in a mod that builds, loads and ships (`config.cpp`, `CfgMods`, `requiredAddons`, the PBO and its signature, a boot on a local server, the Workshop), follow `docs/dayz-modding.md` and the build skills (`/dayz-build-pbo`, `/dayz-gate`, `/dayz-launch-test`); the mod development loop is in `dayz-mod-dev`.
