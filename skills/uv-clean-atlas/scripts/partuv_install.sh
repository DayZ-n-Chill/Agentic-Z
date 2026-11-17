#!/bin/bash
# Install PartUV for the pilot in references/partuv-pilot.md. Run on Linux or
# WSL2 with an NVIDIA GPU, miniforge in ~/miniforge3 and the PartUV repo cloned
# to ~/PartUV. Progress goes to /tmp/partuv_install.log; each finished step
# prints a STEP_*_OK line. Keep LF line endings.
set -e
source ~/miniforge3/etc/profile.d/conda.sh
LOG=/tmp/partuv_install.log
echo "=== partuv install $(date) ===" > "$LOG"

conda create -y -n partuv python=3.11 >> "$LOG" 2>&1
conda activate partuv
conda install -y -c conda-forge 'libstdcxx-ng>=13' 'libgcc-ng>=13' >> "$LOG" 2>&1
echo STEP_CONDA_OK

pip install torch==2.7.1 --index-url https://download.pytorch.org/whl/cu128 >> "$LOG" 2>&1
echo STEP_TORCH_OK
pip install torch-scatter -f https://data.pyg.org/whl/torch-2.7.1+cu128.html >> "$LOG" 2>&1
echo STEP_SCATTER_OK

cd ~/PartUV
pip install -r requirements.txt >> "$LOG" 2>&1
echo STEP_REQS_OK
pip install partuv bpy >> "$LOG" 2>&1
echo STEP_PARTUV_OK

if [ ! -f ~/PartUV/model_objaverse.ckpt ]; then
  wget -q https://huggingface.co/mikaelaangel/partfield-ckpt/resolve/main/model_objaverse.ckpt -O ~/PartUV/model_objaverse.ckpt
fi
ls -lh ~/PartUV/model_objaverse.ckpt
echo STEP_CKPT_OK

python - <<'PYEOF'
import torch
print("torch", torch.__version__, "cuda", torch.cuda.is_available())
import partuv
print("partuv import OK")
PYEOF
echo INSTALL_DONE
