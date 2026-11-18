# Collision probes

How to read an object's collision through dayz-mcp with `scene_raycast`, `player_move` and `player_teleport`: the set of rays and its controls, what the reply fields mean, how to pose a test object, and which results prove nothing.

The verbs belong to the third-party dayz-mcp tool. Their behaviour and every number here were measured in game on DayZ 1.29 with that tool and are not checked on `P:\`; `MCPBridge.c` and `MCPClientBridge.c` lines are dayz-mcp's own source. Vanilla facts cite the vanilla file.

## What `scene_raycast` casts

| Call | What it does |
|---|---|
| default `method="rvproxy"` | Intersects the LODs in the mode given by `intersect`: `geom`, `view` or `fire`. These are the vanilla `ObjIntersectGeom`, `ObjIntersectView` and `ObjIntersectFire` (`P:\scripts\3_game\global\dayzphysics.c:67` to `:69`). With `intersect="view"` and radius 0 the bridge casts a 0.05 m sphere where the vanilla ray has none (`MCPBridge.c:2496`, `:2528` to `:2531`). |
| `method="bullet"`, `radius=0` | Casts `DayZPhysics.RayCastBullet` (`dayzphysics.c:211`) in the server's physics world, limited to the layers BUILDING, DOOR, VEHICLE, ROADWAY, TERRAIN, ITEM_SMALL, ITEM_LARGE and FENCE (`MCPBridge.c:2983` to `:3004`). |

Count a `bullet` hit only when `object_type` is the target and the position is where its face should be: a vertical ray through a box with no collision returns `hit=1` on the terrain. A miss alone does not prove the object has no physics shape, because its layer can be outside the mask, and a hit does not mean the player collides (see `WoodenCrate` below).

## Reading the reply

- `entry=0` means terrain, or a ray that started inside an object. A vertical ray to the ground returns `hit=1`, `object_type=""`, `surface_type=cp_grass` or `cp_concrete2`, `entry=0`, `exit=0`; a ray that hits an object from outside returns `entry=1`; a ray that starts inside reads `entry 0, exit 1` at distance 0. Tell terrain by its empty `object_type`, not by `entry=0` alone. A mod that filters out `!hit.entry` throws away natural ground; a placement hologram that never snapped to the ground was traced to this.
- The `normal` of an `rvproxy` reply is not a face normal. The bridge copies the engine's `RaycastRVResult.dir` (`MCPBridge.c:2958`), which vanilla documents as the "direction and size of the intersection" (`dayzphysics.c:104`); the Enforce Script pack found the same on house walls (`_shared/enscript/depth/`, "Surface normals"). It lies along the ray in every object hit, including a box turned about 10 degrees, and its length is the ray's path through the object: (-2.1, 0, 0) across a 2 m box is its width plus the 0.05 m sphere at each side. On the ground it measured 0.16 to 0.42 long. Never read it as a normal and never threshold it (`dot >= 0.9` is never reached).
- A face normal comes from `method="bullet"` (`MCPBridge.c:2998`): a unit vector in all 40 hits measured, up to 0.31 degrees off the axis on `HouseNoDestruct` statics and on the axis on items.
- `component` is filled on `rvproxy` hits; the bridge leaves it 0 on `bullet` hits (`MCPBridge.c:2983` to `:3004`).

## The set of rays and its controls

This is the set the `dayz-p3d-audit` absolute winding check fires (`dayz-p3d-audit/references/winding-absolute-check.md`). Rays "from at least two angles" cannot tell the causes below apart, so fire nine rays in each mode (`geom`, `view`, `fire`):

- One vertical ray down the object's axis. On a solid box whose collision spans its own axis, a LOD recentred by a missing `autocenter=0` (`dayz-p3d-audit/references/p3d-killers.md`) still sits on that ray, so a miss there is not the recentring. On an object with gaps or separate parts the shifted collision can leave the axis: check that the ray crosses the collider both where it is modelled and where recentring would put it.
- Four horizontal rays through the middle, one from each side, and two more heights on one side.
- Two rays from inside the object outward. A sound object answers `entry 0, exit 1` at distance 0.

Fire the same rays, in the same run, at two controls:

- an object from the same PBO and load path, which separates the model from the build and the loading;
- a vanilla object of the same physics layer. `WoodenCrate` sets no `physLayer` (`P:\DZ\gear\camping\config.cpp:10157`) and takes `item_small` from `Inventory_Base` (`P:\DZ\data\config.cpp:3169`). For a static, use `Land_Container_1Aoh` below.

In one measured run a test box took 0 of 27 rays while the second box from the same PBO and `WoodenCrate` took 21 of 21 each. The rays locate a miss; they do not name the cause. When the suspect is the winding, only a pair of builds that changes the winding alone decides it. A pair that also changes the Visual LOD and the normals supports the cause without deciding it.

## A vanilla control before you blame the mesh

If `scene_raycast` misses a mod static, repeat the same ray (`view`, `fire` and `geom`, from outside and from inside) at a vanilla static spawned next to it: `world_spawn(type="Land_Container_1Aoh")`. It has flat walls and is a `HouseNoDestruct` (`P:\DZ\structures\industrial\config.cpp:2258`), so `IsBuilding()` is true, and it also serves as a wall for holograms.

| Control | Mod object | Likely cause |
|---|---|---|
| Hit | Miss in every mode, from both sides | Reversed convex collision components: inverted winding in the Geometry, View Geometry and Fire Geometry LODs. The binarized model keeps them and the engine does not see them. |
| Hit | Hit only from inside | Reversed faces in the visual mesh only. |

These name the likely cause, not a measured one. With the source winding restored, the same ray found the front face at +0.079 m and a wall 0.42 m thick. The correction rule (0 % agreement is a disagreement, not a direction) lives in `dayz-p3d-audit`.

## Picking an item up proves nothing about its collision

- Vanilla targeting casts `RaycastRVProxy` from the camera over `c_RayDistance` 5 m (`P:\scripts\4_world\classes\useractionscomponent\actiontargets.c:241` to `:255`, `:840`), with the default type `ObjIntersectView` (`dayzphysics.c:88`).
- At a camera pitch of -45 degrees or lower it also takes the objects in a cone, `c_ConeAngle` 30 degrees and `c_MaxTargetDistance` 3 m (`actiontargets.c:324` and `:325`, `:841` to `:843`), and scores them by their distance to the ray with `DistSqrPoint2Line`, with no hit needed (`actiontargets.c:528` and `:529`). This path was read in the source, not measured: no verb sets the camera pitch.
- `ActionTakeItemToHands` checks only the distance to the object's position, through `CCTObject` (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiontakeitemtohands.c:13`; `P:\scripts\4_world\classes\useractionscomponent\targetconditionscomponents\cctobject.c:1` to `:24`). Its other conditions (`IsTakeable`, not placed or deleted, attachment state, room in the hands, and from 1.30 a `DigitalCodeLock` the player cannot detach; `actiontakeitemtohands.c:31` to `:46`) do not look at collision either.
- dayz-mcp's `action_use` builds its target from the nearest object of the class, with `componentIndex -1` and the object's position as the cursor hit, and casts no ray (`MCPClientBridge.c:3769`, `:3783`, `:3861`).

