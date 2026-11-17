# Measured recipes for three kinds of model

Three results measured on real mods, each for one kind of model: cookware, a client side cable segment, and a weapon or other asset posed in the hands. They are measurements on third-party mods, not vanilla facts; the vanilla files they name were confirmed to exist on `P:\`.

Evidence labels: `[EXACT]` is measured, `[DESIGN]` is a rule derived from it.

## Cookware: origin at the centre of the underside (added 2026-09-26)

`[EXACT]` Put a custom cookware's origin at the centre of the underside, Y up, like the vanilla frying pan and cooking pot (`P:\DZ\gear\cooking\fryingpan.p3d`, `P:\DZ\gear\cooking\cookingpot.p3d`; their bounding box starts at Y 0.000).

Vanilla heat source anchor heights, measured offline on the vanilla models after an ODOL to MLOD conversion (DayZ 1.30.164014 experimental):

| Heat source | Anchor | Height |
|---|---|---|
| Gas stove | `cookingpot.001` | 0.084 m |
| Fireplace, over the stone oven | `direct_cooking_a`, `direct_cooking_b`, `direct_cooking_c` | 0.624 m |
| Fireplace, tripod pot | | 0.607 m |
| FireplaceIndoor | | 0.343 m |
| OvenIndoor | | 0.844 m |

The three direct cooking proxies are config classes of the fireplace (`Proxydirect_cooking_a` at `P:\DZ\gear\cooking\config.cpp:2011`).

## Client local cable segment model (added 2026-09-28)

`[EXACT]` Build the unit cable segment with py3d as an open cylinder, 1 m over +Z, centred, radius 0.01, with visual LODs of 8, 5 and 3 sides, no collision geometry, every visual face in the selection `camo`, and the faces wound inward (measured in game, DayZDiag 1.29, on a third-party power mod's cables).

Give the model a name with the mod's prefix: `CfgModels` classes are global across mods.

Vanilla props cannot serve as segments: their pivots are arbitrary, and `P:\DZ\gear\camping\proxies\metalwire.p3d` is a ring.

## In-hands frame gate and build discriminator for assets posed at runtime (added 2026-06-12)

Origin: a third-party weapon mod whose first two test cycles failed. Every offline gate passed and the weapon shipped floating and orbiting, with an idle stance, the camera inside the model and an invisible attached magazine. The corrective build was also delivered blind: the tester's report was "it looks the same to me".

1. **In-hands frame gate, before the first in-game deploy of any weapon or posed asset.** Load the debinarized donor (the weapon whose animation and pose family the asset inherits: the vanilla mp5k or akm, or another mod weapon) into the alignment viewer together with the body p3d and verify the use frame: bore height (the muzzle memory point's y), eye point, grip at origin, and envelope against the donor, in numbers and by eye. Attachment seat checks do not cover this: they validate items against your weapon, never your weapon against the pose.
2. **Pair the states animation with the skeleton (evidence of 2026-06-12).** `w_mp5k_states.anm` (`P:\DZ\anims\anm\player\reloads\mp5\w_mp5k_states.anm`) requires the full MP5K skeleton: charging, bullet, mag_release, hide_barrel, firemode, plus shell_parent and axis_rotation_a/b in memory. The vanilla `P:\DZ\weapons\firearms\mp5\mp5k.p3d` carries them. Simple three bone skeletons (magazine, bolt, trigger) pair with AK family states (`P:\DZ\anims\anm\player\reloads\ak74u\w_aks74u_states.anm`, or the akm family) and the default rifle reload commands, proven in game on two third-party weapon mods whose scripts remap no command. Match the states animation to the skeleton actually built, or build the donor's full skeleton.
3. **Review a generated config for extra fields**, diffing it against the vanilla or donor reference, not only checking that the plan's fields are present. A smuggled weapon level `aimSpeedModifier[]={0.18,...}` caused aim drag ("the weapon orbits the screen"), and both independent reviewers missed it because their prompts only asked about the plan's fields. No vanilla `config.cpp` under `P:\DZ\` sets `aimSpeedModifier` at all, so a diff against any vanilla weapon shows it.
4. **Every corrective build declares its observable discriminator before the test**: "if this build loads, X must visibly change" (an `OnDebugSpawn`, a print, a value). "Looks the same" without a discriminator cannot tell a wrong hypothesis from a stale build; in that case check the build's identity first.

Weapon memory points and selections are in `_shared/weapons/model-selections.md`.
