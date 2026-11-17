# model.cfg animations for generated objects

A worked reference for the `model.cfg` side of an object this skill generates: skeleton, animation types, config sources, script control, memory axes and complete examples. The facts checked against vanilla live in the animation pack (`_shared/animation/README.md`): open `model-cfg-animations.md` there for what shipped models store (the fence gate runs 0 to 100, the barrel lids hide at 0.6) and `script-hooks.md` for the script calls. Where this file cites `P:\`, the line was opened and confirmed; the rest is `model.cfg` format knowledge and measurements on mod models, which no vanilla text file on `P:\` shows (vanilla ships `model.cfg` only inside its binarized models).

## 1. Model.cfg Structure Overview

The animation system requires two main class blocks in `model.cfg`:

### CfgSkeletons (Bone Structure)

Defines the bone hierarchy used by animations:

```cpp
class CfgSkeletons {
    class MyObject_Skeleton {
        isDiscrete = 1;                    // 1 for mechanical objects (no interpolation)
        skeletonInherit = "";              // empty for new skeleton, or inherit from parent
        skeletonBones[] = {
            "switch", "",                  // bone_name, parent_bone (empty = root)
            "button", "",
            "led_indicator", "",
            "cover", ""
        };
    };
};
```

**Key Points:**
- `isDiscrete = 1` → Mechanical objects (switches, doors). Prevents interpolation artifacts.
- `isDiscrete = 0` → Smooth/organic movement (flags, cloth).
- Both values are Binarize format knowledge: a shipped model does not show which one it was built with.
- Parent `""` = root bone (world origin). Most DayZ objects use root for all bones.
- Bone names must match selection names in the p3d file.

### CfgModels (Visual Properties & Animations)

Defines model appearance and animation classes:

```cpp
class CfgModels {
    class Default {
        // base class - empty
    };

    class MyObject: Default {
        skeletonName = "MyObject_Skeleton";  // link to skeleton
        sections[] = {
            "led_green",
            "led_red"                        // hiddenSelections for material swaps
        };
        class Animations {
            // animation definitions here (see section 2)
        };
    };
};
```

**sections[]** = Named selections that can have materials swapped via `SetObjectTexture()`.

---

## 2. Animation Types (Complete Syntax)

### ROTATION (Most Common)

For rotating parts: switches, dials, valves, lids.

```cpp
class switch_rotate {
    type = "rotation";
    source = "switch_state";              // AnimationSource name (from config.cpp)
    selection = "switch";                 // Named selection in p3d (must match bone)
    axis = "switch_axis";                 // 2 memory points defining rotation axis
    minValue = 0;                         // source value at angle0
    maxValue = 1;                         // source value at angle1
    angle0 = 0;                           // radians when source = minValue
    angle1 = "rad 45";                    // radians when source = maxValue
    // angle1 = 0.7854;                   // alternative: direct radians (45° = 0.7854)
};
```

**How it works:**
- The axis is a line in 3D space defined by two memory points.
- When `source` = minValue, the selection rotates by `angle0` around the axis.
- When `source` = maxValue, the selection rotates by `angle1` around the axis.
- Linear interpolation between minValue and maxValue.
- Right-hand rule: thumb along axis, fingers curl = positive rotation direction.

---

### TRANSLATION (Linear Movement)

For moving parts: buttons, sliders, drawers, pistons.

```cpp
class button_press {
    type = "translation";
    source = "button_state";
    selection = "button";
    axis = "button_axis";                 // 2 memory points, direction = point1 → point2; 1 m long here
    minValue = 0;
    maxValue = 1;
    offset0 = 0;                          // in lengths of the axis, when source = minValue
    offset1 = 0.003;                      // 3mm when source = maxValue, on this 1 m axis
};
```

**How it works:**
- Translation follows the axis direction (from point 1 to point 2 of the axis).
- `offset0` and `offset1` count lengths of the axis, not metres (inferred from vanilla data, not measured in game: section 5, Placement Rules, rule 3): on a 1 m axis `offset0` = 0, `offset1` = 0.003 travel 3mm; on a 1 cm axis the same values travel 0.03mm.
- At source = 0.5, the selection moves half of that, 1.5mm on the 1 m axis.
- Movement is linear with source value.

*(Corrected 2026-10-03: the comments read "meters movement when source = minValue" and "3mm when source = maxValue", and the bullets "`offset0` = 0, `offset1` = 0.003 means travel 3mm total." and "At source = 0.5, the selection moves 1.5mm along the axis.", true only on a 1 m axis.)*

---

### HIDE (Show/Hide Based on State)

For discrete visibility: LED indicators, cover panels, interchangeable parts.

```cpp
class hide_cover {
    type = "hide";
    source = "cover_open";
    selection = "cover";
    minValue = 0;
    maxValue = 1;
    hideValue = 0.5;                      // hidden when source >= hideValue
};
```

**How it works:**
- When `source >= hideValue` → selection is hidden.
- When `source < hideValue` → selection is visible.
- No intermediate states: binary on/off.

**Variant: Hide with Inverse Logic**
```cpp
class hide_battery_missing {
    type = "hide";
    source = "battery_missing";
    selection = "battery";
    hideValue = 0.5;
    minValue = 0;
    maxValue = 1;
    // Script sets the source to 1 while no battery is installed: source >= 0.5, the battery mesh is hidden
    // Script sets the source to 0 once a battery is installed: source < 0.5, the battery mesh is visible
};
```

---

### ROTATIONX, ROTATIONY, ROTATIONZ (Axis-Locked)

For rotation around a single fixed axis: dials with full 360° rotation.

```cpp
class dial_rotate {
    type = "rotationZ";                   // Z axis rotation
    source = "dial_value";
    selection = "dial";
    axis = "";                            // NOT needed for axis-locked types
    angle0 = 0;                           // radians at minValue
    angle1 = "rad 270";                   // 270° = 3/4 rotation at maxValue
    minValue = 0;
    maxValue = 1;
};
```

**Axis-Locked Types:**
- `rotationX` → Rotate around X axis (pitch)
- `rotationY` → Rotate around Y axis (yaw)
- `rotationZ` → Rotate around Z axis (roll)

**When to use:**
- Use when you only need rotation on one axis and the axis never changes.
- More stable than "rotation" type for full 360° (avoids gimbal lock).
- Axis memory points NOT required.

---

## 3. Animation Sources (config.cpp)

Define animation sources in the object's config.cpp class:

```cpp
class CfgVehicles {
    class MyObject: HouseNoDestruct {
        model = "\path\to\myobject.p3d";
        displayName = "My Device";

