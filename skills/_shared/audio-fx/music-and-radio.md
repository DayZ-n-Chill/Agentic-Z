# Music and radio: the dynamic music player and transmitter static

How the client side music player picks a track, how a mod adds a music zone or the music of a custom world, and how the 1.30 bunker static of radios works. Line numbers are from the 1.30 scripts on `P:\`; statements about 1.29 are not yet checked on `P:\`.

## Contents

- [The dynamic music player](#the-dynamic-music-player)
- [A music zone around an entity](#a-music-zone-around-an-entity)
- [Music of a custom world (1.30)](#music-of-a-custom-world-130)
- [Radio static on the bunker frequency (1.30)](#radio-static-on-the-bunker-frequency-130)

## The dynamic music player

`DynamicMusicPlayer` (`P:\scripts\3_game\systems\dynamicmusicplayer\dynamicmusicplayer.c:81`) plays menu, time of day and location music on the client. The mission creates it with the registry of the current world (`P:\scripts\5_mission\mission\missionbase.c:36`), inside `#ifndef SERVER`, and any script reaches it with `GetGame().GetMission().GetDynamicMusicPlayer()` (`P:\scripts\3_game\gameplay.c:752`).

Its categories are the `EDynamicMusicPlayerCategory` enum: `NONE`, `MENU`, `CREDITS`, `TIME`, `LOCATION_STATIC`, `LOCATION_STATIC_PRIORITY` and `LOCATION_DYNAMIC` (`P:\scripts\3_game\enums\edynamicmusicplayercategory.c:1`).

The public calls a mod uses:

| Line | Method | Use |
|---|---|---|
| 272 | `SetCategory(DynamicMusicPlayerCategoryPlaybackData playbackData)` | Switch the playing category. The data object holds `m_Category`, `m_Forced` and `m_FadeOut` (line 73). The credits menu uses it. |
| 289 | `RegisterDynamicLocation(notnull Entity caller, int locationType, float locationSize)` | Add a music zone around an entity. |
| 303 | `UnregisterDynamicLocation(notnull Entity caller)` | Remove that zone. |

There is no public call to play one named track. `PlayTrack` is `private` (`P:\scripts\3_game\systems\dynamicmusicplayer\dynamicmusicplayer.c:511`). It builds a `SoundObject`, sets `WaveKind.WAVEMUSIC` and plays it with `Play2D`, so a track is an ordinary sound set played flat in the music category. A track is faded out with `SetFadeOutFactor` on a 0.2 second tick (`P:\scripts\3_game\systems\dynamicmusicplayer\dynamicmusicplayer.c:579`).

## A music zone around an entity

The vanilla contaminated area is the model. It registers itself on the client and removes itself when it is deleted:

```c
// P:\scripts\4_world\classes\contaminatedarea\contaminatedarea.c:17
override void InitZoneClient()
{
    super.InitZoneClient();

    g_Game.GetMission().GetDynamicMusicPlayer().RegisterDynamicLocation(this, DynamicMusicLocationTypes.CONTAMINATED_ZONE, m_Radius);
}

override void EEDelete(EntityAI parent)
{
    super.EEDelete(parent);

    if (!g_Game.IsServer())
        g_Game.GetMission().GetDynamicMusicPlayer().UnregisterDynamicLocation(this);
}
```

- The location types are constants of `DynamicMusicLocationTypes`: `NONE = -1`, `CONTAMINATED_ZONE = 0` and `UNDERGROUND = 1` (`P:\scripts\3_game\systems\dynamicmusicplayer\dynamicmusicplayer.c:4`).
- `locationSize` is turned into a rectangle around the entity's position (`P:\scripts\3_game\systems\dynamicmusicplayer\dynamicmusicplayer.c:289`), so the zone does not follow an entity that moves later.
- Call both on the client only. The mission creates the music player inside `#ifndef SERVER`, so a dedicated server has none.

## Music of a custom world (1.30)

Since 1.30 each world builds its own registry. `MissionBase.InitialiseWorldData()` switches on the lower case world name and creates the registry class for it (`P:\scripts\5_mission\mission\missionbase.c:107`):

| World name | Registry | Line |
|---|---|---|
| `chernarusplus` | `DynamicMusicPlayerRegistryChernarus` | 117 |
| `enoch` | `DynamicMusicPlayerRegistryEnoch` | 122 |
| `sakhal` | `DynamicMusicPlayerRegistrySakhal` | 127 |
| `nasdara` | `DynamicMusicPlayerRegistryNasdara` | 132 |
| `samplemap5` | `DynamicMusicPlayerRegistryNasdara` | 137 |
| `mainmenuscenexbox` (console builds only) | the base `DynamicMusicPlayerRegistry` | 143 |
| any name not listed in the switch | the base `DynamicMusicPlayerRegistry` | 149 |

