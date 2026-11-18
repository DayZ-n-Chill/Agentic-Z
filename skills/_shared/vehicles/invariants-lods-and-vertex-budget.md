# Distance LODs and the vertex budget

How many visual LODs an imported vehicle needs, how far each way of reducing a mesh goes, how to bake far LODs that draw the right side, and how to tell offline that a model is over the engine's vertex ceiling.

The vanilla car to compare LOD counts against is `P:\DZ\vehicles\wheeled\civiliansedan\civiliansedan.p3d`; it is binarized, which py3d cannot read, so the face counts below come from a debinarized copy and are not checked on `P:\`. The other numbers were measured on mod vehicles (an imported coupe and helicopter). `binarize.exe` ships with DayZ Tools; `/dayz-preflight` checks DayZ Tools is installed.

## Build the distance LODs before cutting LOD 0

A vehicle with one visual LOD draws its full face count at every distance. The vanilla sedan ships five visual LODs (14,636, 10,364, 3,717, 1,713 and 123 faces); an imported coupe shipped one, 231k faces always, and its freeze in the admin preview and on spawn did not move with de-duplication (18.5 MiB less) or a smaller shadow LOD (32k to 3.5k), because it was bound by faces drawn. Count visual LODs against the sedan on day one; two is the floor to ship. Cutting LOD 0 itself is a last resort, and the user decides it.

- Bake distance LODs (resolution 2, 3, 4) flat into the main model, with no proxy references: proxies of LOD 0 render only while LOD 0 renders. Build them from the rip's own LODs and leave the cabin out of far LODs, as vanilla does.
- Planar dissolve (Blender limited dissolve, which keeps shape, material slots and UVs) stops at a factor of 2 to 2.6, not 5 to 8, because a rip's own LODs are mid-detail meshes. The coupe body went from 58.7k to 34.5k at 15 degrees, 27k at 30 and 22.4k at 45. That gives one good near LOD (about 27k at resolution 2). Reaching the sedan's 3.7k and 1.7k needs collapse decimation, which deforms the mesh and drops slots and UVs, so measure the dissolve ceiling and ask how far to go before promising far LODs.
- A step that assumes exactly one visual LOD breaks on a set of them. Replace the whole visual block with every working LOD below resolution 100, sorted, and keep every structural LOD. Test it on a copy first: Geometry, Memory, hit points, View Geometry and Fire Geometry must come out bit-identical (get-in depends on them), then check the deployed model against its backup. The flat body source is the shell's LOD 0 minus proxy faces, plus the part models; the cabin lives in the interior proxy. Review the baked LOD in a render before deploying (`_shared/models/blender-visual-review.md`).

## Far LODs that render black or see-through

These are two different failures:

- Black: stored normals point inward, a shading fault. The body's winding gives a cross product pointing inward (the build negates paint and lamp classes for this), so a flat LOD baked with raw cross-product normals renders about 60 percent black. Fix the stored normals.
- See-through: winding inverted, a culling fault. Faces point inward and are culled from outside.

Diagnose offline by counting the fraction of far LOD faces with `cross · (centroid - carCenter) > 0` against LOD 0, which renders correctly. On the coupe the far LOD read about 98 percent against about 17 percent on LOD 0: winding inverted. If stored normals already point outward (it reads see-through, not black), one global vertex order flip fixes it: `face.vertices.reverse()` on every face, leaving normals alone, which took the count from 98 to 2 percent, matching LOD 0. Use a majority repair per connected component only when the far LOD is mixed (low edge consistency), not merely inverted. The cause was a LOD assembler that took the dissolve winding as is with raw cross-product normals and skipped the consistency pass the shell gets; it printed `outward=38.9%` and nothing checked it.

Check every baked far LOD against LOD 0 this way before deploying; Blender cannot judge DayZ winding, because it culls the other side. The measuring tool must follow the engine's order: culling runs before the depth test, so group the hits at the nearest distance plus a small margin and ask whether any of them faces the camera. Re-read the controls whenever a fix changes the kind of geometry the tool sees. Vertex count is no constraint here: 26k resolved vertices for a 27k-face body.

## Measure the vertex ratio on what you ship

The ratio of resolved vertex triples (point, normal, UV) per triangle measured on a decimated mesh does not carry over to an authored one. Decimate collapses edges and breaks normal sharing, which inflates the ratio: on one helicopter 1.301 on a Decimate export (ratios 0.26 to 0.6 per group) against 0.941 on the source's own Medium LODs, 28 percent apart, which changed the plan from 2.43 projected sub-models to 1.75 measured. Measure on the geometry you will ship, and re-measure per model; never copy a ratio or a ceiling between assets.

If the source ships its own LODs (GTA `.yft` High, Medium and Low, a racing-game rip, Sollumz-imported datablocks), use them instead of decimating. Swapping `obj.data` to the `<piece>_medium` datablock is usually better in triples and keeps visual decimation out of the agent's hands.

## Let `binarize` decide whether it loads

`binarize` is the offline judge of whether a model loads, with three verdicts; a 65,535 limit counted by py3d is not. A model that passes every offline check and still will not spawn is almost always over the resolved vertex ceiling, so run `binarize` before touching the Geometry LOD. `PHYSICS (E): Won't simulate, it has no geometry` is the same defect as `Too many vertices`: the engine aborts while loading the MLOD, so a perfect Geometry LOD does not clear it. py3d count checks (resolved under 65,535, normal pool, digest, identical Geometry) do not clear a spawn.

- `CAPACITY_FAIL`: do not go in game.
- `OTHER_FAIL`: do not touch the geometry.
- `PASS` while the game still reports no geometry: look at serialization or another cause; an in-game spawn judges.

A model built to fail on capacity is a control, not evidence against `binarize`. How to run it, the evidence for each verdict, the measured ceiling and headroom, and why reversing corner order is free while adding a normal is not, are in `binarize-vertex-budget.md`.
