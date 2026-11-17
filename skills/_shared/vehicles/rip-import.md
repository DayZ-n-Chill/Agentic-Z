# Ripped racing-game (source-game Grub format) to DayZ CarScript import

The rip import path in detail: what a per-car rip folder holds, which parts to include, how to derive dimensions and the transform from the locators, the structural LOD recipe, the first in-game spawn results and their root causes, textures, materials, wheels, glass, interior and doors.

> Status: field notes from one worked example, the SUB_BRZ build (2026-06 to 2026-10), with MercedesAMGLF, kt_roadkill, FC (Frontera Cars), LFQuad and a Tyson89 Landrover as controls. Those measurements and in-game results are the author's and were not repeated here. Sections are dated and later ones correct earlier ones; a block marked SUPERSEDED, RETRACTED or RESOLVED says which. The vanilla script line numbers in this file were opened on this repo's `P:\` (a 1.30 build) and corrected where they had moved; a number that follows a mod's own file (`unknown_40493.c:1017`, `rip_p2_group.py:110`) is the note's own. Tags such as SP-096 or LL-172 are the notes' own lesson numbers, and `CLAIM-...` tags are the notes' own claim register. Paths such as `<vehicle-import>\...`, `SUB_BRZ_dev\...`, `LFHeli_dev\...` or `AI/20_Knowledge/...` point into those mods' work folders and the author's notes, which are not part of this repo. "Invariant N", "preflight #N" and "#N" all mean the numbered invariants; `skills/dayz-vehicles/SKILL.md` lists which file holds each number. Skills of other parts of this import are named without a path (dayz-model-pipeline, dayz-test-ingame, dayz-texture-pipeline, dayz-mcp-verify, enforce-script-reference).

## Vanilla anchors checked on `P:\`

- Get-in has two gates: `CrewPositionIndex` at `P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetintransport.c:46` and `CrewCanGetThrough` at `P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetintransport.c:54`.
- The base `CrewCanGetThrough` returns false unless `CFGMODS_DEFINE_TEST` is defined (`P:\scripts\3_game\vehicles\transport.c:724`); the note was written with `:727-734`.
- `GetSeatAnimationType` raises "not implemented" in the base class (`P:\scripts\3_game\vehicles\transport.c:682`), and so does `GetAnimInstance` (`P:\scripts\3_game\vehicles\transport.c:662`).
- The sedan's `GetCarDoorsState` returns `DOORS_MISSING` when no door is attached (`P:\scripts\4_world\entities\vehicles\inheritedcars\civiliansedan.c:185`), and its `CrewCanGetThrough` override is at `P:\scripts\4_world\entities\vehicles\inheritedcars\civiliansedan.c:226`.
- The first-person vehicle camera `DayZPlayerCamera1stPersonVehicle` extends `DayZPlayerCamera1stPerson` (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercameravehicles.c:4`).
- `maxSteeringAngle` is 30 or 35 on the vanilla cars: 30 at `P:\DZ\vehicles\wheeled\config.cpp:1375`, 35 at `P:\DZ\vehicles\wheeled\config.cpp:5240`.
- `P:\DZ\vehicles\wheeled\civiliansedan\data\glass.rvmat` is as the texture section describes it: ambient and diffuse alpha 0.75, `renderFlags[]` holding `"noZwrite"`, the Super shader, and `gazglass_nohq.paa` in `Stage1`.
- The vanilla proxy models the notes reuse exist under `P:\DZ\vehicles\wheeled\civiliansedan\proxy\`: `sedanwheel.p3d`, `sedanwheel_destroyed.p3d`, the four `sedandoors_*.p3d` and `prox_int.p3d`.
- The proxy class and the model file name are tied as the s37 section says: `ProxySedanWheel_destroyed` (`P:\DZ\vehicles\wheeled\config.cpp:23981`) names `sedanWheel_destroyed.p3d` two lines down.
- `CivSedanWheel` (`P:\DZ\vehicles\wheeled\config.cpp:4762`) has `radius=0.34` in config. The 0.3587 and 0.359 the notes quote as "vanilla sedanwheel radius" is the author's measurement of the wheel mesh on a debinarized copy, a different quantity that was not measured again here.
- `P:\DZ\vehicles\wheeled\civiliansedan\civiliansedan.p3d` is a binarized ODOL, so the axis convention, proxy frames, LOD counts and face counts quoted for the vanilla sedan come from the author's debinarized copy.

Read with `gta-rip-intake.md` (the other rip family), `rip-geometry-and-winding.md`, `vehicle-structural-parity.md`, and `skills/rip-vehicle-import/SKILL.md`, the skill that runs a new rip import step by step.

## What this file covers

How to turn a car ripped from a racing game (the Grub container:
`.modelbin` meshes, `.swatchbin` textures, `.carbin` car definition) into a drivable DayZ `CarScript`
vehicle. Companion to `vehicle-structural-parity.md` (parity-first method) and `external-obj-import.md`
(generic OBJ import). Derived from the SUB_BRZ build (Subaru BRZ FE '22 widebody, 2026-06-23) — the first
concrete case; treat SUB_BRZ paths as the worked example.

## RENDER-CRASH GOTCHAS — read FIRST (each cost a full session, SUB_BRZ s14 2026-06-29)
Two defects make the DayZ CLIENT crash ~9-22s **while rendering the car** (fault offset constant, e.g.
`…D5F9`, "Unknown module" = GPU/shader; the module BASE changes per launch via ASLR, the OFFSET is the bug).
Neither is caught by any offline gate, by G3, or by a Blender render — only the in-game render crashes.
1. **Degenerate UVs = GPU crash.** If a visual LOD has `uniqUV=1` (every vertex UV identical, e.g. a
   transplant that set `uv=(0,0)` on all corners), UV derivatives are zero → mipmap `log2(0)` → NaN → the
   GPU crashes when that surface is on screen. SUB_BRZ's OZ wheel (`rip_build_wheel.py`) did exactly this.
   **Any geometry transplant MUST emit real, non-constant UVs** — and avoid seams with extreme derivative
   jumps (a cylindrical `atan2` UV with ×N tiling can still crash at the ±π seam). Check `uniqUV` per LOD vs
   a vanilla control (vanilla sedanwheel LOD0 = 1203, not 1).
2. **Raw rip body weight tumbles the client.** A full rip body is ~400k+ visual faces; >~315k crashes
   the render (vanilla Mercedes loads at 315k; SUB_BRZ at 417k did not). User-reported symptom = "lag at
   spawn" then crash. **Decimate before shipping** — see DECIMATION below.
Diagnosis order when the client crashes ON the car (not the spawn-blocker): rule out weight, then geometry
corruption (NaN/overflow/UV-NaN health check), then a degraded environment (wipe `storage_1` — a corrupt CE
storage causes FALSE load-crashes), then bisect render inputs ONE at a time (glass alpha, per-mesh
materials, the wheel — never two at once).

## DECIMATION — rip bodies are too dense to render; planar-dissolve to ~200k (SUB_BRZ s14)
(supersedes the "NO decimation" wording of the 2026-06-24 architecture section below)
Pipeline `<vehicle-import>\scripts\decimate_{export,blender_batch,rebuild}.py` + `orchestrate_decimate.py`
(py3d→Blender→py3d). Per chunk: export verts/faces/UV + slot=(material,texture,region-selection) → Blender
`dissolve_limited` planar at 10° with `delimit={MATERIAL,UV,SEAM,SHARP}` (collapses source-game's flat
oversubdivision, KEEPS boundaries/curves/material/UV) → triangulate → rebuild p3d recomputing smooth
normals + rebuilding the named selections by slot. Result 440k→198k, 77.7→39.7 MB, shape intact (validate
with an assembled 3-angle render), G3 4/4. Decimate ONLY the proxy chunks; leave the shell visual
(wheel/light/tail selections), ViewPilot and structural LODs untouched. Planar dissolve does NOT deform
(only near-coplanar faces collapse) — this is the "won't break the model" decimation to use, NOT aggressive
collapse (which the user rightly rejected).

Tooling: **the community Grub-format extraction tools** (`carbin_importer.py`, `modelbin_importer.py`).
`modelbin_importer.py` imports one `.modelbin` (geometry-only with `use_materials=False`, try/except per
piece). `carbin_importer.py` assembles the whole car via the skeleton but needs the **GameDB SQLite**
(`gamedbRC.slt`, `use_db=True`) for physics/dims. Run headless: `blender --background --factory-startup
--python <script> -- <args>`.

## RIP ANATOMY (per-car folder)

| File | Holds | DayZ use |
|---|---|---|
| `Manifest.xml` | every part: `<Model path>` grouped by `PartEnum` under `NonUpgradeablePart`/`UpgradeablePart` | INCLUDE/EXCLUDE source |
| `Locators.xml` | named locators with a 4×4 `SceneTransform` (`_41`/`_42`/`_43` = x/y/z translation) | memory points, wheel positions, seat/crew, dims |
| `physicsdefinition.bin` | per-car physics (binary, ~1.6 KB) | no available parser; not used |
| `<CAR>.carbin` (+ `.carbin_debug`) | car definition / active part config | assembled by carbin_importer (needs GameDB) |
| `IKAnchorBones.xml` | steering + pedal IK | steering geometry only (NOT the values — see below) |
| `carscene_<CAR>_build_report.html` | render report | winding **oracle** for the geometry gate (NOT a readable parts list) |
| `_library` (shared, NOT in a one-car zip) | materials/textures `_fmnext`, tires, wheels | surface textures (texture phase) |

## MANIFEST → INCLUDE / EXCLUDE

Parse `Manifest.xml`: each `<Model path="game:\...\X.modelbin" LODs="N">` lives under an ancestor element
with a `PartEnum` attribute. Resolve `game:\` → your `game_path` root for `[ -f ]` existence checks.

- **`__slod` suffix = shadow-only** (LODs=1). Feeds the Shadow Volume LOD, NOT the visual INCLUDE — bucket separately.
- **The `bumperfcustom` trap**: the config/carbin can reference a custom part (`bumperfcustom_a`) that ships
  **only** as `bumperfcustom_a__slod` (shadow), with no visible `.modelbin`. The visible part is then the
  standard one (`bumperf_a`). ALWAYS `[ -f ]` the visible modelbin before assuming a custom part is usable.
- **Stock vs widebody variants**: a widebody rip ships BOTH stock (`body_a`, `fenders_a`) and wide
  (`bodywide_a`, `fenderswide_a`) — the Manifest is the full catalog; the carbin config selects. For a
  widebody build INCLUDE the `*wide*` and EXCLUDE the stock equivalents (same LOD count = full replacement,
  not flares). The exclusivity is a `[verify]` prior — confirm no z-fight in the visual assemble
  (blender-visual-review), do not treat it as a fact.
- Wheel rims (`oz_rallyracing_wheellf` etc.): EXCLUDE if reusing the vanilla `sedanwheel.p3d`; the source-game rim
  becomes a post-MVP cosmetic.

## RF (RIGHT-SIDE) RECONCILIATION — the mirror-list is an OUTPUT, never assumed

LHD ripped racing-game cars ship the **driver (left) side** geometry and **mirror the passenger side in-engine**. On disk:

- **Mirror-gaps** (left ships, right absent → generate by X-mirror + winding re-fix on mirrored faces):
  doors, door cards, door handles, door jambs, door speakers, **seats**, seatbelts, skirts.
- **Shipped both sides** (symmetric render parts): glass, head/tail lights, wing mirrors, brakes (calipers/rotors).

The `.carbin_debug` references right-side parts by logical name, but those modelbins are NOT on disk — `[ -f ]`
each right-side `.modelbin` to classify SHIPPED vs MIRROR-GAP per part. (SUB_BRZ: 14 shipped-both, 8 mirror-gaps.)

## DIMENSIONS — data-driven from Locators.xml (NOT real-world, NOT GameDB)

The wheel locators give verified geometry. `SceneTransform value._41/_42/_43` = translation x/y/z (x lateral,
y up, z longitudinal):

- **wheelbase** = `wheelLF.z − wheelLR.z`. SUB_BRZ: 1.286372 − (−1.288897) = **2.575 m**, which matches the real
  BRZ 2575 mm exactly → reading the transform correctly is **validated by the real-world cross-check**.
- **track** = `wheelRF.x − wheelLF.x` (wheel-center; a widebody reads wide).
- **tire-contact plane** = `wheel.y − vanilla_wheel_radius` (NOT bbox-min, which includes the splitter). Sets
  the DayZ re-origin so the car sits on the ground.

Always cross-check the computed wheelbase against the real car's spec: a match confirms the axis/units; a
mismatch means you read the wrong axis.

## DRIVETRAIN / MASS — GameDB-gated, mark [UNVERIFIED], do NOT guess-parse

drivetrain, torque, differential, tire widths, ride height live in the **GameDB SQLite** (`Data_Car` /
`Data_CarBody`), which `carbin_importer.py` reads with `use_db=True` (the SQL is at `carbin_importer.py:1887`).
The per-car rip usually does NOT include the GameDB; `physicsdefinition.bin` has no parser (0 ASCII strings).

So drivetrain (e.g. RWD) and curb mass are **real-world facts** marked `[UNVERIFIED vs rip — GameDB absent]`,
NOT decoded from the rip. Do NOT guess-parse the binary for a float "mass" — a value from guessed offsets is
worse than an honest `[UNVERIFIED]` + real-world target (anti-tautology, R22). DayZ mass is not a config field
anyway: it is baked from Geometry-LOD `#Mass#` vertex weights, so the real-world curb mass is only the
authoring target.

