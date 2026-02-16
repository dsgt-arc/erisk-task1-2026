# Documentation

Documentation for the eRisk 2026 Task 1 project: Conversational Depression Detection.

---

## 📋 Research Proposal

- **[eRisk 2026 Research Proposal](references/2026-02-09-erisk-2026-research-proposal.md)** - Official project proposal with objectives, timeline, and methodology

---

## 💡 Concepts (Research Ideas)

Architectural approaches and design decisions:

| Concept | Description | Status |
|---------|-------------|--------|
| **[Multi-Head Symptom Regression](concepts/multi-head-symptom-regression.md)** | RoBERTa + 21 independent regression heads for BDI-II scoring | ✅ Implemented |
| **[Adaptive Interview Policies](concepts/adaptive-interview-policies.md)** | Semi-structured question selection with mention detection | ✅ Implemented |

**Add new concepts:** Use `/docs:concept` command

---

## 📚 References

### Research Proposals
- [eRisk 2026 Research Proposal](references/2026-02-09-erisk-2026-research-proposal.md) (2026-02-09)

### Literature
- [references/literature/](references/literature/) - Papers and articles

### Deep Research (AI Syntheses)
- [references/deep-research/](references/deep-research/) - AI research outputs

**Add new references:** Use `/docs:reference` command

---

## 🔧 Vendor Documentation

External tools and assessment instruments:

| Tool | Description | Documentation |
|------|-------------|---------------|
| **BDI-II** | Beck Depression Inventory-II | [vendor/bdi-ii.md](vendor/bdi-ii.md) |

**Add new vendor docs:** Use `/docs:vendor` command

---

## 📖 Guides

| Guide | Description |
|-------|-------------|
| [Getting Started](guides/getting-started.md) | Fork, setup, first experiment |
| [Agent Tooling](guides/agent-tooling.md) | Skills, slash commands, and OpenSpec explained |
| [Claude Commands](guides/claude-commands.md) | Slash command reference |
| [OpenSpec](guides/openspec.md) | OPSX spec-driven development workflow |
| [PACE Setup](guides/pace-setup.md) | PACE cluster environment setup |

---

## 📁 Directory Structure

```
docs/
├── README.md           # This file
├── concepts/           # Research ideas and hypotheses
│   ├── multi-head-symptom-regression.md
│   └── adaptive-interview-policies.md
├── references/
│   ├── 2026-02-09-erisk-2026-research-proposal.md
│   ├── literature/     # Papers and articles
│   └── deep-research/  # AI research outputs
├── vendor/             # External tool documentation
│   └── bdi-ii.md       # Beck Depression Inventory-II
├── guides/             # How-to documentation
│   ├── getting-started.md
│   ├── agent-tooling.md
│   ├── claude-commands.md
│   ├── openspec.md
│   └── pace-setup.md
└── _templates/         # Document templates (don't modify)
    ├── concept.md
    ├── reference.md
    ├── experiment-proposal.md
    ├── experiment-result.md
    ├── experiment-tasks.md
    └── experiment-design.md
```

---

## 🎯 Document Types & Usage

### Concepts
- **Purpose:** Capture testable research ideas and hypotheses
- **Command:** `/docs:concept`
- **Naming:** `kebab-case-name.md`
- **Example:** `multi-head-symptom-regression.md`

### References
- **Purpose:** External knowledge (papers, articles, proposals)
- **Command:** `/docs:reference`
- **Naming:** `YYYY-MM-DD-descriptive-name.md`
- **Example:** `2026-02-09-erisk-2026-research-proposal.md`

### Vendor Documentation
- **Purpose:** Document external tools, datasets, APIs
- **Command:** `/docs:vendor`
- **Naming:** `tool-name.md`
- **Example:** `bdi-ii.md`

---

## 🔄 Research Workflow

```
Reference → Concept → Experiment Proposal → Results
    ↓          ↓              ↓                ↓
 papers     ideas      test hypothesis    document
```

1. **Capture knowledge:** Use `/docs:reference` for papers/articles
2. **Form ideas:** Use `/docs:concept` for testable hypotheses
3. **Run experiments:** Use `/experiment:proposal` to structure work
4. **Document results:** Use `/experiment:result` to record outcomes

---

## Related

- **Experiments:** [user/victor/experiments/](../user/victor/experiments/)
- **Project README:** [README.md](../README.md)
- **AI Assistant Guide:** [CLAUDE.md](../CLAUDE.md)
