# Vehicle model killers: mass, wheel clearance, crew and the vertex ceiling

Vehicle checks that extend the P3D killers in `skills/dayz-p3d-audit/references/p3d-killers.md`: mass tagged in the wrong LOD, wheel-well clearance, crew seat components, crew proxy triangles, and a vertex ceiling check that counts the wrong thing.

> Status: the in-game results below were measured on mod vehicles (two quad bikes, one of them a working control, and an imported sports car), not on vanilla ones; they are third-party mod behaviour, not vanilla. A citation written with its full `P:\` path was opened on the vanilla data on `P:\` (a 1.30 build). What `audit_p3d.py` checks is described in `skills/dayz-p3d-audit/SKILL.md`, and its vehicle checks and killers 11 to 13 in `skills/dayz-p3d-audit/references/vehicle-checks.md`. The clearance and crew checks below are run by hand.

Related file in this pack: `binarize-vertex-budget.md` (the measured vertex ceiling of `binarize`, which replaces any fixed ceiling named below).

## Vanilla anchors checked on `P:\`

- `CrewPositionIndex` resolves the crew seat from the component a get-in raycast hits (`P:\scripts\3_game\vehicles\transport.c:179`), which is why each seat needs a component of its own.

## `#Mass#` must live only in the Geometry LOD

A `#Mass#` tagg in any LOD other than Geometry is baked instead of the Geometry mass, and the vehicle spawns below ground and is ejected. This file holds the check and the repair; the measured quad bike case (the baked centre of mass, the spawn depth and the LOD bisection) is in `vehicle-structural-parity.md`, section "2026-06-02 — Spawn-launch root cause CORRECTED".

### The check

Go through every LOD of the `.p3d` (Visual under 1000, Shadow, Geometry 1e13, Memory 1e15, LandContact 2e15, ViewGeo 6e15, FireGeo 7e15):

- The Geometry LOD (resolution 1e13) must have a `#Mass#` tagg with non-zero values, and `lod.mass` must not be `None`.
- Every other LOD must have no `#Mass#` tagg, even one that holds only zeroes. One there is CRITICAL.

The DayZ fork of py3d in `scripts/tools/py3d` reports a `#Mass#` tagg outside the Geometry LOD as `ERR_MASS_ONLY_GEOMETRY` from `P3D.validate()`, and `audit_p3d.py` prints that finding as CRITICAL when the fork is in use (`skills/dayz-p3d-audit/references/vehicle-checks.md`). With any other py3d, run the snippet below by hand.

A failure message that says what to do:

> `FireGeometry LOD (res 7e15) contains a #Mass# tagg with N points. AddonBuilder/binarize will bake the mass of THIS LOD (not the Geometry LOD), producing CoM=(0,0,0) and inv_inertia=0 in the deployed ODOL, so ECE_PLACE_ON_SURFACE will spawn the vehicle below ground. FIX: clear the mass from this LOD (set point.mass = None in the assembler, not 0.0).`

### py3d writes the tagg for a mass of `0.0`

py3d writes a `#Mass#` tagg when any `point.mass` of the LOD is not `None`, even when it is exactly `0.0`. So `point.mass = 0.0` leaves a tagg of zeroes, `binarize` uses it, and the centre of mass is 0. In a LOD that is not the Geometry LOD, set `point.mass = None` (the Python `None`, not `0.0`).

### Detecting it without touching the model

```python
import py3d  # py3d.P3D(f) is the reader; py3d.read_p3d does not exist
with open(path, "rb") as f:
    m = py3d.P3D(f)
for lod in m.lods:
    # resolution is a float32 (1e13 reads back as 9999999827968.0), so compare with a band
    if abs(lod.resolution - 1e13) >= 1e12:  # Anything but Geometry
        has_mass_tagg = any(
            p.mass is not None for p in (lod.points if hasattr(lod, "points") else [])
        )
        if has_mass_tagg:
            print(f"CRITICAL: LOD res={lod.resolution:.0e} has #Mass# tagg (must be Geometry-only)")
```

### Repairing an assembled model

Load the `.p3d`, go through every LOD that is not the Geometry LOD, set `point.mass = None` on its points, and write the file back. Verify after the fix: run `binarize.exe -always -addon=<dir> <src> <dst> <wildcard>` and read `ModelInfo CoM` in the ODOL, which must not be `(0,0,0)`.

Bisect by LOD before trying fixes one at a time: that is what found this defect.

---

