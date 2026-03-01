#!/bin/bash
#SBATCH -J erisk-sample
#SBATCH -N 1 --gres=gpu:V100:1
#SBATCH -t 1:00:00
#SBATCH --account=paceship-dsgt_clef2026
#SBATCH --array=1-10
#SBATCH -o logs/p%x_s%a_%j.out
#SBATCH -e logs/p%x_s%a_%j.err

# Runs N parallel interviews of ONE persona.
# Array index = sample number, persona passed as arg.
#
# Usage:
#   sbatch --job-name=4 batch.sh 4       # 10 samples of persona 4
#   sbatch --job-name=4 --array=11-20 batch.sh 4  # 10 more samples
#   sbatch --job-name=4 --array=1-50 batch.sh 4   # 50 samples at once

PERSONA_ID=${1:?Usage: sbatch batch.sh <persona_id>}
SAMPLE_ID=$SLURM_ARRAY_TASK_ID

# Environment
export HF_HOME=/storage/scratch1/8/vgong7/.cache/huggingface
export UV_CACHE_DIR=/storage/scratch1/8/vgong7/.cache/uv
export UV_PYTHON_INSTALL_DIR=/storage/scratch1/8/vgong7/.local/share/uv/python
export UV_PROJECT_ENVIRONMENT="/storage/scratch1/8/vgong7/.venv-erisk"

source /storage/scratch1/8/vgong7/.venv-erisk/bin/activate

cd ~/scratch/erisk-2026/user/victor/experiments/002-multi-agent/src

# Each sample gets its own output dir
OUTPUT_DIR="../results/samples/persona-${PERSONA_ID}/sample-${SAMPLE_ID}"
mkdir -p "$OUTPUT_DIR"

echo "=== Persona $PERSONA_ID, Sample $SAMPLE_ID ==="

python run.py \
  --personas $PERSONA_ID \
  --run-id 1 \
  --interviewer-provider openai \
  --scorer-provider openai \
  --max-turns 18 \
  --ensemble-size 3 \
  --score-every-n 1 \
  --output-dir "$OUTPUT_DIR"
