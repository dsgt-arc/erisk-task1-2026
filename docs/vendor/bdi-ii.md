# Beck Depression Inventory-II (BDI-II)

**Type:** Clinical Assessment Tool
**Version:** BDI-II (1996)
**Purpose:** Depression severity measurement
**Tags:** #assessment #depression #clinical #psychometrics

---

## Overview

The Beck Depression Inventory-II (BDI-II) is a 21-question multiple-choice self-report inventory used to measure the severity of depression in adults and adolescents aged 13 and above.

**Original Publication:** Beck, A. T., Steer, R. A., & Brown, G. K. (1996). *Manual for the Beck Depression Inventory-II.* San Antonio, TX: Psychological Corporation.

---

## Structure

### 21 Symptom Items

Each item corresponds to a specific symptom of depression:

| ID | Symptom | Description |
|----|---------|-------------|
| 1 | Sadness | Feeling sad or unhappy |
| 2 | Pessimism | Negative outlook on future |
| 3 | Past failure | Sense of having failed |
| 4 | Loss of pleasure | Anhedonia, loss of enjoyment |
| 5 | Guilty feelings | Excessive guilt |
| 6 | Punishment feelings | Expectation of punishment |
| 7 | Self-dislike | Negative self-perception |
| 8 | Self-criticalness | Excessive self-criticism |
| 9 | Suicidal thoughts or wishes | Thoughts of self-harm |
| 10 | Crying | Increased crying behavior |
| 11 | Agitation | Restlessness, irritability |
| 12 | Loss of interest | Reduced interest in people/activities |
| 13 | Indecisiveness | Difficulty making decisions |
| 14 | Worthlessness | Feeling worthless or useless |
| 15 | Loss of energy | Fatigue, low energy |
| 16 | Changes in sleeping pattern | Insomnia or hypersomnia |
| 17 | Irritability | Increased irritability |
| 18 | Changes in appetite | Decreased or increased appetite |
| 19 | Concentration difficulty | Trouble focusing or concentrating |
| 20 | Tiredness or fatigue | Physical exhaustion |
| 21 | Loss of interest in sex | Decreased libido |

### Scoring Scale

**Per Item:**
- Each item is rated on a 4-point scale: **0 to 3**
- Higher scores indicate greater symptom severity

**Examples:**

**Item 1 (Sadness):**
- 0: I do not feel sad
- 1: I feel sad much of the time
- 2: I am sad all the time
- 3: I am so sad or unhappy that I can't stand it

**Item 16 (Sleep):**
- 0: I have not experienced any change in my sleeping pattern
- 1a: I sleep somewhat more than usual
- 1b: I sleep somewhat less than usual
- 2a: I sleep a lot more than usual
- 2b: I sleep a lot less than usual
- 3a: I sleep most of the day
- 3b: I wake up 1-2 hours early and can't get back to sleep

---

## Total Score Interpretation

**Score Range:** 0 to 63 (sum of all 21 items)

### Severity Bands

| Total Score | Classification | Description |
|-------------|----------------|-------------|
| 0–13 | **Minimal depression** | Normal mood fluctuations |
| 14–19 | **Mild depression** | Some symptoms present |
| 20–28 | **Moderate depression** | Clinical significance |
| 29–63 | **Severe depression** | Significant impairment |

---

## Clinical Use

### Administration

- **Format:** Self-report questionnaire
- **Time:** 5-10 minutes to complete
- **Context:** Clinical settings, research, screening

### Instructions (Standard)

> "On this questionnaire are groups of statements. Please read each group of statements carefully. Then pick out the one statement in each group which best describes the way you have been feeling **during the past two weeks, including today**."

**Key Point:** Assesses symptoms over the **past 2 weeks** (not just current moment).

---

## Psychometric Properties

### Reliability

