# Save streams on 1.30

What DayZ 1.30 changed in the vanilla save streams: the storage version, the construction data ahead of the energy data, the player's thermal value, the combination lock's third value, the code lock, the rebuildable building block and the bunker broadcast file. Open it when porting a 1.29 mod that saves data, or when a 1.29 save loads wrong on 1.30.

The 1.29 scripts are not on `P:\`. Every statement of what 1.29 did is a comparison that is not checked here; every 1.30 fact cites the current scripts.

## What changed

| Part of the save | 1.29 | 1.30 | Effect on a 1.29 mod |
|---|---|---|---|
| `GAME_STORAGE_VERSION` | 142 | 144 (`P:\scripts\3_game\global\game.c:5`) | the hook's `version` on a 1.30 save is 144 |
| Start of the `EntityAI` stream | energy or nothing, then the variables | the construction block first, read only when `version >= 143` | a mod that skips `super` or counts values misreads rebuilt houses |
| End of the `PlayerBase` stream | ends with the arrow manager | adds one thermal float, with no version check | a 1.29 player record fails to load on a 1.30 server |
| `CombinationLock` | two values | a third value, read only when `version >= 143` | a subclass that reads two values itself shifts every later field |
| `DigitalCodeLock` | not in the game | `super`, then the code lock component | new item; old worlds have none |
| `BaseBuildingBase` | three masks and `m_HasBase` | the same | no change |
| `Rebuilding` on map houses | not in the game | its own version and ten ints in the construction block | not a pattern for a mod's own version check |
| `$mission:BunkerBroadcastPersistenceStorage.bin` | not in the game | a mission file of two objects, no header, reads unchecked | not a model for a mod's own file |

## The storage version is 144

`static int GAME_STORAGE_VERSION = 144;` (`P:\scripts\3_game\global\game.c:5`). `CGame` passes it to `StorageVersion` (`game.c:50`) and exposes `proto native int SaveVersion()` (`:435`). The combination lock and the construction block check `version >= 143`, so a 1.29 record stored as 142 skips them. The thermal float has no check.

Never compare `SaveVersion()` with a hard coded number from one game version, and never branch your own data on it (`versioning-and-migration.md`).

## The construction block comes before energy

`EntityAI.OnStoreSave` first asks the construction component to write, then writes the energy values:

```c
// P:\scripts\3_game\entities\entityai.c:2910
void OnStoreSave (ParamsWriteContext ctx)
{
    ConstructionBasic constructionComponent = GetConstructionBasic();
    if (constructionComponent)
        constructionComponent.HandleStoreSave(ctx);

    // Saving of energy related states
    if ( m_EM )
    {
```

`OnStoreLoad` reads the block only when `version >= 143` and a component exists (`entityai.c:2978` to `:2983`). On `ConstructionBasic` the hook writes nothing and `HandleStorageEvents` returns `false` (`P:\scripts\3_game\systems\construction_basic.c:29` to `:35`), so a player built fence has an empty block. Only `Rebuilding` writes one.

The energy part still has eight values when an energy manager exists: `m_EM.GetEnergy()`, `IsPassive()`, `IsSwitchedOn()`, `IsPlugged()`, and the energy source's persistent id in four ints (`entityai.c:2920` to `:2947`), then `SaveVariables` (`:2951`). `LoadVariables` still runs only when `version >= 140` (`entityai.c:3053` to `:3058`). The full layout is in `save-load-contract.md`.

## The player's thermal value

`PlayerBase` saves and loads at `P:\scripts\4_world\entities\manbase\playerbase.c:7353` and `:7408`. On a multiplayer server save, after the arrow manager, it calls `m_ThermalBiasHandler.OnStoreSave(ctx)` (`playerbase.c:7395`). The load has no version check:

```c
// P:\scripts\4_world\entities\manbase\playerbase.c:7514
if (version >= 134)
{
    ArrowManagerPlayer arrowManager = ArrowManagerPlayer.Cast(GetArrowManager());
    arrowManager.Load(ctx);
}

if (!m_ThermalBiasHandler.OnStoreLoad(ctx, version))
{
    Print("---- failed to load ThermalBiasHandler, read fail  ----");
    return false;
}
```

The handler saves one float, `m_TemporaryResistanceTime`, and returns `false` when the read fails (`P:\scripts\4_world\classes\thermalbiashandler.c:67` to `:78`).

A 1.29 player record in `storage_1/players.db` ends after the arrow manager, with no float (the 1.30 save writes the arrow manager at `playerbase.c:7392` and `:7393`, then the float). A 1.30 multiplayer server always reads it, so the load fails with `failed to load ThermalBiasHandler`; nothing fills in a default. A mod that overrides `PlayerBase.OnStoreSave` or `OnStoreLoad` must keep calling `super` in the same place. Fields put before `super`, or after a copied 1.29 ending without the float, load the rest of the record wrong. Do not add your own version check around the thermal value unless you also stop writing it.

## The combination lock's third value

`CombinationLock.OnStoreSave` writes `m_Combination`, `m_CombinationLocked` and `m_CombinationInside` after `super` (`P:\scripts\4_world\entities\itembase\combinationlock.c:128` to `:136`). The load reads the third value only from version 143:

```c
// P:\scripts\4_world\entities\itembase\combinationlock.c:169
if (version >= 143)						//added with 143
{
    //combination two (inside lock)
    if (!ctx.Read(m_CombinationInside))
    {
        m_CombinationInside = 0;
        return false;
    }
}
```

A 1.29 lock (version 142) still loads; the third value is skipped. A mod that calls `super.OnStoreSave` but writes its own `OnStoreLoad` without the version 143 branch reads `m_CombinationInside` as its own next field.

Vanilla sets defaults such as `m_Combination = 0` before returning `false` on a failed read (`combinationlock.c:145` to `:148`). That leaves half applied state, which `where-to-save.md` rules out for mod code; read into locals and apply only after every read succeeds.

## The code lock

`DigitalCodeLock` saves `super`, then its `CodeLockComponent` (`P:\scripts\4_world\entities\itembase\codelock.c:505` and `:512`). The component writes `m_LockPIN`, `m_IsLocked` and `m_DoorIndex` (`P:\scripts\4_world\classes\codelockcomponent.c:257` to `:262`) and reads them back with no version check, since the class is new. A failed PIN read sets `m_LockPIN` to empty and `m_HasPIN` to false before returning `false` (`codelockcomponent.c:264` onwards): the same half applied state, not to be copied.

## Base building and rebuilt houses

`BaseBuildingBase.OnStoreSave` still writes `super`, `m_SyncParts01`, `m_SyncParts02`, `m_SyncParts03` and `m_HasBase` (`P:\scripts\4_world\entities\itembase\basebuildingbase.c:419` to `:429`). Its construction block is empty, so the 93 part packing lives in those three ints.

`Rebuilding`, on map houses, writes through the `EntityAI` block: `REBUILDING_STORAGE_VERSION` (1), then `m_SyncParts1` to `m_SyncParts10` (`P:\scripts\4_world\classes\rebuilding\rebuilding.c:3` and `:501` to `:514`). `DeserializeConstructionData` rejects a stored version below the current one but accepts one above it (`rebuilding.c:518` to `:524`), the opposite of the "future version" case in `migration-matrix.md`. Do not copy it: an extra int written after the ten by a later build would be read as energy data, and the rest of the house would load wrong. The full layout is in `base-building-rebuildable.md`.

## The bunker broadcast file

`BunkerBroadcastPersistenceStorage` is not an entity stream. It keeps its own file, `STORAGE_PATH = "$mission:BunkerBroadcastPersistenceStorage.bin"`, holding a `BunkerBroadcastHandlerPersistenceData` and a `BunkerBroadcastSchedulerPersistenceData` (`P:\scripts\4_world\classes\bunkerbroadcasthandler.c:16` to `:21`). The payload is `m_LastReportHour` and `m_LastReportMinute` ints and a `TIntStringMap m_LastActiveBunkers`, bunker id to lock code (`:5` to `:14`).

| Method | What it does | Source |
|---|---|---|
| `Load` | opens the file with a `FileSerializer`, reads the handler data then the scheduler data, closes, returns `true`; returns `false` only when the file does not open | `bunkerbroadcasthandler.c:56` to `:69` |
| `Save` | opens the file for writing, writes the two objects, closes | `bunkerbroadcasthandler.c:73` to `:82` |

There is no version header. `FileSerializer.Read` returns `bool` (`P:\scripts\1_core\proto\serializer.c:58`), and `Load` ignores it and returns `true` once the file opens. `DeleteFile` and `CopyFile` work only under `$profile:` and `$saves:` (`P:\scripts\1_core\proto\ensystem.c:528` to `:532`), so the recoverable file replace in `sidecar-files.md` cannot be done on `$mission:` with them.

Treat this file as a vanilla exception, not a template. A mod that keeps similar state writes a version header, checks every `Read`, and saves under `$profile:` or `$saves:`, where backup, delete and copy work. Never describe a `$mission:` `FileSerializer` overwrite as atomic.

`JsonFileLoader<T>.LoadFile` and the deprecated `JsonLoadFile` are at `P:\scripts\3_game\tools\jsonfileloader.c:7` to `:40` and `:104` to `:131`. No 1.30 change to CF ModStorage is checked (`cf-modstorage.md`).

## What breaks in a 1.29 mod

| Break | What you see |
|---|---|
| A `PlayerBase` override copies the 1.29 ending without the thermal float, or never calls `super` | `---- failed to load ThermalBiasHandler, read fail  ----` in the log, and the player record does not load |
| A `CombinationLock` subclass reads two values after `super`, or skips `super` | the subclass reads `m_CombinationInside` as its own field, and every later value in that record is one int off; attachments and cargo are separate records (`save-load-contract.md`), and whether a misread parent affects them is engine behaviour not checked on `P:\` |
| An `EntityAI` subclass on a rebuilt house skips `super` or jumps a fixed count past the energy data | the construction block, which comes first, is misread |
| A mod relies on `BunkerBroadcastPersistenceStorage` being atomic or backed up | it is neither |

## Porting checklist

- Call `super.OnStoreSave` and `super.OnStoreLoad` on `PlayerBase`, `CombinationLock`, `DigitalCodeLock` and any entity with a construction component; never copy the 1.29 ending by hand.
- In a `CombinationLock` subclass, read `m_CombinationInside` from version 143 on, or leave it to `super`.
- Treat a 1.29 player record on a 1.30 server as truncated: it fails at the thermal float, and vanilla does not migrate it (`migration-matrix.md`).
- Keep the 93 part packing on player built objects; never apply the `Rebuilding` block or its version to them.
- Keep mission wide state in a file under `$profile:` or `$saves:` with the pattern in `sidecar-files.md`, not with an unchecked `FileSerializer` overwrite.
- After a game update, search for each method name again; line numbers move.
