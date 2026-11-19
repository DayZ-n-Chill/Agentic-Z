# Localization

How UI text is translated: the one stringtable format DayZ reads (`stringtable.csv`), how layouts and script name a key, a naming scheme, the column header that decides whether the engine reads the file at all, and preview panels that need no stringtable.

## stringtable.csv

DayZ reads `stringtable.csv` only. The Arma 3 `stringtable.xml` (Project, Package and Key elements) is never read: vanilla ships `P:\languagecore\stringtable.csv` and no XML stringtable, and an XML file in a mod gives no error, its keys just print raw (`skills/dayz-build-pbo/references/stringtable-and-script-checks.md`).

Put `stringtable.csv` at the addon root, beside `config.cpp`. A header row, then one row per key:

```csv
"Language","original","english","spanish","german","russian","chinesesimp"
"STR_MYMOD_DEVICE_NAME","Device Name","Device Name","Nombre del Dispositivo","Gerätename","Device Name","Device Name"
```

- In a `.layout`, write `text "#STR_MYMOD_DEVICE_NAME"`, with the `#` and the quotes.
- In script, pass the key to `SetText("#STR_MYMOD_DEVICE_NAME")`, or translate it with `Widget.TranslateString("#STR_MYMOD_DEVICE_NAME")` (`proto static`, `P:\scripts\1_core\proto\enwidgets.c:112`).
- The key in the CSV's first column never has the `#`; only references to it do.
- The `original` column is the fallback when the player's language has no entry. Still fill every column of the header, copying the English text into columns you do not translate (see the header rules below).
- Raw text in a layout shows fine but cannot be translated and breaks translation mods. Put every UI string in the stringtable.

## Naming keys

```text
STR_MYMOD_<DEVICE>_<ELEMENT>
STR_MYMOD_PHONE_TITLE_MAIN
STR_MYMOD_ATM_BTN_WITHDRAW
```

One prefix for the whole mod keeps keys easy to search and apart from other mods' keys.

## The header

Vanilla's file starts with fifteen columns: `"Language","original","english","czech","german","russian","polish","hungarian","italian","spanish","french","chinese","japanese","portuguese","chinesesimp"` (`P:\languagecore\stringtable.csv:1`).

Measured in game on 1.29, over eight variants of the addon and nine of the CSV:

- Keys resolve with nearly everything else stripped from the addon. Scripts, `data\`, `gui\`, `model.cfg`, `include.lst` and a rich `CfgPatches` or `CfgMods` can all go: an addon of three files, `$PBOPREFIX$`, a minimal config and the CSV, resolves its keys.
- The header decides. With the seven columns `"Language","original","english","spanish","german","russian","chinesesimp"`, keys resolve even with two data rows. With four (no `german`, `russian` or `chinesesimp`) every key prints raw, whatever the row count, although the PBO loads and the client's language column is filled.
- Row count, file size, blank lines, the packer (FileBank or MakePbo) and the form of `$PBOPREFIX$` make no difference.
- Which of the three missing columns matters was not isolated. Always use the full seven column header, and copy the English text into columns you have not translated.

A key the engine did not register prints raw without its `#`, exactly like a key that does not exist. A stringtable comes only from an addon PBO at start; a `.layout` loaded from `$profile:` brings none, so text you change while iterating is a literal or is set from script. The `templates/stringtable.csv` of this pack carries the seven column header.

## Preview panels with no stringtable

`skills/dayz-layout-preview/gen_panel_layout.py` writes layouts for the `$profile:` loop (`hot-iteration.md`): a chat or log feed, a label and value panel, and a small HUD. Every text starts empty and is set at runtime, so no stringtable is needed; a ten line feed was filled this way in game. The widget names are a contract, listed in `templates/panel-contract.md`. `--self-test` checks the braces and that names are unique without starting the game.
