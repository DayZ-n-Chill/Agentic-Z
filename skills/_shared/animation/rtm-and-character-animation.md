# RTM files and character animation

Where vanilla DayZ uses `.rtm` animation files, and why player and infected animation is a different system that this specialist does not change.

## Where vanilla uses `.rtm`

`.rtm` files are skeletal animation clips. Vanilla references them in two places. The `.rtm` files themselves are not in the `P:\` unpack, only the references to them.

| Use | Where | Example |
|---|---|---|
| Face poses on survivor heads | `CfgHeads` in `P:\DZ\characters\heads\config.cpp:4639` | `class RTM_Face { type = "rtm"; anim = "dz\characters\heads\anim\neutral.rtm"; };` at :4682 to :4686, with `DeadFace`, `HurtFace` and the rest inheriting it from :4687 |
| Lip sync shapes | Same file, `class Lipsync` | `type = "lipsync"; vizem[] = {...}` lists one `.rtm` per mouth shape (:4667 to :4681) |
| Simple animals | `P:\DZ\animals\animconfig\config.xml` | butterfly `States` play `\dz\animals\data\rtm\Butterfly_Fly.rtm` (:347) and `Butterfly_Open.rtm` (:352); birds play `\dz\animals\birds\data\anim\flying.rtm` (:428) |

For a mod, `.rtm` work means a new face pose or a small animal state in the same shape as these entries: a clip whose bone names match the target skeleton, referenced by path from config. Keep the clip's bone names identical to the skeleton's.

### The format and its tools

Nothing in this section can be checked on `P:\`, which holds no `.rtm` files under `P:\DZ`. `.rtm` is the animation format of the older Real Virtuality engine; in DayZ it is the legacy route, not how characters, infected, animals with graphs or weapons are animated (that is `.anm`, `anm-clips.md`).

### The format is reverse engineered

Bohemia does not document `.rtm`; the structures are internal. Treat every description of the format as reverse engineering, not a contract: it can differ between engine versions.

### Shape of the file

- **Plain (`RTM_0101`).** An optional `RTM_MDAT` header (frame properties as name and value at float phases), then `RTM_0101`: a motion vector of three floats, the frame count, the bone count, bone names of a fixed 32 bytes each, and for every frame one transform per bone as a 4 by 3 float matrix. Byte offsets were not checked against a vanilla file.
- **Binarized.** A separate compact format, versions 3, 4 and 5 (Arma 2 and Arma 3). Its layout is not known here; only its existence is.

### What can write an `.rtm`

- The package in `scripts/tools/dayz-animation-formats/` reads and writes one unbinarized `RTM_0101` block with an optional `RTM_MDAT` before it (`read_rtm`, `write_rtm`), and refuses anything else. Its output was read back by Arma 3 Object Builder 2.5.1 with motion, phases, metadata and transforms preserved. That is a file check, not proof the game accepts the clip.
- Nothing here writes binarized `.rtm`.
- Do not promise that a hand written `.rtm` plays in game until it has been through the user's converter and an in-game test.
- Reading `.rtm` in Python is well trodden: the `rtm_import` Blender addon parses it (import only).

For authoring, prefer Blender or `FBXToRTMGui.exe` over writing matrices by hand.

### The pipeline (the user's tools)

1. Keyframe the animation in Blender against the target skeleton.
2. Export it to `.rtm`, either straight from Blender with the Arma 3 Object Builder addon, or to FBX first and then to `.rtm` with `FBXToRTMGui.exe` from DayZ Tools.
3. Reference the `.rtm` from config.
4. Pack and sign the mod.
5. Test it in game.

- **Arma 3 Object Builder** (a Blender 4.2+ addon) exports `.rtm` from a timeline range. The phase runs from 0.0 to 1.0 across the render range, so a wrong range squashes or clips the animation. The only frame property known is `StepSound`. It carries Arma's name, but the format is the same one.
- **`FBXToRTMGui.exe`** (DayZ Tools): set the bind pose FBX and the `modelbox.xml`, pick the skeleton (`ManSkeleton`), the root bone (`Hips`), and a frame rate equal to the source's. Not tried on the current DayZ Tools.

### Traps

- Bone names must match the target skeleton exactly, the same rule as on the `.anm` route.
- The frame rate must be the same in the source file and in the converter, or the clip's speed drifts.
- Scale between Blender meters and the engine's space: the factor for DayZ was not established.
- MotionBuilder: FBX to RTM is documented as working with MotionBuilder 2009 and broken with 2015. Newer versions were not checked.
- DayZATool is the `.anm` tool. Do not use it for `.rtm` round trips; its extracted rigs are unreliable.

### When to use `.rtm` and when `.anm`

- `.rtm`: a face pose or a simple animal state in the shape vanilla uses, or a legacy clip. A prop that only turns or slides does not need a clip at all; that is a `model.cfg` animation (`model-cfg-animations.md`).
- `.anm`: anything on a character, infected, graph driven animal or weapon. Never use `.rtm` for a player weapon animation; it is the most common wrong turn.

### The tools by name

- Arma 3 Object Builder: the Blender addon that imports and exports `.rtm`; its documentation lists the `.rtm` properties.
- ArmAToolbox: an older Blender `.rtm` export.
- `rtm_import`: a Blender addon that reads `.rtm` (import only).
- FBX to RTM: `FBXToRTMGui.exe` in DayZ Tools, documented on the Bohemia Interactive community wiki.

## Player and infected use `.anm` graphs instead

Survivors and infected do not use `.rtm` or `model.cfg` animations. They run Workbench animation graphs over `.anm` clips:

| Part | Path |
|---|---|
| Player graph and instances | `P:\DZ\anims\workspaces\player\player_main\` (`player_main.agr`, its sub-graphs `master.agf`, `actions.agf` and six more, `player_main.asi`, `player_main_1h.asi`, `player_main_2h.asi` and the other `.asi` files). In 1.29 the sub-graphs were `master.agr`, `actions.agr` and so on; 1.30 lists only the `.agf` files (`GraphFilesResourceNames`, `P:\DZ\anims\workspaces\player\player_main\player_main.agr:1587`), and any `.agr` sub-graph still in that folder is left over from an older unpack. |
| Event and sync tables | `P:\DZ\anims\workspaces\player\player_eventtable.ae`, `player_synctable.asy` |
| Clips | `P:\DZ\anims\anm\player\`, `P:\DZ\anims\anm\infected\` |
| Skeleton bone lists | `P:\DZ\anims\cfg\skeletons.anim.xml` (infected `hermit_newbindpose.xob` at :2, survivor `player_testing.xob` at :110, the `z_hermit.xob` list at :430, which no vanilla `skeletonName` under `P:\DZ\characters\` names, and the animals). Which list a class binds is its `skeletonName`: `hermit_newbindpose.xob` on `ZombieBase` (`P:\DZ\characters\zombies\config.cpp:76`), `player_testing.xob` on `SurvivorBase` (`P:\DZ\characters\data\config.cpp:158`) |

Items in hands pick an existing instance and an IK pose in script; how vanilla and a mod register them is in `items-in-hands.md`.

## Scope

- In scope: `model.cfg` animations, `.rtm` clips referenced from config, naming an existing player command for an action (`script-hooks.md`), and naming an existing `.asi` and IK pose for an item in hands.
- Out of scope: editing the player or infected graph, new `.anm` clips or new player commands. A changed graph or a new command needs a replacement animation graph built in Workbench; tell the art lead it is a separate project for the user to decide on.

## What the graph layer allows without replacing it

New clips do not always need a replaced graph. A clip for one item or weapon can be bound through a child `.asi` that lists only the lines it changes, registered for that item class with `AddItemInHandsProfileIK` (`P:\scripts\3_game\dayzplayer.c:243`); nothing in the graph is touched, so it does not collide with other mods. Authoring the clip is still Workbench and Blender work for the user. When a task heads that way, open:

| Question | File |
|---|---|
| Which graph, template and instance files exist, which `CMD_` commands and variables they declare, what collides | `anim-graphs.md` |
| How an item or weapon gets its instance and IK pose, and how script switches the instance | `items-in-hands.md` |
| What places a driver's or rider's hands and body, and how to change the pose for one vehicle class | `rider-poses.md` |
| The `.anm` route from keyframes to a clip the game loads | `anm-clips.md` |
| The scripts that write and inspect SEAnim and RTM, build the viewers and solve rider poses | `skills/dayz-animation-pipeline/SKILL.md` |
| A custom creature's graph and skeleton | `_shared/ai/creature-animation.md` |
