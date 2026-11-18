# The silent P3D killers: measured detail

The measured evidence behind killers 1 to 10 of `p3d-killers.md`: what was tested in game, how each fault is detected, how it is fixed, and what was not measured. Same numbering as that file. Killers 11 to 13 are vehicle faults and live in `vehicle-checks.md`.

Where this file and `p3d-killers.md` once disagreed (killers 1, 2 and 8), the in-game measurements here are the newer evidence and `p3d-killers.md` was corrected to match.

**Not yet checked on `P:\`.** The measurements below were made in game on mod models (DayZDiag 1.29.163709, TestPowerGrid and synthetic test boxes) and offline with py3d. Vanilla models on `P:\` are binarized, so the winding and component facts cannot be read from them. The vanilla script and config lines that are cited were opened and confirmed.

**Terms used throughout**

- *Rule 12* (the model pipeline skill, numbered in `_shared/models/generated-model-rules.md`): the Blender to DayZ conversion. In a correct MLOD both the cross product `cross(v1-v0, v2-v0)` and the stored normals point away from the side meant to be seen, so on a solid seen from outside both point inward.
- *Rule 18* (same skill): the per-component winding check of a collision LOD. Every face of every closed, convex `ComponentNN` must read inward.
- *Rule 1* (same skill): each collision component is one closed, convex part.
- `scene_raycast`, `RayCastBullet`: the ray battery driven through the dayz-mcp bridge (a script-side `RaycastRVProxy` per intersection mode `geom`, `view`, `fire`, and `DayZPhysics.RayCastBullet` for the physics world).
- py3d findings such as `ERR_WINDING_INVERTED` are codes of `P3D.validate()` in the DayZ fork of py3d under `scripts/tools/py3d/`. `audit_p3d.py` prints them when that fork is in use.

**Contents**

1. Collision LOD wound opposite to the Visual LOD
2. No `ComponentNN` selection in the collision LODs
3. Missing `autocenter=0` LOD property
4. Missing Memory LOD or Geometry LOD
5. Missing `pos center` memory point
6. Missing animation selections and axes
7. Missing `box_placing_min` / `box_placing_max` memory points
8. Incomplete component coverage
9. Non-watertight collision mesh
10. Missing surface material on collision LODs
- Needle triangles in a collision component
- Source meshes for collision: zero-area faces, orphan points, inexact hulls


## 1. Collision LOD Wound Opposite to the Visual LOD (CRITICAL — Most Common from Blender)

A collision component (Geometry, View or Fire Geometry LOD) whose cross product
`cross(v1-v0, v2-v0)` points OUTWARD lets the LOD raycasts (`RaycastRV`, `RaycastRVProxy`)
from outside pass through it, the rays action targeting (`view`) and ballistic hits (`fire`)
rely on (Rule 18 of `_shared/models/generated-model-rules.md` and its symptom triplet). On the boxes measured below
its physics body still stopped a walking player and held one standing on it. A correct MLOD
winds the cross product away from the side meant to be seen and stores its normals the same
way (Rule 12): INWARD on a solid seen from
outside, which every collision component is. Rule 12's in-game probe of 2026-10-01 agrees:
Geometry, View and Fire components converted with its map registered `scene_raycast` hits from
both sides, and after the det=+1 map alone none — a map that also mirrors the model and leaves
its normals outward, so not a winding-only experiment.

**Measured in game** (2026-10-02, DayZDiag 1.29.163709, driven by dayz-mcp): killer #2's 2 m box
(one `Component01` per collision LOD, every face wound inward) against the same bytes with every
face of its Geometry, View and Fire LODs reversed and their normals negated (Rule 18: 6 of 6
faces outward per LOD; `audit_p3d.py`: `ERR_WINDING_INVERTED` on all three; Visual and Memory
LODs byte-identical). Each was packed unbinarized and binarized (binarize does not undo the
outward winding: the binarized outward boxes missed the same rays) and loaded as an
`Inventory_Base` item (`physLayer="item_large"`) and as a `HouseNoDestruct`:

| collision LODs | `scene_raycast` in `geom`, `view`, `fire` | `RayCastBullet` (physics) | player walking into it | player standing on top |
|---|---|---|---|---|
| wound inward | every ray hits | hits the faces | stopped about 0.36 m before the face | stands on the top (MLOD item) |
| wound outward | no ray hits; vertical rays reach the ground | hits the same faces | stopped about 0.36 m before the face | stands on the top (MLOD and binarized items) |

Rays per item and mode: one from above, one from the side, one from inside; on the static copies
one from the side per mode and one from above in `view`. A `view` ray cast like the action
cursor's, from eye height toward the box, stopped on the inward MLOD item and went through the
outward one. The rays and the walk gave the same answer for both packings and both classes; the
standoff is the server's reading (the owner client stopped about 0.33 m before the face). The
stand probe put the player 6-7 cm above the top and moved them for 0.5 s, then read the server:
right after a teleport, standing still, the server kept the teleported height for 3 s even above
open ground. Same-run controls: a vanilla `HescoBox` stopped the player where it did in the
killer #2 run; on open ground the walk covered 7.5 m in 5 s, and a player placed 2.17 m above
the ground and moved for 0.5 s fell to it. On these boxes the outward winding hid the box from
the LOD raycasts and from nothing measured in the physics world. A walk does not diagnose the
winding either way: these outward boxes stopped the player, and a 0.49 m `item_small` kit let
the player through with either winding (`winding-absolute-check.md`, rule 6).

**Root cause**: the collision LOD and the Visual LOD reached the MLOD by different paths.
Rule 12's map treats every LOD alike; the mismatch comes from a LOD that did not go through it
the same way: collision boxes built in code in DayZ space with outward winding (code-built
geometry does not go through the map), a collision LOD exported with another axis map, or a
face reversal applied to some LODs and not to others. The model looks perfect and can still
stop the player (measured above), but the LOD raycasts go through it.

**Detection**: Rule 18's per-component check decides, once its prerequisites hold: every
non-proxy face of the collision LOD belongs to a `ComponentNN` selection (killer #8), and every
component is closed (killer #9) and convex (Rule 1 of `_shared/models/generated-model-rules.md`). Then compare each
face's cross product with `face_centroid - component_centroid`; on a convex component this reads
each face exactly. A healthy component has EVERY face pointing toward its centroid (inward), not
most of them: one face pointing away is an inverted face. Faces outside every component, an open
or non-convex component, a component with no face scored, or a face without a reading (its first
three corners collinear, so a zero cross product: py3d `WARN_DEGENERATE_FACES`) leave the check
unresolved — meet the prerequisite or fix that face first, and never read an empty census as
healthy. `audit_p3d.py` does not run
this check; it reports the relative trigger below. The absolute mesh-center comparison was
removed from the script for false positives.

> **AUTOMATED CHECK (added 2026-05-21; scope corrected 2026-10-02)**: with the DayZ fork of py3d
> in use, `audit_p3d.py` prints a RELATIVE winding check from py3d `P3D.validate()` (its
> `--- py3d validate() ---` section; with any other py3d the section says it did not run). It compares each
> collision LOD's winding orientation, seen from that LOD's centroid, against the **Visual LOD**
> and emits `ERR_WINDING_INVERTED` (printed as CRITICAL) when both are uniform and opposite.
> This replaces the old absolute centroid heuristic, which false-positived on every Blender
> export (left-handed transform) and so was disabled — that disablement is exactly why an
> inverted collision sphere could pass a full audit with "ALL PASSED". The relative check is
> coordinate-system-agnostic, but it judges whole LODs against the Visual LOD, so it is a
> trigger, not the verdict [OFFLINE MEASURED 2026-10-02, py3d 1.8.0, synthetic unit boxes]:
>
> - it fires on a one-box collision LOD wound outward under a Rule 12 Visual LOD, and clears
>   after `face.vertices.reverse()` (for that box's normals, see **Fix**);
> - it also fires on a healthy inward box when the Visual LOD's cross product points outward:
>   an inside-out Visual LOD (`winding-absolute-check.md`, item 1 of "The three py3d gates"), or a room meant to
>   be seen from inside (`winding-absolute-check.md`, rule 4);
> - on a collision LOD of two boxes 4 m apart, one box wound outward raises only
>   `WARN_WINDING_MIXED`, and the same LOD with both boxes inward still reads mixed (16.7 %
>   outward from the LOD's centroid).
>
> **MANDATORY when you GENERATE or EDIT a collision LOD** (procedural sphere, py3d round-trip,
> Blender import, inspector rebuild): re-run `audit_p3d.py` and Rule 18's per-component check
> **before deploying**: with its prerequisites met, every non-proxy face of every component must
> read inward. An `ERR_WINDING_INVERTED` CRITICAL that a complete
> per-component check does not confirm says nothing against the collision: check the Visual LOD
> against the side meant to be seen instead (Check A table in `winding-diagnostics.md`; a room
> seen from inside is right as it is). An unresolved check confirms nothing either way. Run
> these checks even when the object blocks the player: the outward boxes measured above still
> stopped a walking player and held one standing on top, and a body made with
> `dBodyCreateDynamicEx` takes its shape from the `geoms` passed to it (`P:\scripts\1_core\proto\enphysics.c:51`),
> not from the LOD, so neither a walk nor a moving body tells
> the winding. A player walking through the object is not evidence of outward winding either:
> look for a collision LOD with no `ComponentNN` selection (killer #2) and at the body itself
> (its layer, its height, how it was created: the physics pack, `skills/_shared/physics/layers-and-raycasts.md` and `rigid-body-api.md`).

**Fix**: `face.vertices.reverse()` on each face that reads outward, and only on those
(`proxy:*` faces excluded): on a convex, closed component the reading is exact, and a component
wound outward reads outward on every face. Never a `vertices[1]`/`[2]` swap, which inverts a
triangle but turns a quad `[0,1,2,3]` into `[0,2,1,3]`, a crossed face (the py3d README under `scripts/tools/py3d/`).
Do not reverse a collision LOD to match the Visual LOD: shipped collision LODs carry mixed
whole-LOD signs, while seven debinarized vanilla models and four TestPowerGrid models wind 0 % outward per
component (`winding-absolute-check.md`, rule 7). Read the stored normals of the faces you
reverse with the Check A table in `winding-diagnostics.md`: negate a face's normals in the same
pass only if they pointed outward along with its winding (otherwise py3d's absolute check then
reports the winding against its own normals, `ERR_WINDING_VS_NORMALS`); keep them if they already
pointed inward. A normal shared with a face you leave alone gets a new pool entry
(`winding-diagnostics.md`, "From Check B to fix", item 3).

**Why the collision failure may not affect the Visual LOD**: Visual and Geometry LODs have independent face data.
One can be correct while the other is inverted. DayZ renders Visual LODs single-sided with backface culling:
inverted faces are see-through / textured on the inside. Check the Visual LOD offline with the absolute check
(`winding-absolute-check.md`) and Check A (`winding-diagnostics.md`).

*(Corrected 2026-10-02 against Rule 12 of `_shared/models/generated-model-rules.md`, measured in game 2026-10-01, and
Rule 18. This killer was titled "Inverted Face Winding" and opened: "Geometry LOD faces have
normals pointing INWARD. Raycasts from outside pass through without detecting collision — no
collision, no action targeting, no physics." Its root cause read: "Blender Z-up → DayZ Y-up axis
conversion flips triangle winding on collision LODs while leaving the Visual LOD correct." Its
detection read: "Compare each collision LOD's winding orientation against the Visual LOD of the
same model." The automated check took the Visual LOD as the reference, "(which renders correctly
in-game and therefore defines this model's correct convention)", and ended: "If the CRITICAL
fires, swap `vertices[1]`/`[2]` on every face of that LOD so it matches the Visual LOD
convention." The Fix line read: "Swap `vertices[1]` and `vertices[2]` of each inverted face."
The last paragraph ended by pointing at the offline winding gate of the model tools
(`check_dayz_winding.py`). That script then predated Rule 12 and failed a correct export; since
2026-10-02 it reads Rule 12 (`skills/dayz-model-tools/scripts/check_dayz_winding.py`; `skills/_shared/models/tools-winding-gate.md`).)*

*(Measured in game 2026-10-02, the outward boxes above: the opening said an outward component
"lets raycasts from outside pass through without detecting collision — no collision, no action
targeting, no ballistic hits"; the root cause ended "The model looks perfect but is physically
invisible."; and the MANDATORY note ended "A separately-created dynamic physics body
(`dBodyCreateDynamicEx`) can still make the object move, which masks inverted collision winding
— the object rolls but the player walks through it and no action cursor registers." The outward
boxes stopped a walking player like the inward ones and held one standing on top, and only the
LOD raycasts missed them, the `view` rays the action cursor casts among them: the missing action
fits the measurement, the walk-through does not. The sentence matches the
rolling stone in the physics pack (`skills/_shared/physics/rigid-body-api.md` and `drop-and-throw.md`), a
`dBodyCreateDynamicEx` sphere, and that pack puts the stone's walk-through down to a body
created only on the server and its missing action to a missing View Geometry LOD.)*

## 2. No `ComponentNN` Selection in the Collision LODs (CRITICAL)

A box whose Geometry, View and Fire LODs all carried no `ComponentNN` selection had no collision
in any consumer that was measured: no `scene_raycast` hit in `geom`, `view` or `fire`, no
`RayCastBullet` hit, and the player walked through it. No line in the RPT or the script log said
so. `component01` and `Component01` gave the same result as each other.

**Measured in game** (2026-10-02, DayZDiag 1.29.163709, driven by dayz-mcp): one 2 m box written
as three MLODs that are byte-identical except for the selection on the Geometry, View and Fire
LODs: `Component01`, `component01` (those two files differ in exactly three bytes, the `C` of
each name), or none. Each was loaded packed unbinarized and binarized, as an `Inventory_Base` item
(`physLayer="item_large"`) and as a `HouseNoDestruct`, with every face wound inward (Rule 18):

| collision selection | `scene_raycast` (item; geom, view, fire) | `RayCastBullet` (physics) | player walking into it |
|---|---|---|---|
| `Component01` | 6/6 per mode, both packings | hit, both packings | stopped 0.36 m before the face |
| `component01` | 6/6 per mode, both packings | hit, both packings | stopped 0.36 m before the face |
| none | 0/6 per mode, both packings | no hit | walked through |

Rays per item and mode: one from above, one from each of the four sides at mid-height, one from
inside; the two names gave the same faces to the centimetre. The `HouseNoDestruct` copies gave the
same answer on one horizontal ray per mode, the physics ray and the walk. Same-run vanilla
controls (layers from their vanilla configs): `HescoBox` (`item_large`) took every ray and
stopped the player at the same 0.36 m; `WoodenCrate` (`item_small`, inherited from
`Inventory_Base`) took every ray and did not stop the player. The crate is also low, so the run
does not tell whether its layer or its height let the player pass; either way, a walk-through
alone does not show that the collision geometry is missing. A free walk covered the 7.5 m in
about 5 s; a blocked one held for the full 10 s.

**Binarize removes the difference anyway**: from the `Component01` and the `component01` MLOD it
writes the same ODOL, byte for byte, with the name stored as `component01`.

**Detection**: a collision LOD with faces and no `ComponentNN` selection. From py3d 1.9.0,
`P3D.validate()` (`_check_component_naming`) raises `ERR_COMPONENT_NAMING` on each Geometry, View
or Fire LOD that has faces outside its proxy triangles and no selection whose name starts with
`component`, in any case; when there are such names but none is `Component` and a number (only
`Component_01`, say) it raises `WARN_COMPONENT_NAMING` instead. An empty component selection
counts as present there. Up to py3d 1.8.0 it checked the Geometry LOD
only ("No Component selection found"), and the same code also fired on a lowercase
`component01`, which works, so that reading is a false positive.

**Fix**: select each closed, convex part of the collision LOD as its own `ComponentNN`
(`Component01`, `Component02`, ...) over all of that part's points and faces, the components
together covering the LOD (killer #8). Do not rename `component01` to `Component01` to repair
collision: both gave the same results.

**Not measured**: other spellings (`COMPONENT01`, `Component1`, `Component_01`), names that
differ only by case inside one model, more than one component per LOD, a component in some
collision LODs and none in others, consumers other than the three above (weapon fire, the action
cursor, vehicles hitting it, AI), vehicles.

*(Corrected 2026-10-02: titled "Component Selection Case Sensitivity", this entry read: "Geometry
LOD component MUST be `Component01` (uppercase C). The engine string-matches exactly.
`component01`, `COMPONENT01`, or any variation silently fails — engine finds zero components and
ignores ALL collision geometry." and "**Verified against**: TestPowerGrid production models (fridge,
furnace, battery_adapter) all use `Component01`." Those files show which name TestPowerGrid used,
not that another name fails. An earlier run the same day (the kit-box measurement behind rule 6
of `winding-absolute-check.md`) also reported TestPowerGrid's `lf_solarpanel.p3d`, whose collision
component is `component01`, taking 21 of 21 rays.)*

## 3. Missing `autocenter=0` LOD Property

The rule and the audit's behaviour are in `p3d-killers.md` section 3. Two more points:

- **Which LODs carry it.** The property does not have to sit on every collision LOD (Geometry, LandContact, View Geometry, Fire Geometry, plus Roadway and Hit points when present). Vanilla does not do that: the binarized `P:\DZ\gear\camping\wooden_case.p3d`, `sea_chest.p3d`, `watchtower.p3d`, `territory_flag.p3d` and `P:\DZ\gear\containers\55galdrum.p3d` each hold the `autocenter` property exactly once in the whole file, while `P:\DZ\gear\camping\fence.p3d` holds it seven times. So the Geometry LOD is where it is needed, and more LODs may carry it. The audit checks the Geometry LOD only.
- In py3d: `lod.properties['autocenter'] = '0'`.

## 4. Missing Memory LOD or Geometry LOD

Same as `p3d-killers.md` section 4. A LandContact LOD (`2e15`, ground placement contact points) is also recommended for objects that rest on the ground; 980 vanilla models carry one (`_shared/models/lods.md`).

Some online guides quote `7e13` for View Geometry and `3e13` for Fire Geometry; those values misclassify DayZ LODs, where View and Fire Geometry are `6e15` and `7e15`. That does not make every `e13` resolution foreign to DayZ: `P:\DZ\vehicles\water\boat_01\boat_01.p3d` carries a `2e13` LOD in its header (its buoyancy geometry), and eight vanilla models carry a `4e13` GeoPhys LOD (`_shared/conventions/assets.md`).

## 5. Missing `pos center` Memory Point

Same as `p3d-killers.md` section 5; nothing measured beyond it.

## 6. Missing Animation Selections & Axes

The rule is in `p3d-killers.md` section 6. Why the audit reads `model.cfg` and does not guess from names:

A rig may bind an axis and a selection under different names. A cloned vanilla-style wheel rig has the selection `wheelfrontleft` and the rotation axis `wheel_1_1_axis`, tied together only in `model.cfg`:

```cpp
class wheel_1_1 { source="wheelfrontleft"; selection="wheelfrontleft"; axis="wheel_1_1_axis"; };
```

A check that assumes `wheel_1_1_axis` needs a visual selection named `wheel_1_1` reports the selection as missing when it exists under another name. On one custom quad body that guess produced 12 CRITICAL findings, all false. So:

- `audit_p3d.py` with `--model-cfg` reads each animation's own `selection=` and `axis=` and checks those names (`check_animations`).
- The DayZ fork of py3d still makes the name guess in `validate()` (`ERR_AXIS_SELECTION_MISSING`, `WARN_AXIS_SELECTION_EMPTY`). The audit drops those two findings when it checked a `model.cfg`, and prints them only as WARNING, with a note to pass `--model-cfg`, when it did not.
- Without a `model.cfg`, confirm by hand that both names of each animation exist in the `.p3d`: the axis as a two-point Memory selection, the `selection=` in the Visual LOD.

## 7. Missing `box_placing_min` / `box_placing_max` Memory Points

Same as `p3d-killers.md` section 7. The fallback order is in vanilla script: `GetProjectionCollisionBox` uses `box_placing_min` and `box_placing_max` only when `GetCollisionBox` fails (`P:\scripts\4_world\classes\hologram.c:1069`). The vanilla deployables named there (`wooden_case.p3d`, `sea_chest.p3d`, `55galdrum.p3d`) hold `boundingbox_min` and no `box_placing_min` string.

## 8. Incomplete Component Coverage

Every face of a collision LOD (proxy triangles aside), and every point those faces use, must belong
to a `ComponentNN` selection with weight=1: one component per closed, convex part
(Rule 1 of `_shared/models/generated-model-rules.md`), the components together covering the LOD. A closed part left out of
every component collides with nothing in the LODs it is left out of, also when they have other
components (measured in game on two such parts, below): a box left out of all three took no
`scene_raycast` hit in `geom`, `view` or `fire` and no `RayCastBullet` hit, and the player walked
through it; a lever left out of Geometry and Fire took no hit in those LODs and no `RayCastBullet`
hit, and its knob did not stop a player walking into it; no log line said so. A part left out only
in part (one face of a box whose other faces are in a component, or faces whose points sit in one)
was not measured. Never merge separate parts into one `Component01` to make it cover everything: a
component that holds two separate parts is not convex.

`audit_p3d.py` reports this at two strengths. Its own `check_component_coverage` counts the union of the
`ComponentNN` selections on the Geometry LOD and prints a WARNING for uncovered vertices or faces. With
the DayZ fork of py3d it also prints the fork's findings described next: `ERR_COMPONENT_COVERAGE`
(CRITICAL) on any of the three collision LODs, and `WARN_COMPONENT_COVERAGE` on the View and Fire LODs
(the fork's Geometry WARN is dropped as a duplicate of the script's own).

py3d 1.10.0 (`_check_component_coverage`) reads the union of the `ComponentNN` selections, whatever
the case, on the Geometry, View and Fire LODs, against the faces that no component holds and the
points those faces use that no component holds. Proxy triangles (a `proxy:` selection holding one
triangle and, as its 3 points, that triangle's corners; a whole box under a proxy name counts as
collision geometry) and points that no face uses are not counted. It groups the faces into pieces
that share a corner position and raises `ERR_COMPONENT_COVERAGE`, an ERROR, for the case measured
below: a piece that is a closed solid (each edge used by two of its faces, once each way, around a
volume) with no face and no point in any component. It reads each LOD on its own, while the parts
measured below were left out of all three LODs (the box) or of Geometry and Fire (the lever): its
message says that a part left out of one LOD alone was not measured. A piece thinner than 16 float32
steps at its distance from the model's origin (taken as at least 1 m) counts as flat, so a
double-sided sheet stays the WARN wherever it lies; corners are read as the MLOD stores them
(float32), so a model reads the same in memory and once written. Every other face in no component (a
part left out only in part, an open piece such as a stray triangle, a flat double-sided sheet, a
closed piece too thin for the cutoff at its distance from the origin, which errs toward the WARN),
and every point of a covered face that no component holds, stay `WARN_COMPONENT_COVERAGE`, whose
message says they were not measured. A LOD with no component at all is `ERR_COMPONENT_NAMING`'s
finding (killer #2); one whose component selections are all empty is read like any other, its closed
parts raising the ERROR (an empty selection itself was not measured). On the three door samples of
the door tutorial (`skills/_shared/animation/door-patterns.md`) it is silent on `Simple_Door` and `Door_w_Button` and raises the ERROR on
the Geometry and Fire LODs of `Expert_Mode`, whose lever (18 faces, one closed piece: selection
`lever` in Geometry, `door1_open` in Fire) is in no component there, though the tutorial's text
lists the lever among the parts that take up space. py3d 1.10.1, the version under
`scripts/tools/py3d/`, runs this check unchanged. py3d 1.9.0 raises every face in
no component as `WARN_COMPONENT_COVERAGE`, and its message says that a face left out beside covered
ones was not measured: with that version, read a closed part it counts in no component as the
measured case below.

**Measured in game** (2026-10-02, DayZDiag 1.29.163709, driven by dayz-mcp): a pair of 2 m boxes,
A in `Component01` and B either in `Component02` or in no component (the two MLODs byte-identical
apart from the three `Component02` tags; every face wound inward, Rule 18), loaded packed
binarized and unbinarized, as a `HouseNoDestruct` and as an `Inventory_Base` item
(`physLayer="item_large"`):

| box B | rays on B (`geom`, `view`, `fire`, `RayCastBullet`) | player walking into B |
|---|---|---|
| `Component02` | 26/26 | stopped 0.33 m before the face |
| in no component | 0/46; the vertical rays reach the ground | walked through: 7.5 m in about 5 s, as on open ground |

Box A took 40/40 in the same objects. Binarize keeps the left-out faces in the ODOL (it lowercases
the component names); the engine ignores them. The tutorial's `Expert_Mode`, spawned the same way,
gave the lever no Geometry, Fire or physics hit (0/28), and a player walking into the lever's knob
stopped on the block behind it. In its View LOD the lever is `Component09`, one closed piece that
is not convex (an octagonal knob and a bar): only the knob answered (3/3) and the bar took none
(0/9), so that non-convex component collided only in part; each collision LOD answered by its own
components (the lever, a component in View only, was hit in View only). No RPT or script-log line
named any of these models. Not measured: a part left out only in part, weapon fire, the action
cursor, vehicles, DayZ 1.30 Exp.

Up to py3d 1.8.0 the check compared `Component01` alone with the
whole Geometry LOD, so it fired on a healthy multi-component LOD: `gate_and.p3d`'s Geometry LOD
holds six components of 8 points each (48 points, 36 faces) and reads "Component01 covers 8/48
vertices", yet that model took every ray in game (`winding-absolute-check.md`, rule 6).
With that version, count the union of the `ComponentNN` selections yourself.

*(Corrected 2026-10-02: titled "Incomplete Component01 Coverage", this entry read "`Component01`
must include ALL vertices AND ALL faces of the Geometry LOD with weight=1." The first correction
that day still opened "Every vertex and face of a collision LOD must belong to a `ComponentNN`
selection" and said "Partial coverage means partial collision — some faces won't register
raycasts.", a consequence measured only for a LOD with no component at all.)*

*(Updated 2026-10-02, after the in-game A/B above: the first paragraph read "A face outside every
component is expected not to collide, but that was measured only for a LOD with no component at
all (killer #2), not for a face left out next to covered ones.", and the py3d paragraph read "A
face outside every component on a LOD that has others was not measured in game, so the finding
stays a WARN." and closed "whether that lever collides in game was not measured.")*

*(Updated 2026-10-03, py3d 1.10.0: the py3d paragraph opened "py3d 1.9.0 `WARN_COMPONENT_COVERAGE`
(`_check_component_coverage`) reads the union", said "one whose component selections are all empty
is reported here, every face counted. py3d 1.9.0 raises it as a WARN, and its message says that a
face left out beside covered ones was not measured: both predate the in-game A/B below, which
measured whole parts left out beside covered ones." and "flags the Geometry and Fire LODs of
`Expert_Mode`".)*

*(Updated 2026-10-03, after the py3d 1.10.0 review: the first paragraph read "A closed part left out
of every component collides with nothing, also when the same LOD has other components: no
`scene_raycast` hit in `geom`, `view` or `fire`, no `RayCastBullet` hit, the player walks through
it, and no log line says so (measured in game on two such parts, below).", which gave both parts the
box's readings: the lever was a component in View and was hit there, and a walk along its arm was
inconclusive.)*

## 9. Non-Watertight Collision Mesh

Same as `p3d-killers.md` section 9. A closed component is also a prerequisite of the per-component winding check (killer 1): an open component leaves that check unresolved.

## 10. Missing Surface/Material Assignment on Collision LODs

Same as `p3d-killers.md` section 10. View Geometry is not among the LODs whose faces must carry a penetration material: `p3d-killers.md` keeps a material-less View Geometry face as a WARNING, for the reason given there (the vanilla files show that a model carries a penetration material, not which LOD uses it). The penetration materials named in that section's table were confirmed as strings in `P:\DZ\gear\camping\wooden_case.p3d`, `sea_chest.p3d` (`wood_desk.rvmat`) and `P:\DZ\gear\containers\55galdrum.p3d` (`metalplate.rvmat`).

`audit_p3d.py` checks collision materials on every model, not only on vehicle models (a wheel or damper selection), and fails the run on Geometry, GeoPhys and Fire Geometry.

## Needle triangles in a collision component

A needle is a triangle that is almost a line: tiny in area, or tiny against its longest edge. Convex hull builders produce them when two points nearly coincide or a point sits a hair off an edge.

**Measured in game** (DayZ 1.29.163709, a rock model whose collision is many convex hulls, 2026-10-02): two convex hulls built with Qhull that each held one needle took no ray in `geom`, `view` or `fire`, and binarize said nothing. Built again without the point opposite each needle's longest edge, they took every ray. The engine's own limit lies between a ratio of 4.6e-7 (no hit; the needle had an area of 3e-8 m²) and 1.19e-4 (hit).

**Detection**: `audit_p3d.py` (`check_collision_needle_triangles`) reads every face of every `ComponentNN` selection in the Geometry, View and Fire LODs, any case of the name. A quad is read as the two triangles of its fan. It fails a triangle (CRITICAL) whose area is under 1e-6 m², or whose area over the square of its longest edge is under 1e-4. A face at weight 0 is not in the selection. Proxy triangles are left out, by the rule the DayZ fork of py3d uses: a selection named `proxy:<path>.<index>` that holds exactly one triangle and, as its points, exactly that triangle's corners. A selection under a proxy name with any other shape is not a proxy and is read. A face in no component is the coverage check's subject (killer 8), not this one's.

**Fix**: build that hull again without the point the finding names, the corner opposite the needle's longest edge. The procedure for generated hulls is in `_shared/models/py3d-generation.md`, under "Needle triangles".

## Source meshes for collision: zero-area faces, orphan points, inexact hulls

Measured offline on a building generated from Blender whose collision is hundreds of convex pieces (a rock with a helicopter interior, 2026-10-01; the collision recipe is in `_shared/models/lods-authoring.md`, under "Collision of a large building with an interior").

1. **Source meshes carry zero-area faces, and dropping them can leave orphan points.** 5.4 % of the rock's faces and 11 % of the lift cabin's had zero area. Drop them, then emit only the points the remaining faces use: after the drop, 8 points stood 1.5 to 10.8 cm off the surface in the project's fidelity check, all of them corners of dropped faces, and a point without a face poisons any bounding box computed from `lod.points`. The same meshes had about 240 rock faces and 38 interior faces wound against their stored normals. That disagreement does not say which side is wrong (`winding-absolute-check.md`, rule 1), and smoothed normals can point against a face that is right (rule 5): read those faces with the Check A table (`winding-diagnostics.md`) on the MLOD, after the Rule 12 conversion, before reversing any. Its rows are written toward Rule 12's MLOD convention, not toward the Blender mesh before the conversion. The project turned each one to its normals; that step was not checked in game.
2. **`bmesh.ops.convex_hull` hulls are not exactly convex.** In that project's builds the hulls merged near-coplanar triangles into n-gons that are not planar, and fanned back into triangles those folded by a few mm; near-duplicate points made slivers whose plane is noise. Recomputing each hull with Qhull (`scipy.spatial.ConvexHull`), after welding points at 1 mm and dropping the point that made a sliver, left 0 open or non-convex pieces in the project's integrity check. A convexity check needs a model built to fail it, and it must require the models it expects: the project's first version passed on an empty folder.
