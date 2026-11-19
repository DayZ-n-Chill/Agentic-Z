# Rigid bodies from script

Covers creating, waking, moving and removing a physics body from Enforce Script, where friction and bounce come from, the calls that do not exist, and why a script body fails on an item that already has a native one.

For an item that only has to fall or be thrown, use the native path in `drop-and-throw.md`. Joints between two bodies are in `joints.md`.

## The physics world

- `dGetGravity(worldEnt)` and `dSetGravity(worldEnt, g)` read and change the gravity of the whole world, not of one body (`P:\scripts\1_core\proto\enphysics.c:15`, `:17`).
- `dSetTimeSlice(worldEnt, timeSlice)`: "Default is 1/40, thus simulation runs on 40fps" (`P:\scripts\1_core\proto\enphysics.c:18` to `:19`). `PhysicsWorld.GetTimeSlice`, `GetUpdateRate` and `SetUpdateRate` are the class versions (`P:\scripts\1_core\physics\physicsworld.c:37`, `:42`, `:48`). Changing either changes the step for everything.

## Two APIs, one engine

- The global functions `dBody...`, `dGeom...` and `dJoint...` take an entity and are what vanilla gameplay code uses (`dBodyIsSet`, `P:\scripts\1_core\proto\enphysics.c:57`).
- The `Physics` class wraps the same engine as methods on `obj.GetPhysics()` and adds a few extras: `ClearForces`, `GetTotalForce`, `GetTotalTorque` and `SetResponseIndex` (`P:\scripts\1_core\physics\physics.c:106` to `:115`), and the constants `KMH2MS`, `MS2KMH`, `STANDARD_GRAVITY` and `VGravity` (`:18` to `:21`).

## Creating and removing a body

| Call | Does | Source |
|---|---|---|
| `dBodyCreateStaticEx(ent, geoms)` | Static body from your own geometries | `P:\scripts\1_core\proto\enphysics.c:38` |
| `dBodyCreateGhostEx(ent, geoms)` | Ghost body from your own geometries (vanilla does not say more about what a ghost does) | `P:\scripts\1_core\proto\enphysics.c:39` |
| `dBodyCreateDynamicEx(ent, centerOfMass, mass, geoms)` | Dynamic body from your own geometries | `P:\scripts\1_core\proto\enphysics.c:51` |
| `Physics.CreateDynamic(ent, mass, layerMask)` | Dynamic body "from geometry embedded in attached VObject", that is from the model; false when the model has none | `P:\scripts\1_core\physics\physics.c:184` to `:189` |
| `Physics.CreateStatic(ent, layerMask)` | Static body from the model's geometry; `layerMask` is ANDed with the layers in the model, so `0xffffffff` keeps them | `P:\scripts\1_core\physics\physics.c:166` to `:170` |
| `Physics.CreateGhostEx(ent, geoms)` | Ghost body from your own geometries | `P:\scripts\1_core\physics\physics.c:210` |
| `dBodyDestroy(ent)` | Removes the body | `P:\scripts\1_core\proto\enphysics.c:54` |

- A geometry is a `PhysicsGeomDef(name, geom, materialName, layerMask)` (`P:\scripts\1_core\physics\physicsgeomdef.c:18`), with the public fields `Frame[4]`, its local transform, and `ParentNode`, a bone it can attach to (`:13`, `:14`). The vanilla doc example is `PhysicsGeomDef("", dGeomCreateBox(size), "material/default", 0xffffffff)` (`P:\scripts\1_core\proto\enphysics.c:34`). The shapes are `dGeomCreateBox`, `dGeomCreateSphere`, `dGeomCreateCapsule` and `dGeomCreateCylinder` (`P:\scripts\1_core\proto\enphysics.c:186` to `:195`); `dGeomDestroy` frees one (`:198`). On a body, `dBodyGetGeom(ent, name)` finds a geometry's index, -1 when missing, and `dBodyGetNumGeoms(ent)` counts them (`:202`, `:204`).
- For the centre of mass, vanilla's test body passes the centre of its bounds, `(mins + maxs) * 0.5` (`P:\scripts\2_gamelib\entities\scriptmodel.c:40` to `:44`).
- Always remove the old body before creating a new one: `if (dBodyIsSet(this)) dBodyDestroy(this);`. The vanilla test entity does this in its destructor (`dBodyDestroy`, `P:\scripts\2_gamelib\entities\scriptmodel.c:57` to `:58`).
- `dBodyCreateStatic` and `dBodyCreateDynamic` (no `Ex`) appear only inside `#ifdef GAME_TEMPLATE` code (`P:\scripts\2_gamelib\entities\scriptmodel.c:31` and `:35`) and are not declared for DayZ.

