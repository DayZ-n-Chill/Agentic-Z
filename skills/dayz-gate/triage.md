# Triage reference

How `triage.py` matches log lines, how to triage a log the user pasted, and how to record a diagnosis so the next run sees it as known. The short version is in the Triage section of [SKILL.md](SKILL.md).

## How a line is matched

`triage.py` fingerprints each line (timestamps, absolute paths, hex addresses and numbers normalized, lowercased) and matches it against `known-errors.json` (regex entries shipped with the repo) and the project's learned file `.claude/local-memory/dayz-gate-known-errors.json`. Run it on its own for any log:

```cmd
python "<skill-dir>\triage.py" <log-file> [...] [--mod <ModName>] [--mod-dir workspace\<ModName>] [--json]
```

## Which lines count as errors

A line is an error when one of the category patterns in `triage.py` (`ERROR_CATEGORIES`) matches it, or when a catalog or learned entry matches it. The categories:

| Category | Lines |
|---|---|
| `crash` | `Unhandled exception`, `Access violation` |
| `compile` | `Can't compile "<Module>" script module`, `SCRIPT (E): @"file,line": ...`, `file.c(line): ...` |
| `null_pointer`, `cant_find` | `NULL pointer to instance`, `Can't find ...`. The in-game gate fails these only when they name the mod. |
| `connection` | A refused join: `0x00020005` (filePatching), `0x00020017` (a diag client on a server that is not diag), `0x00020013` (different game builds), `0x00010002` (signatures) |
| `storage` | Persistence the server cannot read: `!!! Serious stream damage detected during load`, `Failed to read modstorage for entity`, `Scripted variables corrupted` |
| `server_exit` | A server that shuts itself down: `[Server] :: termination in: N`, `BattlEye initialization failed` |
| `mission`, `missing_config`, `missing_texture`, `missing_model` | `Mission script has no main function`, `No entry '...'`, `Cannot load texture`, `Cannot open object` |

The `storage` and `server_exit` lines say the test run itself is not valid; they are not defects of the mod. A `storage` line names a random persisted entity, not the cause: the cause is the mod set or an unclean stop, and the fix resets the world, so ask the user before applying it. The measured cases behind these entries are in `skills/dayz-test-ingame/references/troubleshooting.md` and `skills/dayz-test-ingame/references/build-and-storage-traps.md`.

Two things every DayZDiag session prints are deliberately not errors, and `test_triage.py` pins that:

- The line `Module PluginConfigDebugProfile is not Registred in PluginManager.c!` and the `SCRIPT (E)` stack that follows it (`GetPlugin()`, `OnInit()` of `pluginitemdiagnostic.c`, `PluginsInit()` and so on). Vanilla prints it under `DIAG_DEVELOPER` (`P:\scripts\4_world\plugins\pluginmanager.c:339`), once per peer on each mission start, with or without a mod.
- `Can't load @<Mod>/Anims/cfg/skeletons.anim.xml`, reported once for every loaded mod.

Do not add catalog entries for them: an entry would make every watch report them.

## Pasted logs

When the user pastes a crash log or RPT instead of naming a file, triage the pasted text. Pipe it on stdin, or pass it with `--text`:

```cmd
python "<skill-dir>\triage.py" --stdin --json < pasted.txt
python "<skill-dir>\triage.py" --text "<pasted log>" --json
```

Results look the same as for a file, with `file` set to `<pasted>` and `line` counted within the paste. Give the user the cause and fix of each `known` result and hand it to its `owner_agent`. Dispatch `dayz-mod-debugger` with only the `new` lines and the log around them. The paste-in hook (`hooks/paste_router.py`) already runs this triage on every prompt that holds DayZ error lines and adds the result to the conversation, so for a pasted log you usually only act on its list.

## Recording a diagnosis

After a reviewer has diagnosed a `new` result, record it so the next run sees it as known:

```cmd
python "<skill-dir>\triage.py" --learn <id> --fingerprint "<fingerprint or raw log line>" [--meaning "..." --fix "..." --owner <agent>]
```

An existing `<id>` lends its meaning, fix and owner; a new id needs all three. Learned entries go to the per-project file, never into the shipped `known-errors.json`; add an entry there by hand (with a `source`) when the error is general.