## Wheel-well clearance: measure against the wheel radius, not the hub

A chassis that reaches inside the wheel radius makes the physics push the wheel collider out of the chassis on spawn, and the vehicle is ejected. This file holds the check; the measured quad bike case (the clearances of the broken model and of a working control) is in `vehicle-structural-parity.md`, section "Correction (2026-06-01) — spawn-launch is wheel-collision + placement, NOT mass/inertia".

### The check

For each wheel of the model (each `wheel_*_*` proxy):

1. Read the effective radius from config (the wheel's radius in `class Wheels { ... }`) or from the wheel `.p3d` (half the Y size of the cylinder's bounding box).
2. Compute the smallest distance from the chassis Geometry LOD hull to the wheel proxy centre with py3d (project the proxy centre onto the hull).
3. Under the wheel radius: **CRITICAL**. The wheel collider is inside the chassis and the vehicle is ejected on spawn.
4. Under 1.20 times the wheel radius: **WARNING**, a minimal margin (vibration, contact that comes and goes). A working control sat at a ratio of about 1.27.

A failure message that says what to do:

> `Wheel '<wheel_proxy_name>': chassis-to-wheel-center distance = X.XX m < wheel_radius (Y.YY m). The physics treats this as self-penetration on spawn and ejects the vehicle. FIX: reshape the chassis Geometry LOD to open the wheel wells (target clearance >= wheel_radius * 1.25 to 1.30). Measure against the wheel volume (a cylinder of wheel_radius), not the hub.`

Do not replace this with a "hubs outside hull" check: it measures the 8-point hub box, so it passes when the full wheel cylinder is inside the chassis. `vehicle-structural-parity.md` covers building the wheel collider and diagnosing wheel contact, not this check.

---

## Crew checks (get-in and co-driver)

Two checks for any vehicle that declares a `Crew` (a driver plus a co-driver or passengers). Both defects are silent in game (no RPT error); on one quad bike mod, finding these two took about seven days.

### Check A: `seat_driver` and `seat_codriver` spread across the collision grid

In the ViewGeo LOD, flag the model when the selections `seat_driver` or `seat_codriver` are spread over more than one or two components: the get-in is probably broken, or the co-driver never appears. Each seat belongs in a component of its own. The engine resolves which seat a get-in raycast hit with `CrewPositionIndex(component)` (`P:\scripts\3_game\vehicles\transport.c:179`), from the component the raycast strikes. When the seats are smeared over the collision grid, the crew components are scrambled and the co-driver position never resolves.

### Check B: crew proxies that are 90/45/45 isosceles triangles

Flag the model when the `crewdriver` or `crewcodriver` proxies are isosceles 90/45/45 triangles: the frame derived by sorting the angles is ambiguous, and the player sits sideways or turns on get-in. The triangle must have three distinct angles. `skills/_shared/models/proxy-frames.md` ("Crew proxies") gives the frame convention (+Y is vehicle forward) and the fix, and the proxy editor of the dayz-model-tools skill rewrites the triangle.

---

## A vertex ceiling check that counts face corners gives a false positive

A ceiling check that compares the face corner count (`faces × 3`) with 65536 is wrong. The 16-bit ceiling is on the number of resolved unique vertices per LOD, the distinct `(point, normal, uv)` triples; the corner count may be far over 65536 as long as the set of unique vertices is not. A dense visual LOD often has more than 65536 face corners and resolves to far fewer vertices, so that check reports a false CRITICAL on models that load and render.

Measured on an imported sports car: Visual LOD0 had 96,585 face corners and resolved to 22,143 unique vertices, well under 65535, and the body loaded and rendered. The defect being chased at the time (the vehicle would not spawn) was unrelated: the engine rejected the crew and wheel geometry. `rip-import.md` records that first in-game spawn.

The correct count:

```python
res = set()
for f in lod.faces:
    for v in f.vertices:
        res.add((v.point_index, v.normal_index, tuple(v.uv)))
if len(res) > 65535:
    flag_critical(f"LOD resolves to {len(res)} unique vertices > 65535 (16-bit ceiling)")
```

`check_lod0_vertex_budget` in `skills/dayz-p3d-audit/scripts/audit_p3d.py` counts this way: CRITICAL only when the resolved unique vertices exceed 65535, and a WARNING that names the resolved count when the raw point or face corner counts exceed 65536. The number of resolved vertices a model can carry is itself measured, not fixed: see `binarize-vertex-budget.md`.
