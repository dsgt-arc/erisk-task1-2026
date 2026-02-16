"""
eRisk 2026 Task 1: Conversational Depression Detection Pipeline

MVP for automated depression screening using LLM personas.

Conducts semi-structured interviews targeting 21 BDI-II symptoms with
LLM-based symptom scoring and adaptive question policy.
"""

import os
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from pathlib import Path
import json

import numpy as np
import llm

def load_env():
    env_file = Path(__file__).parents[2] / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    if value:  # Only set if value is not empty
                        os.environ[key.strip()] = value.strip()

load_env()

#=============================
#    BDI-II Symptom List
#=============================
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

SYMPTOM_TO_ID = {symptom: idx for idx, symptom in enumerate(BDI_SYMPTOMS)}
ID_TO_SYMPTOM = {idx: symptom for idx, symptom in enumerate(BDI_SYMPTOMS)}


#=============================
#        Data Models
#=============================
@dataclass
class Question:
    """Single interview question targeting a BDI-II symptom."""
    symptom_id: int
    symptom_name: str
    text: str
    kind: str  # "broad" | "followup" | "severity" -> how deep/specific the question is


@dataclass
class Message:
    """Single message in the conversation."""
    speaker: str  # e.g. "system" or "persona"
    turn_idx: int
    text: str
    targeted_symptom_id: Optional[int] = None


@dataclass
class Conversation:
    """Complete interview conversation"""
    persona_id: str
    messages: List[Message] = field(default_factory=list)

    def add_message(self, speaker: str, text: str, targeted_symptom_id: Optional[int] = None) -> None:
        """Add a message to the conversation."""
        turn_idx = len(self.messages)
        msg = Message(speaker=speaker, turn_idx=turn_idx, text=text, targeted_symptom_id=targeted_symptom_id)
        self.messages.append(msg)

    def get_persona_messages(self) -> List[Message]:
        """Return only messages from the persona."""
        return [msg for msg in self.messages if msg.speaker == "persona"]

    def format_for_display(self) -> str:
        """Format conversation as readable text."""
        lines = []
        for msg in self.messages:
            speaker = "Interviewer" if msg.speaker == "system" else "Client"
            lines.append(f"{speaker}: {msg.text}")
        return "\n".join(lines)


