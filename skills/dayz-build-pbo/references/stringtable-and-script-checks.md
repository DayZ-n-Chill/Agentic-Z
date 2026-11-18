# Stringtable and script checks

What to check in a mod's stringtable and scripts before packing: that every `#STR_` key resolves from a `stringtable.csv` DayZ can read, and that the scripts avoid what Enforce Script rejects. The other pre-build checks are indexed in `pre-build-checks.md`.

## DayZ reads `stringtable.csv`

DayZ uses `stringtable.csv`, not the `stringtable.xml` of Arma 3. One DayZ mod project tree holds 38 `stringtable.csv` files and no XML, and the deployed PBOs checked carry the CSV only. An XML stringtable is a file the engine never reads, and it does not complain: an unresolved key prints its own name, and the client RPT logs nothing about it. The failure stays silent all the way to the player's screen.

The format, as shipping mods carry it: a header row, then one row per key. The key sits in column 1 without the leading `#`, which belongs only to the reference in code, config or a `.layout`. Save it as UTF-8 with no BOM and LF line endings.

```csv
"Language","original","english","spanish","german","russian","chinesesimp"
"STR_MYMOD_DEVICE_NAME","Device Name","Device Name","Device Name","Device Name","Device Name","Device Name"
```

An unresolved stringtable is a header problem, not an addon size problem. Measured in game: a three-file addon (`$PBOPREFIX$`, a minimal `config.cpp` and `stringtable.csv`) with two data rows resolves its keys, provided the CSV carries the seven-column header above. With a four-column header, without `german`, `russian` and `chinesesimp`, every key stays unresolved at any size, although the PBO mounts and serves files and the client's own language column holds text. Fill untranslated columns with the English text. The full rule is in `skills/_shared/ui/localization.md`.

Vanilla's own header starts with `"Language","original","english"` and has 15 language columns, those four among them (`P:\languagecore\stringtable.csv:1`).

## Stringtable checks

| Check | Level |
|---|---|
| `#STR_` references found in `.c` and `.cpp` files, `config.cpp` (`displayName`, `description`) and every `.layout` (widget `text`) | Collect them all |
| A `#STR_` reference exists but no `stringtable.csv` | Fail |
| The header row is present and every data row has the same column count | Fail |
| Every referenced key is in column 1 of a `stringtable.csv`, without the `#` | Fail |
| A key defined but never used | Warn |
| A language column empty for a key | Warn |
| A generic key name such as `STR_UI_YES` | Warn; use a mod-specific prefix so keys do not clash with other mods |

Sample report lines:

```text
[FAIL] stringtable.csv not found, but 5 #STR_ references in config.cpp
[PASS] stringtable.csv header valid (7 columns, every row matches)
[FAIL] Missing key: STR_MYMOD_DEVICE_NAME (config.cpp line 23)
[WARN] Unused key: STR_OLD_DESCRIPTION
[WARN] Russian text missing for STR_ITEM_DESC
```

## Script checks

`/dayz-build-pbo` already runs the script validator's code rules through `/dayz-lint`; how to run it alone and read its result is in `script-linter-and-compile-gate.md`. The checks below are the fallback when the validator is not available, and a useful second pass when it is. Run them when the addon has a `scripts/` folder.

| Check | Rule |
|---|---|
| Ternary | No `cond ? a : b`; write `if` and `else`. |
| Array concatenation | No `+=` on arrays; add with `.Insert()` or `.InsertAll()`. |
| Bare expressions | No function result left without an assignment or statement. |
| `#include` paths | Every `#include "path/file.h"` points at an existing file; check relative and absolute forms. |
| `GetGame()` in a destructor | Guarded by a null check. |
| `Print()` left in | Warn, not fail. |
| Endless loops | No `while (true)` without a `break`. |
| Return values | Every non-void function returns on every path. |
| Basic syntax | No unclosed strings, bad escape sequences, stray tokens or broken class declarations. |

Never flag `++`, `--` or `foreach`; vanilla uses them (`foreach` at `P:\scripts\3_game\tools\cameratools.c:14`, `last_index++` at `P:\scripts\3_game\tools\tools.c:200`). A search of every `.c` file under `P:\scripts` finds no ternary, which matches `skills/_shared/enscript/patterns/language_workarounds.md` ("No vanilla script uses `cond ? a : b`").

Sample report lines:

```text
[WARN] scripts/Item_Base.c line 42: array += concatenation is not supported; use .InsertAll()
[WARN] scripts/Item_Base.c line 103: GetGame() called in a destructor without a null check
[FAIL] #include "scripts\missing.h" not found
[PASS] Script syntax valid (no unclosed braces or quotes)
```
