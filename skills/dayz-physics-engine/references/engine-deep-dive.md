# Engine physics deep dive (Enforce Script)

Covers the full rigid body API (`dBody`, `dGeom`, `dJoint`), interaction layers, the two raycast families and who uses which, contacts, the native drop and throw path, the player controller, surfaces, what the engine syncs to clients, and a worked case (a rolling stone item).

Citations are `P:\...:line`, opened on `P:\` (a 1.30 build). `1.29:<path>:<line>` is a line in the 1.29 scripts, which are not on `P:\` and were not re-checked. In code blocks a comment such as `// :38` is a line of the file named in the heading above the block. What script cannot show is marked `[UNVERIFIED]` or `[INFERRED]`.

## 1. Summary

- The rigid body API is a set of global functions, `dBody...`, `dGeom...` and `dJoint...`, declared in `P:\scripts\1_core\proto\enphysics.c` (a Bullet engine behind ODE style names). They take an `IEntity`: the body is attached to the entity.
- There is also a wrapper class `Physics` (`P:\scripts\1_core\physics\physics.c`) with the same functions as methods (`ApplyImpulse`, `CreateDynamicEx` and so on) plus extras (`ClearForces`, `GetTotalForce`, `SetResponseIndex`, `AddGeom`). Vanilla gameplay code uses the global `dBody` functions almost everywhere; the wrapper is the newer Enfusion style.
- Interaction layers (`PhxInteractionLayers`, `P:\scripts\3_game\global\dayzphysics.c:1-43`) are bit masks. The layer to layer matrix is global per world (`dSetInteractionLayer`), and each body or geometry carries its own mask (`dBodySetInteractionLayer`).
- Raycasts come in two families. `RaycastRV` and `RaycastRVProxy` test the model LODs (Fire, View, Geom, chosen by `ObjIntersect`). `RayCastBullet`, `SphereCastBullet` and the `OverlapBullet` calls test the Bullet physics world, filtered by `PhxInteractionLayers`. The action cursor uses `RaycastRVProxy` with `ObjIntersectView` by default, which is why an action does not appear on a model with no View Geometry.
- Contacts arrive as a `sealed class Contact` (`P:\scripts\1_core\physics\contact.c`) with `Impulse`, `Normal`, `Position` and the velocities before and after, through `EOnContact` once `SetEventMask(EntityEvent.CONTACT)` is set.
- The native path for dynamic items is `InventoryItem.ThrowPhysically(player, force, collideWithCharacters = true)` plus `Object.CreateDynamicPhysics`, `EnableDynamicCCD` and `SetDynamicPhysicsLifeTime`. Vanilla calls `ThrowPhysically` on the server and on the owner client (not on remote clients), so the body exists on both.
- There are no setters for friction or restitution per body, no gravity vector per body, and no `dBodySetVelocity` (the global `SetVelocity` is used). Friction and restitution come from the physics material given to the geometry (the string in `PhysicsGeomDef.MaterialName`, or a `.bisurf` surface).

## 2. Verified API (exact signatures)

### 2.1 Physics world (`P:\scripts\1_core\proto\enphysics.c`)

```c
proto native int    dGetNumDynamicBodies(notnull IEntity worldEnt);          // :9
proto native IEntity dGetDynamicBody(notnull IEntity worldEnt, int index);   // :10
proto native void   dSetInteractionLayer(notnull IEntity worldEntity, int mask1, int mask2, bool enable); // :11
proto native bool   dGetInteractionLayer(notnull IEntity worldEntity, int mask1, int mask2);              // :12
proto native vector dGetGravity(notnull IEntity worldEntity);                // :15
proto native void   dSetGravity(notnull IEntity worldEntity, vector g);      // :17  global, not per body
proto native void   dSetTimeSlice(notnull IEntity worldEntity, float timeSlice); // :19  default 1/40, so 40 steps a second
```

The object style equivalent is `PhysicsWorld`, with `SetInteractionLayer`, `GetGravity`, `SetGravity`, `GetTimeSlice`, `GetUpdateRate` and `SetUpdateRate` (20 to 1000) (`P:\scripts\1_core\physics\physicsworld.c:21-48`).

### 2.2 Creating and destroying bodies (`P:\scripts\1_core\proto\enphysics.c`)

```c
proto bool dBodyCreateStaticEx (notnull IEntity ent, PhysicsGeomDef geoms[]);                       // :38
proto bool dBodyCreateGhostEx  (notnull IEntity ent, PhysicsGeomDef geoms[]);                       // :39
proto bool dBodyCreateDynamicEx(notnull IEntity ent, vector centerOfMass, float mass, PhysicsGeomDef geoms[]); // :51
proto native void dBodyDestroy(notnull IEntity ent);   // :54
proto native bool dBodyIsSet(notnull IEntity ent);     // :57
```

- `PhysicsGeomDef(string name, dGeom geom, string materialName, int layerMask)`, with `Frame[4]` (the local transform) and `ParentNode` (a bone) as public fields (`P:\scripts\1_core\physics\physicsgeomdef.c:9-26`).
- The doc example in vanilla: `PhysicsGeomDef("", dGeomCreateBox(size), "material/default", 0xffffffff)` (`P:\scripts\1_core\proto\enphysics.c:34`).
- Static wrapper calls: `Physics.CreateStatic(ent, layerMask)` and `Physics.CreateDynamic(ent, mass, layerMask)` build from the model's geometry; `Physics.CreateDynamicEx`, `CreateStaticEx` and `CreateGhostEx` take your geometries (`P:\scripts\1_core\physics\physics.c:170-210`).
- The globals `dBodyCreateStatic` and `dBodyCreateDynamic` (no `Ex`, with a layer mask) are used only in `P:\scripts\2_gamelib\entities\scriptmodel.c:31` and `:35`, under `#ifdef GAME_TEMPLATE`, and are not declared in `enphysics.c`. In DayZ use the wrapper `Physics.CreateDynamic` or the `Ex` calls.

### 2.3 State, mass, damping, sleep, CCD (`P:\scripts\1_core\proto\enphysics.c`)

