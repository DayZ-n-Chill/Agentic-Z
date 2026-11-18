# Interaction layers and raycasts

Covers the physics interaction layers, the three ways to switch a collision off and what each one touches, the two families of ray and overlap tests, which one each vanilla system uses, and why the action cursor ignores a physics body.

Probing one LOD of one model is in `collision-lods.md`.

## Interaction layers

`PhxInteractionLayers` is a bit mask enum (`P:\scripts\3_game\global\dayzphysics.c:1`). The engine assigns the layers; script only sees the names. The ones a mod meets most, with where vanilla script uses each:

| Layer | Seen in vanilla | Line |
|---|---|---|
| `BUILDING` | In the mask of the roof check (table below) | `P:\scripts\3_game\global\dayzphysics.c:6` |
| `CHARACTER` | What vanilla tests an object's layer against to decide whether it blocks a player | `P:\scripts\3_game\global\dayzphysics.c:7` |
| `VEHICLE` | In the same mask as `BUILDING` | `P:\scripts\3_game\global\dayzphysics.c:8` |
| `DYNAMICITEM`, `DYNAMICITEM_NOCHAR` | By their names, a dropped or thrown item with and without collision against characters; the assignment is inside the engine | `P:\scripts\3_game\global\dayzphysics.c:9`, `:10` |
| `ROADWAY` | In the action cursor's ground test, with `TERRAIN` and `WATERLAYER` | `P:\scripts\3_game\global\dayzphysics.c:11` |
| `FIREGEOM` | "Redefinition of 'RAGDOLL_NO_CHARACTER'", says the comment above it | `P:\scripts\3_game\global\dayzphysics.c:17` |
| `ITEM_SMALL`, `ITEM_LARGE` | The config `physLayer` values; see `mass-and-weight.md` | `P:\scripts\3_game\global\dayzphysics.c:37`, `:38` |

`TEMP` is the last named bit (`P:\scripts\3_game\global\dayzphysics.c:42`); there are no layers reserved for mods. The full list, in bit order: NOCOLLISION, DEFAULT, BUILDING, CHARACTER, VEHICLE, DYNAMICITEM, DYNAMICITEM_NOCHAR, ROADWAY, VEHICLE_NOTERRAIN, CHARACTER_NO_GRAVITY, RAGDOLL_NO_CHARACTER (also named FIREGEOM), DOOR, RAGDOLL, WATERLAYER, TERRAIN, GHOST, WORLDBOUNDS, FENCE, AI, AI_NO_COLLISION, AI_COMPLEX, TINYCAPSULE, TRIGGER, TRIGGER_NOTERRAIN, ITEM_SMALL, ITEM_LARGE, CAMERA, TEMP (`P:\scripts\3_game\global\dayzphysics.c:1` to `:43`).

## Three ways to stop a collision

| Call | What it changes | Source |
|---|---|---|
| `dSetInteractionLayer(worldEntity, mask1, mask2, enable)` | The layer to layer matrix of the whole world. The first parameter only finds the world. | `P:\scripts\1_core\proto\enphysics.c:11`; the doc of `PhysicsWorld.SetInteractionLayer`, `P:\scripts\1_core\physics\physicsworld.c:14` to `:21` |
| `dBodySetInteractionLayer(ent, mask)` | Which layers one body belongs to; `dBodySetGeomInteractionLayer(ent, index, mask)` does it for one geometry of the body | `P:\scripts\1_core\proto\enphysics.c:59`, `:61` |
| `dBodyCollisionBlock(ent1, ent2)` | Collision between one pair of entities; `dBodyRemoveBlock` lifts it | `P:\scripts\1_core\proto\enphysics.c:116`, `:117` |

Switching off `CHARACTER` against `DYNAMICITEM` with `dSetInteractionLayer` changes it for every dynamic item on the server. To let one player pass through one object, use the pair block.

To check at run time whether two layers interact, use the query vanilla uses to decide whether an object can block a vehicle door (`dGetInteractionLayer`, `P:\scripts\3_game\vehicles\transport.c:787` to `:788`):

```c
int layer = dBodyGetInteractionLayer(obj);
bool blocksPlayer = dGetInteractionLayer(this, PhxInteractionLayers.CHARACTER, layer);
```

## Two families of tests

They look at different things. Choosing the wrong one is a common cause of "my raycast hits nothing".

| Family | Looks at | Filter | Source |
|---|---|---|---|
| `DayZPhysics.RaycastRV` and `RaycastRVProxy` | The model LODs: Fire Geometry, View Geometry or Geometry | `ObjIntersectFire` (0), `ObjIntersectView` (1), `ObjIntersectGeom` (2), `ObjIntersectIFire` (3), `ObjIntersectNone` (4) | `P:\scripts\3_game\global\dayzphysics.c:199`, `:208`; the values at `:66` to `:71` |
| `DayZPhysics.RayCastBullet`, `SphereCastBullet` and the `OverlapBullet` calls | The physics world: bodies and their layers | A `PhxInteractionLayers` mask | `P:\scripts\3_game\global\dayzphysics.c:211`, `:213`, `:216` to `:228` |

