# Weapon classes and parents

Which vanilla class a new weapon inherits from, in `config.cpp` and in Enforce Script, and why the choice decides how it reloads and jams.

## Two hierarchies with the same names

A weapon exists twice: as a `CfgWeapons` class in `config.cpp` and as a script class in `4_World`. The two trees use the same class names but do not have to share parents.

- The AKM config class `AKM_Base` inherits `Rifle_Base` (`P:\DZ\weapons\firearms\akm\config.cpp:26`), while the script class `AKM_Base` inherits `RifleBoltFree_Base` (`P:\scripts\4_world\entities\firearms\automaticrifle\akm.c:1`).
- The CZ527 config class `CZ527` (scope 2, the one players hold) inherits `CZ527_Base` (`P:\DZ\weapons\firearms\cz527\config.cpp:180`). There is no script class named `CZ527`; only `CZ527_Base` exists in script (`P:\scripts\4_world\entities\firearms\rifle\cz527.c:1`). Vanilla relies on the engine using the script class of the nearest config ancestor that has one.

So a mod weapon that inherits a vanilla config class gets that class's script behavior with no script of its own. Write a script class only when the weapon needs different behavior, such as its own recoil. Name it after the mod's config class and put it in `4_World`.

## Script base classes by mechanism

The script base decides the weapon state machine: how it chambers, reloads, fires and jams. Pick the base that matches the real action of the gun, then the closest vanilla gun on that base.

| Script base | Mechanism | Defined at | Vanilla example |
|---|---|---|---|
| `Weapon` | Engine side root for every firearm | `P:\scripts\4_world\entities\core\inherited\weapon.c:4` | |
| `Weapon_Base` | Common firearm code (firing hook, jamming, recoil object, bullet selections) | `P:\scripts\4_world\entities\firearms\weapon_base.c:38` | |
| `Rifle_Base` | Root for long guns | `P:\scripts\4_world\entities\firearms\rifle_base.c:10` | |
| `RifleBoltFree_Base` | Detachable magazine, bolt does not lock open | `P:\scripts\4_world\entities\firearms\rifleboltfree_base.c:92` | AKM, AUG, VSS |
| `RifleBoltLock_Base` | Detachable magazine, bolt locks open on empty | `P:\scripts\4_world\entities\firearms\rifleboltlock_base.c:119` | M4A1 (`automaticrifle\m4a1.c:1`), SVD, FAL |
| `BoltActionRifle_ExternalMagazine_Base` | Bolt action with a detachable magazine | `P:\scripts\4_world\entities\firearms\boltactionrifleexternalmagazine_base.c:112` | CZ527, CZ550, Scout |
| `BoltActionRifle_InnerMagazine_Base` | Bolt action loaded round by round into an internal magazine | `P:\scripts\4_world\entities\firearms\boltactionrifleinnermagazine_base.c:68` | Mosin 91/30 (`rifle\mosin9130.c:5`), Winchester 70 |
| `ChamberFirst_InnerMagazine_SemiAutomatic_Base` | Semi automatic with an internal magazine | `P:\scripts\4_world\entities\firearms\chamberfirstinnermagazinesemiautomatic_base.c:68` | Remington 12 shotgun (`shotgun\remington12.c:1`) |
| `RifleSingleShot_Base` | Single shot, break action | `P:\scripts\4_world\entities\firearms\riflesingleshot_base.c:65` | IZH18 (`rifle\izh18.c:5`) |
| `DoubleBarrel_Base` | Two barrels, two muzzles | `P:\scripts\4_world\entities\firearms\doublebarrel_base.c:119` | Derringer |
| `OpenBolt_Base` | Fires from an open bolt | `P:\scripts\4_world\entities\firearms\openbolt_base.c:122` | MP18 (`smg\mp18.c:1`), PM73 RAK |
| `Pistol_Base` | Detachable magazine pistol | `P:\scripts\4_world\entities\firearms\pistol_base.c:149` | FNX45 (`pistol\fnx45.c:1`) |

Some guns build their own state machine on a plain base: the SKS on `Rifle_Base` (`automaticrifle\sks.c:69`), the MP133 pump shotgun on `Rifle_Base` (`shotgun\mp133.c:64`) and the Magnum revolver on `Weapon_Base` (`pistol\magnum.c:50`). Each mechanism base builds its states and transitions in `InitStateMachine` (for example `boltactionrifleexternalmagazine_base.c:123`; the empty default is `weapon_base.c:133`). Do not override `InitStateMachine` for a gun that matches a vanilla mechanism; inherit the matching base instead.

## Config base classes

The `CfgWeapons` roots are in `P:\DZ\data\config.cpp` (addon `DZ_Data`):

- `Rifle_Base` at `:4051` sets the shared long gun defaults (shoulder and melee slots at `:4058`, `damagePerShot` at `:4072`, the default `Reliability` at `:4218`, melee modes at `:4222`, bone remap at `:4241`).
- `BoltActionRifle_Base` at `:4259`, with `BoltActionRifle_InnerMagazine_Base` at `:4281` and `BoltActionRifle_ExternalMagazine_Base` at `:4284`.
- `Shotgun_Base` at `:4287` and `Pistol_Base` at `:4303`.

Vanilla guns put shared values in a `scope=0` base class and the spawnable variants in `scope=2` children (`CZ527_Base` at `cz527\config.cpp:31` with `scope=0`, `CZ527` at `:180` with `scope=2`). Inherit from the `scope=2` class when the mod gun uses the vanilla model, or from the `_Base` class when it brings its own model and attachment list.

## Hand animations

The player only holds a weapon correctly when its class, or a parent, has an item in hands profile. Vanilla registers them by class name in `DayZPlayerTypeRegisterItems` (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:334`), for example `CZ527_Base` at `:416` and the magazine `Mag_CZ527_5rnd` at `:591`. A mod gun that inherits a registered vanilla class reuses that profile. The bolt action bone remap is registered for `BoltActionRifle_Base` at `:1592`. A new animation set belongs to the animation specialist.

## Reload animation overrides

`Weapon_Base.GetWeaponSpecificCommand` returns the reload or action animation for a weapon action (`weapon_base.c:1257`). The default passes the command through. The AUG overrides it to swap rifle reloads for its own (`P:\scripts\4_world\entities\firearms\automaticrifle\aug.c:18`). Only override it when the gun reuses a mechanism but needs a different reload animation.
