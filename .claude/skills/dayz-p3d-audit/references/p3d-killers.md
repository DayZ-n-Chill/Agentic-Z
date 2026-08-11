# The 10 Silent P3D Killers

These produce ZERO engine errors but break functionality completely. Built from
production debugging where models rendered correctly but had zero collision,
missing animations, or broken textures.

## 1. Inverted Face Winding (CRITICAL — Most Common from Blender)

Geometry LOD faces have normals pointing INWARD. Raycasts from outside pass through
without detecting collision — no collision, no action targeting, no physics.

**Root cause**: Blender Z-up → DayZ Y-up axis conversion flips triangle winding on
collision LODs while leaving the Visual LOD correct. The model looks perfect but is
physically invisible.

**Detection**: NOT with a naive centroid-based cross-product check — DayZ is
left-handed and that heuristic produces up to 100% false positives on correct
models. Use the edge-pair topology and averaged-normal checks described in
`winding-methodology.md` (same folder).

**Fix**: Swap `vertices[1]` and `vertices[2]` of each inverted face.

**Why Visual LOD isn't affected**: Visual and Geometry LODs have independent face data.
The renderer draws both sides; collision only detects the "front" face.

## 2. Component Selection Case Sensitivity (CRITICAL)

Geometry LOD component MUST be `Component01` (uppercase C). The engine string-matches
exactly. `component01`, `COMPONENT01`, or any variation silently fails — engine finds
zero components and ignores ALL collision geometry.

Field-verified: production placed-object models all use `Component01`.

## 3. Missing `autocenter=0` LOD Property (CRITICAL for Inventory_Base)

For items with `autocenter=0` in config.cpp, the Geometry LOD MUST ALSO carry
`autocenter=0` as a named property. Config property controls the visual mesh;
LOD property controls the collision mesh. Without both, collision is displaced.

**Where**: Named property on Geometry (1e13), GeoPhys (2e13), FireGeo (3e13) LODs.
In py3d: `lod.properties['autocenter'] = '0'`

## 4. Missing Memory LOD or Geometry LOD (CRITICAL)

A P3D without a Memory LOD (res ~1e15) will have no animation, no bounding data, and
potentially crash the engine. A P3D without a Geometry LOD (res ~1e13) will have zero
collision and zero action targeting.

**Required LODs for any interactive DayZ object:**

- LOD 0: Visual (res=0.0) — rendering
- Memory (res ~1e15) — animation axes, bounding, interaction points
- Geometry (res ~1e13) — collision and cursor raycasting

**Recommended additional LODs:**

- GeoPhys (res ~2e13) — physics collision (player walking, vehicles)
- FireGeo (res ~3e13) — ballistic damage zones

## 5. Missing `pos center` Memory Point

Without `pos center`, the engine calculates bounding center from vertex distribution.
For tall/asymmetric objects (flagpoles where most vertices are in cloth at top), the
calculated center is far from the base — breaking the action targeting pre-filter.

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

- `box_placing_min` — single point at the minimum corner of the placement bounding box
- `box_placing_max` — single point at the maximum corner

Without these, the hologram collision check may malfunction (permanently block placement
or never detect terrain collision).

**Note (empirical, vanilla 1.x)**: This memory-point pair is a *fallback*. Vanilla
`hologram.c::GetProjectionCollisionBox` first calls `m_Projection.GetCollisionBox(min_max)`,
which returns the bbox derived from the Geometry LOD; only if that fails does it fall
back to `box_placing_*`. Vanilla deployables (`55galdrum`, `wooden_case`, `sea_chest`,
`MilitaryCrate` from a6_base_storage) ship `boundingbox_min/max` as Memory LOD selection
names — NOT `box_placing_*` — and rely on the Geometry LOD bbox. So this rule fires only
for items without a proper Geometry LOD or with broken `GetCollisionBox()` data.

## 8. Incomplete Component01 Coverage

`Component01` must include ALL vertices AND ALL faces of the Geometry LOD with weight=1.
Partial coverage means partial collision — some faces won't register raycasts.

## 9. Non-Watertight Collision Mesh

The Geometry LOD mesh must be closed (watertight) — every edge shared by exactly 2 faces.
Open meshes (with boundary edges/holes) cause unreliable collision where raycasts can
pass through gaps.

## 10. Missing Surface/Material Assignment on Collision LODs (CRITICAL)

Every face in the collision LODs (Geometry / GeoPhys / FireGeometry / ViewGeometry /
HitPoints) MUST have a `material` assigned, pointing to a penetration `.rvmat` that in
turn references a `.bisurf` file. Without this assignment, the engine raycasts hit the
geometry but cannot resolve a surface to consult — bullets pass through, footstep sound
is missing, and action cursor may not register.

Vanilla items always ship this — verifiable via `strings <p3d> | grep penetration`:

| Vanilla object   | Penetration material assigned             |
|------------------|-------------------------------------------|
| `55galdrum`      | `dz\data\data\penetration\metalplate.rvmat` + `metalPlate.bisurf` |
| `wooden_case`    | `dz\data\data\penetration\wood_desk.rvmat` + `wood_desk.bisurf` |
| `sea_chest`      | `dz\data\data\penetration\wood_desk.rvmat` + `wood_desk.bisurf` |
| `MilitaryCrate` (a6_base_storage) | `dz\data\data\penetration\plastic.rvmat` + `plastic.bisurf` |

Detection (py3d):

```python
for lod in p.lods:
    if lod.resolution in collision_lod_ranges:
        for face in lod.faces:
            assert (face.material or '') != '', f"face missing material in {lod_label}"
```

Fix: in Object Builder OR programmatically via py3d, set `face.material =
"dz\\data\\data\\penetration\\<surface>.rvmat"` for every face in every collision LOD
and write back. Visual LOD keeps its complex multi-stage `.rvmat` (e.g. `wooden_case.rvmat`)
unchanged — the penetration `.rvmat` is a SEPARATE simpler material used only by
collision LODs. Symptoms persist after binarization (ODOL preserves the empty
material), so this can be missed until in-game ballistic test.

---

## Common Blender Export Pitfalls

1. **Z-up → Y-up flips collision winding but not visual** — always verify Geometry LOD
   normals independently from Visual LOD
2. **Blender Geometry LOD may inherit `class=house`** from Object Builder templates
3. **py3d read-write cycles** preserve validity but change file size (~800 bytes per
   property change). This is normal.
4. **Addon Builder binarizes MLOD → ODOL** — all MLOD issues persist into builds
5. **Named selections are case-sensitive** in MLOD format. `Component01` ≠ `component01`
6. **Memory LOD must have zero faces** — only single-vertex points. Faces in Memory LOD
   may confuse the engine.
7. **Animation axis points must be in the SAME named selection** — both points of
   `flag_mast_axis` must be in one selection, not split across two.

---

## Script-Side Gotchas

These aren't P3D issues but commonly co-occur during debugging:

- `IsTakeable()` MUST return `true` for `ActionManagerClient` to include the entity
  in the action targeting pipeline. Use `CanPutInCargo()=false` +
  `CanPutIntoHands()=false` + `RemoveAction(ActionTakeItem)` for non-pickup items.
- `SetFullyRaised()` in group creation → flags start at progress=1.0 → only
  `LowerFlag` appears initially, not `RaiseFlag` (checks `< 1.0`).
- SyncVar timing vs RPC cache timing can deadlock ActionConditions.
- `autocenter=0` on FlagKit (handheld) causes it to float when dropped — only set
  on placed objects, not kits.
