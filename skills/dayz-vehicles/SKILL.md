---
name: dayz-vehicles
description: "Checks a DayZ ground or water vehicle model offline (get-in memory points, seat selections, wheel axis handedness; in a binarized model, whether a named selection has a section the engine draws and which bone its vertices bind to) and points vehicle authoring, import and debugging at the right file of the vehicle pack. Use when building, importing, porting or debugging a car, truck, quad or boat: CarScript config.cpp and model.cfg, drivetrain and suspension, crew and get-in, doors, lights, gauges, proxies, LODs, a ripped or OBJ model that will not spawn, get-in missing, wheels missing or spinning backwards, a white or untextured vehicle, or a vehicle that breaks when packed for a server."
argument-hint: "<model.p3d> [more.p3d ...] | <binarized.p3d> --selection <name> | <binarized.p3d> --texture <substring>"
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-vehicles

Drivable wheeled vehicles extend `CarScript`. There is no generic vehicle base, and a car is never built from `EntityAI` or `Inventory_Base`: `CarScript` brings wheels, seats, sound and the damage system, and the mod configures the rest. Boats extend `BoatScript`. This skill is the vehicle layer on top of generic model work (geometry, LODs, textures): it holds the offline vehicle checks, and its tables say which file of the vehicle pack answers which question. The pack is `skills/_shared/vehicles/`; its front index is `skills/_shared/vehicles/README.md`.

