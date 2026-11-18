# Vehicle pack

Reference for building cars, boats and helicopters: the class tree, simulation config, attachment slots, crew seats, fluids and damage. Every fact cites the vanilla file on `P:\` it came from. Line numbers match the vanilla data at the time of writing; when a line has moved, Grep for the class or key name.

The pack also covers motorbikes and aircraft built on `CarScript`, and it holds field notes measured on real vehicle builds (imports, rips, gauges, lights, build and test gates). Each field-note file says near its top what was opened on `P:\` and what was measured in game on a mod test vehicle, which is mod behaviour and not vanilla.

Open only the file the current step needs.

| Question | File |
|---|---|
| Which parent class, which addon to require, which script class to write, which overrides are mandatory | `class-hierarchy.md` |
| `SimulationModule` keys: engine, clutch, gearbox, axles, suspension, wheels, boat propeller | `simulation.md` |
| `attachments[]`, `CfgSlots`, door and wheel part classes, inventory categories, crew seats, door states | `attachments-and-crew.md` |
| Fuel, oil, coolant and brake fluid, engine start rules, battery and plugs | `fluids-and-engine.md` |
| `DamageSystem` zones, zone names script depends on, crash damage to the vehicle and crew | `damage.md` |
| Helicopters: what vanilla ships, the native classes and the `CarScript` route, which shipped flight model to learn from | `helicopters.md` |
| Aircraft on `CarScript`: entity events, what the car body does to a scripted velocity, angular velocity axes, sleeping the body, what stops the engine | `aviation-carscript-base.md` |
| Owner prediction with the Pawn classes, `ForceCorrection`, ownership timing, the pilot's camera | `aviation-networking.md` |
| Custom flight inputs that read zero, `SyncedValue` priming, deadzones, in-seat actions and input excludes | `aviation-inputs-and-actions.md` |
| Motorbikes: the three-layer class tree, the addon, differences from a car, script overrides, config blocks | `motorbikes.md` |
| The ten rules that break a motorbike, measured tuning lessons, what is unfinished in 1.30 | `motorbike-invariants.md` |

A ripped racing-game car has its own route in `ripped-car-proxy-split.md`.

## Pick the route first

Choose by where the asset came from and how it is built, not by its symptom.

| What you have | Route |
|---|---|
| A car ripped from a racing game, split into proxies, with doors or other moving parts | `ripped-car-proxy-split.md` |
| A vehicle already being built from its own written plan | That plan; do not move it to this pack |
| Any other vehicle: authored from scratch, an OBJ import, a port from another mod or game | The tables of this README |

Before re-importing or re-assembling any piece, measure whether it is complete, face for face, against the model already packed: a mesh that looks rotten is usually complete and the defect lies elsewhere (`rip-panel-open-rim.md`). The offline vehicle checks (get-in anchors, seat selections, wheel axes, ODOL sections and bone bindings) are scripts of `/dayz-p3d-audit`.

## Before writing a name

Rules in this pack are named by their section heading, not by number. Before writing a class name, property or named selection, Grep it under `P:\DZ\vehicles\` or in the file a pack file cites, and mark a value you could not check as "not yet checked on `P:\`".

## Aircraft in depth

| Question | File |
|---|---|
| Fixed-wing flight in script: lift, drag, stall, atmosphere, self levelling, NaN guards, damping with no pilot | `aviation-aerodynamics.md` |
| Per-aircraft parameter values: large, small, aerobatic and flying car presets | `aviation-aircraft-presets.md` |
| `AnimationSources` and `model.cfg` classes for control surfaces, dials, dampers and the propeller | `aviation-animation-and-modelcfg.md` |
| What DayZ 1.30 changed under a plane or helicopter that inherits `CarScript` | `aviation-dayz-1-30.md` |
| Navigation lights, headlights and seaplane spray | `aviation-effects-and-lights.md` |
| One base class for several planes: config skeleton, `requiredAddons`, sub-mod wrapper, Pawn classes, ground and air modes | `aviation-fixed-wing.md` |
| Testing a scripted flight model in game and judging it from logs | `aviation-flight-testing.md` |
| Flight inputs in `Inputs.xml`, keyboard and pad scheme, stringtable | `aviation-input-bindings.md` |
| Offsets measured with py3d that land on the wrong end of the aircraft, and the runtime probe that settles it | `aviation-model-axes.md` |
| Engine sound shaders and sets, RPM band crossfade | `aviation-sounds.md` |
| Thermal (FLIR) view by swapping textures and materials per entity | `aviation-thermal-imaging.md` |
| Optional aircraft weapons: tracer projectiles, raycast damage, pilot only fire, impact effects timed to the tracer | `aviation-weapons.md` |
| The server side of an aircraft gun: ammunition from cargo, alternating muzzles, the damage ray, choosing a damage zone | `aviation-weapon-fire-code.md` |
| Memory points, skeleton bones and the lit dashboard material a plane model needs | `aviation-plane-model.md` |
| Skipping unchanged animation calls, update rates, cached inputs, cockpit detail in proxies | `aviation-script-performance.md` |
| Seaplanes: the `Buoyancy` class, water takeoff in script, large and small templates, spray effects | `aviation-seaplanes.md` |
| Helicopter flight loops of published mods, one file each | `helicopter-expansion.md`, `helicopter-mh6.md`, `helicopter-rffs.md`, `helicopter-sib.md` |
| Those helicopter mods side by side | `helicopter-model-comparison.md` |
| Which Workshop helicopter mods can be read as plain script | `helicopter-mod-sources.md` |

Before the first boot of an aircraft, check these faults, which compile clean and fail silently:

| Check | File |
|---|---|
| A flight loop in `EOnSimulate` sets `SetEventMask(EntityEvent.SIMULATE)` in the constructor (`CarScript` registers only `POSTSIMULATE` and `POSTFRAME`); nothing is pumped from `EOnFrame` with a hardcoded dt | `aviation-carscript-base.md` |
| A kinematic solver adds gravity back each tick, zeroes angular velocity after `SetOrientation`, and the test airframe has no wheels | `aviation-carscript-base.md` |
| The body is kept awake while flown and never put to sleep in the tick of `EEInit`; a fixed direct gear does not stop the engine when the pilot gets out (`OnDriverExit`) | `aviation-carscript-base.md` |
| Every custom `UA*` name matches across `inputs.xml`, the script read and the stringtable; the driver's client primes each custom action with `SyncedValue` every tick when the server reads it | `aviation-inputs-and-actions.md` |
| `GetNetworkMoveStrategy()` was probed on the client before the network model was chosen; no smoothing filter sits on the pilot's own camera | `aviation-networking.md` |
| Lights and battery follow the 1.30 vehicle contract | `aviation-dayz-1-30.md` |
| A helicopter that flies on `CarScript` does not use `HelicopterScript` as its base | `helicopters.md` |

## Motorbikes in depth

| Question | File |
|---|---|
| Motorbike actions, `MotorbikeHud`, lights, horn and VFX components, sound classes | `motorbike-actions-hud-lights-sounds.md` |
| The `MotorbikeScript` config class and the key values of both vanilla bikes side by side | `motorbike-config-contract.md` |
| The vanilla `SimulationModule` and `AnimationSources` of `Motorbike_01` | `motorbike-simulation-config.md` |
| The vanilla damage zones, damage materials and wheel classes of `Motorbike_01` | `motorbike-damage-and-wheel-config.md` |
| The full specification for a new motorbike | `motorbike-forward-contract.md` |
| Rider animation: vehicle command, `vehicles.agf`, clips, camera | `motorbike-rider-animation.md` |
| Native `Motorbike` interface, callbacks, `MotorbikeScript` lifecycle, net sync | `motorbike-script-api.md` |
| What the binarized vanilla bike models hold, at a glance, and how to read the tables | `motorbike-vanilla-p3d-anatomy.md` |
| Full model tables of each vanilla bike: LODs, bones, animations, memory points, proxies, selections | `motorbike-01-model-anatomy.md`, `motorbike-02-model-anatomy.md` |
| Every vanilla file the motorbike files cite, with line counts | `motorbike-vanilla-sources.md` |

## Symptoms of a ripped car

| Symptom | File |
|---|---|
| An attached wheel, door or part simulates but does not render: the proxy class name, the proxy frame, `ProxyVehiclePart` against `ProxyAttachment`, racks | `attachment-proxies.md` |
| A door shows no open or close action: choosing among the three door mechanisms | `vehicle-door-mechanisms.md` |
| The get-in prompt never shows: the action's guards in order, right-hand drive door pairing, asking the game which guard blocks | `get-in-guards.md` |
| Wheels are attached but do not simulate: the slot to Fire Geometry wiring | `wheel-simulation-wiring.md` |
| The car renders white or untextured on a dedicated server: what binarize leaves out, the include list, the two fixes | `binarize-dropped-textures.md` |

## Authoring and config

| Question | File |
|---|---|
| A car's `config.cpp` block by block: what each file owns, the class tree, `SimulationModule`, crew, lights, sounds, `AnimationSources`, how config, `model.cfg` and the model wire together, keys that do nothing | `vehicle-config-and-modelcfg.md` |
| Attachments, cargo and fuel; wheel and door items with their slots and proxies; an engine that will not start; `OnDebugSpawn` | `vehicle-parts-and-start.md` |
| A car's `model.cfg`: skeleton, animation classes, what the engine feeds the dashboard needles, reusing a vanilla rig, the crew proxy frame, limits of the seat probe | `vehicle-modelcfg-animations.md` |
| `DamageSystem` zones in config, window glass, `RefTexsMats[]` and `"hidden"`, a windscreen that never hid | `vehicle-damage-and-glass.md` |
| Ruined wheels: the swap script on 1.29 and 1.30, the ruined proxy, repair, the in-hands pose, flat tyre radius, sealing the rim | `ruined-wheels.md` |
| Boats (propeller, buoyancy, boat fluids, get-in always open, boat actions), trucks (three axles, double wheels under one class name), quads | `vehicle-types-boat-truck.md` |
| What changed for vehicles in DayZ 1.30, the deleted `ToggleHeadlights`, script module paths, ODOL version 56, line drift, and a 1.29 to 1.30 checklist | `dayz-1-30-vehicles.md` |
| DayZ 1.30 light profiles, the light toggle and lens flare, the battery methods, horn, `GetWeightCoef`, ganged rear bulbs | `dayz-1-30-lights-and-battery.md` |
| DayZ 1.30 get-in condition and boarding side, boats, `speedGeoms`, wreck cisterns, the motorbike camera | `dayz-1-30-get-in-and-boats.md` |
| DayZ 1.30 ruined wheel twins and the new tyre fields | `dayz-1-30-wheels.md` |
| What each of `.p3d`, `config.cpp` and `model.cfg` owns; what to measure before the first in-game cycle; gaps a port inherits | `new-car-day-one.md` |

## Making an imported or procedural model work

| Question | File |
|---|---|
| Comparing a car with the vanilla sedan before the first test: what each LOD holds, the memory point catalogue, selections, lights, damage and animation sources, auditing a car you received, checking the checker | `vehicle-structural-parity.md` |
| The Geometry LOD, mass and centre of mass, what makes a car launch or sink on spawn, wheel wells, contact diagnostics, suspension, the wheel `.p3d` collider | `vehicle-geometry-and-mass.md` |
| Proxy paths without `.p3d`, body chunk frames, bone selections for attachment proxies, hub and seat `componentNN` tags, which way a car faces, wheel spin direction, high-detail bodies as proxies | `vehicle-proxies.md` |
| Seat components, inward winding and point flags, the crew proxy triangle, the script class get-in needs, the script module, the headless seat probe | `crew-get-in-geometry.md` |
| OBJ import, first half: copying the closest item, splitting faces by material, the UV flip, the transform, winding against normals | `external-obj-import.md` |
| OBJ import, second half: decimating per material, smooth normals, LOD assembly and resolutions, PAA encoding, wiring into the mod, first-import problems | `obj-import-assembly.md` |
| Reducing a high-poly import to per-LOD face budgets | `decimation-libraries.md` |
| PNG to PAA in pure Python | `_shared/textures/png-to-paa-encoding.md` |
| Origin, `autocenter` and placement problems | `placement-and-autocenter.md` |
| Rip geometry: retopology, proxy triangle winding, where `autocenter=0` belongs, what a winding check must cover, fixing winding per connected part, deleting faces by side and with py3d, comparing two builds | `rip-geometry-and-winding.md` |
| A ripped racing game car: what the rip folder holds, which parts to include, the right side, dimensions and the transform from the locators, drivetrain and mass data | `rip-import.md` |
| Rip body and structural LODs: shell plus proxy chunks, thinning, what crashes the render, the LOD recipe, first spawn faults, offline checks, building and launching | `rip-structural-lods.md` |
| Rip textures: swatch UV channels, the factory paint colour, materials by type from the source, glass, interiors and two-sided surfaces, duplicate faces | `rip-textures-and-materials.md` |
| Rip wheels, doors and interior: deploying a rebuilt shell, wheels that draw, the original rim, track width, doors from the rip, the car's own first-person interior | `rip-wheels-and-doors.md` |
| Rip glass bands and gap closure, material transfer with foreign geometry, where a rally lift belongs, patching a deployed structure | `rip-glass-and-gap-closure.md` |
| A new ripped car split into proxies with moving parts: the transform, what to settle first, what the rips ship for doors, the user's visual check before a build, the order of work | `ripped-car-proxy-split.md` |
| Reviewing which parts of a ripped car are kept, dropped or movable without Blender: the viewer's Three.js files, the steps per car, the data the GLB must carry | `rip-classify-viewer.md` |
| Field by field, what a per-car profile of a rip import pipeline holds and which step reads it | `rip-profile-schema.md` |
| Reading a GTA V mod archive offline; bone names against mesh pieces; why an exclusion list is literal names | `gta-rip-intake.md` |
| Mesh and UV health, mirror against rotation, raw winding, the nose direction, cabin alignment, steering wheel against hands | `invariants-import-mesh-and-winding.md` |
| How many visual LODs, how far planar dissolve and collapse go, the resolved-vertex ceiling | `invariants-lods-and-vertex-budget.md` |
| The three verdicts of `binarize`, the real ceiling in resolved triples, headroom, log lines that mean nothing | `binarize-vertex-budget.md` |
| Mass tagged in the wrong LOD, wheel-well clearance, seat components, crew proxy triangles, the vertex ceiling false positive | `p3d-vehicle-killers.md` |

## Get-in, seats, doors and proxies

| Question | File |
|---|---|
| No get-in prompt, no co-driver or rear seat, no door action; four seats; right-hand drive; which vanilla car to copy; inherited config keys | `invariants-get-in-and-seats.md` |
| The four-link get-in condition chain, action registration, the `Geometry` and `autocenter=0` gate for proxied submodels, which anchor really places the occupant, and why a part's `model=` governs both the fitted part and the loose item | `get-in-actions-and-proxy-pose.md` |
| Proxy placement measured on a working car, the four layers of a detachable part, debug spawns and `attachments[]` after a baked part becomes an attachment, binarized output that is not byte-stable | `proxies-and-detachable-parts.md` |
| The two registrations an action for a seated player needs, continuous actions and input excludes from the seat, a shared script core, a phantom vehicle command after a crash | `seated-actions-and-get-in-faults.md` |
| Hiding a baked attachment proxy from script with an animation source, blocking a seat while something is attached | `attachment-proxy-hiding.md` |
| Door edges: measuring the missing edge, closing it by script, hood and trunk against a door | `doors-and-panel-edges.md` |
| Why a ripped door, hood or tailgate shows a see-through rim, what does not close it, how to cap it and check the cap | `rip-panel-open-rim.md` |
| Letting a rider fire their own weapon from a moving vehicle (the free gunner pattern) | `gunner-shoot-from-vehicle.md` |

## Wheels, engine and handling

| Question | File |
|---|---|
| "No proper selection in geometry", wheels off their hubs, a car that spawns sunk, a wheel facing backwards, a missing axle | `invariants-wheels-and-hubs.md` |
| Engine will not start or stalls, test kits, a car that rolls away, steering ramp, mass, tyre grip, drivetrain ratios, measured sedan launch | `invariants-engine-fluids-and-handling.md` |
| Whether an animation turns the right way: wheels, steering, doors, dials | `animation-sign-and-axis.md` |

## Lights, dashboard and views

| Question | File |
|---|---|
| Lights that do not switch: material paths, hidden selection order and ownership, bulbs, driver exit | `lights.md` |
| An LED or indicator that changes colour and optionally lights the scene: the hidden selection, the swap from script, a `PointLightBase` on a memory point | `emissive-leds-and-dynamic-lights.md` |
| The `.rvmat` for each LED state: shader and stages, `emmisive[]` strength and spelling, an LED that renders black | `emissive-led-materials.md` |
| Dashboard needles: selection, axis and bone, the `Indicator*` classes, which way vanilla needles turn, `rpm` against its ceiling, the build order | `gauge-needles.md` |
| The needle mesh: canonical pose, cutting a needle out of an imported cluster, rest angle, depth, winding and normal signs of new faces | `gauge-needle-part.md` |
| A dial's screen frame: mirror against rotation, the V direction, deriving `angle0` and `angle1` | `gauge-dial-frame.md` |
| Dial art: measuring the printed arc, one texture per dial, padding, legibility on screen, stale textures | `gauge-dial-art.md` |
| A fuel gauge panel on a model with no face for it | `gauge-fuel-panel.md` |
| A map on a cockpit screen: the render target route, satellite tiles, tile overlap, sliding tile window | `cockpit-screens-and-map-tiles.md` |
| What the seated player sees: the res 1100 View Pilot LOD and its proxies, trimming it safely, collapsed UVs in far LODs, offline first-person viewer traps | `view-pilot-and-first-person.md` |
| The View Pilot of a shell and proxy car: body geometry, its three states, creating a missing one, counting what the seat sees against LOD 0 | `view-pilot-assembly.md` |
| Closing gaps the seated rider sees through: membranes in the View Pilot only, behind the steering sweep, tested from every eye | `view-pilot-closures.md` |
| An empty inventory preview of a door or part: `rotationFlags` per side, `invview` placement | `inventory-preview.md` |
| Identical textures and a server-side measurement as false diagnoses; selections the car drives must live in the shell, not a proxy | `materials-and-selections.md` |

## Build, runtime and test

| Question | File |
|---|---|
| `model.cfg` for ODOL against MLOD, reversed wheel spin, proxy drive paths, offline PBO checks | `build-packaging-and-debug.md` |
| Proving an animation and new geometry survived binarization: skeleton bones, `sections[]`, section flags, PAA encoding, translation offsets | `animation-bake-and-odol-sections.md` |
| Is the packed PBO the approved artifact; `config.cpp` syntax with `CfgConvert` and canaries; comparing native crashes | `deploy-gates-and-crash-fingerprint.md` |
| Per-tick events, engine state on a passenger's client, visual state on a fresh spawn, a vehicle drawn or exited in the wrong place | `runtime-state-and-sync.md` |
| Network ownership against a forced seat, why writing the pose fights the owner, a custom Pawn frame | `network-physics-ownership.md` |
| Driving, seating and unseating a vehicle from an automated test bridge; what the server still checks; camera traps | `test-stand-and-mcp.md` |
| Whether a pose complaint is perspective; anchoring a HUD marker ray; checking a ripped part before rebuilding it; an offline visibility check | `visual-metrics-and-viewer.md` |
| Winding checks for imported cars: the orientation rule, per-piece uniformity, the see-through ray check, duplicate faces, shading seams, what a clean `validate()` and a Blender culling render cannot prove, the sign of a face a script adds or moves | `visual-gates-and-winding.md` |

## Method and history

| Question | File |
|---|---|
| Counting the cycles spent on one goal, making a check able to fail before trusting it, what a pass covers, habits that stop re-deriving known causes | `method-and-gate-calibration.md` |
| Import checks that can be trusted: a failing case for every rule, three exit states, independent controls, a config check is not a visual check | `process-gates.md` |

## Where vanilla keeps vehicle data

| What | Path on `P:\` |
|---|---|
| Native config parents (`Transport`, `Car`, `Boat`, `Motorbike`, `Helicopter`) | `P:\bin\config.cpp:1404` to `:1563` |
| Cars, their doors and wheels | `P:\DZ\vehicles\wheeled\config.cpp` (addon `DZ_Vehicles_Wheeled`) |
| Boats | `P:\DZ\vehicles\water\config.cpp` (addon `DZ_Vehicles_Water`) |
| Motorbikes | `P:\DZ\vehicles\singletrack\config.cpp` (addon `DZ_Vehicles_Singletrack`) |
| Batteries, plugs, radiators and other shared parts | `P:\DZ\vehicles\parts\config.cpp` (addon `DZ_Vehicles_Parts`) |
| Inventory slot definitions (`CfgSlots`) | `P:\scripts\config.cpp:11` (addon `DZ_Scripts`) |
| Native script classes | `P:\scripts\3_game\vehicles\` (`transport.c`, `car.c`, `boat.c`, `motorbike.c`, `helicopter.c`) |
| Script classes | `P:\scripts\4_world\entities\vehicles\` (`carscript.c`, `boatscript.c`, `motorbikescript.c`, `helicopterscript.c`, `inheritedcars\`, `inheritedboats\`, `inheritedmotorbikes\`) |
| Door, wheel and plug item scripts | `P:\scripts\4_world\entities\core\inherited\inventoryitem.c` |
