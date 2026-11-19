# Mesh health and seams before unwrapping

What a mesh must pass before any UV work, the Blender API traps that corrupt UV layers in headless runs, and which seam methods break an atlas into fragments and which keep it to a few islands. The DayZ side of UV mapping (formats, materials, symptoms in game) is in `uv-mapping.md`; the unwrap pipeline is in `tools-uv-atlas.md`.

Nothing here is a game fact. The numbers were measured on the body and wheels of a quad bike mod.

## Mesh health comes first

Unwrapping or baking a broken mesh gives false diagnoses, for example a "double wall" that is really mirrored mapping on a single wall. What an artist reports, and what to measure:

| What the artist says | What to measure | Quad bike body |
|---|---|---|
| "Open, unwelded vertices" | Vertices that would merge at under 0.5 mm (KD tree), plus coincident duplicate faces | 190 to 715 vertices per part in the mechanical groups; about 1.9k duplicate faces in 2 parts |
| "Convexity issue", "it does not close" | Boundary edges (edges with one face), shells that are not watertight | 65 to 3,674 open edges per part; most are single wall design, not breakage |
| "Weird normals" | Edges with inconsistent winding; non manifold edges (more than two faces) | 28 winding edges and 264 non manifold edges on the grille, a stacked strip design |

No script for this is shipped; any bmesh script that measures the same things will do:

1. Audit each part first: boundary edges, non manifold edges, duplicate vertices, duplicate faces, zero area faces and winding.
2. Weld adaptively. A blind weld at 0.5 mm merges parts that legitimately touch and creates non manifold edges (one seat part went from 0 to 168). Try 0.5, 0.2, 0.1, 0.05 and 0.01 mm in turn, and for each mesh take the largest distance that does not raise the non manifold count and keeps the UVs. Check both conditions in the script. The weld keeps loop UVs (checked on 15 meshes).
3. Delete coincident duplicate faces, degenerate faces and loose geometry, then recalculate normals.
4. Pass only when the non manifold count is no higher than before, the share of non zero UVs is unchanged, and a render shows no black patches (black patches are flipped normals).
5. Leave open edges that are there by design (single walls, strips). DayZ draws them; they matter only for a watertight check or an interior ambient occlusion bake.

Zero length face normals exist in real meshes, and zero area faces crash naive code. Every UV script in `/dayz-model-tools` guards them, but a broken mesh still gives specks.

## Blender API traps

Each of these gave at least one wrong result.

