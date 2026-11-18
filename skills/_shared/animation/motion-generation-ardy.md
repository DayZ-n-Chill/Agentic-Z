# Generated locomotion with ARDY (experimental)

**Experimental.** Nothing here has produced a clip that plays in DayZ. The setup was run on one machine; the route into the game is a plan with no step tested.

A setup and usage guide; no script for it ships in this repo, and nothing here runs against `P:\`, DayZ Tools or the game. What it says about ARDY describes the project's own pages and one install on one machine. None of it is checkable on `P:\`: re-check the project pages listed below before relying on a detail, and do not trust videos or marketing.

## What ARDY does not solve (read before investing time)

The goal is **full-body survivor locomotion** (running, jumping, vaulting, scene traversal), not weapon animation.

The real bottleneck of a weapon grip in DayZ is geometric parity between the weapon model and the reference `.anm` on the `Weapon_Root` and `RightHand_Dummy` bones. Both are in the vanilla bone list of the player skeleton `player_testing.xob`: `RightHand_Dummy` at `P:\DZ\anims\cfg\skeletons.anim.xml:115` and `Weapon_Root` at `P:\DZ\anims\cfg\skeletons.anim.xml:254`. The parity problem was measured in game on one weapon project; that result is not checkable on `P:\`. ARDY works on a full-body "core" skeleton (its bone count is unconfirmed; count the joints in the first generated `.npz`) with hand control as an end-effector position. It has no concept of held object geometry, individual fingers or the DayZ ASI and IK system. Bringing ARDY to a weapon grip problem would be solving the wrong layer. For grip work use `realistic-motion.md` and `weapon-in-hands.md`.

## What it is

**ARDY** is "Autoregressive Diffusion with Hybrid Representation for Interactive Human Motion Generation" (NVIDIA, SIL research lab). It is a two-stage autoregressive transformer denoiser: stage 1 predicts the global root motion, stage 2 predicts the body motion conditioned on the root. It supports sparse kinematic constraints in time and joints. Real-time control: online text prompts, root trajectories and waypoints, full-body keyframes, end-effector joint positions and rotations, mouse waypoint editing, keyboard velocity commands and long-horizon goals.

- Repo: https://github.com/nv-tlabs/ardy
- Landing page and paper: https://research.nvidia.com/labs/sil/projects/ardy/
- Models: https://huggingface.co/collections/nvidia/ardy
- Read the code's and the model weights' terms before redistributing anything derived from them.

## VRAM budget (read before launching anything)

The text encoder alone (Llama-3-8B-Instruct, bf16) asks for about **14 GB**; the README also offers CPU text-encoder options (`cpu / bfloat16`, `cpu / float32`) that encode prompts more slowly but need less VRAM. The total is an estimate, not stated by the project: 16 to 18 GB at minimum and about **24 GB for smooth real time** (unverified). A 24 GB card such as an RTX 3090 has no margin at all. WSL2 adds its own VRAM overhead on top. Expect a real risk of running out of memory in real-time mode.

Mitigations to try, in order, when memory runs out:

1. Launch `run_text_encoder_server.py` in a separate process, which shows its footprint alone before the rest of the model is added.
2. Close every other process that reserves VRAM (a browser with GPU acceleration, another loaded model) before launching the demo.
3. If it still does not fit smoothly, generate offline from the command line instead of the real-time demo: `python "$ARDY_SCRIPTS/generate.py" "<prompt>" --model core` (with `ARDY_SCRIPTS` set as in "Launch the interactive demo" below), run from the root of the ARDY clone. Output goes to `outputs/`.

## Setup: WSL2, a dedicated conda env

**Use a new, separate conda env, never an env another heavy model already uses.** Mixing the dependencies of two heavy models in one env is the fastest way to break both.

```bash
# Inside WSL2 (Ubuntu 22.04 is the distribution this setup was run on)
conda create -n ardy python=3.11 -y
conda activate ardy

# Install PyTorch BEFORE the rest, and pin the CUDA index to what the driver of this
# machine supports. The repo uses cu126 (CUDA 12.6) as its example. Before copying the
# command, check `nvidia-smi` (installed driver) against the CUDA compatibility matrix;
# do not assume cu126 is right.
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126

