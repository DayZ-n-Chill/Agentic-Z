// =============================================================================
// MyMod_PlayerBase.c
// Comprehensive modded PlayerBase showing:
//   1. Member variables (server state, a synced bitfield, a client-only timer)
//   2. Init + NetSync registration
//   3. OnStoreSave / OnStoreLoad with version guard
//   4. OnRPC additions
//   5. Stat reads (health, blood, energy, stamina)
//   6. Reading an agent count
//   7. Inventory queries
//   8. Server guards on the methods that change state
//
// Placement: Scripts/4_World/Entities/ManBase/MyMod_PlayerBase.c
//
// RULE: every override MUST call super.* unless you have a deliberate reason
//        not to. Forgetting super is a common source of broken interactions.
// =============================================================================

// ---- Persistence version for MY mod's player data --------------------------
const int MYMOD_PLAYER_STORE_VERSION = 2;

// ---- RPC IDs used by OnRPC below -------------------------------------------
// The same enum as 04_rpc_patterns.c. A mod declares it once, so keep a single
// copy if you take both files.
enum MyMod_ERPCs
{
    RPC_SHOW_NOTIFICATION = 20000,
}

// ---- Shared between server and client via NetSync --------------------------
enum MyMod_PlayerSyncFlags
{
    HAS_CANTEEN  = 1,  // bit 0
    IS_POISONED  = 2,  // bit 1
    IS_EXHAUSTED = 4,  // bit 2
    // add more bits up to 31 (int32)
}

