# Generating a model

How a DayZ object is generated end to end: the model, its LODs, textures, materials, animations and config, with Blender run without its window and the py3d library. The main route builds the geometry in Blender and writes the `.p3d` with py3d; a quick route uses py3d alone.

The model belongs to `dayz-object-builder`. The `config.cpp` classes go to `dayz-config-specialist`, script to `dayz-script-specialist`, vehicles to `dayz-vehicle-specialist`; this file says what the model needs from each. `_shared/dayz-conventions.md` applies on top. This is a method with no script of its own; the steps that need DayZ Tools or the game run through skills that check their own setup (`/dayz-pack-texture`, `/dayz-build-pbo`, `/dayz-launch-test`). It names no vanilla fact of its own; those are in the files it points to.

## What it makes

| Part | How |
|---|---|
| Geometry | Blender without its window: bevel, subdivision, boolean cutouts, smooth shading |
| LODs | Decimate from LOD0 to LOD3, with the user's approval (below) |
| UVs and AO | Smart UV Project and an AO bake from the real geometry |
| Textures | Pillow and OpenSimplex: coherent noise, FBM, several layers |
| The `.p3d` | py3d: visual LODs, Geometry, Fire Geometry, View Geometry, Memory, and a shadow LOD only when asked for |
| Animations | A `model.cfg` with skeleton, bones, and rotation, translation and hide animations |
| Config | The `CfgVehicles` class with `AnimationSources`, `DamageSystem` and `hiddenSelections` |
| Materials | `.rvmat` files, emissive ones for LEDs and indicators |
| Addon layout | `$PBOPREFIX$` and a folder tree ready to pack |
| Preview | A Three.js page so the user approves the design before the real model is built |

## Before any work

- **Ask before decimating anything the player sees.** Flag any decimation of LOD0 or another visual LOD to the user and wait for approval; by default the user decimates by hand. Collision and view LODs can be decimated without asking.
- **Files from outside the repo.** Before editing a `.p3d`, `.paa` or `.rvmat` from outside, compare the live asset with the newest delivery and settle every difference; before deploying a `.p3d` an artist sent back, run the offline checks (`artist-returns.md`). An exporter keeps what is visible and drops the rest.
- **Vehicles.** A wheeled vehicle built from scratch reveals what a real DayZ vehicle carries (wheel hubs in Geometry, crew proxies in View Geometry, damage zones in Fire Geometry, lights, animation sources) one error at a time in game unless you read the full layout first. Read `_shared/vehicles/vehicle-structural-parity.md` and `_shared/vehicles/vehicle-config-and-modelcfg.md` before baking, and hand tuning, wheel simulation and dedicated server problems to `dayz-vehicle-specialist`. An imported vehicle follows `_shared/vehicles/ripped-car-proxy-split.md`, not the Smart UV and decimation defaults here.

## Setup

- py3d from this repo, version 1.6.0 or later: `py -m pip install -e scripts\tools\py3d`. Never `pip install py3d`, which is an unrelated library on PyPI; `py3d-assembly-rules.md` shows how to check which one is active.
- Blender on the path for the main route (`blender --version`).
- For textures: `py -m pip install opensimplex pillow`.

## The main route: Blender and py3d

1. **Define the object.** The user says what it does, how it looks and what moves. List the static parts, the moving parts, the interaction points and, for a powered device, its connections. Start from a specification in `device-recipes.md` or write a new one.
2. **Preview.** Optional but worth it: a Three.js page showing the object with toggles for its states (on, off, open, closed), approved by the user before the real model.
3. **Geometry in Blender** (`blender-headless.md`). Build from primitives and modifiers, shade curved surfaces smooth, run Smart UV Project, and export LOD0 as OBJ (about 1,500 to 2,000 vertices for a small object). Once the user approves, make LOD1 to LOD3 with Decimate at 0.50, 0.25 and 0.12. Optionally bake AO (Cycles, 64 samples or more). Save the `.blend`.
4. **Textures** (`_shared/textures/procedural-textures.md`). OpenSimplex noise with FBM in layers: base, flow, grain, micro, wear, sparse detail. Multiply the AO into the diffuse if you baked one. Write `_co`, `_nohq` and `_smdi` per surface at 512x512 as `.png`. Never use `random()` per pixel for a surface.
5. **Write the `.p3d` with py3d** (`py3d-generation.md`). Read the OBJ exports into the visual LODs (`0.0`, `1.0`, `4.0`, `8.0`). Build Geometry, Fire Geometry and View Geometry as convex boxes from py3d primitives. Build Memory with the animation axes, port points, `actionPos` and `ce_center`. Add the named selections across every LOD, set the `.paa` and `.rvmat` paths, write the file and read it back.
6. **Materials.** A standard `.rvmat` per surface, emissive ones for LEDs (green, red, off), and penetration materials on the collision LODs (`model-material-file.md`, `_shared/textures/rvmat-mod-patterns.md`).
7. **`model.cfg` and config.** `CfgSkeletons`, `CfgModels` and the animations (`_shared/animation/device-model-cfg.md`, `_shared/animation/device-animation-patterns.md`). The `CfgModels` class name matches the `.p3d` file name. The `CfgVehicles` class goes to `dayz-config-specialist`.
8. **Package** `$PBOPREFIX$` and the folders under `workspace/<ModName>/`.

