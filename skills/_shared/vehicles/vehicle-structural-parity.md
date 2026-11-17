# Vehicle structural parity checklist

The parity-first method: debinarize a vanilla car once, diff your model against it, and build every missing LOD, selection, crew proxy, wheel hub and script override in one pass, with the dated addenda that corrected the method as it was used on real vehicles.

> Status: third-party mod behaviour and field measurements, not vanilla, unless a line cites `P:\`. The measurements were taken on the mod vehicles named in each entry (LFQuad, SUB_BRZ, MercedesAMGLF, WRX STI), on a working third-party quadbike mod (called "the reference quad" below), on a shipped third-party car mod, and on an example 4x4 built to the documented method; they are not checked on `P:\`. A citation written with its full `P:\` path was opened on the vanilla data (a 1.30 build). A citation without `P:\` names a file under `P:\scripts` or `P:\DZ\vehicles\wheeled`: the `carscript.c`, `car.c`, `transport.c`, `civiliansedan.c`, `offroadhatchback.c`, `van_01.c`, `actiongetintransport.c` and `dayzphysics.c` numbers were opened there and match. Values read from the binarized vanilla models were read with an external ODOL reader and are not checked by the repo tests. `[DOC]` marks a rule documented by Bohemia Interactive.

The addenda are in the order they were written, and later ones correct earlier ones. Read a "Correction" before acting on the addendum it names; the last three sections (occluder membership, LOD frame parity, ground contact) refine the sections they name.

## Vanilla anchors checked on `P:\`

- The reference model is `P:\DZ\vehicles\wheeled\civiliansedan\civiliansedan.p3d`. It is binarized (ODOL), which py3d cannot read, so the values quoted from it were read with an external ODOL reader and are not checked by the repo tests.
- The crew proxy models are `P:\DZ\vehicles\wheeled\proxies\crew_driver.p3d` and `P:\DZ\vehicles\wheeled\proxies\crew_cargo.p3d`.
- `CrewPositionIndex` is declared at `P:\scripts\3_game\vehicles\transport.c:179`.
- The base `CrewCanGetThrough`, which returns false in a normal build, is at `P:\scripts\3_game\vehicles\transport.c:724`.
- The base `GetSeatAnimationType`, which only raises an error, is at `P:\scripts\3_game\vehicles\transport.c:682`.
- The get-in condition reads `CrewPositionIndex` at `P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetintransport.c:46`.
- It reads `CrewCanGetThrough` at `P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetintransport.c:54`.
- `CanReachSeatFromDoors` is at `P:\scripts\4_world\entities\vehicles\carscript.c:2177`.
- `GetDoorConditionPointFromSelection` is at `P:\scripts\4_world\entities\vehicles\carscript.c:2141`.
- `WheelHasContact` is declared at `P:\scripts\3_game\vehicles\car.c:286`.
- `WheelCountPresent` is declared at `P:\scripts\3_game\vehicles\car.c:348`.
- The sedan's `hiddenSelections` list starts at `P:\DZ\vehicles\wheeled\config.cpp:5138`.

## Why parity first

> Generating a wheeled vehicle from scratch (procedural / Blender-to-DayZ) reveals the structural
> pieces a real DayZ vehicle has ONE ERROR AT A TIME in-game. To avoid that whack-a-mole,
> debinarize a vanilla vehicle ONCE and diff against it BEFORE baking.
> Reference: civiliansedan (`DZ\vehicles\wheeled\civiliansedan\civiliansedan.p3d`, ODOL version 56 in the header of the copy on `P:\`, debinarizable).

## Parity-first method (do this BEFORE baking a vehicle)

1. Debinarize the civiliansedan (ODOL v56 on `P:\`) with an external ODOL→MLOD converter whose ODOL reader handles v56.
2. Enumerate every LOD (resolution + `named_selections` + `proxies`) with the ODOL reader.
3. Diff against your model's read-back (py3d) and your `config.cpp`.
4. Build ALL missing pieces in one pass — do not discover them error-by-error in-game.

## Required LOD set for a functional wheeled vehicle

The civiliansedan ships 10 LODs: 6 visual + the special LODs below. A from-scratch vehicle needs at
minimum Geometry + Memory + ViewGeometry (if it has crew) + FireGeometry (if it takes damage).

| LOD | resolution | carries | needed when |
|---|---|---|---|
| Geometry | 1.0e13 | collision hull as `componentNN` + `wheel_X_X_damper_land` (wheel hubs as FACES, not only memory) + `seat_driver`/`seat_codriver` + door selections | always |
| Memory | 1.0e15 | crew/pos points, wheel axes, light points, particle points, `seat_con_*` | always |
| ViewGeometry | 6.0e15 | CREW PROXIES (`crewdriver`/`crewcodriver`/`crewcargoN`) as proxy objects + occlusion components + seats + wheels | if config declares `class Crew` |
| FireGeometry | 7.0e15 | damage-zone components + crew proxies + wheels (ballistic + damage) | if vehicle takes localized damage |
| LandContact | 2.0e15 | ground contact points | never on a modern `Car` — the civiliansedan has NO LandContact LOD (see "Modern `Car` ground-contact correction" at the end). |

## Crew proxies (the #1 post-spawn gotcha)

`config.cpp` `class Crew` → `Driver.proxyPos="crewdriver"`, `CoDriver.proxyPos="crewcodriver"`. The
engine then looks for crew PROXY OBJECTS named crewdriver/crewcodriver in the **ViewGeometry LOD** (and
FireGeometry). Memory points named crewdriver are NOT sufficient.

Symptom if missing: `PHYSICS (E): Proxy with bone name 'crewdriver' was not found in view geometry level
of model` (the vehicle still spawns, but get-in/crew is broken).

Vanilla proxy models: `\dz\vehicles\wheeled\proxies\crew_driver.p3d` (-> crewdriver) and
`\dz\vehicles\wheeled\proxies\crew_cargo.p3d` (-> crewcodriver, crewcargo1, crewcargo2). Place them at the
crew memory points (`crewdriver`/`crewcodriver` / `pos_driver`/`pos_codriver`).

## Lights

- Model visual LODs: selections `light_1_1`, `light_1_2`, `light_2_1`, `light_2_2`, `light_brake`,
  `light_brake_1_2`, `light_brake_2_2`, `light_reverse_1_2`, `light_reverse_2_2`, `light_dashboard`, `light_rear`.
- Model Memory LOD: `light_left`, `light_left_dir`, `light_right`, `light_right_dir`, `light_reverse`,
  `reflector_1_1`, `reflector_2_1`.
- Config (CarScript): `hiddenSelections[]` with the light_* selections; `hiddenSelectionsMaterials[]` ->
  a lights `.rvmat`; material-switch properties `frontReflectorMatOn/Off`, `brakeReflectorMatOn/Off`,
  `ReverseReflectorMatOn/Off`, `TailReflectorMatOn/Off`, `dashboardMatOn/Off`.

Without the selections + memory points + config, headlights mount but never illuminate.

## Damage

- Config: `class DamageSystem { class GlobalHealth { healthLevels[] } }` + `class DamageZones`
  (chassis, front, back, roof, engine, fueltank, fender_1_1/1_2/2_1/2_2, windowfront, windowback).
- Model: each zone maps to a component in FireGeometry + `dmgzone_*` selections across visual/ViewGeo/FireGeo/Memory.
- Wreck (DayZ cars): handled via destruction effects / material swap rather than a dedicated Wreck class
  in `wheeled/config.cpp` — verify the exact mechanism against the reference before relying on it.

Without DamageZones + FireGeometry components there is no localized damage and no wreck.

## AnimationSources (wheel / damper / steering)

The dampers need user animation sources: config `class AnimationSources` with `damper_1_1/2_1/1_2/2_2`
as `source="user"` (`initPhase` + `animPeriod`). Without this block: `unknown animation source damper`.
Wheel rotation (`source "wheel"`) and steering (`source "direction"`) are driven by the car simulation
when `Axles -> Wheels` (`animRotation`/`animTurn`/`wheelHub`) are correct AND the wheel hubs exist as
faces in the Geometry LOD (`wheel_X_X_damper_land`). `model.cfg` defines the animation classes; the
config wires them.

## Cross-reference

- Tools: an external ODOL→MLOD converter (to debinarize the reference; not part of this repo), skill `enforce-script-reference` (config blocks),
  `dayz-animation-pipeline` (model.cfg / AnimationSources), `dayz-particles` (damage effects).
- After deploy, gate on the RPT, not on the offline diff.

---

## Addendum (2026-05-26) — Lessons from "the quad doesn't drive" debugging (LFQuad)

> Verified against civiliansedan (ODOL v54 on DayZ 1.29, not re-checked on `P:\`, whose copy is v56) (full), hatchback_02/offroadhatchback/offroad_02 (FireGeo), and
> the reference quad v53 (header only). Marked [VERIFIED] vs [HYPOTHESIS]: a divergence from the
> reference is a candidate, not a verdict; do not assert a cause without reading the mechanism.

### Vehicle that DOES NOT roll / sinks / bounces, with ENTIRE checklist present

If the vehicle spawns, steers, and makes sound but DOES NOT ROLL, SINKS, and BOUNCES, without RPT error, the
wheel PhysX simulation is not engaging. Key discriminator [VERIFIED]: "steers (steering animates) but
does not roll" = wheel recognized by config/anim but its physics (contact/suspension/rotation) blocked.

- Wheel hub CANNOT be inside the chassis convex hull [strong HYPOTHESIS]. Raycast wheel
  casts a ray downwards from hub; if it originates inside chassis collision, it auto-collides -> no
  ground contact -> no suspension (sinks) + no traction (doesn't roll). A single convex hull of entire
  body is INCORRECT: encompasses wheel space. Chassis needs wheel-wells (absent collision
  where wheels go): hull narrower than track, or multi-component with gaps. Verify offline
  that each hub remains OUTSIDE the hull and tire does not penetrate it.
- Silent failure (no RPT error) -> instrument, do not guess [PROCESS]. Temporary debug script in
  vehicle's .c logging GetWheelCount(), wheel speed vs EngineGetRPM(), server vs client,
  contact. Observe failure. Loop "one hypothesis -> one change -> one test" prohibited.
- What is NOT the cause if cloned from a working vehicle [VERIFIED]: drivetrain (engine/torque/clutch/
  gearbox/differential), scripts (child CarScript; cosmetic differences), model.cfg. "Doesn't roll" failure
  is usually model/geometry or native binding, not the cloned config/script.

### Wheel-proxies in FireGeometry [VERIFIED 4/4 vanilla]

ALL reviewed vanilla cars carry wheel proxies in their FireGeometry LOD, identical to those in
Visual LOD (sedan sedanwheel.001-005, hatchback_02, niva, offroad_02). Replicate: copy wheel-proxies
from Visual to FireGeo (3-vertex proxy face + selection proxy:path.NNN, mass 0). Note: the rule that
proxies stay out of FireGeometry applies to item-type attachments, NOT to wheels.

### Size of wheel_X_X_damper_land hub in Geometry [VERIFIED vs sedan]

SMALL convex component (~0.20x0.18x0.18, sedan), NOT a large box. A from-scratch build with boxes of
~0.40 is 2x too large and reaches almost down to the ground.

### Mass, COM, and suspension scale with the vehicle [VERIFIED vs the reference quad]

- Mass is computed from vertex weights in Geometry LOD. A real quad weighs ~1000 kg (the reference quad
  ModelInfo: mass 1061.5, COM (0, 0.474, -0.011)), NOT the ~250 default of a procedural hull. Too
  low mass -> unstable physics (bounce).
- Suspension (stiffness/compression/damping) scales with mass: DO NOT clone that of a heavy crawler
  onto a light quad (brutally stiff springs -> bounce). Clone from comparable mass.
- wheelHubRadius = radius of HUB COMPONENT (small ~0.11-0.15), NOT tire radius.
  the reference quad 0.11 (tire 0.367); sedan 0.15.
- Wheel radius vs belly clearance: wheel contact ~Y=0 and chassis underside well above (sedan
  belly clearance 0.428 m). Small wheels -> body rides too low.

### Wreck [VERIFIED sedan]

The sedan ships 3 dedicated directional wreck .p3d files
(P:\DZ\vehicles\wheeled\civiliansedan\wreck\civiliansedan_wrecked{front,back,both}.p3d). No vanilla script
under P:\scripts and no vehicle config.cpp under P:\DZ references them, so they ship unused; there is no
vanilla wreck spawn to copy. Empty healthLevels {} is valid.

### Tools / reference parity [VERIFIED]

- The reference quad (v53): NOT full-debinarizable (desync in EmbeddedMaterial v53), but header/ModelInfo
  YES (mass, COM, geometry_center, LOD resolutions) by monkeypatching LOD.read to skip geometry
  parsing. For its real geometry -> Object Builder (handles v53). (Stale: see Correction 2026-05-30c.)
- The debinarizer INVERTS winding (ODOL->MLOD) -> a debinarized MLOD is NOT a reliable winding
  reference. For collision winding use Check C (cross vs component centroid).
- Working quad LOD set (the reference quad): visual 0-6, View Pilot 1100, Geometry 1e13, Memory 1e15, ViewGeo
  6e15, FireGeo 7e15 (without LandContact).


---

## Addendum (2026-05-29) — Wheel proxy `.p3d` Memory anatomy [VERIFIED vs the reference quad]

> This section covers the `.p3d` of the **wheel attachment** (the separate file referenced
> from `CfgNonAIVehicles` `ProxyVehiclePart` and tied to the body via `inventorySlot`), not the
> body. A gap here gave LFQuad a permanent `contact=0` and a divergent bounce.

### The wheel proxy `.p3d` is NOT "a wheel with visual LODs". PhysX uses its Memory LOD to build the wheel collider.

Without the 5 canonical selections in the wheel proxy's Memory LOD, **PhysX does not know the size
of the wheel collider** and defaults to the proxy's Geometry LOD (typically an 8v 0.20³
proxy cube generated by dayz-model-pipeline when creating from scratch). The effective
wheel collider ends up the size of a tiny cube instead of a wheel Ø(2×radius).
Symptom: `wheelCount=N wheelPresent=N` (wheels attached OK) but `contact=0` always after
first in-game frame (wheel→ground raycast only reaches ±0.10 m below hub anchor
instead of ±radius). Result: body falls freely until chassis Geometry collides,
cumulative divergent bounce, eventually `speedo` exceeds finite range and engine
executes `Will delete object with !finite or outside world coords`.

### The 5 canonical mem-points (measured on the reference quad's wheel `.p3d`, ODOL v53)

Each is a `Selection` of 1 unique point in the Memory LOD (resolution 1e15). All follow
the reference quad's convention (Y vertical/radial, X axial/width, Z radial with intentional
inversion between min and max).

| Selection | Reference quad value (front wheel) | Meaning | Scaling to custom wheel |
|---|---|---|---|
| `ce_center` | `(−1e-05, 0.0, 0.0)` ≈ (0,0,0) | collider center | always origin |
| `ce_radius` | `(3e-05, 0.37679, 0.40015)` | radius marker (Y) + width marker (Z) | `(0, wheel_radius, ce_radius_Z)` — preserve the reference Z/Y ratio (~1.062×Y) |
| `boundingbox_min` | `(−0.19095, −0.3816, +0.38558)` | min corner with **positive Z** | `(−width/2, −wheel_radius, +wheel_radius)` |
| `boundingbox_max` | `(+0.20446, +0.39014, −0.38393)` | max corner with **negative Z** | `(+width/2, +wheel_radius, −wheel_radius)` |
| `invview` | `(−0.23026, −1e-05, 0.0)` | negative X offset (likely for view inversion) | preserve offset relative to axial width |

**Non-standard quirk**: `boundingbox_min.Z > boundingbox_max.Z` (Z inverted between min and max).
DO NOT normalize — it is the engine's convention for wheel proxies. Copy literally scaling Y/Z
with `factor_radial = wheel_radius / 0.38587` and X with `factor_axial = width / 0.39541`.

### How to build them with py3d 1.0.0

All 6 quirks of py3d 1.0.0 apply (constructor with args, int weight, rebind after grow,
lowercase matname, overwrite-in-place for `ce_center` if it already exists, +Z/-Z frame if
wheel comes from Blender). See `skills/dayz-animation-pipeline/references/py3d-1.0.0-quirks.md` of the dayz-animation-pipeline
skill and `skills/_shared/py3d-mlod-notes.md`. DO NOT duplicate the pattern here — the animation pipeline skill
is the canonical place for writing Memory LODs via py3d.

### Acceptance criterion for wheel proxies generated from scratch

Before declaring a wheel proxy "ready", verify with py3d:

```python
mem = next(l for l in p3d.lods if abs(l.resolution - 1e15) < 1e12)
required = {"ce_center", "ce_radius", "boundingbox_min", "boundingbox_max", "invview"}
missing = required - set(mem.selections.keys())
assert not missing, f"wheel proxy Memory incomplete: missing {missing}"
```

This must be part of the post-bake round-trip for any wheel proxy, as a required anatomical
check and not as optional backlog.

### The audit covers it (cross-ref)

`dayz-p3d-audit` Killer 11 (`skills/dayz-p3d-audit/references/vehicle-checks.md`) covers the case.
If an audit of a wheel proxy returns PASS with only `ce_center`, the check did not cover this dimension.


---

## Addendum (2026-05-30) — Canonical car-build invariants [build rules documented by Bohemia; cause analysis corrected below]

> What it resolves: LFQuad shipped bouncing/launching on spawn despite 4+ iterations. This addendum
> encodes the canonical build method for the Geometry LOD and the mass of a DayZ car. The build rules
> stand; the claim that a monolithic Geometry causes the launch was later refuted (see the
> corrections of 2026-06-01 and 2026-06-02 below). Marks: [DOC] = documented by Bohemia Interactive
> or in the PhysX SDK documentation; [MEASURED] = measured on a reference model; [CONSENSUS] = common
> modding practice with no official documentation.

### What the engine documentation establishes

- **Geometry LOD and mass** [DOC]: per-vertex mass in the Geometry LOD gives the total mass and the
  centre of mass; wheel hubs are separate components; a wheel proxy sits in FireGeometry; the Diag
  build has an in-game vehicle debug.
- **Geometry shape** [DOC]: Geometry objects need a thickness of at least 0.5 m; parts thinner than
  15 cm do not collide at speed; Geometry components must be closed and convex, or collision does not
  work; mass distribution sets the inertia. In Object Builder, `Find Components`, `Find Non-Convexities`
  and `Component Convex Hull` check and repair this.
- **Arma 3 cars** [DOC]: a separate PhysX LOD (4e13), the centre of mass centred left-right, and
  `sprungMass` summing to the weight. DayZ differs on the PhysX LOD (see Addendum 2026-05-30b).
- **Launch mechanism (PhysX)** [DOC]: bodies created overlapping can explode, because the solver
  resolves the penetration in a single time step, which can give large velocities. The clamp on the
  depenetration velocity is not exposed to modders; the engine clamps internally, but bad geometry
  triggers it anyway. Sharp edges in a geometry impart a large moment on contact and send the
  vehicle into the air [CONSENSUS, matches the PhysX mechanism].

### The build invariant of the Geometry LOD (what was missing)

**The Geometry of a working car is a COMPOSITE of several closed convex components, NEVER a
monolithic hull.** [DOC] The Geometry LOD checklist: convex components; named property `autocenter`
with value `0`; a simple shape with no unnecessary components; **mass applied on ALL
components**; wheel hubs present with their selections assigned; centre of mass checked. Every
component's vertices carry weight, and the total mass of the vehicle and its centre of mass are
computed from those weights. (The reference quad = **23 chassis components + 4 hubs**; LFQuad shipped with **1**
`component01` hoarding ~90% of mass — anti-pattern.)

Consequences of building it as a monolith, as first diagnosed on LFQuad's bounce (both legs were
later refuted as the launch cause; see the corrections below):
1. **Trigger (shape):** a single tightly fitted convex hull with sharp edges, upon waking rigid body on
   spawn, overlaps terrain/hubs → PhysX resolves penetration in one step → huge impulse → launch.
2. **Amplifier (inertia):** mass concentrated in 1 component → pathological/low inertia tensor
   (LFQuad Izz **128.5** = 37% of the reference quad's **350.7** [MEASURED]) → any impulse spins/flips it →
   re-penetrates → gains energy → `Will delete object with !finite or outside world coords`.

### Canonical checklist (each point offline-verifiable; add to the round-trip)

| # | Rule | Basis | Check |
|---|---|---|---|
| 1 | Geometry = multiple **closed** convex `componentNN` (no monolith) | [DOC] | clean `Find Non-Convexities` + `Find Non-Closed`; component count > 1 for the chassis |
| 2 | **Mass on ALL components** (incl. 4 hubs), not concentrated in one | [DOC] | sum weight per component; none at 0; none >~60% of total |
| 3 | `autocenter = 0` as named property on **each** Geometry component | [DOC] | read named properties per component |
| 4 | CoM **centered in X** (left-right); reasonable Y/Z, no large bias | [DOC] | `CoM.x ≈ 0`; LFQuad CoM (0, 0.513, **+0.399**) vs the reference quad (0, 0.474, −0.011) [MEASURED] → large Z bias |
| 5 | Component thickness ≥ 0.5 m (a quad is narrow: the reference quad's chassis ±0.275 = 0.55 m) | [DOC] | chassis component width ≥0.5 m away from the wheels (LFQuad at ±0.175 = 0.35 m ✗; see "Tension with item #5" below) |
| 6 | Hubs `wheel_X_X_damper_land` = real convex components with mass, NOT just face selections | [DOC] | each hub is a closed component with weight |
| 7 | Proxies (wheel/crew/doors) **NOT** in Geometry LOD (they don't animate, don't collide there) | [DOC] | Geometry without proxies; wheel-proxies yes in Visual+ViewGeo+FireGeo |
| 8 | Fire Geometry mandatory in vehicles | [DOC] | FireGeo present |
| 9 | `drown_engine` memory point defined (if missing → 0 0 0 → engine drowns at origin) | [DOC] | point present and positioned at the engine |

### Suspension: calibrated to the mass (documented formula)

[DOC] The stiffness has to hold the mass that gravity pushes down; a starting point is
`compression = stiffness / 10`, `damping = compression * 3` (then adjust). **Reference config of the
example 4x4** (AWD; only an order-of-magnitude anchor, do not copy blindly to a quad):

```cpp
class Suspension { stiffness=40000; compression=2100; damping=5400; travelMaxUp=0.10; travelMaxDown=0.06; };
wheelHubMass=15;      // KG, only applies if wheel is NOT attached
wheelHubRadius=0.284; // measured from hub component (Shift+E, Y axis), never negative
```

Comparison [MEASURED]: the reference quad's stiffness 40000–41000; **LFQuad 20000** (half), damping 9000, travelMaxUp
0.293/0.414. Documented trap: mass too LOW + stiffness copied from a heavier vehicle →
catapult. (LFQuad is NOT in that trap: its mass is correct 1061.5 and its stiffness is lower than the
reference — suspension is NOT the bounce trigger; confirmed in-game. Swapping suspension and
damping values does not cure a floating/bouncing car whose cause lies elsewhere.)

### model.cfg — `suspension_damper` pattern (resolves recurring minValue/maxValue vs offsets doubt)

[DOC] From the example 4x4's model.cfg. **`minValue=0` / `maxValue=1` fixed; actual travel is
driven by offsets** (NOT vice versa):

```cpp
class suspension_damper_1_1 {
    type="translation"; source="damper_1_1"; selection="wheel_1_1_damper";
    axis="wheel_1_1_damper_axis";
    minValue=0.0; maxValue=1.0;        // FRONT (rear uses maxValue=0.6, visual only)
    offset0=0.05;  offset1=-0.35;      // travel: +0.05 (above rest) to −0.35 (compression)
};
// config.cpp AnimationSources: class damper_1_1 { source="user"; initPhase=0.4857; animPeriod=1; }
//   initPhase sets the visual position of the damper AT REST (front ~0.486, rear ~0.400).
```

Skeleton [DOC]: front = `damper → steering → wheel` (3 levels, with steering bone); rear =
`damper → wheel` (without steering bone). Damper `source` (`damper_1_1`…) matches `animDamper` in
config `Axles→Wheels` and the `AnimationSources` class.

### config.cpp — mass is NOT in config

[DOC] A working car config carries no `mass`/`sprungMass`/`centerOfMass`/`geometryClass` in config.cpp. Mass
is set ONLY via vertex weights in Geometry LOD (Object Builder, Alt+M). Do not attempt setting mass via
config in DayZ CarScript.

### Open points of this addendum

- Whether a DayZ car needs a **PhysX LOD 4e13** separate from Geometry 1e13, as Arma 3 does:
  resolved in Addendum 2026-05-30b (it does not).
- No config key carries `sprungMass` or a total mass; mass, CoM and inertia come from the Geometry
  LOD weights only.

---

## Addendum (2026-05-30b) — Per-LOD content map, memory-point catalog, proxy placement [LOD roles documented by Bohemia; catalog measured on the reference quad]

> Complement to the "Required LOD set" above and Addendum 2026-05-30 (Geometry/mass invariants).
> Here: WHAT concrete content goes into each car LOD, the full catalog of memory points, where
> proxies go per LOD, and what each LOD is for. The **config.cpp + model.cfg** portion lives in
> `vehicle-config-and-modelcfg.md` (do not duplicate).

### What goes into each car LOD

| LOD | resolution | Car content | What the LOD is for [DOC] |
|---|---|---|---|
| Resolution 0–N | 0,1,4,8 | visual mesh + wheel/crew/door proxies in EVERY visual LOD where they should appear | A proxy must be in every resolution LOD it should appear in. A visual LOD must not hold an empty named selection that an animation or the engine uses (wheels and so on); that can crash the game. |
| Geometry | 1.0e13 | closed convex `componentNN` (multi-component chassis) + hubs `wheel_X_Y_damper_land` as own components; mass per vertex → mass+CoM | Convex components. The total mass and the centre of mass are computed from the vertex weights. Wheel hubs have their own components. |
| Memory | 1.0e15 | ALL memory points (catalog below): crew pos/dir, wheel axes, damper axes, light points, `drown_engine`, dials | Named selections that define lights, vehicle entry points and control points for animations. |
| LandContact | 2.0e15 | ground contact vertices (civiliansedan has none; do not add one to a modern `Car`, see the last section) | Only the vertices that touch the ground, mainly for vehicles. Wrongly placed points make the model levitate or sink. |
| Roadway | 3.0e15 | walkable surface (roof/hood if player can stand on it) — not mandatory | Needed where a unit must stand on the model. It must not overlap the Geometry LOD, or the unit wobbles. |
| Hitpoints | 5.0e15 | one `dmgZone_*` selection for each config damage zone | Unconnected named vertices mark where the destroyable parts are (wheels, lights and so on). |
| ViewGeometry | 6.0e15 | CREW PROXIES (`crewdriver`/`crewcodriver`/`crewcargoN`) + occlusion components + seats | With no component in View or Fire Geometry the cursor cannot open the action menu. |
| FireGeometry | 7.0e15 | damage-zone components + **wheel-proxies** (identical to Visual) + crew proxies | Must hold a proxy object named after the wheel slot, so the simulation can attach a wheel and suspension at that position. |
| Shadow Volume | 1.0e4 / 1.1e4 | closed+triangulated shadow, slightly shrunk vs visual (optional) | Must be slightly smaller than the resolution LOD, or the model looks partly or fully shaded. |

Geometry rules [DOC]: Geometry objects need a thickness of at least 0.5 m to work properly · parts
thinner than 15 cm cannot collide at higher speeds · Geometry components must be closed convex
objects · validate in Object Builder with `Structure → Topology → Find Non-Closed` +
`Structure → Convexities → Find Non-Convexities` / `Component Convex Hull`.

### PhysX LOD 4e13: Arma 3 yes, DayZ no

Addendum 2026-05-30 left open whether DayZ cars have a separate PhysX LOD 4e13
next to Geometry 1e13. Resolved: that LOD is **Arma 3**. An Arma 3 car needs a 4e13 LOD of convex
components as simple as possible, holding just the main body of the car; the engine adds the wheels
later. DayZ **references** (the example 4x4, the reference quad, civiliansedan) use
**Geometry 1e13 without a separate 4e13**. → Do NOT add a 4e13 LOD to a DayZ car unless
verified in-game.

### "Flying tanks" ≠ spawn bounce

Two documented effects are easy to conflate. "Flying tanks" is specific to **cannon/turret barrels
that PROTRUDE in the PhysX LOD**: the collision of a barrel with the environment moves the tank very
violently. It is NOT spawn depenetration bounce. The spawn bounce mechanism is: PhysX resolves
interpenetration in one step → impulse, plus sharp edges [CONSENSUS]. Both are real but distinct.
(Nothing documented links spawn bounce to geometry protruding below the origin → that link remains
`[verify in-game]`.)

### Memory point catalog for a car [VERIFIED on the reference quad]

> Read from the strings of the reference quad (v53); every name below was present unless marked.
> Wheel pattern `wheel_<side>_<axle>`, side 1=left/2=right, axle 1=front/2=rear, as on vanilla:
> the truck's front axle holds `Truck_01_Wheel_1_1` and `Truck_01_Wheel_2_1`, `P:\DZ\vehicles\wheeled\config.cpp:18589` and `:18594`.

- **Crew/seats:** `pos_driver`(+`_dir`), `pos_codriver`(+`_dir`), `pos_cargo`(+`_dir`); proxies
  `crewdriver`,`crewcodriver`,`crewcargo1`,`crewcargo2`; selections `seat_driver`,`seat_codriver`,`seat_cargoN`;
  door-condition `seat_con_1_1`,`seat_con_2_1`.
- **Wheels (×4):** `wheel_X_Y_axis` (2 pts, rotation axis), `wheel_X_Y_damper` (suspension translation
  selection), `wheel_X_Y_damper_axis` (2 pts), `wheel_X_Y_damper_land` (ground contact = config
  `wheelHub`), `wheel_X_Y_steering`+`_steering_axis` (front only), `steering_hub_X_1` (front).
- **Steering/dashboard:** `steeringwheel`, `drivewheel`(+`_axis`), `mph`(+`_axis`), `rpm`(+`_axis`),
  `fuel_1`(+`_axis`), `dial_temp`(+`_axis`), `light_dashboard`.
- **Lights:** `light_1_1`,`light_2_1` (front), `light_1_2`,`light_2_2` (tail), `light_brake_1_2/2_2`,
  `light_reverse_1_2/2_2`, beam `light_left`(+`_dir`),`light_right`(+`_dir`), `reflector_1_1`,`reflector_2_1`.
- **Engine/particles:** `engine`(+`_axis`), `enginerun`,`engineshake`; `drown_engine` (critical, row 9 of the 2026-05-30 checklist);
  `ptcexhaust_*`/`ptccoolantpos` `[TBD-verify — did not appear in the reference quad's strings]`.
- **Other:** `pos center` (with space), `ce_center`/`ce_radius` (Central Economy loot), `fuelpoint`.

### Named selections per LOD (car)

- **Visual LODs:** wheels `wheel_X_Y`, suspension `wheel_X_Y_damper`, steering `wheel_X_1_steering`,
  `steeringwheel`/`drivewheel`, doors `doors_*`, seats `seat_*`, lights `light_*` (hiddenSelections),
  `color`/`base`/`special` (hiddenSelections), chassis catch-all (`zbytek`).
- **Geometry/Collision LODs:** `componentNN` (lowercase `component01` — vanilla vehicles use lowercase,
  measured via py3d on CivilianSedan and the extracted MLOD of the reference quad; lowercase also collided like
  uppercase on an item and a building in game, see "`validate()` ERR_COMPONENT_NAMING" below. The reference quad's Geometry
  has 27 components — ~30-50 suffice for sedan/hatch). Hubs `wheel_X_Y_damper_land` as own components.
- **Hitpoints LOD:** one `dmgZone_*` per config zone (`dmgZone_chassis/front/back/fender_*/engine/fuelTank/lights_*`).

### Proxies per LOD (car)

- **Wheel proxies:** in EVERY Visual LOD + ViewGeometry + FireGeometry (identical), mass 0. NOT in Geometry
  (hubs in Geometry are components, not proxies). Their `.p3d` needs the 5 mem-points from Memory
  (Addendum 2026-05-29). 3-vertex proxy-face + `proxy:path.NNN`.
- **Crew proxies:** ViewGeometry + FireGeometry; vanilla models `\dz\vehicles\wheeled\proxies\crew_driver.p3d`
  / `crew_cargo.p3d`. Without them → `Proxy with bone name 'crewdriver' was not found in view geometry level`.
- **Door proxies:** door is a separate `.p3d` (`CarDoor` item) referenced by `inventorySlot`; its
  opening is animated by body model.cfg, not the proxy. A proxy model must carry the geometry
  property `autocenter = 0`, otherwise the 0,0,0 axis of the inserted model is not correct [DOC].


---

## Correction (2026-05-30c) — the reference quad's Geometry is extractable; the 2026-05-26 Object Builder note is stale

The Addendum 2026-05-26 note above says the reference quad (v53) is not fully debinarizable and routes its real geometry to Object Builder. That held only for an early state of the ODOL reader.

Current state: the v16 material block parses, all 12 LODs parse, and a complete MLOD of the reference quad can be generated and round-trips. Its Geometry LOD reads correctly, with hubs + 27 convex components + `class=vehicle`. The residual reader gap affects only visual LODs above 16 KB, which does not matter for Geometry work.

Operational rule: for car Geometry parity, use the extracted MLOD of the reference quad as the quantitative reference and edit the Geometry LOD with py3d. Treat the 2026-05-26 "Object Builder" sentence as history, not current guidance.

---

## (added 2026-06-05) Geometry LOD named property `class=vehicle` -- required parity

The Geometry LOD of every vanilla wheeled vehicle carries the named property `class = vehicle`
(alongside `autocenter = 0`). Verified universal -- civiliansedan, sedan_02, hatchback_02,
offroadhatchback, offroad_02, truck_01: 6/6 have `('class','vehicle')` on their Geometry LOD. It
flags the Geometry as a VEHICLE physics body. A procedurally-assembled Geometry that sets only
`autocenter=0` (the common py3d mistake -- assemble scripts set autocenter but never `class`) omits
it. Replicate it: `geo_lod.properties['class'] = 'vehicle'`, write back, confirm
`strings model.p3d | grep -c vehicle`.

Causation caveat (verified in-game 2026-05-27): adding `class=vehicle` did NOT fix LFQuad's
`WheelCountPresent()==0` -- it was deployed, confirmed present in the binarized Geometry LOD, and the
in-game result was unchanged. So treat `class=vehicle` as REQUIRED PARITY (6/6 vanilla carry it; a
vehicle build must replicate it and it is cheap), NOT as the proven wheel-simulation gate. The
actual silent wheel-sim gate verified in-game is the `CfgSlots.selection` <-> FireGeometry proxy
selection consistency rule (see `enforce-script-reference`, wheel attachment).

## Correction (2026-06-01) — spawn-launch is wheel-collision + placement, NOT mass/inertia [VERIFIED probe + in-game]

> Refutes the CAUSE framework of Addendum 2026-05-30 (which attributed bounce to monolithic hull/sharp
> edges as trigger + low inertia as amplifier). The multi-component construction method
> from that addendum remains valid parity; what is corrected is **what causes the launch**.

- **Mass/CoM/inertia REFUTED as trigger [VERIFIED probe]:** a body with mass re-biased to the reference quad's
  CoM (Y 0.474) + roll inertia ~209 (≈ the reference quad's 215) **bounced identically** (spd 15.1 at t0.5,
  matching to 3 digits). Spawn impulse is ~vertical with constant total mass → by physics `v~J/m` is
  independent of mass DISTRIBUTION. Convex decomposition and mass distribution are **orthogonal**
  levers: splitting the monolith does not move CoM/inertia and does not stop bounce by itself.
- **The reference quad's "Izz 350.7" was a uniform-mass artifact of the MLOD** (stripped); real roll inertia
  from the ODOL header is ~215. The "37% of the reference quad" comparison used the artifact.
- **Cause #1 MEASURED: chassis Geometry OVERLAPS wheel volume.** Each wheel center
  (`*_damper_land`) has chassis points at 0.16-0.19 m (tire radius 0.34) vs the reference quad's clean 0.43-0.46 m.
  The engine wheel collider self-penetrates with the chassis → PhysX ejects (the mechanism
  "overlapping objects explode" is real, but overlap is chassis-vs-WHEEL, not monolith-vs-terrain).
  Fixed: in-game wheels proceed to make contact (`wc` 0→1111 at t0.3).
- **Cause #2 MEASURED (in-game, side-by-side): placement.** Even with #1 fixed, LFQuad spawns at
  h=−0.264 (origin below surface) vs the reference quad +0.216 → buried wheels → ejection. Trace
  mechanism **unresolved**; do not claim "ECE traces over Geometry Y_min" as general
  fact (matches LFQuad but the reference quad +0.216 does not fit).
- **Still valid from 2026-05-30:** Geometry = multiple closed convex components + mass in all (the reference quad
  23 chassis + 4 hubs) is **real parity**, but it is parity, NOT the bounce trigger.

---

## Addendum (2026-06-01) — wheel-well clearance vs radius, wheel cylinder, contact diagnostics, mass-safe edit [VERIFIED]

### Killer check: wheel-well clearance against tire RADIUS (not hub box)

The old check "hubs outside hull" validated only the 8-pt hub box, NOT the full wheel cylinder
→ overlap slipped through. Correct, measurable check: for each wheel center (`*_damper_land`
centroid), **no chassis (non-hub) collision point may fall inside the tire radius**
(config `radius`, ~0.34, NOT the small `wheelHubRadius`). Target = reference clearance (radius +
~0.07-0.09 m). [VERIFIED: LFQuad 0.16-0.19 < 0.34 = overlap → bounce; the reference quad 0.43-0.46, 0 inside].
Across travel: clear in X (lateral) → well holds when
wheel moves up under compression.

### WHEEL `.p3d` Geometry must be a cylinder ~radius, NOT a box

A box with semi-axis = radius has **corners at radius·√2 (+42%)** → oversized square collider.
[VERIFIED: LFQuad wheel box, corners 0.482 vs config 0.34; the reference quad's 24-pt cylinder, uniform radial
0.340-0.366; check: `radial(Y-Z)` from center ≈ radius and uniform — box ⇒ max=min·√2].
And wheel `.p3d` needs **ViewGeo + FireGeo** (the reference quad has them;
a from-scratch build often omits them). Construct the cylinder: N-gon in Y-Z (radius) extruded in X (width) →
`scipy.ConvexHull` yields outward faces+normals; sel `component01` over all pts/faces; add LODs
ViewGeo (6e15) and FireGeo (7e15, sels `component01`+`wheel`). [VERIFIED: round-trip py3d + binarizes
in-game]. Wheel FireGeo must have penetration material on its faces (rubber/metalplate like
the reference quad); `material=""` degrades ballistics/surface (does not block spawn/contact).

### Reference collision = decomposition into NON-uniform convex boxes (not fine mesh, not uniform grid, not arbitrary hull)

[VERIFIED: the reference quad's Geometry = 23 skewed 8-pt boxes sized to the body (spine X±0.13, slabs
X±0.66) + 4 cylinders; LFQuad was 27 uniform axis-aligned boxes]. "Following
contour" = non-uniform boxes per region (width = actual body width there, narrowed at wheels
for wells) — NOT a convex hull of the body (engulfs it: VISUAL body reaches X±0.472,
over the wheel) and NOT decomposition into arbitrary hulls (inflate/bridge at fenders).
Box skew in the reference is invisible in-game (collision is not rendered) →
do not spend effort replicating it; do spend on functional aspects (clearance/radius/contact).