        class AnimationSources {
            class switch_state {
                source = "user";           // "user" = script-controlled
                initPhase = 0;             // initial value (0.0 to 1.0)
                animPeriod = 0.5;          // seconds to complete full animation
                sound = "";                // optional click sound EH
            };

            class button_state {
                source = "user";
                initPhase = 0;
                animPeriod = 0.1;          // faster: 100ms button press
            };

            class cover_open {
                source = "user";
                initPhase = 0;
                animPeriod = 0.8;          // slower: 800ms for smooth reveal
            };
        };
    };
};
```

**Key Properties:**

| Property | Purpose |
|----------|---------|
| `source = "user"` | Script controls animation via SetAnimationPhase() |
| `initPhase = X` | Starting value (0.0 = minValue, 1.0 = maxValue) |
| `animPeriod = X` | Time in seconds to complete full animation (0→1 range) |
| `sound = "..."` | Sound event hash (optional) |

`animPeriod` is not the duration of a single `SetAnimationPhase` call. It is the time per unit of phase: with a 0 to 1 range it is the time the animation takes to play from phase 0 to phase 1. If you call `SetAnimationPhase("switch_state", 1.0)` with `animPeriod = 0.5`, the animation visually plays over 0.5 seconds. Vanilla's fence gate runs 0 to 100 with `animPeriod=0.018`, about 1.8 seconds for the full swing (`_shared/animation/animation-sources.md`).

`sound` in a source was not found in the vanilla sources read for the animation pack; treat it as unverified.

---

## 4. Script Control (Enforce Script)

### Setting the phase

```cpp
// Set animation phase (0.0 = minValue, 1.0 = maxValue)
SetAnimationPhase("switch_state", 1.0);

// Get current phase
float currentPhase = GetAnimationPhase("switch_state");

