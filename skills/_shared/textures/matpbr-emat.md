# MatPBR and `.emat`: the metallic and roughness route

A second material route for assets authored as a metallic and roughness set: an `.emat` file holding a `MatPBR` block, a stub `.rvmat` of the same name, and textures imported through Workbench. It sits beside the Super route in `rvmat-cookbook.md`; it does not replace it.

**Status: not documented by Bohemia, not confirmed by any vanilla file on `P:\`, and not run by this repo.** Everything about `MatPBR` below rests on two example `.emat` and `.rvmat` files and the steps that go with them. Treat each claim as a lead until your own Workbench import and an in-game look confirm it, and prefer the Super route when you need a well trodden path. What vanilla does ship is in the last section.

## Contents

- [When to use it](#when-to-use-it)
- [Textures it needs](#textures-it-needs)
- [The three companion files](#the-three-companion-files)
- [Preparing the ambient occlusion map](#preparing-the-ambient-occlusion-map)
- [Importing into Workbench](#importing-into-workbench)
- [Applying it to an object](#applying-it-to-an-object)
- [Glass and transparency](#glass-and-transparency)
- [Limits](#limits)
- [Tips](#tips)
- [What vanilla ships](#what-vanilla-ships)

## When to use it

| Use MatPBR when | Use Super when |
|---|---|
| The source is an authored metallic and roughness set (Substance, Quixel, a bought pack, a generated set) | The source already has DayZ suffix textures, or you are cloning a vanilla material |
| The asset is a weapon, clothing, a vehicle or a building | The asset is terrain (no MatPBR terrain path is known) |
| The material needs no damage or destruct look | The item needs `healthLevels[]` damage looks (`config-wiring.md`) |
| A larger texture footprint is acceptable | Mod size or the texel budget is tight |

It is reported to work on weapons, clothing, vehicles and buildings (not checked here), and is not solved for terrain.

## Textures it needs

Unreal style suffixes, separate from the DayZ suffixes in `suffixes-and-sizes.md`:

| Suffix | Role | Notes |
|---|---|---|
| `_albedo` | Base color | The role `_co` has in the Super route |
| `_ao` | Ambient occlusion | One per model is usually enough (see Tips) |
| `_metallic` | Metalness | Works only in a limited way; check per asset |
| `_normal` | Normal map, DirectX convention | The same Y- convention as `_nohq` (`normal-maps.md`); do not compress it |
| `_roughness` | Roughness | The opposite sense of the gloss in `_smdi` blue |

These source names are for Workbench, not ImageToPAA: `/dayz-pack-texture` refuses them.

## The three companion files

The Super route needs one `.rvmat`. This route needs three files per material:

1. **The `.emat`** holds the `MatPBR { ... }` block and every texture reference, as Workbench resource IDs and not plain paths.
2. **The `.rvmat`** is a stub with only `PixelShaderID` and `VertexShaderID`. The example files use `CalmWater`. Why that ID works for a solid surface is not known; take it as an observed recipe, not an understood mechanism.
3. **An environment cube map**: a 256 x 128 image imported as EDDS with `GenerateCubemap` ticked and `TiledTexture` unticked in the import settings. A fully bright map works better than a dark-bottomed one on most surfaces, and a darker one on glass (not checked here).

**Naming rule:** the `.emat` and the `.rvmat` have the same file name and differ only in extension. Treat this as a hard requirement.

## Preparing the ambient occlusion map

A default AO bake renders too dark in game (not checked here). To brighten it in any editor with a Screen blend mode:

1. Duplicate the AO layer.
2. Invert the colors of the duplicate.
3. Set the duplicate's blend mode to Screen.
4. Flatten to one layer.

## Importing into Workbench

1. Put the files at their final place first, with the `.emat` and the `.rvmat` already sharing a name.
2. Register and import both in DayZ Workbench.
3. Click each `.edds` in Workbench and confirm it imported. If one failed, save the source again as a 32-bit PNG and import again. Doing this for every texture up front saves the retry.
4. Select every `.edds` except the normal map and import again with `DXTCompression` (import settings, bottom right). Select several with Ctrl; a misclick means selecting the batch again.
5. Open the `.emat` and copy each texture's resource ID (the `{` 16 hex digits `}` identifier Workbench made on import) into its slot.

**Resource ID trap:** the ID is derived from the registered file's path and name. Renaming or moving a registered `.edds` breaks it. To move a texture, move the source PNG and import again at the new place. A PNG saved by Blender can fail an import for the reason given in `suffixes-and-sizes.md` ("Images ImageToPAA refuses").

## Applying it to an object

- Assign the `.rvmat` stub, not the `.emat`, as the material: in Object Builder, in `config.cpp`, or with `SetObjectMaterial`.
- The face texture field is ignored under MatPBR. Leave it at its default.

## Glass and transparency

Two methods. The resource IDs in the blocks are examples; an ID only exists after your own import, so do not reuse these.

Caveats (not checked here): overlapping see-through surfaces (foliage) sort badly, and there is no vertex animation like the vanilla tree shader's.

### Whole surface see-through (glass panes)

`Sort translucent` with `BlendMode AlphaBlend`. A darker environment map works better here.

```
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

