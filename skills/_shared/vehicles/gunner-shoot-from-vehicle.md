# Gunner, shoot from a vehicle: the attached-rider pattern (SIBNIC)

How a rider can fire their own handheld weapon from a moving car or boat: the player is linked to the vehicle at an anchor, frozen by a scripted human command, and reports that they are not in a vehicle.

> Status: every fact about the third-party mod Gunner_SIB_NIC v2.61 (author SIBNIC) comes from the notes' author reading its recovered scripts on 2026-07-07; none of it is checked on `P:\`, and the mod's files are not part of this repo. The `unknown_NNNN.c:line` references are file names in that recovered script tree. A citation written with its full `P:\` path was opened on the vanilla data of this repo. A citation without `P:\` keeps the line number the note was written with, for the DayZ build that entry names, and is not yet checked on `P:\`: Grep for the symbol before relying on the number. The vanilla methods the pattern is built from are in the anchors below.

## Vanilla anchors checked on `P:\`

- `LinkToLocalSpaceOf` is native on `Human`: `P:\scripts\3_game\human.c:1391`.
- `HumanCommandScript` is the scripted command base class: `P:\scripts\3_game\human.c:1236`.
- `StartCommand_Script` starts one: `P:\scripts\3_game\human.c:1623`.
- `IsInVehicle` is declared on `DayZPlayerImplement`, the parent of `PlayerBase`: `P:\scripts\4_world\entities\dayzplayerimplement.c:468`.
- `UnlinkFromLocalSpace` undoes the link: `P:\scripts\3_game\human.c:1392`.
- `dBodyActive` sets the active state of a body: `P:\scripts\1_core\proto\enphysics.c:64`.
- `dBodyEnableGravity` switches gravity on a body: `P:\scripts\1_core\proto\enphysics.c:69`.

## The pattern in one paragraph

> How to let a player **fire their own handheld weapon while riding a moving vehicle**. The player is
> **rooted to an anchor point** (standing/crouch in the vehicle bed or boat deck) — they aim and fire but
> do NOT walk around (the freeze is the whole point, piece #3). Distilled from reverse-engineering
> **Gunner_SIB_NIC v2.61** (author SIBNIC, JAPM-obfuscated, recovered 2026-07-07, findings f_002 to f_015 of that extraction). Study source only — not
> forkable (obfuscated + signed + license-gated heli half). Evidence paths below are file names in the
> recovered script tree of that extraction. Obfuscated identifiers are named by role.
>
> This is the **handheld attached-gunner** family. For a **fixed vehicle turret** (its own `CfgMagazines`/
> `CfgAmmo`, `ProcessDirectDamage`), that is a different recipe — the BRDM vehicle-weapon pattern of the
> author's own notes (`vehicle-weapon-system.md`, not part of this repo). They compose: one
> technical can carry both.

## The one trick that makes it work

**`PlayerBase.IsInVehicle()` overridden to return `false` while the gunner state is active.**
`unknown_16371.c:218-226`. DayZ gates weapon raise/fire on the player NOT being in a vehicle. A player who
is physically riding the vehicle but reports `IsInVehicle()==false` is treated as on-foot → can raise and
fire normally. Everything else is scaffolding around this lie.

## The seven pieces

1. **Attach without a crew seat** — `LinkToLocalSpaceOf(trans, localMatrix)`. `unknown_16371.c:80-90`.
   Compute the local matrix from the model-space anchor:
   ```
   GetTransform(playerWorld);
   playerWorld[3] = trans.ModelToWorld(modelSpaceAnchor);
   trans.GetTransform(vehWorld);
   Math3D.MatrixInvMultiply4(vehWorld, playerWorld, local);
   SetTransform(local);
   LinkToLocalSpaceOf(trans, local);      // rider now moves WITH the vehicle
   ```
   `UnlinkFromLocalSpace()` on exit (`:66`). Same primitive DayZ uses for ladders/attached entities.

2. **Freeze rider physics** — `dBodyEnableGravity(this,false)` + `dBodyActive(this, ActiveState.INACTIVE)`.
   `unknown_16371.c:70-73`, re-asserted in `CommandHandler` (`:165-169`) because the engine re-activates
   the body. Without it the rider falls or gets punted by the moving collider.

3. **The freeze — `HumanGunnerCommand` (this is why the player can't walk)** —
   `StartCommand_Script(new HumanGunnerCommand(this, stanceParam))`, `unknown_16371.c:55-59`, re-issued
   from `CommandHandler` every tick (`:148-185`). The class (recovered by brute-force decompress; the
   extractor's size filter had dropped it):
   ```c
   class HumanGunnerCommand extends HumanCommandScript {
       PlayerBase m_user; int m_stance;
       void HumanGunnerCommand(PlayerBase p, int stance) { m_user = p; m_stance = stance; }
       override void OnActivate() {
           HumanAnimInterface hai = m_user.GetAnimInterface();
           int v = hai.BindVariableInt("Stance");
           if (m_stance >= threshold) PreAnim_SetInt(v, m_stance);   // force the pose — that is ALL
       }
   };
   ```
   `StartCommand_Script` puts the player into a **fully scripted human command that replaces normal
   locomotion**. This subclass overrides only `OnActivate` (bind + force the `Stance` anim var) with **no
   `OnUpdate`/`PrePhysUpdate`/`PostPhysUpdate`** → the engine runs no walk logic → the player is
   **animation-locked in the stance**: free to rotate/aim and fire, but cannot translate. This is the
   anti-movement mechanism. Reimplementing is easy — a tiny `HumanCommandScript` that only sets stance.

4. **Self-transport damage immunity** — `EEOnDamageCalculated` returns `false` when
   `source == m_gunner_transport`. `unknown_16371.c:42-53`. Riding your own vehicle otherwise logs
   collision damage.

5. **Input controller — locks movement (client), does NOT enable walking** — `MissionGameplay.OnUpdate`
   → per-frame, `unknown_18413.c:225-711`. Every movement key is `UAInput.ForceDisable(true)` while gunner
   (belt-and-suspenders on top of the #3 command freeze). `UATempRaiseWeapon` enabled only when a `Weapon`
   is in hands (`:315-339`). **Do not mistake the W/S raycast block (`:475-701`) for live walk logic:** it
   raycasts floor/obstacle and re-enables the Forward/Back key, but the actual movement — a teleport
   between the `//tp start`/`//tp end` markers (`:617-621`, `:687-691`) — is **commented out**, and a
   `HumanCommandScript` ignores locomotion input anyway. It is dead code from a reposition feature SIBNIC
   pulled. Net: the player is stationary.

