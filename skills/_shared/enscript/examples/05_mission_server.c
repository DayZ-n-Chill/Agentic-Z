// =============================================================================
// MyMod_MissionServer.c
// MissionServer overrides for:
//   - Server startup / init
//   - Player connect / disconnect
//   - Scheduled tasks via CallLater
//   - Starter item for newly created characters
//
// Placement: Scripts/5_Mission/Mission/MyMod_MissionServer.c
//
// Vanilla source this was checked against:
//   class MissionServer extends MissionBase   P:\scripts\5_mission\mission\missionserver.c:5
//   class Mission (OnInit / OnMissionStart)   P:\scripts\3_game\gameplay.c:685, :700-701
// =============================================================================

modded class MissionServer
{
    // -----------------------------------------------------------------------
    // State
    // -----------------------------------------------------------------------
    protected ref map<string, int> m_MyMod_ConnectedCount; // uid -> connect count
    protected int                  m_MyMod_TickCounter;

    // -----------------------------------------------------------------------
    // Construction: runs once when the mission object is created on server.
    // Vanilla constructor: P:\scripts\5_mission\mission\missionserver.c:66
    // Unverified on P: (engine behaviour, no modded class in vanilla): a
    // constructor in a modded class runs in addition to the vanilla one.
    // -----------------------------------------------------------------------
    void MissionServer()
    {
        // Nothing here yet; prefer OnInit / OnMissionStart for game-context work
    }

    // -----------------------------------------------------------------------
    // OnInit: vanilla loads cfggameplay, spawn presets and restricted areas
    // here (P:\scripts\5_mission\mission\missionserver.c:85-97).
    // Called by the engine; exact timing is not visible in script (unverified).
    // -----------------------------------------------------------------------
    override void OnInit()
    {
        super.OnInit(); // MUST call super

        m_MyMod_ConnectedCount = new map<string, int>;

        // Schedule a repeating server-tick every 60 seconds.
        // CallLater(func fn, int delay = 0, bool repeat = false, void param1 = NULL, ...)
        // P:\scripts\2_gamelib\tools.c:61
        // CALL_CATEGORY_GAMEPLAY = 2, "Runs unless ingame menu is opened"
        // P:\scripts\3_game\tools\tools.c:10
        // Vanilla does the same for UpdatePlayersStats:
        // P:\scripts\5_mission\mission\missionserver.c:68
        GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).CallLater(
            this.MyMod_ServerTick,
            60000,
            true   // repeat = keep calling until explicitly removed (P:\scripts\2_gamelib\tools.c:54)
        );

        Print("[MyMod] MissionServer initialized");
    }

    // -----------------------------------------------------------------------
    // OnMissionStart: vanilla creates the contaminated-area zones and bunker
    // broadcast here (P:\scripts\5_mission\mission\missionserver.c:99-106).
    // Called by the engine; exact timing is not visible in script (unverified).
    // -----------------------------------------------------------------------
    override void OnMissionStart()
    {
        super.OnMissionStart();
        Print("[MyMod] Mission started");
    }

    // -----------------------------------------------------------------------
    // Destructor: clean up repeating callbacks to avoid dangling calls.
    // Remove(func fn): P:\scripts\2_gamelib\tools.c:65
    // Vanilla mirrors this in ~MissionServer: P:\scripts\5_mission\mission\missionserver.c:80-83
    // -----------------------------------------------------------------------
    void ~MissionServer()
    {
        GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).Remove(this.MyMod_ServerTick);
    }

    // -----------------------------------------------------------------------
    // InvokeOnConnect: player entity + identity are fully ready.
    // Vanilla: P:\scripts\5_mission\mission\missionserver.c:435
    // Called from OnEvent after a NEW character is created (ClientNewEventTypeID,
    // :336) and when an EXISTING character is loaded (ClientReadyEventTypeID,
    // :357). Not called on ClientReconnectEventTypeID (:380-392).
    // -----------------------------------------------------------------------
    override void InvokeOnConnect(PlayerBase player, PlayerIdentity identity)
    {
        super.InvokeOnConnect(player, identity);

        if (!player || !identity)
            return;

        // GetId(): hashed unique id, safe for logs/DB (P:\scripts\3_game\gameplay.c:367-368)
        string uid = identity.GetId();

        // Track connections
        // map.Find(key, out val) / Set / Insert: P:\scripts\1_core\proto\enscript.c:877, :902, :926
        int count;
        if (m_MyMod_ConnectedCount.Find(uid, count))
            m_MyMod_ConnectedCount.Set(uid, count + 1);
        else
            m_MyMod_ConnectedCount.Insert(uid, 1);

        // 3-second delay so the client HUD is rendered before we send messages.
        // CALL_CATEGORY_SYSTEM = 0, "Runs always" (P:\scripts\3_game\tools\tools.c:8)
        GetGame().GetCallQueue(CALL_CATEGORY_SYSTEM).CallLater(
            this.MyMod_WelcomePlayer,
            3000,
            false,   // do NOT repeat
            player
        );

        // GetName(): nick name (P:\scripts\3_game\gameplay.c:361-362)
        Print(string.Format("[MyMod] %1 connected (uid=%2)", identity.GetName(), uid));
    }

    // -----------------------------------------------------------------------
    // InvokeOnDisconnect
    // Vanilla: P:\scripts\5_mission\mission\missionserver.c:442
    // Called from PlayerDisconnected (:703), where vanilla notes "identity can
    // be already deleted" (:692), so GetIdentity() below may return null.
    // -----------------------------------------------------------------------
    override void InvokeOnDisconnect(PlayerBase player)
    {
        super.InvokeOnDisconnect(player);

        if (!player)
            return;

        // Man.GetIdentity(): P:\scripts\3_game\entities\man.c:21
        PlayerIdentity id = player.GetIdentity();
        if (id)
            Print(string.Format("[MyMod] %1 disconnected", id.GetName()));
    }

    // -----------------------------------------------------------------------
    // OnClientNewEvent: creates and equips a brand-new character and returns it.
    // Good hook for giving starter items.
    // Vanilla: P:\scripts\5_mission\mission\missionserver.c:549
    // (there is no HandleNewPlayer in vanilla MissionServer). Hooking here
    // covers both vanilla equip paths: cfggameplay spawn presets (:565-586) and
    // the default EquipCharacter path (:589-594). StartingEquipSetup (:540) is
    // only reached from EquipCharacter (:536), so it misses spawn presets.
    // -----------------------------------------------------------------------
    override PlayerBase OnClientNewEvent(PlayerIdentity identity, vector pos, ParamsReadContext ctx)
    {
        PlayerBase player = super.OnClientNewEvent(identity, pos, ctx);

        if (!player)
            return player;

        // Spawn a starter item into cargo or an attachment slot (server only).
        // GameInventory.CreateInInventory(string type) returns null when there
        // is no free spot: P:\scripts\3_game\systems\inventory\inventory.c:870-876
        EntityAI item = player.GetInventory().CreateInInventory("MyMod_CustomCanteen");
        if (item)
        {
            MyMod_CustomCanteen canteen; // defined in 01_custom_item.c
            // Class.CastTo(out Class to, Class from): P:\scripts\1_core\proto\enscript.c:110
            if (Class.CastTo(canteen, item))
            {
                // ItemBase.SetQuantity(float value, ...): P:\scripts\4_world\entities\itembase.c:3315
                // Liquid is water: Bottle_Base varLiquidTypeInit=512 (P:\DZ\data\config.cpp:3529)
                // = LIQUID_WATER (P:\scripts\3_game\constants.c:578)
                canteen.SetQuantity(500);   // pre-fill with water
                canteen.MyMod_SetContaminated(false);
            }
        }

        return player;
    }

    // -----------------------------------------------------------------------
    // Welcome helper (called via CallLater, so player may have disconnected)
    // -----------------------------------------------------------------------
    void MyMod_WelcomePlayer(PlayerBase player)
    {
        // Object.IsAlive(): P:\scripts\3_game\entities\object.c:517
        if (!player || !player.IsAlive())
            return;

        // RPCSingleParam sends to ALL clients when recipient is null
        // (P:\scripts\3_game\global\game.c:970-974), so bail out without an identity.
        PlayerIdentity id = player.GetIdentity();
        if (!id)
            return;

        string msg = string.Format("Welcome, %1! Stay alive.", id.GetName());

        // RPCSingleParam(Object target, int rpc_type, Param param, bool guaranteed,
        //                PlayerIdentity recipient = null): P:\scripts\3_game\global\game.c:1013
        // ERPCs.RPC_USER_ACTION_MESSAGE: P:\scripts\3_game\enums\erpcs.c:15
        // Client reads Param1<string> and shows it with MessageAction:
        // P:\scripts\4_world\entities\manbase\playerbase.c:5773-5782, :6930
        // Same call vanilla uses in ActionBase.SendMessageToClient:
        // P:\scripts\4_world\classes\useractionscomponent\actionbase.c:1269
        Param1<string> p = new Param1<string>(msg);
        GetGame().RPCSingleParam(player, ERPCs.RPC_USER_ACTION_MESSAGE, p, true, id);
    }

    // -----------------------------------------------------------------------
    // Periodic server-side tick (every 60 s)
    // -----------------------------------------------------------------------
    void MyMod_ServerTick()
    {
        m_MyMod_TickCounter++;

        // Every 5 minutes do a heavier operation
        if (m_MyMod_TickCounter % 5 == 0)
        {
            MyMod_HeavyTick();
        }
    }

    void MyMod_HeavyTick()
    {
        // e.g. scan all players and apply environmental effects
        // CGame.GetPlayers(out array<Man> players): P:\scripts\3_game\global\game.c:945
        array<Man> players = new array<Man>;
        GetGame().GetPlayers(players);

        foreach (Man man : players)
        {
            PlayerBase pb;
            if (Class.CastTo(pb, man) && pb.IsAlive())
            {
                // example: nudge rain exposure modifier
                // pb.GetEnvironment()... etc.
            }
        }
    }
}
