# The p3d inspector: Recipe JSON, viewer and rebuild

How to run the three inspector scripts of `/dayz-model-tools`, which read a source (MLOD) `.p3d` into one Recipe JSON, show it in a browser where memory points and axis ends can be dragged, and build a new `.p3d` from the edited Recipe. The Recipe fields are in `tools-p3d-inspector-recipe.md`, the page in `tools-p3d-inspector-viewer.md`, and what a rebuild can lose in `tools-p3d-inspector-round-trip.md`.

Tool behaviour, not game facts. Of the points the viewer colours, only `ce_center`, `box_placing_min`, `box_placing_max` and the `_axis` names are vanilla (`memory-points.md`); vanilla script reads `ce_center` at `P:\scripts\3_game\entities\object.c:1363`.

```
model.p3d  --extract-->  Recipe JSON  --viewer-->  edit by hand  --build-->  new .p3d
```

## Which tool for which job

| Task | Use |
|---|---|
| Look inside a model, move memory points or axis ends by hand | This inspector |
| A binarized (ODOL) `.p3d` | Not readable here. Agentic-Z ships no ODOL to MLOD converter; work from the source model. |
| A textured preview, or `.paa` to `.png` | The 3D viewer tool in `scripts/tools/dayz-3d-viewer` (`tools-3d-viewer-formats.md`) |
| Collision, winding, path and structure checks | `/dayz-p3d-audit`, on the model before and after a rebuild |
| Placing or aligning proxies on a host model | The proxy scripts of `/dayz-model-tools` (`proxy-frames.md`); the inspector does not write proxies safely |

The viewer draws flat shaded geometry with no textures on purpose: its job is to make memory points, axes, selections, collision LODs and bounds visible and editable.

## Before you start

- The extractor and the builder read and write `.p3d` with the DayZ fork of py3d (1.6.0 or later). They use the copy in `scripts/tools/py3d/` with nothing to install, and fall back to an installed py3d when that folder is missing. Never `pip install py3d`: the PyPI package of that name is an unrelated library.
- numpy is needed only by the builder's auto-fix: `python -m pip install numpy`. Without numpy the builder skips the auto-fix and says nothing.
- The viewer needs neither. It writes one HTML file that loads Three.js 0.185.1 as ES modules from the jsDelivr CDN, so the browser needs internet access the first time. The page scaffold comes from `viewer_core.py` in `scripts/tools/dayz-3d-viewer`; the script stops and names the paths it tried when that file is missing.

## How to run

The scripts are in `skills\dayz-model-tools\scripts\`:

```cmd
REM 1. Model to Recipe
python "<scripts>\p3d_inspector_extract.py" path\to\model.p3d -v -o recipe.json

REM 2. Recipe to interactive viewer (open the HTML in a browser)
python "<scripts>\p3d_inspector_viewer.py" recipe.json inspector.html

REM 3. Edited Recipe to a new model
python "<scripts>\p3d_inspector_build.py" recipe_edited.json path\to\model_rebuilt.p3d -v
```

| Script | Arguments | Does |
|---|---|---|
| `p3d_inspector_extract.py` | `<model.p3d> [-v] [-o recipe.json]` | Reads every LOD, memory point, axis, selection, property and referenced path into a Recipe JSON. With no argument or `--demo [out.json]` it writes a demo Recipe. |
| `p3d_inspector_viewer.py` | `<recipe.json> [output.html]`, or `--demo [output.html]` | Writes the viewer HTML. `--demo` needs no model at all. |
| `p3d_inspector_build.py` | `<recipe.json> [output.p3d] [-v] [--no-autofix]` | Writes an MLOD `.p3d` from a Recipe. |

In the viewer the user drags points, then presses **Export Recipe**, selects all and copies the JSON from the box (the clipboard API is blocked for a page opened from disk). The export holds only `meta`, `memory_points`, `axes` and `bbox`, not the LODs. Copy its `memory_points` and `axes` over the same two keys of the extracted Recipe, save that as the edited Recipe and build from it. Building from the export alone writes a model with nothing but a Memory LOD.

Write the outputs under `output/<descriptive-folder>/` unless the model belongs to a mod in `workspace/<ModName>/`.

## Rules that keep a rebuild safe

1. **Never build over the only copy of a model.** Build to a new file name and keep the original.
2. **A rebuild can wipe Memory LOD selections.** The builder rebuilds the Memory LOD as points only: its faces, the face membership of its selections (damage zones, crew positions, proxies), any selection that holds only faces, and selection weights are dropped. Point membership, which the axes use, survives. Before any rebuild you mean to keep, run the round-trip test in `tools-p3d-inspector-round-trip.md` and compare selection counts, not names. To move a point on a model with important memory selections, edit the MLOD with py3d directly.
3. **The `.p3d` is the truth, not the Recipe.** If the model was edited elsewhere since the Recipe was made, extract again before trusting the viewer.
4. **Auto-fix reverses every face of every LOD.** The builder does that when over half the faces of the first Visual LOD (the visual LOD with the lowest resolution, whether that is 0.0 or 1.0) disagree with their stored normals. That disagreement does not say which of the two is wrong (`dayz-p3d-audit/references/winding-absolute-check.md`), so on a model that rendered correctly, build with `--no-autofix`.
5. **Audit after every build.** Run `/dayz-p3d-audit` on the new file. The builder checks nothing beyond what it writes.

## Limits

- Source (MLOD) models only.
- The viewer has no textures and no axis lock: a point moves in the plane facing the camera.
- The extractor does not record per-point mass; the builder estimates it (`tools-p3d-inspector-recipe.md`).
- The builder writes no sharp edges, and it drops any LOD the extractor could not name (`tools-p3d-inspector-recipe.md`, "LOD types").
- On Linux the scripts run natively; opening the result in Object Builder goes through Proton as `_shared/linux-proton.md` describes.
