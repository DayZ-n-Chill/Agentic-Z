// =============================================================================
// MyMod_Agent_Modifier.c
// Full agent + modifier stack showing how the vanilla disease system works:
//
//   AgentBase       – the "disease" that grows inside the player's pool
//   ModifierBase    – the periodic effect that fires when the disease is active
//   Registration    – via config.cpp CfgVehicles / item transferability
//   PlayerBase mods – inserting agents, checking counts, activating modifiers
//
// Agents and modifiers are SERVER-SIDE ONLY systems.
//
// Placement: Scripts/4_World/Classes/TransmissionAgents/  (agents)
//            Scripts/4_World/Classes/PlayerModifiers/      (modifiers)
//            Scripts/4_World/Entities/ManBase/              (player hooks)
//
// config.cpp (for transferability via items):
//   class CfgVehicles {
//       class MyMod_ContaminatedFood : Edible_Base {
//           agentTransferability    = 1;  // food can carry agents
//           agentTransferabilityIn  = 1;
//       };
//   };
// =============================================================================

// =============================================================================
// 1. AGENT
// =============================================================================
// Place in: Scripts/4_World/Classes/TransmissionAgents/Agents/MyMod_RustAgent.c

class MyMod_RustAgent : AgentBase
{
    void MyMod_RustAgent()
    {
        Init();
    }

    override void Init()
    {
        // eAgents enum integer – pick a value NOT used by vanilla.
        // Vanilla uses 1..512; use 1024+ for mods.
        m_Type                  = eAgents.FOOD_POISON;  // reuse vanilla for simplicity
                                                         // OR define a custom enum value

        m_Invasibility          = 5;    // grow rate when potent
        m_TransferabilityIn     = 0.2;  // 20 % chance to infect player from item
        m_TransferabilityOut    = 0.05; // 5 % chance to transfer to another item
        m_Digestibility         = 0.15; // agents digested per ml/g consumed
        m_MaxCount              = 1000; // cap
        m_AutoinfectCount       = 30;
        m_AutoinfectProbability = CalculateAutoinfectProbability(0.0001); // ~0.01%/hr

        m_DieOffSpeed           = 0.5;  // dies quickly when immune system is strong
        m_AntibioticsResistance = 0.3;  // antibiotics work well against this
        m_Potency               = EStatLevels.HIGH; // only grows if immunity is HIGH
    }
}

// =============================================================================
// 2. MODIFIER
// =============================================================================
// Place in: Scripts/4_World/Classes/PlayerModifiers/Modifiers/MyMod_RustModifier.c

class MyMod_RustModifier : ModifierBase
{
    static const float TICK_HEALTH_LOSS = 0.5; // health drained per active tick

    void MyMod_RustModifier()
    {
        // m_ID maps to eModifiers enum; vanilla uses 1..29; pick 100+ for mods
        m_ID                 = eModifiers.MDF_FOODPOISONING; // reuse for demo
        m_TickIntervalActive = 5.0;  // fire every 5 s while active
        m_IsPersistent       = true; // survive server restarts
        m_TrackActivatedTime = true;
    }

    // ---- Activation condition -----------------------------------------------
    // Called every m_TickIntervalInactive seconds; return true to activate.
    override bool ActivateCondition(PlayerBase player)
    {
        // Activate when the player has a significant amount of rust agent
        return player.GetSingleAgentCount(eAgents.FOOD_POISON) > 200;
    }

    // ---- Deactivation condition ---------------------------------------------
    // Called every m_TickIntervalActive seconds while active; return true to stop.
    override bool DeactivateCondition(PlayerBase player)
    {
        return player.GetSingleAgentCount(eAgents.FOOD_POISON) <= 50;
    }

    // ---- Effect tick --------------------------------------------------------
    // Called every m_TickIntervalActive seconds while this modifier is active.
    override void OnTick(PlayerBase player, float deltaT)
    {
        // Drain health
        player.AddHealth("", "", -TICK_HEALTH_LOSS);

        // Optionally trigger a symptom (e.g. vomit animation)
        // player.GetSymptomManager().QueueUpSymptom(SymptomIDs.SYMPTOM_NAUSEA, "");

        // Visual feedback – send a HUD warning via RPC
        if (player.GetIdentity())
        {
            Param1<string> msg = new Param1<string>("You feel the rust sickness spreading...");
            GetGame().RPCSingleParam(
                player,
                ERPCs.RPC_USER_ACTION_MESSAGE,
                msg,
                false,  // unreliable – cosmetic only
                player.GetIdentity()
            );
        }
    }

    // ---- On activation: show one-time notification --------------------------
    override void OnActivate(PlayerBase player)
    {
        super.OnActivate(player);
        if (player.GetIdentity())
        {
            Param1<string> msg = new Param1<string>("You contracted rust sickness!");
            GetGame().RPCSingleParam(player, ERPCs.RPC_USER_ACTION_MESSAGE, msg, true, player.GetIdentity());
        }
    }

    // ---- On deactivation ----------------------------------------------------
    override void OnDeactivate(PlayerBase player)
    {
        super.OnDeactivate(player);
        if (player.GetIdentity())
        {
            Param1<string> msg = new Param1<string>("You recovered from rust sickness.");
            GetGame().RPCSingleParam(player, ERPCs.RPC_USER_ACTION_MESSAGE, msg, true, player.GetIdentity());
        }
    }

    // ---- Persistence --------------------------------------------------------
    override void OnStoreSave(ParamsWriteContext ctx)
    {
        super.OnStoreSave(ctx);
        // save custom fields if any
    }

    override bool OnStoreLoad(ParamsReadContext ctx)
    {
        if (!super.OnStoreLoad(ctx))
            return false;
        return true;
    }
}

// =============================================================================
// 3. REGISTRATION in PlayerBase
// =============================================================================
// Modifiers and agents must be registered in their manager on player init.

modded class PlayerBase
{
    // ---- Register modifier so the manager knows this type exists ------------
    override void OnStoreLoad_RemotePlayerMods(ParamsReadContext ctx, int version)
    {
        super.OnStoreLoad_RemotePlayerMods(ctx, version);
    }

    // The manager is initialised in vanilla; we inject our entry here
    override void InitModifiers()
    {
        super.InitModifiers();
        GetModifiersManager().AddModifier(MyMod_RustModifier);
    }

    // ---- Helper: manually infect this player (call from item, action, etc.) -
    void MyMod_InjectRustAgent(int amount)
    {
        if (!GetGame().IsServer())
            return;
        InsertAgent(eAgents.FOOD_POISON, amount);
        // The modifier's ActivateCondition fires on next tick automatically
    }

    // ---- Helper: clear the agent (e.g. after taking an antidote) ------------
    void MyMod_CureRust()
    {
        if (!GetGame().IsServer())
            return;
        RemoveAllAgents();
        GetModifiersManager().DeactivateModifier(eModifiers.MDF_FOODPOISONING);
    }
}
