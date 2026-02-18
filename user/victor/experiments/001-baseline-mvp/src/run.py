"""
eRisk 2026 Task 1: Conversational Depression Detection Pipeline

Main orchestration module for running interviews with LLM personas
and generating BDI-II depression assessments.

Architecture:
- Persona: Llama-3-8B-Instruct + LoRA adapter (loaded locally)
- Interviewer: External LLM (OpenAI/Claude) with conversation.md prompt
- Submission: JSON exports per eRisk format specification
"""

import os
import argparse
from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime

# Local imports
from persona import Persona
from interviewer import Interviewer, InterviewResult, run_interview
import submission


_verbose = True


def load_env():
    """Load environment variables from .env file."""
    env_paths = [
        Path(__file__).parent.parent / ".env",
        Path(__file__).parents[4] / ".env",  # Repo root
    ]

    for env_file in env_paths:
        if env_file.exists():
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        if value and key.strip() not in os.environ:
                            os.environ[key.strip()] = value.strip()
            break


load_env()


def _log(message: str):
    """Print message if verbose mode enabled."""
    if _verbose:
        print(message)


def interview_persona(
    interviewer: Interviewer, persona_id: int
) -> InterviewResult:
    """
    Run a complete interview with a single persona.

    Args:
        interviewer: Interviewer instance to conduct the interview
        persona_id: Persona number (1-20)

    Returns:
        InterviewResult with conversation and assessment
    """
    _log(f"\n{'='*60}")
    _log(f"Starting interview with Persona {persona_id}")
    _log(f"{'='*60}")

    p = Persona()
    _log(f"Persona {persona_id} loaded.")

    def query_fn(message: str, _history: List[Dict[str, str]]) -> str:
        messages = p.chat(message)
        return messages[-1]["content"]

    return run_interview(
        interviewer=interviewer,
        persona_query_fn=query_fn,
        persona_id=persona_id,
        verbose=_verbose,
    )


def interview_all(
    interviewer: Interviewer, persona_ids: List[int]
) -> List[InterviewResult]:
    """
    Run interviews with multiple personas.

    Args:
        interviewer: Interviewer instance to conduct the interviews
        persona_ids: List of persona numbers to interview

    Returns:
        List of InterviewResult objects
    """
    _log(f"\nRunning interviews with {len(persona_ids)} personas...")
    _log(f"Personas: {persona_ids}")

    start_time = datetime.now()
    results = []

    for i, persona_id in enumerate(persona_ids):
        _log(f"\n[{i+1}/{len(persona_ids)}] Interviewing persona {persona_id}...")
        results.append(interview_persona(interviewer, persona_id))

    duration = datetime.now() - start_time
    _log(f"\nCompleted {len(persona_ids)} interviews in {duration}")

    return results


def export_submission(
    results: List[InterviewResult],
    run_id: int = 1,
    output_dir: Optional[Path] = None,
    manual: bool = False,
) -> Dict[str, Path]:
    """
    Export results in eRisk submission format.

    Args:
        results: List of InterviewResult objects
        run_id: Run number (1-3)
        output_dir: Directory for output files
        manual: Whether this is a manual/human-assisted run

    Returns:
        Dict with paths to exported files
    """
    if not results:
        raise ValueError("No results to export. Run interviews first.")

    _log(f"\nExporting submission files (run {run_id})...")

    paths = submission.export_all(
        results=results,
        run_id=run_id,
        output_dir=output_dir,
        manual=manual,
    )

    detailed_path = submission.export_detailed_log(
        results=results,
        run_id=run_id,
        output_dir=output_dir,
    )
    paths["detailed"] = detailed_path

    _log(f"Interactions: {paths['interactions']}")
    _log(f"Results: {paths['results']}")
    _log(f"Detailed log: {paths['detailed']}")

    validation = submission.validate_submission(
        paths["interactions"],
        paths["results"],
    )

    if validation["valid"]:
        _log(f"Validation: PASSED ({validation['personas_count']} personas)")
    else:
        _log("Validation: FAILED")
        for error in validation["errors"]:
            _log(f"  ERROR: {error}")

    for warning in validation.get("warnings", []):
        _log(f"  WARNING: {warning}")

    return paths


def print_summary(results: List[InterviewResult]):
    """Print summary of all interview results."""
    if not results:
        print("No results to summarize.")
        return

    print(f"\n{'='*60}")
    print("Interview Summary")
    print(f"{'='*60}\n")

    print(f"{'Persona':<10} {'Turns':<8} {'BDI':<6} {'Severity':<12} {'Key Symptoms'}")
    print("-" * 70)

    for result in sorted(results, key=lambda r: r.persona_id):
        symptoms = ", ".join(result.key_symptoms[:3]) if result.key_symptoms else "-"
        print(f"{result.persona_id:<10} {len(result.turns):<8} {result.total_bdi_score:<6} {result.severity:<12} {symptoms}")

    print("-" * 70)

    avg_score = sum(r.total_bdi_score for r in results) / len(results)
    avg_turns = sum(len(r.turns) for r in results) / len(results)

    print(f"\nTotal personas: {len(results)}")
    print(f"Average BDI score: {avg_score:.1f}")
    print(f"Average turns: {avg_turns:.1f}")
    print()


def main():
    """CLI entry point."""
    global _verbose

    parser = argparse.ArgumentParser(
        description="eRisk 2026 Task 1: Conversational Depression Detection"
    )

    parser.add_argument(
        "--personas", type=int, nargs="+", default=[1, 2],
        help="Persona IDs to interview (default: 1 2)",
    )
    parser.add_argument(
        "--run-id", type=int, default=1, choices=[1, 2, 3],
        help="Run number for submission (1-3)",
    )
    parser.add_argument(
        "--provider", type=str, default="anthropic", choices=["openai", "anthropic"],
        help="LLM provider for interviewer",
    )
    parser.add_argument(
        "--model", type=str, default=None,
        help="Specific model to use for interviewer",
    )
    parser.add_argument(
        "--max-turns", type=int, default=18,
        help="Maximum turns per interview",
    )
    parser.add_argument(
        "--output-dir", type=Path, default=None,
        help="Output directory for submission files",
    )
    parser.add_argument(
        "--manual", action="store_true",
        help="Mark this as a manual/human-assisted run",
    )
    parser.add_argument(
        "--quiet", action="store_true",
        help="Suppress verbose output",
    )

    args = parser.parse_args()
    _verbose = not args.quiet

    print("\n" + "=" * 60)
    print("eRisk 2026 Task 1: Conversational Depression Detection")
    print("=" * 60 + "\n")

    print(f"Configuration:")
    print(f"  Personas: {args.personas}")
    print(f"  Run ID: {args.run_id}")
    print(f"  Interviewer: {args.provider}" + (f" ({args.model})" if args.model else ""))
    print(f"  Max turns: {args.max_turns}")
    print(f"  Manual run: {args.manual}")
    print()

    interviewer = Interviewer(
        provider=args.provider,
        model=args.model,
        max_turns=args.max_turns,
    )

    # Run interviews
    results = interview_all(interviewer, args.personas)

    # Print summary
    print_summary(results)

    # Export submission
    paths = export_submission(
        results=results,
        run_id=args.run_id,
        output_dir=args.output_dir,
        manual=args.manual,
    )

    print("\nDone!")
    print(f"Submission files saved to: {paths['interactions'].parent}")


if __name__ == "__main__":
    main()
