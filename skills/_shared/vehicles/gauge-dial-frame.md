# Gauge dial frame and angles

How to fix the screen frame of a dial so its art is neither mirrored nor rotated, how to tell a mirror from a rotation by measurement, and how `angle0` and `angle1` follow from that frame.

The wiring is in `gauge-needles.md` and the art measurements in `gauge-dial-art.md`. Everything here was measured on mod test vehicles (two quads and a coupe) and is not checked on `P:\`.

## Anchor the frame to the model's own right

Mapping polar art onto a dial needs two in-plane axes. A generic "any perpendicular to the normal" gives the dial an arbitrary roll, and correcting that by eye with a half turn is where mirrors start. A half turn is a rotation and cannot undo a reflection: a mapping of `u <- -b`, `v <- -a` swaps the axes and negates one, which is a reflection no angle offset removes.

The cross product alone does not fix it either. One generator built `u = cross(w, axis)` and assumed that was the driver's right; on that model it came out +X, while the model's own markers put `light_left` at x +0.373 and `light_right` at x -0.374, so the driver's right is -X. The check render built its frame with the same expression, reproduced the fault and called it correct.

Anchor the frame instead of compensating:

```python
MODEL_RIGHT = (-1.0, 0.0, 0.0)                 # from light_right - light_left
w = normalize(up - axis * dot(up, axis))       # vehicle up, projected into the dial plane
u = normalize(cross(w, axis))
if dot(u, MODEL_RIGHT) < 0:
    u = -u
