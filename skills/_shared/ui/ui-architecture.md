# Structuring a large mod UI

How a large production mod keeps many screens manageable: a registry of layouts by name, widget fields bound by name, pages and tabs, an event bus, compile time feature switches, an RPC dispatcher, and formatting numbers for display. Each pattern also fits a mod with interactive devices such as a phone, an ATM or a terminal.

The patterns come from a large production group and map mod; `My*` names are its helper classes and are not vanilla. The vanilla calls are cited.

## Layouts by name

Register every layout path once at init under a short name, then create layouts by name anywhere. Paths live in one place and a theme or a device can swap a whole set.

```c
// in the layout manager's constructor
RegisterLayout("GroupUI", "MyMod/gui/layouts/menu/mapmenu_default.layout");
RegisterLayout("ChatItem", "MyMod/gui/layouts/helper/day_z_chat_item.layout");
RegisterLayout("3DMarker", "MyMod/gui/layouts/helper/3dmarker.layout");

// anywhere
Widget w = MyLayoutManager.Get().CreateLayout("ChatItem", parentWidget);
Widget w2 = MyLayoutManager.Get().CreateLayout("3DMarker"); // no parent: on the screen root
```

Underneath it is the vanilla `WorkspaceWidget.CreateWidgets(string layout, Widget parentWidget = NULL, bool immedUpdate = true)` (`P:\scripts\1_core\proto\enwidgets.c:181`).

## Widget fields bound by name

`ConnectClassWidgetVariables` fills every member whose name matches a widget name in the tree, replacing dozens of `FindAnyWidget` calls:

```c
class MyGroupManagePage
{
    EditBoxWidget searchbox;
    ButtonWidget btn_kick, btn_leave, btn_upgrade;
    TextWidget txt_groupname;
    Widget playerlist_members, panel_list;
}

ConnectClassWidgetVariables(this, rootWidget, excludeArray, renameArray);
```

`excludeArray` lists member names to skip, such as `{"rootWidget", "buttonWidget"}`. `renameArray` is a flat list of pairs, not a map: each even index is a member name and the next odd index the widget it binds to. To bind the member `mapWidget` to the widget `Map`:

```c
TStringArray GetConnectRenameFields() { return {"mapWidget", "Map", "mapNotFound", "MapNotFound"}; }
```

## Pages and tabs

Keep an array of page objects. Each has a tab button made at run time, a content panel, a `pageID` and `pageSubID` (pages that share a `pageID` share one tab), and a priority for the tab order.

```c
void InitPages()
{
    pages.Clear();
    InitPage(new MyInfoPage(MyPageSettingsType.INFO));
    InitPage(new MyGroupCreatePage(MyPageSettingsType.GROUP));
    InitPage(new MyGroupManagePage(MyPageSettingsType.GROUP));
}

void ChangePageTo(MyGroupPage page)
{
    if (currentPage)
        currentPage.OnHide();
    currentPage = page;
    page.OnShow();
}

btnWidget.SetSort(1000 - priority); // higher priority comes first
```

`SetSort` is at `enwidgets.c:130`. A page that may not open returns false from its tab handler; the manage page opens only for a player in a group:

```c
override bool OnTopButtonClicked(Widget w)
{
    if (!super.OnTopButtonClicked(w))
        return false;
    PlayerBase pb = PlayerBase.Cast(GetGame().GetPlayer());
    return pb && pb.GetMyGroup() != null;
}
```

## An event bus

A static `ScriptInvoker` on a manager class lets any component react without knowing who fired:

```c
class MyColorManager_
{
    static ref ScriptInvoker Event_OnColorChange = new ScriptInvoker();
    static void InvokeOnChanged() { Event_OnColorChange.Invoke(); }
}

void MyComponent()
{
    MyColorManager_.Event_OnColorChange.Insert(OnColorChanged);
}

void ~MyComponent()
{
    if (MyColorManager_.Event_OnColorChange)
        MyColorManager_.Event_OnColorChange.Remove(OnColorChanged);
}
```

Remove the callback in every destructor, or the invoker calls into a dead object. The group mod fires `OnColorChange`, `OnPositionChange`, `OnLayoutChanged`, `OnScreenSizeChanged`, `StreamerModeChanged`, `GPSChanged` and `OnConfigReceived` this way. `ScriptInvoker` is vanilla (`P:\scripts\2_gamelib\tools.c:115`).

## Feature switches at compile time

Wrap each optional subsystem in a define so a server can drop it without script errors:

```c
#ifndef MYMOD_DISABLE_CHAT
modded class Chat { ... }
modded class ChatInputMenu { ... }
#endif

#ifdef MYMOD_FEATURE_PLOTPOLE
// territory features
#endif
```

## An RPC dispatcher

Register one callback per RPC type, then let a group level handler dispatch further by sub type:

```c
class My_RPC_AG_Client : My_RPCHandler
{
    void My_RPC_AG_Client()
    {
        RegisterRPC(MyGroupRPCs.GROUP_RPC, ScriptCaller.Create(OnGroupRPC));
        RegisterRPC(MyGroupRPCs.MY_GLOBAL_CHAT, ScriptCaller.Create(OnChatMessage));
    }

    void OnGroupRPC()
    {
        int type = 0;
        if (!ctx.Read(type))
            return;
        pb.GetMyGroup().OnRPCClient(type, ctx);
    }
}

void OnRPCClient(int type, ParamsReadContext ctx)
{
    if (type == MyGroupRPCs.ADD)
    {
        // handle add
    }
    else if (type > MyGroupRPCs.START_MARKER_RPC)
    {
        int uid;
        ctx.Read(uid);
        MyMarker marker = FindAnyMarkerByUID(uid);
        if (marker)
            marker.OnMarkerRPCClient(type, ctx);
    }
}
```

## Showing a float with fixed decimals

`string.Format` (`P:\scripts\1_core\proto\enstring.c:526`) has placeholders `%1` to `%9` with no precision, so trim the decimals by hand:

```c
string MyMod_FloatToString(float f, bool oneDecimal)
{
    string txt = "" + f;
    int index = txt.IndexOf(".");
    if (oneDecimal)
    {
        if (index > 0)
            txt = txt.Substring(0, index + 2);
        else
            txt = txt + ".0";
    }
    else if (index > 0)
        txt = txt.Substring(0, index);
    return txt;
}
```

## Where each pattern fits a device mod

| Pattern | Use in a device mod |
|---|---|
| Layouts by name | Swap a phone or ATM layout set per device skin |
| Widget fields by name | Less boilerplate in every UI class |
| Event bus | Device state broadcasts, refresh triggers, phone notifications |
| Saved client settings (`hud-overlays.md`) | ATM preferences, themes, shortcuts |
| Color and position managers (`hud-overlays.md`) | Player themes, movable notifications and minimap |
| Text measuring (`chat-ui.md`) | Chat bubble sizes, receipt layout |
| Reused chat lines (`chat-ui.md`) | A messaging app |
| World markers (`world-markers-and-compass.md`) | Device locations and waypoints |
| Pages and tabs | Phone apps, ATM screens |
| Refresh on change (`map-and-markers.md`) | Device lists |
| Pings (`world-markers-and-compass.md`) | Quick markers from a phone app |
| Feature switches | Optional subsystems such as CCTV, battery or phone |
