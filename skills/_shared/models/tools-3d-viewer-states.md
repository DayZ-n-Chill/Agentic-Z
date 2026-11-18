# Moving parts and material states of a model

Where a model's moving parts and material states are defined, across the `.p3d`, `model.cfg` and `config.cpp`, and the maths that turns an animation phase into a movement. Open it when extending the viewer tool, or when working out by hand how a model's parts move. How the viewer would play them is planned in `tools-3d-viewer-states-build.md`; the tool today (`scripts/tools/dayz-3d-viewer`) shows one static mesh and reads neither `config.cpp` nor `model.cfg`.

The rules for `model.cfg` animations (types, radians, value ranges, naming) are in `_shared/animation/model-cfg-animations.md`, and the config sources in `_shared/animation/animation-sources.md`. The worked examples come from a power grid mod (switches, logic gates, lamps), not from vanilla; the vanilla side of each fact is cited where it appears.

## Three files, three jobs

| File | Holds | What the viewer needs from it |
|---|---|---|
| `.p3d` | Visual LODs with their faces, selections (`switch`, `light_led`, `camo`) and materials; the Memory LOD with axes and points (`switch_axis`, `ce_center`); the collision LODs | The geometry, which faces belong to which selection, and the axis points |
| `model.cfg` | `CfgSkeletons` with `skeletonBones[]`; `CfgModels` with `sections[]` and `Animations` (`type`, `selection`, `axis`, offsets, angles) | How each selection moves |
| `config.cpp` | `CfgVehicles` with `model`, `hiddenSelections[]`, `hiddenSelectionsTextures[]`, `hiddenSelectionsMaterials[]` and `AnimationSources` (`source="user"`, `initPhase`, `animPeriod`) | Which selections can change material, and the phase sources |

## Selections overlap

The `.p3d` is the truth for geometry. Each visual LOD holds named selections, groups of points and faces that can move or change material, and they are not exclusive: a face can be in a moving selection and a material swap selection at once. On the mod's push button:

| Selection | Points | Faces | Role |
|---|---|---|---|
| `zbytek` | 132 | 256 | The fixed housing and base plate |
| `button_push` | 196 | 384 | The moving part, button body and LED |
| `led_indicator` | 130 | 256 | The LED alone, whose material swaps |

`led_indicator` lies wholly inside `button_push`, so the LED moves with the button and also changes colour. `zbytek` and `button_push` share no face, and every face is in at least one selection.

## Animations in `model.cfg`

The `CfgModels` class named after the `.p3d` lists in `sections[]` the selections whose material can be swapped (they must match the `.p3d` names exactly) and in `Animations` one class per movement:

| Field | Meaning |
|---|---|
| `type` | `"translation"` or `"rotation"` in these examples; the other types (`rotationX`, `translationY`, `hide` and the rest) are in `_shared/animation/model-cfg-animations.md` |
| `source` | The animation source from `config.cpp` |
| `selection` | The `.p3d` selection to move |
| `axis` | The Memory LOD selection of two points that sets the axis |
| `memory` | 1 when the axis comes from the Memory LOD, 0 from geometry |
| `minValue`, `maxValue` | The phases where the movement starts and ends. The examples use 0 to 1, but the range is the model's own choice: the vanilla fence gate script sets the phase to 100 (`GATE_ROTATION_ANGLE_DEG`, `P:\scripts\4_world\entities\itembase\basebuildingbase\fence.c:12`, applied at `:507` and `:508`) |
| `offset0`, `offset1` | The translation at `minValue` and `maxValue`, in lengths of the axis |
| `angle0`, `angle1` | The rotation at `minValue` and `maxValue`, in radians |

An axis is a Memory LOD selection of two points. On the push button, `button_axis` runs from (0, 0, 0.023) to (0, 0, 0.041): direction (0, 0, 1), length 0.018 m. A Memory selection of one point is a point, not an axis (on these models `actionPos`, `cable_attach`, `ce_center` and the `port_*` points).

