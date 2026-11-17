# `ScriptInputUserData`: the player input channel

Covers `ScriptInputUserData`, the channel that carries a player's own input to the server: the class, its guard, the vanilla write sites, the engine-driven receive chain, and when to use it instead of `ScriptRPC`.

Status: source reading of build `119356`. Checked on `P:\` on 2026-11-17: every cited line below was opened on `P:\scripts` and holds what the note says. Measured payload limits of this channel are in `script-network-limits.md`, `script-network-arrays.md` and `script-network-array-types.md`.

`ScriptRPC` is the general script-to-script call; it is not how vanilla moves a player's own input. For that, build `119356` has a dedicated input channel whose write end is `ScriptInputUserData`: the caller writes a packet, the engine carries it with the player's input, and script on the receiving side reads it back as a `ParamsReadContext`. This note maps that path only — the class, the guard that gates it, the vanilla write sites, and the engine-driven receive chain. For `ScriptRPC` itself (target object, `rpc_type`, recipient identity), see the `enforce-script-reference` skill (`references/networking.md`) and `skills/_shared/enscript/references/api_network.md`; nothing here replaces it.

All citations are the official scripts, revision `119356`, under `scripts/`. Paraphrase is the rule: only short signatures are quoted.

## The class

`class ScriptInputUserData : ParamsWriteContext` (`P:\scripts\3_game\gameplay.c:120`) is a native-backed write context. Its whole declared surface is a constructor and destructor (`:122-123`), `proto native void Reset()` (`:125`), `proto native void Send()` (`:126`), `proto native bool CopyFrom(ParamsReadContext other)` (`:128`), and `proto native static bool CanStoreInputUserData()` (`:131`). Because it extends `ParamsWriteContext`, payload is written with the inherited `Write(...)` calls in a fixed order and read back in the same order on the other side; the class itself adds no field, no addressing, and no delivery option.

Two consequences follow directly from those declarations, and both are stated here as readings of the signatures, not as measured engine behaviour:

- `Send()` takes no argument, so a packet names no destination: there is no target object, no recipient identity, and no message id to choose.
- Dispatch inside the packet is the payload's own first value. Vanilla writes an `INPUT_UDT_*` constant first (`P:\scripts\3_game\tools\component\_constants.c:2-20`), and the receiver reads that first `int` to route the packet (see below).

## The guard: `CanStoreInputUserData()`

The one-line source comment on `CanStoreInputUserData` states the contract: the static check returns true "when the channel is free, AND the InputBuffer is NOT full" (`P:\scripts\3_game\gameplay.c:130-131`). Vanilla treats a false answer as "do not start this input action now", not as an error: the predictive inventory entry points in `scripts/3_game/entities/man.c` abandon the action instead of writing: the boolean entry points `return false`, and the void entry points use a bare `return` (`:130`, `:180`, `:241`, `:383`, `:424`, `:474`, `:521`, `:578`, `:617`, `:660`, `:699`, `:740`); the weapon path returns false at `P:\scripts\4_world\classes\weapons\weaponmanager.c:792`; and the inventory defers the pending manipulation event, then runs all four deferred handlers (`HandleHandEvent`, `HandleTakeToDst`, `HandleSwapEntities`, `HandleForceSwapEntities`) and clears it only when the guard allows (`P:\scripts\4_world\systems\inventory\dayzplayerinventory.c:4626-4631`).

So the usable pattern is: check, then write, then send — in that order, every time. Writing first and checking later cannot work: the guard has to pass before the write. Reading of the declared surface, the only clear is `Reset()` (`P:\scripts\3_game\gameplay.c:125`), which empties the buffer for reuse; there is no separate cancel for a packet that was already sent.

## The write/send path in vanilla

The minimal shape appears wherever vanilla sends a one-off input packet: create the context, `Write(...)` the type constant and then the payload in order, and call the argument-less `Send()`. The mute notification writes its type, an id and a flag, then sends (`P:\scripts\3_game\client\onlineservices.c:381-385`); the weapon manager writes its action type, action and acknowledgement id, adds the per-action arguments, and sends at the end of the same method (`P:\scripts\4_world\classes\weapons\weaponmanager.c:525-571`); the bot spam test builds hand-event and move packets the same way and sends each one (`P:\scripts\4_world\systems\bot\bot_testspamuseractions.c:73-102`).

Inventory is the heavy user, and it shows the second shape: a packet built to be handed on, not sent in place. Hand events are serialised into a fresh `ScriptInputUserData` context at `P:\scripts\4_world\systems\inventory\dayzplayerinventory.c:1603-1604`, `:1665-1666`, `:1701-1702`, `:1759-1760` and `:1890-1891`, and the resulting context is then consumed by the juncture/validation flow of the same file; other sites build one to pass to `SendSyncJuncture(...)` (`:3786`, `:4257`) or to build a writable serializer via the constructor form at `:3381`, `:3469` and `:4465`. `CopyFrom(ParamsReadContext)` is what lets a read-side serializer be turned into one of these writable packets (`:3381-3383`, `:3469-3471`).

The first written value is the routing key: the inventory serializers write `INPUT_UDT_INVENTORY` before the command body (`P:\scripts\3_game\systems\inventory\inventoryinputuserdata.c:7`, `:72`, `:107`), exactly as the mute and weapon sites write their own constants first. A custom packet that omits that first `int`, or writes it in a different position, will not match the receiver's read.

## The receive path is engine-driven

No script registers for these packets; the engine delivers them. The documented origin, in the inventory's own header comment, is "engine - `DayZPlayer::OnInputUserDataReceived`" feeding "script - `DayZPlayerImplement.OnInputUserDataReceived`" (`P:\scripts\4_world\systems\inventory\dayzplayerinventory.c:699-704`). That script entry point reads the first `int` as the user-data type and passes the rest of the context on (`P:\scripts\4_world\entities\dayzplayerimplement.c:3040-3049`).

From there the inventory branch is three steps. `DayZPlayerInventory.OnInputUserDataProcess(ParamsReadContext)` stores the packet through the native `StoreInputUserData(ctx)` instead of handling it inline (`P:\scripts\4_world\systems\inventory\dayzplayerinventory.c:705-716`, `:758`). The later handling step, `OnHandleStoredInputUserData`, reads its leading value and, in the non-diagnostic path, runs the server inventory validation when `g_Game.IsServer()` holds — and calls `Error("OnHandleStoredInputUserData - Client")` otherwise (`:722-749`, the `Error` itself at `:748`). Packets addressed to a remote (non-owning) player take the sibling entry `OnInputUserDataForRemote(ParamsReadContext)`, which reaches the remote execution path (`:761-782`); the player routes the `INPUT_UDT_INVENTORY` case to it at `P:\scripts\4_world\entities\dayzplayerimplement.c:963-965`.

Because delivery is engine-driven, there is no script-side subscription to forget. The engine calls `DayZPlayerImplement.OnInputUserDataReceived` (`P:\scripts\4_world\entities\dayzplayerimplement.c:3040-3049`), which routes the packet; a mod can override that entry point, but it cannot replace the delivery. A mod that needs custom input behaviour hooks the handling/validation side, or sends its own packet and handles it in its own player code.

## The two sibling contexts

Two related classes sit directly below in the same file. `class ScriptRemoteInputUserData : ParamsWriteContext` adds a constructor, a destructor and `proto native void Reset()` — and nothing else: no `Send()`, no `CopyFrom`, no guard (`P:\scripts\3_game\gameplay.c:143-149`). `class ScriptJunctureData : ParamsWriteContext` has the same minimal shape (`P:\scripts\3_game\gameplay.c:151-157`). The declarations alone do not say where they are used, but the 119356 call sites do: `ScriptRemoteInputUserData` is created, written and handed to `StoreInputForRemotes` in `SyncHandEventToRemote` (`P:\scripts\4_world\systems\inventory\dayzplayerinventory.c:4375-4388`), and `ScriptJunctureData` is created and written in `scripts/4_world/entities/dayzplayersyncjunctures.c` (for example `:46`, `:67`, `:91`, `:101`, `:146`). This note maps the class surface and those examples; it does not assign the full delivery lifecycle of either path.

## `ScriptInputUserData` or `ScriptRPC`?

This distinction is an inference from the declarations and call sites above, labelled as such; it is not a statement the source makes in one place.

| Question | `ScriptInputUserData` | `ScriptRPC` |
|---|---|---|
| Destination chosen by caller | No — `Send()` has no argument | Yes — target, id and recipient are send arguments |
| Routing key | First payload `int` (`INPUT_UDT_*`) | The `rpc_type` argument |
| Receiver | The player input path (engine-delivered) | The target's `OnRPC` handler |
| Typical vanilla payload | Own-player input: actions, inventory, weapons | General script messages either direction |

Use the input channel when the message *is* player input — something the owning client originates and the server must validate as input. Use `ScriptRPC` for everything addressed: a specific object, a specific player, or a reply. The full `ScriptRPC` contract, including the server-to-client target rule, stays in the `enforce-script-reference` skill (`references/networking.md`) and `skills/_shared/enscript/references/api_network.md`.

## Gotchas

- Check `CanStoreInputUserData()` before writing, not before sending: vanilla checks at the decision point and abandons or defers the action on false.
- `Send()` takes no arguments. Any design that needs a target, a recipient or a message id is a `ScriptRPC` design, not this one.
- The receive path is engine-driven; do not wait for a registration call or an invoker that the scripts do not contain.
- `OnHandleStoredInputUserData` errors on a client (`.../dayzplayerinventory.c:748`): handling stored input is server work in this build's inventory path.
- Server-side validation remains the handler's responsibility. The channel delivers a client's packet; nothing in the class declarations validates its contents, and the vanilla inventory routes stored packets into its server validation for exactly that reason (`:742-745`).

## How to reproduce

From the root of the extracted build-`119356` script tree:

```text
grep -n "class ScriptInputUserData" scripts/3_game/gameplay.c
grep -n "CanStoreInputUserData" scripts/3_game/entities/man.c scripts/4_world/classes/weapons/weaponmanager.c
grep -n "OnInputUserDataProcess\|StoreInputUserData\|OnHandleStoredInputUserData\|OnInputUserDataForRemote" scripts/4_world/systems/inventory/dayzplayerinventory.c
grep -n "ScriptInputUserData" scripts/3_game/client/onlineservices.c scripts/4_world/systems/bot/bot_testspamuseractions.c
grep -n "ScriptRemoteInputUserData\|ScriptJunctureData" scripts/3_game/gameplay.c scripts/4_world/systems/inventory/dayzplayerinventory.c scripts/4_world/entities/dayzplayersyncjunctures.c
```

## Limits

- Build `119356` only; line numbers and the guard placement are this build's.
- Source reading, not an in-game test: no statement here claims measured runtime behaviour, delivery timing, or buffer sizes beyond the one-line source comment.
- The engine side (`DayZPlayer::OnInputUserDataReceived`, the native bodies of `Send`, `Reset`, `CopyFrom` and `StoreInputUserData`) is not in the script tree; its existence is documented by the script declarations and comments.
- No vanilla code is copied into this note beyond the short signatures quoted above; everything else is paraphrase with a `path:line` citation.
