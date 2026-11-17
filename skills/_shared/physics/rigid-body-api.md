# Rigid bodies from script

Covers creating, waking, moving and removing a physics body from Enforce Script, where friction and bounce come from, the calls that do not exist, and why a script body fails on an item that already has a native one.

For an item that only has to fall or be thrown, use the native path in `drop-and-throw.md`. Every signature, the joints and the worked recipes are in `skills/dayz-physics-engine/references/engine-deep-dive.md`.

## Two APIs, one engine

- The global functions `dBody...`, `dGeom...` and `dJoint...` take an entity and are what vanilla gameplay code uses (`dBodyIsSet`, `P:\scripts\1_core\proto\enphysics.c:57`).
- The `Physics` class wraps the same engine as methods on `obj.GetPhysics()` and adds a few extras: `ClearForces`, `GetTotalForce`, `GetTotalTorque` and `SetResponseIndex` (`P:\scripts\1_core\physics\physics.c:106-115`), and the constants `KMH2MS`, `MS2KMH`, `STANDARD_GRAVITY` and `VGravity` (`:18-21`).

## Creating and removing a body

| Call | Does | Source |
|---|---|---|
| `dBodyCreateStaticEx(ent, geoms)` | Static body from your own geometries | `P:\scripts\1_core\proto\enphysics.c:38` |
| `dBodyCreateGhostEx(ent, geoms)` | Ghost body from your own geometries (vanilla does not say more about what a ghost does) | `P:\scripts\1_core\proto\enphysics.c:39` |
| `dBodyCreateDynamicEx(ent, centerOfMass, mass, geoms)` | Dynamic body from your own geometries | `P:\scripts\1_core\proto\enphysics.c:51` |
| `Physics.CreateDynamic(ent, mass, layerMask)` | Dynamic body "from geometry embedded in attached VObject", that is from the model; false when the model has none | `P:\scripts\1_core\physics\physics.c:184-189` |
| `dBodyDestroy(ent)` | Removes the body | `P:\scripts\1_core\proto\enphysics.c:54` |

- A geometry is a `PhysicsGeomDef(name, geom, materialName, layerMask)` (`P:\scripts\1_core\physics\physicsgeomdef.c:18`). The shapes are `dGeomCreateBox`, `dGeomCreateSphere`, `dGeomCreateCapsule` and `dGeomCreateCylinder` (`P:\scripts\1_core\proto\enphysics.c:186` to `:195`).
- Always remove the old body before creating a new one: `if (dBodyIsSet(this)) dBodyDestroy(this);`. The vanilla test entity does this in its destructor (`dBodyDestroy`, `P:\scripts\2_gamelib\entities\scriptmodel.c:57-58`).
- `dBodyCreateStatic` and `dBodyCreateDynamic` (no `Ex`) appear only inside `#ifdef GAME_TEMPLATE` code (`P:\scripts\2_gamelib\entities\scriptmodel.c:31` and `:35`) and are not declared for DayZ.

