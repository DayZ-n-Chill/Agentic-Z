# Build and storage traps that make a test run meaningless

Measured ways a build, deploy and test cycle goes green without testing the change: backups packed into the PBO, a locked PBO that is never replaced, a post-build check that only tests existence, `DSSignFile` signing the old PBO, and mission storage (`storage_1`) written by a different mod set, above all with or without Community Framework.

How the pieces map to this repo: the build step (`dayz-test.ps1 -Build`, `Invoke-Build`) is `/dayz-build-pbo`; launching server and client (`-Mode all`) is `/dayz-launch-test`; stopping is `/dayz-stop-test`; reading the logs is `/dayz-logwatch`; the pass or fail verdict is `/dayz-gate`. The mod source that the text calls `P:\<Mod>` is the junction to `workspace/<ModName>/`, and the profile folders it calls `<Mod>_dev\_server\profiles` and `<Mod>_dev\_client\profiles` are `.server/<instance>/Profiles` and `.server/!ClientDiagLogs` here.

Terms used below: "this box" and "this install" in dated findings mean the Windows test machine the measurement was taken on, not yours. `[EXACT]` marks a flag, path or behaviour that was verified in a real run; `[DESIGN]` marks something plausible that was not verified, so check it in game before relying on it.

These are measured results and tool behaviour (AddonBuilder, FileBank, DSSignFile, DSCheckSignatures, Community Framework). They are not yet checked on `P:\`.

## Backups (`.bak_*`) next to the scripts inflate the PBO and break a text check

A `<file>.c.bak_*` left beside the `.c` it backs up is packed by any build that copies the tree as it is, such as `dayz-test.ps1 -Build -PackOnly`. The game ignores it (Enforce compiles only `*.c`), but the PBO grows (measured on a helicopter mod: 827,593 bytes with 29 backups inside against 115,609 bytes without them) and a text search of the PBO finds an old anchor in the backup instead of the active file. `/dayz-build-pbo` leaves `*.bak` out through `exclude.lst`. Keep backups outside the mod source, and when you check a PBO by text, count matches instead of testing for one.

## Clean storage before any measurement boot - persisted entities re-fire EEInit

Vehicles (and other persistent entities) saved in the mission's `storage_1` run their `EEInit` again on the next boot. Any logic armed there - a test `CallLater`, a JSON-driven spike/tuning mode, a countdown - fires again on every persisted instance at once. Real case (2026-07-11): two helicopters from the day before re-armed their W0 spike at boot and flew off on their own after 60 s (two phantom CSV pairs contaminating the corpus, so the data no longer came from the one run being measured; the user even saw them fly with no explanation).

Rule: before every boot meant for measurement (cells, spikes, telemetry), the mission storage must be clean - rename `storage_1` -> `storage_1.bak_<date>_<reason>` (reversible), not only after a dirty kill. The current SOP only covers the dirty kill / stream-damage case (see the symptom table in `troubleshooting.md`). The rename also purges test entities accumulated from earlier sessions. Cross-ref `references/mcp/README.md` ("The loop": step 2 takes the session lease, step 8 releases it and stops the run).

## Introducing CF on a mission with persistence written without CF crashes the server

If a project adds **Community Framework** (and with it Dabs/VPP) to a mission whose `storage_*` was
written in runs **without** CF, the server starts, loads the mission and **dies** when it reads the
persisted entities. Exact signature (measured 2026-08-02, server `crash_*.log`):

```
SCRIPT (E): Virtual Machine Exception
Reason: Failed to read modstorage for entity Type=Rangefinder, Position=<...>
Class: 'CF_ModStorageObject<ItemBase>'
  JM/CF/.../modstorage\cf_modstorageobject.c:142  Function OnStoreLoad_CF
  .../mpmissions/dayzOffline.chernarusplus/init.c:6  Function main
