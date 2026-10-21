# Blender handoff notes

What to tell the user when a moving part is modelled in Blender, so the bones and selections line up when the model reaches Object Builder. These are notes for the user to follow in their own tools. Agentic-Z ships no Blender tooling, and this specialist never runs Blender.

## What the user gets from you

A short list, one line per moving part:

| Item | Example |
|---|---|
| Bone and selection name | `door_1` |
| Parent bone, if any | `door_1_handle` under `door_1` |
| Axis memory points | `door_1_axis`, two points on the hinge line |
| Which LODs carry the selection | every visual LOD that shows the part, plus Geometry, FireGeometry and ViewGeometry where the part has a component |
| Rest pose | closed, so phase 0 means closed |
| Pivot side and direction | hinge on the left, opens away from the player |

## Rules for the export

1. **Names are the contract.** The selection name in the `.p3d` is the bone name in `skeletonBones[]` and the `selection` of the animation. Vanilla models keep them identical: the house door bone is `doors5` with axis `doors5_axis` (`P:\DZ\structures\Residential\HouseBlocks\houseblock_3f_corner1.p3d`). Use lower case with underscores so the names survive any export tool unchanged.
2. **Model the part closed.** The animation moves from the modelled pose, so the rest pose must be the phase 0 state.
3. **Hinges come from memory points, not from Blender pivots.** Object origins and pivots in Blender do not carry into the game. The axis is the two point selection in the Memory LOD, placed by the user or by `dayz-object-builder`.
4. **One part, one selection group.** Every face of the door, the handle and its geometry component sit in that part's selection. Faces left out stay behind when the part moves.
5. **Do not rely on exported armatures.** For `model.cfg` animations the skeleton is the bone list in `model.cfg`; the `.p3d` only needs the matching named selections.
6. **Character clips are a different job.** A rig meant for player animation follows the bone list in `P:\DZ\anims\cfg\skeletons.anim.xml` and goes through Workbench, which is out of scope (see `rtm-and-character-animation.md`).

## After the import

Ask `dayz-object-builder`, through the art lead, to check the selections and memory points in Object Builder and to run `/dayz-p3d-audit` on the mod's model. Then write or update `model.cfg` to match the names it reports.
