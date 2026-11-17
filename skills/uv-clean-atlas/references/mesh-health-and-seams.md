# Mesh health before unwrapping, and where to cut

The checks a mesh must pass before any UV work, the Blender API traps that corrupt UV layers in headless runs, and the seam methods that were measured: which fragment an atlas and which keep it to a few islands. Measured in July 2026 on the body and wheels of a quad-bike vehicle mod (a 1987 Yamaha Banshee model, the quad bike below). The DayZ side of UV mapping (formats, materials, symptoms in game) is in `_shared/models/uv-mapping.md`.

## Contents

- [Mesh health comes first](#mesh-health-comes-first)
- [Blender API traps](#blender-api-traps)
- [Proving zero overlap](#proving-zero-overlap)
- [Fewer islands: cut by topology, not by angle](#fewer-islands-cut-by-topology-not-by-angle)
- [Repairing an existing layout](#repairing-an-existing-layout)
- [What pack_islands does and does not do](#what-pack_islands-does-and-does-not-do)

## Mesh health comes first

UV work rests on mesh health. Unwrapping or baking on a broken mesh produces false diagnoses, for example a "double wall" that was really mirrored mapping on a single wall. What an artist reports, and what it measures as:

| What the artist says | What to measure | The quad-bike body, measured |
|---|---|---|
| "Open, unwelded vertices" | Vertices that would merge at under 0.5 mm (KD-tree), plus coincident duplicate faces | 190 to 715 vertices per part in the mechanical groups; about 1.9k duplicate faces in 2 parts |
| "Convexity issue", "it does not close" | Boundary edges (edges with 1 face), shells that are not watertight | 65 to 3,674 open edges per part; most are single-wall design, not breakage |
| "Weird normals" | Edges with inconsistent winding; non-manifold edges (more than 2 faces) | 28 winding edges and 264 non-manifold edges on the grille, a stacked-strip design |

The recipe (no script for it is shipped here; any bmesh script that measures the same things will do):

1. Audit first: boundary edges, non-manifold edges, duplicate vertices, duplicate faces, zero-area faces and winding, per part.
2. Weld **adaptively**. This is the central pitfall: a blind weld at 0.5 mm merges parts that legitimately touch and *creates* non-manifold edges (one seat part went from 0 to 168). Use a ladder of 0.5, 0.2, 0.1, 0.05 and 0.01 mm: for each mesh, take the largest distance whose result does not increase the non-manifold count and preserves the UVs. Both conditions are checked automatically. The weld preserves loop UVs (verified 100% on 15 meshes).
3. Delete coincident duplicate faces, degenerate faces and loose geometry; recalculate normals.
4. Exit gates: non-manifold count after is no higher than before, the share of non-zero UVs is unchanged, and a render shows no black patches (black patches are flipped normals).
5. Open edges that are there by design (single walls, strips) stay. DayZ renders them. They only matter for a watertight check or an interior ambient occlusion bake.

Zero-length face normals exist in real meshes, and zero-area faces crash naive code. Every script in this skill guards them, but garbage in still means specks out.

## Blender API traps

Each of these cost at least one wrong result.

1. **Stale `loop_triangles`** (hit twice). Cached references to `me.loop_triangles` go stale after any round trip through edit mode. The result is silent corruption or an `IndexError`. Rebuild the cache after each `mode_set`. The symptom of the corruption was two UV layers that ended up byte for byte identical.
2. **Layers contaminating each other** (hit three times, a different root cause). Building several UV layers with operators (`smart_project`, `unwrap`, `pack_islands`) in one headless session can leave a pair of layers byte for byte identical even though different pipelines made them, with no stale cache involved. Two defenses, both mandatory: compare every pair of layers for byte equality at the end of any build with more than one layer (`foreach_get` into numpy arrays, then `array_equal`), and rebuild the affected candidate on its own in a clean session with one layer. Equal *metrics* between two methods are not the bug: density normalization plus a global pack push any re-projected field to the same statistical balance (about the same island count and px/m). Only equal *data* is a bug.
3. **`bpy.ops.uv.smart_project` ignores the face selection when headless and unwraps the whole mesh.** This is the most severe. Four different pipelines that each "re-projected only the selected faces" all converged on layouts of exactly the same 2,043 islands, which was `smart_project` at 45° over everything. The symptom is identical island counts from supposedly different methods. To re-project specific faces, do not use the operator: project them by hand onto a plane (an orthonormal basis of the cluster's dominant normal, UVs written directly), which is scoped by construction. `uv.unwrap` and `pack_islands` do respect the selection (measured indirectly: packing by section worked).
4. **`bm.to_mesh(me)` invalidates earlier RNA references** such as `me.uv_layers[...].data`. Fetch them again after each `to_mesh`.
5. **Never deduplicate bmesh loop-UV wrappers by `id()`.** The wrappers are transient and their ids are recycled, so loops get skipped silently. Each loop owns its UV; visit each loop once. `loop.index` has the same problem: it is not guaranteed to be initialized. Key corners by `(face.index, vert.index)`.

A general tell: numbers that are exactly 100% or exactly 0.000, or two results that are exactly equal, point at a tool artifact before they point at the model.

## Proving zero overlap

A Monte Carlo overlap estimate has a noise floor of about 0.05 to 0.15% and cannot assert "zero". The exact test is a 2D triangle against triangle separating-axis test (SAT) on candidate pairs from a spatial grid: interiors that intersect count, touching at a boundary does not (epsilon 1e-9). About 74k triangles give about 10^5 candidate pairs, which takes seconds in Python. Say "no overlap" only when the SAT pair count is 0. This matters for any tool that bakes or paints on the atlas, such as Substance Painter. The skill's `sat_gate.py` is this test.

## Fewer islands: cut by topology, not by angle

The user's reference was a whole object (a wheel) as **4 or 5 islands**, not hundreds. The rule that cost about 12 dead-end iterations to learn:

**Fragmentation does not come from the geometry. It comes from the algorithm cutting at every sharp edge.**

Measure the shells first (the edge-connected components). The quad-bike wheel has 15 shells and the bodywork 13. The **island floor is the shell count**, because an unwrapper cannot merge disconnected shells. With 13 shells the target is about 13 to 30 islands, not 500 to 2,000.

Methods that fragment, measured on the tire (7,056 faces, 1 shell):

- `smart_project` at any angle: **1,115 islands**. It splits at every tread block.
- Working on the authored UVs, which are already fragmented: 500 to 2,000.
- Stitching slivers together: 544. Better, still terrible.

All of them attack the symptom.

**The method that works is a topological cut followed by an unwrap that resists folding:**

1. **Open the closed shells.** A closed shell of genus 0 (a sphere, a box, a cap) has trivial homology, so tree-cotree gives it no cuts, it stays closed, and LSCM fails with "Unwrap failed to solve". Mark the edges of one seed face per closed shell as seams (a slit). Each shell becomes a disk with a boundary, which can always be solved.
2. **Tree-cotree**, the minimal homological cut. Build a primal spanning forest on the vertices, shortest edges first, which gives clean cuts. Build a dual forest on the faces over the manifold edges that are not in the primal forest. The edges in neither tree are the cut graph (the homology generators): mark them as seams. Each shell opens into a disk with the minimum number of cuts, 2 per handle.
3. **`unwrap(method="MINIMUM_STRETCH")`**, the SLIM solver. It resists folding and closes without overlap far better than `ANGLE_BASED` or `CONFORMAL`.
4. Bisect the few badly folded islands along their PCA axis (8% threshold), in **one single pass**. The loop cascades when iterated: 26 islands became 508.
5. Normalize density, then pack with the `CONCAVE` shape method.

Measured result: **wheel 29 islands (3,261 px/m at 2048), bodywork 22 islands (857 px/m, 13 SAT pairs, almost clean)**, against 508 to 2,000 for every earlier method. The layout is legible: the tire caps are 2 disks, the rim is a cross, the tread is one sweep.

The honest residual: closed **curved** shells (a tire carcass, domed caps) keep minor self-overlap after LSCM. Re-projecting them onto a plane folds them worse, because they are not developable, and more cuts fragment them. An artist relaxes them or adds one seam per shell in seconds. Automatic, perfect zero overlap on a closed curved surface is a hard problem that even RizomUV's automatic seams only half solve.

No script for this cut is shipped; `sat_gate.py` is the exact overlap check it relies on. Two later measurements limit the method (see "Known traps" in `SKILL.md`): with seams this sparse, SLIM can collapse most triangles to zero UV area without a warning, and the view-chart method in `uv_view_charts.py` replaced it as the default for vehicle panels.

## Repairing an existing layout

**Stitching small islands** reduces fragmentation when the user asks for "larger groups". Stitch island S to the neighbor N with which it shares the most mesh boundary, using a **similarity transform** (as a complex number, `s = (b2 - b1) / (a2 - a1)`) that aligns the shared edge. It is conformal, so it cannot wrinkle. The final recipe (the fourth version):

- Normalize density first, so a correct stitch has `|s|` close to 1; reject outside 0.75 to 1.33.
- Add an **absolute** density guard of 0.6 to 1.6 after each stitch. Without it, chains of stitches accumulate drift (a p5 of 0.027 was measured).
- Check the stitched island does not overlap N, by sampling 8 points per triangle.
- Try the top 3 neighbors; sweep until nothing changes.

Result: 865 clean merges, 2,054 islands down to 544, p5 density 0.245. Ruled out with data: a rigid weld of the whole shared boundary, which wrinkles the faces along the seam (p5 0.031).

Local folds between **adjacent** faces are not fixed by translating them, because they move together. Re-project the cluster onto a local plane instead.

**Splitting a folded island without re-projecting it** keeps the authored unwrap. Walk the island breadth first by mesh adjacency, accepting a face into the current sub-region as long as the mapping stays injective (test overlap by sampling against a grid of the region). A blocked face opens a new sub-region. Sub-regions 1 to n are then moved outside the tile (+2k in U for sub-region k), which breaks loop continuity so the packer treats them as islands of their own. Measured: 16 folded islands became 2 to 5 sub-regions each, the original density was preserved (690 px/m at 2048) and overlap fell from 88% to 0.2%.

## What pack_islands does and does not do

Measured 2026-07-06:

1. **It does not normalize the selection into the 0 to 1 tile.** It leaves the content near its current scale and tile (`CLOSEST_UDIM`). Any remap after packing must measure the real bounding box. A blind remap crushed some groups about 40 times.
2. **Packing by zones costs about 30 to 36% of the global density.** In a global pack the dust (tiny islands) fills the gaps between large islands. Reserving a band for it leaves those gaps empty (the quad bike: 703 px/m against 449 px/m). Visual order in an atlas has a measurable price; let the artist who uses it decide whether to pay.
3. It optimizes area, not legibility, and it shuffles rotations. That is why the skill's final pack for a paint atlas is the shelf packer, not `pack_islands`.
