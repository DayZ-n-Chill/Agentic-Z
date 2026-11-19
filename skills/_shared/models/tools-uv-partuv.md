# PartUV

How to install and run PartUV, the setup faults to expect, and how it scored against the view chart pipeline of `tools-uv-atlas.md` on the same meshes. Nothing here is a game fact.

PartUV (SIGGRAPH Asia 2025) combines the PartField part tree with a recursive chart extraction that bounds distortion. Its native core does ABF and LSCM and ships as prebuilt pip wheels. It is the only UV AI with public code and weights.

## Setup

It runs on Linux or WSL2 with an NVIDIA GPU. `skills/dayz-model-tools/scripts/partuv_install.sh` runs these steps and logs each one:

```bash
conda create -y -n partuv python=3.11
conda activate partuv
conda install -y -c conda-forge 'libstdcxx-ng>=13' 'libgcc-ng>=13'   # GLIBCXX_3.4.32
pip install torch==2.7.1 --index-url https://download.pytorch.org/whl/cu128
pip install torch-scatter -f https://data.pyg.org/whl/torch-2.7.1+cu128.html
cd <PartUV clone> && pip install -r requirements.txt && pip install partuv bpy
pip install pytz 'setuptools<82'        # undeclared dependencies, see below
wget https://huggingface.co/mikaelaangel/partfield-ckpt/resolve/main/model_objaverse.ckpt
```

The script does not install `pytz` and `setuptools<82`; run that line yourself after it.

Run from the PartUV repository root, because the checkpoint path is relative to the current folder:

```bash
mkdir -p pilot/<mesh_stem>          # preprocess exports into this subfolder
python demo/partuv_demo.py --mesh_path pilot/<mesh>.obj \
  --output_path pilot/out --pack_method blender --save_visuals
```

## Setup faults

Each of these stops a run.

- `pytz` and `pkg_resources` are undeclared dependencies. Run `pip install pytz 'setuptools<82'`: setuptools 82 removed `pkg_resources`, and lightning 2.2 still imports it.
- The checkpoint is 1,243,631,761 bytes. A truncated download throws `PytorchStreamReader failed reading zip archive`; check it with `zipfile.ZipFile(...).testzip()`.
- `preprocess()` exports the processed mesh into `<mesh_dir>/<mesh_stem>/`. Create that folder first or it stops with `FileNotFoundError`.
- "Invalid mesh data from numpy arrays. Exiting." (exit 3) means it needs a clean, all triangle OBJ: triangulated, degenerate faces dissolved, loose geometry dropped. `export_objs_tri.py` writes exactly that:

  ```cmd
  blender -b <file.blend> -P "<repo>\skills\dayz-model-tools\scripts\export_objs_tri.py" -- <object_name> <out.obj>
  ```

- Run `export LD_LIBRARY_PATH=$CONDA_PREFIX/lib` before the demo, so the native module finds its libstdc++.
- The distortion threshold is hardcoded as `threshold=1.25` in `demo/partuv_demo.py`. Edit a copy with `sed` to change it.
- The PartField checkpoint derives from NVIDIA work. Review its license before shipping outputs in a commercial product.

## How it scored

Same meshes (the quad bike body of `tools-uv-atlas.md`), same audit code. The view chart rows are the pipeline before boundary straightening and the cutting of leftover faces into specks; the current scripts give 54 islands (30 panels) on the retopology and 65 on the rip.

| Run | Islands | Panels | Specks | Density p05 to p95 | Notes |
|---|---|---|---|---|---|
| View chart pipeline, retopology, 10.5k quads | 43 | 28 | 6 | 0.87 to 1.18 | SAT = 0 |
| PartUV, retopology, t = 1.25 | 162 | 51 | 108 | 0.85 to 1.16 | Distortion 1.19 |
| PartUV, retopology, t = 2.0 | 127 | 34 | 93 | 0.81 to 1.20 | Distortion 1.80 |
| View chart pipeline, rip, 36.9k triangles | 63 | 23 | 35 | 0.82 to 1.46 | SAT = 0 |
| PartUV, rip, t = 1.25 | 232 | 64 | 158 | 0.79 to 1.25 | Distortion 1.25 |

PartField inference takes about 4 s for 10k to 37k triangles; the whole demo takes about 1.5 to 2 minutes with the model load and the Blender packing. Video memory is no issue at these sizes.

On vehicle content PartField splits springs and junk micro shells into many parts. Each is unwrapped to 1 or 2 charts with no dust merge, so the atlas fills with specks. Its packing is `pack_islands`, which leaves the islands at random orientations.

## Using it as a chart source

PartUV or PartField can supply the charts (parts by meaning) for the later stages of `uv_clean_atlas.py`: stages 3 to 7 in `tools-uv-atlas.md` (SLIM unwrap and fold guard, SAT finisher, straightening, shelf pack and metrics). Audit such a run with `audit_partuv.py`, which imports a PartUV `final_packed.obj`, scores it with `uv_metrics.py`, repacks it with the shelf packer and scores it again:

```cmd
blender -b -P "<repo>\skills\dayz-model-tools\scripts\audit_partuv.py" -- <in.obj> <out_dir> <tag> <out.blend>
```
