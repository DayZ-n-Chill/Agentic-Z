# Push button and wall switch

Worked specifications of two control devices of a third-party electrical power mod: a push button and a wall switch, with their geometry, memory points, selections, animations, LED states, textures and config. The shared design language, budgets and names are in `device-recipes.md`. Coordinates are millimetres with Z up; convert to metres and Y up when you build the `.p3d`.

## Push button

The fullest worked example: generated entirely in Python, a 218 KB `.p3d` with 9 LODs, about 192 vertices at LOD0 (cylinders and a torus), a cap that moves 3 mm, an LED with three states (green, red, off through `hiddenSelections`), 12 procedural textures (rust, wear, dirt, fingerprints, brushed metal), 7 `.rvmat` files including the 3 emissive LED states, and a full `model.cfg`, `config.cpp` and `$PBOPREFIX$`. It is a control point that fires a script event.

Size: 36 mm flange, 30 mm body, 28 mm tall at rest (3 mm flange, 20 mm body, 5 mm of cap above the body), 3 mm travel. The origin is the centre of the flange's underside, so Z runs from 0 to 28 mm.

| Part | Shape | Size | Sides | Vertices | Notes |
|---|---|---|---|---|---|
| Flange | Cylinder | 36 mm across, 3 mm high | 32 | 64 | Wall or panel mount, Z 0 to 3 |
| Body | Cylinder | 30 mm across, 20 mm high | 32 | 64 | On the flange, Z 3 to 23 |
| Cap | Cylinder | 12 mm across, 8 mm high | 16 | 32 | Moves; Z 20 to 28 at rest (3 mm sits in a bore in the body top), Z 17 to 25 pressed |
| LED ring | Torus | 14 mm outside, 2 mm tube | 16 | 32 | Round the cap, set into the body top at Z 23 |
| Total LOD0 | | | | about 192 | |

| Memory point | Position | Purpose |
|---|---|---|
| `button_axis_top` | `[0, 0, 28]` | Start of the travel axis: cap top at rest |
| `button_axis_bot` | `[0, 0, 25]` | End of the axis; top to bottom is the 3 mm travel |
| `actionPos` | `[0, 0, 28]` | Where the player presses |
| `ce_center` | `[0, 0, 14]` | Centre of the object |

Selections: `body`, `button` (the moving cap), `led_green` (on), `led_red` (fault), `led_off` (no power), `flange`.

Animation `button_press`: a translation of the `button` selection along -Z, from `button_axis_top` to `button_axis_bot`, 3 mm in 0.1 s, played once when script triggers it.

| State | Selection | Meaning |
|---|---|---|
| 0 | `led_green` | Active, power flowing |
| 1 | `led_red` | Fault, power cut |
| 2 | `led_off` | No power, standby |

Script switches the LED with `SetObjectTexture` or `SetObjectMaterial` on the hidden selection's index (`P:\scripts\3_game\entities\entityai.c:2881` and `:2884`).

| Surface | `_co` | `_nohq` | `_smdi` |
|---|---|---|---|
| Cap | Glossy black plastic | Fine radial pattern | Roughness 0.3, metal 0.0 |
| LED ring | Colour gradient | Flat | Emissive 1.0 |
| Body | RAL 7016 with logos | Brushed | Roughness 0.65, metal 0.3 |
| Flange | Matte grey | Screw hole dents | Roughness 0.8, metal 0.1 |

All four at 512.

```cpp
class MyMod_PushButton: Inventory_Base
{
    displayName = "Push Button";
    scope = 2;
    model = "\MyMod\devices\push_button.p3d";
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

Where this differs from the Arma way of writing it:

- It has a parent class. `Inventory_Base` is the usual parent of a placeable item (`model-config-and-packing.md`); use the parent the device really needs.
- It uses `weight` in grams, not `mass = 0.2;`. Physics mass is the point mass on the Geometry LOD (`_shared/physics/mass-and-weight.md`).
- It has no `class EventHandlers` with SQF strings. DayZ has no SQF: the start-up and press logic live in the device's Enforce Script class (its constructor and a user action), which is script work.

## Wall switch

A wall mounted toggle for a power branch; a lever at plus or minus 45 degrees shows the state. A 78 KB `.p3d`, 85 by 85 by 15 mm.

| Part | Shape | Size | Vertices | Notes |
|---|---|---|---|---|
| Backplate | Rounded rectangle | 85 x 85 x 10 mm, 2 mm bevel | 32 | Flush mount, screw holes |
| Lever | Thin block | 15 x 8 x 3 mm | 8 | Turns 45 degrees either way |
| Face frame | Raised border | 75 x 75 mm, bevelled | 24 | Round the lever opening |
| Total LOD0 | | | about 64 | |

| Memory point | Position | Purpose |
|---|---|---|
| `switch_axis_x` | two points on the hinge line | The lever's hinge. The mod's file puts both at `[0, 0, 0]`, which makes a zero length axis that turns nothing: spread the two points along X |
| `actionPos` | `[0, 0, 7]` | Lever centre, where the player interacts |
| `ce_center` | `[0, 0, 5]` | Centre of the object |

Selections: `body` (backplate), `switch_lever` (moves), `frame`.

Animation `switch_toggle`: a rotation of `switch_lever` about X (the left to right hinge) from -45 degrees (down) to +45 degrees (up), 0.3 s, centred at 0, toggled by the player.

| Surface | `_co` | `_nohq` | `_smdi` |
|---|---|---|---|
| Backplate | RAL 7016 with a label | Light brushing | Roughness 0.65, metal 0.3 |
| Lever | Black phenolic plastic | Smooth | Roughness 0.3, metal 0.0 |
