# erisk-2026
Mental health risk detection on the Internet for the CLEF eRisk 2026 competition.

## Approaches
**Task 1: Conversational Depression Detection**

Multi-agent interview system (interviewer + scorer + orchestrator) that conducts adaptive BDI-II depression screening conversations with LLM-simulated personas (LLaMA 8B + LoRA). Scores 21 BDI-II symptoms per persona across 3 independent runs.

- `001-baseline-mvp` — Single-LLM interview + scoring baseline (archived)
- `002-multi-agent` — Three-agent architecture with GPT (archived)
- `003-open-source` — **Baseline** OpenAI for both conversation & scoring agents, no programmatic supervision.
- `004-weaver` — **Active.** Weaver run selection, BM25 dialogue tree, labeling functions, cluster imputation. Free Gemma 27B interviewer + paid GPT scorer.

**Task 2: Contextualised Early Detection of Depression**

**Task 3: Sentence Ranking for ADHD Symptoms**

## Repository Structure
```
├── docs/                   # Research documentation
│   ├── references/         # External sources (papers, proposals)
│   ├── concepts/           # Ideas and hypotheses
│   └── vendor/             # External tool docs
├── openspec/               # Spec-driven development (code changes)
│   ├── specs/              # What IS built
│   └── changes/            # What should change
├── skills/                 # Custom Claude Code skills
│   ├── experiment/         # Experiment management
│   └── research-docs/      # Documentation tools
└── user/                   # Individual workspaces
    └── <username>/
        └── experiments/    # Numbered experiments
```
