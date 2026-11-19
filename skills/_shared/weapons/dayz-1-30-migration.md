# Moving a weapon mod to DayZ 1.30

What breaks when a weapon mod written for 1.29 runs on 1.30, the checks to make when moving it, and where the four weapons 1.30 adds live in the data. Each 1.30 fact lives in its topic file; this file links to it.

## What breaks

- A call to `AmmoTypesAPI.GetExplosionParticleID` no longer compiles (`weapon-script-api.md`, "Explosion effects").
- Quick reload never starts when a `TestAttachMagazine` override refuses the quick case (`weapon-script-api.md`, "Firearm actions").
- A workaround that lets an open bolt gun drop its magazine now fights `FirearmActionDetachMagazine`, which `OpenBolt_Base` registers itself (`P:\scripts\4_world\entities\firearms\openbolt_base.c:382` to `:389`).
- Spawning `SCARL`, `Luger`, `LeeEnfield`, `MP18` or their magazines fails on a server whose data has no config class for them ("The four new weapons" below).
- The official 1.30 modding changelog names `SoundHitType` and `GetSoundHitType()`, but neither exists in the scripts (`weapon-script-api.md`).

## Checklist

- [ ] Replace explosion particle lookups with `AmmoTypesAPI.GetExplosiveEffectData(ammoType, surfaceType)`.
- [ ] Drop `SetParticleExplosion` and script maps from surface to particle; set `particle` on the `CfgAmmo` class.
- [ ] For an unusual pistol, override the `Get*PistolAnimState()` getters and keep the stock pistol state machine (`weapon-script-api.md`, "Pistol animation states").
- [ ] Check `TestAttachMagazine` overrides against custom magazine and bolt states.
- [ ] Use `LocalAcquireCartridgeEx` in custom chamber helpers (`weapon-script-api.md`, "Taking a round from the magazine").
- [ ] Take the 1.30 magazine drop block if the mod copied the 1.29 one (`weapon-script-api.md`, "Where a swapped magazine lands").
- [ ] To inherit a 1.30 weapon, put its `CfgPatches` class in `requiredAddons[]` (below).
- [ ] List the four new weapons in `types.xml` only when the server's data has their config classes.

## The four new weapons

Their script classes, parents and hand profiles are in `weapon-classes.md`, "Script classes for the 1.30 weapons"; their recoil classes in `recoil-fire-modes.md`; their bone remaps in `model-selections.md`; the bayonet in `attachments.md`; the MP18 drum in `magazines-ammo.md`.

Their config and models are under `P:\DZ\weapons_takistan\`, not under `P:\DZ\weapons\`. The config parent is not always the script parent: `SCARL_Base` and `MP18_Base` both inherit `Rifle_Base` in config, while their script classes extend `SCARH_Base` and `OpenBolt_Base`.

| Classes (scope 2) | Config parent | Config | Addon to require | Model |
|---|---|---|---|---|
| `SCARL`, `SCARL_Black` | `SCARL_Base: Rifle_Base` | `P:\DZ\weapons_takistan\firearms\scarl\config.cpp:26`, `:278`, `:361` | `DZ_Weapons_Nasdara_Firearms_SCARL` (`:3`) | `scarl.p3d` (`:281`) |
| `LeeEnfield` | `LeeEnfield_Base: BoltActionRifle_ExternalMagazine_Base` | `P:\DZ\weapons_takistan\firearms\leeenfield\config.cpp:27`, `:172` | `DZ_Weapons_Nasdara_Firearms_LeeEnfield` (`:3`) | `leeenfield.p3d` (`:177`) |
| `MP18` | `MP18_Base: Rifle_Base` | `P:\DZ\weapons_takistan\firearms\mp18\config.cpp:26`, `:196` | `DZ_Weapons_Nasdara_Firearms_mp18` (`:3`) | `mp18.p3d` (`:201`) |
| `Luger` | `Luger_Base: Pistol_Base` | `P:\DZ\weapons_takistan\pistols\luger\config.cpp:26`, `:170` | `DZ_Pistols_Nasdara_Luger` (`:3`) | `luger.p3d` (`:179`) |
| `Mag_Luger_8Rnd` (8 rounds), `Mag_MP18_Drum32Rnd` (32), `Mag_LeeEnfield_10Rnd` (10) | `Magazine_Base` | `P:\DZ\weapons_takistan\attachments\magazine\config.cpp:21`, `:158`, `:316` | `DZ_Weapons_Nasdara_Magazines` (`:3`) | `magazine_*.p3d` in the same folder |
| `P1907_Bayonet` | `Inventory_Base`; `inventorySlot[]` holds `weaponBayonetLeeEnfield` and `Knife` (`:38` to `:42`) | `P:\DZ\weapons_takistan\attachments\muzzle\config.cpp:21` | `DZ_Weapons_Nasdara_Muzzle` (`:3`) | `bayonet_p1907.p3d` (`:26`) |

The Luger and the MP18 take the same two magazines, the Luger box and the MP18 drum (`P:\DZ\weapons_takistan\pistols\luger\config.cpp:41` to `:45`; `P:\DZ\weapons_takistan\firearms\mp18\config.cpp:43` to `:47`), and the Lee-Enfield offers the bayonet slot (`P:\DZ\weapons_takistan\firearms\leeenfield\config.cpp:181`). The models are binarized like every vanilla weapon model on `P:\`, so compare against them through config and script, as for any vanilla gun (`troubleshooting.md`).

For an open bolt SMG of your own, the MP18 and the PM73 RAK are the vanilla open bolt guns (`PM73Rak_Base extends OpenBolt_Base`, `P:\scripts\4_world\entities\firearms\smg\pm73rak.c:5`). The CZ61 is closed bolt (`CZ61_Base : RifleBoltLock_Base`, `P:\scripts\4_world\entities\firearms\smg\cz61.c:4`), so it is the wrong base.

## Loot

The `types.xml` of Chernarus, Livonia and Sakhal list the new class names with a nominal of 0 (`SCARL` at `P:\DZ\worlds\chernarusplus\ce\db\types.xml:19815`, `P:\DZ\worlds\enoch\ce\db\types.xml:19378` and `P:\DZ\worlds\sakhal\ce\db\types.xml:19934`), except `SCARL_Black`, which Livonia gives 4 (`enoch\ce\db\types.xml:19390`). Nasdara spawns them (`P:\DZ\worlds\nasdara\ce\db\types.xml`): `LeeEnfield` 30 (`:13908`), `Luger` 55 (`:14090`), `MP18` 35 (`:14541`), `SCARL` 4 (`:20086`), `SCARL_Black` 0 (`:20100`), `Mag_LeeEnfield_10Rnd` 33 (`:14997`), `Mag_Luger_8Rnd` 75 (`:15014`), `Mag_MP18_Drum32Rnd` 38 (`:15068`) and `P1907_Bayonet` 30 (`:17916`). Spawning them in game is not yet tested.
