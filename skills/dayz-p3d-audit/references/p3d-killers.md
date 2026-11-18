# The Silent P3D Killers

These produce ZERO engine errors but break functionality completely. Built from
production debugging where models rendered correctly but had zero collision,
missing animations, or broken textures.

Killers 1 to 10 apply to any model. Killers 11 to 13 apply to wheeled vehicles and
are detailed in `vehicle-checks.md`. The in-game measurements behind killers 1, 2
and 8 are in `killers-detail.md`; the needle triangle fault is in
`collision-mesh-hygiene.md`.

**Contents**

1. Collision LOD wound outward (was "Inverted Face Winding")
2. Component Selection Name
3. Missing `autocenter=0` LOD property
4. Missing Memory LOD or Geometry LOD
5. Missing `pos center` Memory Point
6. Missing Animation Selections & Axes
7. Missing `box_placing_min` / `box_placing_max` Memory Points
8. Incomplete Component Coverage
9. Non-Watertight Collision Mesh
10. Missing Surface/Material Assignment on Collision LODs
11. Wheel model whose Memory LOD has only `ce_center` (vehicles)
12. Wheels placed too low against the body (vehicles)
13. Vehicle Geometry built as one component (vehicles)
- Needle triangles in a collision component
- Common Blender Export Pitfalls
- Script-Side Gotchas

## 1. Collision LOD Wound Outward (CRITICAL once confirmed: Most Common from Blender)

A collision component (Geometry, View Geometry or Fire Geometry LOD) whose cross
product `cross(v1-v0, v2-v0)` points OUTWARD lets the engine's LOD raycasts from outside
pass through it: no action targeting, no ballistic hit. A correct MLOD winds every face
of a collision component INWARD and stores its normals inward too. Measured in game: a box wound inward took every ray in `geom`, `view` and `fire`; the same
box wound outward took none, yet its physics body still stopped a walking player and
held one standing on it (`killers-detail.md`, "Collision LOD wound outward"). So a walk test does not show
this fault, and a player walking through an object is not evidence of it.

**Root cause**: the collision LOD and the Visual LOD reached the MLOD by different
paths: collision built in code with outward winding, a collision LOD exported with
another axis map, or a face reversal applied to some LODs and not to others. The model
looks perfect.

**Detection**: NOT with a naive centroid-based cross-product check against the whole
LOD: DayZ is left-handed and that heuristic produces up to 100% false positives on
correct models. Per component it is exact: on a closed, convex `ComponentNN`, compare
each face's cross product with `face_centroid - component_centroid`; every face must
point toward the centroid. With the DayZ fork of py3d in use, `audit_p3d.py` prints the
fork's relative check, `ERR_WINDING_INVERTED` (CRITICAL), when a collision LOD and the
Visual LOD are wound opposite ways. That finding is a trigger for the per-component
check, not the verdict: it also fires on healthy collision LODs under an inside-out
Visual LOD (`winding-absolute-check.md`). The edge-pair topology and averaged-normal
checks are in `winding-methodology.md` (same folder).

**Fix**: `face.vertices.reverse()` on each face that reads outward, and only on those
(proxy triangles excluded). Do not swap `vertices[1]` and `vertices[2]`: that inverts a
triangle but turns a quad `[0,1,2,3]` into `[0,2,1,3]`, a crossed face. Do not reverse
a collision LOD to make it match the Visual LOD. Then set the stored normals of the
reversed faces as `killers-detail.md`, "Collision LOD wound outward", says.

**Why Visual LOD may not be affected**: Visual and Geometry LODs have independent face
data, so one can be right while the other is inverted. DayZ renders Visual LODs
single-sided with backface culling: an inverted visual face is see-through from
outside and textured on the inside.

## 2. Component Selection Name (NOTE for lowercase, WARNING for other spellings)

