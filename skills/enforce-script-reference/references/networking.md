# Networking and persistence

Synced variables, `ScriptRPC`, the game level `Event_OnRPC` bus, what replicates without custom sync, `OnStoreSave` and `OnStoreLoad`, side checks during load, and file I/O. Examples use names from the LFPowerGrid mod (LFPG). A line cited as `P:\...:N` was opened on `P:\`; measured results name the mod and build that measured them and were not re-run here. The short checked patterns are in `skills/_shared/enscript/patterns/` (`netsync.md`, `rpc.md`, `persistence.md`).

## Architecture overview

DayZ uses a client and server model, and the server has authority. The mechanisms:

1. **Synced variables**: automatic variable synchronization from the server to clients
2. **`ScriptRPC`**: manual remote procedure calls, in both directions
3. **Persistence**: `OnStoreSave` and `OnStoreLoad`, so state survives a server restart

4. **Inventory commands (1.30)**: not synced variables. Retail `DayZPlayerInventory` no longer runs `ProcessInputData` (the method is still at `P:\scripts\4_world\systems\inventory\dayzplayerinventory.c:3319`; its call sites are inside `#ifdef DIAG_DEVELOPER` and need `IsOldProcessInputDataEnable()`, `:668-687` and `:734-744`). The live path: `ValidateInventoryCommandServer` (`:3410`), `ExecuteInventoryCommandServer` (`:3501`), `ExecuteInventoryCommandClient` (`:3569`), `ExecuteInventoryCommandRemote` (`:3633`). Desync repair: `INPUT_UDT_INVENTORY_CHECK = 16` (`P:\scripts\3_game\tools\component\_constants.c:19`), `OnInventoryCheck` (`P:\scripts\4_world\systems\inventory\dayzplayerinventory.c:5003`), capped at `INVENTORY_REPAIR_MAX_ITEMS` = 5 items and `INVENTORY_REPAIR_MAX_DISTANCE` = 500 m (`P:\scripts\4_world\systems\inventory\dayzplayerinventory.c:163-164`). Hand state machine: the 1.30 guards pass automatically only for `e.m_IsRemote` (1.29 passed `m_IsJuncture || m_IsRemote`), and `HandGuardIsNotSurrendered` is new (`P:\scripts\3_game\systems\inventory\hand_guards.c:405`). The bodies are in `dayz-1-30-enforce-script.md`.

---

## Synced variables (`RegisterNetSyncVariable*`)

Synced variables replicate member field changes from the server to all clients.

### Registration: in the constructor

```
class LF_MyDevice extends ItemBase
{
    // Declare the synced field
    bool m_PoweredNet;
    int m_LoadPercent;
    float m_Temperature;

    void LF_MyDevice()
    {
        // Register in constructor — NOT in EEInit, NOT anywhere else
        string varPowered = "m_PoweredNet";
        RegisterNetSyncVariableBool(varPowered);

        string varLoad = "m_LoadPercent";
        RegisterNetSyncVariableInt(varLoad, 0, 100);  // min, max for compression

        string varTemp = "m_Temperature";
        RegisterNetSyncVariableFloat(varTemp, 0.0, 200.0, 2);  // min, max, digits after the decimal point
    }
}
```

**Registration variants:**
- `RegisterNetSyncVariableBool(string varName)` — 1 bit
- `RegisterNetSyncVariableInt(string varName, int min, int max)` — compressed int
- [EXACT][CLAIM-NETSYNC-FLOAT-DIGITS] `RegisterNetSyncVariableFloat(string varName, float min = 0, float max = 0, int precision = 1)` — compressed float. `precision` is the number of digits kept after the decimal point, not a bit count; `min == max` turns quantization off (`P:\scripts\3_game\entities\entityai.c:2853-2861`). Vanilla passes `2` for the effect-area radius and heights (`P:\scripts\4_world\classes\contaminatedarea\effectarea.c:99-101`) and `5` for an animation phase in 0..1 (`P:\scripts\4_world\entities\building\underground\entrance\land_underground_entrance.c:76`).

### Writing synced variables: server only

```
void SetPowered(bool state)
{
    #ifdef SERVER
    m_PoweredNet = state;
    SetSynchDirty();  // Marks entity for sync on next network tick
    #endif
}
```

