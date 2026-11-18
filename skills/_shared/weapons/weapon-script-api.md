# Weapon script calls

Covers the script calls around a firearm: spawning it loaded, reading its state, the state machine it carries, the firearm actions, and the calls that changed in DayZ 1.30. Class parents are in `weapon-classes.md`; magazines and ammo are in `magazines-ammo.md`.

Short citations name files under `P:\scripts\4_world\entities\firearms\` unless a full path is given.

## Spawning a loaded weapon

- `Weapon_Base.CreateWeaponWithAmmo(string weaponType, string magazineType = "", int flags = WeaponWithAmmoFlags.CHAMBER)` is static: it creates the weapon with `CreateObjectEx` and then calls `SpawnAmmo` on it (`P:\scripts\4_world\entities\firearms\weapon_base.c:720`).
- `SpawnAmmo(string magazineType = "", int flags = WeaponWithAmmoFlags.CHAMBER)` loads a weapon that already exists: it fills an internal magazine or attaches one, and fills the chamber (`P:\scripts\4_world\entities\firearms\weapon_base.c:740`). An empty magazine type lets the game pick one.
- `flags` is a bit mask of `WeaponWithAmmoFlags` (`P:\scripts\4_world\entities\firearms\weapon_base.c:11` to `:29`):

| Flag | Value | Meaning |
|---|---|---|
| `NONE` | 0 | Full magazine, nothing chambered. |
| `CHAMBER` | 1 | Chamber a round. |
| `CHAMBER_RNG` | 2 | Maybe chamber, chance applied in sequence (for example 1 1 1 0 0 0). |
| `CHAMBER_RNG_SPORADIC` | 4 | Maybe chamber, an independent chance per chamber (for example 0 1 0 0 1 1). |
| `QUANTITY_RNG` | 8 | Random round count in the magazine. |
| `AMMO_MAG_RNG` | 16 | Random ammo type per round in the magazine; the type must be an empty string. |
| `AMMO_CHAMBER_RNG` | 32 | Random ammo type per chamber; the type must be an empty string. |
| `MAX_CAPACITY_MAG` | 64 | With an empty type, pick the magazine with the highest capacity instead of a random one. |

- Presets on `Weapon_Base`: `SAMF_DEFAULT` is `CHAMBER | MAX_CAPACITY_MAG` and `SAMF_RNG` is `CHAMBER_RNG | QUANTITY_RNG` (`P:\scripts\4_world\entities\firearms\weapon_base.c:41`, `:43`).

Spawn on the server only.

## Reading a weapon's state

- On `Weapon` (`P:\scripts\4_world\entities\core\inherited\weapon.c`): `GetInternalMagazineCartridgeCount(int muzzleIndex)` (`:111`) and `GetMagazine(int muzzleIndex)` (`:240`).
- On `Weapon_Base`: `IsJammed()` (`weapon_base.c:399`); `CanFire()` (`weapon_base.c:1262`), which is true when the current chamber is loaded and not fired out and the weapon is not jammed, not lifted against a wall and not ruined; `OnFire(int muzzle_index)` (`weapon_base.c:1020`); `OnFireModeChange(int fireMode)` (`weapon_base.c:1048`); `EEFired(int muzzleType, int mode, string ammoType)` (`weapon_base.c:341`).

## The state machine

- `Weapon_Base` owns it (`P:\scripts\4_world\entities\firearms\weapon_base.c:48` to `:55`): `m_abilities` (`:48`), `m_fsm` (`:49`), `m_isJammed` (`:50`), `m_Charged` (`:54`), `m_WeaponOpen` (`:55`); `m_ChanceToJam` is at `:72`.
- Each mechanism base fills it in `InitStateMachine`. `RifleBoltFree_Base` (`P:\scripts\4_world\entities\firearms\rifleboltfree_base.c:106`) has the stable states `C00`, `C10`, `C11`, `C01`, `JF0` and `JF1` (`:94` to `:99`). The vanilla comment names the pattern `[CLJ][01][01]`: closed, locked or jammed; no bullet or bullet; no magazine or magazine (`:128` to `:129`). It adds ability records for reload (`:109` to `:113`), chambering (`:115`), mechanism (`:117`), unjamming start and end (`:119` to `:120`) and fire jam, normal and dry (`:122` to `:124`).
- `ValidateAndRepair()` asks the state machine to check itself against the weapon's real contents and fix its state (`P:\scripts\4_world\entities\firearms\weapon_base.c:1078`). Vanilla calls it when the weapon enters an inventory (`:1084` to `:1097`) and, since 1.30, when a magazine is detached: `EEItemDetached` calls it if `item.IsMagazine()` (`P:\scripts\4_world\entities\firearms\weapon_base.c:1115` to `:1121`).

### Pistol animation states (since 1.30)

`Pistol_Base.InitStateMachine` passes the animation state of each stable state through four virtual getters: `GetDischargedPistolAnimState()`, `GetChargedPistolAnimState()`, `GetOpenPistolAnimState()` and `GetJammedPistolAnimState()` (`P:\scripts\4_world\entities\firearms\pistol_base.c:203` to `:212`; defined at `:611` to `:629`). They return values of `enum PistolAnimState` (`P:\scripts\4_world\entities\firearms\pistol_base.c:2` to `:8`): `DEFAULT` 0, `OPENED_DISCHARGED` 1, `CLOSED_CHARGED` 2, `JAMMED` 3. A pistol whose slide behaves differently overrides the getters and keeps the stock state machine, as the Luger does (`P:\scripts\4_world\entities\firearms\pistol\luger.c:8` to `:21`).

The pistol has ten stable states, named on the vanilla pattern `[OC][CDJ][01][01]`: slide open or closed; discharged, charged or jammed; no bullet or bullet; no magazine or magazine (`P:\scripts\4_world\entities\firearms\pistol_base.c:199` to `:202`). The closed states take the discharged, charged or jammed getter and the two open states (`OD00`, `OD01`) take the open getter (`:203` to `:212`). Jammed states exist only with a bullet in the chamber (`CJF0`, `CJF1`), and open states only discharged with no bullet. When a custom pistol's slide looks wrong in one situation, find that situation's state here first, then override the one getter it uses.

## Firearm actions

The action classes are in `P:\scripts\4_world\classes\useractionscomponent\actions\weapons\`:

| File | Classes |
|---|---|
| `firearmactionattachmagazine.c` | `FirearmActionAttachMagazine` (`:11`), `FirearmActionAttachMagazineQuick` (`:225`) |
| `firearmactiondetachmagazine.c` | `FirearmActionDetachMagazine` (`:151`); the old `FirearmActionDetachMagazine_Old` (`:14`) is marked obsolete since 1.30 |
| `firearmactionloadbullet.c` | `FirearmActionLoadBullet` (`:1`), `FirearmActionLoadBulletQuick` (`:82`) |
| `firearmactionloadmultibullet.c` | `FirearmActionLoadMultiBullet` (`:1`), `FirearmActionLoadMultiBulletQuick` (`:94`), `FirearmActionLoadMultiBulletRadial` (`:171`) |
| `firearmactionmechanicmanipulate.c` | `FirearmActionMechanicManipulate` (`:1`) |
| `firearmactionunjam.c` | `FirearmActionUnjam` (`:1`) |

Changes in 1.30:

- The quick attach action used for quick reload, `FirearmActionAttachMagazineQuick` (`P:\scripts\4_world\classes\useractionscomponent\actions\weapons\firearmactionattachmagazine.c:225`), requires `weapon.TestAttachMagazine(weapon.GetCurrentMuzzle(), mag, false, true)` in its condition (`:256`). A mod that overrides `TestAttachMagazine` and gets this case wrong stops the quick reload from starting. The plain `FirearmActionAttachMagazine` condition checks `WeaponManager.CanAttachMagazine` or `CanSwapMagazine` instead (`:26` to `:35`).
- `FirearmActionDetachMagazine` extends `ActionSequentialBase` (`P:\scripts\4_world\classes\useractionscomponent\actions\weapons\firearmactiondetachmagazine.c:151`) and can be performed from the inventory (`:262` to `:265`).
- `OpenBolt_Base.SetActions()` removes the load bullet actions and adds `FirearmActionDetachMagazine` (`P:\scripts\4_world\entities\firearms\openbolt_base.c:382` to `:389`), so an open bolt gun needs no workaround to drop its magazine.

## Taking a round from the magazine

The state machine helper that chambers from the attached magazine calls `mag.LocalAcquireCartridgeEx(damage, type)` (`P:\scripts\4_world\entities\firearms\fsm\weapon_utils.c:9`). `LocalAcquireCartridgeEx` wraps the proto `LocalAcquireCartridge` and then calls `UpdateAnimation()` (`P:\scripts\4_world\entities\itembase\magazine\magazine.c:180` to `:185`; the proto is at `:79`), which is what moves the MP18 drum (see `magazines-ammo.md`). Use the `Ex` call in a custom chamber helper. DayZ 1.29 called `LocalAcquireCartridge` there (the 1.29 scripts are not on `P:\`, so this is not checked).

## Explosion effects (changed in 1.30)

- `AmmoTypesAPI.GetExplosiveEffectData(string ammoName, string surfaceName)` returns an `ExplosiveEffectData` with `m_ParticleID` and `m_SoundSetName` (`P:\scripts\3_game\global\ammotypes.c:90`; the class is at `P:\scripts\3_game\global\ammotypes.c:1`). It returns null when `NO_GUI` is defined, so check the result on a server build.
- Vanilla reads the surface with `SurfaceGetType3D` and then asks for the effect (`P:\scripts\3_game\ammoeffects.c:49` to `:56`); the explosion code also starts the sound set with `SetStartSoundParams` (`P:\scripts\3_game\dayzgame.c:3634` to `:3638`).
- Effects are registered per ammo and surface with `AddExplosionParticleEffect` (`P:\scripts\3_game\global\ammotypes.c:78`), for example the RGD5 grenade on `Hit_Desert_Sand` with `"ExplosionDustEffect_SoundSet"` (`:66`).
- `GetExplosionParticleID`, the 1.29 call (the 1.29 scripts are not on `P:\`, so its old form is not checked), is gone: no file under `P:\scripts` contains the name. A mod that still calls it does not compile.
- On `ExplosivesBase`, `SetParticleExplosion`, both `AddExplosionEffectForSurface` overloads, `m_TypeToSurfaceParticleIDMap` and `InitSpecificsExplosionEffectForSurface` are marked `[Obsolete("1.30: Handled in AmmoTypes instead")]` (`P:\scripts\4_world\entities\explosivesbase.c:306`, `:386`, `:432`, `:40`, `:380`). Set `particle` on the `CfgAmmo` class instead of keeping a script map from surface to particle.

The official 1.30 modding changelog also names `SoundHitType` and `SurfaceInfo.GetSoundHitType()`. Neither exists in `P:\scripts\3_game\surfaceinfo.c` or anywhere else under `P:\scripts`; do not call them.

## Where a swapped magazine lands

When a magazine swap cannot put the old magazine in the inventory, `WeaponManager` drops it on the ground with an orientation built from the player's orientation (`Math3D.YawPitchRollMatrix`, `Math3D.MatrixToQuat`, then `SetGroundEx`, `P:\scripts\4_world\classes\weapons\weaponmanager.c:1364` to `:1368`). DayZ 1.29 passed an unset `dir` array there (the 1.29 scripts are not on `P:\`, so not checked); a mod that copied the 1.29 block should take the 1.30 one.

## Measured lessons in this pack

What was measured in game on custom firearms lives in the topic files: the selection, memory point and bone remap checks in `model-selections.md`, the fire mode scope trap in `weapon-config.md`, the mesh import in `model-import.md`, and a symptom table in `troubleshooting.md`.
