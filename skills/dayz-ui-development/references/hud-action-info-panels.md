# HUD action info panels and cursor construction grids (DayZ 1.30)

How the 1.30 interaction cursor shows the tools and materials an action needs: the classes, the layouts, and how a mod adds its own panel. Read it before modding `ActionTargetsCursor` or building a HUD panel that shows item icons outside the inventory.

Added 2026-09-16 from DayZ Experimental 1.30 (build 1.30.164014): `ActionTargetsCursor.c`, `ActionInfoPanels.c`, `ActionInfoGrids.c`, `ConstructionInfoIcons.c`, `GenericIcon.c`, and the layouts `action_info_spacer.layout`, `SimpleIconTemplate.layout` and `day_z_hud.layout`. The `path:line` citations were re-read on a `P:\` holding 1.30. The action info classes, `GenericIcon.c` and the two layouts `action_info_spacer.layout` and `SimpleIconTemplate.layout` are 1.30 additions; `ActionTargetsCursor.c` and `day_z_hud.layout` also exist in 1.29, without the parts described here.

---

## 1. Overview & Architecture

In DayZ 1.30, the interaction cursor (`ActionTargetsCursor`) gains a modular subsystem for contextual action information, specifically designed for multi-stage construction, crafting, and repair actions:

```
ActionTargetsCursor (5_Mission/GUI/ActionTargetsCursor.c)
 └── m_TargetActionInfoPanelMap: map<int, ref array<ref TargetActionInfoPanelBase>>
      └── TargetActionInfoPanelBase (P:\scripts\5_mission\gui\inventorynew\containeditems\actioninfopanels.c:5) [LayoutHolder]
           ├── Layout: "Gui/layouts/new_ui/hud/action_info_spacer.layout"
           └── ConstructionActionInfoPanel (P:\scripts\5_mission\gui\inventorynew\containeditems\actioninfopanels.c:82)
                ├── ConstructionActionInfoToolsGrid (SecondaryGrid0) [ActionInfoGridBase]
                │    └── array<ref GenericIconBase> (ConstructionToolInfoIcon)
                ├── Widget m_Separator ("Separator")
                └── ConstructionActionInfoMaterialsGrid (SecondaryGrid1) [ActionInfoGridBase]
                     └── array<ref GenericIconBase> (ConstructionMaterialInfoIcon)
```

This replaces hardcoded cursor labels with dynamic visual grids showing:
1. **Required tools** for the action (highlighted or ghosted depending on hands/inventory state).
2. **Required materials** with formatted RichText quantity indicators (`<color hex="...">X</color><color hex="...">/Y</color>`).

---

## 2. ActionTargetsCursor Integration

### 2.1. Panel Initialization & Registration

In `P:\scripts\5_mission\gui\actiontargetscursor.c:152-176`, panels are registered by action category:

```c
// [EXACT] P:\scripts\5_mission\gui\actiontargetscursor.c:152
protected void InitActionInfoPanels()
{
	m_TargetActionInfoPanelMap = new map<int, ref array<ref TargetActionInfoPanelBase>>();
	m_ActiveInfoPanels = new array<ref TargetActionInfoPanelBase>();

	CreateActionInfoPanel(ConstructionActionInfoPanel,ACTION_ORDER_INTERACT_CONTINUOUS); //hand builds (regular + indication only)
	CreateActionInfoPanel(ConstructionActionInfoPanel,ACTION_ORDER_CONTINUOUS); //build (regular + indication only)

	m_Root.Update();
}

