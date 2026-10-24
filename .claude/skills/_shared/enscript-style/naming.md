# Enforce Script style: Naming and files

Part of the Enforce Script style guide; the index and the task table are in `../enscript-style.md`. The guide is a mirror of the [TrueDolphin/references wiki](https://github.com/TrueDolphin/references/wiki/EnScript-(Enforce-Script)-Style-Guide).

Vanilla facts: the vanilla calls named here (`GetGame()`, native calls, `[Obsolete]`) cite `P:\scripts\` below; the language itself is in `../enscript/references/language_types.md` and `language_compile.md`.

## Introduction

EnScript (Enforce Script) is the object-oriented scripting language used by the Enfusion engine in DayZ Standalone. This style guide is based on conventions observed in the vanilla DayZ scripts.

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
class MyMod_Settings
class PlayerBase
class ItemBase
class MyMod_ToolBase
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
MyMod_Settings m_Settings;
ref MyMod_SettingsMenu m_MyMod_SettingsMenu;
```

**Static Variables:**

- Use `s_` prefix for static member variables
- Use PascalCase after the prefix

```
static ref array<EntityAI> s_MyMod_TrackedItems;
```

**Local Variables:**

- Use camelCase for local variables
- No prefix required

```
int bitmask;
string itemName;
vector hitPosition;
```

### Methods/Functions

**PascalCase** for method names:

```
void SetDefaults()
int GetMaxItems()
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

If someone is writing a mod that will likely be modded/overridden, suggest using the Obsolete attribute on a method/field/variable instead of removing them altogether. The style guide reports that Workbench shows a warning when an obsolete member is used; this is unverified, because the warning comes from the compiler and nothing under `P:\scripts` shows it. The attribute is the vanilla `class Obsolete` (`P:\scripts\1_core\proto\enscript.c:359`).

```
[Obsolete()]
vector GetCustomPosition()
{
    // Custom expensive calculation
}
```

**Specific use note 1:** If at all possible, avoid using `GetObjectsAtPosition` and `GetObjectsAtPosition3D` (`P:\scripts\3_game\global\game.c:923` and `:930`) as much as possible. Static arrays on the class you're looking for, triggers, or the `GetScene` methods are all much better options available.

**Specific use note 2:** If at all possible, avoid `g_Game.SurfaceIsPond()`, `SurfaceIsSea()` or `SurfaceRoadY` (`P:\scripts\3_game\global\game.c:1197`, `:1196` and `:1177`) as much as possible. The style guide reports that they are remarkably slow for their intended purpose; this is unverified, because they are native engine calls and their cost is not visible in script.

Recommend using `if (g_Game.GetWaterDepth(pos) > 0)` (`game.c:1198`) for checking if a position is in water. A depth above zero means water: vanilla `Hologram.IsUnderwater` treats `GetWaterDepth(...) > 0` as underwater (`P:\scripts\4_world\classes\hologram.c:937`). Use something similar to the following for surface y calculating.

```
vector GetSurfacePosition(float x, float z)
{
    return Vector(x, g_Game.SurfaceY(x, z), z);   // game.c:1176
}
```

**Important Note:** The style guide reports that there is overhead from calling native methods from script, so for simple operations custom script methods may actually be faster. This speed claim is unverified: no vanilla file measures it. Vanilla does define `GetGame()` as a plain script function, `DayZGame GetGame() { return g_Game; }` (`P:\scripts\3_game\gameplay.c:636`); the report that it replaced a `proto native` version because the script one is faster is also unverified.

**Rule:** Use proto methods when they perform complex/expensive operations. For simple operations (like returning a global), script implementations are reported (unverified) to be often faster.

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
class MyMod_ItemTracker
{
    const int MAX_ITEMS = 10;
    const float SEARCH_RADIUS = 100.0;
}
```

**Enums:**

Use enums to group related constants: **avoid creating many similarly named global constants**:

```
// PREFERRED: Grouped with enum
enum EMyMod_State
{
    Idle,
    Running,
    Stopped
}

// ALSO ACCEPTABLE: UPPER_SNAKE_CASE enums
enum EMyMod_State
{
    IDLE,
    RUNNING,
    STOPPED
}

// AVOID: Multiple global constants
const int MYMOD_STATE_IDLE = 0;
const int MYMOD_STATE_RUNNING = 1;
const int MYMOD_STATE_STOPPED = 2;
```

**Enum Naming:**

- **PascalCase** is generally nicer to read: `enum EStatus { Idle, Running, Stopped }`
- **UPPER_SNAKE_CASE** can be used for clarity in some cases: `enum EStatus { IDLE, RUNNING, STOPPED }`
- Choose one style and be consistent within your codebase

**Preprocessor Defines:**

Use UPPERCASE for preprocessor defines:

```
#define MYMOD_DEBUG
#define MYMOD_FEATURE_X
```

**Config Class Name Defines (DayZ 1.26+):**

Unverified engine behaviour: since DayZ 1.26 the engine is reported to define each `CfgMods` class name in script. Nothing on `P:\scripts` shows it (vanilla script only reads the `CfgMods` class names, at `P:\scripts\3_game\client\mods\modloader.c:17-23`), so confirm it in game before relying on it. To add custom defines that do not depend on this, use the `defines[]` array in your `config.cpp`:

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
};
```

Real example: CF's binarized `config.bin` inside `P:\Mods\@CF\Addons\scripts.pbo` (CF 1.5.8; no line numbers, since the config is rapified) has `class CfgMods { class JM_CommunityFramework { ... defines[] = { "CF_MODULE_CONFIG", "CF_EXPRESSION", "CF_MODULES", ... }; }; };`. That shows the `defines[]` array sits inside the mod's `CfgMods` class next to `dir`, `name` and `type`.

These defines can then be used in script:

```
#ifdef YOURMOD
    // Mod-specific code
#endif
```

**Rule:** Declare new global constants (and globals in general) sparingly to avoid polluting the global namespace. Use class-specific constants, enums, and config-based defines instead.
