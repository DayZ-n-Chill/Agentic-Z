# Weapons pack

Tier 3 reference for firearms: the weapon class, magazines, ammunition, attachments, recoil, fire modes, muzzle effects and the model names the art lead must provide. Written for `dayz-weapon-specialist`; any DayZ worker may open one file for one task. Tier 1 and Tier 2 still apply on top.

Every vanilla fact cites the file on `P:\` it came from as `path:line`. Lessons measured in game on mod weapons say so where they appear; their files are not on `P:\`. Line numbers drift between game updates, so Grep for the class or key name when a line no longer matches.

## Which file to open

| Question | File |
|---|---|
| Which vanilla parent do I inherit, in config and in script? How does the engine find the script class? | `weapon-classes.md` |
| What goes in the `CfgWeapons` class and its `CfgPatches`? Chambering, magazines, jamming, damage, sights. | `weapon-config.md` |
| How do the magazine, the ammo pile and the bullet point at each other? | `magazines-ammo.md` |
| Which slot names exist, and how do optics and suppressors change the weapon? | `attachments.md` |
| How do I set recoil, and how do fire modes, burst and rate of fire work? | `recoil-fire-modes.md` |
| Muzzle flash, barrel smoke and shot sounds. | `muzzle-effects.md` |
| What memory points, selections and bones must the model have? Which selection maps to which player bone, how do I register a remap, and how do I fix a selection painted on the wrong part? | `model-selections.md` |
| Script calls: spawning a loaded weapon, reading its state, the state machine, firearm actions, the 1.30 explosion effect calls. | `weapon-script-api.md` |
| How does a weapon get its hand pose and clips, what can a custom weapon change without replacing the player graph, and how do I make the support hand close? | The animation pack: `_shared/animation/weapon-in-hands.md` (grip, binding, the support hand) and `_shared/animation/weapon-anim-blender.md` (clips, state names, registration, `reloadAction`, loop notes) |
| How do I bring a Blender weapon mesh into the `.p3d` the right way round, and which build do I test? | `model-import.md` |
| What do I check before the first in-game test, and what causes a given symptom? | `troubleshooting.md` |
| What breaks when a weapon mod moves to 1.30, and where do the four 1.30 weapons (SCAR-L, Lee-Enfield, MP18, Luger) and their addons live? | `dayz-1-30-migration.md` |

## Worked example used across the pack

Most examples use the CZ527, the vanilla bolt action hunting rifle with a five round detachable magazine. Its config is `P:\DZ\weapons\firearms\cz527\config.cpp` and its script is `P:\scripts\4_world\entities\firearms\rifle\cz527.c`. The AKM (`P:\DZ\weapons\firearms\akm\config.cpp`) is the example for automatic fire and for a full set of attachment slots.
