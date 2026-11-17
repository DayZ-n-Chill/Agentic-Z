# Advanced pitfalls and debugging

Compiler quirks, runtime crashes, `modded class` rules, scoping traps, debugging tools and the DayZ 1.30 traps. A line cited as `P:\...:N` was opened on `P:\` (game storage version 144). Measured results name the build they were measured on and were not re-run here; entries marked "reported" could not be checked on `P:\`. The rule numbers point into `hard-rules.md`.

## Compiler Bugs & Quirks

### 1. `int.MIN` comparison bug (reported, not checked on `P:\`)

```
// BROKEN — Enforce Script bug
1 < int.MIN;       // returns TRUE (should be false)
1 < -2147483647;   // also returns TRUE

// The root cause: integer overflow in the comparison logic
// Workaround: avoid comparing against int.MIN directly
```

### 2. Negation of Array Element Doesn't Compile

```
// BROKEN — doesn't compile
if (!list[1])  // compile error

// CORRECT
if (list[1] == 0)  // compiles fine
```

### 3. switch/default Return Bug

```
// BROKEN — compiler claims "not all paths return a value"
string Test(string what)
{
    switch (what)
    {
        case "A":
        case "B":
            return "X";
        default:
            return "Y";
    }
    // Compiler insists there's a missing return even though
    // default catches everything
}

// WORKAROUND — move last return out of switch
string Test(string what)
{
    switch (what)
    {
        case "A":
        case "B":
            return "X";
    }
    return "Y";  // default case, outside switch
}
```

### 4. Compile Errors Show Wrong File/Line

When a class referenced in code doesn't exist (e.g., missing addon), the
compiler shows the **last successfully parsed file at EOF**, not the file
with the actual error. This is extremely misleading.

**Debugging strategy**: If you get a compile error in a file that looks
correct, check if any class it references requires an addon that isn't loaded.

### 5. An #ifdef Block Holding Only a Comment Compiles (no segfault measured)

An empty `#ifdef` block, comments or not, is often said to cause a segfault. Measured on DayZDiag 1.30.164289 (2026-11-09), in a mod's `4_World` scripts: a block holding only a comment compiled and ran on server and client, at file scope, in a class body and in a method body, each with `DIAG_DEVELOPER` (which DayZDiag defines on both peers) and with a macro nobody defines; the method's marker was printed and neither process hung. Vanilla 1.30 ships such a block, `#ifdef DIAG_DEVELOPER` around one commented line, at `P:\scripts\4_world\classes\environment\environment.c:1-3`.

```
// Compiled and ran on DayZDiag 1.30.164289, server and client
#ifdef DIAG_DEVELOPER
// only a comment
#endif
```

Not measured: a block with nothing at all inside, a retail build, DayZ 1.29. The script validator (`scripts/tools/dayz-script-validator/`) still reports such a block, as a WARN (`ES-EMPTY-IFDEF`); remove the block if it holds no code.

### **`Expected ',' or ')', not a '0'`** + cascade (`Unexpected scope`, `Syntax error`) on a signature line

- The lexer splits an identifier that STARTS with a reserved keyword followed by a digit: `out vector out0` is tokenized as keyword `out` + type `vector` + keyword `out` + literal `0`, so the parser sees a stray `'0'` that "does not exist" on the line at first glance. Same family as a keyword used as a name (the `owned` row in `review-and-troubleshooting.md`), but the trigger is keyword+digit, not keyword alone. Affected prefixes: `out`, `ref`, `new`, `auto`, `inout`. Vanilla contains zero `out<digit>` identifiers (full grep of `P:\scripts`)
- Rename to a non-keyword prefix: `dst0`, `res0`, `val0`, etc. Diag: if the error names a digit token (`'0'`, `'1'`, …) you cannot find on the line, suspect a parameter or variable whose name starts with a reserved keyword. Measured in a mod compile (2026-08-07): the compile failed at three signature lines, and renaming `out0..out3` to `dst0..dst3` compiled clean.

### **`Unknown operator '%'`**: `%` in an expression with a float literal