```c
proto native void  dBodySetInteractionLayer(notnull IEntity ent, int mask);          // :59
proto native int   dBodyGetInteractionLayer(notnull IEntity ent);                    // :60
proto native void  dBodySetGeomInteractionLayer(notnull IEntity ent, int index, int mask); // :61
proto native int   dBodyGetGeomInteractionLayer(notnull IEntity ent, int index);     // :62
proto native void  dBodyActive(notnull IEntity ent, ActiveState activeState);        // :64
proto native void  dBodyDynamic(notnull IEntity ent, bool dynamic);                  // :65
proto native bool  dBodyIsDynamic(notnull IEntity ent);                              // :66
proto native bool  dBodyIsActive(notnull IEntity ent);                               // :68
proto native bool  dBodyEnableGravity(notnull IEntity ent, bool enable);             // :69  bool, not a vector
proto native void  dBodySetDamping(notnull IEntity ent, float linearDamping, float angularDamping); // :70
proto native void  dBodySetSleepingTreshold(notnull IEntity body, float linearTreshold, float angularTreshold); // :71
proto native bool  dBodyIsSolid(notnull IEntity ent);                                // :73
proto native void  dBodySetSolid(notnull IEntity ent, bool solid);                   // :74
proto native void  dBodyEnableCCD(notnull IEntity body, float maxMotion, float sphereCastRadius); // :83  -1 disables
proto native void  dBodySetLinearFactor(notnull IEntity body, vector linearFactor);  // :87  zero an axis for 2D physics
proto native vector dBodyGetCenterOfMass(notnull IEntity body);                      // :90
proto native void  dBodySetInertiaTensorV(notnull IEntity body, vector v);           // :119
proto native void  dBodySetInertiaTensorM(notnull IEntity body, vector m[3]);        // :120
proto native float dBodyGetMass(notnull IEntity ent);                                // :122
proto native void  dBodySetMass(notnull IEntity body, float mass);                   // :123
```

- `enum ActiveState { INACTIVE, ACTIVE, ALWAYS_ACTIVE }` (`P:\scripts\1_core\physics\activestate.c:9-17`). `ALWAYS_ACTIVE` stops a rolling object falling asleep half way down a slope.
- `enum SimulationState { NONE, COLLISION, SIMULATION }` (`P:\scripts\1_core\physics\simulationstate.c:12-20`), set through `Physics.ChangeSimulationState` (`P:\scripts\1_core\physics\physics.c:51`).

### 2.4 Impulses, forces, velocities, transform (`P:\scripts\1_core\proto\enphysics.c`)

```c
proto void  dBodyApplyImpulse(notnull IEntity body, vector impulse);                  // :141
proto void  dBodyApplyImpulseAt(notnull IEntity body, vector impulse, vector pos);    // :136  pos in world space
proto void  dBodyApplyForce(notnull IEntity body, vector force);                      // :146
proto void  dBodyApplyForceAt(notnull IEntity body, vector pos, vector force);        // :151
proto native void dBodyApplyTorque(notnull IEntity body, vector torque);              // :153
proto native void dBodyApplyTorqueImpulse(notnull IEntity ent, vector torqueImpulse); // :125
proto native vector GetVelocity(notnull IEntity ent);                                 // :104  global, works on a player
proto native void   SetVelocity(notnull IEntity ent, vector vel);                     // :111  global
proto vector dBodyGetAngularVelocity(notnull IEntity body);                           // :158
proto void   dBodySetAngularVelocity(notnull IEntity body, vector angvel);            // :165  rad/s per axis, not yaw/pitch/roll
proto native vector dBodyGetVelocityAt(notnull IEntity body, vector globalpos);       // :177
proto native void  dBodySetTargetMatrix(notnull IEntity body, vector matrix[4], float timeslice); // :170  kinematic move
proto native void  dBodyGetWorldTransform(notnull IEntity body, out vector matrix[4]);       // :172
proto native void  dBodyGetDirectWorldTransform(notnull IEntity body, out vector matrix[4]); // :173
proto native float dBodyGetKineticEnergy(notnull IEntity body);                       // :175
// Blocking collision between one pair:
proto native dBlock dBodyCollisionBlock(notnull IEntity ent1, notnull IEntity ent2);  // :116
proto native void   dBodyRemoveBlock(notnull IEntity worldEntity, dBlock block);      // :117
```

Only on the `Physics` wrapper: `ClearForces()`, `GetTotalForce()`, `GetTotalTorque()` and `SetResponseIndex(int)` (`P:\scripts\1_core\physics\physics.c:106-115`), `IsKinematic()` (`:63`) and `GetGeomSurfaces(index, out array<SurfaceProperties>)` (`:160`).

### 2.5 Geometries and joints (`P:\scripts\1_core\proto\enphysics.c`)

```c
proto native dGeom dGeomCreateBox(vector size);                       // :186
proto native dGeom dGeomCreateSphere(float radius);                   // :189  the one a rolling stone needs
proto native dGeom dGeomCreateCapsule(float radius, vector extent);   // :192
proto native dGeom dGeomCreateCylinder(float radius, vector extent);  // :195
proto native void  dGeomDestroy(dGeom geom);                          // :198
proto native int   dBodyGetGeom(notnull IEntity ent, string name);    // :202
proto native int   dBodyGetNumGeoms(notnull IEntity ent);             // :204
```

Joints (`P:\scripts\1_core\proto\enphysics.c:212-270`): `dJointCreateHinge`, `Hinge2`, `Slider`, `BallSocket`, `Fixed`, `ConeTwist`, `6DOF` and `6DOFSpring`, each taking `(ent1, ent2, ..., bool block, float breakThreshold)`, plus `dJointDestroy` (`:220`). Setters per type: `dJointHingeSetLimits`, `dJointHingeSetAxis` and `dJointHingeSetMotorTargetAngle` (`:223-225`), `dJointConeTwistSetLimits` (`:241`), `dJoint6DOFSetLinearLimits`, `dJoint6DOFSetAngularLimits` and `dJoint6DOFSetLimit` (`:250-252`), `dJoint6DOFSpringSetSpring` (`:255`; stiffness -1 and damping -1 switch the spring off), and the full slider set (`:258-270`). A joint that breaks raises `EOnJointBreak` (`P:\scripts\1_core\proto\enentity.c:207`).

### 2.6 Interaction layers

