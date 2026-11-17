# Texture suffixes and sizes

What each texture suffix means, how ImageToPAA packs it, which sizes vanilla uses, and the procedural textures that fill an empty material slot.

## How the suffix works

ImageToPAA reads the last `_xx` of the filename and looks it up in `<DayZ Tools>\Bin\ImageToPAA\TexConvert.cfg` (`class TextureHints`). The match picks the compression format and any channel swizzle. A file with no matching suffix gets no rule from that file, so it can end up in the wrong format or color space, which is why `/dayz-pack-texture` refuses it. Never rename the user's images; report the suffix you suggest.

## The suffixes mod gear uses

| Suffix | Role | What `TexConvert.cfg` does | Goes in |
|---|---|---|---|
| `_co` | Color (diffuse), no alpha | `DXT1`, sRGB (`class ColorMap`) | The model face, `hiddenSelectionsTextures[]`, or `Stage3` of a Skin material |
| `_ca` | Color with alpha | `DXT5`, sRGB (`class ColorAlphaMap`) | Same places as `_co`, when the surface needs transparency (glass, hair, straps) |
| `_nohq` | Normal map, high quality | `DXT5`; alpha becomes 1 minus red and red becomes 1 minus alpha (`class normalmap_hq`) | `Stage1` |
| `_smdi` | Specular | `DXT1`, red forced to 1, green and blue kept (`class specular_diffuseinverse_map`) | `Stage5` |
| `_as` | Ambient shadow (baked occlusion) | `DXT1`, only green kept (`class ambient_shadow`) | `Stage4` of a Super material |
| `_mc` | Macro (a color layer blended over the base) | `DXT5` (`class macro`) | `Stage3` of a Super material, `Stage2` of a Skin material |
| `_dt` | Detail (fine tiling grain) | Only alpha kept, mipmaps fade out with distance (`class detail_short`) | `Stage2` of a Super material |

