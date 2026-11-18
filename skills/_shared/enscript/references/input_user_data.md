# Reference: `ScriptInputUserData`, the player input channel

The channel that carries a player's own input to the server: the class, its guard, how vanilla writes and sends a packet, the engine driven receive path, and when to use it instead of `ScriptRPC`. Every line below was opened on `P:\scripts`. This is source reading; the measured payload sizes and queue depth are in `network_payload_limits.md`, and `ScriptRPC` itself is in `api_network.md`.

## The class

`class ScriptInputUserData : ParamsWriteContext` (`P:\scripts\3_game\gameplay.c:120`) declares only a constructor and destructor (`:122-123`), `proto native void Reset()` (`:125`), `proto native void Send()` (`:126`), `proto native bool CopyFrom(ParamsReadContext other)` (`:128`) and `proto native static bool CanStoreInputUserData()` (`:131`). The payload goes in with the inherited `Write(...)` calls and is read back in the same order.

- `Send()` takes no argument: a packet names no target object, no recipient and no message id.
- The routing key is the first value written. Vanilla writes an `INPUT_UDT_*` constant first (`P:\scripts\3_game\tools\component\_constants.c:2-20`), and the receiver reads that `int` to route the packet. A custom packet that leaves it out, or writes it later, does not match the receiver's read.
- `Reset()` empties the buffer for reuse. There is no cancel for a packet already sent.

## The guard: check, then write, then send

The source comment says `CanStoreInputUserData()` returns true "when the channel is free, AND the InputBuffer is NOT full" (`P:\scripts\3_game\gameplay.c:130-131`). Vanilla treats false as "do not start this action now", not as an error:

- The predictive inventory calls in `P:\scripts\3_game\entities\man.c` give up instead of writing (for example `:130`, `:180`, `:241`, `:383`).
- The weapon manager returns false (`P:\scripts\4_world\classes\weapons\weaponmanager.c:792`).
- The player inventory keeps the pending event and handles it only when the guard allows (`P:\scripts\4_world\systems\inventory\dayzplayerinventory.c:4626-4631`).

So check the guard at the decision point, before writing, every time. The return of each `Write` must be checked too: a full packet makes `Write` return false while the guard still said true (`network_payload_limits.md`).

## How vanilla sends

- One off packets: create the context, write the type constant, write the payload, call `Send()`. Examples: the mute notification (`P:\scripts\3_game\client\onlineservices.c:381-385`), the weapon manager (`P:\scripts\4_world\classes\weapons\weaponmanager.c:525-571`).
- Packets built to be handed on: the inventory serializes hand events into a fresh `ScriptInputUserData` (`P:\scripts\4_world\systems\inventory\dayzplayerinventory.c:1603-1604`) and passes others to `SendSyncJuncture(...)` (`:3786`, `:4257`). `CopyFrom` turns a read context into a writable packet (`:3381-3383`). The inventory serializers write `INPUT_UDT_INVENTORY` first (`P:\scripts\3_game\systems\inventory\inventoryinputuserdata.c:7`, `:72`, `:107`).

## The receive path is engine driven

No script registers for these packets. The engine calls `DayZPlayerImplement.OnInputUserDataReceived`, which reads the first `int` as the type and passes the rest on (`P:\scripts\4_world\entities\dayzplayerimplement.c:3040-3049`; the origin is named in the comment at `P:\scripts\4_world\systems\inventory\dayzplayerinventory.c:699-704`).

- The inventory branch stores the packet with the native `StoreInputUserData(ctx)` instead of handling it at once (`P:\scripts\4_world\systems\inventory\dayzplayerinventory.c:705-716`, `:758`).
- `OnHandleStoredInputUserData` runs the server inventory validation when `g_Game.IsServer()` holds and raises `Error(...)` on a client (`:722-749`, the error at `:748`). Handling stored input is server work.
- Packets for a remote, non-owning player go to `OnInputUserDataForRemote` (`:761-782`), routed from `P:\scripts\4_world\entities\dayzplayerimplement.c:963-965`.

A mod can override `OnInputUserDataReceived` to route its own type, but cannot replace the delivery. Nothing in the class validates the contents: the server handler must, as vanilla does with `ValidateInventoryCommandServer` (`P:\scripts\4_world\systems\inventory\dayzplayerinventory.c:742-745`).

## The two sibling contexts

`ScriptRemoteInputUserData` (`P:\scripts\3_game\gameplay.c:143-149`) and `ScriptJunctureData` (`:151-157`) are write contexts with only a constructor, a destructor and `Reset()`: no `Send()`, no guard. Vanilla fills the first and hands it to `StoreInputForRemotes` in `SyncHandEventToRemote` (`P:\scripts\4_world\systems\inventory\dayzplayerinventory.c:4375-4388`), and writes the second in `P:\scripts\4_world\entities\dayzplayersyncjunctures.c` (for example `:46`, `:67`).

## `ScriptInputUserData` or `ScriptRPC`

Inferred from the declarations and call sites above:

| Question | `ScriptInputUserData` | `ScriptRPC` |
|---|---|---|
| Caller picks the destination | No: `Send()` has no argument | Yes: target, id and recipient are arguments |
| Routing key | The first payload `int` | The `rpc_type` argument |
| Receiver | The player input path, engine delivered | The target's `OnRPC` |
| Vanilla use | Own player input: actions, inventory, weapons | Script messages in either direction |
| Size the receiver read (measured) | About 143 ASCII characters, 128 ints | 1,023 ASCII characters, 4,096 ints |

Use the input channel when the message is input the owning client starts and the server must validate as input. Use `ScriptRPC` for anything addressed: an object, a player or a reply.