A translation, with A and B the two axis points:

```text
axis_dir     = normalize(B - A)
axis_length  = distance(A, B)
phase        = clamp(source_value, minValue, maxValue)
t            = (phase - minValue) / (maxValue - minValue)
displacement = lerp(offset0, offset1, t) * axis_length
new_position = original_position + axis_dir * displacement
```

A rotation turns every point of the selection about A along `axis_dir` by `angle = lerp(angle0, angle1, t)`, with `t` worked out the same way.

Two animations on one source run one after the other when their phase ranges follow each other. The lid of the mod's AND gate:

| Animation | Phase | Angle |
|---|---|---|
| `latches` | 0.0 to 0.2 | 0 to -0.5 rad (-28.6 degrees) |
| `lid` | 0.2 to 1.0 | 0 to -1.5 rad (-85.9 degrees) |

From 0.0 to 0.2 the latches turn and the lid waits; from 0.2 to 1.0 the latches stay and the lid opens.

## Material states in `config.cpp`

`hiddenSelections[]` lists the `.p3d` selections whose texture or material can be swapped at run time, and `hiddenSelectionsTextures[]` and `hiddenSelectionsMaterials[]` follow it index by index. Vanilla: the medium tent's `hiddenSelections[]` (`P:\DZ\gear\camping\config.cpp:49`), followed by its textures and materials. The animation sources are config too: a vanilla `AnimationSources` block with `source="user"`, `initPhase` and `animPeriod` is at `P:\DZ\gear\containers\config.cpp:99` (the barrel lids).

On the mod's switch, index 0 is `camo`, 1 is `switch` and 2 is `light_led`:

```cpp
hiddenSelections[]          = {"camo",          "switch",        "light_led"};
hiddenSelectionsTextures[]  = {"switch_co.paa", "switch_co.paa", ""};
hiddenSelectionsMaterials[] = {"switch.rvmat",  "switch.rvmat",  "led_off.rvmat"};
```

Script swaps them with `SetObjectMaterial` (`P:\scripts\3_game\entities\entityai.c:2884`) and `SetObjectTexture` (`:2881`), whose first argument is the index into `hiddenSelections[]`:

```c
SetObjectMaterial(2, "path\\to\\led_green.rvmat");  // index 2 = light_led
SetObjectTexture(0, "path\\to\\alt_co.paa");         // index 0 = camo
```

The other materials are not listed in config; they come from script. The mod names its LED materials `led_off.rvmat`, `led_green.rvmat` and `led_red.rvmat`, so a viewer finds them by file name or takes them as input.

## Examples from the mod

| Device | Selections | Movement | Material states |
|---|---|---|---|
| Switch V1 | `switch`, `light_led`, `camo` | translation of `switch` on `switch_axis`, offset 0 to 0.5 | `light_led`: `led_off` by default, `led_green`, `led_red` |
| Switch V2 | `switch`, `light_led`, `camo` | rotation of `switch` on `switch_axis`, 0 to -3.0 rad (172 degrees) | as Switch V1 |
| AND, OR and XOR gates | `unit`, `lid`, `latches`, `bolts`, `light_led_input0`, `light_led_input1`, `light_led_output0`, `camo`, `camosymbol` | `latches` then `lid`, as above | three LEDs, each swapped on its own |
| RF broadcaster and intercom | `camo`, `camoscreen`, `light_led`, `light_led2`, `microphone`, `knob_freq`, `knob_input`, `knob_vol` | `knob_freq` and `knob_vol` 0 to -4.712 rad (270 degrees), `knob_input` 0 to -1.5708 rad (90 degrees) | two LEDs, and `camoscreen` swaps its texture for the display |
| Fridge | | door rotation, 0 to 3.0 rad (172 degrees) | `light_led` |
| Searchlight | | `light_main` pitch, 1.5708 to -1.5708 rad (90 degrees up and down) | `light`, a material swap for the glowing lens |
