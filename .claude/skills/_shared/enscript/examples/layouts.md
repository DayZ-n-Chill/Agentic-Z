# Example layouts: what they are and their script companions

The three `.layout` examples start with their root widget, like every vanilla layout in `P:\gui\layouts\`: no BOM and no comment lines. Their notes and companion scripts live here instead, so a copied layout passes the repo's `.layout` check (`hooks/edit_check.py`) unchanged.

Copy a layout to your mod as `MyMod/gui/layouts/<name>.layout` (the `gui/` folder at the root of a `/dayz-new-mod` scaffold, whose `$PBOPREFIX$` is the mod name) and load that same path with `GetGame().GetWorkspace().CreateWidgets(path, parent)` (`GetWorkspace`, `P:\scripts\3_game\global\game.c:85`; `CreateWidgets`, `P:\scripts\1_core\proto\enwidgets.c:181`). The format is described in `../references/gui_layout.md`.

Position values whose exact toggle (`hexactpos`, `vexactpos`) is 0 are fractions (0..1) of the parent, not pixels (`../references/gui_layout.md`, "Coordinate System"). A pixel offset such as `16` needs the toggle at 1. With `halign center_ref` or `right_ref` (and `valign center_ref` or `bottom_ref`) the position is an offset from that anchor, so `0` centres the widget and `16` sits 16 px in from the right or bottom edge.

## Contents

- [11: HUD overlay with plain text](#11-hud-overlay-with-plain-text)
- [12: Menu with a filter, a list and buttons](#12-menu-with-a-filter-a-list-and-buttons)
- [13: Item inspect panel](#13-item-inspect-panel)

---

## 11: HUD overlay with plain text

`11_hud_plain_text.layout`: three text labels (`LabelMain`, `LabelSub`, `LabelWarning`) that a modded HUD updates each frame. Save it as `MyMod/gui/layouts/mymod_hud_overlay.layout`.

Mod `IngameHud`, not `Hud`. `Hud.Init` is an empty base method (`P:\scripts\3_game\gameplay.c:640`) and `IngameHud.Init` does not call `super` (`P:\scripts\5_mission\gui\ingamehud.c:143`), so a `modded class Hud` override never runs. `IngameHud.Update(float timeslice)` is at `ingamehud.c:1141`. Wrap the class in `#ifndef NO_GUI` (see `../patterns/modded_class.md`).

```c
// Scripts/5_Mission/MyMod_Hud.c
#ifndef NO_GUI
modded class IngameHud
{
    protected TextWidget m_MyMod_LblStatus;
    protected TextWidget m_MyMod_LblSub;
    protected TextWidget m_MyMod_LblWarn;

    override void Init(Widget hud_panel_widget)
    {
        super.Init(hud_panel_widget);
        Widget overlay = GetGame().GetWorkspace().CreateWidgets("MyMod/gui/layouts/mymod_hud_overlay.layout", hud_panel_widget);
        m_MyMod_LblStatus = TextWidget.Cast(overlay.FindAnyWidget("LabelMain"));
        m_MyMod_LblSub    = TextWidget.Cast(overlay.FindAnyWidget("LabelSub"));
        m_MyMod_LblWarn   = TextWidget.Cast(overlay.FindAnyWidget("LabelWarning"));
    }

    override void Update(float timeslice)
    {
        super.Update(timeslice);
        PlayerBase player = PlayerBase.Cast(GetGame().GetPlayer());
        if (!player || !m_MyMod_LblStatus)
            return;
        m_MyMod_LblStatus.SetText(string.Format("HP: %1", Math.Round(player.GetHealth("", "Health"))));
        m_MyMod_LblSub.SetText(string.Format("Blood: %1", Math.Round(player.GetHealth("", "Blood"))));
        m_MyMod_LblWarn.Show(player.GetHealth("", "Health") < 20.0);
    }
}
#endif
```

`FindAnyWidget` is at `enwidgets.c:169`, `TextWidget.SetText` at `:195` and `Widget.Show` at `:125`.

---

## 12: Menu with a filter, a list and buttons

`12_menu_interactions.layout`: an `EditBoxWidgetClass` filter (`EditFilter`), a two-column `TextListboxWidgetClass` (`ItemList`), a detail label (`LabelDetail`) and two buttons (`BtnRefresh`, and `BtnClose` with `userID 1`). Save it as `MyMod/gui/layouts/mymod_itembrowser.layout`.

The event handlers are the `UIScriptedMenu` ones: `OnClick(Widget w, int x, int y, int button)`, `OnChange(Widget w, int x, int y, bool finished)` and `OnItemSelected(Widget w, int x, int y, int row, int column, int oldRow, int oldColumn)` (`P:\scripts\3_game\tools\uiscriptedmenu.c:238`, `:478` and `:298`).

