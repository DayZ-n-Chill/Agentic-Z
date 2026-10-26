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

## Territory flag

`TerritoryFlag` (`P:\scripts\4_world\entities\itembase\basebuildingbase\totem.c:1`) saves its refresher state after the base building data: `m_RefresherTimeRemaining`, `m_RefreshTimeCounter`, `m_FlagRefresherMaxDuration` and `m_RefresherActive` (`:101` to `:108`). It reads `m_RefresherActive` only from storage version 118 on (`:134`). The flag's refresher keeps nearby base parts from expiring, so a fault here shows up later as whole bases despawning.

## Locks

| Lock | Saved values | Source |
|---|---|---|
| `CombinationLock` | `m_Combination`, `m_CombinationLocked`, `m_CombinationInside`; the inside combination only from version 143, and an old field read and discarded before 105 | `P:\scripts\4_world\entities\itembase\combinationlock.c:128` to `:178` |
| `DigitalCodeLock` | Passes the stream to its `CodeLockComponent`, which writes `m_LockPIN`, `m_IsLocked`, `m_DoorIndex` | `P:\scripts\4_world\entities\itembase\codelock.c:484` and `:491`; `P:\scripts\4_world\classes\codelockcomponent.c:257` and `:264` |

The digital lock is a good model for a mod safe with a code: keep the lock logic in a helper object, and have the owner call the helper's save and load in its own place in the chain. A PIN of 4 to 6 digits is the vanilla rule (`codelockcomponent.c:23` and `:24`).

## Decay and damage settings

Base decay and base damage can be turned off by the server owner. `CfgGameplayHandler.GetDisableBaseDamage()` and `GetDisableBaseDecay()` read them (`P:\scripts\3_game\cfggameplayhandler.c:167` and `:172`), and `EntityAI` checks the decay switch through `ConstructionBasic.CanConstructionDecay()` before decaying (`P:\scripts\3_game\systems\construction_basic.c:37`; `P:\scripts\3_game\entities\entityai.c:3909`). A mod that adds its own base parts should respect both switches rather than add its own.