`enum PhxInteractionLayers` (`P:\scripts\3_game\global\dayzphysics.c:1-43`), in bit order: NOCOLLISION, DEFAULT, BUILDING, CHARACTER, VEHICLE, DYNAMICITEM, DYNAMICITEM_NOCHAR, ROADWAY, VEHICLE_NOTERRAIN, CHARACTER_NO_GRAVITY, RAGDOLL_NO_CHARACTER, FIREGEOM (a second name for RAGDOLL_NO_CHARACTER), DOOR, RAGDOLL, WATERLAYER, TERRAIN, GHOST, WORLDBOUNDS, FENCE, AI, AI_NO_COLLISION, AI_COMPLEX, TINYCAPSULE, TRIGGER, TRIGGER_NOTERRAIN, ITEM_SMALL, ITEM_LARGE, CAMERA, TEMP.

How they work, checked by use:

- **Global matrix.** `dSetInteractionLayer(world, mask1, mask2, enable)` switches the interaction between layers on or off for the whole world. The first parameter is only the entity used to find the world; the doc of `PhysicsWorld.SetInteractionLayer` says "Modifies interaction matrix of interaction layers" (`P:\scripts\1_core\physics\physicsworld.c:14-21`).
- **Per body.** `dBodySetInteractionLayer(ent, mask)` sets which layers that body belongs to; `dBodySetGeomInteractionLayer` does it for one geometry.
- **Matrix query.** The vanilla pattern, used to decide whether an object blocks a vehicle door by asking whether CHARACTER collides with its layer (`dGetInteractionLayer`, `P:\scripts\3_game\vehicles\transport.c:787-788`):

```c
int layer = dBodyGetInteractionLayer(o);
bool interacts = dGetInteractionLayer(this, PhxInteractionLayers.CHARACTER, layer);
```

  The same query tells you at run time whether CHARACTER against DYNAMICITEM is active.
- There are no reserved "custom" layers; `TEMP` is the last named bit. A new layer would be an unused bit with its pairs switched on through `dSetInteractionLayer` (`[INFERRED]`, a reasonable reading with no vanilla example).

### 2.7 Raycasts, shape casts and overlaps

All on `DayZPhysics` (`P:\scripts\3_game\global\dayzphysics.c:123-230`):

```c
proto static bool RaycastRV(vector begPos, vector endPos, out vector contactPos, out vector contactDir,
    out int contactComponent, set<Object> results = NULL, Object with = NULL, Object ignore = NULL,
    bool sorted = false, bool ground_only = false, int iType = ObjIntersectView, float radius = 0.0,
    CollisionFlags flags = CollisionFlags.NEARESTCONTACT);                                  // :199
proto static bool RaycastRVProxy(notnull RaycastRVParams in, out notnull array<ref RaycastRVResult> results,
    array<Object> excluded = null);                                                         // :208
proto static bool GetHitSurface(Object other, vector begPos, vector endPos, string surface);            // :204
proto static bool GetHitSurfaceAndLiquid(Object other, vector begPos, vector endPos, string surface, out int liquidType); // :206
proto static bool RayCastBullet(vector begPos, vector endPos, PhxInteractionLayers layerMask, Object ignoreObj,
    out Object hitObject, out vector hitPosition, out vector hitNormal, out float hitFraction);          // :211
proto static bool SphereCastBullet(vector begPos, vector endPos, float radius, PhxInteractionLayers layerMask, ...); // :213
proto static bool GeometryOverlapBullet(vector transform[4], dGeom geometry, PhxInteractionLayers layerMask, notnull CollisionOverlapCallback callback); // :216
proto static bool EntityOverlapBullet(...) / EntityOverlapSingleBullet(...) / SphereOverlapBullet(pos, radius, ...)
    / CylinderOverlapBullet(...) / CapsuleOverlapBullet(...) / BoxOverlapBullet(...);       // :218-228
```

