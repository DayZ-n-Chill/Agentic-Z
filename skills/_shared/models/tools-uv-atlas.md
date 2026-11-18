# Clean UV atlas for hard surface meshes

How to turn a hard surface mesh (a vehicle body, a prop, weapon furniture) into a UV atlas a person can read like a livery template: each island a recognizable panel, nothing overlapping, even texel density, and moderate stretch accepted as the price of legibility. The DayZ side of UVs (how a `.p3d` stores them, which UV set a material reads, what binarizing does, symptoms in game) is in `uv-mapping.md`.

The scripts run inside Blender and need no DayZ Tools and no `P:\` drive, so nothing here cites vanilla data. They are in `skills\dayz-model-tools\scripts\`, written `<scripts>` below. The numbers come from the body of a quad bike mod, on two inputs: a clean retopology of 10.5k quads (54 islands, 30 of them panels, outlines straightened, overlap exactly zero) and a raw decimated rip of 36.9k triangles (65 islands, straightening rolled back on its own, overlap exactly zero). Sixteen other methods gave 500 to 2,000 islands on the same body.

## Which method

Pick the row before running anything. Mixing them is how a paint mesh ends up with hundreds of islands nobody can paint.

| The mesh | Method | Read |
|---|---|---|
| Vehicle panels, a prop or weapon body a person will paint (the default) | The view chart pipeline below | This file |
| An organic mesh in one shell a person will paint: a statue, a coat, a character | Photograph it, do not unwrap | `tools-uv-organic-photograph.md` |
| A group the view chart pipeline or SLIM collapses (faces with zero UV area, a layer of NaN) | `smart_project` over the whole mesh, then an exact fold loop | "The smart_project fallback" below |
| A model that already ships, where only UVs may change, or an atlas shared by more than one visual LOD | Each LOD unwrapped on its own, both packed into one sheet | `tools-uv-multi-lod-atlas.md` |

The last row is a different job: the LOD chain and the material assignment are fixed, and few large islands are no longer possible. Read that file first.

## Requirements

- Blender 4.3 or later, run headless. The `MINIMUM_STRETCH` (SLIM) unwrap method is required. Checked in Blender 5.1.
- Mesh health first. Run the weld and degenerate face checks before unwrapping: duplicate vertices read as open boundaries, and zero area faces crash naive code. Every script here guards zero length normals, but a broken mesh still gives specks. The checks and the adaptive weld are in `tools-uv-mesh-health.md`.
- A decimated rip can be unwrapped directly. When the mesh has 3D micro detail on curved surfaces, such as tire lugs, retopology and a bake is still the better path. Any retopology or decimation of a mesh meant to be seen needs the user's approval before it is applied.

## How to run

```cmd
blender -b <in.blend> -P "<scripts>\uv_clean_atlas.py" -- <out.blend> <out_dir> <tag> <min_faces> <object_name>
```

| Argument | Notes |
|---|---|
| `<in.blend>` | The file holding the mesh. The script saves to `<out.blend>`, so this file stays as it was unless both paths are the same |
| `<out.blend>` | Saved copy: the original mesh with the new unwrap in its active UV layer |
| `<out_dir>`, `<tag>` | Where the renders go: `<tag>_uvlayout.png` and `<tag>_uvgrid.png` |
| `<min_faces>` | Charts smaller than this merge into a neighbour. 30 worked for the 10k mesh, 60 for the 37k mesh |
| `<object_name>` | The mesh object to unwrap. Left out or misspelled, the script takes the first mesh object in the file without a warning, so always pass it |

Look at the layout PNG yourself before showing it to the user.

## Pipeline stages

1. Charts by dominant view, per shell (`uv_view_charts.py`). For each connected shell, cluster the face normals with k-means (k from 1 to 3, chosen by how far the normals spread) and cap the result at k charts per shell: only the largest component of each cluster is a core, and every other patch joins the neighbour it shares the longest boundary with. This is how an artist unwraps a body panel, one island per view side of each piece, with the stretch taken on the wrap edges. Helical shells such as springs, which clustering shatters, fall back to growing regions inside a 100 degree normal cone, which unrolls them as strips.
2. Dust merge. Charts under `min_faces` join the neighbour with the longest shared boundary. Isolated micro shells with no neighbour stay as specks for the packer.
3. SLIM unwrap and fold guard, one round. Unwrap everything with `MINIMUM_STRETCH`. A chart is folded when more than 5 % of its triangles have mixed winding (counted per triangle, because bowtie quads hide when signed areas are summed per face), or when more than 3 % of it overlaps itself by Monte Carlo sampling (a wrap past 360 degrees keeps consistent winding while overlapping). Split a folded chart on the sign of its normals, so a wrapped cylinder becomes two half shells, with a median split along the PCA axis of the centroids as the fallback. The guard runs once; see "Known traps" for when to iterate.
4. SAT finisher, one round. Run the exact triangle against triangle check over the whole layer. The offending faces, in practice slivers of a few mm² on creases, get all their edges seamed so they become invisible speck islands, and everything is unwrapped again with plain SLIM flags.
5. Boundary straightening, panels only (`uv_straighten.py`). Walk each panel island's boundary loops, smooth them with Taubin lambda/mu smoothing (which does not shrink), cap each corner's movement at 0.35 times the local boundary spacing (thin hole rims invert past that), and spread the movement a few rings into the interior. There are no pins, no second solve and no repack, so the layout cannot blow up. Strips and thin islands are skipped, because smoothing their two rails separately turns them into bowties. Up to about 40 leftover offending faces are cut out as specks; more than that means the mesh does not take straightening, and the stage rolls itself back (active on the retopology, rolled back on the raw rip, both ending at SAT = 0).
6. Shelf pack (`uv_shelf_pack.py`). Turn each island by PCA so its long axis is horizontal. Pack the panels in rows, largest first. Turn the strips (aspect above 6: springs, rails, trims) upright, scale them to the height of the panel field and group them on the right; strips are nearly invisible parts, so they pay the texel cost and the panels keep theirs. Specks go into a grid in one corner. The shelf width is tried in dry runs until the block is roughly square.
7. Metrics and verdict (`uv_metrics.py`). Prints the island count, the Monte Carlo overlap, the density spread and the SAT verdict, and renders the two PNG files.

Never replace stage 6 with `pack_islands`: it optimizes area, shuffles the rotations and destroys legibility.

## Reading the output

```text
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

