# Weapons pack

Tier 3 reference for firearms: the weapon class, magazines, ammunition, attachments, recoil, fire modes, muzzle effects and the model names the art lead must provide. Written for `dayz-weapon-specialist`; any DayZ worker may open one file for one task. Tier 1 and Tier 2 still apply on top.

Every fact cites the vanilla file on `P:\` it came from as `path:line`. Line numbers drift between game updates, so Grep for the class or key name when a line no longer matches.

## Which file to open

| Question | File |
|---|---|
| Which vanilla parent do I inherit, in config and in script? How does the engine find the script class? | `weapon-classes.md` |
| What goes in the `CfgWeapons` class and its `CfgPatches`? Chambering, magazines, jamming, damage, sights. | `weapon-config.md` |
| How do the magazine, the ammo pile and the bullet point at each other? | `magazines-ammo.md` |
| Which slot names exist, and how do optics and suppressors change the weapon? | `attachments.md` |
| How do I set recoil, and how do fire modes, burst and rate of fire work? | `recoil-fire-modes.md` |
| Muzzle flash, barrel smoke and shot sounds. | `muzzle-effects.md` |
| What memory points, selections and bones must the model have? | `model-selections.md` |

## Worked example used across the pack

Most examples use the CZ527, the vanilla bolt action hunting rifle with a five round detachable magazine. Its config is `P:\DZ\weapons\firearms\cz527\config.cpp` and its script is `P:\scripts\4_world\entities\firearms\rifle\cz527.c`. The AKM (`P:\DZ\weapons\firearms\akm\config.cpp`) is the example for automatic fire and for a full set of attachment slots.
