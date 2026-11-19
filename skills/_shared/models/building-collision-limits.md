# Collision of a very large building

How to build the collision of a large building with rooms inside so that it follows the visible walls and still passes Binarize, which can reject a collision LOD with no message at all.

Every figure here was measured offline on one mod model: a rock shaped building made in Blender, with a hangar, an attic, a ground floor room and a lift inside, whose collision runs to hundreds of convex pieces per LOD. None was measured again on another model, and none can be checked on `P:\`, where vanilla models are binarized. For scale, the vanilla barn `P:\DZ\structures\industrial\farms\barn_wood1.p3d` stores 564 components in its largest collision LOD (`lods.md`, "Geometry"). The everyday LOD limits are in `lods-authoring.md`.

## Source file size grows with the square of the pieces

With 1,150 pieces in Geometry, View and Fire Geometry the source MLOD weighed 478 MB. With 827 to 997 pieces of 6 points each, and a separate, coarser View Geometry that kept only the pieces that matter for actions (doors, buttons), it weighed 55 to 75 MB. The binarized file does not carry this cost: 78.4 MB of MLOD became 2.1 MB of ODOL. The MLOD does, and in a Git repository it needs LFS past GitHub's 100 MB. The separate View Geometry did not hold up: its own pieces left 28 % of the skin open to rays and passed 2,048 components, so the View Geometry went back to the Geometry's pieces.

Why the size grows that way follows from the format: an MLOD stores each named selection as one byte per point and one byte per face of its LOD, and every `ComponentNN` is a selection. The py3d in `scripts/tools/py3d` writes `len(all_points) + len(all_faces)` bytes per selection. N pieces of k points and f faces each make a LOD of about N times k points and N times f faces, so their selections take about N² times (k + f) bytes in each collision LOD.

Before assembling, clean the source meshes and check the hulls: faces with no area, points no face uses, faces wound against their normals and `bmesh.ops.convex_hull` hulls that are not exactly convex are in `dayz-p3d-audit/references/collision-mesh-hygiene.md`, "Source meshes for collision".

## Which room a point belongs to

Inside surfaces are open meshes; floors and ceilings are separate objects. Near their edges, cross sections of the lining, upward rays and the side of the nearest surface all put points in the wrong room. What worked:

- Extrude each patch behind its visible side up to the next visible surface along a ray, stopping 3 cm short.
- Give moving parts hard volumes worked out by hand: the platform's travel, the lift cabin, the doors.
- Make floor slabs by convex decomposition of their outline, with convex holes cut by half planes.

## Collision that follows the visible face

1. Build prisms per region of nearly flat faces, not per random sample cluster. Patches from k-means clusters of random samples stood far behind a tightly curved wall: the hull's chord entered the room, and the cut that removed it left the patch far back. On the hangar lining 38 % of the wall had its collision more than 15 cm behind, and the corners up to 1 m, the limit of the probe. Prisms per region, each extruded from 0.5 cm behind the region's deepest face toward the next visible surface behind it, gave a median of 1 cm and less than 2 % beyond 15 cm. The extrusion aims to stop 3 cm short of that surface; a cap on depth and a minimum thickness of 1.5 cm can leave a smaller gap, so check the clearance you get. That reading covers the prisms alone, before the room test thins, splits or drops a prism that enters a room.
2. Extrude along the face's own geometric normal turned to its visible side, not along the mean of its corner normals. Next to a crease the smoothed normal leans by up to about 45 degrees, and prisms along it stood up to a face's width behind their far corner (median 10.5 cm); along the geometric normal, 1 cm.
3. Grow the regions by position, not by shared edges. The room meshes, like the skin, are triangle soups: 1,872 faces gave 1,843 regions when neighbours had to share an edge, and 652 when corners closer than 2 cm counted (flatness tolerance 8 cm).
4. Test a room with floor below, ceiling above, and three of four horizontal rays hitting the visible side of the walls. A test that looks only down and up counts the rock of a door's lintel and jambs as room: the pieces there were dropped and a 0.84 by 1.55 m gap opened (131 of 368,013 samples of the hole probe). A room's ceiling can also be another object, such as the slab of the room above; without it the vertical test missed the room almost everywhere, and pieces entered it by up to 0.40 m.
5. Test every outside triangle, not random samples. Four passes of 60,000 random samples left 0.15 % of the skin open at the seams; testing every outside triangle at 7 points finds the ones with a hole in one pass.

## Binarize and the visual LOD

Binarized with its visual LOD 0 only, textures and materials on, the whole building in one model with smooth normals failed with `CAPACITY_FAIL` at 92,430 resolved vertices (py3d's count of distinct point, normal and UV triples). Split into the rock (49,929) and the interior with smooth normals on its inner face (42,501), both passed. The rock passed above the limit of 46,133 measured on a helicopter import, so that figure does not carry over to another model (`_shared/vehicles/binarize-vertex-budget.md`). Split normals on a height field more than triple its resolved vertices: the attic's inner face, 33,046 triangles, counted 56,743 with split normals and 17,392 with smooth ones (a lower bound, counted in Blender).

## Binarize rejects a collision LOD without a message

With 1,843 convex pieces in Geometry, View and Fire Geometry, `binarize.exe` wrote no ODOL and printed no capacity line; a wrapper that sorts runs into pass, capacity failure and other failure read `OTHER_FAIL`. It is not the file size: a 247.8 MB MLOD failed and a 264.4 MB one passed. Without its collision LODs the same model passed.

The boundary over 9 variants, read per collision LOD (a variant without its View Geometry failed like the full one; which measure is the real limit was not isolated):

| Per collision LOD | Largest that passed | Smallest that failed |
|---|---|---|
| Faces | 28,124 | 32,766 |
| Named selections times points | 31,494,324 | 33,889,401 |
| Selection bytes | 81,723,788 | 83,726,487 |
| Pieces | 1,786 | 1,501 |
| Points | 22,281 | 22,281 |

The first three rows separate the passes from the failures equally well (2^25 = 33,554,432 lies between the two products); the piece count and the point count alone do not. A cap of 32,768 faces cannot be the only limit, since 32,766 already failed; one alongside another limit is not ruled out. A variant with few faces and many selections would settle it and was not run.

A truncated MLOD gives the same `OTHER_FAIL`: one variant was cut off while being written, inside its Geometry LOD. Before reading an `OTHER_FAIL` as this limit, walk the MLOD to the `#EndOfFile#` TAGG of every LOD.

