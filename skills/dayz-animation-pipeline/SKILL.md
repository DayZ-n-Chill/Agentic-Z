---
name: dayz-animation-pipeline
description: "Runs the DayZ animation tools: writes a model.cfg from one JSON description, writes and inspects SEAnim and RTM files, solves a vehicle rider pose from model anchors, builds the weapon animation and grip viewers, samples a Blender scene against a motion contract and validates it, and retargets Mixamo clips inside Blender (experimental). Use when one of these scripts has to run. The knowledge behind them (model.cfg animations, graphs, clips, items and weapons in hands, rider poses, Blender, realistic motion, building doors) is the animation pack, skills/_shared/animation/README.md."
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-animation-pipeline

The scripts of the animation work. What each step means, which route fits a request and every vanilla fact behind it are in the animation pack: start at `skills/_shared/animation/README.md`. What an agent delivers and what the user runs (text, interchange files, GUI tools and the game) is in `skills/_shared/animation/tooling-and-walls.md`.

Follow `skills/_shared/dayz-conventions.md`. The scripts read the files named on their command line and write their results or a scratch folder; none needs DayZ Tools or the game, so none gates on `/dayz-preflight` (the stated exception in `dayz-conventions.md`).

## Scripts

All in `<skill-dir>\scripts\`. The viewer steps pass files through the folder named by `DAYZ_ANIM_SCRATCH` (default `<tempdir>\dayz-anim-pipeline`). The two Blender steps take the rig FBX after `--` on the command line, or from `DAYZ_ANIM_RIG_FBX`; `extract_weapon.py` takes the `.p3d` as its argument, or from `DAYZ_ANIM_WEAPON_P3D`. Run a Blender step as `blender -b --python-exit-code 1 --python <script> -- <rig.fbx>` and stop at the first non-zero exit: without that flag an uncaught Python error still exits 0.

| Script | Needs | What it does | Read first |
|---|---|---|---|
| `gen_model_cfg.py` | Python | Writes a `model.cfg` from one JSON description of bones and animations (`python gen_model_cfg.py spec.json > model.cfg`; `--self-test` prints a sample). Warns on an animation type or key outside its checked set and on a selection that is not a declared bone. | `model-cfg-animations.md` |
| `ik_pose_to_seanim.py` | Python | Solves a rider pose from the anchors in an `anchors.json` (seat, two grips, two feet) with two bone IK and writes one SEAnim per variant. The files hold solved joint positions and identity rotations: the step that turns positions into rotations against a rest pose is not written, with or without `--rest-pose`, so the output is a position reference, not a clip the game can play. | `rider-pose-solver.md` |
| `seanim_writer.py` | Python | The older SEAnim writer used by the two exporters here. New format work uses `scripts/tools/dayz-animation-formats/` (below). | `anm-clips.md` |
| `seanim_export.py` | Python | Turns a viewer animation JSON (local quaternions per bone and frame) into SEAnim through the bone frame map of the rig it reads. For weapon bone and partial tracks only, not full body actions. | `weapon-anim-viewer.md` |
| `fbx_extract.py` | Blender | Dumps the Bohemia character rig FBX to `rig_raw.json`: rest matrices, parents, lengths, the body mesh and every empty. | `weapon-anim-viewer.md` |
| `extract_empties.py` | Blender | Writes the helper empties' world matrices to `empties_armworld.json`. Exits 1 and writes nothing when the FBX has no `RightHand_Dummy`. | `weapon-anim-viewer.md` |
| `build_rig_dayz.py` | Python, numpy | Converts the two JSON files to `rig_dayz.json` in the viewer's frame. That frame is right handed, so its coordinates written into a `.p3d` as they are land mirrored. | `blender-headless-authoring.md` |
| `extract_weapon.py` | Python, py3d | Extracts an MLOD weapon's first visual LOD and memory points to `weapon.json`. Stops when the installed py3d is not the DayZ fork. | `weapon-anim-viewer.md` |
| `build_viewer.py` | Python, `viewer_core.py` | Builds the weapon animation viewer page from `rig_dayz.json` and `weapon.json` (`python build_viewer.py [out.html] [--viewer-core <path>]`). It looks for the viewer core under `scripts/tools/dayz-3d-viewer/` and then `skills/_shared/`. The page loads Three.js from a CDN. | `weapon-anim-viewer.md` |
| `weapon_grip_viewer.py` | Python, py3d, `viewer_core.py` | Compares a custom weapon's memory points, bore line and hand zones with a vanilla reference (both MLOD) and writes a viewer page plus an optional JSON report. The page loads Three.js from a CDN. | `weapon-in-hands.md` |
| `sample_blender_motion.py` | Blender | Reads a motion contract's landmarks, transforms and segments from a scene, frame by frame, into a neutral JSON report. Prints `BLENDER_MOTION_SAMPLING_ERROR=...` and exits 2 on invalid input. | `motion-contract.md` |
| `validate_motion_contract.py` | Python, standard library only | Report plus contract in, deterministic audit JSON out. Exit 0: every required check passes; 1: valid input, one or more required checks fail; 2: invalid contract, sample or execution, no verdict, reason on stderr as `MOTION_CONTRACT_ERROR=...`. | `realistic-motion.md` |
| `run_regression_tests.py` | Python; starts Blender when it finds one | Unit tests, the Blender sampler test, the synthetic fixtures in `fixtures\` and, with `--real-fixtures`, a real case. Prints `DAYZ_ANIMATION_REGRESSION=` and a JSON summary and exits 0, or `DAYZ_ANIMATION_REGRESSION_ERROR=...` and exits 1. | `realistic-motion.md` |
| `retargeting.py`, `bone_matching.py` | Blender, through the Blender MCP server | Experimental. Fuzzy bone matching and Mixamo retargeting onto a Blender rig, loaded into a live Blender session. | `mixamo-retarget.md` |

The file names in the last column are in `skills/_shared/animation/`.

### py3d

The `.p3d` scripts need the DayZ fork of py3d (`scripts/tools/py3d/`, version 1.6.0 or later, `py3d.IS_DAYZ_FORK` true). `pip install py3d` installs an unrelated point cloud library from PyPI, and every geometry read then returns plausible garbage, so check the flag before trusting a result. To install the fork from a built wheel, run `skills/dayz-model-tools/scripts/install_py3d.py` (`--dry-run` shows what it would do).

```cmd
python -c "import py3d; assert getattr(py3d, 'IS_DAYZ_FORK', False), py3d.__file__"
```

### SEAnim and RTM files

New format work uses the strict package in `scripts/tools/dayz-animation-formats/`: `read_seanim`, `write_seanim`, `read_rtm`, `write_rtm` and their `_bytes` forms, and the inspector:

```cmd
cd scripts\tools\dayz-animation-formats
python -m dayz_animation_formats inspect <file.seanim or file.rtm>
```

It handles full SEAnim v1 (channels, modifiers, notes, float32 and float64) and one unbinarized `RTM_0101` block with an optional `RTM_MDAT` before it. It refuses unknown flags and blocks, bad counts, truncated files, invalid names, non-finite values, wrong RTM bone order and trailing bytes. A file that round-trips through it is not proof the game accepts it.

### Motion contract check

Sample the scene inside Blender, then validate the report with plain Python. `BLENDER_EXE` holds the path to the Blender executable.

```cmd
"%BLENDER_EXE%" --background "<scene.blend>" --python "<skill-dir>\scripts\sample_blender_motion.py" -- --contract "<contract.json>" --output "<report.json>"
python "<skill-dir>\scripts\validate_motion_contract.py" --report "<report.json>" --contract "<contract.json>" --output "<audit.json>"
python "<skill-dir>\scripts\run_regression_tests.py" [--real-fixtures] [--output <summary.json>]
```

The regression run takes Blender from `BLENDER_EXE`, or `blender` on `PATH`; with neither, the sampler step reports `SKIP_NO_BLENDER`, which is not a PASS. The real case needs its `.blend` in `DAYZ_ANIM_REAL_CASE_BLEND`; that scene is not in this repo, so without it the result is `SKIP_REAL_FIXTURE`, not PASS.

### Mixamo retarget (experimental)

Load both modules once per Blender session through the MCP server's `execute_blender_code`:

```python
import sys
sys.path.insert(0, r"<skill-dir>\scripts")
from retargeting import *
```

Then follow the two phase run, the known gaps and the fixture in `skills/_shared/animation/mixamo-retarget.md`. Never bake straight off the automatic map.

### Wrappers

Outside an agent session, `scripts\dayz\anim-model-cfg.bat` runs `gen_model_cfg.py`, and `scripts\dayz\motion-contract.bat` and `scripts\dayz\motion-regression.bat` run `validate_motion_contract.py` and `run_regression_tests.py`, each with the same arguments.

## Building, testing and shipping

Build the mod with `/dayz-build-pbo`, run it with `/dayz-launch-test`, and read the logs with `/dayz-logwatch`; `skills/dayz-launch-test/references/mod-loop.md` has the whole loop from `config.cpp` to the Workshop. The only acceptance for an animation is seeing it play in game with no bone errors in the RPT.
