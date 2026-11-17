# Imported meshes, orientation and winding: invariants

Checks for a vehicle body that comes from an OBJ, a glTF or a game rip: mesh and UV health, mirror against rotation, winding, the nose direction, cabin alignment and what offline visual gates cannot see.

> Status: field notes measured on third-party mods, each named in its entry (SUB_BRZ, SUB_WRXSTI, MercedesAMGLF, LFQuad, LFQuad2, LFQuad3, Arma2Quad, LFHeli). Those measurements were not repeated here. A citation written with its full `P:\` path was opened on the vanilla data of this repo. A citation without `P:\` keeps the line number the note was written with, for the DayZ build that entry names, and is not yet checked on `P:\`: Grep for the symbol before relying on the number. Where they were opened, the `carscript.c` numbers matched this repo's `P:\` (a 1.30 build), the `transport.c` numbers sat 3 to 9 lines lower than written, and the `DZ\vehicles\wheeled\config.cpp` numbers differed. Tags such as SP-205 or LL-244 are the notes' own lesson numbers. Paths such as `<vehicle-import>\...` or `SUB_BRZ_dev\...` point into those mods' work folders, which are not part of this repo. "Invariant N", "preflight #N" and "#N" all mean the numbered invariants; `skills/dayz-vehicles/SKILL.md` lists which file holds each number.

## Vanilla anchors checked on `P:\`

- The third person vehicle camera sets `m_fIgnoreParentYaw` to `0.0` (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercameravehicles.c:189`), which is why the seated player's yaw decides what reads as forward.
- The vanilla control these notes measure against is `P:\DZ\vehicles\wheeled\civiliansedan\civiliansedan.p3d`. It is a binarized ODOL, which py3d cannot read, so the nose, hub and proxy numbers quoted from it were not measured again here.

## Mirror or rotation: check all three axes before declaring a model mirrored (added 2026-08-02, LFHeli HH-60G)

**Mirror-vs-rotation invariant (added 2026-08-02, LFHeli HH-60G):** before you declare an
imported model "mirrored" and reach for the `det=-1` import rule, **check all THREE axes**. A table
of memory points cannot tell a reflection from a rotation on its own — points have no handedness, so
only the PATTERN of sign flips does:

**The general test is the SIGNED VOLUME, not counting axes.** Take four LABELLED, non-coplanar
corresponding points (A,B,C,D) and compute `det[B-A, C-A, D-A]` on each side. An individual point has
no handedness, but a labelled tetrahedron does:

- signed volume **keeps its sign** -> proper transform (`det=+1`) -> rotation. The model is FINE and
  `det=-1` would ADD a mirror that is not there.
- signed volume **flips sign** -> improper transform (`det=-1`) -> the reflection is real; apply the
  `det=-1` import rule plus pseudovector (`-S.n`) normals.
- volume ~= 0 -> your four points are coplanar: pick others, the test says nothing.

Counting inverted axes is only the axis-aligned shortcut of that test, and it is easy to misread:

| axes flipped (axis-aligned case only) | what it is |
|---|---|
| ONE inverted, other two intact | reflection |
| TWO inverted, third intact | rotation of 180 deg about the third axis |
| all three inverted | point reflection = 180 deg rotation + mirror; decompose before acting |

Real case, and it nearly cost a full re-emission of 16 `.p3d`: one session measured only X, saw the
sign flipped and concluded "mirrored"; the user authorised de-mirroring. Measuring Z too showed
**38/38 points with X and Z inverted and Y intact** — a 180 deg yaw (det=+1), which is the pipeline's
normal convention, not a defect. Control that settled it: the sister airframe that already flies
in-game has the SAME convention (nose at -Z in the file). Applying `det=-1` would have introduced a
real reflection where none existed and broken a winding policy already verified in-game. The
review that settled it did exactly the tetrahedron test: `+6.076679` in file against `+6.076514`
in runtime, ratio `+0.999973` - same sign, proper transform, argument closed without a game cycle.

**Say what the test does NOT cover.** A proper file->runtime transform does not rule out a mirror
baked in EARLIER (before the `.p3d`, in the source mesh or the exporter) nor a pre-mirrored UV
island, which is a texture defect and shows up as backwards lettering with the geometry perfectly
correct. Those are separate investigations with separate evidence; do not let a clean parity check
close them.

