# Battery adapter, generator and cable segment

Worked specifications of three power devices of a third-party electrical power mod: a battery adapter, a floor generator and the cable segment drawn between devices. The shared design language, budgets, names and the LED script calls are in `device-recipes.md`. Coordinates are millimetres with Z up, except the cable segment, which is in metres in the DayZ frame. These describe a mod's models, not vanilla.

Port names match the device script's `AddPort` calls (here `input_1`, `output_1`, `output_2`), and each port needs its `_dir` point or the cable cannot attach (`memory-and-selections-authoring.md`, "Electrical port convention").

## Battery adapter

The link between a battery item and the grid, with regulated DC output. A 156 KB `.p3d`, 80 by 50 by 35 mm, wall mountable, origin at the centre. No animations: LEDs and the script UI show its state.

| Part | Shape | Size | Vertices | Notes |
|---|---|---|---|---|
| Housing | Rounded box | 80 x 50 x 35 mm, 2 mm bevel | 48 | Chamfered edges |
| Battery slot | Box cut | 60 x 40 x 25 mm, boolean | 0 | Recessed top; the battery slides in |
| Cable gland | Cylinder, 16 sides | 12 mm across, 10 mm long | 32 | On the back, standing out 10 mm |
| Terminal posts | 2 cylinders, 12 sides | 6 mm across, 8 mm high | 24 each | Positive red, negative black |
| Mounting tabs | 2 thin plates | 15 x 40 x 3 mm | 24 in all | Left and right, screw holes |
| Total LOD0 | | | about 152 | |

| Memory point | Position | Purpose |
|---|---|---|
| `actionPos` | `[0, 0, 17.5]` | Centre of the battery slot |
| `ce_center` | `[0, 0, 0]` | Centre of the housing |
| `port_input_1` | `[0, -25, 5]` | Cable gland on the back |
| `port_input_1_dir` | `[0, -35, 5]` | 10 mm further back: the cable leaves through the gland |
| `port_output_1` | `[8, 0, 2]` | Positive terminal |
| `port_output_1_dir` | `[8, 0, 12]` | 10 mm above the post: the cable leaves upward |
| `port_output_2` | `[-8, 0, 2]` | Negative terminal |
| `port_output_2_dir` | `[-8, 0, 12]` | |

Selections: `body`, `battery_slot` (dark inside), `terminal_positive`, `terminal_negative`, `led_green`, `led_off`, `cable_gland`, `mount_tab_l`, `mount_tab_r`.

| State | Selection | Meaning |
|---|---|---|
| 0 | `led_green` | A valid battery is in the slot and powered |
| 1 | `led_off` | Empty slot or a battery that does not fit |

| Surface | `_co` | `_nohq` | `_smdi` |
|---|---|---|---|
| Housing | RAL 7016 with label art | Brushed metal | Roughness 0.65, metal 0.3 |
| Terminals | Copper and brass yellow | Machined | Roughness 0.2, metal 1.0 |
| Cable gland | Black rubber spiral | Fine spiral ridges | Roughness 0.85, metal 0.0 |

## Floor generator

A standing power source that charges the grid and burns fuel over time. An 892 KB `.p3d`, 600 by 400 by 500 mm, about 80 kg.

| Part | Shape | Size | Vertices | Notes |
|---|---|---|---|---|
| Housing | Box, 5 mm bevel | 600 x 400 x 500 mm | 160 | Main frame |
| Engine shroud | Box with grille | 500 x 350 x 250 mm | 120 | Top; the vents are in the normal map, not cut |
| Control panel | Tilted face, 15 degrees | 300 x 250 mm | 80 | Front; buttons and gauge |
| Fuel cap | Cylinder, 24 sides | 50 mm across, 20 mm high | 48 | On the side, hinged |
| Exhaust | Bent cylinder, 16 sides | 40 mm across, 300 mm long | 80 | Top rear |
| Feet | 4 cylinders, 12 sides | 25 mm across, 15 mm high | 24 each | Bottom corners |
| Total LOD0 | | | about 584 | |

The housing runs from -300 to 300 mm in X, -200 (rear) to 200 (front) in Y and -250 to 250 in Z about `ce_center`, with +Y as the front like the other devices. The control panel covers Z -225 to 25 on the front face, so its centre is at Z -100.

| Memory point | Position | Purpose |
|---|---|---|
| `fuel_cap_pivot` | `[300, 0, 220]` | Cap hinge on the +X side |
| `panel_pivot` | `[0, 200, 25]` | Top edge of the panel on the front, for its opening |
| `actionPos` | `[0, 200, -100]` | Panel centre on the front |
| `ce_center` | `[0, 0, 0]` | Centre of the generator |
| `port_output_1` | `[300, 0, 80]` | Main output on the +X side |
| `port_output_1_dir` | `[320, 0, 80]` | 20 mm further out: the cable leaves sideways |
| `fuel_input` | `[300, 25, 220]` | Centre of the 50 mm cap opening, 25 mm from the hinge; read by script for fuel |

Selections: `body`, `engine_shroud`, `control_panel`, `fuel_cap`, `exhaust_pipe`, `led_green` (running), `led_yellow` (low fuel), `led_red` (fault, overload, shutdown), `fuel_gauge_indicator` (optional moving needle).

| Animation | Selection | Movement | Duration |
|---|---|---|---|
| `fuel_cap_open` | `fuel_cap` | Rotation about Z (a vertical hinge), 0 to 90 degrees, pivot `[300, 0, 220]` | 0.5 s |
| `panel_cover_open` | `control_panel` | Rotation about X (tilting forward), 0 to 110 degrees, hinge on the top edge `[0, 200, 25]` | 0.6 s |

| State | Selection | Meaning |
|---|---|---|
| 0 | `led_green` | Engine running, grid stable |
| 1 | `led_yellow` | Fuel under 20% |
| 2 | `led_red` | Fault, overheat or overload; shut down |

| Surface | `_co` | `_nohq` | `_smdi` |
|---|---|---|---|
| Housing | RAL 7016 with stickers | Weathered metal | Roughness 0.7, metal 0.2 |
| Engine shroud | Dark grey with grille | Grille ridges | Roughness 0.8, metal 0.05 |
| Control panel | Black phenolic with labels | Embossed legend | Roughness 0.5, metal 0.0 |
| Exhaust | Rusty steel | Corrosion streaks | Roughness 0.9, metal 0.3 |

## Cable segment

The visible piece of cable between two devices, drawn on the client. It is the segment measured in game in `domain-recipes.md`, "A cable segment drawn on the client"; build that one. Fixed length variants and connector ends were not measured and are not part of it.

| LOD | Shape | Sides | Notes |
|---|---|---|---|
| Visual 0 | Open cylinder, radius 0.01 m, 1 m along +Z, centred on the origin | 8 | No end caps |
| Visual 1 | Same | 5 | |
| Visual 2 | Same | 3 | |
| Collision | None | | No Geometry, Fire Geometry or View Geometry |

Put every visual face, in every visual LOD, in the selection `camo`, and wind the faces inward. Give the model a class name with the mod's prefix, because `CfgModels` classes are global across mods. Texture: black rubber with colour bands in the `_co`, a woven pattern in the `_nohq`, roughness 0.8 and metal 0.0 in the `_smdi`.