What to do before binarizing:

1. Measure each collision LOD with a header reader. Points and faces are in each LOD's `P3DM` header, and the named selections and their bytes in its TAGG list, which a reader skips through by each TAGG's size without loading the file (seconds for 350 MB).
2. Where any of the first three measures is above the largest value that passed (first column above), move pieces to a second model placed with the same transform, created and deleted together with the main one. Do not merge or decimate pieces to fit.
3. Treat those values as one model's safe bounds, not a pass mark: Binarize still decides for every model that results.

The second model works in game: a collision only `House` class of 602 pieces, spawned with the rock at its transform. A `geom` ray cast from 30 m out toward the rock stopped on one of its pieces, and 1,188 rays per LOD from outside found no holes in Geometry, Fire or View Geometry. No Fire or View Geometry ray was checked against that model's pieces on their own.

## Binarize reports `Too many vertices` from the collision LODs

In a later build the rock failed with `CAPACITY_FAIL`, a `Too many vertices` line naming its MLOD, even with its visual LOD put back to a version that had passed: its collision had grown. Read from the MLOD (14 LODs, three of them collision LODs):

| Build | Pieces per collision LOD | Points per collision LOD | Points, all LODs | Points, visual LOD 0 | Result |
|---|---|---|---|---|---|
| The build in use | 1,241 | 16,370 | 93,935 | | pass |
| A build that passed | 1,240 | 16,325 | 94,091 | 25,230 | pass |
| The failing build | 1,263 | 16,582 | 96,409 | 26,891 | `CAPACITY_FAIL` |
| The failing build, visual LOD 0 put back | 1,263 | 16,582 | 94,750 | 25,232 | `CAPACITY_FAIL` |
| The failing build without its last 33 outside pieces | 1,230 | 16,094 | 93,286 | | pass |

For this model the limit lies between 1,240 and 1,263 pieces per collision LOD, or between 94,091 and 94,750 points over all LODs; these builds cannot tell which. Named selections times points in one collision LOD do not explain it alone: the interior model of the same addon passes with about 1,800 selections of 17,641 points in its one collision LOD. Nor is it the silent limit above, since Binarize printed `Too many vertices` here. Capping the rock at 1,230 pieces and moving the rest to the collision only model passed Binarize 6 times out of 6.

On a `CAPACITY_FAIL`, compare every LOD of the last build that passed with the failing one before blaming the latest change. Here the visual LOD had changed in the same build and was blamed first; put back as it had passed, the model still failed.
