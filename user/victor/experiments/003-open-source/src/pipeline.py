"""
Multi-agent interview pipeline.

Orchestrates the three agents (interviewer, scorer, orchestrator)
through a turn-by-turn interview loop.
"""

import time
from typing import Callable, List, Dict

from models import (
    InterviewState, InterviewResult, ConversationMessage,
)
from agents.interviewer import InterviewerAgent
from agents.scorer import ScorerAgent
from agents.orchestrator import Orchestrator


class InterviewPipeline:
    """
    Runs a complete multi-agent interview with a persona.

    Per-turn flow:
    1. (Turn > 1) Scorer analyzes full transcript
    2. Orchestrator generates guidance from scorer output
    3. Interviewer generates next question using guidance
    4. Question sent to persona, response recorded
    """

    def __init__(
        self,
        interviewer: InterviewerAgent,
        scorer: ScorerAgent,
        orchestrator: Orchestrator,
        max_turns: int = 18,
        score_every_n_turns: int = 1,
        verbose: bool = True,
    ):
        self.interviewer = interviewer
        self.scorer = scorer
        self.orchestrator = orchestrator
        self.max_turns = max_turns
        self.score_every_n_turns = score_every_n_turns
        self.verbose = verbose

    def run(
        self,
        persona_query_fn: Callable[[str, List[Dict[str, str]]], str],
        persona_id: int,
    ) -> InterviewResult:
        """
        Run a complete interview.

        Args:
            persona_query_fn: Function(message, history) -> response
            persona_id: ID of the persona being interviewed

        Returns:
            InterviewResult with conversation and final scores
        """
        state = InterviewState(persona_id=persona_id)

        self._log(f"\n{'='*60}")
        self._log(f"Interview with Persona {persona_id}")
        self._log(f"{'='*60}\n")

        while not state.finished:
            state.current_turn += 1
            self._run_turn(state, persona_query_fn)

        # Final scoring pass (always run at end for complete assessment)
        if state.messages:
            self._log("  [Final scoring pass... ", end="")
            t0 = time.time()
            final_scores = self.scorer.score(state.transcript_text())
            elapsed = time.time() - t0
            self._log(f"done in {elapsed:.1f}s, "
                       f"total={final_scores.total_score}, "
                       f"severity={final_scores.severity}]")
            state.scorer_history.append(final_scores)

        return self._build_result(state)

    def _run_turn(
        self,
        state: InterviewState,
        persona_query_fn: Callable,
    ):
        """Execute one interview turn."""
        turn = state.current_turn

        # Step 1: Score transcript (skip turn 1 — no transcript yet)
        should_score = (
            turn > 1
            and state.messages
            and (turn - 1) % self.score_every_n_turns == 0
        )

        if should_score:
            self._log(f"  [Scoring transcript... ", end="")
            t0 = time.time()
            scorer_output = self.scorer.score(state.transcript_text())
            elapsed = time.time() - t0
            self._log(f"done in {elapsed:.1f}s, "
                       f"total={scorer_output.total_score}, "
                       f"conf={scorer_output.mean_confidence:.2f}]")
            state.scorer_history.append(scorer_output)

        # Step 2: Orchestrator generates guidance
        guidance = self.orchestrator.generate_guidance(state)
        state.guidance_history.append(guidance)

        # Check if orchestrator says to wrap up (and this isn't turn 1)
        if guidance.wrap_up and turn > 1:
            closing = self.interviewer.generate_message(state, guidance)
            state.messages.append(
                ConversationMessage(role="interviewer", content=closing, turn=turn)
            )
            self._log(f"[Turn {turn}] Interviewer (closing): {closing}")
            state.finished = True
            state.finish_reason = "orchestrator_wrap_up"
            return

        # Step 3: Interviewer generates question
        message = self.interviewer.generate_message(state, guidance)
        state.messages.append(
            ConversationMessage(role="interviewer", content=message, turn=turn)
        )
        self._log(f"[Turn {turn}] Interviewer: {message}")

        # Step 4: Get persona response
        persona_history = [
            {"role": "user" if m.role == "interviewer" else "assistant",
             "content": m.content}
            for m in state.messages[:-1]
        ]
        persona_response = persona_query_fn(message, persona_history)

        state.messages.append(
            ConversationMessage(role="persona", content=persona_response, turn=turn)
        )
        self._log(f"           Persona: {persona_response}\n")

        # Safety: hard stop at max turns
        if turn >= self.max_turns:
            state.finished = True
            state.finish_reason = "max_turns"

    def _build_result(self, state: InterviewState) -> InterviewResult:
        """Convert InterviewState to InterviewResult."""
        final_scores = state.scorer_history[-1] if state.scorer_history else None

        if final_scores:
            symptom_list = sorted(
                final_scores.symptoms.values(),
                key=lambda s: s.score,
                reverse=True,
            )
            key_symptoms = [s.name for s in symptom_list if s.score > 0][:4]
        else:
            key_symptoms = []

        return InterviewResult(
            persona_id=state.persona_id,
            messages=state.messages,
            final_scores=final_scores,
            total_bdi_score=final_scores.total_score if final_scores else 0,
            severity=final_scores.severity if final_scores else "Minimal",
            key_symptoms=key_symptoms,
            confidence=final_scores.mean_confidence if final_scores else 0.0,
            scorer_history=state.scorer_history,
        )

    def _log(self, message: str, end: str = "\n"):
        if self.verbose:
            print(message, end=end, flush=True)
