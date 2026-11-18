# Oil pits and custom effect areas

How an oil pit works (its delay, its damage and what the client shows), how to place one, and how to write an effect area of your own on the 1.30 tick. The fire, smoke and light the client plays are in `dayz-particles/references/dayz-1-30-world-particles.md`, section "Oil pits"; how many particles a contaminated area asks for is in `dayz-particles/references/effect-area-particles.md`.

## The area and its delay

The area type is `EEffectAreaType.OIL_PIT = 8` (`P:\scripts\4_world\classes\contaminatedarea\effectarea.c:10` to `:16`).

`OilPitArea` (`P:\scripts\4_world\classes\contaminatedarea\oilpitarea.c:7`) sets `PRE_BURNING_DURATION_MIN` to 3 and `PRE_BURNING_DURATION_MAX` to 10 (`oilpitarea.c:10` and `:11`). `RandomizeIntervals` passes them to `Math.RandomInt` (`:54`), whose upper bound is exclusive (`P:\scripts\1_core\proto\enmath.c:26` to `:38`), so the delay is 3 to 9 whole seconds.

`InitZoneServer` creates the trigger and calls `StartBurning` after that delay (`oilpitarea.c:33` to `:48`), and `StartBurning` sets `EOilPitState.BURNING` on the trigger (`:57` to `:61`). Until then the pit does no damage. A freshly loaded pit looks harmless for up to 9 s, so wait for the burning state before you judge a test.

## Damage

From `P:\scripts\4_world\entities\scriptedentities\triggers\oilpittrigger.c:7`:

```c
	protected const float 	DAMAGE_TICK_RATE 	= 1.0;	// seconds between fire damage ticks
	protected const float 	DAMAGE_MULTIPLIER	= 20.0;	// damage per tick
```

From `oilpittrigger.c:63`:

```c
	override void OnStayServerEvent(TriggerInsider insider, float deltaTime)
	{
		if (!m_DealDamageFlag)
			return;

		EntityAI entity = EntityAI.Cast(insider.GetObject());
		if (entity)
			entity.ProcessDirectDamage(DamageType.CUSTOM, this, "", "HeatDamage", "0 0 0", DAMAGE_MULTIPLIER);
	}
```

`OnStayStartServerEvent` raises the damage flag only in the `BURNING` state and once per `DAMAGE_TICK_RATE` (`oilpittrigger.c:53` to `:61`). Anything inside takes 20 heat damage per second.

## What the client shows

`UpdateState` (`oilpittrigger.c:90` to `:126`) starts the fire, smoke and light. The sound `oil_pit_burn_SoundSet` plays only within 200 m and is checked again every 2 s (`:3` to `:5`; `UpdateSoundRange` and `UpdateSound`, `:201` to `:224`). The position is snapped to the ground with `SurfaceRoadY` (`:128` to `:134`).

`UpdateState` runs only on clients. `DeferredInit` skips it on a headless or dedicated server (`oilpittrigger.c:37`), and the other caller, `OnVariablesSynchronized` (`:82` to `:88`), is called only on clients (`P:\scripts\3_game\entities\entityai.c:3067`). The `PlayInWorld` calls in its ignition branch (`oilpittrigger.c:105` to `:116`) need no guard of their own.

## Placing one

The mission's `cfgeffectarea.json` lists effect areas as entries with `AreaName`, `Type`, `TriggerType` and `Data`. The vanilla Sakhal file uses the types `GeyserArea`, `HotSpringArea` and `VolcanicArea` (`P:\DZ\worlds\sakhal\ce\cfgeffectarea.json`). No vanilla file on `P:\` places an oil pit, so an entry with `Type` `OilPitArea` and `TriggerType` `OilPitTrigger` follows from the class names and is unverified until a test server shows the pit burning. The mission file belongs to dayz-server-admin.

## Writing your own area

Inherit `OilPitArea`, or copy its trigger and net sync pattern. Override `OnCEIterate(float currentTime, float elapsedTime)`, as `EffectArea` does (`P:\scripts\4_world\classes\contaminatedarea\effectarea.c:191`). `OnCEUpdate` is marked obsolete in 1.30 (`P:\scripts\3_game\entities\entityai.c:4924` and `:4925`), so an area that still overrides it may never iterate or resize its particles. `SpawnParticles` snaps each particle to `SurfaceRoadY` (`effectarea.c:412` to `:414`). The script class belongs to dayz-script-specialist.

## Checking it in game

On a local test server from `/dayz-launch-test`, wait 3 to 9 s after the pit loads, then expect 20 heat damage per second and the `OIL_FIRE1` or `OIL_FIRE2` particles.