The Geometry LOD needs a `Component01` selection (then `Component02` and so on). Object
Builder spells it `Component01`, but lowercase `component01` works too: every binarized
vanilla model on `P:\` stores it in lowercase, so the audit reports lowercase only as a
NOTE. Another spelling such as `COMPONENT01` is a WARNING (it does not fail the run):
rename it to `Component01` to match vanilla. A Geometry LOD with no component selection
at all is CRITICAL, since it has no collision.

Measured in game (`killers-detail.md`, "No component selection"): a box with no `ComponentNN` selection
in its Geometry, View and Fire LODs took no ray, no physics ray, and the player walked
through it, with no log line. `component01` collided exactly like `Component01`, and
binarize writes both as `component01`, so never rename lowercase to repair collision.
Other spellings were not measured. The View and Fire Geometry LODs need their own
components too: with the DayZ fork of py3d in use, the audit prints
`ERR_COMPONENT_NAMING` (CRITICAL) for a View or Fire Geometry LOD that has faces and no
component selection.

## 3. Missing `autocenter=0` LOD property (WARNING; matters only when config.cpp sets autocenter=0)

For items with `autocenter=0` in config.cpp, the Geometry LOD MUST ALSO carry
`autocenter=0` as a named property. Without both, collision is displaced (measured on mod models; not checked on `P:\`).

Vanilla sets `autocenter` in no `CfgVehicles` class: in vanilla `config.cpp` it appears only on `CfgNonAIVehicles` proxy classes such as `ProxyVehiclePart` (`P:\DZ\vehicles\wheeled\config.cpp:23905`). Vanilla carries it in the model instead: 78 of the 82 models under `P:\DZ\gear\camping\` hold the named property `autocenter` with the value `0`, kits and placed objects alike (read from the ODOL strings).

**Where**: Named property on the Geometry LOD (1e13).
In py3d: `lod.properties['autocenter'] = '0'`

## 4. Missing Memory LOD or Geometry LOD (CRITICAL)

A P3D without a Memory LOD (res ~1e15) will have no animation, no bounding data, and
potentially crash the engine. A P3D without a Geometry LOD (res ~1e13) will have zero
collision. The action cursor raycasts the View Geometry LOD, not the Geometry LOD
(`RaycastRVParams` defaults to `ObjIntersectView`, `P:\scripts\3_game\global\dayzphysics.c:88`).

**Required LODs for any interactive DayZ object:**

- LOD 0, Visual (res=0.0): rendering
- Memory (res ~1e15): animation axes, bounding, interaction points
- Geometry (res ~1e13): collision and physics

**Recommended additional LODs:**

- ViewGeo (res ~6e15): cursor and action raycasts; vanilla items carry one (76 of the 82 models under `P:\DZ\gear\camping\`, all 13 under `P:\DZ\gear\containers\` and all 60 under `P:\DZ\gear\tools\`, read from the ODOL headers)
- FireGeo (res ~7e15): ballistic damage zones

The audit reports a missing ViewGeo or FireGeo as a NOTE. It does not ask for a
GeoPhys LOD (res 4e13, the PhysX geometry): only 12 of the 10,626 models under `P:\DZ` carry one, pillows, stretchers, medical cylinders and wire fences among them (read from the ODOL headers; the LOD table is in `skills/_shared/conventions/assets.md`). When a model has one, the audit runs the watertight, degenerate face and material checks on it.

## 5. Missing `pos center` Memory Point

Without `pos center`, the engine calculates bounding center from vertex distribution.
For tall/asymmetric objects (flagpoles where most vertices are in cloth at top), the
calculated center is far from the base, breaking the action targeting pre-filter.

**Fix**: Add `pos center` at `(0.0, 0.0, 0.0)` in Memory LOD for `autocenter=0` items.

## 6. Missing Animation Selections & Axes

If model.cfg defines an animation (like `flag_mast`), the P3D MUST have:

- **Visual LOD**: Named selection matching the animation selection name (e.g. `flag_mast`)
  covering all vertices/faces that should animate
- **Memory LOD**: Named selection matching the axis name (e.g. `flag_mast_axis`) with
  EXACTLY 2 points defining the animation axis (start and end of translation/rotation)

If either is missing, the animation silently does nothing.

## 7. Missing `box_placing_min` / `box_placing_max` Memory Points

For deployable objects using the hologram placement system, the Memory LOD needs:

- `box_placing_min`: single point at the minimum corner of the placement bounding box
- `box_placing_max`: single point at the maximum corner

Without these, the hologram collision check may malfunction (permanently block placement
or never detect terrain collision).

This memory point pair is a fallback. `GetProjectionCollisionBox` first calls `m_Projection.GetCollisionBox(min_max)`, the box of the Geometry LOD, and reads `box_placing_min` and `box_placing_max` only when that fails and `box_placing_min` exists (`P:\scripts\4_world\classes\hologram.c:1067` to `:1075`). Vanilla deployables (`55galdrum`, `wooden_case`, `sea_chest`) hold `boundingbox_min` and no `box_placing_min`, and rely on the Geometry LOD box. Vanilla puts the pair only in the 8 hologram models named `*placing.p3d` under `P:\DZ\gear\camping\` (`fence_kit_placing.p3d`, `territory_flag_kit_placing.p3d` and the tents, among them). So this rule fires only for items without a proper Geometry LOD or with broken `GetCollisionBox()` data. What else placement reads from the model is in `killers-detail.md`, "What vanilla script reads from the collision LODs".

## 8. Incomplete Component Coverage

The Component selections (`Component01` to `ComponentNN`) together cover every vertex and
face of the Geometry LOD, with weight=1. Each component is one convex closed piece. A
non-convex shape is split into several convex components (Object Builder's Find Components),
so do not merge them into one. A closed part left out of every component gets no
collision: its faces do not register raycasts.

Measured in game (`killers-detail.md`, "Parts left out of every component"): a closed part left out of every
component collided with nothing in the LODs it was left out of, even beside covered
parts (0 of 46 rays, and the player walked through), and the one non-convex component
measured collided only in part. A part left out only in part was not measured. With
the DayZ fork of py3d in use, the audit prints `ERR_COMPONENT_COVERAGE` (CRITICAL) for
a closed part in no component on the Geometry, View or Fire Geometry LOD.

## 9. Non-Watertight Collision Mesh

The Geometry LOD mesh must be closed (watertight): every edge shared by exactly 2 faces.
Open meshes (with boundary edges/holes) cause unreliable collision where raycasts can
pass through gaps.

## 10. Missing Surface/Material Assignment on Collision LODs (CRITICAL)

Every face in the collision LODs (Geometry / GeoPhys / FireGeometry / HitPoints) MUST
have a `material` assigned (ViewGeometry is the exception, see below), pointing to a penetration `.rvmat` that in
turn references a `.bisurf` file. Without this assignment, the engine raycasts hit the
geometry but cannot resolve a surface to consult: bullets pass through, footstep sound
is missing, and action cursor may not register.

Vanilla items always ship this: verifiable via `strings <p3d> | grep penetration`:

| Vanilla object   | Penetration material assigned             |
|------------------|-------------------------------------------|
| `55galdrum`      | `dz\data\data\penetration\metalplate.rvmat` + `metalplate.bisurf` |
| `wooden_case`    | `dz\data\data\penetration\wood_desk.rvmat` + `wood_desk.bisurf` |
| `sea_chest`      | `dz\data\data\penetration\wood_desk.rvmat` + `wood_desk.bisurf` |

`audit_p3d.py` runs this check on the Geometry, GeoPhys, FireGeo and ViewGeo LODs. A
face with no material is CRITICAL in Geometry, GeoPhys and FireGeo, but only a WARNING
in ViewGeo: View Geometry blocks sight and the action cursor, and BI models commonly
leave its faces without a penetration material. (Unverified: the vanilla models on P:\
are binarized ODOL, which the audit cannot read, and the `strings` evidence above shows
a model carries a penetration material, not which LOD's faces use it. So the audit does
not fail a run on a material-less ViewGeo.) Detection (py3d):

```python
for lod in p.lods:
    if lod.resolution in collision_lod_ranges:
        for face in lod.faces:
            assert (face.material or '') != '', f"face missing material in {lod_label}"
