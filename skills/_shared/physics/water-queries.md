# Water queries over water objects

What the engine's water queries return over objects that carry their own water: the vanilla river and stream pieces, the streambed kit, and a roadway water face of your own. For a map maker deciding how to build rivers, and for a scripter who tests whether a point is in water.

The query declarations are on `P:\`. Every number below was measured in game on a server, on Chernarus and on a test map, and can't be checked on `P:\`. Not tested: a boat, a player drinking, and how the water looks.

## The queries

| Query | Declared at |
|---|---|
| `GetWaterDepth(vector posWS)` | `P:\scripts\3_game\global\game.c:1198` |
| `GetWaterSurfaceHeightNoFakeWave(vector posWS)`: "the nearest water or object surface under a point, ignoring land", without the fake wave; `GetWaterSurfaceHeightWithFakeWave` adds it | `game.c:1199`, `:1200`, `:1202` |
| `SurfaceIsSea(float x, float z)` | `game.c:1196` |
| `SurfaceIsPond(float x, float z)` | `game.c:1197` |
| `SurfaceRoadY3D(float x, float y, float z, RoadSurfaceDetection rsd)` | `game.c:1178` |
| `GetObjectsAtPosition(vector pos, float radius, out array<Object> objects, out array<CargoBase> proxyCargos)` | `game.c:923` |

The vanilla pieces are the models `river_24_*` and `stream_14_*` under `P:\DZ\water\streams\` (for example `P:\DZ\water\streams\river_24_24.p3d`) and the kit under `P:\DZ\water\streambed\`.

Query at gameplay heights, the water surface plus or minus 1 m, never from high above: on a pitched piece the level you read moves with the height of the query (see "How the level is read over a roadway water face").

## Load the objects before you query on an empty server

With no player connected, `GetWaterDepth`, `GetWaterSurfaceHeightNoFakeWave` and `SurfaceRoadY3D` over the streambed kit and over the `stream_14` pieces of Chernarus return sea level and a depth of 0. Pond pieces placed in the map's own layer read correctly.

Call `GetGame().GetObjectsAtPosition(Vector(x, 0, z), 30, objs, proxies)` in the same frame first, and keep both arrays alive until the water queries have run. With that, 371 of 417 points on the kit's axes read water.

- On the kit, 61 % of the points read wet where the terrain lies less than 0.05 m below the kit's roadway water face, and all of them where it lies 0.15 m or more below.
- The water you see on the kit is a separate 14 by 24 m calm water proxy sheet, which no server query sees.

## Vanilla rivers and streams are pitched

To learn how vanilla cuts its water into pieces, walk the map on the server with `GetObjectsAtPosition` (Chernarus fits in 103 by 103 cells of 150 m) and log, for every water piece, its pose, its `GetDirectionUp` and the water queries along its axes. Chernarus gives:

| Pieces | Count | Pitched | Pitch: median, 95th percentile, maximum |
|---|---|---|---|
| Ponds and lakes | 670 | 3 | not measured |
| `river_24_*` | 660 | 562 | 1.5, 4.7, 8.4 degrees |
| `stream_14_*` | 460 | 388 | 2.2, 9.0, 39.3 degrees |

- The water surface the engine returns follows the slope of the piece: the median ratio of water slope to piece slope is 0.95 on the rivers (172 pieces) and 0.94 on the streams (188 pieces). Streambed kit pieces mix in other surfaces, so they give no clean ratio.
- At the centres of the pieces above 50 m altitude, `SurfaceIsPond` is true for only 75 of 375 river pieces and 30 of 384 stream pieces, while the water depth is positive for 365 of 375 and 312 of 384.

So in a vanilla bed, `SurfaceIsPond` returning false is the normal case and does not rule water out. Test the depth instead. Never require `SurfaceIsPond` to be true in a map check: it pushes the map maker to replace pitched beds with flat planes, and stepped flat planes leave visible steps and dry strips on sloped stretches.

## How the level is read over a roadway water face

Over a roadway water face, `GetWaterSurfaceHeightNoFakeWave` and `GetWaterDepth` follow this rule, which matches 1,940 of 1,941 logged points within 2 mm over a channel built from vanilla pieces:

1. The candidate faces are those whose bounding box in world x and z contains the query point.
2. The query point is taken into the object's model space with its own height, through the object's whole transform (rotation and uniform scale).
3. A candidate counts only when that model space point falls inside the face in model x and z.
4. The level is the model y of the face's first vertex, held level in model space, and brought back to the world as (local x, y of the first vertex, local z). Over several objects the highest level wins; in one logged case of two overlapping levels the engine returned the lower one.

What follows for a map maker:

- On a pitched piece, a query a height `dy` above or below the surface reads the level shifted by `dy` times the sine of the pitch along the piece: an error of about `dy` times the pitch squared (pitch in radians). Queried from 50 m above the ground, that is 6.0 cm at 2 degrees and 1.5 cm at 1 degree, whatever the scale. Near the edges of a face the water is lost and shows false holes. That is why a probe queries at gameplay heights.
- On the vanilla straights (`river_24_*`, `stream_14_*`) the skirt on the negative z side reads its bottom (its first vertex is at -0.07 m) and the skirt on the positive z side reads the flat level (its first vertex is at +0.07 m). Their Roadway LOD (resolution 3e15) has the same vertices as the first visual LOD, and every roadway normal is (0, 1, 0).
- At gameplay heights the flat part matches the mesh within 1 cm in 84 to 97 % of the samples, with no holes; the differences are on the skirts (plus or minus 0.07 times the scale) and at some joints (up to 13 cm).
- Straights laid edge to edge around a bend leave gaps, where the sea shows through when the bed is below sea level. When using only straights, overlap them by one pair of skirts (6 m times the scale).
