# Generated model pipeline

Generates a DayZ object end to end: the 3D model, its LODs, textures, materials, animations and the config that goes with it, using Blender without its window and the py3d library. The primary path builds geometry in Blender (bevel, subdivision, booleans, Smart UV, an AO bake, LODs) and assembles the `.p3d` with py3d. A fallback path uses py3d alone for quick prototypes.

Follow `skills/_shared/dayz-conventions.md`. This is a workflow with reference files and no script of its own, so it has no preflight gate. The steps that need DayZ Tools or the game run through skills that gate themselves: `/dayz-pack-texture`, `/dayz-build-pbo`, `/dayz-launch-test`.

The model belongs to `dayz-object-builder`. The classes in `config.cpp` are written by `dayz-config-specialist`, the script by `dayz-script-specialist`, vehicles by `dayz-vehicle-specialist`; this file says what the model needs from each.

## What it produces

1. Geometry from Blender headless: bevel, subdivision, boolean cutouts, smooth shading.
2. LODs from the Decimate modifier (LOD0 down to LOD3), subject to the decimation gate below.
3. Smart UV projection and an AO bake from the real geometry.
4. Procedural textures with Pillow and OpenSimplex: coherent noise, FBM, several composited layers.
5. A `.p3d` written directly with py3d: LODs, named selections, memory points.
6. The full LOD set: Resolution, Geometry, Fire Geometry, View Geometry, Memory, and a shadow LOD only when asked for.
7. Animations: a `model.cfg` with skeleton, bones, and rotation, translation and hide animations.
8. Config: the `CfgVehicles` class with `AnimationSources`, `DamageSystem` and `hiddenSelections`.
9. Materials: `.rvmat` files, with emissive ones for LEDs and indicators.
10. The addon layout: `$PBOPREFIX$` and a folder structure ready to pack.
11. An interactive 3D preview (a Three.js HTML page) so the user can approve the design before the real model is built.

## Gates that come before any work

- **Decimation gate.** Any decimation whose result the player sees (LOD0 or another visual LOD) is flagged to the user and approved before it runs; by default the user decimates by hand. Decimating without asking is acceptable only for collision and view LODs.
- **Provenance (Phase 0).** Before editing a `.p3d`, `.paa` or `.rvmat` that came from outside the repo, compare the live asset with the latest delivery and settle every difference: `artist-returns.md`.
- **Artist return preflight.** Before deploying a `.p3d` that came back from an artist, run the offline preflight in the same file. An exporter keeps what is visible and drops the rest, so an untouched LOD is suspicious, not safe.
- **Vehicles.** A wheeled vehicle built from scratch shows what a real DayZ vehicle carries (wheel hubs in Geometry, crew proxies in View Geometry, damage zones in Fire Geometry, lights, animation sources) one error at a time in game unless the full anatomy is extracted first. Read the structural parity and vehicle config notes in the vehicles pack (`skills/_shared/vehicles/vehicle-structural-parity.md` and `skills/_shared/vehicles/vehicle-config-and-modelcfg.md`) before baking, and hand tuning, wheel simulation and dedicated server problems to `dayz-vehicle-specialist`. For an imported vehicle follow the vehicle import profile (`skills/_shared/vehicles/rip-family-b-runbook.md`), not the generic Smart UV and decimation defaults here.

## Setup

- **py3d, the DayZ `.p3d` library in this repo**, version 1.6.0 or later: `python -m pip install -e scripts\tools\py3d`. Never `pip install py3d` (an unrelated library on PyPI). `py3d-assembly-rules.md` has the check that the right one is active.
- **Blender** on the path, for Path A (`blender --version`).
- **Python packages** for the textures: `python -m pip install opensimplex pillow`.

## Pipeline

### Path A: Blender headless plus py3d assembly (primary)

