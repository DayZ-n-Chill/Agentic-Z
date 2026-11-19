# Imported mesh and winding checks

Checks for a vehicle body that comes from an OBJ, a glTF or a game rip: mesh and UV health, telling a mirror from a rotation, winding, which way the nose points, cabin alignment, and what numbers alone cannot see.

The measured cases come from mod vehicles (imported cars and helicopters), not vanilla. The vanilla car to compare against is `P:\DZ\vehicles\wheeled\civiliansedan\civiliansedan.p3d`; it is binarized, which py3d cannot read, so numbers quoted from it were read with an outside converter and are not checked on `P:\`. The full record of offline visual checks and their winding traps is in `visual-gates-and-winding.md`.

## Mesh and UV health first

For any imported model, ripped or not, audit mesh and UVs before anything else; a broken mesh produces false findings later (a "double wall" that was a mirrored UV on one wall, a "convexity" problem that was open edges).

1. Audit the mesh (open edges, non-manifold edges, duplicate vertices and faces, winding per piece) and the UVs (islands, overlap, density, mirrored islands).
2. Clean with an adaptive weld, stepping from 0.5 down to 0.01 mm, and stop if non-manifold edges grow or UVs change. A blind 0.5 mm weld fuses pieces that only touch and creates non-manifold edges.
3. Unwrap by sections as `_shared/models/uv-mapping.md` describes.
4. Require overlap near zero for baking, even density, an atlas a person can read, and a checker render with smooth shading; flat shading on a grid reads falsely as low poly or blurry.

No overlap means an exact separating-axis test of zero (`SAT=0`). A Monte Carlo estimate has a measured floor above zero, so its "0%" proves nothing. Route vehicle UV repair to the clean UV atlas method (`_shared/models/tools-uv-atlas.md`); `PartUV` is not the vehicle default. Run the exact overlap test after every anti-fold round, keep going while it is above zero, and block any mesh that never reaches zero.

## LODs made by a decimate modifier

With no artist, collapse plus planar dissolve per object is the normal LOD path, and the modifier leaves loose vertices that no triangle uses. Every count-based check stays green while the data ships broken: a per-vertex loop driven by `mesh.loops` never reaches a loose vertex, so its slot keeps the initial value, and `(0,0,0)` becomes a zero-length normal. The source had 0 loose vertices in 224,700; after decimation LOD 1 had 786 and LOD 2 had 4,024, plus 16 normals as short as `3e-6` that a "greater than 0" test passed.

- Delete loose vertices after every decimate: `bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")`. It removes only geometry no triangle uses. Skip the bmesh round trip when there is nothing to delete.
- Require every emitted normal to be unit length, with the cut at 0.5, not 0: a unit normal survives float32 within about `1e-7` of 1.0, so anything shorter is a cancelled sum. Replace a bad one from its neighbours, never from `poly.normal`, which points the wrong way after a mirroring import.
- Require every index to fall inside its own piece's vertex range; no count check sees an out-of-range index, and it fails at assembly.

A drift number that mixes classes is not a measurement. Split surviving vertices into intact (the same incident triangles as LOD 0, drift must be about 0), recomputed (topology changed, drift is fine) and degenerate (counted, never averaged). Mixed, a 99th percentile of 90.00 degrees hid a real defect and hid that untouched geometry was clean within 0.26 degrees. An exact round angle is a fingerprint: 90.00 is `acos(0)`, a null vector on one side. Match survivors on a grid of about `1e-4` m, not `1e-6`; positions are float32, and the finer grid drops about a third of untouched vertices at random.

Position finds candidates, not identity: a seam can put different normal or UV corners at one coordinate. Pair intact data by a carried source vertex or corner id and primitive id. If that id was lost and a bucket is not unique, report "inconclusive", not pass or fail. Run the source against itself through the same matcher and require a residual near zero before trusting any comparison.

## Mirror or rotation

Before calling an imported model mirrored and applying a determinant -1 import, check all three axes. A point has no handedness, but a labelled tetrahedron does: take four labelled, non-coplanar matching points A, B, C, D and compute `det[B-A, C-A, D-A]` on each side.

- Same sign: a proper transform (determinant +1), a rotation. The model is fine, and a determinant -1 import would add a mirror.
- Opposite sign: a real reflection. Apply the determinant -1 import with normals transformed as pseudovectors.
- Near zero: the points are coplanar; pick others.

Counting flipped axes is the axis-aligned shortcut of the same test, and easy to misread:

| Axes flipped | What it is |
|---|---|
| One | Reflection |
| Two, the third intact | 180 degree rotation about the third axis |
| All three | Point reflection, a 180 degree rotation plus a mirror; split it before acting |

