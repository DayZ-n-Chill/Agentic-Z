# Dabs collections, two way binding and animation

How Dabs Framework's `ObservableCollection` fills a list, which widgets bind both ways, and how `WidgetAnimator` and `LinearColor` work, with the traps in each. Views, bindings and commands are in `dabs-mvc-internals.md`.

Dabs Framework is a third party mod. These facts are checked against its own scripts in the Steam Workshop copy (`addons\Scripts.pbo`), not vanilla; paths and lines are that copy's. The vanilla call underneath a collection is `Widget.AddChild(Widget child, bool immedUpdate = true)` (`P:\scripts\1_core\proto\enwidgets.c:161`), which moves each item's root into the bound spacer.

## ObservableCollection

```c
ref ObservableCollection<MyMod_RowView> m_Items = new ObservableCollection<MyMod_RowView>(this);
```

Pass the `ViewController`. The element type must be a class. Storage is `ref array<ref TValue>` (`MVC\Observables\ObservableCollection.c:41`).

Every one of these updates the UI: `Insert`, `InsertAt`, `InsertAll`, `Remove(int index)`, `Remove(TValue value)`, `RemoveOrdered`, `RemoveRange(start, end)`, `Set(index, value)`, `MoveIndex(index, moveIndex)`, `SwapItems(a, b)` and `Clear`. `Get`, `Count`, `Find` and `GetArray` read.

- The layout binding's `Binding_Name` equals the name of the controller field that holds the collection. `NotifyCollectionChanged` finds the field by looking the instance up in reverse and logs "could not find variable" otherwise.
- For a collection of views, the element type is a `ScriptView` subclass that overrides `GetLayoutFile()`. Each item builds its own tree, and `Insert` moves its root into the bound spacer with `AddChild`.
- Bind the collection to a `WrapSpacerWidget`, `GridSpacerWidget` or `ScrollWidget`.
- `Clear()` empties the storage with `m_Data.Clear()` (`MVC\Observables\ObservableCollection.c:138` to `:142`), and the spacer's controller removes each child by walking `GetChildren` and `GetSibling` and calling `RemoveChild` (`SpacerBaseWidgetController.c:88` to `:95`).
- An item that holds a `ref` back to its controller leaks: nothing breaks the cycle. Null the back reference in the item's destructor.
- Don't use `ObservableSet`. It raises `NotifyCollectionChangedAction.Add` and `.Set` (`MVC\Observables\ObservableSet.c:14`, `:23`, `:43`), and the enum has only `Insert`, `InsertAt`, `Remove`, `Replace`, `Move`, `Swap` and `Clear` (`MVC\Types\NotifyCollectionChangedAction.c`).
- The widget to controller registry matches the exact type. `RegisterWidgetControllers` (`3_Game\DabsFramework\!Core\DayZGame.c:54` to `:80`) looks up `data.Type()` without walking the inheritance chain, so a widget type that isn't registered logs "Could not find WidgetController for type X".

A scroll list bound to a collection, from Dabs's own `layouts\options\options_tab.layout`:

```c
ScrollWidgetClass Scroll {
 "Scrollbar V" 1
 {
  WrapSpacerWidgetClass Content {
   scriptclass "ViewBinding"
   "Size To Content V" 1
   {
    ScriptParamsClass {
     Binding_Name "MyCollection"
    }
   }
  }
 }
}
```

## Which widgets bind both ways