**A script body does not attach to a vanilla inventory item.** Measured in game (source pack test mod BenchRE, DayZDiag 1.29, 2026-08-26; not checkable on `P:\`): `Physics.CreateDynamic`, `CreateDynamicEx` and `CreateStaticEx` returned a false value on 7 of 7 tries on `SmallStone` and `WoodenStick`, while `ThrowPhysically` worked on the same items. Items already have a native body. A script body needs a host entity with no physics of its own.

## State, sleep and fast bodies

| Call | Does | Source |
|---|---|---|
| `dBodyActive(ent, ActiveState)` | Wake, sleep, or `ALWAYS_ACTIVE` (never sleeps) | `P:\scripts\1_core\proto\enphysics.c:64`; enum at `P:\scripts\1_core\physics\activestate.c:9` |
| `dBodyDynamic(ent, bool)` | Switch between dynamic and static | `P:\scripts\1_core\proto\enphysics.c:65` |
| `dBodyEnableGravity(ent, bool)` | Gravity on or off; there is no gravity vector per body | `P:\scripts\1_core\proto\enphysics.c:69` |
| `dBodySetDamping(ent, linear, angular)` | Damping | `P:\scripts\1_core\proto\enphysics.c:70` |
| `dBodySetSleepingTreshold(body, linear, angular)` | When the body may fall asleep | `P:\scripts\1_core\proto\enphysics.c:71` |
| `dBodySetLinearFactor(body, linearFactor)` | Scales all impulses, velocities and forces per axis; "Zero any axis if you want to do 2D physics" | `P:\scripts\1_core\proto\enphysics.c:84-87` |
| `dBodyEnableCCD(body, maxMotion, sphereCastRadius)` | Continuous collision detection; see "Fast bodies" in `drop-and-throw.md` | `P:\scripts\1_core\proto\enphysics.c:83` |

- An impulse on a sleeping body is lost. Wake it first: `dBodyActive(ent, ActiveState.ACTIVE)` then `dBodyDynamic(ent, true)`.
- For a body that must keep rolling, use `ALWAYS_ACTIVE`, a very low but not zero linear and angular damping, and a low sleeping threshold. If it slides without rotating, the surface friction is too low (it lives in the `.bisurf`, below); if it vibrates or never stops, raise the damping. (Source pack lesson LL-014, from its rolling stone project.)

## Moving a body

| Call | Does | Source |
|---|---|---|
| `dBodyApplyImpulse(body, impulse)` | Impulse at the centre | `P:\scripts\1_core\proto\enphysics.c:141` |
| `dBodyApplyImpulseAt(body, impulse, pos)` | Impulse at a world position; off centre gives roll | `P:\scripts\1_core\proto\enphysics.c:136` |
| `dBodyApplyForce(body, force)` and `dBodyApplyForceAt(body, pos, force)` | Continuous force | `P:\scripts\1_core\proto\enphysics.c:146`, `:151` |
| `dBodyApplyTorqueImpulse(ent, torqueImpulse)` | Spin impulse | `P:\scripts\1_core\proto\enphysics.c:125` |
| `GetVelocity(ent)` and `SetVelocity(ent, vel)` | Linear velocity; global functions, not `dBody` calls | `P:\scripts\1_core\proto\enphysics.c:104`, `:111` |
| `dBodySetAngularVelocity(body, angvel)` | Rotation around x, y and z in rad/s, "not yaw/pitch/roll" | `P:\scripts\1_core\proto\enphysics.c:163-165` |
| `dBodySetTargetMatrix(body, matrix, timeslice)` | Kinematic move to a transform | `P:\scripts\1_core\proto\enphysics.c:170` |

The vanilla car push shows the pattern: `dBodyApplyImpulseAt(car, impulse, car.ModelToWorld(car.GetEnginePos()))` (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionpushcar.c:52`). The object push is in `contact.md`.

## Friction and bounce

There is no setter for friction or restitution. Both come from the physics material named on each geometry (`MaterialName`, `P:\scripts\1_core\physics\physicsgeomdef.c:15`) and from the surface, which is defined in `CfgSurfaces` or in the object's `.bisurf` file (the `SurfaceInfo` header comment, `P:\scripts\3_game\surfaceinfo.c:4`). `SurfaceInfo` exposes roughness, dustness and penetrability but no friction (`GetRoughness`, `P:\scripts\3_game\surfaceinfo.c:28`).

Measured in game (BenchRE, DayZDiag 1.29; not checkable on `P:\`): a `.bisurf` `restitution` value did not turn into bounce on a dropped item. A `SmallStone` dropped from 5 m onto open field rebounded 0.02 to 10 mm.

## Calls that do not exist

Each name on the left has 0 matches in `P:\scripts`.

| Often assumed | Use instead |
|---|---|
| `dBodySetFriction`, `SetRestitution`, `SetBounciness` | The geometry's material and the surface's `.bisurf` |
| `dBodySetGravity` (a gravity vector per body) | `dBodyEnableGravity(ent, bool)`, or the global `dSetGravity(worldEntity, g)` (`P:\scripts\1_core\proto\enphysics.c:17`) |
| `dBodySetVelocity`, `dBodyGetVelocity` | `SetVelocity` and `GetVelocity` |
| `dBodyApplyAngularImpulse` | `dBodyApplyTorqueImpulse` |
| `AddForce` | `dBodyApplyForce` |
| `SetMaxLinearVelocity` | Clamp the velocity yourself each tick |

## Debugging a body

- Count and list the world's dynamic bodies with `dGetNumDynamicBodies(worldEnt)` and `dGetDynamicBody(worldEnt, index)` (`P:\scripts\1_core\proto\enphysics.c:9-10`).
- Draw a shape where you think the body is: `Shape.CreateSphere(color, flags, origin, radius)` (`P:\scripts\1_core\proto\endebug.c:169`), with `ShapeFlags.ONCE` for a shape redrawn each frame (`:132`). Do not keep a pointer to a `ONCE` shape.
- The body state queries (`dBodyIsSet`, `dBodyIsDynamic`, `dBodyIsActive`) are in `drop-and-throw.md`.