// Example: Toggle switch
if (GetAnimationPhase("switch_state") < 0.5) {
    SetAnimationPhase("switch_state", 1.0);  // on
} else {
    SetAnimationPhase("switch_state", 0.0);  // off
}
```

Change the state on the server, then make every client end on the same phase. The phase is not synced for you: vanilla's barrel keeps its open state in a net synced variable and calls `SetAnimationPhase` on each client from `OnVariablesSynchronized` (`P:\scripts\4_world\entities\itembase\barrel_colorbase.c:158`, which calls `UpdateVisualState` at `:144`). The screen pattern at the end of this file follows the vanilla way. The two vanilla patterns are in `_shared/animation/script-hooks.md`.

### Complete Example: Toggle Switch (EventHandler)

```cpp
// In config.cpp AnimationSources
class switch_state {
    source = "user";
    initPhase = 0;
    animPeriod = 0.3;
};

// In Enforce Script (on the object instance)
void ToggleSwitch() {
    float phase = GetAnimationPhase("switch_state");
    if (phase < 0.5) {
        SetAnimationPhase("switch_state", 1.0);  // animation plays to 1.0 over 0.3s
    } else {
        SetAnimationPhase("switch_state", 0.0);  // animation plays to 0.0 over 0.3s
    }
}
```

---

## 5. Memory Points for Axes

In Blender or Object Builder, create a Memory LOD with axis definition points.

### Axis Structure

Each animation using an axis requires exactly 2 memory points in the Memory LOD:

```
Axis Name: "switch_axis"
├── Point 1: (0, 0, 0.05)    [line start]
└── Point 2: (0, 0, -0.05)   [line end]
```

The axis vector is: Point2 - Point1 = direction of rotation/translation.

### Placement Rules

1. **Rotation Axis:**
   - Place at the pivot point of the rotating part.
   - Direction (P1→P2) determines rotation axis.
   - Right-hand rule applies: curl fingers in rotation direction, thumb points along axis.

   Example: Door hinge at bottom-left corner:
   ```
   "door_axis"
   P1: (-0.5, 0, 0)     [bottom of hinge]
   P2: (-0.5, 1, 0)     [top of hinge, axis = Y direction]
   Rotation: Y axis (yaw) opens/closes door
   ```

2. **Translation Axis:**
   - P1→P2 vector = direction and magnitude reference: an offset of 1 moves the selection by the whole P1→P2 vector (rule 3).
   - `offset` values apply along this direction.
   - Example: Sliding panel moving left 0.2m:
   ```
   "panel_slide_axis"
   P1: (0, 0, 0)
   P2: (-1, 0, 0)       [1 m long, so offset1 reads in metres]
   offset1 = 0.2        [moves -0.2m in X]
   ```

3. **Scale:**
   - Rotation: only the direction matters; (0,0,0)→(0,0,1) and (0,0,0)→(0,0,100) are the same Z axis.
   - Translation: the length matters (inferred from vanilla data, not measured in game; next bullet). `offset0`/`offset1` count lengths of the axis, so the selection moves `offset × |P2 − P1|`. To move `d` metres, make the axis `d` long with `offset1 = 1`, or 1 m long with `offset1 = d`. A short axis with an offset written in metres barely moves: 0.003 on a 1 cm axis is 0.03 mm.
   - [EXACT] What was read on 2026-10-03, and what is inferred from it. Read: Binarize stores a translation's offsets as `model.cfg` writes them and its axis at its own length. One mod's `model.cfg` (a tray) writes `offset1 = 1` on twelve drift axes 12.1 to 16.2 mm long, and the binarized tray of the same build (ODOL v55) stores 1.0, with each axis at its source length; a compiler that converted metres to axis lengths would have stored 62 to 83. The binarized vanilla `DZ\weapons\firearms\m249\m249.p3d` (ODOL v54, from an older binarizer, assumed to keep offsets the same way) therefore carries the offsets its authors wrote: `bulletMove000` to `bulletMove011` and the `linkMove*` classes run from −1 to 0 on axes 1.11 to 1.15 cm long, about the pitch of a belt link; `bolt_pull_1` runs from 0 to +1 on an 8.34 cm axis; `magazine_reload_move_1` runs from 0 to +1.45 on a 10 cm axis. Its rotation axes, in contrast, are stored as unit vectors, as wheel axes are (the animation sign and axis notes in the vehicles pack, `_shared/vehicles/README.md`). Inferred, not measured in game: the engine moves a selection by the offset times that stored axis; read as metres, the m249's belt would jump a metre per round. The `dayz-3d-viewer` skill plans the same formula for its animation preview, not yet implemented. A 1 m axis gives the same travel under either reading, which is why the vehicles material recommends making a translation's memory axis exactly 1 m long. The animation pack states the same unit: offsets are in axis lengths (`_shared/animation/model-cfg-animations.md`).

   *(Corrected 2026-10-03: this rule read "Axis vector doesn't define scale; only direction matters." and "Can use (0,0,0)→(0,0,1) or (0,0,0)→(0,0,100) — both are Z axis." for every axis, and rule 2's example called its 1 m axis "[normalized to -X direction]".)*

---

## 6. Skeleton Bones

Bones form the animated skeleton. Each animated selection must have a corresponding bone.

### Basic Skeleton (Flat Hierarchy)

Most DayZ objects use flat hierarchy (all bones parented to root):

```cpp
class CfgSkeletons {
    class SimpleDevice_Skeleton {
        isDiscrete = 1;
        skeletonBones[] = {
            "switch", "",      // all rooted
            "button", "",
            "cover", "",
            "led", ""
        };
    };
};
```

### Hierarchical Skeleton (Chains)

For multi-part movements (arm → forearm → hand):

```cpp
class Arm_Skeleton {
    isDiscrete = 1;
    skeletonBones[] = {
        "arm", "",           // root
        "forearm", "arm",    // child of arm
        "hand", "forearm"    // child of forearm
    };
};
```

Parent relationships:
- Child inherits parent's transformation.
- If `arm` rotates 45°, `forearm` and `hand` rotate with it.
- Then `forearm` rotates an additional amount independently.

### Requirements

- Bone name must match the selection name in the p3d.
- Each selection to be animated needs a bone.
- Non-animated selections don't need bones.
- Parent bone must be declared BEFORE child bone in skeletonBones[].

---

## 7. Named Selections Across LODs

DayZ p3d files use multiple LODs: Resolution, Geometry, Fire, View, etc.

### Animated Selections

- They must exist in every visual (Resolution) LOD that should show the movement.
- The vertices in the selection = vertices that move with animation.
- They are needed in the Geometry, Fire Geometry and View Geometry LODs only where the collision should move with the part. A small switch or button can leave them out; a door leaf cannot. Vanilla building doors carry the `doorsN` selection in every LOD that matters (`_shared/models/selections.md`), and the animation pack's naming checklist says the same.

### Named Selection Best Practice

The LOD names stand for the resolution values in `_shared/conventions/assets.md`.

```
MyObject.p3d
├── Visual LODs (0 or 1, then 2, 3, ...)
│   ├── Mesh
│   │   ├── switch (named selection, will animate)
│   │   ├── button
│   │   ├── cover
│   │   └── housing
│   └── Named Selections: switch, button, cover
│
├── Geometry LOD (1.0e+13)
│   └── Mesh
│       ├── switch, button, cover, housing as ComponentNN convex parts
│       └── animated selections only where the collision must move
│
└── Memory LOD (1.0e+15)
    └── switch_axis, button_axis, cover_axis (axis memory points)
