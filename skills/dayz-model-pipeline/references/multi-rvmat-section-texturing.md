# Multi material rvmat: texturing one mesh per section (Multi shader)

How to give one mesh region two to four tiling detail textures with the `Multi` shader: the mask, the stage and texGen layout, the two UV sets, the `uvTransform` values, an annotated template and the pitfalls.

The same shader from the material side (when Multi is worth it, painting the mask, the checks before accepting a Multi material) is in `skills/dayz-texture-pipeline/references/multi-rvmat-section-texturing.md`. Read that file for the `.rvmat` work and this one for the model side and the annotated template.

What is checked and what is not: the stage layout, the texGen numbers and the `uvTransform` forms were compared with the 1,960 vanilla `Multi` materials under `P:\DZ\`, and the lines that cite `P:\` were opened; the counts are in `_shared/models/multi-rvmat-texturing.md`. The workflow, the costs, the UV advice and the pitfalls are tool knowledge, not checked on `P:\`.

## When to use which technique

| Technique | Use when | Cost |
|---|---|---|
| One rvmat per named selection (`hiddenSelections`, or a material per face) | Few large sections, or swapping at runtime is needed (an LED on and off, skins) | One draw section per material |
| **Multi shader (this file)** | One mesh region needs 2 to 4 tiling detail textures (walls, large props, terrain like surfaces) at a high texel density | A single material, but about 15 texture fetches and a heavier pixel shader |
| A baked UV atlas | Small items, a budget of one material | Cheapest, lowest fidelity |

The Multi shader is rare on DayZ items for performance reasons: it suits buildings and large statics, not handheld items. Vanilla agrees on where it is used: of its 1,960 `Multi` materials, 1,268 are under the three structures folders and 542 under `P:\DZ\vehicles\`, with the rest on rocks and water structures, and none under `P:\DZ\gear\`. Its strongest feature is specular per section: each masked material gets its own specular response (polished metal, painted metal and rubber differ) instead of one gray plastic specular for everything. A correct roughness and gloss response per section is worth more than decorative emissive effects.

## How it works

A low resolution **mask of red, green, blue and black** (painted on the model's UV layout) selects which of 4 tiling detail texture sets shows where: **black, red, green, blue** map to texGen 0 to 3. Each region is "what is white in a normal alpha mask". Workflow from Blender: paint or generate one ordinary black and white mask per material, then composite them into the R, G and B channels (the fourth material is black, meaning none of the three).

### Stage, texGen and color mapping

| Color | Color (`_co`) stage | Specular stage | Normal (`_nohq`) stage | texGen |
|---|---|---|---|---|
| Black | `Stage0` | `Stage5` | `Stage11` | 0 (5 for the specular stage) |
| Red | `Stage1` | `Stage6` | `Stage12` | 1 (6 for the specular stage) |
| Green | `Stage2` | `Stage7` | `Stage13` | 2 (7 for the specular stage) |
| Blue | `Stage3` | `Stage8` | `Stage14` | 3 |
| Mask, macro, ambient shadow | `Stage4` (mask), `Stage9` (`_mc`), `Stage10` (`_as` or `_ads`) | | | 4 |

Vanilla follows this table: `P:\DZ\structures\residential\houseblocks\data\a1-1_multi1.rvmat` has exactly these fifteen stages with these texGen numbers, including `Stage8` on texGen 3.

- `PixelShaderID = "Multi"; VertexShaderID = "Multi";`
- `Stage4`, the mask, is the red, green, blue and black texture painted on UV set 1. Vanilla names it `_mask.paa`; the file name is free.
- `Stage9`, the macro map, is a color tint over the whole model ("the real texture"; the details overlay it).
- `Stage10` is the `_as.paa` or `_ads.paa` ambient shadow.
- The specular stage of a section can be procedural: `#(argb,8,8,3)color(0.5,G,B,1,DTSMDI)`, where G is the specular intensity and B the glossiness. Tune it per material type instead of sharing one. Vanilla does this in most `Multi` materials (`a1-1_multi1.rvmat` has `#(argb,8,8,3)color(0.5,0,1,1,DTSMDI)` on `Stage8`), and where it uses a file there it is usually a detail specular map, `_dtsmdi.paa`, not an `_smdi.paa`.

## Two UV sets (the part most people miss)

Two UV sets are required:

- **UV set 1** (`uvSource="tex1"`): the original unwrap. It places the mask, the macro map and the ambient shadow (texGen 4). **Never touch it.**
- **UV set 0** (`uvSource="tex"`): a copy of UV set 1, then scaled up heavily. It drives the tiling of the detail textures (texGen 0 to 3). Bigger UVs mean more tiling and more texel density.

