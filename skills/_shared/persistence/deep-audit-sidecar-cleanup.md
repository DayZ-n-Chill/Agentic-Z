# Sidecar cleanup symmetry: mechanical check 2

Catches the bug class where a writer creates a sidecar or marker file and the matching cleanup site fails to remove it. The file stays, later boots misread the container's state, and recovery silently misroutes. Open this in step 1 for any mod that writes marker or sidecar files next to its save files.

Reasoning agents miss this because each writer looks correct in isolation: the bug is the missing entry on the deleter side, which is a different file.

The function names, suffixes and `file:line` values in the tables are from the virtual storage example (third-party mod); they show the shape of each table and are not vanilla facts. The search lines in the code blocks are recipes for the agent's search tool.

## Worked example: VULN-008 (virtual storage mod)

`StartRestore` wrote `.restoring`. `WriteManifest` wrote `.manifest.json`. Both writers were correct. `DeleteContainerFiles(sid)` removed `.lfv`, `.lfv.bak1`, `.lfv.bak2`, `.tmp`, `.virtualizing` and `.quarantine.json`, but not `.restoring` and not `.manifest.json`. After an admin reset of a container in the middle of a restore, the marker survived. On the next boot, recovery saw a `.restoring` with no `.lfv` and treated the container as crashed during restore, blocking the slot.

## Procedure

### Step 1: inventory every sidecar and marker writer

Search for every site that writes a recognized sidecar or marker extension:

```text
Grep "FileWrite|FileSave|JsonFileLoader\.SaveFile|JsonSaveFile|MakeDirectory" --type c --output_mode content -n true
Grep "\.virtualizing|\.restoring|\.manifest\.json|\.quarantine\.json|\.partial|\.locked" --type c --output_mode content -n true
```

`FileWrite` and `FileSave` are names a mod may give its own wrappers; a search of `P:\scripts\1_core` and `P:\scripts\3_game` finds neither. The vanilla calls that put a file on disk are `OpenFile` with a write mode (`P:\scripts\1_core\proto\ensystem.c:417`) followed by `FPrint` or `FPrintln` (`ensystem.c:462`, `ensystem.c:481`), `CopyFile` (`ensystem.c:531`), `MakeDirectory` (`ensystem.c:525`), the `JsonFileLoader` calls `SaveFile` (`P:\scripts\3_game\tools\jsonfileloader.c:42`) and `JsonSaveFile` (`jsonfileloader.c:134`), and a `FileSerializer` (`P:\scripts\1_core\proto\serializer.c:103`). Add `OpenFile|FPrint|CopyFile|FileSerializer` to the first pattern so a writer that calls them directly is not missed.

Build the table:

| Sidecar | Writer site | File:Line | Lifecycle owner |
|---|---|---|---|
| `.virtualizing` | `Virtualize_BeginBatch` | persistence.c:340 | virtualize state |
| `.restoring` | `StartRestore` | restore.c:88 | restore state |
| `.manifest.json` | `WriteManifest` | manifest.c:42 | per container |
| `.quarantine.json` | `WriteQuarantineSidecar` | quarantine.c:66 | per failure |

### Step 2: inventory every consumer site

For each sidecar, three obligations exist downstream:

1. **Successful completion path**: the success branch must remove or rotate the marker.
2. **`DeleteContainerFiles(sid)` (or the equivalent reset)**: an admin reset or a purge of the `.lfv` must remove the sidecar.
3. **Boot orphan cleanup**: the first-boot scan that handles "marker exists, owner state unknown".

For each row in the writer table, walk these three:

```text
Grep "DeleteFile|RemoveFile" --type c --output_mode content -n true
```

The vanilla delete is `DeleteFile` (`P:\scripts\1_core\proto\ensystem.c:528`); `RemoveFile` is in the pattern only to catch a mod's own wrapper.

Find the success-path delete and `DeleteContainerFiles` (or your project's equivalent). Confirm that the boot scan in the recovery module enumerates this sidecar.

### Step 3: cross table

| Sidecar | Success-path delete? | DeleteContainerFiles? | Boot orphan scan? |
|---|---|---|---|
| `.virtualizing` | yes (persistence.c:412) | yes (cleanup.c:55) | yes (recovery.c:140) |
| `.restoring` | yes (restore.c:188) | **no: VULN-008** | yes (recovery.c:155) |
| `.manifest.json` | n/a (overwritten in place) | **no: VULN-008** | n/a |
| `.quarantine.json` | n/a (admin only) | yes (cleanup.c:60) | yes (recovery.c:170) |

Any "no" in any column is a finding. Severity:

- Boot scan missing: P0 (orphans accumulate forever, slot wedged)
- `DeleteContainerFiles` missing: P0 or P1 (an admin reset leaves stale state)
- Success-path delete missing: P1 (the next operation sees a stale marker)

### Step 4: the "n/a" trap

`.manifest.json` shows `n/a` for the success-path delete because manifests are overwritten in place. That is fine for the success path, but the `DeleteContainerFiles` column still requires a yes. A purged container must not leave behind a `.manifest.json` that points to nothing. Do not let "n/a" leak into the reset and cleanup column.

## Heuristics

- A writer that produces a file with a fixed suffix has a cleanup obligation in three places. Always.
- A "marker" (carries state) and a "sidecar" (carries data) follow the same rules. Do not skip sidecars on the assumption that "the data is just metadata".
- Watch for sidecars written by **alternative entry points** (admin commands, synchronous paths). Often the canonical path cleans up and the shortcut does not. See `deep-audit-entry-points.md`.

## Time budget

About 5 minutes per sidecar (4 sidecars in that mod, so about 20 minutes). Worth it: this is the single highest-leverage check by bugs found per minute.
