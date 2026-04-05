# Experiment 004: Weaver Run Selection + Dialogue Tree

**Author:** Victor Gong (vgong7@gatech.edu)
**Date:** 2026-03-15 (updated 2026-04-05)
**Status:** In progress — personas 7–12 submitted, local Gemma 27B added

## What We Built

- **Weaver-aggregated run selection** — replaces the heuristic in `select_runs.py` (60% BDI median proximity + 40% symptom consensus) with per-sample reliability weights learned from pairwise agreement across 21 BDI-II symptoms. Builds a consensus BDI profile via weighted median and selects runs closest to consensus.

- **Precomputed dialogue tree** — structured question bank (~30-40 nodes in `data/question_bank.yaml`) with BM25 followup navigation. Covers 6 symptom clusters with 2-3 openers + 1-2 follow-up layers each. The interviewer checks the tree first and falls back to LLM generation when no good match exists.

- **Labeling functions** — lightweight keyword/regex classifiers (`src/labeling_functions.py`) that detect symptom mentions and severity signals in persona responses. Feeds into the orchestrator to boost priority of detected symptoms without any LLM calls.

## Why It Matters

- **Better run selection**: The old heuristic collapses 21 symptom scores into one number (total BDI) and weights all samples equally. Weaver looks at all 21 symptoms independently and automatically down-weights outlier interviews where the model hallucinated or the conversation went sideways. Grounded in weak supervision theory (Saad-Falcon et al., 2025, arXiv:2506.18203).

- **Interview consistency**: LLM-generated questions drift, miss symptom clusters, and vary widely across runs — especially with free/open-source models. The dialogue tree standardizes openers and first follow-ups, reducing score variance and ensuring all symptom clusters get covered.

- **Cost reduction**: Tree-driven turns use zero LLM calls for the interviewer. Labeling functions replace LLM-based response classification for the orchestrator. Local Gemma 27B (4-bit quantized) eliminates API calls entirely for the interviewer, avoiding TPM rate limits.

- **Open-source model friendly**: Both features compensate for weaker instruction-following in free models. The tree provides guardrails so the interviewer can't go off-script. Weaver aggregation recovers signal from noisy scores by leveraging agreement patterns. Running Gemma locally on V100 avoids rate limits that caused sample failures with the Google AI Studio API.

## Hypothesis

Combining Weaver-style run selection with a precomputed dialogue tree reduces BDI score variance across runs and improves the consistency of selected submissions, compared to the 003 baseline using simple heuristic selection and fully LLM-driven interviews.

## Background

Experiment 003 validated the three-agent architecture (interviewer + scorer + orchestrator) with free model support. Batch runs of 30 samples per persona showed high variance in BDI scores (stdev 3-5 points). The selection heuristic often picked runs that agreed on total score but diverged on individual symptoms. Interviews with free models frequently missed symptom clusters or asked redundant questions.

## Changes from 003-open-source

1. **`src/weaver.py`** (new) — `WeaverAggregator` class with `learn_weights()`, `consensus_profile()`, `rank_samples()`
2. **`select_runs.py`** (rewritten) — Weaver ranking replaces heuristic; `--legacy` flag for comparison
3. **`data/question_bank.yaml`** (new) — 6 clusters, ~12 openers, ~20 followups
4. **`src/dialogue_tree.py`** (new) — `load_bank()`, `get_opener()`, `get_followup()` with BM25
5. **`src/labeling_functions.py`** (new) — `detect_symptoms()` with keyword/regex rules
6. **`src/agents/interviewer.py`** (modified) — tree-first dispatcher with LLM fallback
7. **`src/agents/orchestrator.py`** (modified) — accepts LF signals, boosts detected symptom priority
8. **`src/pipeline.py`** (modified) — integrates LFs, logs tree vs LLM source per turn; top-4 symptom ties broken by confidence
9. **`src/llm.py`** (modified) — local Gemma 27B via transformers (4-bit NF4 quantization) replaces Google AI Studio API; old API code commented out
10. **`visualize.py`** (new) — generates 17 comparison charts from results CSVs (base vs new)
11. **CLI cleanup** — removed `--use-tree`, `--use-lf`, `--manual`, `--interviewer-model`, `--scorer-model`; tree and LFs always on, model decided by `--free`

## Success Criteria

- [ ] Weaver selection produces lower per-symptom variance than legacy heuristic
- [ ] Dialogue tree covers all active-probe clusters in first 8 turns
- [ ] Tree-driven interviews achieve comparable BDI scores to LLM-only interviews
- [ ] `tree_turns / total_turns` ratio > 40% with dialogue tree enabled
- [ ] Labeling functions correctly detect >80% of explicitly mentioned symptoms