Then convert the `.png` files with `/dayz-pack-texture`, audit with `/dayz-p3d-audit`, pack with `/dayz-build-pbo` and test with `/dayz-launch-test`.

## Other routes

| Route | When | How |
|---|---|---|
| py3d alone | No Blender, or very simple geometry (boxes, plain cylinders); lower quality | The main route without step 3, with the geometry built from py3d primitives in step 5 (`py3d-generation.md`) |
| A mesh from elsewhere | The user already has an `.fbx`, `.obj` or `.glb` that cannot be generated | `blender-import-preflight.md`, then `blender-external-mesh.md` |
| Labelling an imported model | The user must mark which parts move and where the axes sit | The p3d inspector of `/dayz-model-tools` (`tools-p3d-inspector.md`), or the 3D viewer for a textured view (`tools-3d-viewer.md`); the config is generated from the labels |

## The rules that fail most

All rules are in `generated-model-rules.md`. The ones that break most models:

- Geometry, Fire Geometry and View Geometry components are convex, closed and named `ComponentNN`; mass sits on Geometry only.
- LOD resolution values are exact; a wrong value hides the LOD type from the engine.
- Memory points are single vertices; an axis is exactly two points.
- Every collision face has a penetration `.rvmat`, and placed objects carry `autocenter=0`.
- Blender to DayZ is a reflection: `(x,y,z)` to `(x,z,y)`, face order kept, normals negated. Check an asymmetric feature in game; no winding check sees a mirror.
- An attachment needs the proxy face and selection in the parent, the proxy `.p3d` and the `CfgNonAIVehicles` class; since 1.30 the proxy triangle also goes in View Geometry.
- Read every `.p3d` back with py3d after writing it.

## Which file to open

| Question | File |
|---|---|
| Which rules must the model meet, and which LOD values do I use? | `generated-model-rules.md` |
| Something is wrong with the result: which cause, which fix? | `generated-model-troubleshooting.md` |
| How do I drive Blender without its window? | `blender-headless.md` |
| What do I check before working on an imported FBX or reshaping a mesh? | `blender-import-preflight.md` |
| How do I clean up and export a mesh from another tool? | `blender-external-mesh.md` |
| Why is the axis map a reflection, and how do I check winding? | `axes-and-winding.md` |
| How do I write a `.p3d` with py3d, check it, and check baked mass with `binarize.exe`? | `py3d-generation.md` |
| Which py3d, where may mass sit, how do I replace a section safely? | `py3d-assembly-rules.md` |
| What goes in each LOD, and how do I keep a big building's collision inside Binarize's limits? | `lods-authoring.md` |
| Which memory points and selections does the model need, and how are cable ports named? | `memory-and-selections-authoring.md` |
| How do I write and drive the `model.cfg` animations? | `_shared/animation/device-model-cfg.md`, then `_shared/animation/device-animation-patterns.md` |
| What does the model need in `config.cpp`, and how is it packed? | `model-config-and-packing.md` |
| How do I make `_co`, `_nohq` and `_smdi` with noise? | `_shared/textures/procedural-textures.md` |
| Which material recipe fits (flat colour, damage, lit panel, glass, emissive)? | `_shared/textures/rvmat-mod-patterns.md` |
| How do I give one mesh several tiling textures? | `multi-rvmat-texturing.md` |
| What changed in 1.30? | `dayz-1-30-models.md` |
| An artist sent a `.p3d` back: what do I check? | `artist-returns.md` |
| Is there a worked specification to adapt (button, switch, generator, cable, junction box)? | `device-recipes.md` |
| Cookware, a cable segment, a weapon in the hands? | `domain-recipes.md` |
| Is this Binarize or proxy fault a known open one? | `unconfirmed-findings.md` |
| What changes on Linux? | `_shared/linux-proton.md`; in-game checks in `skills/dayz-launch-test/references/linux.md` |

What vanilla models carry (LODs, memory points, named properties, proxies, selections) is in this pack's `README.md` files list, cited from `P:\`.

## When a model is done

A render is not acceptance. A model is done when `/dayz-p3d-audit` reports no CRITICAL finding on the MLOD and, wherever collision, actions or attachments matter, the object was spawned and checked in game. A clean py3d read back, a matching hash or a passing winding check does not prove it spawns (`py3d-assembly-rules.md`).

Before reading a 1.30 model with an ODOL reader, read the version in its header: vanilla 1.30 models and models binarized by DayZ Tools for 1.30 are ODOL v56 (`dayz-1-30-models.md`).

To end in a mod that builds, loads and ships, go on with `/dayz-lint`, `/dayz-build-pbo`, `/dayz-launch-test` and `/dayz-release-pack`.
