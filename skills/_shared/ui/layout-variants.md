# Layout variants on 1.30

How a 1.30 mod hides, recolors or adds widgets in a vanilla `.layout` without replacing the file: a layout variant at the vanilla path, how its widget IDs are derived, how to pack it, how to limit the change to one screen by inheriting the vanilla layout, and what happens when a mod shadows an imageset or the styles file.

Everything here was measured in game on 1.30 diag builds against the Esc menu, `P:\gui\layouts\day_z_ingamemenu.layout`, which `P:\scripts\5_mission\gui\ingamemenu.c:38` creates. A conclusion drawn from those runs rather than seen in them is marked inferred. A layout variant is not the same as a test copy of your own layout under your own path (`widget-name-collisions.md`).

## What a variant file looks like

Workbench writes one for you:

1. Make an authoring folder holding a `mod.cpp`. Start Workbench from its own folder, so it finds `dayz.gproj`, with `-filePatching` and `-mod=<authoring folder>`. The resource browser then lists the addon beside `DZ`.
2. Right click the vanilla layout (`DZ/gui/layouts/<name>.layout`) and create a resource variant for the selected addon.
3. Pick the variant in the editor's "Resource Variants" list, edit, save.

Workbench writes `gui/layouts/<name>.layout` and a `<name>.layout.meta` into the addon. The file mirrors the whole vanilla tree in vanilla order: the root has no ID, every other widget is `Class "{id}" { Prefab "{id}" }`, and only edited widgets carry properties. A widget you add gets its own 64 bit ID, a `Name` and no `Prefab`. Here `version` is recolored, `copyright` hidden and one widget added inside `Licensing`:

```text
FrameWidgetClass {
 {
  WrapSpacerWidgetClass "{00000000564F35E9}" {
   Prefab "{00000000564F35E9}"
   {
    TextWidgetClass "{00000000308B9F61}" {
     Prefab "{00000000308B9F61}"
     color 1 0 0 1
     "text color" 0.629 0 0 1
    }
    TextWidgetClass "{00000000BB186E8D}" {
     Prefab "{00000000BB186E8D}"
     visible 0
    }
    TextWidgetClass "{6ACB5888C22B23AC}" {
     Name "MyMod_Added"
     color 1 0 0 1
     text "TEST"
    }
   }
  }
```

The vanilla widgets behind those IDs are `Licensing`, `version` and `copyright` (`P:\gui\layouts\day_z_ingamemenu.layout:8`, `:25` and `:42`).

A variant written by hand in this format, with the derived IDs and no `.meta`, applies the same way. `scripts/tools/dayz-ui-lab/dayz_ui_lab/widget_ids.py` prints the IDs of any layout.

## How widget IDs are derived

An ID is `00000000` followed by a CRC-32 of the widget's `Name` and then each ancestor's `Name`, up to but not including the layout root, with no separators. `version` inside `Licensing` hashes `versionLicensing` to `308B9F61`; the root level `dayz_logo` (`P:\gui\layouts\day_z_ingamemenu.layout:540`) hashes to `9FF48118`. A named root hashes its own name. The CRC uses polynomial `0x04C11DB7`, most significant bit first, a shift register that is not augmented, and `0xFFFFFFFF` as both start value and final XOR; `zlib.crc32` and CRC-32/BZIP2 give other values.

- Some vanilla layouts store their IDs in the file (`P:\gui\layouts\xbox\day_z_ingamemenu_xbox.layout:232`). Of 1,438 stored IDs, 1,395 equal the derived one; the rest are 64 bit IDs of widgets added later and a block of hand numbered IDs in the underground trigger editor layout. Where vanilla stores an ID, a variant needs that ID (inferred).
- Two siblings with the same name share an ID (`P:\gui\layouts\xbox\day_z_ingamemenu_xbox.layout:232` and `:667`, both `CDEFDF47`), so one variant entry cannot tell them apart (inferred).
- An ID changes when the widget or any ancestor below the root is renamed. Recompute and compare IDs after every DayZ update.

## What a variant does in game

- It hides (`visible 0`), changes and adds widgets in place, at the root and inside nested containers, with no duplicates. Matching is by `Prefab` ID, not by name, and vanilla script finds an added widget with `FindAnyWidget`.
- An entry whose ID no widget has is dropped with a warning, and the rest applies: `GUI (W): Overridden prefab member '<name>' (GUID: '{<id>}' type: TextWidgetClass) no longer exists in prefab`. After an update that renames or moves a widget, your edit to it stops applying with only that line in the log.
- A file keyed by names, not IDs, only adds. A full copy of the vanilla layout drew every widget twice; a partial file with a changed `copyright` added a second `copyright`; a container keyed by name became a second container. Its top level widgets do join the vanilla root.
- Two mods that vary one layout both apply. Both added widgets appear, a hide from either holds, and where both change the same property the mod later in `-mod=` wins. Two `gui` prefix PBOs holding different files load together, and the vanilla `gui` files neither holds still load.

