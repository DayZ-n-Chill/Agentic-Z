# Fence gate

How the vanilla Fence adds a gate, barbed wire damage, two kinds of lock and extra saved fields on top of the base building parts. Copy its shape when your own buildable object needs state beyond which parts are built.

`Fence: BaseBuildingBase` is declared at `P:\scripts\4_world\entities\itembase\basebuildingbase\fence.c:1`. Its gate state is kept in its own fields, separate from the part bit masks.

## Gate state

A part declares itself a gate with `is_gate=1` in the `Construction` block, read once per part type into `m_IsGate` (`P:\scripts\4_world\classes\basebuilding\typeconstructiondata\constructionparttyped.c:85`). The Fence then tracks `m_GateState` and `m_IsOpened`. The open and close animation and the lock are driven from `m_IsOpened`.

The actions are `ActionOpenFence` (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\actionopenfence.c`) and `ActionCloseFence` (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\actionclosefence.c`). Each plays the gate animation and flips `m_IsOpened`.

`CanOpenFence` requires hinges, a closed gate and no lock (`fence.c:486` to `:492`), but `OpenFence` checks none of that and opens (`fence.c:502` to `:542`). A script that opens a gate, such as a powered opener, calls `CanOpenFence` first or it opens locked gates.

## Barbed wire damage

`CreateAreaDamage` (`P:\scripts\4_world\entities\itembase\basebuildingbase.c:980` to `:1025`) builds an `AreaDamageLoopedDeferred_NoVehicle` between the `<slot>_min` and `<slot>_max` memory points, with ammo `BarbedWireHit`, hitting the torso, hands, legs and feet. The Fence overrides it to turn the damage box by 100 degrees while the gate is open (`fence.c:618` to `:626`), and `UpdateBarbedWireAreaDamagePos` moves the box when the gate finishes opening or closing (`fence.c:591` to `:615`).

Barbed wire is a `mountables[]` attachment (see `base-building-config.md`, section "Slots on the entity class"). When the wire's own damage zone is ruined, `Construction.OnHealthLevelChanged` (`P:\scripts\4_world\classes\basebuilding\construction.c:116` to `:133`) only unmounts the wire: `BarbedWire.SetMountedState(false)` unlocks its slot and makes it takeable (`barbedwire.c:66` to `:77`), so it stays attached until a player takes it. Vanilla drops the wire when the wall part under it goes: `Fence.OnPartDestroyedServer` drops `Wall_Barbedwire_1` and any lock when `wall_base_down` is destroyed, and `Wall_Barbedwire_2`, the camo net and any lock when `wall_base_up` is destroyed (`fence.c:405` to `:417`); a gate destroyed by a connected part drops all of them and closes the gate (`:392` to `:404`). `GateAttachmentsSanityCheck` drops either wire whose wall base is not built (`fence.c:813` to `:828`).

## Locks

| Constant | Value | Source |
|---|---|---|
| `ATTACHMENT_COMBINATION_LOCK` | `CombinationLock` | `fence.c:19` |
| `ATTACHMENT_CODE_LOCK` | `DigitalCodeLock` | `fence.c:20` |
| `ATTACHMENT_SLOT_CAMONET` | `Wall_Camonet` | `fence.c:22` |
| `ATTACHMENT_SLOT_BARBEDWIRE_DOWN`, `_UP` | `Wall_Barbedwire_1`, `Wall_Barbedwire_2` | `fence.c:23` and `:24` |
| `ATTACHMENT_SLOT_COMBINATION_LOCK` | `Att_CombinationLock` | `fence.c:25` |
| `ATTACHMENT_SLOT_CODE_LOCK` | `Att_CodeLock` | `fence.c:26` |

`GetCombinationLock()` (`fence.c:155` to `:159`) and `GetCodeLock()` (`fence.c:161` to `:165`) find the lock in its slot. The two exclude each other: the combination lock slot is hidden while the gate is not fully built or a code lock is mounted (`fence.c:206` to `:212`), and either lock attaches only to a fully built gate that is closed and holds no lock of the other kind (`fence.c:452` to `:460`). `IsLocked()` is true for a locked lock of either kind (`fence.c:127` to `:142`).

A combination lock no longer opens just because the right numbers are dialled; it has its own `ActionCombinationLockUnlock` (`P:\scripts\4_world\entities\itembase\combinationlock.c:686`). It saves `m_Combination`, `m_CombinationLocked`, then `m_CombinationInside`, and reads the third value only from storage version 143 (`combinationlock.c:128` to `:136` and `:169` to `:177`).

A `DigitalCodeLock` owns a `CodeLockComponent` (`P:\scripts\4_world\entities\itembase\codelock.c:1`, `:9`, `:30`), which saves `m_LockPIN`, `m_IsLocked` and `m_DoorIndex` in that order (`P:\scripts\4_world\classes\codelockcomponent.c:257` to `:262`). A PIN has 4 to 6 digits (`codelockcomponent.c:23` and `:24`).

Lock slots on map building doors are a different system, in `_shared/animation/building-door-locks.md`.

## Saved gate fields

The gate fields go after the base building data, the vanilla model of a subclass saving after `super`:

```c
// P:\scripts\4_world\entities\itembase\basebuildingbase\fence.c:255
override void OnStoreSave( ParamsWriteContext ctx )
{
    super.OnStoreSave( ctx );

    ctx.Write( m_GateState );
    ctx.Write( m_IsOpened );
}
```

`super` writes `m_SyncParts01`, `m_SyncParts02`, `m_SyncParts03` and `m_HasBase`. `OnStoreLoad` (`fence.c:265` to `:298`) calls `super`, then, for a save older than storage version 110, reads one `bool` and throws it away in place of the gate state; otherwise it reads `m_GateState`. Both branches then read `m_IsOpened`.

That branch tests the game's storage version, which only the game can raise. A mod cannot copy it. When you add a saved field to your own subclass, write your mod's own version first, after `super`, and branch on it so old saves load with the old layout (`versioning-and-migration.md`). The base building damage system version is separate: `GetDamageSystemVersionChange()` returns `111` (`basebuildingbase.c:1132` to `:1135`). A mistake in the gate fields loses every fence on the server, so run the checklist in `base-building-save-checklist.md`.

## Repair

`Fence.CanBeRepairedToPristine()` returns true (`fence.c:480` to `:483`). Repair needs 15 percent of the build materials, `REPAIR_MATERIAL_PERCENTAGE = 0.15` (`P:\scripts\4_world\classes\constructionbase.c:34`, used at `:1210` and `:1272`), rounded down and at least 1 (`Math.Max(Math.Floor(quantity), 1)`, `:1211` and `:1273`). A material with `skipOnRepair=1` is not taken on repair (`:1254`). The repair itself is the generic `ActionRepairPart`, not code in `fence.c`.

## Copying the pattern

1. Add the state fields and register them for net sync in the constructor, beside the base `m_SyncParts*`.
2. Save and load them after `super`, in the same order both ways.
3. Write your mod's own version first, raise it when the layout changes, and branch on it for old saves. Never branch on the game's `version`.
4. If the state has a physical volume, such as area damage or a moving leaf, move it in the same handler that changes the state, as the Fence does at `fence.c:618` to `:626`.
5. Change the state on the server only and let net sync carry it to clients.
6. If a lock or other attachment can leave its slot without the detach action, release the slot lock in `EEItemDetached` and repair a slot left locked with no item in `AfterStoreLoad`, as the Fence does for the combination lock (`fence.c:246` to `:253` and `:304` to `:307`).
