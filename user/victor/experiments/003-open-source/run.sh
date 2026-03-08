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
hf auth login

# API keys
export OPENAI_API_KEY="sk-..."

# Run for single persona
cd user/victor/experiments/002-multi-agent/src
python run.py \
  --personas 4 \
  --run-id 1 \
  --interviewer-provider openai \
  --scorer-provider openai \
  --max-turns 18 \
  --ensemble-size 3 \
  --score-every-n 1

# Copy results to local machine (run from local terminal)
# scp -r "vgong7@login-phoenix.pace.gatech.edu:/storage/scratch1/8/vgong7/erisk-2026/user/victor/experiments/002-multi-agent/results/" ~/Downloads/




#######################
# SLURM JOB COMMANDS. #
#######################

# 1. Add AI provider API key to .bashrc
echo 'export OPENAI_API_KEY="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"' >> ~/.bashrc 

# 2. Authenticate to Hugging Face models
export HF_HOME=/storage/scratch1/8/vgong7/.cache/huggingface
source /storage/scratch1/8/vgong7/.venv-erisk/bin/activate
huggingface-cli login

# 3. Submit 30 samples for Persona 3 (3 batches of 10, or all at once)
sbatch --job-name=3 --array=1-30 batch.sh 3

# 4. Monitor
squeue -u vgong7

# 5. After all jobs finish, pick top 3 closest to mean
python select_runs.py 3

# Output:
#   Persona 4: 50 samples
#   Scores: [5, 7, 8, 8, 9, 10, 10, 11, ...]
#   Mean: 12.3, Median: 11.0, Stdev: 5.2
#   Selected 3 closest to mean (12.3):
#     Run 1: sample-17 → BDI=12 (dist=0.3)
#     Run 2: sample-33 → BDI=13 (dist=0.7)
#     Run 3: sample-8  → BDI=12 (dist=0.3)
#   → Copied to submissions/persona-3/run-1/
#   → Copied to submissions/persona-3/run-2/
#   → Copied to submissions/persona-3/run-3/