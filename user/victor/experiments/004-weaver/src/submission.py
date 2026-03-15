"""
Submission exporter for eRisk 2026 Task 1.

Handles formatting and saving output files according to the official
submission guidelines:
- interactions_<run_id>.json: Conversation logs
- results_<run_id>.json: BDI-II scores and key symptoms
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from models import InterviewResult


def export_interactions(
    results: List[InterviewResult],
    run_id: int = 1,
    output_dir: Optional[Path] = None,
    manual: bool = False,
) -> Path:
    """
    Export conversation logs in eRisk submission format.
    
    Args:
        results: List of InterviewResult objects
        run_id: Run number (1-3)
        output_dir: Directory to save file (default: results/)
        manual: Whether this is a manual/human-assisted run
        
    Returns:
        Path to saved file
    """
    if output_dir is None:
        output_dir = Path(__file__).parent.parent / "results"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Build interactions data
    interactions = [result.to_conversation_log() for result in results]
    
    # Sort by persona ID
    interactions.sort(key=lambda x: int(x["LLM"]))
    
    # Determine filename
    prefix = "manual_" if manual else ""
    filename = f"{prefix}interactions_run{run_id}.json"
    filepath = output_dir / filename
    
    with open(filepath, "w") as f:
        json.dump(interactions, f, indent=2)
    
    return filepath


def export_results(
    results: List[InterviewResult],
    run_id: int = 1,
    output_dir: Optional[Path] = None,
    manual: bool = False,
) -> Path:
    """
    Export classification results in eRisk submission format.
    
    Args:
        results: List of InterviewResult objects
        run_id: Run number (1-3)
        output_dir: Directory to save file (default: results/)
        manual: Whether this is a manual/human-assisted run
        
    Returns:
        Path to saved file
    """
    if output_dir is None:
        output_dir = Path(__file__).parent.parent / "results"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Build results data
    results_data = [result.to_result_entry() for result in results]
    
    # Sort by persona ID
    results_data.sort(key=lambda x: int(x["LLM"]))
    
    # Determine filename
    prefix = "manual_" if manual else ""
    filename = f"{prefix}results_run{run_id}.json"
    filepath = output_dir / filename
    
    with open(filepath, "w") as f:
        json.dump(results_data, f, indent=2)
    
    return filepath


def export_all(
    results: List[InterviewResult],
    run_id: int = 1,
    output_dir: Optional[Path] = None,
    manual: bool = False,
) -> Dict[str, Path]:
    """
    Export both interactions and results files.
    
    Args:
        results: List of InterviewResult objects
        run_id: Run number (1-3)
        output_dir: Directory to save files
        manual: Whether this is a manual/human-assisted run
        
    Returns:
        Dict with 'interactions' and 'results' paths
    """
    interactions_path = export_interactions(results, run_id, output_dir, manual)
    results_path = export_results(results, run_id, output_dir, manual)
    
    return {
        "interactions": interactions_path,
        "results": results_path,
    }


def export_detailed_log(
    results: List[InterviewResult],
    run_id: int = 1,
    output_dir: Optional[Path] = None,
) -> Path:
    """
    Export detailed logs with full assessment data (not for submission).
    
    Includes reasoning, turn-by-turn assessments, and other metadata
    useful for debugging and analysis.
    
    Args:
        results: List of InterviewResult objects
        run_id: Run number
        output_dir: Directory to save file
        
    Returns:
        Path to saved file
    """
    if output_dir is None:
        output_dir = Path(__file__).parent.parent / "results"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    detailed_data = []
    for result in results:
        detailed_data.append({
            "persona_id": result.persona_id,
            "total_turns": len(result.messages) // 2,
            "bdi_score": result.total_bdi_score,
            "severity": result.severity,
            "key_symptoms": result.key_symptoms,
            "confidence": result.confidence,
            "final_assessment": {
                sid: {
                    "score": s.score,
                    "confidence": s.confidence,
                    "evidence": s.evidence,
                }
                for sid, s in result.final_scores.symptoms.items()
            } if result.final_scores else None,
            "scorer_history": [
                {
                    "pass": i + 1,
                    "total_score": so.total_score,
                    "severity": so.severity,
                    "mean_confidence": so.mean_confidence,
                }
                for i, so in enumerate(result.scorer_history)
            ],
            "messages": [
                {"role": m.role, "content": m.content, "turn": m.turn}
                for m in result.messages
            ],
        })
    
    # Sort by persona ID
    detailed_data.sort(key=lambda x: x["persona_id"])
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"detailed_log_run{run_id}_{timestamp}.json"
    filepath = output_dir / filename
    
    with open(filepath, "w") as f:
        json.dump(detailed_data, f, indent=2)
    
    return filepath


def validate_submission(
    interactions_path: Path,
    results_path: Path,
) -> Dict[str, Any]:
    """
    Validate submission files against eRisk format requirements.
    
    Args:
        interactions_path: Path to interactions JSON file
        results_path: Path to results JSON file
        
    Returns:
        Dict with validation status and any errors
    """
    errors = []
    warnings = []
    
    # Load files
    try:
        with open(interactions_path) as f:
            interactions = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        errors.append(f"Failed to load interactions file: {e}")
        interactions = []
    
    try:
        with open(results_path) as f:
            results = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        errors.append(f"Failed to load results file: {e}")
        results = []
    
    # Check interactions format
    interaction_llms = set()
    for i, item in enumerate(interactions):
        if "LLM" not in item:
            errors.append(f"Interaction {i}: missing 'LLM' field")
        else:
            interaction_llms.add(item["LLM"])
        
        if "conversation" not in item:
            errors.append(f"Interaction {i}: missing 'conversation' field")
        else:
            for j, msg in enumerate(item["conversation"]):
                if "role" not in msg:
                    errors.append(f"Interaction {i}, message {j}: missing 'role' field")
                elif msg["role"] not in ("user", "assistant"):
                    errors.append(f"Interaction {i}, message {j}: invalid role '{msg['role']}'")
                if "message" not in msg:
                    errors.append(f"Interaction {i}, message {j}: missing 'message' field")
    
    # Check results format
    result_llms = set()
    for i, item in enumerate(results):
        if "LLM" not in item:
            errors.append(f"Result {i}: missing 'LLM' field")
        else:
            result_llms.add(item["LLM"])
        
        if "bdi-score" not in item:
            errors.append(f"Result {i}: missing 'bdi-score' field")
        elif not isinstance(item["bdi-score"], int):
            warnings.append(f"Result {i}: 'bdi-score' should be integer")
        elif not 0 <= item["bdi-score"] <= 63:
            warnings.append(f"Result {i}: 'bdi-score' {item['bdi-score']} outside valid range 0-63")
        
        if "key-symptoms" not in item:
            errors.append(f"Result {i}: missing 'key-symptoms' field")
        elif len(item["key-symptoms"]) > 4:
            warnings.append(f"Result {i}: more than 4 key symptoms listed")
    
    # Check persona coverage
    expected_llms = set(str(i) for i in range(1, 21))
    missing_interactions = expected_llms - interaction_llms
    missing_results = expected_llms - result_llms
    
    if missing_interactions:
        warnings.append(f"Missing interactions for personas: {sorted(missing_interactions)}")
    if missing_results:
        warnings.append(f"Missing results for personas: {sorted(missing_results)}")
    
    # Check consistency
    if interaction_llms != result_llms:
        extra_interactions = interaction_llms - result_llms
        extra_results = result_llms - interaction_llms
        if extra_interactions:
            warnings.append(f"Personas in interactions but not results: {sorted(extra_interactions)}")
        if extra_results:
            warnings.append(f"Personas in results but not interactions: {sorted(extra_results)}")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "personas_count": len(result_llms),
    }


if __name__ == "__main__":
    # Test with mock data
    from models import InterviewResult, ConversationMessage

    mock_results = []
    for persona_id in [1, 2]:
        result = InterviewResult(persona_id=persona_id)
        result.messages = [
            ConversationMessage(
                role="interviewer",
                content="How have you been feeling lately?",
                turn=1,
            ),
            ConversationMessage(
                role="persona",
                content="Not great, honestly. I've been feeling pretty down.",
                turn=1,
            ),
            ConversationMessage(
                role="interviewer",
                content="I'm sorry to hear that. How long has this been going on?",
                turn=2,
            ),
            ConversationMessage(
                role="persona",
                content="A few weeks now. It's been hard.",
                turn=2,
            ),
        ]
        result.total_bdi_score = 18 if persona_id == 1 else 5
        result.severity = "Mild" if persona_id == 1 else "Minimal"
        result.key_symptoms = ["Sadness", "Loss of energy"] if persona_id == 1 else []
        result.confidence = 0.8
        mock_results.append(result)
    
    # Export
    print("Testing submission export...")
    paths = export_all(mock_results, run_id=1)
    print(f"Interactions: {paths['interactions']}")
    print(f"Results: {paths['results']}")
    
    # Validate
    print("\nValidating submission...")
    validation = validate_submission(paths["interactions"], paths["results"])
    print(f"Valid: {validation['valid']}")
    print(f"Personas: {validation['personas_count']}")
    if validation["errors"]:
        print(f"Errors: {validation['errors']}")
    if validation["warnings"]:
        print(f"Warnings: {validation['warnings']}")
