# Animating a custom creature

The path from a rigged animal, infected or predator in Blender to a creature that moves in game: skeleton, export, `model.cfg`, a first graph, and AI wiring. The graph format itself is in `anim-graph.md`; the script side of creatures (commands, handlers, mind states) is in `skills/_shared/ai/creatures.md`.

Two kinds of statement are mixed here. Vanilla facts cite `P:\`. Workflow advice is common creature modding practice, not checked on `P:\`; tutorials on the subject get several names wrong (table in `SKILL.md`).

## The layers

```
Blender (rig, skeleton, clips)
  -> FBX (custom properties on, no leaf bones, no camera or lamp, animation baked)
  -> Workbench and Object Builder (import, weights, checks)
  -> model.cfg (CfgSkeletons with bone and parent pairs)
  -> animation graph (states, commands, variables, events)   <- most of the creative work
  -> config.cpp (a CfgVehicles class modelled on a vanilla animal)
  -> minimal script (inventory, skinning, hit components)
  -> skeleton XML packed with the mod
  -> in game, on a vanilla AI template (hen, herbivore or predator)
```

Start with the smallest graph that can run, one state with one clip, and see it in game before adding states, variables or events. Building the whole graph offline and finding the fault on the first spawn is the most common mistake.

## Two bones the engine understands

| Bone | Vanilla | Note |
|---|---|---|
| `EntityPosition` | `<bone name="EntityPosition" index = "0" movement = "true" lod = "0" />` (`P:\DZ\anims\cfg\skeletons.anim.xml:5`; the same line follows `Scene_Root` at the top of every animal block; the wolf block starts at `:897`, with `Scene_Root` at `:898` and `EntityPosition` at `:899`) | The bone the engine moves the entity with. Graphs name it: the wolf's attack source predicts on it (`AnimSrcNodePrediction PredictionTurn` with `Bone "EntityPosition"`, `P:\DZ\animals\animations\!graph_files\wolf\wolf_maingraph.agf:52`, `:53`). |
| `LookAt` | `P:\DZ\anims\cfg\skeletons.anim.xml:17` in the block the infected bind (`hermit_newbindpose.xob`), `:444` in `z_hermit.xob` | The look target. There is no `Pin` bone; the "Pin Look At" of some tutorials is this. |

Practice, not checked on `P:\`:

- **Orientation of `EntityPosition`:** forward is +Y (green in Blender) and up is +Z (blue). A wrong orientation makes the animal walk sideways or sink into the ground.
- **Bone names without spaces from the start.** Workbench turns spaces into underscores; Object Builder may not. Use `EntityPosition` style or lower case with underscores.
- **Flying creatures need tricks**; the game has no native flight for AI.
- **Workbench may need a restart** to notice changed bones or skeletons on `P:\`. That is project caching, not a bug.
- If these two bones are added after the rig was built, move each to its proper place before export: `EntityPosition` at the root, `LookAt` as a child of the head.

## The skeleton XML

- The file is `skeletons.anim.xml`, with both dots. Its root is `<skeletons version="1.0">` (`P:\DZ\anims\cfg\skeletons.anim.xml:1`), with one `<skeleton name="....xob">` per skeleton listing `<bone name="..." lod="N" />` entries.
- The engine finds it by its path inside the PBO, not through a config key. The vanilla addon's `config.cpp` holds only its `CfgPatches` class `DZ_Anims_Cfg` (`P:\DZ\anims\cfg\config.cpp:3`); there is no key pointing at the XML.
- For a mod (not tested here): pack an XML for the new skeleton at the same kind of path, `<mod>\anims\cfg\<name>.anim.xml`, and list `DZ_Anims_Cfg` in the mod's `requiredAddons[]`.
- Tutorials blame a missing XML for a crash on first spawn. The more likely cause is the `.xob` skeleton or its bones not being reachable by the graph, since the XML only lists them (not tested). Check that both the XML and the `.xob` it names are in the PBO.

## FBX export from Blender (checklist)

- Custom properties: export them.
- Leaf bones: off.
- Camera and lamp: not in the file.
- Bake animation: on, so Workbench receives the clips.
- Rotation: check the creature's orientation in Workbench right after import, before doing anything else.

## `model.cfg`

The `CfgSkeletons` layout is the same as for any model (`config-driven-animation.md`): pairs of bone and parent. For a creature, inherit the skeleton of a vanilla animal of similar build and add your own bones. Use `isDiscrete = 0`: creatures move organically; 1 is for mechanical parts.

## The graph

What the graph defines:

| Part | Role |
|---|---|
| States | Idle, walk, trot, run, attack, hit, death (one or several by side or zone hit), swim, turn. |
| Sources | Which clip each state plays. |
| Transitions | When to change state: a variable, an event, the end of a clip. |
| Variables | Numbers that steer blending and selection, such as `speed`. |
| Commands | Names the AI and engine use to start states, such as `CMD_Death` and `CMD_Attack`. |
| Events | Markers inside a clip that fire sound, damage or the end of a simulation. |

Vanilla names for commands and variables, with lines, are in `anim-graph.md`. The ones a creature needs first: `CMD_Death`, `CMD_Attack`, `CMD_AttackSuccess`, `CMD_Hit`, `CMD_LookAt`, and the variables `speed`, `SlopeAngleX` and `SlopeAngleZ` (`P:\DZ\animals\animations\!graph_files\wolf\wolf_graph.agr:6`, `:36`, `:41`).

The creature's config names the graph, its default instance and its start node in `class enfanimsys`, as the infected do (`graphname`, `defaultinstance`, `startnode`, `P:\DZ\characters\zombies\config.cpp:74` to `:77`).

### Build it in this order

1. One graph, one state machine, one idle state, one clip.
2. The model in game with a minimal `model.cfg`: geometry, mass, a basic fire geometry. Check the model with `/dayz-p3d-audit`.
3. The creature spawns, is visible, plays the idle and does not crash.
4. Only then: walk to run blended by `speed`, terrain alignment, hit, death, attack.

A fault in one state of a graph built all at once costs hours or days of bisection.

### Locomotion blend

A blend node between walk, trot and run on the `speed` variable, with an explicit transition time. Turn clips must start and end in poses that match the walk and run loops; a turn that starts or ends anywhere else pops.

### Terrain alignment

Copy the vanilla node, a procedural transform on `SlopeAngleX` times π/180 (`anim-graph.md`, "Terrain alignment"), from the animal closest in build.

### Death

Death can be several states, chosen by where and from which side the creature was hit. The vanilla predator graph is the reference to copy.

### Hit and attack

- A hit is a transition from several states (idle, walk, run). A bought asset that only has a standing hit needs hits from the other poses blended in Blender's non-linear editor, or the transition looks broken.
- An attack needs an attack state and a success state. Damage belongs to the success, which the AI signals with `CMD_AttackSuccess`. Events inside the attack clip mark the impact frame and the sound.

### Events

Events fire sound, end a simulation (the death has finished, so the body can be cleaned up) and apply damage on the right frame. Adding events can break a graph whose event table does not list them. When Workbench fails to load a copied vanilla graph, fix the event table before touching logic.

### Clips from bought assets

Stock models rarely come with clips whose start and end poses fit DayZ's transitions. Recombine them in Blender so that walk to run, idle to attack and the rest meet in the same pose.

## AI wiring for an ambient creature

For a harmless ambient animal, such as a gull, that should cost little:

- Copy the AI template of the hen or another ambient animal (`aiAgentTemplate`; how templates are linked is in `skills/_shared/ai/behaviour-config.md`).
- Set its team and friendliness so it does not fight.
- Give it a minimal inventory, a skinning setup and hit components.
- For a predator, copy the wolf or bear and adjust the attack range.

The method throughout: clone the nearest vanilla creature, change as little as possible, test, repeat. Much of this area is thinly documented by Bohemia.

## Known limits (as of March 2024)

Not solved then, and not rechecked: holding two weapons at once, the full bow mechanic, and custom additive locomotion (changing the additive walk and run layer easily breaks the character). A plan that touches any of these is high risk from the first day.

## Blender version

Blender 3.6.8 is the version known to work with the DayZ animation plugin; Blender 4.1 has broken the plugin in at least one setup. Neither is checked here. Start on 3.6.8 and try one short clip on a newer version before committing to it.
