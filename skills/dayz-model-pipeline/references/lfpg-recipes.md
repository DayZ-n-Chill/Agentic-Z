# LF_PowerGrid recipes: object specifications to adapt

Seven object specifications from the LF_PowerGrid mod (a third-party electrical power mod), with its design language, vertex budgets and naming habits. Use them as starting points for a new device. They describe that mod's own models, so nothing here is a vanilla fact and none of it was checked on `P:\`; where the source wrote something that cannot work in DayZ, the text says so and gives the DayZ form.

## Overview

**LF_PowerGrid (LFPG)** is a DayZ electrical power system mod adding generators, batteries, switches, cable networks, and control devices. Each object follows strict design and mechanical specifications to ensure mod compatibility and visual cohesion.

This file documents **proven recipes**: geometric, animation, and material specifications extracted from production LFPG objects, tested in that mod and ready to adapt.

How to read the numbers: coordinates in the memory point lists are millimetres in the modelling frame the source used, with Z up. A DayZ model is in metres with Y up, so convert both the unit and the axes when building the `.p3d` (`critical-rules.md` Rule 12). Animation blocks are shorthand specifications, not `model.cfg` syntax; `animations.md` has the real syntax.

---

## Design Language: LFPG Industrial Standard

### Material Palette
- **Primary**: Dark gray painted metal (RAL 7016 anthracite) — Roughness 0.65, Metallic 0.3
- **Accents**: Brushed aluminum (satin finish) — Roughness 0.4, Metallic 1.0
- **Seals**: Black rubber gaskets (matte) — Roughness 0.8, Metallic 0.0
- **Indicators**: Colored LEDs (red, green, yellow) — self-illuminating via emissive maps

### Scale & Dimensions
- **Handheld**: 15–25cm (push buttons, small adapters)
- **Wall-mounted**: 30–50cm (switches, circuit breakers)
- **Tabletop/Floor**: 40–80cm (batteries, sorters, control boxes)
- **Large machinery**: 60–120cm (generators, junction boxes)

### Visual Cues
- **Edges**: Consistent 2–3mm bevels on all major panels
- **Mounting**: DIN-rail tabs or M6 screw holes (embossed into geometry)
- **Cable entry**: Spiral-threaded cable glands (12mm or 16mm std) on device back/sides
- **Labels**: Embossed text (0.5mm recessed) or silk-screened via diffuse map
- **Status**: Colored LEDs visible from operation distance (≥2 meters)

### Texture Resolution Strategy
| Device Size | Diffuse | Normal | SMDI | Notes |
|-------------|---------|--------|------|-------|
| ≤30cm | 512×512 | 512×512 | 512×512 | Handheld — readable detail |
| 31–60cm | 1024×1024 | 1024×1024 | 1024×1024 | Wall panels, buttons |
| 61–120cm | 2048×2048 | 1024×1024 | 1024×1024 | Generators, large cabinets |

---

## Recipe 1: Push Button (Reference Implementation)

**Status**: Production-tested, 218KB p3d

This is the complete worked example of the skill, generated entirely in Python: 9 LODs in a 218KB `.p3d`, 328 vertices at LOD 0 (32 segment cylinders and a dome), an animated button (translation, 3mm travel), an LED with three material states (green, red, off through `hiddenSelections`), 12 procedural textures (rust, wear, dirt, fingerprints, brushed metal), 7 `.rvmat` files including the 3 emissive LED states, and a complete `model.cfg`, `config.cpp` and `$PBOPREFIX$`.

**Purpose**: User-interface control point; activates electrical devices via script event.

**Dimensions**: 30mm diameter, 20mm total height, 3mm button travel.

### Geometry Specification

| Component | Shape | Dimensions | Segments | Vertices | Notes |
|-----------|-------|-----------|----------|----------|-------|
| Main body | Cylinder | Ø30mm, H20mm | 32 | 64 | Base housing, centered at origin |
| Button cap | Cylinder | Ø12mm, H8mm | 16 | 32 | Animated, -3 to 0mm Z travel |
| LED ring | Torus | OD 14mm, tube Ø2mm | 16 | 32 | Embedded 2mm into body top |
| Mounting flange | Cylinder | Ø36mm, H3mm | 32 | 64 | Base for wall/panel mounting |
| **Total LOD0** | — | — | — | **~328** | 32-segment cylinders standard |

