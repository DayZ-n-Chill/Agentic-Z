# Action info panels on the cursor

How the DayZ 1.30 interaction cursor shows the tools and materials a build action needs, which classes and layouts draw it, and how a mod adds its own panel. Read it before you mod `ActionTargetsCursor` or show item icons outside the inventory.

The action info classes, `GenericIcon.c`, `action_info_spacer.layout` and `SimpleIconTemplate.layout` are new in 1.30. `ActionTargetsCursor.c` and `day_z_hud.layout` exist in 1.29 too, without these parts.

## How it fits together

`ActionTargetsCursor` keeps a map from action category to panels, `m_TargetActionInfoPanelMap: map<int, ref array<ref TargetActionInfoPanelBase>>`. Vanilla registers one panel type, `ConstructionActionInfoPanel`, which holds two grids of icons and a separator:

| Part | Class | Widget | Shows |
|---|---|---|---|
| Panel | `ConstructionActionInfoPanel` (`P:\scripts\5_mission\gui\inventorynew\containeditems\actioninfopanels.c:82`), a `TargetActionInfoPanelBase` (`:5`) | Root of `Gui/layouts/new_ui/hud/action_info_spacer.layout` | |
| Tools grid | `ConstructionActionInfoToolsGrid` | `SecondaryGrid0` | One `ConstructionToolInfoIcon` per tool, lit or ghosted by what the player holds |
| Separator | `Widget m_Separator` | `Separator` | Shown only when both grids have icons |
| Materials grid | `ConstructionActionInfoMaterialsGrid` | `SecondaryGrid1` | `ConstructionMaterialInfoIcon`s with a colored "have / need" count in rich text |

## Registration and update

`InitActionInfoPanels` registers panels per category (`P:\scripts\5_mission\gui\actiontargetscursor.c:152` to `:176`):

```c
protected void InitActionInfoPanels()
{
	m_TargetActionInfoPanelMap = new map<int, ref array<ref TargetActionInfoPanelBase>>();
	m_ActiveInfoPanels = new array<ref TargetActionInfoPanelBase>();

	CreateActionInfoPanel(ConstructionActionInfoPanel,ACTION_ORDER_INTERACT_CONTINUOUS); //hand builds (regular + indication only)
	CreateActionInfoPanel(ConstructionActionInfoPanel,ACTION_ORDER_CONTINUOUS); //build (regular + indication only)

	m_Root.Update();
}
```

`CreateActionInfoPanel` spawns the type, casts it to `TargetActionInfoPanelBase`, calls `SetParentWidget(m_Root)`, adds its main widget to `m_Root` with `AddChild(..., false)`, calls `Init()` and appends it to the category's array. The French comment vanilla puts on the `AddChild` line says "it is not a LayoutHolder". The category keys are cursor constants: `ACTION_ORDER_INTERACT_CONTINUOUS = 1` and `ACTION_ORDER_CONTINUOUS = 3` (`actiontargetscursor.c:56` and `:58`).

Each frame `UpdateAdditionalActionInfo` (`actiontargetscursor.c:1268` to `:1292`) clears `m_ActiveInfoPanels`, walks `m_ActionMap`, and for every action whose `IsTargetInfoAction()` is true calls `panel.UpdateTargetActionInfoPanel(action.GetClientActionInfo(), m_Target)` on that category's panels and marks them active. A visible panel whose action no longer applies gets `PerformPanelCleanup()`.

## Other 1.30 cursor changes

- An action that can't start yet dims its button prompt icons to alpha `0.149` instead of `1.0`: `if (!action.CanBeStarted())` sets `SetAlpha(0.149)` on `<row>_btn_icon_xbox` and `<row>_btn_icon` (`actiontargetscursor.c:1118` to `:1122`).
- The Xbox icon setters are marked `[Obsolete("no replacement")]`: `SetInteractXboxIcon`, `SetContinuousInteractXboxIcon`, `SetSingleXboxIcon`, `SetContinuousXboxIcon` and `SetXboxIcon` (`:1368` to `:1377`). The cursor now uses one setter that writes a rich text glyph for the bound controller button:

```c
protected void SetControllerIcon(string pWidgetName, string pInputName)
{
	RichTextWidget w = RichTextWidget.Cast(m_Root.FindAnyWidget(pWidgetName + "_btn_icon_xbox"));
	w.SetText(InputUtils.GetRichtextButtonIconFromInputAction(pInputName, "", EUAINPUT_DEVICE_CONTROLLER));
}
```

From `actiontargetscursor.c:146` to `:150`. Up to 1.29 the setters loaded fixed Xbox images.

## The layouts

`P:\gui\layouts\new_ui\hud\action_info_spacer.layout:1`:

| Widget | Class | Size | Notes |
|---|---|---|---|
| `MainWrap` | `WrapSpacerWidgetClass` | 350 by 51 | `"Size To Content V" 1` |
| `MainGrid` | `GridSpacerWidgetClass` | | Columns 100, rows 100 |
| `SecondaryGrid0` | `GridSpacerWidgetClass` | 51 by 51 | Tools; rows 100 |
| `IconMarginCard_Wrap4` to `6` | `WrapSpacerWidgetClass` | 55 by 55 | Each holds an `IconBg_Image` of 51 by 51 |
| `Separator` | `PanelWidgetClass` | 14 by 55 | Holds `Spacer_Image`, 3 by 15, empty `image0` |
| `SecondaryGrid1` | `GridSpacerWidgetClass` | 51 by 51 | Materials; columns 5, rows 100 |
| `IconMarginCard_Wrap1` to `3` | `WrapSpacerWidgetClass` | 55 by 55 | Each holds an `IconBg_Image` of 51 by 51 |

