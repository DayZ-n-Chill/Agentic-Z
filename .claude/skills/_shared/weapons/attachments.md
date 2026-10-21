# Attachments

Slot names, optics, suppressors, and how attachments change the weapon they sit on.

## Slots

- A weapon offers slots through `attachments[]` (AKM at `P:\DZ\weapons\firearms\akm\config.cpp:197`: `weaponButtstockAK`, `WeaponHandguardAK`, `weaponWrap`, `weaponOpticsAK`, `weaponFlashlight`, `weaponMuzzleAK`, `weaponBayonetAK`).
- An attachment says where it fits through `inventorySlot[]` (`HuntingOptic` at `P:\DZ\weapons\attachments\optics\config.cpp:1443`).
- Slot names are defined in `CfgSlots` in `P:\scripts\config.cpp` (addon `DZ_Scripts`, `CfgSlots` at `:11`). The weapon slots run from `Slot_weaponBayonet` at `:219` to `Slot_weaponWrap` at `:442`. A new slot needs its own `CfgSlots` class with `name`, `displayName` and `ghostIcon`, the same shape as `Slot_weaponOpticsHunting` at `:393`.
- Copy a slot name from a vanilla user of the slot, not from memory. Vanilla itself mixes case: the AKM lists `WeaponHandguardAK` (`akm\config.cpp:200`) while the slot is named `weaponHandguardAK` (`P:\scripts\config.cpp:299`) and the handguards use that spelling (`P:\DZ\weapons\attachments\support\config.cpp:2253`). Keep the case of the `CfgSlots` name in new code.

Weapon slots most mods reuse:

| Slot | Takes | Example user |
|---|---|---|
| `weaponOpticsHunting` | `HuntingOptic` | CZ527 (`cz527\config.cpp:189`), CZ550, Winchester 70, Ruger 10/22 |
| `weaponOpticsLRS` | `LongrangeOptic` (`optics\config.cpp:1326`, slot at `:1340`) | No vanilla weapon lists this slot. |
| `weaponOpticsAK`, `weaponOptics`, `weaponOpticsMosin` | AK, rail and Mosin optics | AKM, M4, Mosin |
| `weaponMuzzleAK`, `weaponMuzzleM4`, `weaponMuzzleMosin` | Suppressors and compensators | `AK_Suppressor` (`P:\DZ\weapons\attachments\muzzle\config.cpp:1059`, slot at `:1076`) |
| `suppressorImpro` | `ImprovisedSuppressor` (`muzzle\config.cpp:834`) | CZ527 (`cz527\config.cpp:190`), AUG |
| `weaponWrap` | Weapon wraps | CZ527, AKM |
| `weaponFlashlight`, `weaponBipod`, `weaponBayonet*`, `weaponButtstock*`, `weaponHandguard*` | As named | See `P:\scripts\config.cpp:219` to `:442` |

Because no vanilla gun offers `weaponOpticsLRS`, a mod gun that takes the long range scope is the first user of that pairing. Flag it as untested: the in-game test must check that the scope sits on the rail and that its camera lines up.

## How attachments change the weapon

`PropertyModifiers` (`P:\scripts\4_world\classes\propertymodifiers.c`) reads `recoilModifier`, `swayModifier` and `sightMisalignmentModifier` from the weapon and then multiplies each by the same key on every attachment (`:38` to `:63`). A missing key counts as `1 1 1` (`:65` to `:72`). So `AK_Suppressor` with `recoilModifier[]={0.89999998,0.89999998,0.89999998}` (`muzzle\config.cpp:1084`) cuts recoil by about ten percent.

Suppressors also set `noiseShootModifier` (`muzzle\config.cpp:1083`, `-0.93000001` on `AK_Suppressor`) and `dispersionModifier`.

## Optics

- Script class `ItemOptics` (`P:\scripts\4_world\entities\core\inherited\itemoptics.c:1`); config base `ItemOptics_Base` (`optics\config.cpp:18`).
- `memoryPointCamera` and `cameraDir` on the optic name memory points in the optic's own model (`HuntingOptic` at `optics\config.cpp:1465` and `:1466`).
- `HuntingOptic` shows Winchester style rings when the parent weapon sets `winchesterTypeOpticsMount=1`, and rail rings otherwise (`P:\scripts\4_world\entities\itembase\inventory_base\huntingoptic.c:66` to `:70`). The CZ527 sets it at `cz527\config.cpp:44`.
- `Weapon_Base.CanEnterIronsights` allows iron sight aiming when no optic is fitted, or when the optic allows it through `HasWeaponIronsightsOverride` (`P:\scripts\4_world\entities\firearms\weapon_base.c:1269`).

## Suppressors

- Script class `ItemSuppressor` (`P:\scripts\4_world\entities\core\inherited\inventoryitem.c:2`); `AK_Suppressor` extends it (`P:\scripts\4_world\entities\itembase\suppressorbase\ak_suppressor.c:1`).
- On each shot `Weapon_Base.EEFired` plays the weapon's fire particles and then the suppressor's own (`weapon_base.c:341` to `:356`). The weapon's `MuzzleFlash` sets `ignoreIfSuppressed=1` so the flash hides behind a suppressor (`cz527\config.cpp:139`).
- Suppressed shot sounds come from the fire mode's `soundSetShotExt[]` (see `muzzle-effects.md`).

## Starting attachments for testing

The CZ527 script fits a `HuntingOptic` when spawned from the debug menu (`P:\scripts\4_world\entities\firearms\rifle\cz527.c:9` to `:14`). A mod gun can do the same in its own `OnDebugSpawn` override.