**Tool knowledge** (Bohemia's Super shader notes, not a vanilla file): in `_smdi` the green channel is how strong the highlight is and the blue channel is how tight it is (gloss). That matches the swizzle above, which throws red away. Paint dark green and dark blue for cloth, bright green and bright blue for polished metal or glass.

What those rules mean when you look at a packed file. The counts are from a header scan of the 30,094 `.paa` files under `P:\DZ`:

- **`_nohq` is not a plain RGB image inside.** `class normalmap_hq` sets `channelSwizzleA = "1-R"` and `channelSwizzleR = "1-A"`: the stored alpha is 1 minus the normal's X, and the stored red is 0 for an opaque source. All 3,865 vanilla `_nohq.paa` files are DXT5 and carry the `SWIZ` tag `05 04 02 03`, for example `P:\DZ\vehicles\wheeled\hatchback_02\data\hatchback_02_rust_body_nohq.paa`. Convert the `.paa` back with ImageToPAA and measure on that PNG, which is plain (X, Y, Z) again.
- **`_nohq` is DirectX style, Y-** (**tool knowledge**, Bohemia's "RVMAT basics" wiki page). Blender bakes OpenGL style, Y+, by default, so its green channel is inverted before the export. How to measure a source of unknown convention is in `dayz-texture-pipeline/references/map-conventions.md`.
- **`_as` keeps only green.** `class ambient_shadow` forces red, blue and alpha to 1, and all 1,114 vanilla `_as.paa` files carry the `SWIZ` tag `08 08 02 08`. Judge an `_as` by its green channel, never as greyscale: in `P:\DZ\gear\consumables\data\pile_of_planks_as.paa` green averages 53 while the other channels sit at 255.
- **`_smdi` gets a white red channel whatever you paint.** `class specular_diffuseinverse_map` sets `channelSwizzleR = "1"`; all 2,696 vanilla `_smdi.paa` files carry the `SWIZ` tag `08 08 02 03`. Checked with ImageToPAA on 2026-11-17: a source filled with R = 0, G = 56, B = 200 decodes back as (255, 56, 200, 255).
- **The suffix is the end of the name.** A normal map named `vest_nohq_DX.png` matches no normal map rule and is packed as a plain texture (reported by one mod project, not rechecked). Keep the role suffix last.

The other suffixes `/dayz-pack-texture` accepts (`_lco`, `_lca`, `_no`, `_non`, `_nopx`, `_sm`, `_ads`, `_adshq`, `_mco`, `_detail`, `_cdt`, `_dtsmdi`, `_mask`, `_sky`) are for terrain, vegetation, buildings and the sky. The full list and the reason for it are in `_shared/conventions/assets.md`.

Thermal textures are named `<name>_ti_ca.paa` (for example `P:\DZ\characters\tops\data\pcu5jacket_ti_ca.paa`). They pack as `_ca` and go in `StageTI` (see `rvmat-stages.md`).

## Sizes

Every side must be a power of two (64, 128, 256, 512, 1024, 2048). The two sides may differ. ImageToPAA enforces it: a 96 x 64 PNG is refused with `Error (Img is not of power of 2 size)` (checked 2026-11-17), and every one of the 30,094 `.paa` files under `P:\DZ` has power of two sides. One mod project reports that a 1920 x 1080 `.paa` made by another encoder still loads as a UI texture; that is a third party report and vanilla ships no such file (`dayz-texture-pipeline/references/ui-textures-and-edds.md`). A header scan of the vanilla `.paa` files shows what vanilla picks:

| Folder under `P:\DZ` | Most common `_co` size | Notes |
|---|---|---|
| `weapons\firearms` | 2048 x 2048 (78 files) | `_nohq` and `_smdi` match the `_co` |
| `characters\tops` | 2048 x 1024 (149 files) | 512 x 512 next (75), for small shirts and armbands |
| `characters\vests` | 1024 x 1024 (12 files) | 2048 x 2048 for the larger vests (8) |
| `characters\heads` | 2048 x 1024 (104 files) | transparent parts such as hair are `_ca`, mostly 1024 x 1024 |
| `gear\tools` | 1024 x 1024 (20 files) | 512 x 512 for small tools |
| `gear\food` | 1024 x 1024 (109 files) | 512 x 512 next (42) |

Rules of thumb that follow from the scan:

- Make `_nohq`, `_smdi` and `_as` the same size as their `_co`. In the folders above 820 of 882 such textures match their `_co`; the rest are smaller, mostly `_as` at half size.
- Pick the size by how big the item is on screen: 2048 for a gun or a full outfit, 1024 for a vest, a tool or a can, 512 for a small item.
- Bigger textures cost memory on every client. Don't go above 2048 for an item.

## Procedural textures for empty slots

When a stage has no real texture, vanilla writes a procedural one instead of leaving the stage out. The form is `#(argb,8,8,3)color(r,g,b,a,TAG)`, where the tag names the role. These are the neutral values vanilla uses (from `P:\DZ\characters\tops\data\bomberjacket.rvmat`, `P:\DZ\vehicles\wheeled\data\auta_skla.rvmat` and `P:\DZ\characters\glasses\data\tacgoggles_glass.rvmat`):

| Slot | Neutral value | Means |
|---|---|---|
| Normal (`Stage1`) | `#(argb,8,8,3)color(0.5,0.5,1,1,NOHQ)` | Flat surface |
| Detail (`Stage2`) | `#(argb,8,8,3)color(0.5,0.5,0.5,1,DT)` | No detail grain |
| Macro (`Stage3`) | `#(argb,8,8,3)color(0,0,0,0,MC)` | No macro layer (alpha 0) |
| Ambient shadow (`Stage4`) | `#(argb,8,8,3)color(1,1,1,1,AS)` | No baked shadow |
| Specular (`Stage5`) | `#(argb,8,8,3)color(1,1,1,1,SMDI)` | Full highlight, used on glass |
| Environment (`Stage7`) | `#(argb,8,8,3)color(0,0,0,1,CO)` | No reflection |

Fresnel is always procedural: `#(ai,64,64,1)fresnel(n,k)`, or `#(ai,64,64,1)fresnelGlass(n)` for glass. See `rvmat-stages.md`.

Two of these slots have more than one vanilla value, counted over the `.rvmat` files under `P:\DZ`:

- **Detail.** `color(0.5,0.5,0.5,1,DT)` appears 3,843 times and `color(0.5,0.5,0.5,0.5,DT)` 1,299 times, for example at `P:\DZ\vehicles\wheeled\offroad_02\data\offroad_02_decals.rvmat:27`. Copy the one in the material you started from.
- **Specular.** There is no single neutral value. Of 1,007 procedural `SMDI` textures, the most common is `color(0,0,1,1,SMDI)` (297 times, for example `P:\DZ\characters\bodies\data\jeans_f_grd.rvmat:59`), which has green at 0 and so no highlight at all; `color(1,1,1,1,SMDI)` comes second with 153. The first number (red) is 0 in 566 of them and 1 in 384, so a white red looks conventional, not required; what red does in the shader is not verified. Pick the value by the highlight you want: green is its strength and blue its tightness.

## Without DayZ Tools

On a machine with no ImageToPAA (Linux, macOS, a clean Windows), `skills/_shared/vehicles/png-to-paa-encoding.md` holds a pure Python DXT1 writer for opaque `_co` textures and describes the `.paa` file layout. It is tool notes that were not run here; `/dayz-pack-texture` stays the normal route.

## Images ImageToPAA refuses

`/dayz-pack-texture` checks the suffix, the extension and the size from the file header. These pass a header check and still fail in ImageToPAA with `Error (Loading of img failed)`:

| Input | Checked | Fix |
|---|---|---|
| A TGA with RLE compression (image type 10) | 2026-11-17: exit code 1 and no `.paa`; the same pixels uncompressed convert | Save it uncompressed |
| A PNG with 16 bits per channel | 2026-11-17 with a greyscale file: exit code 1 and no `.paa` | Export 8 bits per channel |
| A PNG saved by Blender (extra EXIF, gamma and chromaticity data) | Reported by one mod project, not rechecked | Save it again with an image library or editor |

The measurements, the reverse conversion and more cases are in `dayz-texture-pipeline/references/baked-atlas-to-paa.md`.
