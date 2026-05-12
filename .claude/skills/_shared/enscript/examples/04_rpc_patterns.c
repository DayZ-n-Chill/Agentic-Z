// =============================================================================
// MyMod_RPC.c
// All common RPC patterns:
//   1. Custom RPC ID enum (avoids collision with vanilla ERPCs and other mods)
//   2. RPCSingleParam  – simplest server→specific client broadcast
//   3. GetGame().RPC   – server→all clients (or to a specific entity)
//   4. ScriptRPC        – builder pattern for multi-param payloads
//   5. OnRPC override  – receiving side on PlayerBase
//   6. Client→Server   – sending an RPC from client to server
//
// Placement: Scripts/4_World/Entities/ManBase/MyMod_RPC.c
//            (or split per concern)
// =============================================================================

// ---- 1. Custom RPC ID -------------------------------------------------------
// Vanilla ERPCs occupies 0..~200.  Community mods use high ranges.
// Pick a range unlikely to collide; document it in your mod's README.

enum MyMod_ERPCs
{
    // Range 20000–20099 claimed by MyMod
    RPC_SHOW_NOTIFICATION      = 20000,
    RPC_SYNC_PLAYER_DATA       = 20001,
    RPC_CLIENT_REQUEST_RESPAWN = 20002,  // client → server
}

// ---- Helper struct sent as payload ------------------------------------------
// Must be a class so it can be written/read from a ParamsReadContext.
// Keep it flat; nested objects require manual serialisation.

class MyMod_PlayerDataPayload
{
    int   Points;
    float Reputation;
    string Faction;

    void Write(ParamsWriteContext ctx)
    {
        ctx.Write(Points);
        ctx.Write(Reputation);
        ctx.Write(Faction);
    }

    bool Read(ParamsReadContext ctx)
    {
        if (!ctx.Read(Points))      return false;
        if (!ctx.Read(Reputation))  return false;
        if (!ctx.Read(Faction))     return false;
        return true;
    }
}

// ---- 2. Server → specific client (RPCSingleParam) --------------------------
// The simplest path: one Param wrapper, delivered only to the target player.

void MyMod_SendNotification(PlayerBase player, string message)
{
    if (!GetGame().IsServer())
        return;

    // RPCSingleParam(target_entity, rpc_id, param, guaranteed, recipient_identity)
    // ‣ target_entity  : entity the OnRPC is dispatched on
    // ‣ guaranteed     : true = reliable TCP-like, false = unreliable UDP-like
    // ‣ recipient      : null = broadcast to all; PlayerIdentity = unicast
    Param1<string> p = new Param1<string>(message);
    GetGame().RPCSingleParam(
        player,
        MyMod_ERPCs.RPC_SHOW_NOTIFICATION,
        p,
        true,
        player.GetIdentity()
    );
}

// ---- 3. Server → ALL clients (GetGame().RPC) --------------------------------

void MyMod_BroadcastPlayerData(PlayerBase player)
{
    if (!GetGame().IsServer())
        return;

    // Build the payload
    MyMod_PlayerDataPayload payload = new MyMod_PlayerDataPayload();
    payload.Points     = 100;
    payload.Reputation = 0.75;
    payload.Faction    = "East";

    // Pack into a Param array
    Param4<int, float, string, int> p = new Param4<int, float, string, int>(
        payload.Points,
        payload.Reputation,
        payload.Faction,
        player.GetSimulationTimeStamp() // extra marker to identify which player
    );

    array<ref Param> params = new array<ref Param>;
    params.Insert(p);

    // null recipient = all connected players receive this on 'player' entity
    GetGame().RPC(player, MyMod_ERPCs.RPC_SYNC_PLAYER_DATA, params, true);
}

// ---- 4. ScriptRPC – multi-param builder pattern ----------------------------
// Useful when your payload grows; avoids 8-param Param8 nesting.

void MyMod_SendComplexData(PlayerBase player, string key, int value, float factor)
{
    if (!GetGame().IsServer())
        return;

    ScriptRPC rpc = new ScriptRPC();
    rpc.Write(key);
    rpc.Write(value);
    rpc.Write(factor);

    // Send(target_entity, rpc_id, guaranteed, recipient_identity)
    rpc.Send(player, MyMod_ERPCs.RPC_SYNC_PLAYER_DATA, true, player.GetIdentity());
}

// ---- 5. OnRPC override – receiving on PlayerBase ----------------------------
// Always add YOUR cases inside the switch; never remove vanilla cases.

modded class PlayerBase
{
    override void OnRPC(PlayerIdentity sender, int rpc_type, ParamsReadContext ctx)
    {
        // ALWAYS call super first so vanilla cases still run
        super.OnRPC(sender, rpc_type, ctx);

        switch (rpc_type)
        {
            // Guard: client-only cases should only run on the local machine
            #ifndef SERVER

            case MyMod_ERPCs.RPC_SHOW_NOTIFICATION:
            {
                Param1<string> p = new Param1<string>("");
                if (ctx.Read(p))
                {
                    // Display in the game chat
                    MessageAction(p.param1);
                }
                break;
            }

            case MyMod_ERPCs.RPC_SYNC_PLAYER_DATA:
            {
                // ScriptRPC read path matches the write order exactly
                string key;
                int    value;
                float  factor;

                if (!ctx.Read(key))    break;
                if (!ctx.Read(value))  break;
                if (!ctx.Read(factor)) break;

                // Apply received data...
                // (update HUD, store in client-side cache, etc.)
                break;
            }

            #endif  // SERVER

            // Server-side cases go here (no preprocessor guard needed –
            // they simply won't match on clients since they never send them)
            case MyMod_ERPCs.RPC_CLIENT_REQUEST_RESPAWN:
            {
                if (!GetGame().IsServer())
                    break;

                // Validate and process client's respawn request
                // (never trust client input – always validate server-side)
                break;
            }
        }
    }
}

// ---- 6. Client → Server RPC -------------------------------------------------
// Clients can send RPCs UP to the server by calling RPC/RPCSingleParam
// on a server-side entity (usually themselves).  The server receives it
// in that entity's OnRPC with rpc_type matching the enum value.

void MyMod_ClientRequestRespawn(PlayerBase localPlayer)
{
    // Guard: only the local controlling client should call this
    if (GetGame().IsServer())
        return;

    if (!localPlayer || !localPlayer.IsAlive())
        return;

    Param1<int> p = new Param1<int>(1); // simple "I want to respawn" signal
    GetGame().RPCSingleParam(
        localPlayer,
        MyMod_ERPCs.RPC_CLIENT_REQUEST_RESPAWN,
        p,
        true,
        null   // recipient null = server only (no other clients need this)
    );
}
