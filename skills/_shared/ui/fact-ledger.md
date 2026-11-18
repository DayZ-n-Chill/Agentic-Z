# UI fact ledger: engine protos, Dabs Framework, rich text markup and production corrections

A fact ledger for UI work on windows, phones and terminals: what the engine protos say, what the Dabs Framework source says, how rich text markup behaves, which early assumptions turned out wrong, and what is still untested. Later retractions are marked in place with their date.

**How facts are marked here.**

- The `enwidgets.c` rows were checked on `P:\` (DayZ 1.30) and carry the 1.30 lines.
- The Dabs rows name files inside Dabs Framework (third-party mod behaviour, not vanilla). The lines spot checked against the Workshop copy of the mod (its `Scripts.pbo`, files under `3_Game\DabsFramework\MVC\`) match: `ViewController.c:63`, `:84-117`, `:316-357`, `ScriptView.c:46-124`, `:238-266`, `:293-296` and `ViewBinding.c:206-231`. The rest are not yet checked.
- The rich text rows describe the documented markup of the newer Enfusion engine (Arma Reforger). They are not checked on `P:\`.
- "Production" means behaviour seen in a shipped mod's UI. It is not yet checked on `P:\` or in game here.

---

## Corrections to earlier claims

- **`map<Widget, T>` works.** Dabs uses it in production. An earlier claim that it crashes was wrong; the crash it was built on probably had another cause.
- **`NotifyPropertyChanged` does not corrupt references.** The bug blamed on it was `FindAnyWidget` returning wrong references for widgets inside a `ButtonWidget`.
- **Override methods do not have to be contiguous.** A production window that does not keep them together works.
- **No custom tween or color code is needed with Dabs.** It already has `WidgetAnimator` and `LinearColor`.

---

## Part 1: facts verified by source

### From enwidgets.c (engine protos, 25 facts)

| # | Fact | Evidence |
|---|---|---|
| P1 | Widget.Show(bool show, bool immedUpdate = true) — has immedUpdate parameter | `P:\scripts\1_core\proto\enwidgets.c:125` |
| P2 | Widget.SetFlags adds flags, ClearFlags removes them | `P:\scripts\1_core\proto\enwidgets.c:128` and `:131` |
| P3 | Widget.Unlink() destroys the widget and all its children | comment at `P:\scripts\1_core\proto\enwidgets.c:173` |
| P4 | Widget.IsVisibleHierarchy() checks visibility of the entire parent chain | `P:\scripts\1_core\proto\enwidgets.c:139` |
| P5 | Widget.SetLV(float) is static and sets the global widget luminance, [-15, 0], default 0 | `P:\scripts\1_core\proto\enwidgets.c:114-115` |
| P6 | Widget.SetTextLV(float) is static and sets the global text luminance, [-15, 0] | `P:\scripts\1_core\proto\enwidgets.c:116-117` |
| P7 | ScrollWidget has complete API: GetVScrollPos, VScrollToPos, VScrollToPos01, VScrollToWidget(child), GetContentHeight, IsScrollbarVisible | `P:\scripts\1_core\proto\enwidgets.c:481-502` |
| P8 | RichTextWidget supports: GetContentHeight, SetContentOffset, ElideText, GetNumLines, SetLinesVisibility, GetLineWidth | `P:\scripts\1_core\proto\enwidgets.c:224-234` |
| P9 | MultilineEditBoxWidget has: GetLinesCount, GetCarriageLine, GetCarriagePos, SetLine, GetLine | `P:\scripts\1_core\proto\enwidgets.c:313-321` |
| P10 | ImageWidget has alpha mask system: LoadMaskTexture, SetMaskProgress, SetMaskTransitionWidth | `P:\scripts\1_core\proto\enwidgets.c:282-310` |
| P11 | SpacerWidget has SetContentAlignmentH/V with WA_LEFT/RIGHT/CENTER/TOP/BOTTOM | `P:\scripts\1_core\proto\enwidgets.c:465-471`; the `WidgetAlignment` enum at `P:\scripts\1_core\proto\enwidgets.c:88-94` |
| P12 | TextWidget has SetBold, SetItalic, SetShadow, SetOutline, GetTextSize, SetTextExactSize | `P:\scripts\1_core\proto\enwidgets.c:189-217` |
| P13 | CanvasWidget has DrawLine(x1,y1,x2,y2,width,color) and Clear() | `P:\scripts\1_core\proto\enwidgets.c:341-345` |
| P14 | VideoWidget complete: Load, Play, Pause, Stop, SetTime, GetTime, GetTotalTime, SetCallback | `P:\scripts\1_core\proto\enwidgets.c:543-632` |
| P15 | SetFocus(Widget) and GetFocus() are global functions | `P:\scripts\1_core\proto\enwidgets.c:698` and `:702` |
| P16 | GetWidgetUnderCursor() global function | `P:\scripts\1_core\proto\enwidgets.c:184` |
| P17 | SetModal(Widget) exists | `P:\scripts\1_core\proto\enwidgets.c:700` |
| P18 | SetActiveWindow(Widget, bool resetFocus) exists | `P:\scripts\1_core\proto\enwidgets.c:695` |
| P19 | WidgetFlags has native DRAGGABLE flag | `P:\scripts\1_core\proto\enwidgets.c:84` |
| P20 | WidgetFlags.CLIPCHILDREN exists | `P:\scripts\1_core\proto\enwidgets.c:81` |
| P21 | OnEvent(EventType, Widget, int, int) exists in ScriptedWidgetEventHandler | `P:\scripts\1_core\proto\enwidgets.c:685` |
| P22 | EditBoxWidget.GetText() returns string (no out param) | `P:\scripts\1_core\proto\enwidgets.c:349` |
| P23 | SliderWidget has SetMinMax, GetStep, SetStep | `P:\scripts\1_core\proto\enwidgets.c:358-367` |
| P24 | ButtonWidget has SetTextHorizontalAlignment, SetTextVerticalAlignment | `P:\scripts\1_core\proto\enwidgets.c:395-399` |
| P25 | PasswordEditBoxWidget.SetHideText(bool) exists | `P:\scripts\1_core\proto\enwidgets.c:355` |

### From Dabs Framework source (28 facts)

| # | Fact | File |
|---|---|---|
| D1 | NotifyPropertyChanged("X") only touches bindings with Binding_Name=="X" | ViewController.c:106-112 |
| D2 | NotifyPropertyChanged("") updates all bindings (expensive) | ViewController.c:91-103 |
| D3 | NotifyPropertyChanged with notify_controller=false avoids PropertyChanged callback | ViewController.c:84,114 |
| D4 | LoadWidgetsAsVariables uses FindAnyWidget once, in the constructor | ScriptView.c:238-266 |
| D5 | ViewController.OnWidgetScriptInit calls SetHandler automatically | ViewController.c:63 |
| D6 | Relay_Command: 1) RelayCommand variable, 2) typename, 3) g_Script.CallFunction | ViewBinding.c:206-231 |
| D7 | ViewController.OnClick calls InvokeCommand and returns true when it was handled; only an unhandled click goes on to super. The first reading here ("calls InvokeCommand and super, so an override plus super fires twice") was corrected: see rule 16 in `checklist-and-troubleshooting.md` | ViewController.c:316-335 |
| D8 | CheckBox uses OnChange (not OnClick) for InvokeCommand | ViewController.c:337-357 |
| D9 | ObservableCollection.Clear() does m_Data.Clear() | ObservableCollection.c:138-142 |
| D10 | SpacerBaseWidgetController.Clear() iterates GetChildren/GetSibling + RemoveChild | SpacerBaseWidgetController.c:88-95 |
| D11 | ViewBinding is not reactive: it requires an explicit NotifyPropertyChanged | ViewBinding.c (no auto-sync) |
| D12 | Two_Way_Binding requires CanTwoWayBind()=true on WidgetController | ViewBinding.c:112 |
| D13 | EditBox, Button, CheckBox, Slider, MultilineEditBox, SpacerBase support Two_Way. The Workshop copy also returns true for ProgressBar, XComboBox and TextListbox (`CanTwoWayBind` in their controllers) | WidgetController/*.c |
| D14 | Sub-property binding: dot notation "m_Obj.value" works | PropertyInfo.GetSubScope, SampleMVC.c:185 |
| D15 | map<Widget, ViewBinding> used in production (ViewBindingHashMap) | Types.c:24, ViewController.c:319 |
| D16 | ScriptView constructor: CreateWidget → LoadWidgetsAsVariables → Controller | ScriptView.c:46-97 |
| D17 | GetLayoutRoot() valid immediately post-constructor | TooltipView.c:48-51 |
| D18 | GetScreenSize() valid immediately post-constructor | TooltipView.c:51 |
| D19 | WidgetAnimator exists with 30 easings and properties POS/SIZE/ROT/COLOR/TEXT | WidgetAnimator.c, WidgetAnimationTimer.c |
| D20 | WidgetAnimator used in production: AnimateColor(panel, value, 10) | OptionSelectorColorViewController.c:38 |
| D21 | LinearColor class with 140+ named colors, HSV, Lerp, BlendModes | Color.c |
| D22 | ScriptViewMenu handles ChangeGameFocus, cursor and menu hierarchy on open. It does not handle ESC, and its destructor does not release game focus: see `dabs-mvc-internals.md` | ScriptViewMenu.c |
| D23 | TooltipView demonstrates GetScreenPos, GetScreenSize, SetScreenPos, GetTextSize, GetMousePos | Tooltip.c:34-128 |
| D24 | ButtonWidget.SetColor() works without LoadImageFile | SampleMVC.c:153 |
| D25 | UseUpdateLoop() returns true by default; override false to disable | ScriptView.c:293-296 |
| D26 | ScriptView destructor: Unlink layout, delete controller, remove from All | ScriptView.c:99-124 |
| D27 | GetFocus() == EditBox works to know which widget has focus | OptionSelectorSliderView.c:41 |
| D28 | ScrollWidget+WrapSpacer+ObservableCollection works in production | options_tab.layout |

### Rich text markup (5 facts, not checked on `P:\`)

Documented for the newer Enfusion engine (Arma Reforger); confirm each in game before relying on it in DayZ.

| # | Fact |
|---|---|
| W1 | RichTextWidget tags: `<b>`, `<i>`, `<color rgba/hex/name>`, `<image set name scale>`, `<outline>`, `<shadow>`, `<font>` |
| W2 | Tags cannot overlap — parser needs clean hierarchy |
| W3 | Wrap + re-layout is expensive with long texts |
| W4 | Bold/italic require SDF fonts |
| W5 | `<image set="..." name="..." scale="1" />` — default scale 1.0 = line height |

### From production (not checked here)

- `FindAnyWidget` returned wrong references for widgets inside a `ButtonWidget`. The corruption first blamed on `NotifyPropertyChanged` came from this (rule 8 in `checklist-and-troubleshooting.md`).
- `map<Widget, T>` works. Dabs uses it. The crash once blamed on it was probably something else.

---

## Part 2: assumptions resolved

| # | Original claim | Final verdict | Evidence |
|---|---|---|---|
| A1 | Contiguous override methods mandatory | **False**: a production window does not comply and works | Production |
| A2 | SetHandler(this) mandatory | **True in vanilla, not needed with Dabs** | ViewController.c:63 |
| A3 | GetScreenSize returns 0 in constructor | **False**: Dabs TooltipView uses it right after the constructor | TooltipView.c:51 |
| A4 | Widget.Unlink() destroys widget | **Confirmed**: the engine comment and the ScriptView destructor | `P:\scripts\1_core\proto\enwidgets.c:173` |
| A5 | GetGame().IsServer() true on client during load | Not UI-relevant | — |
| A6 | DayZ colors 30-50% darker | **Retracted**: not an engine default. It is the player's `HUD_BRIGHTNESS`, which vanilla applies with the same two calls. `Widget.SetLV(0)` from a mod overrides the setting. Saturated colors barely affected, grays and pastels much darker: that remains true. See finding 6. | `P:\scripts\1_core\proto\enwidgets.c:114-117` and `SetHudBrightness` at `P:\scripts\3_game\dayzgame.c:3910-3919` |
| A7 | UIScaler ComputeScale | **Pending E12**, the multi resolution visual test. Later measurements answer it: exact layout values already scale with the screen height, so a script scaler doubles the scaling (rule 3 in `checklist-and-troubleshooting.md`) | — |
| A8 | Invalid SoundSets | **Confirmed**: commented as TODO | Production |
| A9 | UpdateInventoryMenu | Not UI-relevant | — |
| A10 | ref only in member fields | Conservative but safe | Dabs uses ref+autoptr |
| A11-A13 | DPI and resolution | **Pending E12** | — |

---

## Part 3: key findings

### 1. WidgetAnimator removes the need for a custom tween
Dabs has complete animation: position, size, rotation, color, alpha, text size.
30 easing curves. Loop. Color with blend modes. Used in production.

### 2. LinearColor provides complete color system
140+ named colors, HSV, Lerp, BlendModes, luminance. A base for a theme system.

### 3. ScriptViewMenu as an alternative for input management
It handles ChangeGameFocus, the cursor and the menu hierarchy on open. Trade off: it uses the UIManager menu stack. It does not close on ESC and does not release game focus on close (`dabs-mvc-internals.md`).

### 4. map<Widget, T> works
Dabs `ViewBindingHashMap = map<Widget, ViewBinding>` used throughout the MVC architecture.
Opens the door to a widget factory with map<string, ImageWidget>.

### 5. NotifyPropertyChanged is safe
Only touches bindings for the specific name. Does not scan or overwrite other fields.
The bug once blamed on it was FindAnyWidget returning incorrect refs inside ButtonWidget.

### 6. Widget.SetLV(0), retracted: do not call it from a mod
> **Retraction.** The measurement below is correct; the recipe deduced from it is not.
> `SetLV` and `SetTextLV` are `proto static` and global (`P:\scripts\1_core\proto\enwidgets.c:114-117`), and vanilla uses them
> to apply the brightness the player chose: `SetHudBrightness()` is those two calls and nothing else (`P:\scripts\3_game\dayzgame.c:3910-3914`),
> fed from `EDayZProfilesOptions.HUD_BRIGHTNESS` through `GetHUDBrightnessSetting()` (`P:\scripts\3_game\dayzgame.c:3916-3919`)
> in `OnInitialize()` (`P:\scripts\3_game\dayzgame.c:2109-2114`).
> Calling them in a mod's init **overrides the user's preference** across the entire HUD, including
> vanilla. And what the test measured was not an engine constant: it was the
> `HUD_BRIGHTNESS` of that machine. A helicopter HUD that removed both calls passed the same UI
> checks afterwards.

Tested in-engine. With the HUD brightness of that machine, pure
saturated colors (red, green, blue) were barely affected, and grays and pastels
(white, 50% gray, emerald, red400, blue400) came out significantly darker.
That remains true — and it is the player's setting doing its job.

### 7. ScrollWidget.VScrollToWidget(child) exists
Auto-scroll to a specific child. Perfect for a phone SMS view (scroll to latest).

### 8. ImageWidget has alpha mask system
LoadMaskTexture + SetMaskProgress + SetMaskTransitionWidth = "reveal"-type transitions
with gradient. Free for UI animations without extra code.

### 9. MultilineEditBoxWidget has cursor position
GetCarriageLine() + GetCarriagePos() — key for a PC terminal.

### 10. Function-as-command simplifies Relay_Command
`Relay_Command "OnSaveExecute"` + `bool OnSaveExecute(ButtonCommandArgs args)` in the
controller. Without needing to create separate RelayCommand classes.

---

## Part 4: pending runtime tests

One is still pending (E7 was closed, then its conclusion retracted):

| # | Test | Procedure | What for |
|---|---|---|---|
| **E7** | ~~Darkening factor + SetLV~~ | Closed, then retracted: `SetLV(0)` did brighten the colors on the test machine, because it overwrote that machine's HUD brightness setting (finding 6). Do not use it as a fix | ~~Theme system~~ |
| **E12** | Multi-resolution | Open panel at 720p/1080p/1440p. Screenshots. | Multi-res |

The color test mini mod in `color-test-harness.md` was prepared for E7. E12 is done by opening any existing panel at each resolution.
