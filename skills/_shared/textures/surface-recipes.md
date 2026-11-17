# Surface recipes: cloth, metal, glass, skin

Which vanilla material to copy for each kind of surface, and the values vanilla uses there. Copy the whole file into the mod's `data\` folder, change the texture paths to the mod's `$PBOPREFIX$`, then change only the values below. Never edit a vanilla file on `P:\`.

The numbers come from a scan of the pristine Super materials in each folder (damage and destruct files left out). The middle range is where half of the vanilla files sit.

## Cloth

Start from `P:\DZ\characters\tops\data\hoodie.rvmat` (soft fabric) or `P:\DZ\characters\vests\data\ballisticvest.rvmat` (heavy webbing).

| Folder under `P:\DZ` | Files | `specularPower` median (middle range) | Most common fresnel |
|---|---|---|---|
| `characters\tops` | 99 | 55 (50 to 70) | `fresnel(1,0.7)` (20), `fresnel(1.37,0.25)` (15) |
| `characters\pants` | 63 | 55 (45 to 80) | `fresnel(1.37,0.25)` (19) |
| `characters\vests` | 17 | 70 (65 to 80) | `fresnel(1,0.7)` (11) |

- Keep the highlight weak in the `_smdi` (dark green, dark blue). `ballisticvest.rvmat` also lowers `specular[]` to about 0.33 with `specularPower=20`.
- An `_as` is worth baking for clothing with folds: `hoodie.rvmat` has `hoodie_as.paa` in `Stage4`, and 38 of the 99 tops materials and 34 of the 63 pants materials use a real `_as`. The rest keep the placeholder.
- `Stage7` stays `dz\data\data\env_land_co.paa` (71 of the 99 tops); the `_smdi` keeps cloth from looking wet.
- Leave `Stage3` empty. Macro textures on clothing are mostly the shared damage macros (`rvmat-stages.md`).

## Metal

Start from `P:\DZ\weapons\firearms\akm\data\akm.rvmat` (gun steel with a macro texture) or `P:\DZ\gear\tools\data\crowbar.rvmat` (worn tool steel with a baked `_as`).

| Folder under `P:\DZ` | Files | `specularPower` median (middle range) | Most common fresnel |
|---|---|---|---|
| `weapons\firearms` | 94 | 120 (100 to 200) | `fresnel(0.7,0.8)` (31) |
| `gear\tools` | 72 | 100 (about 75 to 150) | `fresnel(0.7,0.8)` (10) |

- `akm.rvmat`: `specular[]={0.79000002,0.75,0.74000001,1}`, `specularPower=70`, `akm_mc.paa` in `Stage3`, `fresnel(0.8,0.7)`, `env_land_co.paa` in `Stage7`.
- `crowbar.rvmat`: `specular[]` near 0.27, `specularPower=50`, `crowbar_as.paa` in `Stage4`, `#(ai,32,128,1)fresnel(2.9,3)`.
- Polished metal gets a brighter `_smdi` and a higher `specularPower`; rusty or painted metal gets a darker `_smdi` and stays near 50 to 100.
- Optics and lenses on weapons use `dz\data\data\env_land_optic_co.paa` in `Stage7` (23 of the 94 firearms materials).
- A mod gun that changes a vanilla gun's look keeps the vanilla material's stages and swaps only the textures.
- Pick the `Stage7` environment map by how strong the highlight is. DayZ ships 21 of them in `P:\DZ\data\data\` (`env_co.paa` and twenty named `env_*_co.paa`). `env_land_optic_co.paa` has an olive ground half, so a bright silver or mirror surface under it can read olive in game (one mod's report); `env_land_chrome_co.paa` is neutral. The measured colors of six of the maps are in `dayz-texture-pipeline/references/rvmat-cookbook.md`.

### Vehicle paint

- Start from the nearest vanilla vehicle body, for example `P:\DZ\vehicles\wheeled\civiliansedan\data\civiliansedan.rvmat` (`specularPower=200`) or the motorbike's, which sets `specular[]={1.1,1.1,1.1,1}` and `specularPower=160` (`P:\DZ\vehicles\singletrack\Motorbike_02\data\motorbike_02_body.rvmat:5-6`).
- Vanilla paint is far darker in the `_smdi` than it looks. Measured on that motorbike's red body texture (one mod project, 2026-11-02): the red paint has a green median of 5 out of 255 and half of the whole body's texels have green at 4 or less; the bright values sit only on bare metal. Measure the vanilla asset nearest to yours before painting an `_smdi`; the tables are in `dayz-texture-pipeline/references/map-conventions.md`.
- A part with one flat color and no color texture on its faces does not use Super. See the constant color shader in `rvmat-stages.md`.
- Color variants are one texture per variant on a `color` hidden selection: `dayz-texture-pipeline/references/vehicle-materials-and-color-variants.md`. The vehicle's config belongs to dayz-vehicle-specialist.

## Glass

Glass is the Super shader too. What makes it see-through is the alpha channel of its color texture, so the color texture must be `_ca`, not `_co`, for example `P:\DZ\vehicles\wheeled\data\hatchback_glass_ca.paa`. The `_ca` comes from the model face or `hiddenSelectionsTextures[]`, or sits in `Stage0` of the material.

Pick the vanilla file nearest to your glass:

| Glass | Start from | What it shows |
|---|---|---|
| Vehicle window | `P:\DZ\vehicles\wheeled\data\auta_skla.rvmat` | Every stage a placeholder, `Stage6` `#(ai,64,64,1)fresnelGlass(1.9)`, `specularPower=200`, a `StageTI` |
| Visor with its own texture | `P:\DZ\characters\headgear\data\riothelmet_glass.rvmat` | `Stage0` holds `riothelmet_glass_ca.paa`, `renderFlags[]={"noZwrite"}`, `fresnelGlass()` |
| Goggle lens | `P:\DZ\characters\glasses\data\tacgoggles_glass.rvmat` | Its own `_nohq` and `_smdi`, `specularPower=1000`, plain `fresnel(0.78,1.16)` |
| Small lamp or lens | `P:\DZ\gear\tools\data\flashlight_glass.rvmat` | A procedural `Stage0` with alpha 0.1, `forcedDiffuse` raised, `"NoZWrite"` |

