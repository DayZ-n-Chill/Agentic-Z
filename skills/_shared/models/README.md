# Model and LOD pack

Reference for `dayz-object-builder`: what a DayZ `.p3d` needs inside, LOD by LOD, and how to run the model tools. The model side of an animated door is in the animation pack (`_shared/animation/doors.md`). Open only the file the task needs. Tier 2 still applies on top: the LOD resolution table lives in `_shared/conventions/assets.md` and is not repeated here.

Vanilla models under `P:\DZ\` are binarized ODOL, which Object Builder and `/dayz-p3d-audit` can't open. The vanilla facts in this pack come from reading the plain text that ODOL files still carry: the LOD resolution list in the file header, and the names of selections, memory points, named properties and proxies. Each fact names the model or the scan it came from. Where a rule is Object Builder or Binarize format knowledge that no vanilla file on `P:\` shows, the file says so.

| Question | Open |
|---|---|
| Which LODs does a model need, in what order, and how are the visual LODs numbered? What are the rules for Geometry, Fire Geometry and View Geometry? | `lods.md` |
| Which memory points does vanilla script look for, how are they made, and how are axes built and placed? | `memory-points.md` |
| Which named properties does vanilla set, and where does mass go? | `named-properties.md` |
| How is a proxy named and placed? | `proxies.md` |
| How does a proxy triangle become a position and a facing, and why does an attached model come out rotated or on the floor (clothing on a static host, crew seats, body-part and weapon attachment proxies)? | `proxy-frames.md` |
| What is a named selection, which LOD does each kind belong in, who reads it, and how do tools lose it? | `selections.md` |
| Which selections and points does a building, ladder or well carry (door leaves, ladder schemes, the Paths LOD, loot and rain sound points, `liquid_source`)? | `building-selections.md` |
| How are UVs stored in a `.p3d`, which UV set does each material stage read, and how is an in-game texture fault traced back to the UVs? | `uv-mapping.md` |
| How does vanilla texture one mesh with up to four tiling surfaces through a `Multi` material, and what must the model carry for it? | `multi-rvmat-texturing.md` |
| What does a door need in the model, and who writes the rest? | `_shared/animation/doors.md` (the door subject lives in the animation pack) |
| How are model axes mapped from Blender to DayZ, and how must visual and collision LODs be wound? | `axes-and-winding.md` |
| How do I build a model in Blender over MCP without exploded parts, wrong sizes, broken booleans or bare boxes (the helper library, joint and detail planning, the geometry rules, the normal bake)? | `blender-assembly.md` |
| What do I check after each part of a Blender build, how do I finish the scene, and why does a render over MCP show the old mesh? | `blender-assembly-checks.md` |
| How do I scan a reference image zone by zone for the detail list, and where does each texture detail land? | `blender-detail-scan.md` |
| How do I review a Blender model by eye: the capture, the fix loop and its stop rule, checking that a fix landed? | `blender-visual-review.md` |
| What do I look for in the renders (orientation, scale, normals, animated parts, a vanilla model, a reference photo)? | `blender-review-checklist.md` |
| Why can't a Blender render judge DayZ winding, and which two Blender checks still catch a flip? | `blender-winding-flips.md` |
| How do I take a generated mesh (image or text to 3D) to a DayZ prop: generators, retopology, bake, handoff, writing the MLOD? | `ai-generation.md` |
| How do I take a production model from the brief to the packed file in checked stages (research sheet, plan with tests, build, fault review, fixes, final check)? | `model-build-stages.md` |
| How is a new object generated end to end (Blender and py3d or py3d alone, what to ask first, the steps, when it is done)? | `generated-model-pipeline.md` |
| Which rules must a generated model meet, and which LOD resolution values does it use? | `generated-model-rules.md` |
| A generated model is wrong in game: which cause, which fix? | `generated-model-troubleshooting.md` |
| How do I drive Blender without its window (starting it, primitives, modifiers, UVs, materials, the AO bake)? | `blender-headless.md` |
| How do I export OBJ files for py3d from a Blender script, make the LOD set, and avoid losing data on export? | `blender-headless-export.md` |
| What must I check before working on an imported FBX or reshaping an imported mesh? | `blender-import-preflight.md` |
| How do I clean up and export a mesh that came from another tool? | `blender-external-mesh.md` |
| How do I write a `.p3d` with py3d (the API, LOD values, selections, Memory LOD points, build order, the checklist)? | `py3d-generation.md` |
| How do I map Blender's Z up geometry into a `.p3d` without mirroring it, and when may a script reverse faces? | `py3d-axis-map.md` |
| How do I write a proxy triangle and a minimal proxy model with py3d? | `py3d-proxies.md` |
| How do I read an existing MLOD with py3d: LODs, faces, selections, bounds, texture paths? | `py3d-reading.md` |
| Which py3d checks and repairs catch a model off centre, axes swapped between LODs, bad UVs or winding that disagrees with the normals? | `py3d-shape-checks.md` |
| Which py3d checks catch broken proxies, selections missing from collision LODs and collision LODs without `autocenter`, materials or mass? | `py3d-part-checks.md` |
| How do I check baked mass offline with `binarize.exe`, build a collision LOD from a convex hull, and find needle triangles rays pass through? | `py3d-collision-and-mass.md` |
| Which py3d to install, where mass may sit, how to replace part of a LOD safely, what the validator's axis finding means | `py3d-assembly-rules.md` |
| How do I reduce a visual LOD, stay within the vertex and normal limits, name Blender objects for the FBX import, and keep the LOD count down? | `lods-authoring.md` |
| A very large building with rooms inside: collision that follows the walls, and Binarize rejecting the collision LODs with or without a message | `building-collision-limits.md` |
| Where each named selection must be present, the three parts of a proxy, and a cable port naming scheme | `memory-and-selections-authoring.md` |
| What the model needs in `config.cpp`, the addon layout, packing and testing | `model-config-and-packing.md` |
| How is the `CfgNonAIVehicles` class of an attachment proxy named, and why does an item need its own? | `proxy-attachment-config.md` |
| What does a Super `.rvmat` for a new model hold, stage by stage, and how does a part glow? | `model-material-file.md` |
| What DayZ 1.30 changed for models (View Geometry proxies, `-cacheP3D`, `disableSimulation`, `liquid_source`, ODOL v56) | `dayz-1-30-models.md` |
| An artist sent a `.p3d` back, or a binary came from outside: what to check before using it | `artist-returns.md` |
| Worked specifications of electrical devices to adapt: shared design, budgets, names, a template | `device-recipes.md` |
| A push button and a wall switch, part by part | `device-recipes-controls.md` |
| A battery adapter, a floor generator and a cable segment, part by part | `device-recipes-power.md` |
| A six output sorter and a junction box, part by part | `device-recipes-distribution.md` |
| Cookware on vanilla heat sources, a client side cable segment, a weapon posed in the hands | `domain-recipes.md` |
| Binarize and proxy faults reported but not confirmed | `unconfirmed-findings.md` |

## Model tools

How to run the scripts of `/dayz-model-tools` and what was measured with them. Tool behaviour, not game facts.

| Question | Open |
|---|---|
| Look inside a `.p3d`, drag memory points or axis ends, rebuild it from a Recipe | `tools-p3d-inspector.md` |
| The Recipe JSON fields and what the builder writes | `tools-p3d-inspector-recipe.md` |
| The inspector page: layers, colours, dragging, export | `tools-p3d-inspector-viewer.md` |
| What an extract and rebuild can lose, and how to test for it | `tools-p3d-inspector-round-trip.md` |
| A proxy renders at the floor, floats or turns: extract, rewrite, edit and write back the proxy triangles | `tools-proxy-align.md` |
| The offline winding and normal gate: what it reads, its verdicts, what a PASS does not cover | `tools-winding-gate.md` |
| A clean, readable UV atlas for a hard-surface mesh and the exact overlap gate | `tools-uv-atlas.md` |
| Which Blender, SLIM, fold guard and Windows traps break the clean UV atlas pipeline | `tools-uv-atlas-traps.md` |
| What a mesh must pass before unwrapping, seams, stitching and splitting islands | `tools-uv-mesh-health.md` |
| Re-unwrapping a model that already ships, or one atlas shared between LODs | `tools-uv-multi-lod-atlas.md` |
| A paint atlas for an organic one-shell mesh by projection | `tools-uv-organic-photograph.md` |
| What to measure on the UVs of an assembled `.p3d` | `tools-uv-mlod-audit.md` |
| PartUV: install, run and how it scored | `tools-uv-partuv.md` |
| Other automatic unwrap tools and why they were not chosen | `tools-uv-tool-survey.md` |
| A `.p3d` with its textures to a `.glb` and an HTML page; `.paa` to `.png` | `tools-3d-viewer.md` |
| Which PAA types decode, and how an RVMAT becomes a page material | `tools-3d-viewer-formats.md` |
| Which Three.js version and loading method a generated page can use, and how to test it | `tools-threejs-viewers.md` |
| Where a model's moving parts and material states are defined, and the maths of each animation | `tools-3d-viewer-states.md` |
| The plan (not built) for playing `model.cfg` animations and LED states in the viewer | `tools-3d-viewer-states-build.md` |
| A local vision model as a pre-filter on renders: which checklist questions it may answer, how each was calibrated, running `vr_score.py` and `vr_calibrate.py` | `tools-vlm-judge.md` |
| The JSON format of a render checklist and how `--view` routes each question to one image | `tools-vlm-checklist-format.md` |

## Other packs this one leans on

| Topic | Pack |
|---|---|
| Model faults that break a `.p3d` with no engine error | `dayz-p3d-audit/references/p3d-killers.md` |
| Collision faults and probing a LOD from script | `_shared/physics/collision-lods.md` |
| Bones and the `Animations` block in `model.cfg` | `_shared/animation/model-cfg-animations.md` |
| Weapon memory points and selections | `_shared/weapons/model-selections.md` |
| Clothing models and their proxies | `_shared/wearables/references/models-and-proxies.md` |

## After every model change

The user makes the edits in Object Builder and saves the MLOD file. Then run `/dayz-p3d-audit` on that file, with `--model-cfg` and `--config` when the model has them, and read the findings against `dayz-p3d-audit/references/p3d-killers.md`. Fix every CRITICAL finding before the work goes back to the art lead.
