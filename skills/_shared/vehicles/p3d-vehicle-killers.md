# Vehicle model killers

Which vehicle model faults stop a car spawning or seating, and how to check each one: mass in the wrong LOD, wheel well clearance, crew seat components, crew proxy triangles, and a vertex limit check that counts the wrong thing. They add to the general model killers in `skills/dayz-p3d-audit/references/p3d-killers.md`; `/dayz-p3d-audit` runs some of them (`skills/dayz-p3d-audit/references/vehicle-checks.md`), and the clearance and crew checks are run by hand. Results were measured on mod vehicles: two quad bikes, one a working control, and an imported sports car.

## `#Mass#` only in the Geometry LOD

A `#Mass#` tag in any LOD other than Geometry is baked instead of the Geometry mass, and the vehicle spawns below ground and is thrown out. The quad bike case that showed it is in `vehicle-structural-parity.md`.

Go through every LOD: visual (below 1000), Shadow, Geometry (1e13), Memory (1e15), LandContact (2e15), View Geometry (6e15) and Fire Geometry (7e15).

- The Geometry LOD must have a `#Mass#` tag with non-zero values, and `lod.mass` must not be `None`.
- No other LOD may have a `#Mass#` tag, even one holding only zeroes.

The py3d build in `scripts/tools/py3d` reports a tag outside the Geometry LOD as `ERR_MASS_ONLY_GEOMETRY` from `P3D.validate()`, and `audit_p3d.py` prints it as CRITICAL when that build is in use. With any other py3d, run the snippet below.

A useful failure message: "Fire Geometry LOD (res 7e15) has a `#Mass#` tag with N points. Binarize bakes the mass of this LOD, not the Geometry LOD, giving a centre of mass of (0,0,0) and zero inverse inertia, so `ECE_PLACE_ON_SURFACE` spawns the vehicle below ground. Clear the mass from this LOD (set `point.mass = None`, not `0.0`)."

py3d writes the tag whenever any `point.mass` in the LOD is not `None`, even `0.0`. So `point.mass = 0.0` leaves a tag of zeroes, binarize uses it, and the centre of mass is 0. Outside the Geometry LOD set `point.mass = None`.

```python
import py3d  # py3d.P3D(f) is the reader; there is no py3d.read_p3d
with open(path, "rb") as f:
    m = py3d.P3D(f)
for lod in m.lods:
    # resolution is a float32 (1e13 reads back as 9999999827968.0), so compare with a band
    if abs(lod.resolution - 1e13) >= 1e12:  # every LOD except Geometry
        has_mass_tag = any(p.mass is not None for p in getattr(lod, "points", []))
        if has_mass_tag:
            print(f"CRITICAL: LOD res={lod.resolution:.0e} has a #Mass# tag (Geometry only)")
```

To repair an assembled model, load it, set `point.mass = None` on every point of every LOD except Geometry, and write it back. Then run `binarize.exe -always -addon=<dir> <src> <dst> <wildcard>` and read `ModelInfo CoM` in the binarized model; it must not be `(0,0,0)`. When a spawn fault has no obvious cause, bisect by LOD before trying fixes one at a time.

## Wheel well clearance

A chassis that reaches inside the wheel radius makes the physics push the wheel collider out on spawn, and the vehicle is thrown. For each `wheel_*_*` proxy:

1. Read the wheel radius from the config (`class Wheels`) or from the wheel `.p3d` (half the Y size of its bounding box).
2. Compute with py3d the smallest distance from the chassis Geometry LOD hull to the wheel proxy centre.
3. Below the wheel radius: critical. The wheel collider is inside the chassis.
4. Below 1.20 times the radius: a warning, since the margin is thin and contact comes and goes. A working control sat at about 1.27.

A useful failure message: "Wheel `<name>`: chassis to wheel centre distance X.XX m is less than the wheel radius Y.YY m. The physics treats this as the vehicle inside itself and throws it on spawn. Open the wheel wells in the Geometry LOD to at least 1.25 to 1.30 times the radius, measured against the wheel cylinder, not the hub."

Do not replace this with a check that the hubs sit outside the hull: it measures the eight point hub box, so it passes while the whole wheel cylinder is inside the chassis.

## Crew seats and crew proxies

Two checks for any vehicle with a `Crew`. Both faults are silent in game, with no RPT error.

- Seat components. In the View Geometry LOD, flag the model when `seat_driver` or `seat_codriver` is spread over more than one or two components. Each seat belongs in a component of its own, because the engine picks the seat from the component the get-in ray hits with `CrewPositionIndex` (`P:\scripts\3_game\vehicles\transport.c:182`). Seats smeared over the collision grid scramble the crew components, so get-in breaks or the co-driver seat never resolves.
- Proxy triangles. Flag a `crewdriver` or `crewcodriver` proxy that is an isosceles 90, 45, 45 triangle: the frame taken from sorting its angles is ambiguous, and the player sits sideways or turns on get-in. The triangle needs three different angles. `_shared/models/proxy-frames.md` (section "Crew proxies") gives the frame convention, +Y along the vehicle's forward direction, and the fix; the proxy editor of `skills/dayz-model-tools/` rewrites the triangle.

## A vertex limit check that counts corners

A check that compares the face corner count (`faces * 3`) with 65536 is wrong. The 16-bit limit is on resolved unique vertices per LOD, the distinct `(point, normal, uv)` triples. A dense visual LOD often has more than 65536 corners and far fewer vertices, so the corner check reports a false critical on models that load. Measured on an imported sports car: visual LOD 0 had 96,585 corners and 22,143 unique vertices, and the body loaded and rendered; the spawn fault was elsewhere, in the crew and wheel geometry (`rip-import.md`).

The correct count:

```python
res = set()
for f in lod.faces:
    for v in f.vertices:
        res.add((v.point_index, v.normal_index, tuple(v.uv)))
if len(res) > 65535:
    flag_critical(f"LOD resolves to {len(res)} unique vertices > 65535 (16-bit limit)")
```

`check_lod0_vertex_budget` in `skills/dayz-p3d-audit/scripts/audit_p3d.py` counts this way: critical only when resolved unique vertices pass 65535, and a warning naming the resolved count when the raw point or corner count passes 65536. How many resolved vertices a model can really carry is measured per model; see `binarize-vertex-budget.md`.