From `CanTwoWayBind()` in each file under `MVC\WidgetController\`:

| Widget | Both ways | Controller to view | View to controller |
|---|---|---|---|
| `EditBoxWidget`, `PasswordEditBoxWidget`, `MultilineEditBoxWidget` | yes | `SetText` | `GetText` |
| `ButtonWidget` | yes | `SetState(bool)` | `GetState` |
| `CheckBoxWidget` | yes | `SetChecked` | `IsChecked` |
| `SliderWidget` | yes | `SetCurrent` | `GetCurrent` |
| `ProgressBarWidget`, `XComboBoxWidget`, `TextListboxWidget` | yes | see each controller file | |
| `SpacerBaseWidget`, `WrapSpacerWidget`, `GridSpacerWidget`, `ScrollWidget` | yes | `AddChild` | `GetFocus` (the selection) |
| `TextWidget`, `MultilineTextWidget`, `RichTextWidget` | no | `SetText` | |
| `ImageWidget` | no | `LoadImageFile` | |

On a button, `Binding_Name` maps to the pressed state, and `Selected_Item` binds its label text through `SetText` and `GetText`.

## WidgetAnimator

`3_Game\DabsFramework\!Core\WidgetAnimator.c`, outside `MVC\`. Use it instead of writing tween code on top of Dabs.

| Call | Does |
|---|---|
| `Animate(source, property, end_value, TimeSpan time)` | From the current value to `end_value` |
| `Animate(source, property, start_value, end_value, int time)` | From an explicit start |
| `AnimateEx(source, property, end_value, time, WidgetAnimatorEasing easing = 0)` | With an easing curve |
| `AnimateLoop(source, property, [start_value,] end_value, int time)` | Repeats |
| `AnimateColor(source, [start_color,] LinearColor end_color, time, BlendMode blend_mode = BlendMode.NORMAL, bool loop = false)` | Color with a blend mode |
| `AnimateColorHSV(source, vector start_color, vector end_color, time, bool loop = false, easing = 0)` | Color through HSV |
| `CancelAnimate(source, property = -1, bool reset = false)` | Stops one or all |
| `HasAnimation(source, property)`, `GetAnimations(source)` | Reads what is running |

```c
WidgetAnimator.Animate(widget, WidgetAnimatorProperty.COLOR_A, 1.0, 300);
WidgetAnimator.AnimateEx(widget, WidgetAnimatorProperty.POSITION_Y, 0, 300, WidgetAnimatorEasing.EASE_OUT_SINE);
WidgetAnimator.AnimateColor(widget, endColor, 300, BlendMode.NORMAL);
WidgetAnimator.CancelAnimate(widget);
```

`WidgetAnimatorProperty` is a set of bit flags (`!Core\Enum\WidgetAnimatorProperty.c`):

| Flag | Value | Flag | Value |
|---|---|---|---|
| `POSITION_X` | 1 | `COLOR_G` | 512 |
| `POSITION_Y` | 2 | `COLOR_B` | 1024 |
| `SIZE_W` | 4 | `COLOR_H` | 2048 |
| `SIZE_H` | 8 | `COLOR_S` | 4096 |
| `ROTATION_X` (roll) | 16 | `COLOR_V` | 8192 |
| `ROTATION_Y` (pitch) | 32 | `EXACT_TEXT` | 16384 |
| `ROTATION_Z` (yaw) | 64 | `SIZE_EXACT_W` | 32768 |
| `COLOR_A` | 128 | `SIZE_EXACT_H` | 65536 |
| `COLOR_R` | 256 | `LINEAR_COLOR` (A, R, G and B) | 1920 |

Color values are floats from 0 to 1. `WidgetAnimatorEasing` has `NONE` plus `EASE_IN_`, `EASE_OUT_` and `EASE_INOUT_` for Sine, Quad, Cubic, Quart, Quint, Exponential, Circ, Back, Elastic and Bounce.

The animator runs on the `CALL_CATEGORY_GUI` queue, cancels the earlier animation of the same property on the same widget, and its timer deletes itself when done. On a `TextWidget`, `COLOR_A` also changes the outline alpha. Deleting or unlinking a widget mid animation is safe; the timer holds a weak reference and cleans up on the next GUI tick.

The traps:

- The time unit is milliseconds, but the `TimeSpan` helpers count seconds. `TimeSpan` is `typedef int` (`1_Core\DabsFramework\TimeSpan.c:71`), so `TimeSpan.FromMinutes(1)` gives 60 and the animator reads 60 ms. Pass plain millisecond ints.
- `EASE_IN_BOUNCE` and `EASE_OUT_BOUNCE` are swapped in the implementation (`!Core\WidgetAnimationTimer.c:134` and `:135`).
- `AnimateColor` does nothing when the current color already equals the end color, loop included (`!Core\WidgetAnimator.c:103`).
- `AnimateColorHSV` doesn't cancel earlier animations, unlike every other entry point, and starts three timers, one each for H, S and V.
- Finished timers stay in the static `m_RunningTimers` array; only `CancelAnimate` removes them (`:150` to `:157`), so a long session leaks slots.

## LinearColor

`3_Game\DabsFramework\!Core\Color.c` declares `class LinearColor: int`, an ARGB integer with helpers.

| Group | Calls |
|---|---|
| Create | `Create(r, g, b)` and `Create(a, r, g, b)` with ints 0 to 255; `CreateF(r, g, b)` and `CreateF(a, r, g, b)` with floats 0 to 1; `CreateHSV(hue, sat, val, alpha)` with hue 0 to 360 and the rest 0 to 1; `FromHex(hex)` |
| Read and write | `GetAlpha`, `GetRed`, `GetGreen`, `GetBlue` and their `Set` pairs; `GetLuminance()`; `ToHexColor()`; `ToVector()` (float RGB, 0 to 1) |
| Combine | `Lerp(a, b, blendMode, t)`, `Blend(a, b, blendMode)`, `IsEqual(other, epsilon)`, `Add`, `Subtract`, `Multiply` |
| Blend modes | `NORMAL`, `MULTIPLY`, `SCREEN`, `OVERLAY`, `HARD_LIGHT`, `SOFT_LIGHT` |
| Constants | About 150 `static const LinearColor` values named after the X11 colors: `LinearColor.RED`, `.DARK_SLATE_GRAY`, `.CORNFLOWER_BLUE` |

Dabs's own color option animates a picker with `WidgetAnimator.AnimateColor(ColorPickerPanel, Value, 10);` (`OptionSelectorColorViewController.c:38`). A `ButtonWidget` takes `SetColor()` without any `LoadImageFile` first (`SampleMVC.c:153`).
