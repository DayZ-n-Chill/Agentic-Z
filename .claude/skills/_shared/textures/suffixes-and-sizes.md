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

The other suffixes `/dayz-pack-texture` accepts (`_lco`, `_lca`, `_no`, `_non`, `_nopx`, `_sm`, `_ads`, `_adshq`, `_mco`, `_detail`, `_cdt`, `_dtsmdi`, `_mask`, `_sky`) are for terrain, vegetation, buildings and the sky. The full list and the reason for it are in `_shared/conventions/assets.md`.

Thermal textures are named `<name>_ti_ca.paa` (for example `P:\DZ\characters\tops\data\pcu5jacket_ti_ca.paa`). They pack as `_ca` and go in `StageTI` (see `rvmat-stages.md`).

## Sizes

Every side must be a power of two (64, 128, 256, 512, 1024, 2048). The two sides may differ. A header scan of the vanilla `.paa` files shows what vanilla picks:

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
