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

### Points in the AKM memory LOD

Read in the memory LOD of a debinarized vanilla `akm.p3d` (model space, muzzle toward -X, Y up). The names `bolt_axis`, `trigger_axis`, `magazine_axis`, `nabojnicestart`, `ce_center` and `invview` occur in `P:\DZ\weapons\firearms\akm\akm.p3d`; positions and directions cannot be checked on `P:\`, where the model is binarized:

- `bolt_axis` (two points): the travel of the bolt or charging handle, parallel to the bore.
- `trigger_axis` (two points): the trigger's axis, sideways.
- `magazine_axis` and `recoil` (two points each): magazine and recoil axes, roughly vertical on the AKM. Their exact meaning is not confirmed.
- `nabojnicestart` and `nabojniceend`: on the AKM the ejection direction is up, to the right and to the rear.
- `eye` sits 5.2 cm above the bore on AKM iron sights.
- `ce_center`, `ce_radius`, `invview`, `boundingbox_min` and `boundingbox_max` are present too.
- There are no hand or grip points in a weapon model. The grip comes from the player's IK pose animation, which is animation work.

Checks worth making on a new model before the first test (each one failed on an AI generated rifle mesh, measured against the AKM):

- `usti hlavne` and `konec hlavne` share height and side offset, so the bore is level. A `konec hlavne` 4.6 cm too high tilted that rifle's fire line by 6.3 degrees.
- `bolt_axis` is parallel to the bore, and `magazine_axis` and `recoil` point the way they do on the reference gun (on that mesh they were sideways, 90 degrees off).
- The ejection direction is within about 25 degrees of the reference gun's (on that mesh it was 42 degrees off, with no rearward part).
- `eye` sits about as high over the bore as on the reference gun.
- The casing side depends on how the weapon sits in model space. On a custom SMG the two ejection points were on +Z and threw casings into the receiver; -Z was right (confirmed in game). Read the side off the reference weapon, do not assume it.

## Selections

| Name | Kind | Used by | Source |
|---|---|---|---|
| `camo` (and `camo2` and so on) | `hiddenSelections[]` | Retexture slots; `hiddenSelectionsTextures[]` and `hiddenSelectionsMaterials[]` need one entry per name, in the same order. | `cz527\config.cpp:72` to `:75`, `:193`, `:197`; AKM has two at `P:\DZ\weapons\firearms\akm\config.cpp:72` to `:76` |
| `hide_barrel` | `simpleHiddenSelections[]` | The barrel part `HideWeaponBarrel` hides on the client while aiming through an optic that does not allow depth of field. | `cz527\config.cpp:68` to `:71`; `P:\scripts\4_world\entities\firearms\weapon_base.c:98`, `:2121` |
| `magazine` | `simpleHiddenSelections[]` | The visible magazine, switched by `ShowMagazine` and `HideMagazine`. Without it script falls back to the engine magazine selection. | `weapon_base.c:99`, `:2133` to `:2146` |
| `bullet`, `bullet2`, `bullet3` and on | `simpleHiddenSelections[]` | The chambered round for each muzzle, switched by `ShowBullet` and `HideBullet`. Without them script falls back to the engine bullet selection. | `weapon_base.c:101` to `:118`, `:379` to `:397` |
| `drum`, `drum_sound` | Animation source and memory point on a drum magazine model | `Mag_MP18_Drum32Rnd` turns the source `drum` as rounds leave and plays its lever sound at the point `drum_sound` (see `magazines-ammo.md`). | `P:\scripts\4_world\entities\itembase\magazine\magazines.c:81`, `:95` |
| `zasleh` | Fire animation selection | Muzzle flash geometry named by `selectionFireAnim`, set on `Magazine_Base` and `ItemOptics`. | `P:\DZ\weapons\attachments\magazine\config.cpp:52`; `P:\DZ\data\config.cpp:3535` |

## Bones for animation

The weapon's moving parts are remapped to player skeleton bones by `boneRemap[]`, so the model's selections must use these names:

- Rifles (`Rifle_Base`, `P:\DZ\data\config.cpp:4241` to `:4257`): `bolt`, `magazine`, `trigger`, `charging`, `bullet`, `mag_release`, `boltrelease`.
- Bolt actions (`BoltActionRifle_Base`, `P:\DZ\data\config.cpp:4265` to `:4279`): `bolthandle`, `boltbody`, `boltbodyS`, `trigger`, `bullet`, `magazine`.
- The same lists are registered in script (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:1580` and `:1592`).
- Pistols (`Pistol_Base`, `P:\DZ\data\config.cpp:4478`; in script `dayzplayercfgbase.c:1582` and `:1583`): `bolt`, `magazine`, `bullet`, `trigger` and `hammer` (to `Weapon_Bone_01`). `PistolAlt_Base` adds `barrel` (`:1585`), and the MP133 pump shotgun has its own list with `pump` and `feedRamp` (`Mp133Shotgun_Base`, `:1588`).
- Several vanilla guns replace the base list with their own, one `AddItemBoneRemap` call each (`:1597` to `:1640`): IZH-18, B95, SKS, Derringer, Magnum, flare gun, Longhorn, the IZH shotguns, Remington 12, M79 and crossbow. Read the one for the gun you inherit before naming selections.
- Since 1.30 two more weapon bases have their own script remap: `LeeEnfield_Base` with `bolthandle`, `boltbody`, `trigger`, `bullet`, `bullet1` and `magazine` (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:1605`), and `Luger_Base` with `bolt`, `magazine`, `bullet`, `trigger`, `slide`, `toggle1` and `toggle2` (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:1621`). `SCARL_Base` and `MP18_Base` have none and use the `Rifle_Base` list.