`action_use(ActionTakeItemToHands)` put a test box in the player's hands while all 27 of its rays missed. Read collision from `scene_raycast` against a same-layer control.

## Does the player collide: the walk-into test

Teleport the player 4 m from the object's centre, call `player_move(to=<4 m past the centre, on the far side>, speed="walk", hold_s=10)`, then read the end position with `query_player_state` (server).

- Blocked: `arrived:false` and the player stopped just before the face after the full hold (about 0.36 m before it on 2 m boxes). `released_by:"hold"` only says the hold ran out, and `arrived:false` anywhere else is `INCONCLUSIVE`.
- Free: `arrived:true` (7.5 m in about 5 s). Walk the same distance and bearing on open ground as the free reference.
- The measured walks all went nearly straight ahead (`applied_angle_deg` 0, and 0.04 once), so steering angle and its sign were not tested.
- A walk-through alone does not prove missing collision geometry. A vanilla `WoodenCrate` (`item_small`, low) took every ray and did not stop the player, while a `HescoBox` (`physLayer="item_large"`, `P:\DZ\gear\camping\config.cpp:11336`) stopped it. Layer and height were not separated.

## Standing on top: move the player before you read its height

An idle player is not a probe. After `player_teleport(pos=[x, <top + 0.07>, z], skip_clearance_check=true)` the player kept the teleport height and did not fall, above a box and above open ground alike: the server read the same height twice over 3 to 4 s, and above open ground the client's physics position (the `start_pos` that `player_move` reports) still read it 15 s later. Godmode was on, the dayz-mcp default, in every reading; whether the bridge, godmode or the engine holds the player up was not separated.

