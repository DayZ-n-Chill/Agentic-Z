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

## Player and infected use `.anm` graphs instead

Survivors and infected do not use `.rtm` or `model.cfg` animations. They run Workbench animation graphs over `.anm` clips:

| Part | Path |
|---|---|
| Player graph and instances | `P:\DZ\anims\workspaces\player\player_main\` (`player_main.agr`, `master.agr`, `actions.agr`, `player_main.asi`, `player_main_1h.asi`, `player_main_2h.asi` and the other `.asi` files) |
| Event and sync tables | `P:\DZ\anims\workspaces\player\player_eventtable.ae`, `player_synctable.asy` |
| Clips | `P:\DZ\anims\anm\player\`, `P:\DZ\anims\anm\infected\` |
| Skeleton bone lists | `P:\DZ\anims\cfg\skeletons.anim.xml` (survivor `hermit_newbindpose.xob` at :2, infected `z_hermit.xob` at :430, and the animals) |

Items in hands pick an existing instance and an IK pose in script: `pType.AddItemInHandsProfileIK("Inventory_Base", "dz/anims/workspaces/player/player_main/player_main_1h.asi", toolsOneHanded, "dz/anims/anm/player/ik/gear/apple.anm")` (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:373`). Mods add their items through `ModItemRegisterCallbacks` (`:305`, with `RegisterOneHanded` at :309 and `RegisterTwoHanded` at :311, called from :1552 and :1555).

## Scope

- In scope: `model.cfg` animations, `.rtm` clips referenced from config, naming an existing player command for an action (`script-hooks.md`), and naming an existing `.asi` and IK pose for an item in hands.
- Out of scope: editing the player or infected graph, new `.anm` clips or new player commands. Those need a replacement animation graph built in Workbench; tell the art lead it is a separate project for the user to decide on.
