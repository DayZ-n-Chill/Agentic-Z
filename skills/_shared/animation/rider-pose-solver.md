# Rider pose solver

How to get a driver's or passenger's seated pose by solving it from a few fixed points on the vehicle model instead of keying the body bone by bone, and how the solved pose becomes clips. What the vanilla graph does with a rider is in `rider-poses.md`; what was measured with solved clips in game is in `rider-pose-measured.md`.

## When this route fits

- The vehicle's shape breaks the shared vanilla pose: hands off the wheel or bars, feet off the floor, the torso clipping. Typical for a quad or motorbike with handlebars, unusual grip or footpeg positions, or an unusual seat height.
- Nobody is available to key four clips by hand.
- The anchors can be placed precisely as memory points on the model. This is the precondition.

It does not fit expressive action clips such as combat or a reload while driving (keyframe work, `anm-clips.md`), or a vanilla pose that already looks acceptable, where the rest pose round trip below costs more than a small offset is worth. Shipping the clips by replacing the graph runs into the graph replacement limit (`tooling-and-walls.md`); the child instance route in `rider-poses.md` replaces no graph file.

## The anchors

Memory points in the vehicle's Memory LOD. Any names work as long as the solver input uses the same ones.

| Memory point | Drives | Note |
|---|---|---|
| `crewdriver` | Pelvis, where the rider sits | Reuse the seat's own point. |
| `pos_grip_L`, `pos_grip_R` | Hand targets | On a wheel at the rim; on handlebars at the grips. |
| `pos_footpeg_L`, `pos_footpeg_R` | Foot targets | In a car the pedal area of the floor; on a bike the pegs. |

For a passenger use the same set under another prefix, such as `crewcodriver` and `pos_co_grip_L`. Add the points with the `.p3d` inspector of the model tools or a py3d script (`_shared/models/py3d-generation.md`), then run `/dayz-p3d-audit`.

The engine never reads these points; they feed the offline solver only. In the vanilla graph the hands go where the steering clip leaves them (`rider-poses.md`), so a different grip or footpeg position needs new clips, not a model or config change.

Every anchor coordinate must be in the frame of the `.p3d` it is baked into. When a project keeps two frames for one model, such as an authoring frame facing +Z and a shipped frame facing -Z, convert first (there, negate Z). The side test of the get in action (`get-in-sides.md`) is safe because it asks the model for local coordinates, but the anchors are not: after placing them, open the `.p3d` in a viewer aligned to the shipped frame and check that `crewdriver` sits where the pelvis should.

## What is solved

The solver writes 21 joints (full bone list in `player-skeleton.md`):

- spine chain, 7: `Pelvis`, `Spine`, `Spine1`, `Spine2`, `Spine3`, `Neck`, `Head`;
- arms, 4 a side: `LeftShoulder`, `LeftArm`, `LeftForeArm`, `LeftHand` and the right ones;
- legs, 3 a side: `LeftUpLeg`, `LeftLeg`, `LeftFoot` and the right ones.

It leaves the hand IK helpers (`LeftHandIK`, `RightHandIK`, `LeftHandIKTarget`) alone; the engine drives those when it plays the clip, and keying them too over constrains the pose.

No FABRIK or CCD is needed. Each arm and leg is an analytic two bone solve, and the spine is a straight line with one `lean` number:

| Part | Solve |
|---|---|
| Arm, per side | From the shoulder (end of the spine chain) to the grip, with upper arm 0.30 m and forearm 0.27 m (fixed defaults, which `--rest-pose` does not replace) and an elbow hint forward and slightly down so the elbow does not flip. Gives elbow and hand positions. |
| Leg, per side | Hip to knee to ankle, 0.42 m and 0.41 m, knee hint forward. |
| Spine | `Pelvis` at the seat anchor tilted forward by `lean`; `Spine` to `Spine3` spread evenly on the line from `Pelvis` to the base of the neck; `Neck` and `Head` on the same line with an optional small look ahead. |

`lean` is the torso's only freedom: 0 upright (a cruiser or quad), 0.2 a slight lean (a typical car driver), 0.5 a strong one. Above about 0.6 the spine clips, so cap it. With `steerMax` not zero the spine also twists by 0.2 times the steering angle between `Pelvis` and `Spine3`, which keeps the elbows natural; turn it off for cars, where the body stays neutral.

The hand lands exactly on the grip by construction of the solver. That is not evidence of contact in game (`rider-pose-measured.md`, "Measure the grip hole first").

