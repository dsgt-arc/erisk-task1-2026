# Experiment 001: Baseline MVP Pipeline

**Author:** Victor Gong (vgong7@gatech.edu)
**Date:** 2026-02-10
**Status:** In Progress

## Hypothesis

A semi-structured conversational interview system using RoBERTa-based multi-task regression with adaptive question selection can effectively estimate BDI-II depression severity scores from interactions with LLM personas.

## Background

eRisk 2026 Task 1 requires systems to conduct limited-turn conversations with LLM personas that simulate different depression profiles according to BDI-II standards. Unlike traditional text classification approaches that passively analyze existing posts, this task demands:

1. **Active interviewing** - The system must ask questions strategically
2. **Clinical structure** - Questions should target all 21 BDI-II symptoms
3. **Adaptive behavior** - Follow-up questions based on detected symptoms
4. **Constraint handling** - Limited turns per persona (prompt budget)

This baseline MVP establishes the foundational architecture and validates the approach end-to-end before integrating real persona APIs and training data.

## Method

### Architecture

**1. Question Bank**
- Hardcoded question templates for each of 21 BDI-II symptoms
- Multiple question types: broad (open-ended), follow-up (probing), severity (intensity)
- Enables semi-structured interviews with variation

**2. Interview Policy (Semi-Structured + Adaptive)**
- **Early phase (turns 0-10):** Prioritize high-risk symptoms
  - Sadness, Loss of pleasure, Suicidal thoughts, Loss of energy, Sleep changes
- **Mid-phase (turns 10-15):** Adaptive follow-ups based on mention detection
  - If sleep mentioned → ask follow-up sleep questions
- **Late phase (turns 15+):** Ensure coverage of remaining symptoms
- **Constraints:** Max 2-3 questions per symptom, max 20 total turns

**3. Mention Detector**
- TF-IDF + Logistic Regression classifier
- **Baseline scope:** Sleep symptom only (proof of concept)
- Trained on synthetic examples (positive: sleep complaints, negative: generic statements)
- Enables policy to detect implicit mentions and adapt

**4. Symptom Regressor**
- **Backbone:** RoBERTa-base (pre-trained transformer)
- **Architecture:** 21 independent MLP heads (one per BDI-II symptom)
  - Hidden layer: 768 → 64 → 1
  - ReLU activation, dropout 0.1
- **Pooling:** CLS token from RoBERTa last hidden state
- **Loss:** MSE (mean squared error) per symptom

**5. Scoring Pipeline**
- Score each persona utterance: N messages → N×21 score matrix
- **Aggregation:** Max-pooling per symptom (column-wise)
  - Rationale: Strongest symptom evidence matters most
- Clamp scores to BDI-II item range [0, 3]
- Sum to total BDI-II score [0, 63]
- Map to severity bands (minimal/mild/moderate/severe)

### Data Flow

```
1. Policy selects question based on conv state
   ↓
2. System asks → Persona replies (simulated)
   ↓
3. MentionDetector analyzes reply
   ↓
4. Policy adapts (follow-up if symptom detected)
   ↓
5. Repeat until turn budget exhausted
   ↓
6. ScoringPipeline:
   - RoBERTa encodes all persona messages
   - 21 heads score each message
   - Max-pool per symptom
   - Clamp [0,3] → Sum → Severity band
```

### Current Limitations (MVP Scope)

**Stub Implementations:**
- **Persona simulation:** Keyword-based canned responses
  - Production: Replace with real eRisk LLM persona API
- **Training data:** Synthetic random labels for demonstration
  - Production: Train on real eRisk conversations with BDI-II labels

**Mention Detector:**
- Only detects sleep symptoms currently
- Future: Expand to all 21 symptoms

**No real evaluation yet:**
- Need actual persona models (released Feb 16+)
- Need validation set with ground-truth BDI-II scores

## Success Criteria

### MVP Validation (This Experiment)

✅ **Must Have:**
- [ ] All components implemented and integrated
- [ ] End-to-end pipeline runnable (demo mode)
- [ ] Produces valid BDI-II scores [0-63] and severity bands
- [ ] Interview policy respects turn constraints
- [ ] Code is modular and extensible

🎯 **Nice to Have:**
- [ ] Mention detector works on synthetic sleep examples
- [ ] Training loop demonstrates how to fine-tune model
- [ ] Clear interfaces for swapping stub implementations

### Future Experiments (Post-MVP)

Once real data becomes available:
- **Experiment 002:** Integrate real persona APIs (Feb 16+)
- **Experiment 003:** Train on labeled data, evaluate on validation set
- **Experiment 004:** Expand MentionDetector to all symptoms
- **Experiment 005:** Compare pooling strategies (max vs. mean vs. attention)
- **Experiment 006:** Optimize question selection policy (RL?)

**Competition Target Metrics:**
- Mean Absolute Error (MAE) on BDI-II total score: < 5.0
- Item-level correlation: > 0.6
- Severity band accuracy: > 70%

## Tasks

- [x] Define BDI-II symptom constants and mappings
- [x] Implement core data classes (Question, Message, Conversation)
- [x] Build QuestionBank with hardcoded questions
- [x] Implement MentionDetector with synthetic sleep training
- [x] Implement InterviewPolicy with adaptive logic
- [x] Implement SymptomRegressor (RoBERTa + 21 heads)
- [x] Implement ScoringPipeline (pooling + aggregation)
- [x] Create persona simulation stub
- [x] Create interview runner orchestration
- [x] Add main() demo
- [ ] Run end-to-end test and validate outputs
- [ ] Document architecture and extension points
- [ ] Create README for experiment directory
- [ ] (Optional) Add unit tests for key components
- [ ] (Optional) Create Jupyter notebook for result analysis

## Expected Outcomes

**Code Deliverables:**
- Fully functional MVP pipeline in `src/pipeline.py`
- Modular design enabling easy extension
- Clear stubs for real API/data integration

**Validation:**
- Demo successfully runs simulated interview
- Produces reasonable BDI-II scores and severity classification
- Policy adapts based on sleep mentions

**Documentation:**
- This proposal document
- Code comments and docstrings
- Architecture diagram in results/

**Learnings:**
- Validate whether message-level scoring + max-pooling is reasonable
- Identify bottlenecks in the interview policy
- Understand computational requirements (inference time per conversation)

## Timeline

- **Week 1 (Feb 10-16):** ✅ MVP implementation complete
- **Week 2 (Feb 17-23):** Integrate first real persona models, test on real API
- **Week 3 (Feb 24-Mar 2):** Collect training data, begin model fine-tuning
- **Week 4 (Mar 3-9):** Evaluate baseline, document results

## Notes

**Related Documents:**
- Research proposal: `/Users/victor/Downloads/Research Proposals_ eRisk 2026 - Google Drive.pdf`
- MVP specification: `/Users/victor/Downloads/given my research proposal here + our discussion,.md`

**Next Experiments:**
- 002: Real persona integration
- 003: Model training with labeled data
- 004: Mention detector expansion
- 005: Policy optimization
