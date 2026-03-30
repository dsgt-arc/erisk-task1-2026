"""
Visualization script for comparing base (paid/GPT) vs new (free/Weaver) approaches.

Reads all CSVs from results/ and generates comparison charts saved to results/figures/.

Usage:
    python visualize.py
    python visualize.py --results-dir results/ --output-dir results/figures/
"""

import argparse
import re
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import seaborn as sns

# ── Colour palette ──────────────────────────────────────────────────────────
BASE_COLOR = "#4C72B0"   # blue  — paid / GPT baseline
NEW_COLOR  = "#DD8452"   # orange — free / Weaver+Tree

SEVERITY_ORDER  = ["Minimal", "Mild", "Moderate", "Severe"]
SEVERITY_COLORS = {
    "Minimal":  "#2ca02c",
    "Mild":     "#bcbd22",
    "Moderate": "#ff7f0e",
    "Severe":   "#d62728",
}

sns.set_theme(style="whitegrid", font_scale=1.1)


# ── Data loading ─────────────────────────────────────────────────────────────

def load_csvs(results_dir: Path) -> pd.DataFrame:
    """Load all *_scores_base.csv and *_scores_new.csv into one DataFrame."""
    rows = []
    for f in sorted(results_dir.glob("persona-*_scores_*.csv")):
        m = re.match(r"persona-(\d+)_scores_(base|new)\.csv", f.name)
        if not m:
            continue
        approach = "Base (Paid)" if m.group(2) == "base" else "New (Weaver+Free)"
        df = pd.read_csv(f)
        df["approach"] = approach
        rows.append(df)

    if not rows:
        raise FileNotFoundError(f"No score CSVs found in {results_dir}")

    combined = pd.concat(rows, ignore_index=True)
    combined["persona_id"] = combined["persona_id"].astype(int)
    combined["persona_label"] = "P" + combined["persona_id"].astype(str)
    combined["severity"] = pd.Categorical(
        combined["severity"], categories=SEVERITY_ORDER, ordered=True
    )
    return combined


def parse_symptoms(df: pd.DataFrame) -> pd.DataFrame:
    """Explode the key_symptoms column into one row per symptom."""
    exploded = df.copy()
    exploded["key_symptoms"] = exploded["key_symptoms"].fillna("").str.split("; ")
    exploded = exploded.explode("key_symptoms")
    exploded = exploded[exploded["key_symptoms"].str.strip() != ""]
    return exploded


# ── Individual plots ──────────────────────────────────────────────────────────

def plot_bdi_boxplot(df: pd.DataFrame, out: Path):
    """Box plots of BDI score per persona, side-by-side approaches."""
    personas = sorted(df["persona_label"].unique())
    fig, ax = plt.subplots(figsize=(max(8, len(personas) * 1.8), 5))

    sns.boxplot(
        data=df, x="persona_label", y="bdi_score", hue="approach",
        order=personas, palette={"Base (Paid)": BASE_COLOR, "New (Weaver+Free)": NEW_COLOR},
        width=0.55, linewidth=1.2, flierprops=dict(marker="o", markersize=4),
        ax=ax,
    )
    ax.set_title("BDI Score Distribution per Persona", fontsize=14, fontweight="bold")
    ax.set_xlabel("Persona")
    ax.set_ylabel("BDI Score (0–63)")
    ax.set_ylim(0, 65)
    ax.axhspan(0, 13, alpha=0.04, color="#2ca02c")
    ax.axhspan(14, 19, alpha=0.04, color="#bcbd22")
    ax.axhspan(20, 28, alpha=0.06, color="#ff7f0e")
    ax.axhspan(29, 63, alpha=0.06, color="#d62728")
    _add_severity_legend(ax)
    ax.legend(title="Approach", loc="upper right")
    fig.tight_layout()
    fig.savefig(out / "01_bdi_boxplot_per_persona.png", dpi=150)
    plt.close(fig)
    print(f"  Saved: 01_bdi_boxplot_per_persona.png")


def plot_bdi_violin(df: pd.DataFrame, out: Path):
    """Violin plot of BDI score distribution across all personas."""
    fig, ax = plt.subplots(figsize=(6, 5))
    sns.violinplot(
        data=df, x="approach", y="bdi_score",
        palette={"Base (Paid)": BASE_COLOR, "New (Weaver+Free)": NEW_COLOR},
        inner="box", linewidth=1.2, ax=ax,
    )
    ax.set_title("Overall BDI Score Distribution", fontsize=14, fontweight="bold")
    ax.set_xlabel("")
    ax.set_ylabel("BDI Score (0–63)")
    ax.set_ylim(0, 65)
    fig.tight_layout()
    fig.savefig(out / "02_bdi_violin_overall.png", dpi=150)
    plt.close(fig)
    print(f"  Saved: 02_bdi_violin_overall.png")