A short move applies the fall. Teleport above the centre of the top, call `player_move(angle_deg=0, speed="walk", hold_s=0.5)`, then `query_player_state`:

- Above open ground the player dropped to the ground (about 2.1 m).
- On three 2 m `Inventory_Base` boxes, at least 4 m from their neighbours, two wound outward (one source model, one binarized) and one wound inward, the server's y matched the top to within 0.0001 m (spawn y plus 2.000 m, where `scene_raycast(method="bullet")` hit it), and x and z lay 0.70 to 0.75 m from the centre, inside the top.

Read the server's position after the move. With x and z inside the top's footprint, y at the top means the player stands on it and y at the ground means it fell through; an end point off the footprint, or any other height, is `INCONCLUSIVE`. Start above the centre of an isolated top, with no other support at that height within reach, and run the same teleport and move above open ground as the falling reference. Keep the move short: 0.5 s moved the player 0.70 to 0.75 m, so a top whose nearest edge is closer than that can be walked off.

## Posing a test object square to the world

- `rotation=0` leaves the bridge's `RF_DEFAULT` (512, "use default placement setuped on object in config", `P:\scripts\3_game\ce\centraleconomy.c:66`), which turned an `Inventory_Base` box about 10 degrees: a side face reading moved 0.22 m across 1.2 m of the face.
- `rotation=64` spawned the same box with its faces on the world axes, on flat concrete. Vanilla gives 64 two names, `RF_IGNORE` ("object will spawn as model was created", `centraleconomy.c:57`) and `RF_RANDOMROT` (`:63`). The result agrees with the first comment and does not settle how the engine reads the value.
- Check the pose before you trust face coordinates. Two parallel rays at one height on a vertical face catch a turn (unequal readings) but not a tilt, so also read `scene_raycast(method="bullet")` normals on two faces that are not parallel, such as a side and the top, and check that each lies along its axis. Allow for the ground: statics read up to 0.31 degrees off the axis, the terrain about as much, items the same as the ground under them.
- Read the object again a few seconds later. Rotation may change an item's configured resting side; slopes and settling were not measured.

## An item can come out with its sides swapped

One source model held two 2 m boxes, A (x -3 to -1) in `Component01` and B (x 1 to 3) in `Component02`; a twin model had B in no component. Each was spawned binarized and as source, with `flags=8389668` and `rotation=64`, as `HouseNoDestruct` and as `Inventory_Base` (`item_large`).

- On the four statics the west box was A, as modelled: it answered as component 0 (`Component02` reads 1), and on the twins it was the only box that took rays.
- On the four items the boxes had swapped sides, as a half turn about Y leaves them: the west box answered as component 1, and on the twins every hit was component 0 on the east box while the west box took no ray.
- The boxes are symmetric in z, so these rays cannot tell a half turn from a mirror in x. Parallel rays read equal on the items too, and the normals pointed the same way as on the statics, since the swap keeps every face on the axes. A test object symmetric about its origin cannot show the swap, and `object_inspect` returns memory points in model space (`GetMemoryPointPos`, `MCPBridge.c:2240`; vanilla `P:\scripts\3_game\entities\object.c:452`), not the pose.

So give the test object sides a ray can tell apart and check which one answers where: one component per side, read from the `component` of `rvproxy` hits, or a collider on one side only. Put the parts off centre in z as well to tell a half turn from a mirror, and probe along z too, because a quarter turn moves parts that lie along x onto the z axis. `telemetry_read(mode="object_at")` returns the object's `GetOrientation()` (`MCPBridge.c:3137`); it was not read in that run. Not measured: whether the swap is fixed or random (all four items swapped, and 64 is also `RF_RANDOMROT`), other `rotation` and `flags` values, other base classes and layers, and the cause.
