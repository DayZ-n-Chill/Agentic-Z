# Distance LODs and the vertex budget: invariants

How many visual LODs an imported vehicle needs, how far each decimation method goes, and how to tell offline that a model is over the engine's resolved-vertex ceiling.

> Status: field notes measured on third-party mods, each named in its entry (SUB_BRZ, SUB_WRXSTI, MercedesAMGLF, LFQuad, LFQuad2, LFQuad3, Arma2Quad, LFHeli). Those measurements were not repeated here. A citation written with its full `P:\` path was opened on the vanilla data of this repo. A citation without `P:\` keeps the line number the note was written with, for the DayZ build that entry names, and is not yet checked on `P:\`: Grep for the symbol before relying on the number. Where they were opened, the `carscript.c` numbers matched this repo's `P:\` (a 1.30 build), the `transport.c` numbers sat 3 to 9 lines lower than written, and the `DZ\vehicles\wheeled\config.cpp` numbers differed. Tags such as SP-205 or LL-244 are the notes' own lesson numbers. Paths such as `<vehicle-import>\...` or `SUB_BRZ_dev\...` point into those mods' work folders, which are not part of this repo. "Invariant N", "preflight #N" and "#N" all mean the numbered invariants; `skills/dayz-vehicles/SKILL.md` lists which file holds each number.

## Vanilla anchors checked on `P:\`

- The vanilla control for LOD counts is `P:\DZ\vehicles\wheeled\civiliansedan\civiliansedan.p3d`. It is a binarized ODOL, which py3d cannot read, so the face counts quoted below were measured by the notes' author on a debinarized copy and were not measured again here.
- `binarize.exe` ships with DayZ Tools; `/dayz-preflight` checks that DayZ Tools is installed before any step here that runs it.

## Imported-mesh budget: measure the triple ratio on the geometry you ship (added 2026-07-29, LFHeli HH-60G)

**Imported-mesh budget invariant (added 2026-07-29, LFHeli HH-60G):** a **triples/triangle ratio
measured on a DECIMATED mesh does not extrapolate to an authored one.** `Decimate` collapses edges
and breaks normal sharing, so it inflates resolved (point, normal, uv) triples per triangle. Measured
on the same asset: **1.301** on the Decimate-ratio export (0.26-0.6 per group) versus **0.941** on the
source's own Medium LODs — 28 % apart, and enough to change how many sub-`.p3d` you plan for (2.43
projected LODs against 1.75 measured). Rule: measure the ratio on the geometry you will SHIP, not on
whatever export you have lying around. Corollary, and it is the bigger win: **if the source ships an
authored LOD ladder (GTA `.yft` High/Medium/Low, ripped racing-game, Sollumz-imported `.blend` datablocks), use it
instead of decimating** — swapping `obj.data` to the `<piece>_medium` datablock is usually better in
triples AND satisfies the "the agent never decimates visual" clause of a product spec. Re-measure per
model; never copy a ratio or a resolved ceiling between assets.

## Invariant 13: author the distance LOD ladder before fighting LOD0 decimation

**Distance-LOD ladder: a single-visual-LOD import renders its FULL face count at ANY distance —
author the ladder BEFORE fighting LOD0 decimation.** (added 2026-07-07, SUB_BRZ s25 measured)
Vanilla civiliansedan ships 5 visual LODs (14,636 → 10,364 → 3,717 → 1,713 → 123 faces); SUB_BRZ
shipped 1 (231k always) and the admin-preview/spawn freeze did NOT move with dedup (−18.5 MiB) or
shadow (32k→3.5k) fixes — it is render/face-bound. Distance LODs res 2/3/4 are baked FLAT into the
main (no proxy refs: proxies of res-0 only render while res-0 renders) from the rip's authored LODs
(planar-dissolve measured ceiling = ÷2-2.6); exclude the cabin from far LODs (vanilla does). Day-1 check: count
visual LODs vs the control — ≥2 is also the product-spec floor (AC1.4-class). LOD0 decimation stays
user-gated and becomes a LAST resort, not the first.
**s26 EXECUTED the ladder (SUB_BRZ deployed, measured) — measured continuation of the contract:**
(a) **Planar-dissolve (Blender limited-dissolve, shape+UV preserving) tops out at ÷2-2.6, NOT ÷5-8** —
the rip's authored LODs are mid-detail racing meshes, not impostors. SUB_BRZ body 58.7k → 34.5k@15° /
27k@30° / 22.4k@45°. It yields ONE good near LOD (res2 ~27k, quality intact, no gate). To reach vanilla
parity (sedan res3/res4 = 3.7k/1.7k) you need COLLAPSE decimation, which deforms and is user-gated — so
MEASURE the planar ceiling and ask how far to take the ladder BEFORE promising res3/res4.
`decimate_blender.py` (planar) preserves material-slot + UV; collapse does not.
(b) **Bake far-LOD stored normals OUTWARD — SUPERSEDED in part by (d) for the winding census.**
The body winding gives +cross INWARD (the build negates paint/lamp classes via `negate_classes`);
a flat LOD baked with raw +cross renders ~60% inside-out (black). Fix that BLACK failure in the
stored normals; the `cross·(centroid−carCenter)` winding target comes from (d)'s census against
the LOD0 control (the corrected SUB_BRZ far LOD measured ~2%, not 100%), and vertex order is handled
there. resolved<65535 holds easily (26k for a 27k-face body).
(c) **The transplant assumes exactly ONE visual LOD** (`p4_transplant_dyn assert len(vis)==1`). A ladder
needs a multi visual-LOD transplant: replace the deployed visual block with ALL work res<100 LODs
(sorted), KEEPING every struct LOD. GATE it with a self-test on a COPY: struct LODs
(Geo/Mem/HP/ViewGeo/FireGeo) must come out BIT-IDENTICAL (get-in), then re-verify real deployed vs
backup. Flat body source = shell res0 minus proxy faces + the chunk p3ds (cabin already excluded — it
lives in the intact interior proxy). Render-review the baked LOD before deploy (blender-visual-review).
(d) **A far-LOD baked WITHOUT the shell's make-consistent/orient pass ships with its WINDING globally
INVERTED → the body reads TRANSPARENT (see-through) at mid/far distance — a DISTINCT failure from (b)'s
BLACK.** (added 2026-07-09, SUB_BRZ s29 measured+fixed) Transparent = winding/cull wrong (anti-cross faces
point INWARD → culled from outside); black = stored normals point inward (shading). Diagnose OFFLINE by
census: fraction of far-LOD faces with `cross·(centroid−center)>0` vs the LOD0 control that renders fine —
far-LOD ~98% cross-outward while LOD0 ~17% ⇒ winding inverted. FIX: if stored normals ALREADY point outward
(`storedN-outward` high, i.e. it reads transparent not black), a GLOBAL vertex-order flip
(`face.vertices.reverse()` on every face, do NOT touch normals — they ride the vertices) suffices — census
98%→2%, matching LOD0. Reach for make-consistent+orient (`rip_winding_core.repair_winding_majority`) ONLY
 when the far-LOD is topologically MIXED (low interior-edge consistency), not merely globally inverted (G5
 simple-first). Root cause on SUB_BRZ: the in-line s26 ladder assembler took the dissolve winding VERBATIM +
 raw +cross normals and skipped make-consistent (which the shell's `rip_winding_core` runs) → res=2 shipped
 see-through, `outward=38.9%` was printed and ignored, no offline gate. GATE any baked far-LOD by census-vs-LOD0
 BEFORE deploy — Blender cannot judge DayZ winding (right- vs left-handed cull). Instrument
 replicates consumer ORDER: culling runs BEFORE depth test (LL-485); group
 hits at t_min+epsilon and ask whether ANY face camera, and reread controls when
 fix changes geometry class that instrument resolves.

> History of the superseded text: `history/superseded-family-b-rules.md`, section "Invariant 13".

## Invariant 24: binarize is the three-state offline load oracle (SP-122)

**`binarize` is the three-state offline load oracle; `RESOLVED_LIMIT = 65535` is a false friend (SP-122, LFHeli HH-60G, 2026-07-29).**
Measured evidence for this invariant — the three verdict states, the real ceiling in triple
units, headroom accounting and what does NOT discriminate — is in
`binarize-vertex-budget.md`.

> History of the superseded text: `history/superseded-family-b-rules.md`, section "Invariant 24".

## Invariant 27: a model that passes every offline gate and still will not spawn is usually over the resolved-vertex ceiling

**A model that passes every offline gate and still refuses to spawn is almost always over the RESOLVED-VERTEX ceiling — and `binarize` tells you offline, in 90 seconds (LFHeli HH-60G, 2026-07-29).** `PHYSICS (E): Won't simulate, it has no geometry` is emitted when the engine aborts while **loading the MLOD**, before it ever builds physics — so a perfect Geometry LOD does not exonerate the model, and chasing it as a collision problem costs days. **Do this first, not last**: drop the `.p3d`s into a dir under `P:\` with a `model.cfg` declaring **every** basename, run `binarize.exe -always <src> <out>`, and read the verdict — `Too many vertices` names the culprit by filename. Validated 25/25 against in-game verdicts on 28 variants (zero false greens, zero false reds), which turns model bisection from ~6 min per variant into ~90 s per batch. That validation ran without `-addon`. [DESIGN] Give the call a dedicated `-addon` folder all the same, since without one a later import's call, its source outside `P:\`, stalled before its first model; with one only `PASS` has been run so far, no `CAPACITY_FAIL`, and a source under `P:\` was not timed (`binarize-vertex-budget.md` item 2). Three rules that make it a real gate: (a) the verdict is **three-valued** — `PASS` needs a *new* non-empty ODOL (a residual one is a false green), `CAPACITY_FAIL` needs the `Too many vertices` line *attributed to that MLOD*, and anything else is `OTHER_FAIL` which **blocks and does not authorize touching geometry**; (b) the verdict is reproducible but the **ODOL bytes are not** (same input, 1.725.025 and 1.726.689 b in two clean runs) — never gate on the ODOL SHA; (c) the ceiling in `(point, normal, uv)` units is **not 65535 and not portable** — measured 46.133 on the HH-60G across four bases, because the engine's cap is on POST-SPLIT vertices and your counter under-counts by a model-dependent factor (1,4205 here, 1,46 on the OH-1). An assembler with `RESOLVED_LIMIT = 65535` hardcoded closed its own gate in green for weeks on a model the engine refuses. **Re-measure per model, and know your headroom** — the deployed HH-60G sat 114 triples under the cliff, one normal tweak from death. Full detail, including why reversing corner order is free while minting a normal is not: **SP-122** in `binarize-vertex-budget.md`. Tool: `<vehicle-import>\scripts\p3d_vertex_gate.py` (its HH-60G copy calls binarize without `-addon`: `binarize-vertex-budget.md` item 2). **SP-216 rider:** py3d **count** gates (resolved<65535, normal pool, digest, identical Geometry) do not authorize spawn. The first oracle for `Won't simulate, it has no geometry` is `binarize` (invariant 27): `CAPACITY_FAIL` → do not go in-game; `OTHER_FAIL` → do not touch geometry; `PASS` and the game still says no-geometry → then yes, serialization / another axis, and in-game spawn is the judge. The V8 of SP-216 is the negative capacity control (`CTL_CAPACITY`), not a refutation of `binarize`.
