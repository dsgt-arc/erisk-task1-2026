"""
eRisk 2026 Task 1: Open-Source Multi-Agent Depression Detection

CLI entry point. All LLM calls routed through OpenRouter API.
Use --free for zero-cost open-source models.
"""

import os
import argparse
from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime

from models import InterviewResult
from agents.interviewer import InterviewerAgent
from agents.scorer import ScorerAgent
from agents.orchestrator import Orchestrator
from pipeline import InterviewPipeline
import submission


def load_env():
    """Load environment variables from .env file."""
    env_paths = [
        Path(__file__).parent.parent / ".env",
        Path(__file__).parents[4] / ".env",
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


def make_mock_persona():
    """Create a mock persona for local testing without GPU."""
    responses = [
        "I've been feeling pretty down lately, to be honest. Nothing seems to interest me anymore.",
        "Yeah, it's been like this for a few weeks now. I used to love playing guitar but I haven't touched it in over a month.",
        "Sleep has been terrible. I wake up at 4am and can't get back to sleep. Then I'm exhausted all day.",
        "My appetite is basically gone. I have to force myself to eat.",
        "I guess I've been avoiding my friends. It just feels like too much effort.",
        "I don't know, I just feel kind of worthless sometimes. Like nothing I do matters.",
        "I've been having trouble focusing at work. Can't seem to get through a simple report without zoning out.",
        "I cry sometimes, yeah. Usually at night when I'm alone. It just comes out of nowhere.",
        "I guess I'm pretty hard on myself. I keep thinking about all the mistakes I've made.",
        "I'm just so tired all the time. Even small things feel exhausting.",
        "I'm more irritable than usual. I snap at people for no reason and then feel terrible about it.",
        "Thanks for listening. It's been hard to talk about this stuff.",
        "Yeah, I think that's about right. It's been a rough few months.",
        "I appreciate you taking the time. It means a lot.",
    ]
    call_count = [0]

    def mock_fn(message, history):
        idx = min(call_count[0], len(responses) - 1)
        call_count[0] += 1
        return responses[idx]

    return mock_fn


def export_submission_files(
    results: List[InterviewResult],
    run_id: int = 1,
    output_dir: Optional[Path] = None,
    manual: bool = False,
) -> Dict[str, Path]:
    """Export results in eRisk submission format."""
    if not results:
        raise ValueError("No results to export.")

    print(f"\nExporting submission files (run {run_id})...")

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

    print(f"  Interactions: {paths['interactions']}")
    print(f"  Results: {paths['results']}")
    print(f"  Detailed log: {paths['detailed']}")

    validation = submission.validate_submission(
        paths["interactions"],
        paths["results"],
    )

    if validation["valid"]:
        print(f"  Validation: PASSED ({validation['personas_count']} personas)")
    else:
        print("  Validation: FAILED")
        for error in validation["errors"]:
            print(f"    ERROR: {error}")

    for warning in validation.get("warnings", []):
        print(f"    WARNING: {warning}")

    return paths


def print_summary(results: List[InterviewResult]):
    """Print summary of all interview results."""
    if not results:
        print("No results to summarize.")
        return

    print(f"\n{'='*60}")
    print("Interview Summary")
    print(f"{'='*60}\n")

    print(f"{'Persona':<10} {'Turns':<8} {'BDI':<6} {'Severity':<12} {'Conf':<8} {'Key Symptoms'}")
    print("-" * 80)

    for result in sorted(results, key=lambda r: r.persona_id):
        symptoms = ", ".join(result.key_symptoms[:3]) if result.key_symptoms else "-"
        n_turns = len(result.messages) // 2
        print(f"{result.persona_id:<10} {n_turns:<8} {result.total_bdi_score:<6} "
              f"{result.severity:<12} {result.confidence:<8.2f} {symptoms}")

    print("-" * 80)

    avg_score = sum(r.total_bdi_score for r in results) / len(results)
    avg_turns = sum(len(r.messages) // 2 for r in results) / len(results)
    avg_conf = sum(r.confidence for r in results) / len(results)

    print(f"\nTotal personas: {len(results)}")
    print(f"Average BDI score: {avg_score:.1f}")
    print(f"Average turns: {avg_turns:.1f}")
    print(f"Average confidence: {avg_conf:.2f}")
    print()


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="eRisk 2026 Task 1: Multi-Agent Depression Detection"
    )

    # Persona selection
    parser.add_argument("--personas", type=int, nargs="+", default=[1, 2],
                        help="Persona IDs to interview (default: 1 2)")
    parser.add_argument("--run-id", type=int, default=1, choices=[1, 2, 3],
                        help="Run number for submission (1-3)")

    # Model selection (OpenRouter model strings)
    parser.add_argument("--interviewer-model", type=str, default=None,
                        help="OpenRouter model for interviewer (e.g. openai/gpt-4.1-mini)")
    parser.add_argument("--scorer-model", type=str, default=None,
                        help="OpenRouter model for scorer (e.g. openai/gpt-4.1-mini)")
    parser.add_argument("--free", action="store_true",
                        help="Use free open-source models (meta-llama/llama-3.1-8b-instruct:free)")
    parser.add_argument("--ensemble-size", type=int, default=1,
                        help="Number of scorer passes (1=fast, 3=accurate)")
    parser.add_argument("--score-every-n", type=int, default=1,
                        help="Score transcript every N turns")

    # Orchestrator config
    parser.add_argument("--max-turns", type=int, default=18,
                        help="Maximum turns per interview")
    parser.add_argument("--confidence-threshold", type=float, default=0.6,
                        help="Confidence threshold for stopping")

    # Output
    parser.add_argument("--output-dir", type=Path, default=None,
                        help="Output directory for submission files")
    parser.add_argument("--manual", action="store_true",
                        help="Mark as manual/human-assisted run")
    parser.add_argument("--quiet", action="store_true",
                        help="Suppress verbose output")

    # Dialogue tree
    parser.add_argument("--use-tree", action="store_true",
                        help="Enable precomputed dialogue tree for interviewer")
    parser.add_argument("--tree-threshold", type=float, default=1.5,
                        help="BM25 match threshold for dialogue tree followups")
    parser.add_argument("--use-lf", action="store_true",
                        help="Enable labeling functions for orchestrator")

    # Testing
    parser.add_argument("--mock-persona", action="store_true",
                        help="Use mock persona instead of real Llama model")

    args = parser.parse_args()
    verbose = not args.quiet

    # Resolve model selection: explicit flag > --free > paid default
    # --free only affects interviewer; scorer stays paid for reliable JSON output
    from llm import PAID_DEFAULT, FREE_DEFAULT
    interviewer_model = args.interviewer_model or (FREE_DEFAULT if args.free else PAID_DEFAULT)
    scorer_model = args.scorer_model or PAID_DEFAULT

    print("\n" + "=" * 60)
    print("eRisk 2026 Task 1: Open-Source Depression Detection")
    print("=" * 60 + "\n")

    # Load dialogue tree if requested
    tree_bank = None
    if args.use_tree:
        from dialogue_tree import load_bank
        tree_path = Path(__file__).parent.parent / "data" / "question_bank.yaml"
        tree_bank = load_bank(tree_path)

    print("Configuration:")
    print(f"  Personas: {args.personas}")
    print(f"  Run ID: {args.run_id}")
    print(f"  Interviewer model: {interviewer_model}")
    print(f"  Scorer model: {scorer_model}"
          + f" (ensemble={args.ensemble_size}, every={args.score_every_n})")
    print(f"  Max turns: {args.max_turns}")
    print(f"  Confidence threshold: {args.confidence_threshold}")
    print(f"  Mock persona: {args.mock_persona}")
    if args.free:
        print(f"  Mode: FREE (open-source models)")
    if args.use_tree:
        n_openers = sum(
            len(c.get("openers", []))
            for c in tree_bank.get("clusters", {}).values()
        )
        print(f"  Dialogue tree: ON ({n_openers} openers, threshold={args.tree_threshold})")
    if args.use_lf:
        print(f"  Labeling functions: ON")
    print()

    # Create agents
    interviewer = InterviewerAgent(
        model=interviewer_model,
        tree_bank=tree_bank,
        tree_threshold=args.tree_threshold,
    )
    scorer = ScorerAgent(
        model=scorer_model,
        ensemble_size=args.ensemble_size,
    )
    orchestrator = Orchestrator(
        confidence_threshold=args.confidence_threshold,
        max_turns=args.max_turns,
    )

    pipeline = InterviewPipeline(
        interviewer=interviewer,
        scorer=scorer,
        orchestrator=orchestrator,
        max_turns=args.max_turns,
        score_every_n_turns=args.score_every_n,
        verbose=verbose,
        use_lf=args.use_lf,
    )

    # Run interviews
    start_time = datetime.now()
    results = []

    for i, persona_id in enumerate(args.personas):
        print(f"\n[{i+1}/{len(args.personas)}] Starting persona {persona_id}...")

        if args.mock_persona:
            query_fn = make_mock_persona()
        else:
            from persona import Persona
            p = Persona(persona_id=persona_id)

            def query_fn(msg, hist, _p=p):
                return _p.chat(msg)[-1]["content"]

        result = pipeline.run(persona_query_fn=query_fn, persona_id=persona_id)
        results.append(result)

    duration = datetime.now() - start_time
    print(f"\nCompleted {len(args.personas)} interviews in {duration}")

    # Print summary
    print_summary(results)

    # Export submission
    paths = export_submission_files(
        results=results,
        run_id=args.run_id,
        output_dir=args.output_dir,
        manual=args.manual,
    )

    print("\nDone!")
    print(f"Submission files saved to: {paths['interactions'].parent}")


if __name__ == "__main__":
    main()
