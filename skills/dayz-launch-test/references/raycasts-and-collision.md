# Raycasts and collision in game

How to read an object's collision in the running game: the two vanilla raycasts and what their results mean, the set of rays and its controls, why picking an item up proves nothing, and the walk-into and stand-on tests for the player.

Vanilla facts cite the file on `P:\`. Every count and distance below was measured in game on DayZ 1.29 with test boxes and is not checked on `P:\`.

## The two raycasts

| Call | What it casts | Source |
|---|---|---|
| `DayZPhysics.RaycastRVProxy` | Intersects LODs in the mode given by the input's `type`: `ObjIntersectFire` (0), `ObjIntersectView` (1) or `ObjIntersectGeom` (2). The default is `ObjIntersectView`. | `P:\scripts\3_game\global\dayzphysics.c:66` to `:68`; the default at `:88` |
| `DayZPhysics.RayCastBullet` | Casts in the physics world against a `PhxInteractionLayers` mask and returns a hit normal. | `dayzphysics.c:211` |

Count a bullet hit only when the hit object is the target and the position is where its face should be: a vertical ray through a box with no collision hits the terrain below. A miss alone does not prove the object has no physics shape, because its layer can be outside the mask, and a hit does not mean the player collides (`WoodenCrate` below).

## Reading the results

- The `dir` of an `RaycastRVResult` is not a face normal. Vanilla documents it as "direction outside (in world coord) or (in case of line-object collision) direction and size of the intersection" (`dayzphysics.c:104`). Measured, it lies along the ray in every object hit, including a box turned about 10 degrees, and its length is the ray's path through the object: (-2.1, 0, 0) across a 2 m box. On the ground it measured 0.16 to 0.42 long. Never threshold it as a normal (`dot >= 0.9` is never reached). The Enforce Script pack found the same on house walls (`_shared/enscript/depth/`, "Surface normals").
- A face normal comes from `RayCastBullet`'s `hitNormal`: a unit vector in all 40 hits measured, up to 0.31 degrees off the axis on `HouseNoDestruct` statics and on the axis on items.
- Terrain and starting inside: a vertical ray to the ground hits with no object and a surface type such as `cp_grass` or `cp_concrete2`, with `entry` and `exit` both false; a ray that hits an object from outside has `entry` true; a ray that starts inside reads `entry` false, `exit` true at distance 0. Tell terrain by the missing object, not by `entry` alone. A mod that filters out hits with `!entry` throws away natural ground; a placement hologram that never snapped to the ground was traced to this.
- `component` names the hit component on `RaycastRVProxy` hits, which is how you find a seat or door component for an action.

## The set of rays and its controls

Rays "from at least two angles" cannot tell the causes apart, so fire nine rays in each mode (`geom`, `view`, `fire`). This is the set the `/dayz-p3d-audit` absolute winding check describes (`skills/dayz-p3d-audit/references/winding-absolute-check.md`).

- One vertical ray down the object's axis. A collision LOD recentred by a missing `autocenter=0` (`skills/dayz-p3d-audit/references/p3d-killers.md`) still sits on that ray on a solid box, so a miss there is not the recentring. On an object with gaps or separate parts, check that the ray crosses the collider both where it is modelled and where recentring would put it.
- Four horizontal rays through the middle, one from each side, and two more heights on one side.
- Two rays from inside the object outward. A sound object answers `entry` false, `exit` true at distance 0.

Fire the same rays, in the same run, at two controls:

- an object from the same PBO and load path, which separates the model from the build and the loading;
- a vanilla object of the same physics layer. `WoodenCrate` sets no `physLayer` (`P:\DZ\gear\camping\config.cpp:10167`), nor does its parent `Container_Base` (`P:\DZ\data\config.cpp:3319`), so it takes `item_small` from `Inventory_Base` (`P:\DZ\data\config.cpp:3169`). For a static, use `Land_Container_1Aoh`, a `HouseNoDestruct` with flat walls (`P:\DZ\structures\industrial\config.cpp:2258`).

In one run a test box took 0 of 27 rays while a second box from the same PBO and `WoodenCrate` took 21 of 21 each. The rays locate a miss; they do not name the cause. When the suspect is the winding, only a pair of builds that changes the winding alone decides it.

| Vanilla control | Mod object | Likely cause |
|---|---|---|
| Hit | Miss in every mode, from both sides | Inverted winding in the Geometry, View Geometry and Fire Geometry components. The binarized model keeps them and the engine does not see them. |
| Hit | Hit only from inside | Reversed faces in the visual mesh only. |

These name the likely cause, not a measured one. With the source winding restored, the same ray found the front face at +0.079 m and a wall 0.42 m thick.

## Picking an item up proves nothing about its collision

- Action targeting casts `RaycastRVProxy` from the camera over `c_RayDistance` (`P:\scripts\4_world\classes\useractionscomponent\actiontargets.c:246` and `:255`) with the default `ObjIntersectView`.
- With the camera pitched down it also takes the objects in a cone, `c_ConeAngle` and `c_MaxTargetDistance` (`actiontargets.c:325`), and scores them by their distance to the ray with `DistSqrPoint2Line`, no hit needed (`:531`, `:543`). Read in source, not measured.
- `ActionTakeItemToHands` checks only the distance to the object's position, through `CCTObject` (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiontakeitemtohands.c:13`; `P:\scripts\4_world\classes\useractionscomponent\targetconditionscomponents\cctobject.c:1` to `:24`). Its other conditions (`actiontakeitemtohands.c:31` to `:47`) do not look at collision either.

A test box went into the player's hands while all 27 of its rays missed. Read collision from rays against a same-layer control.

## Does the player collide: the walk-into test

Put the player 4 m from the object's centre, walk them for 10 s towards a point 4 m past the centre on the far side, then read the end position on the server.

- Blocked: the player did not arrive and stopped just before the face (about 0.36 m before it on 2 m boxes). Not arriving anywhere else is inconclusive.
- Free: the player arrived (7.5 m in about 5 s). Walk the same distance and bearing on open ground as the free reference.
- A walk-through alone does not prove missing collision geometry. A vanilla `WoodenCrate` took every ray and did not stop the player, while a `HescoBox` (`physLayer="item_large"`, `P:\DZ\gear\camping\config.cpp:11346`) stopped it. Layer and height were not separated.

## Standing on top: move the player before you read its height

An idle player is not a probe. Teleported to 0.07 m above a box top, the player kept that height and did not fall, above a box and above open ground alike, for at least 15 s. God mode was on in every reading, so whether it holds the player up was not separated.

A short move applies the fall: teleport above the centre of the top, walk forward for 0.5 s, then read the server position.

- Above open ground the player dropped to the ground (about 2.1 m).
- On three isolated 2 m `Inventory_Base` boxes the server's y matched the top to within 0.0001 m, and x and z lay 0.70 to 0.75 m from the centre, inside the top.

With x and z inside the top's footprint, y at the top means the player stands on it and y at the ground means it fell through; anything else is inconclusive. Use an isolated top, run the same teleport and move above open ground as the falling reference, and keep the move short: 0.5 s moved the player 0.70 to 0.75 m, so a smaller top can be walked off.
