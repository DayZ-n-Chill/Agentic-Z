# Gunner, shoot from a vehicle: the attached-rider pattern

How a rider can fire their own handheld weapon from a moving car or boat: the player is linked to the vehicle at an anchor, frozen by a scripted human command, and reports that they are not in a vehicle.

> Status: the pattern below is third-party mod behaviour, not vanilla. It describes how one third-party gunner mod (version 2.61, obfuscated) works; its files are not part of this repo and none of its behaviour is checked on `P:\` or was run here. Identifiers in that mod are named by role where the original name is obfuscated. A citation written with its full `P:\` path was opened on the vanilla data of this repo. The vanilla methods the pattern is built from are in the anchors below.

## Vanilla anchors checked on `P:\`

- `LinkToLocalSpaceOf` is native on `Human`: `P:\scripts\3_game\human.c:1391`.
- `HumanCommandScript` is the scripted command base class: `P:\scripts\3_game\human.c:1236`.
- `StartCommand_Script` starts one: `P:\scripts\3_game\human.c:1623`.
- `IsInVehicle` is declared on `DayZPlayerImplement`, an ancestor of `PlayerBase` (through `ManBase`): `P:\scripts\4_world\entities\dayzplayerimplement.c:468`.
- `PlayerBase.CanReceiveItemIntoHands` returns `false` while `IsInVehicle()` is true: `P:\scripts\4_world\entities\manbase\playerbase.c:2284`.
- `UnlinkFromLocalSpace` undoes the link: `P:\scripts\3_game\human.c:1392`.
- `dBodyActive` sets the active state of a body: `P:\scripts\1_core\proto\enphysics.c:64`.
- `dBodyEnableGravity` switches gravity on a body: `P:\scripts\1_core\proto\enphysics.c:69`.
- `StartCommand_Vehicle` seats a player in a real crew seat: `P:\scripts\3_game\human.c:1526`.
- `AddNoiseTarget` is the noise system call: `P:\scripts\3_game\noise.c:10`.

## The pattern in one paragraph

This is how to let a player **fire their own handheld weapon while riding a moving vehicle**. The player is **rooted to an anchor point** (standing or crouched in the vehicle bed or on a boat deck): they aim and fire but do NOT walk around. The freeze is the whole point (piece 3). Treat the mod as a pattern to study, not as code to reuse: it is obfuscated and signed. Write your own implementation.

This is the **handheld attached-gunner** family. A **fixed vehicle turret** (its own `CfgMagazines` and `CfgAmmo`, damage through `ProcessDirectDamage`) is a different recipe. The two compose: one technical can carry both.

## The one trick that makes it work

**`PlayerBase.IsInVehicle()` is overridden to return `false` while the gunner state is active.** Vanilla player code branches on `IsInVehicle()` in many places (the anchors list one). A player who is physically riding the vehicle but reports `IsInVehicle()==false` is treated as on foot, so they can raise and fire normally. Everything else is scaffolding around this lie. That this override is what unlocks raise and fire is the mod's behaviour, not checked on `P:\`.

## The seven pieces

1. **Attach without a crew seat**: `LinkToLocalSpaceOf(trans, localMatrix)`. Compute the local matrix from the model-space anchor:
   ```
   GetTransform(playerWorld);
   playerWorld[3] = trans.ModelToWorld(modelSpaceAnchor);
   trans.GetTransform(vehWorld);
   Math3D.MatrixInvMultiply4(vehWorld, playerWorld, local);
   SetTransform(local);
   LinkToLocalSpaceOf(trans, local);      // rider now moves WITH the vehicle
   ```
   Call `UnlinkFromLocalSpace()` on exit.

2. **Freeze rider physics**: `dBodyEnableGravity(this,false)` plus `dBodyActive(this, ActiveState.INACTIVE)`, asserted again in `CommandHandler` every tick because the engine re-activates the body. Without it the rider falls or gets punted by the moving collider.

3. **The freeze: a `HumanCommandScript` subclass (this is why the player cannot walk)**. The mod calls `StartCommand_Script(new HumanGunnerCommand(this, stanceParam))` and issues it again from `CommandHandler` every tick. The class:
   ```c
   class HumanGunnerCommand extends HumanCommandScript {
       PlayerBase m_user; int m_stance;
       void HumanGunnerCommand(PlayerBase p, int stance) { m_user = p; m_stance = stance; }
       override void OnActivate() {
           HumanAnimInterface hai = m_user.GetAnimInterface();
           int v = hai.BindVariableInt("Stance");
           if (m_stance >= threshold) PreAnim_SetInt(v, m_stance);   // force the pose, and that is ALL
       }
   };
   ```
   `StartCommand_Script` puts the player into a **fully scripted human command that replaces normal locomotion**. This subclass overrides only `OnActivate` (bind and force the `Stance` animation variable) with **no `OnUpdate`, `PrePhysUpdate` or `PostPhysUpdate`**, so the engine runs no walk logic and the player is **animation-locked in the stance**: free to rotate, aim and fire, but unable to translate. This is the anti-movement mechanism. Writing your own is easy: a tiny `HumanCommandScript` that only sets the stance.

4. **Self-transport damage immunity**: `EEOnDamageCalculated` returns `false` when the damage source is the gunner's own transport. Riding your own vehicle otherwise logs collision damage.

5. **Input controller: locks movement on the client, does NOT enable walking**. From `MissionGameplay.OnUpdate`, every frame, every movement key gets `UAInput.ForceDisable(true)` while the player is a gunner (a second lock on top of the command freeze of piece 3). `UATempRaiseWeapon` is enabled only when a `Weapon` is in hands. The mod also carries a forward and back block that raycasts the floor and obstacles and re-enables the Forward and Back keys, but the movement itself (a teleport) is commented out, and a `HumanCommandScript` ignores locomotion input anyway. It is dead code from a reposition feature. Net: the player is stationary.

6. **Leash**: each frame measure `vector.Distance(player, trans.ModelToWorld(anchor))`; if it exceeds the slot's `distance`, fire a server RPC that snaps the player home. This catches the rider when physics drift moves them off the anchor even though input is locked.

7. **Camera and stance control**: `CameraHandler` forces `m_Camera3rdPerson` according to the slot's camera mode; `HandleView` toggles on `CameraViewChanged()` but suppresses the flip while the weapon is raised. `CanChangeStance` blocks prone and crouch transitions that would clip the rider through the vehicle.

## Two flavors, one config

- **Seated gunner**: a *real* crew seat via `StartCommand_Vehicle(transport, seat, GetSeatAnimationType(seat))`, with the weapon unlocked. The classic turret seat.
- **Attached gunner**: the `LinkToLocalSpaceOf` attach plus the scripted-command freeze at an anchor. Rooted in place (not seated, not walking).

Both flow through `PlayerBase.ModCommandHandlerBefore` as a queued-transition state machine: board seat, exit, board gunner from seat, board gunner standalone, exit gunner. **Exit restores the position from the vehicle's own crew memory point**, not a hardcoded spot: `ConfigGetChildName` on `CfgVehicles <type> Crew` gives the seat class, `ConfigGetText` on its `getInPos` gives the memory point name, then `GetMemoryPointPos`, `ModelToWorld` and `SetPosition`.

Sync variables: one bool on the player for the gunner state (`RegisterNetSyncVariableBool`), and per-seat permission bitmasks on the car or boat (`RegisterNetSyncVariableInt`, one bit per seat, set from JSON in `EEInit`).

## Per-vehicle JSON

A `$profile:` JSON keyed by vehicle **type**, with up to **10 slots** (`gunner1` to `gunner10`). Per slot: `type` (0 = off), `camera` (force first person, toggle, or force third person), `distance` (the leash), `stance`, and `pos`, `pos_auto` and `dir` (the model-space anchor and facing). The `collision`, `intersect`, `script_collision` and `move` fields belong to the disabled reposition feature. `CarScript.EEInit` loads the slot config for `GetType()` from a global map and sets the seat lock bits; the map is synced to clients with an RPC.

## Scope and requirements

`CfgPatches.requiredAddons` is `DZ_Data`, `DZ_Vehicles_Wheeled` and `DZ_Vehicles_Water`: **cars and boats**. Both `CarScript` and `BoatScript` are modded identically. The config is script-side (`CfgMods` plus `CfgPatches`).

## Known weaknesses (fix these if you write your own)

- **The player is fixed, with no reposition.** The gunner is rooted to the anchor; the forward and back shuffle is commented out (a teleport on a moving platform desyncs). A real "step along the bed" ability is new work (a move command that respects the vehicle-local frame and the leash), not a config toggle.
- **Client-side safety net.** The freeze is engine-enforced (scripted command), but the input suppression and the leash monitor run on the client; the only server correction is the radius snap. If you add repositioning, validate it on the server with a **throttled** raycast (200 to 300 ms, not every frame; many gunners would cost server FPS).
- **No fire noise at vehicle level.** Firing is vanilla per weapon; a technical full of shooters is as loud as one rifle. Add a call to `AddNoiseTarget` if you want infected to respond.
- **No move-speed aim penalty.** You aim identically at 80 km/h and parked. A sway that reads the `Transport` speed adds tactical depth.
- **`LinkToLocalSpaceOf` plus `dBodyActive(INACTIVE)` is fragile.** It is fought every frame; a hard collision can pop the rider off, which is why the leash exists. Consider a defensive re-link on `EOnContact`, or turn it into a feature (a thrown-off ragdoll above an impact-speed threshold).

## Cross-references

- The RPC dispatch used here (one fixed id plus a function name) is in `skills/enforce-script-reference/references/networking.md`, "One ID and a function name: the RPCManager pattern".
- Pose command work: the dayz-animation-pipeline skill.