**s22 (2026-07-02) — verified on the FM2023 BRZ rip, sharpens the above:**
- `physicsdefinition.bin` DOES parse: `physicsdefinition.bin.bt` (010 template) ships in the
  source-game-extraction-tools repo. But even parsed it carries only the **collision hull** — for the BRZ:
  `DefinitionType=Vehicle`, `Mass=0.0`, inertia tensors zero/NaN, then a PointCloud. Exhaustive float32
  scan of all 404 slots = no value in curb-weight range. Mass is absent from the per-car file **by design**
  (delegated to the GameDB), not merely "unparseable". Do not mine it.
- **Title of these rips: most likely the 2026 racing-game sequel (internal dev/RC build), NOT FM2023.** The build report
  (`carscene_*_build_report.html`) shows Perforce branch `forte_main`, depot `the studio internal depot`, build agent
  `PGL-HNX026`, "restricted access" — an INTERNAL pre-release build (CarBuildTime 2026-04-20; `gamedbRC.slt`
  = Release Candidate; FH6 shipped 2026-05-19). `_fmnext` is the shared next-gen material library (FM2023 +
  FH6), NOT FM2023-exclusive; `.carbin` Root type = `07 00` (one gen past FH5 `06 00`). Not confirmable by
  public codename. Lesson: identify the title from the build report's p4 branch/depot, not just the library
  namespace — the namespace is shared across the generation.
- **`gamedbRC.slt` is whole-file encrypted** (entropy ~7.95 bits/byte, no SQLite/zlib/zstd magic; source-game
  pattern = Arxan TransformIT + CRC-32). Two community tools exist; neither is a clean fit for a dev/RC rip:
  - `the local community GameDB crypto CLI (FH5-era)` — CLI, fully **local**, but supports only up to **FH5 v1.614.70.0**
    (keys from the XeNTaX thread). Does NOT cover FH6/FM2023.
  - `the server-side GameDB crypto client (2026-title)` — targets **FH6** and does GameDB→editable-SQLite, but the GameDB decrypt is
    **server-side**: closed-source .NET client that ships **no keys**, needs a reachable backend + a gated
    **application key**, and **uploads the file to the author's backend** to decrypt (verified from its
    README/release notes: *"All decrypt/encrypt runs server-side; the app ships no keys"*).
  - **Verdict for these internal dev/RC rips: do NOT use the server-side tool.** The GameDB is a non-public
    build ("restricted access" in the build report) — uploading it to a third-party modding backend is a
    privacy/security problem, and the backend may not even hold keys for a non-retail RC build. Get the data
    from the RIP SOURCE (who has the internal build): a decrypted `.slt`, or a CSV of the `model`+`gamecars`
    tables. Do not burn a session decrypting.
- **Exact columns to request** (schema = `cardb.bt` in the repo): table `model` → `DrivetrainTypeID`
  (→ `drivetraintype` = RWD/AWD/FWD), `EnginePlacementID`, `Name`, `Year`; table `gamecars` → `CurbWeight`
  (mass), `WeightDistribution` (front %), `SimPeakPower`, `SimPeakTorque`, `NumGears`, `RideHeight`,
  `Front/RearTireWidth`+`Ratio`+`WheelDiameter` (cross-checks DayZ wheel radius). Keyed by `carid`. Ask for
  the decrypted `.slt` (whole fleet at once) or a CSV of those two tables. Units of power/torque and the
  `WeightDistribution` convention need calibrating against one known car's real spec on first decrypt.
- **Plan B when the GameDB is unavailable — public FH6 stat sites, no decrypt needed.** In-game curb weight /
  drivetrain / power / front-weight-% are published per car by community sites and cross-check cleanly.
  Verified for the 2022 BRZ (FH6): RWD, 2,835 lb = **1286 kg**, 228 hp, **53% front** (`game8` archives/600793
  and `calculators.games FH6 car pages (2022 Subaru BRZ)` agree; `kudosprime.com/fh6/carlist.php`
  gives weight already in **kg**, 614 models by make, but no weight-distribution). These are RETAIL FH6 values,
  not read from the encrypted RC GameDB — but mass/drivetrain don't change between builds, so they're a
  reliable authoring source for the whole fleet. Try these BEFORE chasing the encrypted GameDB; the GameDB
  only wins if you need the exact RC-build numbers or a bulk export.

## STEERING IK — read the geometry, NOT the value

`IKAnchorBones.xml` carries `SteeringWheelMaxDegrees` (SUB_BRZ: 270) and `steering_ik_rot_left/right
RotZ=±1.94`. These are source-game values — do NOT copy them. DayZ `maxSteeringAngle` is ~30–35°. Use the IK file
for the steering-wheel pivot/axis geometry (the animated-wheel anchor), not the rotation amounts.

## PARITY VERIFIER — verify_<mod>.py (generalizes beyond source-game)

Each imported vehicle gets a `verify_<mod>.py` asserting structural parity against the CONTROL
(`CivilianSedan` v54). Pattern (see `verify_amglf.py` / `verify_brz.py`):

- py3d MLOD reader → per-LOD anatomy. Resolution bands: Geometry ~1e13, Memory ~1e15, ViewGeo ~6e15, FireGeo
  ~7e15, ViewPilot ~1100, Shadow ~10000, Visual <100.
- proxy classification anchored to basename/path (`endswith("wheel.p3d")`, crew substrings), NOT loose substring.
- `build_checks()` → `(id, group, severity, ok, measured, expected, ref)`; FAIL = hard gate, WARN = soft.
- **`--self-test` is the non-vacuity proof**: a synthetic IDEAL anatomy passes 0 hard-fails AND a synthetic
  BROKEN fails an EXACT expected set. Proves the verifier discriminates without a real file and without py3d.
- check `os.path.isfile` BEFORE `import py3d`, so a missing target reports cleanly (exit 4 "not built yet")
  without the dependency.
- per-mod policy knobs at the top: vanilla-wheel reuse (no mod wheel proxy), monolithic body (body-split =
  WARN not FAIL), interior-animation gate severity, crew seat count. Mark names not yet pinned to the CONTROL
  `[TBD]` and pin them by debinarizing the CONTROL.

### Generalized harness + MANDATORY gates (2026-06-25) [VERIFIED: self-test PASS, positive-control OK on CivilianSedan, SUB_BRZ 24/24]

