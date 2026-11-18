# Weapon troubleshooting

What to check offline before the first in-game test of a custom firearm, and where to look when it misbehaves. Each line points to the pack file that holds the fact.

## Compare with the gun you inherit

Pick the vanilla or third-party weapon whose ammo, magazines, recoil, sounds and animations you want: the AKM for an AK pattern rifle, the AKS-74U or PM73 RAK for an SMG. Read its config and a readable copy of its model, and match them: the same selection names, memory points laid out the same way, and a config base chosen for its behaviour.

The vanilla weapon models on `P:\` are binarized (for example `P:\DZ\weapons\firearms\pm73rak\pm73rak.p3d`, named at `P:\DZ\weapons\firearms\pm73rak\config.cpp:201`), and this repo ships no debinarizer. Compare against the vanilla config and scripts plus a readable model you have the right to open; `/dayz-p3d-audit` reads the mod's own MLOD source.

## Before the first test

1. `model` names the file's real path in the PBO, and the build started from an empty temp folder (`weapon-config.md`, "Model path").
2. The binarized build is what you test, and a mod on a weapon pack the Diag build refuses runs on the retail game (`model-import.md`).
3. Every selection that feeds a bone remap covers its real part (`model-selections.md`, "A selection on the wrong part").
4. The casing ejection points sit on the side the reference gun uses (`model-selections.md`, "Points in the AKM memory LOD").
5. The model has no hand or grip points; the grip is animation work (`_shared/animation/weapon-in-hands.md`).
6. `Mode_*` classes are declared at the root of the file, not inside `CfgWeapons` (`weapon-config.md`, "Forward declarations").
7. The weapon you build on ships a config class and model in the data you have; a 1.30 script class alone is not enough (`dayz-1-30-migration.md`).
8. The memory points pass the AKM checks: level bore, `bolt_axis` parallel to it, ejection direction and `eye` height close to the reference (`model-selections.md`).

## Symptom to cause

| Symptom | Likely cause | Read |
|---|---|---|
| Invisible or white weapon, or a crash on equip | `model` points at the wrong path, or the game loads an old copy left in the build | `weapon-config.md`, "Model path" |
| Winding or normals changed, nothing changes in game | The game loads an unbinarized or old model | `model-import.md` |
| Bolt or charging handle does not move | The selection is on the wrong part, the remap is missing, or the weapon states clip has no bolt channel | `model-selections.md`, "Bones for animation" |
| Trigger does not move when firing | No `trigger` to `Weapon_Trigger` remap | `model-selections.md`, "Registering a remap for a mod weapon" |
| Casings eject on the wrong side | `nabojnicestart` and `nabojniceend` on the wrong side of the model | `model-selections.md` |
| Stuck in single fire, no mode name in the HUD | `Mode_*` declared inside `CfgWeapons` | `weapon-config.md`, "Forward declarations"; `recoil-fire-modes.md` |
| Tilted fire line, muzzle flash off the barrel | `usti hlavne` and `konec hlavne` not level, or `usti hlavne` misplaced | `model-selections.md` |
| Magazine will not attach | The magazine class is missing from `magazines[]` | `attachments.md`, `magazines-ammo.md` |
| Optic or attachment refused | No shared name between `attachments[]` and the item's `inventorySlot[]`, or the optic needs a mount first | `attachments.md` |
| Quick reload never starts, plain reload works | A `TestAttachMagazine` override refuses the quick case | `weapon-script-api.md`, "Firearm actions" |
| Compile error on `GetExplosionParticleID` | Removed in 1.30 | `weapon-script-api.md`, "Explosion effects" |
| Pistol slide or toggle in the wrong state | Override the pistol animation state getters | `weapon-script-api.md`, "Pistol animation states" |
| `SCARL`, `Luger`, `LeeEnfield` or `MP18` will not spawn | No config class for them in the data the server runs | `dayz-1-30-migration.md` |
| Grip, hands or aiming pose wrong; bolt, reload or unjam motion wrong | Animation work, not config | `_shared/animation/weapon-in-hands.md`, `_shared/animation/weapon-anim-blender.md` |
