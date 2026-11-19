# Vehicle proxies

How proxy paths, frames and bone selections must be written for a car's body chunks, wheels, crew and doors, how components are tagged, which way a DayZ car faces, and how to bring in a high-detail body as proxies.

Facts were measured against the vanilla sedan and its proxies, shipped third-party car mods and test vehicles. The sedan and its proxies are binarized on `P:\`, so frames and selections read from them came from converted copies (**model knowledge**). The in-game render is the only real test for proxies: offline frame checks and renders passed on test cars that then drew wrong in game.

## Proxy paths have no `.p3d`

A proxy selection is `proxy:<path>.<NNN>`, a three-digit index, and `<path>` has no `.p3d`; the engine adds it when it resolves the model. Vanilla writes `proxy:\dz\vehicles\wheeled\civiliansedan\proxy\sedanwheel.001`, for the model `P:\DZ\vehicles\wheeled\civiliansedan\proxy\sedanwheel.p3d`. Writing `...sedanwheel.p3d.001` makes the engine look for `sedanwheel.p3d.p3d`, so the proxy is dropped without notice: wheels do not simulate and body chunks vanish, while editors and py3d still see the selection. On a wheel this showed as `PHYSICS (W): Proxy with name 'CivSedanWheel_X_Y' was not found in FireGeometry`, a spawn that seemed to freeze, and a car that revs in first gear without moving. Pass `add_proxy(path, index, ...)` a path without `.p3d`, and fix the path before judging the frame.

## Body chunks: model space and the vanilla frame

A geometry-only proxy (one visual LOD, no config class: vanilla `prox_int` and `sedan_engine`, and the body chunks of shipped car mods) draws its model transformed by the frame the engine derives from the proxy triangle. It needs all three:

1. Geometry in model space, at its real place on the car. The vanilla interior spans Y 0.36 to 1.56 and the engine Z -2.30 to -1.12 (`P:\DZ\vehicles\wheeled\civiliansedan\proxy\prox_int.p3d`, `sedan_engine.p3d`). Centring each chunk on the origin piles them all at the origin.
2. A path without `.p3d`.
3. The triangle frame `R=((-1,0,0),(0,0,1),(0,1,0))`, which `py3d.derive_proxy_frame` returns for vanilla `prox_int` and `sedan_engine` and for the body and steering wheel proxies of a shipped car mod. py3d's `canonical_proxy_triangle(rotation=None)` gives a triangle the engine draws turned about 90 degrees.

```python
lod.add_proxy(path, index, origin=(0,0,0), rotation=((-1,0,0),(0,0,1),(0,1,0)), scale=0.1)  # path without .p3d
```

The engine normalises the triangle, so its scale does not change placement, and it does not place a model by its bounding box centre either. Attachment proxies (wheels, crew, doors) are placed by physics and config, so their positions are no reference for body chunks.

Detailed car mods proxy the body and it works; decimating a high-detail body to fit (about 60% for a 167k vertex body) is the wrong default. Measure the import scale against a fixed file, the source model; measuring against your own output shrinks the car about 3% per rebuild.

## Attachment proxies need a bone selection

A proxy the engine binds to a bone (crew, wheel, door) needs two things in the LOD:

1. the `proxy:<path>.<NNN>` selection and triangle, which `add_proxy` creates;
2. a named selection called after the bone, holding the same 3 points and 1 face. Object Builder writes it when you name a proxy; `add_proxy` does not.

Without the second, `Load entity type` logs `PHYSICS (E): Proxy with bone name 'crewdriver' was not found in view geometry level of model`, the crew is not set up, `CrewPositionIndex` returns -1 and the get-in action never shows. Wheels log `PHYSICS (W): Proxy with name 'CivSedanWheel_1_1' was not found in FireGeometry of the shape`. Body chunks have no bone and need no such selection.

The sedan binds every attachment proxy this way in View Geometry and Fire Geometry:

| Bone selection | Proxy |
|---|---|
| `crewdriver` | `crew_driver.001` |
| `crewcodriver` | `crew_cargo.001` |
| `wheel_1_1`, `wheel_1_2`, `wheel_2_1`, `wheel_2_2` | `sedanwheel.003`, `.004`, `.001`, `.002` |
| `doors_driver`, `doors_codriver` | `sedandoors_driver.001`, `sedandoors_codriver.001` |
| `radiator` | `radiator_car.001` |

Wheel bones map by position, not by proxy index. The bone names must also appear in `CfgSkeletons` `skeletonBones[]` of `model.cfg`. The crew models are `P:\DZ\vehicles\wheeled\proxies\crew_driver.p3d` (for `crewdriver`) and `crew_cargo.p3d` (for `crewcodriver`, `crewcargo1`, `crewcargo2`), placed at the crew memory points; memory points named `crewdriver` alone are not enough. The visual LODs of the sedan carry the `wheel_X_Y` selections too, so add them there as well (`attachment-proxies.md`). After each crew or wheel `add_proxy`, create the bone selection from the proxy's points and faces and set the point flags to 63. Measured in game: with the bone selections added, the server RPT showed no `PHYSICS` errors.

## Hub and seat selections share faces with a component

The engine finds collision and action components only by `componentNN`. A hub or seat selection whose faces are in no `componentNN` is invisible to it, and entity creation fails:

- `PHYSICS (E): Won't simulate, wheel wheel_1_1_damper_land has no proper selection in geometry`
- `PHYSICS (E): Action selection 'seat_driver' was not found in view or fire geometry level of model when parsing class Crew::Crew`

