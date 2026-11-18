# Door LODs in Object Builder

What each LOD of a door model holds, what the three worked patterns put in each, and the Object Builder checks to run before export. The model is `dayz-object-builder` work. The 1.30 lock memory points are in `building-door-locks.md`, "Memory names the lock code reads".

The three worked patterns come from third party mod samples, not vanilla, so their LOD contents cannot be checked on `P:\` and their models are not in this repo. The lever findings below were measured in game on the handle and lever sample.

## Names carry across every LOD

A moving or interactive part uses the same name in every LOD where it has a role, and the same name in `model.cfg` and `config.cpp`. Not every visible part belongs in every physical LOD: the simple door leaves the handle out of Geometry because it needs no collision, and keeps it in the visible and interaction LODs.

## What each LOD is for

| LOD | Holds | Rules |
|---|---|---|
| Resolution | The visible object. | Name every part that matters to animation or materials; animated names match the skeleton bones and animation selections. |
| Geometry | Collision and physical presence. | Only parts that take up space, under their Resolution names. Closed, convex shapes, found with Structure, Topology, Find Components. |
| View Geometry | Interaction and view occlusion; AI should not see through it. | The interactive named selection lives here and is the `model.cfg` `source`. It may differ from the moving selection. |
| Fire Geometry | Bullet penetration. | The parts that need a penetration value, with fitting penetration RVMATs, named like their components. |
| Memory | Points and axes that are not drawn. | One two point axis per rotation (`door1_axis`, `handle_axis`, `lever_axis`), the `soundPos` point such as `door1_action`, and the interaction point. |

When View Geometry is missing the engine uses Geometry instead (engine behaviour, not visible on `P:\`). The door action finds the door from the View Geometry component the player aims at, through `GetDoorIndex(int componentIndex)` (`P:\scripts\3_game\entities\building.c:28`).

For a separate button or lever, put `door1_open` on the controller in View Geometry so Open appears there and not at the door. A static button need not be a skeleton bone.

If a small handle needs collision in a new design, ask the user before adding it; do not copy the simple door's omission blindly. Building Fire Geometry from View Geometry is what the patterns do, not a rule: check what the new prop needs ballistically.

General axis rules are in `_shared/models/memory-points.md` and `model-cfg-animations.md`.

## What the three patterns put in each LOD

| LOD | Simple door | Door with button | Handle and lever |
|---|---|---|---|
| Resolution | Frame, `door1`, `handle` | Frame, door, handle, button | `door1`, `handle`, `lever` |
| Geometry | `door1`; no handle | `door1` and the button | `door1` and the lever, but the lever is in no component |
| View Geometry | Door and handle interaction and occlusion | The button's selection `door1_open` | The lever's selection `door1_open`, also `Component09` |
| Fire Geometry | The relevant parts with penetration materials | A copy of View Geometry with penetration RVMATs | View Geometry without the lever's component, with penetration RVMATs |
| Memory | `door1_axis`, `handle_axis`, `door1_action`, interaction point | `door1_axis`, `door1_action`, interaction point at the button | Door, handle and lever axes, action and sound point, interaction point |
| Mapping | Handle is a child of the door; both use source `door1` | Only the door is a bone, on source `door1_open` | Handle follows the door, lever follows nothing; all on `door1_open` |

## The lever that collides with nothing

The handle and lever sample means to have the lever in Geometry, but its `Expert_Mode.p3d` leaves the lever out of every component in two of the three collision LODs:

| LOD | Components | The lever (18 faces, 20 points) |
|---|---|---|
| Geometry | `Component01` to `Component05`: frame, door, the block the lever sits on | Selection `lever`, in no component |
| View Geometry | `Component01` to `Component09` | `door1_open`, with `Component09` holding the same 18 faces |
| Fire Geometry | `Component01` to `Component08` | `door1_open`, in no component |

The lever is one closed piece that is not convex: an octagonal knob and a bar, whose convex hull holds 1.4 times its volume. The py3d tool in `scripts/tools/py3d/` reports `ERR_COMPONENT_COVERAGE` on its Geometry and Fire LODs (18 of 48 and 18 of 66 faces in no component), and nothing on the other two samples.

Measured in game with the model spawned as a `HouseNoDestruct`, packed both binarized and not: no Geometry, Fire or physics ray touched the lever, and a player walking into the knob was stopped by the block behind it, not by the knob. In View Geometry only the knob answered rays; the bar took none. Weapon fire and the action cursor were not tested. The general rule is in `skills/dayz-p3d-audit/references/p3d-killers.md`: the component selections together must cover every face.

To make the lever solid in your own model:

1. Rebuild it in Geometry, View Geometry and Fire Geometry as two closed, convex solids, the knob and the bar, each its own `ComponentNN`.
2. Close the octagon's flat side on each part with a face of its own, wound like the rest of that part, with its own points, so the two stay separate solids. Splitting the existing faces into two selections is not enough: the parts share that side and no face closes it, so each would have four open edges.
3. Keep both parts in the lever's other selections: `door1_open` in View Geometry (the Doors source) and `lever` (the selection `model.cfg` animates). The sample's View and Fire LODs have no `lever` selection, so there the lever would stay put while its animation runs (read from the file, not tested in game).
4. Run the Object Builder checks below again.

This repair is not tested in game.

## Object Builder checks

On Geometry, View Geometry and Fire Geometry, in order:

1. Structure, Topology, Find Components.
2. Structure, Convexity, Find Non-Convexities.
3. Look for open or inside out shapes with Solid Fill Faces.
4. Where it fits, repair with Structure, Triangulate Convex.
5. Run the convexity check again.
6. Check the named selections again after any topology change.

Then run `/dayz-p3d-audit` on the MLOD with `--model-cfg` and `--config`; it checks that each animation's selection and axis exist.

## Before export

- [ ] Visible animated parts are named in the Resolution LOD.
- [ ] Only parts that take up space are in Geometry, and its components are found and named.
- [ ] No Geometry, View Geometry or Fire Geometry face lies outside every `ComponentNN`; a part in no component collides with nothing.
- [ ] Geometry, View and Fire shapes are closed and convex.
- [ ] View Geometry holds the source interaction selection and gives the intended occlusion.
- [ ] Fire Geometry has fitting penetration RVMATs.
- [ ] Every rotation has a named Memory axis.
- [ ] The action and sound point matches `soundPos`, and the interaction point is where the action should appear.
- [ ] A static button is out of the skeleton; an animated lever is in it.
- [ ] Names are compared across files character by character.
- [ ] For a lockable building door (1.30), Memory has the slot selections that match `CfgSlots`: `att_combinationlock`, `att_codelock`, or the numbered wood and metal variants.
- [ ] For a one sided door (1.30), Memory has the pair named by `interactPositionPoint` and `interactDirPoint`.
- [ ] For a bunker style inside bypass (1.30), Memory has `<DoorsSubclass>_action` and `<DoorsSubclass>_inside` when you copy the `Bunker` pattern.