class QuestionBank:
    """
    Repository of questions targeting each BDI-II symptoms.
    Contains broad, follow-up, and severity questions.
    """

    def __init__(self):
        self._questions = self._build_question_bank()

    # TODO: Expand question set and test across personas to identify optimal version
    def _build_question_bank(self) -> Dict[int, Dict[str, List[Question]]]:
        questions = {}

        # Symptom 0: Sadness
        questions[0] = {
            "broad": [
                Question(0, "Sadness", "How have you been feeling emotionally lately?", "broad"),
                Question(0, "Sadness", "Tell me about your mood over the past few weeks.", "broad"),
            ],
            "followup": [
                Question(0, "Sadness", "How often do you feel sad or down?", "followup"),
                Question(0, "Sadness", "Do you feel sad most of the day?", "severity"),
            ],
        }

        # Symptom 3: Loss of pleasure
        questions[3] = {
            "broad": [
                Question(3, "Loss of pleasure", "What activities do you enjoy doing?", "broad"),
                Question(3, "Loss of pleasure", "How interested are you in your hobbies?", "broad"),
            ],
            "followup": [
                Question(3, "Loss of pleasure", "Have you lost interest in things you used to enjoy?", "followup"),
            ],
        }

        # Symptom 8: Suicidal thoughts
        questions[8] = {
            "broad": [
                Question(8, "Suicidal thoughts or wishes", "Have you had any thoughts of harming yourself?", "broad"),
            ],
            "followup": [
                Question(8, "Suicidal thoughts or wishes", "How often do these thoughts occur?", "severity"),
            ],
        }

        # Symptom 14: Loss of energy
        questions[14] = {
            "broad": [
                Question(14, "Loss of energy", "How are your energy levels?", "broad"),
                Question(14, "Loss of energy", "Do you feel tired during the day?", "broad"),
            ],
            "followup": [
                Question(14, "Loss of energy", "Is this different from how you usually feel?", "followup"),
            ],
        }

        # Symptom 15: Changes in sleeping pattern
        questions[15] = {
            "broad": [
                Question(15, "Changes in sleeping pattern", "How has your sleep been lately?", "broad"),
                Question(15, "Changes in sleeping pattern", "Tell me about your sleep patterns.", "broad"),
            ],
            "followup": [
                Question(15, "Changes in sleeping pattern", "Are you sleeping more or less than usual?", "followup"),
                Question(15, "Changes in sleeping pattern", "How many hours do you sleep per night?", "severity"),
            ],
        }

        # Symptom 19: Tiredness or fatigue
        questions[19] = {
            "broad": [
                Question(19, "Tiredness or fatigue", "Do you feel fatigued?", "broad"),
            ],
            "followup": [
                Question(19, "Tiredness or fatigue", "Does rest help with the fatigue?", "followup"),
            ],
        }

        # Generic questions for remaining symptoms
        generic_symptoms = [1, 2, 4, 5, 6, 7, 9, 10, 11, 12, 13, 16, 17, 18, 20]
        for symptom_id in generic_symptoms:
            symptom_name = BDI_SYMPTOMS[symptom_id]
            questions[symptom_id] = {
                "broad": [
                    Question(symptom_id, symptom_name, f"Have you experienced any {symptom_name.lower()}?", "broad"),
                ],
                "followup": [
                    Question(symptom_id, symptom_name, f"Can you tell me more about your {symptom_name.lower()}?", "followup"),
                ],
            }

        return questions

    def get_broad_questions(self, symptom_id: int) -> List[Question]:
        """Get all broad questions for a symptom."""
        return self._questions.get(symptom_id, {}).get("broad", [])

    def get_followup_questions(self, symptom_id: int) -> List[Question]:
        """Get all follow-up questions for a symptom."""
        return self._questions.get(symptom_id, {}).get("followup", [])

    def sample_broad(self, symptom_id: int) -> Optional[Question]:
        """Sample a random broad question for a symptom."""
        broad_qs = self.get_broad_questions(symptom_id)
        return random.choice(broad_qs) if broad_qs else None

    def sample_followup(self, symptom_id: int) -> Optional[Question]:
        """Sample a random follow-up question for a symptom."""
        followup_qs = self.get_followup_questions(symptom_id)
        return random.choice(followup_qs) if followup_qs else None


#=============================
# Symptom Detection & Scoring
#=============================
class SymptomDetector:
    """
    LLM-based symptom mention detector that guides question prompting.
    Supports all 21 BDI-II symptoms using any LLM provider.
    """

    def __init__(self, provider: str = "openai", model: str = None, cache: bool = True):
        self.provider = provider
        self.model = model

    def _detect(self, text: str, symptom_id: int) -> bool:
        """Detect if text mentions a specific symptom."""
        symptom_name = BDI_SYMPTOMS[symptom_id]
        prompt = f"""Does the following text mention or suggest symptoms related to "{symptom_name}" (as defined in BDI-II depression inventory)?

Text: "{text}"

Answer only "YES" or "NO"."""

        kwargs = {"temperature": 0.0, "max_tokens": 5}
        if self.model:
            kwargs["model"] = self.model

        response = llm.chat(prompt, provider=self.provider, **kwargs)
        result = "yes" in response.lower()

        return result

    def mentions_symptom(self, text: str, symptom_id: int) -> bool:
        return self._detect(text, symptom_id)

    def mentions_sleep(self, text: str, threshold: float = 0.3) -> bool:
        return self._detect(text, 15)

    def mentions_sadness(self, text: str) -> bool:
        return self._detect(text, 0)

    def mentions_anhedonia(self, text: str) -> bool:
        return self._detect(text, 3)

    def mentions_suicidality(self, text: str) -> bool:
        return self._detect(text, 8)

    def mentions_energy_loss(self, text: str) -> bool:
        return self._detect(text, 14)