- `RaycastRVParams` (`P:\scripts\3_game\global\dayzphysics.c:49-92`): `type` defaults to `ObjIntersectView` (`:88`). The documented values are `ObjIntersectFire(0)`, `ObjIntersectView(1)`, `ObjIntersectGeom(2)`, `ObjIntersectIFire(3)` and `ObjIntersectNone(4)` (`:66-71`); the constants themselves are defined in the engine, not in script.
- `RaycastRVResult` (`P:\scripts\3_game\global\dayzphysics.c:98-113`): `obj` and `parent` (a proxy when `hierLevel > 0`), `pos`, `dir`, `component`, `surface` (a `SurfaceInfo`), `entry` and `exit`.
- `CollisionFlags` (`P:\scripts\1_core\proto\endebug.c:140-148`): FIRSTCONTACT, NEARESTCONTACT, ONLYSTATIC, ONLYDYNAMIC, ONLYWATER, ALLOBJECTS. Not checked on `P:\`: from 1.30.164289 `NONE = 0` comes first, which moves every other value up by one. The copy on `P:\` has no `NONE`.
- `CollisionOverlapCallback.OnContact(IEntity other, Contact contact)` (`P:\scripts\3_game\global\dayzphysics.c:115-121`) receives overlap results.
- `PhxRaycast...` does not exist (0 matches in `P:\scripts`).

Who uses what in vanilla:

| Use | API | Geometry or layers | Citation |
|---|---|---|---|
| Action cursor, first pass | `RaycastRVProxy` | `ObjIntersectView` (the default) with `CollisionFlags.ALLOBJECTS` | `P:\scripts\4_world\classes\useractionscomponent\actiontargets.c:248-255` |
| Action cursor, ground fallback | `RayCastBullet` | `ROADWAY`, `TERRAIN`, `WATERLAYER` | `P:\scripts\4_world\classes\useractionscomponent\actiontargets.c:383-384` |
| Action cursor, liquid surface with no object (1.30) | scoring | utility 0.01 when `GetLiquidType()` is not `LIQUID_NONE` | `P:\scripts\4_world\classes\useractionscomponent\actiontargets.c:532-534` |
| Melee aim and hit zone | `RaycastRV` | `ObjIntersectIFire` | `P:\scripts\4_world\entities\dayzplayerimplementmeleecombat.c:625` |
| Melee obstruction | `RayCastBullet` | `BUILDING`, `DOOR`, `VEHICLE`, `ROADWAY`, `TERRAIN`, `ITEM_SMALL`, `ITEM_LARGE`, `FENCE` | `P:\scripts\4_world\entities\dayzplayerimplementmeleecombat.c:674-689` |
| Weapon lift | the member mask `hit_mask`, which adds `AI` | physics layers | `P:\scripts\4_world\entities\firearms\weapon_base.c:75` |
| Under a roof? (`Environment`) | `RayCastBullet`, 25 m straight up | `ITEM_LARGE`, `BUILDING`, `VEHICLE` | `P:\scripts\4_world\classes\environment\environment.c:650-654` |
| Admin spawn on the crosshair | `RayCastBullet` | `BUILDING`, `DOOR`, `VEHICLE`, `ROADWAY`, `TERRAIN`, `CHARACTER`, `AI`, `RAGDOLL`, `RAGDOLL_NO_CHARACTER` | `P:\scripts\4_world\plugins\pluginbase\plugindeveloper.c:523-524` |

### 2.8 Contacts and events

`sealed class Contact` (`P:\scripts\1_core\physics\contact.c:9-50`):

```c
Physics Physics1; Physics Physics2;
SurfaceProperties Material1; SurfaceProperties Material2;
float  Impulse;            // "Impulse applied to resolve the collision" (:21)
int    ShapeIndex1, ShapeIndex2;
vector Normal;             // collision axis (:27)
vector Position;           // contact point, world space (:29)
float  PenetrationDepth;
float  RelativeNormalVelocityBefore / After;
vector RelativeVelocityBefore / After;
vector VelocityBefore1/2, VelocityAfter1/2;
proto native vector GetNormalImpulse();                       // :47
proto native float  GetRelativeVelocityBefore(vector vel);    // :48
proto native float  GetRelativeVelocityAfter(vector vel);     // :49
```

Register with `SetEventMask(EntityEvent.CONTACT)` (the `CONTACT` value at `P:\scripts\1_core\proto\enentity.c:97`) and override `event protected void EOnContact(IEntity other, Contact extra)` (`:213`). `Contact` can't be created from script: its constructor is private (`P:\scripts\1_core\physics\contact.c:11`).

Vanilla patterns:

- **Player.** The constructor registers the event (`SetEventMask`, `P:\scripts\4_world\entities\dayzplayerimplement.c:174`). `EOnContact` (`P:\scripts\4_world\entities\dayzplayerimplement.c:3958-3974`; `1.29:4_world\entities\dayzplayerimplement.c:3822-3835`) calls `RegisterTransportHit(transport)` when `other` is a `Transport` and `g_Game.IsServer()`.
- **Infected and animals.** `ZombieBase` (`SetEventMask` at `P:\scripts\4_world\entities\creatures\infected\zombiebase.c:50`, `EOnContact` at `:1030-1043`) and `DayZAnimal` (`SetEventMask` at `P:\scripts\3_game\entities\dayzanimal.c:692`, `EOnContact` at `:942`) do the same.
- **`RegisterTransportHit`** (`P:\scripts\3_game\entities\entityai.c:4134`; `1.29:3_game\entities\entityai.c:4089-4156`; the Motorbike branch new in 1.30 at `P:\scripts\3_game\entities\entityai.c:4166-4183`, before Boat): damage of type `DT_CUSTOM` with ammo `"TransportHit"` and magnitude `GetVelocity(transport).Length()`, and if the victim dies, `dBodyApplyImpulse(this, 40 * velocity)` (for a Motorbike the corpse impulse is `5.0 * velocity`, not 40). A stone that should hurt and launch uses the same damage plus impulse pattern.
- **`ItemBase`.** `EOnContact` (`P:\scripts\4_world\entities\itembase.c:1119-1148`) uses `extra.RelativeVelocityBefore.Length()`, through `ProcessImpactSoundEx` (`P:\scripts\3_game\entities\inventoryitem.c:200-227`), for the impact sound; the client plays it under `#ifndef SERVER` and the server sets a sync variable. It does not use `Impulse` for force.
- **Vehicles.** The high level callback is `Transport.OnContact(string zoneName, vector localPos, IEntity other, Contact data)` (`P:\scripts\3_game\vehicles\transport.c:315-343`). In 1.29 `CarScript` overrode it (`1.29:4_world\entities\vehicles\carscript.c:1454-1480`); in 1.30 cars inherit `Transport.OnContact`. Damage comes from the vehicle's own change of momentum, not from `data.Impulse`. The warning "Can be called very frequently in one frame" is above `BoatScript.OnContact` in 1.30 (`P:\scripts\4_world\entities\vehicles\boatscript.c:425`; `1.29:4_world\entities\vehicles\carscript.c:1453`).
- **`ItemBase` with trigger and contact together.** `EasterEgg` sets `SetEventMask(EntityEvent.CONTACT | EntityEvent.TOUCH)` (`P:\scripts\4_world\entities\itembase\gear\consumables\easteregg.c:40`). The fireplace does the same (`P:\scripts\4_world\entities\itembase\fireplacebase\fireplace.c:17`), raises a flag in `ContactEvent` after checking `dBodyIsActive(this)` (`:62`), and handles the contact in `EOnPostSimulate` (`:66`).

### 2.9 Native path for dynamic items (drop and throw)

```c
// P:\scripts\3_game\entities\inventoryitem.c
proto native void EnableCollisionsWithCharacter(bool state);   // :21
proto native bool HasCollisionsWithCharacter();                // :22
proto native void ThrowPhysically(DayZPlayer player, vector force, bool collideWithCharacters = true); // :26
proto native void ForceFarBubble(bool state);                  // :31  use the far network bubble
// P:\scripts\3_game\entities\object.c
proto native void CreateDynamicPhysics(int interactionLayers); // :456 (line 462 in 1.29)
proto native void EnableDynamicCCD(bool state);                // :457 (line 463 in 1.29)
proto native void SetDynamicPhysicsLifeTime(float lifeTime);   // :458 (line 464 in 1.29)
```

The lifecycle seen in vanilla:

1. **Throw from the hands.** `HandActionThrow.Action` (`P:\scripts\3_game\systems\inventory\hand_actions.c:62-88`) moves the item to the ground through the inventory and then:

