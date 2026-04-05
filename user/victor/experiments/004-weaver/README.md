# Experiment 004: Weaver Run Selection + Dialogue Tree

Multi-agent depression detection for eRisk 2026 Task 1 with Weaver-style run selection, precomputed dialogue tree, and labeling functions for interview consistency.

## Quick Start

```bash
# Install dependencies
cd /path/to/erisk-2026
uv sync --package 004-weaver

# Set API keys
export OPENAI_API_KEY="your-key"  # scorer always uses GPT

# Run with mock persona (no GPU needed)
cd user/victor/experiments/004-weaver/src
python run.py --mock-persona --personas 1

# Run with free local Gemma 27B for interviewer (GPU required, 4-bit quantized)
python run.py --mock-persona --personas 1 --free

# Run with paid GPT for interviewer
python run.py --mock-persona --personas 1

# Select runs with Weaver aggregation
cd ..
python select_runs.py 5 --mix

# Compare with legacy heuristic
python select_runs.py 5 --mix --legacy

# Generate comparison visualizations
python visualize.py
```

## What Changed from 003

- **Weaver run selection** — replaces 60% median + 40% consensus heuristic with per-sample reliability weights learned from pairwise agreement across 21 BDI-II symptoms
- **Dialogue tree** — precomputed question bank (~30 nodes) with BM25 followup matching, LLM fallback for off-tree responses
- **Labeling functions** — keyword/regex classifiers detect symptom mentions in persona responses, feed signals to orchestrator
- **Local Gemma 27B** — `--free` runs the interviewer locally via transformers (4-bit NF4 quantized), no API calls or rate limits
- **Key symptom tiebreaker** — top-4 symptoms now broken by confidence when scores are tied, not arbitrary dict order
- **Tree/LLM logging** — pipeline logs whether each turn used a tree question or LLM-generated question

## Architecture

```
Persona (LLaMA 8B + LoRA)
    ↕ conversation
Interviewer Agent (Gemma 27B local or GPT)
    ← guided by Orchestrator (deterministic, no LLM)
    ← tree-first: BM25 dialogue tree → LLM fallback
    ← labeling functions detect symptoms in persona responses
Scoring Agent (GPT, always paid)
    → 21 BDI-II symptom scores + confidence + evidence
    ↓
Run ~30 interviews per persona
    ↓
Weaver Aggregation
    → pairwise agreement weights → consensus profile → rank by L1 distance
    → select top 3 runs for submission
```

## Model Routing

| Flag | Interviewer | Scorer |
|------|-------------|--------|
| (default) | `gpt-5-nano` (paid API) | `gpt-5-nano` (paid API) |
| `--free` | `gemma-3-27b-it` (local GPU, 4-bit) | `gpt-5-nano` (paid API) |

The `--free` flag loads Gemma 27B locally with 4-bit NF4 quantization via bitsandbytes. Fits on a single V100 (32GB). Model is loaded once and reused across all turns and personas in the same process.

To revert to the old Google AI Studio API route, change `FREE_DEFAULT` in `src/llm.py` back to `"gemini:gemma-3-27b-it"` and uncomment the deprecated code blocks.

## CLI Flags

```
--personas N [N ...]        Persona IDs to interview (default: 1 2)
--run-id {1,2,3}            Submission run number
--mock-persona              Use canned responses instead of Llama model
--free                      Use local Gemma 27B for interviewer (scorer always paid)
--max-turns N               Max conversation turns (default: 18)
--ensemble-size N           Scorer passes per turn (1=fast, 3=accurate)
--score-every-n N           Score every Nth turn (default: 1)
--confidence-threshold F    Stopping threshold (default: 0.6)
--tree-threshold F          BM25 match threshold (default: 1.5)
--output-dir PATH           Output directory for results
--quiet                     Suppress verbose output
```

Dialogue tree and labeling functions are always enabled. Scorer always uses `gpt-5-nano`.

### select_runs.py

```
python select_runs.py <persona_id>
  --free          Use samples-free directory
  --mix           Pool paid + free samples
  --top N         Number of runs to select (default: 3)
  --csv           Export scores to CSV
  --legacy        Use old heuristic instead of Weaver
```

### visualize.py

Generates 17 comparison charts (base vs new) from CSVs in `results/`:

```
python visualize.py
python visualize.py --results-dir results/ --output-dir results/figures/
```

## PACE Workflow

```bash
# SSH + allocate GPU
ssh vgong7@login-phoenix.pace.gatech.edu
salloc -N 1 --gres=gpu:V100:1 -t 2:00:00 --account=paceship-dsgt_clef2026

# Submit batch of 20 free samples for persona 11
sbatch --job-name=11 --array=1-20 batch.sh 11 --free

# Submit 10 paid baseline samples
sbatch --job-name=11 --array=1-10 batch.sh 11

# Monitor jobs
squeue -u vgong7

# After jobs finish, select top 3 runs
python select_runs.py 11 --mix

# Copy submissions to local
scp -r vgong7@login-phoenix.pace.gatech.edu:~/scratch/erisk-2026/user/victor/experiments/004-weaver/submissions/ ~/Downloads/submissions/
```

## Results

Results CSVs are in `results/` with per-sample BDI scores, confidence, turns, and key symptoms. Figures are generated to `results/figures/` by `visualize.py`.

Evidence from personas 7–12:
- **Lower variance** in 4 of 6 personas (strongest: P11 std 13.96→7.79, P12 std 9.76→5.58)
- **Tighter turn spread** averaging ~11.5 turns (std 2.34) vs baseline ~10.74 (std 2.70)
- **Lower confidence** (0.459 vs 0.508) — free model produces thinner evidence strings
- **Severity shift** toward moderate/mild — undershooting likely caused by fewer assessed GENTLE_PROBE symptoms in shorter interviews

No ground truth available until eRisk evaluation in May 2026.

## Related

- [Experiment Proposal](PROPOSAL.md) — features implemented and rationale
- [003-open-source](../003-open-source/) — predecessor without Weaver/tree
