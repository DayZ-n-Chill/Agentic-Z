# Evidence and controls

How to tell real evidence from evidence that only looks real: the deployed build against the source, which code path wrote a log line, positive and negative controls that can actually fail, inventories that are complete, and store constructors that write while they read. Open this in steps 1 and 3 and whenever a check comes back clean.

These are audit lessons from third-party projects; the DayZ facts in the last section were measured in game and cannot be checked on `P:\`. The vanilla storage version they refer to is `GAME_STORAGE_VERSION` (`P:\scripts\3_game\global\game.c:5`).

## Production triage: deployed artifact, path attribution, gates whose name lies, starting auditors

Case: the LF_VStorage mod, five production bugs and a dual audit.

- **The deployed artifact is not the source (before step 1 when the trigger is a production bug)**: if audited code is distributed packaged (PBO/build), compare artifact mtime vs relevant fix files mtime AND probe INSIDE artifact (string-probe classnames on binary, without unpacking) BEFORE root-causing against source. Declare drift as its own finding. Case: PBO 28-May without 01-Jun CodeLockBridge, 2 of 5 bugs were partially deployment drift.
- **Path attribution in log evidence**: a log line that "proves X works" is attributed to emitting path (synchronous shutdown vs action hook vs periodic scan) before classifying partial-vs-broken. Case: "MMG virtualizes" came ONLY from OnMissionFinish; zero runtime path activity in entire session.
- **Lying-named gates (add to auditor prompts)**: for each trigger gate function (HasX/CanY/IsZ), paste and read BODY, do not accept name as evidence of coverage. Case: `HasCargoOrAttachments` without any attachments check → all slot storage invisible to all 4 triggers; missed by 9 auditors + cross-actor and uncovered by user pushback.
- **Starting auditors (step 2)**: background agents automatically deny permission prompts outside the working folder, so start auditors in the foreground, all in a single turn (parallel). Case: mechanical checks agent bounced in background with PERMISSION-FAIL.

## Four standing rules for claims, fakes, locks and verifiers

- **Scope of a non-causality claim**: Bound every claim of non-causality to the size, version, fixture, and conditions where verified. Do not promote "X does not matter" as a universal conclusion if the corpus does not cover other regimes.
- **Fakes and fixtures**: Make every remote fake/stub emit the same types as the real wire, not just equivalent values. Do not use `is True`/`is False` with serialized data; explicitly test `0/1`, bool, and missing values according to contract. The fixture composes request as producer composes it, never the most complete one "for convenience": facing in-game defect with green suite, first look for test that already covered case and compare inputs field by field.
- **Resource exclusion**: Verify every resource exclusion with two real acquisitions on target OS and require the second to fail. Inspect socket, file-sharing, and stdlib mutex defaults; configure lock fail-closed.
- **Verifiers that report zero work**: For every verifier asserting deleted/moved/repaired/restored, require an affected count greater than zero or an independent pre-check proving there was no work. Do not accept `{ok:true, count:0}` as proof on its own.

## A correct citation may not prove what is asked of it (step 3a)

An auditor cited an official vanilla test as proof that an API was synchronous: test measured a counter before and after call and asserted `== 1` on next statement. The citation was literal and exact. But sibling of that API, **documented as asynchronous**, passed the same assert a few lines down. Test did not discriminate, so it proved nothing about synchrony.

**Rule**: before accepting a third-party test, assert, or invariant as proof of property P, locate case that DOES NOT have P and verify that same assert fails. If negative control passes, evidence does not discriminate, it is compatible with conclusion, does not support it. It is same axis as "a gate that cannot be turned red is not a gate", applied to third-party evidence instead of own gates. Verifying that the citation exists is the first rung; verifying citation DISCRIMINATES is second, and is the one skipped.

## A control is calibrated to the worst real case, not a convenient one

Previous corollary covers control that does not discriminate. This one covers one that discriminates but in the wrong range.

A sweep of 18 files searched for a known defect, a rewritten line left alongside the old one, measuring common prefix `>= 55` characters between neighboring lines. It yielded **0**. It carried positive control, and control was planted on a pair sharing **77**: passed green. The only difficult real case shared **~32** before diverging, so probe would not have found it ever. It was fixed because external reviewer named it, not because sweep detected it.

Lowering threshold was not answer either: at 25 there were 27 hits, nearly all legitimate repetition. **Threshold was not problem; measured magnitude was.** The good probe measures *similarity* over neighbors of lines that change ADDED, defect only exists where something landed, and its control is planted in real cases.

**Rule**: a positive control answers "can it find something?", and that is not the question; the question is "can it find THIS?". Plant it in worst known real case. If there is none yet, declare up to what toughness coverage is demonstrated, "0 remaining, verified up to similarity 0.60", instead of saying "0 remaining" point-blank. And if moving threshold causes result to jump from 0 to dozens of false positives without passing through useful range, stop: you are measuring the wrong magnitude.

**Cheap signal**: if you wrote positive control and someone else found defect, check whether your control would have caught theirs.

## A control that inherits the instrument's convention is born blind

Previous two cover control that does not discriminate and one discriminating out of range. This one covers one that discriminates perfectly **inside the blind spot intended to be measured**.

A gate checked that proxies were rotated 180 degrees around vertical axis. It had negative control and was well thought out: generated a model rotated 180 degrees around a *horizontal* axis and required gate to flag it in red. It did. Gate GREEN on good artifact, negative RED, and result in game was **wrong**, weapons had rotated around horizontal.

Cause: control generator applied `R_new = Ry(180) * R_old`, multiplying from the LEFT, and function deriving frame returns axes as rows in world coordinates. Multiplying from left negates rows, meaning it rotates around proxy's **own axis**, not around world's. Measured: local Y axis of those proxies pointed to `(1.0, -0.001, 0.006)`, world's X. **The control used the same mistaken convention as the gate**, so it confirmed convention instead of testing it.

**Rule**: when what might be wrong is a CONVENTION (multiplication order, rows versus columns, local frame versus world, axis order, endianness, 0-based versus 1-based), control cannot be built with same code or same convention as instrument. It is built from outside: an artifact whose expected value is known via another means, a manual measurement, an external reference file, a visible asymmetrical marker, and compared against that. A control that shares gate apparatus only proves that apparatus is self-consistent.

**Cheap signal**: if control and instrument share function, module, or formula, it is not an independent control. And if gate comes out green and observable result comes out wrong, suspect convention before threshold.

## Repair-on-load constructors turn every reader into a writer

A store constructor that prunes, migrates, compacts, normalizes, or repairs while loading is not read-only. Every call site that constructs it can write the same file, even when the caller's help text or docstring says "read-only". Treat that claim as unverified until the constructor and its callees have been read.

**Step-1 caller census:**

1. Grep every construction of the store class, including tests and alternate entry points.
2. Classify each caller as intentional writer, required reader, or test. For each required reader, trace constructor side effects through the persistence choke point.
3. Check the lock's scope. `threading.RLock` excludes threads in one process; it does not serialize two processes writing the same file. A shared file needs an inter-process lock or a design that gives only one process write authority.
4. Look for readers that discard exactly the records the loader repairs or prunes. That is a mechanical signal that maintenance is an unwanted side effect, not part of the read.

**Read-only must be structural.** A read-only mode loads without repair or checkpointing, and the persistence choke point plus every public mutator must raise if a future caller attempts to write. Pin the contract with a file that contains material the normal loader would repair, then compare its bytes before and after the read-only operation; an unchanged mtime is not enough evidence.

**A pre-operation backup is not fail-closed merely because it uses `O_EXCL`.** The path `FileExistsError -> success` can reuse a stale, empty, or crash-truncated backup, and one fixed backup name protects only the first destructive operation. Use a fresh numbered slot per operation (`.bak`, `.bak.2`, ...), create it with `O_EXCL`, validate its bytes and size, never reuse it, and fail closed when the bounded slots are exhausted.

A permanent fail-closed state must also be observable. Whenever a repair or destructive operation can stop because no valid backup slot remains, require the existing diagnostic surface to emit a finding. Always ask: **how does a human learn that this brake is engaged?**

## Census the inventory before handing it to auditors; compare the deployed PBO with the source

1. A regex-generated inventory is closed with an independent census before auditors see it: the LFPowerGrid save/load-body table listed 11 files while 25 contained `ctx.Read` or `ctx.Write`, missing an entire hook family (`LFPG_OnStore*Device`, 10 classes). Auditors treat the handed table as complete.
2. Design note: "the deployed artifact is not the source" is checked in DayZ by extracting the PBO and comparing by content (EOL-normalized) against each candidate tag: a release tag differed from the published PBO in 51 of 144 scripts.
3. Do not count entities by searching class names in `storage_1\data\*.bin` (nor in `types.bin`): the positive control returns 0 matches in a world that does contain those classes. Count them in game.
