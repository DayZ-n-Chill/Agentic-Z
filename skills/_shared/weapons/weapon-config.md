# Weapon config

The `CfgWeapons` keys a firearm needs, and the `CfgPatches` entry that loads it after vanilla. Examples come from the CZ527 (`P:\DZ\weapons\firearms\cz527\config.cpp`) unless a line says otherwise.

## CfgPatches

- Vanilla names one addon per gun, such as `DZ_Weapons_Firearms_CZ527` (`cz527\config.cpp:3`), which requires `DZ_Data` and `DZ_Weapons_Firearms` (`:15` to `:19`).
- Vanilla lists its weapon classes in `units[]` and leaves `weapons[]` empty (`cz527\config.cpp:5` to `:13`). Every vanilla weapons addon under `P:\DZ\weapons` has `weapons[]={};`.
- `requiredAddons[]` names the addon of every parent class used: the gun's own addon for the weapon, `DZ_Weapons_Magazines` for a magazine (`P:\DZ\weapons\attachments\magazine\config.cpp:3`), `DZ_Weapons_Ammunition` for an ammo pile (`P:\DZ\weapons\ammunition\config.cpp:3`), `DZ_Weapons_Projectiles` for a bullet (`P:\DZ\weapons\projectiles\config.cpp:3`), `DZ_Weapons_Optics` and `DZ_Weapons_Muzzles` for attachments.

## Forward declarations

Fire mode and optics bases are declared at the root of the file, outside `cfgWeapons`, before they are used (`cz527\config.cpp:22` to `:27`: `Mode_Safe`, `Mode_SemiAuto`, `Mode_Single`, `Mode_Burst`, `Mode_FullAuto`, `OpticsInfoRifle`). The parent weapon class is declared inside `cfgWeapons` (`:30`).

Where each declaration goes matters, because a forward declaration in the wrong scope creates a new empty class and reports no error:

