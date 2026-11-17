---
name: dayz-physics-engine
description: "Reference for DayZ engine physics in Enforce Script: the dBody rigid body API, collision layers, raycasts, EOnContact and TransportHit damage, thrown and rolling objects, the player controller, lift platforms, ragdoll and .ragdoll files, fall damage, PhysicsSetSimpleDeath, and moving physics work off the server. Use when a player walks through an object, an action or the cursor does not appear on it, a thrown or rolling object misbehaves, a mod needs contact damage or a ragdoll, or someone asks how to reduce server physics load (Spanish trigger: física DayZ). Not for vehicle authoring or flight, which have their own skills."
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# DayZ engine physics (Enforce Script)

Follow `skills/_shared/dayz-conventions.md`. This skill is reference only; it runs no scripts, so there is no preflight gate. The short, symptom-first version of this material for `dayz-physics-specialist` is the physics pack, `skills/_shared/physics/`; this skill holds the full depth.

How to read the citations:

- `P:\...:line` is the vanilla file unpacked on `P:\` (a 1.30 build), opened to confirm the line.
- `1.29:<path>:<line>` is a line number in the 1.29 scripts. They are not on `P:\`, so these were not re-checked; use them only to find the same code in an older build.
- "Measured" marks an in-game result from a test mod. It names the build and what was measured, and can't be checked on `P:\`. `[EXACT]`, `[INFERRED]`, `[DESIGN]` and `[UNVERIFIED]` say how firm a line is.

When something that sounds common is missing here, check "What does not exist" before assuming it exists.

## What to read

The body covers the working set. Open a reference only when the task needs that depth.

| Question | Read |
|---|---|
| Full `dBody`, `dGeom` and `dJoint` signatures, the raycast families and who uses which, surfaces, the drop and throw lifecycle | `references/engine-deep-dive.md` |
| Why and how vehicles replicate, `CarScript` damage by momentum, `Pawn` and `TransportOwnerState`, the push action | `references/transport-netsync.md` |
| The damage pipeline, the `EEHitBy` chain, the `RegisterTransportHit` flow line by line, hit zones, what armor really does | `references/damage-and-transporthit.md` |
| 1.30: `.ragdoll` and `RagdollDef`, `PhysicsSetSimpleDeath`, waking while falling, the fall damage `CurveExp` | `references/ragdoll-and-fall-damage.md` |

## The 11 engine truths

These prevent the classic bugs.

1. **A body only collides where it exists.** The player capsule (the character controller, CCT) is simulated on the client (its calls, `PhysicsIsFalling` to `PhysicsIsRagdoll`, are at `P:\scripts\3_game\human.c:1426-1452`; `1.29:3_game\human.c:1397-1418`). A rigid body created only on the server can never block a player, because the client's controller has nothing to collide with. This is architectural; no layer mask fixes it.
2. **The action cursor sees View Geometry, not physics.** Action targeting calls `RaycastRVProxy` (`P:\scripts\4_world\classes\useractionscomponent\actiontargets.c:255`; `1.29:4_world\classes\useractionscomponent\actiontargets.c:214-219`), whose parameters default to `ObjIntersectView` (`P:\scripts\3_game\global\dayzphysics.c:88`). No View Geometry LOD in the `.p3d` means no action and no admin tool selection, whatever physics body exists. Since 1.30 a liquid surface with no object is also scored as a target, at utility 0.01 (the `LIQUID_NONE` test, `P:\scripts\4_world\classes\useractionscomponent\actiontargets.c:532-534`); the `ActionTarget` constructor takes `surfaceName` (`:125`).
   - Qualification (read in the source, not measured): at a camera pitch of -45 degrees or lower, targeting also takes the objects inside a 30 degree, 3 m cone (`GetEntitiesInCone`, `P:\scripts\4_world\classes\useractionscomponent\actiontargets.c:324-325`; `c_MaxTargetDistance` and `c_ConeAngle` at `:841-843`) and scores them by their distance to the cursor ray (`DistSqrPoint2Line`, `:528-529`), with no hit on them needed. So an item on the ground can become a target without any View Geometry hit. Picking an item up proves nothing about its collision (the dayz-mcp-verify skill has that case).
3. **`dSetInteractionLayer` is global.** It edits the world's layer to layer interaction matrix (`P:\scripts\1_core\physics\physicsworld.c:14-21`, the `SetInteractionLayer` doc); the first parameter only finds the world. To stop two specific entities colliding, use the pair block instead: `dBlock b = dBodyCollisionBlock(entA, entB);` and later `dBodyRemoveBlock(world, b);` (`P:\scripts\1_core\proto\enphysics.c:116-117`).
4. **Friction and restitution are material strings, not setters.** They come from the physics material given to each geometry (`PhysicsGeomDef.MaterialName`, for example `"material/default"`, `P:\scripts\1_core\physics\physicsgeomdef.c:15`) and from surface definitions (`.bisurf` files and `CfgSurfaces`). There is no `dBodySetFriction` style call (0 matches in `P:\scripts`). Measured in game (DayZDiag 1.29, 2026-08-26): `.bisurf` `restitution` does not turn into bounce on the native item path. A SmallStone dropped from 5 m onto open field rebounds 0.02 to 10 mm (apparent e = 0.009 to 0.046, n=6).
5. **`Transport` replicates because it is a `Pawn`.** `Transport extends Pawn` (`P:\scripts\3_game\vehicles\transport.c:66`), with a continuous `TransportOwnerState` of world transform, linear velocity and angular velocity (`:11-30`) sent to every proxy (`PawnOwnerState`, `P:\scripts\3_game\entities\pawn.c:20-25`). `ItemBase` is not a `Pawn`: clients get only occasional entity snapshots and never velocities. A free dynamic body on an `ItemBase` looks synced only at low latency or in local tests.
6. **The native throw path runs on the server and on the owner client.** `HandActionThrow` checks `GetInstanceType() != DayZPlayerInstanceType.INSTANCETYPE_REMOTE` before `item.ThrowPhysically(player, throwEvent.GetForce())` (`P:\scripts\3_game\systems\inventory\hand_actions.c:77-81`). That is why a thrown item collides for the thrower. Whether remote clients get a local body is not visible in script; treat collision for third parties as unverified until tested in game.
7. **Drop and throw physics is temporary by design.** It has a lifetime: `StopItemDynamicPhysics()` ends it with `SetDynamicPhysicsLifeTime(0.01)` (`P:\scripts\4_world\entities\itembase.c:4530-4534`). An object that must roll for a long time has to renew or extend the lifetime, or not depend on the drop path. Measured in game (DayZDiag 1.29, 2026-08-26): the default lifetime is exactly 15 s (n=2; `dBodyIsDynamic` polled at 4 Hz flips at t=15.00), and `SetDynamicPhysicsLifeTime(3600)` is honored (still dynamic past a 300 s watchdog).
8. **A player's `EOnContact` reacts only to `Transport`.** `DayZPlayerImplement.EOnContact` casts `Transport.Cast(other)` and ignores everything else (`P:\scripts\4_world\entities\dayzplayerimplement.c:3958-3974`; `1.29:4_world\entities\dayzplayerimplement.c:3822-3836`). A custom `ItemBase` that should hurt players must detect the contact itself and call `target.ProcessDirectDamage(...)` from its own `EOnContact`.
9. **Script impulses push corpses, not living players.** Vanilla applies `dBodyApplyImpulse` to the victim only when `IsDamageDestroyed()` is true, that is on a ragdoll (`P:\scripts\3_game\entities\entityai.c:4158-4164`). A living player is moved by the contact solver itself (both bodies present, layers interacting), not by script.
10. **Config driven animated geometry on a building is not a mover.** Measured in game, DayZDiag 1.29.163709 `[EXACT]`: a standing player stays suspended while the piece descends; a moving player rides up but not down (they stay up, can walk a few metres on nothing, then fall); a parked car is clipped through by the rising piece; a running car rises a little and drops. Any elevator or lift platform needs a script layer that carries the rider. On the way down the client seems to keep the old collision for a while (a hypothesis, not measured).
11. **A platform that is a separate entity does carry riders.** Measured in game, DayZDiag 1.29.163709, one client on localhost `[EXACT]`: a `House` whose config inherits `HouseNoDestruct` with `animPhysDetachSpeed=100`, moved with `SetPosition` every frame on the server and on each client from the same clock (the server re-syncs the time every 0.25 s, the client extrapolates), lifted a standing player 8.9 m in 15 s (peak 0.93 m/s) without touching the player's position: within 5 cm on the server and 7.9 cm on the client, the client error being one frame of lag (correlation 0.89 with speed times frame time). The player must be linked (`PhysicsGetLinkedEntity() == platform`, `P:\scripts\3_game\human.c:1434`); after a teleport they need one native step before they link.
    - **Walking and jumping on it** (same platform, build and setup; four 8.9 m trips played by hand; the player's position logged at 20 Hz while the platform moved and 2 Hz while it stood: 1,448 samples on the server, 1,369 on the client) `[EXACT]`:
      - *Walking during the travel keeps the link.* `link=1` in every sample until the player stepped off onto the deck at the end, and no slide in any sample. On each of the three trips walked, 96.0 to 97.8 % of the server samples and 98.4 to 99.6 % of the client samples stayed within 8 cm of the face (the descent counted without its two jumps).
      - *A jump keeps the link and is relative to the platform.* The two jumps, both on the way down, spent 0.42 to 0.47 s in the air with a peak 0.30 to 0.32 m above the face, `link=1` throughout, and landed on the platform. That is close to the vanilla jump on still ground: `StartCommand_Fall(2.6)` (`P:\scripts\4_world\entities\dayzplayerimplementjumpclimb.c:97`) starts the fall at 2.6 m/s up (`StartCommand_Fall(float pYVelocity)`, `P:\scripts\3_game\human.c:1501`), a 0.345 m, 0.53 s arc by ballistics. The run does not tell whether the link carries the player in the air or the take-off inherits the platform's velocity: on these two jumps the two differ by about 2 cm at most, below what the trace resolves. It does rule out a jump that leaves the player at 2.6 m/s up in the world, neither carried nor inheriting: by the same ballistics its peak would be about 0.5 to 0.6 m above the face, which was descending at 0.60 to 0.83 m/s. No jump was made going up.
      - *Walking aboard links on its own.* A player who walked onto the stopped platform was linked with no preparatory step, about 8 s before it started; that step is only needed after a teleport. No sample read a fall when the player stepped off at the bottom (0.35 m down to the floor, logged at 2 Hz, so a drop that short can fall between two samples) or onto the deck at the top in about the last half second of the travel, with the platform within 3 cm of it (logged at 20 Hz).
      - *Short spikes.* The player read up to 22 cm off the face on the server and 12.6 cm on the client for one sample (up to three in a row on the server), and was back within 5 cm at the next. The offset trails the travel (above the face going down, below it going up) except in one client sample. On the client the spikes follow long frames (correlation about 0.7 with speed times frame time; 53 ms frames at the spikes, 8 ms elsewhere); on the server the correlation is 0.31 and the cause is open.
      - Not measured: a jump while the platform rises, a vehicle with a driver aboard, the latency of a second client on another machine.
    - **Vehicles on that platform.** Asleep (`dBodyActive` with `INACTIVE`) plus `SetPosition` plus `Transport.Synchronize()`: the server carries them but the client receives nothing until they wake. Do not use. Awake only (`ALWAYS_ACTIVE`): a sedan rides well, but a `CarScript` helicopter with its own flight model bounces up to 24 cm and slides 31 cm. Awake with `SetVelocity` set to the platform velocity plus 4 times the position error, every frame: the sedan (with and without wheels) and the helicopter ride within 4.6 cm on the server and 11.5 cm on the client, and stop exactly when released.
    - **The frame hook.** `EOnFrame` never reaches a `House` instance, even with `SetEventMask(EntityEvent.FRAME)` (measured `fe=0`). The `GetGame().GetUpdateQueue(CALL_CATEGORY_GAMEPLAY)` invoker runs every frame on server and client (`P:\scripts\3_game\dayzgame.c:3081`).
    - **A script can walk a client controlled player only with the overrides on both sides, every move.** In 1.29 multiplayer with reconciliation, `OverrideMovementSpeed` and `OverrideMovementAngle` (`P:\scripts\3_game\human.c:253` and `:256`; `1.29:3_game\human.c:234-237`) moved the player 0.24 to 0.40 m in 1.5 s when set on the client only, and 0.00 m when also set once on the server by RPC. What walks it (measured on DayZDiag 1.29, one client on localhost; this is how the dayz-mcp `player_move` tool works): the owner sets both overrides `ENABLED` on every command tick and sends a `ScriptInputUserData` request; the server applies the same two overrides `ENABLED` in every `ConsumeMove` after `super` and in its `CommandHandler`, then `DISABLED` at the end. Owner and server walked 0.76 m per 0.5 s (about 1.52 m/s) and stopped at the same position. Script fields added to `PlayerBaseMove` never reached the server.
    - **A Roadway face of another model across the travel stops the ride down** (measured in game on an elevator mod, DayZDiag 1.29.163709, 2026-10-02 and 03) `[EXACT]`: an elevator cabin of this kind (a `HouseNoDestruct` moved with `SetPosition` on the update queue) carried a player up through its stops but not down. Going down, it left them standing at the stop's floor height, 18.59 or 12.78 m, and went on without them. The dayz-mcp `player_trace` tool read the building's interior model as the floor, no linked entity and no fall. That model's collision slabs had the shaft cut out, but its Roadway LOD did not: it had 26 Roadway triangles at 12.78 and 16 at 18.59 inside the shaft's footprint, the faces the rising cabin had carried the player through. With the shaft cut out of that Roadway too (the only change in that build: that model, and in it only those Roadway polygons), the player rode down 2, 1, 0, and on a later build a 2 to 0 ride stayed linked to the cabin in all 1,033 samples, none falling. So a character stands on a Roadway face where no Geometry is, and no `RaycastRV` probe can target it: `ObjIntersect` offers Fire, View, Geom, IFire and None, not Roadway (`P:\scripts\3_game\constants.c:31-38`). Before shipping a lift, cabin or sliding piece, check offline that no Roadway face of any other model lies in the volume its collision sweeps (the piece's own Roadway moves with it: the cabin has one, so leave the cabin out of the check). In this case an offline check that swept the cabin's Geometry, shrunk 1 cm, from stop 0 to stop 2 failed the old models on 25 faces and passed the fixed ones with 0. Not measured: a `RayCastBullet` with `PhxInteractionLayers.ROADWAY` against a model's Roadway LOD; one cabin in one building.

## API quick map

### Create and destroy (`P:\scripts\1_core\proto\enphysics.c`)

```c
proto bool dBodyCreateStaticEx (notnull IEntity ent, PhysicsGeomDef geoms[]);                        // :38
proto bool dBodyCreateGhostEx  (notnull IEntity ent, PhysicsGeomDef geoms[]);                        // :39
proto bool dBodyCreateDynamicEx(notnull IEntity ent, vector centerOfMass, float mass, PhysicsGeomDef geoms[]); // :51
proto native void dBodyDestroy(notnull IEntity ent);                                                 // :54
proto native bool dBodyIsSet(notnull IEntity ent);                                                   // :57
```

- `PhysicsGeomDef(string name, dGeom geom, string materialName, int layerMask)`, with public `Frame[4]` and `ParentNode` (`P:\scripts\1_core\physics\physicsgeomdef.c:9-26`).
- Geometries: `dGeomCreateBox(size)` (`P:\scripts\1_core\proto\enphysics.c:186`), `dGeomCreateSphere(radius)` (`:189`), `dGeomCreateCapsule` (`:192`), `dGeomCreateCylinder` (`:195`), `dGeomDestroy` (`:198`).
- `dBodyCreateStatic` and `dBodyCreateDynamic` (no `Ex`) exist only under `#ifdef GAME_TEMPLATE` (`P:\scripts\2_gamelib\entities\scriptmodel.c:31` and `:35`); they do not compile in DayZ. The wrapper `Physics.CreateDynamic(ent, mass, layerMask)` builds the geometry from the entity's `.p3d` (`P:\scripts\1_core\physics\physics.c:189`).
- Recreate pattern: always `if (dBodyIsSet(this)) dBodyDestroy(this);` before creating again.