`verify_rip_car.py` (in `<vehicle-import>\tools\`) SUPERSEDES per-car `verify_brz.py`: ONE parametrized
verifier, a POLICY dict per car (`brz`, `amglf`), checks tiered **U** (universal engine contract) vs
**P** (car-specific policy: dmgzone list, body-proxy naming, mod token). Run these as GATES (they
BLOCK), not optional steps — skippable verification is how the offline false-green happened:

- `verify_rip_car.py --self-test --car <car>` — non-vacuity proof (synthetic IDEAL passes 0 hard
  fails; BROKEN fails the EXACT set incl. the historical 0/12-componentNN spawn blocker).
- `verify_rip_car.py --positive-control <CivilianSedan_mlod.p3d> --car <car>` — **the contract
  validator**: the UNIVERSAL subset MUST pass on the known-good vanilla car. If a universal check
  fails on the sedan, the contract is mis-specified (too strict / wrong name) → fix the verifier, not
  the car. This replaces `[TBD]`-pin-by-hand with ground-truth validation, and it caught a real false
  assumption shared with `verify_amglf.py` (see vehicle-structural-parity.md Addendum 2026-06-25).
- `verify_rip_car.py <target.p3d> --car <car>` — 0 all-hard-pass / 1 hard-fail / 4 missing-or-not-MLOD.
- `roundtrip_writer.py [<p3d>]` — proves py3d `read→save→read` is structurally lossless (the
  LFInfectedBig skinned-export corruption class). Default control = CivilianSedan.
- `roundtrip_structural.py` — **bisects the BUILDER, not just the verifier** (added 2026-06-25). Drives the
  REAL `rip_p3_structural.build_structural(profile)` with the CivilianSedan control (its visual shell +
  locators derived from its OWN memory points) and requires the regenerated structural LODs to pass the
  UNIVERSAL subset (tier U minus `vis.*`, which belong to the Phase-2 shell). POSITIVE (dual_tag ON): 19/19
  structural-universal PASS → the builder emits contract-satisfying structure for a car it never tuned
  against. NEGATIVE (dual_tag OFF): the bisection CATCHES `geo.hub_componentNN` + `view.seat_componentNN`
  (the historical 0/12 spawn blocker) → non-tautological. This is the test that would have caught the s7
  blocker OFFLINE. (Builder refactored to `build_structural(P)` + `BRZ_PROFILE` + `__main__` guard; running
  it directly = the BRZ build verbatim, behaviour-preservation proven A==B vs a pre-refactor snapshot.)
- `fit_transform.py` — rule-fits the rip→DayZ transform from source/output pairs (added 2026-06-25):
  recovers `(-Fx, Fy+Y0, -Fz)` + Y0 from data and confirms it is a pure sign-flip+offset (unit scale, no
  hidden rotation/permutation). The BRZ pair is SELF-CONSISTENT (output built by this L2D → residual 0.000 by
  construction, R22 tell) → rescued by a **discrimination self-test**: 4 wrong transforms (sign flip, Y0±0.1,
  1.05× scale, axis swap) blow the residual far past tol, so the 0.000 on the correct one is meaningful. (An
  independent Mercedes pair is DEFERRED — no clean source↔output anchor correspondence on disk; data-driven to
  ingest one when a future car keeps both Locators and an independent author.)
- `visual_gate.py <p3d> <out_dir> [--label N] [--views N]` — **generic for ANY DayZ `.p3d`** (added
  2026-06-25). Exports the visual LOD to OBJ and renders N orbit + top + low views via Blender 5.1 headless
  (the dayz-3d-viewer Three.js viewer is retired) + a `blender-visual-review` checklist + an
  unresolved-proxy inventory. CAVEAT (s20 2026-07-02, supersedes the old "reproduces the engine cull"
  claim): it does NOT reproduce the engine — the engine renders the ANTI-cross side and shades with the
  STORED MLOD normals, while Blender no-normals + backface culling shows the +cross side (the opposite);
  it also does NOT resolve body-split proxy chunks. Use for geometry presence / silhouette / proxy
  inventory only; winding and see-through verdicts are IN-GAME ONLY.

Universality split: `verify_rip_car.py` (tier-U contract + per-car POLICY), `visual_gate.py` and
`roundtrip_writer.py` are GENERIC for any DayZ car (see `vehicle-structural-parity.md` Addendum 2026-06-25b).
`roundtrip_structural.py` and `fit_transform.py` are PATTERNS bound to the source-game builder/transform — for a
non-ripped car, point the bisection at that car's `build_structural` and the fit at its transform. Shared
helper: `_harness_util.py` (`clean_visual_shell` = reconstruct a runnable shell-only `.p3d` from a deployed one).

Env: `python` 3.14.3 + py3d 1.2.0. A phase is CLOSED only with {positive-control OK + target hard-pass +
structural-bisection PASS + visual-gate captures reviewed}, never on internal asserts alone. Wiring into
`dayz-test.ps1` (`Invoke-G3-StructuralVerify` = verify + `roundtrip_structural`; `Invoke-G7-OfflineDiff`;
exit≠0 blocks the PBO) is the build-time gate — **HELD until the SUB_BRZ script-class Cowork session closes**
(it shares the SUB_BRZ tree); the offline harnesses in `<vehicle-import>\tools\` are done and green.

## PIPELINE PHASES (reusable front-end)

0 harness + product-spec + verify skeleton · 1 manifest INCLUDE/EXCLUDE + RF + dims (this doc) · 2 geometry →
visual `.p3d` shell + LODs + winding-with-oracle · 3 structural (Geometry/Memory/View/Fire/Hitpoints, vanilla
wheel reuse, mass) · 4 config.cpp + model.cfg · 5 textures. Phases 1–4 are the reusable rip→DayZ front-end.
Per-car scripts to reuse: `_parse_manifest.py` (PartEnum inventory), `_classify_parts.py` (INCLUDE/EXCLUDE/
SHADOW + RF `[ -f ]` probe) — in the SUB_BRZ workspace `<vehicle-import>\tools\`.

---

## PHASE 3 — STRUCTURAL AUTHORING (the drivable skeleton) — verified on SUB_BRZ 2026-06-24

Phase 2 leaves a visual `.p3d` (shell + proxy chunks, or monolithic). Phase 3 ADDS the structural LODs
WITHOUT touching the visual body geometry. Builder reference: `<vehicle-import>\scripts\rip_p3_structural.py`
(reads the deployed shell, writes a new full `.p3d`, deploy is a separate SHA-checked step).

### 3.0 Derive the locator→DayZ transform EMPIRICALLY (never assume) — and the DayZ axis convention

The `Locators.xml` is in **source-game** space (Fx,Fy,Fz). The Phase-2 body geometry was placed in DayZ space by
the geometry transform. Memory points MUST co-locate with the deployed geometry, so derive the locator→DayZ
map by **matching centroids**, not by assuming axes:

1. Pick identifiable parts (headlights, taillights) and compute their centroid in the DEPLOYED DayZ geometry.
2. Compare to the matching source locator. Solve the per-axis sign/offset.

SUB_BRZ result: **`DayZ = (−Fx, Fy + Y0, −Fz)`**, `Y0 = (wheel_radius − rip_wheel_center_y) + lift`
(`(0.3587 − 0.19464) + 0.18 = 0.34406`). The `(−x, −z)` is a **180° rotation about vertical (det +1, proper,
NOT a mirror)** — it is legitimate, see below.

**DayZ vehicle axis convention (from CivilianSedan, the CONTROL — VERIFIED):** **front = −z** (headlights
z≈−2.4, engine/drown_engine z≈−1.7), **rear = +z** (reverse light +2.56, exhaust/refill +2.2), **driver =
+x** (`seat_driver` +0.436). source-game is front=+z, so a correct rip→DayZ import flips z. **Do NOT "fix" a
180°-rotated-looking car** — confirm against CivilianSedan first; a static render cannot reveal a front/back
swap, only the marker/centroid check can. (SUB_BRZ nearly triggered a false refactor here.)

### 3.1 Wheel naming convention `wheel_<side>_<axle>` (pinned from CivilianSedan)

From `civsedanwheel_X_Y` positions: **first index = side (1 = +x, 2 = −x), second index = axle (1 = front
= −z, 2 = rear = +z)**. So `wheel_1_1`=+x front, `wheel_2_1`=−x front, `wheel_1_2`=+x rear, `wheel_2_2`=−x
rear. FRONT (steered) wheels are `_X_1`. This is what `verify_<mod>.py` `FRONT_WHEELS=["1_1","2_1"]` and the
config `Axles`/`model.cfg` steering must agree with.

### 3.2 Proxy path format — vanilla & kt use NO `.p3d` suffix (latent-bug class)

MLOD proxy selections are `proxy:<path>.<NNN>` where `<path>` has **NO `.p3d` extension** — verified against
BOTH vanilla CivilianSedan (`proxy:\dz\vehicles\wheeled\civiliansedan\proxy\sedanwheel.001`) and the shipped
kt_roadkill mod (`proxy:kt_roadkill_scum\proxy\..._wheel.001`). The engine appends `.p3d` at resolve time.
A `.p3d`-suffixed path (`...sedanwheel.p3d.001`) resolves to `...sedanwheel.p3d.p3d` → **proxy not found →
that geometry is missing in-game** (silent: spawns fine in editor checks). SUB_BRZ Phase 2 had this bug on
its chunk proxies; Phase 3 normalized all of them. ALWAYS write proxy paths without the extension. (`verify_*`
was hardened to accept both forms so it doesn't mask the bug.)

### 3.3 The structural LOD recipe (py3d 1.2.0 DayZ fork)

py3d helpers used: `LOD.set_memory_point(name, coords)` (1-pt), manual 2-pt for `*_axis`, `LOD.add_proxy(path,
index, origin, rotation)`, `LOD.set_total_mass(kg)`, an `add_box` that forces OUTWARD winding per box centroid.

- **Geometry (1e13)**: ≥4 convex closed `component0N` boxes following the body, with wheel-wells cleared at
  the 4 corners (chassis points ≥ `tire_radius + 0.07` from each wheel center) + 4 small hub boxes named
  `wheel_X_Y_damper_land` (~0.20×0.18×0.18) + `seat_driver`/`seat_codriver`. `properties{autocenter:"0",
  class:"vehicle"}`. **`set_total_mass(curb_mass)` ONLY on this LOD**; X-symmetric boxes → CoM.x≈0.
  Component names **lowercase `component01`** == vanilla (see 3.5).
- **Memory (1e15, 0 faces)**: per wheel `_axis`(2-pt, lateral x = spin), `_damper`(1-pt), `_damper_axis`(2-pt
  vertical = travel), `_damper_land`(1-pt = hub); front `_steering`(1-pt)+`_steering_axis`(2-pt vertical);
  `pos_driver(_dir)`/`pos_codriver(_dir)`; `seat_con_1_1`/`2_1`; dials `mph/rpm/fuel_1/drivewheel`(+`_axis`);
  `refill` (**NOT `fuelpoint`**); `light_left/right(_dir)`+`light_reverse`+`reflector_1_1/2_1`; `engine`+
  `drown_engine`; `ce_center/ce_radius/boundingbox_min/max/invview`+`pos center`; `ptcexhaust_start/end`/
  `ptcenginepos`/`ptccoolantpos`. DayZ light naming: `light_left`=+x, `light_right`=−x (matches sedan).
- **ViewGeometry (6e15)**: 1 occlusion `component01` box + `seat_driver`/`seat_codriver` boxes + 4 wheel
  proxies (vanilla `sedanwheel`) + crew proxies `crew_driver`(→crewdriver) + `crew_cargo`(→crewcodriver).
- **FireGeometry (7e15)**: one box per dmgZone, each box assigned to BOTH `component0N` AND `dmgzone_X`
  (so it counts as a component and a damage zone) + 4 wheel proxies + crew proxies.
- **Hitpoints (5e15)**: 1-pt selection per dmgZone; **assert `set(Hitpoints) == set(FireGeo dmgzones) ==
  config.componentNames`** (the config side is the consumer — author the dmgZone set and document it for the
  config author).
- **Shadow (1e4)**: shell geometry **shrunk ~2%** about its centroid (Rule "shadow slightly smaller than
  visual", else the body renders fully shaded), materials/UV stripped. (Or build from the rip `__slod` parts.)
- **ViewPilot (1100)**: first-person cockpit = interior parts (dash/gauges/wheel) only, NOT seats. Counts
  toward the <65535 resolved-vertex ceiling.

### 3.4 `#Mass#` only on Geometry — the per-LOD guard (spawn-underground class)

py3d emits `#Mass#` for any LOD where a point has `mass != None`. A stray `#Mass#` on a non-Geometry LOD →
binarize bakes CoM=(0,0,0) → car spawns underground and PhysX-ejects. After assembling, **assert** only the
Geometry LOD has mass (`new Point()` defaults to `mass=None`; `add_proxy` points are None too).

### 3.5 `validate()` findings that are EXPECTED for a vehicle (don't chase)

- **`ERR_COMPONENT_NAMING` (lowercase `component01`)** is a **false-positive for vehicles** from py3d up
  to 1.8.0 (pinned until 2026-10-02) — vanilla CivilianSedan itself triggers it (it uses
  lowercase); py3d 1.9.0
  does not check the case. Match vanilla: lowercase. (`component01` collided
  like `Component01` on an `Inventory_Base` item too: dayz-p3d-audit killer #2, measured in game 2026-10-02. The same code
  for a collision LOD with faces and no component at all is not expected: on an item and a building that
  collision was gone; vehicles not measured. From 1.9.0 it also checks the View and Fire LODs, and a
  Geometry LOD without faces, such as the one in a debinarized vanilla `sedanwheel_destroyed`, no
  longer raises it.)
  *(Corrected 2026-10-02: the parenthesis read "Uppercase `Component01` is the Inventory_Base rule.")*
- **`ERR_AXIS_SELECTION_MISSING`** fires for every Memory `*_axis` whose homonymous selection is absent from
  the **visual** LOD. For wheels this is REAL — assign each wheel proxy face ALSO to visual `wheel_X_Y`
  (rotation), `wheel_X_Y_damper` (suspension translation) and front `wheel_X_1_steering` selections so
  model.cfg can drive it; without them the animation is a silent no-op. For deferred dials it is expected.
- `WARN_NOT_WATERTIGHT` (proxy triangles are open), `WARN_WINDING_MIXED` (multi-box collision: each box is internally consistent relative to its own centroid;
  the warning uses the global centroid, so infer no absolute sign — see invariant 18 of the dayz-model-pipeline skill and use the relative check against the Visual LOD), `WARN_LOD_KIND_UNKNOWN` (ViewPilot 1100) —
  all expected.

### 3.6 Animated interior vs the shell+proxy architecture (the gauge/steering trap)

A proxy chunk's named selections **cannot be animated by the parent model.cfg** — the parent animates its OWN
selections; a proxy only moves with its anchor face. So any part that must animate (steering wheel
`drivewheel`, gauge needles `mph/rpm/fuel_1`) MUST live in the **main model (shell)**, not a proxy chunk.
If Phase 2 grouped `gaugecluster`/`steeringwheel` into a proxy chunk, the animated-interior pass must first
**relocate them into the shell**, then isolate the needle geometry. The source-game `gaugecluster` is usually a
single mesh with no separate needles → needle isolation needs face segmentation or synthetic needle geometry
(defer it explicitly; author the dial Memory points regardless).

### 3.7 Cross-project risk: large body-proxy placement (watch at the first in-game spawn)

The sibling MERCEDES_AMGLF (same proxy approach) hit a P1: the engine renders **large body-proxy geometry
displaced ~2.5 m** in-game (proxy frame was confirmed identity = not the cause). Mitigations in play:
keep each proxy chunk < 65535 resolved verts and keep a REAL body shell in LOD0 (kt pattern, not all-proxy).
If chunks spawn displaced, this is that bug — resolve the proxy-placement convention before iterating.


## (added 2026-06-24) BODY = BASIC SHELL + FULL-DETAIL PROXIES — do NOT QEC-collapse the rip

> SUPERSEDED in part (s14 2026-06-29): proxy chunks MUST be planar-dissolved to ~200k total before
> shipping — a raw ~400k+ body crashes the client render (see §DECIMATION and render-crash gotcha #2).
> "Full-detail / NO decimation" below means no QEC collapse (which crumples aero parts), not zero decimation.

The dense source-game body does NOT decimate to a clean game-budget shell — QEC (even per-part,
boundary-preserving) CRUMPLES the dense custom/aero parts (front/rear fold, panel holes). Confirmed on
SUB_BRZ 2026-06-24 (two decimation attempts rendered as a crumpled wreck). The body is NOT a monolithic
decimated LOD0, and NOT an all-proxy LOD0 with no base either (all-proxy breaks hiddenSelections paint).
Replicate the shipped vanilla/community pattern:

Reference (debinarize one and LOOK before choosing an approach — cite-then-verify, R2.1):
- CivilianSedan LOD0 = real body shell ~14.6k faces carrying the paint selection `camo_exteriorcolor` +
  lights + dmgzones, PLUS proxy refs for doors/hood/trunk/engine/wheels/crew.
- kt_roadkill_scum_armed LOD0 = real shell ~13.4k faces (light/paint selections) + proxy refs (wheels,
  crew, doors, gun, motor, body/body2). Structural LODs only; **1 visual LOD** (no decimated ladder).

Architecture:
- LOD0 = a BASIC real shell = the clean low-poly STOCK parts (unibody `body_a` + lights), real geometry,
  NO QEC collapse (planar dissolve per §DECIMATION is mandatory). Carries paint via hiddenSelections (`color`) + light selections (light_left/right,
  light_brake_1_2/2_2, light_reverse_1_2/2_2, light_dashboard).
- Everything else = full-detail PROXY chunks (`\<MOD>\proxies\*_chunk_NN.p3d`), each < 65535 resolved,
  NO QEC collapse (planar dissolve per §DECIMATION is mandatory): dense custom widebody/aero (flares, fenders custom, fog lights, bumpers), other panels,
  glass, interior. `add_proxy(path, index, origin=(0,0,0))` at identity (parts are in absolute car space).
- Paint of proxy parts (user decision 2026-06-24): hiddenSelections does NOT reach proxy geometry, so
  body-colored proxy parts get the livery BAKED into their own rvmat (single fixed livery = v1 scope;
  color-swap / damage-material on those parts is out for v1). The shell is hiddenSelections-paintable.

Part classification (which goes where): dump per-part vert/face counts; the clean low-poly STOCK shell
parts (body_a + small panels) -> real shell; the dense custom/aero parts (> ~8k v: bodywide, fenderscustom,
fenderswide, foglights, bumpers) -> full-detail proxies. Interior -> proxy.

Correction to the stock-vs-widebody note above: the `*wide*` parts are flares BOLT-ON ON TOP of the stock
shell, NOT full replacements -- INCLUDE `body_a` (it is the central roof/cabin shell; excluding it deletes
the roof). "Same LOD count" is not proof of replacement. (SUB_BRZ G1 excluded body_a by mistake; the visible
"hole" was the missing roof.)

Proxy path form (Phase 3 finding 2026-06-24): NO `.p3d` suffix. Vanilla/kt proxy selections are
`proxy:\path\name.NNN` (no extension); py3d `add_proxy` that writes `...name.p3d.NNN` is a latent bug
(likely won't resolve in-engine) -- write the proxy ref WITHOUT `.p3d`, matching vanilla/kt. The
`verify_<mod>.py` `_proxy_file` helper must accept both forms.

Builder: `rip_p2_shellproxy.py` (real shell LOD + per-chunk proxy build + add_proxy); structural LODs by
`rip_p3_structural.py`. The earlier `rip_p2_proxybuild.py` (all-proxy, no base) and `rip_p2_assemble.py`
(monolithic decimated) are OBSOLETE.

verify_<mod>.py for this architecture: `MIN_VISUAL_LODS=1`; collect named selections from the proxy chunks
(`mod_proxy_sels`) and test the shell+proxy UNION for material/light/dial selections (glass/interior live in
the chunks); assert each proxy chunk < 65535. Run `--mod-root <projects-root>` WITHOUT a trailing backslash
(PowerShell `"$x\"` escapes the closing quote -> mangled arg).


## (added 2026-06-24, s2) FIRST IN-GAME SPAWN RESULT — structural gates pass, car does NOT spawn [VERIFIED in-game]

> Closes the loop on §3.7's "watch at the first in-game spawn". SUB_BRZ reached its first in-game spawn
> (DayZDiag server+client, VPP Object Spawner). It does NOT spawn drivable. Root cause **OPEN** — under
> research (handoff: `SUB_BRZ_dev\reviews\2026-06-24-spawn-blocker-research-handoff.md`).

**The failure (server RPT, at `Load entity type 'SUB_BRZ'`):**
```
PHYSICS (E): Action selection 'seat_driver'/'seat_codriver' was not found in view or fire geometry ... class Crew::Crew
PHYSICS (E): Won't simulate, wheel wheel_1_1_damper_land has no proper selection in geometry
```
Entity creation fails → nothing usable spawns (+ a hard client lag, see below).

**PROCESS LESSON [VERIFIED]: offline parity ≠ drivable — the in-game SPAWN is the only gate that catches
crew/wheel simulation.** `verify_brz.py` (parity vs CivilianSedan), `audit_p3d.py`, AND a manual py3d diff vs
the debinarized CivilianSedan all pass / give only the known false-positives (§3.5) — yet the engine rejects
the crew action selections and the wheel hub. The structural LODs are parity-correct on every measurable
metric (mass 1270 kg distributed across 14 components, 12/12 outward winding per box, convex closed separate
islands, hub 0.20×0.18×0.18, lowercase `component01`, exact LOD resolutions, seat/hub selections present in
the right LODs) and STILL rejected. **Add an in-game spawn gate to Phase 4 BEFORE declaring a ripped racing-game car done;
do NOT trust the offline verifier as proof of drivability.**

**Ruled out this session [VERIFIED] — do not re-try:**
- **Build mode**: packonly (MLOD) and AddonBuilder-binarized (ODOL) give the IDENTICAL crew/wheel error.
  Not the lever (refutes "a vehicle must be ODOL to simulate").
- **Penetration materials** (audit Killer #10): the 288 collision faces had empty material (a REAL defect —
  vanilla ships `dz\data\data\penetration\*.rvmat`); assigning them changed NOTHING. Killer #10 is a different
  failure class (ballistic/cursor), NOT crew/wheel simulation rejection.
- **Vertex ceiling**: audit's "LOD0 over 65535" is a FALSE POSITIVE — it counts face-indices (96585); the
  resolved unique vertices (pt+normal+uv) = 22143, under 65535. The body loads and renders.

**OPEN [HYPOTHESIS, NOT verified]:** root cause unknown. NOTE the body is the §"BASIC SHELL + FULL-DETAIL
PROXIES" kt-pattern (a REAL low-poly shell in LOD0 + proxy chunks), **NOT all-proxy** — so "the proxy body
breaks simulation" is unproven and probably wrong (the crew/wheel selections are direct geometry in the
structural LODs, exactly like vanilla). Candidate deltas vs vanilla still UNTESTED as cause: vanilla hub =
16 pt / 15 face shape vs SUB_BRZ 8 pt / 12 face box; SUB_BRZ has `seat_driver`/`seat_codriver` boxes in the
**Geometry** LOD (vanilla has seats only in ViewGeo). Next session must research a WORKING community
custom-body car (kt_roadkill) + the engine's exact requirement behind those two messages before editing
geometry.

**Side-symptom (NOT the blocker):** the LOD0 shell's light selections are inflated
(`light_left`/`light_right`/`tail` ≈ 6594 faces each — should be small lenses) → likely the spawn lag and a
lights-paint bug.

> Origin: SUB_BRZ Phase 4 in-game test 2026-06-24 (config.cpp written by an agent + first VPP spawn). Cross-ref §3.7
> (proxy-placement P1, MERCEDES_AMGLF) and `vehicle-structural-parity.md` (Crew check + wheel "no proper
> selection"). Sister project MERCEDES_AMGLF (same architecture) also has in-game smoke PENDING — neither
> ripped racing-game car is confirmed drivable yet.

## (added 2026-06-24, s7) Spawn blocker RESOLVED + body render fixed — get-in ACTIONS + drivability still OPEN [PARTIAL in-game verify]

Closes the s2 "FIRST IN-GAME SPAWN RESULT" only for **spawn + render**. **VERIFIED in-game** (user looked at the
render): the entity CREATES (both PHYSICS errors gone) and the body renders aligned + right-side-out (recognizable
car). **NOT verified / still OPEN — do NOT claim "drivable":** (a) the in-game **get-in / crew ACTIONS do NOT
appear** (the action menu is empty on the car), (b) **drivability untested**, (c) the user reports **parts still
look missing** — the "untextured glass" explanation below is a HYPOTHESIS, not confirmed. So: spawn-blocker fixed,
render fixed, the car is NOT yet a working vehicle.

Three fixes took SUB_BRZ from "won't spawn at all" to "spawns + body renders aligned + solid", in this diagnostic
order:

1. **SPAWN BLOCKER = componentNN dual-tag** (full detail: `vehicle-structural-parity.md` "componentNN DUAL-TAG").
   The Geometry hubs/seats and ViewGeo seats were standalone islands (**0% componentNN overlap**) → the two
   PHYSICS errors. The s2 candidate deltas (hub 16pt-vs-8pt-box, seats-in-Geometry) were RED HERRINGS. Fix: tag
   each hub/seat box ALSO `componentNN` in `rip_p3_structural.py` (mirrors the FireGeo dmgzone dual-tag it
   already did). Verifier check = the face-overlap % (100% on every working car, 0% on the broken one).

2. **PROXY FRAME** (chunks rendered rotated ~90°/scattered → not a car): apply `R=((-1,0,0),(0,0,1),(0,1,0))` to
   the body-chunk `add_proxy` in `rip_p2_shellproxy.py` (it used the default `rotation=None` = py3d "identity" =
   the wrong frame the engine rotates ~90°). Same convention as MercedesAMGLF s4
   (`vehicle-structural-parity.md` "TRIANGLE FRAME"). SUB_BRZ paths were already without `.p3d`.

3. **WINDING** (normals inverted: checkerboard/texture on the INTERIOR face, exterior see-through): the
   `force_outward` in `rip_p2_shellproxy.py` (centroid-based "make outward") + the det=-1 transform render
   inverted in-game. force_outward IS the tautological "make outward" the REGEN section warns about; memory's s3
   "force-outward 95-97% NOT decisive" was WRONG — it WAS decisive. Fix = keep glTF vertex order (do NOT
   force_outward); for already-built geometry, a global vertex-order flip of the body faces (shell + chunks),
   KEEP the stored normals (they point exterior → consistent with the now-exterior-rendered surface). In-game is
   the gate (offline winding check is tautological).

**STILL OPEN after #1–#3 (do NOT treat as done):**
- **Get-in / crew ACTIONS do not appear in-game.** seat_driver is now a proper `componentNN` in ViewGeo (which
  removed the spawn-PARSE error), but the action menu on the spawned car is empty. The crew action / proxy
  resolution at runtime is a SEPARATE post-spawn problem — unsolved. (Note: a `world_spawn`/VPP spawn has no wheel
  attachments, so the car sits on its chassis / can float; whether that blocks the action is unverified.)
- **Apparent missing parts / holes.** The client RPT is clean of proxy-not-found and all 9 chunks load, so the
  LEADING HYPOTHESIS is untextured glass (windows see-through without a glass material) + the checkerboard
  placeholder. BUT the user reports parts still look missing — this is NOT confirmed all-glass; re-check per-part
  (or after texturing) before closing it.

> Origin: SUB_BRZ Phase 4 in-game 2026-06-24 s7 (single Cowork session, VPP spawn). Builders fixed so car #2
> inherits: `rip_p2_shellproxy.py` (proxy frame + winding), `rip_p3_structural.py` (componentNN dual-tag).
> Box-exclusive gotcha confirmed: SUB_BRZ + MERCEDES_AMGLF Cowork sessions `-Kill` each other's DayZDiag — only
> ONE session tests in-game at a time. Pending (non-blocking): textures (Phase 5), 417k-face lag, PBO `.bak`
> bloat cleanup.

## (added 2026-06-25, s8) GET-IN ROOT CAUSE #2 — a ripped racing-game car needs an Enforce Script CLASS, not just geometry [VERIFIED in-game + vs FC/vanilla source]

s7 fixed spawn+render. s8 confirmed the s7 bone-selection fix AND found why get-in / crew actions still never appear.

**Fix (d) — companion bone selections — CONFIRMED in-game (2026-06-25).** Re-spawned the deployed PBO via dayz-mcp:
the server RPT has ZERO `PHYSICS (E/W)` lines — the s2/s8 `crewdriver`/`crewcodriver`/`CivSedanWheel not found`/
`seat_driver not found`/`no proper selection` errors are GONE. The attachment-proxy companion bone selections
(vehicle-structural-parity.md "ATTACHMENT proxy ... BONE-NAME selection") resolve the engine binding. This fixes
get-in's **gate-1** (`CrewPositionIndex(componentIndex) >= 0`). It is necessary but NOT sufficient (see below).

**ROOT CAUSE #2 (the real get-in blocker, geometry-independent):** `ActionGetInTransport.ActionCondition`
(`P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetintransport.c:45-55`) has TWO gates that BOTH must pass: (1) `CrewPositionIndex >= 0`
(crew proxy bone = fix d), AND (2) `CrewCanGetThrough(crewIndex)` (:54). **`CrewCanGetThrough` is NOT overridden by
`CarScript` or `Car`** — only by the concrete car classes (CivilianSedan etc.). A ripped racing-game car whose config is
`class <MOD>: CarScript` with NO Enforce Script class runs as **bare `CarScript`** (verified in-game: telemetry
`class_name:"CarScript"`), so `CrewCanGetThrough` falls to the base stub `Transport.CrewCanGetThrough`
(`P:\scripts\3_game\vehicles\transport.c:724-731`) which returns `false` in the normal build (`#ifndef CFGMODS_DEFINE_TEST`).
→ gate-2 false → **get-in action NEVER appears**, no matter how perfect the crew bone is. Same trap for
`GetSeatAnimationType` (transport.c:682-687 → `Error("not implemented")`) and `GetAnimInstance` (transport.c:662, used in Start()).

**THE FIX = ship a thin `<MOD>_Base.c` script class (PIPELINE requirement — add to Phase 4).** Modeled on FC
("Frontera Cars", a shipped community car mod): `FC_Uaz_Pickup_Rest_Base extends CarScript`
(FC_Uaz_Pickup_Rest/Scripts/unknown_40493.c:1) overrides `CrewCanGetThrough` (:1017), `GetSeatAnimationType` (:539),
`GetAnimInstance` (:524), `GetCarDoorsState` (:977), `GetDoorSelectionNameFromSeatPos` (:1058),
`GetDoorInvSlotNameFromSeatPos` (:1079), `GetDoorConditionPointFromSelection` (:1165),
`CanReachSeatFromSeat`/`CanReachDoorsFromSeat`. FC cars extend `CarScript` DIRECTLY (config
`class FC_Vaz_2101: CarScript`, FC_Options/data/Vehicles/FC_Vaz_2101/config.cpp:514) — they do NOT re-parent to a
vanilla car. The mod needs a `CfgMods` script module (worldScriptModule files[]) to compile the `.c`.

**Doors are NOT required for get-in.** `GetCarDoorsState` returns `DOORS_MISSING` when no CarDoor attachment exists
(civiliansedan.c:185-192, FC unknown_40493.c:982-985), and `DOORS_MISSING != DOORS_CLOSED` → `CrewCanGetThrough`
returns true → passable. So a script class with NO door attachments gives WORKING get-in (baked doors stay static).
Openable doors = a separate FEATURE (CarDoor classes + door proxies + door `.p3d` + AnimationSources DoorsX +
model.cfg door bones), exactly as FC ships (FC_Vaz_2101 `class FC_Vaz_2101_Door_Driver: CarDoor` config.cpp:326,
`AnimationSources class DoorsDriver` :843).

**Task-3 see-through chunks = s7's GLOBAL winding flip inverted the chunks that were correct-before.** User reports
see-through "gaps" at the engine bay + above each rear fender (symmetric). RPT clean of proxy-not-found (all 9
chunks load) → geometry IS present but inverted (DayZ backface-culls inward winding → looks like a missing proxy).
The SUB_BRZ transform `(−Fx, Fy+Y0, −Fz)` is **det +1** (proper 180° rotation, PRESERVES winding), so the correct DayZ
winding = the glTF winding UNCHANGED. Fix = re-derive per-chunk winding from the glTF source (NO `force_outward`, NO
global flip), or surgically flip back ONLY the chunks the global flip broke (identify by comparison vs glTF normals —
non-tautological because s7 flipped blindly, not to match). Do NOT global-flip again; do NOT iterate in-game.

> Origin: SUB_BRZ s8 2026-06-25 (dayz-mcp broker repaired — kill `--require-version` daemons, run one without it;
> in-game RPT grep + telemetry + user's full-res eye). Cross-ref FC (Frontera Cars) reverse-engineered cars in the
> project root (`FC_Uaz_Pickup_Rest`, `FC_Options`), vehicle-structural-parity.md "componentNN DUAL-TAG" +
> "ATTACHMENT proxy BONE-NAME selection" (now CONFIRMED in-game).

## (added 2026-06-25, s8) WINDING + BUILD lessons from the s7/s8 see-through debug [VERIFIED]

Four pipeline traps pinned while fixing the see-through chunks (§"s7" + §"s8 ... Task-3"). The mechanism and
the global-flip story are in those sections; this is the reusable methodology.

### 1. The offline glTF winding metric is a FALSE-GREEN GLOBAL-flip detector — the DayZ render is the only gate

A per-chunk "winding vs glTF" agreement metric (compare each face's vertex order against the source glTF) reported
**ALL chunks inverted**: pre-fix global agreement **0.127**, post-`force_outward` **0.873** — exactly complementary
(0.127 ≈ 1 − 0.873). A metric that flips the WHOLE set between two complementary values is measuring a GLOBAL flip,
NOT per-chunk correctness — it **cannot discriminate a solid chunk from a see-through one**. Proof it was vacuous:
the known-SOLID main body and the known-SEE-THROUGH engine bay BOTH read "disagree". The anti-vacuity gate ("the
method must flag the known-bad anchors") passed TRIVIALLY because flagging EVERYTHING includes the bad anchors —
a tautology (R22, error-exactly-0/complementary tell). RULE: validate a winding metric against a **known-SOLID
reference reading SOLID** (not only a known-bad reading bad); if it cannot separate solid from see-through it is a
global-flip detector, not a winding checker. The real gate is the **DayZ render** (a face that backface-culls is
inverted); the offline metric is a hint, not acceptance (false-green twice — same lesson as the proxy-frame GATE).

### 2. Per-piece flip with NO per-piece selections → connected-component analysis, then select by spatial criterion

rip-built chunks carry only **material selections** (`color`/`glass`/`interior`), NOT per-piece named selections.
To flip ONE piece that shares a chunk with others you cannot select it by name. Use **connected-component analysis**:
union-find over faces sharing a `point_index` → components; then select the target by a spatial criterion on each
component's centroid/bbox. Worked example (SUB_BRZ engine-bay cavity): isolate front high-y components
(centroid `z < −0.6` AND `y >= 0.85` → **7 comps / 1948 faces**) out of **88** front components — the other 81 were
low-y engine internals to EXCLUDE. Flip the whole file ONLY when a chunk == exactly one piece. Mechanism of the flip
= **reverse per-face vertex order; leave the normal pool untouched** (`tools\patch_winding.py` `rev()`; same as
`flip_winding.py` — the normal pool is global, indexed by `vertex.normal_index`, so reversing face vertex order does
not touch it).

### 3. Build flag: `-Build -PackOnly` is REQUIRED — `-PackOnly` alone runs the STALE PBO

`-PackOnly` on its own SKIPS the build and ships the existing (stale) PBO. A NEW script class (the `<MOD>_Base.c`
from ROOT CAUSE #2) or NEW/edited geometry needs `-Build` to actually compile/repack — filePatching does NOT load
the `worldScriptModule` `.c` or the `.p3d` geometry from the work drive, so "it ran but nothing changed" after a
geometry/script edit is usually a missing `-Build`. Use `-Build -PackOnly` for any change beyond a filePatched
script tweak.

### 4. Visual winding review CONFOUNDS on an UNTEXTURED model — three false "holes"

Reviewing winding by eye on a not-yet-textured car gives three false "see-through" reads that are NOT winding bugs:
- **Untextured GLASS** windows look see-through — that is a TEXTURING matter (Phase 5: a glass material), not winding.
- **Empty WHEEL ARCHES** (no wheels yet = Phase 4) plus tall grass at rocker height read as "lower-flank holes".
- The **untextured-material checkerboard placeholder** is opaque, not a hole.

Discriminator: an **opaque panel that BLOCKS distant terrain at panel height = solid**; genuine through-show appears
only BELOW the rocker line / INSIDE the arches = missing wheels, not inverted winding. A horizontal **Geometry-LOD
raycast** hitting a closed hull corroborates solidity — but note it probes the Geometry/View LOD, NOT the Visual LOD
(a Visual-LOD winding inversion can still render see-through while the Geometry raycast reads solid), so it is
corroboration, not proof. The definitive gate remains the in-game render after texturing.

> Origin: SUB_BRZ s7/s8 see-through debug 2026-06-24/25 (builders `rip_p2_shellproxy.py`, `tools\patch_winding.py`;
> in-game render + RPT). Cross-ref §"s7" (global winding flip), §"s8 ... Task-3 see-through chunks" (det +1 ⇒ glTF
> winding unchanged), and `vehicle-structural-parity.md` proxy-frame GATE (offline false-green class).


## PHASE 5 — TEXTURES (added 2026-06-28, SUB_BRZ Phase 5; core verified in-game)

The reusable texturing pass for a ripped racing-game car. Core confirmed in-game (smoke green: painted body + glass +
collision + stable spawn). Builders updated so car #2 is born textured. Pipeline scripts:
`rip_p5_{materials,swatch,texture,gate,deploy}.py` + `_rip_p5_gate_blender.py` (in `<vehicle-import>`).

### Texture source — what the rip actually ships (verify, the STEP-0 premise was half-wrong)
- **No single paint atlas.** Body paint = a constant carPaint color (BRZ ≈ linear `(0.005,0.105,0.420)`
  → sRGB `#105BAD`). Convert linear→sRGB for the `_co` PNG; the procedural `#(argb)color()` used in
  Phases 1-4 was already linear.
- **`Textures__AO__Swatches__<part>_AO_AO_*.png` are per-part packed NORMAL (RGB, tangent-space) + AO
  (alpha), NOT grayscale AO.** 512² RGBA, ~40% island coverage. Present only for relief parts
  (bumpers/fenders/skirts/wings/hood); the main shell `body_a`/`bodywide_a` have NONE (flat paint is
  correct for a smooth panel). Decode: RGB std≈0.9 unit-length ⇒ normal; alpha continuous inside islands
  ⇒ AO. Build `_co = paint × (AO_MIN + (1-AO_MIN)·AO)` (AO_MIN≈0.55, off-island = full paint),
  `_nohq = swatch RGB` (off-island = flat `(128,128,255)`; green-flip for DirectX Y- is the ONE item
  not verifiable offline — confirm in-game).
- **`LiveryMasks__*` are ~empty for a stock-colour car** (1-11% coverage on the BRZ): livery is negligible
  → v1 body = flat glossy paint, skip the livery projection (B2). "Photorealistic livery" reduces to
  "glossy paint" when the masks are empty — check coverage before planning a projection bake.

### The swatch UV is TEXCOORD2 — and you must VERIFY it, `use_materials=True` is broken
- The importer reads 5 UV layers `TEXCOORD0-4`; `TEXCOORD2` is the per-part normalized `[0,1]` swatch/AO
  space. `TEXCOORD0/1/4` are wide-range tiling channels (absmax ~30). `group.py` previously captured
  `uv.active` (= TEXCOORD0 for body) → wrong channel. Fix = `bm.loops.layers.uv.get("TEXCOORD2")`.
- **`use_materials=True` (the ground-truth texture↔texcoord binding) THROWS on most parts (GameDB absent).**
  So you cannot harvest the binding from the importer. Fallback: TEXCOORD2 + **render-verify** — apply each
  part's swatch through TEXCOORD2 in Blender (unlit emission) and eyeball that the normal detail lands on
  the geometry's panel edges/curves (flat purple on flat areas). A UV-vs-swatch-coverage IoU is CONFOUNDED
  by mirrored islands + partial coverage (0.28-0.81 even when aligned) — use the render, not the IoU.

### Per-face material wiring belongs in the BUILDER (chunk merge loses part identity)
`rip_p2_shellproxy.build_lod` now assigns `face.texture`+`face.material` per face: a part in
`data\sw\swatch_map.json` (per-part `_co`+`_nohq`+rvmat) wins, else the shared class material
(`color→brz_paint.rvmat`, `glass→glass.rvmat`, `interior/trim→matte NormalMapSpecularMap`). Thread the
part stem through each piece tuple `(V,F,UVc,Nc,sel,stem)`. A solid-colour `_co` + procedural glass are
**UV-invariant** → the flat-paint+glass layer works even on `(0,0)` UVs; only the per-part swatch detail
needs the TEXCOORD2 fix.

- **Glass = clone vanilla `dz\vehicles\wheeled\civiliansedan\data\glass.rvmat`** (Super + `renderFlags
  {"noZwrite"}` + ambient/diffuse alpha 0.75; refs `gazglass_nohq/_smdi` which ship in DZ_Vehicles_Wheeled,
  a requiredAddon). Translucent, UV-independent, fleet-reusable. Resolves the "see-through windows = missing
  parts" symptom (that was untextured glass, NOT a winding bug — §"s8 ... false holes").

### WINDING — SUPERSEDED by visual-gates-and-winding.md #10(j) (s20 2026-07-02; reimport gate DEGRADED 2026-08-24 to offline-traced: it cannot be exercised by play alone, it needs an actual reimport, so it closes on the next one)
`__N` was never authored: `rip_p2_group.py:110,131` captures `l.vert.normal` after `bm.normal_update()`
(bmesh drops custom split normals), so `orient_authored` oriented the winding to its own pre-mirror winding
— wrong for EVERY piece (the source glb is winding↔normal consistent 99.99%; the s12 near-global exterior
inversion was this pass, not the rip). THE RULE: keep the raw glTF winding VERBATIM for all pieces (net
rip→DayZ `(-Fx, Fy+Y0, -Fz)`, det=+1); stored normals = smooth(+cross) of the FINAL winding; de-dup
first, then repair only the ~0.5% source-inconsistent FACES by MAJORITY flood-fill per connected component.
The backface-cull render is a HINT (it shows the +cross side; the engine renders the ANTI-cross side).
Plan + numbers: `SUB_BRZ_dev\reviews\2026-07-02-s20-plan-reimport-unico-v2.md`.

### DEPLOY — transplant, never overwrite the structural shell
The Phase-2 rebuild of `sub_brz.p3d` has ONLY the visual LOD; the DEPLOYED shell carries the verified
structural LODs (Geometry/Memory/LandContact/ViewGeo/FireGeo with crew proxies / componentNN / wheel hubs =
spawn + get-in). Deploying the rebuilt shell wholesale destroys spawn/get-in. `rip_p5_deploy.py`:
deployable shell = **rebuilt visual LOD0 (textured, new winding, aligned with the new chunks) + the deployed
shell's structural LODs[1:]** (same car-space; bbox Y matches). Chunks are visual-only → deploy the rebuilt
textured ones. Verify: 8 LODs, 10 proxy refs, ≥50 structural key-selections, body faces > 1000. Backup first.

**Trap (regression, SUB_BRZ 2026-06-28, in-game): the transplant DROPS the 4 visual-LOD wheel proxies.** The
rebuilt visual LOD0 carries the body `brz_chunk` proxies but NOT the vanilla `sedanwheel` proxies that render
the attached wheels → in-game the wheels SIMULATE (Fire proxies intact) but render INVISIBLE, and the
structural gate (24/24) does NOT catch it (it checks View/Fire wheel proxies + structural selections, never
the visual-LOD proxy set; `verify_<mod>.py` `vis.wheel_proxies` is the one check the structural gate skips).
The texture session's smoke missed it too — it spawned with `attachment_count=0` (no wheels attached), so
there were no wheels to be invisible. `rip_p5_deploy.py` must copy the 4 `sedanwheel` proxies into the
rebuilt visual LOD0 **frame-faithful** — the exact 3-point triangles from the pre-transplant visual LOD (NOT
`add_proxy`, which re-canonicalizes the triangle → wrong frame). After ANY visual-LOD-only rebuild (texture
pass / decimate / transplant) re-verify visual-LOD wheel-proxy count == 4. **CAVEAT (corrected 2026-06-28):
restoring the proxies is NECESSARY (vanilla + the LFQuad control carry them in the visual LOD) but was NOT
confirmed SUFFICIENT — SUB_BRZ wheels stayed INVISIBLE in-game even after the restore.** Wheel RENDER also
needs (a) a wheel ITEM attached to each slot and (b) a correct proxy↔slot binding (index/position matching the
config wheel slots). Diagnose invisible-wheels END-TO-END in-game (attached-but-not-rendering vs no-attachment;
compare the proxy index/anchor against the LFQuad control that renders) — do NOT assume the proxy restore
alone fixes it. The offline `vis.wheel_proxies` PASS does NOT prove in-game render.

**RESOLVED (s12, 2026-06-28) — the two pieces the restore was missing:** restoring the visual-LOD wheel
proxies is necessary but needs (1) the right FRAME and (2) COMPANION selections.
1. **Frame.** A restored proxy via `add_proxy`/`rotation=None` keeps py3d's IDENTITY frame `((1,0,0),(0,1,0),(0,0,1))`
   → the engine renders the wheel rotated ~90° (invisible). Vanilla uses a **mirrored-by-side** frame, measured
   on `civiliansedan_mlod` VISUAL LODs: anchor **x<0** → `((-1,0,0),(0,0,1),(0,1,0))`, **x>0** →
   `((1,0,0),(0,0,-1),(0,1,0))`. SUB_BRZ reuses the vanilla `sedanwheel` geometry, so copy the **VANILLA** frame
   (NOT kt's — its mirror differs because its wheel geometry differs). Reframe in place by anchor-x sign:
   `canonical_proxy_triangle(p0=current_anchor, rotation=frame_by_side, scale=0.1)` overwriting the 3 triangle pts.
2. **Companions.** Vanilla + kt carry `wheel_X_Y` companion selections in the VISUAL LOD too (not only View/Fire);
   the import had ZERO there → the attached wheel has no bone binding (and no spin anim target). Add them with the
   `fix_wheel_binding.py` pattern (`lod.new_selection(wn); ns.points=dict(proxy.points); ns.faces=dict(proxy.faces)`),
   mapping proxy→`wheel_X_Y` by the SAME centroid rule used for View/Fire (so model.cfg spin stays consistent).
Builder `rip_p5_deploy.py` must emit BOTH on the rebuilt visual LOD0. Offline re-verify: each visual wheel proxy
derives to the by-side vanilla frame + the 4 `wheel_X_Y` companions present. In-game (s12): wheels RENDER on the
hubs after this fix. **Lead-correction:** the s11 "vanilla has NO visual-LOD wheel proxies, remove them" claim was
FALSE — vanilla CivilianSedan has 5 in EVERY visual LOD (verified on the real `.p3d`).

### LAUNCH gotcha for the in-game smoke (cost a session)
DayZDiag launched from an AGENT-owned process (a `run_in_background` task, or `dayz-test.ps1`'s own
bind-wait) is killed when that process/job ends — the server dies mid-CE with no RPT, the client survives.
`dayz-test.ps1` ALSO false-negatives its 240s bind-wait (the server bound, `Get-NetUDPEndpoint` confirmed,
but it refused to launch the client and killed the server). Fix: launch server + client via a `.bat` with
`start ""` (true detachment, independent process group) — they then survive across agent tool calls. Poll
`Get-NetUDPEndpoint -LocalPort 2302` yourself. The MCP bridge `legacy_blocked` ("poll did not include ver=")
is just incomplete init — it goes `ok` once the mission fully loads. Cross-ref the dayz-test-ingame skill.

## VISUAL OVERHAUL — cross-car lessons (added 2026-06-28, SUB_BRZ s12)

Once a ripped racing-game car DRIVES, the rest is visual and it RECURS on every car. Do it from the source, not by eyeballing.

### Paint color: read it from `ManufacturerColors.bin`, don't guess
The exact factory paint lives in the rip's `ManufacturerColors.bin` (per car). Layout per color entry:
[selection-name strings: Body/Hood/Mirror/Wing/…] + **3×float32 sRGB tint** + the `_library` materialbin path.
Entry **[0] = the default color**. Parse: for each `Game:\Media…materialbin` string, the 3 floats are the 12
bytes ending 1 byte before the path's `Game`. Non-vacuity check: run the whole table — white≈(0.99,…), black≈(0.08,…).
SUB_BRZ default = `wrblue_pearl_sub` → (0.0157,0.290,0.639) = **#044AA3** (a prior pass GUESSED #105BAD = wrong).
Reusable: `decode_color2.py`. Note: `the clay-render output\out` renders are CLAY (no color) and `_library` materials are
PROCEDURAL — there is **no painted-car bitmap to copy**; the DayZ target is solid-color-per-piece + AO.

### Black panels + see-through = WINDING, not texture — DECODE the `_co` before touching it
Before chasing an "atlas / UV-out-of-range" texture bug, decode the deployed `_co.paa` and measure dark%. On
SUB_BRZ every `_co` was solid/blue with **dark%=0.0** → the "black panels" were inverted-winding faces
(backface-culled → the dark interior shows through), i.e. the SAME bug as see-through. Don't regenerate textures.
The `_co` should be **solid color (UV-invariant)** regardless: imported chunk UVs are arbitrary, so a solid `_co`
(`Image.new("RGB",(256,256),BLUE)`) reads right on any UV; per-part swatch `_co` must fill OFF-island with the
paint color (never black) — `rip_p5_swatch.encode_part` already does `co[~cov]=PAINT`.

### Winding orientation — SUPERSEDED (s20 2026-07-02): keep the raw glTF winding; do NOT flip from photos
The glb authored normals are winding-consistent 99.99% (inverted NOWHERE) and the pipeline `__N` was never
authored (`rip_p2_group.py` captures `l.vert.normal` after `bm.normal_update()` = smoothed pre-mirror
winding — the "oracle" was the mirrored winding itself). Do NOT flip from photos and do NOT orient to an
oracle: keep the raw glTF winding VERBATIM for all pieces (net `(-Fx, Fy+Y0, -Fz)`, det=+1) and repair only
the ~0.5% source-inconsistent faces by per-connected-component MAJORITY flood-fill. What REMAINS true: the
`geometric-winding vs stored-vertex-normal` check is tautological (normals follow winding by construction) —
use vanilla-anchored absolute stats instead (stored·cross>0 ≈ 96-99%; roof cross-outward ≈ 1.6%). See
visual-gates-and-winding.md #10(j) + `SUB_BRZ_dev\reviews\2026-07-02-s20-plan-reimport-unico-v2.md`; the reimport's
in-game gate is PENDING.

### Suspensions + axles: do NOT exclude them — the wheels visually ride on them
Phase 1/2 EXCLUDED `suspension_a`+`undercarriage_a` (rip droop) for a Phase-3 re-pose that never happened → in-game
the visible suspension/axle the wheels sit on is missing (user-reported, s12). Re-include them (re-posed to ride
height); they're part of the look even though they're not the drivetrain sim. Add to the INCLUDE manifest, not EXCLUDE.

### Driver / ViewPilot LOD must carry the car's OWN interior, not vanilla `civiliansedan_int1`
First-person in-seat renders the pilot/interior LOD. If it falls back to vanilla `civiliansedan_int1` you get a
mismapped/overlapping interior (user photo, s12) that only looks right from a free admin camera (which renders
LOD0). The pilot LOD needs the car's own interior geometry. Separately, the LOD0 interior also needs its winding
fixed (it sees-through like the exterior).

### Paint finish — metallic/pearl is an APPROXIMATION; high specular AMPLIFIES normal-map artifacts
source pearl paint (flake + clearcoat) is not reproducible in DayZ's Super shader — aim for an approximation:
a solid `_co` of the source color + the Super stages (specular / fresnel / env reflection). Two s12 findings:
- Raising specularPower (180→300) + brighter SMDI made the reflection clearly better (user: "the reflection is much better").
- BUT high specular AMPLIFIES any per-part `_nohq` normal-map artifact (green-flip / DXT1 banding) into visible
  speckle on the paint ("pixelated"). Levers to try: `--flip-green` the normals, lower specularPower a touch, or
  flatten the per-part normal. Also: the raw `ManufacturerColors` BaseColor reads "washed out / dull" vs the
  pearl-rendered car — push the blue MORE vibrant than the raw source triplet to compensate for the missing flake.

### Original rim — swap the proxy TARGET, keep the vanilla slot
The rip ships the real rim (e.g. `oz_rallyracing_wheellf.modelbin`); v1 uses vanilla `sedanwheel` (rim = post-MVP
cosmetic). To show the original rim: build a custom wheel `.p3d` (local-centered, radius ≈ vanilla sedanwheel
0.3587, full Geometry/Memory/ViewGeo/FireGeo LOD set) and point the wheel proxies at it (`proxy:...\<rim>.NNN`)
KEEPING the vanilla-mirrored visual-LOD frame + the `wheel_X_Y` companions (edit in place, never `add_proxy`).
The config keeps the vanilla `CivSedanWheel_*` SLOTS — the ITEM stays vanilla, only the displayed model changes.
4 corners by instancing/mirror (negate Nx on the right side for winding).

### Material assignment — read the per-mesh material from the `.modelbin`, do NOT paint everything blue
The single biggest per-car time-sink is assigning paint/metal/glass by eye. DON'T — the source has it. Each
part's `.modelbin` embeds the `.materialbin` path(s) it uses as ASCII strings; the path encodes the material
TYPE (`_library\materials\_fmnext\<TYPE>\`). Extract it with the reusable `tools\extract_part_materials.py`
(string-scan, no format parse): part → materialbin → TYPE ∈ {PAINT, METAL, CHROME, GLASS, PLASTIC,
INTERIOR(leather/fabric), RUBBER, LIGHT(emitter), CARBON, MIRROR, BLACK(glass_edge/blackframe), PLATE, BADGE}.
The naive pipeline ("paint every non-swatch face the body color") mis-assigns the body color to METAL parts
(exhaust, wing, roll cage, undercarriage), and leaves the glass edge-trim + interiorLOD1 wrong. **Systematic
builder (do this once, every ripped car inherits it):** parse mesh→material from the source-game `Model` blob
(`carbin_importer.py` `Model`: `meshes_length`+`materials_length`, mesh carries a material index) STANDALONE
(no Blender), classify each material, and assign a DayZ rvmat per TYPE from an author-once **TYPE→rvmat table**
(PAINT→car-paint with the color, METAL→gunmetal/steel, CHROME/MIRROR→chrome, GLASS→glass, BLACK→opaque dark,
PLASTIC→matte black, INTERIOR→leather/fabric, RUBBER→matte black, LIGHT→emissive, CARBON→carbon). Only
`carpaint` on a **paintable selection** (Body/Hood/Mirror/Wing, listed in `ManufacturerColors.bin`) gets the
body color (default = entry[0]). This removes the per-car eye-tuning and fixes, at the root: blue-on-metal,
white-interior-seen-through-glass (interiorLOD1 / interior winding), and black-bits-on-glass (glass_edge /
blackframe = opaque trim, not the see-through window). Origin: SUB_BRZ s12b — user directive "no trial and error".

### Material map — IMPLEMENTED + corrected (SUB_BRZ s13; method offline-verified, in-game gate PENDING)
The s12b plan was built. Four corrections/invariants the next ripped racing-game car needs UP FRONT:
- **Classify by the materialbin PATH FOLDER, not the instance name — the name LIES.** rollcage meshes named
  `leather_MGL`/`plastic_lgl` resolve to `…\Metal\Steel.materialbin` = METAL. The folder
  (`…\materials\_fmnext\<FOLDER>\`) is the canonical TYPE; `specialcase\` is keyed by FILE (blackframe/blackhole→
  BLACK, mirror_*→MIRROR, undercarriage→METAL). `extract_part_materials.py` (per-part string-scan) is only a HINT
  (returns a SET; 50/84 SUB_BRZ parts are multi-material) → you NEED per-mesh. Standalone reader
  `rip_material_map.py` copies BinaryStream/Bundle/Blob/Model/Mesh from modelbin_importer (NO bpy): per part,
  visible meshes (LOD+render_pass filter) in order, path→TYPE.
- **The import already splits meshes:** each Blender object is one mesh named `"<mesh.name> <material.name>"`
  (modelbin_importer L1237). `rip_p2_group` tags every face with its TYPE by object-name lookup → npz
  `<part>__MAT` (geometry byte-identical — assert V/F vs backup).
- **Apply WITHOUT regenerating geometry.** Regen (`rip_p2_shellproxy`) uses `add_proxy` + rebuilds shell/chunks
  → destroys P0 wheels, exterior winding, ViewGeo, crew. Instead REPAINT the DEPLOYED p3d by CENTROID: build
  {centroid_DayZ→TYPE} from the npz (part_dayz x,z+Y0,y), match each visual face by rounded centroid (validated
  100%, max NN 6 µm), reassign `face.material`/`face.texture` ONLY → `rip_p5_repaint.py` (`--apply`; dry by
  default). Structural LODs/proxies untouched, G3 stays 4/4.
- **Repaint only METAL/CHROME/MIRROR/BLACK/CARBON — NEVER PLASTIC.** Widebody flares are PLASTIC in the source but
  painted body color (PLASTIC = 54% of SUB_BRZ faces); remapping them to black wrecks the car. PAINT/GLASS/INTERIOR
  keep their shared materials. TYPE→rvmat authored once in `rip_p5_typemats.py` (brz_metal/chrome/black/carbon).
- **wing_b = PAINT** (the s12b "wing=METAL" was wrong — the path is `paint\paintedmetal`; the extractor/path is the fact).
- Pack `-BuildOnly -PackOnly` (MLOD raw keeps face.material; binarize would drop it).
Order: `rip_material_map.py` → `rip_p2_group.py` (Blender) → `rip_p5_typemats.py` → `rip_p5_repaint.py --apply`
→ pack. STATE: applied s13; exterior (colour/lights/mirrors/per-mesh) in-game-confirmed by the user.

### Wheels / glass / interior / suspension — applied s13 (exterior confirmed; finer items pending)
- **Original rim from the rip — kill the motion-blur discs FIRST.** `oz_rallyracing_wheellf` ships `blur*`
  meshes (smooth discs that hide the spokes when spinning) → they make the rim look hollow/solid and were
  why blind scripts rendered a hollow centre. Delete every `blur*` mesh, then clean the driveshaft (verts
  x<−0.10, the axle to the diff). Build the TYRE procedurally — a torus reads as a BALLOON; use a revolved
  flat-band profile (walls + arc shoulders + circumferential tread grooves, width ~0.30). Scale the
  assembled wheel to vanilla radius 0.359 and TRANSPLANT onto sedanwheel_mlod.p3d (replace LOD0 visual,
  KEEP its Geo/Mem/View/Fire collision LODs). Point the wheel proxies by RENAMING the
  `proxy:...sedanwheel.NNN` selections to `\<Mod>\<wheel>.NNN` — **NO `.p3d` suffix**. The doubled
  `\<Mod>\<wheel>.p3d.NNN` form makes the engine seek `<wheel>.p3d.p3d`, DROP the proxy, and spawn with
  `wheelPresent=0` → `PHYSICS (W): Proxy with name 'CivSedanWheel_X_Y' was not found in FireGeometry` =
  the perceived spawn *freeze* + "revs in 1st, does not drive" (SUB_BRZ s26, RPT-verified 2026-07-08; the
  Visual0 kept the correct `sedanwheel` proxy so the wheel RENDERS but does not SIMULATE). The transplanted
  `<wheel>.p3d` must ALSO keep sedanwheel's 5 Memory collider points (ce_center/ce_radius/boundingbox_*/
  invview) or the collider degrades to cube-size (contact=0); if it does not, point the ViewGeo/FireGeo
  proxy at vanilla `\dz\vehicles\wheeled\civiliansedan\proxy\sedanwheel.NNN` instead. See
  `vehicle-structural-parity.md` §"MLOD proxy selections carry NO `.p3d` extension". NEVER add_proxy. Do the rim assembly
  in BLENDER INTERACTIVE (MCP) — eyes catch the blur-disc / balloon-profile issues that blind scripts miss.
  `rip_build_wheel.py` = the transplant. (rim is front-left only; mirror for 4 corners.)
- **Glass "double pane z-fight" — RETRACTED (s20).** `glass*int_a` panes are the legitimate cabin-side layer
  of the two-sided glass pair (raw winding ~92-100% cross-outward = anti-cross side faces the cabin); the s13
  artefact came from the inverted import orientation (orient_authored — deployed chunk_06 glass 73.9%
  cross-outward = renders inside-only, bug B2), not from an inherent double-pane z-fight. Do NOT run
  `rip_fix_glass_zfight.py`; keep both panes with the raw glTF winding (reimport in-game gate pending).
- **Interior see-through / invisible seat = single-sided.** Setting `face.flags |= 0x20000` did not
  produce two-sided rendering; the interior stayed see-through in-game (see invariant #1 under
  "VISUAL CORRECTNESS" below). The route confirmed to work is double-siding the geometry, subject to
  the resolved-vertex budget (this interior was ~72k faces; duplicating drove chunk_07 to 112k
  resolved, above the 65535 cap). The `0x20000` vs BI-wiki `0x00000020` dispute is CLOSED as moot:
  `binarize.exe` discards the MLOD per-face `flags` field outright, so neither value ever reaches the
  game. Measured 2026-08-24 by binarize round-trip; invariant #1 carries the method and its controls.
- **Excluded geometry (suspension/axles).** `rip_p2_shellproxy` SKIPs `suspension_a` (rip full-droop pose).
  Re-include by INJECTING into an existing chunk (`rip_add_suspension.py` → chunk_09, no add_proxy), forced
  to METAL (its `paintedmetal` mis-maps to PAINT/blue on the arms). `rip_coverage_audit.py` lists rip-vs-p3d
  gaps up front (paintable-variant parts + skeleton/proxylod are fine to omit).
- **Body colour FLAT, not swatch.** Body PAINT = a flat solid `_co` (`rip_decode_color.py` value); the
  per-part AO/normal swatch's DXT1 blocks read in-game as "pixelated". Keep specular low (~0.28) so the Super
  shader doesn't wash the blue out, and darken the raw ManufacturerColors value a touch if it reads light.


## VISUAL CORRECTNESS — single-sided interiors, glass, normals, materials (SUB_BRZ s15, 2026-06-30)

The decimated rip body drives and the exterior renders, but the cabin/glass need a visual pass. Five
invariants, each verified in-game (the user's eye is the gate):

1. **MLOD per-face `flags` do NOTHING in DayZ, because `binarize.exe` discards the field.** Flagging
   single-sided interior faces with `0x20000` left them see-through in-game (first real test of the s13
   assumption); the mechanism was pinned offline on 2026-08-24 with a binarize round-trip. Three MLODs
   differing ONLY in `face.flags` on 2092 faces — `0`, `0x00000020`, `0x00020000` — binarized to a
   BYTE-IDENTICAL model (sha256 620d4fec1646fcdb...). Two positive controls in the same run did come out
   different: moving one point by 1 cm, and clearing the texture on those same faces. So binarize reads
   the file and honours other per-face fields; it drops `flags` specifically. To render a surface from
   BOTH sides, **double-side the geometry** — no flag value works, so do not look for one.

2. **Double-side = a reversed-winding twin per face with the NEGATED PER-VERTEX normal of the source
   (smooth, deduped), NOT a flat per-face normal.** A flat twin normal kills vertex sharing and explodes the
   resolved-vertex count (chunk07: 22k→103k flat vs 22k→44k smooth-negated). The 65535 cap is a binarize
   limit; packonly MLOD tolerates more (a ~82k-resolved ViewPilot still renders) but stay under it. The tool
   `rip_double_side_interior.py` uses flat normals — fix it to negated-per-vertex before reuse.

3. **Two-tone glossy paint = shell-vs-chunks NORMAL-SIGN mismatch — SUPERSEDED (s20 2026-07-02, see
   visual-gates-and-winding.md #10(j)).** The s15 two-tone was a RELATIVE shell-vs-chunks mismatch; the chunks' `+cross`
   normals were the CORRECT convention (vanilla stored·cross>0 = 96.2%, brz_int 99.5% in-game OK) and the
   deployed shell at 0.5% is the anomaly (prime B1 bright-triangle candidate). Do NOT negate the cross:
   stored normals = smooth(+cross) of the FINAL winding for shell AND chunks (`decimate_rebuild.py` must be
   set back to +cross); shell-vs-chunks agreement only proves internal consistency, not correctness
   (reimport in-game gate pending).

4. **source interior materials are near-BLACK** (brz_black diffuse 0.015, brz_interior 0.13, brz_trim 0.095) →
   the cabin reads as an invisible void in DayZ lighting even when solid (geometry double-sided). Raise them
   (s15: 0.015→0.04 / 0.13→0.20 / 0.095→0.16). Note brz_black is shared interior+exterior trim, so
   brightening also greys the exterior black trim a little.

5. **First-person (ViewPilot LOD res=1100) — DOUBLE-SIDE it; orient-inward is WRONG (SUB_BRZ s17, CONFIRMED in-game).**
   The 1PP camera sits at the seated player's HEAD (`dayzplayercameravehicles.c` extends `DayZPlayerCamera1stPerson`),
   and DayZ renders the vehicle's ViewPilot(1100) LOD there. A single-sided rip interior renders as **"few things
   drawn + you see the world through the car"** from the seat — DayZ's pilot-view winding culls it, and the
   `0x20000` (NoBackfaceCulling) flag does NOTHING (invariant #1). **Orientation is NOT the fix** (s15's orient-inward
   FAILED in-game): measured SUB_BRZ 71-90% of faces toward the head vs vanilla civiliansedan 57-60%, yet vanilla
   renders and SUB_BRZ didn't → *more-inward ≠ more-visible*; ~85% single-sided faces get culled leaving ~4k
   scattered = the "few things". **FIX = double-side the ViewPilot interior** (per face: a reversed-winding twin with
   the NEGATED per-vertex smooth normal, deduped in the pool) + set all ViewPilot face flags to 0 (cosmetic
   only: binarize discards the field — invariant #1).
   Feasible once resolved-verts < ~32k (doubles to <65535); deployed SUB_BRZ was 24k→43k (s15's "82k can't double"
   was a stale, larger ViewPilot). Diff vs vanilla that pinned it: vanilla ViewPilot has 13 proxies (incl.
   `prox_int`) and SUB_BRZ had 0 — that half holds. The "vanilla flags=0" half does NOT: vanilla ships
   binarized, where per-face flags do not exist, so that number came from a debinarizer that hardcodes
   `face.flags = 0` (`odol_to_mlod.py:115`) — the instrument answering its own question. It justifies
   nothing either way, since binarize discards the field. In-game s17: "the interior now draws" (user).
   RESIDUAL (separate, material pass): the rip interior reads GREY (brz_interior_fp/brz_trim near-grey) — needs
   proper interior colour, not a geometry fix.
   SUPERSEDED as primary fix by visual-gates-and-winding.md #10(i)/(j) (s20): the defect was import ORIENTATION; the s19
   in-game-confirmed fix is single-sided RAW winding as a prox_int-style dedicated proxy. Double-siding
   remains a fallback only (~2x resolved verts toward the 65535 cap).

**Glass:** car-window glass is single-sided + transparent (ambient/diffuse alpha ~0.22-0.32, `noZwrite`,
Super shader — NOT the "Glass" PixelShaderID, which is building glass). Double-siding glass double-blends the
alpha → too opaque (s15 mistake, reverted). Keep glass single-sided; if it is invisible from outside that is a
winding/orientation issue, not alpha. **Per-piece material correctness (wipers→plastic, bumper→metal) must
come from the SOURCE part map, not spatial bounding boxes** — bboxes catch neighbour pieces (fender/hood).

6. **Duplicate-face z-fight (body speckle "all over") = a source ASSEMBLY defect, NOT winding.** Every body face is emitted twice (coincident, same-winding, different UV channel), PREDATING decimation -- the s7-s15 "winding" red herring. Detect NON-tautologically by counting coincident faces per `(frozenset point_indices, winding-parity)` + per identical vertex positions (clean ~0, duplicated 10-70%); fix = de-dup keeping 1 per (position-set, normal-direction), preserving opposite-winding double-sides, never a `proxy:` face. `dedup_faces.py`+`position_dedup.py`. SUB_BRZ s16: -20320 faces, confirmed in-game. Add a de-dup pass to the importer. Full entry: #10 (e) in `visual-gates-and-winding.md`, indexed from invariant 10 in `invariants-import-mesh-and-winding.md`.

## DOORS / movable parts — the rip ships them PRE-CUT with hinge locators (SUB_BRZ s36, 2026-07-17)

source-game versions every movable part as its OWN model (the source game animates them: `MojoConfig.xml`
`doorLF`/`doorRF` autovista events). BRZ Manifest: `scene\exterior\doors\doorlf_a.modelbin` (door
sheet, authored-LOD bitmask) + `doorhandlelf_a` + `doorjamblf_a` + `scene\interior\doors\
doorcardlf_a.modelbin` (interior card). Left side only (right = mirror, standard RF pattern).
Hinge axes ship in `Locators.xml`: `carLocator_doorLF/RF` (BRZ: x ±0.884088, y 0.495741,
z 0.006927, source frame) + `carLocator_doorHandleLF/RF` + `carLocator_entryDoorLF` — exactly the
axis `class Doors`/AnimationSources needs, same transform as the geometry.

RCA (why this section exists): SUB_BRZ assembled the body WITH the doors fused into the proxy
chunks, then s34/s35 planned door removal as "manual doorcard marking in Blender" because the
cabin census was ambiguous (17k/30k faces captured by the footprint, no discriminator). Both were
non-problems: (a) the pre-cut rip pieces + known transform (`dp=(x, z+Y0, y)`, Y0 per car) make
fused-face identification a tri_signature/centroid MATCHING job against the rip piece (the exact
pattern of `s34_chunk_03_census.py` for calipers); (b) a parallel lane (s33) had ALREADY built
`sub_brz_doors_{driver,codriver}.p3d` from the authored LODs (`work\s33_f2_doors\
C2b_checkpoint.md`: 9 LODs each, collision preserved, LOD0 floor set by the doorcard's authored
bitmask 0x0003 — no sub-LOD exists, accept the overage) and the HANDOFF never registered it, so
two later sessions budgeted work that was DONE. Lessons: read the Manifest for `doors\`/movable
parts BEFORE planning any body-cut surgery; register built artifacts (path + checkpoint) in the
LIVE-STATE the day they are built.

## 2026-07-18 (s37) — B1 wheels-invisible RCA closed: identity proxy frames + vis2 without proxies

History: s35 saw invisible wheels in-game; s36 refuted 7 hypotheses and applied the candidate fix
"add visual LOD 0.0 to the wheel item" — REFUTED in-game s37 (wheels attached 4/4 server-side,
sim fully functional — accelerates, wheelspins, upshifts, takes damage — and ZERO render, no
raycast hit at the hubs). RCA s37 (an agent review + independent double measurement): the shell's four
wheel proxies in visual res 0.0 carried an IDENTITY frame (py3d `add_proxy(rotation=None)`, point
flags 0) and visual res 2.0 had NO wheel proxies at all; ViewGeo/FireGeo carried the correct
per-side lateral frames (flags 63). Control: civiliansedan MLOD ships sedanwheel.001-.005 in EVERY
visual LOD (1/2/3/4/6) + VG + FG, frames mirrored per side. Minimal fix (shell-only, no config/
model.cfg/item changes): copy the ViewGeo triangle onto the vis0 proxy in-place (preserves all
selection membership) + `add_proxy` into vis2 with a leaf companion. Door proxies measured on the
same control: UNIFORM frame `((-1,0,0),(0,0,1),(0,1,0))` on all four sedandoors_* proxies (no
per-side mirroring — door models are mirrored per side instead).
B5 (native client crash on the ruined-wheel swap at 60+ km/h, minidump): the CfgNonAIVehicles
class `ProxySUB_BRZ_Wheel_destroyed` did not match the proxy file basename `sub_brz_wheel_ruined`
(vanilla ties them: `ProxySedanWheel_destroyed` <-> `sedanWheel_destroyed.p3d`) — 1-line class
rename. Both fixes verified offline (double-measured); in-game gate = the next drive-test.
Method lesson: the cheap discriminator was measuring the visual proxies' FRAMES against the
control BEFORE touching the item's LODs — s36 spent its cycle on the item asset instead.
Promoted (2026-07-18): invariant 21 in `invariants-get-in-and-seats.md` and the family B cookbook `cookbook-attachment-invisible.md` of the rip-vehicle-import skill.

**Changing the TRACK means moving the WHOLE corner, and the limit is the hub, not the arch (SP-416, added 2026-10-01, SUB_BRZ s97).** [EXACT] On that car the four wheel proxies carried the SAME frame in every LOD (no per-side rotation), unlike the vanilla controls above, whose wheel frames are mirrored per side (it is the door proxies that share one frame); so shifting the wheel mesh inside the wheel `.p3d` moved the left wheels inboard and the right ones outboard at the same time. Read the four frames first: it is one call. To change the track, move per side: the proxy triangle in every LOD that carries it, the `wheel_<side>_<axle>_*` memory points (axle, damper, damper_axis, damper_land, steering, steering_axis), the `..._damper_land` Geometry box, and the brake/hub chunk plus its merged copies in the far LODs - on SUB_BRZ s97 that was 748 shell points and 1,570 chunk points in total for 10 cm of track (5 cm per side). The travel limit is the brake/hub box reaching the rim's inner face, not the wheel arch; profile the rim sweep (local x, radius) against the brake points before spending a cycle.


## Wheel proxy frames are a `(frame, referenced model)` pair (SP-156, added 2026-08-31)

Do not promote an anchor-X frame literal across wheel models. The sedanwheel
literal above is calibrated only for that referenced geometry. A working
Landrover control measured the opposite pair for `Landrover_Wheel`: `x>0` uses
`((-1,0,0),(0,0,1),(0,1,0))`, and `x<0` its mirror. Derive both sides with
`py3d.derive_proxy_frame` from a known-good car that uses the same wheel item,
then require the candidate to match. A negative fixture that swaps the two sides
must fail.


## Prove workspace identity before importing or auditing (SP-330, added 2026-08-31)

A rip media tree may contain several vehicles. Before packaging a workspace,
select 3-5 names from the intended `manifest`/`include.txt` and require them in
the `Manifest.xml` under that exact vehicle directory. A work-folder name is not
identity evidence. Missing names block the handoff instead of being explained as
an incomplete export after the audit.

## Route primitives by functional owner, never by material alone (SP-158, added 2026-08-31)

Freeze import routing per source primitive with a stable key that includes the
source node instance/breadcrumb and primitive index, or an adapter-defined equivalent;
a mesh index alone is not unique for instancing or multi-primitive meshes. Require
every included primitive exactly once. Material identifies a surface, not the object
that must move it: a steering-wheel decal must stay in the steering proxy even when
it shares `INT_DECALS` with the dashboard; door fasteners and decals must follow the
door. Add negative fixtures for movable-part primitives so a material-only router
must fail.

## Wheel items are local; body proxy chunks are model-space (SP-159, added 2026-08-31)

A glTF/FBX intermediate commonly holds wheel vertices in car world-space. Before
emitting a separate wheel `.p3d`, derive its source hub deterministically, subtract
that centre from points, and require `abs(bbox_center_axis) < 1e-4 m` on every axis.
The host proxy then supplies the hub translation once. Without this step the source
translation and proxy anchor are both applied. This bbox-centre gate is wheel-only:
hinge-local doors, hoods and trunks are intentionally not centred. Pure body proxy
chunks retain the model-space convention in `vehicle-structural-parity.md`.

## Named selections can carry primitive identity through packonly (SP-162, added 2026-08-31)

**[MEASURED OFFLINE ON ONE RAW PACKONLY TOOLCHAIN]** An MLOD with 170 selections,
mixed case and names through 63 characters survived `AddonBuilder -packonly -> PBO ->
ExtractPbo` byte-identical, including selection order and point/face membership. This
is a capability canary for a route already declared raw packonly, not a recommendation
to choose that build mode. Re-run generation, packing, extraction, SHA-256 and semantic
name/order/membership comparison when the environment changes. This does not cover
binarized ODOL; a binarized route needs its own preservation spike.

## Label, decal and tiled-pattern UVs are semantic exceptions (SP-335, added 2026-08-31)

The `TEXCOORD2` swatch rule above does not apply to every face. Measured bezel
labels, decals and shifter graphics sample their atlas from `TEXCOORD0` without a
V flip. Tiled patterns use `TEXCOORD1` multiplied by the material's MTPR factors.
Do not substitute the pipeline unwrap: DayZ materials do not add the missing UV
transform by default, so tiling must be baked into face UVs with sampler wrapping.
Require an UV-over-atlas overlay before accepting either route.

## Locate the build source through the build script, then prove it by data (SP-343, added 2026-08-31)

Before basing a fix or audit on a mod tree, inspect `build_*.ps1` for its `$source`
root and compare a content hash from that root with the corresponding blob in the
deployed PBO. A display/archive copy can be complete and still be an old generation;
folder recency and naming do not establish build ancestry.
