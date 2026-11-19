# Evidence and controls

How to tell real evidence from evidence that only looks real during a data audit: the deployed build against the source, which code path wrote a log line, controls that can actually fail, inventories that are complete, and checks that report no work. Open it in steps 1 and 3 of `deep-audit.md`, and whenever a check comes back clean.

These are audit rules. The DayZ facts in the last section were measured in game and cannot be checked on `P:\`.

## Before looking for a cause in the source

When the audit starts from a bug on a live server:

- The deployed build is not the source. If the mod ships packed, as a PBO, compare the PBO's modification time with that of the files holding the relevant fixes, and search inside the PBO for class names as strings, without unpacking it, before you look for a cause in the source. Report drift as its own finding. In one storage mod the PBO predated the fix that added a code lock bridge class, so two of five live bugs were partly old builds.
- Find which path wrote each log line. Before calling a feature partial or broken, trace every log line that "proves it works" to the path that wrote it: the synchronous shutdown, an action hook or a periodic scan. In the same mod, all the evidence that it stored containers came from `OnMissionFinish`; the run time paths did nothing all session.
- A gate's name is not its body. For each trigger gate (`HasX`, `CanY`, `IsZ`), paste and read the body; the name proves nothing. In the same mod `HasCargoOrAttachments` checked no attachments, so slot storage was invisible to every trigger, and many reviews missed it.
- Start the step 2 reviews in the foreground, together. A background agent cannot answer a permission prompt for files outside the working folder, so it fails instead.

## Rules for claims, fakes, locks and checks

- A claim that something is not a cause holds only for the size, version, data and conditions it was checked under. Do not turn "X does not matter" into a general rule when the checks did not cover other cases.
- A fake or stub of a remote side emits the same types as the real one, not just equal values. Never test serialized data with `is True` or `is False`; test `0` and `1`, booleans and missing values as the contract defines them. A test request is built the way the real producer builds it, never the most complete request for convenience. When the game shows a defect and the tests pass, first find the test that should have covered it and compare its inputs with the real ones field by field.
- Check every lock with two real attempts on the target system and require the second to fail. Look at the defaults of sockets, file sharing and standard library mutexes, and set each lock to refuse when in doubt.
- A check that says something was deleted, moved, repaired or restored must report a count above zero, or come with a separate check showing there was nothing to do. `{ok:true, count:0}` alone proves nothing.

## A correct citation may not prove the point

An auditor cited a vanilla test as proof that an API was synchronous: the test read a counter before and after the call and asserted `== 1` on the next line. The citation was exact. But a sibling API, documented as asynchronous, passed the same assert a few lines further down. The test could not tell the two apart, so it proved nothing about synchrony.

Before accepting a third party test, assert or rule as proof of a property, find a case without that property and check that the same assert fails there. If it passes, the evidence fits the conclusion but does not support it. Checking that a citation exists is the first step; checking that it tells cases apart is the second, and the one that gets skipped.

## A control built the same way as the gate shares its blind spot

A gate checked that proxies were turned 180 degrees about the vertical axis. Its negative control built a model turned 180 degrees about a horizontal axis and required the gate to fail it, which it did. The gate passed the real model and failed the control, and the result in game was still wrong: the weapons were turned about a horizontal axis.

The control applied `R_new = Ry(180) * R_old`, multiplying on the left, while the function that reads the frame returns the axes as rows in world space. Multiplying on the left flips rows, which turns about the proxy's own axis, not the world's. Measured: the local Y axis of those proxies pointed to `(1.0, -0.001, 0.006)`, the world X axis. The control used the gate's own mistaken convention, so it confirmed the convention instead of testing it.

When the thing that may be wrong is a convention (multiplication order, rows or columns, local or world frame, axis order, byte order, counting from 0 or 1), never build the control with the same code or convention as the gate. Build it from outside, from something whose value is known another way: a measurement by hand, an external reference file, a visible asymmetric marker. If the control and the gate share a function, module or formula, the control is not independent. If the gate passes while the visible result is wrong, suspect the convention before the threshold.

## Check the inventory before the reviews get it

1. Close a list built by regex with an independent count before reviewers see it. One power grid mod's table of save and load bodies listed 11 files while 25 contained `ctx.Read` or `ctx.Write`, missing a whole hook family (the mod's `OnStore*Device` hooks, 10 classes). Reviewers treat the table they are given as complete.
2. To check that a deployed PBO matches the source, unpack it and compare file contents, with line endings normalised, against each candidate tag. In one mod a release tag differed from the published PBO in 51 of 144 scripts.
3. Do not count entities by searching for class names in `storage_1\data\*.bin` or `types.bin`: a search for classes known to be in the world returns 0 matches. Count them in game.
