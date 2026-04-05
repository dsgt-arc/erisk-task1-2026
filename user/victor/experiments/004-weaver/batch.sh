#!/bin/bash
#SBATCH -J erisk-sample
#SBATCH -N 1 --gres=gpu:V100:1
#SBATCH -t 1:00:00
#SBATCH --account=paceship-dsgt_clef2026
#SBATCH --array=1-10
#SBATCH -o logs/p%x_s%a_%j.out
#SBATCH -e logs/p%x_s%a_%j.err

# Runs N parallel interviews of ONE persona.
# --free uses local Gemma 27B (4-bit) for interviewer; scorer always paid GPT.
#
# Usage:
#   sbatch --job-name=4 batch.sh 4              # 10 paid samples
#   sbatch --job-name=4 batch.sh 4 --free       # 10 free samples (local Gemma)
#   sbatch --job-name=4 --array=1-20 batch.sh 4 --free  # 20 free samples

PERSONA_ID=${1:?Usage: sbatch batch.sh <persona_id> [--free]}
shift
EXTRA_FLAGS="$@"

# Environment
export HF_HOME=/storage/scratch1/8/vgong7/.cache/huggingface
export UV_CACHE_DIR=/storage/scratch1/8/vgong7/.cache/uv
export UV_PYTHON_INSTALL_DIR=/storage/scratch1/8/vgong7/.local/share/uv/python
export UV_PROJECT_ENVIRONMENT="/storage/scratch1/8/vgong7/.venv-erisk"

source /storage/scratch1/8/vgong7/.venv-erisk/bin/activate

cd ~/scratch/erisk-2026/user/victor/experiments/004-weaver/src

SAMPLE_ID=$SLURM_ARRAY_TASK_ID

# Tag output dir with model type
if echo "$EXTRA_FLAGS" | grep -q "\-\-free"; then
    OUTPUT_DIR="../results/samples-free/persona-${PERSONA_ID}/sample-${SAMPLE_ID}"
else
    OUTPUT_DIR="../results/samples-paid/persona-${PERSONA_ID}/sample-${SAMPLE_ID}"
fi
mkdir -p "$OUTPUT_DIR"

echo "=== Persona $PERSONA_ID, Sample $SAMPLE_ID, Flags: $EXTRA_FLAGS ==="

python run.py \
  --personas $PERSONA_ID \
  --run-id 1 \
  --max-turns 18 \
  --ensemble-size 1 \
  --score-every-n 1 \
  --output-dir "$OUTPUT_DIR" \
  $EXTRA_FLAGS