```

### Selection Priority

If a vertex is in multiple named selections (third-party mod behaviour, not measured against vanilla):
- The LAST animation in the Animations class wins.
- Example: If "button" vertex is in both "button" and "housing", and both have animations, the button animation takes precedence.

---

## 8. Common Animation Patterns for DayZ Devices

### Toggle Switch (On/Off)

```cpp
// model.cfg
class switch_on_off {
    type = "rotation";
    source = "switch_state";
    selection = "switch";
    axis = "switch_axis";
    minValue = 0;
    maxValue = 1;
    angle0 = "rad -22.5";    // -22.5° at OFF (0)
    angle1 = "rad 22.5";     // +22.5° at ON (1)
};

// config.cpp
class switch_state {
    source = "user";
    initPhase = 0;
    animPeriod = 0.3;
};
```

### Push Button (Momentary)

```cpp
class button_press {
    type = "translation";
    source = "button_state";
    selection = "button";
    axis = "button_axis";
    minValue = 0;
    maxValue = 1;
    offset0 = 0;             // resting
    offset1 = 0.003;         // 3mm down on a 1 m axis (section 5, rule 3)
};

// config.cpp animPeriod
class button_state {
    source = "user";
    initPhase = 0;
    animPeriod = 0.1;        // 100ms press/release
};

// Script (resets button after press)
void PressButton() {
    SetAnimationPhase("button_state", 1.0);
    GetGame().GetCallQueue(CALL_CATEGORY_SYSTEM).CallLater(ReleaseButton, 150);  // 150ms
}

