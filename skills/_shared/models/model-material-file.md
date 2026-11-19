# A model's material file

What a Super shader `.rvmat` for a new model holds, stage by stage, which texture suffix goes where, and how a part is made to glow. The stage by stage reference with every vanilla variant is `_shared/textures/rvmat-stages.md`; the full suffix list is in `_shared/conventions/assets.md`, and `/dayz-pack-texture` turns a `.png` into a `.paa`.

## Seven stages in a fixed order

A Super material has seven stages, and each one feeds a fixed input of the shader. Vanilla puts the macro map in `Stage3` and the specular map in `Stage5` (`P:\DZ\gear\camping\data\wooden_case.rvmat:35` and `:59`), so a three stage file with the specular map in `Stage3` feeds the wrong map to the shader.

| Stage | Holds | Wooden case |
|---|---|---|
| `Stage1` | Normal map `_nohq` | `wooden_case_nohq.paa` (`wooden_case.rvmat:11`) |
| `Stage2` | Detail map, or a `DT` placeholder | `#(argb,8,8,3)color(0.5,0.5,0.5,0.5,DT)` (`:23`) |
| `Stage3` | Macro map, or an `MC` placeholder | `#(argb,8,8,3)color(0,0,0,0,MC)` (`:35`) |
| `Stage4` | Ambient shadow `_as`, or an `AS` placeholder | `wooden_case_as.paa` (`:47`) |
| `Stage5` | Specular map `_smdi` | `wooden_case_smdi.paa` (`:59`) |
| `Stage6` | Fresnel | `#(ai,32,128,1)fresnel(1.61,0.22)` (`:71`) |
| `Stage7` | Environment map | `dz\data\data\env_land_co.paa` (`:76`) |

A starting file in that layout:

```cpp
ambient[] = {1.0, 1.0, 1.0, 1.0};
diffuse[] = {1.0, 1.0, 1.0, 1.0};
forcedDiffuse[] = {0.0, 0.0, 0.0, 1.0};
emmisive[] = {0.0, 0.0, 0.0, 1.0};
specular[] = {0.3, 0.3, 0.3, 1.0};
specularPower = 80;
PixelShaderID = "Super";
VertexShaderID = "Super";

class Stage1
{
    texture = "my_addon\data\textures\my_texture_nohq.paa";
    uvSource = "tex";
    class uvTransform { aside[] = {1,0,0}; up[] = {0,1,0}; dir[] = {0,0,0}; pos[] = {0,0,0}; };
};
class Stage2
{
    texture = "#(argb,8,8,3)color(0.5,0.5,0.5,0.5,DT)";
    uvSource = "tex";
    class uvTransform { aside[] = {10,0,0}; up[] = {0,10,0}; dir[] = {0,0,0}; pos[] = {0,0,0}; };  // 10 times tiling for a real detail map
};
class Stage3
{
    texture = "#(argb,8,8,3)color(0,0,0,0,MC)";
    uvSource = "tex";
    class uvTransform { aside[] = {1,0,0}; up[] = {0,1,0}; dir[] = {0,0,0}; pos[] = {0,0,0}; };
};
class Stage4
{
    texture = "#(argb,8,8,3)color(1,1,1,1,AS)";      // or a _as.paa
    uvSource = "tex";
    class uvTransform { aside[] = {1,0,0}; up[] = {0,1,0}; dir[] = {0,0,0}; pos[] = {0,0,0}; };
};
class Stage5
{
    texture = "my_addon\data\textures\my_texture_smdi.paa";
    uvSource = "tex";
    class uvTransform { aside[] = {1,0,0}; up[] = {0,1,0}; dir[] = {0,0,0}; pos[] = {0,0,0}; };
};
class Stage6
{
    texture = "#(ai,32,128,1)fresnel(1.61,0.22)";
    uvSource = "none";
};
class Stage7
{
    texture = "dz\data\data\env_land_co.paa";
    uvSource = "tex";
    class uvTransform { aside[] = {1,0,0}; up[] = {0,1,0}; dir[] = {0,0,0}; pos[] = {0,0,0}; };
};
```

## Texture suffixes

| Suffix | Holds |
|---|---|
| `_co.paa` | Colour |
| `_nohq.paa` | Normal map |
| `_smdi.paa` | Specular and gloss |
| `_as.paa` | Ambient shadow |
| `_mc.paa` | Macro colour, a tint over the whole surface |

## Glowing parts

Set `emmisive[]` above zero for a part that should glow, such as an LED. Vanilla spells the key `emmisive` (`P:\DZ\characters\vests\data\ballisticvest.rvmat:4`); keep that spelling. To switch a glow on and off, list the part's selection in `hiddenSelections[]` with its materials in `hiddenSelectionsMaterials[]`, and swap the material from script (an LED off, green or red). How script does the swap is in `_shared/textures/runtime-material-swaps.md`.
