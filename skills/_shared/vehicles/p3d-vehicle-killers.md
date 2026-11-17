# Vehicle model killers: mass, wheel clearance, crew and the vertex ceiling

Vehicle checks that extend the P3D killers in `skills/dayz-p3d-audit/references/p3d-killers.md`: mass tagged in the wrong LOD, wheel-well clearance, crew seat components, crew proxy triangles, and a vertex ceiling check that counts the wrong thing.

> Status: field notes measured on third-party mods, each named in its entry (SUB_BRZ, SUB_WRXSTI, MercedesAMGLF, LFQuad, LFQuad2, LFQuad3, Arma2Quad, LFHeli). Those measurements were not repeated here. A citation written with its full `P:\` path was opened on the vanilla data of this repo. A citation without `P:\` keeps the line number the note was written with, for the DayZ build that entry names, and is not yet checked on `P:\`: Grep for the symbol before relying on the number. Where they were opened, the `carscript.c` numbers matched this repo's `P:\` (a 1.30 build), the `transport.c` numbers sat 3 to 9 lines lower than written, and the `DZ\vehicles\wheeled\config.cpp` numbers differed. Tags such as SP-205 or LL-244 are the notes' own lesson numbers. Paths such as `<vehicle-import>\...` or `SUB_BRZ_dev\...` point into those mods' work folders, which are not part of this repo. "Invariant N", "preflight #N" and "#N" all mean the numbered invariants; `skills/dayz-vehicles/SKILL.md` lists which file holds each number.

> The audit script these notes were written against is the source pack's copy of `audit_p3d.py`. Statements about what that script checks ("not automated", "patched 2026-07-06") describe that copy; read `skills/dayz-p3d-audit/SKILL.md` for what the script in this repo checks. The mass, clearance and crew snippets below are run by hand.

## Vanilla anchors checked on `P:\`

- `CrewPositionIndex` resolves the crew seat from the component a get-in raycast hits (`P:\scripts\3_game\vehicles\transport.c:179`), which is why each seat needs a component of its own.

## #Mass# must live only in Geometry LOD (added 2026-06-02)

**Origin**: LFQuad N1.5 closed 2026-06-02 (handoff `30_Sessions/2026-06-02-LFQuad-placement-fix-firegeo-mass-CLOSED.md`). A spurious `#Mass#` (all values at 0) in LFQuad FireGeo LOD caused AddonBuilder/binarize to bake mass of THAT LOD → deployed ODOL with `CoM=(0,0,0)` and inertia 0. `ECE_PLACE_ON_SURFACE` placed vehicle at height of CoM = 0 → spawn 0.48 m underground → ejection.

### MANUAL check (mass-only-geometry) — NOT automated in audit_p3d.py

(Verified 2026-07-06: no mass-related check codes in `audit_p3d.py` nor in py3d `validate()` — the only `mass` hits in the fork are the `#Mass#` tagg reader/writer and the round-trip verify. Run the reference snippet below manually.)

Per-LOD validation: iterate ALL LODs of `.p3d` (Visual <1000, Geometry 1e13, Memory 1e15, LandContact 2e15, ViewGeo 6e15, FireGeo 7e15, Shadow) and check:

- `Geometry LOD` (res 1e13): MUST have `#Mass#` tagg with non-zero values and `lod.mass != None`.
- **ALL other LODs**: MUST NOT have `#Mass#` tagg. If they do (even with all 0s), severity **CRITICAL**.

Check failure message (FireGeo):
> *`FireGeometry LOD (res 7e15) contains a `#Mass#` tagg with N points. AddonBuilder/binarize will bake the mass of THIS LOD (not the Geometry LOD), producing CoM=(0,0,0) and inv_inertia=0 in the deployed ODOL → ECE_PLACE_ON_SURFACE will spawn the vehicle below ground. FIX: clear the mass from this LOD (set `point.mass = None` in the assemble, not `0.0`). py3d emits `#Mass#` if ANY point.mass is not None.*`

### py3d gotcha (subtle)

py3d **emits `#Mass#` tagg if ANY `point.mass` of LOD is ≠ None**, even if exactly `0.0`. That is why `point.mass = 0.0` leaves tagg with zeroes → binarize uses it → CoM=0. Correct way in non-Geometry LODs is `point.mass = None` (Python None, not `0.0`).

### Headless detection (without touching model)

```python
import py3d  # py3d.P3D(f) is the reader; py3d.read_p3d does not exist
with open(path, "rb") as f:
    m = py3d.P3D(f)
for lod in m.lods:
    if lod.resolution != 1e13:  # Anything but Geometry
        has_mass_tagg = any(
            p.mass is not None for p in (lod.points if hasattr(lod, "points") else [])
        )
        if has_mass_tagg:
            print(f"CRITICAL: LOD res={lod.resolution:.0e} has #Mass# tagg (must be Geometry-only)")
```

### Headless fix tool

For .p3d already assembled with bug, see `LFQuad_dev/tools/fix_firegeo_mass.py` (LFQuad-specific but pattern generalizes: load p3d, iterate LOD ≠ Geometry, set `point.mass = None`, rewrite). Post-fix verification: `binarize.exe -always -addon=<dir> <src> <dst> <wildcard>` and read ODOL `ModelInfo CoM` (must be ≠ (0,0,0)).

### Cross-ref
LL-079 (LOD bisection isolated the bug), LL-080 (the durable lesson), R26 (verifiable criteria), R35.1 (bisection before trial-and-error).

---

## Wheel-well clearance: measure against wheel RADIUS, not against HUB (added 2026-06-02, SP-024)