### Memory Points (Named Selections)
```
Memory Points:
  - button_axis_top: [0, 0, 20]  (Z-axis rotation for button animation)
  - button_axis_bot: [0, 0, 17]  (second point defining axis)
  - actionPos: [0, 0, 10]         (player interaction center)
  - ce_center: [0, 0, 10]         (electrical center, port location)

Named Selections:
  - body                          (main housing)
  - button                        (animated cap)
  - led_green                     (active/on state)
  - led_red                       (fault state)
  - led_off                       (unpowered state)
  - flange                        (mounting surface)
```

### Animations (1 Total)

**button_press** (translation, Z-axis, 3mm travel, 0.1s phase):
```
Type: Translation
Axis: [0, 0, 1]  (Z, downward)
Source: button (named selection)
Offset: 3mm
Duration: 0.1s (fast click feedback)
Loop: False (one-shot, triggered by script)
```

### LED States (3 Total) — Via Hidden Selections

| State | LED Selection | Color | Meaning |
|-------|---------------|-------|---------|
| 0 | led_green | Green | Device active, power flowing |
| 1 | led_red | Red | Fault detected, power interrupted |
| 2 | led_off | Dark/Off | No power, standby |

Script sets the state by swapping the texture or material of the LED's hidden selection: `SetObjectTexture(0, "\path\to\texture")` on the button object, where 0 is the index in `hiddenSelections[]` (`P:\scripts\3_game\entities\entityai.c:2881`; `SetObjectMaterial` at `:2884` swaps the `.rvmat`). The source wrote this call in Arma SQF form, `setObjectTexture [buttonObj, 0, ...]`, which DayZ does not have.

### Texture Maps (12 Total: 4 Surfaces × 3 Maps Each)

| Surface | Resolution | _co (Diffuse) | _nohq (Normal) | _smdi (SMDI) |
|---------|-----------|---------------|---------------|-------------|
| Button cap | 512×512 | Glossy black plastic | Fine radial pattern | Rough 0.3, metal 0.0 |
| LED ring | 512×512 | RGB gradient map | None (flat) | Emissive 1.0 |
| Body | 512×512 | RAL 7016 + logos | Brushed finish | Rough 0.65, metal 0.3 |
| Flange | 512×512 | Matte gray | Screw hole indents | Rough 0.8, metal 0.1 |

### Configuration Example
```cpp
class lfpg_push_button: Inventory_Base
{
    displayName = "Push Button";
    scope = 2;
    model = "\lfpg_objects\devices\push_button.p3d";
    weight = 200;                 // grams

    class AnimationSources
    {
        class button_press
        {
            source = "user";
            animPeriod = 0.1;
            initPhase = 1;
        };
    };
};
```

Three corrections to the source's version of this block, which was written the Arma way:

- It had no parent class. `Inventory_Base` is the usual parent of a placeable item (`config-and-packing.md`); use the parent the device really needs.
- It had `mass = 0.2;`. A DayZ item's inventory weight is `weight` in grams, and its physics mass is the point mass on the Geometry LOD (`_shared/physics/mass-and-weight.md`).
- It had a `class EventHandlers` with SQF strings (`init = "this call LFPG_fnc_button_init";`, `hit = "this call LFPG_fnc_button_press";`). DayZ has no SQF: the init and press logic live in the object's Enforce Script class (for example its constructor and a user action), which is script work.

---

## Recipe 2: Battery Adapter

**Status**: Production-tested, 156KB p3d

**Purpose**: Interface between battery inventory item and electrical grid; provides DC output regulation.

**Dimensions**: 80×50×35mm (WxDxH), wall-mountable.

### Geometry Specification

| Component | Shape | Dimensions | Segments | Vertices | Notes |
|-----------|-------|-----------|----------|----------|-------|
| Main housing | Rounded box | 80×50×35mm | beveled 2mm | 48 | Chamfered edges, center origin |
| Battery slot | Box cutout | 60×40×25mm (boolean) | — | 0 | Recessed top, battery slides in |
| Cable gland | Cylinder | Ø12mm, L10mm | 16 | 32 | Back side, protruding 10mm |
| Terminal posts | Cylinder (×2) | Ø6mm, H8mm | 12 | 24 each | Positive (red) & negative (black) |
| Mounting tabs | Thin rectangles | 15×40×3mm (×2) | — | 24 total | Left & right sides, screw holes |
| **Total LOD0** | — | — | — | **~450** | Optimized for wall mounting |