On DayZDiag 1.30.164289 (2026-11-09), in a mod's `4_World` script, `float x = (cell % 103) * 150 + 150 * 0.5;` and `float x = (cell % SIDE) * STEP + STEP * 0.5;` (`static const float STEP`, `static const int SIDE`) each stopped the World module with `Unknown operator '%'` at its own line, then `Can't compile "World" script module!`. With the `%` in an `int` local first, `int col = cell % SIDE; float x = col * STEP; x = x + STEP * 0.5;` compiled and ran. Both failing lines hold the literal `0.5`, so whether a `static const float` with no literal beside it fails is not isolated. The second expression has also been seen to fail with `Unknown operator ''`, in a mission's `init.c`; that was not measured again. Syntax rule 13 in `hard-rules.md` gives the rule; the script validator reports it as `ES-MODULO-FLOAT-CONTEXT`.

### Six recurring compile-fail families

1. **Opaque file handles are not integers.** `FileHandle` and `FindFileHandle` are `int[]` aliases (`P:\scripts\1_core\proto\ensystem.c:390`, `:503`). Declare the proper type without `= 0`; test `if (!handle)` and track open state separately. The directory API is `FindFile(pattern, out name, out attr, flags)`, `FindNextFile(handle, out name, out attr)`, then `CloseFindFile(handle)` (`:520-522`). `OpenFile` returns `FileHandle` (`:417`); `ReadFile(FileHandle, void, int)` (`:425`) is not a whole-file-by-path helper. Read text with `OpenFile(READ)` + repeated `FGets` + `CloseFile`, as vanilla does (`P:\scripts\5_mission\gui\controlsxbox.c:297-305`).
2. **`ScriptRPC` has no `WriteString`.** The class `ScriptRPC` adds only `Reset` and `Send` to `ParamsWriteContext` (`P:\scripts\3_game\gameplay.c:104-118`); that context is a `Serializer`, whose payload API is generic `Write` / `Read` (`P:\scripts\1_core\proto\serializer.c:57-58`). A class member that keeps the RPC object needs a strong `ref`.
3. **`string.Replace` mutates and returns an `int`** (`P:\scripts\1_core\proto\enstring.c:156`). Chaining `.Replace().Replace()` tries to call `Replace` on that integer. Copy to a local, call `Replace` once per step, then return the local.
4. **Long formulas have a compiler limit.** On DayZDiag 1.30.164289, one statement on one line that alternates string literals with an `int` and a float's `ToString()` (`string s = "a" + i0 + " b" + f0.ToString() + …`) compiled with 17 terms and failed with 18 and with 20: `Formula too complex` on its line, then `Incompatible parameter 'i0'`, then `Can't compile "World" script module!`. Other operand types and a statement over several lines are not measured; a JSON-style expression with roughly 30 operands also failed in a mod's compile. Build it incrementally (`result = result + part;`). The script validator warns on a statement that holds a string literal and joins 18 or more terms with `+` (`ES-FORMULA-TOO-COMPLEX`).
5. **Locals have method scope, not block scope.** Reusing one local name in sibling `if` or `switch` branches produces `Multiple declaration`; rename per branch or hoist once. Separate `#ifdef` / `#else` compile views may reuse a name because only one view exists at a time.
6. **Brace-only balance is incomplete.** `Unmatched brackets detected!` can come from parentheses or square brackets. An offline checker must balance `()`, `[]`, and `{}` after stripping strings and comments, per file. It cannot replace the game compile gate; preprocessor views, encoding failures, and these API contracts remain outside that check.

The compiler can stop after the first family and expose the next one only after a rebuild. Fix and re-run every required game compile view until all layers are clean.

---

## Runtime Crashes (Segfaults)

### 6. Compound Expression Assigned to Array Element

```
// SEGFAULT
m_IsInside[index] = vector.DistanceSq(a, b) <= distSq;

// CORRECT — split into two statements
bool isInside = vector.DistanceSq(a, b) <= distSq;
m_IsInside[index] = isInside;
```

**Rule**: Never assign the result of a compound expression (comparison,
arithmetic, function call chain) directly to an array element. Always
use an intermediate local variable.

### 7. NormalMapMacro Shader on Dedicated Server

