# Cleanup of marker and side files

Covers mechanical check 2 of the deep audit (`deep-audit.md`): code writes a marker or side file next to a save file, and the matching cleanup does not remove it. The file stays, a later boot misreads the container's state, and recovery takes the wrong branch without a word. Run it for any mod that writes such files.

Each writer looks right on its own; the bug is a missing line in the cleanup code, which sits in another file. The function names, suffixes and `file:line` values in the tables come from a third-party virtual storage mod. They show the shape of each table and are not vanilla facts. The search lines are patterns for the agent's own search tool.

## Example: a marker that outlived an admin reset

In the virtual storage mod `StartRestore` wrote `.restoring` and `WriteManifest` wrote `.manifest.json`. Both writers were right. `DeleteContainerFiles(sid)` removed `.lfv`, `.lfv.bak1`, `.lfv.bak2`, `.tmp`, `.virtualizing` and `.quarantine.json`, but not `.restoring` or `.manifest.json`. After an admin reset of a container that was being restored, the marker stayed. At the next boot recovery found a `.restoring` with no `.lfv`, took the container for one that crashed during a restore, and blocked the slot.

## List every writer

Find every place that writes a file or a known marker:

```text
Grep "FileWrite|FileSave|JsonFileLoader\.SaveFile|JsonSaveFile|MakeDirectory|OpenFile|FPrint|CopyFile|FileSerializer" --type c --output_mode content -n true
Grep "\.virtualizing|\.restoring|\.manifest\.json|\.quarantine\.json|\.partial|\.locked" --type c --output_mode content -n true
```

`FileWrite` and `FileSave` are names a mod may give its own wrappers; neither exists in `P:\scripts\1_core` or `P:\scripts\3_game`. The vanilla calls that put a file on disk are:

| Call | Source |
|---|---|
| `OpenFile` with a write mode, then `FPrint` or `FPrintln` | `P:\scripts\1_core\proto\ensystem.c:417`, `:462`, `:481` |
| `CopyFile`, `MakeDirectory` | `ensystem.c:531`, `:525` |
| `JsonFileLoader` `SaveFile` and `JsonSaveFile` | `P:\scripts\3_game\tools\jsonfileloader.c:42` and `:134` |
| A `FileSerializer` | `P:\scripts\1_core\proto\serializer.c:103` |

| File | Written by | File:Line | Lives as long as |
|---|---|---|---|
| `.virtualizing` | `Virtualize_BeginBatch` | persistence.c:340 | the virtualize state |
| `.restoring` | `StartRestore` | restore.c:88 | the restore state |
| `.manifest.json` | `WriteManifest` | manifest.c:42 | the container |
| `.quarantine.json` | `WriteQuarantineSidecar` | quarantine.c:66 | the failure |

## Three places each file must be removed

Every file in the writer table must be handled in three places:

1. The success path removes or rotates it.
2. The reset (`DeleteContainerFiles(sid)` or its equivalent), run by an admin or a purge of the `.lfv`, removes it.
3. The scan at boot handles it when the file exists and its owner's state is unknown.

Find the deletes:

```text
Grep "DeleteFile|RemoveFile" --type c --output_mode content -n true
```

The vanilla delete is `DeleteFile` (`P:\scripts\1_core\proto\ensystem.c:528`); `RemoveFile` is in the pattern only to catch a mod's own wrapper. Find the success path delete and the reset, and confirm the boot scan in the recovery code lists this file.

| File | Success path deletes it | Reset deletes it | Boot scan handles it |
|---|---|---|---|
| `.virtualizing` | yes (persistence.c:412) | yes (cleanup.c:55) | yes (recovery.c:140) |
| `.restoring` | yes (restore.c:188) | no, the defect | yes (recovery.c:155) |
| `.manifest.json` | not applicable, rewritten in place | no, the defect | not applicable |
| `.quarantine.json` | not applicable, admin only | yes (cleanup.c:60) | yes (recovery.c:170) |

Every "no" is a finding:

- Boot scan missing: data loss, because orphans pile up and the slot stays blocked.
- Reset missing: data loss or needs recovery, because an admin reset leaves stale state.
- Success path delete missing: needs recovery, because the next operation sees a stale marker.

"Not applicable" in the success column does not carry over to the reset column. A manifest rewritten in place needs no delete on success, but a purged container must not leave a `.manifest.json` that points at nothing.

## What to keep in mind

- A writer of a file with a fixed suffix must be cleaned up in all three places.
- A marker (it carries state) and a side file (it carries data) follow the same rules. Data that is "just metadata" still needs cleanup.
- Admin commands and synchronous shortcuts often write files the main path cleans up and they do not (`deep-audit-entry-points.md`).

Allow about 5 minutes per file; the virtual storage mod had four, so about 20 minutes. No other check finds as many bugs per minute.
