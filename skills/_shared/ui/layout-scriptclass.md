# Script classes and parameters in a layout

How a layout widget gets its own script handler through `scriptclass`, how `ScriptParamsClass` passes values to it, and how a layout names a style. The widget events the handler receives are listed in `script-recipes.md`.

## Attaching a handler

A widget with `scriptclass "MyMod_NumberField"` gets an instance of that class when the layout is created. The engine fills its `reference` fields from the widget's `ScriptParamsClass`, then calls `OnWidgetScriptInit(Widget w)` once.

```text
EditBoxWidgetClass AmountInput {
 scriptclass "MyMod_NumberField"
 position 10 10
 size 200 30
 hexactpos 1
 vexactpos 1
 hexactsize 1
 vexactsize 1
 {
  ScriptParamsClass {
   maxLength 6
   pattern "[0-9]+"
  }
 }
}
```

```c
class MyMod_NumberField : ScriptedWidgetEventHandler
{
    reference int maxLength;    // filled from ScriptParamsClass before init
    reference string pattern;
    protected Widget m_Root;

    void OnWidgetScriptInit(Widget w)
    {
        m_Root = w;
        w.SetHandler(this);     // without this no event arrives
    }

    override bool OnChange(Widget w, int x, int y, bool finished)
    {
        return false;
    }
}
```

Vanilla does the same in `SizeToChild`: `reference` fields at `P:\scripts\3_game\gui\containers\sizetochild.c:3` to `:7` and `OnWidgetScriptInit(Widget w)` at `:14`. `SetHandler` is at `P:\scripts\1_core\proto\enwidgets.c:172`.

Handlers like this suit number or ID validators on an edit box, margins worked out from the parent, tooltips on hover, drag behaviour and spinning or pulsing icons.

## Where ScriptParamsClass goes

`ScriptParamsClass` always sits in a block of its own with no child widgets in it: the widget's only block on a leaf, or a second block after the block that holds the children. It holds its fields directly, with no inner braces. All 50 `ScriptParamsClass` blocks in the vanilla layouts under `P:\gui\layouts` have this shape, for example a second block after the children holding `AlignChilds 1` and `Gap 2` (`P:\gui\layouts\day_z_hud.layout:309` to `:314`), and so do all 157 in a count over shipped third party layouts.

```text
PanelWidgetClass GapPanel {
 scriptclass "MyMod_GapHandler"
 {
  // child widgets here
 }
 {
  ScriptParamsClass {
   gapHorizontal -10
   gapVertical -10
  }
 }
}
```

Dabs Framework reads its binding fields (`Binding_Name`, `Relay_Command`, `Two_Way_Binding`) from the same block; see `_shared/enscript/integrations/dabs_framework.md` and `dabs-mvc-internals.md`.

## Naming a style

```text
PanelWidgetClass Border {
 style MyMod_Outline
 color 1 1 1 1
}
```

The name is unquoted and must be declared, in a registered `.styles` file, under the block of this widget's type: a panel's style under `<Widget Name="PanelWidget">`. A button's states are `Normal`, `Pushed`, `Highlight`, `Focus` and `Disabled` (`P:\gui\looknfeel\dayzwidgets.styles:1598` to `:1642`); there is no `Pressed` and no `Hover`. The whole system is in `styles-format.md`.
