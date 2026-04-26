"""
Orchestrator: Algorithmic component that reads scorer output and
generates guidance for the interviewer agent.

No LLM calls. Deterministic. Fast.
"""

from collections import defaultdict
from typing import List, Tuple

from models import (
    ScorerOutput, OrchestratorGuidance, InterviewState,
    BDI_SYMPTOM_IDS, SYMPTOM_ID_TO_NAME,
)

# Symptom clusters for natural conversational grouping
SYMPTOM_CLUSTERS = {
    "mood_pleasure": ["q01_sadness", "q04_anhedonia"],
    "physical": ["q15_energy", "q16_sleep", "q18_appetite", "q20_fatigue"],
    "outlook_social": ["q02_pessimism", "q12_loss_of_interest"],
    "cognition": ["q13_indecisiveness", "q19_concentration"],
    "self_perception": ["q07_self_dislike", "q14_worthlessness"],
    "guilt_criticism": ["q05_guilt", "q08_self_criticalness"],
    "passive_observe": [
        "q03_past_failure", "q06_punishment", "q10_crying",
        "q11_agitation", "q17_irritability",
    ],
    "sensitive": ["q09_suicidal_thoughts", "q21_sex"],
}


class Orchestrator:
    """
    Reads scorer output and interview state to produce guidance
    for the interviewer agent.
    """

    def __init__(
        self,
        confidence_threshold: float = 0.6,
        max_turns: int = 18,
        stability_window: int = 3,
        max_focus_symptoms: int = 4,
    ):
        self.confidence_threshold = confidence_threshold
        self.max_turns = max_turns
        self.stability_window = stability_window
        self.max_focus_symptoms = max_focus_symptoms

    def generate_guidance(self, state: InterviewState) -> OrchestratorGuidance:
        """Analyze current interview state and produce guidance."""
        turn = state.current_turn

        # If no scorer output yet (turn 1), give initial guidance
        if not state.scorer_history:
            return self._initial_guidance(turn)

        latest_scores = state.scorer_history[-1]

        # Check stopping conditions
        wrap_up, finish_reason = self._should_stop(state, latest_scores)

        if wrap_up:
            return OrchestratorGuidance(
                focus_symptoms=[],
                guidance_text=self._wrap_up_text(finish_reason),
                wrap_up=True,
                turn_number=turn,
                scores_stable=True,
            )

        # Identify symptoms needing attention
        focus_symptoms = self._select_focus_symptoms(latest_scores)
        stable = self._check_stability(state)

        guidance_text = self._build_guidance_text(
            latest_scores, focus_symptoms, turn, stable,
        )

        return OrchestratorGuidance(
            focus_symptoms=focus_symptoms,
            guidance_text=guidance_text,
            wrap_up=False,
            turn_number=turn,
            scores_stable=stable,
        )

    def _initial_guidance(self, turn: int) -> OrchestratorGuidance:
        """Guidance for the very first turn (no scorer data yet)."""
        return OrchestratorGuidance(
            focus_symptoms=["q01_sadness", "q04_anhedonia"],
            guidance_text=(
                "## Current Focus\n\n"
                "This is the start of the interview. Open with a warm greeting "
                "and ask broadly about mood and what the persona has been enjoying lately. "
                "Target: Sadness (q01) and Loss of Pleasure (q04).\n"
            ),
            wrap_up=False,
            turn_number=turn,
        )

    def _should_stop(
        self, state: InterviewState, latest: ScorerOutput
    ) -> Tuple[bool, str]:
        """Determine if the interview should end."""
        turn = state.current_turn

        # Hard stop at max turns
        if turn >= self.max_turns:
            return True, "max_turns_reached"

        # All symptoms above confidence threshold
        all_confident = all(
            s.confidence >= self.confidence_threshold
            for s in latest.symptoms.values()
        )
        if all_confident and turn >= 8:
            return True, "all_symptoms_confident"

        # Score stability: if total score unchanged for N consecutive turns
        if self._check_stability(state) and turn >= 10:
            return True, "scores_stable"

        return False, ""

    def _check_stability(self, state: InterviewState) -> bool:
        """Check if scores have stabilized over the stability window."""
        if len(state.scorer_history) < self.stability_window:
            return False
        recent = state.scorer_history[-self.stability_window:]
        totals = [s.total_score for s in recent]
        return max(totals) - min(totals) <= 2

    def _select_focus_symptoms(self, scores: ScorerOutput) -> List[str]:
        """
        Select which symptoms the interviewer should focus on next.
        Priority: unassessed > low-confidence.
        """
        candidates = []
        for sid, symptom in scores.symptoms.items():
            if not symptom.assessed:
                priority = -2.0
            elif symptom.confidence < self.confidence_threshold:
                priority = symptom.confidence
            else:
                continue  # Already well-assessed

            candidates.append((sid, priority))

        candidates.sort(key=lambda x: x[1])
        selected_ids = [sid for sid, _ in candidates[:self.max_focus_symptoms]]

        return self._group_by_cluster(selected_ids)

    def _group_by_cluster(self, symptom_ids: List[str]) -> List[str]:
        """Reorder symptom IDs so related symptoms are adjacent."""
        id_to_cluster = {}
        for cluster_name, members in SYMPTOM_CLUSTERS.items():
            for sid in members:
                id_to_cluster[sid] = cluster_name

        clusters = defaultdict(list)
        for sid in symptom_ids:
            cluster = id_to_cluster.get(sid, "other")
            clusters[cluster].append(sid)

        # Emit clusters with most members first
        ordered = []
        for cluster_name in sorted(clusters, key=lambda c: -len(clusters[c])):
            ordered.extend(clusters[cluster_name])

        return ordered

    def _build_guidance_text(
        self,
        scores: ScorerOutput,
        focus_symptoms: List[str],
        turn: int,
        stable: bool,
    ) -> str:
        """Build the natural-language guidance injected into the interviewer prompt."""
        lines = ["## Current Focus\n"]

        if focus_symptoms:
            lines.append("The following symptoms need more exploration:")
            for sid in focus_symptoms:
                s = scores.symptoms[sid]
                name = SYMPTOM_ID_TO_NAME[sid]
                if not s.assessed:
                    lines.append(f"- **{name}** ({sid}): NOT YET ASSESSED")
                else:
                    lines.append(
                        f"- **{name}** ({sid}): confidence {s.confidence:.1f}, "
                        f"current score {s.score}"
                    )
            lines.append("")

        # List well-assessed symptoms so interviewer doesn't waste turns
        well_assessed = [
            s for s in scores.symptoms.values()
            if s.confidence >= self.confidence_threshold and s.assessed
        ]
        if well_assessed:
            names = ", ".join(
                f"{s.name} ({s.confidence:.1f})"
                for s in sorted(well_assessed, key=lambda x: -x.confidence)[:6]
            )
            lines.append(f"Well-assessed (do NOT revisit): {names}\n")

        # Turn budget awareness
        remaining = self.max_turns - turn
        if remaining <= 4:
            lines.append(
                f"**Turn budget low ({remaining} turns remaining).** "
                "Focus on the most important gaps.\n"
            )

        if stable:
            lines.append(
                "Scores have been stable. Consider wrapping up if you feel "
                "you have enough information.\n"
            )

        return "\n".join(lines)

    def _wrap_up_text(self, reason: str) -> str:
        """Generate wrap-up guidance text."""
        reasons = {
            "max_turns_reached": "Maximum turns reached.",
            "all_symptoms_confident": "All assessable symptoms are well-assessed.",
            "scores_stable": "Scores have stabilized across recent turns.",
        }
        return (
            "## Wrap Up\n\n"
            f"It is time to end the interview. Reason: {reasons.get(reason, reason)}\n"
            "Thank the persona warmly for their openness and end the conversation "
            "naturally. Do NOT ask any new questions.\n"
        )
