# Re-unwrapping a shipped model with a LOD chain

How to change only the UVs of a model that already ships: proving the change is UV only, why a LOD transfer fails, the shared sheet layout that replaces it, and how to align the high poly and judge the bake. Read it when the request is "re-unwrap the shipped model", "change UVs only" or "make both LODs share a texture", or when an atlas has to serve more than one visual LOD.

`tools-uv-atlas.md` treats the input as raw material. Here the model already ships: its selections carry memory points, damage zones and proxy mounts, its material assignment is wired into `config.cpp`, and the only thing you may move is UV. The numbers were measured on the body of a quad bike mod: two visual LODs of 38,831 and 15,422 faces, 16 materials, 4 wheel proxies and 29 selections per LOD. None of it is checked on `P:\`.

## Make "UV only" a measurement

Before touching anything, record a fingerprint of everything that is not UV and compare against it afterwards. Hash the whole model with `Vertex.uv` as the one field left out, rather than listing what must survive.

Per LOD, hash the point coordinates, the face to point topology, the `(texture, material)` pair of every face, and the selection names. In MLOD the UV lives per face vertex, so a real unwrap moves no point, and any difference in those four hashes means the change is no longer UV only.

Test the fingerprint by mutation before trusting it:

| Mutation | Expected | What it moves |
|---|---|---|
| Untouched file | Passes | Nothing |
| One UV moved by 0.25 | Passes | Nothing |
| One point moved by 1 mm | Fails | Only `points` |
| One selection renamed | Fails | Only `selections` |

The second row is the one that matters and the one usually skipped. A check that also rejects the legitimate change is broken, and you only see that if you test the good case too.

## You cannot transfer a fragmented layout onto a decimated LOD

Three transfers, three different failures, all on the same pair of LODs:

| Method | Result on LOD1 |
|---|---|
| Nearest neighbour per corner, biased 12 % toward the face centre | Occupancy 25.114 %, one face taking 41 % of the atlas |
| Pinned island per face, fallback affine map | Correct density (ratio LOD1/LOD0 = 0.97) and 8,409 overlapping pairs, 349,089 texels |
| Per island projection with the point clipped to the triangle | 4,647 pairs, 329,542 texels, and 167 squashed faces |

The second row shows why density alone proves nothing: it was right and the sheet was still ruined. A per face affine map is right locally and inconsistent globally, so neighbouring faces overlap.

The cause is arithmetic. The LOD0 islands had a median of 2 faces. LOD0 carries 38,831 faces over 10.76 m² and LOD1 15,422 faces over 10.53 m², so the mean LOD1 face is 2.5 times the area of a LOD0 face. One coarse face spans several islands at once: clamp it into one and it squashes, spread it across several and its neighbours pile up.

Before any LOD transfer, measure `median island area / mean coarse face area`. Below about 1 the transfer cannot work.

## You cannot fix it by cutting fewer seams

Making the islands bigger fails on this mesh. Unwrap only (no fold loop, no packing), with the collapse share beside the island count:

| Seam strategy | Seams | Islands | Median faces | Largest | NaN | Collapsed |
|---|---:|---:|---:|---:|---:|---:|
| `smart_project` 80 degrees | 49 | 8,515 | 2 | 389 | 0 | 0.0 % |
| Material boundaries plus edges sharper than 60 degrees | 15,401 | 5,188 | 2 | 1,579 | 0 | 15.3 % |
| Material boundaries plus edges sharper than 40 degrees | 21,669 | 8,577 | 2 | 819 | 0 | 0.1 % |
| Material boundaries plus edges sharper than 25 degrees | 28,433 | 13,442 | 2 | 620 | 0 | 0.0 % |
| Material boundaries only | 49 | 695 | 19 | 1,594 | 0 | 100.0 % |

The floor is 495 connected shells, so 695 islands is nearly ideal, and it flattens the whole mesh. The only seam family that survives is the projection, which is the one that fragments. The middle thresholds are worse than both ends: more seams and collapse.

A few large islands need a mesh you may retopologize. A shipped hard surface body with hundreds of small welded shells does not give that choice.

A probe that compares seam strategies must report collapse. One that measured only island count and NaN chose the material boundary strategy. Run through the whole recipe (fold loop and packing), that strategy reported 1,308 px/m and 76 % occupancy, better than the correct run, because every counter filters `abs(area) > 1e-14` first; only the exact SAT check over the unfiltered triangles found that 30,032 of 38,832 triangles (77 %) were still collapsed. This is the rule from `tools-uv-atlas.md`, section "Collapsed faces hide from the overlap check", applied to the probes you write yourself. Put collapsed over total in every comparison table, including throwaway ones.

## The layout that works: one sheet, separate regions

Neither LOD carries the other's layout. Unwrap each on its own with the projection recipe, scale the coarse LOD to its share, and pack both together as one packing problem into a single sheet.

One texture still serves both. Paint once on the fine LOD's region, and fill the coarse LOD's region at bake time by baking it from the same high poly. A bake works per texel, so it never meets the granularity problem.

Setting the share: after per island density normalization each island's UV area equals its 3D area, so the two LODs arrive at roughly 1:1. The packer scales everything uniformly, so the ratio going in is the ratio coming out. Scale the coarse LOD by `sqrt(want / have)` before packing and the split lands exactly.

Result at a 75/25 split, a 4096 sheet and a 4 texel pack margin:

| | LOD0 | LOD1 |
|---|---:|---:|
| Faces | 38,831 | 15,422 |
| Islands after the fold loop | 8,708 | 6,287 |
| Fold loop rounds | 4 | 2 |
| Collapsed | 0.00 % | 0.00 % |
| Exact SAT overlap | 0 pairs | 0 pairs |
| Sheet share | 75.0 % | 25.0 % |
| Density | 349 px/m | 204 px/m |

Overlapping pairs between the two LODs: 0. Every island holds one material, which comes free when you seam the material boundaries before unwrapping (49 edges on this mesh). An island with two materials cannot be painted and breaks any per material check.

Sharing has a cost. Packing both LODs dropped the fine LOD from 528 px/m (alone, 17.9 % occupancy) to 349 px/m (shared, 10.4 % total). Most of that is the gutter: about 15,000 islands of roughly 19 texels a side, each paying a 4 texel margin, is a 42 % linear inflation per island. The options:

- Fewer islands: not available on this mesh (previous section).
- A smaller pack margin: about +18 % at 2 texels, but it voids any bleed test made against the bake's own margin, so measure again.
- A bigger sheet: double the density at 8192, for four times the texture memory.

Report the number and let the owner choose. 349 px/m was 2.6 times the shipped reference, so it was accepted.

## Aligning the high poly: search the frame, never assume it

A high to low bake fires rays from the low surface and records the high one. If the two are not in the same place the map records detail from the wrong spot, and no offline check shows it; in game the relief does not match the silhouette.

On this model the high poly rip (the model taken from another game) was judged unusable at p95 = 6.1 mm, a figure taken against a different OBJ with no frame search. Trying all 48 axis permutations with sign flips, each re-centred on the bounding box, gave:

```text
(-x,  z,  y)   p50=  0.47 mm   p95=   1.82 mm   outside cage   2.0%   best
( x,  z,  y)   p50=  1.14 mm   p95=  21.35 mm   outside cage   9.0%
identity       p50=163.71 mm   p95= 438.62 mm   outside cage  93.6%
( x,  z, -y)   p50=829.14 mm   p95=1210.97 mm   outside cage 100.0%
```

- Sorted bounding box sizes identify the object first. `[0.8848, 0.9478, 1.8736]` against `[0.8848, 0.9463, 1.8732]` says "same object, same scale, axes permuted", and that the search is worth running.
- Re-centre each candidate on the bounding box centre before scoring it. A correct permutation scores badly under a pure origin offset and gets thrown out; this model needed a 144 mm shift on one axis.
- Check the determinant of the 3x3. +1 means a rotation, and the baked normals keep their handedness. −1 means the alignment mirrors, and the map will be wrong in a way that is easy to miss.
- Move the low mesh into the high poly's space, not the other way round. A rigid transform leaves tangent space normals untouched, and moving one object beats re-parenting eleven.

Judge the alignment by reach, not by deviation. The coarse LOD is meant to deviate from the high poly, since capturing that is what the bake is for, so a limit of `p95 < cage/4` wrongly threw it out at 5.22 mm. What separates good from bad is the share of the low mesh beyond the ray's reach: 1.9 % and 2.1 % for the two aligned LODs, 93.6 % and 95.6 % for the wrong frames, with p50 two orders of magnitude apart (1.7 mm against 164 mm). Fail on more than 10 % beyond the cage or p50 above the cage distance, and report p50 and p95 without failing on them.

## Measure the map where it is sampled

The bake's own check rejected a good map at 2.433 % non unit normals against a 1 % limit. 99.08 % of those texels were in the packing gutter; of the texels a triangle actually covers, only 0.0976 % were short. The gutter share follows the island count, not the bake quality (this sheet is 89.6 % empty), so a whole sheet limit measures fragmentation and calls it a defect.

Rasterize the UV coverage, erode it by one texel to get the core (texels whose whole 3x3 neighbourhood is covered), and run both tests there:

- non unit normals inside the core, and
- texels still holding the fill colour inside the core.

The second test earns its place. Over the whole sheet a "less than 92 % neutral" check passed almost by default with 89.6 % empty; inside the core it read 29.55 %, which showed that only the fine LOD had been baked and the coarse LOD's quarter had never received a ray. With both baked it read 9.166 %.

The leftover neutral is the faces whose ray cannot reach the high poly (2.30 % and 2.67 % here), flattened to neutral on purpose because a cage cannot invent a surface that is not there. Flatten the triangle grown by a couple of texels, not its bounding box: bounding box plus 7 wiped 226,663 texels where triangle plus 2 wiped 86,249 for the same faces.

## Take the density floor from shipped work

The mod's wheels are the shipped reference: their `_co` decodes at 1024 x 1024 with UV density 0.1307 to 0.1438, so 134 to 147 px/m in game. Read against a 2048 texture the asset does not use, the same density gives about 292 px/m, which is wrong.

Take the floor from shipped and accepted work, and measure both halves (the UV density from the model and the texture side from the file), so nothing enters as a constant.

A floor taken from atlases that each covered only part of the body (755 px/m at 4096) is too high: packing less surface into the same sheet buys density for free, so a whole body atlas fails while being denser than anything the mod ships. A limit set above everything the project ships stays red and stops being read.

When a floor is set wrong, check something else rather than only lowering the bar. Here the replacement added uniformity: no material below 60 % of the body's own median. A single global floor cannot tell a healthy sheet from one with a single starved group, and a starved group is what shows in game as one blurry part.

## Checklist

1. Record the non UV fingerprint, and test it by mutation, including the legitimate change.
2. Measure `median island area / mean coarse face area`. Below about 1, do not transfer.
3. Choose seams with a probe that reports collapse, not just island count.
4. Unwrap each LOD separately; seam the material boundaries first.
5. Normalize density per island, scale the coarse LOD by `sqrt(want/have)`, and pack both as one problem.
6. Prove zero overlap within each LOD and between them, exactly.
7. Align the high poly by searching frames; check the determinant; judge by reach.
8. Bake every LOD; measure the map inside the island cores.
9. Compare density with shipped work, and report what sharing cost.
