# Cards and tabs

How to build an info card and a set of tabs, each as a layout plus a menu class. Toggles and number fields are in `form-controls.md`; restacking and click problems are in `stacking-and-clickability.md`.

The samples are patterns, not vanilla excerpts, and are not run in game. They use a vanilla `UIScriptedMenu`, which receives the events of its own layout (`layoutRoot`, `P:\scripts\3_game\tools\uiscriptedmenu.c:69`) without `SetHandler`, as `InGameMenu` does (`P:\scripts\5_mission\gui\ingamemenu.c:36` and `:161`). Unit flags are written out on every widget; see `checklist-and-troubleshooting.md`, "Declare all four unit flags".

## A card

A fixed size frame with a background that fills it and two lines of text:

```c
FrameWidgetClass CardPrice {
 position 12 46
 size 93 52
 hexactpos 1
 vexactpos 1
 hexactsize 1
 vexactsize 1
 {
  ImageWidgetClass CardPriceBg {
   size 1 1
   hexactpos 0
   vexactpos 0
   hexactsize 0
   vexactsize 0
   stretch 1
   ignorepointer 1
  }
  TextWidgetClass CardPriceLabel {
   position 8 4
   size 77 16
   hexactpos 1
   vexactpos 1
   hexactsize 1
   vexactsize 1
   font "gui/fonts/MetronBook"
   "text halign" left
   "text valign" center
   ignorepointer 1
  }
  TextWidgetClass CardPriceValue {
   position 8 24
   size 77 22
   hexactpos 1
   vexactpos 1
   hexactsize 1
   vexactsize 1
   font "gui/fonts/Metron"
   "text halign" left
   "text valign" center
   ignorepointer 1
  }
 }
}
```

```c
void MyMod_UpdatePriceCard(Widget root, float currentPrice, float change)
{
    TextWidget label = TextWidget.Cast(root.FindAnyWidget("CardPriceLabel"));
    TextWidget value = TextWidget.Cast(root.FindAnyWidget("CardPriceValue"));
    if (!label || !value)
        return;
    label.SetText("#STR_MyMod_CurrentPrice");
    value.SetText(currentPrice.ToString());
    int color = ARGB(255, 100, 200, 100);
    if (change < 0)
        color = ARGB(255, 200, 100, 100);
    value.SetColor(color);
}
```

Every child ignores the pointer; give the frame a handler if the whole card should be clickable.

## Tabs

A bar of tab buttons over stacked panels, one visible at a time:

```c
FrameWidgetClass TabContainer {
 position 0 60
 size 400 300
 hexactpos 1
 vexactpos 1
 hexactsize 1
 vexactsize 1
 {
  ButtonWidgetClass TabBtnCash {
   size 200 32
   hexactpos 1
   vexactpos 1
   hexactsize 1
   vexactsize 1
  }
  ButtonWidgetClass TabBtnAccount {
   position 200 0
   size 200 32
   hexactpos 1
   vexactpos 1
   hexactsize 1
   vexactsize 1
  }
  FrameWidgetClass CashPanel {
   position 0 32
   size 400 268
   hexactpos 1
   vexactpos 1
   hexactsize 1
   vexactsize 1
  }
  FrameWidgetClass AccountPanel {
   visible 0
   position 0 32
   size 400 268
   hexactpos 1
   vexactpos 1
   hexactsize 1
   vexactsize 1
  }
 }
}
```

```c
override bool OnClick(Widget w, int x, int y, int button)
{
    if (w.GetName() == "TabBtnCash")
    {
        SelectTab(0);
        return true;
    }
    if (w.GetName() == "TabBtnAccount")
    {
        SelectTab(1);
        return true;
    }
    return false;
}

protected void SelectTab(int index)
{
    layoutRoot.FindAnyWidget("CashPanel").Show(index == 0);
    layoutRoot.FindAnyWidget("AccountPanel").Show(index == 1);

    int cashColor = ARGB(255, 40, 40, 45);
    int acctColor = ARGB(255, 40, 40, 45);
    if (index == 0)
        cashColor = ARGB(255, 60, 60, 70);
    else
        acctColor = ARGB(255, 60, 60, 70);

    // when each tab button holds a background image named "BtnBg"
    ImageWidget cashBg = ImageWidget.Cast(layoutRoot.FindAnyWidget("TabBtnCash").FindWidget("BtnBg"));
    ImageWidget acctBg = ImageWidget.Cast(layoutRoot.FindAnyWidget("TabBtnAccount").FindWidget("BtnBg"));
    if (cashBg)
        cashBg.SetColor(cashColor);
    if (acctBg)
        acctBg.SetColor(acctColor);
}
```

Hide every panel but the active one on each switch.
