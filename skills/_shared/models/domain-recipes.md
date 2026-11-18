# Cookware, cable segments and posed weapons

What to get right for three kinds of model: cookware that sits on vanilla heat sources, a client side cable segment, and a weapon or other asset posed in the hands. The measurements come from mod models, not from vanilla files; the vanilla models and lines they name are on `P:\`.

## Cookware

Put a custom cookware's origin at the centre of its underside, Y up, as the vanilla frying pan and cooking pot do: their bounding boxes start at Y 0.000 (`P:\DZ\gear\cooking\fryingpan.p3d`, `P:\DZ\gear\cooking\cookingpot.p3d`).

Heights of the vanilla heat source anchors, measured on the vanilla models after an ODOL to MLOD conversion:

| Heat source | Anchor | Height |
|---|---|---|
| Gas stove (`PortableGasStove`, `P:\DZ\gear\cooking\config.cpp:1457`) | `cookingpot.001` | 0.084 m |
| Fireplace, over the stone oven | `direct_cooking_a`, `direct_cooking_b`, `direct_cooking_c` | 0.624 m |
| Fireplace, tripod pot | | 0.607 m |
| `FireplaceIndoor` (`config.cpp:358`) | | 0.343 m |
| `OvenIndoor` (`config.cpp:507`) | | 0.844 m |

The three direct cooking proxies are config classes of the fireplace, for example `Proxydirect_cooking_a: ProxyAttachment` (`P:\DZ\gear\cooking\config.cpp:2011`, with `_b` and `_c` at `:2020` and `:2029`); the pot on the gas stove is `ProxyCookingPot` (`:1993`).

## A cable segment drawn on the client

Measured in game on a mod's power cables: build the unit segment with py3d as an open cylinder 1 m long along +Z, centred, radius 0.01, with visual LODs of 8, 5 and 3 sides, no collision geometry, every visual face in the selection `camo`, and the faces wound inward.

Give the model a class name with the mod's prefix, because `CfgModels` classes are global across mods. Vanilla props cannot serve as segments: their pivots are arbitrary, and `P:\DZ\gear\camping\proxies\metalwire.p3d` is a ring.

## A weapon or asset posed in the hands

A weapon can pass every offline check and still float, drift round the screen, stand in the idle stance, put the camera inside the model and hide its magazine. These checks catch that.

1. **Check the hold before the first in-game test.** Load the binarized model of the weapon whose animations and pose your asset reuses (the vanilla `mp5k` or `akm`, or another mod weapon), converted back to MLOD, into the alignment viewer with your body `.p3d`. Compare in numbers and by eye: bore height (the muzzle memory point's Y), eye point, grip at the origin, and the outline against the reference. Attachment seat checks do not cover this; they test items against your weapon, never your weapon against the pose.
2. **Match the states animation to the skeleton you built.** `P:\DZ\anims\anm\player\reloads\mp5\w_mp5k_states.anm` needs the full MP5K skeleton: `charging`, `bullet`, `mag_release`, `hide_barrel`, `firemode`, plus `shell_parent` and `axis_rotation_a` and `axis_rotation_b` in Memory, as the vanilla `P:\DZ\weapons\firearms\mp5\mp5k.p3d` carries. A simple three bone skeleton (magazine, bolt, trigger) pairs with the AK family states (`P:\DZ\anims\anm\player\reloads\ak74u\w_aks74u_states.anm`, or the AKM family) and the default rifle reload commands; that worked in game on two mod weapons whose scripts remap no command. Otherwise build the reference weapon's full skeleton.
3. **Diff a generated config against a vanilla weapon,** not only for the fields you planned. A stray weapon level `aimSpeedModifier[]={0.18,...}` drags the aim so the weapon drifts round the screen. No vanilla `config.cpp` under `P:\DZ\` sets `aimSpeedModifier`, so a diff against any vanilla weapon shows it.
4. **Say what a fix build must change before you test it:** "if this build loads, X must visibly change" (an `OnDebugSpawn`, a print, a value). "It looks the same" without that cannot tell a wrong idea from a stale build; check which build is loaded first.

Weapon memory points and selections are in `_shared/weapons/model-selections.md`.