### Mass-safe collision edit: move points, do not regenerate

To open wheel-wells without disrupting physics: **move existing Geometry points**
(preserves per-point `#Mass#` → EXACT total mass + CoM); do NOT regenerate geometry (regenerating
redistributes mass → shifts CoM). [VERIFIED: reshape by moving points ±X maintained mass 1061.5 + CoM
(0,0.627,0.260) exact; a convex-hull regeneration shifted CoM 0.260→0.348].

### Contact diagnosis (isolates `contact=0` in ONE run)

Log `WheelHasContact(i)` per wheel + `WheelCountPresent()` for vehicle AND a working reference
(the reference quad) **side by side** in the test mission. `wc=0000` vs `wc=1111` isolates "wheels never
make contact". With `wp=0` (no wheel-item attached) the engine still simulates colliders from the model →
`wc` reflects the health of the model's wheel collision. Side-by-side delta (LFQuad −0.264 vs the reference quad
+0.216 at spawn) pinpointed placement immediately; "flies to 38 m" alone did not indicate it. API: `Car.Cast(o)`,
`WheelHasContact(int)`, `WheelCount()`, `WheelCountPresent()` — `P:\scripts\3_game\vehicles\car.c:286`, `:345` and `:348`.

### Tension with item #5 (thickness ≥0.5 m)

