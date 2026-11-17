---
name: dayz-model-pipeline
description: "Builds a complete DayZ object from scratch or from an outside mesh: geometry in Blender headless, a .p3d assembled with py3d (visual, Geometry, Fire Geometry, View Geometry and Memory LODs, named selections, memory points, proxies), procedural textures, .rvmat materials, model.cfg animations and the config.cpp entries the model needs. Use when the user wants a new model generated, or a Blender, FBX, OBJ or GLB mesh turned into a game ready .p3d, or asks about LODs, memory points, named selections, model.cfg, procedural textures, .rvmat materials, the Blender to DayZ axis conversion and face winding, an artist's returned .p3d, cacheP3D, liquid_source, disableSimulation, a View Geometry attachment proxy, or LF_PowerGrid objects."
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-model-pipeline

Generates a DayZ object end to end: the 3D model, its LODs, textures, materials, animations and the config that goes with it, using Blender without its window and the py3d library. The primary path builds geometry in Blender (bevel, subdivision, booleans, Smart UV, an AO bake, LODs) and assembles the `.p3d` with py3d. A fallback path uses py3d alone for quick prototypes.

Follow `skills/_shared/dayz-conventions.md`. This skill is a workflow with reference files; it ships no script of its own, so it has no preflight gate. The steps that need DayZ Tools or the game run through skills that gate themselves: `/dayz-pack-texture`, `/dayz-build-pbo`, `/dayz-launch-test`.

The model belongs to `dayz-object-builder`. The classes in `config.cpp` are written by `dayz-config-specialist`, the script by `dayz-script-specialist`, vehicles by `dayz-vehicle-specialist`; this skill says what the model needs from each.

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
- **Provenance (Phase 0).** Before editing a `.p3d`, `.paa` or `.rvmat` that came from outside the repo, compare the live asset with the latest delivery and settle every difference: `references/artist-return-and-provenance.md`.
- **Artist return preflight.** Before deploying a `.p3d` that came back from an artist, run the offline preflight in the same file. An exporter keeps what is visible and drops the rest, so an untouched LOD is suspicious, not safe.
- **Vehicles.** A wheeled vehicle built from scratch shows what a real DayZ vehicle carries (wheel hubs in Geometry, crew proxies in View Geometry, damage zones in Fire Geometry, lights, animation sources) one error at a time in game unless the full anatomy is extracted first. Read the structural parity and vehicle config notes in the vehicles pack (`_shared/vehicles/README.md`) before baking, and hand tuning, wheel simulation and dedicated server problems to `dayz-vehicle-specialist`. For an imported vehicle follow the vehicle import profile (the `rip-vehicle-import` skill), not the generic Smart UV and decimation defaults here.

## Setup

- **py3d, the DayZ fork in this repo**, version 1.6.0 or later: `python -m pip install -e scripts\tools\py3d`. Never `pip install py3d` (an unrelated library on PyPI). `references/py3d-assembly-rules.md` has the check that the right one is active.
- **Blender** on the path, for Path A (`blender --version`).
- **Python packages** for the textures: `python -m pip install opensimplex pillow`.

## Pipeline

### Path A: Blender headless plus py3d assembly (primary)

1. **Define the object.** The user describes what the object does, how it looks and what moves. Identify the static parts, the animated parts, the interaction points and, for a powered device, its connections. Pick a recipe from `references/lfpg-recipes.md` or define a new one.
2. **Preview (optional, recommended).** Build a Three.js HTML page that shows the object in 3D with toggles for its states (on, off, open, closed). Let the user approve the design before the real model is generated.
3. **Geometry in Blender headless** (`references/blender-headless.md`). Build from primitives and modifiers (bevel, subdivision, boolean), shade curved surfaces smooth, run Smart UV Project, and export LOD0 as OBJ (full detail, about 1,500 to 2,000 vertices for a small object). Generate LOD1 to LOD3 with Decimate at ratios 0.50, 0.25 and 0.12 once the user has approved them (decimation gate). Optionally bake an AO map from the real geometry (Cycles, 64 samples or more). Save the `.blend` as a reference.
4. **Procedural textures** (`references/procedural-textures.md`). Use OpenSimplex coherent noise with FBM, composited in layers: base, flow, grain, micro, wear, sparse detail. If an AO map was baked, multiply it into the diffuse. Generate `_co`, `_nohq` and `_smdi` maps per surface at 512x512 as `.png`. Never use `random()` per pixel for a surface pattern.
5. **Assemble the `.p3d` with py3d** (`references/py3d-direct-generation.md`). Read the Blender OBJ exports into the visual LODs (0.0, 1.0, 4.0, 8.0). Build the Geometry, Fire Geometry and View Geometry LODs as convex boxes with py3d primitives; they do not need Blender quality. Build the Memory LOD with the animation axes, port points, `actionPos` and `ce_center`. Add the named selections across all LODs, assign the texture and material paths (`.paa`, `.rvmat`), write the file and read it back to verify.
6. **Materials.** A standard `.rvmat` per surface type, emissive materials for LEDs (green, red, off), and penetration materials on the collision LODs (`references/config-and-packing.md`, `references/rvmat-patterns.md`).
7. **`model.cfg` and config.** `CfgSkeletons`, `CfgModels` and the animations (`references/animations.md`); the `CfgVehicles` class with `AnimationSources`, `hiddenSelections` and `DamageSystem` goes to `dayz-config-specialist`. The `CfgModels` class name must match the `.p3d` file name.
8. **Package.** `$PBOPREFIX$` and the folder structure, under `workspace/<ModName>/`.

