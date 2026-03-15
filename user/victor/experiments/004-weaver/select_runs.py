"""
Select the 3 best runs from a batch of samples using Weaver-style aggregation.

Learns per-sample reliability weights from pairwise agreement across 21 BDI-II
symptoms, builds a consensus profile via weighted median, and selects runs
closest to consensus.

Usage:
    python select_runs.py <persona_id>
    python select_runs.py 4           # analyze persona 4 (paid only)
    python select_runs.py 4 --free    # analyze persona 4 (free only)
    python select_runs.py 4 --mix     # pool paid + free, pick best 3
    python select_runs.py 4 --top 3   # pick top 3 (default)
    python select_runs.py 4 --csv     # export scores to CSV
    python select_runs.py 4 --legacy  # use old heuristic instead of Weaver
"""

import argparse
import csv
import json
import re
import shutil
import statistics
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from models import BDI_SYMPTOM_IDS, SYMPTOM_ID_TO_NAME, ScorerOutput, SymptomScore
from weaver import WeaverAggregator


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
        entry["key_symptoms"] = data[0].get("key-symptoms", [])

        # Pull per-symptom scores from detailed log
        detailed = list(sample_dir.glob("detailed_log_run1_*.json"))
        if detailed:
            with open(detailed[0]) as f:
                detail_data = json.load(f)
            if detail_data:
                entry["confidence"] = detail_data[0].get("confidence", 0.0)
                entry["severity"] = detail_data[0].get("severity", "")
                entry["turns"] = detail_data[0].get("total_turns", 0)
                # Extract per-symptom scores for Weaver aggregation
                assessment = detail_data[0].get("final_assessment", {})
                if assessment:
                    entry["symptom_scores"] = assessment
        samples.append(entry)
    return samples


def sample_to_scorer_output(sample: dict) -> ScorerOutput:
    """Convert a sample's symptom_scores dict into a ScorerOutput."""
    assessment = sample.get("symptom_scores", {})
    symptoms = {}
    for sid in BDI_SYMPTOM_IDS:
        if sid in assessment:
            s = assessment[sid]
            symptoms[sid] = SymptomScore(
                symptom_id=sid,
                score=int(s.get("score", 0)),
                confidence=float(s.get("confidence", 0.0)),
                evidence=s.get("evidence", ""),
                assessed=float(s.get("confidence", 0.0)) > 0.0,
            )
        else:
            symptoms[sid] = SymptomScore(
                symptom_id=sid, score=0, confidence=0.0,
                evidence="", assessed=False,
            )
    return ScorerOutput(symptoms=symptoms)


def print_histogram(scores, median_val):
    """Print an ASCII histogram of the score distribution."""
    if not scores:
        return

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


def legacy_select(samples, top_n):
    """Original heuristic: 60% median proximity + 40% symptom consensus."""
    scores = [s["score"] for s in samples]
    median = statistics.median(scores)
    score_range = max(scores) - min(scores) if max(scores) != min(scores) else 1

    symptom_counts = Counter()
    for s in samples:
        for sym in s.get("key_symptoms", []):
            symptom_counts[sym] += 1
    consensus_symptoms = [sym for sym, _ in symptom_counts.most_common(4)]

    for s in samples:
        score_dist = abs(s["score"] - median) / score_range
        overlap = len(set(s.get("key_symptoms", [])[:4]) & set(consensus_symptoms))
        symptom_penalty = 1.0 - (overlap / 4.0) if consensus_symptoms else 0.0
        s["legacy_rank"] = 0.6 * score_dist + 0.4 * symptom_penalty

    ranked = sorted(samples, key=lambda s: s["legacy_rank"])
    return ranked[:top_n]