# Full installation (includes the demo). Alternatives: `pip install -e .` (core only, no
# interactive demo, which is not enough for this use) or `pip install -e ".[trt]"` (with TensorRT).
pip install -e ".[all]"
```

Build requirements: **CMake 3.15 or newer and a C++17 compiler**. Confirm WSL2 has them (`cmake --version`, `g++ --version`) before installing; if they are missing, `sudo apt install cmake build-essential`.

Clone the repo onto a mounted data drive (a `/mnt/<drive>/...` path), not onto the WSL2 system disk: there is more space and large models load faster. When no such drive is available on this machine, ask the user where to clone before picking a default.

### Model weights: downloaded automatically, behind a Hugging Face gate

**The weights do not need to be downloaded by hand**: the repo downloads them when the demo is used. Available models: `ARDY-Core-RP-20FPS-Horizon40/8`, `ARDY-G1-RP-25FPS-Horizon52/8`, `ARDY-SOMA-RP-30FPS-Horizon60` and `ARDY-SOMA-RP-30FPS-KimodoRep-Horizon60`. SOMA is the default `--model`; without `--model core` you get SOMA output, not core.

The text encoder uses `meta-llama/Meta-Llama-3-8B-Instruct`, a **gated** model on Hugging Face. Request access on its model page (approval is usually fast but not instant, so allow for it) and then authenticate:

```bash
hf auth login
# or save the token directly:
# echo "hf_..." > ~/.cache/huggingface/token
```

## Launch the interactive demo

The demo is `run_demo.py` in the `scripts` folder of the ARDY clone. Run it with the clone's root as the working directory:

```bash
ARDY_SCRIPTS="$PWD/scripts"          # set once, in the root of the ARDY clone
python "$ARDY_SCRIPTS/run_demo.py"
python "$ARDY_SCRIPTS/run_demo.py" --help
```

Optional: run the text encoder in its own process. This is recommended here, to watch its VRAM footprint before the rest is added, given how tight a 24 GB card is:

```bash
python "$ARDY_SCRIPTS/run_text_encoder_server.py"
```

Browser UI: **http://localhost:2333** (the visualization viewer is at **http://localhost:2334**).

The skeleton is chosen with `--model`. It takes a nickname (`soma`, `soma-kimodo`, `core`, `g1`), a nickname with a horizon (`core8`, `g152`) or a full checkpoint name (`ARDY-Core-RP-20FPS-Horizon40`). The default is `soma`, so always pass `--model core`:

```bash
python "$ARDY_SCRIPTS/run_demo.py" --model core
```

For survivor locomotion use the **`core`** skeleton (a generic humanoid), not `g1` or the default `soma`: `g1` is the rig of the real Unitree G1 bipedal robot, not a character skeleton.

## What it produces

`.npz` files with:

- `posed_joints`: world-space joint positions, shape `[T, J, 3]`
- joint rotations, local and global
- root positions
- foot contacts

The `g1` skeleton also exports a MuJoCo qpos CSV, a robotics simulation format. It is not relevant to character locomotion; ignore it if it appears.

By default outputs go to the repo's `outputs/` folder.

## Getting the output into DayZ: a plan, not tested

Everything in this section is design, not tested code. No step of the chain has been run. Before writing retargeting code, decide with the user whether each stretch gets its own checkpoint, and do not chain the steps in one session without stopping in between.

### Why this plan exists without being verified

The use chosen for ARDY is full-body survivor locomotion (running, jumping, vaulting). For that to become playable in DayZ a conversion chain is needed that does not exist today. Writing the plan down now saves a later session from working out again what is missing, but **do not take it as a verdict that the chain works**: each arrow below is a plausible point of failure that nobody has explored.

### The complete chain

```
ARDY .npz ("core" skeleton: world-space joints + rotations + root + foot contacts)
  │
  │  [DESIGN] Step 1: parsing
  ▼
Import into Blender (custom Python script, numpy to armature)
  │
  │  [DESIGN] Step 2: the highest-risk step
  ▼
Retarget to OFP2_ManSkeleton (the DayZ player skeleton)
  │
  │  [EXISTING: the pipeline already used and verified, see anm-clips.md]
  ▼
Export .txa → Workbench → .anm (SEAnim / DayZATool)
  │
  ▼
