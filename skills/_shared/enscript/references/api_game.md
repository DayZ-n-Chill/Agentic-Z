# Reference: the game object, side checks, config and logging

`GetGame()` and the calls a mod makes on it most: which side the code runs on, time, the mission, the world, config reads and logging. Facts cite the vanilla file on `P:\scripts\` they were checked against (game storage version 144, `P:\scripts\3_game\global\game.c:5`).

## Getting the game

| Call | Returns | Source |
|---|---|---|
| `GetGame()` | The global `DayZGame` instance. | `P:\scripts\3_game\gameplay.c:636` |
| `g_Game` | The same instance as a global variable. Current vanilla writes `g_Game` almost everywhere. | `P:\scripts\3_game\dayzgame.c:4074` |
| `GetDayZGame()` | The same, typed `DayZGame`. | `P:\scripts\3_game\dayzgame.c:4076` |

The engine API lives on `CGame` (`P:\scripts\3_game\global\game.c:7`); `DayZGame` adds the call queues and RPC dispatch.

## Which side am I on

| Call | True when | Source |
|---|---|---|
| `IsServer()` | This machine has authority: a dedicated server, or single player. | `P:\scripts\3_game\global\game.c:1120` |
| `IsClient()` | The game runs as a client. | `:1119` |
| `IsMultiplayer()` | A networked session. | `:1118` |
| `IsDedicatedServer()` | A dedicated server. Vanilla calls it the robust check, valid much sooner during load than the others. | `:1121` to `:1125` |

Use `IsServer()` for authority work so it also runs in single player. Use `IsDedicatedServer()` or `#ifdef SERVER` to skip client only work such as UI and sound on a server (`language_compile.md`, `_shared/conventions/scripts.md`).

## Time

| Call | Unit | Source |
|---|---|---|
| `GetTime()` | Mission time in milliseconds, as `int`. | `P:\scripts\3_game\global\game.c:1535` |
| `GetTickTime()` | Seconds since the game started, as `float`. | `:911` to `:914` |

Both clocks start again at every boot, so neither is a timestamp you can save or use to order events across restarts. For a saved timestamp use the UTC wall clock: `GetYearMonthDayUTC(out int year, out int month, out int day)` (`P:\scripts\1_core\proto\ensystem.c:100`) and `GetHourMinuteSecondUTC(out int hour, out int minute, out int second)` (`P:\scripts\1_core\proto\ensystem.c:76`).

The world clock speed has a setter and no getter: `proto native void SetTimeMultiplier(float timeMultiplier)` (`P:\scripts\3_game\global\world.c:14`), and no `GetTimeMultiplier` exists in `P:\scripts`. Code that reports the multiplier must remember what it set, or report it as unknown, never as a default `0`.

The `Math` class has no `Exp`. Write an exponential as `Math.Pow(Math.EULER, x)`: `Pow` is at `P:\scripts\1_core\proto\enmath.c:183` and `EULER` at `P:\scripts\1_core\proto\enmath.c:11`, and vanilla writes `Pow(EULER,-mean)` itself (`P:\scripts\1_core\proto\enmath.c:710`).

## Mission and world

- `GetMission()` returns `Mission` (`P:\scripts\3_game\global\game.c:1093`). Cast it to `MissionServer` on the server or `MissionGameplay` on the client; both extend `MissionBase` (`P:\scripts\5_mission\mission\missionserver.c:5`, `P:\scripts\5_mission\mission\missiongameplay.c:1`). Those types live in `5_mission`, so only `5_mission` code can name them.
- `GetMission().GetHud()` gives the HUD on a client (`P:\scripts\3_game\gameplay.c:720`).
- `GetWorld()` returns the `World` (`P:\scripts\3_game\global\game.c:931`).
- `SurfaceY(x, z)` is the terrain height and `SurfaceRoadY(x, z)` includes roads and surfaces on top (`:1176`, `:1177`).
- `GetObjectsAtPosition(pos, radius, out objects, out proxyCargos)` and its 3D form find nearby objects (`:923`, `:930`). They are slow; the style guide says to avoid them (`_shared/enscript-style.md`).
- `GetObjectByNetworkId(low, high)` finds an object from its two network ID halves (`:356`).
- `GetWeather()` returns the `Weather` object (`P:\scripts\3_game\global\game.c:1371`). `GetOvercast()`, `GetFog()`, `GetRain()`, `GetSnowfall()` and `GetWindDirection()` each return a phenomenon (`P:\scripts\3_game\weather.c:183-199`) with `GetActual()` and `GetForecast()` (`P:\scripts\3_game\weather.c:38-41`) and `Set(forecast, time, minDuration)`, where `time` is the seconds taken to reach the value and `minDuration` the seconds it then holds (`P:\scripts\3_game\weather.c:43-49`). Wind speed is a plain float, `GetWindSpeed()` and `SetWindSpeed()` (`P:\scripts\3_game\weather.c:248-256`), and `SetStorm(density, threshold, timeOut)` sets lightning (`P:\scripts\3_game\weather.c:211-219`).
- To show a popup on a client from the server with no client mod, call `NotificationSystem.SendNotificationToPlayerIdentityExtended(identity, show_time, title, detail, icon)` (`P:\scripts\3_game\client\notifications\notificationsystem.c:141-151`); it sends `RPC_SEND_NOTIFICATION_EXTENDED` and the vanilla client draws it. `AddNotificationExtended` (`P:\scripts\3_game\client\notifications\notificationsystem.c:215`) is the local, client side call and shows nothing when the server calls it.

## World to screen

