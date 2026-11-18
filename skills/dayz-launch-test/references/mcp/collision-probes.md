# Collision probes: rays, controls, walk-into and stand-on tests

How to read an object's collision with `scene_raycast`, `player_move` and `player_teleport`: the ray battery and its controls, what the reply fields mean, how to pose a test fixture, and which results prove nothing.

The verbs are dayz-mcp's; their behaviour and every measurement here are third-party, taken in game sessions on DayZDiag 1.29.163709 unless a line says otherwise, and not yet checked on `P:\`. Vanilla facts cite the vanilla file. `MCPBridge.c:NNN` and `MCPClientBridge.c:NNN` are lines of dayz-mcp's own source at the time of the measurement.

## What `scene_raycast` casts

- The default `method="rvproxy"` intersects the LODs, in the mode given by `intersect`: `geom`, `view` or `fire`. These are the vanilla intersection types `ObjIntersectGeom`, `ObjIntersectView` and `ObjIntersectFire` (`P:\scripts\3_game\global\dayzphysics.c:67-69`).
- `method="bullet"` with `radius=0` casts `DayZPhysics.RayCastBullet` (vanilla: `P:\scripts\3_game\global\dayzphysics.c:211`) in the server's physics world, restricted to the layers BUILDING, DOOR, VEHICLE, ROADWAY, TERRAIN, ITEM_SMALL, ITEM_LARGE and FENCE (`MCPBridge.c:2983-3004`; added 2026-10-02). Count a hit only when `object_type` is the target and the position is where its face should be: a vertical ray through a box without collision returns `hit=1` on the terrain. A miss alone does not prove the object has no physics shape (its layer can be outside the mask), and a hit does not mean the player collides (the `WoodenCrate` below).
- With `intersect="view"` the ray uses the cursor's mode, but the bridge casts a 0.05 m sphere when the radius is 0 (`MCPBridge.c:2496`, `:2528-2531`), where the vanilla ray has none.

## Reading the reply

- **`entry=0` is terrain, or a ray that started inside an object** (measured 2026-09-07 with `intersect=fire` and `geom`). A vertical ray against the ground returns `hit=1`, `object_type=""`, `surface_type=cp_grass|cp_concrete2`, `entry=0`, `exit=0`; against an object from outside it returns `entry=1`. Qualified 2026-10-03: a ray that starts inside an object also reads `entry=0` (the inside rays of run 606a5dbb read `entry 0, exit 1` at distance 0 on the controls). Tell terrain by its empty `object_type`, not by `entry=0` alone. A mod that filters `!hit.entry` discards natural ground (a placement hologram that never snaps to the ground was traced to this).
- **The `normal` of an `rvproxy` reply is not a face normal.** The bridge copies the engine's `RaycastRVResult.dir` (`MCPBridge.c:2958`), which vanilla documents for a line-object collision as the "direction and size of the intersection" (`P:\scripts\3_game\global\dayzphysics.c:104`), as the Enforce Script pack (`skills/_shared/enscript/depth/`) ("Surface normals") found on house walls. Measured magnitudes on the ground were 0.16 to 0.42. In two runs (the first and run cf2d6bb3) it lay along the ray in all 190 `rvproxy` hits on an object, a box yawed about 10 degrees included ((-1.963, 0, 0) and (-1.966, 0, 0)), and its length is the ray's path through the object: (-2.1, 0, 0) across a 2 m box is its width plus the 0.05 m sphere at each side. So it says nothing about the face: never read it as a normal and never use it as a threshold (`dot >= 0.9` is never reached). Corrected 2026-10-02: earlier versions said to use it for direction only, and read the pose from it lying along the axis; with the default method it always does.
- **A face normal comes from `method="bullet"`** (`MCPBridge.c:2998`): a unit vector in all 40 of its hits, up to 0.31 degrees off the axis on `HouseNoDestruct` statics and on the axis on items.
- **`component`** is filled on `rvproxy` hits (`geom`, `view` or `fire`); the bridge leaves it 0 on `bullet` hits (`MCPBridge.c:2983-3004`).

## The ray battery and its controls

Added 2026-10-03; it is the battery of the `dayz-p3d-audit` skill's "Absolute winding check" rule 6, fired on DayZDiag 1.29.163709 on 2026-10-02 (dayz-mcp run 606a5dbb). An earlier version of this playbook asked for rays "from at least two angles", which cannot tell the causes below apart.

Nine rays per mode (`geom`, `view`, `fire`):

- One vertical ray down the object's axis. On a solid box whose collision spans its own axis, like the measured kit box, a LOD recentred by a missing `autocenter=0` (`dayz-p3d-audit`, killer 3) still sits on that ray, so a miss there is not the recentring. On an object with gaps or several separate parts the shifted collision can leave the axis: check that the ray crosses the collider both where it is modelled and where the recentring would put it.
- Four horizontal rays through the middle, one from each side, and two more heights on one side.
- Two rays from inside the object outward: a sound object answers `entry 0, exit 1` at distance 0.

