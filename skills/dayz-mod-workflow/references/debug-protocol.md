# Debug and fix protocol

How to diagnose a DayZ mod feature that "doesn't work" after it was implemented: six layers checked top down, the rules for probes, and component bisection when the layers do not isolate the cause. `dayz-mod-workflow` points here from its "Debug and fix" section. For general debugging method (root cause before fix) see `systematic-debugging`.

Start from the logs when there are any. `/dayz-gate` and `/dayz-logwatch` triage every error line; a known line already carries its fix and owner, and a new one goes to `dayz-mod-debugger`. This protocol is for what remains: the feature that fails with a clean log.

## The six layers (in this order)

**Layer 1: config and engine**
- [ ] Is the `scope` value in `config.cpp` right?
- [ ] Does the class inherit from the right parent?
- [ ] Does the config compile without errors? (`/dayz-lint`, then `/dayz-gate build`)

**Layer 2: entity setup**
- [ ] Does the entity spawn in game?
- [ ] Is `IsTakeable()` what you intended? A ground item that is neither takeable nor `IsActionTargetVisible()` has its action cursor hidden (`P:\scripts\5_mission\gui\actiontargetscursor.c:719`); see `error-catalog.md`, "E12: stopping pickup".
- [ ] Does the base class provide the behaviour you expect?

**Layer 3: action registration**
- [ ] Is `AddAction(MyAction)` in the entity's `SetActions()` override (`AddAction`, `P:\scripts\4_world\entities\itembase.c:255`)?
- [ ] Is the action class registered in `ActionConstructor.RegisterActions`, and does it compile? (`skills/_shared/enscript/patterns/actions.md`)
- [ ] Does `CreateConditionComponents` set the right target and item conditions?

**Layer 4: client conditions**
- [ ] Does `ActionCondition()` read only data both sides have? The server runs it again as the start gate.
- [ ] Is the target type check right?
- [ ] Does the target condition's range or component match the expected interaction distance?
- [ ] (since 1.30) Does `CanBeStarted()` return true?

**Layer 5: server execution**
- [ ] Do the server-side methods (`*Server()`) run?
- [ ] Do permissions and validation pass?
- [ ] Do the data writes succeed?

**Layer 6: response path**
- [ ] Is the RPC sent back to the client?
- [ ] Is the client cache updated?
- [ ] Is the UI refreshed?

For a bug that is not about an action, the same top-down order reads: logs (RPT and script log), config, RPC, engine class hierarchy, client and server data, race conditions.

Rules:

- **Never debug layer N+1 until layer N is confirmed working.**
- **Propose the fix and explain why before applying it.**
- **Under 90% confidence, ask the user before applying it.**
- **After a fix, run the edge-case checklist again** (`checklists.md`, section 8).

## Measure before forming another hypothesis

Once the static layers are confirmed, do not jump straight to another reading of the code or to a bisection. First prove what the instrument measured and whether the suspect code could have run before the symptom.

1. **State the question and the instrument (lesson LL-287).** Before basing a decision on a measurement, write "this command answers X, not Y" and keep three outcomes: `PASS`, `FAIL` and `INCONCLUSIVE/SETUP_FAIL`. Privacy sweeps are case-insensitive and look for variants. A sample ordered by path cannot be used to estimate proportions. A reproduction protocol is not valid until it has produced at least one red result with the fix turned off. A dependency error is reproduced in the known-good environment before it is blamed on the repo. If the first instrument says "it is clean", confirm with a second, independent instrument.

2. **A silent run needs a probe at the receiver (lesson LL-261).** If the static path is verified end to end and the run is still silent, stop reading code and put a minimal probe on the first line of the receiver, on each side that matters. Every fail-closed guard logs, rate-limited, the reason it dropped the call. First tell "did not arrive" from "arrived and was rejected"; only then go on through the layers.

3. **Prove the change could have run before bisecting (lesson LL-304).** For a suspected regression, show that the changed code ran before the symptom. With no earlier marker, the build number correlating with the bug proves nothing: instrument the callback where the effect is seen and capture the full stack to name the caller. Print the stack line by line. Measured by the knowledge pack (claim `CLAIM-WF-LOG-CUT-129-ONLY`): the 1.29 retail logger cut long messages at about 255 characters, while on 1.30 neither DayZDiag nor the retail server does (the 1.30 retail client was not measured). Bisect the change only when it is proven to run in time and the cause is still open.

## Probe rules

