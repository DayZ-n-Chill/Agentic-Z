# Reference: players, identities and player state

Finding players, telling them apart, the connect hooks in `MissionServer`, and reading health and stats. Facts cite the vanilla file on `P:\scripts\` they were checked against (game storage version 144, `P:\scripts\3_game\global\game.c:5`).

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

To show a player a short line of text, call `player.MessageStatus(text)` (`P:\scripts\4_world\entities\manbase\playerbase.c:6924`), not `GetGame().Chat()`: it does not depend on a chat mod.

## `PlayerIdentity`

| Method | Value | Source (`3_game\gameplay.c`) |
|---|---|---|
| `GetId()` | Hashed unique ID. Vanilla says it "can be used in database or logs". | `:367` |
| `GetPlainId()` | Plain ID, such as the Steam ID. Vanilla says it "cannot be used in database or logs". | `:369` |
| `GetName()` / `GetPlainName()` / `GetFullName()` | Display names. | `:361`, `:363`, `:365` |
| `GetPlayerId()` | Session number, reused after the player leaves. Never store it. | `:371` |
| `GetPingAvg()` and the other ping and bandwidth calls | Connection stats. | `:341` to `:357` |

The engine owns identities (`P:\scripts\3_game\gameplay.c:382`): hold them without `ref` and null check them. `PlayerIdentity` is the moddable class (`:387` to `:388`).

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

### Asking for a respawn from script

`GetGame().RespawnPlayer()` (`P:\scripts\3_game\global\game.c:1107`) sends the request, and the server's `OnClientRespawnEvent` kills the character only when it is unconscious or restrained (`player.IsUnconscious() || player.IsRestrained()`, `P:\scripts\5_mission\mission\missionserver.c:615`). For a living, conscious, unrestrained player nothing happens on the server. The vanilla menu's `GameRespawn` calls `RespawnPlayer()` and then runs the death screen on the client without waiting for an answer (`P:\scripts\5_mission\gui\ingamemenu.c:345` to `:348`), so copying it for a living player reports success while nothing changed (measured in game with a 1.30 diag build). Before the call, refuse on the client when the player exists, `IsAlive()`, is not unconscious and is not restrained; to give a living player a new body, kill it first. Detail: `skills/_shared/enscript/depth/api-patterns.md`.

### Seated players

`GetCommand_Vehicle()` returns a command that exists only on the machine that started it. The get in action creates it with `StartCommand_Vehicle` (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetintransport.c:104`); nothing creates it from the replicated crew list. A player that server script put in a seat is in the crew on the client, yet `GetCommand_Vehicle()` is `null` there, so any client check written as "is seated" fails (measured in game with a scripted helicopter mod, not checked on `P:\`). The other vehicle traps are in `skills/_shared/enscript/depth/vehicle-scripting.md`.

To move a seated player from server script, move the vehicle: `GetCommand_Vehicle()` (`P:\scripts\3_game\human.c:1528`) gives the `HumanCommandVehicle`, its `GetTransport()` (`P:\scripts\3_game\human.c:716`) the vehicle, and `GetTransform` and `SetTransform` on the vehicle carry the occupant along. Reported, not checked on `P:\`: the occupant's own position lags one frame, so read the vehicle's `GetPosition()` when you report where it went. A player on foot moves with `SetPosition(pos)`.

## Health

Health lives in zones and types. An empty zone means the global zone and an empty type means the main health (`P:\scripts\3_game\entities\object.c:989` to `:994`).

| Call | Source (`3_game\entities\object.c`) |
|---|---|
| `GetHealth(zone, type)`, `GetHealth01(zone, type)`, `GetMaxHealth(zone, type)` | `:994`, `:1001`, `:1008` |
| `SetHealth(zone, type, value)`, `AddHealth(...)`, `DecreaseHealth(...)` | `:1015`, `:1027`, `:1034` |
| `GetHealth()` and `SetHealth(value)` without zone | Same as `("", "")`. `:1062`, `:1077` |
| `IsAlive()` | `!IsDamageDestroyed()`. `:517` |

Players use the types `"Health"`, `"Blood"` and `"Shock"`: `m_Player.GetHealth("","Blood")` and `player.GetHealth("", "Shock")` (`P:\scripts\4_world\classes\debugmonitorvalues.c:140`, `P:\scripts\4_world\classes\playermodifiers\modifiers\diseases\heatstroke.c:376`). Change health only on the server.

## Stats

`PlayerBase` returns typed stats such as `GetStatWater()` and `GetStatEnergy()` (`P:\scripts\4_world\entities\manbase\playerbase.c:8197`, `:8215`). Each is a `PlayerStat<float>` with `Get()`, `Set(value)`, `Add(value)`, `GetMin()`, `GetMax()` and `GetNormalized()` (`P:\scripts\4_world\classes\playerstats\playerstatbase.c:32`, `:85`, `:129`, `:134`). Vanilla drains energy with `m_Player.GetStatEnergy().Add(-1 * ENERGY_DRAIN_FROM_VOMIT);` (`P:\scripts\4_world\classes\playermodifiers\modifiers\conditions\poisoning.c:88`).

Three limits on adding your own player state, all read on `P:\`:

- **A custom stat needs an index above 11.** `PlayerStatsPCO` registers stats by position. 1.30 added `THERMAL_BIAS` as index 11 of `EPlayerStats_v130` (`P:\scripts\4_world\classes\playerstats\playerstatspco.c:312-326`; `EPlayerStats_current` extends it at `:356`), so a stat a 1.29 mod placed at 11 now collides with it and corrupts the saved stats.
- **Synced modifier IDs are bits, and nine are taken.** `eModifierSyncIDs` uses `0x1` to `0x100` (`P:\scripts\4_world\classes\playermodifiers\modifiersmanager.c:2-12`; at most 32 synced modifiers), so a custom synced modifier takes a bit from `0x200` up. The modifier list itself is filled in `ModifiersManager.Init()` (`P:\scripts\4_world\classes\playermodifiers\modifiersmanager.c:90`); add yours from a `modded class ModifiersManager`.
- **Stamina does not sync through `SetSynchDirty`.** The server sends it with a sync juncture, `SJ_STAMINA`, in `SyncStamina` (`P:\scripts\4_world\classes\staminahandler.c:831-839`). For a custom stamina cost call `DepleteStaminaEx` with an `EStaminaModifiers` value (`P:\scripts\4_world\classes\staminahandler.c:1144`); `PUSH_CAR` already exists (`P:\scripts\3_game\enums\estaminamodifiers.c:13`).

## State checks

| Call | Source (`4_world\entities\manbase\playerbase.c`) |
|---|---|
| `IsUnconscious()` | `:3925` |
| `IsRestrained()` | `:2219` |
| `GetModifiersManager()` (diseases and conditions) | `:8192` |
| `GetHumanInventory().GetEntityInHands()` | `P:\scripts\3_game\systems\inventory\humaninventory.c:16` |

Check these on the server before acting on a client request (`_shared/conventions/scripts.md`, "What the server must validate").