Fire the same battery, in the same run, at two controls:

- an object from the same PBO and load path, which separates the model from the build and the loading;
- a vanilla object of the same physics layer (`physLayer`). `WoodenCrate` sets none (`P:\DZ\gear\camping\config.cpp:10157`) and takes `item_small` from `Inventory_Base` (`P:\DZ\data\config.cpp:3169`). For a static, use the `Land_Container_1Aoh` control below.

In that run the kit box under test took 0 of 27 rays, while the same PBO's second kit and `WoodenCrate` took 21 of 21 each (the battery without the two extra heights). The battery locates a miss; it does not name the cause. When the suspect is the winding, only a pair that changes the winding alone decides: the kit's paired run in rule 6 did; the rule 12 pair, which also turned the Visual LOD and the normals, supports the cause without deciding it.

## A vanilla control before blaming the mesh (measured 2026-09-07)

If `scene_raycast` does not hit a mod static, repeat the same ray (in `view`, `fire` and `geom`, from outside and from inside) against a vanilla static spawned next to it: `world_spawn(type="Land_Container_1Aoh")`. It has flat walls, is a `HouseNoDestruct` (`P:\DZ\structures\industrial\config.cpp:2258`) for which `IsBuilding()` is true, and also serves as a wall for holograms.

- Control hit and mod miss in all modes and from both sides: likely reversed convex collision components (inverted winding in the Geometry, View Geometry and Fire Geometry LODs: the binarized model keeps them, the engine does not see them).
- Control hit and mod hit only from inside: likely reversed faces in the visual mesh only.

With the source winding restored the same ray gave the front face at +0.079 m and a wall 0.42 m thick. The correction rule lives in `dayz-p3d-audit` (0% agreement is a discrepancy, not a direction). Qualified 2026-10-03: the two readings above name the likely cause, not a measured one; only a pair that changes the winding alone decides it, as "The ray battery and its controls" says.

## Picking an item up proves nothing about its collision

Added 2026-10-03; vanilla source read on 1.29 and rechecked on `P:\`, bridge source read, the pickup seen in the same run.

- Vanilla targeting casts `RaycastRVProxy` from the camera over `c_RayDistance` 5 m (`P:\scripts\4_world\classes\useractionscomponent\actiontargets.c:241-255`, `:840`) with the default type `ObjIntersectView` (`P:\scripts\3_game\global\dayzphysics.c:88`).
- At a camera pitch of -45 degrees or lower it also takes the objects of a cone, `c_ConeAngle` 30 degrees and `c_MaxTargetDistance` 3 m (`P:\scripts\4_world\classes\useractionscomponent\actiontargets.c:324-325`, `:841-843`), and scores them by their distance to that ray with `DistSqrPoint2Line`, with no hit on them needed (`P:\scripts\4_world\classes\useractionscomponent\actiontargets.c:528-529`).
- The take action's target condition checks only the distance to the object's position: `ActionTakeItemToHands` uses `CCTObject` (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiontakeitemtohands.c:13`, `P:\scripts\4_world\classes\useractionscomponent\targetconditionscomponents\cctobject.c:1-24`). Its other conditions (`IsTakeable`, not being placed or deleted, attachment state, room in the hands, and since 1.30 a `DigitalCodeLock` the player cannot detach; `P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiontakeitemtohands.c:31-46`) do not look at collision either.
- `action_use` builds its world target from the nearest object of the class, with `componentIndex -1` and the object's position as the cursor hit, and casts no ray (`MCPClientBridge.c:3769`, `:3783`, `:3861`).

In that run `action_use(ActionTakeItemToHands)` put the kit box in the player's hands while all 27 rays of its battery missed it. Read collision from `scene_raycast` against a same-layer control. The cone path is read in the source, not measured: no MCP verb sets the camera pitch.

## Does the player collide: the walk-into probe

Added 2026-10-02. The run teleported the player 4 m from the object's centre and called `player_move(to=<4 m past the centre, on the far side>, speed="walk", hold_s=10)`, then read the end position with `query_player_state` (server).