```c
if ( player.GetInstanceType() != DayZPlayerInstanceType.INSTANCETYPE_REMOTE )
    item.ThrowPhysically(player, throwEvent.GetForce());
```

   It runs on the server and on the owner client, not on remotes: the dynamic simulation exists on both. Remotes receive the result over the network (`[UNVERIFIED]`: the replication inside the engine is not visible in script).
2. **Emptying an inventory or container.** `MiscGameplayFunctions.ThrowEntityFromInventory` (`P:\scripts\4_world\static\miscgameplayfunctions.c:1297-1353`) calls `entityIB.ThrowPhysically(null, force, false)` (`:1345`), so with no collision against characters, and for entities that are not `ItemBase` it calls `dBodyApplyImpulse(entity, force)` (`:1351`).
3. **Admin spawn with physics.** `item.ThrowPhysically(null, "0 0 0")` on the server starts the fall (`P:\scripts\4_world\plugins\pluginbase\plugindeveloper.c:430` and `:553`).
4. **Stopping.** `ItemBase.StopItemDynamicPhysics()` calls `SetDynamicPhysicsLifeTime(0.01)` (`P:\scripts\4_world\entities\itembase.c:4530-4534`). The drop physics has a lifetime managed by the engine; 0.01 ends it at once. The flag is `m_ItemBeingDroppedPhys` (`P:\scripts\4_world\entities\itembase.c:59`).
5. `CreateDynamicPhysics(layers)` is never called from vanilla script (only its declaration matches). The engine calls it inside `ThrowPhysically` (`[INFERRED]`); it is exposed for mods.
6. **Hook to set the body up again.** `override void OnCreatePhysics()` calls `RefreshPhysics()` (`P:\scripts\4_world\entities\itembase.c:1150-1155`). Real `RefreshPhysics` overrides: `P:\scripts\4_world\entities\itembase\tentbase.c:162`, the fireplace (`P:\scripts\4_world\entities\itembase\fireplacebase\fireplace.c:479`), `hescobox.c`, `kitbase.c` and `batterycharger.c` in `P:\scripts\4_world\entities\itembase\`.

The layers `DYNAMICITEM` and `DYNAMICITEM_NOCHAR` (`P:\scripts\3_game\global\dayzphysics.c:9-10`) match the `collideWithCharacters` parameter of `ThrowPhysically` and `EnableCollisionsWithCharacter` (`[INFERRED]` from the names and the signature; the assignment inside the engine is `[UNVERIFIED]`).

### 2.10 Player controller (character controller)

The player's controller is not a rigid body that script can see. Its API is on `Human` (`P:\scripts\3_game\human.c`):

```c
proto native bool    CheckFreeSpace(vector localDir, float distance, bool useHeading, vector posOffset = vector.Zero, float xzScale = 1.0); // :1381
proto       float    CollisionMoveTest(vector dir, vector offset, float xzScale, IEntity ignoreEntity, out IEntity hitEntity, out vector hitPosition, out vector hitNormal); // :1387
proto native void    LinkToLocalSpaceOf(notnull IEntity child, vector pLocalSpaceMatrix[4]); // :1391
proto native bool    PhysicsIsFalling(bool pValidate);            // :1428  also true while the ragdoll moves faster than 1 m/s
proto native IEntity PhysicsGetFloorEntity();                     // :1431
proto native IEntity PhysicsGetLinkedEntity();                    // :1434
proto native bool    PhysicsWasSlidingOffLinkedEntity();          // :1438  config 'animPhysDetachSpeed'
proto native void    PhysicsGetVelocity(out vector pVelocity);    // :1441
proto native void    PhysicsEnableGravity(bool pEnable);          // :1443
proto native bool    PhysicsIsSolid();                            // :1445
proto native void    PhysicsSetSolid(bool pSolid);                // :1446
proto native void    PhysicsSetSimpleDeath(bool pEnable);         // :1449  new in 1.30, the "old" death state
proto native void    PhysicsSetRagdoll(bool pEnable);             // :1451
proto native bool    PhysicsIsRagdoll();                          // :1452
```

- The same calls in 1.29 (`1.29:3_game\human.c`): `CheckFreeSpace` 1354, `CollisionMoveTest` 1357, `LinkToLocalSpaceOf` 1361, `PhysicsIsFalling` 1397, `PhysicsGetFloorEntity` 1400, `PhysicsGetLinkedEntity` 1403, `PhysicsWasSlidingOffLinkedEntity` 1407, `PhysicsGetVelocity` 1410, `PhysicsEnableGravity` 1412, `PhysicsIsSolid` 1414, `PhysicsSetSolid` 1415, `PhysicsSetRagdoll` 1418. In 1.29 the comment above `PhysicsSetRagdoll` read "Sets and synchronize interaction layers 'RAGDOLL' and 'RAGDOLL_NO_CHARACTER' to prevent body stacking and players going through dead creatures" (line 1417); the 1.30 file no longer has it.
- New in 1.30: `PhysicsSetSimpleDeath` sits under the comment "Old system for handling player death state, was previously handled by PhysicsSetRagdoll" (`P:\scripts\3_game\human.c:1448-1449`); `HumanCommandUnconscious.IsRagdoll()` (`P:\scripts\3_game\human.c:647`); the death branch calls `PhysicsSetSimpleDeath(true)` (`P:\scripts\4_world\entities\dayzplayerimplement.c:745`).
- The controller belongs to the `CHARACTER` layer (`[INFERRED]`, strongly: the query at `P:\scripts\3_game\vehicles\transport.c:788` asks `dGetInteractionLayer(this, PhxInteractionLayers.CHARACTER, layer)` to decide what blocks a player).
- Vanilla drives it: `PhysicsEnableGravity(true)` when a vehicle death's simulation ends (`P:\scripts\4_world\entities\dayzplayerimplement.c:32`) and `PhysicsSetSolid(true)` (`:661`).
- For a player not to pass through a stone, the stone's body must (a) exist on the machine that simulates the controller, which is the player's own client, and (b) be in a layer whose interaction with `CHARACTER` is on, for example `DYNAMICITEM`.

### 2.11 Surfaces

- `SurfaceProperties` is opaque (`P:\scripts\1_core\physics\surfaceproperties.c:9-15`). The useful subclass is `SurfaceInfo` (`P:\scripts\3_game\surfaceinfo.c:8-71`): `GetByName` and `GetByFile` (O(n), `:16` and `:22`), `GetName`, `GetEntryName`, `GetSurfaceType`, `GetRoughness`, `GetDustness`, `GetBulletPenetrability`, `GetThickness`, `GetDeflection`, `GetTransparency`, `GetAudability`, `IsLiquid`, `IsStairs`, `IsPassthrough`, `IsSolid`, `GetSoundEnv`, `GetImpact`, `GetLiquidType`, `GetStepParticleId`, `GetWheelParticleId`. Its header comment says surfaces are defined in `CfgSurfaces` or in an object's `.bisurf` file, and that the engine manages their lifetime, so do not store handles (`P:\scripts\3_game\surfaceinfo.c:4-5`).
- Detection on `CGame` (`P:\scripts\3_game\global\game.c`): `GetSurface(SurfaceDetectionParameters, SurfaceDetectionResult)` (`:1169`), `SurfaceY` (`:1176`), `SurfaceRoadY` and `SurfaceRoadY3D` (`:1177-1178`), `SurfaceGetType` and `SurfaceGetType3D` (`:1180-1183`), `SurfaceUnderObject`, `SurfaceUnderObjectEx` and `SurfaceUnderObjectByBone` (`:1184-1186`), `SurfaceGetNormal` (`:1188`), sea level and waves (`:1189-1202`). The config helpers `IsSurfaceDigable` and `IsSurfaceFertile` read `CfgSurfaces <surface> isDigable` and `isFertile` (`:1246-1260`).
- Item impact: `DayZPhysics.GetHitSurfaceAndLiquid`, used at `P:\scripts\3_game\entities\inventoryitem.c:170-175`.
- Surface friction and restitution are not exposed to script: `SurfaceInfo` has no friction getter, and the physics material is assigned by string when a geometry is created (`PhysicsGeomDef.MaterialName`, for example `"material/default"`).

### 2.12 What the engine syncs to clients

- `Transport` has `proto native void Synchronize()`, "Synchronizes car's state in case the simulation is not running" (`P:\scripts\3_game\vehicles\transport.c:171-172`). Under `FEATURE_NETWORK_RECONCILIATION`, `Transport extends Pawn` (`P:\scripts\3_game\vehicles\transport.c:66`) with the states `TransportOwnerState` and `TransportMove` (transform plus linear and angular velocity, `:11-50`): move replication with replay ("full state synchronization ... triggering a replay on the owner", `P:\scripts\3_game\entities\pawn.c:20-24`).
- `EntityAI` syncs variables through `RegisterNetSyncVariableBool`, `Int`, `Float` and `Object` (`P:\scripts\3_game\entities\entityai.c:2832-2869`) and `SetSynchDirty` (`:3064`). Position is not part of that.
- A thrown `ItemBase` is simulated on the server and the owner client (2.9, step 1). The final position on remotes comes from the inventory flow (`LocationSyncMoveEntity`, `P:\scripts\3_game\systems\inventory\hand_actions.c:74`) and the native item replication (`[UNVERIFIED]`, not visible in script).
- For a body made with `dBodyCreateDynamicEx` on an `ItemBase` there is no script that syncs the transform. If a client sees it move (observed in game), that is the native replication of the entity's position, not a simulation: the client has no body, so the player passes through it.

## 3. Vanilla patterns

**Create a dynamic body with your own geometry.** The only complete example, with `dBodyCreateDynamicEx`, is under `#ifdef GAME_TEMPLATE` (`P:\scripts\2_gamelib\entities\scriptmodel.c:35-51`):

