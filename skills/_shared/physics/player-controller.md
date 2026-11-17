# Players and physics

Covers the player's character controller: where it is simulated and what that means for collision, the calls script has on it, riding a moving platform, lifting the player from a command script, the ragdoll, and fall damage. The 1.30 changes are marked.

The measured results below come from in-game tests; each names its build where it is known. They can't be checked on `P:\`, so confirm them in game before a design depends on one. The full write-ups are in `skills/dayz-physics-engine/SKILL.md` and `skills/dayz-physics-engine/references/ragdoll-and-fall-damage.md`.

## The controller is not a rigid body

- A player is moved by a character controller, driven through calls on `Human` (`class Human`, `P:\scripts\3_game\human.c:1359`), not by a body that `dBody` calls steer.
- The controller is simulated on the player's own client. **A body that exists only on the server can never block a player**: that client has nothing to collide with. No layer setting changes this. To block or carry a player, the object's collision must exist on the client too: a model's Geometry LOD (`collision-lods.md`), or the native throw path, which vanilla runs on the server and the owner client (`drop-and-throw.md`).
- The controller interacts as the `CHARACTER` layer: vanilla asks `dGetInteractionLayer(this, PhxInteractionLayers.CHARACTER, layer)` to decide what blocks a player (`P:\scripts\3_game\vehicles\transport.c:788`).

## Controller calls

| Call | Answers or does | Line in `P:\scripts\3_game\human.c` |
|---|---|---|
| `PhysicsIsFalling(bool pValidate)` | Is the controller falling; from 1.30 also true while the ragdoll moves faster than 1 m/s | `P:\scripts\3_game\human.c:1428` |
| `PhysicsGetFloorEntity()` | The entity below the player | `P:\scripts\3_game\human.c:1431` |
| `PhysicsGetLinkedEntity()` | The entity the player is linked to (a boat, a platform) | `P:\scripts\3_game\human.c:1434` |
| `PhysicsWasSlidingOffLinkedEntity()` | Did that entity move faster than its config `animPhysDetachSpeed` | `P:\scripts\3_game\human.c:1438` |
| `PhysicsGetVelocity(out vector pVelocity)` | The controller's linear velocity | `P:\scripts\3_game\human.c:1441` |
| `PhysicsEnableGravity(bool pEnable)` | Controller gravity on or off | `P:\scripts\3_game\human.c:1443` |
| `PhysicsSetSolid(bool pSolid)` | By its name, whether the controller is solid; vanilla has no comment on it and calls it with `true` after pulling a player out of a vehicle | `P:\scripts\3_game\human.c:1446` |
| `CheckFreeSpace(localDir, distance, useHeading, ...)` | Is there room for the collider in a direction | `P:\scripts\3_game\human.c:1381` |
| `CollisionMoveTest(dir, offset, xzScale, ignoreEntity, ...)` | Can the character move that way; returns the fraction of the distance | `P:\scripts\3_game\human.c:1387` |

`GetVelocity(ent)` and `SetVelocity(ent, vel)` are global and accept a player (`P:\scripts\1_core\proto\enphysics.c:104`, `:111`).

Vanilla's only config use of `animPhysDetachSpeed` is on boats (`animPhysDetachSpeed=5`, `P:\DZ\vehicles\water\config.cpp:55`).

## Riding a moving platform

Measured in game (DayZDiag 1.29.163709, one client on localhost):

- **Animated geometry of a building does not carry a player.** A piece moved by a config animation leaves a standing player hanging in the air on the way down, and clips through a parked car on the way up. A lift needs script.
- **A separate entity moved with `SetPosition` every frame, on the server and on each client, does carry a player**, once the player is linked to it (`PhysicsGetLinkedEntity() == platform`). The test platform was a `House` inheriting `HouseNoDestruct` with `animPhysDetachSpeed=100`; it lifted a standing player 8.9 m in 15 s within 5 cm on the server. Walking and jumping on it kept the link. A player teleported onto it needs one native step before linking; a player who walks on links at once.
- **`EOnFrame` does not reach a `House`.** Drive the platform from the update queue, which runs every frame on server and client: `GetUpdateQueue(CALL_CATEGORY_GAMEPLAY)` (`P:\scripts\3_game\dayzgame.c:3081`).
- **A Roadway face of another model inside the travel stops the ride down.** The measured case, and why no raycast finds such a face, are in `collision-lods.md`; keep every other model's Roadway faces out of the volume the cabin sweeps.
- **Vehicles on the platform:** keep them awake and set their velocity each frame to the platform's velocity plus a correction for the position error. A sleeping vehicle moved with `SetPosition` is not sent to clients until it wakes.

## Lifting the player from a command script

Measured in game (DayZDiag 1.30.164014 experimental, 2026-10-06):

- A `HumanCommandScript` that raises the player with `PrePhys_SetTranslation` (local space, `P:\scripts\3_game\human.c:1313`) gets no lift while controller gravity is on: the first air tick lost its whole upward step. With `PhysicsEnableGravity(false)` from take-off to landing the body followed the translation.
- The command owns switching gravity back on at every exit, including a ride that ends in the air. Vanilla itself only ever calls `PhysicsEnableGravity(true)`, when a vehicle death's simulation ends (`P:\scripts\4_world\entities\dayzplayerimplement.c:32`).
- `PhysicsIsFalling(true)` is not a pure read. Skipping that call on the ticks before the lift made every take-off lose its first air tick; calling it again, result ignored, fixed it. What `pValidate` does is not documented (`P:\scripts\3_game\human.c:1428`).
- `PostPhys_SetPosition` takes world space (`P:\scripts\3_game\human.c:1327`); `PrePhys_SetTranslation` takes local space. Mixing them up is a common cause of a body that snaps.