protected void CreateActionInfoPanel(typename panelType, int actionCategory)
{
	TargetActionInfoPanelBase tInfoPanel = TargetActionInfoPanelBase.Cast(panelType.Spawn());
	tInfoPanel.SetParentWidget(m_Root);
	m_Root.AddChild(tInfoPanel.GetMainWidget(),false); //ce n'est pas un LayoutHolder, bypassing inheritance
	tInfoPanel.Init();

	if (!m_TargetActionInfoPanelMap.Get(actionCategory))
		m_TargetActionInfoPanelMap.Set(actionCategory,new array<ref TargetActionInfoPanelBase>());

	array<ref TargetActionInfoPanelBase> tmp = m_TargetActionInfoPanelMap.Get(actionCategory);
	tmp.Insert(tInfoPanel);
	m_TargetActionInfoPanelMap.Set(actionCategory, tmp);
}
```

The French comment on the `AddChild` line is vanilla's ("it is not a LayoutHolder"). The two category keys are constants of the cursor class: `ACTION_ORDER_INTERACT_CONTINUOUS = 1` and `ACTION_ORDER_CONTINUOUS = 3` (`P:\scripts\5_mission\gui\actiontargetscursor.c:56`, `:58`).

### 2.2. Per-Frame Target Info Update

When an action is active, `ActionTargetsCursor.UpdateAdditionalActionInfo` (`P:\scripts\5_mission\gui\actiontargetscursor.c:1268-1292`) iterates over `m_ActionMap` and, for each action with `IsTargetInfoAction()`, updates its panels (or clears them if it no longer applies):

```c
// [EXACT] P:\scripts\5_mission\gui\actiontargetscursor.c:1268-1292
	protected void UpdateAdditionalActionInfo()
	{
		m_ActiveInfoPanels.Clear();

		foreach (int actionType, ActionBase action : m_ActionMap)
		{
			bool update = action != null && action.IsTargetInfoAction();
			array<ref TargetActionInfoPanelBase> tmp = m_TargetActionInfoPanelMap.Get(actionType);
			if (tmp)
			{
				foreach (TargetActionInfoPanelBase panel : tmp)
				{
					if (update)
					{
						panel.UpdateTargetActionInfoPanel(action.GetClientActionInfo(),m_Target);
						m_ActiveInfoPanels.Insert(panel);
					}
					else if (panel.IsVisible())
					{
						panel.PerformPanelCleanup();
					}
				}
			}
		}
	}
```

### 2.3. Visual Dimming for Non-Startable Actions

In `P:\scripts\5_mission\gui\actiontargetscursor.c:1118-1122`, if an action cannot currently be started (`!action.CanBeStarted()`), button prompt icons are dimmed to alpha `0.149` (normal is `1.0`):

```c
// [EXACT] P:\scripts\5_mission\gui\actiontargetscursor.c:1118
if (!action.CanBeStarted())
{
	widget.FindAnyWidget(actionWidget + "_btn_icon_xbox").SetAlpha(0.149);
	widget.FindAnyWidget(actionWidget + "_btn_icon").SetAlpha(0.149);
}
```

### 2.4. Universal Controller Icon Binding (Gamepad / Console)

Legacy Xbox-specific icon setters are deprecated in 1.30:
```c
// [EXACT] P:\scripts\5_mission\gui\actiontargetscursor.c:1368-1377
[Obsolete("no replacement")]
void SetInteractXboxIcon(string imageset_name, string image_name);
[Obsolete("no replacement")]
void SetContinuousInteractXboxIcon(string imageset_name, string image_name);
[Obsolete("no replacement")]
void SetSingleXboxIcon(string imageset_name, string image_name);
[Obsolete("no replacement")]
void SetContinuousXboxIcon(string imageset_name, string image_name);
[Obsolete("no replacement")]
protected void SetXboxIcon(string name, string imageset_name, string image_name);
```

Replaced by the universal `SetControllerIcon`:
```c
// [EXACT] P:\scripts\5_mission\gui\actiontargetscursor.c:146-150
protected void SetControllerIcon(string pWidgetName, string pInputName)
{
	RichTextWidget w = RichTextWidget.Cast(m_Root.FindAnyWidget(pWidgetName + "_btn_icon_xbox"));
	w.SetText(InputUtils.GetRichtextButtonIconFromInputAction(pInputName, "", EUAINPUT_DEVICE_CONTROLLER));
}
```
*(up to 1.29: Set*XboxIcon methods with fixed Xbox images; since 1.30: SetControllerIcon with cross-platform RichText glyphs).*

---

## 3. Layout Structure

### 3.1. `action_info_spacer.layout`

Path: `P:\gui\layouts\new_ui\hud\action_info_spacer.layout:1`

Hierarchy:
```
WrapSpacerWidgetClass MainWrap (size 350 51, Size To Content V 1)
 └── GridSpacerWidgetClass MainGrid (Columns 100, Rows 100)
      ├── GridSpacerWidgetClass SecondaryGrid0 (size 51 51, Rows 100)  <-- Tools grid
      │    └── WrapSpacerWidgetClass IconMarginCard_Wrap4..6 (size 55 55)
      │         └── ImageWidgetClass IconBg_Image4..6 (size 51 51)
      ├── PanelWidgetClass Separator (size 14 55)
      │    └── ImageWidgetClass Spacer_Image (size 3 15, image0 "")
      └── GridSpacerWidgetClass SecondaryGrid1 (size 51 51, Columns 5, Rows 100)  <-- Materials grid
           └── WrapSpacerWidgetClass IconMarginCard_Wrap1..3 (size 55 55)
                └── ImageWidgetClass IconBg_Image1..3 (size 51 51)
