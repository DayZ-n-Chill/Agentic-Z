# Materials, drivers and shape keys in bpy

How a script animates shader values, links one property to another with a driver, and keys shape keys in Blender, and where each one's Action really lives. F-curves and easing are in `blender-bpy-fcurves.md`; cameras and constraints in `blender-bpy-objects-camera.md`.

This is Blender behaviour, run against Blender 5.1 or taken from the 4.3 and 5.1 API references, so nothing here cites `P:\`.

## Material animation lives on the node tree

A `Material` is an ID with its own `animation_data`, but its shader graph, `material.node_tree`, is a separate ID with its own. After keying a Principled BSDF socket, `material.animation_data` is `None` and the Action, named `"<MaterialName>Action"`, sits on `material.node_tree.animation_data`. Look there when finding or baking material animation. Shape keys work the same way (below).

Key a socket by calling `keyframe_insert` on the socket itself, not the node and not `node.inputs`:

```python
principled = material.node_tree.nodes["Principled BSDF"]
principled.inputs["Base Color"].default_value = (1.0, 0.0, 0.0, 1.0)
principled.inputs["Base Color"].keyframe_insert("default_value", frame=1)
principled.inputs["Emission Strength"].default_value = 2.0
principled.inputs["Emission Strength"].keyframe_insert("default_value", frame=1)
```

Keying `node.inputs` raises `TypeError: bpy_struct.keyframe_insert() property "inputs" not animatable`. `NodeSocketFloat.default_value` and its colour and vector siblings are plain writable properties, so keying them needs nothing special.

Emission pulses, alpha fades and mix factors all follow the same recipe: set `default_value`, key it, repeat. For a steady pulse, key one or two values and add a Noise or Cycles modifier to the curve (`blender-bpy-fcurve-modifiers.md`), reached with `material.node_tree.animation_data.action.fcurve_ensure_for_datablock(...)`.

## Principled BSDF socket names

Socket names are node data at run time, not static properties, so read them with `[s.name for s in node.inputs]` before keying; Blender has renamed them between versions. In 5.1, in order: Base Color, Metallic, Roughness, IOR, Alpha, Normal, Weight, Diffuse Roughness, Subsurface Weight, Subsurface Radius, Subsurface Scale, Subsurface IOR, Subsurface Anisotropy, Specular IOR Level, Specular Tint, Anisotropic, Anisotropic Rotation, Tangent, Transmission Weight, Coat Weight, Coat Roughness, Coat IOR, Coat Tint, Coat Normal, Sheen Weight, Sheen Roughness, Sheen Tint, Emission Color, Emission Strength, Thin Film Thickness, Thin Film IOR.

Clearcoat is now Coat Weight and its siblings, and Transmission is Transmission Weight, so the several Weight inputs do not clash. Emission is split into Emission Color and Emission Strength.

## The Mix node

`ShaderNodeMix`, the single Mix node since 3.4, has `data_type`, `blend_type` (`MIX`, `ADD`, `MULTIPLY` and the rest), `factor_mode` (`UNIFORM`, `NON_UNIFORM`), `clamp_factor` and `clamp_result`. Its static enum lists `ROTATION` for `data_type`, but in a shader tree `mix.data_type = 'ROTATION'` raises `TypeError: enum "ROTATION" not found in ('FLOAT', 'VECTOR', 'RGBA')`; rotation mixing exists only in Geometry Nodes.

The node carries the sockets of every data type at once and enables those of the current one:

| Index | Name | Identifier |
|---|---|---|
| 0, 1 | Factor | `Factor_Float`, `Factor_Vector` |
| 2, 3 | A, B | `A_Float`, `B_Float` |
| 4, 5 | A, B | `A_Vector`, `B_Vector` |
| 6, 7 | A, B | `A_Color`, `B_Color` |
| 8, 9 | A, B | `A_Rotation`, `B_Rotation` |

`mix.inputs["A"]` finds the enabled socket for the current `data_type` (after `data_type = 'RGBA'` it is `A_Color`), not the first match, but only if you set `data_type` before looking it up. The reference does not say so. The older `ShaderNodeMixRGB` still exists with `blend_type`, `use_alpha` and `use_clamp`; its factor socket is `"Fac"`.

## Drivers

`driver_add(path, index=-1)` and `driver_remove(path, index=-1)` sit on `bpy_struct` like `keyframe_insert`. Drivers live in `id.animation_data.drivers`, apart from any Action or slot, and each driver curve's `.driver` holds the `Driver`.

`Driver` has `type` (`AVERAGE` default, `SUM`, `SCRIPTED`, `MIN`, `MAX`), `expression` (for `SCRIPTED`), `use_self` (adds `self` for the driven data; "dependencies for properties accessed via self may not be fully tracked"), `variables`, `is_valid` and `is_simple_expression`.

```python
var = driver.variables.new()        # no arguments; set name and type after
var.name = "dist"                   # ASCII, no dots or spaces; used as is in the expression
var.type = 'TRANSFORMS'             # SINGLE_PROP, TRANSFORMS, ROTATION_DIFF, LOC_DIFF, CONTEXT_PROP
target = var.targets[0]             # one target, two for the _DIFF types
target.id = car_object
target.data_path = "..."            # SINGLE_PROP only
target.transform_type = 'LOC_X'     # LOC_X to Z, ROT_X to W, SCALE_X to Z, SCALE_AVG
target.transform_space = 'WORLD_SPACE'   # also TRANSFORM_SPACE, LOCAL_SPACE
target.rotation_mode = 'AUTO'       # also the Euler orders, QUATERNION, SWING_TWIST_X to Z
target.use_fallback_value = True    # with fallback_value, used when data_path cannot resolve
```

`driver.variables.remove(var)` removes one. The swing and twist rotation modes split a joint's turn into swing and twist, the usual way to drive corrective shape keys or helper bones.

Keep expressions to the simple set when the file must travel. Simple expressions use ASCII names, number literals, `frame`, `pi`, `True`, `False`, the arithmetic and comparison operators, `and`, `or`, `not`, the conditional expression, and `min max radians degrees abs fabs floor ceil trunc round int sin cos tan asin acos atan atan2 exp log sqrt pow fmod lerp clamp smoothstep`. The manual says "Simple expressions are evaluated even when Python script execution is disabled". Anything else runs as real Python, which Blender's Auto Run Python Scripts setting blocks in untrusted files: a driver that works in the MCP session can stop on a render farm or another install. Prefer the simple set, or `AVERAGE`, `SUM`, `MIN` and `MAX` with no expression.

Use a driver when a value must stay consistent with another live value; use keys for timed, authored values. A wheel that turns with distance travelled:

```python
fcurve = wheel.driver_add("rotation_euler", 1)
drv = fcurve.driver
drv.type = 'SCRIPTED'
var = drv.variables.new(); var.name = "dist"; var.type = 'TRANSFORMS'
t = var.targets[0]; t.id = car; t.transform_type = 'LOC_X'; t.transform_space = 'WORLD_SPACE'
drv.expression = "dist / 1.0"     # distance over the wheel radius in metres
```

With the car keyed from x = 0 at frame 1 to x = 2π at frame 50, the wheel's `rotation_euler.y` at frame 50 is exactly 6.2832. Retime the car and the wheel stays right; a keyed wheel would drift.

## Shape keys

The shape key block (`mesh.shape_keys`, also on curves and lattices) is its own ID: `mesh.animation_data` is `None` and the Action, `"<MeshName>Action"`, sits on `mesh.shape_keys.animation_data`.

```python
mesh_obj.shape_key_add(name="Basis")
sk = mesh_obj.shape_key_add(name="Smile")
sk.value = 0.0
sk.keyframe_insert(data_path="value", frame=1)
sk.value = 1.0
sk.keyframe_insert(data_path="value", frame=20)
```

`ShapeKey` has `value` (0 to 1 by default, `slider_min` and `slider_max` each settable from −10 to 10 for overshoot), `mute`, `vertex_group` (where the key applies), `relative_key` (what it is measured from, by default the Basis) and `interpolation` (`KEY_LINEAR`, `KEY_CARDINAL`, `KEY_CATMULL_ROM`, `KEY_BSPLINE`). That interpolation only matters in absolute mode; in the normal relative mode (`Key.use_relative = True`, the default) each key blends by its `value`. Absolute mode runs through the keys with `Key.eval_time`, like `Curve.eval_time`.
