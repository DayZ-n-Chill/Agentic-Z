# Multi materials

When the Multi shader is worth it, which mask color picks which material, a starting block to adapt, how to paint the mask, and what to check before you accept a Multi material.

The stage roles, the `TexGen` classes, the two UV sets, how many vanilla files follow each, and what the model has to carry are in `_shared/models/multi-rvmat-texturing.md`; this file does not repeat them. Blocks with `MyMod` paths are shapes to adapt.

## When Multi is worth it

Use Multi only when it beats one material per selection. For most items one `.rvmat` per selection is simpler, easier to debug and closer to how vanilla gear is made. Multi suits large statics and rock or building surfaces that blend several tiled material sets through a mask while keeping the section count low.

| Technique | Best for | Cost |
|---|---|---|
| One `.rvmat` per selection | Items, weapons, small props, clean material islands | More sections and draw calls, but simple |
| Multi | Large statics with tiled material families and a mask | A fixed stage layout, a mask and two UV sets |
| One baked atlas | Simple props with one baked material | No tiling per material and one `_smdi` for everything |

Read a vanilla Multi material before writing your own, such as the rock that sets `PixelShaderID="Multi"` at `P:\DZ\rocks\data\rock_apart1\rock_apart1.rvmat:7`.

## What the mask picks

The mask chooses between four material families (**tool knowledge**: no vanilla text file states the mapping):

| Mask color | Family | Color, specular and normal stages |
|---|---|---|
| Black | Base | Stage0, Stage5, Stage11 |
| Red | Red | Stage1, Stage6, Stage12 |
| Green | Green | Stage2, Stage7, Stage13 |
| Blue | Blue | Stage3, Stage8, Stage14 |

Each family has its own color, specular and normal textures. That is the gain over a baked atlas: highlight and relief can differ under each part of the mask.

What the vanilla rock shows:

- The mask is `rock_apart1_mask.paa` in `Stage4` with `texGen="4"` (`P:\DZ\rocks\data\rock_apart1\rock_apart1.rvmat:117` to `:120`), and `TexGen4` reads `uvSource="tex1"` (`:53` to `:55`).
- The specular slot holds the placeholder `color(0.5,0,1,1,DTSMDI)` (`:122` to `:125`). Vanilla tags this slot `DTSMDI`, the detail and specular form, not plain `SMDI`.
- `Stage10` holds the baked `_as` with `texGen="4"`, so it also reads the second UV set (`:147` to `:150`).
- The rock declares `TexGen0` to `TexGen7` and shifts some with `pos[]`, so one tiled texture can sit at a different offset per family.
- `P:\DZ\rocks_bliss\data\r_rock_general1.rvmat` swaps the UV sets: `TexGen4` reads `uvSource="tex"` (line 55) and the tiling `TexGen` classes read `tex1`, tiled 13 times. Pick one assignment and make the model's UV sets match it. When the mask's set is missing, mirrored, overlapping or scaled like the tiling set, the mask lands in the wrong place.

## Starting block

A shape to adapt, not a finished material. `rvmat_template.py multi` (`rvmat-cookbook.md`) prints it with `TexGen1` to `TexGen3` written out in full. Replace every path and test it with a real mask and both UV sets. Vanilla also gives the specular stages their own `TexGen5` to `TexGen7`; copy those from a vanilla Multi file when the specular detail needs its own tiling.

```cpp
PixelShaderID="Multi";
VertexShaderID="Multi";

class TexGen0
{
	uvSource="tex";
	class uvTransform { aside[]={1,0,0}; up[]={0,1,0}; dir[]={0,0,1}; pos[]={0,0,0}; };
};
class TexGen1: TexGen0 {};
class TexGen2: TexGen0 {};
class TexGen3: TexGen0 {};
class TexGen4
{
	uvSource="tex1";
	class uvTransform { aside[]={1,0,0}; up[]={0,1,0}; dir[]={0,0,1}; pos[]={0,0,0}; };
};

class Stage0 { texture="MyMod\data\black_co.paa"; texGen="0"; };
class Stage1 { texture="MyMod\data\red_co.paa"; texGen="1"; };
class Stage2 { texture="MyMod\data\green_co.paa"; texGen="2"; };
class Stage3 { texture="MyMod\data\blue_co.paa"; texGen="3"; };
class Stage4 { texture="MyMod\data\asset_mask.paa"; texGen="4"; };

class Stage5 { texture="MyMod\data\black_smdi.paa"; texGen="0"; };
class Stage6 { texture="MyMod\data\red_smdi.paa"; texGen="1"; };
class Stage7 { texture="MyMod\data\green_smdi.paa"; texGen="2"; };
class Stage8 { texture="MyMod\data\blue_smdi.paa"; texGen="3"; };

class Stage9 { texture="#(argb,8,8,3)color(0,0,0,0,MC)"; texGen="4"; };
class Stage10 { texture="#(argb,8,8,3)color(1,1,1,1,AS)"; texGen="4"; };

class Stage11 { texture="MyMod\data\black_nohq.paa"; texGen="0"; };
class Stage12 { texture="MyMod\data\red_nohq.paa"; texGen="1"; };
class Stage13 { texture="MyMod\data\green_nohq.paa"; texGen="2"; };
class Stage14 { texture="MyMod\data\blue_nohq.paa"; texGen="3"; };
```

The macro in `Stage9` and the ambient shadow in `Stage10` read `TexGen4`, the mask's UV set, as the rock's do (`P:\DZ\rocks\data\rock_apart1\rock_apart1.rvmat:142` to `:150`), so they cover the mesh once instead of tiling.

## Painting the mask

- Paint pure black, red, green and blue for a hard split.
- Use blends only after you have seen the result in the engine.
- Paint the mask over the UV set its `TexGen` reads.
- Ship the mask as a `.paa` at its packed path; the working file can be a PNG or a layered file, but the `.rvmat` names the `.paa`. Call it `<name>_mask` like the rock's; `/dayz-pack-texture` accepts the `_mask` suffix.

## Common mistakes

- Multi on a small item that selections would handle more simply.
- No second UV set, or the mask reading the same UV set as the tiling textures.
- Only color textures supplied, which throws away the per family specular and normal that are the point of Multi.
- A source `.png` or `.tga` path left in the `.rvmat`.

## Before accepting a Multi material

1. `PixelShaderID` and `VertexShaderID` are both `Multi`.
2. Stage4 names the mask and reads, through its `TexGen`, the UV set that lays the mask over the mesh once: usually `tex1`, or `tex` when the tiling textures read `tex1`.
3. Stage0 to Stage3, Stage5 to Stage8 and Stage11 to Stage14 are present, or left out on purpose with the reason written down.
4. The mask colors land on the intended families in the engine.
5. The asset really gains from fewer sections or from tiled materials per family.

`rvmat_lint.py` checks the first three: a missing Stage0 to Stage4 is an error, and a mask not on `tex1` or a missing later stage is a warning.