- **Both sides from the first cycle (lesson LL-147).** For any synced-state failure, instrument client and server from the first cycle and confirm the value on the side where the symptom is seen. Treat every difference between the sides as first-class data before proposing a fix.
- **Payload order and length (lesson LL-199).** In client-side probes put time, position and state first; leave raw values and flags for the end. Keep each useful payload under about 225 characters so a logger wrapper cannot cut it.
- **A time stamp on every line (lesson LL-200).** Start each diagnostic line with `t=GetTickTime()`. Estimate the server-to-client clock offset from the median of RPC request and acknowledge pairs, interpolate one series onto the other, and discard samples with too large a gap. What to do with the aligned series is in `measurement-discipline.md`.
- **Prove a probe can be reached before adding fields to it.** When a probe has never printed, do not add fields first. Walk up from its call site to the function entry and evaluate every `return`, `continue`, side guard and state guard in the real scenario. Then search for the probe's marker in both the server and the client logs; a probe can be silent only on the side you are looking at. Add instrumentation only after the existing probe is shown to run and its fields fail to tell the cases apart. If a guard exits first, move the probe or exercise a state that reaches it. A probe behind a guard it cannot pass fails because of where it is, not because of what it measures.
- **Probe independence and time order.** Before settling a bug with a run-time probe, prove that the measured quantity is independent of the transform or constant it is compared with. A world-space point computed by applying the entity's transform to a fixed model point is not an independent observation of that transform. Treat an exactly round ratio, a value equal to a model constant, or a field that is zero in every sample as an alarm about the probe before using it as evidence. Check selection and memory-point names in the source model. Time-series analysis keeps the order: plain "minimum to maximum" arithmetic reports a descent as an ascent when the maximum came first. Report ordered intervals and unrounded values.
- **Attribute an engine-channel error to its emitter.** An RPT line in `RESOURCES`, `MATERIAL` or `PHYSICS` can come from a diagnostic call in the mod, not from the engine's own asset load. Before using such a line as root-cause evidence:
  1. Search the mod for every API that can open or inspect the named resource.
  2. Match the RPT against the script log of the same run. Matching counts, inputs and instance numbers are the emitter's signature.
  3. Compare the delay with the mod's own `CallLater` intervals.
  4. Find positive proof of the load, such as a non-empty resolved `GetShapeName()` or a later warning that could only come from walking the shape.

  A probe that cannot finish logs an explicit inconclusive reason and its input. It must not leave an unexplained engine-channel error that can be mistaken for a product symptom.

## Layer 7: component bisection

**When.** The six layers have not isolated the cause, and the symptom is **binary**: pass or fail, visible or invisible, the action shows or does not, a centre of mass of zero or not.

**Procedure** (described for a multi-LOD `.p3d`; it works the same for a mod with several modules or a pipeline with several phases):

1. **List the separable components.**
   - A `.p3d`: each LOD (Visual, Geometry, Fire Geometry, View Geometry, LandContact, Memory, Shadow).
   - A mod: each sub-module (a modded class, an RPC, a layout, an animation, a particle).
   - A pipeline: each phase (extract, assemble, bake, binarize, PBO, deploy).
2. **Build a hybrid of control and test:** half A from the one that works, half B from the one that fails. For a `.p3d`, copy the control model and replace its Fire Geometry and View Geometry LODs with the test model's, keeping the rest. For a mod, inherit in `config.cpp` from the control module and override only the members of the suspect test module.
3. **Reproduce the symptom on the hybrid.** If it fails, the bug is in half B; if it passes, the bug is in half A. Recurse into that half.
4. **Repeat** until one component is isolated. N components take about log2(N) experiments (3 LODs: 2 bisections; 8 sub-modules: 3).
5. **Only then** read the mechanism inside the isolated component and name the root cause as a `path:line`. Bisection isolates the component; naming the cause still means reading the code, not stopping at "it is in component X".

**What to avoid.** Varying parameters of the suspect component ("what if the mass is not uniform?", "what if the topology is triangles?", "what if the material is metal plate?") before bisecting components. Each variation is a concrete experiment and feels like progress, but if the first suspicion is wrong you spend one experiment per variation without reaching the bug. Bisection confirms or refutes the suspicion in log2(N) experiments.

**Measured case** (the knowledge pack author's LFQuad project, closed 2026-06-02). The vehicle's `.p3d` spawned with a centre of mass of (0,0,0) in the deployed binarized model. All the first evidence pointed at the Geometry LOD (mass, topology, material). Five trial-and-error binarizations ruled out material, mass distribution, topology, skeleton and writer; **two bisection binarizations** (a hybrid of a working vehicle with the LFQuad Geometry LOD, and LFQuad without its Fire Geometry LOD) isolated the cause to the Fire Geometry LOD: a stray mass tag of zeroes there, which binarize took over the Geometry LOD's mass.

**Use it before the bug, too.** For a new path or pipeline (the first skinned export, the first proxy convention, the first crew selection, a fire mode scope in a new `CfgWeapons` class), run a known-good control through the same pipeline before the first iteration on your own asset. Does a vanilla asset already do it? Read it or round-trip it first: read the vanilla config on `P:\` (the knowledge pack reads the vanilla `bin.pbo` config for this), debinarize a vanilla `.p3d` where you have a tool for it (the skills under `dayz-pbo-reverse-engineering` and `dayz-model-pipeline` cover that; `/dayz-p3d-audit` itself reads source models only), or pass a vanilla model through your exporter. If the control fails too, the bug is in the pipeline, not in your asset. Two measured cases this would have cut short: a `Mode_FullAuto` whose scope was shadowed by the vanilla class (visible by reading the vanilla config, not by theorizing about the model or the animation), and a mesh mirrored left to right (caught only when the skeleton was compared with a vanilla one, after about eight sessions of iterating against the FBX rig).

Related lessons: bisect before trial and error (LL-079), the stray Fire Geometry mass tag (LL-080).
