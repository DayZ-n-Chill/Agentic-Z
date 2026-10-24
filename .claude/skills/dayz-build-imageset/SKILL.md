---
name: dayz-build-imageset
description: "Packs PNG sprites from a mod's .gui-sources/<setname>/ folders into a DayZ .imageset definition and .paa atlas under gui/imagesets/. Use when a mod's HUD or menu icons need to become an imageset that .layout files can reference."
argument-hint: "<ModName> | <mod-root> [--mod-name <name>]"
---

<!-- skill-dir-note -->
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
py -m pip install -r "<skill-dir>\requirements.txt"
```

## How to run

```cmd
python "<skill-dir>\build_imageset.py" <ModName> [--mod-name <name>]
python "<skill-dir>\build_imageset.py" <mod-root> [--mod-name <name>]
```

| Argument | Required? | Notes |
|---|---|---|
| `<ModName>` | one of the two | Resolves to `workspace/<ModName>/` in the project cached by `/dayz-init`, like the other `/dayz-*` skills, so it works from the repo root. |
| `<mod-root>` | one of the two | A path to a folder containing `.gui-sources/`. Any argument with a slash, backslash or drive letter, or `.` / `..`, is read as a path (use `.\MyMod` for a folder in the current directory). |
| `--mod-name <name>` | no | Root used in the `path` field of the `.imageset` (`<name>\gui\imagesets\<setname>.paa`). Defaults to the mod's `$PBOPREFIX$`, because in-PBO paths are rooted at the PBO prefix (vanilla `P:\DZ\gui.txt:1` has `prefix=gui\`, and `P:\gui\imagesets\playstation_buttons2.imageset:7` references `Gui/imagesets/...`). With no `$PBOPREFIX$` it falls back to the folder name with a `[WARN]`. |

## What it does

1. Preflight gate (DayZ Tools needed for `ImageToPAA.exe`), before any other check.
2. Check that Pillow is installed and that `<mod-root>/.gui-sources/` exists with at least one subfolder.
3. Resolve `ImageToPAA.exe` from DayZ Tools.
4. For each subfolder of `<mod-root>/.gui-sources/`:
   - Collect all `.png` files in that subfolder. Each file becomes one named sprite (the file's stem becomes the `ImageSetDefClass` name). A stem that is not an identifier (letters, digits and underscores, not starting with a digit; so no spaces or hyphens) fails that set with a `[FAIL]` naming the files to rename. A `.png` that Pillow cannot read (corrupt, truncated or 0 bytes) fails that set with a `[FAIL]` naming the file; the other sets still build. A subfolder with no `.png` files is skipped with a `[WARN]`, and its outputs from an earlier run are deleted.
   - Sort sprites by height descending and shelf-pack into the smallest power-of-two atlas that fits (each dimension picked from 256 / 512 / 1024 / 2048 / 4096; rectangular atlases allowed; ordered by area, square preferred at equal area), with a 10px gutter on all sides of every sprite.
   - If everything fits in one atlas: emit `<setname>.{paa,imageset}`.
   - If sprites won't fit in a single 4096x4096 atlas: split, next-fit in height order (a new atlas starts when the current one overflows), into multiple atlases and emit `<setname>_1.{paa,imageset}`, `<setname>_2.{paa,imageset}`, etc. Each part is its own self-contained imageset.
   - Compose each atlas as PNG via Pillow, convert to `.paa` via `ImageToPAA.exe`. The atlas fails if ImageToPAA exits non-zero or leaves no `.paa`, or if a `.paa` from an earlier run is still there unchanged (it did not rewrite the file).
   - Once every atlas of the set converted, delete this set's outputs from an earlier run that this run did not rewrite (`<setname>.*` after a split, extra `<setname>_N.*` when the part count drops), so no orphan atlas is left behind. If any atlas failed, nothing is deleted, so the earlier good atlas stays. Stems matching another source set's name are left alone.
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
- `<ModName>` is given but no project is cached by `/dayz-init`, or `workspace/<ModName>/` doesn't exist.
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
