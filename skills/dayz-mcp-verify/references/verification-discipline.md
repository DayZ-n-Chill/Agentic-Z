# Verification discipline: when a verdict is worth believing

Rules for reading and writing verdicts from an MCP-driven run: which mod the run loaded, what the PBO really holds, where a hang is, how many samples a negative has, and how to review the bridge itself without signing off on a layer you did not open.

These are lessons from game sessions with the third-party dayz-mcp tool, each with the session that paid for it. None is a vanilla fact and none is checked on `P:\`. `<dayz-mcp>` is the folder of your dayz-mcp checkout.

## Before blaming the mod

- **Check the stimulus first.** Before blaming the mod for an automated FAIL, check the source of the actuator or bridge and confirm the stimulus reached the subject. Run an equivalent control with one difference, or a manual test, to tell a harness defect from a mod defect.
- **One repro per defence layer.** If several defences catch the same failure, design one repro per layer that reaches that layer's protection point. Ask for each layer's own signal; an aggregate PASS of "it does not fail" does not prove that all of them work.
- **A dead peer explains the errors after it.** At the first odd error of a client-side verb, check the client's process id, the tail of its RPT and `bridge_status` before continuing. If the peer died, collect the minidump and the evidence and record a degraded shutdown; do not diagnose the errors that follow as harness state.
- **Read the client log before recording a FAIL** (`verb-gotchas.md`, "Six traps", trap 6).

## Check which mod a run loaded before reading its verdict (added 2026-10-03)

`dayz_test_run` boots the registered project its `project` argument names (a name with no launcher policy is rejected with `bad_project`) and reports `succeeded` for that run, whether or not it is the mod you meant to test. In one run the `project` argument named another registered mod by mistake: the server loaded that mod and `@DayZ_MCP` with another mission, never the mod under test, and the absence of the mod's compile errors was read as a fix. A "defect measured in the engine" was written from it and had to be retracted.

Before you attribute a compile result or any verdict to the mod under test, read the `-mod=` and `-mission=` of that run in its RPT. The `dayz-test-ingame` skill states the rule from the launch side: an in-game observation is worth whatever the `-mod=` line of its own run is worth. `run-lifecycle.md` ("A free lease does not mean a free machine") reads the same line to know whose run it is.

## Audit the deployed PBO's file index, not just the source tree (added 2026-10-04)

The build can pack untracked scratch files, so assuming the PBO holds exactly the source tree misattributes a compile verdict read from the boot's log. Know what the build packed before a decisive boot.

- The PBO index is plain text near the start of the binary. `grep -a "scripts\\\\" <mod>.pbo` finds the names, but it prints whole newline-delimited chunks of binary, not one name per line, so it is not a file list.
- To read the index itself, use a reader over the header. In this repo the module `skills/dayz-build-pbo/pbo_entries.py` has no command line; call `read_pbo(path).entries` from Python to get a PBO's entries; the `dayz-test-ingame` skill lists the PBO and compares the packed `.c` count with the source's.
- Keep experiments out of the packed tree. A rebuild packs the scratch files still in it, so after a rebuild read the deployed PBO's index again before the decisive boot. AddonBuilder's `-temp` sync is incremental and can serve stale source, but `/dayz-build-pbo` already empties its temp dir `P:\temp\<ModName>` on every build, so no flag is needed for that.

Limit: the index audit establishes what is packed, never why a compile failed.

Measured in a session that spent two days on a mod's compile failures; the listing behaviour of `grep -a` was measured on real PBOs.

## A server hang is bounded by log tails first (added 2026-10-04)

A boot that never finishes (1 of N driver snapshots, the RPT frozen, the process alive and spinning at low CPU) is a verdict without a location. Before attributing the hang to a specific branch:

1. **Read both log tails of the run, and start from the one that carries the markers.** In the run behind this section the RPT tail did not locate the hang (it ended in world-streaming warnings); the useful markers (the mod's `MARK` lines, stage messages, init-completion lines) were in `script*.log`. The interval between the last printed stage and the first missing one is a candidate, not a location. Before turning it into a location, check in the source and in the run's own logs: (a) the order of the markers, and that each one is mandatory on that path; (b) that they belong to the same flow and to this run; (c) that their emission is visible. A marker printed from a deferred callback (the mission driver pattern in `actions-ui-and-inventory.md` starts with `CallLater`) is not in the same flow as the init stages, so its order relative to them is not guaranteed. If any of these guarantees is missing, instrument the entries and exits of the stages before narrowing. A missing stage proves a lack of observed progress, not where the server spins: "no prune-stage message after init" is a different fact from "spinning inside the prune loop".
2. **Verify the candidate region's loop structure in source before suspecting it** (a descending loop with every branch decrementing; resolution capped per tick; helper functions free of loops). That removes the cheap suspects and moves the suspicion to the remaining ones (world-scan helpers, recursion or re-entry on the engine side), without ever naming them as the cause.
3. **Evidence of a regression needs a controlled comparison between revisions; a bisect inside one revision only localizes.** For a code path that never ran in the engine under any revision (the instrument compiled for the first time the same day), the attribution to the newest change stays unproven: the hang may be a regression, an old bug surfacing for the first time, or an artefact of the instrument, and the path never having run before does not clear the newest change either. A scenario bisect within one revision (one sub-path toggled: crossing the delete threshold against marking strikes only) yields a candidate sub-path where the hang triggers, never evidence of a regression: the base revision may carry the same defect. Evidence of a regression comes only from the same scenario with one variable changed (the revision, or only the newest change reverted). The merge stays on hold until that comparison closes.

The case behind this section: a seed-and-prune strike scenario that hung the server between init and the first prune snapshot.

`/dayz-logwatch` reads both logs with triage; the `systematic-debugging` skill has the general method.

## A negative of one sample is not a negative (added 2026-09-01)

While closing a gate, a material override was written again on a worn garment and the garment did not change. The garment was at health level 4. It was written up as a scoped finding ("at health level 4, a new override never gets rendered"), with the mechanism declared as not established and with two captures taken minutes apart. It looked prudent. It was false.

The two captures ruled out a rendering artefact, not the sample size of one, which was what the whole claim rested on. Repeating the observation does not raise the experiment's sample size; it only confirms the observation was read correctly. And the variable was confounded: between the write that worked and the one that did not, two things changed, the health level (0 to 4) and the moment of the write (right after a state change, against an arbitrary instant). The result was blamed on the one being watched.

Before writing a negative into a handoff from this kind of test:

1. Count experiment samples, not captures. A repeated capture is n=1.
2. List everything that changed between the working and the failing case. If there are two or more, the negative names neither until the matrix is crossed.
3. Scoping the finding to one axis looks cautious and is one more claim: the chosen axis may be the wrong one, and the caution then points away from the real mechanism.

## Verifier and bridge integrity: evidence, contract and identity

The bridge measures and tells subjects apart; a green is valid only if the command got a response and the protocol keeps the identity it means to isolate.

1. **Every negative criterion needs liveness per command.** Before resolving "X did not occur", require a response attributable to that command, for example `answered(tag)`, not an earlier response of the run. Without it the case is `INCONCLUSIVE`, never `PASS`. Publish the global response count and, if it is zero, abort early instead of printing a set of verdicts. A denial case passes only after showing that the subject could receive and execute the request.
2. **Take a census of keys before closing the wire format.** Search for each new top-level key in the serialized flat object and across all of its consumers. Obvious names such as `state`, `status`, `error` or `type` are usually taken; if they collide, nest the payload under an object named for the feature (the measured case ended as `{ok, dialog:{state,...}}`) instead of overloading the field. The gate reads the real shared contract; the producer's own test suite does not prove forward compatibility.
3. **A handshake change is global, and authentication is not identity.** Before changing a version constant, or deploying the PBO or daemon that carries it, inspect the processes and sessions that load that mod right now. If someone else's game is present, do not publish: coordinate or revert; holding your lease does not prove that no one else consumes the protocol. Keep two fields with different contracts: the instance identity stays stable for the life of the process and is not hot-reloaded; the key only authenticates and can rotate. Knowing the instance grants no authority, and a shared profile token does not identify a process. Never reuse the secret as the identity.
4. **A cache must preserve the discriminator.** Before caching fencing, authorization, rate limits or session resolution, write down which property distinguishes the result and show that the cache key preserves it. Caching by instance let two processes share a process id: the intruder received 100 of 100 mutations and the binding never switched to AMBIGUOUS. Caching the table for 50 ms hid the second polling peer: 40 of 40 ticks without a single command. Measure hits and cost under the real pattern and under load: in the measured case the useful rate was 0.0 and the cost at rest did not represent the loaded regime. A cache that saves no measured work, or merges distinct actors, is removed.

## Three layers that do not name each other (added 2026-08-29)

Do not declare that a verb does not do something after reading only the Python side. The MCP server has three layers, and none names the others in its own text:

```
1. the tool in Python         dayz_mcp/server.py
2. HTTP ingress               loopback.py, session_coordination.py
3. the bridge in Enforce      MCPBridge.c, inside the game
```

Many tools are a thin wrapper that ends in `runtime.call_bridge(...)`. The real semantics live downstream. A reviewer who opens only one layer believes the whole system is in front of them and signs off on behaviour they have not seen.

Measured on 2026-08-29: two independent reviewers made the same mistake the same night, on the same system.

- One declared the claim "`y=0` snaps to the ground" for `world_spawn` false, reasoning that Python passes `pos` through `_require_vec3` untouched. The premise was right and the conclusion wrong: the snap happens in the bridge. In `MCPBridge.c`, `ValidateSpawnArgs` sets `validation.flags = ECE_PLACE_ON_SURFACE` as the default for `flags=0`, and `IsAllowedSpawnFlags` asks for that bit in every accepted combination but one, `ECE_CREATEPHYSICS|ECE_TRACE`. The fact had also been measured four times already (`pos=[7500,0,7500]` gave `pos_real y=313.14`).
- The other declared that "no file produces `box_claimed`" after searching for it in `daemon.py`. The emitter lives two hops further, in `session_coordination.py` inside `box_wait_touch`, reached through `loopback.py`.

Both opened files and cited `path:line`. Verifying is not enough: verify in the layer where the behaviour would live.

Rules:

1. Before declaring that a verb does not do something, check whether its body ends in `call_bridge`. If it does, the only honest answer is "not verifiable from the Python side", with a note that `MCPBridge.c` has to be opened to decide.
2. Before declaring that a field is not produced, do not trust the module where the assumed architecture would put it. Search for the field name across all of `<dayz-mcp>/tools/dayz_mcp/`.
3. Before contradicting documented behaviour, search the measurement notes. They record measurements: contradicting one means refuting the measurement, not reading code from another layer. It takes five seconds.
4. A useful asymmetry: to assert that something does happen, seeing it once is enough. To assert that it does not, you must have looked where it would happen.

When writing a review brief: if the reviewer's workspace holds only one layer, say so in the brief and require that everything about the other layers goes under a "not verified" heading. In the run behind this section the brief did not say so, and both reviewers filled the gap with inference instead of a statement of ignorance. A well-placed "unverifiable" is worth more than a brilliant false finding, because the false one travels: by the time the refutation arrived, another session had already applied a fix to something that was not broken.

## Gating a pull request through an external executor (added 2026-10-02)

Two defects, measured in one aborted attempt to gate an external pull request by temporarily repointing the source path in a gate executor's TOML config:

1. **A programmatic swap of Windows paths inside TOML edits TOML escapes, not path bytes.** In a basic (double-quoted) string every backslash is escaped (`\\`). Writing single backslashes turns `\U` into an invalid unicode escape, and the parser stops with `TOMLDecodeError: Invalid hex value` before anything is evaluated: the run died in preflight. A hash that matches the planned bytes does not prove the TOML parses. Load the result with `tomllib` in a fresh process and compare the decoded path with the intended one before handing it over: a single backslash before `t` or `n` parses fine, into a tab or a newline. Literal (single-quoted) strings take backslashes as they are.
2. **Check the deployed PBO against the sealed baseline before planning the gate.** The executor validated the deployed PBO against a sealed baseline hash. When they differ, the gate needs the owner's baseline, PBO and source aligned first; no repointing or rebuild resolves it. The abort path: preflight rejects, restore the TOML and the PBO byte for byte, freeze the evidence, escalate.

Measured in one gate run that aborted in preflight; the clean abort preserved the owner's PBO.
