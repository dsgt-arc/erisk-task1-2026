# Experiment 002: Multi-Agent Pipeline

Multi-agent conversational depression detection for eRisk 2026 Task 1. Three agents (interviewer, scorer, orchestrator) replace the single-LLM approach from 001-baseline-mvp.

## Quick Start

```bash
# Install dependencies
cd /path/to/erisk-2026
uv sync --package 002-multi-agent

# Set API keys
export OPENAI_API_KEY="your-key"

# Run with mock persona (no GPU needed)
cd user/victor/experiments/002-multi-agent/src
python run.py --mock-persona --personas 0 --max-turns 10

# Run with real Llama persona (requires GPU)
python run.py --personas 1 2 3 --max-turns 18 --ensemble-size 3
```

## Architecture

```
Scorer (LLM)  ──→  Orchestrator (Python)  ──→  Interviewer (LLM)
   ↑ full              picks focus              asks question ↓
   │ transcript         symptoms                              │
   └──────────────── Persona responds ←───────────────────────┘
```

| Agent | Type | Responsibility |
|-------|------|----------------|
| Scorer | LLM | Score 21 BDI-II symptoms with confidence + evidence |
| Orchestrator | Pure Python | Select focus symptoms, decide when to stop |
| Interviewer | LLM | Ask empathetic questions following orchestrator guidance |

## Directory Structure

```
002-multi-agent/
├── src/
│   ├── models.py              # Shared data classes
│   ├── agents/
│   │   ├── scorer.py          # BDI-II scorer (LLM, ensemble support)
│   │   ├── orchestrator.py    # Algorithmic orchestrator (no LLM)
│   │   └── interviewer.py     # Conversational interviewer (LLM)
│   ├── pipeline.py            # Main interview loop
│   ├── run.py                 # CLI entry point
│   ├── submission.py          # eRisk submission format export
│   ├── llm.py                 # LLM provider interface
│   └── persona.py             # Llama persona loader
├── prompts/
│   ├── scorer.md              # Full BDI-II rubric with score anchors
│   └── interviewer.md         # Conversational guidelines
├── tests/                     # 32 tests (models, agents, pipeline)
└── results/                   # Submission output files
```

## CLI Flags

```
--personas N [N ...]       Persona IDs to interview (default: 1 2)
--run-id {1,2,3}           Submission run number
--mock-persona             Use canned responses instead of Llama model
--max-turns N              Max conversation turns (default: 18)
--ensemble-size N          Scorer passes per turn (1=fast, 3=accurate)
--score-every-n N          Score every Nth turn (default: 1)
--confidence-threshold F   Stopping threshold (default: 0.6)
--interviewer-provider     openai or anthropic
--scorer-provider          openai or anthropic
--quiet                    Suppress verbose output
```

## Tests

```bash
cd user/victor/experiments/002-multi-agent
uv run --no-project --python 3.11 pytest tests/ -v
```

## Related

- [Experiment Proposal](PROPOSAL.md)
- [001-baseline-mvp](../001-baseline-mvp/) — predecessor single-agent approach