### Memory Points & Named Selections
```
Memory Points:
  - actionPos: [0, 0, 17.5]       (center of battery slot, player interaction)
  - ce_center: [0, 0, 5]          (electrical reference point)
  - port_in: [0, -25, 5]          (cable gland back, input)
  - port_out_pos: [8, 0, 2]       (positive terminal output)
  - port_out_neg: [-8, 0, 2]      (negative terminal output)

Named Selections:
  - body                          (main housing, painted metal)
  - battery_slot                  (cutout area, dark interior)
  - terminal_positive             (red post, metallic)
  - terminal_negative             (black post, metallic)
  - led_green                     (connected state)
  - led_off                       (disconnected state)
  - cable_gland                   (threaded insert)
  - mount_tab_l                   (left bracket)
  - mount_tab_r                   (right bracket)
```

### Animations (0 Total)
Static device — all state indicated via LEDs and script UI.

### LED States (2 Total)

| State | LED Selection | Meaning | Trigger |
|-------|---------------|---------|---------|
| 0 | led_green | Battery connected & valid | Battery object in slot, powered |
| 1 | led_off | Disconnected/no battery | Empty slot or incompatible battery |

### Texture Maps (9 Total: 3 Surfaces × 3 Maps)

| Surface | _co (Diffuse) | _nohq (Normal) | _smdi (SMDI) |
|---------|---------------|---------------|-------------|
| Housing | RAL 7016 + label art | Brushed metal texture | Rough 0.65, metal 0.3 |
| Terminals | Copper/brass yellow | Machined finish | Rough 0.2, metal 1.0 |
| Cable gland | Black rubber spiral | Fine spiral ridges | Rough 0.85, metal 0.0 |

---

## Recipe 3: Sorter (6-Output Router)

**Status**: Production-tested, 412KB p3d

**Purpose**: Routes electrical signals/items from 1 input to 6 outputs based on script-defined rules; display panel shows active routes.

**Dimensions**: 200×150×80mm (WxDxH).

### Geometry Specification

| Component | Shape | Dimensions | Segments | Vertices | Notes |
|-----------|-------|-----------|----------|----------|-------|
| Main housing | Rounded box | 200×150×80mm | bevel 3mm | 80 | Central chassis |
| Front panel | Flat rect | 180×70mm | embossed grid | 60 | Grid lines for LED matrix (2×3 outputs) |
| Input port | Cable gland | Ø12mm, L8mm | 16 | 32 | Left side center |
| Output ports (×6) | Cable glands | Ø12mm each | 16 | 32×6 | Right side, 2 columns × 3 rows |
| Status LED strip | Thin bar | 160×8×2mm | flat | 24 | Top front, 6 LEDs mapped |
| DIN-rail clip | Bracket | 30×20×5mm | — | 28 | Back side, for cabinet mounting |
| **Total LOD0** | — | — | — | **~900** | High detail for UI visibility |

### Memory Points & Named Selections
```
Memory Points:
  - actionPos: [0, 0, 40]         (front panel center, UI interaction)
  - ce_center: [0, 0, 0]          (device center, routing reference)
  - port_in: [-100, 0, 0]         (input cable gland, left side)
  - port_out_0: [100, 35, 27]     (output 0, top-right)
  - port_out_1: [100, 35, 0]      (output 1, mid-right)
  - port_out_2: [100, 35, -27]    (output 2, bot-right)
  - port_out_3: [100, -35, 27]    (output 3, top-right lower)
  - port_out_4: [100, -35, 0]     (output 4, mid-right lower)
  - port_out_5: [100, -35, -27]   (output 5, bot-right lower)

Named Selections:
  - body                          (main housing)
  - front_panel                   (display surface)
  - led_strip                     (6 segments, per-output control)
  - input_port, output_port_0–5   (cable glands)
  - din_clip                      (mounting bracket)
```

### Animations (0 Total)
All state shown via LED positions and panel graphics (rendered to texture at runtime).