def plot_variance_comparison(df: pd.DataFrame, out: Path):
    """Bar chart: BDI standard deviation per persona for each approach."""
    stats = (
        df.groupby(["persona_label", "approach"])["bdi_score"]
        .std()
        .reset_index()
        .rename(columns={"bdi_score": "std"})
    )
    personas = sorted(df["persona_label"].unique())
    fig, ax = plt.subplots(figsize=(max(8, len(personas) * 1.8), 5))
    sns.barplot(
        data=stats, x="persona_label", y="std", hue="approach",
        order=personas, palette={"Base (Paid)": BASE_COLOR, "New (Weaver+Free)": NEW_COLOR},
        ax=ax,
    )
    ax.set_title("BDI Score Variance (Std Dev) per Persona", fontsize=14, fontweight="bold")
    ax.set_xlabel("Persona")
    ax.set_ylabel("Standard Deviation (BDI points)")
    ax.legend(title="Approach")
    fig.tight_layout()
    fig.savefig(out / "03_variance_comparison.png", dpi=150)
    plt.close(fig)
    print(f"  Saved: 03_variance_comparison.png")


def plot_severity_distribution(df: pd.DataFrame, out: Path):
    """Stacked bar chart of severity band counts per approach."""
    counts = (
        df.groupby(["approach", "severity"])
        .size()
        .reset_index(name="count")
    )
    total = counts.groupby("approach")["count"].transform("sum")
    counts["pct"] = counts["count"] / total * 100

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    for ax, approach, color in zip(
        axes, ["Base (Paid)", "New (Weaver+Free)"], [BASE_COLOR, NEW_COLOR]
    ):
        sub = counts[counts["approach"] == approach]
        sub = sub.set_index("severity").reindex(SEVERITY_ORDER).fillna(0)
        bars = ax.bar(
            sub.index, sub["pct"],
            color=[SEVERITY_COLORS[s] for s in sub.index],
            edgecolor="white", linewidth=1.2,
        )
        ax.set_title(approach, fontsize=12, fontweight="bold")
        ax.set_ylabel("% of Samples")
        ax.set_ylim(0, 100)
        ax.set_xlabel("Severity Band")
        for bar, val in zip(bars, sub["pct"]):
            if val > 3:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 1,
                    f"{val:.0f}%", ha="center", va="bottom", fontsize=9,
                )

    fig.suptitle("Severity Band Distribution", fontsize=14, fontweight="bold")
    fig.tight_layout()
    fig.savefig(out / "04_severity_distribution.png", dpi=150)
    plt.close(fig)
    print(f"  Saved: 04_severity_distribution.png")


def plot_confidence_comparison(df: pd.DataFrame, out: Path):
    """Box plots of confidence per persona for each approach."""
    personas = sorted(df["persona_label"].unique())
    fig, ax = plt.subplots(figsize=(max(8, len(personas) * 1.8), 5))
    sns.boxplot(
        data=df, x="persona_label", y="confidence", hue="approach",
        order=personas, palette={"Base (Paid)": BASE_COLOR, "New (Weaver+Free)": NEW_COLOR},
        width=0.55, linewidth=1.2, ax=ax,
    )
    ax.set_title("Scoring Confidence per Persona", fontsize=14, fontweight="bold")
    ax.set_xlabel("Persona")
    ax.set_ylabel("Mean Confidence (0–1)")
    ax.set_ylim(0, 1.05)
    ax.axhline(0.6, linestyle="--", color="gray", linewidth=1, label="Threshold (0.6)")
    ax.legend(title="Approach")
    fig.tight_layout()
    fig.savefig(out / "05_confidence_comparison.png", dpi=150)
    plt.close(fig)
    print(f"  Saved: 05_confidence_comparison.png")


