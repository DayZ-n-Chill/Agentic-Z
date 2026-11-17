---
name: uv-clean-atlas
description: "Builds clean, readable UV atlases for hard-surface game meshes (a few large islands a person can name, zero overlap, moderate stretch) with a headless Blender pipeline, and audits any UV set with an exact overlap check plus island and density numbers. Use when the user wants to unwrap or re-unwrap a vehicle, prop or weapon body for texturing (generate UVs, unwrap, UV wrapping, readable atlas, the UVs come out as a thousand islands, overlapping islands, stretched texture, livery template, clean UVs, prepare the model for texturing), to audit UVs (how many islands, is there overlap), for a vehicle imported from another game that needs UVs, or when they ask about AI UV unwrapping, PartUV or PartField: read the pilot verdict here before recommending any AI tool. Spanish triggers: generar UVs, atlas legible, las UVs salen con mil islas, islas que se pisan, textura estirada, plantilla de livery, UVs limpias, preparar el modelo para texturizar, auditar UVs, cuántas islas, hay solape, IA para UVs."
argument-hint: "<in.blend> <out.blend> <out_dir> <tag> <min_faces> <object_name>"
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /uv-clean-atlas

Turns a hard-surface mesh (a vehicle body, a prop, weapon furniture) into a UV atlas a person can read like a livery template: each island is a recognizable panel, nothing overlaps, texel density is even, and moderate stretch is accepted as the price of legibility.

