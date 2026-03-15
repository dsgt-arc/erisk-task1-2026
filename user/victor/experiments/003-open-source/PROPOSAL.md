# Experiment 003: Open-Source Multi-Agent Pipeline via OpenRouter

**Author:** Victor Gong (vgong7@gatech.edu)
**Date:** 2026-03-06
**Status:** In progress

## Hypothesis

Routing all LLM calls through OpenRouter and adding support for free open-source models enables cost-free batch processing of all 20 personas. Combined with Weaver-style weak verifier aggregation and a precomputed dialogue tree, open-source models can approach paid model accuracy.

## Background

Experiment 002 validated the multi-agent architecture (interviewer + scorer + orchestrator) using GPT-5-mini via direct OpenAI API calls. It works well but costs ~$0.03-0.05 per interview. Running 30 samples × 20 personas × 3 ensemble passes = 1,800 scorer calls gets expensive.

This experiment migrates to OpenRouter (unified API gateway) and adds free model support, laying groundwork for two research directions: Weaver aggregation and dialogue trees.

## Changes from 002-multi-agent

### 1. OpenRouter Migration (Implemented)

All LLM calls now route through OpenRouter's OpenAI-compatible endpoint:
- Single API key (`OPENROUTER_API_KEY`), single base URL
- Model selection via OpenRouter strings: `openai/gpt-4.1-mini`, `meta-llama/llama-3.1-8b-instruct:free`, etc.
- Removed direct Anthropic SDK dependency
- `--free` CLI flag for zero-cost open-source models

### 2. Free Model Support (Implemented)

- `--free` flag sets both interviewer and scorer to `meta-llama/llama-3.1-8b-instruct:free`
- `--interviewer-model` / `--scorer-model` for manual override
- Priority: explicit model flag > `--free` > paid default (`openai/gpt-4.1-mini`)

---

## Research Direction A: Weaver Algorithm for Weak Verifier Aggregation

**Paper:** "Shrinking the Generation-Verification Gap with Weak Verifiers" (Saad-Falcon et al., 2025, arXiv:2506.18203)

### Core Idea

The Weaver framework combines multiple imperfect "verifiers" via weighted ensembling to approximate a strong verifier. In their experiments, combining several small judge/reward models matched the jump from GPT-4o to o3-mini on reasoning tasks (69% → 87%).

### Application to Our Pipeline

Our **scorer agent** is a verifier — it reads a transcript and outputs BDI-II scores. Currently we ensemble multiple passes of the same model. Weaver suggests a better approach:

#### Multi-Model Ensemble Scoring
Instead of 3 passes of GPT-4.1-mini, run the scorer prompt through N different free models:
- `meta-llama/llama-3.1-8b-instruct:free`
- `google/gemma-2-9b-it:free`
- `mistralai/mistral-7b-instruct:free`
- `qwen/qwen-2.5-7b-instruct:free`

Each produces a 21-item BDI-II score vector. Aggregate with learned weights.

#### Weighted Aggregation (Weaver's Key Insight)
Not all verifiers are equal. Learn per-model reliability weights using:
1. **Agreement with paid model** — Run a calibration set of 5-10 transcripts through both GPT-4.1-mini and each free model. Weight by agreement rate.
2. **Internal consistency** — Does the model's confidence correlate with its evidence quality? Models with better self-calibration get higher weight.
3. **Weak supervision (no labels needed)** — Programmatic labeling functions:
   - "If persona mentions sleep problems, q08_sleep score should be > 0"
   - "If persona says 'I feel worthless', q14_worthlessness score should be >= 2"
   - Models that agree with these heuristics are weighted higher.

#### Output Normalization + Filtering
- Discard scorer outputs that fail JSON parsing
- Normalize score distributions (some models may systematically score higher/lower)
- Filter models that produce implausible patterns (e.g., all 0s or all 3s)

#### Confidence-Weighted Median
Instead of simple median, weight each model's vote by its estimated reliability:
```
final_score[symptom] = weighted_median(scores, weights)
```

### Open Questions
- **Calibration without ground truth:** We don't have real BDI-II labels. Can weak supervision alone estimate model accuracy?
- **Format compliance:** Can free 7B-8B models reliably output the structured JSON the scorer prompt requires? May need a simpler output format or post-processing.
- **Aggregation granularity:** Per-symptom weights (some models better at certain symptoms) vs. global per-model weights?
- **Cost-accuracy tradeoff:** Is 5 free models better than 1 paid model? What's the break-even point?

