# Config.cpp and .rvmat Validation

## Config.cpp Validation

### Baked-in P:\ Drive Paths (CRITICAL)

Absolute paths like `P:\DZ\gear\consumables\data\rag_co.paa` only exist on the
developer's machine. These MUST be converted to game-relative paths:

```cpp
// WRONG — breaks on any other machine:
hiddenSelectionsTextures[] = {"P:\DZ\gear\consumables\data\rag_co.paa"};

// CORRECT — works everywhere:
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
    autocenter = 0;        // MANDATORY — prevents visual mesh burial
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

Same rule as config.cpp — `P:\` paths break on distribution:

```text
// WRONG:
texture="P:\dz\gear\camping\data\flag_generic_nohq.paa";

// CORRECT (vanilla reference):
texture="dz\gear\camping\data\flag_generic_nohq.paa";
```

### Required Texture Stages

Standard DayZ .rvmat needs at minimum:

- Stage 0: Diffuse color texture (`_co.paa`)
- Stage 1: Normal map (`_nohq.paa`)
- Stage 2: Specular/detail map (`_smdi.paa`)

Missing stages produce engine warnings but don't crash.
