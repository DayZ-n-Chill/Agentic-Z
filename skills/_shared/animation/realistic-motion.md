# Directing realistic motion

How to produce a credible animation and close its integration with honest evidence: measurable motion contracts, gates per stage and evidence states. Open it when motion must look physically believable on the player, hands and weapons, reloads, unjam actions, locomotion, creatures, vehicle occupants, mechanisms or props, and above all for clipping, crossed fingers, overextended joints, fake contact, an object that does not follow the hand, stutter, bad loops, or a clip that looks right in Blender and wrong in game. The director's work sets the acceptance; the Blender and DayZ files keep technical authority.

The motion contract scripts (`sample_blender_motion.py`, `validate_motion_contract.py`, `run_regression_tests.py`) are in `skills/dayz-animation-pipeline/scripts/`; how to run them is in `skills/dayz-animation-pipeline/SKILL.md`.

## Authority boundary

Before acting, read `motion-authority-and-routing.md`.

- Read `blender-mcp-workflow.md` before operating on Actions, rigs, constraints, curves, renders or export from Blender.
- Read the DayZ side of this pack (`README.md` names the file per question) before deciding format, skeleton, export mask, FPS or frame budget, notetracks, anim graph or ASI, compile, wiring or DayZ integration.
- Load the extra domain skill or pack the routing table names for characters, creatures, vehicles, P3D, retargeting or in-game test; then apply the checks in `motion-domain-gates.md`.
- When two of them conflict, the specialized authority wins. Record the divergence and stop the affected gate; do not invent a third rule.

If the request is strictly technical (choosing an `AnimationSource`, registering an `.anm`, explaining an ASI state), the technical file answers it (`model-cfg-animations.md`, `anm-clips.md`, `anim-graphs.md`). This file is for authoring, evaluating or improving motion.

## Domain routing

