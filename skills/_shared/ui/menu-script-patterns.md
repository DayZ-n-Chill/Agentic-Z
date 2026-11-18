# Menu script patterns

Script patterns that polished mod menus share: imageset icons, tabs, lists built from a row layout, a search filter, a press twice to confirm button, a status message that fades, server set colors, a 3D item preview, a HUD overlay and click sounds. They are mod practice, not vanilla behaviour, except where a line cites `P:\`.

## Icons from a vanilla imageset

Vanilla ships icon imagesets (`dayz_gui`, `dayz_inventory`, `dayz_crosshairs`), so a mod needs no texture of its own for common icons.

```c
ImageWidget icon = ImageWidget.Cast(m_Root.FindAnyWidget("MyIcon"));
if (icon)
    icon.LoadImageFile(0, "set:dayz_gui image:icon_pin");

RichTextWidget rt = RichTextWidget.Cast(m_Root.FindAnyWidget("MyRichText"));
if (rt)
    rt.SetText("<image set='dayz_gui' name='icon_pin' /> Location found");
```

A mod's own imagesets are registered in `config.cpp` under `CfgMods`, `class defs`, `class imageSets` (`script-recipes.md`).

## Tabs

One button per tab over a shared content panel; selecting a tab recolors the buttons and refills or swaps the content.

```c
void SelectTab(int idx)
{
    m_ActiveTab = idx;
    for (int i = 0; i < m_TabBgs.Count(); i++)
    {
        if (i == idx)
            m_TabBgs[i].SetColor(MYMOD_COL_TAB_ACTIVE);
        else
            m_TabBgs[i].SetColor(MYMOD_COL_TAB_INACTIVE);
    }
    RefreshContent();
}
```

## A list built from a row layout

The list is a `ScrollWidgetClass` holding a `GridSpacerWidgetClass` or `WrapSpacerWidgetClass`; script removes the old rows and creates one row layout per item.

```c
void PopulateItems(array<ref MyMod_ItemData> items)
{
    Widget child = m_ItemList.GetChildren();
    while (child)
    {
        Widget next = child.GetSibling();
        child.Unlink();   // destroys the widget and all its children
        child = next;
    }

    for (int i = 0; i < items.Count(); i++)
    {
        Widget row = GetGame().GetWorkspace().CreateWidgets("MyMod/gui/layouts/item_row.layout", m_ItemList);
        if (!row)
            continue;
        TextWidget nameText = TextWidget.Cast(row.FindAnyWidget("ItemName"));
        if (nameText)
            nameText.SetText(items[i].m_Name);
    }
}
```

Creating every row at once lags with lists in the thousands. Past about 50 rows, create only the visible rows plus a few and reuse them as the list scrolls.

## A search filter

Show or hide each row by a case blind substring match on every change of the search box.

```c
void OnSearchChanged()
{
    string query = m_SearchText;
    query.ToLower();
    for (int i = 0; i < m_AllItems.Count(); i++)
    {
        string itemName = m_AllItems[i].m_Name;
        itemName.ToLower();
        m_ItemWidgets[i].Show(query == "" || itemName.IndexOf(query) >= 0);
    }
}
```

## Press twice to confirm

The first press turns the button red with a "Confirm?" label and starts a timer; a second press inside the time runs the action; the timer running out restores the button.

```c
void OnDangerousClick()
{
    if (!m_ConfirmActive)
    {
        m_ConfirmActive = true;
        m_ConfirmTimer = 3.0;
        m_BtnText.SetText("#STR_MYMOD_CONFIRM");
        m_BtnBg.SetColor(MYMOD_COL_RED);
        return;
    }
    m_ConfirmActive = false;
    RunDangerousAction();
    RestoreButton();
}

void Update(float dt)
{
    if (m_ConfirmActive)
    {
        m_ConfirmTimer -= dt;
        if (m_ConfirmTimer <= 0)
        {
            m_ConfirmActive = false;
            RestoreButton();
        }
    }
}
```

A status message that clears itself works the same way: set the text and a timer, and put the default text back when the timer runs out.

## Colors the server sets

The DayZ Expansion market menu lets a server owner set its colors in JSON. The pattern: a settings class of `int` colors with defaults, sent to the client and applied when the menu opens.

```c
class MyMod_MenuColors
{
    int BaseBackground;
    int ButtonNormal;
    int TextPrimary;

    void SetDefaults()
    {
        BaseBackground = ARGB(235, 30, 30, 30);
        ButtonNormal = ARGB(255, 37, 53, 80);
        TextPrimary = ARGB(255, 220, 220, 220);
    }
}
```

Tint a white source, never a procedural texture string from script: `LoadImageFile` with `#(argb,8,8,3)color(...)` fails on 1.29 (`widget-classes.md`). A `PanelWidgetClass` with `style rover_sim_colorable` tints with `SetColor` and needs no image.

## A 3D item preview

For one item, use `ItemPreviewWidgetClass` and `SetItem(EntityAI)` (`P:\scripts\3_game\gameplay.c:288`); it needs no camera (`preview-widgets.md`). `RTTextureWidget` has no methods of its own (`P:\scripts\1_core\proto\enwidgets.c:243`); `SetGUIWidget` makes it an entity shader's `$rendertarget` (`:637`) and `ImageWidget.SetImageTexture` shows it in an image (`:258`), but filling it from widgets does not work (`text-sizing-and-rendering.md`).

## A HUD overlay

A HUD element that stays across menus is created once in `MissionGameplay.OnInit`, updated from `OnUpdate`, and never takes input: no `ChangeGameFocus`, no `ShowUICursor`. `SetSort(1000)` on its root puts it above the game HUD and below menus. It must `Unlink()` its root in `OnMissionFinish`, or a server hop stacks a second copy (`plan-to-implementation.md`). Hiding it with the vanilla HUD is in `vanilla-menus-map.md`, "The HUD".

## Click sounds

Vanilla menus play no click or hover sounds (`vanilla-menus-map.md`). Mods borrow a light vanilla sound set:

```c
static void MyMod_PlayUIClick()
{
    SEffectManager.PlaySound("pickUpBackPack_Plastic_Light_SoundSet", vector.Zero);
}
```

`SEffectManager.PlaySound(string sound_set, vector position, ...)` is at `P:\scripts\3_game\effectmanager.c:178`. `pickUpBackPack_Plastic_Light_SoundSet` is at `P:\DZ\sounds\hpp\config.cpp:323810`; `pickUpBackPack_Metal_SoundSet` (`:323784`) is louder. Play them on clicks and confirmations, not on hover or tab changes.
