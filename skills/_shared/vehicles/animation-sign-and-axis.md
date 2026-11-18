# Animation direction and axis

How to prove offline that a wheel, door, steering or dial animation turns the right way, by comparing angle and axis together against the matching class of a vanilla car.

Dashboard needles in full (frames, deriving `angle0` and `angle1`) are in `gauge-needles.md`. The mod values here were measured on a test car and a test quad; they are mod behaviour, not vanilla.

## The vanilla cars to compare against

The reference models are the binarized `P:\DZ\vehicles\wheeled\civiliansedan\civiliansedan.p3d` and `P:\DZ\vehicles\wheeled\offroadhatchback\offroadhatchback.p3d`. py3d cannot read ODOL, so their axis and angle values were read with an external ODOL parser from the 1.29 models (ODOL version 54). They are not yet checked against the version 56 models on `P:\`.

## Judge the sign with its axis

Wheels that spin backwards, doors that hinge the wrong way and inverted steering are one bug, and checking `angle1` alone cannot catch it. The sign of the axis is free: a rotation of `theta` about `a` equals a rotation of `-theta` about `-a`. A mod with axis `(-1,0,0)` and `angle1 = +6.28` moves exactly like a vanilla class with `(1,0,0)` and `-6.28`. Compare raw angles and you flag a correct model and pass a broken one.

Compare the product `angle1 x unit(axis_dir)` instead, against the matching class of the vanilla car. For a translation (`anim_type=4`, dampers) use `unit(axis_dir) * (offset1 - offset0)`.

## Where the values live after binarize

The compiled ODOL carries the whole rig, so this is an offline check. In the `odol_reader` module of the external ODOL parser (see `/dayz-p3d-audit` for how to point at it):

| Field | Holds |
|---|---|
| `animations.classes[i]` | `anim_name`, `anim_source`, `anim_type` (`0` rotation, `4` translation), `angle0`, `angle1`, `offset0`, `offset1` |
| `animations.anims2bones[lod][i]` | An index into the global skeleton; do not pass it through `lod.sub_skeletons_to_skeleton` |
| `animations.axis_data[lod][i]` | A `(position, direction)` pair, not two points |

Wheel axes come back as exact `(1,0,0)` unit vectors, and dampers as `(0, 0.3, 0)` where `0.3` is the travel length. Binarize lowercases `anim_source` and keeps the case of `anim_name`, so compare sources without case.

## Pick the right class in the vanilla car

Comparing against the wrong class flips the verdict. `CivilianSedan` has two classes driven by `turnfrontleft` with the same angles and opposite axes: `steering_swivel_1_1` on `(0,-1,0)` and `steering_arm_steering_1_1` on `(0,+1,0)`. Your steering bone matches the swivel, the knuckle the wheel hangs from and the parent of `wheel_X_1` in your skeleton, never the tie rod. Read the vanilla skeleton chain before you choose; a comment in your own `model.cfg` saying which one you matched proves nothing.

A test car checked against `civiliansedan.p3d`:

| Part | Mod | Vanilla class | Result |
|---|---|---|---|
| Wheel roll, four wheels | `-6.283185 x (1,0,0)` | `wheel_1_1` to `wheel_2_2`: the same | Identical |
| Steering, two wheels | `+pi/2 x (0,1,0)` | `steering_swivel_X_1`: `-pi/2 x (0,-1,0)` | Identical |
| Driver and co-driver doors | `+1.396 x (0,1,0)` and `-1.396 x (0,1,0)` | `DoorsDriver_a` and `DoorsCoDriver_a`: the same signs | Same convention |

Dampers built as single bone translations have no match in the sedan. `CivilianSedan` builds its suspension from about 20 rotation classes on `susp_arm_*` bones, so checking translation dampers against it fails every time. Compare them against a model built the same way, such as the Land Rover model under "Dial needles" below.

## How to check it

For every animation class, on every LOD with an active binding, check the product against the vanilla class, plus `anim_source` without case, the bone binding, and an `axis_dir` that is not zero length. Prove the check with two test cases, and get them the right way round:

- Must fail: flip the axis or the angle, one at a time. That is a real direction fault.
- Must pass: flip both at once. Same rotation, written differently; a check that rejects it is tied to one way of authoring and rejects a correct mod.

Checking only that the axis is not null is not a direction check; it passes a door that hinges backwards. With this check, wheel direction is proven before the build, and the game only confirms it.

## Proxy selection indexes in ODOL

After binarization, `Proxy.named_selection_index` points at the generated instance selection `proxy:<same-model>.<NNN>`, not at the role or bone selection. On a door proxy the generated instance and `doors_driver` sat at neighbouring indexes; rejecting that as a role mismatch is a false alarm. `Proxy.bone_index` points into the global skeleton directly.

## Dial needles

`IndicatorSpeed` in `offroadhatchback.p3d` (ODOL version 54) binds bone `dial_speed` with `source=speed`, `angle0=0`, `angle1=+190` degrees, axis position `(0.4934, 1.1957, -0.4940)` and direction `(0, 0.4216, 0.9068)`. The dial normal points up and towards the driver: the front is `-Z`, so `+Z` faces the seat. A positive angle with the axis towards the viewer turns clockwise as the viewer sees it, which is how a speedometer reads.

A Land Rover model in MLOD form, readable with py3d, builds the same needle the other way: `mph_axis` runs from `(0.700, 1.492, -0.628)` to `(0.700, 1.492, -0.629)`, pointing to `-Z` away from the driver, with `angle1 = -4.5361256` (-260 degrees). Both give the same product, towards the driver and positive, so both turn the same way. A check that compared raw `angle1` signs would fail one of two working cars.

For a new dial, compare against the hatchback's `IndicatorSpeed` and prove the check with the two test cases above. Sources and ranges (`speed` in km/h, `rpm` from 0 to 1, `"rad N"` meaning degrees) are in `vehicle-modelcfg-animations.md`, section "What the engine feeds the needles".