void ReleaseButton() {
    SetAnimationPhase("button_state", 0.0);
}
```

`CallLater` takes the function itself, then the delay in milliseconds (`P:\scripts\2_gamelib\tools.c:61`); the form with an object and a function name is `CallLaterByName` (`:63`). Passing `this, "ReleaseButton"` to `CallLater` matches neither signature.

### Hinged Door/Lid (90° Swing)

```cpp
class lid_open {
    type = "rotation";
    source = "lid_state";
    selection = "lid";
    axis = "lid_hinge";      // hinge axis (usually Y for vertical hinge)
    minValue = 0;
    maxValue = 1;
    angle0 = 0;              // closed
    angle1 = "rad 90";       // 90° open
};

// config.cpp
class lid_state {
    source = "user";
    initPhase = 0;
    animPeriod = 0.8;        // smooth 800ms open
};
```

### Multi-State Dial (Discrete Positions)

```cpp
class dial_select {
    type = "rotationZ";      // full 360° rotation
    source = "dial_state";
    selection = "dial";
    angle0 = 0;
    angle1 = "rad 360";      // full rotation
    minValue = 0;
    maxValue = 1;
};

// config.cpp
class dial_state {
    source = "user";
    initPhase = 0;
    animPeriod = 0.5;
};

// Script: 4 discrete positions
void SetDialPosition(int position) {
    // position: 0, 1, 2, 3
    float phase = position / 4.0;  // 0.0, 0.25, 0.5, 0.75
    SetAnimationPhase("dial_state", phase);
}
```

### Sliding Panel (Drawer)

```cpp
class drawer_slide {
    type = "translation";
    source = "drawer_state";
    selection = "drawer";
    axis = "drawer_axis";    // axis points along slide direction (-X)
    minValue = 0;
    maxValue = 1;
    offset0 = 0;             // fully closed
    offset1 = 0.4;           // 40cm extended on a 1 m axis (section 5, rule 3)
};

// config.cpp
class drawer_state {
    source = "user";
    initPhase = 0;
    animPeriod = 0.6;
};
```

---

## 9. Multiple Animations

A single object can have many animations controlled independently or together.

### Independent Animations (Different Sources)

```cpp
class Animations {
    class switch_rotate {
        type = "rotation";
        source = "switch_state";
        selection = "switch";
        // ...
    };

    class button_press {
        type = "translation";
        source = "button_state";
        selection = "button";
        // ...
    };

    class led_indicator {
        type = "hide";
        source = "led_state";
        selection = "led";
        hideValue = 0.5;
    };
};
```

Script controls each independently:
```cpp
SetAnimationPhase("switch_state", 1.0);  // switch moves
SetAnimationPhase("button_state", 1.0);  // button moves
SetAnimationPhase("led_state", 1.0);     // LED shows
// All three happen at the same time, but driven by different sources
```

### Linked Animations (Same Source)

Multiple animations can share a source to move together:

```cpp
class Animations {
    class door_left {
        type = "rotation";
        source = "both_doors";  // SAME source
        selection = "door_left";
        axis = "door_left_axis";
        angle0 = 0;
        angle1 = "rad 90";
    };

    class door_right {
        type = "rotation";
        source = "both_doors";  // SAME source
        selection = "door_right";
        axis = "door_right_axis";
        angle0 = 0;
        angle1 = "rad -90";     // opposite direction
    };
};
```

Script:
```cpp
SetAnimationPhase("both_doors", 0.5);  // both doors move together at phase 0.5
```

---

## 10. Complete Working Example: Industrial Switch Box

Full functional example: a device with toggle switch, push button, RGB LED (material swap), and hinged cover.

### model.cfg

```cpp
class CfgSkeletons {
    class SwitchBox_Skeleton {
        isDiscrete = 1;
        skeletonBones[] = {
            "switch", "",
            "button", "",
            "cover", "",
            "led_indicator", ""
        };
    };
};

class CfgModels {
    class Default {};

    class SwitchBox: Default {
        skeletonName = "SwitchBox_Skeleton";
        sections[] = {"led_green", "led_red", "led_blue"};

        class Animations {
            class switch_toggle {
                type = "rotation";
                source = "switch_state";
                selection = "switch";
                axis = "switch_axis";
                minValue = 0;
                maxValue = 1;
                angle0 = "rad -30";
                angle1 = "rad 30";
            };