`GetScreenPos(worldPos)` returns the screen position in pixels as `x` and `y`, and in `z` the distance between the camera and the point (`P:\scripts\3_game\global\game.c:962` to `:963`). A point behind the camera still gets an `x` and `y`, so check `z` before you place a marker. Vanilla shows its debug labels only when `z > 0` (`P:\scripts\4_world\plugins\pluginbase\plugindeveloper\pluginuniversaltemperaturesourceclient.c:163` to `:167`).

```c
vector screen = g_Game.GetScreenPos(targetPos);
m_Marker.Show(screen[2] > 0);
if (screen[2] > 0)
    m_Marker.SetPos(screen[0], screen[1]);
```

## Players

`GetPlayer()` is the player this machine controls, `GetPlayers(out array<Man>)` fills every player, and `GetPlayerByIndex(i)` wraps it (`P:\scripts\3_game\global\game.c:944` to `:952`). A dedicated server controls no player, so server code finds players with `GetPlayers` or from a `PlayerIdentity`. More in `api_player.md`.

On a client `GetPlayer()` is also `null` while the game is still loading. Reported, not checked on `P:\` (the crash is native): during that time the camera getters `GetCurrentCameraPosition()` and `GetCurrentCameraDirection()` (`P:\scripts\3_game\global\game.c:731`, `:732`) crash the client with a native crash that no script null check catches. In a client handler that can run early (an RPC, a polled command), return when `GetGame().GetPlayer()` is `null` before you call anything that reads the camera or the world. Detail: `skills/_shared/enscript/depth/runtime-traps.md`.

## Reading config

Paths are class names separated by spaces, not dots: `"CfgSurfaces " + surface + " isDigable"` (`P:\scripts\3_game\global\game.c:1248`). The first word may also be `configFile` or `missionConfigFile` (`:445`).

| Call | Returns | Source |
|---|---|---|
| `ConfigGetText(path, out value)` | `bool` success, string in `value`. | `:449` |
| `ConfigGetTextOut(path)` | The string directly. | `:465` |
| `ConfigGetFloat(path)`, `ConfigGetInt(path)`, `ConfigGetVector(path)` | The value, or 0 when missing. | `:524`, `:539`, `:532` |
| `ConfigGetTextArray(path, out values)` | Fills a `TStringArray`. | `:558` |
| `ConfigIsExisting(path)` | Whether the entry exists. Check it before you trust a 0. | `:612` |
| `IsKindOf(className, parentName)` | Config inheritance test by name. | `:1437` |

An object builds its own path from `GetType()`, for example `"CfgVehicles " + GetType() + " "` (`P:\scripts\3_game\entities\object.c:424`).

`IsKindOf(string cfg_class_name, string cfg_parent_name)` follows the parents written in config, not the parents written in script (`P:\scripts\3_game\global\game.c:1437`). A class can be `class X : Y` in script and `class X : Z` in `CfgVehicles`; the test then answers for `Z`. When a check that should match through inheritance does not, read the class's config parent (for a packed mod, turn its `config.bin` back into text with `CfgConvert.exe -txt`) and compare the two chains. The reported case is in `skills/_shared/enscript/depth/api-patterns.md`.

## Logging

| Call | Writes | Source |
|---|---|---|
| `Print(value)` | Any value to the script log. | `P:\scripts\1_core\proto\endebug.c:96` |
| `PrintFormat("%1 %2", a, b)` | Formatted text. | `:108` |
| `PrintToRPT(value)` | The RPT file. | `:99` |
| `ErrorEx(msg, ErrorExSeverity.WARNING)` | A script error with a severity of `INFO`, `WARNING` or `ERROR` (the default). | `:83`, `:61` |
| `DumpStack()` | The current call stack. | `:27` |
| `Debug.Log(msg, plugin)` | Only when `LogManager.IsLogsEnable()` is true; otherwise it writes nothing. | `P:\scripts\3_game\tools\debug.c:183`, `:595` |

Use `Print` or `ErrorEx` for messages you must see in a normal test session; `Debug.Log` is silent unless logs are enabled.

Reported, not checked on `P:\` (the log writer is native): the script log cuts every `Print` line at 255 characters (172 of 193 diagnostic lines were cut at exactly 255 in one measured session). Write a long diagnostic as several short lines that share a tag, and print a stack line by line. Later measurements narrow it: the cut came from the 1.29 retail logger, and neither DayZDiag 1.30 nor the 1.30 retail server cut long lines. Short lines stay the safe habit for a mod that may run on an older server.

On the retail server the RPT repeats the script log's `SCRIPT` lines (server RPTs of 1.29 and 1.30), so a script error shows in both.

## Connect error codes

A `CONNECTING FAILED (0x...)` message is an engine connect error, not a BattlEye kick. The code is two shorts: the high short is the `ErrorCategory`, the low one the value inside it (`P:\scripts\3_game\global\errormodulehandler\errormodulehandler.c:4-26`). Category 1 is `ConnectErrorClient` (`connecterrorclientmodule.c`) and 2 is `ConnectErrorServer` (`connecterrorservermodule.c`), both in `P:\scripts\3_game\global\errormodulehandler\`; each enum starts `UNKNOWN = -1`, `OK = 0`. So `0x00020005` is `EConnectErrorServer.FILE_PATCHING` (`connecterrorservermodule.c:10`) and `0x00010002` is `EConnectErrorClient.ALREADY_CONNECTING` (`connecterrorclientmodule.c:7`): the client is still busy with an earlier join. The usage examples in the comments of `errormodulehandler.c` number the categories one higher; the measured messages follow the enum. The codes seen in test runs and their fixes are in `skills/dayz-launch-test/references/troubleshooting.md`.
