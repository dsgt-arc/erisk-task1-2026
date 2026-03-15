"""
Precomputed dialogue tree with BM25 navigation.

Loads a YAML question bank and provides functions to:
- Get opener questions for target symptoms
- Match persona responses to follow-up branches via BM25
- Fall back to LLM when no good tree match exists
"""

from pathlib import Path
from typing import Optional, List, Set

import yaml
from rank_bm25 import BM25Okapi


def load_bank(path: Path) -> dict:
    """Load question bank YAML and build BM25 indices for each opener's followups."""
    with open(path) as f:
        bank = yaml.safe_load(f)

    # Build a flat lookup: symptom_id → list of openers
    bank["_symptom_to_openers"] = {}
    for cluster_name, cluster in bank["clusters"].items():
        for opener in cluster["openers"]:
            for sid in opener.get("target_symptoms", []):
                bank["_symptom_to_openers"].setdefault(sid, []).append(opener)
            # Build BM25 index for this opener's followups
            followups = opener.get("followups", [])
            if followups:
                corpus = [fu.get("trigger_keywords", []) for fu in followups]
                opener["_bm25"] = BM25Okapi(corpus)

    return bank


def get_opener(
    bank: dict,
    focus_symptoms: List[str],
    used_ids: Set[str],
) -> Optional[dict]:
    """
    Find the best unused opener matching any of the focus symptoms.

    Returns the opener dict or None if all relevant openers are exhausted.
    """
    symptom_to_openers = bank.get("_symptom_to_openers", {})

    for sid in focus_symptoms:
        for opener in symptom_to_openers.get(sid, []):
            if opener["id"] not in used_ids:
                return opener

    return None


def get_followup(
    bank: dict,
    last_response: str,
    current_node: dict,
    threshold: float = 1.5,
) -> Optional[dict]:
    """
    BM25-match the persona's response against the current node's followups.

    Returns the best-matching followup dict if the BM25 score exceeds
    the threshold, otherwise None (signaling LLM fallback).
    """
    followups = current_node.get("followups", [])
    if not followups:
        return None

    bm25 = current_node.get("_bm25")
    if bm25 is None:
        return None

    # Tokenize response
    tokens = _tokenize(last_response)
    if not tokens:
        return None

    scores = bm25.get_scores(tokens)
    best_idx = max(range(len(scores)), key=lambda i: scores[i])

    if scores[best_idx] >= threshold:
        return followups[best_idx]

    return None


def _tokenize(text: str) -> List[str]:
    """Simple whitespace tokenizer with lowering and basic cleanup."""
    return [
        w.strip(".,!?;:'\"()[]")
        for w in text.lower().split()
        if len(w.strip(".,!?;:'\"()[]")) > 1
    ]