1. **Define the object.** The user describes what the object does, how it looks and what moves. Identify the static parts, the animated parts, the interaction points and, for a powered device, its connections. Pick a recipe from `device-recipes.md` or define a new one.
2. **Preview (optional, recommended).** Build a Three.js HTML page that shows the object in 3D with toggles for its states (on, off, open, closed). Let the user approve the design before the real model is generated.
3. **Geometry in Blender headless** (`blender-headless.md`). Build from primitives and modifiers (bevel, subdivision, boolean), shade curved surfaces smooth, run Smart UV Project, and export LOD0 as OBJ (full detail, about 1,500 to 2,000 vertices for a small object). Generate LOD1 to LOD3 with Decimate at ratios 0.50, 0.25 and 0.12 once the user has approved them (decimation gate). Optionally bake an AO map from the real geometry (Cycles, 64 samples or more). Save the `.blend` as a reference.
4. **Procedural textures** (`_shared/textures/procedural-textures.md`). Use OpenSimplex coherent noise with FBM, composited in layers: base, flow, grain, micro, wear, sparse detail. If an AO map was baked, multiply it into the diffuse. Generate `_co`, `_nohq` and `_smdi` maps per surface at 512x512 as `.png`. Never use `random()` per pixel for a surface pattern.
5. **Assemble the `.p3d` with py3d** (`py3d-generation.md`). Read the Blender OBJ exports into the visual LODs (0.0, 1.0, 4.0, 8.0). Build the Geometry, Fire Geometry and View Geometry LODs as convex boxes with py3d primitives; they do not need Blender quality. Build the Memory LOD with the animation axes, port points, `actionPos` and `ce_center`. Add the named selections across all LODs, assign the texture and material paths (`.paa`, `.rvmat`), write the file and read it back to verify.
6. **Materials.** A standard `.rvmat` per surface type, emissive materials for LEDs (green, red, off), and penetration materials on the collision LODs (`model-config-and-packing.md`, `_shared/textures/rvmat-mod-patterns.md`).
7. **`model.cfg` and config.** `CfgSkeletons`, `CfgModels` and the animations (`_shared/animation/model-cfg-device-examples.md`); the `CfgVehicles` class with `AnimationSources`, `hiddenSelections` and `DamageSystem` goes to `dayz-config-specialist`. The `CfgModels` class name must match the `.p3d` file name.
8. **Package.** `$PBOPREFIX$` and the folder structure, under `workspace/<ModName>/`.

Then convert the `.png` files with `/dayz-pack-texture`, audit with `/dayz-p3d-audit`, pack with `/dayz-build-pbo` and test with `/dayz-launch-test`.

### Path B: py3d only (fallback, quick prototypes)

Use it when Blender is not available or the geometry is very simple (cubes, basic cylinders). Everything is generated in Python: lower quality, no dependency beyond pip. Follow steps 1 to 8 but skip step 3 and build the geometry in step 5 from py3d primitives (`py3d-generation.md`).

### Path C: manual Blender workflow for an outside mesh

Use it when the user already has a complex mesh from somewhere else (`.fbx`, `.obj`, `.glb`) that cannot be generated: scale and orientation, cleanup, decimation, keeping its textures. `blender-external-mesh.md`, after `blender-import-preflight.md`.

### Path D: viewer and tagger for an outside model

When the user imports a model and needs to label its parts (animated, static, where an axis sits), use the model tools instead of building a viewer by hand: the p3d inspector of `/dayz-model-tools` to inspect, edit and round trip a `.p3d` (`tools-p3d-inspector.md`), or the 3D viewer tool for a textured view (`tools-3d-viewer.md`). The config is then generated from the labels.

## Rules that matter most

The full list of 21 rules, with the measurements behind them, is `generated-model-rules.md`. The ones that cause most failures:

- Geometry, Fire Geometry and View Geometry components are convex and closed, named `ComponentNN`; mass sits on the Geometry LOD only.
- The LOD resolution values are exact (`skills/_shared/conventions/assets.md`); a wrong value means the engine does not see that LOD type.
- Memory points are single vertices; an animation axis is exactly two points.
- Every collision face has a penetration `.rvmat`; placed objects carry `autocenter=0`.
- Blender to DayZ is a reflection: map `(x,y,z)` to `(x,z,y)`, keep the face order, negate the normals. Check an asymmetric feature in game, because no winding check can see a mirrored model.
- An attachment needs three things: the proxy face and selection in the parent, the proxy `.p3d`, and the `CfgNonAIVehicles` class. Since 1.30 the proxy triangle also goes in View Geometry.
- Read every `.p3d` back with py3d after writing it.

## What to read