- `overlap` between 0.0 and 0.15 % together with `SAT_VERDICT: pairs=0` says nothing overlaps among the triangles the check tested. That is not yet a pass: this log has no collapsed count, because the pipeline's checks drop zero area UV triangles without counting them. Run `sat_gate.py` on `<out.blend>` (see "Auditing an existing UV set") and read its `SAT_INPUT` line. The atlas is clean only when `collapsed_tris=0`, `nan_tris=0` and `SAT_PAIRS: 0`. Report `SAT_PAIRS` together with collapsed over total faces.
- `STRAIGHTEN_ROLLBACK*` lines are the safety valve working, not a failure. The mesh keeps the layout from before straightening, which already passed.
- `islands` far above three times `SHELLS` means `min_faces` is too small, the mesh has health problems, or it needs another method (see "Which method").

## What to change when the result is wrong

Change one thing per rebuild.

| Symptom | What to change |
|---|---|
| Tiny junk islands everywhere | Run the mesh health checks first; raise `min_faces` |
| A physical piece split oddly | Its normal spread sits near a k threshold; check the `_spread` cutoffs (70 and 125 degrees) in `uv_view_charts.py` |
| Springs or rails in fragments | `frag_limit` and the cone fallback in `uv_view_charts.py` |
| Outlines still wobbly | Straightening rolled back (see the log); that mesh needs retopology or hand placed seams for crisp outlines |

## The quality gate

