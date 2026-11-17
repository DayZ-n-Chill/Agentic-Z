# Memory points

What goes in the Memory LOD (`1.0e+15`), the names vanilla script looks up, and how an animation axis is built.

## Rules

- The Memory LOD holds points only. Each named selection is one point, or two points for an axis. The audit warns when the LOD has faces (`check_memory_lod` in `skills/dayz-p3d-audit/scripts/audit_p3d.py`).
- An axis is a selection of exactly two points, named after the bone it turns: bone `doors5` uses `doors5_axis` in `houseblock_3f_corner1.p3d`. Both points sit in the one selection, never split across two. The name is a convention: what ties an axis to the part it moves is the animation class in `model.cfg`, which names its own `selection` and `axis`, and a rig may give them unrelated names (a wheel selection `wheelfrontleft` turning on `wheel_1_1_axis`). The audit, run with `--model-cfg`, checks the selection and axis each animation names and reports CRITICAL when one is missing or the axis does not have exactly two points (`check_animations` in `skills/dayz-p3d-audit/scripts/audit_p3d.py`). Without a `model.cfg` it only guesses from the `_axis` name, as a WARNING, and only when the DayZ fork of py3d is in use.
- Script finds points by name with `GetMemoryPointPos`, `MemoryPointExists` and `GetMemoryPointIndex` (`P:\scripts\3_game\entities\object.c:451` to `:454`). Spell the name exactly as the script or config that uses it.
- Placed objects need `pos center` at `(0,0,0)` (`dayz-p3d-audit/references/p3d-killers.md` section 5, and the autocenter rule in `named-properties.md`). This rule comes from mod debugging of tall objects, not from vanilla: none of the 572 models under `P:\DZ\gear\` and none of the 161 under `P:\DZ\vehicles\wheeled\` holds a `pos center` point (the watchtower, the fence and the territory flag pole included). Vanilla marks an object's center with `ce_center` instead. So the audit asks for `pos center` only as a WARNING, and only on an item whose config sets `autocenter = 0`.
- Format knowledge, not shown by a vanilla file: the order of an axis's two points sets the direction a rotation turns in (right hand rule). A memory selection can itself be named as the `selection` of an animation, which moves an action point along with the part it belongs to.
- A memory selection is a set of points, and tools can lose the set while keeping the name. After any conversion or rebuild, check that each memory selection still holds its points (`selections.md`, "Membership lost by tools").
- Two models of the same family can be authored in frames that differ by a quarter turn. Before copying a rotation offset or a point from one model to its sibling, compare their memory points one by one (`dayz-p3d-audit/references/manual-checks.md`, "Sibling-model frame parity").

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
| `pos_driver`, `pos_driver_dir`, `pos_coDriver`, `pos_coDriver_dir`, `pos_cargo1` and so on | Where a player stands to get into a seat, and which way they face. Config names them per seat as `getInPos` and `getInDir` | `P:\DZ\vehicles\wheeled\config.cpp:271` and `:272` (`getInPos="pos_driver"`, `getInDir="pos_driver_dir"`); the names are stored in `P:\DZ\vehicles\wheeled\civiliansedan\civiliansedan.p3d` |
| any name | A light or a sound at a point: `CreateLightAtObjMemoryPoint`, `PlaySoundSetAtMemoryPoint` | `P:\scripts\4_world\entities\scriptedlightbase.c:215`, `P:\scripts\3_game\entities\object.c:1294` |

The wooden case shows a typical item set: `boundingbox_min`, `boundingbox_max`, `ce_center`, `ce_radius`, `invview`, `lid_axis`, `hook_axis` and `throwingimpulseposition` (names stored in `P:\DZ\gear\camping\wooden_case.p3d`). Weapon points are in `_shared/weapons/model-selections.md`. Building points (door axes and action points, ladder entry and exit points, loot and rain sound points) are in `building-selections.md`.

How common each name is, from a scan of the 572 models under `P:\DZ\gear\`: `ce_center` in 453, `ce_radius` in 452, `boundingbox_min` in 428, `invview` in 404, `box_placing_min` in 8 (for example `P:\DZ\gear\camping\cartentplacing.p3d`).

## Wheel models

A wheel is its own `.p3d`, placed on the vehicle body as a proxy. Of 12 vanilla wheel models scanned under `P:\DZ\vehicles\wheeled\`, 11 hold the same five memory points: `ce_center`, `ce_radius`, `boundingbox_min`, `boundingbox_max` and `invview` (for example `P:\DZ\vehicles\wheeled\offroadhatchback\proxy\nivawheel.p3d`). `P:\DZ\vehicles\wheeled\civiliansedan\proxy\sedanwheel.p3d` holds only the last three. Give a new wheel all five. Reported from one custom quad, not checked on `P:\`: a wheel with only `ce_center` never touched the ground in the simulation (`dayz-p3d-audit/references/vehicle-checks.md`, killer 11).

## Names the mod invents

Points that only the mod's own script or config reads can have any name, for example `Fuse_Start` and `Fuse_End` on the fireworks launcher (`P:\scripts\4_world\entities\itembase\gear\tools\fireworkslauncher.c:520`, `:525`). Hand the exact names to whoever writes that script or config.

Names such as `actionPos` and `soundPos`, which modelling guides list as interaction points, are of this kind: no vanilla script under `P:\scripts\` looks up a point called `actionPos`, and a vanilla building door names its sound point in config (`soundPos="doorsTwin1_action"`, `P:\DZ\structures\residential\config.cpp:7363`). A worked third-party example of a full naming scheme, the cable ports of the LF_PowerGrid mod (`port_input_N`, `port_output_N` and their `_dir` points, matched to the port names its script registers), is in `dayz-model-pipeline/references/memory-and-selections.md`.
