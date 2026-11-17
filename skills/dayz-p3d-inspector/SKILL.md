---
name: dayz-p3d-inspector
description: "Shows what is inside a DayZ .p3d model and lets the user edit its memory points by hand: extracts every LOD, memory point, axis, selection and named property into one Recipe JSON, opens it in an interactive 3D viewer where points and axis ends can be dragged, and builds a new .p3d from the edited Recipe. Use when the user says inspect the model, show me the p3d, view or move memory points, recipe json, build p3d from a recipe, or round-trip a p3d. Not for collision or structure audits (/dayz-p3d-audit) and not for a textured preview (dayz-3d-viewer)."
argument-hint: "<model.p3d> | <recipe.json> [output]"
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-p3d-inspector

A three-step round trip over one source (MLOD) `.p3d`:

```
model.p3d  --extract-->  Recipe JSON  --viewer-->  edit by hand  --build-->  new .p3d
```

The extractor reads the model into a Recipe JSON, the viewer writes one HTML file that shows it in 3D and lets the user drag memory points and axis ends, and the builder writes a fresh `.p3d` from the edited Recipe.

Follow `skills/_shared/dayz-conventions.md`. The scripts work on files anywhere on disk and need neither `P:\`, DayZ Tools nor the game, so they do not run `/dayz-preflight`.

## What this skill owns, and what it hands off

It owns the Recipe JSON (one complete description of a `.p3d`), the interactive editor and the Recipe to `.p3d` builder. Everything else belongs to another skill:

| Task | Use |
|---|---|
| A binarized (ODOL) `.p3d` | Not readable here. The repo ships no ODOL to MLOD converter; work from the source model. |
| A textured preview, or `.paa` to `.png` | `dayz-3d-viewer` |
| Collision, winding, path and structure checks | `/dayz-p3d-audit`, on the model before and after a rebuild |
| Making a model from scratch or fixing its geometry | `dayz-model-pipeline` |
| Placing or aligning proxies on a host model | `dayz-proxy-align` |

The viewer draws flat shaded geometry with no textures on purpose: its job is to make memory points, axes, selections, collision LODs and bounds visible and editable.

## Before you start

- The extractor and the builder read and write `.p3d` with the DayZ fork of py3d (1.6.0 or later). They use the copy in this repo under `scripts/tools/py3d/` with nothing to install. Never `pip install py3d`: the PyPI package of that name is an unrelated library.
- Without that folder (a plugin install that ships only `skills/`) both scripts fall back to the installed py3d, and stop with an install hint when there is none.
- numpy is needed only by the builder's auto-fix: `python -m pip install numpy`. Without numpy the builder skips the auto-fix and says nothing.
- The viewer needs neither. It writes one HTML file that loads Three.js 0.185.1 as ES modules from the jsDelivr CDN, so the browser needs internet access the first time. The page scaffold comes from `viewer_core.py`, which ships with the 3D viewer tool in `scripts/tools/dayz-3d-viewer`; the script stops and names the paths it tried when that file is missing.
- `<skill-dir>\scripts\install_py3d.py` is optional. It installs the fork from a built wheel so that `import py3d` works outside this repo, and stops when no wheel was built.

## How to run

```cmd
REM 1. Model to Recipe
python "<skill-dir>\scripts\p3d_inspector_extract.py" path\to\model.p3d -v -o recipe.json

REM 2. Recipe to interactive viewer (open the HTML in a browser)
python "<skill-dir>\scripts\p3d_inspector_viewer.py" recipe.json inspector.html

REM 3. Edited Recipe to a new model
python "<skill-dir>\scripts\p3d_inspector_build.py" recipe_edited.json path\to\model_rebuilt.p3d -v
```

| Script | Arguments | Does |
|---|---|---|
| `p3d_inspector_extract.py` | `<model.p3d> [-v] [-o recipe.json]` | Reads every LOD, memory point, axis, selection, property and referenced path into a Recipe JSON. With no argument or `--demo [out.json]` it writes a demo Recipe. |
| `p3d_inspector_viewer.py` | `<recipe.json> [output.html]`, or `--demo [output.html]` | Writes the viewer HTML. `--demo` needs no model at all. |
| `p3d_inspector_build.py` | `<recipe.json> [output.p3d] [-v] [--no-autofix]` | Writes an MLOD `.p3d` from a Recipe. |

In the viewer the user drags points, then presses **Export Recipe**, selects all and copies the JSON from the box (the clipboard API is blocked for a page opened from disk). The export holds only `meta`, `memory_points`, `axes` and `bbox`, not the LODs. Copy its `memory_points` and `axes` over the same two keys of the extracted Recipe, save that as the edited Recipe and build from it. Building from the export alone writes a model with nothing but a Memory LOD.

Write the outputs under `output/<descriptive-folder>/` unless the model belongs to a mod in `workspace/<ModName>/`.

Outside an agent session, `scripts\dayz\p3d-inspector-extract.bat`, `scripts\dayz\p3d-inspector-viewer.bat` and `scripts\dayz\p3d-inspector-build.bat` run the three scripts with the same arguments.

## Rules that keep a rebuild safe

1. **Never build over the only copy of a model.** Build to a new file name and keep the original.
2. **A rebuild can wipe Memory LOD selections.** On real models the builder can lose which points belong to which memory selection (axes, damage zones, crew positions, proxies) while every name still looks right. Before any rebuild you mean to keep, run the round-trip test in `references/round-trip-caveats.md` and compare selection counts, not names. To move a point on a model with important memory selections, edit the MLOD with py3d directly.
3. **The `.p3d` is the truth, not the Recipe.** If the model was edited elsewhere since the Recipe was made, extract again before trusting the viewer.
4. **Auto-fix reverses every face of every LOD.** The builder does that when over half the faces of the first Visual LOD disagree with their stored normals. That disagreement does not say which of the two is wrong (`dayz-p3d-audit/references/winding-absolute-check.md`), so on a model that rendered correctly, build with `--no-autofix`.
5. **Audit after every build.** Run `/dayz-p3d-audit` on the new file. The builder checks nothing beyond what it writes.

## References

| Question | Open |
|---|---|
| What is in the Recipe JSON, which LOD types does it know, and what exactly does the builder write (faces, UVs, mass, the Memory LOD, auto-fix)? | `references/recipe-format.md` |
| What can the viewer show and how is it used (layers, point colours, dragging, snapping, export), and why is it built the way it is? | `references/viewer.md` |
| What gets lost or misread in a round trip (memory selections, stale Recipes, selection indices, unused face bytes), and how do I test for it? What is planned and not built? | `references/round-trip-caveats.md` |

Facts about memory points and selections themselves are in `_shared/models/memory-points.md` and `_shared/models/selections.md`.

## Limits

- Source (MLOD) models only.
- The viewer has no textures and no axis lock: a point moves in the plane facing the camera.
- The extractor does not record per-point mass; the builder estimates it (`references/recipe-format.md`).
- The builder writes no proxies and no sharp edges, and it drops any LOD the extractor could not name (`references/recipe-format.md`, "LOD types").
- On Linux the scripts run natively; opening the result in Object Builder goes through Proton as the shared Linux notes describe (`_shared/linux-proton.md`).
