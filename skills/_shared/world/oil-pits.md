# Oil pits and custom effect areas (DayZ 1.30)

How the 1.30 oil pit works (its delay, its damage and what the client shows), how to place one, and how to write an effect area of your own on the 1.30 tick. Checked on `P:\` (DayZ 1.30). The fire, smoke and light the client plays are listed in `dayz-particles/references/dayz-1-30-particles.md` ("Oil pits"); how many particles a contaminated area asks for is in `dayz-particles/references/effect-area-particles.md`.

## The area

The area type is `EEffectAreaType.OIL_PIT = 8` (`P:\scripts\4_world\classes\contaminatedarea\effectarea.c:10` to `:16`).

`OilPitArea` (`P:\scripts\4_world\classes\contaminatedarea\oilpitarea.c:7`): `PRE_BURNING_DURATION_MIN` 3 and `PRE_BURNING_DURATION_MAX` 10 (`oilpitarea.c:10` to `:11`). `RandomizeIntervals` passes them to `Math.RandomInt` (`oilpitarea.c:54`), whose upper bound is exclusive (`P:\scripts\1_core\proto\enmath.c:26` to `:38`), so the delay is 3 to 9 whole seconds. `InitZoneServer` creates the trigger and calls `StartBurning` after that random delay (`oilpitarea.c:33` to `:48`). `StartBurning` sets `EOilPitState.BURNING` on the trigger (`oilpitarea.c:57` to `:61`). Until then the pit does no damage, so a freshly loaded pit looks inert for up to 9 s: wait for the state before judging a test.

## Damage

```c
// P:\scripts\4_world\entities\scriptedentities\triggers\oilpittrigger.c:7
	protected const float 	DAMAGE_TICK_RATE 	= 1.0;	// seconds between fire damage ticks
	protected const float 	DAMAGE_MULTIPLIER	= 20.0;	// damage per tick
```

```c
// P:\scripts\4_world\entities\scriptedentities\triggers\oilpittrigger.c:63
	override void OnStayServerEvent(TriggerInsider insider, float deltaTime)
	{
		if (!m_DealDamageFlag)
			return;

		EntityAI entity = EntityAI.Cast(insider.GetObject());
		if (entity)
			entity.ProcessDirectDamage(DamageType.CUSTOM, this, "", "HeatDamage", "0 0 0", DAMAGE_MULTIPLIER);
	}
```

`OnStayStartServerEvent` raises the damage flag only in the `BURNING` state and once per `DAMAGE_TICK_RATE` (`oilpittrigger.c:53` to `:61`).

## The client side

`UpdateState` (`oilpittrigger.c:90` to `:126`) starts the fire, smoke and light. The sound `oil_pit_burn_SoundSet` plays only within 200 m and is re-checked every 2 s (`oilpittrigger.c:3` to `:5`; `UpdateSoundRange` and `UpdateSound`, `oilpittrigger.c:201` to `:224`). The position is snapped to the ground with `SurfaceRoadY` (`oilpittrigger.c:128` to `:134`).

`UpdateState` runs only on clients: `DeferredInit` skips it on a headless or dedicated server (`oilpittrigger.c:37`), and the other caller, `OnVariablesSynchronized` (`oilpittrigger.c:82` to `:88`), is called only on clients (`P:\scripts\3_game\entities\entityai.c:3067`). So the `PlayInWorld` calls in its ignition branch (`oilpittrigger.c:105` to `:116`) need no guard of their own.

## Placing one

Effect areas are listed in the mission's `cfgeffectarea.json` as entries with `AreaName`, `Type`, `TriggerType` and `Data`; the vanilla Sakhal file uses the types `GeyserArea`, `HotSpringArea` and `VolcanicArea` (file `P:\DZ\worlds\sakhal\ce\cfgeffectarea.json`). No vanilla file on `P:\` places an oil pit, so an entry with `Type` `OilPitArea` and `TriggerType` `OilPitTrigger` is a design inference from the class names, not a copied example. The mission file belongs to dayz-server-admin.

## Writing your own area

For a custom area, inherit `OilPitArea` or copy its trigger and net sync pattern. Override `OnCEIterate(float currentTime, float elapsedTime)`, as `EffectArea` does (`P:\scripts\4_world\classes\contaminatedarea\effectarea.c:191`); `OnCEUpdate` is marked obsolete in 1.30 (`P:\scripts\3_game\entities\entityai.c:4924` to `:4925`), so an area that still overrides it may never iterate or resize its particles. `SpawnParticles` snaps each particle to `SurfaceRoadY` (`effectarea.c:412` to `:414`). The script class belongs to dayz-script-specialist.

## Testing in game

On a local test server from `/dayz-launch-test`, wait 3 to 9 s, then expect 20 heat damage per second and the `OIL_FIRE1` or `OIL_FIRE2` particles.
