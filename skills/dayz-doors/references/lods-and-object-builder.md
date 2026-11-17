# LODs and Object Builder for DayZ doors

What each LOD of a door model has to hold, the per pattern requirements of the three tutorial examples, the Object Builder checks to run, and the extra memory points 1.30 reads. The 1.30 section was checked on `P:\` (DayZ 1.30). The rest comes from novoGOD's third party tutorial *Doors_Buttons_Lesson* (cited by file and line; its files are not in this repo) and from one in-game measurement by the author of the source notes.

## Contents

- [Cross-LOD rule](#cross-lod-rule)
- [Resolution LOD](#resolution-lod)
- [Geometry LOD](#geometry-lod)
- [View Geometry LOD](#view-geometry-lod)
- [Fire Geometry LOD](#fire-geometry-lod)
- [Memory LOD](#memory-lod)
- [Pattern matrices](#pattern-matrices)
- [Object Builder validation](#object-builder-validation)
- [Pre-export checklist](#pre-export-checklist)
- [DayZ 1.30: memory points and lock slots](#dayz-130-memory-points-and-lock-slots)
- [Sources](#sources)

## Cross-LOD rule

Names are the contract. A moving or interactive part uses its intended name in every LOD where that role exists, and the same name in `model.cfg` and `config.cpp`.

Not every visible part belongs in every physical LOD. Simple Door leaves the handle out of Geometry because it needs no collision, and keeps it in the visible and interaction LODs (**Simple_Door Readme.txt:9-23**).

## Resolution LOD

Purpose: draw the visible object.

- Name every visible part that matters to animation or materials.
- Simple: frame, door, handle (**Simple_Door Readme.txt:9-10**).
- Button: frame, door, handle, button (**Door_w_Button Readme.txt:9-10**).
- Expert: door, handle, lever (**Expert tutorial:8-9**).
- Animated names must match the skeleton bones and the animation selections.

Do not conclude that every visible part needs collision. Fill the later LODs by function.

## Geometry LOD

Purpose here: physical presence and collision.

- Include only parts that need real space.
- Reuse the name from the Resolution LOD.
- Find components with **Structure > Topology > Find Components**.
- Shapes must be closed and convex.
- Simple: the named door; the handle is left out (**Simple_Door Readme.txt:12-14**).
- Button: **door1** and the button (**Door_w_Button Readme.txt:12**).
- Expert: **door1** and the lever (**Expert tutorial:11**). The tutorial's P3D leaves the lever out of every component: see [Expert Mode lever](#expert-mode-lever-in-no-component-measured-2026-10-02).

If a small handle needs collision in a new design, ask the user before adding it; do not copy the omission blindly.

### Expert Mode lever: in no component (measured 2026-10-02)

The tutorial's text puts the lever in Geometry (**Expert tutorial:11**), but its `Expert_Mode.p3d` leaves the lever out of every component in two of the three collision LODs (read with py3d by the author of the source notes):

| LOD | Components | The lever (18 faces, 20 points) |
|---|---|---|
| Geometry | `Component01` to `Component05`: frame, door, the block the lever is mounted on | selection `lever`, in no component |
| View Geometry | `Component01` to `Component09` | `door1_open`, and `Component09` holding the same 18 faces |
| Fire Geometry | `Component01` to `Component08` | `door1_open`, in no component |

The lever is one closed piece that is not convex: an octagonal knob and a bar (its convex hull holds 1.4 times its volume). The py3d fork under `scripts/tools/py3d/` reports `ERR_COMPONENT_COVERAGE` on the Geometry and Fire LODs in its 1.10.0 and 1.10.1 releases (a closed part in no component: 18 of 48 and 18 of 66 faces); its 1.9.0 release reported the same case as `WARN_COMPONENT_COVERAGE`. On the Simple Door and Door with Button models the coverage check reports nothing.

In game (DayZDiag 1.29.163709, the P3D packed both binarized and not, spawned as a `HouseNoDestruct`), no Geometry, Fire or physics ray touched the lever, and a player walking into the knob was stopped by the block behind it, not by the knob. In View Geometry only the knob answered rays; the bar took none. Copied as it is, the pattern gives a lever that no Geometry, Fire or physics query hits and that does not stop a walking player (weapon fire was not tested), and whose View Geometry component answers rays only at the knob (the action cursor was not tested either). The general rule behind this is in `skills/dayz-p3d-audit/references/p3d-killers.md`: the Component selections together must cover every face.

To make the lever solid in your own model, rebuild it in Geometry, View Geometry and Fire Geometry as two closed, convex solids, the knob and the bar, each its own `ComponentNN`. Splitting the existing faces into two selections is not enough: the knob and the bar share the octagon's flat side and no face closes it, so each group would have four open edges. Close that side on each part with a face of its own, wound like the rest of that part, and give each part its own points there so the two stay separate solids. Keep both parts in the lever's other selections: `door1_open` in View Geometry (the Doors source) and `lever` (the selection `model.cfg` animates). The tutorial's View and Fire LODs have no `lever` selection, so the lever there would stay put while its animation runs (read from the files, not tested in game). Then run [Object Builder validation](#object-builder-validation) again. This repair itself was not tested in game.

## View Geometry LOD

Purpose in the tutorial:

- Interaction components and selections.
- View occlusion: units and AI should not see through a correct object.
- The Geometry LOD stands in when View Geometry is missing (**Simple_Door Readme.txt:16-18**).

Requirements:

- Put the interactive named selection here.
- Match the `model.cfg` **source** to that interaction selection.
- The source may differ from the moving selection.
- For a separate button or lever, put **door1_open** on the controller so Open appears there and not at the door (**Door_w_Button Readme.txt:14-16**; **Expert tutorial:13-15**).
- A static button need not be a skeleton bone (**Door_w_Button Readme.txt:65**).

On the vanilla side, the door action finds the door from the View Geometry component the player aims at: `GetDoorIndex(int componentIndex)` (`P:\scripts\3_game\entities\building.c:28`).

## Fire Geometry LOD

Purpose: bullet penetration and its materials.

- Include the parts that need a penetration value.
- Give them penetration RVMATs that fit the material.
- Keep the names in line with the matching components.
- Simple includes the relevant parts for penetration (**Simple_Door Readme.txt:20-21**).
- Button and Expert describe a copy of View Geometry with penetration RVMATs (**Button tutorial:18**; **Expert tutorial:17**).

A literal copy of View Geometry is the tutorial's pattern, not a general rule. Check what the new prop needs ballistically.

## Memory LOD

Purpose: selections and points that are not drawn, for rotations, actions, sounds and prompts.

Provide:

- A named axis selection for each animated rotation: **door1_axis**, **handle_axis**, **lever_axis** as needed.
- The axis points named by **axis** with **memory = 1**.
- A named sound and action position such as **door1_action**, named by **soundPos**.
- A named interaction point at the door, button or lever.

Simple lists door and handle axes, the door action and sound position, and the interaction point (**Simple_Door Readme.txt:23**). Button moves the interaction point to the button (**Door_w_Button Readme.txt:16**). Expert adds the lever axis and action points (**Expert tutorial:15**).

A rotation axis is a pair of Memory points; the general rules are in `_shared/models/memory-points.md` and `_shared/animation/model-cfg-animations.md`. This file stays on the Doors mapping.

For a door that opens from one side or takes an inventory lock (1.30), also add the Memory names in [DayZ 1.30: memory points and lock slots](#dayz-130-memory-points-and-lock-slots).

## Pattern matrices

### Simple Door

| LOD | What the tutorial requires |
|---|---|
| Resolution | Frame, named **door1**, named **handle**. |
| Geometry | Named **door1**; no handle geometry in this design. |
| View Geometry | Door and handle interaction and occlusion components. |
| Fire Geometry | The relevant parts with penetration materials. |
| Memory | **door1_axis**, **handle_axis**, **door1_action**, the interaction point. |

Mapping: the handle is a child of the door; both animations use source **door1** (**Doors_Buttons_Lesson/Door/Simple_Door.cfg:10-11,29-52**).

### Door with Button

| LOD | What the tutorial requires |
|---|---|
| Resolution | Frame, door, handle, button. |
| Geometry | **door1** and the button. |
| View Geometry | The button's selection **door1_open**; occlusion as needed. |
| Fire Geometry | Named components with penetration RVMATs. |
| Memory | **door1_axis**, **door1_action**, the interaction point at the button. |

Mapping: only the door is a bone; it rotates from source **door1_open** (**Doors_Buttons_Lesson/Door_w_Button/Door_w_Button.cfg:7-10,27-38**).

### Expert Mode

| LOD | What the tutorial requires |
|---|---|
| Resolution | Named **door1**, **handle**, **lever**. |
| Geometry | **door1** and the lever. The tutorial's P3D leaves the lever out of every component ([measured](#expert-mode-lever-in-no-component-measured-2026-10-02)). |
| View Geometry | The lever's selection **door1_open**; occlusion as needed. In the tutorial's P3D the lever is also `Component09`, one component that is not convex and answers rays only at its knob. |
| Fire Geometry | Named components with penetration RVMATs. The tutorial's P3D leaves the lever out of every component. |
| Memory | Door, handle and lever axes, the action and sound point, the interaction point. |

Mapping: the handle follows the door; the lever follows nothing; all use source **door1_open** (**Doors_Buttons_Lesson/Expert_Mode/Expert_Mode.cfg:7-12,29-64**).

## Object Builder validation

Run on Geometry, View Geometry and Fire Geometry:

1. **Structure > Topology > Find Components**.
2. **Structure > Convexity > Find-NonConvexities**.
3. Look for open or inside out shapes with **Solid Fill Faces**.
4. Where it fits, use **Structure > Triangulate Convex**, the repair the tutorial's author prefers.
5. Run the convexity check again.
6. Check the named selections again after any topology change.

Menu paths and tips: **Simple_Door Readme.txt:12-14**. Then run `/dayz-p3d-audit` on the MLOD with `--model-cfg` and `--config`; it checks that each animation's selection and axis exist.

## Pre-export checklist

- [ ] Visible animated parts are named in the Resolution LOD.
- [ ] Only parts that take up space are in Geometry.
- [ ] Geometry components are found and named.
- [ ] No Geometry, View Geometry or Fire Geometry face lies outside every `ComponentNN`. In game, a part left out of every component collided with nothing.
- [ ] Geometry, View and Fire shapes are closed and convex.
- [ ] View Geometry holds the real source interaction selection.
- [ ] View Geometry gives the intended occlusion.
- [ ] Fire Geometry has fitting penetration RVMATs.
- [ ] Every rotation has a named Memory axis.
- [ ] The action and sound point matches the config's **soundPos**.
- [ ] The interaction point is where the action should appear.
- [ ] A static button is left out of the skeleton; an animated lever is in it.
- [ ] Names are compared across files character by character.
- [ ] (1.30, lockable building door) Memory has the slot selections that match `CfgSlots`: `att_combinationlock`, `att_codelock`, or the numbered wood and metal variants.
- [ ] (1.30, one sided door) Memory has the pair named by `interactPositionPoint` and `interactDirPoint`.
- [ ] (1.30, bunker style inside bypass) Memory has `<DoorsSubclass>_action` and `<DoorsSubclass>_inside` when you copy the `Bunker` pattern.

## DayZ 1.30: memory points and lock slots

The tutorial's Memory LOD (axes, `soundPos`, interaction) is unchanged. 1.30 adds named points that script reads, not `class Animations`.

| Role | Config or script name | Memory names | Where |
|---|---|---|---|
| Lock attachment proxy | the `selection` of the `CfgSlots` class | `att_combinationlock`, `att_codelock`, and the numbered wood and metal variants | `Slot_Att_CombinationLock`, `P:\scripts\config.cpp:2316` to `:2321`; `Slot_Att_CodeLock`, `P:\scripts\config.cpp:2768` to `:2773` |
| One sided open and close | `interactPositionPoint` and `interactDirPoint` on the Doors child | whatever strings you write there; empty or missing means `MemPointDirectionalCheck` returns true | `P:\scripts\3_game\entities\additionaldoorsinfo.c:34` to `:38`; `MemPointDirectionalCheck`, `P:\scripts\4_world\static\miscgameplayfunctions.c:942` |
| Bunker inside against outside | `Bunker.CanDoorBeOpened` builds `"%1_action"` and `"%1_inside"` from `doorInfo.m_DoorType` | for a Doors subclass `Door1`: `Door1_action` and `Door1_inside` | `CanDoorBeOpened`, `P:\scripts\4_world\entities\building\bunker.c:47` to `:54` |
| Code lock facing | `MEMPOINT_CENTER` and `MEMPOINT_INSIDE` of `DigitalCodeLock`, on the item's own P3D | `ce_center`, `inside` | `P:\scripts\4_world\entities\itembase\codelock.c:3` to `:4`, used at `:221` |
| Combination lock faces | selections on the item | `lock_attached_outside`, `lock_attached_inside` | `LOCK_SELECTION_OUTSIDE`, `P:\scripts\4_world\entities\itembase\combinationlock.c:27` to `:28` |
| Bunker crate spawn | `BroadcastedBunker` | `storagecratepos`, `storagecratedir` | `CRATE_SPAWN_POSITION_MEM_NAME`, `P:\scripts\4_world\entities\building\bunker.c:175`; `storagecratedir`, `:316` |

Design note: a custom building that should take the vanilla `CombinationLock` or `DigitalCodeLock` needs the slot selection in Memory (and usually a proxy in the Resolution LOD) whose name matches the `selection` of the `CfgSlots` class. The fence already lists both slots at entity level (`attachments[]`, `P:\DZ\gear\camping\config.cpp:4362` to `:4368`).

Doors of a house that can be rebuilt: `doorConstructionPhysicsSource` names an `AnimationSources` entry, not a Memory point. `Rebuilding` sets its phase to 1.0 when the door starts to open and to 0.0 when it starts to close (`OnConstructionDoorOpenStart`, `P:\scripts\4_world\classes\rebuilding\rebuilding.c:439` to `:461`).

## Sources

Tutorial ranges read in full context:

- **Simple_Door Readme.txt:6-23**
- **Door_w_Button Readme.txt:6-18**
- **Welcome to novoGODs Expert_Mode Door mod.txt:5-17**
- **WELCOME TO novoGODS Shit Door Tutorial.txt:17-22**

Measured in game by the author of the source notes: the Expert lever's missing collision (2026-10-02, DayZDiag 1.29.163709; [Expert Mode lever](#expert-mode-lever-in-no-component-measured-2026-10-02)).

Official LOD reference the tutorial points at:

- https://community.bistudio.com/wiki/LOD