The script remap is an array of pairs, the model's selection first and the player bone second, passed to `AddItemBoneRemap` (`P:\scripts\3_game\dayzplayer.c:245-252`). `bolt` goes to `Weapon_Bolt`, `magazine` to `Weapon_Magazine`, `trigger` to `Weapon_Trigger`. A part can instead be animated by the model's own `model.cfg`; drive each part one way only.

The names are the wiring: config, `model.cfg` and the remap find each part by its selection name, so a renamed selection breaks the remap and the animation source with no error.

### Registering a remap for a mod weapon

A mod weapon whose class is not under a vanilla base with a remap registers its own pairs in the same override that registers its hand profile (`weapon-classes.md`, "Hand animations"). The shape that worked on a custom SMG (measured in game; a mod script, not on `P:\`):

```c
modded class ModItemRegisterCallbacks
{
    override void RegisterFireArms(DayZPlayerType pType, DayzPlayerItemBehaviorCfg pBehavior)
    {
        super.RegisterFireArms(pType, pBehavior);

        array<string> partRemap = { "bolt", "Weapon_Bolt", "trigger", "Weapon_Trigger" };
        pType.AddItemBoneRemap("MyMod_Smg_Base", partRemap);
    }
}
```

- `Weapon_Bolt` moves with the weapon states clip, the fifth argument of `AddItemInHandsProfileIK` (`P:\scripts\3_game\dayzplayer.c:243`).
- `Weapon_Trigger` moves with the vanilla player fire and reload clips. On that SMG it was seen animated in the fire clips and in the PM73 reload clip; without the remap the trigger stayed still on fire (measured in game).
- That SMG left `magazine` out of the remap because its magazine moved through `model.cfg` animation sources. The vanilla rifle list includes it (`dayzplayercfgbase.c:1579`).

A remap is needed only when inherited player clips must move the weapon's parts through the `Weapon_*` bones. It is not needed for a part that only `model.cfg` moves. Third-party weapon packs register remaps the same way, one call per weapon base (mod scripts, not on `P:\`; read the pack's script before quoting its arrays).

### A selection on the wrong part

A selection that feeds a remap must cover the real part. On a custom SMG the `bolt` selection had been painted on the barrel, in front of the chamber (X from -0.19 to -0.09), so the remap would have moved the barrel; comparing the selection's centre with where a bolt sits (behind the chamber) caught it before a test (confirmed in game after the repaint; a mod model, not on `P:\`). Ask the object builder for the centre and bounds of each remapped selection and check them against the reference gun.

The repair that worked on that SMG (measured in game):

1. Paint the right faces into the selection with a face painter page made for the model; the painter and refiner pattern is in `skills/_shared/animation/selections-for-actions.md`.
2. Write the selection into the `.p3d` with py3d (`scripts/tools/py3d/`), not by rebuilding the model from its recipe, which drops selections. On the SMG 245 vertices of `bolt` and 243 of `trigger` went into the first visual LOD this way.
3. Copy the selection to the other visual LODs and the shadow LOD by nearest vertex (centres within 3.4 mm on the SMG), keeping a backup of the model, then reload it and check the selection's centre again. After the repaint `bolt` sat at X from -0.07 to 0.04, behind the chamber.
4. Keep the selection names unchanged.

The 1.30 remaps add names a model for those classes must cover: `slide`, `toggle1` and `toggle2` on the Luger, `bolthandle`, `boltbody` and `bullet1` on the Lee-Enfield (lines above). How `eye` lines up with `usti hlavne` on those two has not been measured.

## Other config the model must match

- `InventorySlotsOffsets` places the gun on the back (`Shoulder`) and in the melee slot (`cz527\config.cpp:119` to `:131`).
- `itemSize[]` should fit the model's size in the inventory (`cz527\config.cpp:192`).
- `WeaponLength` should match the real length for the weapon lift check (`cz527\config.cpp:49`).

## What to hand the art lead

A list with: every memory point above that the config names, each `hiddenSelections[]` name with its texture and material, each `simpleHiddenSelections[]` name, the bone names for the chosen base, and one proxy per magazine and attachment slot the gun offers. Mark any name you could not confirm on a vanilla source.
