# PartUV pilot: setup, quirks and measured results

How to install and run PartUV, what went wrong on the way, and how it scored against the Track A pipeline of `tools-uv-atlas.md` on the same meshes. Piloted on 2026-07-16 on WSL2 Ubuntu 22.04 with an RTX 3090.

PartUV (SIGGRAPH Asia 2025; its GitHub repository is named PartUV) combines the PartField hierarchical part tree with a recursive chart extraction that bounds distortion. Its native core does ABF and LSCM and ships as prebuilt pip wheels. In 2025 and 2026 it is the only "UV AI" with public code and weights.

## Environment that worked

WSL2 Ubuntu 22.04, RTX 3090, miniforge. `skills/dayz-model-tools/scripts/partuv_install.sh` runs these steps and logs each one:

```bash
conda create -y -n partuv python=3.11
conda activate partuv
conda install -y -c conda-forge 'libstdcxx-ng>=13' 'libgcc-ng>=13'   # GLIBCXX_3.4.32
pip install torch==2.7.1 --index-url https://download.pytorch.org/whl/cu128
pip install torch-scatter -f https://data.pyg.org/whl/torch-2.7.1+cu128.html
cd ~/PartUV && pip install -r requirements.txt && pip install partuv bpy
pip install pytz 'setuptools<82'        # undeclared deps (see quirks)
wget https://huggingface.co/mikaelaangel/partfield-ckpt/resolve/main/model_objaverse.ckpt
```

The script does not install `pytz` and `setuptools<82`; run that line by hand after it (quirk 1).

Run from the PartUV repo root, because the checkpoint path is relative to the current folder:

```bash
mkdir -p pilot/<mesh_stem>          # quirk 3: preprocess exports into this subfolder
python demo/partuv_demo.py --mesh_path pilot/<mesh>.obj \
  --output_path pilot/out --pack_method blender --save_visuals
```

## Quirks checklist

Each one cost a failed run.

1. `pytz` and `pkg_resources` are undeclared dependencies. Run `pip install pytz 'setuptools<82'`: setuptools 82 removed `pkg_resources`, and lightning 2.2 still imports it.
2. Checkpoint integrity: expect **1,243,631,761 bytes**. A truncated download throws `PytorchStreamReader failed reading zip archive`. Verify with `zipfile.ZipFile(...).testzip()`.
3. `preprocess()` exports the processed mesh into `<mesh_dir>/<mesh_stem>/`. Create that folder first or it dies with `FileNotFoundError`.
4. "Invalid mesh data from numpy arrays. Exiting." (exit 3) means it needs a sanitized, pure-triangle OBJ: triangulated, degenerate faces dissolved, loose geometry dropped. `<repo>\skills\dayz-model-tools\scripts\export_objs_tri.py` does exactly this:

   ```cmd
   blender -b <file.blend> -P "<repo>\skills\dayz-model-tools\scripts\export_objs_tri.py" -- <object_name> <out.obj>
   ```
5. Run `export LD_LIBRARY_PATH=$CONDA_PREFIX/lib` before the demo, so the native module finds its libstdc++.
6. The distortion threshold is hardcoded as `threshold=1.25` in `demo/partuv_demo.py`. Edit a copy with `sed` to change it.
7. License caveat: the PartField checkpoint is derived from NVIDIA work. Review its license before shipping outputs in a commercial product. For a hobby mod it is fine in practice.

## Measured results

Same meshes, same audit code. The Track A rows were measured with the pipeline as it stood in the pilot, before stage 5 (boundary straightening and the excision of leftover faces as specks). The current scripts give 54 islands (30 panels) on the retopology and 65 on the rip; see the top of `tools-uv-atlas.md`.

| Config | Islands | Panels | Specks | Density p05 to p95 | Notes |
|---|---|---|---|---|---|
| Track A, retopo, 10.5k quads | **43** | 28 | 6 | 0.87 to 1.18 | SAT = 0 proven |
| PartUV, retopo, t = 1.25 | 162 | 51 | 108 | 0.85 to 1.16 | distortion 1.19 |
| PartUV, retopo, t = 2.0 | 127 | 34 | 93 | 0.81 to 1.20 | distortion 1.80 |
| Track A, rip, 36.9k triangles | **63** | 23 | 35 | 0.82 to 1.46 | SAT = 0 proven |
| PartUV, rip, t = 1.25 | 232 | 64 | 158 | 0.79 to 1.25 | distortion 1.25 |

Runtime: PartField inference takes about 4 s for 10k to 37k triangles; the full demo takes about 1.5 to 2 minutes including the model load and the Blender packing. VRAM is no issue on a 3090 at these sizes.

Failure mode on vehicle content: PartField splits helicoids (springs) and junk micro-shells into many parts. Each is unwrapped to 1 or 2 charts with no dust merging, so the atlas fills with specks. Its packing is `pack_islands`, which leaves the islands at chaotic orientations.

## The reusable idea

PartUV or PartField can serve as an alternative **chart source** (semantic parts) that feeds the stages of `uv_clean_atlas.py` that come after charting (stages 3 to 7 in `tools-uv-atlas.md`: SLIM unwrap and fold guard, SAT finisher, straightening, shelf pack and metrics). Audit any such experiment with `audit_partuv.py`, which imports a PartUV `final_packed.obj`, scores it with `uv_metrics.py`, re-packs it with the semantic shelf packer and scores it again:

```cmd
blender -b -P "<repo>\skills\dayz-model-tools\scripts\audit_partuv.py" -- <in.obj> <out_dir> <tag> <out.blend>
```