On an imported helicopter one session measured only X, saw it flipped and called the model mirrored. Measuring Z too showed all 38 points with X and Z flipped and Y intact: a 180 degree yaw, the pipeline's normal convention, and the sister airframe already flying in game had the same nose at minus Z. The tetrahedron test gave +6.076679 in the file against +6.076514 at runtime, ratio +0.999973, the same sign, which settled it without a game session. A determinant -1 import would have added a real mirror and broken winding already confirmed in game.

A proper file to runtime transform does not rule out a mirror baked in earlier, in the source mesh or the exporter, or a mirrored UV island, which shows as backwards lettering on correct geometry. Those need their own checks.

Prefer relative measurements. A comparison inside one file through one reader survives whatever axis convention the reader uses; a file against runtime comparison does not. "The 10 crew proxies are rotated 180 degrees from the 15 part proxies" holds even if you never settle which handedness py3d reports.

## Texture or mesh

"The textures look wrong" on an imported vehicle has several unrelated causes, and auditing the texture pipeline is the slowest way to tell them apart. Check in this order:

1. Audit the UVs, not the textures: exact overlap, island count and density. Overlap above zero, islands of 2 to 4 faces, or very uneven density put the problem before any `.rvmat`.
2. Ask where the mesh came from. A decimated rip cannot give game-ready UVs; the fix is retopology (bake the high poly onto a clean low poly), not a different unwrap or texture route.
3. Render the same material on a control that is known good. If it looks right, the pipeline is cleared and the defect is in this model.
4. Only then audit `.rvmat` stages, `_co`, `_nohq` and `_smdi` paths, PAA conversion and `hiddenSelections` (`_shared/textures/`; the vehicle shader choice is in `_shared/textures/vehicle-materials.md`).

If two pipeline audits come back clean, the texture is not applied wrong; change direction instead of running a third. On one helicopter two audits cleared the whole chain (UVs identical across Blender, MLOD and ODOL, PAA unchanged, `uvSource=tex`, no `hiddenSelections`); on one car the cause was the rip's decimated topology. Steps 1 or 2 would have branched away from the texture pipeline in both.

On a ripped vehicle, first count faces per source material and texture pair. Game rips colour bodies through the host game's paint system, so those materials (in GTA `vehicle_generic_smallspecmap*`, "primary") have no diffuse or a zero-byte file. An importer that needs some texture per face falls back to whatever is there, and if that is the livery or decal sheet, signs, numbers and camouflage are stamped across the body. One texture carrying a large share of the model, especially a decal atlas, is the signature; a 0-byte or missing DDS proves the fallback. On an imported helicopter a 22.4 MB livery sheet carried 23,716 of 35,385 faces (67 percent), 8,695 of them pure fallback, with `vehicle_generic_smallspecmap3.dds` at 0 bytes. Those faces want a flat colour `_co`; their UVs were never meant to address a texture, so no UV work is involved. The diagnosis is measured; the flat colour fix is not yet confirmed in game.

## Winding of an imported vehicle

Keep the raw glTF winding as it is for every piece. For a rip with a measured proper transform, rip to DayZ is `(-Fx, Fy+Y0, -Fz)`, determinant +1, which keeps the authored visible side. Store MLOD normals as the smooth cross product of the final winding.

- Never orient winding to a normal oracle (an authored `__N` channel, which was never authored and holds normals of the pre-mirror winding, so orienting to it inverted every piece) or to "outward from the centre".
- Repair only the faces that are inconsistent in the source, about 0.5 percent, by flipping each connected component to its majority, after removing duplicates. Never flip by minority area.
- `glass*int_a` panes are real cabin-side glass; do not delete them as z-fighting.
- A Blender back-face culling render is only a hint: it shows the side the cross product points to, while the engine draws the other side. The game is the judge.

Winding depends on the source. A rip or vehicle with a measured determinant +1 transform keeps its winding as above. A generic import with no profile follows "The Blender to DayZ map" in `_shared/models/generated-model-rules.md`: the determinant -1 map, face order kept, normals negated, no face reversed. An in-game comparison decides a correction; a lineage check decides preservation. Do not apply the generic model pipeline's Smart UV, decimation or flip defaults to a vehicle.

## The nose points to minus Z

Vanilla vehicles point their nose to minus Z. Read on the binarized sedan itself, not a converted copy: `light_1_1` at Z -2.387, `dmgzone_front` at -2.355, the front axle at -1.655, the exhaust at plus Z.

