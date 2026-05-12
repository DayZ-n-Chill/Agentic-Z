# Dabs Framework Integration

[Dabs Framework](https://github.com/InclementDab/DayZ-Dabs-Framework) — attribute-driven development toolkit. Eliminates explicit registration boilerplate for actions, settings, GUI views, and Workbench plugins via compile-time attributes.

---

## Attribute-Based Action Registration

Instead of adding actions to every item's `GetActions()` override, Dabs scans for `[RegisterAction(...)]` on your action class at load time.

```c
// Scripts/4_World/Classes/UserActionsComponent/Actions/
// ActionMyMod_Dabs_DrinkContaminate.c

[RegisterAction(MyMod_CustomCanteen)]   // <- registers this action for MyMod_CustomCanteen
class ActionMyMod_Dabs_DrinkContaminate : ActionSingleUseBase
{
    void ActionMyMod_Dabs_DrinkContaminate()
    {
        m_CallbackClass = ActionSingleUseBaseCB;
        m_CommandUID    = DayZPlayerConstants.CMD_ACTIONMOD_EAT;
        m_Text          = "Contaminate";
    }

    override void CreateConditionComponents()
    {
        m_ConditionItem   = new CCINotRuined;
        m_ConditionTarget = new CCTNone;
    }

    override bool CanBePerformedServer(Man player)
    {
        MyMod_CustomCanteen c;
        return Class.CastTo(c, player.GetHeldItem()) && c.GetQuantity() > 0;
    }

    override void OnExecuteServer(ActionData action_data)
    {
        MyMod_CustomCanteen c;
        if (Class.CastTo(c, action_data.m_MainItem))
            c.MyMod_SetContaminated(true);
    }
}
```

---

## Attribute-Based Workbench Plugin

Register a plugin into the Workbench tool menu without touching `workbenchplugins.c`.

```c
// Scripts/Editor/Workbench/MyMod_DiagPlugin.c

[RegisterPlugin("MyMod Diagnostics")]  // label shown in Workbench menu
class MyMod_DiagPlugin : ScriptPlugin
{
    override void OnMenu(vWidget wgt)
    {
        // Build a simple diagnostic panel
        wgt.SetText("MyMod Diagnostics v1.0");
    }
}
```

---

## Dabs MVC: ScriptView-based GUI

Dabs MVC binds a `.layout` XML file to a ViewModel class, reducing the manual widget-wiring in vanilla `UIScriptedMenu`.

### ViewModel

```c
// Scripts/5_Mission/GUI/ViewModels/MyMod_InventoryViewModel.c

class MyMod_InventoryViewModel : ScriptView
{
    // Data exposed to the view (automatically bound to widget properties by name)
    string Title    = "My Mod Inventory";
    int    ItemCount = 0;

    // Called when the view is mounted
    override void OnViewLoad()
    {
        super.OnViewLoad();
        Refresh();
    }

    // Manually trigger a UI refresh
    override void Refresh()
    {
        PlayerBase player = PlayerBase.Cast(GetGame().GetPlayer());
        if (!player)
            return;

        ItemCount = player.GetInventory().AttachmentCount();
        NotifyPropertiesChanged({"ItemCount"}); // Dabs auto-updates bound widgets
    }

    // Bound to BtnClose widget's OnClick via layout attribute
    void BtnClose_OnClick()
    {
        Close();
    }
}
```

### Layout XML binding (excerpt, saved as `.layout` file in Workbench)

```xml
<Widget class="SpacerWidget" name="root">
    <Widget class="TextWidget" name="Title"     bind="Title" />
    <Widget class="TextWidget" name="ItemCount" bind="ItemCount" />
    <Widget class="ButtonWidget" name="BtnClose" onClick="BtnClose_OnClick" />
</Widget>
```

### Opening the view

```c
GetGame().GetUIManager().EnterScriptedMenu(MENU_MYMOD_INVENTORY, null);
// Or via Dabs helper:
MyMod_InventoryViewModel view = new MyMod_InventoryViewModel();
view.Load("GUI\\Layouts\\MyMod\\Inventory.layout");
```

---

## Settings Attribute

Dabs can expose server/client settings through the vanilla settings system without writing the full settings class boilerplate:

```c
// Adds a toggle to the Gameplay settings panel automatically
[RegisterSetting("MyMod", "EnableWelcomeMessage", SettingType.BOOL, "Enable welcome message", true)]
class MyMod_Settings : ScriptSettings
{
}

// Read anywhere:
bool enabled = MyMod_Settings.GetBool("EnableWelcomeMessage");
```

---

## Type Safety Notes

- Dabs attributes are **compile-time** — the class must be loadable from the relevant Script Module layer or the attribute has no effect.
- Avoid mixing Dabs `[RegisterAction]` with vanilla `GetActions()` on the same type — you will get duplicate entries.
- Dabs MVC `NotifyPropertiesChanged` uses **reflection** to match property names to widget names; misspelling a name fails silently.
