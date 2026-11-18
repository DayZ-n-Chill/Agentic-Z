# Saving entities and files

How an entity saves its fields across restarts with its own version number, which config key makes it persistent, and which file calls to use for JSON and safe writes. The full save contract is in `_shared/persistence/` and `../patterns/persistence.md`; path tokens and `FileMode` are in `../references/file_paths.md`.

## Save and load in the same order

`OnStoreSave` and `OnStoreLoad` read and write one unnamed stream, so the load reads exactly what the save wrote, in the same order, and returns false on any failed read.

The `version` argument of `OnStoreLoad` is the game's storage version (`GAME_STORAGE_VERSION`, `P:\scripts\3_game\global\game.c:5`), not your mod's. Write your own version number first and branch on it:

```c
const int MYMOD_SAVE_VERSION = 2;

override void OnStoreSave(ParamsWriteContext ctx)
{
    super.OnStoreSave(ctx);
    ctx.Write(MYMOD_SAVE_VERSION);
    ctx.Write(m_PoweredNet);
    ctx.Write(m_NewField);
}

override bool OnStoreLoad(ParamsReadContext ctx, int version)
{
    if (!super.OnStoreLoad(ctx, version))
        return false;
    int saveVersion;
    if (!ctx.Read(saveVersion))
        return false;
    if (!ctx.Read(m_PoweredNet))
        return false;
    if (saveVersion >= 2)
    {
        if (!ctx.Read(m_NewField))
            return false;
    }
    else
    {
        m_NewField = MYMOD_DEFAULT_VALUE;
    }
    return true;
}
```

Change the saved layout without a version and every entity with old data fails to load and is lost. One large mod wipes saves on a major layout change instead of migrating.

## Which entities persist

Persistent entities carry `storageCategory` in `config.cpp`. `Inventory_Base` already sets `storageCategory = 1` (`P:\DZ\data\config.cpp:3170`), so a class derived from it inherits it. What the other values vanilla uses mean is not checked on `P:\`.

## JSON files

Use `JsonFileLoader<T>.LoadFile(string filename, out T data, out string errorMessage)` (`P:\scripts\3_game\tools\jsonfileloader.c:7`) and `SaveFile` (`:42`), and check both the `bool` result and the error text. The older `JsonLoadFile` and `JsonSaveFile` return `void` (`:105`) and cannot report failure; never use them in new code. JSON file calls are synchronous and block the main thread, so never call them from `OnUpdate()`.

## Other file calls

| Call | Use |
|---|---|
| `FileExist(path)` | Does the file exist |
| `CopyFile(src, dst)` | Copy |
| `DeleteFile(path)` | Delete |
| `MakeDirectory(path)` | Create a folder |

There is no `RenameFile`; no vanilla script under `P:\scripts\` names one. Copy, then delete.

## A save that cannot leave a half-written file

1. Write to a `.tmp` file.
2. Optionally, behind a setting, check that the `.tmp` reads back.
3. Copy the current file to `.bak`.
4. `CopyFile` the `.tmp` over the target.
5. `DeleteFile` the `.tmp`.
6. On load, if the target is missing and a `.bak` exists, restore from it.
