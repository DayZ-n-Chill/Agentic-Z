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
// Layout file: MyMod/GUI/layouts/MyMod_InventoryMenu.layout (under the mod's $PBOPREFIX$)
// (Create in Workbench → Resource Browser → right-click → New → Layout; menu path unverified on P:)
//
// To open: GetGame().GetUIManager().EnterScriptedMenu(MENU_MYMOD_INVENTORY, null)
//   // P:\scripts\3_game\tools\uimanager.c:4
// EnterScriptedMenu only works for IDs the mission knows how to build: the engine
// asks DayZGame.CreateScriptedMenu, which forwards to Mission.CreateScriptedMenu
//   // P:\scripts\3_game\dayzgame.c:1415-1421
// and vanilla MissionBase only builds vanilla IDs (switch, else null)
//   // P:\scripts\5_mission\mission\missionbase.c:198-353
// so a custom menu MUST also override CreateScriptedMenu (see bottom of file).
// =============================================================================

// ---- Custom menu ID ---------------------------------------------------------
// Vanilla menu IDs are global int constants, not an enum or a MenuID class
//   // P:\scripts\3_game\constants.c:171-223 (MENU_ANY = 1 ... MENU_UNDERGROUND_TRIGGER_EDITOR = 48)
// so a mod declares its own global constant, far above the vanilla range.
const int MENU_MYMOD_INVENTORY = 1000;

// ---- Event handler ----------------------------------------------------------
// ScriptedWidgetEventHandler routes widget events (click, focus, drag…)
// to registered callback methods.  One handler object per menu instance.
//   // P:\scripts\1_core\proto\enwidgets.c:656

class MyMod_InventoryMenuHandler : ScriptedWidgetEventHandler
{
    private MyMod_InventoryMenu m_Menu;

    void MyMod_InventoryMenuHandler(MyMod_InventoryMenu menu)
    {
        m_Menu = menu;
    }

    // Called when a widget under the handler's root is clicked
    // P:\scripts\1_core\proto\enwidgets.c:658
    override bool OnClick(Widget w, int x, int y, int button)
    {
        // P:\scripts\1_core\proto\ensystem.c:310-312 (MouseState.LEFT)
        if (button != MouseState.LEFT)
            return false;

        if (w == m_Menu.m_BtnClose)
        {
            m_Menu.Close(); // P:\scripts\3_game\tools\uiscriptedmenu.c:31
            return true;
        }

        if (w == m_Menu.m_BtnRefresh)
        {
            m_Menu.Refresh();
            return true;
        }

        return false;
    }

    // Hover highlight. The handler is set on layoutRoot (see Init), so it receives
    // mouse enter/leave for EVERY widget under the root, the root included. Only
    // the two buttons may be tinted, or the whole menu turns yellow.
    private int m_HoverColor; // the button's own layout color, restored on leave

    private bool IsHoverButton(Widget w)
    {
        return w && (w == m_Menu.m_BtnClose || w == m_Menu.m_BtnRefresh);
    }

    // P:\scripts\1_core\proto\enwidgets.c:665
    override bool OnMouseEnter(Widget w, int x, int y)
    {
        if (!IsHoverButton(w))
            return false;

        // Widget.GetColor / SetColor: P:\scripts\1_core\proto\enwidgets.c:145, :144
        // ARGB: P:\scripts\1_core\proto\proto.c:322
        m_HoverColor = w.GetColor();
        w.SetColor(ARGB(255, 200, 200, 100));
        return false; // return false = don't consume, let vanilla process too
    }

    // P:\scripts\1_core\proto\enwidgets.c:666
    override bool OnMouseLeave(Widget w, Widget enterW, int x, int y)
    {
        if (!IsHoverButton(w))
            return false;

        // Restore the color from the layout instead of forcing white
        w.SetColor(m_HoverColor);
        return false;
    }
}

