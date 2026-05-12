// =============================================================================
// MyMod_InventoryMenu.c
// A custom UIScriptedMenu (in-game overlay menu):
//   - Created from a .layout file (GUI made in Workbench/GUI Editor)
//   - Handles mouse input via ScriptedWidgetEventHandler
//   - Dynamically adds rows to a TextListboxWidget
//   - Opened from a keyboard hotkey in MissionGameplay
//
// Placement: Scripts/5_Mission/GUI/Menus/MyMod_InventoryMenu.c
//
// Layout file: GUI\Layouts\MyMod\MyMod_InventoryMenu.layout
// (Create in Workbench → Resource Browser → right-click → New → Layout)
//
// To open: GetGame().GetUIManager().EnterScriptedMenu(MENU_MYMOD_INVENTORY, null)
//   where MENU_MYMOD_INVENTORY is defined in a modded MenuID enum.
// =============================================================================

// ---- Custom menu ID (added via modded enum) ---------------------------------
// Enforce Script does not support adding values to existing enums directly;
// use a separate enum and a modded const pattern for the ID.

modded class MenuID
{
    // This opens a "gap" to avoid collision with vanilla IDs (vanilla uses 0..39)
    static const int MYMOD_INVENTORY = 1000;
}

// ---- Event handler ----------------------------------------------------------
// ScriptedWidgetEventHandler routes widget events (click, focus, drag…)
// to registered callback methods.  One handler object per menu instance.

class MyMod_InventoryMenuHandler : ScriptedWidgetEventHandler
{
    private MyMod_InventoryMenu m_Menu;

    void MyMod_InventoryMenuHandler(MyMod_InventoryMenu menu)
    {
        m_Menu = menu;
    }

    // Called when a mouse button is released over a widget with this handler
    override bool OnClick(Widget w, int x, int y, int button)
    {
        if (button != MouseState.LEFT)
            return false;

        if (w == m_Menu.m_BtnClose)
        {
            m_Menu.Close();
            return true;
        }

        if (w == m_Menu.m_BtnRefresh)
        {
            m_Menu.Refresh();
            return true;
        }

        return false;
    }

    // Called when mouse enters a widget (hover highlight)
    override bool OnMouseEnter(Widget w, int x, int y)
    {
        w.SetColor(ARGB(255, 200, 200, 100));
        return false; // return false = don't consume, let vanilla process too
    }

    override bool OnMouseLeave(Widget w, Widget enterW, int x, int y)
    {
        w.SetColor(ARGB(255, 255, 255, 255));
        return false;
    }
}

// ---- Menu -------------------------------------------------------------------
class MyMod_InventoryMenu : UIScriptedMenu
{
    // Widgets (populated in Init from layout)
    TextListboxWidget m_ItemList;
    ButtonWidget      m_BtnClose;
    ButtonWidget      m_BtnRefresh;
    TextWidget        m_LabelTitle;

    private ref MyMod_InventoryMenuHandler m_Handler;

    // ---- MenuID override ----------------------------------------------------
    override int GetID()
    {
        return MenuID.MYMOD_INVENTORY;
    }

    // ---- Build widget tree --------------------------------------------------
    // Init is called once when the menu is opened.
    // layoutRoot is set automatically by the engine from the .layout path.
    override Widget Init()
    {
        // Load the .layout file; result stored in layoutRoot
        layoutRoot = GetGame().GetWorkspace().CreateWidgets(
            "GUI\\Layouts\\MyMod\\MyMod_InventoryMenu.layout"
        );

        if (!layoutRoot)
        {
            Error("[MyMod] Failed to load MyMod_InventoryMenu.layout");
            return null;
        }

        // Grab named widgets from the layout tree
        m_ItemList   = TextListboxWidget.Cast(layoutRoot.FindAnyWidget("ItemList"));
        m_BtnClose   = ButtonWidget.Cast(layoutRoot.FindAnyWidget("BtnClose"));
        m_BtnRefresh = ButtonWidget.Cast(layoutRoot.FindAnyWidget("BtnRefresh"));
        m_LabelTitle = TextWidget.Cast(layoutRoot.FindAnyWidget("LabelTitle"));

        // Set up event handler AFTER fetching widget references
        m_Handler = new MyMod_InventoryMenuHandler(this);
        layoutRoot.SetHandler(m_Handler);

        if (m_LabelTitle)
            m_LabelTitle.SetText("Inventory");

        // Populate the list on open
        PopulateList();

        // Lock focus to this menu
        LockControls();

        return layoutRoot;
    }

    // ---- Rebuild list -------------------------------------------------------
    override void Refresh()
    {
        PopulateList();
    }

    private void PopulateList()
    {
        if (!m_ItemList)
            return;

        m_ItemList.ClearItems();

        // Walk local player's cargo recursively
        PlayerBase player = PlayerBase.Cast(GetGame().GetPlayer());
        if (!player)
            return;

        EntityAI item = player.GetInventory().GetEntityInHands();
        if (item)
            AddItemRow(item);

        for (int i = 0; i < player.GetInventory().AttachmentCount(); i++)
        {
            EntityAI attachment = player.GetInventory().GetAttachmentFromIndex(i);
            AddItemRow(attachment);
        }
    }

    private void AddItemRow(EntityAI item)
    {
        if (!item)
            return;

        string name = item.GetDisplayName();
        float  health = item.GetHealth01("", "") * 100.0;
        string healthStr = string.Format("%.0f%%", health);

        // TextListboxWidget: AddItem(text, userData_class, column, row=-1)
        m_ItemList.AddItem(name,      null, 0);
        m_ItemList.AddItem(healthStr, null, 1);
    }

    // ---- Cleanup ------------------------------------------------------------
    override void OnHide()
    {
        UnlockControls();
        super.OnHide();
    }
}

// =============================================================================
// Opening the menu from a keypress in MissionGameplay
// =============================================================================
modded class MissionGameplay
{
    override void OnKeyPress(int key)
    {
        super.OnKeyPress(key);

        // KeyCode 36 = END key (example) – pick one that is not already bound
        if (key == KeyCode.KC_END)
        {
            if (!GetGame().GetUIManager().IsMenuOpen(MenuID.MYMOD_INVENTORY))
                GetGame().GetUIManager().EnterScriptedMenu(MenuID.MYMOD_INVENTORY, null);
            else
                GetGame().GetUIManager().Back();
        }
    }
}
