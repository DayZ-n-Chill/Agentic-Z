---
name: dayz-model-tools
description: "Runs the DayZ model tools on source (MLOD) .p3d and .blend files: the p3d inspector (Recipe JSON, a 3D page to drag memory points, rebuild), the proxy editor (find and fix proxies that render at the floor, float or turn), the clothing alignment viewer and the FBX handoff to an artist, the offline winding and normal gate, the clean UV atlas pipeline with its exact overlap gate, and the .p3d to .glb viewer tool. Use when one of these has to run: inspect or rebuild a p3d, move memory points, align a proxy, fit worn clothing plates, export clothing for an artist, check winding before a pack, unwrap or audit UVs, or preview a model in a browser. The knowledge behind them is the model pack, skills/_shared/models/README.md."
argument-hint: "<tool> <model.p3d | recipe.json | file.blend> [options]"
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-model-tools

The scripts of the model work. Each tool has one how-to file in the model pack (`skills/_shared/models/`) with its options, its output, its limits and what was measured with it; read that file before the first run. This page only says which script does what and how to start it.

Follow `skills/_shared/dayz-conventions.md`. The scripts read and write only the files named on their command line and need neither DayZ Tools nor the game, so they do not gate on `/dayz-preflight` (the stated exception in `dayz-conventions.md`). The one exception is `worn_overlay.py`: it reads vanilla clothing and runs the preflight gate when its `--dz` folder is on `P:\`.

Write outputs under `output/<descriptive-folder>/` unless the model belongs to a mod in `workspace/<ModName>/`. Never write over the only copy of a model: build to a new file name, then run `/dayz-p3d-audit` on the result.

## Before the first run

- py3d is the DayZ fork in `scripts/tools/py3d/`, 1.6.0 or later. The scripts use that folder directly or an installed copy of it. Never `pip install py3d`: the PyPI package of that name is an unrelated library. `install_py3d.py` installs the fork from a built wheel when one is at hand; Agentic-Z ships none.
- The HTML pages take their scaffold from `viewer_core.py` in `scripts/tools/dayz-3d-viewer/` and load Three.js from a CDN, so the browser needs a network the first time.
- The UV scripts and `export_clothing_fbx.py` run inside Blender (`blender -b ... -P <script> -- <args>`), not under plain Python.

## Scripts

All in `<skill-dir>\scripts\`.

### p3d inspector

How-to: `tools-p3d-inspector.md`, with `tools-p3d-inspector-recipe.md` (the Recipe fields), `tools-p3d-inspector-viewer.md` (the page) and `tools-p3d-inspector-round-trip.md` (what a rebuild can lose).

```cmd
python "<skill-dir>\scripts\p3d_inspector_extract.py" model.p3d -v -o recipe.json
python "<skill-dir>\scripts\p3d_inspector_viewer.py" recipe.json inspector.html
python "<skill-dir>\scripts\p3d_inspector_build.py" recipe_edited.json model_rebuilt.p3d -v
```

| Script | Does |
|---|---|
| `p3d_inspector_extract.py` | MLOD `.p3d` to Recipe JSON: every LOD, memory point, axis, selection and property |
| `p3d_inspector_viewer.py` | Recipe to a standalone page where points and axis ends can be dragged |
| `p3d_inspector_build.py` | Edited Recipe to a new MLOD `.p3d`; `--no-autofix` on a model that rendered correctly |

Outside an agent session: `scripts\dayz\p3d-inspector-extract.bat`, `p3d-inspector-viewer.bat`, `p3d-inspector-build.bat`.

### Proxy editor

How-to: `tools-proxy-align.md`. The frame rule behind it is `proxy-frames.md`.

```cmd
python "<skill-dir>\scripts\proxy_extract.py" host.p3d recipe.json
python "<skill-dir>\scripts\proxy_canon.py" recipe.json edits.json
python "<skill-dir>\scripts\proxy_apply.py" host.p3d edits.json host_aligned.p3d --verify
```

| Script | Does |
|---|---|
| `proxy_frame.py` | The frame rule (angle sort, anchor, orientation) and the canonical triangle; used by the others |
| `proxy_extract.py` | Host `.p3d` to `recipe.json`, with an `ambiguous` flag per proxy |
| `worn_overlay.py` | Adds the worn model of one item per slot to the recipe (needs an external ODOL reader) |
| `proxy_canon.py` | Rewrites every proxy as an unambiguous triangle; `--rot Slot=AXIS:DEG` per slot |
| `proxy_viewer.py` | Recipe to an editor page with a move and rotate gizmo; exports `edits.json` |
| `proxy_apply.py` | Writes the listed proxy points back into the MLOD and changes nothing else |
| `install_py3d.py` | Installs the py3d fork from a built wheel |

Outside an agent session: `scripts\dayz\proxy-extract.bat`, `proxy-canon.bat`, `proxy-worn-overlay.bat`, `proxy-viewer.bat`, `proxy-apply.bat`.

### Worn clothing

How-to: `skills/_shared/wearables/references/fitting-worn-models.md` (alignment viewer and artist handoff) and `skills/_shared/wearables/references/autofit-on-official-rig.md`. The templates for the handoff are in `<skill-dir>\templates\` (`model.cfg.template`, `README-ARTIST.template.md`).

```cmd
python "<skill-dir>\scripts\alignment_viewer_extract.py" garment_m.p3d --out work
python "<skill-dir>\scripts\alignment_viewer_build.py" --data work\align_data.json
python "<skill-dir>\scripts\apply_alignment_json.py" --adjust adjust.json garment_m.p3d garment_f.p3d
blender -b --python "<skill-dir>\scripts\export_clothing_fbx.py" -- --out package --texture garment_co.png garment_m.p3d garment_f.p3d
```

| Script | Does |
|---|---|
| `alignment_viewer_extract.py` | Worn model to region data for the alignment page |
| `alignment_viewer_build.py` | Writes `alignment_viewer.html` with sliders per region |
| `apply_alignment_json.py` | Applies the exported adjustments to every LOD; backs each file up first |
| `export_clothing_fbx.py` | Runs in Blender: FBX package with UVs, diffuse PNG and the bone weights |

Outside an agent session: `scripts\dayz\clothing-viewer-extract.bat`, `clothing-viewer-build.bat`, `clothing-viewer-apply.bat`.

### Winding and normal gate

How-to: `tools-winding-gate.md`. Run it on the source MLOD after building the `.p3d` and before every pack. Exit 0 is PASS, 1 a model defect with the fix printed, 2 invalid input or a binarized file.

```cmd
python "<skill-dir>\scripts\check_dayz_winding.py" model.p3d
```

| Script | Does |
|---|---|
| `check_dayz_winding.py` | Signed volume per closed shell and stored normals per corner, for every visual LOD |
| `make_fixtures.py` | In `winding_fixtures\`: rewrites the four fixture models the gate's tests use |

Outside an agent session: `scripts\dayz\check-winding.bat`.

### Clean UV atlas

How-to: `tools-uv-atlas.md` (which method, the pipeline, the quality gate, the traps). The other UV files in the pack: `tools-uv-mesh-health.md`, `tools-uv-multi-lod-atlas.md`, `tools-uv-organic-photograph.md`, `tools-uv-mlod-audit.md`, `tools-uv-partuv.md`, `tools-uv-tool-survey.md`.

```cmd
blender -b in.blend -P "<skill-dir>\scripts\uv_clean_atlas.py" -- out.blend out_dir tag min_faces object_name
blender -b file.blend -P "<skill-dir>\scripts\sat_gate.py" -- object_name
```

| Script | Does |
|---|---|
| `uv_clean_atlas.py` | The paint atlas pipeline, stages 1 to 7 |
| `uv_view_charts.py`, `uv_straighten.py`, `uv_shelf_pack.py`, `uv_metrics.py` | The stages the pipeline imports; `uv_metrics.py` is also the audit module |
| `sat_gate.py` | The exact overlap gate for one object's active UV layer |
| `project_atlas.py` | The orthographic projector of the photograph method |
| `export_objs_tri.py` | A sanitized, triangulated OBJ for PartUV |
| `audit_partuv.py` | Scores a PartUV result and re-packs it |
| `partuv_install.sh` | Installs PartUV on Linux or WSL2 (bash) |

### 3D viewer tool

How-to: `tools-3d-viewer.md`, with `tools-3d-viewer-formats.md` (PAA and RVMAT), `tools-threejs-viewers.md` (the page library and testing it) and `tools-3d-viewer-states.md` (the plan for animations and LED states, not built). The tool is `scripts/tools/dayz-3d-viewer`, run as `python -m dayz_3d_viewer`; this skill ships no script for it.

## Tests

The `test_*.py` files in `<skill-dir>\scripts\` run under plain pytest and need no Blender: `python -m pytest -q skills/dayz-model-tools`.
