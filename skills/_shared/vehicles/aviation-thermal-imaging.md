# Thermal imaging for an aircraft sight

Why a thermal (FLIR) view cannot be built with post-processing, and the approach that works: swapping each entity's textures and materials, with a restore rule that fails safe.

The script calls cite `P:\`. The swap comes from a community thermal mod, whose `ThermalScripts/4_World/Thermal.c` is the source; it is mod behaviour, not vanilla, and not yet checked in game here.

## Post-processing cannot do it

A post-process requester works on the finished frame and knows nothing about entities. It can grade, desaturate or tint, and nothing more, so a "thermal" mode built that way draws a zombie exactly like the ground behind it. No setting of a `PPERequester_*` class or of `PPEGlow` separates a warm body from cold ground.

## Swap texture and material per entity

1. Find candidates with `GetObjectsAtPosition(pos, radius, objects, cargos)` (`P:\scripts\3_game\global\game.c:923`).
2. Keep the living ones. Optionally check line of sight with `RayCastBullet` (`P:\scripts\3_game\global\dayzphysics.c:211`).
3. For each hidden selection, save the originals with `GetObjectTexture` and `GetObjectMaterial`, then call `SetObjectTexture(i, tex)` and `SetObjectMaterial(i, mat)`. All four are on `EntityAI`, not `Object` (`P:\scripts\3_game\entities\entityai.c:2881` to `:2885`).

The glow comes from the material's `emmisive[]` with `diffuse[] = {0,0,0,1}`, together with the swapped texture, so each creature tier needs both. In the mod's `Thermal.c`, apply and restore sit at lines 120 to 270, the driver at 424 to 560 and tracking at 700 to 860.

Vanilla materials can also carry a `StageTI` thermal texture (`_shared/textures/rvmat-stages.md`). That is separate: a search of `P:\scripts` for "thermal" finds only body temperature code and no call that turns on a thermal view.

## Restore everything

Every painted entity must be put back: on a mode change, when the sight closes, when it leaves the scan radius, and when it dies or is deleted. Restore by reconfirming: mark everything unseen at the start of each scan, mark again what the scan finds, and restore the rest. A list the code has to remember to walk fails with an entity that glows forever; reconfirming fails towards restoring.
