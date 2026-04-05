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
uv sync --package 004-weaver --python 3.11
source /storage/scratch1/8/vgong7/.venv-erisk/bin/activate

# Auth (first time only)
hf auth login

# API keys (scorer uses GPT)
export OPENAI_API_KEY="sk-..."

# Run single persona (paid interviewer)
cd user/victor/experiments/004-weaver/src
python run.py \
  --personas 11 \
  --run-id 1 \
  --max-turns 18 \
  --ensemble-size 1 \
  --score-every-n 1

# Run single persona (free local Gemma 27B interviewer)
python run.py \
  --personas 11 \
  --run-id 1 \
  --free \
  --max-turns 18

# Copy results to local machine (run from local terminal)
# scp -r vgong7@login-phoenix.pace.gatech.edu:~/scratch/erisk-2026/user/victor/experiments/004-weaver/submissions/ ~/Downloads/submissions/


#######################
# SLURM JOB COMMANDS  #
#######################

# 1. Submit 10 paid baseline samples for persona 11
sbatch --job-name=11 --array=1-10 batch.sh 11

# 2. Submit 20 free samples (local Gemma 27B) for persona 11
sbatch --job-name=11 --array=1-20 batch.sh 11 --free

# 3. Monitor
squeue -u vgong7

# 4. After all jobs finish, select top 3 runs with Weaver
cd ~/scratch/erisk-2026/user/victor/experiments/004-weaver
python select_runs.py 11 --mix

# Output:
#   Persona 11: 30 samples
#   === Weaver Aggregation (30 samples) ===
#   Weights: #5=0.042, #12=0.041 ... #8=0.028
#   Consensus BDI: 22 (Moderate)
#   Selected 3 (Weaver pairwise agreement):
#     Run 1: free/sample-5  → BDI=22 (dist=2, w=0.042)
#     Run 2: free/sample-12 → BDI=21 (dist=3, w=0.041)
#     Run 3: paid/sample-3  → BDI=23 (dist=3, w=0.038)
#   → Copied to submissions/samples-mix/persona-11/run-{1,2,3}/

# 5. Upload to FTP
cd submissions
lftp -e "set ftp:ssl-force true; set ssl:verify-certificate no" -u DS-GT,PASSWORD ftp://erisk.irlab.org
# Inside lftp:
#   mkdir -p task1-llms-results/persona11/run-1
#   lcd persona-11/run-1
#   mput interactions_run1.json results_run1.json
