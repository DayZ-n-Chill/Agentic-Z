// =============================================================================
// MyMod_PlayerBase.c
// Comprehensive modded PlayerBase showing:
//   1. Member variable declaration (server + client, guarded by macros)
//   2. Init + NetSync registration
//   3. OnStoreSave / OnStoreLoad with version guard
//   4. OnRPC additions
//   5. Stats manipulation (health, blood, energy, water)
//   6. Agents and modifiers access
//   7. Inventory queries
//   8. Server/client guards in every method
//
// Placement: Scripts/4_World/Entities/ManBase/MyMod_PlayerBase.c
//
// RULE: every override MUST call super.* unless you have a deliberate reason
//        not to. Forgetting super is a common source of broken interactions.
// =============================================================================

// ---- Persistence version for MY mod's player data --------------------------
const int MYMOD_PLAYER_STORE_VERSION = 2;

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

    // Synced to clients
    protected int   m_MyMod_SyncFlags;      // bitfield

    // Client-side only (visual)
    protected float m_MyMod_LocalGlowTimer;

    // -----------------------------------------------------------------------
    // Init: register NetSync variables HERE, always after super()
    // -----------------------------------------------------------------------
    override void Init()
    {
        super.Init();

        RegisterNetSyncVariableInt("m_MyMod_SyncFlags");
        // Optionally bound the range to save bandwidth (min, max)
        // RegisterNetSyncVariableInt("m_MyMod_SyncFlags", 0, 7);
    }

    // -----------------------------------------------------------------------
    // NetSync encode (server): call whenever any flag changes
    // -----------------------------------------------------------------------
    void MyMod_UpdateSyncFlags()
    {
        if (!GetGame().IsServer())
            return;

        m_MyMod_SyncFlags = 0;

        EntityAI held = GetHeldItem();
        if (held && held.IsInherited(MyMod_CustomCanteen))
            m_MyMod_SyncFlags |= MyMod_PlayerSyncFlags.HAS_CANTEEN;

        if (GetSingleAgentCount(eAgents.FOOD_POISON) > 200)
            m_MyMod_SyncFlags |= MyMod_PlayerSyncFlags.IS_POISONED;

        if (GetStamina() < 10)
            m_MyMod_SyncFlags |= MyMod_PlayerSyncFlags.IS_EXHAUSTED;

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
    // Persistence – SAVE
    // Write fields in a stable order; never re-order between versions.
    // -----------------------------------------------------------------------
    override void OnStoreSave(ParamsWriteContext ctx)
    {
        super.OnStoreSave(ctx);  // MUST be first

        ctx.Write(MYMOD_PLAYER_STORE_VERSION);  // version header
        ctx.Write(m_MyMod_Points);
        ctx.Write(m_MyMod_Reputation);
        ctx.Write(m_MyMod_IsBanned);
        // v2 fields:
        ctx.Write(m_MyMod_SyncFlags);
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

        if (myVersion < 1)
            return true;

        if (!ctx.Read(m_MyMod_Points))    return false;
        if (!ctx.Read(m_MyMod_Reputation)) return false;
        if (!ctx.Read(m_MyMod_IsBanned))  return false;

        if (myVersion < 2)
            return true;  // m_MyMod_SyncFlags not in older saves; keep default

        if (!ctx.Read(m_MyMod_SyncFlags)) return false;

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

    // Get blood volume (0..5000 ml)
    float MyMod_GetBlood()
    {
        PlayerStat<float> stat;
        if (!m_PlayerStats)
            return 5000;
        // PlayerStats exposes individual stats via GetStatObject
        return GetStatBlood().Get();
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
