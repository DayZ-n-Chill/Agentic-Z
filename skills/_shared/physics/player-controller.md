# Players and physics

Covers the player's character controller: where it is simulated and what that means for collision, the calls script has on it, riding a moving platform, lifting the player from a command script, and walking a player from script. The ragdoll and fall damage are in `ragdoll-and-fall-damage.md`.

Results marked measured in game were seen on a running game and can't be checked on `P:\`; confirm them in game before a design depends on one.

## The controller is not a rigid body

- A player is moved by a character controller, driven through calls on `Human` (`class Human`, `P:\scripts\3_game\human.c:1359`), not by a body that `dBody` calls steer.
- The controller is simulated on the player's own client, so a body that exists only on the server never blocks a player: that client has nothing to collide with. No layer setting changes this. To block or carry a player, the object's collision must exist on the client too: a model's Geometry LOD (`collision-lods.md`), or the native throw path, which vanilla runs on the server and the owner client (`drop-and-throw.md`).
- The controller interacts as the `CHARACTER` layer: vanilla asks `dGetInteractionLayer(this, PhxInteractionLayers.CHARACTER, layer)` to decide what blocks a player (`P:\scripts\3_game\vehicles\transport.c:791`).

## Controller calls

| Call | Answers or does | Source |
|---|---|---|
| `PhysicsIsFalling(bool pValidate)` | Is the controller falling; from 1.30 also true while the ragdoll moves faster than 1 m/s | `P:\scripts\3_game\human.c:1428` |
| `PhysicsGetFloorEntity()` | The entity below the player | `human.c:1431` |
| `PhysicsGetLinkedEntity()` | The entity the player is linked to (a boat, a platform) | `human.c:1434` |
| `PhysicsWasSlidingOffLinkedEntity()` | Did that entity move faster than its config `animPhysDetachSpeed` | `human.c:1438` |
| `PhysicsGetVelocity(out vector pVelocity)` | The controller's linear velocity | `human.c:1441` |
| `PhysicsEnableGravity(bool pEnable)` | Controller gravity on or off | `human.c:1443` |
| `PhysicsIsSolid()` and `PhysicsSetSolid(bool pSolid)` | By their names, whether the controller is solid; vanilla has no comment on them and calls `PhysicsSetSolid(true)` after pulling a player out of a vehicle (`P:\scripts\4_world\entities\dayzplayerimplement.c:661`) | `human.c:1445`, `:1446` |
| `LinkToLocalSpaceOf(child, pLocalSpaceMatrix[4])` | Links an entity into the local space of the player | `human.c:1391` |
| `CheckFreeSpace(localDir, distance, useHeading, ...)` | Is there room for the collider in a direction | `human.c:1381` |
| `CollisionMoveTest(dir, offset, xzScale, ignoreEntity, ...)` | Can the character move that way; returns the fraction of the distance | `human.c:1387` |

`GetVelocity(ent)` and `SetVelocity(ent, vel)` are global and accept a player (`P:\scripts\1_core\proto\enphysics.c:104`, `:111`). Vanilla's only config use of `animPhysDetachSpeed` is on boats (`animPhysDetachSpeed=5`, `P:\DZ\vehicles\water\config.cpp:55`).

## Riding a moving platform

All of this section is measured in game with one client; none of it can be checked on `P:\`.

- Animated geometry of a building does not carry a player. A piece moved by a config animation leaves a standing player hanging in the air on the way down, and clips through a parked car on the way up. A lift needs script.
- A separate entity moved with `SetPosition` every frame, on the server and on each client, does carry a player once the player is linked to it (`PhysicsGetLinkedEntity() == platform`). A `House` inheriting `HouseNoDestruct` with `animPhysDetachSpeed=100` lifts a standing player 8.9 m in 15 s within 5 cm on the server and within 7.9 cm on the client, one frame behind. Walking and jumping on it keep the link. A player teleported onto it needs one native step before linking; a player who walks on links at once.
- A jump on the platform is relative to it. Jumps on the way down stay linked, spend 0.42 to 0.47 s in the air, peak 0.30 to 0.32 m above the face and land on the platform, close to the vanilla jump on still ground: `StartCommand_Fall(2.6)` (`P:\scripts\4_world\entities\dayzplayerimplementjumpclimb.c:97`; `StartCommand_Fall(float pYVelocity)`, `P:\scripts\3_game\human.c:1501`) is a 0.345 m, 0.53 s arc. Not measured: a jump while the platform rises.
- `EOnFrame` does not reach a `House`. Drive the platform from the update queue, which runs every frame on server and client: `GetUpdateQueue(CALL_CATEGORY_GAMEPLAY)` (`P:\scripts\3_game\dayzgame.c:3081`).
- A Roadway face of another model inside the travel stops the ride down. Why no raycast finds such a face is in `collision-lods.md`; keep every other model's Roadway faces out of the volume the cabin sweeps.
- Keep vehicles on the platform awake and set their velocity each frame to the platform's velocity plus 4 times the position error. With that, a sedan (with and without wheels) and a helicopter on a `CarScript` flight model ride within 4.6 cm on the server and 11.5 cm on the client, and stop exactly when released. Awake with no velocity set, the sedan rides well but the helicopter bounces up to 24 cm and slides 31 cm. A sleeping vehicle moved with `SetPosition`, even with `Transport.Synchronize()`, is not sent to clients until it wakes (`network-and-authority.md`).

## Lifting the player from a command script

Measured in game on 1.30; not checked on `P:\`.

- A `HumanCommandScript` that raises the player with `PrePhys_SetTranslation` (local space, `P:\scripts\3_game\human.c:1313`) gets no lift while controller gravity is on: the first air tick loses its whole upward step, and 0.2 s into the flight the body is 1 cm under its take-off height where about 0.34 m up was asked for.
- With `PhysicsEnableGravity(false)` from take-off to landing the body follows the translation: every server air tick stays within 3 cm, and the apex on the owner client is 0.996 to 1.001 times the ballistic height. Not measured: a remote observer, flights longer than 0.6 s, and fall damage after a flight with gravity off.
- The command owns switching gravity back on at every exit, including a ride that ends in the air. Vanilla itself only ever calls `PhysicsEnableGravity(true)` when a vehicle death's simulation ends (`P:\scripts\4_world\entities\dayzplayerimplement.c:32`).
- `PhysicsIsFalling(true)` is not a pure read. Skip that call on the ticks before the lift and every take-off loses its first air tick; call it, result ignored, and the lift works. What `pValidate` does is not documented (`P:\scripts\3_game\human.c:1428`).
- `PostPhys_SetPosition` takes world space (`P:\scripts\3_game\human.c:1327`); `PrePhys_SetTranslation` takes local space. Mixing them up is a common cause of a body that snaps.

## Walking a player from script

`OverrideMovementSpeed` and `OverrideMovementAngle` (`P:\scripts\3_game\human.c:253`, `:256`) move a client controlled player only when both the owner client and the server apply them on every move. Set on the client only, the player moves 0.24 to 0.40 m in 1.5 s; set on the client and once on the server by RPC, not at all (measured in game; not checked on `P:\`).

The shape that walks the player:

1. The owner sets both overrides on every command tick and sends a `ScriptInputUserData` request.
2. The server applies the same two overrides in every `ConsumeMove` after `super` and in its `CommandHandler`.
3. Both switch them off at the end.

Owner and server then move at 1.52 m/s and stop at the same position. Script fields added to `PlayerBaseMove` never reach the server, so carry the request in `ScriptInputUserData`.
