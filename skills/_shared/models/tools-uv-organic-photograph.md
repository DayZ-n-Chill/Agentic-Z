# Paint atlas for an organic mesh

How to build a paintable atlas for a statue, a coat or a one shell character by projecting it orthographically, photographing it from its elevations, instead of unwrapping it. The unwrap pipeline for hard surface panels is in `tools-uv-atlas.md`.

Nothing here is a game fact. The method was measured, and accepted by its user, on a one shell statue mesh generated with Tripo. The engine is `project_atlas.py` in `skills/dayz-model-tools/scripts/`, a projector first written for a quad bike body. The shell classification and paint groups of that vehicle are not in this repo, and the driver that peeled the statue's limbs is not shipped because it holds paths and thresholds for that statue only. The steps below are enough to drive the engine on another mesh.

Never run `uv_view_charts.py` plus the SLIM unwrap on a one shell organic mesh; that clustering is for vehicle panels. On the statue it produced 25 charts, the dust merge took them to 5 with density from 0.00 to 3.95, and every repair tried (k=6 clustering, a Voronoi split, absorbing small charts) deformed the result. The `smart_project` fallback gave 215 islands: not few, and not by views.

## What done looks like

In order:

1. The user can read the atlas. It shows elevations of the asset, in pieces a painter can name, not a tight pack and not 200 crumbs.
2. No overlap between islands: the exact SAT pair count is 0. Report collapsed faces against the total; any collapse of unwrapped faces fails. Triangles seen edge on in the photograph (`n·axis ≈ 0`) are part of the photograph, not a collapse; the statue had 4 in 11k.
3. No self overlap inside the photograph. This is what the user sees as "there is still overlap": one part of the mesh in front of another in the same view. Peel the overlapping pieces until the ghost is gone. A leftover of about 0.03 from the thickness of a sleeve tube was accepted.
4. One global scale `a`, so the coefficient of variation of scale is 0. The map is affine: `u = a·u_proj + b`, `v = a·v_proj + c`. Peeled pieces move by rigid translation only. Never normalize density per island; it deforms the photograph.
5. Few islands, each a piece of a view. Two elevations: n+ (skin, outside) and n− (lining, inside). Left and right stay in the same frame. Peel the legs, then the limbs that occlude. The statue ended at 15 islands. Never colour left and right into extra frames; that destroys the elevation.

## Recipe

1. Clean the mesh. Do not remesh as part of the UV work.
2. Measure the photograph axis from the bounding box, the island area and the self overlap. Up is the longest bounding box axis. Never allow a top down view when a side elevation exists. On the statue: up = Z, the thin axis = +Y, the front. An unsplit closed coat has a self overlap of about 1.0, so it must be split by normal sign.
3. Split by normal sign: n+ is the skin or outside, n− the lining or inside. They are two elevations of the same asset and never share an island.
4. Split left and right only when the shell's bounding box crosses the measured X mid plane. Keep both in the same elevation, as an archipelago at their real projected XY. If the exact check finds a collision on the midline, nudge a small gap in U (`du_each` of about 0.01 world units). Never put left and right in different frames.
5. Use one photograph rotation, so that world up increases with V (head up). The spine sits at `u_proj = 0`.
6. Pack the cropped frames as rectangles (the maxrects packer of the `out_g10` stage). Two frames side by side: lining, then skin. Align the pieces inside each layer, then the layers to each other. Never pack the islands tightly like puzzle pieces.
7. Pass only on SAT = 0. If the user still sees overlap, it is occlusion inside one island of the photograph; peel pieces. Add no cameras beyond about two elevations unless the user asks.

### Peeling overlapping pieces

Repeat until the ghost is gone. Keep the same `a` and move pieces by rigid translation only. Place each piece so it still reads as that part of the elevation: legs below the hem, arms beside the body, a second occluder above.

Legs: when the coat overlaps the legs in the photograph, make a legs island. Cut near the hem; the faces below it whose connected component reaches the floor are legs. Coat skirt that does not reach the floor stays with the coat. Move the legs down (negative Δv), below the hem, feet down, midline kept.

Limbs and other occluders: on the remaining coat islands, rasterize the photograph and find the pixels covered two or more times. The front occluder is the covering face with the larger world depth along the view and a real gap (on the statue: larger world Y, ΔY of 0.02 or more). The connected components of those front faces are a limb. If a component still shares photo pixels, it is a second piece (`arm2`). Skip grazing components of fewer than 8 faces. Move arms to the side (Δu) and leftover occluders above (positive Δv).