Judge the atlas against these, in order. The bar is a game livery template, where a whole car side is one island, and so are the roof, the hood and each door.

1. Islands are recognizable panels: about 15 to 45 for a full vehicle body. A person must be able to say what each island is ("that is the left fender") without a legend. The floor is the shell count; aim for 1 to 3 charts per shell.
2. Zero overlap, proven, with zero collapsed faces. A Monte Carlo estimate has a noise floor of about 0.06 to 0.15 %, so claim "no overlap" only from the exact SAT check with 0 pairs (`sat_gate.py`). SAT = 0 covers only the triangles that entered the test; see the next section.
3. Even density, with moderate stretch accepted. The 5th and 95th percentile of texel density stay within roughly 0.8 to 1.5 of the median. Even density beats zero distortion, because chasing zero distortion is what breaks an atlas into confetti. See "Density must stay even" for the other side of this.
4. Organized layout: panels aligned to the axes in rows, long strips grouped upright on one side, specks in a corner.
5. The user judges last. Render the layout and show it; "a person can read the atlas" is the acceptance test. Expect one or two rounds of feedback.

### Collapsed faces hide from the overlap check

Any check that filters part of its input must report how many items it was given, how many it tested and how many it filtered out. A pass with a non zero filtered count covers only what entered the test.

`sat_gate.py` skips any triangle whose UV area is `1e-14` or less before pairing it, because a degenerate triangle cannot overlap anything. An unwrap that collapses faces to zero UV area therefore does not fail the gate. It vanishes from it, and the worse the collapse, the cleaner the verdict reads.

Measured on the quad bike's material groups: a chrome group was reported as "zero overlap proven by exact SAT, 17 islands, 14,140 px/m" while 31.0 % of its faces were collapsed. The chassis read "96 islands, 1,964 px/m" with 78.0 % collapsed, its density averaged over the surviving 22 %. Solved properly, the same chassis gives 1,198 islands and 755 px/m, 2.6 times worse than the figure reported as a success.

Report collapsed over total next to the SAT pair count, and treat any collapse as a fail. Two cheap signs that it is happening:

- The island count drops and the texel density rises as the defect grows, because both are computed over the survivors only. A metric that improves while the mesh gets worse is the sign.
- A mirrored share that is neither 0 nor 100 % may be collapse, not mixed handedness (`tools-uv-mlod-audit.md`).

## Auditing an existing UV set

| Question | Tool |
|---|---|
| Is there any overlap, exactly, and on which faces? | `blender -b <file.blend> -P "<scripts>\sat_gate.py" -- <object_name>` prints `SAT_INPUT` (faces and triangles tested, and how many were dropped as collapsed or NaN), then `SAT_PAIRS`, `SAT_FACES` and up to 40 offending faces with their 3D position |
| How many islands, how much overlap, how even is the density, and what does the layout look like? | Import `uv_metrics.py` in a Blender script and call `score_and_render(obj, out_dir, tag)`; its rasterizer works headless. Its grid render replaces the object's materials and removes every camera and light, so never save the file afterwards |
| How good are the UVs of an assembled `.p3d` (LODs, proxies, material groups)? | Measure on the MLOD with py3d (`tools-uv-mlod-audit.md`) |
| How does a PartUV result score? | `audit_partuv.py` (`tools-uv-partuv.md`) |

## Paint atlas or fallback

For a body, a prop or anything a person paints, use the view chart pipeline above. The island floor is `SHELLS`; aim for about 1 to 3 charts per shell, about 15 to 45 islands on a vehicle body. SAT pairs = 0 counts only with collapsed = 0. The final pack is the shelf pack.

For an organic mesh in one shell (a statue, a coat, a character), photograph it instead (`tools-uv-organic-photograph.md`). Never run `uv_view_charts.py` and SLIM on that kind of mesh: on a one shell statue of 5.7k faces it gave 25 charts, the dust merge took them to 5 with density from 0.00 to 3.95, and the `smart_project` fallback at 80 degrees gave 215 islands, which the user rejected as neither few nor by views. The photograph with peeling gave 15 islands, SAT = 0 and a self overlap of 0.033.

