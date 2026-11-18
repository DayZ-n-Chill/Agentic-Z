# Making LODs

How to reduce a visual LOD without losing a feature, the vertex and normal limits that make the game drop or crash on a LOD, the Blender object names that Object Builder's FBX import turns into LODs, and the ceiling on the number of LODs.

What each LOD type is for, its resolution value and the rules for Geometry, Fire Geometry, View Geometry, Roadway and shadow LODs are in `lods.md`; the resolution values are in the Tier 2 table in `_shared/conventions/assets.md`. Vanilla models on `P:\` are binarized (`P:\DZ\gear\camping\wooden_case.p3d` starts with the bytes `ODOL`), so the limits and figures below are format knowledge or measured on mod models and are not checked on `P:\`. A very large building whose collision Binarize rejects is in `building-collision-limits.md`.

## Reducing a visual LOD

Decimate of type DISSOLVE merges faces that lie in one plane into ngons, and a `.p3d` stores only triangles and quads, so those ngons have to be triangulated again. A curved body has few faces in one plane: dissolve merges almost nothing, and triangulating what it does merge raises the count. On a quad vehicle mod, LOD 1 made by planar dissolve had 122k triangles, more than the 60k of LOD 0. Do not use planar dissolve on curved bodywork.

To reduce a LOD and keep one feature whole (a radiator grille, a logo, a badge), use Decimate COLLAPSE with a protected vertex group. Build a vertex group from the feature (often it can be picked by material) and set `vertex_group=<group>`, `invert_vertex_group=True` and `vertex_group_factor=1.0`. It reduces exactly like plain collapse and leaves the feature alone. On the same quad, ratios 0.5, 0.25 and 0.1 gave 78k, 39k and 15.6k triangles with the 37 face grille kept at 37 each time; plain collapse cut it to 26, 9 and 3.

Count the triangles of each LOD again after decimating. Decimating a LOD the player sees needs the user's approval first (`generated-model-pipeline.md`).

## Vertex and normal limits

A LOD holds at most 32,768 vertex normals. Past that the game crashes or draws the LOD invisible. No file on `P:\` states the limit. A LOD that does not show in Buldozer is the first sign the model is over it.

For a vehicle, or any model that carries attachments, count the whole LOD 0 as the game builds it: the body mesh plus every wheel, light and attachment proxy, each counted once per copy (four wheels, two headlights), not once per source file. On that sum the ceilings are about 32,768 normals and about 65,536 vertices, the ranges of a signed and an unsigned 16 bit index (measured on a mod vehicle import, not checked on `P:\`). Go over either and the game crashes on load or draws the LOD invisible, which is slow to track down because each part's own `.p3d` looks fine alone. Budget against both before you make proxies and LODs; `/dayz-p3d-audit` prints the LOD 0 vertex budget of a model.

Traps when trimming to fit:

- Normals nothing points at. Cutting faces with py3d without reindexing leaves unused entries in the normal pool, so the count does not drop. Count the normals that faces use, not the length of the pool.
- Weld first. A triangle soup has three times as many vertices as faces; merging vertices that sit on the same spot cuts the count for free before any decimation.
- Two LODs at one resolution. Two LODs with the same resolution value make an invalid LOD set; each lower LOD needs a strictly larger value.

How Binarize itself counts and where it stops is in `_shared/vehicles/binarize-vertex-budget.md`.

## Face direction

Which way faces must be wound in each LOD, the Blender to DayZ axis map and how to tell a correct export from one that is inside out or mirrored are in `axes-and-winding.md`. The Blender checks before export are in `blender-winding-flips.md`.

## Object names for the FBX import

Object Builder assigns Blender objects to LODs on FBX import by their names:

| Object name | LOD |
|---|---|
| `{selectionName}_LOD__{resolution}` (two underscores) | Resolution LOD |
| `{selectionName}_LODGeometry` | Geometry |
| `{selectionName}_LODFireGeometry` | Fire Geometry |
| `{selectionName}_LODViewGeometry` | View Geometry |
| `{selectionName}_LODShadowVolume` | Shadow volume |
| `{selectionName}_LODMemory` | Memory |
| `{selectionName}_LODRoadway` | Roadway |

For a simple box: `LOD0_LOD__0.000` and `LOD0_LOD__1.000` are resolution LODs 0 and 1, `Component01_LODGeometry` is a Geometry component and `Component01_LODFireGeometry` a Fire Geometry component.

In Object Builder's import dialog:

- Tick "LODs".
- Set Master Scale to 0.01; Blender exports 100 times too large.
- After import, run Structure > Squarize All LODs to clean up the triangles.
- After import, run Structure > Convexity > Component Convex Hull on the Geometry LOD.

## Number of LODs

Keep the total number of LODs in a model under about 30: 30 or more in total can crash the binarizer (Bohemia tool documentation; not checked on `P:\`). The count covers every type together (resolution, Geometry, Fire, View, shadow, Memory, Roadway and the rest), not just the resolution LODs. The usual set (copy LOD 0, decimate to about 50 %, 25 % and 12 %, set textures and sections before cutting so they carry over) is above and in `blender-headless.md`.
