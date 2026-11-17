# Multi shader: several tiled materials under one mask

When to use the Multi shader, its stage layout, the two UV sets it needs, how to paint the mask, and the checks before accepting a Multi material.

The model side of the same shader (the two UV sets on the mesh, faces without a texture, an annotated template) is in `skills/dayz-model-pipeline/references/multi-rvmat-section-texturing.md`, and the vanilla counts are in `skills/_shared/models/multi-rvmat-texturing.md`.

How to read it: a `P:\` citation was checked on the vanilla files. The skeleton with `MyMod` paths is a shape to adapt.

## When Multi is worth it

Use Multi only when it beats one material per selection. For most items, one `.rvmat` per selection is simpler, easier to debug and closer to how vanilla gear is made. Multi suits large statics and rock or building surfaces that need several tiled material sets blended through a mask while the section count stays low.

| Technique | Best for | Tradeoff |
|---|---|---|
| One `.rvmat` per selection | Items, weapons, small props, clean material islands | More sections and draw calls, but simple |
| Multi shader | Large statics with tiled material families and a mask | A fixed stage layout, a mask and two UV sets |
| One baked UV atlas | Simple props with one baked material | No tiling per material and one `_smdi` for everything |

Vanilla uses Multi widely for rocks and buildings: 1,960 of the `.rvmat` files under `P:\DZ` set both shader IDs to `Multi`, for example `PixelShaderID="Multi"` at `P:\DZ\rocks\data\rock_apart1\rock_apart1.rvmat:7`. Read one of those next to this file before writing your own.

## What Multi does

A mask picks between four material families:

| Mask color | Family |
|---|---|
| Black | Base |
| Red | Red |
| Green | Green |
| Blue | Blue |

Each family has its own color, specular and normal textures. That is the gain over a baked atlas: the highlight and the relief can differ per masked material.

## Stage layout

| Family | Color | Specular | Normal |
|---|---|---|---|
| Black | Stage0 | Stage5 | Stage11 |
| Red | Stage1 | Stage6 | Stage12 |
| Green | Stage2 | Stage7 | Stage13 |
| Blue | Stage3 | Stage8 | Stage14 |

Shared stages:

| Stage | Holds |
|---|---|
| Stage4 | The mask (red, green, blue and black), on the second UV set |
| Stage9 | Macro |
| Stage10 | Ambient shadow |

The vanilla rock follows this layout:

- The mask sits in `Stage4` with `texGen="4"` (`P:\DZ\rocks\data\rock_apart1\rock_apart1.rvmat:117-120`), and `TexGen4` uses `uvSource="tex1"` (`P:\DZ\rocks\data\rock_apart1\rock_apart1.rvmat:53-55`).
- `Stage5` to `Stage8` hold the specular slot. The rock fills it with the placeholder `color(0.5,0,1,1,DTSMDI)` (`P:\DZ\rocks\data\rock_apart1\rock_apart1.rvmat:122-125`): vanilla tags this slot `DTSMDI`, the detail and specular form, not plain `SMDI`.
- `Stage10` holds the baked `_as` with `texGen="4"`, so it also reads the second UV set (`P:\DZ\rocks\data\rock_apart1\rock_apart1.rvmat:147-150`).
- `Stage11` to `Stage14` hold the `_nohq` textures (`P:\DZ\rocks\data\rock_apart1\rock_apart1.rvmat:152-155`).
- The rock declares `TexGen0` to `TexGen7` and shifts some of them with `pos[]`, so the same tiled texture can sit at a different offset per family.

## UV sets

Multi needs two UV sets:

- UV set 0 (`tex`): tiling coordinates for the material textures.
- UV set 1 (`tex1`): placement of the mask, with no overlaps.

When the second set is missing, mirrored, overlapping or scaled like the tiling set, the mask lands in the wrong place.

## Skeleton

A shape to adapt, not a finished material. `rvmat_template.py multi` prints it. Replace every path and check it with a real mask and both UV sets.

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
class Stage4 { texture="MyMod\data\asset_mask_co.paa"; texGen="4"; };

class Stage5 { texture="MyMod\data\black_smdi.paa"; texGen="0"; };
class Stage6 { texture="MyMod\data\red_smdi.paa"; texGen="1"; };
class Stage7 { texture="MyMod\data\green_smdi.paa"; texGen="2"; };
class Stage8 { texture="MyMod\data\blue_smdi.paa"; texGen="3"; };

class Stage9 { texture="#(argb,8,8,3)color(0,0,0,0,MC)"; texGen="0"; };
class Stage10 { texture="#(argb,8,8,3)color(1,1,1,1,AS)"; texGen="4"; };

class Stage11 { texture="MyMod\data\black_nohq.paa"; texGen="0"; };
class Stage12 { texture="MyMod\data\red_nohq.paa"; texGen="1"; };
class Stage13 { texture="MyMod\data\green_nohq.paa"; texGen="2"; };
class Stage14 { texture="MyMod\data\blue_nohq.paa"; texGen="3"; };
```

The script's own skeleton writes `TexGen1` to `TexGen3` out in full instead of inheriting; both forms describe the same thing. Vanilla writes each `TexGen` in full.

## Painting the mask

- Paint pure black, red, green and blue for a hard assignment.
- Use blends only after the result was looked at in the engine.
- Keep the mask on UV set 1.
- Ship the mask as a `.paa` in the packed path. The working file can be a PNG or a layered file, but the `.rvmat` names the `.paa`. The vanilla rock names its mask `rock_apart1_mask.paa`; `_mask` is a suffix `/dayz-pack-texture` accepts.

## Pitfalls

- Multi on a small item that selections would handle more simply.
- No second UV set, or the mask assigned to `tex` and not `tex1`.
- Only color textures supplied, which gives up the per family specular and normal that are the point of Multi.
- A source `.png` or `.tga` path left in the `.rvmat`.

## Checks before accepting a Multi material

1. `PixelShaderID` and `VertexShaderID` are both `Multi`.
2. Stage4 names the mask and reads UV set 1 (`tex1`), directly or through its `TexGen`.
3. Stage0 to Stage3, Stage5 to Stage8 and Stage11 to Stage14 are present, or left out on purpose with the reason written down.
4. The mask colors line up with the intended families in the engine.
5. The asset really gains from fewer sections or from tiled materials per family.

`rvmat_lint.py` checks 1 to 3: a missing Stage0 to Stage4 or a mask not on `tex1` is an error, and a missing later stage is a warning.