### State, damping, sleep, CCD (`P:\scripts\1_core\proto\enphysics.c`)

```c
dBodySetInteractionLayer(ent, mask)            // :59  (per body)   dBodyGetInteractionLayer :60
dBodyActive(ent, ActiveState.X)                // :64  INACTIVE | ACTIVE | ALWAYS_ACTIVE
dBodyDynamic(ent, bool)                        // :65
dBodyEnableGravity(ent, bool)                  // :69  bool only, no vector
dBodySetDamping(ent, linear, angular)          // :70
dBodySetSleepingTreshold(body, lin, ang)       // :71
dBodyEnableCCD(body, maxMotion, castRadius)    // :83  (-1 disables) against tunneling
dBodySetLinearFactor(body, vector)             // :87  zero an axis for 2D physics
dBodyGetMass / dBodySetMass                    // :122-123
```

`enum ActiveState { INACTIVE, ACTIVE, ALWAYS_ACTIVE }` is at `P:\scripts\1_core\physics\activestate.c:9-17`. `ALWAYS_ACTIVE` stops a body falling asleep half way down a slope.

### Impulses, forces, velocities (`P:\scripts\1_core\proto\enphysics.c`)

```c
dBodyApplyImpulse(body, impulse)               // :141
dBodyApplyImpulseAt(body, impulse, worldPos)   // :136  off centre gives natural torque and roll
dBodyApplyForce / dBodyApplyForceAt            // :146 / :151
dBodyApplyTorque / dBodyApplyTorqueImpulse     // :153 / :125
GetVelocity(ent) / SetVelocity(ent, v)         // :104 / :111  global functions (work on Man too)
dBodyGetAngularVelocity / dBodySetAngularVelocity  // :158 / :165  rad/s per axis, not yaw/pitch/roll
dBodyGetVelocityAt(body, worldPos)             // :177
dBodySetTargetMatrix(body, matrix, timeslice)  // :170  kinematic move
dBodyGetKineticEnergy(body)                    // :175
```

