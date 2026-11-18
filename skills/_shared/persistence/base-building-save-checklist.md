# Persistence audit: the synced bit masks (data-critical)

The hand-off checklist for a base building save change. Line numbers are from the vanilla scripts and configs on `P:\` (game storage version 144). A citation marked `1.29` points at the 1.29 scripts, which are not on `P:\`; those lines were not checked there and are kept as a map for older mods.

**Data audit gate.** Any mod that adds parts, changes the bitmask packing or the `id` ranges, or touches `OnStoreSave`/`OnStoreLoad` ordering is modifying player progression, a bug here means players lose their bases after a server restart. Run the deep audit in `deep-audit.md` before declaring it release-safe.

## 1. The representation, three 31-bit ints, netsync AND save at once

Part-built state is not stored per part. It is packed into three sync ints `m_SyncParts01/02/03` (`P:\scripts\4_world\entities\itembase\basebuildingbase.c:10-12`), registered for netsync in the ctor (`:43-45`). This same representation is both the network sync and the persistence format, there is no separate per-part save record.

Part `id` → bit:

- `id` 1 to 31: `m_SyncParts01`
- `id` 32 to 62: `m_SyncParts02`
- `id` 63 to 93: `m_SyncParts03`

Bit ops in `RegisterPartForSync` (`basebuildingbase.c:137-164`). Also `m_InteractedPartId` / `m_PerformedActionId` (`:13-14`, registered `:46-47`) sync the last action so clients play the right SFX (`SetActionFromSyncData` `:248-262`).

## 2. The 93-part cap

Three ints × 31 usable bits = **93 distinct parts maximum per BaseBuildingBase entity**. Every part's `id` MUST be unique and in 1..93 across the whole `Construction{}` block. A duplicate id makes two parts share a bit (they toggle together); an id outside that range matches no branch of `RegisterPartForSync`, so its bit is never set and the part is lost on every restart. There is no runtime warning, verify by hand or with a script that every `id` in the config is unique and ≤93.

## 3. OnStoreSave / OnStoreLoad, strict ordering

- `OnStoreSave` (`basebuildingbase.c:420-430`): writes `m_SyncParts01`, `02`, `03`, then `m_HasBase`.
- `OnStoreLoad` (`basebuildingbase.c:432-464`): reads the three ints then `m_HasBase`, each guarded with a `return false` on read failure (default-then-abort).

**Subclass-after-super invariant:** a subclass writes/reads its extra fields after calling `super`, in the exact same order in both methods. Fence appends `m_GateState`, `m_IsOpened` after the base three ints (`P:\scripts\4_world\entities\itembase\basebuildingbase\fence.c:246-254` save / `:256-289` load). Reorder either side, or write in the subclass before `super`, and every saved base corrupts on the next load.

## 4. Load reconciliation

- `AfterStoreLoad` (`basebuildingbase.c:466-474`) calls `SetPartsAfterStoreLoad()` (`:476-487`), which calls `SetPartsFromSyncData()`: it rebuilds each part's built flag from the bitmask, sets base state from the base part, re-syncs.
- Guarded by `m_FixDamageSystemInit`, the damage-system migration path uses `EEOnAfterLoad` + a 500ms deferred call instead (`basebuildingbase.c:505-513`).
- `SetPartFromSyncData` (`basebuildingbase.c:265-304`) is the core: per part, compares "built in sync bitmask" vs "built flag", adds/removes constructed parts, shows/hides physics, toggles the `Deployed` proxy for the base, and **failsafe-relocks attached materials** (`:303`, "failsafe for corrupted sync/storage data").

## 5. Version bumps

- Base damage-system version: `GetDamageSystemVersionChange()` returns `111` (`basebuildingbase.c:1133-1136`).
- Fence gate persistence bumped at **v110**, `Fence.OnStoreLoad` reads a discarded bool for `version < 110`, then the gate fields for current versions (`fence.c:256-289`).

Both of those are the game's versions, which a mod cannot raise. When you add a persisted field, write your mod's own version int first, bump it, and branch on it so old saves load with the old layout and new saves with the new one. Never migrate by the game's `version` (`skills/_shared/persistence/versioning-and-migration.md`).

## 6. Data audit hand-off checklist

Before declaring a base-building persistence change release-safe, confirm with the deep audit (`deep-audit.md`):

1. Every part `id` in the `Construction{}` block is unique and in 1..93.
2. `OnStoreSave` and `OnStoreLoad` write and read the same fields in the same order.
3. Every subclass writes/reads its fields after `super`, same order both ways.
4. A new persisted field bumps the mod's own version (written first) and adds a branch on it for old saves, not a branch on the game's `version`.
5. Crash-recovery walk: kill the server between each I/O hop of save/load, does the next boot recover the base or lose parts? (walk it step by step.)
6. The failsafe relock path (`SetPartFromSyncData`, `basebuildingbase.c:303`) still runs for corrupted sync/storage data.
7. In-game gate: build parts, restart the server, confirm every part and the base survive (not just an offline audit: lost-base bugs that only surface on a real restart).

## 7. Out of scope for this pass

`TerritoryFlag: BaseBuildingBase` is declared at `P:\DZ\gear\camping\config.cpp:12470`. Its saved refresher fields are covered in the persistence pack (`_shared/persistence/base-building.md`, section Territory flag); the radius and decay mechanics were not traced here. The `show_on_init` config field was read by the 1.29 `UpdateConstructionParts` with no observed effect, and no script on `P:\` reads it.

## 8. DayZ 1.30: Rebuilding is a second stream (not the 93 part cap)

(until 1.29: the three-int / 93-part model was the only construction persistence). (since 1.30: it still is, **for `BaseBuildingBase` only**.)

Verified unchanged on `BaseBuildingBase`:

```c
// P:\scripts\4_world\entities\itembase\basebuildingbase.c:420-430
	override void OnStoreSave( ParamsWriteContext ctx )
	{   
		super.OnStoreSave( ctx );
		
		//sync parts 01
		ctx.Write( m_SyncParts01 );
		ctx.Write( m_SyncParts02 );
		ctx.Write( m_SyncParts03 );
		
		ctx.Write( m_HasBase );
	}