def weaver_select(samples, top_n):
    """Weaver-style selection using pairwise agreement weights."""
    # Build ScorerOutputs from detailed logs
    scorer_outputs = []
    valid_indices = []
    for i, s in enumerate(samples):
        if "symptom_scores" in s:
            scorer_outputs.append(sample_to_scorer_output(s))
            valid_indices.append(i)

    if not scorer_outputs:
        print("  [WARNING] No per-symptom scores found in detailed logs. Falling back to legacy.")
        return legacy_select(samples, top_n)

    if len(scorer_outputs) < 3:
        print(f"  [WARNING] Only {len(scorer_outputs)} samples with per-symptom scores. Using all.")

    aggregator = WeaverAggregator()
    weights = aggregator.learn_weights(scorer_outputs)
    consensus = aggregator.consensus_profile(scorer_outputs, weights)
    ranked = aggregator.rank_samples(scorer_outputs, consensus, weights)

    # Print diagnostics
    print(f"\n  === Weaver Aggregation ({len(scorer_outputs)} samples) ===")

    # Top/bottom weights
    weight_pairs = sorted(weights.items(), key=lambda x: -x[1])
    top_w = ", ".join(f"#{valid_indices[i]}={w:.3f}" for i, w in weight_pairs[:5])
    bot_w = ", ".join(f"#{valid_indices[i]}={w:.3f}" for i, w in weight_pairs[-2:])
    print(f"  Weights: {top_w} ... {bot_w}")

    # Consensus profile
    top_symptoms = sorted(
        consensus.symptoms.values(), key=lambda s: s.score, reverse=True
    )
    symptom_summary = ", ".join(
        f"{SYMPTOM_ID_TO_NAME.get(s.symptom_id, s.symptom_id)}={s.score}"
        for s in top_symptoms if s.score > 0
    )
    print(f"  Consensus BDI: {consensus.total_score} ({consensus.severity})")
    if symptom_summary:
        print(f"  Active symptoms: {symptom_summary}")
    print()

    # Map back to original samples
    selected = []
    for idx, dist in ranked[:top_n]:
        orig_idx = valid_indices[idx]
        samples[orig_idx]["weaver_dist"] = dist
        samples[orig_idx]["weaver_weight"] = weights[idx]
        selected.append(samples[orig_idx])

    return selected, consensus


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
    parser.add_argument("--legacy", action="store_true",
                        help="Use old heuristic (60%% median + 40%% consensus) instead of Weaver")
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
        print(f"No samples found for persona {args.persona_id}")
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

    print_histogram(scores, median)

    # Export CSV if requested
    if args.csv:
        csv_path = args.output_dir / f"persona-{args.persona_id}_scores.csv"
        args.output_dir.mkdir(parents=True, exist_ok=True)
        export_csv(samples, args.persona_id, csv_path)
        print()

    # Select runs
    if args.legacy:
        selected = legacy_select(samples, args.top)
        consensus = None
        print(f"Selected {args.top} (legacy: median proximity 60% + symptom consensus 40%):")
        for i, s in enumerate(selected):
            dist = abs(s["score"] - median)
            syms = ", ".join(s.get("key_symptoms", [])[:4]) or "-"
            tier_tag = f" [{s['tier']}]" if s.get("tier") else ""
            print(f"  Run {i+1}: {s['name']} → BDI={s['score']} (dist={dist:.1f}){tier_tag}")
            print(f"         {syms}")
    else:
        result = weaver_select(samples, args.top)
        if isinstance(result, tuple):
            selected, consensus = result
        else:
            selected = result

        print(f"Selected {args.top} (Weaver pairwise agreement):")
        for i, s in enumerate(selected):
            dist = s.get("weaver_dist", "?")
            weight = s.get("weaver_weight", 0.0)
            syms = ", ".join(s.get("key_symptoms", [])[:4]) or "-"
            tier_tag = f" [{s['tier']}]" if s.get("tier") else ""
            print(f"  Run {i+1}: {s['name']} → BDI={s['score']} (dist={dist}, w={weight:.3f}){tier_tag}")
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
        for old_file in dest.glob("*_run*.*"):
            new_name = re.sub(r"_run\d+", f"_run{run_id}", old_file.name)
            if new_name != old_file.name:
                old_file.rename(dest / new_name)

        print(f"  → Copied to {dest}")

    print(f"\nDone. Submissions in {args.output_dir}")


if __name__ == "__main__":
    main()
