# F-curve modifiers in bpy

How a script adds noise, loops, polynomials, smoothing, limits, steps and envelopes to an F-curve in Blender, and which of them changed in 4.4 and 5.1. The F-curve data model is in `blender-bpy-fcurves.md`.

This is Blender behaviour, run against Blender 5.1 or taken from the 4.3 and 5.1 API references, so nothing here cites `P:\`.

## Adding a modifier

`fcurve.modifiers.new(type=...)` returns an `FModifier`; `fcurve.modifiers.remove(modifier)` removes it. The reference's one line description of `new()` says "Add a constraint to this object", a copying slip from `ObjectConstraints.new()`; it returns an `FModifier`.

In 5.1 `type` takes `NULL`, `GENERATOR`, `FNGENERATOR`, `ENVELOPE`, `CYCLES`, `NOISE`, `LIMITS`, `STEPPED` and `SMOOTH`; 4.3 lacks `SMOOTH`.

Every modifier has `active`, `blend_in` and `blend_out` (frames to fade in and out), `frame_start` and `frame_end` (used only with `use_restricted_range=True`), `influence` (0 to 1, used only with `use_influence=True`), `mute`, `name`, `show_expanded`, and the read only `type` and `is_valid`.

Since 4.4, removing a modifier, constraint or shape key also deletes the drivers on that item's own properties, such as a driver on a constraint's `influence`. A cleanup step can remove a driver you added earlier without any message.

## Noise for camera shake

| `FModifierNoise` member | Meaning |
|---|---|
| `blend_type` | `REPLACE` (default), `ADD`, `SUBTRACT`, `MULTIPLY`. |
| `scale` | "Scaling (in time) of the noise": higher is slower and wider. |
| `strength` | Amplitude. |
| `phase` | Random seed. |
| `offset` | Time offset. |
| `depth` | Octaves of fine detail, 0 to 32767. |
| `lacunarity` (4.4) | Default 2.0, "Gap between successive frequencies". Needs `depth` above 0. |
| `roughness` (4.4) | Default 0.5, "Amount of high frequency detail". Needs `depth` above 0. |
| `use_legacy_noise` (4.4) | `False` on new modifiers, `True` on old files: "Has the issue that it can produce values outside of -1/1". |

Blender 4.4 reworked the noise so values stay within −0.5 to 0.5, with defaults close to the old look.

For camera shake, key the base motion (one key at rest for a still camera), add a noise modifier to each rotation curve and, if wanted, each location curve, set `strength` for amount and `scale` for speed (smaller is faster), and give each axis its own `phase` so they do not move together. The key is required: Blender skips a curve with no keys and no generating modifier, and noise does not generate, so noise on an unkeyed curve does nothing. The noise is added around the keyed value.

```python
for axis in range(3):
    cam.keyframe_insert("rotation_euler", index=axis, frame=1)
fcurve = cam.animation_data.action.fcurve_ensure_for_datablock(cam, "rotation_euler", index=0)
noise = fcurve.modifiers.new(type='NOISE')
noise.scale = 6.0       # lower is faster
noise.strength = 0.02   # radians
noise.phase = 0.0       # different per axis
```

## Cycles for loops

`FModifierCycles` has `mode_before` and `mode_after` (`NONE` default, `REPEAT`, `REPEAT_OFFSET`, `MIRROR`) and `cycles_before` and `cycles_after` (0 is endless).

| Mode | Use |
|---|---|
| `REPEAT` | An exact loop; the first and last keys must already share value and tangent. |
| `REPEAT_OFFSET` | Each copy starts where the last ended, for motion that keeps advancing: a walk moving forward, a conveyor, a spin. |
| `MIRROR` | Plays forward then back, for a breathing or bobbing idle with no reset. |

With both ends on `REPEAT` or `REPEAT_OFFSET` and nothing else changed, the curve is trivially cyclic: automatic handles smooth the seam, and `INSERTKEY_CYCLE_AWARE` respects the cycle when inserting.

Cycles must be the first modifier on the curve, and so must Smooth, because both read the original keys. So a curve can have one or the other, never both.

```python
bob = obj.animation_data.action.fcurve_ensure_for_datablock(obj, "location", index=2)
bob.modifiers.new(type='CYCLES').mode_after = 'REPEAT'
```

## Smooth, new in 5.1

`FModifierSmooth`, "Smooth curve using Gaussian smoothing", smooths without changing keys. `sigma` (0.1 to 100) shapes the curve in frames, lower being sharper; `filter_width` (1 to 32) sets how many frames are averaged around each key, higher being smoother and slower. It must be first on the curve and cannot sit with Cycles. On 4.3 `modifiers.new(type='SMOOTH')` fails, so check `bpy.app.version >= (5, 1, 0)` first.

## Generator, limits, stepped and envelope

| Modifier | Members | Does |
|---|---|---|
| `FModifierGenerator` | `mode` (`POLYNOMIAL` default, `POLYNOMIAL_FACTORISED`), `poly_order` (1 to 100), `coefficients` (32 floats from x⁰), `use_additive` | A polynomial curve, replacing or added to the keys. |
| `FModifierLimits` | `min_x`, `max_x`, `min_y`, `max_y` with `use_min_x` and the rest | Clamps the value, or cuts the time range to constant outside it. |
| `FModifierStepped` | `frame_step`, `frame_offset`, `frame_start` and `frame_end` with their `use_` flags | Holds each value for N frames, for stop motion or animating on twos. |
| `FModifierEnvelope` | `reference_value`, `default_min`, `default_max`, `control_points` (each with `frame`, `min`, `max`) | A gain envelope over time. |
