# Flag-lifecycle audit: mechanical check 4

Catches the bug class where two state stores must move together but one moves without the other. The most common shape: a flag in memory flips while the sidecar on disk still holds the previous truth, or the other way round. Open this in step 1 for every concept the mod tracks in more than one place, and for every concept that must survive a restart.

Reasoning agents miss this because each state store looks consistent internally: the bug is the asymmetry between stores.

The store names, functions and `file:line` values in the tables are from the LF_VStorage example (third-party mod); they show the shape of each table and are not vanilla facts. The search line in the code block is a recipe for the agent's search tool.

## Worked example: VULN-010 (LF_VStorage 1.4.6)

Quarantined containers had two state stores: a `.quarantine.json` sidecar on disk, and an `m_AdminRecoveryFlags` map in memory. The admin command `recover-quarantine <sid>` deleted the sidecar from disk but only set a flag in memory. On the next boot the flag in memory was lost and the sidecar was gone. The container appeared healthy. The actual data file was still in the quarantined format. Loading it produced corrupt state.

The fix had to keep the two stores in sync: clear the sidecar **after** the recovery write succeeded, and persist the recovery flag if the recovery needed more than one boot.

## Procedure

### Step 1: inventory the state stores per concept

For each concept the mod tracks (quarantine status, virtualization status, detection of an external virtual storage mod, and so on), list every place it lives:

| Concept | In-memory store | On-disk store | Sidecar | Other |
|---|---|---|---|---|
| Quarantine status | `m_QuarantineMap` | none | `.quarantine.json` | none |
| Admin recovery flag | `m_AdminRecoveryFlags` | none: VULN-010 | n/a | n/a |
| Virtualize state | `m_StateMachine[sid]` | header byte | `.virtualizing` | n/a |
| External VS detected | `m_ExternalVSDetected` | none: VULN-001 | n/a | n/a |

If the same concept lives in two or more stores, it has a flag-lifecycle obligation. If it lives in one store but should survive crashes and restarts, **it should be two stores**: flag the missing on-disk store as a finding.

### Step 2: for each concept with two or more stores, build a transition matrix

For every operation that touches the concept, record which stores it changes:

| Operation | Mutates `m_QuarantineMap` | Mutates `.quarantine.json` | Atomic? |
|---|---|---|---|
| `Quarantine(sid)` | set | write | no: write first, then set |
| `Recover(sid, success)` | clear | delete | no: delete first, then clear |
| `OnBoot` (load sidecar) | set | read | n/a |
| `recover-quarantine` admin | sets a flag in **another map** | deletes the sidecar | **stores diverge** |

The "stores diverge" row is the finding. Either:

1. the admin command must update both stores, or
2. the admin command must use the same store as `Recover` (no separate flag map).

### Step 3: verify the ordering invariants

Two stores that move together still need an order. Two valid patterns:

**Disk-first** (the durable truth is on disk, memory is a cache):

```
1. Write sidecar with new state, fsync
2. Update in-memory map
3. If crash between 1 and 2: next boot reads sidecar, restores memory: safe
```

**Memory-first** (writes are coalesced, the sidecar is a checkpoint):

```
1. Update in-memory map
2. Schedule sidecar write
3. If crash between 1 and 2: state lost: only safe if state can be recomputed
```

For data-critical stores (quarantine, persistence flags, money), use disk-first. Memory-first is acceptable only for stores where loss is recoverable (for example per-tick caches).

"fsync" in the disk-first pattern names the general step. Enforce Script has no flush call: the nearest a mod gets is `CloseFile` (`P:\scripts\1_core\proto\ensystem.c:443`) on the handle and then reading the file back, so in a DayZ mod step 1 reads "write the sidecar, close it, read it back and verify".

### Step 4: verify reset and cleanup symmetry

For each concept, the reset path must clear all stores:

```text
Grep "Reset|Clear|Purge|Wipe" --type c --output_mode content -n true
```

Find the reset functions. For each, walk down: which stores does it touch? If concept X has stores A, B and C and the reset touches only A and B, that is a finding.

### Step 5: output

Findings table:

| Concept | Issue | Stores affected | File:Line |
|---|---|---|---|
| Admin recovery flag | Memory only: lost on restart | `m_AdminRecoveryFlags` only | admin.c:88 |
| External VS detected | Memory only: lost on world reload | `m_ExternalVSDetected` only | mission.c:42 |
| Quarantine | Reset clears the sidecar but not memory | `m_QuarantineMap` not cleared in `DeleteContainerFiles` | cleanup.c:55 |

Severity:

- Memory only on a data-critical concept: P0
- Reset asymmetry where memory holds stale data after a disk wipe: P1
- Wrong ordering (memory-first on a critical store): P0 or P1 depending on recoverability

## Heuristics for spotting concepts that need two stores

- Crosses a reboot? Must be on disk
- Crosses a world reload? Must be on disk
- Crosses only ticks? In memory is fine
- Admin can override? Both stores must update consistently
- Recovery path reads it? Must be on disk

## Common false positives

- Per-session UI state (no need to persist)
- Per-tick computation caches (can be recomputed)
- Constants computed from on-disk state (the disk store is authoritative)

## Time budget

About 5 minutes per two-store concept. LF_VStorage had about 4 such concepts, so 20 minutes. The catch rate of this check is lower than that of the path-naming or sidecar-symmetry checks, but the bugs it finds are typically P0 (data-critical state held only in memory).