```

The third image under `SecondaryGrid0` is spelled `IconBg_Imag6` in the vanilla file (line 117).

### 3.2. `SimpleIconTemplate.layout`

Path: `P:\gui\layouts\new_ui\hud\simpleicontemplate.layout:1`

Hierarchy used by `GenericIconBase` (the widgets its script looks up; the file holds a few more):
```
FrameWidgetClass Icon (size 59 59)
 ├── ImageWidgetClass ImageBackdrop (color 0 0 0 0.231)
 ├── PanelWidgetClass EmptySelected (style Outline)
 ├── ImageWidgetClass GhostSlot (set:dayz_inventory image:missing, color 1 1 1 0.4)
 ├── PanelWidgetClass Col (style rover_sim_colorable)
 └── PanelWidgetClass PanelWidget (style blank)
      ├── ItemPreviewWidgetClass Render
      │    └── OutOfReach, Mounted, AmmoIcon, Cursor, TemperaturePanel
      └── PanelWidgetClass QuantityPanel
           ├── ProgressBarWidgetClass QuantityBar
           ├── GridSpacerWidgetClass QuantityStackPanel
           │    └── RichTextWidgetClass Quantity
           └── GridSpacerWidgetClass QuantityStackPanel0
                └── TextWidgetClass Quantity0
```

---

## 4. Class Hierarchy & Script API

### 4.1. `TargetActionInfoPanelBase` & `ConstructionActionInfoPanel`

Located in `P:\scripts\5_mission\gui\inventorynew\containeditems\actioninfopanels.c:1-109`:

```c
// [EXACT] P:\scripts\5_mission\gui\inventorynew\containeditems\actioninfopanels.c:5-20
class TargetActionInfoPanelBase: ActionInfoPanelBase
{
	protected int m_VisibleGridCount;
	protected ActionInfoDataBase m_ActionInfo;
	protected ActionTarget m_Target;
	protected ref array<ref ActionInfoGridBase> m_GridsArray;

	void Init()
	{
		InitGridStructure();
	}

	protected void InitGridStructure()
	{
		m_GridsArray = new array<ref ActionInfoGridBase>();
	}
```

`ConstructionActionInfoPanel` (`P:\scripts\5_mission\gui\inventorynew\containeditems\actioninfopanels.c:82-108`) creates the two grids and toggles the separator in `UpdateInterval` (`:100-108`):

```c
// [EXACT] P:\scripts\5_mission\gui\inventorynew\containeditems\actioninfopanels.c:82-98
class ConstructionActionInfoPanel: TargetActionInfoPanelBase
{
	protected Widget m_Separator;

	void ConstructionActionInfoPanel(LayoutHolder parent)
	{
	}

