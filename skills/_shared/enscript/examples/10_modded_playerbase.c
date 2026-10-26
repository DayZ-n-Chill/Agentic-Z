// =============================================================================
// MyMod_PlayerBase.c
// Comprehensive modded PlayerBase showing:
//   1. Member variables (server state and a synced bitfield)
//   2. Init + NetSync registration
//   3. OnStoreSave / OnStoreLoad with version guard
//   4. Stat reads (health, blood, energy, stamina)
//   5. Reading an agent count
//   6. Inventory queries
//   7. Server guards on the methods that change state
//
// RPC handling on PlayerBase (OnRPC) is shown in 04_rpc_patterns.c, whose
// modded PlayerBase.OnRPC handles every MyMod_ERPCs value. This file adds no
// OnRPC override: a second handler for the same RPC id would re-read a
// context the first handler already consumed.
//
// Placement: Scripts/4_World/Entities/ManBase/MyMod_PlayerBase.c
//
// RULE: every override MUST call super.* unless you have a deliberate reason
//        not to. Forgetting super is a common source of broken interactions.
// =============================================================================

// ---- Persistence version for MY mod's player data --------------------------
const int MYMOD_PLAYER_STORE_VERSION = 2;

// ---- Item type used by MyMod_UpdateSyncFlags below -------------------------
// MyMod_CustomCanteen is declared in 01_custom_item.c. Take that file with this
// one, or swap the check for a vanilla type such as Canteen
// (P:\scripts\4_world\entities\itembase\edible_base\bottle_base\canteen.c:1).

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

    // -----------------------------------------------------------------------
    // Init: register NetSync variables HERE, always after super().
    // PlayerBase has its own Init(), called from its constructor
    // (P:\scripts\4_world\entities\manbase\playerbase.c:359-364).
    // -----------------------------------------------------------------------
    override void Init()
    {
        super.Init();

        RegisterNetSyncVariableInt("m_MyMod_SyncFlags");
        // Optionally bound the range (min, max) so the value is quantized;
        // min == max (the default 0, 0) means no quantization
        // (P:\scripts\3_game\entities\entityai.c:2843-2850; vanilla passes a
        // range at entityai.c:227). 0..7 covers the three flags above; widen
        // it when you add a bit.
        // RegisterNetSyncVariableInt("m_MyMod_SyncFlags", 0, 7);
    }

    // -----------------------------------------------------------------------
    // NetSync encode (server): builds the flags and marks the player dirty
    // only when they changed, since this runs on every scheduled tick
    // (netsync.md: never call SetSynchDirty every frame; SetSynchDirty is
    // P:\scripts\3_game\entities\entityai.c:3064).
    // -----------------------------------------------------------------------
    void MyMod_UpdateSyncFlags()
    {
        if (!GetGame().IsServer())
            return;

        int flags = 0;

        EntityAI held = GetItemInHands();   // P:\scripts\4_world\entities\manbase\playerbase.c:6733
        if (held && held.IsInherited(MyMod_CustomCanteen))
            flags |= MyMod_PlayerSyncFlags.HAS_CANTEEN;

        // GetSingleAgentCount(int agent_id) is playerbase.c:8121 and FOOD_POISON
        // is P:\scripts\3_game\enums\eagents.c:9; vanilla's poisoning modifier
        // reads it the same way (P:\scripts\4_world\classes\playermodifiers\modifiers\conditions\poisoning.c:32).
        // 200 is an example threshold for this mod, not a vanilla constant.
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
    // (vanilla override: playerbase.c:6170)
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
    // OnScheduledTick (vanilla: playerbase.c:3007) runs on BOTH machines:
    //   server, for every player: MissionServer.TickScheduler calls OnTick
    //     (P:\scripts\5_mission\mission\missionserver.c:781), which calls
    //     OnScheduledTick (playerbase.c:3129);
    //   client, for the local player only: MissionGameplay.TickScheduler
    //     (P:\scripts\5_mission\mission\missiongameplay.c:230).
    // The IsServer guard below keeps the state changes on the server.
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
    // The write order must mirror OnStoreLoad below, which reads the vanilla
    // data first (super.OnStoreLoad), so super.OnStoreSave comes first here.
    // Vanilla PlayerBase calls super before its own fields in both
    // (playerbase.c:7353-7361 save, :7408-7421 load).
    // -----------------------------------------------------------------------
    override void OnStoreSave(ParamsWriteContext ctx)
    {
        super.OnStoreSave(ctx);  // first, to mirror the read order in OnStoreLoad

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
    // Stat helpers – thin wrappers so callers don't need to dig into managers
    // -----------------------------------------------------------------------

    // Get current health (0..100: SurvivorBase GlobalHealth Health hitpoints=100,
    // P:\DZ\characters\data\config.cpp:122,378-382)
    float MyMod_GetHealth()
    {
        return GetHealth("", "");
    }

    // Get blood volume (0..5000 ml: Blood hitpoints=5000,
    // P:\DZ\characters\data\config.cpp:412-414). Blood is a health type, not a player stat:
    // vanilla reads it with GetHealth("GlobalHealth", "Blood")
    // (P:\scripts\4_world\classes\playermodifiers\modifiers\bloodregen.c:14).
    float MyMod_GetBlood()
    {
        return GetHealth("GlobalHealth", "Blood");
    }

    // Get energy (0..5000 kcal: the Energy stat is registered with min 0 and
    // max PlayerConstants.SL_ENERGY_MAX, P:\scripts\4_world\classes\playerstats\playerstatspco.c:340,
    // and SL_ENERGY_MAX = 5000, P:\scripts\3_game\playerconstants.c:45)
    float MyMod_GetEnergy()
    {
        return GetStatEnergy().Get();
    }

    // Get stamina as a percentage (0..100). Raw stamina runs 0..staminaMax: the
    // handler starts stamina and its cap at CfgGameplayHandler.GetStaminaMax()
    // (P:\scripts\4_world\classes\staminahandler.c:335-338), which reads cfggameplay.json's
    // staminaMax (P:\scripts\3_game\cfggameplayhandler.c:217-220), default
    // GameConstants.STAMINA_MAX = 100 (P:\scripts\3_game\cfggameplaydatajson.c:135,
    // P:\scripts\3_game\constants.c:749). Dividing by that maximum keeps the result
    // 0..100 on a server that changes staminaMax.
    float MyMod_GetStaminaPct()
    {
        if (!m_StaminaHandler)
            return 100;
        return m_StaminaHandler.GetStamina() / CfgGameplayHandler.GetStaminaMax() * 100;
    }

    // -----------------------------------------------------------------------
    // Inventory helpers
    // -----------------------------------------------------------------------

    // Count how many of a given type are in player's full inventory.
    // EnumerateInventory(InventoryTraversalType, out array<EntityAI>) is
    // P:\scripts\3_game\systems\inventory\inventory.c:121-128; INORDER is one of
    // PREORDER/INORDER/POSTORDER/LEVELORDER (P:\scripts\3_game\gameplay.c:4-11),
    // and vanilla calls it the same way (P:\scripts\4_world\classes\debug\presethandlers.c:179).
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
