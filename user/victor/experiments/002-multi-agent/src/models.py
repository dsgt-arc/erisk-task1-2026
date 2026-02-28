"""
Shared data models for the multi-agent depression detection pipeline.

All agents communicate through these data classes. The orchestrator reads
ScorerOutput and writes OrchestratorGuidance. The interviewer reads
OrchestratorGuidance. The scorer reads conversation transcripts.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any


# BDI-II symptom IDs (official ordering)
BDI_SYMPTOM_IDS = [
    "q01_sadness",
    "q02_pessimism",
    "q03_past_failure",
    "q04_anhedonia",
    "q05_guilt",
    "q06_punishment",
    "q07_self_dislike",
    "q08_self_criticalness",
    "q09_suicidal_thoughts",
    "q10_crying",
    "q11_agitation",
    "q12_loss_of_interest",
    "q13_indecisiveness",
    "q14_worthlessness",
    "q15_energy",
    "q16_sleep",
    "q17_irritability",
    "q18_appetite",
    "q19_concentration",
    "q20_fatigue",
    "q21_sex",
]

BDI_SYMPTOM_NAMES = [
    "Sadness", "Pessimism", "Past failure", "Loss of pleasure",
    "Guilty feelings", "Punishment feelings", "Self-dislike",
    "Self-criticalness", "Suicidal thoughts or wishes", "Crying",
    "Agitation", "Loss of interest in others", "Indecisiveness",
    "Worthlessness", "Loss of energy", "Changes in sleeping pattern",
    "Irritability", "Changes in appetite", "Concentration difficulty",
    "Tiredness or fatigue", "Loss of interest in sex",
]

SYMPTOM_ID_TO_NAME = dict(zip(BDI_SYMPTOM_IDS, BDI_SYMPTOM_NAMES))
SYMPTOM_NAME_TO_ID = dict(zip(BDI_SYMPTOM_NAMES, BDI_SYMPTOM_IDS))


@dataclass
class SymptomScore:
    """Assessment of a single BDI-II symptom."""
    symptom_id: str
    score: int
    confidence: float
    evidence: str
    assessed: bool = False

    @property
    def name(self) -> str:
        return SYMPTOM_ID_TO_NAME.get(self.symptom_id, self.symptom_id)


@dataclass
class ScorerOutput:
    """Complete output from the scorer agent for one scoring pass."""
    symptoms: Dict[str, SymptomScore]
    total_score: int = 0
    severity: str = "Minimal"
    reasoning: str = ""

    def __post_init__(self):
        self.total_score = sum(s.score for s in self.symptoms.values())
        self.severity = self._compute_severity(self.total_score)

    @staticmethod
    def _compute_severity(total: int) -> str:
        if total <= 13:
            return "Minimal"
        elif total <= 19:
            return "Mild"
        elif total <= 28:
            return "Moderate"
        else:
            return "Severe"

    @property
    def mean_confidence(self) -> float:
        if not self.symptoms:
            return 0.0
        return sum(s.confidence for s in self.symptoms.values()) / len(self.symptoms)

    def low_confidence_symptoms(self, threshold: float = 0.5) -> List[SymptomScore]:
        """Return symptoms below the confidence threshold, sorted ascending."""
        return sorted(
            [s for s in self.symptoms.values() if s.confidence < threshold],
            key=lambda s: s.confidence,
        )

    def unassessed_symptoms(self) -> List[SymptomScore]:
        """Return symptoms that have not been assessed yet."""
        return [s for s in self.symptoms.values() if not s.assessed]


@dataclass
class OrchestratorGuidance:
    """Instructions from the orchestrator to the interviewer agent."""
    focus_symptoms: List[str]
    guidance_text: str
    wrap_up: bool = False
    turn_number: int = 0
    scores_stable: bool = False


@dataclass
class ConversationMessage:
    """A single message in the conversation."""
    role: str  # "interviewer" or "persona"
    content: str
    turn: int


@dataclass
class InterviewState:
    """Mutable state of an ongoing interview."""
    persona_id: int
    messages: List[ConversationMessage] = field(default_factory=list)
    scorer_history: List[ScorerOutput] = field(default_factory=list)
    guidance_history: List[OrchestratorGuidance] = field(default_factory=list)
    current_turn: int = 0
    finished: bool = False
    finish_reason: str = ""

    def transcript_text(self) -> str:
        """Format the conversation as a plain-text transcript for the scorer."""
        lines = []
        for msg in self.messages:
            role_label = "Interviewer" if msg.role == "interviewer" else "Persona"
            lines.append(f"{role_label}: {msg.content}")
        return "\n".join(lines)

    def to_llm_history(self) -> List[Dict[str, str]]:
        """Convert to format expected by persona.chat() / submission export."""
        result = []
        for msg in self.messages:
            role = "user" if msg.role == "interviewer" else "assistant"
            result.append({"role": role, "message": msg.content})
        return result


@dataclass
class InterviewResult:
    """Final result of a completed interview. Compatible with submission.py."""
    persona_id: int
    messages: List[ConversationMessage] = field(default_factory=list)
    final_scores: Optional[ScorerOutput] = None
    total_bdi_score: int = 0
    severity: str = "Minimal"
    key_symptoms: List[str] = field(default_factory=list)
    confidence: float = 0.0
    scorer_history: List[ScorerOutput] = field(default_factory=list)

    def to_conversation_log(self) -> Dict[str, Any]:
        """Convert to eRisk submission format for interactions file."""
        conversation = []
        for msg in self.messages:
            role = "user" if msg.role == "interviewer" else "assistant"
            conversation.append({"role": role, "message": msg.content})
        return {"LLM": str(self.persona_id), "conversation": conversation}

    def to_result_entry(self) -> Dict[str, Any]:
        """Convert to eRisk submission format for results file."""
        return {
            "LLM": str(self.persona_id),
            "bdi-score": self.total_bdi_score,
            "key-symptoms": self.key_symptoms[:4],
        }
