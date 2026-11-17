# DayZ 1.30: what changed in the vanilla UI, what breaks in a mod, and how to migrate

The changes DayZ 1.30 made to the action prompt HUD, the inventory slot icon classes and the preview widgets, the mod code each change breaks, and a migration checklist.

**How facts are marked here.** A `P:\` path with a line was opened and checked on `P:\` (DayZ 1.30). "Before 1.30" statements describe DayZ 1.29, which is not on `P:\`, so they are not checked. Lines marked "from the changelog" restate the 1.30 experimental modding changelog and are not checked on `P:\` either.

---

## Contents

- [What changed](#what-changed)
- [What breaks and how to migrate](#what-breaks-and-how-to-migrate)
- [Migration checklist](#migration-checklist)
- [Where the details are](#where-the-details-are)

## What changed

### 1. The action prompt rows in day_z_hud.layout are PanelWidgets

- These rows are `PanelWidgetClass` in 1.30: `item` (`P:\gui\layouts\day_z_hud.layout:2294`), `interact` (`:2477`), `continuous_interact` (`:2755`), `single` (`:3033`), `continuous` (`:3249`), `ia_interact` (`:4083`) and `ia_continuous_interact` (`:4306`). Before 1.30 they were `ImageWidgetClass` (not checked on `P:\`).
- The new style `ActionWidget` (`P:\gui\looknfeel\dayzwidgets.styles:3700`) draws a 9-slice frame from the `ActionWidgetGradient*` images of the `dayz_gui` imageset (`P:\gui\imagesets\dayz_gui.imageset:1917`). On `P:\` the style is set on the two containers, `GridSpacerWidgetClass ActionTargetsCursorWidget` (`P:\gui\layouts\day_z_hud.layout:2287`) and the second one at `:3859`; the rows themselves carry a `color` and no `style`.

### 2. Action info panels and construction grids on the cursor

- `ActionTargetsCursor` builds extra info panels through `InitActionInfoPanels()` (`P:\scripts\5_mission\gui\actiontargetscursor.c:152-158`): a `ConstructionActionInfoPanel` for the continuous interact slot and one for the continuous slot.
- The panel classes are `ActionInfoPanelBase`, `TargetActionInfoPanelBase` and `ConstructionActionInfoPanel` (`P:\scripts\5_mission\gui\inventorynew\containeditems\actioninfopanels.c:2`, `:5` and `:82`), over the layout `Gui/layouts/new_ui/hud/action_info_spacer.layout` (set at `:31`).
- The tools grid (`ConstructionActionInfoToolsGrid`, `P:\scripts\5_mission\gui\inventorynew\containeditems\actioninfogrids.c:103`) compares the `build_action_type` config value of the item in hands with `part.GetBuildIndicationTypeMask()` (`:134-140`). The materials grid (`ConstructionActionInfoMaterialsGrid`, `:236`) shows quantities as RichText: `<color hex="...">X</color><color hex="...">/Y</color>` (`P:\scripts\5_mission\gui\inventorynew\containeditems\constructioninfoicons.c:347`).
- Icons no longer depend on the inventory tree: `GenericIconBase: SlotsIconBase` (`P:\scripts\5_mission\gui\inventorynew\containeditems\genericicon.c:1`) uses `Gui/layouts/new_ui/hud/SimpleIconTemplate.layout` (`:65`).

### 3. Actions that cannot start are dimmed

When `!action.CanBeStarted()`, the button icons (`<name>_btn_icon` and `<name>_btn_icon_xbox`) get `SetAlpha(0.149)` (`P:\scripts\5_mission\gui\actiontargetscursor.c:1118-1121`).

### 4. The Xbox icon setters are obsolete

- `SetInteractXboxIcon`, `SetContinuousInteractXboxIcon`, `SetSingleXboxIcon`, `SetContinuousXboxIcon` and `SetXboxIcon` are marked `[Obsolete("no replacement")]` and have no body (`P:\scripts\5_mission\gui\actiontargetscursor.c:1368-1377`).
- Their job is done by `SetControllerIcon(string pWidgetName, string pInputName)` (`:146`), which writes a RichText glyph for any controller with `InputUtils.GetRichtextButtonIconFromInputAction(...)` (`:149`). It is `protected`, so call it from a class that extends or mods `ActionTargetsCursor`.

### 5. SlotsIconBase was split out of SlotsIcon

`SlotsIconBase: LayoutHolder` (`P:\scripts\5_mission\gui\inventorynew\containeditems\slotsiconbase.c:1`, 743 lines) now holds the generic slot logic, and `SlotsIcon: SlotsIconBase` (`P:\scripts\5_mission\gui\inventorynew\containeditems\slotsicon.c:1`, 216 lines) is left with event registration.

### 6. Preview widget calls

- `ItemPreviewWidget` gained `SetForceFlipEnable(bool enable)` and `SetForceFlip(bool value)` (`P:\scripts\3_game\gameplay.c:300-301`). The preview classes are `PreviewWidget`, `ItemPreviewWidget` and `PlayerPreviewWidget` (`P:\scripts\3_game\gameplay.c:276`, `:286` and `:305`).
- The changelog ticket T181406 promised `WorldToScreen` and `ScreenToWorld` on preview widgets. Neither name appears anywhere under `P:\scripts`, so script cannot call them. Turning particles off in previews is not exposed either.

### 7. Editor and parser updates (from the changelog)

- The Layout Editor was updated to Enfusion 2023.
- Enfusion config parsing was updated for `*.layout` and `*.emat` files.

## What breaks and how to migrate

| What breaks | Severity | Cause | Migration |
|---|---|---|---|
| `ImageWidget.Cast(m_Root.FindAnyWidget("interact"))` returns null | Critical | The prompt rows are `PanelWidgetClass` (`P:\gui\layouts\day_z_hud.layout:2294`, `:2477` and the others above) | Change the fields to plain `Widget` and drop the cast: vanilla scripts declare no `PanelWidget` class (a grep of `P:\scripts\` for `class PanelWidget` finds none), so `PanelWidget.Cast(...)` names a type they do not have. For a custom background, tint the row with `SetColor`, or change the look through the `ActionWidget` style or a layout variant (`layout-variants-130.md`). Do not use `w.SetStyle(...)`: no `SetStyle` is declared or called anywhere under `P:\scripts` |
| Compile warnings from the obsolete Xbox setters | Medium | `SetInteractXboxIcon` and the others are `[Obsolete]` (`P:\scripts\5_mission\gui\actiontargetscursor.c:1368`) | Use `SetControllerIcon(widgetName, inputName)` (`:146`) |
| Changes to slots do not reach the new cursor and HUD icons | Medium | `SlotsIcon` is no longer the single base class; `SlotsIconBase` was split out and `GenericIconBase` added | Mod or extend `SlotsIconBase` for slot logic, or `GenericIconBase` for generic icons |
| Code assumes `WorldToScreen` on previews | Low | The ticket was not exposed to script (`P:\scripts\3_game\gameplay.c:276-313`) | Do not call `WorldToScreen` or `ScreenToWorld` on `ItemPreviewWidget` or `PlayerPreviewWidget` |

## Migration checklist

- [ ] Search the whole mod for `FindAnyWidget("interact")`, `"item"`, `"continuous_interact"`, `"single"`, `"continuous"` and `"ia_interact"`, and replace `ImageWidget` with plain `Widget`.
- [ ] Remove calls to the `Set*XboxIcon` methods in scripts that extend or mod `ActionTargetsCursor`; use `SetControllerIcon`.
- [ ] A mod that decorated inventory slots: check that its extensions target `SlotsIconBase` and still call `super.InitIcon` and `super.InitIconWidgets` (`P:\scripts\5_mission\gui\inventorynew\containeditems\slotsiconbase.c:61` and `:95`).
- [ ] For a new panel on the cursor, read the panel architecture in `hud-action-info-panels.md`.
- [ ] Check your 9-slice styles against the new `ActionWidget` style (`styles-format.md`).

## Where the details are

| Topic | File |
|---|---|
| Cursor info panels and construction grids | `hud-action-info-panels.md` |
| HUD map and inventory architecture | `vanilla-menus-map.md` |
| Widget API, with the preview widgets | `widget-api.md` |
| The `.styles` system | `styles-format.md` |
| Changing one vanilla widget in place with a 1.30 layout variant | `layout-variants-130.md` |
