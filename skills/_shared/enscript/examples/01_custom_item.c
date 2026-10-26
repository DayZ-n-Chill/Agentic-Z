// =============================================================================
// MyMod_CustomCanteen.c
// Custom canteen item: quantity (liquid), custom liquid type filtering,
// NetSync for a "contamination" state, full persistence with version guard.
//
// Placement: Scripts/4_World/Entities/ItemBase/MyMod_CustomCanteen.c
//
// Checked against vanilla DayZ on P:\ (paths cited inline as P:\...:line).
//
// config.cpp (excerpt – do NOT put this inside the .c file):
//   class CfgVehicles {
//       class Bottle_Base;  // P:\DZ\gear\drinks\config.cpp:25 (vanilla Canteen derives from it, :26)
//       class MyMod_CustomCanteen : Bottle_Base {
//           scope = 2;
//           displayName = "Tactical Canteen";
//           descriptionShort = "A military surplus canteen. Holds 1000 ml.";
//           model = "\dz\gear\drinks\Canteen.p3d";   // P:\DZ\gear\drinks\config.cpp:31
//           weight = 168;
//           itemSize[] = {2,2};                      // P:\DZ\gear\drinks\config.cpp:41
//           quantityBar = 1;                         // read at P:\scripts\4_world\entities\itembasetype.c:74 (Bottle_Base already sets it, P:\DZ\data\config.cpp:3525)
//           varQuantityInit = 500; varQuantityMin = 0; varQuantityMax = 1000;   // P:\DZ\gear\drinks\config.cpp:47-49
//           varLiquidTypeInit = 512;                 // LIQUID_WATER = 512, P:\scripts\3_game\constants.c:578; read at itembasetype.c:82
//           liquidContainerType = "512";             // bitmask of accepted liquids; read at P:\scripts\4_world\entities\itembasetype.c:80
//           // SetObjectTexture(0, ...) below swaps hiddenSelections[0]. Vanilla Canteen
//           // declares no hiddenSelections (P:\DZ\gear\drinks\config.cpp:26-55), so add
//           // hiddenSelections[] = {"<selection>"}; with a selection your model has.
//           // UNVERIFIED: which named selections canteen.p3d contains (binary model).
//       };
//   };
// =============================================================================

// ---- persistence version for this item; bump when adding new saved fields ----
const int MYMOD_CANTEEN_STORE_VERSION = 1;

class MyMod_CustomCanteen : Bottle_Base // P:\scripts\4_world\entities\itembase\edible_base\bottle_base.c:7 (Bottle_Base extends Edible_Base)
{
    // -----------------------------------------------------------------------
    // NetSync / server-side state
    // -----------------------------------------------------------------------
    protected bool  m_IsContaminated;       // synced to clients
    protected float m_ContaminationLevel;   // server only (not synced, not saved)

    // -----------------------------------------------------------------------
    // Constructor – register net-sync variables here. EntityAI has no Init()
    // to override; vanilla Bottle_Base registers its own in the constructor
    // (P:\scripts\4_world\entities\itembase\edible_base\bottle_base.c:42-46).
    // Parent constructors run first automatically, so no super call is needed.
    // -----------------------------------------------------------------------
    void MyMod_CustomCanteen()
    {
        // Registers a bool to be included in the NetSync packet.
        // Name MUST exactly match the member variable name (string).
        RegisterNetSyncVariableBool("m_IsContaminated"); // P:\scripts\3_game\entities\entityai.c:2832
    }

    // -----------------------------------------------------------------------
    // Server-side: mark the canteen as contaminated and push to clients
    // -----------------------------------------------------------------------
    void MyMod_SetContaminated(bool state)
    {
        if (!GetGame().IsServer()) // P:\scripts\3_game\global\game.c:1120
            return;

        m_IsContaminated = state;
        SetSynchDirty();    // schedule a NetSync packet; MP server only, P:\scripts\3_game\entities\entityai.c:3063-3064
    }

    // -----------------------------------------------------------------------
    // Client-side: called after every NetSync packet with fresh values
    // P:\scripts\3_game\entities\entityai.c:3066-3069; Bottle_Base overrides it too (bottle_base.c:137)
    // -----------------------------------------------------------------------
    override void OnVariablesSynchronized()
    {
        super.OnVariablesSynchronized();

        // m_IsContaminated is now up-to-date on the client
        if (m_IsContaminated)
        {
            // e.g. apply a dirty texture to hiddenSelections[0]
            // P:\scripts\3_game\entities\entityai.c:2880-2881
            SetObjectTexture(0, "path\\to\\dirty_overlay.paa");
        }
        else
        {
            SetObjectTexture(0, ""); // empty string clears it, as vanilla does at P:\scripts\4_world\entities\itembase\blowtorch.c:50
        }
    }