```

**What is most misleading**: the cited entity is **vanilla and random** (here a `Rangefinder`), so
the message points anywhere except the mod you just added. And the client does not fail: it
loads normally (`PlayerBase OnStoreLoad SUCCESS`) and closes cleanly after the server, which reinforces
the mistaken reading of a client problem.

**Cause**: DayZServer's `dayzOffline.*` missions are shared between projects. A project running
without CF persists entities without CF's `modstorage` data; the next one that does include CF
reads them and crashes.

**Remedy** (the convention already used in the mission folder itself, with 4 occurrences:
`storage_1_corrupt-modstorage-20260720 / 0728 / 0729 / 0802`): with the processes stopped, **rename**
`storage_1` → `storage_1_corrupt-modstorage-<YYYYMMDD>` and let the server regenerate it. It is a rename, not
a deletion, so it is reversible - but **starting again with CF on that storage crashes again**:
what is preserved is evidence, not a state you can return to with CF enabled.

**Tell the user before rotating**: the world and the character are reset.

Cross-ref "Clean storage before any measurement boot" above (the same action, renaming `storage_1`, for a different reason: persisted
entities that re-fire `EEInit`). Combined rule: **any change in the mod set that
changes who writes `modstorage` requires clean storage**, the same as a measurement boot.

### The trap works in both directions, and the rule is decided at launch

The reverse direction also bites, and faster: a server **without** CF starting on a
`storage_1` written **with** CF enters a storm of Virtual Machine Exceptions - `!!! Scripted variables corrupted upon
"<entity>"` for each persisted entity (measured: **15,688 in about 3 min**, plain `-mod=@DayZ_MCP`
on a storage freshly saved by a server with CF) - and can die partway through writing,
leaving the storage worse: rewritten entities lose their CF modstorage, and the next
server that does include CF crashes with the signature above. So the crossings chain together:
a server without CF rewrites the storage, a server with CF then crashes on it, and the storage has to be rotated.

**Rule when launching on a shared mission**: either `-mod=` includes CF, or `storage_1` is rotated
before starting. There is no third stable option: the storage carries CF data as soon as a
server with CF saves once. To rotate, rename it with a reason
(`storage_1.bak-<YYYYMMDD>-<HHMM>-<reason>`, with the processes stopped; occurrences on 2026-08-21:
`-1605-modstorage-corrupt`, `-1610-cfless-storm`). The server's own RPT says which storage needs rotating,
on the line `[StorageDirs] :: Selected storage directory:`.

## The `modstorage` rule is skipped often: check it before every launch

The section "Introducing CF on a mission with persistence written without CF crashes the server" is correct and **has failed again**. Counted on 2026-08-29 in
the shared mission folder `DayZServer\mpmissions\dayzOffline.chernarusplus`:

    12 storage_1*corrupt-modstorage* folders, from 2026-07-20 to 2026-08-29,
    from at least 5 different projects.

12 occurrences in 40 days. A note skipped 12 times is not fixed by reading it more
carefully the 13th time: the precondition can be checked by a script, and it is being checked by hand.

**Operational rule: persistence belongs to the mod set that wrote it.** Before launching
with a `-mod=` that differs from the previous run on the same mission, rotate. The rule is not "if
you suspect a problem": it applies **whenever the list changes**, and adding one mod already changes it.

    # with processes stopped
    $m = "<mission>"
    Rename-Item -LiteralPath "$m\storage_1" -NewName "storage_1_corrupt-modstorage-$(Get-Date -f yyyyMMdd)_<project>"

Rename, not deletion: it is reversible. But starting again with CF on that storage crashes again,
so what is preserved is evidence, not a state you can return to.

**Warning to give before rotating**: the world and character of that mission are reset.

And the process failure that let it slip this time, which is the one to recognize:
**the precondition was checked against the first plan, and then the plan changed.** The plan was a new,
private copy of the mission, so "clean mission, no storage" was true when the run was dispatched. Then
the tool rejected the absolute path (`dayz_test_run` validates the `mission` field against
`_MISSION_ALIASES` in dayz-mcp's `dayz_test_tool.py` and only accepts `chernarus|livonia|sakhal`),
which pushed the run onto the shared mission. The precondition had been ruled out under the old plan, and no one checked it again under the new one.

**A precondition you ruled out holds only for the plan you ruled it out under: if the plan changes,
check it again.** This applies to every caveat in this skill, not just this one.

## Test-cycle rules

### A mixed mod (models and scripts) needs a build that passes `-include`

`dayz-test.ps1 -Build` passes no `-include` list, so for a mod with models and scripts its PBO can lose the `.c` files. Build with `/dayz-build-pbo`, which passes `include.lst` and checks the entries afterwards. Why `-include` filters only part of what AddonBuilder packs: `skills/dayz-build-pbo/references/post-build-gates.md`, "`-include` is not the final PBO manifest".

### Binarize before spending a boot

Every candidate `.p3d` needs a binarize PASS verdict before entering a PBO, even if
final packing uses `-packonly`: packonly preserves MLOD, but does not make engine accept a
model that binarize rejects. Group models in the change and pay this gate once before build;
post-build census remains mandatory and tests another boundary.

### Offline identity between source and deployed PBO

Before planning by `path:line` citations or spending an in-game cycle, test what bytes the
game will compile:

1. Extract deployed PBO to a scratch with an extractor that correctly expands `Cprs`
   entries; validate extractor first against a known baseline.
2. Compute SHA-256 of file inside PBO and of source file cited by plan.
3. Require equal hashes for every file the change depends on. A recent PBO modified time says
   nothing about the files inside it.

If hashes differ, plan is citing a tree different from runtime. Rebuild and repeat the
gate before diagnosing logic. This offline check is the cheap discriminant complementing
the `srcprobe` discriminator in `windows-launch-cycle.md`.

### Deploy guard protects destination, does not freeze entire box

On a shared box, "zero DayZ processes" is too broad. Before replacing a PBO require
the two conditions protecting that destination:

1. No live process references target mod in its `CommandLine`/modline, measured with
   `Win32_Process`; executable name is not enough.
2. Target PBO allows exclusive opening with `FileShare.None`.

Record baseline hash just before copying and verify published hash after. If either
condition fails, do not deploy. If both pass, do not close processes from other lanes loading other
mods.

## Two traps of the build-deploy-test cycle that make a useless run green

Both measured on 2026-08-31 closing an engine gate. Neither gives an error; both let
you draw conclusions from a run that did not test what you think.

### 1. `DSSignFile` returns 0 after a failed build - and signs the OLD PBO

`dayz_test_run` (and any live client/server) leaves the PBO **locked**. Rebuilding with
AddonBuilder while the run is up gives `[ERROR]: Build failed`, and if the script chains
signing, `DSSignFile` exits with **`EXIT=0`** quite happily: it has signed the previous binary.

Chained in a `.ps1`, the result is a `SIGN=0` that seems to confirm deployment.

**Stop the run before rebuilding**, and verify the result by **the PBO table against
source size**, never by exit codes:

```
scripts\4_World\MyMod_Probe.c    3579     <- and on disk: 3579
scripts\5_Mission\MyMod_Driver.c 4756     <- and on disk: 4756
```

It is the same rule as for the build itself (the verdict of a build is the PBO
file table, not the exit code; `skills/dayz-build-pbo/references/addonbuilder-rules.md` records that AddonBuilder
exits 0 on some error paths), extended to signing: **the exit code of `DSSignFile` says
nothing about whether the build got in.**

### 2. Persistence returns the subject as the previous run left it

An experiment measuring entity state (health, wetness, quantity, temperature) **cannot
rely on spawn loadout**. Measured: character returned with garment at `wetlevel=4
hplevel=2`, exactly where previous run had left it, so control for new run
started **already past the threshold it had to cross** - and would have given "control does not
fire" falsely.

The probe **normalizes the subject** before measuring anything (`SetWet(0)`, `SetHealthLevel(0)`, whatever
applies) and records it in log. And if there is a client part depending on that state, it binds to
**the condition, not a timer**: wait to observe subject already normalized, because
normalization itself is a state change that can clobber what you were about to measure.

### 3. A signature negative control that cannot fail

[EXACT] `DSCheckSignatures` does not check every byte of a PBO,
nor the PBO's own SHA-1 trailer against its content. Measured on a quad-bike mod release
(the default v3 signature of `DSSignFile`, 2026-10-26): one byte changed inside
a `_co.paa` texture entry, with the trailer left as it was, still answered
`Signature ... is OK`. Two controls did fail with `is wrong`: the previous build's PBO next
to the new `.bisign`, and the new PBO with one byte of a `.c` entry changed and the trailer
recomputed, which is what any repacker writes. Build the negative control the way a packer
would, or from another PBO; a raw byte flip proves nothing about the signature. Another build's
PBO only fails when the two builds differ in an entry the signature covers: a second mod's release candidate
(2026-11-05), which differed from its previous release only in one `.p3d` entry (its bytes and
timestamp) and the trailer, answered `is OK` with the previous release's PBO next to its new `.bisign`, while
its `.c`-byte control answered `is wrong`. For a change that only touches models or textures, the
`.c`-byte control is the one that can fail.

## The build gate of `dayz-test.ps1` checks less than `/dayz-build-pbo`

After AddonBuilder returns, `Invoke-Build` in `scripts/dayz-test.ps1` stops on `Build failed` in AddonBuilder's output, checks that the PBO exists and is newer than the build start, and probes the deployed PBO for exclusive write before it builds. It does not compare the PBO's entries with the source, and when `Build Successful` is missing it only warns. Older copies checked only the exit code, `Test-Path` and a size above 4096 bytes: all three pass on the previous PBO when a running game holds it locked, so the script printed `[ok] deployed` next to AddonBuilder's `[ERROR]: Build failed`. If those two lines appear in one run, the PBO under test is the old one.

`/dayz-build-pbo` runs the full gate (result code from AddonBuilder's log, a fresh PBO, every staged `.c` and `.p3d` in the entry table); why each level matters is in `skills/dayz-build-pbo/references/post-build-gates.md`. So build with `/dayz-build-pbo` and launch without `-Build`, and stop the run before you rebuild.

One more mask on the script's route: when `<WorkDrive>\Mods` is missing, `Invoke-Build` creates the destination with `New-Item -Force`. The current script runs its preflight first and creates the `P:\Mods` junction, but when `Mods` already exists as a plain folder it only warns, and the PBO lands in a folder the engine never reads (measured: `exit=0; Mods created=True; junction=False`). `/dayz-preflight` reports a plain `P:\Mods` folder.