class InterviewPolicy:
    """
    Semi-structured adaptive interview policy.
    Selects next question based on conversation state and symptom coverage.
    """

    def __init__(
        self,
        question_bank: QuestionBank,
        mention_detector: SymptomDetector,
        max_turns: int = 20,
        max_questions_per_symptom: int = 3,
    ):
        self.question_bank = question_bank
        self.mention_detector = mention_detector
        self.max_turns = max_turns
        self.max_questions_per_symptom = max_questions_per_symptom

        self.symptom_question_count: Dict[int, int] = {i: 0 for i in range(21)}
        self.symptoms_touched: set = set()
        self.high_priority_symptoms = [0, 3, 8, 14, 15]  # sadness, anhedonia, suicidality, energy, sleep

    def select_next_question(self, conv: Conversation) -> Optional[Question]:
        """
        Select the next question based on conversation state.

        Logic:
        1. Stop if max turns reached
        2. Early conversation: cycle through high-priority symptoms
        3. Later: use mention detection for adaptive follow-ups
        4. Otherwise: cover uncovered or under-covered symptoms
        """
        turn_count = len(conv.messages)

        if turn_count >= self.max_turns:
            return None

        #Early conversation: prioritize key symptoms
        if turn_count < 10:
            for symptom_id in self.high_priority_symptoms:
                if self.symptom_question_count[symptom_id] < self.max_questions_per_symptom:
                    # Ask broad if first time, follow-up otherwise
                    if self.symptom_question_count[symptom_id] == 0:
                        q = self.question_bank.sample_broad(symptom_id)
                    else:
                        q = self.question_bank.sample_followup(symptom_id)
                        if q is None:  # No follow-ups available
                            continue

                    if q:
                        self.symptom_question_count[symptom_id] += 1
                        self.symptoms_touched.add(symptom_id)
                        return q

        #Adaptive follow-up: check last persona message for sleep mention
        persona_messages = conv.get_persona_messages()
        if persona_messages:
            last_msg = persona_messages[-1]
            sleep_symptom_id = 15

            if (
                self.mention_detector.mentions_sleep(last_msg.text)
                and self.symptom_question_count[sleep_symptom_id] < self.max_questions_per_symptom
            ):
                q = self.question_bank.sample_followup(sleep_symptom_id)
                if q:
                    self.symptom_question_count[sleep_symptom_id] += 1
                    self.symptoms_touched.add(sleep_symptom_id)
                    return q

        #General coverage: find least-covered symptom
        uncovered_symptoms = [i for i in range(21) if i not in self.symptoms_touched]
        if uncovered_symptoms:
            symptom_id = random.choice(uncovered_symptoms)
            q = self.question_bank.sample_broad(symptom_id)
            if q:
                self.symptom_question_count[symptom_id] += 1
                self.symptoms_touched.add(symptom_id)
                return q

        #Under-covered symptoms
        under_covered = [
            i for i in range(21)
            if self.symptom_question_count[i] < self.max_questions_per_symptom
        ]
        if under_covered:
            symptom_id = random.choice(under_covered)
            q = self.question_bank.sample_followup(symptom_id)
            if q is None:
                q = self.question_bank.sample_broad(symptom_id)
            if q:
                self.symptom_question_count[symptom_id] += 1
                self.symptoms_touched.add(symptom_id)
                return q

        #No more questions to ask
        return None

