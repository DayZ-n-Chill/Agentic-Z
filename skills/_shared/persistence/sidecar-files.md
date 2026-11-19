# Files of the mod's own

How to keep mod data in its own file under the server profile: the file functions vanilla offers, the load rules, a save sequence that can be recovered at every step, and why it is never atomic. Open it for server wide data, or anything an admin must read or repair outside the game. The table of loaders and the `$profile:` prefix are in `versioning-and-migration.md`, "Data outside the object store".

## What script can do with files

| Function | Source |
|---|---|
| `FileExist`, `OpenFile`, `ReadFile`, `CloseFile` | `P:\scripts\1_core\proto\ensystem.c:397`, `:417`, `:425`, `:443` |
| `FPrint`, `FPrintln`, `FGets` | `ensystem.c:462`, `:481`, `:501` |
| `FindFile` (folder scan), `MakeDirectory` | `ensystem.c:520`, `:525` |
| `DeleteFile`, `CopyFile` | `ensystem.c:528`, `:531` |

There is no rename, no move and no flush. A search of `ensystem.c` for `Rename` or `MoveFile` finds nothing. The comments on `DeleteFile` and `CopyFile` say they work only on `$profile:` and `$saves:` paths. A design that says "rename", "move" or "atomic replace" uses an API DayZ does not have, and the nearest thing to a flush is `CloseFile` followed by reading the file back.

For JSON, use `JsonFileLoader<T>.LoadFile(filename, out data, out errorMessage)` and check its `bool` before using `data` (`P:\scripts\3_game\tools\jsonfileloader.c:7`). Log `errorMessage` without private paths or player IDs. `JsonLoadFile` is deprecated and returns nothing, so a failed parse looks like success (`jsonfileloader.c:105`).

## Loading

1. If the file cannot be opened, return failure. Leave the original alone and create nothing.
2. Read into a local copy. A failed or short read returns failure and applies nothing.
3. Check the header, the version, the declared lengths and the whole payload before applying anything.
4. Broken JSON, a foreign layout, extra data at the end or a cut file keeps the original as evidence and applies no partial values.

## Saving so that every step can be recovered

Use fixed names next to the file: `<file>.tmp`, `<file>.bak` and, if you keep a checksum, `<file>.sha256`.

1. Build the whole new record in memory, with its own version header.
2. Write it to `<file>.tmp` and close it. If the write fails, the half written temp file may be deleted; the original is untouched.
3. Open `<file>.tmp` again, read all of it, parse it and check it holds what you meant to write. A complete temp file that fails this check is kept as evidence.
4. If `<file>` exists, copy it to `<file>.bak`. If that fails, stop; the original and the temp file are both still there.
5. `DeleteFile(<file>)`, then `CopyFile(<file>.tmp, <file>)`. If the delete fails, stop. If the server stops after the delete, or the copy fails, the file is missing, but the temp file and the backup make recovery certain.
6. Open `<file>` again and check all of it. If it is short or invalid, delete it and keep `<file>.tmp` and `<file>.bak`. `CopyFile` returning `true` is not proof the bytes arrived.
7. If you keep a checksum, write it now. If that fails, keep everything and do not report a clean save.
8. Delete `<file>.tmp` only after steps 6 and 7 passed.

Between steps 5 and 6 the file does not exist. The backup and the kept temp file make that gap recoverable; nothing makes it atomic. Treat any code or comment that calls this replace atomic as a defect.

## The nine places a file operation can fail

Inject a failure at each of these and check what survives.

| Where | Injected failure | What must hold |
|---|---|---|
| Open for reading | The handle is 0 | Original untouched; no new file created |
| Read | Input cut halfway | No partial state applied |
| Parse | Broken JSON or a foreign layout | Original untouched and kept as evidence |
| Backup | The backup copy fails | Stop before the replace; original and `.tmp` remain |
| Temp write | `FPrint` fails or the disk is full | The half written temp may go; original untouched |
| Temp check | Header or payload does not match | Keep the complete `.tmp`; original untouched |
| Replace | Failure between the delete and the copy | File may be missing; `.tmp` and `.bak` are there |
| Check after copy | The copied file is short | Delete the bad file; keep `.tmp` and `.bak` |
| Leftover `.tmp` at boot | The candidate is valid, or cut | Promote only checked content; never decide by date |

Every row keeps either the original bytes or the files needed to recover them. Returning failure without saying which files remain is not a complete result.

## A leftover temp file at boot

Judge `<file>.tmp` by its content, never by its modification time; the time says when the folder entry changed, not whether the bytes form a whole record.

* If it cannot be read fully, has a bad header, declares a length it does not hold, or fails the layout check, do not promote it. Keep it as evidence and leave the real file alone.
* If it checks out, back up the real file, do the same delete and copy, check the copy, write the checksum, and only then delete the temp file.
* If promotion fails after the delete, keep the temp file and the backup. The same gap applies.

## Vanilla's mission file is not a model

`BunkerBroadcastPersistenceStorage` writes `$mission:BunkerBroadcastPersistenceStorage.bin` (`STORAGE_PATH` at `P:\scripts\4_world\classes\bunkerbroadcasthandler.c:18`) with a `FileSerializer`:

* It holds two objects: the bunker report time (`m_LastReportHour`, `m_LastReportMinute`) and `m_LastActiveBunkers`, a map from bunker ID to lock code (`bunkerbroadcasthandler.c:5` to `:14`).
* `Save` opens it for writing and writes both objects (`:73` to `:81`). There is no version header, no temp file and no check after writing.
* `Load` returns `true` once `Open` succeeds and ignores what `Read` returns (`:56` to `:68`), although `Serializer.Read` returns `bool` (`P:\scripts\1_core\proto\serializer.c:58`). A missing file leaves the defaults the constructor set (`:29` to `:34`).
* `DeleteFile` and `CopyFile` do not work on `$mission:`, so the recoverable save above cannot be done there.

A mod that keeps similar state puts it under `$profile:` or `$saves:`, with a version header and a check on every read. If it must sit next to the mission, document that it cannot be rotated and that a failed read is invisible.

## Checklist

- The file has its own version header.
- Every loader result and error message is checked before any state is applied.
- Reads go into locals; a parse or length failure applies nothing.
- The temp file is read back and checked before the backup and the replace.
- A failed backup stops before the delete.
- The gap between delete and copy is documented as not atomic.
- The copy is read back and checked in full.
- A bad copy is deleted while `.tmp` and `.bak` stay.
- The checksum is written before the temp file is removed.
- A valid and a cut leftover temp file get different, fixed actions, and none is decided by date.