// ---- Menu -------------------------------------------------------------------
// P:\scripts\3_game\tools\uiscriptedmenu.c:66
class MyMod_InventoryMenu : UIScriptedMenu
{
    // Widgets (populated in Init from layout)
    TextListboxWidget m_ItemList;   // P:\scripts\1_core\proto\enwidgets.c:439
    ButtonWidget      m_BtnClose;   // P:\scripts\1_core\proto\enwidgets.c:381
    ButtonWidget      m_BtnRefresh;
    TextWidget        m_LabelTitle; // P:\scripts\1_core\proto\enwidgets.c:189

    private ref MyMod_InventoryMenuHandler m_Handler;

    // ---- MenuID override ----------------------------------------------------
    // Optional: CreateScriptedMenu already calls SetID(id) and the base GetID
    // returns it (P:\scripts\3_game\tools\uiscriptedmenu.c:146-153).
    override int GetID()
    {
        return MENU_MYMOD_INVENTORY;
    }

    // ---- Build widget tree --------------------------------------------------
    // Init is called once when the menu is created; script must create the widgets,
    // assign layoutRoot and return it ("create widgets here and return layout root
    // Widget") // P:\scripts\3_game\tools\uiscriptedmenu.c:69, :161-166
    override Widget Init()
    {
        // Load the .layout file; vanilla does the same:
        //   // P:\scripts\5_mission\gui\helpscreen.c:21
        // GetWorkspace: P:\scripts\3_game\global\game.c:85; CreateWidgets: P:\scripts\1_core\proto\enwidgets.c:181
        layoutRoot = GetGame().GetWorkspace().CreateWidgets("MyMod/GUI/layouts/MyMod_InventoryMenu.layout");

        if (!layoutRoot)
        {
            Error("[MyMod] Failed to load MyMod_InventoryMenu.layout"); // P:\scripts\1_core\proto\endebug.c:90
            return null;
        }

        // Grab named widgets from the layout tree
        // FindAnyWidget: P:\scripts\1_core\proto\enwidgets.c:169
        m_ItemList   = TextListboxWidget.Cast(layoutRoot.FindAnyWidget("ItemList"));
        m_BtnClose   = ButtonWidget.Cast(layoutRoot.FindAnyWidget("BtnClose"));
        m_BtnRefresh = ButtonWidget.Cast(layoutRoot.FindAnyWidget("BtnRefresh"));
        m_LabelTitle = TextWidget.Cast(layoutRoot.FindAnyWidget("LabelTitle"));

        // Set up event handler AFTER fetching widget references.
        // A handler on the root also receives events of child widgets: vanilla
        // CTKeyframe sets it on m_Root and tests child widgets in OnFocus
        //   // P:\scripts\5_mission\gui\cameratools\ctkeyframe.c:42, :146-160
        m_Handler = new MyMod_InventoryMenuHandler(this);
        layoutRoot.SetHandler(m_Handler); // P:\scripts\1_core\proto\enwidgets.c:172

        if (m_LabelTitle)
            m_LabelTitle.SetText("Inventory"); // P:\scripts\1_core\proto\enwidgets.c:195

        // Populate the list on open
        PopulateList();

        // No LockControls() here: the base OnShow() already calls it and the base
        // OnHide() calls UnlockControls()
        //   // P:\scripts\3_game\tools\uiscriptedmenu.c:173-192

        return layoutRoot;
    }

    // ---- Rebuild list -------------------------------------------------------
    // P:\scripts\3_game\tools\uiscriptedmenu.c:59 (UIMenuPanel.Refresh)
    override void Refresh()
    {
        super.Refresh();
        PopulateList();
    }

