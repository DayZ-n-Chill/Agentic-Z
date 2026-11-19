# Material patterns from mods

Which material a generated or imported model reaches for after the basic Super material: flat colors without a bake, a damage overlay that shows wear, an on and off pair for lit panels, glass, and a very bright emissive. Read `rvmat-stages.md` first; it holds the stage by stage reference.

The damage overlay and the dashboard swap are read from vanilla files on `P:\`. The other patterns were read on mod aircraft, a mod car and a mod hangar (third-party mod behaviour, not vanilla), and are reusable beyond aircraft.

## Flat colors: one material per color, no atlas bake

For a single colored model, or one flat color per piece, use one `.rvmat` per material with `diffuse[]` set to the base color and `texture=""`. It needs no UVs and leaves no gaps. Baking many flat materials into one UV atlas leaves black holes and smudges; keep atlas bakes for models with real texture detail.

## Damage that shows wear, not only a tint

When damage shows only as a color tint, the `_damage.rvmat` has a procedural `color()` texture in `Stage3` where vanilla puts an overlay texture. The vanilla wooden case uses `texture="dz\weapons\data\weapons_damage_wood_mc.paa"` in `Stage3` of its damage material (`P:\DZ\gear\camping\data\wooden_case_damage.rvmat:35`), tiled four times with the axes swapped, `aside[]={0,4,0}` and `up[]={4,0,0}` (`:39` and `:40`). Its destruct material uses `weapons_destruct_wood_mc.paa` the same way (`P:\DZ\gear\camping\data\wooden_case_destruct.rvmat:35`). For metal use `weapons_damage_metal_mc.paa` and `weapons_destruct_metal_mc.paa` from the same folder, `P:\DZ\weapons\data\`.

## Lit panels: an on and off pair

A dashboard, control panel or display with an on and an off state uses two materials that differ in two places only. One mod's pair:

| Key | `Controls.rvmat` (off) | `Controls_on.rvmat` (on) |
|---|---|---|
| `ambient[]`, `diffuse[]` | `{0.9999992,...}` | same |
| `forcedDiffuse[]` | `{0,0,0,1}` | `{0.1,0.1,0.1,1}`, a slight glow |
| `specular[]`, `specularPower` | `{0.882,...}`, `55` | same |
| `Stage5` | `...controls_SMDI.paa` | `...controls_on_SMDI.paa`, with the lit elements |

Everything else is identical. The swap itself is vanilla: `dashboardMatOn` and `dashboardMatOff` are vanilla vehicle config keys (`P:\DZ\vehicles\wheeled\config.cpp:1336` and `:1337` on the offroad hatchback), and `CarScript` and `MotorbikeScript` register them with their `VehicleLightsComponent`, which swaps the dashboard material along with the lights (`P:\scripts\4_world\entities\vehicles\carscript.c:230` and `:231`; `P:\scripts\4_world\entities\vehicles\motorbikescript.c:121` and `:122`). A config class that inherits `CarScript` only sets the two keys:

```cpp
class MyMod_Plane: CarScript
{
	dashboardMatOn="MyMod\MyPlane\data\Controls_on.rvmat";
	dashboardMatOff="MyMod\MyPlane\data\Controls.rvmat";
};
```

Related vehicles can share one pair; one vehicle's config may name another's materials directly.

## Glass

The see-through part comes from the alpha of the `_ca` color texture, not from the material (`surface-recipes.md`, "Glass"). One mod's glass material:

```cpp
ambient[]={0.55,0.55,0.55,1};
diffuse[]={0.45,0.45,0.45,1};
forcedDiffuse[]={0,0,0,1};
emmisive[]={0,0,0,1};
specular[]={0.25,0.25,0.25,1};
specularPower=1320;
renderFlags[]={"noZwrite"};
PixelShaderID="Super";
VertexShaderID="Super";
class Stage1 { texture="#(argb,8,8,3)color(0.5,0.5,1,1,NOHQ)"; };
class Stage4 { texture="#(argb,8,8,3)color(1,1,1,1,AS)"; };
class Stage5 { texture="#(argb,8,8,3)color(1,1,1,1,SMDI)"; };
class Stage6 { texture="#(ai,64,64,1)fresnel(1,0)"; uvSource="tex1"; };
class Stage7 { texture="dz\data\data\env_land_chrome_co.paa"; };
```

- `renderFlags[]={"noZwrite"}` is that mod's choice, not a need. Some vanilla glass sets it, such as `P:\DZ\characters\headgear\data\firehelmetvisor.rvmat:9` to `:12`, whose `specularPower` is 200; vanilla car glass does not (`P:\DZ\vehicles\wheeled\data\auta_skla.rvmat` has no `renderFlags[]`, and `rvmat-stages.md` says a window needs none). A see-through window needs a `_ca` whose alpha is not white.
- `specularPower=1320` is far above the mod's opaque materials, which sit around 50 to 200.
- The normal, ambient shadow and `_smdi` stages hold procedural placeholders rather than real textures.
- `Stage7` uses the chrome environment map, not `env_land_co.paa`, for a stronger reflection.
- The `fresnel(1,0)` stage gives a softer edge fall-off than the mod's opaque materials, which use `fresnel(1.1,0.3)`. That value is rare in vanilla: 25 materials under `P:\DZ` use it, all vehicle wrecks under `structures\wrecks` and `structures_takistan\Wrecks`, such as `P:\DZ\structures\wrecks\vehicles\data\wreck_mtvr_cargo.rvmat:71`.

## A damage variant with its own overlay

A mod engine material and its damaged copy share the base textures and change these values:

| Key | `engine.rvmat` | `engine_scratch_damagex1.rvmat` |
|---|---|---|
| `ambient[]`, `diffuse[]` | `{0.9999,...}` | `{0.634,...}`, darker |
| `specular[]` | `{0.882,...}` | `{0.392,...}`, weaker |
| `specularPower` | `55` | `85`, sharper on worn metal |
| `Stage2` | the base detail | `DZ\data\data\detail_maps\plastic1_512_dt.paa`, a vanilla detail map |
| `Stage3` | `#(argb,8,8,3)color(0,0,0,0,mc)` | `<mod>\<aircraft>\data\damage_layer_mc.paa` |