Always guard the write with `#ifdef SERVER` and call `SetSynchDirty()`. Without `SetSynchDirty`, clients never see the change. (For code that must also run in single player, where `SERVER` is not defined, guard with `GetGame().IsServer()` instead.)

### Reading synced variables: the client callback

```
override void OnVariablesSynchronized()
{
    super.OnVariablesSynchronized();

    // m_PoweredNet is now updated on client
    // React to state change (visual updates, sounds, etc.)
    if (m_PoweredNet)
    {
        // Turn on lights, play sound, swap rvmat
    }
    else
    {
        // Turn off lights, stop sound
    }
}
```

`OnVariablesSynchronized` fires on the client when any registered variable changes. You cannot tell which one changed, so check every field you care about.

---

## `ScriptRPC`: manual remote calls

For complex data, or for client to server communication, use `ScriptRPC`.

### Sending (client to server, or server to client)

```
// Client sends to server (target = the entity)
void SendMyRequest(int data1, string data2)
{
    ScriptRPC rpc = new ScriptRPC();
    rpc.Write(data1);
    rpc.Write(data2);

    Object target = m_Device;  // entity the RPC targets
    int rpcId = LFPG_RPC_MY_REQUEST;
    bool guaranteed = true;
    PlayerIdentity identity = null;  // null = server

    rpc.Send(target, rpcId, guaranteed, identity);
    // ScriptRPC is consumed on Send — no need to delete
}

// Server sends to specific client
void SendResponseToClient(PlayerBase player, PlayerIdentity who, int result)
{
    ScriptRPC rpc = new ScriptRPC();
    rpc.Write(result);

    Object target = player;  // ← target = player entity (NOT null, NOT m_Device)
    int rpcId = LFPG_RPC_MY_RESPONSE;
    bool guaranteed = true;

    rpc.Send(target, rpcId, guaranteed, who);
}
```

### A server to client response: `target` must be the receiving player entity

This is the most common reason for "the UI never opens, no error in the logs".

When your dispatcher routes incoming RPCs through `OnRPC` of a `modded class PlayerBase` (the LFPG pattern), a server response reaches that handler only if the RPC's `target` is the player entity. With another target the RPC is silently dropped on the client: no crash, no warning, nothing happens.

| target arg | identity arg | Where it lands on the client |
|------------|--------------|------------------------------|
| `player` (`PlayerBase`) | `sender` (identity) | `player.OnRPC` fires. Use this for every server to client response |
| `m_Device` (any entity) | `sender` | `m_Device.OnRPC` fires. Use it only when the receiver is on the device, not on `PlayerBase` |
| `null` | `sender` | Dispatched, but it rarely reaches `PlayerBase.OnRPC`: the UI will not open. It works for simple "write a chat line" RPCs in some builds and is unreliable for the rest |
| `null` | `null` | Broadcast to all, with no specific handler. Avoid |

A real incident (the LFPG ATM, 2026-04):

- The server response used `rpc.Send(null, CHANNEL, true, sender)`, and the UI never opened.
- Working sibling handlers (CCTV `HandleLFPG_RequestCameraList`, Sorter `HandleSorterConfigRequest`) all use `rpc.Send(player, CHANNEL, true, sender)`.
- Fix: pass the `PlayerBase player` parameter (that the dispatcher already hands your server handler) as the `target` in the response `rpc.Send`.

The standard server to client response, for handlers that receive `(PlayerBase player, PlayerIdentity sender, ...)`:

```
rpc.Send(player, LFPG_RPC_CHANNEL, true, sender);
```

- `player` (the target) routes the RPC to that player's `PlayerBase.OnRPC` on the client.
- `sender` (the identity) is the network filter: only that one client receives the packet.

Passing only the identity without the player as target does restrict who receives the packet, but without a target the handler chain on the client usually does not fire.

### Receiving: the `OnRPC` override

```
override void OnRPC(PlayerIdentity sender, int rpc_type, ParamsReadContext ctx)
{
    super.OnRPC(sender, rpc_type, ctx);

    if (rpc_type == LFPG_RPC_MY_REQUEST)
    {
        // Server receives from client
        #ifdef SERVER
        int data1;
        if (!ctx.Read(data1))
            return;  // ALWAYS check Read return

        string data2;
        if (!ctx.Read(data2))
            return;

        // Validate sender identity
        if (!sender)
            return;

        // Process request...
        HandleMyRequest(sender, data1, data2);
        #endif
        return;
    }

    if (rpc_type == LFPG_RPC_MY_RESPONSE)
    {
        // Client receives from server
        int result;
        if (!ctx.Read(result))
            return;

        // Update UI...
        return;
    }
}
```