- **Internal consistency (Cronbach's α):** 0.91 to 0.94
- **Test-retest reliability:** 0.73 to 0.96 (1-week interval)

### Validity

- **Concurrent validity:** High correlation with other depression measures (Hamilton Depression Rating Scale, r = 0.71)
- **Discriminant validity:** Distinguishes depressed from non-depressed individuals
- **Sensitivity:** 81% (correctly identifies depressed individuals)
- **Specificity:** 92% (correctly identifies non-depressed individuals)

---

## Relevance to eRisk 2026 Task 1

### Task Requirements

Systems must:
1. **Estimate total BDI-II score** [0-63]
2. **Identify severity band** (minimal/mild/moderate/severe)
3. **Detect symptom presence** (which of 21 symptoms are present)

### Challenges

1. **Conversational assessment:** Traditional BDI-II is a questionnaire, not a dialog
   - Our system must map free-form conversation → structured scores
2. **Indirect mentions:** Personas may not directly state symptoms
   - "I'm exhausted" → maps to Item 15 (Loss of energy) and/or Item 20 (Tiredness)
3. **Severity quantification:** How to map vague statements → 0-3 scale?
   - "I sleep badly" → Is this 1, 2, or 3?
4. **Limited turns:** Can't ask all 21 items explicitly (prompt budget constraint)
   - Must prioritize and infer

---

## Implementation Considerations

### Question Design

Our `QuestionBank` targets each BDI-II item:

```python
# Item 16: Changes in sleeping pattern
questions = {
    "broad": "How has your sleep been lately?",
    "followup": "Are you sleeping more or less than usual?",
    "severity": "How many hours do you sleep per night?",
}
```

### Scoring Strategy

**Message-level scoring + Max-pooling:**

```python
# Score each persona utterance for all 21 symptoms
scores = symptom_model.score_texts(persona_messages)  # (N, 21)

# Max-pool per symptom (column-wise)
item_scores = np.max(scores, axis=0)  # (21,)

# Clamp to [0, 3]
item_scores = np.clip(item_scores, 0, 3)

# Sum to total
total_score = np.sum(item_scores)  # [0, 63]

# Map to severity band
if total_score <= 13:
    severity = "minimal"
elif total_score <= 19:
    severity = "mild"
elif total_score <= 28:
    severity = "moderate"
else:
    severity = "severe"
```

---

## Ethical Considerations

### Not a Diagnostic Tool (in our context)

- **BDI-II:** Clinical screening tool (requires trained administration + follow-up)
- **Our system:** Research prototype for conversational depression detection
- **Important:** We are NOT replacing clinical diagnosis - this is a research evaluation

### Safety

- **Suicidality (Item 9):** Must be assessed carefully
  - Our policy prioritizes this in early turns
  - Real-world systems would need crisis protocols (not in scope for eRisk 2026)

### Privacy

- eRisk 2026 uses **simulated LLM personas**, not real patients
- No actual patient data or PHI (Protected Health Information) involved

---

## Resources

### Official Documentation

- Beck, A. T., Steer, R. A., & Brown, G. K. (1996). Manual for the Beck Depression Inventory-II. San Antonio, TX: Psychological Corporation.

### Research Literature

- Dozois, D. J., Dobson, K. S., & Ahnberg, J. L. (1998). A psychometric evaluation of the Beck Depression Inventory–II. *Psychological Assessment*, 10(2), 83-89.
- Wang, Y. P., & Gorenstein, C. (2013). Psychometric properties of the Beck Depression Inventory-II: a comprehensive review. *Brazilian Journal of Psychiatry*, 35(4), 416-431.

### Online Resources

- APA PsycTests: https://www.apa.org/depression-guideline/beck-depression-inventory.pdf
- BDI-II scoring guidelines: https://www.pearsonassessments.com/

---

## Related Documents

- [Experiment 001 - Baseline MVP](../../user/victor/experiments/001-baseline-mvp/PROPOSAL.md)
- [Multi-Head Symptom Regression](../concepts/multi-head-symptom-regression.md)
- [Adaptive Interview Policies](../concepts/adaptive-interview-policies.md)
