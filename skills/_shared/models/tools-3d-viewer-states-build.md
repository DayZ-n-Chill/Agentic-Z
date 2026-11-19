# Viewer states: the build plan

How the viewer tool in `scripts/tools/dayz-3d-viewer` would play a model's animations and swap its materials: the group tree in Three.js, the movement and swap code, the two config readers it needs, the data the extractor would add, and the order to build it in. None of this is built yet. Where the data comes from and the maths of each movement are in `tools-3d-viewer-states.md`.

This is a tool plan, not a set of game facts. The vanilla facts it rests on are cited in `tools-3d-viewer-states.md`, for example the index into `hiddenSelections[]` that `SetObjectMaterial` takes (`P:\scripts\3_game\entities\entityai.c:2884`).

## A tree of groups instead of one mesh

Build a tree of `THREE.Group` objects rather than one flat mesh, so that moving a group moves everything in it:

| Group | Holds |
|---|---|
| `modelRoot` | Everything |
| `static_group` | The faces in no moving selection, one mesh per material (`housing.rvmat`, `base_plate.rvmat`) |
| `anim_switch` | The `switch` selection: the `switch_body` mesh and the `light_led` mesh, whose material swaps |
| `anim_lid` | The `lid` selection |

Because selections overlap, a face can be in a moving group and a swap group at once. Put each swappable mesh inside the moving group it belongs to: the LED mesh is a child of the button group, so it moves with the button and still changes material on its own.

To build the tree:

1. Collect the moving selections from the `Animations` of `model.cfg`.
2. Collect the swap selections from `hiddenSelections[]` in `config.cpp`.
3. For each face of the visual LOD, put it in the group of its moving selection; with several, the one deepest in the bone tree; with none, the static group.
4. Inside each group, split the faces into meshes by material, so each can be swapped.
5. Faces of a swap selection inside a moving one (the LED in the button) become a sub mesh of the moving group.

## Movement in Three.js

A translation, where `anim_group` is the group of the selection:

```javascript
const t = clamp((phase - minValue) / (maxValue - minValue), 0, 1);
const disp = lerp(offset0, offset1, t) * axisLength;
anim_group.position.copy(originalPos).addScaledVector(axisDir, disp);   // originalPos stored once
```

A rotation about the axis point, not about the world origin:

```javascript
const t = clamp((phase - minValue) / (maxValue - minValue), 0, 1);
const q = new THREE.Quaternion().setFromAxisAngle(axisDir, lerp(angle0, angle1, t));
anim_group.rotation.set(0, 0, 0);
anim_group.position.copy(originalPos);
anim_group.applyQuaternion(q);
anim_group.position.sub(axisOrigin).applyQuaternion(q).add(axisOrigin);
```

## Material swaps

Build every material state once, then assign on a change:

```javascript
const ledMaterials = {
    // colours must be THREE.Color objects: a plain [r, g, b] array is ignored without an error
    off:   new THREE.MeshStandardMaterial({ color: new THREE.Color(0.4, 0.4, 0.4) }),
    green: new THREE.MeshStandardMaterial({ color: new THREE.Color(0, 0.8, 0), emissive: new THREE.Color(0, 1, 0) }),
    red:   new THREE.MeshStandardMaterial({ color: new THREE.Color(0.8, 0, 0), emissive: new THREE.Color(1, 0, 0) }),
};

ledMesh.material = ledMaterials[newState];
pointLight.intensity = newState === 'off' ? 0 : 0.5;          // optional glow at the LED
if (newState !== 'off') pointLight.color.set(newState === 'green' ? 0x00ff00 : 0xff0000);
```

## The page

Below the 3D view and its counts (vertices, triangles, materials), two panels: Animations, with one slider per source (`switch_state`, `open_lid`) showing its phase, and States, with buttons per swap selection (LED: Off, Green, Red; Skin: Default, Alt 1).

## Two config readers

`config_parser.py` reads one `CfgVehicles` class from `config.cpp`:

```json
{
  "class": "MyMod_PushButton",
  "model": "\\MyMod\\data\\switch_v1\\switch_v1.p3d",
  "hiddenSelections": ["camo", "switch", "light_led"],
  "hiddenSelectionsTextures": ["switch_co.paa", "switch_co.paa", ""],
  "hiddenSelectionsMaterials": ["switch.rvmat", "switch.rvmat", "led_off.rvmat"],
  "animationSources": {"switch_state": {"source": "user", "initPhase": 0, "animPeriod": 0.3}}
}
```

`modelcfg_parser.py` reads one model's skeleton, sections and animations from `model.cfg`:

```json
{
  "model": "switch_v1",
  "skeleton": {"bones": [{"name": "unit", "parent": ""}, {"name": "switch", "parent": ""}, {"name": "light_led", "parent": ""}]},
  "sections": ["switch", "light_led", "camo"],
  "animations": [
    {"name": "SwitchToggle", "type": "translation", "source": "switch_state", "selection": "switch",
     "axis": "switch_axis", "minValue": 0.0, "maxValue": 1.0, "offset0": 0.0, "offset1": 0.5}
  ]
}
```

Both can use regular expressions over the config text rather than a full C parser, since Bohemia config is simpler; they must handle nested classes, arrays, quoted strings and comments.

## What `extract_geometry_for_viewer()` would add

Beside `positions`, `normals`, `uvs` and `groups`, which it returns today:

| Key | Holds | From |
|---|---|---|
| `selections` | The vertex indices of each selection (`"switch": [0, 1, 2, 5, 6]`) | The `.p3d` |
| `axes` | Per axis, `origin`, `direction` and `length` (`switch_axis`: (0, 0, 0.023), (0, 0, 1), 0.018) | The Memory LOD |
| `animations` | Type, source, selection, axis, phase range, offsets or angles | `model.cfg` |
| `material_states` | Per swap selection, the colour and emissive values of each state (`default`, `green`, `red`) | `config.cpp` and the other `.rvmat` files |

## Build order

1. The two config readers.
2. Per selection vertex indices and axes from the extractor, and the group tree.
3. Material states: for each hidden selection collect the other `.rvmat` files, found by name (`led_off` leads to `led_green` and `led_red` in the same folder), read each into colour values, and convert and embed the `.paa` of each state as base64 when it has one.
4. The page: a slider per source, buttons per swap selection, movement through group transforms, swaps through prebuilt materials, and optionally a point light at each LED.
5. Web mode: write the animation and state data as a JSON file beside the `.glb` and apply the same logic, or export an animated glTF with morph targets or a skeleton.