Only on the `Physics` wrapper: `ClearForces`, `GetTotalForce`, `GetTotalTorque` and `SetResponseIndex` (`P:\scripts\1_core\physics\physics.c:106-115`); the constants `Physics.KMH2MS`, `STANDARD_GRAVITY` (9.81) and `VGravity` (`:18-21`).

### Interaction layers

`PhxInteractionLayers` (`P:\scripts\3_game\global\dayzphysics.c:1-43`), in bit order: NOCOLLISION, DEFAULT, BUILDING, CHARACTER, VEHICLE, DYNAMICITEM, DYNAMICITEM_NOCHAR, ROADWAY, VEHICLE_NOTERRAIN, CHARACTER_NO_GRAVITY, RAGDOLL_NO_CHARACTER (also named FIREGEOM), DOOR, RAGDOLL, WATERLAYER, TERRAIN, GHOST, WORLDBOUNDS, FENCE, AI, AI_NO_COLLISION, AI_COMPLEX, TINYCAPSULE, TRIGGER, TRIGGER_NOTERRAIN, ITEM_SMALL, ITEM_LARGE, CAMERA, TEMP.

The runtime query, as vanilla writes it (`dGetInteractionLayer`, `P:\scripts\3_game\vehicles\transport.c:787-788`):

```c
int layer = dBodyGetInteractionLayer(obj);
bool blocksPlayer = dGetInteractionLayer(this, PhxInteractionLayers.CHARACTER, layer);
```