```

Fix: in Object Builder OR programmatically via py3d, set `face.material =
"dz\\data\\data\\penetration\\<surface>.rvmat"` for every face in every collision LOD
and write back. Visual LOD keeps its complex multi-stage `.rvmat` (e.g. `wooden_case.rvmat`)
unchanged: the penetration `.rvmat` is a SEPARATE simpler material used only by
collision LODs. Symptoms persist after binarization (ODOL preserves the empty
material), so this can be missed until in-game ballistic test.

## 11. Wheel Model Whose Memory LOD Has Only `ce_center` (wheeled vehicles)

A wheel model (the separate `.p3d` placed on the body as a proxy) normally carries five
memory points: `ce_center`, `ce_radius`, `boundingbox_min`, `boundingbox_max` and
`invview`. On one custom quad a wheel with only `ce_center` gave `contact=0` on every
wheel every frame, a bouncing chassis and a speed reading that diverged, with no log
line. Not checked by the script. Detail, the vanilla scan and its one counterexample:
`vehicle-checks.md`.

## 12. Wheels Placed Too Low Against the Body (wheeled vehicles)

A tire bottom below the model origin, or a chassis floor below the wheel-center line,
leaves the belly too close to the ground: `contact=0` at rest and an elastic bounce.
The fix raises wheels and chassis floor together. Not checked by the script; measure
it as `vehicle-checks.md` shows.

## 13. Vehicle Geometry Built as One Component (wheeled vehicles)

A working car's Geometry LOD is many closed convex components, each with mass, plus
wheel hubs. One monolithic hull gives low inertia. It is a construction rule, not the
cause of a launch at spawn: that was traced in game to a `#Mass#` tag on a LOD other
than Geometry, which the audit reports through the DayZ fork of py3d
(`ERR_MASS_ONLY_GEOMETRY`). Diagnose the mass first. Detail: `vehicle-checks.md`.