## Walking a player from script

`OverrideMovementSpeed` and `OverrideMovementAngle` (`P:\scripts\3_game\human.c:253`, `:256`) move a client controlled player only when both the owner client and the server apply them on every move. Measured in game (DayZDiag 1.29): set on the client only, the player moved 0.24 to 0.40 m in 1.5 s; applied on both sides every tick, 1.52 m/s with both ending at the same position.

## Ragdoll

- **1.30:** the calls are `PhysicsSetSimpleDeath(bool pEnable)` (new, `P:\scripts\3_game\human.c:1449`), `PhysicsSetRagdoll(bool pEnable)` (`:1451`) and `PhysicsIsRagdoll()` (`:1452`). An unconscious player's command has `IsRagdoll()` (`P:\scripts\3_game\human.c:647`).
- **1.30:** the death branch that starts no death command now calls `PhysicsSetSimpleDeath(true)` (`P:\scripts\4_world\entities\dayzplayerimplement.c:745`). 1.29 called `PhysicsSetRagdoll(true)` there (that build is not on `P:\`; the comment at `P:\scripts\3_game\human.c:1448` says the death state "was previously handled by PhysicsSetRagdoll").
- **1.30:** the ragdoll's bodies are data: `RagdollDef` in `P:\DZ\characters\bodies\human.ragdoll:1`, 11 `RagdollBone` entries with a mass, capsule or sphere geometries on `flesh.bisurf`, and joint limits. The masses add up to 73.9 kg (pelvis `Mass 17` at `P:\DZ\characters\bodies\human.ragdoll:5`).
- These calls are on `Human` only. Infected and animals inherit `DayZCreature`, which extends `EntityAI` (`P:\scripts\3_game\entities\dayzanimal.c:24`), so they have no ragdoll call. Giving an infected a `ragdoll =` entry and player death clips did nothing in game (seen on 1.30.164078; not checkable on `P:\`).
- **A ragdoll on a living player works on the server only.** Measured in game (2026-06-10): after `DisableSimulation(false)`, waking the body and `PhysicsSetRagdoll(true)`, an impulse took and the body slid 77.6 m on the server, but the owner's client kept a standing, controllable avatar. It needs custom position sync to be usable.
- **Waking too early buries the player.** In that test a wake at 0.5 s left the player 40 m under the terrain. Vanilla waits for `m_UnconsciousTime > 2` (`P:\scripts\4_world\entities\manbase\playerbase.c:3420`), and from 1.30 also refuses while `PhysicsIsFalling(false)` is true (`:3423`). Keep both guards in a custom wake.
- Vanilla pushes a body from script only when it is dead: `RegisterTransportHit` calls `dBodyApplyImpulse` behind `IsDamageDestroyed()` (`P:\scripts\3_game\entities\entityai.c:4159`). A living player is moved by the collision itself. See `contact.md`.

## Fall damage (1.30)

`DayZPlayerImplementFallDamage` changed in 1.30 from a straight line to a curve, with lower starting heights.

| Effect | Starts at | Full at | Curve power | Source |
|---|---|---|---|---|
| Health | 2 m (`HEALTH_HEIGHT_LOW`) | 12 m | 2.0 | `P:\scripts\4_world\entities\dayzplayerimplementfalldamage.c:26`, `:104` |
| Shock | 0 m (`SHOCK_HEIGHT_LOW`) | 8 m | 2.0 | `P:\scripts\4_world\entities\dayzplayerimplementfalldamage.c:29`, `:108` |
| Broken legs | 3 m (`BROKENLEGS_HEIGHT_LOW`) | 8 m | 2.5 | `P:\scripts\4_world\entities\dayzplayerimplementfalldamage.c:31`, `:111` |

- The curve is `CurveExp(low, high, value, power)`: the height's position between low and high, clamped to 0 to 1, raised to the power (`P:\scripts\4_world\entities\dayzplayerimplementfalldamage.c:92-97`).
- `Randomize` returns a coefficient of 1 unchanged, so a lethal fall is not rolled back down (`P:\scripts\4_world\entities\dayzplayerimplementfalldamage.c:160-163`).
- The damage is dealt with `ProcessDirectDamage` and the ammo `FallDamageHealth` and `FallDamageShock` (`FALL_DAMAGE_AMMO_HEALTH`, `P:\scripts\4_world\entities\dayzplayerimplementfalldamage.c:20`; applied at `:155`), both defined in `P:\DZ\weapons\melee\config.cpp:2182` (`FallDamageHealth`).
- The 1.29 values were health 5 to 14 m, shock 3 to 12 m and broken legs 5 to 9 m, on a straight line (that build is not on `P:\`). A `modded class` that copies those constants and `Math.InverseLerp` compiles on 1.30 and silently brings the old, weaker curve back.
