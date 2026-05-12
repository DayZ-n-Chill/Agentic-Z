// =============================================================================
// ActionMyMod_RepairCanteen.c
// A continuous (hold-to-complete) action on MyMod_CustomCanteen.
// Shows the animation loop, Do() per-frame logic, progress bar integration,
// and proper cancel/interrupt handling.
//
// Placement: Scripts/4_World/Classes/UserActionsComponent/Actions/
//            ActionMyMod_RepairCanteen.c
// =============================================================================

// ---- Callback ---------------------------------------------------------------
class ActionMyMod_RepairCanteenCB : ActionContinuousBaseCB
{
    // Fires when the loop animation begins ("ActionExecStart" anim event)
    override void OnStartAnimationLoop(ActionData action_data)
    {
        super.OnStartAnimationLoop(action_data);
        // optional: play initial SFX
    }

    // Fires when the loop animation ends ("ActionExecEnd" anim event)
    override void OnEndAnimationLoop(ActionData action_data)
    {
        super.OnEndAnimationLoop(action_data);
        // optional: play completion SFX
    }
}

// ---- Action -----------------------------------------------------------------
class ActionMyMod_RepairCanteen : ActionContinuousBase
{
    static const float REPAIR_DURATION = 5.0;  // total seconds to complete

    void ActionMyMod_RepairCanteen()
    {
        m_CallbackClass   = ActionMyMod_RepairCanteenCB;
        m_CommandUID      = DayZPlayerConstants.CMD_ACTIONMOD_EAT;
        m_FullBody        = false;
        m_StanceMask      = DayZPlayerConstants.STANCEMASK_ERECT;
        m_Text            = "Repair Canteen";
        // Duration for the vanilla continuous-action progress bar
        m_LockTargetOnUse = true;
    }

    // ---- Conditions ---------------------------------------------------------

    override void CreateConditionComponents()
    {
        m_ConditionItem   = new CCINotRuined;
        m_ConditionTarget = new CCTNone;
    }

    override bool CanBePerformedServer(Man player)
    {
        MyMod_CustomCanteen canteen;
        if (!Class.CastTo(canteen, player.GetHeldItem()))
            return false;

        // Only allow if not already (nearly) full health
        return canteen.GetHealth01("", "") < 0.99;
    }

    override bool CanBePerformed(Man player)
    {
        return player.IsAlive();
    }

    override string GetText()
    {
        return m_Text;
    }

    // ---- Per-frameDo loop (server) ------------------------------------------
    // Called each server tick while the player holds the action input.
    // action_data.m_State drives the state machine: UA_INITIALIZE → UA_PROCESSING
    //   → UA_FINISHED  (or UA_CANCEL on release).

    override void Do(ActionData action_data, int state)
    {
        if (state == UA_INITIALIZE)
        {
            // First tick: store start time in action_data.m_Player (or use a static)
            action_data.m_Player.SetAnimCommandTypeModifier(0);
        }

        if (state == UA_PROCESSING)
        {
            // Accumulate time using GetGame().GetTickTime() delta
            // (action_data carries no built-in timer; use float stored on item or player)
            MyMod_CustomCanteen canteen;
            if (!Class.CastTo(canteen, action_data.m_MainItem))
            {
                action_data.m_State = UA_CANCEL;
                return;
            }

            // Example: push incremental health repair each tick
            float dt = action_data.m_Player.GetDeltaT();
            float healPerSec = (1.0 / REPAIR_DURATION) * canteen.GetMaxHealth("", "");
            canteen.AddHealth("", "", healPerSec * dt);

            // Signal completion when the item is fully repaired
            if (canteen.GetHealth01("", "") >= 0.99)
                action_data.m_State = UA_FINISHED;
        }
    }

    // ---- Finished (server) --------------------------------------------------

    override void OnFinishProgressServer(ActionData action_data)
    {
        MyMod_CustomCanteen canteen;
        if (!Class.CastTo(canteen, action_data.m_MainItem))
            return;

        canteen.SetHealth("", "", canteen.GetMaxHealth("", ""));

        // Notify player
        PlayerBase pb;
        if (Class.CastTo(pb, action_data.m_Player))
        {
            Param1<string> msg = new Param1<string>("Canteen repaired!");
            GetGame().RPCSingleParam(pb, ERPCs.RPC_USER_ACTION_MESSAGE, msg, true, pb.GetIdentity());
        }
    }

    // ---- Progress bar (client) ----------------------------------------------
    // Return a value 0..1 to drive the vanilla on-screen progress widget.

    override float GetProgress(ActionData action_data)
    {
        MyMod_CustomCanteen canteen;
        if (!Class.CastTo(canteen, action_data.m_MainItem))
            return 0;
        return canteen.GetHealth01("", "");
    }

    // Return the text shown above the progress bar
    override string GetProgressText()
    {
        return "Repairing...";
    }
}