**Corollary worth more than the rule — prefer RELATIVE measurements.** A comparison made *within one
file, through one reader* is robust to whatever axis convention your reader uses; an absolute
file-vs-runtime comparison is not. "The 10 crew proxies carry a frame rotated 180 deg from the 15
piece proxies" is sound even if you never establish which handedness py3d reports, because both sides
went through the same lens. When a diagnosis can be phrased as a relative comparison against a
control inside the same asset, phrase it that way and it survives being wrong about conventions.

## Texture or mesh: discriminate before auditing the texture pipeline (added 2026-07-27)

"The textures look wrong" on an imported vehicle is a symptom with at least three unrelated
causes, and auditing the texture pipeline is the **most expensive** way to find out which. Run
this ladder first; each rung is minutes, the full audit is sessions.

1. **Audit the UVs, not the textures.** Exact SAT overlap + island count + density
   (`uv-clean-atlas`, `uv_audit.py`). Overlap > 0, atomised islands (2-4 faces each) or wildly
   uneven density means the problem is upstream of any `.rvmat` — no material wiring fixes it.

   **No-overlap means an exact `SAT=0` (SP-214, added 2026-08-31).** A Monte-Carlo
   estimate has a measured nonzero floor, so its displayed `0%` is not proof. Route
   vehicle UV repair to `uv-clean-atlas` and use its current chart/SLIM/fold/SAT and
   semantic-packing contract; `PartUV` is not the vehicle default. One anti-fold
   round is a cost target, not a correctness exception: run the same exact SAT
   detector after every round, continue when it is nonzero, and block any mesh that
   does not reach zero. This pack owns the routing and acceptance gate, not a second
   copy of that implementation.

2. **Ask where the mesh came from.** A decimated rip cannot yield game-ready UVs: the cause is
   topology, not the unwrap algorithm or the texture route. The fix is retopo (bake the high-poly
   onto a clean low-poly), and no amount of pipeline correction substitutes for it.
3. **Render the same material on a known-good control.** If a vanilla-derived control looks right
   with the same route, the pipeline is exonerated and the defect is in this asset.
4. **Only now** audit `.rvmat` stages, `_co/_nohq/_smdi` paths, `.paa` conversion and
   `hiddenSelections` — see dayz-texture-pipeline, and its
   vehicle materials and colour variants reference for the vehicle-specific shader choice
   (Super where faces carry a `_co`, NormalMapSpecularMap for constant-colour parts, tiled detail
   for overlapping or un-baked UVs).

**Cost rule**: if two rounds of pipeline auditing come back clean, "the texture is applied wrong"
is REFUTED — change branch instead of running a third. An audit that exonerates the pipeline is
evidence about where the bug is NOT, and repeating it produces no new information.

Evidence for the rule: on LFHeli OH-1, F6 ran a double audit that exculpated the entire offline
chain (UVs identical across blend/MLOD/ODOL, old PAA identical to new, `rvmat uvSource=tex`, zero
`hiddenSelections`, no faces inside the watermark box) — the textures were never the problem. On
SUB_BRZ the documented root cause was the decimated rip's topology, reached after six rounds and
a pivot to a human artist. In both cases the ladder above would have branched away on rung 1 or 2.

### Rip-specific rung 0 — a "paint" material in the source has NO diffuse; never substitute a livery sheet (added 2026-07-27)

Before running the ladder on a **ripped** vehicle (GTA, ripped racing-game, any game rip), census which source
material each face carries and what the import mapped it to. Game rips colour the body through the
host game's **paint system**, not through a texture: in GTA those materials are
`vehicle_generic_smallspecmap*` / "primary" and their diffuse is legitimately **absent or a
zero-byte file**. An importer that needs *some* texture per face will silently fall back to whatever
is available — and if what is available is the model's **livery/decal sheet**, the result is signs,
numbers and camo stamped across the whole fuselage. The symptom reads as "the UVs are wrong" or
"textures are crossed", and both readings send you down the expensive branch.

- **Discriminator (minutes)**: count faces per `(source material -> texture)` pair. A single texture
  carrying a large share of the model, especially a decal/livery atlas, is the signature. Cross-check
  the source file size on disk: a **0-byte** or missing DDS proves the fallback fired.
