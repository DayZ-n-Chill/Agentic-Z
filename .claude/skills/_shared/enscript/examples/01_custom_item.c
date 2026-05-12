// =============================================================================
// MyMod_CustomCanteen.c
// Custom canteen item: quantity (liquid), custom liquid type filtering,
// NetSync for a "contamination" state, full persistence with version guard.
//
// Placement: Scripts/4_World/Entities/ItemBase/MyMod_CustomCanteen.c
//
// config.cpp (excerpt – do NOT put this inside the .c file):
//   class CfgVehicles {
//       class Bottle_Base;
//       class MyMod_CustomCanteen : Bottle_Base {
//           scope = 2;
//           displayName = "Tactical Canteen";
//           descriptionShort = "A military surplus canteen. Holds 1000 ml.";
//           model = "\dz\gear\containers\canteen.p3d";
//           weight = 168;
//           itemSize[] = {2,2};
//           quantityBar = 1;
//           varQuantityInit = 500; varQuantityMin = 0; varQuantityMax = 1000;
//           liquidTypesMask = 2; // LIQUID_WATER only
//       };
//   };
// =============================================================================

// ---- persistence version for this item; bump when adding new saved fields ----
const int MYMOD_CANTEEN_STORE_VERSION = 1;

class MyMod_CustomCanteen : Bottle_Base
{
    // -----------------------------------------------------------------------
    // NetSync / server-side state
    // -----------------------------------------------------------------------
    protected bool  m_IsContaminated;       // synced to clients
    protected float m_ContaminationLevel;   // server only (not synced, not saved)

    // -----------------------------------------------------------------------
    // Init – register net-sync variables AFTER calling super
    // -----------------------------------------------------------------------
    override void Init()
    {
        super.Init();

        // Registers a bool to be included in the NetSync packet.
        // Name MUST exactly match the member variable name (string).
        RegisterNetSyncVariableBool("m_IsContaminated");
    }

    // -----------------------------------------------------------------------
    // Server-side: mark the canteen as contaminated and push to clients
    // -----------------------------------------------------------------------
    void MyMod_SetContaminated(bool state)
    {
        if (!GetGame().IsServer())
            return;

        m_IsContaminated = state;
        SetSynchDirty();    // schedule a NetSync packet
    }

    // -----------------------------------------------------------------------
    // Client-side: called after every NetSync packet with fresh values
    // -----------------------------------------------------------------------
    override void OnVariablesSynchronized()
    {
        super.OnVariablesSynchronized();

        // m_IsContaminated is now up-to-date on the client
        if (m_IsContaminated)
        {
            // e.g. apply a dirty texture selection
            SetObjectTexture(0, "path\\to\\dirty_overlay.paa");
        }
        else
        {
            SetObjectTexture(0, "");
        }
    }

    // -----------------------------------------------------------------------
    // Gameplay hook: when the player drinks from this item
    // -----------------------------------------------------------------------
    override void OnApply(PlayerBase player)
    {
        super.OnApply(player);

        if (m_IsContaminated && GetGame().IsServer())
        {
            // Insert a cholera agent.  Agent type IDs are defined in eAgents enum.
            player.InsertAgent(eAgents.CHOLERA, 50);
        }
    }

    // -----------------------------------------------------------------------
    // Persistence – SAVE
    // Always call super first, then write your own fields in order.
    // -----------------------------------------------------------------------
    override void OnStoreSave(ParamsWriteContext ctx)
    {
        super.OnStoreSave(ctx);

        // Write version header so we can guard reads on load
        ctx.Write(MYMOD_CANTEEN_STORE_VERSION);
        ctx.Write(m_IsContaminated);
    }

    // -----------------------------------------------------------------------
    // Persistence – LOAD
    // Read fields in the same order they were written.
    // NEVER read more than was written; guard new fields with version checks.
    // -----------------------------------------------------------------------
    override bool OnStoreLoad(ParamsReadContext ctx, int version)
    {
        if (!super.OnStoreLoad(ctx, version))
            return false;

        int myVersion;
        if (!ctx.Read(myVersion))
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
    override void EEItemPickedUp(bool player_droped_b)
    {
        super.EEItemPickedUp(player_droped_b);
        // e.g. log pickup for admin analytics (server-side)
    }

    override void EEItemDropped()
    {
        super.EEItemDropped();
    }

    override void OnItemLocationChanged(EntityAI old_owner, EntityAI new_owner)
    {
        super.OnItemLocationChanged(old_owner, new_owner);
        // Fires when item moves between inventories (server + client)
    }

    // -----------------------------------------------------------------------
    // Destruction: release any ref-counted resources created in Init
    // -----------------------------------------------------------------------
    void ~MyMod_CustomCanteen()
    {
        // Nothing to do here for this example, but the destructor is available.
    }
}
