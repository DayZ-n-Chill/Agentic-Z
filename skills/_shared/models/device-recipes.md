# Electrical device specifications

Which worked specifications exist for electrical devices (a push button, a wall switch, a battery adapter, a sorter, a generator, a cable segment and a junction box), the design language they share, their vertex budgets and naming, and a template for a new device. They describe the models of a third-party electrical power mod, version 2.8 and later, so they are starting points to adapt, not vanilla facts. Where an Arma habit does not work in DayZ, the text gives the DayZ form.

| Device | File |
|---|---|
| Push button, wall switch | `device-recipes-controls.md` |
| Battery adapter, floor generator, cable segment | `device-recipes-power.md` |
| Sorter, junction box | `device-recipes-distribution.md` |

Coordinates in the memory point lists are millimetres in a modelling frame with Z up. A DayZ model is in metres with Y up, so convert both the unit and the axes when you build the `.p3d` (`generated-model-rules.md`, "The Blender to DayZ map"). Animation blocks are short specifications, not `model.cfg` syntax; the real syntax is in `_shared/animation/device-model-cfg.md`. The cable segment alone is in metres in the DayZ frame.

## Design language

| Part | Finish | Roughness | Metallic |
|---|---|---|---|
| Main body | Dark grey painted metal, RAL 7016 anthracite | 0.65 | 0.3 |
| Accents | Brushed aluminium, satin | 0.4 | 1.0 |
| Seals | Matte black rubber | 0.8 | 0.0 |
| Indicators | Red, green and yellow LEDs, lit through emissive maps | | |

- Edges get a 2 to 3 mm bevel on every main panel.
- Mounting is DIN rail tabs or M6 screw holes modelled into the geometry.
- Cables enter through threaded glands of 12 or 16 mm on the back or sides.
- Labels are embossed (0.5 mm deep) or printed in the `_co`.
- Status LEDs read from 2 m or more.

Largest size of each device: push button 36 mm, battery adapter 80 mm, wall switch 85 mm, junction box 150 mm, sorter 200 mm, generator 600 mm; cable in 1 m segments, 20 mm across.

| Device size | `_co` | `_nohq` | `_smdi` | Devices |
|---|---|---|---|---|
| Up to 30 cm | 512 | 512 | 512 | Push button, battery adapter, wall switch, junction box, sorter |
| 31 to 60 cm | 1024 | 1024 | 1024 | Generator |
| 61 to 120 cm | 2048 | 1024 | 1024 | None |

## LED states through hidden selections

Script shows an LED state by swapping the texture or material of the LED's hidden selection: `SetObjectTexture(0, "\MyMod\data\led_green_co.paa")` on the device, where 0 is the index in `hiddenSelections[]` (`P:\scripts\3_game\entities\entityai.c:2881`); `SetObjectMaterial` swaps the `.rvmat` (`:2884`). Arma's SQF `setObjectTexture [obj, 0, ...]` does not exist in DayZ. Green means active, red a fault, yellow a warning, and off no power.

## Vertex budgets

Pick the tier by how much visible detail the device carries, not by its size: the 200 mm sorter has about 416 vertices at LOD0, more than twice the 152 of the 80 mm battery adapter and six times the 64 of the 85 mm wall switch.

| Tier | LOD0 | LOD1 | LOD2 | LOD3 | Devices |
|---|---|---|---|---|---|
| Light | up to 500 | up to 250 | up to 125 | up to 60 | Wall switch (64), battery adapter (152), push button (192), junction box (368), sorter (416) |
| Medium | 500 to 1000 | 250 to 500 | 100 to 250 | 50 to 125 | Generator (584) |
| Heavy | 1000 to 2000 | 500 to 1000 | 250 to 500 | 125 to 250 | None |
| Machinery | 2000 to 3000 | 1000 to 1500 | 500 to 750 | 250 to 375 | None |

Collision geometry (Geometry, Fire Geometry, View Geometry) uses at most 8 to 20 convex vertices per object, close to the bounding box.

## Names