Use the same query to log whether CHARACTER against DYNAMICITEM is active when debugging "walks through".

### Raycast and overlap families

`DayZPhysics` (`P:\scripts\3_game\global\dayzphysics.c:123-230`) has two separate worlds. Pick the right one.

| Family | Sees | Use for |
|---|---|---|
| `RaycastRV` (`P:\scripts\3_game\global\dayzphysics.c:199`) and `RaycastRVProxy` (`:208`) | The model LODs, chosen by `ObjIntersect`: Fire (0), View (1), Geom (2), IFire (3), None (4) (`:66-71`) | Cursor and action targeting, hit surfaces, melee aim |
| `RayCastBullet` (`P:\scripts\3_game\global\dayzphysics.c:211`), `SphereCastBullet` (`:213`) and the `OverlapBullet` calls (`:216-228`) | The Bullet physics world, filtered by `PhxInteractionLayers` | Physical line of sight, ground probes, area queries on bodies |

- `CollisionFlags` is FIRSTCONTACT, NEARESTCONTACT, ONLYSTATIC, ONLYDYNAMIC, ONLYWATER, ALLOBJECTS (`P:\scripts\1_core\proto\endebug.c:140-148`). Not checked on `P:\`: from 1.30.164289 the enum starts with `NONE = 0`, which moves every other value up by one. The copy on `P:\` has no `NONE`, so never pass these as numbers.
- Overlap callback: `CollisionOverlapCallback.OnContact(IEntity, Contact)` (`P:\scripts\3_game\global\dayzphysics.c:115-121`).
- The action cursor's ground fallback uses `RayCastBullet` with `ROADWAY|TERRAIN|WATERLAYER` (`P:\scripts\4_world\classes\useractionscomponent\actiontargets.c:383-384`; `1.29:4_world\classes\useractionscomponent\actiontargets.c:324-325`).

### Contacts

- `sealed class Contact` (`P:\scripts\1_core\physics\contact.c:9-50`): `Impulse` (`:21`), `Normal`, `Position`, `PenetrationDepth`, `RelativeVelocityBefore` and `RelativeVelocityAfter`, `GetNormalImpulse()` (`:47`).
- Receive it with `SetEventMask(EntityEvent.CONTACT)` and `override void EOnContact(IEntity other, Contact extra)` (`P:\scripts\1_core\proto\enentity.c:213`).
- Vanilla measures the size of an impact with `extra.RelativeVelocityBefore.Length()` (`P:\scripts\3_game\entities\inventoryitem.c:202`), ignores anything under 0.3, and skips repeats inside `SOUND_CONTACT_SKIP` (0.33 s, `:207`). It does not use `Impulse` for this.
- A vehicle's `OnContact` "Can be called very frequently in one frame", as vanilla warns above `BoatScript.OnContact` (`P:\scripts\4_world\entities\vehicles\boatscript.c:425`; `1.29:4_world\entities\vehicles\carscript.c:1453`). Buffer contacts and process them once per tick: vanilla caches the first contact in `Transport.OnContact` (`P:\scripts\3_game\vehicles\transport.c:315-343`) and consumes it in `EOnPostSimulate`.

### The native dynamic item path (drop and throw)

```c
// P:\scripts\3_game\entities\inventoryitem.c
proto native void EnableCollisionsWithCharacter(bool state);   // :21
proto native void ThrowPhysically(DayZPlayer player, vector force, bool collideWithCharacters = true); // :26
// P:\scripts\3_game\entities\object.c
proto native void CreateDynamicPhysics(int interactionLayers); // :456 (line 462 in 1.29); no vanilla script calls it
proto native void EnableDynamicCCD(bool state);                // :457 (line 463 in 1.29)
proto native void SetDynamicPhysicsLifeTime(float lifeTime);   // :458 (line 464 in 1.29)
```

Lifecycle:

- Throw: `HandActionThrow` (`P:\scripts\3_game\systems\inventory\hand_actions.c:62-88`), on the server and the owner.
- Inventory dump: `ThrowEntityFromInventory` calls `ThrowPhysically(null, force, false)` (`P:\scripts\4_world\static\miscgameplayfunctions.c:1297-1353`, the call at `:1345`).
- Admin spawn with gravity: `item.ThrowPhysically(null, "0 0 0")` on the server (`P:\scripts\4_world\plugins\pluginbase\plugindeveloper.c:430` and `:553`).
- Hook to set the body up again: `override void OnCreatePhysics()`, which calls `RefreshPhysics()` (`P:\scripts\4_world\entities\itembase.c:1150-1155`). The tent, fireplace, Hesco box, kit and battery charger override `RefreshPhysics` (for example `P:\scripts\4_world\entities\itembase\tentbase.c:162`).
- The `DYNAMICITEM` and `DYNAMICITEM_NOCHAR` pair maps to `collideWithCharacters` by its naming `[INFERRED]`; the assignment inside the engine is not visible in script.

### Player controller (`P:\scripts\3_game\human.c`)

- `PhysicsIsFalling` (`P:\scripts\3_game\human.c:1428`; the comment at `:1426-1427` adds "returns true if the ragdoll is moving greater than 1m/s"; `1.29:3_game\human.c:1397`).
- `PhysicsGetFloorEntity` (`P:\scripts\3_game\human.c:1431`; `1.29:3_game\human.c:1400`), `PhysicsGetLinkedEntity` (`:1434`), `PhysicsGetVelocity` (`:1441`), `PhysicsEnableGravity` (`:1443`), `PhysicsSetSolid` (`:1446`).
- `PhysicsSetSimpleDeath` (`P:\scripts\3_game\human.c:1449`, new in 1.30, under the comment "Old system for handling player death state, was previously handled by PhysicsSetRagdoll"), `PhysicsSetRagdoll` (`:1451`; `1.29:3_game\human.c:1418`), `PhysicsIsRagdoll` (`:1452`). Also `HumanCommandUnconscious.IsRagdoll` (`P:\scripts\3_game\human.c:647`).
- `CheckFreeSpace` (`P:\scripts\3_game\human.c:1381`), `CollisionMoveTest` (`:1387`), `LinkToLocalSpaceOf` (`:1391`).

**Lifting the player from a `HumanCommandScript` needs the controller's gravity off.** Measured in game, DayZDiag 1.30.164014 experimental, 2026-10-06, server and one client on one machine `[EXACT]`. A skateboard ride command integrated its own ollie (`dy = vy·dt − ½g·dt²` each tick, vy 2.69 m/s at take-off) and passed `dy` as the y of `PrePhys_SetTranslation`, which is local space (`P:\scripts\3_game\human.c:1313`). In `PostPhysUpdate` it compared `PostPhys_GetPosition` with the integrated height and, past 3 cm, pinned the height with `PostPhys_SetPosition` on every air tick (world space, `P:\scripts\3_game\human.c:1325-1327`).

- *Gravity on, the default:* the body did not rise. The first air tick ended 0.088 m under the integrated height on the server and on the owner client, which is that tick's whole 0.084 m step lost. 0.2 s into the flight, with the pin already on, the server read the body 1 cm under its take-off height, where the integration asked for about +0.34 m.
- *`Human.PhysicsEnableGravity(false)` from take-off to landing* (`P:\scripts\3_game\human.c:1443`), the only script change in the next build: the body followed the translation. The server never needed the pin (every air tick within 3 cm). On the owner client the root peaked at 0.996 and 1.001 times vy²/2g in the two landed flights, sampled at about 10 Hz; in the second one the client had switched to the pin after reading the body 0.079 m above the integration on its second air tick.
- *`PhysicsEnableGravity(true)` at the landing*, and in `OnDeactivate` for a ride that ends in the air: after the first landing the rider rolled down a slope again, 2.6 m of descent over the next 11 s.

Vanilla calls `PhysicsEnableGravity` once, with `true`, when a vehicle death's simulation ends (`P:\scripts\4_world\entities\dayzplayerimplement.c:32`), so a command that switches the gravity off owns switching it back on at every exit. Not measured: a remote observer, flights longer than the 0.6 s these lasted, and fall damage after a flight with the gravity off.

**`PhysicsIsFalling(true)` is not a pure read.** Measured in game, DayZDiag 1.30.164014 experimental, 2026-10-06, a later build of the same skateboard command `[EXACT]`. This command switches the gravity off at the pop, 0.1 s before the take-off, and then lifts the body with `PrePhys_SetTranslation(Vector(0, dy, z))`. In the earlier builds an airborne guard called `PhysicsIsFalling(true)` on every tick of the pop; this build skipped that call during the pop, and every take-off lost its first air tick: `PostPhys_GetPosition` read exactly that tick's `dy` under the integrated height (errors of -0.11 to -0.15 m), the body barely rose for about 0.1 s, and the apex reached 0.44 to 0.61 of vy²/2g, on a climb and on a downhill alike. Calling it again on the ticks of the pop, its result ignored, was the only take-off change between the build of run 1 and the build of runs 2 and 3 (the other suspect, an extra `PostPhys_GetPosition` read on every tick, was in both): in runs 2 and 3 the apex came to 1.00 of vy²/2g (0.70 m for 0.698 expected), with no correction. What `pValidate` does is not documented (`P:\scripts\3_game\human.c:1428`). A command that lifts the body with the gravity off keeps calling `PhysicsIsFalling(true)` on the ticks before the lift, or measures its first air tick.

### Joints

`dJointCreateHinge`, `Hinge2`, `Slider`, `BallSocket`, `Fixed`, `ConeTwist`, `6DOF` and `6DOFSpring`, each ending in `bool block, float breakThreshold`, plus setters per type (`P:\scripts\1_core\proto\enphysics.c:212-270`). A joint that breaks raises `EOnJointBreak` (`P:\scripts\1_core\proto\enentity.c:207`).

### Surfaces

- `SurfaceInfo` (`P:\scripts\3_game\surfaceinfo.c:8-71`): `GetByName` and `GetByFile`, roughness, dustness, penetrability, `IsLiquid`, `IsSolid`, step and wheel particle ids.
- Detection on `CGame`: `GetSurface`, `SurfaceY`, `SurfaceGetType`, `SurfaceUnderObject`, `SurfaceGetNormal` (`P:\scripts\3_game\global\game.c:1169-1188`).
- Impact surface: `DayZPhysics.GetHitSurfaceAndLiquid` (`P:\scripts\3_game\global\dayzphysics.c:206`), used at `P:\scripts\3_game\entities\inventoryitem.c:170-175`.
- No friction getters; see truth 4. Water over water objects (river and stream pieces, a roadway `water_ext` face) is in `skills/_shared/physics/water-queries.md`.

## Recipes

**A. Custom dynamic sphere body (server side baseline)**

```c
PhysicsGeomDef geoms[] = {PhysicsGeomDef("", dGeomCreateSphere(0.5), "material/default",
    PhxInteractionLayers.DYNAMICITEM)};
