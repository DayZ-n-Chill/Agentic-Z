# rvmat patterns for generated models

Material recipes this skill reaches for after the basic Super material: flat colors without a texture bake, a damage overlay, an on and off pair for lit panels, glass, a six stage variant and a very bright emissive. The stage by stage reference for a `.rvmat` is `_shared/textures/rvmat-stages.md`; read that first. The damage overlay is read from vanilla files on `P:\`. The other patterns are third-party mod behaviour, not vanilla, and are marked as such.

## Flat color models: one .rvmat per material, not a UV atlas bake

For monochrome models, or models with one flat color per piece, use one `.rvmat` per material with `diffuse[]` set to the
base color and `texture=""` (no UVs needed, no gaps). A UV atlas bake of many flat materials yields
black holes and smudges. Atlas baking is for models with real texture detail.

## Damage that shows as cracks and wear, not only a tint

When damage shows only as a color tint, the `_damage.rvmat` has a procedural `color()` texture in `Stage3` instead of the vanilla overlay texture. Vanilla's wooden case uses `texture="dz\weapons\data\weapons_damage_wood_mc.paa"` in `Stage3` of its damage material (`P:\DZ\gear\camping\data\wooden_case_damage.rvmat:35`), tiled four times with the axes swapped: `aside[]={0,4,0}` and `up[]={4,0,0}` (`P:\DZ\gear\camping\data\wooden_case_damage.rvmat:39` to `:40`). Its destruct material uses `weapons_destruct_wood_mc.paa` the same way (`P:\DZ\gear\camping\data\wooden_case_destruct.rvmat:35`). For metal use `weapons_damage_metal_mc.paa` and `weapons_destruct_metal_mc.paa`, which sit in the same folder, `P:\DZ\weapons\data\`.

## Third-party mod patterns (not vanilla)

These patterns are third-party mod behaviour, not vanilla, read on aircraft, a car and a hangar on 2026-05-23. They were applied to aircraft there but are reusable in general. The exception is the dashboard material swap, whose config properties and script are vanilla (see the toggle pattern below).

### Toggle rvmat pattern (lights on/off without duplicating material)

For dashboards, control panels, displays that have an "on" and "off" state, create **two near-identical rvmats** with minimal diff:

```
Controls.rvmat (lights off)           Controls_on.rvmat (lights on)
ambient[]      = {0.9999992,...}     ambient[]      = {0.9999992,...}    SAME
diffuse[]      = {0.9999992,...}     diffuse[]      = {0.9999992,...}    SAME
forcedDiffuse[] = {0,0,0,1}      →   forcedDiffuse[] = {0.1,0.1,0.1,1}   DIFFERS (slight emissive boost)
specular[]     = {0.882,...}         specular[]     = {0.882,...}         SAME
specularPower  = 55                  specularPower  = 55                  SAME

Stage5 SMDI:
  texture = "...controls_SMDI.paa"   texture = "...controls_on_SMDI.paa"  DIFFERS

Everything else identical.
```

**Pattern**: only `forcedDiffuse` (controls overall brightness) + Stage5 SMDI texture (specular/material mask with glowing elements) differ. This two-rvmat diff was read on a mod. The swap itself is vanilla: `dashboardMatOn` and `dashboardMatOff` are vanilla CfgVehicles properties (for example `P:\DZ\vehicles\wheeled\config.cpp:1336-1337` on the offroad hatchback), and vanilla `CarScript` and `MotorbikeScript` register them with their `VehicleLightsComponent`, which swaps the dashboard material with the lights (`P:\scripts\4_world\entities\vehicles\carscript.c:230-231`, `P:\scripts\4_world\entities\vehicles\motorbikescript.c:121-122`). A class that inherits `CarScript` only sets the two properties:

```cpp
class MyPlane: CarScript {
    dashboardMatOn  = "MyMod\MyPlane\data\Controls_on.rvmat";
    dashboardMatOff = "MyMod\MyPlane\data\Controls.rvmat";
    ...
};
```

Related vehicles can share the pair: the config of one aircraft can name the rvmats of another directly.

### Glass rvmat distinctives

Transparency comes from the alpha of the `_ca` color texture, not from the rvmat (`_shared/textures/surface-recipes.md`, "Glass"). The values below are one mod's glass material:

```cpp
ambient[]      = {0.55,0.55,0.55,1};
diffuse[]      = {0.45,0.45,0.45,1};
forcedDiffuse[] = {0,0,0,1};
emmisive[]     = {0,0,0,1};
specular[]     = {0.25,0.25,0.25,1};
specularPower  = 1320;                      // HIGH — glassy reflection
renderFlags[]  = {"noZwrite"};              // optional; this mod's choice
PixelShaderID  = "Super";
VertexShaderID = "Super";