    // -----------------------------------------------------------------------
    // Gameplay hook: when the player drinks from this item.
    // Drinking calls Edible_Base.Consume -> OnConsume
    // (P:\scripts\4_world\entities\itembase\edible_base.c:95-103), reached from
    // PlayerBase.Consume (P:\scripts\4_world\entities\manbase\playerbase.c:7743),
    // which the drink action calls on the server only
    // (P:\scripts\4_world\classes\useractionscomponent\actioncomponents\cacontinuousquantityedible.c:52-58).
    // Note: ItemBase.OnApply (itembase.c:4510) is only called by injector actions, not drinking.
    // -----------------------------------------------------------------------
    override void OnConsume(float amount, PlayerBase consumer)
    {
        super.OnConsume(amount, consumer);

        if (m_IsContaminated && GetGame().IsServer())
        {
            // Insert a cholera agent.  Agent type IDs are defined in eAgents enum
            // (CHOLERA = 1, P:\scripts\3_game\enums\eagents.c:5).
            consumer.InsertAgent(eAgents.CHOLERA, 50); // P:\scripts\4_world\entities\manbase\playerbase.c:8115
        }
    }

    // -----------------------------------------------------------------------
    // Persistence – SAVE (server only; P:\scripts\3_game\entities\entityai.c:2910)
    // Always call super first, then write your own fields in order.
    // -----------------------------------------------------------------------
    override void OnStoreSave(ParamsWriteContext ctx) // ParamsWriteContext = Serializer, P:\scripts\3_game\gameplay.c:16
    {
        super.OnStoreSave(ctx);

        // Write version header so we can guard reads on load
        ctx.Write(MYMOD_CANTEEN_STORE_VERSION); // Serializer.Write, P:\scripts\1_core\proto\serializer.c:57
        ctx.Write(m_IsContaminated);
    }

    // -----------------------------------------------------------------------
    // Persistence – LOAD (P:\scripts\3_game\entities\entityai.c:2978; ItemBase override at itembase.c:3089)
    // Read fields in the same order they were written.
    // NEVER read more than was written; guard new fields with version checks.
    // -----------------------------------------------------------------------
    override bool OnStoreLoad(ParamsReadContext ctx, int version)
    {
        if (!super.OnStoreLoad(ctx, version))
            return false;

        int myVersion;
        if (!ctx.Read(myVersion)) // Serializer.Read returns bool, P:\scripts\1_core\proto\serializer.c:58
            return false;

        // Guard: if this save pre-dates our mod, leave defaults
        if (myVersion < 1)
            return true;

        if (!ctx.Read(m_IsContaminated))
            return false;

        // Guard: if a future field gets added in version 2, check here:
        // if (myVersion < 2) return true;
        // if (!ctx.Read(m_SomeFutureField)) return false;

        return true;
    }

    // -----------------------------------------------------------------------
    // Vanilla hooks – always call super, even when adding nothing
    // -----------------------------------------------------------------------
    override void OnInventoryEnter(Man player) // P:\scripts\4_world\entities\itembase.c:3902
    {
        super.OnInventoryEnter(player);
        // e.g. log pickup for admin analytics (guard with IsServer() for server-side work)
    }

    override void OnInventoryExit(Man player) // P:\scripts\4_world\entities\itembase.c:3914
    {
        super.OnInventoryExit(player);
    }

    override void OnItemLocationChanged(EntityAI old_owner, EntityAI new_owner) // P:\scripts\3_game\entities\entityai.c:970; ItemBase override itembase.c:1162
    {
        super.OnItemLocationChanged(old_owner, new_owner);
        // Fires when item moves between inventories; called from EntityAI.EEItemLocationChanged
        // (P:\scripts\3_game\entities\entityai.c:976-979). UNVERIFIED on P:: which machines the
        // engine calls EEItemLocationChanged on (believed server + client).
    }

    // -----------------------------------------------------------------------
    // Destruction: release any ref-counted resources created in the constructor
    // -----------------------------------------------------------------------
    void ~MyMod_CustomCanteen()
    {
        // Nothing to do here for this example, but the destructor is available.
    }
}
