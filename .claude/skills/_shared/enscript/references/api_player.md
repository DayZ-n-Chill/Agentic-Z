# Reference: players, identities and player state

Finding players, telling them apart, the connect hooks in `MissionServer`, and reading health and stats. Facts cite the vanilla file on `P:\scripts\` they were checked against (game storage version 144, `P:\scripts\3_game\global\game.c:5`). The older `player_api.md` lists more `PlayerBase` helpers that are not yet checked line by line.

## Classes

`PlayerBase extends ManBase` (`P:\scripts\4_world\entities\manbase\playerbase.c:49`) is the class every survivor uses; mod it with `modded class PlayerBase`. Engine calls give you `Man` or `DayZPlayer`, so cast: `PlayerBase player = PlayerBase.Cast(GetGame().GetPlayer());` (`P:\scripts\4_world\entities\itembase.c:663`).

## Finding players

| Call | Returns | Source |
|---|---|---|
| `GetGame().GetPlayer()` | The player this machine controls. A dedicated server controls none. | `P:\scripts\3_game\global\game.c:944` |
| `GetGame().GetPlayers(out array<Man> players)` | Every player. | `:945` |
| `GetGame().GetPlayerByIndex(i)` | One player from that list, or `null`. | `:946` to `:952` |
| `identity.GetPlayer()` | The player of a `PlayerIdentity`. | `P:\scripts\3_game\gameplay.c:374` |
| `player.GetIdentity()` | The player's `PlayerIdentity`. | `P:\scripts\3_game\entities\man.c:21` |

## `PlayerIdentity`

| Method | Value | Source (`3_game\gameplay.c`) |
|---|---|---|
| `GetId()` | Hashed unique ID. Vanilla says it "can be used in database or logs". | `:367` |
| `GetPlainId()` | Plain ID, such as the Steam ID. Vanilla says it "cannot be used in database or logs". | `:369` |
| `GetName()` / `GetPlainName()` / `GetFullName()` | Display names. | `:361`, `:363`, `:365` |
| `GetPlayerId()` | Session number, reused after the player leaves. Never store it. | `:371` |
| `GetPingAvg()` and the other ping and bandwidth calls | Connection stats. | `:341` to `:357` |

The engine owns identities (`P:\scripts\3_game\gameplay.c:382`): hold them without `ref` and null check them. `PlayerIdentity` is the moddable class (`:386`).

## Connect and disconnect hooks (server)

All on `MissionServer` in `P:\scripts\5_mission\mission\missionserver.c`. Mod it with `modded class MissionServer` and call `super`.

| Hook | When | Line |
|---|---|---|
| `OnClientNewEvent(identity, pos, ctx)` | A new character is created; returns the `PlayerBase`. | 549 |
| `OnClientReadyEvent(identity, player)` | The ready event for a character that already exists; selects it for the player. | 599 |
| `InvokeOnConnect(player, identity)` | Called after both of the above; calls `player.OnConnect()`. | 435, called at 336 and 357 |
| `OnClientRespawnEvent(identity, player)` | The player respawns. | 611 |
| `OnClientReconnectEvent(identity, player)` | The player reconnects to a living character. | 633 |
| `OnClientDisconnectedEvent(identity, player, logoutTime, authFailed)` | The player starts to leave. | 641 |
| `InvokeOnDisconnect(player)` | Calls `player.OnDisconnect()`. | 442 |
| `PlayerDisconnected(player, identity, uid)` | The player has gone. Vanilla warns the identity may already be deleted here, so use `uid`. | 690, 692 |

`PlayerBase.OnConnect()` and `OnDisconnect()` are the per player forms (`P:\scripts\4_world\entities\manbase\playerbase.c:7623`, `:7647`). `InvokeOnConnect` is the one place that runs for both new and loaded characters.

## Health

Health lives in zones and types. An empty zone means the global zone and an empty type means the main health (`P:\scripts\3_game\entities\object.c:989` to `:994`).

| Call | Source (`3_game\entities\object.c`) |
|---|---|
| `GetHealth(zone, type)`, `GetHealth01(zone, type)`, `GetMaxHealth(zone, type)` | `:994`, `:1001`, `:1008` |
| `SetHealth(zone, type, value)`, `AddHealth(...)`, `DecreaseHealth(...)` | `:1015`, `:1027`, `:1034` |
| `GetHealth()` and `SetHealth(value)` without zone | Same as `("", "")`. `:1062`, `:1077` |
| `IsAlive()` | `!IsDamageDestroyed()`. `:517` |

Players use the types `"Health"`, `"Blood"` and `"Shock"`: `m_Player.GetHealth("","Blood")` and `player.GetHealth("", "Shock")` (`P:\scripts\4_world\classes\debugmonitorvalues.c:140`, `P:\scripts\4_world\classes\playermodifiers\modifiers\diseases\heatstroke.c:369`). Change health only on the server.

## Stats

`PlayerBase` returns typed stats such as `GetStatWater()` and `GetStatEnergy()` (`P:\scripts\4_world\entities\manbase\playerbase.c:8197`, `:8215`). Each is a `PlayerStat<float>` with `Get()`, `Set(value)`, `Add(value)`, `GetMin()`, `GetMax()` and `GetNormalized()` (`P:\scripts\4_world\classes\playerstats\playerstatbase.c:32`, `:85`, `:129`, `:134`). Vanilla drains energy with `m_Player.GetStatEnergy().Add(-1 * ENERGY_DRAIN_FROM_VOMIT);` (`P:\scripts\4_world\classes\playermodifiers\modifiers\conditions\poisoning.c:88`).

## State checks

| Call | Source (`4_world\entities\manbase\playerbase.c`) |
|---|---|
| `IsUnconscious()` | `:3925` |
| `IsRestrained()` | `:2219` |
| `GetModifiersManager()` (diseases and conditions) | `:8192` |
| `GetHumanInventory().GetEntityInHands()` | `P:\scripts\3_game\systems\inventory\humaninventory.c:16` |

Check these on the server before acting on a client request (`_shared/conventions/scripts.md`, "What the server must validate").
