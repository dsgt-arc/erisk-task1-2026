# Experiment 002: Multi-Agent Depression Detection Pipeline

**Author:** Victor Gong (vgong7@gatech.edu)
**Date:** 2026-02-28
**Status:** Implemented, local validation complete

## Hypothesis

Splitting the single-LLM interview+scoring pipeline into three specialized agents (interviewer, scorer, orchestrator) will produce more consistent BDI-II scores by eliminating the conflict between asking good questions and tracking 21 symptoms simultaneously.

## Background

The 001-baseline-mvp used a single LLM that interviewed AND scored in one pass. Problems observed:
- Scorer loses track of symptoms over long conversations
- Inconsistent scores across runs (LLM tries to do too much)
- No confidence tracking — can't tell which symptoms were actually assessed

## Method

### Architecture: Three Agents

```
Persona responds
    → Scorer analyzes full transcript (21 scores + confidence + evidence)
    → Orchestrator picks focus areas (pure Python, no LLM)
    → Interviewer asks next question (guided by orchestrator)
    → Persona responds → ...
```

**Scorer** (LLM, stateless): Receives full transcript each call. Outputs JSON with score (0-3), confidence (0-1), and evidence quote per symptom. Supports ensemble mode (multiple passes, median aggregation). Confidence calibration clamps overconfident thin-evidence scores.

**Orchestrator** (pure Python, no LLM): Three-tier probe strategy — active probe (9 symptoms like sadness, sleep), gentle probe (8 symptoms like guilt, irritability), never probe (4 sensitive items like suicidal thoughts, sex). Stops when: max turns reached, all probeable symptoms confident, or scores stabilize. Groups focus symptoms by cluster for natural conversation flow.

**Interviewer** (LLM): Receives conversation history + orchestrator guidance. Outputs plain text only — no scoring burden. Empathetic, follows guidance on which symptoms to explore.

### Key Design Decisions

1. **Orchestrator is algorithmic, not LLM** — deterministic, zero cost, fast
2. **Scorer is stateless** — full transcript each call, no accumulated drift
3. **Confidence calibration** — "Not assessed" → 0.0, thin evidence capped at 0.3, single-pass capped at 0.9
4. **Symptom clusters** — related symptoms grouped (mood, physical, cognition, etc.) so interviewer asks natural follow-ups
5. **score_every_n_turns** — configurable scoring frequency to control API costs

## Success Criteria

- [x] All agents implemented and tested (32 unit + integration tests)
- [x] End-to-end pipeline produces valid BDI-II scores and eRisk submission files
- [x] Validated with mock persona + real OpenAI API calls
- [ ] Test on PACE cluster with real Llama persona models
- [ ] Compare scores against 001-baseline on same personas

## Results (Local Mock Test)

Persona 0 (mock, moderate depression), 5 turns, ensemble=1:
- BDI score: 16 (Mild)
- Correctly scored: sadness (1), anhedonia (2), sleep (3), appetite (3), energy (2), fatigue (2), loss of interest (3)
- Unassessed symptoms correctly got confidence 0.0
- Evidence quotes directly from transcript
- Total time: ~3 min (10 API calls)
