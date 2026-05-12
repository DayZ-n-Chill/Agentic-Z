// =============================================================================
// MyMod_MissionServer.c
// MissionServer overrides for:
//   - Server startup / init
//   - Player connect / disconnect
//   - Scheduled tasks via CallLater
//   - Artillery broadcast (from vanilla pattern)
//   - Safe player spawn hook
//
// Placement: Scripts/5_Mission/Mission/MyMod_MissionServer.c
// =============================================================================

modded class MissionServer
{
    // -----------------------------------------------------------------------
    // State
    // -----------------------------------------------------------------------
    protected ref map<string, int> m_MyMod_ConnectedCount; // uid → connect count
    protected int                  m_MyMod_TickCounter;

    // -----------------------------------------------------------------------
    // Construction: runs once when the mission object is created on server
    // -----------------------------------------------------------------------
    void MissionServer()
    {
        // Nothing here yet; prefer OnInit / OnMissionStart for game-context work
    }

    // -----------------------------------------------------------------------
    // OnInit: game context is valid, server config is loaded
    // -----------------------------------------------------------------------
    override void OnInit()
    {
        super.OnInit(); // MUST call super

        m_MyMod_ConnectedCount = new map<string, int>;

        // Schedule a repeating server-tick every 60 seconds
        // CallLater(function, delay_ms, repeat, param...)
        GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).CallLater(
            this.MyMod_ServerTick,
            60000,
            true   // repeat = keep calling until explicitly removed
        );

        Print("[MyMod] MissionServer initialized");
    }

    // -----------------------------------------------------------------------
    // OnMissionStart: world is fully loaded, CE has run, players can join
    // -----------------------------------------------------------------------
    override void OnMissionStart()
    {
        super.OnMissionStart();
        Print("[MyMod] Mission started");
    }

    // -----------------------------------------------------------------------
    // Destructor: clean up repeating callbacks to avoid dangling calls
    // -----------------------------------------------------------------------
    void ~MissionServer()
    {
        GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).Remove(this.MyMod_ServerTick);
    }

    // -----------------------------------------------------------------------
    // InvokeOnConnect: player entity + identity are fully ready
    // NOTE: PlayerConnected(uid) fires BEFORE the entity exists; use this one.
    // -----------------------------------------------------------------------
    override void InvokeOnConnect(PlayerBase player, PlayerIdentity identity)
    {
        super.InvokeOnConnect(player, identity);

        if (!player || !identity)
            return;

        string uid = identity.GetId();

        // Track connections
        int count;
        if (m_MyMod_ConnectedCount.Find(uid, count))
            m_MyMod_ConnectedCount.Set(uid, count + 1);
        else
            m_MyMod_ConnectedCount.Insert(uid, 1);

        // 3-second delay so the client HUD is rendered before we send messages
        GetGame().GetCallQueue(CALL_CATEGORY_SYSTEM).CallLater(
            this.MyMod_WelcomePlayer,
            3000,
            false,   // do NOT repeat
            player
        );

        Print(string.Format("[MyMod] %1 connected (pid=%2)", identity.GetName(), uid));
    }

    // -----------------------------------------------------------------------
    // InvokeOnDisconnect
    // -----------------------------------------------------------------------
    override void InvokeOnDisconnect(PlayerBase player)
    {
        super.InvokeOnDisconnect(player);

        if (!player)
            return;

        PlayerIdentity id = player.GetIdentity();
        if (id)
            Print(string.Format("[MyMod] %1 disconnected", id.GetName()));
    }

    // -----------------------------------------------------------------------
    // HandleNewPlayer: called just before the new character is placed in world.
    // Good hook for giving starter items.
    // -----------------------------------------------------------------------
    override void HandleNewPlayer(PlayerBase player, string uid, Param par)
    {
        super.HandleNewPlayer(player, uid, par);

        if (!player)
            return;

        // Spawn a starter item into cargo (server only)
        EntityAI item = player.GetInventory().CreateInInventory("MyMod_CustomCanteen");
        if (item)
        {
            MyMod_CustomCanteen canteen;
            if (Class.CastTo(canteen, item))
            {
                canteen.SetQuantity(500);   // pre-fill with water
                canteen.MyMod_SetContaminated(false);
            }
        }
    }

    // -----------------------------------------------------------------------
    // Welcome helper (called via CallLater, so player may have disconnected)
    // -----------------------------------------------------------------------
    void MyMod_WelcomePlayer(PlayerBase player)
    {
        if (!player || !player.IsAlive())
            return;

        string name = "";
        PlayerIdentity id = player.GetIdentity();
        if (id)
            name = id.GetName();

        string msg = string.Format("Welcome, %1! Stay alive.", name);
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
