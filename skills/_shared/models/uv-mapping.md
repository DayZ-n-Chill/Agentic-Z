# UV mapping

How texture coordinates are stored in a `.p3d`, which UV set each material stage reads, what binarizing does to them, and how to trace an in-game texture fault back to the UVs. For making a new unwrap, use the `uv-clean-atlas` skill; this file is the DayZ side.

What is checked and what is not: the material and config facts cite vanilla files on `P:\`. The file format details are Bohemia format knowledge, the measured numbers were taken on a quad-bike mod and one infected model, and both are marked "not checked on `P:\`" where they appear, because vanilla models are binarized and no vanilla file shows them.

## Contents

- [What to know first](#what-to-know-first)
- [Terms, and why each matters when something looks wrong](#terms-and-why-each-matters-when-something-looks-wrong)
- [Where UVs are stored](#where-uvs-are-stored)
- [V direction between formats](#v-direction-between-formats)
- [Which UV set a material stage reads](#which-uv-set-a-material-stage-reads)
- [What works without good UVs](#what-works-without-good-uvs)
- [Damage and destruct materials read the same UVs](#damage-and-destruct-materials-read-the-same-uvs)
- [Normal maps and UVs](#normal-maps-and-uvs)
- [Baking in Blender for DayZ](#baking-in-blender-for-dayz)
- [Symptom to cause](#symptom-to-cause)
- [Reference numbers](#reference-numbers)
- [Sources outside P:\](#sources-outside-p)

## What to know first

- A UV is a (u, v) pair **per face-vertex**, not per 3D point. The same point can have different UVs on different faces; seams and islands start there.
- UV overlap is fine for **reading** a texture (mirroring, tiling, trim sheets) and fatal for **baking**: a bake of ambient occlusion, color or normals writes two surfaces into the same texels.
- A flat texture (a solid `_co`, procedural glass) looks the same whatever the UVs are, even with garbage UVs or all (0,0). Only per-part detail needs good UVs. The corollary for diagnosis: a flat texture *hides* broken UVs, and the problem surfaces on the day someone adds detail.
- Binarizing quantizes the UVs over the range of the whole LOD, so one face with huge tiling costs precision on every face of that LOD (see "ODOL" below).
- A `_nohq` normal map has green pointing down (the DirectX convention). A bake from Blender has green up and must be flipped (see "Normal maps and UVs").
- Every UV seam duplicates vertices when the model is binarized, because a runtime vertex is a unique combination of point, normal and UV. More seams means more vertices and an earlier "Too many vertices" from Binarize.

## Terms, and why each matters when something looks wrong

| Term | What it is | Why it matters |
|---|---|---|
| Per face-vertex storage | The UV lives on the corner of a face, not on the point | A seam is a point with more than one UV; runtime formats split that vertex |
| Seams and islands | Cuts that let the surface lie flat | Every island edge can bleed at lower mip levels; tiny islands make a bake unreadable |
| Overlap | Several faces over the same UV space | Legitimate for reading; breaks any bake |
| Mirrored islands | Islands whose UV area has a negative sign | Flips the tangent basis, which shows as a lighting seam with a normal map |
| Texel density | Texture pixels per meter of surface | Uneven density gives sharp and blurry parts from the same file |
| Padding and mip bleed | The margin between islands | Without it the mip levels average in texels from outside, and seams appear only at a distance |
| Tiling outside 0 to 1 | Valid, the sampler wraps | It also widens the range the binarizer quantizes |
| Degenerate UVs | An island collapsed to a line or a point | Texture swept along one axis or a single color; breaks the tangent calculation (RPT: "Error while trying to generate ST for points") |
| Several UV sets | Extra channels beside the first | The engine supports them and vanilla materials use the second one (see below) |

## Where UVs are stored

### MLOD, the editable format

MLOD format knowledge, matched by how py3d reads the file; not checked on `P:\`, where every model is binarized (`P:\DZ\gear\camping\barbed_wire.p3d` starts with `ODOL`, version 56).

- Each face-vertex record holds a point index, a normal index and one UV as two 32-bit floats, uncompressed. A new vertex defaults to (0,0). In py3d that is `Vertex.read` in `scripts/tools/py3d/py3d/__init__.py`.
- A face has 3 or 4 vertices and carries its own texture path and material path.
- The LOD also carries `#UVSet#` tags. The format allows up to 8 UV sets per LOD. Set 0 is mandatory and repeats the UVs stored on the faces.
- **Which reader keeps a second set.** The py3d in `scripts/tools/py3d/` keeps every set above 0 through a read and write cycle, as `Vertex.uv_sets` (`LOD._read_uv_set` reads them, `LOD.uv_set_ids` lists them). The py3d package from PyPI (not used in this repo: `/dayz-p3d-audit` and its `requirements.txt` use the repo's copy too) ignores the tag on read and writes only set 0, so a model saved through it loses its second set. A converter from ODOL back to MLOD can also keep the first set only.
- Whatever the reader, a tool that builds the model from one UV layer (an OBJ import, a glTF round trip) produces one set. A model that needs a second set gets it in Object Builder or through `Vertex.uv_sets`.

### ODOL, the binarized format

ODOL format knowledge; not checked on `P:\`.

- Each UV set stores four floats, `UVScale` (min U, min V, max U, max V), followed by compressed pairs.
- Each axis is normalized against the minimum and maximum over the **whole LOD** and stored as a 16-bit integer, about 65,534 steps. So one face with a huge UV value lowers UV precision for the entire LOD.
- Binarize warns about it in the RPT: `UV coordinate on point N is too big UV(153.36, 0.99) - the UV compression may produce inaccurate results`.
- A working limit, derived from the step count and not an official figure: the error stays under half a texel while the total UV range of the LOD is at most about 64 for a 1024 texture, **about 32 for 2048** and about 16 for 4096.
- The open-source packer armake also wraps UVs per vertex and sets tiling flags when UVs leave 0 to 1. Bohemia's Binarize may differ.
- The ODOL header has a count of UV sets. An off-by-3 error in reading that field corrupted a custom parser's output once; check it first when a home-made ODOL reader returns garbage UVs.

An unwrap that keeps everything inside 0 to 1 is safe from all of this. Put tiling in the material (`uvTransform`, below) instead of in the UVs.

## V direction between formats

The most common source of import bugs. Not checked on `P:\`; the py3d rows are read from its code.

| Route | Flip | Where |
|---|---|---|
| OBJ to `.p3d` | `v_p3d = 1 - v_obj` | The assembly script writes `(u, 1.0 - v)` |
| `.p3d` to glTF and back | `1 - v` on export, undone on import | `_recipe_visual_geometry` and `_recipe_build_visual` in `scripts/tools/py3d/py3d/__init__.py`; the 3D viewer relies on it |
| Inside Blender | V = 0 at the bottom (the OpenGL convention) | Blender's OBJ exporter already writes the OBJ convention |

- Every converter must state its convention. Verify with an **asymmetric checker texture**, never with a flat one, which looks the same either way and hides the flip.
- Models taken from another game can carry several UV layers. One other game's model format (`.modelbin`) had five (`TEXCOORD0` to `TEXCOORD4`): `TEXCOORD2` was the 0 to 1 per-part channel (swatches and ambient occlusion) and layers 0, 1 and 4 were tiling channels with values up to about 30. Blender's active layer picked the wrong one. Fetch the layer by name (`bm.loops.layers.uv.get("TEXCOORD2")`).
- When a face is mirrored, its UV corners must be reversed together with its winding.

## Which UV set a material stage reads

Each stage of a `.rvmat` names the coordinates it samples with `uvSource` and can transform them with `class uvTransform`. The stage layout is in `_shared/textures/rvmat-stages.md`; this section adds what matters for unwrapping.

**`uvSource` values in vanilla.** A scan of all 34,899 `.rvmat` files under `P:\DZ` finds four values:

| Value | Uses | Meaning | Example |
|---|---|---|---|
| `tex` | 128,422 | The first UV set | `uvSource="tex"` at `P:\DZ\characters\tops\data\bomberjacket_destruct.rvmat:12` |
| `worldPos` | 50,590 | World position, no UVs involved; terrain and tree materials | `uvSource="WorldPos"` at `P:\DZ\plants\tree\data\b_fagussylvatica_leaves_1f.rvmat:38` |
| `tex1` | 6,278 | The **second** UV set | `uvSource="tex1"` at `P:\DZ\characters\belts\data\civ_belt.rvmat:52` |
| `none` | 3,166 | No coordinates; fresnel and other procedural stages | `uvSource="none"` at `P:\DZ\characters\belts\data\civ_belt.rvmat:76` |

The format also defines `pos`, `norm`, `worldNorm`, `texShoreAnim`, `texCollimator` and `texCollimatorInv`, with `tex` as the default. None of those appears in a vanilla DayZ material, so treat them as untested here.

**The second UV set is ordinary in vanilla Super materials.** Of the 5,841 Super materials (5,838 spelled `Super` and 3 spelled `super`), 1,020 have at least one stage on `tex1`. By stage: `Stage4` (ambient shadow `_as`) 913, `Stage3` (macro `_mc`) 671, `Stage2` (detail) 265, `Stage1` (normal) 44, `Stage5` (specular) 20.

- The usual case is a baked ambient shadow map with no overlap on a model whose color UVs are tiled or mirrored: `civ_belt.rvmat` puts `civ_belt_as.paa` on `tex1` (`:51` to `:52`) and leaves every other texture on `tex`.
- A few models use the second set for everything: `P:\DZ\gear\camping\data\large_tent.rvmat` has `uvSource="tex1"` on stages 1 to 5 (`:12`, `:24`, `:36`, `:48`, `:60`).
- Bohemia's name for this is "use texture coords 2". The Multi shader reads its mask from the second set too (1,960 vanilla Multi materials; 3,251 of their stages use `tex1`).
- A mod model that wants this needs a real second UV set in the `.p3d`. See "Which reader keeps a second set" above before sending such a model through a script.

**`uvTransform` tiles, rotates and offsets.** `aside[]` and `up[]` are the two rows of a 2D matrix, `pos[]` is the offset. The identity is `aside[]={1,0,0}` and `up[]={0,1,0}`. 1,564 vanilla Super materials have at least one stage that is not the identity, most often `Stage2` (972) and `Stage3` (665).

- Plain tiling: the rubber boat's damage material repeats its detail map 5 by 5 with `aside[]={5,0,0}` and `up[]={0,5,0}` (`P:\DZ\vehicles\water\boat_01\data\boat_01_damage.rvmat:27` to `:28`).
- Tiling with a rotation: `aside[]={3,1,0}` and `up[]={-1,3,0}` at `P:\DZ\weapons\pistols\mkii\data\ruger_metal_1.rvmat:39` to `:40`.
- Third-party mod materials do the same, not checked on `P:\`: one tiles its `_dt` 6 by 3 with `aside={6,0,0}` and `up={0,3,0}`, and one vehicle body material uses `aside={16,0,0}` on `Stage2`.
- A stage can name `texGen=N` instead, which points it at a shared coordinate setup. The `Multi` materials work this way (`multi-rvmat-texturing.md`).

For an unwrap this means: keep the islands inside 0 to 1 at one even density, and let the material repeat the detail map. Tiling written into the UVs costs precision at binarize time; tiling written into the material costs nothing.

## What works without good UVs

- A solid color `_co`, procedural glass, and any procedural color texture. Vanilla does this for the bare torso: `hiddenSelectionsTextures[]` at `P:\DZ\characters\tops\config.cpp:41` holds `#(argb,8,8,3)color(0.843137,0.768627,0.658824,1.0,CO)` instead of a file.
- A flat-color material: a `.rvmat` with `diffuse[]` set and no color texture. On a model that is one color per material this is the right answer, and a bake is wasted effort (see "Baking").
- Retexturing through config or script. `hiddenSelectionsTextures[]` and `hiddenSelectionsMaterials[]` swap the texture or material on a named selection without touching UVs, and script does the same with `SetObjectTexture` (`P:\scripts\3_game\entities\entityai.c:2881`) and `SetObjectMaterial` (`:2884`). That is why flat color variants of a model keep working on bad UVs. Measured on a quad-bike mod: its color variants are flat textures on a selection and looked right on an atomized unwrap.

The other side of this: a retexture that has detail must follow the UV layout the model already has.

## Damage and destruct materials read the same UVs

The health-level materials (`_damage.rvmat`, `_destruct.rvmat`; see `_shared/textures/rvmat-stages.md`) sample the model's own UVs. In `P:\DZ\characters\tops\data\bomberjacket_destruct.rvmat` the wear macro on `Stage3` uses `uvSource="tex"` (`:36`) with the identity transform, like the stages around it.

Two consequences:

- Re-unwrapping a vanilla model, or a mod model whose damage materials already exist, moves where the wear lands. A retexture has to keep the UV layout.
- The identity transform is not a rule. Of the 2,057 vanilla Super materials named `_damage` or `_destruct`, 793 tile at least one stage, most often the wear macro on `Stage3` (556 files). `P:\DZ\characters\backpacks\data\attack2backpack_destruct.rvmat` repeats `vests_destruct_mc.paa` twice each way with `aside[]={2,0,0}` (`:39`) and `up[]={0,2,0}` (`:40`). So check the vanilla material you copy from instead of assuming 1 to 1.

## Normal maps and UVs

Not checked on `P:\` by a citation: the channel direction was measured against vanilla textures.

- `_nohq` is the DirectX convention: Y negative, green pointing **down**. A Cycles bake is Y positive, so invert green (`G' = 255 - G`) before converting, every time.
- The `.paa` stores the channels swizzled (how ImageToPAA does it is in `_shared/textures/suffixes-and-sizes.md`; the `.paa` file layout and a writer that needs no DayZ Tools are in `skills/_shared/vehicles/png-to-paa-encoding.md`). To inspect a `_nohq` converted back to PNG, undo the swizzle first.
- Mirrored islands with a `_nohq` give a lighting seam on the mirror axis and relief that looks sunken on the mirrored side. Vanilla vehicles mirror whole sides and accept it. The cost: logos and text cannot go on a mirrored side.
- To verify the green direction, light the model from straight above and look at a feature with **horizontal** relief that exists only in the map. A correlation over the whole frame is noise.
- An overlap score between the UV layout and the texture (IoU) is confounded by mirrored islands and partial coverage: it read 0.28 to 0.81 on layouts that were aligned. The reliable gate is a render, not the number.

## Baking in Blender for DayZ

A recipe that worked on two mod models (a quad bike and an infected character). Not checked on `P:\`.

- **Retopology invalidates the UVs that came before it.** Any retopology (QuadriFlow, Voxel Remesh, Quad Remesher, Tencent's topology model, any AI retopology service) throws away the UVs of the source mesh. The order is fixed: generate, retopologize, **unwrap again**, finish the UVs, bake, then build the LODs. Never bake against UVs from before the retopology; the maps come out badly projected. A high-to-low texture bake (the `bake-texture` step of an AI 3D toolchain) therefore stops being optional in any chain that retopologizes.
- A hard edge (a smoothing split) almost always needs a UV seam in the same place. A seam without a hard edge is fine. A hard edge without a seam is the most common cause of visible seams in a normal bake.
- **Unwrap by sections, not by loose parts.** Lay the atlas out by logical sections of the model (tank, chassis, seat, mudguards), ideally matching the named selections and materials, each section with contiguous islands a person can recognize. An automatic unwrap by loose parts or faces (Smart UV Project with no manual seams) atomizes the model into thousands of anonymous islands that nobody can paint or debug: one quad-bike body had a median of 2 to 4 faces per island. Smart UV Project is fine for the ambient occlusion and normal bake of an organic mesh that is already in sections; it is not an authoring unwrap for a vehicle made of many parts.
- Unwrap settings that worked on the infected model: seams in hidden areas, Smart UV Project with margin 0.003, then `pack_islands(rotate=True, margin=0.008)`. Result: 96.8% of the bounding box filled, stretch from 0.82 to 1.13 between the 10th and 90th percentile.
- Normal bake, high to low: selected to active, Cycles, extrusion and ray distance set from the gap between the meshes, a margin of 8 px or more, a Non-Color image. **Fill the image with neutral (128,128,255) first and bake with `use_clear=False`**, so a ray that misses leaves neutral instead of black or an inverted normal.
- If the low mesh was posed again after retopology, bake against a proxy mesh that has the final low mesh's topology and UVs at its positions from before the pose change. Tangent space does not depend on the pose.
- Ambient occlusion: hide the high mesh and everything except the low one, so it occludes only itself. The mean value went from 64 to 202 when this was done.
- A model that is one color per material and has no real texture: do not bake an atlas. Use a flat-color `.rvmat` per material with `diffuse[]` and no color texture.
- Padding for an atlas: 16 px at 2048, and a gutter of at least twice that between islands.

## Symptom to cause

"Audit" below means measuring the listed number on the MLOD; the method is in `uv-clean-atlas/references/mlod-uv-audit.md`. "OB" is Object Builder.

| What you see in game | Likely cause | How to confirm | Fix |
|---|---|---|---|
| A face in one flat color | Missing UVs, UVs at (0,0), or a collapsed island | Audit: share of zero UVs; OB: Structure, Check Faces | Map the faces; OB's neighbor mapping for loose faces |
| The wrong texture repeated on different parts; ambient shadow with doubled spots | A bake over overlapping UVs | Audit: overlap per group and between groups | Unwrap again without overlap for the bake, or put the `_as` on a second UV set with `uvSource="tex1"` |
| A lighting seam on the center axis; detail sunken on one side | Mirrored islands with a `_nohq` | Audit: mirrored share (negative UV area) | Offset the mirrored half; bake again with the engine's tangent basis |
| Sharp in Object Builder, distorted or shimmering after binarizing | 16-bit quantization over a huge UV range in the LOD | RPT: "UV coordinate on point N is too big"; audit: bounds | Bring the tiling back near 0; move tiling into the material's `uvTransform`; split materials |
| Texture swept or stretched along one axis | Degenerate UVs (a planar map from a bad view, a broken import) | Audit: degenerate share; RPT: "generate ST for points" | Unwrap the affected faces again |
| Blurry although the texture is large | Low or uneven texel density | Audit: px/m; a checker grid in game | Scale the islands to one density |
| Seams that only show at a distance | Mip bleed from too little padding | Look at the `.paa` mip levels and the island padding | More edge padding; an atlas background close to the island colors |
| A bake that comes out black, with holes or circles | Tiny islands on a black background, plus UV drift | Audit: islands (median faces per island) and density | Flat-color material if the model is one color; otherwise unwrap with larger islands |
| "Too many vertices" from Binarize | Too many UV and normal splits | Count the seams | Share normals and UVs where possible; fewer islands |
| Correct offline, wrong in game | The V direction was lost in a converter | Run an asymmetric checker through the whole pipeline | Add or remove `1 - v` at the step that lost it |
| Nobody can tell which island is which part; the wrong part gets painted or baked | An automatic unwrap by loose parts or faces instead of by sections | Audit: a median of 2 to 4 faces per island; open the atlas and try to read it | Unwrap **by sections**, with seams marked by hand |

## Reference numbers

Not checked on `P:\`. Vanilla texture sizes per folder are in `_shared/textures/suffixes-and-sizes.md`.

| Metric | Value | Basis |
|---|---|---|
| Edge padding | 8 px at 1024, 16 px at 2048; gutter at least twice that | Common game-art practice |
| Texel density, props | about 512 px/m | Common game-art practice |
| Texel density, first-person weapons | about 1024 px/m or more | Common game-art practice |
| A density that shipped and was accepted | The wheels of a quad-bike mod, 134 to 147 px/m (a 1024 `_co`, UV density 0.1307 to 0.1438) | Measured by decoding the shipped `.paa` |
| Largest UV range per LOD before binarizing costs half a texel | about 32 for a 2048 texture | Derived from the 16-bit step count and the RPT warning |
| Acceptable stretch in Blender | 10th to 90th percentile within 0.8 to 1.2 | Measured on the infected model |
| Smart UV Project and pack | margin 0.003, pack margin 0.008, `rotate=True` | Measured on the infected model |

The wheel density was first written down as about 292 px/m. That was the same UV density read against a 2048 texture the wheels do not use. When you derive a floor from shipped work, measure both halves: the density from the model and the texture size from the file.
