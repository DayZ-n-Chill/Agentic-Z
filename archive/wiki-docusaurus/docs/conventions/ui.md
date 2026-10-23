# DayZ UI scripting realities (Tier 2 topic)

Part of Tier 2. Where DayZ UI colors come from and how each source is overridden. Read it together with the core rules in `.claude/skills/_shared/dayz-conventions.md`, which still apply.

## UI scripting realities (read before any "change the X color" task)

DayZ's UI has no central theme system; no `PrimaryAccentColor` constant flows through every widget. A color comes from three independent places, each overridden differently:

1. `.layout` files in `P:\gui\layouts\` (100+ files). Colors are baked per widget as RGBA values. `modded class` does not apply; overriding means shipping a same-named layout in your mod's `gui/layouts/`, which replaces the whole layout and is brittle across DayZ updates.
2. Inline ARGB literals in `P:\scripts\5_mission\gui\` (10+ files), such as `w.SetColor(0xFFFFEC44)` in `actionmenu.c:74`. Override the containing class's method with `modded class`, not the constant.
3. `Colors` / `FadeColors` constants in `P:\scripts\3_game\colors.c`. `modded class Colors { const int X = ...; }` is a no-op for compile-time constants, because callers baked the original value at compile time. `COLOR_DAYZ_RED` is referenced in one place across vanilla scripts (`P:\scripts\5_mission\gui\newui\mainmenu\mainmenupromo.c:157`), so even a working override would only recolor the main-menu promo banner.

So "change all the red UI to blue" is not a one-file task: it means sweeping `.layout` files per widget and overriding every class method that calls `SetColor(<red ARGB>)` in `5_mission/gui/`. That is hours of work. For new mods that need theming, build on CUI (Community UI Framework), which supplies the theme layer the engine lacks; for one-off recolors, scope the task to one element.

When the user asks for a color or theme change, ask for scope first (single element or sweep) and warn about the layout/script split before invoking any agent.

## Reference packs for UI work

Load these at the step that needs them, not up front:

- `.claude/skills/_shared/enscript/references/gui_layout.md`: the `.layout` format.
- `.claude/skills/_shared/enscript/references/widget_api.md`: widget script classes, events, loading layouts, menus and imagesets.
- `.claude/skills/_shared/enscript/integrations/dabs_framework.md`: Dabs Framework, only for mods that depend on it. Its facts are framework facts, not vanilla.
- `/dayz-build-imageset`: turns PNG icons into an imageset.
