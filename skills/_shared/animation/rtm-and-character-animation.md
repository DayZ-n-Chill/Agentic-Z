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

Not checked on `P:\`, which holds no `.rtm` files; from the source knowledge pack's reading of community pages. The format is reverse engineered: the Bohemia community wiki page for it carries a notice that it describes internal, undocumented structures. An unbinarized file is an optional `RTM_MDAT` block of frame properties followed by `RTM_0101`: a motion vector, the frame and bone counts, bone names of a fixed 32 bytes, and one 4 by 3 matrix per bone and frame. A binarized form also exists. The user writes `.rtm` from Blender with the Arma 3 Object Builder addon or converts FBX with `FBXToRTMGui.exe` from DayZ Tools; the source and the converter must use the same frame rate, or the clip's speed drifts. Never use `.rtm` for a player weapon animation. Tools and traps: `skills/dayz-animation-pipeline/references/skeletal-rtm.md`.

## Player and infected use `.anm` graphs instead

Survivors and infected do not use `.rtm` or `model.cfg` animations. They run Workbench animation graphs over `.anm` clips:

| Part | Path |
|---|---|
| Player graph and instances | `P:\DZ\anims\workspaces\player\player_main\` (`player_main.agr`, its sub-graphs `master.agf`, `actions.agf` and six more, `player_main.asi`, `player_main_1h.asi`, `player_main_2h.asi` and the other `.asi` files). In 1.29 the sub-graphs were `master.agr`, `actions.agr` and so on; 1.30 lists only the `.agf` files (`GraphFilesResourceNames`, `P:\DZ\anims\workspaces\player\player_main\player_main.agr:1587`), and any `.agr` sub-graph still in that folder is left over from an older unpack. |
| Event and sync tables | `P:\DZ\anims\workspaces\player\player_eventtable.ae`, `player_synctable.asy` |
| Clips | `P:\DZ\anims\anm\player\`, `P:\DZ\anims\anm\infected\` |
| Skeleton bone lists | `P:\DZ\anims\cfg\skeletons.anim.xml` (infected `hermit_newbindpose.xob` at :2, survivor `player_testing.xob` at :110, the `z_hermit.xob` list at :430, which no vanilla `skeletonName` under `P:\DZ\characters\` names, and the animals). Which list a class binds is its `skeletonName`: `hermit_newbindpose.xob` on `ZombieBase` (`P:\DZ\characters\zombies\config.cpp:76`), `player_testing.xob` on `SurvivorBase` (`P:\DZ\characters\data\config.cpp:158`) |

Items in hands pick an existing instance and an IK pose in script: `pType.AddItemInHandsProfileIK("Inventory_Base", "dz/anims/workspaces/player/player_main/player_main_1h.asi", toolsOneHanded, "dz/anims/anm/player/ik/gear/apple.anm")` (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:373`). Mods add their items through `ModItemRegisterCallbacks` (`:305`, with `RegisterOneHanded` at :309 and `RegisterTwoHanded` at :311, called from :1552 and :1555).

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
| The full workflows, measured results and tools (SEAnim, RTM, viewer, rider poses, the 1.30 graph port) | `skills/dayz-animation-pipeline/SKILL.md` |
| A custom creature's graph and skeleton | `_shared/ai/creature-animation.md` |