| Question | Read |
|---|---|
| What are the hard rules, and which LOD values do I use? | `generated-model-rules.md` |
| Something is wrong with the result: which cause, which fix? | `generated-model-troubleshooting.md` |
| How do I drive Blender without its window (primitives, modifiers, UVs, AO bake, LODs, OBJ export)? | `blender-headless.md` |
| What must I check before working on an imported FBX or reshaping an imported mesh? | `blender-import-preflight.md` |
| How do I clean up and export a mesh that came from another tool? | `blender-external-mesh.md` |
| Why is the axis conversion a reflection, and how do I verify winding on collision LODs, glTF sources and open geometry? | `axes-and-winding.md` |
| How do I write a `.p3d` with py3d (API, LOD build order, proxies, reading and diagnosing a file, a collision hull, checking baked mass offline with `binarize.exe`)? | `py3d-generation.md` |
| Which py3d do I install, where may mass sit, how do I replace a section safely, and what does the validator's axis finding mean? | `py3d-assembly-rules.md` |
| What goes in each LOD, and how do I keep a big building's collision inside Binarize's limits? | `lods-authoring.md` |
| Which memory points and named selections does a model need, how do proxy selections work, and how are the cable ports of a power grid mod named? | `memory-and-selections-authoring.md` |
| How do I write the `model.cfg` skeleton and animations, and drive them? | `_shared/animation/model-cfg-device-examples.md` |
| What does the model need in `config.cpp`, which proxy classes, which `.rvmat`, and how is it packed? | `model-config-and-packing.md` |
| How do I generate `_co`, `_nohq` and `_smdi` maps with coherent noise? | `_shared/textures/procedural-textures.md` |
| Which material recipe fits: flat color, damage overlay, lit panel, glass, bright emissive? | `_shared/textures/rvmat-mod-patterns.md` |
| How do I give one mesh several tiling detail textures (Multi shader, mask, second UV set, `uvTransform`)? | `multi-rvmat-texturing.md` |
| What changed in 1.30 (View Geometry proxies, `-cacheP3D`, `disableSimulation`, `liquid_source`, ODOL v56)? | `dayz-1-30-models.md` |
| An artist sent a `.p3d` back, or a binary came from outside: what do I check before using it? | `artist-returns.md` |
| Is there a worked object specification I can adapt (button, switch, generator, cable, junction box)? | `device-recipes.md` |
| Cookware, a cable segment, or a weapon held in the hands: what was measured? | `domain-recipes.md` |
| Is this binarize or proxy fault a known open one that is not yet confirmed? | `unconfirmed-findings.md` |
| What changes on Linux? | `skills/_shared/linux-proton.md` (Blender and the model tools are a row of section 1); in-game checks in `skills/dayz-launch-test/references/linux.md` |

Facts about what vanilla models carry are in this pack, checked on `P:\`: `README.md` (LODs, memory points, named properties, proxies, selections, doors).

## Reading the evidence labels

The reference files mark how each statement was established: `[EXACT]` measured or read from a file, `[OFFLINE MEASURED]` measured without the game, `[CHANGELOG]` stated by an official changelog only, `[DESIGN]` a rule derived from those, `[UNVERIFIED]` not confirmed. Most measurements were made on mod models (power grid mod devices, a quad, a motorcycle, imported weapons), which is third-party mod behaviour, not vanilla; a line that cites `P:\` was checked against vanilla.

## Acceptance

A rendered view is not acceptance. A model is accepted when `/dayz-p3d-audit` reports no CRITICAL finding on the MLOD and, wherever collision, actions or attachments matter, the object was spawned and checked in game. A clean py3d read back, a matching digest or a passing winding check does not prove the model will spawn (`py3d-assembly-rules.md`, "Spawn remains an engine gate").

Before reading a vanilla 1.30 model with an ODOL reader, read the version in its header: vanilla models are ODOL v56 since 1.30 (v54 in 1.29), and so are the models DayZ Tools binarizes since its update of 2026-10-15 (`dayz-1-30-models.md`).

## After the model

When the work has to end in a mod that builds, loads and ships (`config.cpp` and `CfgMods`, `requiredAddons`, the PBO and its signature, a boot on a local server, the Workshop), continue with `/dayz-lint`, `/dayz-build-pbo`, `/dayz-launch-test` and `/dayz-release-pack`.
