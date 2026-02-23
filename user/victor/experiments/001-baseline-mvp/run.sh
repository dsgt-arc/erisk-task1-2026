#SSH into PACE cluster
ssh vgong7@login-phoenix.pace.gatech.edu

#Request GPU node
salloc -N 1 --gres=gpu:V100:1 -t 2:00:00 --account=paceship-dsgt_clef2026

#Set cache to scratch directory
export HF_HOME=/storage/scratch1/8/vgong7/.cache/huggingface
export UV_CACHE_DIR=/storage/scratch1/8/vgong7/.cache/uv
export UV_PYTHON_INSTALL_DIR=/storage/scratch1/8/vgong7/.local/share/uv/python

#Pull latest code (if updates)
cd scratch/erisk-2026
git pull origin main

#Sync venv and packages
export UV_PROJECT_ENVIRONMENT="/storage/scratch1/8/vgong7/.venv-erisk"
source /storage/scratch1/8/vgong7/.venv-erisk/bin/activate
uv sync --package 001-baseline-mvp --python 3.11


#Auth into HuggingFace
hf auth login

#Export API keys
export OPENAI_API_KEY="sk..."

#Run
cd src
python run.py --personas 0 --provider openai