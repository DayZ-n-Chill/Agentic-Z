# Global functions and game services

Which global calls production mods rely on for the screen, debugging, launch parameters, files, web requests, sound, notifications, players, nearby objects, JSON, frame callbacks, key bindings, weather and bones, with a short example of each. Strings, math and config lookups are in `language-builtins.md`; entities and inventory in `entity-inventory-api.md`.

## Screen and mouse

`GetScreenSize` and `GetMousePos` (`P:\scripts\1_core\proto\ensystem.c:331` and `:329`); `GetWidgetUnderCursor` and `GetFocus` (`P:\scripts\1_core\proto\enwidgets.c:184` and `:702`).

```c
int w, h;
GetScreenSize(w, h);                   // screen resolution
int mx, my;
GetMousePos(mx, my);                   // mouse position in pixels
Widget hovered = GetWidgetUnderCursor();
Widget focused = GetFocus();
```

Vanilla handles `WindowsResizeEventTypeID` in `MissionGameplay.OnEvent` (`P:\scripts\5_mission\mission\missiongameplay.c:788`). A mod can catch the same event in a modded `DayZGame.OnEvent` and read `GetScreenSize` again.

## Debugging and launch parameters

`DumpStackString` (`P:\scripts\1_core\proto\endebug.c:50`); `TickCount` (`P:\scripts\1_core\proto\ensystem.c:106`); `GetCLIParam` and `IsCLIParam` (`ensystem.c:125` and `:135`), both with examples in the vanilla comments.

```c
string stack;
DumpStackString(stack);               // the call stack as a string
int start = TickCount(0);
int elapsed = TickCount(start);       // CPU ticks since start

bool has = IsCLIParam("myFlag");      // -myFlag
string val;
GetCLIParam("port", val);             // -port=2302
```

The vanilla comment says `TickCount` returns "number of CPU ticks between 'prev' and 'now'". It gives no conversion to milliseconds, so compare tick counts with each other rather than dividing by a fixed number.

## Listing a folder

`FindFile`, `FindNextFile` and `CloseFindFile` (`P:\scripts\1_core\proto\ensystem.c:520` to `:522`), with `FileAttr` at `:505` and `FindFileFlags` at `:513`. Enforce Script has no `do ... while`, so loop on a flag:

```c
string filename;
FileAttr attr;
FindFileHandle fh = FindFile(dir + "/*", filename, attr, FindFileFlags.ALL);
if (fh)
{
    bool found = true;
    while (found)
    {
        bool isDir = (attr & FileAttr.DIRECTORY);
        found = FindNextFile(fh, filename, attr);
    }
    CloseFindFile(fh);
}
```

## Web requests

`CreateRestApi` and `GetRestApi` (`P:\scripts\3_game\http\restapi.c:181` and `:183`), `POST` (`:123`), `SetHeader` (`:141`), `RestCallback` (`:50`).

```c
RestApi api = GetRestApi();
if (!api)
    api = CreateRestApi();
RestContext ctx = api.GetRestContext("https://example.com/api");
ctx.SetHeader("application/json");
ctx.POST(new MyMod_RestCallback(), "param=value", jsonBody);
// MyMod_RestCallback extends RestCallback and overrides OnSuccess, OnError, OnTimeout
```

## Sound

`SEffectManager.PlaySound(soundSetName, worldPos)` plays a positioned sound (`P:\scripts\3_game\effectmanager.c:178`). For a 2D interface sound, build the sound object yourself: `SoundObjectBuilder` and `SoundParams` (`P:\scripts\3_game\sound.c:82` and `:137`), `Play2D` (`:58`).

```c
SoundParams sp = new SoundParams(soundSetName);
if (sp.IsValid())
{
    SoundObjectBuilder sob = new SoundObjectBuilder(sp);
    SoundObject so = sob.BuildSoundObject();
    so.SetKind(WaveKind.WAVEEFFECT);
    AbstractWave wave = g_Game.GetSoundScene().Play2D(so, sob);
    wave.Loop(false);
    wave.Play();
}
```

## Notifications

`NotificationSystem.SendNotificationToPlayerIdentityExtended(identity, show_time, title, detail, icon)` (`P:\scripts\3_game\client\notifications\notificationsystem.c:141` to `:151`) sends `RPC_SEND_NOTIFICATION_EXTENDED`, and the vanilla client shows it, so a server mod can pop up a message with no client mod. A `null` identity sends it to everyone.

The local calls such as `AddNotificationExtended(show_time, title, detail, icon)` (`notificationsystem.c:215`) are for the client. Called on the server they notify nobody (measured in game).

## Online players

On the server, `GetPlayerIndentities` (`P:\scripts\3_game\global\game.c:1166`); vanilla spells it `Indentities`, so keep that spelling. On a client, `ClientData.m_PlayerList` (`P:\scripts\3_game\client\clientdata.c:8`).

```c
// server
array<PlayerIdentity> ids = new array<PlayerIdentity>();
g_Game.GetPlayerIndentities(ids);

// client
if (ClientData.m_PlayerList && ClientData.m_PlayerList.m_PlayerList)
{
    foreach (SyncPlayer sp : ClientData.m_PlayerList.m_PlayerList)
    {
        string steamId = sp.m_Identity.GetPlainId();
    }
}
```

## Objects near a point

`GetObjectsAtPosition3D(pos, radius, out objects, out proxyCargos)` (`P:\scripts\3_game\global\game.c:930`) returns terrain statics, such as bushes (an `Object` with an empty `GetType()`), as well as players, items, vehicles and infected. Filter by type if you only want entities. Measured in game: a radius of 30 in an open field returned 38 objects.

