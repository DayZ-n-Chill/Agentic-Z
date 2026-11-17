# Layout variants on DayZ 1.30: change a vanilla `.layout` without replacing it

How a 1.30 mod hides, changes or adds widgets in a vanilla layout through a layout variant, how to pack one, how to scope it to one screen by inheritance, and what happens when a mod shadows an imageset or the styles file.

Measured by the source author on DayZ 1.30.164200 (stable, DayZDiag), 2026-10-27 and 2026-11-05, and on 1.30.164289 with variants
written by hand, 2026-11-10 and 2026-11-12. Each `CLAIM-...` tag below is the id of a claim in the knowledge pack's
`sources/claims.json`, which holds its evidence; the review notes and probe plans behind them are not in this repo. The runs
are not repeated here. Target:
`P:\gui\layouts\day_z_ingamemenu.layout`, the Esc menu, created by
`P:\scripts\5_mission\gui\ingamemenu.c:38`.

The vanilla `path:line` citations were re-read on a `P:\` holding 1.30.164014. That build's `day_z_ingamemenu.layout`
has the same lines; its `day_z_hud.layout` is the older form with no stored widget IDs (`layout-format.md`, "Widget names").

Not to be confused with the test or debug *copy* of your own layout (`verification-and-automation.md`: two layouts
with the same widget names make one of them unreachable): that is a second file under your own path. A 1.30 layout variant is a
file at the **vanilla** path, in a PBO that shadows the vanilla prefix, which the engine applies on top of
the vanilla layout.

## 1. Generate it in Workbench

[EXACT][CLAIM-UI-VARIANT-WORKBENCH-FORMAT-130] Recipe that produced a working variant:

1. Make an authoring root folder holding a `mod.cpp`. Start Workbench **from its own folder** (so it finds
   `dayz.gproj`) with `-filePatching` and `-mod=<authoring root>`; the resource browser then lists the
   addon beside `DZ`.
2. In the resource browser, right-click the vanilla layout (`DZ/gui/layouts/<name>.layout`) and create a
   resource variant for the selected addon. The log reads `Creating new resource variant for selected addon`.
3. Pick the variant in the editor's "Resource Variants" picker, make the edits, save.

Workbench writes `gui/layouts/<name>.layout` **plus a `<name>.layout.meta`** into the addon (vanilla
layouts have no `.meta`). The file mirrors the whole vanilla tree in vanilla order: the root has no ID, and
every other widget is `Class "{id}" { Prefab "{id}" }`. Only edited widgets carry properties. A widget you
add gets its own 64-bit ID, a `Name` and **no** `Prefab`. Excerpt of the generated file (Licensing
container: `version` recoloured, `copyright` hidden, one widget added):

```
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
     Name "eoc_probe4_added"
     color 1 0 0 1
     text "TEST"
     "text color" 0.629 0 0 1
    }
   }
  }