### LED States (6 Total) — Per-Channel Control

| Output | LED Selection | Color | Script Control |
|--------|---------------|-------|----------------|
| 0–5 | led_strip segments | Green when active | Script toggles per logic |

Via script: one method on the sorter sets the LED of one output, taking the output index and the color state, and swaps that segment's texture or material with `SetObjectTexture` or `SetObjectMaterial`. The source wrote it as an Arma SQF call (`[sorterObj, outputIndex, colorState] call LFPG_fnc_set_sorter_led`); in DayZ it is an Enforce Script method.

### Texture Maps (12 Total: 4 Surfaces × 3 Maps)

| Surface | _co (Diffuse) | _nohq (Normal) | _smdi (SMDI) |
|---------|---------------|---------------|-------------|
| Housing | RAL 7016 + logos | Brushed metal | Rough 0.65, metal 0.3 |
| Front panel | Dark gray + grid overlay | Raised grid lines | Rough 0.7, metal 0.1 |
| Cable glands (×6) | Black rubber | Spiral texture | Rough 0.85, metal 0.0 |
| LED strip | Matte black backing | Flat | Emissive map per state |

---

## Recipe 4: Wall Switch

**Status**: Production-tested, 78KB p3d

**Purpose**: Wall-mounted toggle control for power branches; 45° lever indicates state.

**Dimensions**: 85×85×15mm (WxHxD).

### Geometry Specification

| Component | Shape | Dimensions | Segments | Vertices | Notes |
|-----------|-------|-----------|----------|----------|-------|
| Backplate | Rounded rect | 85×85×10mm | bevel 2mm | 32 | Flush mount, screw holes |
| Toggle lever | Thin rectangle | 15×8×3mm | — | 8 | Rotated ±45° from center |
| Face frame | Raised border | 75×75mm | beveled | 24 | Surrounds toggle cutout |
| **Total LOD0** | — | — | — | **~220** | Ultra-light for performance |

### Memory Points & Named Selections
```
Memory Points:
  - switch_axis_x: [0, 0, 0]      (pivot X, lower point)
  - switch_axis_x: [0, 0, 0]      (pivot X, upper point; as written in the source. Two
                                   identical points make a zero length axis, which cannot
                                   turn anything: spread them along X, the hinge line)
  - actionPos: [0, 0, 7]          (lever center, interact point)
  - ce_center: [0, 0, 5]          (electrical reference)

Named Selections:
  - body                          (backplate)
  - switch_lever                  (animated toggle)
  - frame                         (border surround)
```

### Animations (1 Total)

**switch_toggle** (rotation, X-axis, ±45°, 0.3s phase):
```
Type: Rotation
Axis: [1, 0, 0]  (X, left-right hinge)
Source: switch_lever
Min phase: -45°  (Down position)
Max phase: +45°  (Up position)
Duration: 0.3s
Loop: True (manual toggle)
Offset: 0 (centered neutral)
```

### Texture Maps (6 Total: 2 Surfaces × 3 Maps)

| Surface | _co (Diffuse) | _nohq (Normal) | _smdi (SMDI) |
|---------|---------------|---------------|-------------|
| Backplate | RAL 7016 + label | Light brushed finish | Rough 0.65, metal 0.3 |
| Lever | Black phenolic plastic | Smooth | Rough 0.3, metal 0.0 |

---

## Recipe 5: Floor Generator

**Status**: Production-tested, 892KB p3d

**Purpose**: Stationary power source; generates electricity to charge grid, consumes fuel over time.

**Dimensions**: 600×400×500mm (WxDxH), ~80kg.

### Geometry Specification

| Component | Shape | Dimensions | Segments | Vertices | Notes |
|-----------|-------|-----------|----------|----------|-------|
| Main housing | Box | 600×400×500mm | bevel 5mm | 160 | Central frame chassis |
| Engine shroud | Box with grille | 500×350×250mm | normal map | 120 | Top section, ventilation (no geometry cuts) |
| Control panel | Angled surface | 300×250mm, 15° tilt | subdivided | 80 | Front face, holds buttons/gauge |
| Fuel cap | Cylinder | Ø50mm, H20mm | 24 | 48 | Side-mounted, hinged cover |
| Exhaust pipe | Cylinder + bend | Ø40mm, L300mm | 16 | 80 | Top rear, exit vent |
| Rubber feet | Cylinder (×4) | Ø25mm, H15mm | 12 each | 24×4 | Bottom corners, isolation |
| **Total LOD0** | — | — | — | **~1900** | Large floor unit, visible detail |

