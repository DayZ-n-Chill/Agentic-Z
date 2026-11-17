# Base building persistence

How built parts, territory flags and locks survive a restart, and which config changes break bases already on a server.

## Built parts are three bit masks

`BaseBuildingBase` (`P:\scripts\4_world\entities\itembase\basebuildingbase.c:2`) does not save its parts by name. It saves three ints, `m_SyncParts01`, `m_SyncParts02` and `m_SyncParts03`, plus `bool m_HasBase` (declared at `:8` to `:12`, written at `:420` to `:430`, read at `:432` to `:463`). Each built part sets one bit.

The bit comes from the part's config `id`:

| `id` range | Mask | Source |
|---|---|---|
| 1 to 31 | `m_SyncParts01` | `basebuildingbase.c:143` |
| 32 to 62 | `m_SyncParts02` | `basebuildingbase.c:150` |
| 63 to 93 | `m_SyncParts03` | `basebuildingbase.c:157` |

The same three ints are the network sync: they are registered as net sync variables in the constructor (`basebuildingbase.c:43` to `:45`), so there is no separate save record per part. An ID outside 1 to 93 matches none of the three branches of `RegisterPartForSync` (`basebuildingbase.c:137` to `:164`), so no bit is set for it.

So one object holds at most 93 parts, and IDs start at 1 (`basebuildingbase.c:139`, "part_id must starts from index = 1"). The ID is read from config as `id` (`P:\scripts\4_world\classes\basebuilding\typeconstructiondata\constructionparttyped.c:83`), and the vanilla comment says it "must be unique and withing sync limit" (`:9`, spelled that way).

## The config side

Parts live in a `Construction` class inside the object's `CfgVehicles` entry, grouped by main part. The vanilla fence is the model: `class Fence: BaseBuildingBase` (`P:\DZ\gear\camping\config.cpp:3252`), its `class Construction` (`:4529`), main part `class wall`, and the foundation part `class base` with `is_base=1` and `id=1` (`:4537`). The script walks main parts then parts in that order (`P:\scripts\4_world\classes\basebuilding\typeconstructiondata\constructionparttypedholder.c:19` to `:29`).

## Config changes that break existing bases

Because the save holds bits, not names, these changes alter what an existing base looks like after a restart:

| Change | Effect on saved bases |
|---|---|
| Change a part's `id` | The saved bit now belongs to another part, or to none. Parts appear or vanish. |
| Give two parts the same `id` | Both read the same bit. |
| Remove a part | Its bit is still set in old saves and points at nothing; reusing that `id` later builds the new part on old bases. |
| An `id` above 93 or below 1 | Never saved. The part is lost on every restart. |
| Add a part with a new, unused `id` | Safe. Old saves have the bit clear. |

Rule: treat every shipped part `id` as permanent. New parts get new IDs.

## Rebuilding after load

`AfterStoreLoad` calls `SetPartsAfterStoreLoad` (`basebuildingbase.c:466` and `:476`), which rebuilds parts from the masks with `SetPartsFromSyncData` (`:307`), sets the base state and syncs to clients. When the damage system is being reset after load, it waits and runs the same rebuild from `EEOnAfterLoad` half a second later (`:505`). A modded base building class that overrides `AfterStoreLoad` must call `super`, or parts are not rebuilt.

For each part, `SetPartFromSyncData` compares the saved bit with the part's built flag, adds or removes the part and its physics, and then locks or unlocks the attached materials again with `SetLockOnAttachedMaterials`, which vanilla comments as a "failsafe for corrupted sync/storage data" (`basebuildingbase.c:265` to `:304`). `BaseBuildingBase` returns `111` from `GetDamageSystemVersionChange` (`basebuildingbase.c:1133`), which is what triggers the delayed rebuild for saves older than that version (see `versioning-and-migration.md`, "Config changes that need a reset").

## A subclass saves after the masks: the Fence gate