A script body does not attach to a vanilla inventory item. On `SmallStone` and `WoodenStick`, `Physics.CreateDynamic`, `CreateDynamicEx` and `CreateStaticEx` return false every time, while `ThrowPhysically` works on the same items (measured in game; not checked on `P:\`). Items already have a native body, so a script body needs a host entity with no physics of its own.

## State, sleep and fast bodies

| Call | Does | Source |
|---|---|---|
| `dBodyActive(ent, ActiveState)` | Wake, sleep, or `ALWAYS_ACTIVE` (never sleeps) | `P:\scripts\1_core\proto\enphysics.c:64`; enum at `P:\scripts\1_core\physics\activestate.c:9` |
| `dBodyDynamic(ent, bool)` | Switch between dynamic and static | `P:\scripts\1_core\proto\enphysics.c:65` |
| `dBodyEnableGravity(ent, bool)` | Gravity on or off; there is no gravity vector per body | `P:\scripts\1_core\proto\enphysics.c:69` |
| `dBodySetDamping(ent, linear, angular)` | Damping | `P:\scripts\1_core\proto\enphysics.c:70` |
| `dBodySetSleepingTreshold(body, linear, angular)` | When the body may fall asleep | `P:\scripts\1_core\proto\enphysics.c:71` |
| `dBodySetLinearFactor(body, linearFactor)` | Scales all impulses, velocities and forces per axis; "Zero any axis if you want to do 2D physics" | `P:\scripts\1_core\proto\enphysics.c:84` to `:87` |
| `dBodyEnableCCD(body, maxMotion, sphereCastRadius)` | Continuous collision detection; see "Fast bodies" in `drop-and-throw.md` | `P:\scripts\1_core\proto\enphysics.c:83` |
| `dBodyIsSolid(ent)` and `dBodySetSolid(ent, bool)` | Whether the body is solid | `P:\scripts\1_core\proto\enphysics.c:73`, `:74` |
| `dBodyGetCenterOfMass(body)` | The centre of mass offset | `P:\scripts\1_core\proto\enphysics.c:90` |
| `dBodySetInertiaTensorV(body, v)` and `dBodySetInertiaTensorM(body, m[3])` | Inertia tensor | `P:\scripts\1_core\proto\enphysics.c:119`, `:120` |
| `dBodyGetMass` and `dBodySetMass` | Mass in kg; see `mass-and-weight.md` | `P:\scripts\1_core\proto\enphysics.c:122`, `:123` |
| `Physics.IsKinematic()` and `Physics.ChangeSimulationState(state)` | Kinematic check; switch between `NONE`, `COLLISION` and `SIMULATION` | `P:\scripts\1_core\physics\physics.c:63`, `:51` |

- An impulse on a sleeping body is lost (engine behavior, not visible on `P:\`; confirm in game). Wake it first: `dBodyActive(ent, ActiveState.ACTIVE)` then `dBodyDynamic(ent, true)`.
- For a body that must keep rolling, use `ALWAYS_ACTIVE`, a very low but not zero linear and angular damping, and a low sleeping threshold. If it slides without rotating, the surface friction is too low (it lives in the `.bisurf`, below); if it vibrates or never stops, raise the damping. This tuning was seen in game on a rolling stone body and is not checked on `P:\`.

## Moving a body

| Call | Does | Source |
|---|---|---|
| `dBodyApplyImpulse(body, impulse)` | Impulse at the centre | `P:\scripts\1_core\proto\enphysics.c:141` |
| `dBodyApplyImpulseAt(body, impulse, pos)` | Impulse at a world position; off centre gives roll | `P:\scripts\1_core\proto\enphysics.c:136` |
| `dBodyApplyForce(body, force)` and `dBodyApplyForceAt(body, pos, force)` | Continuous force | `P:\scripts\1_core\proto\enphysics.c:146`, `:151` |
| `dBodyApplyTorqueImpulse(ent, torqueImpulse)` | Spin impulse | `P:\scripts\1_core\proto\enphysics.c:125` |
| `GetVelocity(ent)` and `SetVelocity(ent, vel)` | Linear velocity; global functions, not `dBody` calls | `P:\scripts\1_core\proto\enphysics.c:104`, `:111` |
| `dBodySetAngularVelocity(body, angvel)` | Rotation around x, y and z in rad/s, "not yaw/pitch/roll" | `P:\scripts\1_core\proto\enphysics.c:163` to `:165` |
| `dBodySetTargetMatrix(body, matrix, timeslice)` | Kinematic move to a transform | `P:\scripts\1_core\proto\enphysics.c:170` |
| `dBodyApplyTorque(body, torque)` | Continuous torque | `P:\scripts\1_core\proto\enphysics.c:153` |
| `dBodyGetAngularVelocity(body)` | Rotation speed, rad/s per axis | `P:\scripts\1_core\proto\enphysics.c:158` |
| `dBodyGetWorldTransform` and `dBodyGetDirectWorldTransform(body, out matrix[4])` | The body's transform | `P:\scripts\1_core\proto\enphysics.c:172`, `:173` |
| `dBodyGetKineticEnergy(body)` | Kinetic energy | `P:\scripts\1_core\proto\enphysics.c:175` |

The vanilla car push shows the pattern: `dBodyApplyImpulseAt(car, impulse, car.ModelToWorld(car.GetEnginePos()))` (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionpushcar.c:52`). The object push is in `contact.md`.

