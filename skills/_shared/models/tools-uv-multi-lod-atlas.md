# Re-unwrapping a model that already ships, with a LOD chain

What changes when the only thing you may move is UV: how to prove the change is UV only, why a LOD transfer fails, the shared-sheet layout that replaces it, and how to align and judge the bake. Measured end to end on 2026-09-01 and 02 on the body model of a quad-bike vehicle mod: two visual LODs of 38,831 and 15,422 faces, 16 materials, 4 wheel proxies and 29 selections per LOD. Nothing here was checked on `P:\`; it is measured on that mod.

This is a different job from the one `tools-uv-atlas.md` describes. There the input is a mesh you are free to treat as raw material. Here the model **already ships**: its selections carry memory points, damage zones and proxy mounts, its material assignment is wired into `config.cpp`, and the only thing you are allowed to move is UV. Everything below is what that constraint costs and how to pay it.

Read this when the request sounds like "re-unwrap the shipped model", "change UVs only" or "make both LODs share a texture", or when an atlas has to serve more than one visual LOD.

## Contents

1. [Make "UV only" a measurement](#1-make-uv-only-a-measurement-not-an-intention)
2. [You cannot transfer a fragmented layout onto a decimated LOD](#2-you-cannot-transfer-a-fragmented-layout-onto-a-decimated-lod)
3. [You cannot fix it by cutting fewer seams](#3-you-cannot-fix-it-by-cutting-fewer-seams)
4. [The shape that works: one sheet, disjoint regions](#4-the-shape-that-works-one-sheet-disjoint-regions)
5. [Aligning the high-poly](#5-aligning-the-high-poly-search-the-frame-never-assume-it)
6. [Measure the map where it is sampled](#6-measure-the-map-where-it-is-sampled)
7. [Calibrate density against what already ships](#7-calibrate-density-against-what-already-ships)
8. [Checklist](#checklist)

## 1. Make "UV only" a measurement, not an intention

Before touching anything, freeze a fingerprint of everything that is **not** UV and compare against it afterwards. Write it in complementary form: not a list of things that must survive (that list is written by whoever is doing the changing) but a hash of the whole, with `Vertex.uv` as the single field deliberately left out.

Per LOD, hash the point coordinates, the face-to-point topology, the `(texture, material)` pair of every face, and the selection names. In MLOD the UV lives per face-vertex, so a legitimate unwrap does not need to touch a single point, and any difference in those four hashes means the change stopped being a UV change.

Calibrate it by mutation before believing it. Four candidates were built in the run:

| Mutation | Expected | What it moves |
|---|---|---|
| Untouched file | passes | nothing |
| **One UV moved by 0.25** | **passes** | nothing |
| One point moved by 1 mm | fails | only `points` |
| One selection renamed | fails | only `selections` |

The bold row is the one that matters and the one usually skipped. A gate that also rejects the legitimate change is not strict, it is broken, and that failure is invisible if you only ever test the bad cases.

## 2. You cannot transfer a fragmented layout onto a decimated LOD

Three attempts, three distinct failure modes, all measured on the same pair of LODs:

| Attempt | Method | Result on LOD1 |
|---|---|---|
| v1 | Nearest neighbor per corner, biased 12% toward the face center | occupancy **25.114%**, a single face with **41% of the atlas** |
| v2 | Pinned island per face, fallback affine map | correct density (ratio LOD1/LOD0 = 0.97) and **8,409 overlapping pairs**, 349,089 texels |
| v3 | Per-island projection with the point clipped to the triangle | 4,647 pairs, 329,542 texels, and **167 squashed faces** |

The v2 row is the instructive one: **the density came out right and the sheet was still ruined**. A per-face affine map is locally correct and globally inconsistent, so adjacent faces overlap each other. Checking density alone would have shipped it.

### The cause is granularity, and it is arithmetic

The LOD0 islands had a **median of 2 faces**. LOD0 carries 38,831 faces over 10.76 m² and LOD1 15,422 faces over 10.53 m², so the mean LOD1 face is **2.5 times** the area of a LOD0 face. One coarse face therefore spans several islands at once. Clamp it into one and it squashes; spread it across several and its neighbors pile up. There is no third option, and no amount of care in the transfer changes the arithmetic.

Before attempting any LOD transfer, measure the ratio `median island area / mean coarse face area`. Below about 1 the transfer cannot work.

## 3. You cannot fix it by cutting fewer seams

The obvious response is to make the islands bigger. Measured on the same mesh, unwrap only (no fold loop, no packing), with the collapse percentage next to the island count:

| Seam strategy | Seams | Islands | Median faces | Largest | NaN | **Collapsed** |
|---|---:|---:|---:|---:|---:|---:|
| `smart_project` 80° | 49 | 8,515 | 2 | 389 | 0 | **0.0%** |
| Material boundaries + edges sharper than 60° | 15,401 | 5,188 | 2 | 1,579 | 0 | **15.3%** |
| Material boundaries + edges sharper than 40° | 21,669 | 8,577 | 2 | 819 | 0 | 0.1% |
| Material boundaries + edges sharper than 25° | 28,433 | 13,442 | 2 | 620 | 0 | 0.0% |
| **Material boundaries only** | 49 | **695** | **19** | 1,594 | 0 | **100.0%** |

The floor is 495 connected shells in 3D, so 695 islands is nearly optimal, and it flattens the entire mesh. The only seam family that survives is the projection route, and that is precisely the one that fragments. The intermediate angle thresholds are worse than both ends: more seams *and* collapse.

**The trade is not negotiable on this class of mesh.** The advice to build a legible atlas of few large semantic islands assumes a mesh you may retopologize. A shipped hard-surface body with hundreds of small welded shells does not offer that choice.

### The probe that recommended the disaster

The first version of that seam probe measured island count and NaN, and nothing else, so it recommended the 695-island strategy. The figures in this paragraph come from running that strategy through the whole recipe (fold loop and packing), not from the raw unwrap in the table above, which collapsed 100.0%; the fold loop's cuts and re-unwraps brought part of the triangles back. Every counter downstream in the recipe filters `abs(area) > 1e-14` before measuring, so over the survivors the collapsed run reported **1,308 px/m and 76% occupancy**: better numbers than the correct run's. Only the exact SAT check over the unfiltered triangles found that **30,032 of 38,832, or 77%,** were still collapsed after the fold loop.

This is the rule from "Collapsed faces hide from the overlap check" in `tools-uv-atlas.md`, one level deeper: it is not only the shipped gate that inherits the area filter, it is **the probe you write to choose between strategies**. A probe that cannot see the failure the project already paid for will select for it. Put `collapsed / total` in every comparison table you build, including the throwaway ones.

## 4. The shape that works: one sheet, disjoint regions

Neither LOD carries the other's layout. Each is unwrapped on its own with the projection recipe, the coarse LOD is scaled to take a declared share, and both are packed **together as one packing problem** into a single sheet.

One texture still serves both: painting happens once on the fine LOD's region, and the coarse LOD's region is filled at bake time by baking it directly from the same high-poly. That is simpler than resampling the fine region, and it never meets the granularity problem, because a bake works per texel.

Setting the share: after per-island density normalization each island's UV area equals its 3D area, so the two LODs arrive at roughly 1:1. The packer fits everything uniformly, so **the ratio going in is the ratio coming out**. Scale the coarse LOD by `sqrt(want / have)` before packing and the split lands exactly.

Measured result at a 75/25 split, a 4096 sheet and a 4-texel pack margin:

| | LOD0 | LOD1 |
|---|---:|---:|
| Faces | 38,831 | 15,422 |
| Islands after converging | 8,708 | 6,287 |
| Fold loop iterations | 4 | 2 |
| Collapsed | **0.00%** | **0.00%** |
| Exact SAT overlap | **0 pairs** | **0 pairs** |
| Real sheet share | 75.0% | 25.0% |
| Density | 349 px/m | 204 px/m |

Overlapping pairs between the two LODs: **0**. Every island holds one material, which comes free if you seam the material boundaries before unwrapping: 49 edges on this mesh, and worth doing, because an island with two materials cannot be painted and breaks any per-material check.

### What sharing costs

Packing both LODs dropped the fine LOD from 528 px/m (alone, 17.9% occupancy) to 349 px/m (shared, 10.4% total). Most of that is not the sharing but the **gutter**: about 15,000 islands of roughly 19 texels a side, each paying a 4-texel margin, is a 42% linear inflation per island. The levers, in order of honesty:

- Fewer islands: not available here, see section 3.
- A smaller pack margin: cheap (about +18% at 2 texels), but it invalidates whatever no-bleed measurement was made against the bake's own margin, so it costs a re-measure.
- A bigger sheet: doubles density at 8192, at four times the texture memory.

Report the number and let the owner choose. 349 px/m was 2.6 times the shipped reference (section 7), so it was accepted.

## 5. Aligning the high-poly: search the frame, never assume it

A high-to-low bake fires rays from the low surface and records the high one. If the two are not in the same place the map records detail from the wrong spot, and the error is invisible in every offline check. It shows up in game as relief that does not match the silhouette.

The handoff for this model said the high-poly rip (the model taken from another game) "could not serve this mesh", citing p95 = 6.1 mm. That figure had been taken against a different OBJ **and** without any frame search. The real fit, found by trying all 48 axis permutations with sign flips, each re-centered on the bounding box:

```
(-x,  z,  y)   p50=  0.47 mm   p95=   1.82 mm   outside cage   2.0%   <- this one
( x,  z,  y)   p50=  1.14 mm   p95=  21.35 mm   outside cage   9.0%
identity       p50=163.71 mm   p95= 438.62 mm   outside cage  93.6%
( x,  z, -y)   p50=829.14 mm   p95=1210.97 mm   outside cage 100.0%
```

Two things make the search cheap and reliable:

- **Sorted bounding-box dimensions identify the object before anything else.** `[0.8848, 0.9478, 1.8736]` against `[0.8848, 0.9463, 1.8732]` says "same object, same scale, axes permuted" in one line, and tells you the search is worth running.
- **Re-center each candidate on the bounding-box center before scoring.** A correct permutation scores terribly under a pure origin offset and gets discarded; this model needed a 144 mm shift in one axis.

**Check the determinant of the 3x3.** Here it came out +1, so the transform is a rotation and the baked normals keep their handedness. A −1 means the alignment mirrors, and the map will be chirally wrong in a way that is easy to miss.

Move the low mesh into the high-poly's space, not the other way round. A rigid transform leaves tangent-space normals untouched, since they are defined against the surface, and moving one object beats re-parenting eleven.

### The guard criterion is reach, not deviation

A first guard demanded `p95 < cage/4` and threw the coarse LOD out at p95 = 5.22 mm. That was wrong: **the coarse LOD is supposed to deviate from the high-poly**. Capturing exactly that deviation is what the bake is for.

The criterion that discriminates is the fraction of the low mesh sitting beyond the ray's reach: **1.9% and 2.1%** for the two aligned LODs against **93.6% and 95.6%** for the misaligned frames, with `p50` separating them by two orders of magnitude (1.7 mm against 164 mm). Fail on `fraction beyond cage > 10%` or `p50 > cage`, and report p50 and p95 without gating on them.

## 6. Measure the map where it is sampled

The bake's own quality check rejected a good map at 2.433% non-unit normals against a 1% bar. Opening the file showed that **99.08% of those texels were in the packing gutter**; of the texels a triangle actually covers, only **0.0976%** were short.

The gutter fraction tracks island count, not bake quality (this sheet is 89.6% empty), so a whole-sheet threshold measures fragmentation and calls it a defect.

Rasterize the UV coverage, erode it by one texel to get the "core" (texels whose whole 3x3 neighborhood is covered), and put both tests there:

- non-unit normals inside the core, and
- **texels still holding the seed color inside the core**.

That second test is the one that earns its place. Over the whole sheet, "under 92% neutral" was nearly free with 89.6% empty. Inside the core it read **29.55%**, and that number is what revealed that only the fine LOD had been baked and the coarse LOD's quarter of the sheet had never received a ray. After baking both: **9.166%**.

Keep the residual honest rather than hiding it. The leftover neutral is the faces whose ray cannot reach the high-poly (2.30% and 2.67% here), which are deliberately flattened to neutral because a cage cannot invent a surface that is not there. Flatten the **triangle** dilated by a couple of texels, not its bounding box: bounding box + 7 wiped 226,663 texels where triangle + 2 wiped 86,249 for the same faces.

## 7. Calibrate density against what already ships

An earlier audit quoted about 292 px/m as the healthy reference measured on the same mod's wheels. Re-measured on 2026-09-01 by decoding the shipped `.paa`: the wheel `_co` is **1024 x 1024**, with UV density 0.1307 to 0.1438, so the shipped figure is **134 to 147 px/m**. The 292 is that density read against a 2048 texture the asset does not use.

The general form matters more than the number: **derive the floor from shipped and accepted work, and measure both halves** (the UV density from the model and the texture side from the file) so nothing is carried in as a constant.

An earlier floor for this work (755 px/m at 4096) was taken from two previous atlases that each covered a *subset* of the same body. Packing less surface into the same sheet buys density for free, so a whole-body atlas "failed" while being denser than anything the mod ships. A gate calibrated above everything the project ships goes permanently red and stops being read.

When a floor turns out to be miscalibrated, move the axis and harden something else rather than lowering the bar. Here the replacement added **uniformity** (no material below 60% of the body's own median), which a single global floor cannot see: it cannot distinguish a healthy sheet from one with a single starved group, and a starved group is exactly what shows up in game as one blurry part.

## Checklist

1. Freeze the non-UV fingerprint, and calibrate it by mutation, including the legitimate change.
2. Measure `median island area / mean coarse face area`. Below about 1, do not transfer.
3. Choose seams with a probe that reports **collapse**, not just island count.
4. Unwrap each LOD separately; seam the material boundaries first.
5. Normalize density per island, scale the coarse LOD by `sqrt(want/have)`, and pack both as one problem.
6. Prove zero overlap within each LOD *and* between them, exactly.
7. Align the high-poly by searching frames; check the determinant; gate on reach.
8. Bake every LOD; measure the map inside the island cores.
9. Compare density against shipped work, and report what sharing cost.
