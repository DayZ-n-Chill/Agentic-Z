# Reference: RPCs, `ScriptRPC` and net sync

The calls that move data between server and clients. Facts cite the vanilla file on `P:\scripts\` they were checked against (game storage version 144, `P:\scripts\3_game\global\game.c:5`). ID ranges, the handler template and validation rules are in `patterns/rpc.md`, `patterns/netsync.md` and `_shared/conventions/scripts.md`.

## Choosing

- Net sync: small state that every nearby client must see, such as a bool, a state number or a quantity. The engine sends it when the object is dirty.
- RPC: one off events, or data only one player needs.

## Sending an RPC

| Call | Use | Source |
|---|---|---|
| `GetGame().RPCSingleParam(target, id, param, guaranteed, recipient = null)` | One `Param` value. | `P:\scripts\3_game\global\game.c:1013` |
| `GetGame().RPC(target, id, params, guaranteed, recipient = null)` | An `array<ref Param>`. | `:1011` |
| `obj.RPCSingleParam(id, param, guaranteed, recipient)` / `obj.RPC(...)` | The same with `obj` as the target. | `P:\scripts\3_game\entities\object.c:850`, `:844` |
| `ScriptRPC rpc = new ScriptRPC(); rpc.Write(x); rpc.Send(target, id, guaranteed, recipient);` | Several values of any type. | `P:\scripts\3_game\gameplay.c:104`, `:117` |

Direction and recipient (`P:\scripts\3_game\gameplay.c:111` to `:116`):

- Called on a client, the RPC goes to the server.
- Called on the server, it goes to every client when `recipient` is `null`, or only to that `PlayerIdentity`. Vanilla notes that naming a recipient "increase[s] security and decrease[s] network traffic".
- `target` is the object the RPC is for. `null` makes it a global RPC handled by the game.
- `guaranteed = true` for anything that must arrive; `false` only for frequent updates where a lost packet does not matter.
- `ScriptRPC.Send` does not clear the buffer, so a second `Send` repeats the same data; call `Reset()` to reuse it (`gameplay.c:109`, `:112`).

Vanilla's own example writes an `int`, a `string` and an `array<float>` in order and reads them back in the same order (`P:\scripts\3_game\gameplay.c:18` to `:45`).

## Receiving an RPC

| Target | Handler | Source |
|---|---|---|
| An object | `override void OnRPC(PlayerIdentity sender, int rpc_type, ParamsReadContext ctx)` on its class. Call `super.OnRPC` first. | `P:\scripts\3_game\entities\object.c:860`, `P:\scripts\3_game\entities\entityai.c:3507` to `:3509` |
| `null` (global) | `DayZGame.OnRPC(sender, target, rpc_type, ctx)`, or subscribe to `DayZGame.Event_OnRPC`. | `P:\scripts\3_game\dayzgame.c:3141`, `:991` |

`DayZGame.OnRPC` invokes `Event_OnRPC` for every RPC, then calls `target.OnRPC` when there is a target (`P:\scripts\3_game\dayzgame.c:3143` to `:3151`). A mod that listens on `Event_OnRPC` sees every RPC in the game, so filter by ID first.

Read in the order you wrote. Each `ctx.Read(value)` returns `bool`; stop when it returns `false` (`P:\scripts\1_core\proto\serializer.c:58`). A value sent with `RPCSingleParam` is read back as the same `Param` type:

```c
Param1<bool> p_skinned_state = new Param1<bool>(false);
if (ctx.Read(p_skinned_state))
{
	float state = p_skinned_state.param1;
}
```

Source: `P:\scripts\3_game\entities\entityai.c:3518` to `:3521`. `ParamsReadContext` and `ParamsWriteContext` are both `Serializer` (`P:\scripts\3_game\gameplay.c:15`, `:16`); it handles primitives, arrays, sets, maps, static arrays and classes (`P:\scripts\1_core\proto\serializer.c:3` to `:7`).

`sender` is the identity the engine attached to the message. On the server, trust it and nothing in the payload that claims to be a player (`_shared/conventions/scripts.md`).

## Net sync

Register fields in the constructor of an `EntityAI` child, as `EntityAI` itself does (`P:\scripts\3_game\entities\entityai.c:208`, `:218` to `:229`).

| Call | Behaviour | Source (`3_game\entities\entityai.c`) |
|---|---|---|
| `RegisterNetSyncVariableBool("m_Field")` | Syncs a bool. | `:2832` |
| `RegisterNetSyncVariableBoolSignal("m_Field")` | When true it is sent to clients and becomes false again. | `:2840` |
| `RegisterNetSyncVariableInt("m_Field", min, max)` | Syncs an int, quantised to the range. With `min == max` (the default 0, 0) there is no quantisation. | `:2850` |
| `RegisterNetSyncVariableFloat("m_Field", min, max, precision)` | Syncs a float with `precision` digits after the point. | `:2861` |
| `RegisterNetSyncVariableObject("m_Field")` | Syncs an object reference, only once it has a network ID; it does not handle the object despawning on the client. | `:2869` |
| `SetSynchDirty()` | Marks the object for sending. Takes effect only on a multiplayer server. | `:3063` to `:3064` |
| `OnVariablesSynchronized()` | Called on clients after new values arrive. Override, call `super`, then update visuals. | `:3066` to `:3069` |

The name is the field name as a string, and may reach into a member object: `RegisterNetSyncVariableBool("m_EM.m_IsSwichedOn")` (`:218`). Pass ranges that cover every value: vanilla registers temperature with `GetTemperatureMin()` and `GetTemperatureMax()` (`:261`) and wetness with precision 2 (`P:\scripts\4_world\entities\itembase.c:190`).

Flow: the server changes the field, calls `SetSynchDirty()`, and each client gets `OnVariablesSynchronized()`. Never set a synced field on a client to change game state; only the server's value counts.
