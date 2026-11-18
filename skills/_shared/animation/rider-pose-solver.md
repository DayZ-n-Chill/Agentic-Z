# Vehicle rider pose from model anchors

Two things are in this file. The first is a way to get the seated pose of a driver or passenger by solving it from a few fixed points on the vehicle model instead of keying the body bone by bone. The second is how such a pose reaches the game for one vehicle class without replacing the player graph, with everything that was measured on the way.

Vanilla facts cite `P:\` (DayZ 1.30). Measured results come from two setups: a quad (May 2026, where the solver was worked out) and a motorbike on DayZDiag 1.30.164014 (September and October 2026). Measured results are evidence for that setup, not rules.

## When this route fits

- The vehicle's shape breaks the vanilla shared pose: hands floating off the wheel or bars, feet off the floor, the torso clipping. Typical for a quad or motorbike with handlebars, unusual grip or footpeg positions, or an unusual seat height.
- There is no animator to key four clips by hand.
- The anchors can be placed precisely as memory points in the model. That is the precondition.

## When it does not

- Expressive action clips (combat, a reload while driving). That is keyframe work: `anm-clips.md`.
- The vanilla pose already looks acceptable. The calibration against a rest pose (below) costs more than a small offset is worth.
- The plan ships the clips by replacing the graph and the user has not accepted the graph wall (`tooling-and-walls.md`). The child `.asi` route below replaces no graph file.

## The anchors

Memory points in the vehicle's Memory LOD. Any names work as long as the solver's input uses the same points.

| Memory point | Drives | Notes |
|---|---|---|
| `crewdriver` | Pelvis (where the rider sits) | Reuse the point the seat already has. |
| `pos_grip_L`, `pos_grip_R` | Left and right hand targets | On a steering wheel, at the rim; on handlebars, at the grips. |
| `pos_footpeg_L`, `pos_footpeg_R` | Left and right foot targets | In a car, the pedal area of the floor; on a bike, the pegs. |

For a passenger place the same set under another prefix, for example `crewcodriver` and `pos_co_grip_L`.

Add the points with the dayz-p3d-inspector or dayz-model-pipeline skills, then run `/dayz-p3d-audit` on the model.

**The engine never reads these points.** They feed the offline solver only. In the vanilla graph the hands go where the steering pose clip leaves them (see "Where the hands come from"), so a different grip or footpeg position needs new clips, not a model or config change.

## The 21 joints that are solved

The full bone list is in `player-skeleton.md`. The solver writes these:

- Spine chain (7): `Pelvis`, `Spine`, `Spine1`, `Spine2`, `Spine3`, `Neck`, `Head`.
- Arms (4 a side): `LeftShoulder`, `LeftArm`, `LeftForeArm`, `LeftHand` and the `Right` ones.
- Legs (3 a side): `LeftUpLeg`, `LeftLeg`, `LeftFoot` and the `Right` ones.

It does not write the hand IK helpers (`LeftHandIK`, `RightHandIK`, `LeftHandIKTarget`). The engine drives those when it plays the clip; keying them as well would over-constrain the pose.

## The solver: two bone IK per limb and a straight spine

FABRIK and CCD are not needed. An analytic two bone solve for each arm and leg, plus a straight spine with one `lean` number, gave a hand to grip error of 0.0000 in the quad's cases. That zero is true by construction of the solver; it is not evidence of contact in game (see "Measure the grip hole first").

```
ARM (per side)
  in:  shoulder position (from the spine chain), grip target (from the anchor),
       upper arm and forearm lengths (fixed defaults in the script, 0.30 and 0.27 m;
       --rest-pose does not replace them),
       pole hint: forward and slightly down, which stops the elbow flipping
  out: elbow and hand positions; turning them into rotations of Shoulder, Arm,
       ForeArm and Hand is the step the script does not do yet (next section)

LEG (per side)
  the same shape, hip to knee to ankle (fixed defaults 0.42 and 0.41 m), pole hint forward

SPINE
  Pelvis at the seat anchor, tilted forward by lean
  Spine to Spine3 spread evenly along the straight line from Pelvis to the base of the Neck
  Neck and Head along the same line, with an optional small look ahead
