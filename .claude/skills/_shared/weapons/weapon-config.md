# Weapon config

The `CfgWeapons` keys a firearm needs, and the `CfgPatches` entry that loads it after vanilla. Examples come from the CZ527 (`P:\DZ\weapons\firearms\cz527\config.cpp`) unless a line says otherwise.

## CfgPatches

- Vanilla names one addon per gun, such as `DZ_Weapons_Firearms_CZ527` (`cz527\config.cpp:3`), which requires `DZ_Data` and `DZ_Weapons_Firearms` (`:15` to `:19`).
- Vanilla lists its weapon classes in `units[]` and leaves `weapons[]` empty (`cz527\config.cpp:5` to `:13`). Every vanilla weapons addon under `P:\DZ\weapons` has `weapons[]={};`.
- `requiredAddons[]` names the addon of every parent class used: the gun's own addon for the weapon, `DZ_Weapons_Magazines` for a magazine (`P:\DZ\weapons\attachments\magazine\config.cpp:3`), `DZ_Weapons_Ammunition` for an ammo pile (`P:\DZ\weapons\ammunition\config.cpp:3`), `DZ_Weapons_Projectiles` for a bullet (`P:\DZ\weapons\projectiles\config.cpp:3`), `DZ_Weapons_Optics` and `DZ_Weapons_Muzzles` for attachments.

## Forward declarations

Fire mode and optics bases are declared at the root of the file, outside `cfgWeapons`, before they are used (`cz527\config.cpp:22` to `:27`: `Mode_Safe`, `Mode_SemiAuto`, `Mode_Single`, `Mode_Burst`, `Mode_FullAuto`, `OpticsInfoRifle`). The parent weapon class is declared inside `cfgWeapons` (`:30`).

## Keys on the weapon class

| Key | What it does | Vanilla line |
|---|---|---|
| `chamberableFrom[]` | Ammo pile classes (in `CfgMagazines`) that can be loaded straight into the chamber. | `cz527\config.cpp:55` |
| `magazines[]` | Magazine classes that fit the gun. A new magazine must be listed here or the gun refuses it. | `cz527\config.cpp:60` |
| `chamberSize` | Rounds the chamber holds. | `cz527\config.cpp:53` |
| `magazineSwitchTime` | Time to swap magazines. | `cz527\config.cpp:64` |
| `attachments[]` | Attachment slot names the gun offers (see `attachments.md`). Vanilla sets it on the `scope=2` class. | `cz527\config.cpp:186` |
| `modes[]` and one class per mode | Fire modes (see `recoil-fire-modes.md`). | `cz527\config.cpp:81` |
| `recoilModifier[]`, `swayModifier[]` | Three multipliers each; attachments multiply them further. | `cz527\config.cpp:66`, `:67` |
| `ironsightsExcludingOptics[]` | Optics whose model covers the iron sights; the CZ527 lists `HuntingOptic`. Engine key: no vanilla script reads it, so confirm the effect in game. | `cz527\config.cpp:45` |
| `winchesterTypeOpticsMount` | Makes `HuntingOptic` show its Winchester rings instead of its rail rings. | `cz527\config.cpp:44`; read in `P:\scripts\4_world\entities\itembase\inventory_base\huntingoptic.c:66` |
| `PPDOFProperties[]` | Depth of field while aiming. Read by `Weapon_Base.InitDOFProperties`. | `cz527\config.cpp:42`; `P:\scripts\4_world\entities\firearms\weapon_base.c:1279` |
| `WeaponLength`, `ObstructionDistance` | Used by the weapon lift check near walls. `WeaponLength` defaults to 0.8 when missing. | `cz527\config.cpp:49`, `:50`; `weapon_base.c:1300` |
| `initSpeedMultiplier` | Engine key; by its name a multiplier on the bullet's `initSpeed`. The CZ527 uses 1.2, the AKM 0.9 (`akm\config.cpp:43`). | `cz527\config.cpp:52` |
| `barrelArmor` | Engine key for barrel wear; it pairs with the bullet's `damageBarrel` (see `magazines-ammo.md`). | `cz527\config.cpp:51` |
| `class NoiseShoot` | How far AI hears the shot (`strength`, `type="shot"`). | `cz527\config.cpp:76` |
| `class OpticsInfo: OpticsInfoRifle` | Iron sight camera: `memoryPointCamera="eye"`, zeroing distances in `discreteDistance[]`. | `cz527\config.cpp:110` |
| `simpleHiddenSelections[]`, `hiddenSelections[]` | Parts script can hide, and retexture slots (see `model-selections.md`). | `cz527\config.cpp:68`, `:72` |
| `class Particles` | Muzzle flash and smoke (see `muzzle-effects.md`). | `cz527\config.cpp:132` |
| `weaponStateAnim` | Weapon state animation file. | `cz527\config.cpp:178` |
| `model`, `itemSize[]`, `weight` | The `.p3d`, the inventory size, the weight in grams. | `cz527\config.cpp:185`, `:192`, `:35` |

## Jamming

- `class Reliability` holds `ChanceToJam[]` with five values, one per health level from pristine to ruined. `Rifle_Base` uses `{0,0.001,0.0099999998,0.1,1}` (`P:\DZ\data\config.cpp:4218` to `:4221`); `BoltActionRifle_Base` never jams until ruined, `{0,0,0,0,1}` (`:4261` to `:4264`).
- Script reads it on the server in `InitReliability` (`weapon_base.c:1289`) and picks the value for the current health level in `GetChanceToJam` (`weapon_base.c:403`).

## Damage

- `class DamageSystem` with `GlobalHealth` and `Health` sets `hitpoints` and the `healthLevels[]` materials (`cz527\config.cpp:201`; 300 hitpoints at `:207`).
- `damagePerShot` on `Rifle_Base` is `0.050000001` (`P:\DZ\data\config.cpp:4072`).
- Vanilla retexture variants that swap materials also list the original material in `RefTexsMats[]` inside `Health`, then their own `healthLevels[]` (`cz527\config.cpp:272`). Copy that shape for a new color.

## Changing a vanilla gun

Redeclare the vanilla class with its original parent and only the keys you change, and add its addon to `requiredAddons[]`. When you change an array such as `attachments[]` or `magazines[]`, write the whole array with `=` and keep the vanilla entries; Tier 2 (`conventions/config.md`) explains why `+=` is unsafe.
