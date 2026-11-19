# Sorter and junction box

Worked specifications of two distribution devices of a third-party electrical power mod: a six output sorter and a six port junction box. The shared design language, budgets, names and the LED script calls are in `device-recipes.md`. Coordinates are millimetres with Z up. These describe a mod's models, not vanilla.

Each port needs a `_dir` point named after the device script's `AddPort` call, or the cable cannot attach (`memory-and-selections-authoring.md`, "Electrical port convention").

## Sorter

Routes power or items from one input to six outputs by rules set in script; a front panel shows the active routes. A 412 KB `.p3d`, 200 by 150 by 80 mm. No animations: LEDs and panel graphics show the state.

| Part | Shape | Size | Vertices | Notes |
|---|---|---|---|---|
| Housing | Rounded box, 3 mm bevel | 200 x 150 x 80 mm | 80 | Main body |
| Front panel | Flat plate with an embossed grid | 180 x 70 mm | 60 | Grid for the 2 by 3 LED layout |
| Input port | Gland, 16 sides | 12 mm across, 8 mm long | 32 | Middle of the left side |
| Output ports | 6 glands, 16 sides | 12 mm across | 32 each | Right side, 2 columns of 3 |
| Status LED strip | Thin bar | 160 x 8 x 2 mm | 24 | Top front, one LED per output |
| DIN rail clip | Bracket | 30 x 20 x 5 mm | 28 | Back, for cabinet mounting |
| Total LOD0 | | | about 416 | |

| Memory point | Position | Purpose |
|---|---|---|
| `actionPos` | `[0, 75, 0]` | Panel centre on the +Y front |
| `ce_center` | `[0, 0, 0]` | Centre of the housing |
| `port_input_1` | `[-100, 0, 0]` | Input gland, left side |
| `port_input_1_dir` | `[-110, 0, 0]` | |
| `port_output_1` to `port_output_3` | `[100, 35, 27]`, `[100, 35, 0]`, `[100, 35, -27]` | Front column, top to bottom |
| `port_output_4` to `port_output_6` | `[100, -35, 27]`, `[100, -35, 0]`, `[100, -35, -27]` | Rear column, top to bottom |
| `port_output_N_dir` | Each output moved 10 mm further along +X | For example `port_output_1_dir` at `[110, 35, 27]` |

Selections: `body`, `front_panel`, `led_strip` (six segments, one per output), `input_port`, `output_port_1` to `output_port_6`, `din_clip`.

Each output's LED segment turns green when that output is active. Write one Enforce Script method on the sorter that takes the output index and the colour state and swaps that segment's texture or material with `SetObjectTexture` or `SetObjectMaterial`; an SQF function call does not exist in DayZ.

| Surface | `_co` | `_nohq` | `_smdi` |
|---|---|---|---|
| Housing | RAL 7016 with logos | Brushed metal | Roughness 0.65, metal 0.3 |
| Front panel | Dark grey with a grid | Raised grid lines | Roughness 0.7, metal 0.1 |
| Glands | Black rubber | Spiral | Roughness 0.85, metal 0.0 |
| LED strip | Matte black backing | Flat | Emissive map per state |

## Junction box

A central hub that splits or merges power between devices; the logic is in script. A 334 KB `.p3d`, 150 by 150 by 100 mm.

| Part | Shape | Size | Vertices | Notes |
|---|---|---|---|---|
| Chassis | Rounded box, 2 mm bevel | 150 x 150 x 100 mm | 64 | Main body |
| Cable ports | 6 glands, 16 sides | 12 mm across | 32 each | On every side, input or output |
| DIN mount | Thin bracket | 40 x 60 x 3 mm | 16 | Back, rail clip |
| Status LEDs | 6 small cylinders, 8 sides | 3 mm across | 16 each | One per port |
| Total LOD0 | | | about 368 | |

| Memory point | Position | Purpose |
|---|---|---|
| `ce_center` | `[0, 0, 0]` | Centre of the hub |
| `actionPos` | `[0, 0, 50]` | Top centre |
| `port_input_1`, `port_input_2`, `port_input_3` | `[-75, 0, 0]`, `[0, -75, 0]`, `[0, 0, -50]` | Left, rear and bottom faces |
| `port_output_1`, `port_output_2`, `port_output_3` | `[75, 0, 0]`, `[0, 75, 0]`, `[0, 0, 50]` | Right, front and top faces |
| `_dir` points | Each port moved 10 mm further out along its face normal | For example `port_output_1_dir` at `[85, 0, 0]` |

Selections: `body`, `port_0` to `port_5`, `led_0` to `led_5`, `din_mount`. Which ports are inputs and which outputs is the device script's choice; name each memory point after the `AddPort` call that uses it.

| Surface | `_co` | `_nohq` | `_smdi` |
|---|---|---|---|
| Chassis | RAL 7016 | Brushed metal | Roughness 0.65, metal 0.3 |
| Ports | Black rubber | Spiral gland | Roughness 0.85, metal 0.0 |