Using `NormalMapMacro` shader in .rvmat files causes dedicated server crash
at model load time. The shader references client-only rendering paths.
(Reported in a third-party mod; not checked on `P:\`.)

```
// CRASH on dedicated server
Stage3
{
    texture = "...nohq.paa";
    uvSource = "tex";
    class uvTransform { ... };
    shader = NormalMapMacro;  // CRASH
}

// CORRECT — use Super shader with 7 stages for all rvmats
shader = Super;
```

### 8. ProjectionBasedOnParent Creates Real Entities

If a kit/hologram uses `ProjectionBasedOnParent`, the engine creates an
actual entity during placement preview. Without overriding `PlaceEntity()`,
ghost entities accumulate.

```
// REQUIRED override in Hologram
override EntityAI PlaceEntity(EntityAI newEntity)
{
    // Prevent ghost spawn by returning the projected entity
    return newEntity;
}
```

### 9. map<Widget, T> runtime crash (reported; vanilla uses this key type)

```
// Seen in one third-party mod: compiled, then crashed at runtime
ref map<Widget, int> m_Map;

// The mod's workaround: parallel arrays
ref array<Widget> m_Keys;
ref array<int> m_Values;
```

`Widget` is a valid `map` key in vanilla: `m_RadialItemCards` is a `map<Widget, float>` (`P:\scripts\3_game\gui\effects\radialmenu.c:17`), `m_MultiOptionSelectors` is keyed by `Widget` (`P:\scripts\5_mission\gui\newui\charactercreation\charactercreationmenu.c:32`) and so is `m_SpawnButtonsOriginalText` (`P:\scripts\5_mission\gui\scriptconsoleitemstab.c:22`). So the crash the mod saw is not a rule of the language; the cause in that mod was not isolated. `production-patterns.md` uses `map<Widget, int>` for its hover cache. If a map keyed by widgets crashes, check first whether the map outlives the widgets it holds.

### 10. ScriptView Constructor from RPC Context

```
// CRASH — new ScriptView() calls CreateWidgets() internally
// CreateWidgets() fails in RPC context (no workspace available)
void OnRPC(...)
{
    MyMod_SorterView view = new MyMod_SorterView();  // CRASH
}

// CORRECT — pre-create in MissionInit, show/hide later
class MissionGameplay
{
    ref MyMod_SorterView m_SorterView;

    override void OnInit()
    {
        m_SorterView = new MyMod_SorterView();  // safe here
    }
}
```

---

## Operator Precedence Trap

Enforce Script follows C/C++ precedence where bitwise operators have
LOWER priority than comparison operators:

```
// WRONG — interpreted as a & (b == b) = a & true = a & 1
int result = a & b == b;

// CORRECT — explicit parentheses
int result2 = (a & b) == b;
```

This catches developers coming from Python where bitwise ops have higher
precedence than comparisons.

---

## modded class Rules

`modded class` extends vanilla or other mod classes without inheritance:

```
modded class PlayerBase
{
    override void OnConnect()
    {
        super.OnConnect();
        // Custom code
    }

    // Can ADD new methods
    void MyCustomMethod()
    {
    }
}
```

**CRITICAL RULES:**
1. A `modded class` can add member variables as well as methods and overrides. (Rule 25 in `hard-rules.md` and the prefix convention further down this file both add members, and vanilla's own modding example adds a `static const int` member to `modded class ParticleList`, `P:\scripts\3_game\particles\particlelist.c:5`.) Prefix every member you add.
2. Two `modded class` declarations for the same class CAN coexist in different files
3. Call `super.MethodName()` in overrides to preserve vanilla behavior
4. Only ONE `modded class Hologram` can exist across ALL files, because multiple declarations conflict (reported in a third-party mod; it contradicts rule 2 for this one class and was not checked on `P:\`)

    - **`modded class MissionServer` — `OnGameplayDataHandlerLoad` has a vanilla implementation.** It sets `m_RespawnMode`, the debug monitor, and calls `InitialiseWorldData()` (`P:\scripts\5_mission\mission\missionserver.c:161-167`). A `modded` override that omits `super` silently breaks world data. The same applies to `OnClientPrepareEvent`, which decides `useDB` from `GetHive()` (`P:\scripts\5_mission\mission\missionserver.c:449-463`): without `super`, character loading breaks.
    - **CE-safe spawn timing is `GlobalsInit()`, not `OnGameplayDataHandlerLoad`.** The vanilla spawn and the comment *«CE being initialized before spawning them»* live inside `GlobalsInit()` (`P:\scripts\3_game\dayzgame.c:1158`, opens with `if (GetCEApi())` at `:1160`, spawn at `:1173-1174`), queued separately at `:1096`. The Mission hook runs much earlier: `MissionServer.OnInit` calls `CfgGameplayHandler.LoadData()` at `P:\scripts\5_mission\mission\missionserver.c:88` (`OnInit` from `:85`, carriers at `:91`). Citing the `GlobalsInit` spawn lines to justify a spawn in `OnGameplayDataHandlerLoad` is a misattributed citation. The derived rule is not "always spawn late": vanilla spawns Underground carriers in `OnInit` (`UndergroundAreaLoader.SpawnAllTriggerCarriers`, `P:\scripts\5_mission\mission\missionserver.c:91`) because they do not touch the CE. Spawn where vanilla spawns the family you are creating: items / `ItemBase` with CE lifetime go through the ObjectSpawner route.

### A variable named like a type (`map`) fails the whole module

Declaring a variable whose name is already a type name does not compile:
`Widget map = root.FindAnyWidget("mapWidget")` fails with
`Variable name 'map' already used as type name` and the whole module dies
(`Can't compile "Mission" script module!`). The compiler also reports decoys
on later lines (`Trying to modify write protected variable '(null)'`,
`Undefined function 'map.GetFlags'`): the root cause is always the FIRST
line of the block; the rest is noise. Same risk with any type name
(`set`, `array`, `vector`, `string`, `Class`). Indirect symptom: the client
boots, never enters, and dies on its own; the server writes it clearly in
`script_*.log`, the client does not. Measured with a probe script
in a mod (2026-08-22).

### Detecting Other Mods

```
// Compile-time detection (addon loaded)
#ifdef EXPANSION
// Expansion code here
#endif

// Runtime detection (config exists)
string cfgCheck = "CfgPatches ExpansionHardline";
bool hasHardline = GetGame().ConfigIsExisting(cfgCheck);
```

---

## Variable Scoping Traps

### Sibling Scope Re-declaration

```
// COMPILE ERROR — same name in sibling scopes
if (condition)
{
    int x = 5;
}
else
{
    int x = 10;  // ERROR: multiple declaration
}

// CORRECT — hoist before conditional
int x;
if (condition)
{
    x = 5;
}
else
{
    x = 10;
}
```

### Nested Scope Re-declaration

```
// COMPILE ERROR — nested scope shadows outer
int i = 5;
for (int i = 0; i < 12; i = i + 1)  // ERROR
{
}

// CORRECT — different name or hoist
int i = 5;
int j;
for (j = 0; j < 12; j = j + 1)
{
}
```

---

## Debugging Tools

### Print / PrintFormat

```
// Basic print
Print("Hello");
Print(myInt);
Print(myVector);

// Formatted print (format string with %1, %2, etc.)
PrintFormat("Device %1 at pos %2 has load %3", typeName, pos.ToString(), load.ToString());
```

### Error / ErrorEx

```
// Log as error (shows in script errors)
Error("Something failed");

// ErrorEx with detail
ErrorEx("Failed to load config", ErrorExSeverity.WARNING);
```

### Script Console

In Workbench or with admin tools, the script console can execute
Enforce Script at runtime — useful for testing snippets:
```
Print(GetGame().GetTime());
```

### RPT Log Analysis

Common log patterns and what they mean:

| Log Pattern | Meaning |
|---|---|
| `SCRIPT (E): ...` | Script error (non-fatal, usually null reference) |
| `Segmentation fault` | Fatal crash — array bounds, dead pointer, shader |
| `Illegal write at ...` | Heap corruption — usually from timer/alloc fragmentation |
| `Multiple declaration of 'X'` | Variable declared in sibling scopes |
| `Variable name 'X' already used as type name` | A variable named like a type (`map`, `set`, `array`); the lines after it are decoys |
| `Unknown operator '%'` | `%` in an expression with a float (see above) |
| `Formula too complex` | A one-line concatenation of 18 or more terms (see above) |
| `'X' not found` | Class/method doesn't exist — missing addon or typo |
| `Scripted variables corrupted upon "X"` | OnStoreLoad order mismatch |
| `Cannot create object of type 'X'` | Class not in config.cpp or wrong parent |

---

## String & Number Gotchas

### String parameters: a literal argument is fine

Assigning every string literal to a local before passing it is not a rule of the language: syntax rule 5 in `hard-rules.md` says string literals as function arguments work, and vanilla passes them everywhere, for example `layoutRoot.FindAnyWidget("continuebtn")` (`P:\scripts\5_mission\gui\ingamemenu.c:40`).

```
widget.FindAnyWidget("MyWidget");  // fine

// A local is only a readability choice
string wName = "MyWidget";
widget.FindAnyWidget(wName);
```

### Float Precision

```
// Enforce uses 32-bit float — precision ~7 significant digits
// Large timestamps lose precision after 16,777,216 (2^24)
// GetTime() itself returns an int (P:\scripts\3_game\global\game.c:1534); the loss starts when you store it in a float
float time = GetGame().GetTime();  // milliseconds, converted to float
// After 4.66 hours (2^24 ms) the float can no longer hold every millisecond: the step becomes 2 ms
// After 46 hours the step is 16 ms, and it keeps doubling
```

### ToString Limitations

```
// int.ToString() and float.ToString() work
int x = 42;
string s = x.ToString();  // "42"

// No printf-style formatting — build manually
// Format one decimal by hand with a small helper of your own
```

---

# Additional pitfalls: style guide and performance

Each entry notes whether it was checked against vanilla on `P:\`.

### Compiler / language quirks

- **Empty `#ifdef` / `#ifndef` blocks were reported to segfault**, even with only comments
  inside. Not reproduced: on DayZDiag 1.30.164289 a block holding only a
  comment compiled and ran on server and client, at file scope, in a class body and in a
  method body (section 5 above). A block with nothing at all inside, a
  retail build and DayZ 1.29 are not measured. Remove a block that holds no code.

- **`1 < int.MIN` returns TRUE** — and `1 < -2147483647` also returns TRUE. Integer
  comparison against `int.MIN` is broken. Always guard MIN/MAX comparisons explicitly.
  *(Reported; not checked on `P:\`.)*

- **Switch with `default` STILL requires a return outside** — even though every case
  including default returns, the compiler complains "function must return a value".
  Workaround: move the default branch's return to a final `return Y;` after the switch:

  ```c
  string Test(string what)
  {
      switch (what)
      {
          case "A":
          case "B":
              return "X";
      }
      return "Y";  // default moved outside
  }
  ```

- **`if (a & b == b)` parses as `a & (b == b)`** — bitwise has lower precedence than
  comparison in EnScript (C/C++ semantics). Always parenthesize:

  ```c
  if ((a & b) == b)   // CORRECT
  ```

- **Compiler errors with undefined classes / name conflicts point to the WRONG file** —
  the error shows the last `.c` parsed at EOF, NOT the line that triggered the issue.
  When the error location seems wrong, search the entire codebase for the symbol and
  check that all required addons are loaded.

- **`crash_<date>_<time>.log` contains EXCEPTIONS, NOT segfaults** — actual crashes
  (memory faults) write a different dump. When debugging, check both: exception logs
  for handled errors, separate crash dumps for hard segfaults.

### Performance traps (declarations checked in vanilla `game.c`)

- **`GetObjectsAtPosition` / `GetObjectsAtPosition3D` are slow**: `proto native` at
  `P:\scripts\3_game\global\game.c:923` and `:930`. Avoid in tick paths. Prefer:
  - Static arrays on the class you're looking for (`s_AllInstances`)
  - Triggers (`ScriptedEntity`-derived with collision events)
  - `GetScene()` API for scene-graph queries
  *(Vanilla call; the performance claim is not measured.)*

- **`SurfaceIsPond` / `SurfaceIsSea` / `SurfaceRoadY` are slow**: `proto native` at `P:\scripts\3_game\global\game.c:1197`,
  `:1196`, `:1177`. For "is this point in water?" prefer:

  ```c
  if (g_Game.GetWaterDepth(pos) > 0)  // pos is vector
  ```

  Vanilla itself uses both patterns: `SurfaceIsSea` or `SurfaceIsPond` at `P:\scripts\4_world\classes\hologram.c:1128`,
  `GetWaterDepth` at `P:\scripts\3_game\vehicles\transport.c:537` and
  `P:\scripts\4_world\entities\manbase\playerbase.c:7138` (`GetWaterDepth` is declared at `game.c:1198`). When you control
  the call site, prefer `GetWaterDepth`.

  Over water objects (the vanilla river and stream pieces, the streambed kit, a roadway
  `water_ext` face of your own), see `skills/_shared/physics/water-queries.md`: on vanilla
  Chernarus, `SurfaceIsPond` read false at the centre of most river and stream pieces above 50 m.

- **Surface Y position fast pattern**:

  ```c
  vector GetSurfacePosition(float x, float z)
  {
      return Vector(x, g_Game.SurfaceY(x, z), z);
  }
  ```

### Type system: `GetType()` vs `ClassName()`

For entities, `GetType()` returns the **config.cpp class name** (resolved via
`g_Game.ObjectGetType(this, ret)`, `P:\scripts\3_game\entities\object.c:467`), while `ClassName()` returns the **script class
name**. They differ when the script class has no matching config declaration.

```c
// PREFERRED for entities
if (entity.GetType() == "MyMod_Vest") { ... }

// Use ClassName() only when you specifically need the script class name
```

Vanilla uses `GetType()` heavily for the hidden selections lookup (`GetHiddenSelections`, `P:\scripts\3_game\entities\object.c:128`, `:134`, `:140`) and to build config paths (`HasAnimation`, `P:\scripts\3_game\entities\object.c:424`, `:430`, `:436`).

### `[Obsolete()]` attribute (verified vanilla)

Marks methods/fields/vars as deprecated. Workbench surfaces a warning at call sites.
Use when removing API would break dependent mods — soft-deprecate first.

```c
[Obsolete("Use GizmoApi.GetCount")]
proto native int GizmoGetCount();
```

Vanilla examples: `GizmoGetCount` and its two neighbours at `P:\scripts\3_game\global\game.c:802`, `:808`, `:814`, and the `Obsolete` enum at `P:\scripts\3_game\enums\ecrewmemberstate.c:1`.

### `notnull` keyword for parameters

Propagates non-nullness guarantees. The caller has already verified non-null, so the
function can skip the check. Combined with the EnScript rule "null-check where you
know how to handle it":

```c
void Foo()
{
    EntityAI entity = FindSomeEntitySomehow();
    if (!entity) { Print("entity not found"); return; }
    DoStuff(entity);
}

void DoStuff(notnull EntityAI entity)
{
    GameInventory inventory = entity.GetInventory();
    // entity guaranteed non-null; only check inventory if null is semantically valid
}
```

### Modded class member-var prefix convention

When adding members to `modded class X` or to a class extending vanilla, ALWAYS
prefix the member to avoid collision with other mods that also extend `X`:

```c
modded class ItemBase
{
    bool m_Expansion_CustomFlag;       // GOOD — prefixed
    int  m_MyMod_PowerDraw;            // GOOD — prefixed
    bool m_CustomFlag;                 // BAD — collides with any other mod's m_CustomFlag
}
```

### `EXTrace.Start` (Expansion / Community Framework only)

Modern minimal-overhead tracing. **NOT in vanilla DayZ.** Available when Expansion
or DayZ Community Framework is loaded. Replaces older `CF_Trace_0` pattern that
required `#ifdef EXPANSIONTRACE` guards.

```c
auto trace = EXTrace.Start(EXTrace.GENERAL, this, "MethodName");
// no #ifdef needed — no-op when tracing disabled
```

If your mod targets vanilla-only servers, fall back to `Print()` or your own
conditional logger.

### `defines[]` array in CfgMods (DayZ 1.26+)

Auto-generates `#define <ModClassName>` and any custom defines listed:

```cpp
class CfgMods
{
    class YourMod
    {
        defines[] = {"YOURMOD", "YOURMOD_FEATURE_X"};
    };
}
```

Then in script:

```c
#ifdef YOURMOD
    // mod-specific code
#endif
```

*(Version-gated: works only on DayZ 1.26 and later. Not checked on `P:\`.)*

### Cross-mod `#ifdef` gates: use the CfgMods auto-define, NOT a manual `#define`

The CfgMods `defines[]` (or just the implicit `#define <ModClassName>` from
DayZ 1.26+) is visible to **other mods' compilation units**. A manual
`#define X` written inside `<TargetMod>/scripts/Common/Define.c` is **only
visible inside that target mod's own files** — even when the symbol name is
identical. A consumer mod's `#ifdef X` that gates code against the manual
define will silently compile to no-op.

```c
// In <YourMod>/scripts/4_World/...c — gating an override of another mod's class:

#ifdef OtherMod_table   // CfgMods auto-define from OtherMod_table.pbo
modded class OtherMod_table_s { ... }   // works
#endif

#ifdef OtherMod_furniture   // manual #define in OtherMod_table/Common/Define.c
modded class OtherMod_table_s { ... }   // never compiles, override silently lost
#endif
```

Symptom: the `modded class` body never runs. `IsKindOf` / `Open` / hook calls
behave as if the override does not exist, but the codebase compiles cleanly.

Rule: when picking the cross-mod gate symbol, audit the target PBO's
`config.cpp` `CfgPatches` / `CfgMods.defines[]` entries — never trust a
matching `#define` in `scripts/Common/Define.c` to propagate.

### `#ifdef DEVELOPER` ≠ `DIAG_DEVELOPER` — read the actual compile defines

Vanilla has APIs guarded by `#ifdef DEVELOPER` (e.g. `DayZPlayerSyncJunctures.SendGetInVehicle` → `SJ_DEBUG_GET_IN_VEHICLE`, much of `plugindeveloper.c`). Standard `DayZDiag_x64` defines `DIAG_DEVELOPER` but does **NOT** define `DEVELOPER`. Emitting a `DEVELOPER`-only symbol from your mod breaks the compilation of the **entire PBO** (cross-mod compile failure, no clean RPT, only "PBO not loaded" / addons missing) — not a silent no-op. Before relying on any `#ifdef <SYMBOL>` API, verify the `defines:` line of `<profiles>\script_*.log` for BOTH server and client peers (the runtime tells you what is defined). That `OnDebugSpawn` (`#ifdef DIAG_DEVELOPER`) works does NOT prove `DEVELOPER` is active — different macros. Measured in a mod, 2026-06-28: the real compile logs showed `DEVELOPER` was not defined, and the PBO would have shipped broken.

### PluginDeveloper is dead in release — use the retail substitutes

`PluginDeveloper` registers ONLY under `#ifdef DIAG_DEVELOPER` (`RegisterPluginDiag`, `P:\scripts\4_world\plugins\pluginmanager.c:65`, `:249-254`): in `DayZServer_x64` release, `GetPlugin(PluginDeveloper)` returns null and any teleport/give built on it (`TeleportAtCursor`, `SpawnEntityInInventory`…) is DEAD even though it compiles and works in DayZDiag. The retail substitutes (the pattern admin tools such as Community Online Tools use, which runs on retail):

- **Teleport**: `player.SetPosition(pos)` (if y==0, resolve `GetGame().SurfaceY(x, z)` first).
- **Seated player + vehicle**: `HumanCommandVehicle vc = player.GetCommand_Vehicle();` (`P:\scripts\3_game\human.c:1528`), then `Transport veh = vc.GetTransport();` (`P:\scripts\3_game\human.c:716`), then `veh.GetTransform(mat); mat[3] = pos; veh.SetTransform(mat);` — vehicle and occupant move together. **The occupant's position lags one frame**: to report the applied position, read `veh.GetPosition()`, not `player.GetPosition()`.
- **Give**: `player.GetInventory().CreateInInventory(cls)` / `player.GetHumanInventory().CreateInHands(cls)` (`P:\scripts\3_game\systems\inventory\humaninventory.c:44`) with `player.GetItemInHands()` as the hands-occupied guard.

### `foreach` on getter results re-calls the getter

Every iteration calls the method again. Hoist to a local first:

```c
// BAD — getter called N times
foreach (string t : GetTest()) { Print(t); }

// GOOD — getter called once
TStringArray test = GetTest();
foreach (string t : test) { Print(t); }

// ALSO GOOD — direct member access doesn't recall
foreach (string t : m_Test) { Print(t); }
```

### `modded class` must live in the base class's script module; compile both peers

A `modded class X` declaration must be compiled in the same script module that defines `X`. This is stricter than merely referring to the type from a method in a higher module. `PPERequesterBank` is defined in `3_Game` (`P:\scripts\3_game\ppemanager\pperequesterbank.c:4`): referring to it from `4_World` can compile, but declaring `modded class PPERequesterBank` under `Scripts/4_World/` fails with `Unknown type 'PPERequesterBank'` and kills the entire World module. Put that declaration under `Scripts/3_Game/<Mod>/`.

Do not hide the declaration with `#ifndef SERVER`. That can make the dedicated-server compile pass only by excluding the failing code, while the client still compiles it and fails. The release gate must compile **both the dedicated-server and client views**. A server-only gate cannot cover UI, camera, or post-process code excluded by `#ifndef SERVER`; a client-only gate cannot cover `#ifdef SERVER` code. Keep rebuilding both views until neither reports a script-module failure.

### Long concatenation diagnostic cascades

For a long concatenation or formatting expression, `Formula too complex` is the root parser/compiler error. An `Incompatible parameter` reported on the same line can be a cascade, not a second API defect: the 18- and 20-term statements of item 4 in "Six recurring compile-fail families" logged that pair on one line. Split the build into incremental single-line assignments (`s = s + part;`). Extract vector or matrix indexing and function-call results into typed locals before formatting them.

A physical expression longer than 400 characters is a useful offline lint signal, not a language boundary. The limit measured in item 4 (17 terms compiled, 18 failed) holds for one pattern on one line; other operand types are not measured. The script validator warns from 18 terms joined by `+` in a statement that holds a string literal (`ES-FORMULA-TOO-COMPLEX`). The game compile remains the gate.

## DayZ 1.30: obsolete callbacks, ID shift, hand FSM

The 1.30 traps (the full bodies are in `dayz-1-30-enforce-script.md`):

- (through 1.29: `override void OnCEUpdate()`). (since 1.30: `[Obsolete]`; live tick is `OnCEIterate(float currentTime, float elapsedTime)`: `P:\scripts\3_game\entities\entityai.c:3904-3911`, `:4924-4925`.)
- (through 1.29: hand guards auto-passed `e.m_IsJuncture || e.m_IsRemote`). (since 1.30: only `e.m_IsRemote`, `P:\scripts\3_game\systems\inventory\hand_guards.c:299`, `:325`, `:351`. New `HandGuardIsNotSurrendered` `:405` returns `!m_Player.IsSurrendered()`.)
- (through 1.29: `UA_AM_PENDING` was 14). (since 1.30: `UA_AM_INIT = 14` inserted; `PENDING=15`, `ACCEPTED=16`, `REJECTED=17`: the `UA_AM_*` constants at `P:\scripts\3_game\constants.c:508-511`. Never hardcode the integers.)
- (through 1.29: `TakeEntityToCargo` / `AsAttachment` family). (since 1.30: `[Obsolete]`, from `TakeEntityToCargo` on, `P:\scripts\3_game\systems\inventory\inventory.c:1345-1386`; use the Target* variants.)
- (through 1.29: `ActionFillBottleBase` in `RegisterActions`). (since 1.30: `[Obsolete]` `P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionfillbottlebase.c:28-29`; the constructor inserts `ActionObtainLiquidBase`, `P:\scripts\4_world\classes\useractionscomponent\actionconstructor.c:156`.)
- `ProcessInputData` override is silent in retail (DIAG + debug flag only): `P:\scripts\4_world\systems\inventory\dayzplayerinventory.c:668-687`.
- `World.Is3rdPersonDisabled()` is `[Obsolete]` in favour of `GetThirdPersonViewMode` (`P:\scripts\3_game\global\world.c:291`). `GetNoiseReductionByWeather` was **not** deleted; both Weather methods exist and are `[Obsolete]` (`GetNoiseReductionByWeatherEx` at `P:\scripts\3_game\weather.c:407`, `GetNoiseReductionByWeather` at `:454`).

### Looping `CombineItems`: an emptied stack is deleted only on the next frame (added 2026-09-19)

`ItemBase.CombineItems` empties the donor with `AddQuantity(-used)`, which goes through `SetQuantity`. For items with `varQuantityDestroyOnMin = 1` (e.g. `Rag`), `SetQuantity` at the minimum reads `varQuantityDestroyOnMin` and calls `this.Delete()` (`P:\scripts\4_world\entities\itembase.c:3333-3338`). `EntityAI.Delete()` only sets `m_PendingDelete` (`P:\scripts\3_game\entities\entityai.c:779-782`), and `Object.Delete()` queues `ObjectDelete` for the next frame (`P:\scripts\3_game\entities\object.c:82-85`). Until then the emptied stack is still a cargo child with quantity 0, and `CanBeCombined` (`P:\scripts\4_world\entities\itembase.c:2137-2197`) has no pending-delete check: an empty stack is "not full", so it is a valid target.

Any loop that performs several merges in one call (auto-stack, stack-all, loot consolidation) can therefore pick the emptied stack as a later target and move live quantity into it. Everything merged into it disappears on the next frame. Rag stacks 2/2/5: A←B (B=0, pending), A←C (A full, C=3), B←C (C=0) → 9 rags become 6.

Before each target and donor, skip entities already queued for deletion (`IsSetForDeletion`, `P:\scripts\3_game\entities\entityai.c:812-814`), and empty ammunition piles:

```c
if (!item || item.IsSetForDeletion())
    continue;
Magazine pile = Magazine.Cast(item);
if (pile && pile.GetAmmoCount() <= 0)
    continue;
```

Verification: a static trace through the vanilla script tree (2026-09-19); not reproduced in game.
