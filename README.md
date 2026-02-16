# erisk-2026
Mental health risk detection on the Internet for the CLEF eRisk 2026 competition.

## Approaches
**Task 1: Conversational Depression Detection**

Adaptive interview system:
- Semi-structured question policy (prioritize high-risk symptoms)
- LLM-based symptom detection for adaptive follow-ups
- Zero-shot scoring via clinical prompt engineering

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