    private void PopulateList()
    {
        if (!m_ItemList)
            return;

        m_ItemList.ClearItems(); // P:\scripts\1_core\proto\enwidgets.c:427

        // Walk local player's hands and attachments
        // GetGame(): P:\scripts\3_game\gameplay.c:636; GetPlayer() returns DayZPlayer: P:\scripts\3_game\global\game.c:944
        PlayerBase player = PlayerBase.Cast(GetGame().GetPlayer());
        if (!player)
            return;

        // GetEntityInHands lives on Man / HumanInventory, not on GameInventory
        //   // P:\scripts\3_game\entities\man.c:83
        EntityAI item = player.GetEntityInHands();
        if (item)
            AddItemRow(item);

        // GetInventory: P:\scripts\3_game\entities\entityai.c:1884
        // AttachmentCount / GetAttachmentFromIndex: P:\scripts\3_game\systems\inventory\inventory.c:205, :220
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

        string name = item.GetDisplayName(); // P:\scripts\3_game\entities\object.c:476
        // P:\scripts\3_game\entities\object.c:1001; on a client this reads the replicated
        // value (accuracy on client unverified on P:)
        int health = Math.Round(item.GetHealth01("", "") * 100.0); // P:\scripts\1_core\proto\enmath.c:413
        string healthStr = health.ToString() + "%";

        // TextListboxWidget.AddItem(text, userData, column, row = -1) INSERTS A NEW ROW
        // and returns its index; fill further columns of that row with SetItem
        //   // P:\scripts\1_core\proto\enwidgets.c:441-443; vanilla: P:\scripts\5_mission\gui\helpscreen.c:28-29
        int row = m_ItemList.AddItem(name, null, 0);
        m_ItemList.SetItem(row, healthStr, null, 1);
    }

    // ---- Cleanup ------------------------------------------------------------
    // P:\scripts\3_game\tools\uiscriptedmenu.c:184
    override void OnHide()
    {
        super.OnHide(); // base calls UnlockControls(); do not call it twice
    }
}

// =============================================================================
// Building and opening the menu in MissionGameplay
// =============================================================================
modded class MissionGameplay
{
    // Build our menu when the engine asks for MENU_MYMOD_INVENTORY.
    // P:\scripts\5_mission\mission\missionbase.c:198, :348-353 (vanilla: new + SetID)
    override UIScriptedMenu CreateScriptedMenu(int id)
    {
        UIScriptedMenu menu = super.CreateScriptedMenu(id);
        if (!menu && id == MENU_MYMOD_INVENTORY)
        {
            menu = new MyMod_InventoryMenu;
            menu.SetID(id); // P:\scripts\3_game\tools\uiscriptedmenu.c:146
        }

        return menu;
    }

    // P:\scripts\5_mission\mission\missiongameplay.c:742; DayZGame forwards every key
    // press to the mission, also while a menu is open: P:\scripts\3_game\dayzgame.c:2848, :2914-2917
    override void OnKeyPress(int key)
    {
        super.OnKeyPress(key);

        // KeyCode.KC_END: P:\scripts\1_core\proto\ensystem.c:272 – pick one that is not already bound
        if (key == KeyCode.KC_END)
        {
            // Every key arrives here, also while chat (a scripted menu,
            // P:\scripts\5_mission\mission\missiongameplay.c:1247) or another menu is
            // open. Do nothing unless no menu is open or ours is the top one, so End
            // never stacks this menu on top of chat, the inventory or a code lock.
            // GetMenu returns the top-most open menu: P:\scripts\3_game\tools\uimanager.c:59
            UIScriptedMenu top = GetGame().GetUIManager().GetMenu();
            if (top && top.GetID() != MENU_MYMOD_INVENTORY)
                return;

            // IsMenuOpen: P:\scripts\3_game\tools\uimanager.c:154; Back: P:\scripts\3_game\tools\uimanager.c:62
            if (!GetGame().GetUIManager().IsMenuOpen(MENU_MYMOD_INVENTORY))
                GetGame().GetUIManager().EnterScriptedMenu(MENU_MYMOD_INVENTORY, null);
            else
                GetGame().GetUIManager().Back();
        }
    }
}
