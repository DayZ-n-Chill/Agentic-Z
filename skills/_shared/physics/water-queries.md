# Water queries over water objects

What the engine's water queries return over objects that carry their own water: the vanilla river and stream pieces, the streambed kit, and a roadway water face of your own. For a map maker deciding how to build rivers, and for a scripter who tests "is this point in water".

The query declarations were checked on `P:\` (DayZ 1.30). Every number below was measured in game by the author of the source notes, on a DayZDiag server with probe missions of a custom map project (the Baltic map), between 2026-10-03 and 2026-10-14. They are native queries read on the server; a boat, a player drinking and how the water looks were not tested. None of the measurements can be checked on `P:\`.

## The queries

| Query | Declared at |
|---|---|
| `GetWaterDepth(vector posWS)` | `P:\scripts\3_game\global\game.c:1198` |
| `GetWaterSurfaceHeightNoFakeWave(vector posWS)` | `P:\scripts\3_game\global\game.c:1200` |
| `SurfaceIsPond(float x, float z)` | `P:\scripts\3_game\global\game.c:1197` |
| `SurfaceRoadY3D(float x, float y, float z, RoadSurfaceDetection rsd)` | `P:\scripts\3_game\global\game.c:1178` |
| `GetObjectsAtPosition(vector pos, float radius, out array<Object> objects, out array<CargoBase> proxyCargos)` | `P:\scripts\3_game\global\game.c:923` |

The source notes give the 1.29 lines of the first two as 1183 and 1185; that build is not on `P:\`.

The vanilla pieces are the models `river_24_*` and `stream_14_*` under `P:\DZ\water\streams\` (for example `P:\DZ\water\streams\river_24_24.p3d`) and the kit under `P:\DZ\water\streambed\`.

## Measure the vanilla map first

Before deciding how a map's water or terrain objects are cut into pieces, measure how the vanilla map does it with a server probe. The survey behind these notes walked Chernarus in 103 by 103 cells of 150 m with `GetObjectsAtPosition` and logged, for every water piece, its pose, its `GetDirectionUp` and water queries along its axes.

Query at gameplay heights, the water surface plus or minus 1 m, never from high above: on a pitched piece the level you read moves with the height of the query (last section).

## A server with no player reads no object water until the objects are loaded

With no player connected, `GetWaterDepth`, `GetWaterSurfaceHeightNoFakeWave` and `SurfaceRoadY3D` at points over the streambed kit and over the `stream_14` pieces of Chernarus returned sea level and a depth of 0, while the pond pieces of the project's own map layer read correctly.

Calling `GetGame().GetObjectsAtPosition(Vector(x, 0, z), 30, objs, proxies)` in the same frame, and keeping both arrays alive until the water queries had run, made 371 of 417 points on the kit's axes read water.

- On the kit, 61 % of the points read wet where the terrain lay less than 0.05 m below the kit's roadway water face, and 100 % where it lay 0.15 m or more below.
- The water you see on the kit is a separate 14 by 24 m calm water proxy sheet, which no server query sees.

## Vanilla rivers and streams are pitched, and `SurfaceIsPond` is false at most of their centers

A server read of all of vanilla Chernarus, 2026-10-03:

| Pieces | Count | Pitched | Pitch: median, 95th percentile, maximum |
|---|---|---|---|
| Ponds and lakes | 670 | 3 | not measured |
| `river_24_*` | 660 | 562 | 1.5, 4.7, 8.4 degrees |
| `stream_14_*` | 460 | 388 | 2.2, 9.0, 39.3 degrees |

- The water surface the engine returns follows the slope of the piece: the median ratio of water slope to piece slope is 0.95 on the rivers (172 pieces) and 0.94 on the streams (188 pieces).
- At the centers of the pieces above 50 m altitude, `SurfaceIsPond` is true for only 75 of 375 river pieces and 30 of 384 stream pieces, while the water depth is positive for 365 of 375 and 312 of 384.

So in a vanilla bed, `SurfaceIsPond` returning false is the normal case and does not rule water out. Test the depth instead. An acceptance test that demands `SurfaceIsPond` true pushes a map maker to replace pitched beds with flat planes; on the Baltic map those stepped planes left visible steps and dry strips on the sloped stretches. The survey's streambed rows mix other surfaces and cannot be used for the slope ratio.

## How the level is read over a roadway water face

Measured on the DayZDiag server in one run (8392533a) of a vanilla channel pilot on the Baltic map: the rule below reproduces 1,940 of 1,941 logged rows within 2 mm, and a second query height agrees with a mean residual of 1 cm or less. Over a roadway water face, `GetWaterSurfaceHeightNoFakeWave` and `GetWaterDepth` read like this:

1. The candidate faces are those whose bounding box in world x and z contains the query point.
2. The query point is taken into the object's model space with its own height, through the object's whole transform (rotation and uniform scale).
3. A candidate counts only when that model space point falls inside the face in model x and z.
4. The level is the model y of the face's first vertex, held level in model space, and brought back to the world as (local x, y of the first vertex, local z). Over several objects the highest level wins.

What follows:

- On a pitched piece, a query a height `dy` above or below the surface reads the level shifted by `dy` times the sine of the pitch along the piece: an error of about `dy` times the pitch squared (pitch in radians), plus 6.0 cm at 2 degrees and plus 1.5 cm at 1 degree when queried from 50 m above the ground, whatever the scale. Near the edges of a face the water is lost (false holes). That is why a probe has to query at gameplay heights.
- On the vanilla straights (`river_24_*`, `stream_14_*`) the skirt on the negative z side reads its bottom (its first vertex is at -0.07 m) and the skirt on the positive z side reads the flat level (its first vertex, v3, is at +0.07 m). Their Roadway LOD (resolution 3e15) has the same vertices as the first visual LOD, and every roadway normal is (0, 1, 0).
- At gameplay heights the flat part matches the mesh within 1 cm in 84 to 97 % of the samples, with no holes; the differences are on the skirts (plus or minus 0.07 times the scale) and at some joints (up to 13 cm).
- Straights laid edge to edge around a bend leave gaps, where the sea shows through when the bed is below sea level. When using only straights, overlap them by one pair of skirts (6 m times the scale).

Ruled out with the run's data: a roadway that differs from the visual LOD; selection by the exact projected polygon (fails 137 cases with yawed, overlapping pieces); selection in model space only (fails 21 rows); nearness to the face boundary; and the nearest face in model units (241 disagreements). One row is unexplained: where two levels overlapped, the engine returned the lower one.