## What ik_pose_to_seanim.py writes

The script reads an `anchors.json` (seat, two grips, two feet, `lean`, `steerMax`, `twistFactor`, per variant overrides) and writes one SEAnim per variant: idle, steer left, steer right, and a passenger idle when asked.

Its output is not game ready. Each file holds solved joint positions with identity rotations: the step that turns positions into bone rotations against a rest pose is not written, with or without `--rest-pose`. The limb lengths are always the fixed defaults (`DEFAULT_LIMB_LENGTHS`), so positions are approximate for any body. The notes it writes are free text, which DayZATool has refused as malformed events. Use the files as a position reference for posing, or write the rotation step first; the script's header says the same.

## Rest pose round trip

A SEAnim extracted from a vanilla clip stores most bone rotations against the skeleton's rest pose, not as world rotations. A solver that gives world positions has to turn them into local rotations against a rest pose, and a wrong rest pose gives subtly wrong results in game (turned shoulders, a twisted spine) even when a viewer shows it perfect.

1. Pick a vanilla driver idle clip close to the target, such as `p_civiliansedan_driver_idle.anm` under `P:\DZ\anims\anm\player\vehicles\civiliansedan\`.
2. The user runs `DayZATool --extract-anim <file>.anm`, which writes a SEAnim next to it.
3. Use its frame 0 as the bind pose for the conversion (`--rest-pose extracted.seanim`).

Plan this from the start; there is no way round it. The rule holds for DayZATool extracts of vanilla clips. Clips compiled by the Blender plugin are absolute, and comparing raw values across the two gives large false differences (`weapon-anim-compile.md`, "Two conventions for what a key means").

## From anchors to clips

1. Place the anchors in the Memory LOD.
2. Check the pose by eye, worth it for the first vehicle: a small three.js page with sliders for `lean`, `steerMax` and each anchor, running the same solver and exporting the pose as JSON, takes about a day. When the project already has a baked viewer of the model, reuse its embedded data block instead of parsing the `.p3d` again, as `selections-for-actions.md` does.
3. Solve the variants with `ik_pose_to_seanim.py` and finish the rotations: idle, steer left, steer right, passenger idle.
4. The user runs `DayZATool --generate-anim file.seanim 100` for each `.anm`.
5. Bind the clips, through a child instance file for one vehicle class (`rider-poses.md`, "Changing the pose for one vehicle class") or by replacing the graph. The vehicle subgraph is `P:\DZ\anims\workspaces\player\player_main\vehicles.agf`; the motorbike state machine `MotorBikeSTM` runs from `:1582`, and the vanilla rider sets are the template columns `Jawa_05` and `Jawa_Bitrak` (`P:\DZ\anims\workspaces\player\player_main\player_main.ast:1119` and `:1120`) with lines in the base instance (`Vehicle.Jawa_05.AccelerationSpine` at `P:\DZ\anims\workspaces\player\player_main\player_main.asi:5088`). Editing an `.agf` by hand and having the engine accept it is untried; the Workbench animation editor is the known way. Any edited graph sits at vanilla paths, so shipping it makes the mod a graph replacement.
6. Test in game: no bone name errors in the RPT; look at the pose in first person from the seat and from outside on both sides.

Config driven parts around the rider, such as handlebars that turn or accessories that hide when attached, are not character animation and never meet the graph limit (`handlebar-and-steering.md`, `attach-state-parts.md`).

## One angle for the part and the hands

When the steering part turns through `model.cfg` (`handlebar-and-steering.md`) and the hands follow its grips, both ranges must agree, or the hands leave the grips at full lock.

- On a mod's own graph, the `model.cfg` throw and the solver's `steerMax` describe the same angle. `steerMax` is in radians. For `angle0` and `angle1` follow `handlebar-and-steering.md`, "One angle for the part and for the rider's hands". Never pair `angle1 = "rad 0.39"` with `steerMax = 0.39`: `"rad 0.39"` is 0.39 degrees, a throw too small to see.
- On the vanilla 1.30 motorbike graph the clip's frames cover 45 degrees of wheel angle each way whatever the throw, so the solver spreads frames over 45 degrees and clamps at the lock, and the model's `TurnFront` animation must follow the physics angle one to one for bars and hands to agree (`rider-pose-measured.md`).

Write the shared constant down in the project, so an edit to one side updates the other.

The anchor names, joint list, solver and viewer were worked out on one quad model. A second vehicle with different proportions would confirm whether the pattern holds generally.
