# Experiment 001: Baseline MVP Pipeline

End-to-end implementation of the eRisk 2026 Task 1 conversational depression detection system.

## Quick Start

```bash
# From repository root
cd /Users/victor/Documents/GeorgiaTech/Research/erisk-2026-task-1

# Install dependencies
uv sync --package 001-baseline-mvp

# Activate environment
source .venv/bin/activate

# Set API keys
export OPENAI_API_KEY="your-key-here"
# or
export ANTHROPIC_API_KEY="your-key-here"

# Run the pipeline
cd user/victor/experiments/001-baseline-mvp/src
python pipeline.py
```

## What This Experiment Does

Implements and validates the complete MVP architecture:

1. **QuestionBank** - 21 BDI-II symptom question templates
2. **InterviewPolicy** - Semi-structured adaptive question selection
3. **SymptomDetector** - LLM-based symptom mention detection (all 21 symptoms)
4. **LLMSymptomScorer** - Zero-shot LLM scoring with clinical prompts
5. **ScoringPipeline** - Conversation analysis → BDI-II scores → severity band

## Directory Structure

```
001-baseline-mvp/
├── PROPOSAL.md           # Experiment proposal and hypothesis
├── README.md             # This file
├── pyproject.toml        # Dependencies
├── src/
│   ├── __init__.py
│   ├── llm.py            # LLM provider interface
│   └── pipeline.py       # Main MVP implementation
├── data/                 # Training data (when available)
├── results/              # Outputs, checkpoints, metrics
└── notebooks/            # Analysis and visualization
```

## Architecture

See `PROPOSAL.md` for detailed architecture description.

**Key Components:**
- LLM-based symptom detection (supports all 21 BDI-II symptoms)
- Zero-shot conversation scoring with clinical prompting
- Adaptive follow-ups based on mention detection
- Turn budget enforcement (max 20 turns)
- Provider flexibility (OpenAI, Anthropic)

## Current Status

**MVP Implementation:** ✅ Complete
- All components implemented and integrated
- LLM-based symptom detection for all 21 symptoms
- LLM-based conversation scoring
- Ready for real persona API integration

**Next Steps:**
1. Implement `query_persona()` with real eRisk API endpoint
2. Test with released persona models (Feb 16, 2026)
3. Evaluate prompt engineering variations
4. Compare multiple LLM providers (GPT-4o-mini vs Claude Haiku)

## Extending This Experiment

### Add Real Persona API

Implement `query_persona()` in `src/pipeline.py`:

```python
def query_persona(persona_id: str, question: str) -> str:
    """Query a real LLM persona via the eRisk 2026 API."""
    import requests
    response = requests.post(
        "https://erisk-api.example.com/persona/query",
        json={"persona_id": persona_id, "question": question},
        headers={"Authorization": f"Bearer {os.getenv('ERISK_API_KEY')}"}
    )
    return response.json()["response"]
```

### Switch LLM Providers

Modify `main()` in `src/pipeline.py`:

```python
# Use OpenAI (default)
symptom_detector = SymptomDetector(provider="openai", model="gpt-4o-mini")
scoring_pipeline = ScoringPipeline(provider="openai", model="gpt-4o-mini")

# Or use Anthropic
symptom_detector = SymptomDetector(provider="anthropic", model="claude-3-5-haiku-20241022")
scoring_pipeline = ScoringPipeline(provider="anthropic", model="claude-3-5-haiku-20241022")
```

### Optimize Prompts

Edit prompts in `SymptomDetector._build_prompt()` and `LLMSymptomScorer._build_scoring_prompt()` to test different prompt engineering strategies.

## Related Documents

- [Experiment Proposal](PROPOSAL.md)
- [Research Proposal](../../../../docs/references/research-proposal-erisk-2026.md)
- [Project README](../../../../README.md)
