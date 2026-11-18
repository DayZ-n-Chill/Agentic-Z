# Debugging a feature that does not work

How to find out why a DayZ mod feature does nothing after it was built and the log is clean: six layers checked from the top down, how to measure before guessing again, how to place probes, and how to bisect by component when the layers do not find the cause. The implementation protocol (`skills/dayz-scope-mod/references/implementation-protocol.md`, "Debug and fix") points here.

Start from the logs when there are any. `/dayz-gate` and `/dayz-logwatch` triage every error line: a known line already carries its fix and owner, and a new one goes to `dayz-mod-debugger`. This file is for what is left, the feature that fails with a clean log. For an RPT, script log or crash log line, use `error-catalog.md` and `_shared/enscript/depth/runtime-traps.md` instead.

## The six layers, top down

Confirm each layer before you look at the next.

| Layer | Check |
|---|---|
| Config and engine | `scope` in `config.cpp` is right; the class has the right parent; the config compiles (`/dayz-lint`, then `/dayz-gate build`). |
| Entity setup | The entity spawns in game. `IsTakeable()` is what you meant: a ground item that is neither takeable nor `IsActionTargetVisible()` hides its action cursor (`P:\scripts\5_mission\gui\actiontargetscursor.c:719`; `error-catalog.md`, "Stopping pickup (E12)"). The base class gives the behaviour you expect. |
| Action registration | `AddAction(MyAction)` is in the entity's `SetActions()` override (`AddAction`, `P:\scripts\4_world\entities\itembase.c:255`). The action class is registered in `ActionConstructor.RegisterActions` and compiles (`_shared/enscript/patterns/actions.md`). `CreateConditionComponents` sets the right target and item conditions. |
| Client conditions | `ActionCondition()` reads only data both sides have, because the server runs it again as the start gate. The target type check is right. The target condition's range or component matches the interaction distance. Since 1.30, `CanBeStarted()` returns true. |
| Server execution | The server methods (`*Server()`) run, permissions and validation pass, and the data writes succeed. |
| Response path | The RPC goes back to the client, the client cache updates, and the UI refreshes. |

For a bug that is not about an action, the same order reads: logs (RPT and script log), config, RPC, engine class hierarchy, client and server data, race conditions.

- Never debug a layer until the one above it is confirmed.
- Propose the fix and say why before you apply it.
- Under 90 percent confidence, ask the user before applying it.
- After a fix, run the edge case checklist again (`skills/dayz-build-pbo/references/file-checklists.md`, "Edge cases in logic").

## Measure before the next guess

Once the static layers are confirmed, do not jump to another reading of the code or to a bisection. First prove what the instrument measured and whether the suspect code could have run before the symptom.

1. **Say what the instrument answers.** Before you base a decision on a measurement, write "this command answers X, not Y" and keep three outcomes: `PASS`, `FAIL`, and `INCONCLUSIVE` or `SETUP_FAIL`. Search for private data case-insensitively and for its variants. A sample ordered by path cannot estimate proportions. A reproduction is not valid until it has gone red at least once with the fix turned off. Reproduce a dependency error in a known good setup before blaming the repo. If the first instrument says "clean", confirm with a second, independent one.
2. **A silent run needs a probe at the receiver.** If the static path checks out end to end and the run is still silent, stop reading code and put a minimal probe on the first line of the receiver, on each side that matters. Every guard that drops a call logs why, rate limited. Tell "did not arrive" from "arrived and was refused" first, then go on through the layers.
3. **Prove the change could have run before you bisect.** For a suspected regression, show that the changed code ran before the symptom. With no earlier marker, a build number that lines up with the bug proves nothing: log the callback where the effect is seen and capture the full stack to name the caller, printing it one line at a time. The 1.29 retail logger cut long messages at about 255 characters; on 1.30 neither DayZDiag nor the retail server does (the 1.30 retail client was not measured). Bisect only when the change is proven to run in time and the cause is still open.

## Probe rules

