# Evidence and controls

How to tell real evidence from evidence that only looks real: the deployed build against the source, which code path wrote a log line, positive and negative controls that can actually fail, inventories that are complete, and store constructors that write while they read. Open this in steps 1 and 3 and whenever a check comes back clean.

These are audit lessons; the DayZ facts in the last section were measured in game and cannot be checked on `P:\`.

## Production triage: deployed artifact, path attribution, gates whose name lies, starting auditors

Case: a virtual storage mod, five production bugs and a dual audit.

- **The deployed artifact is not the source (before step 1 when the trigger is a production bug)**: if the audited code is distributed packaged (as a PBO or another build), compare the artifact's modification time with the modification times of the relevant fix files, and probe inside the artifact (search the binary for class names as strings, without unpacking it) before you look for a root cause in the source. Report drift as its own finding. Case: the PBO was dated 28 May and lacked the 1 June code lock bridge class, so two of the five bugs were partly deployment drift.
- **Path attribution in log evidence**: before you classify a feature as partial or broken, attribute each log line that "proves X works" to the path that emitted it (synchronous shutdown, action hook or periodic scan). Case: the evidence that "the mod virtualizes" came only from `OnMissionFinish`; the runtime paths showed no activity in the whole session.
- **Gates whose name lies (add to the auditor prompts)**: for each trigger gate function (`HasX`, `CanY`, `IsZ`), paste and read the body; do not accept the name as evidence of coverage. Case: `HasCargoOrAttachments` checked no attachments at all, so all slot storage was invisible to all four triggers. Nine auditors and the cross-actor pass missed it, and it surfaced only when the user pushed back.
- **Starting auditors (step 2)**: background agents automatically deny permission prompts outside the working folder, so start the auditors in the foreground, all in a single turn and in parallel. Case: the mechanical-checks agent failed in the background with a permission failure.

## Four standing rules for claims, fakes, locks and verifiers

- **Scope of a non-causality claim**: bound every claim that something is not a cause to the size, version, fixture and conditions under which it was verified. Do not promote "X does not matter" to a universal conclusion when the corpus does not cover other regimes.
- **Fakes and fixtures**: make every remote fake or stub emit the same types as the real wire, not just equivalent values. Do not use `is True` or `is False` on serialized data; test `0` and `1`, booleans and missing values explicitly, as the contract defines them. A fixture composes a request the way the producer composes it, never the most complete request "for convenience". When the game shows a defect and the suite is green, first look for the test that already covered the case and compare its inputs with the real ones field by field.
- **Resource exclusion**: verify every resource exclusion with two real acquisitions on the target operating system, and require the second one to fail. Inspect the defaults of sockets, file sharing and standard-library mutexes, and configure each lock to fail closed.
- **Verifiers that report zero work**: for every verifier that asserts something was deleted, moved, repaired or restored, require an affected count greater than zero or an independent pre-check proving there was no work to do. Do not accept `{ok:true, count:0}` as proof on its own.

## A correct citation may not prove what is asked of it (step 3a)

An auditor cited an official vanilla test as proof that an API was synchronous: the test measured a counter before and after the call and asserted `== 1` on the next statement. The citation was literal and exact. But a sibling of that API, which is documented as asynchronous, passed the same assert a few lines further down. The test did not discriminate, so it proved nothing about synchrony.

**Rule**: before you accept a third-party test, assert or invariant as proof of a property P, find a case that does not have P and check that the same assert fails there. If this negative control passes, the evidence does not discriminate: it is compatible with the conclusion but does not support it. This is the same idea as "a gate that cannot be turned red is not a gate", applied to third-party evidence instead of your own gates. Checking that the citation exists is the first step; checking that the citation discriminates is the second, and it is the one that gets skipped.

## A control that inherits the instrument's convention is born blind

The previous section covers a control that does not discriminate. This one covers a control that discriminates perfectly, but inside the very blind spot it was meant to measure.

A gate checked that proxies were rotated 180 degrees around the vertical axis. It had a well-designed negative control: it generated a model rotated 180 degrees around a *horizontal* axis and required the gate to flag it red. It did. The gate was green on the good artifact and red on the negative control, and the result in game was **wrong**: the weapons had rotated around a horizontal axis.

The cause: the control generator applied `R_new = Ry(180) * R_old`, multiplying from the left, and the function that derives the frame returns the axes as rows in world coordinates. Multiplying from the left negates rows, which means it rotates around the proxy's own axis, not around the world's. Measured: the local Y axis of those proxies pointed to `(1.0, -0.001, 0.006)`, which is the world X axis. The control used the same mistaken convention as the gate, so it confirmed the convention instead of testing it.

**Rule**: when the thing that might be wrong is a convention (multiplication order, rows versus columns, local versus world frame, axis order, endianness, 0-based versus 1-based), the control cannot be built with the same code or the same convention as the instrument. Build it from outside: an artifact whose expected value is known by other means, such as a manual measurement, an external reference file or a visible asymmetrical marker, and compare against that. A control that shares the gate's apparatus only proves that the apparatus is self-consistent.

**Cheap signal**: if the control and the instrument share a function, module or formula, the control is not independent. And if the gate is green while the observable result is wrong, suspect the convention before the threshold.

## Census the inventory before handing it to auditors; compare the deployed PBO with the source

1. A regex-generated inventory is closed with an independent census before auditors see it: a power grid mod's save and load body table listed 11 files while 25 contained `ctx.Read` or `ctx.Write`, missing an entire hook family (the mod's `OnStore*Device` hooks, 10 classes). Auditors treat the handed table as complete.
2. Design note: "the deployed artifact is not the source" is checked in DayZ by extracting the PBO and comparing by content (EOL-normalized) against each candidate tag: a release tag differed from the published PBO in 51 of 144 scripts.
3. Do not count entities by searching class names in `storage_1\data\*.bin` (nor in `types.bin`): the positive control returns 0 matches in a world that does contain those classes. Count them in game.
