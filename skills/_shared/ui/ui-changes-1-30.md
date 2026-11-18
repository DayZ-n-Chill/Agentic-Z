# UI changes in DayZ 1.30

What DayZ 1.30 changed in the vanilla UI: the action prompt HUD, the cursor info panels, the inventory slot icon classes and the preview widgets, the mod code each change breaks, and what to do about it.

What 1.29 had is not on `P:\`, so "before 1.30" lines are not checked. Lines marked "from the changelog" restate the 1.30 modding changelog and are not checked on `P:\` either.

## What changed

- The action prompt rows of `day_z_hud.layout` are `PanelWidgetClass`: `item` (`P:\gui\layouts\day_z_hud.layout:2424`), `interact` (`:2617`), `continuous_interact` (`:2910`), `single` (`:3203`), `continuous` (`:3431`), `ia_interact` (`:4314`) and `ia_continuous_interact` (`:4549`). Before 1.30 they were `ImageWidgetClass` loading textures such as `card_drop.edds` and `linear_gradient.edds`.
- The new style `ActionWidget` (`P:\gui\looknfeel\dayzwidgets.styles:3700`) draws a 9-slice frame from the `ActionWidgetGradient*` images of `dayz_gui` (`P:\gui\imagesets\dayz_gui.imageset:1920`). It sits on the two cursor containers, `ActionTargetsCursorWidget` (`P:\gui\layouts\day_z_hud.layout:2400`) and `ItemActions` (`:4061`); the rows carry a `color` and no `style`.
- `ActionTargetsCursor` builds extra info panels in `InitActionInfoPanels()` (`P:\scripts\5_mission\gui\actiontargetscursor.c:152` to `:158`): a `ConstructionActionInfoPanel` for the continuous interact slot and one for the continuous slot. The classes are `ActionInfoPanelBase`, `TargetActionInfoPanelBase` and `ConstructionActionInfoPanel` (`P:\scripts\5_mission\gui\inventorynew\containeditems\actioninfopanels.c:2`, `:5` and `:82`) over `Gui/layouts/new_ui/hud/action_info_spacer.layout` (`:31`). Details: `hud-action-info-panels.md`.
- The tools grid (`ConstructionActionInfoToolsGrid`, `P:\scripts\5_mission\gui\inventorynew\containeditems\actioninfogrids.c:103`) compares the `build_action_type` of the item in hand with `part.GetBuildIndicationTypeMask()` (`:134` to `:140`). The materials grid (`ConstructionActionInfoMaterialsGrid`, `:236`) shows quantities as rich text, `<color hex="...">X</color><color hex="...">/Y</color>` (`P:\scripts\5_mission\gui\inventorynew\containeditems\constructioninfoicons.c:347`).
- An action that cannot start has its button icons, `<name>_btn_icon` and `<name>_btn_icon_xbox`, dimmed with `SetAlpha(0.149)` (`P:\scripts\5_mission\gui\actiontargetscursor.c:1118` to `:1121`).
- `SetInteractXboxIcon`, `SetContinuousInteractXboxIcon`, `SetSingleXboxIcon`, `SetContinuousXboxIcon` and `SetXboxIcon` are `[Obsolete("no replacement")]` and declared with no body (`SetInteractXboxIcon` at `P:\scripts\5_mission\gui\actiontargetscursor.c:1369` to `SetXboxIcon` at `:1377`). `SetControllerIcon(string pWidgetName, string pInputName)` (`:146`) writes a rich text glyph for any controller through `InputUtils.GetRichtextButtonIconFromInputAction(...)` (`:149`); it is `protected`, so call it from a class that extends or mods `ActionTargetsCursor`.
- `SlotsIconBase: LayoutHolder` (`P:\scripts\5_mission\gui\inventorynew\containeditems\slotsiconbase.c:1`, 743 lines) holds the generic slot logic, and `SlotsIcon: SlotsIconBase` (`slotsicon.c:1`, 216 lines) keeps the event registration. `GenericIconBase: SlotsIconBase` (`genericicon.c:1`) draws icons outside the inventory on `Gui/layouts/new_ui/hud/SimpleIconTemplate.layout` (`:65`).
- `ItemPreviewWidget` gained `SetForceFlipEnable(bool enable)` and `SetForceFlip(bool value)` (`P:\scripts\3_game\gameplay.c:300` and `:301`). The changelog's `WorldToScreen` and `ScreenToWorld` for preview widgets and its switch for particles in previews are not exposed to script (`preview-widgets.md`).
- From the changelog: the Layout Editor moved to Enfusion 2023, and config parsing was updated for `*.layout` and `*.emat` files.

## What breaks and what to do

| What breaks | How bad | Cause | Fix |
|---|---|---|---|
| `ImageWidget.Cast(m_Root.FindAnyWidget("interact"))` returns null, and the next `LoadImageFile` or `SetColor` is a null pointer error | Crash | The rows are `PanelWidgetClass` (`P:\gui\layouts\day_z_hud.layout:2424` and the lines above) | Make the fields plain `Widget` and drop the cast. Vanilla scripts declare no `PanelWidget` class, so `PanelWidget.Cast` names a type that does not exist. Tint a row with `SetColor`, or change its look through the `ActionWidget` style or a layout variant (`layout-variants.md`). No `SetStyle` exists under `P:\scripts`. |
| Warnings from the Xbox icon setters | Medium | They are obsolete (`SetInteractXboxIcon`, `P:\scripts\5_mission\gui\actiontargetscursor.c:1369`) | Call `SetControllerIcon(widgetName, inputName)` (`:146`) |
| Slot changes do not reach the new cursor and HUD icons | Medium | `SlotsIcon` is no longer the only base; `SlotsIconBase` and `GenericIconBase` are | Mod `SlotsIconBase` for slot logic, or `GenericIconBase` for generic icons |
| Code that calls `WorldToScreen` on a preview | Low | Not exposed to script; `ItemPreviewWidget` declares no such method (`P:\scripts\3_game\gameplay.c:286` to `:313`) | Do not call it |

## Porting checklist

- Search the whole mod for `FindAnyWidget("interact")`, `"item"`, `"continuous_interact"`, `"single"`, `"continuous"`, `"ia_interact"` and `"ia_continuous_interact"`, and change `ImageWidget` to `Widget`.
- Replace calls to the `Set*XboxIcon` methods with `SetControllerIcon` in scripts that extend or mod `ActionTargetsCursor`.
- A mod that decorates inventory slots targets `SlotsIconBase` and still calls `super.InitIcon` and `super.InitIconWidgets` (`P:\scripts\5_mission\gui\inventorynew\containeditems\slotsiconbase.c:61` and `:95`).
- For a new panel on the cursor, read `hud-action-info-panels.md`.
- Compare your 9-slice styles with `ActionWidget` (`styles-format.md`).
- To change one vanilla widget in place, use a layout variant (`layout-variants.md`); the HUD and inventory layout map is in `vanilla-menus-map.md`.
