# Vehicle pack

Reference for building cars, boats and helicopters: the class tree, simulation config, attachment slots, crew seats, fluids and damage. Every fact cites the vanilla file on `P:\` it came from. Line numbers match the vanilla data at the time of writing; when a line has moved, Grep for the class or key name.

The pack also covers motorbikes and aircraft built on `CarScript`, and it holds field notes measured on real vehicle builds (imports, rips, gauges, lights, build and test gates). Each field-note file opens with a status note that says what was opened on `P:\` and what was measured in game on a mod test vehicle, which is mod behaviour and not vanilla. The numbered invariants those notes cite ("invariant N", "preflight #N") are indexed in `skills/dayz-vehicles/SKILL.md`.

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

The deeper aircraft and motorbike references are skill packs: `skills/dayz-aviation/SKILL.md` and `skills/dayz-motorbikes/SKILL.md` index them. A ripped racing-game car has its own route in `skills/rip-vehicle-import/SKILL.md`.

## Authoring and config

| Question | File |
|---|---|
| A complete, source-checked `config.cpp` and `model.cfg` for a drivable car, block by block; window and glass damage zones; what the engine feeds the dashboard needles; how get-in picks a seat; ruined wheels | `vehicle-config-and-modelcfg.md` |
| Boats (propeller, buoyancy, boat fluids, always-free get-in), trucks (three axles, double wheels under one class name), ATV slots | `vehicle-types-boat-truck.md` |
| What changed for vehicles in DayZ 1.30: light profiles and the light toggle, the battery methods, horn, the get-in condition, fluids, boats, `speedGeoms`, ruined wheels and tyre fields, script module paths, line drift, and a 1.29 to 1.30 migration checklist | `dayz-1-30-vehicles.md` |
| What each of `.p3d`, `config.cpp` and `model.cfg` owns; what to measure before the first in-game cycle; gaps a port inherits | `new-car-day-one.md` |

## Making an imported or procedural model work

| Question | File |
|---|---|
| The parity-first method: diff the model against a working vanilla car and build every missing LOD, selection, crew proxy and wheel hub in one pass | `vehicle-structural-parity.md` |
| OBJ to game-ready `.p3d`, end to end: parse, transform, decimate, assemble LODs, encode textures, write config | `external-obj-import.md` |
| Reducing a high-poly import to per-LOD face budgets | `decimation-libraries.md` |
| PNG to PAA in pure Python | `png-to-paa-encoding.md` |
| Origin, `autocenter` and placement problems | `placement-and-autocenter.md` |
| Rip geometry: retopology, winding gate and direction, `autocenter` scope, deleting or splitting faces without breaking selections | `rip-geometry-and-winding.md` |
| The rip import path in detail, including the first in-game spawn results | `rip-import.md` |
| Reading a GTA V mod archive offline; bone names against mesh pieces; why an exclusion list is literal names | `gta-rip-intake.md` |
| Mesh and UV health, mirror against rotation, raw winding, the nose direction, cabin alignment, steering wheel against hands | `invariants-import-mesh-and-winding.md` |
| How many visual LODs, how far planar dissolve and collapse go, the resolved-vertex ceiling | `invariants-lods-and-vertex-budget.md` |
| The three verdicts of `binarize`, the real ceiling in triples, headroom, what does not discriminate | `binarize-vertex-budget.md` |
| Mass tagged in the wrong LOD, wheel-well clearance, seat components, crew proxy triangles, the vertex ceiling false positive | `p3d-vehicle-killers.md` |

## Get-in, seats, doors and proxies

| Question | File |
|---|---|
| No get-in prompt, no co-driver or rear seat, no door action; four seats; right-hand drive; choosing a donor; inherited config keys | `invariants-get-in-and-seats.md` |
| The four-link get-in condition chain, action registration, the `Geometry` and `autocenter=0` gate for proxied submodels, which anchor really places the occupant, and why a part's `model=` governs both the fitted part and the loose item | `get-in-actions-and-proxy-pose.md` |
| Proxy placement measured on a reference car, the four-layer contract of detachable parts, the two registrations a vehicle action needs, View Pilot of a shell and proxy car | `proxies-and-get-in.md` |
| Door edges: measuring the missing edge, closing it by script, hood and trunk against a door | `doors-and-panel-edges.md` |
| Why a ripped door, hood or tailgate shows a see-through rim, and what does not close it | `rip-panel-open-rim.md` |
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
| An LED or indicator that changes colour, glows and optionally lights the scene: hidden selection, one `.rvmat` per state with `emmisive[]`, the swap from script, a `PointLightBase` on a memory point | `emissive-leds-and-dynamic-lights.md` |
| Dashboard needles and dials: frame and mirror traps, rotation direction, deriving `angle0` and `angle1`, needle build, fuel panel from scratch, night check, the full recipe | `gauge-needles.md` |
| A map on a cockpit screen: render target bridge, satmap tiles, tile overlap, sliding tile window | `cockpit-screens-and-map-tiles.md` |
| What the seated player sees: the res 1100 View Pilot LOD and its proxies; offline first-person viewer traps | `view-pilot-and-first-person.md` |
| An empty inventory preview of a door or part: `rotationFlags` per side, `invview` placement | `inventory-preview.md` |
| Identical textures and server mismatch as false diagnoses; parent-driven selections do not reach a proxy | `materials-and-selections.md` |

## Build, runtime and test

| Question | File |
|---|---|
| `model.cfg` for ODOL against MLOD, reversed wheel spin, proxy drive paths, offline PBO checks | `build-packaging-and-debug.md` |
| Proving an animation and new geometry survived binarization: skeleton bones, `sections[]`, section flags, PAA encoding, translation offsets | `animation-bake-and-odol-sections.md` |
| Is the packed PBO the approved artifact; `config.cpp` syntax with `CfgConvert` and canaries; comparing native crashes | `deploy-gates-and-crash-fingerprint.md` |
| Per-tick events, engine state on a passenger's client, visual state on a fresh spawn, a vehicle drawn or exited in the wrong place | `runtime-state-and-sync.md` |
| Network ownership against a forced seat, why writing the pose fights the owner, a custom Pawn frame | `network-physics-ownership.md` |
| Driving, seating and unseating a vehicle from an automated harness; what the server still validates | `test-stand-and-mcp.md` |
| Whether a pose complaint is a perspective artifact; anchoring a HUD marker ray; validating a visual metric | `visual-metrics-and-viewer.md` |
| The per-session history of the imported-car visual gates, items #10(a) to #10(o); what a clean `validate()` and a Blender culling render cannot prove about winding; the sign of a face a script adds or moves | `visual-gates-and-winding.md` |

## Method and history

| Question | File |
|---|---|
| The iteration budget, calibrating a gate before trusting it, what a PASS covers, the habits that stop re-deriving known causes | `method-and-gate-calibration.md` |
| Negative fixtures for import gates, rules drawn from field lessons, a config gate is not a visual gate | `process-gates.md` |
| The superseded diagnostic order, kept for vehicles already in flight. History only | `history/legacy-gate-ladder.md`, `history/pre-change-0-gate-ladder.md` |
| The exact text of rules that were later corrected. History only | `history/superseded-family-b-rules.md` |

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
