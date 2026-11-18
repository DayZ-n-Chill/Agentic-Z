# Moving a weapon mod to DayZ 1.30

What breaks in a weapon mod written for 1.29, the checklist for moving it, and where the four weapons added in 1.30 live. Each 1.30 fact sits in its topic file; this file links to it.

## What breaks

1. A call to `AmmoTypesAPI.GetExplosionParticleID` no longer compiles (`weapon-script-api.md`, "Explosion effects").
2. Quick reload never starts when a `TestAttachMagazine` override refuses the quick case (`weapon-script-api.md`, "Firearm actions").
3. A workaround that lets an open bolt gun drop its magazine now fights the detach action `FirearmActionDetachMagazine` that `OpenBolt_Base` registers itself (`P:\scripts\4_world\entities\firearms\openbolt_base.c:382-389`).
4. Spawning `SCARL`, `Luger`, `LeeEnfield`, `MP18` or their magazines fails on data that has no config class for them (below).
5. The official 1.30 modding changelog names `SoundHitType` and `GetSoundHitType()`, which do not exist in the scripts (`weapon-script-api.md`).

## Checklist

- [ ] Replace explosion particle lookups with `AmmoTypesAPI.GetExplosiveEffectData(ammoType, surfaceType)`.
- [ ] Drop `SetParticleExplosion` and script maps from surface to particle; set `particle` on the `CfgAmmo` class.
- [ ] Unusual pistols: override the `Get*PistolAnimState()` getters and keep the stock pistol state machine (`weapon-script-api.md`, "Pistol animation states").
- [ ] Check `TestAttachMagazine` overrides against custom magazine and bolt states.
- [ ] Use `LocalAcquireCartridgeEx` in custom chamber helpers (`weapon-script-api.md`, "Taking a round from the magazine").
- [ ] Take the 1.30 magazine drop block if the mod copied the 1.29 one (`weapon-script-api.md`, "Where a swapped magazine lands").
- [ ] Compare against a model that ships in the data you have (below).
- [ ] List the four new weapons in `types.xml` only when the server's data has their config classes.

## The four 1.30 weapons

Their script classes, parents and hand profiles are in `weapon-classes.md`, "Script classes with no model or config class"; their recoil classes in `recoil-fire-modes.md`; their bone remaps in `model-selections.md`; the bayonet in `attachments.md`; the MP18 drum in `magazines-ammo.md`.

The vanilla data on `P:\` has no model or config class for them. Build on a weapon that ships there instead:

| New weapon | Script parent | Shipped reference on `P:\` |
|---|---|---|
| `SCARL_Base` | `SCARH_Base` | The SCAR-H, `class SCARH_Base: Rifle_Base` (`P:\DZ\weapons\firearms\scarh\config.cpp:26`), with its model `P:\DZ\weapons\firearms\scarh\scarh.p3d`. Inherit that config, then change `chamberableFrom[]`, `magazines[]` and the script recoil. Its hand profile is the SCAR-H's (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:444`, `:445`). |
| `MP18_Base` | `OpenBolt_Base` | The PM73 RAK, the vanilla open bolt SMG (`PM73Rak_Base extends OpenBolt_Base`, `P:\scripts\4_world\entities\firearms\smg\pm73rak.c:5`; config at `P:\DZ\weapons\firearms\pm73rak\config.cpp:26`). The CZ61 is closed bolt (`CZ61_Base : RifleBoltLock_Base`, `P:\scripts\4_world\entities\firearms\smg\cz61.c:4`). |
| `LeeEnfield_Base` | `BoltActionRifle_ExternalMagazine_Base` | The CZ527 (`P:\DZ\weapons\firearms\cz527\config.cpp:31`) for a detachable magazine bolt action. |
| `Luger_Base` | `Pistol_Base` | A pistol that ships, such as the P1 (`P1_Base`; its fire mode `class Single: Mode_SemiAuto` is at `P:\DZ\weapons\pistols\p1\config.cpp:64`). |

### Game build 1.30.164200

That build ships the four weapons, their magazines and the bayonet in `nasdara\addons\weapons_nasdara.pbo` (prefix `DZ\weapons_takistan`), read from the PBO header of an installed DayZ Server. The PBO is not unpacked on `P:\`, so the classes below come from its derapified configs and are not yet checked on `P:\` (paths relative to `DZ\weapons_takistan\`):

| Classes (scope 2) | Config parent | Config | Model |
|---|---|---|---|
| `SCARL`, `SCARL_Black` | `SCARL_Base: Rifle_Base` | `firearms\SCARL\config.cpp:40`, `:202`, `:222` | `firearms\SCARL\ScarL.p3d` |
| `LeeEnfield` | `LeeEnfield_Base: BoltActionRifle_ExternalMagazine_Base` | `firearms\leeEnfield\config.cpp:41`, `:154` | `firearms\leeEnfield\leeEnfield.p3d` |
| `MP18` | `MP18_Base: Rifle_Base` | `firearms\mp18\config.cpp:40`, `:161` | `firearms\mp18\mp18.p3d` |
| `Luger` | `Luger_Base: Pistol_Base` | `pistols\Luger\config.cpp:40`, `:134` | `pistols\Luger\Luger.p3d` |
| `Mag_Luger_8Rnd` (8 rounds), `Mag_MP18_Drum32Rnd` (32), `Mag_LeeEnfield_10Rnd` (10) | `Magazine_Base` | `attachments\magazine\config.cpp:38`, `:130`, `:234` | `attachments\magazine\magazine_*.p3d` |
| `P1907_Bayonet` | `Inventory_Base`; `inventorySlot[]` holds `weaponBayonetLeeEnfield` and `Knife` | `attachments\muzzle\config.cpp:36` | `attachments\muzzle\bayonet_p1907.p3d` |

In that build the Luger and the MP18 take the same two magazines, the Luger box and the MP18 drum (`pistols\Luger\config.cpp:55`, `firearms\mp18\config.cpp:54`), and the Lee-Enfield takes the bayonet (`firearms\leeEnfield\config.cpp:160`). On that build, compare against the model you inherit from that PBO.

## Loot

The vanilla `types.xml` files list the new class names with a nominal of 0 on Chernarus and Sakhal (`SCARL` at `P:\DZ\worlds\chernarusplus\ce\db\types.xml:19815` and `P:\DZ\worlds\sakhal\ce\db\types.xml:19934`). Livonia gives `SCARL` 0 (`P:\DZ\worlds\enoch\ce\db\types.xml:19378`) but `SCARL_Black` 4 (`P:\DZ\worlds\enoch\ce\db\types.xml:19390`). The Nasdara mission is not on `P:\`; in an installed DayZ Server its `types.xml` gives most of them a nominal above 0 (`Luger` 55, `SCARL` 4). None of them has been spawned in game here yet.
