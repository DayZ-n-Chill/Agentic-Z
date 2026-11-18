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
