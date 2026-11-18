# Thermal imaging for an aircraft sight

Why a thermal (FLIR) view cannot be built with post-processing, and the mechanism that works: swapping textures and materials per entity, with a restore rule that fails safe.

The script calls cite `P:\`. The swap mechanism is third-party mod behaviour, not vanilla (a thermal mod's `ThermalScripts/4_World/Thermal.c`, which is not in this repo), and is not yet checked in game.

## Post-processing cannot do it

A post-process requester works on the assembled frame with no per entity information. It can grade, desaturate or tint, and that is all. A "thermal" mode built that way draws a zombie exactly like the terrain behind it. This is a ceiling, not a tuning problem: no parameter of a `PPERequester_*` class or of `PPEGlow` will separate a warm body from cold ground.

## What works: swap texture and material per entity

1. Scan with `GetObjectsAtPosition(pos, radius, objects, cargos)` (`P:\scripts\3_game\global\game.c:923`).
2. Filter to living entities. Optionally raycast for line of sight with `RayCastBullet` (`P:\scripts\3_game\global\dayzphysics.c:211`).
3. For each hidden selection call `SetObjectTexture(i, tex)` and `SetObjectMaterial(i, mat)`. Both are on `EntityAI`, not on `Object` (`P:\scripts\3_game\entities\entityai.c:2881` to `:2885`). `GetObjectTexture` and `GetObjectMaterial` sit beside them and are how the originals are saved.

The colour comes from the `.rvmat` `emmisive[]` with `diffuse[] = {0,0,0,1}` plus the swapped texture, so a tier per creature type needs both pieces. A working example is that mod's `ThermalScripts/4_World/Thermal.c` (apply and restore at lines 120 to 270, the driver at 424 to 560, tracking at 700 to 860).

Vanilla materials can also carry a `StageTI` thermal texture (`skills/_shared/textures/rvmat-stages.md`). That is a separate thing: a search of `P:\scripts` for "thermal" finds only body temperature code, no script call that turns a thermal view on.

## The rule that decides whether it ships

Every painted entity must be restored: on a mode change, when the sight closes, when the entity leaves the scan radius, and when it dies or is deleted. Design it as restore by reaffirmation: mark everything unseen at the start of a scan, mark again what the scan finds, and restore the remainder. A list the code must remember to walk fails toward an entity that glows forever; reaffirmation fails toward restoring.