**Origin**: LFQuad session 2026-06-01 (handoff `30_Sessions/2026-06-01-LFQuad-spawn-launch-rootcause.md`, PHASE 2). R21 AC-7 of ROUND-2 bake validated "hubs outside hull" using 8-point hub boxes. But actual wheel (radius 0.34) penetrated chassis: min 0.16-0.19 m from wheel center to chassis. PhysX-depenetration ejected vehicle; Croco with 0.43-0.46 m clearance sits clean.

### Added check (wheel-well radius-aware)

For each wheel of the model (`wheel_*_*` proxy):

1. Read effective radius from config: `wheel_radius` of `class Wheels { ... }` or from wheel `.p3d` (cylinder BoundingBox.Y/2).
2. Compute `min_distance(chassis_geometry_hull, wheel_proxy_center)` with py3d (project proxy center onto chassis Geometry LOD hull).
3. If `min_distance < wheel_radius` → **CRITICAL**: wheel collider penetrates chassis → PhysX-depenetration will eject vehicle on spawn.
4. If `min_distance < wheel_radius * 1.20` → **WARNING**: minimal margin (vibration / intermittent contact). Croco-equivalent is ~1.27 ratio.

Check failure message:
> *`Wheel '<wheel_proxy_name>': chassis-to-wheel-center distance = X.XX m < wheel_radius (Y.YY m). PhysX will treat this as self-penetration on spawn and eject the vehicle. FIX: reshape the chassis Geometry LOD to open wheel-wells (target clearance ≥ wheel_radius * 1.25-1.30, Croco-parity). NOT a hub-vs-hull check — must measure against the wheel volume (cylinder of `wheel_radius`).*`

### Anti-pattern caught

The "hubs outside hull" audit measures against the **hub box** (8 small vertices), which passes even when the **full wheel** (effective radius cylinder) penetrates. It is a reproducible false PASS on any vehicle where hub is centered but wheel-well is narrow.

### Cross-ref
LL-082 (the durable lesson), `vehicle-structural-parity.md` Addendum 2026-05-26/29, dayz-model-pipeline wheel rigging section.

---

## Crew check (get-in / co-driver) (added 2026-06-05)

Two new checks for any vehicle that declares a `Crew` (driver + co-driver / passengers).
Both are silent in-game (no RPT error) and cost days of churn when missed. Origin:
LFQuad 2026-06-05 (~7 days of churn diagnosing exactly these two).

### Check A — `seat_driver` / `seat_codriver` spread across the collision grid

Flag (probable broken get-in / co-driver never appears) if, in the **ViewGeo LOD**, the
selections `seat_driver` / `seat_codriver` are **spread over more than 1-2 components**.
Each seat should live in its **own dedicated component** (the Croco pattern). The engine
resolves which seat a get-in raycast hit via `CrewPositionIndex(component)`
(`P:\scripts\3_game\vehicles\transport.c:179`) on the component the raycast strikes. If seats are smeared over the
collision grid, the crew components are chaotic and the co-driver position never resolves.

### Check B — crew proxies are 90/45/45 isosceles triangles

Flag (player sits sideways / rotates on get-in) if the `crewdriver` / `crewcodriver`
proxies are isosceles 90/45/45 triangles → ambiguous angle-sort frame. They must be
**canonical** (three distinct angles). Cross-ref the vehicle crew proxy section of the
dayz-proxy-align skill for the frame convention (+Y → vehicle forward) and the canonical-triangle fix.

---

## Vertex-ceiling flag counts face-indices, not resolved vertices — FALSE POSITIVE (added 2026-06-24)

The DX9 16-bit ceiling flag (`Visual LOD0 over the … vertex ceiling (points=…, face-indices=… > 65536)`)
compares the **face-index count** (`faces × 3`) against 65536. That is NOT the real limit. The DX9 ceiling
is on the number of **resolved unique vertices** (distinct `point_index × normal_index × uv`) per LOD —
indices may far exceed 65536 as long as the unique vertex set does not. A dense visual LOD routinely has
> 65536 face-indices while resolving to far fewer unique vertices, so this fires a **false CRITICAL** on
models that load and render fine.

VERIFIED 2026-06-24 (SUB_BRZ): the audit flagged Visual LOD0 (face-indices 96585 > 65536) as over the
ceiling, but the resolved unique vertices = **22143**, well under 65535 — the body loaded and rendered. The
error it was investigated under (vehicle won't spawn) was UNRELATED (crew/wheel geometry rejection).

**Correct check** (resolved-vertex count, not face-index count):
```python
res = set()
for f in lod.faces:
    for v in f.vertices:
        res.add((v.point_index, v.normal_index, v.uv))
if len(res) > 65535:
    flag_critical(f"LOD resolves to {len(res)} unique vertices > 65535 (DX9 16-bit ceiling)")
```
Cross-ref the project memory dayz-binarize-vertex-limit ("limit of resolved point×normal×uv vertices per
LOD"). **Patched 2026-07-06**: `check_lod0_vertex_budget` in `audit_p3d.py` now computes the resolved-vertex
count directly — CRITICAL only when resolved unique vertices > 65535; raw point/face-index counts over 65536
emit a WARNING that includes the resolved count.

> Origin: SUB_BRZ Phase 4 in-game debug 2026-06-24 (false-positive surfaced while diagnosing a non-spawning
> vehicle). The real blocker was crew/wheel geometry rejection — root cause OPEN. The addendum
> "FIRST IN-GAME SPAWN RESULT" lives in `rip-import.md` of this pack.
>