class LLMSymptomScorer:
    """
    LLM-based BDI-II symptom scorer.
    Uses language models (OpenAI, Anthropic, or local) to score conversations.
    """

    def __init__(self, provider: str = "openai", model: Optional[str] = None):
        self.provider = provider
        self.model = model

    def _build_scoring_prompt(self, conversation: Conversation) -> str:
        conv_text = conversation.format_for_display()

        prompt = f"""You are a clinical psychologist assistant. Based on the following conversation between an interviewer and a client, assess the client's depression symptoms according to the BDI-II (Beck Depression Inventory-II).

The BDI-II measures 21 symptoms on a scale of 0-3:
- 0: Not present or minimal
- 1: Mild
- 2: Moderate
- 3: Severe

Conversation:
{conv_text}

For each of the 21 BDI-II symptoms below, provide a score from 0-3 based ONLY on evidence from the conversation. If a symptom is not discussed or there is insufficient information, score it as 0.

Respond in JSON format with symptom scores:

{{
  "Sadness": <score>,
  "Pessimism": <score>,
  "Past failure": <score>,
  "Loss of pleasure": <score>,
  "Guilty feelings": <score>,
  "Punishment feelings": <score>,
  "Self-dislike": <score>,
  "Self-criticalness": <score>,
  "Suicidal thoughts or wishes": <score>,
  "Crying": <score>,
  "Agitation": <score>,
  "Loss of interest in others": <score>,
  "Indecisiveness": <score>,
  "Worthlessness": <score>,
  "Loss of energy": <score>,
  "Changes in sleeping pattern": <score>,
  "Irritability": <score>,
  "Changes in appetite": <score>,
  "Concentration difficulty": <score>,
  "Tiredness or fatigue": <score>,
  "Loss of interest in sex": <score>,
  "reasoning": "<brief explanation of key symptoms detected>"
}}

Provide ONLY the JSON response, no additional text."""

        return prompt

    def score_conversation(self, conversation: Conversation) -> Dict[str, Any]:
        prompt = self._build_scoring_prompt(conversation)

        kwargs = {"temperature": 0.3, "max_tokens": 2000}
        if self.model:
            kwargs["model"] = self.model

        result_text = llm.chat(prompt, provider=self.provider, **kwargs)

        try:
            scores_dict = json.loads(result_text)
            reasoning = scores_dict.pop("reasoning", "No reasoning provided")
            item_scores = [float(scores_dict.get(symptom, 0)) for symptom in BDI_SYMPTOMS]

            return {
                "item_scores": item_scores,
                "reasoning": reasoning,
            }

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"Error parsing LLM response: {e}")
            print(f"Raw response: {result_text}")
            return {
                "item_scores": [0.0] * 21,
                "reasoning": f"Parse error: {e}",
            }


class ScoringPipeline:
    """
    End-to-end pipeline for scoring conversations.
    Converts conversation → symptom scores → BDI-II total → severity band.
    """

    def __init__(
        self,
        symptom_scorer: LLMSymptomScorer,
        question_bank: QuestionBank,
        mention_detector: SymptomDetector,
    ):
        self.symptom_scorer = symptom_scorer
        self.question_bank = question_bank
        self.mention_detector = mention_detector

    def score_conversation(self, conv: Conversation) -> Dict[str, Any]:
        """
        Score a complete conversation.

        Pipeline:
        1. Pass conversation to LLM scorer
        2. Get 21 symptom scores (0-3 each)
        3. Sum to BDI-II total [0, 63]
        4. Map to severity band
        """
        persona_messages = conv.get_persona_messages()

        if not persona_messages:
            # No persona messages, return zeros
            return {
                "item_scores": [0.0] * 21,
                "total_score": 0.0,
                "severity": "minimal",
                "reasoning": "No conversation data",
            }

        # Score with LLM
        result = self.symptom_scorer.score_conversation(conv)
        item_scores = result["item_scores"]
        reasoning = result.get("reasoning", "")

        item_scores = [min(3.0, max(0.0, score)) for score in item_scores]
        total_score = float(sum(item_scores))
        severity = self._severity_band(total_score)

        return {
            "item_scores": item_scores,
            "total_score": total_score,
            "severity": severity,
            "reasoning": reasoning,
        }

    @staticmethod
    def _severity_band(total_score: float) -> str:
        """Map BDI-II total to severity band."""
        if total_score <= 13:
            return "minimal"
        elif total_score <= 19:
            return "mild"
        elif total_score <= 28:
            return "moderate"
        else:
            return "severe"