## Needle Triangles in a Collision Component (CRITICAL)

A triangle that is almost a line, inside a `ComponentNN` of the Geometry, View or Fire
Geometry LOD. In game a convex hull holding one took no ray at all, and binarize said
nothing. The audit fails a triangle under 1e-6 m², or whose area over the square of
its longest edge is under 1e-4, and names the point to drop. Detail and the measured
limits: `collision-mesh-hygiene.md`, "Needle triangles".

---

## Common Blender Export Pitfalls

1. **Collision and Visual LODs can reach the MLOD wound differently**: collision built
   in code, exported with another axis map or reversed on its own does not follow the
   Visual LOD. Check each collision LOD per component (killer 1), independently from
   the Visual LOD. The Blender to DayZ conversion treats every LOD alike.
2. **Blender Geometry LOD may inherit `class=house`** from Object Builder templates
3. **py3d read-write cycles** preserve validity but change file size (~800 bytes per
   property change). This is normal.
4. **Addon Builder binarizes MLOD → ODOL**: mesh defects persist into builds. The
   winding sign does not: on the one path measured it inverted in every triangle pair,
   so never reuse a winding check calibrated on the MLOD to audit the built ODOL
   (`winding-absolute-check.md`, "The sign flips between MLOD and ODOL").
5. **Keep selection names as vanilla spells them**: `Component01` in the MLOD source
   (binarized vanilla models store `component01`, which also works)
6. **Memory LOD must have zero faces**: only single-vertex points. Faces in Memory LOD
   may confuse the engine.
7. **Animation axis points must be in the SAME named selection**: both points of
   `flag_mast_axis` must be in one selection, not split across two.

---

## Script-Side Gotchas

These aren't P3D issues but commonly co-occur during debugging:

- `IsTakeable()` controls pickup, the inventory vicinity list and the target name label,
  not whether the object can be targeted by actions. Vanilla checks it in the take actions
  (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiontakeitem.c:36`),
  in the vicinity filter (`P:\scripts\4_world\classes\useractionscomponent\actiontargets.c:63`)
  and in the name label (`P:\scripts\5_mission\gui\actiontargetscursor.c:719`).
  `BaseBuildingBase.IsTakeable()` returns `false`
  (`P:\scripts\4_world\entities\itembase\basebuildingbase.c:908`), and fences and
  watchtowers keep their actions. Return `false` from it for a non-pickup item. The name label of a non-takeable item shows only when `IsActionTargetVisible()` returns `true`; it returns `false` on `ItemBase` (`P:\scripts\4_world\entities\itembase.c:4378`), and `Fence` and `Watchtower` override it (`P:\scripts\4_world\entities\itembase\basebuildingbase\fence.c:52`; `watchtower.c:21`).
- `CanBeActionTarget()` decides whether an object can be targeted at all: the cursor ray results and the cone search both drop an object that returns `false` (`actiontargets.c:47` and `:267`). The base returns `!IsHologram()` (`P:\scripts\3_game\entities\object.c:1418`), and `EntityAI` also refuses an entity set for deletion (`P:\scripts\3_game\entities\entityai.c:817`).
- The `flag_mast` animation phase decides which flag action shows, and phase 1 means
  fully lowered: the `flag_mast` source of `TerritoryFlag` starts at `initPhase=1` (`P:\DZ\gear\camping\config.cpp:12633` to `:12636`),
  raising lowers the phase (`actionraiseflag.c:61`). `ActionRaiseFlag` needs phase `> 0`
  (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionraiseflag.c:48`)
  and `ActionLowerFlag` needs phase `< 1` (`...\continuous\actionlowerflag.c:43`), both with a
  flag attached. A script that sets a new flag to phase 0 (fully raised) therefore offers only
  `LowerFlag` at first, not `RaiseFlag`.
- SyncVar timing vs RPC cache timing can deadlock ActionConditions.
- A flag kit with `autocenter=0` in a mod's `config.cpp` floated when dropped (measured on a mod; not checked on `P:\`). Vanilla gives `TerritoryFlagKit` no `autocenter` in config, while its model `P:\DZ\gear\camping\territory_flag_kit.p3d` holds the named property `autocenter` at `0`, like the placed `territory_flag.p3d`. So keep `autocenter` out of a kit's `config.cpp`; the model property alone does not make a vanilla kit float.