Scope: cars, trucks, quads and boats, modelled from scratch or imported from Blender, an OBJ or another game. Anything that flies belongs to the dayz-aviation skill (`<skill-dir>\..\dayz-aviation\`). Two wheels belong to the dayz-motorbikes skill (`<skill-dir>\..\dayz-motorbikes\`): since DayZ 1.30 motorbikes are a vanilla family with their own base class.

Follow `skills/_shared/dayz-conventions.md`. The checks in this skill read only the files you pass them, so they do not run `/dayz-preflight`. Packing, binarizing and in-game steps do: run `/dayz-preflight` before them (it checks that `P:\` is mounted, DayZ Tools is installed and the `P:\Mods` junction exists).

## Pick the route first

Choose the route by where the asset came from and how it is built, not by its symptom.

| What you have | Route | Files to open on day 0 |
|---|---|---|
| A new car ripped from a racing game (a Grub rip), split into proxies, with doors or other moving parts (family B) | The rip-vehicle-import skill (`<skill-dir>\..\rip-vehicle-import\`). Follow only its adapter, golden and allowlist. | This table, that skill's `SKILL.md`, then the asset's own `asset-contract.json`. The schema, the Blender export and the primitive are machine inputs, not more documents to maintain. |
| An asset already in flight with a frozen plan or runbook | That runbook. Do not migrate it here. | Whatever its current plan cites. |
| Any other vehicle: authored from scratch, an OBJ import, a port from another mod or game | The tables below. | The one pack file the current step needs. |
| A family B asset whose adapter is missing | Stop and report. Do not improvise a route from the pack. | None. |

Everything below the route table is a diagnostic atlas, not the day 0 path. Open a file only when the adapter or a symptom points at it.

Before re-importing or re-assembling any piece, measure whether the piece is complete, face for face, against the model already packed. A mesh that looks rotten is usually complete, and the defect lies elsewhere (`rip-panel-open-rim.md` of the pack).

## How to run

`audit_getin_wheels.py` reads `.p3d` files with py3d. It uses the DayZ fork of py3d kept in this repo under `scripts/tools/py3d/`, the one py3d copy every skill shares (`/dayz-p3d-audit` loads the same folder), with nothing to install. `requirements.txt` names that same folder. Use it only where `import py3d` must work as an installed package, and run it from the repo root, because pip reads the path in it against the current folder:

```cmd
python -m pip install -r skills\dayz-vehicles\requirements.txt
```

| Script | What it checks | Input |
|---|---|---|
| `scripts\audit_getin_wheels.py` | Get-in memory points, seat selections and wheel axis handedness | One or more MLOD `.p3d` files (the source model, not a binarized one) |
| `scripts\gate_odol_sections.py` | Whether each named selection of a binarized model has a section the engine draws | One ODOL `.p3d` taken out of the packed PBO, and the selection names |
| `scripts\check_odol_bone_refs.py` | Which skeleton bone the vertices of a section bind to in a binarized model | One ODOL `.p3d` taken out of the packed PBO, and a texture substring |

The two ODOL scripts do not use py3d, which reads MLOD only. They need an external ODOL parser: the modules `bis_reader` and `odol_reader` of an ODOL to MLOD converter. That parser is not part of this repo. Point at its folder with `--backend-root <dir>` or the environment variable `DAYZ_ODOL_BACKEND_ROOT` (the variable the tool in `scripts/tools/dayz-odol-strict/` also reads). Without it both scripts stop with exit code 2 and say what is missing. DayZ 1.30 and its tools write ODOL version 56 (`dayz-1-30-vehicles.md` of the pack), so the parser must read that version.

### audit_getin_wheels.py

```cmd
python "<skill-dir>\scripts\audit_getin_wheels.py" path\to\car.p3d [path\to\control.p3d ...]
```

For each model it prints:

- the LOD list (`Vis0`, `Geo`, `Mem`, `Land`, `View`, `Fire`);
- each get-in anchor of the Memory LOD (`crewdriver`, `crewcodriver`, `pos_driver`, `pos_driver_dir`, `pos_codriver`, `pos_codriver_dir`, `seat_con_1_1`, `seat_con_2_1`) as `OK` with its point count and centroid, `EMPTY` or `ABSENT`;
- the unit direction of each wheel axis (`wheel_1_1_axis`, `wheel_2_1_axis`, `wheel_1_2_axis`, `wheel_2_2_axis`). Left and right axes whose X sign differs are mirrored, which predicts that one side spins backwards with one shared `angle1`; see `animation-sign-and-axis.md` of the pack before changing a sign;
- which seat selections (`seat_driver`, `seat_codriver`, `seatback_driver`, `seatback_codriver`) the Geometry, View Geometry and Fire Geometry LODs hold.

Pass a car that works in game next to the car under test and compare the two blocks: the difference between them does the diagnosis.

Exit codes:

- **0**: every anchor, every wheel axis (two points or more) and every seat selection is present. A seat selection counts when it is in the Geometry or the View Geometry LOD.
- **1**: a model defect. Each one is a `FAIL:` line on stderr after the report.
- **2**: no input, a missing file or a file py3d cannot parse (an `INPUT_ERROR:` line, and no report is printed for any model), or py3d was not found (no `scripts/tools/py3d/` folder and no installed py3d).

The required names are the two-seat roster of the reference quad the check was written against. A four-seat car passes or fails on its front pair only, and a car with no seat-back selections gets a `FAIL:` line for each; read those lines against the car's own `Crew` config before acting on them. The rules behind each line are in `invariants-get-in-and-seats.md` and `invariants-wheels-and-hubs.md`.

Only MLOD files can be read. Agentic-Z ships no debinarizer, so a binarized vanilla model cannot be passed as the control.

### gate_odol_sections.py

```cmd
python "<skill-dir>\scripts\gate_odol_sections.py" path\to\binarized.p3d --selection screen_nav --selection light_dashboard [--lod 0 --lod 1100] [--keyword dashboard] [--backend-root path\to\odol-backend]
```

Run it on the `.p3d` extracted from the PBO you are about to deploy, after any change that adds geometry or a textured selection. A selection can be present in every string table of the binarized file and still never render; what decides is its section (`animation-bake-and-odol-sections.md` of the pack).

It prints the ODOL version and LOD resolutions, the skeleton bones whose name is a gated selection or contains a keyword, and for each LOD read (default: 0 and 1100, the third-person and first-person visual LODs): the vertex, face, section and selection counts, the bounding box, the textures and materials whose path contains a keyword (default keywords: `gps`, `marker`, `cluster`, `screen`, `argb`, `color`, `dashboard`, `cab_screen`), the number of faces no section covers, and the proxies. For each `--selection` it prints the face and vertex lists, whether the selection is sectional, each section's face range, bone range, texture, material and `special` flags, each vertex's position, UV and bone reference, the UV span, and each face's area in square millimetres.

Exit codes:

- **0**: every gated selection is drawable in every LOD read, or no `--selection` was given (overview only).
- **1**: a model defect. Each one is a `FAIL:` line on stderr after the report: the selection is missing, is not sectional (it is not listed in `CfgModels` `sections[]`), owns no section, or one of its sections lacks the hidden-selection bit `0x20000` in `special` (a `0x0000C000` section is never drawn).
- **2**: no input, a missing file, a file with no `ODOL` signature (an MLOD source model), a file the parser cannot read, a `--lod` the model does not have, or no parser backend (an `INPUT_ERROR:` line).

A selection that is absent from the first-person LOD on purpose fails at LOD 1100; pass `--lod 0` alone to gate only the LOD it lives in.

### check_odol_bone_refs.py

```cmd
python "<skill-dir>\scripts\check_odol_bone_refs.py" path\to\binarized.p3d --texture gps_arrow [--texture cluster --max-faces 2] [--reference-texture cluster_co.paa] [--lod 0] [--backend-root path\to\odol-backend]
```

Use it when a section passes the gate above and still does not show. A vertex bound to a bone whose hide animation starts at phase 1 is invisible from spawn, whatever the material or the section says.

For each LOD read it lists every section whose texture path contains a `--texture` substring (with `--max-faces N`, only sections of at most N faces: a witness quad has two), and for each of its vertices the bone name, bone index and weight, or `NONE/static`. With `--reference-texture` it also prints the bone of the first vertex of a section that is known to render (the first section of more than ten faces whose texture path ends with that suffix), to compare against. Read the bone names against the `model.cfg` animations of the model: the script reports and does not judge.

Exit codes:

- **0**: the report was printed.
- **2**: no `--texture`, a missing or unreadable file, a `--lod` the model does not have, or no parser backend (an `INPUT_ERROR:` line).

Outside an agent session, `scripts\dayz\vehicle-getin-wheels.bat`, `scripts\dayz\vehicle-odol-sections.bat` and `scripts\dayz\vehicle-odol-bones.bat` run `audit_getin_wheels.py`, `gate_odol_sections.py` and `check_odol_bone_refs.py` with the same arguments.

## References

All files are in `skills/_shared/vehicles/`. Open only the one the current step needs.

### Authoring and config

| Question | File |
|---|---|
| Which parent class and script class, which addon to require, which overrides are mandatory, what DayZ 1.30 changed in `CarScript` | `class-hierarchy.md` |
| `SimulationModule` keys: engine, clutch, gearbox, axles, suspension, wheels, boat propeller | `simulation.md` |
| `attachments[]`, `CfgSlots`, door and wheel part classes, inventory categories, crew seats, door states | `attachments-and-crew.md` |
| Fuel, oil, coolant and brake fluid, engine start rules, battery and plugs | `fluids-and-engine.md` |
| `DamageSystem` zones, zone names script depends on, crash damage | `damage.md` |
| A complete, source-checked `config.cpp` and `model.cfg` for a drivable car, block by block; window and glass damage zones; what the engine feeds the dashboard needles; how get-in picks a seat; ruined wheels | `vehicle-config-and-modelcfg.md` |
| Boats (propeller, buoyancy, boat fluids, always-free get-in), trucks (three axles, double wheels under one class name), ATV slots | `vehicle-types-boat-truck.md` |
| What changed for vehicles in DayZ 1.30: light profiles and the light toggle, the battery methods, horn, the get-in condition, fluids, boats, `speedGeoms`, ruined wheels and tyre fields, script module paths, line drift, and a 1.29 to 1.30 migration checklist | `dayz-1-30-vehicles.md` |
| What each of `.p3d`, `config.cpp` and `model.cfg` owns; what to measure before the first in-game cycle; gaps a port inherits | `new-car-day-one.md` |

### Making an imported or procedural model work

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

### Get-in, seats, doors and proxies

| Question | File |
|---|---|
| No get-in prompt, no co-driver or rear seat, no door action; four seats; right-hand drive; choosing a donor; inherited config keys | `invariants-get-in-and-seats.md` |
| The four-link get-in condition chain, action registration, the `Geometry` and `autocenter=0` gate for proxied submodels, which anchor really places the occupant, and why a part's `model=` governs both the fitted part and the loose item | `get-in-actions-and-proxy-pose.md` |
| Proxy placement measured on a reference car, the four-layer contract of detachable parts, the two registrations a vehicle action needs, View Pilot of a shell and proxy car | `proxies-and-get-in.md` |
| Door edges: measuring the missing edge, closing it by script, hood and trunk against a door | `doors-and-panel-edges.md` |
| Why a ripped door, hood or tailgate shows a see-through rim, and what does not close it | `rip-panel-open-rim.md` |
| Letting a rider fire their own weapon from a moving vehicle (the free gunner pattern) | `gunner-shoot-from-vehicle.md` |

### Wheels, engine and handling

| Question | File |
|---|---|
| "No proper selection in geometry", wheels off their hubs, a car that spawns sunk, a wheel facing backwards, a missing axle | `invariants-wheels-and-hubs.md` |
| Engine will not start or stalls, test kits, a car that rolls away, steering ramp, mass, tyre grip, drivetrain ratios, measured sedan launch | `invariants-engine-fluids-and-handling.md` |
| Whether an animation turns the right way: wheels, steering, doors, dials | `animation-sign-and-axis.md` |

### Lights, dashboard and views

| Question | File |
|---|---|
| Lights that do not switch: material paths, hidden selection order and ownership, bulbs, driver exit | `lights.md` |
| An LED or indicator that changes colour, glows and optionally lights the scene: hidden selection, one `.rvmat` per state with `emmisive[]`, the swap from script, a `PointLightBase` on a memory point | `emissive-leds-and-dynamic-lights.md` |
| Dashboard needles and dials: frame and mirror traps, rotation direction, deriving `angle0` and `angle1`, needle build, fuel panel from scratch, night check, the full recipe | `gauge-needles.md` |
| A map on a cockpit screen: render target bridge, satmap tiles, tile overlap, sliding tile window | `cockpit-screens-and-map-tiles.md` |
| What the seated player sees: the res 1100 View Pilot LOD and its proxies; offline first-person viewer traps | `view-pilot-and-first-person.md` |
| An empty inventory preview of a door or part: `rotationFlags` per side, `invview` placement | `inventory-preview.md` |
| Identical textures and server mismatch as false diagnoses; parent-driven selections do not reach a proxy | `materials-and-selections.md` |

### Build, runtime and test

| Question | File |
|---|---|
| `model.cfg` for ODOL against MLOD, reversed wheel spin, proxy drive paths, offline PBO checks (the white vehicle after binarize is in the white-car cookbook of the rip-vehicle-import skill) | `build-packaging-and-debug.md` |
| Proving an animation and new geometry survived binarization: skeleton bones, `sections[]`, section flags, PAA encoding, translation offsets | `animation-bake-and-odol-sections.md` |
| Is the packed PBO the approved artifact; `config.cpp` syntax with `CfgConvert` and canaries; comparing native crashes | `deploy-gates-and-crash-fingerprint.md` |
| Per-tick events, engine state on a passenger's client, visual state on a fresh spawn, a vehicle drawn or exited in the wrong place | `runtime-state-and-sync.md` |
| Network ownership against a forced seat, why writing the pose fights the owner, a custom Pawn frame | `network-physics-ownership.md` |
| Driving, seating and unseating a vehicle from an automated harness; what the server still validates | `test-stand-and-mcp.md` |
| Whether a pose complaint is a perspective artifact; anchoring a HUD marker ray; validating a visual metric | `visual-metrics-and-viewer.md` |
| The per-session history of the imported-car visual gates, items #10(a) to #10(o); what a clean `validate()` and a Blender culling render cannot prove about winding; the sign of a face a script adds or moves | `visual-gates-and-winding.md` |

### Method and history

| Question | File |
|---|---|
| The iteration budget, calibrating a gate before trusting it, what a PASS covers, the habits that stop re-deriving known causes | `method-and-gate-calibration.md` |
| Negative fixtures for import gates, rules promoted from recurring lessons, a config gate is not a visual gate | `process-gates.md` |
| The superseded diagnostic order, kept for vehicles already in flight | `history/legacy-gate-ladder.md`, `history/pre-change-0-gate-ladder.md` |
| The exact text of rules that were later corrected | `history/superseded-family-b-rules.md` |

## Numbered invariants

The checks that recur on every vehicle are numbered. Each one is easy to miss and costly to re-derive, so check them up front. Other files cite them as "invariant N", "preflight #N" or "#N".

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

Items 3, 12 and 21 moved to the family B cookbooks of the rip-vehicle-import skill; the invariant files keep a pointer under each number.

## Cite, then verify

Vehicle config and model values are easy to half-remember. Before writing a class name, a property or a named selection, Grep it in vanilla under `P:\DZ\vehicles\` or in the file a pack file cites. Anchor a new vehicle lesson to a real file with `path:line`, never to memory, and mark a value that could not be checked as "not yet checked on `P:\`".

## On Linux

Everything above is the Windows workflow. On Linux the Proton setup, the measured tool matrix and the pitfalls are in the shared Linux and Proton notes (`skills/_shared/linux-proton.md`); this section only says what changes for vehicle work.

- Pack, sign and binarize with dayzmake 1.0.0 or later, a DayZ fork of armake2 (the shared Linux notes say how to install it): `dayzmake build`, `keygen`, `sign`, and `build --proton-binarize` where needed. Plain armake2 is no substitute: it is built for Arma, its V3 file hash leaves out `*.c` files (dayzmake v1.0.0 includes them) and it lacks the DayZ-only functions dayzmake keeps adding. The shared script `skills/_shared/scripts/dayz-mod-pack.sh` wraps them (`init`, `keygen`, `build [--binarize-models]`, `check`, `publish-hint`). A textured cube built this way on 2026-11-03 matched BI binarize from a `P:` root byte for byte; that is not an in-game ODOL check.
- `P:\` is a plain directory mapped by the shared script `dayz-proton.sh init <dir>` (`skills/_shared/scripts/dayz-proton.sh`); a `P:\<Mod>\...` path in the pack is `<dir>/<Mod>/...`.
- Object Builder and TexView run under Proton: `dayz-proton.sh gui ObjectBuilder <p3d>` and `gui TexView <paa>`. Object Builder opened and displayed a model; editing in it was not exercised. The offline checks are Python and run natively: py3d (`scripts/tools/py3d/`), the model preflight (`scripts/tools/dayz-model-preflight/`) and the 3D viewer (`scripts/tools/dayz-3d-viewer/`).
- In-game checks: the Linux notes of the `dayz-test-ingame` skill (`skills/dayz-test-ingame/references/linux.md`).

## Building, testing and publishing the mod

When the work has to end in a mod that builds, loads and ships (`config.cpp` and `CfgMods`, `requiredAddons`, the PBO and its signature, a boot on a local server, the Workshop), build with `/dayz-build-pbo`, test with `/dayz-launch-test`, and follow the mod development skill (dayz-mod-dev) for the full loop.
