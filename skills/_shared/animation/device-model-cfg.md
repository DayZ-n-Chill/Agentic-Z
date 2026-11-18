# Device model.cfg: types, axes and bones

How the `model.cfg` of a small device (switch, button, dial, lid, LED, drawer) is laid out: the skeleton, each animation type with its keys, how memory axes set direction and travel, and which LODs need the moving selection. Config sources, script control and worked patterns are in `device-animation-patterns.md`; a complete switch box is in `device-switch-box.md`.

Vanilla ships `model.cfg` only inside binarized models, so the key names here are Binarize input format. The values vanilla models store, and the script calls, are in `model-cfg-animations.md` and `script-hooks.md`.

## Skeleton and model classes

`CfgSkeletons` lists the bones; `CfgModels` links the model to the skeleton and holds the `Animations` block. The `CfgModels` class name is the `.p3d` file name.

```cpp
class CfgSkeletons
{
    class MyMod_Device_Skeleton
    {
        isDiscrete = 1;
        skeletonInherit = "";
        skeletonBones[] =
        {
            "switch", "",          // bone, then parent ("" for the root)
            "button", "",
            "led_indicator", "",
            "cover", ""
        };
    };
};

class CfgModels
{
    class Default;
    class MyMod_Device: Default
    {
        skeletonName = "MyMod_Device_Skeleton";
        sections[] = {"led_green", "led_red"};
        class Animations
        {
            // one class per moving part, see the types below
        };
    };
};
```

- `isDiscrete = 1` is the usual choice for mechanical parts; `0` is for smooth organic motion such as a flag. A shipped model does not show which value it was built with.
- Every animated selection needs a bone of the same name. Selections that never move need none.
- Declare a parent before its child. A flat list with every bone on the root suits most devices; a chain (`"arm", ""`, `"forearm", "arm"`, `"hand", "forearm"`) passes the parent's motion down, so the hand turns with the arm and then by its own amount.
- `sections[]` lists selections whose material script swaps with `SetObjectTexture`.

## Animation types

| Type | Moves the selection | Keys besides `source`, `selection`, `minValue`, `maxValue` |
|---|---|---|
| `rotation` | Around a two point memory axis | `axis`, `angle0`, `angle1` (radians) |
| `rotationX`, `rotationY`, `rotationZ` | Around one fixed model axis (pitch, yaw, roll) | `angle0`, `angle1`; no `axis` needed |
| `translation` | Along a two point memory axis | `axis`, `offset0`, `offset1` (in lengths of the axis) |
| `hide` | Hides it when the source reaches `hideValue` | `hideValue` |

Between `minValue` and `maxValue` the motion is linear: at `minValue` the part sits at `angle0` or `offset0`, at `maxValue` at `angle1` or `offset1`. Angles are radians; write `"rad 45"` to give degrees (`"rad 90"` is 1.5708, `"rad 180"` 3.1416, `"rad 360"` 6.2832), or work it out as degrees times π divided by 180.

A rotation follows the right hand rule: thumb along the axis from its first point to its second, fingers curl the positive way.

```cpp
class switch_rotate
{
    type = "rotation";
    source = "switch_state";     // config source name, see device-animation-patterns.md
    selection = "switch";        // named selection and bone
    axis = "switch_axis";        // two points in the Memory LOD
    minValue = 0;
    maxValue = 1;
    angle0 = 0;
    angle1 = "rad 45";
};
```

A `hide` animation is all or nothing: the part is hidden while the source is at or above `hideValue` and shown below it. To show a part only when something is installed, let script set the source to 1 while it is missing and 0 once it is there.

```cpp
class hide_battery_missing
{
    type = "hide";
    source = "battery_missing";
    selection = "battery";
    minValue = 0;
    maxValue = 1;
    hideValue = 0.5;
};
```

The single axis types suit a dial that turns a long way, such as `type = "rotationZ"` with `angle1 = "rad 270"`, and need no axis points.

## Memory axes

