# Player input packets: `ScriptInputUserData`

How a player's own input reaches the server: the class, its guard, how vanilla writes and sends a packet, the receive path the engine drives, and when to use it instead of `ScriptRPC`. The measured payload sizes and queue depth are in `network_payload_limits.md`; `ScriptRPC` itself is in `api_network.md`.

## The class

`class ScriptInputUserData : ParamsWriteContext` (`P:\scripts\3_game\gameplay.c:120`) declares only:

| Member | Line |
|---|---|
| Constructor and destructor | `:122` and `:123` |
| `proto native void Reset()` | `:125` |
| `proto native void Send()` | `:126` |
| `proto native bool CopyFrom(ParamsReadContext other)` | `:128` |
| `proto native static bool CanStoreInputUserData()` | `:131` |

The payload goes in with the inherited `Write(...)` calls and is read back in the same order.

- `Send()` takes no argument: a packet names no target object, no recipient and no message id.
- The first value written is the routing key. Vanilla writes an `INPUT_UDT_*` constant first (`P:\scripts\3_game\tools\component\_constants.c:2` to `:20`), and the receiver reads that `int` to route the packet. A custom packet that leaves it out, or writes it later, doesn't match the receiver's read.
- `Reset()` empties the buffer for reuse. A packet already sent can't be cancelled.

## Check the guard, then write, then send

The vanilla comment says `CanStoreInputUserData()` returns true "when the channel is free, AND the InputBuffer is NOT full" (`P:\scripts\3_game\gameplay.c:130` and `:131`). Vanilla treats false as "don't start this action now", not as an error:

- The predictive inventory calls in `P:\scripts\3_game\entities\man.c` give up instead of writing (for example `:130`, `:180`, `:241`, `:383`).
- The weapon manager returns false (`P:\scripts\4_world\classes\weapons\weaponmanager.c:792`).
- The player inventory keeps the pending event and handles it only once the guard allows (`P:\scripts\4_world\systems\inventory\dayzplayerinventory.c:4626` to `:4631`).

Check the guard at the decision point, before writing, every time. Check the return of each `Write` too: a full packet makes `Write` return false while the guard still said true (`network_payload_limits.md`).

## How vanilla sends

- A one off packet: create the context, write the type constant, write the payload, call `Send()`. Examples are the mute notification (`P:\scripts\3_game\client\onlineservices.c:381` to `:385`) and the weapon manager (`P:\scripts\4_world\classes\weapons\weaponmanager.c:525` to `:571`).
- A packet built to be handed on: the inventory serializes hand events into a fresh `ScriptInputUserData` (`P:\scripts\4_world\systems\inventory\dayzplayerinventory.c:1603` and `:1604`) and passes others to `SendSyncJuncture(...)` (`:3786`, `:4257`). `CopyFrom` turns a read context into a writable packet (`:3381` to `:3383`). The inventory serializers write `INPUT_UDT_INVENTORY` first (`P:\scripts\3_game\systems\inventory\inventoryinputuserdata.c:7`, `:72`, `:107`).

## The engine drives the receive side

No script registers for these packets. The engine calls `DayZPlayerImplement.OnInputUserDataReceived`, which reads the first `int` as the type and passes the rest on (`P:\scripts\4_world\entities\dayzplayerimplement.c:3040` to `:3049`; the comment at `P:\scripts\4_world\systems\inventory\dayzplayerinventory.c:699` to `:704` names where it comes from).

- The inventory branch stores the packet with the native `StoreInputUserData(ctx)` instead of handling it at once (`dayzplayerinventory.c:705` to `:716`, `:758`).
- `OnHandleStoredInputUserData` runs the server inventory checks when `g_Game.IsServer()` holds and raises `Error(...)` on a client (`:722` to `:749`; the error at `:748`). Handling stored input is server work.
- Packets for a remote player that the client doesn't own go to `OnInputUserDataForRemote` (`:761` to `:782`), routed from `P:\scripts\4_world\entities\dayzplayerimplement.c:963` to `:965`.

A mod can override `OnInputUserDataReceived` to route its own type, but can't replace the delivery. Nothing in the class checks the contents, so the server handler must, as vanilla does with `ValidateInventoryCommandServer` (`dayzplayerinventory.c:742` to `:745`).

## The two sibling contexts

`ScriptRemoteInputUserData` (`P:\scripts\3_game\gameplay.c:143` to `:149`) and `ScriptJunctureData` (`:151` to `:157`) are write contexts with only a constructor, a destructor and `Reset()`: no `Send()` and no guard. Vanilla fills the first and hands it to `StoreInputForRemotes` in `SyncHandEventToRemote` (`P:\scripts\4_world\systems\inventory\dayzplayerinventory.c:4375` to `:4388`), and writes the second in `P:\scripts\4_world\entities\dayzplayersyncjunctures.c` (for example `:46`, `:67`).

## `ScriptInputUserData` or `ScriptRPC`

Worked out from the declarations and call sites above:

| Question | `ScriptInputUserData` | `ScriptRPC` |
|---|---|---|
| Caller picks the destination | No: `Send()` has no argument | Yes: target, id and recipient are arguments |
| Routing key | The first payload `int` | The `rpc_type` argument |
| Receiver | The player input path, delivered by the engine | The target's `OnRPC` |
| Vanilla use | The player's own input: actions, inventory, weapons | Script messages in either direction |
| Size the receiver could read (measured in game) | About 143 ASCII characters, 128 ints | 1,023 ASCII characters, 4,096 ints |

Use the input channel for input the owning client starts and the server must check as input. Use `ScriptRPC` for anything addressed: an object, a player or a reply.