def plot_turns_comparison(df: pd.DataFrame, out: Path):
    """Box plots of interview turn count per persona."""
    personas = sorted(df["persona_label"].unique())
    fig, ax = plt.subplots(figsize=(max(8, len(personas) * 1.8), 5))
    sns.boxplot(
        data=df, x="persona_label", y="turns", hue="approach",
        order=personas, palette={"Base (Paid)": BASE_COLOR, "New (Weaver+Free)": NEW_COLOR},
        width=0.55, linewidth=1.2, ax=ax,
    )
    ax.set_title("Interview Turn Count per Persona", fontsize=14, fontweight="bold")
    ax.set_xlabel("Persona")
    ax.set_ylabel("Number of Turns")
    ax.legend(title="Approach")
    fig.tight_layout()
    fig.savefig(out / "06_turns_comparison.png", dpi=150)
    plt.close(fig)
    print(f"  Saved: 06_turns_comparison.png")


def plot_mean_scatter(df: pd.DataFrame, out: Path):
    """Scatter plot: mean BDI base vs mean BDI new per persona."""
    means = (
        df.groupby(["persona_label", "approach"])["bdi_score"]
        .mean()
        .unstack("approach")
    )
    if "Base (Paid)" not in means.columns or "New (Weaver+Free)" not in means.columns:
        print("  Skipped scatter (missing approach)")
        return

    fig, ax = plt.subplots(figsize=(5.5, 5.5))
    for persona, row in means.iterrows():
        ax.scatter(row["Base (Paid)"], row["New (Weaver+Free)"],
                   s=90, zorder=5, color="#333")
        ax.annotate(persona, (row["Base (Paid)"], row["New (Weaver+Free)"]),
                    textcoords="offset points", xytext=(6, 4), fontsize=9)

    lo = min(means.min()) - 3
    hi = max(means.max()) + 3
    ax.plot([lo, hi], [lo, hi], "--", color="gray", linewidth=1, label="y = x")
    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    ax.set_xlabel("Mean BDI — Base (Paid)")
    ax.set_ylabel("Mean BDI — New (Weaver+Free)")
    ax.set_title("Mean BDI Score: Base vs New per Persona",
                 fontsize=13, fontweight="bold")
    ax.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(out / "07_mean_bdi_scatter.png", dpi=150)
    plt.close(fig)
    print(f"  Saved: 07_mean_bdi_scatter.png")


def plot_symptom_heatmap(df: pd.DataFrame, out: Path):
    """Heatmap of symptom frequency (% of samples) — base vs new."""
    sym_df = parse_symptoms(df)
    if sym_df.empty:
        print("  Skipped symptom heatmap (no symptom data)")
        return

    # Count how often each symptom appears (% of samples per approach)
    totals = df.groupby("approach").size().to_dict()
    counts = (
        sym_df.groupby(["approach", "key_symptoms"])
        .size()
        .reset_index(name="count")
    )
    counts["pct"] = counts.apply(
        lambda r: r["count"] / totals.get(r["approach"], 1) * 100, axis=1
    )
    pivot = counts.pivot_table(
        index="key_symptoms", columns="approach", values="pct", fill_value=0
    )
    # Keep symptoms mentioned in ≥5% of samples by at least one approach
    pivot = pivot[(pivot >= 5).any(axis=1)]
    pivot = pivot.sort_values(
        pivot.columns.tolist()[0] if pivot.columns.any() else pivot.columns[0],
        ascending=False,
    )

    fig, ax = plt.subplots(figsize=(8, max(5, len(pivot) * 0.4 + 1)))
    sns.heatmap(
        pivot, annot=True, fmt=".0f", cmap="YlOrRd",
        linewidths=0.5, cbar_kws={"label": "% of samples"},
        ax=ax,
    )
    ax.set_title("Symptom Frequency (% samples flagged as key)",
                 fontsize=13, fontweight="bold")
    ax.set_xlabel("Approach")
    ax.set_ylabel("Symptom")
    fig.tight_layout()
    fig.savefig(out / "08_symptom_heatmap.png", dpi=150)
    plt.close(fig)
    print(f"  Saved: 08_symptom_heatmap.png")


