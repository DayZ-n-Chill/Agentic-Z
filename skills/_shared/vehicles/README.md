# Vehicle pack

Reference for building cars, boats and helicopters: the class tree, simulation config, attachment slots, crew seats, fluids and damage. Every fact cites the vanilla file on `P:\` it came from. Line numbers match the vanilla data at the time of writing; when a line has moved, Grep for the class or key name.

The pack also covers motorbikes and aircraft built on `CarScript`, and it holds field notes measured on real vehicle builds (imports, rips, gauges, lights, build and test gates). Each field-note file opens with a status note that says what was opened on `P:\` and what was measured in game on a mod test vehicle, which is mod behaviour and not vanilla. The numbered invariants those notes cite ("invariant N", "preflight #N") are indexed in `README.md`.

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

A ripped racing-game car has its own route in `rip-family-b-runbook.md`.

## Pick the route first

Choose by where the asset came from and how it is built, not by its symptom.

| What you have | Route |
|---|---|
| A car ripped from a racing game, split into proxies, with doors or other moving parts (family B) | `rip-family-b-runbook.md`: follow only its adapter, golden and allowlist, then the asset's own `asset-contract.json` |
| An asset already in flight with a frozen plan or runbook | That runbook; do not migrate it here |
| Any other vehicle: authored from scratch, an OBJ import, a port from another mod or game | The tables of this README |
| A family B asset whose adapter is missing | Stop and report; do not improvise a route from the pack |

Before re-importing or re-assembling any piece, measure whether it is complete, face for face, against the model already packed: a mesh that looks rotten is usually complete and the defect lies elsewhere (`rip-panel-open-rim.md`). The offline vehicle checks (get-in anchors, seat selections, wheel axes, ODOL sections and bone bindings) are scripts of `/dayz-p3d-audit`.

## Numbered invariants

Other files cite these as "invariant N", "preflight #N" or "#N".

| Number | File |
|---|---|
| 0, 0b, 7, 10, 11, 12, 14, 29, 33 | `invariants-import-mesh-and-winding.md` |
| 1, 2, 3, 4, 5, 20, 20b, 21, 22, 23, 28, 30, 31, 32, 34 | `invariants-get-in-and-seats.md` |
| 5b, 5c, 6, 15, 15a, 15b | `invariants-wheels-and-hubs.md` |
| 8, 9, 15c, 15f, 15g, 15h, 16, 17, 18, 19, 35 | `invariants-engine-fluids-and-handling.md` |
| 13, 24, 27 | `invariants-lods-and-vertex-budget.md` |
| 15d | `lights.md` |
| 15e | `test-stand-and-mcp.md` |
| 25, 26 | `gta-rip-intake.md` |
| #10(a) to #10(o) | `visual-gates-and-winding.md` |
| "METHOD #1" to "#4" | `method-and-gate-calibration.md` |
| "Day-1" items | `new-car-day-one.md` |

Items 3, 12 and 21 moved to the symptom files (`symptom-wheels-not-present.md`, `symptom-white-vehicle.md`, `symptom-attachment-invisible.md`); the invariant files keep a pointer under each number. Before writing a class name, property or named selection, Grep it under `P:\DZ\vehicles\` or in the file a pack file cites, and mark a value you could not check as "not yet checked on `P:\`".

## Aircraft in depth

| Question | File |
|---|---|
| Fixed-wing flight in script: lift, drag, stall, atmosphere, self levelling, NaN guards, seaplane buoyancy | `aviation-aerodynamics.md` |
| `AnimationSources` and `model.cfg` classes for control surfaces, dials, dampers and the propeller | `aviation-animation-and-modelcfg.md` |
| What DayZ 1.30 changed under a plane or helicopter that inherits `CarScript` | `aviation-dayz-1-30.md` |
| Navigation lights, headlights and seaplane spray | `aviation-effects-and-lights.md` |
| One base class for several planes: config skeleton, `requiredAddons`, sub-mod wrapper | `aviation-fixed-wing.md` |
| Testing a scripted flight model in game and judging it from logs | `aviation-flight-testing.md` |
| Flight inputs in `Inputs.xml`, keyboard and pad scheme, stringtable | `aviation-input-bindings.md` |
| Offsets measured with py3d that land on the wrong end of the aircraft, and the runtime probe that settles it | `aviation-model-axes.md` |
| Engine sound shaders and sets, RPM band crossfade | `aviation-sounds.md` |
| Thermal (FLIR) view by swapping textures and materials per entity | `aviation-thermal-imaging.md` |
| Optional aircraft weapons: tracer projectiles, hitscan damage, the fire pipeline | `aviation-weapons.md` |
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
| The vanilla `config.cpp` blocks and the parameter table | `motorbike-config-contract.md` |
| The full specification for a new motorbike | `motorbike-forward-contract.md` |
| Rider animation: vehicle command, `vehicles.agf`, clips, camera | `motorbike-rider-animation.md` |
| Native `Motorbike` interface, callbacks, `MotorbikeScript` lifecycle, net sync | `motorbike-script-api.md` |
| What the binarized vanilla bike models hold | `motorbike-vanilla-p3d-anatomy.md` |
| Every vanilla file the motorbike files cite, with line counts | `motorbike-vanilla-sources.md` |

## Symptoms of a ripped car

| Symptom | File |
|---|---|
| An attached wheel, door or part simulates but does not render | `symptom-attachment-invisible.md` |
| A door shows no open or close action | `symptom-door-action-missing.md` |
| The get-in prompt never shows | `symptom-get-in-missing.md` |
| Wheels are attached but do not simulate | `symptom-wheels-not-present.md` |
| The car renders white or untextured on a dedicated server | `symptom-white-vehicle.md` |

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
| The day-0 family B runbook for a new ripped car: the six contract deltas, the source door inventory, the single ledger entry, the B1 to B7 allowlist, the human visual signoff, the conversion rail | `rip-family-b-runbook.md` |
| Reviewing and changing the session A classification of a ripped car's parts without Blender: the viewer's Three.js files, the steps per car, the GLB data contract | `rip-classify-viewer.md` |
| Field by field, what a car profile of the import project holds and which script reads each field (legacy and in flight; not a template) | `rip-profile-schema.md` |
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
| The day-1 checklist and 12-step pipeline a ripped car followed before change 0. History only | `history/family-b-canonical-path.md` |
| The seven document types a new family B car no longer produces since change 0, and where each is kept. History only | `history/family-b-retired-artifacts.md` |
| The full family B runbook that change 1 took off the critical path: smoke test notes, recurring defects, lift, doors, proxy frames, render gate, glass, winding lineage. History only | `history/family-b-runbook-pre-change-1.md` |

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