dBodyCreateDynamicEx(this, GetCenterOfMassOffset(), 80.0, geoms);
dBodySetInteractionLayer(this, PhxInteractionLayers.DYNAMICITEM);
dBodyActive(this, ActiveState.ALWAYS_ACTIVE);     // no sleep half way down a slope
dBodySetDamping(this, 0.05, 0.2);
dBodyEnableCCD(this, 0.4, 0.45);                  // about diameter*0.8, inner radius
```

Remember truth 1: created only on the server, players walk through it. And "Script bodies on vanilla items" below: this fails on an entity that already has a native body.

**B. Native path (recommended for items that must block or hit players)**

```c
// run on the server and the owner client (the guard at hand_actions.c:77):
item.ThrowPhysically(null, impulse, true);   // true: collides with CHARACTER
item.EnableDynamicCCD(true);
item.SetDynamicPhysicsLifeTime(3600);        // renew for long rolling; confirm in game
```

The model needs a Geometry LOD (collision), a View Geometry LOD (cursor, truth 2) and a Fire Geometry LOD (bullets). Check them with `/dayz-p3d-audit`.

**C. Contact damage to players (vehicle parity, from the item's side)**

```c
void MyItem() { SetEventMask(EntityEvent.CONTACT); }
override void EOnContact(IEntity other, Contact extra)
{
    if (!g_Game.IsServer()) return;
    EntityAI target = EntityAI.Cast(other);
    if (target && target.IsAlive())
    {
        float speed = GetVelocity(this).Length();          // m/s
        if (speed > 0.5 && m_CanHit)                        // guard against many contacts per tick
        {
            m_CanHit = false;                               // reset by timer or in the target's EEHitBy
            target.ProcessDirectDamage(DamageType.CUSTOM, this, "", "TransportHit", "0 0 0", speed);
        }
    }
}
```

- `damageCoef` is the velocity: the damage is the base damage of the ammo `TransportHit` times the coefficient (`RegisterTransportHit`, `P:\scripts\3_game\entities\entityai.c:4134`; the Motorbike branch at `:4166-4183`; `1.29:3_game\entities\entityai.c:4089-4156`). The ammo class is `TransportHit` in `P:\DZ\weapons\melee\config.cpp:52-72`: `hitAnimation=1`, `Health` damage 1, `Blood` 0, `Shock` 0. So 10 m/s deals 10 health before armor.
- Vanilla resets its one hit guard in the victim's `EEHitBy` (`m_TransportHitRegistered = false`, `P:\scripts\4_world\entities\dayzplayerimplement.c:1567`; `1.29:4_world\entities\dayzplayerimplement.c:1551`).
- Corpse launch only: `impulse = 40 * velocity; impulse[1] = 60; dBodyApplyImpulse(victim, impulse);` behind `IsDamageDestroyed()` (truth 9).
- Full pipeline: `references/damage-and-transporthit.md`.

**D. Push action (vanilla parity)**

`ActionPushCar` applies `dBodyApplyImpulseAt(car, impulse, car.ModelToWorld(car.GetEnginePos()))` (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionpushcar.c:52`). An application point off centre gives natural roll. The stamina cost is one line, since `EStaminaModifiers.PUSH_CAR` already exists (`P:\scripts\3_game\enums\estaminamodifiers.c:13`).

