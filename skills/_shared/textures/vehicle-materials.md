# Vehicle and hard surface materials

Which shader a vehicle or hard surface part needs, how to add tiled detail when the UVs overlap, how color variants are wired, and how to generate wear in code without it looking generated.

Vehicle paint values (`specularPower`, how dark vanilla paint is in the `_smdi`) are in `surface-recipes.md`. The vehicle config belongs to `dayz-vehicle-specialist`. Lines marked third-party mod behaviour were read in a mod's files, not on `P:\`.

## Which shader for a part

A part's base color comes from the face texture assigned in the `.p3d`, multiplied by the material's `diffuse[]`. That decides the shader:

- **The faces carry a real `_co`** (a proper unwrap): use Super, with `_nohq` in Stage1, detail in Stage2, `_smdi` in Stage5, fresnel in Stage6 and an environment map in Stage7. The sedan body is a vanilla example: `PixelShaderID="Super"` at `P:\DZ\vehicles\wheeled\civiliansedan\data\civiliansedan.rvmat:7`.
- **The part has one constant color and no face `_co`**: use `PixelShaderID="NormalMapSpecularMap"` with `VertexShaderID="NormalMap"` (`rvmat-stages.md` counts how often vanilla does), a `_nohq` in Stage1 and an `_sm` in Stage2. The base color stays the `diffuse[]` constant. Vanilla roads do this: `asf2_sakhal_nohq.paa` in `Stage1` (`P:\DZ\structures_sakhal\roads\parts\data\asf2_sakhal.rvmat:9` to `:11`) and `asf2_sakhal_sm.paa` in `Stage2` (`:21` to `:23`). `mudsakhal_dirt.rvmat` in the same folder is built the same way.

Super expects the color from the face. On a mesh whose faces have no texture, with the color only in `diffuse[]`, Super loses the base color. `NormalMapSpecularMap` adds relief and a specular map on top of the constant, so it improves a flat colored mesh with no `_co` atlas and no change to the `.p3d`.

### Spotting a part with no face texture

Read LOD 0 of the MLOD `.p3d` with py3d (`_shared/py3d-mlod-notes.md`) and look at each face's texture. If all are empty, the model was exported flat shaded and its color lives only in the material's `diffuse[]`: use `NormalMapSpecularMap`, not Super.

That `NormalMapSpecularMap` falls back to the `diffuse[]` constant without a face `_co` is supported only indirectly, by the flat `Normal` shader rendering the diffuse color on faces with no texture. Confirm it in game the first time. If a part renders black, give that selection a `_co` through `hiddenSelectionsTextures[]` (only possible for named hidden selections), or fall back to `Normal` with a `_nohq` in Stage1.

### Stage block for a constant color part

`N` is the tiling factor; keep the part's own color values.

```cpp
ambient[]={...};
diffuse[]={...};
specular[]={...};
specularPower=...;
PixelShaderID="NormalMapSpecularMap";
VertexShaderID="NormalMap";
class Stage1 { texture="MyMod\data\X_nohq.paa"; uvSource="tex"; class uvTransform { aside[]={N,0,0}; up[]={0,N,0}; dir[]={0,0,0}; pos[]={0,0,0}; }; };
class Stage2 { texture="MyMod\data\X_sm.paa"; uvSource="tex"; class uvTransform { aside[]={N,0,0}; up[]={0,N,0}; dir[]={0,0,0}; pos[]={0,0,0}; }; };
```

## Tiled detail on overlapping UVs

When a body packs many materials into one overlapping UV atlas, or has no baked color, a single unwrapped `_nohq` or `_co` bleeds from one part onto the next. Use a tiled detail map instead: `uvSource="tex"` with a `uvTransform` whose `aside[]` and `up[]` repeat the map across each face, whatever the base UV layout. One mod van's body uses `aside[]={16,0,0}; up[]={0,16,0};` in Stage2 (third-party mod behaviour, not vanilla).

Pick the factor by how dense the real detail is, then look in game. With overlapping UVs the tiling starts at a different point on each part, which is fine for a subtle surface texture and visible on a large directional pattern.

## Color variants through a `color` selection

The vehicle exposes a `color` hidden selection, and each variant is a subclass that overrides `hiddenSelectionsTextures[]` at that selection's index. A hidden selection texture applies even when the face texture in the `.p3d` is empty, so variants need no model change.

The shape one mod quad bike uses (third-party mod behaviour, not vanilla), with eight light selections before `color`:

```cpp
class MyMod_QuadBike_Green: MyMod_QuadBike_Base
{
	hiddenSelections[]={ /* eight light selections */, "color" };
	hiddenSelectionsTextures[]={ "","","","","","","","", "MyMod\QuadBike\data\quadbike_green_ca.paa" };
	hiddenSelectionsMaterials[]={ /* eight light materials */, "MyMod\QuadBike\data\quadbike.rvmat" };
};
// The _Yellow, _Red and _Black siblings use quadbike_<color>_ca.paa; _Grey keeps the base.
```

The same pattern serves a whole body texture per color (`body_black_full.paa`, `body_green_full.paa` and so on at the body color index).

- Keep the paint on its own selection with a neutral `diffuse[]`. A variant is then one new color texture and one subclass.
- For a gloss change per color, override `hiddenSelectionsMaterials[]` at the same index.
- The hidden selection side for clothing is in `_shared/wearables/references/color-variants.md`.

### Paint spread over several atlases

A variant subclass changes only the atlases that sit on a `hiddenSelections[]` index (**measured in game**, DayZ 1.30). On a body whose paint was split across several atlases, every atlas not tied to a variant selection kept the base look: the lower details changed and the main body stayed red, because its atlas shared no face with any variant selection.

- Before trusting a variant, count faces. Every visible painted face must fall in a variant hidden selection, in every visual LOD and in the view LODs 1100 and 1200.
- On a strongly saturated base (mean RGB 201 / 53 / 50) a multiplied tint cannot reach other hues. Bake each variant as its own `_co` from the base luminance (`L / mean * target color`), with a soft mask that keeps the dark marks.

## Wear generated in code

Sine based patterns look generated. A wear pass on a baked atlas that modulated the grain with a sine and placed scratches where `sin(x*631 + z*79) > 0.993` inside bands of `sin(y*121)` showed, at one to one on the atlas, rows of dashes like a barcode on the black parts and regular ripples on the silver. Rewritten as below, the patterns were gone at one to one and the wear read well at mid distance in game:

- value noise interpolated in the object's 3D space at two scales, about 16 cm and 5 cm, so it stays continuous across UV seams;
- scratches as 90 random segments of 2 to 7 cm by about 1 mm, laid on the face and along its normal, with a fixed seed;
- dirt from the baked AO, road grime below a height, dust on faces that look up, and the `_co` slightly desaturated.

Start with 3D noise in object space and random segments with a fixed seed, never sine thresholds, and look at the atlas at one to one before spending a game run.
