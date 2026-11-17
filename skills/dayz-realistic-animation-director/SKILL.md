---
name: dayz-realistic-animation-director
description: "Directs the creation, correction, polish, export, integration and verification of realistic DayZ animation from start to finish, with measurable motion contracts and honest evidence states. Use when motion must feel physically believable on the player, hands and weapons, reloads, unjam and unstuck actions, locomotion, creatures, vehicle occupants, mechanisms, props or simulations, and especially for clipping, crossed fingers, overextended joints, fake contact, objects that do not follow the hand, stutter, bad loops or Blender-versus-in-game differences. It orchestrates blender-animation for authoring and dayz-animation-pipeline for engine contracts; it does not replace purely technical questions about config, ASI, skeletons or export. Spanish triggers: \"animación realista\", \"dedos cruzados\", \"contacto falso\", \"el objeto no sigue la mano\"."
argument-hint: "--report <report.json> --contract <contract.json> --output <audit.json>"
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-realistic-animation-director

Produce a credible animation and close its integration with honest evidence. This skill directs the work; the Blender and DayZ skills keep technical authority.

Follow `skills/_shared/dayz-conventions.md`. The three scripts read JSON files and a Blender scene; they never touch `P:\`, DayZ Tools or the game, so they do not gate on `/dayz-preflight`.

## Authority boundary

Before acting, read `references/authority-and-routing.md`.

- Load `blender-animation` before operating on Actions, rigs, constraints, curves, renders or export from Blender.
- Load `dayz-animation-pipeline` before deciding format, skeleton, export mask, FPS or frame budget, notetracks, anim graph or ASI, compile, wiring or DayZ integration.
- Load the extra domain skill the routing table names for characters, creatures, vehicles, P3D, retargeting or in-game test; then apply the checks in `references/domain-gates.md`.
- When two of them conflict, the specialized authority wins. Record the divergence and stop the affected gate; do not invent a third rule.

If the request is strictly technical (choosing an `AnimationSource`, registering an `.anm`, explaining an ASI state), `dayz-animation-pipeline` is the primary skill. Use this skill when authoring, evaluating or improving motion.

## Domain routing

| Animation | Skills added to the director |
|---|---|
| Player, hands, custom human or infected | `dayz-characters`. For creatures, first verify their actual bind pose and skeleton (1.30 changelog, not yet checked on `P:\`: the engine resolves bone indices by name and the 250-bone limit is gone; see `references/dayz-1-30-animation-direction.md`). |
| Weapon, reload, unjam or P3D mechanism | `dayz-weapons` when the entity contract changes, plus the relevant P3D or model skill (check the per-weapon bone remap, such as `LugerBoneRemap` at `P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:1621`, and the dedicated `.asi` profile listed in `references/domain-gates.md`). |
| Occupant, entry or vehicle controls | `dayz-vehicles` (in 1.30: motorbikes on the `MOTO1` and `MOTO2` instances, with two-bone IK on the handlebar). |
| Mocap or external donor | The retargeting skill that applies (`mixamo-retarget`); never without a source-to-target bone map. |
| Runtime test | `/dayz-launch-test`, `/dayz-gate` and `/dayz-logwatch`, or `/dayz-test-ingame` and `/dayz-mcp-verify`, with their lease and lifecycle rules (Workbench Live Editing; 1.30 changelog, not yet checked on `P:\`). |

`blender-animation` and `dayz-animation-pipeline` stay mandatory for authoring and integration; the skills in the table do not replace them.

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

Ask `dayz-animation-pipeline` for the route that applies and record:

- animation type and the authoritative skeleton or rig;
- FPS, duration or frame budget, and loop rules;
- notetracks, events and runtime states;
- included and excluded bones, and the complete moving objects or selections;
- artifacts for export, compile, wiring, build and in-game test.

Do not hardcode 291 frames, 30 FPS or one weapon's notetracks for other animations. Each task gets its own active contract.

### 2. Define acceptance before posing

Read `references/motion-quality-contract.md` and write a per-task contract that declares only the modules that apply:

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

With `blender-animation`, author only the golden poses: start, anticipation, contact, maximum effort, release, recovery and end.

- Render each pose in an on-axis view and at least one oblique view.
- Validate anatomy, silhouette, contact and collision before interpolating.
- For hands, read `references/biomechanics-and-contact.md` and evaluate all five fingers, wrist, forearm, elbow, shoulder and clavicle when they are part of the gesture.
- Do not advance to spline while a key pose clips, is overextended or misses its target.

### 4. Motion and effort

- Apply blocking, then spline, then polish through `blender-animation`.
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

- Hand the Blender export to `blender-animation`, following its active contract.
- Hand the artifact to `dayz-animation-pipeline` for compile, ASI and config, build and deploy.
- Verify the artifact that was actually deployed, not only the source. In DayZ 1.30 the animation graph is a set of `.agf` subgraph files listed by an `AnimSrcGraph` `.agr` index, and `.asi` files use the `AnimSetInstanceSource` class (`references/dayz-1-30-animation-direction.md`).
- Do not say Workbench, DayZATool, Blender MCP or DayZ ran when the session holds no evidence of that run.

### 7. In-game gate

Read `references/evidence-and-integration.md`.

- Test the stances, cameras and states that can alter IK or blending. 1.30 changelog, not yet checked on `P:\`: the Workbench Animation Editor can Live Edit graphs on a running client, which helps debug transitions.
- Review the RPT and compare timing, contact, clipping and mechanical states against the contract.
- If the game contradicts Blender, the game wins and the case becomes a regression.
- If the environment does not allow the test, end in `MANUAL_REQUIRED`, not PASS.

## How to run

Sample the scene inside Blender, then validate the report with plain Python. `BLENDER_EXE` holds the path to the Blender executable.

```cmd
"%BLENDER_EXE%" --background "<scene.blend>" --python "<skill-dir>\scripts\sample_blender_motion.py" -- --contract "<contract.json>" --output "<report.json>"
python "<skill-dir>\scripts\validate_motion_contract.py" --report "<report.json>" --contract "<contract.json>" --output "<audit.json>"
```

| Script | Runs in | What it does |
|---|---|---|
| `sample_blender_motion.py` | Blender's Python (`bpy`) | Reads the contract's landmarks, transforms and segments from the scene, frame by frame, into a neutral JSON report. Prints `BLENDER_MOTION_SAMPLING_ERROR=...` and exits 2 on invalid input. |
| `validate_motion_contract.py` | Any Python 3, standard library only | Report plus contract in, deterministic audit JSON out. |
| `run_regression_tests.py` | Any Python 3; starts Blender when it finds one | Unit tests, the Blender sampler test, the synthetic fixtures and, on request, a real fixture. |

Validator exit codes:

- `0`: all required checks pass;
- `1`: valid input, one or more required checks fail;
- `2`: invalid contract, sample or execution; no quality verdict. The reason is on stderr as `MOTION_CONTRACT_ERROR=...`.

Outside an agent session, `scripts\dayz\motion-contract.bat` and `scripts\dayz\motion-regression.bat` run `validate_motion_contract.py` and `run_regression_tests.py` with the same arguments.

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

Run the reusable suite with:

```cmd
python "<skill-dir>\scripts\run_regression_tests.py" [--real-fixtures] [--output <summary.json>]
```

It prints `DAYZ_ANIMATION_REGRESSION=` followed by a JSON summary and exits 0, or prints `DAYZ_ANIMATION_REGRESSION_ERROR=...` and exits 1 when a fixture does not give its expected verdict. Blender comes from `BLENDER_EXE`, or from `blender` on `PATH`; with neither, the sampler step reports `SKIP_NO_BLENDER`, which is not a PASS.

The fixtures sit in `<skill-dir>\scripts\fixtures\`: one positive report and contract, eleven one-fault negative cases, and the contract of a real case (`sr2m-v44.contract.json`, a bolt-handle unjam whose fingers overlapped, whose fist missed the handle and whose hand did not track it). To include the real case, set `SR2M_V44_BLEND` to its `.blend` and add `--real-fixtures`. That scene is not part of this repo, so when the variable is missing the correct result is `SKIP_REAL_FIXTURE`, not PASS.

## References

| Question | Read |
|---|---|
| Which skill decides what, how is a request routed, what does each side hand over? | `references/authority-and-routing.md` |
| What do the report and the contract look like, and what does each check type measure? | `references/motion-quality-contract.md` |
| What makes a hand, wrist, arm, grip or collision believable? | `references/biomechanics-and-contact.md` |
| Which extra checks apply to a player action, a weapon in hands, locomotion, a creature, a vehicle occupant, a prop or a simulation? | `references/domain-gates.md` |
| What counts as evidence at each step, what goes to the DayZ pipeline, what does each output state mean? | `references/evidence-and-integration.md` |
| What did DayZ 1.30 change for animation, what breaks from 1.29, what is the migration checklist? | `references/dayz-1-30-animation-direction.md` |

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
