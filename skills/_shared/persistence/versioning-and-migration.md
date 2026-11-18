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
| `if (version >= 140)` stomach temperature, in `PlayerStomach.OnStoreLoad` (`:471`) | `P:\scripts\4_world\classes\playerstomach.c:492` |

Some vanilla subsystems also declare a storage version of their own through `GetStorageVersion()` (`P:\scripts\4_world\classes\playerstomach.c:255`, `P:\scripts\4_world\classes\playermodifiers\modifiersmanager.c:178`; `ModifiersManager.OnStoreLoad` at `modifiersmanager.c:273`). These track engine compatibility; none of them versions a mod release.

A mod must not change `GAME_STORAGE_VERSION`. It belongs to the game and moves with game updates, not with your releases, so it cannot tell you which version of your mod wrote a record. Write your own version.

The number was 142 on DayZ 1.29 (the 1.29 scripts are not on `P:\`, so this is not checked here), so a record saved on 1.29 arrives with `version` 142 and skips the two `>= 143` gates above.

Not every vanilla field is gated. `PlayerBase` writes a thermal value through `m_ThermalBiasHandler` after the arrow manager (`P:\scripts\4_world\entities\manbase\playerbase.c:7395`) and reads it back with no version check, failing the whole load when the read fails (`m_ThermalBiasHandler` at `P:\scripts\4_world\entities\manbase\playerbase.c:7520` to `:7524`; the value is the float `m_TemporaryResistanceTime`, `P:\scripts\4_world\classes\thermalbiashandler.c:72-77`). A player record from 1.29 has no such value (the 1.29 scripts are not on `P:\`, so this is not checked here). Two lessons for mod code: gate every field you add, and a `modded class PlayerBase` that copies the old save tail instead of calling `super` breaks on the next game update. The 1.30 changes are listed with the vanilla code in `dayz-1-30-persistence.md`.

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

### Classify every input before changing a format

A reader meets more than "old" and "new". Before a format change ships, say what the reader does with each of these seven inputs: its verdict, how much it consumes, what state it keeps, and whether it writes.

| Input | What the reader does |
|---|---|
| Fresh (no record) | Defaults; the current version is written at the next save |
| Legacy with no version header | Recognise the old layout, read all of it, migrate; rewrite only after a backup |
| Known version | Read exactly the fields of that version |
| Future version (saved by a newer mod) | Reject without applying or writing anything; log once per rate limit window |
| Truncated or damaged | Reject the whole record; keep the state from before the load |
| Same game build, new mod version | Migrate by the mod's own version, never by the game's |
| Old reader, new data (rollback) | State what the old build does with the new record before shipping the new format |

A rejecting reader never writes: no defaults saved over the record, no repair in place. Vanilla is not a model here. `Rebuilding` rejects a stored version lower than its own but accepts a higher one (`m_LastStorageVersion < REBUILDING_STORAGE_VERSION` at `P:\scripts\4_world\classes\rebuilding\rebuilding.c:520`), so a newer layout would be read as if it were the current one.

When a design that leaves the format unchanged gives the same result, propose it first. The full table, the write rule and the mutation check that proves the tests can fail are in `migration-matrix.md`.

### The class must still exist

A stream that matches byte for byte cannot keep an entity the engine no longer creates. When comparing a release with the last one, also compare the class name, its declared parent, its `scope` and its entry in `CfgPatches` `units[]`, and compare the config in the built PBO, not only the source `config.cpp`.

## Adding saved fields to a vanilla class

A `modded class` on a vanilla parent (for example `modded class ItemBase`) puts your values in the middle of the chain: after `ItemBase` and before every subclass. `BaseBuildingBase`, for example, calls `super` and then reads its part masks (`P:\scripts\4_world\entities\itembase\basebuildingbase.c:432` to `:440`), so its values come straight after yours.

That causes two kinds of data loss that no version number can catch:

* **Adding the mod to a server with existing saves.** Old records have no values from you, so your first `Read` takes the next class's data. A version header does not help, because the "version" you read is someone else's value.
* **Removing the mod.** Records now hold your values, and the next class reads them as its own.

So, in order of preference:

1. Save new state on your own classes (`MyMod_...`), which have no old records.
2. If a vanilla class must carry new saved state, ship it only on a fresh server, and say so in the audit report.
3. Or use a framework that gives each mod its own storage block. Community Framework does this; it is not part of vanilla, so its API is not checked here. See `_shared/enscript/integrations/community_framework.md`.

What Community Framework's ModStorage gives (third-party mod behaviour, not yet checked on `P:\`): it writes a framework version, a mod count and one framed block per mod; it hands each mod the `storageVersion` set in its `CfgMods` entry, so the mod can version its own block; and when a mod that owns a block is not loaded, it writes that block back unchanged, so the data is there again after the mod is added back. It does not define the mod's upgrade paths, and it cannot keep values a `modded class` appended outside its framing. The CF line references are in `cf-modstorage.md`.

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

### Replacing a file is not atomic

Script can delete and copy a file but cannot rename or move one: `DeleteFile` and `CopyFile` are the only two (`P:\scripts\1_core\proto\ensystem.c:528` and `:531`), and their comments say they work only on `$profile:` and `$saves:` paths. So "write a temp file, then replace" is really `DeleteFile` on the destination followed by `CopyFile` from the temp file, and between the two calls the destination does not exist. Treat a comment that claims an atomic save as a defect.

A save that can be recovered at every step:

1. Write the whole new record to `<file>.tmp` and close it.
2. Open the temp file again, read and parse it, and check it holds what you meant to write.
3. Copy the current file to `<file>.bak`. If that fails, stop; the original is untouched.
4. Delete the destination, then copy the temp file onto it.
5. Read the destination back and check it. If it is short or invalid, delete it and keep the temp and backup files.
6. Delete the temp file only after step 5 passed.

On load, judge a leftover `.tmp` by its content, never by its date. The full contract, with the nine places an I/O failure can strike and what must survive each one, is `sidecar-files.md`.

Vanilla's own mission file is a counter example, not a pattern: `BunkerBroadcastPersistenceStorage` writes `$mission:BunkerBroadcastPersistenceStorage.bin` with a `FileSerializer`, no version header, and a `Load` that ignores what `Read` returns (`STORAGE_PATH` at `P:\scripts\4_world\classes\bunkerbroadcasthandler.c:18`; `Load` at `P:\scripts\4_world\classes\bunkerbroadcasthandler.c:56`).
