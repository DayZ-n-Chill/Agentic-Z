# dayz-terrain-builder-runner (EXPERIMENTAL)

Drive a Terrain Builder instance that this runner launched, by Win32 messages
only: menu commands through `PostMessage(WM_COMMAND)`, file dialogs through
`WM_SETTEXT`. No `SendInput`, no `SetCursorPos`, no `SetForegroundWindow`: the
desktop stays usable while it runs. Windows only.

**Experimental.** Verified on Spanish Windows, on an instance
this runner launched: menu commands and the standard Windows file dialogs,
with Terrain Builder never taking the focus. **Not verified:** Generate
Layers, a real import, an end-to-end WRP export. This was measured in Terrain
Builder (DayZ Tools), not in the game. The tests here do not repeat it: they
use a fake `user32` and never start Terrain Builder.

Why it can work without focus: Terrain Builder is a wxWidgets 2.8.12 program,
a 32-bit PE with the large-address-aware flag, and `wxFrame::HandleCommand`
processes `WM_COMMAND` without a focus check (wxWidgets 2.8.12 source,
`src/msw/frame.cpp:951-979`; not yet checked against the wxWidgets source or
the executable).

## Before a run

- **A disposable instance and project.** `probe` posts every enabled menu
  entry under a prefix and cancels what opens: whatever an entry does, it
  does.
- **Back up `TerrainBuilder.opt`, `GUILayout.opt` and `Proj.vdat`**, and
  restore them after: Terrain Builder rewrites them on exit. The `.opt` files
  are in DayZ Tools' `Bin/TerrainBuilder` (not yet checked on an install).
- Close the instance with `close`, then remove the state file (or point
  `TBRUNNER_STATE` at a new one): `close` does not clear the recorded pid, and
  `launch` refuses while one is recorded.

## Configure

| Setting | What |
|---|---|
| `--tb-exe <path>` or `TBRUNNER_TB_EXE` | DayZ Tools' `Bin/TerrainBuilder/terrainBuilder.exe`. No default; every command needs it, and its `Logs` folder is where the `.rpt` logs are read. `--tb-exe` goes before the command and wins over the variable |
| `TBRUNNER_STATE` | The state file, `tbrunner-state.json` in the temporary directory by default. `menu.json` is written next to it |

## Commands

```powershell
$env:TBRUNNER_TB_EXE = "<DayZ Tools>\Bin\TerrainBuilder\terrainBuilder.exe"
python scripts/tools/dayz-terrain-builder-runner/tbrunner.py launch
python scripts/tools/dayz-terrain-builder-runner/tbrunner.py menu
python scripts/tools/dayz-terrain-builder-runner/tbrunner.py command <menu id>
python scripts/tools/dayz-terrain-builder-runner/tbrunner.py dialog_file <path>
python scripts/tools/dayz-terrain-builder-runner/tbrunner.py close
```

| Command | Does |
|---|---|
| `launch` | Start Terrain Builder without activating it, record its pid and its new `.rpt` log, send its frame to the bottom of the z-order without activating it |
| `windows` | List the instance's top windows, the controls of its dialogs, and the foreground window and cursor |
| `menu` | Print every menu leaf with its id and write the whole tree to `menu.json` |
| `command <id>` | Refresh the menus, then post one menu command to the frame; refused while a dialog is open |
| `dialog_file <path>` | Type a path into the one open file dialog and press its OK by id 1, right for the standard Windows dialogs and not for Terrain Builder's own |
| `dialog_button <id>` | Press a button of the one open dialog **by id** (read the gotcha on swapped ids first) |
| `wait_log <regex> <seconds>` | Wait for a match in the instance's `.rpt` log |
| `save_loop <id> <tv4p> <count>` | Post a save command `count` times; `passed` counts a changed `.tv4p`, Terrain Builder not taking the foreground, and no dialog. `foreground_same` and `cursor_same` are reported per iteration and do not count toward `passed` |
| `close` | Post `WM_CLOSE` to the frame |
| `probe <prefix>` | Post every enabled leaf under a menu path prefix (`File > Export`), or exact paths joined by `\|`, record the dialogs each opens and cancel them by label; stops at a dialog it cannot close |

Every command addresses only the instance whose pid the state file records.
Output is JSON (or, for `menu`, one line per entry) on stdout.
`command` and `save_loop` print two JSON documents back to back: first a one-line `{"item": ...}` object naming the menu item and whether it is disabled, then the indented report.
Parse them one at a time (for example with `json.JSONDecoder().raw_decode`), not with a single `json.loads`.

| Exit | Meaning |
|---:|---|
| `0` | The command ran; its JSON says what happened, a log line not found included |
| `1` | Refused or failed, `error: <reason>` on stderr: not Windows, no instance or log recorded, no frame, a dialog open or not exactly one, no filename box, the executable not a file, an instance already recorded |
| `2` | Usage error, or no executable set |

## Gotchas

Measured in Terrain Builder (DayZ Tools):

- **Menu ids are dynamic,** and wxWidgets updates a menu's enabled state only on
  `WM_INITMENUPOPUP`: refresh before every command. `command`, `save_loop` and
  `probe` do; read ids from a fresh `menu`.
- **Entries with an icon are owner-draw** and expose no text: `menu` prints
  them as `#<index>` with `(ownerdraw)`.
- **Terrain Builder's own dialogs swap the ids:** Ok is 2 and Cancel is 1, the
  reverse of `IDOK` and `IDCANCEL`. Press them by label: once, a cancel sent by
  id ran an SHP export. `probe` cancels by label; `dialog_button` presses by id.
- **Terrain Builder rewrites `TerrainBuilder.opt`, `Proj.vdat` and
  `GUILayout.opt` on exit:** back them up.
- **The `.rpt` log records neither imports nor Generate Layers,** so
  `wait_log` cannot confirm them.
- **Button labels are Spanish and English** (`ok`, `aceptar`, `abrir`,
  `guardar`, `open`, `save`; `cancel`, `cancelar`), measured on Spanish
  Windows. Another language needs its labels added.

## Design decisions

- The Win32 functions are bound when a command runs, so the module imports on
  any OS, and every command refuses off Windows.
- The executable comes from `--tb-exe` or `TBRUNNER_TB_EXE`; no install path
  is built in.
- Every refusal is an explicit error (exit 1), not an assert or a traceback:
  no state, log or frame recorded, a file that cannot be read, a bad
  `wait_log` pattern.
- Ten subcommands, read with argparse. `press_label` is a helper used by
  `probe`, not a subcommand.
- A menu item that `GetMenuItemInfoW` cannot read does not stop the run:
  `menu` prints it with its error and exits 0, and `probe` leaves it out of
  the leaves it posts.

## Tests

```powershell
python -m pytest scripts/tools/dayz-terrain-builder-runner/tests -q
```

They run on any OS. `user32` is a fake that records every call and fills the
out-parameters and buffers the way the real calls do, and `kernel32`, which
tbrunner binds but never calls, a fake that fails the test on any call; no test
calls a real Windows function or starts Terrain Builder or another program;
the three `TestImport` tests spawn `sys.executable -c` to import the module in
a child Python.
