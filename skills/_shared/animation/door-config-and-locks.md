# Door keys in model.cfg and config.cpp

Which classes and keys a building door needs in `model.cfg` and `config.cpp`, what each one does, and which values the three worked patterns use. The 1.30 script rules for opening and locking a door are in `door-open-and-lock-code.md`.

Vanilla facts cite `P:\` (DayZ 1.30). The three worked patterns are third party mod samples, not vanilla, and their files are not in this repo: the simple door (`Simple_Door.cfg`), the door with a button (`Door_w_Button.cfg`) and the door with a handle and a lever (`Expert_Mode.cfg`), each with its own `config.cpp`. Their values cannot be checked on `P:\`. `door-patterns.md` sets them side by side.

## Two name chains

What the player uses: the View Geometry interaction selection in the `.p3d`, then the `model.cfg` animation `source`, then the `component` of the `class Doors` entry.

What moves: the named selection in the `.p3d`, then a `CfgSkeletons` bone of the same name, then the `selection` of a `CfgModels` animation.

The chains can share a name (`door1` in the simple door) or split (`selection = "door1"` with `source = "door1_open"` in the button door).

In vanilla the `Doors` subclass name, its `component` and the animation source are almost always one name: of the 2,651 `class Doors` entries in the configs under `P:\DZ`, 2,640 have a class name equal to their `component` apart from letter case, for example `class Doors5` with `component="Doors5"` (`P:\DZ\structures\residential\config.cpp:7385`). Two set no `component`, and the Badlands `tandoor1` entry (nine copies) uses `component="tandoor1_door"` (`P:\DZ\structures_takistan\Residential\config.cpp:10159` to `:10162`). Which of the two names that model's source carries is inside the packed `.p3d`, so it is not checked on `P:\`. Keep all three the same in a new door and the question never comes up.

## Skeleton

The three patterns spell the root class `cfgSkeletons`; the usual spelling is `CfgSkeletons`. Either loads.

| Class or key | What it does | In the patterns |
|---|---|---|
| Skeleton class | Named by the model's `skeletonName`. | `Simple_DoorSkeleton`, `Door_w_ButtonSkeleton`, `Expert_ModeSkeleton` |
| `skeletonInherit` | Parent skeleton. | `""` in all three |
| `isDiscrete` | Skeleton flag. | `0` in all three |
| `SkeletonBones[]` | Flat child and parent string pairs. | All three |
| Parent `""` | The bone follows no animated parent. | The `door1` roots and the lever |
| Parent bone name | The child follows that parent. | `handle` under `door1` |

Give each model a skeleton name of its own, built from the `.p3d` base name such as `<p3dname>_skeleton`; the suffix is a convention. Duplicate skeleton names are reported to crash a server; that is not reproduced, so treat unique names as a cheap precaution.

## Animations

| Class or key | What it does | In the patterns |
|---|---|---|
| `class Default` | Empty base with sections and skeleton fields. | All three |
| `sections[]`, `sectionsInherit` | Named material sections and their parent. | Empty in all three |
| `skeletonName` | The exact skeleton class name. | All three |
| Model class | Named after the `.p3d`. | `Simple_Door`, `Door_w_Button`, `Expert_Mode` |
| `class Animations` | One class per animated selection, not per source. | Two, one and three |
| `type = "rotation"` | Turns the selection. | Every animation |
| `selection` | The moving named selection. | `door1`, `handle`, `lever` |
| `source` | The controller or interaction name; may differ from the selection. | `door1` in the simple door; `door1_open` in the other two |
| `axis` | A two point axis selection in the Memory LOD. | `door1_axis`, `handle_axis`, `lever_axis` |
| `memory = 1` | Read the axis from the Memory LOD. | Every rotation |
| `minValue` | Source phase where the motion starts. | Simple door 0.15, its handle 0 |
| `maxValue` | Source phase where `angle1` is reached. | Simple handle 0.15, lever 0.5 |
| `angle0` | Rotation at `minValue`. | 0 everywhere |
| `angle1` | Rotation at `maxValue`; the sign sets the direction. | 1.9 and −1.4; 1.9, −1.7 and −0.88 |

`angle0` and `angle1` are radians (degrees times pi over 180): a bare number is radians, and `"rad 90"` writes 90 degrees. The simple door's `angle1 = 1.9` swings about 109 degrees. This is Binarize format knowledge, not visible on `P:\`; the key notes are in `model-cfg-animations.md`.

One source can drive several animations. The simple door moves `Door1` and `handle` from `door1`; the button door moves only `Door1` from `door1_open`; the handle and lever door moves all three from `door1_open`. The button is not in its skeleton because it does not move.

## Entity class

| Class or key | What it does | In the patterns |
|---|---|---|
| `class CfgPatches` and a patch subclass | The addon. | All three |
| `requiredAddons[] = {"DZ_Data"}` | Needed by every working pattern. | All three |
| `class HouseNoDestruct;` | Forward declaration of the base. | All three |
| `class land_*: HouseNoDestruct` | The entity. | `land_Simple_Door` and its two siblings |
| `scope` | 0 private, 1 protected, 2 public. | 1 in all three |
| `model` | `.p3d` path inside the addon. | All three |
| `class Doors` | The door entries. | All three |

`HouseNoDestruct` is a vanilla class (`P:\DZ\data\config.cpp:3119`). A `scope = 1` class can be placed in Terrain Builder, inherited and created by script, but lists that filter on `scope = 2` hide it. Vanilla does this with `LargeTentClutterCutter`: `scope=1` (`P:\DZ\gear\camping\config.cpp:1454` to `:1456`), created from script with `CreateObjectEx` (`P:\scripts\4_world\entities\itembase\tentbase\largetent.c:140`). Buildings ship with `scope = 1`.

## One entry per door

| Key | What it does | Patterns, or where vanilla reads it |
|---|---|---|
| Doors subclass | Named like the source by convention; `component` is the real binding. | `Door1`; `Door1_Open`; `Door1_Open` and `Lever` |
| `displayName` | Label of the door or controller. | Every entry |
| `component` | The `model.cfg` interaction source. | `door1`; `door1_open` in the other entries |
| `soundPos` | Memory point where the sound plays. | `door1_action`; the lever entry has none |
| `animPeriod` | Duration in seconds. | 1.3; 1.0; 1.0 and 0.5 for the lever |
| `initPhase` | Phase at spawn. | 0.0 everywhere |
| `initOpened` | Chance to spawn open. | 0.0; 0.0; 0.5 and 0.0 for the lever |
| `soundOpen`, `soundClose`, `soundLocked`, `soundOpenABit` | Sound names. | Every entry but the lever |
| `relatedInventorySlots[]` (1.30) | Inventory slots tied to this door (locks), read into `m_RelatedInventorySlotNames`. | `P:\scripts\3_game\entities\additionaldoorsinfo.c:23` to `:27` |
| `lockCompatibilityBitMask` (1.30) | An integer already in bit form; when missing, script uses `1 << EBuildingLockType.LOCKPICK`. | `additionaldoorsinfo.c:29` to `:32` |
| `interactPositionPoint`, `interactDirPoint` (1.30) | Memory points for a door that opens from one side, read into `m_InteractLimitingPositionPoint` and `m_InteractLimitingDirPoint`. | `additionaldoorsinfo.c:34` to `:38` |
| `doorConstructionPart`, `doorConstructionPhysicsSource` (1.30) | For a house door that can be rebuilt: the construction part, and the `AnimationSources` name that switches the door's physics. | `additionaldoorsinfo.c:40` to `:44` |

Door sounds are defined in `P:\DZ\sounds\hpp\config.cpp`, for example `class doorMetalSmallOpen` (`:520946`). Check a name exists there before using it.

`initPhase` is the phase (0 to 1) at spawn, not a delay; 0.0 spawns closed. `initOpened` is a spawn probability: the door spawns open when a random number is below it, so 0 never and 0.5 about half the time. Both are engine behaviour, not visible on `P:\`. Vanilla houses use values such as 0.3 and 0.7 (`initOpened=0.69999999`, `P:\DZ\structures\residential\config.cpp:7392`). The Badlands houses that can be rebuilt use `initOpened=2` on 566 doors (`P:\DZ\structures_takistan\Residential\config.cpp:32`); what a value above 1 does is not visible on `P:\`. One vanilla entry has the broken value `initOpened="0..7"` (`P:\DZ\structures\residential\config.cpp:18622`); do not copy it.

The 1.30 keys are set only by the Badlands houses that can be rebuilt, all in `P:\DZ\structures_takistan\Residential\config.cpp`: `relatedInventorySlots[]` and `lockCompatibilityBitMask=0` on doors (`:37` to `:42`), `interactPositionPoint` and `interactDirPoint` on windows (`:80`, `:81`), and `doorConstructionPart` and `doorConstructionPhysicsSource` on both (`:43`, `:44`). `building-door-locks.md` walks through that house. Vanilla also shows the fence listing `Att_CombinationLock` and `Att_CodeLock` in its entity `attachments[]` (`class Fence`, `P:\DZ\gear\camping\config.cpp:4362` to `:4368`).

## One source, one Doors entry

Start from this rule: one `class Doors` subclass per source, with `component` equal to that source. Animations that share the source get no entry of their own. The simple and button doors follow it.

The handle and lever door breaks it: its model has only `source = "door1_open"`, but its config declares `Door1_Open` and `Lever`, both with `component = "door1_open"`, and the lever entry sets no `soundPos`, `soundOpen` or `soundClose`. Ask the user before copying the second entry.

## Damage

All three patterns carry the same `DamageSystem`:

| Class or key | Value |
|---|---|
| `GlobalHealth`, `Health` | `hitpoints = 1000` |
| `GlobalArmor` | Projectile and melee damage to health, blood and shock all 0 |
| Zone `class Door1`, `Health` | `hitpoints = 1000`, `transferToGlobalCoef = 0` |
| `componentNames[]` | The moving geometry `{"door1"}`, even when the source is `door1_open` |
| `fatalInjuryCoef` | −1 |
| `class ArmorType` | Projectile health 2, melee health 2.5, blood and shock 0 |

Do not swap `componentNames[]` for the Doors component by reflex: the button and lever doors show the two can differ.

## The patterns in one table

| Pattern | Bones (child, parent) | Animated selections | Source | Doors component |
|---|---|---|---|---|
| Simple door | `door1`, none; `handle`, `door1` | `door1`, `handle` | `door1` | `door1` |
| Door with button | `door1`, none | `door1` | `door1_open` | `door1_open` |
| Handle and lever | `door1`, none; `handle`, `door1`; `lever`, none | `door1`, `handle`, `lever` | `door1_open` | `door1_open`, twice |