For a custom world, write a subclass of `DynamicMusicPlayerRegistry` (`P:\scripts\3_game\systems\dynamicmusicplayer\dynamicmusicplayerregistry.c:1`) and create it for your world name in a modded `MissionBase.InitialiseWorldData()`. The Nasdara registry shows what to override:

- `RegisterTracksMenu()` for menu music (`P:\scripts\3_game\systems\dynamicmusicplayer\dynamicmusicplayerregistrynasdara.c:8`).
- `RegisterTracksLocationStatic()` for fixed zones (`P:\scripts\3_game\systems\dynamicmusicplayer\dynamicmusicplayerregistrynasdara.c:18`). Each zone is one call to `RegisterTrackLocationStaticMultiRectangle` with a sound set name and a list of rectangles, such as `"Music_nasdara_Desert_SoundSet"` (`P:\scripts\3_game\systems\dynamicmusicplayer\dynamicmusicplayerregistrynasdara.c:41`).
- `RegisterTracksTime()` for time of day music (`P:\scripts\3_game\systems\dynamicmusicplayer\dynamicmusicplayerregistrynasdara.c:71`). Nasdara registers 15 tracks there with `RegisterTrackTime`: 9 for `DAY`, 2 for `DUSK`, 2 for `DAWN` and 2 for `NIGHT`. Music follows these four parts of the day, not the hour.

`RegisterTrackLocationStaticMultiRectangle(string soundSetName, array<ref TVectorArray> locationBoundaries, int timeOfDay = DynamicMusicPlayerTimeOfDay.ANY, bool runImmediately = false)` is declared `protected` at `P:\scripts\3_game\systems\dynamicmusicplayer\dynamicmusicplayerregistry.c:224`, so call it from inside your registry subclass. With `runImmediately` true the track goes into the `LOCATION_STATIC_PRIORITY` category, otherwise into `LOCATION_STATIC`.

`DynamicMusicPlayerTimeOfDay` is a simplified form of the world's daytime (`P:\scripts\3_game\systems\dynamicmusicplayer\dynamicmusicplayer.c:1054`). Its `Translate` turns `MORNING`, `NOON` and `AFTERNOON` into `DAY`, and `EVENING` into `NIGHT` (`P:\scripts\3_game\systems\dynamicmusicplayer\dynamicmusicplayer.c:1057`).

## Radio static on the bunker frequency (1.30)

A transmitter can play a different static noise while it is tuned to the bunker frequency.

- `TransmitterBase` declares two sound set names, `SOUND_RADIO_TURNED_ON` (`P:\scripts\4_world\entities\itembase\transmitterbase.c:5`) and `SOUND_BUNKER_STATIC_NOISE` (`P:\scripts\4_world\entities\itembase\transmitterbase.c:6`). Both are empty by default.
- `UseBunkerStaticNoise()` returns `IsTunedToBunkerFrequency() && SOUND_BUNKER_STATIC_NOISE != ""` (`P:\scripts\4_world\entities\itembase\transmitterbase.c:135`). When it is true, the static that starts with the radio uses the bunker sound set (`P:\scripts\4_world\entities\itembase\transmitterbase.c:148`).
- `IsTunedToBunkerFrequency()` is a native method of `ItemTransmitter`, not of `InventoryItem` (`P:\scripts\4_world\entities\core\inherited\inventoryitem.c:25`). The frequency it matches is inside the engine and is not in script.
- The personal radio sets `SOUND_BUNKER_STATIC_NOISE = "bunkerbroadcast_staticnoise_SoundSet"` in its constructor (`P:\scripts\4_world\entities\itembase\transmitterbase\personalradio.c:6`), and the base radio does the same (`P:\scripts\4_world\entities\itembase\transmitterbase\baseradio.c:6`).
- Clients switch between the two noises in `OnVariablesSynchronized` (`P:\scripts\4_world\entities\itembase\transmitterbase.c:125`). `SetNextFrequency` already calls `SetSynchDirty()` after a frequency change (`P:\scripts\4_world\entities\itembase\transmitterbase.c:49`).

A custom radio that extends `TransmitterBase` gets the behaviour by setting `SOUND_BUNKER_STATIC_NOISE` in its constructor. A custom radio that changes frequency through its own code must call `SetSynchDirty()` after the change, or clients never switch. One that leaves the name empty never plays the bunker static.
