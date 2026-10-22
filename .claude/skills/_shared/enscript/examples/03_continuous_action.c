// =============================================================================
// ActionMyMod_RepairCanteen.c
// A continuous (hold-to-complete) action on MyMod_CustomCanteen.
// The callback sets how long the hold takes; the engine runs the progress bar
// and calls OnFinishProgressServer when the time is up. Releasing the key
// cancels it.
//
// Placement: Scripts/4_World/Classes/UserActionsComponent/Actions/
//            ActionMyMod_RepairCanteen.c
//
// Built on the vanilla shape of ActionCraftArmband
//   P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actioncraftarmband.c
// Base classes:
//   ActionContinuousBaseCB, ActionContinuousBase
//     P:\scripts\4_world\classes\useractionscomponent\actions\actioncontinuousbase.c:1 and :120
//   CAContinuousTime
//     P:\scripts\4_world\classes\useractionscomponent\actioncomponents\cacontinuoustime.c:1
// =============================================================================

// ---- Callback ---------------------------------------------------------------
// The action component decides when the action completes. CAContinuousTime
// completes after a fixed number of seconds (cacontinuoustime.c:9).
class ActionMyMod_RepairCanteenCB : ActionContinuousBaseCB
{
    override void CreateActionComponent()
    {
        m_ActionData.m_ActionComponent = new CAContinuousTime(ActionMyMod_RepairCanteen.REPAIR_DURATION);
    }
}

// ---- Action -----------------------------------------------------------------
class ActionMyMod_RepairCanteen : ActionContinuousBase
{
    static const float REPAIR_DURATION = 5.0;  // total seconds to complete

    void ActionMyMod_RepairCanteen()
    {
        m_CallbackClass   = ActionMyMod_RepairCanteenCB;
        m_CommandUID      = DayZPlayerConstants.CMD_ACTIONFB_CRAFTING;   // as actioncraftarmband.c:14
        m_FullBody        = true;
        m_StanceMask      = DayZPlayerConstants.STANCEMASK_CROUCH;
        m_Text            = "Repair Canteen";
    }

    // ---- Conditions ---------------------------------------------------------

    override void CreateConditionComponents()
    {
        m_ConditionItem   = new CCINonRuined;           // ccinonruined.c
        m_ConditionTarget = new CCTSelf;                // as actioncraftarmband.c:24
    }

    override bool HasTarget()
    {
        return false;
    }

    // Client shows the action, server re-checks it (actionbase.c:441 and :954)
    override bool ActionCondition(PlayerBase player, ActionTarget target, ItemBase item)
    {
        MyMod_CustomCanteen canteen;
        if (!Class.CastTo(canteen, item))           // item = player.GetItemInHands()
            return false;

        // Only allow if not already (nearly) full health
        // GetHealth01(zone, type): P:\scripts\3_game\entities\object.c:1001
        return canteen.GetHealth01("", "") < 0.99;
    }

    // ---- Animation loop hooks (optional, actioncontinuousbase.c:208 and :228)
    override void OnStartAnimationLoop(ActionData action_data)
    {
        super.OnStartAnimationLoop(action_data);
        // optional: start a looping sound on the client
    }

    override void OnEndAnimationLoop(ActionData action_data)
    {
        super.OnEndAnimationLoop(action_data);
        // optional: stop the looping sound
    }

    // ---- Finished (server, actioncontinuousbase.c:289) ----------------------
    // Runs once when CAContinuousTime reaches REPAIR_DURATION.

    override void OnFinishProgressServer(ActionData action_data)
    {
        MyMod_CustomCanteen canteen;
        if (!Class.CastTo(canteen, action_data.m_MainItem))
            return;

        // SetHealthMax(zone, type): object.c:1105
        canteen.SetHealthMax("", "");

        // Show a message on the player's screen (handled by PlayerBase.OnRPC,
        // P:\scripts\4_world\entities\manbase\playerbase.c:5773)
        PlayerBase pb = action_data.m_Player;
        if (pb)
        {
            Param1<string> msg = new Param1<string>("Canteen repaired!");
            GetGame().RPCSingleParam(pb, ERPCs.RPC_USER_ACTION_MESSAGE, msg, true, pb.GetIdentity());
        }
    }
}

// =============================================================================
// Registration takes two steps, as in 02_custom_action_singleuse.c:
// 1. Register the class in ActionConstructor.RegisterActions
//    (P:\scripts\4_world\classes\useractionscomponent\actionconstructor.c:27).
//    Without it AddAction finds no action and the hold-to-repair never appears.
// 2. Add the action in SetActions() (itembase.c:246-255).
// =============================================================================
modded class ActionConstructor
{
    override void RegisterActions(TTypenameArray actions)
    {
        super.RegisterActions(actions);
        actions.Insert(ActionMyMod_RepairCanteen);
    }
}

modded class MyMod_CustomCanteen
{
    override void SetActions()
    {
        super.SetActions();
        AddAction(ActionMyMod_RepairCanteen);
    }
}