The overlay is one `damage_layer_mc.paa` per aircraft that lays scratches and blackening over the base color. The mod ties it to the damage zone through `healthLevels[]`, where an empty list keeps the base material:

```cpp
healthLevels[]=
{
	{1.0,{}},
	{0.7,{}},
	{0.5,{}},
	{0.3,{"<path>/engine_scratch.rvmat"}},
	{0.0,{"<path>/engine_scratch_damagex1.rvmat"}}
};
```

This example declares no `RefTexsMats[]`. Vanilla vehicle damage zones do declare that list, for example `RefTexsMats[]` at `P:\DZ\vehicles\wheeled\config.cpp:978`; what it is and which zones carry it is in the vehicles pack (`_shared/vehicles/damage.md` and `_shared/vehicles/vehicle-damage-and-glass.md`). Whether a swap reaches its faces is judged in game, never from the materials or the config (`_shared/vehicles/process-gates.md`, "A config check is not a visual check"). A windscreen section in a damage zone of 67 sections never hid on a wreck, although its material sat in the zone's `RefTexsMats[]` slot and the section sat inside `dmgzone_front` as on the vanilla motorbike (`_shared/vehicles/vehicle-damage-and-glass.md`, "A windscreen that never hid").

## Keep all seven Super stages

A Super material has seven stages in this order: normal, detail, macro, ambient shadow, `_smdi`, fresnel, environment map, as in vanilla's `P:\DZ\gear\camping\data\wooden_case.rvmat` (its `_as` sits at `:47` and its `_smdi` at `:59`). A mod car body material drops the ambient shadow stage and moves everything up one: `_smdi` in Stage4, fresnel in Stage5, the environment map in Stage6, plus a thermal stage. No vanilla file on `P:\` does this, and it breaks the stage numbering in `rvmat-stages.md`. Never copy it: write all seven stages, with the placeholder `#(argb,8,8,3)color(1,1,1,1,AS)` in Stage4 when there is no ambient shadow map.

## A very bright emissive

For fluorescent tubes or LEDs that glow even in daylight, a mod hangar sets every color array above 1:

```cpp
ambient[]={10,10,10,10};
diffuse[]={10,10,10,10};
forcedDiffuse[]={10,10,10,10};
emmisive[]={10,10,10,10};
specular[]={10,10,10,10};
specularPower=100;
```

Its `Stage5` also tiles the `_smdi` five times (`aside[]={5,0,0}`, `up[]={0,5,0}`) for finer detail. Values far above 1 are vanilla practice too: the sedan's lit lights use `emmisive[]={1,1,1,120}` (`P:\DZ\vehicles\wheeled\sedan_02\data\sedan_02_lights_e.rvmat:4`).

The material only makes itself look bright; it lights nothing around it. When nearby surfaces must be lit too, add a real `CarLightBase` or `PointLightBase`. An LED screen that must glow from far away and also cast light uses both, with a script controlled `PointLightBase` matched to it.
