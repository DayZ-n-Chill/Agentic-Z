# When an in-game check is worth believing

What makes a check run in the game valid: which mod the run really loaded, what the PBO holds, why a command's own answer is not its effect, where a hang sits, how many samples a negative needs, and what the report must say. These rules apply to any in-game check, by hand or scripted.

Vanilla facts cite the file on `P:\`. The rest was measured in test sessions on a Windows machine and is not checked on `P:\`. Numeric thresholds on telemetry are in `telemetry-thresholds.md`; what makes a scripted test cell valid is in `test-cell-evidence.md`.

## Check which mod the run loaded

Before you credit a compile result or any verdict to the mod under test, read the `-mod=` and `-mission=` of that run in its RPT header. A launch that named another mod by mistake still boots, still loads a mission and still reports success; its missing compile errors then read as a fix. An in-game observation is worth whatever the `-mod=` line of its own run is worth.

- When a check reads process command lines through WMI and the host answers access denied, read the command line DayZ writes at the top of each RPT instead, and use `Get-Process` for the `DayZDiag_x64` processes.
- A log search that returns a `Module: World` line may have returned the client's: check the defines of the returned line (`SERVER` is only in the server's) before taking it for the server's.
- A build whose scripts did not load shows as the base class in place of the mod's class (a vehicle reads `CarScript`), and as a `Module: World; loaded N files` count lower than with the right PBO. Compare that count with a run without the mod.
- Hash the live server and client PBOs with SHA-256 after launch and at the end of the run when a verdict depends on exact bytes.

## Read the deployed PBO's file list, not the source tree

A build can pack stray scratch files, so assuming the PBO holds exactly the source tree misreads a compile verdict from the boot log.

- The PBO index is plain text near the start of the file. `grep -a "scripts\\\\" <mod>.pbo` finds the names but prints whole chunks of binary, not one name per line, so it is not a file list.
- To read the index, parse the header: `skills/dayz-build-pbo/pbo_entries.py` has no command line, so call `read_pbo(path).entries` from Python.
- Keep experiments out of the packed tree; a rebuild packs any scratch file still in it. `/dayz-build-pbo` empties `P:\temp\<ModName>` on every build, so AddonBuilder's incremental `-temp` sync cannot serve stale source there.

The index says what is packed, never why a compile failed.

## Read the effect, never the answer

A command's `ok` is not its result. The same call can answer the same way and do opposite things: a delete by an unknown id and a delete by a real id can both answer success, and only a count of removed objects tells them apart. For every step, read the state it was meant to change.

| What you want to know | Read |
|---|---|
| Did the object land where asked? | Its position some seconds later, against the requested one and the ground height there |
| Did a delete remove anything? | A search for the object afterwards |
| Did the player respawn? | The player's position before and after |
| Did a wait end on its condition? | The condition itself, not the end of the wait |

## Before you blame the mod

1. Check the stimulus first. Confirm the input reached the object before you blame the mod for a FAIL; run a control that differs in one thing, or a manual test, to tell a test defect from a mod defect.
2. Read the client log before you record a FAIL. Many mod events are written by the client, not the server, and a verdict built only from the server log can say FAIL while the client log shows every operation working. `/dayz-logwatch --dir <client profile folder> --since 5` reads it with triage; without `--since` it reads only lines written after the watch starts.
3. A dead peer explains the errors after it. At the first odd error on the client side, check the client's process id and the end of its RPT. If the client died, collect the minidump and stop diagnosing the errors that follow.
4. One reproduction per layer of defence. When several checks guard the same failure, build one reproduction per check that reaches that check, and read each one's own signal. A combined "it does not fail" does not prove they all work.
5. A check that cannot go red proves nothing. Pair every positive with a negative control that must fail, such as an excluded target or an invented class name.

## Place a server hang from the log ends first

A boot that never finishes (the RPT frozen, the process alive at low CPU) is a verdict with no location.

1. Read the end of both logs. The RPT often ends in world streaming warnings; the mod's own markers and init lines are in `script*.log`. The gap between the last printed stage and the first missing one is a candidate, not a location: check that the markers come in that order on that path, belong to the same flow and this run, and are visible. A marker printed from a `CallLater` callback is not in the same flow as the init stages. A missing stage proves no progress was seen, not where the server spins.
2. Check the loop structure of the candidate region in source before you suspect it, to clear the cheap suspects.
3. A regression needs the same scenario with one variable changed (the revision, or just the newest change reverted). Toggling paths inside one revision only narrows the place.

Diag writes the RPT through a buffer of about 52 KB, so a frozen RPT does not tell a dead process from an unflushed buffer. Compare the process CPU over 30 seconds with `Get-Process` twice: flat means stopped, growing means alive.

## A negative from one sample is not a negative

1. Count experiments, not captures. A repeated capture of the same state is still one sample.
2. List everything that changed between the working case and the failing one. With two or more, the negative names none of them until each is tested on its own.
3. Narrowing a finding to one cause is one more claim. If that cause is wrong, the caution points away from the real mechanism.

Example: a material override written again on a worn garment did not change it, and the finding was filed as "at health level 4 a new override is never rendered", backed by two captures minutes apart. It was false. The two captures ruled out a drawing glitch, not a sample of one, and two things had changed between the write that worked and the one that did not: the health level (0 to 4) and the moment of the write (right after a state change, against an arbitrary moment).

Before you file a repeated or `ERR` log line as test noise, write in one sentence what it would mean if true. If that sentence describes damage (a command running again, two entities sharing one id), it is signal.

## What a person sees better

When a person is at the machine, their own check with an admin tool is faster and judges the whole scene at a glance; an automated check wins when nobody is there. What a person cannot measure by eye (telemetry, raycasts, exact placement, repeatable series) still goes through a scripted check. When the render is ambiguous, a person's eye outranks a capture: on a car with faint captures, the user caught a proxy misalignment that was about to be signed as PASS.

## The report

- A criteria table: criterion, PASS, FAIL or INFO, and the evidence for each.
- The captures and the raw telemetry and raycast readings, and one overall verdict.
- A manual test section listing what was not covered: shooting, reloading, interactive inventory, vanilla menus, continuous actions (`actions-doors-and-inventory.md`), doors that need hand input.
- The `-mod=` line of the run, so the verdict can be tied to it.

## Related files

| Question | File |
|---|---|
| Spawn flags, coordinates, posing a test object, killing and respawning the player | `spawning-and-placement.md` |
| Raycasts, collision controls, walk-into and stand-on tests | `raycasts-and-collision.md` |
| Captures, black or flat frames, scripted cameras, a raised weapon, UI pixels | `screenshots-and-cameras.md` |
| Actions, doors, inventory moves, a mission driver | `actions-doors-and-inventory.md` |
| Driving, conditioning and deleting a car | `vehicle-in-game-facts.md` |
| The vehicle acceptance checks and their fixes | `vehicle-acceptance-checks.md` |
| Thresholds on telemetry | `telemetry-thresholds.md` |
| Gates that can fail, teardown, what makes a scripted run valid | `test-cell-evidence.md` |