In-game gate
```

Only the last leg (`.txa` to `.anm` to in game) has a verified pipeline: it is the route in `anm-clips.md` and `blender-txa-export.md` for any skeletal player animation. Steps 1 and 2 are new territory.

### Step 1: parse the `.npz`

Low technical risk: it is a numpy archive with a documented structure (`posed_joints [T,J,3]`, rotations, root, foot contacts). Write a script that loads it and inspects the actual shape of the first generated output before assuming the layout. The README does not give the exact dtype or axis order (XYZ or XZY, Y-up or Z-up).

The axis convention matters twice. Blender is Z-up; the DayZ engine is Y-up (`vector.Up` is `"0 1 0"`, `P:\scripts\1_core\proto\enconvert.c:120`), and the Blender to DayZ export does that conversion (see the axis and winding caveats in the model skills). Confirm the `.npz` convention with a real file; do not assume the convention of another pipeline.

### Step 2: retarget to the DayZ player skeleton (the step that can kill the plan)

Structurally this is the problem `mixamo-retarget.md` already solves, partly and experimentally: mapping a generic external skeleton onto the specific bone hierarchy DayZ expects. Differences that may make it harder than the Mixamo case:

- The ARDY "core" skeleton has no documented official mapping to any game format (not FBX, not BVH, not SMPL). The bone-by-bone map has to be derived by hand, comparing names and hierarchy against the full DayZ player bone map (core and spine, legs, arms, IK helpers, fingers). That map is in `player-skeleton.md`; the vanilla bone list is the `player_testing.xob` block that starts at `P:\DZ\anims\cfg\skeletons.anim.xml:110`.
- The exact bone count of "core" is not known from an official source (the figure of about 27 is not confirmed on the project's landing page or in its repo). Count the actual joints of the first generated `.npz` before trying to map.
- DayZ expects fingers, the hand helpers `LeftHand_Dummy` and `RightHand_Dummy` (both `lod = "1"` in `player_testing.xob`, `P:\DZ\anims\cfg\skeletons.anim.xml:116` and `P:\DZ\anims\cfg\skeletons.anim.xml:115`) and several IK helpers (`RightHandOrigin`, `LeftHandOrigin`, `LeftHandIKTarget`, listed for `player_testing.xob` at `P:\DZ\anims\cfg\skeletons.anim.xml:149-151`). A generic "core" skeleton (bone count unconfirmed) probably covers none of them. Leg and torso locomotion may map reasonably well, but hands and fingers will probably have to stay in their bind pose (unanimated) or inherit from another source.

**Open question to settle with the first test:** is retargeting only legs, torso and spine (leaving arms and hands untouched, or additive) enough for the real goal of running, jumping and vaulting? If yes, the retargeting scope shrinks a lot and the risk drops. Decide this before trying to map hands and fingers, which is where this kind of retarget usually fails most.

### Steps 3 and 4: export and the final pipeline

Once an FK pose exists on the Blender armature with the correct DayZ bone names, the rest of the chain (`.txa`, Workbench, `.anm`) is the verified route in `blender-txa-export.md` and `anm-clips.md`. Nothing new is designed there.

### Alternatives if direct retargeting does not pay off

If step 2 costs too much for the actual benefit:

- Use ARDY only as a **visual reference** (a playblast) and animate by hand in Blender or Cascadeur, instead of trying an automatic one-to-one retarget. This loses "real time" but avoids the skeleton mapping problem.
- Check whether Cascadeur covers the same locomotion goal without ARDY's non-standard skeleton problem. Of the animation tools compared for this goal, Cascadeur was the only one with custom skeleton, IK and FK, and physics support, and its fit was rated conditional and medium. That rating is not checkable on `P:\`.

## Where the rest lives

| Question | Read |
|---|---|
| How does the DayZ animation system work (bones, ASI, the grip)? | `player-skeleton.md`, `anim-graphs.md`, `weapon-in-hands.md` |
| How do I retarget an external skeleton onto a Blender rig? | `mixamo-retarget.md` |
| What acceptance and evidence does the resulting motion need? | `realistic-motion.md` |

## On Linux

Everything above is the Windows workflow and stays valid there. On Linux, the Proton setup, the measured tool matrix and the pitfalls are in `skills/_shared/linux-proton.md`; this section only says what changes here.

- The setup is written for WSL2. On a Linux host it runs natively: same conda environment, no WSL layer, no `/mnt/c` paths. The later `.txa` to Workbench to `.anm` step is Windows first: see `tooling-and-walls.md`, "On Linux".
