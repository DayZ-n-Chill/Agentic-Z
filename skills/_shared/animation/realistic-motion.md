# Realistic motion

How to make an animation look physically believable and prove it, from the first contract to the in game test. Open it for motion on the player, hands and weapons, reloads and unjams, locomotion, creatures, vehicle occupants and props, and above all for clipping, crossed fingers, overextended joints, a hand that misses its grip, a held object that does not follow, stutter, bad loops, or a clip that looks right in Blender and wrong in game.

It sets the acceptance; the Blender and DayZ files keep the technical facts (`motion-authority-and-routing.md`). The checker scripts `sample_blender_motion.py`, `validate_motion_contract.py` and `run_regression_tests.py` are in `skills/dayz-animation-pipeline/scripts/`, and `skills/dayz-animation-pipeline/SKILL.md` says how to run them.

## Before you start

- Read `blender-mcp-workflow.md` before touching Actions, rigs, constraints, curves, renders or export in Blender.
- Read the DayZ file for the question (this pack's `README.md` names it) before deciding format, skeleton, export mask, frame rate and budget, notetracks, graph or instance file, or wiring.
- Add the domain pack for the kind of animation, then the checks for it in `motion-domain-gates.md`:

| Animation | Add |
|---|---|
| Player, hands, custom human or infected | `_shared/wearables/references/body-rigging.md` and `_shared/wearables/references/canonical-bind.md`. For a creature, check its real bind pose and skeleton first (1.30 changelog, not checked on `P:\`: bones are found by name and the 250 bone limit is gone; `dayz-1-30-changes.md`). |
| Weapon, reload, unjam or `.p3d` mechanism | `_shared/weapons/` when the item's config changes, and the model tools. Check the weapon's bone remap, such as `LugerBoneRemap` (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:1621`), and its own instance file (`motion-domain-gates.md`). |
| Occupant, boarding or vehicle controls | `_shared/vehicles/` (1.30: motorbikes on `MOTO1` and `MOTO2` with two bone handlebar IK). |
| Mocap from outside | `mixamo-retarget.md`; never without a source to target bone map. |
| In game test | `/dayz-launch-test`, `/dayz-gate` and `/dayz-logwatch`; the DayZ facts behind an in-game check are listed in `skills/dayz-launch-test/references/README.md`. |

A purely technical question (which `AnimationSource`, how to register an `.anm`, what an instance state means) is answered by `model-cfg-animations.md`, `anm-clips.md` or `anim-graphs.md`, not here.

## Three checks that never stand in for each other

1. The whole chain: knuckles and tips passing says nothing about the middle finger joints. Sample every joint involved.
2. Real contact: no overlap is not a grip. Require a contact pair, a target surface and a distance band.
3. A locked grip: shared keys or one curve do not prove two things move together. Measure `T_actor^-1 * T_target` through the whole grip.

A failure the user or the game can reproduce cancels any offline pass. Turn it into a test case before you key again.

## The steps

1. Look before you change. Inspect the scene, Actions, current frame, selection, constraints and windows. Work on a versioned copy and never overwrite the source `.blend`. When fixing a defect, reproduce it first and keep that failing result. Read the project's instructions, spec, plan and handoff when they exist.
2. Take the DayZ route. From the DayZ files (`tooling-and-walls.md` names the layers) record the animation type and skeleton, frame rate, length or frame budget and loop rules, notetracks, events and states, the bones and moving parts included and left out, and the files to export, compile, wire, build and test. Never carry 291 frames, 30 fps or one weapon's notetracks over to another clip.
3. Write the acceptance before posing. Following `motion-contract.md`, declare only what applies: key poses and beats, joints and limits, contacts with their surfaces and windows, forbidden collisions and allowed contacts, objects that keep their relative transform, intended impacts, snaps or slides, and the real start and end poses and in game states. Tolerances come from a reference, from geometry or from a recorded decision; never loosen one to pass the current attempt. Set `contract_mode` to `diagnostic` or `production`; only `production` can give `OFFLINE_PASS`, and then every check names its source, and `segment_clearance` checks name the source of their capsule radii. Continuous windows use a consecutive `frame_range` with `step: 1`; a few sampled poses say nothing about the frames between them.
4. Block the key poses: start, anticipation, contact, most effort, release, recovery and end. Render each straight on and from at least one oblique view. Check anatomy, silhouette, contact and collision before interpolating; for hands, follow `motion-biomechanics.md` across all five fingers, wrist, forearm, elbow, shoulder and clavicle. Do not move on while a key pose clips, overextends or misses.
5. Add motion and effort through `blender-mcp-workflow.md`: blocking, then spline, then polish. Use timing, spacing, arcs, anticipation, overlap, moving holds and settle as the physics asks. Check position, rotation, velocity, acceleration and jerk. Declare a window for any intended snap or impact; a spike outside it is stutter. On a mechanism move the whole hierarchy, not only the piece one camera sees.
6. Check offline. Run the sampler in Blender, then the validator. Then watch the full video at real speed, review renders of contact, extremes, transitions and recovery from several angles, look for clipping between keys, and compare start and end with the real in game entry pose.
7. Export and wire. The Blender export follows `blender-mcp-workflow.md`; compile, instance file and config, build and deploy follow `weapon-anim-blender.md` and `anm-clips.md`. Check the file that was actually deployed. In 1.30 the graph is `.agf` subgraphs listed by an `.agr` index and `.asi` files use `AnimSetInstanceSource` (`dayz-1-30-changes.md`). Never say Workbench, DayZATool, the Blender MCP or the game ran unless this session shows it.
8. Test in game, as `motion-evidence.md` says. Test the stances, cameras and states that can change IK or blending; Workbench Live Editing on a running client helps with transitions (1.30 changelog). Read the RPT and compare timing, contact, clipping and mechanical states with the contract. When the game disagrees with Blender the game wins and the case becomes a test. When the test cannot run here, end in `MANUAL_REQUIRED`, not a pass.

## Running the checks

Sample inside Blender, then validate with plain Python; the commands are in `skills/dayz-animation-pipeline/SKILL.md`. The validator exits 0 when every required check passes, 1 when any fails, and 2 when the contract or sample is invalid and there is no verdict.

## Results

- `FAIL`: a required check fails.
- `OFFLINE_PASS`: contract, scene, checks, renders and offline file pass; the game test is still open.
- `MANUAL_REQUIRED`: the next step needs an action or tool that is not available.
- `IN_GAME_PASS`: the deployed build and its behaviour in DayZ are proven.

Always report which checks ran, what evidence exists, what was left out and why.

## When a new defect appears

1. Keep the failing scene as read only input.
2. Write the smallest test case that fails for that reason, and show it fail.
3. Add or tighten the check.
4. Show a corrected sample passes, so the check is not circular.
5. Only then change the real animation.

`run_regression_tests.py` runs the unit tests, the Blender sampler test, the synthetic cases and, on request, a real case. Without Blender the sampler step reports `SKIP_NO_BLENDER`, which is not a pass. The cases are one good report and contract, eleven bad ones with one fault each, and the contract of a real bolt handle unjam whose fingers overlapped, whose fist missed the handle and whose hand did not follow it (`unjam-real-case.contract.json`). That case's `.blend` is not in this repo, so without it the right result is `SKIP_REAL_FIXTURE`, not a pass.

## Stop and ask

Stop and ask for the missing decision or evidence when:

- there is no reference and the choice would change the choreography;
- the pipeline and a reference disagree on skeleton, export mask or state;
- the whole mechanical part cannot be identified;
- a tolerance could only be chosen by looking at the attempt it judges;
- the offline checks pass but the picture or the game fails;
- the in game test needs a tool or permission that is missing.

## Related files

| Question | File |
|---|---|
| Who decides what, and what each side hands over | `motion-authority-and-routing.md` |
| The report and contract formats and every check type | `motion-contract.md` |
| What makes a hand, wrist, arm, grip or collision believable | `motion-biomechanics.md` |
| Extra checks for a player action, weapon, locomotion, creature, occupant, prop or simulation | `motion-domain-gates.md` |
| What counts as evidence, the handoff to the pipeline, the result states | `motion-evidence.md` |
| What 1.30 changed for animation | `dayz-1-30-changes.md` |

When the work has to end in a mod that builds, loads and ships, use `/dayz-lint`, `/dayz-build-pbo`, `/dayz-gate` and `/dayz-release-pack`, and `skills/dayz-launch-test/references/mod-loop.md` for the mod's layout.
