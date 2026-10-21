---
name: dayz-build-imageset
---

## Overview

Packs the PNG sprites in each `<mod>/.gui-sources/<setname>/` folder into a DayZ imageset (`.imageset` definition + `.paa` atlas) under `<mod>/gui/imagesets/`, with a 10px gutter around every sprite and power-of-two atlas sizes. Use when a mod's HUD or menu icons need to become an imageset that `.layout` files can reference.

> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-build-imageset

Pack a folder of PNG sprites into a DayZ imageset (atlas + `.imageset` definition file). Source images stay in `.gui-sources/`, which `/dayz-build-pbo` leaves out of the PBO (its `exclude.lst` drops `.gui-sources\`); only the packed `.paa` atlas and `.imageset` file land under `gui/imagesets/` where the engine expects them.

Layout convention:

```
<mod-root>/
  .gui-sources/
    my_icons/
      hud_health.png
      hud_stamina.png
      hud_thirst.png
    main_menu/
      ...
  gui/
    imagesets/
      my_icons.imageset      <- generated
      my_icons.paa           <- generated
      main_menu.imageset
      main_menu.paa
```

Follow `.claude/skills/_shared/dayz-conventions.md`.

## Requirements

Pillow composes the atlas. If it is missing the script exits 1 with an install hint:

```cmd
python -m pip install -r "<skill-dir>\requirements.txt"
```

## How to run

```cmd
python "<skill-dir>\build_imageset.py" [<mod-root>] [--mod-name <name>]
```

| Argument | Required? | Notes |
|---|---|---|
| `<mod-root>` | no | Folder containing `.gui-sources/`. Defaults to current directory. |
| `--mod-name <name>` | no | Name used in the `path` field of the `.imageset` (`<name>\gui\imagesets\<setname>.paa`). Defaults to the basename of `<mod-root>`. |

## What it does

1. Preflight gate (DayZ Tools needed for `ImageToPAA.exe`), before any other check.
2. Check that Pillow is installed and that `<mod-root>/.gui-sources/` exists with at least one subfolder.
3. Resolve `ImageToPAA.exe` from DayZ Tools.
4. For each subfolder of `<mod-root>/.gui-sources/`:
   - Collect all `.png` files in that subfolder. Each file becomes one named sprite (the file's stem becomes the `ImageSetDefClass` name). A stem that is not an identifier (letters, digits and underscores, not starting with a digit; so no spaces or hyphens) fails that set with a `[FAIL]` naming the files to rename. A subfolder with no `.png` files is skipped with a `[WARN]`, and its outputs from an earlier run are deleted.
   - Sort sprites by height descending and shelf-pack into the smallest power-of-two atlas that fits (each dimension picked from 256 / 512 / 1024 / 2048 / 4096; rectangular atlases allowed; ordered by area, square preferred at equal area), with a 10px gutter on all sides of every sprite.
   - If everything fits in one atlas: emit `<setname>.{paa,imageset}`.
   - If sprites won't fit in a single 4096x4096 atlas: split, next-fit in height order (a new atlas starts when the current one overflows), into multiple atlases and emit `<setname>_1.{paa,imageset}`, `<setname>_2.{paa,imageset}`, etc. Each part is its own self-contained imageset.
   - Delete this set's outputs from an earlier run that this run won't rewrite (`<setname>.*` after a split, extra `<setname>_N.*` when the part count drops), so no orphan atlas is left behind. Stems matching another source set's name are left alone.
   - Compose each atlas as PNG via Pillow, convert to `.paa` via `ImageToPAA.exe`. The atlas fails if ImageToPAA exits non-zero or leaves no `.paa`, or if a `.paa` from an earlier run is still there unchanged (it did not rewrite the file).
   - Each `.imageset`'s `path` references its own `.paa` via `<mod-name>\gui\imagesets\<stem>.paa`.
5. Report a summary; exit non-zero if any imageset failed.

## Generated `.imageset` format

```
ImageSetClass {
 Name "my_icons"
 RefSize 512 512
 Textures {
  ImageSetTextureClass {
   mpix 0
   path "MyMod\gui\imagesets\my_icons.paa"
  }
 }
 Images {
  ImageSetDefClass hud_health {
   Name "hud_health"
   Pos 10 10
   Size 64 64
   Flags 0
  }
  ...
 }
 Groups {
 }
}
```

`Pos` is the sprite's top-left in atlas pixels (after gutter); `Size` is the sprite's own dimensions (gutter is NOT included in `Size`).

## Refuses to run if

- `/dayz-preflight` returns non-zero.
- Pillow is not installed.
- `<mod-root>` isn't a directory.
- `<mod-root>/.gui-sources/` doesn't exist or has no subfolders.
- A sprite file name is not an identifier (for example `hud health.png` or `hud-health.png`); that set fails and the others still build.
- A single sprite is larger than 4096x4096 minus gutter (won't fit in any allowed atlas size). Shrink it or deliver it outside an imageset.
- `ImageToPAA.exe` is missing from DayZ Tools.

## Do not

- Don't move source PNGs out of `.gui-sources/` into the mod tree; `/dayz-build-pbo` excludes only `.gui-sources\`, so PNGs anywhere else are packed into the PBO.
- Don't add gutter pixels to the per-sprite `Size` values; the engine reads `Size` as the sprite's own dimensions.
- Don't drop the 10px gutter; it prevents bleed between adjacent sprites at non-1:1 scaling.
- Don't change atlas to non-power-of-two; both width and height are POT independently (rectangular allowed). DayZ's GUI subsystem and `.paa` toolchain expect POT dimensions.
