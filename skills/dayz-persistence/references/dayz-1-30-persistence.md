# DayZ 1.30: persistence changes

What 1.30 changed in the vanilla save streams, with the vanilla code copied in: the storage version, the construction data in front of the energy data, the player's thermal float, the combination lock's third value, the code lock, Rebuilding and the bunker file. Open this when porting a 1.29 mod that saves data, or when a 1.29 save misloads on 1.30.

Every code block was copied from the file named in its first line and compared with `P:\` (game storage version 144). A citation marked `1.29` points at the 1.29 scripts, which are not on `P:\` and were not checked there.

## What changed

| Surface | 1.29 | 1.30 | Effect on a 1.29 mod |
|---|---|---|---|
| `GAME_STORAGE_VERSION` | `142` at 1.29 `3_game\global\game.c:5` | `144` at `P:\scripts\3_game\global\game.c:5` | Hook `version` on a 1.30 save is 144. `g_Game.SaveVersion()` is at `:435` (1.29 `game.c:434`). |
| `EntityAI` prefix | energy-or-nothing, then `SaveVariables` | `GetConstructionBasic().HandleStoreSave` **before** energy; load of that block only if `version >= 143` | Mods that skip `super` or assume a fixed EntityAI prefix misalign on rebuilt houses. |
| `PlayerBase` MP stream | ends at `ArrowManagerPlayer.Save/Load` | appends `m_ThermalBiasHandler.OnStoreSave/OnStoreLoad` with **no** version gate | A 1.29 `player.bin` (`version` 142) loaded on 1.30 MP fails with `failed to load ThermalBiasHandler`. |
| `CombinationLock` | `m_Combination`, `m_CombinationLocked` | plus `m_CombinationInside`; load gated `version >= 143` | Subclass `OnStoreLoad` that does not call `super` after v143 desyncs later bytes. |
| `DigitalCodeLock` | class did not exist | `super` then `CodeLockComponent` PIN / locked / door index | New entity; old worlds have no such items. |
| `BaseBuildingBase` subclass stream | `m_SyncParts01/02/03` + `m_HasBase` | same order | No 1.30 break at the subclass suffix. |
| `Rebuilding` (map houses) | class did not exist | own 11-int payload via `EntityAI` construction handle | Not `BaseBuildingBase`. Do not copy its version check as a future-reject pattern. |
| `$mission:BunkerBroadcastPersistenceStorage.bin` | file did not exist | `FileSerializer` of two objects, no header, no `Read` check | Mission file, not the character/world bin. Not the recoverable JSON sidecar. |

## `GAME_STORAGE_VERSION` = 144

```
// P:\scripts\3_game\global\game.c:5
static int GAME_STORAGE_VERSION = 144;
```

`CGame` still publishes it through `StorageVersion(GAME_STORAGE_VERSION)` at `game.c:50` and `proto native int SaveVersion()` at `:435`. On 1.29 the same native was one line earlier (1.29 `game.c:434`).

Until 1.29 `GAME_STORAGE_VERSION` was 142. Since 1.30 it is 144. CombinationLock and EntityAI construction load branch on `version >= 143`, so a 1.29 record whose stored version is 142 skips those new fields. `ThermalBiasHandler` does not.

## EntityAI prefix (construction then energy)

```
// P:\scripts\3_game\entities\entityai.c:2910
	void OnStoreSave (ParamsWriteContext ctx)
	{
		ConstructionBasic constructionComponent = GetConstructionBasic();
		if (constructionComponent)
			constructionComponent.HandleStoreSave(ctx);
		
		// Saving of energy related states
		if ( m_EM )
		{		
			// Save energy amount
			ctx.Write( m_EM.GetEnergy() );
			
			// Save passive/active state
			ctx.Write( m_EM.IsPassive() );
			
			// Save ON/OFF state
			ctx.Write( m_EM.IsSwitchedOn() );
			
			// Save plugged/unplugged state
			ctx.Write( m_EM.IsPlugged() );
```

(until 1.29: `OnStoreSave` began at the `m_EM` block; 1.29 `3_game\entities\entityai.c:2930-2933`. No construction handle.) Since 1.30 `HandleStoreSave` is a no-op on `ConstructionBasic` (`P:\scripts\3_game\systems\construction_basic.c:29-35`, `HandleStorageEvents` returns `false`). Only `Rebuilding` overrides it and writes. Load:

```
// P:\scripts\3_game\entities\entityai.c:2978
	bool OnStoreLoad (ParamsReadContext ctx, int version)
	{
		ConstructionBasic constructionComponent = GetConstructionBasic();
		if (version >= 143 && constructionComponent)
		{
			constructionComponent.HandleStoreLoad(ctx,version);
		}
		
		// Restoring of energy related states
		if ( m_EM )
		{
```

Energy field count is unchanged versus 1.29: eight typed writes when `m_EM` exists (`GetEnergy`, `IsPassive`, `IsSwitchedOn`, `IsPlugged`, four persistent-ID ints) then `SaveVariables` at `:2951`.

`LoadVariables` remains behind `version >= 140` (`P:\scripts\3_game\entities\entityai.c:3053-3058`).

## `PlayerBase` + `ThermalBiasHandler`

The persistence hooks are `OnStoreSave` and `OnStoreLoad` at `P:\scripts\4_world\entities\manbase\playerbase.c:7353` and `:7408`.

On server MP save, after `ArrowManagerPlayer.Save`:

```
// P:\scripts\4_world\entities\manbase\playerbase.c:7392
			ArrowManagerPlayer arrowManager = ArrowManagerPlayer.Cast(GetArrowManager());
			arrowManager.Save(ctx);
			
			m_ThermalBiasHandler.OnStoreSave(ctx); //save thermal bias handler
		}
	}
```

Load is **not** version-gated:

```
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

Handler payload is one float:

```
// P:\scripts\4_world\classes\thermalbiashandler.c:67
    void OnStoreSave(ParamsWriteContext ctx)
    {
        ctx.Write(m_TemporaryResistanceTime);
    }

    bool OnStoreLoad(ParamsReadContext ctx, int version)
    {
        if (!ctx.Read(m_TemporaryResistanceTime))
            return false;

        return true;
    }
```

Design note: A 1.29 player record has no following float. 1.30 always reads it on server MP. That is a failed load, not a silent default. Contrast `CombinationLock`, which **does** gate the new int. Mods that override `PlayerBase.OnStoreSave/OnStoreLoad` must still call `super` in the same relative position; inserting fields before `super` or after a copied 1.29 suffix without the thermal float desyncs the stream. 1.29 save ended at `arrowManager.Save` (1.29 `4_world\entities\manbase\playerbase.c:7073-7075`).

## `CombinationLock` stream v143

(until 1.29: save wrote `m_Combination` then `m_CombinationLocked`; load had the `version < 105` attached-bool remnant. 1.29 `4_world\entities\itembase\combinationlock.c:90-129`.) (since 1.30: save always writes a third int; load reads it only at `version >= 143`.)

```
// P:\scripts\4_world\entities\itembase\combinationlock.c:128
	override void OnStoreSave( ParamsWriteContext ctx )
	{   
		super.OnStoreSave(ctx);
		
		//write data
		ctx.Write( m_Combination );
		ctx.Write( m_CombinationLocked );
		ctx.Write( m_CombinationInside );
	}
```

```
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

		return true;
	}
```

A 1.29 lock (`version` 142) still loads: the third int is skipped. A 1.30 lock (`version` 144) writes three ints. A mod that calls `super.OnStoreSave` but implements its own `OnStoreLoad` without the `>= 143` branch reads `m_CombinationInside` as the next subclass field.

Vanilla still assigns defaults (`m_Combination = 0`) **before** `return false` on a failed read (`:145-148`). That breaks hard stop 5 of this skill (no partial state after a failed read); do not copy it. Stage, then commit.

## `DigitalCodeLock` / `CodeLockComponent`

New 1.30 item. Entity stream is `super` then the component:

```
// P:\scripts\4_world\entities\itembase\codelock.c:484
	override void OnStoreSave(ParamsWriteContext ctx)
	{
		super.OnStoreSave(ctx);
		
		m_CodeLockComponent.OnStoreSave(ctx);
	}
	
	override bool OnStoreLoad(ParamsReadContext ctx, int version)
	{
		if (!super.OnStoreLoad(ctx, version))
			return false;
		
		if (!m_CodeLockComponent.OnStoreLoad(ctx, version))
			return false;
```

```
// P:\scripts\4_world\classes\codelockcomponent.c:257
	void OnStoreSave(ParamsWriteContext ctx)
	{
		ctx.Write(m_LockPIN);
		ctx.Write(m_IsLocked);
		ctx.Write(m_DoorIndex);
	}
	
	bool OnStoreLoad(ParamsReadContext ctx, int version)
	{
		if (!ctx.Read(m_LockPIN))
		{
			m_LockPIN = "";
			m_HasPIN = false;
			return false;
		}
		
		if (!ctx.Read(m_IsLocked))
			return false;

		if (!ctx.Read(m_DoorIndex))
			return false;
```

No `version` gate: the class did not exist in 1.29. Failed PIN read mutates `m_LockPIN` / `m_HasPIN` before returning `false`, the same hard stop 5 warning.

## `BaseBuildingBase` suffix unchanged; `Rebuilding` is a different stream

```
// P:\scripts\4_world\entities\itembase\basebuildingbase.c:420
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

`ConstructionBasic.HandleStorageEvents` returns `false`, so a traditional player-built fence still has an empty construction handle in `super`. The 93-part / three-int packing lives here, not on `Rebuilding`.

`Rebuilding` (map-house reconstruction) writes through `EntityAI`'s handle:

```
// P:\scripts\4_world\classes\rebuilding\rebuilding.c:1
class Rebuilding : ConstructionBase
{
	static int REBUILDING_STORAGE_VERSION = 1;
```

```
// P:\scripts\4_world\classes\rebuilding\rebuilding.c:501
	protected void SerializeConstructionData(ParamsWriteContext ctx)
	{
		ctx.Write(REBUILDING_STORAGE_VERSION);
		ctx.Write(m_SyncParts1);
		ctx.Write(m_SyncParts2);
		ctx.Write(m_SyncParts3);
		ctx.Write(m_SyncParts4);
		ctx.Write(m_SyncParts5);
		ctx.Write(m_SyncParts6);
		ctx.Write(m_SyncParts7);
		ctx.Write(m_SyncParts8);
		ctx.Write(m_SyncParts9);
		ctx.Write(m_SyncParts10);
	}
```

`DeserializeConstructionData` rejects `m_LastStorageVersion < REBUILDING_STORAGE_VERSION` and **accepts** a stored version greater than current (`P:\scripts\4_world\classes\rebuilding\rebuilding.c:518-524`). That is the opposite of this skill's `future-version` cell. Design note: Do not copy it. A future extra int after the ten sync fields would be consumed as `EntityAI` energy and desync the rest of the house.

## `$mission:BunkerBroadcastPersistenceStorage.bin`

Not an entity stream. Independent mission file:

```
// P:\scripts\4_world\classes\bunkerbroadcasthandler.c:16
class BunkerBroadcastPersistenceStorage : Managed
{
	private const string STORAGE_PATH = "$mission:BunkerBroadcastPersistenceStorage.bin";

	ref BunkerBroadcastSchedulerPersistenceData m_SchedulerData;
	ref BunkerBroadcastHandlerPersistenceData m_HandlerData;
```

```
// P:\scripts\4_world\classes\bunkerbroadcasthandler.c:56
	bool Load()
	{
		FileSerializer file = new FileSerializer();
		if (file.Open(STORAGE_PATH, FileMode.READ))
		{
			file.Read(m_HandlerData);
			file.Read(m_SchedulerData);
			file.Close();
			
			return true;
		}
		
		return false;
	}
```

```
// P:\scripts\4_world\classes\bunkerbroadcasthandler.c:73
	void Save()
	{
		FileSerializer file = new FileSerializer();
		if (file.Open(STORAGE_PATH, FileMode.WRITE))
		{
			file.Write(m_HandlerData);
			file.Write(m_SchedulerData);
			file.Close();			
		}
	}
```

Payload classes (`:5-14`): `m_LastReportHour` / `m_LastReportMinute` ints, and `TIntStringMap m_LastActiveBunkers` (bunker id → lock code). No version header. `FileSerializer.Read` returns `bool` (`P:\scripts\1_core\proto\serializer.c:58`) and vanilla **ignores** it, then returns `true` after a successful `Open`. `DeleteFile` / `CopyFile` only work on `$profile:` and `$saves:` (`P:\scripts\1_core\proto\ensystem.c:528-532`), so the recoverable sidecar replace in `sidecar-files.md` cannot be used on `$mission:` with those primitives.

Design note: Treat this as a vanilla mission-file exception, not a template. A mod that persists bunker-like state should still own a version header, check every `Read`, and pick a location (`$profile:` / `$saves:`) where backup + delete + copy is possible.

## What breaks (1.29 mod → 1.30)

1. `PlayerBase` override that copies the 1.29 MP suffix and omits `ThermalBiasHandler`, or that never calls `super`. Symptom: `---- failed to load ThermalBiasHandler, read fail  ----`.
2. `CombinationLock` subclass `OnStoreLoad` that does not call `super` or that assumes two ints after `super`. Symptom: later fields (or a following attachment) read as `m_CombinationInside`.
3. Any `EntityAI` subclass on a `Rebuilding` house that skips `super` or seeks a fixed offset past "energy". 1.30 writes construction data first when the component is present.
4. Claiming a `$mission:` `FileSerializer` overwrite is atomic, or that `BunkerBroadcastPersistenceStorage` follows `JsonFileLoader` + backup.

`JsonFileLoader<T>.LoadFile` / deprecated `JsonLoadFile` are at the same lines as on 1.29 (`P:\scripts\3_game\tools\jsonfileloader.c:7-40`, `:99-131`). `DeleteFile` / `CopyFile` still at `ensystem.c:528,531`. No 1.30 change in CF ModStorage was checked.

## Migration checklist

- [ ] Call `super.OnStoreSave` / `super.OnStoreLoad` on `PlayerBase`, `CombinationLock`, `DigitalCodeLock`, and any `EntityAI` with a construction component; do not re-implement the 1.29 suffix by copy.
- [ ] `CombinationLock.OnStoreLoad`: `if (version >= 143) ctx.Read(m_CombinationInside)` (or rely on `super`).
- [ ] Do not version-gate `ThermalBiasHandler` yourself on a `PlayerBase` subclass unless you also stop writing it; vanilla always writes it on 1.30 MP save.
- [ ] Classify a 1.29 `player.bin` on 1.30 as `truncated` / failed load for thermal, not as `legacy-no-header` success. Vanilla does not migrate it.
- [ ] Keep `BaseBuildingBase` 93-part packing; do not apply `Rebuilding`'s ten ints / `REBUILDING_STORAGE_VERSION` to player-built fences.
- [ ] If persisting mission-wide bunker state, do not clone vanilla's unchecked `FileSerializer` overwrite. Use the sidecar contract on `$profile:` / `$saves:`.
- [ ] Check every `path:line` again on `P:\` after a game update.