```

`RegisterPartForSync` still packs 1 bit per `id` into `m_SyncParts01/02/03` with the same 1..31 / 32..62 / 63..93 ranges (`basebuildingbase.c:137-164`). `GetDamageSystemVersionChange()` is still `111` (`:1133-1136`).

`Rebuilding` (component on `BuildingBase`, created by `CreateConstructionComponent` at `P:\scripts\4_world\entities\game\super\building.c:23-27`) is a **different** save:

- version const `REBUILDING_STORAGE_VERSION = 1` (`P:\scripts\4_world\classes\rebuilding\rebuilding.c:3`)
- ten ints `m_SyncParts1`..`m_SyncParts10` (`rebuilding.c:7-16`), netsync-registered on `BuildingBase` (`building.c:35-44`)
- `HandleStoreSave` calls `SerializeConstructionData`: the version, then the ten ints (`rebuilding.c:473-514`)
- 2 bits reserved per part (`ConstructionPart.BITWISE_SYNCINFO_SIZE_BASE = 2` at `P:\scripts\4_world\classes\basebuilding\constructionpart.c:6`)
- capacity (derived): `BIT_INT_SIZE = 32` (`P:\scripts\3_game\tools\bitarray.c:4`) × 10 / 2 = **160 part ids**
- bit 0 = built (`constructionpart.c:111-117`); `ConstructionPartRebuildReversibleBase` stores its reversed flag in bit 1 (`:1065-1072`)

Do **not** put Rebuilding parts on a `BaseBuildingBase` entity or write the ten-int blob from a Fence/Watchtower subclass. Fence extra fields still go **after** `super.OnStoreSave` (`fence.c:246-254` in 1.30).

`CombinationLock` on a Fence attachment now writes a third int `m_CombinationInside` and reads it at vanilla stream **version >= 143** (`P:\scripts\4_world\entities\itembase\combinationlock.c:128-136,169-177`). A modded `OnStoreLoad` that always reads the 1.29 two-int layout after `super` will desync every later field. The order of the vanilla stream changes is in `dayz-1-30-persistence.md`; the Fence attachment path is in `base-building-fence-gate.md`.

Extra checks for 1.30:

8. Confirm you are editing `BaseBuildingBase` (3 ints, 1 bit, id 1..93) or `Rebuilding` (10 ints, 2 bits), never both on one class.
9. If the entity attaches `CombinationLock`, `OnStoreLoad` handles `version >= 143`.
10. `DigitalCodeLock` / `CodeLockComponent` persist `m_LockPIN`, `m_IsLocked`, `m_DoorIndex` (`P:\scripts\4_world\classes\codelockcomponent.c:257-262`).
