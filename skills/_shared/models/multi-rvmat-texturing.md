# Multi material texturing

How vanilla textures one mesh with up to four tiling surfaces through a single `Multi` shader material, and what the model has to carry for it: a mask, two UV sets and faces with no texture of their own.

Use it for buildings, walls and large static objects. A handheld item uses one Super material per surface instead (`_shared/textures/rvmat-stages.md`).

## Where vanilla uses it

A scan of the `.rvmat` files under `P:\DZ\` finds 1,960 with `PixelShaderID="Multi"` and `VertexShaderID="Multi"` (for example `P:\DZ\structures\residential\houseblocks\data\a1-1_multi1.rvmat:7`):

| Folder | Files |
|---|---|
| `structures`, `structures_bliss`, `structures_sakhal` | 1,268 |
| `vehicles` | 542 |
| `rocks`, `rocks_bliss`, `rocks_sakhal` | 77 |
| `water`, `water_sakhal` | 73 |

None is under `P:\DZ\gear\`, `P:\DZ\weapons\` or `P:\DZ\characters\`.

## The fifteen stages

1,955 of the 1,960 files have exactly `Stage0` to `Stage14`. The roles below are those of `P:\DZ\structures\residential\houseblocks\data\a1-1_multi1.rvmat`, and the counts say how many of the 1,960 files hold that kind of texture, or a procedural placeholder of that kind, in the stage.

| Stage | Holds | texGen | Vanilla files that agree |
|---|---|---|---|
| `Stage0` to `Stage3` | Color `_co` of surface 1 to 4 | 0, 1, 2, 3 | 1,817 to 1,942 per stage |
| `Stage4` | The mask, `_mask.paa`, that says which surface shows where | 4 | 1,899 |
| `Stage5` to `Stage8` | Detail specular of surface 1 to 4, a `_dtsmdi.paa` file or `#(argb,8,8,3)color(0.5,0,1,1,DTSMDI)` | 5, 6, 7, then 3 for `Stage8` | 1,735 to 1,835 per stage; `Stage8` uses texGen 3 in 1,908 files |
| `Stage9` | Macro color `_mc` over the whole mesh | 4 | 1,669 |
| `Stage10` | Ambient shadow `_as` or `_ads` | 4 | 1,899 |
| `Stage11` to `Stage14` | Normal map `_nohq` of surface 1 to 4 | 0, 1, 2, 3 | 1,919 to 1,958 per stage |

A surface the mesh does not use still has its stages, filled with placeholders: 562 files have a procedural color in `Stage0` and 881 a procedural normal in `Stage14`.

Which color of the mask selects which surface (black, red, green and blue for surfaces 1 to 4) is Bohemia format knowledge that no vanilla text file states; it is described in `_shared/textures/multi-materials.md`, with a skeleton.

The specular stage of a surface can be procedural, `#(argb,8,8,3)color(0.5,G,B,1,DTSMDI)`, where G is the specular intensity and B the glossiness. Give each surface its own values (polished metal, painted metal and rubber differ) rather than one shared gray: a correct specular response per surface is the main gain of the shader. A color or normal stage whose `texGen` does not match its surface's is not reported anywhere; the surface just tiles or lands wrong.

## The texGen classes and the two UV sets

Unlike a Super material, a `Multi` material does not put `uvSource` in each stage. It declares `class TexGen0` to `class TexGen7` at the top, each with a `uvSource` and a `uvTransform`, and each stage names one with `texGen="N"` (`a1-1_multi1.rvmat`). 1,938 of the 1,960 files declare all eight.

- `TexGen4`, the one the mask, the macro map and the ambient shadow use, reads the second UV set, `uvSource="tex1"` (`P:\DZ\structures\residential\houseblocks\data\a1-1_multi1.rvmat:55`), in 1,373 files, and the first, `tex`, in 587.
- `TexGen0` and `TexGen3` read the first UV set, `uvSource="tex"`, in 1,949 and 1,933 files.
- No vanilla `Multi` material names a third UV set.

So a model textured this way usually carries two UV sets: one that tiles the detail textures and one that lays the mask over the whole mesh once. A tiling factor is written in the texGen's `uvTransform`: `TexGen2` of `a1-1_multi1.rvmat` has `aside[]={2,0,0}` and `up[]={0,2,0}`, which repeats that surface twice as often.

- A scale below 1 makes the texture appear bigger (0.5 shows it twice as large); above 1 it tiles more. To move a texture into place, change the `pos[]` offset (U, V) before rescaling. How `aside[]` and `up[]` work in general is in `uv-mapping.md`.
- Vanilla `Multi` materials write the untransformed texGen in two forms: `dir[]={0,0,1}` with `pos[]={0,0,0}` (12,401 texGen classes) and `dir[]={0,0,0}` with `pos[]={0,0,1}` (1,514). `a1-1_multi1.rvmat` has both, the second at `P:\DZ\structures\residential\houseblocks\data\a1-1_multi1.rvmat:16` and `:17`, the first at `:93` and `:94`. Write the first; the second is not an error.

The next two paragraphs are **tool knowledge**, not shown by a vanilla file.

A face that uses a `Multi` material keeps its texture field empty and carries the material only, and the model must be exported with both UV sets or the mask smears across the tiled UVs. After export, read the model with py3d and check the UV set count of each LOD.

A `Multi` material costs about 15 texture fetches and a heavier pixel shader than a Super material, which is why vanilla keeps it off gear. It holds at most four surfaces; for more, split the mesh into several `Multi` materials or use one material per selection. A face that still carries a texture alongside the `Multi` material renders wrong. The mask needs hard edges of pure color: gradients or anti-aliasing blend the surfaces into each other.

## Who does what

- The mask, the UV sets and the faces belong to the model: dayz-object-builder.
- The `.rvmat` and its textures are texture work: dayz-asset-specialist, with `/dayz-pack-texture` for the `.paa` files.
- Copy a vanilla `Multi` material of the same kind of surface and change only the texture paths, as for any other shader.