```

The vanilla widgets behind those IDs are `Licensing`, `version` and `copyright`
(`P:\gui\layouts\day_z_ingamemenu.layout:8`, `:25`, `:42`).

[EXACT][CLAIM-UI-VARIANT-IDS-NAME-HASH-CHECK] **How the IDs are derived.** Computed offline on 2026-11-09
over the vanilla layouts of 1.29, 1.30.164014, 1.30.164200 and 1.30.164289. An ID is `00000000` followed by a
CRC-32 of the widget's `Name` and then each ancestor's `Name`, up to but not including the layout root, with
no separators: `version` inside `Licensing` hashes `versionLicensing` to `308B9F61`, and the root-level
`dayz_logo` (`:540`) hashes to `9FF48118`. A named root hashes its own name. The CRC is polynomial
`0x04C11DB7`, MSB first, in a shift register that is not augmented (the message bits enter at the low end and
no 32 zero bits follow), with init and final XOR `0xFFFFFFFF`; `zlib.crc32` and CRC-32/BZIP2 give other
values. The earlier check hashed the bare name, which is why CRC32, FNV-1, FNV-1a and Adler-32 all failed.

`day_z_ingamemenu.layout` stores no widget IDs (its `{16-hex}` prefixes are texture references,
`imageTexture "{GUID}Gui/textures/..."`), but 10 of the 227 vanilla layouts store one per widget, 1,438 in all
(for example `P:\gui\layouts\xbox\day_z_ingamemenu_xbox.layout:232`; on 1.30.164200 also `day_z_hud.layout`,
line 295 of that build), and 1,395 of them equal the derived ID. The other 43 are nine
64-bit IDs of widgets added after 1.29 (`debug/day_z_debug_monitor.layout`,
`script_console/script_console.layout`) and 34 in
`underground_trigger_editor/day_z_underground_trigger_editor.layout` from `:71`: nine match the chain without
`triggers_section`, and 25 lie between `CC000001` and `CC000020`. Two siblings with one name share an ID
(`P:\gui\layouts\xbox\day_z_ingamemenu_xbox.layout:232` and `:667`, both `CDEFDF47`).

Outside `script_console.layout` and the `debug/` layouts, no widget changed its ID from 1.29 to 1.30.164289;
six were added in `new_ui/options/msstore/game_tab.layout`. The 878 IDs that seven layouts gained in
1.30.164014, and `day_z_hud.layout` in 1.30.164200, are the ones derived from the previous build's names. A
derived ID changes with the name of the widget or of any ancestor below the root, as it did for nine widgets
of `debug/day_z_hud_debug.layout` that moved between 1.29 and 1.30.164014.

[INFERRED] Where the vanilla widget stores an ID, a variant needs that ID rather than the derived one, and
one variant entry cannot tell two same-named siblings apart.

[EXACT][CLAIM-UI-VARIANT-HAND-WRITTEN-130] **A variant written by hand with the derived IDs applies.** On
DayZDiag 1.30.164289 (2026-11-10), a hand-written `day_z_ingamemenu.layout` in the format above, the whole
vanilla tree mirrored with derived IDs, packed with MakePbo (section 3) and **without a `.meta`**, recoloured
`version`, hid `copyright`, `dayz_logo` and `vignette`, and added a widget inside `Licensing`:
`copyright_vis=0 version_color=-65536 licensing_children=3 logo_vis=0 vignette_vis=0 added_probe4=1@Licensing`.
The client log, in the lines of the warning of section 2, names the layout
`{8648FA7C9D16ED7D}gui/layouts/day_z_ingamemenu.layout`, the GUID that Workbench writes into the `.meta`,
although the PBO had none. The IDs of any layout:
`scripts/tools/dayz-ui-lab/dayz_ui_lab/widget_ids.py`.

## 2. What a variant does in game

[EXACT][CLAIM-UI-VARIANT-PREFAB-MERGE-130] A variant generated as above **hides** (`visible 0`),
**modifies** (colour) and **adds** widgets of the vanilla layout **in place**, at the root and inside nested
containers, with no duplicates. Matching is by the `Prefab` ID, not by name. Vanilla script finds an added
widget with `FindAnyWidget`. Probe readout, from a `modded class InGameMenu` after vanilla `Init`:
`copyright_count=1 copyright_vis=0 licensing_count=1 logo_count=1 logo_vis=0 version_color=-65536 added_parent=Licensing`
(`dayz_logo`, `P:\gui\layouts\day_z_ingamemenu.layout:540`, is the root-level hide).

[EXACT][CLAIM-UI-VARIANT-NAME-KEYED-ADD-ONLY-130] **Hand-written, name-keyed files only add.** A full copy
of the vanilla layout with one changed text drew every widget twice; a delta file holding the root,
`Licensing` and a re-texted `copyright` left vanilla's `copyright` untouched and added a second one; a nested
container keyed by name (`Licensing`) became a second container, not a merge. Top-level widgets of such a
file do become children of the vanilla root and are reachable by the menu's own `FindAnyWidget`. The older
conclusion "variants can only add widgets" holds **only** for these files; for Workbench-generated files it is
superseded by the claim above.

[EXACT][CLAIM-UI-VARIANT-STALE-PREFAB-130] **An entry whose ID no widget has is dropped, with a warning.** On
1.30.164289 the entry `TextWidgetClass "{00000000DEADBEEF}" { Prefab "{00000000DEADBEEF}" Name "eoc_l5_stale" }`
inside `Licensing` added nothing (`licensing_children=3`, no `eoc_l5_stale`) and the rest of the variant
applied. The client log has `GUI (W): Overridden prefab member 'eoc_l5_stale' (GUID: '{DEADBEEF}' type:
TextWidgetClass) no longer exists in prefab`. After a DayZ update that renames or moves a widget, edits to it
stop applying with only that warning: recompute the IDs and diff.

[EXACT][CLAIM-UI-VARIANT-TWO-MODS-130] **Two mods varying one layout both apply.** On 1.30.164289, mod A
(`version` red, `copyright` hidden, one widget added) and mod B (`version` green, another widget added), each
with its own variant of `day_z_ingamemenu.layout`, loaded together in both orders: both added widgets sat in
`Licensing` (`licensing_children=4`) and `copyright` stayed hidden, while `version` took the colour of the mod
later in `-mod=` (A then B: `-16711936`, green; B then A: `-65536`, red). B's PBO also held a name-keyed
`day_z_hud.layout`, whose widget joined the HUD root in both orders: two `gui`-prefix shadow PBOs with
different files load together, and the vanilla `gui` files that neither PBO holds still load.

## 3. Packing

[EXACT][CLAIM-UI-VARIANT-GUI-PREFIX-PACKING-130] What worked: the variant's `gui/` folder packed as its own
PBO with prefix `gui` and the 1.30 header property `fsShadowing=1` (RaG PBO Builder `--fs-shadowing`; header
read back from the packed bytes), the `.meta` packed alongside the `.layout`, a `config.cpp` present, the
PBO unsigned, loaded on DayZDiag from a mod folder holding only the probe. Header and builder flags:
`skills/dayz-build-pbo/references/dayz-1-30-pbo-build.md`, section "`fsShadowing`".

[EXACT][CLAIM-UI-VARIANT-MAKEPBO-PACKING-130] MakePbo works too (1.30.164289, 2026-11-10): the same `gui/`
folder, with `prefix=gui` and `fsShadowing=1` as two lines of `$PBOPREFIX$.txt`, packed by MakePbo 2.16
with `config.cpp` compiled to `config.bin`, **no `.meta`**, unsigned; the variants of section 1 and section 2 applied. The
variant's own `CfgPatches` class was not in the game config: `ConfigIsExisting` returned 0 for it, and 1 for
the probe mod's.

[EXACT][CLAIM-UI-VARIANT-NO-CONFIG-130] **`config.cpp` is not needed.** On 1.30.164289 (2026-11-10), a PBO
holding only `layouts/day_z_ingamemenu.layout`, a variant that hides `dayz_logo` and adds a widget inside
`Licensing`, with no `config.cpp`, no `.meta` and no signature, packed by FileBank with the header
`prefix=gui`, `fsShadowing=1`, loaded from its own mod folder and its variant applied:
`logo_vis=0 added_noconfig=1@Licensing licensing_children=3`. How to pack it:
`skills/dayz-build-pbo/references/dayz-1-30-pbo-build.md`, section "`fsShadowing`".

[REPORTED][CLAIM-UI-VARIANT-NO-CONFIG-REPORT] A community author reports packing each variant folder without
`config.cpp`, through an `OVERRIDE` marker file in their own tool, and says pboProject refuses such folders.
The measurement above agrees with the first part; the pboProject refusal is not verified here.

## 4. One screen only: inherit the vanilla layout in a layout of your own

[EXACT][CLAIM-UI-VARIANT-INHERIT-GUID-130] **A layout at your own path that inherits the vanilla layout by
its GUID gives the vanilla tree with your edits, and the vanilla layout stays as it was.** On DayZDiag
1.30.164289 (2026-11-10), a file in the mod's own folder whose root line is
`FrameWidgetClass : "{8648FA7C9D16ED7D}gui/layouts/day_z_ingamemenu.layout" {` and whose body is a variant in
the format of section 1 (`dayz_logo` hidden, a widget `l5p3_added` added inside `Licensing`), created by script with
`CreateWidgets` on its own path, gave the whole vanilla tree with both edits:
`children=8 licensing_children=3 logo_vis=0 added_p3=1@Licensing`, where the vanilla path gives
`children=8 licensing_children=2 logo_vis=1`. The Esc menu, which creates the vanilla path, did not get those
edits: `logo_vis=1 added_p3=0` in the same runs, and `added_p3=0` in a run where it opened after that layout
had been created.

What did not work, in the same runs:

- The same root with the path and no GUID, `FrameWidgetClass : "gui/layouts/day_z_ingamemenu.layout" {`,
  gave what the body gives with no base: a root with no name and no children (`children=0`), and one
  `GUI (W): Overridden prefab member (GUID: '{…}' type: …) no longer exists in prefab` per entry of the body.
- `CreateWidgets("{8648FA7C9D16ED7D}gui/layouts/day_z_ingamemenu.layout")` returned null, with
  `SCRIPT (E): Cannot open layout '{8648FA7C9D16ED7D}gui/layouts/day_z_ingamemenu.layout'` and
  `Cannot load layout` for the same name. The GUID form names a base inside a layout; script does not open it.

[EXACT][CLAIM-UI-LAYOUT-GUID-CRC64-130] **A layout's GUID is a CRC-64 of its path, checked on seven
layouts, with or without a `.meta`.** The client log of 1.30.164289 names layouts with their GUID in
`GUI : Layout load @"{GUID}path"` lines, also layouts packed without a `.meta`:
`{D28473AC9D1FDDED}L5Probe3/gui/l5p3_noinherit.layout`,
`{BF87DB555BA864F7}L5Probe3/gui/l5p3_inherit_path.layout`,
`{D87638C86BF5A92A}DayZ_MCP/gui/layouts/mcp_dialog.layout`, and the Esc menu's
`{8648FA7C9D16ED7D}gui/layouts/day_z_ingamemenu.layout` (section 1). Computed offline on 2026-11-10, each of the four
is the CRC-64/WE of the path in upper case with forward slashes (`GUI/LAYOUTS/DAY_Z_INGAMEMENU.LAYOUT` gives
`8648FA7C9D16ED7D`): polynomial `0x42F0E1EBA9EA3693`, MSB first, no reflection, init and final XOR
`0xFFFFFFFFFFFFFFFF` (check value of `123456789`: `62EC59E3F1A4F00A`), written as 16 upper-case hex digits.
The client log of 2026-11-12 adds `GUI : Layout load @"{F374C13E7501FC6E}GP7Probe/gui/gp7_chat_nobase.layout"`,
`GUI : Layout load @"{0DFA45C5E9E90A3A}GP7Probe/gui/gp7_notice_nobase.layout"` and
`GUI : Layout load @"{BCEF4C226FD9C108}GP7Probe/gui/gp7_child_nobase.layout"`, and computed offline on
2026-11-12 each of the three is the CRC-64/WE of its path in upper case. The GUIDs of the two bases of
`CLAIM-UI-VARIANT-INHERIT-OTHER-LAYOUTS-130` were computed the same way and used as a base, but no log line
names them, so they do not count among the seven checked here.

[EXACT][CLAIM-UI-VARIANT-INHERIT-STACKS-130] **With a variant of the same layout loaded, the inherited base is
the varied layout.** With the PBO of `CLAIM-UI-VARIANT-NO-CONFIG-130` loaded, the layout above gave both its
own edits and the variant's: `licensing_children=4 logo_vis=0 added_variant=1@Licensing added_p3=1@Licensing`.
A variant at the vanilla path applies to every creation of that path, script included:
`CreateWidgets("gui/layouts/day_z_ingamemenu.layout")` gave `logo_vis=0 added_variant=1@Licensing`.

[EXACT][CLAIM-UI-VARIANT-INHERIT-OTHER-LAYOUTS-130] **Two more vanilla layouts work as a base the same
way.** On DayZDiag 1.30.164289 (2026-11-12), a layout at the mod's own path whose root has the class of the
vanilla root and inherits `"{GUID}gui/layouts/<name>.layout"`, with the GUID computed as in
`CLAIM-UI-LAYOUT-GUID-CRC64-130`, gave the vanilla tree with its edits for `gui/layouts/day_z_chat_item.layout`
(`WrapSpacerWidgetClass`, GUID `80E5A5B93003BC87`) and `gui/layouts/notification_info.layout`
(`WindowWidgetClass`, GUID `3D8F7B52AA108BD5`). The body, in the format of section 1, hides one vanilla widget
(`ChatItemSenderWidget`; `BackgroundWidget`) and adds `gp7_added` at the root. In each of the three runs the
root kept its vanilla name (`ChatItemWidget`; `connectionWarningWindowWidget`), held one child more than the
vanilla path gave (3 against 2; 4 against 3), held the hidden widget with visibility 0, kept the other vanilla
widget (`ChatItemTextWidget`; `NotificationMultilineTextWidget`) and held `gp7_added` under the root, and the
vanilla path, created before and after, gave its own tree with no edit. The same root with the last bit of the
GUID changed (`80E5A5B93003BC86`; `3D8F7B52AA108BD4`) and the same path gave the same trees, with no warning
and no log line naming those GUIDs, so these runs do not show that the GUID's value is what finds the base.
The same body with no base gave a root with no name holding only `gp7_added`, and one
`Overridden prefab member (GUID: '{…}' type: …) no longer exists in prefab` warning per `Prefab` entry.

[EXACT][CLAIM-UI-VARIANT-INHERIT-CHILD-130] **A child widget can inherit a vanilla layout the same way.**
On DayZDiag 1.30.164289 (2026-11-12), in a layout of your own whose root `gp7_host_root` holds one child,
`FrameWidgetClass "{7A07000000000004}" : "{8648FA7C9D16ED7D}gui/layouts/day_z_ingamemenu.layout" {` with
`Name "gp7_slot"`, the child held the Esc menu's tree: with no edit inside, 8 children, `Licensing` with 2
and `dayz_logo` visible; with the body of the root-level variant of this section inside (`dayz_logo` hidden,
`gp7_added` added inside `Licensing`), the tree with both edits, as the root-level inheritance gave in the
same runs (8 children, `Licensing` with 3, `dayz_logo` hidden, `gp7_added` inside `Licensing`). The host root
kept one child, the slot, in both cases; the same child with that body and no base held no children, and the
Esc menu the game created in the same runs had neither edit (`Licensing` with 2, `dayz_logo` visible).

[INFERRED] To change one screen only, have that screen's script create a layout of your own that inherits
the vanilla one, at its root or in a child widget, and ship no variant at the vanilla path, because a variant
there reaches every screen that uses the layout; three vanilla layouts have been used as a base in game, and
another vanilla layout's GUID is the same CRC of its path; write the computed GUID, because a wrong one
giving the same base is what these runs measured, not a rule.

## 5. Shadows of an imageset or of the styles replace the whole file

[EXACT][CLAIM-UI-SHADOW-IMAGESET-REPLACES-130] **An imageset in a `gui` shadow PBO replaces the vanilla
imageset; it does not merge with it.** On DayZDiag 1.30.164289 (2026-11-10), a PBO with `prefix=gui` and
`fsShadowing=1`, packed like the one of `CLAIM-UI-VARIANT-NO-CONFIG-130`, held only
`imagesets/BleedingDrops.imageset`: the vanilla file cut to two images, `Bleeding2` resized from 128 x 128 to
100 x 100 and a new `l5p3_added` of 64 x 64. `ImageWidget.LoadImageFile(i, "set:BleedingDrops image:<name>")`
and `GetImageSize` gave `Bleeding2` 100 x 100 and `l5p3_added` 64 x 64, and `Bleeding1` failed. Without the PBO,
`Bleeding1` and `Bleeding2` gave 128 x 128 and `l5p3_added` failed. The images the file did not repeat were
gone for the game too: the log has
`GUI (E): ImageWidget::LoadImageFile can't set image 'set:BleedingDrops image:Bleeding3'` and the same line
for `Bleeding4` to `Bleeding16`, images the probe never loaded.

[EXACT][CLAIM-UI-SHADOW-STYLES-REPLACES-130] **The widget styles behave the same.** A PBO of the same kind
held only `looknfeel/dayzwidgets.styles`, with one `<Widget Name="TextWidget">` section of two styles:
`Normal` moved from `gui/fonts/MetronBook` to `gui/fonts/MetronLight`, and a new `L5Style` on
`gui/fonts/MetronLight`. `TextWidget.GetTextSize` gave the width of one 40-character text under four `style`
values. Without the PBO the widths were `Normal 680`, `Bold 690`, `Light 670` and `L5Style 680`; with it, all
four were `670`. So the file is read (`L5Style` draws like vanilla `Light`, which is on `MetronLight`),
`Normal` is replaced by name, and `Bold`, which the file does not repeat, draws like the new `Normal`. A style
name that does not exist draws like `Normal` too (`L5Style` without the PBO). No error line of that run names
`dayzwidgets`. The whole file is replaced, not only the section the delta holds: on 2026-11-12 the same PBO,
loaded alone again, gave 670 for the four `TextWidget` styles, and three `MultilineTextWidget`s with
`DayZNormal`, `DayZBold` (two styles of the vanilla `MultilineTextWidget` section,
`P:\gui\looknfeel\dayzwidgets.styles:10`, which the delta does not hold) and a style name that does not
exist gave `GetTextSize` 0 x 0, where without the PBO they gave 540, 550
and 540, height 22. Without the PBO, a style name that does not exist measured like `DayZNormal` in that class.

[EXACT][CLAIM-UI-SHADOW-IMAGESET-FULL-130] **A full copy of an imageset shadow works.** On DayZDiag
1.30.164289 (2026-11-12), `@L5ShadowImgFull`, packed by FileBank with header `prefix=gui` and `fsShadowing=1`
and one file, `imagesets/BleedingDrops.imageset` (1955 bytes; PBO 2097 bytes, sha256
`a2a1af2b87c2b0c1ff3c2c6b0d18dc49299b7e3429a13c8dbbb3e13ef2d7aee5`), held the vanilla `BleedingDrops.imageset`
with `Bleeding2` resized to 100 x 100 and a new `l5p3_added` of 64 x 64. Loaded together with the full styles
copy of `CLAIM-UI-SHADOW-STYLES-FULL-130` in one run, it gave `Bleeding1` 128 x 128, `Bleeding2` 100 x 100 and
`l5p3_added` 64 x 64, where without it `Bleeding1` and `Bleeding2` gave 128 x 128 and `l5p3_added` failed. That
run's log has no `LoadImageFile` error, where the delta of `CLAIM-UI-SHADOW-IMAGESET-REPLACES-130` logged one
per image it did not repeat.

[EXACT][CLAIM-UI-SHADOW-STYLES-FULL-130] **A full copy of the styles shadow works.** On DayZDiag 1.30.164289
(2026-11-12), `@L5ShadowStyFull`, packed by FileBank with header `prefix=gui` and `fsShadowing=1` and one file,
`looknfeel/dayzwidgets.styles` (242674 bytes; PBO 242812 bytes, sha256
`b702f3ddbad8b58e88753abe32ab658ec500b702effc55c7f494900ac5b94f4e`), held the vanilla `dayzwidgets.styles`
with the `TextWidget` `Normal` on `gui/fonts/MetronLight` and a new `L5Style` on `gui/fonts/MetronLight`. It
gave `Normal` 670, `Bold` 690, `Light` 670 and `L5Style` 670, where without it they were 680, 690, 670 and
680, and the `MultilineTextWidget` styles kept their widths (540, 550 and 540, as without it). So the changed
and the new style apply, and the styles the copy repeats keep drawing as before.

[INFERRED] A shadow of an imageset or of `dayzwidgets.styles` has to hold the whole vanilla file with your
changes (both full copies worked, both deltas lost what they did not repeat), and it changes those images or
styles on every screen; only `BleedingDrops.imageset` and `dayzwidgets.styles` were measured.

## 6. Unknowns — do not promise these

- **Resource variants made in Workbench for other types.** The shadows of section 5 were plain files. Whether a
  Workbench resource variant of an `.imageset` or of the styles merges like a layout variant is not measured.