Give each hub and seat box both names on the same faces: `wheel_X_Y_damper_land` and a `componentNN` in Geometry, `seat_driver` or `seat_codriver` and a `componentNN` in View Geometry (and Geometry if seats are there). Fire Geometry already does the same for `dmgzone_*`. A collision object must be named `ComponentXX` (per the Bohemia docs).

Check the share of each hub and seat selection's faces that a `componentNN` in the same LOD also covers. Working cars score 100% (the sedan 15 of 15, a shipped car mod 15 of 15, a test quad 60 of 60); a test car that would not spawn scored 0 of 12. Presence checks miss this.

```python
def component_overlap(lod, sel_name):  # 1.0 when correct
    comp = {tuple(sorted(v.point_index for v in f.vertices))
            for n in lod.selections if n.lower().startswith("component")
            for f in lod.selections[n].faces}
    tf = [tuple(sorted(v.point_index for v in f.vertices)) for f in lod.selections[sel_name].faces]
    return sum(k in comp for k in tf) / len(tf)
```

A box hub is a valid component, and seats in Geometry are fine, once they are also `componentNN`.

Vanilla vehicles name components in lower case (`component01`) and work. py3d's `P3D.validate()` up to 1.8.0 flags lower case as `ERR_COMPONENT_NAMING`, and the converted sedan triggers it too, so ignore that case on vehicles; py3d 1.9.0 no longer checks case. Measured in game, `component01` collides like `Component01` on an item and on a `HouseNoDestruct`, binarized or not, and binarize writes both as `component01`. From 1.9.0 the code fires only for a collision LOD with faces and no component at all, which does lose collision on items and buildings; do not ignore that one.

## Which way a car faces

A DayZ car faces -z with the driver on +x. On the converted sedan, headlights, engine and `drown_engine` sit at z -1.7 to -2.4, the reverse light, exhaust and `refill` at z +2.2 to +2.6, and `seat_driver` at x +0.436 (**model knowledge**). Wheels are `wheel_<side>_<axle>`: side 1 is +x, side 2 is -x; axle 1 is the front (-z), axle 2 the rear (+z), so the steered wheels are `_X_1`.

Most other games face +z, so a correct import flips z, and a car that looks turned 180 degrees against its source is usually right. Check it against the sedan's markers; a still render cannot show a front and back swap.

## Wheel spin direction

The `angle1` of each wheel in `model.cfg` must match the direction of its `wheel_X_Y_axis` (two points in Memory). If all four axes share the same X sign, use the same `angle1` on all four (a test quad with `(1,0,0)`; a test car with `(1,0,0)` and `-6.283`). If left and right axes have opposite signs, alternate `angle1` left and right, as a documented 4x4 does. Flipping the right side on uniform axes spins it backwards. Read the axis signs with py3d before setting `angle1`; `skills/dayz-p3d-audit/scripts/audit_getin_wheels.py` does it.

## Bringing in a high-detail body

- Winding through a mirror transform. A transform such as `DayZ=(-s·bx, +s·bz, -s·by)` has a determinant of -1 and flips handedness. A check that compares the transformed geometric normal with the transformed glTF normals is circular: the winding was reversed to make them agree, so it reports about 0% flipped by construction, while the game culls by winding and showed the texture on the inside. Keep the glTF vertex order (`reverse_winding=False`), confirmed in game. Check winding against the DayZ convention or a model known to draw right (`rip-geometry-and-winding.md`).
- A LOD series. Split the body into a shell core (paint, glass, lights, direct geometry) and proxy chunks, each under the per-model vertex ceiling (`binarize-vertex-budget.md`). Run the builders per LOD with decimated regions and LOD-suffixed proxies (`mb_chassis_lod1` and so on); LODs whose body binarizes under the ceiling use direct geometry, the heaviest (usually LOD 0 to 2) use shell and proxies. Decimate per object in headless Blender (Decimate, collapse, `use_collapse_triangulate`) and keep wheels out of the body. Take Geometry, Memory, View Geometry and Fire Geometry from the deployed `.p3d`, so edits made there survive. Judge each LOD and proxy by binarize's verdict, not by a fixed number. Start gently (about 20% from LOD 0 to LOD 1); one test car used five LODs of 182k, 145k, 73k, 23k and 7k plus shadow.
