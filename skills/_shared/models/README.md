# Model and LOD pack

Reference for `dayz-object-builder`: what a DayZ `.p3d` needs inside, LOD by LOD, and how to run the model tools. The model side of an animated door is in the animation pack (`_shared/animation/doors.md`). Open only the file the task needs. Tier 2 still applies on top: the LOD resolution table lives in `_shared/conventions/assets.md` and is not repeated here.

Vanilla models under `P:\DZ\` are binarized ODOL, which Object Builder and `/dayz-p3d-audit` can't open. The vanilla facts in this pack come from reading the plain text that ODOL files still carry: the LOD resolution list in the file header, and the names of selections, memory points, named properties and proxies. Each fact names the model or the scan it came from. Where a rule is Object Builder or Binarize format knowledge that no vanilla file on `P:\` shows, the file says so.

| Question | Open |
|---|---|
| Which LODs does a model need, in what order, and how are the visual LODs numbered? What are the rules for Geometry, Fire Geometry and View Geometry? | `lods.md` |
| Which memory points does vanilla script look for, and how are axes built? | `memory-points.md` |
| Which named properties does vanilla set, and where does mass go? | `named-properties.md` |
| How is a proxy named and placed? | `proxies.md` |
| How does a proxy triangle become a position and a facing, and why does an attached model come out rotated or on the floor (clothing on a static host, crew seats, body-part and weapon attachment proxies)? | `proxy-frames.md` |
| What is a named selection, which LOD does each kind belong in, who reads it, and how do tools lose it? | `selections.md` |
| Which selections and points does a building, ladder or well carry (door leaves, ladder schemes, the Paths LOD, loot and rain sound points, `liquid_source`)? | `building-selections.md` |
| How are UVs stored in a `.p3d`, which UV set does each material stage read, and how is an in-game texture fault traced back to the UVs? | `uv-mapping.md` |
| How does vanilla texture one mesh with up to four tiling surfaces through a `Multi` material, and what must the model carry for it? | `multi-rvmat-texturing.md` |
| What does a door need in the model, and who writes the rest? | `_shared/animation/doors.md` (the door subject lives in the animation pack) |

| How are model axes mapped from Blender to DayZ, and how must visual and collision LODs be wound? | `axes-and-winding.md` |
| How do I build a model in Blender over MCP without exploded parts, scale errors, broken booleans or bare boxes (the helper library, the detail pass, the integrity gate)? | `blender-assembly.md` |
| How do I scan a reference image zone by zone for the detail list, and where does each texture-side detail land? | `blender-detail-scan.md` |
| How do I check a Blender model by eye: multi-angle captures, the defect checklist, the bounded fix loop, the delta check, and catching a winding flip a lit render hides? | `blender-visual-review.md` |
| How do I take an AI-generated mesh (image or text to 3D) to a DayZ prop: generators, retopology, bake, handoff, writing the MLOD? | `ai-generation.md` |
| How do I run a production model build as a gated pipeline (intake, dossier, plan with tests, build, roast, fix loop, ship gate)? | `generation-harness.md` |
| The Phase 1 research dossier to fill in before any geometry is built | `generation-dossier-template.md` |
| The scored rubric for the adversarial roast: 8 categories, evidence, defect list format | `generation-roast-rubric.md` |
| How is a new object generated end to end (Blender headless or py3d alone, the gates, the steps, acceptance)? | `generated-model-pipeline.md` |
| What are the 21 rules a generated model must meet? | `generated-model-rules.md` |
| A generated model is wrong in game: which cause, which fix? | `generated-model-troubleshooting.md` |
| How do I drive Blender without its window (primitives, modifiers, UVs, AO bake, LODs, OBJ export)? | `blender-headless.md` |
| What must I check before working on an imported FBX or reshaping an imported mesh? | `blender-import-preflight.md` |
| How do I clean up and export a mesh that came from another tool? | `blender-external-mesh.md` |
| How do I write a `.p3d` with py3d (API, build order, proxies, diagnostics, repairs, a collision hull, baked mass)? | `py3d-generation.md` |
| Which py3d to install, where mass may sit, how to replace a section safely, what the validator's axis finding means | `py3d-assembly-rules.md` |
| What goes in each LOD of a generated model, the decimation measurements, FBX LOD object names, and keeping a large building's collision inside Binarize's limits | `lods-authoring.md` |
| How to create memory points and named selections, where each must be present, the three parts of a proxy system, and a cable port naming scheme | `memory-and-selections-authoring.md` |
| What the model needs in `config.cpp`, the addon layout, proxy attachment classes, and packing | `model-config-and-packing.md` |
| What 1.30 changed for models (View Geometry proxies, `-cacheP3D`, `disableSimulation`, `liquid_source`, ODOL v56) | `dayz-1-30-models.md` |
| An artist sent a `.p3d` back, or a binary came from outside: what to check before using it | `artist-returns.md` |
| Worked specifications of electrical devices (button, switch, generator, cable, junction box) to adapt | `device-recipes.md` |
| Cookware, a client side cable segment, an asset posed in the hands: what was measured | `domain-recipes.md` |
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
| A clean, readable UV atlas for a hard-surface mesh, the exact overlap gate and the traps | `tools-uv-atlas.md` |
| What a mesh must pass before unwrapping, seams, stitching and splitting islands | `tools-uv-mesh-health.md` |
| Re-unwrapping a model that already ships, or one atlas shared between LODs | `tools-uv-multi-lod-atlas.md` |
| A paint atlas for an organic one-shell mesh by projection | `tools-uv-organic-photograph.md` |
| What to measure on the UVs of an assembled `.p3d` | `tools-uv-mlod-audit.md` |
| PartUV: install, run and how it scored | `tools-uv-partuv.md` |
| Other automatic unwrap tools and why they were not chosen | `tools-uv-tool-survey.md` |
| A `.p3d` with its textures to a `.glb` and an HTML page; `.paa` to `.png` | `tools-3d-viewer.md` |
| Which PAA types decode, and how an RVMAT becomes a page material | `tools-3d-viewer-formats.md` |
| Which Three.js version and loading method a generated page can use, and how to test it | `tools-threejs-viewers.md` |
| The plan (not built) for playing `model.cfg` animations and LED states in the viewer | `tools-3d-viewer-states.md` |
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
