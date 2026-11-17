# LODs and geometry rules for a generated model

What goes in each LOD of a model this skill writes, the limits that make Binarize or the game reject a LOD, how face winding ties in, the Blender object names that Object Builder's FBX import turns into LODs, and one project's full record of keeping a very large building's collision inside Binarize's limits.

What is checked and what is not: lines that cite `P:\` were opened and confirmed against vanilla. The limits (vertex normals, Roadway distance, LOD count), the decimation figures and the whole building section are format knowledge or the source author's measurements on named third-party mods (LFQuad, the SecretRock building, a GLB car import); vanilla models on `P:\` are binarized, so those cannot be checked there. What vanilla models carry, with counts, is in `_shared/models/lods.md`; the resolution values are in the Tier 2 table in `_shared/conventions/assets.md`.

Evidence labels: `[OFFLINE MEASURED]` measured without the game, `[IN-GAME VERIFIED]` measured in game. Codes such as SP-453 and LL-024 are the source author's ticket and lesson numbers. Rule numbers (Rule 12, Rule 18) are the rules in `critical-rules.md`.

## Contents

- [LOD types and their purposes](#lod-types-and-their-purposes)
- [Vertex normal limits](#vertex-normal-limits)
- [Face normals and winding order](#face-normals-and-winding-order-texture-visibility)
- [Naming convention in Blender for FBX export](#naming-convention-in-blender-for-fbx-export)
- [Total LOD count ceiling](#total-lod-count-ceiling-added-2026-07-14)
- [Collision of a large building with an interior](#collision-of-a-large-building-with-an-interior)

## LOD types and their purposes

### Resolution LODs (visual)

These are what the player sees. Several LODs at rising distances reduce the rendering cost. This file does not give the distance at which the game switches visual LODs: before tuning the material of a far LOD, find out in game which LOD is drawn at that distance (`skills/_shared/vehicles/process-gates.md`, SP-483).

| LOD | Resolution value | Purpose |
|---|---|---|
| LOD 0 | 0.000 | Full detail, the closest view |
| LOD 1 | 1.000 | About 50 % of the LOD 0 polygon count |
| LOD 2 | 2.000 | About 25 % of LOD 0 |
| LOD 3 and up | 4.000, 8.000 ... | Further simplification, down to a box |

The values only have to rise. Most vanilla models count 1, 2, 3, 4 (`P:\DZ\gear\camping\wooden_case.p3d` carries 1 to 4), and the generator in this skill spaces them 0, 1, 4, 8; both load (`_shared/models/lods.md`, "Visual LODs").

Rules:

- Do not make identical copies of LOD 0 for the other levels: it wastes memory and gains nothing.
- Each lower LOD should reduce the polygon count in a way that matters.
- All resolution LODs need textures assigned (`.paa` paths).
- UV mapping must be consistent across the LODs that share a texture.

### LOD reduction: planar dissolve does not reduce a curved surface (added 2026-05-23)

Decimate of type DISSOLVE merges coplanar faces into n-gons, but a `.p3d` stores only triangles and quads, so the n-gons have to be triangulated. On a curved body, which has few coplanar faces, the dissolve merges almost nothing, and triangulating the n-gons it does produce raises the count again. Measured on the LFQuad vehicle mod: LOD1 through planar dissolve had 122k triangles, more than the 60k of LOD0. Planar dissolve does not reduce the triangle count of curved bodywork.

To reduce a LOD while keeping a specific feature (a radiator grille, a logo, a badge), use **Decimate COLLAPSE with a protected vertex group**: build a vertex group from the feature (often it can be picked by material) and set `vertex_group=<group>`, `invert_vertex_group=True`, `vertex_group_factor=1.0`. This reduces exactly like plain collapse but keeps the feature whole. Measured on LFQuad at ratios 0.5, 0.25 and 0.1: 78k, 39k and 15.6k triangles, with the grille (material B_GRAY, 37 faces) kept at 37, 37 and 37, whereas plain collapse cut it to 26, 9 and 3. Always check the triangle count of each LOD again after decimating. (Origin: LFQuad phase B, LL-024.)

Decimating a LOD the player sees needs the user's approval first (the decimation gate in `SKILL.md`).

### Geometry LOD (collision)

Defines physical collision: what stops players and objects from passing through.

Requirements:

- Every component is named `ComponentXX` (`Component01`, `Component02`, up to `Component2048`). Far below 2,048, a collision LOD with many pieces can make `binarize` fail with no message: 1,501 pieces of a building failed, and 1,786 lighter ones passed ("Collision of a large building with an interior", below).
- Every component is **convex**: in Object Builder, Structure > Convexity > Component Convex Hull.
- Every component is **closed** (a watertight mesh, no holes).
- Every component has **mass assigned** (Alt-M in Object Builder; at least 10 for a character to collide with it). Mass belongs on this LOD only (`py3d-assembly-rules.md`, "Mass only on the Geometry LOD").
- Always run Find Components (Structure > Topology > Find Components) to validate.
- The named property `class` = `house` is required for buildings. Vanilla: `P:\DZ\structures\industrial\garages\garage_small.p3d` stores `class` = `house`, `map` = `building` and `damage` = `no` together on its Geometry LOD (`_shared/models/named-properties.md`).

In Blender:

- Name the objects `ComponentXX_LODGeometry` so the FBX import assigns them.
- Use Mesh > Convex Hull in edit mode to make a piece convex, and check the result: hulls built by script with `bmesh.ops.convex_hull` came out folded by a few millimetres, and recomputed with Qhull they passed the convexity check (`dayz-p3d-audit/references/killers-detail.md`, "Source meshes for collision"). Passing it does not rule out a needle triangle from Qhull (`py3d-direct-generation.md`, "Needle triangles").
- Assign mass with the vertex mass tools of the Arma 3 Object Builder addon.

### Fire Geometry LOD (ballistics and damage)

Defines where bullets hit and what happens when they do.

Requirements:

- The same component naming rules as the Geometry LOD (`ComponentXX`), and the components must be found (Find Components).
- **Materials define penetration.** Assign a penetration `.rvmat` to every face. In DayZ they live under `dz\data\data\penetration\`; all four below exist as `.rvmat` with a matching `.bisurf` under `P:\DZ\data\data\penetration\`:
  - `dz\data\data\penetration\metalplate.rvmat` for metal objects
  - `dz\data\data\penetration\wood.rvmat` for wooden objects
  - `dz\data\data\penetration\glass.rvmat` for glass
  - `dz\data\data\penetration\concrete.rvmat` for concrete
- **Thickness matters.** The thickness of a component decides how well it resists bullets. Glass that is too thick becomes bulletproof without anyone meaning it to. Model realistic thicknesses.
- If two armor plates overlap, model them as one piece: overlapping fire geometry may cause errors in the bullet simulation.

### View Geometry LOD (occlusion and the action cursor)

Used by the engine to decide what is visible and what is hidden behind objects, and by the action cursor (`_shared/models/lods.md`, "View Geometry").

Requirements:

- The components must be found.
- It should be simpler than the resolution LOD but accurate enough to occlude properly.
- Poor View Geometry causes performance problems and gameplay problems (players visible when they should not be).

### Shadow volume LODs

Cast shadows on the ground, on other objects and on the object itself. No vanilla DayZ model carries one (`_shared/models/lods.md`), so build one only when the user asks. When one is asked for:

- It is simplified compared with the resolution LOD.
- **It must be slightly smaller than the resolution LOD**, otherwise the object appears fully dark in game (use a Push modifier in Blender to shrink it a little).
- No textures are applied.
- All faces are closed.
- Usually two are made: a detailed one for close range and a very simple one for far range. Shadow Volume 0.000 is the detailed one, Shadow Volume 10.000 the simple one (Object Builder's names; the stored resolution values are `1.0e4` and `1.1e4`, `critical-rules.md`).

### Memory LOD

Contains no visible geometry, only single vertices (memory points) that define:

- animation axes (bone pivots)
- positions of the interaction widget
- sound emission points
- overrides of the bounding sphere
- central economy points (`ce_center`, `ce_radius`)

See `memory-and-selections.md` for the memory points in detail.

### Roadway LOD

Defines where characters can walk and what sound their footsteps make. Vanilla buildings, ruins, rocks and the base building fence carry it (3,119 vanilla models, `_shared/models/lods.md`). The requirements below are Bohemia format knowledge, not shown by a vanilla file:

- Flat planes where the walkable surfaces are.
- **All faces must face up.** Faces pointing down make characters fall through.
- Textures can be assigned to define the footstep sound (wood, metal, concrete and so on).
- It must be present below ladder memory points for a ladder to work. Vanilla agrees: the climbable ladder prop `P:\DZ\structures\residential\misc\ladder.p3d` carries a Roadway LOD and the decorative `P:\DZ\structures\furniture\various\ladder_a_wood.p3d` does not (`_shared/models/building-selections.md`).
- It must not overlap the Geometry LOD, or characters wobble.
- If animated elements (bones) exist in the Roadway, it holds at most 255 points (127 in older versions).
- It reaches at most about 36 m from the model's origin, which limits a bridge to about 72 m per `.p3d`.

### Geometry PhysX LOD

A copy of the Geometry or Fire Geometry LOD for PhysX interactions (the source lists it as "Arma 3 / DayZ SA"). In DayZ it is the GeoPhys LOD at `4.0e+13`, carried by 8 vanilla models such as `P:\DZ\structures\furniture\beds\pillow_grey.p3d` (`_shared/models/lods.md`).

- Thrown objects (grenades and the like) interact with this LOD and with the Roadway LOD.
- Keep it as simple as possible: PhysX collisions are expensive.

## Vertex normal limits

- DayZ (the RV engine with DX9): at most 32,768 vertex normals per LOD.
- Going over this crashes the game or makes the LOD invisible.
- Check with Buldozer: if the LOD does not display, the model is over the limit.

### Budget on the resolved LOD0 (proxies summed; DX9 16-bit indices)

The ceiling of 32,768 normals above is per LOD, but for a vehicle or any host of attachments the figure that crashes the game is the **resolved LOD0**: the body mesh plus every wheel, light and attachment proxy resolved and counted once per instance (4 wheels, 2 headlights and so on), not once per source file. DX9 uses 16-bit indices, so the hard ceilings on that resolved sum are about **32,768 normals** and about **65,536 vertices**. Cross either and DayZ crashes on load or draws the LOD invisible, which is costly to diagnose because each part's own `.p3d` looks fine in isolation. Budget against both ceilings before generating proxies and LODs. `/dayz-p3d-audit` prints the LOD0 vertex budget of a model.

Traps when trimming to fit:

- **Orphan normals.** Cutting faces with py3d without reindexing leaves unreferenced entries in the normal pool, so the count does not drop. Measure the normals that are referenced, not the length of the pool.
- **Merge by distance before decimating.** A triangle soup has three times as many vertices as faces; welding coincident vertices first collapses the count for free before any decimation.
- **A LOD ladder with a duplicate resolution.** Two LODs at the same resolution value are an invalid LOD set; each lower LOD needs a strictly larger resolution value.

(Origin: SP-009, LL-026, bug 011 of the kt_roadkill_armed vehicle import.)

## Face normals and winding order (texture visibility)

The RV engine uses the winding order of a face to decide which side is outward (textured, visible) and which is inward (invisible, culled).

Symptoms of a wrong winding order:

- textures render on the inside of the model instead of the outside
- the object appears transparent or invisible from outside
- the object appears solid black from outside (shadow only)

**Rule (`critical-rules.md`, Rule 12).** Geometry authored in Blender and GLB or glTF geometry brought through Blender take the same det=-1 map, and neither is reversed (for a glTF read without Blender see `axes-and-winding.md`, "GLB and glTF imports"):

- **Blender authored geometry** goes through the reflection `x'=x, y'=z, z'=y` (det=-1): apply it to all vertices and normals in all LODs, keep the vertex order (it comes out inward, the MLOD convention) and negate the normals. The old det=+1 rotation `z'=-y` ships a mirrored model (measured in game 2026-10-01).
- **GLB or glTF geometry** brought through Blender is Blender geometry: glTF front faces are counter clockwise like Blender's, and Blender's glTF importer keeps them so. The same map, order and normals apply. Reversing the faces after the det=-1 map turns them outward, which rendered inside out in game (the MercedesAMGLF vehicle mod, 2026-06-24; `axes-and-winding.md`, "GLB and glTF imports").

Never assume. `check_face_winding` (`py3d-direct-generation.md`, "Face Winding Verification") must read about 0 % flipped, but it only shows that the vertex order and the normals agree: an inside out export with both pointing outward reads the same.

**In py3d:** `py3d.blender_to_dayz(model)` (py3d 1.8.0 and later) maps a model that is in Blender space; call it before adding anything built in DayZ space. With `P3D.transform(((1, 0, 0), (0, 0, 1), (0, 1, 0)))` instead, det<0 makes it reverse every face, proxy triangles included: reverse them all back and negate every normal, which leaves the original order (`py3d-direct-generation.md`, "Blender Z-up to DayZ Y-up Rotation").

**In Blender:** a GLB or glTF import needs no flip. Before export, the faces should show blue from outside in the Face Orientation overlay (the `blender-visual-review` skill). If some show red, select all faces of the mesh (not the proxy triangles), use Mesh > Normals > Recalculate Outside and check the overlay again: on an open mesh it can guess wrong. Mesh > Normals > Flip turns the selected faces inward, and Rule 12's map then turns them outward.

**Apply the map to all LODs** (Geometry, Fire Geometry, View Geometry, shadow and Memory LODs included) so that they all land in one convention. A collision LOD left outward lets the LOD raycasts through, the `view` and `fire` rays that actions and ballistic hits rely on (`dayz-p3d-audit/references/p3d-killers.md` section 1, measured in game 2026-10-02). On the 2 m boxes measured there, physics still stopped a walking player; a walk alone does not diagnose winding, since the 0.49 m `item_small` kit let the player through with either winding.

*(Aligned 2026-10-03 with Rule 12 and the GLB and glTF section. Before that this section treated GLB and glTF as a separate case: a pure swap `(x,y,z)->(x,z,y)` followed by reversing the vertex order of every face in every LOD except proxy triangles, with a py3d loop that did it, a Blender fix of "select all faces, Mesh > Normals > Flip", and a closing claim that flipped Geometry faces cause physics pass-through and flipped Fire Geometry faces let bullets through. That recipe turned the faces outward. An earlier version of the loop, three lines that reversed every face, also reversed the proxy triangles. The in-game measurement found outward 2 m collision boxes that still stopped the player, so "physics pass-through" was dropped as a symptom.)*

## Naming convention in Blender for FBX export

Objects in Blender must follow this naming scheme for Object Builder to assign them to LODs on import:

```
{selectionName}_LOD__{resolution}     -> Resolution LOD (note the double underscore)
{selectionName}_LODGeometry           -> Geometry LOD
{selectionName}_LODFireGeometry       -> Fire Geometry LOD
{selectionName}_LODViewGeometry       -> View Geometry LOD
{selectionName}_LODShadowVolume       -> Shadow Volume LOD
{selectionName}_LODMemory             -> Memory LOD
{selectionName}_LODRoadway            -> Roadway LOD
```

Example for a simple box:

```
LOD0_LOD__0.000             -> Resolution LOD 0
LOD0_LOD__1.000             -> Resolution LOD 1
Component01_LODGeometry     -> Geometry LOD component
Component01_LODFireGeometry -> Fire Geometry component
```

FBX import settings in Object Builder:

- Tick the "LODs" checkbox in the import dialog.
- Set Master Scale to **0.01** (Blender exports 100 times too large).
- After import: Structure > Squarize All LODs to clean up the triangulation.
- After import: Structure > Convexity > Component Convex Hull on the Geometry LOD.

## Total LOD count ceiling (added 2026-07-14)

Keep the total number of LODs per model under about 30. Bohemia's LOD wiki page warns that **30 or more LODs in total can crash the binarizer**. This counts all LOD types together (resolution, Geometry, Fire, View, shadow, Memory, Roadway and the rest), not just the resolution LODs. (Source: the Bohemia LOD wiki page, as cited in a 2026 video tutorial on LOD authoring.) The rest of what those tutorials show (copy LOD0, decimate to about 50 %, 25 % and 12 %, set textures and sections before cutting LODs so they carry over) is already covered above and in `blender-headless.md`; this ceiling is the one extra hard limit.

## Collision of a large building with an interior

(SP-453, SP-457, SP-458, added 2026-10-03.)

Measured on one project: a rock shaped building generated from Blender, with a hangar, an attic, a ground floor room and a lift inside (the SecretRock mod's rock helipad, rounds R7.1 to R7.4, 2026-10-01 to 2026-10-03). Its collision is hundreds of convex pieces per model. Every figure below comes from that project; none was measured again on another model, and none can be checked on `P:\`. For scale, the vanilla barn `P:\DZ\structures\industrial\farms\barn_wood1.p3d` stores 564 components in its largest collision LOD (`_shared/models/lods.md`, "Geometry").

### MLOD size grows with the square of the piece count

`[OFFLINE MEASURED]` With 1,150 pieces in Geometry, View and Fire, the rock's MLOD weighed 478 MB; with 827 to 997 pieces of 6 points each and a separate, coarser View Geometry that kept the functional pieces (doors, buttons), 55 to 75 MB. The binarized ODOL does not carry the cost (78.4 MB of MLOD became 2.1 MB of ODOL); the MLOD does, and in a Git repository it needs LFS past GitHub's 100 MB. The separate View did not last: in R7.3 its own set of pieces left 28 % of the skin open to the project's ray test and went past 2,048 components, so the View went back to the Geometry's pieces.

Why it grows that way, from the format rather than from a measurement: an MLOD stores each named selection as one byte per point and one byte per face of its LOD (py3d writes `len(all_points) + len(all_faces)` bytes per selection: `py3d/__init__.py:1968-1974` of the fork in `scripts/tools/py3d`, version 1.10.1), and every `ComponentNN` is a selection. N pieces of k points and f faces each make a LOD of about N·k points and N·f faces, so their selections take about N²·(k + f) bytes in each collision LOD.

Before assembling, clean the source meshes and check the hulls: zero area faces, orphan points, faces wound against their normals and `bmesh.ops.convex_hull` hulls that are not exactly convex are in `dayz-p3d-audit/references/killers-detail.md`, "Source meshes for collision".

### Which room a point belongs to: no membership test on open meshes

`[OFFLINE MEASURED]` Interior surfaces are open meshes (floors and ceilings are other objects). Near their edges, cross sections of the lining, upward rays and the side of the nearest surface all placed points in the wrong room. What worked (R7.1): each patch extruded behind its visible side up to the next visible surface along a ray, minus 3 cm; analytic hard volumes for what moves (platform travel, lift cabin, doors); and floor slabs by convex decomposition of the outline, minus convex holes cut by half planes.

### Collision that follows the visible face (R7.3)

1. `[OFFLINE MEASURED]` Patches from k-means clusters of random samples stand far behind a wall that curves tightly: the hull's chord enters the room, and the cut that removes it leaves the patch far back. On the hangar lining, 38 % of the wall had its collision more than 15 cm behind, and the corners up to 1 m, the probe's limit. Prisms built per region of near flat faces, each extruded from 0.5 cm behind the region's deepest face toward the next visible surface behind it, gave a median of 1 cm and less than 2 % beyond 15 cm. The extrusion aims to stop 3 cm short of that surface; a cap on depth and a minimum thickness of 1.5 cm can leave a smaller margin, so check the clearance that comes out. That reading is of the prisms alone, before the generator's room and hard volume test thins, splits or drops a prism that enters a room; the full model was not part of it.
2. `[OFFLINE MEASURED]` Extrude along the face's geometric normal turned toward its visible side, not along the mean of its corner normals: next to a crease the smoothed normal leans by up to about 45°, and prisms along it stood up to a face's width behind their far corner (median 10.5 cm); along the geometric normal, 1 cm.
3. `[OFFLINE MEASURED]` Grow the regions by position, not by topology. The room meshes, like the vanilla skin, are triangle soups: 1,872 faces gave 1,843 regions with neighbours by shared edge, and 652 with neighbours by corners closer than 2 cm (flatness tolerance 8 cm).
4. `[OFFLINE MEASURED]` A room test that only looks down and up (floor below, ceiling above) counts the rock of a door's lintel and jambs as room: the pieces there were rejected and a 0.84 × 1.55 m gap opened (131 of 368,013 samples of the project's hole probe). A room's ceiling can also be another object, such as the slab of the room above: without it the vertical test missed the room almost everywhere, and pieces entered it by up to 0.40 m. Rule: floor below, ceiling above, and 3 of 4 horizontal rays that hit the visible side of the walls.
5. `[OFFLINE MEASURED]` Random samples miss the seams: four passes of 60,000 samples left 0.15 % of the skin open. Testing every exterior triangle at 7 points finds the triangles with a hole in one pass.

### Binarize: the visual budget

`[OFFLINE MEASURED]` Binarized with its Visual LOD 0 only, textures and materials on: R7.1 in one model, with smooth normals, gave `CAPACITY_FAIL` at 92,430 resolved vertices (py3d's count of `(point, normal, uv)` triples). Split into the rock (49,929) and the interior with smooth normals on its inner face (42,501), both passed. The rock passed above the cliff of 46,133 measured on an HH-60G helicopter import, so that cliff does not carry over to another model (the binarize vertex budget notes in the vehicles pack, item 4). Split normals on a height field face more than triple its resolved vertices: the attic's inner face, 33,046 triangles, counted 56,743 with split normals and 17,392 with smooth ones (a triple counter run in Blender, a lower bound).

### Binarize: a silent limit on the collision LODs

1. `[OFFLINE MEASURED]` With 1,843 convex pieces in Geometry, View and Fire, `binarize.exe` wrote no ODOL and printed no capacity line: the project's three state bench read `OTHER_FAIL`, and no message explained it (claim CLAIM-BINARIZE-COLLISION-LOD-SILENT).
2. `[OFFLINE MEASURED]` It is not the file size: a 247.8 MB MLOD failed and a 264.4 MB one passed. Without its collision LODs, the same model passed.
3. `[OFFLINE MEASURED, variable not isolated]` The boundary over 9 variants, read per collision LOD (a variant without its View LOD failed like the full one):

   | Per collision LOD | Largest that passed | Smallest that failed |
   |---|---|---|
   | Faces | 28,124 | 32,766 |
   | Named selections × points | 31,494,324 | 33,889,401 |
   | Selection bytes | 81,723,788 | 83,726,487 |
   | Pieces | 1,786 | 1,501 |
   | Points | 22,281 | 22,281 |

   The first three separate the passes from the failures equally well (2^25 = 33,554,432 lies between the two products); the piece count and the point count alone do not. A cap at 32,768 faces cannot be the only limit, since 32,766 already failed; one alongside another limit is not ruled out. A variant with few faces and many selections would help decide it; it was not run.
4. `[OFFLINE MEASURED]` A truncated MLOD gives the same `OTHER_FAIL`: one variant was cut off while being written, inside its Geometry LOD. Before reading an `OTHER_FAIL` as this limit, walk the MLOD to the `#EndOfFile#` TAGG of every LOD.
5. Rule (the project's, applied to the models it shipped): before binarizing, measure each collision LOD with a header reader. Points and faces are in each LOD's `P3DM` header, and the named selections and their bytes in its TAGG list, which a reader skips through by each TAGG's size without loading the file (seconds for 350 MB). Where any of the three measures is above the largest value seen to pass (the first column of the table, exact), move pieces to another model with the same transform, created and deleted with the main one. Do not merge or decimate pieces to fit. Those values are one project's conservative bounds, not a PASS threshold: `binarize` still decides for every resulting model.
6. `[IN-GAME VERIFIED, DayZDiag 1.29, 2026-10-03]` The separate model works: a collision only `House` class of 602 pieces, spawned with the rock at its transform. A `geom` ray cast from 30 m out toward the rock stopped on one of its pieces, and the project's battery of 1,188 rays per LOD from outside found 0 holes in Geometry, Fire and View. No Fire or View ray was checked against that model's pieces on their own (claim CLAIM-COLLISION-ONLY-MODEL-INGAME).

### Binarize: `Too many vertices` from the collision LODs (R7.4)

`[OFFLINE MEASURED]` In R7.4 (2026-10-03, `binarize.exe` revision 163709 through the three state bench) the rock read `CAPACITY_FAIL`, a `Too many vertices` line attributed to its MLOD, also with its visual LOD put back as it had passed: its collision had grown. Read from the MLOD (14 LODs, three of them collision LODs) with the project's reader:

| Build | Pieces per collision LOD | Points per collision LOD | Points, all LODs | Points, visual LOD 0 | Verdict |
|---|---|---|---|---|---|
| R7.3, deployed | 1,241 | 16,370 | 93,935 | | PASS |
| A build that passed | 1,240 | 16,325 | 94,091 | 25,230 | PASS |
| The failing build | 1,263 | 16,582 | 96,409 | 26,891 | `CAPACITY_FAIL` |
| The failing build, visual LOD 0 put back | 1,263 | 16,582 | 94,750 | 25,232 | `CAPACITY_FAIL` |
| The failing build without its last 33 exterior pieces | 1,230 | 16,094 | 93,286 | | PASS |

So, for this model, the limit lies between 1,240 and 1,263 pieces per collision LOD, or between 94,091 and 94,750 points over all LODs; these builds cannot tell which. Named selections × points in one collision LOD do not explain it alone: the interior model of the same addon passes with about 1,800 selections of 17,641 points in its one collision LOD. Nor is it the silent limit above, since binarize printed `Too many vertices` for this MLOD. The project caps the rock at 1,230 pieces and moves the rest to its collision only model (item 6 above), and binarize passed 6 of 6 (claim CLAIM-BINARIZE-COLLISION-TOO-MANY-VERTICES).

Rule: on a `CAPACITY_FAIL`, compare every LOD of the last build that passed with the failing one before blaming the change just made. Here the visual LOD had changed in the same round and took the blame for one round; put back as it passed, the model still failed.
