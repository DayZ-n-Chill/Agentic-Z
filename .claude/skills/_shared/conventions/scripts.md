# DayZ script conventions (Tier 2 topic)

Part of Tier 2. Enforce Script layout and the `modded class` rule; code style itself is in `.claude/skills/_shared/enscript-style.md`. Read it together with the core rules in `.claude/skills/_shared/dayz-conventions.md`, which still apply.

## Script conventions

- Enforce Script (DayZ's C#-like language), styled per `enscript-style.md`.
- Folder modules:
  - `scripts/3_Game/`: base game logic
  - `scripts/4_World/`: world-level logic
  - `scripts/5_Mission/`: mission classes for both sides, `MissionServer` on the server and `MissionGameplay` on the client (see below)
- Use `modded class Foo { ... }` for non-destructive overrides, with NO `extends` clause. Reported, not checked on `P:\` and not yet confirmed in Workbench (the compiler is native): `modded class Foo extends Foo` compiles but is a silent no-op, so the override never runs. The rule (no `extends`) holds either way; see `../enscript/patterns/modded_class.md`.

## Client and server ownership

The server is the authority. A client shows the world and asks for changes; the server decides. Each rule below names the vanilla file under `P:\scripts\` it was checked against.

### Which code runs where

- Test the side at run time with `GetGame().IsServer()`, `IsClient()`, `IsMultiplayer()` and `IsDedicatedServer()` (`3_game/global/game.c:1118-1125`). Vanilla notes that `IsDedicatedServer()` is valid much sooner during load than the others, and that `#ifdef SERVER` is the compile time form.
- In single player one process plays both sides. Write `if (GetGame().IsServer())` for authority work rather than testing for "not a client", and add `IsMultiplayer()` when code must only run on a remote client.
- `5_Mission` holds two missions: `MissionServer` runs on the server and `MissionGameplay` runs on the client (`5_mission/mission/missionserver.c:5`, `missiongameplay.c:1`). Server setup goes in `MissionServer`; HUD and input go in `MissionGameplay`.
- Actions split the same way. `ActionBase` calls `OnStartServer` or `OnStartClient` (`4_world/classes/useractionscomponent/actionbase.c:788-796`) and `AnimatedActionBase` calls `OnExecuteServer` or `OnExecuteClient` (`animatedactionbase.c:201-203` in the same folder), chosen by `IsServer()`. Put the effect in the server callback; the client callback is for feedback only.
- UI, widgets, sounds and particles are client only. Guard them with `!GetGame().IsDedicatedServer()`, or `#ifndef NO_GUI` for GUI types (see `../enscript/patterns/modded_class.md`).

### Who owns state

- Health, quantity, inventory, spawning and deleting belong to the server. Vanilla enforces it for quantity: `ItemBase.SetQuantity` returns false and logs "variables are supposed to be changed on server only" when a multiplayer client calls it (`4_world/entities/itembase.c:3315-3318` calls `EntityAI.IsServerCheck` in `3_game/entities/entityai.c:2753-2765`). The check is skipped when the caller passes `allow_client = true` (the fourth parameter, `itembase.c:3315`; `entityai.c:2758-2759`). Do not pass it for gameplay state.
- Move items on the server with the `Server*ToTarget*` inventory calls, such as `ServerTakeEntityToTargetInventory` (`3_game/entities/entityai.c:1983`) and `ServerTakeEntityToTargetAttachment` (`:2047`). The `Predictive*` calls are for a client acting on its own player, and `Local*` calls change only the local copy (`:1955-2050`). Avoid the older forms without `Target`: `ServerTakeEntityAsAttachment` carries `[Obsolete("1.30: Use ServerTakeEntityToTargetAttachment instead")]` (`:4906-4907`), and `ServerTakeEntityToInventory` has the same 1.30 note, though there it is commented out, so it does not warn yet (`:1967-1968`).
- Persistence runs on the server only. The engine calls `OnStoreSave` and `OnStoreLoad` there: they are declared at `3_game/entities/entityai.c:2910` and `:2978`, and their doc comments say "on server side" (`:2894`, `:2955`). Never read or write save data on a client.
- A client may create a local object with `ECE_LOCAL` (`3_game/ce/centraleconomy.c:25`) for previews and effects. Nothing local may change gameplay.

### Getting state to clients

- Use net sync for small values every nearby client needs. Register with `RegisterNetSyncVariable*` in the constructor, change the value on the server, then call `SetSynchDirty()`, which only takes effect on the server in multiplayer. Clients react in `OnVariablesSynchronized()` (`3_game/entities/entityai.c:2832-2850`, `:3063-3069`). Pattern: `../enscript/patterns/netsync.md`.
- Use an RPC for one off events and for data only one player needs.

### RPC direction

- `ScriptRPC.Send` and `GetGame().RPCSingleParam` go to the server when called on a client, and to clients when called on the server (`3_game/gameplay.c:111-117`, `3_game/global/game.c:970-974`, `:1013`). On the server a `null` recipient means every client; pass one player's `PlayerIdentity` to reach only that player.
- Server to client is the normal direction. Client to server is a request, never a command.
- Split handlers by side. Vanilla wraps client only cases in `#ifndef SERVER` inside `PlayerBase.OnRPC` (`4_world/entities/manbase/playerbase.c:5727-5733`). In your own handler, cases only the server may handle start with `if (!GetGame().IsServer()) break;`.
- IDs, payload layout and the handler template are in `../enscript/patterns/rpc.md`.

### What the server must validate

Every client to server RPC is untrusted input. Before acting on one, the server checks:

1. The sender. Take the identity from the `sender` parameter of `OnRPC` (`3_game/entities/object.c:860`), as vanilla does when the code lock checks a dialed code against `sender` (`4_world/classes/codelockcomponent.c:556-567`, handled at `:350-354` on the server) and when mute permissions are keyed on `sender.GetPlainId()` (`3_game/dayzgame.c:3347`). Find the player from it, and never trust a player or identity sent inside the payload. That the engine fills `sender` itself and a client cannot forge it is unverified: vanilla scripts do not state it.
2. The player is alive, conscious, not restrained, and allowed to do this.
3. The target exists, is not ruined, and is within reach of that player.
4. Every value is in range. Clamp counts, amounts and indexes; reject unknown enum values and classnames that are not on an allow list.
5. The rate. Ignore repeats faster than a person could act.
6. The result. The server works out the outcome itself and never applies a health, quantity or price the client sent.

The action system already re-runs the action's `Can` check, including `ActionCondition`, on the server (`4_world/classes/useractionscomponent/actionmanagerserver.c:168`, which calls the three-argument `ActionBase.Can` at `actionbase.c:968-973`; that overload computes the condition mask and forwards to the four-argument `Can` at `:929-966`, which runs `ActionCondition` at `:954`). Keep that check the same on both sides (see `../enscript/patterns/actions.md`).