| Animation | Skills added to the director |
|---|---|
| Player, hands, custom human or infected | The body files of `skills/_shared/wearables/` (`body-rigging.md`, `canonical-bind.md`). For creatures, first verify their actual bind pose and skeleton (1.30 changelog, not yet checked on `P:\`: the engine resolves bone indices by name and the 250-bone limit is gone; see `dayz-1-30-changes.md`). |
| Weapon, reload, unjam or P3D mechanism | The weapon pack, `skills/_shared/weapons/`, when the entity contract changes, plus the relevant P3D or model skill (check the per-weapon bone remap, such as `LugerBoneRemap` at `P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:1621`, and the dedicated `.asi` profile listed in `motion-domain-gates.md`). |
| Occupant, entry or vehicle controls | The vehicle pack, `skills/_shared/vehicles/` (in 1.30: motorbikes on the `MOTO1` and `MOTO2` instances, with two-bone IK on the handlebar). |
| Mocap or external donor | The retargeting skill that applies (`mixamo-retarget.md`); never without a source-to-target bone map. |
| Runtime test | `/dayz-launch-test`, `/dayz-gate` and `/dayz-logwatch`, plus the bridge checks in `skills/dayz-launch-test/references/mcp/`, with their lease and lifecycle rules (Workbench Live Editing; 1.30 changelog, not yet checked on `P:\`). |

`blender-mcp-workflow.md` and the DayZ technical files of this pack stay mandatory for authoring and integration; the skills in the table do not replace them.

## Three checks that never substitute for each other

1. **Full chain:** measuring knuckles and tips does not validate intermediate phalanges. Sample all relevant segments and joints.
2. **Positive contact:** "no penetration" does not mean "gripping". Require a contact pair, a target surface or landmark, and a distance band.
3. **Relative locking:** sharing keyframes or a scalar curve does not prove two elements move together. Measure `T_actor^-1 * T_target` through the whole grip window.

A reproducible visual failure from the user or from the game invalidates any offline `PASS`. Convert it into a fixture before authoring again.

## Gated workflow

### 0. Preserve and observe

- Inspect scene, Actions, current frame, selection, constraints and windows before changing anything.
- Always work from a versioned copy; do not overwrite the source `.blend`.
- If fixing a defect, first reproduce the failure with the current scene and keep that RED evidence.
- Read the project contract (the project's instructions file, product spec, plan and handoff) when one exists.

### 1. Capture the DayZ technical contract

Take the route that applies from the DayZ technical files (`tooling-and-walls.md` names the layers) and record:

- animation type and the authoritative skeleton or rig;
- FPS, duration or frame budget, and loop rules;
- notetracks, events and runtime states;
- included and excluded bones, and the complete moving objects or selections;
- artifacts for export, compile, wiring, build and in-game test.

Do not hardcode 291 frames, 30 FPS or one weapon's notetracks for other animations. Each task gets its own active contract.

### 2. Define acceptance before posing

Read `motion-contract.md` and write a per-task contract that declares only the modules that apply:

- key poses and beats;
- joints, chains and calibrated limits;
- contacts, surfaces and `contact_on..release` windows;
- prohibited collision pairs and permitted contacts;
- objects that must keep their relative transform;
- intentional impact, snap or sliding exceptions;
- the actual entry and exit pose and the in-game states to test.

Tolerances come from a reference, from geometry or from an explicit decision. Never adjust a threshold to make the current candidate pass.

Every contract declares exactly `contract_mode: "diagnostic"` or `contract_mode: "production"`; a missing or unknown value is an error. A contract that can grant `OFFLINE_PASS` uses `production`. Each check declares its provenance (`source_kind`, `source`, `verified_date`, `method`), and any `segment_clearance` check needs shared geometric provenance for the capsule radii. A `diagnostic` contract may reproduce a failure, but its `eligible_for_offline_pass` is always false.

For a continuous window of contact, collision, locking, order, joint range or continuity, use a consecutive `frame_range` with `step: 1`; production requires it. A sparse list of golden poses does not prove what happens between them.

### 3. Blocking

With `blender-mcp-workflow.md`, author only the golden poses: start, anticipation, contact, maximum effort, release, recovery and end.

- Render each pose in an on-axis view and at least one oblique view.
- Validate anatomy, silhouette, contact and collision before interpolating.
- For hands, read `motion-biomechanics.md` and evaluate all five fingers, wrist, forearm, elbow, shoulder and clavicle when they are part of the gesture.
- Do not advance to spline while a key pose clips, is overextended or misses its target.

### 4. Motion and effort

- Apply blocking, then spline, then polish through `blender-mcp-workflow.md`.
- Use timing, spacing, arcs, anticipation, overlap, moving holds and settle according to physical intent.
- Validate position, rotation, velocity, acceleration and jerk on the relevant elements.
- Mark an intentional snap or impact with a declared window; outside it, a spike is stutter.
- In mechanisms, move the full hierarchy or functional selection, not only the visual piece one camera sees.

### 5. Offline audit

Run the sampler in Blender, then the validator (see "How to run"). In addition to the JSON:

- review the full video at real speed;
- review multi-angle renders of contact, extremes, transitions and recovery;
- look for clipping between keyframes, not only on key frames;
- check start and end against the actual runtime entry pose.

### 6. Export and integrate

- Hand the Blender export to `blender-mcp-workflow.md`, following its active contract.
- Hand the artifact on for compile, ASI and config, build and deploy (`weapon-anim-blender.md`, `anm-clips.md`).
- Verify the artifact that was actually deployed, not only the source. In DayZ 1.30 the animation graph is a set of `.agf` subgraph files listed by an `AnimSrcGraph` `.agr` index, and `.asi` files use the `AnimSetInstanceSource` class (`dayz-1-30-changes.md`).
- Do not say Workbench, DayZATool, Blender MCP or DayZ ran when the session holds no evidence of that run.

### 7. In-game gate

Read `motion-evidence.md`.

- Test the stances, cameras and states that can alter IK or blending. 1.30 changelog, not yet checked on `P:\`: the Workbench Animation Editor can Live Edit graphs on a running client, which helps debug transitions.
- Review the RPT and compare timing, contact, clipping and mechanical states against the contract.
- If the game contradicts Blender, the game wins and the case becomes a regression.
- If the environment does not allow the test, end in `MANUAL_REQUIRED`, not PASS.

## Running the checks

Sample the scene inside Blender, then validate the report with plain Python. The commands, the scripts' outputs and their exit codes are in `skills/dayz-animation-pipeline/SKILL.md`. A validator exit of 0 means every required check passes, 1 that one or more fail, and 2 that the contract or sample is invalid and there is no quality verdict.

## Output states

- `FAIL`: at least one mandatory gate fails.
- `OFFLINE_PASS`: contract, scene, audit, renders and offline artifact approved; game test pending.
- `MANUAL_REQUIRED`: the next gate needs an action or tool that is unavailable.
- `IN_GAME_PASS`: the deployed build and the DayZ behaviour are verified with evidence.

Always report which gates ran, what evidence exists, what was left out and why.

## Regression policy

When a new defect appears:

1. freeze the failed scene as read-only input;
2. write a minimal fixture that fails for that reason;
3. demonstrate RED;
4. implement or tighten the check;
5. demonstrate GREEN with a corrected sample, so the test is not tautological;
6. only then modify the production animation.

The reusable regression suite (`run_regression_tests.py`) runs the unit tests, the Blender sampler test, the synthetic fixtures and, on request, a real case. Without Blender the sampler step reports `SKIP_NO_BLENDER`, which is not a PASS. The fixtures are one positive report and contract, eleven one-fault negative cases, and the contract of a real case (`unjam-real-case.contract.json`, a bolt-handle unjam whose fingers overlapped, whose fist missed the handle and whose hand did not track it). The real case's `.blend` is not part of this repo, so without it the correct result is `SKIP_REAL_FIXTURE`, not PASS.

## References

| Question | Read |
|---|---|
| Which file or skill decides what, how is a request routed, what does each side hand over? | `motion-authority-and-routing.md` |
| What do the report and the contract look like, and what does each check type measure? | `motion-contract.md` |
| What makes a hand, wrist, arm, grip or collision believable? | `motion-biomechanics.md` |
| Which extra checks apply to a player action, a weapon in hands, locomotion, a creature, a vehicle occupant, a prop or a simulation? | `motion-domain-gates.md` |
| What counts as evidence at each step, what goes to the DayZ pipeline, what does each output state mean? | `motion-evidence.md` |
| What did DayZ 1.30 change for animation, what breaks from 1.29, what is the migration checklist? | `dayz-1-30-changes.md` |

## Stop conditions

Stop and ask for the missing decision or evidence when:

- no input or output reference exists and a choice would alter the choreography;
- the current pipeline and a reference disagree on skeleton, export mask or runtime state;
- the full mechanical part cannot be identified;
- a tolerance can only be chosen by looking at the candidate it is meant to judge;
- the offline gate passes but the visual or in-game review fails;
- the integration test needs a tool or permission that is unavailable.

## Building, testing and publishing the mod

When this work has to end in a mod that builds, loads and ships (`config.cpp` and `CfgMods`, `requiredAddons`, the PBO, a boot on a local server, the release pack), use `/dayz-lint`, `/dayz-build-pbo`, `/dayz-gate` and `/dayz-release-pack`, and `/dayz-mod-dev` for the mod's structure.