```c
PhysicsGeomDef geoms[] = {PhysicsGeomDef("", dGeomCreateBox(size), "material/default", 0xffffffff)};
dBodyCreateDynamicEx(this, center, 1, geoms);
if (dBodyIsSet(this)) {
    dBodySetMass(this, 1.0);
    dBodyActive(this, ActiveState.ACTIVE);
    dBodyDynamic(this, true);
}
// destructor: if (dBodyIsSet(this)) dBodyDestroy(this);   // scriptmodel.c:57-58
```

**Native throw on the server and the owner client** (`P:\scripts\3_game\systems\inventory\hand_actions.c:76-81`):

```c
DayZPlayer player = DayZPlayer.Cast(e.m_Player);
if ( player.GetInstanceType() != DayZPlayerInstanceType.INSTANCETYPE_REMOTE )
    item.ThrowPhysically(player, throwEvent.GetForce());
```

**Damage, and an impulse when the vehicle contact kills** (`P:\scripts\3_game\entities\entityai.c:4149-4164`, condensed):

```c
if (car.GetSpeedometerAbsolute() > 2)
    ProcessDirectDamage(DT_CUSTOM, transport, "", "TransportHit", "0 0 0", damage);
if (IsDamageDestroyed() && car.GetSpeedometerAbsolute() > 3) {
    impulse = 40 * m_TransportHitVelocity;
    impulse[1] = 40 * 1.5;
    dBodyApplyImpulse(this, impulse);
}
```

**Action cursor.** `RaycastRVProxy` with `CollisionFlags.ALLOBJECTS` and the default type `ObjIntersectView` (`P:\scripts\4_world\classes\useractionscomponent\actiontargets.c:248-255`); proxies are found with `res.hierLevel > 0` (`:271`).

**Layer matrix query.** `P:\scripts\3_game\vehicles\transport.c:787-788` (see 2.6).

**Impact speed for effects.** `float impactVelocity = extra.RelativeVelocityBefore.Length();` (`P:\scripts\3_game\entities\inventoryitem.c:202`), ignored under 0.3 and throttled to one per 0.33 s.

## 4. Gotchas

