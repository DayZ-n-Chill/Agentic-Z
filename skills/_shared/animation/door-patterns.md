# Three worked door patterns

How three complete door samples are wired, side by side: a door with a handle, a door opened by a button, and a door with a handle and a lever. Locks on building doors are in `building-door-locks.md`.

The samples come from third party mods, not vanilla, so their values cannot be checked on `P:\`; their `model.cfg` and `config.cpp` files are not in this repo and the tables carry their content. Read each as a pair: `model.cfg` declares the bones, the moving selections and the source; `config.cpp` binds that source to a `class Doors` entry with timing, sounds and damage. All three share the same scaffolding (`requiredAddons[]` with `"DZ_Data"`, an empty `Default` model class, `skeletonInherit = ""`, `isDiscrete = 0`, `scope = 1` on a `HouseNoDestruct` child) and one `DamageSystem`; `door-config-and-locks.md` describes those once. The vanilla base `HouseNoDestruct` is at `P:\DZ\data\config.cpp:3119`.

## Simple door: door and handle

The handle turns first, then rides along as the door swings. One source, `door1`, drives both, and the handle is a child of the door bone.

| Animation | `selection` | `source` | `axis` | Phase window | Turn, radians |
|---|---|---|---|---|---|
| `Door1` | `door1` | `door1` | `door1_axis` | 0.15 to 1 | 0 to 1.9 |
| `handle` | `handle` | `door1` | `handle_axis` | 0 to 0.15 | 0 to −1.4 |

Both are `type = "rotation"` with `memory = 1`. The windows do not overlap: the handle turns in the first 15 percent of the action and the door swings in the rest. The skeleton is `Simple_DoorSkeleton`; the model class `Simple_Door`, named after the `.p3d`, points at it through `skeletonName`.

| Doors class | `component` | `soundPos` | `animPeriod` | `initPhase` | `initOpened` | Sounds |
|---|---|---|---|---|---|---|
| `Door1` | `door1` | `door1_action` | 1.3 s | 0.0 | 0.0 | `doorMetalSmall` open, close, rattle (locked), open a bit |

The entity is `land_Simple_Door`, with `model` pointing at the addon's `Door\Simple_Door.p3d`.

## Door with button: a static controller

The button never moves, so it is not a bone. It only carries the View Geometry selection `door1_open`, and that name is the source of the door's rotation. Interacting at the button drives the moving selection `door1`.

| Animation | `selection` | `source` | `axis` | Phase window | Turn, radians |
|---|---|---|---|---|---|
| `Door1` | `door1` | `door1_open` | `door1_axis` | 0 to 1 | 0 to 1.9 |

The moving selection and the source have different names; that split is the whole pattern.

| Doors class | `component` | `soundPos` | `animPeriod` | `initPhase` | `initOpened` | Sounds |
|---|---|---|---|---|---|---|
| `Door1_Open` | `door1_open` | `door1_action` | 1.0 s | 0.0 | 0.0 | The same four `doorMetalSmall` sounds |

The damage zone still names the moving part, `componentNames[] = {"door1"}`, not the button's `door1_open`.

## Handle and lever: three parts on one source

A door with a handle, opened from a separate lever. The sample's files are named `Expert_Mode`. All three parts move from `door1_open`, which the lever carries as its interaction selection. The handle follows the door; the lever is a root of its own.

| Animation | `selection` | `source` | `axis` | Phase window | Turn, radians |
|---|---|---|---|---|---|
| `Door1` | `door1` | `door1_open` | `door1_axis` | 0.10 to 1 | 0 to 1.9 |
| `Handle` | `handle` | `door1_open` | `handle_axis` | 0 to 1 | 0 to −1.7 |
| `Lever` | `lever` | `door1_open` | `lever_axis` | 0 to 0.5 | 0 to −0.88 |

Here the windows overlap: the lever finishes its throw halfway, the handle turns over the whole action, and the door starts at 10 percent.

| Doors class | `component` | `soundPos` | `animPeriod` | `initPhase` | `initOpened` | Sounds |
|---|---|---|---|---|---|---|
| `Door1_Open` | `door1_open` | `door1_action` | 1.0 s | 0.0 | 0.5 | The four `doorMetalSmall` sounds |
| `Lever` | `door1_open` | none | 0.5 s | 0.0 | 0.0 | None |

The config has two Doors entries for one source, which breaks the one entry per source rule, and the `Lever` entry has no `soundPos` and no sounds. What that second entry does in game is not tested, so ask the user before copying it. With `initOpened = 0.5` the main door spawns open about half the time. Its damage zone names `door1`.

The lever in this sample's model collides with nothing; the measurement and the repair are in `door-lods.md`, "The lever that collides with nothing".

## The three side by side

| Concern | Simple door | Door with button | Handle and lever |
|---|---|---|---|
| Moving bones | Door and handle | Door only | Door, handle and lever |
| Parents | Handle follows door | Door is the root | Handle follows door; lever is a root |
| Interactive source | `door1` | `door1_open` at the button | `door1_open` at the lever |
| Controller bone | Not needed | Button left out | The lever animates, so it is a bone |
| Phase order | Handle 0 to 0.15, door 0.15 to 1 | Door 0 to 1 | Door 0.10 to 1, handle 0 to 1, lever 0 to 0.5 |
| Doors components | `door1` | `door1_open` | `door1_open`, twice |
| Damage zone component | `door1` | `door1` | `door1` |

None of the patterns uses `AnimationSources` or script; those are in `animation-sources.md` and `script-hooks.md`.
