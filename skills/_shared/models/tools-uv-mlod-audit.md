# UV audit of an assembled model

What to measure on the UVs of a `.p3d` that is already assembled (LODs, selections, proxies, materials), the traps in measuring it, and one measured case. Use it when the question is "are this model's UVs good enough for a detailed texture?" rather than "unwrap this mesh". The Blender side audit of a single mesh is `sat_gate.py` and `uv_metrics.py` (`tools-uv-atlas.md`, "Auditing an existing UV set").

No script in `/dayz-model-tools` computes these metrics; compute them with py3d (`_shared/py3d-mlod-notes.md` covers reading an MLOD). The numbers come from a quad bike mod and are not checked on `P:\`.

## What to measure

Per visual LOD, and per group of faces that share a texture and material:

| Metric | How | Reads as |
|---|---|---|
| Zero UVs | Share of face vertices at exactly (0,0) | Unmapped faces: one flat colour in game |
| NaN | Any non finite UV | A failed unwrap; filter nothing before counting |
| Bounds | Min and max of U and V | Tiling outside 0 to 1, and the range the binarizer quantizes (`uv-mapping.md`) |
| Degenerate | Triangles with zero UV area | Texture swept along one axis; also faces an unwrap collapsed |
| Mirrored | Share of triangles with negative signed UV area | A lighting seam with a normal map |
| Overlap | Monte Carlo sampling with an index grid | Fine for reading a tiled or mirrored texture, fatal for a bake |
| Islands | Union find over shared UVs; report the count and the median faces per island | A median of 2 to 4 faces means the atlas is in crumbs |
| Texel density | `sqrt(uv area / 3D area)`, as px/m at the texture's real size | Blurry or uneven parts |
| Overlap between groups | The same sampling at LOD level | Two materials baked into the same texels |

## Traps in the measurement

- A raster overlap check misses islands smaller than a texel, because a triangle under one texel covers no sample centre. That is why the overlap estimate is Monte Carlo with an index grid.
- Leave proxy faces out. Faces in a `proxy:...` selection carry degenerate UVs by design.
- Leave full frame triangles out of the overlap between groups. A single face mapped to the whole 0 to 1 square (a headlight lens, for example) overlaps everything and reports a false 100 %. The cut off used was a UV area above 0.2.
- Numbers that are exactly 100 % or exactly 0.000 point at a tool fault, not at the model.
- A mirrored share that is neither 0 nor 100 may be collapse, not mixed handedness. A script that leaves degenerate triangles out of the mirrored count but keeps them in the total reports a uniformly mirrored mesh with 31 % of its faces collapsed as 69 % mirrored. Before calling it a handedness defect, check whether the non degenerate count and the mirrored count are the same integer; on three quad bike groups they matched exactly.
- Read density against the size of the texture the asset really uses. Decode the shipped `.paa` and take its side; never assume 2048.

## A measured case: the quad bike

Measured on the deployed `.p3d` files.

Wheels, the healthy reference (they work in game with a real `_co`): zero UVs 0 %, bounds 0.01 to 0.99, overlap 0.2 to 0.4 %, mirrored 0.6 % or less. The wheel `_co` decodes at 1024 x 1024 and the UV density is 0.1307 to 0.1438, so the in game density is 134 to 147 px/m.

Body. The UVs from a Smart UV Project run did reach the `.p3d`: 0 % zero UVs, no NaN, bounds 0 to 1. "Imported without UVs" really meant "without a texture that uses them". The real problems:

- Fragmentation. The group `b_black_1` had 1,859 islands over 9,732 faces (median 4); `b_metal_2` had 2,154 islands (median 2).
- Density. A median of about 27 px/m at 2048, ten times worse than the wheels read the same way. A 10 cm part gets about 2.7 px, which is what causes the bake artifacts on that body (black holes and circles).
- Overlap. 0 to 2 % per group, with a peak of 18.7 % on `b_white` (the `color` selection), and 4.4 % between groups.
- The headlight face (`b_lights_fc_nolight`) maps to the full 0 to 1 square.

The model has two UV sets of different origin, and neither works for a detailed texture. The original authored UVs in the source FBX have good density (349 to 1,900 px/m at 2048) but heavy overlap, because instanced parts are stacked on each other (white bodywork 88.3 % Monte Carlo overlap, other groups 57 to 88 %); they suit tiling or flat colour, not a bake. The Smart UV Project layout in the `.p3d` is the opposite: unique, in crumbs, and 27 px/m.

A detailed texture on that body therefore needs a new unwrap and a new bake. The existing colour variants keep working, because they are flat colours applied through `hiddenSelectionsTextures[]` and do not depend on the UVs.
