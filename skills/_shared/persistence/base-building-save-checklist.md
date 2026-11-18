# Base building save checklist

What to check before a change to how a buildable object saves its parts goes out: the bit mask layout, the 93 part cap, the save order, the version rules and the in game restart test. A change that adds parts, changes `id` values or the mask packing, or touches `OnStoreSave` or `OnStoreLoad` changes player progression; a bug here loses bases on the next restart. Run the deep audit in `deep-audit.md` as well.

## Parts are bits in three ints

Built state is not stored per part. It is packed into `m_SyncParts01`, `m_SyncParts02` and `m_SyncParts03` (`P:\scripts\4_world\entities\itembase\basebuildingbase.c:10` to `:12`), registered for net sync in the constructor (`:43` to `:45`). The same three ints are both the network sync and the save; there is no separate record per part.

| Part `id` | Int |
|---|---|
| 1 to 31 | `m_SyncParts01` |
| 32 to 62 | `m_SyncParts02` |
| 63 to 93 | `m_SyncParts03` |

`RegisterPartForSync` does the bit work (`basebuildingbase.c:136` to `:163`).

## The 93 part cap

Three ints of 31 used bits give at most 93 parts per `BaseBuildingBase` object. Every `id` in the `Construction` block must be unique and between 1 and 93. A duplicate makes two parts share a bit, so they toggle together. An `id` outside the range matches no branch of `RegisterPartForSync`, so its bit is never set and the part is lost on every restart. Nothing warns at run time; check the ids by hand or with a script.

## Save order

- `OnStoreSave` (`basebuildingbase.c:419` to `:429`) writes `m_SyncParts01`, `m_SyncParts02`, `m_SyncParts03`, then `m_HasBase`.
- `OnStoreLoad` (`basebuildingbase.c:431` to `:463`) reads them in that order and returns `false` on any failed read.

A subclass writes and reads its own fields after `super`, in the same order both ways. The Fence appends `m_GateState` and `m_IsOpened` (`P:\scripts\4_world\entities\itembase\basebuildingbase\fence.c:255` to `:263` save, `:265` to `:298` load). Reorder either side, or write before `super`, and every saved base loads wrong.

## What the load rebuilds

`AfterStoreLoad` (`basebuildingbase.c:465` to `:473`) calls `SetPartsAfterStoreLoad` (`:475` to `:486`), which rebuilds the parts from the masks, sets the base state and syncs. When `m_FixDamageSystemInit` is set, the rebuild runs from `EEOnAfterLoad` half a second later instead (`:504` to `:512`). `OnCreatePhysics` runs the same rebuild again (`:488` to `:494`). `SetPartFromSyncData` (`:264` to `:304`) also locks attached materials again, as a "failsafe for corrupted sync/storage data" (`:302`). The full call chain is in `base-building-lifecycle.md`.

## Versions

Two version numbers appear here, and both belong to the game:

- `GetDamageSystemVersionChange()` returns `111` (`basebuildingbase.c:1132` to `:1135`).
- `Fence.OnStoreLoad` reads and throws away one `bool` for a save older than storage version 110, then the gate fields (`fence.c:265` to `:298`).

A mod cannot raise either. When you add a saved field, write your mod's own version first, raise it, and branch on it so old saves load with the old layout. Never branch on the game's `version` (`versioning-and-migration.md`).

## Map buildings save differently

A rebuildable map building saves through `Rebuilding`: its own `REBUILDING_STORAGE_VERSION`, ten ints and two bits per part, up to 160 ids (`P:\scripts\4_world\classes\rebuilding\rebuilding.c:3`, `:7` to `:16`, `:473` to `:514`). Never put rebuild parts on a `BaseBuildingBase` or write the ten int block from a fence or watchtower subclass. The details are in `base-building-rebuildable.md`.

## Locks on the object

- A `CombinationLock` saves a third value, `m_CombinationInside`, read only from storage version 143 (`P:\scripts\4_world\entities\itembase\combinationlock.c:128` to `:136` and `:169` to `:177`). A modded `OnStoreLoad` that always reads the old two values after `super` shifts every later field.
- A `DigitalCodeLock` saves `m_LockPIN`, `m_IsLocked` and `m_DoorIndex` through its `CodeLockComponent` (`P:\scripts\4_world\classes\codelockcomponent.c:257` to `:262`).

The stream changes are in `dayz-1-30-persistence.md`, the fence locks in `base-building-fence-gate.md`.

## The checklist

1. Every part `id` in the `Construction` block is unique and between 1 and 93.
2. `OnStoreSave` and `OnStoreLoad` write and read the same fields in the same order.
3. Every subclass writes and reads its fields after `super`, in the same order both ways.
4. A new saved field raises the mod's own version, written first, and adds a branch on it for old saves; it does not branch on the game's `version`.
5. Kill the server between each read and write of the save and load, step by step, and check whether the next boot gets the base back or loses parts.
6. The material relock in `SetPartFromSyncData` (`basebuildingbase.c:302`) still runs.
7. The class is either a `BaseBuildingBase` (3 ints, 1 bit, ids 1 to 93) or uses `Rebuilding` (10 ints, 2 bits), never both.
8. An object that takes a `CombinationLock` handles storage version 143 in `OnStoreLoad`.
9. In game: build parts, restart the server, and confirm every part and the base come back. Some lost base bugs show only on a real restart.

## Not covered here

`TerritoryFlag: BaseBuildingBase` is declared at `P:\DZ\gear\camping\config.cpp:12480`. Its saved refresher fields are in `base-building.md`, section "Territory flag"; its radius and decay are not traced. No script on `P:\` reads the `show_on_init` config key.
