# What the weapon `.p3d` must contain: named selections and memory points

Which selections and memory points a firearm model must have, what each must cover, and how to check that before a test. How those parts move is animation work and belongs to the dayz-animation-pipeline skill.

Marks: `[VERIFIED in-game]` means measured in game on one of two custom weapon builds, a 9x19 SMG and a 7.62x39 rifle that inherit a third-party weapon pack (third-party mod behaviour, not vanilla; their files are not on `P:\`), `[VERIFIED-vanilla]` means read in the cited vanilla file, `[UNVERIFIED]` means inferred. Facts read in a debinarized vanilla model are marked as not yet checked on `P:\`, because the vanilla models there are binarized and cannot be read. The vanilla names config and script ask for by name are listed, with their `P:\` lines, in `skills/_shared/weapons/model-selections.md`.

## Named selections: the three that matter for a rifle or SMG

A firearm `.p3d` exposes its moving parts as named selections. Each is driven either by the player skeleton, through a bone remap (`bone-remap.md`), or by the model's own `model.cfg` animation sources.

| Selection | Driven by | Evidence |
|---|---|---|
| `bolt` | Player bone `Weapon_Bolt` through `AddItemBoneRemap`; the motion is in the weapon state `.anm` | `[VERIFIED in-game]` on the SMG, 2026-06-30 |
| `trigger` | Player bone `Weapon_Trigger` through `AddItemBoneRemap`; the motion comes from the vanilla player fire and reload animations | `[VERIFIED in-game]` on the SMG (bolt moved; trigger remap present) |
| `magazine` | The model's own `model.cfg` animation sources, not the player skeleton, so it is not driven twice | `[VERIFIED in-game]` on the SMG, whose magazine still rides `model.cfg` |

The vanilla rifle remap lists both `bolt` and `magazine` (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:1579`, `rifleBoneRemap`); the SMG left `magazine` out on purpose.

The names are the wiring. `config.cpp` and `model.cfg` refer to selections by name, so keeping the names keeps everything connected. Rename a selection and the remap and the animation source break with no error.

## W-SEL1: check that a selection covers the real part before trusting it for a remap

`[VERIFIED in-game]` on the SMG, 2026-06-30. The SMG's `bolt` selection had been painted on the barrel (X from -0.19 to -0.09, in front of the chamber and the trigger), not on the bolt. `AddItemBoneRemap` with `bolt` would have slid the barrel, and the bolt would not have moved at all. It was caught offline, before spending a test, by comparing the selection's centre with the anatomy of the gun (a bolt sits behind the chamber, not in front) using a diagram and a face painter. After the repaint the check showed `bolt` at X from -0.07 to 0.04, behind the chamber, the right region.

The check is cheap and offline: dump the selection's vertex centre and bounding box from the `.p3d` and compare them with where that part sits on the reference weapon. Do it for every selection that feeds a bone remap. A selection on the wrong part passes every syntax check and still animates the wrong faces.

## Fixing a selection painted on the wrong part

`[VERIFIED in-game]` on the SMG:

1. **Paint faces into the selection** with a face painter page (an HTML page made for the one model, in which you click faces into a selection). The pattern of a painter plus a refiner that grows the painted region is described in the dayz-animation-pipeline skill (`skills/dayz-animation-pipeline/references/selection-painter-for-actions.md`); use that, do not derive it again.
2. **Write the selections into the `.p3d` with py3d directly, not by rebuilding the model from a recipe.** A rebuild from a recipe drops selections. On the SMG 245 vertices of `bolt` and 243 of `trigger` were written into the first visual LOD this way. py3d is at `scripts/tools/py3d/`.
3. **Copy the selection to the other visual LODs and the shadow LOD by nearest vertex** (centres within 3.4 mm on the SMG), keep a backup of the model first, then reload it and confirm the selection moved to the right region.
4. **Keep the names.** On the SMG `bolt` and `trigger` had no `model.cfg` animation at all (they move through the player animation and the remap, on `Weapon_Bolt` and `Weapon_Trigger`); only `magazine` animates through `model.cfg` animation sources.

## Memory points: the vanilla rifle set