```c
// Scripts/5_Mission/GUI/MyMod_ItemBrowserMenu.c
class MyMod_ItemBrowserMenu : UIScriptedMenu
{
    protected TextListboxWidget m_List;
    protected EditBoxWidget     m_Filter;
    protected TextWidget        m_Detail;

    override Widget Init()
    {
        layoutRoot = GetGame().GetWorkspace().CreateWidgets("MyMod/gui/layouts/mymod_itembrowser.layout");
        m_Filter = EditBoxWidget.Cast(layoutRoot.FindAnyWidget("EditFilter"));
        m_List   = TextListboxWidget.Cast(layoutRoot.FindAnyWidget("ItemList"));
        m_Detail = TextWidget.Cast(layoutRoot.FindAnyWidget("LabelDetail"));
        Populate("");
        return layoutRoot;
    }

    override bool OnChange(Widget w, int x, int y, bool finished)
    {
        if (w == m_Filter)
        {
            Populate(m_Filter.GetText());
            return true;
        }
        return false;
    }

    override bool OnClick(Widget w, int x, int y, int button)
    {
        if (w.GetUserID() == 1)   // BtnClose has userID 1 in the layout
        {
            GetGame().GetUIManager().HideScriptedMenu(this);
            return true;
        }
        return false;
    }

    override bool OnItemSelected(Widget w, int x, int y, int row, int column, int oldRow, int oldColumn)
    {
        if (w == m_List)
        {
            string name;
            string count;
            m_List.GetItemText(row, 0, name);
            m_List.GetItemText(row, 1, count);
            m_Detail.SetText(name + " x" + count);
            return true;
        }
        return false;
    }

    void Populate(string filter)
    {
        m_List.ClearItems();
        int row = m_List.AddItem("Apple", null, 0);
        m_List.SetItem(row, "5", null, 1);
    }
}
```

`TextListboxWidget` has `AddItem(string text, Class userData, int column, int row = -1)`, `SetItem(int position, string text, Class userData, int column)`, `GetItemText(int row, int column, out string text)` and `ClearItems()` (`P:\scripts\1_core\proto\enwidgets.c:442`, `:443`, `:454`, `:427`). `GetUserID` is at `enwidgets.c:136`, `HideScriptedMenu` at `P:\scripts\3_game\tools\uimanager.c:10`.

---

## 13: Item inspect panel

`13_item_preview.layout`: an `ItemPreviewWidgetClass` (`ItemRender`) that renders an item in 3D, two labels and three buttons (`BtnRotateLeft`, `BtnRotateRight`, `BtnClose`). Save it as `MyMod/gui/layouts/mymod_inspect.layout`.

The engine draws the model; script sets the item with `ItemPreviewWidget.SetItem(EntityAI object)` and turns it with `SetModelOrientation(vector vOrientation)` (`P:\scripts\3_game\gameplay.c:288` and `:280`), as the vanilla inventory does (`P:\scripts\3_game\gui\inventorygrid.c:673`).

```c
// Scripts/5_Mission/GUI/MyMod_InspectMenu.c
class MyMod_InspectMenu : UIScriptedMenu
{
    protected ItemPreviewWidget m_Preview;
    protected TextWidget        m_LabelName;
    protected TextWidget        m_LabelHealth;
    protected float             m_RotY = 0;

    override Widget Init()
    {
        layoutRoot    = GetGame().GetWorkspace().CreateWidgets("MyMod/gui/layouts/mymod_inspect.layout");
        m_Preview     = ItemPreviewWidget.Cast(layoutRoot.FindAnyWidget("ItemRender"));
        m_LabelName   = TextWidget.Cast(layoutRoot.FindAnyWidget("LabelItemName"));
        m_LabelHealth = TextWidget.Cast(layoutRoot.FindAnyWidget("LabelHealth"));
        return layoutRoot;
    }

    void SetItem(EntityAI item)
    {
        m_Preview.SetItem(item);
        m_LabelName.SetText(item.GetDisplayName());                                  // object.c:476
        m_LabelHealth.SetText("Condition: " + item.GetHealthLevel().ToString());     // object.c:1171
    }

    override bool OnClick(Widget w, int x, int y, int button)
    {
        string name = w.GetName();   // enwidgets.c:121
        if (name == "BtnRotateLeft")  { Rotate(-15); return true; }
        if (name == "BtnRotateRight") { Rotate(15);  return true; }
        if (name == "BtnClose")       { GetGame().GetUIManager().HideScriptedMenu(this); return true; }
        return false;
    }

    void Rotate(float delta)
    {
        m_RotY += delta;
        m_Preview.SetModelOrientation(Vector(m_RotY, 0, 0));
    }
}
```

`GetDisplayName` and `GetHealthLevel` are in `P:\scripts\3_game\entities\object.c`.