The canonical assignment is texGen 0 to 3 on `tex` and texGen 4 on `tex1`. A single section can be given its own UV set (`tex2` and so on) for independent control of tiling; that is not checked on `P:\`, where vanilla uses `tex` and `tex1` only (`_shared/models/multi-rvmat-texturing.md`).

**Export pitfall:** the `.p3d` must actually contain both UV sets. In Blender keep two UV layers and verify after export (with py3d, check the UV set count of each LOD). If UV set 1 is missing, the mask smears across the tiled UVs.

## uvTransform cheat sheet (for any rvmat, not just Multi)

```cpp
class uvTransform
{
    aside[] = {0.5, 0, 0};  // [U scale, shear, 0]
    up[]    = {0, 0.5, 0};  // [shear, V scale, 0]
    dir[]   = {0, 0, 1};    // leave {0,0,1}
    pos[]   = {0, 0, 0};    // [U offset, V offset, 0]: shift the UVs here
};
```

- A scale **below 1 scales the UVs down, so the texture appears bigger** (0.5 makes it twice as large).
- A scale above 1 means more tiling (this skill already uses `{10,0,0}` for detail maps). Vanilla example: `TexGen2` of `a1-1_multi1.rvmat` has `aside[]={2,0,0}` and `up[]={0,2,0}`.
- To nudge a texture into place, start with `pos[]` offsets before rescaling.
- A second form, `dir[]={0,0,0}; pos[]={0,0,1};`, is also in use. Both forms exist in vanilla `Multi` materials: `dir[]={0,0,1}` with `pos[]={0,0,0}` on 12,401 texGen classes and the second form on 1,514 (`a1-1_multi1.rvmat` has both in one file). Use the form above; the second form is not an error.

## Template (annotated)

```cpp
ambient[]  = {0.5,0.75,0.5,1};
diffuse[]  = {1,1,1,1};
forcedDiffuse[] = {0,0,0,0};
emmisive[] = {0,0,0,1};
specular[] = {0.15,0.15,0.15,1};
specularPower = 10;
PixelShaderID = "Multi";
VertexShaderID = "Multi";
// BLACK section
class TexGen0 { uvSource="tex";  class uvTransform { aside[]={1,0,0}; up[]={0,1,0}; dir[]={0,0,1}; pos[]={0,0,0}; }; };
class TexGen5 { uvSource="tex";  class uvTransform { aside[]={1,0,0}; up[]={0,1,0}; dir[]={0,0,1}; pos[]={0,0,0}; }; };
class Stage0  { texture="MyMod\data\black_section_co.paa";   texGen="0"; };
class Stage5  { texture="MyMod\data\black_section_smdi.paa"; texGen="5"; };
class Stage11 { texture="MyMod\data\black_section_nohq.paa"; texGen="0"; };
// RED section (reuses a vanilla DZ texture, which is common)
class TexGen1 { uvSource="tex";  class uvTransform { aside[]={1,0,0}; up[]={0,1,0}; dir[]={0,0,1}; pos[]={0,0,0}; }; };
class TexGen6 { uvSource="tex";  class uvTransform { aside[]={1,0,0}; up[]={0,1,0}; dir[]={0,0,1}; pos[]={0,0,0}; }; };
class Stage1  { texture="DZ\structures\walls\data\wall_stone_moss_co.paa";   texGen="1"; };
class Stage6  { texture="#(argb,8,8,3)color(0.5,0,0.55,1,DTSMDI)";           texGen="6"; };
class Stage12 { texture="DZ\structures\walls\data\wall_stone_moss_nohq.paa"; texGen="1"; };
// GREEN section (unused here: comment out the whole block if there are only 3 materials)
// BLUE section
class TexGen3 { uvSource="tex";  class uvTransform { aside[]={1,0,0}; up[]={0,1,0}; dir[]={0,0,1}; pos[]={0,0,0}; }; };
class Stage3  { texture="#(argb,8,8,3)color(0,0,0,1,co)";              texGen="3"; };
class Stage8  { texture="#(argb,8,8,3)color(0.5,0,0.1,1,DTSMDI)";      texGen="3"; };
class Stage14 { texture="dz\structures\data\concrete\concrete_old_nohq.paa"; texGen="3"; };
// MASK + MC + AS: the placement UV set
class TexGen4 { uvSource="tex1"; class uvTransform { aside[]={1,0,0}; up[]={0,1,0}; dir[]={0,0,1}; pos[]={0,0,0}; }; };
class Stage4  { texture="MyMod\data\mymodel_mask.paa"; texGen="4"; };
class Stage9  { texture="MyMod\data\mymodel_mc.paa";   texGen="4"; };
class Stage10 { texture="MyMod\data\mymodel_as.paa";   texGen="4"; };
```

The template leaves the green section out. Almost every vanilla `Multi` material keeps all fifteen stages and fills an unused section with procedural placeholders (1,955 of 1,960), so when in doubt keep the green stages (`Stage2`, `Stage7`, `Stage13`, with `TexGen2` and `TexGen7`) and give them placeholders, as `_shared/models/multi-rvmat-texturing.md` shows. The three vanilla textures the template names exist under `P:\DZ\structures\`; before using another vanilla texture, check that the file exists.

To apply it in Object Builder or py3d: select the faces, **remove the texture** (the faces get a material only, the texture field stays empty) and assign this rvmat.

## Pitfalls

- A mask painted with gradients or anti-aliasing makes the sections blend; keep hard edges of pure color unless blending is intended.
- A mismatch between stage and texGen is silent: the color and normal stages of a section must share the section's texGen; the specular stage uses its own texGen (5, 6 and 7, and 3 for the blue section, as in the table above) so that its tiling can differ.
- Faces that still carry a texture together with a Multi rvmat give wrong output; the texture must be removed.
- At most 4 sections (black, red, green, blue). For more, split the mesh into several Multi materials or fall back to one rvmat per selection.
- Specular per section: do not ship one gray `specular[]` for everything. The specular stage of each section is where metal, paint and rubber are told apart.
