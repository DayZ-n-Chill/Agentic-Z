# Animating a custom creature

How a rigged animal, infected or predator gets from Blender to a creature that moves in game: skeleton, export, `model.cfg`, a first graph and the AI wiring. The graph format itself is in `anim-graphs.md`; the script side of creatures (commands, handlers, mind states) is in `skills/_shared/ai/creatures.md`.

Vanilla facts cite `P:\`. Workflow advice is common creature modding practice, not checked on `P:\`. Tutorials on the subject get several names wrong; the table is in `anim-graphs.md`.

## The layers, in order

1. Blender: the rig, the skeleton and the clips.
2. FBX: custom properties on, no leaf bones, no camera or lamp, animation baked.
3. Workbench and Object Builder: import, weights and checks.
4. `model.cfg`: `CfgSkeletons` with bone and parent pairs.
5. The animation graph: states, commands, variables and events. Most of the creative work is here.
6. `config.cpp`: a `CfgVehicles` class modelled on a vanilla animal.
7. A minimal script: inventory, skinning and hit components.
8. The skeleton XML, packed with the mod.
9. In game, on a vanilla AI template (hen, herbivore or predator).

Start with the smallest graph that runs, one state with one clip, and see it in game before adding states, variables or events. Never build the whole graph offline and look for the fault on the first spawn.

## Two bones the engine uses

The engine moves the entity with `EntityPosition` and aims with `LookAt`; their vanilla lines and roles are in `skills/_shared/ai/creature-animation.md`, "Two bones the engine uses". There is no `Pin` bone; the "Pin Look At" of some tutorials is `LookAt`.

Practice, not checked on `P:\`:

- `EntityPosition` faces forward along +Y (green in Blender) with up along +Z (blue). A wrong orientation makes the animal walk sideways or sink into the ground.
- Name bones without spaces from the start. Workbench turns spaces into underscores and Object Builder may not. Use `EntityPosition` style or lower case with underscores.
- If the two bones are added after the rig was built, move each into place before export: `EntityPosition` at the root, `LookAt` as a child of the head.
- Workbench may need a restart to notice changed bones or skeletons on `P:\`. That is project caching, not a bug.
- The game has no native flight for AI, so a flying creature needs workarounds.

## The skeleton XML

- The file is `skeletons.anim.xml`, with both dots. Its root is `<skeletons version="1.0">` (`P:\DZ\anims\cfg\skeletons.anim.xml:1`), with one `<skeleton name="....xob">` per skeleton listing `<bone name="..." lod="N" />` entries. The engine finds it by its path, not by a config key (`skills/_shared/ai/creature-animation.md`).
- For a mod, pack an XML for the new skeleton at the same kind of path, `<mod>\anims\cfg\<name>.anim.xml`, and list `DZ_Anims_Cfg` in `requiredAddons[]` (not tested).
- Tutorials blame a missing XML for a crash on first spawn. The likelier cause is that the graph cannot reach the `.xob` skeleton or its bones, since the XML only lists them (not tested). Check that both the XML and the `.xob` it names are in the PBO.

## FBX export from Blender

- Custom properties: on.
- Leaf bones: off.
- Camera and lamp: not in the file.
- Bake animation: on, so Workbench receives the clips.
- Rotation: check the creature's orientation in Workbench right after import, before anything else.

## `model.cfg`

The `CfgSkeletons` layout is the same as for any model (`model-cfg-animations.md`): bone and parent pairs. For a creature, inherit the skeleton of a vanilla animal of similar build and add your own bones. Use `isDiscrete = 0`, since creatures move organically; 1 is for mechanical parts.

## The graph

| Part | Role |
|---|---|
| States | Idle, walk, trot, run, attack, hit, death (one or several by side or zone hit), swim, turn. |
| Sources | Which clip each state plays. |
| Transitions | When to change state: a variable, an event, the end of a clip. |
| Variables | Numbers that steer blending and selection, such as `speed`. |
| Commands | Names the AI and engine use to start states, such as `CMD_Death` and `CMD_Attack`. |
| Events | Markers inside a clip that fire sound, damage or the end of a simulation. |

A creature needs these first: `CMD_Death`, `CMD_Attack`, `CMD_AttackSuccess`, `CMD_Hit`, `CMD_LookAt`, and the variables `speed`, `SlopeAngleX` and `SlopeAngleZ`. Their vanilla lines are in `anim-graphs.md`; how the config's `class enfanimsys` names the graph, instance and start node is in `skills/_shared/ai/creature-animation.md`.

Build it in this order:

1. One graph, one state machine, one idle state, one clip.
2. The model in game with a minimal `model.cfg`: geometry, mass, a basic fire geometry. Check the model with `/dayz-p3d-audit`.
3. The creature spawns, is visible, plays the idle and does not crash.
4. Only then: walk to run blended by `speed`, terrain alignment, hit, death and attack.

## States that need care

- Locomotion: a blend node between walk, trot and run on `speed`, with an explicit transition time. Turn clips must start and end in poses that match the walk and run loops, or the turn pops.
- Terrain alignment: copy the vanilla node, a procedural transform on `SlopeAngleX` times π/180 (`anim-graphs.md`, "Terrain alignment"), from the animal closest in build.
- Death: several states can be chosen by where and from which side the creature was hit. Copy the vanilla predator graph.
- Hit: a transition from several states (idle, walk, run). A bought asset with only a standing hit needs hits from the other poses blended in Blender's non-linear editor, or the transition looks broken.
- Attack: an attack state and a success state. Damage belongs to the success, which the AI signals with `CMD_AttackSuccess`; events in the attack clip mark the impact frame and the sound.
- Events fire sound, end a simulation (the death has finished, so the body can be cleaned up) and apply damage on the right frame. Adding events can break a graph whose event table does not list them; when Workbench fails to load a copied vanilla graph, fix the event table before touching logic.
- Clips from bought assets rarely start and end in poses that fit DayZ's transitions. Recombine them in Blender so walk to run, idle to attack and the rest meet in the same pose.

## AI wiring for an ambient creature

For a harmless ambient animal such as a gull:

- Copy the AI template of the hen or another ambient animal (`aiAgentTemplate`; how templates link is in `skills/_shared/ai/behaviour-config.md`).
- Set its team and friendliness so it does not fight.
- Give it a minimal inventory, a skinning setup and hit components.

For a predator, copy the wolf or bear and adjust the attack range. Throughout: clone the nearest vanilla creature, change as little as possible, test, repeat. Bohemia documents little of this.

Systems reported unfinished (two weapons, the bow, custom additive locomotion) are listed in `tooling-and-walls.md`, "The walls". Which Blender and plugin version to use is in `anm-clips.md`, "Which Blender plugin, which Blender".
