# Model selections and memory points

The names a weapon model must contain because config or script asks for them by name. The weapon specialist lists these for the art lead; the object builder puts them in the model.

Every name below comes from vanilla config or script. The vanilla weapon models on `P:\` are binarized, so their full contents cannot be read from disk. For a mod gun, confirm the names in its own MLOD model with `/dayz-p3d-audit`.

## Memory points

| Name | Used by | Source |
|---|---|---|
| `usti hlavne` | Muzzle end of the barrel. Barrel length is measured from it, and muzzle effects spawn at it by default (as `Usti hlavne`). | `P:\scripts\4_world\classes\propertymodifiers.c:30`; `P:\scripts\4_world\entities\weaponparticles.c:113` |
| `konec hlavne` | Breech end of the barrel, the other end of the barrel length. | `propertymodifiers.c:31` |
| `eye` | Iron sight camera, named by `memoryPointCamera` in the weapon's `OpticsInfo`. | `P:\DZ\weapons\firearms\cz527\config.cpp:112` |
| `Nabojnicestart`, `Nabojniceend` | Ejection port, start and direction for chamber smoke. Only needed when the config names them. | `cz527\config.cpp:146`, `:147`, `:166`, `:174` |

Optic attachments carry their own camera points in their own models, such as `eyeScope_temp` and `cameraDir` on `HuntingOptic` (`P:\DZ\weapons\attachments\optics\config.cpp:1465`, `:1466`).

## Selections

| Name | Kind | Used by | Source |
|---|---|---|---|
| `camo` (and `camo2` and so on) | `hiddenSelections[]` | Retexture slots; `hiddenSelectionsTextures[]` and `hiddenSelectionsMaterials[]` need one entry per name, in the same order. | `cz527\config.cpp:72` to `:75`, `:193`, `:197`; AKM has two at `P:\DZ\weapons\firearms\akm\config.cpp:72` to `:76` |
| `hide_barrel` | `simpleHiddenSelections[]` | The barrel part `HideWeaponBarrel` hides on the client while aiming through an optic that does not allow depth of field. | `cz527\config.cpp:68` to `:71`; `P:\scripts\4_world\entities\firearms\weapon_base.c:98`, `:2120` |
| `magazine` | `simpleHiddenSelections[]` | The visible magazine, switched by `ShowMagazine` and `HideMagazine`. Without it script falls back to the engine magazine selection. | `weapon_base.c:99`, `:2132` to `:2146` |
| `bullet`, `bullet2`, `bullet3` and on | `simpleHiddenSelections[]` | The chambered round for each muzzle, switched by `ShowBullet` and `HideBullet`. Without them script falls back to the engine bullet selection. | `weapon_base.c:101` to `:118`, `:379` to `:397` |
| `zasleh` | Fire animation selection | Muzzle flash geometry named by `selectionFireAnim`, set on `Magazine_Base` and `ItemOptics`. | `P:\DZ\weapons\attachments\magazine\config.cpp:52`; `P:\DZ\data\config.cpp:3535` |

## Bones for animation

The weapon's moving parts are remapped to player skeleton bones by `boneRemap[]`, so the model's selections must use these names:

- Rifles (`Rifle_Base`, `P:\DZ\data\config.cpp:4241` to `:4257`): `bolt`, `magazine`, `trigger`, `charging`, `bullet`, `mag_release`, `boltrelease`.
- Bolt actions (`BoltActionRifle_Base`, `P:\DZ\data\config.cpp:4265` to `:4279`): `bolthandle`, `boltbody`, `boltbodyS`, `trigger`, `bullet`, `magazine`.
- The same lists are registered in script (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:1580` and `:1592`).

## Other config the model must match

- `InventorySlotsOffsets` places the gun on the back (`Shoulder`) and in the melee slot (`cz527\config.cpp:119` to `:131`).
- `itemSize[]` should fit the model's size in the inventory (`cz527\config.cpp:192`).
- `WeaponLength` should match the real length for the weapon lift check (`cz527\config.cpp:49`).

## What to hand the art lead

A list with: every memory point above that the config names, each `hiddenSelections[]` name with its texture and material, each `simpleHiddenSelections[]` name, the bone names for the chosen base, and one proxy per magazine and attachment slot the gun offers. Mark any name you could not confirm on a vanilla source.