### RPC good practice

- **Validate the sender's identity by its stable ID, never by the `PlayerIdentity` instance (LL-259).** Derive `GetId()` on both sides and compare values; a reference comparison silently rejects a valid sender and survives any transport change. If two or more transports reach the same receiver and fail identically — measured: three distinct transports failed the same way while the RX probe showed the RPC always arrived, because two shared guards compared instances (`sender != GetIdentity()` on the receiver and `GetIdentity() == stored identity` in the player lookup) — audit the shared guards/lookup before changing transport.

1. **Check the return of every `ctx.Read()`.** False means a corrupt or truncated packet.
2. **Validate the sender's identity** on the server.
3. **Use `guaranteed = true` for state that matters**, false for cosmetic updates.
4. **A `ScriptRPC` needs no cleanup after `Send`.** `new ScriptRPC()` is fine and no `delete` is needed. (`Send` does not clear the buffer, see below.)
5. **RPC IDs must be unique per mod.** Use a dedicated block of constants (for example 20100 to 20199).
6. **Rate limit client RPCs** with a cooldown on the server.
7. **Resolve targets by network ID**, not by a device ID of your own or a cached reference.

### Where an RPC lands, and what the server must check

- `ScriptRPC.Send(Object target, int rpc_type, bool guaranteed, PlayerIdentity recipient = NULL)`: sent from a client it goes to the server; sent from the server with `recipient == NULL` it goes to **every** client. A `null` target makes it a global RPC handled by the game object instead of an entity. `Send` does not reset the buffer: calling it again resends the same data until `Reset()` (`P:\scripts\3_game\gameplay.c:104-117`).
- Two receivers. An entity gets `OnRPC(PlayerIdentity sender, int rpc_type, ParamsReadContext ctx)` (`P:\scripts\3_game\entities\object.c:860`, overridden in `P:\scripts\3_game\entities\entityai.c:3507`). The game gets the four-argument form with `Object target` (`P:\scripts\3_game\dayzgame.c:3141`), which forwards to the target's `OnRPC` when `target` is set. Read values in exactly the order they were written.
- Server-side checklist for a request handler, in this order: return unless this is the server; return on a `null` sender; find the acting `PlayerBase` from the sender identity, never from a value in the payload; return if that player is dead; before spawning a class name that came from a client, check it with `g_Game.IsKindOf(name, "Inventory_Base")` or a narrower parent (`P:\scripts\3_game\global\game.c:1437`, which walks `CfgVehicles` then `CfgAmmo` parents); check the distance between the player and the target; and apply a per-player cooldown (rule 6).

### Network ID pattern

```
// Get NetworkID from entity
int netLow;
int netHigh;
m_Device.GetNetworkID(netLow, netHigh);

// Resolve entity from NetworkID
Object resolved = GetGame().GetObjectByNetworkId(netLow, netHigh);
EntityAI entity = EntityAI.Cast(resolved);
if (!entity)
    return;  // Entity no longer exists
```

---

### One ID and a function name: the RPCManager pattern

