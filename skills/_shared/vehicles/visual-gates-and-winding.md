# Winding checks for imported cars

Which offline checks catch winding and shading faults on an imported car and which ones only seem to, the one orientation rule for a ripped car, why a clean `validate()` or a Blender culling render proves nothing about what the game draws, and how to pick the winding of a face a script adds or moves.

Measured offline and in game on cars and a helicopter built from rips and imports; the vanilla reference is the sedan, `P:\DZ\vehicles\wheeled\civiliansedan\civiliansedan.p3d`, read from a converted copy because it is binarized (**model knowledge**). The scripts named in the source builds are not shipped; each section states the method so it can be rebuilt. Glass bands, gap closure, material transfer and structural patches are in `rip-glass-and-gap-closure.md`.

## The orientation rule

Keep the raw glTF winding as it is for every piece. The rip to DayZ transform `(-Fx, Fy + Y0, -Fz)` has a determinant of +1 and keeps the visible side from end to end. Write stored MLOD normals as the smooth `+cross` of the final winding. Never orient winding to a normal channel or outward from the car's centre.

- The source glb is consistent between winding and normals for 261191 of 261227 faces (99.99%), no mesh below 99%. A normal channel captured in Blender after `bm.normal_update()` is not the authored normal: bmesh drops custom split normals, so it is the smoothed `+cross` of the winding before mirroring. Orienting to it flips every piece.
- The game draws the anti-cross side. On the sedan only 1.6% of the roof zone (`dmgzone_roof`) is cross-outward, and 96.2% of its stored normals agree with `+cross`. With raw winding a ripped body piece read 8.8% cross-outward, close to an approved shell at 14.3%.
- Repair only pieces inconsistent in the source (about 0.33% of one car's faces, mostly lights and glass) by majority flood fill per connected component. Never flip by minority area, which inverted a rear glass. A repair can flip 24 to 39% of one glass piece while the car-wide total stays near 0.5%; a warning listing pieces with more than 1% flipped is the expected list, not a failure.
- Check a rebuild face by face against a build with the repairs switched off, from the same data: coverage near 100% and opposite faces exactly equal to the repair count. A whole-car orientation mistake reads 90 to 97% opposite; compare the whole car, since repairs gather in lights and glass and a shell-only diff reads 1 to 3%.
- Every later rebuild (after decimation, for example) must also write `+cross`; a `-cross` rebuild against a `+cross` shell gives two-tone paint.
- Re-running the import reproduced the intermediate data byte for byte; a changed hash on an unchanged rip means the tools changed.
- Inner glass panes are the cabin side of a two-sided pair (92 to 100% cross-outward, facing the cabin). Do not delete them as z-fighting.

The interior is no exception. A ripped cabin oriented by the wrong channel showed see-through in first person. Compare the share of faces pointing at the `crewdriver` anchor with the converted vanilla `prox_int` (about 35%): the raw winding read 30.3%. Rebuilt with raw winding and smooth geometric normals, one sided, as a dedicated interior proxy like `prox_int` (LODs 0.0 and 1100, frame `((-1,0,0),(0,0,1),(0,1,0))`, model space, no bone selection), it drew correctly in game. Fix orientation in the import step, not piece by piece.

## Per-piece uniformity first

The most basic winding fault is a face wound against its own neighbours. Per selection, weld vertices by rounded position and check that every edge shared by two faces is walked in opposite directions; two faces walking it the same way are a mixed pair, and any visible piece with one fails. It is Blender's "Make Normals Consistent" used as a check. One deployed car had 18.2% of its glass area mixed (the rear window), 192 paint faces, 86 light faces, 12 trim and 8 tail faces. Run it before any ray test. The fix order: remove duplicates, make each piece consistent by majority flood fill per component (ignoring edges with more than two faces), then take orientation from the raw winding.

## The see-through ray check

Casting culled rays from many outside directions (a Fibonacci sphere) and flagging faces seen only from the minority side finds faces inverted against the outside without trusting normals, and runs headless. Its raw output is about 94% false: concave pieces such as suspension, trim, interior and underbody are rightly seen from inside (9152 of 9736 one-sided faces on one car; 584 were body). To make it useful:

1. Keep body selections (`color`, `glass`) and drop `suspension`, `trim` and `interior`, mapping each face to its selection on the visual LOD the check indexes.
2. Keep the full ray settings; cutting them undercounted 3.6 times.
3. Drop deliberate double-sided pairs: an exact coincident vertex triple, or centroids within 6 mm with opposite normals.
4. Compare left with right. On symmetric geometry, one-sided body faces on one side and none on its mirror mean that side is inverted: a left tail lamp read 310 of 922 against 0 of 922 on the right. Flip it to match the good side.

It is a hint; the game decides.

## Duplicate faces

Speckle of grey, black or blue triangles all over the body was the source assembly emitting every body face twice: same three vertices, same normal, different UV channel, present before any decimation, so winding and decimation fixes all missed it. One chunk was 71% duplicated, another 50%. Count coincident faces by point set and winding, and by identical rounded positions: a clean car scores about 0, a duplicated one 10 to 70%. Keep one face per position set and normal direction, preferring the copy whose UVs sit in 0 to 1; keep opposite-direction pairs, which are deliberate; never drop a `proxy:` face. One car lost 20320 faces and the speckle was gone in game. Add the pass to the importer.

## Bright triangles on paint

Bright or dark triangles scattered over paint, catching sky light, are shading seams: a winding flip that also negated those faces' stored normals left them antiparallel to their neighbours. Winding, duplicate and material checks all pass. Weld the paint by position and count distinct stored normal directions at each shared point: a smooth surface has one, a seam two opposite ones. Fix it by writing stored normals as the smooth `+cross` of the final winding (the orientation rule above). Never recompute normals outward from the car's centre: a car body is not convex, so that matches only about 70% and inverts the rest. Keep any consistency fix to the area of the complaint: a headlight is a layered lens and reflector, and forcing it consistent can invert a real inner layer.

## Other faults found on imported cars

- A steering wheel is rim, spokes and hub, not a disc, so plane fits of its axis disagree by 12 to 48 degrees on the same mesh. Use the all-points principal axis through the wheel centre as a first guess, then confirm the spin in game or against full-lock photos.
- A one-sided shell is solid from outside yet the driver sees sky and ground through roof and floor. Double only those faces: a reversed twin (`[0,2,1]`) with a negated normal appended to `lod.facenormals` (a pool indexed by `vertex.normal_index`, so reusing the index would not flip it), added to the same selections. Never flip the whole car. Check from the driver's seat.
- An empty fluid on a debug spawn puts its gauge needle at red. The capacities come from `CarScript` (`fuelCapacity`, `brakeFluidCapacity`, `oilCapacity`, `coolantCapacity`, `P:\DZ\vehicles\wheeled\config.cpp:243` to `:246`; fluid types in `ETransportFluid`, `P:\scripts\3_game\vehicles\transport.c:52`), and the fill call is in `fluids-and-engine.md`.
- A first-person view of the interior is drawn from the View Pilot LOD by `DayZPlayerCamera1stPersonVehicle` (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercameravehicles.c:4`); see `rip-wheels-and-doors.md`.

## What `validate()` cannot prove

A clean `py3d.validate()` (py3d 1.10.1 in `scripts/tools/py3d/`) shows that winding, stored normals and LODs agree with each other, not that the game draws the side you meant.

- `_check_winding_absolute`, on visual, Geometry, View and Fire Geometry LODs, compares each face's `cross(e1,e2)` with its stored normal (`ERR_WINDING_VS_NORMALS`, `WARN_WINDING_NORMAL_MISMATCH`) and checks shared edges run opposite ways (`WARN_WINDING_EDGE_INCOHERENT`). A LOD whose faces and normals were turned together agrees and passes.
- `_check_winding_vs_visual` compares each collision LOD with the coarsest visual LOD by the share of faces wound outward from the centre (`ERR_WINDING_INVERTED`). It assumes convex shapes and cannot see a global inversion; when the visual LOD is the inverted one, it flags the healthy collision LODs.

So a model inverted as a whole, as a Blender Z-up to Y-up turn of both winding and normals leaves it, gives no winding finding. The findings expected on a vehicle (`rip-structural-lods.md`) are false positives, and their absence proves nothing either. `save(verify=True)` and `python -m py3d diff` compare counts, selection names and membership, properties, UV sets and mass, never point positions (except memory points): two models with one point at `(0,0,0)` and `(99,99,99)` verify clean and diff to 0.

Checks that do discriminate, cheapest first:

1. Compare a face's vertex order with the converted vanilla equivalent. The converter inverts winding, so a face matching the converted order is the inverted one.
2. `cross(e1,e2) · declared_normal` per face, both in the same space, which removes left and right-handed confusion: 1274 of 1274 faces over 15 vanilla LODs, against an outward share that swings from 0 to 31.8% and means nothing.
3. Edge consistency, which finds the faces in a partial inversion.
4. The game: texture visible only from inside means inverted winding.

Ratios do not predict the render either. A helicopter passed the edge check (at most 0.0025% mixed) and an ODOL census matching the sedan (98 to 100% against 96%), and drew inverted, because winding and normals were both flipped. The cheap decider is an A and B in game: reverse every visual face (never proxy triangles, whose winding encodes their frame), binarize, and let the user look. Census both ODOLs first; if they are equal, the test is void. Binarize keeps the source winding (99.1% against 0.95% on the two variants); it normalises nothing. After fixing a flip in an assembler, recalibrate its winding checks and leave out dots near 0, which merged symmetric normals produce (about 17% of one shell). How to read each py3d winding finding: `skills/dayz-p3d-audit/references/winding-absolute-check.md` and `skills/dayz-p3d-audit/references/winding-diagnostics.md`.

## A Blender culling render cannot judge winding

Two sign changes can cancel. The usual display mapping `(x,y,z)` to `(x,z,y)` has determinant -1 and mirrors apparent winding, while `(x,y,z)` to `(x,-z,y)` has +1. Blender draws the `+cross` side and the game the anti-cross side, so a preview can agree by accident. Use it for shape and placement only. In Blender's Workbench engine enable `scene.display.shading.show_backface_culling`; `material.use_backface_culling` drives EEVEE and does nothing there, and identical culling on and off renders are a void test.

## Winding for a face you add or move

Match the sign of the neighbouring faces known to draw, in the same file and LOD, so both cross every format step alike. A redesigned dash panel on a test quad did not draw: its Newell normal dotted with the line of sight gave +0.951 while all 64 disc faces beside it, which drew, gave negative dots (mean -0.952). Flipping it fixed it. No absolute rule was needed, and none would hold, since the same test inverts across binarize.

- Calibrate on geometry that draws. Reversing vertex order and checking the sign against the neighbours is a two-line assertion.
- Compare only like shapes. Needles are solids and face both ways (12 of 173 read discordant); only the flat coplanar panel and discs belong in the check. Prove such faces were there before with a set comparison of centroids, not a count.
- A translation cannot change winding; assert it anyway.

That panel came out mirrored because of the script that moved it. Corners were sorted by `(-y, -x)` expecting rows to tie on Y, but the two top corners differed by 0.1 mm, so the X tiebreak never ran and the quad mirrored, reversing its winding. Positions and UVs still form a valid rectangle and the texture is not mirrored, so the only sign is a face that vanishes. Quantise sort keys meant to group rows (`round(y, 3)`), or assign corners by quadrant around the centroid, and add the winding sign to the checks of any script that moves vertices.
