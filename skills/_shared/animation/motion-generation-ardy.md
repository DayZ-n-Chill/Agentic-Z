# Generated locomotion with ARDY

What ARDY is, how to set it up and run it, what it writes, and the untested route from its output to a DayZ clip. It is for full body survivor locomotion (running, jumping, vaulting, moving through a scene), not weapon animation.

Experimental: no clip made this way has played in DayZ, and every step after setup is a plan. No script for it ships in this repo, and nothing here runs against `P:\`, DayZ Tools or the game. What this file says about ARDY comes from the project's own pages and one install; check those pages before you rely on a detail, and do not go by videos or marketing.

## What it does not solve

A weapon grip in DayZ fails or works on how well the weapon model lines up with the reference `.anm` on `Weapon_Root` and `RightHand_Dummy`, both bones of the survivor skeleton `player_testing.xob` (`RightHand_Dummy` at `P:\DZ\anims\cfg\skeletons.anim.xml:115`, `Weapon_Root` at `:254`). ARDY works on a full body "core" skeleton and controls a hand only as an end point position. It knows nothing of held object geometry, single fingers or the DayZ instance and IK system, so it works on the wrong layer for a grip. For grip work use `realistic-motion.md` and `weapon-in-hands.md`.

## What it is

ARDY ("Autoregressive Diffusion with Hybrid Representation for Interactive Human Motion Generation", from NVIDIA's SIL research lab) is a two stage autoregressive transformer denoiser: the first stage predicts root motion, the second the body motion on top of it. It takes sparse constraints in time and joints, and real time control by text prompt, root path and waypoints, full body keyframes, end point positions and rotations, mouse waypoints, keyboard velocity and long range goals.

- Code: https://github.com/nv-tlabs/ardy
- Paper and project page: https://research.nvidia.com/labs/sil/projects/ardy/
- Models: https://huggingface.co/collections/nvidia/ardy

Read the licence of the code and of the model weights before you share anything made from them.

## Video memory

The text encoder alone (Llama-3-8B-Instruct in bf16) takes about 14 GB. The project's README also offers the encoder on the CPU (`cpu / bfloat16`, `cpu / float32`), which is slower but saves video memory. The project gives no total; an estimate is 16 to 18 GB at least and about 24 GB for smooth real time, and a 24 GB card leaves no margin. WSL2 adds its own overhead. Expect running out of memory in real time mode.

When it runs out, try in this order:

1. Start `run_text_encoder_server.py` as its own process, which shows its footprint before the rest loads.
2. Close everything else that holds video memory, such as a browser with GPU acceleration or another loaded model.
3. Generate offline instead of in the real time demo: `python "$ARDY_SCRIPTS/generate.py" "<prompt>" --model core` from the root of the clone. Output goes to `outputs/`.

## Setup

Use a new conda environment of its own. Two heavy models in one environment is the quickest way to break both.

```bash
# inside WSL2
conda create -n ardy python=3.11 -y
conda activate ardy

# Install PyTorch first and pin the CUDA index to what the installed driver supports.
# The project uses cu126 as its example; check nvidia-smi against the CUDA compatibility table first.
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126

# Full install, demo included. `pip install -e .` has no demo; `pip install -e ".[trt]"` adds TensorRT.
pip install -e ".[all]"
```

The build needs CMake 3.15 or newer and a C++17 compiler; check with `cmake --version` and `g++ --version`, and install `cmake build-essential` with `apt` if they are missing.

Clone onto a mounted data drive (a `/mnt/<drive>/...` path), not the WSL2 system disk: there is more room and large models load faster. When there is no such drive, ask the user where to clone.

The weights download on first use of the demo. The models are `ARDY-Core-RP-20FPS-Horizon40/8`, `ARDY-G1-RP-25FPS-Horizon52/8`, `ARDY-SOMA-RP-30FPS-Horizon60` and `ARDY-SOMA-RP-30FPS-KimodoRep-Horizon60`. The text encoder `meta-llama/Meta-Llama-3-8B-Instruct` is gated on Hugging Face: request access on its page, allow some time for approval, then sign in with `hf auth login` (or write the token to `~/.cache/huggingface/token`).

## Running the demo

```bash
ARDY_SCRIPTS="$PWD/scripts"                      # once, from the root of the clone
python "$ARDY_SCRIPTS/run_text_encoder_server.py" # optional, in its own process, to watch its memory
python "$ARDY_SCRIPTS/run_demo.py" --model core
```

The browser UI is at http://localhost:2333 and the viewer at http://localhost:2334.

`--model` takes a nickname (`soma`, `soma-kimodo`, `core`, `g1`), a nickname with a horizon (`core8`, `g152`) or a full checkpoint name (`ARDY-Core-RP-20FPS-Horizon40`). The default is `soma`, so always pass `--model core`. `core` is a generic humanoid; `g1` is the rig of the Unitree G1 robot, not a character.

## What it writes

`.npz` files in `outputs/` with `posed_joints` (world space joint positions, shape `[T, J, 3]`), local and global joint rotations, root positions and foot contacts. The `g1` skeleton also writes a MuJoCo qpos CSV for robot simulation; ignore it.

## The route into DayZ, untested

No step below has run. Decide with the user where to stop and check between steps, and do not chain them in one session.

1. Read the `.npz` into Blender with a numpy script that builds an armature. Low risk, but the README gives neither dtype nor axis order, so inspect the first real file before assuming a layout. Blender is Z up and DayZ is Y up (`vector.Up` is `"0 1 0"`, `P:\scripts\1_core\proto\enconvert.c:120`); the Blender to DayZ export converts that, so confirm the `.npz` convention from a real file rather than another pipeline's.
2. Retarget onto the DayZ player skeleton. This is the step most likely to fail. It is the same kind of problem as `mixamo-retarget.md`, but harder: "core" has no published map to any game format (FBX, BVH or SMPL), so the bone map is built by hand against `player-skeleton.md` and the `player_testing.xob` block from `skeletons.anim.xml:110`. Its bone count is not published (a figure of about 27 is not confirmed by the project), so count the joints in the first `.npz`. DayZ expects fingers, the hand helpers `LeftHand_Dummy` and `RightHand_Dummy` (`:116` and `:115`) and IK helpers such as `RightHandOrigin`, `LeftHandOrigin` and `LeftHandIKTarget` (`:149` to `:151`), which "core" very likely lacks. Legs and torso may map well; hands and fingers will likely stay in bind pose or come from another source. Settle with the first test whether legs, torso and spine alone are enough for running, jumping and vaulting; if so, the work and the risk drop a lot.
3. Export and build through the checked route in `blender-txa-export.md` and `anm-clips.md`: `.txa`, then Workbench or DayZATool, then `.anm`.
4. Test in game.

If step 2 costs more than it gives, use ARDY output only as a visual reference and key by hand in Blender or Cascadeur. Of the tools compared for this goal, Cascadeur was the only one with custom skeletons, IK and FK, and physics, and was rated a conditional, medium fit (not checkable on `P:\`).

## On Linux

The setup above is written for WSL2; on a Linux host it runs natively in the same conda environment with no `/mnt/c` paths. The `.txa` to Workbench to `.anm` step is Windows first (`tooling-and-walls.md`, "On Linux"). Proton setup and the tool matrix are in `_shared/linux-proton.md`.

## Related files

| Question | File |
|---|---|
| How the DayZ animation system works: bones, instances, the grip | `player-skeleton.md`, `anim-graphs.md`, `weapon-in-hands.md` |
| Retargeting an outside skeleton onto a Blender rig | `mixamo-retarget.md` |
| The acceptance and evidence the motion needs | `realistic-motion.md` |