### Memory Points & Named Selections
```
Memory Points:
  - fuel_cap_pivot: [300, 0, 220]  (cap hinge point)
  - panel_pivot: [-250, 0, 150]    (panel top edge for opening animation)
  - actionPos: [-200, 0, 300]      (control panel center, player interact)
  - ce_center: [0, 0, 0]           (generator electrical center)
  - port_out: [250, 0, 80]         (main output cable port)
  - fuel_input: [-150, 180, 100]   (fuel cap opening, for script fuel calc)

Named Selections:
  - body                          (main housing)
  - engine_shroud                 (upper section, ventilation)
  - control_panel                 (angled front face)
  - fuel_cap                      (rotating cap, cover)
  - exhaust_pipe                  (top vent)
  - led_green                     (running, stable output)
  - led_yellow                    (low fuel warning)
  - led_red                       (fault, overload, shutdown)
  - fuel_gauge_indicator          (animated needle, optional)
```

### Animations (2 Total)

**fuel_cap_open** (rotation, 90° hinge):
```
Type: Rotation
Axis: [0, 0, 1]  (Z, vertical hinge)
Source: fuel_cap
Range: 0–90°
Duration: 0.5s
Offset: [300, 0, 220]  (pivot point)
```

**panel_cover_open** (rotation, 110° tilt):
```
Type: Rotation
Axis: [1, 0, 0]  (X, forward tilt)
Source: control_panel
Range: 0–110°
Duration: 0.6s
Offset: [-250, 0, 150]  (top edge hinge)
```

### LED States (3 Total)

| State | LED Selection | Color | Condition |
|-------|---------------|-------|-----------|
| 0 | led_green | Green | Engine running, grid stable |
| 1 | led_yellow | Yellow | Fuel <20%, warning active |
| 2 | led_red | Red | Fault/overheat/overload, shutdown |

### Texture Maps (12 Total: 4 Surfaces × 3 Maps)

| Surface | _co (Diffuse) | _nohq (Normal) | _smdi (SMDI) |
|---------|---------------|---------------|-------------|
| Housing | RAL 7016 + stickers | Weathered metal | Rough 0.7, metal 0.2 |
| Engine shroud | Dark gray + grille | Grille ridges detail | Rough 0.8, metal 0.05 |
| Control panel | Black phenolic + labels | Embossed legend | Rough 0.5, metal 0.0 |
| Exhaust | Rusty steel | Corrosion streaks | Rough 0.9, metal 0.3 (oxidized) |

---

## Recipe 6: Cable Segment (Modular Lengths)

**Status**: Production-tested, scalable

**Purpose**: Connects devices to grid; available in 0.5m, 1m, 2m, 5m lengths.

**Dimensions**: Parameterized length, 8mm outer diameter.

### Geometry Specification

| Component | Shape | Dimensions | Segments | Vertices | Notes |
|-----------|-------|-----------|----------|----------|-------|
| Cable spline | Tube | Ø8mm OD, length L | 8/cross-section | ~100 per 1m | Flexible appearance |
| Connector-A | Cylinder | Ø12mm, L6mm | 12 | 24 | Plug end, indexed texture |
| Connector-B | Cylinder | Ø12mm, L6mm | 12 | 24 | Socket end, indexed texture |
| **Total (1m)** | — | — | — | **~150** | Scales linearly per segment |

### Variants
- **cable_05m.p3d**: 50cm, 75 verts (LOD0)
- **cable_1m.p3d**: 100cm, 150 verts (LOD0)
- **cable_2m.p3d**: 200cm, 300 verts (LOD0)
- **cable_5m.p3d**: 500cm, 750 verts (LOD0)

### Memory Points & Named Selections
```
Memory Points:
  - port_a: [0, 0, 0]             (connector A position)
  - port_b: [L, 0, 0]             (connector B position, L = cable length)

Named Selections:
  - cable_main                    (spline tube body)
  - connector_a                   (input end)
  - connector_b                   (output end)
```