- **Both sides from the first run.** For any synced state failure, log client and server from the start and confirm the value on the side where the symptom shows. Treat every difference between the sides as data before you propose a fix.
- **Order and length.** In client probes put time, position and state first and raw values and flags last. Keep each payload under about 225 characters so a logger wrapper cannot cut it.
- **A timestamp on every line.** Start each diagnostic line with `t=GetTickTime()`. Estimate the server to client clock offset from the median of request and acknowledge pairs, put one series onto the other, and drop samples with too large a gap. What to do with the aligned series is in `measurement-discipline.md`.
- **Prove a probe is reached before adding fields.** When a probe has never printed, do not add fields. Walk up from its call site to the function entry and evaluate every `return`, `continue`, side guard and state guard in the real scenario, then search both the server and the client log for its marker; it may be silent only on the side you are reading. If a guard exits first, move the probe or drive a state that reaches it. A probe behind a guard it cannot pass fails because of where it sits, not what it measures.
- **Keep the probe independent of what it checks.** A world space point made by applying the entity's transform to a fixed model point is not an independent view of that transform. An exactly round ratio, a value equal to a model constant, or a field that is zero in every sample is a warning about the probe before it is evidence. Check selection and memory point names in the source model. Keep time order in a series: "minimum to maximum" reports a fall as a rise when the maximum came first. Report ordered intervals and unrounded values.
- **Find who wrote an engine channel error.** An RPT line under `RESOURCES`, `MATERIAL` or `PHYSICS` can come from a diagnostic call in the mod, not the engine's own asset load. Before you treat it as the root cause:
  1. Search the mod for every API that can open or inspect the named resource.
  2. Match the RPT against the same run's script log; matching counts, inputs and instance numbers identify the writer.
  3. Compare the delay with the mod's own `CallLater` intervals.
  4. Find positive proof of the load, such as a non-empty `GetShapeName()` or a later warning that only walking the shape can produce.

  A probe that cannot finish logs an explicit inconclusive reason and its input, never an unexplained engine channel error that can pass for a product symptom.

## Component bisection

Use it when the six layers have not found the cause and the symptom is yes or no: it passes or fails, it is visible or not, the action shows or not, the centre of mass is zero or not.

1. List the separable components. A `.p3d`: each LOD (Visual, Geometry, Fire Geometry, View Geometry, LandContact, Memory, Shadow). A mod: each sub-module (a modded class, an RPC, a layout, an animation, a particle). A pipeline: each phase (extract, assemble, bake, binarize, PBO, deploy).
2. Build a hybrid of the working control and the failing test, half from each. For a `.p3d`, copy the control model and replace its Fire Geometry and View Geometry LODs with the test model's. For a mod, inherit the control module in `config.cpp` and override only the suspect members.
3. Reproduce on the hybrid. If it fails the bug is in the test half; if it passes it is in the control half. Recurse into that half.
4. Repeat until one component is left. N components take about log2(N) runs (3 LODs: 2; 8 sub-modules: 3).
5. Only then read the mechanism inside that component and name the cause as a `path:line`. Bisection finds the component; naming the cause still means reading the code.

Do not vary parameters of the suspect component first ("what if the mass is not uniform?", "what if the faces are triangles?", "what if the material is metal?"). Each variation feels like progress, but if the first suspicion is wrong you spend one run per variation without reaching the bug.

A quad vehicle's `.p3d` spawned with a centre of mass of (0,0,0) once binarized. Everything pointed at the Geometry LOD, and five trial binarizations ruled out material, mass distribution, topology, skeleton and writer. Two bisection binarizations (a working vehicle with the quad's Geometry LOD, and the quad without its Fire Geometry LOD) found it: a stray all-zero mass tag in the Fire Geometry LOD, which binarize took over the Geometry LOD's mass.

Use a control before the bug, too. For a new path or pipeline (the first skinned export, the first proxy convention, the first crew selection, a fire mode in a new `CfgWeapons` class), pass a known good control through it before the first try with your own asset. If vanilla already does it, read the vanilla config on `P:\` first, and pass a model you know works through your exporter; vanilla `.p3d` files stay closed (`/dayz-import-mod` and `skills/dayz-import-mod/references/study-a-packed-mod.md` cover studying another mod's packed model, and `/dayz-p3d-audit` reads source models only). If the control fails too, the bug is in the pipeline, not your asset. Two cases this would have cut short: a `Mode_FullAuto` whose scope was shadowed by the vanilla class, visible by reading the vanilla config; and a mesh mirrored left to right, found only after comparing the skeleton with a vanilla one.