- **Fix direction**: those faces want a **flat colour `_co`** (the host game's paint slot has no DayZ
  equivalent), not the decal sheet and not a re-unwrap. Their UVs were never meant to address a
  texture, so no UV work is involved.
- **Measured evidence.** LFHeli HH-60G (2026-07-27): `hh60g_sign_1_co.paa` — a 22.4 MB livery sheet —
  carried **23,716 / 35,385 faces (67%)**, of which **8,695 (24.6% of the model)** were pure fallback
  (7,568 of the body's `[PRIMARY]` material plus all four doors), with
  `vehicle_generic_smallspecmap3.dds` confirmed **0 bytes** on disk. The user's independent report was
  "things and colours drawn where they don't belong". The OH-1 line hit the same class separately
  (rotor blades wearing camo and a registration number) after the PAA route had been exonerated.
- Status honesty: the diagnosis is measured; the flat-colour fix was **not yet confirmed in-game** at
  the time of writing — treat the fix direction as unverified until a cycle closes it.

## Invariant 0: mesh and UV health before anything else (SP-052)

**Gate #0 — mesh + UV health BEFORE anything else (SP-052).** For ANY imported model (ripped or not),
the FIRST step is a mesh+UV audit, because a broken mesh produces false downstream diagnostics (a
"double wall" that was mirrored UV on a single wall; a "convexity" issue that was open design-boundary
edges). (a) audit `mesh_health.py` (boundary / non-manifold / dup-verts / dup-faces / winding per
piece) + `uv_audit.py` (islands / overlap / density / mirrored); (b) sanitize with an ADAPTIVE weld
(ladder 0.5→0.01 mm; gates: NM must NOT grow + UVs preserved — a blind 0.5 mm weld FUSES
legitimately-touching pieces and CREATES non-manifold); (c) unwrap BY SECTIONS per
the UV mapping note of the model material (source note `uv-mapping-dayz.md`, sections 0.5 and 5); (d) gates: overlap ~0% for bake, uniform density, atlas
legible by a human, checker render with SMOOTH shading (flat shading + grid raster read as a false
"low-poly/blurry"). Tools in `LFQuad_dev\tools\` (mesh_health.py, mesh_sanitize.py bpy-headless;
uv_audit.py py3d) — portable to any vehicle. → the same UV mapping note, and winding #10(f).

## Invariant 0b: when LOD1 and LOD2 come from a decimate modifier, audit its output

**Gate #0b — when LOD1/2 come from DECIMATE instead of an artist, audit the modifier's OUTPUT
(added 2026-08-06, MercedesAMGLF).** No artist is now the normal case, so per-object COLLAPSE +
planar DISSOLVE is the default LOD path. The modifier leaves **loose vertices** — vertices no
triangle indexes. Every count-based gate stays green (triangles, resolved, identity, monotonicity,
frame parity), and the streams ship broken: a per-vertex extract loop driven by `mesh.loops` never
reaches a loose vertex, so whatever the array was initialised to is what gets written. Initialised
to `(0,0,0)` → **zero-length normals in NORMAL.bin**. Measured: source had 0 loose in 224.700 verts;
after decimation, 786 at LOD1 and 4.024 at LOD2 — plus 16 normals of length down to `3e-6` that a
`> 0` usability test happily passed. Three checks close the whole class:
- delete loose verts after every decimate (`bmesh.ops.delete(bm, geom=[v for v in bm.verts if not
  v.link_faces], context="VERTS")`). NOT one of the three forbidden calls — it removes only geometry
  no triangle references. Skip the bmesh round-trip entirely when there is nothing to delete, so
  must-keep pieces never pass through it.
- assert every emitted normal is unit length and normalise on emission. The real cut is **0.5**, not
  0: a unit normal survives float32 within ~1e-7 of 1.0, so anything shorter is a cancelled sum.
  Substitute from NEIGHBOUR normals, never from `poly.normal` — if the import transform negates an
  axis it is a mirror, and the winding-derived normal points the opposite way (see #10 winding).
- assert every index falls inside its own piece's vertex range. No count gate sees an out-of-range
  index; it explodes at assembly.

**Gate corollary — a drift number that mixes classes is not a measurement.** Split survivors into
INTACT (incident-triangle set identical to LOD0 → drift MUST be ~0; any drift here is a real defect),
RECOMPUTED (topology changed → drift is legitimate) and DEGENERATE (counted, never averaged in).
Mixed together, a p99 of `90.00°` hid a real defect AND hid that untouched geometry was clean at
≤0.26°. An exact round angle is a fingerprint, not a result: `90.00` is `acos(0)` = a null vector on
one side. Match survivors on a ~1e-4 m grid, not 1e-6 — positions are written as float32 and a 1e-6
grid drops about a third of the untouched vertices at random, which is why the samples looked tiny.

## Position is a candidate bucket, not identity (SP-163)

**Position is a candidate bucket, not identity (SP-163, added 2026-08-31).**
The grid above may find candidates, but a seam can place distinct normal/UV corners
at the same coordinate. Pair intact data by a carried source vertex/corner and
primitive ID. If that identity was lost and a bucket is non-unique, return
`INCONCLUSIVE`, not PASS or FAIL. Run source against itself through the same matcher
and require approximately zero residual before trusting any product comparison.

## Invariant 7: keep the raw glTF winding verbatim

**Imported-model winding: keep the RAW glTF winding VERBATIM — NEVER orient to a normal oracle
(authored/`__N`) nor to a radial/centroid heuristic (see #10j).** The pipeline's `__N` was never
authored (`rip_p2_group.py:110,131` — smooth normals of the pre-mirror winding) and `orient_authored`
inverted EVERY piece; repair only the ~0.5% source-inconsistent FACES by MAJORITY flood-fill per
connected component, AFTER de-dup (#10e). Blender backface-cull render = HINT only (its convention
false-greened once — it shows the +cross side, the engine renders the ANTI-cross side); in-game render
is the gate. → #10(j) + `SUB_BRZ_dev\reviews\2026-07-02-s20-plan-reimport-unico-v2.md`.

## Invariant 10: offline visual gates that lie, and the one winding rule

**Imported-car offline VISUAL gates that LIE — the #7 family (offline geometry heuristic != in-game truth).** The per-session changelog of sub-entries #10(a)-#10(o) (steering-axis fit, single-sided see-through, debug fluids, raycast oracle, rip duplicate faces, per-piece winding uniformity, ViewPilot interior, bright-triangle shading seams, the import-orientation saga, glass occluder twins, foreign-LOD material transfer, gap skirts, hub-lift decoupling, get-in-preserving patches) lives in **`visual-gates-and-winding.md`** (s14->s23, SUPERSEDED entries archived there). The single operative winding rule stays here:
- **THE RULE (import orientation, #10j):** keep the raw glTF winding VERBATIM for ALL pieces (net rip→DayZ = `(-Fx, Fy+Y0, -Fz)`, det=+1, preserves the authored visible side end-to-end); stored MLOD normals = smooth(+cross) of the FINAL winding. NEVER orient winding to a normal oracle or to outward-of-centre. Repair ONLY source-inconsistent components by MAJORITY flood-fill per connected component (never minority-area). `glass*int_a` panes are legitimate cabin-side glass (do not delete as z-fight). Full mechanism, measurements, and the SUPERSEDED (h)/(i) history: `visual-gates-and-winding.md` #10(j)/(f).
- **Winding is per profile (SP-217).** rip/vehicle with measured transform det=+1: preserve (`#10j`). Generic DCC import with no profile: dayz-model-pipeline Rule 12 (det=-1 map, face order kept, normals negated; no face reversed). The in-game A/B (SP-070) adjudicates correction; a lineage gate adjudicates preservation. Do not apply generic dayz-model-pipeline Smart UV / decimation / flip defaults to a vehicle. *(Aligned 2026-10-03 with Rule 12, measured in game 2026-10-01: the generic case read "Generic DCC import with no profile: flip visual by default (SP-071; proxies exempt).")*

## Invariant 11: vanilla forward is nose at minus Z, and the visual side of an imported car is not one block

**Vanilla forward convention is nose = −Z (ENGINE-NATIVE), and the "visual side" of an imported car
is NOT one homogeneous block — measure EVERY body proxy separately before any bulk rotation
(MERCEDES_AMGLF review 2026-07-03; convention verified offline on native data, the yaw-180 fix's
in-game gate pending).**
- Convention measured on the raw vanilla ODOL (NOT a debinarized MLOD, so no converter-flip doubt):
  sedan `light_1_1` Z=−2.387, `dmgzone_front` −2.355, front axle −1.655, exhaust at +Z (tail).
  Nose=−Z is engine data. (Side-finding: the debinarized sedan MLOD is sign-faithful to the ODOL.)
- Perceived-"forward" chain: the 3PP vehicle camera inherits the SEATED PLAYER's yaw (crew-proxy
  orientation, sim side) + an MS offset — `dayzplayercameravehicles.c:39-49,93-105`
  (`m_fIgnoreParentYaw` set to `0.0` at `:189`; on 1.29 the line was commented out, 1.29 `:194`), defaults `transport.c:652-663`. Headlights and
  hubs play NO role in what the player sees as forward. Traction sign is C++
  (`car.c:199-274` proto native) — inferred −Z from the working sedan; not script-readable.