            class button_press {
                type = "translation";
                source = "button_state";
                selection = "button";
                axis = "button_axis";
                minValue = 0;
                maxValue = 1;
                offset0 = 0;
                offset1 = 0.005;
            };

            class cover_hinge {
                type = "rotation";
                source = "cover_state";
                selection = "cover";
                axis = "cover_hinge_axis";
                minValue = 0;
                maxValue = 1;
                angle0 = 0;
                angle1 = "rad 120";
            };

            class led_hide {
                type = "hide";
                source = "led_state";
                selection = "led_indicator";
                minValue = 0;
                maxValue = 1;
                hideValue = 0.5;
            };
        };
    };
};
```

### config.cpp

```cpp
class CfgVehicles {
    class HouseNoDestruct;

    class SwitchBox: HouseNoDestruct {
        model = "\path\to\switchbox.p3d";
        displayName = "Industrial Switch Box";
        descriptionShort = "Functional control panel";

        class AnimationSources {
            class switch_state {
                source = "user";
                initPhase = 0;
                animPeriod = 0.4;
            };

            class button_state {
                source = "user";
                initPhase = 0;
                animPeriod = 0.15;
            };

            class cover_state {
                source = "user";
                initPhase = 0;
                animPeriod = 1.0;
            };

            class led_state {
                source = "user";
                initPhase = 0;
                animPeriod = 0.2;
            };
        };
    };
};
```

### Usage (Enforce Script)

The methods below belong in the object's own script class, so the calls run on the object itself. A ternary, a three argument `SetObjectTexture` and `CallLater(this, "name", ...)` do not compile in Enforce Script; the block uses calls that exist. `SetObjectTexture(int index, string texture_name)` is a method of the object and takes the hidden selection index (`P:\scripts\3_game\entities\entityai.c:2881`), `CreateObjectEx` needs its flags argument and returns an `Object` to cast (`P:\scripts\3_game\global\game.c:703`), and Enforce Script has no ternary operator (`_shared/enscript/patterns/language_workarounds.md`). The full script is script work (`dayz-script-specialist`).

```cpp
// Spawning one (server side)
SwitchBox switchBox = SwitchBox.Cast(GetGame().CreateObjectEx("SwitchBox", position, ECE_PLACE_ON_SURFACE));

// Toggle switch
void ToggleSwitch() {
    if (GetAnimationPhase("switch_state") < 0.5) {
        SetAnimationPhase("switch_state", 1.0);
        SetObjectTexture(0, "\path\to\led_green.paa");  // green LED
    } else {
        SetAnimationPhase("switch_state", 0.0);
        SetObjectTexture(0, "\path\to\led_red.paa");    // red LED
    }
}

// Press button with release
void PressButton() {
    SetAnimationPhase("button_state", 1.0);
    GetGame().GetCallQueue(CALL_CATEGORY_SYSTEM).CallLater(ReleaseButton, 100);
}

void ReleaseButton() {
    SetAnimationPhase("button_state", 0.0);
}

// Open cover
void OpenCover() {
    SetAnimationPhase("cover_state", 1.0);  // smoothly opens over 1.0 second
}

