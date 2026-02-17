"""
Interviewer module for eRisk 2026 Task 1.

Uses external LLMs (OpenAI, Claude) with the conversation.md system prompt
to conduct structured interviews with personas for depression assessment.
"""

import os
import json
import re
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field

import llm


# BDI-II symptom names (official ordering)
BDI_SYMPTOMS = [
    "Sadness",
    "Pessimism", 
    "Past failure",
    "Loss of pleasure",
    "Guilty feelings",
    "Punishment feelings",
    "Self-dislike",
    "Self-criticalness",
    "Suicidal thoughts or wishes",
    "Crying",
    "Agitation",
    "Loss of interest in others",
    "Indecisiveness",
    "Worthlessness",
    "Loss of energy",
    "Changes in sleeping pattern",
    "Irritability",
    "Changes in appetite",
    "Concentration difficulty",
    "Tiredness or fatigue",
    "Loss of interest in sex",
]


@dataclass
class InterviewTurn:
    """Single turn in the interview."""
    turn_number: int
    interviewer_message: str
    persona_message: Optional[str] = None
    reasoning: Optional[str] = None
    symptom_targeted: Optional[str] = None
    affirmation_level: Optional[str] = None
    assessment_snapshot: Optional[Dict[str, Any]] = None
    raw_llm_output: Optional[str] = None


@dataclass 
class InterviewResult:
    """Complete interview result."""
    persona_id: int
    turns: List[InterviewTurn] = field(default_factory=list)
    final_assessment: Optional[Dict[str, Any]] = None
    total_bdi_score: int = 0
    severity: str = "Minimal"
    key_symptoms: List[str] = field(default_factory=list)
    confidence: float = 0.0
    
    def to_conversation_log(self) -> Dict[str, Any]:
        """Convert to eRisk submission format for interactions file."""
        conversation = []
        for turn in self.turns:
            conversation.append({
                "role": "user",
                "message": turn.interviewer_message,
            })
            if turn.persona_message:
                conversation.append({
                    "role": "assistant",
                    "message": turn.persona_message,
                })
        
        return {
            "LLM": str(self.persona_id),
            "conversation": conversation,
        }
    
    def to_result_entry(self) -> Dict[str, Any]:
        """Convert to eRisk submission format for results file."""
        return {
            "LLM": str(self.persona_id),
            "bdi-score": self.total_bdi_score,
            "key-symptoms": self.key_symptoms[:4],  # Max 4 symptoms
        }