- Stale `loop_triangles`. Cached references to `me.loop_triangles` go stale after any trip through edit mode, which gives silent corruption or an `IndexError`. Rebuild the cache after each `mode_set`. The sign of it was two UV layers that ended up byte for byte identical.
- Layers that contaminate each other. Building several UV layers with operators (`smart_project`, `unwrap`, `pack_islands`) in one headless session can leave two layers byte for byte identical although different pipelines made them, with no stale cache involved. Compare every pair of layers for byte equality at the end of any build with more than one layer (`foreach_get` into numpy arrays, then `array_equal`), and rebuild the affected candidate alone in a clean session with one layer. Equal metrics between two methods are not this bug: density normalization plus a global pack push any layout to about the same island count and px/m. Only equal data is the bug.
- `bpy.ops.uv.smart_project` ignores the face selection when headless and unwraps the whole mesh. Four pipelines that each "re-projected only the selected faces" all produced exactly 2,043 islands, which was `smart_project` at 45 degrees over everything. Identical island counts from different methods are the sign. To re-project chosen faces, project them yourself onto a plane (an orthonormal basis of the cluster's main normal, UVs written directly). `uv.unwrap` and `pack_islands` do respect the selection.
- `bm.to_mesh(me)` invalidates earlier RNA references such as `me.uv_layers[...].data`. Fetch them again after each `to_mesh`.
- Never deduplicate bmesh loop UV wrappers by `id()`. The wrappers are temporary and their ids are reused, so loops get skipped silently. Visit each loop once. `loop.index` is not guaranteed to be set either: key corners by `(face.index, vert.index)`.

Numbers that are exactly 100 % or exactly 0.000, or two results that are exactly equal, point at a tool fault before they point at the model.

## Proving zero overlap

A Monte Carlo overlap estimate has a noise floor of about 0.05 to 0.15 % and cannot show zero. The exact test is a 2D triangle against triangle separating axis test (SAT) on candidate pairs from a spatial grid: interiors that intersect count, touching at a boundary does not (epsilon 1e-9). About 74k triangles give about 10^5 candidate pairs, a few seconds in Python. Say "no overlap" only when the SAT pair count is 0; anything that bakes or paints on the atlas, such as Substance Painter, depends on it. `sat_gate.py` in `/dayz-model-tools` is this test.

## Fewer islands: cut by topology, not by angle

The target for a whole object such as a wheel is 4 or 5 islands, not hundreds. Fragmentation does not come from the geometry; it comes from an algorithm that cuts at every sharp edge.

Count the shells (edge connected components) first. The quad bike wheel has 15 shells and the bodywork 13. The island floor is the shell count, because an unwrapper cannot join separate shells, so with 13 shells the target is about 13 to 30 islands, not 500 to 2,000.

Methods that fragment, measured on the tire (7,056 faces, one shell):

- `smart_project` at any angle: 1,115 islands. It splits at every tread block.
- Working on the authored UVs, which are already in fragments: 500 to 2,000.
- Stitching slivers together: 544.

What works is a topological cut followed by an unwrap that resists folding:

1. Open the closed shells. A closed shell of genus 0 (a sphere, a box, a cap) gets no cuts from tree-cotree, stays closed, and LSCM fails with "Unwrap failed to solve". Mark the edges of one seed face per closed shell as seams, so each shell becomes a disk with a boundary.
2. Tree-cotree, the minimal cut. Build a spanning forest on the vertices, shortest edges first, which gives clean cuts. Build a dual forest on the faces over the manifold edges not in the first forest. The edges in neither forest are the cut graph: mark them as seams. Each shell opens into a disk with the fewest cuts, two per handle.
3. `unwrap(method="MINIMUM_STRETCH")`, the SLIM solver. It resists folding and closes without overlap far better than `ANGLE_BASED` or `CONFORMAL`.
4. Split the few badly folded islands along their PCA axis (8 % threshold), in one pass only. Iterated, it multiplies islands: 26 became 508.
5. Normalize density, then pack with the `CONCAVE` shape method.

Result: the wheel in 29 islands (3,261 px/m at 2048) and the bodywork in 22 (857 px/m, 13 SAT pairs), against 508 to 2,000 for every other method. The layout is readable: the tire caps are two disks, the rim a cross, the tread one sweep.

What is left: closed curved shells (a tire carcass, domed caps) keep small self overlaps after LSCM. Projecting them onto a plane folds them worse, because they are not developable, and more cuts fragment them. An artist relaxes them or adds one seam per shell in seconds; automatic zero overlap on a closed curved surface is a hard problem that even RizomUV's automatic seams only half solve.

No script for this cut is shipped; `sat_gate.py` is the overlap check it relies on. Two limits apply (see "The unwrap" in `tools-uv-atlas-traps.md`): with seams this sparse, SLIM can collapse most triangles to zero UV area without a warning, and the view chart method in `uv_view_charts.py` is the default for vehicle panels instead.

## Repairing an existing layout

Stitching small islands reduces fragmentation when the user asks for larger groups. Stitch island S to the neighbour N it shares the most mesh boundary with, using a similarity transform that aligns the shared edge (as a complex number, `s = (b2 - b1) / (a2 - a1)`). It is conformal, so it cannot wrinkle.

- Normalize density first, so a correct stitch has `|s|` close to 1; reject anything outside 0.75 to 1.33.
- After each stitch, check an absolute density limit of 0.6 to 1.6. Without it, chains of stitches drift (a p5 of 0.027 was measured).
- Check the stitched island does not overlap N, by sampling 8 points per triangle.
- Try the top 3 neighbours; repeat until nothing changes.

Result: 865 clean merges, 2,054 islands down to 544, p5 density 0.245. A rigid weld of the whole shared boundary wrinkles the faces along the seam (p5 0.031); do not use it.

Local folds between adjacent faces cannot be fixed by moving them, because they move together. Re-project the cluster onto a local plane instead.

Splitting a folded island without re-projecting it keeps the authored unwrap. Walk the island breadth first by mesh adjacency, adding a face to the current region while the mapping stays one to one (test overlap by sampling against a grid of the region). A blocked face starts a new region. Regions 1 to n then move outside the tile (+2k in U for region k), which breaks loop continuity so the packer treats each as its own island. Result: 16 folded islands became 2 to 5 regions each, the original density stayed (690 px/m at 2048) and overlap fell from 88 % to 0.2 %.

## What pack_islands does and does not do

- It does not fit the selection into the 0 to 1 tile. It leaves the content near its current scale and tile (`CLOSEST_UDIM`), so any remap after packing must measure the real bounding box. A blind remap crushed some groups about 40 times.
- Packing by zones costs about 30 to 36 % of the global density. In a global pack the tiny islands fill the gaps between large ones; reserving a band for them leaves those gaps empty (703 px/m against 449 px/m on the quad bike). Visual order in an atlas has a price; let the artist decide whether to pay it.
- It optimizes area, not legibility, and shuffles rotations. That is why the final pack for a paint atlas is the shelf packer, not `pack_islands`.
