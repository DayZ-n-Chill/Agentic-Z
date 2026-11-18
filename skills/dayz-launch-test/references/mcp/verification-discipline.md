# When a verdict is worth believing

How to read and write a verdict from an MCP-driven run: which mod the run loaded, what the PBO really holds, where a hang is, how many samples a negative rests on, and how to review the bridge without signing off on a layer you did not open.

These rules come from game sessions with the third-party dayz-mcp tool. None is a vanilla fact or checked on `P:\`; `<dayz-mcp>` is your dayz-mcp checkout.

## Before you blame the mod

- Check the stimulus first. Before blaming the mod for an automated FAIL, read the source of the actuator or bridge and confirm the stimulus reached the object. Run a control that differs in one thing, or a manual test, to tell a test tool defect from a mod defect.
- One reproduction per layer of defence. When several defences catch the same failure, build one reproduction per layer that reaches that layer's own check, and ask for each layer's own signal. A combined PASS of "it does not fail" does not prove they all work.
- A dead peer explains the errors after it. At the first odd error from a client-side verb, check the client's process id, the end of its RPT and `bridge_status` before you go on. If the peer died, collect the minidump and the evidence and record a degraded shutdown; do not diagnose the errors that follow.
- Read the client log before you record a FAIL (`verb-gotchas.md`, "Six traps that cost a run each", trap 6).

## Check which mod the run loaded

`dayz_test_run` boots the registered project its `project` argument names (a name with no launcher policy is rejected with `bad_project`) and reports `succeeded` for that run, whether or not it is the mod you meant. When the argument named another registered mod by mistake, the server loaded that mod with `@DayZ_MCP` and another mission, never the mod under test, and the missing compile errors were read as a fix.

Before you credit a compile result or any verdict to the mod under test, read the `-mod=` and `-mission=` of that run in its RPT. An in-game observation is worth whatever the `-mod=` line of its own run is worth. `run-lifecycle.md`, "A free lease does not mean a free machine", reads the same line to tell whose run it is.

## Read the deployed PBO's file list, not the source tree

A build can pack stray scratch files, so assuming the PBO holds exactly the source tree misreads a compile verdict from the boot log. Know what the build packed before a deciding boot.

- The PBO index is plain text near the start of the file. `grep -a "scripts\\\\" <mod>.pbo` finds the names, but it prints whole newline-separated chunks of binary, not one name per line, so it is not a file list.
- To read the index itself, parse the header. In this repo `skills/dayz-build-pbo/pbo_entries.py` has no command line; call `read_pbo(path).entries` from Python. `/dayz-launch-test` lists the PBO and compares the packed `.c` count with the source's.
- Keep experiments out of the packed tree. A rebuild packs any scratch file still in it, so read the deployed PBO's index again after a rebuild. AddonBuilder's `-temp` sync is incremental and can serve stale source, but `/dayz-build-pbo` empties `P:\temp\<ModName>` on every build, so no flag is needed for that.

The index says what is packed, never why a compile failed.

## Place a server hang from the log ends first

A boot that never finishes (the RPT frozen, the process alive and turning over at low CPU) is a verdict with no location. Before you pin the hang on a branch of code:

1. Read the end of both logs of the run, starting with the one that carries markers. The RPT often ends in world streaming warnings; the mod's own marker lines, stage messages and init lines are in `script*.log`. The gap between the last printed stage and the first missing one is a candidate, not a location. Before you treat it as one, check in the source and in the run's logs that the markers come in that order and each one is mandatory on that path, that they belong to the same flow and this run, and that their output is visible. A marker printed from a deferred callback (the mission driver in `actions-ui-and-inventory.md` starts with `CallLater`) is not in the same flow as the init stages, so its order against them is not guaranteed. If any of this is missing, log the entry and exit of each stage before narrowing. A missing stage proves no progress was seen, not where the server spins: "no prune message after init" is a different fact from "spinning inside the prune loop".
2. Check the loop structure of the candidate region in source before you suspect it: a loop that counts down with every branch decrementing, work capped per tick, helpers with no loops. That clears the cheap suspects and moves suspicion to the rest (world scan helpers, recursion or re-entry on the engine side) without naming any of them as the cause.
3. A regression needs a controlled comparison between revisions; toggling paths inside one revision only narrows the place. For code that never ran in the engine before, blaming the newest change stays unproven: the hang can be a regression, an old bug showing for the first time, or a side effect of the new logging. Only the same scenario with one variable changed (the revision, or just the newest change reverted) shows a regression. Hold the merge until that comparison is done.

`/dayz-logwatch` reads both logs with triage.

## A negative from one sample is not a negative

A material override was written again on a worn garment and the garment did not change. The garment was at health level 4, and the finding was written as "at health level 4 a new override is never rendered", backed by two captures minutes apart. It was false. The two captures ruled out a drawing glitch, not the sample size of one, and two things had changed between the write that worked and the one that did not: the health level (0 to 4) and the moment of the write (right after a state change, against an arbitrary moment).

Before you write a negative into a handoff:

1. Count experiments, not captures. A repeated capture is still one sample.
2. List everything that changed between the working case and the failing one. With two or more, the negative names none of them until each is tested on its own.
3. Narrowing a finding to one cause looks careful but is one more claim. If that cause is the wrong one, the caution points away from the real mechanism.

## Rules for the bridge's own code

A pass is valid only if the command got a response and the protocol keeps apart the things it means to keep apart.

1. Every "did not happen" check needs a response tied to that command, for example `answered(tag)`, not an earlier response from the run. Without one the case is `INCONCLUSIVE`, never `PASS`. Publish the total response count, and if it is zero, stop early instead of printing verdicts. A refusal case passes only after showing that the target could receive and carry out the request.
2. Before you fix the wire format, search for each new top-level key in the serialized object and in every consumer. Names like `state`, `status`, `error` or `type` are usually taken; if one collides, nest the payload under an object named for the feature (for example `{ok, dialog:{state,...}}`) instead of overloading the field. The check reads the real shared contract; the producer's own tests do not prove it stays compatible.
3. A handshake change is global, and authentication is not identity. Before you change a version constant or deploy the PBO or daemon that carries it, look at the processes and sessions that load that mod now. If someone else's game is there, do not publish: coordinate or revert, because holding your lease does not prove nobody else uses the protocol. Keep the instance identity stable for the life of the process and never hot-reload it; the key only authenticates and can rotate. Knowing the instance grants no authority, a shared profile token does not identify a process, and the secret is never the identity.
4. A cache must keep the property that tells results apart. Before you cache fencing, authorization, rate limits or session lookups, write down which property separates the results and show the cache key keeps it. Caching by instance let two processes share a process id: the intruder received 100 of 100 changes and the binding never switched to `AMBIGUOUS`. Caching the peer table for 50 ms hid a second polling peer: 40 of 40 ticks with no command. Measure hits and cost under the real pattern and under load. Remove a cache that saves no measured work or merges separate actors.

## Three layers that do not name each other

Do not declare that a verb does not do something after reading only its Python side. The MCP server has three layers, and none names the others:

| Layer | Files |
|---|---|
| The tool, in Python | `dayz_mcp/server.py` |
| HTTP ingress | `loopback.py`, `session_coordination.py` |
| The bridge, in Enforce Script inside the game | `MCPBridge.c` |

Many tools are a thin wrapper that ends in `runtime.call_bridge(...)`; the real behaviour lives further down. Two reviewers made this mistake on the same system. One called "`y=0` snaps to the ground" false because Python passes `pos` through `_require_vec3` untouched; the snap happens in the bridge, where `ValidateSpawnArgs` defaults `flags=0` to `ECE_PLACE_ON_SURFACE`, and it had been measured four times. The other said no file produces `box_claimed` after searching `daemon.py`; the emitter is in `session_coordination.py`, in `box_wait_touch`, reached through `loopback.py`. Both cited `path:line`. Check in the layer where the behaviour would live.

1. Before you say a verb does not do something, check whether its body ends in `call_bridge`. If it does, the honest answer is "cannot be checked from the Python side; open `MCPBridge.c` to decide".
2. Before you say a field is never produced, search for its name across all of `<dayz-mcp>/tools/dayz_mcp/`, not just the module where you expect it.
3. Before you contradict documented behaviour, search the measurement notes. Contradicting one means disproving the measurement, not reading code in another layer.
4. To say something does happen, seeing it once is enough. To say it does not, you must have looked where it would happen.

When you brief a reviewer whose workspace holds only one layer, say so, and require everything about the other layers under a "not verified" heading. A plain "cannot check" is worth more than a confident wrong finding, because the wrong one spreads: another session can fix something that was never broken.

## Checking a pull request through an outside test runner

Two failures, from an attempt to point a test runner's TOML config at another source path for one run:

1. Swapping Windows paths inside TOML edits TOML escapes, not path bytes. In a basic (double-quoted) string every backslash is escaped as `\\`. Writing single backslashes turns `\U` into an invalid unicode escape and the parser stops with `TOMLDecodeError: Invalid hex value` before anything runs; a single backslash before `t` or `n` parses quietly into a tab or a newline. A hash of the planned bytes does not prove the TOML parses. Load the result with `tomllib` in a fresh process and compare the decoded path with the intended one before handing it over. Literal (single-quoted) strings take backslashes as they are.
2. Compare the deployed PBO with the recorded baseline before you plan the check. The runner validated the deployed PBO against a recorded baseline hash; when they differ, the owner's baseline, PBO and source have to be lined up first, and no path change or rebuild fixes it. On failure: the preflight rejects, restore the TOML and the PBO byte for byte, keep the evidence, and hand it to the owner.