1. `dSetInteractionLayer` changes the world's global matrix (layer to layer), not one body; the first parameter only finds the world (the doc of `PhysicsWorld.SetInteractionLayer`, `P:\scripts\1_core\physics\physicsworld.c:14-21`). Switching off CHARACTER against DYNAMICITEM affects every dynamic item on the server.
2. `Contact` is `sealed` with a private constructor and destructor (`P:\scripts\1_core\physics\contact.c:11-12`): it can't be created or inherited, only received.
3. `EOnContact` fires only with `SetEventMask(EntityEvent.CONTACT)` set and an active body; the fireplace also checks `dBodyIsActive(this)` (`P:\scripts\4_world\entities\itembase\fireplacebase\fireplace.c:62`). On a passive receiver (a player hit by a vehicle) the player's event fires even though the active body is the car.
4. A vehicle's `OnContact` (per damage zone) "Can be called very frequently in one frame" (`P:\scripts\4_world\entities\vehicles\boatscript.c:425`; `1.29:4_world\entities\vehicles\carscript.c:1453`). Buffer it, as vanilla does with `m_ContactCache` in `Transport.OnContact` (`P:\scripts\3_game\vehicles\transport.c:315-343`).
5. The `ObjIntersect...` constants are not defined in script (they are engine built-ins); the values to trust are in the comment at `P:\scripts\3_game\global\dayzphysics.c:66-71`.
6. `dBodyCreateDynamic` and `dBodyCreateStatic` (no `Ex`) exist only in `GAME_TEMPLATE` code and do not compile in DayZ. Use `Physics.CreateDynamic` (the wrapper, `P:\scripts\1_core\physics\physics.c:189`) or `dBodyCreateDynamicEx`.
7. The cursor (`RaycastRVProxy` with `ObjIntersectView`) sees View Geometry. With no View Geometry LOD in the `.p3d` there is no action target even when a rigid body exists: the body lives in the Bullet world, which the cursor does not query except for the ground fallback (`RayCastBullet` with `ROADWAY|TERRAIN|WATERLAYER`, `P:\scripts\4_world\classes\useractionscomponent\actiontargets.c:383-384`). This explains a "Push does not appear" bug.
8. `dBodySetAngularVelocity` takes rotation around the x, y and z axes in rad/s, "not yaw/pitch/roll" (`P:\scripts\1_core\proto\enphysics.c:163`).
9. `SetDynamicPhysicsLifeTime` means drop physics is temporary by design: the engine removes it when the lifetime passes. An object that must roll with no end has to prevent or renew that timeout, or not rely on the drop path. The default, measured in game, is 15 s (`SKILL.md`, truth 7).
10. `GetVelocity` and `SetVelocity` are global functions (they work for a `Man` and for bodies). Do not look for `dBodyGetVelocity`; it does not exist.
11. `Physics.KMH2MS`, `MS2KMH`, `STANDARD_GRAVITY` (9.81) and `VGravity` (`"0 -9.81 0"`) are ready made constants (`P:\scripts\1_core\physics\physics.c:18-21`).
12. The default physics time step is 1/40 s (`dSetTimeSlice`, `P:\scripts\1_core\proto\enphysics.c:18-19`); `PhysicsWorld.SetUpdateRate` accepts 20 to 1000 (`P:\scripts\1_core\physics\physicsworld.c:46-48`). Changing it is global.

## 5. What does not exist

Each absence was checked by search across `P:\scripts`.

| Typical invention | Reality |
|---|---|
| `dBodySetFriction`, `SetFriction`, `SetRestitution`, `SetBounciness`, `SetElasticity`, `SetBounce` | 0 matches. Friction and restitution come from the geometry's physics material (the `MaterialName` string) or the surface; there is no run time setter per body. |
| A gravity vector per body (`dBodySetGravity`, `SetGravityDir`, `GravityFactor`) | 0 matches. Only `dBodyEnableGravity(ent, bool)` (on or off) and the global `dSetGravity(world, g)`. |
| `dBodySetVelocity`, `dBodyGetVelocity` | Do not exist. Use the globals `SetVelocity` and `GetVelocity` (`P:\scripts\1_core\proto\enphysics.c:104` and `:111`) and `dBodySetAngularVelocity`, `dBodyGetAngularVelocity`. |
| `dBodyApplyAngularImpulse` | Does not exist; it is `dBodyApplyTorqueImpulse` (`P:\scripts\1_core\proto\enphysics.c:125`). |
| `AddForce` (Unity style) | 0 matches; it is `dBodyApplyForce` and `dBodyApplyForceAt`. |
| `SetMaxLinearVelocity`, `SetMaxAngularVelocity` | 0 matches; there is no velocity clamp per body. Do it by hand in your own tick. |
| `PhxRaycast...` | 0 matches; the physics world calls are the `Bullet` ones in `DayZPhysics`. |
| A script call to `CreateDynamicPhysics` in vanilla | 0 uses, only the declaration (`P:\scripts\3_game\entities\object.c:456`). Available to mods; no vanilla pattern to copy. |
| A way to set mass from config at run time | `dBodySetMass` exists, but there is no physical "SetWeight". The config weight is for sound and inventory: in 1.30 it is a field of the entity type, `EntityAIType.m_ConfigWeight` (`P:\scripts\3_game\entities\entityaitype.c:18`), read by the impact sound (`P:\scripts\4_world\entities\itembase.c:1125`); 1.29 read it on the item (`1.29:4_world\entities\itembase.c:1199`). |

## 6. Recipes for mods

**A. A custom dynamic body (a sphere) on the server:**

```c
PhysicsGeomDef geoms[] = {PhysicsGeomDef("", dGeomCreateSphere(0.5), "material/default",
    PhxInteractionLayers.DYNAMICITEM)};
dBodyCreateDynamicEx(this, vector.Zero, 80.0, geoms);              // centre of mass offset from the pivot (P:\scripts\2_gamelib\entities\scriptmodel.c:40-44 passes the bounds centre)
dBodySetInteractionLayer(this, PhxInteractionLayers.DYNAMICITEM);  // collides as a dynamic item
dBodyActive(this, ActiveState.ALWAYS_ACTIVE);                      // never sleeps
dBodySetDamping(this, 0.05, 0.2);
dBodyEnableCCD(this, 0.4, 0.45);                                   // about the radius; against tunneling
// push: dBodyApplyImpulseAt(this, dir * force, contactPosWS);
// clean up: if (dBodyIsSet(this)) dBodyDestroy(this);
```

The limit, shown in practice: the body exists only where it was created. The local client's controller does not see it, so the player walks through it.

**B. The native path (recommended).** Let the item use the engine's drop and throw physics.

