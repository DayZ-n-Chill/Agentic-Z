# Test cell gates and evidence

What makes a scripted test's verdict worth believing: gates that can actually fail, a teardown that keeps the logs, the checks a run must pass before it counts, and the two silent ways an in-game observation is spoiled (a missing mod on the `-mod=` line, and an unfocused client). Setting up the cell is in `automated-cells.md`.

Vanilla script facts cite the file on `P:\`. The rest was measured on a Windows test machine with test mods and the third-party dayz-mcp tool, and is not checked on `P:\`.

## A gate must be able to go red

A wrapper is only worth its gates, and two faults make a gate unable to fail while it keeps printing green. Neither shows when you read the script in good faith.

**A flag that turns your regex into a literal.** This looks like a compile gate:

```powershell
Select-String -Path $slog.FullName -Pattern "Compile error|Can't compile" -SimpleMatch
```

`-SimpleMatch` searches for the whole string as written, pipe included, which never occurs in a log. Against a test log holding both real errors it finds 0 matches with `-SimpleMatch` and 2 without. The same trap comes from `-Raw`, `-Literal*`, `[Regex]::Escape` on a pattern meant as a regex, and mixing up `-match` and `-like`.

**A pattern that matches healthy boots.** `not closed`, added for Enforce's `CParser: quoted string not closed`, also matches a line Community Framework writes after every server that was not shut down cleanly, which is every server a tool stopped: `File "$mission:storage_1/communityframework/modstorageplayers.bin" was not closed. Always shut down the server gracefully to prevent data loss.` Anchor the pattern on `CParser`, or require `CParser` on the same line. A gate that goes red on good boots soon gets ignored.

**An analyzer whose input does not depend on the run.** A hardcoded log path makes every later comparison re-read the same old run and report "no change". A script that prints statistics and never sets an exit code is a report, not a gate.

Before you trust a gate you did not write:

1. Feed it a case that must fail and watch it fail. If you have never seen it red, you do not know it is a gate.
2. Grep the wrapper for `-SimpleMatch`, `-Raw` or `-Literal*` beside any pattern holding `|`, `.`, `*`, `\` or `(`.
3. Take inputs as parameters, and check that the analysed file is newer than the run that made it.
4. Exit non-zero on failure, and check that the caller passes the code on.

Fix the gates before a measurement series, not after: greens from a gate that cannot fail mean nothing, and you cannot tell later which were real.

## Teardown copies the logs before it kills

Killing the client at once loses its last unflushed log buffer. In one run the client log stopped about 56 seconds before the moment the server recorded the player getting out, so the window that mattered existed only in the discarded buffer. The order is:

1. Copy the script logs while the process is still alive.
2. Check that the copy holds the stretch that matters: count the probe lines you expected, not just a non-empty file.
3. Only then `Stop-Process`.

There is no second copy of an unflushed buffer, so a teardown that kills first cannot be repaired.

## Read the real `Print` payload first

A string variable reaches the script log in this form:

```text
SCRIPT       : string <var> = '<payload>'
```

The closing quote sticks to the last field. Take what lies between `= '` and the last quote first, then split out fields and numbers. A log gate always carries fixtures copied from a real log as well as made-up cases, plus fixtures with a cut wrapper; a self-test that never read a real line only checks the parser you imagined.

## What makes a run valid

A cell emits `PASS` only when it shows it booted in the planned mode, covered the whole transition, and produced the evidence the verdict reads.

1. **Preflight by mechanism and mode.** Write each guard as the mechanism it protects and the modes it affects, and code that branch: a guard that only matters with a client aborts with a client and only warns in a no-client run, with no manual bypass. On a machine with several stacks, a cell with a client is not isolated from the keyboard: list the other `DayZDiag` processes with their process ids, mods and ports, record the focus risk, and use a test only DIAG guard that refuses human actions that would change state while the script runs. If port 2302 belongs to another session, pick another free port. If you cannot show isolation, the result is `SETUP_FAIL`.
2. **Boot identity.** In a series that relaunches the client, wait 60 seconds between one shutdown and the next start; a native crash during that start is `SETUP_FAIL`, not a regression. A single isolated run needs no cooldown. When packing evidence, never pick a file by its modified time: dayz-mcp names its files in UTC while RPT names and modified times use local time. Match the boot id or an internal marker against the time recorded for the incident, and reject the bundle if the expected boot markers are missing.
3. **The whole transition, compiled on both sides.** Write each transition as four steps: the input, the state you can observe, the exit and the state after the exit, and drive all four from the script. A test that only enters has not covered the transition. Search the script logs of server and client for `Compile error` and `Can't compile` before waiting for any marker: a dead client, a live server and `Can't compile` mean code only the client compiles is broken, not a timeout. Offline lint cannot prove `private` or `protected` visibility.
4. **A shutdown that fits the measurement.** Copying logs before the kill keeps what was written, but proves nothing about results written on exit. For leak reports, flushes, destructors and final hooks, ask for a graceful shutdown, wait for a marker that the hook ran, then collect. A forced kill makes every exit metric `SETUP_FAIL`. "The problem did not appear" is never `PASS` if the check never ran.

## An observation is worth its `-mod=` line

`managed-launcher.md` reads `-mod=` to learn whose machine it is. Here you read it to learn whether an observation counts, before you act on it.

The failure is silent: a missing mod gives no error, the game starts and the observation looks normal. On two quad bike mods tested together, only one of ten runs loaded the animation mod `@SurvivorAnims`. Each mod's `GetAnimInstance` override returns its own instance only when `CfgPatches SurvivorAnims` exists (checked with `ConfigIsExisting`, `P:\scripts\3_game\global\game.c:612`) and otherwise falls back to `VehicleAnimInstances.V3S` (`P:\scripts\4_world\entities\vehicles\vehicleaniminstances.c:4`), the truck pose on a quad. With that pose the driver's camera is in the wrong place, which changes what is seen from the seat and which LOD the engine picks. A LOD fix made on those runs had to be withdrawn.

When an in-game observation will decide code or geometry:

1. Find that run's server and client RPTs and read their first `-mod=` line.
2. Check that every mod the behaviour depends on is there. The three most often missed: an animation mod that a `GetAnimInstance` or other hook asks for with `ConfigIsExisting` (without it, pose and camera differ); a framework such as Community Framework that writes per entity storage; and the content mod whose objects must be seen.
3. If one is missing, reclassify the observation rather than discarding it. What does not depend on pose or LOD still holds (a mirrored texture is mirrored from any angle); what depends on where the eye is does not.
4. With every mod present, also read whether the run rendered textured and, for anything that depends on the eye, where the eye was. Both changed between runs with the same command line (`window-capture-pitfalls.md`, "Runs that never load their textures", and `vehicle-first-person-eye.md`).

A mod folder with a space, such as `@Survivor Animations`, splits the command line; the RPT shows it cut at `-mod=...;P:\Mods\@Survivor`. Link it through a junction with no space, such as `@SurvivorAnims`.

To check a whole day's runs at once:

```bash
for f in _server/profiles/*.RPT _client/profiles/*.RPT; do
  m=$(grep -m1 -oE '\-mod=[^ ]*' "$f")
  printf "%-52s %s\n" "$(basename $f)" "$m"
done
```

## An unfocused client runs at about 20 fps

Measured on a helicopter mod's bench by switching focus on purpose, with a windowed DayZDiag client and server on one machine:

- With its window in front the client ran at 25.0 ms a frame (40 fps); without focus at 51 to 52 ms (about 20 fps). Switching focus inside one cell moved the median between 26 and 53 ms.
- It is not shared GPU or CPU load: none of 10 slow cells coincided with local model inference, and pinning the client to 2 cores at high priority left 4 of 4 cells at 51 to 52 ms. Slow frames form a tight ceiling (91 percent within 3 ms), not a contention tail.
- The helicopter's idle bounce followed focus: still in 6 of 6 runs with focus held, bouncing without it. Every client side measurement (presentation, owner physics, vehicle traces) inherits the focus state.
- On a machine with several sessions, other applications take the foreground every few seconds (chat clients, editors, another session's AddonBuilder, Explorer).

Rules:

1. A bench that measures the client keeps it in the foreground for the whole run (reasserting every 0.25 seconds is enough) and logs once a second whether it held.
2. If the design needs focus elsewhere, park it on a visible window of a process you own (a small Tk window works). Two targets fail: the DayZ server console (Windows hands focus straight back to the client) and `Start-Process notepad.exe` on Windows 11 (the returned process id is a launcher that exits at once; the window lives in another process).
3. Archived runs with random focus mix two frame regimes: before comparing variants, split them by frame time or repeat with focus held.