Each `axis` is a named selection of exactly two points in the Memory LOD. The vector from the first point to the second is the axis.

- Rotation: put the axis on the pivot. Only its direction counts; a hinge from `(-0.5, 0, 0)` to `(-0.5, 1, 0)` turns the part about Y.
- Translation: the length counts too. `offset0` and `offset1` are lengths of the axis, not metres, so the part moves `offset` times the axis length. To move `d` metres, make the axis 1 m long and write `offset1 = d`, or make it `d` long with `offset1 = 1`. An offset written in metres on a short axis barely moves: 0.003 on a 1 cm axis is 0.03 mm. The motion is linear in the source, so at source 0.5 a 0 to 0.003 translation on a 1 m axis has moved 1.5 mm.

The axis length rule is read from binarized models, not measured in game. Binarize stores a translation's offsets as `model.cfg` writes them and keeps the axis at its own length: a mod tray whose `model.cfg` writes `offset1 = 1` on axes 12.1 to 16.2 mm long stores 1.0, where a compiler that converted metres would have stored 62 to 83. The vanilla M249 (`P:\DZ\weapons\firearms\m249\m249.p3d`) therefore carries its authors' values: `bulletMove000` to `bulletMove011` and the `linkMove` classes run from -1 to 0 on axes 1.11 to 1.15 cm long, about one belt link; `bolt_pull_1` runs 0 to 1 on an 8.34 cm axis; `magazine_reload_move_1` runs 0 to 1.45 on a 10 cm axis. Read as metres, that belt would jump a metre per round. Its rotation axes are stored as unit vectors, as wheel axes are. A 1 m axis gives the same travel under either reading, which is why the vehicles pack makes translation axes exactly 1 m long. `model-cfg-animations.md` uses the same unit.

## Which LODs need the moving selection

The LOD names stand for the resolution values in `_shared/conventions/assets.md`.

| LOD | Holds |
|---|---|
| Every visual LOD that shows the motion | The moving selection; its vertices are the ones that move. |
| Geometry, Fire Geometry, View Geometry | The selection only where the collision must move with the part. A small switch can leave it out; a door leaf cannot. Vanilla building doors carry their `doorsN` selection in every LOD the door exists in (`_shared/models/building-selections.md`). |
| Memory | The axis selections (`switch_axis`, `button_axis`, `cover_axis`). |

When one vertex sits in two animated selections, the last animation in the `Animations` class wins. That is reported for a third party mod and not checked against vanilla.

## When it does not move

| Symptom | Likely cause | Fix |
|---|---|---|
| Nothing moves, no error | Axis points missing from the Memory LOD, or selection name differs between `.p3d` and `model.cfg` | Add the axis; match the name letter for letter. Matching ignores case (the shipped barrel stores `lid` while its config says `class Lid`, `P:\DZ\gear\containers\config.cpp:101`; `model-cfg-animations.md`), but keep it identical. |
| Crash on load | An animated selection has no bone | Add it to `skeletonBones[]`. |
| Jitter on a mechanical part | `isDiscrete = 0` | Set `isDiscrete = 1`. |
| Never reaches the end | Both axis points in one place | Give the axis length. |
| Turns the wrong way | Axis points reversed | Swap the points or negate the angles. |
| Translation barely moves or leaves the model | Offset in metres on an axis not 1 m long | Make the axis 1 m long and write the travel in metres. |
| A child moves wrongly | Parent declared after the child | Order `skeletonBones[]` parent first. |

Several animations on one selection are not by themselves a fault: the binarized M249 binds the magazine's hide, two rotations and five translations to one bone, `bolt_pull_1` and `bolt_pull_2` to another, and each belt round's bone to two hides, a rotation and a translation. The offroad hatchback drives `seatdriver` with `SeatDriver` and `SeatDriverRot` over separate source ranges (`model-cfg-animations.md`). Which combinations do fight is not measured; test each animation alone, then give animations that share a selection separate ranges as the seat does.
