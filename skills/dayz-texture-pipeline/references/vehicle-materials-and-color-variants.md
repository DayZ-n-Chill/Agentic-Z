# Vehicle and hard surface materials: shader choice, tiled detail, color variants

Which shader a vehicle or hard surface part needs, how to add tiled detail when the UVs overlap, how color variants are wired, and what one mod learned about generating wear by code.

How to read it: a `P:\` citation was checked on the vanilla files. Facts from third party mods name the mod (FC_Uaz_2206, Croco QuadBike, LFQuad3) and were read in that mod's files, not on `P:\`. The suffix table is in `_shared/textures/suffixes-and-sizes.md` and the vehicle config side belongs to dayz-vehicle-specialist.

## Which shader for a part

A part's base color comes from the face texture assigned in the `.p3d`. The material's `diffuse[]` multiplies it. That decides the shader:

- **The faces carry a real `_co`** (a proper unwrap): use Super, with `_nohq` in Stage1, `_smdi` in Stage5, detail in Stage2, fresnel in Stage6 and an environment map in Stage7. A vanilla body to mirror is the sedan's, which sets `PixelShaderID="Super"` at `P:\DZ\vehicles\wheeled\civiliansedan\data\civiliansedan.rvmat:7`. Third party example: `FC_Uaz_2206\textures\body.rvmat`.
- **A constant color part with no face `_co`**: use `PixelShaderID="NormalMapSpecularMap"` with `VertexShaderID="NormalMap"`, a `_nohq` in Stage1 and an `_sm` in Stage2. The base color stays the `diffuse[]` constant. Vanilla roads do this: the shader pair at `P:\DZ\structures_sakhal\roads\parts\data\asf2_sakhal.rvmat:7-8`, `asf2_sakhal_nohq.paa` in `Stage1` (`P:\DZ\structures_sakhal\roads\parts\data\asf2_sakhal.rvmat:9-11`) and `asf2_sakhal_sm.paa` in `Stage2` (`P:\DZ\structures_sakhal\roads\parts\data\asf2_sakhal.rvmat:21-23`). `mudsakhal_dirt.rvmat` in the same folder is built the same way.

Why it matters: Super expects the color from the face. On a mesh whose faces have an empty texture (the color lives only in `diffuse[]`), Super loses the base color. `NormalMapSpecularMap` adds relief and a specular map on top of the constant, so it improves a flat constant color mesh with no `_co` atlas and no change to the `.p3d`.

How common each is under `P:\DZ` (scan of 2026-11-17): Super pairs 5,838 files, `NormalMapSpecularMap` with `NormalMap` 87 (roads, ruins, decals and similar tiled surfaces), and `Normal` with `Basic` 76 (the flat shader with no stages: lighting from the vertex normals only).

### Finding the "no face texture" case

Read LOD 0 of the MLOD `.p3d` with py3d (`skills/_shared/py3d-mlod-notes.md`) and look at each face's texture. All empty means the model was exported flat shaded and its color is only the material's `diffuse[]`. That is the sign to use `NormalMapSpecularMap`, not Super.

### Not yet confirmed in game

That `NormalMapSpecularMap` falls back to the `diffuse[]` constant when there is no face `_co` is supported only indirectly: the flat `Normal` shader already renders the diffuse color on faces with no texture. Confirm it in game on first use. If a part renders black, give that selection a `_co` through `hiddenSelectionsTextures[]` (possible only for named hidden selections) or fall back to `Normal` with a `_nohq` in Stage1.

### Stage block for a constant color part

```cpp
ambient[]={...};            // keep the part's tuned color
diffuse[]={...};            // base color (no face _co needed)
specular[]={...};
specularPower=...;
PixelShaderID="NormalMapSpecularMap";
VertexShaderID="NormalMap";
class Stage1 { texture="MyMod\data\X_nohq.paa"; uvSource="tex"; class uvTransform { aside[]={N,0,0}; up[]={0,N,0}; dir[]={0,0,0}; pos[]={0,0,0}; }; };
class Stage2 { texture="MyMod\data\X_sm.paa";   uvSource="tex"; class uvTransform { aside[]={N,0,0}; up[]={0,N,0}; dir[]={0,0,0}; pos[]={0,0,0}; }; };
```

## Tiled detail on overlapping or unbaked UVs

When a body packs many materials into one overlapping UV atlas, or has no baked color, a single unwrapped `_nohq` or `_co` bleeds from one part onto another. Use a tiled detail map: `uvSource="tex"` with a `uvTransform` whose `aside[]` and `up[]` repeat the map across each face, whatever the base UV layout is. The FC_Uaz_2206 body uses `aside[]={16,0,0}; up[]={0,16,0};` in Stage2. Pick the factor by how dense the real detail is, then look in game: with overlapping UVs the tiling starts at a different point on each part, which is fine for a subtle surface texture and visible for a large directional pattern.

## Normal map orientation

`_nohq` is DirectX style, X+ and Y-. Invert the green channel of an OpenGL source before the `.paa` export. How to measure a source of unknown convention is in `map-conventions.md`.

## Color variants: the `color` hidden selection

A vehicle exposes a `color` hidden selection, and each variant is a subclass that overrides the entry of `hiddenSelectionsTextures[]` at that selection's index. A hidden selection texture applies even when the face texture in the `.p3d` is empty, so this needs no model change.

Croco QuadBike (third party, read in `CrocoVehicles\QuadBike\config.cpp`):

```cpp
class Croco_QuadBike_Green: Croco_QuadBike_base
{
    hiddenSelections[]         = { ...8 lights..., "color" };               // "color" is the last index
    hiddenSelectionsTextures[] = { "","","","","","","","","",  "CrocoVehicles\QuadBike\data\quadbike_green_ca.paa" };
    hiddenSelectionsMaterials[]= { ...lights.rvmat..., "CrocoVehicles\QuadBike\data\quadbike.rvmat" };
};
// siblings: _Yellow, _Red, _Black use quadbike_<color>_ca.paa; _Grey uses the base
```

FC_Uaz_2206 uses the same pattern (`body_black_full.paa`, `body_green_full.paa` and so on at the body color index).

- Keep the paint on its own selection with a material whose `diffuse[]` is neutral. A variant is then one new color texture and one subclass.
- For a gloss change per color, override `hiddenSelectionsMaterials[]` at the same index.
- The hidden selection mechanics for clothing are in `_shared/wearables/references/color-variants.md`.

### Paint spread over several atlases, and saturated bases

Measured in game (LFQuad3, DayZ 1.30.164014, 2026-09-14): a variant subclass only changes the atlases that sit on a `hiddenSelections[]` index. With the paint split across several atlases, every atlas not attached to a variant selection kept the base look: only the lower details changed and the main body stayed red, because its atlas shared no face with any variant selection.

Starting points from that case:

- Before trusting a variant, count faces: every visible painted face must fall in a variant hidden selection, in every visual LOD and in the view LODs 1100 and 1200.
- On a saturated base (measured mean RGB 201 / 53 / 50) a multiplied tint cannot reach other hues. Bake each variant as its own `_co` from the base luminance (`L / mean * target color`) with a soft mask that keeps the dark marks.

## A worn variant generated by code

One mod's account (2026-10-28, its own tool, nothing stored): a procedural wear pass on a baked atlas first modulated the grain with a sine and placed scratches where `sin(x*631 + z*79) > 0.993` inside bands of `sin(y*121)`. At one to one on the atlas it showed rows of dashes like a barcode on the black parts and regular ripples on the silver. It was rewritten before any game run:

- value noise interpolated in the object's 3D space at two scales (about 16 cm and 5 cm), so it stays continuous across UV seams;
- scratches as 90 random segments of 2 to 7 cm by about 1 mm, laid on the face and along its normal, with a fixed seed;
- dirt from the baked AO, road grime below a height, dust on faces that look up, and the `_co` slightly desaturated.

At one to one the patterns were gone, and the owner reported that in game the wear showed at mid distance.

Starting point: prefer 3D noise in object space and random segments with a fixed seed over sine thresholds. Look at the atlas at one to one before spending a game run.
