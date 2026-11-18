# Collision hulls and baked mass with py3d

How to check a model's baked mass and centre of mass offline with `binarize.exe` instead of a full build and spawn, how to build a collision LOD from a convex hull with py3d, and the needle triangles a hull can carry that rays pass through.

Tool knowledge about the py3d in `scripts/tools/py3d` and DayZ Tools, measured on mod models offline and in game. Vanilla models on `P:\` are binarized (`P:\DZ\gear\camping\wooden_case.p3d` starts with the bytes `ODOL`), so none of this is checked there.

## Mass and centre of mass, offline

A vehicle's mass and centre of mass are not in config: Binarize bakes them from the point masses of the Geometry LOD (`_shared/vehicles/vehicle-geometry-and-mass.md`). To see what the engine will use, binarize the model, but not through a full build, deploy and spawn, which takes about 5 minutes. Addon Builder calls `binarize.exe` with the same bake, so calling it alone gives the same result in about 30 seconds:

```cmd
"<DayZ Tools>\Bin\Binarize\binarize.exe" -always -maxProcesses=0 -addon=<addonDir> <srcDir> <dstDir> <wildcard.p3d>
```

`<DayZ Tools>` is the DayZ Tools folder, which `/dayz-preflight` finds. Then read `ModelInfo.CoM` and the inertia from the binarized file.

The source should sit under `P:\` for Binarize to resolve the model's material paths. Run from a folder outside `P:\`, a quad's materials failed to load but the mass bake still worked (checked against a control), so outside `P:\` is fine when only the mass and centre of mass matter. On another vehicle import, direct calls from outside `P:\` did not load the materials with or without `-addon`, while Addon Builder builds staged outside `P:\` resolved theirs; the location is one lead among several (`skills/dayz-build-pbo/references/binarize-file-lookup.md`).

Use this loop for any change to mass, centre of mass, ride height or placement of a vehicle, together with the check that only the Geometry LOD has a `#Mass#` entry (`py3d-assembly-rules.md`, "Mass only on the Geometry LOD"). With `ECE_PLACE_ON_SURFACE` the spawn height follows the baked centre of mass, not the lowest Geometry point, LandContact or the bounding box; measured, the origin sits at about the centre of mass height minus the lowest Geometry point. A model whose mass never bakes (centre of mass 0) spawns with its origin at ground level, underground, and is thrown out, and no change to the geometry fixes that until the mass bakes. Removing LODs one at a time is what isolates this fault (`dayz-p3d-audit/references/vehicle-checks.md`).

Two small scripts make the loop quicker and do not ship with this repo: a reader of the binarized `ModelInfo` block that says whether the mass was baked, and a script that strips the mass entry from the Fire Geometry LOD.

## A collision LOD from a convex hull

py3d can build collision geometry as well as read it. The parts it uses:

| Object | Fields |
|---|---|
| `Point` | `coords`, `flags`, `mass` |
| `Vertex` | `point_index`, `normal_index`, `uv` |
| `Face(all_points, all_normals)` | `vertices`, `flags`, `texture`, `material` |
| `Selection(all_points, all_faces)` | `points`, `faces`, both dicts |
| `LOD` | `resolution`, `points`, `facenormals`, `faces`, `selections` |

Faces point at normals by `normal_index` into the LOD's `facenormals` pool, not inline.

A cylinder collider, for a wheel say:

1. Build a ring of N points in the Y Z plane and pass them to `scipy.spatial.ConvexHull`. Its `simplices` are the faces and its `equations` give the outward normals.
2. The `simplices` come in no fixed winding. Read every face with the per component check (`dot(outward, cross_n) < 0` on every face; `generated-model-rules.md`, "The per component winding check") and reverse with `face.vertices.reverse()` the faces that read outward.
3. Store the negated `hull.equations[i, :3]` as the normal of every face, reversed or not: the equations point outward on every face, and the MLOD wants winding and normals both inward. On a 12 sided cylinder (scipy 1.17.1), 22 of 44 faces came wound outward; reversing those and keeping the outward normals on the other 22 left py3d at 50 % agreement with `WARN_WINDING_NORMAL_MISMATCH`, while negating every normal read 100 % with no finding.
4. Add one selection `component01` over all points and faces, then copies at View Geometry (`6e15`) and Fire Geometry (`7e15`) as needed.

A finding that the collider is wound against the visual LOD (`ERR_WINDING_INVERTED`) only prompts the per component check. Never reverse a collider just to match the visual LOD.

## Needle triangles

Qhull can leave a needle where it triangulates a flat face of the hull with nearly collinear points on its edge: a triangle whose area over the square of its longest edge is about 1e-7. A filter for degenerate faces that reads the polygons before they are triangulated does not see it.

Measured in game on a mod building whose hulls were built with py3d and `scipy.spatial.ConvexHull`: two components of a lid, with needles of 4.6e-7 and 1.6e-7 and areas of about 3e-8 m², took no `scene_raycast` ray in `geom`, `view` or `fire` anywhere round their outline, while the lid's other two components (1.8e-4 and 8e-4) were hit. Each hull was closed and convex, had mass and was wound inward, and Binarize said nothing. Dropping from each component the point opposite the longest edge of its needle (one point per component; the hull shrank by less than 0.3 µm) and building the hull again made both components take the rays, with the lid closed, in all three LODs.

`/dayz-p3d-audit` reads every triangle of the components of the Geometry, View and Fire Geometry LODs (a quad as two) and fails one under 1e-6 m², or under 1e-4 of the square of its longest edge, naming the point to drop (`dayz-p3d-audit/references/collision-mesh-hygiene.md`, "Needle triangles"). Those are the audit's thresholds; the engine's own limit lies between 4.6e-7, which failed, and 1.19e-4, which worked.

## Run a LOD adding script once

A script that adds LODs is not safe to run twice: run again over its own output, it duplicates the LODs and the model is invalid. Make it skip a LOD whose resolution already exists, or run it only on the original or a backup.