### Texture Maps (3 Total: 2 Surfaces × 3 Maps)

| Surface | _co (Diffuse) | _nohq (Normal) | _smdi (SMDI) |
|---------|---------------|---------------|-------------|
| Cable insulation | Black rubber + color bands | Woven texture | Rough 0.8, metal 0.0 |
| Connector plugs | Brass/chrome | Machined ridges | Rough 0.3, metal 1.0 |

---

## Recipe 7: Junction Box (6-Port Hub)

**Status**: Production-tested, 334KB p3d

**Purpose**: Central hub for multi-device power distribution; splitter/merger logic handled by script.

**Dimensions**: 150×150×100mm (WxDxH).

### Geometry Specification

| Component | Shape | Dimensions | Segments | Vertices | Notes |
|-----------|-------|-----------|----------|----------|-------|
| Main chassis | Rounded box | 150×150×100mm | bevel 2mm | 64 | Central hub structure |
| Cable ports (×6) | Cable glands | Ø12mm each | 16 each | 32×6 | All sides, configurable input/output |
| DIN mounting | Thin bracket | 40×60×3mm | — | 16 | Rear side, standard rail clip |
| Status LED (×6) | Small cylinders | Ø3mm | 8 each | 16×6 | LED indicators for each port |
| **Total LOD0** | — | — | — | **~700** | Distribution hub |

### Memory Points & Named Selections
```
Memory Points:
  - ce_center: [0, 0, 0]          (hub center, routing reference)
  - actionPos: [0, 0, 50]         (top center, UI interaction)
  - port_0: [75, 0, 0]            (port on right face)
  - port_1: [-75, 0, 0]           (port on left face)
  - port_2: [0, 75, 0]            (port on front face)
  - port_3: [0, -75, 0]           (port on rear face)
  - port_4: [0, 0, 50]            (port on top)
  - port_5: [0, 0, -50]           (port on bottom)

Named Selections:
  - body, port_0–5, led_0–5, din_mount
```

### Texture Maps (6 Total: 2 Surfaces × 3 Maps)

| Surface | _co (Diffuse) | _nohq (Normal) | _smdi (SMDI) |
|---------|---------------|---------------|-------------|
| Chassis | RAL 7016 | Brushed metal | Rough 0.65, metal 0.3 |
| Ports | Black rubber | Spiral gland | Rough 0.85, metal 0.0 |

---

## General Recipe Template: Custom LFPG Object

Use this checklist for any new LFPG device:

```markdown
## Recipe: [Device Name]

**Status**: [Alpha/Beta/Production], [file size] p3d
**Purpose**: [What does it do in the power grid?]
**Dimensions**: [WxDxH mm], approx. [mass] kg

### Geometry Specification
| Component | Shape | Dimensions | Segments | Vertices | Notes |
| ... | ... | ... | ... | ... | ... |
| **Total LOD0** | | | | **[X]** | |

### Memory Points & Named Selections
- List all actionPos, ce_center, electrical ports
- List all named selections for animation/texturing

### Animations ([N] Total)
- [name]: [type], [parameters], [duration]

### LED States ([N] Total)
| State | LED | Meaning |

### Texture Maps ([N] Total: [M] Surfaces × 3 Maps)
| Surface | _co | _nohq | _smdi |

### Configuration (Config.cpp)
```cpp
class lfpg_[device_name]
{
    // Class properties
};
```

### Assembly Notes
- [Mounting constraints]
- [Electrical connection rules]
- [Script integration points]
```

---

## Performance Budgets

### Vertex Allocation by Device Type

| Category | LOD0 | LOD1 | LOD2 | LOD3 | Notes |
|----------|------|------|------|------|-------|
| Handheld (≤30cm) | 200–500 | 100–250 | 50–125 | 25–60 | Push buttons, adapters |
| Wall panel (31–60cm) | 500–1000 | 250–500 | 100–250 | 50–125 | Switches, sorters |
| Floor unit (61–120cm) | 1000–2000 | 500–1000 | 250–500 | 125–250 | Generators, junction boxes |
| Machinery (>120cm) | 2000–3000 | 1000–1500 | 500–750 | 250–375 | Large substations |

**Collision geometry (Geometry/Fire/View)**: 8–20 convex verts max per object. Use bounding box approximation.