- `RaycastRVParams` defaults to `ObjIntersectView` (`P:\scripts\3_game\global\dayzphysics.c:88`). The `ObjIntersect` values are engine constants; the numbers to trust are the ones in that comment (`:66` to `:71`).
- A `RaycastRVProxy` hit comes back as `RaycastRVResult` (`P:\scripts\3_game\global\dayzphysics.c:98` to `:113`): `obj`, which is the proxy object when `hierLevel` is above 0, and `parent`, its top parent; `pos` and `dir`; `component`, the component index in the LOD that was hit; `surface`; and `entry` and `exit`, false when the start or end point was inside. Vanilla finds proxy hits with `hierLevel > 0` (`P:\scripts\4_world\classes\useractionscomponent\actiontargets.c:271`).
- An overlap test reports through `CollisionOverlapCallback.OnContact(IEntity other, Contact contact)` (`P:\scripts\3_game\global\dayzphysics.c:115` to `:121`).
- `CollisionFlags` is FIRSTCONTACT, NEARESTCONTACT, ONLYSTATIC, ONLYDYNAMIC, ONLYWATER, ALLOBJECTS (`P:\scripts\1_core\proto\endebug.c:140` to `:148`). Pass the names, never numbers: a game version that adds `NONE = 0` at the front shifts every value by one (reported, not checked on `P:\`, whose copy has no `NONE`).
- There is no Roadway choice in `ObjIntersect` (`P:\scripts\3_game\constants.c:31` to `:38`), so `RaycastRV` cannot probe a Roadway LOD; see `collision-lods.md` for why that matters for lifts.

Vanilla examples of each family:

| System | Test | Source |
|---|---|---|
| Action cursor | `RaycastRVProxy`, default `ObjIntersectView`, `CollisionFlags.ALLOBJECTS` | `P:\scripts\4_world\classes\useractionscomponent\actiontargets.c:248` to `:255` |
| Action cursor, ground fallback | `RayCastBullet` with `ROADWAY`, `TERRAIN` and `WATERLAYER` | `P:\scripts\4_world\classes\useractionscomponent\actiontargets.c:383` to `:384` |
| Melee aim | `RaycastRV` with `ObjIntersectIFire` | `P:\scripts\4_world\entities\dayzplayerimplementmeleecombat.c:625` |
| Melee obstruction | `RayCastBullet` with `BUILDING`, `DOOR`, `VEHICLE`, `ROADWAY`, `TERRAIN`, `ITEM_SMALL`, `ITEM_LARGE` and `FENCE` | `P:\scripts\4_world\entities\dayzplayerimplementmeleecombat.c:674` |
| Weapon lift | The member mask `hit_mask`, the melee set plus `CHARACTER` and `AI` | `P:\scripts\4_world\entities\firearms\weapon_base.c:75` |
| Admin spawn at the crosshair | `RayCastBullet` with `BUILDING`, `DOOR`, `VEHICLE`, `ROADWAY`, `TERRAIN`, `CHARACTER`, `AI`, `RAGDOLL` and `RAGDOLL_NO_CHARACTER` | `P:\scripts\4_world\plugins\pluginbase\plugindeveloper.c:523` to `:524` |
| Under a roof (`m_IsUnderRoof`) | `RayCastBullet` with `ITEM_LARGE`, `BUILDING` and `VEHICLE` | `P:\scripts\4_world\classes\environment\environment.c:650` to `:654` |
| Placement hologram | `RaycastRV` with `ObjIntersectFire` | `P:\scripts\4_world\classes\hologram.c:683` |

## The action cursor sees View Geometry, not physics

- The cursor's first pass is `RaycastRVProxy` with the default `ObjIntersectView` (above). A model with no View Geometry LOD gets no action prompt, whatever physics body it has. No layer change fixes that; the fix is in the model (`collision-lods.md`).
- The physics world is asked only for the ground under the cursor (the `RayCastBullet` fallback above).
- At a camera pitch of -45 degrees or lower the cursor also collects entities in a cone in front of the player (`GetEntitiesInCone`, `P:\scripts\4_world\classes\useractionscomponent\actiontargets.c:324` to `:325`) with `c_MaxTargetDistance = 3.0` and `c_ConeAngle = 30.0` (`:841`, `:843`), and scores them by distance to the cursor ray (`DistSqrPoint2Line`, `:528`). So an item on the ground can be picked up without any View Geometry hit. Picking an item up proves nothing about its collision.
- Since 1.30 a liquid surface with no object is a target too, at utility 0.01 (the `LIQUID_NONE` test, `P:\scripts\4_world\classes\useractionscomponent\actiontargets.c:532` to `:534`). The `ActionTarget` constructor takes `surfaceName` (`:125`) and `GetSurfaceLiquidType()` reads it back (`:184` to `:187`).

## Surface under a point

- `DayZPhysics.GetHitSurface(other, begPos, endPos, surface)` and `GetHitSurfaceAndLiquid(other, begPos, endPos, surface, liquidType)` name the surface of an object (`P:\scripts\3_game\global\dayzphysics.c:204`, `:206`). What a surface exposes is in `surfaces.md`. On open terrain `GetHitSurfaceAndLiquid` returns no name, because it needs an object and terrain is not one (measured in game, 6 of 6 tries; not checked on `P:\`).
- For terrain use `SurfaceGetType(x, z, out type)` or `SurfaceGetType3D` on the game object (`P:\scripts\3_game\global\game.c:1180`, `:1183`).
