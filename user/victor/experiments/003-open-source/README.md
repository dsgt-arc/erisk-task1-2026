# Experiment 003: Open-Source Pipeline via OpenRouter

Multi-agent depression detection for eRisk 2026 Task 1, now routing all LLM calls through OpenRouter with support for free open-source models.

## Quick Start

```bash
# Install dependencies
cd /path/to/erisk-2026
uv sync --package 003-open-source

# Set API key
export OPENROUTER_API_KEY="your-key"

# Run with free open-source models (no cost)
cd user/victor/experiments/003-open-source/src
python run.py --mock-persona --free --personas 1

# Run with paid models
python run.py --mock-persona --personas 1 2 3

# Mix models (free interviewer, paid scorer)
python run.py --mock-persona --interviewer-model meta-llama/llama-3.1-8b-instruct:free --scorer-model openai/gpt-4.1-mini
```

## What Changed from 002

- **OpenRouter migration** — single API endpoint for all models (OpenAI, Anthropic, Meta, Google, Mistral)
- **`--free` flag** — zero-cost interviews using `meta-llama/llama-3.1-8b-instruct:free`
- **Removed Anthropic SDK** — everything goes through OpenRouter's OpenAI-compatible API
- **Research proposals** — Weaver aggregation + dialogue tree (see [PROPOSAL.md](PROPOSAL.md))

## CLI Flags

```
--personas N [N ...]        Persona IDs to interview (default: 1 2)
--run-id {1,2,3}            Submission run number
--mock-persona              Use canned responses instead of Llama model
--free                      Use free open-source models (zero cost)
--interviewer-model STR     OpenRouter model string for interviewer
--scorer-model STR          OpenRouter model string for scorer
--max-turns N               Max conversation turns (default: 18)
--ensemble-size N           Scorer passes per turn (1=fast, 3=accurate)
--score-every-n N           Score every Nth turn (default: 1)
--confidence-threshold F    Stopping threshold (default: 0.6)
--quiet                     Suppress verbose output
```

Model priority: explicit `--*-model` > `--free` > paid default (`openai/gpt-4.1-mini`)

## Related

- [Experiment Proposal](PROPOSAL.md) — includes Weaver + dialogue tree research directions
- [002-multi-agent](../002-multi-agent/) — predecessor with direct OpenAI/Anthropic API calls