#=============================
#     Persona Interface
#=============================
def query_persona(persona_id: str, question: str) -> str:
    """
    Query a real LLM persona via the eRisk 2026 API.

    Args:
        persona_id: Unique identifier for the persona
        question: Question to ask the persona

    Returns:
        Persona's response text

    TODO: Replace with actual eRisk persona API endpoint when released.
    Example implementation:
        import requests
        response = requests.post(
            "https://erisk-api.example.com/persona/query",
            json={"persona_id": persona_id, "question": question}
        )
        return response.json()["response"]
    """
    raise NotImplementedError(
        f"Real persona API not yet implemented. Cannot query persona '{persona_id}' with question: '{question}'"
    )


#=============================
#      Interview + Demo
#=============================
def run_interview(
    persona_id: str,
    policy: InterviewPolicy,
    scoring_pipeline: ScoringPipeline,
    max_turns: int = 20,
) -> Dict[str, Any]:

    conv = Conversation(persona_id=persona_id)

    print(f"Starting interview with persona {persona_id}...")
    print("=" * 60)

    for turn in range(max_turns):
        question = policy.select_next_question(conv)
        if question is None:
            print("\n[Interview ended: no more questions]\n")
            break

        conv.add_message("system", question.text, targeted_symptom_id=question.symptom_id)
        print(f"\nTurn {turn + 1} [Symptom: {question.symptom_name}]")
        print(f"System: {question.text}")

        reply = query_persona(persona_id, question.text)
        conv.add_message("persona", reply, targeted_symptom_id=question.symptom_id)
        print(f"Persona: {reply}")

    print("=" * 60)

    print("\nScoring conversation with LLM...")
    scores = scoring_pipeline.score_conversation(conv)

    return {
        "conversation": conv,
        "scores": scores,
    }


def main():
    print("\n" + "=" * 60)
    print("eRisk 2026 Task 1 MVP Pipeline (LLM-Based Scoring)")
    print("=" * 60 + "\n")

    random.seed(42)
    np.random.seed(42)

    print("Initializing components...")

    question_bank = QuestionBank()
    print("* Question bank loaded")

    #Initialize LLM provider (reads from .env or defaults to openai)
    provider = os.getenv("LLM_PROVIDER", "openai")
    model = os.getenv("LLM_MODEL", None)

    print(f"* Using LLM provider: {provider}")
    if model:
        print(f"Using model: {model}")

    #Initialize symptom detector (uses LLM for mention detection)
    mention_detector = SymptomDetector(provider=provider, model=model, cache=True)
    print("* Symptom detector initialized")

    #Initialize LLM symptom scorer
    symptom_scorer = LLMSymptomScorer(provider=provider, model=model)
    print("* LLM symptom scorer initialized\n")

    scoring_pipeline = ScoringPipeline(
        symptom_scorer=symptom_scorer,
        question_bank=question_bank,
        mention_detector=mention_detector,
    )

    policy = InterviewPolicy(
        question_bank=question_bank,
        mention_detector=mention_detector,
        max_turns=20,
        max_questions_per_symptom=2,
    )

    # Run interview with real persona
    # TODO: Replace with actual persona IDs from eRisk 2026 dataset
    persona_id = "test_persona_001"

    result = run_interview(
        persona_id=persona_id,
        policy=policy,
        scoring_pipeline=scoring_pipeline,
        max_turns=15,
    )

    print("\n" + "=" * 60)
    print("Interview Results")
    print("=" * 60 + "\n")

    scores = result["scores"]
    conv = result["conversation"]

    print(f"Total messages: {len(conv.messages)}")
    print(f"Persona messages: {len(conv.get_persona_messages())}\n")

    print("BDI-II Symptom Scores:")
    print("-" * 60)
    for idx, score in enumerate(scores["item_scores"]):
        symptom_name = BDI_SYMPTOMS[idx]
        print(f"{idx:2d}. {symptom_name:30s}: {score:.2f}")

    print("-" * 60)
    print(f"Total BDI-II Score: {scores['total_score']:.2f} / 63")
    print(f"Severity Band: {scores['severity'].upper()}")

    if "reasoning" in scores:
        print(f"\nLLM Reasoning:\n{scores['reasoning']}")

    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
