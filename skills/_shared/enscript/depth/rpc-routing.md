# RPC routing

How a `ScriptRPC` is sent and where it lands, why a server reply must target the player entity, what the server checks before acting, and how to read `Event_OnRPC` without eating another handler's data. One-ID dispatch and Community Framework are in `rpc-manager-and-cf.md`; synced variables in `networking.md`.

## Sending

`ScriptRPC.Send(Object target, int rpc_type, bool guaranteed, PlayerIdentity recipient = NULL)` (`P:\scripts\3_game\gameplay.c:104` to `:117`). From a client it goes to the server. From the server with a null recipient it goes to every client. A null target makes it a global RPC handled by the game, not an entity. `Send` does not clear the buffer: calling it again resends the same data until `Reset()`. A `ScriptRPC` needs no `delete` after sending.

```c
void MyMod_SendRequest(int data1, string data2)
{
    ScriptRPC rpc = new ScriptRPC();
    rpc.Write(data1);
    rpc.Write(data2);
    rpc.Send(m_Device, MYMOD_RPC_REQUEST, true, null);   // client to server
}
```

Use `guaranteed = true` for state that matters and false for cosmetic updates.

## A server reply targets the player

When replies are dispatched through `OnRPC` of a `modded class PlayerBase`, a reply reaches that handler only if its target is the player entity. Any other target is dropped on the client with no error, the usual cause of "the menu never opens and the log is clean".

| Target | Recipient | On the client |
|---|---|---|
| `player` | `sender` | `player.OnRPC` fires. Use this for every reply |
| A device entity | `sender` | The device's `OnRPC` fires; only when the receiver lives on the device |
| `null` | `sender` | `PlayerBase.OnRPC` never fires: `DayZGame.OnRPC` calls `target.OnRPC` only when a target is set, and a null target reaches only `Event_OnRPC` and the game's own `switch` (`P:\scripts\3_game\dayzgame.c:3144` to `:3155`) |
| `null` | `null` | A broadcast with no handler. Avoid |

A dispatcher usually hands the server handler `(PlayerBase player, PlayerIdentity sender, ...)`; pass that `player` as the reply's target:

```c
rpc.Send(player, MYMOD_RPC_CHANNEL, true, sender);
```

The target picks the handler and the recipient filters who receives the packet. Seen in a third-party ATM mod: a reply sent with `rpc.Send(null, CHANNEL, true, sender)` never opened the menu, while its sibling handlers sent with `player` as target worked.

## Receiving

An entity receives `OnRPC(PlayerIdentity sender, int rpc_type, ParamsReadContext ctx)` (`P:\scripts\3_game\entities\object.c:860`, overridden in `P:\scripts\3_game\entities\entityai.c:3507`). The game receives the four-argument form with `Object target` (`dayzgame.c:3141`) and forwards to the target when one is set. Read values in exactly the order they were written, and return on any failed read:

```c
override void OnRPC(PlayerIdentity sender, int rpc_type, ParamsReadContext ctx)
{
    super.OnRPC(sender, rpc_type, ctx);
    if (rpc_type != MYMOD_RPC_REQUEST)
        return;
    #ifdef SERVER
    int data1;
    string data2;
    if (!sender || !ctx.Read(data1) || !ctx.Read(data2))
        return;
    MyMod_HandleRequest(sender, data1, data2);
    #endif
}
```

## What the server checks

In this order, before acting on a request:

1. Return unless this is the server.
2. Return on a null sender.
3. Find the acting `PlayerBase` from the sender's identity, never from a value in the payload.
4. Return if that player is dead.
5. Before spawning a class name a client sent, check it with `g_Game.IsKindOf(name, "Inventory_Base")` or a narrower parent. It looks the class up in `CfgVehicles`, then `CfgAmmo`, `CfgMagazines`, `cfgWeapons` and `CfgNonAIVehicles`, and walks the parents of the first match (`P:\scripts\3_game\global\game.c:1436` to `:1459`).
6. Check the distance between the player and the target.
7. Apply a per player cooldown.

Compare identities by their stable ID, never by `PlayerIdentity` instance. Read `GetId()` on both sides and compare the strings; an instance comparison such as `sender != GetIdentity()` on the receiver, or `GetIdentity() == stored identity` in a player lookup, rejects a valid sender. When several ways of sending fail the same way while a probe shows the RPC arriving, check the shared guards and player lookup before changing transport (measured in game).

Find targets by network ID, not by a mod-made device ID or a cached reference:

```c
int netLow, netHigh;
m_Device.GetNetworkID(netLow, netHigh);
EntityAI entity = EntityAI.Cast(GetGame().GetObjectByNetworkId(netLow, netHigh));
if (!entity)
    return;   // gone
```

## RPC IDs

Keep each mod's IDs in its own block of constants, for example 20100 to 20199, and use fixed high literals. Never derive an ID from `ERPCs.RPC_END`: the enum holds a block of entries under `#ifdef DIAG_DEVELOPER` (`P:\scripts\3_game\enums\erpcs.c:121` to `:223`) before `RPC_END` (`:225`), so its value differs between diag and retail. A diag client with a retail server then sends an RPC nobody handles, with no error, because the `switch` in `DayZGame.OnRPC` has no `default:`. Vanilla writes constants as `const int`, hex included (`P:\scripts\1_core\constants.c:35`, `:63` to `:72`).

## Reading `Event_OnRPC` safely

`DayZGame.Event_OnRPC` (`P:\scripts\3_game\dayzgame.c:991`) fires for every RPC type on both processes: it is invoked at `:3144`, before the `if (target)` at `:3148` and outside the `#ifndef SERVER` and `#ifndef NO_GUI` that guard vanilla's `switch` (`:3157` and `:3158`). `ParamsReadContext` is a `Serializer` (`P:\scripts\3_game\gameplay.c:15`), and a read consumes the stream even when the type is wrong, with no rewind (`P:\scripts\1_core\proto\serializer.c:55` to `:65`). Measured in game: a `Param1<int>` read over a `Param1<T>` payload of another type returned true (value 3), and the correct read after it returned false.

So a subscriber that reads before checking its own `rpc_type` eats another handler's data, and the symptom shows elsewhere: cfggameplay never arrives, stamina or lighting glitches. Filter the type and the side before the first read, as vanilla does (`P:\scripts\3_game\syncevents.c:13`):

```c
if (rpc_type != MYMOD_RPC_ID)
    return;
if (GetGame().IsDedicatedServer())
    return;   // client-only handler; invert for a server-only one
Param1<string> payload = new Param1<string>("");
if (!ctx.Read(payload))
    return;
```

Vanilla's `UndergroundAreaLoader.OnRPC` reads without filtering only because it is called from a `case ERPCs.RPC_UNDERGROUND_SYNC:` that already filtered (`dayzgame.c:3169` to `:3172`). When several subscribers read in the wrong order, load order decides which one breaks.

`Event_OnRPC` is `static`, so subscribe by class name without `modded class DayZGame`, the way vanilla reads `DayZGame.MISSION_STATE_GAME` (`P:\scripts\4_world\entities\dayzplayerimplement.c:846`); that avoids clashing with another mod's `OnRPC`. Subscribe early. Vanilla's `SyncEvents.RegisterEvents()` runs in the `MissionGameplay` constructor (`P:\scripts\5_mission\mission\missiongameplay.c:82`), client side and late, which works only because its RPCs come at `ClientNew`. Anything the server sends during `ClientPrepare` (`P:\scripts\5_mission\mission\missionserver.c:317` to `:324`) arrives before that mission exists and is lost.
