---
name: dayz-layout-preview
description: "Renders a DayZ .layout to approximate PNG previews at several screen sizes (1280x720, 1920x1080, 2560x1440, 3440x1440 by default): widget boxes, panel colors, text and image placeholders placed from position, size, the exact toggles, halign and valign. Flags widgets that leave the screen, have no area or miss an exact toggle. Use when you want to see how a layout holds up at other resolutions without starting the game."
argument-hint: "<file.layout> [more.layout] [--sizes 1280x720,1920x1080] [--out <folder>] [--show-hidden] [--json]"
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-layout-preview

A script reads the `.layout`, works out every widget's box at each screen size and draws it. It starts no game and needs no DayZ Tools. The AI only looks at the PNGs and the findings and decides what to change.

Follow `.claude/skills/_shared/dayz-conventions.md`. The layout format itself is in `.claude/skills/_shared/figma-to-dayz-rules.md`.

It does not gate on `/dayz-preflight`: it reads only the `.layout` files you pass and needs no DayZ Tools, so a layout in your clone previews with P:\ unmounted. When an input path is on P:\ (a vanilla layout) and P:\ is not mounted, the script says so and points you to `/dayz-workdrive` instead of reporting a plain missing file.

## Requirements

Pillow draws the PNGs. If it is missing the script exits 2 with an install hint:

```cmd
python -m pip install -r "<skill-dir>\requirements.txt"
```

## How to run

```cmd
python "<skill-dir>\layout_preview.py" <file.layout> [more.layout ...] [options]
```

| Argument | Notes |
|---|---|
| `<file.layout>` | One or more layouts. Vanilla ones under `P:\gui\layouts\` work too. |
| `--sizes` | Comma separated `WIDTHxHEIGHT` list. Default `1280x720,1920x1080,2560x1440,3440x1440`. |
| `--out` | Folder for the PNGs. Default `output\layout-preview\` under the project root, wherever you run it from. A folder inside `workspace\<ModName>\` is refused (exit 1). |
| `--show-hidden` | Also draw widgets with `visible 0`, faded. By default they and their children are left out. |
| `--no-labels` | Leave widget names off the boxes. |
| `--json` | Print every widget's box at every size, and the findings, as JSON. Stdout then holds only the JSON; the `[OK]`, `[WARN]` and `[FAIL]` lines go to stderr. |

Each PNG is named `<layout>_<W>x<H>.png`. When two layouts in one run share a file name, their parent folder names go in front (`modA_gui_hud_1280x720.png`, `modB_gui_hud_1280x720.png`) so neither overwrites the other.

## Output and exit codes

One `[OK]` line per PNG, then one `[WARN]` line per finding. Exit 0 when every layout was drawn, 1 when a file is missing or cannot be parsed, a path is on P:\ while P:\ is not mounted (the line says to run `/dayz-workdrive`), or `--out` is inside a mod's workspace folder (the line says why), 2 when Pillow is missing.

| Finding | Means |
|---|---|
| `off-screen` | A shown widget's box goes past the screen edge at the listed sizes. Often a pixel offset that only fits wide screens. |
| `no-area` | A shown widget is under one pixel wide or high at the listed sizes, usually a tiny relative size. |
| `missing-toggle` | A widget sets `position` or `size` without all four exact toggles. The preview reads a missing toggle as 0 (relative); Workbench may not. |

## What the preview draws

- Frames as grey outlines, panels and windows filled with their `color`, images as a tinted box with a cross and the `image0` name, buttons in green, spacers in purple.
- Text from `text`, clipped to its box, at `"exact text size"` when `"exact text" 1` is set, aligned by `"text halign"` and `"text valign"`. Localized keys such as `#layout_...` are drawn as written.
- Children in `priority` order, so higher priority draws on top.

## How boxes are worked out

- `hexactsize 1` makes the width that many pixels; `hexactsize 0` makes it that fraction of the parent's width. The same goes for `vexactsize`, `hexactpos` and `vexactpos`.
- `halign right_ref` measures the x offset from the parent's right edge, `center_ref` from its center. `valign bottom_ref` and `center_ref` work the same way. The plain `right`, `center` and `bottom` values are treated the same as the `_ref` ones.
- `scaled 1` multiplies exact pixel values by the screen height divided by 1080.
- A `GridSpacerWidgetClass` splits its box, less `Padding` and `Margin`, into `Columns` by `Rows` cells and fills them in order. A `WrapSpacerWidgetClass` flows its children left to right and wraps at its width. Children of either ignore their own `position`.

## Limits

- It is an approximation, not the game renderer. Fonts, styles, imageset art, `fixaspect`, `"Size To Content"`, safe zones and script that moves widgets at run time are not drawn.
- The 1080 reference height for `scaled 1` is an assumption. Check a layout that depends on it in game with `/dayz-launch-test`.
- It reads structure loosely. A file the edit hook rejects may still draw; fix what the hook reports first.

## Do not

- Don't treat a clean preview as proof the layout loads. Workbench and the game are the judges; `dayz-layout-validator` checks the rules.
- Don't write PNGs into a mod folder; they would be packed into the PBO. The script refuses an `--out` under `workspace\<ModName>\`.
