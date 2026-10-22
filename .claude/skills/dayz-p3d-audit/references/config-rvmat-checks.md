# Config.cpp and .rvmat Validation

## Config.cpp Validation

### Baked-in P:\ Drive Paths (WARNING, fails the run)

Absolute paths like `P:\DZ\gear\consumables\data\rag_co.paa` only exist on the
developer's machine. `audit_p3d.py` reports each one as a WARNING with its line
number, and any WARNING in a text file makes the run exit 1. Convert them to
game-relative paths:

```cpp
// WRONG: breaks on any other machine:
hiddenSelectionsTextures[] = {"P:\DZ\gear\consumables\data\rag_co.paa"};

// CORRECT: works everywhere:
hiddenSelectionsTextures[] = {"DZ\gear\consumables\data\rag_co.paa"};
```

**Where to check**: `hiddenSelectionsTextures[]`, `hiddenSelectionsMaterials[]`,
and any texture/material path in config.cpp.

**Exception**: Paths starting with `P:\` are valid ONLY during development on a
workbench with P: drive mounted. They must be stripped for distribution/PBO packing.

### Required Properties for Placed Objects

```cpp
class MyPlacedObject: Inventory_Base
{
    autocenter = 0;        // MANDATORY: prevents visual mesh burial
    model = "\ModName\data\model.p3d";  // Backslash prefix = addon root
    // For kits (handheld items): do NOT set autocenter=0
};
```

### AnimationSources Must Match model.cfg

If model.cfg defines animation `flag_mast` with `source = "flag_mast"`, config.cpp
MUST have a matching AnimationSources entry:

```cpp
class AnimationSources
{
    class flag_mast
    {
        source = "user";    // "user" = script-controlled
        animPeriod = 0.5;
        initPhase = 1;      // 0=up, 1=down for vanilla flag convention
    };
};
```

### hiddenSelections Must Match P3D

Every entry in `hiddenSelections[]` MUST have a matching named selection in the
Visual LOD of the P3D. Missing selections silently fail (no texture swap occurs).

## Material (.rvmat) Validation

### P:\ Drive Paths in .rvmat Files

Same rule and severity as config.cpp (WARNING, fails the run); `P:\` paths break on distribution:

```text
// WRONG:
texture="P:\dz\gear\camping\data\flag_generic_nohq.paa";

// CORRECT (vanilla reference):
texture="dz\gear\camping\data\flag_generic_nohq.paa";
```

### Texture Stages (Super shader, manual check)

`audit_p3d.py` does not check stages; review them by hand. Vanilla gear materials
use `PixelShaderID="Super"` / `VertexShaderID="Super"` with `Stage1` to `Stage7`
(for example `DZ\gear\camping\data\wooden_case.rvmat`,
`DZ\characters\vests\data\ballisticvest.rvmat`,
`DZ\weapons\firearms\akm\data\akm.rvmat`):

| Stage | Holds | Typical vanilla value |
|---|---|---|
| (none) | Diffuse `_co`, supplied by the model's face texture or `hiddenSelectionsTextures[]`, not by the rvmat | |
| `Stage1` | Normal map | the item's `_nohq.paa` |
| `Stage2` | Detail map | `#(argb,8,8,3)color(0.5,0.5,0.5,1,DT)` placeholder, or a `_dt.paa` |
| `Stage3` | Macro map | `#(argb,8,8,3)color(0,0,0,0,MC)` placeholder, or a `_mc.paa` (akm) |
| `Stage4` | Ambient shadow | `#(argb,8,8,3)color(1,1,1,1,AS)` placeholder, or an `_as.paa` (wooden_case) |
| `Stage5` | Specular | the item's `_smdi.paa` |
| `Stage6` | Fresnel, `uvSource="none"` | `#(ai,64,64,1)fresnel(...)` |
| `Stage7` | Environment map | `dz\data\data\env_land_co.paa` |

Keep every stage, using the procedural placeholder when there is no texture,
and copy the layout from a vanilla rvmat of a similar item rather than writing
one from scratch. Only a minority of vanilla Super materials add a `Stage0`
with the diffuse (330 of 5,841 under `P:\DZ`).
