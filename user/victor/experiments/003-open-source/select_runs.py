"""
Select the 3 runs closest to the median BDI-II score from a batch of samples.

Usage:
    python select_runs.py <persona_id>
    python select_runs.py 4           # analyze persona 4 (paid only)
    python select_runs.py 4 --free    # analyze persona 4 (free only)
    python select_runs.py 4 --mix     # pool paid + free, pick best 3
    python select_runs.py 4 --top 3   # pick top 3 (default)
    python select_runs.py 4 --csv     # export scores to CSV
"""

import argparse
import csv
import json
import shutil
import statistics
from collections import Counter
from pathlib import Path


def collect_samples(samples_dir: Path, tier_label: str = ""):
    """Collect all sample scores from a persona's samples directory."""
    if not samples_dir.exists():
        return []
    samples = []
    for sample_dir in sorted(samples_dir.iterdir()):
        results_file = sample_dir / "results_run1.json"
        if not results_file.exists():
            continue
        with open(results_file) as f:
            data = json.load(f)
        if not data:
            continue

        label = f"{tier_label}/{sample_dir.name}" if tier_label else sample_dir.name
        entry = {"dir": sample_dir, "score": data[0]["bdi-score"], "name": label, "tier": tier_label}

        # Pull key symptoms if available
        entry["key_symptoms"] = data[0].get("key-symptoms", [])

        # Pull confidence from detailed log if available
        detailed = list(sample_dir.glob("detailed_log_run1_*.json"))
        if detailed:
            with open(detailed[0]) as f:
                detail_data = json.load(f)
            if detail_data:
                entry["confidence"] = detail_data[0].get("confidence", 0.0)
                entry["severity"] = detail_data[0].get("severity", "")
                entry["turns"] = detail_data[0].get("total_turns", 0)
        samples.append(entry)
    return samples


def print_histogram(scores, median_val):
    """Print an ASCII histogram of the score distribution."""
    if not scores:
        return

    # Bucket into bins of width 5 (0-4, 5-9, 10-14, ...)
    max_score = max(scores)
    bins = {}
    for s in scores:
        bucket = (s // 5) * 5
        bins[bucket] = bins.get(bucket, 0) + 1

    max_count = max(bins.values())
    bar_width = 40

    print("  BDI Score Distribution:")
    for bucket in range(0, max_score + 5, 5):
        count = bins.get(bucket, 0)
        bar_len = int((count / max_count) * bar_width) if max_count > 0 else 0
        bar = "█" * bar_len
        label = f"  {bucket:2d}-{bucket+4:2d}"
        median_marker = " ◄ median" if bucket <= median_val < bucket + 5 else ""
        print(f"{label} |{bar} {count}{median_marker}")
    print()


def export_csv(samples, persona_id, output_path):
    """Export sample scores to CSV."""
    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["persona_id", "sample", "bdi_score", "severity", "confidence", "turns", "key_symptoms"])
        for s in sorted(samples, key=lambda x: x["score"]):
            writer.writerow([
                persona_id,
                s["name"],
                s["score"],
                s.get("severity", ""),
                f"{s.get('confidence', 0.0):.2f}",
                s.get("turns", ""),
                "; ".join(s.get("key_symptoms", [])),
            ])
    print(f"  CSV exported to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Select best runs from samples")
    parser.add_argument("persona_id", type=int, help="Persona ID")
    parser.add_argument("--top", type=int, default=3, help="Number of runs to select")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--free", action="store_true",
                      help="Use samples-free directory (default: samples-paid)")
    mode.add_argument("--mix", action="store_true",
                      help="Pool paid + free samples, pick best across both")
    parser.add_argument("--samples-dir", type=Path, default=None,
                        help="Samples directory (default: results/samples-{paid|free}/persona-{id})")
    parser.add_argument("--output-dir", type=Path, default=None,
                        help="Output directory for selected runs")
    parser.add_argument("--csv", action="store_true",
                        help="Export all scores to CSV")
    args = parser.parse_args()

    results_root = Path(__file__).parent / "results"
    pid = f"persona-{args.persona_id}"

    if args.mix:
        samples = (
            collect_samples(results_root / "samples-paid" / pid, "paid")
            + collect_samples(results_root / "samples-free" / pid, "free")
        )
        if args.output_dir is None:
            args.output_dir = Path(__file__).parent / "submissions" / "samples-mix" / pid
    elif args.samples_dir:
        samples = collect_samples(args.samples_dir)
        if args.output_dir is None:
            args.output_dir = Path(__file__).parent / "submissions" / pid
    else:
        tier = "samples-free" if args.free else "samples-paid"
        samples = collect_samples(results_root / tier / pid, tier.split("-")[1])
        if args.output_dir is None:
            args.output_dir = Path(__file__).parent / "submissions" / tier / pid

    if not samples:
        print(f"No samples found in {args.samples_dir}")
        return

    # Stats
    scores = [s["score"] for s in samples]
    mean = statistics.mean(scores)
    median = statistics.median(scores)
    stdev = statistics.stdev(scores) if len(scores) > 1 else 0

    print(f"\nPersona {args.persona_id}: {len(samples)} samples")
    print(f"  Scores: {sorted(scores)}")
    print(f"  Mean: {mean:.1f}, Median: {median:.1f}, Stdev: {stdev:.1f}")
    print(f"  Range: {min(scores)} - {max(scores)}")
    print()

    # Histogram
    print_histogram(scores, median)

    # Export CSV if requested
    if args.csv:
        csv_path = args.output_dir / f"persona-{args.persona_id}_scores.csv"
        args.output_dir.mkdir(parents=True, exist_ok=True)
        export_csv(samples, args.persona_id, csv_path)
        print()

    # Symptom consensus: find the 4 most commonly reported symptoms across all samples
    symptom_counts = Counter()
    for s in samples:
        for sym in s.get("key_symptoms", []):
            symptom_counts[sym] += 1
    consensus_symptoms = [sym for sym, _ in symptom_counts.most_common(4)]

    if consensus_symptoms:
        print("  Symptom consensus (top 4):")
        for sym in consensus_symptoms:
            freq = symptom_counts[sym]
            pct = freq / len(samples) * 100
            print(f"    {sym}: {freq}/{len(samples)} ({pct:.0f}%)")
        print()

    # Combined ranking: score distance (normalized) + symptom overlap
    # Lower = better
    score_range = max(scores) - min(scores) if max(scores) != min(scores) else 1
    for s in samples:
        score_dist = abs(s["score"] - median) / score_range  # 0-1
        overlap = len(set(s.get("key_symptoms", [])[:4]) & set(consensus_symptoms))
        symptom_penalty = 1.0 - (overlap / 4.0) if consensus_symptoms else 0.0  # 0-1
        s["rank_score"] = 0.6 * score_dist + 0.4 * symptom_penalty

    ranked = sorted(samples, key=lambda s: s["rank_score"])
    selected = ranked[:args.top]

    print(f"Selected {args.top} (median proximity 60% + symptom consensus 40%):")
    for i, s in enumerate(selected):
        dist = abs(s["score"] - median)
        overlap = len(set(s.get("key_symptoms", [])[:4]) & set(consensus_symptoms))
        tier_tag = f" [{s['tier']}]" if s.get("tier") else ""
        syms = ", ".join(s.get("key_symptoms", [])[:4]) or "-"
        print(f"  Run {i+1}: {s['name']} → BDI={s['score']} (dist={dist:.1f}, "
              f"symptoms={overlap}/4){tier_tag}")
        print(f"         {syms}")

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