```

`lean` is the only freedom the torso has: 0 is an upright rider (as on a cruiser or a quad), 0.2 a slight forward lean (a typical car driver), 0.5 a strong one. Above about 0.6 the spine clips, so cap it.

Optional: a slight torso twist with the steering. When `steerMax` is not zero the spine twists by 0.2 times the steering angle between `Pelvis` and `Spine3`, which keeps the elbows at a natural angle. Turn it off for cars, where the body stays neutral.

## What `ik_pose_to_seanim.py` does today

The script solves the joints from an `anchors.json` (seat, two grips, two feet, `lean`, `steerMax`, `twistFactor`, and per variant overrides) and writes one SEAnim per variant: idle, steer left, steer right, and a passenger idle when asked.

Its output is not ready for the game. Each file holds the solved joint positions and identity rotations: the step that turns positions into bone rotations against a rest pose is not written, with or without `--rest-pose`. The limb lengths are the script's fixed defaults (`DEFAULT_LIMB_LENGTHS`) on every run, so the positions are approximate for any body. Use the files as a position reference for posing, or finish that step first. The notes it writes are free text, which DayZATool has refused as malformed events. The script's own header says the same; read it before promising output from it.

## Rest pose calibration

A SEAnim extracted from a vanilla clip stores most bone rotations relative to the skeleton's rest pose, not as world rotations. A solver that produces world positions has to turn them into local rotations against a rest pose. If the rest pose it assumes differs from the real one, the pose in game is subtly wrong (rotated shoulders, a twisted spine) even when a viewer shows it perfect.

The procedure that works:

1. Pick a vanilla driver idle clip close to the target, for example `p_civiliansedan_driver_idle.anm` under `P:\DZ\anims\anm\player\vehicles\civiliansedan\`.
2. The user runs `DayZATool --extract-anim <file>.anm`, which writes a SEAnim next to it.
3. Use its frame 0 as the bind pose for the conversion (`--rest-pose extracted.seanim`).

Plan for this round trip from the first day. There is no shortcut around it.

One caution about the "relative to rest" rule: it holds for DayZATool extracts of vanilla clips. Clips compiled by the Blender plugin are absolute, and comparing raw values across the two conventions gives large false differences (`weapon-anim-blender.md`, "Two conventions for what a key means").

## Which frame the anchors are in

If a project has two coordinate frames for one model (an authoring or viewer frame and the frame of the shipped `.p3d`), every anchor coordinate must be in the frame of the `.p3d` it is baked into. The quad had a front along +Z authoring frame and a front along −Z production frame; baking anchors from one into the other meant negating Z first.

The side test of the get in action (`get-in-sides.md`) is safe from this, because it asks the model for local coordinates in whatever frame the `.p3d` uses. The anchors themselves are not: after placing them, open the `.p3d` in a viewer aligned to the production frame and check that `crewdriver` sits where the pelvis should.

## Pipeline, start to finish

1. **Place the anchors** in the Memory LOD.
2. **Check the pose by eye** (optional, worth it for the first vehicle). The quad used a small three.js page with sliders for `lean`, `steerMax` and each anchor, running the same solver and exporting the pose as JSON. Building one takes about a day. If the project already has a baked viewer of the model, reuse its embedded data block instead of parsing the `.p3d` again (`selections-for-actions.md` uses the same trick).
3. **Solve the variants** with `ik_pose_to_seanim.py` and finish the rotations (see above): idle, steer left, steer right, passenger idle.
4. **The user runs DayZATool** (`--generate-anim file.seanim 100`) to get each `.anm`.
5. **Bind the clips.** Either replace the graph, which hits the wall, or use a child `.asi` for the one vehicle class (next section). The vehicle sub-graph is `P:\DZ\anims\workspaces\player\player_main\vehicles.agf`; the motorbike machine `MotorBikeSTM` runs from `:1582`, and the vanilla rider sets are the template columns `Jawa_05` and `Jawa_Bitrak` (`P:\DZ\anims\workspaces\player\player_main\player_main.ast:1119`, `:1120`) with lines in the base instance (`Vehicle.Jawa_05.AccelerationSpine` at `P:\DZ\anims\workspaces\player\player_main\player_main.asi:5088`). Editing an `.agf` by hand and having the engine accept it has not been tried; the Workbench animation editor remains the known way to edit a graph. However it is edited, the graph sits at vanilla paths, so shipping it makes the mod a graph replacement.
6. **Test in game.** No bone name errors in the RPT. Look at the pose from inside the vehicle in first person and from outside on both sides.

Config driven parts around the rider (the handlebar turning, accessories that hide when attached) are not character animation and never meet the wall: `handlebar-and-steering.md`, `items-in-hands.md`.

## A pose for one vehicle class without a graph change

The vanilla mechanism (the 1.30 instance switch that surrender uses) is in `rider-poses.md`, "Changing the pose for one vehicle class". What follows is what was measured with it.

### Measured while the vehicle stands

Motorbike test, DayZDiag 1.30.164014, dedicated server and the owning client, one player, 2026-09-28. A child `.asi` of `player_main.asi` that overrides only the column the vehicle rides on, registered through `RegisterCustom` and swapped in while the player rode one vehicle class, changed that player's pose on that class only. `vehicles.agf`, `player_main.ast` and `player_main.agr` were untouched. Like the weapon route, it does not meet the graph wall; it can still collide with any other mod that swaps the player's instance.

What was run:

- **The file.** A text `.asi` in the vanilla format, its header copied from `player_main_surrender.asi` (lines 1 to 6), holding only the two `Vehicle.Jawa_Bitrak.DriverSteering...` lines, pointed at the CivilianSedan's steering poses. The vanilla lines it borrows are `Vehicle.CivilianSedan.DriverSteeringExtreme` and `DriverSteeringMain` (`P:\DZ\anims\workspaces\player\player_main\player_main.asi:4785` to `:4790`); the lines it replaces are `Vehicle.Jawa_Bitrak.DriverSteeringExtreme` and `DriverSteeringMain` (`P:\DZ\anims\workspaces\player\player_main\player_main.asi:5175` to `:5180`). Vanilla stores its `.asi` files the same way in its PBO: plain text, LF line ends, no `.meta`. Packed as a plain file of the mod's PBO (AddonBuilder with `-packonly` keeps it as it is), the child loaded by path with no Workbench step and no workspace entry.
- **Registration.** `AddItemInHandsProfileIK("<no such item>", "<pboprefix>/anims/<name>.asi", cfg, "")` with an empty handed `DayzPlayerItemBehaviorCfg`, inside `RegisterCustom`, which runs before the preload `DebugPreloadAnimationInstances` (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:1653`). It returned 913 on both machines. `DayZPlayerTypeRegisterItems` runs twice per machine (called at `P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:12` and `:21`), and the client runs it once more for the main menu character.
- **The swap**, run on the dedicated server and on the owning client. On: in `OnCommandVehicleStart` of `PlayerBase` (`P:\scripts\4_world\entities\manbase\playerbase.c:4342`) when the vehicle command's transport `IsKindOf` the class, with surrender's two calls. Off: as soon as `IsGettingOut()` is true, and again in `OnCommandVehicleFinish` (`:4375`) before `super`, with `EnableAutoAnimInstUpdateOnHandsChange(true)`, the base `player_main.asi` by path and `OnItemInHandsChanged(true)`, so that vanilla's own `RefreshHandAnimationState` (`P:\scripts\4_world\entities\manbase\playerbase.c:4384`) runs after it.
- **Measured.** Both machines received `OnCommandVehicleStart` and `OnCommandVehicleFinish` and ran `CommandHandler`. Their switch on calls were logged 24 ms apart, their switch off calls at the start of the get out 5 ms apart. Stopped, on the owning client's samples, the rider's left hand, pelvis and head sat 0.84, 1.01 and 1.01 m from the same player on the same model without the swap (the server logged too few control samples for its own comparison). The same player stayed unswapped on the other classes of the row. On exit both machines logged the switch back with the automatic switch on again. The instance itself was not read back (the debug instance fields came out empty), but the same player's stopped pose on three other variants ridden afterwards matched the control's on both machines (pelvis 1.098 m high in the bike's model space, against 0.093 m with the swap), so the override was gone.
- **Not tested here:** other riders, restoring a held item, remote observers, late join.

Traps found on the way:

- After the get out clip the command read as seated, not getting out, until `OnCommandVehicleFinish`. A check every frame switched the rider back on for 32 ms on the server and 28 ms on the client. Latch the swap off from the get out until the command is gone.
- `GetBoneIndexByName` on `Human` (`P:\scripts\3_game\human.c:1417`) returns ids that look like hashes, and several are negative: `RightHand` gave −1405358722, and `RightFoot`, `RightToeBase`, `LeftForeArm` and `RightHandRing1` were negative too. An early probe treated every negative id as missing. Only −1 means missing; tested that way every one of them resolved (the right hand mirrored the left).
- The server's hands are not the client's. For the same stopped pose the dedicated server put the left hand 0.35 m (vanilla pose) and 0.55 m (swapped pose) from where the client did, while pelvis and head agreed within a few millimetres. Measure hand placement on the client.

Still open, each needing its own in-game check:

- Remote observers and late join. `OnCommandVehicleStart` and `OnCommandVehicleFinish` are engine callbacks (`P:\scripts\3_game\human.c:1691`, `:1692`) and nothing yet shows that they reach remote proxies.
- A weapon in the hands.
- An item change or the delayed hand refresh while riding: `OnItemInHandsChanged(bool pInstant = false, bool pChangeAnimationInstance = true)` (`P:\scripts\3_game\humanitems.c:112`) and the `RefreshHandAnimationState(396)` call (`P:\scripts\4_world\entities\manbase\playerbase.c:6197` to `:6200`).
- The restart after unconsciousness, ejection and death.
- Other graph mods. Survivor Animations' graph at the time was in the 1.29 format with no `Jawa_` lines, so on a server that loads it this route has nothing to override. Whether another graph replacement still uses the `Vehicle.Jawa_Bitrak.` bindings has to be checked per mod.

### Own clips on the rider, measured end to end

The same child `.asi` route with generated clips, riding included. Measured on a custom sport bike model, DayZDiag 1.30.164014, dedicated server and the owning client, one player, four runs on 2026-09-28. The test mod kept a config table (one class per pose, each with a vehicle class and an `.asi`), registered every `.asi` in `RegisterCustom`, switched in `OnCommandVehicleStart`, `CommandHandler` and a client poll every frame, and latched off from the start of the get out.

**A generated clip plays.** A clip made with `DayZATool --generate-anim <file>.seanim 100` plays. DayZATool writes `ANIMSET5`, and 1.30 ships player clips in three versions (counted in the player clip PBO: 10 `ANIMSET4`, 2,398 `ANIMSET5`, 5,007 `ANIMSET6`). A vanilla steering pose with `Spine1` bent 20 degrees put the stopped rider's head 0.4 mm (median of 129 client samples) from the clip's forward kinematics and 19 cm from the vanilla one. Later first person probe runs saw the stopped head move by several centimetres between runs and looks (see the last bullet of this section). The `Resource` line of the `.asi` loaded both as a bare path and with an invented `{GUID}` in front; vanilla ships no `.meta` for its clips.

**The steering clip always spans 45 degrees each way.** The motorbike steering poses are read at `Time "clamp((VehicleSteering + 0.785) * 0.63694..., 0.0, 1.0)"` (`P:\DZ\anims\workspaces\player\player_main\vehicles.agf:50` for `DriverSteeringMain`, and the same `Time` expression at `P:\DZ\anims\workspaces\player\player_main\vehicles.agf:1466` for `DriverSteeringExtreme`). `VehicleSteering` is the wheel angle in radians, so the clip always covers −45 to +45 degrees of wheel angle, whatever the bike's lock. Author frame `i` of `N` at `(2i/(N−1) − 1) × 45` degrees, clamped to the lock. The node reads normalized time, so the frame count is free: 37 frames put a 20 degree lock exactly on a frame.

Measured on the sport bike (20 degree lock): with the frames spread over the lock instead, both hands sat 44 mm from where that clip puts them at full lock (the engine was reading it at 0.45 of its length). With the frames at 45 degrees, the frame that best explains the measured hands (mean fit residual 0.3 mm per hand) sat at the bars' measured angle: 20.0 degrees stopped at full lock; riding at 11 to 27 km/h with the bars between −16.0 and +17.4 degrees, within 1.2 degrees of the bars (0.1 or less in 29 of 39 samples; fit residual median 0.3 mm, at most 0.6 mm per hand). That shows the hands following the clip frame of the bars' angle. The clip puts the hands on the grips by construction of the solver; no hand to grip distance was measured in game. Two solvers missed this scale until the hands were measured 44 mm off.

**Write the transitions as absolute, whole body poses.** The vanilla `IdleToDrive` and `DriveToIdle` clips hold differences: per bone, pose = base × add in local space, with the translations added. `IdleToDrive` goes over the riding pose (its frame 0 rebuilds the stopped pose within 0.19 degrees and it ends at identity) and `DriveToIdle` over the stopped one. The engine plays them as states of `Idle_MotorBikeSTM` (`IdleToDrive` and `DriveToIdle`, `P:\DZ\anims\workspaces\player\player_main\vehicles.agf:1204` to `:1220`) under the blend node `Steerinng` (spelled so in the file, `:2720`). A DayZATool clip holding the same kind of data played as an absolute pose: during the transitions the pelvis, spine, neck and head collapsed onto one point near the rider's root (8 of 209 client and 9 of 218 server samples; the hands and some leg bones stayed apart). Exported as absolute poses that key every bone of the steering pose, arms included, there was no collapse (210 client and 218 server samples), and while stopping the measured hands sat 0.1 to 1.5 mm from the clips' hands at the measured bar angle (3 client samples). Keep the vanilla notes (`Sound` at frame 10 of `IdleToDrive`, `Step` at 7 and 15 of `DriveToIdle`); a SEAnim with notes needs presence flag 64.

**Reading the bars' real angle, for a probe.** `GetBonePivotsForAnimationSource(GetViewGeometryLevel(), "turnfront", pivots)` (`P:\scripts\3_game\entities\object.c:233`, with `GetViewGeometryLevel` at `:220`), then `GetBoneRotationMS(pivots[0], q)` (`P:\scripts\3_game\entities\object.c:242`). The angle is `2 * atan2(|q.xyz|, |q.w|)`, signed along the steering axis. Vanilla does the same lookup for its sounds (`GetBonePivotsForAnimationSource` at `P:\scripts\4_world\entities\vehicles\motorbikescript.c:287` to `:292`). `WheelGetDirection(0)` on `Motorbike` (`P:\scripts\3_game\vehicles\motorbike.c:247`) gives the front wheel's direction.

**A scripted get out, for a test that must see the pose switch back.** `ActionGetOutTransport` needs no target: its `HasTarget` returns false (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetouttransport.c:220`), its `ActionCondition` reads only the vehicle command (`:70`), and it ends in `GetOutVehicle` (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetouttransport.c:183`). So starting the action with any target gets the rider off. Measured: the switch off fired at the start of the get out on both machines; the get out took 2 s.

**How close it sat.** Stopped, the medians per bone sat 0.1 to 0.5 mm from the clip's forward kinematics (single samples up to 37 cm during the blend after getting on). Riding, pelvis medians 1.1 to 1.7 cm and head medians 2.1 to 2.6 cm (owning client; the graph's lean and acceleration layers add to the pose). Getting on and off still play the vanilla clips (the leg over the tail) and blend into the new pose in about 0.3 s. One sample while pulling away had both hands 4 cm wider than the grips during the state blend. In later first person probe runs on the same bike (2026-10-16 to 24, DayZDiag 1.30.164.200), with the same clips in every run, the bike stopped and the pelvis within 0.6 mm, the head moved over up to 7.6 cm between runs and looks. The cause is not established.