// Show LED when condition met
void SetLEDActive(bool active) {
    if (active) {
        SetAnimationPhase("led_state", 1.0);
    } else {
        SetAnimationPhase("led_state", 0.0);
    }
}
```

---

## 11. Common Mistakes & Troubleshooting

| Problem | Cause | Solution |
|---------|-------|----------|
| Animation doesn't work (no error) | Axis points not in Memory LOD | Add axis memory points to Memory LOD in editor |
| Silent failure, no animation | Selection name mismatch (p3d vs model.cfg) | Verify the selection name matches letter for letter. Keep the case identical too, although matching ignores case: the shipped barrel stores `lid` while its config says `class Lid` (`_shared/animation/model-cfg-animations.md`) |
| Crash on load | Missing bone in skeleton | Add bone to `skeletonBones[]` for every animated selection |
| Animation jittery/twitchy | `isDiscrete = 0` on mechanical object | Set `isDiscrete = 1` for mechanical parts |
| Animation plays instantly | `animPeriod = 0` | Set `animPeriod` to > 0 (e.g., 0.5 seconds) |
| Animation doesn't reach maxValue | Axis vector is zero | Ensure axis P1 ≠ P2 (non-zero vector) |
| Wrong rotation direction | Axis vector points wrong way | Swap P1 and P2, or negate angle values |
| Translation barely moves, or leaves the model | Offset written in metres on an axis that is not 1 m long | Offsets count lengths of the axis (section 5, rule 3): make the axis 1 m long and write the travel in metres |
| Multiple animations fight | Same selection in different animations | Ensure each selection is in only one animation |
| Bone inherits wrong transform | Bone parent mismatch | Parent bone must be declared first in `skeletonBones[]` |

*(Note 2026-10-03 on "Multiple animations fight", read from vanilla data: the binarized m249 binds several animations to one bone. One bone carries the magazine's hide, two rotations and five translations, another `bolt_pull_1` and `bolt_pull_2`, and each belt round's bone two hides, a rotation and a translation. Sharing a selection is therefore not by itself the cause; which combinations do fight was not measured.)*

---

## Reference: Radians Conversion

```
"rad 45"   = 45° = 0.7854 radians
"rad 90"   = 90° = 1.5708 radians
"rad 180"  = 180° = 3.1416 radians
"rad 270"  = 270° = 4.7124 radians
"rad 360"  = 360° = 6.2832 radians
```

Use `"rad X"` syntax in model.cfg for readability, or calculate radians directly: `angle = degrees * π / 180`.

---

## Key Takeaways

1. **Skeleton** defines bone hierarchy; each animated selection needs a bone.
2. **Animation classes** in model.cfg link bone to visual result (rotation/translation/hide).
3. **AnimationSources** in config.cpp define the source state and timing.
4. **Memory points** define axes for rotation and translation; must be in Memory LOD.
5. **SetAnimationPhase()** controls animation from script: set the state on the server and apply the phase on clients from the synced state.
6. **isDiscrete = 1** prevents jitter on mechanical objects.
7. **Named selections** must exist in every visual LOD that shows the movement, and in the collision LODs only where the collision moves too.

### Screen on/off: two-layer translation pattern (vs. material swap)

For a device that needs an **emissive lit screen** when "on" and a black
screen when "off", there are two valid approaches. Don't mix them:

**Pattern A — Translation animation over an emissive face (recommended)**

The model has two overlapping face sets in the same selection slot:
- A `screen` selection with the emissive texture (`_Emission.paa`, etc.).
- A `HideScreen` selection with a black/off texture, positioned a hair
  above `screen` so it covers it at rest.

A translation animation physically slides `HideScreen` out of view when
the device is on, exposing the emission underneath:

```cpp
// model.cfg
class HideScreen {
    type       = "translation";
    source     = "user";
    selection  = "HideScreen";
    axis       = "HideScreen_axis";      // 2-point memory axis
    minValue   = 0.0;
    maxValue   = 1.0;
    offset0    = 0.0;
    offset1    = 0.5;                    // 0.5m on a 1 m axis (section 5, rule 3) — well off-screen
};
```

```cpp
// config.cpp — two variants of the same model
class MyDevice_Admin : Inventory_Base  // always-on variant
{
    class AnimationSources { class HideScreen { source="user"; initPhase=1; animPeriod=0.3; }; };
    // HideScreen cover hidden from spawn → emission visible
};

class MyDevice : Inventory_Base         // power-gated variant
{
    class AnimationSources { class HideScreen { source="user"; initPhase=0; animPeriod=0.3; }; };
    // Starts with cover visible (off look); script toggles.
};
```

```c
// Enforce Script: in OnVariablesSynchronized (LFPG_OnVarSync is LF_PowerGrid's own hook for it)
if (m_PoweredNet) SetAnimationPhase("HideScreen", 1.0);  // hide cover → emission shows
else              SetAnimationPhase("HideScreen", 0.0);  // show cover → black screen
```

**Pattern B — Material swap via `hiddenSelections`**

Swap the screen face's `.rvmat` at runtime. Works for solid-color LEDs but
**fails silently for textured screens** when the replacement rvmat uses
procedural `#(argb,…)color(...)` stages — the engine renders black.

**Choosing:** if the "on" look needs a real texture (logo, gradient, UI
bitmap) → use Pattern A. If it's a single emissive color dot → use
`hiddenSelections` with Normal/Basic shader rvmats (see
`skills/_shared/vehicles/emissive-leds-and-dynamic-lights.md`, Pattern A there).

**Pitfall — don't combine them:** if you register the screen selection
in `hiddenSelections[]` AND drive it with a translation animation, the
engine does both (swap material + translate), which usually breaks one
of the two effects. Keep the animated selection OUT of `hiddenSelections`.

---
