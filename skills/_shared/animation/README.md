# Animation pack

Reference for `dayz-animation-specialist`: moving parts in `model.cfg`, the config entries that feed them, the script that plays them, building doors, clips and graphs, items and weapons in hands, rider poses, the Blender side, and the checks for realistic motion. Open only the file the task needs. The runnable tools (`model.cfg` generator, SEAnim and RTM writers, viewers, rider pose solver, motion contract checker, Mixamo retarget modules) are in `skills/dayz-animation-pipeline/`; its `SKILL.md` says how to run each one.

Vanilla ships `model.cfg` only inside the packed `.p3d` files, so there is no vanilla `model.cfg` text on `P:\` to copy from. The names and values these files quote from vanilla models are the ones stored in the shipped `.p3d` files under `P:\DZ\`; the `model.cfg` key names come from the Binarize input format and are marked as such where they appear. How each statement is marked (vanilla fact, measured result, not checked) is in `tooling-and-walls.md`, "Marking what is checked".

## Moving parts (config driven animation)

| Question | Open |
|---|---|
| How do I write the skeleton bones and the `Animations` block? Which keys, units, engine sources and names? | `model-cfg-animations.md` |
| What goes in `config.cpp` so an animation can be driven: `AnimationSources`, building `Doors`? Why does a source read a phase but not move? | `animation-sources.md` |
| Which script call plays the animation, on which side, and how do clients see it? How do I read a pose back? | `script-hooks.md` |
| A door, hatch or lid on a building or static prop, a door opened by a button or lever, the 1.30 lock rules | `building-doors.md`, then `door-config-and-locks.md` (keys and lock code), `door-lods.md` (what each LOD holds) and `door-patterns.md` (three worked patterns, locks on building doors) |
| A handlebar or steering wheel that turns with the steering | `handlebar-and-steering.md` |
| A get in that puts the player on the correct side of a seat | `get-in-sides.md` |
| Named selections precise enough for action raycasts (seat, grip, door handle) | `selections-for-actions.md` |
| Worked `model.cfg` examples for a generated device (switch, lever, button, LED, panel door): skeleton, animation types, sources, script control, common mistakes | `model-cfg-device-examples.md` |
| What must the user keep straight when the model comes from Blender? | `blender-handoff.md` |
| What does a door need inside the `.p3d` (bones, axes, components, action points), and who writes each part? | `doors.md` (the model side is `dayz-object-builder` work) |

## Clips, graphs and skeletons

| Question | Open |
|---|---|
| Which tool does what, what the agent delivers and what the user runs, the walls, signing, Linux | `tooling-and-walls.md` |
| Where does DayZ use `.rtm`, how is that different from character animation, the `.rtm` format and tools | `rtm-and-character-animation.md` |
| The `.anm` route from keyframes to a clip the game loads, DayZATool, which Blender plugin | `anm-clips.md` |
| Graph, template and instance files, `CMD_` commands, variables, tags, weapon state names, the 1.29 to 1.30 graph port, names tutorials get wrong, which mod changes collide | `anim-graphs.md` |
| What a scripted player command can make the vanilla graph do: locomotion, foot events, `Raised` | `scripted-commands.md` |
| Player bones by zone, hand and IK helpers, twist bones, the frame an IK pose is keyed in | `player-skeleton.md` (measured parent table: `player-skeleton-parents.txt`) |
| A custom animal, infected or other creature from a Blender rig to the game | `creature-rig-to-game.md`; the commands and variables are in `anim-graphs.md`; the config wiring and the two engine bones are in `_shared/ai/creature-animation.md` |
| What 1.30 changed for animation and the migration checklist | `dayz-1-30-changes.md` |
| The old py3d 1.0.0 write quirks and the frame check for a rebake script | `../py3d-mlod-notes.md`, "Writing a `.p3d` from a script" |

## Items, weapons and riders

| Question | Open |
|---|---|
| How does an item get its pose in the hands, how do parts show or hide with attach state, how does script switch the animation instance? | `items-in-hands.md` |
| How a custom weapon sits in the hands and in the sights, and why the grip fix is geometry | `weapon-in-hands.md` |
| A complete custom player weapon animation from Blender to the game | `weapon-anim-blender.md` |
| A weapon clip posed in the interactive viewer and exported as SEAnim | `weapon-anim-viewer.md` |
| What places a driver's or rider's hands and body, and how do I change the pose for one vehicle class without replacing the graph? | `rider-poses.md` |
| A rider pose solved from seat, grip and footpeg anchors, and what was measured with own clips on a rider | `rider-pose-solver.md` |

## Blender

| Question | Open |
|---|---|
| Driving Blender through the MCP server: preflight probe, the 4.4 and 5.0 API break, runtime rules, the authoring stages, checks before delivery | `blender-mcp-workflow.md` |
| What a Blender clip must be to enter the DayZ pipeline: routes, what to key, coordinate maps, loop notetracks | `blender-txa-export.md` |
| Keyframes authored with Blender run from the command line, axis and handedness maps | `blender-headless-authoring.md` |
| Bones, pose spaces, keyframing, Actions, IK, cycles and baking in `bpy` | `blender-bpy-armatures.md` |
| F-curves, easing, modifiers, cameras, constraints, materials, shape keys and drivers in `bpy` | `blender-bpy-objects-camera.md` |
| Rigid bodies, cloth, soft bodies, particles, baking and export in `bpy` | `blender-bpy-physics.md` |
| The animation principles in F-curve terms, the self-audit, previews and the review loop | `blender-realism-and-review.md` |

## Realistic motion

| Question | Open |
|---|---|
| Motion that must look believable, or that clips, stutters, loops badly, or looks right in Blender and wrong in game: the gated workflow and evidence states | `realistic-motion.md` |
| Which file or skill decides what, and what each side hands the other | `motion-authority-and-routing.md` |
| The report and contract formats and every check type of the motion checker | `motion-contract.md` |
| Anatomy, contact, relative lock and collision rules for hands and held objects | `motion-biomechanics.md` |
| Extra checks per kind of animation: player action, weapon, locomotion, creature, vehicle occupant, prop | `motion-domain-gates.md` |
| The evidence ladder, the visual review set and the integration handoff | `motion-evidence.md` |

## Experimental

Nothing in these files has been validated in game; treat every step as untested.

| Question | Open |
|---|---|
| Mixamo or other FBX motion capture onto a Blender rig | `mixamo-retarget.md`, with `mixamo-bone-mapping.md` when the automatic map has gaps |
| Generated survivor locomotion with ARDY, and the untested route into DayZ | `motion-generation-ardy.md` |

## Worked vanilla examples

These three vanilla objects cover the common cases. `animation-sources.md`, `model-cfg-animations.md`, `script-hooks.md` and `blender-handoff.md` refer back to them.

| Case | Config | Script | Model |
|---|---|---|---|
| Building door, no mod script | `P:\DZ\structures\residential\config.cpp:7341` (`Land_HouseBlock_3F_Corner1`, `class Doors` at :7357) | `P:\scripts\4_world\classes\useractionscomponent\actions\interact\actionopendoors.c:1` | `P:\DZ\structures\Residential\HouseBlocks\houseblock_3f_corner1.p3d` |
| Item lid that hides and shows | `P:\DZ\gear\containers\config.cpp:99` (`Barrel_ColorBase` `AnimationSources`) | `P:\scripts\4_world\entities\itembase\barrel_colorbase.c:144` | `P:\DZ\gear\containers\55galDrum.p3d` |
| Gate that rotates with a custom range | `P:\DZ\gear\camping\config.cpp:4418` (`Fence` `AnimationSources`) | `P:\scripts\4_world\entities\itembase\basebuildingbase\fence.c:488` | `P:\DZ\gear\camping\fence.p3d` |

Humanoids rigged to the vanilla skeleton (a custom infected, survivor or NPC) are in the wearables pack (`skills/_shared/wearables/references/body-rigging.md`); `/dayz-model-tools` runs the winding gate on them.
