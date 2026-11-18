# Fence gate: the worked example

The vanilla Fence as a template for a stateful part on top of the base building system: gate state, barbed wire damage, locks and the saved gate fields. Open this before adding a gate, a lock or any extra saved state to your own buildable object.

Line numbers are from the vanilla scripts and configs on `P:\` (game storage version 144). A citation marked `1.29` points at the 1.29 scripts, which are not on `P:\`; those lines were not checked there and are kept as a map for older mods.

`Fence: BaseBuildingBase` (`P:\scripts\4_world\entities\itembase\basebuildingbase\fence.c:1`, 947 lines on `P:\`) is the richest concrete entity: it adds a gate state machine, an open/close animation, a combo lock, barbed-wire area damage, and a persisted gate field. Use it as the template when adding any stateful sub-behaviour on top of the base part system.

## 1. Gate state

The gate has its own state field `m_GateState` plus `m_IsOpened`, separate from the part bitmask. A part declares itself a gate with `is_gate=1` in the `Construction{}` block (read once per part type into `m_IsGate`, `P:\scripts\4_world\classes\basebuilding\typeconstructiondata\constructionparttyped.c:85`; on 1.29 in `UpdateConstructionParts`, 1.29 `construction.c:256-264`). The gate's open/close animation and combo lock are driven off `m_IsOpened` / the combolock, and the barbed-wire area damage is rotated with the gate.

The open/close actions are `P:\scripts\4_world\classes\useractionscomponent\actions\interact\actionopenfence.c` and `P:\scripts\4_world\classes\useractionscomponent\actions\interact\actionclosefence.c`. Opening/closing plays the gate animation and toggles `m_IsOpened`.

## 2. Barbed-wire area damage

`CreateAreaDamage` (`P:\scripts\4_world\entities\itembase\basebuildingbase.c:981-1026`) builds an `AreaDamageLoopedDeferred_NoVehicle` from the `<slot>_min` / `<slot>_max` memory points, ammo `"BarbedWireHit"`, hitting Torso / hands / legs / feet. Fence rotates that area damage with the gate (`fence.c:604-612`) so the damage volume follows the gate leaf as it swings.

Barbed wire is a `mountables[]` attachment (proxy physics toggled, see `base-building-config.md §2`); vanilla has no handler that unmounts the wire when its own damage zone is ruined. What vanilla does is drop the wire when the wall part it hangs on goes: `Fence.OnPartDestroyedServer` drops `Wall_Barbedwire_1` when `wall_base_down` is destroyed and `Wall_Barbedwire_2` when `wall_base_up` is destroyed (`P:\scripts\4_world\entities\itembase\basebuildingbase\fence.c:391-403`), and `GateAttachmentsSanityCheck` drops either wire whose wall base is not built (`fence.c:799-814`).

## 3. Gate persistence and the version bump

The gate state is persisted after the base three sync ints, following the strict `OnStoreSave`/`OnStoreLoad` ordering invariant (this is the canonical example of the subclass-after-super rule in `base-building-save-checklist.md`):

- `Fence.OnStoreSave` (`fence.c:246-254`): calls `super.OnStoreSave` first (which writes `m_SyncParts01/02/03` then `m_HasBase`), then writes `m_GateState`, `m_IsOpened`.
- `Fence.OnStoreLoad` (`fence.c:256-289`): calls `super.OnStoreLoad` first, then handles a legacy branch: for `version < 110` it reads and discards a bool, then reads the gate state + opened for current versions.

**Version note:** Fence gate persistence was bumped at **v110**. The base damage-system version is `GetDamageSystemVersionChange()` returning `111` (`basebuildingbase.c:1133-1136`). The Fence branch tests the game's storage version, which only the game can raise; a mod cannot reuse that pattern. When you add a persisted field to a subclass, write your mod's own version int first (after `super`) and branch on it, reading the old layout for old saves and the new layout for new ones, so existing bases don't corrupt on the first load after the update. Never migrate by the game's version (`skills/_shared/persistence/versioning-and-migration.md`). Getting this wrong loses every fence on the server, so treat it as data-critical and run the data audit (`base-building-save-checklist.md`).

## 4. Repair

`Fence.CanBeRepairedToPristine()` returns true (`fence.c:466-469`). Repair scales the material requirement by `REPAIR_MATERIAL_PERCENTAGE=0.15` (`P:\scripts\4_world\classes\constructionbase.c:34`, used at `constructionbase.c:1105` and `:1167`; 1.29 `construction.c:13,640-644`), floor min 1. The repair action itself is the generic `ActionRepairPart` / kit path (not in `fence.c`).

## 5. What to copy when authoring your own stateful entity

1. Add the state field(s) and register them for netsync in the ctor, alongside the base `m_SyncParts*`.
2. Persist them in `OnStoreSave`/`OnStoreLoad` after `super`, in the exact same order both ways.
3. Write your mod's own version int first, bump it when the layout changes, and branch on it to read old saves; never branch on the game's `version`.
4. If the behaviour has a physical volume (area damage, a moving leaf), rotate/relocate it in the same handler that mutates the state (`fence.c:604-612` pattern).
5. Gate the whole thing behind server authority, the state mutation runs server-side and syncs to clients.

## 6. DayZ 1.30: `DigitalCodeLock` and combination lock unlock

(until 1.29: Fence lock attachment was `CombinationLock` on `Att_CombinationLock` only; finishing the dial unlocked/detached the lock). (since 1.30: Fence also declares `DigitalCodeLock` on `Att_CodeLock`.)

```c
// P:\scripts\4_world\entities\itembase\basebuildingbase\fence.c:19-26
	typename ATTACHMENT_COMBINATION_LOCK	= CombinationLock;
	typename ATTACHMENT_CODE_LOCK			= DigitalCodeLock;
	
	const string ATTACHMENT_SLOT_CAMONET			= "Wall_Camonet";
	const string ATTACHMENT_SLOT_BARBEDWIRE_DOWN	= "Wall_Barbedwire_1";
	const string ATTACHMENT_SLOT_BARBEDWIRE_UP		= "Wall_Barbedwire_2";
	const string ATTACHMENT_SLOT_COMBINATION_LOCK 	= "Att_CombinationLock";
	const string ATTACHMENT_SLOT_CODE_LOCK 			= "Att_CodeLock";