6. **Leash / tether** — each frame measure `vector.Distance(player, trans.ModelToWorld(anchor))`; if it
   exceeds the slot's `distance`, fire a server RPC (`Gunner_FixPos_Server`) to snap the player home.
   `unknown_18413.c:381-415,593-609`. Catches the rider when physics drift moves them off the anchor even
   though input is locked.

7. **Camera + stance control** — `CameraHandler` forces `m_Camera3rdPerson` per slot camera mode;
   `HandleView` toggles on `CameraViewChanged()` but suppresses the flip while the weapon is raised
   (`unknown_16371.c:259-308`). `CanChangeStance` blocks prone/crouch transitions that would clip the
   rider through the vehicle (`:187-217`).

## Two flavors, one config

- **Seated gunner** (`custom_seat=true`): a *real* crew seat via `StartCommand_Vehicle(transport, seat,
  GetSeatAnimationType(seat))`, weapon unlocked. Classic turret seat.
- **Attached gunner** (`custom_seat=false`): `LinkToLocalSpace` attach + `HumanGunnerCommand` freeze at an
  anchor. Rooted in place (not seated, not walking). The innovative one.

Both flow through `PlayerBase.ModCommandHandlerBefore` as a queued-transition state machine
(`unknown_9224.c:12-213`): board seat / exit / board-gunner-from-seat / board-gunner-standalone /
exit-gunner. **Exit restores position from the vehicle's own crew memory point**, not a hardcoded spot:
`ConfigGetChildName(CfgVehicles <type> Crew, seatIdx, seatClass)` → `ConfigGetText(... Crew <seat>
getInPos)` → `GetMemoryPointPos` → `ModelToWorld` → `SetPosition` (`unknown_9224.c:181-192`).

