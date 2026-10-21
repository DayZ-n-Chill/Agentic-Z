# model.cfg skeletons and animations

How the bones and the `class Animations` block in a mod's `model.cfg` are laid out, which units the values use, and how names must line up with the `.p3d` and `config.cpp`.

## Who writes what

The file is shared with `dayz-object-builder`. The animation specialist writes the bone entries for the moving parts (`skeletonBones[]`) and the `class Animations` block inside the model's `CfgModels` class. `dayz-object-builder` keeps the rest: the skeleton class itself and its inheritance, `sections[]`, the named selections and the LOD setup in the `.p3d`.

## Layout

Key names below are the Binarize input format. Vanilla does not ship `model.cfg` text on `P:\`, so the layout is format knowledge; the names and values in the next section are what vanilla models store.

```cpp
class CfgSkeletons
{
    class MyMod_Bunker_Skeleton
    {
        skeletonInherit = "";
        isDiscrete = 0;
        skeletonBones[] =
        {
            "door_1", "",        // bone, then its parent ("" for none)
            "door_1_handle", "door_1"
        };
    };
};

class CfgModels
{
    class Default;
    class MyMod_Bunker: Default          // class name = the .p3d file name without extension
    {
        skeletonName = "MyMod_Bunker_Skeleton";
        sections[] = {};
        class Animations
        {
            class Door_1_Rotate
            {
                type = "rotation";
                source = "door_1";       // config source name; see animation-sources.md
                selection = "door_1";    // bone name = named selection in the .p3d
                axis = "door_1_axis";    // two point selection in the Memory LOD
                memory = 1;
                minValue = 0;
                maxValue = 1;
                angle0 = 0;
                angle1 = "rad 90";       // radians; "rad 90" converts degrees
            };
        };
    };
};
```

`skeletonBones[]` is a flat list of pairs: each bone, then its parent bone or `""`. A child bone moves with its parent, so a handle that turns on a door goes under the door bone.

### Animation types

| `type` | What it does | Extra keys |
|---|---|---|
| `rotation` | Turns the bone around the axis. | `angle0`, `angle1` (radians) |
| `rotationX`, `rotationY`, `rotationZ` | Turns around a model axis instead of a memory axis. | `angle0`, `angle1` |
| `translation` | Slides the bone along the axis. | `offset0`, `offset1` (in axis lengths) |
| `translationX`, `translationY`, `translationZ` | Slides along a model axis. | `offset0`, `offset1` |
| `hide` | Hides the bone once the phase reaches `hideValue`. | `hideValue` |

## What vanilla models store

Read from the shipped models on `P:\DZ\`. Each row is one animation as the game loads it.

| Model | Animation | Source | Value range | Result | Bone and axis names in the model |
|---|---|---|---|---|---|
| `P:\DZ\gear\camping\fence.p3d` | `Wall_Gate_Rotate` | `user` | 0 to 100 | rotation, 0 to 1.7453 rad (100 degrees) | skeleton `fence_skeleton`, bones `wall_gate`, `wall_interact`, axis `rotate_axis` |
| `P:\DZ\structures\Residential\HouseBlocks\houseblock_3f_corner1.p3d` | `Doors5` | `doors5` | 0 to 1 | rotation, 0 to minus 1.5708 rad (90 degrees the other way) | bone `doors5`, axis `doors5_axis`, sound point `doors5_action` |
| `P:\DZ\gear\containers\55galDrum.p3d` | `Lid`, `Lid2` | `lid`, `lid2` | 0 to 1 | hide at 0.6 | skeleton `55galDrum_skeleton`, bones `lid`, `lid2` |

What this shows:

- **Angles are radians.** `angle1 = 90` turns the part 90 radians, which spins it many times. Write `1.5708` or `"rad 90"`.
- **The value range is yours to choose.** Fence runs 0 to 100 so script can pass degrees: `fence.c:12` sets `GATE_ROTATION_ANGLE_DEG = 100` and `fence.c:498` calls `SetAnimationPhase("Wall_Gate_Rotate", 100)`. A phase is only meaningful inside `minValue` to `maxValue`.
- **A negative angle opens the other way.** Mirror a door by changing the sign, not the bone.
- **Hide works on a threshold.** The barrel lids hide at 0.6, so phase 1 hides and phase 0 shows; `Lid2` starts at phase 1 (hidden) in `P:\DZ\gear\containers\config.cpp:110`.
- **Names are stored in lower case.** The model holds `lid` while `config.cpp` says `class Lid` (`P:\DZ\gear\containers\config.cpp:101`), so matching ignores case. Keep the case identical anyway so a reviewer can grep it.
- **Animation name and source can differ.** The house model's `Doors1` animation uses source `doorstwin1`, the config door class `DoorsTwin1` (`P:\DZ\structures\residential\config.cpp:7359`). Script and doors find animations by source; `SetAnimationPhase` takes the source name.

## Naming checklist

1. Every bone in `skeletonBones[]` is a named selection in every visual LOD that moves, and in the Geometry, FireGeometry and ViewGeometry LODs where those parts should move with it.
2. Every `axis` is a selection of exactly two points in the Memory LOD.
3. Every `source` other than an engine source matches a class in the item's `AnimationSources` or the building's `Doors` (see `animation-sources.md`).
4. The `CfgModels` class name matches the `.p3d` file name, and `skeletonName` matches the `CfgSkeletons` class.
5. One moving part, one bone. A part that moves with another part is a child bone of it.

Items 1, 2, 4 and 5 are Binarize rules, not something a vanilla file on `P:\` shows; the vanilla models above follow them (bone `doors5` with axis `doors5_axis`).
