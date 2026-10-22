# Enforce Script style: Naming and files

Part of the Enforce Script style guide; the index and the task table are in `../enscript-style.md`. The guide is a mirror of the [TrueDolphin/references wiki](https://github.com/TrueDolphin/references/wiki/EnScript-(Enforce-Script)-Style-Guide).

Vanilla facts: the vanilla calls named here (`GetGame()`, native calls, `[Obsolete]`) cite `P:\scripts\` below; the language itself is in `../enscript/references/language_types.md` and `language_compile.md`.

## Introduction

EnScript (Enforce Script) is the object-oriented scripting language used by the Enfusion engine in DayZ Standalone. This style guide is based on conventions observed in the official Bohemia Interactive DayZ Script Diff and in large community mods.

---

## File Organization

### File Extensions

- Use `.c` extension for all EnScript files
- File names should match the primary class name when possible

### Directory Structure

Scripts are typically organized by layer inside a root folder called `Scripts/`:

- `1_Core/`: Core systems
- `2_GameLib/`: Game library
- `3_Game/`: Game-specific code
- `4_World/`: World entities
- `5_Mission/`: Mission logic

---

## Naming Conventions

### Classes

**PascalCase** for all class names:

```
class MyMod_GarageSettings
class PlayerBase
class ItemBase
class MyMod_PatrolBase
```

**Prefixes:**

- Prefix your own classes with a short mod tag (e.g., `MyMod_`), so they never clash with vanilla or another mod
- Base classes often end with `Base`
- Abstract classes may start with `Abstract`

**Modded Classes:**

- **ALWAYS prefix member variables** in modded classes or classes inheriting from vanilla/other mods:

```
// CORRECT: Prefixed members in modded class
modded class ItemBase
{
    bool m_MyMod_CustomFlag;
    int m_MyMod_CustomValue;
}

// CORRECT: Prefixed members in inherited class
class MyMod_SomeItem : ItemBase
{
    bool m_MyMod_SpecialProperty;
}
```

This prevents name conflicts with vanilla code or other mods.

### Variables

**Member Variables:**

- Use `m_` prefix for private/protected member variables
- Use PascalCase after the prefix

```
bool m_IsLoaded;
MyMod_MarkerModule m_MarkerModule;
ref MapMenu m_MyMod_MapMenu;
```

**Static Variables:**

- Use `s_` prefix for static member variables
- Use PascalCase after the prefix

```
static ref array<EffectArea> s_MyMod_DangerousAreas;
```

**Local Variables:**

- Use camelCase for local variables
- No prefix required

```
int bitmask;
string lootingBehavior;
vector hitPosition;
```

### Methods/Functions

**PascalCase** for method names:

```
void SetDefaultLootingBehaviour()
int GetLootingBehaviour()
void OnSend(ParamsWriteContext ctx)
bool OnReceive(ParamsReadContext ctx)
```

**Override Methods:**

- Always use the `override` keyword when overriding parent methods

```
override void OnSend(ParamsWriteContext ctx)
override bool OnReceive(ParamsReadContext ctx)
```

**Proto Methods vs Custom Methods:**

When available, prefer using proto (native engine) methods over custom script implementations **when the native method performs expensive logic**. Proto methods are faster for complex operations as they run in native code.

```
// PREFERRED: Proto method for expensive operations
proto native vector GetPosition();   // P:\scripts\3_game\entities\object.c:287

// AVOID: Custom reimplementation of expensive native logic
vector GetPosition()
{
    // Custom expensive calculation
}
```

If someone is writing a mod that will likely be modded/overridden, suggest using the Obsolete attribute on a method/field/variable instead of removing them altogether. The workbench will show a warning when used. The attribute is the vanilla `class Obsolete` (`P:\scripts\1_core\proto\enscript.c:359`).

```
[Obsolete()]
vector GetCustomPosition()
{
    // Custom expensive calculation
}
```

**Specific use note 1:** If at all possible, avoid using `GetObjectsAtPosition` and `GetObjectsAtPosition3D` (`P:\scripts\3_game\global\game.c:923` and `:930`) as much as possible. Static arrays on the class you're looking for, triggers, or the `GetScene` methods are all much better options available.

**Specific use note 2:** If at all possible, avoid `g_Game.SurfaceIsPond()`, `SurfaceIsSea()` or `SurfaceRoadY` (`P:\scripts\3_game\global\game.c:1197`, `:1196` and `:1177`) as much as possible. They're remarkably slow for their intended purpose.

Recommend using `if (g_Game.GetWaterDepth(vectorpos) <= 0)` (`game.c:1198`) for checking if vector is in water, and something similar to the following for surface y calculating.

```
vector GetSurfacePosition(float x, float z)
{
    return Vector(x, g_Game.SurfaceY(x, z), z);   // game.c:1176
}
```

**Important Note:** There is overhead from calling native methods from script. For simple operations, custom script methods may actually be faster. This is why `proto native CGame GetGame()` was replaced with `DayZGame GetGame() { return g_Game; }` (`P:\scripts\3_game\gameplay.c:636`): the script version is faster for simple global access.

**Rule:** Use proto methods when they perform complex/expensive operations. For simple operations (like returning a global), script implementations are often faster.

### Parameters

Use camelCase for parameters:

```
void Log(string msg)
void SetValue(int value, bool isEnabled)
static vector GetPlacementPosition(vector pos)
```

### Constants and Defines

**Constants:**

Use `const` for class-specific constants, or enums for grouped constants:

```
class VehicleManager
{
    const int MAX_VEHICLES = 10;
    const float SEARCH_RADIUS = 100.0;
}
```

**Enums:**

Use enums to group related constants: **avoid creating many similarly named global constants**:

```
// PREFERRED: Grouped with enum
enum EVehicleType
{
    Car,
    Truck,
    Helicopter
}

// ALSO ACCEPTABLE: PASCAL_CASE enums
enum EVehicleType
{
    CAR,
    TRUCK,
    HELICOPTER
}

// AVOID: Multiple global constants
const int VEHICLE_TYPE_CAR = 0;
const int VEHICLE_TYPE_TRUCK = 1;
const int VEHICLE_TYPE_HELICOPTER = 2;
```

**Enum Naming:**

- **CamelCase** is generally nicer to read: `enum EStatus { Idle, Running, Stopped }`
- **PASCAL_CASE** can be used for clarity in some cases: `enum EStatus { IDLE, RUNNING, STOPPED }`
- Choose one style and be consistent within your codebase

**Preprocessor Defines:**

Use UPPERCASE for preprocessor defines:

```
#define MYMOD_MARKER_VIS_WORLD
#define MYMOD_VEHICLES
```

**Config Class Name Defines (DayZ 1.26+):**

As of DayZ 1.26, config `CfgMods` class names are automatically defined in script. To add custom defines, use the `defines[]` array in your `config.cpp`:

```
class CfgMods
{
    class YourMod
    {
        defines[] =
        {
            "YOURMOD",
            "YOURMOD_FEATURE_X"
        };
    };
}
```

These defines can then be used in script:

```
#ifdef YOURMOD
    // Mod-specific code
#endif
```

**Rule:** Declare new global constants (and globals in general) sparingly to avoid polluting the global namespace. Use class-specific constants, enums, and config-based defines instead.
