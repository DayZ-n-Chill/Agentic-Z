# Enforce Script style: Debugging and error handling

Part of the Enforce Script style guide; the index and the task table are in `../enscript-style.md`. The guide is a mirror of the [TrueDolphin/references wiki](https://github.com/TrueDolphin/references/wiki/EnScript-(Enforce-Script)-Style-Guide).

Vanilla facts: Logging and side checks are checked in `../enscript/references/api_game.md`.

## Debugging and Tracing

### Debug traces: Expansion only

The `EXTrace` and `EXError` helpers and the `EXPANSIONTRACE` define that older copies of this guide showed belong to the DayZ Expansion mod. They exist only when Expansion is loaded, so they are not general practice; do not use them in a mod that does not depend on Expansion. Vanilla has no trace helper; put temporary traces behind your own define (see Debug Defines below).

### Logging

Vanilla logs with `Print(...)` and reports errors with `ErrorEx(string err, ErrorExSeverity severity = ErrorExSeverity.ERROR)` (`P:\scripts\1_core\proto\endebug.c:83`). Prefix every line with your mod tag so it can be found in `script.log`:

```
Print("[MyMod] loaded " + count + " entries");
ErrorEx("[MyMod] unknown state " + stateName);
ErrorEx("[MyMod] config uses a removed key", ErrorExSeverity.WARNING);
```

More on logging and when `Debug.Log` prints: `../enscript/references/api_game.md`.

### Error Logs

**Exception logs** are named `crash_<date>_<time>.log`, but they contain exceptions, not actual crashes (segfaults). Actual segfaults create different crash dumps.

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

```
bool IsWearingSunglasses(notnull EntityAI entity)
{
    GameInventory inventory = entity.GetInventory();
    if (!inventory)
    {
        // CORRECT: `GetInventory` returning null means that the entity
        // has no inventory at all, hence it isn't wearing sunglasses
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
        // AVOID: an instance of a player will always have an inventory
        // If for some reasons the player inventory is null, there probably are some other serious issues
        return false;
    }
    return true;
}
```

**Important:** `if (something)` does not just check for null: it checks whether the value evaluates to true. For objects, this means checking existence.

### Value Validation

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

The `IsClient()` and `IsServer()` methods behave unexpectedly during game load:

```
// WRONG: Returns false on client during load
if (GetGame().IsClient())

// CORRECT: Reliable client check
if (!g_Game.IsDedicatedServer())

// WRONG: Returns true on client during load
if (GetGame().IsServer())

// CORRECT: Reliable server check (dedicated only)
if (g_Game.IsDedicatedServer())

// CORRECT: Server check including offline/singleplayer
if (g_Game.IsServer() && !g_Game.IsMultiplayer())
```

**Rule:** Use `IsDedicatedServer()` for reliable client/server detection, especially in initialization code. Vanilla says the same: it calls `IsDedicatedServer()` a "robust check which is preferred than the above, as it is valid much sooner" (`P:\scripts\3_game\global\game.c:1121-1125`).
