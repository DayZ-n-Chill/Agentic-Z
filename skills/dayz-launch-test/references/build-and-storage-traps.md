# Build and storage traps

How a build, deploy and test cycle goes green without testing the change: backups packed into the PBO, a locked PBO that is never replaced, a build check that only tests that a file exists, a signature written over the old PBO, and mission storage written by a different mod set, above all with or without Community Framework.

In this repo the build step is `/dayz-build-pbo`, the launch is `/dayz-launch-test`, the stop is `/dayz-stop-test`, the logs are `/dayz-logwatch` and the verdict is `/dayz-gate`. The orchestrator script `../scripts/dayz-test.ps1` names the same steps `-Build` and `-Mode all`; its mod source `P:\<Mod>` is the junction to `workspace/<ModName>/`, and its `<Mod>_dev\_server\profiles` and `<Mod>_dev\_client\profiles` are `.server/<instance>/Profiles` and `.server/!ClientDiagLogs` here.

The tool behaviour here (AddonBuilder, DSSignFile, DSCheckSignatures, Community Framework) was measured on a Windows test machine and is not checked on `P:\`. Vanilla script facts cite the file.

## Storage belongs to the mod set that wrote it

Community Framework (CF) writes its own `modstorage` data into every saved entity, so a mission's `storage_1` only loads cleanly under the mod set that wrote it. The `dayzOffline.*` missions in the DayZ Server folder are shared by every project on the machine, which is how the sets get mixed.

**Adding CF to storage written without it crashes the server.** The server starts, loads the mission and dies reading the saved entities. The server `crash_*.log` shows:

```text
SCRIPT (E): Virtual Machine Exception
Reason: Failed to read modstorage for entity Type=Rangefinder, Position=<...>
Class: 'CF_ModStorageObject<ItemBase>'
  JM/CF/.../modstorage\cf_modstorageobject.c:142  Function OnStoreLoad_CF
  .../mpmissions/dayzOffline.chernarusplus/init.c:6  Function main
