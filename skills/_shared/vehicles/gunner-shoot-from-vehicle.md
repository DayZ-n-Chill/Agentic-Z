# Shooting from a moving vehicle

How a rider can fire their own handheld weapon from a moving car or boat: the player is linked to the vehicle at an anchor, frozen by a scripted human command, and reports that they are not in a vehicle.

The pattern is read from one third-party gunner mod (version 2.61, obfuscated and signed); its behaviour is not checked on `P:\` and was not run here. Its obfuscated identifiers are named here by role. Study it as a pattern and write your own code. The vanilla methods it is built from are cited.

This is the handheld gunner, rooted to a point in a truck bed or on a boat deck: the rider aims and fires but does not walk. A fixed vehicle turret, with its own `CfgMagazines` and `CfgAmmo` and damage through `ProcessDirectDamage`, is a different recipe; one vehicle can carry both.

## The trick that makes it work

The mod overrides `PlayerBase.IsInVehicle()` to return `false` while the rider is a gunner. Vanilla player code branches on `IsInVehicle()` (declared on `DayZPlayerImplement`, `P:\scripts\4_world\entities\dayzplayerimplement.c:468`); for example `PlayerBase.CanReceiveItemIntoHands` returns `false` while it is true (`P:\scripts\4_world\entities\manbase\playerbase.c:2284`). A rider who reports `false` is treated as on foot and can raise and fire. That this override alone unlocks raising and firing is the mod's behaviour, not checked on `P:\`.

## The pieces

1. Attach without a crew seat with `LinkToLocalSpaceOf` (`P:\scripts\3_game\human.c:1391`), computing the local matrix from a model-space anchor, and undo it on exit with `UnlinkFromLocalSpace` (`:1392`):

   ```c
   GetTransform(playerWorld);
   playerWorld[3] = trans.ModelToWorld(modelSpaceAnchor);
   trans.GetTransform(vehWorld);
   Math3D.MatrixInvMultiply4(vehWorld, playerWorld, local);
   SetTransform(local);
   LinkToLocalSpaceOf(trans, local);   // the rider now moves with the vehicle
   ```

2. Freeze the rider's body with `dBodyEnableGravity(this, false)` (`P:\scripts\1_core\proto\enphysics.c:69`) and `dBodyActive(this, ActiveState.INACTIVE)` (`:64`), applied again every tick in `CommandHandler` because the engine wakes the body. Without it the rider falls or is knocked off by the moving collider.

3. Freeze movement with a `HumanCommandScript` subclass (`P:\scripts\3_game\human.c:1236`), started with `StartCommand_Script` (`:1623`) and issued again every tick:

   ```c
   class MyMod_GunnerCommand extends HumanCommandScript
   {
       PlayerBase m_User;
       int m_Stance;

       void MyMod_GunnerCommand(PlayerBase p, int stance)
       {
           m_User = p;
           m_Stance = stance;
       }

       override void OnActivate()
       {
           HumanAnimInterface hai = m_User.GetAnimInterface();
           int v = hai.BindVariableInt("Stance");
           PreAnim_SetInt(v, m_Stance);   // force the pose, nothing else
       }
   }
   ```

   A scripted command replaces normal locomotion. This one overrides only `OnActivate` and has no `OnUpdate`, `PrePhysUpdate` or `PostPhysUpdate`, so no walk logic runs: the rider can turn, aim and fire but not move.

4. Ignore damage from the rider's own vehicle: `EEOnDamageCalculated` returns `false` when the source is the gunner's transport, or riding logs collision damage.

5. Lock movement input on the client: from `MissionGameplay.OnUpdate`, every movement input gets `UAInput.ForceDisable(true)` while the player is a gunner, and `UATempRaiseWeapon` is enabled only with a `Weapon` in hands. The mod's forward and back shuffle has its movement commented out and is dead code.

6. Leash: every frame, measure `vector.Distance(player, trans.ModelToWorld(anchor))`; past the slot's `distance`, a server RPC snaps the rider back. This catches physics drift that input locks cannot.

7. Camera and stance: force first or third person per slot, block the view toggle while the weapon is raised, and block prone and crouch changes that would push the rider through the vehicle.

## Seated and attached gunners

- Seated gunner: a real crew seat through `StartCommand_Vehicle(transport, seat, GetSeatAnimationType(seat))` (`P:\scripts\3_game\human.c:1526`), with the weapon allowed.
- Attached gunner: the link and the scripted freeze above, rooted at an anchor.

Both run through `PlayerBase.ModCommandHandlerBefore` as a queue of transitions: board seat, exit, seat to gunner, gunner from outside, exit gunner. On exit the rider is placed at the vehicle's own crew point, not a fixed spot: `ConfigGetChildName` on `CfgVehicles <type> Crew` gives the seat class, `ConfigGetText` on its `getInPos` gives the memory point, then `GetMemoryPointPos`, `ModelToWorld` and `SetPosition`.

Synced state: one bool on the player for the gunner state (`RegisterNetSyncVariableBool`) and one int per car or boat holding a bit per seat (`RegisterNetSyncVariableInt`), set from JSON in `EEInit`.

## Per-vehicle settings

A JSON file under `$profile:`, keyed by vehicle type, holds up to ten slots (`gunner1` to `gunner10`). Each slot has `type` (0 is off), `camera` (force first person, toggle, or force third person), `distance` (the leash), `stance`, and `pos`, `pos_auto` and `dir` (the anchor and facing in model space). The `collision`, `intersect`, `script_collision` and `move` fields belong to the disabled shuffle. `CarScript.EEInit` loads the slots for `GetType()` from a global map synced to clients by RPC.

The mod requires `DZ_Data`, `DZ_Vehicles_Wheeled` and `DZ_Vehicles_Water`, so it covers cars and boats; `CarScript` and `BoatScript` are modded the same way.

## Weaknesses to fix in your own version

- The rider cannot reposition. Stepping along the bed is new work: a move command in the vehicle's frame that respects the leash, not a setting.
- The input lock and the leash run on the client; the server only snaps back past the radius. If you add movement, check it on the server with a throttled raycast (every 200 to 300 ms, not every frame, or many gunners cost server frame rate).
- Firing makes only the weapon's own noise; a truck full of shooters is as loud as one rifle. Call `AddNoiseTarget` (`P:\scripts\3_game\noise.c:10`) if infected should react.
- Aim is the same parked and at 80 km/h. Sway that reads the `Transport` speed adds depth.
- Fighting the engine every frame with a link and an inactive body is fragile; a hard hit can throw the rider off, which is why the leash exists. Re-link defensively on `EOnContact`, or make it a feature: a ragdoll throw above an impact speed.

## Related

- The RPC dispatch with one fixed id and a function name: `_shared/enscript/depth/rpc-manager-and-cf.md`, section "One ID and a function name".
- Pose command work: `/dayz-animation-pipeline`.
