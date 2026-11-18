# Creature animation: config wiring and the bones the engine drives

How an animal or infected class is tied to its animation graph and AI template, where each vanilla creature's graph files are, and the two bones the engine moves and aims. Open this when AI script or a creature config has to line up with an animation.

The rest of the creature animation subject lives in the animation pack, owned by dayz-animation-specialist (front index `skills/_shared/animation/README.md`):

| Topic | File |
|---|---|
| The commands a creature graph declares (`CMD_Attack`, `CMD_AttackSuccess`, the infected `CMD_HIT_LIGHT` set), the variables (`speed`, `SlopeAngleX` and the rest), terrain alignment nodes, the 1.30 graph format | `skills/_shared/animation/anim-graphs.md` |
| Building a custom creature from a Blender rig: export, `model.cfg`, the first graph, the order to build it in, AI wiring for an ambient animal | `skills/_shared/animation/creature-rig-to-game.md` |

The script calls that raise the commands (`StartCommand_Attack` and the rest) are in `creatures.md`.

## From config class to graph

A creature's config names its graph in `class enfanimsys`:

| Key | Wolf (`P:\DZ\animals\canis_lupus\config.cpp:266` to `:272`) | Infected (`P:\DZ\characters\zombies\config.cpp:71` to `:78`) |
|---|---|---|
| `meshObject` | `dz\animals\canis_lupus\Data\canis_lupus_skeleton.xob` | `dz\characters\zombies\z_hermit_m.xob` |
| `graphname` | `dz\animals\animations\!graph_files\Wolf\Wolf_Graph.agr` | `dz\anims\workspaces\infected\infected_main\infected.agr` |
| `defaultinstance` | `dz\animals\animations\!graph_files\Wolf\Wolf_AnimInstance.asi` | `dz\anims\workspaces\infected\infected_main\infected_main.asi` |
| `startnode` | `AlignToTerrain_Rot` | `MasterControl` |
| `skeletonName` | `canis_lupus_skeleton.xob` | `hermit_newbindpose.xob` |

The AI side is a separate key on the same class: `aiAgentTemplate`, `Predators_Wolf` for the wolf (`P:\DZ\animals\canis_lupus\config.cpp:37`) and `AmbientLife_Gallus_Gallus_Domesticus` for the hen (`P:\DZ\animals\gallus_gallus_domesticus\config.cpp:27`). Templates are in `behaviour-config.md`.

## Graph files per creature

Each graph is a master `.agr` (variables and commands), one or more `.agf` sub-graphs (states and blends), an `.ast` template (which animation names exist) and `.asi` instances (name to clip), all text:

| Creature | Folder |
|---|---|
| Wolf | `P:\DZ\animals\animations\!graph_files\wolf\` (`wolf_graph.agr`, `wolf_maingraph.agf`, `wolf.ast`, `wolf_animinstance.asi`) |
| Deer, boar, cow, sheep, goat | `P:\DZ\animals\animations\!graph_files\herbivores\`, one graph with one instance per species |
| Hen, hare, fox | `P:\DZ\animals\animations\!graph_files\ambientlife\` |
| Bear | `P:\DZ\animals_bliss\animations\!graph_files\bear\` |
| Infected | `P:\DZ\anims\workspaces\infected\infected_main\` |

## Two bones the engine uses

| Bone | Vanilla | Role |
|---|---|---|
| `EntityPosition` | `movement = "true"`, near the top of every skeleton block (`P:\DZ\anims\cfg\skeletons.anim.xml:5`; the wolf's at `:899`) | The bone the entity is moved with. Clips predict on it: `Bone "EntityPosition"` in the wolf's attack source (`P:\DZ\animals\animations\!graph_files\wolf\wolf_maingraph.agf:53`). |
| `LookAt` | `P:\DZ\anims\cfg\skeletons.anim.xml:17` in the block the infected bind (`hermit_newbindpose.xob`), `:444` in `z_hermit.xob` | The look target. |

Bone names for all vanilla skeletons are listed in `P:\DZ\anims\cfg\skeletons.anim.xml`, one `<skeleton name="....xob">` block each. The addon that ships it has nothing in its `config.cpp` but its `CfgPatches` class `DZ_Anims_Cfg` (`P:\DZ\anims\cfg\config.cpp:3`), so the engine finds the XML by its path, not by a config key.