What a player perceives as forward follows the seated player's yaw, which comes from the crew proxy's orientation: the third-person vehicle camera sets `m_fIgnoreParentYaw` to `0.0` (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercameravehicles.c:189`; the camera chain at `:39` to `:49` and `:93` to `:105`; defaults such as `GetTransportCameraDistance` at `P:\scripts\3_game\vehicles\transport.c:652` to `:663`). Headlights and hubs play no part. The sign of traction is native: `GetBrake`, `EngineGetRPM` and `GetGear` are engine calls (`P:\scripts\3_game\vehicles\car.c:200` to `:248`); minus Z is inferred from the working sedan.

A shell turned 180 degrees against the simulation shows both at once: first gear seems to drive backwards, and the wheel proxies sit mirrored off their hubs. Compare `dmgZone_front` and the hubs (simulation) with the headlights and wheel proxies (visual) against nose minus Z.

The visual side of an imported car is not one block; measure every body proxy separately before any bulk rotation. Decide the cabin's orientation with anatomical pairs (seat, steering wheel, column rake, driver side) against untouched simulation anchors (hubs, damage zones, engine memory points), never with a mixed bounding box or the cluster's own memory points, which share its error. Then rotate exactly that cluster, in every file and LOD the host references: shell, body proxies, crew proxies, and the `pos_*` and `drivewheel*` points. On one car the fix rotated the whole cabin in the main files but missed the 12 proxy models used by visual LODs 1 and 2, so mid-distance LODs still drew the old orientation. Afterwards the anchors sat exactly on the hubs, the seat on the left, the wheel 0.34 m ahead of it with a rake of (0, 0.516, 0.857) parallel to vanilla, and driving in game showed no reversed pose.

If the `drivewheel_axis` pair is near vertical (Y dominant), the wheel sweeps left and right like a wiper instead of turning in its plane. The axis must be roughly perpendicular to the rim plane, mostly Z with some Y.

## Steering wheel against hands

The seat animation belongs to the vanilla car, so hands land on its wheel plane. Measure the rim centre against the crew anchor and the rim's tilt against the control before moving anything. On one car the centre was already within 1 to 1.6 cm, but the rim tilted 15.8 degrees against the sedan's 31.0. At radius 0.159 m that puts the rim's top and bottom 4.2 cm off the sedan's plane, and a hand at half radius 2.1 cm off, matching the report "top hand 2 cm behind, bottom hand 2 cm in front". Rotate the wheel piece about its own rim centre to the sedan's tilt and rewrite `drivewheel` and `drivewheel_axis` parallel to the new rim normal; that car's axis was 38 degrees off its own rim while the sedan's is exactly parallel, and a skewed axis also makes the wheel wobble. Do not recline the crew proxy when the position already matches. Fit the rim by principal components of the outer radius; on a debinarized model, recover selections whose point membership was lost through their faces.

## Thresholds on a measured axis

A rig threshold on a measured axis needs its source declared for every member of a pair. The door rig requires `dir_y > 0.999`, and a rip's tilt put one hinge just under it. One car declared a projected vertical axis for one door only; the other kept its raw fitted axis at `|dir_y| = 0.998575`, 3.059 degrees off, and the build refused much later. Project each side keeping its own XZ midpoint; the two sides of a rip are not symmetric, and mirroring would have moved the hinge 3.7 cm (driver x +0.849278, co-driver x -0.811827). Do not lower the threshold for one car: it exists so doors do not open tilted, and lowering it lowers it for every car.

## What numbers cannot see

Checks that measure only numbers cannot see a proxy's colour or orientation; only an eye on an assembled render can. One imported car reached the PBO with every name, face, hash, seat, door and slot check green, while 64 percent of its faces were in one material and the whole interior in another: the import had no material map and sent 37 named parts (badges, mirrors, exhaust, jambs, skirts, underbody, arms) into the paint material. Its four wheel proxies used an identity matrix where vanilla writes two mirrored matrices, one per side, and it used the 176 mm vanilla sedan wheel instead of its own. The user saw all four defects within minutes of the first assembled look.

- Render the assembled car with its materials; loose grey parts show neither a wrong colour nor a reversed rim.
- Tie a human verdict to the SHA-256 of what was reviewed, and make the check fail when the verdict is stale, so a rebuild cannot inherit an approval.
- Check handedness with brand text. DayZ is left-handed and most viewers are right-handed, so coordinates passed unchanged mirror the model, which looks normal until a badge reads backwards.

This does not replace testing in game; it finds the visible defects sooner. A white or untextured car on a server is covered in `binarize-dropped-textures.md`.
