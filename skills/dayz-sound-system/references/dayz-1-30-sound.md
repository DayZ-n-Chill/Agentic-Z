# DayZ 1.30 sound: headless check, noise, music, radios

What DayZ 1.30 changed for mod audio, with the vanilla lines quoted, what breaks in a 1.29 mod and a migration checklist. Line numbers are from the 1.30 scripts on `P:\`. Statements about 1.29 come from the notes this file was built from; `P:\` holds 1.30, so they are not yet checked on `P:\`.

The pack files under `skills/_shared/audio-fx/` explain how to use each system; this file is the record of what changed.

## Contents

- [Server and headless checks](#server-and-headless-checks)
- [EffectSound: a fade in starts at zero volume](#effectsound-a-fade-in-starts-at-zero-volume)
- [Player sound event HEAVY_BREATHING (animation event 907)](#player-sound-event-heavy_breathing-animation-event-907)
- [Music: one registry per world](#music-one-registry-per-world)
- [Transmitters: bunker static](#transmitters-bunker-static)
- [Step sounds of static vegetation](#step-sounds-of-static-vegetation)
- [The destructor of a sound event](#the-destructor-of-a-sound-event)
- [Noise system](#noise-system)
- [Sandstorm sound](#sandstorm-sound)
- [A changelog entry that is not in script](#a-changelog-entry-that-is-not-in-script)
- [What changes](#what-changes)
- [What breaks in a 1.29 audio or stealth mod](#what-breaks-in-a-129-audio-or-stealth-mod)
- [Migration checklist](#migration-checklist)

## Server and headless checks

`Object.PlaySoundSet` still tests only for a dedicated server in 1.30:

```c
// P:\scripts\3_game\entities\object.c:1247
	bool PlaySoundSet( out EffectSound sound, string sound_set, float fade_in, float fade_out, bool loop = false )
	{
		if ( g_Game && !g_Game.IsDedicatedServer() )
		{
```

Up to 1.29 that was the only check written down for sound. 1.30 adds a second one on the game, for code that must not run on a headless client either:

```c
// P:\scripts\3_game\global\game.c:1132
	/**
	 \brief Check whether the application is headless or a dedicated server (it combines IsDedicatedServer and IsHeadless)
		\note This includes servers with a head as well (-headlessMode=0)
	*/
	proto native bool		IsHeadlessOrDedicatedServer();
```

The vanilla sound handlers that use it:

```c
// P:\scripts\4_world\classes\soundhandlers\itemsoundhandler.c:121
		if (g_Game.IsHeadlessOrDedicatedServer())
			return;
```

```c
// P:\scripts\4_world\classes\soundhandlers\playersoundmanager.c:105
		if( !g_Game.IsHeadlessOrDedicatedServer() ) 
		{
			m_ClientCharacterDistanceCheck.Run(2, this, "CheckAllowUpdate", null, true);
		}
```

```c
// P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgsounds.c:335
	if(!g_Game.IsHeadlessOrDedicatedServer())//sounds are unnecessary on server
	{
```

`SEffectManager.Cleanup` logs a warning when sound parameters or effects exist on that side (`P:\scripts\3_game\effectmanager.c:536`). The source notes say `IsHeadlessOrDedicatedServer` is not in the 1.29 `game.c`.

Design note: in new play and stop code for synced item sounds, test `IsHeadlessOrDedicatedServer()`. `PlaySoundSet` on `Object` still tests `IsDedicatedServer()`; do not assume it moved.

## EffectSound: a fade in starts at zero volume

```c
// P:\scripts\3_game\effects\effectsound.c:549
	void Event_OnSoundWaveStarted()
	{
		m_SoundWaveIsPlaying = true;
		if (m_SoundFadeInDuration > 0)
		{
			SetSoundVolume(0);
		}
```

Up to 1.29, `Event_OnSoundWaveStarted` set `m_SoundWaveIsPlaying` and called its invokers with no change of volume (1.29, not yet checked on `P:\`). Design note: a looped item sound with a fade in above zero no longer starts at full volume for one frame.

## Player sound event HEAVY_BREATHING (animation event 907)

The new ID in the enum:

```c
// P:\scripts\4_world\classes\soundevents\playersoundevents\playersoundeventhandler.c:38
	HEAVY_BREATHING,
```

Its event class:

```c
// P:\scripts\4_world\classes\soundevents\playersoundevents\events\heavybreathevents.c:21
class HeavyBreathEvent1 : HeavyBreathSoundEventBase
{
	void HeavyBreathEvent1()
	{
		m_ID = EPlayerSoundEventID.HEAVY_BREATHING;
		m_SoundVoiceAnimEventClassID = 907;
	}
}
```

It is registered with `RegisterState(new HeavyBreathEvent1())` (`P:\scripts\4_world\classes\soundevents\playersoundevents\playersoundeventhandler.c:99`). Vanilla requests it from silicosis with `RequestSoundEventEx(EPlayerSoundEventID.HEAVY_BREATHING, true, EPlayerSoundEventParam.HIGHEST_PRIORITY)` (`P:\scripts\4_world\classes\playermodifiers\modifiers\diseases\silicosis.c:105`).

## Music: one registry per world

`RegisterDynamicLocation` is unchanged and still on `DynamicMusicPlayer` (`P:\scripts\3_game\systems\dynamicmusicplayer\dynamicmusicplayer.c:289`). What is new: each world creates its own registry.

```c
// P:\scripts\5_mission\mission\missionbase.c:130
			case "nasdara":
				m_WorldData = new NasdaraData();
				m_DynamicMusicPlayerRegistry = new DynamicMusicPlayerRegistryNasdara();
				break;
```

The fixed music zones of Nasdara are registered with `RegisterTrackLocationStaticMultiRectangle` (declared at `P:\scripts\3_game\systems\dynamicmusicplayer\dynamicmusicplayerregistry.c:224`; the calls run from `P:\scripts\3_game\systems\dynamicmusicplayer\dynamicmusicplayerregistrynasdara.c:39` to `:67`). Its time of day music is 15 tracks for `DAY`, `DUSK`, `DAWN` and `NIGHT`, registered in `RegisterTracksTime` (`P:\scripts\3_game\systems\dynamicmusicplayer\dynamicmusicplayerregistrynasdara.c:71`). Music does not follow the hour.

```c
// P:\scripts\3_game\systems\dynamicmusicplayer\dynamicmusicplayer.c:1054
class DynamicMusicPlayerTimeOfDay : WorldDataDaytime
{
	//! translates WorldDataDaytime -> DynamicMusicPlayerTimeOfDay
	static int Translate(int value)
	{
		switch (value)
		{
			case MORNING:
				return DAY;
			case NOON:
				return DAY;
			case AFTERNOON:
				return DAY;
			case EVENING:
				return NIGHT;
```

## Transmitters: bunker static

```c
// P:\scripts\4_world\entities\itembase\transmitterbase.c:5
	string SOUND_RADIO_TURNED_ON 		= "";
	string SOUND_BUNKER_STATIC_NOISE 	= "";
```

```c
// P:\scripts\4_world\entities\itembase\transmitterbase.c:135
	protected bool UseBunkerStaticNoise()
	{
		return IsTunedToBunkerFrequency()  &&  SOUND_BUNKER_STATIC_NOISE != "";
	}
```

The native method is declared in the class `ItemTransmitter`, in the file `inventoryitem.c`. It is not a method of the class `InventoryItem`:

```c
// P:\scripts\4_world\entities\core\inherited\inventoryitem.c:25
	proto native bool IsTunedToBunkerFrequency();
```

```c
// P:\scripts\4_world\entities\itembase\transmitterbase\personalradio.c:6
		SOUND_BUNKER_STATIC_NOISE = "bunkerbroadcast_staticnoise_SoundSet";
```

The base radio assigns `SOUND_BUNKER_STATIC_NOISE` the same way (`P:\scripts\4_world\entities\itembase\transmitterbase\baseradio.c:6`).

`SetNextFrequency` already calls `SetSynchDirty()` (`P:\scripts\4_world\entities\itembase\transmitterbase.c:49`). Not known: the frequency that `IsTunedToBunkerFrequency` matches; it is inside the engine.

## Step sounds of static vegetation

```c
// P:\scripts\3_game\entities\staticobjecttype.c:13
		string pathBase = "CfgNonAIVehicles " + GetName() + " VegetationSounds";
		if (!g_Game.ConfigIsExisting(pathBase))
			return;
```

```c
// P:\scripts\3_game\entities\staticobjecttype.c:44
	SoundObjectBuilder GetVegetationSoundBuilderFromEventID(int stepEventID)
	{
		if (m_CustomVegetationSoundsMap)
			return m_CustomVegetationSoundsMap.Get(stepEventID);
```

The macro `CUSTOM_PLAYER_MOVEMENT_SOUNDSETS` is at `P:\DZ\data\basicdefines.hpp:310` and runs to line 338. (An earlier digest placed it at lines 68 to 96 of that file; those lines hold other defines.) Animation event IDs it uses: walking 1, 2, 23, 24, 51, 52; crouched 21, 22, 31, 32, 33, 34, 131; running 3, 4, 17, 101, 53, 54; sprinting 5, 6, 35, 36, 37, 38, 100, 110, 111; scuffing 7, 8.

## The destructor of a sound event

```c
// P:\scripts\4_world\classes\soundevents\soundevents.c:12
	void ~SoundEventBase()
	{
		if (g_Game) 
			Stop();
	}
```

Design note: do not add a destructor of the 1.29 style to a subclass of `InfectedSoundEventBase` that calls `m_SoundSetCallback.Stop()` after `g_Game` is gone.

## Noise system

The change is described in `skills/_shared/audio-fx/noise-for-ai.md`, and the AI side in `skills/_shared/ai/perception.md`. The lines:

- `GetEnvironmentNoiseReduction` on `NoiseSystem` (`P:\scripts\3_game\noise.c:13`).
- The player's step noise passes only `GetNoiseMultiplier` (`P:\scripts\4_world\entities\dayzplayerimplement.c:3472`).
- Infected call `AddNoise` with no multiplier (`P:\scripts\4_world\entities\creatures\infected\zombiebase.c:600`).
- `class AIParams` with the rain, snowfall, sea, fog, wind and sandstorm multipliers (`P:\DZ\data\aiconfigs\config.cpp:12`).

## Sandstorm sound

The weather class `Sandstorm` names three sound sets in `soundSets[]`: `SandStorm_Debris_SoundSet`, `SandStorm_Close_SoundSet` and `SandStorm_Dist_SoundSet` (`P:\DZ\data\config.cpp:1536`). The engine plays them with the weather; script does not start them. The sandstorm also damps AI hearing through `sandstormToNoiseMultiplier` (`P:\DZ\data\aiconfigs\config.cpp:20`). Its visual side is in the dayz-particles skill, `skills/dayz-particles/references/dayz-1-30-particles.md`.

## A changelog entry that is not in script

The 1.30 changelog mentions `SoundHitType` and a `GetSoundHitType()` getter. No script file on `P:\` contains either name, and `P:\scripts\3_game\surfaceinfo.c` has no such getter. Do not call them.

## What changes

- Noise is damped by the engine, and `GetEnvironmentNoiseReduction(pos)` reads the result. `AIParams` gains snowfall, fog, wind and sandstorm multipliers.
- `IsHeadlessOrDedicatedServer()` guards the item and player sound paths. `Object.PlaySoundSet` still uses `IsDedicatedServer()`.
- `EffectSound` sets the volume to zero when a wave with a fade in starts.
- `EPlayerSoundEventID.HEAVY_BREATHING` and `HeavyBreathEvent1` (animation event 907); silicosis requests it.
- One `DynamicMusicPlayerRegistry` class per world, and `DynamicMusicPlayerTimeOfDay.Translate` (morning, noon and afternoon become `DAY`; evening becomes `NIGHT`).
- Transmitters: `SOUND_BUNKER_STATIC_NOISE` and `IsTunedToBunkerFrequency()`.
- `StaticObjectType` and the macro `CUSTOM_PLAYER_MOVEMENT_SOUNDSETS` for the step sounds of vegetation.
- Item sounds started with `StartItemSoundServer` travel by RPC, several per frame, instead of one synced variable (`skills/_shared/audio-fx/item-and-player-sounds.md`).

## What breaks in a 1.29 audio or stealth mod

1. Calls to `GetNoiseReductionByWeather` and `NoiseAIEvaluate.GetNoiseReduction` are marked obsolete.
2. A weather multiplier still passed into `AddNoise` damps the noise twice.
3. A custom radio that ignores the bunker frequency never plays `bunkerbroadcast_staticnoise_SoundSet`.
4. A subclass of `InfectedSoundEventBase` whose destructor calls `Stop()` without `if (g_Game)` can crash on shutdown (reported in the source notes, not checked on `P:\`).
5. A looped sound with a fade in now starts at volume zero. Levels tuned around the first frame of 1.29 sound different.

## Migration checklist

- [ ] What AI hears: read `GetEnvironmentNoiseReduction(pos)`; balance through `AIParams`, not through weather maths in script.
- [ ] New client play and stop code: test `IsHeadlessOrDedicatedServer()`.
- [ ] Custom transmitter: set `SOUND_BUNKER_STATIC_NOISE`, and call `SetSynchDirty()` after a frequency change (vanilla `SetNextFrequency` already does).
- [ ] Custom world music: subclass `DynamicMusicPlayerRegistry` and register zones with `RegisterTrackLocationStaticMultiRectangle`.
- [ ] Custom bushes: add `VegetationSounds` to the `CfgNonAIVehicles` class, or use the macro `CUSTOM_PLAYER_MOVEMENT_SOUNDSETS`.
- [ ] Do not call `SurfaceInfo.GetSoundHitType`; it is not in script.
- [ ] For the full signature lists, open `sound-deep-dive.md`.