### Implementation Sketch (Future)
- `src/weaver.py` — Multi-model scorer runner + weight learning + aggregation
- `src/labeling_functions.py` — Snorkel-style programmatic labeling functions for weak supervision
- `data/calibration/` — Saved transcripts + paid model scores for weight calibration

---

## Research Direction B: Precomputed Dialogue Tree

### Problem

Open-source interviewer models (and even paid models) drift in conversation:
- Ask redundant questions already covered
- Miss symptom clusters the orchestrator asked them to probe
- Inconsistent question quality across runs
- Result: high variance in BDI-II scores

### Proposal: Hybrid Dialogue Tree + LLM Fallback

#### Layer 1: Precomputed Question Bank

Design 2-3 opener questions per BDI-II symptom cluster, plus 1-2 layers of follow-up:

| Cluster | Opener | Follow-up L1 | Follow-up L2 |
|---------|--------|-------------|-------------|
| Mood/Pleasure | "How have you been feeling overall lately?" | "Has anything been bringing you joy recently?" | "When was the last time you genuinely enjoyed something?" |
| Sleep/Energy | "How's your sleep been?" | "Do you feel rested when you wake up?" | "Has your energy level changed recently?" |
| Cognition | "How's your focus been at work or school?" | "Do you find it hard to make decisions?" | "Have you been more indecisive than usual?" |
| Self-Worth | "How do you feel about yourself these days?" | "Are you often hard on yourself?" | "Do you compare yourself to others a lot?" |
| Appetite/Weight | "How's your appetite been?" | "Have you noticed any changes in your weight?" | — |
| Social | "Have you been spending time with friends or family?" | "Do you ever feel like withdrawing from people?" | — |

#### Layer 2: BM25 Navigation

After the persona responds, determine which dialogue tree branch to follow:
1. BM25 index all possible tree nodes by keywords
2. Score the persona's response against tree nodes
3. If top BM25 score > threshold → use the precomputed follow-up question
4. If below threshold (off-topic or ambiguous) → fall back to LLM-generated question

This means many turns use **zero LLM calls** for the interviewer.

#### Layer 3: Snorkel Weak Supervision for Response Classification

Multiple simple labeling functions classify persona responses into symptom clusters:
- Keyword matchers: "sleep", "insomnia", "tired" → sleep cluster
- Regex patterns: r"can't (focus|concentrate)" → cognition cluster
- Negation detection: "I don't enjoy" → anhedonia
- Sentiment heuristics: strongly negative → mood cluster

Snorkel's label model resolves conflicts when multiple LFs fire. This guides the orchestrator's next focus selection without needing an LLM.

### Benefits
- **Consistency:** Same opening questions → comparable interviews across runs
- **Cost reduction:** Precomputed questions = zero LLM cost for those turns
- **Better with weak models:** Tree provides guardrails; LLM only fills gaps
- **Reproducibility:** Tree-based turns are deterministic
- **Faster interviews:** No LLM latency for tree-based turns

### Open Questions
- How many follow-up layers before LLM takes over? (Propose: 2 layers max)
- Should the tree cover all 21 BDI items or only the "safe to probe" ones from orchestrator's tier system?
- How to handle natural transitions between clusters? (Risk of feeling like a checklist)
- BM25 threshold tuning — too high = always falls back to LLM, too low = gives wrong follow-up

### Implementation Sketch (Future)
- `data/question_bank.json` — The precomputed question tree
- `src/dialogue_tree.py` — Tree loader, BM25 index, navigation logic
- `src/labeling_functions.py` — Shared with Weaver; Snorkel-style LFs for response classification
- `src/agents/interviewer.py` — Modified: check tree first, fallback to LLM
- Python packages: `rank_bm25`, `snorkel` (or lightweight custom label model)

---

## Success Criteria

- [x] OpenRouter migration working (all models accessible via single API)
- [x] `--free` flag enables zero-cost interviews
- [ ] Validate free model output quality (can Llama-3.1-8B follow scorer prompt?)
- [ ] Implement Weaver multi-model ensemble scorer
- [ ] Build and test dialogue tree question bank
- [ ] Compare: free models + Weaver vs. single paid model on same personas