`Fence` is the vanilla model for extra saved state on a buildable object. Its `OnStoreSave` calls `super` and then writes `m_GateState` and `m_IsOpened` (`P:\scripts\4_world\entities\itembase\basebuildingbase\fence.c:246` to `:254`). Its `OnStoreLoad` calls `super`, then, for a save older than version 110, reads one `bool` into `m_ToDiscard` and throws it away in place of `m_GateState` (which it sets to `GATE_STATE_NONE`), and otherwise reads `m_GateState`; in both cases it then reads `m_IsOpened` (`fence.c:256` to `:289`). `AfterStoreLoad` works the gate state out again from the built parts and opens the gate if it was saved open (`fence.c:291` to `:308`).

Copy that shape: your fields after `super`, the same order both ways, and a branch for every older layout.

## Since 1.30: the construction component

On 1.30 the construction logic lives in a component that `EntityAI` creates. That 1.30 moved it there is a comparison with 1.29, and the 1.29 scripts are not on `P:\`, so the move itself is not checked here; the facts in the table are checked against the current scripts. What a base building mod has to know:

| Fact | Source |
|---|---|
| `BaseBuildingBase` holds `protected ref ConstructionBasic m_Construction`; reach it with `GetConstruction()` (a cast to `Construction`) or `GetConstructionBasic()`, not through the field | `basebuildingbase.c:15`; `GetConstruction` at `basebuildingbase.c:883` |
| `CreateConstructionComponent` creates `new Construction(this)` for a `BaseBuildingBase` | `basebuildingbase.c:872` |
| `Construction` extends `ConstructionBase`, which holds the shared logic | `P:\scripts\4_world\classes\basebuilding\construction.c:2`; `P:\scripts\4_world\classes\constructionbase.c:30` |
| The part config is cached once per entity type in `ConstructionPartTypeData`, not read per instance | `InitPartTypeData` at `P:\scripts\4_world\classes\basebuilding\typeconstructiondata\constructionparttyped.c:45` |
| Vanilla actions call `BuildPartServerEx` and `DismantlePartServerEx`; `BuildPartServer` and `DismantlePartServer` are `[Obsolete]` wrappers, so an override of the old names no longer runs | `BuildPartServerEx` at `constructionbase.c:179`; `DismantlePartServerEx` at `constructionbase.c:190`; `BuildPartServer` at `constructionbase.c:1703` |
| Build collision is `IsCollidingEx(CollisionCheckData)`; `CreateCollisionTrigger` and its siblings are `[Obsolete("no replacement")]` | `IsCollidingEx` at `constructionbase.c:1481`; `CreateCollisionTrigger` at `constructionbase.c:1757` |

None of this changed the save: the three masks and `m_HasBase` are written exactly as before (the 1.29 scripts are not on `P:\`, so the comparison is not checked here).

## Rebuildable map buildings are a second, separate save

Since 1.30 a map building (`BuildingBase`) can carry a construction component too (the 1.29 scripts are not on `P:\`, so "since 1.30" is not checked here). It is a different class with a different save, and its numbers do not apply to player built objects.

| | `BaseBuildingBase` (fence, watchtower, your mod's wall) | `Rebuilding` on `BuildingBase` (map houses) |
|---|---|---|
| Component | `Construction` | `Rebuilding`, created in `CreateConstructionComponent` (`P:\scripts\4_world\entities\game\super\building.c:23` to `:27`) |
| Sync ints | 3: `m_SyncParts01` to `m_SyncParts03` | 10: `m_SyncParts1` to `m_SyncParts10` (`P:\scripts\4_world\classes\rebuilding\rebuilding.c:7` to `:16`), registered at `building.c:35` to `:44` |
| Bits per part | 1 | 2: `BITWISE_SYNCINFO_SIZE_BASE` (`P:\scripts\4_world\classes\basebuilding\constructionpart.c:6`) |
| Part ids | 1 to 93 | up to 160, derived: 10 ints of `BIT_INT_SIZE` 32 bits (`P:\scripts\3_game\tools\bitarray.c:4`) at 2 bits each |
| Written by | the class's own `OnStoreSave`, after `super` | `SerializeConstructionData`: `REBUILDING_STORAGE_VERSION`, then the ten ints (`rebuilding.c:501` to `:514`), through the `EntityAI` construction block at the start of the stream |
| Own version | none; gated on the game's storage version | `REBUILDING_STORAGE_VERSION = 1` (`rebuilding.c:3`) |

Do not write the ten int block from a `BaseBuildingBase` subclass, and do not apply the 93 part cap to a rebuildable building. On the `P:\` build only script classes for rebuildable houses were found (`Land_House_1M1` at `P:\scripts\4_world\entities\building\rebuildable\house_1m1.c:1`); their configs are not in the unpacked `P:\DZ` data, so the config side is not checked here. The keys such a building's `Construction` class reads are listed in `references/dayz-1-30-construction-rebuilding.md` of the `dayz-basebuilding` skill.

## Territory flag

`TerritoryFlag` (`P:\scripts\4_world\entities\itembase\basebuildingbase\totem.c:1`) saves its refresher state after the base building data: `m_RefresherTimeRemaining`, `m_RefreshTimeCounter`, `m_FlagRefresherMaxDuration` and `m_RefresherActive` (`:101` to `:108`). It reads `m_RefresherActive` only from storage version 118 on (`:134`). The flag's refresher keeps nearby base parts from expiring, so a fault here shows up later as whole bases despawning.

## Locks

| Lock | Saved values | Source |
|---|---|---|
| `CombinationLock` | `m_Combination`, `m_CombinationLocked`, `m_CombinationInside`; the inside combination only from version 143, and an old field read and discarded before 105 | `P:\scripts\4_world\entities\itembase\combinationlock.c:128` to `:178` |
| `DigitalCodeLock` | Passes the stream to its `CodeLockComponent`, which writes `m_LockPIN`, `m_IsLocked`, `m_DoorIndex` | `P:\scripts\4_world\entities\itembase\codelock.c:484` and `:491`; `P:\scripts\4_world\classes\codelockcomponent.c:257` and `:264` |

The digital lock is a good model for a mod safe with a code: keep the lock logic in a helper object, and have the owner call the helper's save and load in its own place in the chain. A PIN of 4 to 6 digits is the vanilla rule (`codelockcomponent.c:23` and `:24`).

On a fence the two locks sit in their own slots, `Att_CombinationLock` and `Att_CodeLock` (`ATTACHMENT_SLOT_CODE_LOCK` at `P:\scripts\4_world\entities\itembase\basebuildingbase\fence.c:26`; `GetCodeLock` at `fence.c:161`), and a fence accepts one only while the other is absent (`fence.c:438` to `:446`). `IsLocked` is true for a locked lock of either kind (`fence.c:127` to `:142`). `CanOpenFence` checks `IsLocked`, but `OpenFence` does not (`CanOpenFence` at `fence.c:472`; `OpenFence` at `fence.c:488`), so a script that opens a gate, for example a powered opener, calls `CanOpenFence` first or it opens locked gates.

A subclass of `CombinationLock` with its own `OnStoreLoad` must either call `super` or read the third value from version 143 on; reading the old two values shifts everything after them.

## Decay and damage settings

Base decay and base damage can be turned off by the server owner. `CfgGameplayHandler.GetDisableBaseDamage()` and `GetDisableBaseDecay()` read them (`P:\scripts\3_game\cfggameplayhandler.c:167` and `:172`), and `EntityAI` checks the decay switch through `ConstructionBasic.CanConstructionDecay()` before decaying (`P:\scripts\3_game\systems\construction_basic.c:37`; `P:\scripts\3_game\entities\entityai.c:3909`). A mod that adds its own base parts should respect both switches rather than add its own.

## Where the deep material is

The `dayz-basebuilding` skill holds the rest: every `Construction` config field with its reader (`references/config-contract.md`), the call chain from kit to saved base (`references/entity-lifecycle.md`), the Fence as a worked example (`references/fence-gate-case.md`), the hand-off checklist before a save change ships (`references/persistence-audit.md`) and the 1.30 changes with the vanilla code (`references/dayz-1-30-construction-rebuilding.md`).