- Blocked means `arrived:false` and the player stopped just before the face after the full hold (about 0.36 m before it on that run's 2 m boxes). `released_by:"hold"` only says the hold expired, and `arrived:false` anywhere else is INCONCLUSIVE.
- Free means `arrived:true` (7.5 m in about 5 s). Walk the same distance and bearing on open ground as the free reference.
- Every walk of that run went north nearly straight ahead (`applied_angle_deg` 0, and 0.04 on one walk), so it did not exercise a steering angle or its sign.
- A walk-through alone does not prove missing collision geometry: a vanilla `WoodenCrate` (`item_small`, low) took every ray and did not stop the player, while a `HescoBox` (`physLayer="item_large"`, `P:\DZ\gear\camping\config.cpp:11336`) stopped it. That run did not separate the crate's layer from its height.

## Standing on top: move the player before reading its height

Added 2026-10-02, measured in a later run on 2 m boxes. This is a second reading of the object's physics body, on its top instead of a side face.

An idle player is not a probe. After `player_teleport(pos=[x, <top + 0.07>, z], skip_clearance_check=true)` the player kept the teleport height (y 340.6000) and did not fall, on a box top and above open ground alike: the server read it twice over 3 to 4 s (`query_player_state`), and above open ground the client's physics position (the `start_pos` that `player_move` reports) still read it 15 s after the teleport (the worn-items run in `actions-ui-and-inventory.md` saw the same after a teleport to y=160). Every `query_player_state` of these probes read godmode on, the dayz-mcp default; the run did not separate the bridge, godmode and the engine as the cause.

A short move applies the fall. The run teleported the player above the centre of each top, called `player_move(angle_deg=0, speed="walk", hold_s=0.5)`, then `query_player_state`:

- Above open ground the player dropped to the ground (y 340.6000 to 338.459).
- On the boxes (three `Inventory_Base` items at least 4 m from their neighbours: two wound outward, one as source model and one binarized, and one wound inward) the server's y matched the top to within 0.0001 m (spawn y + 2.000 m, where `scene_raycast(method="bullet")` hit it), and its x and z lay 0.70 to 0.75 m from the centre, inside the 2 m top.

Read the server's position after the move. With x and z still inside the top's footprint, y at the top's height means the player stands on it and y at the ground means it fell through; an endpoint off the footprint, or any other height, is INCONCLUSIVE. Start above the centre of an isolated top (no other support at that height within the walk's reach, or the player can end on it), and run the same teleport and move above open ground as the falling reference. Keep the move short: 0.5 s took the player 0.70 to 0.75 m, with the edge 1 m away. A top whose nearest edge is closer than that can be walked off in 0.5 s, and the endpoint check then reads INCONCLUSIVE.

## Axis-aligned fixtures: try `rotation=64`, then check the pose

Added 2026-10-02, same run as the walk-into probe.

- `rotation=0` leaves the bridge's `RF_DEFAULT` (512, "use default placement setuped on object in config", `P:\scripts\3_game\ce\centraleconomy.c:66`), which yawed an `Inventory_Base` probe about 10 degrees: a side-face reading moved 0.22 m across 1.2 m of the face.
- `rotation=64` spawned the same box with its faces on the world axes (equal readings at both offsets), on flat concrete. Vanilla gives 64 two names, `RF_IGNORE` ("object will spawn as model was created", `P:\scripts\3_game\ce\centraleconomy.c:57`) and `RF_RANDOMROT` (`P:\scripts\3_game\ce\centraleconomy.c:63`). The result agrees with the first comment and does not settle how the engine reads the value.
- Before trusting face coordinates, check the pose. Two parallel rays at one height on a vertical face catch a yaw (unequal readings) but not a tilt, so also read `scene_raycast(method="bullet")` normals on two faces that are not parallel, such as a side and the top (a tilt about one face's normal leaves that normal unchanged), and check that each lies along its axis, allowing for the ground: the statics read up to 0.31 degrees off the axis, the terrain about as much, the items on it.
- Read the fixture again a few seconds later. The rotation may change an item's configured resting side; slopes and settling were not measured.

### An item can come out with its sides swapped, and none of these checks shows it

Measured 2026-10-02 on DayZDiag 1.29.163709 (dayz-mcp run cf2d6bb3). One source model held two 2 m boxes, A (x -3 to -1) in `Component01` and B (x 1 to 3) in `Component02`, and a twin had B in no component. Each model was spawned, binarized and as source, with `flags=8389668` and `rotation=64`, as `HouseNoDestruct` and as `Inventory_Base` (`item_large`).

- On the four statics the west box was A, as modelled: it answered as component 0 (`Component01`; `Component02` reads 1), and on the twins it was the only box that took rays.
- On the four items the boxes had swapped sides, as a turn of 180 degrees about Y leaves them: the west box answered as component 1, and on the twins every hit was component 0 on the east box while the west box took no ray.
- The boxes are symmetric in z, so these rays cannot tell that half-turn from a mirror in x. Parallel rays read equal on the items too, and the normals pointed the same way as on the statics, since the swap keeps every face on the axes. A fixture symmetric about its origin, like the single box above, cannot show it, and `object_inspect` returns memory points in model space (`GetMemoryPointPos`, `MCPBridge.c:2240`; vanilla `P:\scripts\3_game\entities\object.c:452`), not the pose.

So give the fixture sides that a ray can tell apart and check which answers where: one component per side, read from the `component` of `rvproxy` hits, or a collider on one side only. Put the parts off-centre in z as well to tell a half-turn from a mirror, and probe along z too: a quarter-turn moves parts that lie along x onto the z axis. `telemetry_read(mode="object_at")` returns the object's `GetOrientation()` (`MCPBridge.c:3137`); that run did not read it. Not measured: whether the swap is fixed or random (all four items swapped; 64 is also `RF_RANDOMROT`), other `rotation` and `flags` values, base classes and layers, and the cause.
