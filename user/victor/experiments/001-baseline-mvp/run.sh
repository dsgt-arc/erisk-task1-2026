#SSH into PACE cluster
ssh vgong7@login-phoenix.pace.gatech.edu

#Request GPU node
salloc -N 1 --gres=gpu:V100:1 -t 2:00:00 --account=paceship

#Set cache to scratch directory
export HF_HOME=/storage/scratch1/8/vgong7/.cache/huggingface
export XDG_CACHE_HOME=/storage/scratch1/8/vgong7/.cache

#Pull latest code (if updates)
cd scratch/erisk-2026
git pull origin main

#Sync venv and packages
cd user/victor/experiments/001-baseline-mvp
export UV_PROJECT_ENVIRONMENT="$TMPDIR/.venv"
uv sync --package 001-baseline-mvp
source $TMPDIR/.venv/bin/activate

#Auth into HuggingFace
hf auth login

#Export API keys
export OPENAI_API_KEY="sk..."

#Run
cd src
python run.py --personas 1 --provider openai