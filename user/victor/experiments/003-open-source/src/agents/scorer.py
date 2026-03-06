"""
Scorer agent: Analyzes a conversation transcript and produces
per-symptom BDI-II scores with confidence and evidence.

Can be run in ensemble mode (multiple passes, median aggregation)
for more reliable scoring.
"""

import json
import re
import statistics
from pathlib import Path
from typing import Optional, List

import llm
from models import BDI_SYMPTOM_IDS, ScorerOutput, SymptomScore


class ScorerAgent:
    """
    Stateless scorer that analyzes a transcript and outputs BDI-II scores.

    Each call to score() is independent — the scorer does not maintain
    conversation state. It receives the full transcript each time.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        prompt_path: Optional[Path] = None,
        ensemble_size: int = 1,
        ensemble_temperature: float = 0.3,
    ):
        self.model = model
        self.ensemble_size = ensemble_size
        self.ensemble_temperature = ensemble_temperature

        if prompt_path is None:
            prompt_path = Path(__file__).parent.parent.parent / "prompts" / "scorer.md"
        self.system_prompt = prompt_path.read_text()

    def score(self, transcript: str) -> ScorerOutput:
        """
        Score a transcript. If ensemble_size > 1, runs multiple passes
        and aggregates via median.
        """
        if self.ensemble_size <= 1:
            return self._single_score(transcript, temperature=0.0)

        outputs = []
        for _ in range(self.ensemble_size):
            outputs.append(
                self._single_score(transcript, temperature=self.ensemble_temperature)
            )
        return self._aggregate_ensemble(outputs)

    def _single_score(self, transcript: str, temperature: float) -> ScorerOutput:
        """Run one scoring pass."""
        prompt = (
            f"## Transcript\n\n{transcript}\n\n---\n\n"
            "Now analyze this transcript and output your assessment as JSON."
        )

        kwargs = {
            "temperature": temperature,
            "max_tokens": 4000,
            "system_prompt": self.system_prompt,
        }
        if self.model:
            kwargs["model"] = self.model

        raw = llm.chat(prompt, **kwargs)
        return self._parse_response(raw)

    def _parse_response(self, raw: str) -> ScorerOutput:
        """Parse the scorer LLM's JSON response into a ScorerOutput."""
        json_match = re.search(r'\{[\s\S]*\}', raw)
        if not json_match:
            return self._empty_output("No JSON found in scorer response")

        try:
            data = json.loads(json_match.group())
        except json.JSONDecodeError:
            return self._empty_output("Failed to parse scorer JSON")

        symptoms = {}
        scores_data = data.get("scores", {})
        for sid in BDI_SYMPTOM_IDS:
            entry = scores_data.get(sid, {})
            raw_score = int(entry.get("score", 0))
            raw_confidence = float(entry.get("confidence", 0.0))
            evidence = entry.get("evidence", "Not assessed")

            # Confidence calibration: clamp overconfident thin-evidence scores
            calibrated_confidence = self._calibrate_confidence(
                raw_confidence, evidence
            )

            symptoms[sid] = SymptomScore(
                symptom_id=sid,
                score=min(3, max(0, raw_score)),
                confidence=calibrated_confidence,
                evidence=evidence,
                assessed=calibrated_confidence > 0.0,
            )

        return ScorerOutput(
            symptoms=symptoms,
            reasoning=data.get("reasoning", ""),
        )

    def _calibrate_confidence(self, confidence: float, evidence: str) -> float:
        """Clamp overconfident scores with thin evidence."""
        if not evidence or evidence.lower() in (
            "not assessed",
            "no relevant discussion in transcript",
            "no relevant discussion in transcript.",
            "not yet assessed",
        ):
            return 0.0
        if len(evidence) < 15:
            return min(confidence, 0.3)
        # Cap single-pass confidence at 0.9 (only ensemble can reach 1.0)
        return min(confidence, 0.9)

    def _aggregate_ensemble(self, outputs: List[ScorerOutput]) -> ScorerOutput:
        """Aggregate multiple scoring passes using median score and max confidence."""
        symptoms = {}
        for sid in BDI_SYMPTOM_IDS:
            scores = [o.symptoms[sid].score for o in outputs]
            confidences = [o.symptoms[sid].confidence for o in outputs]
            evidences = [o.symptoms[sid].evidence for o in outputs]
            symptoms[sid] = SymptomScore(
                symptom_id=sid,
                score=int(statistics.median(scores)),
                confidence=max(confidences),
                evidence=max(evidences, key=len),
                assessed=any(o.symptoms[sid].assessed for o in outputs),
            )
        return ScorerOutput(symptoms=symptoms)

    def _empty_output(self, reason: str = "Scoring failed") -> ScorerOutput:
        """Return a zeroed-out ScorerOutput when parsing fails."""
        symptoms = {}
        for sid in BDI_SYMPTOM_IDS:
            symptoms[sid] = SymptomScore(
                symptom_id=sid, score=0, confidence=0.0,
                evidence=reason, assessed=False,
            )
        return ScorerOutput(symptoms=symptoms)