Item #5 from 2026-05-30 checklist ("chassis component ≥0.5 m wide") **conflicts with wheel-wells**:
collision must be NARROW next to wheels to clear them. The ≥0.5 m applies to high-speed collision
of the main body; in the wheel zone, narrow is REQUIRED. Apply #5 to the body away from
wheels, not to wheel-well boxes.

---

## 2026-06-02 — Spawn-launch root cause CORRECTED (confirmed in-game, LFQuad)

The earlier "monolithic Geometry / low inertia -> spawn launch" hypothesis (2026-05-30, marked
[verify in-game]) is **refuted**. Confirmed cause of a vehicle that spawns underground and gets
ejected: a stray `#Mass#` tag on a NON-Geometry LOD (typically FireGeometry 7e15).

- binarize bakes mass from whichever LOD carries `#Mass#`. A FireGeo `#Mass#` of all-zeros makes the
  ODOL ModelInfo `CoM=(0,0,0)`, inertia=0 -> `ECE_PLACE_ON_SURFACE` seats by CoM=0 -> spawns ~0.48 m low
  -> wheels buried -> PhysX depenetration -> ejection.
- The Geometry LOD (multi-component, convex, hubs) was correct the whole time. Proven by bisection:
  the reference quad's model + LFQuad's Geometry baked CoM 0.627; LFQuad-without-FireGeo baked 0.627. Material,
  mass-distribution, tris-vs-quads, skeleton and the py3d writer were all ruled out by experiment.