### The smart_project fallback

Use it only for a group where SLIM or a sparse cut collapses faces, never as the recipe for a paint atlas. No shipped script runs it or the shared sheet recipe for LODs, so build them from the steps here and in `tools-uv-multi-lod-atlas.md`, and check the result with `sat_gate.py`.

- On the quad bike a topological (tree-cotree) unwrap collapsed 31 % of a chrome group and 78 % of the chassis, because its seams were too sparse. What closed those groups at collapsed = 0 and SAT = 0: `smart_project` at 66 degrees over the whole mesh, then `seams_from_islands` so a later unwrap keeps the same cuts, then a fold loop whose detector is the exact SAT check, then a pack with the `CONCAVE` shape method.
- The price is the island count: 17 became 214, and 96 became 1,198. That price is correct, because the "few" islands before were collapsed faces.
- `smart_project` run headless ignores the face selection and unwraps everything, so it only fits a whole mesh.
- Seam the material boundaries as well, so no island holds two materials. A mixed island cannot be painted and breaks any per material check.
- Give the packer its margin in texels (4 texels of 4096 is 0.000977), not as a fixed UV distance. At 7,760 islands a fixed 0.003 threw away 90 % of the sheet: occupancy went from 5.7 % to 19.9 % at 4 texels.

Three tempting shortcuts fail on a vehicle with several materials and LODs:

- Seaming only the material boundaries and skipping `smart_project`. On the body that gave 695 islands, close to the floor of 495 shells, and 100.0 % of the triangles collapsed to zero UV area straight out of the unwrap; after the fold loop and packing 77 % were still collapsed. `smart_project` at 66 degrees gave 8,711 islands but is the only seam family on that mesh with 0.0 % collapse. The comparison is in `tools-uv-multi-lod-atlas.md`, section "You cannot fix it by cutting fewer seams".
- Transferring the coarse LOD's UVs from LOD0 by nearest surface. The best of three transfers left 4,647 overlapping pairs and 167 collapsed faces. The LOD0 islands had a median of 2 faces while a LOD1 face had 2.5 times the area of a LOD0 face, so no transfer can work. Unwrap each LOD on its own and pack both into one sheet.
- A density floor taken from atlases that covered only part of the body. Packing less surface into the same sheet buys density for free; a floor of 755 px/m at 4096 from such atlases failed a whole body atlas that was denser than anything the mod ships.

Done this way on the same model, both visual LODs ended at 0.00 % collapsed and 0 SAT pairs, with 0 overlapping pairs between them, a 75/25 split of the sheet, and 349 and 204 px/m.

## Density must stay even

A few islands laid out by views do not license wrap stretch. The 5th and 95th percentile of density must stay within about 0.8 to 1.5 of the median. A one shell statue that clusters to 25 charts and merges to 5 (p05 = 0.00, p95 = 3.95) fails, even though its island count looks like a livery template.

Never merge a view chart into its neighbour when the merge would make the island wrap past this limit; keep the extra island.

## Handing off to texturing and DayZ

- The output file keeps the original mesh, with the new unwrap in its active UV layer. Export from there, or build the `.p3d` with py3d from there.
- Binarizing quantizes UVs to 16 bit integers over the range of the whole LOD, so one face with huge tiling degrades the entire LOD. This pipeline keeps everything inside 0 to 1, so it is safe (`uv-mapping.md`).
- Density reference: the quad bike's wheels, the closest shipped and accepted yardstick, have a UV density of 0.1307 to 0.1438 on a `_co` that decodes at 1024 x 1024, which is 134 to 147 px/m in game. Props sit around 512 px/m and first person weapons around 1024 px/m.
- When you derive a density floor, measure both halves: the density from the model and the texture size from the `.paa` itself. Nothing should enter as a constant.

## PartUV and other tools