Validated on 2026-07-16 on the body of LFQuad (the source author's quad-bike mod), on two inputs: a clean retopology of 10.5k quads (54 islands, 30 of them panels, outlines straightened, overlap exactly zero) and a raw decimated rip of 36.9k triangles (65 islands, straightening rolled back automatically, overlap exactly zero). Sixteen earlier methods had produced 500 to 2,000 islands on the same body.

The scripts run inside Blender and need no DayZ Tools and no `P:\` drive. The DayZ side of UVs (how a `.p3d` stores them, which UV set a material reads, what binarizing does, symptoms in game) is in `skills/_shared/models/uv-mapping.md`.

## Which method

Pick the row before running anything. Mixing them is how a paint mesh ends up with hundreds of islands nobody can paint.

| The mesh | Method | Read |
|---|---|---|
| Vehicle panels, a prop or weapon body that a person will paint (the default) | **Track A**: view charts, the pipeline below | This file |
| An organic mesh in one shell that a person will paint: a statue, a coat, a character | **Photograph**, do not unwrap | `references/organic-paint-photograph.md` |
| A group that Track A or SLIM collapses (faces with zero UV area, a layer of NaN) | **Track B**: `smart_project` over the whole mesh, then an exact fold loop | "Two tracks" below |
| A model that already ships, where only UVs may change, or an atlas that serves more than one visual LOD | Each LOD unwrapped on its own, both packed into one sheet | `references/multi-lod-shared-atlas.md` |

The last row is a different job. The LOD chain and the material assignment are fixed, and the advice about a few large islands stops being available. Read that reference first: it has the measured seam trade-off, why a LOD transfer cannot work below a granularity ratio, the shared-sheet layout that replaces it, and how to align and judge the bake.

## Requirements

- Blender 4.3 or later, run headless. The `MINIMUM_STRETCH` (SLIM) unwrap method is required. Verified in 5.1.
- Mesh health first. Run the weld and degenerate-face checks before unwrapping: duplicate vertices read as open boundaries, and zero-area faces crash naive code. Every script here guards zero-length normals, but garbage in still means specks out. The checks and the adaptive weld are in `references/mesh-health-and-seams.md`.
- A decimated rip can be unwrapped directly (validated). If the mesh has 3D micro-detail on curved surfaces, such as tire lugs, retopology followed by a bake is still the better product path. Any retopology or decimation of a mesh meant to be seen needs the user's approval before it is applied.

## How to run

```cmd
blender -b <in.blend> -P "<skill-dir>\scripts\uv_clean_atlas.py" -- <out.blend> <out_dir> <tag> <min_faces> <object_name>
```

| Argument | Notes |
|---|---|
| `<in.blend>` | The file holding the mesh. The script saves to `<out.blend>`, so this file stays as it was unless both paths are the same. |
| `<out.blend>` | Saved copy: the original mesh with the new unwrap in its active UV layer. |
| `<out_dir>`, `<tag>` | Where the renders go: `<tag>_uvlayout.png` and `<tag>_uvgrid.png`. |
| `<min_faces>` | Charts smaller than this are merged into a neighbor. Validated values: 30 for the 10k mesh, 60 for the 37k mesh. |
| `<object_name>` | The mesh object to unwrap. When it is left out, or no object has that name, the script takes the first mesh object in the file without a warning, so always pass it. |

Read the layout PNG yourself before showing it to the user.

## Pipeline stages

What each stage does and why it exists:

1. **Artist-style charts by dominant view, per shell** (`uv_view_charts.py`). For each connected shell (a physical piece), cluster the face normals with k-means (k from 1 to 3, chosen by how far the normals spread) and cap the result at k charts per shell: only the largest component of each cluster is a core, and every other patch merges into the neighbor it shares the longest boundary with. This reproduces how an artist unwraps a body panel: one island per "view side" of each piece (the top of a fender, its underside), swallowing the stretch on the wrap edges. Helicoid shells such as springs, which clustering shatters, fall back to growing regions inside a 100° normal cone, which unrolls them as strips.
2. **Dust merge.** Charts under `min_faces` merge into the neighbor sharing the longest boundary. This kills confetti at the source. Isolated micro-shells with no neighbor survive as "specks", and the packer deals with them.
3. **SLIM unwrap and fold guard, one round.** Unwrap everything with `MINIMUM_STRETCH`. Detect folded charts in two ways: more than 5% mixed winding counted per *triangle* (bowtie quads hide when signed areas are summed per face), and more than 3% Monte Carlo self-overlap per chart (a wrap of more than 360° keeps consistent winding while overlapping, so a winding check alone misses it). Fix a folded chart by bisecting it on the sign of its normals (a wrapped cylinder becomes two half shells), with a median split along the PCA axis of the centroids as the fallback. The guard runs once: a second pass chases 1 to 2% cosmetic folds and cascades the island count (see "Known traps" for the one case where iterating is right).
4. **SAT finisher, one round.** Run the exact triangle against triangle check over the whole layer. The offending faces (in practice slivers of a few mm² on creases) get all their edges seamed, which isolates them as invisible speck islands, and everything is unwrapped again with plain SLIM flags.
5. **Boundary straightening, panels only, no solver** (`uv_straighten.py`). Walk each panel island's boundary loops with the bmesh radial walk, smooth them with Taubin lambda/mu smoothing (which does not shrink), cap each corner's displacement at 0.35 times the local boundary spacing (thin hole rims invert beyond that), and diffuse the displacement a few rings into the interior. There are no pins, no second solve and no repack; the displacement is bounded, so it cannot blow up the layout. Strips and thin islands are skipped, because smoothing their two rails independently turns them into bowties. Up to about 40 leftover offending faces are cut out as micro-specks. A larger set means the mesh does not tolerate straightening, and the stage rolls itself back (measured: active on the LFQuad retopology, rolled back on the raw rip; both end at SAT = 0).
6. **Semantic shelf pack** (`uv_shelf_pack.py`). Rotate every island by PCA so its long axis is horizontal. Pack the panels in rows, largest first. Turn the strips (aspect above 6: springs, rails, trims) vertical, scale them down to the height of the panel field, and group them on the right; strips are nearly invisible parts, so they pay the texel cost and the panels keep theirs. Specks go into a grid in one corner. The shelf width is tried in dry runs until the block is roughly square.
7. **Metrics and verdict** (`uv_metrics.py`). The script prints the island count, the Monte Carlo overlap, the density spread and the SAT verdict, and renders the two PNG files.

Do not "improve" stage 6 with `pack_islands`: it optimizes area, shuffles the rotations and destroys the legibility.

## Reading the output

```
SHELLS: 13                          # connected components = the island floor
CHARTS_VIEW: 41                     # after per-shell view clustering
CHARTS_AFTER_DUST: 34
FOLD_GUARD: bisecting 1 charts ...  # more than 2 or 3 charts here = a mesh very prone to wrapping
SAT_PRE_FINISH: pairs=3 faces=6     # slivers of a few mm2, expected to be small
STRAIGHTEN: loops=17 corners=1072   # panels whose outlines were smoothed
EXCISE: 9 residual offender faces   # or STRAIGHTEN_ROLLBACK_EARLY on a hostile mesh
SHELF_PACK: islands=54 panels=30 strips=9 specks=15
SAT_VERDICT: pairs=0 (ZERO OVERLAP PROVEN)   # the release gate
METRICS[...] islands=54 overlap=0.09% density_p05/p50/p95=0.85/1.00/1.20
```

- `overlap` (Monte Carlo) between 0.0 and 0.15% together with `SAT_VERDICT: pairs=0` is clean. Report the SAT line.
- `STRAIGHTEN_ROLLBACK*` lines are the safety valves working, not failures. The mesh keeps the layout from before straightening, which was already validated.
- `islands` far above three times `SHELLS` means `min_faces` is too small, the mesh has health problems, or the mesh needs a different method (see "Which method").

## What to change when the result is wrong

Change one thing per rebuild.

| Symptom | What to change |
|---|---|
| Tiny junk islands everywhere | Run the mesh health pass first; raise `min_faces` |
| A physical piece split oddly | Its normal spread sits near a k threshold; check the `_spread` cutoffs (70° and 125°) in `uv_view_charts.py` |
| Springs or rails fragmented | `frag_limit` and the cone fallback in `uv_view_charts.py` |
| Outlines still wobbly | Straightening rolled back (see the log); that mesh needs retopology or manual seams for crisp profiles |

## The quality gate

Judge the atlas against these, in priority order. The bar is a professional game livery template, where a whole car side is one island, and so are the roof, the hood and each door.

1. **Islands are semantic panels.** About 15 to 45 meaningful islands for a full vehicle body. A person must be able to say what each island is ("that is the left fender") without a legend. The floor is the shell count; aim for 1 to 3 charts per shell.
2. **Zero overlap, proven, with zero collapsed faces.** A Monte Carlo overlap estimate has a noise floor of about 0.06 to 0.15%, so "no overlap" may only be claimed from the exact SAT check with **0 pairs** (`sat_gate.py`), never from Monte Carlo numbers. And SAT = 0 only covers the triangles that entered the test; see the next section.
3. **Even density; moderate stretch is acceptable.** The 5th and 95th percentile of texel density stay within roughly 0.8 to 1.5 of the median. Even density beats zero distortion. Chasing zero distortion is exactly what fragments an atlas into confetti, and that trade is the root failure this skill fixes. This is still a hard gate in the other direction; see "Density must stay even".
4. **Organized layout.** Panels aligned to the axes in rows, long strips grouped vertically at one side, micro-specks clustered in a corner.
5. **The final judge is the user.** Render the layout and show it. "A person can read the atlas" is the acceptance test. Expect one or two rounds of feedback.

### Collapsed faces hide from the overlap check

The rule: any gate that filters part of its input must publish how many items it was given, how many it evaluated and how many it filtered out. A pass with a non-zero filtered count only covers what entered the test.

`sat_gate.py` skips any triangle whose UV area is `1e-14` or less before pairing it, because a degenerate triangle cannot overlap anything. So an unwrap that *collapses* faces to zero UV area does not fail the gate. It vanishes from it, and the worse the collapse, the cleaner the verdict reads.

Measured on the LFQuad material groups on 2026-08-27: a chrome group was reported as "done, zero overlap proven by exact SAT, 17 islands, 14,140 px/m" while **31.0% of its faces were collapsed**. The chassis read "96 islands, 1,964 px/m" with **78.0%** collapsed, its density averaged over the surviving 22%. Solved honestly, that same chassis gives 1,198 islands and **755 px/m**: the true number is 2.6 times worse than the one reported as a win.

Report `collapsed / total` next to the SAT pair count, and treat any collapse as a fail, not a footnote. Two cheap signs that it is happening:

- Criteria 1 and 3 move the wrong way. The island count *drops* and the texel density *rises* as the defect grows, because both are computed over the survivors only. A gate metric that improves while the mesh degrades is the signature.
- A mirrored share that is neither 0 nor 100% may be collapse, not mixed handedness. See `references/mlod-uv-audit.md`.

## Auditing an existing UV set

| Question | Tool |
|---|---|
| Is there any overlap, exactly, and on which faces? | `blender -b <file.blend> -P "<skill-dir>\scripts\sat_gate.py" -- <object_name>` prints `SAT_PAIRS`, `SAT_FACES` and up to 40 offending faces with their 3D position |
| How many islands, how much overlap, how even is the density, and what does the layout look like? | Import `uv_metrics.py` in a Blender script and call `score_and_render(obj, out_dir, tag)`. Its rasterizer works headless. Its grid render replaces the object's materials and removes every camera and light in the scene, so do not save the file afterwards |
| How good are the UVs of an assembled `.p3d` (LODs, proxies, material groups)? | Measure on the MLOD with py3d; the metrics and their traps are in `references/mlod-uv-audit.md` |
| How does a PartUV result score? | `audit_partuv.py`, see `references/partuv-pilot.md` |

## Two tracks: paint atlas and the smart_project fallback

### Track A, the paint atlas (the default)

For a body, a prop, or anything a person paints.

**Hard-surface panels.** Charts are the view sides of each 3D shell (`uv_view_charts.py`): one island per camera view of each physical piece, swallowing the stretch on the wrap edges.

- The island floor is `SHELLS`. Aim for about 1 to 3 charts per shell. An island count far above three times `SHELLS` means the wrong track was used.
- A vehicle body lands at about 15 to 45 islands.
- SAT pairs = 0 **and** collapsed = 0. SAT = 0 with collapse is a fake pass.
- The final pack is the shelf pack, not `pack_islands`.
- The user reading the atlas is the acceptance test.

**Organic, one shell** (statue, coat, character): photograph, do not unwrap. The full recipe is `references/organic-paint-photograph.md`; the engine is `project_atlas.py`. In short: the outside (n+) and the lining (n−) are two elevations and are never stacked; left and right stay in the same frame when the bounding box crosses the X mid-plane, with a tiny nudge in U if the midline collides, never extra frames; one global scale; pieces that overlap in the photo (legs, meaning the floor-reaching component below the hem, and limbs, meaning the front occluder) are peeled and translated rigidly inside the same elevation until the ghost is gone; SAT = 0. A leftover of about 0.03 from tube thickness was accepted. Do not run `uv_view_charts.py` and SLIM on this class of mesh. On the statue (1 shell, 5.7k faces after a QuadriFlow remesh) that gave 25 charts, the dust merge took them to 5 with density from 0.00 to 3.95, and the k=6 and Voronoi variants deformed it; Track B at 80° gave SAT = 0, 215 islands and 65.7% occupancy and the user rejected it as neither minimal nor by views. What shipped on 2026-09-02 was the photograph with peeling: 15 islands, SAT = 0, self-overlap 0.033.

### Track B, the smart_project fallback

Only for a group where SLIM or a sparse cut **collapses** faces. Do not use Track B as the recipe for a paint atlas. No script here runs Track B or the shared-sheet recipe for LODs; the source project ran them from session scripts that are not shipped, so build them from the steps below and in `references/multi-lod-shared-atlas.md`, and gate the result with `sat_gate.py`.

- Validated on 2026-08-27. A topological (tree-cotree) unwrap collapsed 31% of a chrome group and 78% of the chassis, because its seams were too sparse. The route that closed those groups at collapsed = 0 and SAT = 0: `smart_project` at 66° over the whole mesh, then `seams_from_islands` so a later unwrap keeps the same cuts, then a fold loop whose detector is the exact SAT check, then a pack with the `CONCAVE` shape method.
- The price is the island count: 17 became 214, and 96 became 1,198. That price is correct, measured against "few" islands that were really collapsed faces.
- `smart_project` run headless ignores the face selection and unwraps everything, so it is only acceptable over a whole mesh.
- Seam the material boundaries as well, so no island holds two materials. A mixed island cannot be painted and makes any per-material check meaningless.
- Give the packer its margin in **texels** (4 texels of 4096 is 0.000977), not as a fixed UV distance. At 7,760 islands a fixed 0.003 threw away 90% of the sheet: occupancy went from 5.7% to 19.9% at 4 texels.
- The fold loop's detector must be the exact SAT check, not a Monte Carlo percentage (see "Known traps").

### Three claims that were measured and found false

These were written down mid-session on 2026-09-01, as additions to Track B for a vehicle with materials and LODs, and corrected the next day. They are kept because they look right and will be proposed again.

- **"Seam only the material boundaries; skip `smart_project`."** The reason looked good: `smart_project` at 66° on the body gave **8,711 islands against 495 3D shells, a 17 times overcut**, with 18% occupancy and 530 px/m. Seams on material boundaries alone gave 695 islands with a median of 19 faces, near the 495-shell floor exactly as hoped, and **100.0% of the triangles collapsed to zero UV area**. The probe that recommended it measured the island count and NaN but not collapse, so over the survivors it reported 1,308 px/m and 76% occupancy, better numbers than the correct run's. `smart_project` remains the only seam family on that mesh with 0.0% collapse. The table of five strategies is in `references/multi-lod-shared-atlas.md`, section 3.
- **"The coarse LOD does not unwrap; transfer its UVs from LOD0 by nearest surface, one material at a time."** Three transfer strategies were measured. The best left **4,647 overlapping pairs and 167 collapsed faces**, and the one whose density came out right (ratio 0.97) still left 8,409 pairs. The cause is arithmetic, and no care in the transfer fixes it: the LOD0 islands have a median of 2 faces, while a LOD1 face has 2.5 times the area of a LOD0 face. Each LOD is unwrapped on its own and both are packed into separate regions of one sheet; sections 2 and 4 of the same reference.
- **"The density floor is 755 px/m at 4096."** That floor came from two earlier atlases that each covered a *subset* of the same body, and packing less surface into the same sheet buys density for free. Against it a whole-body atlas failed while being denser than anything the mod ships. Derived again from shipped work, the reference is 134 to 147 px/m (below); section 7 of the same reference.

What the corrected recipe delivered on the same model: both visual LODs at **0.00% collapsed and 0 SAT pairs**, 0 overlapping pairs between the LODs, a 75/25 split of the sheet, and 349 and 204 px/m.

## Density must stay even

A few islands laid out by views does not license wrap stretch. The 5th and 95th percentile of density must stay within about 0.8 to 1.5 of the median. A one-shell statue that view-clusters to 25 charts and then dust-merges to 5 (p05 = 0.00, p95 = 3.95) is a fail, even though its island count looks like a livery template.

Do not dust-merge a view chart into its neighbor when that merge would make the island wrap past the density gate. Keep the extra view island. Minimize the island count against Track B's hundreds, not against this gate.

## Handing off to texturing and DayZ

- The output file keeps the original mesh, with the new unwrap in its active UV layer. Export from there, or build the `.p3d` with py3d from there.
- Binarizing quantizes UVs to 16-bit integers over the minimum and maximum of the whole LOD, so one face with huge tiling degrades the entire LOD. This pipeline keeps everything inside 0 to 1, so it is safe. Details and the rest of the DayZ side are in `skills/_shared/models/uv-mapping.md`.
- Texel density reference: the LFQuad wheels, the closest shipped and accepted yardstick, have a UV density of 0.1307 to 0.1438 on a `_co` that decodes at **1024 x 1024**, which is **134 to 147 px/m** in game. That was measured again on 2026-09-01 by decoding the shipped `.paa`; an earlier figure of about 292 px/m was the same density read against a 2048 texture the asset does not use. Props sit around 512 px/m and first-person weapons around 1024 px/m.
- When you derive a density floor, measure both halves: the density from the model and the texture size from the file. Nothing should enter as a constant.

## PartUV and other tools

Read this before recommending any "UV AI".

Verdict of 2026-07-16 (RTX 3090, WSL2): PartUV runs locally and is the only real UV AI with code and weights, but on vehicle content it **lost** to this pipeline on the first criterion. It produced 162 islands (threshold 1.25) and 127 (threshold 2.0) against 43 on the same retopology mesh, and 232 against 63 on the same rip. It charts per PartField part with no dust control, so helicoids and junk shells explode into storms of specks. The density spread was comparable, and its GPU cost is fine (about 4 s of inference for 10k to 37k triangles).

Use it only when semantic part separation matters more than the island count, or as an experimental chart source feeding this pipeline's later stages. Setup, quirks, exact numbers and the commands to run it again are in `references/partuv-pilot.md`.

The wider 2026 survey (Ministry of Flat, RizomUV, xatlas, Nuvo, SeamGPT and others, and why each was discarded or shortlisted) is in `references/tool-research.md`.

## Known traps

Every one of these was hit during development.

**Blender operators**

- `bpy.ops.uv.smart_project` run headless ignores the face selection and unwraps everything. The Track A pipeline never uses it. If you script around it, do not rely on the selection.
- `smart_project` stays unusable for a partial selection, but as a seam generator for a whole mesh it is the honest fallback when the topological cut collapses. On four LFQuad groups it gave 0.0% collapsed and SAT = 0 where the tree-cotree route gave 3.6 to 78.0% collapsed. Follow it with `seams_from_islands`. The price is the island count (17 to 214, 96 to 1,198), and "Collapsed faces hide from the overlap check" is why that price is the correct one.
- Never deduplicate bmesh loop-UV wrappers by `id()`. The wrappers are transient and their ids are recycled, so loops get skipped silently. Each loop owns its UV; visit each loop once. The same goes for `loop.index`, which is not guaranteed to be initialized: key corners by `(face.index, vert.index)`.
- Zero-length face normals exist in real meshes. Guard every `Vector.angle()`.

**The unwrap**

- Sparse seams make SLIM fail silently. With a tree-cotree cut graph (133 seam edges for 42 shells over 45k triangles), `MINIMUM_STRETCH` returned **78.3% of the triangles collapsed straight out of the unwrap**, a median UV extent per triangle of exactly zero, and no warning. `ANGLE_BASED` on the same seams left 15.8% collapsed and squeezed the whole layout into U from 0 to 0.048, which is 18 px/m. On another group both solvers returned a UV layer that was **all NaN** (109,086 NaN values, 6 per triangle for 18,181 triangles). NaN fails an `area > eps` test, so every triangle was filtered out and the gate downstream died in `min()` on an empty list. An `except TypeError` around `bpy.ops.uv.unwrap` only catches a Blender that does not know the enum. Check the returned layer for NaN and for collapse instead.
- A pinned SLIM re-solve is a chain of traps. `no_flip` defaults to False, and the default 10 iterations do not converge against pins (1,302 folded pairs measured). With pins, the automatic pack also drops the *unpinned* islands on top of the pinned ones, which shows up as phantom SAT counts between islands before packing. The shipped pipeline avoids pins entirely and uses local diffusion; do not bring them back casually.
- `no_flip=True` on a full re-unwrap makes charts that are prone to wrapping overlap in a spiral instead of flipping (133 leftover pairs measured on the rip). Flips are the fold guard's signal; do not suppress them globally.

**Guards and gates**

- Monte Carlo overlap has a noise floor. Only SAT = 0 proves zero overlap.
- The fold guard's detector must be the gate's own instrument. A Monte Carlo estimate over a percentage threshold can never clear an exact zero-tolerance gate: whatever sits below the threshold survives every round, forever. Measured on 2026-08-27 with the exact per-island SAT check as the detector instead: the engine group went from 31,481 pairs to 0, and the chassis from 5,839 to 0.
- "One guard round only" is a cost rule, not a correctness rule. In the Track A pipeline a second pass chases 1 to 2% cosmetic folds and cascades the island count (32 to 84 measured, and 26 to 508 in an earlier spike), so one round is right whenever it already leaves the exact gate at zero. When it does not, iterate until the gate is clean and pay the islands: 200 to 244 and 546 to 1,375 were measured, over 3 to 7 rounds, with texel density essentially unchanged. A mesh that still folds cannot ship, however few islands it has. Pair counts do not fall steadily across rounds (4, 2, 7, 10, 0 was measured), so do not stop at the first increase.
- Judge overlap only on the final packed layout, and prefer a rollback over cutting out many faces. More than about 40 offending faces after straightening means the stage hurt the mesh.

**Boundary smoothing**

- A plain Laplacian on a closed curve is curve-shortening flow: it collapses the boundaries into the island (605k SAT pairs measured). Use Taubin lambda/mu smoothing and cap each corner's displacement by the local boundary spacing.

**Working on Windows**

- For a script that goes from Windows into WSL, strip the CRLF line endings (`tr -d '\r'`) before running it with `bash`. Never escape quoted Python inline through PowerShell into bash; write a script file.
- Do not write or edit `.py` files inside a folder synced by OneDrive; files have come back truncated or with null bytes. Work in a scratch folder and copy the results in, checking the size.

## On Linux

Everything above is the Windows workflow and holds there. For Linux, the Proton setup, the measured tool matrix and the pitfalls are in `_shared/linux-proton.md`; this section only says what changes for this skill.

- The WSL2 steps are Linux already. Run them natively and skip the Windows to WSL plumbing (stripping CRLF, quoting from PowerShell into bash).
- Headless Blender is `blender -b <file.blend> --python <script> -- <args>`.
- The PNG step of `project_atlas.py` (`render_atlas_pngs`) calls `powershell.exe` with `draw_atlas_fallback.ps1`, a script that is not shipped here on any OS. On Linux, skip that step or draw the atlas PNG files with PIL.

## Scripts

All in `<skill-dir>\scripts\`. Every `.py` here runs inside Blender (`blender -b ... -P <script> -- <args>`), not under plain Python.

| Script | Does |
|---|---|
| `uv_clean_atlas.py` | The Track A pipeline, stages 1 to 7 |
| `uv_view_charts.py`, `uv_straighten.py`, `uv_shelf_pack.py`, `uv_metrics.py` | The stages, imported by the pipeline; `uv_metrics.py` is also the audit module |
| `sat_gate.py` | The exact overlap gate for the active UV layer of one object |
| `project_atlas.py` | The orthographic projector behind the photograph method. `blender -b <file.blend> --python project_atlas.py -- <assignment.json or SMOKE> <outdir> [--placement-override <file.json>]`. It is tied to the LFQuad body mesh and stops with exit code 2 on any other `.blend` until its constants are changed; see "Running the engine" in `references/organic-paint-photograph.md` |
| `export_objs_tri.py` | Exports an object as a sanitized, triangulated OBJ for PartUV |
| `audit_partuv.py` | Scores a PartUV result and re-packs it with the shelf packer |
| `partuv_install.sh` | Installs PartUV on Linux or WSL2 |

## References

| Question | Open |
|---|---|
| How do I build a paint atlas for a statue, a coat or a one-shell character? | `references/organic-paint-photograph.md` |
| How do I re-unwrap a model that already ships, or share one atlas between LODs? How do I align the high-poly and judge the bake? | `references/multi-lod-shared-atlas.md` |
| What must a mesh pass before unwrapping? Which Blender calls corrupt UV layers? Why do angle-based cuts fragment, and how does a topological cut work? How do I stitch or split islands in an existing layout? | `references/mesh-health-and-seams.md` |
| What do I measure on an assembled `.p3d`, and what do the numbers of a bad unwrap look like? | `references/mlod-uv-audit.md` |
| How do I install and run PartUV, and how did it score? | `references/partuv-pilot.md` |
| Which other automatic unwrap tools exist, and why were they not chosen? | `references/tool-research.md` |
| How does DayZ store and read UVs, and which in-game symptom points at which UV fault? | `skills/_shared/models/uv-mapping.md` |
