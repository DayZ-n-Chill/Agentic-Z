// =============================================================================
// MyMod_RustModifier.c
// A custom player modifier driven by a vanilla disease agent, built on the
// shape of the vanilla PoisoningMdfr and BrokenLegsMdfr:
//   P:\scripts\4_world\classes\playermodifiers\modifiers\conditions\poisoning.c
//   P:\scripts\4_world\classes\playermodifiers\modifiers\conditions\brokenlegs.c
//
//   Agent: the "disease" count in the player's agent pool (eAgents)
//   Modifier: the periodic effect that runs while a condition holds
//   Registration: AddModifier(new ...) in a modded ModifiersManager.Init()
//
// Agents and modifiers are SERVER-SIDE ONLY systems.
//
// Why no custom agent: eAgents values are bit flags that "MUST MATCH CONFIG-SIDE
// AGENT CONFIGURATION" (P:\scripts\3_game\enums\eagents.c:1), and agents are
// registered by the vanilla PluginTransmissionAgents
// (P:\scripts\4_world\plugins\pluginbase\plugintransmissionagents.c:22-26).
// This example reacts to the vanilla FOOD_POISON agent instead.
//
// Placement: Scripts/4_World/Classes/PlayerModifiers/Modifiers/MyMod_RustModifier.c
// =============================================================================

// ---- Modifier ID -------------------------------------------------------------
// Modifier IDs are plain ints kept in a map (ModifiersManager.AddModifier,
// P:\scripts\4_world\classes\playermodifiers\modifiersmanager.c:188-200) and must
// be 1 or higher (:192). Never reuse a vanilla eModifiers value
// (P:\scripts\4_world\classes\playermodifiers\emodifiers.c): two modifiers with
// one ID replace each other. Pick a number far above eModifiers.COUNT.
const int MYMOD_MDF_RUST = 25000;

// =============================================================================
// 1. MODIFIER
// =============================================================================
class MyMod_RustModifier : ModifierBase
{
    static const int   AGENT_THRESHOLD_ACTIVATE   = 200;
    static const int   AGENT_THRESHOLD_DEACTIVATE = 50;
    static const float TICK_HEALTH_LOSS           = 0.5; // health drained per active tick

    // Vanilla modifiers set their fields in Init(), which InitBase calls
    // (P:\scripts\4_world\classes\playermodifiers\modifierbase.c:38-50).
    override void Init()
    {
        m_ID                    = MYMOD_MDF_RUST;
        m_TickIntervalInactive  = DEFAULT_TICK_TIME_INACTIVE;  // modifiersmanager.c:29
        m_TickIntervalActive    = 5.0;   // run OnTick every 5 s while active
        m_IsPersistent          = true;  // saved with the player (modifierbase.c:15)
        // Keep this false for a mod modifier. When a saved modifier ID is not
        // found (your mod was removed), the loader skips the ID but cannot skip
        // its saved time value, and the rest of the player's save is misread
        // (modifiersmanager.c:285-302).
        m_TrackActivatedTime    = false;
        m_AnalyticsStatsEnabled = false; // vanilla analytics are for vanilla IDs
    }

    // ---- Activation condition (modifierbase.c:176) --------------------------
    // Checked every m_TickIntervalInactive seconds; return true to activate.
    override bool ActivateCondition(PlayerBase player)
    {
        // GetSingleAgentCount: P:\scripts\4_world\entities\manbase\playerbase.c:8121
        return player.GetSingleAgentCount(eAgents.FOOD_POISON) > AGENT_THRESHOLD_ACTIVATE;
    }

    // ---- Deactivation condition (modifierbase.c:181) ------------------------
    override bool DeactivateCondition(PlayerBase player)
    {
        return player.GetSingleAgentCount(eAgents.FOOD_POISON) <= AGENT_THRESHOLD_DEACTIVATE;
    }

    // ---- Effect tick --------------------------------------------------------
    // Called every m_TickIntervalActive seconds while this modifier is active.
    override void OnTick(PlayerBase player, float deltaT)
    {
        player.AddHealth("", "", -TICK_HEALTH_LOSS);
    }

    // ---- On activation (modifierbase.c:187) ---------------------------------
    override void OnActivate(PlayerBase player)
    {
        // PlayerBase.OnRPC shows ERPCs.RPC_USER_ACTION_MESSAGE + Param1<string>
        // as an action message (playerbase.c:5773).
        if (player.GetIdentity())
        {
            Param1<string> msg = new Param1<string>("You contracted rust sickness!");
            GetGame().RPCSingleParam(player, ERPCs.RPC_USER_ACTION_MESSAGE, msg, true, player.GetIdentity());
        }
    }

    // A persistent modifier is re-activated on connect with OnReconnect
    // (modifierbase.c:190); vanilla PoisoningMdfr forwards it to OnActivate.
    override void OnReconnect(PlayerBase player)
    {
        OnActivate(player);
    }

    // ---- On deactivation (modifierbase.c:191) -------------------------------
    override void OnDeactivate(PlayerBase player)
    {
        if (player.GetIdentity())
        {
            Param1<string> msg = new Param1<string>("You recovered from rust sickness.");
            GetGame().RPCSingleParam(player, ERPCs.RPC_USER_ACTION_MESSAGE, msg, true, player.GetIdentity());
        }
    }
}

// =============================================================================
// 2. REGISTRATION
// =============================================================================
// ModifiersManager builds every modifier in Init(), called from its constructor
// (modifiersmanager.c:80-90). AddModifier takes an instance, not a typename
// (modifiersmanager.c:188).
modded class ModifiersManager
{
    override void Init()
    {
        super.Init();
        AddModifier(new MyMod_RustModifier);
    }
}

// =============================================================================
// 3. PlayerBase helpers
// =============================================================================
modded class PlayerBase
{
    // Infect this player (call from an item, an action, etc.).
    // InsertAgent: playerbase.c:8115
    void MyMod_InjectRustAgent(int amount)
    {
        if (!GetGame().IsServer())
            return;
        InsertAgent(eAgents.FOOD_POISON, amount);
        // ActivateCondition sees it on the next inactive tick
    }

    // Cure (e.g. after taking an antidote).
    // RemoveAgent: playerbase.c:8102; DeactivateModifier: modifiersmanager.c:232
    void MyMod_CureRust()
    {
        if (!GetGame().IsServer())
            return;
        RemoveAgent(eAgents.FOOD_POISON);
        GetModifiersManager().DeactivateModifier(MYMOD_MDF_RUST);
    }
}