modded class PlayerBase
{
    // -----------------------------------------------------------------------
    // Member variables
    // Server-side state (no NetSync)
    // -----------------------------------------------------------------------
    protected int   m_MyMod_Points;
    protected float m_MyMod_Reputation;
    protected bool  m_MyMod_IsBanned;
    protected int   m_MyMod_QuestsDone;     // added in store version 2

    // Synced to clients. Derived state: rebuilt from the player on every
    // scheduled tick, so it is never saved (saving it would only grow every
    // player record).
    protected int   m_MyMod_SyncFlags;      // bitfield

    // Client-side only (visual)
    protected float m_MyMod_LocalGlowTimer;

    // -----------------------------------------------------------------------
    // Init: register NetSync variables HERE, always after super().
    // PlayerBase has its own Init(), called from its constructor
    // (P:\scripts\4_world\entities\manbase\playerbase.c:359-364).
    // -----------------------------------------------------------------------
    override void Init()
    {
        super.Init();

        RegisterNetSyncVariableInt("m_MyMod_SyncFlags");
        // Optionally bound the range to save bandwidth (min, max)
        // RegisterNetSyncVariableInt("m_MyMod_SyncFlags", 0, 7);
    }

    // -----------------------------------------------------------------------
    // NetSync encode (server): builds the flags and marks the player dirty
    // only when they changed, since this runs on every scheduled tick
    // (netsync.md: never call SetSynchDirty every frame).
    // -----------------------------------------------------------------------
    void MyMod_UpdateSyncFlags()
    {
        if (!GetGame().IsServer())
            return;

        int flags = 0;

        EntityAI held = GetItemInHands();   // P:\scripts\4_world\entities\manbase\playerbase.c:6733
        if (held && held.IsInherited(MyMod_CustomCanteen))
            flags |= MyMod_PlayerSyncFlags.HAS_CANTEEN;

        if (GetSingleAgentCount(eAgents.FOOD_POISON) > 200)
            flags |= MyMod_PlayerSyncFlags.IS_POISONED;

        if (GetStaminaHandler().GetStamina() < 10)   // playerbase.c:2042, staminahandler.c:1081
            flags |= MyMod_PlayerSyncFlags.IS_EXHAUSTED;

        if (flags == m_MyMod_SyncFlags)
            return;

        m_MyMod_SyncFlags = flags;
        SetSynchDirty();
    }

    // -----------------------------------------------------------------------
    // NetSync decode (client): all synced variables are fresh here
    // -----------------------------------------------------------------------
    override void OnVariablesSynchronized()
    {
        super.OnVariablesSynchronized();

        bool isPoisoned  = (m_MyMod_SyncFlags & MyMod_PlayerSyncFlags.IS_POISONED)  != 0;
        bool isExhausted = (m_MyMod_SyncFlags & MyMod_PlayerSyncFlags.IS_EXHAUSTED) != 0;

        // Update local HUD / VFX
        if (isPoisoned)
        {
            // e.g. enable a green tint PPE effect
        }

        if (isExhausted)
        {
            // e.g. apply screen-space vignette
        }
    }

    // -----------------------------------------------------------------------
    // OnScheduledTick: server-side periodic update for this player
    // -----------------------------------------------------------------------
    override void OnScheduledTick(float deltaTime)
    {
        super.OnScheduledTick(deltaTime);

        if (!GetGame().IsServer())
            return;

        // Example: passive reputation decay
        m_MyMod_Reputation = Math.Max(0, m_MyMod_Reputation - 0.01 * deltaTime);
        MyMod_UpdateSyncFlags();
    }

    // -----------------------------------------------------------------------
    // WARNING: saved fields on a vanilla class. Ship this only on a fresh
    // server. On a server with existing saves the first ctx.Read(myVersion)
    // reads another class's data and the player record fails to load; removing
    // the mod later breaks loading again. Otherwise use CF ModStorage. See
    // _shared/persistence/versioning-and-migration.md, "Adding saved fields to
    // a vanilla class".
    // -----------------------------------------------------------------------

    // -----------------------------------------------------------------------
    // Persistence – SAVE
    // Write fields in a stable order; never re-order between versions.
    // Save only state the server cannot rebuild; m_MyMod_SyncFlags is not saved.
    // -----------------------------------------------------------------------
    override void OnStoreSave(ParamsWriteContext ctx)
    {
        super.OnStoreSave(ctx);  // MUST be first

        ctx.Write(MYMOD_PLAYER_STORE_VERSION);  // version header
        ctx.Write(m_MyMod_Points);
        ctx.Write(m_MyMod_Reputation);
        ctx.Write(m_MyMod_IsBanned);
        // v2 fields:
        ctx.Write(m_MyMod_QuestsDone);
    }

    // -----------------------------------------------------------------------
    // Persistence – LOAD
    // -----------------------------------------------------------------------
    override bool OnStoreLoad(ParamsReadContext ctx, int version)
    {
        if (!super.OnStoreLoad(ctx, version))
            return false;

        int myVersion;
        if (!ctx.Read(myVersion))
            return false;

        if (!ctx.Read(m_MyMod_Points))    return false;
        if (!ctx.Read(m_MyMod_Reputation)) return false;
        if (!ctx.Read(m_MyMod_IsBanned))  return false;

        if (myVersion < 2)
            return true;  // m_MyMod_QuestsDone not in older saves; keep default

        if (!ctx.Read(m_MyMod_QuestsDone)) return false;

        return true;
    }

    // -----------------------------------------------------------------------
    // OnRPC additions
    // -----------------------------------------------------------------------
    override void OnRPC(PlayerIdentity sender, int rpc_type, ParamsReadContext ctx)
    {
        super.OnRPC(sender, rpc_type, ctx);

        switch (rpc_type)
        {
            #ifndef SERVER
            case MyMod_ERPCs.RPC_SHOW_NOTIFICATION:
            {
                Param1<string> p = new Param1<string>("");
                if (ctx.Read(p))
                    MessageAction(p.param1);
                break;
            }
            #endif
        }
    }

    // -----------------------------------------------------------------------
    // Stat helpers – thin wrappers so callers don't need to dig into managers
    // -----------------------------------------------------------------------

    // Get current health (0..100)
    float MyMod_GetHealth()
    {
        return GetHealth("", "");
    }

    // Get blood volume (0..5000 ml). Blood is a health type, not a player stat:
    // vanilla reads it with GetHealth("GlobalHealth", "Blood")
    // (P:\scripts\4_world\classes\playermodifiers\modifiers\bloodregen.c:14).
    float MyMod_GetBlood()
    {
        return GetHealth("GlobalHealth", "Blood");
    }

    // Get energy (0..5000 kcal)
    float MyMod_GetEnergy()
    {
        return GetStatEnergy().Get();
    }

    // Get stamina (0..100)
    float MyMod_GetStaminaPct()
    {
        if (!m_StaminaHandler)
            return 100;
        return m_StaminaHandler.GetStamina();
    }

    // -----------------------------------------------------------------------
    // Inventory helpers
    // -----------------------------------------------------------------------

    // Count how many of a given type are in player's full inventory
    int MyMod_CountItem(typename itemType)
    {
        int count = 0;
        array<EntityAI> items = new array<EntityAI>;
        GetInventory().EnumerateInventory(InventoryTraversalType.INORDER, items);

        foreach (EntityAI e : items)
        {
            if (e.IsInherited(itemType))
                count++;
        }
        return count;
    }

    // Find first item of a given type in cargo/hands/attachments
    EntityAI MyMod_FindItem(typename itemType)
    {
        array<EntityAI> items = new array<EntityAI>;
        GetInventory().EnumerateInventory(InventoryTraversalType.INORDER, items);

        foreach (EntityAI e : items)
        {
            if (e.IsInherited(itemType))
                return e;
        }
        return null;
    }
}