### Punch through (mesh, foliage with holes)

`AlphaTest` makes pixels under a threshold fully see-through. It uses the brighter environment map.

```
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

## Limits

Not checked here. Treat them as hard limits until shown otherwise.

- **No macro or damage overlay.** There are no stages, so the Super pattern of a wear macro in Stage3 does not exist here. Whether `healthLevels[]` can still swap between whole MatPBR materials per health level is a reasonable guess from how that array works, and it is not confirmed. Check it in game before a damage look depends on it.
- The metallic response is limited and uneven. Judge it per asset, not by the source tool's preview.
- The textures are usually larger in total than the Super and `_smdi` form.
- A surface meant to show a clear reflection needs to be darker, or should use the Super route.
- No terrain path was found.

## Tips

- **Share maps across parts** when the surface is the same. Roughness, metallic and normal change the reflection, so keep them per material. AO is usually the same across a model: one AO map per model cuts the mod size.
- **Resolution:** 2K as the standard, 1K for small objects. 4K works and costs 16 times the pixels of 1K and 4 times those of 2K, in load time and video memory on every client.
- **Do not compress the normal map.** Compression loses detail, and the metallic response looks better when the normal is not perfectly flat (not checked here).
- **Check the license** of a bought texture set before feeding it to a generating or editing tool. Some licenses forbid it.

## What vanilla ships

Checked on `P:\` on 2026-11-17.

- Vanilla ships `.emat` files as text, with texture references in the same `{` hex `}` plus path form. The pond material opens with `MatWaterPool {` (`P:\DZ\water_bliss\ponds\data\enoch_pond.emat:1`) and names its normal map as `NormalMap "{126A7892740C80E0}DZ/water_bliss/ponds/data/enoch_pond_nohq.edds"` (`P:\DZ\water_bliss\ponds\data\enoch_pond.emat:4`).
- The stub pairing is vanilla too. Next to that file sits `enoch_pond.rvmat`, two lines long: `PixelShaderID="CalmWater"` and `VertexShaderID="CalmWater"` (`P:\DZ\water_bliss\ponds\data\enoch_pond.rvmat:1-2`). Fourteen vanilla `.rvmat` files under `P:\DZ` use that shader pair, all of them water, and eight have an `.emat` of the same name beside them. The lake stub is the same two lines (`P:\DZ\water\ponds\data\water_lake.rvmat:1-2`), with its `.emat` under `P:\graphics\materials\water\`.
- Under `P:\DZ` there are 11 `.emat` files: eight `MatWaterPool` and three `MatOceanOld` (`P:\DZ\worlds\sakhal\data\sakhal_sea.emat:1`). None holds a `MatPBR` block.
- A material class with PBR in its name does exist in the Workbench data: `MatPBRBasic {` with `AlphaTest` and `BlendMode` keys (`P:\system\wbdata\previewwindow\transparentmat.emat:1-4`). No vanilla `.emat` on `P:\` uses a class named plain `MatPBR`, so the block shape above rests on the two example files alone.
- Particle and postprocess `.emat` files are a different use of the same format; the particle classes are covered by the `/dayz-particles` skill.

`rvmat_lint.py` (`rvmat-cookbook.md`) warns when a stub `.rvmat` (no stages, a shader other than Super, Multi or Normal) has no `.emat` beside it, or when that `.emat` lacks a required map or names one by a plain path. A vanilla style water pair with `MatWaterPool` gets no warning.