An alternative to a growing `enum` of RPC IDs: register one high fixed RPC ID on `DayZGame.Event_OnRPC`, and dispatch on a function name written as the first parameter. Adding a networked call then means writing a method whose name matches the string: no enum to maintain, no ID per message. This is the classic community "RPCManager" (in the style of Cj187's); it is used in SIBNIC's Gunner mod (`RPCManager_Gunner`).

```c
protected const int FRAMEWORK_RPC_ID = 1004258;   // one high, unlikely-to-collide id

class RPCManager_X
{
    protected Class m_InstanceClass;                       // the object holding the handler methods
    void RPCManager_X()  { GetDayZGame().Event_OnRPC.Insert(OnRPC); }
    void ~RPCManager_X() { GetDayZGame().Event_OnRPC.Remove(OnRPC); }
    void Reg_Class(Class instance) { m_InstanceClass = instance; }
    Class GetInstanceClass() { return m_InstanceClass; }

    void OnRPC(PlayerIdentity sender, Object target, int rpc_type, ParamsReadContext ctx)
    {
        if (rpc_type != FRAMEWORK_RPC_ID) return;
        Param1<string> fn = new Param1<string>("");
        if (!ctx.Read(fn)) return;
        auto callData = new Param3<ParamsReadContext,PlayerIdentity,Object>(ctx, sender, target);
        GetGame().GameScript.CallFunctionParams(GetRPCManager_X().GetInstanceClass(), fn.param1, NULL, callData);
    }

    void SendRPC(ref array<ref Param> params, bool guaranteed = false,
                 ref PlayerIdentity toIdentity = NULL, ref Object toTarget = NULL)
    {
        GetGame().RPC(toTarget, FRAMEWORK_RPC_ID, params, guaranteed, toIdentity);
    }
}
static ref RPCManager_X g_RPCManager_X;
static ref RPCManager_X GetRPCManager_X() { if (!g_RPCManager_X) g_RPCManager_X = new ref RPCManager_X; return g_RPCManager_X; }
```

The sender writes the function name as the first parameter:
```c
ref array<ref Param> p = new array<ref Param>;
p.Insert(new Param1<string>("MyVerb_Client"));          // dispatch name
p.Insert(new Param2<PlayerBase,int>(player, seatIdx));  // payload the handler reads
GetRPCManager_X().SendRPC(p, true, identity);
```
The handler is a method on the registered instance, for example a `modded MissionGameplay` that called `GetRPCManager_X().Reg_Class(this)` in its constructor:
```c
void MyVerb_Client(ref ParamsReadContext ctx, ref PlayerIdentity sender, ref Object target)
{
    Param2<PlayerBase,int> par = new Param2<PlayerBase,int>(NULL, 0);
    ctx.Read(par);
    // ... act on par.param1 / par.param2
}
```

**Trade-offs.** For: adding a call is trivial, there is one ID, and the names document themselves. Against: `CallFunctionParams` dispatches on a string (a typo silently does nothing, and nothing checks the name at compile time); the single ID can still collide if two mods pick the same number (pick a random high one); and nothing checks the side or the authority for you, so the handler must check `GetGame().IsServer()` and validate the sender itself (a `*_Server` method must not trust entities a client supplied). Fail closed on an unknown or invalid payload.

The sample is the community code as it ships, including `ref` on parameters and `new ref`, which the rules in `memory-management.md` tell you not to write in your own code.

- **`Event_OnRPC` fires for all `rpc_type` on both processes** (`P:\scripts\3_game\dayzgame.c:991`; `Invoke` at `:3144` is before the `if (target)` at `:3148` and **outside** the `#ifndef SERVER` / `#ifndef NO_GUI` that guard the vanilla `switch` at `:3157-3158`). `Serializer.Read` **consumes the context even when the type does not match** — there is no rewind (`P:\scripts\1_core\proto\serializer.c:56-64`). A subscriber that calls `ctx.Read` before checking its own `rpc_type` eats another handler's payload; the downstream handler (`CfgGameplayHandler.OnRPC`, `UndergroundAreaLoader.OnRPC`) then gets `false` and the symptom ("cfggameplay never arrives", stamina/lighting glitches) points away from the mod. [MEASURED IN-GAME 2026-08-17: `Read` with `Param1<int>` over a `Param1<T>` payload returned true (value 3); the subsequent correct-type `Read` returned false.] The correct pattern is vanilla's: filter **`rpc_type` and side** before any read (`P:\scripts\3_game\syncevents.c:13`). Vanilla can read unfiltered inside `UndergroundAreaLoader.OnRPC` only because it is called from the `case` that already filtered (`P:\scripts\3_game\dayzgame.c:3146-3150`); a mod in `Event_OnRPC` has no such `case`.
- **Do not derive mod RPC IDs from `ERPCs.RPC_END`.** The enum contains **96 lines conditioned on `#ifdef DIAG_DEVELOPER`** (`P:\scripts\3_game\enums\erpcs.c:110-205`) **before** `RPC_END` (`:225`), so its numeric value **differs between diag and retail builds**. A derived ID mismatches in a client-diag / server-retail pair and fails **silently**: the RPC is sent, nobody handles it, no error. Use fixed high literals (`const int` with hex is vanilla idiom: `P:\scripts\1_core\constants.c:35`, `:63-72`). Supporting fact: the `switch` in `DayZGame.OnRPC` has **no `default:`**, so an unknown `rpc_type` produces no engine error.
- **Hooking `Event_OnRPC` does not require `modded class DayZGame`.** `Event_OnRPC` is `static` and accessed by class name — vanilla idiom: `DayZGame.MISSION_STATE_GAME` (`P:\scripts\4_world\entities\dayzplayerimplement.c:846`), `DayZGame.DeferredInit` (`P:\scripts\3_game\ppemanager\ppemanager.c:83`) — which avoids collision with another mod that overrides `OnRPC`. The `Insert` must not copy vanilla's timing: `SyncEvents.RegisterEvents()` lives in the `MissionGameplay` constructor (`P:\scripts\5_mission\mission\missiongameplay.c:82`), which is **client-side and late**; it can afford that because its RPCs fire in `ClientNew`. A document sent in `ClientPrepare` (`P:\scripts\5_mission\mission\missionserver.c:317-324`) arrives **before** that mission exists and is lost without trace.

### Community Framework: module events and RPC dispatch in single player (CF 1.5.8)

These facts are about the Community Framework mod, read in its source at version 1.5.8 (September 2026; the file paths below are under its `JM/CF/Scripts/` folder). They were not measured in game and are not yet checked against the CF copy on `P:\`. `skills/_shared/enscript/integrations/community_framework.md` holds the facts this repo checked in the CF PBO.

- Register a module with the class attribute `[CF_RegisterModule(MyModule)]` above its declaration; the attribute's constructor inserts the type into the module manager (`1_Core/CommunityFramework/Module/CF_RegisterModule.c:1-6`, used at `4_World/CommunityFramework/ModStorage/CF_ModStorageModule.c:6`).
- Every event handler takes `(Class sender, CF_EventArgs args)` and only fires after its `Enable...()` call in `OnInit()`. On `CF_ModuleCore` (`1_Core/CommunityFramework/Module/CF_ModuleCore.c:76-238`): `OnMissionStart`, `OnMissionFinish`, `OnMissionLoaded`, `OnUpdate`, `OnSettingsChanged`, `OnPermissionsChanged`, `OnWorldCleanup`, the `OnMPSession*` / `OnMPConnect*` events, `OnRespawn`, `OnLoginTime`, `OnLoginStatus`, `OnLogout`, `OnChat`. `OnUpdate` receives a `CF_EventUpdateArgs`; cast it and read `DeltaTime` (`1_Core/CommunityFramework/EventArgs/CF_EventUpdateArgs.c:1-7`). The mission keeps one instance and reuses it (`5_Mission/CommunityFramework/Mission/MissionBase.c:7`), so do not store it.
- `CF_ModuleWorld` adds the server-side client lifecycle (`4_World/CommunityFramework/Module/CF_ModuleWorld.c`): `OnInvokeConnect`, `OnInvokeDisconnect`, `OnClientNew`, `OnClientRespawn`, `OnClientReady`, `OnClientPrepare`, `OnClientReconnect`, `OnClientLogout`, `OnClientDisconnect` (fires when the player has left; no reconnect follows), `OnClientLogoutCancelled`, each with its `Enable...()` (`:3-101`).
- `SingleplayerExecutionType` only matters when one process is both server and client (offline, not multiplayer). There, `Server` runs the handler once as the server call, `Client` once as the client call, and `Both` runs it twice, server call first. In multiplayer the value is ignored: the server always handles, and clients always handle (`3_Game/CommunityFramework/RPC/RPCManager.c:8-13`, `:89-98`). `SendRPCs` does not support `Both` and logs a warning (`:142`, `:162-164`).

### `Event_OnRPC`: filter before the first context read (SP-338)

The bus above is safe because it rejects the RPC id before `ctx.Read`. `ParamsReadContext` is a `Serializer` (`P:\scripts\3_game\gameplay.c:15`), and a read consumes its stream even when the requested payload type is wrong; there is no seek or rewind (`P:\scripts\1_core\proto\serializer.c:55-65`). `DayZGame.Event_OnRPC` receives every RPC on both processes (`P:\scripts\3_game\dayzgame.c:3141-3155`), so the id and applicable side must be rejected before any read.

```c
// WRONG: this can consume another handler's payload.
Param1<string> payload = new Param1<string>("");
if (!ctx.Read(payload)) return;
if (rpc_type != MY_RPC_ID) return;

// RIGHT: filter id and side first, then touch ctx.
if (rpc_type != MY_RPC_ID) return;
if (GetGame().IsDedicatedServer()) return; // client-only handler; invert for server-only
Param1<string> safePayload = new Param1<string>("");
if (!ctx.Read(safePayload)) return;
```

For side filters that run during load, use `IsDedicatedServer()` and `!IsDedicatedServer()` instead of relying on `IsClient()`. A wrong-order subscriber can break a different mod or a vanilla consumer with no warning; when multiple subscribers are wrong, load order decides which one consumes the stream first.

### Server changes seen to replicate without custom sync (SP-338)

These results were measured (with the knowledge pack's LFProbe mod) from a dedicated server to a client that was already connected, with both running when the change was made:

| Server call | Seen on the connected client without custom sync | Declaration |
|---|---|---|
| `SetObjectMaterial(int, string)` | Yes | `P:\scripts\3_game\entities\entityai.c:2884` |
| `SetObjectTexture(int, string)` | Yes | `P:\scripts\3_game\entities\entityai.c:2881` |
| `SetAnimationPhase(string, float)` | Yes, including fractional phases | `P:\scripts\3_game\entities\entity.c:15` |
| `SetPosition(vector)` | Yes | `P:\scripts\3_game\entities\object.c:294` |
| `SetScale(float)` | No | `P:\scripts\1_core\proto\enentity.c:448` |

Replicate scale yourself, for example with `RegisterNetSyncVariableFloat` (`P:\scripts\3_game\entities\entityai.c:2861`; line 2881 of `entityai.c` in 1.29.0.163451) [EXACT], then apply the synced value on the client. The argument is decimal digits and defaults to `1`. Raise it when values such as `1.25` must survive range quantization, or pass equal minimum and maximum values when the unbounded form is intended. Scale also affects collision: otherwise identical LFProbe boxes at scale `1` and `0.5` produced vertical ray distances of `0.2018 m` and `0.1018 m` (ratio `0.5045`).

A measured replication says nothing about a client that joins later or about objects placed in the map; both remain unverified. Animation state is also model-specific: `Barrel_ColorBase` drives its two caps from the phase (`P:\scripts\4_world\entities\itembase\barrel_colorbase.c:148-154`), and phase `0.5` exposed both in the LFProbe measurement. `GetAnimationPhase` immediately after a write also returned the previous value in that probe. Verify the target model and the required observation timing.

**Visual writes made only on the client are overwritten (measured in game, DayZ 1.30.164014 Exp).** `SetObjectTexture` / `SetSimpleHiddenSelectionState` written only on the owning client are overwritten when the server re-forwards the object (measured once: on drop, the liquid returned to the config color while the display name stayed). The server must also write the visuals — but only when what is visible changes, keyed to the state that owns them — and the client re-applies them in `EEItemLocationChanged`. Vanilla precedent for server-written visuals: `SetObjectMaterial` in `ChemLight.CreateLight` carries the comment "must be server side!" (`P:\scripts\4_world\entities\itembase\chemlight.c:68`, DayZ 1.30.164014 Exp). [EXACT]

---

## Persistence (`OnStoreSave` and `OnStoreLoad`)

Entities with persistence enabled save and load data across server restarts. The checked pattern and the save contract are in `skills/_shared/enscript/patterns/persistence.md` and the persistence pack (`skills/_shared/persistence/README.md`).

### Saving

```
override void OnStoreSave(ParamsWriteContext ctx)
{
    super.OnStoreSave(ctx);

    // Write in EXACT same order as OnStoreLoad reads
    ctx.Write(m_PoweredNet);
    ctx.Write(m_FilterJSON);
    ctx.Write(m_LinkedContainerLow);
    ctx.Write(m_LinkedContainerHigh);
}
```

### Loading

```
override bool OnStoreLoad(ParamsReadContext ctx, int version)
{
    if (!super.OnStoreLoad(ctx, version))
        return false;

    // Read in EXACT same order as OnStoreSave writes
    if (!ctx.Read(m_PoweredNet))
        return false;

    if (!ctx.Read(m_FilterJSON))
        return false;

    if (!ctx.Read(m_LinkedContainerLow))
        return false;

    if (!ctx.Read(m_LinkedContainerHigh))
        return false;

    return true;
}
```

### Version management

When you add persisted fields, old saves do not contain them, so the load must know which layout it is reading. The `version` argument of `OnStoreLoad` is the game's storage version (`GAME_STORAGE_VERSION`, `P:\scripts\3_game\global\game.c:5`), not a version of your mod, so write your own version number first and branch on that. (The knowledge pack's example branched on `version >= 2` as if it were the mod's own number; that is corrected here.)

```
const int MYMOD_SAVE_VERSION = 2;

override void OnStoreSave(ParamsWriteContext ctx)
{
    super.OnStoreSave(ctx);
    ctx.Write(MYMOD_SAVE_VERSION);   // your own version header
    ctx.Write(m_PoweredNet);
    ctx.Write(m_NewField);
}

override bool OnStoreLoad(ParamsReadContext ctx, int version)
{
    if (!super.OnStoreLoad(ctx, version))
        return false;

    int saveVersion;
    if (!ctx.Read(saveVersion))
        return false;

    // Original fields (v1)
    if (!ctx.Read(m_PoweredNet))
        return false;

    // Field added in v2
    if (saveVersion >= 2)
    {
        if (!ctx.Read(m_NewField))
            return false;
    }
    else
    {
        m_NewField = DEFAULT_VALUE;  // sensible default for old saves
    }

    return true;
}
```

If you change the saved layout without handling versions, every existing entity with old data fails to load and its data is corrupted. The LFPowerGrid mod wipes saves on a major layout change instead of migrating.

### Persistence config

The knowledge pack sets `storageCategory` on its entities in `config.cpp`:
```
class LF_MyDevice: Inventory_Base
{
    scope = 2;
    storageCategory = 1;  // enables persistence
};
```

---

## Side checks during load

The knowledge pack reports that during loading the side check functions return unexpected values:

| Function | During load | After load |
|---|---|---|
| `GetGame().IsServer()` | **true** even on client | true on server |
| `GetGame().IsClient()` | **unreliable** on client (not guaranteed true during load; see rules 19-20) | true on client |
| `GetGame().IsDedicatedServer()` | false on the client (correct) | false on the client |
| `GetGame().IsMultiplayer()` | true (correct) | true |

Rule: during load use `GetGame().IsDedicatedServer()` for server checks and `!GetGame().IsDedicatedServer()` for client checks. Vanilla calls it the robust check, "valid much sooner" (`P:\scripts\3_game\global\game.c:1121-1125`).

Exception: to support offline and single player play, `IsServer()` is correct (it returns true in single player, where the client is also the server).

---

## File I/O

Enforce Script has a small set of file operations (the path tokens and `FileMode` are in `skills/_shared/enscript/references/file_paths.md`):

```
// JSON serialization (typed)
JsonFileLoader<MyClass>.JsonLoadFile(path, myInstance);
JsonFileLoader<MyClass>.JsonSaveFile(path, myInstance);

// File existence check
bool exists = FileExist(path);

// Copy and delete (no rename!)
CopyFile(srcPath, dstPath);
DeleteFile(path);

// Directory operations
MakeDirectory(dirPath);
```

### Use the JSON helpers that return a status (SP-136)

Treat the `JsonLoadFile` and `JsonSaveFile` calls in the snippet above as examples of the old API only, not as advice for new code. Use `JsonFileLoader<T>.LoadFile(string filename, out T data, out string errorMessage)` and check both its `bool` result and error text. The legacy helpers return `void` and cannot signal failure. JSON file I/O is synchronous and blocks the main thread; never call it from `OnUpdate()`.

There is no `RenameFile` in Enforce Script (no vanilla script under `P:\scripts\` names one). Use `CopyFile` then `DeleteFile`.

**A save that cannot leave a half-written file** (used in production by the LFPowerGrid mod):

1. Write to `.tmp`
2. Check that `.tmp` can be read (optional, behind a setting)
3. Back up the existing file to `.bak`
4. `CopyFile` from `.tmp` to the target
5. `DeleteFile` the `.tmp`
6. On load: if the target is missing but `.bak` exists, restore from the backup
