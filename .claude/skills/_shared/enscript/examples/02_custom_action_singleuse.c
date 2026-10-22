// =============================================================================
// ActionMyMod_DrinkContaminate.c
// A player-initiated single-use action that appears on MyMod_CustomCanteen.
// Uses the eat animation and can only run when the canteen is in hands,
// not ruined, and has water.
//
// Placement: Scripts/4_World/Classes/UserActionsComponent/Actions/
//            ActionMyMod_DrinkContaminate.c
//
// Built on the vanilla shape of ActionTurnOnWhileInHands
//   P:\scripts\4_world\classes\useractionscomponent\actions\singleuse\actionturnonwhileinhands.c
// Base classes:
//   ActionSingleUseBase   P:\scripts\4_world\classes\useractionscomponent\actions\actionsingleusebase.c:29
//   ActionBase            P:\scripts\4_world\classes\useractionscomponent\actionbase.c:51
// =============================================================================

// ---- Action -----------------------------------------------------------------
// The default callback (ActionSingleUseBaseCB, actionsingleusebase.c:1) is used,
// so no m_CallbackClass is set here.
class ActionMyMod_DrinkContaminate : ActionSingleUseBase
{
    void ActionMyMod_DrinkContaminate()
    {
        m_CommandUID      = DayZPlayerConstants.CMD_ACTIONMOD_EAT;   // eat animation
        m_StanceMask      = DayZPlayerConstants.STANCEMASK_ERECT |
                            DayZPlayerConstants.STANCEMASK_CROUCH;
        m_Text            = "Drink (Contaminate Test)";
    }

    // ---- Conditions ---------------------------------------------------------

    // Built once by the action manager (actionbase.c:245)
    override void CreateConditionComponents()
    {
        m_ConditionItem   = new CCINonRuined;           // item in hands, not ruined (ccinonruined.c)
        m_ConditionTarget = new CCTNone;                // no world target required
    }

    // No world target: the action works on the item in hands (actionbase.c:259)
    override bool HasTarget()
    {
        return false;
    }

    // Checked on the client to show the action and on the server before it runs
    // (actionbase.c:441 and :954; actionmanagerserver.c:168).
    override bool ActionCondition(PlayerBase player, ActionTarget target, ItemBase item)
    {
        // Cast safely: prefer Class.CastTo over direct cast to avoid nullref crash.
        // No ternary allowed, so use if/else:
        MyMod_CustomCanteen canteen;
        if (!Class.CastTo(canteen, item))           // item = player.GetItemInHands()
            return false;

        if (canteen.GetQuantity() <= 0)             // itembase.c:3486
            return false;

        return player.IsAlive();
    }

    // ---- Execution (server-side) --------------------------------------------

    // animatedactionbase.c:179
    override void OnExecuteServer(ActionData action_data)
    {
        MyMod_CustomCanteen canteen;
        if (!Class.CastTo(canteen, action_data.m_MainItem))
            return;

        // Mark contaminated
        canteen.MyMod_SetContaminated(true);

        // Consume some quantity (itembase.c:3315)
        float current = canteen.GetQuantity();
        canteen.SetQuantity(current - 100);

        // Show a message on the player's screen. PlayerBase.OnRPC turns
        // ERPCs.RPC_USER_ACTION_MESSAGE + Param1<string> into MessageAction
        // (P:\scripts\4_world\entities\manbase\playerbase.c:5773).
        PlayerBase pb = action_data.m_Player;
        if (pb)
        {
            Param1<string> msg = new Param1<string>("You drank from a contaminated canteen!");
            GetGame().RPCSingleParam(pb, ERPCs.RPC_USER_ACTION_MESSAGE, msg, true, pb.GetIdentity());
        }
    }

    // ---- Optional client-side work (animatedactionbase.c:183) ---------------
    override void OnExecuteClient(ActionData action_data)
    {
        // runs on the executing client (not on other clients or server)
    }
}

// =============================================================================
// Registration takes two steps. Place the modded ActionConstructor block in
// the same file or a separate one.
// 1. Register the class in ActionConstructor.RegisterActions, so the action
//    manager builds it (P:\scripts\4_world\classes\useractionscomponent\actionconstructor.c:3-27).
// 2. Add the action to the item in SetActions(), the way ItemBase adds its own
//    (P:\scripts\4_world\entities\itembase.c:246-253).
// Without step 1, AddAction logs "Action ActionMyMod_DrinkContaminate dosn't
// exist!" and returns (itembase.c:255-262).
// =============================================================================
modded class ActionConstructor
{
    override void RegisterActions(TTypenameArray actions)    // actionconstructor.c:27
    {
        super.RegisterActions(actions);
        actions.Insert(ActionMyMod_DrinkContaminate);
    }
}

// Step 2 goes inside the class MyMod_CustomCanteen declaration
// (01_custom_item.c), not in a modded class: modded_class.md says not to
// declare class X and modded class X in the same mod.
//
// In MyMod_CustomCanteen (01_custom_item.c):
//     override void SetActions()
//     {
//         super.SetActions();
//         AddAction(ActionMyMod_DrinkContaminate);    // itembase.c:255
//         AddAction(ActionMyMod_RepairCanteen);       // 03_continuous_action.c
//     }
