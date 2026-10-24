# rvmat keys, shaders and stages

What each key and stage of a DayZ `.rvmat` does, for the two shaders mod items use: Super (gear, weapons, clothing, vehicles) and Skin (character bodies and heads).

## Contents

- [Which shader](#which-shader)
- [The keys above the stages](#the-keys-above-the-stages)
- [Super stages](#super-stages)
- [Skin stages](#skin-stages)
- [Damage and destruct materials](#damage-and-destruct-materials)
- [Thermal stage](#thermal-stage)

## Which shader

`PixelShaderID` and `VertexShaderID` name the shader. A scan of the 34,899 `.rvmat` files under `P:\DZ` finds:

| Shader pair | Files | Used for |
|---|---|---|
| `Super` / `Super` | 5,838 | Every item, weapon, piece of clothing, vehicle part and most building parts |
| `Skin` / `Skin` | 244 | Character bodies and heads under `P:\DZ\characters\heads\data\` |
| `SuperHair` / `Super` | 128 | Hair and fur |
| `Multi` / `Multi` | 1,960 | Building surfaces that blend several layers |
| `TerrainX` / `Terrain` | 25,030 | Terrain layers, made by Terrain Builder |

A mod item uses Super. Use Skin only for a new character body or head, and copy a vanilla head material when you do. The other shaders belong to map and building work, not to this pack.

## The keys above the stages

From `P:\DZ\characters\tops\data\bomberjacket.rvmat`:

```cpp
ambient[]={1,1,1,1};
diffuse[]={1,1,1,1};
forcedDiffuse[]={0,0,0,0};
emmisive[]={0,0,0,1};
specular[]={1,1,1,1};
specularPower=100;
PixelShaderID="Super";
VertexShaderID="Super";
```

| Key | What to do with it |
|---|---|
| `ambient[]`, `diffuse[]` | Leave at `{1,1,1,1}` on Super items. The color comes from the texture. |
| `forcedDiffuse[]` | Leave at `{0,0,0,0}`. Vanilla raises it only on thin see-through parts such as `P:\DZ\gear\tools\data\flashlight_glass.rvmat`. |
| `emmisive[]` | Leave at `{0,0,0,1}` unless the part glows. Vanilla spells the key `emmisive`; keep that spelling. |
| `specular[]` | Highlight color and strength, multiplied with the `_smdi`. |
| `specularPower` | Highlight tightness. Low for cloth, high for metal and glass (values per surface in `surface-recipes.md`). |
| `renderFlags[]` | Optional. Vanilla glass sometimes adds `"NoZWrite"` (for example `P:\DZ\characters\headgear\data\riothelmet_glass.rvmat`). |

## Super stages

Every stage is a `class StageN` with a `texture` and a `uvSource`. Stages 1 to 5 and 7 use `uvSource="tex"` with this identity `uvTransform`; Stage6 uses `uvSource="none"` and has no `uvTransform`:

```cpp
class Stage1
{
	texture="MyMod\data\vest_nohq.paa";
	uvSource="tex";
	class uvTransform
	{
		aside[]={1,0,0};
		up[]={0,1,0};
		dir[]={0,0,0};
		pos[]={0,0,0};
	};
};
```

| Stage | Holds | Neutral value when empty |
|---|---|---|
| (none) | The `_co` or `_ca` comes from the model face or `hiddenSelectionsTextures[]`, not from the rvmat | |
| `Stage1` | Normal map `_nohq` | `#(argb,8,8,3)color(0.5,0.5,1,1,NOHQ)` |
| `Stage2` | Detail `_dt` | `#(argb,8,8,3)color(0.5,0.5,0.5,1,DT)` |
| `Stage3` | Macro `_mc` | `#(argb,8,8,3)color(0,0,0,0,MC)` |
| `Stage4` | Ambient shadow `_as` | `#(argb,8,8,3)color(1,1,1,1,AS)` |
| `Stage5` | Specular `_smdi` | `#(argb,8,8,3)color(1,1,1,1,SMDI)` |
| `Stage6` | Fresnel, always procedural | `#(ai,64,64,1)fresnel(n,k)` |
| `Stage7` | Environment (reflection) map | `dz\data\data\env_land_co.paa`, or `#(argb,8,8,3)color(0,0,0,1,CO)` for none |
| `StageTI` | Thermal texture `_ti_ca` (optional) | leave the stage out |

Keep all seven numbered stages, even when most hold placeholders. In the clothing, weapon, tool and glasses folders every vanilla Super material has Stage1 to Stage7. A `Stage0` with the color texture appears only on some glass, glowing and vehicle parts (for example `riothelmet_glass.rvmat` and `P:\DZ\gear\tools\data\flashlight_glass.rvmat`); ordinary gear does not need it.

The fresnel numbers set how the highlight grows at a grazing angle. Copy them from the vanilla material you based yours on rather than inventing them. Common values by folder are in `surface-recipes.md`.

## Skin stages

Skin puts the color texture inside the material and has no Stage7. All 244 Skin materials under `P:\DZ\characters\heads\data\` use these stage roles, for example `P:\DZ\characters\heads\data\m_adam\hhl_m_adam_body_shaved.rvmat`:

| Stage | Holds |
|---|---|
| `Stage1` | Normal map `_nohq` |
| `Stage2` | Macro: the empty placeholder, or a blood or injury `_mc` such as `dz\characters\heads\data\bloodyhands_mc.paa` |
| `Stage3` | Color `_co` |
| `Stage4` | Ambient shadow, usually `#(argb,8,8,3)color(1,1,1,1,AS)` |
| `Stage5` | Specular `_smdi` |
| `Stage6` | Fresnel, `fresnel(0.5,0.3)` in 240 of the 244 |

The `ambient`, `diffuse`, `forcedDiffuse` and `emmisive` values of a Skin material are tuned per head and are far from the Super defaults (`hhl_m_adam_body_shaved.rvmat` has `ambient[]={2,2,2,1}`). Copy them from the nearest vanilla head and change only the texture paths.

## Damage and destruct materials

Vanilla items swap material as they lose health. The config lists one material set per health level in `healthLevels[]`, for example `class TacticalGoggles` at `P:\DZ\characters\glasses\config.cpp:598`:

| Health level | Material |
|---|---|
| `1` and `0.7` | `TacGoggles.rvmat` (pristine and worn) |
| `0.5` and `0.3` | `TacGoggles_damage.rvmat` (damaged and badly damaged) |
| `0` | `TacGoggles_destruct.rvmat` (ruined) |

Write three materials per surface: `<name>.rvmat`, `<name>_damage.rvmat` and `<name>_destruct.rvmat`. Comparing `P:\DZ\characters\tops\data\bomberjacket.rvmat` with its `_damage` and `_destruct` files shows what changes:

- `Stage3` points at a shared wear macro instead of the empty placeholder: `dz\characters\tops\data\tops_damage_mc.paa` and `dz\characters\tops\data\tops_destruct_mc.paa`. Weapons, gear and other clothing folders have their own; Grep the folder for `_damage_mc` and `_destruct_mc`.
- `specular[]` drops to `{0.47450981,0.47450981,0.47450981,1}` and `specularPower` from 100 to 55.
- `Stage6` becomes `fresnel(1.28,0.5)` and `Stage7` becomes `#(argb,8,8,3)color(0.15,0.15,0.15,1,CO)`, so the worn item stops reflecting.
- Stages 1, 2, 4 and 5 keep the item's own textures.

Pointing a mod's damage materials at the vanilla wear macro is fine; the path stays `dz\...`. The `healthLevels[]` entry itself is config work for the worker who owns the item's class: dayz-wearables-specialist for clothing, gear and characters, dayz-vehicle-specialist for vehicles, dayz-weapon-specialist for weapons, and dayz-config-specialist for anything else.

## Thermal stage

`StageTI` gives the item its look through thermal optics. 18 of the 99 pristine `characters\tops` materials have one, for example `P:\DZ\characters\tops\data\pcu5jacket.rvmat`:

```cpp
class StageTI
{
	texture="dz\characters\tops\data\pcu5jacket_ti_ca.paa";
};
```

It is optional. Leave it out unless the user asks for a thermal look, or reuse a vanilla `_ti_ca` from the same folder.
