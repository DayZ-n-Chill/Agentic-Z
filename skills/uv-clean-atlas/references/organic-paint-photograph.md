# Paint atlas for an organic one-shell mesh: photograph, do not unwrap

How to build a paintable atlas for a statue, a coat or a one-shell character by projecting it orthographically ("photographing" it) instead of unwrapping it. The method was accepted by its user on 2026-09-02 on a statue mesh generated with Tripo (run `g12_arm` below). The script output labels it G12; the projection and packing stages it reuses are labelled G9 and G10.

The engine is `<skill-dir>\scripts\project_atlas.py`, the projector first written for the LFQuad vehicle body (LFQuad is the source author's quad-bike mod). The script is a copy; the LFQuad project keeps its own, along with the shell classification and the paint groups the vehicle method was developed on, none of which are in this repo. The driver that peels the statue's limbs was run live against that one mesh and is not shipped, because it holds paths and thresholds for that statue only. The steps below are enough to drive the engine on another mesh.

Do not run `uv_view_charts.py` plus the SLIM unwrap on a one-shell organic mesh. That clustering is for vehicle panels. On the statue it produced 25 charts, the dust merge took them to 5 with density from 0.00 to 3.95, and the attempts to repair that (k=6 clustering, a Voronoi split, absorbing small charts) all deformed the result. The `smart_project` fallback gave 215 islands and was rejected: not few, and not by views.

## What "done" looks like

In priority order:

1. **The user can read the atlas.** It shows elevations of the asset, in pieces a painter can name. Not a tetris pack and not 200 crumbs.
2. **No overlap between islands.** The exact SAT pair count is 0. Report collapsed faces against the total; any collapse of unwrapped faces is a fail. Triangles seen edge-on in the photo (`n·axis ≈ 0`) are part of the photograph, not an unwrap collapse; the statue had 4 in 11k.
3. **Self-overlap inside the photograph is gone.** This is what the user sees as "there is still overlap": one part of the mesh in front of another in the same view. Peel the overlapping pieces until the ghost is gone. A leftover of about 0.03 from the thickness of a sleeve tube was accepted.
4. **One global scale `a`.** The coefficient of variation of scale is 0. The map is affine: `u = a·u_proj + b`, `v = a·v_proj + c`. Peeled pieces get a rigid translation only. Do not normalize density per island; that deforms the photo.
5. **Few islands, each a piece of a view.** Two elevations: n+ (skin, outside) and n− (lining, inside). Left and right stay in the same frame. Peel the legs, then the limbs that occlude. The statue ended at 15 islands, not 40 and not 215. Do not graph-color left and right into extra frames; that destroys the elevation.

## Recipe

1. Sanitize the mesh. Do not remesh as part of the UV work.
2. Measure the photograph axis from the bounding box, the island area and the self-overlap. Up is the longest bounding-box axis. Do not allow a top-down view when a side elevation exists. On the statue: up = Z, the thin axis = +Y, the front. An unsplit closed coat has a self-overlap of about 1.0, so it must be split by normal sign.
3. Split by **normal sign**: n+ is the skin or outside, n− is the lining or inside. They are two elevations of the same asset and are never stacked in one island.
4. Split **left and right** only when the shell's bounding box crosses the measured X mid-plane. Keep both in the same elevation, as an archipelago at their real projected XY. If the exact check finds a collision on the midline, nudge a tiny gap in U (`du_each` of about 0.01 world units). Do not put left and right in different frames.
5. Use one photograph rotation, so that world up increases with V (head up). The spine sits at `u_proj = 0`.
6. Pack the **cropped frames as rectangles** (the G10 maxrects packer). Two frames side by side: lining, then skin. Align the pieces inside each layer, then the layers to each other. Do not pack the islands like tetris.
7. **Gate on SAT = 0.** If the user still sees overlap, it is occlusion inside one island of the photograph. Peel pieces. Do not add cameras beyond about two elevations unless the user asks.

### Peeling overlapping pieces within one elevation

Repeat until the ghost is gone. Keep the same `a` and use rigid translation only. Place each piece so it still reads as that part of the elevation: legs below the hem, arms beside the body, a second occluder above.

**Legs.** When the coat overlaps the legs in the photo, make a legs island. Cut near the hem; the faces below it whose connected component **reaches the floor** are legs. Coat skirt that does not reach the floor stays with the coat. Translate the legs with a negative Δv: below the hem, feet down, midline kept.

**Limbs and other occluders.** On the remaining coat islands, rasterize the photograph and find the pixels covered two or more times. The **front occluder** is the covering face with the larger world depth along the view and a real gap (on the statue: larger world Y, ΔY of 0.02 or more). The connected components of those front faces are a limb. If a component still shares photo pixels, it is a second piece (`arm2`). Skip grazing components of a few faces (fewer than 8). Translate arms to the side (Δu) and leftover occluders above (positive Δv).

Do not use a Voronoi split. Do not use `smart_project`. Do not let the texturing tool recreate the UVs.

## Worked example: the statue, 2026-09-02

Mesh: `statue_remesh.blend`, object `statue`, 5,756 faces, 1 shell, identity world transform.

| Run | Islands | SAT pairs | Self-overlap | Occupancy | Notes |
|---|---:|---:|---:|---:|---|
| `g12_proj` | 4 | 2 | 0.234 | 0.73 | Two elevations; SAT pairs on the left/right midline; coat over legs. User: recognizable, but overlaps |
| `g12_legs` | 8 | 0 | 0.166 | 0.54 | Legs cut at z = 0.32 by floor-reaching component, Δv = −0.194. User: better, overlap remains (sleeve) |
| `g12_arm` | 15 | 0 | 0.033 | 0.19 | Front occluders peeled; arms Δu ±0.27, `arm2` Δv = +0.77. User: better, keep this recipe; painting comes next |

The leftover 0.033 is the thickness of the sleeve tube plus folds of fewer than 8 faces. It is not the arm-over-chest ghost.

## Do not

- Unwrap (SLIM, angle based or `smart_project`) a paint atlas for an organic mesh.
- Run the `uv_view_charts.py` k-means clustering or its cone fallback on a one-shell coat.
- Let the texturing tool (Modddif in the source project) recreate the UVs. Generate only on this atlas.
- Graph-color left and right into extra elevations to force SAT = 0.
- Normalize density per island; it deforms the photograph.
- Hand UV work to a 3D generation model (Hunyuan3D on a local GPU was ruled out for this job).