Read this before recommending any "UV AI". PartUV runs locally and is the only UV AI with public code and weights, but on vehicle content it loses on island count. On the same meshes it produced 162 islands (threshold 1.25) and 127 (threshold 2.0) against 43 for this pipeline on the retopology, and 232 against 63 on the rip. Those 43 and 63 are this pipeline before stage 5; the current scripts give 54 and 65. PartUV charts per PartField part with no dust control, so springs and junk shells burst into specks. Its density spread was comparable, and its GPU cost is low (about 4 s of inference for 10k to 37k triangles).

Use it only when separating parts by meaning matters more than the island count, or as a chart source feeding stages 3 to 7 here. Setup and numbers are in `tools-uv-partuv.md`; the wider survey (Ministry of Flat, RizomUV, xatlas, Nuvo, SeamGPT and others) is in `tools-uv-tool-survey.md`.

## Known traps

The Blender operator, unwrap, fold guard, boundary smoothing and Windows traps measured on this pipeline are in `tools-uv-atlas-traps.md`. Read it before you script around `smart_project`, SLIM or pins.

## On Linux

The steps above are the Windows workflow. For Linux, the Proton setup, tool matrix and pitfalls are in `_shared/linux-proton.md`. What changes here:

- The WSL2 steps are Linux already; run them natively and skip the CRLF and quoting steps (`tools-uv-atlas-traps.md`, "On Windows").
- Headless Blender is `blender -b <file.blend> --python <script> -- <args>`.
- The PNG step of `project_atlas.py` (`render_atlas_pngs`) would run `draw_atlas_fallback.ps1` through `powershell.exe`, but that script is not shipped, so on every OS the step skips itself, logs `PNG_RENDER_SKIPPED` and the run ends normally. Draw the atlas PNG files from `atlas_a_islands.json` yourself, for example with PIL.

## Scripts

Each script below runs inside Blender (`blender -b ... -P <script> -- <args>`), not under plain Python; `partuv_install.sh` runs under bash. The `test_*.py` files in the same folder run under plain pytest and need no Blender.

| Script | Does |
|---|---|
| `uv_clean_atlas.py` | The view chart pipeline, stages 1 to 7 |
| `uv_view_charts.py`, `uv_straighten.py`, `uv_shelf_pack.py`, `uv_metrics.py` | The stages, imported by the pipeline; `uv_metrics.py` is also the audit module |
| `sat_gate.py` | The exact overlap check for the active UV layer of one object |
| `project_atlas.py` | The orthographic projector behind the photograph method. It is tied to the quad bike body mesh and exits with code 2 on any other `.blend` until its constants are changed (`tools-uv-organic-photograph.md`, section "Running the engine") |
| `export_objs_tri.py` | Exports an object as a clean, triangulated OBJ for PartUV |
| `audit_partuv.py` | Scores a PartUV result and repacks it with the shelf packer |
| `partuv_install.sh` | Installs PartUV on Linux or WSL2 |

## Where to read more

| Question | Open |
|---|---|
| Which Blender, SLIM, fold guard and Windows traps break this pipeline? | `tools-uv-atlas-traps.md` |
| How do I build a paint atlas for a statue, a coat or a one shell character? | `tools-uv-organic-photograph.md` |
| How do I re-unwrap a model that already ships, or share one atlas between LODs, and how do I align the high poly and judge the bake? | `tools-uv-multi-lod-atlas.md` |
| What must a mesh pass before unwrapping, which Blender calls corrupt UV layers, and how do I stitch or split islands? | `tools-uv-mesh-health.md` |
| What do I measure on an assembled `.p3d`, and what do the numbers of a bad unwrap look like? | `tools-uv-mlod-audit.md` |
| How do I install and run PartUV, and how did it score? | `tools-uv-partuv.md` |
| Which other automatic unwrap tools exist, and why were they not chosen? | `tools-uv-tool-survey.md` |
| How does DayZ store and read UVs, and which in game symptom points at which UV fault? | `uv-mapping.md` |
