"""
Select the 3 runs closest to the mean BDI-II score from a batch of samples.

Usage:
    python select_runs.py <persona_id>
    python select_runs.py 4           # analyze persona 4 samples
    python select_runs.py 4 --top 3   # pick top 3 (default)
"""

import argparse
import json
import shutil
import statistics
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Select best runs from samples")
    parser.add_argument("persona_id", type=int, help="Persona ID")
    parser.add_argument("--top", type=int, default=3, help="Number of runs to select")
    parser.add_argument("--samples-dir", type=Path, default=None,
                        help="Samples directory (default: results/samples/persona-{id})")
    parser.add_argument("--output-dir", type=Path, default=None,
                        help="Output directory for selected runs")
    args = parser.parse_args()

    if args.samples_dir is None:
        args.samples_dir = Path(__file__).parent / "results" / "samples" / f"persona-{args.persona_id}"
    if args.output_dir is None:
        args.output_dir = Path(__file__).parent / "submissions" / f"persona-{args.persona_id}"

    # Collect all sample scores
    samples = []
    for sample_dir in sorted(args.samples_dir.iterdir()):
        results_file = sample_dir / "results_run1.json"
        if not results_file.exists():
            continue
        with open(results_file) as f:
            data = json.load(f)
        if not data:
            continue
        score = data[0]["bdi-score"]
        samples.append({"dir": sample_dir, "score": score, "name": sample_dir.name})

    if not samples:
        print(f"No samples found in {args.samples_dir}")
        return

    # Stats
    scores = [s["score"] for s in samples]
    mean = statistics.mean(scores)
    median = statistics.median(scores)
    stdev = statistics.stdev(scores) if len(scores) > 1 else 0

    print(f"Persona {args.persona_id}: {len(samples)} samples")
    print(f"  Scores: {sorted(scores)}")
    print(f"  Mean: {mean:.1f}, Median: {median:.1f}, Stdev: {stdev:.1f}")
    print(f"  Range: {min(scores)} - {max(scores)}")
    print()

    # Rank by distance from mean
    ranked = sorted(samples, key=lambda s: abs(s["score"] - mean))
    selected = ranked[:args.top]

    print(f"Selected {args.top} closest to mean ({mean:.1f}):")
    for i, s in enumerate(selected):
        dist = abs(s["score"] - mean)
        print(f"  Run {i+1}: {s['name']} → BDI={s['score']} (dist={dist:.1f})")

    # Copy to submissions directory
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for i, s in enumerate(selected):
        run_id = i + 1
        dest = args.output_dir / f"run-{run_id}"
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(s["dir"], dest)

        # Rename files to match run ID
        for old_file in dest.glob("*_run1.*"):
            new_name = old_file.name.replace("_run1", f"_run{run_id}")
            old_file.rename(dest / new_name)

        print(f"  → Copied to {dest}")

    print(f"\nDone. Submissions in {args.output_dir}")


if __name__ == "__main__":
    main()