A suggested layout for a new mod built from these specifications (the power mod itself keeps each device's model in its own folder under `PowerMod\data\`, for example `\PowerMod\data\battery_adapter\PM_BatterySlot.p3d`; see `proxy-attachment-config.md`):

```text
\MyMod\devices\push_button.p3d, battery_adapter.p3d, sorter_6out.p3d,
               wall_switch.p3d, generator_floor.p3d, cable_1m.p3d, junction_box_6p.p3d
\MyMod\data\devices\push_button_co.paa, push_button_nohq.paa, push_button_smdi.paa, ...
```

- Selections are `<part>_<material or colour>`: `body_housing`, `button_black`, `led_green`, `led_red`, `led_off`, `terminal_positive`, `terminal_negative`, `cable_gland`, `din_clip`, `mount_tab_l`, `mount_tab_r`.
- Memory points are `<device part>_<purpose>`, plus the common `actionPos` (where the player interacts) and `ce_center` (the object's centre): `button_axis`, `switch_axis_x`, `fuel_cap_pivot`.
- Cable ports are `port_input_N` and `port_output_N`, with `N` matching the device script's `AddPort` calls, each paired with a `_dir` point; the cable leaves along the line from the port to its `_dir` point. Without the `_dir` point the cable cannot attach (`memory-and-selections-authoring.md`, "Electrical port convention").

## Common problems

| Problem | Cause | Fix |
|---|---|---|
| The object clips into the ground | Collision box too large or not convex | An 8 to 12 vertex box; look at the Geometry LOD in Object Builder or probe it from script (`_shared/physics/collision-lods.md`). `#show collisions` is not a DayZ command |
| LEDs cannot be seen at a distance | Emissive map too small | 1024 for the LED texture, inside the `_co` or on its own surface |
| Animation stutters | Durations off the frame grid (the mod's rule of thumb at 60 Hz, not measured) | 0.05, 0.1, 0.15, 0.2, 0.3, 0.5 or 0.6 s |
| A cable does not line up | Segment not centred or not along +Z | The segment runs from Z -0.5 m to +0.5 m about its origin (`device-recipes-power.md`) |
| Textures seam or bleed | Islands too close, so mipmaps mix neighbours | Pad between islands and extend each island's colour past its edge. UVs run 0 to 1 at any texture size, so never rescale them for a larger texture |
| Memory points sit wrong in game | The editor origin differs from the `.p3d` origin | Export with the model origin at `[0,0,0]` and check in the p3d inspector |

## Checklist for a new device

- Vertices within the tier budget; collision convex, 8 to 20 vertices, about 10% larger than the visual.
- Memory points checked in a `.p3d` viewer for position and direction; selections complete and not overlapping.
- Animations smooth at 60 Hz; `_co`, `_nohq` and `_smdi` present at the right size, no missing texture colour in game.
- LED colours match the states (green active, red fault, yellow warning).
- `config.cpp` clean; mass realistic with the centre of mass right; glands at 12 mm and M6 holes where the standard asks.
- No floating geometry, degenerate triangles or ngons.
- Tested in game with the power framework loaded; icons and previews made.

Industry standards the designs follow: DIN 43700 (panel instrument frames of 48, 72 and 96 mm), EN 60423 and EN 50262 (metric gland threads M16x1.5 and M20x1.5), IEC 61076 (circular connectors; 12 mm in that mod), RAL 7016. To export from Blender instead of assembling with py3d, the Arma 3 Object Builder add-on for Blender works; the shipped `.p3d` is binarized by Addon Builder (`/dayz-build-pbo`). Object Builder and Buldozer preview a `.p3d` and its animations (`/dayz-launch-objectbuilder`).

## Template

~~~markdown
## <Device name>

What it does in the power grid. Size W x D x H mm, about <mass> kg.

| Part | Shape | Size | Sides | Vertices | Notes |
|---|---|---|---|---|---|
| ... | | | | | |
| Total LOD0 | | | | <X> | |

Memory points: actionPos, ce_center, port_input_N and port_output_N with their _dir points.
Selections: every part that animates or changes texture.
Animations: name, type, values, duration.
LED states: state, selection, meaning.
Textures: surface, _co, _nohq, _smdi.

```cpp
class MyMod_<Device>: Inventory_Base
{
};
```

Mounting limits, connection rules, script hooks.
~~~
