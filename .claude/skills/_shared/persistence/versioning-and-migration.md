# Versioning and migration

How to stamp your own save version, change what you save without breaking old saves, and where data that is not tied to one object belongs.

## Contents

- [Two version numbers](#two-version-numbers)
- [Your own version, written first](#your-own-version-written-first)
- [Changing what you save](#changing-what-you-save)
- [Adding saved fields to a vanilla class](#adding-saved-fields-to-a-vanilla-class)
- [Config changes that need a reset](#config-changes-that-need-a-reset)
- [Data outside the object store](#data-outside-the-object-store)

## Two version numbers

The `version` argument of `OnStoreLoad` is the game's storage version, not yours. The game sets it from `GAME_STORAGE_VERSION` (144 on this build, `P:\scripts\3_game\global\game.c:5`) by calling `StorageVersion` at startup (`:50`, native at `:425`). `LoadVersion()` and `SaveVersion()` return the version being loaded and saved (`:430` and `:435`).

Vanilla gates its own fields on that number:

| Gate | Source |
|---|---|
| `if (version >= 143 && constructionComponent)` | `P:\scripts\3_game\entities\entityai.c:2981` |
| `if (version >= 140)` load variables | `P:\scripts\3_game\entities\entityai.c:3053` |
| `if (version >= 114)` quick bar flag | `P:\scripts\4_world\entities\itembase.c:3103` |
| `if (version < 105)` read a removed field | `P:\scripts\4_world\entities\itembase\combinationlock.c:160` |
| `if (version >= 143)` read a new field | `P:\scripts\4_world\entities\itembase\combinationlock.c:169` |

A mod must not change `GAME_STORAGE_VERSION`. It belongs to the game and moves with game updates, not with your releases, so it cannot tell you which version of your mod wrote a record. Write your own version.

## Your own version, written first

Write your version as the first value after `super`, and read it first after `super`. Every later read can then branch on it.

```c
class MyMod_Safe : Container_Base
{
    static const int MYMOD_SAFE_SAVE_VERSION = 2;

    protected string m_MyMod_Owner;   // added in version 1
    protected int m_MyMod_Opens;      // added in version 2

    override void OnStoreSave(ParamsWriteContext ctx)
    {
        super.OnStoreSave(ctx);
        ctx.Write(MYMOD_SAFE_SAVE_VERSION);
        ctx.Write(m_MyMod_Owner);
        ctx.Write(m_MyMod_Opens);
    }

    override bool OnStoreLoad(ParamsReadContext ctx, int version)
    {
        if (!super.OnStoreLoad(ctx, version))
            return false;

        int saveVersion;
        if (!ctx.Read(saveVersion))
            return false;

        if (!ctx.Read(m_MyMod_Owner))
            return false;

        if (saveVersion >= 2)
        {
            if (!ctx.Read(m_MyMod_Opens))
                return false;
        }
        else
        {
            m_MyMod_Opens = 0;
        }

        return true;
    }
}
```

`Container_Base` is the vanilla container parent (`P:\scripts\4_world\entities\itembase\container_base.c:1`). The pattern matches the vanilla chain in `P:\scripts\3_game\entities\entityai.c:2910` and `:2978`.

## Changing what you save

| Change | What to do | Vanilla model |
|---|---|---|
| Add a field | Write it last. Bump your version. Read it only when the saved version is at least the new one; otherwise set a default and carry on. | `combinationlock.c:169` |
| Remove a field | Stop writing it and bump your version. When the saved version is older, still read the old value into a local variable and throw it away, so the reads after it stay aligned. | `combinationlock.c:160` to `:167` |
| Change a field's type or meaning | Treat it as a remove plus an add: read the old form for old versions, convert it, write only the new form. | |
| Reorder fields | Do not. If you must, it is a remove plus an add for every moved field. | |

Rules for every upgrade path:

1. An old save is not an error. Never return `false` because a field is missing from an older version; set the default.
2. Keep every old branch for as long as any server may still hold a save from that version. Removing a branch strands those saves.
3. A save from a newer version than the running mod (a server rolled back) holds fields this build does not know. Tell server owners not to roll a mod back after it has saved data; the audit report says so.
4. Test two paths before each release: a fresh object, and an object saved by the last released version and loaded by the new one.

## Adding saved fields to a vanilla class

A `modded class` on a vanilla parent (for example `modded class ItemBase`) puts your values in the middle of the chain: after `ItemBase` and before every subclass. `BaseBuildingBase`, for example, calls `super` and then reads its part masks (`P:\scripts\4_world\entities\itembase\basebuildingbase.c:432` to `:440`), so its values come straight after yours.

That causes two kinds of data loss that no version number can catch:

* **Adding the mod to a server with existing saves.** Old records have no values from you, so your first `Read` takes the next class's data. A version header does not help, because the "version" you read is someone else's value.
* **Removing the mod.** Records now hold your values, and the next class reads them as its own.

So, in order of preference:

1. Save new state on your own classes (`MyMod_...`), which have no old records.
2. If a vanilla class must carry new saved state, ship it only on a fresh server, and say so in the audit report.
3. Or use a framework that gives each mod its own storage block. Community Framework does this; it is not part of vanilla, so its API is not checked here. See `_shared/enscript/integrations/community_framework.md`.

The same holds for `modded class PlayerBase`. The player's chain also writes its server sections only on a multiplayer server (`P:\scripts\4_world\entities\manbase\playerbase.c:7366`), so mirror any condition you put around a write with the same condition around the read.

## Config changes that need a reset

`ItemBase.GetDamageSystemVersionChange()` returns the storage version at which an item's config `DamageSystem` changed; the default `-1` does nothing (`P:\scripts\4_world\entities\itembase.c:651`). When the loaded version is older, the item re-inits its damage system after load (`:3092`, `:3218`). The barrel returns `110` (`P:\scripts\4_world\entities\itembase\barrel_colorbase.c:24`). It compares against the game's storage version, so it suits vanilla updates; for your own items, reset health from your own save version instead.

## Data outside the object store

Server wide data (stats, lists, settings) does not belong to one object. Keep it in a file under the server profile and write it only on the server.

| Tool | Use | Source |
|---|---|---|
| `JsonFileLoader<T>.LoadFile(filename, out data, out errorMessage)` and `SaveFile(filename, data, out errorMessage)` | Read and write a class as JSON; both return `bool`. The older `JsonLoadFile` and `JsonSaveFile` say to use these instead. | `P:\scripts\3_game\tools\jsonfileloader.c:7`, `:42`, `:104` |
| `FileSerializer` with `Open(path, FileMode)`, `Write`, `Read`, `Close` | Binary file with the same positional rules as the object store | `P:\scripts\1_core\proto\serializer.c:103` to `:110`; example at `:71` |
| `FileExist(name)`, `MakeDirectory(name)` | Check for a file, create the folder first | `P:\scripts\1_core\proto\ensystem.c:397`, `:525` |
| `$profile:` path prefix | The server's profile folder | `P:\scripts\4_world\plugins\pluginbase\pluginrecipesmanager.c:353` |

Put a version field in every JSON file too, and migrate it forward on load; `_shared/enscript/patterns/json_config_migration.md` shows how.