Read in the memory LOD of a debinarized vanilla `akm.p3d` (model space, muzzle toward -X, Y up); not yet checked on `P:\`. The full catalogue table lives in the dayz-animation-pipeline skill (its weapon in hands reference) and is not repeated here. This file keeps the entity side rules and the points a memory point audit must find:

- `usti hlavne`: the muzzle tip (Czech for "barrel mouth"), where the flash appears and the projectile leaves. Script reads it by this name (`P:\scripts\4_world\classes\propertymodifiers.c:30`).
- `konec hlavne`: the rear of the barrel (`P:\scripts\4_world\classes\propertymodifiers.c:31`). It must share Y and Z with `usti hlavne` so the fire line is level.
- `nabojnicestart` and `nabojniceend`: the shell ejection path, two points; on the AKM the direction is up, right and to the rear.
- `bolt_axis` (two points): the travel of the bolt or charging handle, parallel to the bore.
- `trigger_axis` (two points): the trigger animation axis, sideways (along Z).
- `magazine_axis` and `recoil` (two points each): magazine and recoil axes. Their exact meaning is marked "not checked" in the animation skill's own note; carry that mark forward.
- `eye`: the iron sight and aiming camera anchor, about 5 cm above the bore on AKM iron sights; a rail changes the camera height. Anchoring the camera is animation work; that the point exists at roughly the right height is entity work.
- `ce_center` and `ce_radius`, `invview`, `boundingbox_min` and `boundingbox_max`.

### W-MEM1: the casing side depends on the weapon's axes

`[VERIFIED in-game]` on the SMG. `nabojnicestart` and `nabojniceend` set the side casings eject on; the wrong side throws them into the receiver. The SMG had them on +Z (wrong), was flipped to -Z, and that was confirmed correct on 2026-06-30. The correct side depends on how the weapon sits in model space, so read the reference weapon's memory LOD and do not assume it from another weapon. Vanilla names the two points in the weapon's particle config (`Nabojnicestart` at `P:\DZ\weapons\firearms\cz527\config.cpp:146`).

### W-MEM2: a weapon `.p3d` carries no hand or grip memory points

Read in the memory LOD of the debinarized `akm.p3d`, which has no hand selections; not yet checked on `P:\`. The grip is set by the player's IK pose animation and by matching the reference weapon's shape, not by points in the weapon. That is the animation boundary: see the dayz-animation-pipeline skill. If you find yourself wanting to add a "grip" point to the weapon, stop; the answer is on the animation side.

## Memory point checks

Each of these failed on a real AI generated mesh (the rifle, 2026-06-11). They are checks against the AKM reference; the animation skill's weapon in hands reference carries the measured failures.

- `usti hlavne` and `konec hlavne` share Y and Z (a level bore). The rifle had `konec hlavne` 4.6 cm too high, a bore tilted by 6.3 degrees.
- `bolt_axis` is parallel to the bore.
- `magazine_axis` and `recoil` point the way they do on the reference family (roughly vertical on the AKM; the rifle had them sideways, 90 degrees off).
- The ejection direction is within about 25 degrees of the reference (the rifle: 42 degrees off, with no rearward component).
- The height of `eye` over the bore is close to the reference.

The script that draws and checks these, `weapon_grip_viewer.py`, lives with the dayz-animation-pipeline skill. Use it for the memory point audit instead of writing another.

## Open points

- The meaning of `magazine_axis`, `recoil` and `weapon back` is carried over from the animation skill's reference marked "not checked"; it was not confirmed here.

## DayZ 1.30: the new firearm scripts have no model in some builds

Until 1.29, comparing with vanilla meant opening the model of the vanilla weapon whose script you inherit (the 1.29 data is not on `P:\`, so not checked there). Since 1.30 the scripts for `SCARL_Base`, `Luger_Base`, `LeeEnfield_Base`, `MP18_Base` and `P1907_Bayonet` exist, but the data on `P:\` has no model for them: there is no folder for them under `P:\DZ\weapons\firearms\` or `P:\DZ\weapons\pistols\`. `P:\DZ\weapons\firearms\scarh\scarh.p3d` is there; use that, or the AKM, the PM73 RAK (`P:\DZ\weapons\firearms\pm73rak\pm73rak.p3d`, the vanilla open bolt SMG) or a 1.29 pistol, as the memory LOD reference. (Game build 1.30.164200 ships the four weapons' own models in `weapons_nasdara.pbo`, which is not unpacked on `P:\`. See `dayz-1-30-weapons.md`.)

If you make a stand-in mesh for those class names anyway, W-SEL1 covers the extra selection names the vanilla remaps use (`bone-remap.md`): `slide`, `toggle1` and `toggle2` for the Luger; `bolthandle`, `boltbody` and `bullet1` for the Lee-Enfield. The MP18 drum magazine script drives the animation source `drum` and plays a sound at the memory point `drum_sound` (`P:\scripts\4_world\entities\itembase\magazine\magazines.c:81-95`).

How `eye` lines up with `usti hlavne` on the Luger and the Lee-Enfield has not been measured in game, for lack of a readable model. `[UNVERIFIED]` Leave those points until you have the shipped mesh.
