# Rip geometry and winding

Geometry work on a ripped vehicle mesh: automatic retopology, winding rules for proxy triangles and visual faces, where `autocenter=0` belongs, how to check and fix winding per connected part, and how to delete faces from a `.p3d` without breaking selections.

The vanilla reference is `P:\DZ\vehicles\wheeled\civiliansedan\civiliansedan.p3d` with its interior proxy `P:\DZ\vehicles\wheeled\civiliansedan\proxy\prox_int.p3d`. Both are binarized and py3d cannot read them, so the winding and normal figures here were measured on converted copies and on test vehicles, a car and a helicopter (**model knowledge**). The winding rule for an imported car (keep the raw glTF winding) is in `invariants-import-mesh-and-winding.md`; the import route is `rip-import.md`.

## Retopology of a dense rip

To turn a dense rip into a clean low poly mesh for baking and UVs:

- Voxel remesh does not work for hard surfaces: it melts panels into blobs and loses holes and edges (seen on a 37k triangle car body). Quadriflow per panel does: split by loose parts, mark sharp edges at 35 degrees, then remesh each part with `use_preserve_sharp` and `use_preserve_boundary`. Remeshing the whole body at once gives worse flow.
- `bpy.ops.object.quadriflow_remesh` reporting "Remeshing failed" on a clean mesh (no boundary, no non-manifold edges, Euler number 2) means the target is too low, not that the geometry is dirty. The solver gives up when `target_faces` cannot place singularities for the detail. Sweep the target upward on throwaway copies (Quadriflow is destructive) and keep the leanest target that gives quads with at least about 0.4 times the faces you want. An 8972 triangle fender failed at targets 100 to 1800 and worked from 2600. `remove_doubles`, making manifold and dissolving degenerates do not help on a mesh that is already clean.
- Quadriflow gives an even grid; it does not follow edges like hand retopology. That is right for baking to a low poly mesh, because the normal map carries the detail, and a vehicle panel does not deform.
- Leave pieces under about 200 triangles (clips, bolts) as they are. Recalculate normals outward on join, and watch panels modelled with thickness: the inner face goes dark, and the game mesh wants a single face.

On a test vehicle seat this took 36899 triangles to 10502 quads, 72% fewer. The solver behaviour is measured; the full automatic retopology route has not been checked in game. Check mesh and UVs afterwards (`invariants-import-mesh-and-winding.md`) and map UVs as `_shared/models/uv-mapping.md` describes.

## Rewriting a proxy triangle

Moving the three points of a proxy triangle to change its orientation flips the geometric winding while the stored vertex normals stay as they were: on a test helicopter `dot(geometric, stored)` went from `+1.0` to `-1.0` on all three proxies. A pure translation keeps the winding.

So a check of a `.p3d` edit asserts `dot(geometric, stored) > 0.9` on proxy triangles only. A hull built with reversed winding on purpose has a negative dot on every visual face by design: on the test helicopter one door had 7227 dots per LOD, none above 0.9, median `-0.942910`. Applying the proxy rule to visual faces fails every valid face, and "fixing" that by flipping normals breaks the model. For edited visual faces, compare the resolved normal with the original corner by corner, within 1e-6.

## Where `autocenter=0` belongs

Vanilla sets `autocenter=0` on the `ProxyVehiclePart` config class (`P:\DZ\vehicles\wheeled\config.cpp:23901` to `:23905`). That config key is separate from the per-LOD `autocenter=0` property measured below.

On a working reference vehicle all five sub-models with geometry carry the LOD property on their visual LOD and their Geometry LOD. The host model has no properties on its visual LOD. So the property belongs on the sub-models, not on the host. Two limits on what it does:

- The usual sign, `model_info.bounding_center` not zero after binarize, can be absent while the visual LOD property is missing: an empty Geometry LOD carrying `autocenter=0` already stops binarize from re-centring.
- Binarizing with and without the property on the visual LODs gave the same result in all 66 `model_info` fields and the same face counts per LOD; only the property block differs. The property reaches the ODOL and can be checked there, but any effect happens at run time. Settling it needs an in-game A and B test: two PBOs that differ only in the property, with a repeatable camera pose.

## What a winding check must cover

1. The whole part, not the part you touched. A fix that flipped only the paint material and checked only paint read 97.9% to 99.5% correct, while two other materials (4,460 and 315 faces per door) stayed inverted. Count every material of the part, faces agreeing and disagreeing with their stored normals.
2. Every LOD that draws, including 1100. The View Pilot LOD is a copy of LOD 1, so fixing LOD 1 and skipping 1100 leaves first person broken: one driver door still had 4,341 faces to flip, almost all in its 1100.
3. Double-sided pairs have three states. A healthy pair has both faces agreeing with their own stored normals. A group where all faces disagree was inverted whole by an earlier global flip; flip all its faces, which keeps the two sides opposite. A mixed group cannot be settled offline: skip it and warn. Skipping every pair leaves the all-disagreeing pairs broken and the count still reads clean.

A count after the fix that reruns the same test as the fix can only fail if the flip did nothing. Compare the flipped counts per material against a prediction made before the fix; whether the stored normals themselves are right can only be settled in game.