Sync vars: `m_gunner_current_to_seat_costom` (`RegisterNetSyncVariableBool`, `unknown_16371.c:14`);
per-seat permission bitmasks `m_lock_in_out` / `m_lock_in_out_gunner` on Car/Boat
(`RegisterNetSyncVariableInt`, `unknown_10583.c:9-10`), one bit per seat, set from JSON in `EEInit`.

## Per-vehicle JSON (`Json_gunner_sib`)

`unknown_11478.c:8-224`. A `$profile:` JSON keyed by vehicle **type**, up to **10 slots**
(`gunner1..gunner10`). Per slot: `type` (0=off), `collision`/`intersect`/`script_collision` (checks for the
disabled reposition), `camera` (force-1st/toggle/force-3rd), `distance` (leash), `stance`, `move` (gated the
disabled forward/back reposition; player is fixed in v2.61), `pos`/`pos_auto`/`dir` (model-space anchor +
facing). `CarScript.EEInit` loads the slot config for
`GetType()` from a global map and sets the seat lock bits; the map is synced to clients via an
`UpdateGunnerMass_Client` RPC.

## Scope + requirements

`CfgPatches.requiredAddons = DZ_Data, DZ_Vehicles_Wheeled, DZ_Vehicles_Water` (`unknown_952.c:61`) —
**cars + boats**. Both `CarScript` and `BoatScript` are modded identically (`Transport` sibling
contract). Config is script-side (`CfgMods` + `CfgPatches`), no `config.bin`.

## Known weaknesses (fix these if you reimplement)

- **Player is fixed — no reposition.** The gunner is rooted to the anchor; SIBNIC's forward/back shuffle is
  commented out (teleport-on-a-moving-platform desyncs). A real "step along the bed" ability is net-new work
  (a `HumanCommandMove`-style command that respects the vehicle-local frame + leash), not a config toggle.
- **Client-side safety net.** The freeze is engine-enforced (scripted command), but the input suppression +
  leash monitor run client-side; the only server correction is the `Gunner_FixPos_Server` radius snap. If
  you add repositioning, validate it server-side on a **throttled** raycast (200-300 ms, budget scheduler —
  not per frame; N gunners would tank server FPS).
- **No fire noise at vehicle level.** Firing is vanilla per-weapon; a technical full of shooters is as
  loud as one rifle. Add `NoiseSystem.AddNoiseTarget` (BRDM pattern) if you want infected to respond.
- **No move-speed aim penalty.** You aim identically at 80 km/h and parked. A velocity-informed sway
  (read the `Transport` speed) adds tactical depth.
- **`LinkToLocalSpace` + `dBodyActive(INACTIVE)` fragility.** Fought every frame; a hard collision can pop
  the rider off — that's why the leash exists. Consider a defensive re-link on `EOnContact`, or turn it
  into a feature (thrown-off ragdoll above an impact-speed threshold).

## Cross-references

- `vehicle-weapon-system.md` (the author's own note, not part of this repo) — the fixed-turret sibling pattern.
- RPC dispatch bus used here (single fixed id + string function name) → the enforce-script-reference skill
  ("Single-ID string-dispatch RPC bus (RPCManager)").
- Pose command work → the dayz-animation-pipeline skill (`HumanCommandScript`, rider IK).
- Vehicle recovery of another SIBNIC mod → the author's own research index (not part of this repo).