```c
// On the server and on the owner client (the guard at hand_actions.c:77):
item.ThrowPhysically(null, impulse, true);   // true: collides with CHARACTER
item.EnableDynamicCCD(true);
item.SetDynamicPhysicsLifeTime(3600);        // renew or extend for long rolling; confirm the exact behaviour in game
```

The `.p3d` needs a Geometry LOD (collision), a View Geometry LOD (cursor and actions) and a Fire Geometry LOD (bullets). The engine builds the physics geometries from the model, so no `dGeomCreate...` call is needed.

**C. Reading the force of an impact** (damage by speed, the vanilla pattern):

```c
void MyStone() { SetEventMask(EntityEvent.CONTACT); }
override void EOnContact(IEntity other, Contact extra)
{
    float v = extra.RelativeVelocityBefore.Length();      // relative impact speed (m/s)
    // or extra.Impulse (kg·m/s applied by the solver) / extra.GetNormalImpulse()
    if (g_Game.IsServer() && v > 4 && other.IsInherited(DayZPlayer)) { /* ProcessDirectDamage; no dBodyApplyImpulse on a living player (controller): deal damage */ }
}
```

A living player (the controller) is not pushed with `dBodyApplyImpulse`; vanilla does that only to corpses and ragdolls (`P:\scripts\3_game\entities\entityai.c:4158-4164`).

**D. Switching off the collision between two specific entities.** `dBlock b = dBodyCollisionBlock(entA, entB);` and later `dBodyRemoveBlock(world, b);` (`P:\scripts\1_core\proto\enphysics.c:116-117`). More precise than touching the global matrix.

**E. A physics raycast with a layer filter:**

```c
Object hit; vector pos, n; float frac;
DayZPhysics.RayCastBullet(from, to, PhxInteractionLayers.DYNAMICITEM|PhxInteractionLayers.TERRAIN, ignore, hit, pos, n, frac);
```

## 7. Worked case: a rolling stone item

The case: a stone, an `ItemBase`, that players push and that rolls and hurts.

1. **"The player passes through the stone."** Architectural, not a layer problem. A body made with `dBodyCreateDynamicEx` on the server only will never collide with the local client's controller, which is simulated on the client. The right fix is a body on the client too: create it on both sides, or better, use the native path (`ThrowPhysically` or `CreateDynamicPhysics`), which vanilla already runs on the server and the owner (`P:\scripts\3_game\systems\inventory\hand_actions.c:77-81`).
2. **"Push does not appear."** Confirmed: the cursor uses `RaycastRVProxy` with `ObjIntersectView` (`P:\scripts\4_world\classes\useractionscomponent\actiontargets.c:248-255`); with no View Geometry LOD there is no target. No physics layer fixes it.
3. **Damage and impulse.** The pattern `EOnContact`, then a server check, then `ProcessDirectDamage` with `"TransportHit"` is exactly what vanilla does (`P:\scripts\4_world\entities\dayzplayerimplement.c:3958-3974` and `P:\scripts\3_game\entities\entityai.c:4134-4224`), but the other way round: in vanilla the victim handles the event, not the striker. A player's `EOnContact` will not see a stone as a `Transport`, so the stone should detect the contact and damage the player, or register its own damage.
4. **Keeping it rolling.** `dBodyActive` with `ALWAYS_ACTIVE`, a low `dBodySetSleepingTreshold`, a low `dBodySetDamping`, and CCD with `dBodyEnableCCD(maxMotion about diameter * 0.8, inner radius)`.
5. **Pushing.** `dBodyApplyImpulseAt(stone, dir * F, contactPos)` gives natural roll (an implied torque), better than `dBodyApplyImpulse` at the origin.
6. **Checking layers at run time.** Log `dGetInteractionLayer(this, PhxInteractionLayers.CHARACTER, dBodyGetInteractionLayer(this))` after creating the body (the pattern at `P:\scripts\3_game\vehicles\transport.c:787-788`).
7. **If moving to the native path.** Watch `SetDynamicPhysicsLifeTime` (drop physics expires; `StopItemDynamicPhysics` ends it with 0.01, `P:\scripts\4_world\entities\itembase.c:4530-4534`) and `EnableCollisionsWithCharacter(true)`.

## 8. Vanilla files

The vanilla files cited above, all under `P:\scripts\`:

- `1_core\proto\enphysics.c` (the whole `dBody`, `dGeom` and `dJoint` API)
- `1_core\physics\contact.c`, `physics.c`, `physicsworld.c`, `physicsgeomdef.c`, `activestate.c`, `simulationstate.c`, `surfaceproperties.c`
- `1_core\proto\enentity.c` (`EntityEvent`, the `EOn...` events), `1_core\proto\endebug.c` (`CollisionFlags`)
- `3_game\global\dayzphysics.c` (`PhxInteractionLayers`, `DayZPhysics`), `3_game\global\game.c` (surfaces)
- `3_game\entities\object.c`, `inventoryitem.c`, `entityai.c`, `pawn.c`, `dayzanimal.c`, and `3_game\human.c`
- `3_game\vehicles\transport.c`, `3_game\systems\inventory\hand_actions.c`, `3_game\surfaceinfo.c`
- `4_world\entities\itembase.c`, `dayzplayerimplement.c`, `dayzplayerimplementmeleecombat.c`, `4_world\entities\creatures\infected\zombiebase.c`, `4_world\entities\vehicles\carscript.c`, `4_world\entities\firearms\weapon_base.c`
- `4_world\classes\useractionscomponent\actiontargets.c`, `4_world\classes\environment\environment.c`, `4_world\static\miscgameplayfunctions.c`, `4_world\plugins\pluginbase\plugindeveloper.c`
- `2_gamelib\entities\scriptmodel.c` (`GAME_TEMPLATE`), `4_world\entities\itembase\tentbase.c`, `fireplacebase\fireplace.c`, `gear\consumables\easteregg.c`

## 9. DayZ 1.30

The line moves and the new player physics calls are folded into the sections above. The `.ragdoll` file and `RagdollDef`, `PhysicsSetSimpleDeath`, the unconscious wake guard on `PhysicsIsFalling` and the fall damage `CurveExp` are in `ragdoll-and-fall-damage.md`. The Motorbike branch of `RegisterTransportHit` and the fall damage thresholds are in `damage-and-transporthit.md`.