- Symptom map: shell visual yaw-180 vs sim ⇒ 1st gear reads as "drives backwards" AND wheel
  proxies sit mirrored (−X,−Z) off their hubs, BOTH at once. Diagnose by comparing
  `dmgZone_front`/hubs (sim) vs headlights/wheel-proxies (visual) against nose=−Z.
> History of the superseded text: `history/superseded-family-b-rules.md`, section "Invariant 11".

- **CORRECTION to THE TRAP (added 2026-08-01, adjudicated from the applied fix's dated backups +
  in-game outcome — supersedes the "interior/dash/steering/occlusion correctly sim-aligned" claim
  above):** on the Mercedes those `mb_` contents were VISUAL-aligned (coherent with the yaw-180
  shell), and the executed fix had to rotate the ENTIRE cabin cluster — all 6 `mb_` contents +
  crew proxies (View/Fire) + `pos_driver/codriver(+_dir)` + `drivewheel(+_axis`, re-authored to
  the vanilla rake) — in a second same-day pass (backups `pre-visual-yaw180-2026-07-07\` vs
  `pre-cabin-align-2026-07-07\`: shell rotated, cabin still old), after a first shell-only pass
  per the 07-03 scope left the cockpit 180° off the body. The sim-aligned claim came from
  content-bbox reading plus validating `mb_steering` against a memory point of the SAME
  misaligned cluster (self-validation — the SP-132 "gate shares the producer's frame" shape).
  Rules that survive: (a) still measure each proxy separately, but adjudicate cabin orientation
  with ANATOMICAL PAIRS (seat↔steering-wheel↔column-rake↔driver side) against untouched sim
  anchors (hubs, dmgZones, engine memory) — never with mixed-content bbox or the cluster's own
  memory points; (b) the correct rotation unit is EVERYTHING that defines the visual+pose
  experience: shell + body proxies + crew proxies + `pos_*`/`drivewheel*` cockpit points.
  Post-fix coherence verified offline (anchors exact on hubs, LHD seat side, wheel 0.34 m ahead
  of seat, rake (0,0.516,0.857) vanilla-parallel) and live (Task 9 v64 PASS + manual drive
  2026-07-23, no inverted-drive or backwards-pose reports). Full adjudication:
  `MERCEDES_AMGLF_dev\reviews\2026-07-02-fable-review-plan-OUTPUT.md`.
  **R22 refinement (2026-08-01, Codex re-measured the same backups — narrows the rule above):**
  the "rotate the entire cabin cluster" adjudication is Mercedes-SPECIFIC; the durable rule is
  two-sided — (1) adjudicate cabin orientation with the anatomical pairs against untouched sim
  anchors, then (2) rotate exactly the adjudicated cluster IN EVERY FILE/LOD THE HOST
  REFERENCES, measuring each file, never presuming: the applied 07-07 fix itself MISSED the 12
  `mb_*_lod1/_lod2.p3d` referenced by the host's visual LODs 1-2 (byte-identical to pre-fix,
  hash-verified by two independent reviewers) — so mid-distance LODs still draw the body
  proxies in the OLD orientation. The original warning to measure every proxy separately
  SURVIVES; what was wrong was its Mercedes factual claim, not its method.

- Cheap steering-wheel check: if the `drivewheel_axis` memory pair is near-VERTICAL (Y-dominant
  direction), the wheel sweeps left-right like a wiper instead of rotating in its plane. The axis
  must be ~perpendicular to the rim plane (Z-dominant, some Y).
Evidence + probes: `MERCEDES_AMGLF_dev\reviews\2026-07-03-fable-review-b1b6-plan.md`.

## Invariant 12: white car (moved)

For family B this item now lives in the rip-vehicle-import skill, in its family B cookbook `cookbook-white-car.md`.

## Invariant 14: steering wheel against hands

**Steering wheel vs hands: measure rim-center delta AND plane tilt vs the control BEFORE moving
anything — the seat anim is the control's, so hands land on ITS wheel plane.** (added 2026-07-07,
SUB_BRZ s25 measured) SUB_BRZ: rim-center delta vs crew anchor already in parity (1-1.6 cm) but rim
tilt 15.8° vs sedan 31.0° → ±r·sin(Δ) = ±2.1 cm at r=0.159 = exactly the user's "top hand 2 cm
behind, bottom hand 2 cm in front". Fix = rotate the wheel PIECE about its own rim center to the
control's tilt and re-author `drivewheel`/`drivewheel_axis` memory points parallel to the new rim
normal (SUB_BRZ's axis was 38° off its own rim; the sedan's is exactly parallel — a misaligned axis
also wobbles the G5 wheel animation). Do NOT recline the crew proxy when the positional delta is in
parity. Reusable tool: `<vehicle-import>\s25_plan\measure_wheel_vs_crew.py` (fits rim by
outer-radial PCA; handles debinarized selections whose point-membership is lost via faces, LL-018).
Same open symptom on MercedesAMGLF — apply there.

## Invariant 29: a rig threshold on a measured axis needs its source declared for both members of a pair

**A rig threshold on a MEASURED axis must have its source declared for EVERY member of a symmetric pair — declaring it on one side leaves the other on raw measurement, and the build refuses months later (added 2026-08-16, SUB_WRXSTI T8.3 blocker).** The detachable-door rig requires `dir_y > 0.999` (`rip_p3_structural.py`), and a rip's placement tilt lands a door hinge just under it. The WRX profile fixed that for ONE door by declaring `hinge.axis_source.declared = assembly.alignment_build.doorRF`, an axis projected to vertical with its XZ midpoint kept — and the other door, declaring no `axis_source`, kept riding its raw PCA axis. Measured when the whole structural build refused: codriver `|dir_y| = 1.0000`, driver `|dir_y| = 0.998575` = **3.059°**, i.e. one door 3 degrees from a threshold the other met exactly. This is `DZ-R7` (trace the invariant to all call-sites) applied to profile DATA rather than code, and it is invisible until the gate fires, because both doors look declared and only one is. Two riders paid the same day: (a) project each side keeping **its own** XZ midpoint, never mirror the other door's — the two sides of a rip are not symmetric, and mirroring here would have moved the hinge 3.7 cm (driver x +0.849278 vs codriver x −0.811827); (b) relaxing the threshold to admit the one bad case is the tempting fix and the wrong one — the threshold exists so a door does not open tilted, and lowering it for one car lowers it for all.

## Invariant 33: numbers cannot see proxy colour or orientation

**A gate lane measuring only numbers is blind to proxy color and orientation, and the only instrument seeing them is an eye in front of an ASSEMBLED render (added 2026-08-16, SUB_WRXSTI).** Existing names, preserved faces, matching hashes, and complete seat→door→slot matrices: all of that passes green on a monochrome car with reversed wheels. Measured: WRX arrived in PBO with 64% of its faces in ONE material and entire interior in another (import recorded `material_map: null` and sent 37 named parts — badges, mirrors, exhaust, jambs, skirts, underbody, arms — into the paint bucket), with four wheel proxies written with IDENTITY matrix where vanilla writes TWO mirrored ones, one per side, and with 176 mm vanilla sedan wheel instead of its own. All four defects were found by user within minutes upon first seeing assembled car; none was visible to any gate. Three riders. (a) Render must be ASSEMBLED and with materials: loose grey parts reveal neither wrong color nor inverted rim — a `visual_sheet` drawing grey geometry per part already existed and caught nothing. (b) Human verdict is tied to sha256 of what was reviewed, or it rots: after a rebuild no one can tell whether THIS car or previous was approved, and gate must turn red from stale, not remain green. (c) Calibrate chirality with BRAND TEXT, not intuition: DayZ is left-handed and viewer engines are typically right-handed, so passing coordinates as-is is a reflection, and a mirrored car looks normal until a badge reads backwards. Honest trade-off: this DOES NOT replace in-game testing, it merely makes finding what is seen cheaper.
