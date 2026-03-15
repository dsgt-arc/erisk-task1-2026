# Experiment 004: Weaver Run Selection + Dialogue Tree

Multi-agent depression detection for eRisk 2026 Task 1 with Weaver-style run selection and precomputed dialogue tree for interview consistency.

## Quick Start

```bash
# Install dependencies
cd /path/to/erisk-2026
uv sync --package 004-weaver

# Set API keys
export OPENAI_API_KEY="your-key"
export GOOGLE_AI_API_KEY="your-key"

# Run with dialogue tree + labeling functions
cd user/victor/experiments/004-weaver/src
python run.py --mock-persona --personas 1 --use-tree --use-lf

# Run without tree (same as 003 behavior)
python run.py --mock-persona --personas 1

# Select runs with Weaver aggregation
cd ..
python select_runs.py 5 --mix

# Compare with legacy heuristic
python select_runs.py 5 --mix --legacy
```

## What Changed from 003

- **Weaver run selection** — replaces 60% median + 40% consensus heuristic with per-sample reliability weights learned from pairwise agreement across 21 BDI-II symptoms
- **Dialogue tree** — precomputed question bank (~30 nodes) with BM25 followup matching, LLM fallback for off-tree responses
- **Labeling functions** — keyword/regex classifiers detect symptom mentions in persona responses, feed signals to orchestrator
- **Tree/LLM logging** — pipeline logs whether each turn used a tree question or LLM-generated question

## CLI Flags

```
--personas N [N ...]        Persona IDs to interview (default: 1 2)
--run-id {1,2,3}            Submission run number
--mock-persona              Use canned responses instead of Llama model
--free                      Use free open-source models (zero cost)
--interviewer-model STR     Model string for interviewer
--scorer-model STR          Model string for scorer
--max-turns N               Max conversation turns (default: 18)
--ensemble-size N           Scorer passes per turn (1=fast, 3=accurate)
--score-every-n N           Score every Nth turn (default: 1)
--confidence-threshold F    Stopping threshold (default: 0.6)
--use-tree                  Enable dialogue tree for interviewer
--tree-threshold F          BM25 match threshold (default: 1.5)
--use-lf                    Enable labeling functions for orchestrator
--quiet                     Suppress verbose output
```

### select_runs.py

```
python select_runs.py <persona_id>
  --free          Use samples-free directory
  --mix           Pool paid + free samples
  --top N         Number of runs to select (default: 3)
  --csv           Export scores to CSV
  --legacy        Use old heuristic instead of Weaver
```

## Related

- [Experiment Proposal](PROPOSAL.md) — features implemented and rationale
- [003-open-source](../003-open-source/) — predecessor without Weaver/tree
