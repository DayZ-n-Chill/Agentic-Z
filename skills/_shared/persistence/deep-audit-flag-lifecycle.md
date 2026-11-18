# Two stores that must move together

Covers mechanical check 4 of the deep audit (`deep-audit.md`): a concept the mod keeps in more than one place, such as a flag in memory and a file on disk, where one place changes and the other does not. Run it for every concept kept in two places, and for every concept that must survive a restart.

Each store looks right when read on its own; the bug is the difference between them, so reading the code path by path misses it. The store names, functions and `file:line` values in the tables come from a third-party virtual storage mod. They show the shape of each table and are not vanilla facts. The search line is a pattern for the agent's own search tool.

## Example: an admin command that cleared one store

In the virtual storage mod a quarantined container lived in two stores: a `.quarantine.json` file on disk and an `m_AdminRecoveryFlags` map in memory. The admin command `recover-quarantine <sid>` deleted the file but only set a flag in memory. After the next boot the flag was gone and so was the file, so the container looked healthy while its data file was still in the quarantined format. Loading it produced corrupt state.

The fix keeps the two stores in step: delete the file only after the recovery write succeeded, and save the recovery flag to disk when the recovery takes more than one boot.

## List the stores for each concept

For each concept the mod tracks (quarantine, virtualizing, whether another storage mod is present), list every place it lives:

| Concept | In memory | On disk | Marker file | Other |
|---|---|---|---|---|
| Quarantine status | `m_QuarantineMap` | none | `.quarantine.json` | none |
| Admin recovery flag | `m_AdminRecoveryFlags` | none, the defect | none | none |
| Virtualize state | `m_StateMachine[sid]` | header byte | `.virtualizing` | none |
| Other storage mod detected | `m_ExternalVSDetected` | none, a defect | none | none |

A concept in two or more stores has to keep them in step. A concept in one store that must survive a crash or a restart needs a second store on disk; report the missing store as a finding.

## Record what each operation changes

For every operation on a concept with two or more stores, record which stores it changes:

| Operation | Changes `m_QuarantineMap` | Changes `.quarantine.json` | In one step? |
|---|---|---|---|
| `Quarantine(sid)` | set | write | no: write first, then set |
| `Recover(sid, success)` | clear | delete | no: delete first, then clear |
| `OnBoot` (load the file) | set | read | not applicable |
| `recover-quarantine` admin command | sets a flag in another map | deletes the file | the stores split |

The row where the stores split is the finding. Fix it one of two ways: the admin command updates both stores, or it uses the same store as `Recover` and the separate flag map goes.

## Check the order

Two stores that change together still need an order. Disk first suits data that must survive, because the disk holds the truth and memory is a cache:

```text
1. Write the file with the new state and make sure it is on disk
2. Update the map in memory
3. A crash between 1 and 2: the next boot reads the file and rebuilds memory, so nothing is lost
```

Memory first suits only state that can be computed again, because writes are batched and the file is a checkpoint:

```text
1. Update the map in memory
2. Schedule the file write
3. A crash between 1 and 2: the state is lost, safe only if it can be computed again
```

Use disk first for quarantine, saved flags, money and anything else players lose. Keep memory first for per tick caches.

Enforce Script has no flush call. The nearest a mod gets is `CloseFile` on the handle (`P:\scripts\1_core\proto\ensystem.c:443`) and then reading the file back, so in a DayZ mod step 1 reads "write the file, close it, read it back and check it".

## Check that every reset clears every store

Find the reset functions:

```text
Grep "Reset|Clear|Purge|Wipe" --type c --output_mode content -n true
```

Walk each one and note which stores it touches. If a concept lives in stores A, B and C and the reset clears only A and B, that is a finding.

## Report

| Concept | Issue | Stores affected | File:Line |
|---|---|---|---|
| Admin recovery flag | Memory only, lost on restart | `m_AdminRecoveryFlags` only | admin.c:88 |
| Other storage mod detected | Memory only, lost on world reload | `m_ExternalVSDetected` only | mission.c:42 |
| Quarantine | Reset deletes the file but not the map entry | `m_QuarantineMap` not cleared in `DeleteContainerFiles` | cleanup.c:55 |

Severity, in the terms of `deep-audit.md`:

- Data players lose kept only in memory: data loss.
- A reset that wipes the disk but leaves stale data in memory: needs recovery.
- Memory first on data players lose: data loss or needs recovery, depending on whether the state can be rebuilt.

Which concepts need a store on disk:

- Survives a reboot or a world reload: on disk.
- Lives only from tick to tick: memory is fine.
- An admin can override it: both stores change together.
- A recovery path reads it: on disk.

Not findings: per session UI state, per tick caches that can be computed again, and values computed from what is on disk (the disk is the truth).

Allow about 5 minutes per concept with two stores; the virtual storage mod had about four, so about 20 minutes. This check finds fewer bugs than the path naming and cleanup checks, but the ones it finds are usually data loss.
