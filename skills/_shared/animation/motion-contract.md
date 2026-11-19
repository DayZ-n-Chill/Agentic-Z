# Motion contract and checks

What the motion report and contract look like, every check type the validator knows, what a result means, and where tolerances may come from. The workflow that uses them is in `realistic-motion.md`; the commands are in `skills/dayz-animation-pipeline/SKILL.md`.

Sampling and judging are separate. `sample_blender_motion.py` reads the scene into a neutral report; `validate_motion_contract.py` judges that report against the checks. So the unit tests run without Blender, and no scene script can quietly define its own success.

## The report

```json
{
  "schema_version": 1,
  "metadata": {
    "fps": 30.0,
    "frame_start": 0,
    "frame_end": 290,
    "action_bindings": [{"object": "Rig", "action": "clip", "frame_start": 0.0, "frame_end": 290.0}]
  },
  "frames": {
    "52": {
      "points": {"contact": [0.1, 0.2, 0.3]},
      "segments": {"finger2": {"a": [0, 0, 0], "b": [0, 0.03, 0], "radius_m": 0.006}},
      "transforms": {"hand": {"p": [0, 0, 0], "q": [0, 0, 0, 1]}}
    }
  }
}
```

Units are metres, degrees and seconds. Quaternions in JSON are always `[x, y, z, w]`.

## What the sampler reads

| Field | Meaning |
|---|---|
| `sample_frames` | Single frames for isolated poses, rising and unique. |
| `sample_ranges` | Inclusive `{start, end, step}` ranges; use `step: 1` for contact, lock and collision windows. |
| `action_bindings` | Optional `{object, action}` pairs, assigned for the run and restored after. |
| `landmarks` | Named points: `bone_head`, `bone_tail`, `bone_point` (with `factor` 0 to 1), `object_origin`, `mesh_vertex_centroid` (with evaluated mesh vertex indices), `average` (of named `sources`); any of them may add `offset_world`. |
| `transforms` | Named transforms: `pose_bone_world`, `pose_bone_local` (`matrix_basis`, for joint limits against the rest and parent chain), `object_world`. |
| `segments` | Named capsule centre lines, each with a `radius_m` of 0 or more. |
| `checks` | Skipped by the sampler and read by the validator, so one file holds the whole contract. |

A missing object, bone, vertex, frame, Action or radius, a value that is not finite, or a frame outside the scene timeline is invalid input and exits with `2`; it never drops a channel quietly.

Bone names in `transforms` and `landmarks` must match the exported skeleton letter for letter. Per the 1.30 changelog (not checked on `P:\`) the engine finds bones by a hash of the name, so the name is the only key; the skeletons added in 1.30 carry an `index` only on `EntityPosition` (`P:\DZ\anims\cfg\skeletons.anim.xml:988`).

## Check types

| Check | Measures | Notes |
|---|---|---|
| `timeline` | Exact frame rate, scene start and end, inclusive frame count | With `require_action_range: true` every bound Action must have the same range. Take the values from the DayZ route. |
| `point_distance_band` | `surface_gap = distance(point_a, point_b) - radius_a_m - radius_b_m` against `min_m` and `max_m` | Negative is sinking in; above the maximum is a miss. |
| `segment_clearance` | Smallest capsule surface distance | Use explicit `segment_pairs` for anatomy so segments of one chain are never compared by accident; `segments_a` against `segments_b` suits separate object groups. |
| `ordered_projection` | Point groups projected on a fixed `axis` or a per frame `axis_from_points` | Use several groups along a chain: roots, middle joints, tips. Tips alone are not enough. |
| `relative_transform_lock` | The target in actor space every frame against the first contact frame | Needs two frames or more. Declare translation and rotation drift limits and a consecutive `frame_range`; split windows around a slip or release. |
| `joint_angle_range` | Quaternion angle from a reference | A single swing angle cannot tell twist from bending; a coarse guard only. |
| `joint_swing_twist_range` | Twist about a local `twist_axis` and the swing left over | Signed twist limits and a maximum swing. Feed it `pose_bone_local`. |
| `continuity_limit` | Point speed, acceleration and jerk | Only limits backed by the action or a reference. Leave impact or snap windows out, or give them their own contract. |
| `rotation_continuity_limit` | Angular speed, acceleration and jerk as shortest path rotation vectors | Local transforms for body stutter, world or object transforms for mechanical stutter. |
| `endpoint_match` | Named points and transforms at two frames | Matching poses alone do not prove a seamless loop. |
| `seam_derivative_match` | Velocity coming into the loop end against velocity leaving the loop start | Point linear velocity, or transform linear and angular velocity. Pair it with `endpoint_match`. |

## What a result says

Each check returns `pass`, `required`, `worst_frame`, `measured`, `limit` and a message. `overall_pass` is true only when every required check passes; optional checks stay visible but cannot hide a required failure. The result also repeats `contract_mode` and gives `eligible_for_offline_pass`, which is true only when a production contract passes every required check.

## Where tolerances come from

In this order:

1. an approved reference pose or motion;
2. measured geometry and known surface thickness;
3. a checked spread of vanilla clips;
4. a decision the user made, written into the contract.

Never take a tolerance only from the candidate being judged. Run a corrected sample through the same check to show it can pass, so the check is not circular.

`contract_mode` is required and is exactly `diagnostic` or `production`. A contract that can give `OFFLINE_PASS` uses `production`, and then every check carries:

```json
"provenance": {
  "source_kind": "approved_reference | measured_geometry | verified_vanilla | explicit_user_decision",
  "source": "path, asset, capture or recorded decision",
  "verified_date": "YYYY-MM-DD",
  "method": "how the numeric bound was derived"
}
```

A contract with any `segment_clearance` check also carries `segment_radius_provenance` with the same fields. In production, contact, collision, lock, order, joint range and continuity checks use a consecutive `frame_range` with `step: 1`; scattered `frames` count only as diagnostic evidence. A diagnostic contract may leave provenance out, but it never supports a production pass, even when `overall_pass` is true.