```

The entity named is vanilla and random (here a `Rangefinder`), so the message points away from the mod you just added. The client does not fail: it loads (`PlayerBase OnStoreLoad SUCCESS`) and closes cleanly after the server, which makes it look like a client problem.

**Removing CF from storage written with it floods the log and damages the storage.** A server without CF on a `storage_1` saved by a server with CF throws `!!! Scripted variables corrupted upon "<entity>"` for every saved entity, 15,688 in about 3 minutes in one run, and can die partway through writing. The entities it rewrites lose their CF data, so the next server with CF crashes on them as above.

So there is no third stable state: once a server with CF saves, the storage carries CF data. When you launch on a shared mission, either `-mod=` includes CF or you rotate `storage_1` first. More generally, rotate before any launch whose `-mod=` differs from the last run on that mission; adding one mod already counts. On one shared mission folder 12 rotations from at least 5 projects piled up within 40 days, so check this before every launch rather than when something looks wrong. The server's RPT names the storage it uses on the line `[StorageDirs] :: Selected storage directory:`.

### Rotating storage

With the processes stopped, rename it with a date and a reason and let the server create a new one:

```powershell
$m = "<mission>"
Rename-Item -LiteralPath "$m\storage_1" -NewName "storage_1_corrupt-modstorage-$(Get-Date -f yyyyMMdd)_<project>"
```

A rename is reversible, but booting with CF on that storage crashes again: what you keep is evidence, not a state to return to. Tell the user before you rotate, because the world and the character of that mission reset.

A check you ruled out holds only for the plan you ruled it out under. In one run the plan was a fresh private copy of the mission, so "clean mission, no storage" was true; then `dayz_test_run` refused the absolute path (dayz-mcp accepts only the aliases `chernarus`, `livonia` and `sakhal` for `mission`), the run fell back to the shared mission, and nobody checked the storage again. When the plan changes, check every caveat again.

## Clean storage before a measurement boot

Saved vehicles and other persistent entities run `EEInit` again on the next boot (`P:\scripts\3_game\entities\entityai.c:905`). Anything armed there, a test `CallLater`, a tuning mode driven by a JSON file, a countdown, fires again on every saved instance at once. Two helicopters saved the day before re-armed a test mode at boot and flew off by themselves after 60 seconds, adding two runs of data that did not come from the run being measured.

Before every boot meant for measurement (test cells, tuning runs, telemetry), rotate `storage_1` to `storage_1.bak_<date>_<reason>`, not only after an unclean stop. The rename also clears test entities piled up by earlier sessions. In a dayz-mcp run this happens before the session lease is taken (`mcp/README.md`, "The loop").

## Persistence brings the subject back as the last run left it

An experiment that measures entity state (health, wetness, quantity, temperature) cannot trust the spawn loadout. A character came back wearing a garment at `wetlevel=4 hplevel=2`, exactly where the previous run left it, so the control started past the threshold it was meant to cross and would have reported "control does not fire".

Normalize the subject before measuring (`SetWet(0)`, `P:\scripts\4_world\entities\itembase.c:3688`; `SetHealthLevel(0)`, `P:\scripts\3_game\entities\object.c:1087`; whatever applies) and log it. If a client part depends on that state, wait for the condition, not a timer: normalizing is itself a state change that can clobber what you were about to measure.

## Backups packed into the PBO

A `<file>.c.bak_*` beside the `.c` it backs up is packed by any build that copies the tree as it is, such as `dayz-test.ps1 -Build -PackOnly`. Enforce compiles only `*.c`, so the game ignores it, but the PBO grows (827,593 bytes with 29 backups inside against 115,609 without, on a helicopter mod) and a text search of the PBO finds an old anchor in a backup instead of the active file. `/dayz-build-pbo` leaves `*.bak` out through `exclude.lst`. Keep backups outside the mod source, and when you check a PBO by text, count matches instead of testing for one.

## A locked PBO is signed and reported as deployed

A running client or server, or a live `dayz_test_run`, keeps the PBO locked. Rebuilding with AddonBuilder then prints `[ERROR]: Build failed`, and a chained `DSSignFile` still exits 0: it signed the previous PBO. A script that chains the two prints a sign result of 0 that looks like a confirmed deploy.

Stop the run before you rebuild, and judge the result by the PBO's file table against the source sizes, never by exit codes:

```text
scripts\4_World\MyMod_Probe.c    3579     <- on disk: 3579
scripts\5_Mission\MyMod_Driver.c 4756     <- on disk: 4756
```

This is the build rule (the verdict is the file table; AddonBuilder exits 0 on some error paths, `skills/dayz-build-pbo/references/addonbuilder-rules.md`) carried over to signing.

### What `dayz-test.ps1` checks, and what it misses

After AddonBuilder returns, `Invoke-Build` in `../scripts/dayz-test.ps1` stops on `Build failed` in the output, checks that the PBO exists and is newer than the build start, and tests the deployed PBO for exclusive write before it builds. It does not compare the PBO's entries with the source, and it only warns when `Build Successful` is missing. Older copies checked only the exit code, `Test-Path` and a size above 4096 bytes, which all pass on the old PBO when a running game holds it, so they printed `[ok] deployed` beside `[ERROR]: Build failed`. If you see both lines in one run, the PBO under test is the old one.

When `<WorkDrive>\Mods` is missing, `Invoke-Build` creates it with `New-Item -Force`. The current script runs its preflight first and creates the `P:\Mods` junction, but when `Mods` already exists as a plain folder it only warns, and the PBO lands where the engine never reads (measured: `exit=0; Mods created=True; junction=False`). `/dayz-preflight` reports a plain `P:\Mods` folder.

`dayz-test.ps1 -Build` also passes no `-include` list, so a mod with both models and scripts can lose its `.c` files. Build with `/dayz-build-pbo`, which passes `include.lst` and checks the entries afterwards (why: `skills/dayz-build-pbo/references/post-build-gates.md`, "`-include` is not the final PBO manifest"), launch without `-Build`, and stop the run before you rebuild.

## Before you spend a boot

- **Binarize first.** Every candidate `.p3d` needs a binarize pass before it goes into a PBO, even when final packing uses `-packonly`: packonly keeps the MLOD but does not make the engine accept a model that binarize rejects. Group the models of a change and run this once before the build; the census after the build still runs and tests something else.
- **Prove the PBO holds the source you are reading.** Unpack the deployed PBO to a scratch folder with an extractor that expands compressed entries correctly (check it against a known PBO first), hash each file the change depends on and its source file with SHA-256, and require equal hashes. A recent PBO modified time says nothing about the files inside. If they differ, rebuild before diagnosing logic. This complements the source probe in `windows-build-and-mount.md`.
- **Guard the deploy target, not the whole machine.** On a shared machine "no DayZ process at all" is too broad. Before you replace a PBO, require that no live process loads the target mod (read each `CommandLine` through `Win32_Process`; the executable name is not enough) and that the PBO opens with `FileShare.None`. Record its hash just before copying and check the published hash after. If either condition fails, do not deploy; if both pass, leave other sessions' processes alone.

## A signature check that cannot fail

`DSCheckSignatures` does not check every byte of a PBO, nor the PBO's SHA-1 trailer against its content (measured with `DSSignFile`'s default v3 signature on a quad bike mod release). One byte changed inside a `_co.paa` texture entry, with the trailer left as it was, still answered `Signature ... is OK`. Two controls did fail with `is wrong`: the previous build's PBO beside the new `.bisign`, and the new PBO with one byte of a `.c` entry changed and the trailer recomputed, which is what any repacker writes.

Build the negative control the way a packer would, or from another build; a raw byte flip proves nothing. Another build's PBO fails only when the two builds differ in an entry the signature covers: a release candidate that differed from the previous release only in one `.p3d` entry and the trailer answered `is OK` with the old PBO beside its new `.bisign`, while its `.c` byte control answered `is wrong`. For a change that only touches models or textures, the `.c` byte control is the one that can fail.