Then convert the `.png` files with `/dayz-pack-texture`, audit with `/dayz-p3d-audit`, pack with `/dayz-build-pbo` and test with `/dayz-launch-test`.

### Path B: py3d only (fallback, quick prototypes)

Use it when Blender is not available or the geometry is very simple (cubes, basic cylinders). Everything is generated in Python: lower quality, no dependency beyond pip. Follow steps 1 to 8 but skip step 3 and build the geometry in step 5 from py3d primitives (`references/py3d-direct-generation.md`).

### Path C: manual Blender workflow for an outside mesh

Use it when the user already has a complex mesh from somewhere else (`.fbx`, `.obj`, `.glb`) that cannot be generated: scale and orientation, cleanup, decimation, keeping its textures. `references/blender-workflow.md`, after `references/blender-import-preflight.md`.

### Path D: viewer and tagger for an outside model

When the user imports a model and needs to label its parts (animated, static, where an axis sits), use the sibling skills instead of building a viewer by hand: `dayz-p3d-inspector` to inspect, edit and round trip a `.p3d`, or `/dayz-3d-viewer` for a textured 3D view. The config is then generated from the labels.

## Rules that matter most

The full list of 21 rules, with the measurements behind them, is `references/critical-rules.md`. The ones that cause most failures:

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
| What are the hard rules, and which LOD values do I use? | `references/critical-rules.md` |
| Something is wrong with the result: which cause, which fix? | `references/troubleshooting.md` |
| How do I drive Blender without its window (primitives, modifiers, UVs, AO bake, LODs, OBJ export)? | `references/blender-headless.md` |
| What must I check before working on an imported FBX or reshaping an imported mesh? | `references/blender-import-preflight.md` |
| How do I clean up and export a mesh that came from another tool? | `references/blender-workflow.md` |
| Why is the axis conversion a reflection, and how do I verify winding on collision LODs, glTF sources and open geometry? | `references/axes-and-winding.md` |
| How do I write a `.p3d` with py3d (API, LOD build order, proxies, reading and diagnosing a file, a collision hull, checking baked mass offline with `binarize.exe`)? | `references/py3d-direct-generation.md` |
| Which py3d do I install, where may mass sit, how do I replace a section safely, and what does the validator's axis finding mean? | `references/py3d-assembly-rules.md` |
| What goes in each LOD, and how do I keep a big building's collision inside Binarize's limits? | `references/lods-and-geometry.md` |
| Which memory points and named selections does a model need, how do proxy selections work, and how are LF_PowerGrid cable ports named? | `references/memory-and-selections.md` |
| How do I write the `model.cfg` skeleton and animations, and drive them? | `references/animations.md` |
| What does the model need in `config.cpp`, which proxy classes, which `.rvmat`, and how is it packed? | `references/config-and-packing.md` |
| How do I generate `_co`, `_nohq` and `_smdi` maps with coherent noise? | `references/procedural-textures.md` |
| Which material recipe fits: flat color, damage overlay, lit panel, glass, bright emissive? | `references/rvmat-patterns.md` |
| How do I give one mesh several tiling detail textures (Multi shader, mask, second UV set, `uvTransform`)? | `references/multi-rvmat-section-texturing.md` |
| What changed in 1.30 (View Geometry proxies, `-cacheP3D`, `disableSimulation`, `liquid_source`, ODOL v56)? | `references/dayz-1-30-model-pipeline.md` |
| An artist sent a `.p3d` back, or a binary came from outside: what do I check before using it? | `references/artist-return-and-provenance.md` |
| Is there a worked object specification I can adapt (button, switch, generator, cable, junction box)? | `references/lfpg-recipes.md` |
| Cookware, a cable segment, or a weapon held in the hands: what was measured? | `references/domain-recipes.md` |
| Has the community reported this binarize or proxy fault? | `references/community-findings.md` |
| What changes on Linux? | `references/linux.md` |

Facts about what vanilla models carry are in the model pack, checked on `P:\`: `skills/_shared/models/README.md` (LODs, memory points, named properties, proxies, selections, doors).

## Reading the evidence labels

The reference files mark where each statement comes from: `[EXACT]` measured or read from a file, `[OFFLINE MEASURED]` measured without the game, `[CHANGELOG]` stated by an official changelog only, `[DESIGN]` a rule derived from those, `[UNVERIFIED]` not confirmed. Codes such as SP-246 and LL-504 are the source author's ticket and lesson numbers; they are kept so that the files can refer to each other and to the other imported skills. Most measurements were made on the author's own mods (LF_PowerGrid, LFQuad, LFDucati, the A6 weapons); a line that cites `P:\` was checked against vanilla here.

## Acceptance

A rendered view is not acceptance. A model is accepted when `/dayz-p3d-audit` reports no CRITICAL finding on the MLOD and, wherever collision, actions or attachments matter, the object was spawned and checked in game. A clean py3d read back, a matching digest or a passing winding check does not prove the model will spawn (`references/py3d-assembly-rules.md`, "Spawn remains an engine gate").

Before reading a vanilla 1.30 model with an ODOL reader, read the version in its header: vanilla models are ODOL v56 since 1.30 (v54 in 1.29), and so are the models DayZ Tools binarizes since its update of 2026-10-15 (`references/dayz-1-30-model-pipeline.md`).

## After the model

When the work has to end in a mod that builds, loads and ships (`config.cpp` and `CfgMods`, `requiredAddons`, the PBO and its signature, a boot on a local server, the Workshop), continue with `/dayz-lint`, `/dayz-build-pbo`, `/dayz-launch-test` and `/dayz-release-pack`.