## A script body of your own

The shape for a custom entity with no native body (a sphere that rolls), built from the calls above. It is not a vanilla pattern; tune the numbers in game.

```c
PhysicsGeomDef geoms[] = {PhysicsGeomDef("", dGeomCreateSphere(0.5), "material/default", PhxInteractionLayers.DYNAMICITEM)};
if (dBodyIsSet(this)) dBodyDestroy(this);
dBodyCreateDynamicEx(this, vector.Zero, 80.0, geoms);
dBodySetInteractionLayer(this, PhxInteractionLayers.DYNAMICITEM);
dBodyActive(this, ActiveState.ALWAYS_ACTIVE);   // no sleep half way down a slope
dBodySetDamping(this, 0.05, 0.2);
dBodyEnableCCD(this, 0.4, 0.45);                // maxMotion a little under the radius
```

Created only on the server, players walk through it (`player-controller.md`), and other clients see it move only through whatever the engine replicates (`network-and-authority.md`). For an item, use `ThrowPhysically` instead (`drop-and-throw.md`).

## Friction and bounce

There is no setter for friction or restitution. Both come from the physics material named on each geometry (`MaterialName`, `P:\scripts\1_core\physics\physicsgeomdef.c:15`) and from the surface, which is defined in `CfgSurfaces` or in the object's `.bisurf` file (the `SurfaceInfo` header comment, `P:\scripts\3_game\surfaceinfo.c:4`). `SurfaceInfo` exposes roughness, dustness and penetrability but no friction (`GetRoughness`, `P:\scripts\3_game\surfaceinfo.c:28`).

A `.bisurf` `restitution` value does not turn into bounce on a dropped item: a `SmallStone` dropped from 5 m onto open field rebounds 0.02 to 10 mm (measured in game; not checked on `P:\`).

## Calls that do not exist

No function with a name on the left is declared or called anywhere in `P:\scripts`.

| Often assumed | Use instead |
|---|---|
| `dBodySetFriction`, `SetFriction`, `SetRestitution`, `SetBounciness`, `SetElasticity`, `SetBounce` | The geometry's material and the surface's `.bisurf` |
| `dBodySetGravity`, `SetGravityDir`, `GravityFactor` (a gravity vector per body) | `dBodyEnableGravity(ent, bool)`, or the global `dSetGravity(worldEntity, g)` (`P:\scripts\1_core\proto\enphysics.c:17`) |
| `dBodySetVelocity`, `dBodyGetVelocity` | `SetVelocity` and `GetVelocity`; for the velocity at one point of a body, `dBodyGetVelocityAt(body, globalpos)` (`P:\scripts\1_core\proto\enphysics.c:177`) |
| `dBodyApplyAngularImpulse` | `dBodyApplyTorqueImpulse` |
| `AddForce` | `dBodyApplyForce` |
| `SetMaxLinearVelocity`, `SetMaxAngularVelocity` | Clamp the velocity yourself each tick |
| `PhxRaycast...` | The `Bullet` casts on `DayZPhysics` (`layers-and-raycasts.md`) |

Two more that are often assumed: an `EOnSimulate` override on `CarScript` (there is none in `carscript.c` or `transport.c`; car physics is native and script calls the control setters, while `BoatScript` does override it, `P:\scripts\4_world\entities\vehicles\boatscript.c:393`), and a vanilla script call to `CreateDynamicPhysics` (declared at `P:\scripts\3_game\entities\object.c:456` and never called).

## Debugging a body

- Count and list the world's dynamic bodies with `dGetNumDynamicBodies(worldEnt)` and `dGetDynamicBody(worldEnt, index)` (`P:\scripts\1_core\proto\enphysics.c:9` to `:10`).
- Draw a shape where you think the body is: `Shape.CreateSphere(color, flags, origin, radius)` (`P:\scripts\1_core\proto\endebug.c:170`), with `ShapeFlags.ONCE` for a shape redrawn each frame (`:132`). Do not keep a pointer to a `ONCE` shape.
- The body state queries (`dBodyIsSet`, `dBodyIsDynamic`, `dBodyIsActive`) are in `drop-and-throw.md`.
