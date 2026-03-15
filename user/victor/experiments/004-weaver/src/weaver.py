"""
Weaver-style aggregation for run selection.

Treats each batch sample's 21-item BDI-II score vector as a "weak verifier vote."
Learns per-sample reliability weights from pairwise agreement statistics,
then aggregates via weighted median to find the best consensus profile.

Based on: "Shrinking the Generation-Verification Gap with Weak Verifiers"
(Saad-Falcon et al., 2025, arXiv:2506.18203)
"""

from typing import Dict, List, Tuple

from models import BDI_SYMPTOM_IDS, ScorerOutput, SymptomScore


class WeaverAggregator:
    """Learn sample reliability weights and aggregate BDI-II scores."""

    def __init__(self, symptom_ids: List[str] = None):
        self.symptom_ids = symptom_ids or BDI_SYMPTOM_IDS

    def learn_weights(self, samples: List[ScorerOutput]) -> Dict[int, float]:
        """
        Learn per-sample reliability weights from pairwise agreement.

        For each pair of samples (i, j), compute what fraction of 21
        binarized symptoms they agree on. A sample's weight is its
        mean agreement with all other samples (normalized to sum to 1).

        Samples that agree with more others are assumed more reliable.
        """
        n = len(samples)
        if n <= 1:
            return {0: 1.0} if n == 1 else {}

        # Binarize: score > 0 → 1, else → 0
        binary = [self._binarize(s) for s in samples]
        k = len(self.symptom_ids)

        # Pairwise agreement matrix
        agreement = [[0.0] * n for _ in range(n)]
        for i in range(n):
            for j in range(i + 1, n):
                matches = sum(1 for a, b in zip(binary[i], binary[j]) if a == b)
                rate = matches / k
                agreement[i][j] = rate
                agreement[j][i] = rate

        # Per-sample weight = mean agreement with others
        raw_weights = {}
        for i in range(n):
            raw_weights[i] = sum(agreement[i][j] for j in range(n) if j != i) / (n - 1)

        # Normalize to sum to 1
        total = sum(raw_weights.values())
        if total == 0:
            return {i: 1.0 / n for i in range(n)}
        return {i: w / total for i, w in raw_weights.items()}

    def consensus_profile(
        self, samples: List[ScorerOutput], weights: Dict[int, float]
    ) -> ScorerOutput:
        """
        Build consensus BDI profile using weighted median across samples.

        For each symptom: weighted median score, weighted mean confidence,
        evidence from highest-weighted sample.
        """
        symptoms = {}
        for sid in self.symptom_ids:
            scores = [s.symptoms[sid].score for s in samples]
            confidences = [s.symptoms[sid].confidence for s in samples]
            w_list = [weights.get(i, 0.0) for i in range(len(samples))]

            med_score = self._weighted_median(scores, w_list)

            # Weighted mean confidence
            w_conf = sum(c * w for c, w in zip(confidences, w_list))

            # Evidence from highest-weighted sample
            best_idx = max(range(len(samples)), key=lambda i: weights.get(i, 0.0))
            evidence = samples[best_idx].symptoms[sid].evidence

            symptoms[sid] = SymptomScore(
                symptom_id=sid,
                score=med_score,
                confidence=min(w_conf, 1.0),
                evidence=evidence,
                assessed=med_score > 0 or w_conf > 0.3,
            )

        return ScorerOutput(symptoms=symptoms)

    def rank_samples(
        self,
        samples: List[ScorerOutput],
        consensus: ScorerOutput,
        weights: Dict[int, float] = None,
    ) -> List[Tuple[int, float]]:
        """
        Rank samples by L1 distance from consensus profile.

        Returns [(sample_index, distance)] sorted ascending (closest first).
        Ties broken by sample weight (higher weight preferred).
        """
        ranked = []
        for i, s in enumerate(samples):
            dist = sum(
                abs(s.symptoms[sid].score - consensus.symptoms[sid].score)
                for sid in self.symptom_ids
            )
            # Negate weight for tiebreaking (higher weight = lower sort key)
            w = weights.get(i, 0.0) if weights else 0.0
            ranked.append((i, dist, -w))

        ranked.sort(key=lambda x: (x[1], x[2]))
        return [(idx, dist) for idx, dist, _ in ranked]

    def _binarize(self, output: ScorerOutput) -> List[int]:
        """Convert 21 symptom scores to binary vector (score > 0 → 1)."""
        return [1 if output.symptoms[sid].score > 0 else 0 for sid in self.symptom_ids]

    @staticmethod
    def _weighted_median(values: List[int], weights: List[float]) -> int:
        """Compute weighted median of integer values."""
        if not values:
            return 0

        # Sort by value, carrying weights
        pairs = sorted(zip(values, weights), key=lambda x: x[0])
        total_weight = sum(w for _, w in pairs)
        if total_weight == 0:
            # Fall back to simple median
            sorted_vals = sorted(values)
            return sorted_vals[len(sorted_vals) // 2]

        # Find the value where cumulative weight crosses half
        cumulative = 0.0
        half = total_weight / 2.0
        for val, w in pairs:
            cumulative += w
            if cumulative >= half:
                return val

        return pairs[-1][0]