## JSON

`JsonSerializer` (`P:\scripts\3_game\gameplay.c:49`); `JsonFileLoader.LoadFile` and `SaveFile` return `bool` (`P:\scripts\3_game\tools\jsonfileloader.c:7` and `:42`), while the old `JsonLoadFile` returns `void` (`:105`).

```c
JsonSerializer serializer = new JsonSerializer();
string json, error;
serializer.WriteToString(instance, true, json);
serializer.ReadFromString(instance, jsonString, error);

JsonFileLoader<MyMod_Config>.LoadFile(path, instance, error);
JsonFileLoader<MyMod_Config>.SaveFile(path, instance, error);
```

Check the `bool` from `LoadFile` to catch a failure. `JsonLoadFile` and `JsonSaveFile` return nothing and give no error, so read them only in old code and don't use them in new code. File reads and writes block the main thread; never call them from `OnUpdate`.

## Frame callbacks

`GetUpdateQueue` (`P:\scripts\3_game\dayzgame.c:1238`); when each queue ticks is in `../references/api_scheduling.md`.

```c
g_Game.GetUpdateQueue(CALL_CATEGORY_SYSTEM).Insert(MyCallback);   // every frame: void MyCallback(float timeslice)
g_Game.GetUpdateQueue(CALL_CATEGORY_SYSTEM).Remove(MyCallback);

g_Game.GetCallQueue(CALL_CATEGORY_SYSTEM).Call(MyFunction);       // once, next frame
```

## Key bindings

`Input.LocalPress(string action, bool check_focus = true)` (`P:\scripts\3_game\tools\input.c:62`). On `UAInput` (`P:\scripts\3_game\inputapi\uainput.c`): `Binding` `:39`, `SelectAlternative` `:48`, `AlternativeCount` `:49`, `LocalPress` `:60`, `IsCombo` `:67`, `Supress` `:84` (vanilla's spelling). `UAIDWrapper.InputP` is at `:29`, and on the input API `GetInputByName` at `:218` and `GetButtonName` at `:220`. The `inputs.xml` format is in `../integrations/input_bindings.md`.

```c
// three ways to test a press
g_Game.GetInput().LocalPress("UAMyModAction", false);
GetUApi().GetInputByName("UAMyModAction").LocalPress();
UAIDWrapper wrapper = GetUApi().GetInputByName("UAMyModAction").GetPersistentWrapper();   // store once
// each frame: if (wrapper.InputP() && wrapper.InputP().LocalPress()) { ... }

GetUApi().GetInputByName("UAMyModAction").Supress();    // hide the press from other handlers

UAInput input = GetUApi().GetInputByName("UAMyModAction");
string keyName = GetUApi().GetButtonName(input.Binding(0));
for (int a = 0; a < input.AlternativeCount(); a++)
{
    input.SelectAlternative(a);
    if (input.IsCombo())
    {
        // input.Binding(0) plus input.Binding(1)
    }
}
```

## Clipboard and mission time

`CopyToClipboard` (`P:\scripts\3_game\global\game.c:663`); `GetTime` returns the mission time as an `int` of milliseconds (`game.c:1534`).

## Weather

`g_Game.GetWeather()` returns the `Weather` object (`P:\scripts\3_game\global\game.c:1370`).

| Call | What it does | Source |
|---|---|---|
| `GetOvercast()`, `GetFog()`, `GetRain()`, `GetSnowfall()`, `GetWindDirection()` | Each returns a `WeatherPhenomenon` | `P:\scripts\3_game\weather.c:183` to `:199` |
| `GetActual()`, `GetForecast()` | Read a phenomenon | `weather.c:38` to `:41` |
| `Set(float forecast, float time = 0, float minDuration = 0)` | `time` is the seconds to blend over, `minDuration` the seconds the value holds | `weather.c:43` to `:49` |
| `SetLimits`, `SetForecastChangeLimits` | Bound a phenomenon | `weather.c:74` and `:95` |
| `GetWindSpeed()`, `SetWindSpeed()`, `GetWindMaximumSpeed()`, `SetWindMaximumSpeed()` | Wind speed is a plain float on `Weather` | `weather.c:248` to `:269` |
| `SetStorm(float density, float threshold, float timeOut)` | Lightning: density 0 to 1, the overcast above which lightning may appear, and the minimum seconds between strikes | `weather.c:211` to `:219` |

Measured on a fresh Chernarus server: overcast 0.484, rain 0, fog 0, wind speed 10.

`Weather.GetNoiseReductionByWeather()` is `[Obsolete]` in 1.30, not deleted, in favour of `GetNoiseReductionByWeatherEx(notnull Object object)` (`weather.c:407` and `:408`). That one is also `[Obsolete]`, "Kept for HUD and old mods", because AI noise damping now lives in the native AI parameters. Vanilla still calls `GetNoiseReductionByWeatherEx` (`P:\scripts\4_world\static\sensesaievaluate.c:23`).

`World.Is3rdPersonDisabled()` is `[Obsolete]` in 1.30. Use `GetThirdPersonViewMode()`, which returns `ThirdPersonMode` with `DISABLED`, `ENABLED` and `VEHICLES_ONLY` (`P:\scripts\3_game\global\world.c:177`, `:291` to `:305`).

## Bones

`GetBoneIndex` (`P:\scripts\3_game\entities\entity.c:36`) and `GetBonePositionWS` (`P:\scripts\3_game\entities\object.c:238`):

```c
int idx = man.GetBoneIndex("Spine2");
vector worldPos = man.GetBonePositionWS(idx);
```