def plot_symptom_diff_bar(df: pd.DataFrame, out: Path):
    """Horizontal bar: difference in symptom frequency (new − base)."""
    sym_df = parse_symptoms(df)
    if sym_df.empty:
        return

    totals = df.groupby("approach").size().to_dict()
    counts = (
        sym_df.groupby(["approach", "key_symptoms"])
        .size()
        .reset_index(name="count")
    )
    counts["pct"] = counts.apply(
        lambda r: r["count"] / totals.get(r["approach"], 1) * 100, axis=1
    )
    pivot = counts.pivot_table(
        index="key_symptoms", columns="approach", values="pct", fill_value=0
    )
    if "Base (Paid)" not in pivot.columns or "New (Weaver+Free)" not in pivot.columns:
        return
    diff = (pivot["New (Weaver+Free)"] - pivot["Base (Paid)"]).sort_values()
    diff = diff[diff.abs() >= 3]   # only show meaningful differences

    fig, ax = plt.subplots(figsize=(7, max(4, len(diff) * 0.4 + 1)))
    colors = [NEW_COLOR if v > 0 else BASE_COLOR for v in diff]
    ax.barh(diff.index, diff.values, color=colors, edgecolor="white")
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_xlabel("Difference in % flagged (New − Base)")
    ax.set_title("Symptom Frequency Shift: New vs Base",
                 fontsize=13, fontweight="bold")
    patches = [
        mpatches.Patch(color=NEW_COLOR, label="More in New (Weaver+Free)"),
        mpatches.Patch(color=BASE_COLOR, label="More in Base (Paid)"),
    ]
    ax.legend(handles=patches, fontsize=9)
    fig.tight_layout()
    fig.savefig(out / "09_symptom_diff_bar.png", dpi=150)
    plt.close(fig)
    print(f"  Saved: 09_symptom_diff_bar.png")


def plot_confidence_vs_bdi(df: pd.DataFrame, out: Path):
    """Scatter: confidence vs BDI score, coloured by approach."""
    fig, ax = plt.subplots(figsize=(7, 5))
    for approach, color in [("Base (Paid)", BASE_COLOR), ("New (Weaver+Free)", NEW_COLOR)]:
        sub = df[df["approach"] == approach]
        ax.scatter(sub["bdi_score"], sub["confidence"], alpha=0.5, s=30,
                   color=color, label=approach)
    ax.set_xlabel("BDI Score")
    ax.set_ylabel("Confidence")
    ax.set_title("Confidence vs BDI Score", fontsize=13, fontweight="bold")
    ax.legend(title="Approach")
    fig.tight_layout()
    fig.savefig(out / "10_confidence_vs_bdi_scatter.png", dpi=150)
    plt.close(fig)
    print(f"  Saved: 10_confidence_vs_bdi_scatter.png")


def plot_turns_vs_bdi(df: pd.DataFrame, out: Path):
    """Scatter: turns vs BDI score, coloured by approach."""
    fig, ax = plt.subplots(figsize=(7, 5))
    for approach, color in [("Base (Paid)", BASE_COLOR), ("New (Weaver+Free)", NEW_COLOR)]:
        sub = df[df["approach"] == approach]
        ax.scatter(sub["turns"], sub["bdi_score"], alpha=0.5, s=30,
                   color=color, label=approach)
    ax.set_xlabel("Number of Turns")
    ax.set_ylabel("BDI Score")
    ax.set_title("Interview Length vs BDI Score", fontsize=13, fontweight="bold")
    ax.legend(title="Approach")
    fig.tight_layout()
    fig.savefig(out / "11_turns_vs_bdi_scatter.png", dpi=150)
    plt.close(fig)
    print(f"  Saved: 11_turns_vs_bdi_scatter.png")


def plot_severity_agreement(df: pd.DataFrame, out: Path):
    """For each persona: compare median severity band between approaches."""
    medians = (
        df.groupby(["persona_label", "approach"])["bdi_score"]
        .median()
        .unstack("approach")
        .reset_index()
    )
    if "Base (Paid)" not in medians.columns or "New (Weaver+Free)" not in medians.columns:
        return

    personas = sorted(medians["persona_label"].unique())
    x = np.arange(len(personas))
    w = 0.35

    fig, ax = plt.subplots(figsize=(max(8, len(personas) * 1.8), 5))
    bars_base = ax.bar(x - w / 2, medians["Base (Paid)"],     w, color=BASE_COLOR, label="Base (Paid)")
    bars_new  = ax.bar(x + w / 2, medians["New (Weaver+Free)"], w, color=NEW_COLOR,  label="New (Weaver+Free)")

    ax.set_xticks(x)
    ax.set_xticklabels(personas)
    ax.set_xlabel("Persona")
    ax.set_ylabel("Median BDI Score")
    ax.set_ylim(0, 65)
    ax.set_title("Median BDI Score per Persona: Base vs New",
                 fontsize=13, fontweight="bold")
    _add_severity_legend(ax, loc="upper left")
    ax.axhspan(0,  13, alpha=0.04, color="#2ca02c")
    ax.axhspan(14, 19, alpha=0.04, color="#bcbd22")
    ax.axhspan(20, 28, alpha=0.06, color="#ff7f0e")
    ax.axhspan(29, 63, alpha=0.06, color="#d62728")
    ax.legend(title="Approach", loc="upper right")
    fig.tight_layout()
    fig.savefig(out / "12_median_bdi_per_persona.png", dpi=150)
    plt.close(fig)
    print(f"  Saved: 12_median_bdi_per_persona.png")


