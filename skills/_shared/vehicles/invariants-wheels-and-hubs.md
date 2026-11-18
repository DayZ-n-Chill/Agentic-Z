# Wheels, hubs and axles: invariants

Where wheel hubs live in the model, how wheel proxies line up with them, hub height against tyre radius, wheel facing, and the axle classes the engine counts.

> Status: the measurements below were taken in game or offline on mod vehicles, named in each entry; they describe those mods, not vanilla, unless a vanilla citation backs them. Every citation of a vanilla file was opened on `P:\` (a 1.30 build), whether it is written with its full `P:\` path or with the file name alone. A citation marked `1.29` gives the line in a 1.29 build, which is not on `P:\` and is not checked. "Invariant N", "preflight #N" and "#N" all mean the numbered invariants; `README.md` lists which file holds each number.

## Vanilla anchors checked on `P:\`

- The `CarScript` base names the hub of each wheel with `wheelHub="wheel_1_1_damper_land"` and its three siblings (`P:\DZ\vehicles\wheeled\config.cpp:297`).
- `CivSedanWheel` has `radius=0.34` (`P:\DZ\vehicles\wheeled\config.cpp:4762-4778`).
- Vanilla lists both `Front` and `Rear` inside every `Axles` override: the `RearDrive` template (`P:\DZ\vehicles\wheeled\config.cpp:494` to `:510`) and `OffroadHatchback` (`P:\DZ\vehicles\wheeled\config.cpp:1431` to `:1466`).
- `civiliansedan_mlod.p3d`, the vanilla control named below, is a debinarized copy of the vanilla sedan. It is not on `P:\`, and py3d cannot read the binarized `P:\DZ\vehicles\wheeled\civiliansedan\civiliansedan.p3d`, so the hub, proxy and matrix numbers quoted from the sedan are not checked on `P:\`.

## A faithful import does not mean the pieces line up (added 2026-07-27)

**A bit-exact import and correctly-fitting pieces are different properties.** When a model is
assembled by script, each piece is placed at a **procedurally computed anchor** (centroid, bbox
centre, a reference point). If that anchor diverges from the real reference, the pieces sit wrong
while every import check passes. Seen on three vehicles (TestMercedes, TestCoupe, TestHeli):

- TestMercedes: the 28 wheel proxies sat **-0.240 m in X** from their Memory hubs. Fix: measure
  the offset with py3d and shift only those triangles (max error 0.0 m afterwards).
- TestHeli OH-1: import fidelity 12/12 at max 3.2e-7 m, and the `SEATS` procedural anchor still
  diverged **583 mm** from the source mesh.

**Gate before declaring an assembly good**: for every proxy, measure its anchor against the real
reference (the matching Memory point, or the source mesh position) and assert the delta is ~0.
Import fidelity, digest equality and structural diffs do NOT catch this — they compare the piece
to itself, not to where it belongs.

**Do NOT "fix" it by adjusting the pipeline transform.** That is the intuitive move and it is a
false fix: it displaces everything else that was already correct. Correct the individual anchor.

**False friend — `autocenter=0` is not this bug.** It is a real and separate requirement (the
engine recenters LODs by bbox without it, displacing collision ~20-25 cm from visual; see
`_shared/models/generated-model-rules.md` and `dayz-p3d-audit`), but it does not cause or cure anchor divergence.
TestMercedes spent a full RCA on that hypothesis and closed it as unproven: adding `autocenter=0`
to all 18 proxy LODs changed nothing geometric, and the protrusions and see-through were already
present in the earlier baseline. Do not re-run that investigation.

## Invariant 5b: wheelHub names a Geometry and Memory selection, not the visual wheel

**`wheelHub` names a GEOMETRY/MEMORY selection, not the visual `wheel_X_Y` — and the visual
`wheel_X_Y` IS the proxy's own triangle under a second name (added 2026-08-07, TestMercedes).**
`class Wheels { class Left { wheelHub="wheel_1_1_damper_land"; } }` resolves to a selection that
lives in Geometry `1e13` (a ~0.20 m hub box) and Memory `1e15` (1 point) — vanilla
`DZ\vehicles\wheeled\config.cpp:297`. It is NOT the `wheel_X_Y` selection on the visual LOD.
Measured on two independent cars: that visual companion has the SAME centroid and the SAME bbox
as its `proxy:<path>.NNN` selection, i.e. it is one triangle carrying two names (vanilla shows it
as 1 face too). Consequences, each of which cost a session:
- **A gate of the form "proxy anchor -> companion centroid == 0" measures nothing about the wheel.**
  It computes `|anchor - centroid|` of a single triangle, which is a pure function of that
  triangle's SIZE. Measured on the same model: 0.131757 m for a 0.339x0.204 triangle vs
  0.000745 m for py3d's canonical `scale=0.001`. Against the real hub both artifacts read
  **0.000000 m**. Point the gate at `wheel_X_Y_damper_land`.
- **Proxy triangle size bakes NO scale.** The frame is derived from UNIT vectors
  (`derive_proxy_frame` in `scripts/tools/py3d/py3d/__init__.py`), and vanilla's binarised proxy
  matrix is orthonormal (`|aside|=|up|=|dir|=1.000000` on `civiliansedan.p3d`, ODOL v54 when measured; the copy on `P:\` carries version 56 in its header). A 1 mm
  canonical triangle and a 0.34 m one place the same wheel; TestCoupe shipped on `scale=0.001`.
  Do not "fix" a small triangle.
- **Vanilla reference, if you need one:** `civiliansedan` puts the hub **0.106334-0.107333 m
  INBOARD** of the wheel proxy, the whole delta in X. Hub coincident with the proxy (0 m) is
  tighter than vanilla, not a defect.
- **Before matching a magnitude to another open debt, decompose it by AXIS.** 0.1318 m was read
  as "the wheel drawn 13 cm off its simulated position" because it resembled a 0.136 m track
  debt; the 0.1318 lives entirely in Y/Z (`dX = 0.000000` exactly on all four wheels) and the
  track debt lives entirely in X. Orthogonal — the resemblance was numerology.
- **Read a gate's PRODUCT verdict from a run WITHOUT its negative fixtures**, then repeat it on
  the known-good artifact as a control. Run with `--negative-fixture` and the fixture's
  deliberate reds (yaw-180 families, stripped companions) interleave with the product rows and
  read as product failures.

## Invariant 5c: owner-only driving hitch, hub clearance and LandContact

**Owner-only driving hitch: audit hub-ground clearance and remove `LandContact`
before blaming scripts (added 2026-08-31).** The driver owns the physics
solve while a passenger interpolates, so smooth passenger motion does not clear
collision geometry. Working DayZ car controls use the tyre's PhysX sphere plus a
small `wheel_*_damper_land` Geometry box (about 0.20×0.22×0.22 m) and no
`LandContact` LOD. Require `hub_y - mounted_tyre_radius` to exceed both
`Suspension.travelMaxUp` and `travelMaxDown`. A wheel-sized hub or retained legacy
`LandContact` points at the tyre plane can strike terrain every bump and make the
owner's solver hitch. `ObstacleGenerator { carve=1; }` and visual face count do
not discriminate this defect; a heavier known-good control refutes them.

## Invariant 6: measure the axle in the model before setting the wheel angle1 sign

**Wheel `angle1` sign: measure the axle in the `.p3d` BEFORE setting it.** An offline check predicts
reversed spin without an in-game cycle. → `build-packaging-and-debug.md` §2-3.

## Invariant 15: hub level uses the radius of the wheel you mount

**Hub level must use the radius of the wheel you actually MOUNT, not the rip's rim.**
Hypothesis with numbers, not yet confirmed in game. (added 2026-07-07, TestCoupe)
TestCoupe profile `WHEEL_R=0.3637` (source-game rim) while the mounted wheel is `CivSedanWheel` radius 0.34
(`P:\DZ\vehicles\wheeled\config.cpp:4762-4778`) → 2.4 cm hub-vs-radius mismatch, same order as the
observed damper rest −4.3/−5.6 cm ("wheels slightly up"). Day-1 check: `WHEEL_R == mounted-wheel
radius` or document why not.

## Invariant 15a: a wrong hub level spawns sunk and corrects itself when a player mounts

**The symptom of a wrong hub level is "it spawns sunk and corrects itself once a player
mounts" — and vanilla parks the hub ABOVE the tyre radius, not level with it (measured
2026-09-09, Arma2Quad; offline, in-game pending).** Invariant 15 says to match the
mounted wheel's radius but gives no control value and no way to recognise the defect from a
user report. Both, measured: the quad's four `wheel_*_damper_land` sat at `cy=+0.3231` with a
mounted wheel of `radius=0.350149`, i.e. **hub_y − radius = −0.0271**; the control
`civiliansedan_mlod.p3d` sits at `+0.3627` against `CivSedanWheel radius=0.34`
(`P:\DZ\vehicles\wheeled\config.cpp:4778`), i.e. **+0.0227**. Sign is the whole diagnosis:
negative puts the wheels under the terrain at spawn and the settling suspension lifts the body,
which reads to a player as a sync bug; vanilla's positive margin spawns slightly clear and drops.
Confirm the config `radius` against the wheel MESH before touching the body — measure the
outer radius in the plane perpendicular to the spin axis (here 0.3501/0.3502, so the config was
right and the hub was wrong).
**Fix the ORIGIN, not the hubs.** Translating the whole model leaves every body-to-hub relation
intact, so the settled pose is unchanged and only the spawn pose moves; raising the hubs alone
changes ride height by the same amount and breaks a pose the user already accepted.
**And measure `autocenter` instead of fearing it:** the warning that the engine re-centres a LOD
lacking `autocenter=0` did NOT apply here — 10 of 12 LODs lacked it, with bbox centres 0.62–1.63 m
off origin, and the model renders aligned in-game, so a global translation survives. If it were
re-centring, those LODs would already be scattered by up to a metre relative to Geometry.

## Invariant 15b: wheel mesh facing needs an asymmetric witness

**Wheel-mesh facing needs an asymmetric witness, not a symmetric bbox (added 2026-08-31).** Split wheel points by the sign of the mesh's shortest axis
and compare minimum radius in the perpendicular plane. The closed exterior face
reaches the hub (`rmin≈0`); the open interior begins near the rim. A negated bbox
range passes before and after a 180° turn and is therefore tautological. For
the measured x-axle wheel, correct a reversed side with the 180° Y rotation
`(x,y,z)→(-x,y,-z)` and rotate points and stored normals together. Calibrate the axis-to-side mapping on an independently
known-good mounted wheel, never on the candidate, then repeat the measurement on
the wheel blob extracted from the deployed PBO.

## A componentNN-tagged hub is useless in the wrong LOD (added 2026-08-29, TestQuad2, an Arma 2 OA ATV port)

Invariant 4 (`invariants-get-in-and-seats.md`) requires seats and hubs to carry the dual-tag `componentNN`. It states
WHAT tag, not WHERE. The other half --that selection must live in **Geometry** LOD-- is
what failed on this port, and what a port inherits from donor unknowingly.

Engine signature:

    ENTITY       : Load entity type '<Class>'
    PHYSICS   (E): Won't simulate, wheel wheel_1_1_damper_land has no proper selection in geometry

Consequence: `CreateObjectEx` returns **null**. Vehicle **fails to spawn**; it is not merely looking wrong.

**Where hubs go, measured on THREE working models**, not just one:

| model | `*_damper_land` in Geometry | LandContact LOD |
|---|---|---|
| TestQuad (working reference) | 4, with faces and dual-tag `componentNN` | **does not exist** |
| `civiliansedan_mlod.p3d` (vanilla) | 4 | **does not exist** |
| a second working quad bike mod | 4 | **does not exist** |
| TestQuad2 (port, failed to spawn) | **0** | exists, and there all 4 were, with 1 point and 0 faces |

**The port trap:** an Arma 2 MLOD has a LandContact LOD, and a port leaves the contact
points there because the names match. DayZ does not read the hub from that LOD: `wheelHub` in
`config.cpp` resolves against **Geometry**. Both symptoms are the same error: a selection with
1 point and 0 faces cannot carry `componentNN` either, because it has no faces to tag.

**5-second check before any in-game cycle:** every `wheelHub` that the config names must exist in
the Geometry LOD, with faces, and carry both tags. Take the list of hubs from the model's own
config, which names them, not from a hand-written list.

A process warning, and the costly half of this entry: the signature of this error was once
written only in an archived rule, which carried no authority, so nobody read it as a rule. When
you archive a rule, check that the part still in force keeps BOTH questions: what, and where.

**Confirmed in game the same day.** After the four selections were moved to the Geometry LOD
(names put on geometry that ALREADY existed, without adding a single face), the vehicle **spawns**:

    [TestQ2-TEST] TestQuad2 type=TestQuad2 pos=<13282.5, 7.27, 6883.2> wheels=4 fuel=1

`CreateObjectEx` returns the object instead of null, with all four wheels attached. So the missing
Geometry selections were not only a necessary fix: they were **sufficient** for the engine to
build physics. That is worth knowing because the engine stops at the FIRST error, so before the
test it was possible that more blockers lay behind it.

**Measured trade-off, to watch when driving:** in a port, the only geometry that belongs to each
wheel is usually **the entire wheel** (here 0.198 x 0.599 x 0.599 m), against the reference hub
box (0.20 x 0.22 x 0.22 m). Using it is the honest choice, because inventing a small box changes
the Geometry LOD mass, but it leaves a collision component about 3 times larger on two axes. If
the suspension behaves strangely or the vehicle feels anchored after the fix, suspect that size
first, not the config.

## Every axle must be listed in an Axles override: what the engine enumerates is not inherited (added 2026-09-11, Arma2Quad)

A derived vehicle class that redeclares `class Axles: Axles` and lists only one axle loses the
other one entirely - not its values, the axle itself. Measured on three drivetrain variants that
declared only `class Rear: Rear`: in game all three reported `wheel_count` 2 against 4 on the
control, sat nose-down (pitch -7 to -10 deg against -0.3) and would not move. The user saw it
before the diagnosis did: *"the front wheels are buried and they do not turn"*. The fix is one
line per variant: `class Front: Front {};`.

The discriminator, which is what makes this reusable: in the SAME override `Clutch`, `Engine`,
`Gearbox` and `Steering` were inherited without being declared, and those variants kept engine,
gearbox and steering. Inheritance works for children the engine looks up BY NAME; it does not
for children the engine ENUMERATES because their names are free - the axles under `Axles`.
Vanilla never exercises the hole: every vanilla car lists both `Front` and `Rear` in every
override (`DZ\vehicles\wheeled\config.cpp:494-530`, `:1431-1466`), so copying vanilla hides it.

Nothing offline catches it: CfgConvert parses the config without a complaint and the script
linter says nothing. The cheap tell is to count in the engine what should be there -
`telemetry_read(mode="object_at").wheel_count` on the prepared fixture - before handing a build
to a human. A bare `fixture_not_ready` from `vehicle_prepare_fixture` is usually exactly this.
