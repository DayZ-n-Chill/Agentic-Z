# Ragdoll and fall damage

Covers the player ragdoll calls, what changed in 1.30, ragdolling a living player, waking from unconsciousness safely, and the fall damage curve. The format of the `.ragdoll` file, its bone masses and how a survivor body binds it are in `skills/_shared/wearables/references/ragdoll.md`. The character controller itself is in `player-controller.md`.

The measured results below come from in-game tests and can't be checked on `P:\`; confirm them in game before a design depends on one.

## Ragdoll calls

- **1.30:** the calls are `PhysicsSetSimpleDeath(bool pEnable)` (new, `P:\scripts\3_game\human.c:1449`), `PhysicsSetRagdoll(bool pEnable)` (`:1451`) and `PhysicsIsRagdoll()` (`:1452`). An unconscious player's command has `IsRagdoll()` (`P:\scripts\3_game\human.c:647`).
- **1.30:** the death branch that starts no death command now calls `PhysicsSetSimpleDeath(true)` (`P:\scripts\4_world\entities\dayzplayerimplement.c:745`). 1.29 called `PhysicsSetRagdoll(true)` there (that build is not on `P:\`; the comment at `P:\scripts\3_game\human.c:1448` says the death state "was previously handled by PhysicsSetRagdoll"). In 1.29 the comment above `PhysicsSetRagdoll` said it set and synchronized the `RAGDOLL` and `RAGDOLL_NO_CHARACTER` layers so bodies do not stack and players do not walk through dead creatures; the 1.30 file has no such comment.
- **1.30:** while an unconscious player's ragdoll is active, vanilla drops the vehicle they came from, so they are not put back in it on waking (`m_TransportCache = null` behind `hcu.IsRagdoll()`, `P:\scripts\4_world\entities\manbase\playerbase.c:3346-3350`).
- **1.30:** the ragdoll's bodies are data: `RagdollDef` in `P:\DZ\characters\bodies\human.ragdoll:1`, 11 `RagdollBone` entries with a mass, capsule or sphere geometries on `flesh.bisurf`, and joint limits. The masses add up to 73.9 kg (pelvis `Mass 17` at `P:\DZ\characters\bodies\human.ragdoll:5`). There is no script call that loads a ragdoll file (no `LoadRagdollFile` in `P:\scripts`).
- These calls are on `Human` only. Infected and animals inherit `DayZCreature`, which extends `EntityAI` (`P:\scripts\3_game\entities\dayzanimal.c:24`), so they have no ragdoll call. Giving an infected a `ragdoll =` entry and player death clips did nothing in game (seen on 1.30.164078; not checkable on `P:\`): the death command played the clip and froze in its last pose. A corpse swap (on death, spawn a survivor at the same transform, move the gear, kill it) is an idea that has not been tested.

## A ragdoll on a living player

- **It works on the server only.** Measured in game (2026-06-10): after `DisableSimulation(false)` (as the death flow does, `P:\scripts\4_world\entities\dayzplayerimplement.c:735`), waking the body with `dBodyActive` `ACTIVE` and `dBodyDynamic(p, true)`, and `PhysicsSetRagdoll(true)`, an impulse of velocity times mass took on the first try and the body slid 77.6 m at 4 to 6.7 m/s, uphill included. `dBodyGetMass` read 87.5 kg there; that is the controller body, not the 73.9 kg of the ragdoll file. The owner's client kept a standing, controllable avatar. It needs custom position sync to be usable.
- **Switching it off does not snap back.** `PhysicsSetRagdoll(false)` left the player exactly where the body had ended.
- **Waking too early buries the player.** In that test a wake at 0.5 s left the player 40 m under the terrain. Vanilla waits for `m_UnconsciousTime > 2` (`P:\scripts\4_world\entities\manbase\playerbase.c:3420`), and from 1.30 also refuses while `PhysicsIsFalling(false)` is true (`:3423`), which includes a ragdoll still moving faster than 1 m/s (`P:\scripts\3_game\human.c:1426-1428`). Keep both guards in a custom wake.
- Vanilla pushes a body from script only when it is dead: `RegisterTransportHit` calls `dBodyApplyImpulse` behind `IsDamageDestroyed()` (`P:\scripts\3_game\entities\entityai.c:4159`). A living player is moved by the collision itself. See `contact.md`.

## Fall damage (1.30)

`DayZPlayerImplementFallDamage` changed in 1.30 from a straight line to a curve, with lower starting heights.

| Effect | Starts at | Full at | Curve power | Source |
|---|---|---|---|---|
| Health | 2 m (`HEALTH_HEIGHT_LOW`) | 12 m | 2.0 | `P:\scripts\4_world\entities\dayzplayerimplementfalldamage.c:26`, `:104` |
| Shock | 0 m (`SHOCK_HEIGHT_LOW`) | 8 m | 2.0 | `P:\scripts\4_world\entities\dayzplayerimplementfalldamage.c:29`, `:108` |
| Broken legs | 3 m (`BROKENLEGS_HEIGHT_LOW`) | 8 m | 2.5 | `P:\scripts\4_world\entities\dayzplayerimplementfalldamage.c:31`, `:111` |

- The other `CurveExp` curves in `HandleFallDamage` use power 1.8 for bleeding hands and feet, 2.0 for bleeding legs, gloves, pants and the bleeding chance, and 2.2 for shoes (`P:\scripts\4_world\entities\dayzplayerimplementfalldamage.c:116-139`).
- The curve is `CurveExp(low, high, value, power)`: the height's position between low and high, clamped to 0 to 1, raised to the power (`P:\scripts\4_world\entities\dayzplayerimplementfalldamage.c:92-97`).
- `Randomize` returns a coefficient of 1 unchanged, so a lethal fall is not rolled back down (`P:\scripts\4_world\entities\dayzplayerimplementfalldamage.c:160-163`).
- The damage is dealt with `ProcessDirectDamage` and the ammo `FallDamageHealth` and `FallDamageShock` (`FALL_DAMAGE_AMMO_HEALTH` and `FALL_DAMAGE_AMMO_SHOCK`, `P:\scripts\4_world\entities\dayzplayerimplementfalldamage.c:20-21`; applied at `:155-156`), both defined in `P:\DZ\weapons\melee\config.cpp` (`FallDamageHealth` at `:2182`, `FallDamageShock` at `:2201`). The rest of the damage path is in `damage-pipeline.md`.
- The 1.29 values were health 5 to 14 m, shock 3 to 12 m and broken legs 5 to 9 m, on a straight line (that build is not on `P:\`). A `modded class` that copies those constants and `Math.InverseLerp` compiles on 1.30 and silently brings the old, weaker curve back.
