# Memory points

What goes in the Memory LOD (`1.0e+15`), the names vanilla script looks up, and how an animation axis is built.

## Rules

- The Memory LOD holds points only. Each named selection is one point, or two points for an axis. The audit warns when the LOD has faces (`check_memory_lod` in `skills/dayz-p3d-audit/scripts/audit_p3d.py`).
- An axis is a selection of exactly two points, named after the bone it turns: bone `doors5` uses `doors5_axis` in `houseblock_3f_corner1.p3d`. The audit checks that every `<name>_axis` in the Memory LOD has a `<name>` selection in the visual LOD and reports CRITICAL when it does not.
- Script finds points by name with `GetMemoryPointPos`, `MemoryPointExists` and `GetMemoryPointIndex` (`P:\scripts\3_game\entities\object.c:451` to `:454`). Spell the name exactly as the script or config that uses it.
- Placed objects need `pos center` at `(0,0,0)` (`dayz-p3d-audit/references/p3d-killers.md` section 5, and the autocenter rule in `named-properties.md`).

## Names vanilla looks up

| Point | Used for | Where vanilla reads it |
|---|---|---|
| `ce_center` | The object's center for actions, vicinity and the code lock | `P:\scripts\3_game\entities\object.c:1363` (`GetCenter`), `P:\scripts\4_world\classes\useractionscomponent\actiontargets.c:854`, `P:\scripts\5_mission\gui\inventorynew\vicinityitemmanager.c:11`, `P:\scripts\4_world\entities\itembase\codelock.c:4` |
| `boundingbox_min`, `boundingbox_max`, `invView` | The item's inventory preview box and camera. `boundingbox_min2`, `boundingbox_max2`, `invView2` and so on add more views | `P:\scripts\3_game\gameplay.c:293` to `:295`; `invView2` at `P:\scripts\3_game\entities\entityai.c:3771` |
| `box_placing_min`, `box_placing_max` | Fallback hologram box when the Geometry LOD box fails | `p3d-killers.md` section 7 |
| `<bone>_axis` | Hinge or slide line of a moving part | `houseblock_3f_corner1.p3d` (`doors1_axis` to `doors9_axis`), `wooden_case.p3d` (`lid_axis`) |
| `<door>_action` | Where a building door's sound plays; named by `soundPos` in `class Doors` | `P:\DZ\structures\residential\config.cpp:7363` (`doorsTwin1_action`) |
| `light_left`, `light_right`, `light_reverse` and their `_dir` points | Car lights | `P:\scripts\4_world\entities\vehicles\carscript.c:165` to `:169` |
| `refill` | Where a vehicle is refuelled | `P:\scripts\3_game\vehicles\transport.c:112` |
| any name | A light or a sound at a point: `CreateLightAtObjMemoryPoint`, `PlaySoundSetAtMemoryPoint` | `P:\scripts\4_world\entities\scriptedlightbase.c:215`, `P:\scripts\3_game\entities\object.c:1294` |

The wooden case shows a typical item set: `boundingbox_min`, `boundingbox_max`, `ce_center`, `ce_radius`, `invview`, `lid_axis`, `hook_axis` and `throwingimpulseposition` (names stored in `P:\DZ\gear\camping\wooden_case.p3d`). Weapon points are in `_shared/weapons/model-selections.md`.

## Names the mod invents

Points that only the mod's own script or config reads can have any name, for example `Fuse_Start` and `Fuse_End` on the fireworks launcher (`P:\scripts\4_world\entities\itembase\gear\tools\fireworkslauncher.c:520`, `:525`). Hand the exact names to whoever writes that script or config.