**Still open:** remote observers and late join (needs a second client), a held item, the restart after unconsciousness, ejection and death, and get in and get out clips of the mod's own.

### Measure the grip hole first

Measured on the skinned body mesh, DayZ 1.30.164014. Vanilla vehicle clip hands close on a thin bar: the centre of the vanilla fist's hole sat about 23 mm from the memory point centre that had been used, and the hole's radius is 9.9 mm on the left hand and 11.5 mm on the right (the vanilla motorbike's bar), against a custom grip of 20.1 mm that cut up to 19 to 20 mm into the hand.

- Before reusing vanilla clip hands on another vehicle, measure the clip's fist hole against the new grip or wheel radius.
- Vehicle memory points such as the `accelerator` and `clutchlever` axes are not fist centres.
- A "hands at 0 mm" reading that the solver satisfies by construction is not evidence of contact. Measure the wrap in degrees and the penetration on the mesh.
- Wrap by rotating each finger and thumb phalanx tangent to the grip. The test reached 330 to 360 degrees covered, with 5 to 6 mm of overlap at every piece, through the whole steering range.

## One angle for the part and for the hands

If the steering part turns by `model.cfg` (`handlebar-and-steering.md`) and the rider's hands follow its grips, the two ranges must agree, or the hands leave the grips at full lock, which shows at once in game.

- On a mod's own graph (the quad): the `model.cfg` throw and the solver's `steerMax` describe the same angle. `steerMax` is in radians. For the unit and form of `angle0` and `angle1`, follow `handlebar-and-steering.md` ("One angle for the part and for the rider's hands"). Do not pair `angle1 = "rad 0.39"` with `steerMax = 0.39`; that file explains why it is wrong: `"rad 0.39"` is 0.39 degrees, a throw too small to see, while `steerMax` stays in the solver's radians.
- On the vanilla 1.30 motorbike graph the contract is a different one: the clip's frames are read over 45 degrees of wheel angle each way whatever the `model.cfg` throw, so the solver maps frames to 45 degrees and clamps at the lock, and the model's `TurnFront` animation must follow the physics angle one to one (the sport bike's does) for the bars and the hands to agree.

Write the shared constant down in the project so a later edit to one side updates the other.

## Reference case

The anchor names, joint list, solver shape and viewer pattern were worked out on one quad model (May 2026). If a second vehicle with different proportions confirms the same pattern, it is worth a case study file of its own.