	override protected void InitGridStructure()
	{
		super.InitGridStructure();

		m_GridsArray.Insert(new ConstructionActionInfoToolsGrid(this, m_RootWidget.FindAnyWidget("SecondaryGrid0")));
		m_GridsArray.Insert(new ConstructionActionInfoMaterialsGrid(this, m_RootWidget.FindAnyWidget("SecondaryGrid1")));

		m_Separator = m_RootWidget.FindAnyWidget("Separator");
	}
```

### 4.2. `ActionInfoGrids`

Located in `P:\scripts\5_mission\gui\inventorynew\containeditems\actioninfogrids.c:1-290`:

- **`ActionInfoGridBase: LayoutHolder`** (`:1`): Manages an array of `GenericIconBase` instances, dynamically allocates new icon wrappers via `CreateNewIcon(int idx = -1)` (`:40`), and handles hide/show logic. Both construction grids extend `ConstructionActionInfoGrid: ActionInfoGridBase` (`:86`).
- **`ConstructionActionInfoToolsGrid`** (`:103`): Reads the tool in the player's hands, takes its bitmask from config (`toolCfgPath = "cfgVehicles" + " " + tool.GetType() + " " + "build_action_type"`, `:140`; `TOOL_HANDS` with no tool) and matches it against `part.GetBuildIndicationTypeMask()` (`:134`). Populates one `ConstructionToolInfoIcon` per `EConstructionTools` bit.
- **`ConstructionActionInfoMaterialsGrid`** (`:236`): Creates five `ConstructionMaterialInfoIcon`s (`DEFAULT_MATERIAL_ICON_COUNT`, `:238`) and hands each the current `ConstructionPart` and the target entity. Each icon reads its own material from `m_Part.GetMaterialsData()` (slot name `m_MaterialSlotName`, required amount `m_MaterialQuantity`; `P:\scripts\5_mission\gui\inventorynew\containeditems\constructioninfoicons.c:223`, `:390`).

### 4.3. `GenericIconBase` & `ConstructionInfoIcons`

- **`GenericIconBase: SlotsIconBase`** (`P:\scripts\5_mission\gui\inventorynew\containeditems\genericicon.c:1`):
  Extends `SlotsIconBase` to render standalone icons outside `InventoryMenu`.
  Notice that `m_QuantityItem` is cast to `RichTextWidget` rather than `TextWidget`:
  `m_QuantityItem = RichTextWidget.Cast(m_MainWidget.FindAnyWidget("Quantity"));` (`P:\scripts\5_mission\gui\inventorynew\containeditems\genericicon.c:37`)

- **`ConstructionToolInfoIcon: ConstructionInfoIcon`** (`P:\scripts\5_mission\gui\inventorynew\containeditems\constructioninfoicons.c:52`):
  Maps `EConstructionTools` values to icons of the `dayz_inventory` imageset (`InitGhostIcon`, `:64-105`; the default is `image:missing`):
  - `TOOL_MOUNT_WIRE` -> `"image:plierstools"`
  - `TOOL_NAIL` / `TOOL_MOUNT_LOG` -> `"image:hammertools"`
  - `TOOL_DIG_BASE` -> `"image:shoveltools"`
  - `TOOL_HEAVY` -> `"image:sladgehammertools"` (vanilla's spelling)
  - `TOOL_EXCAVATION` -> `"image:pickaxetools"`
  - `TOOL_HANDS` -> `"image:hands"`
  - `TOOL_BRICKLAYING` -> `"image:bricklayingtools"`

- **`ConstructionMaterialInfoIcon: ConstructionInfoIcon`** (`P:\scripts\5_mission\gui\inventorynew\containeditems\constructioninfoicons.c:161`):
  Formats material amounts dynamically with RichText color formatting:
  `RichTextWidget.Cast(m_QuantityItem).SetText(string.Format("<color hex=\"%1\">%2</color><color hex=\"%3\">/%4</color>", ...))` (`:347`, `:377`)

---

## 5. Extension & Modding Patterns

To attach a custom information panel to the cursor in a mod:
1. Subclass `TargetActionInfoPanelBase`. `CreateActionInfoPanel` casts the spawned panel to that class and calls its `Init()`, so a bare `ActionInfoPanelBase` subclass does not work there.
2. Override `SetLayoutName()` to point to your custom spacer/grid layout.
3. In a `modded class ActionTargetsCursor`, override `InitActionInfoPanels()`, call `super.InitActionInfoPanels()` first, and register your panel via `CreateActionInfoPanel(MyCustomInfoPanel, ACTION_ORDER_CONTINUOUS)`.
4. In your custom action (`ActionBase`), implement `override bool IsTargetInfoAction() { return true; }` and return your payload in `override ActionInfoDataBase GetClientActionInfo()` (`P:\scripts\4_world\classes\useractionscomponent\actionbase.c:277`, `:282`).

This recipe is read from the vanilla code above; it has not been run in game.
