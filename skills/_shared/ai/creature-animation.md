# Creature animation: graph, skeleton and the names AI drives

How an animal or infected class is tied to its animation graph, which commands and variables the graph declares, and the two bones the engine moves and aims. Open this when a custom creature needs clips or a graph, or when AI script has to line up with an animation. Building a creature from a Blender rig is covered step by step in `skills/dayz-animation-pipeline/references/creature-animation.md`; the graph file format is in `skills/dayz-animation-pipeline/references/anim-graph.md`.

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

## Graph files

Each graph is a master `.agr` (variables and commands), one or more `.agf` sub-graphs (states and blends), an `.ast` template (which animation names exist) and `.asi` instances (name to clip), all text:

| Creature | Folder |
|---|---|
| Wolf | `P:\DZ\animals\animations\!graph_files\wolf\` (`wolf_graph.agr`, `wolf_maingraph.agf`, `wolf.ast`, `wolf_animinstance.asi`) |
| Deer, boar, cow, sheep, goat | `P:\DZ\animals\animations\!graph_files\herbivores\`, one graph with one instance per species |
| Hen, hare, fox | `P:\DZ\animals\animations\!graph_files\ambientlife\` |
| Bear | `P:\DZ\animals_bliss\animations\!graph_files\bear\` |
| Infected | `P:\DZ\anims\workspaces\infected\infected_main\` |

## Commands the graph declares

These are the names graph conditions test. The script calls that raise them (`StartCommand_Attack` and the rest) are in `creatures.md`.

| Creature | Commands | Where |
|---|---|---|
| Animals | `CMD_Attack`, `CMD_AttackSuccess`, `CMD_Death`, `CMD_JumpType`, `CMD_LookAt`, `CMD_AnimCallBack`, `CMD_Hit`, `CMD_LookAtXChange` | `P:\DZ\animals\animations\!graph_files\wolf\wolf_graph.agr:63` to `:84` |
| Infected | `CMD_HIT_LIGHT`, `CMD_HIT_HEAVY`, `CMD_DEATH`, `CMD_ATTACK`, `CMD_TURN`, `CMD_VAULT`, `CMD_CRAWL`, `CMD_NODEATH` | `P:\DZ\anims\workspaces\infected\infected_main\infected.agr:46` to `:67` |

`CMD_AttackSuccess` is the attack connecting. There is no `CMD_Success`, and spellings with spaces or in lower case do not exist.

## Variables

Every animal graph declares the same set (`P:\DZ\animals\animations\!graph_files\wolf\wolf_graph.agr:6` to `:56`):

| Variable | Range | Use |
|---|---|---|
| `speed` | 0 to 5 | Blends walk, trot and run. |
| `turn` | −180 to 180 | Turning. |
| `behaviorAction`, `alertLevel`, `behaviorSlotID` | integers | What the AI is doing. |
| `lookXAngle`, `lookYAngle` | degrees | Where the head looks. |
| `SlopeAngleX`, `SlopeAngleZ` | −90 to 90 | Ground slope, filled by the engine. |
| `InjuryLevel`, `AnimalType` | integers | Limping, and the species within a shared graph. |

There is no `swimming` variable on any animal.

## Terrain alignment

The body tilts with the ground through a procedural transform fed by the slope variable in radians: `Expression "SlopeAngleX  * 0.01745329251994329576923690768489"` on the wolf's `AlignToTerrain_Rot` node, which is also its start node (`P:\DZ\animals\animations\!graph_files\wolf\wolf_maingraph.agf:5` to `:8`). The herbivore graph has one such node per build, `TerrainRot_BoarAndPig`, `TerrainRot_CowAndBull`, `TerrainRot_Deers` and `TerrainRot_SheepAndGoat`, with the slope clamped to ±40 degrees (`P:\DZ\animals\animations\!graph_files\herbivores\herbivores_maingraph.agf:2407` to `:2410`, `:2449`, `:2505`, `:2547`). A new creature copies the node of the vanilla animal closest in build.

## Two bones the engine uses

| Bone | Vanilla | Role |
|---|---|---|
| `EntityPosition` | `movement = "true"`, near the top of every skeleton block (`P:\DZ\anims\cfg\skeletons.anim.xml:5`; the wolf's at `:899`) | The bone the entity is moved with. Clips predict on it: `Bone "EntityPosition"` in the wolf's attack source (`P:\DZ\animals\animations\!graph_files\wolf\wolf_maingraph.agf:53`). |
| `LookAt` | `P:\DZ\anims\cfg\skeletons.anim.xml:17` in the block the infected bind (`hermit_newbindpose.xob`), `:444` in `z_hermit.xob` | The look target. |

Bone names for all vanilla skeletons are listed in `P:\DZ\anims\cfg\skeletons.anim.xml`, one `<skeleton name="....xob">` block each. The addon that ships it has nothing in its `config.cpp` but its `CfgPatches` class `DZ_Anims_Cfg` (`P:\DZ\anims\cfg\config.cpp:3`), so the engine finds the XML by its path, not by a config key.

## For a custom creature

- Start from the vanilla creature closest in build and behaviour: its skeleton, graph, template, instance and AI template. Change as little as possible.
- Get one idle state with one clip playing in game before adding states.
- A mod that ships its own graph for a new creature class collides with nothing. A mod that replaces a vanilla creature's graph collides with any other mod replacing the same one.
- 1.30 rewrote every vanilla graph in a new text format. A graph written for 1.29 has to be ported; whether 1.30 loads the old format is not tested.
