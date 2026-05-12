// =============================================================================
// ActionMyMod_DrinkContaminate.c
// A player-initiated single-use action that appears on MyMod_CustomCanteen.
// Uses the "hands" animation command (pickup-style) and can only execute
// when the item is in hands and has water.
//
// Placement: Scripts/4_World/Classes/UserActionsComponent/Actions/
//            ActionMyMod_DrinkContaminate.c
//
// Registration inside MyMod_CustomCanteen (same or separate file):
//   override void GetActions(typename action_input_type, out array<ActionBase_Basic> actions)
//   {
//       super.GetActions(action_input_type, actions);
//       if (action_input_type == DefaultDamageInput)
//           actions.Insert(ActionMyMod_DrinkContaminate.Cast(
//               GetGame().ConfigGetInt("CfgVehicles ... ActionMyMod_DrinkContaminate")));
//   }
//
// The preferred modern way is via GetActions / SetActions on the item:
// =============================================================================

// ---- Callback ---------------------------------------------------------------
// Callbacks are instantiated per-player per-action and carry the state machine.
// For single-use, the default ActionSingleUseBaseCB is usually sufficient.
// Override only when you need custom animation hooks or sound triggers.

class ActionMyMod_DrinkContaminateCB : ActionSingleUseBaseCB
{
    // Called at the animation "ActionExec" event keyframe
    override void OnAnimationEventInternalProcess(int user_data)
    {
        super.OnAnimationEventInternalProcess(user_data);
        // additional SFX / VFX here if needed
    }
}

// ---- Action -----------------------------------------------------------------
class ActionMyMod_DrinkContaminate : ActionSingleUseBase
{
    void ActionMyMod_DrinkContaminate()
    {
        m_CallbackClass   = ActionMyMod_DrinkContaminateCB;
        m_CommandUID      = DayZPlayerConstants.CMD_ACTIONMOD_EAT;   // eat animation
        m_FullBody        = false; // upper-body only
        m_StanceMask      = DayZPlayerConstants.STANCEMASK_ERECT |
                            DayZPlayerConstants.STANCEMASK_CROUCH;
        m_Text            = "Drink (Contaminate Test)";
    }

    // ---- Conditions ---------------------------------------------------------

    // Which target component class must match for the action to be offered
    override void CreateConditionComponents()
    {
        m_ConditionItem   = new CCINotRuined;           // item in hands, not ruined
        m_ConditionTarget = new CCTNone;                // no world target required
    }

    // Additional arbitrary condition evaluated every frame to show/hide action
    override bool HasProperTarget(ActionData action_data)
    {
        return true;
    }

    override bool CanBePerformedServer(Man player)
    {
        // Cast safely – prefer Class.CastTo over direct cast to avoid nullref crash.
        // No ternary allowed, so use if/else:
        MyMod_CustomCanteen canteen;
        if (!Class.CastTo(canteen, player.GetHeldItem()))
            return false;

        if (canteen.GetQuantity() <= 0)
            return false;

        return true;
    }

    override bool CanBePerformed(Man player)
    {
        return player.IsAlive();
    }

    override string GetText()
    {
        return m_Text;
    }

    // ---- Execution (server-side) --------------------------------------------

    override void OnExecuteServer(ActionData action_data)
    {
        MyMod_CustomCanteen canteen;
        if (!Class.CastTo(canteen, action_data.m_MainItem))
            return;

        // Mark contaminated
        canteen.MyMod_SetContaminated(true);

        // Consume some quantity (reduce quantity on the item)
        float current = canteen.GetQuantity();
        canteen.SetQuantity(current - 100);

        // Notify the player via RPC chat message
        PlayerBase pb;
        if (Class.CastTo(pb, action_data.m_Player))
        {
            Param1<string> msg = new Param1<string>("You drank from a contaminated canteen!");
            GetGame().RPCSingleParam(pb, ERPCs.RPC_USER_ACTION_MESSAGE, msg, true, pb.GetIdentity());
        }
    }

    // ---- Optional client-side preview (e.g. disable crosshair) --------------
    override void OnExecuteClient(ActionData action_data)
    {
        // runs on the executing client (not on other clients or server)
    }
}

// =============================================================================
// Registration  – add to the item via its GetActions override
// Place this modded block in the same file or a separate one.
// =============================================================================
modded class MyMod_CustomCanteen
{
    // The action system calls this to build the action list for the item.
    // action_input_type maps to the input device class (mouse, gamepad, etc.)
    override void GetActions(typename action_input_type, out array<ActionBase_Basic> actions)
    {
        super.GetActions(action_input_type, actions);

        if (action_input_type == DefaultDamageInput)
        {
            // Lazy-init the global action object (shared across all item instances)
            ActionManagerBase.AddAction(ActionMyMod_DrinkContaminate);
        }
    }
}