- The fire mode bases are root classes of the engine config, defined before `CfgWeapons` opens: `WeaponMode_Base` (`P:\bin\config.cpp:224`), `Mode_SemiAuto` (`P:\bin\config.cpp:237`), `Mode_Single` (`P:\bin\config.cpp:254`), `Mode_Burst` (`P:\bin\config.cpp:271`), `Mode_Double` (`P:\bin\config.cpp:293`) and `Mode_FullAuto` (`P:\bin\config.cpp:315`), then `OpticsInfoDefault` (`P:\bin\config.cpp:334`), `Muzzle_Base` (`P:\bin\config.cpp:345`) and only then `CfgWeapons` (`P:\bin\config.cpp:366`). `OpticsInfoRifle` is a root class too (`P:\DZ\data\config.cpp:3930`).
- `Mode_FullAuto` is the class that sets `autoFire=1` (`P:\bin\config.cpp:318`); `WeaponMode_Base` has `autoFire=0` (`P:\bin\config.cpp:226`).
- A `class Mode_FullAuto;` written inside `CfgWeapons` declares a different, empty class there. A weapon mode `class FullAuto: Mode_FullAuto` then inherits the empty one, has no `autoFire`, and the engine drops the mode: the gun fires single shots only, shows no mode name in the HUD and the fire mode key does nothing. Binarize and `CfgConvert` accept it, and the derapified config looks correct. Confirmed in game on a custom SMG, where the cause took about 12 rebuilds to find.
- Weapon bases (`Rifle_Base`, another mod's `_Base` class) are members of `CfgWeapons` and are declared inside it.

To find out why a gun will not cycle its fire modes: add a throwaway `scope=2` class that inherits a base known to cycle and changes nothing but `model`, spawn it next to your gun, and press the fire mode key on both. If the clone cycles, the fault is in your config, and when your config compares equal to a working mod's, compare scope against the engine config in `P:\bin\config.cpp`. Give every throwaway weapon its own `model`: a class that inherits a `scope=0` base with no model crashed on spawn in that test.

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

The same keys on an automatic rifle, the AKM (`P:\DZ\weapons\firearms\akm\config.cpp`): `initSpeedMultiplier` `:43`, `chamberableFrom[]` `:46`, `magazines[]` `:51`, `simpleHiddenSelections[]` `:68`, `modes[]` `:77`, the mode classes `:87` and `:119` with `dispersion` at `:116` and `:164`, `discreteDistance[]` `:170`, `weaponStateAnim` `:189` and `attachments[]` `:197`. The base you inherit may differ; Grep the key in its config before quoting a line.

More keys seen in vanilla:

- `chamberSize` is 1 on most firearms; guns that hold their rounds in the chamber or an internal tube set it higher: 5 on the Mosin (`P:\DZ\weapons\firearms\mosin9130\config.cpp:47`), 7 on the Repeater (`P:\DZ\weapons\firearms\repeater\config.cpp:41`).
- `chamberedRound=""` sits next to `chamberSize` on several guns (`P:\DZ\weapons\firearms\b95\config.cpp:40`; SCAR-H at `P:\DZ\weapons\firearms\scarh\config.cpp:39`). Engine key; no vanilla script reads it.
- `recoilModifier[]={1,1,1}` is the neutral value (`P:\DZ\weapons\firearms\b95\config.cpp:61`).
- `aiRateOfFire` and `aiRateOfFireDistance` appear on the launchers (`P:\DZ\weapons\launchers\rpg7\config.cpp:37`, `:38`). Engine keys.
- `reloadAction` is set only on the bow and launcher bases in vanilla (`P:\DZ\data\config.cpp:4592`, `:4756`); third-party weapon packs set it on rifles too (for example `reloadAction = "ReloadAKM"` on an AK; mod config, not on `P:\`). It does not drive the reload; see `_shared/animation/weapon-anim-wiring.md`, "The reloadAction key is legacy".

## Model path

`model` must name the file where it really sits inside the PBO, for example `model="\MyMod\data\my_rifle.p3d"` when the model is under `data\`. On a custom rifle, a `model` that pointed at the PBO root while the file lived under `data\` wasted a whole series of builds: builds made without a clean temp folder carried an old unbinarized copy at the root, the game loaded that copy, and every measurement of the real model was meaningless; the first clean build then showed an invisible weapon and crashed on equip (measured in game on that rifle). `/dayz-lint` reports a `model` path that names no file in the mod (`missing-model`). `/dayz-build-pbo <ModName>` empties its temp folder (`P:\temp\<ModName>`) before every build, which is what removes such leftovers; its `--clean` flag does something else, wiping `P:\Mods\@<ModName>\Addons\` before the build. Importing the mesh and testing the binarized build: `model-import.md`.

## Jamming

- `class Reliability` holds `ChanceToJam[]` with five values, one per health level from pristine to ruined. `Rifle_Base` uses `{0,0.001,0.0099999998,0.1,1}` (`P:\DZ\data\config.cpp:4218` to `:4221`); `BoltActionRifle_Base` never jams until ruined, `{0,0,0,0,1}` (`:4261` to `:4264`).
- Script reads it on the server in `InitReliability` (`weapon_base.c:1289`) and picks the value for the current health level in `GetChanceToJam` (`weapon_base.c:403`).

## Damage

- `class DamageSystem` with `GlobalHealth` and `Health` sets `hitpoints` and the `healthLevels[]` materials (`cz527\config.cpp:201`; 300 hitpoints at `:207`).
- `damagePerShot` on `Rifle_Base` is `0.050000001` (`P:\DZ\data\config.cpp:4072`).
- Vanilla retexture variants that swap materials also list the original material in `RefTexsMats[]` inside `Health`, then their own `healthLevels[]` (`cz527\config.cpp:272`). Copy that shape for a new color.

## Changing a vanilla gun

Redeclare the vanilla class with its original parent and only the keys you change, and add its addon to `requiredAddons[]`. When you change an array such as `attachments[]` or `magazines[]`, write the whole array with `=` and keep the vanilla entries. The vanilla parent comes from an already compiled PBO, and a child's `+=` onto an array inherited across that PBO boundary is not a safe basis for the merged list (`_shared/vehicles/proxies-and-detachable-parts.md`, section "When a baked part becomes an attachment", covers this for `attachments[]`; not yet checked on `P:\` for `magazines[]`). With `=` the effective list is exactly what you wrote.
