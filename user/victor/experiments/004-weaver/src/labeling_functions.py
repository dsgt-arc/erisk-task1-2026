"""
Lightweight keyword/regex labeling functions for persona response classification.

No LLM calls — pure pattern matching. Detects symptom mentions and severity
hints in persona responses, feeding signals to the orchestrator.
"""

import re
from typing import List


# (compiled_pattern, symptom_id, severity_hint)
# severity_hint: -1 = present but unknown severity, 1-3 = estimated severity
_RULES = [
    # Sleep
    (re.compile(r"\b(can'?t sleep|insomnia|waking up|tossing and turning|barely sleep|oversleep|sleeping too much|sleep.{0,10}(terrible|awful|bad|horrible))\b", re.I), "q16_sleep", -1),
    # Energy / Fatigue
    (re.compile(r"\b(exhausted|no energy|drained|can barely|so tired|wiped out|run down)\b", re.I), "q15_energy", 2),
    (re.compile(r"\b(tired|fatigue|sluggish|dragging|low energy)\b", re.I), "q20_fatigue", -1),
    # Appetite
    (re.compile(r"\b(no appetite|can'?t eat|not hungry|lost.{0,5}appetite|skipping meals|eating.{0,10}(less|more|too much)|overeating|weight.{0,5}(gain|loss|lost|gained))\b", re.I), "q18_appetite", -1),
    # Concentration
    (re.compile(r"\b(can'?t (focus|concentrate|think)|brain fog|distracted|spacing out|hard to (focus|concentrate|decide)|forgetful)\b", re.I), "q19_concentration", -1),
    (re.compile(r"\b(can'?t (decide|make.{0,10}decision)|indecisive|go back and forth)\b", re.I), "q13_indecisiveness", -1),
    # Sadness / Mood
    (re.compile(r"\b(feel(ing)? (sad|down|low|blue|empty|numb|miserable|hopeless|awful|terrible))\b", re.I), "q01_sadness", -1),
    (re.compile(r"\b(crying|cry a lot|tears|tearful|can'?t stop crying)\b", re.I), "q10_crying", -1),
    # Anhedonia
    (re.compile(r"\b(don'?t enjoy|lost interest|nothing.{0,10}(fun|interesting|enjoy)|used to (enjoy|like|love).{0,20}(not|don'?t|anymore)|everything.{0,5}(flat|pointless|boring))\b", re.I), "q04_anhedonia", -1),
    # Pessimism
    (re.compile(r"\b(no point|hopeless|nothing.{0,10}change|won'?t get better|what'?s the point|no future|bleak|dread)\b", re.I), "q02_pessimism", -1),
    # Self-worth
    (re.compile(r"\b(worthless|useless|failure|hate myself|disgusted.{0,5}myself|not good enough|loser|piece of)\b", re.I), "q14_worthlessness", 2),
    (re.compile(r"\b(don'?t like myself|disappointed.{0,10}myself|self.{0,3}(hate|loathing))\b", re.I), "q07_self_dislike", -1),
    # Guilt
    (re.compile(r"\b(feel(ing)? guilty|my fault|blame myself|should(n'?t| not) have|constant guilt)\b", re.I), "q05_guilt", -1),
    # Social / Loss of interest
    (re.compile(r"\b(avoid(ing)? people|withdrawn|isolat(ed|ing)|don'?t (want to|feel like) (see|be around)|pushing.{0,10}away)\b", re.I), "q12_loss_of_interest", -1),
    # Agitation
    (re.compile(r"\b(restless|can'?t sit still|agitated|on edge|pacing|fidget|wound up|keyed up)\b", re.I), "q11_agitation", -1),
    # Irritability
    (re.compile(r"\b(irritable|irritated|snapping|angry|short temper|losing.{0,5}(patience|temper)|annoyed.{0,5}(easily|everything))\b", re.I), "q17_irritability", -1),
    # Suicidal (passive detection only)
    (re.compile(r"\b(kill myself|end it|suicide|suicidal|don'?t want to (live|be alive|be here)|better off dead|no reason to live)\b", re.I), "q09_suicidal_thoughts", 3),
]

# Severity escalators — override severity_hint when matched
_SEVERITY_HIGH = re.compile(r"\b(all the time|constantly|every (single )?day|always|never stops|can'?t escape|overwhelming|unbearable|completely|entirely)\b", re.I)
_SEVERITY_MED = re.compile(r"\b(most of the time|usually|often|a lot|frequently|pretty much|almost always|majority)\b", re.I)
_SEVERITY_LOW = re.compile(r"\b(sometimes|occasionally|a little|once in a while|now and then|from time to time|a bit)\b", re.I)


def detect_symptoms(response: str) -> List[dict]:
    """
    Apply keyword/regex rules to a persona response.

    Returns list of dicts:
        [{"symptom_id": "q16_sleep", "severity_hint": 2, "rule": "keyword:sleep"}]

    severity_hint: 1=mild, 2=moderate, 3=severe, -1=present but unknown severity
    """
    if not response or not response.strip():
        return []

    hits = []
    seen_symptoms = set()

    for pattern, symptom_id, base_severity in _RULES:
        if symptom_id in seen_symptoms:
            continue
        if pattern.search(response):
            severity = base_severity
            # Apply severity escalators if base is unknown (-1)
            if severity == -1:
                if _SEVERITY_HIGH.search(response):
                    severity = 3
                elif _SEVERITY_MED.search(response):
                    severity = 2
                elif _SEVERITY_LOW.search(response):
                    severity = 1

            hits.append({
                "symptom_id": symptom_id,
                "severity_hint": severity,
                "rule": f"regex:{pattern.pattern[:40]}",
            })
            seen_symptoms.add(symptom_id)

    return hits