# stop with an error if the light markers disagree with MODEL_RIGHT, or are missing
u_uv = uc + k * dot(radial, u)
v_uv = vc - k * dot(radial, w)                 # the V sign is measured, see below
```

Take "right" from markers the model writes about itself: `light_right` minus `light_left`, or `wheel_1_1` and `wheel_2_1`, or a `*_dir` point. "Up" is vehicle +Y projected onto the dial plane. The needle axis points at the driver. The target mapping is right to +U and up to -V, because V=0 is the top edge of the image. No `atan2` is needed; recomposing an angle into coordinates is where axes got swapped.

A new part, such as a fuel panel, has no anchor of its own. Project its frame from the anchored dial frame (Gram-Schmidt over the part's normal); never rebuild it with a cross product or flip it by components. One build did `Up = cross(Np, Rp)` and, when Up came out inverted, flipped Up and recomputed `Rp`, which dragged `Rp` to the driver's left (`<Rp, right>` of -1.0000); a guard caught it. Check `<u_part, anchored right>` is positive, because the sign of `angle0` depends on it.

The cheap first check on any cluster: read `light_left` and `light_right` from the Memory LOD and the sign of `<u, light_right - light_left>`. Negative means the frame is mirrored. On a second quad that check read `light_left` x +0.3011, `light_right` x -0.3131 and `<u, right>` of -0.6142: mirrored, the same root on a different model and toolchain. Its earlier fix, negating `angle0` and `angle1`, had pinned the needles to the right numbers on a face written backwards.

## The V direction is measured per pipeline

Whether V needs `1 - v` is not an engine fact; it depends on what your tools already did to the model's UVs. One assembler writes `(u, 1.0 - v)` for every UV it takes from an OBJ, so dials on that model must match it. On a quad whose UVs came from an Arma 2 MLOD without that step, V as-is gave readable art, and `1 - v` sampled another region of the atlas rather than a mirror.

The rule is a procedure, not a sign: write dial V in the same direction as the model's other UVs, and find that direction with art whose orientation admits no debate, such as text or a readable decal, rendered with the real `.p3d` UVs. Body textures already seen in game without complaint are that anchor. A wrong guess gives either a mirror or an offset, both plausible, and without the anchor you cannot tell which.

## Mirror or rotation: fit the mapping

Fit by least squares the 2 by 2 matrix that takes (right, up) to (U, V), using the real UVs of the built `.p3d`. With a residual near 1e-6 the fit describes the whole mapping:

| Result | Meaning |
|---|---|
| right to +U, up to -V | Correct |
| right to +U, up to +V | Vertical mirror; text reads as in a mirror |
| right to -U, up to -V | Horizontal mirror |
| right to -U, up to +V | 180 degree rotation |

Image V grows down and screen up grows up, so an unmirrored dial has a negative determinant; positive means mirrored. That holds only when +U is the model's real right. In a frame built by cross product without the marker check, the same mirrored build read negative on all three dials; re-measured in the anchored frame it read +513, +491 and +1290, and the corrected build -513, -491 and -1290.

Fit one disc at a time. Mixing two dials and a colour swatch gave anisotropy 6.9 and 780 px of residual; a single disc gave anisotropy 1.000000 and 0.0000 px.

This table is what tells a mirror from a rotation, and you need it: the report was "upside down, rotate 180" and the measurement said vertical mirror. Do not apply the correction the symptom describes; map to the absolute target, and the result is right whatever words describe the fault.

## Trust a check only after it reproduces known states

A check that has matched only one state tells reachable from unreachable, not good from bad. The dial check was calibrated against three builds:

| Mapping | Frame | Render | In game |
|---|---|---|---|
| (+U, +V) | built by cross product, mirrored | upside down | "upside down, rotate 180" |
| (+U, -V) | built by cross product, mirrored | mirrored, red on the left | "still mirrored" |
| (+U, -V) | anchored to the lights | 0 at lower left, clockwise, red on the right | accepted |

Mappings are named in the frame of their own `u`, so the two (+U, -V) rows are different mappings, which is why the frame is a column. The same calibration ruled out other causes by measurement: the texture does not arrive flipped (mean difference 0.20 as is against 9.00 mirrored), the driver does not see the back of the disc (88 faces toward +Y against 16), the axis does not point inward (`<driver - p0, axis>` of +0.0210 and +0.0203), and reversed winding after binarizing is the format's convention.

Three rules: anchor the frame to something the model says about itself; never let the check share the expression that defines the frame with the code it checks; calibrate the check against known states before believing a new verdict. Before inferring a sign from a sequence of user reports, check which build each report saw: two reports of one build are one observation.

## Angles follow from the frame

`angle0` turns the needle from the angle it is modelled at, not to an absolute angle: `angle0 = painted_zero - mesh_angle`, both in the same frame. With a positive sweep turning clockwise for the driver (`gauge-needles.md`) and clockwise meaning a falling screen angle:

```text
angle0 = rest - theta(minValue)
angle1 = rest - theta(maxValue)
```

`rest` is the blade's screen angle in the built model (`gauge-needle-part.md`) and `theta(v)` is the screen angle of the printed value. Draw the needle over every printed value in a render of the real UVs to close it.

Un-mirroring a dial moves the painted zero to another physical place, so old angles are wrong even if nobody touched the needle. And because old and new frames differ by a reflection (`theta_new = C - theta_old`), the turning direction flips too. Under a mirror `theta` becomes `-theta`: the speedometer's painted 0 sat at 213 degrees and was seen at 147, so a parked needle pointed at about 120 km/h. Once the mapping was fixed, the same `angle0` landed on 0. One cause gives both "art upside down" and "needles do not start at 0", so do not fix the angles separately; the sweep is kept, only the origin moves.

## Final numbers on one quad

| Dial | `minValue` | `maxValue` | `angle0` | `angle1` | Sweep | Checked at |
|---|---|---|---|---|---|---|
| Speed | 0 | 150 | `"rad 232.5"` | `"rad 535.3"` | 302.8 | 11 values, 0 to 100 |
| RPM | 0 | 1 | `"rad 213.1"` | `"rad 456.4"` | 243.3 | 7 values, 0 to 6 |
| Fuel | 0 | 1 | `"rad -129.1"` | `"rad -47.6"` | 81.5 | E, half, F |

Determinants in the anchored frame: speed -512.5, rpm -491.2, fuel -1290. The speedometer line was fitted over 0 to 100 only.

The dial centre in the texture comes from two methods that agree (the non-black centroid and a least-squares circle on the major ticks, within 12.7 px on speed and 6.4 px on rpm); the radius is the real disc edge. Moving the centre moves the angles, so re-derive them. The painted disc has 32 segments, radius 0.0254, centred on the pivot offset by `lift`. Assign each needle to its disc by x position, not by name: with the driver's right at -X, `aguja_izquierda` ("left needle") at x +0.056 drives speed and `aguja_derecha` at x -0.055 drives rpm.
