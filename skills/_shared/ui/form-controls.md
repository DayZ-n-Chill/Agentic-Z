# Toggles and number fields

How to build a two way toggle and a pair of number fields that convert as the player types, each as a layout plus a menu class. Cards and tabs are in `cards-and-tabs.md`; restacking and click problems are in `stacking-and-clickability.md`.

The samples are patterns, not vanilla excerpts, and are not run in game. They use a vanilla `UIScriptedMenu`, which receives the events of its own layout (`layoutRoot`, `P:\scripts\3_game\tools\uiscriptedmenu.c:69`) without `SetHandler`, as `InGameMenu` does (`P:\scripts\5_mission\gui\ingamemenu.c:36` and `:161`). Unit flags are written out on every widget; see `checklist-and-troubleshooting.md`, "Declare all four unit flags".

## A two way toggle

Two buttons side by side over a track, with an indicator that moves under the chosen side. Text and decoration ignore the pointer so clicks reach the buttons:

```c
FrameWidgetClass CurrencyToggle {
 position 12 126
 size 200 32
 hexactpos 1
 vexactpos 1
 hexactsize 1
 vexactsize 1
 {
  ImageWidgetClass ToggleBg {
   size 200 32
   hexactpos 1
   vexactpos 1
   hexactsize 1
   vexactsize 1
   stretch 1
   ignorepointer 1
  }
  ImageWidgetClass ToggleIndicator {
   size 100 32
   hexactpos 1
   vexactpos 1
   hexactsize 1
   vexactsize 1
   stretch 1
   ignorepointer 1
  }
  ButtonWidgetClass OptionLeft {
   size 100 32
   hexactpos 1
   vexactpos 1
   hexactsize 1
   vexactsize 1
   {
    TextWidgetClass OptionLeftText {
     size 1 1
     hexactpos 0
     vexactpos 0
     hexactsize 0
     vexactsize 0
     font "gui/fonts/Metron"
     "text halign" center
     "text valign" center
     text "EUR"
     ignorepointer 1
    }
   }
  }
  ButtonWidgetClass OptionRight {
   position 100 0
   size 100 32
   hexactpos 1
   vexactpos 1
   hexactsize 1
   vexactsize 1
   {
    TextWidgetClass OptionRightText {
     size 1 1
     hexactpos 0
     vexactpos 0
     hexactsize 0
     vexactsize 0
     font "gui/fonts/Metron"
     "text halign" center
     "text valign" center
     text "BTC"
     ignorepointer 1
    }
   }
  }
 }
}
```

```c
class MyMod_CurrencyMenu extends UIScriptedMenu
{
    protected Widget m_ToggleIndicator;
    protected TextWidget m_OptionLeftText;
    protected TextWidget m_OptionRightText;
    protected bool m_IsBtc;

    override Widget Init()
    {
        layoutRoot = GetGame().GetWorkspace().CreateWidgets("MyMod/gui/layouts/currency.layout");
        m_ToggleIndicator = layoutRoot.FindAnyWidget("ToggleIndicator");
        m_OptionLeftText = TextWidget.Cast(layoutRoot.FindAnyWidget("OptionLeftText"));
        m_OptionRightText = TextWidget.Cast(layoutRoot.FindAnyWidget("OptionRightText"));
        return layoutRoot;
    }

    override bool OnClick(Widget w, int x, int y, int button)
    {
        if (w.GetName() == "OptionLeft")
        {
            SelectCurrency(false);
            return true;
        }
        if (w.GetName() == "OptionRight")
        {
            SelectCurrency(true);
            return true;
        }
        return false;
    }

    protected void SelectCurrency(bool isBtc)
    {
        m_IsBtc = isBtc;
        float targetX = 0;
        int leftColor = ARGB(255, 255, 255, 255);
        int rightColor = ARGB(255, 128, 128, 128);
        if (isBtc)
        {
            targetX = 100;
            leftColor = ARGB(255, 128, 128, 128);
            rightColor = ARGB(255, 255, 255, 255);
        }
        m_ToggleIndicator.SetPos(targetX, 0);
        m_OptionLeftText.SetColor(leftColor);
        m_OptionRightText.SetColor(rightColor);
    }
}
```

Each button is half the track, and the indicator sits at 0 or 100. To slide it instead of jumping, a mod that depends on Dabs Framework can call `WidgetAnimator.AnimateEx(m_ToggleIndicator, WidgetAnimatorProperty.POSITION_X, targetX, 200, WidgetAnimatorEasing.EASE_OUT_CUBIC)` (`dabs-observables-and-animation.md`). To read a key every frame, use `GetUApi().GetInputByName("UAxxx").LocalPress()` (`GetInputByName`, `P:\scripts\3_game\inputapi\uainput.c:218`); the input must be declared in `inputs.xml` and that file named in `config.cpp`, or `GetInputByName` returns null (`skills/_shared/enscript/integrations/input_bindings.md`).

## A numeric input that converts

Two edit boxes that fill each other as the player types, clamped to a range. Parse with `ToFloat()`:

```c
override bool OnChange(Widget w, int x, int y, bool finished)
{
    float val;
    if (w == m_EditBtcAmount)
    {
        val = Math.Clamp(m_EditBtcAmount.GetText().ToFloat(), 0, m_MaxBtc);
        m_EditEurAmount.SetText((val * m_BtcPrice).ToString());
        return true;
    }
    if (w == m_EditEurAmount)
    {
        val = Math.Clamp(m_EditEurAmount.GetText().ToFloat() / m_BtcPrice, 0, m_MaxBtc);
        m_EditBtcAmount.SetText(val.ToString());
        return true;
    }
    return false;
}
```

`OnChange(Widget w, int x, int y, bool finished)` is at `P:\scripts\1_core\proto\enwidgets.c:675`, and `EditBoxWidget.GetText()` returns the string (`:349`). Put each edit box over an `ImageWidgetClass` background with `ignorepointer 1` and leave the edit box itself clickable.