**E. Wake a sleeping body before an impulse**

`dBodyActive(ent, ActiveState.ACTIVE); dBodyDynamic(ent, true);` then apply the impulse. An impulse on a sleeping body is lost.

## Debugging physics

- A visual overlay works in retail builds: `Shape.CreateSphere(0x88FF0000, ShapeFlags.TRANSP|ShapeFlags.NOZBUFFER, pos, r)` and `Shape.CreateLines(...)`, with `ShapeFlags.ONCE` for shapes drawn each frame (`P:\scripts\1_core\proto\endebug.c:125-169`). Never keep a pointer to a `ONCE` shape.
- Log the layer matrix at run time with the `dGetInteractionLayer` query above.
- Count the world's bodies: `dGetNumDynamicBodies(world)` and `dGetDynamicBody(world, i)` (`P:\scripts\1_core\proto\enphysics.c:9-10`).
- Fast iteration: the Diag executable with `-filePatching` reloads scripts without a PBO rebuild (no BattlEye, no signature checks). `/dayz-launch-test` starts the Diag server and client; the dayz-mod-workflow skill has the full loop.

## What does not exist

Checked: 0 matches in `P:\scripts` for each name on the left.

| API that sounds plausible | Reality |
|---|---|
| `dBodySetFriction`, `SetRestitution`, `SetBounciness` | A physics material string per geometry, and `.bisurf`, only |
| A gravity vector per body (`dBodySetGravity`) | Only `dBodyEnableGravity(ent, bool)` and the global `dSetGravity(world, g)` (`P:\scripts\1_core\proto\enphysics.c:17`) |
| `dBodySetVelocity`, `dBodyGetVelocity` | The global `SetVelocity` and `GetVelocity` (`P:\scripts\1_core\proto\enphysics.c:104` and `:111`) |
| `dBodyApplyAngularImpulse` | `dBodyApplyTorqueImpulse` (`P:\scripts\1_core\proto\enphysics.c:125`) |
| `AddForce` (Unity style) | `dBodyApplyForce` and `dBodyApplyForceAt` |
| A `SetMaxLinearVelocity` clamp | Clamp by hand each tick |
| `PhxRaycast...` | The physics world casts are the `Bullet` family in `DayZPhysics` |
| `EOnSimulate` on `CarScript` | Car physics is native; script only calls the control setters. (`BoatScript` does override `EOnSimulate`, `P:\scripts\4_world\entities\vehicles\boatscript.c:393`.) |
| A vanilla script call to `CreateDynamicPhysics` | Declared but never called from script, so there is no vanilla usage pattern |
| `Synchronize()` on `EntityAI` or `ItemBase` | `Transport` only (`P:\scripts\3_game\vehicles\transport.c:171-172`) |