class Interviewer:
    """
    LLM-based interviewer that conducts depression screening conversations.
    
    Uses the conversation.md system prompt to guide an external LLM
    (OpenAI GPT, Anthropic Claude) through a structured interview.
    """
    
    def __init__(
        self,
        provider: str = "anthropic",
        model: Optional[str] = None,
        system_prompt_path: Optional[Path] = None,
        max_turns: int = 18,
        temperature: float = 0.7,
    ):
        """
        Initialize the interviewer.
        
        Args:
            provider: LLM provider ("openai" or "anthropic")
            model: Specific model to use (default: provider's default)
            system_prompt_path: Path to conversation.md prompt file
            max_turns: Maximum conversation turns before stopping
            temperature: LLM sampling temperature
        """
        self.provider = provider
        self.model = model
        self.max_turns = max_turns
        self.temperature = temperature
        
        # Load system prompt
        if system_prompt_path is None:
            system_prompt_path = Path(__file__).parent.parent / "prompts" / "conversation.md"
        
        self.system_prompt = self._load_system_prompt(system_prompt_path)
        
    def _load_system_prompt(self, path: Path) -> str:
        """Load the system prompt from file."""
        if not path.exists():
            raise FileNotFoundError(f"System prompt not found: {path}")
        return path.read_text()
    
    def _build_messages(
        self,
        conversation_history: List[Dict[str, str]],
        persona_message: Optional[str] = None,
    ) -> str:
        """Build the prompt for the interviewer LLM."""
        
        # Format conversation history
        history_text = ""
        if conversation_history:
            for msg in conversation_history:
                role = "You" if msg["role"] == "user" else "Persona"
                history_text += f"{role}: {msg['message']}\n"
        
        if persona_message:
            history_text += f"Persona: {persona_message}\n"
        elif not conversation_history:
            history_text = "[This is the start of the conversation. You speak first.]\n"
        
        prompt = f"""{self.system_prompt}

---

## Current Conversation

{history_text}

Now generate your next response. Output the JSON object as specified in the Output Format section above."""

        return prompt
    
    def _parse_llm_response(self, response: str) -> Tuple[str, Dict[str, Any]]:
        """
        Parse the LLM's JSON response to extract message and assessment.
        
        Returns:
            Tuple of (interviewer_message, parsed_json_dict)
        """
        # Try to extract JSON from response
        json_match = re.search(r'\{[\s\S]*\}', response)
        
        if json_match:
            try:
                data = json.loads(json_match.group())
                message = data.get("your_response", "")
                return message, data
            except json.JSONDecodeError:
                pass
        
        # Fallback: treat entire response as message
        # This happens if the LLM doesn't output proper JSON
        return response.strip(), {
            "your_response": response.strip(),
            "assessment": {"complete": False, "confidence": 0.0},
        }
    
    def generate_turn(
        self,
        conversation_history: List[Dict[str, str]],
        persona_message: Optional[str] = None,
        turn_number: int = 1,
    ) -> InterviewTurn:
        """
        Generate the next interviewer turn.
        
        Args:
            conversation_history: Previous messages in the conversation
            persona_message: The persona's last message (None for first turn)
            turn_number: Current turn number
            
        Returns:
            InterviewTurn with the interviewer's response and assessment
        """
        prompt = self._build_messages(conversation_history, persona_message)
        
        kwargs = {
            "temperature": self.temperature,
            "max_tokens": 2000,
        }
        if self.model:
            kwargs["model"] = self.model
        
        raw_response = llm.chat(prompt, provider=self.provider, **kwargs)
        
        interviewer_message, parsed_data = self._parse_llm_response(raw_response)
        
        # Extract assessment data
        assessment = parsed_data.get("assessment", {})
        
        turn = InterviewTurn(
            turn_number=turn_number,
            interviewer_message=interviewer_message,
            persona_message=persona_message,
            reasoning=parsed_data.get("reasoning", ""),
            symptom_targeted=parsed_data.get("symptom_targeted", ""),
            affirmation_level=parsed_data.get("affirmation_level", ""),
            assessment_snapshot=assessment,
            raw_llm_output=raw_response,
        )
        
        return turn
    
    def should_stop(self, turn: InterviewTurn) -> bool:
        """Determine if the interview should end."""
        # Stop if max turns reached
        if turn.turn_number >= self.max_turns:
            return True
        
        # Stop if assessment indicates completion with high confidence
        assessment = turn.assessment_snapshot or {}
        if assessment.get("complete", False) and assessment.get("confidence", 0) >= 0.75:
            return True
        
        # Stop if ready_to_stop flag is set
        if turn.raw_llm_output:
            try:
                data = json.loads(re.search(r'\{[\s\S]*\}', turn.raw_llm_output).group())
                if data.get("ready_to_stop", False):
                    return True
            except (json.JSONDecodeError, AttributeError):
                pass
        
        return False
    
    def extract_final_scores(self, last_turn: InterviewTurn) -> Dict[str, Any]:
        """Extract final BDI-II scores from the last turn's assessment."""
        assessment = last_turn.assessment_snapshot or {}
        scores = assessment.get("scores", {})
        
        # Map prompt score keys to BDI symptom names
        score_mapping = {
            "q01_sadness": "Sadness",
            "q02_pessimism": "Pessimism",
            "q04_anhedonia": "Loss of pleasure",
            "q05_guilt": "Guilty feelings",
            "q07_self_dislike": "Self-dislike",
            "q09_suicidal_thoughts": "Suicidal thoughts or wishes",
            "q12_loss_of_interest": "Loss of interest in others",
            "q13_indecisiveness": "Indecisiveness",
            "q15_energy": "Loss of energy",
            "q16_sleep": "Changes in sleeping pattern",
            "q18_appetite": "Changes in appetite",
        }
        
        # Build full 21-item score array
        item_scores = [0] * 21
        symptom_to_idx = {name: idx for idx, name in enumerate(BDI_SYMPTOMS)}
        
        for key, symptom_name in score_mapping.items():
            if key in scores:
                score_data = scores[key]
                score = score_data.get("score", 0) if isinstance(score_data, dict) else 0
                idx = symptom_to_idx.get(symptom_name)
                if idx is not None:
                    item_scores[idx] = min(3, max(0, int(score)))
        
        total_score = sum(item_scores)
        
        # Determine severity band
        if total_score <= 13:
            severity = "Minimal"
        elif total_score <= 19:
            severity = "Mild"
        elif total_score <= 28:
            severity = "Moderate"
        else:
            severity = "Severe"
        
        # Extract key symptoms (top 4 by score)
        symptom_scores = [(BDI_SYMPTOMS[i], item_scores[i]) for i in range(21)]
        symptom_scores.sort(key=lambda x: x[1], reverse=True)
        key_symptoms = [name for name, score in symptom_scores if score > 0][:4]
        
        return {
            "item_scores": item_scores,
            "total_score": total_score,
            "severity": severity,
            "key_symptoms": key_symptoms,
            "confidence": assessment.get("confidence", 0.0),
        }


