// =============================================================================
// MyMod_RPC.c
// All common RPC patterns:
//   1. Custom RPC ID enum (avoids collision with vanilla ERPCs and other mods)
//   2. RPCSingleParam  – simplest server→specific client send
//   3. GetGame().RPC   – server→all clients (or to a specific entity)
//   4. ScriptRPC        – builder pattern for multi-param payloads
//   5. OnRPC override  – receiving side on PlayerBase
//   6. Client→Server   – sending an RPC from client to server
//
// Placement: scripts/4_World/Entities/ManBase/MyMod_RPC.c
//            (or split per concern)
// Vanilla checked against P:\scripts (paths cited inline as path:line).
// =============================================================================

// ---- 1. Custom RPC ID -------------------------------------------------------
// Vanilla ERPCs occupies -4..~190: PB_* markers are -1..-4, RPC_SYNC_ITEM_VAR = 0,
// and RPC_END (the "do not append after" marker) lands at 189 with
// DIAG_DEVELOPER on, lower without it.
// P:\scripts\3_game\enums\erpcs.c:1-7, :225
// Community mods use high ranges.
// Pick a range unlikely to collide; document it in your mod's README.

enum MyMod_ERPCs
{
	// Range 20000–20099 claimed by MyMod
	RPC_SHOW_NOTIFICATION      = 20000,
	RPC_SYNC_PLAYER_DATA       = 20001,  // Param4 payload (section 3)
	RPC_CLIENT_REQUEST_RESPAWN = 20002,  // client → server
	RPC_SYNC_COMPLEX_DATA      = 20003,  // ScriptRPC payload (section 4)
}

// ---- Helper struct sent as payload ------------------------------------------
// ParamsReadContext / ParamsWriteContext are typedefs of Serializer
// (P:\scripts\3_game\gameplay.c:15-16); Serializer.Write/Read return bool
// (P:\scripts\1_core\proto\serializer.c:57-58).
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
	// GetGame() returns g_Game  – P:\scripts\3_game\gameplay.c:636
	// IsServer()                – P:\scripts\3_game\global\game.c:1120
	if (!GetGame().IsServer())
		return;

	// RPCSingleParam(Object target, int rpc_type, Param param, bool guaranteed,
	//                PlayerIdentity recipient = null)
	// P:\scripts\3_game\global\game.c:1013
	// ‣ target     : object whose OnRPC receives it (null = handled by CGame)
	//                P:\scripts\3_game\global\game.c:971
	// ‣ guaranteed : true = reliable, false = may be dropped
	//                (meaning not documented on P:\scripts – unverified)
	// ‣ recipient  : on the server, null = all clients; PlayerIdentity = one client
	//                P:\scripts\3_game\global\game.c:974
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
		player.GetSimulationTimeStamp() // simulation timestamp of the sender, not a player id
		                                // P:\scripts\3_game\entities\entity.c:8-9
	);

	array<ref Param> params = new array<ref Param>;
	params.Insert(p);

	// RPC(Object target, int rpcType, notnull array<ref Param> params, bool guaranteed,
	//     PlayerIdentity recipient = null)  – P:\scripts\3_game\global\game.c:1011
	// recipient omitted (null) = every client receives this on 'player' entity
	// P:\scripts\3_game\global\game.c:974
	GetGame().RPC(player, MyMod_ERPCs.RPC_SYNC_PLAYER_DATA, params, true);
}

// ---- 4. ScriptRPC – multi-param builder pattern ----------------------------
// Useful when your payload grows; avoids 8-param Param8 nesting.
// Uses its own RPC ID: its payload layout differs from section 3's, and one ID
// must always carry one layout or the receiver reads garbage.