class Stage1 { texture = "#(argb,8,8,3)color(0.5,0.5,1,1,NOHQ)"; ... };  // procedural normal
class Stage4 { texture = "#(argb,8,8,3)color(1,1,1,1,AS)"; ... };          // procedural AS
class Stage5 { texture = "#(argb,8,8,3)color(1,1,1,1,SMDI)"; ... };        // procedural SMDI
class Stage6 { texture = "#(ai,64,64,1)fresnel(1,0)"; uvSource = "tex1"; ... };  // softer fresnel for glass
class Stage7 { texture = "dz\data\data\env_land_chrome_co.paa"; ... };     // CHROME env map, not env_land
```

Some vanilla glass sets the same flag: `renderFlags[]` with `"noZwrite"` in `P:\DZ\characters\headgear\data\firehelmetvisor.rvmat:9` to `:12` (its `specularPower` is 200, lower than the 1320 above). Vanilla car glass does not: `P:\DZ\vehicles\wheeled\data\auta_skla.rvmat` has no `renderFlags[]`.

Key points:
- `renderFlags[] = {"noZwrite"}` is optional. A window does not need it (`_shared/textures/rvmat-stages.md`); a see-through window needs a `_ca` color texture with a non-white alpha
- `specularPower = 1320` — much higher than opaque materials (typical 50-200)
- Glass usually omits real textures for Stage4/5 (uses procedural `color(...)` placeholders)
- Stage7 uses `env_land_chrome_co.paa` for reflective chrome look, not the regular `env_land_co.paa`
- Stage6 fresnel `(1,0)` softer than standard `(1.1,0.3)` — glass has subtle edge fall-off

### Damage variant rvmat pattern

For materials that should look damaged/scratched/burnt at higher damage levels, create a damage variant with same texture base + overlay:

```cpp
// engine.rvmat (normal)                    engine_scratch_damagex1.rvmat (damaged)
ambient[]    = {0.9999,...};                 ambient[]    = {0.634,...};         REDUCED
diffuse[]    = {0.9999,...};                 diffuse[]    = {0.634,...};         REDUCED
specular[]   = {0.882,...};                  specular[]   = {0.392,...};         REDUCED
specularPower = 55;                          specularPower = 85;                  HIGHER (worn = sharper specular)

// Stage1-2: same base textures
// Stage3 (Macro Color) is the KEY:
Stage3 normal:  "#(argb,8,8,3)color(0,0,0,0,mc)"
Stage3 damaged: "<mod>\<aircraft>\data\damage_layer_mc.paa"   // CUSTOM damage overlay

// Stage2 detail (worn material reuses vanilla DZ texture):
Stage2 damaged: "DZ\data\data\detail_maps\plastic1_512_dt.paa"   // Reuse vanilla
```

**Pattern**: damage variants share base texture set, swap Stage3 (Macro Color) for a damage overlay texture, reduce color values to simulate burn/wear. The damage overlay is a single `damage_layer_mc.paa` per aircraft that overlays scratches/blackening on top of the base diffuse.

Tied to `DamageSystem` zones via `healthLevels[]`:

```cpp
healthLevels[] = {
    {1.0, {}},                                     // pristine: base rvmat
    {0.7, {}},
    {0.5, {}},
    {0.3, {"<path>/engine_scratch.rvmat"}},        // damaged level 1
    {0.0, {"<path>/engine_scratch_damagex1.rvmat"}} // damaged level 2 / destroyed
};
```

This example declares no `RefTexsMats[]`. Vanilla vehicle damage zones do declare that list (for example `RefTexsMats[]` at `P:\DZ\vehicles\wheeled\config.cpp:978`); what it is and which zones carry it is vehicle material, in the vehicles pack (`_shared/vehicles/damage.md` and `_shared/vehicles/vehicle-config-and-modelcfg.md`). Whether a swap reaches its faces is
judged in game, not from the rvmats or the config (`skills/_shared/vehicles/process-gates.md`, "A config gate is not a visual gate"). That file records a glass section
that never hid although config and ODOL
matched the vanilla motorbike glass slot in the two respects checked (glass rvmat in its `RefTexsMats[]`
slot, section inside `dmgzone_front`), with a zone of 67 sections against two to five in vanilla.

### 6-stage rvmat layout (AS stage dropped): not checked on P:\

A standard Super rvmat has 7 stages (NOHQ, DT, MC, AS, SMDI, Fresnel, env), the order of vanilla's `P:\DZ\gear\camping\data\wooden_case.rvmat`. A 6-stage layout read on a car body material drops the AS stage and moves SMDI up to Stage4:

```
Stage1=NOHQ, Stage2=DT, Stage3=MC, Stage4=SMDI, Stage5=Fresnel, Stage6=env (combined), StageTI=thermal
```

This layout is not checked on `P:\` and departs from the seven-stage Super rule in `_shared/textures/rvmat-stages.md` (Stage4 is AS, Stage5 is SMDI, and all seven numbered stages are kept even when most hold placeholders). Do not use it: write all seven stages, with the AS placeholder `#(argb,8,8,3)color(1,1,1,1,AS)` in Stage4 when the material has no ambient shadow map.

### HDR emissive trick (super-bright lights)

For materials that simulate fluorescent lamps / bright LEDs glowing visibly even in daylight, use values **>1.0** across all stages — engine accepts HDR-range values:

```cpp
ambient[]       = {10,10,10,10};
diffuse[]       = {10,10,10,10};
forcedDiffuse[] = {10,10,10,10};
emmisive[]      = {10,10,10,10};
specular[]      = {10,10,10,10};
specularPower   = 100;
// Plus Stage5 SMDI uvTransform aside/up = {5,0,0}/{0,5,0} (texture scale 5x for finer detail)
```

This produces a glowing material without needing point light objects: it is purely material based. It was read on the fluorescent lamps of a hangar model. Tradeoff: no actual illumination on nearby surfaces (no dynamic light cast), just the material itself appears very bright. Combine with a real `CarLightBase` or `PointLightBase` if you need surfaces lit too.

For LED screens that need both a glow visible from far away and dynamic light, use this trick plus a script controlled `PointLightBase` to match.
