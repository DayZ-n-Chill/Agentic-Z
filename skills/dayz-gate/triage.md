# Triage reference

How `triage.py` matches log lines, how to triage a log the user pasted, and how to record a diagnosis so the next run sees it as known. The short version is in the Triage section of [SKILL.md](SKILL.md).

## How a line is matched

`triage.py` fingerprints each line (timestamps, absolute paths, hex addresses and numbers normalized, lowercased) and matches it against `known-errors.json` (regex entries shipped with the repo) and the project's learned file `.claude/local-memory/dayz-gate-known-errors.json`. Run it on its own for any log:

```cmd
python "<skill-dir>\triage.py" <log-file> [...] [--mod <ModName>] [--mod-dir workspace\<ModName>] [--json]
```

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