def plot_bdi_histogram_overlay(df: pd.DataFrame, out: Path):
    """Overlapping histograms of BDI scores for all samples."""
    fig, ax = plt.subplots(figsize=(7, 5))
    bins = np.arange(0, 66, 4)
    for approach, color in [("Base (Paid)", BASE_COLOR), ("New (Weaver+Free)", NEW_COLOR)]:
        sub = df[df["approach"] == approach]["bdi_score"]
        ax.hist(sub, bins=bins, alpha=0.55, color=color, label=approach, edgecolor="white")
    ax.axvline(13.5, color="#2ca02c", linestyle=":", linewidth=1.2)
    ax.axvline(19.5, color="#bcbd22", linestyle=":", linewidth=1.2)
    ax.axvline(28.5, color="#ff7f0e", linestyle=":", linewidth=1.2)
    ax.set_xlabel("BDI Score")
    ax.set_ylabel("Count")
    ax.set_title("BDI Score Histogram (All Samples)", fontsize=13, fontweight="bold")
    ax.legend(title="Approach")
    fig.tight_layout()
    fig.savefig(out / "13_bdi_histogram_overlay.png", dpi=150)
    plt.close(fig)
    print(f"  Saved: 13_bdi_histogram_overlay.png")


def plot_summary_table(df: pd.DataFrame, out: Path):
    """Render a summary stats table as a figure."""
    summary = (
        df.groupby(["persona_label", "approach"])["bdi_score"]
        .agg(["mean", "std", "median", "min", "max"])
        .round(1)
        .reset_index()
    )
    summary.columns = ["Persona", "Approach", "Mean", "Std", "Median", "Min", "Max"]

    fig, ax = plt.subplots(figsize=(12, max(3, len(summary) * 0.35 + 1.5)))
    ax.axis("off")
    tbl = ax.table(
        cellText=summary.values,
        colLabels=summary.columns,
        cellLoc="center",
        loc="center",
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(9)
    tbl.scale(1, 1.4)

    # Colour header
    for j in range(len(summary.columns)):
        tbl[0, j].set_facecolor("#404040")
        tbl[0, j].set_text_props(color="white", fontweight="bold")

    # Colour approach cells
    for i in range(1, len(summary) + 1):
        approach = summary.iloc[i - 1]["Approach"]
        color = "#dce8f5" if "Base" in approach else "#fde8d0"
        for j in range(len(summary.columns)):
            tbl[i, j].set_facecolor(color)

    ax.set_title("Summary Statistics: BDI Scores by Persona & Approach",
                 fontsize=12, fontweight="bold", pad=10)
    fig.tight_layout()
    fig.savefig(out / "14_summary_table.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: 14_summary_table.png")


def plot_confidence_mean_bar(df: pd.DataFrame, out: Path):
    """Mean confidence bar chart per persona, grouped by approach."""
    personas = sorted(df["persona_label"].unique())
    stats = (
        df.groupby(["persona_label", "approach"])["confidence"]
        .mean()
        .reset_index()
    )
    fig, ax = plt.subplots(figsize=(max(8, len(personas) * 1.8), 5))
    sns.barplot(
        data=stats, x="persona_label", y="confidence", hue="approach",
        order=personas, palette={"Base (Paid)": BASE_COLOR, "New (Weaver+Free)": NEW_COLOR},
        ax=ax,
    )
    ax.axhline(0.6, linestyle="--", color="gray", linewidth=1, label="Threshold (0.6)")
    ax.set_title("Mean Confidence per Persona", fontsize=13, fontweight="bold")
    ax.set_xlabel("Persona")
    ax.set_ylabel("Mean Confidence")
    ax.set_ylim(0, 1.0)
    ax.legend(title="Approach")
    fig.tight_layout()
    fig.savefig(out / "15_confidence_mean_bar.png", dpi=150)
    plt.close(fig)
    print(f"  Saved: 15_confidence_mean_bar.png")


def plot_top_symptoms_grouped(df: pd.DataFrame, out: Path):
    """Grouped bar chart: top 10 most frequent symptoms, base vs new."""
    sym_df = parse_symptoms(df)
    if sym_df.empty:
        return

    totals = df.groupby("approach").size().to_dict()
    counts = (
        sym_df.groupby(["approach", "key_symptoms"])
        .size()
        .reset_index(name="count")
    )
    counts["pct"] = counts.apply(
        lambda r: r["count"] / totals.get(r["approach"], 1) * 100, axis=1
    )

    # Top 10 symptoms by combined frequency
    top_symptoms = (
        counts.groupby("key_symptoms")["pct"].sum()
        .nlargest(10).index.tolist()
    )
    sub = counts[counts["key_symptoms"].isin(top_symptoms)]

    fig, ax = plt.subplots(figsize=(10, 5))
    sns.barplot(
        data=sub, x="key_symptoms", y="pct", hue="approach",
        order=top_symptoms,
        palette={"Base (Paid)": BASE_COLOR, "New (Weaver+Free)": NEW_COLOR},
        ax=ax,
    )
    ax.set_xticklabels(ax.get_xticklabels(), rotation=35, ha="right", fontsize=9)
    ax.set_title("Top 10 Key Symptoms: Base vs New",
                 fontsize=13, fontweight="bold")
    ax.set_xlabel("Symptom")
    ax.set_ylabel("% of Samples")
    ax.legend(title="Approach")
    fig.tight_layout()
    fig.savefig(out / "16_top_symptoms_grouped_bar.png", dpi=150)
    plt.close(fig)
    print(f"  Saved: 16_top_symptoms_grouped_bar.png")


def plot_score_range_per_persona(df: pd.DataFrame, out: Path):
    """Per-persona: range (max-min) of BDI scores as a proxy for consistency."""
    ranges = (
        df.groupby(["persona_label", "approach"])["bdi_score"]
        .agg(lambda x: x.max() - x.min())
        .reset_index()
        .rename(columns={"bdi_score": "range"})
    )
    personas = sorted(df["persona_label"].unique())
    fig, ax = plt.subplots(figsize=(max(8, len(personas) * 1.8), 5))
    sns.barplot(
        data=ranges, x="persona_label", y="range", hue="approach",
        order=personas, palette={"Base (Paid)": BASE_COLOR, "New (Weaver+Free)": NEW_COLOR},
        ax=ax,
    )
    ax.set_title("BDI Score Range (Max − Min) per Persona",
                 fontsize=13, fontweight="bold")
    ax.set_xlabel("Persona")
    ax.set_ylabel("BDI Score Range (points)")
    ax.legend(title="Approach")
    fig.tight_layout()
    fig.savefig(out / "17_score_range_per_persona.png", dpi=150)
    plt.close(fig)
    print(f"  Saved: 17_score_range_per_persona.png")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _add_severity_legend(ax, loc="lower right"):
    patches = [
        mpatches.Patch(color=SEVERITY_COLORS[s], alpha=0.5, label=s)
        for s in SEVERITY_ORDER
    ]
    leg = ax.legend(handles=patches, title="Severity Bands", fontsize=8,
                    loc=loc, framealpha=0.8)
    ax.add_artist(leg)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Visualize base vs new approach comparison")
    parser.add_argument("--results-dir", type=Path,
                        default=Path(__file__).parent / "results")
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()

    out = args.output_dir or args.results_dir / "figures"
    out.mkdir(parents=True, exist_ok=True)

    print(f"Loading CSVs from: {args.results_dir}")
    df = load_csvs(args.results_dir)
    print(f"  {len(df)} samples across {df['persona_id'].nunique()} personas\n")
    print(f"Saving figures to: {out}\n")

    plot_bdi_boxplot(df, out)
    plot_bdi_violin(df, out)
    plot_variance_comparison(df, out)
    plot_severity_distribution(df, out)
    plot_confidence_comparison(df, out)
    plot_turns_comparison(df, out)
    plot_mean_scatter(df, out)
    plot_symptom_heatmap(df, out)
    plot_symptom_diff_bar(df, out)
    plot_confidence_vs_bdi(df, out)
    plot_turns_vs_bdi(df, out)
    plot_severity_agreement(df, out)
    plot_bdi_histogram_overlay(df, out)
    plot_summary_table(df, out)
    plot_confidence_mean_bar(df, out)
    plot_top_symptoms_grouped(df, out)
    plot_score_range_per_persona(df, out)

    print(f"\nDone. {len(list(out.glob('*.png')))} figures saved to {out}")


if __name__ == "__main__":
    main()
