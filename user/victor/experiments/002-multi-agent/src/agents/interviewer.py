"""
Interviewer agent: Generates natural, empathetic interview questions.

Completely unburdened from scoring. Its only job is to ask good questions
guided by the orchestrator's instructions.
"""

import json
import re
from pathlib import Path
from typing import Optional

import llm
from models import InterviewState, OrchestratorGuidance


class InterviewerAgent:
    """
    LLM-based interviewer that generates conversational questions.

    Input: conversation history + orchestrator guidance
    Output: a single string (the next question/message)
    """

    def __init__(
        self,
        provider: str = "openai",
        model: Optional[str] = None,
        prompt_path: Optional[Path] = None,
        temperature: float = 0.7,
    ):
        self.provider = provider
        self.model = model
        self.temperature = temperature

        if prompt_path is None:
            prompt_path = (
                Path(__file__).parent.parent.parent / "prompts" / "interviewer.md"
            )
        self.base_prompt = prompt_path.read_text()

    def generate_message(
        self,
        state: InterviewState,
        guidance: OrchestratorGuidance,
    ) -> str:
        """
        Generate the interviewer's next message.

        Args:
            state: Current interview state with full conversation history
            guidance: Orchestrator's guidance for this turn

        Returns:
            The interviewer's next message as plain text
        """
        prompt = self._build_prompt(state, guidance)

        kwargs = {
            "temperature": self.temperature,
            "max_tokens": 500,
            "system_prompt": self.base_prompt,
        }
        if self.model:
            kwargs["model"] = self.model

        raw = llm.chat(prompt, provider=self.provider, **kwargs)
        return self._extract_message(raw)

    def _build_prompt(
        self,
        state: InterviewState,
        guidance: OrchestratorGuidance,
    ) -> str:
        """Build the user prompt for the interviewer LLM."""
        if state.messages:
            history = "\n".join(
                f"{'You' if m.role == 'interviewer' else 'Persona'}: {m.content}"
                for m in state.messages
            )
        else:
            history = "[This is the start of the conversation. You speak first.]"

        return (
            f"{guidance.guidance_text}\n\n"
            f"---\n\n"
            f"## Conversation So Far\n\n"
            f"{history}\n\n"
            f"---\n\n"
            f"Now generate your next message. Output ONLY the text of your "
            f"message to the persona. Do not include JSON, metadata, or reasoning."
        )

    def _extract_message(self, raw: str) -> str:
        """
        Extract the plain-text message from the LLM response.
        Strip any JSON or metadata the LLM might include despite instructions.
        """
        # If the response looks like JSON, try to extract a message field
        if raw.strip().startswith("{"):
            try:
                data = json.loads(raw)
                for key in ("message", "your_response", "response", "text"):
                    if key in data:
                        return data[key].strip()
            except json.JSONDecodeError:
                pass

        # Strip markdown code fences if present
        text = raw.strip()
        text = re.sub(r'^```(?:json)?\s*\n?', '', text)
        text = re.sub(r'\n?```\s*$', '', text)
        return text.strip()
