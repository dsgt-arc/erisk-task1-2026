# erisk-2026
Mental health risk detection on the Internet for the CLEF eRisk 2026 competition.

## Approaches
**Task 1: Conversational Depression Detection**

Multi-agent interview system (interviewer + scorer + orchestrator) that conducts adaptive BDI-II depression screening conversations with LLM-simulated personas (LLaMA 8B + LoRA). Scores 21 BDI-II symptoms per persona across 3 independent runs.

- `001-baseline-mvp` — Single-LLM interview + scoring baseline (archived)
- `002-multi-agent` — Three-agent architecture with GPT (archived)
- `003-open-source` — **Baseline** OpenAI for both conversation & scoring agents, no programmatic supervision.
- `004-weaver` — **Active.** Weaver run selection, BM25 dialogue tree, labeling functions, cluster imputation. Free Gemma 27B interviewer + paid GPT scorer.

## Repository Structure
```
user/victor/experiments/
├── 001-baseline-mvp/       # Single-LLM interview + scoring (archived)
│   ├── src/                # Pipeline code
│   ├── results/            # Raw interview outputs
│   ├── submissions/        # Formatted FTP submissions
│   ├── prompts/            # System prompts
│   └── notebooks/          # Analysis notebooks
├── 002-multi-agent/        # Three-agent GPT architecture (archived)
│   ├── src/
│   │   └── agents/         # Interviewer, scorer, orchestrator
│   ├── results/
│   ├── submissions/
│   └── tests/
├── 003-open-source/        # OpenAI baseline, no programmatic supervision
│   ├── src/
│   │   └── agents/
│   ├── results/
│   └── submissions/
│       ├── samples-free/
│       ├── samples-paid/
│       └── samples-mix/
└── 004-weaver/             # Active — Weaver + BM25 tree + labeling fns
    ├── src/
    │   └── agents/         # interviewer.py, scorer.py, orchestrator.py
    ├── results/
    │   └── figures/        # Visualization outputs
    ├── submissions/        # persona-{N}/ dirs with top-3 runs
    ├── prompts/
    └── notebooks/
```
