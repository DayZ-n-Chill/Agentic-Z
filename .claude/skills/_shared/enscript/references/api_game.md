# Reference: the game object, side checks, config and logging

`GetGame()` and the calls a mod makes on it most: which side the code runs on, time, the mission, the world, config reads and logging. Facts cite the vanilla file on `P:\scripts\` they were checked against (game storage version 144, `P:\scripts\3_game\global\game.c:5`). The older `game_api.md` holds extra tips that are not yet checked line by line.

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
| `GetTime()` | Mission time in milliseconds, as `int`. | `P:\scripts\3_game\global\game.c:1533` to `:1534` |
| `GetTickTime()` | Seconds since the game started, as `float`. | `:911` to `:914` |

## Mission and world

- `GetMission()` returns `Mission` (`P:\scripts\3_game\global\game.c:1093`). Cast it to `MissionServer` on the server or `MissionGameplay` on the client; both extend `MissionBase` (`P:\scripts\5_mission\mission\missionserver.c:5`, `P:\scripts\5_mission\mission\missiongameplay.c:1`). Those types live in `5_mission`, so only `5_mission` code can name them.
- `GetMission().GetHud()` gives the HUD on a client (`P:\scripts\3_game\gameplay.c:720`).
- `GetWorld()` returns the `World` (`P:\scripts\3_game\global\game.c:931`).
- `SurfaceY(x, z)` is the terrain height and `SurfaceRoadY(x, z)` includes roads and surfaces on top (`:1176`, `:1177`).
- `GetObjectsAtPosition(pos, radius, out objects, out proxyCargos)` and its 3D form find nearby objects (`:923`, `:930`). They are slow; the style guide says to avoid them (`_shared/enscript-style.md`).
- `GetObjectByNetworkId(low, high)` finds an object from its two network ID halves (`:356`).

## Players

`GetPlayer()` is the player this machine controls, `GetPlayers(out array<Man>)` fills every player, and `GetPlayerByIndex(i)` wraps it (`P:\scripts\3_game\global\game.c:944` to `:952`). A dedicated server controls no player, so server code finds players with `GetPlayers` or from a `PlayerIdentity`. More in `api_player.md`.

## Reading config

Paths are class names separated by spaces, not dots: `"CfgSurfaces " + surface + " isDigable"` (`P:\scripts\3_game\global\game.c:1248`). The first word may also be `configFile` or `missionConfigFile` (`:445`).

| Call | Returns | Source |
|---|---|---|
| `ConfigGetText(path, out value)` | `bool` success, string in `value`. | `:449` |
| `ConfigGetTextOut(path)` | The string directly. | `:465` |
| `ConfigGetFloat(path)`, `ConfigGetInt(path)`, `ConfigGetVector(path)` | The value, or 0 when missing. | `:524`, `:539`, `:532` |
| `ConfigGetTextArray(path, out values)` | Fills a `TStringArray`. | `:558` |
| `ConfigIsExisting(path)` | Whether the entry exists. Check it before you trust a 0. | `:612` |
| `IsKindOf(className, parentName)` | Config inheritance test by name. | `:1436` |

An object builds its own path from `GetType()`, for example `"CfgVehicles " + GetType() + " "` (`P:\scripts\3_game\entities\object.c:424`).

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
