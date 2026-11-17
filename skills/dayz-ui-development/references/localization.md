# Localization: stringtable.xml, stringtable.csv and the panel generator

How UI text is translated: the two stringtable formats, how layouts and script refer to a key, a naming convention, the measured rule that decides whether a `stringtable.csv` is registered at all, and the generator for preview panels that need no stringtable.

**How facts are marked here.** A `P:\` path with a line was checked on `P:\` (DayZ 1.30). The CSV results were measured in game by the source author on 2026-08-21 (DayZ 1.29) and are not yet checked here.

---

## File format (stringtable.xml)

Put `stringtable.xml` at the addon root, beside `config.cpp`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<Project name="MyMod">
    <Package name="MyAddon">
        <Key Id="STR_MYMOD_DEVICE_NAME">
            <Original>Device Name</Original>
            <English>Device Name</English>
            <Spanish>Nombre del Dispositivo</Spanish>
            <French>Nom de l'Appareil</French>
            <German>Gerätename</German>
        </Key>
    </Package>
</Project>
```

## Usage rules

- **In a `.layout`:** `text "#STR_MYMOD_DEVICE_NAME"`, with the `#` prefix and the quotes.
- **In script:** `Widget.TranslateString("#STR_MYMOD_DEVICE_NAME")` (`TranslateString` is `proto static` at `P:\scripts\1_core\proto\enwidgets.c:112`), or pass the key straight to `SetText("#STR_MYMOD_...")`.
- **The `Key Id` never includes `#`.** Only references to the key do.
- `<Original>` is the fallback when the player's language has no entry.
- Leave out languages you do not support. English plus one or two others is enough for a mod.

## Naming convention (the LFPG example)

```
STR_LFPG_[DEVICE]_[ELEMENT]
STR_LFPG_BTC_BTN_BUY_BTC     (the Buy Bitcoin button on the Bitcoin device)
STR_LFPG_PHONE_TITLE_MAIN    (the main title on the phone)
```

Keep one prefix for the whole mod. It makes keys easy to search for and keeps them apart from other mods' keys.

## Common mistake

Raw text in a `.layout` shows up fine, but it cannot be translated and it breaks translation mods. Put every UI string in the stringtable.

## stringtable.csv: the column header decides whether the engine registers it

DayZ also accepts a `stringtable.csv` at the addon root. Vanilla's own file starts with fifteen columns: `"Language","original","english","czech","german","russian","polish","hungarian","italian","spanish","french","chinese","japanese","portuguese","chinesesimp"` (`P:\languagecore\stringtable.csv:1`).

Measured in game on 2026-08-21, in two test series flown the same day (eight structural variants of the addon, then nine variants of the CSV itself):

- Key resolution survives removing every structural element of the addon: scripts and class definitions, `data\`, `gui\`, `model.cfg`, `include.lst`, the config body, a rich `CfgPatches` or `CfgMods`. An addon of **three files** (`$PBOPREFIX$`, a minimal config and the csv) resolves its keys.
- **The switch is the column header.** With these seven columns, `"Language","original","english","spanish","german","russian","chinesesimp"`, keys resolve even with only two data rows. With four columns (no `german`, `russian` or `chinesesimp`) the key is printed raw at any size (263 rows or 8), even though the PBO loads (confirmed from the addon list in a crash report) and even though the client's language column is there with text in it.
- Row count, total size and blank lines make no difference.
- The packer makes no difference (FileBank and MakePbo behave the same), and neither does the `$PBOPREFIX$` dialect (`prefix=...;product=...;` or a bare name), including under MakePbo, which does read the file.
- Which of the three removed columns is the one that matters was not isolated. The safe rule is the full seven column header.

**Practical rule.** Every `stringtable.csv` you pack carries the seven column header; columns you have not translated copy the English text. Use as many rows as you need; two are enough.

Two more consequences:

- A key that was not registered is printed raw **without** the `#`. The engine recognised it as a key and did not find it, which looks exactly like a key that does not exist.
- A `.layout` loaded from `$profile:` brings no stringtable with it. Stringtables enter only through an addon PBO at boot. For text you change while iterating, write literals or set the text from the test harness, not keys.

The `stringtable.csv` in this skill's `templates\` folder carries the seven column header for this reason.

## Preview panels on demand (generator included)

`<skill-dir>\scripts\gen_panel_layout.py` writes layouts made for the hot iteration loop (load from `$profile:`, reload, set text from the harness; see `hot-iteration.md`): a chat or log feed, a label and value panel, and a minimal HUD. The widget names are a contract (`TitleText`, `FeedLine0` to `FeedLineN-1`, `LabelK` and `ValueK`), documented in `<skill-dir>\scripts\CONTRACT.md`.

- Flown in game on 2026-08-21: a ten line feed was filled at runtime with no stringtable.
- `--self-test` checks that braces balance and that widget names are unique, without starting the game.
