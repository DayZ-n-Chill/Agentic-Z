# Animation pack

Reference for `dayz-animation-specialist`: moving parts in `model.cfg`, the config entries that feed them, the script that plays them, building doors, clips and graphs, items and weapons in hands, rider poses, the Blender side, and the checks for realistic motion. Open only the file the task needs. The SEAnim and RTM format package is in `scripts/tools/dayz-animation-formats/`. The other runnable tools (`model.cfg` generator, viewers, rider pose solver, motion contract checker, Mixamo retarget modules) are in `skills/dayz-animation-pipeline/`; its `SKILL.md` says how to run each one.

Vanilla ships `model.cfg` only inside the packed `.p3d` files, so there is no vanilla `model.cfg` text on `P:\` to copy from. The names and values these files quote from vanilla models are the ones stored in the shipped `.p3d` files under `P:\DZ\`; the `model.cfg` key names come from the Binarize input format and are marked as such where they appear. How each statement is marked (vanilla fact, measured result, not checked) is in `tooling-and-walls.md`, "Marking what is checked".

## Moving parts (config driven animation)

| Question | Open |
|---|---|
| How do I write the skeleton bones and the `Animations` block? Which keys, units, engine sources and names? | `model-cfg-animations.md` |
| What goes in `config.cpp` so an animation can be driven: `AnimationSources`, building `Doors`? Why does a source read a phase but not move? | `animation-sources.md` |
| Which script call plays the animation, on which side, and how do clients see it? How do I read a pose back? | `script-hooks.md` |
| A door, hatch or lid on a building or static prop, a door opened by a button or lever, the 1.30 lock rules | `building-doors.md`, then `door-config-and-locks.md` (the `model.cfg` and `config.cpp` keys), `door-lods.md` (what each LOD holds), `door-patterns.md` (three worked patterns), `door-open-and-lock-code.md` (the 1.30 open check and one sided doors) and `building-door-locks.md` (combination and code locks on building doors, moving a 1.29 door mod) |
| A handlebar or steering wheel that turns with the steering | `handlebar-and-steering.md` |
| A get in that puts the player on the correct side of a seat | `get-in-sides.md` |
| Named selections precise enough for action raycasts (seat, grip, door handle) | `selections-for-actions.md` |
| The `model.cfg` of a small device (switch, button, dial, lid, LED): skeleton, animation types, memory axes and travel, which LODs need the selection | `device-model-cfg.md` |
| Config sources, script control and worked patterns for a device: toggle, push button, lid, dial, drawer, linked animations | `device-animation-patterns.md` |
| A complete switch box in `model.cfg`, `config.cpp` and script, and the two ways to light a screen | `device-switch-box.md` |
| What must the user keep straight when the model comes from Blender? | `blender-handoff.md` |
| What does a door need inside the `.p3d` (bones, axes, components, action points), and who writes each part? | `doors.md` (the model side is `dayz-object-builder` work) |

## Clips, graphs and skeletons

| Question | Open |
|---|---|
| Which tool does what, what the agent delivers and what the user runs, the walls, signing, Linux | `tooling-and-walls.md` |
| Where does DayZ use `.rtm`, how is that different from character animation, the `.rtm` format and tools | `rtm-and-character-animation.md` |
| The `.anm` route from keyframes to a clip the game loads, DayZATool, which Blender plugin | `anm-clips.md` |
| Graph files, `CMD_` commands, variables, terrain alignment, tags, names tutorials get wrong, which mod changes collide | `anim-graphs.md` |
| Instance (`.asi`) and template (`.ast`) files, the player's instances, weapon state names, what a weapon states clip stores | `anim-instances-and-templates.md` |
| The 1.30 graph syntax and node types, opening the player graph in Workbench, porting a 1.29 graph | `anim-graph-format-1-30.md` |
| What a scripted player command can make the vanilla graph do: locomotion, foot events, `Raised` | `scripted-commands.md` |
| Player bones by zone, hand and IK helpers, twist bones, the frame an IK pose is keyed in | `player-skeleton.md` (measured parent table: `player-skeleton-parents.txt`) |
| A custom animal, infected or other creature from a Blender rig to the game | `creature-rig-to-game.md`; the commands and variables are in `anim-graphs.md`; the config wiring and the two engine bones are in `_shared/ai/creature-animation.md` |
| What 1.30 changed for animation and the migration checklist | `dayz-1-30-changes.md` |
| The old py3d 1.0.0 write quirks and the frame check for a rebake script | `_shared/py3d-mlod-notes.md`, "Writing a `.p3d` from a script" |

## Items, weapons and riders

| Question | Open |
|---|---|
| How does an item get its pose in the hands, and how does script switch the animation instance? | `items-in-hands.md` |
| How do parts of a model show, hide or swap with attach state? | `attach-state-parts.md` |
| How a custom weapon sits in the hands and in the sights, and why the grip fix is geometry | `weapon-in-hands.md` |
| A custom player weapon animation from Blender to the game: what it is, the two routes, plugin setup, the rig and its IK helpers, starting from a vanilla pose | `weapon-anim-blender.md` |
| Authoring each kind of weapon clip: IK pose, fire, weapon states, reload, hold actions with loop notes, helper bone rules | `weapon-anim-authoring.md` |
| Exporting `.txa`, events, the plugin's coordinate changes, compiling in Workbench and what the compile loses | `weapon-anim-compile.md` |
| The weapon's instance file, state names, script registration and bone remap, its `model.cfg` and `config.cpp`, mod layout | `weapon-anim-wiring.md` |
| Building and testing a weapon animation, the elbow, failure catalogue, checklist, AKM frame budget, open questions | `weapon-anim-testing.md` |
| A weapon clip posed in the interactive viewer and exported as SEAnim | `weapon-anim-viewer.md` |
| What places a driver's or rider's hands and body, and how do I change the pose for one vehicle class without replacing the graph? | `rider-poses.md` |
| A rider pose solved from seat, grip and footpeg anchors, and how it becomes clips | `rider-pose-solver.md` |
| What was measured in game with a per class rider pose and with own clips on a rider: the steering clip's 45 degree span, absolute transitions, the grip hole | `rider-pose-measured.md` |

## Blender

| Question | Open |
|---|---|
| Driving Blender through the MCP server: preflight probe, the 4.4 and 5.0 API break, runtime rules, the authoring stages, checks before delivery | `blender-mcp-workflow.md` |
| What a Blender clip must be to enter the DayZ pipeline: the two export routes, what to deliver, the plugin setup, Export Type | `blender-txa-export.md` |
| Which bones a `.txa` export keys or leaves out, and the axis maps of the plugin and the SEAnim exporter | `txa-bones-and-axes.md` |
| `LoopStart` and `LoopEnd` for an action a script timer ends, such as an unjam | `loop-notetracks.md` |
| Keyframes authored with Blender run from the command line, axis and handedness maps | `blender-headless-authoring.md` |
| Bone matrices, pose spaces and rotation modes in `bpy` | `blender-bpy-armatures.md` |
| Key types, inserting keys, Actions, the NLA and cycles in `bpy` | `blender-bpy-keyframes-and-actions.md` |
| IK constraints, baking constrained motion and operator context in `bpy` | `blender-bpy-ik-and-baking.md` |
| F-curves, Action slots, interpolation and easing in `bpy` | `blender-bpy-fcurves.md` |
| Noise, Cycles, Smooth and the other F-curve modifiers | `blender-bpy-fcurve-modifiers.md` |
| Camera lens and aim, paths, orbit rigs, constraints, parenting, motion paths in `bpy` | `blender-bpy-objects-camera.md` |
| Material keys, drivers and shape keys in `bpy` | `blender-bpy-materials-drivers.md` |
| Rigid bodies, constraints, throwing, scale and gravity in `bpy` | `blender-bpy-physics.md` |
| Cloth, soft bodies and particles in `bpy` | `blender-bpy-cloth-and-particles.md` |
| Baking simulations to keys, FBX and Alembic export | `blender-bpy-sim-baking-export.md` |
| The animation principles in F-curve terms, fixes for robotic motion, frame counts, camera feel | `blender-realism-and-review.md` |
| The numeric self-audit, stills and previews, which frames to review, the stages from blocking to polish | `blender-review-loop.md` |

## Realistic motion

| Question | Open |
|---|---|
| Motion that must look believable, or that clips, stutters, loops badly, or looks right in Blender and wrong in game: the steps, checks and result states | `realistic-motion.md` |
| Which file or skill decides what, and what each side hands the other | `motion-authority-and-routing.md` |
| The report and contract formats and every check type of the motion checker | `motion-contract.md` |
| Anatomy, contact, relative lock and collision rules for hands and held objects | `motion-biomechanics.md` |
| Extra checks per kind of animation: player action, weapon, locomotion, creature, vehicle occupant, prop | `motion-domain-gates.md` |
| What counts as evidence at each step, the renders to capture, the handoff to the DayZ pipeline and the result states | `motion-evidence.md` |

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
| Gate that rotates with a custom range | `P:\DZ\gear\camping\config.cpp:4428` (`Fence` `AnimationSources`) | `P:\scripts\4_world\entities\itembase\basebuildingbase\fence.c:502` | `P:\DZ\gear\camping\fence.p3d` |

Humanoids rigged to the vanilla skeleton (a custom infected, survivor or NPC) are in the wearables pack (`skills/_shared/wearables/references/body-rigging.md`); `/dayz-model-tools` runs the winding gate on them.