## Packing

- Pack the variant's `gui/` folder as its own PBO with prefix `gui` and the 1.30 header property `fsShadowing=1` (`skills/dayz-build-pbo/references/dayz-1-30-pbo-build.md`, section "`fsShadowing`"). Packed with a `.meta` and a `config.cpp`, unsigned, it applied.
- MakePbo works too, with `prefix=gui` and `fsShadowing=1` as two lines of `$PBOPREFIX$.txt`, no `.meta` and `config.cpp` binarised. The variant's own `CfgPatches` class was not in the game config afterwards (`ConfigIsExisting` returned 0).
- `config.cpp` is not needed: a PBO holding only `layouts/day_z_ingamemenu.layout`, with no config, no `.meta` and no signature, packed by FileBank with that header, applied its variant.
- Not measured: whether pboProject accepts a variant folder with no `config.cpp`.

## Changing one screen only

A variant at the vanilla path reaches every screen that creates that layout, script included. To change one screen, have its script create a layout of your own that inherits the vanilla one:

```text
FrameWidgetClass : "{8648FA7C9D16ED7D}gui/layouts/day_z_ingamemenu.layout" {
 // body in the variant format: hide dayz_logo, add a widget inside Licensing
}
```

- Created with `CreateWidgets` on your own path, it gives the whole vanilla tree with your edits, and the Esc menu, which creates the vanilla path, stays unchanged.
- A child widget can inherit the same way: `FrameWidgetClass "{7A07000000000004}" : "{8648FA7C9D16ED7D}gui/layouts/day_z_ingamemenu.layout" {` with a `Name`, inside a root of your own, held the Esc menu tree with the edits.
- With a variant of the same layout loaded, the inherited base is the varied layout.
- The path with no GUID gives an empty root and one "no longer exists in prefab" warning per entry. `CreateWidgets("{8648FA7C9D16ED7D}gui/layouts/day_z_ingamemenu.layout")` returns null with `Cannot open layout`: the GUID form names a base inside a layout, not a file script can open.
- `gui/layouts/day_z_chat_item.layout` (a `WrapSpacerWidgetClass` root, GUID `80E5A5B93003BC87`) and `gui/layouts/notification_info.layout` (a `WindowWidgetClass` root, GUID `3D8F7B52AA108BD5`) work as a base the same way; the inheriting root uses the class of the vanilla root.

A layout's GUID is the CRC-64/WE of its path in upper case with forward slashes: `GUI/LAYOUTS/DAY_Z_INGAMEMENU.LAYOUT` gives `8648FA7C9D16ED7D`. Polynomial `0x42F0E1EBA9EA3693`, most significant bit first, no reflection, `0xFFFFFFFFFFFFFFFF` as start value and final XOR (the check value of `123456789` is `62EC59E3F1A4F00A`), written as 16 upper case hex digits. The client log names every layout it loads with that GUID, `GUI : Layout load @"{GUID}path"`, also for layouts packed with no `.meta`, and seven checked paths matched the formula. A GUID with its last bit changed still found the same base with no warning, so these runs do not show that the value is what finds the base; write the computed one (inferred).

## Shadowing an imageset or the styles file

A `gui` shadow PBO with `fsShadowing=1` that holds an imageset or `looknfeel/dayzwidgets.styles` replaces the whole vanilla file; it does not merge.

- An imageset cut down to two images made every other image of that set fail on every screen: `GUI (E): ImageWidget::LoadImageFile can't set image 'set:BleedingDrops image:Bleeding3'`, and so on for the images it left out. The changed and new images worked.
- A styles file holding one `TextWidget` section of two styles replaced the whole file: `Normal` took the new font, `Bold`, which the file left out, drew like the new `Normal`, and the `MultilineTextWidget` styles it left out (`P:\gui\looknfeel\dayzwidgets.styles:10`) measured 0 by 0. No error line names the file.
- A full copy of the vanilla imageset or styles file with your changes works: the changed and new entries apply, the rest draw as before, and the log stays clean.
- So a shadow holds the whole vanilla file with your changes, and it changes those images or styles on every screen (inferred; measured on `BleedingDrops.imageset` and `dayzwidgets.styles` only).
- A style name that does not exist draws like `Normal` in `TextWidget` and like `DayZNormal` in `MultilineTextWidget`.

Not measured: whether a Workbench resource variant of an imageset or of the styles merges like a layout variant.