- `#Mass#` MUST live only on the Geometry LOD (1e13). py3d emits `#Mass#` on any LOD with a point whose
  `mass != None`. After every assemble, assert `lod.mass` per-LOD: only Geometry `!= None`, rest `None`.
  Fix: `point.mass=None` on non-Geometry LODs (the pattern is in `p3d-vehicle-killers.md`).
- Placement depends on the baked CoM (`h ~= CoM.y - GeometryYmin`), NOT on Geometry-Ymin / LandContact /
  bbox. No geometry tweak fixes a CoM=0 spawn -- bake the mass first.
- The build checklist of Addendum 2026-05-30 stays valid as BUILD invariants -- only the "monolith =>
  spawn launch" diagnosis is invalidated. Mass-only-Geometry check: `skills/dayz-p3d-audit/references/vehicle-checks.md`
  (`ERR_MASS_ONLY_GEOMETRY`, in the Killer 13 section). LOD bisection is what isolated the bug.

## (added 2026-06-22) Audit an INHERITED / imported vehicle BEFORE planning

When receiving a finished vehicle (config + model.cfg + p3d) or importing one from another game, audit it
host-direct BEFORE committing a plan — it reframes the scope and is cheap. Measured on MercedesAMGLF
(2026-06-22), a car received with config, model.cfg and p3d already made.

- **MLOD parse of the p3d (host-direct, ~60 Python lines)**: per LOD prints resolution + number of points/faces +
  named selections. Confirms which LODs / memory points / proxies ALREADY exist. A p3d "that looks complete"
  might truly be so (do not rebuild the structure) or have specific gaps (fix them one by one). Tell of
  a correct parse: final offset == file size, and resolutions match DayZ magic values
  (Geometry 1e13, Memory 1e15, ViewGeo 6e15, FireGeo 7e15). (Case: the received p3d had 9 LODs + 50
  memory points + wheel/crew proxies → good TEMPLATE, not a sketch.)
