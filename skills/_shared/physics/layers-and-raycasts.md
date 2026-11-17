# Interaction layers and raycasts

Covers the physics interaction layers, the three ways to switch a collision off and what each one touches, the two families of ray and overlap tests, which one each vanilla system uses, and why the action cursor ignores a physics body.

Full signatures and the table of vanilla callers are in `skills/dayz-physics-engine/references/engine-deep-dive.md` (sections 2.6 and 2.7). Probing one LOD of one model is in `collision-lods.md`.

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

`TEMP` is the last named bit (`P:\scripts\3_game\global\dayzphysics.c:42`); there are no layers reserved for mods.

## Three ways to stop a collision

| Call | What it changes | Source |
|---|---|---|
| `dSetInteractionLayer(worldEntity, mask1, mask2, enable)` | The layer to layer matrix of the **whole world**. The first parameter only finds the world. | `P:\scripts\1_core\proto\enphysics.c:11`; the doc of `PhysicsWorld.SetInteractionLayer`, `P:\scripts\1_core\physics\physicsworld.c:14-21` |
| `dBodySetInteractionLayer(ent, mask)` | Which layers **one body** belongs to | `P:\scripts\1_core\proto\enphysics.c:59` |
| `dBodyCollisionBlock(ent1, ent2)` | Collision between **one pair** of entities; `dBodyRemoveBlock` lifts it | `P:\scripts\1_core\proto\enphysics.c:116`, `:117` |

Switching off `CHARACTER` against `DYNAMICITEM` with `dSetInteractionLayer` changes it for every dynamic item on the server. To let one player pass through one object, use the pair block.

To check at run time whether two layers interact, use the query vanilla uses to decide whether an object can block a vehicle door (`dGetInteractionLayer`, `P:\scripts\3_game\vehicles\transport.c:787-788`):

```c
int layer = dBodyGetInteractionLayer(obj);
bool blocksPlayer = dGetInteractionLayer(this, PhxInteractionLayers.CHARACTER, layer);
```

## Two families of tests

They look at different things. Choosing the wrong one is a common cause of "my raycast hits nothing".

| Family | Looks at | Filter | Source |
|---|---|---|---|
| `DayZPhysics.RaycastRV` and `RaycastRVProxy` | The model LODs: Fire Geometry, View Geometry or Geometry | `ObjIntersectFire` (0), `ObjIntersectView` (1), `ObjIntersectGeom` (2), `ObjIntersectIFire` (3), `ObjIntersectNone` (4) | `P:\scripts\3_game\global\dayzphysics.c:199`, `:208`; the values at `:66-71` |
| `DayZPhysics.RayCastBullet`, `SphereCastBullet` and the `OverlapBullet` calls | The physics world: bodies and their layers | A `PhxInteractionLayers` mask | `P:\scripts\3_game\global\dayzphysics.c:211`, `:213`, `:216-228` |

- `RaycastRVParams` defaults to `ObjIntersectView` (`P:\scripts\3_game\global\dayzphysics.c:88`).
- An overlap test reports through `CollisionOverlapCallback.OnContact(IEntity other, Contact contact)` (`P:\scripts\3_game\global\dayzphysics.c:115-121`).
- `CollisionFlags` is FIRSTCONTACT, NEARESTCONTACT, ONLYSTATIC, ONLYDYNAMIC, ONLYWATER, ALLOBJECTS (`P:\scripts\1_core\proto\endebug.c:140-148`). Pass the names, never numbers: a later 1.30 build may put `NONE = 0` first, which shifts every value by one (not checkable on `P:\`, whose copy has no `NONE`).
- There is no Roadway choice in `ObjIntersect` (`P:\scripts\3_game\constants.c:31-38`), so `RaycastRV` cannot probe a Roadway LOD; see `player-controller.md` for why that matters for lifts.

Vanilla examples of each family:

| System | Test | Source |
|---|---|---|
| Action cursor | `RaycastRVProxy`, default `ObjIntersectView`, `CollisionFlags.ALLOBJECTS` | `P:\scripts\4_world\classes\useractionscomponent\actiontargets.c:248-255` |
| Action cursor, ground fallback | `RayCastBullet` with `ROADWAY`, `TERRAIN` and `WATERLAYER` | `P:\scripts\4_world\classes\useractionscomponent\actiontargets.c:383-384` |
| Melee aim | `RaycastRV` with `ObjIntersectIFire` | `P:\scripts\4_world\entities\dayzplayerimplementmeleecombat.c:625` |
| Under a roof (`m_IsUnderRoof`) | `RayCastBullet` with `ITEM_LARGE`, `BUILDING` and `VEHICLE` | `P:\scripts\4_world\classes\environment\environment.c:650-654` |
| Placement hologram | `RaycastRV` with `ObjIntersectFire` | `P:\scripts\4_world\classes\hologram.c:683` |

## The action cursor sees View Geometry, not physics

- The cursor's first pass is `RaycastRVProxy` with the default `ObjIntersectView` (above). A model with no View Geometry LOD gets no action prompt and cannot be selected by admin tools, whatever physics body it has. No layer change fixes that; the fix is in the model (`collision-lods.md`).
- The physics world is asked only for the ground under the cursor (the `RayCastBullet` fallback above).
- At a camera pitch of -45 degrees or lower the cursor also collects entities in a cone in front of the player (`GetEntitiesInCone`, `P:\scripts\4_world\classes\useractionscomponent\actiontargets.c:324-325`) with `c_MaxTargetDistance = 3.0` and `c_ConeAngle = 30.0` (`:841`, `:843`), and scores them by distance to the cursor ray (`DistSqrPoint2Line`, `:528`). So an item on the ground can be picked up without any View Geometry hit. Picking an item up proves nothing about its collision.
- Since 1.30 a liquid surface with no object is a target too, at utility 0.01 (the `LIQUID_NONE` test, `P:\scripts\4_world\classes\useractionscomponent\actiontargets.c:532-534`).

## Surface under a point

- `DayZPhysics.GetHitSurfaceAndLiquid(other, begPos, endPos, surface, liquidType)` names the surface of an object (`P:\scripts\3_game\global\dayzphysics.c:206`). Measured in game (DayZDiag 1.29; not checkable on `P:\`): it returned no name for open terrain in 6 of 6 probes, because it needs an object and terrain is not one.
- For terrain use `SurfaceGetType(x, z, out type)` or `SurfaceGetType3D` on the game object (`P:\scripts\3_game\global\game.c:1180`, `:1183`).
