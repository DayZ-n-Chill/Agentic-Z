# Visual gates and winding: the session record for imported cars

The per-session record of invariant 10, "imported-car offline visual gates that lie", sub-entries #10(a) to #10(o), followed by the later winding lessons: what `validate()` cannot prove, why a Blender culling render cannot adjudicate winding, and how to choose the sign of a face a script adds or moves.

> Status: field notes measured in game and offline on third-party mods, each named in its entry (LFQuad, LFQuad2, SUB_BRZ, MercedesAMGLF, LFHeli OH-1). This is third-party mod behaviour, not vanilla, and the measurements were not repeated on `P:\`. Every vanilla citation is written with its full `P:\` path and was opened on the vanilla data on `P:\` (a 1.30 build). The scripts the entries name (`gate_car.py`, `winding_consistency.py`, `rip_p2_build_v2.py` and the like) are the import pipeline's scripts in those mods' work folders and are not part of this repo; each entry states the method so the check can be rebuilt. Labels such as s14 or s20 number the work sessions in date order. "Invariant N", "preflight #N" and "#N" all mean the numbered invariants; `skills/dayz-vehicles/SKILL.md` lists which file holds each number.

This is the historical, per-session record of sessions s14 to s23 across LFQuad, SUB_BRZ and MercedesAMGLF. Superseded entries are kept under their own headers as history. The single operative winding rule (#10j, THE RULE) is stated under invariant 10 in `invariants-import-mesh-and-winding.md`; this file is the full detail behind it. A citation of the form `#10(x)` in another file resolves against the sub-entries below.

## Vanilla anchors checked on `P:\`

- The fluid enum `ETransportFluid` (`FUEL`, `OIL`, `BRAKE`, `COOLANT`) starts at `P:\scripts\3_game\vehicles\transport.c:52`.
- `CarFluid` aliases it at `P:\scripts\3_game\vehicles\car.c:18`.
- The first-person vehicle camera that #10(g) is about, `DayZPlayerCamera1stPersonVehicle`, is declared at `P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercameravehicles.c:4`.
- The control model the measurements below use is `P:\DZ\vehicles\wheeled\civiliansedan\civiliansedan.p3d`. It is binarized (ODOL), which py3d cannot read, so the values quoted from it were read with an external ODOL reader, which is not part of this repo, and were not read again here.