## Game winding is the reverse of MLOD winding

Measured twice in game against a known good part: a face draws when its MLOD geometric winding looks into the blocked side of its shell. The import transform is a reflection, so the rasterizer sees mirrored winding, while stored normals pass through unchanged for lighting. The body of the test car worked only because its rip normals came out mirrored too and the body builder aligned winding to them, which cancelled out. A part built another way, such as doors from a later cut, breaks that, and flips by material, by stored normal or per face never converge.

Fix winding per connected part:

1. Classify each face by casting rays both ways from its centroid against the part's own mesh: open, blocked, rim or enclosed. A face is right when it looks into the blocked side. Prove the classifier on a part known good in game first.
2. Group faces into connected parts by shared edges and vote within each part over open and blocked faces only; rim and enclosed faces carry no signal. A healthy mesh splits cleanly, skins near 1.00 or near 0.00. If a large part mixes both, stop: flipping it would also flip a good skin.
3. Flip whole parts that are 60% or more open, reversing faces and negating normals into new copies, never in place. Leave parts at 40% or less. Leave tiny parts (fewer than 8 judged faces) that read 50/50 alone. Any real ambiguity stops the run before saving.
4. Before writing, assert that the verdict still fits the model (face counts, index ranges). A stale verdict silently flips the wrong faces.
5. Export, classify and count again: no part may remain to flip on any LOD that draws.

Concave pieces such as mirror housings defeat ray classification. Restore them to their last state known good in game, and check the restored count against the count recorded when they broke.

A grey band over the windshield in first person was the sun visor's edge, seen because the seated camera rides high; it was real geometry. Check what the camera sees with a fan of rays before cutting anything. The fix there was the seat pose (crew proxy 5 mm lower), not a trim.

## Deleting faces by side

Classifying faces by the sign of their X centroid works for faces wholly on one side and silently breaks any surface crossing the axis. A flat panel is usually a quad of two triangles; if it crosses X=0, one triangle's centroid falls on each side and half the panel goes. In game the panels show as half triangles and half gaps. On a test helicopter 9 canopy panels of 2 faces each kept 1 face each, while the island count did not change.

1. Before deleting by side, check whether any island of the selection crosses the symmetry plane (`min_x < 0 < max_x`). If one does, decide per island or leave crossing islands out.
2. A test along one axis catches everything that shares it. A band of 0.85 m around each door anchor along Z also covered the canopy. Add a second axis (height) or compare face to face against the sub-model that holds that geometry.
3. Check offline that each island keeps its face count, or loses none or all. An island going from 2 faces to 1 is a split quad. Totals do not show it.
4. When the geometric test is doubtful, open a viewer and let the user pick. A small Three.js page with clickable islands costs less than a lost in-game cycle. Show two layers, deployed faces (click to delete) and deleted faces (click to restore), over a wireframe hull, since a solid hull hides the panels to pick, and export two id lists. Before handing it over, confirm the page loads and take a screenshot of it.

Vertices of a selection that no face uses are evidence, not garbage: on the test helicopter 357 such points on one side were the trace of 619 lost faces. Measure before cleaning.

## Deleting faces with py3d

In py3d (`scripts/tools/py3d/py3d/__init__.py`, class `Selection`), `Selection.all_faces` is a reference to the `lod.faces` list, not a copy, and `Selection.write()` checks its keys by identity against that list and raises `RuntimeError` on a foreign one.

- `lod.faces = [f for f in lod.faces if ...]` makes a new list. Every selection stays bound to the old one, and writing the LOD raises `RuntimeError` for a stale binding (`LOD.write`). Mutate in place instead, or recreate the selection with `lod.new_selection(name)`.
- Delete in place from the highest index down: `for i in reversed(cut): del lod.faces[i]`.
- First remove those faces from each `Selection.faces` (a dict keyed by face), or `write()` stops on a foreign key.

After saving, read the file back and check every named selection's count: the old count minus the faces removed from it. In one case 187 deleted faces left `glass` at 5910 of 6022, `interior` at 4383 of 4458 and `trim` untouched at 4072. A count that does not match means the deletion took something it should not have.

Before deleting, ask which selections the faces belong to. `glass` drives glass breaking, unlike a decorative selection, and losing 2% of a selection is not the same as losing 90%. Leave unused vertices in place: removing them reindexes the whole LOD and throws away evidence. And check how many LODs the part has: a headliner fix had to go into the visual LOD and the 1100, or it came back in first person.

## Comparing two builds

To check that a build changed only what it should:

1. A key meant to ignore order cannot hold section indices. A key built on `face_index_start` and `face_index_end` marked 7 of 10 untouched models as changed, because AddonBuilder reorders exactly those. Use the multiset of material, texture, face vertex indices and lighting bit, resolved through the name tables, and void the result if the sections do not cover every face.
2. Adding a texture changes `texHeaders.bin`, the PBO's texture index. Expect it, or the check fails falsely.
3. Compare `.p3d` entries by content and every other entry by bytes. A check that parses every changed entry as ODOL breaks as soon as a texture changes.