- 191 pristine vanilla materials use `fresnelGlass` in `Stage6`. Use it for windows and visors.
- Glass wants a strong highlight: a bright `_smdi` or the `#(argb,8,8,3)color(1,1,1,1,SMDI)` placeholder, and `specularPower` of 200 or more.
- Glass that breaks gets its own `_damage` and `_destruct` materials, like `tacgoggles_glass_damage.rvmat`; the item config lists them in `healthLevels[]` beside the frame material (`P:\DZ\characters\glasses\config.cpp:598`).
- Frame and glass are two materials on two sets of faces. Ask dayz-object-builder for separate selections when the model has only one.
- A decal with alpha that lies on paint (a sticker, a label) is not a window. Copy the offroad's sticker material, which is Super with `renderFlags[]` holding `"nozwrite"` (`P:\DZ\vehicles\wheeled\offroad_02\data\offroad_02_decals.rvmat:7-12`). One mod project reports that its labels rendered opaque until that flag was added.
- A glowing lens or lamp face is an on and off material pair that differs in `emmisive[]` (`rvmat-stages.md`).

## Skin

Only character bodies and heads use the Skin shader. Clothing never does, even where it shows bare skin.

- Start from the vanilla head of the same sex nearest to yours, for example `P:\DZ\characters\heads\data\m_adam\hhl_m_adam_body_shaved.rvmat`.
- The color texture goes in `Stage3`, not on the model face (stage table in `rvmat-stages.md`).
- Keep the vanilla `ambient[]`, `diffuse[]`, `forcedDiffuse[]`, `emmisive[]`, `specular[]` and `specularPower` (30 in `hhl_m_adam_body_shaved.rvmat`). They are tuned for skin, not defaults.
- Keep `fresnel(0.5,0.3)`, which 240 of the 244 vanilla Skin materials use.
- Blood and injury versions swap `Stage2` to a blood or wound macro: `P:\DZ\characters\heads\data\f_baty\hhl_f_baty_body_bloodyhands.rvmat` differs from `hhl_f_baty_body.rvmat` only there. A new character usually needs one per vanilla variant it copies.
- A new survivor body is more than a material. Hand the config and model side to dayz-wearables-specialist through the art lead (`_shared/wearables/references/characters.md`).
