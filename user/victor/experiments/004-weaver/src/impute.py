"""
Cluster-based imputation for unassessed BDI-II symptoms.

When the scorer returns confidence=0.0 for a symptom (unassessed / not discussed),
imputes a score from assessed symptoms in related clusters rather than defaulting
to 0. Uses clinically-grounded symptom co-occurrence groups.

Only imputes GENTLE_PROBE and passive_observe symptoms. DO_NOT_PROBE symptoms
(suicidal thoughts, sex, past failure, punishment) always stay at 0 if unassessed.
"""

from typing import Dict

from models import BDI_SYMPTOM_IDS, ScorerOutput, SymptomScore


# Clinically-grounded co-occurrence groups.
# Each symptom maps to a list of "donor" symptoms ordered by clinical relevance.
# If donors are assessed, their weighted average is used to impute.
_IMPUTATION_DONORS = {
    # Emotional reactions — impute from mood cluster
    "q10_crying": ["q01_sadness", "q04_anhedonia", "q05_guilt"],
    "q11_agitation": ["q17_irritability", "q15_energy", "q01_sadness"],
    "q17_irritability": ["q11_agitation", "q01_sadness", "q20_fatigue"],
    # Self-perception — impute from each other + guilt
    "q07_self_dislike": ["q14_worthlessness", "q08_self_criticalness", "q05_guilt"],
    "q14_worthlessness": ["q07_self_dislike", "q08_self_criticalness", "q01_sadness"],
    # Guilt/criticism — impute from each other + self-perception
    "q05_guilt": ["q08_self_criticalness", "q07_self_dislike", "q14_worthlessness"],
    "q08_self_criticalness": ["q05_guilt", "q07_self_dislike", "q14_worthlessness"],
    # Physical — impute from each other
    "q20_fatigue": ["q15_energy", "q16_sleep", "q18_appetite"],
    "q15_energy": ["q20_fatigue", "q16_sleep", "q01_sadness"],
    "q16_sleep": ["q20_fatigue", "q15_energy", "q18_appetite"],
    "q18_appetite": ["q16_sleep", "q20_fatigue", "q01_sadness"],
    # Cognition — impute from each other + fatigue
    "q13_indecisiveness": ["q19_concentration", "q20_fatigue", "q15_energy"],
    "q19_concentration": ["q13_indecisiveness", "q20_fatigue", "q15_energy"],
    # Mood — impute from each other + outlook
    "q01_sadness": ["q04_anhedonia", "q02_pessimism", "q10_crying"],
    "q04_anhedonia": ["q01_sadness", "q12_loss_of_interest", "q20_fatigue"],
    "q02_pessimism": ["q01_sadness", "q04_anhedonia", "q14_worthlessness"],
    "q12_loss_of_interest": ["q04_anhedonia", "q01_sadness", "q20_fatigue"],
}

# Never impute these — they should only be scored from direct evidence
_NEVER_IMPUTE = {"q03_past_failure", "q06_punishment", "q09_suicidal_thoughts", "q21_sex"}

# Donor weights: first donor is most relevant, decays
_DONOR_WEIGHTS = [0.5, 0.3, 0.2]


def impute_unassessed(scores: ScorerOutput) -> ScorerOutput:
    """
    Return a new ScorerOutput with unassessed symptoms imputed from
    clinically-related assessed symptoms.

    Rules:
    - Only imputes symptoms with confidence=0.0 (truly unassessed)
    - Never imputes DO_NOT_PROBE symptoms (suicidal, sex, past failure, punishment)
    - Imputed scores are capped at 2 (never impute "severe")
    - Imputed confidence is set to 0.15 (clearly lower than any real assessment)
    - If no donors are assessed, leaves the symptom at 0
    """
    new_symptoms: Dict[str, SymptomScore] = {}

    for sid in BDI_SYMPTOM_IDS:
        original = scores.symptoms[sid]

        # Already assessed or never impute — keep as-is
        if original.confidence > 0.0 or sid in _NEVER_IMPUTE:
            new_symptoms[sid] = original
            continue

        # Try to impute from donors
        donors = _IMPUTATION_DONORS.get(sid, [])
        if not donors:
            new_symptoms[sid] = original
            continue

        weighted_sum = 0.0
        weight_total = 0.0
        for donor_sid, weight in zip(donors, _DONOR_WEIGHTS):
            donor = scores.symptoms.get(donor_sid)
            if donor and donor.confidence > 0.0:
                weighted_sum += donor.score * weight
                weight_total += weight

        if weight_total == 0.0:
            # No assessed donors — leave at 0
            new_symptoms[sid] = original
            continue

        imputed_score = round(weighted_sum / weight_total)
        imputed_score = min(imputed_score, 2)  # cap at moderate

        new_symptoms[sid] = SymptomScore(
            symptom_id=sid,
            score=imputed_score,
            confidence=0.15,
            evidence=f"Imputed from related symptoms (no direct discussion)",
            assessed=False,  # still marked unassessed
        )

    return ScorerOutput(
        symptoms=new_symptoms,
        reasoning=scores.reasoning,
    )
