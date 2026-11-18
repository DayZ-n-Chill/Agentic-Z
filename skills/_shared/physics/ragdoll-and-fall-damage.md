# Ragdoll and fall damage

Covers the player ragdoll calls, ragdolling a living player, waking from unconsciousness safely, and the fall damage curve, with what changed in 1.30. The format of the `.ragdoll` file, its bone masses and how a survivor body binds it are in `_shared/wearables/references/ragdoll.md`. The character controller itself is in `player-controller.md`.

## Ragdoll calls

- The calls are `PhysicsSetSimpleDeath(bool pEnable)` (new in 1.30, `P:\scripts\3_game\human.c:1449`), `PhysicsSetRagdoll(bool pEnable)` (`:1451`) and `PhysicsIsRagdoll()` (`:1452`). An unconscious player's command has `IsRagdoll()` (`:647`).
- The death branch that starts no death command calls `PhysicsSetSimpleDeath(true)` (`P:\scripts\4_world\entities\dayzplayerimplement.c:745`). Before 1.30 it called `PhysicsSetRagdoll(true)`; the vanilla comment says the death state "was previously handled by PhysicsSetRagdoll" (`P:\scripts\3_game\human.c:1448`). A mod written for 1.29 that hooks the ragdoll call at death no longer sees it there.
- While an unconscious player's ragdoll is active, vanilla drops the vehicle they came from, so they are not put back in it on waking (`m_TransportCache = null` behind `hcu.IsRagdoll()`, `P:\scripts\4_world\entities\manbase\playerbase.c:3346` to `:3350`).
- The ragdoll's bodies are data: `RagdollDef` in `P:\DZ\characters\bodies\human.ragdoll:1`, 11 `RagdollBone` entries with a mass, capsule or sphere geometries on `flesh.bisurf`, and joint limits. The masses add up to 73.9 kg (pelvis `Mass 17` at `human.ragdoll:5`). No script call loads a ragdoll file (no `LoadRagdollFile` in `P:\scripts`).
- These calls are on `Human` only. Infected and animals inherit `DayZCreature`, which extends `EntityAI` (`P:\scripts\3_game\entities\dayzanimal.c:24`), so they have no ragdoll call. Giving an infected a `ragdoll =` entry and player death clips does nothing: the death command plays the clip and freezes in its last pose (measured in game; not checked on `P:\`). Unverified (not tested in game): a corpse swap, that is on death spawning a survivor at the same transform, moving the gear across and killing it.

## A ragdoll on a living player

Measured in game; not checked on `P:\`.

- It works on the server only. Call `DisableSimulation(false)` (as the death flow does, `P:\scripts\4_world\entities\dayzplayerimplement.c:735`), wake the body with `dBodyActive` `ACTIVE` and `dBodyDynamic(p, true)`, then `PhysicsSetRagdoll(true)`. An impulse of velocity times mass then takes at once, and the body slides 77.6 m at 4 to 6.7 m/s, uphill included. `dBodyGetMass` reads 87.5 kg there; that is the controller body, not the 73.9 kg of the ragdoll file.
- The owner's client keeps a standing, controllable avatar, so the effect needs your own position sync to be usable.
- `PhysicsSetRagdoll(false)` leaves the player exactly where the body ended; it does not snap back.
- A wake 0.5 s after the ragdoll starts leaves the player 40 m under the terrain.

## Waking safely

- Vanilla waits for `m_UnconsciousTime > 2` (`P:\scripts\4_world\entities\manbase\playerbase.c:3420`), and from 1.30 also refuses while `PhysicsIsFalling(false)` is true (`:3423`), which includes a ragdoll still moving faster than 1 m/s (`P:\scripts\3_game\human.c:1426` to `:1428`). Keep both guards in a custom wake.
- The unconscious command's `WakeUp(int targetStance = -1)` takes the stance to stand up into, and `IsWakingUp()` says the get up is still playing (`P:\scripts\3_game\human.c:644` and `:645`). Vanilla wakes into `STANCEIDX_PRONE`, but passes -1 when the player was swimming or went unconscious in a vehicle (`m_LastCommandBeforeUnconscious == COMMANDID_VEHICLE`), because "stance change animation could play" there (`P:\scripts\4_world\entities\manbase\playerbase.c:3425` to `:3431`). A custom wake that always forces prone can play that animation in water or in a seat.
- Vanilla pushes a body from script only when it is dead: `RegisterTransportHit` calls `dBodyApplyImpulse` behind `IsDamageDestroyed()` (`P:\scripts\3_game\entities\entityai.c:4159`). A living player is moved by the collision itself; see `contact.md`.

## Fall damage

In 1.30 `DayZPlayerImplementFallDamage` uses a curve with these heights:

| Effect | Starts at | Full at | Curve power | Source |
|---|---|---|---|---|
| Health | 2 m (`HEALTH_HEIGHT_LOW`) | 12 m | 2.0 | `P:\scripts\4_world\entities\dayzplayerimplementfalldamage.c:26`, `:104` |
| Shock | 0 m (`SHOCK_HEIGHT_LOW`) | 8 m | 2.0 | `dayzplayerimplementfalldamage.c:29`, `:108` |
| Broken legs | 3 m (`BROKENLEGS_HEIGHT_LOW`) | 8 m | 2.5 | `dayzplayerimplementfalldamage.c:31`, `:111` |

- The curve is `CurveExp(low, high, value, power)`: the height's position between low and high, clamped to 0 to 1, raised to the power (`P:\scripts\4_world\entities\dayzplayerimplementfalldamage.c:92` to `:97`).
- The other `CurveExp` curves in `HandleFallDamage` use power 1.8 for bleeding hands and feet, 2.0 for bleeding legs, gloves, pants and the bleeding chance, and 2.2 for shoes (`:116` to `:139`).
- `Randomize` returns a coefficient of 1 unchanged, so a lethal fall is not rolled back down (`:160` to `:163`).
- The damage is dealt with `ProcessDirectDamage` and the ammo `FallDamageHealth` and `FallDamageShock` (`FALL_DAMAGE_AMMO_HEALTH` and `FALL_DAMAGE_AMMO_SHOCK`, `:20` and `:21`; applied at `:155` and `:156`), both defined in `P:\DZ\weapons\melee\config.cpp` (`FallDamageHealth` at `:2182`, `FallDamageShock` at `:2201`). The rest of the damage path is in `damage-pipeline.md`.
- 1.29 used a straight line with health from 5 to 14 m, shock from 3 to 12 m and broken legs from 5 to 9 m (not on `P:\`, which holds 1.30). A `modded class` that copies those constants and `Math.InverseLerp` still compiles on 1.30 and quietly brings the weaker damage back.