def run_interview(
    interviewer: Interviewer,
    persona_query_fn,
    persona_id: int,
    verbose: bool = True,
) -> InterviewResult:
    """
    Run a complete interview with a persona.
    
    Args:
        interviewer: Interviewer instance
        persona_query_fn: Function(message, history) -> response for querying persona
        persona_id: ID of the persona being interviewed
        verbose: Print conversation as it progresses
        
    Returns:
        InterviewResult with full conversation and assessment
    """
    result = InterviewResult(persona_id=persona_id)
    conversation_history: List[Dict[str, str]] = []
    
    if verbose:
        print(f"\n{'='*60}")
        print(f"Interview with Persona {persona_id}")
        print(f"{'='*60}\n")
    
    turn_number = 0
    while True:
        turn_number += 1
        
        # Get interviewer's next message
        persona_last_msg = conversation_history[-1]["message"] if conversation_history and conversation_history[-1]["role"] == "assistant" else None
        
        turn = interviewer.generate_turn(
            conversation_history=conversation_history,
            persona_message=persona_last_msg,
            turn_number=turn_number,
        )
        
        if verbose:
            print(f"[Turn {turn_number}]")
            print(f"Interviewer: {turn.interviewer_message}")
        
        # Add interviewer message to history
        conversation_history.append({
            "role": "user",
            "message": turn.interviewer_message,
        })
        
        # Check if we should stop before getting persona response
        if interviewer.should_stop(turn):
            result.turns.append(turn)
            if verbose:
                print("\n[Interview ended by interviewer]\n")
            break
        
        # Get persona response
        # Convert history to persona's expected format
        persona_history = [
            {"role": "user" if m["role"] == "user" else "assistant", "content": m["message"]}
            for m in conversation_history[:-1]  # Exclude the message we just added
        ]
        
        persona_response = persona_query_fn(turn.interviewer_message, persona_history)
        turn.persona_message = persona_response
        
        if verbose:
            print(f"Persona: {persona_response}\n")
        
        # Add persona response to history
        conversation_history.append({
            "role": "assistant",
            "message": persona_response,
        })
        
        result.turns.append(turn)
        
        # Safety check for max turns
        if turn_number >= interviewer.max_turns:
            if verbose:
                print("\n[Max turns reached]\n")
            break
    
    # Extract final scores from last turn
    if result.turns:
        final_scores = interviewer.extract_final_scores(result.turns[-1])
        result.final_assessment = final_scores
        result.total_bdi_score = final_scores["total_score"]
        result.severity = final_scores["severity"]
        result.key_symptoms = final_scores["key_symptoms"]
        result.confidence = final_scores["confidence"]
    
    if verbose:
        print(f"{'='*60}")
        print(f"Interview Complete")
        print(f"{'='*60}")
        print(f"Total turns: {len(result.turns)}")
        print(f"BDI-II Score: {result.total_bdi_score}")
        print(f"Severity: {result.severity}")
        print(f"Key symptoms: {result.key_symptoms}")
        print(f"Confidence: {result.confidence:.2f}")
        print(f"{'='*60}\n")
    
    return result


if __name__ == "__main__":
    # Simple test with mock persona
    def mock_persona(message: str, history: List[Dict[str, str]]) -> str:
        """Mock persona for testing."""
        responses = [
            "I've been feeling pretty down lately, to be honest. Nothing seems to interest me anymore.",
            "Yeah, it's been like this for a few weeks now. I used to love playing guitar but I haven't touched it in over a month.",
            "Sleep has been terrible. I wake up at 4am and can't get back to sleep. Then I'm exhausted all day.",
            "My appetite is basically gone. I have to force myself to eat.",
            "I guess I've been avoiding my friends. It just feels like too much effort.",
            "I don't know, I just feel kind of worthless sometimes. Like nothing I do matters.",
            "Thanks for listening. It's been hard to talk about this stuff.",
        ]
        turn = len(history) // 2
        return responses[min(turn, len(responses) - 1)]
    
    print("Testing Interviewer with mock persona...")
    
    interviewer = Interviewer(
        provider="anthropic",
        max_turns=10,
    )
    
    result = run_interview(
        interviewer=interviewer,
        persona_query_fn=mock_persona,
        persona_id=0,
        verbose=True,
    )
    
    print("\nConversation log format:")
    print(json.dumps(result.to_conversation_log(), indent=2))
    
    print("\nResult format:")
    print(json.dumps(result.to_result_entry(), indent=2))
