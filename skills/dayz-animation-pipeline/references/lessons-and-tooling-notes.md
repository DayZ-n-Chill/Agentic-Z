# Rules learned on projects, and tooling notes

Short rules from mod project post-mortems, plus notes on tools and on Linux. They are project experience, not vanilla facts, except where a line cites `P:\`.

## Rules for animated parts and poses

| Rule |
|---|
| **A sub-piece of a proxy cannot be animated in place.** `model.cfg` moves whole selections and whole proxies. To animate one moving part of a proxied attachment, split it into its own proxy or selection. |
| **A mod that derives from another mod's model needs its own `.p3d`, its own `model.cfg` and its own `model=` entry** to add animations. Inheriting the config class alone does not bind a new skeleton or animation. |
| **One angle for a turning part and for the IK that keeps hands on it.** Put the same value in `angle0` and `angle1` and in the solver's `steerMax`, and check both ends. Not on the 1.30 motorbike graph, whose steering poses span ±45 degrees of wheel angle whatever the model turns; there, make the frames at 45 degrees and clamp at the stop (`vehicle-rider-ik-pose.md`). |
| **No scripted snap and no extra `pos_*_L` and `pos_*_R` points for a vehicle boarded from both sides.** Copy the vanilla structure: crew proxies, and seat selections and components that exist in the View Geometry and Fire Geometry. Keep the vanilla action. (`dual-entry-action-pattern.md` keeps the older snap as a fallback.) |
| **The steering source is `steeringwheel`.** `DrivingWheel` is the usual animation class name, not a source; vanilla stores exactly that pair (`P:\DZ\vehicles\wheeled\offroadhatchback\offroadhatchback.p3d`). Copy the standard bone chain of damper, then steering, then wheel, and do not try to feed a second animation from a wheel source. |
| **A steering visual driven from the client through a `user` source snaps back to 0 in multiplayer.** Use the engine source. (`handlebar-and-steering-config.md`.) |
| **Before adjusting a pose offline, list what really determines it in game:** the weapon's origin, the bone remap, the IK pose, the geometry, and the stance and aim space. Build the viewer from that data; do not chain visual guesses. |
| **For joints the game solves with IK at run time, dump the bones' model space positions from the client and rebuild the offline pose from positions.** Do not guess the elbow's swivel or trust raw rotations whose convention is not verified. |

## Notes on tools

**Editing a large file through a synced folder.** In one setup, an editor tool silently cut the new text at about 5 to 8 KB when the target sat in a OneDrive folder or a plugin mount: the file was written, the second half was missing, and no error was raised. The workaround was to write the block to a temporary file, check its end, copy it with a script, and read the destination back. That is a fault of that setup, not of DayZ tools; the lasting habit is to read a large file back after writing it and check that its last line is the one intended.

**Reuse a viewer's baked geometry** instead of parsing a large `.p3d` again, and **draw overlays unlit and pushed 5 mm off the surface**: both in `selection-painter-for-actions.md`.

**A written file is not a verified file.** After any script writes a `.p3d`, reopen it and assert the selections are not empty, the memory points are where they should be and the material count is unchanged (`py3d-1.0.0-quirks.md`, "Check the output before calling it done").

## Layer notes from the quad rider project

A quad rider mod added these to the three layers in `SKILL.md`:

- **Steering rotation is layer 1**: `model.cfg` only, engine source, two axis points (`handlebar-and-steering-config.md`).
- **A scripted get in is script, between layers 1 and 2**: a `modded class ActionGetInTransport` (`dual-entry-action-pattern.md`), now mostly replaced by the native directional hooks of 1.30.
- **A rider pose solved from anchors is layer 2**: two bone IK on the player skeleton from five anchors in the `.p3d` (seat, two grips, two feet), written as SEAnim by `ik_pose_to_seanim.py`. The files hold solved joint positions and identity rotations, with or without `--rest-pose`: the step that turns positions into rotations against a rest pose is not written, so the output is a position reference, not a clip the game can play (`vehicle-rider-ik-pose.md`).
- **Clips made with DayZATool play as absolute poses**, so a transition between two rider poses has to be written out whole, not as a difference (measured in game on a motorbike rider, 2026-09-28; same reference).

## On Linux

Everything in this skill is the Windows workflow. What changes on Linux, as measured under Proton (not checked here; the Proton setup and tool matrix are in `skills/_shared/linux-proton.md`):

- `.rtm` and `.p3d` binarize through `dayzmake build --proton-binarize` with dayzmake 1.0.0 or later.
- Workbench starts under Proton and compiles its bundled scripts. Its animation editor, `.agr` and `.asi` editing, and the `.txa` to `.anm` import were not verified there. Without `P:\dz` extracted it logs missing vanilla config entries.
- Object Builder runs under Proton.
- The tool in `scripts/tools/dayz-animation-formats/` is Python and runs natively.
- PowerShell helper scripts need translating to shell.