```

`GetCodeLock()` finds the slot (`fence.c:161-165`). `GetCombinationLock()` is unchanged (`:155-159`). The two locks exclude each other: the combination lock slot is hidden and refuses an attachment while a code lock is mounted, and the code lock is refused while a combination lock is mounted (`fence.c:206-211`, `:438-446`).

`CombinationLock.SetActions` now includes `ActionCombinationLockUnlock` (`P:\scripts\4_world\entities\itembase\combinationlock.c:686`). Dialing the right combination is not enough. Persist: `OnStoreSave` writes `m_Combination`, `m_CombinationLocked`, then `m_CombinationInside`; `OnStoreLoad` reads the third int only when `version >= 143` (`combinationlock.c:128-136,169-177`). Fence gate fields themselves still follow the v110 branch (`fence.c:246-289`, the methods of §3).

Building-door lock slots on `BuildingBase` (`P:\scripts\4_world\entities\game\super\building.c:10-11`) are covered by `skills/_shared/animation/door-patterns.md`. This file only covers the Fence attachment.

`Fence.OnStoreSave` in 1.30:

```c
// P:\scripts\4_world\entities\itembase\basebuildingbase\fence.c:246-254
	override void OnStoreSave( ParamsWriteContext ctx )
	{   
		super.OnStoreSave( ctx );
		
		//write
		ctx.Write( m_GateState );
		ctx.Write( m_IsOpened );
		if (LogManager.IsBaseBuildingLogEnable()) bsbDebugPrint("[bsb] OnStoreSave - build=" + m_GateState + " opened=" + m_IsOpened);
	}
```
