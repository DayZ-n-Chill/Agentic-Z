# Enforce Script style: Debugging and error handling

Part of the Enforce Script style guide; the index and the task table are in `../enscript-style.md`. The guide is a mirror of the [TrueDolphin/references wiki](https://github.com/TrueDolphin/references/wiki/EnScript-(Enforce-Script)-Style-Guide).

Vanilla facts: Logging and side checks are checked in `../enscript/references/api_game.md`.

## Debugging and Tracing

### Debug traces: Expansion only

The `EXTrace` and `EXError` helpers and the `EXPANSIONTRACE` define that older copies of this guide showed belong to the DayZ Expansion mod. `class EXTrace` is defined in `P:\Mods\@DayZ-Expansion-Core\Addons\core_scripts.pbo`, `3_Game\DayZExpansion_Core\ExpansionTracing.c:30`, and `class EXError` in the same PBO at `3_Game\DayZExpansion_Core\ExpansionStatic.c:139`. The define is commented out (`//#define EXPANSIONTRACE`) in `P:\Mods\@DayZ-Expansion-Core\Addons\0_core_preload.pbo`, `Common\DayZExpansion_Core_Defines.c:45`, so the `#ifdef EXPANSIONTRACE` guards are off by default. They are not vanilla, so they are not general practice; do not use them in a mod that does not depend on Expansion. For a stack trace in vanilla, call `DumpStack()` (`P:\scripts\1_core\proto\endebug.c:27`) or `DebugPrint.LogErrorAndTrace(string msg)`, which logs the message as an error with a trace (`P:\scripts\3_game\tools\debugprint.c:124`). Put temporary traces behind your own define (see Debug Defines below).

### Logging

Vanilla logs with `Print(...)` (`proto void Print(void var)`, `P:\scripts\1_core\proto\endebug.c:96`) and reports errors with `ErrorEx(string err, ErrorExSeverity severity = ErrorExSeverity.ERROR)` (`endebug.c:83`). `ErrorExSeverity` has `INFO`, `WARNING` and `ERROR`; `WARNING` is at `endebug.c:64`. Prefix every line with your mod tag so it can be found in `script.log`:

```
Print("[MyMod] loaded " + count + " entries");
ErrorEx("[MyMod] unknown state " + stateName);
ErrorEx("[MyMod] config uses a removed key", ErrorExSeverity.WARNING);
```

More on logging and when `Debug.Log` prints: `../enscript/references/api_game.md`.

### Error Logs

**Exception logs** are named `crash_<date>_<time>.log`, but they contain exceptions, not actual crashes (segfaults). Actual segfaults create different crash dumps. This naming is unverified: the engine writes these files, and nothing under `P:\scripts` names them.

### Debug Defines

```
//#define MYMOD_SETTINGS_LOGGING
//#define MYMOD_RPC_LOGGING
```

Comment out defines that should not be in production code.

---

## Error Handling

### Existence/Null Checks

1. Existence/Null checks should be done where you know how to handle such cases; propagate the non-nullness guarantee to other methods with `notnull`

```
void Foo()
{
    EntityAI entity = FindSomeEntitySomehow();
    Print(IsWearingSunglasses(entity));
}

bool IsWearingSunglasses(EntityAI entity)
{
    if (entity == null)
    {
        // WRONG: we don't know how to handle null variables
        return false;
    }
    return true;
}

void Foo()
{
    EntityAI entity = FindSomeEntitySomehow();
    if (!entity)
    {
        // CORRECT: we do know what to do with a null value
        Print("entity not found");
        return;
    }
    Print(IsWearingSunglasses(entity));
}
```

2. Use null checks when a null value is semantically valid

`GetInventory()` is a native method declared on `EntityAI` (`proto native GameInventory GetInventory();`, `P:\scripts\3_game\entities\entityai.c:1884`). Its declaration says nothing about when it returns null, so the comments in examples 2 and 3 are illustrations of the rule, not checked engine guarantees (unverified: engine behaviour). Keep a null check whenever you are not sure.

```
bool IsWearingSunglasses(notnull EntityAI entity)
{
    GameInventory inventory = entity.GetInventory();
    if (!inventory)
    {
        // CORRECT: here null is treated as "this entity has no inventory",
        // hence it isn't wearing sunglasses (unverified: engine behaviour)
        return false;
    }
    return true;
}
```

3. Avoid unnecessary checks

```
bool IsPlayerWearingSunglasses(notnull PlayerBase player)
{
    GameInventory inventory = player.GetInventory();
    if (!inventory)
    {
        // AVOID (illustration): if your code guarantees a player always has an
        // inventory, this check only hides a deeper bug (unverified: engine behaviour)
        return false;
    }
    return true;
}
```

**Important:** `if (something)` does not just check for null: it checks whether the value evaluates to true. For objects, this means checking existence.

### Value Validation

`typename.StringToEnum` returns `-1` when no enum member has the given name (`P:\scripts\1_core\proto\enconvert.c:670-683`, `return -1;` at line 683), so test for `-1` before using the value:

```
int value = typename.StringToEnum(EMyMod_State, stateName);
if (value == -1)
{
    ErrorEx("[MyMod] unknown state " + stateName);
}
else
{
    m_State = value;
}
```

### Client/Server Checks

**CRITICAL: g_Game Behavior During Load**

The `IsClient()` and `IsServer()` methods can give the wrong answer early in game load. Vanilla states only that `IsDedicatedServer()` "is valid much sooner" than them (`P:\scripts\3_game\global\game.c:1121-1125`); the exact wrong values in the comments below are unverified (they are engine behaviour, not visible in script).

```
// AVOID in early init: may return false on a client during load (unverified)
if (GetGame().IsClient())

// CORRECT: Client, or offline single player (also true there, where this process is the server too)
if (!g_Game.IsDedicatedServer())

// AVOID in early init: may return true on a client during load (unverified)
if (GetGame().IsServer())

// CORRECT: Reliable server check (dedicated only)
if (g_Game.IsDedicatedServer())

// CORRECT: Offline / single player only (false on a dedicated server)
if (!g_Game.IsMultiplayer())

// CORRECT: Any server, dedicated or offline
if (!g_Game.IsMultiplayer() || g_Game.IsDedicatedServer())
```

**Rule:** In early init use `IsDedicatedServer()` to skip client-only work, and `!g_Game.IsMultiplayer() || g_Game.IsDedicatedServer()` for authority work that must also run offline; after load use `IsServer()` for authority work (`_shared/enscript/references/api_game.md`). Vanilla calls `IsDedicatedServer()` a "robust check which is preferred than the above, as it is valid much sooner" (`P:\scripts\3_game\global\game.c:1121-1125`).