## Offloading physics from the server

Gameplay physics cannot leave the authority; only cosmetic physics can. (Checked against `P:\`.)

- **No channel out of the process for work done each tick.** Vanilla scripts expose no native extension call (0 matches for `callExtension`, `LoadLibrary` or `DllImport` in `P:\scripts`). The only network exit is `RestApi`: asynchronous with a callback (`GET` at `P:\scripts\3_game\http\restapi.c:103`, `POST` at `:123`) or blocking the thread (`GET_now` at `:108`, `POST_now` at `:128`). Fine for slow work that tolerates latency; never for a physics step.
- **Owner prediction does not remove server work.** The authority consumes and replays the owner's move (`PawnMove`, `P:\scripts\3_game\entities\pawn.c:79-81`; `ConsumeMove`, `:270-274`), and a native comparison runs as well, with the more severe result winning (`CompareMove`, `:261-265`). So a script `CompareMove` that always returns `APPROVE` cannot suppress corrections. Vanilla cars follow this under `NetworkMoveStrategy.PHYSICS` (`IsServerOrOwner`, `P:\scripts\4_world\entities\vehicles\carscript.c:2590-2601`).
- **Cosmetic physics can run on each client at no server cost.** `ECE_LOCAL` creates an object on that machine only (`P:\scripts\3_game\ce\centraleconomy.c:25`); vanilla gives local objects collision with `ECE_LOCAL | ECE_CREATEPHYSICS` (`P:\scripts\5_mission\gui\scriptconsoleitemstab.c:696`). Whether a local object accepts a dynamic body is unverified.
- **Measure before optimizing.** `EnProfiler` profiles script only (`P:\scripts\1_core\proto\enprofiler.c:62-63`, the `-profile` launch parameter). For native cost, compare server CPU with and without the load on a capped server (the dayz-test-ingame skill's 1.30 notes, "Measuring server load"). Measured on 1.30 experimental: 50 server side dummy players sprinting did not show at 60 FPS and 100 did (the dayz-mcp-verify skill's 1.30 notes).

## `PhysicsSetRagdoll` on a live player (measured)

Measured in an in-game test with script logs and full telemetry. It replaces the earlier expectation that the call "probably does not simulate" on a live player. From 1.30 the ragdoll is no longer an opaque native blob: vanilla ships a `RagdollDef` in `P:\DZ\characters\bodies\human.ragdoll`. The notes below still apply; the data format, the Workbench editor and `PhysicsSetSimpleDeath` are in `references/ragdoll-and-fall-damage.md`.

- **The server does simulate it**, given: (1) `DisableSimulation(false)` before the toggle, as the death flow does (`P:\scripts\4_world\entities\dayzplayerimplement.c:735`); (2) waking first with `dBodyActive(p, ActiveState.ACTIVE)` and `dBodyDynamic(p, true)`; (3) `dBodyApplyImpulse(p, V * mass)`. `dBodyGetMass` returned the player's real mass (87.5 kg) and the impulse took on the first try, with no `SetVelocity` needed. The body slid 77.6 m at 4 to 6.7 m/s following the terrain, uphill included (very low effective friction).
- **The owner client does not.** The local avatar never ragdolls: it stays standing and controllable (movement is client authoritative), a total desync between server and owner. A live ragdoll works end to end only with custom position sync.
- Toggling `PhysicsSetRagdoll(false)` does not rubber band: the entity stays exactly where the body ended (position before equals position after, verified).
- **Get-up danger.** `StartCommand_Unconscious(0)` plus `WakeUp` at 0.5 s left the player, on the server, 40 m under the terrain, with a fall into the void, real unconsciousness and death. Vanilla's guard against waking too early is 2 s (`m_UnconsciousTime > 2`, `P:\scripts\4_world\entities\manbase\playerbase.c:3420`; `1.29:4_world\entities\manbase\playerbase.c:3184`). From 1.30 vanilla also refuses to wake a falling player: `if (false == PhysicsIsFalling(false))` (`P:\scripts\4_world\entities\manbase\playerbase.c:3423`) comes before `hcu.WakeUp(wakeUpStance)` (`:3431`). A custom 0.5 s wake path that skips these can still bury the body.

## Script bodies on vanilla items (measured)

Measured on a DayZDiag 1.29 server and client run, 2026-08-26. The raw logs are not in this repo.

- **`Physics.CreateDynamic`, `CreateDynamicEx` and `CreateStaticEx` return a false value on a vanilla `InventoryItem`** (SmallStone and WoodenStick spawned with `CreateObjectEx`): 7 of 7 attempts on the server. The native path on the same items works (`ThrowPhysically`, `SetDynamicPhysicsLifeTime`, `dBodyIsDynamic` read over 2,402 ticks). Items already have a native body and the `Create...Ex` family does not attach to them, which matches its 0 gameplay uses in vanilla. A host for a script body must have no physics of its own (not yet validated: a custom entity in the style of `P:\scripts\2_gamelib\entities\scriptmodel.c`).
- **`DayZPhysics.GetHitSurfaceAndLiquid` does not name terrain surfaces.** `RayCastBullet` over open field returns a valid hit position, but the call needs an `Object` and terrain is not one (6 of 6 probes came back with no name). For terrain use `CGame.SurfaceGetType(x, z, out type)` (`P:\scripts\3_game\global\game.c:1180`) or `SurfaceGetType3D` (`:1183`).
- **On a multiplayer client, `CreateObjectEx` without `ECE_LOCAL` returns null** (n=2). For local test geometry on a client add `ECE_LOCAL` (`P:\scripts\3_game\ce\centraleconomy.c:25`; the client pattern is at `P:\scripts\3_game\particles\particle.c:119`).

## Rolling bodies: damping and friction

- For rolling bodies, use a very low but non zero linear and angular damping and adjust the sleeping threshold. Do not minimize contact friction: it lives in the `.bisurf`. If the body slides without rotating, raise the friction; if it vibrates or does not stop, raise the damping.

## DayZ 1.30

What changes:

- The ragdoll is data driven. Vanilla ships a `RagdollDef` with 11 bones, capsules and one sphere, `flesh.bisurf` and joints (`P:\DZ\characters\bodies\human.ragdoll:1-202`). Workbench adds a ragdoll editor (1.30 experimental modding changelog).
- Death state: up to 1.29, `DayZPlayerImplement` called `PhysicsSetRagdoll(true)` (`1.29:4_world\entities\dayzplayerimplement.c:736`). From 1.30 the branch that does not start a death command calls `PhysicsSetSimpleDeath(true)` (`P:\scripts\4_world\entities\dayzplayerimplement.c:745`). `PhysicsSetRagdoll` and `PhysicsIsRagdoll` remain (`P:\scripts\3_game\human.c:1451-1452`).
- An unconscious ragdoll drops the vehicle re-attach: `if (hcu && hcu.IsRagdoll())` then `m_TransportCache = null` (`P:\scripts\4_world\entities\manbase\playerbase.c:3346-3350`).
- Fall damage is an exponential `CurveExp` with much lower height gates: health from 2 m, shock from 0 m, broken legs from 3 m. `Randomize` no longer rolls a lethal coefficient of 1.0 back down. Detail in `references/damage-and-transporthit.md` and `references/ragdoll-and-fall-damage.md`.
- The action cursor still uses View Geometry (`RaycastRVProxy` with `ObjIntersectView`). Liquid surfaces without an object are now targets (utility 0.01).
- Changelog only, no script counterpart: hiding the physics components of a static mesh no longer leaves a leftover collision at the origin.

What breaks:

- A `modded class DayZPlayerImplementFallDamage` that copies the 1.29 `Math.InverseLerp` thresholds: falls of 2.5 to 4 m now cause shock and can break legs in vanilla, and the copy silently restores the old curve.
- A custom unconscious wake that calls `hcu.WakeUp()` while `PhysicsIsFalling(false)` is true: vanilla now refuses, and skipping the guard can still bury the body (the 1.29 measurement above).
- Assuming the player ragdoll's collision and mass are native and can't be edited: a `.ragdoll` can now be authored (binding it to a character is covered by the dayz-characters skill).
- Assuming infected can ragdoll: `ragdoll =` in an infected's `enfanimsys` plus player death clips with the `Ragdoll` event did nothing in an in-game test on 1.30.164078. The ragdoll API is on `Human` only. The reference proposes a corpse swap instead, a design that has not been tested; see `references/ragdoll-and-fall-damage.md` section 1.

Migration checklist:

- [ ] If you override fall damage: port `CurveExp` and the 1.30 height constants; keep `if (pValue == 1) return pValue;` in `Randomize`.
- [ ] Custom humanoids: ship a `.ragdoll` next to the body; do not assume a `LoadRagdollFile` call exists in script (`[UNVERIFIED]`: no such call in `P:\scripts`).
- [ ] Custom unconscious wake: keep `m_UnconsciousTime > 2` and `PhysicsIsFalling(false) == false`.
- [ ] Action targeting over water: expect a surface target even with no object (`ActionTarget.GetSurfaceLiquidType`).
- [ ] Death path: `PhysicsSetSimpleDeath(true)` is the death branch without a ragdoll that script can see.

## Related skills and packs

- `skills/_shared/physics/`: the physics pack, with a symptom to cause table and who fixes what.
- `/dayz-p3d-audit`: checks the Geometry, View Geometry and Fire Geometry LODs that physics and the cursor need.
- `skills/_shared/enscript/patterns/physics_items.md`: making a spawned item physics active.
- Related skills, by name: enforce-script-reference (language rules, RPC and sync variables, config.cpp, action basics), dayz-model-pipeline (building the collision LODs), dayz-mod-workflow (the implementation protocol and the Diag fast loop), dayz-sound-system (impact and rolling audio driven from contact events), dayz-characters (binding a `.ragdoll`), dayz-vehicles, dayz-motorbikes and dayz-aviation (vehicle authoring and flight), and dayz-mod-dev (the entry point when the work has to end in a mod that builds, loads and ships: `config.cpp` and `CfgMods`, `requiredAddons`, the PBO and its signature, a boot on a local server, the Workshop).
