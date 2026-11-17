# The sign of an animation is not judged without its axis

How to prove offline that a wheel, door, steering or dial animation turns the right way: compare the pseudovector of angle and axis against the matching class of a vanilla control.

> Status: field notes. The mod-side values below were measured on mod test vehicles (the SUB_BRZ sedan and the LFQuad3 quad) and are mod behaviour, not vanilla; they were not repeated for this file. A citation written with its full `P:\` path was opened on the vanilla data of this repo (a 1.30 build). "Invariant N", "preflight #N" and "#N" all mean the numbered invariants; `skills/dayz-vehicles/SKILL.md` lists which file holds each number.

Related file in this pack: `gauge-needles.md` (dashboard needles in full: frames, rotation direction, deriving `angle0` and `angle1`).

## Vanilla anchors checked on `P:\`

- The controls measured below are the binarized vanilla models `P:\DZ\vehicles\wheeled\civiliansedan\civiliansedan.p3d` and `P:\DZ\vehicles\wheeled\offroadhatchback\offroadhatchback.p3d`. py3d cannot read ODOL, so the axis and angle values quoted from them were read with an external ODOL parser from the 1.29 models (ODOL version 54) and are not yet checked on `P:\`, which holds version 56.

## An animation's SIGN is never judged without its AXIS: use the pseudovector against the control

Wheels spinning backwards, doors hinging the wrong way and inverted steering are the same bug,
and reviewing `angle1` alone cannot catch any of them, because **the axis sign is a free
reparametrization**: `R(theta, a) == R(-theta, -a)`, so a mod with axis `(-1,0,0)` and
`angle1 = +6.28` moves *identically* to the control's `(1,0,0)` / `-6.28`. Compare the raw
angle against a control and you will flag a correct artifact and miss a real one. The
falsifiable invariant is the pseudovector `angle1 x unit(axis_dir)`, compared against the
homologous class of the vanilla CONTROL.

**Where the evidence lives after Binarize** (so this is an OFFLINE gate, not an in-game guess):
the compiled ODOL carries the whole rig. In the `odol_reader` module of the external ODOL parser
(the one `skills/dayz-vehicles/SKILL.md` says how to point at), `animations.classes[i]` has
`anim_name`, `anim_source`, `anim_type` (0=rotation, 4=translation), `angle0/angle1`,
`offset0/offset1`; `animations.anims2bones[lod][i]` indexes the **global** skeleton (it does NOT
go through `lod.sub_skeletons_to_skeleton`); `animations.axis_data[lod][i]` is
**`(position, direction)`, NOT two points**. Measured: wheel axes come back as exactly
`(1,0,0)` unit vectors and dampers as `(0, 0.3, 0)` where 0.3 is the travel length.
Binarize also **lowercases `anim_source` while preserving `anim_name` case**, so compare
sources case-insensitively.

**The trap that inverts the verdict: picking the wrong homologue in the control.**
`CivilianSedan` carries TWO classes driven by `turnfrontleft` with identical angles and
**opposite** axes: `steering_swivel_1_1` on `(0,-1,0)` and `steering_arm_steering_1_1` on
`(0,+1,0)`. The homologue of your steering bone is the **swivel** (the knuckle the wheel hangs
from, i.e. the parent of `wheel_X_1` in your skeleton chain), never the tie rod. Read the
control's skeleton chain before choosing; a comment in your own `model.cfg` asserting which one
you matched is not evidence.

**Worked parity check** (SUB_BRZ against `civiliansedan.p3d`, ODOL version 54, measured 2026-07-28):

| Leg | Mod | Control homologue | Verdict |
|---|---|---|---|
| wheel roll x4 | `-6.283185 x (1,0,0)` | `wheel_1_1..2_2`: same | identical |
| steering x2 | `+pi/2 x (0,1,0)` | `steering_swivel_X_1`: `-pi/2 x (0,-1,0)` | identical |
| door driver / codriver | `+1.396 x (0,1,0)` / `-1.396 x (0,1,0)` | `DoorsDriver_a` / `DoorsCoDriver_a`: same signs | same convention |

**Dampers have no vanilla homologue if you use the single-bone translation rig.**
`CivilianSedan` models suspension as about 20 ROTATION classes on `susp_arm_*` bones.
Gating your `type="translation"` dampers against the sedan fails by construction: their control
is a model built with the same single-bone translation rig (the Land Rover reference
model named below is one), not the sedan.

**How to gate it**: assert the pseudovector per animation class against the control, on every
LOD that carries an active binding, plus `anim_source` case-insensitive, bone binding, and a
non-degenerate `axis_dir`. Two fixtures, and getting them the right way round is the whole
point:

- **negative (must FAIL)**: invert the axis **or** the angle, one at a time. That is a real
  direction defect.
- **positive (must PASS)**: invert **both** at once. Same rotation, different parametrization;
  a gate that rejects it is over-fitted to one authoring convention and will reject a correct
  mod.

Checking only "the axis is not null" is not a direction check at all: a gate that does only
that accepts a backwards-hinging door. Translation animations (`anim_type=4`, dampers) need the
same treatment with `unit(axis_dir) * (offset1 - offset0)`.

The measurement turns the wheel-direction question from "spend an in-game cycle to discover it"
into "already proven offline, in-game only confirms", which is the difference between one cycle
and two.

## ODOL proxy selection indexes are not bone-selection indexes

After binarization, `Proxy.named_selection_index` resolves to the generated
instance selection `proxy:<same-model>.<NNN>`, not to the role/bone selection.
A measured door proxy used adjacent indexes for the generated instance and
`doors_driver`; rejecting that layout as a role mismatch is a false positive.
`Proxy.bone_index` resolves against the global skeleton directly. Together with
the rules above: compare `anim_source` case-insensitively, and resolve
`animations.anims2bones[lod][class]` against the global skeleton without applying
`sub_skeletons_to_skeleton`.

## Dial needles have a vanilla homologue too: compare the pseudovector, not the sign

Measured 2026-09-02 from `offroadhatchback.p3d` (ODOL version 54): `IndicatorSpeed` binds bone `dial_speed`, `source=speed`,
`angle0=0`, `angle1=+190 deg`, axis position (0.4934, 1.1957, -0.4940) and direction (0, 0.4216, 0.9068): the
dial normal pointing UP and TOWARDS the driver (front is -Z, so +Z is towards the seat). Positive angle with the
axis towards the viewer = clockwise for the viewer, which is how a speedometer reads.

A Land Rover reference model in MLOD form (readable with py3d)
authors the same needle the OTHER way: `mph_axis` = (0.700, 1.492, -0.628) -> (0.700, 1.492, -0.629), i.e. the
direction points to -Z, AWAY from the driver, and `angle1 = -4.5361256` (-260 deg). Both give the same
pseudovector `angle1 x unit(axis_dir)` (towards the driver, positive): same rotation. A gate that compares raw
`angle1` signs between the two would flag one of two working cars.

Rule for a new dial: pick the hatchback `IndicatorSpeed` as the homologue, assert the pseudovector against it,
and calibrate with the two fixtures of this file (flip only the axis or only the angle = must FAIL; flip both =
must PASS). Sources and ranges (`speed` km/h, `rpm` 0..1, `"rad N"` = degrees) are in
`vehicle-config-and-modelcfg.md` section 12, "Dashboard needles".