---

## Naming Conventions

### File Structure
```
\lfpg_objects\devices\
  push_button.p3d
  battery_adapter.p3d
  sorter_6out.p3d
  wall_switch.p3d
  generator_floor.p3d
  cable_1m.p3d
  junction_box_6p.p3d

\lfpg_textures\devices\
  push_button_co.paa
  push_button_nohq.paa
  push_button_smdi.paa
  ... (follow same pattern)
```

### Named Selection Naming
```
[component]_[material/color]
Examples:
  - body_housing
  - button_black
  - led_green, led_red, led_off
  - terminal_positive, terminal_negative
  - cable_gland
  - din_clip
  - mount_tab_l, mount_tab_r
```

### Memory Point Naming
```
[device_specific]_[purpose]
Examples:
  - actionPos              (universal: player interaction)
  - ce_center              (universal: electrical center/reference)
  - button_axis            (button devices)
  - switch_axis_x          (switch devices)
  - fuel_cap_pivot         (generator)
  - port_in, port_out      (power flow direction)
  - port_out_0–5           (multi-port sorters/hubs)
```

---

## Common Pitfalls & Solutions

| Problem | Root Cause | Fix |
|---------|-----------|-----|
| Object clips through terrain | Collision box too large, not convex | Use 8–12 vertex box, then look at the Geometry LOD in Object Builder or probe it from script (`_shared/physics/collision-lods.md`). The source's `#show collisions` is not a DayZ command |
| LEDs not visible at distance | Emissive map resolution too low, not on viewport | Use 1024×1024 for LED texture, embed in diffuse OR use separate surface |
| Animation stutter/jumpy | Keyframe timing not frame-aligned (base 60Hz; the source mod's rule of thumb, not measured) | Use durations: 0.05s, 0.1s, 0.15s, 0.2s, 0.3s, 0.5s, 0.6s |
| Cable doesn't connect visually | Port positions not symmetrical (A vs B) | Verify port_a=[0,0,0], port_b=[L,0,0] for cables; match socket depth |
| Textures seam/repeat poorly | UV layout assumes 512×512, applied to 1024×1024 | Adjust UV scale: 1024 res = 1.0; 2048 res = 2.0 multiplier |
| Memory points offset in-game | Coordinates in editor ≠ exported p3d origin | Re-export with model origin at [0,0,0]; verify in p3d inspector |

---

## Integration Checklist

For each new LFPG object before production release:

- [ ] All vertices < budget for category (see Performance Budgets)
- [ ] Collision box is convex, 8–20 verts, 10% larger than visual
- [ ] Memory points verified in p3d viewer (position + orientation correct)
- [ ] Named selections complete and non-overlapping
- [ ] Animations tested at 60 Hz base (smooth, no jitter)
- [ ] All textures (\_co, \_nohq, \_smdi) present, correct resolution, no pink missing texture
- [ ] LED colors map to electrical states (green=active, red=fault, yellow=warning)
- [ ] Config.cpp syntax validated (no stray commas, brackets matched)
- [ ] Device mass realistic (kg), center of mass correct
- [ ] Cable/port positions match standard (Ø12mm glands, M6 screw holes)
- [ ] Scanned for floating geo, degenerate tris, N-gons (all quads/tris)
- [ ] Tested in vanilla DayZ + LFPG mod loaded
- [ ] Icon/texture previews generated for server/config display

---

## References & Standards

- **DIN 43700**: Industrial rack/cabinet mounting (59mm pitch, 84.1mm centers)
- **DIN 43305**: Cable gland threads (M16×1.5, M20×1.5 standard)
- **IEC 61076**: Circular connectors (12mm Ø standard in LFPG)
- **RAL 7016**: Anthracite gray, industrial standard
- **Blender with the Arma 3 Object Builder add-on**: one way to export a `.p3d` from Blender instead of assembling it with py3d; the final binarized `.p3d` comes from Addon Builder (`/dayz-build-pbo`)
- **DayZ Tools**: Object Builder and Buldozer to inspect a `.p3d` and preview its animations (`/dayz-launch-objectbuilder`)

---

These recipes are version 1.0 of the mod's specification, last updated 2026-03-28, for LFPG v2.8 and later.
