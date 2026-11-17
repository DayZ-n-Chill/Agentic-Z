# Auditing the UVs of an assembled MLOD `.p3d`

What to measure on a `.p3d` that is already assembled (LODs, selections, proxies, materials), the traps in measuring it, and one fully measured case. Use it when the question is "are this model's UVs good enough for a detailed texture?" rather than "unwrap this mesh". The Blender-side audit of a single mesh is `sat_gate.py` and `uv_metrics.py` (see `SKILL.md`).

The source project measured all of this with its own py3d script, `uv_audit.py`, which is not shipped in this repo. The list below is what that script computed, so the same numbers can be reproduced with py3d (`_shared/py3d-mlod-notes.md` covers reading an MLOD). The measurements are from LFQuad (the source author's quad-bike mod) and were not checked on `P:\`.

## What to measure

Per visual LOD and per group of faces sharing a texture and material:

| Metric | How | Reads as |
|---|---|---|
| Zero UVs | Share of face-vertices at exactly (0,0) | Unmapped faces: one flat color in game |
| NaN | Any non-finite UV | A failed unwrap; filter nothing before counting |
| Bounds | Min and max of U and V | Tiling outside 0 to 1, and the range the binarizer quantizes (`_shared/models/uv-mapping.md`) |
| Degenerate | Triangles with zero UV area | Texture swept along one axis; also faces an unwrap collapsed |
| Mirrored | Share of triangles with negative signed UV area | A lighting seam with a normal map |
| Overlap | Monte Carlo sampling with an index grid | Fine for reading a tiled or mirrored texture, fatal for a bake |
| Islands | Union-find over shared UVs; report the count and the median faces per island | A median of 2 to 4 faces means the atlas is atomized |
| Texel density | `sqrt(uv area / 3D area)`, as px/m at the texture's real size | Blurry or uneven parts |
| Overlap between groups | The same sampling at LOD level | Two materials baked into the same texels |

## Traps in the measurement

- A classic raster overlap check **fails on islands smaller than a texel**: a triangle under one texel covers no sample center. That is why the overlap estimate is Monte Carlo with an index grid.
- **Leave proxy faces out.** Faces in a `proxy:...` selection carry degenerate UVs by design.
- **Leave "full-frame" triangles out of the overlap between groups.** A single face mapped to the whole 0 to 1 square (a headlight lens, for example) overlaps everything and reports a false 100%. The threshold used was a UV area above 0.2.
- Numbers that are exactly 100% or exactly 0.000 are a sign of a tool artifact, not of the model.
- **A mirrored share that is neither 0 nor 100 may be collapse, not mixed handedness.** The source script left degenerate triangles out of the mirrored count but kept them in the total, so a uniformly mirrored mesh with 31% of its faces collapsed reported 69% mirrored. Before calling it a chirality defect, check whether the non-degenerate count and the mirrored count are the same integer. On three LFQuad groups they matched exactly.
- Read density against the size of the texture the asset really uses. Decode the shipped `.paa` and take its side; do not assume 2048 (see the wheel figures below).

## The measured case: LFQuad, July 2026

Measured 2026-07-05 on the deployed `.p3d` files.

**Wheels, the healthy reference** (they work in game with a real `_co`): zero UVs 0%, bounds 0.01 to 0.99, overlap 0.2 to 0.4%, mirrored 0.6% or less. Density was first reported as a median of about 292 px/m, read against a 2048 texture. Re-measured on 2026-09-01 by decoding the shipped `.paa`, the wheel `_co` is 1024 x 1024 with UV density 0.1307 to 0.1438, which is **134 to 147 px/m** in game. Use the corrected figure.

**Body.** The UVs from a Smart UV Project run in May 2026 *did* reach the `.p3d`: 0% zero UVs, no NaN, bounds 0 to 1. "Imported without UVs" really meant "without a texture that uses them". The real problems:

- **Fragmentation.** The group `b_black_1` had 1,859 islands over 9,732 faces (median 4); `b_metal_2` had 2,154 islands (median 2).
- **Density.** A median of about 27 px/m at 2048, ten times worse than the wheels on the same reading. A 10 cm part is about 2.7 px, which is the measured cause of the bake artifacts on that body (black holes and circles).
- **Overlap.** 0 to 2% per group, with a peak of **18.7%** on `b_white` (the `color` selection), and 4.4% between groups.
- The headlight face (`b_lights_fc_nolight`) maps to the full 0 to 1 square.

**Two UV lineages, neither usable for a detailed texture.** An "87.5% overlap" figure from earlier research was not from the deployed `.p3d`. It was resolved on 2026-07-06: it belongs to the model's *original* authored UVs in the source FBX (white bodywork 88.3% Monte Carlo overlap, other groups 57 to 88%). The originals have good density (349 to 1,900 px/m at 2048) but massive overlap, because instanced parts are stacked on each other. They are unusable for a bake and usable for tiling or flat color. The Smart UV Project layout in the `.p3d` is the opposite: unique, atomized, and 27 px/m.

**Consequence.** A detailed texture on that body needs a new unwrap and a new bake. The existing color variants keep working through it, because they are flat colors applied by `hiddenSelectionsTextures[]` and do not depend on the UVs.