- **Vertex audit of the SOURCE (glTF accessors / FBX) per mesh**: splitting into proxies is a problem of
  GROUPING meshes under the per-model vertex ceiling of each LOD and each proxy (measured per model, with
  binarize's verdict as the gate: see `binarize-vertex-budget.md`), NOT of
  decimation. Sum `accessors[POSITION].count` per mesh and group them. (Case: 166 meshes / 236k verts; the
  largest 26.7k —no single one passes— but the aggregate blows through the ceiling ×7.)
- **Verify the SEMANTICS of inherited selections vs vanilla, not just their presence**: an inherited
  "complete" config can bring latent functional bugs. Compare each selection against how the vanilla
  engine consumes it:
  - `hiddenSelections`: vanilla uses FIXED light indices (CivilianSedan `P:\DZ\vehicles\wheeled\config.cpp:5138-5148`:
    front 0/1, brake 2/3, reverse 4/5, tail 6/7, dashboard 8). A config putting `color/glass/interior` into
    0-2 and lights behind DEVIATES → risk of broken lights.
  - refueling: vanilla loads position only if `MemoryPointExists("refill")` and `GetActionCompNameFuel()`
    returns `"refill"` (`P:\scripts\3_game\vehicles\transport.c:112-113` and `:459-461`). A p3d with `fuelpoint` (not
    `refill`) leaves the fuel action without position (falls back to 0,0,0).

---

## Addendum (2026-06-24) — proxy-path format + DayZ vehicle axis convention [VERIFIED vs CivilianSedan + a shipped third-party car mod]

> Two vehicle-general facts pinned on SUB_BRZ. Apply to ANY DayZ vehicle,
> not just imports from another game.

### MLOD proxy selections carry NO `.p3d` extension

A proxy selection is `proxy:<path>.<NNN>` (3-digit index) where `<path>` has **no `.p3d` suffix** — the
engine appends `.p3d` when it resolves. VERIFIED on vanilla (`proxy:\dz\vehicles\wheeled\civiliansedan\
proxy\sedanwheel.001`) and on a shipped third-party car mod.
Writing `...sedanwheel.p3d.001` makes the engine look for `...sedanwheel.p3d.p3d` → **proxy not found → that
attachment/geometry silently missing in-game** (wheels don't simulate, body proxy chunks invisible). It is a
silent failure: offline editor/py3d checks still "see" the proxy selection. ALWAYS author proxy paths
without the extension. py3d `add_proxy(path, index, ...)` → pass `path` without `.p3d`.

### Pure-geometry body-proxy TRIANGLE FRAME — py3d "identity" != engine identity [VERIFIED in-game 2026-06-24, MercedesAMGLF]

A pure-geometry proxy (body chunk / engine / interior / dash — 1 visual LOD, no config class) renders its
referenced geometry transformed by the frame the engine derives from the proxy TRIANGLE. MODEL-SPACE geometry +
the right triangle = the chunk overlays the shell exactly. Two traps, both bit MercedesAMGLF:

- **Geometry MODEL-SPACE, not centered.** Author each chunk at its real car position (vanilla `prox_int`
  Y[0.36,1.56] cabin, `sedan_engine` Z[-2.30,-1.12] front — measured by debinarizing the vanilla proxy `.p3d`).
  Re-centering each chunk to the origin makes the engine pile them all AT the origin.
- **Triangle frame MUST be `R=((-1,0,0),(0,0,1),(0,1,0))`, NOT py3d's "identity".** That is the value
  `py3d.derive_proxy_frame` returns for vanilla `prox_int`/`sedan_engine` AND for the body and steering-wheel proxies of a shipped third-party car mod.
  py3d's `canonical_proxy_triangle(rotation=None)` ("identity") produces a triangle the ENGINE RENDERS
  ROTATED ~90 deg — it passed every offline check yet failed in-game twice. Author with:
  `lod.add_proxy(path, index, origin=(0,0,0), rotation=((-1,0,0),(0,0,1),(0,1,0)), scale=0.1)` (path WITHOUT `.p3d`).

GATE: for proxies the offline frame/render is NOT a valid acceptance gate (false-green twice on MercedesAMGLF) —
the gate is the in-game spawn+render; offline only rules out gross errors (missing selection, duplicate `.p3d`).
Attachment proxies (wheel/crew/door) are placed by physics/config, not the triangle — their `pos` is NOT a
reference for pure-geometry placement.

### DayZ vehicle axis convention: front = −z, driver = +x

Measured on CivilianSedan, ODOL v54 on DayZ 1.29, not re-measured on the v56 copy on `P:\` (the CONTROL): headlights/engine/`drown_engine` at **z ≈ −1.7..−2.4** (front),
reverse light/exhaust/`refill` at **z ≈ +2.2..+2.6** (rear), `seat_driver` at **x = +0.436** (driver on
+x). So a DayZ car FACES −z. Wheel naming `wheel_<side>_<axle>`: side 1 = +x, side 2 = −x; axle 1 = front
(−z), axle 2 = rear (+z) — front (steered) wheels are `_X_1`. When importing from a tool whose cars face +z
(most other games), the correct transform flips z; a car that "looks rotated 180°" relative to the source is
usually CORRECT — verify against CivilianSedan markers (a static render cannot show a front/back swap), do not
refactor on sight.

### `validate()` ERR_COMPONENT_NAMING is a false-positive for vehicles

Vanilla vehicle Geometry LODs use **lowercase `component01`** (CivilianSedan does, and it works) — the
py3d/audit "engine requires `Component01` uppercase" rule does not hold for Inventory_Base items either:
measured in game on 2026-10-02, `component01` collides exactly like `Component01` on an item and on a
`HouseNoDestruct`, unbinarized and binarized, and binarize writes both as `component01` (dayz-p3d-audit
killer #2). Match vanilla (lowercase) for vehicles; the resulting `ERR_COMPONENT_NAMING` from `P3D.validate()`
up to py3d 1.8.0 (pinned until 2026-10-02) is expected (the CONTROL itself triggers it); py3d 1.9.0 does not check
the case and stays silent. The same code for a collision LOD with faces and no component at all is not one
to wave off: on an item and a building that collision was gone (vehicles not measured); from 1.9.0 it is
the only reason the code fires, on the Geometry, View or Fire LOD.

## Addendum (2026-06-24) — componentNN DUAL-TAG: hub/seat selections must SHARE faces with a componentNN [VERIFIED in-game, was the SUB_BRZ spawn blocker]

The LOD tables above list `componentNN` + `wheel_X_Y_damper_land` + `seat_driver`/`seat_codriver` as if they were
independent selections. They are NOT independent: **the engine enumerates collision/action components ONLY by
`componentNN`**, so a hub/seat selection whose faces are in NO `componentNN` (a standalone island) is invisible to
the component pass and entity creation FAILS:
- `PHYSICS (E): Won't simulate, wheel wheel_1_1_damper_land has no proper selection in geometry`
- `PHYSICS (E): Action selection 'seat_driver' was not found in view or fire geometry level of model when parsing class Crew::Crew`

REQUIREMENT (a collision object must be named `ComponentXX` [DOC]): each hub/seat box carries BOTH names on the SAME
faces — `wheel_X_Y_damper_land` AND a `componentNN` (Geometry); `seat_driver`/`seat_codriver` AND a `componentNN`
(ViewGeo, plus Geometry if seats live there). The hub IS component0N; the seat IS component0M. This is the SAME
dual-tag a FireGeo already does for `dmgzone_*` + `componentNN` on one box — extend it to the Geometry hubs and the
ViewGeo/Geometry seats.

THE DISCRIMINATOR (add to the car's verifier): for each hub/seat selection, the % of its faces also covered by a
`componentNN` in the same LOD. Working cars = **100%** (CivilianSedan 15/15, a shipped third-party car mod 15/15, LFQuad 60/60); the
SUB_BRZ that would NOT spawn = **0/12**. 100% = pass; anything else = the spawn blocker.
```python
def component_overlap(lod, sel_name):  # returns 1.0 when ok
    comp = {tuple(sorted(v.point_index for v in f.vertices))
            for n in lod.selections if n.lower().startswith("component")
            for f in lod.selections[n].faces}
    tf = [tuple(sorted(v.point_index for v in f.vertices)) for f in lod.selections[sel_name].faces]
    return sum(k in comp for k in tf) / len(tf)
```
Why it survives many "the selection is present and parity-correct" cycles: everyone checks PRESENCE; nobody checks
the componentNN face-OVERLAP. Offline parity ≠ drivable — this is one more thing only the in-game spawn gate (or
this overlap check) catches. Two other candidate deltas (hub 16pt-vs-8pt-box, seats-in-Geometry) were RED HERRINGS:
a box hub is a valid component, seats-in-Geometry is fine (LFQuad does it) — once they are ALSO componentNN.


---

## Addendum (2026-06-25) — ATTACHMENT proxy needs a companion BONE-NAME selection (py3d add_proxy omits it) [VERIFIED vs CivilianSedan + a shipped third-party car mod; confirmed in-game on SUB_BRZ]

An **attachment** proxy (crew / wheel / door — i.e. one the engine binds to a skeleton bone, NOT a pure-geometry
body chunk) needs TWO things in the LOD, not one:
1. the `proxy:<path>.<NNN>` selection + triangle (what `py3d LOD.add_proxy` creates), AND
2. a **companion NAMED SELECTION whose name IS the bone name** (`crewdriver`, `crewcodriver`, `wheel_1_1`,
   `wheel_2_1`, `wheel_1_2`, `wheel_2_2`, `doors_driver`, `doors_codriver`, `radiator`, …), carrying the **SAME
   3 points + 1 face** as the proxy. This is the proxy→bone binding Object Builder writes when you "name" a proxy.

`py3d add_proxy` creates only (1). Without (2) the engine reports, at `Load entity type`:
- `PHYSICS (E): Proxy with bone name 'crewdriver'/'crewcodriver' was not found in view geometry level of model`
  → crew not set up → `CrewPositionIndex` returns -1 → **get-in action never appears** (the cursor hits the seat
  component but the crew position isn't registered).
- `PHYSICS (W): Proxy with name 'CivSedanWheel_1_1'..'2_2' was not found in FireGeometry of the shape` (the wheel
  attachment can't find its hub proxy).

**Pure-geometry body-chunk proxies do NOT need (2)** (no bone) — that is why they resolve with zero error while the
crew/wheel proxies fail; do not be misled into thinking py3d proxies are universally broken.

VERIFIED — both working models bind every attachment proxy this way, in **ViewGeo AND FireGeo**:
```
# CivilianSedan ViewGeo+FireGeo non-proxy selections that share points with a proxy:
crewdriver   -> crew_driver.001    crewcodriver -> crew_cargo.001
wheel_1_1 -> sedanwheel.003  wheel_1_2 -> sedanwheel.004  wheel_2_1 -> sedanwheel.001  wheel_2_2 -> sedanwheel.002
doors_driver -> sedandoors_driver.001   doors_codriver -> sedandoors_codriver.001   radiator -> radiator_car.001
```
The wheel **bone name maps by POSITION** (`wheel_<side>_<axle>`, side1=+x/2=−x, axle1=front=−z/2=rear=+z), NOT by the
proxy index. The bone names must also exist in `model.cfg` `CfgSkeletons skeletonBones[]` (SUB_BRZ already declares
`crewdriver`/`crewcodriver`/`wheel_*`).

DISCRIMINATOR / verifier (add to the car's verifier): for each attachment proxy, assert a same-points companion
selection named after its bone exists. SUB_BRZ had **0** bone selections (only the 4 occlusion components + 2 seats);
CivilianSedan and the third-party car mod have the full set. Builder rule: after each crew/wheel `add_proxy`, create
the bone selection (`add_proxy(rotation=R, scale=1.0)` + point flags 63 + a bone selection from the proxy's
faces/points).

GATE: as with every proxy finding here, offline checks gave FALSE-GREEN 4 times on SUB_BRZ (occlusion / frame / scale
/ flags) — the only valid gate is the in-game RPT (the `bone name not found` line gone). This bone-selection fix is
**CONFIRMED in-game on SUB_BRZ (2026-06-25)**: after a re-spawn the server RPT has ZERO `PHYSICS (E/W)` lines
(all `bone name not found` / `no proper selection` gone). BUT this only fixes get-in **gate-1** (`CrewPositionIndex`);
**gate-2 (`CrewCanGetThrough`) needs the car to run as an Enforce Script CLASS, not bare `CarScript`** — a car imported
from a racing game with config `class <MOD>: CarScript` and no `.c` runs as bare CarScript whose `CrewCanGetThrough` returns false (base
`Transport` stub) → get-in still never appears. See the next addendum, "GET-IN ROOT CAUSE #2".

**Separate, do not conflate with get-in:** (a) doors do not have to open or close before get-in shows (see
"Doors are NOT required for get-in" below; SUB_BRZ has no CarDoor **attachments**, its doors are baked into body
chunks). (b) get-in's `CanReachSeatFromDoors` (`carscript.c:2177`) uses the
`seat_con_X_Y` **memory point** + player within 1.0 m, NOT the physical door attachment.



---

## Addendum (2026-06-25) — GET-IN ROOT CAUSE #2: a custom CarScript vehicle needs an Enforce Script CLASS, not just geometry [VERIFIED in-game on SUB_BRZ 2026-06-25 + vs vanilla source]

> Project-agnostic. Applies to ANY DayZ ground vehicle declared `class <MOD>: CarScript` with no `.c` script
> class — imports from another game, OBJ or Blender, cars/trucks/quads authored from scratch. This is the get-in blocker that
> survives a perfectly parity-correct model (every LOD, every selection, every memory point present). The two
> proxy-side gotchas above (componentNN DUAL-TAG, ATTACHMENT proxy BONE-NAME) fix gate-1 of get-in; THIS fixes
> gate-2 and is independent of geometry.

### Symptom

The vehicle spawns, renders and collides, but the "Get in" action NEVER appears in the action menu.
No RPT error by itself (the action is silently filtered inside its `ActionCondition`). Telemetry tell: the
reported `class_name` stays at the base `"CarScript"` instead of your `"<MOD>_Base"` — the override class never
attached because there is no script module compiling it.

### Cause — the two-gate ActionCondition + the unoverridden base stub

`ActionGetInTransport.ActionCondition`
(`P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetintransport.c:45-55`) has TWO gates
that BOTH must pass:
1. gate-1 `CrewPositionIndex(componentIndex) >= 0` — needs the crew proxy bone selection (the "ATTACHMENT proxy
   BONE-NAME" addendum above); and
2. gate-2 `transport.CrewCanGetThrough(crewIndex)` (~:54), then a reachability loop
   `CanReachSeatFromDoors(selections[i], playerPosition, 1.0)` (:62-66).

`CrewCanGetThrough` is **NOT overridden by `CarScript` or `Car`** — only by the concrete vanilla car classes
(`CivilianSedan` etc.). A vehicle running as **bare `CarScript`** falls to the base stub
`Transport.CrewCanGetThrough` (`P:\scripts\3_game\vehicles\transport.c:724-731`), which returns **false** in the
normal build (`#ifndef CFGMODS_DEFINE_TEST`) → gate-2 false → get-in never appears, no matter how perfect the
crew bone is. The same trap hits `GetSeatAnimationType` (`transport.c:682-686` → `Error("not implemented")`) and
`GetAnimInstance` (used in `ActionGetInTransport.Start`), both of which also `Error()`/false in the base.

### Fix — ship a thin `<MOD>_Base.c` script class (PIPELINE requirement; for an import pipeline add to the config/script phase)

Minimal M1 set (the three are mandatory; door mappers / `CanReach*` / `GetSeatIndexFromDoor` /
`GetAnimSourceFromSelection` are M2 — needed for openable doors and seat-switching, not for entering+driving).
Signatures as in `CivilianSedan` (`scripts/4_world/.../civiliansedan.c:109,119`):

```c
class <PREFIX>_Base extends CarScript
{
    override int GetAnimInstance()                 { return VehicleAnimInstances.SEDAN; }       // civiliansedan.c:109
    override int GetSeatAnimationType(int posIdx)                                               // civiliansedan.c:119
    {
        switch (posIdx) { case 0: return DayZPlayerConstants.VEHICLESEAT_DRIVER;
                          case 1: return DayZPlayerConstants.VEHICLESEAT_CODRIVER; }            // add PASSENGER_* per seat
        return 0;
    }
    override bool CrewCanGetThrough(int posIdx)    { return posIdx == 0 || posIdx == 1; }       // M1 ungated; gate on door-state at M2
    // MODEL must carry memory points seat_con_1_1 / seat_con_2_1 + a crew config with seat_driver / seat_codriver.
    // M2 (openable doors / seat-switch): GetCarDoorsState, door-slot mappers, CanReach*, GetSeatIndexFromDoor, GetAnimSourceFromSelection.
}
```

The mod needs a `CfgMods` script module (`worldScriptModule files[]`) so the `.c` compiles. A shipped
third-party car mod uses the same pattern (third-party mod behaviour, not vanilla): its base class extends
`CarScript` directly instead of re-parenting to a vanilla car, and overrides
`CrewCanGetThrough`/`GetSeatAnimationType`/`GetAnimInstance` plus the M2 door methods itself.

### Geometry requirement (verified) — `seat_con_*` memory points

`CarScript.CanReachSeatFromDoors` (`scripts/.../carscript.c:2177-2198`) calls
`GetDoorConditionPointFromSelection` → `if (MemoryPointExists(conPointName))` and only then compares distance
≤ 1.0; if the memory point is absent it returns false → action filtered. The base maps `seat_driver`→`seat_con_1_1`,
`seat_codriver`→`seat_con_2_1` (`carscript.c:2141`), so NO override is needed for the mapping, but the model MUST
carry the memory points `seat_con_1_1`/`seat_con_2_1`, positioned so the player is ≤ 1.0 m away when facing the
door/seat. The `crew` config must expose `seat_driver`/`seat_codriver`.

LHD-only caveat (added 2026-10-01, WRX STI): "no override is needed" holds for
a LEFT-HAND-DRIVE layout only. On a right-hand-drive car whose memory points are named by physical
side (driver door = `seat_con_2_1`), the base table pairs each seat with the far door and get-in
dies on the 1.0 m test from the correct door; override `GetDoorConditionPointFromSelection` crossing
the sides, as vanilla does for its own layouts (`OffroadHatchback.c:364-379`, `Van_01.c:269-287`,
DayZ 1.30.164014 Exp).

### Doors are NOT required for get-in

`GetCarDoorsState` returns `DOORS_MISSING` when no `CarDoor` attachment exists (`civiliansedan.c:190-193`),
and `DOORS_MISSING != DOORS_CLOSED` → `CrewCanGetThrough` passes. A script class with
NO door attachments gives WORKING get-in (baked doors stay static). Openable doors are a SEPARATE feature (`CarDoor`
classes + door proxies + door `.p3d` + `AnimationSources DoorsX` + model.cfg door bones).

### In-game tell after the fix

Telemetry reports the custom class (`class_name:"<MOD>_Base"` instead of `"CarScript"`) AND "Get in" appears.
As with every finding here, offline checks cannot prove get-in — the gate is in-game.


## Addendum (2026-06-25) — verification = validate against the CONTROL, not assert blind; damper/steering are NOT universal [VERIFIED vs CivilianSedan MLOD]

A verifier whose expected values are hardcoded (even when comments cite "sedan") is a false-green
risk: it asserts the producer's internal consistency, not the engine contract. Fix = a **positive
control**: run the UNIVERSAL subset of checks against a known-good vanilla car (`CivilianSedan`
debinarized MLOD) and require it to PASS. If the sedan fails a "universal" check, the contract is
wrong, not the car. Give the verifier a positive-control mode that takes the sedan MLOD.

What the positive control CAUGHT and corrected — the per-car verifiers of MercedesAMGLF and SUB_BRZ both had it:
- They asserted `wheel_X_Y_damper` / `wheel_X_Y_damper_axis` and `wheel_X_1_steering` / `_steering_axis`
  as **Memory-LOD universal** selections. **The vanilla sedan has NONE of them in Memory.** It uses a
  `susp_arm_*` linkage (double-wishbone) with `susp_arm_steering_X_1_axis` for steering, and keeps
  `wheel_X_Y_damper_land` in the **Geometry** LOD (the hub), not Memory. The simple
  `wheel_X_Y_damper`/`wheel_X_1_steering` scheme is a convention of imported models, NOT vanilla contract.
- TRUE universal wheel contract (sedan-verified): `wheel_X_Y_axis` in Memory + `wheel_X_Y_damper_land`
  in Geometry, each 100% inside a `componentNN` (see the componentNN dual-tag addendum). Damper/steering
  selection NAMES are per-car/per-skeleton (model.cfg) → POLICY tier, not universal.

Run-before-closed gates (block, don't skip): a verifier self-test (non-tautology proof, catches
the 0/12-componentNN blocker), the positive control on the sedan (contract satisfiable), the
target hard-pass, and a py3d read→save→read round trip (write fidelity). Never close a phase on a
metric that is 0.000/100% by construction.

---

## Addendum (2026-06-25b) — reusable verification harness for ANY car (generic vs import-specific split)

A car build needs a verification harness whose gates BLOCK: skippable verification is how the offline
false-green happened. None of the tools below ship in this repo; build them per project from these
descriptions. The GENERIC pieces apply to ANY DayZ vehicle (procedural / OBJ / glTF too), the rest are
PATTERNS to re-point.

GENERIC (wire these for any car, not just an import from another game):
- **A universal car verifier** — a tier-**U** universal engine contract + a per-car `POLICY` dict
  (dmgzone list, body-proxy naming, mod token). A positive-control mode run on the debinarized
  CivilianSedan MLOD proves the contract is satisfiable; a self-test proves non-vacuity. Add a POLICY
  entry per new car instead of forking one verifier per car.
- **A visual gate** — Blender-headless N-angle render + the `blender-visual-review` checklist +
  an unresolved-proxy inventory. CAVEAT (2026-07-02): it does NOT reproduce the engine cull — the engine
  renders the ANTI-cross side and shades with the STORED MLOD normals, while Blender no-normals + backface
  culling shows the +cross side (the exact opposite); and it does NOT resolve body-split proxy chunks
  (they are inventoried, not rendered). Use it only for geometry presence / silhouette / proxy inventory;
  winding and see-through verdicts are IN-GAME ONLY. Works on any `.p3d`.
- **A writer round trip** — py3d read→save→read fidelity (catches the skinned-export corruption class).
- **A clean visual shell** — reconstruct a runnable shell-only `.p3d` from a deployed full one.

PATTERN (bound to a builder/transform — re-point for each build pipeline):
- STRUCTURAL BISECTION: feed YOUR structural builder the CONTROL (CivilianSedan
  shell + locators from its own memory points) and require the regenerated LODs to pass the UNIVERSAL subset.
  Run a NEGATIVE control too (break the invariant — e.g. disable the hub/seat componentNN dual-tag) and require
  the bisection to CATCH it: that proves it tests the BUILDER and is non-tautological (it would have caught the
  0/12 blocker offline). Requires the builder exposed as `build_structural(profile)` (parametrized shell /
  locators / mass / bbox-source / out), not a hardcoded script.
- TRANSFORM FIT: fit the source→DayZ transform from anchor pairs, confirm it is a pure
  sign-flip+offset, and PERTURB it (wrong sign / offset / scale) to prove the residual discriminates — a
  self-built pair gives residual 0.000 by construction, so the discrimination test is what makes it
  real, not the residual.

The implementation for imports from another game and the MANDATORY-gates spec: `rip-import.md` §"Generalized harness".



---

## Addendum (2026-06-27) — Crew get-in: dedicated seat components + canonical crew-proxy triangle [VERIFIED in-game: LFQuad + MercedesAMGLF]

The "Get in" radial and the seated player are governed by TWO ViewGeometry structures that procedural / regen body pipelines get wrong by default. Both blocked LFQuad (resolved 2026-06-05) and MercedesAMGLF (2026-06-27). Symptom: the driver works but the **codriver radial never appears**, and the seated player sits sideways/backward or mis-placed.

### 1. Get-in appears for driver but NOT codriver (raycast "always driver")

DayZ resolves the seat with **`Transport.CrewPositionIndex(componentIdx)`** (proto native, `P:\scripts\3_game\vehicles\transport.c:179`) over the **collision component the cursor raycast HITS in the ViewGeometry LOD** (`ObjIntersectView`, `dayzphysics.c:88`; consumed at `actiongetintransport.c:45-46`) — NOT by memory-point proximity. So each seat needs its OWN dedicated, clean, closed-convex component:

- `seat_driver` = 1 dedicated `ComponentNN` (its own cube); `seat_codriver` = 1 dedicated `ComponentNN`. Dual-tag: the seat selection and its `ComponentNN` share the SAME faces (100% overlap).
- Seats painted across a multi-component grid -> the raycast never lands cleanly on the 2nd seat -> "always driver". (LFQuad: `seat_driver/codriver` spread over 88/112 points across ~23 components -> codriver never appeared.)
- References: vanilla CivilianSedan `seat_driver`=component31 / `seat_codriver`=component32 (one each); the reference quad one each.
- **FIX (LFQuad + MercedesAMGLF):** replace with 2 dedicated seat-cube components — each a clean closed box (8 verts, 12 tris, ALL faces outward) tagged `seat_X` + its own `ComponentNN` on the same faces.

Closed-car note (MercedesAMGLF): a closed car does NOT need the full body shell in ViewGeo — 2 dedicated seat cubes + wheel/crew proxies suffice. A solid body box (e.g. a central "spine") only OCCLUDES the seat cubes (cursor hits the spine first -> no seat hit) -> remove it. LFQuad/vanilla keep a shell only because they are open / have window openings.

### 2. Seated player sideways/backward/mis-placed, and proxy translations "don't move" him

Seated position AND orientation come from the **crew-proxy triangle** (`crewdriver`/`crewcodriver`, present in ViewGeo AND FireGeo), NOT from `pos_driver`/`pos_codriver` memory points. Two traps:

- **Triangle SHAPE must be CANONICAL = 3 distinct angles.** `origin + e1 + e2` with edge lengths ~1.0 and ~2.0 (angles 90 / 63.4 / 26.6). An isosceles 90/45/45 triangle = AMBIGUOUS frame (the proxy angle-sort rule ties -> orientation rotates differently per seat). A TINY triangle (py3d `add_proxy(scale=0.1)` -> edges ~0.05) is below the engine's frame-derivation threshold -> player mis-placed AND **translating the proxy has little/no visible effect** (the "I moved it and nothing happened" symptom on MercedesAMGLF). Make it canonical and translations respond.
- **FRAME (facing) depends on e1/e2 AND the model's base orientation.** Model facing -z (vanilla convention) -> SUB_BRZ and vanilla use `e1=(0,0,1), e2=(0,2,0)` -> `R=((-1,0,0),(0,0,1),(0,1,0))`. A model yaw-rotated 180 deg (e.g. an import reoriented in a later phase, like MercedesAMGLF) needs `e1=(0,0,-1)` -> `R=((1,0,0),(0,0,-1),(0,1,0))` to face forward. Replicate a KNOWN-GOOD same-orientation reference; do NOT copy a frame cross-model without recomputing. Practical tell: with the canonical triangle, +z moved the MercedesAMGLF player FORWARD (its forward is -z after the 180 deg yaw) — establish the sign empirically once, then it is exact.
- **The triangle ORIGIN (v0) anchor sets the seated HEIGHT + longitudinal position** — not the memory point. Translate all 3 verts together; use ~15 cm steps (small steps read as "no change"). A low sports-car roof may clip the standing pose regardless (inherent; not fixable from the .p3d).

### Builder fix (so future cars never hit this)
Import and regen builders create crew proxies via `add_proxy(..., scale=0.1)` -> tiny ambiguous triangles, and may paint seats over the collision grid. Change crew-proxy creation to emit the **canonical triangle (edges ~1.0/2.0, 3 distinct angles)** with the model-correct frame, in BOTH ViewGeo and FireGeo, and build seats as **2 dedicated clean cubes** (one ComponentNN each) from the start.

The earlier diagnosis "codriver needs crew proxies in FireGeo" is REFUTED: the cause is collision-component cleanliness + the canonical proxy triangle, not FireGeo presence.

### CRITICAL EXTENSION (2026-06-28, SUB_BRZ — in-game CONFIRMED): seat ComponentNN cubes must be INWARD-wound + point flags `0x0000003F`, or they are NOT raycast-collidable

The "2 dedicated clean cubes, all faces outward" rule above is NECESSARY BUT NOT SUFFICIENT for a py3d-authored vehicle. A seat cube with **OUTWARD winding + point flags 0** is **invisible to `DayZPhysics.RaycastRV(..., ObjIntersectView)`** — the get-in action-target raycast never resolves it, so `CrewPositionIndex` falls back to component0 and the **codriver radial never appears** (the driver "works" only by that fallback; even the driver cube isn't truly hit). The crew mapping `CrewPositionIndex(comp)->crewIdx` is already correct (comp0→driver, comp1→codriver) — irrelevant while the geometry isn't raycast-collidable.

Measured (SUB_BRZ vs LFQuad positive control, headless probe): BRZ seat cubes were OUTWARD + flags 0 → `RaycastRV` `hit=0` from every direction at the exact cube center. After rebuilding the BRZ ViewGeo seat ComponentNN with **inward winding + point flags copied from the control** (not just shape/name), `RaycastRV` returns `hit=1 comp=1 crewIdx=1` and the codriver get-in works **in-game (confirmed 2026-06-28)**. The flag value to copy is `0x0000003F`: sealed control `civiliansedan_mlod.p3d` SHA `823585B6EC9727F70C3ABCAD309ECBF7E87DBA1E66FA14A1ECAB9AB1FCA921DD`, ViewGeometry (res 6e15), 478 points / 422 faces, histogram `0x0000003F` → 478 points (100.0%), `0x02000000` → 0 points (measured with py3d 1.4.0, reproduced on two byte-identical copies of the file). The patch changed winding and flags together and never isolated the flag as cause; the safe rule is the sealed vanilla convention. Corroborated on a second working model: the MLOD of the reference quad carries `0x0000003F` on 482 of 482 ViewGeometry points. The `0x02000000` once recorded as the requirement is what the py3d-based exporter emits — 290 of 296 points on the LFQuad body — so that value had been measured on the product, not on the control.

**Rule:** build ViewGeometry collision ComponentNN for vehicles (seats, and any cursor/action-targetable component) by COPYING the sealed vanilla control's convention — **inward winding + point flags `0x0000003F`** — not py3d's default outward+flags0. Outward py3d boxes pass every offline shape/winding/dual-tag check yet are NOT raycast-collidable. Dual-tag and the in-game confirmations stand: SUB_BRZ and MercedesAMGLF headless `hit=1 comp=6 crewIdx=1`.

**Diagnostic (reusable, no manual aim):** a headless mission probe that spawns the car + a known-good control, dumps `CrewPositionIndex(0..79)`, and casts `DayZPhysics.RaycastRV` (FIRE+VIEW) at each seat — localizes "mapping vs raycast vs collidability" in one run. Parse the raw `hit=1 comp=N crewIdx=N` lines, NOT a boolean verdict — a regex `-match '1'` also matches `-1` (a false-green seen in practice).

### MercedesAMGLF CONFIRMATION + refinements (2026-06-28) — the seat winding+flags fix CONFIRMED on a 2nd car

The CRITICAL EXTENSION above is now CONFIRMED on MercedesAMGLF (headless crew-probe: codriver VIEW ray from its door side -> `hit=1 comp=6 crewIdx=1`; driver -> `hit=1 comp=5 crewIdx=0`). Three refinements from applying it to a CLOSED car:

- **Apply it MINIMALLY when the seat ComponentNN already map.** If the ViewGeo seats already enumerate as their own ComponentNN with the correct crew mapping (verify with the get-in diag PROBE / crew-probe `CrewPositionIndex(comp)`), do NOT rebuild the whole ViewGeo (SUB_BRZ rebuilt all ~23 components). Flip ONLY the seat ComponentNN faces in-place to inward winding + set their point flags to `0x0000003F`, recomputing each face normal from the new (inward) order. This preserves the verified component indices/positions and the seat<->componentNN dual-tag. MercedesAMGLF: only `seat_driver`=Component06 / `seat_codriver`=Component07 changed; body components left untouched; the car's verifier stayed 35/35.

- **"Body shell in ViewGeo / high-index seats" is a RED HERRING for the codriver blocker.** MercedesAMGLF added 5 body occlusion components + moved seats to high indices (idx 5/6) on the theory that the engine "could not discriminate 2 bare cubes" -> the codriver STILL failed. The real and ONLY cause was winding+flags (proven on the next run). Confirms + sharpens the 2026-06-27 closed-car note: a closed car needs NEITHER a body shell NOR high-index seat placement in ViewGeo -- just the 2 seat cubes, inward-wound + point-flagged. Leave any body occlusion components OUTWARD + flags 0 (inert, non-raycast-collidable -> cannot occlude the seat ray). Do not chase the "give the ViewGeo a body" lever; chase winding+flags.

- **Crew-probe seat anchor: aim at `pos_driver`/`pos_codriver` memory points (engine space) -- but ONLY if they sit inside the seat cube.** `c.GetMemoryPointPos("pos_driver")` returns ENGINE-space coords, sidestepping the py3d->engine sign flip (MercedesAMGLF engine driver = +x, py3d driver = -x). Its pos_driver/codriver are y~0.78, INSIDE the seat cubes -> aim there directly (no height-raise). CAVEAT for the positive control: a VANILLA car's `pos_driver` is the door-sill ENTRY point (CivilianSedan: y~0.07, x~+-1.4), NOT the seat center -> a ray aimed there hits the body (comp=-1), giving a FALSE "control failed". For a positive control, anchor at the seat ComponentNN centroid, or use a car whose `pos_X` is at the seat (LFQuad). The target's result is self-validating when its rays hit the real seat comps.

- **Crew-probe tooling** (reusable, no manual aim): a mission `init.c` that spawns target + control near the player, dumps the `CrewPositionIndex` table and casts RaycastRV VIEW+FIRE per seat from +-x/+-z; and a runner that injects the probe into the PROJECT-LOCAL `<Mod>_dev\_server\mpmissions\...\init.c` (NOT the shared DayZServer mission), launches detached, polls the server `script.log` for `[CREW-PROBE]`, and restores the original init.c in `finally`. Parse the raw `hit=N comp=N crewIdx=N` integers, never a regex `-match '1'` (it also matches `-1`). Build-only PBO for the probe: `dayz-test.ps1 -Build` builds and then launches (it has no build-only switch) -> replicate its AddonBuilder call directly (`<src> <target> -prefix=<Mod> -temp=<FRESH_DIR> -packonly`); a FRESH `-temp` gives a clean sync.

---

## Appendix — REGEN-FROM-glTF + GET-IN RADIAL / LOD ladder

> These two blocks are structural parity for imported/regen bodies and belong with the parity method.

## REGEN-FROM-glTF BODY + PROXY-SPLIT (added 2026-06-24)

Regenerating a high-poly body from a glTF/FBX and splitting it into proxies to beat the
vertex ceiling (measured per model, gated by binarize: see `binarize-vertex-budget.md`) has two traps that pass every offline gate and
only surface in-game. Measured on MercedesAMGLF, 2026-06-24.

### glTF→DayZ winding: the offline check can be a tautology
The transform `DayZ=(-s·bx,+s·bz,-s·by)` has `det=-1` (a mirror) and flips face handedness. A winding
check that compares the post-transform geometric normal against the post-transform **declared glTF
normals** is **tautological** — the winding was reversed precisely to make them agree, so it reports
~0.00% flipped by construction (a result of 0.000 by construction is the tell). It proves internal consistency, not that DayZ
renders the texture outward. DayZ backface-culls by **winding**; the mirror-compensating reverse left
the front face pointing inward, so the body rendered see-through (texture on the interior) in-game.
Fix confirmed in-game: do NOT reverse — keep the glTF vertex order (`reverse_winding=False`). The
offline winding check must validate against the DayZ convention or against a reference model known to
render correctly, never against the normals you picked to match.

### proxy placement: an identity frame does not mean the geometry is aligned
A proxy `proxy:\...\X.NNN` is a tiny triangle whose engine-derived frame (angle-sort, computed by
`py3d.derive_proxy_frame` = the engine's rule, see the `dayz-proxy-align` skill) can be **identity-perfect**
(det +1, unambiguous, angles 90/63.4/26.6) and the referenced geometry still render ~2.5 m offset. The
frame is not the whole story: the engine places the referenced model by a **non-origin reference
point**, so a vanilla wheel (local geometry centered at its own origin, ~0.4 m, full LOD set) lands
right while a body region in **model-space** (car-sized, single visual LOD) is shifted by roughly its
own extent. Two fixes that FAILED on MercedesAMGLF: bumping the proxy-triangle scale (the engine
normalizes the triangle, so scale is moot) and the "wheel pattern" (re-center the geometry to its
bbox-center + anchor at that center — proves the engine does not use bbox-center either).

A first reading of this ("vanilla does not proxy the car body, so fit the body under 65535 as direct
geometry instead") is superseded by the next block.

### proxy placement — the confirmed convention (in-game, 2026-06-24, MercedesAMGLF)

The model-space geometry with py3d's "identity" frame FAILED in game: the body proxies rendered rotated or
invisible, while the offline gate (frame = identity for all 6 `mb_` proxies, scatter render, verifier 33/33) was
**FALSE-GREEN twice**. Two causes, both written out in the 2026-06-24 addendum above: the proxy SELECTION PATH
carried a `.p3d` extension ("MLOD proxy selections carry NO `.p3d` extension"), and py3d's "identity" triangle is
not the engine's identity ("Pure-geometry body-proxy TRIANGLE FRAME"). **FIX THE PATH FIRST**, then judge the frame.

Detailed car mods DO proxy the body and it works. A pure-geometry proxy (1 visual LOD, no config class — vanilla
`prox_int`/`sedan_engine`, and the body, chassis and engine chunks of shipped third-party car mods) needs ALL THREE of:

> 1. **Geometry in MODEL-SPACE** (real car position, NOT re-centered).
> 2. **Proxy selection path WITHOUT `.p3d`** (`proxy:<path>.<NNN>`).
> 3. **Proxy-triangle FRAME = `R=((-1,0,0),(0,0,1),(0,1,0))`**, the measured vanilla frame; never trust py3d's
>    "identity".

Attachment proxies (wheel/crew/door) are NOT a placement reference: they are placed by physics/config (axles,
`proxyPos`) so their non-zero `pos` misleads. Re-fit/decimate is the WRONG default for a high-detail body
(MercedesAMGLF body ~167k resolved → ~60% decimation); proxies are correct and work when authored as above.
The transform-scale reference must be a STABLE artifact (the donor `.p3d`), never the
deployed shell (pointing at your own output shrinks scale ~3%/rebuild). **For proxies the offline
frame/render is NOT a valid gate — the gate is the in-game render.**



## GET-IN RADIAL + LOD LADDER on proxy-body cars (added 2026-06-27, MercedesAMGLF)

### Script binding (precondition, silent failure)
A car `class X: CarScript` whose `CfgMods.<Mod>.defs.worldScriptModule` does not load its script path →
the script class never binds → the get-in trio (and every override) is DEAD without error (`script.log`
0-byte = false-clean; telemetry reports BASE class `CarScript`). On DayZ 1.29 the working form was
`dir = "<Mod>";` plus backslashes, `files[] = {"<Mod>\scripts\4_World"}`. On DayZ 1.30.164200 that does not
hold (measured in game): LFQuad's `dir = "LFQuad"` plus a backslash path loaded nothing on the server, and the
same path with forward slashes loaded; detail and counts are in `dayz-1-30-vehicles.md`. Write forward slashes.
Confirm with telemetry `ClassName()` ≠ base, and by comparing the script log's
`Module: World; loaded Nx files` line with a run without the mod. For telemetry to read the EXACT
config-class name, the leaf class `class <Mod> extends <Mod>_Base {}` is required.

### The "Get in" radial — blocker is GEOMETRIC (collision component + crew proxy), NOT `GetCrewIndex`
A missing `GetCrewIndex` override is not the cause: MercedesAMGLF resolved DRIVER get-in in game without
touching `GetCrewIndex` (telemetry `comp=0 crewIdx=0`, the native mapping works). The full mechanism is in
Addendum 2026-06-27 "Crew get-in" above. Summary:

`CrewPositionIndex(componentIdx)` (native, transport.c:179) resolves the seat by the **collision component
hit by cursor raycast in ViewGeo** (`ObjIntersectView`, actiongetintransport.c:45-46) — NOT by
`GetCrewIndex` nor by memory points. The two real blockers, both geometric:
- an **occluding solid box** in ViewGeo (e.g., a central "spine") → cursor hits it BEFORE the seat
  cube → no get-in. Fix = delete it (MercedesAMGLF driver, in-game).
- each seat = its **own clean, dedicated ComponentNN** (closed cube, dual-tag); painted onto a multi-component
  grid → "always driver", codriver is never hit (LFQuad).
- pose comes from **CANONICAL crew-proxy triangle** (edges ~1.0/2.0), not from tiny `add_proxy(scale=0.1)`.

`GetCrewIndex` and the door system are NOT the path for basic get-in (both
LFQuad and MercedesAMGLF show the driver radial without them). A forced seat entry does not prove
get-in: an MCP `vehicle_enter` call puts the player in the seat and bypasses `ActionCondition`, so a
car on which the radial was never observed is a FALSE-GREEN. Observe the radial itself.


### DECISIVE codriver blocker = INWARD-wound seat ComponentNN + point flags `0x0000003F`
"Clean seat cubes, all faces outward" is NECESSARY BUT NOT SUFFICIENT, and the door system is not needed. The rule, the measurement on the sealed vanilla control, the minimal way to apply it and the crew-probe gate are in "CRITICAL EXTENSION (2026-06-28)" and "MercedesAMGLF CONFIRMATION + refinements" above. Codriver get-in works on SUB_BRZ (in game) and MercedesAMGLF (headless probe) with it. For any new py3d-built car apply it up front; do not discover the blocker in game.

### Inverted wheels: measure axis in .p3d BEFORE setting `angle1` (offline check, predicts bug without in-game)
`model.cfg` wheel `angle1` must match `dir` of each `wheel_X_Y_axis` (2 points in Memory LOD):
- UNIFORM axes (all 4 with same X sign) → UNIFORM `angle1` across all 4 (LFQuad `(1,0,0)`; SUB_BRZ `(1,0,0)`→`-6.283`).
- MIRRORED axes (opposite X sign L/R) → alternating L/R `angle1` (the example 4x4's convention).
Applying the right-side flip on uniform axes spins the right side backwards.
**Audit 2026-06-27:** MercedesAMGLF had uniform axes `(-1,0,0)` but alternating `angle1` → inverted
wheels, predicted OFFLINE. Fix = uniform `angle1`. Offline check: `py3d` → `dir` of `wheel_X_Y_axis`, compare
X signs between L and R (reusable script: `skills/dayz-vehicles/scripts/audit_getin_wheels.py`).

### LOD ladder for a shell+proxy car (re-import of decimated model)
The body is split into shell-core (carpaint/glass/lights, direct in LOD) + N `mb_` proxies (each under the
per-model vertex ceiling of `binarize-vertex-budget.md`). For a ladder of visual LODs from a model decimated by the artist:
- Run the proxy and shell builders PER LOD with decimated regions and proxies with
  suffix (`mb_chassis_lod1`, etc.). LODs whose body binarizes under that ceiling → DIRECT geometry (no proxies); those
  exceeding (typically LOD0/LOD1/LOD2) → shell+proxies.
- Decimate with **headless Blender** (`--background --python`, modifier Decimate COLLAPSE, `use_collapse_triangulate`),
  per-object to preserve groups; re-split by group to regions. Exclude wheels from body (handled via wheel proxy).
- **Keep support LODs (Geometry/Memory/ViewGeo/FireGeo) from the DEPLOYED .p3d**, not from the donor model —
  ensuring any subsequent edit to those LODs survives (e.g., get-in patch in ViewGeo). Transform (scale)
  IS measured against the stable donor model (not against own output: shrinks ~3%/rebuild).
- Gate PER LOD and PER proxy on binarize's verdict, not on a fixed number (see `binarize-vertex-budget.md`
  item 4: the 65535 resolved count is a false friend; the measured cliff was 46,133 triples); the car's verifier must stay green.
- First gentle step (e.g., −20% LOD0→LOD1) preserves close-up quality; accelerate after. Measured ladder on
  MercedesAMGLF: 5 LODs 182k/145k/73k/23k/7k + shadow.

## Occluder membership beats component granularity (correction, added 2026-08-31)

The closed-car rule above still stands: when no body ViewGeometry shell is needed,
omit it and keep only the dedicated seat components. When an open vehicle intentionally
needs a shell occluder, however, small components alone do not prove that the seats are
reachable. A finely split cloud can still block every ray if detachable doors or
interior pieces were assigned to the shell.

Build that occluder from shell-owned surfaces. Exclude detachable panels and interior
chunks that have their own functional owner. Gate two independent defects:

1. Calibrate the largest component's bbox-volume / shell bbox-volume ratio against
   a working control and a monolithic-body red fixture. This detects the single body envelope.
2. Cast bilateral door-side ray fans toward every seat component. The first hit must be
   that seat's exact one-to-one `componentNN`. Include separate red fixtures with door
   surfaces and with interior surfaces left in the shell; both must fail.

The ray fan is an offline geometric discriminator with two-sided triangles. It does not
predict engine backface culling, so a green result still needs the in-game get-in cycle.
This correction narrows the earlier closed-car-specific statement that body occlusion was
a red herring; it does not change that measured root cause or restore a shell where none
is required.


## LOD frame parity uses area moments, not raw vertex PCA (added 2026-08-31)

**[HISTORICAL OFFLINE MEASUREMENT; CALIBRATE PER MODEL]** A decimator preserves
surface while changing vertex density. Raw vertex centroid and PCA can therefore
report a frame change on a correct LOD (measured false drift:
about 0.035 m and 18°). Compare `LODn` with `LOD0` using area-weighted centroid and
covariance, orient each principal axis with the area-weighted third moment, and
return `INCONCLUSIVE` when an axis or its sign is degenerate. Calibrate angular and
centroid tolerances on a working pair from the same model family; measured examples
of 2° and 0.02 m are not universal defaults. Enumerate the LOD files from the host's
`proxy:` selections rather than a hand list.

## Modern `Car` ground-contact correction (added 2026-08-31)

Both LOD tables above say the same for a modern
DayZ `Car`: do not carry or add a `LandContact` LOD. Ground contact uses the tyre's
wheel collider plus the small `wheel_*_damper_land` component in Geometry. Treat a
different vehicle archetype as a separate contract and calibrate it against a
working control before introducing any contact LOD.
