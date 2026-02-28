# SSH into PACE cluster
ssh vgong7@login-phoenix.pace.gatech.edu

# Request GPU node
salloc -N 1 --gres=gpu:V100:1 -t 2:00:00 --account=paceship-dsgt_clef2026

# Set caches to scratch (avoid home quota)
export HF_HOME=/storage/scratch1/8/vgong7/.cache/huggingface
export UV_CACHE_DIR=/storage/scratch1/8/vgong7/.cache/uv
export UV_PYTHON_INSTALL_DIR=/storage/scratch1/8/vgong7/.local/share/uv/python

# Pull latest code
cd ~/scratch/erisk-2026
git pull origin main

# Sync venv
export UV_PROJECT_ENVIRONMENT="/storage/scratch1/8/vgong7/.venv-erisk"
uv sync --package 002-multi-agent --python 3.11
source /storage/scratch1/8/vgong7/.venv-erisk/bin/activate

# Auth (first time only)
# huggingface-cli login

# API keys
export OPENAI_API_KEY="sk-..."

# Run for single persona
cd user/victor/experiments/002-multi-agent/src
python run.py \
  --personas 3 \
  --run-id 1 \
  --interviewer-provider openai \
  --scorer-provider openai \
  --max-turns 18 \
  --ensemble-size 1 \
  --score-every-n 1

# Copy results to local machine (run from local terminal)
# scp -r "vgong7@login-phoenix.pace.gatech.edu:/storage/scratch1/8/vgong7/erisk-2026/user/victor/experiments/002-multi-agent/results/" ~/Downloads/
