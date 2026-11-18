# MatPBR and `.emat` materials

Covers the second material route, for assets made as a metallic and roughness set: an `.emat` file holding a `MatPBR` block, a stub `.rvmat` of the same name, and textures imported through Workbench. It sits beside the Super route in `rvmat-cookbook.md` and does not replace it.

Bohemia does not document this route, no vanilla file on `P:\` uses a `MatPBR` block, and it is unverified here. Everything about `MatPBR` below comes from two example `.emat` and `.rvmat` files and the steps that came with them, so confirm each point with your own Workbench import and a look in game. Prefer Super when you need a well trodden path. What vanilla does ship is in the last section.

## When to use it

| Use MatPBR when | Use Super when |
|---|---|
| The source is a metallic and roughness set (Substance, Quixel, a bought pack, a generated set) | The source already has DayZ suffix textures, or you are copying a vanilla material |
| The asset is a weapon, clothing, a vehicle or a building | The asset is terrain (no MatPBR terrain route is known) |
| The material needs no damage or destruct look | The item needs `healthLevels[]` damage looks (`config-wiring.md`) |
| A larger texture budget is fine | Mod size or texel budget is tight |

Reported to work on weapons, clothing, vehicles and buildings; not checked on `P:\`.

## Textures it needs

Unreal style suffixes, separate from the DayZ suffixes in `suffixes-and-sizes.md`:

| Suffix | Role | Notes |
|---|---|---|
| `_albedo` | Base color | Plays the part `_co` plays in Super |
| `_ao` | Ambient occlusion | One per model is usually enough |
| `_metallic` | Metalness | Responds only partly; judge per asset |
| `_normal` | Normal map, DirectX convention | Same Y- convention as `_nohq` (`normal-maps.md`); leave it uncompressed |
| `_roughness` | Roughness | The opposite sense of the gloss in `_smdi` blue |

These names are for Workbench, not ImageToPAA; `/dayz-pack-texture` refuses them.

## The three files per material

Super needs one `.rvmat`. MatPBR needs three files:

1. The `.emat`, holding the `MatPBR { ... }` block. Every texture in it is named by its Workbench resource ID, not a plain path.
2. The `.rvmat`, a stub with only `PixelShaderID` and `VertexShaderID`. The example files use `CalmWater`; why that works on a solid surface is not known, so treat it as a recipe that works, not a mechanism.
3. An environment cube map: a 256 x 128 image imported as EDDS with `GenerateCubemap` ticked and `TiledTexture` unticked. A fully bright map suits most surfaces and a darker one suits glass (reported, not checked).

The `.emat` and the `.rvmat` share one file name and differ only in extension. Keep it that way.

## Brightening the ambient occlusion map

A default AO bake renders too dark in game (reported, not checked). In any editor with a Screen blend mode:

1. Duplicate the AO layer.
2. Invert the duplicate.
3. Set the duplicate to Screen.
4. Flatten.

## Importing into Workbench

1. Put the files at their final place first, with the `.emat` and `.rvmat` already sharing a name.
2. Register and import both in DayZ Workbench.
3. Click each `.edds` and confirm it imported. If one failed, save its source again as a 32-bit PNG and import again; doing this for every texture first saves the retry.
4. Select every `.edds` except the normal map (Ctrl click) and import again with `DXTCompression` set in the import settings, bottom right.
5. Open the `.emat` and paste each texture's resource ID, the `{` 16 hex digits `}` code Workbench made on import, into its slot.

The resource ID comes from the registered file's path and name, so renaming or moving a registered `.edds` breaks it. To move a texture, move its source PNG and import again at the new place. A PNG saved by Blender can fail the import for the reason in `suffixes-and-sizes.md`, "Images ImageToPAA refuses".

## Putting it on an object

- Assign the stub `.rvmat`, not the `.emat`, as the material: in Object Builder, in `config.cpp` or with `SetObjectMaterial`.
- MatPBR ignores the face texture field; leave it at its default.

## Glass and see-through surfaces

The resource IDs below are examples. An ID exists only after your own import, so never reuse these. Reported, not checked: overlapping see-through surfaces such as foliage sort badly, and there is no vertex animation like the vanilla tree shader's.

For a pane that is see-through all over, use `Sort translucent` with `BlendMode AlphaBlend` and the darker environment map:

```cpp
MatPBR {
 AlbedoMap "{107E0EF11826BF98}...glass_ca.edds"
 Sort translucent
 CastShadow 0
 ReceiveShadow 1
 Specular 0.1 0.1 0.1 0.5
 SpecularMul 0.05
 Diffuse 0.95 0.95 0.95 0.5
 BlendMode AlphaBlend
 NormalMap "{7E0685D245F77EF8}...glass_normal.edds"
 RoughnessMap "{9A31F3AB2ED461C8}...glass_roughness.edds"
 MetalnessMap "{E43FB2221EF03FF2}...glass_glass_metallic.edds"
 AOMap "{4EA7E41FBEECE7C7}...glass_ao.edds"
 EnvReflMap "{C67F75AABD568129}...env_landdark_co.edds" cube
}
```

For holes in a mesh or foliage, `AlphaTest` makes pixels under the threshold fully clear. It uses the brighter environment map:

```cpp
MatPBR {
 AlbedoMap "{CD0D20E47EAAF7B4}...texture_albedo.edds"
 CastShadow 1
 ReceiveShadow 1
 SpecularMul 0.05
 AlphaTest 0.05
 NormalMap "{8C28C3AFF87D1AF7}...texture_normal.edds"
 RoughnessMap "{58B6DAB5DC14D87F}...texture_roughness.edds"
 MetalnessMap "{AE30B70648A7C2DE}...texture_metallic.edds"
 AOMap "{E66D5BFBF10675E1}...texture_ao.edds"
 EnvReflMap "{066623E928F029E6}...env_land_co.edds" cube
}
```

## Limits and habits

Reported, not checked; treat them as limits until a test shows otherwise.

- There are no stages, so the Super habit of a wear macro in Stage3 has no place here. Whether `healthLevels[]` can still swap whole MatPBR materials per level is a fair guess from how the array works and is unconfirmed; test it in game before a damage look depends on it.
- The metallic response is limited and uneven. Judge it on the asset, not in the source tool's preview.
- The textures usually weigh more in total than a Super set with `_smdi`.
- A surface meant to show a clear reflection has to be darker, or should use Super.
- Share maps between parts only where the surface is the same. Roughness, metallic and normal change the reflection, so keep them per material; AO is usually the same across a model, and one AO map per model saves mod size.
- Use 2K as the standard size and 1K for small objects. 4K works, at 16 times the pixels of 1K and 4 times those of 2K, paid in load time and video memory on every client.
- Leave the normal map uncompressed: compression loses detail, and the metallic response looks better when the normal is not perfectly flat.
- Read the licence of a bought texture set before feeding it to a generating or editing tool; some forbid it.

## What vanilla ships

- `.emat` files are plain text, and textures in them use the same `{` hex `}` plus path form. The pond material opens with `MatWaterPool {` (`P:\DZ\water_bliss\ponds\data\enoch_pond.emat:1`) and names its normal map as `NormalMap "{126A7892740C80E0}DZ/water_bliss/ponds/data/enoch_pond_nohq.edds"` (`:4`).
- The stub pairing is vanilla too. Beside that file sits `enoch_pond.rvmat`, two lines long: `PixelShaderID="CalmWater"` and `VertexShaderID="CalmWater"` (`P:\DZ\water_bliss\ponds\data\enoch_pond.rvmat:1` and `:2`). Fourteen `.rvmat` files under `P:\DZ` use that pair, all water, and eight have an `.emat` of the same name beside them. The lake stub is the same two lines (`P:\DZ\water\ponds\data\water_lake.rvmat:1` and `:2`), with its `.emat` under `P:\graphics\materials\water\`.
- `P:\DZ` holds 11 `.emat` files: eight `MatWaterPool` and three `MatOceanOld` (`P:\DZ\worlds\sakhal\data\sakhal_sea.emat:1`). None holds a `MatPBR` block.
- The Workbench data has a class with PBR in its name, `MatPBRBasic {`, with `AlphaTest` and `BlendMode` keys (`P:\system\wbdata\previewwindow\transparentmat.emat:1` to `:4`). No vanilla `.emat` uses a class named plain `MatPBR`, so the block shape above rests on the two example files alone.
- Particle and postprocess `.emat` files use the same format for something else; the particle classes are in `/dayz-particles`.

`rvmat_lint.py` (`rvmat-cookbook.md`) warns when a stub `.rvmat` (no stages, a shader other than Super, Multi or Normal) has no `.emat` beside it, or when that `.emat` misses a required map or names one by a plain path. A vanilla style water pair with `MatWaterPool` passes without a warning.
