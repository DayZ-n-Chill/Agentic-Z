---
name: ardy-motion-generation
description: "Installs and runs NVIDIA ARDY, an open-source real-time motion generation model (autoregressive diffusion, controlled by text, waypoints or keyboard), locally under WSL2 on a 24 GB GPU, to generate full-body locomotion (running, jumping, vaulting, scene traversal) for the DayZ survivor. Use when the user says install ARDY, try ARDY, generate animation with ARDY, real-time motion generation, AI locomotion for the survivor, animation from text or waypoints, or picks the generative locomotion project back up (Spanish: \"instala ARDY\", \"prueba ARDY\", \"genera animación con ARDY\", \"motion generation en tiempo real\", \"locomoción del survivor con AI\", \"animación por texto/waypoints\"). Not for weapon or grip animation, which is out of scope by design."
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# ARDY: real-time motion generation (NVIDIA)

This skill is a setup and usage guide; it ships no script and runs nothing against `P:\`, DayZ Tools or the game. What it says about ARDY describes the project's own pages and one install on one machine. None of it is checkable on `P:\`: re-check the project pages listed below before relying on a detail, and do not trust videos or marketing.

## What ARDY does not solve (read before investing time)

The goal of this skill is **full-body survivor locomotion** (running, jumping, vaulting, scene traversal), not weapon animation.

The real bottleneck of a weapon grip in DayZ is geometric parity between the weapon model and the reference `.anm` on the `Weapon_Root` and `RightHand_Dummy` bones. Both are in the vanilla bone list of the player skeleton `player_testing.xob`: `RightHand_Dummy` at `P:\DZ\anims\cfg\skeletons.anim.xml:115` and `Weapon_Root` at `P:\DZ\anims\cfg\skeletons.anim.xml:254`. The parity problem was measured in game on one weapon project; that result is not checkable on `P:\`. ARDY works on a full-body skeleton (about 27 "core" bones) with hand control as an end-effector position. It has no concept of held object geometry, individual fingers or the DayZ ASI and IK system. Bringing ARDY to a weapon grip problem would be solving the wrong layer. For grip work use `dayz-realistic-animation-director` and `dayz-animation-pipeline`.

## What it is

**ARDY** is "Autoregressive Diffusion with Hybrid Representation for Interactive Human Motion Generation" (NVIDIA, SIL research lab). It is a two-stage autoregressive transformer denoiser: stage 1 predicts the global root motion, stage 2 predicts the body motion conditioned on the root. It supports sparse kinematic constraints in time and joints. Real-time control: online text prompts, root trajectories and waypoints, full-body keyframes, end-effector joint positions and rotations, mouse waypoint editing, keyboard velocity commands and long-horizon goals.

- Repo: https://github.com/nv-tlabs/ardy
- Landing page and paper: https://research.nvidia.com/labs/sil/projects/ardy/
- Models: https://huggingface.co/collections/nvidia/ardy
- License: Apache-2.0 for the code; the weights are under a separate "NVIDIA Open Model" license. Read its exact terms before redistributing any derivative (personal research use is not affected).

## VRAM budget (read before launching anything)

The text encoder alone (Llama-3-8B-Instruct, bf16) asks for about **14 GB**. The documented total is 16 to 18 GB at minimum and about **24 GB for smooth real time**. A 24 GB card such as an RTX 3090 has no margin at all; for comparison, TRELLIS2-4B, another heavy model, was measured peaking at only 6.5 GB on that card. WSL2 adds its own VRAM overhead on top. Expect a real risk of running out of memory in real-time mode.

Mitigations to try, in order, when memory runs out:

1. Launch `run_text_encoder_server.py` in a separate process, which shows its footprint alone before the rest of the model is added.
2. Close every other process that reserves VRAM (a browser with GPU acceleration, another loaded model) before launching the demo.
3. If it still does not fit smoothly, accept generation that is not real time (batched or offline) if the repo allows it. The README does not confirm this; check the demo's `--help` output after installing (see "Launch the interactive demo").

## Setup: WSL2, a dedicated conda env

**Use a new, separate conda env, never an env another heavy model already uses.** An example is a TRELLIS2 env pinned to exactly PyTorch 2.6.0 with extensions compiled against that build: mixing the dependencies of two heavy models in one env is the fastest way to break both.

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

**The weights do not need to be downloaded by hand**: the repo downloads them when the demo is used. Available models: `ARDY-Core-RP-20FPS-Horizon40/8` and `ARDY-G1-RP-25FPS-Horizon52/8`.

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

**Unverified:** the README does not confirm an explicit flag for choosing the `core` or the `g1` skeleton in the demo command. It is probably selected through a config or through which checkpoint is loaded. Check the `--help` output after installing before assuming a flag.

For survivor locomotion use the **`core`** skeleton (a generic humanoid), not `g1`: `g1` is the rig of the real Unitree G1 bipedal robot, not a character skeleton.

## What it produces

`.npz` files with:

- `posed_joints`: world-space joint positions, shape `[T, J, 3]`
- joint rotations, local and global
- root positions
- foot contacts

The `g1` skeleton also exports a MuJoCo qpos CSV, a robotics simulation format. It is not relevant to character locomotion; ignore it if it appears.

By default outputs go to the repo's `outputs/` folder.

## Next steps: integration into DayZ (a plan, unverified; do not build without a checkpoint)

Everything in this section is design, not tested code. Before writing any retargeting script, read `references/dayz-integration-plan.md` in full (it holds the complete checklist) and the skills it names. Do not assume the pipeline described here works as written.

The pending chain in short: `.npz` (world-space joints, "core" skeleton of about 27 bones), then import into Blender, then **retarget to the DayZ player skeleton** (`player_testing.xob`, which the RPT calls `OFP2_ManSkeleton`; the same kind of problem `mixamo-retarget` faces and that skill is still experimental: a generic external skeleton onto the specific DayZ one, with no official ARDY mapping to any game format), then export `.txa`, then the existing `dayz-animation-pipeline` route to `.anm`, then the in-game gate.

No part of that chain is tested. See `references/dayz-integration-plan.md` for the detail and the open questions before trying it.

## References

| Question | Read |
|---|---|
| What would it take to get ARDY output into DayZ, step by step, and what is still open? | `references/dayz-integration-plan.md` |
| How does the real DayZ animation system work (bones, ASI, skeleton map, the grip mechanism)? | `dayz-animation-pipeline`, and the animation pack index `_shared/animation/README.md` |
| How do I retarget an external skeleton onto a Blender rig? | `mixamo-retarget` |

## On Linux

Everything above is the Windows workflow and stays valid there. On Linux, the Proton setup, the measured tool matrix and the pitfalls are in `_shared/linux-proton.md`; this section only says what changes for this skill.

- The setup is written for WSL2. On a Linux host it runs natively: same conda environment, no WSL layer, no `/mnt/c` paths. The later `.txa` to Workbench to `.anm` step is Windows-first: see the Linux notes of `dayz-animation-pipeline`.
