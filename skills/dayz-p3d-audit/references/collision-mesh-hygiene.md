# Collision mesh hygiene

Covers the mesh faults that make a convex collision piece fail without a word: needle triangles, zero-area faces, points left without a face, and hulls that are not quite convex. How to assemble collision from many pieces is in `_shared/models/building-collision-limits.md`; the generated hull procedure is in `_shared/models/py3d-collision-and-mass.md`.

These are measured results from mod models, in game and offline; they are not checked on `P:\`, where vanilla models are binarized.

## Needle triangles

A needle is a triangle that is almost a line: tiny in area, or tiny against its longest edge. Convex hull builders make them when two points nearly coincide or a point sits a hair off an edge.

Measured in game on a rock model whose collision is many convex hulls: two hulls built with Qhull that each held one needle took no ray in `geom`, `view` or `fire`, and binarize said nothing. Built again without the point opposite each needle's longest edge, they took every ray. The engine's own limit lies between a ratio of 4.6e-7 (no hit; that needle had an area of 3e-8 m²) and 1.19e-4 (hit).

**Detection.** `audit_p3d.py` (`check_collision_needle_triangles`) reads every face of every `ComponentNN` selection in the Geometry, View and Fire LODs, in any case of the name:

- A quad is read as the two triangles of its fan.
- It fails a triangle (CRITICAL) whose area is under 1e-6 m², or whose area over the square of its longest edge is under 1e-4.
- A face at weight 0 is not in the selection.
- Proxy triangles are left out by the rule the DayZ fork of py3d uses: a selection named `proxy:<path>.<index>` that holds exactly one triangle and exactly that triangle's corners. A selection under a proxy name with any other shape is read.
- A face in no component belongs to the coverage check (`killers-detail.md`, "Parts left out of every component"), not this one.

**Fix.** Build that hull again without the point the finding names, the corner opposite the needle's longest edge. The procedure for generated hulls is in `_shared/models/py3d-collision-and-mass.md`, section "Needle triangles".

## Source meshes for collision

Measured offline on a building generated from Blender whose collision is hundreds of convex pieces (a rock with a helicopter interior).

**Zero-area faces, then orphan points.** 5.4 % of the rock's faces and 11 % of the lift cabin's had zero area. Drop them, then write only the points the remaining faces use. After the drop, 8 points stood 1.5 to 10.8 cm off the surface, all of them corners of dropped faces, and a point with no face spoils any bounding box computed from `lod.points`.

**Faces against their normals.** The same meshes had about 240 rock faces and 38 interior faces wound against their stored normals. That disagreement does not say which side is wrong, and smoothed normals can point against a face that is right (`winding-absolute-check.md`, "Reading rules"). Read those faces with the Check A table (`winding-diagnostics.md`) on the MLOD after the Blender to DayZ conversion, not on the Blender mesh before it, and before reversing any. Turning each face to its normals, as that build did, is not checked in game.

**Hulls from `bmesh.ops.convex_hull` are not exactly convex.** It merged near-coplanar triangles into n-gons that are not planar, and once fanned back into triangles those folded by a few millimetres; near-duplicate points made slivers whose plane is noise. Recomputing each hull with Qhull (`scipy.spatial.ConvexHull`), after welding points at 1 mm and dropping the point that made a sliver, left no open or non-convex piece.

**Test the convexity check itself.** Feed it a model built to fail, and make it require the models it expects: a check that finds no files must fail, not pass.
