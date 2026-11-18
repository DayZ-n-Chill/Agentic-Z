# Collision killers measured in game

What was measured in game for the three collision killers of `p3d-killers.md` (a collision LOD wound outward, no `ComponentNN` selection, and parts left out of every component), how each is detected and fixed, and short notes on the other model killers. The vehicle killers are in `vehicle-checks.md`; needle triangles and source mesh cleanup are in `collision-mesh-hygiene.md`.

Vanilla models on `P:\` are binarized, so winding and component facts cannot be read from them. The results below were measured in game on test boxes and mod models, and offline with py3d; they are not checked on `P:\`. The vanilla script and model lines that are cited were opened.

## Terms used here

- The Blender to DayZ map: the section "The Blender to DayZ map" of `_shared/models/generated-model-rules.md`. After it, both the cross product `cross(v1-v0, v2-v0)` and the stored normals point away from the side meant to be seen, so on a solid seen from outside both point inward.
- The per component winding check: the section "The per component winding check" of the same file. Every face of every closed, convex `ComponentNN` of a collision LOD must read inward. Its section "Convex collision components" says each component is one closed, convex part.
- The ray set: rays cast in game in the `geom`, `view` and `fire` intersection modes through `RaycastRVProxy`, plus `DayZPhysics.RayCastBullet` for the physics world. How to cast them and which controls to run is in `skills/dayz-launch-test/references/mcp/collision-probes.md`.
- py3d findings such as `ERR_WINDING_INVERTED` are codes of `P3D.validate()` in the DayZ fork of py3d under `scripts/tools/py3d/`. `audit_p3d.py` prints them when that fork is in use.

## Collision LOD wound outward

A collision component (Geometry, View Geometry or Fire Geometry LOD) whose cross product points outward lets the LOD raycasts from outside (`RaycastRV`, `RaycastRVProxy`) pass through it. Those are the rays the action cursor (`view`) and ballistic hits (`fire`) rely on. Its physics body still stops a walking player and holds one standing on top.

Measured in game on a 2 m box with one `Component01` per collision LOD, every face wound inward, against the same file with every face of its Geometry, View and Fire LODs reversed and their normals negated (Visual and Memory LODs identical). Each was packed binarized and unbinarized, and loaded as an `Inventory_Base` item (`physLayer="item_large"`) and as a `HouseNoDestruct`:

| Collision LODs | Rays in `geom`, `view`, `fire` | `RayCastBullet` | Player walking into it | Player on top |
|---|---|---|---|---|
| Wound inward | every ray hits | hits the faces | stopped about 0.36 m before the face | stands on the top |
| Wound outward | no ray hits; vertical rays reach the ground | hits the same faces | stopped about 0.36 m before the face | stands on the top |

- Binarize does not undo the outward winding: the binarized outward boxes missed the same rays.
- A `view` ray cast like the action cursor's, from eye height toward the box, stopped on the inward box and went through the outward one.
- The 0.36 m standoff is the server's reading; the owning client stopped about 0.33 m before the face.
- Right after a teleport, the server keeps the teleported height for about 3 s even above open ground, so a stand test moves the player before reading the server.
- Controls in the same session: a vanilla `HescoBox` stopped the player at the same distance, a free walk covered 7.5 m in 5 s, and a player placed 2.17 m above the ground fell to it.

A walk does not tell the winding either way: these outward boxes stopped the player, and a 0.49 m `item_small` kit let the player through with either winding (`winding-absolute-check.md`, "Reading rules").

Models converted with the Blender to DayZ map took rays from both sides on their Geometry, View and Fire components; after a map that only mirrors the model (determinant +1), none did. That map also leaves the normals outward, so the pair is not a test of the winding alone.

**Root cause.** The collision LOD and the Visual LOD reached the MLOD by different paths. The Blender to DayZ map treats every LOD alike, so the mismatch comes from a LOD that skipped it: collision boxes built in code in DayZ space with outward winding, a collision LOD exported with another axis map, or a face reversal applied to some LODs and not others. The model looks perfect.

**Detection.** The per component winding check decides, once its prerequisites hold: every non-proxy face of the collision LOD belongs to a `ComponentNN` selection (see "No component selection" below), and every component is closed and convex. Compare each face's cross product with `face_centroid - component_centroid`; on a convex component this reads each face exactly. A healthy component has every face pointing toward its centroid, not most of them: one face pointing away is an inverted face. Faces outside every component, an open or non-convex component, a component with no face scored, or a face whose first three corners are collinear (py3d `WARN_DEGENERATE_FACES`) leave the check unresolved. Meet the prerequisite or fix that face first, and never read an empty count as healthy. `audit_p3d.py` does not run this check, and it has no whole LOD centroid check, because that heuristic flags every correct Blender export.

What the script does print, with the DayZ fork of py3d, is a relative check in its `--- py3d validate() ---` section: it compares each collision LOD's winding, seen from that LOD's centroid, with the Visual LOD's and raises `ERR_WINDING_INVERTED` (printed as CRITICAL) when both are uniform and opposite. With any other py3d the section says it did not run. It is a trigger, not the verdict. Measured offline on synthetic unit boxes:

- It fires on a one box collision LOD wound outward under a correct Visual LOD, and clears after `face.vertices.reverse()`.
- It also fires on a healthy inward box when the Visual LOD's cross product points outward: an inside-out Visual LOD (`winding-absolute-check.md`, "The three py3d gates") or a room meant to be seen from inside.
- On a collision LOD of two boxes 4 m apart, one box wound outward raises only `WARN_WINDING_MIXED`, and the same LOD with both boxes inward still reads mixed (16.7 % outward from the LOD's centroid).

After you generate or edit a collision LOD (a procedural sphere, a py3d round trip, a Blender import, an inspector rebuild), run `audit_p3d.py` and the per component check again before deploying: every non-proxy face of every component must read inward. An `ERR_WINDING_INVERTED` that a complete per component check does not confirm says nothing against the collision; check the Visual LOD against the side meant to be seen instead (the Check A table in `winding-diagnostics.md`; a room seen from inside is right as it is). An unresolved check confirms nothing either way.

Run these checks even when the object blocks the player. A body made with `dBodyCreateDynamicEx` takes its shape from the `geoms` passed to it (`P:\scripts\1_core\proto\enphysics.c:51`), not from the LOD, so neither a walk nor a moving body tells the winding. A player walking through the object is not evidence of outward winding either: look for a collision LOD with no `ComponentNN` selection, and at the body itself, its layer, its height and how it was made (`_shared/physics/layers-and-raycasts.md` and `_shared/physics/rigid-body-api.md`). The rolling stone of the physics pack, a `dBodyCreateDynamicEx` sphere, is that case: the player walks through it because its body exists only on the server, and it has no action because it has no View Geometry LOD (`_shared/physics/rigid-body-api.md` and `_shared/physics/drop-and-throw.md`).

**Fix.** Run `face.vertices.reverse()` on each face that reads outward, and only on those, `proxy:*` faces excluded. On a closed, convex component the reading is exact, and a component wound outward reads outward on every face. Never swap `vertices[1]` and `vertices[2]`: it inverts a triangle but turns a quad `[0,1,2,3]` into `[0,2,1,3]`, a crossed face (the py3d README under `scripts/tools/py3d/`).

Never reverse a collision LOD to match the Visual LOD. Shipped collision LODs carry mixed whole LOD signs, while seven debinarized vanilla models and four shipped mod models wind 0 % outward per component (`winding-absolute-check.md`, "Reading rules"). Read the stored normals of the faces you reverse with the Check A table in `winding-diagnostics.md`: negate a face's normals in the same pass only if they pointed outward along with its winding, and keep them if they already pointed inward. Otherwise py3d's absolute check reports the winding against its own normals, `ERR_WINDING_VS_NORMALS`. A normal shared with a face you leave alone gets a new pool entry (`winding-diagnostics.md`, "From Check B to fix").

The Visual LOD has its own face data, so one can be right while the other is inverted. DayZ draws Visual LODs single sided with backface culling, so inverted faces are see-through and show their texture from inside. Check the Visual LOD offline with the absolute check (`winding-absolute-check.md`) and Check A (`winding-diagnostics.md`). The model tools' offline winding gate reads the Blender to DayZ map (`skills/dayz-model-tools/scripts/check_dayz_winding.py`; `skills/_shared/models/tools-winding-gate.md`).

## No component selection

A box whose Geometry, View and Fire LODs carry no `ComponentNN` selection has no collision in any consumer measured: no ray hit in `geom`, `view` or `fire`, no `RayCastBullet` hit, and the player walks through it. No line in the RPT or the script log says so. `component01` and `Component01` behave the same.

Measured in game on one 2 m box written as three MLODs that differ only in the selection on the Geometry, View and Fire LODs, every face wound inward, each loaded packed unbinarized and binarized, as an `Inventory_Base` item (`physLayer="item_large"`) and as a `HouseNoDestruct`:

| Collision selection | Rays per mode (item) | `RayCastBullet` | Player walking into it |
|---|---|---|---|
| `Component01` | 6 of 6, both packings | hit, both packings | stopped 0.36 m before the face |
| `component01` | 6 of 6, both packings | hit, both packings | stopped 0.36 m before the face |
| none | 0 of 6, both packings | no hit | walked through |

The six rays per mode came from above, from each of the four sides at mid height and from inside; both names gave the same faces to the centimetre. The `HouseNoDestruct` copies gave the same answer. A shipped mod model whose collision component is `component01` also took 21 of 21 rays.

Vanilla controls in the same session, layers from their vanilla configs: `HescoBox` (`item_large`) took every ray and stopped the player at 0.36 m; `WoodenCrate` (`item_small`, inherited from `Inventory_Base`) took every ray and did not stop the player. The crate is also low, so the run does not tell whether its layer or its height let the player pass. Either way, a walk-through alone does not show that the collision geometry is missing.

Binarize writes the same ODOL, byte for byte, from the `Component01` and the `component01` MLOD, with the name stored as `component01`.

**Detection.** `P3D.validate()` (`_check_component_naming`) raises `ERR_COMPONENT_NAMING` on each Geometry, View or Fire LOD that has faces outside its proxy triangles and no selection whose name starts with `component`, in any case. When such names exist but none is `Component` and a number (only `Component_01`, say), it raises `WARN_COMPONENT_NAMING` instead. An empty component selection counts as present.

**Fix.** Select each closed, convex part of the collision LOD as its own `ComponentNN` (`Component01`, `Component02`, ...) over all of that part's points and faces, the components together covering the LOD. Renaming `component01` to `Component01` repairs nothing; both work.

Not measured: other spellings (`COMPONENT01`, `Component1`, `Component_01`), names that differ only by case inside one model, more than one component per LOD, a component in some collision LODs and none in others, other consumers (weapon fire, the action cursor, vehicles hitting it, AI), and vehicles.

## Parts left out of every component

Every face of a collision LOD (proxy triangles aside), and every point those faces use, must belong to a `ComponentNN` selection with weight 1: one component per closed, convex part, the components together covering the LOD. A closed part left out of every component collides with nothing in the LODs it is left out of, even when those LODs have other components, and no log line says so. Never merge separate parts into one `Component01` to cover everything: a component that holds two separate parts is not convex.

Measured in game on a pair of 2 m boxes, A in `Component01` and B either in `Component02` or in no component (the files otherwise identical, every face wound inward), packed binarized and unbinarized, as a `HouseNoDestruct` and as an `Inventory_Base` item (`physLayer="item_large"`):

| Box B | Rays on B (`geom`, `view`, `fire`, `RayCastBullet`) | Player walking into B |
|---|---|---|
| `Component02` | 26 of 26 | stopped 0.33 m before the face |
| In no component | 0 of 46; vertical rays reach the ground | walked through: 7.5 m in about 5 s, as on open ground |

Box A took 40 of 40 in the same objects. Binarize keeps the left-out faces in the ODOL (it lowercases the component names), and the engine ignores them.

The `Expert_Mode` sample of the door tutorial (`_shared/animation/door-patterns.md`), spawned the same way, has a lever (18 faces, one closed piece; selection `lever` in Geometry, `door1_open` in Fire) in no component on its Geometry and Fire LODs. The lever took no Geometry, Fire or physics hit (0 of 28), and a player walking into its knob stopped on the block behind it. In its View LOD the lever is `Component09`, one closed piece that is not convex (an octagonal knob and a bar): only the knob answered (3 of 3) and the bar took none (0 of 9). So each collision LOD answers by its own components, and a non-convex component collides only in part.

Not measured: a part left out only in part (one face of a box whose other faces are in a component), a part left out of one LOD alone, weapon fire, the action cursor, vehicles.

**Detection.** `audit_p3d.py` reports this at two strengths:

- Its own `check_component_coverage` counts the union of the `ComponentNN` selections on the Geometry LOD and prints a WARNING for uncovered vertices or faces.
- With the DayZ fork of py3d it also prints the fork's findings: `ERR_COMPONENT_COVERAGE` (CRITICAL) on any of the three collision LODs, and `WARN_COMPONENT_COVERAGE` on the View and Fire LODs. The fork's Geometry WARN is dropped as a duplicate of the script's own.

The fork's `_check_component_coverage` reads the union of the `ComponentNN` selections, in any case, on the Geometry, View and Fire LODs, each LOD on its own:

- It leaves out proxy triangles (a `proxy:` selection holding one triangle and exactly that triangle's three corners; a whole box under a proxy name counts as collision geometry) and points no face uses.
- It groups the uncovered faces into pieces that share a corner position. A piece that is a closed solid (each edge used by two of its faces, once each way, around a volume) with no face and no point in any component raises `ERR_COMPONENT_COVERAGE`, the measured case.
- A piece thinner than 16 float32 steps at its distance from the model's origin (taken as at least 1 m) counts as flat, so a double-sided sheet stays a WARN wherever it lies. Corners are read as the MLOD stores them (float32), so a model reads the same in memory and once written.
- Every other uncovered face (a part left out only in part, an open piece such as a stray triangle, a flat double-sided sheet, a closed piece too thin for the cutoff), and every point of a covered face that no component holds, stays `WARN_COMPONENT_COVERAGE`, whose message says these cases were not measured.
- A LOD with no component at all is `ERR_COMPONENT_NAMING`'s finding. One whose component selections are all empty is read like any other, its closed parts raising the error.

On the three door tutorial samples it is silent on `Simple_Door` and `Door_w_Button` and raises the error on the Geometry and Fire LODs of `Expert_Mode`, for the lever above, although the tutorial's text lists the lever among the parts that take up space.

Count the union of all `ComponentNN` selections, never `Component01` alone. A healthy Geometry LOD of six components of 8 points each (48 points, 36 faces) reads "Component01 covers 8/48 vertices" under a `Component01` only count, yet that model took every ray in game.

## Notes on the other killers

**`autocenter=0`** (rule and audit in `p3d-killers.md`). The property does not have to sit on every collision LOD. Vanilla holds the `autocenter` property exactly once in each of `P:\DZ\gear\camping\wooden_case.p3d`, `sea_chest.p3d`, `watchtower.p3d`, `territory_flag.p3d` and `P:\DZ\gear\containers\55galdrum.p3d`, while `P:\DZ\gear\camping\fence.p3d` holds it seven times. So the Geometry LOD is where it is needed, and more LODs may carry it. The audit checks the Geometry LOD only. In py3d: `lod.properties['autocenter'] = '0'`.

**Memory and Geometry LODs.** A LandContact LOD (`2e15`, the ground contact points) is also worth adding to an object that rests on the ground; 980 vanilla models carry one (`_shared/models/lods.md`). Some online guides give `7e13` for View Geometry and `3e13` for Fire Geometry; in DayZ those are `6e15` and `7e15`. Other `e13` values do exist: `P:\DZ\vehicles\water\boat_01\boat_01.p3d` has a `2e13` LOD in its header (its buoyancy geometry), and eight vanilla models carry a `4e13` GeoPhys LOD (`_shared/conventions/assets.md`).

**Animation selections and axes.** A rig may bind an axis and a selection under different names, tied together only in `model.cfg`. A wheel rig cloned from the vanilla style has the selection `wheelfrontleft` and the axis `wheel_1_1_axis`:

```cpp
class wheel_1_1 { source="wheelfrontleft"; selection="wheelfrontleft"; axis="wheel_1_1_axis"; };
```

A check that expects `wheel_1_1_axis` to need a selection named `wheel_1_1` reports a selection missing that exists under another name; on one custom quad body that guess gave 12 CRITICAL findings, all false. So:

- `audit_p3d.py --model-cfg` reads each animation's own `selection=` and `axis=` and checks those names (`check_animations`).
- The DayZ fork of py3d still guesses from names in `validate()` (`ERR_AXIS_SELECTION_MISSING`, `WARN_AXIS_SELECTION_EMPTY`). The audit drops those two findings when it read a `model.cfg`, and without one prints them only as WARNING, with a note to pass `--model-cfg`.
- Without a `model.cfg`, confirm by hand that both names of each animation exist in the `.p3d`: the axis as a two point Memory selection, the `selection=` in the Visual LOD.

**`box_placing_min` and `box_placing_max`.** `GetProjectionCollisionBox` uses them only when `GetCollisionBox` fails (`P:\scripts\4_world\classes\hologram.c:1069`). The vanilla deployables `wooden_case.p3d`, `sea_chest.p3d` and `55galdrum.p3d` hold `boundingbox_min` and no `box_placing_min` string.

**Closed collision mesh.** A closed component is also a prerequisite of the per component winding check: an open component leaves that check unresolved.

**Collision materials.** View Geometry is not among the LODs whose faces must carry a penetration material; `p3d-killers.md` keeps a material-less View Geometry face as a WARNING, because the vanilla files show that a model carries a penetration material, not which LOD uses it. The penetration materials named there appear as strings in `P:\DZ\gear\camping\wooden_case.p3d`, `sea_chest.p3d` (`wood_desk.rvmat`) and `P:\DZ\gear\containers\55galdrum.p3d` (`metalplate.rvmat`). `audit_p3d.py` checks collision materials on every model, not only vehicle models, and fails the run on Geometry, GeoPhys and Fire Geometry.