Never use a Voronoi split or `smart_project`, and never let the texturing tool recreate the UVs.

## Running the engine

```text
blender -b <file.blend> --python <repo>\skills\dayz-model-tools\scripts\project_atlas.py -- <assignment.json or SMOKE> <outdir> [--placement-override <file.json>]
```

The script never saves the `.blend`. It writes `atlas_metrics.json`, the island files (`atlas_a_islands.json`, `atlas_b_islands.json`, `island_visibility.json`) and the frozen `assignment_REAL.json` into `<outdir>`, prints one `SUMMARY` line, and exits with code 3 when a check fails.

It is the projector as it ran on the quad bike body, so these parts must change before it accepts another mesh:

| In the script | What it holds for the quad bike | Effect on another mesh |
|---|---|---|
| `EXPECTED_BLEND_SHA256` | The SHA-256 of that one `.blend` | `main()` logs `ERROR blend sha256` and exits with code 2 |
| `EXPECTED_FACE_COUNT` | 10,502 faces | The face count check fails |
| `find_body_object()` | Looks for an object named `carroceria` (Spanish for bodywork) | Falls back to the mesh object with the most faces and logs a warning |
| `CONTROL_A_SHELL`, `CONTROL_B_SHELL` | Shells `S06` and `S03`, with their expected overlap figures | The two controls read the wrong piece or raise a `KeyError` |
| `G7_CROSSING_SHELLS`, `G7_MIRROR_PAIRS`, `G7_ATLAS_A_SHELLS`, `G8_FRONT_VIEW_ROTATIONS` | That body's shell ids | The `out_g7` to `out_g9` layouts place the wrong pieces |
| `SMOKE_ISLANDS_A`, `SMOKE_OVERLAP_A`, the `G3_*` figures | Earlier results on that body, used as baselines | The "not worse than baseline" comparisons mean nothing |

Three more things to know:

- The stage follows the name of `<outdir>`. `out_g7`, `out_g8`, `out_g9` and `out_g10` select the anatomical, two panel, archipelago and cropped frame layouts. Any other folder name runs the projection axis search and the older block packer. Each named stage reads `atlas_metrics.json` from the folder that holds the assignment file, so run the stages in order, each fed the previous stage's frozen assignment.
- `SMOKE` in place of the assignment file derives a provisional split by shell size and shape and writes `assignment_SMOKE.json`. It checks the plumbing; it is not the paint classification.
- `--placement-override` applies a JSON of rigid per island translations on top of the `out_g10` result (logged as G11). The file must have exactly the keys `source` (`"uv_arranger"`), `base` (`"out_g10"`), `atlas` (`"A"`), `uv_space` (`[0, 0, 1, 1]`) and `islands`, with one row per base island holding `id`, `placement_center_uv` and `delta_uv`; anything else is rejected. With an override the script then calls `render_atlas_pngs`, which runs `draw_atlas_fallback.ps1` through `powershell.exe`. That renderer is not shipped, so the step logs `PNG_RENDER_SKIPPED` after the metrics are written and the run ends normally; draw the PNG files from `atlas_a_islands.json` another way. Without an override it writes `REPORT_G10.md` next to `<outdir>` instead.

## Worked example: the statue

Mesh: object `statue`, 5,756 faces after a QuadriFlow remesh, one shell, identity world transform.

| Step | Islands | SAT pairs | Self overlap | Occupancy | Result |
|---|---:|---:|---:|---:|---|
| Projection only | 4 | 2 | 0.234 | 0.73 | Two elevations; SAT pairs on the left and right midline; coat over legs. Readable, but overlapping |
| Legs peeled | 8 | 0 | 0.166 | 0.54 | Legs cut at z = 0.32 by floor reaching component, Δv = −0.194. Better; the sleeve still overlaps |
| Arms peeled | 15 | 0 | 0.033 | 0.19 | Front occluders peeled; arms Δu ±0.27, `arm2` Δv = +0.77. Accepted for painting |

The leftover 0.033 is the thickness of the sleeve tube plus folds of fewer than 8 faces, not the arm over chest ghost.

## Do not

- Unwrap (SLIM, angle based or `smart_project`) a paint atlas for an organic mesh.
- Run the `uv_view_charts.py` k-means clustering or its cone fallback on a one shell coat.
- Let the texturing tool recreate the UVs. Generate texture only on this atlas.
- Colour left and right into extra elevations to force SAT = 0.
- Normalize density per island; it deforms the photograph.
- Hand UV work to a 3D generation model. Hunyuan3D on a local GPU was ruled out for this job.