void MyMod_SendComplexData(PlayerBase player, string key, int value, float factor)
{
	if (!GetGame().IsServer())
		return;

	// class ScriptRPC: ParamsWriteContext  – P:\scripts\3_game\gameplay.c:104
	ScriptRPC rpc = new ScriptRPC();
	rpc.Write(key);
	rpc.Write(value);
	rpc.Write(factor);

	// Send(Object target, int rpc_type, bool guaranteed, PlayerIdentity recipient = NULL)
	// P:\scripts\3_game\gameplay.c:117
	rpc.Send(player, MyMod_ERPCs.RPC_SYNC_COMPLEX_DATA, true, player.GetIdentity());
}

// ---- 5. OnRPC override – receiving on PlayerBase ----------------------------
// Always add YOUR cases inside the switch; never remove vanilla cases.

modded class PlayerBase
{
	// Same signature as vanilla – P:\scripts\4_world\entities\manbase\playerbase.c:5727
	override void OnRPC(PlayerIdentity sender, int rpc_type, ParamsReadContext ctx)
	{
		// ALWAYS call super first so vanilla cases still run
		// (vanilla does the same – playerbase.c:5729)
		super.OnRPC(sender, rpc_type, ctx);

		switch (rpc_type)
		{
			// Guard: client-only cases, wrapped exactly as vanilla does
			// P:\scripts\4_world\entities\manbase\playerbase.c:5733
			#ifndef SERVER

			case MyMod_ERPCs.RPC_SHOW_NOTIFICATION:
			{
				// Read a whole Param back with ctx.Read(p), as vanilla's own example does
				// P:\scripts\3_game\global\game.c:998-999 (doc comment above CGame.RPC)
				Param1<string> p = new Param1<string>("");
				if (ctx.Read(p))
				{
					// Prints to the local game chat in the "colorAction" style (client: g_Game.Chat)
					// P:\scripts\4_world\entities\manbase\playerbase.c:6911-6921, :6930-6933
					MessageAction(p.param1);
				}
				break;
			}

			case MyMod_ERPCs.RPC_SYNC_PLAYER_DATA:
			{
				// Each Param in the sent array is read back in order with ctx.Read
				// P:\scripts\4_world\plugins\pluginbase\plugindevelopersync.c:596-607
				Param4<int, float, string, int> data = new Param4<int, float, string, int>(0, 0, "", 0);
				if (!ctx.Read(data))
					break;

				// Apply received data (data.param1 .. data.param4)...
				// (update HUD, store in client-side cache, etc.)
				break;
			}

			case MyMod_ERPCs.RPC_SYNC_COMPLEX_DATA:
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

			// Server-side cases go here, outside the #ifndef SERVER block,
			// and start with an IsServer() guard
			case MyMod_ERPCs.RPC_CLIENT_REQUEST_RESPAWN:
			{
				if (!GetGame().IsServer())
					break;

				// Validate and process client's respawn request
				// (never trust client input – always validate server-side;
				//  'sender' is the identity the engine attached to the message)
				break;
			}
		}
	}
}

// ---- 6. Client → Server RPC -------------------------------------------------
// Called on a client, RPC/RPCSingleParam/ScriptRPC.Send are evaluated on the
// server (P:\scripts\3_game\global\game.c:970, P:\scripts\3_game\gameplay.c:111).
// The server receives it in the target entity's OnRPC with rpc_type matching
// the enum value.

void MyMod_ClientRequestRespawn(PlayerBase localPlayer)
{
	// Guard: only the local controlling client should call this
	if (GetGame().IsServer())
		return;

	// IsAlive() = !IsDamageDestroyed()  – P:\scripts\3_game\entities\object.c:517-520
	if (!localPlayer || !localPlayer.IsAlive())
		return;

	Param1<int> p = new Param1<int>(1); // simple "I want to respawn" signal
	GetGame().RPCSingleParam(
		localPlayer,
		MyMod_ERPCs.RPC_CLIENT_REQUEST_RESPAWN,
		p,
		true,
		null   // from a client the RPC always goes to the server; recipient picks a
		       // client only when sending from the server (game.c:970-974)
	);
}