---
10. **Imported-car offline VISUAL gates that LIE — the #7 family (offline geometry heuristic ≠ in-game truth).**
   (a) **Steering axis is NOT a reliable offline plane-fit.** A ripped/regen steering wheel is rim+spokes+hub,
   not a flat disc — PCA / rim-only fit / normal structure-tensor disagree by **12–48°** on the SAME mesh
   (MercedesAMGLF s14, measured 4 ways). The offline disc-normal gives only the CORRECTION DIRECTION (more/less
   reclined vs the current `drivewheel_axis`), never a trustworthy angle. Use the all-points PCA normal through
   the wheel centroid as a first cut, then confirm the flat-in-plane spin IN-GAME / against the user's full-lock
   wheel photos — that is the gate. "PCA the disc normal" on its own over-claims offline
   reliability. (s14: applied offline, in-game confirmation pending.)
   (b) **A single-sided imported shell renders SEE-THROUGH from INSIDE the cabin** (roof + floor especially — no
   interior backing). The body is solid from OUTSIDE (winding correct) yet the driver sees sky/ground through
   roof/floor because those skins backface-cull from below/above. Fix = **per-piece double-side**, NOT a global
   winding flip (that inverts the whole car — the s13 disaster in #7): duplicate each roof/floor face with
   reversed winding (`[0,2,1]`) + the normal NEGATED — append the negated vector to `lod.facenormals` (a POOL
   indexed by `vertex.normal_index`, so reusing the index would NOT flip it) and add the twin to the same
   selections. Additive ⇒ it cannot invert the car; identify roof/floor by region + geometric normal, but the
   driver-seat view is the gate. (MercedesAMGLF s14, applied; in-game pending.)
   (c) **Debug-spawn fluid gauges read RED unless you fill ALL four.** `OnDebugSpawn` must also
   `Fill(CarFluid.OIL,…)` + `Fill(CarFluid.BRAKE,…)`, not just FUEL/COOLANT, or the dash oil/brake needles spawn
   red-empty and the car looks broken (enum order FUEL/OIL/BRAKE/COOLANT, `P:\scripts\3_game\vehicles\transport.c:52-57`, the `ETransportFluid` that `CarFluid` aliases on 1.30; capacities are
   engine-default, no config field needed).

   (d) **The see-through raycast winding oracle is a useful HEADLESS hint, but its RAW output is ~94% false
   positives — filter by body selection or it lies.** Casting backface-cull rays from many exterior directions
   (Fibonacci sphere) and flagging faces nearest only from the minority side is robust and
   pool-of-normals-independent (unlike the #7 normal-vs-normal tautology), so it catches inverted body faces a
   render might miss — and headlessly. BUT volumetric/concave geometry — `suspension`, `trim`, `interior`,
   undercarriage — is legitimately "seen from inside" and floods the count: on the deployed SUB_BRZ, **9152 of
   9736 single-sided faces (94%) were `suspension`/`trim`; only 584 were body (`color`/`glass`)**. Three rules
   make it actionable: (1) **filter by selection** — keep body selections (`color`/`glass`), exclude
   `suspension`/`trim`/`interior`; map face→selection via `(src,fidx)` over `lods[0]` (the visual LOD — verified
   the same LOD the oracle indexes `fidx` on). (2) **full raycast params** — reducing them LIES (`60/40/48`→3127
   vs `260/80/72`→11262, a 3.6× undercount that hides the real distribution). (3) **twin-test** to drop
   intentional double-siding (exact coincident vertex-triple, or centroid <6 mm + opposite normal). (4) **L-vs-R
   asymmetry is the decisive bug tell**: over symmetric geometry, if one side has single-sided body faces and its
   mirror has ~zero, that side's winding is inverted (a real bug), not intentional 1-sided glass (which is
   symmetric). MercedesAMGLF: left tail-lamp glass **310/922** single-sided vs right **0/922** -> confirmed
   asymmetric winding bug (rest of car ~clean, 2 `color` faces); for an asymmetry the fix is a **FLIP** (match the
   good side), distinct from #10b double-side. Validated gate_car on a 2nd car here (AMGLF = body-in-shell +
   material-less `mb_*` proxies -> just a new profile, no code change). Still a HINT
   (method #2), NOT the final gate — in-game render decides. The pipeline tool that encapsulates this is
   `gate_car.py` (profile-driven `body_selections`/`exclude_selections`; raycast oracle
   `raycast_winding.py`). Verified by direct measurement on the deployed BRZ (2026-06-30).

   (e) **The source ASSEMBLY emits every body face TWICE -> coincident same-winding DUPLICATES that z-fight into a
   grey/black/blue triangle speckle "all over the body" -- the s7-s15 "winding" RED HERRING.** The faces are
   correctly wound, just DUPLICATED (same 3 verts, same normal, DIFFERENT UV channel: TEXCOORD0 tiling vs TEXCOORD2
   swatch); it PREDATES decimation (proven vs the pre-decimate backup -- identical exact-dup count), so every
   decimation/winding fix MISSES it. On SUB_BRZ chunk_03 was **71% duplicated**, chunk_05 50%. Detector
   (NON-tautological, unlike the #7 winding-vs-normal): count coincident faces per `(frozenset(point_indices),
   winding-parity)` AND per identical rounded vertex POSITIONS -- a clean car ~0 coincident, a duplicated one
   10-70%. Fix = **de-dup keeping ONE face per (position-set, normal-DIRECTION) group**: same-direction copies are
   redundant (drop, prefer the UV-in-[0,1] swatch copy), OPPOSITE-direction pairs are the intentional double-side
   (#10b) -> KEEP both; never drop a `proxy:` face (wheels). Tools `dedup_faces.py` (index+parity) +
   `position_dedup.py` (position-identical; neither script is kept, re-derive them from this entry) -- SUB_BRZ s16 removed
   20320 faces, z-fight gone in-game, body+structure intact. **Add a de-dup pass to the importer so car #2 is born clean.** Detail: `rip-import.md`, section "VISUAL CORRECTNESS". (SUB_BRZ s16 2026-07-01, confirmed in-game.)

   (f) **PRIMARY winding gate = per-piece TOPOLOGICAL uniformity — run it BEFORE the see-through raycast
   (#10d).** The raycast finds faces inverted vs the EXTERIOR; it does NOT prioritize faces inverted vs
   their own NEIGHBOURS inside a piece — the more basic defect, and the source of the triangular artifacts
   the user sees in-game. Cheap, deterministic, no raycast: per selection, WELD vertices by rounded
   position, then check every interior edge (shared by 2 faces) is traversed in OPPOSITE directions; two
   faces traversing it the SAME way = a mixed-winding pair. Any visible piece with >0 mixed faces FAILS
   (this is Blender's "Make Normals Consistent" as a gate). Measured on the deployed BRZ: glass 18.2% of
   area mixed (the backlight), color 192 faces (hood + scattered), light 86, trim 12, tail 8;
   interior/suspension uniform. Tool: `winding_consistency.py --car <profile>`. Full
   winding FIX (amended s20): de-dup first (#10e), then make each piece consistent (MAJORITY flood-fill per
   connected component, excluding >2-face edges); orientation then comes from the raw source winding
   VERBATIM (#10j) — do NOT add an orient-outward pass (raycast/centroid): a correct exterior is only
   ~1.6-14.3% cross-outward (the engine renders the ANTI-cross side) and legitimate cabin-side pieces
   (`glass*int_a` 92-100% outward) face the cabin. This is the FIRST winding
   check on any imported model; #7 / #10d / in-game render come after. (SUB_BRZ 2026-07-01: `gate_car.py`
   shipped on the see-through check alone and skipped this basic per-piece uniformity check.)

   (g) **First-person INTERIOR invisible / "see the world through the car" = single-sided ViewPilot(1100) LOD ->
   DOUBLE-SIDE it, do NOT orient-inward (SUB_BRZ s17, CONFIRMED in-game).** DayZ renders the vehicle's ViewPilot LOD
   at the seated player's HEAD (engine behaviour seen in game, not readable in the scripts on `P:\`); a single-sided rip interior + `0x20000` flag renders as
   "few things drawn + world seen through" from the seat (winding-culled; MLOD per-face flags do nothing at
   all — binarize discards the field, round-trip 2026-08-24, `rip-import.md`, "VISUAL CORRECTNESS", item 1). Orientation
   is NOT the fix (measured: SUB_BRZ MORE toward-head than vanilla civiliansedan yet invisible -> more-inward != more-
   visible). FIX = per ViewPilot face, add a reversed-winding TWIN with the NEGATED per-vertex smooth normal (dedup the
   pool) + set all ViewPilot flags to 0 (vanilla parity); feasible when resolved-verts <~32k (doubles to <65535).
   Detail + the vanilla-diff that pinned it: `rip-import.md`, "VISUAL CORRECTNESS", item 5. (Residual: rip interior reads
   GREY -> material pass, not geometry.)
   SUPERSEDED as primary fix by (i)/(j) (s20): the defect was import ORIENTATION (orient_authored wrong for
   every piece, #10j); the s19 in-game-confirmed fix is single-sided RAW winding as a prox_int-style proxy.
   The s17 "orientation is NOT the fix" inference used the flawed `__N` oracle. Double-siding remains a
   fallback only, at the cost of ~2x resolved verts toward the 65535 cap.

   (h) [FIX SUPERSEDED by (j), s20 2026-07-02: the detector below (welded-position antiparallel stored
   normals) remains valid, but do NOT heal toward the authored/deployed orientation — the deployed exterior
   at 0.5% stored·cross>0 is the anomaly (prime B1 candidate); stored normals = smooth(+cross) of the FINAL
   winding, and source-inconsistent components are repaired by MAJORITY flood-fill per connected component,
   never the area criterion (it inverted the BRZ rear glass).]
   **Bright/reflective TRIANGLES scattered on imported car PAINT (they catch sky/specular, distinct from the body
   colour around them) = shading-normal SEAMS, NOT winding/z-fight/material.** A per-face winding flip that NEGATES the
   per-face normal (the #10d/#10f fix, or an import/decimation step) leaves those faces' stored normals ANTIPARALLEL to
   their un-flipped neighbours -> a shading discontinuity that reads as a bright (or dark) triangle, while winding is
   fine (#10d/#10f pass), z-fight is absent (#10e), and each face's material is correct per-face. Detector
   (non-tautological): weld the piece's paint faces by position; at each shared position count DISTINCT stored-normal
   directions -- a smooth surface has 1, a seam has 2 antiparallel. FIX = HEAL the orientation, do NOT recompute normals
   from geometry: propagate the AUTHORED orientation across the paint surface (flood-fill on adjacent stored-normal
   agreement `dot(smean_a, smean_b)`) and NEGATE only the minority faces (per connected component keep the majority-AREA
   side, so the approved look is preserved EXACTLY on the majority). Flip only CLEAR seams (`dot < -0.5`, >120deg):
   genuine paint creases at 90-120deg are rare (real sharp edges are paint-to-trim/glass = different material =
   excluded) and rounding one is worse than a faint triangle. **NEVER orient "outward-from-car-centre": a car body is
   NON-convex, so centre-outward matches the authored normals only ~70% -> recomputing that way INVERTS ~30% of the
   paint shading = a full-car regression.** Also SCOPE make-consistent to the COMPLAINT region: a `light`/headlight
   selection is a multi-layer lens+reflector where forcing consistency can invert a legitimate inner layer -- do NOT
   flip a whole headlight to zero a metric the user never complained about (SUB_BRZ s18: `light` 86 mixed were ALL front
   = 723-face flip, skipped; the complaint was rear reds -> only `tail`+`trim`). Tools `smooth_normals.py`
   (thresh sweep + heal) + `winding_fix_t4.py` (make-consistent scoped by selection). (SUB_BRZ s18 2026-07-01,
   offline faceted-positions 3347->1613; in-game gate = user's eye.)

   (i) [MECHANISM SUPERSEDED by (j), s20 2026-07-02: authored normals are inverted NOWHERE (the GLB is
   99.99% winding-consistent); the "70.5% authored" oracle was the pipeline's `__N` (smoothed pre-mirror
   winding), and orient_authored is wrong for EVERY piece, not only the interior. The raw-winding interior
   FIX below stands (in-game OK).]
   **The source-game import orients winding to the rip's AUTHORED normals, which are INVERTED for the
   interior -> use the glTF's RAW winding (SUB_BRZ s19, CONFIRMED in-game).** `rip_p2_shellproxy.
   orient_authored()` flips each face's winding to match its authored source normal. For the EXTERIOR this
   works (authored normals point outward); for the INTERIOR the source-game authored normals are INVERTED vs the
   DayZ convention -> winding ends up backwards -> see-through in 1PP (ViewPilot LOD 1100). Cheap offline
   discriminator: the **toward-driver gate** -- fraction of faces whose normal points at the crewdriver
   anchor -- compared to the same gate on the debinarized vanilla `prox_int` (~35%). Measured on the BRZ
   cabin: authored normals 70.5% (inverted) vs geometric RAW winding 30.3% (~=vanilla). FIX (in-game
   confirmed): rebuild from the **RAW winding + smooth geometric normals** (NOT the authored ones),
   single-side, as a dedicated interior proxy in the vanilla `prox_int` pattern (LODs res 0.0+1100, frame
   `((-1,0,0),(0,0,1),(0,1,0))` verified via `derive_proxy_frame`, ambiguous=False; interior geometry is
   model-space, no companion bone). The interior geometry was structurally SANE (boundary edges ~8-10%,
   like vanilla) -- the defect was purely ORIENTATION. Do NOT patch normals piece-by-piece: the cause is
   the import's orientation step, common to every piece; the fix belongs in `rip_p2_*`. Tool:
   `interior_design_gate.py` (toward-driver gate over orientation candidates:
   authored / raw / outward-of-component / inward-of-component). (SUB_BRZ s19 2026-07-01.)

   (j) **CORRECTION to (i)'s mechanism + the SINGLE import orientation rule (SUB_BRZ s20 2026-07-02 —
   MEASURED offline vs vanilla + two in-game-confirmed artifacts; the reimport's in-game gate is PENDING).**
   source-game authored normals are NOT inverted anywhere: the source glb is winding<->normal consistent
   261191/261227 (99.99%), no mesh <99%. The "authored 70.5%" candidate in (i)'s gate was the pipeline's
   `__N` channel, which is NOT authored — `rip_p2_group.py` captures `l.vert.normal` after
   `bm.normal_update()`, and bmesh drops custom split normals -> `__N` == smoothed(+cross) of the
   PRE-mirror winding. That is why "authored" and "raw" were exact complements (70.5+30.3~=100.8): the
   oracle was the mirror-flipped winding itself. Consequences, all measured:
   - `orient_authored` is wrong for EVERY piece, not only the interior (s12's near-global exterior flip
     was undoing it). RAW winding on the exterior: `body_a` 8.8% cross-outward ~= deployed approved shell
     14.3% ~= vanilla band (sedan `dmgzone_roof` **1.6%** cross-outward — the roof pins the engine
     convention: **the rendered/front side is the ANTI-cross side**).
   - THE RULE: keep the raw glTF winding VERBATIM for ALL pieces (net rip→DayZ = `(-Fx, Fy+Y0, -Fz)`,
     det=+1, preserves the authored visible side end-to-end); stored MLOD normals = smooth(+cross) of the
     FINAL winding (vanilla 96.2% stored.cross>0, brz_int 99.5% and in-game OK; the deployed BRZ exterior
     at 0.5% is the outlier -> prime candidate for the (h) bright-triangle class). NEVER orient winding to
     a normal oracle or to outward-of-centre.
   - Repair ONLY source-inconsistent components (~0.33% of BRZ faces: glassr 108, bodyfoglights 443,
     lights 86+84...) by MAJORITY flood-fill per connected component — never minority-area (sign-ambiguous:
     it inverted the BRZ rear glass; deployed glass measured 73.9% cross-outward = renders inside-only).
   - `glass*int_a` panes are the legitimate cabin-side glass layer (measured 92-100% outward = anti-cross
     faces the cabin): do NOT delete them as "z-fight" — with correct orientation there is none.
   This entry supersedes the Phase 5 "WINDING" section of `rip-import.md`, pending that in-game gate.

   **s21 STATUS (2026-07-02): the rule is now TOOLING with offline gates GREEN — in-game Gd still pending.**
   **UPDATE 2026-07-06: the in-game Gd gate has since run — s23 cycle 1 was deployed 2026-07-03 and judged
   in game 2026-07-05; the issues that round found are fixed offline and wait for one joint deploy.**
   Car #N starts from `rip_p2_build_v2.py` (+ `rip_winding_core.py`,
   `rip_p2_interior.py`) and the `gates_v2.py` step gate — NEVER from rip_p2_shellproxy v1
   (fail-fast-guarded, and it EXECUTES its v1 build at module level, so its "helpers" are NOT
   importable; copy constants instead). Measured on the BRZ:
   - The majority repair flips ENTIRE minority subregions, not just the mixed-edge seam faces: a glass
     piece can flip 24-39% of its own faces while the car-wide total stays ~0.5% (BRZ: 2148/440911 =
     0.49%). Per-piece Ga warnings >1% are the EXPECTED census of source-inconsistent pieces, not a
     builder failure — do not panic-revert per piece.
   - Face-level validation pattern: build the full-detail FINAL vs VERBATIM (R2/R3 off) pair from the
     same npz and Gb+ them — coverage ~100%, opposite == the repair count EXACTLY. A doctrine-scale
     regression (any orient_authored-class pass) reads ~90-97% opposite (measured 97.23% vs the v1
     shell); repair-scale reads ~0.5%. Compare at WHOLE-car granularity, not shell-only (repairs
     concentrate in lights/glass: a shell-only diff reads 1-3% and false-fails the band).
   - Stored-normal sign is COUPLED to the shell convention: v2 shells are smooth(+cross), so every
     downstream rebuild (e.g. `decimate_rebuild.py` after decimation) must also write +cross — a
     -cross rebuild against a +cross shell reproduces the s15 two-tone paint with the opposite sign.
   - The import chain is deterministic: re-running Blender import+group reproduced the npz
     BYTE-identical (SHA256). A changed npz hash on an unchanged rip means the toolchain moved —
     investigate before building.

   (k) **Re-typing a face's VIEW ROLE requires an EXPLICIT orientation decision (flip or twin) —
   the inherited winding is NEVER valid for the new role (SUB_BRZ s22 2026-07-02, measured
   offline; in-game gate pending).** The cycle-4 glass_int_policy re-typed inner-pane GLASS faces
   into a BLACK occluder band meant to be seen from OUTSIDE, but the faces kept the pane's
   cabin-facing winding -> 100% culled from outside (occ02 raycast: 529/4431 rear-slot + 70/4893
   cowl rays reached the ground THROUGH the car; 0 rays lacked geometry = nothing missing, pure
   orientation). Process rule: any policy that changes a face's view role must pair the re-type
   with an orientation decision — DOUBLE-SIDE (anti-parallel twin, same per-vertex UV = reversed
   per-corner UV rows) when both sides are seen (a simple flip covered the outside equally in
   simulation but de-renders the rim from the cabin). Emit twins AFTER the R3 majority repair
   (pre-repair they make every band edge non-manifold and corrupt the flood-fill graph). Gate
   offline BEFORE burning the in-game cycle: orientation census dot(cross, outward) + occlusion
   raycast — the `occ01`/`occ02` scripts (post-fix use the PAIR-aware census
   `occ01b_band_pairs.py`: a 1-NN match always picks the original of a coincident
   pair and false-negatives the twin).

   (k-CORRECTION, s22 rebuild-2 — BLANKET double-siding is itself a regression class): twinning
   the WHOLE re-typed band blacked out 68-100% of every window view in-game (the inner pane sits
   0-1mm behind the outer glass; a 15cm BLACK band double-sided IS a painted-over window; the
   occlusion gate alone gave a false green because it measures coverage, not appearance). Twin
   ONLY the LOAD-BEARING faces: `rip_glass_twin_probe.py` (needy-ray probe:
   ring + pane-bbox GRID verticals + oblique 60/30 from the pane's outward azimuth; twin = first
   double-sided hit of a ray that otherwise ends below floor_y). BRZ measured: 129 of 463 band
   faces (windshield 63, rear 66, sides 0). Two gate lessons that cost an offline iteration each:
   (1) the gate's rays must be a SUBSET of the probe's rays (occ02's zone GRID sampled corners
   the ring-only probe never traced -> 8 leak rays); (2) an appearance gate (band faces as first
   rendered hit through each pane, `v2_probe.py` style) must run NEXT TO the occlusion
   gate — coverage and appearance bound each other (rear window floor: ~50% band = the slot
   closure itself; below that needs structural closure, not twins).

   (l) **Authored LODs can carry FOREIGN geometry — NN material transfer needs a GLOBAL cross-part
   fallback + an extent gate (SUB_BRZ s22 2026-07-02, measured).** The authored LOD2 of
   `bumperfbadge_a` bakes fascia trim into the badge part (extent 8.4x the full part's bbox
   diagonal; 175/183 faces with their intra-part NN donor >25mm) -> a per-part transfer can only
   donate the tiny real part's types (CHROME) and paints the foreign trim grey in the scoops. FIX
   (rip_mat_transfer.py): faces whose intra-part donor sits >25mm re-vote against the GLOBAL
   full-detail pool (the overlapping neighbour part types them correctly); scan EVERY part for
   extent-ratio LOD-vs-full >1.5x = foreign-geometry flag (warn loudly; the fallback fixes the
   typing, the geometry itself may still need a per-part budget exclude). GOTCHA that bit here:
   numpy fixed-width string dtype truncates SILENTLY on assignment ('PLASTIC' -> 'PLASTI' into the
   badge's <U6 `__MAT` array -> unknown type -> class-fallback BLUE); promote to the pool's dtype
   before any cross-part assignment.

   (l-CORRECTION, s22 rebuild-2 — the UNCONDITIONAL global re-vote is itself a regression class):
   on parts WITHOUT the foreign signature, decimation alone displaces LOD centroids >25mm, and the
   global pool votes brighter NEIGHBOUR parts — the BRZ diffuser shipped 8 BLACK faces as
   METAL/CHROME (donors exhaust/undercarriage/suspension at 23-46mm) = grey jagged artifacts.
   Scope the re-vote to parts with extent-ratio > 1.5x ONLY (the badge signature it was built
   for); everywhere else the intra-part vote stays authoritative (reverts 89/89 accidental
   re-types, measured). Report far-donor counts either way.

   (m) **When load-bearing occluder twins bottom out, close the glass↔body gap with AUTHORED opaque
   geometry IN THE GAP, not more twins (SUB_BRZ s23 2026-07-03, occ02-measured; in-game gate
   pending).** The inner-pane occluder band sits 0-1mm behind the transparent outer glass (measured
   100% overlap on all 6 panes), so ANY outward-visible band face — twin, flip, or blanket — renders
   IN FRONT of the glass = the grey-window regression. The slot the twins were sealing is the
   annular glass↔body gap; close THAT with NEW geometry kept ≥ glass_clear (~8mm) from any
   transparent glass so it can never re-grey: (a) a skirt lofted from the outer pane's boundary ring
   to the nearest opaque body edge (walk the boundary EDGE LOOPS for continuity, not angle-sorted
   points; overshoot the body target ~15%+1cm so the tip tucks INTO the body solid = no crack); plus
   (b) a SUNKEN BAND for the top-down cowl/rear slots (copy the inner-pane frit faces sunk ~10cm in
   −y = the physical plenum / dash-top panel a real car has there). **DOUBLE-SIDE it** (both
   windings): a single-sided strip is culled from one hemisphere — cross-INWARD renders lateral but
   is culled TOP-DOWN because the glasshouse centroid sits ABOVE the rear deck, so occ02 reopens;
   double-siding in the gap is safe (clear of glass) and renders from every exterior angle. This is
   the "structural closure, not twins" that (k-CORRECTION) predicted below ~50% band coverage. Gate:
   occ02 top-down (0 seethru) + a LATERAL first-hit census + a golden-relative diff vs the last
   deployed (absolute lateral counts include harmless preexisting belt-line rim cracks — gate
   RELATIVE). RESIDUAL not closed by the gap skirt: the lateral WEDGE (sail-panel under the mirror =
   a through-glass-EDGE view into a deep cabin cavity) needs a targeted frit-edge twin AT the glass,
   which risks re-greying → eye-gated, ship + confirm in-game.
   A gap seen ONLY from the seat closes the other way round: single-sided, in the ViewPilot alone,
   behind what moves through the rider's line of sight (`proxies-and-get-in.md`, "Closing first-person gaps").

   (n) **Decouple the wheel HUB level from the body rally LIFT (SUB_BRZ s23 2026-07-03,
   offline-measured; in-game pending).** A rally/stance lift belongs to the body (Y0), NOT the wheel
   hubs. `rip_p3_structural.py` pinned `W[k] = (x, WHEEL_R + LIFT, z)` → adding LIFT to BOTH buried
   the hub 18cm above the suspension knuckle, cancelled the visible stance, and collapsed the chassis
   clearance to 7.6cm (vanilla 25.8) = a plausible "won't drive off-road". Add a `hub_lift` profile
   param (default 0.0): hubs sit at the rim contact (WHEEL_R), the wheel meets the knuckle end,
   clearance is restored, and the body lift becomes real rally stance (fenders ~18cm above the
   wheels). config.cpp/model.cfg are untouched — they reference names; the *_axis are memory points
   that ride the hub. Gate: the 4 wheel anchors == WHEEL_R in every structural LOD, knuckle-hub gap
   ≤ 2cm, chassis clearance ≥ 0.20m.

   (o) **Before a full structural re-transplant, VERIFY the builder reproduces the DEPLOYED get-in;
   if it doesn't, deploy the fix as a scripted surgical PATCH of the deployed structural, not a regen
   (SUB_BRZ s23 2026-07-03, measured at deploy).** The deployed structural can carry
   post-processed get-in the builder does NOT reproduce: SUB_BRZ's deployed ViewGeo has a
   23-component collision hull + `crewdriver`/`crewcodriver` BONE-NAMED selections (added by
   `fix_crew_binding.py`, required by config.cpp `proxyPos`) + LOCAL wheel proxies, while the current
   `rip_p3_structural.py` emits a 3-component ViewGeo with NO crew-named selections — a full struct
   transplant would REGRESS the get-in that cost dozens of iterations (#10 s6-s9). So: diff the fresh
   struct vs the deployed PER LOD before transplanting; if the get-in selections diverge, apply the
   geometric fix (hub Δy, crew Δxyz, #Mass#) as a deterministic, gated, by-selection-IDENTITY patch
   of the deployed p3d — move ONLY the wheel/crew/mass selections, gate per-point that nothing else
   moved AND crewdriver/crewcodriver survive, backup + read-back (`patch_deployed_struct.py` pattern).
   Test the patch on a COPY first (never the live file for a get-in edit). The pipeline debt (fold
   the hull + crew-binding into the builder so a full transplant becomes viable for car #2) is a
   separate task.


## A clean `validate()` does not prove winding is correct (added 2026-08-12)

Hard rule before using `py3d.validate()` as a winding gate on a vehicle: **a clean result
shows that winding, stored normals and LODs agree with each other, not that the engine
draws the side you meant.** This describes py3d 1.10.1, the version in `scripts/tools/py3d/`.

`validate()` runs two winding checks (`scripts/tools/py3d/py3d/__init__.py`):

- `_check_winding_absolute`, on every visual, Geometry, View Geometry and Fire Geometry
  LOD, compares each face's `cross(e1,e2)` with its own stored normal
  (`ERR_WINDING_VS_NORMALS`, `WARN_WINDING_NORMAL_MISMATCH`) and checks that neighbouring
  faces traverse a shared edge in opposite directions (`WARN_WINDING_EDGE_INCOHERENT`). It
  sees that winding and normals disagree, not which of the two is wrong, and a LOD whose
  faces and normals were turned together agrees 100% and passes.
- `_check_winding_vs_visual` is RELATIVE: it compares each collision LOD with the visual
  LOD of lowest resolution, by the share of faces wound outward from the LOD's centroid
  (`ERR_WINDING_INVERTED`). That test assumes convex geometry and cannot see a global
  inversion. If the visual LOD is the inverted one, the finding lands on the HEALTHY
  collision LODs; reversing those to match leaves a model that no check flags any more.

So a model inverted as a whole, winding and normals together -- what a Blender Z-up to
Y-up import leaves when both are turned -- still returns no winding finding.

The other two instruments are also invalid as geometry proofs: `save(verify=True)`
(`_verify_against`) and `python -m py3d diff` compare counts, selection names and
membership, properties, UV sets and mass, never point positions (`diff` compares positions
for memory points only). Reproduced: two models with one point at `(0,0,0)` vs
`(99,99,99)` -> verify OK and `diff` returns `total: 0`, exit 0.

Consequence for section 3.5 of `rip-import.md` ("`validate()` findings that are EXPECTED for a
vehicle"): that list exists because the relative check assumes CONVEX geometry and therefore
spits false positives on hollow hulls and L-shapes. But the correct reading is not just
"ignore those findings", it is also **"their absence proves nothing"**.

Verification that does discriminate, in order of cost:
1. Compare vertex order of a face against debinarized vanilla equivalent.
2. `cross(e1,e2) . declared_normal` per face -- both vectors in SAME space, so
   left-handed (DayZ) vs right-handed (Three.js) confusion disappears. Measured over 15 vanilla
   LODs: 1274/1274 faces = 100.0000%, versus a `pct_outward` swinging between 0% and
   31.8% without meaning anything.
3. Edge consistency: two neighboring faces traverse the shared edge in opposite
   directions. Locates specific faces in partial inversions.
4. In-game test (texture visible only from inside = inverted winding).

How to read each py3d winding finding is in
`skills/dayz-p3d-audit/references/winding-absolute-check.md`.

   - **Winding ratios do not predict render (LFHeli OH-1 2026-07-19).** Neither the interior edge-pair (`winding_consistency.py`, `#10(f)`) nor the ODOL dot-neg cross-vs-stored-normals ratio vs vanilla predicts the render. Real case: edge-pair ≤0.0025%, ODOL 98-100% dot-neg ≈ civiliansedan 96% → methodical PASS, and the model rendered INVERTED (stored normals coherent with the winding: both inverted vs the engine — the ratio measures internal coherence, not the absolute sign the engine renders).
   - **Cheap definitive discriminant = all-flipped A/B in-game.** Reverse vertex order of ALL visual faces (~1 line in the assembler, or a short py3d script), binarize, A/B in-game with the user's eye (~40 min). EXCLUDE proxy triangles from the flip: their winding encodes the proxy frame (P′). Before the A/B, census the ODOL of BOTH variants: if they come out equal, the A/B is null (anti-nullity gate).
   - **Binarize PRESERVES source winding.** Same reader, both variants' ODOL dot-neg census: 99.1% → 0.95%. Do not trust "binarize already normalises to the convention": it normalises nothing. Distinct from the debinarizer ODOL→MLOD inversion (`vehicle-structural-parity.md`). When pinning the flip in an assembler: recalibrate its winding gates (the expected fraction inverts) and exclude dots ≈0 from the census (merged symmetric normals give a null dot with no information; on OH-1 they were ~17% of the shell and sank the fraction). OH-1 assembler already ships reversed visual winding on purpose (`FLIP_VISUAL_WINDING = True`): `rip-geometry-and-winding.md`. See also `skills/rip-vehicle-import/SKILL.md` and `skills/dayz-p3d-audit/references/winding-diagnostics.md`.


## A Blender culling render cannot adjudicate DayZ winding (added 2026-08-31)

Two sign changes can cancel. The common display mapping `(x,y,z)->(x,z,y)` swaps
one axis pair and has determinant `-1`, so it reflects handedness and apparent
winding; the proper-rotation alternative `(x,y,z)->(x,-z,y)` has determinant `+1`.
Blender renders the `+cross` side while the measured DayZ chain renders the
anti-cross side. A preview can therefore agree by accident. Use it for geometry
and placement only; the winding verdict remains the in-game control/A-B.

In Blender's Workbench render engine, enable `scene.display.shading.show_backface_culling`.
`material.use_backface_culling` controls EEVEE and is inert in that engine. Pixel-
identical "culling on/off" outputs are a null test, not confirmation.

What py3d can and cannot prove about winding is in
`skills/dayz-p3d-audit/references/winding-absolute-check.md`.

## Choosing the sign for a face you are ADDING or MOVING: copy the visible neighbours (added 2026-09-07)

The invariants above are about detecting faces that are already wrong. The complementary
question — which winding a face should have when a script creates or relocates it — has a
cheaper answer than any absolute rule: **match the sign of the faces beside it that are known to
render**, in the same file and the same LOD, so both sides cross whatever format boundary
follows (MLOD to ODOL included).

Measured on LFQuad2 (2026-09-07). A redesigned dash panel did not draw at all; only a stray
needle remained visible. The panel's Newell normal dotted with the line of sight gave **+0.951**
while all **64** disc faces sitting next to it, which render correctly, gave negative dots
(mean -0.952, 0 of 64 positive). Flipping the panel to agree fixed it. No absolute claim about
which way a normal "should" point was needed, and none would have been portable: the same
predicate inverts across binarisation.

Three practical consequences:

- **Calibrate the gate on geometry that is drawing, not on a rule.** Reversing the vertex order
  and re-checking the sign against the neighbours is a two-line assertion.
- **Restrict the gate to comparable shapes.** Applying it to the whole dash flagged 12 of 173
  needle faces as discordant, which is normal: needles are solids and legitimately face both
  ways. The panel and the discs are flat and coplanar, so only they belong in the comparison.
  Proving those 12 were pre-existing needed a set comparison of face centroids before and after,
  not a count.
- **A translation cannot change winding, but assert it anyway.** It costs nothing and it caught
  nothing only because the earlier bug had already been found.

## A sort tiebreak that never fires: 0.1 mm mirrored the quad (added 2026-09-07)

The panel above came out mirrored because of the script that repositioned it, not because of the
model. Corners were assigned from `sorted(range(4), key=lambda k: (-y[k], -x[k]))`, on the
assumption that the primary key would tie within a row and let the X tiebreak order left from
right. The two top corners differed by **0.1 mm** in Y (1.2663 vs 1.2664), so the primary key
never tied, the X tiebreak never ran, and the quad was mirrored in X — which reverses the
winding.

The failure is silent: positions and UVs are still a valid rectangle, the texture is not
mirrored (because the UV is a function of the final position), and the only symptom is a face
that vanishes under culling. **When a sort is meant to group by rows or columns, quantise the
key** (`round(y, 3)`, or bucket by a tolerance wider than the model's noise), or assign corners
by quadrant relative to the centroid, which is exact regardless of noise. And add the winding
sign to the acceptance gate of any script that reassigns vertex positions: a gate that only
checks coordinates and UVs passes this bug.