The third tools image is spelled `IconBg_Imag6` in the vanilla file (`:117`); keep that spelling if you look it up.

`GenericIconBase` loads `SimpleIconTemplate.layout`, whose root is `FrameWidgetClass Icon` (`P:\gui\layouts\new_ui\hud\simpleicontemplate.layout:1`). The widgets its script looks up (the file holds a few more):

| Widget | Class | Notes |
|---|---|---|
| `Icon` | `FrameWidgetClass` | 59 by 59, the root |
| `ImageBackdrop` | `ImageWidgetClass` | Color `0 0 0 0.231` |
| `EmptySelected` | `PanelWidgetClass` | Style `Outline` |
| `GhostSlot` | `ImageWidgetClass` | `set:dayz_inventory image:missing`, color `1 1 1 0.4` |
| `Col` | `PanelWidgetClass` | Style `rover_sim_colorable` |
| `PanelWidget` | `PanelWidgetClass` | Style `blank`; holds the rest |
| `Render` | `ItemPreviewWidgetClass` | With `OutOfReach`, `Mounted`, `AmmoIcon`, `Cursor`, `TemperaturePanel` |
| `QuantityPanel` | `PanelWidgetClass` | Holds `QuantityBar` (progress bar), `Quantity` (rich text) and `Quantity0` (text) |

## The classes

`TargetActionInfoPanelBase` (`actioninfopanels.c:5` to `:20`) extends `ActionInfoPanelBase` and holds `m_VisibleGridCount`, `m_ActionInfo`, `m_Target` and `m_GridsArray`; `Init()` calls `InitGridStructure()`, which creates the array. `ConstructionActionInfoPanel` (`:82` to `:108`) overrides `InitGridStructure` to add both grids and find `Separator`, and shows or hides the separator in `UpdateInterval` (`:100` to `:108`):

```c
override protected void InitGridStructure()
{
	super.InitGridStructure();
	m_GridsArray.Insert(new ConstructionActionInfoToolsGrid(this, m_RootWidget.FindAnyWidget("SecondaryGrid0")));
	m_GridsArray.Insert(new ConstructionActionInfoMaterialsGrid(this, m_RootWidget.FindAnyWidget("SecondaryGrid1")));
	m_Separator = m_RootWidget.FindAnyWidget("Separator");
}
```

In `P:\scripts\5_mission\gui\inventorynew\containeditems\actioninfogrids.c`:

- `ActionInfoGridBase: LayoutHolder` (`:1`) keeps an array of `GenericIconBase`, makes new icons with `CreateNewIcon(int idx = -1)` (`:40`) and shows or hides them. Both construction grids extend `ConstructionActionInfoGrid` (`:86`).
- `ConstructionActionInfoToolsGrid` (`:103`) reads the tool in the player's hands, takes its mask from `cfgVehicles <type> build_action_type` (`:140`; `TOOL_HANDS` with no tool) and matches it against `part.GetBuildIndicationTypeMask()` (`:134`), adding one icon per `EConstructionTools` bit.
- `ConstructionActionInfoMaterialsGrid` (`:236`) makes five icons (`DEFAULT_MATERIAL_ICON_COUNT`, `:238`) and hands each the current `ConstructionPart` and target. Each icon reads its material from `m_Part.GetMaterialsData()`: slot name `m_MaterialSlotName` and required amount `m_MaterialQuantity` (`P:\scripts\5_mission\gui\inventorynew\containeditems\constructioninfoicons.c:223` and `:390`).

`GenericIconBase` extends `SlotsIconBase` to draw icons outside the inventory menu (`P:\scripts\5_mission\gui\inventorynew\containeditems\genericicon.c:1`). Its quantity is a rich text widget: `m_QuantityItem = RichTextWidget.Cast(m_MainWidget.FindAnyWidget("Quantity"));` (`genericicon.c:37`).

`ConstructionToolInfoIcon` (`constructioninfoicons.c:52`) maps each tool to a `dayz_inventory` image in `InitGhostIcon` (`:64` to `:105`); the default is `image:missing`:

| Tool | Image |
|---|---|
| `TOOL_MOUNT_WIRE` | `image:plierstools` |
| `TOOL_NAIL`, `TOOL_MOUNT_LOG` | `image:hammertools` |
| `TOOL_DIG_BASE` | `image:shoveltools` |
| `TOOL_HEAVY` | `image:sladgehammertools` (vanilla's spelling) |
| `TOOL_EXCAVATION` | `image:pickaxetools` |
| `TOOL_HANDS` | `image:hands` |
| `TOOL_BRICKLAYING` | `image:bricklayingtools` |

`ConstructionMaterialInfoIcon` (`constructioninfoicons.c:161`) writes the count as `string.Format("<color hex=\"%1\">%2</color><color hex=\"%3\">/%4</color>", ...)` into the rich text widget (`:347` and `:377`).

## Adding your own panel

Read from the vanilla code above; not run in game.

1. Subclass `TargetActionInfoPanelBase`. `CreateActionInfoPanel` casts to that class and calls `Init()`, so a bare `ActionInfoPanelBase` subclass does not work there.
2. Override `SetLayoutName()` to point at your own spacer and grid layout.
3. In a `modded class ActionTargetsCursor`, override `InitActionInfoPanels()`, call `super.InitActionInfoPanels()` first, then `CreateActionInfoPanel(MyMod_InfoPanel, ACTION_ORDER_CONTINUOUS)`.
4. In your action, return true from `IsTargetInfoAction()` and your payload from `GetClientActionInfo()` (`P:\scripts\4_world\classes\useractionscomponent\actionbase.c:277` and `:282`).
